"""
correzione.py — la correzione assistita dei compiti dalle foto (senza Streamlit).

Il docente sceglie la verifica (una delle sue, oppure la traccia da foto) e carica i compiti degli alunni: per ogni alunno una o PIÙ foto/pagine, con il nome.
LA CORREZIONE È IN DUE PASSI SEPARATI. 1) LEGGERE: un modello trascrive riga per riga ciò che lo studente ha scritto, senza valutare e senza vedere le
soluzioni (così non «vede» ciò che dovrebbe esserci), segnando con [?] ciò che non legge con certezza e indicando dove sta ogni riga sulla pagina; un SECONDO
lettore (modello diverso, economico) rilegge le stesse pagine e dove le due letture non coincidono (tipicamente un + o un - perso) la richiesta è «da controllare».
2) VALUTARE: dalla trascrizione (solo testo) si confrontano le soluzioni e si propongono punti, esito, commento e la riga dell'errore. Così il docente vede
«cosa ho letto» e il pezzo di compito con l'errore, può correggere la lettura e rivalutare quella richiesta.
Il docente controlla (le valutazioni dubbie sono segnalate), corregge i punti e ottiene voti, schede per gli alunni, un resoconto della classe e gli argomenti
da ripassare.

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
from prompts import prompt_leggi_compito, prompt_soluzioni, prompt_valuta_lettura

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


LATO_PAGINA = 1900               # lato lungo massimo delle pagine mandate ai modelli (oltre non servono: vengono ridotte)


def pagine_compito(compito: list) -> list:
    """Le pagine di un compito (foto o PDF) come immagini JPEG pronte per i modelli: orientate come nell'EXIF, RGB, ridotte a LATO_PAGINA e con il
    contrasto un po' ripreso (una foto col telefono ha spesso ombre e carta grigia). Restituisce una lista di bytes; le pagine illeggibili si saltano."""
    from PIL import Image, ImageOps
    from docx_import import espandi_file
    out = []
    for f in espandi_file(compito):
        dati = f.get("data") or b""
        if not dati:
            continue
        pezzi = [dati]
        if (f.get("mime_type") or "").startswith("application/pdf"):
            try:
                from latex_utils import pdf_to_images_bytes
                pezzi = (pdf_to_images_bytes(dati)[0] or [])[:MAX_PAGINE_COMPITO]
            except Exception:
                pezzi = []
        for b in pezzi:
            try:
                im = Image.open(io.BytesIO(b))
                im.load()
                im = ImageOps.exif_transpose(im).convert("RGB")
                if max(im.size) > LATO_PAGINA:
                    k = LATO_PAGINA / max(im.size)
                    im = im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))), Image.LANCZOS)
                im = ImageOps.autocontrast(im, cutoff=1)
                buf = io.BytesIO()
                im.save(buf, "JPEG", quality=90)
                out.append(buf.getvalue())
            except Exception:
                continue
    return out


def _riquadro(v):
    """[x0, y0, x1, y1] in millesimi, controllato; None se non è un riquadro sensato."""
    try:
        x0, y0, x1, y1 = [int(round(float(x))) for x in v]
    except (TypeError, ValueError):
        return None
    x0, x1 = sorted((max(0, min(1000, x0)), max(0, min(1000, x1))))
    y0, y1 = sorted((max(0, min(1000, y0)), max(0, min(1000, y1))))
    return [x0, y0, x1, y1] if (x1 - x0 >= 20 and y1 - y0 >= 8) else None


def normalizza_lettura(grezzo, struttura: dict, n_pagine: int) -> dict:
    """La trascrizione dell'AI riportata alla struttura vera: una voce per OGNI richiesta, righe pulite, pagine e riquadri controllati."""
    g = grezzo if isinstance(grezzo, dict) else {}
    per_id = {}
    for r in (g.get("richieste") if isinstance(g.get("richieste"), list) else []):
        if isinstance(r, dict) and r.get("id") is not None:
            per_id[str(r["id"]).strip().lower()] = r
    richieste = {}
    for r in richieste_piatte(struttura):
        v = per_id.get(r["id"].lower())
        if v is None:
            richieste[r["id"]] = {"trovata": False, "vuoto": False, "righe": []}
            continue
        righe = []
        for x in (v.get("righe") if isinstance(v.get("righe"), list) else []):
            if not isinstance(x, dict):
                continue
            testo = _testo(x.get("testo"), 400)
            if not testo:
                continue
            try:
                pag = int(x.get("pagina") or 1)
            except (TypeError, ValueError):
                pag = 1
            righe.append({"pagina": min(max(1, pag), max(1, n_pagine)), "riquadro": _riquadro(x.get("riquadro")), "testo": testo,
                          "dubbio": _testo(x.get("dubbio"), 120)})
        richieste[r["id"]] = {"trovata": True, "vuoto": v.get("vuoto") is True and not righe, "righe": righe[:30]}
    return {"nome": _testo(g.get("nome"), 40), "non_corrisponde": g.get("non_corrisponde") is True, "richieste": richieste}


