"""
ui_agente.py — l'interfaccia dell'agente (solo disegno, nessuna logica AI né accesso ai dati).

`render_home` disegna la barra «Cosa ti serve?» con la conversazione (bolle: le tue a destra, quelle dell'assistente a sinistra), le domande con
risposte rapide e il riepilogo di ciò che l'agente ha capito. Restituisce un EVENTO (o None) e main.py decide cosa fare:
    {"tipo": "testo", "testo": str, "files": list}   il docente ha scritto (e magari allegato) qualcosa
    {"tipo": "opzione", "testo": str}                ha scelto una risposta rapida
    {"tipo": "conferma"}                             «Crea verifica»
    {"tipo": "impagina_conferma"}                    «Impagina» (file allegati)
    {"tipo": "ritocco", "campo": "esercizi"|"eccellenza"|"punteggi", "delta": int, "valore": bool}   piccola correzione della scheda, senza AI
    {"tipo": "modulo"}                               «Modifica nel modulo»
    {"tipo": "annulla"}                              ha cambiato idea / nuova conversazione
    {"tipo": "vai", "dove": "impagina"|"libro"|"storico"}

Regola di stile del progetto: i contenitori `blk_…` non condividono la radice del nome con i pulsanti che contengono; qui si usano classi esatte.
"""
import html

import streamlit as st
import streamlit.components.v1 as components

import agente


def _esc(x) -> str:
    return html.escape(str(x if x is not None else ""))


def _css_pillole(T: dict) -> str:
    """Risposte rapide e scorciatoie come pillole (valgono anche nella pagina finale)."""
    acc = T["accent"]
    return (
        "<style>"
        "html body .stApp [class*='st-key-blk_ag_pill'] button{border-radius:999px !important;min-height:2.3rem !important;padding:.15rem .95rem !important;"
        f"border:1.5px solid {acc}55 !important;background:{T['card']} !important;box-shadow:none !important;transition:all .15s ease !important;}}"
        f"html body .stApp [class*='st-key-blk_ag_pill'] button p{{color:{acc} !important;font-weight:650 !important;font-size:.86rem !important;}}"
        f"html body .stApp [class*='st-key-blk_ag_pill'] button:hover{{background:{acc} !important;border-color:{acc} !important;transform:translateY(-1px);"
        f"box-shadow:0 8px 18px {acc}38 !important;}}"
        "html body .stApp [class*='st-key-blk_ag_pill'] button:hover p,html body .stApp [class*='st-key-blk_ag_pill'] button:hover span{color:#fff !important;}"
        "</style>"
    )


