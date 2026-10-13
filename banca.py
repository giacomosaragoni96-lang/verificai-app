"""
banca.py — archivio dei MODELLI di verifica su Supabase (solo lato server). Nessun import di streamlit.

Tabelle (vedi modelli_verifica.sql): banca_fonti (il file caricato) e banca_modelli (la sua struttura).
Ogni funzione prende il client Supabase con la chiave di servizio (supabase_admin).
"""
import logging

logger = logging.getLogger("verificai.banca")

FONTI = "banca_fonti"
MODELLI = "banca_modelli"


def tabelle_pronte(sb) -> bool:
    """True se le due tabelle esistono (create con modelli_verifica.sql)."""
    try:
        for t in (FONTI, MODELLI):
            sb.table(t).select("id").limit(1).execute()
        return True
    except Exception as e:                            # noqa: BLE001
        logger.warning("Modelli di verifica: tabelle non disponibili (%s)", str(e)[:200])
        return False


def salva_modello(sb, risultato: dict, materia: str = "", scuola: str = "") -> dict:
    """
    Salva il risultato di banca_import.analizza_verifica come modello «in attesa di approvazione».
    Se lo stesso file (stessa impronta) è già in archivio non lo ricarica.
    Restituisce {"modello_id", "gia_presente", "materia"}.
    """
    f = risultato["fonte"]
    esistente = sb.table(FONTI).select("id").eq("hash", f["hash"]).limit(1).execute().data
    if esistente:
        return {"modello_id": None, "gia_presente": True, "materia": materia or None}
    materia = materia or risultato.get("materia") or ""
    fonte = sb.table(FONTI).insert({
        "nome": f["nome"], "tipo": f["tipo"], "titolo": f.get("titolo"), "materia": materia or None,
        "scuola": scuola or None, "hash": f["hash"],
    }).execute().data[0]
    m = risultato["modello"]
    nome = (f.get("titolo") or f["nome"])[:120] + (f" — {m['argomento']}" if m.get("argomento") else "")
    modello = sb.table(MODELLI).insert({
        "fonte_id": fonte["id"], "nome": nome, "materia": materia or None, "scuola": scuola or None,
        "struttura": m, "approvato": False,
    }).execute().data[0]
    return {"modello_id": modello["id"], "gia_presente": False, "materia": materia or None}


def modelli(sb, approvato: bool | None = None, materia: str | None = None, scuola: str | None = None) -> list:
    q = sb.table(MODELLI).select("*")
    if approvato is not None:
        q = q.eq("approvato", approvato)
    if materia:
        q = q.eq("materia", materia)
    if scuola:
        q = q.eq("scuola", scuola)
    return q.order("created_at", desc=True).execute().data or []


def aggiorna_modello(sb, modello_id: str, campi: dict):
    ammessi = {k: v for k, v in campi.items() if k in ("nome", "materia", "scuola", "approvato")}
    if ammessi:
        sb.table(MODELLI).update(ammessi).eq("id", modello_id).execute()


def elimina_modello(sb, modello_id: str):
    """Elimina il modello e il file da cui viene."""
    riga = sb.table(MODELLI).select("fonte_id").eq("id", modello_id).limit(1).execute().data
    sb.table(MODELLI).delete().eq("id", modello_id).execute()
    if riga and riga[0].get("fonte_id"):
        sb.table(FONTI).delete().eq("id", riga[0]["fonte_id"]).execute()
