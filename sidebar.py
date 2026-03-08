# ── sidebar.py — VerificAI ───────────────────────────────────────────────────
# Sidebar: Modello AI, Tema, Contatore mensile, Storico, Logout.
# ─────────────────────────────────────────────────────────────────────────────

import streamlit as st
from datetime import datetime, timezone


def _tempo_fa(iso_str: str) -> str:
    """Converte un timestamp ISO in formato umano relativo (es. '2 ore fa', 'ieri')."""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        diff = now - dt
        seconds = int(diff.total_seconds())
        if seconds < 60:
            return "ora"
        minutes = seconds // 60
        if minutes < 60:
            return f"{minutes} min fa"
        hours = minutes // 60
        if hours < 24:
            return f"{hours} {'ora' if hours == 1 else 'ore'} fa"
        days = hours // 24
        if days == 1:
            return "ieri"
        if days < 7:
            return f"{days} giorni fa"
        weeks = days // 7
        if weeks < 4:
            return f"{weeks} sett. fa"
        months = days // 30
        if months < 12:
            return f"{months} {'mese' if months == 1 else 'mesi'} fa"
        return dt.strftime("%d/%m/%Y")
    except Exception:
        return iso_str[:10] if iso_str else ""


def render_sidebar(
    supabase_admin,
    utente,
    verifiche_mese_count,
    is_admin,
    limite_raggiunto,
    T,
    SCUOLE,
    MODELLI_DISPONIBILI,
    LIMITE_MENSILE,
    giorni_al_reset_func,
    compila_pdf_func,
    supabase_client,
    current_stage: str = "INPUT",
    THEMES: dict = None,
    THEME_LABELS: dict = None,
    extract_blocks_func=None,
    pdf_to_images_func=None,
) -> dict:

    STAGE_INPUT  = "INPUT"
    STAGE_REVIEW = "REVIEW"
    STAGE_FINAL  = "FINAL"

    theme_changed = False

    # Guard anti-doppio-rendering: Streamlit in alcuni casi può richiamare
    # il codice sidebar più volte nello stesso run (es. import circolare).
    # Questo lock garantisce una sola istanza per rerun.
    _sb_run_id = id(st.session_state)
    _sb_guard_key = f"_sb_rendered_{_sb_run_id}"

    with st.sidebar:
        _acc = T.get("sidebar_accent", "#79C0FF")
        _acc2 = T.get("accent2", _acc)
        # La sidebar ha sempre sfondo scuro → i colori testo devono essere CHIARI
        # indipendentemente dal tema principale (chiaro/scuro).
        _sb_text  = T.get("sidebar_input_text", "#E6EDF3")
        _sb_muted = T.get("sidebar_input_text", "#E6EDF3") + "99"
        st.markdown(
            f'<div class="sidebar-logo">📝 Verific<span style="background:linear-gradient(135deg,{_acc},{_acc2});'
            f'-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;">AI</span></div>',
            unsafe_allow_html=True
        )
        st.markdown(
            f'<div style="height:2px;background:linear-gradient(90deg,{_acc},transparent);'
            f'border-radius:2px;margin-bottom:1rem;opacity:.5;"></div>',
            unsafe_allow_html=True
        )
        # ── MODELLO AI — routing per piano ───────────────────────────────────
        # Admin  → sceglie manualmente qualsiasi modello
        # Free   → Flash Lite fisso (automatico)
        # Pro    → Flash, con upgrade a Pro se materia STEM (gold necessario)
        # Il model_id effettivo viene poi eventualmente aggiornato in main.py
        # tramite get_model_id_per_piano(piano, materia) al momento della generazione.
        st.markdown('<div class="sidebar-label">Qualità generazione</div>', unsafe_allow_html=True)

        # Determina piano corrente (admin sovrascrive tutto)
        _piano = "admin" if is_admin else st.session_state.get("piano_utente", "free")

        if is_admin:
            # Admin: selezione manuale completa
            _nomi_admin = list(MODELLI_DISPONIBILI.keys())
            _sel_modello = st.selectbox(
                "modello",
                _nomi_admin,
                label_visibility="collapsed",
                key="sb_modello_admin",
            )
            modello_id = MODELLI_DISPONIBILI[_sel_modello]["id"]
            st.markdown(
                f'<div style="font-size:0.72rem;color:{_sb_muted};padding:3px 0 0 2px;">'
                f'🔧 Admin: selezione manuale abilitata.</div>',
                unsafe_allow_html=True
            )
        elif _piano == "pro":
            # Pro: Flash come default, possibilità di scegliere tra Lite e Flash
            _nomi_pro = [
                k for k, v in MODELLI_DISPONIBILI.items()
                if v["piano"] in ("free", "pro")
            ]
            _sel_pro = st.selectbox(
                "modello", _nomi_pro, index=1,   # default Flash
                label_visibility="collapsed",
                key="sb_modello_pro",
            )
            modello_id = MODELLI_DISPONIBILI[_sel_pro]["id"]
            st.markdown(
                f'<div style="font-size:0.72rem;color:{_sb_muted};padding:3px 0 0 2px;">'
                f'⚡ Piano Pro attivo. Per materie scientifiche (matematica, fisica, chimica) considera il Piano Gold.</div>',
                unsafe_allow_html=True
            )
        elif _piano == "gold":
            # Gold: accesso completo incluso Pro 2.5
            _nomi_gold = list(MODELLI_DISPONIBILI.keys())
            _sel_gold = st.selectbox(
                "modello", _nomi_gold, index=2,  # default Pro 2.5
                label_visibility="collapsed",
                key="sb_modello_gold",
            )
            modello_id = MODELLI_DISPONIBILI[_sel_gold]["id"]
            st.markdown(
                f'<div style="font-size:0.72rem;color:{_sb_muted};padding:3px 0 0 2px;">'
                f'🌟 Piano Gold attivo · Gemini 2.5 Pro disponibile.</div>',
                unsafe_allow_html=True
            )
        else:
            # Free: Flash Lite fisso, non selezionabile
            _nome_lite = "⚡ Flash 2.5 Lite (veloce · Free)"
            modello_id = MODELLI_DISPONIBILI[_nome_lite]["id"]
            st.markdown(
                f'<div style="background:{T["hint_bg"]};border:1px solid {T["hint_border"]}; '
                f'border-radius:8px;padding:6px 10px;font-size:0.74rem;color:{T["hint_text"]}; '
                f'margin:4px 0;font-family:DM Sans,sans-serif;">'
                f'⚡ <b>Flash 2.5 Lite</b> — Piano Free<br/>'
                f'<span style="opacity:.8;">Passa al Piano Pro per Flash 2.5 (umanistiche) '
                f'o Gold per il motore avanzato (materie scientifiche).</span></div>',
                unsafe_allow_html=True
            )

        # ── TEMA ──────────────────────────────────────────────────────────────
        if THEMES and THEME_LABELS and len(THEMES) > 1:
            st.markdown(
                f'<div class="sidebar-label" style="margin-top:.9rem;">Tema</div>',
                unsafe_allow_html=True,
            )
            _theme_keys   = list(THEMES.keys())
            _theme_names  = [THEME_LABELS.get(k, k) for k in _theme_keys]
            _cur_theme    = st.session_state.get("theme", _theme_keys[0])
            _cur_idx      = _theme_keys.index(_cur_theme) if _cur_theme in _theme_keys else 0
            _sel_theme_name = st.selectbox(
                "tema",
                _theme_names,
                index=_cur_idx,
                label_visibility="collapsed",
                key="sb_tema_sel",
            )
            _sel_theme_key = _theme_keys[_theme_names.index(_sel_theme_name)]
            if _sel_theme_key != _cur_theme:
                st.session_state.theme = _sel_theme_key
                theme_changed = True

        # ── CONTATORE MENSILE ─────────────────────────────────────────────────
        st.markdown(
            f'<div class="sidebar-label" style="margin-top:1rem;">Utilizzo mensile</div>',
            unsafe_allow_html=True
        )
        _perc_uso   = min(100, int(verifiche_mese_count / LIMITE_MENSILE * 100))
        _color_bar  = (T["error"] if limite_raggiunto
                       else (T["warn"] if _perc_uso >= 70 else T["success"]))
        _count_class = ("limit-reached" if limite_raggiunto
                        else ("limit-near" if _perc_uso >= 70 else ""))

        _gg_reset, _hh_reset = giorni_al_reset_func()
        if _gg_reset == 0:
            _reset_str = f"Si rinnova tra {_hh_reset} ore"
        elif _gg_reset == 1:
            _reset_str = "Si rinnova domani"
        else:
            _reset_str = f"Si rinnova tra {_gg_reset} giorni"

        st.markdown(f"""
        <div class="monthly-bar">
          <div class="monthly-bar-header">
            <span class="monthly-bar-label">Verifiche questo mese</span>
            <span class="monthly-bar-count {_count_class}">
              {verifiche_mese_count} / {LIMITE_MENSILE}
            </span>
          </div>
          <div class="monthly-progress">
            <div class="monthly-progress-fill"
                 style="width:{_perc_uso}%;background:{_color_bar};"></div>
          </div>
          <div style="text-align:right;font-size:0.68rem;color:{_sb_muted};
                      margin-top:4px;font-family:'DM Sans',sans-serif;">
            🔄 {_reset_str}
          </div>
        </div>
        """, unsafe_allow_html=True)

        if limite_raggiunto:
            st.warning(f"Limite mensile raggiunto ({LIMITE_MENSILE} verifiche). {_reset_str}.")

        # ── CTA UPGRADE PRO ───────────────────────────────────────────────────
        if limite_raggiunto or _perc_uso >= 60:
            _rimaste = max(0, LIMITE_MENSILE - verifiche_mese_count)
            if limite_raggiunto:
                _msg = "Limite raggiunto."
                _sub = "Passa a Pro per verifiche illimitate."
            else:
                _msg = f"Ti restano {_rimaste} {'verifica' if _rimaste==1 else 'verifiche'}."
                _sub = "Con Pro avresti accesso illimitato."
            st.markdown(f"""
            <div style="background:{T['hint_bg']};border:1px solid {T['hint_border']};
                        border-radius:12px;padding:.65rem .9rem;margin:.5rem 0 .3rem 0;">
              <div style="font-size:.73rem;font-weight:700;color:{T['accent']};
                           font-family:'DM Sans',sans-serif;margin-bottom:2px;">
                ✦ VerificAI Pro
              </div>
              <div style="font-size:.7rem;color:{_sb_text};font-family:'DM Sans',sans-serif;
                          margin-bottom:.45rem;line-height:1.4;">
                {_msg} {_sub}
              </div>
              <div style="font-size:.68rem;color:{_sb_muted};font-family:'DM Sans',sans-serif;">
                Verifiche illimitate · Versione anti-copia (Fila B) · Adattata BES/DSA · Soluzioni per il docente
              </div>
            </div>
            """, unsafe_allow_html=True)

        # ── STORICO VERIFICHE ─────────────────────────────────────────────────
        st.markdown(
            f'<div class="sidebar-label" style="margin-top:1rem;">Le mie verifiche</div>',
            unsafe_allow_html=True
        )

        _refresh_key  = st.session_state._storico_refresh
        _page_size    = 5
        _storico_limit = st.session_state._storico_page * _page_size

        # ── Filtro ricerca storico ─────────────────────────────────────────
        _storico_search = st.text_input(
            "Cerca nelle verifiche",
            placeholder="🔍 Cerca per materia, argomento…",
            key="storico_search_input",
            label_visibility="collapsed",
        ).strip().lower()

        # Filtro materia — init session state
        if "_storico_filter_mat" not in st.session_state:
            st.session_state._storico_filter_mat = None

        try:
            storico = (
                supabase_admin.table("verifiche_storico")
                .select("id, materia, argomento, created_at, latex_a, latex_b, latex_r, scuola, num_esercizi, modello")
                .eq("user_id", utente.id)
                .is_("deleted_at", "null")
                .order("created_at", desc=True)
                .limit(_storico_limit + 1)
                .execute()
            )

            if storico.data:
                # ── Materia filter chips ──────────────────────────────────
                _all_materie = sorted(set(
                    v.get("materia", "") for v in storico.data if v.get("materia")
                ))
                if len(_all_materie) > 1:
                    _active_mat = st.session_state._storico_filter_mat

                    # Streamlit buttons per i filtri
                    _filter_cols = st.columns(min(len(_all_materie) + 1, 4))
                    with _filter_cols[0]:
                        if st.button("Tutte", key="filter_all",
                                     use_container_width=True,
                                     type="primary" if not _active_mat else "secondary"):
                            st.session_state._storico_filter_mat = None
                            st.rerun()
                    for _fi, _fm in enumerate(_all_materie[:3]):
                        with _filter_cols[min(_fi + 1, len(_filter_cols) - 1)]:
                            if st.button(_fm[:8], key=f"filter_{_fm}",
                                         use_container_width=True,
                                         type="primary" if _active_mat == _fm else "secondary"):
                                st.session_state._storico_filter_mat = _fm
                                st.rerun()

                # Applica filtri combinati (search + materia)
                _filtered = storico.data
                if st.session_state._storico_filter_mat:
                    _filtered = [
                        v for v in _filtered
                        if v.get("materia") == st.session_state._storico_filter_mat
                    ]
                if _storico_search:
                    _filtered = [
                        v for v in _filtered
                        if _storico_search in (
                            v.get("materia","") + " " +
                            v.get("argomento","") + " " +
                            v.get("scuola","")
                        ).lower()
                    ]

                _ha_altri      = len(storico.data) > _storico_limit and not _storico_search
                dati_pagina    = _filtered[:_storico_limit] if not _storico_search else _filtered
                _pref          = st.session_state._preferiti

                # Ordina: preferiti SEMPRE prima (stabili), poi per data decrescente
                dati_per_data    = sorted(dati_pagina, key=lambda x: x["created_at"], reverse=True)
                dati_ordinati    = sorted(dati_per_data, key=lambda x: 0 if x["id"] in _pref else 1)

                _n_show = len(dati_ordinati)
                _n_total = len(storico.data)

                with st.expander(
                    f"Storico ({_n_show}{' filtrate' if _storico_search or st.session_state._storico_filter_mat else ''} / {_n_total} verifiche)",
                    expanded=bool(_storico_search) or bool(st.session_state._storico_filter_mat),
                ):
                  if not dati_ordinati and (_storico_search or st.session_state._storico_filter_mat):
                      st.caption(f"Nessun risultato per il filtro selezionato.")
                  for v in dati_ordinati:
                    # ── Tempo relativo (es. "2 ore fa", "ieri") ───────────
                    _time_ago      = _tempo_fa(v["created_at"])
                    is_pref        = v["id"] in _pref
                    star_ico       = "★" if is_pref else "☆"
                    arg_trunc      = v["argomento"][:28] + ("…" if len(v["argomento"]) > 28 else "")
                    mat_str        = v['materia']
                    scu_str        = v.get('scuola', '')
                    n_es_str       = v.get('num_esercizi', '')
                    _has_b         = bool(v.get("latex_b"))
                    _has_r         = bool(v.get("latex_r"))

                    # ── Card visuale con tempo relativo ───────────────────
                    _badge_html = ""
                    if scu_str:
                        _badge_html += f'<span style="background:{T["bg2"]};color:{T["muted"]};font-size:.58rem;font-weight:600;padding:1px 5px;border-radius:4px;margin-right:3px;">{scu_str[:16]}</span>'
                    if _has_b:
                        _badge_html += f'<span style="background:{T["accent_light"]};color:{T["accent"]};font-size:.58rem;font-weight:700;padding:1px 5px;border-radius:4px;margin-right:3px;">FILA B</span>'
                    if _has_r:
                        _badge_html += f'<span style="background:{T["hint_bg"]};color:{T["hint_text"]};font-size:.58rem;font-weight:700;padding:1px 5px;border-radius:4px;">BES</span>'

                    st.markdown(
                        f'<div class="storico-card">'
                        f'  <div class="storico-card-top">'
                        f'    <span class="storico-card-mat">{mat_str}</span>'
                        f'    <span class="storico-card-date">{_time_ago}</span>'
                        f'  </div>'
                        f'  <div class="storico-card-arg">{arg_trunc}</div>'
                        + (f'  <div class="storico-card-meta">'
                           + (f'<span class="storico-card-nes">{n_es_str} esercizi</span>' if n_es_str else '')
                           + f'</div>' if n_es_str else '')
                        + f'  <div class="storico-card-badges">{_badge_html}</div>'
                        f'</div>',
                        unsafe_allow_html=True
                    )

                    # ── Azioni: stella + elimina ──────────────────────────────
                    _col_star, _col_del, _col_spacer = st.columns([1, 1, 2])
                    with _col_star:
                        st.markdown(
                            f'<div class="{"stella-btn-on" if is_pref else "stella-btn"}">',
                            unsafe_allow_html=True
                        )
                        if st.button(star_ico, key=f"star_{v['id']}_{_refresh_key}"):
                            if v["id"] in st.session_state._preferiti:
                                st.session_state._preferiti.discard(v["id"])
                            else:
                                st.session_state._preferiti.add(v["id"])
                            st.rerun()
                        st.markdown("</div>", unsafe_allow_html=True)

                    with _col_del:
                        st.markdown('<div class="elimina-btn">', unsafe_allow_html=True)
                        if st.button("🗑", key=f"del_{v['id']}_{_refresh_key}"):
                            try:
                                supabase_admin.table("verifiche_storico") \
                                    .update({"deleted_at": datetime.now(timezone.utc).isoformat()}) \
                                    .eq("id", v["id"]) \
                                    .execute()
                                st.session_state._preferiti.discard(v["id"])
                                st.session_state._storico_refresh += 1
                                st.toast("Verifica rimossa.")
                                st.rerun()
                            except Exception as del_err:
                                st.error(f"Errore: {del_err}")
                        st.markdown("</div>", unsafe_allow_html=True)

                    # ── Azioni principali: Apri + Riusa impostazioni ──────────
                    if v.get("latex_a"):
                        if st.button(
                            "📄 Apri verifica",
                            key=f"reload_a_{v['id']}_{_refresh_key}",
                            use_container_width=True
                        ):
                                latex_a = v["latex_a"]
                                # Reset completo dello stato verifiche per evitare
                                # residui di sessioni precedenti
                                st.session_state.verifiche = {
                                    "A":  {"latex": latex_a, "latex_originale": latex_a,
                                           "pdf": None, "preview": False,
                                           "docx": None, "pdf_ts": None, "docx_ts": None},
                                    "B":  {"latex": "", "pdf": None, "preview": False,
                                           "docx": None, "pdf_ts": None, "docx_ts": None, "latex_originale": ""},
                                    "R":  {"latex": "", "pdf": None, "preview": False,
                                           "docx": None, "pdf_ts": None, "docx_ts": None, "latex_originale": ""},
                                    "RB": {"latex": "", "pdf": None, "preview": False,
                                           "docx": None, "pdf_ts": None, "docx_ts": None, "latex_originale": ""},
                                    "S":  {"latex": None, "testo": None, "pdf": None},
                                }
                                # Compila PDF
                                pdf, _ = compila_pdf_func(latex_a)
                                if pdf:
                                    st.session_state.verifiche["A"]["pdf"]     = pdf
                                    st.session_state.verifiche["A"]["preview"] = True
                                # Preview immagini
                                if pdf and pdf_to_images_func:
                                    try:
                                        imgs, _ = pdf_to_images_func(pdf)
                                        st.session_state.preview_images = imgs or []
                                    except Exception:
                                        st.session_state.preview_images = []
                                else:
                                    st.session_state.preview_images = []
                                # Estrai blocchi con la funzione passata (evita import circolare)
                                if extract_blocks_func:
                                    try:
                                        pre, blks = extract_blocks_func(latex_a)
                                        st.session_state.review_preamble = pre
                                        st.session_state.review_blocks   = blks
                                        st.session_state.review_sel_idx  = 0
                                    except Exception:
                                        st.session_state.review_preamble = ""
                                        st.session_state.review_blocks   = []
                                # Popola gen_params dal record storico
                                st.session_state.gen_params = {
                                    "materia":         v.get("materia", ""),
                                    "difficolta":      v.get("scuola", ""),
                                    "argomento":       v.get("argomento", ""),
                                    "durata":          "1 ora",
                                    "num_esercizi":    v.get("num_esercizi", 4),
                                    "punti_totali":    100,
                                    "mostra_punteggi": True,
                                    "con_griglia":     True,
                                    "perc_ridotta":    25,
                                    "modello_id":      v.get("modello", "gemini-2.5-flash-lite"),
                                }
                                st.session_state.preview_page      = 0
                                st.session_state["_prev_stage"]    = None  # forza scroll top
                                st.session_state._saved_to_storico = True  # già in storico
                                st.session_state.stage = "FINAL"
                                st.rerun()

                        # ── IDEA #1: Riusa impostazioni (pre-fill form senza caricare verifica) ──
                        if st.button(
                            "🔄 Riusa impostazioni",
                            key=f"reuse_{v['id']}_{_refresh_key}",
                            use_container_width=True,
                            help="Pre-compila il form con materia, scuola e numero esercizi di questa verifica"
                        ):
                            st.session_state.gen_params = {
                                "materia":         v.get("materia", ""),
                                "difficolta":      v.get("scuola", ""),
                                "argomento":       "",   # Lascia vuoto — nuovo argomento
                                "num_esercizi":    v.get("num_esercizi", 4),
                                "mostra_punteggi": True,
                                "punti_totali":    100,
                                "con_griglia":     True,
                            }
                            st.session_state.input_percorso = "B"
                            st.session_state.stage = "INPUT"
                            st.session_state["_prev_stage"] = None
                            st.toast(f"✅ Impostazioni di «{v.get('argomento','')}» caricate!", icon="🔄")
                            st.rerun()

                        if v.get("latex_b"):
                            if st.button(
                                "Ricarica Fila B",
                                key=f"reload_b_{v['id']}_{_refresh_key}",
                                use_container_width=True
                            ):
                                st.session_state.verifiche["B"]["latex"] = v["latex_b"]
                                pdf, _ = compila_pdf_func(v["latex_b"])
                                if pdf:
                                    st.session_state.verifiche["B"]["pdf"]     = pdf
                                    st.session_state.verifiche["B"]["preview"] = True
                                st.rerun()

                  if _ha_altri:
                    if st.button("Carica altre", key="storico_load_more",
                                 use_container_width=True):
                        st.session_state._storico_page += 1
                        st.rerun()
                  elif st.session_state._storico_page > 1:
                    st.caption(f"Tutte le {len(dati_pagina)} verifiche caricate.")
            else:
                st.caption("Nessuna verifica salvata ancora.")

        except Exception:
            st.caption("Storico non disponibile.")

        # ── USER + LOGOUT ─────────────────────────────────────────────────────
        email_utente = utente.email or ""
        iniziale     = email_utente[0].upper() if email_utente else "?"

        _piano_label = {
            "admin": "Admin",
            "gold":  "Piano Gold",
            "pro":   "Piano Pro",
        }.get(_piano, "Piano gratuito")
        st.markdown(f"""
        <div class="user-pill">
          <div class="user-avatar">{iniziale}</div>
          <div class="user-info">
            <div class="user-email">{email_utente}</div>
            <div class="user-role">Docente · {_piano_label}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="logout-btn-wrap">', unsafe_allow_html=True)
        if st.button("↩ Esci dall'account", key="logout_btn"):
            from auth import cancella_sessione_cookie
            cancella_sessione_cookie()
            supabase_client.auth.sign_out()
            st.session_state.utente          = None
            st.session_state.stage           = "INPUT"
            st.session_state.pop("_sb_access_token",  None)
            st.session_state.pop("_sb_refresh_token", None)
            st.session_state._token_check_done = False
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    return {
        "modello_id":    modello_id,
        "theme_changed": theme_changed,
    }