def _css(T: dict) -> str:
    acc, acc2 = T["accent"], T.get("accent2", T["accent"])
    f = "font-family:'DM Sans',sans-serif;"
    return (
        "<style>"
        ".st-key-blk_agente{max-width:46rem;margin:0 auto;}"
        # ── titolo ────────────────────────────────────────────────────────────
        f".ag-hero{{text-align:center;margin:1.4rem 0 1.5rem;{f}}}"
        f".ag-hero b{{display:block;font-size:2.5rem;font-weight:800;letter-spacing:-.04em;line-height:1.08;color:{T['text']};}}"
        f".ag-hero b em{{font-style:normal;background:linear-gradient(100deg,{acc},{acc2});-webkit-background-clip:text;background-clip:text;color:transparent;}}"
        f".ag-hero span{{display:block;margin-top:.7rem;font-size:1.02rem;line-height:1.5;color:{T['text2']};}}"
        f".ag-cap{{text-align:center;margin:.85rem 0 0;font-size:.78rem;line-height:1.7;color:{T['muted']};{f}}}"
        f".ag-cap i{{font-style:normal;margin:0 .45rem;opacity:.5;}}"
        # ── casella di scrittura ──────────────────────────────────────────────
        f"html body .stApp .st-key-blk_agente [data-testid='stChatInput']{{background:{T['card']} !important;border:1.5px solid {T['border']} !important;"
        "border-radius:22px !important;padding:.3rem .35rem !important;box-shadow:0 18px 44px rgba(15,23,42,.08),0 2px 6px rgba(15,23,42,.04) !important;"
        "transition:border-color .2s ease,box-shadow .2s ease !important;}"
        f"html body .stApp .st-key-blk_agente [data-testid='stChatInput']:focus-within{{border-color:{acc} !important;"
        f"box-shadow:0 0 0 4px {acc}22,0 20px 48px {acc}2b !important;}}"
        "html body .stApp .st-key-blk_agente [data-testid='stChatInput'] > div,html body .stApp .st-key-blk_agente [data-testid='stChatInput'] > div > div,"
        "html body .stApp .st-key-blk_agente [data-testid='stChatInput'] textarea{background:transparent !important;border:none !important;box-shadow:none !important;}"
        f"html body .stApp .st-key-blk_agente [data-testid='stChatInput'] textarea{{font-size:1.03rem !important;color:{T['text']} !important;}}"
        f"html body .stApp .st-key-blk_agente [data-testid='stChatInput'] textarea::placeholder{{color:{T['muted']} !important;opacity:1;}}"
        f"html body .stApp .st-key-blk_agente [data-testid='stChatInputSubmitButton']{{background:linear-gradient(135deg,#2563EB,#1D4ED8) !important;"
        f"border-radius:14px !important;color:#fff !important;box-shadow:0 8px 18px #2563EB55 !important;transition:transform .15s ease !important;}}"
        "html body .stApp .st-key-blk_agente [data-testid='stChatInputSubmitButton']:hover{transform:scale(1.06);}"
        f"html body .stApp .st-key-blk_agente [data-testid='stChatInputSubmitButton']:disabled{{background:{T['border']} !important;box-shadow:none !important;}}"
        "html body .stApp .st-key-blk_agente [data-testid='stChatInputSubmitButton'] svg{fill:#fff !important;color:#fff !important;}"
        # ── conversazione: bolle ──────────────────────────────────────────────
        f".ag-top{{display:flex;align-items:center;justify-content:space-between;margin:.2rem 0 .5rem;{f}font-size:.72rem;font-weight:800;letter-spacing:.09em;"
        f"text-transform:uppercase;color:{T['muted']};}}"
        f".ag-row{{display:flex;gap:.6rem;margin:.6rem 0;align-items:flex-end;animation:ag-entra .3s ease both;{f}}}"
        ".ag-row.u{justify-content:flex-end;}"
        f".ag-av{{flex:0 0 2.1rem;width:2.1rem;height:2.1rem;border-radius:50%;display:flex;align-items:center;justify-content:center;color:#fff;"
        f"font-weight:800;font-size:.72rem;letter-spacing:-.02em;background:linear-gradient(135deg,#2563EB,#1D4ED8);box-shadow:0 6px 14px #2563EB44;}}"
        f".ag-bub{{max-width:80%;padding:.72rem 1.05rem;border-radius:20px;font-size:.96rem;line-height:1.5;word-wrap:break-word;}}"
        f".ag-row.u .ag-bub{{background:linear-gradient(135deg,#2563EB,#1D4ED8);color:#fff;border-bottom-right-radius:6px;box-shadow:0 10px 24px #2563EB40;}}"
        f".ag-row.b .ag-bub{{background:{T['card']};color:{T['text']};border:1px solid {T['border']};border-bottom-left-radius:6px;box-shadow:0 6px 18px rgba(15,23,42,.06);}}"
        ".ag-file{display:inline-flex;align-items:center;gap:.3rem;margin:.4rem .35rem 0 0;padding:.14rem .6rem;border-radius:999px;background:rgba(255,255,255,.22);font-size:.76rem;}"
        f".ag-dots{{display:inline-flex;gap:.28rem;padding:.2rem 0;}}"
        f".ag-dots i{{width:.45rem;height:.45rem;border-radius:50%;background:{T['muted']};animation:ag-punti 1.2s ease-in-out infinite;}}"
        ".ag-dots i:nth-child(2){animation-delay:.18s;}.ag-dots i:nth-child(3){animation-delay:.36s;}"
        "@keyframes ag-punti{0%,60%,100%{opacity:.25;transform:translateY(0);}30%{opacity:1;transform:translateY(-3px);}}"
        "@keyframes ag-entra{from{opacity:0;transform:translateY(8px);}to{opacity:1;transform:none;}}"
        # ── scheda «Ho capito» ────────────────────────────────────────────────
        f".ag-card{{margin:.5rem 0 .8rem 2.7rem;padding:1.05rem 1.2rem 1.1rem;border-radius:20px;background:{T['card']};border:1px solid {acc}40;"
        f"box-shadow:0 14px 34px {acc}18;{f}animation:ag-entra .3s ease both;position:relative;overflow:hidden;}}"
        f".ag-card::before{{content:'';position:absolute;left:0;top:0;bottom:0;width:4px;background:linear-gradient(180deg,{acc},{acc2});}}"
        f".ag-eye{{font-size:.68rem;font-weight:800;letter-spacing:.1em;text-transform:uppercase;color:{acc};margin-bottom:.35rem;}}"
        f".ag-card .ag-arg{{font-size:1.15rem;font-weight:800;letter-spacing:-.015em;color:{T['text']};line-height:1.3;}}"
        f".ag-card .ag-ind{{margin-top:.3rem;font-size:.88rem;color:{T['text2']};line-height:1.5;white-space:pre-line;}}"
        ".ag-chips{display:flex;flex-wrap:wrap;gap:.4rem;margin-top:.8rem;}"
        f".ag-chip{{font-size:.77rem;padding:.26rem .7rem;border-radius:999px;background:{acc}14;border:1px solid {acc}2e;color:{T['text']};}}"
        f".ag-chip i{{font-style:normal;color:{T['text2']};margin-right:.35rem;}}"
        f".ag-nota{{margin-top:.8rem;padding-top:.7rem;border-top:1px dashed {T['border']};font-size:.79rem;line-height:1.55;color:{T['text2']};}}"
        f".ag-nota b{{color:{T['text']};}}"
        f".ag-rit{{{f}font-size:.7rem;font-weight:800;letter-spacing:.09em;text-transform:uppercase;color:{T['muted']};margin:.2rem 0 .3rem;}}"
        "html body .stApp .st-key-blk_ag_azioni{margin-left:2.7rem;}"
        f"html body .stApp .st-key-blk_ag_rit{{background:{T['card']};border:1px solid {T['border']};border-radius:16px;padding:.75rem 1rem .6rem;margin:.1rem 0 .75rem;}}"
        f".ag-lab{{{f}font-size:.68rem;font-weight:800;letter-spacing:.09em;text-transform:uppercase;color:{T['muted']};margin:0 0 .3rem;}}"
        "html body .stApp .st-key-blk_ag_rit [data-testid='stNumberInput'] input{font-weight:700;font-size:1rem;text-align:center;}"
        "html body .stApp .st-key-blk_ag_rit [data-testid='stNumberInput'] > div{max-width:9.5rem;}"
        "@media (max-width:640px){.ag-hero b{font-size:2rem;}.ag-card,html body .stApp .st-key-blk_ag_azioni{margin-left:0;}.ag-bub{max-width:90%;}}"
        "@media (prefers-reduced-motion: reduce){.ag-row,.ag-card,.ag-dots i{animation:none !important;}}"
        "</style>" + _css_pillole(T)
    )


