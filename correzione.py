"""
correzione.py — la correzione assistita dei compiti dalle foto (senza Streamlit).

Il docente sceglie la verifica (una delle sue, oppure la traccia da foto) e carica i compiti degli alunni, uno per file. Per ogni alunno l'AI legge le
pagine e propone, richiesta per richiesta, punti, esito e un breve commento; il docente controlla (le valutazioni dubbie sono segnalate), corregge i
punti e ottiene voti, schede per gli alunni, un resoconto della classe e gli argomenti da ripassare.

REGOLE:
- I PUNTI E IL VOTO LI CALCOLA IL CODICE: l'AI propone i punti di ogni richiesta, che qui si limitano a [0, massimo] a passi di 0,5; somme e voti non
  si fidano mai dell'AI.
- La struttura da correggere (richieste, id, punti massimi) viene dal LaTeX della verifica (`latex_utils.parse_esercizi`, lo stesso lettore della tabella dei
  punteggi), non dall'AI: gli id sono stabili e uguali per tutti gli alunni.
- Un compito che l'AI non riesce a leggere NON diventa uno zero: resta «da controllare».
- Privacy: i compiti e i nomi degli alunni vivono solo nella sessione. Qui non si scrive mai su disco o database.
"""
import csv
import io
import json
import logging
import re
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed

import esercizio_foto as ef
from config import MAX_PAGINE_COMPITO
from latex_utils import extract_blocks, parse_esercizi
from prompts import prompt_correggi_compito, prompt_soluzioni

logger = logging.getLogger(__name__)

ESITI = ("corretto", "parziale", "errato", "vuoto", "illeggibile")
SOGLIA_CONFIDENZA = 0.7          # sotto questa soglia la valutazione è «da controllare»
SCALE = {
    "prop": "Proporzionale (punti ÷ totale × 10)",
    "suff60": "Sufficienza al 60% (il 6 corrisponde al 60% dei punti)",
}
SCALA_PREDEFINITA = "prop"


# ── Struttura della verifica ──────────────────────────────────────────────────
def _numero(v) -> float:
    try:
        return float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return 0.0


def struttura_da_latex(latex: str) -> dict:
    """La struttura da correggere: {"esercizi": [{"n", "titolo", "testo", "richieste": [{"id", "label", "punti_max"}]}], "totale", "punti_assegnati"}.
    Gli id sono «1a», «1b», «2», …; se la verifica non ha punti si dividono 100 punti in parti uguali (`punti_assegnati` = True)."""
    _pre, blocchi = extract_blocks(latex or "")
    letti = parse_esercizi(latex or "")
    esercizi, usati = [], set()
    for i, (b, p) in enumerate(zip(blocchi, letti), 1):
        voci = p.get("items") or []
        richieste = []
        for k, (label, pts) in enumerate(voci, 1):
            lab = re.sub(r"[^0-9A-Za-z]", "", str(label or "")).lower()
            rid = f"{i}{lab}" if lab else (f"{i}" if len(voci) == 1 else f"{i}.{k}")
            while rid in usati:
                rid += "'"
            usati.add(rid)
            richieste.append({"id": rid, "label": str(label or "").strip() or "—", "punti_max": _numero(pts)})
        corpo = re.sub(r"\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}", "[grafico]", b.get("body", ""), flags=re.DOTALL)
        esercizi.append({"n": i, "titolo": re.sub(r"\s+", " ", b.get("title", "")).strip(), "testo": corpo.strip()[:1800], "richieste": richieste})
    totale = sum(r["punti_max"] for e in esercizi for r in e["richieste"])
    assegnati = False
    nr = sum(len(e["richieste"]) for e in esercizi)
    if esercizi and totale <= 0 and nr:                  # nessun punteggio nella verifica: 100 punti in parti uguali
        assegnati = True
        base = round(100 / nr * 2) / 2
        for e in esercizi:
            for r in e["richieste"]:
                r["punti_max"] = base
        totale = sum(r["punti_max"] for e in esercizi for r in e["richieste"])
    return {"esercizi": esercizi, "totale": totale, "punti_assegnati": assegnati}


def richieste_piatte(struttura: dict) -> list:
    """Tutte le richieste in ordine, ciascuna con il suo esercizio: [{"id", "label", "punti_max", "esercizio", "titolo"}]."""
    return [{**r, "esercizio": e["n"], "titolo": e["titolo"]} for e in struttura.get("esercizi", []) for r in e["richieste"]]


