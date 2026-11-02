"""
ui_agente.py — l'interfaccia dell'agente (solo disegno, nessuna logica AI né accesso ai dati).

`render_home` disegna la barra «Cosa ti serve?» con la conversazione, le domande con risposte rapide e il riepilogo di ciò che l'agente
ha capito. Restituisce un EVENTO (o None) e main.py decide cosa fare:
    {"tipo": "testo", "testo": str, "files": list}   il docente ha scritto (e magari allegato) qualcosa
    {"tipo": "opzione", "testo": str}                ha scelto una risposta rapida o un esempio
    {"tipo": "conferma"}                             «Crea verifica»
    {"tipo": "impagina_conferma"}                    «Impagina» (file allegati)
    {"tipo": "ritocco", "campo": "esercizi"|"eccellenza"|"punteggi", "delta": int, "valore": bool}   piccola correzione della scheda, senza AI
    {"tipo": "modulo"}                               «Modifica nel modulo»
    {"tipo": "annulla"}                              ha cambiato idea
    {"tipo": "vai", "dove": "impagina"|"libro"|"storico"}
"""
import html

import streamlit as st
import streamlit.components.v1 as components

import agente

_ESEMPI_ICONE = [":material/school:", ":material/history_edu:", ":material/replay:"]


def _esc(x) -> str:
    return html.escape(str(x if x is not None else ""))


def _css(T: dict) -> str:
    acc, acc2 = T["accent"], T.get("accent2", T["accent"])
    return (
        "<style>"
        ".st-key-blk_agente{max-width:46rem;margin:0 auto;}"
        # intestazione con la scintilla che pulsa piano
        ".ag-hero{text-align:center;margin:.2rem 0 1.1rem;font-family:'DM Sans',sans-serif;}"
        f".ag-spark{{display:inline-flex;width:2.7rem;height:2.7rem;align-items:center;justify-content:center;border-radius:14px;margin-bottom:.55rem;"
        f"background:linear-gradient(135deg,{acc},{acc2});box-shadow:0 10px 26px {acc}55;animation:ag-pulsa 3.2s ease-in-out infinite;}}"
        "@keyframes ag-pulsa{0%,100%{transform:scale(1);}50%{transform:scale(1.07);}}"
        f".ag-hero b{{display:block;font-size:1.7rem;font-weight:800;letter-spacing:-.025em;color:{T['text']};line-height:1.15;}}"
        f".ag-hero span.ag-s{{display:block;font-size:.9rem;color:{T['text2']};margin-top:.4rem;line-height:1.45;}}"
        # la casella di scrittura: bordo che si accende quando ci si scrive
        f".st-key-blk_agente [data-testid='stChatInput']{{border-radius:18px;border:1.5px solid {acc}40;box-shadow:0 10px 28px {acc}14;"
        f"background:{T['card']};transition:border-color .18s ease,box-shadow .18s ease;}}"
        f".st-key-blk_agente [data-testid='stChatInput']:focus-within{{border-color:{acc};box-shadow:0 0 0 4px {acc}22,0 12px 32px {acc}26;}}"
        # messaggi
        f".st-key-blk_agente [data-testid='stChatMessage']{{border-radius:16px;background:{T['card']};border:1px solid {T['border']};"
        "animation:ag-entra .28s ease both;}"
        "@keyframes ag-entra{from{opacity:0;transform:translateY(6px);}to{opacity:1;transform:none;}}"
        # esempi come carte
        f".st-key-blk_ag_esempi button{{min-height:4.4rem;text-align:left;border-radius:16px;border:1px solid {T['border']};background:{T['card']};"
        "transition:transform .15s ease,box-shadow .15s ease,border-color .15s ease;}"
        f".st-key-blk_ag_esempi button:hover{{transform:translateY(-2px);border-color:{acc};box-shadow:0 10px 22px {acc}1f;}}"
        ".st-key-blk_ag_esempi button p{font-size:.84rem;line-height:1.35;}"
        # scheda di riepilogo
        f".ag-card{{margin:.2rem 0 .7rem;padding:1rem 1.1rem;border-radius:16px;background:linear-gradient(160deg,{T['card']} 0%,{acc}10 100%);"
        f"border:1px solid {acc}40;box-shadow:0 8px 22px {acc}14;font-family:'DM Sans',sans-serif;animation:ag-entra .3s ease both;}}"
        f".ag-card .ag-arg{{font-size:1.08rem;font-weight:800;color:{T['text']};line-height:1.3;}}"
        f".ag-card .ag-ind{{margin-top:.25rem;font-size:.86rem;color:{T['text2']};line-height:1.45;white-space:pre-line;}}"
        ".ag-chips{display:flex;flex-wrap:wrap;gap:.4rem;margin-top:.7rem;}"
        f".ag-chip{{font-size:.76rem;padding:.22rem .65rem;border-radius:999px;background:{acc}18;border:1px solid {acc}33;color:{T['text']};}}"
        f".ag-chip i{{font-style:normal;color:{T['text2']};margin-right:.3rem;}}"
        f".ag-nota{{margin-top:.7rem;font-size:.78rem;line-height:1.5;color:{T['text2']};}}"
        f".ag-nota b{{color:{T['text']};}}"
        f".ag-q{{font-size:1rem;font-weight:700;color:{T['text']};margin:.1rem 0 .5rem;font-family:'DM Sans',sans-serif;}}"
        f".ag-rit{{font-family:'DM Sans',sans-serif;font-size:.72rem;font-weight:800;letter-spacing:.07em;text-transform:uppercase;color:{T['muted']};margin:.1rem 0 .25rem;}}"
        "@media (prefers-reduced-motion: reduce){.ag-spark,.st-key-blk_agente [data-testid='stChatMessage'],.ag-card{animation:none !important;}}"
        "</style>"
    )


