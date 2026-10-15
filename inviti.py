"""
Inviti tra colleghi: un docente invita un amico con un link personale; quando l'amico si iscrive e completa la sua
prima verifica, chi ha invitato guadagna verifiche con tutto il piano Pro (`config.BONUS_PER_INVITO` per amico,
fino a `config.MAX_INVITI_CON_BONUS` amici).

Logica senza Streamlit: riceve il client Supabase del server (chiave di servizio). Le tabelle (`codici_invito`,
`inviti`, `bonus_usati`) si creano con `migrazione_inviti.sql` e si scrivono solo da qui. Ogni funzione che legge o
scrive NON solleva: in caso di errore restituisce un valore prudente (nessun bonus, nessun invito).
"""
import logging
import re
import secrets
import string
from typing import Optional, Tuple

from config import BONUS_PER_INVITO, MAX_INVITI_CON_BONUS, VERIFICHE_PER_CODICE

logger = logging.getLogger("verificai.inviti")

_ALFABETO = string.ascii_lowercase + string.digits
_RE_CODICE = re.compile(r"^[a-z0-9]{6,16}$")


def codice_valido(codice) -> Optional[str]:
    """Il codice dell'URL, se ha la forma giusta (minuscolo, 6-16 caratteri alfanumerici); altrimenti None."""
    c = str(codice or "").strip().lower()
    return c if _RE_CODICE.match(c) else None


def codice_di(sb, user_id: str) -> Optional[str]:
    """Il codice di invito personale dell'utente; lo crea la prima volta. None se non si riesce."""
    try:
        r = sb.table("codici_invito").select("codice").eq("user_id", user_id).limit(1).execute()
        if r.data:
            return r.data[0]["codice"]
        for _ in range(5):
            codice = "".join(secrets.choice(_ALFABETO) for _ in range(8))
            try:
                sb.table("codici_invito").insert({"user_id": user_id, "codice": codice}).execute()
                return codice
            except Exception as e:                      # codice già preso o corsa tra due sessioni: si riprova
                r2 = sb.table("codici_invito").select("codice").eq("user_id", user_id).limit(1).execute()
                if r2.data:
                    return r2.data[0]["codice"]
                logger.info("codice di invito occupato, riprovo: %s", e)
    except Exception as e:
        logger.warning("codice_di non riuscito: %s", e)
    return None


def registra_invito(sb, codice: str, invitato_id: str) -> bool:
    """
    Collega un utente nuovo a chi l'ha invitato. Vale solo se: il codice esiste, l'invitato non è chi invita, non ha
    ancora nessuna verifica (altrimenti non è un utente nuovo) e non è già stato invitato da qualcuno.
    """
    codice = codice_valido(codice)
    if not codice:
        return False
    try:
        r = sb.table("codici_invito").select("user_id").eq("codice", codice).limit(1).execute()
        if not r.data:
            return False
        invitante = r.data[0]["user_id"]
        if str(invitante) == str(invitato_id):
            return False
        gia = sb.table("verifiche_storico").select("id").eq("user_id", invitato_id).limit(1).execute()
        if gia.data:
            return False
        sb.table("inviti").insert({"invitante_id": invitante, "invitato_id": invitato_id}).execute()
        return True
    except Exception as e:                              # anche «già invitato» (indice unico) finisce qui: va bene
        logger.info("registra_invito non registrato: %s", e)
        return False


def convalida_invito(sb, invitato_id: str) -> None:
    """Da chiamare quando l'invitato completa la sua prima verifica: da quel momento l'invito vale."""
    try:
        sb.table("inviti").update({"convalidato_il": "now()"}) \
            .eq("invitato_id", invitato_id).is_("convalidato_il", "null").execute()
    except Exception as e:
        logger.warning("convalida_invito non riuscita: %s", e)


def riepilogo(sb, user_id: str) -> Tuple[bool, int, int, int]:
    """
    (ok, inviti_convalidati, bonus_guadagnati, bonus_residui). ok=False se non si riesce a leggere
    (in quel caso nessun bonus: mai Pro per un guasto).
    """
    try:
        c = sb.table("inviti").select("id", count="exact").eq("invitante_id", user_id) \
            .not_.is_("convalidato_il", "null").execute()
        convalidati = int(c.count or 0)
        u = sb.table("bonus_usati").select("verifica_id", count="exact").eq("user_id", user_id).execute()
        usati = int(u.count or 0)
    except Exception as e:
        logger.warning("riepilogo inviti non riuscito: %s", e)
        return False, 0, 0, 0
    try:                                    # codici del questionario completo (tabella assente = nessun credito)
        cd = sb.table("codici_sblocco").select("codice", count="exact").eq("usato_da", user_id).execute()
        da_codici = int(cd.count or 0) * VERIFICHE_PER_CODICE
    except Exception:
        da_codici = 0
    guadagnati = min(convalidati, MAX_INVITI_CON_BONUS) * BONUS_PER_INVITO + da_codici
    return True, convalidati, guadagnati, max(0, guadagnati - usati)


def usa_bonus(sb, user_id: str, verifica_id) -> bool:
    """Segna una verifica come «bonus»: da lì in poi ha tutto il piano Pro, e consuma un credito."""
    if not verifica_id:
        return False
    try:
        sb.table("bonus_usati").insert({"user_id": user_id, "verifica_id": verifica_id}).execute()
        return True
    except Exception as e:
        logger.warning("usa_bonus non riuscito: %s", e)
        return False


def e_verifica_bonus(sb, user_id: str, verifica_id) -> bool:
    """True se quella verifica è stata creata con un credito bonus."""
    if not verifica_id:
        return False
    try:
        r = sb.table("bonus_usati").select("verifica_id").eq("user_id", user_id) \
            .eq("verifica_id", verifica_id).limit(1).execute()
        return bool(r.data)
    except Exception as e:
        logger.warning("e_verifica_bonus non riuscito: %s", e)
        return False