def _chiama_json(model, contenuto, chiave: str):
    """Chiama il modello (due tentativi) e restituisce il JSON letto, oppure (None, motivo)."""
    ultimo = "risposta non valida"
    for _ in range(2):
        try:
            risposta = ef._chiama(model, contenuto)
        except Exception as e:
            ultimo = str(e)[:140]
            continue
        grezzo = _estrai_json(risposta)
        if isinstance(grezzo, dict) and isinstance(grezzo.get(chiave), list):
            return grezzo, ""
    return None, ultimo


def leggi_compito(model, struttura: dict, pagine: list, materia: str = "", scuola: str = "") -> dict:
    """PRIMO PASSO: trascrive il compito (pagine = JPEG già preparate). Restituisce {"ok", "lettura" | "messaggio"}; non solleva mai."""
    if not pagine:
        return {"ok": False, "messaggio": "Non riesco ad aprire le pagine di questo compito: prova con foto JPG o PNG, oppure un PDF."}
    prompt = prompt_leggi_compito(materia, scuola, traccia_testo(struttura), len(pagine))
    grezzo, motivo = _chiama_json(model, [prompt] + [{"mime_type": "image/jpeg", "data": p} for p in pagine], "richieste")
    if grezzo is None:
        return {"ok": False, "messaggio": f"Non sono riuscito a leggere questo compito ({motivo}). Prova con una foto più nitida."}
    return {"ok": True, "lettura": normalizza_lettura(grezzo, struttura, len(pagine))}


def _chiave_lettura(righe: list) -> str:
    """Le righe di una richiesta ridotte a una forma confrontabile: stessi caratteri, senza spazi né differenze tra i vari «meno»."""
    t = " ".join(r["testo"] for r in righe)
    t = t.replace("−", "-").replace("–", "-").replace("—", "-").replace("×", "*").replace("·", "*").replace("÷", "/").replace("[?]", "")
    return re.sub(r"\s+", "", t).lower()


def confronta_letture(prima: dict, seconda: dict) -> dict:
    """{id: righe della seconda lettura} per le richieste in cui le due letture NON coincidono (un segno o una cifra diversi); le altre non compaiono.
    Una differenza di sole spaziature o di simboli equivalenti non conta."""
    diverse = {}
    for rid, a in (prima.get("richieste") or {}).items():
        b = (seconda.get("richieste") or {}).get(rid) or {}
        if not a.get("righe") and not b.get("righe"):
            continue
        if _chiave_lettura(a.get("righe") or []) != _chiave_lettura(b.get("righe") or []):
            diverse[rid] = b.get("righe") or []
    return diverse


def testo_letture(lettura: dict, struttura: dict) -> str:
    """La trascrizione come testo per il passo di valutazione: per ogni richiesta le righe numerate (1., 2., …)."""
    blocchi = []
    for r in richieste_piatte(struttura):
        v = (lettura.get("richieste") or {}).get(r["id"]) or {}
        if v.get("righe"):
            corpo = "\n".join(f"{k}. {x['testo']}" + (f"   (dubbio: {x['dubbio']})" if x.get("dubbio") else "") for k, x in enumerate(v["righe"], 1))
        elif v.get("vuoto") or not v.get("trovata", True):
            corpo = "(vuota: nessuna risposta scritta)"
        else:
            corpo = "(vuota: nessuna risposta scritta)"
        blocchi.append(f"[{r['id']}]\n{corpo}")
    return "\n\n".join(blocchi)