def titolo_breve(titolo: str) -> str:
    return re.sub(r"^\s*Esercizio\s*\d+\s*[:.\-–]?\s*", "", titolo or "", flags=re.IGNORECASE).strip() or titolo or "Esercizio"


def traccia_testo(struttura: dict) -> str:
    """La traccia per il prompt: per ogni esercizio il testo e l'elenco delle richieste con id e punti massimi."""
    righe = []
    for e in struttura.get("esercizi", []):
        righe.append(f"ESERCIZIO {e['n']} — {titolo_breve(e['titolo'])}\n{e['testo']}")
        for r in e["richieste"]:
            righe.append(f"  · {r['id']} · {r['punti_max']:g} pt" + (f" · richiesta {r['label']}" if r["label"] != "—" else ""))
        righe.append("")
    return "\n".join(righe).strip()


def soluzioni_di_riferimento(model, latex: str, materia: str) -> str:
    """Le soluzioni sintetiche della verifica (una chiamata): servono di riferimento a chi corregge. Stringa vuota se non si riesce."""
    corpo = "\n\n".join(f"\\subsection*{{{b['title']}}}\n{b['body']}" for b in extract_blocks(latex or "")[1])
    if not corpo.strip():
        return ""
    try:
        r = model.generate_content(prompt_soluzioni(corpo, materia))
        return (r.text or "").strip()
    except Exception as e:
        logger.warning("soluzioni di riferimento non riuscite: %s", e)
        return ""


# ── Lettura e controllo della risposta dell'AI ────────────────────────────────
def _estrai_json(testo: str):
    t = re.sub(r"^```[a-z]*\s*|\s*```$", "", (testo or "").strip())
    try:
        return json.loads(t)
    except ValueError:
        m = re.search(r"\{.*\}", t, re.DOTALL)
        if not m:
            return None
        try:
            return json.loads(m.group(0))
        except ValueError:
            return None


def _passo(v: float, massimo: float) -> float:
    return max(0.0, min(float(massimo), round(float(v) * 2) / 2))


def _testo(v, massimo: int) -> str:
    t = re.sub(r"\s+", " ", str(v or "")).strip()
    return "" if t.lower() in ("null", "none") else t[:massimo]


def normalizza_correzione(grezzo, struttura: dict) -> dict:
    """La risposta dell'AI riportata alla struttura vera: una riga per OGNI richiesta, punti nei limiti, esiti validi. Ciò che manca resta «da controllare»."""
    g = grezzo if isinstance(grezzo, dict) else {}
    per_id = {}
    for r in (g.get("righe") if isinstance(g.get("righe"), list) else []):
        if isinstance(r, dict) and r.get("id") is not None:
            per_id[str(r["id"]).strip().lower()] = r
    righe = []
    for r in richieste_piatte(struttura):
        v = per_id.get(r["id"].lower())
        if v is None:
            righe.append({**r, "punti": 0.0, "esito": "vuoto", "commento": "Non l'ho trovata nel compito: controlla.", "confidenza": 0.0, "da_controllare": True})
            continue
        esito = str(v.get("esito") or "").strip().lower()
        esito = esito if esito in ESITI else "parziale"
        try:
            conf = max(0.0, min(1.0, float(v.get("confidenza", 0.7))))
        except (TypeError, ValueError):
            conf = 0.7
        righe.append({**r, "punti": _passo(_numero(v.get("punti")), r["punti_max"]), "esito": esito, "commento": _testo(v.get("commento"), 140),
                      "confidenza": conf, "da_controllare": conf < SOGLIA_CONFIDENZA or esito == "illeggibile"})
    nome = _testo(g.get("nome"), 40)
    return {"nome": nome, "non_corrisponde": g.get("non_corrisponde") is True, "righe": righe,
            "commento_generale": _testo(g.get("commento_generale"), 280)}


