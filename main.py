import streamlit as st
import base64
import re
import os
import time
import google.generativeai as genai
from generation import genera_verifica
from prompts import (
    prompt_titolo, prompt_corpo_verifica, prompt_controllo_qualita,
    prompt_versione_b, prompt_versione_ridotta, prompt_soluzioni,
    prompt_modifica,
)
from docx_export import latex_to_docx_via_ai
from latex_utils import (
    compila_pdf, inietta_griglia, riscala_punti,
    fix_items_environment, rimuovi_vspace_corpo, pulisci_corpo_latex,
    rimuovi_punti_subsection, parse_esercizi, build_griglia_latex,
    pdf_to_images_bytes,
)
from config import (
    APP_NAME, APP_ICON, APP_TAGLINE, SHARE_URL, FEEDBACK_FORM_URL,
    LIMITE_MENSILE, ADMIN_EMAILS, MODELLI_DISPONIBILI, THEMES,
    SCUOLE, CALIBRAZIONE_SCUOLA, MATERIE, NOTE_PLACEHOLDER, TIPI_ESERCIZIO,
)
from dotenv import load_dotenv
from supabase import create_client, Client

# ── NUOVO: import da auth.py ─────────────────────────────────────────────────────
from auth import ripristina_sessione, mostra_auth

if "theme" not in st.session_state:
    st.session_state.theme = "light"
T = THEMES[st.session_state.theme]

# ── CONFIGURAZIONE ──────────────────────────────────────────────────────────────
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    st.error("⚠️ Chiave API mancante! Crea un file .env con: GOOGLE_API_KEY=la_tua_chiave")
    st.stop()
genai.configure(api_key=API_KEY)
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
SUPABASE_SERVICE_KEY = st.secrets["SUPABASE_SERVICE_KEY"]
supabase_admin: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# ── PERSISTENT LOGIN ─────────────────────────────────────────────────────────────
# _ripristina_sessione() e mostra_auth() sono ora in auth.py
ripristina_sessione(supabase)

# ── AUTENTICAZIONE GATE ──────────────────────────────────────────────────────────
if 'utente' not in st.session_state:
    st.session_state.utente = None

if st.session_state.utente is None:
    mostra_auth(supabase)
    st.stop()

# ── FUNZIONI ───────────────────────────────────────────────────────────────────

def _get_verifiche_mese(user_id):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    primo_mese = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
    try:
        res = supabase_admin.table("verifiche_storico") \
            .select("id", count="exact") \
            .eq("user_id", user_id) \
            .gte("created_at", primo_mese) \
            .execute()
        return res.count or 0
    except Exception:
        return 0


