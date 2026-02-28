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


# ── FORM LOGIN / REGISTRAZIONE ────────────────────────────────────────────────────
def mostra_auth(supabase):
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,wght@0,300;0,400;0,600;0,700;0,900;1,400&display=swap');

    html, body, [data-testid="stAppViewContainer"], .stApp {
        background: #111110 !important;
        font-family: 'DM Sans', sans-serif !important;
    }
    [data-testid="stHeader"], [data-testid="stDecoration"],
    [data-testid="stToolbar"], #MainMenu, footer { display: none !important; }

    .block-container {
        padding: 0 !important;
        max-width: 460px !important;
        margin: 0 auto !important;
    }
    [data-testid="stMainBlockContainer"] { padding: 0 !important; }

    /* ── Card principale ── */
    .auth-card-wrap {
        background: #18181A;
        border: 1px solid #28282C;
        border-radius: 24px;
        padding: 2rem 2rem 1.8rem 2rem;
        margin: 1.5rem 1rem 0 1rem;
        box-shadow: 0 20px 60px rgba(0,0,0,.5), 0 4px 16px rgba(0,0,0,.3);
        position: relative;
        overflow: hidden;
    }
    .auth-card-wrap::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 2px;
        background: linear-gradient(90deg, #0A84FF 0%, #30D158 50%, #0A84FF 100%);
        opacity: .7;
    }

    /* ── Inputs ── */
    [data-testid="stTextInput"] input {
        background: #222226 !important;
        border: 1.5px solid #32323A !important;
        border-radius: 12px !important;
        color: #F2F2F7 !important;
        font-family: 'DM Sans', sans-serif !important;
        font-size: .95rem !important;
        padding: 14px 16px !important;
        min-height: 50px !important;
        transition: border-color .15s ease, box-shadow .15s ease !important;
    }
    [data-testid="stTextInput"] input:focus {
        border-color: #0A84FF !important;
        box-shadow: 0 0 0 3px rgba(10,132,255,0.18) !important;
        outline: none !important;
    }
    [data-testid="stTextInput"] input::placeholder {
        color: #48484E !important;
        opacity: 1 !important;
    }
    [data-testid="stTextInput"] label p {
        color: #8E8E93 !important;
        font-size: 0.78rem !important;
        font-weight: 700 !important;
        letter-spacing: .06em !important;
        text-transform: uppercase !important;
        font-family: 'DM Sans', sans-serif !important;
    }

    /* ── Tabs ── */
    [data-testid="stTabs"] [data-baseweb="tab-list"] {
        background: #0F0F11 !important;
        border-radius: 12px !important;
        padding: 4px !important;
        gap: 3px !important;
        border: 1px solid #28282C !important;
        margin-bottom: 1.4rem !important;
    }
    [data-testid="stTabs"] [data-baseweb="tab"] {
        border-radius: 9px !important;
        font-size: .82rem !important;
        font-weight: 700 !important;
        color: #636366 !important;
        padding: 0.5rem 1.1rem !important;
        background: transparent !important;
        font-family: 'DM Sans', sans-serif !important;
        letter-spacing: .02em !important;
        transition: background .15s, color .15s !important;
    }
    [data-testid="stTabs"] [aria-selected="true"] {
        background: #28282C !important;
        color: #F2F2F7 !important;
    }
    [data-testid="stTabs"] [data-baseweb="tab-highlight"] { display: none !important; }

    /* ── Primary button ── */
    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #0A84FF 0%, #0A6ED4 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        font-weight: 800 !important;
        font-size: .95rem !important;
        min-height: 52px !important;
        letter-spacing: .01em !important;
        box-shadow: 0 4px 20px rgba(10,132,255,0.35) !important;
        width: 100% !important;
        font-family: 'DM Sans', sans-serif !important;
        transition: filter .15s, transform .15s !important;
    }
    div.stButton > button[kind="primary"]:hover {
        filter: brightness(1.12) !important;
        transform: translateY(-1px) !important;
    }
    div.stButton > button[kind="primary"]:active {
        transform: scale(0.98) !important;
    }

    /* ── Alert / warning / success ── */
    [data-testid="stAlert"] {
        border-radius: 10px !important;
        font-family: 'DM Sans', sans-serif !important;
        font-size: .85rem !important;
    }

    /* ── Reset info box ── */
    .reset-info {
        font-size: 0.82rem;
        color: #8E8E93;
        padding: 0.8rem 1rem;
        background: #1C1C1E;
        border-radius: 10px;
        border-left: 2px solid #32323A;
        margin-bottom: 0.9rem;
        font-family: 'DM Sans', sans-serif;
        line-height: 1.5;
    }

    /* ── Features list under logo ── */
    .auth-features {
        display: flex;
        justify-content: center;
        gap: 1.2rem;
        margin: .4rem 0 0 0;
        flex-wrap: wrap;
    }
    .auth-feature-item {
        display: flex;
        align-items: center;
        gap: 5px;
        font-size: .72rem;
        color: #636366;
        font-family: 'DM Sans', sans-serif;
        font-weight: 500;
    }
    .auth-feature-dot {
        width: 5px; height: 5px;
        border-radius: 50%;
        background: #0A84FF;
        flex-shrink: 0;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Header / Logo ────────────────────────────────────────────────────────────
    st.markdown("""
    <div style="padding:3rem 1rem 0 1rem;text-align:center;">
      <div style="font-size:2.8rem;font-weight:900;letter-spacing:-0.04em;
                  color:#F2F2F7;line-height:1;margin-bottom:0.5rem;
                  font-family:'DM Sans',sans-serif;">
        Verific<span style="background:linear-gradient(135deg,#0A84FF 0%,#30D158 100%);
                             -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                             background-clip:text;">AI</span>
      </div>
      <p style="font-size:.88rem;color:#636366;margin:0 auto .6rem auto;
                font-family:'DM Sans',sans-serif;font-weight:400;">
        Crea <strong style="color:#AEAEB2;font-weight:600;">verifiche scolastiche professionali</strong> in secondi.
      </p>
      <div class="auth-features">
        <div class="auth-feature-item">
          <div class="auth-feature-dot"></div>
          Generazione AI
        </div>
        <div class="auth-feature-item">
          <div class="auth-feature-dot" style="background:#30D158;"></div>
          Export PDF e Word
        </div>
        <div class="auth-feature-item">
          <div class="auth-feature-dot" style="background:#FF9F0A;"></div>
          BES / DSA incluso
        </div>
      </div>
    </div>
    <div class="auth-card-wrap">
    """, unsafe_allow_html=True)

    tab_login, tab_reg, tab_reset = st.tabs(["Accedi", "Registrati", "Password"])

    with tab_login:
        st.write("")
        email    = st.text_input("Email", key="login_email", placeholder="docente@scuola.it")
        password = st.text_input("Password", type="password", key="login_pass", placeholder="••••••••")
        st.write("")
        if st.button("Accedi", type="primary", use_container_width=True, key="btn_login"):
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
        if st.button("Crea account gratuito", type="primary", use_container_width=True, key="btn_reg"):
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
        <div class="reset-info">
          Inserisci la tua email. Riceverai un link per reimpostare la password.
        </div>
        """, unsafe_allow_html=True)
        email_reset = st.text_input("Email", key="reset_email", placeholder="docente@scuola.it")
        st.write("")
        if st.button("Invia link di reset", type="primary", use_container_width=True, key="btn_reset"):
            if not email_reset:
                st.warning("Inserisci la tua email.")
            else:
                try:
                    supabase.auth.reset_password_email(email_reset)
                    st.success("Email inviata! Controlla la casella di posta.")
                except Exception as e:
                    st.error(f"Errore nell'invio: {e}")

    st.markdown("</div>", unsafe_allow_html=True)

    # Footer sotto il card
    st.markdown("""
    <div style="text-align:center;padding:.8rem 1rem 1.5rem;font-size:.72rem;
                color:#48484E;font-family:'DM Sans',sans-serif;line-height:1.6;">
      Accedendo accetti i termini di utilizzo.<br>
      <span style="opacity:.6;">VerificAI · Beta · Per i docenti italiani</span>
    </div>
    """, unsafe_allow_html=True)
