"""
ui_upgrade.py — pagina «Passa a Pro»: schede Free e Pro, garanzie, esempi di qualità, domande frequenti, pulsante di acquisto,
invito a un collega e campo «Ho già il codice di licenza». Solo interfaccia: piani e prezzi stanno in config.py, il controllo
del codice in licenze.py (chiamato da main.py tramite `on_attiva`).
"""
import os
from urllib.parse import quote

import streamlit as st

from config import (BONUS_PER_INVITO, CHECKOUT_URL_PRO, ETICHETTE_FUNZIONI, LEGALE_PRONTO, LIMITE_MENSILE,
                    MAX_INVITI_CON_BONUS, PREZZO_PRO_ANNUALE)

_CARTELLA_ESEMPI = os.path.join("assets", "esempi")

_FREE_VOCI = (
    f"{LIMITE_MENSILE} verifiche al mese",
    "PDF della verifica pronto per la stampa",
    "Modifica di ogni esercizio",
    "Modello AI veloce",
)
_PRO_VOCI = (
    "Tutto quello che c'è nel piano Free",
    "Modello AI più accurato: esercizi più precisi",
    "Fila B: stessa verifica, dati diversi, contro la copiatura",
    "Versione BES/DSA semplificata",
    "Soluzioni e griglia di valutazione",
    "Scheda di allenamento (~40 esercizi) e tutto in un solo file",
    "Verifica da un tuo file e logo della scuola",
)

_CSS = """<style>
.up-hero { text-align:center; margin:.2rem 0 1.4rem; }
.up-hero h1 { font-family:'DM Sans',sans-serif; font-size:2rem; font-weight:800; letter-spacing:-.025em; margin:0; padding:0; }
.up-hero p { font-family:'DM Sans',sans-serif; color:#64748B; margin:.4rem 0 0; font-size:1rem; }
.up-piani { display:grid; grid-template-columns:1fr 1fr; gap:1rem; align-items:stretch; margin-bottom:1.1rem; }
.up-card { position:relative; border:1px solid #CBD5E1; border-radius:18px; padding:1.4rem 1.3rem 1.2rem; background:#fff;
  font-family:'DM Sans',sans-serif; }
.up-card.pro { border:2px solid #1D4ED8; box-shadow:0 14px 34px rgba(29,78,216,.18);
  background:linear-gradient(180deg,#F5F8FF 0%,#fff 38%); }
.up-badge { position:absolute; top:-.7rem; right:1.1rem; background:linear-gradient(135deg,#FDE68A,#F59E0B); color:#1E3A8A;
  font-size:.7rem; font-weight:800; letter-spacing:.08em; text-transform:uppercase; padding:.22rem .7rem; border-radius:999px; }
.up-nome { font-size:1.05rem; font-weight:800; color:#0F172A; }
.up-prezzo { font-size:2.1rem; font-weight:800; letter-spacing:-.03em; color:#0F172A; margin-top:.15rem; line-height:1.1; }
.up-prezzo small { font-size:.85rem; font-weight:600; color:#64748B; letter-spacing:0; }
.up-card ul { list-style:none; margin:.9rem 0 0; padding:0; }
.up-card li { display:flex; gap:.5rem; font-size:.92rem; line-height:1.4; color:#1E293B; padding:.28rem 0; margin:0; }
.up-card li::before { content:"✓"; flex:0 0 auto; font-weight:800; color:#16A34A; }
.up-card.pro li::before { color:#1D4ED8; }
.up-garanzie { display:grid; grid-template-columns:repeat(3,1fr); gap:.6rem; margin:.9rem 0 1.4rem; }
.up-g { text-align:center; font-family:'DM Sans',sans-serif; font-size:.85rem; color:#334155; background:#F1F5F9;
  border-radius:12px; padding:.65rem .5rem; line-height:1.35; }
.up-g b { display:block; font-size:.9rem; color:#0F172A; }
@media (max-width: 640px) { .up-piani, .up-garanzie { grid-template-columns:1fr; } .up-hero h1 { font-size:1.6rem; } }
/* pulsante di acquisto: oro, come gli altri inviti al Pro */
html body .stApp .st-key-up_cta [data-testid="stLinkButton"] a, html body .stApp .st-key-up_cta button {
  background:linear-gradient(135deg,#FDE68A 0%,#FBBF24 55%,#F59E0B 100%) !important; border:0 !important; border-radius:999px !important;
  min-height:3.1rem; box-shadow:0 10px 22px rgba(245,158,11,.40), inset 0 1px 0 rgba(255,255,255,.6) !important; }
html body .stApp .st-key-up_cta [data-testid="stLinkButton"] a, html body .stApp .st-key-up_cta [data-testid="stLinkButton"] a *,
html body .stApp .st-key-up_cta button, html body .stApp .st-key-up_cta button * {
  color:#1E3A8A !important; -webkit-text-fill-color:#1E3A8A !important; font-weight:800 !important; font-size:1.05rem !important; }
</style>"""


