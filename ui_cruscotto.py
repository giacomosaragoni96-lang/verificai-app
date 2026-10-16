"""
ui_cruscotto.py — la pagina «Cruscotto» (solo admin, stage CRUSCOTTO): solo interfaccia, i calcoli stanno in cruscotto.py.
"""
from datetime import datetime, timedelta, timezone

import streamlit as st

import cruscotto

LANCIO = "2026-10-15T00:00:00+00:00"
PERIODI = ["Oggi", "Ultimi 7 giorni", "Ultimi 30 giorni", "Dal lancio (15 ottobre)", "Tutto"]


def _dal(periodo: str):
    adesso = datetime.now(timezone.utc)
    if periodo == "Oggi":
        return adesso.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    if periodo == "Ultimi 7 giorni":
        return (adesso - timedelta(days=7)).isoformat()
    if periodo == "Ultimi 30 giorni":
        return (adesso - timedelta(days=30)).isoformat()
    if periodo.startswith("Dal lancio"):
        return LANCIO
    return None


@st.cache_data(ttl=300, show_spinner=False)
def _dati(_client, dal, escludi_emails: tuple, escludi_pezzi: tuple, mostra_email: bool) -> dict:
    return cruscotto.calcola(_client, dal, set(escludi_emails), list(escludi_pezzi), mostra_email)


def _pct(a: int, b: int) -> str:
    return f"{round(100 * a / b)}%" if b else "—"


def _sezione(titolo: str, sottotitolo: str = ""):
    st.markdown(f"#### {titolo}")
    if sottotitolo:
        st.caption(sottotitolo)


