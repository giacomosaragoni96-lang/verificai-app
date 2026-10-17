"""
ui_impostazioni.py — la pagina «Impostazioni predefinite» (stage IMPOSTAZIONI): solo interfaccia. I dati e le funzioni vengono da main.py tramite `ctx`.

Quello che si imposta qui vale per ogni verifica e resta salvato finché non si cambia: preferenze di scrittura, stile del PDF, logo della scuola.
"""
import html

import streamlit as st

import profilo


def _torna(ctx, chiave: str, primario: bool) -> None:
    if ctx["da_form"]:
        if st.button("Torna alla verifica che stavi creando", key=f"imp_torna_{chiave}", type="primary" if primario else "secondary",
                     icon=":material/arrow_back:", use_container_width=primario):
            ctx["torna"]()
    elif st.button("← Indietro", key=f"imp_torna_{chiave}", type="tertiary"):
        ctx["torna"]()


def riepilogo(T: dict, ctx: dict, frasi: list, nome_stile: str, modificato: bool) -> None:
    """Scheda con ciò che verrà applicato a ogni verifica (istruzioni, stile, logo), come sarà dopo il salvataggio."""
    acc, tx, t2 = T["accent"], T["text"], T["text2"]
    logo = ctx["logo_info"]()
    if logo is None:
        logo_txt, logo_ok = "Nessun logo", False
    elif logo.get("attivo", True):
        logo_txt, logo_ok = "Il logo della scuola è nell'intestazione", True
    else:
        logo_txt, logo_ok = "Logo caricato, ma spento", False
    if frasi:
        voci = "".join(f'<li>{html.escape(f)}</li>' for f in frasi)
        istruz = f'<ul class="rs-l">{voci}</ul>'
    else:
        istruz = '<div class="rs-v rs-vuoto">Nessuna istruzione fissa: ogni verifica parte da zero.</div>'
    stato = ('<span class="rs-b rs-da">Da salvare</span>' if modificato else '<span class="rs-b rs-ok">Salvato</span>')
    st.markdown(
        "<style>"
        f".rs{{margin:1rem 0 .4rem;padding:1.1rem 1.3rem;border-radius:18px;background:linear-gradient(160deg,{T['card']} 0%,{acc}10 100%);"
        f"border:1px solid {acc}33;border-left:5px solid {acc};box-shadow:0 12px 28px {acc}1f,0 2px 6px rgba(15,23,42,.06);font-family:'DM Sans',sans-serif;}}"
        f".rs-t{{display:flex;align-items:center;gap:.6rem;font-weight:800;font-size:1.05rem;color:{tx};margin-bottom:.15rem;}}"
        f".rs-s{{font-size:.86rem;color:{t2};margin-bottom:.8rem;}}"
        ".rs-b{font-size:.68rem;font-weight:800;letter-spacing:.06em;text-transform:uppercase;padding:.15rem .6rem;border-radius:999px;}"
        ".rs-ok{background:#DCFCE7;color:#166534;}.rs-da{background:#FEF3C7;color:#92400E;}"
        f".rs-r{{display:flex;gap:.8rem;align-items:flex-start;padding:.6rem 0;border-top:1px solid {acc}22;}}"
        f".rs-i{{flex:0 0 2.1rem;height:2.1rem;border-radius:10px;background:{acc}1a;display:flex;align-items:center;justify-content:center;font-size:1.05rem;}}"
        f".rs-k{{font-size:.7rem;font-weight:800;letter-spacing:.07em;text-transform:uppercase;color:{t2};margin-bottom:.1rem;}}"
        f".rs-v{{font-size:.95rem;color:{tx};line-height:1.45;}}.rs-vuoto{{color:{t2};}}"
        f".rs-l{{margin:0;padding-left:1.1rem;font-size:.95rem;color:{tx};line-height:1.5;}}.rs-l li{{margin:.1rem 0;}}"
        "</style>"
        f'<div class="rs"><div class="rs-t">Cosa verrà applicato a ogni verifica {stato}</div>'
        '<div class="rs-s">Così si presenteranno le tue prossime verifiche. Quello che scrivi nella descrizione ha sempre la precedenza.</div>'
        f'<div class="rs-r"><div class="rs-i">✍️</div><div><div class="rs-k">Istruzioni fisse</div>{istruz}</div></div>'
        f'<div class="rs-r"><div class="rs-i">🎨</div><div><div class="rs-k">Stile del PDF</div><div class="rs-v">{html.escape(nome_stile)}</div></div></div>'
        f'<div class="rs-r"><div class="rs-i">🏫</div><div><div class="rs-k">Logo della scuola</div>'
        f'<div class="rs-v{"" if logo_ok else " rs-vuoto"}">{logo_txt}</div></div></div></div>',
        unsafe_allow_html=True)


