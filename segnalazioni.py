"""
segnalazioni.py — segnalazioni ANONIME di verifiche venute male (senza Streamlit).

Il docente scrive cosa non va; se lascia la spunta arrivano anche il testo della verifica e i dettagli tecnici della
generazione (prompt, risposta del modello, consumi). Non si salva MAI chi ha inviato: niente user_id, email o IP.
La tabella `segnalazioni` (migrazione_segnalazioni.sql, da eseguire a mano) ha la sicurezza a livello di riga attiva
e nessuna policy: scrive solo il server con la chiave di servizio e legge solo chi gestisce il database.
"""
import json

from latex_utils import rimuovi_logo_b64

MAX_NOTA = 2000
MAX_TESTO = 200_000          # caratteri: oltre questo si taglia (un debug completo ne ha circa 100 mila)
MAX_PER_SESSIONE = 3


def _taglia(testo, massimo: int = MAX_TESTO):
    t = "" if testo is None else str(testo)
    return t if len(t) <= massimo else t[:massimo] + "\n… [tagliato]"


def testo_debug(debug: dict | None, latex_finale: str = "") -> str:
    """I dettagli della generazione in un unico testo, nello stesso formato del file scaricabile dall'admin."""
    d = debug or {}
    return "\n\n".join([
        "=== RICHIESTA ===\n" + json.dumps(d.get("richiesta"), ensure_ascii=False, indent=2, default=str),
        "=== CHIAMATE ===\n" + json.dumps(d.get("chiamate"), ensure_ascii=False, indent=2, default=str),
        f"=== CONTROLLO QUALITÀ ===\n{d.get('controllo_qualita')} (punteggio {d.get('validation_score')})",
        "=== AUTOVERIFICA ===\n" + json.dumps(d.get("autoverifica"), ensure_ascii=False, indent=2, default=str),
        "=== PROMPT INVIATO AL MODELLO ===\n" + str(d.get("prompt")),
        "=== RISPOSTA GREZZA DEL MODELLO ===\n" + str(d.get("risposta_grezza")),
        "=== DOPO CONTROLLO QUALITÀ ===\n" + str(d.get("dopo_controllo_qualita")),
        "=== DOPO AUTOVERIFICA ===\n" + str(d.get("dopo_autoverifica")),
        "=== LATEX FINALE (dopo pesi, punti, griglia, logo) ===\n" + str(latex_finale),
    ])


def costruisci_segnalazione(nota: str, esercizio, parametri: dict | None, modello: str | None, piano: str | None,
                            latex: str | None, debug: dict | None = None, allega: bool = True) -> dict:
    """
    La riga da inserire in `segnalazioni`. `esercizio` è il numero (da 1) dell'esercizio segnalato, o None per tutta la verifica.
    Con allega=False restano solo la nota e i dati generali (materia, scuola, argomento, modello, piano).
    """
    p = parametri or {}
    latex_pulito = rimuovi_logo_b64(latex or "")
    riga = {
        "nota": _taglia((nota or "").strip(), MAX_NOTA),
        "esercizio": int(esercizio) if esercizio else None,
        "materia": p.get("materia"),
        "scuola": p.get("difficolta"),
        "argomento": p.get("argomento"),
        "modello": modello,
        "piano": piano,
        "latex": None,
        "debug": None,
    }
    if allega:
        riga["latex"] = _taglia(latex_pulito)
        if debug:
            riga["debug"] = _taglia(testo_debug(debug, latex_pulito))
    return riga
