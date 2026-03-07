import streamlit as st
import time

# ── NIENTE PIÙ COOKIE — usiamo i query params dell'URL ───────────────────────
# Dopo il login l'URL diventa: https://tuaapp.streamlit.app/?rt=TOKEN
# Il token sopravvive al refresh perché è nell'URL stesso.

# ── Palette Notte — hardcoded per non importare config ───────────────────────
# (evita dipendenze circolari; questi valori devono rimanere in sync con config.py)
_N_BG       = "#0D1117"   # sfondo pagina
_N_CARD     = "#1C2128"   # card principale
_N_CARD2    = "#21262D"   # superficie secondaria
_N_BG2      = "#161B22"   # terzo livello
_N_TEXT     = "#E6EDF3"   # testo principale
_N_TEXT2    = "#8B949E"   # testo secondario
_N_MUTED    = "#6E7681"   # testo muted
_N_BORDER   = "#30363D"   # bordo
_N_BORDER2  = "#3D444D"   # bordo medio
_N_ACC      = "#58A6FF"   # accent primario (blu elettrico)
_N_ACC2     = "#79C0FF"   # accent secondario
_N_ACC_L    = "#0D2340"   # accent light (sfondo pill, dark)
_N_SB_DARK  = "#010409"   # sidebar/top bar ultra-dark


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


