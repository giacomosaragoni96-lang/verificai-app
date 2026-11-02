"""
cruscotto_persone.py — le schede «Persone», «Verifiche» e «Feedback» del cruscotto admin (senza Streamlit): solo lettura.

Una riga per persona (iscrizione, verifiche, funzioni, piano, inviti, crediti, costo), una per verifica, il registro eventi di ognuno,
e i testi liberi (commenti, segnalazioni, questionari). I totali sono «di sempre»: non dipendono dal periodo scelto nel cruscotto.
Le tabelle che non esistono ancora (migrazioni da eseguire a mano) danno semplicemente colonne vuote.
Le tabelle anonime (commenti, segnalazioni, questionari) restano anonime: nessuna riga viene legata a una persona.
"""
from collections import Counter, defaultdict

from cruscotto import _esclusi, _tutte, utenti


def _tutte_con_ripiego(client, tabella: str, colonne: str, opzionali: tuple = (), campo_data: str = "created_at") -> list:
    """Come `_tutte`, ma se una colonna facoltativa non esiste ancora (migrazione non eseguita) riprova senza."""
    righe = _tutte(client, tabella, colonne, None, campo_data)
    if not righe and opzionali:
        righe = _tutte(client, tabella, ",".join(c for c in colonne.split(",") if c not in opzionali), None, campo_data)
    return righe


def _conta_funzioni(tipi) -> Counter:
    """Le funzioni usate: gli eventi di accesso, scelta e paywall non sono funzioni."""
    return Counter(t for t in tipi if t and not t.startswith(("accesso:", "scelta:", "paywall:")))


def testo_funzioni(c: Counter, massimo: int = 8) -> str:
    return ", ".join(f"{t}×{n}" if n > 1 else t for t, n in c.most_common(massimo))


