"""
ui_banca.py — pagina «Modelli di verifica» (riservata all'admin): carica le verifiche in LaTeX che
vuoi prendere come riferimento (stile, numero di esercizi, distribuzione dei punti) e approvale.

Solo interfaccia: la lettura del file sta in banca_import.py e il database in banca.py.
"""
import pandas as pd
import streamlit as st

import banca
import banca_import
from config import CATEGORIE_SCUOLA, MATERIE

_MSG = "_bk_msg"
AUTO = "Rileva dal titolo"


def _istruzioni_tabelle():
    st.error("Le tabelle dei modelli non ci sono ancora su Supabase.", icon="🗄️")
    st.markdown(
        "1. Apri **Supabase → SQL Editor → New query**.\n"
        "2. Incolla il testo qui sotto (è il file `modelli_verifica.sql`) e premi **Run**.\n"
        "3. Torna qui e ricarica la pagina."
    )
    try:
        with open("modelli_verifica.sql", encoding="utf-8") as f:
            st.code(f.read(), language="sql")
    except OSError:
        st.caption("File modelli_verifica.sql non trovato nella cartella dell'app.")


def _carica(sb):
    st.caption("Carica le verifiche in LaTeX (.tex) che consideri perfette: l'app ne ricava la struttura "
               "(sezioni, numero di quesiti, punti, esercizi facoltativi) e il codice come riferimento di stile. "
               "Nessuna AI: la lettura è esatta e gratuita.")
    c1, c2 = st.columns(2)
    scelta = c1.selectbox("Materia", [AUTO] + MATERIE, key="bk_materia",
                          help="«Rileva dal titolo» usa il titolo della verifica (es. «Verifica di Matematica»); "
                               "se non la trova resta vuota e la imposti dopo.")
    scuola = c2.selectbox("Scuola a cui è destinata", CATEGORIE_SCUOLA,
                          index=CATEGORIE_SCUOLA.index("Professionale"), key="bk_scuola")
    materia = "" if scelta == AUTO else scelta

    if st.session_state.get(_MSG):
        for tipo, testo in st.session_state.pop(_MSG):
            (st.success if tipo == "ok" else st.warning)(testo)

    ciclo = st.session_state.setdefault("bk_ciclo", 0)
    files = st.file_uploader("Verifiche (.tex)", type=["tex"], accept_multiple_files=True, key=f"bk_up_{ciclo}")
    if files and st.button("Leggi e salva", type="primary", key="bk_analizza"):
        messaggi = []
        for f in files:
            try:
                ris, motivo = banca_import.analizza_verifica(f.name, f.getvalue())
                if ris is None:
                    messaggi.append(("avviso", f"{f.name}: {motivo}."))
                    continue
                esito = banca.salva_modello(sb, ris, materia, scuola)
                if esito["gia_presente"]:
                    messaggi.append(("avviso", f"{f.name}: era già stato caricato."))
                else:
                    m = ris["modello"]
                    mat = esito.get("materia") or "materia non riconosciuta (impostala qui sotto)"
                    messaggi.append(("ok", f"{f.name} ({mat}): {sum(s['n_quesiti'] for s in m['sezioni'])} quesiti in "
                                           f"{len(m['sezioni'])} sezioni, punti base {m['punti_base']} + facoltativi "
                                           f"{m['punti_extra']}. Approvalo per usarlo."))
            except Exception as e:                        # noqa: BLE001
                messaggi.append(("avviso", f"{f.name}: errore ({str(e)[:160]})"))
        st.session_state[_MSG] = messaggi
        st.session_state["bk_ciclo"] = ciclo + 1
        st.rerun()


def _elenco(sb):
    elenco = banca.modelli(sb)
    st.subheader(f"Modelli ({len(elenco)})")
    if not elenco:
        st.info("Nessun modello. Carica una verifica in LaTeX qui sopra.")
        return
    for m in elenco:
        s = m["struttura"]
        etichetta = ("✅ " if m["approvato"] else "⏳ ") + m["nome"] + f"  ·  {m.get('materia') or '—'}  ·  {m.get('scuola') or '—'}"
        with st.expander(etichetta):
            st.markdown(f"Punti base **{s.get('punti_base')}** + facoltativi **{s.get('punti_extra')}** = **{s.get('totale')}**"
                         + (f" · base PDP/DSA {s['base_pdp_dsa']}" if s.get("base_pdp_dsa") else "")
                         + ("" if s.get("punti_letti") else " · ⚠️ punti non letti dalla tabella finale"))
            st.dataframe(pd.DataFrame([{
                "Sezione": x["nome"], "Tipo": x["tipo"], "Quesiti": x["n_quesiti"],
                "Punti": " · ".join("—" if p is None else str(p) for p in x["punti"]),
                "Facoltativi": ("tutto l'esercizio (*)" if x["facoltativi"] and len(x["facoltativi"]) == x["n_quesiti"]
                                else ", ".join(x["facoltativi"]) or "—")} for x in s.get("sezioni", [])]),
                hide_index=True, use_container_width=True)
            nome = st.text_input("Nome del modello", value=m["nome"], key=f"bk_mn_{m['id']}")
            c1, c2 = st.columns(2)
            nm = c1.selectbox("Materia", MATERIE, key=f"bk_mm_{m['id']}",
                              index=MATERIE.index(m["materia"]) if m.get("materia") in MATERIE else 0)
            ns = c2.selectbox("Scuola", CATEGORIE_SCUOLA, key=f"bk_ms2_{m['id']}",
                              index=CATEGORIE_SCUOLA.index(m["scuola"]) if m.get("scuola") in CATEGORIE_SCUOLA else 0)
            b1, b2, b3 = st.columns(3)
            if b1.button("Disapprova" if m["approvato"] else "Approva", key=f"bk_ma_{m['id']}", use_container_width=True):
                banca.aggiorna_modello(sb, m["id"], {"approvato": not m["approvato"], "nome": nome, "materia": nm, "scuola": ns})
                st.rerun()
            if b2.button("Salva modifiche", key=f"bk_ms_{m['id']}", use_container_width=True):
                banca.aggiorna_modello(sb, m["id"], {"nome": nome, "materia": nm, "scuola": ns})
                st.rerun()
            if b3.button("Elimina", key=f"bk_md_{m['id']}", use_container_width=True):
                banca.elimina_modello(sb, m["id"])
                st.rerun()
            with st.popover("Vedi il codice LaTeX"):
                st.code(s.get("sorgente_latex", ""), language="latex")


def render_banca(sb, torna_indietro):
    """Pagina Modelli di verifica. torna_indietro(): riporta alla schermata di creazione."""
    h1, h2 = st.columns([5, 1])
    h1.markdown("## Modelli di verifica")
    if h2.button("← Indietro", key="bk_indietro", use_container_width=True):
        torna_indietro()
        return
    if sb is None or not banca.tabelle_pronte(sb):
        _istruzioni_tabelle()
        return
    _carica(sb)
    st.divider()
    _elenco(sb)
