"""
ui_correzione.py — la zona «Correggi i compiti» (stage CORREZIONE): solo interfaccia. Dati e operazioni (AI, PDF, caricamenti) arrivano da main.py
tramite `ctx`; la logica sta in correzione.py.

Quattro passi: 1 La verifica · 2 I compiti · 3 Revisione · 4 Risultati. Tutto lo stato sta in `ctx["stato"]` (dizionario in sessione):
    fase, verifica {titolo, materia, scuola, struttura, soluzioni, origine}, alunni [...], scala, sel
I compiti degli alunni non si salvano mai: restano nella sessione finché il docente non li elimina.
"""
import html
import re

import streamlit as st

import correzione as cor

PASSI = ["La verifica", "I compiti", "Revisione", "Risultati"]
_COLORE_ESITO = {"corretto": "#16A34A", "parziale": "#D97706", "errato": "#DC2626", "vuoto": "#64748B", "illeggibile": "#7C3AED"}
_ETICHETTA_ESITO = {"corretto": "Corretto", "parziale": "Parziale", "errato": "Errato", "vuoto": "Vuoto", "illeggibile": "Illeggibile"}


def _esc(x) -> str:
    return html.escape(str(x if x is not None else ""))


def _css(T: dict) -> str:
    acc, f = T["accent"], "font-family:'DM Sans',sans-serif;"
    return (
        "<style>"
        ".st-key-blk_cor{max-width:62rem;margin:0 auto;}"
        f".cor-tit{{{f}font-size:2rem;font-weight:800;letter-spacing:-.03em;color:{T['text']};line-height:1.1;}}"
        f".cor-sub{{{f}font-size:.98rem;color:{T['text2']};margin:.35rem 0 .2rem;line-height:1.5;}}"
        f".cor-priv{{display:inline-flex;align-items:center;gap:.4rem;{f}font-size:.76rem;font-weight:650;color:{T['text2']};padding:.2rem .7rem;border-radius:999px;"
        f"border:1px solid {T['border']};background:{T['card']};margin-top:.3rem;}}"
        # stepper
        f".cor-steps{{display:flex;gap:.5rem;margin:1.1rem 0 1.3rem;{f}}}"
        f".cor-step{{flex:1;padding:.55rem .8rem;border-radius:14px;border:1px solid {T['border']};background:{T['card']};font-size:.82rem;font-weight:650;color:{T['muted']};"
        "display:flex;align-items:center;gap:.55rem;}"
        f".cor-step i{{font-style:normal;width:1.45rem;height:1.45rem;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;font-size:.74rem;"
        f"background:{T['border']};color:{T['text2']};}}"
        f".cor-step.on{{border-color:{acc};color:{T['text']};box-shadow:0 8px 20px {acc}22;}}"
        f".cor-step.on i{{background:linear-gradient(135deg,#2563EB,#1D4ED8);color:#fff;}}"
        f".cor-step.ok{{color:{T['text2']};}}.cor-step.ok i{{background:#16A34A;color:#fff;}}"
        # carte e numeri
        f".cor-card{{background:{T['card']};border:1px solid {T['border']};border-radius:18px;padding:1rem 1.15rem;margin:.4rem 0 .8rem;{f}}}"
        f".cor-card b.t{{display:block;font-size:1.05rem;color:{T['text']};}}.cor-card span.s{{font-size:.85rem;color:{T['text2']};}}"
        f".cor-voto{{{f}font-size:2.6rem;font-weight:800;letter-spacing:-.04em;line-height:1;color:{T['text']};}}"
        f".cor-voto small{{font-size:.9rem;font-weight:600;color:{T['text2']};letter-spacing:0;margin-left:.5rem;}}"
        f".cor-lab{{{f}font-size:.66rem;font-weight:800;letter-spacing:.1em;text-transform:uppercase;color:{T['muted']};margin:0 0 .25rem;}}"
        f".cor-pill{{display:inline-block;padding:.12rem .6rem;border-radius:999px;font-size:.72rem;font-weight:700;color:#fff;{f}}}"
        f".cor-warn{{display:inline-block;padding:.12rem .6rem;border-radius:999px;font-size:.72rem;font-weight:700;color:#92400E;background:#FEF3C7;border:1px solid #FCD34D;{f}}}"
        f".cor-bar{{height:.55rem;border-radius:999px;background:{T['border']};overflow:hidden;margin:.25rem 0 .6rem;}}"
        ".cor-bar i{display:block;height:100%;border-radius:999px;}"
        f".cor-rig{{{f}font-size:.9rem;color:{T['text']};font-weight:700;}}.cor-rig small{{display:block;font-weight:500;color:{T['muted']};font-size:.74rem;}}"
        "html body .stApp .st-key-blk_cor_lista button{justify-content:flex-start;text-align:left;border-radius:12px;min-height:2.6rem;padding:.3rem .8rem;}"
        "html body .stApp .st-key-blk_cor_lista button p{font-size:.84rem;font-weight:650;text-align:left;}"
        "@media (max-width:760px){.cor-steps{flex-wrap:wrap;}.cor-step{flex:1 1 45%;}}"
        "</style>"
    )


