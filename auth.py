import streamlit as st
import streamlit.components.v1 as components
import time

# ── NIENTE PIÙ COOKIE — usiamo i query params dell'URL ───────────────────────
# Dopo il login l'URL diventa: https://tuaapp.streamlit.app/?rt=TOKEN
# Il token sopravvive al refresh perché è nell'URL stesso.

# Palette login: tema chiaro moderno
try:
    from config import THEMES
    # Usa tema chiaro per login
    T = THEMES.get("giorno", {})
except ImportError:
    T = {}

# Colori tema chiaro - alta leggibilità
_BG        = "#FFFFFF"
_CARD      = "#F8FAFC" 
_CARD2     = "#F1F5F9"
_BG2       = "#F8FAFC"
_TEXT      = "#1E293B"
_TEXT2     = "#475569"
_MUTED     = "#64748B"
_BORDER    = "#E2E8F0"
_BORDER2   = "#CBD5E1"
_ACCENT    = "#3B82F6"
_ACCENT2   = "#60A5FA"
_ACCENT_L  = "#EFF6FF"

# Colori moderni aggiuntivi
_PRIMARY    = _ACCENT
_PRIMARY_L  = _ACCENT2
_SUCCESS    = "#10B981"
_WARNING    = "#F59E0B"
_ERROR      = "#EF4444"
_SURFACE    = _CARD
_SURFACE_L  = _CARD2


def get_cookie_controller():
    """Stub di compatibilità — non fa nulla, mantenuto per non rompere main.py."""
    return None


def ripristina_sessione(supabase):
    """
    Tenta di ripristinare la sessione dal query param ?rt=TOKEN.
    Se il token è valido, logga l'utente e aggiorna il token.
    """
    if st.session_state.get("utente") is not None:
        return

    rt = st.query_params.get("rt", None)
    if not rt:
        return

    try:
        res = supabase.auth.refresh_session(rt)
        if res and res.user:
            st.session_state.utente = res.user
            st.session_state["_sb_access_token"]  = res.session.access_token
            st.session_state["_sb_refresh_token"] = res.session.refresh_token
            st.query_params["rt"] = res.session.refresh_token
    except Exception:
        st.query_params.pop("rt", None)
        st.session_state.utente = None


def salva_sessione_cookie(res):
    """Salva il refresh token nell'URL dopo login/registrazione."""
    st.query_params["rt"] = res.session.refresh_token


def cancella_sessione_cookie():
    """Rimuove il token dall'URL al logout."""
    st.query_params.pop("rt", None)


