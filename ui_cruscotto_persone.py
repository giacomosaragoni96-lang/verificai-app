"""
ui_cruscotto_persone.py — schede «Persone», «Verifiche» e «Feedback» del cruscotto (solo admin): solo interfaccia, i dati vengono da cruscotto_persone.py.
"""
from datetime import datetime, timedelta, timezone

import streamlit as st

import cruscotto_persone as cp

try:
    from zoneinfo import ZoneInfo
    _ROMA = ZoneInfo("Europe/Rome")
except Exception:                       # senza database dei fusi si resta in UTC
    _ROMA = timezone.utc


@st.cache_data(ttl=300, show_spinner=False)
def _anagrafica(_client, escludi_emails: tuple, escludi_pezzi: tuple) -> dict:
    return cp.anagrafica(_client, set(escludi_emails), list(escludi_pezzi))


@st.cache_data(ttl=300, show_spinner=False)
def _feedback(_client) -> dict:
    return cp.feedback(_client)


@st.cache_data(ttl=300, max_entries=30, show_spinner=False)
def _latex(_client, verifica_id) -> dict:
    return cp.latex_verifica(_client, verifica_id)


@st.cache_data(ttl=300, max_entries=30, show_spinner=False)
def _dettaglio_segnalazione(_client, segnalazione_id) -> dict:
    return cp.dettaglio_segnalazione(_client, segnalazione_id)


def svuota_cache() -> None:
    for f in (_anagrafica, _feedback, _latex, _dettaglio_segnalazione):
        f.clear()


def _data(ts, con_ora: bool = True) -> str:
    """«18/10/2026 14:32» nell'ora italiana (vuoto se manca)."""
    if not ts:
        return ""
    try:
        d = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return d.astimezone(_ROMA).strftime("%d/%m/%Y %H:%M" if con_ora else "%d/%m/%Y")
    except Exception:
        return str(ts)[:16].replace("T", " ")


def _chi(email: str, mostra_email: bool) -> str:
    return email if mostra_email or "@" not in email else email.split("@")[0][:3] + "…@" + email.split("@")[1]


def _senza_immagini(latex: str) -> str:
    """Le righe %IMG_B64 (logo e figure incorporati) sono lunghissime: nella lettura si riassumono, il file scaricato resta intero."""
    out = []
    for riga in (latex or "").splitlines():
        if riga.startswith("%IMG_B64:"):
            nome = riga.split(":", 2)[1] if riga.count(":") >= 2 else "immagine"
            out.append(f"% [immagine incorporata: {nome}, {len(riga) // 1365} KB circa]")
        else:
            out.append(riga)
    return "\n".join(out)


def _vedi_verifica(client, v: dict, mostra_email: bool, chiave: str) -> None:
    """Scheda di una verifica: dati, funzioni usate e LaTeX (Fila A, Fila B, BES/DSA se salvate)."""
    st.markdown(f"##### {v['argomento'] or 'Senza titolo'}")
    st.caption(f"{_data(v['quando'])} · {_chi(v['email'], mostra_email)} · {v['materia'] or '—'} · {v['scuola'] or '—'}"
               + (f" · classe {v['classe']}" if v["classe"] else "") + f" · {v['modello'] or 'modello ?'} · {v['esercizi'] or '?'} esercizi · percorso {v['percorso']}"
               + (" · ELIMINATA dall'utente" if v["eliminata"] else "") + (f" · esito: {v['esito']}" if v["esito"] else "") + f" · costo ${v['costo_usd']:.3f}")
    st.caption("Funzioni usate: " + (cp.testo_funzioni(v["funzioni"]) or "nessuna oltre alla creazione"))
    dati = _latex(client, v["id"])
    scelte = {lab: dati.get(k) for k, lab in (("latex_a", "Fila A"), ("latex_b", "Fila B"), ("latex_r", "BES/DSA")) if dati.get(k)}
    if not scelte:
        st.info("Il LaTeX di questa verifica non è salvato (o non si riesce a leggere).")
        return
    lab = st.segmented_control("Versione", list(scelte), default=list(scelte)[0], key=f"cr_ver_{chiave}", label_visibility="collapsed") or list(scelte)[0]
    testo = scelte[lab]
    st.download_button("Scarica il .tex", testo, file_name=f"verifica_{v['id']}_{lab.replace(' ', '').replace('/', '')}.tex", mime="application/x-tex", key=f"cr_dl_{chiave}_{lab}")
    st.code(_senza_immagini(testo), language="latex", line_numbers=False)