def _chip(etichetta: str, valore: str) -> str:
    return f'<span class="ag-chip"><i>{_esc(etichetta)}</i>{_esc(valore)}</span>'


_SCINTILLA = '<svg width="22" height="22" viewBox="0 0 24 24" fill="#fff"><path d="M12 2l2.4 6.6L21 11l-6.6 2.4L12 20l-2.4-6.6L3 11l6.6-2.4z"/></svg>'


def card_riepilogo(T: dict, dec: dict, default_ecc: bool = True) -> str:
    """Ciò che l'agente ha capito, in una scheda: argomento in evidenza, poi le scelte, poi le assunzioni dichiarate."""
    par = dec.get("crea") or {}
    chips = "".join(_chip(e, v) for e, v in agente.riepilogo(par, default_ecc))
    if dec.get("versioni"):
        chips += _chip("Poi preparo", ", ".join(agente.VERSIONI.get(k, k) for k in dec["versioni"]))
    ass = "".join(f"<div>• {_esc(a)}</div>" for a in dec.get("assunzioni") or [])
    nota = f'<div class="ag-nota"><b>Ho assunto:</b>{ass}</div>' if ass else ""
    resto = '<div class="ag-nota">Quello che non ho indicato lo imposto come al solito: lo puoi cambiare qui sotto o in «Modifica nel modulo».</div>'
    return (f'<div class="ag-card"><div class="ag-arg">{_esc(par.get("argomento") or "Verifica dagli appunti caricati")}</div>'
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
    return ('<div class="ag-card"><div class="ag-arg">Impagino la tua verifica</div>'
            + (f'<div class="ag-ind">Poi: {_esc(richiesta)}</div>' if richiesta else '<div class="ag-ind">Gli esercizi restano identici: li rimetto in pagina con intestazione e punteggi.</div>')
            + f'<div class="ag-chips">{chips}</div>'
            '<div class="ag-nota">Leggo le pagine, ricontrollo i numeri e ti mostro la verifica pronta: se qualcosa non è uguale, lo correggi a parole.</div></div>')


def opzioni_rapide(opzioni: list, prefisso: str) -> str | None:
    """Pulsanti con le risposte rapide a una domanda: restituisce il testo di quello premuto."""
    if not opzioni:
        return None
    scelta = None
    colonne = st.columns(min(len(opzioni), 4), gap="small")
    for i, (col, o) in enumerate(zip(colonne, opzioni)):
        if col.button(o, key=f"{prefisso}_{i}", use_container_width=True, type="secondary"):
            scelta = o
    return scelta


def suggerimenti_rapidi(items: list, prefisso: str) -> str | None:
    """Scorciatoie sotto la casella della pagina finale: [(etichetta, testo)] → testo di quella premuta (nessuna attesa: le risolve il codice)."""
    if not items:
        return None
    scelta = None
    st.markdown('<div class="ag-rit">Con un tocco</div>', unsafe_allow_html=True)
    colonne = st.columns(len(items), gap="small")
    for i, (col, (et, testo)) in enumerate(zip(colonne, items)):
        if col.button(et, key=f"{prefisso}_{i}", use_container_width=True, type="secondary", icon=":material/bolt:"):
            scelta = testo
    return scelta


def _ritocchi(dec: dict):
    """Piccole correzioni alla scheda senza chiamare l'AI: numero di esercizi, esercizio per l'eccellenza, tabella dei punti."""
    par = dec.get("crea") or {}
    st.markdown('<div class="ag-rit">Ritocca al volo</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns([1.5, 1, 1, 1.4], gap="small", vertical_alignment="center")
    n = par.get("num_esercizi")
    c1.caption(f"Esercizi: **{n if n else 'standard'}**")
    evento = None
    if c2.button("−", key="ag_meno", use_container_width=True, help="Un esercizio in meno"):
        evento = {"tipo": "ritocco", "campo": "esercizi", "delta": -1}
    if c3.button("+", key="ag_piu", use_container_width=True, help="Un esercizio in più"):
        evento = {"tipo": "ritocco", "campo": "esercizi", "delta": 1}
    ecc = par.get("eccellenza")
    ecc_v = True if ecc is None else bool(ecc)
    nuovo = c4.toggle("Eccellenza", value=ecc_v, key=f"ag_ecc_{ecc}", help="Un esercizio finale facoltativo e più difficile")
    if nuovo != ecc_v:
        evento = {"tipo": "ritocco", "campo": "eccellenza", "valore": nuovo}
    pun = par.get("punteggi")
    pun_v = True if pun is None else bool(pun)
    nuovo_p = st.toggle("Tabella dei punteggi in fondo", value=pun_v, key=f"ag_pun_{pun}")
    if nuovo_p != pun_v:
        evento = {"tipo": "ritocco", "campo": "punteggi", "valore": nuovo_p}
    return evento


def render_home(T: dict, chat: list, esempi: list, blocco: str | None, bloccate: list, allegati: list | None = None, js_microfono: str = "") -> dict | None:
    """Barra + conversazione della schermata iniziale. `blocco` = testo se non si può creare ora (limite mensile); `bloccate` = versioni non disponibili;
    `allegati` = nomi dei file allegati nella barra; `js_microfono` = script della dettatura (lo prepara main.py)."""
    evento = None
    with st.container(key="blk_agente"):
        st.markdown(_css(T), unsafe_allow_html=True)
        if not chat:
            st.markdown(f'<div class="ag-hero"><div class="ag-spark">{_SCINTILLA}</div><b>Cosa ti serve?</b>'
                        '<span class="ag-s">Scrivilo come lo diresti a un collega: argomento, classe, cosa vuoi in più.<br>'
                        'Puoi anche trascinare appunti o una verifica da sistemare. Se manca qualcosa te lo chiedo.</span></div>', unsafe_allow_html=True)
        for m in chat:
            if m.get("stage", "home") != "home":
                continue
            if m["ruolo"] == "utente":
                with st.chat_message("user"):
                    st.markdown(_esc(m["testo"]).replace("\n", "  \n"))
                    for f in m.get("allegati") or []:
                        st.caption(f"📎 {f}")
            elif m.get("testo"):
                with st.chat_message("assistant", avatar=":material/auto_awesome:"):
                    st.markdown(_esc(m["testo"]))

        ultimo = chat[-1] if chat and chat[-1]["ruolo"] == "agente" else None
        dec = (ultimo or {}).get("decisione") or {}
        az = dec.get("azione")
        if az == "domanda":
            st.markdown(f'<div class="ag-q">{_esc(dec.get("domanda"))}</div>', unsafe_allow_html=True)
            sc = opzioni_rapide(dec.get("opzioni") or [], "ag_opt")
            if sc:
                evento = {"tipo": "opzione", "testo": sc}
        elif az == "crea":
            st.markdown(card_riepilogo(T, dec), unsafe_allow_html=True)
            nb = [k for k in dec.get("versioni") or [] if k in bloccate]
            if nb:
                st.caption("Non posso ancora preparare: " + ", ".join(agente.VERSIONI.get(k, k) for k in nb) + " (funzioni complete da sbloccare).")
            if blocco:
                st.warning(blocco)
            rit = _ritocchi(dec)
            if rit:
                evento = rit
            c1, c2, c3 = st.columns([3, 2, 1.4], gap="small")
            if c1.button("Crea verifica", key="ag_crea", type="primary", icon=":material/auto_awesome:", use_container_width=True, disabled=bool(blocco)):
                evento = {"tipo": "conferma"}
            if c2.button("Modifica nel modulo", key="ag_modulo", type="secondary", icon=":material/tune:", use_container_width=True):
                evento = {"tipo": "modulo"}
            if c3.button("Annulla", key="ag_annulla", type="tertiary", use_container_width=True):
                evento = {"tipo": "annulla"}
        elif az == "impagina" and allegati:
            st.markdown(card_impagina(T, dec, allegati), unsafe_allow_html=True)
            if blocco:
                st.warning(blocco)
            c1, c2 = st.columns([3, 1.4], gap="small")
            if c1.button("Impagina", key="ag_impagina", type="primary", icon=":material/auto_fix_high:", use_container_width=True, disabled=bool(blocco)):
                evento = {"tipo": "impagina_conferma"}
            if c2.button("Annulla", key="ag_annulla_imp", type="tertiary", use_container_width=True):
                evento = {"tipo": "annulla"}
        elif az in ("impagina", "libro", "storico"):
            etichetta = {"impagina": "Impagina la mia verifica", "libro": "Apri il modulo e aggiungi la foto", "storico": "Apri «Le mie verifiche»"}[az]
            icona = {"impagina": ":material/upload_file:", "libro": ":material/photo_camera:", "storico": ":material/folder_open:"}[az]
            if st.button(etichetta, key="ag_vai", type="primary", icon=icona):
                evento = {"tipo": "vai", "dove": az}

        if not chat and esempi:
            with st.container(key="blk_ag_esempi"):
                cols = st.columns(len(esempi), gap="small")
                for i, (col, e) in enumerate(zip(cols, esempi)):
                    if col.button(e, key=f"ag_es_{i}", use_container_width=True, type="secondary", icon=_ESEMPI_ICONE[i % len(_ESEMPI_ICONE)]):
                        evento = {"tipo": "opzione", "testo": e}
        elif az == "crea":
            st.caption("Vuoi cambiare altro? Scrivilo qui sotto («meglio 6 esercizi», «aggiungi la fila B»…).")

        if js_microfono:
            with st.container(key="dettatura_ag"):
                components.html(js_microfono, height=0)
        invio = st.chat_input("Scrivi o detta cosa ti serve… (puoi allegare appunti o una verifica)", key="ag_in", accept_file="multiple",
                              file_type=["pdf", "png", "jpg", "jpeg", "webp", "docx"])
        if invio and evento is None:
            if isinstance(invio, str):
                testo, files = invio.strip(), []
            else:
                testo = (getattr(invio, "text", None) or (invio.get("text") if isinstance(invio, dict) else "") or "").strip()
                files = list(getattr(invio, "files", None) or (invio.get("files") if isinstance(invio, dict) else []) or [])
            if testo or files:
                evento = {"tipo": "testo", "testo": testo, "files": files}
    return evento
