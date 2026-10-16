"""
cruscotto.py — i numeri del servizio per l'admin (senza Streamlit): chi arriva, cosa usa, quanto costa, cosa dicono i tester.

Legge soltanto (con la chiave di servizio che l'app ha già, tramite il client Supabase passato da chi chiama): nessuna scrittura, nessuno schema nuovo.
Fonti: usage_events, verifiche_storico, aperture_app, questionario_tester, segnalazioni e l'elenco utenti di Supabase Auth.
Le attività dell'admin e degli account di prova si possono escludere (`escludi_emails`, `escludi_pezzi`): altrimenti i numeri dei primi giorni sono
quasi tutti dello sviluppatore. Le tabelle anonime (aperture, questionario, segnalazioni) restano anonime: non si lega nessuna riga a una persona.
"""
import statistics
from collections import Counter, defaultdict

PAGINA = 1000
MASSIMO_RIGHE = 50_000
_SCALE = {"utile": "Ti è servito davvero? (1-5)", "facile": "Quanto è stato facile? (1-5)"}
_MULTI = {"formula": "Formule preferite", "piaciuto": "Cosa è piaciuto di più", "funzioni_mese": "Funzioni che userebbero ogni mese",
          "non_useresti": "Funzioni che non userebbero"}
_PREZZI = {"vw_troppo_basso": "troppo basso", "vw_conveniente": "conveniente", "vw_caro": "comincia a essere caro", "vw_troppo_caro": "troppo caro"}


def _tutte(client, tabella: str, colonne: str, dal: str | None = None, campo_data: str = "created_at") -> list:
    """Tutte le righe (a pagine da 1000) di una tabella dal momento `dal`. Qualsiasi errore = elenco vuoto (la tabella può non esistere)."""
    righe, da = [], 0
    try:
        while da < MASSIMO_RIGHE:
            q = client.table(tabella).select(colonne)
            if dal:
                q = q.gte(campo_data, dal)
            dati = q.order(campo_data).range(da, da + PAGINA - 1).execute().data or []
            righe += dati
            if len(dati) < PAGINA:
                break
            da += PAGINA
    except Exception:
        return righe
    return righe


def utenti(client) -> list:
    """[{id, email, created_at}] da Supabase Auth (vuoto se non si può leggere)."""
    out, pagina = [], 1
    while pagina < 60:
        try:
            lista = client.auth.admin.list_users(page=pagina, per_page=200)
        except Exception:
            break
        if not lista:
            break
        for u in lista:
            out.append({"id": str(getattr(u, "id", "")), "email": (getattr(u, "email", "") or ""), "created_at": str(getattr(u, "created_at", "") or "")})
        if len(lista) < 200:
            break
        pagina += 1
    return out


def giorno(ts) -> str:
    return str(ts or "")[:10]


def etichetta(uid: str, email: str, mostra_email: bool) -> str:
    return (email or uid[:8]) if mostra_email else (uid or "")[:8]


def _esclusi(elenco_utenti: list, escludi_emails: set, escludi_pezzi: list) -> set:
    em = {e.lower() for e in escludi_emails or set()}
    pezzi = [p.lower() for p in (escludi_pezzi or []) if p.strip()]
    out = set()
    for u in elenco_utenti:
        mail = (u.get("email") or "").lower()
        if mail in em or any(p in mail for p in pezzi):
            out.add(u["id"])
    return out