def _esempi() -> list:
    """Coppie (immagine Free, immagine Pro) presenti in assets/esempi: free_1.png / pro_1.png, …"""
    coppie = []
    for n in range(1, 4):
        f, p = (os.path.join(_CARTELLA_ESEMPI, f"{k}_{n}.png") for k in ("free", "pro"))
        if os.path.exists(f) and os.path.exists(p):
            coppie.append((f, p))
    return coppie


def _url_acquisto(email: str | None) -> str:
    """Link di acquisto con l'email del docente già compilata."""
    if not CHECKOUT_URL_PRO:
        return ""
    return CHECKOUT_URL_PRO + (f"?checkout[email]={quote(email)}" if email else "")


def _scheda(nome: str, prezzo: str, dettaglio: str, voci: tuple, pro: bool = False) -> str:
    li = "".join(f"<li>{v}</li>" for v in voci)
    badge = '<div class="up-badge">Consigliato</div>' if pro else ""
    return (f'<div class="up-card{" pro" if pro else ""}">{badge}<div class="up-nome">{nome}</div>'
            f'<div class="up-prezzo">{prezzo} <small>{dettaglio}</small></div><ul>{li}</ul></div>')


def render_upgrade(on_back, funzione: str | None = None, assaggio_usato: bool = False,
                   e_pro: bool = False, email: str | None = None, on_attiva=None, e_admin: bool = False,
                   invito: dict | None = None):
    """
    on_back        : callable che riporta alla pagina precedente
    funzione       : la funzione Pro che ha portato qui (per il titolo), se c'è
    assaggio_usato : True se l'utente ha già usato la sua prima verifica «tutto Pro»
    e_pro          : l'utente ha già il piano Pro
    email          : email dell'utente (precompila il pagamento)
    on_attiva      : callable(codice) -> (ok, messaggio, dettaglio_admin); None = campo non mostrato
    e_admin        : mostra il dettaglio tecnico degli errori
    invito         : {"link", "convalidati", "residui"} per «Invita un collega» (None = non mostrato)
    """
    if st.button("← Indietro", key="up_indietro", type="tertiary"):
        on_back()
        return

    st.markdown(_CSS + '<div class="up-hero"><h1>VerificAI Pro</h1>'
                '<p>Tutto il kit per la tua classe, con un solo pagamento per l\'anno scolastico.</p></div>',
                unsafe_allow_html=True)
    if e_pro:
        st.success("Hai già il piano Pro: tutte le funzioni sono attive. Grazie!")
        return
    if funzione in ETICHETTE_FUNZIONI:
        st.info(f"Con il piano Pro puoi avere {ETICHETTE_FUNZIONI[funzione]} e tutto il resto del kit per la tua classe.")
    if assaggio_usato:
        st.caption("Nella tua prima verifica hai provato tutte le funzioni del piano Pro. Da ora sei sul piano Free.")

    st.markdown('<div class="up-piani">'
                + _scheda("Free", "0 €", "per sempre", _FREE_VOCI)
                + _scheda("Pro", f"{PREZZO_PRO_ANNUALE} €", "anno scolastico · un solo pagamento", _PRO_VOCI, pro=True)
                + '</div>', unsafe_allow_html=True)

    url = _url_acquisto(email)
    with st.container(key="up_cta"):
        if url:
            st.link_button(f"Passa a Pro · {PREZZO_PRO_ANNUALE} €", url, type="primary", use_container_width=True)
        else:
            st.button("Passa a Pro (disponibile a breve)", disabled=True, use_container_width=True, key="up_presto")
    if url:
        st.caption("Dopo il pagamento ricevi un codice di licenza: incollalo più sotto, in «Ho già il codice», per attivare il piano.")
    else:
        st.caption("L'acquisto sarà disponibile a breve. Nel frattempo continui con il piano attuale.")

    _link = (' · <a href="?pagina=rimborsi" target="_blank" rel="noopener">Rimborsi</a>'
             ' · <a href="?pagina=termini" target="_blank" rel="noopener">Termini</a>') if LEGALE_PRONTO else ""
    st.markdown('<div class="up-garanzie">'
                '<div class="up-g"><b>↩️ Rimborso entro 14 giorni</b>Se non ti convince, ti restituiamo tutto</div>'
                '<div class="up-g"><b>🔁 Nessun rinnovo automatico</b>Paghi una volta, senza abbonamenti nascosti</div>'
                '<div class="up-g"><b>👩‍🏫 Fatto da un docente</b>Per colleghi che vogliono risparmiare tempo</div></div>'
                f'<div style="text-align:center;font-size:.8rem;color:#64748B;margin:-.8rem 0 1.2rem;">'
                f'Pagamento sicuro con Lemon Squeezy{_link}</div>', unsafe_allow_html=True)

    esempi = _esempi()
    if esempi:
        st.markdown("### Stesso argomento, due qualità")
        st.caption("Due verifiche generate con la stessa richiesta: a sinistra Free, a destra Pro.")
        for f, p in esempi:
            c1, c2 = st.columns(2, gap="small")
            c1.image(f, caption="Free", use_container_width=True)
            c2.image(p, caption="Pro", use_container_width=True)

    st.markdown("### Domande frequenti")
    with st.expander("Cosa succede dopo il pagamento?"):
        st.write("Ricevi via email un codice di licenza. Lo incolli in «Ho già il codice» (più sotto) e il piano Pro si attiva subito, senza ricaricare la pagina.")
    with st.expander("Posso usarlo su più account?"):
        st.write("Il codice vale per un solo account. Se cambi email o account, scrivici dal link Feedback e lo sistemiamo.")
    with st.expander("Quanto dura e cosa succede dopo?"):
        st.write("Il piano dura un anno dall'attivazione. Alla scadenza torni al piano Free e le verifiche che hai creato restano tue. Non c'è nessun rinnovo automatico.")
    with st.expander("Posso essere rimborsato?"):
        st.write("Sì: entro 14 giorni dall'acquisto puoi chiedere il rimborso integrale. Il codice viene disattivato e torni al piano Free.")
    with st.expander("Le mie verifiche e i miei dati sono al sicuro?"):
        st.write("I dati della carta non passano da VerificAI: li gestisce Lemon Squeezy. Non inserire dati personali degli studenti nelle richieste.")

    if invito:
        st.markdown("### Invita un collega")
        st.caption(f"Per ogni collega che si iscrive e crea la sua prima verifica ricevi {BONUS_PER_INVITO} verifiche con tutto il piano Pro "
                   f"(fino a {MAX_INVITI_CON_BONUS} colleghi). Colleghi arrivati: {invito['convalidati']} · Verifiche Pro disponibili: {invito['residui']}.")
        st.code(invito["link"], language=None)

    if on_attiva is not None:
        with st.expander("Ho già il codice di licenza", expanded=False, icon=":material/key:"):
            codice = st.text_input("Codice di licenza", key="up_codice", placeholder="XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX")
            if st.button("Attiva il piano Pro", key="up_attiva", type="primary", disabled=not (codice or "").strip()):
                with st.spinner("Controllo il codice…"):
                    ok, msg, dett = on_attiva(codice)
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
                    if e_admin and dett:
                        st.caption(f"Dettaglio tecnico (visibile solo all'admin): {dett}")
