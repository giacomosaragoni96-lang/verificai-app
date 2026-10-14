import streamlit as st
import streamlit.components.v1 as components
import base64
import hashlib
import html
import os
import secrets as _secrets
import time
from urllib.parse import urlencode

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
_ACCENT    = "#2563EB"   # lo stesso blu dell'app
_ACCENT2   = "#3B82F6"
_ACCENT_L  = "#EFF6FF"

# Colori moderni aggiuntivi
_PRIMARY    = _ACCENT
_PRIMARY_L  = _ACCENT2
_SUCCESS    = "#10B981"
_WARNING    = "#92400E"  # Very dark orange - ensures any text is readable
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

    # Ritorno da Google (?code=...): scambia il codice e crea la sessione
    gestisci_ritorno_google(supabase)
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


# ── LOGIN CON GOOGLE — Supabase OAuth con PKCE ───────────────────────────────
# Il browser va su Google passando da Supabase e torna all'app con ?code=...
# Dopo il ritorno la sessione Streamlit è nuova, quindi il "code_verifier" PKCE
# resta in memoria sul server (cache condivisa, scade in 10 minuti) e si ritrova
# con l'id in ?goauth=. Poi il flusso è quello di sempre: sessione in ?rt=TOKEN.
_PKCE_SCADENZA = 600


@st.cache_resource
def _pkce_pendenti() -> dict:
    return {}


def _b64url(dati: bytes) -> str:
    return base64.urlsafe_b64encode(dati).rstrip(b"=").decode()


def _url_app() -> str:
    try:
        url = st.secrets.get("APP_URL")
    except Exception:
        url = None
    if not url:
        try:
            from config import SHARE_URL as url
        except Exception:
            url = "https://verificai.streamlit.app"
    return str(url).rstrip("/")


@st.cache_data(ttl=300, show_spinner=False)
def _google_attivo(base: str, chiave: str) -> bool:
    """True se su Supabase il provider Google è acceso (impostazioni pubbliche del progetto)."""
    try:
        import requests
        r = requests.get(f"{base}/auth/v1/settings", headers={"apikey": chiave}, timeout=5)
        return bool(r.ok and r.json().get("external", {}).get("google"))
    except Exception:
        return False


def url_login_google():
    """Indirizzo a cui mandare il browser per il login con Google (None se non configurato)."""
    try:
        base  = str(st.secrets["SUPABASE_URL"]).rstrip("/")
        chiave = str(st.secrets["SUPABASE_KEY"])   # chiave pubblica (anon), la stessa del client
    except Exception:
        return None
    if not _google_attivo(base, chiave):
        return None   # provider spento su Supabase: niente pulsante che porterebbe a un errore

    ora = time.time()
    in_cache = st.session_state.get("_google_login")
    if in_cache and ora - in_cache["t"] < _PKCE_SCADENZA * 0.8:
        return in_cache["url"]

    pendenti = _pkce_pendenti()
    for k in [k for k, (_, t) in pendenti.items() if ora - t > _PKCE_SCADENZA]:
        pendenti.pop(k, None)
    while len(pendenti) >= 200:
        pendenti.pop(next(iter(pendenti)), None)

    verifier  = _b64url(os.urandom(48))
    challenge = _b64url(hashlib.sha256(verifier.encode()).digest())
    sid       = _secrets.token_urlsafe(12)
    pendenti[sid] = (verifier, ora)

    # Un link condiviso (?share=) non deve perdersi nel giro di login con Google
    _par_ritorno = {"goauth": sid}
    _share = st.query_params.get("share")
    if _share and isinstance(_share, str) and len(_share) <= 64:
        _par_ritorno["share"] = _share
    redirect_to = f"{_url_app()}/?" + urlencode(_par_ritorno)
    url = f"{base}/auth/v1/authorize?" + urlencode({
        "provider": "google",
        "redirect_to": redirect_to,
        "code_challenge": challenge,
        "code_challenge_method": "s256",
        "prompt": "select_account",     # Google chiede sempre quale account usare
    })
    st.session_state["_google_login"] = {"url": url, "t": ora}
    return url