def correggi_compito(model, struttura: dict, soluzioni: str, compito: list, materia: str = "", scuola: str = "") -> dict:
    """Corregge il compito di un alunno. `compito` = pagine {"data", "mime_type", "name"}. Restituisce {"ok", "correzione" | "messaggio"}; non solleva mai.
    Un tentativo in più se la risposta non è un JSON utilizzabile."""
    errore = ef.controlla_foto(compito, MAX_PAGINE_COMPITO)
    if errore:
        return {"ok": False, "messaggio": errore}
    parti = ef._parti(compito)
    prompt = prompt_correggi_compito(materia, scuola, traccia_testo(struttura), soluzioni, len(parti))
    ultimo = "risposta non valida"
    for _ in range(2):
        try:
            risposta = ef._chiama(model, [prompt] + parti)
        except Exception as e:
            ultimo = str(e)[:140]
            continue
        grezzo = _estrai_json(risposta)
        if isinstance(grezzo, dict) and isinstance(grezzo.get("righe"), list) and grezzo["righe"]:
            return {"ok": True, "correzione": normalizza_correzione(grezzo, struttura)}
    return {"ok": False, "messaggio": f"Non sono riuscito a leggere questo compito ({ultimo}). Prova con una foto più nitida."}


def correggi_tutti(model, struttura: dict, soluzioni: str, compiti: list, materia: str = "", scuola: str = "", on_fatto=None, paralleli: int = 3) -> list:
    """Corregge più compiti insieme (poche chiamate in parallelo). `compiti` = [pagine di ciascun alunno]. Restituisce i risultati nello stesso ordine.
    `on_fatto(n_fatti, totale)` è chiamata dal thread di chi invoca (si può usare per aggiornare una barra)."""
    risultati = [None] * len(compiti)
    if not compiti:
        return risultati
    with ThreadPoolExecutor(max_workers=max(1, min(paralleli, len(compiti)))) as pool:
        futuri = {pool.submit(correggi_compito, model, struttura, soluzioni, c, materia, scuola): i for i, c in enumerate(compiti)}
        fatti = 0
        for f in as_completed(futuri):
            i = futuri[f]
            try:
                risultati[i] = f.result()
            except Exception as e:                       # non dovrebbe accadere (correggi_compito non solleva), ma un thread non deve fermare gli altri
                risultati[i] = {"ok": False, "messaggio": str(e)[:140]}
            fatti += 1
            if on_fatto:
                try:
                    on_fatto(fatti, len(compiti))
                except Exception:
                    pass
    return risultati


# ── Punti, voti, statistiche ──────────────────────────────────────────────────
def punti_alunno(righe: list) -> tuple:
    """(punti ottenuti, massimo) di un alunno: sempre ricalcolati qui."""
    return sum(r["punti"] for r in righe), sum(r["punti_max"] for r in righe)


def voto(punti: float, massimo: float, scala: str = SCALA_PREDEFINITA) -> float:
    """Il voto in decimi, a mezzi punti. 'prop' = proporzionale; 'suff60' = il 6 al 60% dei punti (2 a zero, 10 al massimo)."""
    if massimo <= 0:
        return 0.0
    p = max(0.0, min(1.0, punti / massimo))
    v = (2 + p / 0.6 * 4 if p < 0.6 else 6 + (p - 0.6) / 0.4 * 4) if scala == "suff60" else p * 10
    return round(v * 2) / 2


def voto_testo(v: float) -> str:
    return (f"{v:g}").replace(".", ",")


def valido(alunno: dict) -> bool:
    """L'alunno ha una correzione utilizzabile (non in errore, non di un'altra verifica)."""
    return bool(alunno.get("righe")) and not alunno.get("errore") and not alunno.get("non_corrisponde")


def statistiche(alunni: list, struttura: dict, scala: str = SCALA_PREDEFINITA) -> dict:
    """Il quadro della classe: voti, media, mediana, sufficienti, distribuzione, esercizi e richieste da ripassare (dai punti persi)."""
    ok = [a for a in alunni if valido(a)]
    voti = [voto(*punti_alunno(a["righe"]), scala) for a in ok]
    if not voti:
        return {"n": 0, "voti": [], "media": None, "mediana": None, "minimo": None, "massimo": None, "sufficienti": 0, "distribuzione": {}, "esercizi": [], "richieste": []}
    etichette = ["<4", "4", "5", "6", "7", "8", "9", "10"]
    distribuzione = {e: 0 for e in etichette}
    for v in voti:
        distribuzione["<4" if v < 4 else str(min(10, int(v)))] += 1
    esercizi, richieste = [], []
    for e in struttura.get("esercizi", []):
        mx = sum(r["punti_max"] for r in e["richieste"])
        if mx <= 0:
            continue
        ottenuti = sum(r["punti"] for a in ok for r in a["righe"] if r["esercizio"] == e["n"])
        esercizi.append({"n": e["n"], "titolo": titolo_breve(e["titolo"]), "percentuale": round(100 * ottenuti / (mx * len(ok)))})
    for r in richieste_piatte(struttura):
        if r["punti_max"] <= 0:
            continue
        ottenuti = sum(x["punti"] for a in ok for x in a["righe"] if x["id"] == r["id"])
        richieste.append({"id": r["id"], "esercizio": r["esercizio"], "percentuale": round(100 * ottenuti / (r["punti_max"] * len(ok)))})
    return {"n": len(ok), "voti": voti, "media": round(statistics.mean(voti), 2), "mediana": statistics.median(voti), "minimo": min(voti), "massimo": max(voti),
            "sufficienti": sum(1 for v in voti if v >= 6), "distribuzione": distribuzione,
            "esercizi": esercizi, "richieste": sorted(richieste, key=lambda x: x["percentuale"])[:5]}


