"""
ui_upgrade.py — pagina «Passa a Pro»: cosa cambia tra Free e Pro, esempi di qualità, pulsante di acquisto
e campo «Ho già il codice di licenza». Solo interfaccia: piani e prezzi stanno in config.py, il controllo
del codice in licenze.py (chiamato da main.py tramite `on_attiva`).
"""
import os
from urllib.parse import quote

import streamlit as st

from config import CHECKOUT_URL_PRO, ETICHETTE_FUNZIONI, FUNZIONI_PRO, LIMITE_MENSILE, PREZZO_PRO_ANNUALE

_CARTELLA_ESEMPI = os.path.join("assets", "esempi")

_CONFRONTO = (
    ("Verifiche al mese", f"{LIMITE_MENSILE}", "Fino a 100 (uso corretto)"),
    ("Modello AI", "Veloce", "Più accurato: esercizi più precisi"),
    ("PDF della verifica e modifica degli esercizi", "Sì", "Sì"),
    ("Soluzioni, Fila B, versione BES/DSA", "—", "Sì"),
    ("File Word e griglia di valutazione", "—", "Sì"),
    ("Logo della scuola sulla verifica", "—", "Sì"),
    ("Scheda di allenamento (~40 esercizi) e kit in un solo file", "—", "Sì"),
)


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


def render_upgrade(on_back, funzione: str | None = None, assaggio_usato: bool = False,
                   e_pro: bool = False, email: str | None = None, on_attiva=None, e_admin: bool = False):
    """
    on_back        : callable che riporta alla pagina precedente
    funzione       : la funzione Pro che ha portato qui (per il titolo), se c'è
    assaggio_usato : True se l'utente ha già usato la sua prima verifica «tutto Pro»
    e_pro          : l'utente ha già il piano Pro
    email          : email dell'utente (precompila il pagamento)
    on_attiva      : callable(codice) -> (ok, messaggio, dettaglio_admin); None = campo non mostrato
    e_admin        : mostra il dettaglio tecnico degli errori
    """
    if st.button("← Indietro", key="up_indietro"):
        on_back()
        return

    st.markdown("## VerificAI Pro")
    if e_pro:
        st.success("Hai già il piano Pro: tutte le funzioni sono attive. Grazie!")
        return
    if funzione in ETICHETTE_FUNZIONI:
        st.info(f"Con Pro puoi avere {ETICHETTE_FUNZIONI[funzione]} e tutto il resto del kit per la tua classe.")
    if assaggio_usato:
        st.caption("Nella tua prima verifica hai provato tutto il Pro. Da ora sei sul piano Free.")

    st.markdown(f"**{PREZZO_PRO_ANNUALE} € per l'anno scolastico**, pagamento unico. Niente rinnovi automatici.")

    righe = "| | Free | Pro |\n|---|---|---|\n" + "\n".join(f"| {a} | {b} | {c} |" for a, b, c in _CONFRONTO)
    st.markdown(righe)

    esempi = _esempi()
    if esempi:
        st.markdown("### Stesso argomento, due qualità")
        st.caption("Due verifiche generate con la stessa richiesta: a sinistra Free, a destra Pro.")
        for f, p in esempi:
            c1, c2 = st.columns(2, gap="small")
            c1.image(f, caption="Free", use_container_width=True)
            c2.image(p, caption="Pro", use_container_width=True)

    url = _url_acquisto(email)
    if url:
        st.link_button(f"Passa a Pro · {PREZZO_PRO_ANNUALE} €", url, type="primary", use_container_width=True)
        st.caption("Dopo il pagamento ricevi un codice di licenza: incollalo qui sotto per attivare il piano.")
    else:
        st.button("Passa a Pro (disponibile a breve)", disabled=True, use_container_width=True, key="up_presto")
        st.caption("L'acquisto sarà disponibile a breve. Nel frattempo continui con il piano attuale.")

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

    st.caption("Funzioni incluse: " + ", ".join(ETICHETTE_FUNZIONI[f] for f in FUNZIONI_PRO if f in ETICHETTE_FUNZIONI) + ".")
