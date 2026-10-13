"""
banca.py — archivio degli esercizi su Supabase (solo lato server). Nessun import di streamlit.

Tabelle (vedi banca_esercizi.sql): banca_fonti, banca_esercizi, banca_modelli.
Ogni funzione prende il client Supabase con la chiave di servizio (supabase_admin).
"""
import logging

logger = logging.getLogger("verificai.banca")

FONTI = "banca_fonti"
ESERCIZI = "banca_esercizi"
MODELLI = "banca_modelli"

_CAMPI_ESERCIZIO = (
    "numero", "sezione", "ruolo", "testo_latex", "opzioni", "soluzione_latex", "difficolta",
    "difficolta_origine", "argomento", "tecniche", "tipo", "punti", "facoltativo", "ha_figura",
)


def tabelle_pronte(sb) -> bool:
    """True se le tre tabelle esistono (sono state create con banca_esercizi.sql)."""
    try:
        for t in (FONTI, ESERCIZI, MODELLI):
            sb.table(t).select("id").limit(1).execute()
        return True
    except Exception as e:                            # noqa: BLE001
        logger.warning("Banca esercizi: tabelle non disponibili (%s)", str(e)[:200])
        return False


# ── salvataggio di un'analisi ─────────────────────────────────────────────────

def _riga_esercizio(e: dict, fonte_id: str, materia: str, scuola: str) -> dict:
    riga = {k: e.get(k) for k in _CAMPI_ESERCIZIO if k in e}
    riga["testo_latex"] = (e.get("testo_latex") or "").strip()
    riga["opzioni"] = e.get("opzioni") or []
    riga["ruolo"] = e.get("ruolo") or "esercizio"
    riga["tecniche"] = [str(t) for t in (e.get("tecniche") or [])]
    riga["argomento"] = e.get("argomento") or e.get("capitolo")
    riga["sezione"] = e.get("sezione") or e.get("titolo_sezione") or e.get("capitolo")
    riga["facoltativo"] = bool(e.get("facoltativo"))
    riga["ha_figura"] = bool(e.get("ha_figura"))
    riga["fonte_id"], riga["materia"], riga["scuola"], riga["approvato"] = fonte_id, materia or None, scuola or None, False
    return riga


def salva_analisi(sb, risultato: dict, materia: str = "", scuola: str = "") -> dict:
    """
    Salva il risultato di banca_import.analizza_file con gli esercizi «in attesa di revisione».
    Se lo stesso file (stessa impronta) è già in archivio non lo ricarica.
    Restituisce {"fonte_id", "nuovi", "gia_presente"}.
    """
    f = risultato["fonte"]
    if not materia or materia == "auto":
        materia = risultato.get("materia") or ""
    esistente = sb.table(FONTI).select("id").eq("hash", f["hash"]).limit(1).execute().data
    if esistente:
        return {"fonte_id": esistente[0]["id"], "nuovi": 0, "gia_presente": True}

    nuova = sb.table(FONTI).insert({
        "nome": f["nome"], "tipo": f["tipo"], "titolo": f.get("titolo"), "materia": materia or None,
        "scuola": scuola or None, "hash": f["hash"], "nota_livelli": risultato.get("nota_livelli") or None,
    }).execute().data[0]
    fonte_id = nuova["id"]

    righe = [_riga_esercizio(e, fonte_id, materia, scuola) for e in risultato["esercizi"]
             if (e.get("testo_latex") or "").strip()]
    for i in range(0, len(righe), 100):
        sb.table(ESERCIZI).insert(righe[i:i + 100]).execute()

    if risultato.get("modello_verifica"):
        m = risultato["modello_verifica"]
        sb.table(MODELLI).insert({
            "fonte_id": fonte_id, "nome": (f.get("titolo") or f["nome"])[:120] + (f" — {m['argomento']}" if m.get("argomento") else ""),
            "materia": materia or None, "scuola": scuola or None, "struttura": m, "approvato": False,
        }).execute()
    return {"fonte_id": fonte_id, "nuovi": len(righe), "gia_presente": False, "materia": materia or None}


# ── lettura ───────────────────────────────────────────────────────────────────

def elenco_fonti(sb) -> list:
    """Le fonti, dalla più recente, con il numero di esercizi in attesa e approvati."""
    fonti = sb.table(FONTI).select("*").order("created_at", desc=True).execute().data or []
    conteggi = {}
    for r in sb.table(ESERCIZI).select("fonte_id,approvato").execute().data or []:
        c = conteggi.setdefault(r["fonte_id"], {"in_attesa": 0, "approvati": 0})
        c["approvati" if r["approvato"] else "in_attesa"] += 1
    for f in fonti:
        f.update(conteggi.get(f["id"], {"in_attesa": 0, "approvati": 0}))
    return fonti


