"""
importa_esercizi.py — legge schede, verifiche e appunti (PDF o LaTeX) e ne ricava gli esercizi catalogati.

Non tocca il sito né il database: per ogni file produce un JSON e una pagina HTML da rivedere.

    python importa_esercizi.py materiale/scheda.pdf
    python importa_esercizi.py materiale/verifica.tex
    python importa_esercizi.py materiale                  # tutti i .tex e .pdf della cartella
    python importa_esercizi.py materiale --senza-ai       # solo lettura del codice, niente AI

Come legge i file:
  • .tex di VERIFICA o SCHEDA: il codice è letto da un programma (testo, formule, punti e facoltativi
    esatti); l'AI serve solo a etichettare (argomento, tecniche, difficoltà).
  • .tex di APPUNTI e .pdf: li legge l'AI (a blocchi).
I file restano sul tuo computer (la cartella materiale/ è ignorata da git). Usa GOOGLE_API_KEY del .env.
"""
import argparse
import glob
import html
import json
import os
import re
import sys
import time

from dotenv import load_dotenv

load_dotenv()

for _flusso in (sys.stdout, sys.stderr):          # la console di Windows non stampa tutti i simboli
    try:
        _flusso.reconfigure(encoding="utf-8")
    except Exception:
        pass

import ai_client                                  # noqa: E402
from config import MODEL_FLASH_ID, livello_normalizzato  # noqa: E402
from estrai_tex import corpo_documento, leggi_tex, togli_commenti  # noqa: E402
from prompts import prompt_etichetta_esercizi, prompt_importa_esercizi  # noqa: E402


# ── chiamate all'AI ───────────────────────────────────────────────────────────