def _chip(etichetta: str, valore: str) -> str:
    return f'<span class="ag-chip"><i>{_esc(etichetta)}</i>{_esc(valore)}</span>'


def bolla_utente(testo: str, allegati: list | None = None) -> str:
    """La tua richiesta: bolla a destra. (main.py la mostra subito, prima della risposta.)"""
    files = "".join(f'<span class="ag-file">📎 {_esc(f)}</span>' for f in allegati or [])
    return f'<div class="ag-row u"><div class="ag-bub">{_esc(testo).replace(chr(10), "<br>")}{("<br>" + files) if files else ""}</div></div>'


def bolla_assistente(testo: str) -> str:
    return f'<div class="ag-row b"><div class="ag-av">AI</div><div class="ag-bub">{_esc(testo).replace(chr(10), "<br>")}</div></div>'


def bolla_scrive() -> str:
    """I tre puntini mentre l'assistente sta pensando."""
    return '<div class="ag-row b"><div class="ag-av">AI</div><div class="ag-bub"><span class="ag-dots"><i></i><i></i><i></i></span></div></div>'


def card_riepilogo(T: dict, dec: dict, default_ecc: bool = True) -> str:
    """Ciò che l'agente ha capito, in una scheda: argomento in evidenza, poi le scelte, poi le assunzioni dichiarate."""
    par = dec.get("crea") or {}
    chips = "".join(_chip(e, v) for e, v in agente.riepilogo(par, default_ecc))
    if dec.get("versioni"):
        chips += _chip("Poi preparo", ", ".join(agente.VERSIONI.get(k, k) for k in dec["versioni"]))
    ass = "".join(f"<div>• {_esc(a)}</div>" for a in dec.get("assunzioni") or [])
    nota = f'<div class="ag-nota"><b>Ho assunto:</b>{ass}</div>' if ass else ""
    resto = '<div class="ag-nota">Quello che non ho indicato lo imposto come al solito: puoi ritoccarlo qui sotto o in «Modifica nel modulo».</div>'
    return (f'<div class="ag-card"><div class="ag-eye">Ho capito</div><div class="ag-arg">{_esc(par.get("argomento") or "Verifica dagli appunti caricati")}</div>'
            + (f'<div class="ag-ind">{_esc(par["indicazioni"])}</div>' if par.get("indicazioni") else "")
            + f'<div class="ag-chips">{chips}</div>{nota}{resto}</div>')