def normalizza_correzione(grezzo, struttura: dict, lettura: dict | None = None, diverse: dict | None = None) -> dict:
    """La valutazione dell'AI riportata alla struttura vera: una riga per OGNI richiesta, punti nei limiti, esiti validi; ogni riga porta anche ciò che è stato
    letto, la riga dell'errore e, se le due letture non coincidono, la lettura alternativa. Ciò che manca resta «da controllare»."""
    g = grezzo if isinstance(grezzo, dict) else {}
    lettura = lettura or {}
    diverse = diverse or {}
    per_id = {}
    for r in (g.get("righe") if isinstance(g.get("righe"), list) else []):
        if isinstance(r, dict) and r.get("id") is not None:
            per_id[str(r["id"]).strip().lower()] = r
    righe = []
    for r in richieste_piatte(struttura):
        v = per_id.get(r["id"].lower())
        letta = (lettura.get("richieste") or {}).get(r["id"]) or {}
        base = {**r, "lettura": letta.get("righe") or [], "lettura_alt": diverse.get(r["id"]), "riga_errore": None, "errore": ""}
        if v is None:
            righe.append({**base, "punti": 0.0, "esito": "vuoto", "commento": "Non l'ho trovata nel compito: controlla.", "confidenza": 0.0, "da_controllare": True})
            continue
        esito = str(v.get("esito") or "").strip().lower()
        esito = esito if esito in ESITI else "parziale"
        try:
            conf = max(0.0, min(1.0, float(v.get("confidenza", 0.7))))
        except (TypeError, ValueError):
            conf = 0.7
        try:
            k = int(v.get("riga_errore")) if v.get("riga_errore") is not None else None
        except (TypeError, ValueError):
            k = None
        k = k if (k is not None and 1 <= k <= len(base["lettura"])) else None
        dubbi = any("[?]" in x["testo"] or x.get("dubbio") for x in base["lettura"])
        diversa = base["lettura_alt"] is not None
        da_ctrl = conf < SOGLIA_CONFIDENZA or esito == "illeggibile" or diversa or (dubbi and esito not in ("corretto", "vuoto"))
        righe.append({**base, "punti": _passo(_numero(v.get("punti")), r["punti_max"]), "esito": esito, "commento": _testo(v.get("commento"), 140),
                      "riga_errore": k, "errore": _testo(v.get("errore"), 140) if esito not in ("corretto", "vuoto") else "",
                      "confidenza": conf, "da_controllare": da_ctrl, "lettura_incerta": dubbi, "letture_diverse": diversa})
    return {"nome": _testo(lettura.get("nome"), 40), "non_corrisponde": lettura.get("non_corrisponde") is True, "righe": righe,
            "commento_generale": _testo(g.get("commento_generale"), 280)}


def valuta_lettura(model, struttura: dict, soluzioni: str, lettura: dict, materia: str = "", scuola: str = "", diverse: dict | None = None) -> dict:
    """SECONDO PASSO: valuta la trascrizione (solo testo). Restituisce {"ok", "correzione" | "messaggio"}; non solleva mai."""
    prompt = prompt_valuta_lettura(materia, scuola, traccia_testo(struttura), soluzioni, testo_letture(lettura, struttura))
    grezzo, motivo = _chiama_json(model, prompt, "righe")
    if grezzo is None:
        return {"ok": False, "messaggio": f"Non sono riuscito a valutare questo compito ({motivo}). Riprova."}
    return {"ok": True, "correzione": normalizza_correzione(grezzo, struttura, lettura, diverse)}


def correggi_compito(modelli: dict, struttura: dict, soluzioni: str, compito: list, materia: str = "", scuola: str = "", pagine: list | None = None) -> dict:
    """Corregge il compito di un alunno in due passi. `modelli` = {"lettura", "lettura2" (facoltativo), "valutazione"}; `compito` = file {"data", "mime_type", "name"}
    (una o più foto o un PDF). Restituisce {"ok", "correzione", "pagine" (JPEG usate) | "messaggio"}; non solleva mai."""
    errore = ef.controlla_foto(compito, MAX_PAGINE_COMPITO)
    if errore:
        return {"ok": False, "messaggio": errore}
    pagine = pagine or pagine_compito(compito)
    if len(pagine) > MAX_PAGINE_COMPITO:
        return {"ok": False, "messaggio": f"Questo compito ha {len(pagine)} pagine: al massimo {MAX_PAGINE_COMPITO} per alunno."}
    prima = leggi_compito(modelli["lettura"], struttura, pagine, materia, scuola)
    if not prima["ok"]:
        return prima
    diverse = {}
    if modelli.get("lettura2") is not None:
        seconda = leggi_compito(modelli["lettura2"], struttura, pagine, materia, scuola)
        if seconda["ok"]:
            diverse = confronta_letture(prima["lettura"], seconda["lettura"])
    ris = valuta_lettura(modelli["valutazione"], struttura, soluzioni, prima["lettura"], materia, scuola, diverse)
    if ris["ok"]:
        ris["pagine"] = pagine
        ris["lettura"] = prima["lettura"]
    return ris


