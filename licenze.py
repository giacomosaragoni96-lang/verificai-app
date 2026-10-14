"""
licenze.py — attivazione e riconvalida delle licenze Pro (Lemon Squeezy, API pubblica delle licenze).

Nessun import di Streamlit e nessuna chiave segreta: l'API delle licenze è pubblica. Il docente compra, riceve un
codice e lo incolla nell'app; qui lo si controlla e, solo se è valido e del NOSTRO prodotto, si scrive la riga in
`subscriptions` (con la chiave di servizio passata da chi chiama). Mai l'utente scrive in `subscriptions`.

Fail-closed: se gli ID del negozio e del prodotto non sono in config, nessun codice viene accettato.
"""
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import requests

from config import LEMON_PRODUCT_ID, LEMON_STORE_ID

logger = logging.getLogger(__name__)

API = "https://api.lemonsqueezy.com/v1/licenses"
TIMEOUT = 10
RICONVALIDA_ORE = 24          # ogni quanto si ricontrolla la licenza
TOLLERANZA_GIORNI = 3         # se il servizio non risponde si resta Pro per questi giorni dall'ultima convalida
DURATA_GIORNI = 365           # se la licenza non dice la scadenza

_RE_CHIAVE = re.compile(r"^[A-Za-z0-9\-]{10,80}$")


@dataclass(frozen=True)
class EsitoLicenza:
    ok: bool
    messaggio: str              # frase per il docente
    dettaglio_admin: str = ""   # dettaglio tecnico, da mostrare solo all'admin


class ServizioNonRaggiungibile(Exception):
    pass


def _chiama(percorso: str, dati: dict) -> dict:
    """POST form all'API delle licenze; ritorna il JSON (anche con errori 4xx, che hanno `error`)."""
    try:
        r = requests.post(f"{API}/{percorso}", data=dati, headers={"Accept": "application/json"}, timeout=TIMEOUT)
    except requests.RequestException as e:
        raise ServizioNonRaggiungibile(str(e)) from e
    try:
        return r.json()
    except ValueError as e:
        raise ServizioNonRaggiungibile(f"risposta non valida ({r.status_code})") from e


def _adesso() -> datetime:
    return datetime.now(timezone.utc)


