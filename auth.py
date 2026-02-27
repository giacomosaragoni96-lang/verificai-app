import streamlit as st
import streamlit.components.v1 as components


# ── INJECT JS: salva token in localStorage ──────────────────────────────────────
def _inject_save_tokens(access_token: str, refresh_token: str):
    """Salva i token in localStorage via JS."""
    components.html(f"""
    <script>
      try {{
        localStorage.setItem('sb_at', '{access_token}');
        localStorage.setItem('sb_rt', '{refresh_token}');
      }} catch(e) {{}}
    </script>
    """, height=0)


# ── INJECT JS: cancella token da localStorage ───────────────────────────────────
def cancella_sessione_cookie():
    """Rimuove i token da localStorage."""
    components.html("""
    <script>
      try {
        localStorage.removeItem('sb_at');
        localStorage.removeItem('sb_rt');
      } catch(e) {}
    </script>
    """, height=0)
    st.session_state._token_check_done = False


# ── INJECT JS: legge token e manda a ?_at=...&_rt=... ───────────────────────────
def _inject_token_reader():
    """Legge i token da localStorage e redirige con query params se trovati."""
    components.html("""
    <script>
      (function() {
        // evita loop
        if (window.location.search.indexOf('_at=') !== -1) return;
        try {
          var at = localStorage.getItem('sb_at');
          var rt = localStorage.getItem('sb_rt');
          if (at && rt && at.length > 10 && rt.length > 10) {
            var url = window.location.pathname +
                      '?_at=' + encodeURIComponent(at) +
                      '&_rt=' + encodeURIComponent(rt);
            window.location.replace(url);
          }
        } catch(e) {}
      })();
    </script>
    """, height=0)


# ── FUNZIONE PRINCIPALE: ripristina sessione da localStorage ────────────────────
def ripristina_sessione(supabase):
    """Tenta di ripristinare la sessione dal localStorage tramite query params."""
    if st.session_state.get('utente') is not None:
        return
    if st.session_state.get('_token_check_done'):
        return

    # Caso 1: siamo arrivati qui con i query params (redirect da JS)
    at = st.query_params.get("_at", None)
    rt = st.query_params.get("_rt", None)

    if at and rt:
        # Pulisce i parametri e segna come fatto
        st.session_state._token_check_done = True
        try:
            sess = supabase.auth.set_session(at, rt)
            if sess and sess.user:
                st.session_state.utente = sess.user
                # Aggiorniamo i token per il prossimo giro
                _inject_save_tokens(sess.session.access_token, sess.session.refresh_token)
                # RIMUOVIAMO i parametri dall'URL per pulizia
                st.query_params.clear()
                st.rerun() # <--- AGGIUNGI QUESTO PER ENTRARE NELL'APP
        except Exception:
            cancella_sessione_cookie()
    else:
        # Caso 2: Nessun parametro. Inietta JS e ASPETTA un istante
        _inject_token_reader()
      

# ── SALVA SESSIONE DOPO LOGIN ────────────────────────────────────────────────────
def salva_sessione_cookie(res):
    """Salva i token in localStorage dopo il login."""
    _inject_save_tokens(res.session.access_token, res.session.refresh_token)


# ── FORM DI LOGIN/REGISTRAZIONE ─────────────────────────────────────────────────
def mostra_auth(supabase):
    import time

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
                    st.session_state.utente = res.user
                    st.session_state["_sb_access_token"] = res.session.access_token
                    st.session_state["_sb_refresh_token"] = res.session.refresh_token
                    salva_sessione_cookie(res)
                    st.rerun()
                except Exception as e:
                    err_str = str(e).lower()
                    if "invalid login" in err_str or "invalid credentials" in err_str:
                        st.warning("Password errata. Usa il tab 'Password' per reimpostarla.")
                    elif "email not confirmed" in err_str:
                        st.warning("Email non confermata. Controlla la casella di posta.")
                    else:
                        st.warning("Accesso non riuscito. Controlla email e password.")
                    time.sleep(2)

    with tab_reg:
        st.write("")
        email_r = st.text_input("Email", key="reg_email", placeholder="docente@scuola.it")
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
                        st.session_state["_sb_access_token"] = res.session.access_token
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
