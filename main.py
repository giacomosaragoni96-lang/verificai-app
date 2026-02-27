# ── main.py — VerificAI ──────────────────────────────────────────────────────
# Orchestrazione UI con macchina a tre stati:
#   STAGE_INPUT  → configurazione + tasto Genera
#   STAGE_REVIEW → revisione esercizio per esercizio (Fila A)
#   STAGE_FINAL  → preview immagine + download di tutte le varianti
# ─────────────────────────────────────────────────────────────────────────────

import streamlit as st
import base64
import re
import os
import time
import google.generativeai as genai

from sidebar import render_sidebar
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
from auth import mostra_auth, ripristina_sessione, salva_sessione_cookie, cancella_sessione_cookie
from styles import get_css


# ── COSTANTI STAGE ────────────────────────────────────────────────────────────
STAGE_INPUT  = "INPUT"
STAGE_REVIEW = "REVIEW"
STAGE_FINAL  = "FINAL"

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title=APP_NAME,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── SUPABASE ──────────────────────────────────────────────────────────────────
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
SUPABASE_SERVICE_KEY = st.secrets["SUPABASE_SERVICE_KEY"]
supabase_admin: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# ── TEMA ──────────────────────────────────────────────────────────────────────
if "theme" not in st.session_state:
    st.session_state.theme = "light"
T = THEMES[st.session_state.theme]

# ── CONFIGURAZIONE API ────────────────────────────────────────────────────────
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    st.error("⚠️ Chiave API mancante! Crea un file .env con: GOOGLE_API_KEY=la_tua_chiave")
    st.stop()
genai.configure(api_key=API_KEY)

# ── AUTENTICAZIONE GATE ───────────────────────────────────────────────────────
if "utente" not in st.session_state:
    st.session_state.utente = None

if st.session_state.utente is None:
    ripristina_sessione(supabase)
    if st.session_state.utente is None:
        mostra_auth(supabase)
        st.stop()


# ═══════════════════════════════════════════════════════════════════════════════
#  FUNZIONI DI UTILITÀ
# ═══════════════════════════════════════════════════════════════════════════════

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
        reset = now.replace(year=now.year + 1, month=1, day=1,
                            hour=0, minute=0, second=0, microsecond=0)
    else:
        reset = now.replace(month=now.month + 1, day=1,
                            hour=0, minute=0, second=0, microsecond=0)
    delta = reset - now
    return delta.days, delta.seconds // 3600


def _stima_dimensione(data_bytes):
    if data_bytes is None:
        return "—"
    kb = len(data_bytes) / 1024
    return f"{kb:.0f} KB" if kb < 1024 else f"{kb / 1024:.1f} MB"


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
            righe.append(f"  - Esercizio {i_ex + 1}: circa {pts_per_ex[i_ex]} pt")
        righe.append(
            f"REGOLA CRITICA: la somma di TUTTI i (X pt) nei sottopunti DEVE essere "
            f"ESATTAMENTE {punti_totali} pt."
        )

    ha_primo_custom = len(esercizi_custom) > 0
    if not ha_primo_custom:
        righe.append(
            f"\nREGOLA PRIMO ESERCIZIO (Esercizio 1 — SEMPRE presente):\n"
            f"Il primo esercizio DEVE chiamarsi 'Saperi Essenziali' e coprire i concetti fondamentali.\n"
            f"NON inserire mai il simbolo (*). È obbligatorio per tutti. Livello accessibile.\n"
            f"Gli esercizi {2}–{num_totale} possono approfondire e variare."
        )

    righe.append(f"\nDETTAGLIO ESERCIZI ({num_totale} totali):")
    for i, ex in enumerate(esercizi_custom, 1):
        tipo, desc = ex.get("tipo", "Aperto"), ex.get("descrizione", "").strip()
        riga = f"- Esercizio {i} [{tipo}]" + (f": {desc}" if desc else "")
        if ex.get("immagine"):
            riga += f" — vedi immagine allegata per l'esercizio {i}"
            immagini.append({"idx": i, "data": ex["immagine"].getvalue(),
                             "mime_type": ex["immagine"].type})
        if tipo == "Scelta multipla":
            riga += " — opzioni con \\begin{enumerate}[a)] \\item ... \\end{enumerate}"
        elif tipo == "Vero/Falso":
            riga += " — $\\square$ \\textbf{V} $\\quad\\square$ \\textbf{F} (min 3 affermazioni)"
        elif tipo == "Completamento":
            riga += " — \\underline{\\hspace{3cm}} per gli spazi"
        righe.append(riga)
    if n_liberi > 0:
        start_idx = len(esercizi_custom) + 1
        righe.append(f"- Esercizi {start_idx}–{num_totale}: genera tu {n_liberi} esercizi coerenti.")
    return "\n".join(righe), immagini


# ═══════════════════════════════════════════════════════════════════════════════
#  FUNZIONI PER IL SISTEMA A BLOCCHI (STAGE_REVIEW)
# ═══════════════════════════════════════════════════════════════════════════════

def _extract_blocks(latex: str) -> tuple[str, list]:
    """
    Divide il LaTeX in preamble + lista di blocchi esercizio.
    Ogni blocco: {'title': str, 'body': str}
    """
    pattern = r"(?=\\subsection\*\{)"
    parts = re.split(pattern, latex)
    if len(parts) <= 1:
        return latex, []

    preamble = parts[0]
    blocks = []
    for raw in parts[1:]:
        m = re.match(r"\\subsection\*\{([^}]*)\}(.*)", raw, re.DOTALL)
        if m:
            body = m.group(2).rstrip()
            # Rimuovi \end{document} dall'ultimo blocco
            body = re.sub(r"\s*\\end\{document\}\s*$", "", body).rstrip()
            blocks.append({"title": m.group(1), "body": body})
    return preamble, blocks


def _reconstruct_latex(preamble: str, blocks: list) -> str:
    """Ricostruisce il LaTeX completo da preamble + lista blocchi."""
    result = preamble
    for b in blocks:
        result += f"\\subsection*{{{b['title']}}}\n{b['body']}\n\n"
    if "\\end{document}" not in result:
        result += "\n\\end{document}"
    return result