# ── FORM LOGIN / REGISTRAZIONE — Notte Design ────────────────────────────────
def mostra_auth(supabase):
    # ── CSS scoped alla pagina di login ──────────────────────────────────────
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;0,800;0,900;1,400&display=swap');

    /* ═══ Base page — Notte palette ═══ */
    html, body,
    [data-testid="stAppViewContainer"],
    .stApp {{
        background: {_N_BG} !important;
        font-family: 'DM Sans', sans-serif !important;
        overflow-x: hidden;
        color-scheme: dark !important;
    }}

    /* ── Ambient glow: pennellata blu in alto, scuro in basso ── */
    [data-testid="stAppViewContainer"]::before {{
        content: '';
        position: fixed; top: -140px; left: 50%;
        transform: translateX(-50%);
        width: 700px; height: 520px;
        background: radial-gradient(ellipse at center,
            rgba(88,166,255,.14)  0%,
            rgba(121,192,255,.06) 45%,
            transparent 70%);
        pointer-events: none; z-index: 0;
        animation: aGlow1 11s ease-in-out infinite;
    }}
    [data-testid="stAppViewContainer"]::after {{
        content: '';
        position: fixed; bottom: -100px; right: -80px;
        width: 400px; height: 320px;
        background: radial-gradient(ellipse at center,
            rgba(13,36,64,.18)  0%,
            transparent 65%);
        pointer-events: none; z-index: 0;
        animation: aGlow2 14s ease-in-out infinite;
    }}
    @keyframes aGlow1 {{
        0%,100% {{ transform: translateX(-50%) translateY(0px);   }}
        50%      {{ transform: translateX(-50%) translateY(18px);  }}
    }}
    @keyframes aGlow2 {{
        0%,100% {{ transform: translateY(0px)   scale(1);    }}
        50%      {{ transform: translateY(-13px) scale(1.04); }}
    }}

    /* ── Nascondi chrome Streamlit ── */
    [data-testid="stHeader"],
    [data-testid="stDecoration"],
    [data-testid="stToolbar"],
    #MainMenu, footer {{ display: none !important; }}

    /* ── Layout centrato ── */
    .block-container {{
        padding: 2rem 1rem !important;
        max-width: 480px !important;
        margin: 0 auto !important;
    }}
    [data-testid="stMainBlockContainer"] {{ padding: 0 !important; }}

    /* ═══ Card principale — Minimal SaaS: ombre morbide, bordi sottili ═══ */
    [data-testid="stMainBlockContainer"] > div > [data-testid="stVerticalBlock"] {{
        background: {_N_CARD};
        border-radius: 20px;
        border: 1px solid {_N_BORDER};
        margin: 0 auto;
        max-width: 480px;
        box-shadow:
            0 2px 8px  rgba(0,0,0,.06),
            0 8px 32px rgba(0,0,0,.12),
            0 0 0 1px  rgba(88,166,255,.06);
        position: relative;
        overflow: hidden;
        color-scheme: dark !important;
        transition: box-shadow .25s ease;
    }}

    /* ── Barra superiore animata — gradient blu ── */
    [data-testid="stMainBlockContainer"] > div > [data-testid="stVerticalBlock"]::before {{
        content: '';
        position: absolute; top: 0; left: 0; right: 0; height: 4px;
        background: linear-gradient(90deg,
            {_N_ACC}  0%,
            {_N_ACC2} 40%,
            {_N_SB_DARK} 65%,
            {_N_ACC2} 80%,
            {_N_ACC}  100%);
        background-size: 200% 100%;
        animation: topBarSlide 5s linear infinite;
        border-radius: 20px 20px 0 0;
    }}
    @keyframes topBarSlide {{
        0%   {{ background-position: 0% 0; }}
        100% {{ background-position: 200% 0; }}
    }}

    /* ── Padding interno della card ── */
    [data-testid="stMainBlockContainer"] > div > [data-testid="stVerticalBlock"] > div {{
        padding: 2.2rem 2.4rem 1.8rem !important;
    }}

    /* ═══ Inputs — design pulito, focus ring ═══ */
    [data-testid="stTextInput"] input {{
        background: {_N_BG2} !important;
        border: 1px solid {_N_BORDER} !important;
        border-radius: 12px !important;
        color: {_N_TEXT} !important;
        -webkit-text-fill-color: {_N_TEXT} !important;
        font-family: 'DM Sans', sans-serif !important;
        font-size: 1rem !important;
        padding: 14px 16px !important;
        min-height: 52px !important;
        transition: border-color .2s ease, box-shadow .2s ease, background .2s ease !important;
        color-scheme: dark !important;
    }}
    [data-testid="stTextInput"] input:focus {{
        border-color: {_N_ACC} !important;
        box-shadow: 0 0 0 3px rgba(88,166,255,.18) !important;
        background: {_N_CARD} !important;
        outline: none !important;
    }}
    [data-testid="stTextInput"] input::placeholder {{
        color: {_N_MUTED} !important; opacity: 1 !important;
    }}
    [data-testid="stTextInput"] label p {{
        color: {_N_TEXT2} !important;
        font-size: .82rem !important;
        font-weight: 600 !important;
        font-family: 'DM Sans', sans-serif !important;
    }}

    /* ═══ Tabs — pill selector blu ═══ */
    [data-testid="stTabs"] [data-baseweb="tab-list"] {{
        background: {_N_BG2} !important;
        border-radius: 12px !important;
        padding: 4px !important;
        gap: 2px !important;
        border: 1.5px solid {_N_BORDER} !important;
        margin-bottom: 1.4rem !important;
    }}
    [data-testid="stTabs"] [data-baseweb="tab"] {{
        border-radius: 9px !important;
        font-size: .85rem !important;
        font-weight: 600 !important;
        color: {_N_TEXT2} !important;
        -webkit-text-fill-color: {_N_TEXT2} !important;
        font-family: 'DM Sans', sans-serif !important;
        padding: .55rem 1.1rem !important;
        transition: background .18s, color .18s !important;
    }}
    [data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] {{
        background: {_N_CARD} !important;
        background-color: {_N_CARD} !important;
        color: {_N_ACC} !important;
        -webkit-text-fill-color: {_N_ACC} !important;
        font-weight: 700 !important;
        box-shadow: 0 1px 4px rgba(0,0,0,.30) !important;
    }}
    [data-testid="stTabs"] [role="tabpanel"] {{
        padding: 0 !important;
    }}

    /* ═══ Primary button — Minimal SaaS: ombra morbida, hover lift ═══ */
    div.stButton > button[kind="primary"],
    div.stButton > button[data-testid="stBaseButton-primary"] {{
        background: linear-gradient(135deg, {_N_ACC}, {_N_ACC2}) !important;
        color: #0D1117 !important;
        -webkit-text-fill-color: #0D1117 !important;
        border: none !important;
        border-radius: 12px !important;
        font-family: 'DM Sans', sans-serif !important;
        font-weight: 800 !important;
        font-size: 1rem !important;
        min-height: 52px !important;
        letter-spacing: -.02em !important;
        box-shadow: 0 4px 16px rgba(88,166,255,.22) !important;
        transition: filter .2s ease, box-shadow .2s ease, transform .2s ease !important;
    }}
    div.stButton > button[kind="primary"]:hover,
    div.stButton > button[data-testid="stBaseButton-primary"]:hover {{
        filter: brightness(1.08) !important;
        box-shadow: 0 8px 28px rgba(88,166,255,.32) !important;
        transform: translateY(-2px) !important;
    }}

    /* ═══ Warning / error messages — toast-like, bordi sottili ═══ */
    [data-testid="stAlert"] {{
        background: {_N_CARD2} !important;
        border: 1px solid {_N_BORDER} !important;
        border-radius: 12px !important;
        color: {_N_TEXT} !important;
        font-family: 'DM Sans', sans-serif !important;
        padding: 1rem 1.25rem !important;
        box-shadow: 0 2px 8px rgba(0,0,0,.08) !important;
    }}

    /* ═══ Stat row ═══ */
    .auth-stats {{
        display: flex; flex-wrap: wrap; justify-content: center;
        gap: .28rem; margin: .5rem 0 .4rem;
    }}
    .auth-stat-pill {{
        background: {_N_CARD2};
        border: 1.5px solid {_N_BORDER};
        border-radius: 20px;
        padding: .26rem .72rem;
        font-size: .69rem; font-weight: 600;
        color: {_N_TEXT2}; font-family: 'DM Sans', sans-serif;
        display: inline-flex; align-items: center; gap: .28rem;
    }}
    .auth-stat-num {{ color: {_N_ACC}; font-weight: 800; }}

    /* feature pills */
    .auth-feat-wrap {{
        display: flex; flex-wrap: wrap; gap: .28rem;
        justify-content: center; margin-top: .45rem;
    }}
    .auth-feat-pill {{
        font-size: .66rem; font-weight: 600;
        color: {_N_ACC2};
        background: {_N_ACC_L};
        border: 1px solid rgba(88,166,255,.25);
        border-radius: 20px; padding: .18rem .6rem;
        font-family: 'DM Sans', sans-serif;
    }}

    /* divisore orizzontale decorativo */
    .auth-hr {{
        height: 1.5px;
        background: linear-gradient(90deg,
            transparent, {_N_BORDER}, {_N_BORDER2}, {_N_BORDER}, transparent);
        margin: 0 0 1.3rem; border-radius: 2px;
    }}

    /* hint reset password */
    .auth-reset-hint {{
        font-size: .82rem; color: {_N_TEXT2};
        padding: .75rem 1rem;
        background: {_N_BG2};
        border-radius: 10px;
        border-left: 3px solid {_N_ACC};
        margin-bottom: .9rem;
        line-height: 1.5;
    }}

    /* trust bar in fondo */
    .auth-trust {{
        display: flex; justify-content: center; gap: 1.3rem;
        margin-top: .9rem; padding-top: .9rem;
        border-top: 1.5px solid {_N_BORDER};
    }}
    .auth-trust-item {{
        display: flex; align-items: center; gap: .28rem;
        font-size: .66rem; color: {_N_MUTED};
        font-family: 'DM Sans', sans-serif;
    }}
    </style>
    """, unsafe_allow_html=True)

    # ── Wordmark + headline ───────────────────────────────────────────────────
    st.markdown(f"""
    <div style="text-align:center; padding:.85rem 0 1.15rem;">

      <!-- Logo wordmark — titolo elegante, font grande e bilanciato -->
      <div style="
          font-family: 'DM Sans', sans-serif;
          font-size: clamp(2.6rem, 6vw, 3.4rem);
          font-weight: 900;
          letter-spacing: -0.04em;
          color: {_N_TEXT}; line-height: 1.1;
          margin-bottom: .55rem;">
        📝&thinsp;Verific<span style="
          background: linear-gradient(135deg,{_N_ACC},{_N_ACC2});
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;">AI</span>
      </div>

      <!-- Tagline -->
      <p style="font-size:.93rem; font-weight:500;
                color:{_N_TEXT2}; margin:0 0 .55rem;
                line-height:1.55; font-family:'DM Sans',sans-serif;">
        Crea&nbsp;<strong style="color:{_N_TEXT}; font-weight:800;">verifiche scolastiche professionali</strong><br>
        in&nbsp;<strong style="color:{_N_ACC}; font-weight:800;">30 secondi</strong>&nbsp;invece di 45 minuti.
      </p>

      <!-- Stat pills -->
      <div class="auth-stats">
        <div class="auth-stat-pill">⚡&nbsp;<span class="auth-stat-num">30s</span>&thinsp;media generazione</div>
        <div class="auth-stat-pill">📊&nbsp;Rubrica MIM inclusa</div>
        <div class="auth-stat-pill">🌟&nbsp;BES/DSA automatico</div>
      </div>

      <!-- Feature pills -->
      <div class="auth-feat-wrap">
        <span class="auth-feat-pill">✍️ Scrittura a mano</span>
        <span class="auth-feat-pill">📚 Template gallery</span>
        <span class="auth-feat-pill">⚡ Fila B one-click</span>
        <span class="auth-feat-pill">📐 Grafici TikZ</span>
        <span class="auth-feat-pill">✏️ DOCX modificabile</span>
      </div>

    </div>

    <!-- Divisore sottile -->
    <div class="auth-hr"></div>
    """, unsafe_allow_html=True)

    # ── Tabs ─────────────────────────────────────────────────────────────────
    tab_login, tab_reg, tab_reset = st.tabs(
        ["  Accedi  ", "  Registrati  ", "  Password  "]
    )

    with tab_login:
        st.write("")
        email    = st.text_input("Email",    key="login_email", placeholder="docente@scuola.it")
        password = st.text_input("Password", key="login_pass",  placeholder="••••••••",
                                 type="password")
        st.write("")
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
                        st.warning("Password errata. Usa il tab **Password** per reimpostarla.")
                    elif "email not confirmed" in err:
                        st.warning("Email non confermata. Controlla la casella di posta.")
                    elif "user not found" in err or "no user" in err:
                        st.warning("Nessun account trovato. Registrati prima.")
                    else:
                        st.warning("Accesso non riuscito. Controlla email e password.")
                    time.sleep(2)

    with tab_reg:
        st.write("")
        email_r    = st.text_input("Email", key="reg_email", placeholder="docente@scuola.it")
        password_r = st.text_input(
            "Password (min. 6 caratteri)", key="reg_pass",
            placeholder="••••••••", type="password",
        )
        st.write("")
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
                    st.error(f"Errore durante la registrazione: {e}")

    with tab_reset:
        st.write("")
        st.markdown(
            '<div class="auth-reset-hint">'
            "Inserisci la tua email. Riceverai un link per reimpostare la password."
            "</div>",
            unsafe_allow_html=True,
        )
        email_reset = st.text_input("Email", key="reset_email", placeholder="docente@scuola.it")
        st.write("")
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

    # ── Trust bar + footer ────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="auth-trust">
      <div class="auth-trust-item">🔒&ensp;Dati protetti</div>
      <div class="auth-trust-item">🇮🇹&ensp;Per docenti italiani</div>
      <div class="auth-trust-item">⚡&ensp;Gratis per iniziare</div>
    </div>
    <div style="text-align:center; padding:.78rem 0 .12rem; font-family:'DM Sans',sans-serif;">
      <p style="font-size:.7rem; color:{_N_MUTED}; margin:0;">
        Accedendo accetti i&nbsp;<a href="#"
          style="color:{_N_TEXT2}; font-weight:600; text-decoration:none;">termini di utilizzo</a>.
      </p>
      <p style="font-size:.64rem; color:{_N_BORDER2}; margin:.25rem 0 0;">
        VerificAI · Beta · Per i docenti italiani
      </p>
    </div>
    """, unsafe_allow_html=True)
