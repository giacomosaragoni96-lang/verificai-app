"""
sblocco.py — codici che si ricevono compilando il questionario completo e che danno verifiche con tutte le funzioni (senza Streamlit).

Il questionario è anonimo: il codice si genera alla fine e NON viene collegato alle risposte. Quando l'utente lo inserisce
nell'app (account loggato) la riga del codice registra chi l'ha usato: così un codice vale una volta sola e un account ne può usare
al massimo `config.MAX_CODICI_PER_UTENTE`. Ogni codice vale `config.VERIFICHE_PER_CODICE` verifiche complete (i crediti si leggono
in inviti.riepilogo, insieme a quelli degli inviti). Tabella: `codici_sblocco` (migrazione_sblocco.sql, da eseguire a mano).
Nessuna funzione solleva: in caso di errore ritorna un valore prudente.
"""
import logging
import secrets
from datetime import datetime, timezone
from typing import Optional, Tuple

from config import MAX_CODICI_PER_UTENTE

logger = logging.getLogger("verificai.sblocco")

_ALFABETO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"        # niente 0/O, 1/I: si copia a mano senza errori


def _canonico(testo: str) -> str:
    return "".join(ch for ch in (testo or "").upper() if ch.isalnum())


def formatta(codice: str) -> str:
    """«VFABCD2345» → «VF-ABCD-2345»."""
    c = _canonico(codice)
    return f"{c[:2]}-{c[2:6]}-{c[6:10]}" if len(c) == 10 else c


def genera_codice(sb) -> Optional[str]:
    """Crea e salva un codice nuovo; ritorna il codice (formato VF-XXXX-XXXX) o None se non riesce."""
    if sb is None:
        return None
    for _ in range(5):
        c = "VF" + "".join(secrets.choice(_ALFABETO) for _ in range(8))
        try:
            sb.table("codici_sblocco").insert({"codice": c}).execute()
            return formatta(c)
        except Exception as e:
            logger.warning("codice non salvato (riprovo): %s", e)
    return None


def riscatta(sb, user_id: str, testo: str) -> Tuple[bool, str]:
    """Collega un codice all'utente. (ok, messaggio per l'utente)."""
    c = _canonico(testo)
    if len(c) != 10 or not c.startswith("VF"):
        return False, "Il codice non è scritto bene: deve essere del tipo VF-ABCD-2345."
    try:
        n = sb.table("codici_sblocco").select("codice", count="exact").eq("usato_da", user_id).execute()
        if int(n.count or 0) >= MAX_CODICI_PER_UTENTE:
            return False, "Hai già usato tutti i codici disponibili per questo account."
        r = sb.table("codici_sblocco").update({"usato_da": user_id, "usato_il": datetime.now(timezone.utc).isoformat()}) \
            .eq("codice", c).is_("usato_da", "null").execute()
        if r.data:
            return True, "Fatto! Hai nuove verifiche con tutte le funzioni."
        esiste = sb.table("codici_sblocco").select("codice").eq("codice", c).limit(1).execute()
        return False, ("Questo codice è già stato usato." if esiste.data else "Non trovo questo codice: controlla di averlo copiato per intero.")
    except Exception as e:
        logger.warning("riscatto non riuscito: %s", e)
        return False, "Non riesco a controllare il codice in questo momento. Riprova tra poco."
