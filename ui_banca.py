"""
ui_banca.py — pagina «Banca esercizi» (riservata all'admin): carica, rivedi, approva, cerca.

Solo interfaccia: l'analisi dei file sta in banca_import.py e il database in banca.py.
"""
import pandas as pd
import streamlit as st

import ai_client
import banca
import banca_import
from config import CATEGORIE_SCUOLA, MATERIE, MODEL_FLASH_ID

_MSG = "_bk_msg"


def _istruzioni_tabelle():
    st.error("Le tabelle della banca non ci sono ancora su Supabase.", icon="🗄️")
    st.markdown(
        "1. Apri **Supabase → SQL Editor → New query**.\n"
        "2. Incolla il testo qui sotto (è il file `banca_esercizi.sql`) e premi **Run**.\n"
        "3. Torna qui e ricarica la pagina."
    )
    try:
        with open("banca_esercizi.sql", encoding="utf-8") as f:
            st.code(f.read(), language="sql")
    except OSError:
        st.caption("File banca_esercizi.sql non trovato nella cartella dell'app.")


def _modello_ai():
    try:
        return ai_client.crea_modello(MODEL_FLASH_ID).per("importazione")
    except Exception:
        return None


# ── 1. CARICA ─────────────────────────────────────────────────────────────────

def _tab_carica(sb):
    st.caption("Carica verifiche, schede, appunti o libri. Gli esercizi vanno in coda: li controlli e li approvi nella scheda «Da approvare».")
    c1, c2 = st.columns(2)
    materia = c1.selectbox("Materia", MATERIE, key="bk_materia")
    scuola = c2.selectbox("Scuola a cui è destinato", CATEGORIE_SCUOLA, index=CATEGORIE_SCUOLA.index("Professionale"),
                          key="bk_scuola",
                          help="Serve per scegliere gli esercizi giusti quando un docente genera una verifica.")
    with st.expander("Opzioni"):
        livelli = st.radio(
            "Nelle schede, le sezioni «Livello N» sono…", ["auto", "difficolta", "argomenti"], horizontal=True,
            format_func={"auto": "lo capisce l'AI", "difficolta": "livelli di difficoltà",
                         "argomenti": "argomenti diversi"}.get, key="bk_livelli")
        senza_ai = st.checkbox(
            "Salta le etichette dell'AI (gratis, ma senza argomento, tecniche e difficoltà stimata)", key="bk_senza_ai",
            help="Il codice LaTeX di verifiche e schede viene sempre letto dal programma (testo, punti e struttura esatti). "
                 "L'AI aggiunge solo le etichette. Appunti e PDF richiedono sempre l'AI.")

    if st.session_state.get(_MSG):
        for tipo, testo in st.session_state.pop(_MSG):
            (st.success if tipo == "ok" else st.warning)(testo)

    ciclo = st.session_state.setdefault("bk_ciclo", 0)
    files = st.file_uploader("File (.tex o .pdf)", type=["tex", "pdf"], accept_multiple_files=True,
                             key=f"bk_up_{ciclo}")
    if files and st.button("Analizza e metti in coda", type="primary", key="bk_analizza"):
        modello = None if senza_ai else _modello_ai()
        messaggi = []
        for f in files:
            with st.status(f"{f.name}…", expanded=True) as stato:
                try:
                    ris = banca_import.analizza_file(f.name, f.getvalue(), materia, modello, livelli, senza_ai,
                                                     on_progress=st.write)
                    if ris is None:
                        stato.update(label=f"{f.name}: non letto", state="error")
                        messaggi.append(("avviso", f"{f.name}: non riesco a leggerlo (servono l'AI per i PDF e per gli appunti)."))
                        continue
                    esito = banca.salva_analisi(sb, ris, materia, scuola)
                    if esito["gia_presente"]:
                        stato.update(label=f"{f.name}: già in banca", state="complete")
                        messaggi.append(("avviso", f"{f.name}: era già stato caricato, non lo ricarico."))
                    else:
                        stato.update(label=f"{f.name}: {esito['nuovi']} esercizi in coda", state="complete")
                        extra = f" {ris['nota_livelli']}" if ris["nota_livelli"] else ""
                        messaggi.append(("ok", f"{f.name} ({ris['fonte']['tipo']}): {esito['nuovi']} esercizi in attesa di revisione.{extra}"))
                    for av in ris["avvisi"]:
                        messaggi.append(("avviso", f"{f.name}: {av}"))
                except Exception as e:                    # noqa: BLE001
                    stato.update(label=f"{f.name}: errore", state="error")
                    messaggi.append(("avviso", f"{f.name}: errore ({str(e)[:160]})"))
        st.session_state[_MSG] = messaggi
        st.session_state["bk_ciclo"] = ciclo + 1
        st.rerun()


# ── 2. DA APPROVARE ───────────────────────────────────────────────────────────

def _df_revisione(righe: list) -> pd.DataFrame:
    return pd.DataFrame([{
        "Tieni": True, "N.": r.get("numero") or "", "★": int(r.get("difficolta") or 2),
        "Argomento": r.get("argomento") or "", "Tecniche": ", ".join(r.get("tecniche") or []),
        "Tipo": r.get("tipo") or "", "Punti": r.get("punti"), "Facoltativo": bool(r.get("facoltativo")),
        "Testo": r.get("testo_latex") or "",
    } for r in righe])