def esercizi(sb, fonte_id: str | None = None, approvato: bool | None = None, materia: str | None = None,
             difficolta: list | None = None, testo: str | None = None, limite: int = 500) -> list:
    q = sb.table(ESERCIZI).select("*")
    if fonte_id:
        q = q.eq("fonte_id", fonte_id)
    if approvato is not None:
        q = q.eq("approvato", approvato)
    if materia:
        q = q.eq("materia", materia)
    if difficolta:
        q = q.in_("difficolta", list(difficolta))
    if testo:
        t = testo.replace(",", " ").replace("%", " ").strip()
        q = q.or_(f"argomento.ilike.%{t}%,sezione.ilike.%{t}%,testo_latex.ilike.%{t}%")
    return q.order("created_at").limit(limite).execute().data or []


def statistiche(sb) -> dict:
    righe = sb.table(ESERCIZI).select("materia,difficolta,approvato").execute().data or []
    approvati = [r for r in righe if r["approvato"]]
    per_materia = {}
    for r in approvati:
        m = per_materia.setdefault(r["materia"] or "—", {1: 0, 2: 0, 3: 0})
        if r["difficolta"] in (1, 2, 3):
            m[r["difficolta"]] += 1
    return {"totale": len(righe), "approvati": len(approvati), "in_attesa": len(righe) - len(approvati),
            "per_materia": per_materia}


# ── revisione ─────────────────────────────────────────────────────────────────

def aggiorna_esercizio(sb, esercizio_id: str, campi: dict):
    ammessi = {k: v for k, v in campi.items() if k in _CAMPI_ESERCIZIO}
    if ammessi:
        sb.table(ESERCIZI).update(ammessi).eq("id", esercizio_id).execute()


def approva_esercizi(sb, ids: list):
    for i in range(0, len(ids), 100):
        sb.table(ESERCIZI).update({"approvato": True}).in_("id", ids[i:i + 100]).execute()


def elimina_esercizi(sb, ids: list):
    for i in range(0, len(ids), 100):
        sb.table(ESERCIZI).delete().in_("id", ids[i:i + 100]).execute()


def elimina_fonte(sb, fonte_id: str):
    """Elimina il file e (a cascata) i suoi esercizi e modelli."""
    sb.table(FONTI).delete().eq("id", fonte_id).execute()


# ── correzione di materia e scuola ────────────────────────────────────────────

def cambia_materia_scuola(sb, fonte_id: str, materia: str | None = None, scuola: str | None = None):
    """Cambia materia e/o scuola di un file e di tutti i suoi esercizi e modelli."""
    campi = {}
    if materia:
        campi["materia"] = materia
    if scuola:
        campi["scuola"] = scuola
    if campi:
        for tabella, chiave in ((FONTI, "id"), (ESERCIZI, "fonte_id"), (MODELLI, "fonte_id")):
            sb.table(tabella).update(campi).eq(chiave, fonte_id).execute()


def sposta_materia(sb, da: str, a: str):
    """Sposta tutto ciò che ha materia «da» sulla materia «a» (per correggere un errore in blocco)."""
    for tabella in (FONTI, ESERCIZI, MODELLI):
        sb.table(tabella).update({"materia": a}).eq("materia", da).execute()


# ── modelli di verifica ───────────────────────────────────────────────────────

def modelli(sb, approvato: bool | None = None) -> list:
    q = sb.table(MODELLI).select("*")
    if approvato is not None:
        q = q.eq("approvato", approvato)
    return q.order("created_at", desc=True).execute().data or []


def aggiorna_modello(sb, modello_id: str, campi: dict):
    ammessi = {k: v for k, v in campi.items() if k in ("nome", "materia", "scuola", "approvato")}
    if ammessi:
        sb.table(MODELLI).update(ammessi).eq("id", modello_id).execute()


def elimina_modello(sb, modello_id: str):
    sb.table(MODELLI).delete().eq("id", modello_id).execute()


# ── ricerca per la generazione (usata nel passo successivo) ───────────────────

def cerca_esercizi(sb, materia: str, difficolta: int, argomento: str = "", scuola: str | None = None,
                   limite: int = 12, escludi_ids: tuple = ()) -> list:
    """Esercizi approvati di una materia e di una difficoltà, filtrati per argomento (se dato).
    `scuola` è una categoria (config.categoria_scuola): quelli della stessa categoria vengono prima."""
    q = (sb.table(ESERCIZI).select("*").eq("approvato", True).eq("materia", materia)
         .eq("difficolta", difficolta).eq("ruolo", "esercizio"))
    if argomento:
        t = argomento.replace(",", " ").replace("%", " ").strip()
        q = q.or_(f"argomento.ilike.%{t}%,sezione.ilike.%{t}%,testo_latex.ilike.%{t}%")
    righe = q.limit(limite * 3).execute().data or []
    righe = [r for r in righe if r["id"] not in escludi_ids]
    if scuola:                                          # prima quelli pensati per la stessa scuola
        righe.sort(key=lambda r: 0 if r.get("scuola") == scuola else 1)
    return righe[:limite]
