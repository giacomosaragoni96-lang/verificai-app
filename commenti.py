"""
commenti.py — commenti ANONIMI e facoltativi lasciati dopo uno scarico (senza Streamlit).

Si salva solo il testo: niente user_id, email o IP. Tabella `commenti_app` in migrazione_commenti.sql (da eseguire a mano):
senza la tabella il commento non viene salvato e l'app funziona lo stesso.
"""

MAX_COMMENTO = 1000


def costruisci_commento(testo) -> dict | None:
    """La riga da inserire in `commenti_app`, oppure None se il commento è vuoto."""
    t = (testo or "").strip()
    return {"commento": t[:MAX_COMMENTO]} if t else None
