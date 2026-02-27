import streamlit as st
import time
from streamlit_cookies_controller import CookieController


# ── COOKIE CONTROLLER ─────────────────────────────────────────────────────────────
def get_cookie_controller():
    if "_cookie_controller" not in st.session_state:
        st.session_state._cookie_controller = CookieController()
    return st.session_state._cookie_controller


# ── RIPRISTINO SESSIONE ───────────────────────────────────────────────────────────
def ripristina_sessione(supabase):
    """
    Logica a due passaggi per gestire il caricamento asincrono del JS:

    RENDER 1: il CookieController viene creato ma il JS non è ancora pronto.
              controller.get() restituisce None (falso negativo).
              Settiamo _cookie_controller_ready=True e usciamo SENZA marcare done.
              Il componente JS triggera automaticamente un rerun.

    RENDER 2: il JS è pronto, controller.get() restituisce il valore reale.
              Ora possiamo leggere il cookie e ripristinare la sessione.
              Solo qui settiamo _cookie_check_done=True.
    """
    # Utente già loggato — non fare nulla
    if st.session_state.get('utente') is not None:
        return

    # Check già completato — non ripetere
    if st.session_state.get('_cookie_check_done'):
        return

    controller = get_cookie_controller()

    # RENDER 1: prima volta che vediamo il controller — JS sta caricando
    # Non leggiamo ancora il cookie, aspettiamo il rerun automatico del componente
    if not st.session_state.get('_cookie_controller_ready'):
        st.session_state._cookie_controller_ready = True
        return  # <-- usciamo senza _cookie_check_done=True, il JS triggera rerun

    # RENDER 2+: JS pronto, leggiamo il cookie per davvero
    refresh_token = controller.get("sb_refresh_token")

    if refresh_token:
        try:
            res = supabase.auth.refresh_session(refresh_token)
            if res and res.user:
                st.session_state.utente = res.user
                st.session_state["_sb_access_token"]  = res.session.access_token
                st.session_state["_sb_refresh_token"] = res.session.refresh_token
                # Rinnova il cookie per altri 30 giorni
                controller.set("sb_refresh_token", res.session.refresh_token,
                               max_age=60 * 60 * 24 * 30)
        except Exception:
            # Token scaduto o invalido
            controller.remove("sb_refresh_token")
            st.session_state.utente = None

    # Marca come completato — non rileggere il cookie ai prossimi rerun
    st.session_state._cookie_check_done = True


def salva_sessione_cookie(res):
    """Salva il refresh token nel cookie dopo login/registrazione."""
    controller = get_cookie_controller()
    controller.set("sb_refresh_token", res.session.refresh_token,
                   max_age=60 * 60 * 24 * 30)


def cancella_sessione_cookie():
    """Cancella il cookie al logout e resetta i flag."""
    controller = get_cookie_controller()
    controller.remove("sb_refresh_token")
    st.session_state._cookie_check_done    = False
    st.session_state._cookie_controller_ready = False


