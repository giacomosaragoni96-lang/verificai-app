"""
banca_import.py — legge una verifica in LaTeX e ne ricava il MODELLO (struttura, punti, stile).

Nessuna AI e nessun import di streamlit: il codice LaTeX è letto da un programma (estrai_tex.py),
quindi sezioni, punti per quesito, esercizi facoltativi (*) e base/extra sono esatti.
"""
import hashlib
import re

from config import MATERIE
from estrai_tex import leggi_tex


def hash_contenuto(dati: bytes) -> str:
    return hashlib.sha256(dati).hexdigest()


def materia_dal_titolo(*testi: str):
    """La materia, se compare nel titolo o nel nome del file («Verifica di Matematica»)."""
    t = " ".join(testi).lower()
    for m in MATERIE:
        if m != "Altra materia" and re.search(r"\b" + re.escape(m.lower()) + r"\b", t):
            return m
    return None


def _sezioni_modello(d: dict) -> list:
    sezioni = []
    for s in d["sezioni"]:
        sezioni.append({
            "nome": s["nome"], "tipo": s["tipo"], "consegna": s["consegna"], "n_quesiti": len(s["quesiti"]),
            "punti": [q.get("punti") for q in s["quesiti"]],
            "facoltativi": [q["etichetta"] for q in s["quesiti"] if q["facoltativo"]],
            "etichette": [q["etichetta"] for q in s["quesiti"]],
            "opzioni_per_quesito": max([len(q["opzioni"]) for q in s["quesiti"]] or [0]),
        })
    return sezioni


def analizza_verifica(nome: str, contenuto: bytes):
    """
    Legge una verifica .tex. Restituisce (risultato, "") con
      risultato = {"fonte": {nome, tipo, titolo, hash}, "materia": str|None, "modello": {...struttura...}}
    oppure (None, "motivo") se il file non è una verifica LaTeX leggibile.
    """
    if not nome.lower().endswith(".tex"):
        return None, "carica una verifica in formato LaTeX (.tex)"
    tex = contenuto.decode("utf-8", errors="replace")
    d = leggi_tex(tex)
    if d["tipo_file"] != "verifica":
        return None, ("questo file sembra " + ("una scheda di esercizi" if d["tipo_file"] == "scheda" else "degli appunti")
                      + ", non una verifica: qui si caricano solo le verifiche")
    sezioni = _sezioni_modello(d)
    if not sezioni:
        return None, "non trovo gli esercizi della verifica"
    modello = {
        "titolo": d["titolo"], "argomento": d["argomento_titolo"], "istruzioni": d["istruzioni"],
        "sezioni": sezioni, "punti_base": d["punti_base"], "punti_extra": d["punti_extra"],
        "totale": d["totale"], "base_pdp_dsa": d["base_pdp_dsa"], "stile": d["stile"],
        "punti_letti": d["punti_letti"],
        "sorgente_latex": tex,                      # il codice originale: stile e impaginazione di riferimento
    }
    titolo = d["titolo"] or nome.rsplit(".", 1)[0]
    return {
        "fonte": {"nome": nome, "tipo": "verifica", "titolo": titolo, "hash": hash_contenuto(contenuto)},
        "materia": materia_dal_titolo(d["titolo"], d["argomento_titolo"], nome),
        "modello": modello,
    }, ""