def card_impagina(T: dict, dec: dict, nomi: list) -> str:
    """Scheda per i file allegati da impaginare: quali file, cosa farne, eventuali richieste del docente."""
    par = dec.get("crea") or {}
    chips = _chip("File", ", ".join(nomi)[:90] if nomi else "—")
    if par.get("materia"):
        chips += _chip("Materia", par["materia"])
    if par.get("scuola"):
        chips += _chip("Scuola", par["scuola"])
    richiesta = dec.get("modifica") or par.get("indicazioni") or ""
    return ('<div class="ag-card"><div class="ag-eye">Ho capito</div><div class="ag-arg">Impagino la tua verifica</div>'
            + (f'<div class="ag-ind">Poi: {_esc(richiesta)}</div>' if richiesta else '<div class="ag-ind">Gli esercizi restano identici: li rimetto in pagina con intestazione e punteggi.</div>')
            + f'<div class="ag-chips">{chips}</div>'
            '<div class="ag-nota">Leggo le pagine, ricontrollo i numeri e ti mostro la verifica pronta: se qualcosa non è uguale, lo correggi a parole.</div></div>')


def opzioni_rapide(opzioni: list, prefisso: str, T: dict | None = None) -> str | None:
    """Risposte rapide a una domanda, come pillole: restituisce il testo di quella premuta."""
    if not opzioni:
        return None
    if T:
        st.markdown(_css_pillole(T), unsafe_allow_html=True)
    scelta = None
    with st.container(key=f"blk_ag_pill_{prefisso}"):
        colonne = st.columns(min(len(opzioni), 4), gap="small")
        for i, (col, o) in enumerate(zip(colonne, opzioni)):
            if col.button(o, key=f"{prefisso}_{i}", use_container_width=True, type="secondary"):
                scelta = o
    return scelta


def suggerimenti_rapidi(items: list, prefisso: str, T: dict | None = None) -> str | None:
    """Scorciatoie sotto la casella della pagina finale: [(etichetta, testo)] → testo di quella premuta (nessuna attesa: le risolve il codice)."""
    if not items:
        return None
    if T:
        st.markdown(_css_pillole(T), unsafe_allow_html=True)
    scelta = None
    st.markdown(f'<div style="font-family:DM Sans,sans-serif;font-size:.7rem;font-weight:800;letter-spacing:.09em;text-transform:uppercase;'
                f'color:{(T or {}).get("muted", "#94A3B8")};margin:.2rem 0 .3rem;">Con un tocco</div>', unsafe_allow_html=True)
    with st.container(key=f"blk_ag_pill_{prefisso}"):
        colonne = st.columns(len(items), gap="small")
        for i, (col, (et, testo)) in enumerate(zip(colonne, items)):
            if col.button(et, key=f"{prefisso}_{i}", use_container_width=True, type="secondary", icon=":material/bolt:"):
                scelta = testo
    return scelta


