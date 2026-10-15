"""
ui_inviti.py — «Invita un collega»: link personale, pulsanti per l'email e per WhatsApp, contatori e finestra.
Solo interfaccia (la logica dei crediti è in inviti.py). Chi invita guadagna config.BONUS_PER_INVITO verifiche con tutte le funzioni
quando il collega si iscrive col suo link e crea la sua prima verifica (fino a config.MAX_INVITI_CON_BONUS colleghi).
"""
import urllib.parse

import streamlit as st

from config import BONUS_PER_INVITO, MAX_INVITI_CON_BONUS


def testo_email(link: str):
    """(oggetto, testo) dell'email di invito: poche righe, in prima persona, senza tono da pubblicità."""
    oggetto = "Una cosa utile per preparare le verifiche"
    testo = (
        "Ciao,\n\n"
        "ti consiglio VerificAI: scrivi l'argomento e ottieni la verifica già impaginata, con punteggi e grafici, "
        "in PDF o in Word modificabile. È gratuito in questa fase.\n\n"
        f"Provalo da qui: {link}\n\n"
        "Fammi sapere cosa ne pensi!"
    )
    return oggetto, testo


def link_email(link: str) -> str:
    oggetto, testo = testo_email(link)
    return "mailto:?subject=" + urllib.parse.quote(oggetto, safe="") + "&body=" + urllib.parse.quote(testo, safe="")


def link_whatsapp(link: str) -> str:
    testo = ("Ciao! Ti consiglio VerificAI: scrivi l'argomento e ottieni la verifica già pronta, in PDF o Word. "
             f"È gratuito in questa fase. Provalo qui: {link}")
    return "https://wa.me/?text=" + urllib.parse.quote(testo, safe="")


def render_invito(T: dict, invito: dict, con_titolo: bool = True) -> None:
    """Il blocco completo. `invito` = {"link", "convalidati", "residui"} (da main._info_invito)."""
    acc = T["accent"]
    link = invito["link"]
    if con_titolo:
        st.markdown(
            f'<div style="font-family:DM Sans,sans-serif;color:{T["text"]};font-weight:800;font-size:1.15rem;margin-bottom:.2rem;">'
            f'Invita un collega: +{BONUS_PER_INVITO} verifiche complete per te</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div style="font-family:DM Sans,sans-serif;color:{T["text2"]};font-size:.93rem;line-height:1.5;margin-bottom:.8rem;">'
        f'Quando un collega si iscrive con il tuo link e crea la sua prima verifica, tu ricevi <b>{BONUS_PER_INVITO} verifiche con tutte le '
        f'funzioni</b> (Fila B, BES/DSA, soluzioni, Word…). Puoi invitare fino a {MAX_INVITI_CON_BONUS} colleghi.</div>',
        unsafe_allow_html=True)
    _stile = (f"display:block;text-align:center;padding:.65rem .8rem;border-radius:12px;font-family:DM Sans,sans-serif;font-weight:800;"
              f"font-size:.92rem;text-decoration:none !important;")
    st.markdown(
        '<div style="display:grid;grid-template-columns:1fr 1fr;gap:.6rem;margin-bottom:.7rem;">'
        f'<a href="{link_email(link)}" target="_blank" rel="noopener" style="{_stile}background:linear-gradient(135deg,{acc},{T["accent2"]});'
        f'color:#fff !important;box-shadow:0 6px 16px {acc}44;">✉️ Invia per email</a>'
        f'<a href="{link_whatsapp(link)}" target="_blank" rel="noopener" style="{_stile}background:#fff;color:#128C7E !important;'
        f'border:1.5px solid #25D366;">💬 WhatsApp</a></div>',
        unsafe_allow_html=True)
    st.caption("Oppure copia il tuo link personale:")
    st.code(link, language=None)
    st.caption(f"Colleghi arrivati: {invito.get('convalidati', 0)} · Verifiche complete disponibili: {invito.get('residui', 0)}")


@st.dialog("Invita un collega")
def _dialogo(T: dict, invito: dict) -> None:
    render_invito(T, invito, con_titolo=False)


def apri_dialogo_invito(T: dict, invito: dict) -> None:
    _dialogo(T, invito)
