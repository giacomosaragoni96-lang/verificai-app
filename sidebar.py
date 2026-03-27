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
        
        # Linea separatoria elegante
        st.markdown(
            f'<div style="height:2px;background:linear-gradient(90deg, {_acc}88, {_acc}33, transparent);'
            f'border-radius:2px;margin:1.5rem 0 2rem 0;"></div>',
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
            f'<div class="sidebar-label" style="margin-top:.5rem;font-size:0.85rem;font-weight:600;">Utilizzo mensile</div>',
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
            st.warning(f"Limite mensile raggiunto ({LIMITE_MENSILE} verifiche). {_reset_str}.")

        # ── CTA UPGRADE PRO ───────────────────────────────────────────────────
        if limite_raggiunto or _perc_uso >= 60:
            _rimaste = max(0, LIMITE_MENSILE - verifiche_mese_count)
            if limite_raggiunto:
                _msg = "Limite mensile raggiunto."
                _sub = "Passa a Pro per verifiche illimitate."
            else:
                _msg = f"Ti restano <b>{_rimaste} {'verifica' if _rimaste==1 else 'verifiche'}</b>."
                _sub = "Con Pro avresti accesso illimitato."
            st.markdown(f"""
            <div class="sb-pro-card">
              <div class="sb-pro-card-header">✦ VerificAI Pro</div>
              <div class="sb-pro-card-body">{_msg} {_sub}</div>
              <div class="sb-pro-card-footer">Verifiche illimitate · Fila B anti-copia · BES/DSA · Soluzioni docente</div>
            </div>
            """, unsafe_allow_html=True)

        # ── LINK STORICO VERIFICHE ─────────────────────────────────────────────
        st.markdown('<div class="sidebar-label" style="margin-top:.3rem;">Le mie verifiche</div>', unsafe_allow_html=True)
        
        # Stats cards semplici
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
            else:
                total_verifiche = 0
        except:
            total_verifiche = 0
        
        # Card con stats e link
        st.markdown(f'''
        <div class="sb-pro-card" style="
            background: linear-gradient({_acc}15, transparent);
            border: 1px solid {_acc}44;
            padding: 1rem;
            border-radius: 12px;
            margin-bottom: 1rem;
            cursor: pointer;
            transition: all 0.2s ease;
        " onclick="window.location.href='#?stage=MIE_VERIFICHE'">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.5rem;">
                <div style="font-size: 1.1rem; font-weight: 600; color: {_sb_text};">
                    📚 Gestisci Verifiche
                </div>
                <div style="background: {_acc}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.8rem; font-weight: 600;">
                    {total_verifiche}
                </div>
            </div>
            <div style="font-size: 0.85rem; color: {_sb_muted};">
                Visualizza, modifica e scarica tutte le tue verifiche
            </div>
        </div>
        ''', unsafe_allow_html=True)
        
        # Link diretto
        if st.button("📄 Apri Storico Completo", key="open_storico", use_container_width=True, type="secondary"):
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

        # ── PERFORMANCE MONITORING (Admin only) ─────────────────────────────
        if is_admin and hasattr(st.session_state, 'quality_stats'):
            st.markdown("---")
            st.markdown("### 📊 Qualità Generazione")
            
            stats = st.session_state.quality_stats
            total = sum(stats.values())
            
            if total > 0:
                # Quality metrics
                excellent_rate = stats.get('excellent', 0) / total * 100
                good_rate = stats.get('good', 0) / total * 100
                poor_rate = stats.get('poor', 0) / total * 100
                
                st.metric("📈 Tasso Successo", f"{excellent_rate + good_rate:.1f}%", 
                         f"+{excellent_rate:.1f}% eccellente")
                
                # Visual quality bar
                quality_data = [
                    ("👍 Ottima", stats.get('excellent', 0), "#059669"),
                    ("👍 Buona", stats.get('good', 0), "#22c55e"), 
                    ("😐 Sufficiente", stats.get('sufficient', 0), "#f59e0b"),
                    ("👎 Insufficiente", stats.get('poor', 0), "#ef4444")
                ]
                
                for label, count, color in quality_data:
                    if count > 0:
                        percentage = count / total * 100
                        st.markdown(f"""
                        <div style="display: flex; justify-content: space-between; align-items: center; margin: 0.2rem 0;">
                            <span style="font-size: 0.8rem;">{label}</span>
                            <span style="font-size: 0.8rem; font-weight: 600;">{count} ({percentage:.0f}%)</span>
                        </div>
                        <div style="background: #e5e7eb; border-radius: 4px; height: 6px; margin: 2px 0;">
                            <div style="background: {color}; width: {percentage}%; height: 100%; border-radius: 4px;"></div>
                        </div>
                        """, unsafe_allow_html=True)
                
                # Validation score tracking
                if hasattr(st.session_state, 'last_validation_score'):
                    last_score = st.session_state.last_validation_score
                    st.metric("🎯 Ultimo Score", f"{last_score:.2f}", 
                             "Buono" if last_score > 0.7 else "Da migliorare")
                
                # Reset stats button
                if st.button("🔄 Reset Statistiche", key="reset_stats", use_container_width=True):
                    st.session_state.quality_stats = {'excellent': 0, 'good': 0, 'sufficient': 0, 'poor': 0}
                    st.rerun()
            else:
                st.info("Nessun feedback raccolto ancora")

    return {
        "modello_id":    modello_id,
        "theme_changed": theme_changed,
    }