def leggi_json(testo: str) -> dict:
    testo = re.sub(r"^```(?:json)?|```$", "", (testo or "").strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(testo)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", testo, re.DOTALL)
        return json.loads(m.group(0)) if m else {}


def chiedi_json(modello, contenuto: list, tentativi: int = 2):
    ultimo = None
    for t in range(tentativi):
        try:
            r = modello.generate_content(contenuto, generation_config={"json": True, "temperature": 0.1})
            return leggi_json(r.text)
        except Exception as e:                    # noqa: BLE001
            ultimo = e
            if ai_client.errore_definitivo(e):
                break
            time.sleep(2 * (t + 1))
    print(f"   ⚠️  chiamata AI non riuscita: {str(ultimo)[:200]}")
    return None


# ── PDF: a blocchi di pagine ──────────────────────────────────────────────────

def blocchi_di_pagine(percorso: str, per_blocco: int):
    import fitz                                   # PyMuPDF, già nelle dipendenze
    doc = fitz.open(percorso)
    for inizio in range(0, len(doc), per_blocco):
        fine = min(inizio + per_blocco, len(doc)) - 1
        parte = fitz.open()
        parte.insert_pdf(doc, from_page=inizio, to_page=fine)
        yield inizio + 1, parte.tobytes()


def esercizi_da_pdf(modello, materia: str, percorso: str, pagine: int) -> list:
    tutti = []
    for prima, dati in blocchi_di_pagine(percorso, pagine):
        print(f"   pagine da {prima}…")
        r = chiedi_json(modello, [prompt_importa_esercizi(materia), {"mime_type": "application/pdf", "data": dati}])
        for e in (r or {}).get("esercizi", []):
            e["pagina"] = prima + int(e.get("pagina_nel_blocco") or 1) - 1
            tutti.append(e)
    return tutti


# ── LaTeX: appunti letti dall'AI sul sorgente ─────────────────────────────────

def blocchi_di_sorgente(tex: str, massimo: int = 12000) -> list:
    """Spezza il corpo del documento su \\section/\\subsection in blocchi di dimensione ragionevole."""
    corpo = corpo_documento(togli_commenti(tex))
    pezzi = [p for p in re.split(r"(?=\\section)", corpo) if p.strip()]
    blocchi, corrente = [], ""
    for p in pezzi:
        sotto = re.split(r"(?=\\subsection)", p) if len(p) > massimo else [p]
        for q in sotto:
            while len(q) > massimo:                       # ultima risorsa: taglio a righe vuote
                taglio = q.rfind("\n\n", 0, massimo) or massimo
                blocchi.append(q[:taglio]); q = q[taglio:]
            if len(corrente) + len(q) > massimo and corrente:
                blocchi.append(corrente); corrente = ""
            corrente += q
    if corrente.strip():
        blocchi.append(corrente)
    return blocchi


def esercizi_da_appunti(modello, materia: str, tex: str) -> list:
    tutti = []
    for i, blocco in enumerate(blocchi_di_sorgente(tex), 1):
        print(f"   blocco {i}…")
        r = chiedi_json(modello, [prompt_importa_esercizi(materia, da_latex=True) + "\n\nCODICE LATEX:\n" + blocco])
        for e in (r or {}).get("esercizi", []):
            e["pagina"] = i
            tutti.append(e)
    return tutti


# ── LaTeX: verifiche e schede lette dal codice ────────────────────────────────

def esercizi_da_verifica(d: dict):
    esercizi, sezioni_mod = [], []
    for si, s in enumerate(d["sezioni"], 1):
        punti = [q.get("punti") for q in s["quesiti"]]
        sezioni_mod.append({
            "nome": s["nome"], "tipo": s["tipo"], "consegna": s["consegna"], "n_quesiti": len(s["quesiti"]),
            "punti": punti, "facoltativi": [q["etichetta"] for q in s["quesiti"] if q["facoltativo"]],
            "etichette": [q["etichetta"] for q in s["quesiti"]],
            "opzioni_per_quesito": max([len(q["opzioni"]) for q in s["quesiti"]] or [0]),
        })
        for q in s["quesiti"]:
            esercizi.append({
                "numero": f"{si}.{q['etichetta']}", "pagina": None, "ruolo": "esercizio",
                "testo_latex": q["testo_latex"], "opzioni": q["opzioni"], "soluzione_latex": None,
                "punti": q.get("punti"), "facoltativo": q["facoltativo"], "sezione": s["nome"],
                "consegna_sezione": s["consegna"], "posizione": si,
                "tipo": "scelta_multipla" if q["opzioni"] else None,
            })
    modello = {
        "titolo": d["titolo"], "argomento": d["argomento_titolo"], "istruzioni": d["istruzioni"],
        "sezioni": sezioni_mod, "punti_base": d["punti_base"], "punti_extra": d["punti_extra"],
        "totale": d["totale"], "base_pdp_dsa": d["base_pdp_dsa"], "stile": d["stile"],
        "punti_letti": d["punti_letti"],
    }
    return esercizi, modello


def esercizi_da_scheda(d: dict) -> list:
    return [{**e, "pagina": None, "ruolo": "esercizio", "opzioni": [], "soluzione_latex": None}
            for e in d["esercizi"]]


def etichetta_con_ai(modello, materia: str, titolo: str, esercizi: list):
    """Argomento, tecniche, difficoltà e tipo per esercizi già estratti dal codice (a gruppi di 40)."""
    for inizio in range(0, len(esercizi), 40):
        gruppo = esercizi[inizio:inizio + 40]
        elenco = [{"id": i, "testo": (e["testo_latex"] + (" | opzioni: " + " ; ".join(e["opzioni"]) if e.get("opzioni") else ""))[:600]}
                  for i, e in enumerate(gruppo)]
        r = chiedi_json(modello, [prompt_etichetta_esercizi(materia, titolo, json.dumps(elenco, ensure_ascii=False))])
        for et in (r or {}).get("etichette", []):
            try:
                e = gruppo[int(et["id"])]
            except (KeyError, ValueError, IndexError, TypeError):
                continue
            for k in ("argomento", "tecniche", "difficolta_stimata", "ha_figura"):
                if k in et:
                    e[k] = et[k]
            if not e.get("tipo") and et.get("tipo"):
                e["tipo"] = et["tipo"]


# ── normalizzazione e pagina di controllo ─────────────────────────────────────

def normalizza(esercizi: list) -> list:
    """Porta tutte le difficoltà su 1-3 (★) mantenendo il livello originale."""
    for e in esercizi:
        L = e.get("livelli_totali")
        if isinstance(e.get("livello_numero"), int) and isinstance(L, int) and L > 0:
            e["difficolta"] = livello_normalizzato(e["livello_numero"], L)
            e["difficolta_origine"] = f"livello {e['livello_numero']} di {L}"
        elif e.get("difficolta_stimata"):
            e["difficolta"] = max(1, min(3, int(e["difficolta_stimata"])))
            e["difficolta_origine"] = "stimata dall'AI"
        else:
            e["difficolta"] = 2
            e["difficolta_origine"] = "non stimata"
    return esercizi


def _h(x) -> str:
    return html.escape(str(x if x is not None else ""))


def pagina_html(titolo: str, esercizi: list, modello: dict | None) -> str:
    struttura = ""
    if modello:
        righe = "".join(
            f"<tr><td>{_h(s['nome'])}</td><td>{_h(s['tipo'])}</td><td>{s['n_quesiti']}</td>"
            f"<td>{_h(' · '.join(str(p) if p is not None else '—' for p in s['punti']))}</td>"
            f"<td>{_h(', '.join(s['facoltativi']) or '—')}</td></tr>" for s in modello["sezioni"])
        struttura = (
            f"<h2>Struttura della verifica</h2><p>{_h(modello['titolo'])} — <b>{_h(modello['argomento'])}</b><br>"
            f"Punti base <b>{modello['punti_base']}</b> + facoltativi <b>{modello['punti_extra']}</b> = "
            f"<b>{modello['totale']}</b>"
            + (f" · base PDP/DSA indicata: {modello['base_pdp_dsa']}" if modello.get("base_pdp_dsa") else "")
            + ("" if modello["punti_letti"] else " · <span style='color:#b42318'>punti non letti dalla tabella</span>")
            + f"<br>Stile: {_h(modello['stile'])}</p>"
            "<table><tr><th>Sezione</th><th>Tipo</th><th>Quesiti</th><th>Punti</th><th>Facoltativi</th></tr>"
            + righe + "</table><h2>Esercizi</h2>")
    righe = []
    for e in esercizi:
        opz = ""
        if e.get("opzioni"):
            opz = "<ul>" + "".join(f"<li>{_h(o)}</li>" for o in e["opzioni"]) + "</ul>"
        sol = f"<div class='sol'>Soluzione: {_h(e['soluzione_latex'])}</div>" if e.get("soluzione_latex") else ""
        flag = " ".join(x for x in (
            "<b>(*) facoltativo</b>" if e.get("facoltativo") else "",
            f"{e['punti']} pt" if e.get("punti") is not None else "",
            "⚠️ figura" if e.get("ha_figura") else "",
            "esempio svolto" if e.get("ruolo") == "esempio_svolto" else "") if x)
        pos = e.get("sezione") or e.get("titolo_sezione") or ""
        riga_pagina = f"p. {e['pagina']}" if e.get("pagina") is not None else ""
        righe.append(
            f"<tr><td>{_h(e.get('numero'))}<br><small>{_h(pos)} {riga_pagina}</small></td>"
            f"<td class='st{e['difficolta']}'>{'★' * e['difficolta']}<br><small>{_h(e['difficolta_origine'])}</small></td>"
            f"<td>{_h(e.get('testo_latex', '')).replace(chr(10), '<br>')}{opz}{sol}</td>"
            f"<td>{_h(e.get('argomento'))}<br><small>{_h(', '.join(e.get('tecniche') or []))}</small></td>"
            f"<td>{_h(e.get('tipo'))}<br><small>{flag}</small></td></tr>")
    return (
        "<!doctype html><meta charset='utf-8'><title>" + _h(titolo) + "</title>"
        "<link rel='stylesheet' href='https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css'>"
        "<script defer src='https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js'></script>"
        "<script defer src='https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js' "
        "onload=\"renderMathInElement(document.body,{delimiters:[{left:'$$',right:'$$',display:true},"
        "{left:'$',right:'$',display:false},{left:'\\\\(',right:'\\\\)',display:false}],throwOnError:false})\"></script>"
        "<style>body{font-family:system-ui,sans-serif;margin:1.5rem}table{border-collapse:collapse;width:100%}"
        "td,th{border:1px solid #d0d5dd;padding:.45rem .6rem;vertical-align:top;font-size:.92rem}"
        "th{background:#f2f4f7;text-align:left}small{color:#667085}.st1{background:#ecfdf3}.st2{background:#fffaeb}"
        ".st3{background:#fef3f2}.sol{margin-top:.4rem;color:#344054}li{list-style:none}</style>"
        f"<h1>{_h(titolo)}</h1>{struttura}<p>{len(esercizi)} esercizi. Controlla formule, livelli e tecniche.</p>"
        "<table><tr><th>N. / posizione</th><th>Livello</th><th>Esercizio</th><th>Argomento / tecniche</th>"
        "<th>Tipo / punti</th></tr>" + "".join(righe) + "</table>"
    )


# ── un file ───────────────────────────────────────────────────────────────────

def elabora_file(percorso: str, a, modello):
    nome = os.path.splitext(os.path.basename(percorso))[0]
    ext = os.path.splitext(percorso)[1].lower()
    print(f"\n▶ {os.path.basename(percorso)}")
    modello_verifica, tipo = None, ext.strip(".")
    esercizi, titolo = [], nome

    if ext == ".tex":
        tex = open(percorso, encoding="utf-8", errors="replace").read()
        d = leggi_tex(tex)
        tipo = d["tipo_file"]
        titolo = d.get("titolo") or nome
        if tipo == "verifica":
            esercizi, modello_verifica = esercizi_da_verifica(d)
        elif tipo == "scheda":
            esercizi = esercizi_da_scheda(d)
        else:                                                   # appunti
            if modello is None:
                print("   appunti: servono l'AI e la chiave nel .env (salto)")
                return None
            esercizi = esercizi_da_appunti(modello, a.materia, tex)
        print(f"   tipo: {tipo} | esercizi letti dal codice: {len(esercizi)}")
        if tipo in ("verifica", "scheda") and modello is not None and not a.senza_ai:
            etichetta_con_ai(modello, a.materia, titolo, esercizi)
    elif ext == ".pdf":
        if modello is None:
            print("   i PDF li legge l'AI: serve la chiave nel .env (salto)")
            return None
        esercizi = esercizi_da_pdf(modello, a.materia, percorso, a.pagine)
    else:
        print("   formato non supportato (uso .tex e .pdf)")
        return None

    esercizi = normalizza(esercizi)
    os.makedirs(a.uscita, exist_ok=True)
    base = os.path.join(a.uscita, nome)
    with open(base + ".json", "w", encoding="utf-8") as f:
        json.dump({"fonte": os.path.basename(percorso), "tipo_file": tipo, "titolo": titolo,
                   "modello_verifica": modello_verifica, "esercizi": esercizi}, f, ensure_ascii=False, indent=1)
    with open(base + ".html", "w", encoding="utf-8") as f:
        f.write(pagina_html(titolo, esercizi, modello_verifica))
    per = {k: sum(1 for e in esercizi if e["difficolta"] == k) for k in (1, 2, 3)}
    print(f"   → {len(esercizi)} esercizi | ★1: {per[1]}  ★2: {per[2]}  ★3: {per[3]} | {base}.html")
    return {"file": os.path.basename(percorso), "tipo": tipo, "esercizi": len(esercizi)}


def main():
    ap = argparse.ArgumentParser(description="Estrae e cataloga gli esercizi da PDF e LaTeX.")
    ap.add_argument("percorsi", nargs="+", help="file .tex/.pdf oppure cartelle (consiglio: materiale/)")
    ap.add_argument("--materia", default="", help="materia, se vuoi guidare la lettura")
    ap.add_argument("--pagine", type=int, default=4, help="pagine per chiamata all'AI per i PDF (default 4)")
    ap.add_argument("--senza-ai", action="store_true", help="solo lettura del codice: nessuna etichetta dell'AI")
    ap.add_argument("--uscita", default=os.path.join("materiale", "estratti"), help="cartella di uscita")
    a = ap.parse_args()

    file = []
    for p in a.percorsi:
        if os.path.isdir(p):
            file += sorted(glob.glob(os.path.join(p, "*.tex")) + glob.glob(os.path.join(p, "*.pdf")))
        elif os.path.isfile(p):
            file.append(p)
        else:
            sys.exit(f"Non trovato: {p}")

    modello = None
    if os.getenv("GOOGLE_API_KEY") and not a.senza_ai:
        ai_client.configura()
        modello = ai_client.crea_modello(MODEL_FLASH_ID).per("importazione")
        ai_client.azzera_uso()
    elif not a.senza_ai:
        print("⚠️  GOOGLE_API_KEY non trovata nel .env: leggo solo il codice delle verifiche e schede, senza etichette.")

    riepilogo = [r for r in (elabora_file(f, a, modello) for f in file) if r]
    uso = ai_client.riepilogo_uso()
    costo = sum(u["costo_usd"] for u in uso)
    print(f"\n{len(riepilogo)} file elaborati | {sum(r['esercizi'] for r in riepilogo)} esercizi | ~${costo:.3f} di AI")
    sost = ai_client.modelli_sostituiti()
    if sost:
        print("Modelli sostituiti perché ritirati:", sost)


if __name__ == "__main__":
    main()