def _tabella_verifiche(client, righe: list, mostra_email: bool, chiave: str, con_persona: bool = True) -> None:
    """Elenco di verifiche; cliccando una riga si apre il LaTeX sotto."""
    import pandas as pd
    if not righe:
        st.caption("Nessuna verifica.")
        return
    df = pd.DataFrame([{**({"Persona": _chi(v["email"], mostra_email)} if con_persona else {}),
                        "Quando": _data(v["quando"]), "Materia": v["materia"], "Argomento": v["argomento"], "Scuola": v["scuola"], "Classe": v["classe"],
                        "Modello": v["modello"], "Esercizi": v["esercizi"], "Percorso": v["percorso"], "Funzioni usate": cp.testo_funzioni(v["funzioni"]),
                        "Esito": v["esito"], "Costo $": v["costo_usd"], "Eliminata": "sì" if v["eliminata"] else ""} for v in righe])
    sel = st.dataframe(df, hide_index=True, width="stretch", height=min(420, 40 + 35 * len(df)), on_select="rerun", selection_mode="single-row", key=f"cr_tab_{chiave}")
    st.caption("Clicca una riga per leggere il LaTeX.")
    if sel.selection.rows:
        _vedi_verifica(client, righe[sel.selection.rows[0]], mostra_email, chiave)


def _scheda_persona(client, p: dict, verifiche: list, mostra_email: bool) -> None:
    import pandas as pd
    st.markdown(f"#### {_chi(p['email'], mostra_email)}")
    st.caption(f"Iscritto il {_data(p['iscritto'])} · ultimo accesso {_data(p['ultimo_accesso']) or '—'} · piano {p['piano']}"
               + (f" · arrivato da «{p['sorgente']}»" if p["sorgente"] else "") + ("" if p["confermato"] else " · email NON confermata"))
    c = st.columns(5)
    c[0].metric("Verifiche", p["verifiche"], help=f"{p['eliminate']} eliminate dall'utente (contano comunque nel tetto)." if p["eliminate"] else None)
    c[1].metric("Modifiche con l'AI", p["modifiche"])
    c[2].metric("Costo AI", f"${p['costo_usd']:.2f}")
    c[3].metric("Colleghi invitati", f"{p['invitati']}", help=f"{p['invitati_convalidati']} hanno creato la prima verifica.")
    c[4].metric("Crediti usati", p["bonus_usati"], help=f"Codici questionario riscattati: {p['codici_sblocco']}.")
    if p["invitato_da"]:
        st.write(f"Invitato da **{_chi(p['invitato_da'], mostra_email)}**" + (" (ha poi creato la prima verifica)" if p["invito_convalidato"] else " (non ha ancora creato verifiche)"))
    if p["invitati_elenco"]:
        st.markdown("**Ha invitato**")
        st.dataframe(pd.DataFrame([{"Collega": _chi(i["email"], mostra_email), "Invitato il": _data(i["invitato_il"]), "Prima verifica il": _data(i["prima_verifica_il"]) or "ancora no"}
                                   for i in p["invitati_elenco"]]), hide_index=True, width="stretch")
    if p["codice_invito"]:
        st.caption(f"Codice invito: {p['codice_invito']}")
    st.markdown(f"**Funzioni usate:** {cp.testo_funzioni(p['funzioni'], 20) or 'nessuna'}")
    st.markdown("**Verifiche create**")
    _tabella_verifiche(client, verifiche, mostra_email, f"p_{p['id'][:8]}", con_persona=False)
    with st.expander(f"Registro delle azioni ({len(p['eventi'])} ultime)"):
        if p["eventi"]:
            st.dataframe(pd.DataFrame([{"Quando": _data(e["quando"]), "Azione": e["tipo"], "Modello": e["modello"], "Costo $": e["costo_usd"] or None, "Verifica": e["verifica_id"]}
                                       for e in reversed(p["eventi"])]), hide_index=True, width="stretch", height=320)