def _ritocchi(dec: dict):
    """Piccole correzioni alla scheda senza chiamare l'AI: quanti esercizi in tutto, esercizio per l'eccellenza, tabella dei punti.
    Il numero mostrato è sempre quello vero (se il docente non l'ha detto, quello che si userebbe)."""
    par = dec.get("crea") or {}
    evento = None
    with st.container(key="blk_ag_rit"):
        c1, c2, c3 = st.columns([1.15, 1.2, 1.3], gap="medium", vertical_alignment="bottom")
        n_ora = par.get("num_esercizi") or agente.totale_predefinito(par)
        c1.markdown('<div class="ag-lab">Esercizi in tutto</div>', unsafe_allow_html=True)
        n_nuovo = c1.number_input("Esercizi in tutto", min_value=3, max_value=11, value=int(n_ora), step=1, key=f"ag_n_{n_ora}_{par.get('eccellenza')}",
                                  label_visibility="collapsed", help="Compreso l'esercizio per l'eccellenza, se c'è.")
        if int(n_nuovo) != int(n_ora):
            evento = {"tipo": "ritocco", "campo": "esercizi", "valore": int(n_nuovo)}
        ecc = par.get("eccellenza")
        ecc_v = True if ecc is None else bool(ecc)
        nuovo = c2.toggle("Esercizio per l'eccellenza", value=ecc_v, key=f"ag_ecc_{ecc}", help="Un esercizio finale facoltativo, più difficile, con pochi punti.")
        if nuovo != ecc_v:
            evento = {"tipo": "ritocco", "campo": "eccellenza", "valore": nuovo}
        pun = par.get("punteggi")
        pun_v = True if pun is None else bool(pun)
        nuovo_p = c3.toggle("Tabella dei punteggi", value=pun_v, key=f"ag_pun_{pun}", help="In fondo alla verifica, da compilare con i voti.")
        if nuovo_p != pun_v:
            evento = {"tipo": "ritocco", "campo": "punteggi", "valore": nuovo_p}
    return evento