def da_ripassare(stat: dict, soglia: int = 60) -> list:
    """Gli esercizi in cui la classe ha ottenuto meno della soglia (percentuale dei punti), dal peggiore: [{"n", "titolo", "percentuale"}]."""
    return sorted([e for e in stat.get("esercizi", []) if e["percentuale"] < soglia], key=lambda e: e["percentuale"])


def indicazioni_recupero(stat: dict) -> str:
    """Il testo da dare alla creazione di una verifica di recupero: gli argomenti in cui la classe è andata peggio."""
    peggio = da_ripassare(stat)[:3] or sorted(stat.get("esercizi", []), key=lambda e: e["percentuale"])[:2]
    if not peggio:
        return ""
    return "Verifica di recupero sugli argomenti in cui la classe è andata peggio: " + "; ".join(f"{e['titolo']} ({e['percentuale']}% dei punti)" for e in peggio) + "."


def da_controllare(alunno: dict) -> int:
    """Quante valutazioni dell'alunno sono dubbie (o il compito intero non si è letto)."""
    if alunno.get("errore") or alunno.get("non_corrisponde"):
        return 1
    return sum(1 for r in alunno.get("righe", []) if r.get("da_controllare") and not r.get("rivista"))


# ── Documenti ─────────────────────────────────────────────────────────────────
_SPECIALI = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}


def latex_escape(t) -> str:
    """Testo normale reso sicuro per LaTeX (i commenti dell'AI e i nomi sono input non fidato)."""
    return "".join(_SPECIALI.get(c, c) for c in str(t or "")).replace("\n", " ")


_PREAMBOLO = ("\\documentclass[11pt,a4paper]{article}\n\\usepackage[utf8]{inputenc}\n\\usepackage[italian]{babel}\n\\usepackage{amsmath,geometry,longtable}\n"
              "\\geometry{margin=2cm}\n\\pagestyle{empty}\n\\setlength{\\parindent}{0pt}\n")


def scheda_latex(materia: str, titolo: str, alunno: dict, scala: str = SCALA_PREDEFINITA) -> str:
    """La scheda di correzione di UN alunno (una pagina): voto, punti, commento di ogni richiesta e in sintesi."""
    p, m = punti_alunno(alunno["righe"])
    v = voto(p, m, scala)
    corpo = []
    for r in alunno["righe"]:
        com = latex_escape(r.get("commento")) or ("Corretto." if r["punti"] >= r["punti_max"] else "")
        corpo.append(f"{latex_escape(str(r['id']))} & {r['punti']:g}/{r['punti_max']:g} & {com} \\\\")
    sintesi = f"\\vspace{{1em}}\\textbf{{In sintesi.}} {latex_escape(alunno.get('commento_generale'))}\n" if alunno.get("commento_generale") else ""
    return (_PREAMBOLO + "\\begin{document}\n"
            f"\\begin{{center}}{{\\LARGE\\textbf{{Scheda di correzione}}}}\\\\[4pt]{{\\large {latex_escape(materia)} -- {latex_escape(titolo)}}}\\end{{center}}\n\\vspace{{.6em}}\n"
            f"\\textbf{{Studente:}} {latex_escape(alunno.get('nome') or '')}\n\n\\vspace{{.8em}}\n"
            f"\\begin{{center}}{{\\Huge\\textbf{{Voto {voto_testo(v)}}}}}\\quad{{\\large ({p:g} punti su {m:g})}}\\end{{center}}\n\\vspace{{.8em}}\n"
            "\\begin{longtable}{p{1.6cm} p{2cm} p{12cm}}\n\\textbf{Richiesta} & \\textbf{Punti} & \\textbf{Commento} \\\\ \\hline\n\\endhead\n"
            + "\n".join(corpo) + "\n\\end{longtable}\n" + sintesi +
            "\\vfill{\\footnotesize\\textit{Correzione proposta con VerificAI e rivista dal docente.}}\n\\end{document}\n")