def render_persone(client, emails: tuple, pezzi: tuple, mostra_email: bool) -> None:
    import pandas as pd
    with st.spinner("Leggo le persone…"):
        a = _anagrafica(client, emails, pezzi)
    persone, verifiche = a["persone"], a["verifiche"]
    adesso = datetime.now(timezone.utc)
    sette = (adesso - timedelta(days=7)).isoformat()
    con_ver = [p for p in persone if p["verifiche"]]
    c = st.columns(5)
    c[0].metric("Iscritti", len(persone))
    c[1].metric("Iscritti ultimi 7 giorni", sum(1 for p in persone if p["iscritto"] >= sette))
    c[2].metric("Con almeno una verifica", len(con_ver), help=f"{round(100 * len(con_ver) / len(persone))}% degli iscritti" if persone else None)
    c[3].metric("Verifiche create", sum(p["verifiche"] for p in persone))
    c[4].metric("Inviti andati a buon fine", sum(p["invitati_convalidati"] for p in persone), help="Colleghi invitati che hanno poi creato la prima verifica.")

    per_giorno = {}
    for p in persone:
        g = (p["iscritto"] or "")[:10]
        if g:
            per_giorno[g] = per_giorno.get(g, 0) + 1
    if per_giorno:
        st.markdown("**Iscrizioni per giorno**")
        st.bar_chart(pd.Series(per_giorno).sort_index(), height=140)

    f1, f2, f3 = st.columns([3, 2, 2], gap="medium")
    cerca = f1.text_input("Cerca (email, materia, provenienza)", key="cr_p_cerca").strip().lower()
    filtro = f2.selectbox("Mostra", ["Tutti", "Con verifiche", "Senza verifiche", "Hanno invitato", "Invitati da un collega", "Piano non free"], key="cr_p_filtro")
    ordine = f3.selectbox("Ordina per", ["Iscrizione (recenti)", "Ultima verifica", "Più verifiche", "Ultimo accesso"], key="cr_p_ordine")
    elenco = [p for p in persone if (not cerca or cerca in f"{p['email']} {p['materie']} {p['sorgente']}".lower())
              and {"Tutti": True, "Con verifiche": p["verifiche"] > 0, "Senza verifiche": p["verifiche"] == 0, "Hanno invitato": p["invitati"] > 0,
                   "Invitati da un collega": bool(p["invitato_da"]), "Piano non free": p["piano"] != "free"}[filtro]]
    chiave_ord = {"Iscrizione (recenti)": lambda p: p["iscritto"], "Ultima verifica": lambda p: p["ultima_verifica"] or "",
                  "Più verifiche": lambda p: p["verifiche"], "Ultimo accesso": lambda p: p["ultimo_accesso"] or ""}[ordine]
    elenco.sort(key=chiave_ord, reverse=True)
    if not elenco:
        st.caption("Nessuna persona con questi filtri.")
        return
    df = pd.DataFrame([{"Email": _chi(p["email"], mostra_email), "Iscritto il": _data(p["iscritto"], False), "Ultimo accesso": _data(p["ultimo_accesso"]),
                        "Verifiche": p["verifiche"], "Prima verifica": _data(p["prima_verifica"]), "Ultima verifica": _data(p["ultima_verifica"]),
                        "Materie": p["materie"], "Funzioni usate": cp.testo_funzioni(p["funzioni"], 6), "Arrivato da": p["sorgente"], "Piano": p["piano"],
                        "Invitato da": _chi(p["invitato_da"], mostra_email), "Ha invitato": p["invitati"] or None, "…di cui attivi": p["invitati_convalidati"] or None,
                        "Costo $": p["costo_usd"], "Email confermata": "sì" if p["confermato"] else "NO"} for p in elenco])
    st.caption(f"{len(elenco)} persone. Clicca una riga per vedere tutto di quella persona.")
    sel = st.dataframe(df, hide_index=True, width="stretch", height=min(460, 40 + 35 * len(df)), on_select="rerun", selection_mode="single-row", key="cr_tab_persone")
    if sel.selection.rows:
        p = elenco[sel.selection.rows[0]]
        with st.container(border=True):
            _scheda_persona(client, p, [v for v in verifiche if v["user_id"] == p["id"]], mostra_email)