def render_home(T: dict, chat: list, blocco: str | None, bloccate: list, allegati: list | None = None, js_microfono: str = "",
                in_arrivo: dict | None = None) -> dict | None:
    """Barra + conversazione della schermata iniziale. `blocco` = testo se non si può creare ora (limite mensile); `bloccate` = versioni non disponibili;
    `allegati` = nomi dei file allegati nella barra; `js_microfono` = script della dettatura (lo prepara main.py).
    `in_arrivo` = la richiesta appena inviata ({"testo", "nomi"}) mentre l'assistente la sta capendo: compare in coda alla storia, con i tre puntini."""
    evento = None
    with st.container(key="blk_agente"):
        st.markdown(_css(T), unsafe_allow_html=True)
        if not chat and not in_arrivo:
            st.markdown('<div class="ag-hero"><b>Cosa ti <em>serve</em>?</b>'
                        '<span>Descrivi la verifica come la diresti a un collega.<br>Al resto penso io.</span></div>', unsafe_allow_html=True)
        else:
            c_a, c_b = st.columns([3, 1.4], vertical_alignment="center")
            c_a.markdown('<div class="ag-top">Conversazione</div>', unsafe_allow_html=True)
            if c_b.button("Nuova richiesta", key="ag_nuova", type="tertiary", icon=":material/restart_alt:", use_container_width=True):
                evento = {"tipo": "annulla"}
        for m in chat:
            if m.get("stage", "home") != "home":
                continue
            if m["ruolo"] == "utente":
                st.markdown(bolla_utente(m["testo"], m.get("allegati")), unsafe_allow_html=True)
            elif m.get("testo"):
                st.markdown(bolla_assistente(m["testo"]), unsafe_allow_html=True)

        if in_arrivo:                                    # la scheda e i pulsanti di prima non servono più: c'è una richiesta nuova in lavorazione
            st.markdown(bolla_utente(in_arrivo["testo"], in_arrivo.get("nomi")) + bolla_scrive(), unsafe_allow_html=True)
        ultimo = chat[-1] if chat and chat[-1]["ruolo"] == "agente" and not in_arrivo else None
        dec = (ultimo or {}).get("decisione") or {}
        az = dec.get("azione")
        if az == "domanda":
            st.markdown(bolla_assistente(dec.get("domanda") or ""), unsafe_allow_html=True)
            with st.container(key="blk_ag_azioni"):
                sc = opzioni_rapide(dec.get("opzioni") or [], "ag_opt")
            if sc:
                evento = {"tipo": "opzione", "testo": sc}
        elif az == "crea":
            st.markdown(card_riepilogo(T, dec), unsafe_allow_html=True)
            with st.container(key="blk_ag_azioni"):
                nb = [k for k in dec.get("versioni") or [] if k in bloccate]
                if nb:
                    st.caption("Non posso ancora preparare: " + ", ".join(agente.VERSIONI.get(k, k) for k in nb) + " (funzioni complete da sbloccare).")
                if blocco:
                    st.warning(blocco)
                rit = _ritocchi(dec)
                if rit:
                    evento = rit
                c1, c2 = st.columns([3, 2], gap="small")
                if c1.button("Crea verifica", key="ag_crea", type="primary", icon=":material/auto_awesome:", use_container_width=True, disabled=bool(blocco)):
                    evento = {"tipo": "conferma"}
                if c2.button("Modifica nel modulo", key="ag_modulo", type="secondary", icon=":material/tune:", use_container_width=True):
                    evento = {"tipo": "modulo"}
                st.caption("Vuoi cambiare altro? Scrivilo qui sotto («meglio 6 esercizi», «aggiungi la fila B»…).")
        elif az == "impagina" and allegati:
            st.markdown(card_impagina(T, dec, allegati), unsafe_allow_html=True)
            with st.container(key="blk_ag_azioni"):
                if blocco:
                    st.warning(blocco)
                c1, c2 = st.columns([3, 2], gap="small")
                if c1.button("Impagina", key="ag_impagina", type="primary", icon=":material/auto_fix_high:", use_container_width=True, disabled=bool(blocco)):
                    evento = {"tipo": "impagina_conferma"}
                if c2.button("Annulla", key="ag_annulla_imp", type="secondary", use_container_width=True):
                    evento = {"tipo": "annulla"}
        elif az in ("impagina", "libro", "storico"):
            etichetta = {"impagina": "Impagina la mia verifica", "libro": "Apri il modulo e aggiungi la foto", "storico": "Apri «Le mie verifiche»"}[az]
            icona = {"impagina": ":material/upload_file:", "libro": ":material/photo_camera:", "storico": ":material/folder_open:"}[az]
            with st.container(key="blk_ag_azioni"):
                if st.button(etichetta, key="ag_vai", type="primary", icon=icona):
                    evento = {"tipo": "vai", "dove": az}

        if js_microfono:
            with st.container(key="dettatura_ag"):
                components.html(js_microfono, height=0)
        invio = st.chat_input("Scrivi o detta cosa ti serve…", key="ag_in", accept_file="multiple",
                              file_type=["pdf", "png", "jpg", "jpeg", "webp", "docx"])
        if not chat and not in_arrivo:
            st.markdown('<div class="ag-cap">Argomento e classe<i>·</i>Fila B, soluzioni, versione per DSA<i>·</i>Appunti, foto o una verifica da sistemare</div>',
                        unsafe_allow_html=True)
        if invio and evento is None and not in_arrivo:
            if isinstance(invio, str):
                testo, files = invio.strip(), []
            else:
                testo = (getattr(invio, "text", None) or (invio.get("text") if isinstance(invio, dict) else "") or "").strip()
                files = list(getattr(invio, "files", None) or (invio.get("files") if isinstance(invio, dict) else []) or [])
            if testo or files:
                evento = {"tipo": "testo", "testo": testo, "files": files}
    return evento