def calcola(client, dal: str | None, escludi_emails: set | None = None, escludi_pezzi: list | None = None, mostra_email: bool = False) -> dict:
    """Tutti i numeri del cruscotto in un dizionario di dati semplici (liste e numeri), pronto da mostrare."""
    elenco = utenti(client)
    email_di = {u["id"]: u["email"] for u in elenco}
    esclusi = _esclusi(elenco, escludi_emails or set(), escludi_pezzi or [])

    eventi = [e for e in _tutte(client, "usage_events", "user_id,tipo,modello,costo_usd,verifica_id,created_at", dal) if e.get("user_id") not in esclusi]
    verifiche = [v for v in _tutte(client, "verifiche_storico", "id,user_id,created_at,materia,scuola,modello,num_esercizi,percorso_scelto,file_mode,deleted_at", dal)
                 if v.get("user_id") not in esclusi]
    aperture = _tutte(client, "aperture_app", "src,tappa,created_at", dal)
    questionari = _tutte(client, "questionario_tester", "versione,risposte,created_at", dal)
    segnalazioni = _tutte(client, "segnalazioni", "id,created_at,materia,nota", dal)

    nuovi = [u for u in elenco if u["id"] not in esclusi and (not dal or (u["created_at"] or "") >= dal)]
    attivi = {e["user_id"] for e in eventi if e.get("user_id")}
    costo_tot = sum(float(e.get("costo_usd") or 0) for e in eventi)
    n_verifiche = len(verifiche)
    aperture_login = [a for a in aperture if (a.get("tappa") or "login") == "login"]

    kpi = {
        "aperture": len(aperture_login), "iscritti": len(nuovi), "attivi": len(attivi), "verifiche": n_verifiche,
        "costo_usd": round(costo_tot, 4), "costo_per_verifica_usd": round(costo_tot / n_verifiche, 4) if n_verifiche else 0.0,
        "questionari": len(questionari), "bot": sum(1 for a in aperture if a.get("tappa") == "bot"),
    }

    # ── da dove arrivano: aperture → entrati → prima verifica → ne fanno più di una ──
    primo = {}
    for e in sorted(eventi, key=lambda x: x.get("created_at") or ""):
        t = e.get("tipo") or ""
        if t.startswith("accesso:") and e.get("user_id") not in primo:
            primo[e["user_id"]] = t.split(":", 1)[1] or "diretto"
    per_utente = Counter(v.get("user_id") for v in verifiche)
    src_aperture = Counter((a.get("src") or "diretto") for a in aperture_login)
    sorgenti = sorted(set(src_aperture) | set(primo.values()))
    imbuto = []
    for s in sorgenti:
        entrati = [u for u, x in primo.items() if x == s]
        con_una = [u for u in entrati if per_utente.get(u, 0) >= 1]
        con_piu = [u for u in entrati if per_utente.get(u, 0) >= 2]
        imbuto.append({"sorgente": s, "aperture": src_aperture.get(s, 0), "entrati": len(entrati), "prima_verifica": len(con_una), "piu_di_una": len(con_piu)})
    imbuto.sort(key=lambda r: -(r["aperture"] + r["entrati"]))

    # ── cosa usano ──
    conta, persone = Counter(), defaultdict(set)
    for e in eventi:
        t = (e.get("tipo") or "").split(":", 1)[0] if (e.get("tipo") or "").startswith(("paywall:", "accesso:")) else (e.get("tipo") or "")
        conta[t] += 1
        persone[t].add(e.get("user_id"))
    funzioni = [{"funzione": t, "volte": n, "persone": len(persone[t])} for t, n in conta.most_common()]
    scelte = {"descrizione": conta.get("scelta:crea", 0), "impagina": conta.get("scelta:impagina", 0)}
    percorsi = Counter((v.get("percorso_scelto") or "descrizione") for v in verifiche)

    # ── quanto costa ──
    per_giorno, per_modello, per_persona = defaultdict(float), defaultdict(float), defaultdict(float)
    for e in eventi:
        c = float(e.get("costo_usd") or 0)
        if c:
            per_giorno[giorno(e.get("created_at"))] += c
            per_modello[e.get("modello") or "?"] += c
            per_persona[e.get("user_id") or "?"] += c
    costi = {
        "giorno": sorted(({"giorno": g, "usd": round(c, 4)} for g, c in per_giorno.items()), key=lambda r: r["giorno"]),
        "modello": sorted(({"modello": m, "usd": round(c, 4)} for m, c in per_modello.items()), key=lambda r: -r["usd"]),
        "persone": [{"utente": etichetta(u, email_di.get(u, ""), mostra_email), "usd": round(c, 4)} for u, c in sorted(per_persona.items(), key=lambda x: -x[1])[:8]],
    }

    # ── ritorno ──
    giorni_utente = defaultdict(set)
    for v in verifiche:
        giorni_utente[v.get("user_id")].add(giorno(v.get("created_at")))
    con_verifica = len(giorni_utente)
    tornati = sum(1 for g in giorni_utente.values() if len(g) >= 2)
    ritorno = {"con_verifica": con_verifica, "tornati": tornati, "percentuale": round(100 * tornati / con_verifica, 1) if con_verifica else 0.0}

    # ── questionario ──
    risp = [q.get("risposte") or {} for q in questionari]
    medie = {}
    for qid, nome in _SCALE.items():
        vals = [r[qid] for r in risp if isinstance(r.get(qid), (int, float))]
        if vals:
            medie[nome] = round(sum(vals) / len(vals), 2)
    raccomanda = [r["consiglieresti"] for r in risp if isinstance(r.get("consiglieresti"), (int, float))]
    nps = None
    if raccomanda:
        nps = round(100 * (sum(1 for x in raccomanda if x >= 9) - sum(1 for x in raccomanda if x <= 6)) / len(raccomanda))
    multi = {}
    for qid, nome in _MULTI.items():
        c = Counter()
        for r in risp:
            v = r.get(qid)
            for x in (v if isinstance(v, list) else ([v] if isinstance(v, str) else [])):
                c[x] += 1
        multi[nome] = c.most_common()
    prezzi = {}
    for qid, nome in _PREZZI.items():
        vals = [float(r[qid]) for r in risp if isinstance(r.get(qid), (int, float))]
        if vals:
            prezzi[nome] = {"mediana": round(statistics.median(vals), 2), "risposte": len(vals)}
    questionario = {
        "risposte": len(risp), "medie": medie, "nps": nps, "multi": multi, "prezzi": prezzi,
        "manca": [str(r["manca"]).strip()[:240] for r in risp if len(str(r.get("manca") or "").strip()) > 10][-12:],
    }

    # ── qualità percepita: «Com'è questa verifica?» per modello e per materia ──
    materia_di = {str(v.get("id")): (v.get("materia") or "?") for v in verifiche}
    per_modello, per_materia = defaultdict(Counter), defaultdict(Counter)
    for e in eventi:
        t = e.get("tipo") or ""
        if t.startswith("esito:"):
            esito = t.split(":", 1)[1]
            per_modello[e.get("modello") or "?"][esito] += 1
            per_materia[materia_di.get(str(e.get("verifica_id")), "?")][esito] += 1

    def _righe(d):
        out = []
        for nome, c in sorted(d.items(), key=lambda x: -sum(x[1].values())):
            tot = sum(c.values())
            out.append({"nome": nome, "risposte": tot, "pronta": c.get("pronta", 0), "ritoccare": c.get("ritoccare", 0), "non_usabile": c.get("non_usabile", 0),
                        "pct_pronta": round(100 * c.get("pronta", 0) / tot) if tot else 0})
        return out
    qualita = {"modello": _righe(per_modello), "materia": _righe(per_materia), "totale": sum(sum(c.values()) for c in per_modello.values())}

    # ── operativo ──
    errori = [e for e in eventi if (e.get("tipo") or "").startswith("errore:")]
    ultimi = [{"quando": str(e.get("created_at") or "")[:16].replace("T", " "), "tipo": e.get("tipo"), "utente": etichetta(e.get("user_id") or "", email_di.get(e.get("user_id"), ""), mostra_email)}
              for e in sorted(eventi, key=lambda x: x.get("created_at") or "", reverse=True)[:30]]
    operativo = {
        "errori": len(errori), "ultimi_errori": [{"quando": str(e.get("created_at") or "")[:16].replace("T", " "), "tipo": e.get("tipo")} for e in errori[-8:]],
        "segnalazioni": len(segnalazioni), "ultime_segnalazioni": [{"quando": giorno(s.get("created_at")), "materia": s.get("materia"), "nota": str(s.get("nota") or "")[:200]}
                                                                 for s in segnalazioni[-6:]],
        "ultimi_eventi": ultimi,
    }
    return {"kpi": kpi, "imbuto": imbuto, "funzioni": funzioni, "scelte": scelte, "percorsi": dict(percorsi), "costi": costi, "ritorno": ritorno,
            "questionario": questionario, "qualita": qualita, "operativo": operativo, "utenti_esclusi": len(esclusi), "utenti_totali": len(elenco)}