def _strip_latex_display(text: str) -> str:
    """Produce una versione leggibile del LaTeX per la preview testuale."""
    # Titoli
    text = re.sub(r"\\subsection\*?\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\section\*?\{([^}]*)\}", r"\1", text)
    # Grassetto / italico
    text = re.sub(r"\\textbf\{([^}]*)\}", r"**\1**", text)
    text = re.sub(r"\\textit\{([^}]*)\}", r"_\1_", text)
    text = re.sub(r"\\emph\{([^}]*)\}", r"_\1_", text)
    # Matematica inline → [...]
    text = re.sub(r"\$\$([^$]+)\$\$", r"[formula: \1]", text)
    text = re.sub(r"\$([^$\n]+)\$", r"[\1]", text)
    # Item etichettati e non
    text = re.sub(r"\\item\[([^\]]+)\]", r"\n    \1", text)
    text = re.sub(r"\\item", r"\n    •", text)
    # Ambienti
    text = re.sub(r"\\begin\{[^}]*\}|\\end\{[^}]*\}", "", text)
    # Spazi e hspace
    text = re.sub(r"\\[hv]space\*?\{[^}]*\}", " ", text)
    text = re.sub(r"\\underline\{([^}]*)\}", r"_\1_", text)
    # Comandi rimanenti con argomento
    text = re.sub(r"\\[a-zA-Z]+\{([^}]*)\}", r"\1", text)
    # Comandi senza argomento
    text = re.sub(r"\\[a-zA-Z]+\*?", "", text)
    # Parentesi graffe residue
    text = re.sub(r"[{}]", "", text)
    # Righe vuote eccessive
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ═══════════════════════════════════════════════════════════════════════════════
#  SESSION STATE INIT
# ═══════════════════════════════════════════════════════════════════════════════

def _vf():
    return {
        "latex": "", "pdf": None, "preview": False,
        "soluzioni_latex": "", "soluzioni_pdf": None, "docx": None,
        "pdf_ts": None, "docx_ts": None, "latex_originale": "",
    }


# Stage
if "stage" not in st.session_state:
    st.session_state.stage = STAGE_INPUT

# Verifiche
if "verifiche" not in st.session_state:
    st.session_state.verifiche = {
        "A": _vf(), "B": _vf(), "R": _vf(), "RB": _vf(),
        "S": {"latex": None, "testo": None, "pdf": None},
    }

# Review blocks (Fila A suddivisa per esercizio)
if "review_preamble" not in st.session_state:
    st.session_state.review_preamble = ""
if "review_blocks" not in st.session_state:
    st.session_state.review_blocks = []  # list of {'title': str, 'body': str}

# Parametri di generazione salvati (per ricostruzione in REVIEW / FINAL)
if "gen_params" not in st.session_state:
    st.session_state.gen_params = {}

# Preview immagini PDF (STAGE_FINAL)
if "preview_images" not in st.session_state:
    st.session_state.preview_images = []

# Misc
if "esercizi_custom" not in st.session_state:
    st.session_state.esercizi_custom = []
if "last_materia" not in st.session_state:
    st.session_state.last_materia = None
if "last_argomento" not in st.session_state:
    st.session_state.last_argomento = None
if "last_gen_ts" not in st.session_state:
    st.session_state.last_gen_ts = None
if "_storico_refresh" not in st.session_state:
    st.session_state._storico_refresh = 0
if "_preferiti" not in st.session_state:
    st.session_state._preferiti = set()
if "_storico_page" not in st.session_state:
    st.session_state._storico_page = 1
if "_onboarding_done" not in st.session_state:
    st.session_state._onboarding_done = False


# ── CONTATORI ─────────────────────────────────────────────────────────────────
_verifiche_mese_count = (
    _get_verifiche_mese(st.session_state.utente.id) if st.session_state.utente else 0
)
_is_admin = (st.session_state.utente.email in ADMIN_EMAILS) if st.session_state.utente else False
_limite_raggiunto = (not _is_admin) and (_verifiche_mese_count >= LIMITE_MENSILE)

# ── CSS + FEEDBACK ────────────────────────────────────────────────────────────
st.markdown(get_css(T), unsafe_allow_html=True)

st.markdown(f"""
<a class="fab-link" href="{FEEDBACK_FORM_URL}" target="_blank" rel="noopener noreferrer"
   onclick="window.open(this.href,'_blank','noopener,noreferrer'); return false;">
  💬 &nbsp; Feedback & Bug
</a>
""", unsafe_allow_html=True)

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
settings = render_sidebar(
    supabase_admin=supabase_admin,
    utente=st.session_state.utente,
    verifiche_mese_count=_verifiche_mese_count,
    is_admin=_is_admin,
    limite_raggiunto=_limite_raggiunto,
    T=T,
    SCUOLE=SCUOLE,
    MODELLI_DISPONIBILI=MODELLI_DISPONIBILI,
    LIMITE_MENSILE=LIMITE_MENSILE,
    giorni_al_reset_func=_giorni_al_reset,
    compila_pdf_func=compila_pdf,
    supabase_client=supabase,
    current_stage=st.session_state.stage,
)
modello_id = settings.get("modello_id", "gemini-2.5-flash-lite")

# ── TOP BAR + HERO ────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="top-bar">
  <div class="top-bar-hint">
    ← Apri le impostazioni per configurare il modello AI e le opzioni avanzate
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class="hero-wrap">
  <div class="hero-left">
    <h1 class="hero-title"><span class="hero-icon">{APP_ICON}</span> Verific<span class="hero-ai">AI</span></h1>
    <p class="hero-sub">{APP_TAGLINE}</p>
    <span class="hero-beta">Versione Beta</span>
  </div>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  STAGE INDICATOR (breadcrumb)
# ═══════════════════════════════════════════════════════════════════════════════