def gestisci_ritorno_google(supabase):
    """Se l'URL contiene ?code=... (ritorno da Google), crea la sessione dell'utente."""
    qp = st.query_params
    code    = qp.get("code")
    errore  = qp.get("error_description") or qp.get("error")
    if not code and not errore:
        return

    sid = qp.get("goauth")
    for chiave in ("code", "goauth", "error", "error_code", "error_description"):
        qp.pop(chiave, None)

    if not code:
        st.session_state["_google_errore"] = "Accesso con Google annullato o non riuscito. Riprova."
        return

    pendenti = _pkce_pendenti()
    if sid and sid in pendenti:
        candidati = [pendenti.pop(sid)[0]]
    else:
        # Se Supabase ha tolto il parametro dal ritorno, provo gli ultimi accessi avviati
        recenti = sorted(pendenti.items(), key=lambda kv: -kv[1][1])[:5]
        candidati = [v for _, (v, _t) in recenti]

    for verifier in candidati:
        try:
            res = supabase.auth.exchange_code_for_session(
                {"auth_code": code, "code_verifier": verifier}
            )
        except Exception:
            continue
        if res and res.user and res.session:
            st.session_state.utente               = res.user
            st.session_state["_sb_access_token"]  = res.session.access_token
            st.session_state["_sb_refresh_token"] = res.session.refresh_token
            salva_sessione_cookie(res)
            return

    st.session_state["_google_errore"] = "Accesso con Google non riuscito. Riprova."


# Messaggi della pagina di accesso: un solo stile, testo scuro su fondo chiaro (contrasto AA).
_MSG_STILI = {
    "errore": ("#FEF2F2", "#991B1B", "#FCA5A5", "❌"),
    "avviso": ("#FFFBEB", "#78350F", "#FCD34D", "⚠️"),
    "ok":     ("#F0FDF4", "#14532D", "#86EFAC", "✅"),
    "info":   ("#EFF6FF", "#1E3A8A", "#93C5FD", "ℹ️"),
}