def render_verifiche(client, emails: tuple, pezzi: tuple, mostra_email: bool) -> None:
    with st.spinner("Leggo le verifiche…"):
        verifiche = _anagrafica(client, emails, pezzi)["verifiche"]
    if not verifiche:
        st.caption("Nessuna verifica.")
        return
    attive = [v for v in verifiche if not v["eliminata"]]
    c = st.columns(4)
    c[0].metric("Verifiche", len(verifiche), help=f"{len(verifiche) - len(attive)} eliminate dagli utenti.")
    c[1].metric("Persone", len({v["user_id"] for v in verifiche}))
    c[2].metric("Con Fila B / BES / soluzioni…", sum(1 for v in verifiche if v["funzioni"]))
    c[3].metric("Costo AI", f"${sum(v['costo_usd'] for v in verifiche):.2f}")

    f1, f2, f3 = st.columns([3, 2, 2], gap="medium")
    cerca = f1.text_input("Cerca (argomento, persona, scuola, classe)", key="cr_v_cerca").strip().lower()
    materie = sorted({v["materia"] for v in verifiche if v["materia"]})
    materia = f2.multiselect("Materia", materie, key="cr_v_materia")
    funzioni = sorted({t for v in verifiche for t in v["funzioni"]})
    funzione = f3.multiselect("Hanno usato", funzioni, key="cr_v_funzione")
    mostra_el = st.toggle("Mostra anche quelle eliminate dagli utenti", value=True, key="cr_v_eliminate")
    elenco = [v for v in verifiche if (mostra_el or not v["eliminata"])
              and (not cerca or cerca in f"{v['argomento']} {v['email']} {v['scuola']} {v['classe']} {v['materia']}".lower())
              and (not materia or v["materia"] in materia) and all(f in v["funzioni"] for f in funzione)]
    st.caption(f"{len(elenco)} verifiche.")
    _tabella_verifiche(client, elenco[:500], mostra_email, "tutte")
    if len(elenco) > 500:
        st.caption("Mostro le 500 più recenti: restringi con i filtri.")


def render_feedback(client) -> None:
    import pandas as pd
    with st.spinner("Leggo i commenti…"):
        f = _feedback(client)
    st.caption("Tutto anonimo: nessuna riga è legata a una persona.")

    with st.container(border=True):
        st.markdown(f"#### Commenti dopo lo scarico ({len(f['commenti'])})")
        if f["commenti"]:
            st.dataframe(pd.DataFrame([{"Quando": _data(r["created_at"]), "Commento": r.get("commento")} for r in f["commenti"]]), hide_index=True, width="stretch",
                         height=min(420, 40 + 35 * len(f["commenti"])), column_config={"Commento": st.column_config.TextColumn(width="large")})
        else:
            st.caption("Ancora nessun commento (o la tabella commenti_app non esiste: migrazione_commenti.sql).")

    with st.container(border=True):
        st.markdown(f"#### Segnalazioni «Qualcosa non va» ({len(f['segnalazioni'])})")
        for s in f["segnalazioni"][:60]:
            tit = f"{_data(s['created_at'])} · {s.get('materia') or '—'} · {s.get('argomento') or 'senza titolo'}" + (f" · esercizio {s['esercizio']}" if s.get("esercizio") else "")
            with st.expander(tit):
                st.write(s.get("nota") or "(nessuna nota)")
                st.caption(f"{s.get('scuola') or '—'} · {s.get('modello') or 'modello ?'} · piano {s.get('piano') or '?'}")
                if st.button("Carica LaTeX e debug", key=f"cr_sg_{s['id']}"):
                    d = _dettaglio_segnalazione(client, s["id"])
                    if d.get("latex"):
                        st.code(_senza_immagini(d["latex"]), language="latex")
                    if d.get("debug"):
                        st.text_area("Debug della generazione", d["debug"], height=240, key=f"cr_sgd_{s['id']}")
                    if not d.get("latex") and not d.get("debug"):
                        st.caption("Chi l'ha scritta non ha allegato il testo.")
        if not f["segnalazioni"]:
            st.caption("Nessuna segnalazione.")

    with st.container(border=True):
        st.markdown(f"#### Questionari completi ({len(f['questionari'])})")
        if f["questionari"]:
            righe = []
            for q in f["questionari"]:
                r = {"Quando": _data(q["created_at"]), "Email (facoltativa)": q.get("email_facoltativa") or ""}
                for k, v in (q.get("risposte") or {}).items():
                    r[k] = ", ".join(map(str, v)) if isinstance(v, list) else v
                righe.append(r)
            st.dataframe(pd.DataFrame(righe), hide_index=True, width="stretch", height=min(460, 40 + 35 * len(righe)))
        else:
            st.caption("Ancora nessuna risposta.")