def _render_stage_indicator():
    stage = st.session_state.stage
    steps = [
        ("01", "Configura", STAGE_INPUT),
        ("02", "Revisione", STAGE_REVIEW),
        ("03", "Download",  STAGE_FINAL),
    ]
    items_html = ""
    for num, label, s in steps:
        if s == stage:
            color   = T["accent"]
            bg      = T["accent_light"]
            fw      = "800"
            opacity = "1"
        elif (
            (stage == STAGE_REVIEW and s == STAGE_INPUT) or
            (stage == STAGE_FINAL)
        ):
            color   = T["success"]
            bg      = T["accent_light"]
            fw      = "600"
            opacity = "0.85"
        else:
            color   = T["muted"]
            bg      = T["bg2"]
            fw      = "500"
            opacity = "0.5"

        items_html += f"""
        <div style="display:flex;align-items:center;gap:6px;opacity:{opacity};">
          <div style="background:{bg};border:1.5px solid {color};border-radius:50%;
                      width:28px;height:28px;display:flex;align-items:center;
                      justify-content:center;font-size:0.7rem;font-weight:800;
                      color:{color};flex-shrink:0;">{num}</div>
          <span style="font-size:0.8rem;font-weight:{fw};color:{color};
                       font-family:'DM Sans',sans-serif;">{label}</span>
        </div>
        """
        if num != "03":
            items_html += f"""
            <div style="flex:1;height:1.5px;background:linear-gradient(90deg,{color}44,{T['border']});
                        min-width:20px;max-width:60px;"></div>
            """

    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:8px;
                padding:0.7rem 1rem;margin-bottom:1.2rem;
                background:{T['bg2']};border:1px solid {T['border']};
                border-radius:12px;flex-wrap:wrap;">
      {items_html}
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  STAGE_INPUT — configurazione + genera
# ═══════════════════════════════════════════════════════════════════════════════