# ── FORM LOGIN / REGISTRAZIONE — Elegant dark (Notte-style) ──────────────────
def mostra_auth(supabase):
    # Rimuovi sticky header e progress bar (residui da sessione precedente)
    components.html("""
<script>
(function() {
  var doc = window.parent.document;
  var old = doc.getElementById('_vai_sticky_hdr');
  if (old) old.remove();
  var pb = doc.getElementById('_vai_progress_bar');
  if (pb) pb.remove();
  var main = doc.querySelector('.main .block-container');
  if (main) main.style.paddingTop = '';
})();
</script>""", height=0)

    # ── CSS Moderno Login Page ──────────────────────────────────────
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

    /* ═══ Base Modern Design System - Tema Chiaro ═══ */
    html, body,
    [data-testid="stAppViewContainer"],
    .stApp {{
        background: {_BG} !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        overflow-x: hidden;
        color-scheme: light !important;
        font-feature-settings: 'cv02', 'cv03', 'cv04', 'cv11';
    }}

    /* ── Modern Gradient Background ── */
    [data-testid="stAppViewContainer"]::before {{
        content: '';
        position: fixed; top: 0; left: 0; right: 0; bottom: 0;
        background: 
            radial-gradient(circle at 20% 20%, rgba({_PRIMARY.replace('#', '')},.08) 0%, transparent 50%),
            radial-gradient(circle at 80% 80%, rgba({_PRIMARY_L.replace('#', '')},.06) 0%, transparent 50%),
            radial-gradient(circle at 50% 50%, rgba({_SUCCESS.replace('#', '')},.03) 0%, transparent 70%);
        pointer-events: none; z-index: 0;
    }}

    /* ── Hide Streamlit Chrome ── */
    [data-testid="stHeader"], [data-testid="stDecoration"], [data-testid="stToolbar"],
    #MainMenu, footer {{ display: none !important; }}

    /* ── Modern Layout ── */
    .block-container {{
        padding: 2rem 1rem !important;
        max-width: 480px !important;
        margin: 0 auto !important;
        position: relative; z-index: 1;
    }}
    [data-testid="stMainBlockContainer"] {{ padding: 0 !important; }}

    /* ═══ Modern Glass Card ═══ */
    [data-testid="stMainBlockContainer"] > div > [data-testid="stVerticalBlock"] {{
        background: rgba({_SURFACE.replace('#', '')},.95) !important;
        backdrop-filter: blur(20px) saturate(180%);
        border: 1px solid rgba({_BORDER.replace('#', '')},.3) !important;
        border-radius: 24px !important;
        margin: 0 auto !important;
        max-width: 480px !important;
        box-shadow:
            0 0 0 1px rgba({_PRIMARY.replace('#', '')},.1),
            0 8px 32px rgba(0,0,0,.4),
            0 24px 64px rgba(0,0,0,.3),
            inset 0 1px 0 rgba(255,255,255,.05) !important;
        position: relative !important;
        overflow: hidden !important;
        transition: all .3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }}

    /* ── Modern Top Accent Bar ── */
    [data-testid="stMainBlockContainer"] > div > [data-testid="stVerticalBlock"]::before {{
        content: '';
        position: absolute; top: 0; left: 0; right: 0; height: 4px;
        background: linear-gradient(90deg, 
            {_PRIMARY} 0%, 
            {_PRIMARY_L} 50%, 
            {_PRIMARY} 100%);
        border-radius: 24px 24px 0 0;
        animation: shimmer 3s ease-in-out infinite;
    }}

    @keyframes shimmer {{
        0%, 100% {{ opacity: 1; }}
        50% {{ opacity: 0.8; }}
    }}

    /* ── Modern Card Padding ── */
    [data-testid="stMainBlockContainer"] > div > [data-testid="stVerticalBlock"] > div {{
        padding: 2.5rem 2.5rem 2rem !important;
    }}

    /* ═══ Modern Inputs ─══ */
    [data-testid="stTextInput"] input {{
        background: rgba({_BG2.replace('#', '')},.8) !important;
        border: 2px solid rgba({_BORDER.replace('#', '')},.2) !important;
        border-radius: 16px !important;
        color: {_TEXT} !important;
        -webkit-text-fill-color: {_TEXT} !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 1rem !important;
        font-weight: 500 !important;
        padding: 16px 20px !important;
        min-height: 56px !important;
        transition: all .25s cubic-bezier(0.4, 0, 0.2, 1) !important;
        color-scheme: light !important;
    }}
    [data-testid="stTextInput"] input:focus {{
        border-color: {_PRIMARY} !important;
        box-shadow: 
            0 0 0 4px rgba({_PRIMARY.replace('#', '')},.15),
            0 0 0 1px {_PRIMARY} !important;
        outline: none !important;
        transform: translateY(-1px) !important;
    }}
    [data-testid="stTextInput"] input::placeholder {{
        color: {_MUTED} !important; 
        opacity: 0.8 !important;
        font-weight: 400 !important;
    }}
    [data-testid="stTextInput"] label p {{
        color: {_TEXT2} !important;
        font-size: .875rem !important;
        font-weight: 600 !important;
        letter-spacing: .01em !important;
        font-family: 'Inter', sans-serif !important;
        margin-bottom: 0.5rem !important;
    }}

    /* ═══ Modern Tabs ─══ */
    [data-testid="stTabs"] [data-baseweb="tab-list"] {{
        background: rgba({_SURFACE_L.replace('#', '')},.6) !important;
        border-radius: 16px !important;
        padding: 6px !important;
        gap: 2px !important;
        border: 1px solid rgba({_BORDER.replace('#', '')},.2) !important;
        margin-bottom: 2rem !important;
        backdrop-filter: blur(10px);
    }}
    [data-testid="stTabs"] [data-baseweb="tab"] {{
        border-radius: 12px !important;
        font-size: .875rem !important;
        font-weight: 600 !important;
        color: {_TEXT2} !important;
        -webkit-text-fill-color: {_TEXT2} !important;
        font-family: 'Inter', sans-serif !important;
        padding: .75rem 1.25rem !important;
        transition: all .2s cubic-bezier(0.4, 0, 0.2, 1) !important;
        position: relative !important;
    }}
    [data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] {{
        background: rgba({_SURFACE.replace('#', '')},.9) !important;
        color: {_PRIMARY} !important;
        -webkit-text-fill-color: {_PRIMARY} !important;
        font-weight: 700 !important;
        box-shadow: 
            0 2px 8px rgba(0,0,0,.2),
            0 0 0 1px rgba({_PRIMARY.replace('#', '')},.2) !important;
    }}
    [data-testid="stTabs"] [role="tabpanel"] {{
        padding: 0 !important;
    }}

    /* ═══ Modern Primary Button ─══ */
    div.stButton > button[kind="primary"],
    div.stButton > button[data-testid="stBaseButton-primary"] {{
        background: linear-gradient(135deg, {_PRIMARY}, {_PRIMARY_L}) !important;
        color: white !important;
        -webkit-text-fill-color: white !important;
        border: none !important;
        border-radius: 16px !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
        min-height: 56px !important;
        letter-spacing: .01em !important;
        box-shadow: 
            0 4px 16px rgba({_PRIMARY.replace('#', '')},.3),
            0 0 0 1px rgba({_PRIMARY.replace('#', '')},.2) !important;
        transition: all .25s cubic-bezier(0.4, 0, 0.2, 1) !important;
        position: relative !important;
        overflow: hidden !important;
    }}
    div.stButton > button[kind="primary"]::before,
    div.stButton > button[data-testid="stBaseButton-primary"]::before {{
        content: '';
        position: absolute; top: 0; left: -100%; width: 100%; height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,.2), transparent);
        transition: left .6s ease;
    }}
    div.stButton > button[kind="primary"]:hover::before,
    div.stButton > button[data-testid="stBaseButton-primary"]:hover::before {{
        left: 100%;
    }}
    div.stButton > button[kind="primary"]:hover,
    div.stButton > button[data-testid="stBaseButton-primary"]:hover {{
        box-shadow: 
            0 8px 24px rgba({_PRIMARY.replace('#', '')},.4),
            0 0 0 1px rgba({_PRIMARY.replace('#', '')},.3) !important;
        transform: translateY(-2px) !important;
    }}

    /* ═══ Modern Messages ─══ */
    [data-testid="stAlert"] {{
        background: rgba({_SURFACE_L.replace('#', '')},.9) !important;
        border: 1px solid rgba({_BORDER.replace('#', '')},.3) !important;
        border-radius: 16px !important;
        color: {_TEXT} !important;
        font-family: 'Inter', sans-serif !important;
        padding: 1.25rem 1.5rem !important;
        box-shadow: 0 4px 16px rgba(0,0,0,.1) !important;
        backdrop-filter: blur(10px);
    }}

    /* ═══ Modern Typography ─══ */
    .auth-heading {{
        font-family: 'Inter', sans-serif;
        font-size: clamp(2rem, 5vw, 2.8rem);
        font-weight: 800;
        letter-spacing: -0.02em;
        color: {_TEXT};
        line-height: 1.1;
        margin-bottom: 0.75rem;
        text-align: center;
    }}
    .auth-subheading {{
        font-family: 'Inter', sans-serif;
        font-size: 1rem;
        font-weight: 500;
        color: {_TEXT2};
        line-height: 1.6;
        text-align: center;
        margin: 0;
    }}

    /* ═══ Modern Trust Bar ═══ */
    .auth-trust {{
        display: flex; justify-content: center; gap: 2rem;
        margin-top: 1.5rem; padding-top: 1.5rem;
        border-top: 1px solid rgba({_BORDER.replace('#', '')},.2);
        opacity: 0.9;
    }}
    .auth-trust-item {{
        display: flex; align-items: center; gap: 0.5rem;
        font-size: 0.8rem; color: {_MUTED};
        font-family: 'Inter', sans-serif;
        font-weight: 500;
        letter-spacing: 0.01em;
    }}

    /* ═══ Modern Divider ═══ */
    .auth-divider {{
        height: 1px;
        background: linear-gradient(90deg, 
            transparent, 
            rgba({_BORDER.replace('#', '')},.3), 
            transparent);
        margin: 2rem 0; border-radius: 1px;
    }}

    /* ═══ Modern Reset Hint ═══ */
    .auth-reset-hint {{
        font-size: 0.9rem; color: {_TEXT2};
        padding: 1rem 1.25rem;
        background: rgba({_BG2.replace('#', '')},.6);
        border-radius: 12px;
        border-left: 4px solid {_PRIMARY};
        margin-bottom: 1.5rem;
        line-height: 1.6;
        backdrop-filter: blur(10px);
    }}

    /* Responsive Design */
    @media (max-width: 480px) {{
        .block-container {{ padding: 1rem 0.5rem !important; }}
        [data-testid="stMainBlockContainer"] > div > [data-testid="stVerticalBlock"] > div {{
            padding: 2rem 1.5rem 1.5rem !important;
        }}
        .auth-trust {{
            flex-direction: column; gap: 1rem; align-items: center;
        }}
    }}
    </style>
    """, unsafe_allow_html=True)

    # ── Modern Header ───────────────────────────────────────────────────
    st.markdown(f"""
    <div style="text-align:center; padding:1rem 0 1.5rem;">

      <div class="auth-heading">
        📝&thinsp;Verific<span style="
          background: linear-gradient(135deg,{_PRIMARY},{_PRIMARY_L});
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;">AI</span>
      </div>

      <p class="auth-subheading">
        Verifiche scolastiche professionali in <strong style="color:{_PRIMARY}; font-weight:700;">30 secondi</strong>.
      </p>

    </div>

    <div class="auth-divider"></div>
    """, unsafe_allow_html=True)

    # ── Tabs ─────────────────────────────────────────────────────────────────
    tab_login, tab_reg, tab_reset = st.tabs(
        ["Accedi", "Registrati", "Password dimenticata?"]
    )

    with tab_login:
        email    = st.text_input("Email",    key="login_email", placeholder="docente@scuola.it")
        password = st.text_input("Password", key="login_pass",  placeholder="••••••••",
                                 type="password")
        if st.button("Accedi →", type="primary", use_container_width=True, key="btn_login"):
            if not email or not password:
                st.warning("Inserisci email e password.")
            else:
                try:
                    res = supabase.auth.sign_in_with_password(
                        {"email": email, "password": password}
                    )
                    st.session_state.utente               = res.user
                    st.session_state["_sb_access_token"]  = res.session.access_token
                    st.session_state["_sb_refresh_token"] = res.session.refresh_token
                    salva_sessione_cookie(res)
                    st.rerun()
                except Exception as e:
                    err = str(e).lower()
                    if "invalid login" in err or "invalid credentials" in err:
                        st.warning("Password errata. Clicca su **Password dimenticata?** qui sopra per reimpostarla.")
                    elif "email not confirmed" in err:
                        st.warning("Email non confermata. Controlla la casella di posta.")
                    elif "user not found" in err or "no user" in err:
                        st.warning("Nessun account trovato. Registrati prima.")
                    else:
                        st.warning("Accesso non riuscito. Controlla email e password.")
                    time.sleep(2)

    with tab_reg:
        email_r    = st.text_input("Email", key="reg_email", placeholder="docente@scuola.it")
        password_r = st.text_input(
            "Password (min. 6 caratteri)", key="reg_pass",
            placeholder="••••••••", type="password",
        )
        if st.button("Crea account gratuito →", type="primary",
                     use_container_width=True, key="btn_reg"):
            if not email_r or not password_r:
                st.warning("Inserisci email e password.")
            elif len(password_r) < 6:
                st.warning("La password deve essere di almeno 6 caratteri.")
            else:
                try:
                    res = supabase.auth.sign_up({"email": email_r, "password": password_r})
                    st.session_state.utente = res.user
                    if res.session:
                        st.session_state["_sb_access_token"]  = res.session.access_token
                        st.session_state["_sb_refresh_token"] = res.session.refresh_token
                        salva_sessione_cookie(res)
                    st.success("Benvenuto su VerificAI! Account creato.")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    _err_str = str(e).lower()
                    if "already registered" in _err_str or "already exists" in _err_str:
                        st.error("Questa email è già registrata. Prova ad accedere oppure clicca su **Password dimenticata?**.")
                    else:
                        st.error("Registrazione non riuscita. Controlla i dati inseriti e riprova, o contattaci se il problema persiste.")

    with tab_reset:
        st.markdown(
            '<div class="auth-reset-hint">'
            "Inserisci la tua email. Riceverai un link per reimpostare la password."
            "</div>",
            unsafe_allow_html=True,
        )
        email_reset = st.text_input("Email", key="reset_email", placeholder="docente@scuola.it")
        if st.button("Invia link di reset →", type="primary",
                     use_container_width=True, key="btn_reset"):
            if not email_reset:
                st.warning("Inserisci la tua email.")
            else:
                try:
                    supabase.auth.reset_password_email(email_reset)
                    st.success("Email inviata! Controlla la casella di posta.")
                except Exception as e:
                    st.error(f"Errore nell'invio: {e}")

    # ── Modern Trust Bar + Footer ────────────────────────────────────────────
    st.markdown(f"""
    <div class="auth-trust">
      <div class="auth-trust-item">🔒&ensp;Dati protetti</div>
      <div class="auth-trust-item">🇮🇹&ensp;Per docenti italiani</div>
      <div class="auth-trust-item">⚡&ensp;Gratis per iniziare</div>
    </div>
    <div style="text-align:center; padding:1rem 0 0.5rem; font-family:'Inter',sans-serif;">
      <p style="font-size:0.8rem; color:{_MUTED}; margin:0; font-weight:500;">
        Accedendo accetti i&nbsp;<a href="#"
          style="color:{_TEXT2}; font-weight:600; text-decoration:none; transition:color .2s;"
          onmouseover="this.style.color='{_PRIMARY}'" 
          onmouseout="this.style.color='{_TEXT2}'">termini di utilizzo</a>.
      </p>
    </div>
    """, unsafe_allow_html=True)