# ── FORM LOGIN / REGISTRAZIONE ────────────────────────────────────────────────────
def mostra_auth(supabase):
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,wght@0,300;0,400;0,600;0,700;0,900;1,400&display=swap');
    html, body, [data-testid="stAppViewContainer"], .stApp {
        background: #0C0C0B !important;
        font-family: 'DM Sans', sans-serif !important;
    }
    [data-testid="stHeader"], [data-testid="stDecoration"],
    [data-testid="stToolbar"], #MainMenu, footer { display: none !important; }
    .block-container {
        padding: 0 !important; max-width: 480px !important; margin: 0 auto !important;
    }
    [data-testid="stMainBlockContainer"] { padding: 0 !important; }
    [data-testid="stTextInput"] input {
        background: #1A1916 !important; border: 1.5px solid #2A2926 !important;
        border-radius: 10px !important; color: #F5F4EF !important;
        font-family: 'DM Sans', sans-serif !important; font-size: 1rem !important;
        padding: 14px 16px !important; min-height: 50px !important;
    }
    [data-testid="stTextInput"] input:focus {
        border-color: #D97706 !important;
        box-shadow: 0 0 0 3px rgba(217,119,6,0.18) !important; outline: none !important;
    }
    [data-testid="stTextInput"] input::placeholder { color: #4A4840 !important; opacity: 1 !important; }
    [data-testid="stTextInput"] label p {
        color: #C8C6BC !important; font-size: 0.85rem !important;
        font-weight: 600 !important; font-family: 'DM Sans', sans-serif !important;
    }
    [data-testid="stTabs"] [data-baseweb="tab-list"] {
        background: #1A1916 !important; border-radius: 10px !important;
        padding: 4px !important; gap: 2px !important;
        border: 1px solid #2A2926 !important; margin-bottom: 1.5rem !important;
    }
    [data-testid="stTabs"] [data-baseweb="tab"] {
        border-radius: 7px !important; font-size: 0.85rem !important;
        font-weight: 600 !important; color: #6B6960 !important;
        padding: 0.45rem 1.2rem !important; background: transparent !important;
    }
    [data-testid="stTabs"] [aria-selected="true"] {
        background: #2A2926 !important; color: #F5F4EF !important;
    }
    [data-testid="stTabs"] [data-baseweb="tab-highlight"] { display: none !important; }
    div.stButton > button[kind="primary"] {
        background: #D97706 !important; color: white !important;
        border: none !important; border-radius: 10px !important;
        font-weight: 700 !important; font-size: 1rem !important;
        min-height: 52px !important;
        box-shadow: 0 2px 20px rgba(217,119,6,0.35) !important;
        width: 100% !important;
    }
    div.stButton > button[kind="primary"]:hover { filter: brightness(1.1) !important; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="padding:3rem 2rem 0 2rem;text-align:center;">
      <div style="font-size:3.2rem;font-weight:900;letter-spacing:-0.04em;
                  color:#F5F4EF;line-height:1;margin-bottom:0.5rem;">
        📝 Verific<span style="background:linear-gradient(135deg,#D97706,#FF8C00);
                               -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                               background-clip:text;">AI</span>
      </div>
      <p style="font-size:1rem;color:#8C8A82;margin:0 auto 2rem auto;max-width:360px;">
        Crea <strong style="color:#C8C6BC;">verifiche scolastiche professionali</strong> in 30 secondi.
      </p>
      <div style="background:#111110;border:1px solid #1E1D1A;border-radius:20px;
                  padding:1.8rem 2rem 0.5rem 2rem;text-align:left;margin-bottom:0.5rem;">
        <div style="font-size:1.3rem;font-weight:800;color:#F5F4EF;margin-bottom:0.3rem;">Inizia subito</div>
        <div style="font-size:0.85rem;color:#6B6960;margin-bottom:0;">
          Gratuito durante il periodo Beta · Nessuna carta richiesta
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    tab_login, tab_reg, tab_reset = st.tabs(["  Accedi  ", "  Registrati  ", "  Password  "])

    with tab_login:
        st.write("")
        email = st.text_input("Email", key="login_email", placeholder="docente@scuola.it")
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
                    st.session_state._cookie_check_done      = False
                    st.session_state._cookie_controller_ready = True  # JS già pronto
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
        email_r   = st.text_input("Email", key="reg_email", placeholder="docente@scuola.it")
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
                        st.session_state._cookie_check_done      = False
                        st.session_state._cookie_controller_ready = True
                        salva_sessione_cookie(res)
                    st.success("Benvenuto su VerificAI! Account creato.")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore durante la registrazione: {e}")

    with tab_reset:
        st.write("")
        st.markdown("""
        <div style="font-size:0.82rem;color:#8C8A82;padding:0.8rem 1rem;
                    background:#161614;border-radius:8px;border-left:2px solid #2A2926;margin-bottom:0.8rem;">
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
