import streamlit as st
import time
import extra_streamlit_components as stx



# ── COOKIE MANAGER ────────────────────────────────────────────────────────────────
@st.cache_resource
def get_cookie_manager():
    return stx.CookieManager()


# ── PERSISTENT LOGIN ──────────────────────────────────────────────────────────────
def ripristina_sessione(supabase):

    # Utente già in sessione, non fare nulla
    if st.session_state.get('utente') is not None:
        return

    # Inizializza il controller
    controller = get_cookie_controller()

    # Aspettiamo un rerun prima di tentare la lettura.
    if not st.session_state.get('_cookie_js_ready'):
        st.session_state['_cookie_js_ready'] = True
        st.rerun()   # ← secondo rerun: ora il JS ha avuto tempo di girare
    
    # Evitiamo di ritentare ad ogni rerun se il check è già stato fatto
    if st.session_state.get('_cookie_check_done'):
        return

    # Tenta di leggere il refresh token dal cookie
    refresh_token = controller.get("sb_refresh_token")

    if refresh_token:
        try:
            res = supabase.auth.refresh_session(refresh_token)
            if res and res.user:
                st.session_state.utente = res.user
                st.session_state["_sb_access_token"]  = res.session.access_token
                st.session_state["_sb_refresh_token"] = res.session.refresh_token
                # Aggiorna il cookie con il token rinnovato
                controller.set("sb_refresh_token", res.session.refresh_token,
                               max_age=60 * 60 * 24 * 30)
        except Exception:
            # Token scaduto o invalido — puliamo
            controller.remove("sb_refresh_token")
            st.session_state.utente = None

    # Segniamo che il check è stato fatto per evitare loop
    st.session_state._cookie_check_done = True


def salva_sessione_cookie(res):
    """Salva il refresh token nel cookie dopo login/registrazione."""
    controller = get_cookie_controller()
    controller.set("sb_refresh_token", res.session.refresh_token,
                   max_age=60 * 60 * 24 * 30)


def cancella_sessione_cookie():
    """Cancella il cookie al logout."""
    controller = get_cookie_controller()
    controller.remove("sb_refresh_token")
    # Resettiamo il flag così al prossimo login funziona tutto
    st.session_state._cookie_check_done = False
    st.session_state['_cookie_js_ready'] = False 


