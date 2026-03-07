import streamlit as st
import streamlit.components.v1 as components
import time

# ── NIENTE PIÙ COOKIE — usiamo i query params dell'URL ───────────────────────
# Dopo il login l'URL diventa: https://tuaapp.streamlit.app/?rt=TOKEN
# Il token sopravvive al refresh perché è nell'URL stesso.

# Palette login: tema Notte da config (singola fonte di verità)
try:
    from config import THEMES
    _N = THEMES.get("notte", {})
except ImportError:
    _N = {}
_N_BG       = _N.get("bg", "#0D1117")
_N_CARD     = _N.get("card", "#1C2128")
_N_CARD2    = _N.get("card2", "#21262D")
_N_BG2      = _N.get("bg2", "#161B22")
_N_TEXT     = _N.get("text", "#E6EDF3")
_N_TEXT2    = _N.get("text2", "#8B949E")
_N_MUTED    = _N.get("muted", "#6E7681")
_N_BORDER   = _N.get("border", "#30363D")
_N_BORDER2  = _N.get("border2", "#3D444D")
_N_ACC      = _N.get("accent", "#58A6FF")
_N_ACC2     = _N.get("accent2", "#79C0FF")
_N_ACC_L    = _N.get("accent_light", "#0D2340")


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

    # ── CSS scoped alla pagina di login ──────────────────────────────────────
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;0,800;0,900;1,400&display=swap');

    /* ═══ Base page — Notte palette, elegant ═══ */
    html, body,
    [data-testid="stAppViewContainer"],
    .stApp {{
        background: {_N_BG} !important;
        font-family: 'DM Sans', sans-serif !important;
        overflow-x: hidden;
        color-scheme: dark !important;
    }}

    /* ── Ambient: soft mesh glow (sottile, elegante) ── */
    [data-testid="stAppViewContainer"]::before {{
        content: '';
        position: fixed; top: -200px; left: 50%;
        transform: translateX(-50%);
        width: 900px; height: 500px;
        background: radial-gradient(ellipse 80% 50% at 50% 0%,
            rgba(88,166,255,.08)  0%,
            rgba(121,192,255,.03) 40%,
            transparent 70%);
        pointer-events: none; z-index: 0;
    }}
    [data-testid="stAppViewContainer"]::after {{
        content: '';
        position: fixed; bottom: -120px; right: -60px;
        width: 380px; height: 380px;
        background: radial-gradient(circle,
            rgba(13,36,64,.12)  0%,
            transparent 60%);
        pointer-events: none; z-index: 0;
    }}

    /* ── Nascondi chrome Streamlit ── */
    [data-testid="stHeader"],
    [data-testid="stDecoration"],
    [data-testid="stToolbar"],
    #MainMenu, footer {{ display: none !important; }}

    /* ── Layout centrato ── */
    .block-container {{
        padding: 2.5rem 1.25rem !important;
        max-width: 440px !important;
        margin: 0 auto !important;
    }}
    [data-testid="stMainBlockContainer"] {{ padding: 0 !important; }}

    /* ═══ Card principale — Elegant: bordo sottile, ombra profonda ═══ */
    [data-testid="stMainBlockContainer"] > div > [data-testid="stVerticalBlock"] {{
        background: {_N_CARD};
        border-radius: 24px;
        border: 1px solid {_N_BORDER};
        margin: 0 auto;
        max-width: 440px;
        box-shadow:
            0 0 0 1px rgba(88,166,255,.04),
            0 4px 24px rgba(0,0,0,.2),
            0 24px 48px rgba(0,0,0,.15);
        position: relative;
        overflow: hidden;
        color-scheme: dark !important;
        transition: box-shadow .3s ease, border-color .3s ease;
    }}

    /* ── Barra superiore — linea accent sottile (non animata, più elegante) ── */
    [data-testid="stMainBlockContainer"] > div > [data-testid="stVerticalBlock"]::before {{
        content: '';
        position: absolute; top: 0; left: 0; right: 0; height: 3px;
        background: linear-gradient(90deg, {_N_ACC}, {_N_ACC2});
        border-radius: 24px 24px 0 0;
    }}

    /* ── Padding interno della card ── */
    [data-testid="stMainBlockContainer"] > div > [data-testid="stVerticalBlock"] > div {{
        padding: 2rem 2.2rem 1.75rem !important;
    }}

    /* ═══ Inputs — elegant, focus ring ═══ */
    [data-testid="stTextInput"] input {{
        background: {_N_BG2} !important;
        border: 1px solid {_N_BORDER} !important;
        border-radius: 14px !important;
        color: {_N_TEXT} !important;
        -webkit-text-fill-color: {_N_TEXT} !important;
        font-family: 'DM Sans', sans-serif !important;
        font-size: 1rem !important;
        padding: 14px 18px !important;
        min-height: 50px !important;
        transition: border-color .25s ease, box-shadow .25s ease !important;
        color-scheme: dark !important;
    }}
    [data-testid="stTextInput"] input:focus {{
        border-color: {_N_ACC} !important;
        box-shadow: 0 0 0 3px rgba(88,166,255,.15) !important;
        outline: none !important;
    }}
    [data-testid="stTextInput"] input::placeholder {{
        color: {_N_MUTED} !important; opacity: 1 !important;
    }}
    [data-testid="stTextInput"] label p {{
        color: {_N_TEXT2} !important;
        font-size: .8rem !important;
        font-weight: 600 !important;
        letter-spacing: .02em !important;
        font-family: 'DM Sans', sans-serif !important;
    }}

    /* ═══ Tabs — pill selector, clean ═══ */
    [data-testid="stTabs"] [data-baseweb="tab-list"] {{
        background: {_N_BG2} !important;
        border-radius: 14px !important;
        padding: 5px !important;
        gap: 4px !important;
        border: 1px solid {_N_BORDER} !important;
        margin-bottom: 1.5rem !important;
    }}
    [data-testid="stTabs"] [data-baseweb="tab"] {{
        border-radius: 10px !important;
        font-size: .84rem !important;
        font-weight: 600 !important;
        color: {_N_TEXT2} !important;
        -webkit-text-fill-color: {_N_TEXT2} !important;
        font-family: 'DM Sans', sans-serif !important;
        padding: .5rem 1rem !important;
        transition: background .2s, color .2s !important;
    }}
    [data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] {{
        background: {_N_CARD} !important;
        background-color: {_N_CARD} !important;
        color: {_N_ACC} !important;
        -webkit-text-fill-color: {_N_ACC} !important;
        font-weight: 700 !important;
        box-shadow: 0 1px 3px rgba(0,0,0,.25) !important;
    }}
    [data-testid="stTabs"] [role="tabpanel"] {{
        padding: 0 !important;
    }}

    /* ═══ Primary button — elegant, subtle lift ═══ */
    div.stButton > button[kind="primary"],
    div.stButton > button[data-testid="stBaseButton-primary"] {{
        background: linear-gradient(135deg, {_N_ACC}, {_N_ACC2}) !important;
        color: #0D1117 !important;
        -webkit-text-fill-color: #0D1117 !important;
        border: none !important;
        border-radius: 14px !important;
        font-family: 'DM Sans', sans-serif !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
        min-height: 50px !important;
        letter-spacing: .01em !important;
        box-shadow: 0 2px 12px rgba(88,166,255,.2) !important;
        transition: box-shadow .25s ease, transform .25s ease !important;
    }}
    div.stButton > button[kind="primary"]:hover,
    div.stButton > button[data-testid="stBaseButton-primary"]:hover {{
        box-shadow: 0 6px 24px rgba(88,166,255,.28) !important;
        transform: translateY(-1px) !important;
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

    /* divisore orizzontale */
    .auth-hr {{
        height: 1px;
        background: {_N_BORDER};
        margin: 0 0 1.4rem; border-radius: 1px;
        opacity: .8;
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
        display: flex; justify-content: center; gap: 1.5rem;
        margin-top: 1rem; padding-top: 1rem;
        border-top: 1px solid {_N_BORDER};
        opacity: .9;
    }}
    .auth-trust-item {{
        display: flex; align-items: center; gap: .3rem;
        font-size: .7rem; color: {_N_MUTED};
        font-family: 'DM Sans', sans-serif;
        letter-spacing: .02em;
    }}
    </style>
    """, unsafe_allow_html=True)

    # ── Wordmark + headline ───────────────────────────────────────────────────
    st.markdown(f"""
    <div style="text-align:center; padding:.75rem 0 1rem;">

      <div style="
          font-family: 'DM Sans', sans-serif;
          font-size: clamp(2.4rem, 5.5vw, 3.2rem);
          font-weight: 900;
          letter-spacing: -0.035em;
          color: {_N_TEXT}; line-height: 1.1;
          margin-bottom: .55rem;">
        📝&thinsp;Verific<span style="
          background: linear-gradient(135deg,{_N_ACC},{_N_ACC2});
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;">AI</span>
      </div>

      <p style="font-size:.9rem; font-weight:500;
                color:{_N_TEXT2}; margin:0;
                line-height:1.5; font-family:'DM Sans',sans-serif;">
        Verifiche scolastiche professionali in <strong style="color:{_N_ACC}; font-weight:700;">30 secondi</strong>.
      </p>

    </div>

    <div class="auth-hr"></div>
    """, unsafe_allow_html=True)

    # ── Tabs ─────────────────────────────────────────────────────────────────
    tab_login, tab_reg, tab_reset = st.tabs(
        ["Accedi", "Registrati", "Reset password"]
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
                        st.warning("Password errata. Usa il tab **Password** per reimpostarla.")
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
                    st.error(f"Errore durante la registrazione: {e}")

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

    # ── Trust bar + footer ────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="auth-trust">
      <div class="auth-trust-item">🔒&ensp;Dati protetti</div>
      <div class="auth-trust-item">🇮🇹&ensp;Per docenti italiani</div>
      <div class="auth-trust-item">⚡&ensp;Gratis per iniziare</div>
    </div>
    <div style="text-align:center; padding:.6rem 0 .1rem; font-family:'DM Sans',sans-serif;">
      <p style="font-size:.72rem; color:{_N_MUTED}; margin:0;">
        Accedendo accetti i&nbsp;<a href="#"
          style="color:{_N_TEXT2}; font-weight:600; text-decoration:none;">termini di utilizzo</a>.
      </p>
    </div>
    """, unsafe_allow_html=True)
