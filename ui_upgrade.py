"""
ui_upgrade.py — pagina «Passa a Pro»: cosa cambia tra Free e Pro, esempi di qualità e (dal lancio)
il pulsante di acquisto. Solo interfaccia: i piani e i prezzi stanno in config.py.
"""
import os

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


def render_upgrade(on_back, funzione: str | None = None, assaggio_usato: bool = False):
    """
    on_back        : callable che riporta alla pagina precedente
    funzione       : la funzione Pro che ha portato qui (per il titolo), se c'è
    assaggio_usato : True se l'utente ha già usato la sua prima verifica «tutto Pro»
    """
    if st.button("← Indietro", key="up_indietro"):
        on_back()
        return

    st.markdown("## Passa a VerificAI Pro")
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

    if CHECKOUT_URL_PRO:
        st.link_button(f"Passa a Pro · {PREZZO_PRO_ANNUALE} €", CHECKOUT_URL_PRO, type="primary",
                       use_container_width=True)
    else:
        st.button("Passa a Pro (disponibile a breve)", disabled=True, use_container_width=True, key="up_presto")
        st.caption("L'acquisto sarà disponibile a breve. Nel frattempo continui con il piano attuale.")
    st.caption("Funzioni incluse: " + ", ".join(ETICHETTE_FUNZIONI[f] for f in FUNZIONI_PRO if f in ETICHETTE_FUNZIONI) + ".")