def _tab_approva(sb):
    fonti = [f for f in banca.elenco_fonti(sb) if f["in_attesa"] > 0]
    if not fonti:
        st.info("Nessun esercizio in attesa di revisione. Carica un file nella scheda «Carica».")
        return
    f = st.selectbox("File da rivedere", fonti, key="bk_fonte_rev",
                     format_func=lambda x: f"{x['nome']} — {x['in_attesa']} in attesa ({x['tipo']})")
    if f.get("nota_livelli"):
        st.info(f["nota_livelli"])
    righe = banca.esercizi(sb, fonte_id=f["id"], approvato=False, limite=1000)
    originale = _df_revisione(righe)
    st.caption("Togli la spunta a ciò che non vuoi tenere; correggi ★, argomento, tecniche e tipo direttamente nella tabella.")
    modificato = st.data_editor(
        originale, key=f"bk_ed_{f['id']}", hide_index=True, use_container_width=True, num_rows="fixed",
        column_config={
            "Tieni": st.column_config.CheckboxColumn(width="small"),
            "N.": st.column_config.TextColumn(disabled=True, width="small"),
            "★": st.column_config.SelectboxColumn(options=[1, 2, 3], required=True, width="small"),
            "Tipo": st.column_config.SelectboxColumn(
                options=["", "aperto", "scelta_multipla", "vero_falso", "completamento", "problema"], width="small"),
            "Punti": st.column_config.NumberColumn(min_value=0, step=1, width="small"),
            "Facoltativo": st.column_config.CheckboxColumn(width="small"),
            "Testo": st.column_config.TextColumn(disabled=True, width="large"),
        },
    )
    with st.expander("Anteprima con le formule"):
        for r in righe[:60]:
            opz = "  \n" + "  \n".join(f"▫ {o}" for o in (r.get("opzioni") or [])) if r.get("opzioni") else ""
            st.markdown(f"**{r.get('numero') or ''}** {'★' * int(r.get('difficolta') or 2)} — {r['testo_latex']}{opz}")
        if len(righe) > 60:
            st.caption(f"… e altri {len(righe) - 60}")

    c1, c2 = st.columns(2)
    if c1.button("Approva quelli spuntati (scarta gli altri)", type="primary", key=f"bk_ok_{f['id']}",
                 use_container_width=True):
        tenuti, scartati = [], []
        for i, r in enumerate(righe):
            nuovo = modificato.iloc[i]
            if not bool(nuovo["Tieni"]):
                scartati.append(r["id"])
                continue
            tenuti.append(r["id"])
            campi = {
                "difficolta": int(nuovo["★"]), "argomento": str(nuovo["Argomento"] or "") or None,
                "tecniche": [t.strip() for t in str(nuovo["Tecniche"] or "").split(",") if t.strip()],
                "tipo": str(nuovo["Tipo"] or "") or None, "facoltativo": bool(nuovo["Facoltativo"]),
                "punti": None if pd.isna(nuovo["Punti"]) else int(nuovo["Punti"]),
            }
            if (campi["difficolta"] != (r.get("difficolta") or 2) or (campi["argomento"] or "") != (r.get("argomento") or "")
                    or campi["tecniche"] != (r.get("tecniche") or []) or (campi["tipo"] or "") != (r.get("tipo") or "")
                    or campi["facoltativo"] != bool(r.get("facoltativo")) or campi["punti"] != r.get("punti")):
                if campi["difficolta"] != (r.get("difficolta") or 2):
                    campi["difficolta_origine"] = "corretta a mano"
                banca.aggiorna_esercizio(sb, r["id"], campi)
        banca.approva_esercizi(sb, tenuti)
        banca.elimina_esercizi(sb, scartati)
        st.session_state[_MSG] = [("ok", f"{len(tenuti)} esercizi approvati, {len(scartati)} scartati.")]
        st.rerun()
    if c2.button("Scarta tutto questo file", key=f"bk_no_{f['id']}", use_container_width=True):
        banca.elimina_fonte(sb, f["id"])
        st.session_state[_MSG] = [("avviso", f"{f['nome']} eliminato dalla banca.")]
        st.rerun()


# ── 3. BANCA ──────────────────────────────────────────────────────────────────

