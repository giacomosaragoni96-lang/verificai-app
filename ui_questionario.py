"""
ui_questionario.py — pagina pubblica «Il tuo parere su VerificAI» (?pagina=questionario). Si apre anche senza accedere.
Le domande e la pulizia delle risposte stanno in questionario.py. Anonimo: non si legge né si salva l'utente.
Chi compila le domande chiave riceve alla fine un codice (sblocco.py) per avere altre verifiche con tutte le funzioni:
il codice non è collegato alle risposte.
"""
import logging

import streamlit as st
import streamlit.components.v1 as components

import sblocco
from config import VERIFICHE_PER_CODICE
from questionario import SEZIONI, e_completo, pulisci_risposte, riga_da_inserire

logger = logging.getLogger("verificai.questionario")


def render_questionario(T: dict, supabase_admin) -> None:
    _c1, _c2, _c3 = st.columns([1, 6, 1])
    with _c2:
        st.markdown(
            f'<div style="font-family:DM Sans,sans-serif;color:{T["text"]};">'
            f'<h1 style="font-size:1.9rem;font-weight:800;margin:1rem 0 .3rem;">Il tuo parere su VerificAI</h1>'
            f'<div style="color:{T["text2"]};line-height:1.6;margin-bottom:.8rem;">'
            f'Grazie per aver provato VerificAI! Rispondi con sincerità, non esistono risposte giuste o sbagliate: ci vogliono '
            f'circa 4 minuti. <b>È anonimo</b>: non sappiamo chi sei (l\'email, in fondo, è facoltativa).</div>'
            f'<div style="background:#EFF6FF;border:1.5px solid #BFDBFE;border-radius:12px;padding:.8rem 1rem;margin-bottom:1.2rem;'
            f'color:#1E3A8A;line-height:1.5;">🎁 <b>Compilando le domande principali ricevi un codice</b>: inseriscilo in VerificAI e ottieni '
            f'<b>{VERIFICHE_PER_CODICE} verifiche con tutte le funzioni</b> (Fila B, BES/DSA, soluzioni, scheda di allenamento, logo, Word…). '
            f'Il codice non è collegato alle tue risposte, che restano anonime.</div></div>',
            unsafe_allow_html=True,
        )
        if st.session_state.get("_questionario_inviato"):
            esito = st.session_state.get("_questionario_esito") or {}
            st.success("Grazie mille! Le tue risposte ci aiutano a migliorare VerificAI.", icon="✅")
            components.html('<script>try{window.parent.localStorage.setItem("vf_feedback_ok","1");}catch(e){}</script>', height=0)   # in questo browser il riquadro del feedback non si mostra più
            if esito.get("codice"):
                st.markdown(f'<div style="font-family:DM Sans,sans-serif;color:{T["text"]};font-weight:700;margin:.6rem 0 .2rem;">'
                            f'Il tuo codice per {VERIFICHE_PER_CODICE} verifiche con tutte le funzioni:</div>', unsafe_allow_html=True)
                st.code(esito["codice"], language=None)
                st.markdown(f'<div style="font-family:DM Sans,sans-serif;color:{T["text2"]};font-size:.92rem;line-height:1.5;">'
                            f'<b>Copialo ora</b>: non verrà più mostrato. In VerificAI apri <b>«Sblocca»</b> (nella barra laterale o dal pulsante '
                            f'con il lucchetto) e incollalo in «Ho un codice». Vale una volta sola, per un solo account.</div>',
                            unsafe_allow_html=True)
            elif esito.get("mancanti"):
                st.warning("Per ricevere il codice servono anche queste risposte: " + "; ".join(esito["mancanti"]) + ".", icon="📝")
                if st.button("Completa le risposte", type="primary", key="q_completa"):
                    st.session_state["_questionario_inviato"] = False
                    st.rerun()
            elif esito.get("gia_dato"):
                st.info("Hai già ricevuto un codice in questa sessione: usa quello. Grazie ancora!", icon="🎁")
            st.markdown('<a href="/" target="_self" style="color:' + T["accent"] + ';font-weight:700;">← Torna a VerificAI</a>',
                        unsafe_allow_html=True)
            return

        with st.form("questionario_tester", border=False):
            for titolo, intro, domande in SEZIONI:
                st.subheader(titolo)
                if intro:
                    st.caption(intro)
                for d in domande:
                    k, t = f"q_{d['id']}", d["tipo"]
                    if t == "scelta":
                        st.radio(d["testo"], d["opzioni"], index=None, key=k)
                    elif t == "multi":
                        st.multiselect(d["testo"], d["opzioni"], key=k, placeholder="Scegli una o più risposte")
                    elif t == "scala":
                        st.radio(f"{d['testo']}  ({d['etichette'][0]} → {d['etichette'][1]})",
                                 list(range(d["da"], d["a"] + 1)), index=None, horizontal=True, key=k)
                    elif t == "euro":
                        st.number_input(d["testo"], min_value=0.0, max_value=10000.0, value=None, step=1.0, key=k,
                                        placeholder="es. 20")
                    elif t == "riga":
                        st.text_input(d["testo"], key=k, max_chars=120)
                    else:
                        st.text_area(d["testo"], key=k, max_chars=1500, height=90)
            st.text_input("Se vuoi essere avvisato quando ci saranno novità, lascia la tua email (facoltativo: senza, resta tutto anonimo)",
                          key="q_email_facoltativa", max_chars=254)
            invia = st.form_submit_button("Invia le risposte", type="primary", use_container_width=True)

        if invia:
            grezze = {d["id"]: st.session_state.get(f"q_{d['id']}") for _t, _i, ds in SEZIONI for d in ds}
            risposte, email = pulisci_risposte(grezze, st.session_state.get("q_email_facoltativa", ""))
            if not risposte:
                st.warning("Non hai risposto a nessuna domanda: rispondi ad almeno una prima di inviare.", icon="⚠️")
                return
            try:
                if supabase_admin is None:
                    raise RuntimeError("database non configurato")
                supabase_admin.table("questionario_tester").insert(riga_da_inserire(risposte, email)).execute()
            except Exception as e:
                logger.warning("questionario non salvato: %s", e)
                st.error("Non sono riuscito a salvare le risposte. Riprova tra un momento.")
                return
            completo, mancanti = e_completo(risposte)
            esito = {}
            if completo:
                if st.session_state.get("_questionario_codice"):          # un codice per sessione
                    esito["gia_dato"] = True
                else:
                    codice = sblocco.genera_codice(supabase_admin)
                    if codice:
                        st.session_state["_questionario_codice"] = codice
                        esito["codice"] = codice
                    else:
                        esito["mancanti"] = ["non sono riuscito a generare il codice: scrivici dal pulsante Feedback e te lo mandiamo"]
            else:
                esito["mancanti"] = mancanti
            st.session_state["_questionario_esito"] = esito
            st.session_state["_questionario_inviato"] = True
            st.rerun()
