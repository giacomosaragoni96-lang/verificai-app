"""
ui_impostazioni.py — la pagina «Impostazioni predefinite» (stage IMPOSTAZIONI): solo interfaccia. I dati e le funzioni vengono da main.py tramite `ctx`.

Quello che si imposta qui vale per ogni verifica e resta salvato finché non si cambia: preferenze di scrittura, stile del PDF, logo della scuola.
"""
import streamlit as st

import profilo


def _torna(ctx, chiave: str, primario: bool) -> None:
    if ctx["da_form"]:
        if st.button("Torna alla verifica che stavi creando", key=f"imp_torna_{chiave}", type="primary" if primario else "secondary",
                     icon=":material/arrow_back:", use_container_width=primario):
            ctx["torna"]()
    elif st.button("← Indietro", key=f"imp_torna_{chiave}", type="tertiary"):
        ctx["torna"]()


def render_impostazioni(T: dict, ctx: dict) -> None:
    _torna(ctx, "alto", primario=False)
    p = ctx["profilo"]
    st.markdown('<div class="pf-sez" style="font-size:1.5rem;">Impostazioni predefinite</div>'
                '<div class="pf-sub">Si applicano a ogni verifica che crei e restano salvate finché non le modifichi. '
                'Quello che scrivi nella descrizione di una verifica ha sempre la precedenza.</div>', unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown("**Come scrivere le verifiche**")
        ids = list(profilo.PILLOLE)
        scelte = st.pills("Accendi quelle che ti servono", ids, selection_mode="multi", default=[i for i in p.get("pillole", []) if i in ids],
                          key="pf_pillole", format_func=lambda i: profilo.PILLOLE[i][0])
        note = st.text_area("Altre istruzioni fisse", value=p.get("note_fisse", ""), height=90, max_chars=profilo.MAX_NOTE, key="pf_note",
                            placeholder="Es.: ultimo esercizio di eccellenza, niente problemi di fisica applicata, richieste brevi")
        stili = ctx["stili"]
        chiavi = [""] + [k for k, _n in stili]
        nomi = {"": "Classico (predefinito)", **{k: n for k, n in stili}}
        stile = st.selectbox("Stile del PDF", chiavi, index=chiavi.index(p.get("stile", "")) if p.get("stile", "") in chiavi else 0,
                             format_func=lambda k: nomi[k], key="pf_stile")
        if st.button("Guarda un'anteprima degli stili", key="pf_anteprima_stili", type="tertiary", icon=":material/visibility:"):
            ctx["anteprima_stili"]()
        st.markdown("**Logo della scuola**")
        st.caption("Lo carichi una volta sola: compare nell'intestazione di ogni verifica, finché non lo cambi o lo togli.")
        ctx["blocco_logo"]()

        modificato = (set(scelte or []) != set(p.get("pillole", [])) or (note or "").strip() != (p.get("note_fisse", "") or "").strip()
                      or (stile or "") != (p.get("stile", "") or "") or ctx["logo_modificato"]())
        if modificato:
            st.caption("Hai modifiche non ancora salvate.")
        if st.button("Salva le impostazioni", key="pf_salva", type="primary", icon=":material/check:", disabled=not modificato):
            ctx["salva"]({**p, "pillole": list(scelte or []), "note_fisse": note, "stile": stile})
            ctx["salva_logo"]()
            ctx["conferma"]("Impostazioni salvate")
            st.rerun()
        frasi = profilo.frasi_preferenze({**p, "pillole": list(scelte or []), "note_fisse": note})
        if frasi:
            st.markdown("**Come finirà nelle tue verifiche**")
            for f in frasi:
                st.markdown(f"- {f}")

    if ctx["da_form"]:
        _torna(ctx, "basso", primario=True)