def _intestazione(T: dict, fase: int) -> None:
    st.markdown(_css(T), unsafe_allow_html=True)
    passi = "".join(
        f'<div class="cor-step {"on" if i + 1 == fase else ("ok" if i + 1 < fase else "")}"><i>{"✓" if i + 1 < fase else i + 1}</i>{p}</div>' for i, p in enumerate(PASSI))
    st.markdown('<div class="cor-tit">Correggi i compiti</div>'
                '<div class="cor-sub">Carica i compiti dei tuoi alunni: propongo punti e commenti, tu controlli. Ottieni voti, schede e gli argomenti da ripassare.</div>'
                '<span class="cor-priv">🔒 I compiti restano solo in questa sessione: non vengono salvati</span>'
                f'<div class="cor-steps">{passi}</div>', unsafe_allow_html=True)


def _barra(percentuale: float, colore: str) -> str:
    return f'<div class="cor-bar"><i style="width:{max(2, min(100, percentuale))}%;background:{colore};"></i></div>'


# ── Passo 1: la verifica ──────────────────────────────────────────────────────
def _passo_verifica(T: dict, ctx: dict) -> None:
    S = ctx["stato"]
    v = S.get("verifica")
    if v:
        s = v["struttura"]
        nr = sum(len(e["richieste"]) for e in s["esercizi"])
        st.markdown(f'<div class="cor-card"><div class="cor-lab">Verifica scelta</div><b class="t">{_esc(v["titolo"])}</b>'
                    f'<span class="s">{_esc(v.get("materia", ""))} · {len(s["esercizi"])} esercizi · {nr} richieste · {s["totale"]:g} punti</span></div>', unsafe_allow_html=True)
        if s.get("punti_assegnati"):
            st.info("Nella verifica non ci sono punteggi: ho diviso 100 punti in parti uguali tra le richieste.", icon="ℹ️")
        with st.expander("Soluzioni di riferimento (le uso per correggere): controllale e correggile se serve", expanded=False, icon=":material/fact_check:"):
            v["soluzioni"] = st.text_area("Soluzioni", value=v.get("soluzioni", ""), height=260, label_visibility="collapsed", key="cor_soluzioni",
                                          help="Se una soluzione è sbagliata, correggila qui: i compiti si correggono sulla base di questo testo.")
        c1, c2 = st.columns([3, 1.4], gap="small")
        if c1.button("Continua: carica i compiti", key="cor_p1_ok", type="primary", icon=":material/arrow_forward:", use_container_width=True):
            S["fase"] = 2
            st.rerun()
        if c2.button("Cambia verifica", key="cor_p1_cambia", type="secondary", use_container_width=True):
            S["verifica"] = None
            st.rerun()
        return

    sorgente = st.segmented_control("Da dove parto", ["Una mia verifica", "Carico la traccia"], default="Una mia verifica", key="cor_sorgente", label_visibility="collapsed") or "Una mia verifica"
    if sorgente == "Una mia verifica":
        opzioni = ctx["opzioni_verifiche"]
        if not opzioni:
            st.info("Non hai ancora verifiche salvate. Crea una verifica, oppure carica la traccia della tua.", icon="ℹ️")
        else:
            idx = st.selectbox("Verifica", range(len(opzioni)), format_func=lambda i: opzioni[i]["etichetta"], key="cor_scelta", label_visibility="collapsed")
            if st.button("Usa questa verifica", key="cor_usa", type="primary", icon=":material/check:", use_container_width=True):
                errore = ctx["scegli"](opzioni[idx]["id"])
                if errore:
                    st.warning(errore)
                else:
                    st.rerun()
    else:
        st.caption("Carica la traccia (PDF o foto): la leggo come per «Impagina». Poi la correzione usa i suoi punteggi.")
        files = st.file_uploader("Traccia", type=["pdf", "png", "jpg", "jpeg", "webp"], accept_multiple_files=True, key=f"cor_traccia_{S.get('ciclo', 0)}",
                                 label_visibility="collapsed")
        c1, c2 = st.columns(2, gap="small")
        materia = c1.selectbox("Materia", ctx["materie"], key="cor_materia")
        scuola = c2.selectbox("Scuola", ctx["scuole"], key="cor_scuola")
        if st.button("Leggi la traccia", key="cor_leggi", type="primary", icon=":material/auto_fix_high:", use_container_width=True, disabled=not files):
            errore = ctx["leggi_traccia"]([{"data": f.getvalue(), "mime_type": f.type or "image/jpeg", "name": f.name} for f in files], materia, scuola)
            if errore:
                st.warning(errore)
            else:
                st.rerun()