# ── AUTENTICAZIONE ────────────────────────────────────────────────────────────────
def mostra_auth(supabase):
    """
    Renderizza la schermata di login/registrazione/reset password.
    Da chiamare solo quando st.session_state.utente è None,
    seguito da st.stop() per bloccare il resto dell'app.
    """
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,wght@0,300;0,400;0,600;0,700;0,900;1,400&display=swap');

    html, body, [data-testid="stAppViewContainer"], .stApp {
        background: #0C0C0B !important;
        font-family: 'DM Sans', sans-serif !important;
    }
    [data-testid="stHeader"],
    [data-testid="stDecoration"],
    [data-testid="stToolbar"],
    #MainMenu, footer { display: none !important; }

    .block-container {
        padding: 0 !important;
        max-width: 420px !important;
        margin: 0 auto !important;
    }
    [data-testid="stMainBlockContainer"] { padding: 0 !important; }

    [data-testid="stTextInput"] input {
        background: #1A1916 !important;
        border: 1.5px solid #2A2926 !important;
        border-radius: 10px !important;
        color: #F5F4EF !important;
        font-family: 'DM Sans', sans-serif !important;
        font-size: 1rem !important;
        padding: 14px 16px !important;
        min-height: 50px !important;
    }
    [data-testid="stTextInput"] input:focus {
        border-color: #D97706 !important;
        box-shadow: 0 0 0 3px rgba(217,119,6,0.18) !important;
        outline: none !important;
    }
    [data-testid="stTextInput"] input::placeholder {
        color: #4A4840 !important;
        opacity: 1 !important;
    }
    [data-testid="stTextInput"] label p {
        color: #C8C6BC !important;
        font-size: 0.85rem !important;
        font-weight: 600 !important;
        font-family: 'DM Sans', sans-serif !important;
    }
    [data-testid="stTabs"] [data-baseweb="tab-list"] {
        background: #1A1916 !important;
        border-radius: 10px !important;
        padding: 4px !important;
        gap: 2px !important;
        border: 1px solid #2A2926 !important;
        margin-bottom: 1.5rem !important;
    }
    [data-testid="stTabs"] [data-baseweb="tab"] {
        border-radius: 7px !important;
        font-size: 0.85rem !important;
        font-weight: 600 !important;
        color: #6B6960 !important;
        padding: 0.45rem 1.2rem !important;
        background: transparent !important;
    }
    [data-testid="stTabs"] [aria-selected="true"] {
        background: #2A2926 !important;
        color: #F5F4EF !important;
    }
    [data-testid="stTabs"] [data-baseweb="tab-highlight"] { display: none !important; }
    div.stButton > button[kind="primary"] {
        background: #D97706 !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
        min-height: 52px !important;
        box-shadow: 0 2px 20px rgba(217,119,6,0.35) !important;
        width: 100% !important;
        transition: filter 0.15s, transform 0.15s !important;
    }
    div.stButton > button[kind="primary"]:hover {
        filter: brightness(1.1) !important;
        transform: translateY(-1px) !important;
    }
    .stAlert { border-radius: 8px !important; }
    .stAlert p, .stAlert div { font-size: 0.88rem !important; }
    </style>
    """, unsafe_allow_html=True)

    # ── HEADER ───────────────────────────────────────────────────────────────────
    st.markdown("""
    <div style="padding:2.2rem 2rem 0 2rem;text-align:center;">
      <div style="display:inline-flex;align-items:center;gap:7px;
                  background:rgba(217,119,6,0.12);border:1px solid rgba(217,119,6,0.3);
                  border-radius:100px;padding:5px 14px;margin-bottom:1.2rem;">
        <span style="width:6px;height:6px;border-radius:50%;background:#F59E0B;display:inline-block;"></span>
        <span style="font-size:0.72rem;font-weight:700;color:#F59E0B;letter-spacing:0.07em;text-transform:uppercase;">
          Generazione AI · Beta gratuita
        </span>
      </div>

      <div style="font-size:3rem;font-weight:900;letter-spacing:-0.04em;
                  color:#F5F4EF;line-height:1;margin-bottom:0.45rem;">
        📝 Verific<span style="background:linear-gradient(135deg,#D97706,#FF8C00);
                               -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                               background-clip:text;">AI</span>
      </div>

      <p style="font-size:0.95rem;color:#8C8A82;font-weight:400;
                margin:0 auto 1.4rem auto;line-height:1.5;max-width:320px;">
        Crea verifiche scolastiche professionali in pochi secondi.<br>
        <span style="color:#6B6960;font-size:0.82rem;">Materia, argomento, livello — il resto lo fa l'AI.</span>
      </p>

      <div style="display:flex;flex-wrap:wrap;gap:0.35rem;justify-content:center;margin-bottom:1.8rem;">
        <span style="background:#161614;border:1px solid #2A2926;border-radius:20px;padding:4px 11px;font-size:0.72rem;color:#C8C6BC;">🧠 AI</span>
        <span style="background:#161614;border:1px solid #2A2926;border-radius:20px;padding:4px 11px;font-size:0.72rem;color:#C8C6BC;">📄 PDF & Word</span>
        <span style="background:#161614;border:1px solid #2A2926;border-radius:20px;padding:4px 11px;font-size:0.72rem;color:#C8C6BC;">🔀 Fila A/B</span>
        <span style="background:#161614;border:1px solid #2A2926;border-radius:20px;padding:4px 11px;font-size:0.72rem;color:#C8C6BC;">🎯 BES/DSA</span>
        <span style="background:#161614;border:1px solid #2A2926;border-radius:20px;padding:4px 11px;font-size:0.72rem;color:#C8C6BC;">✅ Soluzioni</span>
      </div>

      <div style="background:#111110;border:1px solid #1E1D1A;border-radius:16px;
                  padding:1.4rem 1.6rem 0.4rem 1.6rem;text-align:left;">
    """, unsafe_allow_html=True)

    # ── FORM TABS ────────────────────────────────────────────────────────────────
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
                    st.session_state.utente = res.user
                    st.session_state["_sb_access_token"]  = res.session.access_token
                    st.session_state["_sb_refresh_token"] = res.session.refresh_token
                    st.session_state._cookie_check_done   = False  # reset per il prossimo refresh
                    salva_sessione_cookie(res)
                    st.rerun()
                except Exception as e:
                    err_str = str(e).lower()
                    if "invalid login" in err_str or "invalid credentials" in err_str:
                        st.warning("Password errata. Usa il tab 'Password' per reimpostarla.")
                    elif "email not confirmed" in err_str:
                        st.warning("Email non confermata. Controlla la tua casella di posta.")
                    elif "user not found" in err_str or "no user" in err_str:
                        st.warning("Nessun account trovato. Registrati prima.")
                    else:
                        st.warning("Accesso non riuscito. Controlla email e password.")
                    time.sleep(2)

    with tab_reg:
        st.write("")
        email    = st.text_input("Email", key="reg_email", placeholder="docente@scuola.it")
        password = st.text_input("Password (min. 6 caratteri)", type="password", key="reg_pass", placeholder="••••••••")
        st.write("")
        if st.button("Crea account gratuito →", type="primary", use_container_width=True, key="btn_reg"):
            if not email or not password:
                st.warning("Inserisci email e password.")
            elif len(password) < 6:
                st.warning("La password deve essere di almeno 6 caratteri.")
            else:
                try:
                    res = supabase.auth.sign_up({"email": email, "password": password})
                    st.session_state.utente = res.user
                    if res.session:
                        st.session_state["_sb_access_token"]  = res.session.access_token
                        st.session_state["_sb_refresh_token"] = res.session.refresh_token
                        st.session_state._cookie_check_done   = False
                        salva_sessione_cookie(res)
                    st.success("Benvenuto su VerificAI! Account creato.")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore durante la registrazione: {e}")

    with tab_reset:
        st.write("")
        st.markdown("""
        <div style="font-size:0.82rem;color:#8C8A82;line-height:1.5;
                    padding:0.8rem 1rem;background:#161614;border-radius:8px;
                    border-left:2px solid #2A2926;margin-bottom:0.8rem;">
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

    # ── CHIUDI BOX FORM ───────────────────────────────────────────────────────────
    st.markdown("</div>", unsafe_allow_html=True)

    # ── FOOTER ───────────────────────────────────────────────────────────────────
    st.markdown("""
    <div style="display:flex;align-items:center;gap:0.7rem;
                justify-content:center;padding:1.4rem 1rem 2.5rem 1rem;">
      <div style="display:flex;">
        <div style="width:24px;height:24px;border-radius:50%;border:2px solid #0C0C0B;
                    background:linear-gradient(135deg,#D97706,#92400E);
                    display:flex;align-items:center;justify-content:center;
                    font-size:0.55rem;font-weight:700;color:white;">GM</div>
        <div style="width:24px;height:24px;border-radius:50%;border:2px solid #0C0C0B;
                    background:linear-gradient(135deg,#D97706,#92400E);
                    display:flex;align-items:center;justify-content:center;
                    font-size:0.55rem;font-weight:700;color:white;margin-left:-6px;">AR</div>
        <div style="width:24px;height:24px;border-radius:50%;border:2px solid #0C0C0B;
                    background:linear-gradient(135deg,#444,#222);
                    display:flex;align-items:center;justify-content:center;
                    font-size:0.55rem;font-weight:700;color:white;margin-left:-6px;">+</div>
      </div>
      <div style="font-size:0.75rem;color:#6B6960;line-height:1.4;">
        Usato da docenti di tutta Italia ·
        <strong style="color:#8C8A82;">Gratis in Beta</strong>
      </div>
    </div>
    </div>
    """, unsafe_allow_html=True)