def anagrafica(client, escludi_emails: set | None = None, escludi_pezzi: list | None = None) -> dict:
    """{persone: [...], verifiche: [...]} — vedi i campi nel codice; ordinate dalla più recente."""
    elenco = utenti(client)
    esclusi = _esclusi(elenco, escludi_emails or set(), escludi_pezzi or [])
    email_di = {u["id"]: u["email"] for u in elenco}

    eventi = [e for e in _tutte(client, "usage_events", "user_id,tipo,modello,costo_usd,verifica_id,created_at") if e.get("user_id") not in esclusi]
    verifiche = [v for v in _tutte_con_ripiego(client, "verifiche_storico",
                                               "id,user_id,created_at,materia,argomento,scuola,modello,num_esercizi,percorso_scelto,file_mode,deleted_at,classe",
                                               opzionali=("classe",)) if v.get("user_id") not in esclusi]
    abbonamenti = _tutte(client, "subscriptions", "user_id,plan_id,status,current_period_end,provider")
    inviti = _tutte(client, "inviti", "invitante_id,invitato_id,creato_il,convalidato_il", None, "creato_il")
    codici = {r.get("user_id"): r.get("codice") for r in _tutte(client, "codici_invito", "user_id,codice", None, "creato_il")}
    bonus = Counter(r.get("user_id") for r in _tutte(client, "bonus_usati", "user_id,verifica_id", None, "creato_il"))
    sblocchi = Counter(r.get("usato_da") for r in _tutte(client, "codici_sblocco", "usato_da,usato_il", None, "creato_il") if r.get("usato_da"))

    ev_utente, ev_verifica = defaultdict(list), defaultdict(list)
    for e in eventi:
        ev_utente[e.get("user_id")].append(e)
        if e.get("verifica_id") is not None:
            ev_verifica[str(e["verifica_id"])].append(e)
    ver_utente = defaultdict(list)
    for v in verifiche:
        ver_utente[v.get("user_id")].append(v)
    piano_di = {a.get("user_id"): a.get("plan_id") or "pro" for a in abbonamenti if a.get("status") in ("active", "trialing")}
    invitato_da = {r.get("invitato_id"): r for r in inviti}
    invitati_di = defaultdict(list)
    for r in inviti:
        invitati_di[r.get("invitante_id")].append(r)

    righe = []
    for u in elenco:
        uid = u["id"]
        if uid in esclusi:
            continue
        mie = sorted(ver_utente.get(uid, []), key=lambda v: v.get("created_at") or "")
        attive = [v for v in mie if not v.get("deleted_at")]
        ev = sorted(ev_utente.get(uid, []), key=lambda e: e.get("created_at") or "")
        accessi = [e["tipo"].split(":", 1)[1] for e in ev if (e.get("tipo") or "").startswith("accesso:")]
        inv = invitato_da.get(uid)
        suoi = invitati_di.get(uid, [])
        righe.append({
            "id": uid, "email": u["email"], "iscritto": u["created_at"], "ultimo_accesso": u.get("ultimo_accesso") or "", "confermato": u.get("confermato", True),
            "verifiche": len(mie), "eliminate": len(mie) - len(attive),
            "prima_verifica": mie[0].get("created_at") if mie else "", "ultima_verifica": mie[-1].get("created_at") if mie else "",
            "materie": ", ".join(m for m, _ in Counter(v.get("materia") or "?" for v in mie).most_common(3)),
            "funzioni": _conta_funzioni(e.get("tipo") or "" for e in ev),
            "sorgente": accessi[0] if accessi else "",
            "piano": piano_di.get(uid, "free"),
            "invitato_da": email_di.get(inv.get("invitante_id"), (inv.get("invitante_id") or "")[:8]) if inv else "",
            "invito_convalidato": bool(inv and inv.get("convalidato_il")),
            "invitati": len(suoi), "invitati_convalidati": sum(1 for r in suoi if r.get("convalidato_il")),
            "invitati_elenco": [{"email": email_di.get(r.get("invitato_id"), (r.get("invitato_id") or "")[:8]), "invitato_il": r.get("creato_il") or "",
                                 "prima_verifica_il": r.get("convalidato_il") or ""} for r in suoi],
            "codice_invito": codici.get(uid, ""), "bonus_usati": bonus.get(uid, 0), "codici_sblocco": sblocchi.get(uid, 0),
            "costo_usd": round(sum(float(e.get("costo_usd") or 0) for e in ev), 4),
            "modifiche": sum(1 for e in ev if e.get("tipo") == "modifica"), "errori": sum(1 for e in ev if (e.get("tipo") or "").startswith("errore:")),
            "eventi": [{"quando": e.get("created_at") or "", "tipo": e.get("tipo") or "", "modello": e.get("modello") or "",
                        "costo_usd": float(e.get("costo_usd") or 0), "verifica_id": e.get("verifica_id")} for e in ev[-400:]],
        })
    righe.sort(key=lambda r: r["iscritto"], reverse=True)

    elenco_verifiche = []
    for v in sorted(verifiche, key=lambda v: v.get("created_at") or "", reverse=True):
        ev = ev_verifica.get(str(v.get("id")), [])
        elenco_verifiche.append({
            "id": v.get("id"), "user_id": v.get("user_id"), "email": email_di.get(v.get("user_id"), (v.get("user_id") or "")[:8]),
            "quando": v.get("created_at") or "", "materia": v.get("materia") or "", "argomento": v.get("argomento") or "", "scuola": v.get("scuola") or "",
            "classe": v.get("classe") or "", "modello": v.get("modello") or "", "esercizi": v.get("num_esercizi"),
            "percorso": v.get("percorso_scelto") or "descrizione", "file_mode": v.get("file_mode") or "", "eliminata": bool(v.get("deleted_at")),
            "funzioni": _conta_funzioni(e.get("tipo") or "" for e in ev if e.get("tipo") != "verifica"),
            "esito": next((e["tipo"].split(":", 1)[1] for e in reversed(ev) if (e.get("tipo") or "").startswith("esito:")), ""),
            "costo_usd": round(sum(float(e.get("costo_usd") or 0) for e in ev), 4),
        })
    return {"persone": righe, "verifiche": elenco_verifiche}


def latex_verifica(client, verifica_id) -> dict:
    """Il LaTeX salvato di una verifica: {latex_a, latex_b, latex_r} (vuoto se non si legge)."""
    try:
        return (client.table("verifiche_storico").select("latex_a,latex_b,latex_r").eq("id", verifica_id).limit(1).execute().data or [{}])[0]
    except Exception:
        return {}


def feedback(client) -> dict:
    """Commenti dopo lo scarico, segnalazioni e questionari per intero (tutti anonimi), dal più recente."""
    def recenti(righe):
        return sorted(righe, key=lambda r: r.get("created_at") or "", reverse=True)
    return {
        "commenti": recenti(_tutte(client, "commenti_app", "id,created_at,commento")),
        "segnalazioni": recenti(_tutte(client, "segnalazioni", "id,created_at,nota,esercizio,materia,scuola,argomento,modello,piano")),
        "questionari": recenti(_tutte_con_ripiego(client, "questionario_tester", "id,created_at,versione,risposte,email_facoltativa", ("email_facoltativa",))),
    }


def dettaglio_segnalazione(client, segnalazione_id) -> dict:
    """LaTeX e debug di una segnalazione (presenti solo se chi l'ha scritta ha lasciato la spunta)."""
    try:
        return (client.table("segnalazioni").select("latex,debug").eq("id", segnalazione_id).limit(1).execute().data or [{}])[0]
    except Exception:
        return {}