# ── Passo 2: i compiti ────────────────────────────────────────────────────────
def _nome_da_file(nome: str) -> str:
    base = re.sub(r"\.[A-Za-z0-9]{2,4}$", "", nome or "")
    base = re.sub(r"[_\-]+", " ", base).strip()
    return base[:40] if not re.fullmatch(r"(?i)(img|dsc|image|scan|foto|photo|whatsapp)?[\s\d]*", base) else ""


def _passo_compiti(T: dict, ctx: dict) -> None:
    S = ctx["stato"]
    if S.get("alunni"):
        st.markdown(f'<div class="cor-card"><b class="t">Hai già corretto {len(S["alunni"])} compiti</b><span class="s">Puoi riprendere la revisione dal punto in cui eri.</span></div>',
                    unsafe_allow_html=True)
        c1, c2 = st.columns([3, 1.6], gap="small")
        if c1.button("Vai alla revisione", key="cor_p2_rev", type="primary", icon=":material/arrow_forward:", use_container_width=True):
            S["fase"] = 3
            st.rerun()
        if c2.button("Carica altri compiti", key="cor_p2_altri", type="secondary", use_container_width=True):
            S["alunni"], S["sel"] = [], None
            st.rerun()
        return
    st.markdown('<div class="cor-card"><b class="t">Un file per alunno</b>'
                '<span class="s">PDF o foto del compito. Se un alunno ha più pagine, mettile in un unico PDF. Il nome lo leggo dall\'intestazione, ma puoi scriverlo tu.</span></div>',
                unsafe_allow_html=True)
    files = st.file_uploader("Compiti", type=["pdf", "png", "jpg", "jpeg", "webp"], accept_multiple_files=True, key=f"cor_compiti_{S.get('ciclo', 0)}",
                             label_visibility="collapsed")
    if not files:
        if st.button("← Torna alla verifica", key="cor_p2_back", type="tertiary"):
            S["fase"] = 1
            st.rerun()
        return
    if len(files) > ctx["max_studenti"]:
        st.warning(f"Posso correggere al massimo {ctx['max_studenti']} compiti per volta: ho preso i primi {ctx['max_studenti']}.")
        files = files[:ctx["max_studenti"]]
    st.markdown('<div class="cor-lab">Nomi (facoltativi)</div>', unsafe_allow_html=True)
    nomi = []
    colonne = st.columns(2, gap="small")
    for i, f in enumerate(files):
        nomi.append(colonne[i % 2].text_input(f"Alunno {i + 1}", value=_nome_da_file(f.name), key=f"cor_nome_{S.get('ciclo', 0)}_{i}_{f.name}",
                                              label_visibility="collapsed", placeholder=f"Alunno {i + 1} · {f.name[:24]}"))
    secondi = max(1, -(-len(files) // 3)) * 25
    c1, c2 = st.columns([3, 1.2], gap="small")
    if c1.button(f"Correggi {len(files)} {'compito' if len(files) == 1 else 'compiti'}", key="cor_p2_vai", type="primary", icon=":material/auto_awesome:",
                 use_container_width=True, help=f"Di solito ci vogliono circa {secondi} secondi."):
        errore = ctx["correggi"]([(n.strip(), [{"data": f.getvalue(), "mime_type": f.type or "image/jpeg", "name": f.name}]) for n, f in zip(nomi, files)])
        if errore:
            st.warning(errore)
        else:
            S["fase"] = 3
            st.rerun()
    c2.caption(f"≈ {secondi} secondi")


# ── Passo 3: revisione ────────────────────────────────────────────────────────
def _etichetta_alunno(a: dict, scala: str) -> str:
    if a.get("errore"):
        return f"{a.get('nome') or 'Alunno'} · non letto"
    if a.get("non_corrisponde"):
        return f"{a.get('nome') or 'Alunno'} · altra verifica?"
    p, m = cor.punti_alunno(a["righe"])
    dub = cor.da_controllare(a)
    return f"{a.get('nome') or 'Alunno'} · {cor.voto_testo(cor.voto(p, m, scala))}" + (f" · ⚠ {dub}" if dub else (" · ✓" if a.get("controllato") else ""))


def _riga_correzione(T: dict, a: dict, r: dict, scala: str) -> None:
    c1, c2, c3, c4 = st.columns([1.5, 1.1, 1.0, 3.6], gap="small", vertical_alignment="center")
    c1.markdown(f'<div class="cor-rig">{_esc(r["id"])}<small>{_esc(cor.titolo_breve(r["titolo"]))[:28]}</small></div>', unsafe_allow_html=True)
    nuovo = c2.number_input(f"Punti {r['id']}", min_value=0.0, max_value=float(r["punti_max"]), value=float(r["punti"]), step=0.5, key=f"cor_p_{a['id']}_{r['id']}",
                            label_visibility="collapsed", format="%g")
    if abs(float(nuovo) - float(r["punti"])) > 1e-9:
        r["punti"], r["rivista"] = float(nuovo), True
        a["controllato"] = False
    c3.markdown(f'<span class="cor-pill" style="background:{_COLORE_ESITO.get(r["esito"], "#64748B")}">{_ETICHETTA_ESITO.get(r["esito"], r["esito"])}</span>'
                f'<br><span style="font-size:.7rem;color:{T["muted"]};font-family:DM Sans,sans-serif;">max {r["punti_max"]:g}</span>', unsafe_allow_html=True)
    com = c4.text_input(f"Commento {r['id']}", value=r.get("commento", ""), key=f"cor_c_{a['id']}_{r['id']}", label_visibility="collapsed", placeholder="Commento per l'alunno")
    if com != r.get("commento", ""):
        r["commento"] = com
    if r.get("da_controllare") and not r.get("rivista"):
        c4.markdown('<span class="cor-warn">⚠ Da controllare: non sono sicuro di questa valutazione</span>', unsafe_allow_html=True)


def _passo_revisione(T: dict, ctx: dict) -> None:
    S = ctx["stato"]
    alunni = S.get("alunni") or []
    if not alunni:
        S["fase"] = 2
        st.rerun()
    S["scala"] = st.selectbox("Come calcolo il voto", list(cor.SCALE), index=list(cor.SCALE).index(S.get("scala", cor.SCALA_PREDEFINITA)),
                              format_func=lambda k: cor.SCALE[k], key="cor_scala", help="Il voto lo calcola il programma dai punti; puoi cambiare il criterio in ogni momento.")
    scala = S["scala"]
    controllati = sum(1 for a in alunni if cor.valido(a) and cor.da_controllare(a) == 0)
    st.markdown(f'<div class="cor-lab">Controllati {controllati} di {len([a for a in alunni if cor.valido(a)])}</div>', unsafe_allow_html=True)
    st.markdown(_barra(100 * controllati / max(1, len(alunni)), "#16A34A"), unsafe_allow_html=True)

    col_l, col_r = st.columns([1.05, 3.2], gap="large")
    with col_l:
        st.markdown('<div class="cor-lab">Alunni</div>', unsafe_allow_html=True)
        ids = [a["id"] for a in alunni]
        if S.get("sel") not in ids:
            S["sel"] = ids[0]
        sel_id = S["sel"]
        with st.container(key="blk_cor_lista"):
            for x in alunni:
                if st.button(_etichetta_alunno(x, scala), key=f"cor_pick_{x['id']}", use_container_width=True, type="primary" if x["id"] == sel_id else "secondary"):
                    S["sel"] = x["id"]
                    st.rerun()
    a = next(x for x in alunni if x["id"] == sel_id)
    with col_r:
        if a.get("errore"):
            st.warning(a["errore"])
            if st.button("Riprova con questo compito", key=f"cor_riprova_{a['id']}", icon=":material/refresh:"):
                ctx["riprova"](a["id"])
                st.rerun()
            return
        if a.get("non_corrisponde"):
            st.warning("Queste pagine non sembrano il compito di questa verifica. Controlla di aver caricato il file giusto.")
            if st.button("Correggi comunque", key=f"cor_comunque_{a['id']}", icon=":material/refresh:"):
                a["non_corrisponde"] = False
                st.rerun()
            return
        a["nome"] = st.text_input("Nome", value=a.get("nome", ""), key=f"cor_nm_{a['id']}", placeholder="Nome dell'alunno", label_visibility="collapsed")
        ph = st.empty()
        pagine = ctx["anteprima"](a)
        if pagine:
            with st.expander("Guarda il compito", expanded=False, icon=":material/photo_library:"):
                for img in pagine[:6]:
                    try:
                        st.image(img, use_container_width=True)
                    except Exception:                      # una foto rovinata non deve bloccare la revisione
                        st.caption("(anteprima di questa pagina non disponibile)")
        st.markdown('<div class="cor-lab" style="margin-top:.6rem">Richiesta · punti · esito · commento</div>', unsafe_allow_html=True)
        for r in a["righe"]:
            _riga_correzione(T, a, r, scala)
        a["commento_generale"] = st.text_area("In sintesi", value=a.get("commento_generale", ""), key=f"cor_cg_{a['id']}", height=80, placeholder="In sintesi (appare nella scheda)")
        p, m = cor.punti_alunno(a["righe"])
        v = cor.voto(p, m, scala)
        colore = "#16A34A" if v >= 6 else "#DC2626"
        ph.markdown(f'<div class="cor-card"><div class="cor-lab">Voto proposto</div><div class="cor-voto" style="color:{colore}">{cor.voto_testo(v)}<small>{p:g} punti su {m:g}</small></div>'
                    f'{_barra(100 * p / max(1, m), colore)}</div>', unsafe_allow_html=True)
        b1, b2, b3 = st.columns([1.6, 1.6, 1.4], gap="small")
        if b1.button("✓ Controllato", key=f"cor_ok_{a['id']}", type="primary", use_container_width=True):
            a["controllato"] = True
            for r in a["righe"]:
                r["rivista"] = True
            i = [x["id"] for x in alunni].index(a["id"])
            S["sel"] = alunni[min(i + 1, len(alunni) - 1)]["id"]
            st.rerun()
        pdf = ctx["scheda_pdf"](a["id"]) if st.session_state.get(f"cor_vedi_{a['id']}") else None
        if pdf:
            b2.download_button("Scarica la scheda", data=pdf, file_name=f"scheda_{re.sub(r'[^A-Za-z0-9]+', '_', a.get('nome') or 'alunno')}.pdf", mime="application/pdf",
                               key=f"cor_dl_{a['id']}", use_container_width=True, icon=":material/download:")
        elif b2.button("Prepara la scheda", key=f"cor_sch_{a['id']}", type="secondary", use_container_width=True, icon=":material/description:"):
            st.session_state[f"cor_vedi_{a['id']}"] = True
            st.rerun()
        if b3.button("Escludi", key=f"cor_escl_{a['id']}", type="tertiary", use_container_width=True, help="Toglie questo compito dalla classe."):
            S["alunni"] = [x for x in alunni if x["id"] != a["id"]]
            S["sel"] = None
            st.rerun()
    st.divider()
    c1, c2 = st.columns([3, 1.4], gap="small")
    if c1.button("Vedi i risultati della classe", key="cor_p3_ok", type="primary", icon=":material/arrow_forward:", use_container_width=True):
        S["fase"] = 4
        st.rerun()
    if c2.button("← Compiti", key="cor_p3_back", type="secondary", use_container_width=True):
        S["fase"] = 2
        st.rerun()


# ── Passo 4: risultati ────────────────────────────────────────────────────────
def _passo_risultati(T: dict, ctx: dict) -> None:
    S = ctx["stato"]
    scala = S.get("scala", cor.SCALA_PREDEFINITA)
    stat = cor.statistiche(S.get("alunni") or [], S["verifica"]["struttura"], scala)
    if not stat["n"]:
        st.info("Non c'è ancora nessun compito corretto da mostrare.")
        if st.button("← Revisione", key="cor_p4_back0"):
            S["fase"] = 3
            st.rerun()
        return
    m1, m2, m3, m4 = st.columns(4, gap="small")
    m1.metric("Compiti corretti", stat["n"])
    m2.metric("Media", cor.voto_testo(stat["media"]))
    m3.metric("Mediana", cor.voto_testo(stat["mediana"]))
    m4.metric("Sufficienti", f"{stat['sufficienti']} su {stat['n']}")
    c_l, c_r = st.columns(2, gap="large")
    with c_l:
        st.markdown('<div class="cor-lab">Distribuzione dei voti</div>', unsafe_allow_html=True)
        try:
            import pandas as pd
            st.bar_chart(pd.DataFrame({"Alunni": list(stat["distribuzione"].values())}, index=list(stat["distribuzione"].keys())), height=220, color="#2563EB")
        except Exception:
            st.write(stat["distribuzione"])
    with c_r:
        st.markdown('<div class="cor-lab">Come è andata ogni esercizio</div>', unsafe_allow_html=True)
        for e in stat["esercizi"]:
            colore = "#16A34A" if e["percentuale"] >= 70 else ("#D97706" if e["percentuale"] >= 60 else "#DC2626")
            st.markdown(f'<div class="cor-rig">{e["n"]}. {_esc(e["titolo"])[:48]} <span style="float:right;color:{colore}">{e["percentuale"]}%</span></div>{_barra(e["percentuale"], colore)}',
                        unsafe_allow_html=True)
    ripassare = cor.da_ripassare(stat)
    if ripassare:
        st.markdown('<div class="cor-card"><div class="cor-lab">Da ripassare</div><b class="t">'
                    + " · ".join(_esc(e["titolo"]) for e in ripassare[:3]) + '</b><span class="s">Gli esercizi in cui la classe ha preso meno del 60% dei punti.</span></div>',
                    unsafe_allow_html=True)
    else:
        st.success("Nessun esercizio sotto il 60%: buoni risultati su tutta la verifica.", icon="✅")

    st.markdown('<div class="cor-lab" style="margin-top:.8rem">Documenti</div>', unsafe_allow_html=True)
    d1, d2, d3 = st.columns(3, gap="small")
    rep = ctx["report_pdf"]() if st.session_state.get("cor_vedi_report") else None
    if rep:
        d1.download_button("Resoconto della classe (PDF)", data=rep, file_name="resoconto_classe.pdf", mime="application/pdf", key="cor_dl_rep", use_container_width=True,
                           type="primary", icon=":material/download:")
    elif d1.button("Prepara il resoconto (PDF)", key="cor_rep", type="primary", use_container_width=True, icon=":material/summarize:"):
        st.session_state["cor_vedi_report"] = True
        st.rerun()
    zipb = ctx["zip_schede"]() if st.session_state.get("cor_vedi_zip") else None
    if zipb:
        d2.download_button("Schede degli alunni (ZIP)", data=zipb, file_name="schede_alunni.zip", mime="application/zip", key="cor_dl_zip", use_container_width=True,
                           icon=":material/folder_zip:")
    elif d2.button("Prepara le schede (ZIP)", key="cor_zip", type="secondary", use_container_width=True, icon=":material/folder_zip:"):
        st.session_state["cor_vedi_zip"] = True
        st.rerun()
    d3.download_button("Voti (CSV)", data=ctx["csv"]().encode("utf-8-sig"), file_name="voti.csv", mime="text/csv", key="cor_dl_csv", use_container_width=True,
                       icon=":material/table_view:")

    st.markdown('<div class="cor-lab" style="margin-top:.8rem">E adesso?</div>', unsafe_allow_html=True)
    e1, e2 = st.columns([3, 2], gap="small")
    if ripassare or stat["esercizi"]:
        if e1.button("Prepara un recupero su questi argomenti", key="cor_recupero", type="primary", icon=":material/auto_awesome:", use_container_width=True,
                     help="Apro la creazione di una verifica con gli argomenti in cui la classe è andata peggio."):
            ctx["recupero"](cor.indicazioni_recupero(stat))
    if e2.button("Elimina i dati degli alunni", key="cor_azzera", type="secondary", icon=":material/delete:", use_container_width=True,
                 help="Cancella compiti, nomi e correzioni da questa sessione."):
        ctx["azzera"]()
    if st.button("← Torna alla revisione", key="cor_p4_back", type="tertiary"):
        S["fase"] = 3
        st.rerun()


def render_correzione(T: dict, ctx: dict) -> None:
    """La pagina: intestazione, passi e contenuto del passo corrente. `ctx` lo prepara main.py (vedi i campi usati qui sopra)."""
    S = ctx["stato"]
    with st.container(key="blk_cor"):
        if st.button("Indietro", key="cor_indietro", type="tertiary", icon=":material/arrow_back:"):
            ctx["indietro"]()
        fase = int(S.get("fase", 1))
        if fase > 1 and not S.get("verifica"):
            fase = S["fase"] = 1
        _intestazione(T, fase)
        if ctx.get("bloccato"):
            st.caption("La correzione dei compiti è una delle funzioni complete, da sbloccare con il questionario.")
            ctx["pulsante_pro"]()
            return
        {1: _passo_verifica, 2: _passo_compiti, 3: _passo_revisione, 4: _passo_risultati}[fase](T, ctx)