_CSS_PAGINA = """<style>
html body .stApp div[class*="st-key-imp_card_"]:not(#vf) {{
  background: linear-gradient(160deg, {card} 0%, {acc}0D 100%); border: 1px solid {acc}30; border-radius: 20px;
  padding: 1.2rem 1.4rem 1.3rem; margin-bottom: 1rem; box-shadow: 0 14px 30px {acc}1c, 0 2px 6px rgba(15,23,42,.06);
}}
.imp-titolo {{ font-family: 'DM Sans', sans-serif; font-size: 1.9rem; font-weight: 800; letter-spacing: -.03em; line-height: 1.1; color: {tx}; margin: .5rem 0 .25rem; }}
.imp-titolo::after {{ content: ""; display: block; width: 3.6rem; height: .32rem; border-radius: 99px; margin-top: .55rem; background: linear-gradient(90deg, {acc}, {acc2}); }}
.imp-sotto {{ font-family: 'DM Sans', sans-serif; font-size: .96rem; color: {t2}; margin: 0 0 1.1rem; line-height: 1.5; }}
.imp-h {{ display: flex; align-items: center; gap: .7rem; margin: 0 0 .9rem; font-family: 'DM Sans', sans-serif; }}
.imp-hi {{ flex: 0 0 2.3rem; height: 2.3rem; border-radius: 12px; background: linear-gradient(135deg, {acc}, {acc2}); color: #fff;
  display: flex; align-items: center; justify-content: center; font-size: 1.1rem; box-shadow: 0 6px 14px {acc}44; }}
.imp-ht {{ font-weight: 800; font-size: 1.12rem; color: {tx}; line-height: 1.15; }}
.imp-hs {{ font-size: .84rem; color: {t2}; margin-top: .1rem; }}
html body .stApp .st-key-imp_azioni:not(#vf) {{ margin: .2rem 0 .4rem; }}
</style>"""


def _titolo(icona: str, titolo: str, sotto: str) -> None:
    st.markdown(f'<div class="imp-h"><div class="imp-hi">{icona}</div><div><div class="imp-ht">{html.escape(titolo)}</div>'
                f'<div class="imp-hs">{html.escape(sotto)}</div></div></div>', unsafe_allow_html=True)


def render_impostazioni(T: dict, ctx: dict) -> None:
    _torna(ctx, "alto", primario=False)
    p = ctx["profilo"]
    st.markdown(_CSS_PAGINA.format(card=T["card"], acc=T["accent"], acc2=T.get("accent2", T["accent"]), tx=T["text"], t2=T["text2"]), unsafe_allow_html=True)
    st.markdown('<div class="imp-titolo">Impostazioni predefinite</div>'
                '<div class="imp-sotto">Si applicano a ogni verifica che crei e restano salvate finché non le modifichi. '
                'Quello che scrivi nella descrizione di una verifica ha sempre la precedenza.</div>', unsafe_allow_html=True)

    with st.container(key="imp_card_scrittura"):
        _titolo("✍️", "Come scrivere le verifiche", "Preferenze che valgono per ogni materia e ogni classe.")
        ids = list(profilo.PILLOLE)
        scelte = st.pills("Accendi quelle che ti servono", ids, selection_mode="multi", default=[i for i in p.get("pillole", []) if i in ids],
                          key="pf_pillole", format_func=lambda i: profilo.PILLOLE[i][0])
        note = st.text_area("Altre istruzioni fisse", value=p.get("note_fisse", ""), height=90, max_chars=profilo.MAX_NOTE, key="pf_note",
                            placeholder="Es.: ultimo esercizio di eccellenza, richieste brevi, niente date da ricordare")

    with st.container(key="imp_card_aspetto"):
        _titolo("🎨", "Stile e logo", "Come appare il PDF: carattere, intestazione, logo della scuola.")
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
    with st.container(key="imp_azioni"):
        if modificato:        # il pulsante lampeggia (come i suggerimenti della guida, ma più svelto): c'è qualcosa da salvare
            st.markdown("<style>@keyframes salva-lampeggia{0%,100%{box-shadow:0 0 0 0 rgba(245,158,11,0);outline:2px solid rgba(245,158,11,0);outline-offset:3px}"
                        "50%{box-shadow:0 0 0 8px rgba(245,158,11,.32);outline:2px solid rgba(245,158,11,.8);outline-offset:3px}}"
                        "html body .stApp .st-key-pf_salva button:not(:disabled){animation:salva-lampeggia 1.1s ease-in-out infinite;border-radius:12px;}"
                        "@media (prefers-reduced-motion:reduce){html body .stApp .st-key-pf_salva button{animation:none !important}}</style>",
                        unsafe_allow_html=True)
        if st.button("Salva le impostazioni", key="pf_salva", type="primary", icon=":material/check:", disabled=not modificato):
            ctx["salva"]({**p, "pillole": list(scelte or []), "note_fisse": note, "stile": stile})
            ctx["salva_logo"]()
            ctx["conferma"]("Impostazioni salvate")
            st.rerun()

    riepilogo(T, ctx, profilo.frasi_preferenze({**p, "pillole": list(scelte or []), "note_fisse": note}), nomi.get(stile or "", "Classico"), modificato)

    if ctx["da_form"]:
        _torna(ctx, "basso", primario=True)
