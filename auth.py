import streamlit as st
import time


# ── NIENTE PIÙ COOKIE — usiamo i query params dell'URL ───────────────────────────
# Dopo il login l'URL diventa: https://tuaapp.streamlit.app/?rt=TOKEN
# Il token sopravvive al refresh perché è nell'URL stesso.
# Python lo legge direttamente — nessun iframe, nessun JS, funziona su tutti i browser.

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
            # Aggiorna il token nell'URL con quello rinnovato
            st.query_params["rt"] = res.session.refresh_token
    except Exception:
        # Token scaduto o invalido — rimuovi dall'URL
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
        background: #0C0C0B !important;
        font-family: 'DM Sans', sans-serif !important;
    }
    [data-testid="stHeader"], [data-testid="stDecoration"],
    [data-testid="stToolbar"], #MainMenu, footer { display: none !important; }
    .block-container {
        padding: 0 !important; max-width: 420px !important; margin: 0 auto !important;
    }
    [data-testid="stMainBlockContainer"] { padding: 0 !important; }

    /* Card visiva — gestita tramite stVerticalBlock (vedi sotto) */

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
        background: #0F0F0E !important; border-radius: 10px !important;
        padding: 4px !important; gap: 2px !important;
        border: 1px solid #2A2926 !important; margin-bottom: 1.2rem !important;
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
        background: linear-gradient(135deg,#0A84FF,#0A6ED4) !important;
        color: white !important;
        border: none !important; border-radius: 12px !important;
        font-weight: 700 !important; font-size: 1rem !important;
        min-height: 52px !important;
        box-shadow: 0 2px 24px rgba(10,132,255,0.35) !important;
        width: 100% !important; transition: filter .15s ease !important;
    }
    div.stButton > button[kind="primary"]:hover { filter: brightness(1.12) !important; }

    /* Card = stVerticalBlockBorderWrapper che contiene tabs + campi */
    [data-testid="stMainBlockContainer"] > div > [data-testid="stVerticalBlock"] {
        background: #111110;
        border-radius: 20px;
        border: 1px solid #1E1E1C;
        padding: 1.8rem 1.8rem 1.4rem 1.8rem !important;
        margin: 0 auto;
        max-width: 420px;
        box-shadow: 0 0 0 1px #1E1E1C, 0 20px 60px rgba(0,0,0,.5);
        /* gradient top border illusion */
        position: relative;
    }
    [data-testid="stMainBlockContainer"] > div > [data-testid="stVerticalBlock"]::before {
        content:''; position:absolute; top:0; left:0; right:0; height:2px;
        background:linear-gradient(90deg,#0A84FF,#10B981);
        border-radius:20px 20px 0 0;
    }
    </style>
    """, unsafe_allow_html=True)

    # Logo + tagline + badge features — dentro il card (stVerticalBlock)
    st.markdown("""
    <div style="text-align:center;padding:.6rem 0 1.4rem 0;">
      <div style="font-size:2.6rem;font-weight:900;letter-spacing:-0.04em;
                  color:#F5F4EF;line-height:1;margin-bottom:0.45rem;">
        Verific<span style="background:linear-gradient(135deg,#0A84FF,#10B981);
                            -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                            background-clip:text;">AI</span>
      </div>
      <p style="font-size:.9rem;color:#8C8A82;margin:0 0 .9rem 0;">
        Crea <strong style="color:#C8C6BC;">verifiche scolastiche professionali</strong> in secondi.
      </p>
      <div style="display:flex;justify-content:center;gap:.5rem;flex-wrap:wrap;">
        <span style="font-size:.72rem;color:#A8A6A0;background:#1A1916;
                     border:1px solid #2A2926;border-radius:20px;padding:.2rem .65rem;">
          ● Generazione AI
        </span>
        <span style="font-size:.72rem;color:#A8A6A0;background:#1A1916;
                     border:1px solid #2A2926;border-radius:20px;padding:.2rem .65rem;">
          ● Export PDF e Word
        </span>
        <span style="font-size:.72rem;color:#A8A6A0;background:#1A1916;
                     border:1px solid #2A2926;border-radius:20px;padding:.2rem .65rem;">
          ● BES / DSA incluso
        </span>
      </div>
    </div>
    """, unsafe_allow_html=True)

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

    st.markdown("""
    <div style="text-align:center;padding:.9rem 0 .2rem 0;">
      <p style="font-size:.72rem;color:#4A4840;margin:0;">
        Accedendo accetti i <a href="#" style="color:#6A6860;">termini di utilizzo</a>.
      </p>
      <p style="font-size:.68rem;color:#383630;margin:.3rem 0 0 0;">
        VerificAI · Beta · Per i docenti italiani
      </p>
    </div>
    """, unsafe_allow_html=True)