def _data(testo) -> datetime | None:
    if not testo:
        return None
    try:
        d = datetime.fromisoformat(str(testo).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _e_nostro(meta: dict) -> tuple[bool, str]:
    """La licenza è del nostro negozio e del nostro prodotto? (senza ID configurati: mai)"""
    s, p = (meta or {}).get("store_id"), (meta or {}).get("product_id")
    dettaglio = f"store_id={s} product_id={p}"
    if not LEMON_STORE_ID or not LEMON_PRODUCT_ID:
        return False, "ID del negozio/prodotto non ancora in config.py (LEMON_STORE_ID, LEMON_PRODUCT_ID): " + dettaglio
    try:
        return (int(s) == int(LEMON_STORE_ID) and int(p) == int(LEMON_PRODUCT_ID)), dettaglio
    except (TypeError, ValueError):
        return False, dettaglio


def attiva_licenza(sb, user_id: str, chiave: str) -> EsitoLicenza:
    """
    Controlla il codice, lo attiva per questo utente e scrive il piano Pro.
    sb = client Supabase con chiave di servizio.
    """
    chiave = (chiave or "").strip()
    if not _RE_CHIAVE.match(chiave):
        return EsitoLicenza(False, "Il codice non sembra corretto. Copialo di nuovo dalla mail o dalla pagina di acquisto.")

    # Il codice è già di un altro account?
    try:
        gia = sb.table("subscriptions").select("user_id,status").eq("licenza_chiave", chiave).limit(1).execute()
    except Exception as e:
        logger.error("Lettura subscriptions fallita: %s", e)
        return EsitoLicenza(False, "Non riesco a controllare il codice adesso. Riprova tra poco.", str(e))
    if gia.data:
        if str(gia.data[0].get("user_id")) == str(user_id):
            return EsitoLicenza(True, "Il tuo piano Pro è già attivo su questo account.")
        return EsitoLicenza(False, "Questo codice è già stato usato su un altro account.")

    try:
        # 1) si legge la licenza SENZA attivarla (l'attivazione è una sola: non va sprecata su un codice altrui)
        v = _chiama("validate", {"license_key": chiave})
        if not v.get("valid") and not v.get("license_key"):
            return EsitoLicenza(False, "Codice non valido.", str(v.get("error")))
        lic = v.get("license_key") or {}
        ok_nostro, dett = _e_nostro(v.get("meta") or {})
        if not ok_nostro:
            logger.warning("Licenza non accettata (%s)", dett)
            return EsitoLicenza(False, "Questo codice non vale per VerificAI Pro.", dett)
        if lic.get("status") in ("expired", "disabled"):
            return EsitoLicenza(False, "Questo codice è scaduto o non è più valido.", str(lic.get("status")))

        # 2) attivazione per questo utente
        a = _chiama("activate", {"license_key": chiave, "instance_name": str(user_id)})
    except ServizioNonRaggiungibile as e:
        logger.warning("Servizio licenze non raggiungibile: %s", e)
        return EsitoLicenza(False, "Il servizio di verifica non risponde. Riprova tra qualche minuto.", str(e))
    if not a.get("activated"):
        err = str(a.get("error") or "")
        if "limit" in err.lower():
            return EsitoLicenza(False, "Questo codice è già stato usato su un altro account.", err)
        return EsitoLicenza(False, "Non sono riuscito ad attivare il codice.", err)

    lic = a.get("license_key") or lic
    istanza = (a.get("instance") or {}).get("id")
    scadenza = _data(lic.get("expires_at")) or (_adesso() + timedelta(days=DURATA_GIORNI))
    try:
        sb.table("subscriptions").insert({
            "user_id": user_id,
            "stripe_subscription_id": f"ls-{lic.get('id')}",
            "plan_id": "pro", "status": "active",
            "current_period_end": scadenza.isoformat(),
            "cancel_at_period_end": False,
            "provider": "lemonsqueezy", "interval": "year",
            "licenza_chiave": chiave, "licenza_istanza_id": istanza,
            "ultima_verifica_licenza": _adesso().isoformat(),
        }).execute()
    except Exception as e:
        logger.error("Scrittura subscriptions fallita dopo l'attivazione: %s", e)
        try:   # si libera l'attivazione, così il docente può riprovare
            _chiama("deactivate", {"license_key": chiave, "instance_id": istanza})
        except Exception:
            pass
        return EsitoLicenza(False, "Codice valido, ma non riesco a salvare il piano. Riprova tra poco.", str(e))
    return EsitoLicenza(True, "Piano Pro attivato. Grazie!")


def riconvalida_se_serve(sb, user_id: str) -> None:
    """
    Se l'utente ha una licenza Lemon Squeezy attiva non controllata da più di RICONVALIDA_ORE ore, la ricontrolla:
    rimborsata, disabilitata o scaduta → la riga diventa `canceled` (torna Free). Se il servizio non risponde
    si resta Pro per TOLLERANZA_GIORNI dall'ultima convalida riuscita. Non solleva mai eccezioni.
    """
    try:
        res = sb.table("subscriptions").select("id,licenza_chiave,licenza_istanza_id,ultima_verifica_licenza,provider") \
            .eq("user_id", user_id).eq("status", "active").eq("provider", "lemonsqueezy").limit(1).execute()
        if not res.data:
            return
        riga = res.data[0]
        ultima = _data(riga.get("ultima_verifica_licenza"))
        if ultima and _adesso() - ultima < timedelta(hours=RICONVALIDA_ORE):
            return
        try:
            v = _chiama("validate", {"license_key": riga["licenza_chiave"], "instance_id": riga.get("licenza_istanza_id") or ""})
        except ServizioNonRaggiungibile as e:
            logger.warning("Riconvalida licenza: servizio non raggiungibile (%s)", e)
            if ultima is None or _adesso() - ultima > timedelta(days=TOLLERANZA_GIORNI):
                sb.table("subscriptions").update({"status": "canceled"}).eq("id", riga["id"]).execute()
            return
        lic = v.get("license_key") or {}
        if not v.get("valid") or lic.get("status") in ("expired", "disabled"):
            logger.info("Licenza non più valida (%s): piano Free", lic.get("status") or v.get("error"))
            sb.table("subscriptions").update({"status": "canceled"}).eq("id", riga["id"]).execute()
            return
        agg = {"ultima_verifica_licenza": _adesso().isoformat()}
        scad = _data(lic.get("expires_at"))
        if scad:
            agg["current_period_end"] = scad.isoformat()
        sb.table("subscriptions").update(agg).eq("id", riga["id"]).execute()
    except Exception as e:
        logger.error("Riconvalida licenza fallita: %s", e)