def _giorni_al_reset():
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    if now.month == 12:
        reset = now.replace(year=now.year+1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        reset = now.replace(month=now.month+1, day=1, hour=0, minute=0, second=0, microsecond=0)
    delta = reset - now
    giorni = delta.days
    ore    = delta.seconds // 3600
    return giorni, ore

def modifica_verifica_con_ai(latex_originale, richiesta_modifica, model):
    response = model.generate_content(prompt_modifica(latex_originale, richiesta_modifica))
    latex_modificato = response.text.replace("```latex", "").replace("```", "").strip()
    if "\\end{document}" not in latex_modificato:
        latex_modificato += "\n\\end{document}"
    return latex_modificato


def costruisci_prompt_esercizi(esercizi_custom, num_totale, punti_totali, mostra_punteggi):
    n_liberi = max(0, num_totale - len(esercizi_custom))
    righe = [
        f"\nSTRUTTURA ESERCIZI — REGOLA ASSOLUTA:",
        f"Devi generare ESATTAMENTE {num_totale} esercizi, né uno di più né uno di meno.",
        f"Ogni esercizio è un blocco \\subsection*{{Esercizio N: Titolo}}.",
        f"Conta i tuoi \\subsection* prima di terminare: devono essere ESATTAMENTE {num_totale}.",
    ]
    immagini = []

    if mostra_punteggi and num_totale > 0:
        pts_base = punti_totali // num_totale
        resto = punti_totali - pts_base * num_totale
        pts_per_ex = [pts_base] * num_totale
        if resto > 0:
            pts_per_ex[0] += resto
        righe.append(f"\nDISTRIBUZIONE PUNTI SUGGERITA (totale ESATTO: {punti_totali} pt):")
        for i_ex in range(num_totale):
            righe.append(f"  - Esercizio {i_ex+1}: circa {pts_per_ex[i_ex]} pt (distribuisci tra i sottopunti)")
        righe.append(f"REGOLA CRITICA: la somma di TUTTI i (X pt) nei sottopunti DEVE essere ESATTAMENTE {punti_totali} pt.")

    ha_primo_custom = len(esercizi_custom) > 0
    if not ha_primo_custom:
        righe.append(
            f"\nREGOLA PRIMO ESERCIZIO (Esercizio 1 — SEMPRE presente, NON modificabile):\n"
            f"Il primo esercizio DEVE chiamarsi 'Saperi Essenziali' e coprire i concetti fondamentali\n"
            f"dell'argomento che TUTTI gli studenti devono conoscere (definizioni, concetti base, formule\n"
            f"chiave, fatti imprescindibili). NON inserire mai il simbolo (*) in questo esercizio:\n"
            f"è obbligatorio per tutti, nessuna esclusione. Calibra il livello di difficoltà in modo\n"
            f"accessibile. Gli esercizi {2}–{num_totale} possono approfondire e variare."
        )

    righe.append(f"\nDETTAGLIO ESERCIZI ({num_totale} totali):")
    for i, ex in enumerate(esercizi_custom, 1):
        tipo, desc = ex.get('tipo', 'Aperto'), ex.get('descrizione', '').strip()
        riga = f"- Esercizio {i} [{tipo}]" + (f": {desc}" if desc else "")
        if ex.get('immagine'):
            riga += f" — vedi immagine allegata per l'esercizio {i}"
            immagini.append({'idx': i, 'data': ex['immagine'].getvalue(),
                             'mime_type': ex['immagine'].type})
        if tipo == "Scelta multipla":
            riga += " — opzioni con \\begin{enumerate}[a)] \\item prima \\item seconda \\end{enumerate}"
        elif tipo == "Vero/Falso":
            riga += " — $\\square$ \\textbf{V} $\\quad\\square$ \\textbf{F} \\quad testo (min 3)"
        elif tipo == "Completamento":
            riga += " — \\underline{\\hspace{3cm}} per gli spazi"
        righe.append(riga)
    if n_liberi > 0:
        start_idx = len(esercizi_custom) + 1
        end_idx   = num_totale
        righe.append(f"- Esercizi {start_idx}–{end_idx}: genera tu {n_liberi} esercizi coerenti con l'argomento.")
    return "\n".join(righe), immagini


# ── HELPER ───────────────────────────────────────────────────────────────────────
def _tempo_relativo(ts):
    if ts is None:
        return ""
    diff = time.time() - ts
    if diff < 60:
        return "pochi secondi fa"
    elif diff < 3600:
        m = int(diff // 60)
        return f"{m} min fa"
    elif diff < 86400:
        h = int(diff // 3600)
        return f"{h} ore fa"
    else:
        return time.strftime("%d/%m", time.localtime(ts))


def _stima_dimensione(data_bytes):
    if data_bytes is None:
        return "—"
    kb = len(data_bytes) / 1024
    if kb < 1024:
        return f"{kb:.0f} KB"
    return f"{kb/1024:.1f} MB"


# ── SESSION STATE ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title=APP_NAME,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="collapsed"
)


def _vf():
    return {'latex': '', 'pdf': None, 'preview': False,
            'soluzioni_latex': '', 'soluzioni_pdf': None, 'docx': None,
            'pdf_ts': None, 'docx_ts': None, 'latex_originale': ''}

if 'utente' not in st.session_state: st.session_state.utente = None
if 'verifiche' not in st.session_state: st.session_state.verifiche = {'A': _vf(), 'B': _vf(), 'R': _vf(), 'RB': _vf(), 'S': {'latex': None, 'testo': None}}
if 'esercizi_custom' not in st.session_state: st.session_state.esercizi_custom = []
if 'last_materia'    not in st.session_state: st.session_state.last_materia = None
if 'last_argomento'  not in st.session_state: st.session_state.last_argomento = None
if 'last_gen_ts'     not in st.session_state: st.session_state.last_gen_ts = None
if '_storico_refresh' not in st.session_state: st.session_state._storico_refresh = 0
if '_preferiti' not in st.session_state: st.session_state._preferiti = set()
if '_storico_page' not in st.session_state: st.session_state._storico_page = 1
if '_onboarding_done' not in st.session_state: st.session_state._onboarding_done = False

# ── CALCOLA VERIFICHE DEL MESE (una volta per rerun) ────────────────────────────
_verifiche_mese_count = _get_verifiche_mese(st.session_state.utente.id) if st.session_state.utente else 0
_is_admin = (st.session_state.utente.email in ADMIN_EMAILS) if st.session_state.utente else False
_limite_raggiunto = (not _is_admin) and (_verifiche_mese_count >= LIMITE_MENSILE)

# ── CSS GLOBALE ──────────────────────────────────────────────────────────────────
is_dark = (st.session_state.theme == "dark")

_SB_LABEL   = "#c8c6bc"
_SB_MUTED   = "#8a8880"
_SB_BORDER  = "#2a2926"
_SB_TEXT    = "#e8e6e0"

st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;0,800;0,900;1,400&display=swap');

  *, *::before, *::after {{ box-sizing: border-box; }}

  .stApp {{
    background-color: {T['bg']} !important;
    font-family: 'DM Sans', sans-serif;
    color: {T['text']};
    transition: background-color 0.25s ease, color 0.25s ease;
  }}

  .block-container {{
    padding: 5rem 1.5rem 4rem !important;
    max-width: 780px !important;
    margin: 0 auto !important;
  }}

  #MainMenu, footer {{ visibility: hidden; }}
  .stDecoration {{ display: none; }}

  header[data-testid="stHeader"] {{
    background-color: {T['bg']} !important;
    border-bottom: 1px solid {T['border']} !important;
  }}

  header button svg {{
    fill: {T['text']} !important;
    color: {T['text']} !important;
    stroke: {T['text']} !important;
  }}
  header button {{
    background: {T['card']} !important;
    border: 1.5px solid {T['border2']} !important;
    border-radius: 8px !important;
    color: {T['text']} !important;
  }}
  header button:hover {{
    background: {T['hover']} !important;
    border-color: {T['accent']} !important;
  }}
  header button:hover svg {{
    fill: {T['accent']} !important;
  }}
  .stMarkdown h1 a, .stMarkdown h2 a, .stMarkdown h3 a {{ display: none !important; }}

  /* ════ SIDEBAR ════ */
  [data-testid="stSidebar"] {{
    background: #141412 !important;
    border-right: 1px solid {_SB_BORDER} !important;
  }}
  .sidebar-title {{
    font-family: 'DM Sans', sans-serif;
    font-size: 1.1rem !important;
    font-weight: 800 !important;
    letter-spacing: -0.01em;
    color: #f5f3ed !important;
    margin: 0.5rem 0 1.2rem 0;
    padding-bottom: 0.6rem;
    border-bottom: 1px solid {_SB_BORDER};
  }}
  [data-testid="stSidebar"] .block-container {{
    padding: 1.5rem 1.2rem !important;
    max-width: 100% !important;
  }}
  [data-testid="stSidebar"] p,
  [data-testid="stSidebar"] span,
  [data-testid="stSidebar"] label,
  [data-testid="stSidebar"] div {{
    color: {_SB_TEXT} !important;
  }}
  [data-testid="stSidebar"] .stTextInput label p,
  [data-testid="stSidebar"] .stSelectbox label p,
  [data-testid="stSidebar"] .stNumberInput label p {{
    color: {_SB_MUTED} !important;
    font-size: 0.7rem !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    font-weight: 700 !important;
  }}
  [data-testid="stSidebar"] .stCheckbox label {{
    color: {_SB_TEXT} !important;
    font-size: 0.9rem !important;
  }}
  [data-testid="stSidebar"] .stCheckbox [data-testid="stCheckbox"] span:first-child {{
    background-color: {T['input_bg']} !important;
    border: 1.5px solid {T['border2']} !important;
    border-radius: 5px !important;
  }}
  [data-testid="stSidebar"] .stTextInput input,
  [data-testid="stSidebar"] .stNumberInput input {{
    background: #232320 !important;
    border: 1.5px solid #3d3c36 !important;
    border-radius: 8px !important;
    color: #f5f3ed !important;
  }}
  [data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] > div:first-child {{
    background: #232320 !important;
    border: 1.5px solid #3d3c36 !important;
    border-radius: 8px !important;
  }}
  [data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] span {{
    color: #f5f3ed !important;
  }}
  [data-testid="stSidebar"] .stRadio label {{
    color: {_SB_TEXT} !important;
  }}
  [data-testid="stSidebar"] .stRadio [data-testid="stMarkdownContainer"] p {{
    color: {_SB_TEXT} !important;
  }}
  [data-testid="stSidebar"] .stButton button {{
    background: #232320 !important;
    color: #f5f3ed !important;
    border: 1.5px solid #3d3c36 !important;
    border-radius: 8px !important;
  }}
  [data-testid="stSidebar"] .stButton button:hover {{
    background: #2e2d28 !important;
    border-color: #5a5950 !important;
  }}
  [data-testid="stSidebar"] .stSelectSlider [data-testid="stMarkdownContainer"] p {{
    color: {_SB_TEXT} !important;
  }}
  [data-testid="stSidebar"] .section-label {{
    color: #5a5950 !important;
    border-bottom-color: {_SB_BORDER} !important;
  }}
  [data-testid="collapsedControl"] {{
    top: 0.75rem !important;
    left: 0.75rem !important;
    z-index: 999 !important;
  }}
  [data-testid="collapsedControl"] button {{
    background: {T['card']} !important;
    border: 2px solid {T['accent']} !important;
    border-radius: 10px !important;
    color: {T['accent']} !important;
    width: 40px !important;
    height: 40px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    box-shadow: 0 2px 12px {T['accent']}33 !important;
    transition: transform 0.15s ease, box-shadow 0.15s ease, background 0.15s ease !important;
    padding: 0 !important;
  }}
  [data-testid="collapsedControl"] button:hover {{
    background: {T['accent']} !important;
    box-shadow: 0 4px 18px {T['accent']}55 !important;
    transform: scale(1.08) !important;
  }}
  [data-testid="collapsedControl"] button:hover svg {{
    fill: #ffffff !important;
    color: #ffffff !important;
    stroke: #ffffff !important;
  }}
  [data-testid="collapsedControl"] button svg {{
    fill: {T['accent']} !important;
    color: {T['accent']} !important;
    stroke: {T['accent']} !important;
    width: 18px !important;
    height: 18px !important;
  }}

  [data-testid="stSidebar"] .sidebar-label,
  .sidebar-label {{
    font-size: 0.72rem !important;
    font-weight: 800 !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    color: #D97706 !important;
    margin: 1rem 0 0.5rem 0 !important;
    padding-bottom: 0.35rem !important;
    border-bottom: 2px solid #3a3320 !important;
    display: block !important;
  }}

  [data-testid="stSidebar"] .logout-btn-wrap div.stButton > button,
  [data-testid="stSidebar"] .logout-btn-wrap .stButton button,
  [data-testid="stSidebar"] .logout-btn-wrap button {{
    background: transparent !important;
    color: #f87171 !important;
    border: 1px solid #5c2222 !important;
    border-radius: 8px !important;
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    padding: 6px 14px !important;
    width: auto !important;
    min-height: unset !important;
    box-shadow: none !important;
    transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease !important;
    letter-spacing: 0.02em !important;
  }}
  [data-testid="stSidebar"] .logout-btn-wrap div.stButton > button:hover,
  [data-testid="stSidebar"] .logout-btn-wrap .stButton button:hover,
  [data-testid="stSidebar"] .logout-btn-wrap button:hover {{
    background: #2a0f0f !important;
    border-color: #f87171 !important;
    color: #fca5a5 !important;
    box-shadow: 0 0 0 1px #5c2222 !important;
  }}

  h1, h2, h3 {{
    font-family: 'DM Sans', sans-serif !important;
    color: {T['text']} !important;
    letter-spacing: -0.02em;
  }}

  .hero-wrap {{
    margin-bottom: 2.5rem;
    padding-bottom: 1.8rem;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-direction: column;
    flex-wrap: wrap;
    gap: 0;
    position: relative;
  }}
  .hero-left {{ flex: 1; min-width: 200px; text-align: center; }}
  @keyframes iconBounce {{
    0%   {{ transform: rotate(0deg) scale(1); }}
    15%  {{ transform: rotate(-12deg) scale(1.15); }}
    30%  {{ transform: rotate(8deg) scale(1.1); }}
    45%  {{ transform: rotate(-6deg) scale(1.05); }}
    60%  {{ transform: rotate(3deg) scale(1.02); }}
    75%  {{ transform: rotate(-1deg) scale(1.01); }}
    100% {{ transform: rotate(0deg) scale(1); }}
  }}
  @keyframes badgePop {{
    0%   {{ opacity: 0; transform: translateY(6px); }}
    100% {{ opacity: 1; transform: translateY(0); }}
  }}
  @keyframes subFadeIn {{
    0%   {{ opacity: 0; transform: translateY(4px); }}
    100% {{ opacity: 1; transform: translateY(0); }}
  }}
  .hero-title {{
    font-family: 'DM Sans', sans-serif;
    font-size: 96px !important;
    font-weight: 900 !important;
    color: {T['text']};
    line-height: 1.0;
    margin: 0 0 0.15rem 0;
    letter-spacing: -0.04em;
    display: inline-flex;
    align-items: center;
    gap: 0;
    justify-content: center;
  }}
  .hero-icon {{
    display: inline-block;
    margin-right: 0.3em;
    animation: iconBounce 1.1s ease 0.2s both;
    transform-origin: center bottom;
  }}
  .hero-ai {{
    background: linear-gradient(135deg, {T['accent']} 0%, #FF8C00 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    animation: badgePop 0.6s ease 0.5s both;
  }}
  .hero-sub {{
    font-size: 1.05rem;
    color: {T['text2']};
    margin: 0 0 0.55rem 0;
    font-weight: 500;
    letter-spacing: -0.01em;
    animation: subFadeIn 0.5s ease 0.35s both;
    opacity: 0;
  }}
  .hero-beta {{
    display: inline-block;
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: {T['muted']};
    background: {T['card2']};
    border: 1px solid {T['border2']};
    border-radius: 100px;
    padding: 2px 10px;
    font-family: 'DM Sans', sans-serif;
    animation: badgePop 0.5s ease 0.75s both;
    opacity: 0;
  }}

  .stTextInput label p,
  .stSelectbox label p,
  .stNumberInput label p,
  .stTextArea label p,
  .stFileUploader label p {{
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    color: {T['text2']} !important;
    letter-spacing: 0.01em;
    text-transform: uppercase;
    margin-bottom: 4px !important;
  }}

  .stTextInput input,
  .stNumberInput input {{
    background: {T['input_bg']} !important;
    border: 1.5px solid {T['border']} !important;
    border-radius: 10px !important;
    color: {T['text']} !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.95rem !important;
    padding: 14px 16px !important;
    min-height: 52px !important;
    height: 52px !important;
    box-sizing: border-box !important;
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
  }}
  .stTextInput input::placeholder,
  .stNumberInput input::placeholder {{
    color: {T['muted']} !important;
    opacity: 1 !important;
  }}
  .stTextInput input:focus,
  .stNumberInput input:focus {{
    border-color: {T['accent']} !important;
    box-shadow: 0 0 0 3px {T['accent_light']} !important;
    outline: none !important;
  }}
  .stTextArea textarea {{
    background: {T['input_bg']} !important;
    border: 1.5px solid {T['border']} !important;
    border-radius: 10px !important;
    color: {T['text']} !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.9rem !important;
    padding: 10px 14px !important;
  }}
  .stTextArea textarea::placeholder {{
    color: {T['muted']} !important;
    opacity: 1 !important;
  }}
  .stTextArea textarea:focus {{
    border-color: {T['accent']} !important;
    box-shadow: 0 0 0 3px {T['accent_light']} !important;
  }}

  .stSelectbox [data-baseweb="select"] > div:first-child {{
    background: {T['input_bg']} !important;
    border: 1.5px solid {T['border']} !important;
    border-radius: 10px !important;
    color: {T['text']} !important;
  }}
  .stSelectbox [data-baseweb="select"] span {{
    color: {T['text']} !important;
  }}

  .stCheckbox label {{
    color: {T['text']} !important;
    font-size: 0.9rem !important;
    font-family: 'DM Sans', sans-serif !important;
  }}
  .stCheckbox [data-testid="stCheckbox"] span:first-child {{
    background-color: {T['input_bg']} !important;
    border: 1.5px solid {T['border2']} !important;
    border-radius: 5px !important;
  }}

  div.stButton > button[kind="primary"] {{
    background: #D97706 !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    transition: transform 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275), box-shadow 0.2s ease, filter 0.2s ease !important;
    box-shadow: 0 2px 12px rgba(217,119,6,0.35) !important;
    display: block !important;
  }}
  div.stButton > button[kind="primary"]:hover {{
    transform: scale(1.05) !important;
    box-shadow: 0 10px 25px rgba(217,119,6,0.5) !important;
    filter: brightness(1.1) !important;
    border: none !important;
  }}
  div.stButton > button[kind="primary"]:active {{
    transform: scale(0.98) !important;
  }}
  div.stButton > button[kind="primary"]:disabled {{
    background: #9CA3AF !important;
    box-shadow: none !important;
    transform: none !important;
    filter: none !important;
    cursor: not-allowed !important;
    opacity: 0.7 !important;
  }}

  .dl-card {{
    background: #FFFFFF !important;
    padding: 1.2rem;
    border-radius: 15px;
    border: 1px solid #E0E0E0;
    text-align: center;
    margin-bottom: 1rem;
  }}
  .dl-label {{
    font-size: 0.85rem;
    color: #666;
    margin-bottom: 0.8rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }}
  .hint-docx {{
    font-size: 0.78rem;
    color: #888;
    line-height: 1.3;
    margin-top: 12px;
    font-style: italic;
    text-align: left;
    border-top: 1px solid #EEE;
    padding-top: 8px;
  }}

  .output-card {{
    background: {T['card']} !important;
    border: 1.5px solid {T['border2']} !important;
    border-radius: 16px !important;
    padding: 0 !important;
    margin-bottom: 1.5rem !important;
    overflow: hidden !important;
    box-shadow: {T['shadow_md']} !important;
  }}
  .output-card > div {{
    padding: 1.2rem !important;
  }}
  .stDownloadButton button,
  [data-testid="stDownloadButton"] button,
  .stButton [data-testid="baseButton-secondary"],
  .stButton button[kind="secondary"],
  button[data-testid="baseButton-secondary"] {{
    background: {T['card']} !important;
    color: {T['text']} !important;
    border: 1.5px solid {T['border2']} !important;
    border-radius: 12px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 1.05rem !important;
    font-weight: 700 !important;
    padding: 1rem 1.4rem !important;
    transition: border-color 0.18s ease, box-shadow 0.18s ease, transform 0.18s ease !important;
    letter-spacing: 0.01em !important;
    box-shadow: 0 2px 6px rgba(0,0,0,0.04) !important;
    width: 100% !important;
  }}
  .stDownloadButton button:hover,
  [data-testid="stDownloadButton"] button:hover,
  .stButton [data-testid="baseButton-secondary"]:hover,
  button[data-testid="baseButton-secondary"]:hover {{
    background: {T['hover']} !important;
    border-color: {T['accent']} !important;
    transform: translateY(-3px) !important;
    box-shadow: 0 6px 20px rgba(217,119,6,0.18) !important;
    color: {T['text']} !important;
  }}

  .action-card {{
    background: {T['card']} !important;
    border: 2px solid {T['border']} !important;
    border-radius: 14px !important;
    padding: 1.2rem !important;
    margin-bottom: 1rem !important;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
    position: relative !important;
    overflow: hidden !important;
  }}
  .action-card::before {{
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 4px;
    height: 100%;
    background: linear-gradient(180deg, {T['accent']} 0%, {T['accent']}00 100%);
    opacity: 0;
    transition: opacity 0.25s ease;
  }}
  .action-card:hover {{
    border-color: {T['accent']}88 !important;
    box-shadow: 0 8px 24px {T['accent']}15 !important;
    transform: translateY(-2px) !important;
  }}
  .action-card:hover::before {{
    opacity: 1;
  }}
  .action-card .stDownloadButton button,
  .action-card .stButton button {{
    background: linear-gradient(135deg, {T['accent']} 0%, {T['accent']}ee 100%) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 12px !important;
    font-size: 1rem !important;
    font-weight: 700 !important;
    padding: 1rem 1.5rem !important;
    box-shadow: 0 4px 14px {T['accent']}35 !important;
    transition: all 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275) !important;
  }}
  .action-card .stDownloadButton button:hover,
  .action-card .stButton button:hover {{
    transform: scale(1.03) !important;
    box-shadow: 0 6px 20px {T['accent']}50 !important;
    filter: brightness(1.08) !important;
  }}
  .action-card .stDownloadButton button:active,
  .action-card .stButton button:active {{
    transform: scale(0.98) !important;
  }}
  .action-card [data-testid="stExpander"] {{
    background: transparent !important;
    border: 2px dashed {T['border2']} !important;
    border-radius: 12px !important;
    transition: all 0.2s ease !important;
  }}
  .action-card [data-testid="stExpander"]:hover {{
    border-color: {T['accent']} !important;
    background: {T['accent_light']} !important;
  }}
  .action-card [data-testid="stExpander"] summary {{
    background: transparent !important;
    color: {T['text']} !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    padding: 1rem 1.2rem !important;
  }}
  .action-card [data-testid="stExpander"] summary:hover {{
    color: {T['accent']} !important;
  }}
  .action-card [data-testid="stExpander"] summary svg {{
    color: {T['accent']} !important;
  }}
  .tex-download {{
    opacity: 0.7 !important;
    transition: opacity 0.2s ease, transform 0.2s ease !important;
  }}
  .tex-download:hover {{
    opacity: 1 !important;
    transform: translateX(3px) !important;
  }}
  .hint-docx {{
    background: {T['accent_light']} !important;
    border-left: 3px solid {T['accent']} !important;
    border-radius: 8px !important;
    padding: 10px 14px !important;
    margin-top: 8px !important;
    font-size: 0.8rem !important;
    color: {T['text2']} !important;
    line-height: 1.5 !important;
  }}
  .hint-docx strong {{
    color: {T['accent']} !important;
  }}
  .section-action-label {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-size: 0.7rem;
    font-weight: 800;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: {T['muted']};
    margin-bottom: 0.8rem;
    padding-bottom: 0.5rem;
    border-bottom: 2px solid {T['border']};
  }}
  .section-action-label::before {{
    content: '';
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: {T['accent']};
    display: inline-block;
  }}

  .compact-uploader [data-testid="stFileUploader"] section {{
    padding: 0 !important;
    border: none !important;
    background: transparent !important;
    min-height: unset !important;
  }}
  .compact-uploader [data-testid="stFileUploadDropzone"] {{
    display: none !important;
  }}
  .compact-uploader [data-testid="stFileUploader"] button {{
    background: {T['card2']} !important;
    color: {T['text2']} !important;
    border: 1px solid {T['border2']} !important;
    border-radius: 8px !important;
    font-size: 0.8rem !important;
    padding: 6px 14px !important;
  }}
  .compact-uploader [data-testid="stFileUploader"] button:hover {{
    border-color: {T['accent']} !important;
    color: {T['accent']} !important;
  }}

  .tex-btn-wrap .stDownloadButton button,
  .tex-btn-wrap [data-testid="stDownloadButton"] button {{
    background: transparent !important;
    color: {T['muted']} !important;
    border: 1px solid {T['border']} !important;
    border-radius: 6px !important;
    font-size: 0.72rem !important;
    font-weight: 500 !important;
    padding: 0.3rem 0.7rem !important;
    width: 100% !important;
    box-shadow: none !important;
    transform: none !important;
  }}
  .tex-btn-wrap .stDownloadButton button:hover,
  .tex-btn-wrap [data-testid="stDownloadButton"] button:hover {{
    color: {T['text2']} !important;
    border-color: #5a5950 !important;
    background: {T['card2']} !important;
    box-shadow: none !important;
    transform: translateY(-1px) !important;
  }}

  [data-testid="stExpander"] {{
    background: {T['card']} !important;
    border: 1px solid {T['border']} !important;
    border-radius: 12px !important;
    margin-bottom: 0.75rem !important;
    overflow: hidden;
  }}
  [data-testid="stExpander"] summary {{
    padding: 0.85rem 1.1rem !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    color: {T['text']} !important;
    background: {T['card']} !important;
  }}
  [data-testid="stExpander"] summary:hover {{
    background: {T['hover']} !important;
  }}
  [data-testid="stExpander"] > div > div {{
    padding: 0.5rem 1.1rem 1rem !important;
  }}

  hr {{
    border: none;
    border-top: 1px solid {T['border']} !important;
    margin: 2rem 0 !important;
  }}

  [data-testid="stFileUploader"] section {{
    background: {T['card2']} !important;
    border: 1.5px dashed {T['border2']} !important;
    border-radius: 10px !important;
    padding: 0.75rem 1rem !important;
    min-height: unset !important;
  }}
  [data-testid="stFileUploader"] section > div {{ gap: 0.3rem !important; }}
  [data-testid="stFileUploadDropzone"] p,
  [data-testid="stFileUploadDropzone"] span,
  [data-testid="stFileUploadDropzone"] small,
  [data-testid="stFileUploader"] span,
  [data-testid="stFileUploader"] small,
  [data-testid="stFileUploader"] p {{
    color: {T['text2']} !important;
    opacity: 1 !important;
  }}
  [data-testid="stFileUploadDropzone"] button,
  [data-testid="stFileUploader"] button {{
    color: {T['accent']} !important;
    font-weight: 600 !important;
  }}
  [data-testid="stFileUploadDropzone"] svg {{
    fill: {T['muted']} !important;
    color: {T['muted']} !important;
  }}

  .chip {{
    display: inline-flex;
    align-items: center;
    gap: 4px;
    background: {T['accent_light']};
    color: {T['accent']};
    border: 1px solid {T['accent']};
    border-radius: 100px;
    padding: 2px 10px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
  }}

  .expander-heading {{
    font-size: 0.75rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.04em !important;
    text-transform: uppercase !important;
    color: {T['text2']} !important;
    margin: 1rem 0 0.4rem 0 !important;
    padding: 4px 10px !important;
    background: {T['card2']} !important;
    border-left: 3px solid {T['accent']} !important;
    border-radius: 0 6px 6px 0 !important;
    display: block !important;
  }}

  .step-label {{
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 2.2rem 0 0.75rem 0;
    font-family: 'DM Sans', sans-serif;
  }}
  .step-num {{
    width: 26px;
    height: 26px;
    border-radius: 50%;
    background: {T['accent']};
    color: #ffffff;
    font-size: 0.68rem;
    font-weight: 900;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    letter-spacing: 0;
    box-shadow: 0 2px 8px {T['accent']}55;
  }}
  .step-title {{
    font-size: 0.82rem;
    font-weight: 800;
    letter-spacing: 0.07em;
    text-transform: uppercase;
    color: {T['text']};
  }}
  .step-line {{
    flex: 1;
    height: 1px;
    background: linear-gradient(90deg, {T['border2']} 0%, transparent 100%);
  }}

  .ai-hint {{
    display: flex;
    align-items: center;
    gap: 9px;
    background: {T['accent_light']};
    border: 1px solid {T['accent']}55;
    border-radius: 10px;
    padding: 9px 14px;
    font-size: 0.78rem;
    color: {T['text2']};
    margin: 1.8rem 0 0.6rem 0;
    font-family: 'DM Sans', sans-serif;
    line-height: 1.4;
  }}
  .ai-hint-icon {{ font-size: 1rem; flex-shrink: 0; }}
  .ai-hint strong {{ color: {T['accent']}; font-weight: 700; }}

  .modifica-hint {{
    display: flex;
    align-items: flex-start;
    gap: 10px;
    background: {T['bg2']};
    border: 1px solid {T['border']};
    border-left: 3px solid {T['accent']};
    border-radius: 10px;
    padding: 10px 14px;
    margin-bottom: 0.75rem;
    font-size: 0.8rem;
    color: {T['text2']};
    font-family: 'DM Sans', sans-serif;
    line-height: 1.5;
  }}
  .modifica-hint-icon {{ font-size: 1rem; flex-shrink: 0; margin-top: 1px; }}
  .modifica-hint strong {{ color: {T['text']}; font-weight: 700; }}

  .personalizza-wrap [data-testid="stExpander"] {{
    border: 1.5px solid {T['accent']}44 !important;
    border-radius: 14px !important;
    background: {T['card']} !important;
    box-shadow: 0 2px 16px {T['accent']}0f !important;
  }}
  .personalizza-wrap [data-testid="stExpander"] summary {{
    background: {T['accent_light']} !important;
    color: {T['text']} !important;
    font-weight: 700 !important;
    font-size: 0.92rem !important;
    padding: 1rem 1.2rem !important;
  }}
  .personalizza-wrap [data-testid="stExpander"] summary:hover {{
    background: {T['accent_light']} !important;
    filter: brightness(0.96);
  }}
  .personalizza-wrap [data-testid="stExpander"] summary svg {{
    color: {T['accent']} !important;
    fill: {T['accent']} !important;
  }}
  .personalizza-wrap [data-testid="stExpander"] > div > div {{
    padding: 1rem 1.2rem 1.2rem !important;
  }}

  .genera-section {{
    margin-top: 2.2rem;
    margin-bottom: 0.5rem;
  }}

  .genera-hint {{
    text-align: center;
    font-size: 0.73rem;
    color: {T['muted']};
    margin-top: 0.6rem;
    font-family: 'DM Sans', sans-serif;
    letter-spacing: 0.02em;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 5px;
  }}

  .section-label {{
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: {T['muted']};
    margin: 1.2rem 0 0.5rem 0;
    padding-bottom: 0.3rem;
    border-bottom: 1px solid {T['border']};
  }}

  .hint {{
    font-size: 0.78rem;
    color: {T['muted']};
    margin-top: 4px;
    line-height: 1.4;
  }}

  .stSelectSlider [data-testid="stMarkdownContainer"] p {{
    color: {T['text']} !important;
    font-size: 0.88rem !important;
  }}
  .stSlider [data-baseweb="slider"] [role="slider"] {{
    background: {T['accent']} !important;
    border-color: {T['accent']} !important;
  }}
  .stSlider [data-baseweb="slider"] div[data-testid="stTickBar"] {{
    color: {T['muted']} !important;
  }}
  .stSlider label p {{
    color: {T['text2']} !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.01em;
    text-transform: uppercase;
  }}
  .stSlider [data-baseweb="slider"] [data-testid="stSliderThumbValue"] {{
    color: {T['text']} !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
  }}

  .stAlert {{
    border-radius: 10px !important;
    border: none !important;
  }}
  .stAlert p,
  .stAlert span,
  .stAlert div,
  [data-testid="stAlert"] p,
  [data-testid="stAlert"] span,
  [data-testid="stAlert"] div {{
      color: #1a1915 !important;
      opacity: 1 !important;
  }}

  .stProgress > div > div {{
    background: {T['accent']} !important;
    border-radius: 100px !important;
  }}
  .stProgress > div {{
    background: {T['border']} !important;
    border-radius: 100px !important;
    height: 6px !important;
  }}

  .stSubheader {{
    font-family: 'DM Sans', sans-serif !important;
    font-size: 1.15rem !important;
    font-weight: 700 !important;
    color: {T['text']} !important;
  }}

  .status-bar {{
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 14px;
    background: {T['card2']};
    border: 1px solid {T['border']};
    border-radius: 8px;
    font-size: 0.78rem;
    color: {T['muted']};
    margin-top: 0.5rem;
    font-family: 'DM Sans', sans-serif;
  }}
  .status-bar .dot {{
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: {T['success']};
    flex-shrink: 0;
  }}
  .status-bar strong {{
    color: {T['text2']};
    font-weight: 600;
  }}

  .pdf-preview-wrap {{
    margin-top: 1rem;
    border: 1px solid {T['border']};
    border-radius: 14px;
    overflow: hidden;
    box-shadow: {T['shadow_md']};
    background: {T['card2']};
  }}

  .top-bar {{
    display: flex;
    align-items: center;
    justify-content: flex-start;
    gap: 0.75rem;
    margin-bottom: 1.2rem;
  }}
  .top-bar-hint {{
    display: none;
  }}
  @media (max-width: 640px) {{
    .top-bar-hint {{
      display: inline-flex;
      align-items: center;
      gap: 5px;
      background: {T['accent_light']};
      border: 1px solid {T['accent']};
      border-radius: 20px;
      padding: 5px 12px;
      font-size: 0.72rem;
      color: {T['accent']};
      font-weight: 600;
      white-space: nowrap;
    }}
  }}

  .fab-link {{
    position: fixed;
    top: 4.5rem;
    right: 1.5rem;
    z-index: 9999;
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: {T['accent']};
    color: #ffffff !important;
    text-decoration: none !important;
    border-radius: 50px;
    padding: 10px 18px;
    font-family: 'DM Sans', sans-serif;
    font-size: 0.84rem;
    font-weight: 700;
    box-shadow: 0 4px 18px rgba(217,119,6,0.40);
    transition: transform 0.15s ease, filter 0.15s ease;
    white-space: nowrap;
  }}
  .fab-link:hover {{
    transform: translateY(-2px);
    filter: brightness(1.1);
    color: #ffffff !important;
  }}
  @media (max-width: 640px) {{
    .fab-link {{
      top: 4rem;
      right: 0.8rem;
      padding: 8px 14px;
      font-size: 0.78rem;
    }}
  }}

  .disclaimer {{
    display: flex;
    align-items: flex-start;
    gap: 8px;
    padding: 8px 12px;
    background: {T['card2']};
    border: 1px solid {T['border']};
    border-left: 3px solid {T['muted']};
    border-radius: 8px;
    font-size: 0.74rem;
    color: {T['muted']};
    font-family: 'DM Sans', sans-serif;
    line-height: 1.45;
    margin-bottom: 1rem;
  }}
  .disclaimer-icon {{ flex-shrink: 0; font-size: 0.9rem; margin-top: 1px; }}

  .app-footer {{
    text-align: center;
    font-size: 0.72rem;
    color: {T['muted']};
    font-family: 'DM Sans', sans-serif;
    margin-top: 3rem;
    padding-top: 1.2rem;
    border-top: 1px solid {T['border']};
    line-height: 1.6;
  }}

  .user-pill {{
    display: flex;
    align-items: center;
    gap: 10px;
    background: #1e1d1b;
    border: 1px solid #2e2d28;
    border-radius: 12px;
    padding: 10px 14px;
    margin-top: 0.5rem;
  }}
  .user-avatar {{
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: linear-gradient(135deg, #D97706, #FF8C00);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.85rem;
    font-weight: 800;
    color: white;
    flex-shrink: 0;
    font-family: 'DM Sans', sans-serif;
  }}
  .user-info {{
    flex: 1;
    min-width: 0;
  }}
  .user-email {{
    font-size: 0.78rem;
    font-weight: 600;
    color: #e8e6e0 !important;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    font-family: 'DM Sans', sans-serif;
  }}
  .user-role {{
    font-size: 0.65rem;
    color: #6b6960 !important;
    font-family: 'DM Sans', sans-serif;
    margin-top: 1px;
  }}

  .monthly-bar {{
    background: #1e1d1b;
    border: 1px solid #2e2d28;
    border-radius: 10px;
    padding: 10px 14px;
    margin-bottom: 0.5rem;
    font-family: 'DM Sans', sans-serif;
  }}
  .monthly-bar-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 6px;
  }}
  .monthly-bar-label {{
    font-size: 0.72rem;
    font-weight: 700;
    color: #8a8880 !important;
    text-transform: uppercase;
    letter-spacing: 0.07em;
  }}
  .monthly-bar-count {{
    font-size: 0.78rem;
    font-weight: 800;
    color: #e8e6e0 !important;
  }}
  .monthly-bar-count.limit-near {{ color: #F59E0B !important; }}
  .monthly-bar-count.limit-reached {{ color: #EF4444 !important; }}
  .monthly-progress {{
    height: 5px;
    background: #2e2d28;
    border-radius: 100px;
    overflow: hidden;
  }}
  .monthly-progress-fill {{
    height: 100%;
    border-radius: 100px;
    transition: width 0.4s ease;
  }}

  @media (max-width: 640px) {{
    .block-container {{
      padding: 4.5rem 1rem 3rem !important;
    }}
    .hero-title {{ font-size: 56px !important; }}
    .hero-sub {{ font-size: 0.95rem !important; }}
    .hero-wrap {{ margin-bottom: 1.5rem; padding-bottom: 1.2rem; }}
    .top-bar {{
      justify-content: center;
      gap: 0.5rem;
    }}
    .stTextInput input,
    .stNumberInput input {{
      font-size: 1rem !important;
      padding: 14px 16px !important;
      min-height: 52px !important;
      height: 52px !important;
      line-height: 1.4 !important;
      box-sizing: border-box !important;
    }}
    .stTextInput > div > div {{
      min-height: 52px !important;
    }}
    .stTextInput input::placeholder,
    .stNumberInput input::placeholder {{
      font-size: 1rem !important;
      opacity: 1 !important;
    }}
    .stSelectbox [data-baseweb="select"] > div:first-child {{
      padding: 12px 14px !important;
      min-height: 50px !important;
      height: auto !important;
    }}
    .stSelectbox [data-baseweb="select"] span,
    .stSelectbox [data-baseweb="select"] div {{
      font-size: 0.95rem !important;
      white-space: nowrap !important;
      overflow: hidden !important;
      text-overflow: ellipsis !important;
    }}
    [data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] > div:first-child {{
      min-height: 48px !important;
      padding: 10px 12px !important;
    }}
    [data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] span {{
      font-size: 0.85rem !important;
      color: #f5f3ed !important;
    }}
    .stTextArea textarea {{
      font-size: 0.95rem !important;
    }}
    .stButton button {{
      min-height: 48px !important;
      font-size: 1rem !important;
    }}
    [data-testid="stSidebar"] .block-container {{
      padding: 1rem !important;
    }}
    .stDownloadButton button {{
      width: 100% !important;
      min-height: 48px !important;
    }}
  }}

  @media (min-width: 641px) and (max-width: 1024px) {{
    .block-container {{
      padding: 1.5rem 1.5rem 3rem !important;
      max-width: 900px !important;
    }}
  }}

  [data-testid="stSidebar"] .stButton > button,
  [data-testid="stSidebar"] .stButton > button[kind="secondary"],
  [data-testid="stSidebar"] button[data-testid="baseButton-secondary"],
  [data-testid="stSidebar"] .stDownloadButton button,
  [data-testid="stSidebar"] [data-testid="stDownloadButton"] button {{
    background: #1e1d1b !important;
    color: #e8e6e0 !important;
    border: 1.5px solid #3d3c36 !important;
    border-radius: 8px !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    box-shadow: none !important;
    transform: none !important;
    padding: 8px 14px !important;
    min-height: 36px !important;
    width: 100% !important;
  }}
  [data-testid="stSidebar"] .stButton > button:hover,
  [data-testid="stSidebar"] .stButton > button[kind="secondary"]:hover,
  [data-testid="stSidebar"] button[data-testid="baseButton-secondary"]:hover,
  [data-testid="stSidebar"] .stDownloadButton button:hover,
  [data-testid="stSidebar"] [data-testid="stDownloadButton"] button:hover {{
    background: #2a2926 !important;
    border-color: #D97706 !important;
    color: #f5f3ed !important;
    transform: none !important;
    box-shadow: none !important;
  }}

  [data-testid="stSidebar"] [data-testid="stExpander"] {{
    background: #1e1d1b !important;
    border: 1px solid #2e2d28 !important;
    border-radius: 10px !important;
  }}
  [data-testid="stSidebar"] [data-testid="stExpander"] summary {{
    background: #1e1d1b !important;
    color: #c8c6bc !important;
    font-size: 0.82rem !important;
    padding: 0.7rem 1rem !important;
  }}
  [data-testid="stSidebar"] [data-testid="stExpander"] summary:hover {{
    background: #2a2926 !important;
    color: #f5f3ed !important;
  }}
  [data-testid="stSidebar"] [data-testid="stExpander"] > div > div {{
    background: #1e1d1b !important;
    padding: 0.4rem 1rem 0.8rem !important;
  }}
  [data-testid="stSidebar"] [data-testid="stExpander"] p,
  [data-testid="stSidebar"] [data-testid="stExpander"] span {{
    color: #c8c6bc !important;
  }}

  [data-testid="stSidebar"] [data-testid="stExpander"] .stButton > button,
  [data-testid="stSidebar"] [data-testid="stExpander"] div.stButton > button,
  [data-testid="stSidebar"] [data-testid="stExpander"] button[kind="secondary"],
  [data-testid="stSidebar"] [data-testid="stExpander"] button {{
    background: #2a2926 !important;
    background-color: #2a2926 !important;
    color: #c8c6bc !important;
    border: 1px solid #3a3834 !important;
    border-radius: 8px !important;
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    padding: 5px 12px !important;
    min-height: unset !important;
    box-shadow: none !important;
    transition: background 0.15s, border-color 0.15s, color 0.15s !important;
    width: 100% !important;
  }}
  [data-testid="stSidebar"] [data-testid="stExpander"] .stButton > button:hover,
  [data-testid="stSidebar"] [data-testid="stExpander"] div.stButton > button:hover {{
    background: #353330 !important;
    background-color: #353330 !important;
    border-color: {T['accent']} !important;
    color: {T['accent']} !important;
    box-shadow: none !important;
    transform: none !important;
  }}
  [data-testid="stSidebar"] [data-testid="stExpander"] .elimina-btn .stButton > button,
  [data-testid="stSidebar"] [data-testid="stExpander"] .elimina-btn button {{
    background: #1e1008 !important;
    background-color: #1e1008 !important;
    border-color: #5c2222 !important;
    color: #f87171 !important;
  }}
  [data-testid="stSidebar"] [data-testid="stExpander"] .elimina-btn .stButton > button:hover,
  [data-testid="stSidebar"] [data-testid="stExpander"] .elimina-btn button:hover {{
    background: #2a0f0f !important;
    background-color: #2a0f0f !important;
    border-color: #f87171 !important;
    color: #fca5a5 !important;
  }}
  [data-testid="stSidebar"] [data-testid="stExpander"] .stella-btn .stButton > button,
  [data-testid="stSidebar"] [data-testid="stExpander"] .stella-btn button {{
    background: #1e1d1b !important;
    background-color: #1e1d1b !important;
    border-color: #4a4020 !important;
    color: #9a8a50 !important;
    font-size: 1rem !important;
    padding: 3px 8px !important;
    width: auto !important;
  }}
  [data-testid="stSidebar"] [data-testid="stExpander"] .stella-btn-on .stButton > button,
  [data-testid="stSidebar"] [data-testid="stExpander"] .stella-btn-on button {{
    background: #2a2010 !important;
    background-color: #2a2010 !important;
    border-color: {T['accent']} !important;
    color: #F59E0B !important;
    width: auto !important;
  }}

  [data-testid="stSidebar"] .logout-btn-wrap .stButton > button,
  [data-testid="stSidebar"] .logout-btn-wrap button {{
    background: transparent !important;
    color: #f87171 !important;
    border: 1px solid #5c2222 !important;
    border-radius: 8px !important;
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    padding: 6px 14px !important;
    width: auto !important;
    min-height: unset !important;
    box-shadow: none !important;
  }}
  [data-testid="stSidebar"] .logout-btn-wrap .stButton > button:hover,
  [data-testid="stSidebar"] .logout-btn-wrap button:hover {{
    background: #2a0f0f !important;
    border-color: #f87171 !important;
    color: #fca5a5 !important;
    box-shadow: none !important;
    transform: none !important;
  }}

  @keyframes tooltipSlideIn {{
    0%   {{ opacity: 0; transform: translateX(-12px); }}
    15%  {{ opacity: 1; transform: translateX(4px); }}
    25%  {{ opacity: 1; transform: translateX(0); }}
    75%  {{ opacity: 1; transform: translateX(0); }}
    90%  {{ opacity: 0; transform: translateX(-8px); }}
    100% {{ opacity: 0; transform: translateX(-8px); }}
  }}
  .sidebar-tooltip {{
    position: fixed;
    top: 0.9rem;
    left: 3.8rem;
    z-index: 9998;
    display: flex;
    align-items: center;
    gap: 7px;
    background: {T['accent']};
    color: #ffffff;
    font-family: 'DM Sans', sans-serif;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.02em;
    padding: 7px 13px 7px 10px;
    border-radius: 20px;
    box-shadow: 0 4px 18px {T['accent']}55;
    pointer-events: none;
    white-space: nowrap;
    animation: tooltipSlideIn 4.5s ease forwards;
  }}
  .sidebar-tooltip::before {{
    content: '';
    position: absolute;
    left: -6px;
    top: 50%;
    transform: translateY(-50%);
    border-width: 5px 6px 5px 0;
    border-style: solid;
    border-color: transparent {T['accent']} transparent transparent;
  }}
</style>
""", unsafe_allow_html=True)

# ── FEEDBACK BUTTON ──────────────────────────────────────────────────────────────
st.markdown(f"""
<a class="fab-link" href="{FEEDBACK_FORM_URL}" target="_blank" rel="noopener noreferrer"
   onclick="window.open(this.href,'_blank','noopener,noreferrer'); return false;">
  💬 &nbsp; Feedback & Bug
</a>
""", unsafe_allow_html=True)

# ── SIDEBAR ──────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-title">Impostazioni</div>', unsafe_allow_html=True)

    st.markdown('<div class="sidebar-label">Classe</div>', unsafe_allow_html=True)
    st.caption("Questa scelta calibra lessico, complessità e riferimenti teorici degli esercizi.")
    difficolta = st.selectbox("livello", SCUOLE, index=0, label_visibility="collapsed")

    st.markdown('<div class="sidebar-label" style="margin-top:1rem;">Opzioni</div>', unsafe_allow_html=True)
    bes_dsa = st.checkbox(
        "Genera versione ridotta (sostegno/certificazioni)",
        value=False,
        help="Verrà generato un secondo file identico ma con una percentuale di esercizi in meno."
    )
    perc_ridotta = None
    if bes_dsa:
        perc_ridotta = st.select_slider(
            "Esercizi da rimuovere",
            help="Es. 20% = verranno eliminati circa 1 esercizio ogni 5, partendo dai più complessi",
            options=[10, 20, 30],
            value=20,
            format_func=lambda x: f"-{x}%",
        )
    doppia_fila = st.checkbox("Genera Versione A e B (due varianti)", value=False)
    genera_soluzioni = st.checkbox(
        "Genera soluzioni della verifica",
        value=False,
        help="Verrà generato un documento separato con le soluzioni complete."
    )
    bes_dsa_b = False
    if bes_dsa and doppia_fila:
        bes_dsa_b = st.checkbox(
            "Genera versione ridotta anche per Fila B",
            value=False,
        )

    esercizio_multidisciplinare = False
    materia2_scelta  = None
    difficolta_multi = None

    st.markdown('<div class="sidebar-label" style="margin-top:1rem;">Punteggi</div>', unsafe_allow_html=True)
    mostra_punteggi = st.checkbox("Mostra punteggio per esercizio", value=False)
    con_griglia     = st.checkbox("Includi griglia dei punteggi", value=False)
    punti_totali    = st.number_input("Punti totali", min_value=10, max_value=200, value=100, step=5,
                                      disabled=not mostra_punteggi)

    st.markdown('<div class="sidebar-label" style="margin-top:1rem;">Modello AI</div>', unsafe_allow_html=True)
    if _is_admin:
        _sel_modello = st.selectbox(
            "modello",
            list(MODELLI_DISPONIBILI.keys()),
            label_visibility="collapsed"
        )
        modello_id = MODELLI_DISPONIBILI[_sel_modello]["id"]
    else:
        _nomi_display = []
        for _k, _v in MODELLI_DISPONIBILI.items():
            if _v["pro"]:
                _nomi_display.append(_k + "  🔒")
            else:
                _nomi_display.append(_k)
        _sel_display = st.selectbox(
            "modello",
            _nomi_display,
            index=0,
            label_visibility="collapsed"
        )
        _sel_raw = _sel_display.replace("  🔒", "")
        _info    = MODELLI_DISPONIBILI[_sel_raw]
        if _info["pro"]:
            st.markdown(
                f'<div style="font-size:0.74rem;color:{T["muted"]};padding:4px 0 2px 2px;'
                f'font-family:DM Sans,sans-serif;">🔒 Disponibile solo per gli amministratori.</div>',
                unsafe_allow_html=True
            )
            modello_id = MODELLI_DISPONIBILI["⚡ Flash 2.5 Lite (velocissimo)"]["id"]
        else:
            modello_id = _info["id"]

    st.markdown('<div class="sidebar-label" style="margin-top:1rem;">Aspetto</div>', unsafe_allow_html=True)
    tema_sel = st.radio(
        "tema",
        ["☀️ Chiaro", "🌙 Scuro"],
        index=0 if st.session_state.theme == "light" else 1,
        horizontal=True,
        label_visibility="collapsed"
    )
    new_theme = "light" if "Chiaro" in tema_sel else "dark"
    if new_theme != st.session_state.theme:
        st.session_state.theme = new_theme
        st.rerun()

    # ── CONTATORE MENSILE ─────────────────────────────────────────────────────
    st.markdown('<div class="sidebar-label" style="margin-top:1.5rem;">Utilizzo mensile</div>', unsafe_allow_html=True)
    _perc_uso = min(100, int(_verifiche_mese_count / LIMITE_MENSILE * 100))
    _color_bar = "#EF4444" if _limite_raggiunto else ("#F59E0B" if _perc_uso >= 70 else "#10B981")
    _count_class = "limit-reached" if _limite_raggiunto else ("limit-near" if _perc_uso >= 70 else "")
    _gg_reset, _hh_reset = _giorni_al_reset()
    if _gg_reset == 0:
        _reset_str = f"Reset tra {_hh_reset}h"
    elif _gg_reset == 1:
        _reset_str = f"Reset domani"
    else:
        _reset_str = f"Reset tra {_gg_reset}gg"
    st.markdown(f"""
    <div class="monthly-bar">
      <div class="monthly-bar-header">
        <span class="monthly-bar-label">Verifiche questo mese</span>
        <span class="monthly-bar-count {_count_class}">{_verifiche_mese_count} / {LIMITE_MENSILE}</span>
      </div>
      <div class="monthly-progress">
        <div class="monthly-progress-fill" style="width:{_perc_uso}%;background:{_color_bar};"></div>
      </div>
      <div style="text-align:right;font-size:0.68rem;color:#6b6960;margin-top:4px;font-family:'DM Sans',sans-serif;">
        🔄 {_reset_str}
      </div>
    </div>
    """, unsafe_allow_html=True)
    if _limite_raggiunto:
        st.warning(f"Limite mensile raggiunto ({LIMITE_MENSILE} verifiche). {_reset_str}.")

    # ── STORICO VERIFICHE ─────────────────────────────────────────────────────
    st.markdown('<div class="sidebar-label" style="margin-top:1rem;">Le mie verifiche</div>', unsafe_allow_html=True)

    _refresh_key = st.session_state._storico_refresh
    _page_size   = 5
    _storico_limit = st.session_state._storico_page * _page_size
    try:
        storico = supabase_admin.table("verifiche_storico")\
            .select("id, materia, argomento, created_at, latex_a, latex_b, latex_r, scuola")\
            .eq("user_id", st.session_state.utente.id)\
            .is_("deleted_at", "null")\
            .order("created_at", desc=True)\
            .limit(_storico_limit + 1)\
            .execute()

        if storico.data:
            _ha_altri = len(storico.data) > _storico_limit
            dati_pagina = storico.data[:_storico_limit]

            _pref = st.session_state._preferiti
            def _sort_key(v):
                return (0 if v['id'] in _pref else 1, v['created_at'])
            dati_ordinati = sorted(dati_pagina, key=_sort_key)

            for v in dati_ordinati:
                data_str = v['created_at'][:10]
                is_pref  = v['id'] in _pref
                star_ico = "★" if is_pref else "☆"
                star_label_prefix = "⭐ " if is_pref else ""
                label = f"{star_label_prefix}{v['materia']} — {v['argomento'][:20]}{'...' if len(v['argomento'])>20 else ''}"
                with st.expander(f"{label} ({data_str})"):
                    if v.get('scuola'):
                        st.caption(f"{v['scuola'][:35]}")

                    _col_star, _col_spacer = st.columns([1, 3])
                    with _col_star:
                        st.markdown(f'<div class="{"stella-btn-on" if is_pref else "stella-btn"}">', unsafe_allow_html=True)
                        if st.button(star_ico, key=f"star_{v['id']}_{_refresh_key}",
                                     help="Aggiungi/rimuovi dai preferiti"):
                            if v['id'] in st.session_state._preferiti:
                                st.session_state._preferiti.discard(v['id'])
                            else:
                                st.session_state._preferiti.add(v['id'])
                            st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)

                    if v.get('latex_a'):
                        if st.button("♻ Ricarica Fila A", key=f"reload_a_{v['id']}_{_refresh_key}", use_container_width=True):
                            st.session_state.verifiche['A']['latex'] = v['latex_a']
                            pdf, _ = compila_pdf(v['latex_a'])
                            if pdf:
                                st.session_state.verifiche['A']['pdf'] = pdf
                                st.session_state.verifiche['A']['preview'] = True
                            st.rerun()
                    if v.get('latex_b'):
                        if st.button("♻ Ricarica Fila B", key=f"reload_b_{v['id']}_{_refresh_key}", use_container_width=True):
                            st.session_state.verifiche['B']['latex'] = v['latex_b']
                            pdf, _ = compila_pdf(v['latex_b'])
                            if pdf:
                                st.session_state.verifiche['B']['pdf'] = pdf
                                st.session_state.verifiche['B']['preview'] = True
                            st.rerun()
                    st.markdown('<div class="elimina-btn">', unsafe_allow_html=True)
                    if st.button("Elimina", key=f"del_{v['id']}_{_refresh_key}",
                                 use_container_width=True,
                                 help="Rimuovi questa verifica dallo storico"):
                        try:
                            from datetime import datetime, timezone
                            supabase_admin.table("verifiche_storico")\
                                .update({"deleted_at": datetime.now(timezone.utc).isoformat()})\
                                .eq("id", v['id'])\
                                .execute()
                            st.session_state._preferiti.discard(v['id'])
                            st.session_state._storico_refresh += 1
                            st.toast("Verifica rimossa dallo storico.", icon="🗑️")
                            st.rerun()
                        except Exception as del_err:
                            st.error(f"Errore: {del_err}")
                    st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.caption("Nessuna verifica salvata ancora.")

        if storico.data and _ha_altri:
            st.markdown('<div style="margin-top:0.5rem;">', unsafe_allow_html=True)
            if st.button("Carica altre verifiche", key="storico_load_more", use_container_width=True):
                st.session_state._storico_page += 1
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        elif storico.data and st.session_state._storico_page > 1:
            st.caption(f"Tutte le {len(dati_pagina)} verifiche caricate.")

    except Exception as e:
        st.caption("Storico non disponibile.")

    # ── USER PILL + LOGOUT ────────────────────────────────────────────────────
    st.markdown("---")
    email_utente = st.session_state.utente.email or ""
    iniziale = email_utente[0].upper() if email_utente else "?"
    st.markdown(f"""
    <div class="user-pill">
      <div class="user-avatar">{iniziale}</div>
      <div class="user-info">
        <div class="user-email">{email_utente}</div>
        <div class="user-role">Docente · Piano gratuito</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div style="height:0.5rem;"></div>', unsafe_allow_html=True)
    st.markdown('<div class="logout-btn-wrap">', unsafe_allow_html=True)
    if st.button("↩ Esci dall'account", key="logout_btn", use_container_width=False):
        supabase.auth.sign_out()
        st.session_state.utente = None
        st.session_state.pop("_sb_access_token", None)
        st.session_state.pop("_sb_refresh_token", None)
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ── TOPBAR ───────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="top-bar">
  <div class="top-bar-hint">
    ← Apri le impostazioni per configurare classe, opzioni e modello AI
  </div>
</div>
""", unsafe_allow_html=True)

# ── HEADER ───────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="hero-wrap">
  <div class="hero-left">
    <h1 class="hero-title"><span class="hero-icon">{APP_ICON}</span> Verific<span class="hero-ai">AI</span></h1>
    <p class="hero-sub">{APP_TAGLINE}</p>
    <span class="hero-beta">Versione Beta</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ── ONBOARDING ────────────────────────────────────────────────────────────────────
if not st.session_state._onboarding_done:
    if st.query_params.get("_ob") == "done":
        st.session_state._onboarding_done = True
        st.query_params.pop("_ob", None)
        st.rerun()

    _c_accent       = T['accent']
    _c_text         = T['text']
    _c_text2        = T['text2']
    _c_bg2          = T['bg2']
    _c_border       = T['border']
    _c_card         = T['card']
    _c_accent_light = T['accent_light']
    _c_muted        = T['muted']

    st.markdown(
        f'<div style="background:linear-gradient(135deg,{_c_accent_light} 0%,{_c_card} 100%);'
        f'border:1.5px solid {_c_accent};border-radius:14px;'
        f'padding:1.1rem 1.4rem 0.8rem 1.4rem;margin-bottom:0.8rem;font-family:DM Sans,sans-serif;">'
        f'<div style="display:flex;align-items:flex-start;gap:12px;">'
        f'<div style="flex:1;">'
        f'<div style="font-size:0.9rem;font-weight:800;color:{_c_text};margin-bottom:0.7rem;">Come iniziare</div>'
        f'<div style="display:flex;align-items:center;gap:8px;padding:0.45rem 0.75rem;margin-bottom:0.5rem;'
        f'background:{_c_bg2};border-radius:8px;border-left:3px solid {_c_accent};">'
        f'<span>⚙️</span>'
        f'<div style="font-size:0.8rem;color:{_c_text2};">Prima di tutto: apri '
        f'<strong style="color:{_c_text};">☰ Impostazioni</strong> in alto a sinistra '
        f'per scegliere classe e impostazioni</div>'
        f'</div>'
        f'<div style="display:flex;background:{_c_bg2};border:1px solid {_c_border};border-radius:10px;overflow:hidden;margin-bottom:0.75rem;">'
        f'<div style="flex:1;padding:0.6rem 0.85rem;border-right:1px solid {_c_border};">'
        f'<div style="font-size:0.65rem;font-weight:800;color:{_c_accent};text-transform:uppercase;letter-spacing:0.06em;margin-bottom:3px;">01 · Materia</div>'
        f'<div style="font-size:0.76rem;color:{_c_text2};">Scegli la materia</div>'
        f'</div>'
        f'<div style="flex:1;padding:0.6rem 0.85rem;border-right:1px solid {_c_border};">'
        f'<div style="font-size:0.65rem;font-weight:800;color:{_c_accent};text-transform:uppercase;letter-spacing:0.06em;margin-bottom:3px;">02 · Argomento</div>'
        f'<div style="font-size:0.76rem;color:{_c_text2};">Scrivi l\'argomento</div>'
        f'</div>'
        f'<div style="flex:1;padding:0.6rem 0.85rem;">'
        f'<div style="font-size:0.65rem;font-weight:800;color:{_c_accent};text-transform:uppercase;letter-spacing:0.06em;margin-bottom:3px;">03 · Personalizza</div>'
        f'<div style="font-size:0.76rem;color:{_c_text2};">Opzioni avanzate (facoltativo)</div>'
        f'</div>'
        f'</div>'
        f'<div style="text-align:right;">'
        f'<a href="?_ob=done" style="font-size:0.75rem;color:{_c_muted};'
        f'text-decoration:underline;text-underline-offset:2px;cursor:pointer;'
        f'font-family:DM Sans,sans-serif;font-weight:500;">'
        f'Ho capito, non mostrare più →</a>'
        f'</div>'
        f'</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        f'<div style="display:flex;align-items:flex-start;gap:8px;padding:0.6rem 0.9rem;'
        f'margin-bottom:1.2rem;background:{_c_bg2};border-radius:8px;border:1px solid {_c_border};">'
        f'<span style="font-size:0.75rem;color:{_c_muted};line-height:1.45;">'
        f'Le verifiche generate dall\'AI sono <strong style="color:{_c_text2};">suggerimenti didattici</strong>. '
        f'Controlla sempre contenuti e punteggi prima di distribuirle agli studenti.'
        f'</span>'
        f'</div>',
        unsafe_allow_html=True
    )

# ── STEP 1 — MATERIA ─────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="step-label">
  <span class="step-num">01</span>
  <span class="step-title">Materia</span>
  <span class="step-line"></span>
</div>
""", unsafe_allow_html=True)
_materie_select = MATERIE + ["✏️ Altra materia..."]
_materia_sel = st.selectbox("Materia", _materie_select, index=0, label_visibility="collapsed")
if _materia_sel == "✏️ Altra materia...":
    materia_scelta = st.text_input("Scrivi materia:", placeholder="es. Economia Aziendale, Scienze Naturali...",
                                   key="_materia_custom_input", label_visibility="collapsed").strip() or "Matematica"
else:
    materia_scelta = _materia_sel or "Matematica"

# ── STEP 2 — ARGOMENTO ───────────────────────────────────────────────────────────
st.markdown(f"""
<div class="ai-hint">
  <span class="ai-hint-icon">💡</span>
  <span><strong>Suggerimento:</strong> più dettagli fornisci nell'argomento e nelle opzioni avanzate, più la verifica sarà precisa e su misura.</span>
</div>
<div class="step-label">
  <span class="step-num">02</span>
  <span class="step-title">Argomento della verifica</span>
  <span class="step-line"></span>
</div>
""", unsafe_allow_html=True)
argomento_area = st.text_area(
    "argomento",
    placeholder="es. Le equazioni di secondo grado\nes. La Rivoluzione Francese",
    height=100,
    label_visibility="collapsed",
    key="argomento_area"
)
argomento = argomento_area.strip()

# ── STEP 3 — PERSONALIZZA ────────────────────────────────────────────────────────
st.markdown(f"""
<div class="step-label">
  <span class="step-num">03</span>
  <span class="step-title">Personalizza</span>
  <span class="step-line"></span>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="personalizza-wrap">', unsafe_allow_html=True)
with st.expander("Personalizza la verifica"):

    st.markdown(f'<div class="expander-heading">⏱️ Tempistiche e Struttura</div>', unsafe_allow_html=True)
    _c_dur, _c_num = st.columns(2)
    with _c_dur:
        durata_scelta = st.selectbox(
            "Durata della verifica",
            ["30 min", "1 ora", "1 ora e 30 min", "2 ore"],
            index=1,
        )
    with _c_num:
        num_esercizi_totali = st.slider(
            "Numero di esercizi in verifica",
            min_value=1, max_value=15, value=4,
        )

    with st.expander("🎯 Personalizza i singoli esercizi"):
        n_custom = len(st.session_state.esercizi_custom)
        n_liberi = max(0, num_esercizi_totali - n_custom)

        if n_custom == 0:
            st.info(f"Tutti i {num_esercizi_totali} esercizi generati dall'AI.")
        elif n_custom >= num_esercizi_totali:
            st.warning(f"Totale {n_custom}/{num_esercizi_totali} raggiunto — aumenta il numero.")
        else:
            st.success(f"✅ {n_custom} specifici + {n_liberi} liberi = {num_esercizi_totali} totali")

        if st.session_state.esercizi_custom:
            to_remove = None
            for i, ex in enumerate(st.session_state.esercizi_custom):
                st.markdown(f'<div class="expander-heading">Esercizio {i+1}</div>', unsafe_allow_html=True)
                t = st.selectbox("Tipo esercizio", TIPI_ESERCIZIO,
                                 index=TIPI_ESERCIZIO.index(ex.get('tipo', 'Aperto')),
                                 key=f"tipo_{i}", label_visibility="visible")
                st.session_state.esercizi_custom[i]['tipo'] = t

                d = st.text_input("Descrizione dell'esercizio (opzionale)",
                                  value=ex.get('descrizione', ''),
                                  placeholder="es. Risolvi ax²+bx+c=0 mostrando i passaggi",
                                  key=f"desc_{i}", label_visibility="visible")
                st.session_state.esercizi_custom[i]['descrizione'] = d
                _cimg, _cdel = st.columns([3, 1])
                with _cimg:
                    st.markdown('<div class="compact-uploader">', unsafe_allow_html=True)
                    img = st.file_uploader("📎 Immagine allegata",
                                           type=['png','jpg','jpeg'],
                                           key=f"img_{i}", label_visibility="collapsed")
                    st.markdown('</div>', unsafe_allow_html=True)
                    if img: st.session_state.esercizi_custom[i]['immagine'] = img
                    if st.session_state.esercizi_custom[i].get('immagine'):
                        st.image(st.session_state.esercizi_custom[i]['immagine'], width=60)
                with _cdel:
                    st.markdown('<div style="padding-top:4px;">', unsafe_allow_html=True)
                    if st.button("🗑 Rimuovi", key=f"rm_{i}", use_container_width=True):
                        to_remove = i
                    st.markdown('</div>', unsafe_allow_html=True)
                st.markdown('<hr style="margin:0.8rem 0; opacity:0.15;">', unsafe_allow_html=True)
            if to_remove is not None:
                st.session_state.esercizi_custom.pop(to_remove); st.rerun()

        can_add = len(st.session_state.esercizi_custom) < num_esercizi_totali
        if st.button("＋ Aggiungi esercizio specifico", disabled=not can_add):
            st.session_state.esercizi_custom.append({'tipo': 'Aperto', 'descrizione': '', 'immagine': None, 'materia2': '', 'difficolta_multi': 'Media'})
            st.rerun()

    st.markdown('<div class="expander-heading" style="margin-top:1rem;">🎯 Istruzioni per l\'AI</div>', unsafe_allow_html=True)
    note_generali = st.text_area(
        "note", label_visibility="collapsed",
        placeholder=NOTE_PLACEHOLDER.get(materia_scelta, "es. Argomenti da privilegiare, tipo di esercizi..."),
        height=80
    )

    st.markdown(f'<div class="expander-heading">📂 File di riferimento</div>', unsafe_allow_html=True)
    st.markdown('<div class="compact-uploader">', unsafe_allow_html=True)
    file_ispirazione = st.file_uploader(
        "📎 Allega PDF o immagine",
        type=['pdf','png','jpg','jpeg'],
        label_visibility="collapsed"
    )
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# ── BOTTONE GENERA ────────────────────────────────────────────────────────────────
st.markdown('<div class="genera-section">', unsafe_allow_html=True)

genera_btn = st.button(
    "🚀  Genera Verifica",
    use_container_width=True,
    type="primary",
    disabled=_limite_raggiunto
)

if _limite_raggiunto:
    st.markdown(f"""
    <div style="text-align:center;font-size:0.82rem;color:#EF4444;margin-top:0.5rem;
                font-family:'DM Sans',sans-serif;font-weight:600;">
      ⛔ Limite di {LIMITE_MENSILE} verifiche mensili raggiunto. Riprova il mese prossimo.
    </div>
    """, unsafe_allow_html=True)
else:
    _files_hint = ["📄 Verifica"]
    if doppia_fila:
        _files_hint.append("📄 Versione B")
    if bes_dsa:
        _files_hint.append("📄 Ridotta A")
    if bes_dsa and doppia_fila and bes_dsa_b:
        _files_hint.append("📄 Ridotta B")
    if genera_soluzioni:
        _files_hint.append("✅ Soluzioni")
    _files_str = " · ".join(_files_hint)
    _n_files   = len(_files_hint)
    st.markdown(f"""
    <div class="genera-hint">
      <strong style="color:{T['text2']};">File richiesti ({_n_files}):</strong> {_files_str}
    </div>
    """, unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# ── LOGICA GENERAZIONE ───────────────────────────────────────────────────────────
if genera_btn and not _limite_raggiunto:
    if not argomento.strip():
        st.warning("⚠️ Inserisci l'argomento della verifica."); st.stop()
    try:
        model       = genai.GenerativeModel(modello_id)
        materia     = materia_scelta.strip() or "Matematica"
        calibrazione = CALIBRAZIONE_SCUOLA.get(difficolta, "")
        s_es, imgs_es = costruisci_prompt_esercizi(
            st.session_state.esercizi_custom, num_esercizi_totali,
            punti_totali if mostra_punteggi else 0, mostra_punteggi)

        _n_steps = 4 + (2 if doppia_fila else 0) + (1 if bes_dsa else 0) \
                   + (1 if bes_dsa and doppia_fila and bes_dsa_b else 0) \
                   + (1 if genera_soluzioni else 0)
        _step = [0]
        _prog = st.empty()

        def _avanza(testo):
            _step[0] += 1
            perc = int(min(_step[0] / _n_steps, 0.97) * 100)
            _prog.markdown(f"""
<div style="margin:0.6rem 0 1rem 0;">
  <div style="font-size:0.82rem;font-weight:600;color:{T['text2']};
              font-family:'DM Sans',sans-serif;margin-bottom:6px;">{testo}</div>
  <div style="background:{T['border']};border-radius:100px;height:8px;overflow:hidden;">
    <div style="background:linear-gradient(90deg,{T['accent']},{T['accent']}cc);
                width:{perc}%;height:100%;border-radius:100px;
                transition:width 0.4s ease;"></div>
  </div>
</div>
""", unsafe_allow_html=True)

        ris = genera_verifica(
            model=model,
            materia=materia,
            argomento=argomento,
            difficolta=difficolta,
            calibrazione=calibrazione,
            durata=durata_scelta,
            num_esercizi=num_esercizi_totali,
            punti_totali=punti_totali,
            mostra_punteggi=mostra_punteggi,
            con_griglia=con_griglia,
            doppia_fila=doppia_fila,
            bes_dsa=bes_dsa,
            perc_ridotta=perc_ridotta,
            bes_dsa_b=bes_dsa_b,
            genera_soluzioni=genera_soluzioni,
            note_generali=note_generali,
            istruzioni_esercizi=s_es,
            immagini_esercizi=imgs_es,
            file_ispirazione=file_ispirazione,
            on_progress=_avanza,
        )

        def _aggiorna(fid, dati):
            v = st.session_state.verifiche[fid]
            if dati.get('latex'):
                v['latex'] = dati['latex']
                v['latex_originale'] = dati['latex']
            if dati.get('pdf'):
                v['pdf']     = dati['pdf']
                v['pdf_ts']  = time.time()
                v['preview'] = True
            if fid == 'S' and dati.get('testo'):
                v['testo'] = dati['testo']
                v['latex'] = dati.get('latex', '')

        _aggiorna('A',  ris['A'])
        _aggiorna('B',  ris['B'])
        _aggiorna('R',  ris['R'])
        _aggiorna('RB', ris['RB'])
        _aggiorna('S',  ris['S'])

        _prog.markdown(f"""
<div style="margin:0.6rem 0 1rem 0;">
  <div style="font-size:0.82rem;font-weight:600;color:{T['success']};
              font-family:'DM Sans',sans-serif;margin-bottom:6px;">✅  Verifica pronta!</div>
  <div style="background:{T['border']};border-radius:100px;height:8px;overflow:hidden;">
    <div style="background:{T['success']};width:100%;height:100%;border-radius:100px;"></div>
  </div>
</div>
""", unsafe_allow_html=True)
        time.sleep(0.7)
        _prog.empty()

        st.session_state.last_materia   = materia
        st.session_state.last_argomento = ris['titolo']
        st.session_state.last_gen_ts    = time.time()
        st.session_state._onboarding_done = True

        try:
            supabase_admin.table("verifiche_storico").insert({
                "user_id":      st.session_state.utente.id,
                "materia":      materia,
                "argomento":    ris['titolo'],
                "scuola":       difficolta,
                "latex_a":      ris['A']['latex'] or None,
                "latex_b":      ris['B']['latex'] or None,
                "latex_r":      ris['R']['latex'] or None,
                "modello":      modello_id,
                "num_esercizi": num_esercizi_totali,
            }).execute()
            st.session_state._storico_refresh += 1
            st.toast("✅ Verifica salvata!", icon="💾")
        except Exception as e:
            st.warning(f"⚠️ Salvataggio non riuscito: {e}")

        st.rerun()

    except Exception as e:
        st.error(f"❌ Errore: {e}")

# ── OUTPUT ────────────────────────────────────────────────────────────────────────
if st.session_state.verifiche['A']['latex']:
    st.divider()
    _df  = doppia_fila   if 'doppia_fila'  in dir() else False
    _arg = st.session_state.last_argomento or (argomento if 'argomento' in dir() else 'verifica')

    attive = ['A','B'] if _df and st.session_state.verifiche['B']['latex'] else ['A']
    if st.session_state.verifiche['R']['latex']:
        attive.append('R')
    if st.session_state.verifiche['RB']['latex']:
        attive.append('RB')

    for idx, fid in enumerate(attive):
        v = st.session_state.verifiche[fid]
        if idx > 0:
            st.divider()
        with st.container():
            if fid == 'R':
                label_ver = "Verifica Ridotta (Fila A)"
            elif fid == 'RB':
                label_ver = "Verifica Ridotta (Fila B)"
            elif _df:
                label_ver = f"Versione {fid}"
            else:
                label_ver = "La tua verifica"

            st.markdown(f"""
            <div style="background:linear-gradient(135deg, {T['accent_light']} 0%, {T['card']} 100%);
                        border:2px solid {T['accent']};border-radius:16px;padding:0;
                        margin-bottom:1.8rem;overflow:hidden;
                        box-shadow:0 4px 20px {T['accent']}22;">
              <div style="background:{T['accent']};padding:1rem 1.3rem;
                          border-bottom:1px solid {T['accent']};">
                <div style="display:flex;align-items:center;gap:12px;">
                  <span style="font-size:1.8rem;">{APP_ICON}</span>
                  <div style="flex:1;">
                    <div style="font-family:'DM Sans',sans-serif;font-size:1.3rem;
                                font-weight:900;color:#ffffff;letter-spacing:-0.02em;">
                      {label_ver}
                    </div>
                    <div style="font-size:0.75rem;color:#ffffff;opacity:0.85;
                                font-weight:600;margin-top:2px;">
                      Generata con successo
                    </div>
                  </div>
                  <div style="background:#ffffff22;backdrop-filter:blur(10px);
                              border:1px solid #ffffff33;border-radius:20px;
                              padding:6px 16px;font-size:0.72rem;font-weight:700;
                              color:#ffffff;letter-spacing:0.05em;text-transform:uppercase;">
                    ✓ Pronta
                  </div>
                </div>
              </div>
              <div style="padding:1.2rem 1.3rem;background:{T['card']};">
                <div style="display:flex;align-items:flex-start;gap:10px;
                            background:{T['accent_light']};border-left:3px solid {T['accent']};
                            border-radius:8px;padding:12px 16px;">
                  <span style="font-size:1.1rem;flex-shrink:0;">⚠️</span>
                  <span style="font-size:0.82rem;color:{T['text2']};line-height:1.5;">
                    Le verifiche generate sono <strong style="color:{T['text']};">suggerimenti didattici</strong>.
                    Rivedi sempre il contenuto prima della distribuzione — il docente è responsabile del materiale finale.
                  </span>
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            if v['pdf']:
                pdf_size = _stima_dimensione(v['pdf'])
                st.download_button(
                    label=f"📄 Scarica PDF — Alta qualità ({pdf_size})",
                    data=v['pdf'],
                    file_name=f"Verifica_{_arg}_{fid}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    key=f"dl_{fid}"
                )
            else:
                if st.button("📄 Genera PDF", key=f"dlc_{fid}", use_container_width=True):
                    with st.spinner("Compilazione…"):
                        pdf, err = compila_pdf(v['latex'])
                    if pdf:
                        st.session_state.verifiche[fid]['pdf'] = pdf
                        st.session_state.verifiche[fid]['pdf_ts'] = time.time()
                        st.rerun()
                    else:
                        st.error("Errore PDF")
                        with st.expander("Log"): st.text(err)

            st.write("")

            st.markdown(f"""
            <div class="modifica-hint">
              <span>
                <strong>La verifica ti soddisfa?</strong> Scarica il PDF — oppure, se vuoi apportare correzioni
                (cambiare un esercizio, modificare i dati, variare la difficoltà, aggiungere un sottopunto…),
                apri il pannello qui sotto e descrivi nel dettaglio cosa cambiare: più sei preciso, migliore sarà il risultato.
              </span>
            </div>
            """, unsafe_allow_html=True)

            with st.expander("✏️ Modifica questa verifica", expanded=False):
                st.markdown(f"""
                <div style="font-size:0.85rem;color:{T['text2']};margin-bottom:0.8rem;line-height:1.5;">
                    Descrivi le modifiche che vuoi apportare. Esempi:<br>
                    • "Aggiungi un esercizio sulla proprietà distributiva"<br>
                    • "Rimuovi l'esercizio 3"<br>
                    • "Cambia i numeri dell'esercizio 2 con valori più piccoli"<br>
                    • "Aumenta la difficoltà dell'esercizio 4"
                </div>
                """, unsafe_allow_html=True)

                richiesta_modifica = st.text_area(
                    "Cosa vuoi modificare?",
                    height=100,
                    placeholder="es. Sostituisci l'esercizio 2 con un problema sulla velocità media",
                    key=f"modifica_input_{fid}",
                    label_visibility="collapsed"
                )

                col_mod1, col_mod2 = st.columns([1, 1])
                with col_mod1:
                    if st.button("🔄 Applica Modifiche", key=f"modifica_btn_{fid}",
                               use_container_width=True, disabled=not richiesta_modifica.strip()):
                        try:
                            with st.spinner("⏳ Modifica in corso..."):
                                model = genai.GenerativeModel(modello_id)
                                latex_modificato = modifica_verifica_con_ai(
                                    v['latex'],
                                    richiesta_modifica.strip(),
                                    model
                                )
                                latex_modificato = fix_items_environment(latex_modificato)
                                latex_modificato = rimuovi_vspace_corpo(latex_modificato)
                                if mostra_punteggi:
                                    latex_modificato = rimuovi_punti_subsection(latex_modificato)
                                    latex_modificato = riscala_punti(latex_modificato, punti_totali)
                                if con_griglia:
                                    latex_modificato = inietta_griglia(latex_modificato, punti_totali)
                                st.session_state.verifiche[fid]['latex'] = latex_modificato
                                pdf_mod, err_mod = compila_pdf(latex_modificato)
                                if pdf_mod:
                                    st.session_state.verifiche[fid]['pdf'] = pdf_mod
                                    st.session_state.verifiche[fid]['pdf_ts'] = time.time()
                                    st.session_state.verifiche[fid]['preview'] = True
                                    st.session_state.verifiche[fid]['docx'] = None
                                    st.success("✅ Modifiche applicate!")
                                    time.sleep(0.8)
                                    st.rerun()
                                else:
                                    st.error("❌ Errore nella compilazione del PDF modificato")
                                    if err_mod:
                                        with st.expander("Log errore"):
                                            st.text(err_mod)
                        except Exception as e:
                            st.error(f"❌ Errore durante la modifica: {str(e)}")

                with col_mod2:
                    ha_originale = 'latex_originale' in v and v.get('latex_originale')
                    if st.button("🗑️ Ripristina Originale", key=f"reset_mod_{fid}",
                               use_container_width=True,
                               disabled=not ha_originale,
                               help="Torna alla versione generata inizialmente"):
                        if ha_originale:
                            st.session_state.verifiche[fid]['latex'] = v['latex_originale']
                            pdf_orig, _ = compila_pdf(v['latex_originale'])
                            if pdf_orig:
                                st.session_state.verifiche[fid]['pdf'] = pdf_orig
                                st.session_state.verifiche[fid]['pdf_ts'] = time.time()
                                st.session_state.verifiche[fid]['docx'] = None
                            st.success("✅ Versione originale ripristinata!")
                            time.sleep(0.5)
                            st.rerun()

            st.write("")

            if v['docx']:
                docx_size = _stima_dimensione(v['docx'])
                st.download_button(
                    label=f"📝 Scarica File Word Modificabile ({docx_size})",
                    data=v['docx'],
                    file_name=f"Verifica_{_arg}_{fid}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                    key=f"dld_{fid}"
                )
                st.markdown(f"""
                    <div class="hint-docx" style="margin-top: -10px; margin-bottom: 15px;">
                        💡 <b>Nota:</b> La versione Word è modificabile ma ha una resa grafica inferiore.
                        I grafici complessi di funzione (TikZ/Plot) non compaiono in Word e vanno aggiunti a mano.
                    </div>
                """, unsafe_allow_html=True)
            else:
                _docx_gen_key = f"_docx_generating_{fid}"
                if st.button("📝 Genera File Word Modificabile", key=f"dldc_{fid}", use_container_width=True):
                    st.session_state[_docx_gen_key] = True
                if st.session_state.get(_docx_gen_key, False):
                    with st.spinner("⏳ Conversione Word…"):
                        db, de = latex_to_docx_via_ai(v['latex'], con_griglia=con_griglia)
                    if db:
                        st.session_state.verifiche[fid]['docx'] = db
                        st.session_state.verifiche[fid]['docx_ts'] = time.time()
                        st.session_state[_docx_gen_key] = False
                        st.rerun()
                    else:
                        st.session_state[_docx_gen_key] = False
                        st.error("Errore Word")
                        with st.expander("Log"): st.text(de)

            st.write("")

            if v['preview'] and v['pdf']:
                with st.expander("👁 Anteprima PDF", expanded=False):
                    b64 = base64.b64encode(v['pdf']).decode()
                    st.markdown(f"""
                    <iframe src="data:application/pdf;base64,{b64}#toolbar=0&navpanes=0&scrollbar=1"
                            style="width:100%;height:500px;border:none;border-radius:8px;display:block;"></iframe>
                    """, unsafe_allow_html=True)

            _spacer, _tex_col = st.columns([3, 1])
            with _tex_col:
                st.markdown('<div class="tex-btn-wrap">', unsafe_allow_html=True)
                st.download_button(
                    "⬇ Sorgente .tex",
                    data=v['latex'].encode('utf-8'),
                    file_name=f"Verifica_{_arg}_{fid}.tex",
                    mime="text/plain",
                    key=f"dl_tex_{fid}",
                    help="Scarica il sorgente LaTeX per modificarlo"
                )
                st.markdown('</div>', unsafe_allow_html=True)

# ── SOLUZIONI ────────────────────────────────────────────────────────────────────
if st.session_state.verifiche['S'].get('testo') or st.session_state.verifiche['S'].get('pdf'):
    st.divider()
    _arg_s = st.session_state.last_argomento or (argomento if 'argomento' in dir() else 'verifica')
    v_s = st.session_state.verifiche['S']
    st.markdown(f"""
    <div style="background:linear-gradient(135deg, {T['accent_light']} 0%, {T['card']} 100%);
                border:2px solid {T['success']};border-radius:16px;padding:0;
                margin-bottom:1.8rem;overflow:hidden;box-shadow:0 4px 20px {T['success']}22;">
      <div style="background:{T['success']};padding:1rem 1.3rem;">
        <div style="display:flex;align-items:center;gap:12px;">
          <span style="font-size:1.8rem;">📋</span>
          <div style="flex:1;">
            <div style="font-family:'DM Sans',sans-serif;font-size:1.3rem;font-weight:900;color:#ffffff;letter-spacing:-0.02em;">
              Soluzioni
            </div>
            <div style="font-size:0.75rem;color:#ffffff;opacity:0.85;font-weight:600;margin-top:2px;">
              Documento riservato al docente
            </div>
          </div>
          <div style="background:#ffffff22;border:1px solid #ffffff33;border-radius:20px;
                      padding:6px 16px;font-size:0.72rem;font-weight:700;color:#ffffff;
                      letter-spacing:0.05em;text-transform:uppercase;">🔒 Solo docente</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    if v_s.get('pdf'):
        st.download_button(
            label="📄 Scarica Soluzioni PDF",
            data=v_s['pdf'],
            file_name=f"Soluzioni_{_arg_s}.pdf",
            mime="application/pdf",
            use_container_width=True,
            key="dl_sol_pdf"
        )
    st.write("")
    if v_s.get('testo'):
        with st.expander("👁 Mostra soluzioni", expanded=False):
            st.markdown(v_s['testo'])
    if v_s.get('pdf') and v_s.get('preview'):
        with st.expander("👁 Anteprima PDF Soluzioni", expanded=False):
            b64_s = base64.b64encode(v_s['pdf']).decode()
            st.markdown(f"""
            <iframe src="data:application/pdf;base64,{b64_s}#toolbar=0&navpanes=0&scrollbar=1"
                    style="width:100%;height:500px;border:none;border-radius:8px;display:block;"></iframe>
            """, unsafe_allow_html=True)

# ── FOOTER ───────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="app-footer">
  ⚠️ Le verifiche generate dall'AI sono suggerimenti didattici — rivedi sempre il contenuto
  prima di distribuirlo agli studenti. Il docente è responsabile del materiale finale.<br>
  <span style="opacity:0.55;">VerificAI · Versione Beta</span>
</div>
""", unsafe_allow_html=True)

import streamlit.components.v1 as components
components.html(f"""
<style>
  body {{ margin: 0; padding: 0; background: transparent; }}
  #share-btn {{
    background: none;
    border: none;
    cursor: pointer;
    color: {T['accent']};
    font-weight: 600;
    font-size: 0.72rem;
    font-family: 'DM Sans', sans-serif;
    padding: 0;
    display: block;
    margin: 0 auto;
    text-align: center;
    width: 100%;
  }}
  #share-btn:hover {{ text-decoration: underline; }}
</style>
<button id="share-btn" onclick="copyLink()">🔗 Condividi con i colleghi</button>
<script>
function copyLink() {{
  var url = "{SHARE_URL}";
  var btn = document.getElementById("share-btn");
  var ta = document.createElement("textarea");
  ta.value = url;
  ta.style.cssText = "position:fixed;top:0;left:0;opacity:0;";
  document.body.appendChild(ta);
  ta.focus();
  ta.select();
  var ok = false;
  try {{ ok = document.execCommand("copy"); }} catch(e) {{}}
  document.body.removeChild(ta);
  if (ok) {{
    btn.innerText = "✅ Link copiato!";
    setTimeout(function() {{ btn.innerText = "🔗 Condividi con i colleghi"; }}, 2000);
  }} else {{
    btn.innerText = url;
  }}
}}
</script>
""", height=30)
