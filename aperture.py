"""
aperture.py — contatore ANONIMO di quante persone aprono l'app e da quale link arrivano (senza Streamlit).

Serve a capire dove si perde chi arriva dai post (landing → schermata di accesso → iscrizione). Si scrive una riga per sessione
con la sola «sorgente» del link (?src=gruppo1…); mai user_id, email, IP o altro che identifichi la persona.
La tabella `aperture_app` (migrazione_aperture.sql, da eseguire a mano) ha la sicurezza a livello di riga attiva e nessuna
policy: scrive solo il server con la chiave di servizio. Senza la tabella non succede niente (non solleva mai).
"""
import re

_RE_SRC = re.compile(r"[^A-Za-z0-9_-]")


def pulisci_src(src) -> str:
    """La sorgente come si salva: solo lettere, cifre, - e _ (max 30); vuota = «diretto»."""
    s = _RE_SRC.sub("", str(src or ""))[:30]
    return s or "diretto"


def registra_apertura(admin, src, tappa: str = "login") -> bool:
    """Una riga in `aperture_app`. `tappa`: «login» = ha visto la schermata di accesso senza essere dentro. False se non scritta."""
    if admin is None:
        return False
    try:
        admin.table("aperture_app").insert({"src": pulisci_src(src), "tappa": str(tappa)[:20]}).execute()
        return True
    except Exception:
        return False