def rivaluta_richiesta(model, struttura: dict, soluzioni: str, riga: dict, testi: list, materia: str = "", scuola: str = "") -> dict:
    """Rivaluta UNA richiesta dopo che il docente ha corretto la lettura. `testi` = le righe lette (una per riga). Restituisce {"ok", "riga" | "messaggio"}."""
    righe = [{"pagina": 1, "riquadro": None, "testo": t.strip(), "dubbio": ""} for t in testi if t and t.strip()]
    mini = {"nome": "", "non_corrisponde": False, "richieste": {riga["id"]: {"trovata": True, "vuoto": not righe, "righe": righe}}}
    sotto = {"esercizi": [{**e, "richieste": [r for r in e["richieste"] if r["id"] == riga["id"]]} for e in struttura.get("esercizi", [])
                           if any(r["id"] == riga["id"] for r in e["richieste"])]}
    ris = valuta_lettura(model, sotto, soluzioni, mini, materia, scuola)
    if not ris["ok"]:
        return ris
    nuova = next((r for r in ris["correzione"]["righe"] if r["id"] == riga["id"]), None)
    return {"ok": True, "riga": nuova} if nuova else {"ok": False, "messaggio": "Non sono riuscito a rivalutare questa richiesta."}


def correggi_tutti(modelli: dict, struttura: dict, soluzioni: str, compiti: list, materia: str = "", scuola: str = "", on_fatto=None, paralleli: int = 3) -> list:
    """Corregge più compiti insieme (poche chiamate in parallelo). `compiti` = [file di ciascun alunno]. Restituisce i risultati nello stesso ordine.
    `on_fatto(n_fatti, totale)` è chiamata dal thread di chi invoca (si può usare per aggiornare una barra)."""
    risultati = [None] * len(compiti)
    if not compiti:
        return risultati
    with ThreadPoolExecutor(max_workers=max(1, min(paralleli, len(compiti)))) as pool:
        futuri = {pool.submit(correggi_compito, modelli, struttura, soluzioni, c, materia, scuola): i for i, c in enumerate(compiti)}
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


def ritaglio_righe(pagine: list, righe: list, margine: int = 14):
    """Il pezzo di compito che contiene le `righe` date (stessa pagina), come PNG leggero; None se non si può ritagliare. Il riquadro si allarga un po'
    (`margine` millesimi) perché il modello non sia troppo stretto."""
    usabili = [r for r in righe if r.get("riquadro")]
    if not usabili:
        return None
    pag = usabili[0]["pagina"]
    usabili = [r for r in usabili if r["pagina"] == pag]
    if not (1 <= pag <= len(pagine)):
        return None
    x0 = max(0, min(r["riquadro"][0] for r in usabili) - margine)
    y0 = max(0, min(r["riquadro"][1] for r in usabili) - margine)
    x1 = min(1000, max(r["riquadro"][2] for r in usabili) + margine)
    y1 = min(1000, max(r["riquadro"][3] for r in usabili) + margine)
    return ef.ritaglia(pagine[pag - 1], x0, y0, x1, y1, lato_max=1400, peso_max=220_000)


def ritaglio_errore(pagine: list, riga: dict):
    """Il pezzo di compito con l'ERRORE di una richiesta: la riga indicata e quella prima (per capire da dove viene); se non c'è la riga, tutta la risposta."""
    k = riga.get("riga_errore")
    lettura = riga.get("lettura") or []
    if k and 1 <= k <= len(lettura):
        scelte = [lettura[k - 1]] + ([lettura[k - 2]] if k >= 2 else [])
        png = ritaglio_righe(pagine, scelte)
        if png:
            return png
    return ritaglio_righe(pagine, lettura)


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


def scheda_latex(materia: str, titolo: str, alunno: dict, scala: str = SCALA_PREDEFINITA, ritagli: dict | None = None) -> str:
    """La scheda di correzione di UN alunno: voto, punti, commento di ogni richiesta e in sintesi; con `ritagli` ({id richiesta: PNG}) anche il pezzo di
    compito dove sta ogni errore (le figure viaggiano nel LaTeX come il logo: vedi latex_utils.blocco_figura)."""
    p, m = punti_alunno(alunno["righe"])
    v = voto(p, m, scala)
    corpo = []
    for r in alunno["righe"]:
        com = latex_escape(r.get("commento")) or ("Corretto." if r["punti"] >= r["punti_max"] else "")
        corpo.append(f"{latex_escape(str(r['id']))} & {r['punti']:g}/{r['punti_max']:g} & {com} \\\\")
    sintesi = f"\\vspace{{1em}}\\textbf{{In sintesi.}} {latex_escape(alunno.get('commento_generale'))}\n" if alunno.get("commento_generale") else ""
    dove = []
    if ritagli:
        from latex_utils import blocco_figura
        for r in alunno["righe"]:
            png = ritagli.get(r["id"])
            if png:
                dove.append(f"\\textbf{{{latex_escape(str(r['id']))}}}" + (f" -- {latex_escape(r['errore'])}" if r.get("errore") else "") + "\n\n" + blocco_figura(png, 12.0) + "\n")
    if dove:
        sintesi += "\\vspace{1em}\\textbf{Dove sono gli errori}\n\n" + "\n".join(dove)
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
