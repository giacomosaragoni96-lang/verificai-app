"""
banca_import.py — trasforma un file (LaTeX o PDF) in esercizi catalogati. Nessun import di streamlit.

Usato sia dalla pagina "Banca" dell'app sia dallo script importa_esercizi.py.

  • .tex di VERIFICA o SCHEDA: il codice è letto da un programma (estrai_tex.py): testo, formule, punti
    e facoltativi esatti. L'AI serve solo a etichettare (argomento, tecniche, difficoltà).
  • .tex di APPUNTI e .pdf: li legge l'AI, a blocchi.
"""
import hashlib
import json
import re
import time

import ai_client
from config import livello_normalizzato
from estrai_tex import corpo_documento, leggi_tex, togli_commenti
from prompts import prompt_etichetta_esercizi, prompt_importa_esercizi, prompt_tipo_livelli


def hash_contenuto(dati: bytes) -> str:
    return hashlib.sha256(dati).hexdigest()


# ── chiamate all'AI ───────────────────────────────────────────────────────────

def leggi_json(testo: str) -> dict:
    testo = re.sub(r"^```(?:json)?|```$", "", (testo or "").strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(testo)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", testo, re.DOTALL)
        return json.loads(m.group(0)) if m else {}


def chiedi_json(modello, contenuto: list, avvisi: list | None = None, tentativi: int = 2):
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
    if avvisi is not None:
        avvisi.append(f"chiamata AI non riuscita: {str(ultimo)[:200]}")
    return None


# ── PDF e appunti: letti dall'AI ──────────────────────────────────────────────

def blocchi_di_pagine(pdf_bytes: bytes, per_blocco: int):
    import fitz                                   # PyMuPDF, già nelle dipendenze
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    for inizio in range(0, len(doc), per_blocco):
        fine = min(inizio + per_blocco, len(doc)) - 1
        parte = fitz.open()
        parte.insert_pdf(doc, from_page=inizio, to_page=fine)
        yield inizio + 1, len(doc), parte.tobytes()


def esercizi_da_pdf(modello, materia: str, pdf_bytes: bytes, pagine: int, avvisi: list, on_progress=None) -> list:
    tutti = []
    for prima, totali, dati in blocchi_di_pagine(pdf_bytes, pagine):
        if on_progress:
            on_progress(f"Leggo le pagine da {prima} ({totali} in tutto)…")
        r = chiedi_json(modello, [prompt_importa_esercizi(materia), {"mime_type": "application/pdf", "data": dati}], avvisi)
        for e in (r or {}).get("esercizi", []):
            e["pagina"] = prima + int(e.get("pagina_nel_blocco") or 1) - 1
            tutti.append(e)
    return tutti


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
                blocchi.append(q[:taglio])
                q = q[taglio:]
            if len(corrente) + len(q) > massimo and corrente:
                blocchi.append(corrente)
                corrente = ""
            corrente += q
    if corrente.strip():
        blocchi.append(corrente)
    return blocchi


def esercizi_da_appunti(modello, materia: str, tex: str, avvisi: list, on_progress=None) -> list:
    tutti, blocchi = [], blocchi_di_sorgente(tex)
    for i, blocco in enumerate(blocchi, 1):
        if on_progress:
            on_progress(f"Leggo il blocco {i} di {len(blocchi)}…")
        r = chiedi_json(modello, [prompt_importa_esercizi(materia, da_latex=True) + "\n\nCODICE LATEX:\n" + blocco], avvisi)
        for e in (r or {}).get("esercizi", []):
            e["pagina"] = i
            tutti.append(e)
    return tutti


# ── verifiche e schede: lette dal codice ──────────────────────────────────────

def esercizi_da_verifica(d: dict):
    esercizi, sezioni_mod = [], []
    for si, s in enumerate(d["sezioni"], 1):
        sezioni_mod.append({
            "nome": s["nome"], "tipo": s["tipo"], "consegna": s["consegna"], "n_quesiti": len(s["quesiti"]),
            "punti": [q.get("punti") for q in s["quesiti"]],
            "facoltativi": [q["etichetta"] for q in s["quesiti"] if q["facoltativo"]],
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


def etichetta_con_ai(modello, materia: str, titolo: str, esercizi: list, avvisi: list, on_progress=None):
    """Argomento, tecniche, difficoltà e tipo per esercizi già estratti dal codice (a gruppi di 40)."""
    per_sezione = {}
    for e in esercizi:
        per_sezione.setdefault(e.get("sezione") or e.get("titolo_sezione") or "", []).append(e)
    for gruppo_sez in per_sezione.values():
        for k, e in enumerate(gruppo_sez, 1):
            e["_pos"], e["_su"] = k, len(gruppo_sez)

    for inizio in range(0, len(esercizi), 40):
        if on_progress:
            on_progress(f"Etichetto gli esercizi {inizio + 1}–{min(inizio + 40, len(esercizi))} di {len(esercizi)}…")
        gruppo = esercizi[inizio:inizio + 40]
        elenco = [{"id": i,
                   "testo": (e["testo_latex"] + (" | opzioni: " + " ; ".join(e["opzioni"]) if e.get("opzioni") else ""))[:600],
                   "sezione": e.get("sezione") or e.get("titolo_sezione") or "",
                   "posizione": e["_pos"], "su": e["_su"]}
                  for i, e in enumerate(gruppo)]
        r = chiedi_json(modello, [prompt_etichetta_esercizi(materia, titolo, json.dumps(elenco, ensure_ascii=False))], avvisi)
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
    for e in esercizi:
        e.pop("_pos", None)
        e.pop("_su", None)


_PAROLE_DIFFICOLTA = re.compile(r"sfida|facil|difficil|\bbase\b|avanzat|potenziament|approfondiment", re.IGNORECASE)


def interpreta_livelli(modello, esercizi: list, modo: str, avvisi: list | None = None):
    """Le sezioni «Livello N» sono difficoltà o argomenti diversi? Restituisce (modo, motivo)."""
    if modo in ("difficolta", "argomenti"):
        return modo, "scelto a mano"
    titoli = []
    for e in esercizi:
        t = e.get("titolo_sezione", "")
        if t and t not in [x["titolo"] for x in titoli]:
            titoli.append({"titolo": t, "esempi": [x["testo_latex"] for x in esercizi if x.get("titolo_sezione") == t][:2]})
    if modello is not None:
        r = chiedi_json(modello, [prompt_tipo_livelli(json.dumps(titoli, ensure_ascii=False))], avvisi)
        if r and r.get("livelli") in ("difficolta", "argomenti"):
            return r["livelli"], r.get("motivo", "deciso dall'AI")
    hit = sum(1 for x in titoli if _PAROLE_DIFFICOLTA.search(x["titolo"]))
    return ("difficolta" if hit else "argomenti"), "dai titoli delle sezioni (senza AI)"


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


# ── un file intero ────────────────────────────────────────────────────────────

def analizza_file(nome: str, contenuto: bytes, materia: str = "", modello=None, livelli: str = "auto",
                  senza_ai: bool = False, pagine: int = 4, on_progress=None) -> dict | None:
    """
    Analizza un file e restituisce:
      {"fonte": {nome, tipo, titolo, hash}, "esercizi": [...], "modello_verifica": dict|None,
       "nota_livelli": str, "avvisi": [str]}
    oppure None se il formato non è supportato o servono l'AI e non c'è.
    """
    ext = nome.lower().rsplit(".", 1)[-1] if "." in nome else ""
    avvisi: list = []
    usa_ai = modello is not None and not senza_ai
    nota_livelli, modello_verifica, esercizi, titolo = "", None, [], nome.rsplit(".", 1)[0]
    tipo = ext

    if ext == "tex":
        tex = contenuto.decode("utf-8", errors="replace")
        d = leggi_tex(tex)
        tipo = d["tipo_file"]
        titolo = d.get("titolo") or titolo
        if tipo == "verifica":
            esercizi, modello_verifica = esercizi_da_verifica(d)
        elif tipo == "scheda":
            esercizi = esercizi_da_scheda(d)
            interpretazione, motivo = interpreta_livelli(modello if usa_ai else None, esercizi, livelli, avvisi)
            nota_livelli = (f"Le sezioni «Livello N» sono state interpretate come "
                            f"{'LIVELLI DI DIFFICOLTÀ' if interpretazione == 'difficolta' else 'ARGOMENTI DIVERSI'} "
                            f"({motivo}).")
            if interpretazione == "argomenti":
                for e in esercizi:
                    e["capitolo"] = re.sub(r"^Livello\s+\d+\s*[-–—]*\s*", "", e.get("titolo_sezione", ""))
                    e["livello_numero"], e["livelli_totali"] = None, None
        else:                                                   # appunti
            if not usa_ai:
                avvisi.append("appunti: serve l'AI (chiave mancante o analisi senza AI)")
                return None
            esercizi = esercizi_da_appunti(modello, materia, tex, avvisi, on_progress)
        if usa_ai and tipo in ("verifica", "scheda"):
            etichetta_con_ai(modello, materia, titolo, esercizi, avvisi, on_progress)
    elif ext == "pdf":
        if not usa_ai:
            avvisi.append("i PDF li legge l'AI: chiave mancante o analisi senza AI")
            return None
        tipo = "pdf"
        esercizi = esercizi_da_pdf(modello, materia, contenuto, pagine, avvisi, on_progress)
    else:
        avvisi.append("formato non supportato: uso file .tex e .pdf")
        return None

    return {
        "fonte": {"nome": nome, "tipo": tipo, "titolo": titolo, "hash": hash_contenuto(contenuto)},
        "esercizi": normalizza(esercizi), "modello_verifica": modello_verifica,
        "nota_livelli": nota_livelli, "avvisi": avvisi,
    }
