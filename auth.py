import streamlit as st
import time


# ── NIENTE PIÙ COOKIE — usiamo i query params dell'URL ───────────────────────────
# Dopo il login l'URL diventa: https://tuaapp.streamlit.app/?rt=TOKEN
# Il token sopravvive al refresh perché è nell'URL stesso.

def get_cookie_controller():
    """Stub di compatibilità — non fa nulla, mantenuto per non rompere main.py."""
    return None


def ripristina_sessione(supabase):
    """
    Tenta di ripristinare la sessione dal query param ?rt=TOKEN.
    Se il token è valido, logga l'utente e ripulisce l'URL.
    """
    if st.session_state.get('utente') is not None:
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


# ── FORM LOGIN / REGISTRAZIONE — REDESIGN v2 ────────────────────────────────────
def mostra_auth(supabase):
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;0,800;0,900;1,400&display=swap');

    html, body, [data-testid="stAppViewContainer"], .stApp {
        background: #08080A !important;
        font-family: 'DM Sans', sans-serif !important;
        overflow-x: hidden;
    }

    /* ═══ Animated gradient background ═══ */
    [data-testid="stAppViewContainer"]::before {
        content: '';
        position: fixed; top: -200px; left: 50%;
        transform: translateX(-50%);
        width: 800px; height: 600px;
        background: radial-gradient(ellipse at center,
            rgba(217, 119, 6, .12) 0%,
            rgba(124, 58, 237, .06) 40%,
            transparent 70%);
        pointer-events: none; z-index: 0;
        animation: bgFloat 8s ease-in-out infinite;
    }
    [data-testid="stAppViewContainer"]::after {
        content: '';
        position: fixed; bottom: -150px; right: -100px;
        width: 500px; height: 400px;
        background: radial-gradient(ellipse at center,
            rgba(16, 185, 129, .08) 0%,
            transparent 60%);
        pointer-events: none; z-index: 0;
        animation: bgFloat2 10s ease-in-out infinite;
    }
    @keyframes bgFloat {
        0%, 100% { transform: translateX(-50%) translateY(0); }
        50% { transform: translateX(-50%) translateY(20px); }
    }
    @keyframes bgFloat2 {
        0%, 100% { transform: translateY(0) scale(1); }
        50% { transform: translateY(-15px) scale(1.05); }
    }

    [data-testid="stHeader"], [data-testid="stDecoration"],
    [data-testid="stToolbar"], #MainMenu, footer { display: none !important; }

    .block-container {
        padding: 0 !important; max-width: 460px !important; margin: 0 auto !important;
    }
    [data-testid="stMainBlockContainer"] { padding: 0 !important; }

    /* ═══ Glass-morphism Card ═══ */
    [data-testid="stMainBlockContainer"] > div > [data-testid="stVerticalBlock"] {
        background: rgba(18, 18, 20, .85);
        backdrop-filter: blur(24px);
        -webkit-backdrop-filter: blur(24px);
        border-radius: 24px;
        border: 1px solid rgba(255,255,255,.06);
        padding: 2.2rem 2.2rem 1.8rem 2.2rem !important;
        margin: 0 auto; max-width: 460px;
        box-shadow:
            0 0 0 1px rgba(255,255,255,.04),
            0 24px 80px rgba(0,0,0,.6),
            inset 0 1px 0 rgba(255,255,255,.04);
        position: relative;
        overflow: hidden;
    }
    /* ── Top accent bar — gradient ── */
    [data-testid="stMainBlockContainer"] > div > [data-testid="stVerticalBlock"]::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 3px;
        background: linear-gradient(90deg,
            #D97706 0%, #F59E0B 25%, #10B981 50%, #7C3AED 75%, #D97706 100%);
        background-size: 200% 100%;
        animation: gradientSlide 4s linear infinite;
        border-radius: 24px 24px 0 0;
    }
    @keyframes gradientSlide {
        0% { background-position: 0% 0; }
        100% { background-position: 200% 0; }
    }

    /* ═══ Form Inputs ═══ */
    [data-testid="stTextInput"] input {
        background: rgba(28, 28, 30, .8) !important;
        border: 1.5px solid rgba(255,255,255,.08) !important;
        border-radius: 12px !important;
        color: #F5F4EF !important;
        font-family: 'DM Sans', sans-serif !important;
        font-size: 1rem !important;
        padding: 14px 16px !important;
        min-height: 52px !important;
        transition: border-color .2s ease, box-shadow .2s ease !important;
    }
    [data-testid="stTextInput"] input:focus {
        border-color: #D97706 !important;
        box-shadow: 0 0 0 3px rgba(217,119,6,.18) !important;
        outline: none !important;
    }
    [data-testid="stTextInput"] input::placeholder {
        color: rgba(255,255,255,.2) !important;
        opacity: 1 !important;
    }
    [data-testid="stTextInput"] label p {
        color: rgba(200,198,188,.8) !important;
        font-size: 0.85rem !important;
        font-weight: 600 !important;
        font-family: 'DM Sans', sans-serif !important;
    }

    /* ═══ Tabs ═══ */
    [data-testid="stTabs"] [data-baseweb="tab-list"] {
        background: rgba(20, 20, 22, .6) !important;
        border-radius: 12px !important;
        padding: 4px !important;
        gap: 2px !important;
        border: 1px solid rgba(255,255,255,.06) !important;
        margin-bottom: 1.4rem !important;
    }
    [data-testid="stTabs"] [data-baseweb="tab"] {
        border-radius: 9px !important;
        font-size: 0.85rem !important;
        font-weight: 600 !important;
        color: rgba(255,255,255,.35) !important;
        padding: 0.5rem 1.2rem !important;
        background: transparent !important;
        transition: color .2s, background .2s !important;
    }
    [data-testid="stTabs"] [aria-selected="true"] {
        background: rgba(217,119,6,.15) !important;
        color: #F5F4EF !important;
    }
    [data-testid="stTabs"] [data-baseweb="tab-highlight"] { display: none !important; }

    /* ═══ Primary Button ═══ */
    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #C96B00, #D97706) !important;
        color: white !important;
        border: none !important;
        border-radius: 14px !important;
        font-weight: 800 !important;
        font-size: 1rem !important;
        min-height: 54px !important;
        box-shadow: 0 4px 28px rgba(201,107,0,.35) !important;
        width: 100% !important;
        transition: filter .15s ease, box-shadow .2s ease, transform .15s ease !important;
        letter-spacing: .01em !important;
    }
    div.stButton > button[kind="primary"]:hover {
        filter: brightness(1.10) !important;
        box-shadow: 0 6px 36px rgba(201,107,0,.50) !important;
        transform: translateY(-1px) !important;
    }
    div.stButton > button[kind="primary"]:active {
        transform: translateY(0) !important;
    }

    /* ═══ Stats row ═══ */
    .login-stats {
        display: flex; justify-content: center; gap: .5rem;
        margin: .5rem 0 1rem; flex-wrap: wrap;
    }
    .login-stat {
        background: rgba(26, 25, 22, .6);
        border: 1px solid rgba(255,255,255,.06);
        border-radius: 10px;
        padding: .3rem .7rem;
        font-size: .68rem;
        color: rgba(168,166,160,.8);
        font-family: 'DM Sans', sans-serif;
        display: flex; align-items: center; gap: .3rem;
        backdrop-filter: blur(4px);
    }
    .login-stat strong { color: #D97706; }

    /* ═══ Feature pills ═══ */
    .login-pills {
        display: flex; justify-content: center; gap: .35rem;
        flex-wrap: wrap; margin-top: .3rem;
    }
    .login-pill {
        font-size: .63rem; color: rgba(168,166,160,.6);
        background: rgba(26, 25, 22, .4);
        border: 1px solid rgba(255,255,255,.05);
        border-radius: 20px; padding: .15rem .55rem;
    }

    /* ═══ Trust indicators ═══ */
    .login-trust {
        display: flex; justify-content: center; gap: 1.2rem;
        margin-top: .8rem; padding-top: .8rem;
        border-top: 1px solid rgba(255,255,255,.05);
    }
    .login-trust-item {
        display: flex; align-items: center; gap: .3rem;
        font-size: .65rem; color: rgba(168,166,160,.5);
    }
    .login-trust-icon { font-size: .75rem; }

    /* ═══ Success / Warning overrides ═══ */
    [data-testid="stAlert"] {
        background: rgba(20,20,22,.8) !important;
        border-radius: 10px !important;
        border: 1px solid rgba(255,255,255,.08) !important;
        font-size: .85rem !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown("""
    <div style="text-align:center;padding:.3rem 0 1.2rem 0;">
      <div style="font-size:3rem;font-weight:900;letter-spacing:-0.04em;
                  color:#F5F4EF;line-height:1;margin-bottom:0.6rem;">
        Verific<span style="background:linear-gradient(135deg,#C96B00,#D97706);
                            -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                            background-clip:text;">AI</span>
      </div>
      <p style="font-size:.92rem;color:rgba(140,138,130,.9);margin:0 0 .5rem 0;line-height:1.5;">
        Crea <strong style="color:#C8C6BC;">verifiche scolastiche professionali</strong><br>
        in <strong style="color:#D97706;">30 secondi</strong> invece di 45 minuti.
      </p>
      <div class="login-stats">
        <div class="login-stat">⚡ <strong>30s</strong>&nbsp;media generazione</div>
        <div class="login-stat">📊 Rubrica MIM inclusa</div>
        <div class="login-stat">🌟 BES/DSA automatico</div>
      </div>
      <div class="login-pills">
        <span class="login-pill">✍️ Scrittura a mano</span>
        <span class="login-pill">📚 Template gallery</span>
        <span class="login-pill">⚡ One-Click Fila B</span>
        <span class="login-pill">📐 Grafici TikZ/pgfplots</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab_login, tab_reg, tab_reset = st.tabs(["  Accedi  ", "  Registrati  ", "  Password  "])

    with tab_login:
        st.write("")
        email    = st.text_input("Email", key="login_email", placeholder="docente@scuola.it")
        password = st.text_input("Password", type="password", key="login_pass", placeholder="••••••••")
        st.write("")
        if st.button("Accedi →", type="primary", use_container_width=True, key="btn_login"):
            if not email or not password:
                st.warning("Inserisci email e password.")
            else:
                try:
                    res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                    st.session_state.utente               = res.user
                    st.session_state["_sb_access_token"]  = res.session.access_token
                    st.session_state["_sb_refresh_token"] = res.session.refresh_token
                    salva_sessione_cookie(res)
                    st.rerun()
                except Exception as e:
                    err_str = str(e).lower()
                    if "invalid login" in err_str or "invalid credentials" in err_str:
                        st.warning("Password errata. Usa il tab 'Password' per reimpostarla.")
                    elif "email not confirmed" in err_str:
                        st.warning("Email non confermata. Controlla la casella di posta.")
                    elif "user not found" in err_str or "no user" in err_str:
                        st.warning("Nessun account trovato. Registrati prima.")
                    else:
                        st.warning("Accesso non riuscito. Controlla email e password.")
                    time.sleep(2)

    with tab_reg:
        st.write("")
        email_r    = st.text_input("Email", key="reg_email", placeholder="docente@scuola.it")
        password_r = st.text_input("Password (min. 6 caratteri)", type="password", key="reg_pass", placeholder="••••••••")
        st.write("")
        if st.button("Crea account gratuito →", type="primary", use_container_width=True, key="btn_reg"):
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
                    st.error(f"Errore durante la registrazione: {e}")

    with tab_reset:
        st.write("")
        st.markdown("""
        <div style="font-size:0.82rem;color:rgba(140,138,130,.7);padding:0.8rem 1rem;
                    background:rgba(22,22,20,.5);border-radius:10px;
                    border-left:2px solid rgba(217,119,6,.3);margin-bottom:0.8rem;">
          Inserisci la tua email. Riceverai un link per reimpostare la password.
        </div>
        """, unsafe_allow_html=True)
        email_reset = st.text_input("Email", key="reset_email", placeholder="docente@scuola.it")
        st.write("")
        if st.button("Invia link di reset →", type="primary", use_container_width=True, key="btn_reset"):
            if not email_reset:
                st.warning("Inserisci la tua email.")
            else:
                try:
                    supabase.auth.reset_password_email(email_reset)
                    st.success("Email inviata! Controlla la casella di posta.")
                except Exception as e:
                    st.error(f"Errore nell'invio: {e}")

    # ── Footer + Trust indicators ─────────────────────────────────────────────
    st.markdown("""
    <div class="login-trust">
      <div class="login-trust-item">
        <span class="login-trust-icon">🔒</span>
        <span>Dati protetti</span>
      </div>
      <div class="login-trust-item">
        <span class="login-trust-icon">🇮🇹</span>
        <span>Per docenti italiani</span>
      </div>
      <div class="login-trust-item">
        <span class="login-trust-icon">⚡</span>
        <span>Gratis per iniziare</span>
      </div>
    </div>
    <div style="text-align:center;padding:.8rem 0 .2rem 0;">
      <p style="font-size:.72rem;color:rgba(74,72,64,.7);margin:0;">
        Accedendo accetti i <a href="#" style="color:rgba(106,104,96,.8);">termini di utilizzo</a>.
      </p>
      <p style="font-size:.68rem;color:rgba(56,54,48,.6);margin:.3rem 0 0 0;">
        VerificAI · Beta · Per i docenti italiani
      </p>
    </div>
    """, unsafe_allow_html=True)