def _msg(tipo: str, testo: str) -> None:
    sfondo, colore, bordo, icona = _MSG_STILI.get(tipo, _MSG_STILI["info"])
    st.markdown(
        f'<div role="alert" style="background:{sfondo};color:{colore};border:1px solid {bordo};'
        'border-radius:12px;padding:.8rem 1rem;margin:.8rem 0;font-family:DM Sans,sans-serif;'
        f'font-weight:500;font-size:.92rem;line-height:1.5;">{icona} {html.escape(testo)}</div>',
        unsafe_allow_html=True,
    )


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
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;0,800;0,900;1,400&display=swap');

    /* ═══ Base Modern Design System - Tema Chiaro ═══ */
    html, body,
    [data-testid="stAppViewContainer"],
    .stApp {{
        background: {_BG} !important;
        font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
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
    [data-testid="stTextInput"] input,
    .stTextInput input,
    input[type="text"],
    input[type="password"],
    input[type="email"] {{
        background: {_BG2} !important;
        background-color: {_BG2} !important;
        border: 2px solid {_BORDER} !important;
        border-color: {_BORDER} !important;
        border-radius: 16px !important;
        color: {_TEXT} !important;
        color-scheme: light !important;
        -webkit-text-fill-color: {_TEXT} !important;
        -webkit-appearance: none !important;
        appearance: none !important;
        font-family: 'DM Sans', sans-serif !important;
        font-size: 1rem !important;
        font-weight: 500 !important;
        padding: 16px 20px !important;
        min-height: 56px !important;
        transition: all .25s cubic-bezier(0.4, 0, 0.2, 1) !important;
        outline: none !important;
        box-shadow: none !important;
    }}
    
    /* Force CSS custom properties */
    [data-testid="stTextInput"] *,
    .stTextInput * {{
        --background-color: {_BG2} !important;
        --text-color: {_TEXT} !important;
        --border-color: {_BORDER} !important;
    }}
    
    [data-testid="stTextInput"] input:focus,
    .stTextInput input:focus,
    input[type="text"]:focus,
    input[type="password"]:focus,
    input[type="email"]:focus {{
        border-color: {_PRIMARY} !important;
        border: 2px solid {_PRIMARY} !important;
        background: {_BG2} !important;
        background-color: {_BG2} !important;
        color: {_TEXT} !important;
        -webkit-text-fill-color: {_TEXT} !important;
        box-shadow: 
            0 0 0 4px rgba({_PRIMARY.replace('#', '')},.15),
            0 0 0 1px {_PRIMARY} !important;
        outline: none !important;
        transform: translateY(-1px) !important;
    }}
    
    [data-testid="stTextInput"] input:hover,
    .stTextInput input:hover,
    input[type="text"]:hover,
    input[type="password"]:hover,
    input[type="email"]:hover {{
        border-color: {_BORDER2} !important;
        background: {_BG2} !important;
        background-color: {_BG2} !important;
    }}
    
    [data-testid="stTextInput"] input::placeholder,
    .stTextInput input::placeholder,
    input[type="text"]::placeholder,
    input[type="password"]::placeholder,
    input[type="email"]::placeholder {{
        color: {_MUTED} !important; 
        opacity: 0.8 !important;
        font-weight: 400 !important;
        -webkit-text-fill-color: {_MUTED} !important;
    }}
    
    [data-testid="stTextInput"] label p,
    .stTextInput label p {{
        color: {_TEXT2} !important;
        font-size: .875rem !important;
        font-weight: 600 !important;
        letter-spacing: .01em !important;
        font-family: 'DM Sans', sans-serif !important;
        margin-bottom: 0.5rem !important;
        -webkit-text-fill-color: {_TEXT2} !important;
    }}
    
    /* Additional override for any remaining black inputs */
    div[data-testid="stTextInput"] > div > div > input,
    div.stTextInput > div > div > input {{
        background: {_BG2} !important;
        background-color: {_BG2} !important;
        color: {_TEXT} !important;
        -webkit-text-fill-color: {_TEXT} !important;
        border: 2px solid {_BORDER} !important;
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
        font-family: 'DM Sans', sans-serif !important;
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
    div.stButton > button[data-testid="stBaseButton-primary"],
    [data-testid="stFormSubmitButton"] > button {{
        background: linear-gradient(135deg, {_PRIMARY}, {_PRIMARY_L}) !important;
        color: white !important;
        -webkit-text-fill-color: white !important;
        border: none !important;
        border-radius: 16px !important;
        font-family: 'DM Sans', sans-serif !important;
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

    /* ═══ Modern Messages (excluding warnings - handled inline) ═══ */
    [data-testid="stAlert"] {{
        background: rgba({_SURFACE_L.replace('#', '')},.9) !important;
        border: 1px solid rgba({_BORDER.replace('#', '')},.3) !important;
        border-radius: 16px !important;
        color: {_TEXT} !important;
        font-family: 'DM Sans', sans-serif !important;
        padding: 1.25rem 1.5rem !important;
        box-shadow: 0 4px 16px rgba(0,0,0,.1) !important;
        backdrop-filter: blur(10px);
    }}
    
    /* Force white text on dark warning background */
    [data-testid="stAlert"][data-testid="stWarning"] {{
        color: white !important;
        background: {_WARNING} !important;
    }}
    [data-testid="stAlert"][data-testid="stWarning"] * {{
        color: white !important;
    }}
    
    /* Error messages - red background with white text */
    [data-testid="stAlert"][data-testid="stError"] {{
        background: {_ERROR} !important;
        background-color: {_ERROR} !important;
        border: 1px solid {_ERROR} !important;
        color: #1E293B !important;
        -webkit-text-fill-color: #1E293B !important;
    }}
    [data-testid="stAlert"][data-testid="stError"] * {{
        color: #1E293B !important;
        -webkit-text-fill-color: #1E293B !important;
    }}
    
    /* Success messages - green background with white text */
    [data-testid="stAlert"][data-testid="stSuccess"] {{
        background: {_SUCCESS} !important;
        background-color: {_SUCCESS} !important;
        border: 1px solid {_SUCCESS} !important;
        color: #1E293B !important;
        -webkit-text-fill-color: #1E293B !important;
    }}
    [data-testid="stAlert"][data-testid="stSuccess"] * {{
        color: #1E293B !important;
        -webkit-text-fill-color: #1E293B !important;
    }}
    
    /* Info messages - blue background with white text */
    [data-testid="stAlert"][data-testid="stInfo"] {{
        background: {_PRIMARY} !important;
        background-color: {_PRIMARY} !important;
        border: 1px solid {_PRIMARY} !important;
        color: #1E293B !important;
        -webkit-text-fill-color: #1E293B !important;
    }}
    [data-testid="stAlert"][data-testid="stInfo"] * {{
        color: #1E293B !important;
        -webkit-text-fill-color: #1E293B !important;
    }}

    /* ═══ Modern Typography ─══ */
    .auth-heading {{
        font-family: 'DM Sans', sans-serif;
        font-size: clamp(2rem, 5vw, 2.8rem);
        font-weight: 800;
        letter-spacing: -0.02em;
        color: {_TEXT};
        line-height: 1.1;
        margin-bottom: 0.75rem;
        text-align: center;
    }}
    .auth-subheading {{
        font-family: 'DM Sans', sans-serif;
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
        font-family: 'DM Sans', sans-serif;
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

    # ── Intestazione ────────────────────────────────────────────────────
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
        Crea la tua verifica in <strong style="color:{_PRIMARY}; font-weight:700;">un minuto</strong>.
      </p>

    </div>

    <div class="auth-divider"></div>
    """, unsafe_allow_html=True)

    # Link condiviso da un collega: chi non è registrato arriva qui, glielo diciamo
    if st.query_params.get("share"):
        _msg("info", "Un collega ha condiviso una verifica con te: accedi o registrati e la trovi qui.")

    # ── Accedi con Google ────────────────────────────────────────────────────
    _err_google = st.session_state.pop("_google_errore", None)
    if _err_google:
        _msg("errore", _err_google)
    _url_google = url_login_google()
    if _url_google:
        st.markdown(
            f'<a href="{html.escape(_url_google, quote=True)}" target="_blank" rel="noopener" style="'
            'display:flex;align-items:center;justify-content:center;gap:10px;'
            f'background:#fff;color:{_TEXT};border:1.5px solid {_BORDER2};border-radius:12px;'
            'padding:.7rem 1rem;font-weight:700;font-size:.97rem;text-decoration:none;'
            'font-family:DM Sans,sans-serif;margin:.2rem 0 .9rem;">'
            '<svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true">'
            '<path fill="#EA4335" d="M24 9.5c3.5 0 6.6 1.2 9.1 3.6l6.8-6.8C35.8 2.4 30.3 0 24 0 14.6 0 6.5 5.4 2.6 13.2l7.9 6.1C12.4 13.6 17.7 9.5 24 9.5z"/>'
            '<path fill="#4285F4" d="M46.5 24.5c0-1.6-.1-3.1-.4-4.5H24v9h12.7c-.6 3-2.3 5.5-4.8 7.2l7.6 5.9c4.4-4.1 7-10.1 7-17.6z"/>'
            '<path fill="#FBBC05" d="M10.5 28.7a14.5 14.5 0 0 1 0-9.4l-7.9-6.1a24 24 0 0 0 0 21.6l7.9-6.1z"/>'
            '<path fill="#34A853" d="M24 48c6.5 0 11.9-2.1 15.9-5.8l-7.6-5.9c-2.1 1.4-4.9 2.3-8.3 2.3-6.3 0-11.6-4.1-13.5-9.8l-7.9 6.1C6.5 42.6 14.6 48 24 48z"/>'
            '</svg>Continua con Google</a>'
            f'<div style="text-align:center;color:{_TEXT2};font-size:.8rem;margin-bottom:.4rem;'
            'font-family:DM Sans,sans-serif;">Si apre in una nuova scheda · oppure con la tua email</div>',
            unsafe_allow_html=True,
        )

    # ── Schede ───────────────────────────────────────────────────────────────
    tab_login, tab_reg = st.tabs(["Accedi", "Registrati"])

    with tab_login:
        with st.form("form_login", border=False):
            email    = st.text_input("Email",    key="login_email", placeholder="docente@scuola.it")
            password = st.text_input("Password", key="login_pass",  placeholder="••••••••",
                                     type="password")
            invia_login = st.form_submit_button("Accedi →", type="primary", use_container_width=True)
        if invia_login:
            if not email or not password:
                _msg("avviso", "Inserisci email e password.")
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
                    if "email not confirmed" in str(e).lower():
                        _msg("avviso", "Email non confermata. Apri il link che ti abbiamo inviato per posta e poi accedi.")
                    else:
                        _msg("errore", "Email o password non corrette. Se non ricordi la password, "
                                       "usa «Password dimenticata?» qui sotto.")

        with st.expander("Password dimenticata?"):
            st.markdown(
                '<div class="auth-reset-hint">'
                "Inserisci la tua email: ti mandiamo un link per scegliere una nuova password."
                "</div>",
                unsafe_allow_html=True,
            )
            email_reset = st.text_input("Email", key="reset_email", placeholder="docente@scuola.it")
            if st.button("Invia link di reset →", use_container_width=True, key="btn_reset"):
                if not email_reset:
                    _msg("avviso", "Inserisci la tua email.")
                else:
                    try:
                        supabase.auth.reset_password_email(email_reset)
                        _msg("ok", "Se l'email è registrata, riceverai un link per reimpostare la password.")
                    except Exception:
                        _msg("errore", "Non sono riuscito a inviare l'email. Riprova tra qualche minuto.")

    with tab_reg:
        with st.form("form_registrazione", border=False):
            email_r    = st.text_input("Email", key="reg_email", placeholder="docente@scuola.it")
            password_r = st.text_input(
                "Password (almeno 6 caratteri)", key="reg_pass",
                placeholder="••••••••", type="password",
            )
            invia_reg = st.form_submit_button("Crea account gratuito →", type="primary",
                                              use_container_width=True)
        if invia_reg:
            if not email_r or not password_r:
                _msg("avviso", "Inserisci email e password.")
            elif len(password_r) < 6:
                _msg("avviso", "La password deve essere di almeno 6 caratteri.")
            else:
                try:
                    res = supabase.auth.sign_up({"email": email_r, "password": password_r})
                    st.session_state.utente = res.user
                    if res.session:
                        st.session_state["_sb_access_token"]  = res.session.access_token
                        st.session_state["_sb_refresh_token"] = res.session.refresh_token
                        salva_sessione_cookie(res)
                        st.rerun()
                    _msg("ok", "Account creato. Ti abbiamo mandato un'email: conferma l'indirizzo e poi accedi.")
                except Exception as e:
                    _err_str = str(e).lower()
                    if "already registered" in _err_str or "already exists" in _err_str:
                        _msg("errore", "Questa email è già registrata. Prova ad accedere, oppure usa "
                                       "«Password dimenticata?» nella scheda Accedi.")
                    else:
                        _msg("errore", "Registrazione non riuscita. Controlla i dati e riprova; "
                                       "se il problema continua, scrivici.")

    # ── Barra di fiducia + footer ────────────────────────────────────────────
    st.markdown(f"""
    <div class="auth-trust">
      <div class="auth-trust-item">🎁&ensp;5 verifiche gratis al mese</div>
      <div class="auth-trust-item">🇮🇹&ensp;Per docenti italiani</div>
      <div class="auth-trust-item">🔒&ensp;I tuoi dati restano tuoi</div>
    </div>
    <div style="text-align:center; padding:1rem 0 0.5rem; font-family:'DM Sans',sans-serif;">
      <p style="font-size:0.8rem; color:{_TEXT2}; margin:0; font-weight:500;">
        Accedendo accetti l'<a href="?pagina=privacy" target="_blank" rel="noopener"
          style="color:{_TEXT}; font-weight:600;">informativa sulla privacy</a>.
      </p>
    </div>
    """, unsafe_allow_html=True)