def _tab_banca(sb):
    s = banca.statistiche(sb)
    c1, c2, c3 = st.columns(3)
    c1.metric("Esercizi approvati", s["approvati"])
    c2.metric("In attesa", s["in_attesa"])
    c3.metric("Materie", len(s["per_materia"]))
    if s["per_materia"]:
        st.dataframe(pd.DataFrame(
            [{"Materia": m, "★1": v[1], "★2": v[2], "★3": v[3], "Totale": sum(v.values())}
             for m, v in sorted(s["per_materia"].items())]), hide_index=True, use_container_width=True)

    f1, f2, f3 = st.columns([2, 2, 3])
    materia = f1.selectbox("Materia", ["Tutte"] + MATERIE, key="bk_f_materia")
    stelle = f2.multiselect("Difficoltà", [1, 2, 3], default=[1, 2, 3], format_func=lambda x: "★" * x, key="bk_f_stelle")
    testo = f3.text_input("Cerca (argomento, tecnica, testo)", key="bk_f_testo")
    righe = banca.esercizi(sb, approvato=True, materia=None if materia == "Tutte" else materia,
                           difficolta=stelle or None, testo=testo or None, limite=300)
    st.caption(f"{len(righe)} esercizi mostrati (massimo 300).")
    if righe:
        df = pd.DataFrame([{
            "Elimina": False, "★": r.get("difficolta"), "Argomento": r.get("argomento") or "",
            "Tecniche": ", ".join(r.get("tecniche") or []), "Scuola": r.get("scuola") or "",
            "Testo": r.get("testo_latex") or ""} for r in righe])
        ed = st.data_editor(df, key="bk_lista", hide_index=True, use_container_width=True, num_rows="fixed",
                            disabled=["★", "Argomento", "Tecniche", "Scuola", "Testo"],
                            column_config={"Elimina": st.column_config.CheckboxColumn(width="small")})
        da_eliminare = [righe[i]["id"] for i in range(len(righe)) if bool(ed.iloc[i]["Elimina"])]
        if da_eliminare and st.button(f"Elimina {len(da_eliminare)} esercizi spuntati", key="bk_elimina"):
            banca.elimina_esercizi(sb, da_eliminare)
            st.session_state[_MSG] = [("avviso", f"{len(da_eliminare)} esercizi eliminati.")]
            st.rerun()

    with st.expander("File caricati"):
        for f in banca.elenco_fonti(sb):
            a, b = st.columns([5, 1])
            a.markdown(f"**{f['nome']}** · {f['tipo']} · {f.get('materia') or '—'} · {f.get('scuola') or '—'} — "
                       f"{f['approvati']} approvati, {f['in_attesa']} in attesa")
            if b.button("Elimina", key=f"bk_delf_{f['id']}"):
                banca.elimina_fonte(sb, f["id"])
                st.rerun()


# ── 4. MODELLI ────────────────────────────────────────────────────────────────

def _tab_modelli(sb):
    st.caption("Struttura delle verifiche caricate (sezioni, punti, facoltativi). Quelle approvate saranno usate come modello di stile e distribuzione.")
    elenco = banca.modelli(sb)
    if not elenco:
        st.info("Nessun modello: carica una verifica in LaTeX (.tex) e compare qui.")
        return
    for m in elenco:
        s = m["struttura"]
        with st.expander(("✅ " if m["approvato"] else "⏳ ") + m["nome"]):
            st.markdown(f"Punti base **{s.get('punti_base')}** + facoltativi **{s.get('punti_extra')}** = **{s.get('totale')}**"
                        + (f" · base PDP/DSA {s['base_pdp_dsa']}" if s.get("base_pdp_dsa") else ""))
            st.dataframe(pd.DataFrame([{
                "Sezione": x["nome"], "Tipo": x["tipo"], "Quesiti": x["n_quesiti"],
                "Punti": " · ".join("—" if p is None else str(p) for p in x["punti"]),
                "Facoltativi": ("tutto l'esercizio (*)" if x["facoltativi"] and len(x["facoltativi"]) == x["n_quesiti"]
                                else ", ".join(x["facoltativi"]) or "—")} for x in s.get("sezioni", [])]),
                hide_index=True, use_container_width=True)
            nome = st.text_input("Nome del modello", value=m["nome"], key=f"bk_mn_{m['id']}")
            b1, b2, b3 = st.columns(3)
            if b1.button("Disapprova" if m["approvato"] else "Approva", key=f"bk_ma_{m['id']}", use_container_width=True):
                banca.aggiorna_modello(sb, m["id"], {"approvato": not m["approvato"], "nome": nome})
                st.rerun()
            if b2.button("Salva nome", key=f"bk_ms_{m['id']}", use_container_width=True):
                banca.aggiorna_modello(sb, m["id"], {"nome": nome})
                st.rerun()
            if b3.button("Elimina", key=f"bk_md_{m['id']}", use_container_width=True):
                banca.elimina_modello(sb, m["id"])
                st.rerun()


# ── pagina ────────────────────────────────────────────────────────────────────

def render_banca(sb, torna_indietro):
    """Pagina Banca. torna_indietro(): funzione che riporta alla schermata di creazione."""
    h1, h2 = st.columns([5, 1])
    h1.markdown("## Banca esercizi")
    if h2.button("← Indietro", key="bk_indietro", use_container_width=True):
        torna_indietro()
        return
    if sb is None or not banca.tabelle_pronte(sb):
        _istruzioni_tabelle()
        return
    t1, t2, t3, t4 = st.tabs(["Carica", "Da approvare", "Banca", "Modelli"])
    with t1:
        _tab_carica(sb)
    with t2:
        _tab_approva(sb)
    with t3:
        _tab_banca(sb)
    with t4:
        _tab_modelli(sb)