def _render_stage_input():
    # ── ONBOARDING ────────────────────────────────────────────────────────────
    if not st.session_state._onboarding_done:
        if st.query_params.get("_ob") == "done":
            st.session_state._onboarding_done = True
            st.query_params.pop("_ob", None)
            st.rerun()

        st.markdown(
            f'<div style="background:linear-gradient(135deg,{T["accent_light"]} 0%,{T["card"]} 100%);'
            f'border:1.5px solid {T["accent"]};border-radius:14px;'
            f'padding:1.1rem 1.4rem 0.8rem 1.4rem;margin-bottom:0.8rem;font-family:DM Sans,sans-serif;">'
            f'<div style="display:flex;align-items:flex-start;gap:12px;">'
            f'<div style="flex:1;">'
            f'<div style="font-size:0.9rem;font-weight:800;color:{T["text"]};margin-bottom:0.7rem;">Come iniziare</div>'
            f'<div style="display:flex;background:{T["bg2"]};border:1px solid {T["border"]};border-radius:10px;overflow:hidden;margin-bottom:0.75rem;">'
            f'<div style="flex:1;padding:0.6rem 0.85rem;border-right:1px solid {T["border"]};">'
            f'<div style="font-size:0.65rem;font-weight:800;color:{T["accent"]};text-transform:uppercase;letter-spacing:0.06em;margin-bottom:3px;">01 · Materia & Scuola</div>'
            f'<div style="font-size:0.76rem;color:{T["text2"]};">Seleziona materia e tipo di istituto</div>'
            f'</div>'
            f'<div style="flex:1;padding:0.6rem 0.85rem;border-right:1px solid {T["border"]};">'
            f'<div style="font-size:0.65rem;font-weight:800;color:{T["accent"]};text-transform:uppercase;letter-spacing:0.06em;margin-bottom:3px;">02 · Argomento</div>'
            f'<div style="font-size:0.76rem;color:{T["text2"]};">Descrivi l\'argomento della verifica</div>'
            f'</div>'
            f'<div style="flex:1;padding:0.6rem 0.85rem;">'
            f'<div style="font-size:0.65rem;font-weight:800;color:{T["accent"]};text-transform:uppercase;letter-spacing:0.06em;margin-bottom:3px;">03 · Personalizza</div>'
            f'<div style="font-size:0.76rem;color:{T["text2"]};">Opzioni, punteggi, versioni (facoltativo)</div>'
            f'</div>'
            f'</div>'
            f'<div style="text-align:right;">'
            f'<a href="?_ob=done" style="font-size:0.75rem;color:{T["muted"]};'
            f'text-decoration:underline;text-underline-offset:2px;cursor:pointer;'
            f'font-family:DM Sans,sans-serif;font-weight:500;">Ho capito, non mostrare più →</a>'
            f'</div>'
            f'</div>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    # ── STEP 1 — MATERIA + SCUOLA ─────────────────────────────────────────────
    st.markdown(f"""
    <div class="step-label">
      <span class="step-num">01</span>
      <span class="step-title">Materia e Tipo di Scuola</span>
      <span class="step-line"></span>
    </div>
    """, unsafe_allow_html=True)

    col_mat, col_scuola = st.columns(2)

    with col_mat:
        st.markdown(
            f'<div style="font-size:0.75rem;font-weight:700;color:{T["text2"]};'
            f'margin-bottom:4px;font-family:DM Sans,sans-serif;">📚 Materia</div>',
            unsafe_allow_html=True
        )
        _materie_select = MATERIE + ["✏️ Altra materia..."]
        _materia_sel = st.selectbox(
            "Materia", _materie_select, index=0,
            label_visibility="collapsed", key="sel_materia"
        )
        if _materia_sel == "✏️ Altra materia...":
            materia_scelta = st.text_input(
                "Scrivi materia:",
                placeholder="es. Economia Aziendale...",
                key="_materia_custom_input",
                label_visibility="collapsed"
            ).strip() or "Matematica"
        else:
            materia_scelta = _materia_sel or "Matematica"

    with col_scuola:
        st.markdown(
            f'<div style="font-size:0.75rem;font-weight:700;color:{T["text2"]};'
            f'margin-bottom:4px;font-family:DM Sans,sans-serif;">🏫 Tipo di Scuola</div>',
            unsafe_allow_html=True
        )
        # Recupera selezione precedente se disponibile
        _scuola_default_idx = 0
        _prev_scuola = st.session_state.gen_params.get("difficolta", "")
        if _prev_scuola and _prev_scuola in SCUOLE:
            _scuola_default_idx = SCUOLE.index(_prev_scuola)

        difficolta = st.selectbox(
            "Scuola", SCUOLE,
            index=_scuola_default_idx,
            label_visibility="collapsed",
            key="sel_scuola"
        )

    # ── STEP 2 — ARGOMENTO ───────────────────────────────────────────────────
    st.markdown(f"""
    <div class="ai-hint">
      <span class="ai-hint-icon">💡</span>
      <span><strong>Suggerimento:</strong> più dettagli fornisci, più la verifica sarà precisa.</span>
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

    # ── STEP 3 — PERSONALIZZA ────────────────────────────────────────────────
    st.markdown(f"""
    <div class="step-label">
      <span class="step-num">03</span>
      <span class="step-title">Personalizza</span>
      <span class="step-line"></span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="personalizza-wrap">', unsafe_allow_html=True)
    with st.expander("Personalizza la verifica"):

        # ── Tempistiche e struttura ───────────────────────────────────────────
        st.markdown(f'<div class="expander-heading">⏱️ Tempistiche e Struttura</div>',
                    unsafe_allow_html=True)
        _c_dur, _c_num = st.columns(2)
        with _c_dur:
            durata_scelta = st.selectbox(
                "Durata della verifica",
                ["30 min", "1 ora", "1 ora e 30 min", "2 ore"], index=1
            )
        with _c_num:
            num_esercizi_totali = st.slider(
                "Numero di esercizi", min_value=1, max_value=15, value=4
            )

        # ── Punteggi ─────────────────────────────────────────────────────────
        st.markdown(f'<div class="expander-heading" style="margin-top:1rem;">🎯 Punteggi e Valutazione</div>',
                    unsafe_allow_html=True)
        _c_pts1, _c_pts2 = st.columns(2)
        with _c_pts1:
            mostra_punteggi = st.toggle("Mostra punteggi", value=True)
        with _c_pts2:
            con_griglia = st.toggle("Griglia di valutazione", value=False)
        if mostra_punteggi:
            punti_totali = st.slider(
                "Punti totali verifica", min_value=10, max_value=100, value=100, step=5
            )
        else:
            punti_totali = 100

        # ── Varianti ─────────────────────────────────────────────────────────
        st.markdown(f'<div class="expander-heading" style="margin-top:1rem;">📋 Varianti</div>',
                    unsafe_allow_html=True)
        _c_v1, _c_v2 = st.columns(2)
        with _c_v1:
            doppia_fila = st.toggle("Genera Fila B", value=False,
                                    help="Crea una seconda versione con dati diversi")
            bes_dsa = st.toggle("Versione BES/DSA", value=False,
                                help="Genera una versione semplificata/ridotta")
        with _c_v2:
            genera_soluzioni = st.toggle("Genera Soluzioni", value=False,
                                         help="Crea un documento con le soluzioni (riservato al docente)")
            if bes_dsa and doppia_fila:
                bes_dsa_b = st.toggle("BES/DSA anche per Fila B", value=False)
            else:
                bes_dsa_b = False
        if bes_dsa:
            perc_ridotta = st.slider(
                "Riduzione esercizi BES/DSA (%)", min_value=10, max_value=50, value=25, step=5
            )
        else:
            perc_ridotta = 25

        # ── Esercizi personalizzati ───────────────────────────────────────────
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
                    st.markdown(f'<div class="expander-heading">Esercizio {i + 1}</div>',
                                unsafe_allow_html=True)
                    t = st.selectbox(
                        "Tipo esercizio", TIPI_ESERCIZIO,
                        index=TIPI_ESERCIZIO.index(ex.get("tipo", "Aperto")),
                        key=f"tipo_{i}", label_visibility="visible"
                    )
                    st.session_state.esercizi_custom[i]["tipo"] = t
                    d = st.text_input(
                        "Descrizione (opzionale)",
                        value=ex.get("descrizione", ""),
                        placeholder="es. Risolvi ax²+bx+c=0 mostrando i passaggi",
                        key=f"desc_{i}", label_visibility="visible"
                    )
                    st.session_state.esercizi_custom[i]["descrizione"] = d
                    _cimg, _cdel = st.columns([3, 1])
                    with _cimg:
                        st.markdown('<div class="compact-uploader">', unsafe_allow_html=True)
                        img = st.file_uploader(
                            "📎 Immagine allegata", type=["png", "jpg", "jpeg"],
                            key=f"img_{i}", label_visibility="collapsed"
                        )
                        st.markdown("</div>", unsafe_allow_html=True)
                        if img:
                            st.session_state.esercizi_custom[i]["immagine"] = img
                        if st.session_state.esercizi_custom[i].get("immagine"):
                            st.image(st.session_state.esercizi_custom[i]["immagine"], width=60)
                    with _cdel:
                        st.markdown('<div style="padding-top:4px;">', unsafe_allow_html=True)
                        if st.button("🗑 Rimuovi", key=f"rm_{i}", use_container_width=True):
                            to_remove = i
                        st.markdown("</div>", unsafe_allow_html=True)
                    st.markdown('<hr style="margin:0.8rem 0; opacity:0.15;">', unsafe_allow_html=True)
                if to_remove is not None:
                    st.session_state.esercizi_custom.pop(to_remove)
                    st.rerun()

            can_add = len(st.session_state.esercizi_custom) < num_esercizi_totali
            if st.button("＋ Aggiungi esercizio specifico", disabled=not can_add):
                st.session_state.esercizi_custom.append(
                    {"tipo": "Aperto", "descrizione": "", "immagine": None}
                )
                st.rerun()

        # ── Istruzioni AI e File ──────────────────────────────────────────────
        st.markdown(f'<div class="expander-heading" style="margin-top:1rem;">🤖 Istruzioni per l\'AI</div>',
                    unsafe_allow_html=True)
        note_generali = st.text_area(
            "note", label_visibility="collapsed",
            placeholder=NOTE_PLACEHOLDER.get(materia_scelta,
                                             "es. Argomenti da privilegiare, tipo di esercizi..."),
            height=80
        )

        st.markdown(f'<div class="expander-heading">📂 File di riferimento</div>',
                    unsafe_allow_html=True)
        st.markdown('<div class="compact-uploader">', unsafe_allow_html=True)
        file_ispirazione = st.file_uploader(
            "📎 Allega PDF o immagine", type=["pdf", "png", "jpg", "jpeg"],
            label_visibility="collapsed"
        )
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # ── BOTTONE GENERA ────────────────────────────────────────────────────────
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
        _files_hint = ["📄 Verifica A"]
        if doppia_fila:     _files_hint.append("📄 Fila B")
        if bes_dsa:         _files_hint.append("📄 BES/DSA")
        if genera_soluzioni: _files_hint.append("✅ Soluzioni")
        st.markdown(f"""
        <div class="genera-hint">
          <strong style="color:{T['text2']};">File richiesti ({len(_files_hint)}):</strong>
          {' · '.join(_files_hint)}
        </div>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # ── LOGICA GENERAZIONE ────────────────────────────────────────────────────
    if genera_btn and not _limite_raggiunto:
        if not argomento:
            st.warning("⚠️ Inserisci l'argomento della verifica.")
            st.stop()

        calibrazione = CALIBRAZIONE_SCUOLA.get(difficolta, "")
        s_es, imgs_es = costruisci_prompt_esercizi(
            st.session_state.esercizi_custom,
            num_esercizi_totali,
            punti_totali if mostra_punteggi else 0,
            mostra_punteggi
        )

        _n_steps = (4
                    + (2 if doppia_fila else 0)
                    + (1 if bes_dsa else 0)
                    + (1 if bes_dsa and doppia_fila and bes_dsa_b else 0)
                    + (1 if genera_soluzioni else 0))
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

        try:
            model = genai.GenerativeModel(modello_id)
            ris = genera_verifica(
                model=model,
                materia=materia_scelta,
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
                if dati.get("latex"):
                    v["latex"] = dati["latex"]
                    v["latex_originale"] = dati["latex"]
                if dati.get("pdf"):
                    v["pdf"]     = dati["pdf"]
                    v["pdf_ts"]  = time.time()
                    v["preview"] = True
                if fid == "S":
                    if dati.get("testo"): v["testo"] = dati["testo"]
                    if dati.get("latex"): v["latex"] = dati["latex"]
                    if dati.get("pdf"):   v["pdf"]   = dati["pdf"]

            _aggiorna("A",  ris["A"])
            _aggiorna("B",  ris["B"])
            _aggiorna("R",  ris["R"])
            _aggiorna("RB", ris["RB"])
            _aggiorna("S",  ris["S"])

            # Salva parametri per STAGE_REVIEW / FINAL
            st.session_state.gen_params = {
                "materia":         materia_scelta,
                "difficolta":      difficolta,
                "argomento":       ris["titolo"],
                "durata":          durata_scelta,
                "num_esercizi":    num_esercizi_totali,
                "punti_totali":    punti_totali,
                "mostra_punteggi": mostra_punteggi,
                "con_griglia":     con_griglia,
                "doppia_fila":     doppia_fila,
                "bes_dsa":         bes_dsa,
                "perc_ridotta":    perc_ridotta,
                "bes_dsa_b":       bes_dsa_b,
                "genera_soluzioni": genera_soluzioni,
                "modello_id":      modello_id,
            }

            # Estrai blocchi per la revisione
            preamble, blocks = _extract_blocks(st.session_state.verifiche["A"]["latex"])
            st.session_state.review_preamble = preamble
            st.session_state.review_blocks   = blocks

            st.session_state.last_materia    = materia_scelta
            st.session_state.last_argomento  = ris["titolo"]
            st.session_state.last_gen_ts     = time.time()
            st.session_state._onboarding_done = True
            st.session_state.preview_images   = []

            _prog.markdown(f"""
<div style="margin:0.6rem 0 1rem 0;">
  <div style="font-size:0.82rem;font-weight:600;color:{T['success']};
              font-family:'DM Sans',sans-serif;margin-bottom:6px;">✅  Bozza pronta!</div>
  <div style="background:{T['border']};border-radius:100px;height:8px;overflow:hidden;">
    <div style="background:{T['success']};width:100%;height:100%;border-radius:100px;"></div>
  </div>
</div>
""", unsafe_allow_html=True)
            time.sleep(0.7)
            _prog.empty()

            # Salva su Supabase
            try:
                supabase_admin.table("verifiche_storico").insert({
                    "user_id":      st.session_state.utente.id,
                    "materia":      materia_scelta,
                    "argomento":    ris["titolo"],
                    "scuola":       difficolta,
                    "latex_a":      ris["A"]["latex"] or None,
                    "latex_b":      ris["B"]["latex"] or None,
                    "latex_r":      ris["R"]["latex"] or None,
                    "modello":      modello_id,
                    "num_esercizi": num_esercizi_totali,
                }).execute()
                st.session_state._storico_refresh += 1
                st.toast("✅ Verifica salvata!", icon="💾")
            except Exception as e:
                st.warning(f"⚠️ Salvataggio storico non riuscito: {e}")

            # Transizione a REVIEW
            st.session_state.stage = STAGE_REVIEW
            st.rerun()

        except Exception as e:
            _prog.empty()
            st.error(f"❌ Errore durante la generazione: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
#  STAGE_REVIEW — revisione esercizio per esercizio
# ═══════════════════════════════════════════════════════════════════════════════

def _render_stage_review():
    gp = st.session_state.gen_params
    argomento_str = gp.get("argomento", "Verifica")
    materia_str   = gp.get("materia", "")
    scuola_str    = gp.get("difficolta", "")
    mostra_punteggi = gp.get("mostra_punteggi", True)
    punti_totali    = gp.get("punti_totali", 100)
    con_griglia     = gp.get("con_griglia", False)
    modello_rw      = gp.get("modello_id", modello_id)

    # Header ──────────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,{T['accent_light']} 0%,{T['card']} 100%);
                border:2px solid {T['accent']};border-radius:16px;padding:0;
                margin-bottom:1.5rem;overflow:hidden;">
      <div style="background:{T['accent']};padding:0.9rem 1.3rem;">
        <div style="display:flex;align-items:center;gap:12px;">
          <span style="font-size:1.6rem;">✏️</span>
          <div style="flex:1;">
            <div style="font-family:'DM Sans',sans-serif;font-size:1.1rem;font-weight:900;
                        color:#fff;letter-spacing:-0.02em;">Revisione Bozza</div>
            <div style="font-size:0.75rem;color:#ffffff;opacity:0.85;font-weight:500;margin-top:2px;">
              {materia_str} · {scuola_str} · {argomento_str}
            </div>
          </div>
          <div style="background:#ffffff22;border:1px solid #ffffff33;border-radius:20px;
                      padding:5px 14px;font-size:0.7rem;font-weight:700;color:#fff;">
            {len(st.session_state.review_blocks)} ESERCIZI
          </div>
        </div>
      </div>
      <div style="padding:0.9rem 1.3rem;background:{T['card']};">
        <div style="font-size:0.82rem;color:{T['text2']};line-height:1.5;">
          Controlla ogni esercizio. Puoi chiedere all'AI di <strong>rigenerare</strong>
          singoli esercizi con istruzioni precise. Quando sei soddisfatto,
          clicca <strong>Conferma e genera PDF</strong> per procedere.
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    blocks = st.session_state.review_blocks

    if not blocks:
        st.warning("⚠️ Nessun esercizio trovato nel LaTeX generato. Torna indietro e rigenera.")
        if st.button("← Torna alla configurazione"):
            st.session_state.stage = STAGE_INPUT
            st.rerun()
        return

    model_rw = genai.GenerativeModel(modello_rw)

    # Visualizza ogni blocco ──────────────────────────────────────────────────
    for idx, block in enumerate(blocks):
        title     = block.get("title", f"Esercizio {idx + 1}")
        body_tex  = block.get("body", "")
        readable  = _strip_latex_display(body_tex)

        st.markdown(f"""
        <div style="background:{T['bg2']};border:1.5px solid {T['border']};
                    border-radius:12px;overflow:hidden;margin-bottom:1rem;">
          <div style="background:{T['card2']};padding:0.6rem 1rem;
                      border-bottom:1px solid {T['border']};
                      display:flex;align-items:center;gap:8px;">
            <div style="background:{T['accent']};color:#fff;border-radius:50%;
                        width:24px;height:24px;display:flex;align-items:center;
                        justify-content:center;font-size:0.7rem;font-weight:800;
                        flex-shrink:0;">{idx + 1}</div>
            <span style="font-size:0.9rem;font-weight:700;color:{T['text']};
                         font-family:'DM Sans',sans-serif;">{title}</span>
          </div>
          <div style="padding:0.8rem 1rem;">
        """, unsafe_allow_html=True)

        # Preview leggibile
        if readable:
            st.markdown(f"""
            <div style="font-size:0.82rem;color:{T['text2']};line-height:1.6;
                        white-space:pre-wrap;font-family:'DM Sans',sans-serif;">
{readable[:1200]}{'…' if len(readable) > 1200 else ''}
            </div>
            """, unsafe_allow_html=True)

        st.markdown("</div></div>", unsafe_allow_html=True)

        # LaTeX grezzo (collapsibile)
        with st.expander(f"⌨️ Sorgente LaTeX — Esercizio {idx + 1}", expanded=False):
            st.code(f"\\subsection*{{{title}}}\n{body_tex}", language="latex")

        # Modifica AI
        col_input, col_btn = st.columns([4, 1])
        with col_input:
            istruzione = st.text_input(
                f"Modifica esercizio {idx + 1}",
                placeholder="es. Aumenta la difficoltà / Cambia i numeri / Converti in Vero/Falso",
                key=f"rw_istr_{idx}",
                label_visibility="collapsed"
            )
        with col_btn:
            rigenera_pressed = st.button(
                "🔄 Rigenera", key=f"rw_btn_{idx}", use_container_width=True,
                disabled=not istruzione.strip()
            )

        if rigenera_pressed and istruzione.strip():
            # Prompt per rigenerare un singolo blocco
            punti_nota = (
                "Mantieni il formato (X pt) su ogni \\item come nell'originale. "
                "Non è necessario che i punti sommino a un totale preciso."
                if mostra_punteggi else "NON inserire punteggi (X pt)."
            )
            _prompt_rw = (
                f"Sei un docente esperto di {materia_str} e LaTeX.\n"
                f"Devi rigenerare SOLO questo esercizio della verifica, "
                f"secondo l'istruzione del docente.\n\n"
                f"ESERCIZIO ORIGINALE:\n"
                f"\\subsection*{{{title}}}\n{body_tex}\n\n"
                f"ISTRUZIONE DEL DOCENTE: {istruzione.strip()}\n\n"
                f"REGOLE:\n"
                f"- Restituisci SOLO il blocco \\subsection*{{...}} con il nuovo esercizio.\n"
                f"- Mantieni la stessa struttura LaTeX.\n"
                f"- {punti_nota}\n"
                f"- NON includere preambolo o \\begin{{document}}.\n"
                f"OUTPUT: SOLO codice LaTeX del blocco esercizio."
            )
            with st.spinner(f"⏳ Rigenerando esercizio {idx + 1}…"):
                try:
                    resp = model_rw.generate_content(_prompt_rw)
                    nuovo = resp.text.replace("```latex", "").replace("```", "").strip()
                    # Estrai title e body dal nuovo blocco
                    m = re.match(r"\\subsection\*\{([^}]*)\}(.*)", nuovo, re.DOTALL)
                    if m:
                        st.session_state.review_blocks[idx]["title"] = m.group(1)
                        st.session_state.review_blocks[idx]["body"]  = m.group(2).strip()
                    else:
                        st.session_state.review_blocks[idx]["body"] = nuovo
                    st.success(f"✅ Esercizio {idx + 1} aggiornato!")
                    time.sleep(0.5)
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Errore: {e}")

        st.markdown('<hr style="margin:0.4rem 0;opacity:0.12;">', unsafe_allow_html=True)

    # ── TASTO CONFERMA ────────────────────────────────────────────────────────
    st.markdown('<div style="height:1rem;"></div>', unsafe_allow_html=True)

    col_back, col_confirm = st.columns([1, 2])
    with col_back:
        if st.button("← Riconfigura", use_container_width=True):
            st.session_state.stage = STAGE_INPUT
            st.rerun()

    with col_confirm:
        if st.button("✅ Conferma e genera PDF finale", type="primary",
                     use_container_width=True):
            with st.spinner("⏳ Ricostruzione LaTeX e compilazione PDF…"):
                # Ricostruisci il LaTeX da preamble + blocchi eventualmente modificati
                latex_final = _reconstruct_latex(
                    st.session_state.review_preamble,
                    st.session_state.review_blocks
                )
                # Post-processing
                latex_final = fix_items_environment(latex_final)
                latex_final = rimuovi_vspace_corpo(latex_final)
                if mostra_punteggi:
                    latex_final = rimuovi_punti_subsection(latex_final)
                    latex_final = riscala_punti(latex_final, punti_totali)
                if con_griglia:
                    latex_final = inietta_griglia(latex_final, punti_totali)

                # Aggiorna LaTeX in sessione
                st.session_state.verifiche["A"]["latex"] = latex_final
                st.session_state.verifiche["A"]["latex_originale"] = latex_final

                # Compila PDF
                pdf_bytes, err = compila_pdf(latex_final)
                if pdf_bytes:
                    st.session_state.verifiche["A"]["pdf"]     = pdf_bytes
                    st.session_state.verifiche["A"]["pdf_ts"]  = time.time()
                    st.session_state.verifiche["A"]["preview"] = True

                    # Genera anteprima immagini per STAGE_FINAL
                    imgs, _ = pdf_to_images_bytes(pdf_bytes)
                    st.session_state.preview_images = imgs or []

                    st.session_state.stage = STAGE_FINAL
                    st.rerun()
                else:
                    st.error("❌ Errore di compilazione PDF. Controlla il LaTeX.")
                    with st.expander("Log errore"):
                        st.text(err)


# ═══════════════════════════════════════════════════════════════════════════════
#  STAGE_FINAL — preview immagine + download
# ═══════════════════════════════════════════════════════════════════════════════

def _render_stage_final():
    gp  = st.session_state.gen_params
    vA  = st.session_state.verifiche["A"]
    vB  = st.session_state.verifiche["B"]
    vR  = st.session_state.verifiche["R"]
    vRB = st.session_state.verifiche["RB"]
    vS  = st.session_state.verifiche["S"]

    argomento_str   = gp.get("argomento", "Verifica")
    materia_str     = gp.get("materia", "")
    scuola_str      = gp.get("difficolta", "")
    doppia_fila     = gp.get("doppia_fila", False)
    bes_dsa         = gp.get("bes_dsa", False)
    bes_dsa_b       = gp.get("bes_dsa_b", False)
    mostra_punteggi = gp.get("mostra_punteggi", True)
    punti_totali    = gp.get("punti_totali", 100)
    con_griglia     = gp.get("con_griglia", False)
    genera_sol      = gp.get("genera_soluzioni", False)

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,{T['accent_light']} 0%,{T['card']} 100%);
                border:2px solid {T['success']};border-radius:16px;padding:0;
                margin-bottom:1.5rem;overflow:hidden;">
      <div style="background:{T['success']};padding:0.9rem 1.3rem;">
        <div style="display:flex;align-items:center;gap:12px;">
          <span style="font-size:1.6rem;">🎉</span>
          <div style="flex:1;">
            <div style="font-family:'DM Sans',sans-serif;font-size:1.15rem;font-weight:900;
                        color:#fff;letter-spacing:-0.02em;">Verifica Pronta!</div>
            <div style="font-size:0.75rem;color:#ffffff;opacity:0.85;font-weight:500;margin-top:2px;">
              {materia_str} · {scuola_str} · {argomento_str}
            </div>
          </div>
        </div>
      </div>
      <div style="padding:0.9rem 1.3rem;background:{T['card']};">
        <div style="font-size:0.82rem;color:{T['text2']};line-height:1.5;">
          ⚠️ Le verifiche generate dall'AI sono <strong>suggerimenti didattici</strong>.
          Controlla sempre il contenuto prima di distribuirle agli studenti.
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Layout a due colonne: preview | download ──────────────────────────────
    col_preview, col_downloads = st.columns([3, 2], gap="large")

    with col_preview:
        st.markdown(f"""
        <div style="font-size:0.8rem;font-weight:700;color:{T['text2']};
                    text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.6rem;">
          👁 Anteprima — Fila A
        </div>
        """, unsafe_allow_html=True)

        imgs = st.session_state.preview_images

        if imgs:
            # Mostra le prime 3 pagine come immagini
            for i, img_bytes in enumerate(imgs[:3]):
                st.image(img_bytes, use_container_width=True,
                         caption=f"Pagina {i + 1}")
            if len(imgs) > 3:
                st.caption(f"…e altre {len(imgs) - 3} pagine. Scarica il PDF per la versione completa.")
        elif vA.get("pdf"):
            # Fallback: iframe PDF
            b64 = base64.b64encode(vA["pdf"]).decode()
            st.markdown(f"""
            <iframe src="data:application/pdf;base64,{b64}#toolbar=0&navpanes=0&scrollbar=1"
                    style="width:100%;height:520px;border:none;border-radius:8px;display:block;">
            </iframe>
            """, unsafe_allow_html=True)
        else:
            st.info("Anteprima non disponibile.")

        # Tasto rigenera anteprima
        if vA.get("pdf") and not imgs:
            if st.button("🖼️ Genera anteprima immagine", use_container_width=True):
                with st.spinner("Conversione PDF → immagini…"):
                    new_imgs, err = pdf_to_images_bytes(vA["pdf"])
                if new_imgs:
                    st.session_state.preview_images = new_imgs
                    st.rerun()
                else:
                    st.warning("Anteprima immagine non disponibile (pdf2image/pdftoppm assente).")

    with col_downloads:
        st.markdown(f"""
        <div style="font-size:0.8rem;font-weight:700;color:{T['text2']};
                    text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.6rem;">
          📥 Download
        </div>
        """, unsafe_allow_html=True)

        def _download_section(label, icon, fid, v, suffix=""):
            """Renders PDF + DOCX download for a given variant."""
            if not v.get("latex") and not v.get("pdf"):
                return
            st.markdown(f"""
            <div style="background:{T['bg2']};border:1.5px solid {T['border']};
                        border-radius:10px;padding:0.8rem 1rem;margin-bottom:0.75rem;">
              <div style="font-size:0.82rem;font-weight:700;color:{T['text']};
                          margin-bottom:0.5rem;">{icon} {label}</div>
            """, unsafe_allow_html=True)

            fname = f"{argomento_str}_{suffix}".strip("_")

            # PDF
            if v.get("pdf"):
                st.download_button(
                    f"📄 PDF ({_stima_dimensione(v['pdf'])})",
                    data=v["pdf"],
                    file_name=f"{fname}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    key=f"dl_pdf_{fid}"
                )
            elif v.get("latex"):
                if st.button(f"📄 Compila PDF", key=f"gen_pdf_{fid}",
                             use_container_width=True):
                    with st.spinner("Compilazione…"):
                        pdf_b, err = compila_pdf(v["latex"])
                    if pdf_b:
                        st.session_state.verifiche[fid]["pdf"]    = pdf_b
                        st.session_state.verifiche[fid]["pdf_ts"] = time.time()
                        st.rerun()
                    else:
                        st.error("Errore PDF")

            # DOCX
            _docx_gen_key = f"_docx_gen_{fid}"
            if v.get("docx"):
                st.download_button(
                    f"📝 Word ({_stima_dimensione(v['docx'])})",
                    data=v["docx"],
                    file_name=f"{fname}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                    key=f"dl_docx_{fid}"
                )
            else:
                if st.button(f"📝 Genera Word", key=f"gen_docx_{fid}",
                             use_container_width=True):
                    st.session_state[_docx_gen_key] = True
                if st.session_state.get(_docx_gen_key, False):
                    with st.spinner("⏳ Conversione Word…"):
                        db, de = latex_to_docx_via_ai(v["latex"], con_griglia=con_griglia)
                    st.session_state[_docx_gen_key] = False
                    if db:
                        st.session_state.verifiche[fid]["docx"] = db
                        st.rerun()
                    else:
                        st.error("Errore Word")

            # Sorgente LaTeX
            if v.get("latex"):
                st.download_button(
                    "⬇ Sorgente .tex",
                    data=v["latex"].encode("utf-8"),
                    file_name=f"{fname}.tex",
                    mime="text/plain",
                    key=f"dl_tex_{fid}",
                    help="Scarica il sorgente LaTeX per modificarlo con un editor esterno"
                )

            st.markdown("</div>", unsafe_allow_html=True)

        # Fila A (sempre presente)
        _download_section("Verifica — Fila A", "📄", "A", vA, "FilaA")

        # Fila B
        if doppia_fila and vB.get("latex"):
            _download_section("Verifica — Fila B", "📄", "B", vB, "FilaB")

        # BES/DSA A
        if bes_dsa and vR.get("latex"):
            _download_section("Versione BES/DSA — Fila A", "♿", "R", vR, "BES_FilaA")

        # BES/DSA B
        if bes_dsa and doppia_fila and bes_dsa_b and vRB.get("latex"):
            _download_section("Versione BES/DSA — Fila B", "♿", "RB", vRB, "BES_FilaB")

        # Soluzioni
        if vS.get("pdf") or vS.get("testo") or vS.get("latex"):
            st.markdown(f"""
            <div style="background:{T['bg2']};border:1.5px solid {T['success']}44;
                        border-radius:10px;padding:0.8rem 1rem;margin-bottom:0.75rem;">
              <div style="font-size:0.82rem;font-weight:700;color:{T['success']};
                          margin-bottom:0.5rem;">✅ Soluzioni — Solo docente</div>
            """, unsafe_allow_html=True)
            if vS.get("pdf"):
                st.download_button(
                    f"📄 Soluzioni PDF ({_stima_dimensione(vS['pdf'])})",
                    data=vS["pdf"],
                    file_name=f"{argomento_str}_Soluzioni.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    key="dl_sol_pdf"
                )
            if vS.get("testo"):
                with st.expander("👁 Mostra soluzioni"):
                    st.markdown(vS["testo"])
            st.markdown("</div>", unsafe_allow_html=True)

        # ── Torna a modificare la bozza ───────────────────────────────────────
        st.markdown('<div style="height:0.5rem;"></div>', unsafe_allow_html=True)

        col_rev, col_new = st.columns(2)
        with col_rev:
            if st.button("← Rivedi esercizi", use_container_width=True,
                         help="Torna alla fase di revisione per modificare gli esercizi"):
                st.session_state.stage = STAGE_REVIEW
                st.rerun()
        with col_new:
            if st.button("🆕 Nuova Verifica", type="primary", use_container_width=True):
                # Reset completo
                st.session_state.stage           = STAGE_INPUT
                st.session_state.verifiche        = {
                    "A": _vf(), "B": _vf(), "R": _vf(), "RB": _vf(),
                    "S": {"latex": None, "testo": None, "pdf": None},
                }
                st.session_state.review_preamble  = ""
                st.session_state.review_blocks    = []
                st.session_state.gen_params       = {}
                st.session_state.preview_images   = []
                st.session_state.esercizi_custom  = []
                st.session_state.last_argomento   = None
                st.session_state.last_materia     = None
                st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
#  ROUTING PRINCIPALE
# ═══════════════════════════════════════════════════════════════════════════════

_render_stage_indicator()

current_stage = st.session_state.stage

if current_stage == STAGE_INPUT:
    _render_stage_input()

elif current_stage == STAGE_REVIEW:
    _render_stage_review()

elif current_stage == STAGE_FINAL:
    _render_stage_final()


# ── FOOTER ────────────────────────────────────────────────────────────────────
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
    background: none; border: none; cursor: pointer;
    color: {T['accent']}; font-weight: 600; font-size: 0.72rem;
    font-family: 'DM Sans', sans-serif; padding: 0;
    display: block; margin: 0 auto; text-align: center; width: 100%;
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
  ta.focus(); ta.select();
  var ok = false;
  try {{ ok = document.execCommand("copy"); }} catch(e) {{}}
  document.body.removeChild(ta);
  if (ok) {{
    btn.innerText = "✅ Link copiato!";
    setTimeout(function() {{ btn.innerText = "🔗 Condividi con i colleghi"; }}, 2000);
  }} else {{ btn.innerText = url; }}
}}
</script>
""", height=30)