def report_latex(materia: str, titolo: str, alunni: list, struttura: dict, scala: str = SCALA_PREDEFINITA) -> str:
    """Il resoconto della classe: numeri, distribuzione dei voti, voti degli alunni e argomenti da ripassare."""
    st = statistiche(alunni, struttura, scala)
    if not st["n"]:
        return ""
    barre = "\n\n".join(f"\\texttt{{{k:>3}}}\\ \\rule{{{max(0.1, v * 0.5):g}cm}}{{3mm}}\\ {v}" for k, v in st["distribuzione"].items())
    righe = "\n".join(
        f"{latex_escape(a.get('nome') or '—')} & {voto_testo(voto(*punti_alunno(a['righe']), scala))} & {punti_alunno(a['righe'])[0]:g}/{punti_alunno(a['righe'])[1]:g} \\\\"
        for a in sorted([a for a in alunni if valido(a)], key=lambda a: (a.get("nome") or "~").lower()))
    ripassare = da_ripassare(st)
    elenco = ("\\begin{itemize}\n" + "\n".join(f"\\item {latex_escape(e['titolo'])}: {e['percentuale']}\\% dei punti" for e in ripassare) + "\n\\end{itemize}") if ripassare \
        else "Nessun esercizio sotto il 60\\% dei punti: la classe ha ottenuto buoni risultati su tutta la verifica."
    return (_PREAMBOLO + "\\begin{document}\n"
            f"\\begin{{center}}{{\\LARGE\\textbf{{Resoconto della classe}}}}\\\\[4pt]{{\\large {latex_escape(materia)} -- {latex_escape(titolo)}}}\\end{{center}}\n\\vspace{{.8em}}\n"
            f"Compiti corretti: \\textbf{{{st['n']}}}. Media \\textbf{{{voto_testo(st['media'])}}}, mediana \\textbf{{{voto_testo(st['mediana'])}}}, "
            f"da \\textbf{{{voto_testo(st['minimo'])}}} a \\textbf{{{voto_testo(st['massimo'])}}}. Sufficienti: \\textbf{{{st['sufficienti']}}} su {st['n']}.\n\n"
            f"\\vspace{{1em}}\\textbf{{Distribuzione dei voti}}\n\n{barre}\n\n\\vspace{{1em}}\\textbf{{Argomenti da ripassare}}\n\n{elenco}\n\n\\vspace{{1em}}\n"
            "\\begin{longtable}{p{9cm} p{2cm} p{3cm}}\n\\textbf{Studente} & \\textbf{Voto} & \\textbf{Punti} \\\\ \\hline\n\\endhead\n" + righe + "\n\\end{longtable}\n"
            "\\vfill{\\footnotesize\\textit{Documento riservato al docente.}}\n\\end{document}\n")


def _csv_sicuro(t: str) -> str:
    """Un nome che comincia con =, +, - o @ verrebbe letto da Excel come formula."""
    return "'" + t if t[:1] in ("=", "+", "-", "@") else t


def csv_risultati(alunni: list, struttura: dict, scala: str = SCALA_PREDEFINITA) -> str:
    """I voti in CSV (separatore «;», adatto a Excel in italiano): studente, voto, punti e i punti di ogni richiesta."""
    ids = [r["id"] for r in richieste_piatte(struttura)]
    out = io.StringIO()
    w = csv.writer(out, delimiter=";", lineterminator="\n")
    w.writerow(["Studente", "Voto", "Punti", "Massimo"] + [f"Richiesta {i}" for i in ids])
    for a in alunni:
        if not valido(a):
            continue
        p, m = punti_alunno(a["righe"])
        per_id = {r["id"]: r["punti"] for r in a["righe"]}
        w.writerow([_csv_sicuro(a.get("nome") or ""), voto_testo(voto(p, m, scala)), f"{p:g}".replace(".", ","), f"{m:g}"] + [f"{per_id.get(i, 0):g}".replace(".", ",") for i in ids])
    return out.getvalue()
