"""
ui_sblocco.py — pagina «Sblocca altre verifiche complete» (al posto della pagina dei piani, quando i prezzi non sono visibili).
Spiega lo scambio (questionario completo → codice → verifiche con tutte le funzioni) e raccoglie il codice.
"""
import streamlit as st

from config import ETICHETTE_FUNZIONI, VERIFICHE_PER_CODICE, BONUS_PER_INVITO
from ui_inviti import render_invito


def render_sblocco(T: dict, on_back, funzione, residui: int, on_riscatta, invito=None) -> None:
    """
    on_back     : callable che riporta alla pagina precedente
    funzione    : la funzione bloccata che ha portato qui (per il titolo), se c'è
    residui     : verifiche complete ancora a disposizione
    on_riscatta : callable(codice) -> (ok, messaggio)
    invito      : {"link", "convalidati", "residui"} se gli inviti sono attivi, altrimenti None
    """
    if st.button("← Indietro", key="sb_indietro", type="tertiary"):
        on_back()
        return
    acc = T["accent"]
    st.markdown(
        f'<div style="font-family:DM Sans,sans-serif;color:{T["text"]};max-width:760px;margin:.4rem auto 0;">'
        f'<h1 style="font-size:1.9rem;font-weight:800;margin:.4rem 0 .4rem;">Sblocca altre verifiche con tutte le funzioni</h1>'
        f'<div style="color:{T["text2"]};line-height:1.6;">La tua prima verifica aveva tutto il kit. Per le prossime resta '
        f'tutto il necessario per crearle e modificarle; le funzioni extra (Fila B, BES/DSA, soluzioni, scheda di allenamento, griglia, '
        f'logo, Word, caricamento di appunti) le ottieni così: <b>{VERIFICHE_PER_CODICE} verifiche complete</b> compilando il questionario'
        + (f', e <b>altre {BONUS_PER_INVITO} per ogni collega</b> che inviti.' if invito else '.') + '</div></div>',
        unsafe_allow_html=True)
    if funzione in ETICHETTE_FUNZIONI:
        st.info(f"Ti serve {ETICHETTE_FUNZIONI[funzione]}? Fa parte delle funzioni che si sbloccano qui sotto.", icon="🔒")
    _c1, _c2, _c3 = st.columns([1, 6, 1])
    with _c2:
        passi = [("1", "Compila il questionario completo", "Circa 4 minuti, anonimo: ci dici cosa ti è servito e cosa manca."),
                 ("2", "Ricevi un codice", f"Alla fine compare un codice per {VERIFICHE_PER_CODICE} verifiche con tutte le funzioni."),
                 ("3", "Inseriscilo qui sotto", "Poi usi una verifica completa su quella che hai appena creato, su una a tua scelta in «Le mie verifiche» o su una nuova.")]
        for n, t, d in passi:
            st.markdown(
                f'<div style="display:flex;gap:.8rem;align-items:center;margin:.5rem 0;font-family:DM Sans,sans-serif;">'
                f'<div style="flex:0 0 2.2rem;height:2.2rem;border-radius:50%;background:{acc};color:#fff;font-weight:800;display:flex;'
                f'align-items:center;justify-content:center;">{n}</div>'
                f'<div style="color:{T["text"]};line-height:1.35;"><b>{t}</b><br><span style="color:{T["text2"]};font-size:.92rem;">{d}</span></div></div>',
                unsafe_allow_html=True)
        st.markdown(
            f'<a href="?pagina=questionario" target="_blank" rel="noopener" style="display:block;text-align:center;margin:1rem 0 1.2rem;'
            f'padding:.8rem 1rem;border-radius:12px;background:linear-gradient(135deg,{acc},{T["accent2"]});color:#fff !important;'
            f'font-weight:800;text-decoration:none;font-family:DM Sans,sans-serif;">Compila il questionario completo →</a>',
            unsafe_allow_html=True)
        if invito:
            st.markdown("##### Oppure invita un collega")
            render_invito(T, invito, con_titolo=False)
        if residui > 0:
            st.success(f"Hai {residui} verifiche con tutte le funzioni a disposizione: usane una sulla verifica che stavi guardando, su una tua in «Le mie verifiche» o su una nuova.", icon="🎁")
        st.markdown("##### Ho un codice")
        codice = st.text_input("Codice", key="sb_codice", placeholder="VF-ABCD-2345", label_visibility="collapsed")
        if st.button("Sblocca", key="sb_sblocca", type="primary", use_container_width=True, disabled=not (codice or "").strip()):
            with st.spinner("Controllo il codice…"):
                ok, msg = on_riscatta(codice)
            if ok:
                st.success(msg, icon="✅")
                st.session_state.pop("sb_codice", None)
                if st.button("Torna alla verifica e usa una verifica completa", key="sb_torna_dopo", type="primary", icon=":material/arrow_back:", use_container_width=True):
                    on_back()
                    return
            else:
                st.error(msg)
