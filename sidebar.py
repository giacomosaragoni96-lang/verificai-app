# ── sidebar.py — VerificAI ───────────────────────────────────────────────────
# Sidebar: Modello AI, Tema, Contatore mensile, Storico, Logout.
# ─────────────────────────────────────────────────────────────────────────────

import logging

import streamlit as st

logger = logging.getLogger("verificai.sidebar")


def render_sidebar(
    supabase_admin,
    utente,
    verifiche_mese_count,
    is_admin,
    limite_raggiunto,
    T,
    MODELLI_DISPONIBILI,
    LIMITE_MENSILE,
    giorni_al_reset_func,
    supabase_client,
    THEMES: dict = None,
    THEME_LABELS: dict = None,
) -> dict:

    theme_changed = False

    with st.sidebar:
        _acc = T.get("sidebar_accent", "#79C0FF")
        # La sidebar ha sempre sfondo scuro → i colori testo devono essere CHIARI
        # indipendentemente dal tema principale (chiaro/scuro).
        _sb_text  = T.get("sidebar_input_text", "#E6EDF3")
        _sb_muted = T.get("sidebar_muted", "#94A3B8")
        
        # Linea separatoria elegante
        st.markdown(
            f'<div style="height:2px;background:linear-gradient(90deg, {_acc}88, {_acc}33, transparent);'
            f'border-radius:2px;margin:1.5rem 0 2rem 0;"></div>',
            unsafe_allow_html=True
        )
        # ── MODELLO AI — scelto dal piano, non dall'utente ───────────────────
        # Free → Flash Lite · Pro → Flash 2.5 · Gold → Pro 2.5.
        # Solo l'admin può scegliere a mano (expander chiuso).
        # Il model_id effettivo viene poi validato in main.py con
        # get_model_id_per_piano(piano, materia) al momento della generazione.
        _piano = "admin" if is_admin else st.session_state.get("piano_utente", "free")

        if is_admin:
            with st.expander("🔧 Strumenti admin", expanded=False):
                _nomi_admin = list(MODELLI_DISPONIBILI.keys())
                _sel_modello = st.selectbox(
                    "Modello",
                    _nomi_admin,
                    key="sb_modello_admin",
                )
            modello_id = MODELLI_DISPONIBILI[_sel_modello]["id"]
        else:
            _piano_modello = _piano if _piano in ("pro", "gold") else "free"
            modello_id = next(
                v["id"] for v in MODELLI_DISPONIBILI.values()
                if v["piano"] == _piano_modello
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
            f'<div class="sidebar-label" style="margin-top:.5rem;font-size:0.85rem;font-weight:600;">Utilizzo mensile</div>',
            unsafe_allow_html=True
        )
        _perc_uso   = min(100, int(verifiche_mese_count / LIMITE_MENSILE * 100))
        _color_bar  = (T["error"] if limite_raggiunto
                       else (T["warn"] if _perc_uso >= 70 else T["success"]))

        _gg_reset, _hh_reset = giorni_al_reset_func()
        if _gg_reset == 0:
            _reset_str = f"Si rinnova tra {_hh_reset} ore"
        elif _gg_reset == 1:
            _reset_str = "Si rinnova domani"
        else:
            _reset_str = f"Si rinnova tra {_gg_reset} giorni"

        st.markdown(f"""
        <style>
        @media (max-width: 768px) {{
          .mobile-progress-container {{
            margin-bottom: 0.6rem !important;
            padding: 0.4rem !important;
          }}
          .mobile-progress-header {{
            font-size: 0.7rem !important;
            margin-bottom: 0.3rem !important;
          }}
          .mobile-progress-bar {{
            height: 3px !important;
            margin: 0.2rem 0 !important;
          }}
          .mobile-progress-text {{
            font-size: 0.6rem !important;
            margin-top: 0.3rem !important;
          }}
        }}
        </style>
        <div class="mobile-progress-container" style="margin-bottom: 0.6rem; background: rgba(255,255,255,0); border: none; padding: 0;">
          <div class="mobile-progress-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.6rem;">
            <span style="font-size: 0.85rem; font-weight:600; color: {_sb_text}; font-family: 'DM Sans', sans-serif;">
              Verifiche questo mese
            </span>
            <span style="font-size: 0.9rem; font-weight: 800; color: {_sb_text}; font-family: 'DM Sans', sans-serif;">
              {verifiche_mese_count} / {LIMITE_MENSILE}
            </span>
          </div>
          <div class="mobile-progress-bar" style="
            background: rgba(255,255,255,0) !important;
            border: none !important;
            border-radius: 10px;
            overflow: hidden;
            height: 4px;
            width: 100%;
            position: relative;
          ">
            <div style="
              width: {_perc_uso}%;
              background: {_color_bar};
              height: 100%;
              border-radius: 10px;
              transition: width .6s ease;
              position: absolute;
              top: 0;
              left: 0;
            "></div>
          </div>
          <div class="mobile-progress-text" style="text-align: right; font-size: 0.75rem; font-weight:500; color: {_sb_muted}; margin-top: 6px; font-family: 'DM Sans', sans-serif;">
            🔄 {_reset_str}
          </div>
        </div>
        """, unsafe_allow_html=True)

        if limite_raggiunto:
            _err_c = T.get("error", "#EF4444")
            st.markdown(
                f'<div style="background:{_err_c}18;border:1px solid {_err_c}44;'
                f'border-radius:10px;padding:.6rem .9rem;margin:.4rem 0;'
                f'font-size:.78rem;color:{_sb_text};font-family:DM Sans,sans-serif;'
                f'font-weight:600;line-height:1.5;">'
                f'⚠️ Limite mensile raggiunto ({LIMITE_MENSILE} verifiche). {_reset_str}.'
                f'</div>',
                unsafe_allow_html=True,
            )

        # ── LE MIE VERIFICHE — un solo pulsante con il conteggio ──────────────
        total_verifiche = None
        try:
            if utente is not None and supabase_admin is not None:
                storico_count = (
                    supabase_admin.table("verifiche_storico")
                    .select("id", count="exact")
                    .eq("user_id", utente.id)
                    .is_("deleted_at", "null")
                    .execute()
                )
                total_verifiche = storico_count.count if storico_count else 0
        except Exception as _e:
            logger.warning(f"Conteggio storico non disponibile: {_e}")

        _lbl_storico = (
            f"📚 Le mie verifiche ({total_verifiche})"
            if total_verifiche is not None else "📚 Le mie verifiche"
        )
        st.markdown('<div style="height:.9rem"></div>', unsafe_allow_html=True)
        if st.button(_lbl_storico, key="open_storico", use_container_width=True, type="secondary"):
            st.session_state.stage = "MIE_VERIFICHE"
            st.rerun()

        # ── USER + LOGOUT ─────────────────────────────────────────────────────
        if utente is not None:
            email_utente = utente.email or ""
            iniziale     = email_utente[0].upper() if email_utente else "?"
        else:
            email_utente = ""
            iniziale     = "?"

        _piano_label = {
            "admin": "Admin",
            "gold":  "Piano Gold",
            "pro":   "Piano Pro",
        }.get(_piano, "Piano gratuito")
        _piano_icon = {
            "admin": "⚙️",
            "gold":  "🌟",
            "pro":   "⚡",
        }.get(_piano, "🎓")
        st.markdown(f"""
        <div class="user-pill">
          <div class="user-avatar">{iniziale}</div>
          <div class="user-info">
            <div class="user-email">{email_utente}</div>
            <div class="user-role">{_piano_icon} {_piano_label}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="logout-btn-wrap">', unsafe_allow_html=True)
        if st.button("↩ Esci dall'account", key="logout_btn"):
            from auth import cancella_sessione_cookie
            cancella_sessione_cookie()
            supabase_client.auth.sign_out()
            st.session_state.utente          = None
            st.session_state.supabase       = None
            st.session_state.stage          = "INPUT"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    return {
        "modello_id":    modello_id,
        "theme_changed": theme_changed,
    }