def render_cruscotto(T: dict, client, esci, admin_emails: set) -> None:
    import pandas as pd

    if st.button("← Indietro", key="cruscotto_indietro", type="tertiary"):
        esci()
    st.markdown(f'<div style="text-align:center;margin:.2rem 0 1rem;"><div style="font-family:DM Sans,sans-serif;font-size:1.7rem;font-weight:800;'
                f'letter-spacing:-.025em;color:{T["text"]};">Cruscotto</div>'
                f'<div style="font-size:.9rem;color:{T["text2"]};font-family:DM Sans,sans-serif;">Chi arriva, cosa usa, quanto costa, cosa dicono i tester.</div></div>',
                unsafe_allow_html=True)

    c1, c2 = st.columns([2, 3], gap="medium")
    periodo = c1.selectbox("Periodo", PERIODI, index=3, key="cr_periodo")
    escludi_mie = c2.toggle("Escludi le mie attività e gli account di prova", value=True, key="cr_escludi",
                            help="Toglie dai numeri l'admin e le email che contengono i pezzi qui sotto: i primi giorni sono quasi tutte prove tue.")
    c3, c4 = st.columns([3, 2], gap="medium")
    pezzi_txt = c3.text_input("Escludi anche le email che contengono (separate da virgola)", value="+prova, +test", key="cr_pezzi", disabled=not escludi_mie)
    mostra_email = c4.toggle("Mostra le email", value=False, key="cr_email", help="Di default si vedono solo i primi caratteri dell'identificativo.")
    if st.button("Aggiorna i dati", key="cr_aggiorna", icon=":material/refresh:"):
        _dati.clear()
        st.rerun()

    emails = tuple(sorted(admin_emails)) if escludi_mie else ()
    pezzi = tuple(p.strip() for p in pezzi_txt.split(",") if p.strip()) if escludi_mie else ()
    with st.spinner("Leggo i dati…"):
        d = _dati(client, _dal(periodo), emails, pezzi, mostra_email)

    k = d["kpi"]
    if escludi_mie:
        st.caption(f"Escluse {d['utenti_esclusi']} persone su {d['utenti_totali']} (admin e prove). I dati si aggiornano ogni 5 minuti.")
    cols = st.columns(6)
    cols[0].metric("Aperture dell'app", k["aperture"], help="Quante volte qualcuno ha visto la schermata di accesso (bot esclusi).")
    cols[1].metric("Iscritti nuovi", k["iscritti"])
    cols[2].metric("Attivi", k["attivi"], help="Persone con almeno un'azione nel periodo.")
    cols[3].metric("Verifiche create", k["verifiche"])
    cols[4].metric("Costo AI", f"${k['costo_usd']:.2f}", help=f"Circa ${k['costo_per_verifica_usd']:.3f} a verifica.")
    cols[5].metric("Questionari", k["questionari"])

    with st.container(border=True):
        _sezione("Da dove arrivano", "Aperture della schermata di accesso, persone entrate (per link di provenienza) e quante hanno creato una verifica.")
        if d["imbuto"]:
            righe = [{"Sorgente": r["sorgente"], "Aperture": r["aperture"], "Entrati": r["entrati"], "Entrati su aperture": _pct(r["entrati"], r["aperture"]),
                      "Prima verifica": r["prima_verifica"], "Prima verifica su entrati": _pct(r["prima_verifica"], r["entrati"]), "Più di una": r["piu_di_una"]}
                     for r in d["imbuto"]]
            st.dataframe(pd.DataFrame(righe), hide_index=True, use_container_width=True)
        else:
            st.caption("Nessun dato nel periodo.")

    a, b = st.columns(2, gap="medium")
    with a, st.container(border=True):
        _sezione("Cosa usano", "Quante volte e da quante persone.")
        if d["funzioni"]:
            st.dataframe(pd.DataFrame([{"Funzione": f["funzione"], "Volte": f["volte"], "Persone": f["persone"]} for f in d["funzioni"]]),
                         hide_index=True, use_container_width=True, height=330)
        s = d["scelte"]
        st.caption(f"Prima scelta: descrizione {s['descrizione']} · impagina {s['impagina']}. Verifiche create: " +
                   ", ".join(f"{p or 'descrizione'} {n}" for p, n in d["percorsi"].items()))
    with b, st.container(border=True):
        _sezione("Quanto costa", "Dollari per giorno e per modello.")
        if d["costi"]["giorno"]:
            st.bar_chart(pd.DataFrame(d["costi"]["giorno"]).set_index("giorno")["usd"], height=180)
            st.dataframe(pd.DataFrame(d["costi"]["modello"]).rename(columns={"modello": "Modello", "usd": "USD"}), hide_index=True, use_container_width=True)
            st.caption("Chi consuma di più: " + ", ".join(f"{p['utente']} ${p['usd']:.2f}" for p in d["costi"]["persone"][:5]))
        else:
            st.caption("Nessun costo registrato nel periodo.")

    r = d["ritorno"]
    with st.container(border=True):
        _sezione("Ritorno")
        st.write(f"Persone con almeno una verifica: **{r['con_verifica']}** · tornate in un altro giorno: **{r['tornati']}** ({r['percentuale']}%)")

    q = d["questionario"]
    with st.container(border=True):
        _sezione("Questionario", f"{q['risposte']} risposte nel periodo (anonime).")
        if q["risposte"]:
            m1, m2, m3 = st.columns(3)
            for col, (nome, val) in zip((m1, m2), list(q["medie"].items())[:2]):
                col.metric(nome, val)
            m3.metric("Consiglierebbero (NPS)", "—" if q["nps"] is None else q["nps"])
            for nome, voci in q["multi"].items():
                if voci:
                    st.markdown(f"**{nome}**")
                    st.dataframe(pd.DataFrame(voci, columns=["Risposta", "Persone"]), hide_index=True, use_container_width=True)
            if q["prezzi"]:
                st.markdown("**Prezzo annuo (mediana)**")
                st.dataframe(pd.DataFrame([{"Soglia": n, "Mediana €": v["mediana"], "Risposte": v["risposte"]} for n, v in q["prezzi"].items()]),
                             hide_index=True, use_container_width=True)
            if q["manca"]:
                st.markdown("**Cosa manca (ultime risposte)**")
                for t in reversed(q["manca"]):
                    st.markdown(f"- {t}")

    o = d["operativo"]
    with st.container(border=True):
        _sezione("Operativo", f"Errori registrati: {o['errori']} · segnalazioni: {o['segnalazioni']}")
        if o["ultimi_errori"]:
            st.dataframe(pd.DataFrame(o["ultimi_errori"]), hide_index=True, use_container_width=True)
        for sgn in o["ultime_segnalazioni"]:
            st.markdown(f"- **{sgn['quando']}** · {sgn['materia'] or ''}: {sgn['nota']}")
        with st.expander("Ultimi eventi"):
            st.dataframe(pd.DataFrame(o["ultimi_eventi"]), hide_index=True, use_container_width=True)
