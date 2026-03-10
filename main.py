# ── main.py — VerificAI ──────────────────────────────────────────────────────
# Macchina a tre stati:
#   STAGE_INPUT  → configurazione snella + tasto Genera
#   STAGE_REVIEW → revisione esercizio (selectbox + KaTeX + PDF strip)
#   STAGE_FINAL  → download PDF primario + varianti on-demand + secondari small
# ─────────────────────────────────────────────────────────────────────────────

import streamlit as st
import streamlit.components.v1 as components
import base64
import html as html_lib
import logging
import re
import os
import time
from datetime import datetime, timezone

import google.generativeai as genai

from sidebar import render_sidebar
from generation import genera_verifica, analizza_documento_caricato, compila_contesto_generazione
from prompts import (
    prompt_versione_b, prompt_versione_ridotta, prompt_soluzioni,
    prompt_modifica, prompt_qa_verifica,
    prompt_rubrica_valutazione, prompt_da_template, prompt_variante_rapida,
)
from docx_export import latex_to_docx_via_ai, _rubrica_to_docx
from latex_utils import (
    compila_pdf, inietta_griglia, riscala_punti, riscala_punti_custom,
    fix_items_environment, rimuovi_vspace_corpo, pulisci_corpo_latex,
    rimuovi_punti_subsection, pdf_to_images_bytes,
    extract_blocks, reconstruct_latex, extract_corpo, extract_preambolo,
    parse_pts_from_block_body, valida_totale, riscala_single_block,
    parse_items_from_block, apply_item_pts_to_body,
    prepara_esercizi_aperti, conta_punti_latex,
)
from config import (
    APP_NAME, APP_ICON, APP_TAGLINE, SHARE_URL, FEEDBACK_FORM_URL,
    LIMITE_MENSILE, ADMIN_EMAILS, MODELLI_DISPONIBILI, THEMES,
    SCUOLE, CALIBRAZIONE_SCUOLA, MATERIE, NOTE_PLACEHOLDER, TIPI_ESERCIZIO,
    MATERIE_ICONS, MODEL_FAST_ID, get_model_id_per_piano, MATERIE_STEM,
)
# THEME_LABELS è definito nel nuovo config.py — fallback per compatibilità
try:
    from config import THEME_LABELS
except ImportError:
    THEME_LABELS = {k: k.replace("_", " ").title() for k in THEMES}
from dotenv import load_dotenv
from supabase import create_client, Client
from auth import mostra_auth, ripristina_sessione, cancella_sessione_cookie
from styles import get_css, _is_light_color
from ui_helpers import (
    _render_back_button, _make_katex_html, _render_sticky_header,
    _render_step_progress, _split_download_button, _render_breadcrumb,
)

logger = logging.getLogger("verificai.main")
try:
    from styles import _is_light_color
except ImportError:
    def _is_light_color(hex_color: str) -> bool:
        try:
            h = hex_color.lstrip("#")
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            return (0.299 * r + 0.587 * g + 0.114 * b) / 255 > 0.5
        except Exception:
            return False

# ── MATHPIX OCR (opzionale — degradazione graceful se non configurato) ────────
try:
    import mathpix_utils as _mpx
    _MATHPIX_AVAILABLE = True
except ImportError:
    _mpx = None
    _MATHPIX_AVAILABLE = False

# ── ST_YLED (opzionale — sticky_header + split_button) ───────────────────────
# pip install st-styled | https://github.com/EvobyteDigitalBiology/st-styled
# Se non installato: fallback nativo (CSS injection + st.popover)
try:
    import st_yled as _styl
    _STYLED_AVAILABLE = True
except ImportError:
    _styl = None
    _STYLED_AVAILABLE = False


# ── COSTANTI STAGE ────────────────────────────────────────────────────────────
STAGE_INPUT   = "INPUT"
STAGE_PREVIEW = "PREVIEW"   # ← NUOVO: anteprima rapida post-generazione
STAGE_REVIEW  = "REVIEW"
STAGE_FINAL   = "FINAL"
STAGE_MIE_VERIFICHE = "MIE_VERIFICHE"  # ← NUOVO: pagina "Le tue verifiche"

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

# ── TEMA — inizializzazione ───────────────────────────────────────────────────
# Tema default: carta (light). Fallback robusto per sessioni vecchie (aurora/luce/ecc.)
if "theme" not in st.session_state:
    st.session_state.theme = "carta"

_theme_key = st.session_state.theme
# Fallback: qualsiasi chiave non più presente in THEMES → carta
if _theme_key not in THEMES:
    _theme_key = list(THEMES.keys())[0]   # sempre "carta"
    st.session_state.theme = _theme_key
T = THEMES[_theme_key]

# ── CONFIGURAZIONE API ────────────────────────────────────────────────────────
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    st.error("⚠️ Chiave API mancante! Crea un file .env con GOOGLE_API_KEY=...")
    st.stop()
genai.configure(api_key=API_KEY)

# ── VERIFICA DISPONIBILITÀ LATEX ─────────────────────────────────────────────────
# Sarà fatto dopo l'autenticazione per essere visibile all'utente

# ── AUTENTICAZIONE ────────────────────────────────────────────────────────────
if "utente" not in st.session_state:
    st.session_state.utente = None
if st.session_state.utente is None:
    ripristina_sessione(supabase)
    if st.session_state.utente is None:
        mostra_auth(supabase)
        st.stop()

# ── VERIFICA DISPONIBILITÀ LATEX (dopo autenticazione) ─────────────────────────────
try:
    import subprocess
    result = subprocess.run(["pdflatex", "--version"], capture_output=True, text=True, timeout=5)
    if result.returncode != 0:
        st.error("⚠️ **PDF non disponibile** - LaTeX (pdflatex) non è installato correttamente in questo ambiente. La generazione PDF non funzionerà.")
        LATEX_AVAILABLE = False
    else:
        LATEX_AVAILABLE = True
except (FileNotFoundError, subprocess.TimeoutExpired):
    st.error("⚠️ **PDF non disponibile** - LaTeX non è installato in questo ambiente. La generazione PDF non sarà disponibile.")
    LATEX_AVAILABLE = False


# ═══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _get_verifiche_mese(user_id):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    primo = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
    try:
        res = supabase_admin.table("verifiche_storico")\
            .select("id", count="exact")\
            .eq("user_id", user_id)\
            .gte("created_at", primo).execute()
        return res.count or 0
    except Exception as e:
        logger.warning("_get_verifiche_mese failed for %s: %s", user_id, e)
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
    d = reset - now
    return d.days, d.seconds // 3600


def _stima(b):
    if not b: return "—"
    kb = len(b) / 1024
    return f"{kb:.0f} KB" if kb < 1024 else f"{kb/1024:.1f} MB"


def _rubrica_to_pdf(rubrica_testo: str, materia: str = "", livello: str = "") -> bytes | None:
    """Converte il testo Markdown della rubrica di valutazione in PDF via LaTeX/pdflatex."""
    try:
        import re as _re
        from latex_utils import compila_pdf

        def _esc(t: str) -> str:
            t = t.replace('\\', r'\textbackslash{}')
            for a, b in [
                ('&',  r'\&'), ('%', r'\%'), ('#', r'\#'),
                ('_',  r'\_'), ('^', r'\^{}'), ('~', r'\~{}'),
                ('{',  r'\{'), ('}', r'\}'), ('$', r'\$'),
            ]:
                t = t.replace(a, b)
            return t

        def _md2tex(t: str) -> str:
            return _re.sub(r'\*\*([^*]+)\*\*', r'\\textbf{\1}', t)

        meta_esc = _esc(f"{materia} · {livello}") if (materia or livello) else ""

        # ── Strip AI preamble: skip everything before the first ## / ### ────────
        lines_raw = rubrica_testo.strip().split("\n")
        start_idx = 0
        for _i, _l in enumerate(lines_raw):
            if _l.strip().startswith("## ") or _l.strip().startswith("### "):
                start_idx = _i
                break
        lines_raw = lines_raw[start_idx:]

        body_lines: list[str] = []
        in_list   = False
        prev_blank = False   # collapse consecutive blank lines

        for line in lines_raw:
            s = line.strip()

            # ── Blank line ────────────────────────────────────────────────────
            if not s:
                if in_list:
                    body_lines.append(r'\end{itemize}')
                    in_list = False
                if not prev_blank:          # only one vspace per blank group
                    body_lines.append(r'\vspace{5pt}')
                prev_blank = True
                continue
            prev_blank = False

            # ── Top-level section marker (skip, title is in the header) ───────
            if s.startswith("## "):
                continue

            # ── ### Sub-section (Legenda fasce / Indicatori per esercizio) ────
            if s.startswith("### "):
                if in_list:
                    body_lines.append(r'\end{itemize}')
                    in_list = False
                body_lines.append(
                    f'\\section*{{{_md2tex(_esc(s[4:]))}}}'
                )

            # ── Bullet item (handles "- " and "  - " after strip) ────────────
            elif s.startswith("- ") or s.startswith("* "):
                if not in_list:
                    body_lines.append(
                        r'\begin{itemize}[noitemsep,topsep=2pt,leftmargin=1.4em]'
                    )
                    in_list = True
                body_lines.append(f'  \\item {_md2tex(_esc(s[2:]))}')

            # ── Bold line: **full** OR **partial** (extra text) ───────────────
            elif s.startswith("**") and "**" in s[2:]:
                if in_list:
                    body_lines.append(r'\end{itemize}')
                    in_list = False
                tex_line = _md2tex(_esc(s))
                body_lines.append(
                    r'\vspace{4pt}' '\n'
                    r'\noindent ' + tex_line + r'\\[-1pt]'
                )

            # ── Plain paragraph ───────────────────────────────────────────────
            else:
                if in_list:
                    body_lines.append(r'\end{itemize}')
                    in_list = False
                body_lines.append(_md2tex(_esc(s)))

        if in_list:
            body_lines.append(r'\end{itemize}')

        latex = (
            r'\documentclass[a4paper,11pt]{article}' '\n'
            r'\usepackage[utf8]{inputenc}' '\n'
            r'\usepackage[T1]{fontenc}' '\n'
            r'\usepackage[italian]{babel}' '\n'
            r'\usepackage[top=2cm,bottom=2cm,left=2.2cm,right=2.2cm]{geometry}' '\n'
            r'\usepackage[dvipsnames]{xcolor}' '\n'
            r'\usepackage{titlesec}' '\n'
            r'\usepackage{enumitem}' '\n'
            r'\usepackage{microtype}' '\n'
            r'\definecolor{rubTeal}{HTML}{0A8F72}' '\n'
            r'\definecolor{rubDark}{HTML}{1A2E25}' '\n'
            r'\definecolor{rubGray}{HTML}{6B7280}' '\n'
            r'\titleformat{\section}{\normalsize\bfseries\color{rubTeal}}'
            r'{}{0em}{}[\vspace{-3pt}{\color{rubTeal!40}\hrule height 0.5pt}\vspace{1pt}]' '\n'
            r'\titlespacing*{\section}{0pt}{10pt}{4pt}' '\n'
            r'\setlength{\parskip}{3pt}\setlength{\parindent}{0pt}' '\n'
            r'\pagestyle{empty}' '\n'
            r'\begin{document}' '\n'
            r'\begin{center}' '\n'
            r'{\large\bfseries\color{rubTeal} Rubrica di Valutazione}\\[3pt]' '\n'
            + (f'{{\\small\\color{{rubGray}} {meta_esc}}}\\\\[3pt]\n' if meta_esc else '')
            + r'{\color{rubTeal}\rule{\linewidth}{1.4pt}}' '\n'
            r'\end{center}' '\n'
            r'\vspace{4pt}' '\n'
            + '\n'.join(body_lines) + '\n'
            r'\end{document}'
        )

        pdf_bytes, _ = compila_pdf(latex)
        return pdf_bytes
    except Exception as e:
        logger.warning("_rubrica_to_pdf failed: %s", e)
        return None


def _vf():
    return {"latex": "", "pdf": None, "preview": False,
            "docx": None, "pdf_ts": None, "docx_ts": None, "latex_originale": ""}


# _render_back_button → moved to ui_helpers.py


# Parole chiave che indicano che l'utente sta chiedendo una modifica ai punteggi.
# In quel caso il prompt AI viene bloccato e viene mostrato un suggerimento
# a usare il pannello Ricalibra Punteggi.
_SCORE_KEYWORDS = {
    'pt', 'punt', 'punti', 'punteggio', 'punteggi', 'punto',
    'voto', 'voti', 'score', 'valut', 'peso', 'perc', '%',
    '5 pt', '10 pt', '15 pt', '20 pt', '25 pt', '30 pt',
}




# ── On-demand variant generation ───────────────────────────────────────────────

def _genera_variante(tipo: str, model_id: str, gp: dict, vA: dict) -> dict:
    model_v = genai.GenerativeModel(model_id)
    mostra_punteggi = gp.get("mostra_punteggi", True)
    punti_totali    = gp.get("punti_totali", 100)
    con_griglia     = gp.get("con_griglia", False)
    materia         = gp.get("materia", "")
    perc_ridotta    = gp.get("perc_ridotta", 25)
    argomento       = gp.get("argomento", "")

    latex_a    = vA.get("latex", "")
    corpo_a    = extract_corpo(latex_a)
    preamb_a   = extract_preambolo(latex_a)

    def _post(corpo: str) -> str:
        corpo = fix_items_environment(corpo)
        corpo = rimuovi_vspace_corpo(corpo)
        if mostra_punteggi:
            corpo = rimuovi_punti_subsection(corpo)
            corpo = prepara_esercizi_aperti(corpo, punti_totali)
            corpo = riscala_punti(corpo, punti_totali)
        return corpo

    def _compile(latex: str):
        if "\\end{document}" not in latex:
            latex += "\n\\end{document}"
        if con_griglia:
            latex = inietta_griglia(latex, punti_totali)
        pdf, _ = compila_pdf(latex)
        return latex, pdf

    if tipo == "B":
        try:
            resp   = model_v.generate_content(prompt_versione_b(corpo_a))
        except Exception as e:
            raise RuntimeError(f"Variante B: {e}") from e
        corpo  = pulisci_corpo_latex(resp.text.replace("```latex","").replace("```","").strip())
        corpo  = _post(corpo)
        preamb = preamb_a.replace("Versione A", "Versione B")
        if "Versione B" not in preamb:
            preamb = re.sub(r"(Verifica[^\\]*?)(\\\\)", r"\1 — Versione B\2", preamb, count=1)
        latex, pdf = _compile(preamb + "\n" + corpo)
        return {**_vf(), "latex": latex, "pdf": pdf, "preview": bool(pdf),
                "latex_originale": latex}

    if tipo == "R":
        try:
            resp  = model_v.generate_content(
                prompt_versione_ridotta(corpo_a, materia, perc_ridotta,
                                        mostra_punteggi, punti_totali))
        except Exception as e:
            raise RuntimeError(f"Verifica ridotta: {e}") from e
        corpo = pulisci_corpo_latex(resp.text.replace("```latex","").replace("```","").strip())
        corpo = _post(corpo)
        latex, pdf = _compile(preamb_a + "\n" + corpo)
        return {**_vf(), "latex": latex, "pdf": pdf, "preview": bool(pdf),
                "latex_originale": latex}

    if tipo == "S":
        try:
            resp     = model_v.generate_content(prompt_soluzioni(corpo_a, materia))
        except Exception as e:
            raise RuntimeError(f"Soluzioni: {e}") from e
        testo    = resp.text.strip()
        titolo_s = "Soluzioni — " + materia + ": " + argomento
        latex_s  = (
            "\\documentclass[12pt,a4paper]{article}\n"
            "\\usepackage[utf8]{inputenc}\n"
            "\\usepackage[italian]{babel}\n"
            "\\usepackage{amsmath,amsfonts,amssymb,geometry}\n"
            "\\usepackage{fancyhdr}\n"
            "\\usepackage{lastpage}\n"
            "\\usepackage{xcolor}\n"
            "\\usepackage{tcolorbox}\n"
            "\\tcbuselibrary{skins,breakable}\n"
            "\\geometry{margin=2.5cm,top=3cm,bottom=3cm}\n"
            "\\pagestyle{fancy}\n"
            "\\fancyhf{}\n"
            "\\renewcommand{\\headrulewidth}{0pt}\n"
            "\\renewcommand{\\footrulewidth}{0pt}\n"
            "\\fancyhead[C]{{\\color{red!70!black}\\textbf{\\large SOLUZIONI - DOCUMENTO RISERVATO}}}\\\\\n"
            "\\fancyhead[C]{{\\small \\textit{" + materia + " - " + argomento + "}}}\\\\\n"
            "\\fancyhead[C]{{\\small Pagina \\thepage\\ di \\pagelast{}}}\n"
            "\\fancyfoot[C]{{\\tiny \\textit{Documento confidenziale - Vietata la distribuzione agli studenti}}}\n"
            "\\definecolor{solcolor}{RGB}{220,38,38}\n"
            "\\setlength{\\parindent}{0pt}\n"
            "\\setlength{\\parskip}{0.8em plus 0.3em minus 0.2em}\n"
            "\\begin{document}\n"
            "\\begin{center}\n"
            "  {\\color{solcolor}\\rule{\\textwidth}{2pt}} \\\\\[0.3cm]\n"
            "  {\\color{solcolor}\\textbf{\\LARGE " + titolo_s + "}} \\\\\[0.2cm]\n"
            "  {\\large \\textbf{\\textit{Documento Riservato al Docente}}} \\\\\[0.1cm]\n"
            "  {\\small \\textit{Vietata la distribuzione agli studenti}} \\\\\[0.4cm]\n"
            "  {\\color{solcolor}\\rule{\\textwidth}{1pt}} \\\\\[1cm]\n"
            "\\end{center}\n"
            + testo + "\n\\end{document}"
        )
        pdf_s, _ = compila_pdf(latex_s)
        return {"latex": latex_s, "pdf": pdf_s, "testo": testo}

    return {}


# ── Prompt costruzione esercizi ────────────────────────────────────────────────

def _build_prompt_esercizi(esercizi_custom, num_totale, punti_totali, mostra_punteggi):
    n_liberi = max(0, num_totale - len(esercizi_custom))
    righe = [
        f"STRUTTURA ESERCIZI — REGOLA ASSOLUTA:",
        f"Genera ESATTAMENTE {num_totale} esercizi.",
        f"Ogni esercizio è \\subsection*{{Esercizio N: Titolo}}.",
    ]
    immagini = []
    if mostra_punteggi and num_totale > 0:
        pts_b = punti_totali // num_totale
        resto = punti_totali - pts_b * num_totale
        pts   = [pts_b] * num_totale
        if resto: pts[0] += resto
        righe.append(
            f"DISTRIBUZIONE PUNTI — VINCOLO TASSATIVO:\n"
            f"Il punteggio totale della verifica DEVE essere ESATTAMENTE {punti_totali} pt.\n"
            f"REGOLA FONDAMENTALE: NON scrivere MAI il punteggio totale nell'intestazione\n"
            f"dell'esercizio (es. NO '(20pt)' dopo 'Esercizio 1: ...').\n"
            f"Assegna i punti SOLO ai singoli \\item o sottopunti (a), b), c) ecc.) in modo che\n"
            f"la somma sia ESATTAMENTE {punti_totali} pt. Non aggiungere, non togliere nemmeno 1 pt.\n"
            f"Indicazione di partenza (adattala liberamente ma rispetta il totale):"
        )
        for i in range(num_totale):
            righe.append(f"  - Esercizio {i+1}: circa {pts[i]} pt")
        righe.append(
            f"VERIFICA OBBLIGATORIA PRIMA DI RISPONDERE: somma tutti i (X pt) scritti "
            f"nel tuo output. Se la somma ≠ {punti_totali} pt, correggi i punti."
        )

    if not esercizi_custom:
        righe.append(
            f"PRIMO ESERCIZIO: 'Saperi Essenziali' — concetti base, NO simbolo (*)."
            f" Gli esercizi 2–{num_totale} approfondiscono."
        )
    righe.append(f"DETTAGLIO ({num_totale} totali):")
    for i, ex in enumerate(esercizi_custom, 1):
        tipo, desc = ex.get("tipo","Aperto"), ex.get("descrizione","").strip()
        riga = f"- Esercizio {i} [{tipo}]" + (f": {desc}" if desc else "")
        if ex.get("immagine"):
            riga += f" — usa immagine allegata"
            immagini.append({"idx": i, "data": ex["immagine"].getvalue(),
                             "mime_type": ex["immagine"].type})
        if tipo == "Scelta multipla":
            riga += " — \\begin{enumerate}[a)] \\item ... \\end{enumerate}"
        elif tipo == "Vero/Falso":
            riga += " — $\\square$ V $\\quad\\square$ F per ogni affermazione"
        elif tipo == "Completamento":
            riga += " — \\underline{\\hspace{3cm}} per gli spazi"
        righe.append(riga)
    if n_liberi > 0:
        s = len(esercizi_custom) + 1
        righe.append(f"- Esercizi {s}–{num_totale}: genera tu {n_liberi} esercizi coerenti.")
    return "\n".join(righe), immagini


# ═══════════════════════════════════════════════════════════════════════════════
#  SESSION STATE INIT
# ═══════════════════════════════════════════════════════════════════════════════

if "stage"             not in st.session_state: st.session_state.stage = STAGE_INPUT
if "verifiche"         not in st.session_state:
    st.session_state.verifiche = {
        "A": _vf(), "B": _vf(), "R": _vf(), "RB": _vf(),
        "S": {"latex": None, "testo": None, "pdf": None},
    }
if "review_preamble"   not in st.session_state: st.session_state.review_preamble = ""
if "review_blocks"     not in st.session_state: st.session_state.review_blocks = []
if "review_sel_idx"    not in st.session_state: st.session_state.review_sel_idx = 0
if "gen_params"        not in st.session_state: st.session_state.gen_params = {}
if "preview_images"    not in st.session_state: st.session_state.preview_images = []
if "preview_page"      not in st.session_state: st.session_state.preview_page = 0
if "last_preview_ts"   not in st.session_state: st.session_state.last_preview_ts = 0
if "esercizi_custom"   not in st.session_state: st.session_state.esercizi_custom = []
if "last_materia"      not in st.session_state: st.session_state.last_materia = None
if "last_argomento"    not in st.session_state: st.session_state.last_argomento = None
if "_storico_refresh"  not in st.session_state: st.session_state._storico_refresh = 0
if "_preferiti"        not in st.session_state: st.session_state._preferiti = set()
if "_storico_page"     not in st.session_state: st.session_state._storico_page = 1
if "_saved_to_storico" not in st.session_state: st.session_state._saved_to_storico = False
if "gen_time_sec"      not in st.session_state: st.session_state.gen_time_sec = None
# ── Idea #19: Rubrica valutazione ────────────────────────────────────────────
if "rubrica_testo"     not in st.session_state: st.session_state.rubrica_testo = None
if "_rubrica_gen"      not in st.session_state: st.session_state._rubrica_gen = False
if "_rubrica_pdf"      not in st.session_state: st.session_state["_rubrica_pdf"] = None
if "_rubrica_docx"     not in st.session_state: st.session_state["_rubrica_docx"] = None
# ── Idea #8: Template gallery ────────────────────────────────────────────────
if "_template_sel"     not in st.session_state: st.session_state._template_sel = None
# ── Idea #2: One-click variant state ─────────────────────────────────────────
if "_variant_rapida_gen" not in st.session_state: st.session_state._variant_rapida_gen = False
if "file_ispirazione"  not in st.session_state: st.session_state.file_ispirazione = None
if "mathpix_context"   not in st.session_state: st.session_state.mathpix_context = None
if "mathpix_file_hash" not in st.session_state: st.session_state.mathpix_file_hash = None
# Analisi documento caricato
if "analisi_doc"          not in st.session_state: st.session_state.analisi_doc = None
# Lista di analisi accumulate da più file: [{"file_name","file_hash","analisi","file_mode","confirmed"}, ...]
if "analisi_docs_list"    not in st.session_state: st.session_state.analisi_docs_list = []
# Stato info consolidate ricavate da tutti i file
if "info_consolidate"     not in st.session_state: st.session_state.info_consolidate = {}
# Istruzioni per file (key = file_hash → testo istruzione)
if "istruzioni_per_file"  not in st.session_state: st.session_state.istruzioni_per_file = {}
# Esercizi personalizzati da file (accumulo durante sessione)
if "_es_custom_da_file"   not in st.session_state: st.session_state["_es_custom_da_file"] = {}
# Percorso utente: None | "A" | "B"
if "input_percorso"       not in st.session_state: st.session_state.input_percorso = None
# Dialogo conferma Percorso A: None | "in_attesa" | "confermato"
if "dialogo_stato"        not in st.session_state: st.session_state.dialogo_stato = None
# Modalità uso file scelta dall'utente dopo il dialogo
if "file_mode"            not in st.session_state: st.session_state.file_mode = None
# Esercizio specifico da includere (testo estratto)
if "esercizio_da_includere" not in st.session_state: st.session_state.esercizio_da_includere = None
# QA mode (accessibile da entrambi i percorsi)
if "qa_mode"              not in st.session_state: st.session_state.qa_mode = False
if "qa_result"            not in st.session_state: st.session_state.qa_result = None
if "qa_file_hash"         not in st.session_state: st.session_state.qa_file_hash = None
# Preferenze docente (caricate da Supabase)
if "_docente_prefs"       not in st.session_state: st.session_state._docente_prefs = {}
# ── Idea #1: Preferenze silenti (materia, scuola, num_esercizi, punteggi) ────
if "_user_defaults"       not in st.session_state: st.session_state._user_defaults = None
if "_user_defaults_loaded" not in st.session_state: st.session_state._user_defaults_loaded = False
# ── Idea #5: Condivisione con dipartimento ──────────────────────────────────
if "_share_code"          not in st.session_state: st.session_state._share_code = None
if "_share_generating"    not in st.session_state: st.session_state._share_generating = False
# ── Idea #3: Quick regen state ──────────────────────────────────────────────
if "_quick_regen_idx"     not in st.session_state: st.session_state._quick_regen_idx = None
if "_facsimile_mode"        not in st.session_state: st.session_state["_facsimile_mode"]        = False
if "_fac_dialog_pending"   not in st.session_state: st.session_state["_fac_dialog_pending"]   = False
if "_fac_dialog_data"      not in st.session_state: st.session_state["_fac_dialog_data"]      = {}
if "_fac_dialog_shown_for" not in st.session_state: st.session_state["_fac_dialog_shown_for"] = None
if "_fac_confirmed"        not in st.session_state: st.session_state["_fac_confirmed"]        = False
if "_pers_open"           not in st.session_state: st.session_state["_pers_open"] = False
if "_pb_argomento_source"    not in st.session_state: st.session_state["_pb_argomento_source"] = None
if "_pb_argomento_manual_val" not in st.session_state: st.session_state["_pb_argomento_manual_val"] = ""
# Wizard state (Percorso A)
if "wizard_step"           not in st.session_state: st.session_state["wizard_step"] = "upload"
if "wizard_intent_pending" not in st.session_state: st.session_state["wizard_intent_pending"] = None

# ── Flag Mathpix (configurato solo se entrambe le chiavi sono in secrets) ─────
_MATHPIX_OK = (
    _MATHPIX_AVAILABLE and
    _mpx is not None and
    _mpx.is_configured(st.secrets)
)

# ── CONTATORI ─────────────────────────────────────────────────────────────────
_verifiche_mese = _get_verifiche_mese(st.session_state.utente.id) if st.session_state.utente else 0
_is_admin       = st.session_state.utente.email in ADMIN_EMAILS if st.session_state.utente else False
_limite         = (not _is_admin) and (_verifiche_mese >= LIMITE_MENSILE)

# ── CSS + FEEDBACK ────────────────────────────────────────────
st.markdown(get_css(T), unsafe_allow_html=True)

# ── JS fix expander open header ─────────────────────────────────
# st.markdown non esegue <script>. components.html usa un iframe sandbox con
# allow-same-origin che permette window.parent.document → accesso al DOM reale.
_theme_is_light = _is_light_color(T.get("bg", "#000000"))
_exp_fix_bg   = T.get("accent_light", "#E0F2FE")
_exp_fix_fg   = T.get("accent", "#0D9488")
_exp_fix_bdr  = T.get("accent", "#0D9488") + "44"
_btn_fix_bg   = T.get("card", T.get("bg2", "#FFFFFF"))
_btn_fix_fg   = T.get("text", "#0F1117")
_btn_fix_bdr  = T.get("border2", "#CDD1D9")
_is_lt        = "1" if _theme_is_light else ""
components.html(
    f'<script>'
    f'(function(){{'
    f'var p=window.parent,d=p&&p.document;'
    f'if(!d)return;'
    f'var isLight="{_is_lt}";'
    f'var ebg="{_exp_fix_bg}",efg="{_exp_fix_fg}",ebd="1px solid {_exp_fix_bdr}";'
    f'var btnBg="{_btn_fix_bg}",btnFg="{_btn_fix_fg}",btnBd="1.5px solid {_btn_fix_bdr}";'
    f'var ESEL=\'[data-testid="stExpander"] details[open]>summary,[data-testid="stExpander"][open]>summary\';'
    f'var BSEL=\'[data-testid="stButton"]>button,div.stButton>button\';'
    f'function fx(){{'
    f'if(isLight){{'
    # Fix expander open headers on light themes
    f'd.querySelectorAll(ESEL).forEach(function(e){{'
    f'e.style.setProperty("background",ebg,"important");'
    f'e.style.setProperty("background-color",ebg,"important");'
    f'e.style.setProperty("color",efg,"important");'
    f'e.style.setProperty("-webkit-text-fill-color",efg,"important");'
    f'e.style.setProperty("border-bottom",ebd,"important");'
    f'e.style.setProperty("border-radius","12px 12px 0 0","important");'
    f'}});'
    f'd.querySelectorAll(ESEL.split(",").map(function(s){{return s+" *";}}).join(",")).forEach(function(e){{'
    f'e.style.setProperty("color",efg,"important");'
    f'e.style.setProperty("-webkit-text-fill-color",efg,"important");'
    f'e.style.setProperty("background-color","transparent","important");'
    f'}});'
    # Fix ALL secondary buttons with aggressive inline styles
    f'var allSecBtns = d.querySelectorAll('
    f'  \'button[data-testid="stBaseButton-secondary"],'
    f'  \'button[kind="secondary"],'
    f'  \'div.stButton > button:not([kind="primary"]):not([data-testid*="primary"]),'
    f'  \'[data-testid="stButton"] > button:not([data-testid*="primary"])'
    f');'
    f'allSecBtns.forEach(function(e){{'
    f'  if(e.closest(\'[data-testid="stSidebar"]\'))return;'
    f'  var dt = (e.getAttribute("data-testid")||"").toLowerCase();'
    f'  var kd = (e.getAttribute("kind")||"").toLowerCase();'
    f'  if(dt.indexOf("primary")!==-1||kd==="primary")return;'
    f'  e.style.setProperty("background","{T.get("card", T["bg2"])}","important");'
    f'  e.style.setProperty("background-color","{T.get("card", T["bg2"])}","important");'
    f'  e.style.setProperty("color","{T["text"]}","important");'
    f'  e.style.setProperty("-webkit-text-fill-color","{T["text"]}","important");'
    f'  e.style.setProperty("border","1.5px solid {T["border2"]}","important");'
    f'  e.style.setProperty("border-radius","8px","important");'
    f'}});'
    # Fix download buttons
    f'd.querySelectorAll(\'div.stDownloadButton > button\').forEach(function(e){{'
    f'  if(e.closest(\'[data-testid="stSidebar"]\'))return;'
    f'  e.style.setProperty("color","{T.get("success","#059669")}","important");'
    f'  e.style.setProperty("-webkit-text-fill-color","{T.get("success","#059669")}","important");'
    f'}});'
    f'}}'
    f'}}'
    f'try{{new MutationObserver(fx).observe(d.body,{{subtree:true,attributes:true,childList:true}});}}catch(err){{}}'
    f'fx();setInterval(fx,300);'
    f'}})();'
    f'</script>',
    height=0,
    scrolling=False,
)
st.markdown(
    '<a class="fab-link" href="' + FEEDBACK_FORM_URL + '" target="_blank" '
    'rel="noopener noreferrer">💬 Feedback</a>',
    unsafe_allow_html=True
)

# ── ST_YLED — init + global styles ────────────────────────────────────────────
# Personalizza bottoni primari, input e form a livello globale via st_yled.set()
if _STYLED_AVAILABLE:
    try:
        _styl.init()
        # Pulsanti primari — colore coerente con il tema
        _styl.set("button", "border_radius", "12px")
        _styl.set("button", "font_size", "0.95rem")
        # Input
        _styl.set("text_input", "border_radius", "12px")
        _styl.set("text_area",  "border_radius", "12px")
    except Exception:
        pass

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
settings   = render_sidebar(
    supabase_admin=supabase_admin, utente=st.session_state.utente,
    verifiche_mese_count=_verifiche_mese, is_admin=_is_admin,
    limite_raggiunto=_limite, T=T, SCUOLE=SCUOLE,
    MODELLI_DISPONIBILI=MODELLI_DISPONIBILI, LIMITE_MENSILE=LIMITE_MENSILE,
    giorni_al_reset_func=_giorni_al_reset, compila_pdf_func=compila_pdf,
    supabase_client=supabase, current_stage=st.session_state.stage,
    THEMES=THEMES, THEME_LABELS=THEME_LABELS,
    extract_blocks_func=extract_blocks,
    pdf_to_images_func=pdf_to_images_bytes,
)
modello_id = settings.get("modello_id", "gemini-2.5-flash-lite")

# Se il tema è cambiato dalla sidebar, aggiorna T
if settings.get("theme_changed"):
    T = THEMES[st.session_state.theme]
    st.rerun()

# Flag per sapere se siamo sulla landing (usato da breadcrumb e header)
_on_landing = (
    st.session_state.stage == STAGE_INPUT
    and st.session_state.get("input_percorso") is None
)

# ── HEADER UNIFICATO — visibile solo sulla landing ────────────────────────────
if _on_landing:
    st.markdown(
        '<div class="site-header">'
        '  <a class="site-header-logo" href="/" target="_self">'
        '    <span class="site-header-icon">' + APP_ICON + '</span>'
        '    <span class="site-header-name">Verific<span class="site-header-ai">AI</span></span>'
        '    <span class="site-header-beta">Beta</span>'
        '  </a>'
        '</div>',
        unsafe_allow_html=True
    )









# ═══════════════════════════════════════════════════════════════════════════════
#  PREFERENZE DOCENTE — Supabase helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _carica_docente_preferenze(user_id: str, materia: str) -> dict:
    """
    Carica le preferenze salvate per una materia specifica.
    Ritorna {} se non trovate o se si verifica un errore.
    """
    try:
        res = supabase_admin.table("docente_preferenze") \
            .select("preferenze") \
            .eq("user_id", user_id) \
            .eq("materia", materia) \
            .limit(1).execute()
        if res.data:
            return res.data[0].get("preferenze") or {}
    except Exception as e:
        logger.warning("_carica_docente_preferenze failed for %s/%s: %s", user_id, materia, e)
    return {}


def _salva_docente_preferenze(materia: str, prefs: dict) -> None:
    """
    Salva/aggiorna le preferenze del docente per una materia (upsert).
    Operazione non bloccante — i fallimenti vengono silenziosamente loggati.
    """
    from datetime import datetime, timezone
    if not st.session_state.utente:
        return
    try:
        supabase_admin.table("docente_preferenze").upsert({
            "user_id":    st.session_state.utente.id,
            "materia":    materia,
            "preferenze": prefs,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }, on_conflict="user_id,materia").execute()
        # Aggiorna cache locale
        st.session_state._docente_prefs[materia] = prefs
    except Exception as e:
        logger.warning("_salva_docente_preferenze failed for %s: %s", materia, e)



# ═══════════════════════════════════════════════════════════════════════════════
#  IDEA #1 — PREFERENZE SILENTI (salva/carica defaults form utente)
# ═══════════════════════════════════════════════════════════════════════════════

def _load_user_defaults() -> dict:
    """
    Carica le preferenze form silenti dell'utente da Supabase.
    Chiave: user_id con materia='__defaults__'.
    Restituisce {} se non trovate.
    Viene chiamata UNA volta all'avvio e cachata in session_state.
    """
    if st.session_state._user_defaults_loaded:
        return st.session_state._user_defaults or {}
    if not st.session_state.utente:
        return {}
    try:
        res = supabase_admin.table("docente_preferenze") \
            .select("preferenze") \
            .eq("user_id", st.session_state.utente.id) \
            .eq("materia", "__defaults__") \
            .limit(1).execute()
        defaults = res.data[0].get("preferenze", {}) if res.data else {}
        st.session_state._user_defaults = defaults
        st.session_state._user_defaults_loaded = True
        return defaults
    except Exception as e:
        logger.warning("_load_user_defaults failed: %s", e)
        st.session_state._user_defaults_loaded = True
        return {}


def _save_user_defaults_silent(materia: str, scuola: str,
                                num_esercizi: int, mostra_punteggi: bool,
                                punti_totali: int) -> None:
    """
    Salva silenziosamente i defaults del form.
    Chiamata dopo ogni generazione o quando i campi cambiano.
    Non-blocking: errori ignorati.
    """
    from datetime import datetime, timezone
    if not st.session_state.utente:
        return
    defaults = {
        "materia": materia,
        "scuola": scuola,
        "num_esercizi": num_esercizi,
        "mostra_punteggi": mostra_punteggi,
        "punti_totali": punti_totali,
    }
    # Evita write se nulla è cambiato
    cached = st.session_state._user_defaults or {}
    if cached == defaults:
        return
    try:
        supabase_admin.table("docente_preferenze").upsert({
            "user_id":    st.session_state.utente.id,
            "materia":    "__defaults__",
            "preferenze": defaults,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }, on_conflict="user_id,materia").execute()
        st.session_state._user_defaults = defaults
    except Exception as e:
        logger.warning("_save_user_defaults failed: %s", e)


# ═══════════════════════════════════════════════════════════════════════════════
#  IDEA #5 — CONDIVISIONE CON IL DIPARTIMENTO
# ═══════════════════════════════════════════════════════════════════════════════

def _generate_share_code() -> str:
    """Genera un codice breve univoco per la condivisione (6 caratteri alfanumerici)."""
    import hashlib
    seed = f"{time.time()}-{st.session_state.utente.id}-{id(st.session_state)}"
    return hashlib.sha256(seed.encode()).hexdigest()[:8].upper()


def _create_share_link(latex_a: str, materia: str, argomento: str,
                        scuola: str, num_esercizi: int) -> str | None:
    """
    Salva la verifica nella tabella shared_verifiche e restituisce il codice.
    TTL: 30 giorni. Restituisce None in caso di errore.
    """
    from datetime import datetime, timezone, timedelta
    if not st.session_state.utente or not latex_a:
        return None
    code = _generate_share_code()
    try:
        now = datetime.now(timezone.utc)
        supabase_admin.table("shared_verifiche").insert({
            "short_code":    code,
            "user_id":       st.session_state.utente.id,
            "latex_a":       latex_a,
            "materia":       materia,
            "argomento":     argomento,
            "scuola":        scuola,
            "num_esercizi":  num_esercizi,
            "created_at":    now.isoformat(),
            "expires_at":    (now + timedelta(days=30)).isoformat(),
            "view_count":    0,
            "clone_count":   0,
        }).execute()
        return code
    except Exception as e:
        logger.warning("_generate_share_code / _create_share_record failed: %s", e)
        return None


def _load_shared_verifica(code: str) -> dict | None:
    """
    Carica una verifica condivisa dal codice. Restituisce il record o None.
    Incrementa il view_count.
    """
    try:
        res = supabase_admin.table("shared_verifiche") \
            .select("*") \
            .eq("short_code", code) \
            .limit(1).execute()
        if not res.data:
            return None
        record = res.data[0]
        # Incrementa view_count
        try:
            supabase_admin.table("shared_verifiche") \
                .update({"view_count": (record.get("view_count", 0) or 0) + 1}) \
                .eq("short_code", code).execute()
        except Exception:
            pass
        return record
    except Exception:
        return None


def _increment_clone_count(code: str) -> None:
    """Incrementa il contatore cloni per una verifica condivisa."""
    try:
        res = supabase_admin.table("shared_verifiche") \
            .select("clone_count") \
            .eq("short_code", code) \
            .limit(1).execute()
        current = res.data[0].get("clone_count", 0) if res.data else 0
        supabase_admin.table("shared_verifiche") \
            .update({"clone_count": (current or 0) + 1}) \
            .eq("short_code", code).execute()
    except Exception:
        pass



# ═══════════════════════════════════════════════════════════════════════════════
#  QA SECTION — "Verifica la tua Verifica"
# ═══════════════════════════════════════════════════════════════════════════════

def _render_qa_section():
    """
    Modalità QA: carica una verifica già preparata e ottieni un report critico.
    Accessibile dal bivio come percorso separato.
    """
    st.markdown(
        f'<div style="background:linear-gradient(135deg,{T["card2"]},{T["card"]});'
        f'border:2px solid {T["border2"]};border-radius:14px;'
        f'padding:.9rem 1.1rem;margin-bottom:1rem;">'
        f'<div style="font-size:.9rem;font-weight:800;color:{T["accent"]};'
        f'font-family:DM Sans,sans-serif;margin-bottom:.3rem;">🔍 Verifica la tua Verifica</div>'
        f'<p style="font-size:.76rem;color:{T["text2"]};margin:0;line-height:1.5;'
        f'font-family:DM Sans,sans-serif;">'
        f'Carica una verifica già preparata: l\'AI la leggerà e ti darà un report '
        f'dettagliato su errori matematici, domande ambigue, distribuzione dei punti '
        f'e adeguatezza al livello scolastico.'
        f'</p>'
        f'</div>',
        unsafe_allow_html=True
    )

    _qa_col1, _qa_col2 = st.columns(2)
    with _qa_col1:
        _mat_list = MATERIE + ["Non specificata"]
        _qa_mat = st.selectbox(
            "Materia (opzionale)", _mat_list, index=len(_mat_list)-1,
            key="qa_materia", label_visibility="collapsed",
            help="Specifica la materia per un'analisi più precisa",
        )
    with _qa_col2:
        _scu_list = SCUOLE + ["Non specificato"]
        _qa_scu = st.selectbox(
            "Livello scolastico (opzionale)", _scu_list, index=len(_scu_list)-1,
            key="qa_scuola", label_visibility="collapsed",
        )

    qa_file = st.file_uploader(
        "Carica la verifica da analizzare",
        type=["pdf", "png", "jpg", "jpeg"],
        key="qa_file_upload",
        label_visibility="collapsed",
        help="PDF o immagine della verifica. Max ~10 MB.",
    )

    qa_btn = st.button(
        "🔍 Analizza errori e qualità",
        use_container_width=True,
        disabled=not qa_file,
        key="qa_btn",
    )

    qa_result     = st.session_state.get("qa_result")
    qa_result_hash = st.session_state.get("qa_file_hash")

    if qa_btn and qa_file:
        _qa_hash = hash(qa_file.getvalue())
        if _qa_hash != qa_result_hash:
            with st.spinner("🔍 Analisi in corso… (può richiedere 15–30 secondi)"):
                try:
                    _qa_mat_v = _qa_mat if _qa_mat != "Non specificata" else ""
                    _qa_scu_v = _qa_scu if _qa_scu != "Non specificato" else ""
                    _qa_model = genai.GenerativeModel(modello_id)
                    _qa_inp   = [
                        prompt_qa_verifica(materia=_qa_mat_v, livello=_qa_scu_v),
                        {"mime_type": qa_file.type or "image/png",
                         "data": qa_file.getvalue()},
                    ]
                    _qa_resp  = _qa_model.generate_content(_qa_inp)
                    st.session_state.qa_result    = _qa_resp.text.strip()
                    st.session_state.qa_file_hash = _qa_hash
                    st.rerun()
                except Exception as _qe:
                    st.error(f"❌ Analisi non riuscita: {_qe}")

    if qa_result:
        st.markdown("---")
        st.markdown(
            f'<div style="font-size:.8rem;font-weight:700;color:{T["text2"]};'
            f'font-family:DM Sans,sans-serif;margin-bottom:.4rem;">REPORT DI REVISIONE</div>',
            unsafe_allow_html=True
        )
        st.markdown(qa_result)
        st.download_button(
            "⬇️ Scarica report (.txt)",
            data=qa_result.encode("utf-8"),
            file_name="report_verifica.txt",
            mime="text/plain",
            key="qa_download",
            use_container_width=True,
        )
        if st.button("✕ Nuova analisi", key="qa_reset", use_container_width=True):
            st.session_state.qa_result    = None
            st.session_state.qa_file_hash = None
            st.rerun()

    # ── Torna al menu (fondo pagina) ─────────────────────────────────────────
    st.markdown("<div style='height:.8rem'></div>", unsafe_allow_html=True)
    if _render_back_button("← Torna al menu", key="btn_back_qa"):
        st.session_state.qa_mode = False
        st.session_state.input_percorso = None
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
#  HELPERS — PERCORSO A/B
# ═══════════════════════════════════════════════════════════════════════════════

def _reset_percorso():
    """Reset completo del Percorso A (upload). Non tocca gen_params."""
    st.session_state.input_percorso        = None
    st.session_state.dialogo_stato         = None
    st.session_state.file_mode             = None
    st.session_state.analisi_doc           = None
    st.session_state.analisi_docs_list     = []
    st.session_state.info_consolidate      = {}
    st.session_state.istruzioni_per_file   = {}
    st.session_state["_es_custom_da_file"] = {}
    st.session_state.esercizio_da_includere = None
    st.session_state.file_ispirazione      = None
    st.session_state.mathpix_context       = None
    st.session_state.mathpix_file_hash     = None
    # Wizard state
    st.session_state["wizard_step"]         = "upload"
    st.session_state["wizard_intent_pending"] = None


def _esegui_analisi_documento(file_bytes: bytes, mime_type: str, file_name: str):
    """
    Lancia analisi AI sul file e popola st.session_state.analisi_doc.
    Gestisce OCR Mathpix se disponibile.
    Chiama st.rerun() alla fine per aggiornare il dialogo.
    """
    file_hash = hash(file_bytes)
    ad = st.session_state.analisi_doc or {}
    if ad.get("file_hash") == file_hash:
        return  # già analizzato — evita ri-analisi su rerun

    # Mathpix OCR (non bloccante)
    mathpix_ctx = None
    if _MATHPIX_OK and file_hash != st.session_state.mathpix_file_hash:
        try:
            mathpix_ctx = _mpx.ocr_file(
                file_bytes=file_bytes, mime_type=mime_type, secrets=st.secrets
            )
            st.session_state.mathpix_context   = mathpix_ctx
            st.session_state.mathpix_file_hash = file_hash
        except Exception:
            mathpix_ctx = st.session_state.get("mathpix_context")
    else:
        mathpix_ctx = st.session_state.get("mathpix_context")

    # Analisi AI metadati — usa sempre Flash Lite (task leggero ed economico)
    try:
        _model_fast = genai.GenerativeModel(MODEL_FAST_ID)
        result = analizza_documento_caricato(
            model=_model_fast,
            file_bytes=file_bytes,
            mime_type=mime_type,
            mathpix_context=mathpix_ctx,
            materie_valide=MATERIE,
        )
        result["file_hash"] = file_hash
        result["file_name"] = file_name

        # ── GUARDRAIL: file non pertinente ────────────────────────────────────
        if not result.get("pertinente", True):
            # Segna il documento come non pertinente ma NON lo aggiunge alla lista.
            # Salviamo il messaggio di rifiuto in un key temporaneo per mostrarlo nell'UI.
            st.session_state["_analisi_rifiuto"] = {
                "file_name": file_name,
                "messaggio": result.get("messaggio_rifiuto")
                    or "Questo file non sembra materiale scolastico. "
                       "Carica una verifica, appunti, un capitolo del libro o una foto della lavagna.",
            }
            st.rerun()

        st.session_state.analisi_doc    = result
        st.session_state.dialogo_stato  = "in_attesa"
        st.session_state.file_mode      = result.get("modalita_uso_consigliata", "stile_e_struttura")

        # Pre-popola scuola se rilevata
        if result.get("scuola") and result["scuola"] in SCUOLE:
            st.session_state._analisi_scuola = result["scuola"]

        # Pre-popola materia preferenze Supabase
        if result.get("materia") and result["materia"] in MATERIE and st.session_state.utente:
            prefs = _carica_docente_preferenze(st.session_state.utente.id, result["materia"])
            st.session_state._docente_prefs[result["materia"]] = prefs

        # ── Aggiorna lista multi-file ─────────────────────────────────────────
        # Aggiunge alla lista se non già presente (by hash); lo marca come
        # "in attesa di conferma" (confirmed=False).
        _existing_hashes = {d["file_hash"] for d in st.session_state.analisi_docs_list}
        if file_hash not in _existing_hashes:
            st.session_state.analisi_docs_list.append({
                "file_hash":  file_hash,
                "file_name":  file_name,
                "file_bytes": file_bytes,   # ← bytes grezzi per vision AI
                "mime_type":  mime_type,    # ← mime per vision AI
                "analisi":    result,
                "file_mode":  result.get("modalita_uso_consigliata", "stile_e_struttura"),
                "confirmed":  False,   # attende conferma modalità
            })
        # Retrocompatibilità: slot singolo usato da compila_contesto_generazione
        st.session_state.analisi_doc = result
        _consolida_info()

        # ── Proposta facsimile: se è una verifica con alta confidence → apri dialog ─
        _is_verifica_ai = (
            result.get("tipo_documento") == "verifica"
            and float(result.get("confidence", 0)) >= 0.70
            and st.session_state.get("_fac_dialog_shown_for") != file_hash
        )
        if _is_verifica_ai:
            st.session_state["_fac_dialog_pending"] = True
            st.session_state["_fac_dialog_data"]    = result
            st.session_state["_fac_dialog_shown_for"] = file_hash

        # ── Prepara toast da mostrare al prossimo render ────────────────────────
        _det_materia = result.get("materia", "")
        _det_arg     = result.get("contenuto_argomento", "")
        _det_tipo    = result.get("tipo_documento", "")
        _toast_parts = []
        if _det_materia:
            _toast_parts.append(f"**Materia:** {_det_materia}")
        if _det_arg:
            _short_arg = _det_arg[:60] + "…" if len(_det_arg) > 60 else _det_arg
            _toast_parts.append(f"**Argomento:** {_short_arg}")
        if _det_tipo and _det_tipo != "verifica":
            _toast_parts.append(f"**Tipo:** {_det_tipo.replace('_', ' ').title()}")
        st.session_state["_toast_analisi"] = " · ".join(_toast_parts) if _toast_parts else "Documento analizzato."

        st.rerun()
    except Exception as e:
        st.warning(f"⚠️ Analisi non riuscita: {e}. Compila i campi manualmente.", icon="🔬")


def _compute_file_tags(analisi: dict) -> list:
    """Restituisce una lista di tag descrittivi (max 6) derivati dall'analisi AI del file."""
    tags = []
    tipo = analisi.get("tipo_documento", "")
    _tipo_map = {
        "verifica": ("📋", "Verifica", "tipo"),
        "appunti": ("📒", "Appunti", "tipo"),
        "libro": ("📚", "Libro", "tipo"),
        "esercizi_sciolti": ("📝", "Esercizi", "tipo"),
        "esercizio_singolo": ("✏️", "Esercizio", "tipo"),
        "misto": ("📄", "Misto", "tipo"),
    }
    if tipo in _tipo_map:
        icon, label, kind = _tipo_map[tipo]
        tags.append((icon, label, kind))

    tipi_domande = analisi.get("tipi_domande") or []
    for td in tipi_domande:
        if td == "Aperto":
            tags.append(("💬", "Aperto", "content"))
        elif td == "Scelta multipla":
            tags.append(("🔘", "Quiz", "content"))
        elif td == "Vero/Falso":
            tags.append(("✔", "V/F", "content"))
        elif td == "Completamento":
            tags.append(("✍️", "Completamento", "content"))

    stile = (analisi.get("stile_desc") or "").lower()
    if any(w in stile for w in ("teoria", "definizione", "concetto", "spiegazione")):
        tags.append(("📖", "Teoria", "content"))
    elif any(w in stile for w in ("sintesi", "riassunto", "schema", "mappa")):
        tags.append(("🗂️", "Sintesi", "content"))

    if analisi.get("ha_formule"):
        tags.append(("∑", "Formule", "formula"))
    if analisi.get("ha_grafici"):
        tags.append(("📈", "Grafici", "grafico"))

    return tags[:6]


def _consolida_info():
    """
    Ricalcola info_consolidate da tutti i file in analisi_docs_list.
    Priorità: file_mode confermato > ordine inserimento.
    Campi chiave: argomento, scuola, materia.
    """
    lista = st.session_state.analisi_docs_list
    merged: dict = {}
    for entry in lista:
        a = entry.get("analisi", {})
        # Priorità: prendi il primo valore non-vuoto trovato
        for campo in ("materia", "scuola", "contenuto_argomento",
                      "stile_desc", "tipi_domande", "ha_grafici",
                      "ha_formule", "num_esercizi_rilevati", "tipo_documento"):
            if campo not in merged or not merged[campo]:
                v = a.get(campo)
                if v:
                    merged[campo] = v
    # Scuola dalla chiave dedicata (più affidabile)
    if st.session_state.get("_analisi_scuola"):
        merged["scuola"] = st.session_state._analisi_scuola
    st.session_state.info_consolidate = merged


def _render_bivio():
    """
    Home page: logo + titolo MOLTO GRANDE centrato, un solo CTA.
    """

    # ── Logo + headline unificati, tutto centrato ─────────────────────────────
    st.markdown(
        f'''
        <div class="landing-hero-unified">
                    <h2 class="landing-headline-xl">
            Crea verifiche professionali<br>
            <span class="landing-headline-accent-xl">in pochi secondi</span>
          </h2>
          <p class="landing-sub-xl">
            Scegli materia, livello e argomento.<br>
            L'AI costruisce la verifica, tu la revisioni e scarichi.
          </p>
        </div>
        ''',
        unsafe_allow_html=True,
    )

    # ── CTA principale — più prominente ─────────────────────────────────────────────
    st.markdown('<div style="margin: 3rem 0;"></div>', unsafe_allow_html=True)
    _c1, _c2, _c3 = st.columns([1, 2.5, 1])
    with _c2:
        st.markdown(
            '''
            <div class="cta-genera-wrap">
            ''',
            unsafe_allow_html=True,
        )
        if st.button(
            "🚀 Crea Verifica Ora",
            key="btn_genera_verifica_home",
            use_container_width=True,
            type="primary",
            help="Scegli materia e argomento, crea in 30 secondi",
        ):
            st.session_state.input_percorso = "B"
            st.rerun()
        st.markdown(
            '''
            </div>
            ''',
            unsafe_allow_html=True,
        )

    # ── Feature pills — più leggibili per docenti ───────────────────────────────
    st.markdown('<div style="margin: 2rem 0;"></div>', unsafe_allow_html=True)
    st.markdown(
        '''<div style="text-align:center;margin-bottom:1.6rem;">
          <div class="landing-section-kicker">Tutto quello di cui hai bisogno</div>
          <div class="landing-section-title">Una verifica completa, subito</div>
        </div>''',
        unsafe_allow_html=True,
    )
    st.markdown(
        '''
        <div class="tally-features" style="gap: 14px; flex-wrap: wrap; justify-content: center;">
          <span class="tally-feat-pill" style="background: #f0f9ff; color: #0369a1; padding: 10px 18px; font-weight: 600;">
            📄 PDF Stampabile
          </span>
          <span class="tally-feat-pill" style="background: #f0f9ff; color: #0369a1; padding: 10px 18px; font-weight: 600;">
            🎲 Fila A e B
          </span>
          <span class="tally-feat-pill" style="background: #f0f9ff; color: #0369a1; padding: 10px 18px; font-weight: 600;">
            ⭐ Versione BES
          </span>
          <span class="tally-feat-pill" style="background: #f0f9ff; color: #0369a1; padding: 10px 18px; font-weight: 600;">
            ✏️ DOCX Modificabile
          </span>
          <span class="tally-feat-pill" style="background: #f0f9ff; color: #0369a1; padding: 10px 18px; font-weight: 600;">
            📋 Soluzioni
          </span>
          <span class="tally-feat-pill" style="background: #f0f9ff; color: #0369a1; padding: 10px 18px; font-weight: 600;">
            📊 Griglia Valutazione
          </span>
        </div>
        ''',
        unsafe_allow_html=True,
    )

    # ── Feature cards ─────────────────────────────────────

    # ── Feature cards — 6 card, 2 righe ─────────────────────────────────────
    st.markdown("<div style='height:3rem'></div>", unsafe_allow_html=True)
    
    # Sezione Dashboard (prima degli esempi)
    st.markdown("---")
    st.markdown('<div style="margin: 1rem 0;"></div>', unsafe_allow_html=True)
    
    st.markdown(
        """
        <div style="text-align: center; margin-bottom: 2.5rem;">
            <h2 style="font-size: 1.8rem; font-weight: 700; color: #1f2937; margin-bottom: 0.5rem;">
                📊 Il Tuo Dashboard
            </h2>
            <p style="font-size: 1.1rem; color: #6b7280;">
                Gestisci e visualizza tutte le tue verifiche create
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    # Stats cards con dati reali (3 colonne)
    stats = _get_verifiche_stats()
    col1, col2, col3 = st.columns(3, gap="large")
    
    with col1:
        st.markdown(
            f"""
            <div style="
                background: linear-gradient(135deg, #3b82f6, #1d4ed8);
                border-radius: 16px;
                padding: 2rem;
                text-align: center;
                color: white;
                box-shadow: 0 8px 25px -5px rgba(59, 130, 246, 0.3);
                cursor: pointer;
                transition: transform 0.2s, box-shadow 0.2s;
            " onmouseover="this.style.transform='translateY(-4px)'; this.style.boxShadow='0 12px 35px -5px rgba(59, 130, 246, 0.4)'" onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 8px 25px -5px rgba(59, 130, 246, 0.3)'">
                <div style="font-size: 2.5rem; font-weight: 700; margin-bottom: 0.5rem;">
                    📄
                </div>
                <div style="font-size: 2rem; font-weight: 700; margin-bottom: 0.5rem;">
                    {stats['totali']}
                </div>
                <div style="font-size: 1rem; opacity: 0.9;">
                    Verifiche Generate
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    
    with col2:
        st.markdown(
            f"""
            <div style="
                background: linear-gradient(135deg, #10b981, #059669);
                border-radius: 16px;
                padding: 2rem;
                text-align: center;
                color: white;
                box-shadow: 0 8px 25px -5px rgba(16, 185, 129, 0.3);
            ">
                <div style="font-size: 2.5rem; font-weight: 700; margin-bottom: 0.5rem;">
                    📚
                </div>
                <div style="font-size: 2rem; font-weight: 700; margin-bottom: 0.5rem;">
                    {stats['materie']}
                </div>
                <div style="font-size: 1rem; opacity: 0.9;">
                    Materie Coperte
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    
    with col3:
        st.markdown(
            f"""
            <div style="
                background: linear-gradient(135deg, #f59e0b, #d97706);
                border-radius: 16px;
                padding: 2rem;
                text-align: center;
                color: white;
                box-shadow: 0 8px 25px -5px rgba(245, 158, 11, 0.3);
            ">
                <div style="font-size: 2.5rem; font-weight: 700; margin-bottom: 0.5rem;">
                    ✏️
                </div>
                <div style="font-size: 2rem; font-weight: 700; margin-bottom: 0.5rem;">
                    {stats['esercizi_totali']}
                </div>
                <div style="font-size: 1rem; opacity: 0.9;">
                    Esercizi Generati
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    
    # Pulsante per andare alla pagina delle verifiche
    st.markdown('<div style="text-align: center; margin-top: 2.5rem;">', unsafe_allow_html=True)
    if st.button("📄 Gestisci Le Tue Verifiche →", type="primary", use_container_width=True):
        st.session_state.stage = STAGE_MIE_VERIFICHE
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div style="margin: 2rem 0;"></div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
#  _render_facsimile_dedicato()  ← NUOVA funzione, aggiungere prima di _render_stage_input
# ═══════════════════════════════════════════════════════════════════════════════


def _load_user_verifiche():
    """
    Carica tutte le verifiche dell'utente da Supabase
    """
    if not st.session_state.utente:
        return []
    
    try:
        res = supabase_admin.table("verifiche_storico")\
            .select("*")\
            .eq("user_id", st.session_state.utente.id)\
            .order("created_at", desc=True)\
            .execute()
        
        return res.data if res.data else []
    except Exception as e:
        st.error(f"⚠️ Errore nel caricamento delle verifiche: {e}")
        return []

def _rinomina_verifica(verifica_id: int, nuovo_nome: str):
    """
    Rinomina una verifica nel database
    """
    try:
        res = supabase_admin.table("verifiche_storico")\
            .update({"argomento": nuovo_nome})\
            .eq("id", verifica_id)\
            .execute()
        
        return res.data if res.data else None
    except Exception as e:
        st.error(f"⚠️ Errore rinomina: {e}")
        return None

def _toggle_preferito(verifica_id: int, is_preferito: bool):
    """
    Aggiunge/rimuove una verifica dai preferiti
    """
    # TEMPORANEAMENTE DISABILITATO - la colonna 'preferito' non esiste nel database
    st.warning("⚠️ Funzionalità preferiti in sviluppo - colonna database mancante")
    return None

def _genera_link_condivisione(verifica_id: int):
    """
    Genera un link di condivisione per una verifica
    """
    try:
        # Carica la verifica
        res = supabase_admin.table("verifiche_storico")\
            .select("*")\
            .eq("id", verifica_id)\
            .eq("user_id", st.session_state.utente.id)\
            .limit(1)\
            .execute()
        
        if not res.data:
            return None
        
        verifica = res.data[0]
        
        # Genera codice di condivisione
        code = _generate_share_code()
        
        # Salva nella tabella shared_verifiche (solo campi base che sicuramente esistono)
        supabase_admin.table("shared_verifiche").insert({
            "short_code": code,
            "user_id": st.session_state.utente.id,
            "latex_a": verifica.get("latex_a"),
            # Rimossi tutti i campi che potrebbero non esistere:
            # latex_b, latex_r, materia, argomento, scuola, num_esercizi, modello, percorso_scelto
        }).execute()
        
        return f"{SHARE_URL}?share={code}"
        
    except Exception as e:
        st.error(f"⚠️ Errore generazione link: {e}")
        return None

def _get_verifiche_stats():
    """
    Calcola le statistiche delle verifiche dell'utente
    """
    verifiche = _load_user_verifiche()
    
    if not verifiche:
        return {
            "totali": 0,
            "questo_mese": 0,
            "materie": set(),
            "esercizi_totali": 0,
            "qualita_media": 0.0
        }
    
    now = datetime.now(timezone.utc)
    primo_mese = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    materie = set()
    questo_mese_count = 0
    esercizi_totali = 0
    
    for v in verifiche:
        if v.get("materia"):
            materie.add(v["materia"])
        
        # Somma esercizi
        if v.get("num_esercizi"):
            esercizi_totali += v["num_esercizi"]
        
        # Conta verifiche di questo mese
        created_at = v.get("created_at")
        if created_at:
            try:
                created_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                if created_dt >= primo_mese:
                    questo_mese_count += 1
            except:
                pass
    
    return {
        "totali": len(verifiche),
        "questo_mese": questo_mese_count,
        "materie": len(materie),
        "esercizi_totali": esercizi_totali,
        "qualita_media": 4.8  # Placeholder - si può calcolare da feedback reali
    }

def _render_le_tue_verifiche():
    """
    Pagina "Le tue verifiche" - Gestione verifiche create dall'utente
    """
    # Pulsante per tornare indietro
    col_back, col_center = st.columns([1, 4])
    with col_back:
        if st.button("← Torna Indietro", key="back_from_mie_verifiche", 
                     help="Torna alla pagina principale"):
            st.session_state.stage = STAGE_INPUT
            st.session_state.input_percorso = None
            st.rerun()
    
    st.markdown(
        """
        <div style="text-align: center; margin-bottom: 2rem;">
            <h1 style="font-size: 2.5rem; font-weight: 700; color: #1f2937; margin-bottom: 0.5rem;">
                📄 Le Tue Verifiche
            </h1>
            <p style="font-size: 1.2rem; color: #6b7280;">
                Gestisci, visualizza e scarica tutte le verifiche che hai creato
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    # Carica dati reali
    stats = _get_verifiche_stats()
    verifiche = _load_user_verifiche()
    
    # Stats in alto con dati reali
    col1, col2, col3, col4 = st.columns(4, gap="small")
    
    with col1:
        st.markdown(
            f"""
            <div style="
                background: linear-gradient(135deg, #3b82f6, #1d4ed8);
                border-radius: 12px;
                padding: 1.5rem;
                text-align: center;
                color: white;
            ">
                <div style="font-size: 2rem; font-weight: 700;">{stats['totali']}</div>
                <div style="font-size: 0.9rem; opacity: 0.9;">Totali</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    
    with col2:
        st.markdown(
            f"""
            <div style="
                background: linear-gradient(135deg, #10b981, #059669);
                border-radius: 12px;
                padding: 1.5rem;
                text-align: center;
                color: white;
            ">
                <div style="font-size: 2rem; font-weight: 700;">{stats['questo_mese']}</div>
                <div style="font-size: 0.9rem; opacity: 0.9;">Questo mese</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    
    with col3:
        st.markdown(
            f"""
            <div style="
                background: linear-gradient(135deg, #f59e0b, #d97706);
                border-radius: 12px;
                padding: 1.5rem;
                text-align: center;
                color: white;
            ">
                <div style="font-size: 2rem; font-weight: 700;">{stats['materie']}</div>
                <div style="font-size: 0.9rem; opacity: 0.9;">Materie</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    
    with col4:
        st.markdown(
            f"""
            <div style="
                background: linear-gradient(135deg, #8b5cf6, #7c3aed);
                border-radius: 12px;
                padding: 1.5rem;
                text-align: center;
                color: white;
            ">
                <div style="font-size: 2rem; font-weight: 700;">{stats['qualita_media']}</div>
                <div style="font-size: 0.9rem; opacity: 0.9;">Qualità</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    
    st.markdown("---")
    
    # Filtri e ricerca
    col_search, col_materia, col_ordine = st.columns([3, 2, 2])
    
    with col_search:
        search_query = st.text_input("🔍 Cerca verifica...", placeholder="Cerca per materia, argomento...")
    
    # Materie uniche dalle verifiche reali
    materie_real = ["Tutte"] + sorted(list(set([v.get("materia", "Sconosciuta") for v in verifiche if v.get("materia")])))
    with col_materia:
        materia_filter = st.selectbox("📚 Materia", materie_real)
    
    with col_ordine:
        ordine_filter = st.selectbox("📅 Ordina per", ["Più recenti", "Più vecchie", "Alfabetico", "Materia"])
    
    # Filtra le verifiche
    verifiche_filtrate = verifiche.copy()
    
    if search_query:
        verifiche_filtrate = [v for v in verifiche_filtrate if 
            search_query.lower() in v.get("materia", "").lower() or 
            search_query.lower() in v.get("argomento", "").lower()]
    
    if materia_filter != "Tutte":
        verifiche_filtrate = [v for v in verifiche_filtrate if v.get("materia") == materia_filter]
    
    # Ordina le verifiche
    if ordine_filter == "Più recenti":
        verifiche_filtrate.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    elif ordine_filter == "Più vecchie":
        verifiche_filtrate.sort(key=lambda x: x.get("created_at", ""))
    elif ordine_filter == "Alfabetico":
        verifiche_filtrate.sort(key=lambda x: x.get("argomento", ""))
    elif ordine_filter == "Materia":
        verifiche_filtrate.sort(key=lambda x: x.get("materia", ""))
    
    # Mostra verifiche reali
    if verifiche_filtrate:
        for i, verifica in enumerate(verifiche_filtrate):
            # Formatta data
            data_formattata = "Data non disponibile"
            if verifica.get("created_at"):
                try:
                    created_dt = datetime.fromisoformat(verifica["created_at"].replace('Z', '+00:00'))
                    data_formattata = created_dt.strftime("%d/%m/%Y")
                except:
                    pass
            
            with st.container():
                # Header della verifica
                st.markdown(
                    f"""
                    <div style="
                        background: white;
                        border: 1px solid #e5e7eb;
                        border-radius: 12px;
                        padding: 1.5rem;
                        margin-bottom: 1rem;
                        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
                        transition: box-shadow 0.2s;
                    " onmouseover="this.style.boxShadow='0 4px 12px rgba(0, 0, 0, 0.15)'" onmouseout="this.style.boxShadow='0 1px 3px rgba(0, 0, 0, 0.1)'">
                        <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 1rem;">
                            <div>
                                <h3 style="font-size: 1.3rem; font-weight: 600; color: #1f2937; margin: 0 0 0.5rem 0;">
                                    {verifica.get('argomento', 'Verifica senza titolo')}
                                </h3>
                                <div style="display: flex; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 0.5rem;">
                                    <span style="background: #eff6ff; color: #1d4ed8; padding: 0.25rem 0.75rem; border-radius: 20px; font-size: 0.8rem; font-weight: 500;">
                                        📚 {verifica.get('materia', 'Sconosciuta')}
                                    </span>
                                    <span style="background: #f0fdf4; color: #059669; padding: 0.25rem 0.75rem; border-radius: 20px; font-size: 0.8rem; font-weight: 500;">
                                        🏫 {verifica.get('scuola', 'Non specificata')}
                                    </span>
                                    <span style="background: #fefce8; color: #ca8a04; padding: 0.25rem 0.75rem; border-radius: 20px; font-size: 0.8rem; font-weight: 500;">
                                        📝 {verifica.get('num_esercizi', '?')} esercizi
                                    </span>
                                    <span style="background: #f3f4f6; color: #6b7280; padding: 0.25rem 0.75rem; border-radius: 20px; font-size: 0.8rem; font-weight: 500;">
                                        📅 {data_formattata}
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                
                # Tutti i bottoni su una sola riga
                col1, col2, col3, col4, col5, col6, col7 = st.columns([1, 1, 1, 1, 1, 1, 1])
                
                with col1:
                    if st.button(f"👁️ Anteprima", key=f"preview_{verifica.get('id')}_{i}"):
                        if verifica.get("latex_a"):
                            # Compila PDF per anteprima
                            try:
                                pdf_bytes, error = compila_pdf(verifica["latex_a"])
                                if pdf_bytes:
                                    # Converti in immagini per anteprima
                                    images, _ = pdf_to_images_bytes(pdf_bytes)
                                    if images:
                                        st.success("📄 Anteprima generata!")
                                        
                                        # Mostra anteprima in un container
                                        with st.expander("📄 Anteprima Verifica", expanded=True):
                                            for j, img in enumerate(images[:3]):  # Max 3 pagine
                                                st.image(img, caption=f"Pagina {j+1}", use_container_width=True)
                                    else:
                                        st.error("⚠️ Impossibile generare anteprima immagini")
                                else:
                                    st.error(f"⚠️ Errore compilazione PDF: {error}")
                                    # Fallback: mostra codice LaTeX con opzione di copia
                                    st.info("📝 Mostro il codice LaTeX come alternativa:")
                                    
                                    with st.expander("📄 Codice LaTeX (clicca per espandere)", expanded=False):
                                        latex_code = verifica["latex_a"]
                                        st.code(latex_code, language="latex", line_numbers=False)
                                        
                                        # Pulsanti per copiare e scaricare
                                        col1, col2 = st.columns(2)
                                        with col1:
                                            if st.button("📋 Copia LaTeX", key=f"copy_latex_{verifica.get('id')}_{i}"):
                                                st.write("Codice LaTeX copiato negli appunti!")
                                                st.code(latex_code)
                                        with col2:
                                            st.download_button(
                                                "💾 Scarica .tex",
                                                data=latex_code,
                                                file_name=f"verifica_{verifica.get('argomento', 'verifica')}.tex",
                                                mime="text/plain",
                                                key=f"download_tex_{verifica.get('id')}_{i}"
                                            )
                            except Exception as e:
                                st.error(f"⚠️ Errore anteprima: {e}")
                        else:
                            st.warning("⚠️ Contenuto LaTeX non disponibile per questa verifica")
                
                with col2:
                    pdf_disabled = not LATEX_AVAILABLE
                    pdf_help = "Non disponibile: LaTeX non è installato" if pdf_disabled else "Scarica la verifica in formato PDF"
                    
                    if st.button(f"📄 Scarica PDF", key=f"download_{verifica.get('id')}_{i}", 
                                 disabled=pdf_disabled, help=pdf_help):
                        if verifica.get("latex_a"):
                            try:
                                pdf_bytes, error = compila_pdf(verifica["latex_a"])
                                if pdf_bytes:
                                    # Nome file
                                    filename = f"{verifica.get('argomento', 'verifica').replace(' ', '_').replace('/', '_')}_{data_formattata.replace('/', '')}.pdf"
                                    st.download_button(
                                        label="⬇️ Click per scaricare",
                                        data=pdf_bytes,
                                        file_name=filename,
                                        mime="application/pdf",
                                        use_container_width=True,
                                        key=f"final_dl_{verifica.get('id')}_{i}"
                                    )
                                else:
                                    st.error(f"⚠️ Errore compilazione PDF: {error}")
                                    # Fallback: offri download LaTeX
                                    st.info("💡 In alternativa, puoi scaricare il codice LaTeX:")
                                    latex_code = verifica["latex_a"]
                                    st.download_button(
                                        "💾 Scarica file .tex",
                                        data=latex_code,
                                        file_name=f"verifica_{verifica.get('argomento', 'verifica')}.tex",
                                        mime="text/plain",
                                        use_container_width=True,
                                        key=f"tex_fallback_{verifica.get('id')}_{i}"
                                    )
                            except Exception as e:
                                st.error(f"⚠️ Errore download: {e}")
                        else:
                            st.warning("⚠️ Contenuto LaTeX non disponibile per questa verifica")
                
                with col3:
                    if st.button(f"🎲 Parti da questa", key=f"facsimile_{verifica.get('id')}_{i}"):
                        if verifica.get("latex_a"):
                            try:
                                # Carica la verifica come template per facsimile
                                st.session_state.verifiche["A"]["latex"] = verifica["latex_a"]
                                st.session_state.verifiche["A"]["latex_originale"] = verifica["latex_a"]
                                
                                # Compila PDF per preview
                                pdf_bytes, error = compila_pdf(verifica["latex_a"])
                                if pdf_bytes:
                                    st.session_state.verifiche["A"]["pdf"] = pdf_bytes
                                    st.session_state.verifiche["A"]["preview"] = True
                                    
                                    # Genera immagini per preview
                                    images, _ = pdf_to_images_bytes(pdf_bytes)
                                    st.session_state.preview_images = images or []
                                
                                # Estrai blocchi per review
                                pre, blocks = extract_blocks(verifica["latex_a"])
                                if blocks:
                                    st.session_state.review_preamble = pre
                                    st.session_state.review_blocks = blocks
                                
                                # Imposta parametri di generazione basati sulla verifica originale
                                st.session_state.gen_params = {
                                    "materia": verifica.get("materia", "Matematica"),
                                    "difficolta": verifica.get("scuola", "Liceo Scientifico"),
                                    "argomento": verifica.get("argomento", "Verifica"),
                                    "num_esercizi": verifica.get("num_esercizi", 5),
                                    "mostra_punteggi": True,
                                    "punti_totali": 100,
                                    "con_griglia": True,
                                }
                                
                                # Attiva modalità facsimile e vai a preview
                                st.session_state._facsimile_mode = True
                                st.session_state.stage = STAGE_PREVIEW
                                st.session_state._prev_stage = None
                                st.session_state.input_percorso = None
                                
                                st.success("🎲 Facsimile generato! Vai alla preview per creare la tua variante.")
                                st.rerun()
                                
                            except Exception as e:
                                st.error(f"⚠️ Errore generazione facsimile: {e}")
                        else:
                            st.warning("⚠️ Contenuto LaTeX non disponibile per questa verifica")
                
                with col4:
                    if st.button(f"🗑️ Elimina", key=f"delete_{verifica.get('id')}_{i}"):
                        # Conferma eliminazione
                        if f"confirm_delete_{verifica.get('id')}" not in st.session_state:
                            st.session_state[f"confirm_delete_{verifica.get('id')}"] = False
                        
                        if not st.session_state[f"confirm_delete_{verifica.get('id')}"]:
                            st.session_state[f"confirm_delete_{verifica.get('id')}"] = True
                            st.warning("⚠️ Sei sicuro? Click di nuovo per confermare l'eliminazione.")
                            st.rerun()
                        else:
                            # Elimina dal database
                            try:
                                res = supabase_admin.table("verifiche_storico")\
                                    .delete()\
                                    .eq("id", verifica.get("id"))\
                                    .execute()
                                
                                if res.data:
                                    st.success("✅ Verifica eliminata con successo!")
                                    # Rimuovi stato di conferma
                                    del st.session_state[f"confirm_delete_{verifica.get('id')}"]
                                    st.rerun()
                                else:
                                    st.error("⚠️ Errore durante l'eliminazione")
                            except Exception as e:
                                st.error(f"⚠️ Errore eliminazione: {e}")
                            finally:
                                # Reset stato di conferma
                                if f"confirm_delete_{verifica.get('id')}" in st.session_state:
                                    del st.session_state[f"confirm_delete_{verifica.get('id')}"]
                
                with col5:
                    # Rinomina
                    if f"rename_{verifica.get('id')}" not in st.session_state:
                        st.session_state[f"rename_{verifica.get('id')}"] = False
                    
                    if not st.session_state[f"rename_{verifica.get('id')}"]:
                        if st.button(f"✏️ Rinomina", key=f"rename_btn_{verifica.get('id')}_{i}"):
                            st.session_state[f"rename_{verifica.get('id')}"] = True
                            st.rerun()
                    else:
                        # Mostra un messaggio per il rinomina invece di rompere il layout
                        st.info("✏️ Vedi sotto per rinominare")
                
                # Se è in modalità rinomina, mostra l'input in una sezione separata
                if st.session_state.get(f"rename_{verifica.get('id')}", False):
                    st.markdown('<div style="margin: 0.5rem 0; padding: 1rem; background: #f8fafc; border-radius: 8px; border: 1px solid #e2e8f0;">', unsafe_allow_html=True)
                    
                    col_input, col_save, col_cancel = st.columns([2, 1, 1])
                    with col_input:
                        nuovo_nome = st.text_input(
                            "Nuovo nome:",
                            value=verifica.get("argomento", ""),
                            key=f"rename_input_{verifica.get('id')}_{i}",
                            label_visibility="collapsed"
                        )
                    with col_save:
                        if st.button("💾 Salva", key=f"save_rename_{verifica.get('id')}_{i}", use_container_width=True):
                            if nuovo_nome.strip():
                                result = _rinomina_verifica(verifica.get("id"), nuovo_nome.strip())
                                if result:
                                    st.success("✅ Nome aggiornato!")
                                    del st.session_state[f"rename_{verifica.get('id')}"]
                                    st.rerun()
                    with col_cancel:
                        if st.button("❌ Annulla", key=f"cancel_rename_{verifica.get('id')}_{i}", use_container_width=True):
                            del st.session_state[f"rename_{verifica.get('id')}"]
                            st.rerun()
                    
                    st.markdown('</div>', unsafe_allow_html=True)
                
                with col6:
                    # Preferiti (temporaneamente disabilitato)
                    if st.button(f"🤍 Preferiti", key=f"preferito_{verifica.get('id')}_{i}"):
                        st.info("⚠️ Funzionalità preferiti in arrivo! Presto potrai salvare le tue verifiche preferite.")
                
                with col7:
                    # Condivisione
                    if st.button(f"🔗 Condividi", key=f"share_{verifica.get('id')}_{i}"):
                        link = _genera_link_condivisione(verifica.get("id"))
                        if link:
                            st.success("🔗 Link generato!")
                            st.markdown(
                                f"""
                                <div style="
                                    background: #f0fdf4;
                                    border: 1px solid #86efac;
                                    border-radius: 8px;
                                    padding: 1rem;
                                    margin: 0.5rem 0;
                                ">
                                    <div style="font-size: 0.9rem; color: #059669; margin-bottom: 0.5rem;">
                                        📋 Link da condividere:
                                    </div>
                                    <div style="
                                        background: white;
                                        border: 1px solid #d1d5db;
                                        border-radius: 4px;
                                        padding: 0.5rem;
                                        font-family: monospace;
                                        font-size: 0.8rem;
                                        word-break: break-all;
                                    ">
                                        {link}
                                    </div>
                                    <div style="margin-top: 0.5rem;">
                                        <button onclick="navigator.clipboard.writeText('{link}')" 
                                                style="
                                                    background: #059669;
                                                    color: white;
                                                    border: none;
                                                    padding: 0.25rem 0.5rem;
                                                    border-radius: 4px;
                                                    font-size: 0.8rem;
                                                    cursor: pointer;
                                                ">
                                            📋 Copia link
                                        </button>
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )
                
                # Divider tra verifiche (tranne l'ultima)
                if i < len(verifiche_filtrate) - 1:
                    st.markdown("---")
    else:
        st.info("📝 Nessuna verifica trovata. Inizia a creare la tua prima verifica!")
    
    # Pulsante per creare nuova verifica
    st.markdown("---")
    col_center = st.columns([1, 2, 1])
    with col_center[1]:
        if st.button("🆕 Crea Nuova Verifica", type="primary", use_container_width=True):
            st.session_state.stage = STAGE_INPUT
            st.session_state.input_percorso = None
            st.rerun()


def _render_percorso_a_wizard():
    """
    Percorso A — Wizard sequenziale a 4 passi:
    upload → intent → loop → review → genera
    """
    lista  = st.session_state.analisi_docs_list
    info   = st.session_state.info_consolidate
    _wstep = st.session_state.get("wizard_step", "upload")
    _is_facsimile = st.session_state.get("_facsimile_mode", False)

    # ── Wizard step indicator ─────────────────────────────────────────────────
    _WSTEPS = [
        ("upload", "📂", "Carica"),
        ("intent", "🎯", "Intento"),
        ("loop",   "🔄", "Altro?"),
        ("review", "📋", "Riepilogo"),
    ]
    _wnames = [s[0] for s in _WSTEPS]
    _wcur_i = _wnames.index(_wstep) if _wstep in _wnames else 0
    _prog_h = (
        '<div style="display:flex;align-items:center;gap:6px;margin-bottom:1.1rem;' +
        'padding:.55rem 1rem;background:' + T["card"] + ';border-radius:12px;' +
        'border:1px solid ' + T["border"] + ';overflow:hidden;">' 
    )
    for _si, (sid, sico, slbl) in enumerate(_WSTEPS):
        _done = _si < _wcur_i
        _cur  = _si == _wcur_i
        _bc   = T["accent"] if _cur else (T["success"] if _done else T["border2"])
        _fc   = "#fff"
        _lc   = T["accent"] if _cur else (T["success"] if _done else T["muted"])
        _op   = "1" if (_cur or _done) else ".35"
        _ico  = "✓" if _done else sico
        _fw   = "800" if _cur else "500"
        _prog_h += (
            '<div style="display:flex;align-items:center;gap:5px;opacity:' + _op + ';flex-shrink:0;">' +
            '<div style="background:' + _bc + ';border-radius:50%;width:24px;height:24px;' +
            'display:flex;align-items:center;justify-content:center;font-size:.68rem;' +
            'color:' + _fc + ';flex-shrink:0;">' + _ico + '</div>' +
            '<span style="font-size:.78rem;font-weight:' + _fw + ';color:' + _lc + ';' +
            'font-family:DM Sans,sans-serif;white-space:nowrap;">' + slbl + '</span>' +
            '</div>'
        )
        if _si < len(_WSTEPS) - 1:
            _sc = T["success"] if _done else T["border2"]
            _prog_h += '<div style="flex:1;height:1.5px;background:' + _sc + ';opacity:.4;min-width:8px;"></div>'
    _prog_h += '</div>'
    st.markdown(_prog_h, unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────────────────
    # STEP: UPLOAD
    # ─────────────────────────────────────────────────────────────────────────
    if _wstep == "upload":
        # Banner facsimile
        if _is_facsimile:
            st.markdown(
                f'<div style="background:linear-gradient(135deg,{T["accent_light"]},{T["card"]});' +
                f'border:2px solid {T["accent"]};border-radius:14px;' +
                f'padding:.7rem 1rem;margin-bottom:.75rem;' +
                f'display:flex;align-items:center;gap:.8rem;">' +
                f'<span style="font-size:1.3rem;">⚡</span>' +
                f'<div>' +
                f'<div style="font-size:.88rem;font-weight:900;color:{T["accent"]};' +
                f'font-family:DM Sans,sans-serif;margin-bottom:.1rem;">Modalità Facsimile Istantaneo</div>' +
                f'<div style="font-size:.74rem;color:{T["text2"]};font-family:DM Sans,sans-serif;line-height:1.4;">' +
                f'Carica la verifica da cui vuoi creare una variante con dati diversi.' +
                f'</div></div></div>',
                unsafe_allow_html=True
            )

        # OCR hint banner (solo se nessun file)
        if not lista:
            st.markdown(
                f'<div class="ocr-hint-banner">' +
                f'<div class="ocr-hint-icon">✍️</div>' +
                f'<div class="ocr-hint-body">' +
                f'<div class="ocr-hint-title">Carica qualsiasi materiale — anche a mano!</div>' +
                f'<div class="ocr-hint-desc">' +
                f'Il sistema riconosce la <strong>scrittura manuale</strong>: basta una foto del foglio. ' +
                f'Funziona anche con schemi, fotocopie, pagine di libro.' +
                f'</div>' +
                f'<div class="ocr-hint-tags">' +
                f'<span class="ocr-hint-tag">✍️ Scrittura a mano</span>' +
                f'<span class="ocr-hint-tag">📸 Foto lavagna</span>' +
                f'<span class="ocr-hint-tag">📄 Fotocopie</span>' +
                f'<span class="ocr-hint-tag">📚 Libri</span>' +
                f'</div></div></div>',
                unsafe_allow_html=True
            )

        # Guardrail banner
        _rifiuto = st.session_state.get("_analisi_rifiuto")
        if _rifiuto:
            st.markdown(
                f'<div style="background:linear-gradient(135deg,#3B0000,#1C0000);' +
                f'border:2px solid #FF453A;border-radius:14px;padding:.9rem 1.1rem;margin-bottom:.8rem;">' +
                f'<div style="font-size:.85rem;font-weight:800;color:#FF453A;font-family:DM Sans,sans-serif;margin-bottom:.2rem;">' +
                f'File non riconosciuto come materiale scolastico</div>' +
                f'<div style="font-size:.75rem;color:#FFBBB8;font-family:DM Sans,sans-serif;line-height:1.5;">' +
                f'{_rifiuto.get("messaggio","Carica una verifica, appunti, capitoli del libro o la foto di un esercizio.")}' +
                f'</div></div>',
                unsafe_allow_html=True
            )
            if st.button("Chiudi avviso", key="btn_chiudi_rifiuto_w"):
                st.session_state["_analisi_rifiuto"] = None
                st.rerun()

        # Uploader
        if lista:
            st.markdown(
                f'<div style="font-size:.75rem;color:{T["muted"]};font-family:DM Sans,sans-serif;' +
                f'margin-bottom:.3rem;">{len(lista)} file già caricato/i — aggiungi altro materiale</div>',
                unsafe_allow_html=True
            )
        _upload_key = f"wiz_file_up_{len(lista)}"
        file_doc = st.file_uploader(
            "Carica documento",
            type=["pdf", "png", "jpg", "jpeg"],
            key=_upload_key,
            label_visibility="collapsed",
        )

        if file_doc:
            _new_bytes = file_doc.getvalue()
            _new_mime  = file_doc.type or "image/png"
            _new_name  = file_doc.name
            st.session_state.file_ispirazione = file_doc
            _hash_new = hash(_new_bytes)
            _hashes_esistenti = {d["file_hash"] for d in lista}
            if _hash_new not in _hashes_esistenti:
                _ocr_ph = st.empty()
                _ocr_ph.markdown(
                    f'<div class="ocr-skeleton-wrap">'
                    f'<div class="ocr-skeleton-header">'
                    f'<div class="ocr-skeleton-icon">🔬</div>'
                    f'<div style="flex:1">'
                    f'<div class="ocr-skeleton-title">Analisi AI in corso…</div>'
                    f'<div class="ocr-skeleton-sub">Lettura · Riconoscimento argomento · Classificazione</div>'
                    f'</div></div>'
                    f'<div class="ocr-skeleton-steps">'
                    f'<div class="ocr-skeleton-step ocr-step-active"><span>📖</span> Lettura file</div>'
                    f'<div class="ocr-skeleton-step"><span>🧠</span> Identificazione argomento</div>'
                    f'<div class="ocr-skeleton-step"><span>🏷️</span> Classificazione</div>'
                    f'</div>'
                    f'<div class="ocr-skeleton-doc">'
                    f'<div class="ocr-skeleton-scan"></div>'
                    f'<div class="ocr-skeleton-line" style="width:88%"></div>'
                    f'<div class="ocr-skeleton-line" style="width:72%"></div>'
                    f'<div class="ocr-skeleton-line" style="width:91%"></div>'
                    f'</div></div>',
                    unsafe_allow_html=True
                )
                _esegui_analisi_documento(_new_bytes, _new_mime, _new_name)
                _ocr_ph.empty()
            else:
                # File già analizzato — vai direttamente all'intent
                st.session_state["wizard_step"] = "intent"
                st.rerun()

        # After analysis → transition to intent
        if lista and not lista[-1]["confirmed"]:
            st.session_state["wizard_step"] = "intent"
            st.rerun()

        # Back button
        if _render_back_button("← Cambia percorso", key="btn_back_wiz_upload"):
            _reset_percorso()
            st.session_state["wizard_step"] = "upload"
            st.session_state["_facsimile_mode"] = False
            st.rerun()

    # ─────────────────────────────────────────────────────────────────────────
    # STEP: INTENT
    # ─────────────────────────────────────────────────────────────────────────
    elif _wstep == "intent":
        # Trova il file corrente (ultimo non confermato)
        _pending = next((e for e in reversed(lista) if not e["confirmed"]), None)
        if _pending is None:
            # Nessun file pending — torna a upload
            st.session_state["wizard_step"] = "upload"
            st.rerun()
            return

        _a     = _pending["analisi"]
        _tipo  = _a.get("tipo_documento", "altro")
        _mat   = _a.get("materia", "")
        _arg   = _a.get("contenuto_argomento", "")
        _scu   = _a.get("scuola", "")
        _msg   = _a.get("messaggio_proattivo", "")
        _fname = _pending["file_name"]
        _fhash = _pending["file_hash"]

        # ── Card risultato analisi ──────────────────────────────────────────
        _tipo_icons = {
            "verifica": "📋", "appunti": "📒", "libro": "📚",
            "esercizi_sciolti": "📝", "esercizio_singolo": "✏️", "misto": "📄",
        }
        _tipo_icon = _tipo_icons.get(_tipo, "📄")
        _chips_h = ""
        if _mat:  _chips_h += f'<span style="font-size:.7rem;background:{T["card2"]};border-radius:5px;padding:2px 8px;color:{T["text2"]};">{_mat}</span>'
        if _scu:  _chips_h += f' <span style="font-size:.7rem;background:{T["card2"]};border-radius:5px;padding:2px 8px;color:{T["text2"]};">{_scu}</span>'
        if _arg:
            _arg_s = (_arg[:55] + "…") if len(_arg) > 55 else _arg
            _chips_h += f' <span style="font-size:.7rem;background:{T["card2"]};border-radius:5px;padding:2px 8px;color:{T["text2"]};">{_arg_s}</span>'

        st.markdown(
            f'<div style="background:linear-gradient(135deg,{T["accent"]}10,{T["card"]});' +
            f'border:2px solid {T["accent"]}44;border-radius:16px;padding:.9rem 1.1rem;margin-bottom:.9rem;">' +
            f'<div style="display:flex;align-items:center;gap:.7rem;margin-bottom:.5rem;">' +
            f'<span style="font-size:1.5rem;">{_tipo_icon}</span>' +
            f'<div>' +
            f'<div style="font-size:.85rem;font-weight:800;color:{T["text"]};font-family:DM Sans,sans-serif;">{_fname}</div>' +
            f'<div style="font-size:.65rem;color:{T["muted"]};font-family:DM Sans,sans-serif;">{_tipo.replace("_"," ").title()}</div>' +
            f'</div></div>' +
            (f'<div style="display:flex;flex-wrap:wrap;gap:.3rem;margin-bottom:.5rem;">{_chips_h}</div>' if _chips_h else "") +
            (f'<div style="background:{T["hint_bg"]};border:1px solid {T["hint_border"]};border-radius:9px;' +
             f'padding:.45rem .75rem;font-size:.77rem;color:{T["hint_text"]};font-family:DM Sans,sans-serif;line-height:1.5;">{_msg}</div>' if _msg else "") +
            f'</div>',
            unsafe_allow_html=True
        )

        # ── Auto-types (appunti/libro/misto) → skip intent ──────────────────
        _AUTO_TYPES = {"appunti", "libro", "misto"}
        if _tipo in _AUTO_TYPES or _is_facsimile:
            _auto_mode = "copia_fedele" if _is_facsimile else "base_conoscenza"
            _auto_label = "Facsimile — genero variante con dati diversi" if _is_facsimile else "Fonte di concetti per la verifica"
            st.markdown(
                f'<div style="background:{T["card"]};border:1.5px solid {T["accent"]}55;' +
                f'border-radius:12px;padding:.7rem 1rem;margin-bottom:.8rem;' +
                f'display:flex;align-items:center;gap:.7rem;">' +
                f'<span style="font-size:1.2rem;">✅</span>' +
                f'<div>' +
                f'<div style="font-size:.82rem;font-weight:700;color:{T["text"]};font-family:DM Sans,sans-serif;">' +
                f'Utilizzo rilevato automaticamente</div>' +
                f'<div style="font-size:.74rem;color:{T["text2"]};font-family:DM Sans,sans-serif;">{_auto_label}</div>' +
                f'</div></div>',
                unsafe_allow_html=True
            )
            _c1, _c2 = st.columns([3, 1], gap="small")
            with _c1:
                if st.button("Conferma e continua →", key="wiz_intent_auto_confirm",
                             use_container_width=True, type="primary"):
                    _idx = next(i for i, e in enumerate(lista) if e["file_hash"] == _fhash)
                    st.session_state.analisi_docs_list[_idx]["confirmed"] = True
                    st.session_state.analisi_docs_list[_idx]["file_mode"] = _auto_mode
                    st.session_state.file_mode = _auto_mode
                    _consolida_info()
                    st.session_state["wizard_step"] = "loop"
                    st.rerun()
            with _c2:
                if st.button("← Indietro", key="wiz_intent_auto_back",
                             use_container_width=True):
                    # Rimuovi il file pending
                    _ri = next((i for i,e in enumerate(lista) if e["file_hash"] == _fhash), None)
                    if _ri is not None:
                        st.session_state.analisi_docs_list.pop(_ri)
                    _consolida_info()
                    st.session_state["wizard_step"] = "upload"
                    st.rerun()
            return

        # ── Intent selection per verifica / esercizi ────────────────────────
        _INTENT_OPTIONS_VERIFICA = [
            {
                "id":    "copia_fedele",
                "icon":  "⚡",
                "title": "Crea Variante",
                "desc":  "Stessa struttura e tipo di esercizi, ma con dati e numeri completamente diversi. Perfetto per la fila B o per riutilizzare la verifica.",
                "badge": "Più usato",
                "badge_color": T["accent"],
            },
            {
                "id":    "stile_e_struttura",
                "icon":  "📋",
                "title": "Copia Struttura",
                "desc":  "Stesso formato e numero di esercizi, ma argomento o difficoltà diversi. Ideale per un ripasso o per una nuova unità didattica.",
                "badge": None,
                "badge_color": "",
            },
            {
                "id":    "custom",
                "icon":  "✏️",
                "title": "Specifica tu",
                "desc":  "Scrivi istruzioni personalizzate per l'AI. Puoi combinare elementi, cambiare difficoltà, specificare argomenti particolari.",
                "badge": None,
                "badge_color": "",
            },
        ]
        _INTENT_OPTIONS_ESERCIZI = [
            {
                "id":    "includi_esercizio",
                "icon":  "📝",
                "title": "Includi nella verifica",
                "desc":  "Gli esercizi trovati vengono inclusi così come sono nella nuova verifica (con eventuali adattamenti di stile).",
                "badge": None,
                "badge_color": "",
            },
            {
                "id":    "esercizio_simile",
                "icon":  "🔄",
                "title": "Crea esercizi simili",
                "desc":  "L'AI crea nuovi esercizi ispirandosi alla struttura di quelli caricati, con dati e contesto diversi.",
                "badge": "Consigliato",
                "badge_color": T["success"],
            },
            {
                "id":    "custom",
                "icon":  "✏️",
                "title": "Specifica tu",
                "desc":  "Istruzioni personalizzate per come usare questi esercizi.",
                "badge": None,
                "badge_color": "",
            },
        ]

        _is_esercizi = _tipo in ("esercizi_sciolti", "esercizio_singolo")
        _intent_opts = _INTENT_OPTIONS_ESERCIZI if _is_esercizi else _INTENT_OPTIONS_VERIFICA

        st.markdown(
            f'<div style="font-size:.88rem;font-weight:800;color:{T["text"]};' +
            f'font-family:DM Sans,sans-serif;margin-bottom:.65rem;">' +
            f'Cosa vuoi che faccia con questo documento?</div>',
            unsafe_allow_html=True
        )

        _sel_intent = st.session_state.get("wizard_intent_pending", _intent_opts[0]["id"])

        for _opt in _intent_opts:
            _is_sel = _sel_intent == _opt["id"]
            _border = f'2px solid {T["accent"]}' if _is_sel else f'1.5px solid {T["border"]}' 
            _bg     = f'linear-gradient(135deg,{T["accent"]}14,{T["card"]})' if _is_sel else T["card"]
            _shadow = f'0 4px 18px {T["accent"]}22' if _is_sel else "none"
            _badge_html = ""
            if _opt["badge"]:
                _badge_html = (
                    f'<span style="font-size:.58rem;font-weight:800;' +
                    f'background:{_opt["badge_color"]};color:#fff;' +
                    f'padding:2px 7px;border-radius:100px;margin-left:.5rem;' +
                    f'letter-spacing:.04em;">{_opt["badge"]}</span>'
                )
            st.markdown(
                f'<div style="background:{_bg};border:{_border};border-radius:14px;' +
                f'padding:.8rem 1rem;margin-bottom:.45rem;cursor:pointer;' +
                f'box-shadow:{_shadow};transition:all .15s ease;">' +
                f'<div style="display:flex;align-items:center;gap:.6rem;">' +
                f'<span style="font-size:1.3rem;flex-shrink:0;">{_opt["icon"]}</span>' +
                f'<div style="flex:1;">' +
                f'<div style="font-size:.88rem;font-weight:{"900" if _is_sel else "700"};' +
                f'color:{T["accent"] if _is_sel else T["text"]};font-family:DM Sans,sans-serif;">' +
                f'{_opt["title"]}{_badge_html}</div>' +
                f'<div style="font-size:.74rem;color:{T["text2"]};font-family:DM Sans,sans-serif;' +
                f'line-height:1.45;margin-top:.1rem;">{_opt["desc"]}</div>' +
                f'</div>' +
                f'<div style="width:18px;height:18px;border-radius:50%;' +
                f'border:2px solid {T["accent"] if _is_sel else T["border2"]};' +
                f'background:{T["accent"] if _is_sel else "transparent"};' +
                f'display:flex;align-items:center;justify-content:center;' +
                f'flex-shrink:0;font-size:.6rem;color:#fff;">' +
                f'{"●" if _is_sel else ""}</div>' +
                f'</div></div>',
                unsafe_allow_html=True
            )
            if st.button(
                f'{"✓ " if _is_sel else ""}{_opt["title"]}',
                key=f'wiz_intent_sel_{_opt["id"]}',
                use_container_width=True,
                type="primary" if _is_sel else "secondary",
            ):
                st.session_state["wizard_intent_pending"] = _opt["id"]
                st.rerun()

        # Custom text field
        _custom_istr = ""
        if _sel_intent == "custom":
            st.markdown(
                f'<div style="font-size:.78rem;font-weight:600;color:{T["text"]};' +
                f'font-family:DM Sans,sans-serif;margin:.5rem 0 .2rem;">' +
                f'Scrivi le tue istruzioni per l\'AI</div>',
                unsafe_allow_html=True
            )
            _custom_istr = st.text_area(
                "Istruzioni custom",
                placeholder="es. Mantieni le domande V/F, cambia l'argomento a Geometria euclidea, aumenta la difficoltà...",
                height=80,
                label_visibility="collapsed",
                key="wiz_custom_istr",
            ).strip()

        # Confirm + Back row
        st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)
        if st.button(
            "Conferma e continua →",
            key="wiz_intent_confirm",
            use_container_width=True,
            type="primary",
            disabled=not _can_confirm,
        ):
                # Map intent → file_mode
                _mode_map = {
                    "copia_fedele":    "copia_fedele",
                    "stile_e_struttura": "stile_e_struttura",
                    "includi_esercizio": "includi_esercizio",
                    "esercizio_simile":  "esercizio_simile",
                    "custom":            "stile_e_struttura",  # fallback
                }
                _final_mode = _mode_map.get(_sel_intent, "stile_e_struttura")
                _idx = next(i for i, e in enumerate(lista) if e["file_hash"] == _fhash)
                st.session_state.analisi_docs_list[_idx]["confirmed"] = True
                st.session_state.analisi_docs_list[_idx]["file_mode"] = _final_mode
                st.session_state.file_mode = _final_mode
                # Save custom instruction
                if _sel_intent == "custom" and _custom_istr:
                    st.session_state.istruzioni_per_file[str(_fhash)] = _custom_istr
                elif _custom_istr:
                    st.session_state.istruzioni_per_file[str(_fhash)] = _custom_istr
                _consolida_info()
                st.session_state["wizard_intent_pending"] = None
                st.session_state["wizard_step"] = "loop"
                st.rerun()
        if _render_back_button("← Indietro", key="wiz_intent_back"):
            # Remove pending file
            _ri = next((i for i,e in enumerate(lista) if e["file_hash"] == _fhash), None)
            if _ri is not None:
                st.session_state.analisi_docs_list.pop(_ri)
            _consolida_info()
            st.session_state["wizard_intent_pending"] = None
            st.session_state["wizard_step"] = "upload"
            st.rerun()

        if not _can_confirm:
            st.markdown(
                f'<div style="font-size:.73rem;color:{T["warn"]};font-family:DM Sans,sans-serif;' +
                f'margin-top:.2rem;">Scrivi le istruzioni per continuare.</div>',
                unsafe_allow_html=True
            )

    # ─────────────────────────────────────────────────────────────────────────
    # STEP: LOOP
    # ─────────────────────────────────────────────────────────────────────────
    elif _wstep == "loop":
        _n_conf = sum(1 for e in lista if e["confirmed"])
        # Mostra riepilogo file confermati
        st.markdown(
            f'<div style="font-size:.9rem;font-weight:800;color:{T["text"]};' +
            f'font-family:DM Sans,sans-serif;margin-bottom:.7rem;">' +
            f'{"✅ " + str(_n_conf) + " file elaborato/i"}</div>',
            unsafe_allow_html=True
        )
        for _e in [e for e in lista if e["confirmed"]]:
            _tip = _e["analisi"].get("tipo_documento","altro")
            _tic = {"verifica":"📋","appunti":"📒","libro":"📚","esercizi_sciolti":"📝","esercizio_singolo":"✏️"}.get(_tip,"📄")
            _md_labels = {
                "copia_fedele":"Crea Variante","stile_e_struttura":"Copia Struttura",
                "base_conoscenza":"Fonte concetti","includi_esercizio":"Includi esercizi",
                "esercizio_simile":"Esercizi simili",
            }
            _mlab = _md_labels.get(_e["file_mode"], _e["file_mode"])
            _arg_f = _e["analisi"].get("contenuto_argomento","")
            st.markdown(
                f'<div style="background:{T["card"]};border:1px solid {T["border"]};' +
                f'border-radius:10px;padding:.5rem .9rem;margin-bottom:.3rem;' +
                f'display:flex;align-items:center;gap:.5rem;flex-wrap:wrap;">' +
                f'<span style="font-size:.85rem;">{_tic}</span>' +
                f'<span style="font-size:.78rem;font-weight:700;color:{T["text"]};' +
                f'font-family:DM Sans,sans-serif;max-width:160px;overflow:hidden;' +
                f'text-overflow:ellipsis;white-space:nowrap;">{_e["file_name"]}</span>' +
                f'<span style="font-size:.65rem;background:{T["accent"]}22;color:{T["accent"]};' +
                f'border:1px solid {T["accent"]}44;border-radius:5px;padding:1px 7px;' +
                f'font-weight:700;">{_mlab}</span>' +
                (f'<span style="font-size:.65rem;color:{T["muted"]};margin-left:auto;'
                 f'max-width:120px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">' +
                 f'{(_arg_f[:35]+"…") if len(_arg_f)>35 else _arg_f}</span>' if _arg_f else "") +
                f'</div>',
                unsafe_allow_html=True
            )

        st.markdown("<div style='height:.8rem'></div>", unsafe_allow_html=True)
        st.markdown(
            f'<div style="font-size:.9rem;font-weight:800;color:{T["text"]};' +
            f'font-family:DM Sans,sans-serif;margin-bottom:.5rem;">' +
            f'Vuoi aggiungere un altro file?</div>' +
            f'<div style="font-size:.78rem;color:{T["text2"]};font-family:DM Sans,sans-serif;' +
            f'margin-bottom:.75rem;line-height:1.45;">' +
            f'Puoi combinare più fonti: verifica + appunti, appunti + esercizi, ecc.</div>',
            unsafe_allow_html=True
        )

        _lc1, _lc2 = st.columns(2, gap="medium")
        with _lc1:
            if st.button(
                "📂  Sì, aggiungi un file",
                key="wiz_loop_yes",
                use_container_width=True,
            ):
                st.session_state["wizard_step"] = "upload"
                st.rerun()
        with _lc2:
            if st.button(
                "✅  No, vai al riepilogo",
                key="wiz_loop_no",
                use_container_width=True,
                type="primary",
            ):
                st.session_state["wizard_step"] = "review"
                st.rerun()

        # Back: un-confirm last confirmed file and go to intent
        st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)
        _bbl1, _bbl2, _bbl3 = st.columns([3, 2, 3])
        with _bbl2:
            if st.button("← Modifica ultimo file", key="wiz_loop_back",
                         use_container_width=True):
                # Un-confirm the last confirmed entry
                _last_conf_idx = None
                for _ci in reversed(range(len(lista))):
                    if lista[_ci]["confirmed"]:
                        _last_conf_idx = _ci
                        break
                if _last_conf_idx is not None:
                    st.session_state.analisi_docs_list[_last_conf_idx]["confirmed"] = False
                    # Clear saved instruction for that file
                    _fh = str(lista[_last_conf_idx]["file_hash"])
                    st.session_state.istruzioni_per_file.pop(_fh, None)
                    _consolida_info()
                st.session_state["wizard_intent_pending"] = None
                st.session_state["wizard_step"] = "intent"
                st.rerun()

    # ─────────────────────────────────────────────────────────────────────────
    # STEP: REVIEW
    # ─────────────────────────────────────────────────────────────────────────
    elif _wstep == "review":
        _n_conf = sum(1 for e in lista if e["confirmed"])
        if _n_conf == 0:
            st.session_state["wizard_step"] = "upload"
            st.rerun()
            return

        # ── Titolo riepilogo ─────────────────────────────────────────────────
        st.markdown(
            f'<div style="font-size:.95rem;font-weight:900;color:{T["text"]};' +
            f'font-family:DM Sans,sans-serif;margin-bottom:.6rem;">' +
            f'📋 Riepilogo — {_n_conf} file elaborato/i</div>',
            unsafe_allow_html=True
        )

        # ── Riepilogo file + intenti ─────────────────────────────────────────
        _md_labels = {
            "copia_fedele":"⚡ Crea Variante","stile_e_struttura":"📋 Copia Struttura",
            "base_conoscenza":"💡 Fonte concetti","includi_esercizio":"📝 Includi esercizi",
            "esercizio_simile":"🔄 Esercizi simili",
        }
        for _i, _e in enumerate([e for e in lista if e["confirmed"]]):
            _tip = _e["analisi"].get("tipo_documento","altro")
            _tic = {"verifica":"📋","appunti":"📒","libro":"📚","esercizi_sciolti":"📝","esercizio_singolo":"✏️"}.get(_tip,"📄")
            _mlab = _md_labels.get(_e["file_mode"], _e["file_mode"])
            _arg_f  = _e["analisi"].get("contenuto_argomento","")
            _mat_f  = _e["analisi"].get("materia","")
            _scu_f  = _e["analisi"].get("scuola","")
            _istr_f = st.session_state.istruzioni_per_file.get(str(_e["file_hash"]),"")
            st.markdown(
                f'<div style="background:{T["card2"]};border:1.5px solid {T["border"]};' +
                f'border-radius:12px;padding:.7rem 1rem;margin-bottom:.4rem;">' +
                f'<div style="display:flex;align-items:center;gap:.5rem;flex-wrap:wrap;margin-bottom:.3rem;">' +
                f'<span style="font-size:.9rem;">{_tic}</span>' +
                f'<span style="font-size:.82rem;font-weight:700;color:{T["text"]};font-family:DM Sans,sans-serif;">{_e["file_name"]}</span>' +
                f'<span style="font-size:.65rem;background:{T["accent"]}22;color:{T["accent"]};' +
                f'border:1px solid {T["accent"]}44;border-radius:5px;padding:1px 7px;font-weight:700;margin-left:auto;">{_mlab}</span>' +
                f'</div>' +
                (f'<div style="display:flex;flex-wrap:wrap;gap:.3rem;">' +
                 (f'<span style="font-size:.67rem;background:{T["card"]};border-radius:5px;padding:2px 7px;color:{T["text2"]};">{_mat_f}</span>' if _mat_f else "") +
                 (f'<span style="font-size:.67rem;background:{T["card"]};border-radius:5px;padding:2px 7px;color:{T["text2"]};">{_scu_f}</span>' if _scu_f else "") +
                 (f'<span style="font-size:.67rem;background:{T["card"]};border-radius:5px;padding:2px 7px;color:{T["text2"]};">{(_arg_f[:45]+"…") if len(_arg_f)>45 else _arg_f}</span>' if _arg_f else "") +
                 f'</div>' if (_mat_f or _scu_f or _arg_f) else "") +
                (f'<div style="font-size:.68rem;color:{T["hint_text"]};font-family:DM Sans,sans-serif;margin-top:.3rem;' +
                 f'padding:.25rem .5rem;background:{T["hint_bg"]};border-radius:5px;font-style:italic;">' +
                 f'"Istr.: {(_istr_f[:80]+"…") if len(_istr_f)>80 else _istr_f}"</div>' if _istr_f else "") +
                f'</div>',
                unsafe_allow_html=True
            )

        st.markdown(
            f'<div style="height:1px;background:{T["border"]};margin:.6rem 0 .8rem;border-radius:1px;"></div>',
            unsafe_allow_html=True
        )

        # ── Informazioni consolidate ─────────────────────────────────────────
        arg_cons     = info.get("contenuto_argomento","")
        scuola_cons  = info.get("scuola","")
        materia_cons = info.get("materia","")

        _manca_arg = not arg_cons
        _manca_scu = not scuola_cons
        _manca_mat = not materia_cons

        if _manca_arg or _manca_scu or _manca_mat:
            st.markdown(
                f'<div style="background:{T["hint_bg"]};border:1px solid {T["hint_border"]};' +
                f'border-radius:10px;padding:.5rem .85rem;margin-bottom:.6rem;">' +
                f'<div style="font-size:.73rem;font-weight:700;color:{T["hint_text"]};margin-bottom:.2rem;">' +
                f'💡 Alcune info non sono state ricavate — compilale qui:</div></div>',
                unsafe_allow_html=True
            )

        # Riga materia + scuola (solo se mancanti)
        _val_argomento = arg_cons
        _val_scuola    = scuola_cons
        _val_materia   = materia_cons

        _rc1_vals = []
        if _manca_arg:   _rc1_vals.append("arg")
        if _manca_scu:   _rc1_vals.append("scu")
        if _manca_mat:   _rc1_vals.append("mat")

        if _rc1_vals:
            _rr_cols = st.columns(len(_rc1_vals), gap="small")
            for _ri, _rf in enumerate(_rc1_vals):
                with _rr_cols[_ri]:
                    if _rf == "arg":
                        st.markdown('<div class="opt-label">Argomento ✱</div>', unsafe_allow_html=True)
                        _val_argomento = st.text_input(
                            "Argomento", placeholder="es. Equazioni di secondo grado",
                            label_visibility="collapsed", key="rev_arg"
                        ).strip()
                    elif _rf == "scu":
                        st.markdown('<div class="opt-label">Tipo di scuola ✱</div>', unsafe_allow_html=True)
                        _val_scuola = st.selectbox(
                            "Scuola", SCUOLE, index=0,
                            label_visibility="collapsed", key="rev_scu"
                        )
                    elif _rf == "mat":
                        st.markdown('<div class="opt-label">Materia ✱</div>', unsafe_allow_html=True)
                        _mat_opts = MATERIE + ["Altra…"]
                        _val_materia_sel = st.selectbox(
                            "Materia", _mat_opts, index=0,
                            label_visibility="collapsed", key="rev_mat"
                        )
                        if _val_materia_sel == "Altra…":
                            _val_materia = st.text_input(
                                "Scrivi materia", label_visibility="collapsed", key="rev_mat_c"
                            ).strip() or "Matematica"
                        else:
                            _val_materia = _val_materia_sel

        # Argomento (sempre editabile se presente)
        if not _manca_arg:
            st.markdown('<div class="opt-label">Argomento verifica ✱</div>', unsafe_allow_html=True)
            _val_argomento_in = st.text_input(
                "Argomento",
                value=arg_cons,
                label_visibility="collapsed",
                key="rev_arg_edit",
            ).strip()
            if _val_argomento_in:
                _val_argomento = _val_argomento_in

        # Materia + Scuola (sempre editabili se presenti)
        if not _manca_mat or not _manca_scu:
            _rev_c1, _rev_c2 = st.columns(2, gap="small")
            if not _manca_mat:
                with _rev_c1:
                    _mat_list_r = MATERIE + ["Altra materia…"]
                    _mat_idx_r  = _mat_list_r.index(materia_cons) if materia_cons in _mat_list_r else 0
                    # Etichetta rimossa per evitare ripetizioni
                    _sel_mat_r = st.selectbox(
                        "Materia", _mat_list_r, index=_mat_idx_r,
                        label_visibility="collapsed", key="rev_mat_sel"
                    )
                    _val_materia = (
                        st.text_input("Scrivi:", label_visibility="collapsed", key="rev_mat_custom").strip() or "Matematica"
                        if _sel_mat_r == "Altra materia…" else _sel_mat_r
                    )
            if not _manca_scu:
                with (_rev_c2 if not _manca_mat else _rev_c1):
                    _scu_idx_r = SCUOLE.index(scuola_cons) if scuola_cons in SCUOLE else 0
                    # Etichetta rimossa per evitare ripetizioni
                    _val_scuola = st.selectbox(
                        "Scuola", SCUOLE, index=_scu_idx_r,
                        label_visibility="collapsed", key="rev_scu_sel"
                    )

        # N° esercizi + punteggi
        _es_default = info.get("num_esercizi_rilevati", 4) or 4
        _es_default  = max(1, min(int(_es_default), 15))
        _es_opts     = list(range(1, 16))
        _es_idx_r    = _es_opts.index(_es_default) if _es_default in _es_opts else 3
        _rp1, _rp2 = st.columns(2, gap="small")
        with _rp1:
            st.markdown('<div class="opt-label">N° esercizi ✱</div>', unsafe_allow_html=True)
            num_esercizi = st.selectbox(
                "N° esercizi", options=_es_opts, index=_es_idx_r,
                label_visibility="collapsed", key="rev_num_es",
                format_func=lambda x: f"{x} eserc.",
            )
        with _rp2:
            # Calcola punti totali: priorità file > default
            _pt_rilevati = info.get("punti_totali_rilevati")
            if isinstance(_pt_rilevati, (int, float)) and _pt_rilevati > 0:
                punti_totali = int(_pt_rilevati)
                st.markdown('<div class="opt-label">Punti totali <span style="font-size:.75rem;opacity:.7;">(rilevati)</span></div>', unsafe_allow_html=True)
            else:
                punti_totali = 100
                st.markdown('<div class="opt-label">Punti totali</div>', unsafe_allow_html=True)
            
            _pt_opts = list(range(10, 105, 5))
            _pt_idx = _pt_opts.index(punti_totali) if punti_totali in _pt_opts else (_pt_opts.index(100) if 100 in _pt_opts else len(_pt_opts)-1)
            punti_totali = st.selectbox(
                "Punti", options=_pt_opts,
                index=_pt_idx,
                label_visibility="collapsed", key="rev_punti",
                format_func=lambda x: f"{x} pt",
            )

        mostra_punteggi = True
        con_griglia     = True
        _tog_r = st.toggle("Aggiungi punteggi e griglia", value=True, key="rev_toggle_punti")
        mostra_punteggi = _tog_r
        con_griglia     = _tog_r

        # Note finali AI (collassate)
        with st.expander("✏️ Note aggiuntive per l'AI (opzionale)", expanded=False):
            _fmode_prev = lista[0]["file_mode"] if lista else "stile_e_struttura"
            _hint_box_r = {
                "stile_e_struttura": "es. Aumenta la difficoltà, mantieni 4 esercizi",
                "copia_fedele":      "es. Cambia i valori numerici completamente",
                "base_conoscenza":   "es. Concentrati sulla definizione e applicazioni",
            }.get(_fmode_prev, "es. Indica preferenze aggiuntive…")
            istruzioni_extra = st.text_area(
                "Note AI", placeholder=_hint_box_r, height=72,
                label_visibility="collapsed", key="rev_note_ai",
            ).strip()
        
        if "istruzioni_extra" not in dir():
            istruzioni_extra = ""

        # ── Hint rassicurante ────────────────────────────────────────────────
        st.markdown(
            f'<div style="background:{T["hint_bg"]};border-left:3px solid {T["accent"]};' +
            f'border-radius:0 8px 8px 0;padding:.55rem .85rem;margin:.6rem 0 .9rem;' +
            f'font-size:.76rem;color:{T["hint_text"]};font-family:DM Sans,sans-serif;line-height:1.5;">' +
            f'💡 <strong>Tranquillo!</strong> Potrai modificare o rigenerare ogni singolo esercizio ' +
            f'nella fase successiva — la bozza è solo un punto di partenza.</div>',
            unsafe_allow_html=True
        )

        # ── Validazione ──────────────────────────────────────────────────────
        _arg_finale    = _val_argomento or arg_cons
        _scuola_finale = _val_scuola or scuola_cons or (SCUOLE[0] if SCUOLE else "Scuola Media")
        _mat_finale    = _val_materia or materia_cons or "Matematica"
        _manca_ancora  = not _arg_finale

        # ── Pulsante Genera ──────────────────────────────────────────────────
        if _manca_ancora and not _limite:
            st.markdown(
                f'<div style="font-size:.75rem;color:{T["warn"]};text-align:center;margin-bottom:.3rem;">' +
                f'Inserisci l\'argomento per continuare.</div>',
                unsafe_allow_html=True
            )
        
        genera_btn = st.button(
            "🚀  Genera Bozza",
            use_container_width=True,
            type="primary",
            disabled=_limite or _manca_ancora,
            key="rev_genera_btn",
            help="Avvia la generazione AI della verifica. Potrai modificare ogni singolo esercizio prima di scaricare il PDF.",
        )
        # Messaggio spostato sopra il pulsante
        if _limite:
            st.markdown(
                '<div style="text-align:center;font-size:.82rem;color:#EF4444;margin-top:.4rem;">' +
                '⛔ Limite mensile raggiunto.</div>',
                unsafe_allow_html=True
            )
        
        # Avviso PDF non disponibile
        if not LATEX_AVAILABLE:
            st.markdown(
                f'<div style="background:#FEF3C7;border:1px solid #F59E0B;border-radius:8px;'
                f'padding:.8rem;margin:.5rem 0;">'
                f'<div style="text-align:center;font-size:.85rem;color:#92400E;font-weight:600;">'
                f'⚠️ PDF non disponibile - LaTeX non installato</div>'
                f'<div style="text-align:center;font-size:.75rem;color:#B45309;margin-top:.2rem;">'
                f'Potrai generare la verifica ma non scaricare il PDF</div></div>',
                unsafe_allow_html=True,
            )

        if genera_btn and not _limite and not _manca_ancora:
            # Consolida istruzioni per-file
            _istr_per_file_testi = []
            for entry in lista:
                _fh_str = str(entry["file_hash"])
                _istr = st.session_state.istruzioni_per_file.get(_fh_str,"").strip()
                if _istr:
                    _istr_per_file_testi.append(f"[File: {entry['file_name']}] {_istr}")
            _istruzioni_combinate = "\n".join(_istr_per_file_testi)
            if istruzioni_extra:
                _istruzioni_combinate = (
                    istruzioni_extra + ("\n\n" + _istruzioni_combinate if _istruzioni_combinate else "")
                )

            _ad_merged = dict(info)
            if _arg_finale:
                _ad_merged["contenuto_argomento"] = _arg_finale
            if _mat_finale:
                _ad_merged["materia"] = _mat_finale
            if _scuola_finale:
                _ad_merged["scuola"] = _scuola_finale
            st.session_state.analisi_doc = _ad_merged

            _fmode_eff = next(
                (e["file_mode"] for e in lista if e["confirmed"] and e["file_mode"] != "ignora"),
                "ignora"
            )
            st.session_state.file_mode = _fmode_eff

            argomento_gen, note_gen = compila_contesto_generazione(
                analisi=_ad_merged,
                file_mode=_fmode_eff,
                istruzioni_extra=_istruzioni_combinate,
                argomento_override=_arg_finale if _manca_arg else None,
            )
            # ── Se copia_fedele: rafforza l'istruzione anti-copia ────────────
            if _fmode_eff == "copia_fedele":
                _fac_override_a = (
                    "╔══════════════════════════════════════════════════════════════╗\n"
                    "║  ⚠️  ISTRUZIONE CRITICA — FACSIMILE: DATI COMPLETAMENTE NUOVI  ║\n"
                    "╚══════════════════════════════════════════════════════════════╝\n"
                    "REGOLA ASSOLUTA: struttura IDENTICA, dati COMPLETAMENTE DIVERSI.\n"
                    "  • NON usare gli stessi numeri, equazioni, funzioni o valori dell'originale.\n"
                    "  • Riscrivi ogni enunciato — NON copiare nemmeno una frase.\n"
                    "  • Cambia tutti i coefficienti, date, nomi propri, misure al 100%.\n"
                    "  • Il risultato deve sembrare una verifica distinta sullo stesso argomento.\n"
                )
                note_gen = _fac_override_a + "\n\n" + note_gen
            s_es, imgs_es = _build_prompt_esercizi(
                st.session_state.esercizi_custom,
                num_esercizi,
                punti_totali if mostra_punteggi else 0,
                mostra_punteggi,
            )
            if _ad_merged.get("confidence", 0) >= 0.70 and _mat_finale in MATERIE:
                _salva_docente_preferenze(_mat_finale, {
                    "scuola": _scuola_finale,
                    "stile_desc": _ad_merged.get("stile_desc"),
                    "tipi_esercizi_preferiti": _ad_merged.get("tipi_domande"),
                })
            _file_isp = st.session_state.get("file_ispirazione")
            st.session_state.dialogo_stato = "confermato"
            _lancia_generazione(
                materia_scelta=_mat_finale,
                argomento=argomento_gen,
                difficolta=_scuola_finale,
                durata_scelta="1 ora",
                num_esercizi_totali=num_esercizi,
                punti_totali=punti_totali,
                mostra_punteggi=mostra_punteggi,
                con_griglia=con_griglia,
                note_generali=note_gen,
                s_es=s_es,
                imgs_es=imgs_es,
                file_ispirazione=_file_isp,
                mathpix_context=st.session_state.get("mathpix_context"),
            )

        # Back to loop
        st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)
        _brl1, _brl2, _brl3 = st.columns([3, 2, 3])
        with _brl2:
            if st.button("← Modifica file", key="wiz_review_back",
                         use_container_width=True):
                st.session_state["wizard_step"] = "loop"
                st.rerun()


def _render_dialogo_conferma():
    """Deprecato — ora tutto in _render_percorso_a_wizard()."""
    _render_percorso_a_wizard()


def _render_percorso_a_configura(num_esercizi_totali_ref: list):
    """Deprecato — ora tutto in _render_percorso_a_upload()."""
    # Questo path non dovrebbe più essere raggiunto.
    # Restituisce valori di default sicuri per evitare crash.
    return ("", "Matematica", "Generico", True, True, 100, False)


@st.dialog("📋 Verifica rilevata!")
def _mostra_dialogo_facsimile():
    """Popup che appare quando l'AI rileva che il file caricato è una verifica."""
    _a    = st.session_state.get("_fac_dialog_data", {})
    _mat  = _a.get("materia", "")
    _arg  = (_a.get("contenuto_argomento") or "")
    _n_es = _a.get("num_esercizi_rilevati") or "?"
    _pt   = _a.get("punti_totali_rilevati")
    _conf = int(float(_a.get("confidence", 0)) * 100)

    _pt_str  = f" da **{_pt} pt**" if _pt else ""
    _arg_str = f" su *{_arg[:70]}{'…' if len(_arg) > 70 else ''}*" if _arg else ""
    _mat_str = f" di **{_mat}**" if _mat else ""

    st.markdown(
        f"Ho analizzato il file e ho trovato una **verifica{_mat_str}** "
        f"con **{_n_es} esercizi**{_pt_str}{_arg_str}."
    )
    st.markdown(
        "Vuoi generare subito un **facsimile**? Stessa struttura e punteggi, "
        "ma dati, valori e quesiti completamente nuovi."
    )
    if _pt:
        st.caption(f"Punteggio rilevato: {_pt} pt · Confidenza AI: {_conf}%")
    st.divider()
    _d1, _d2 = st.columns(2)
    with _d1:
        if st.button("⚡ Sì, genera facsimile", type="primary", use_container_width=True,
                     disabled=_limite):
            st.session_state["_fac_dialog_pending"] = False
            st.session_state["_fac_confirmed"]      = True
            st.rerun()
    with _d2:
        if st.button("Continua a configurare", use_container_width=True):
            st.session_state["_fac_dialog_pending"] = False
            st.rerun()


def _render_percorso_b_form():
    """
    Percorso B — Layout a colonna singola con upload inline:
    ┌─────────────────────────────────────────────────┐
    │  Materia  │  Scuola                              │
    │  Argomento (2/3)  │  📎 Documento (1/3)          │
    │  N° Esercizi                                     │
    │  ⚙️ Personalizzazione Avanzata (expander)        │
    │  🚀 GENERA BOZZA                                 │
    └─────────────────────────────────────────────────┘
    """

    # ── Popup facsimile se verifica rilevata ─────────────────────────────────
    if st.session_state.get("_fac_dialog_pending"):
        _mostra_dialogo_facsimile()

    # ── Generazione facsimile confermata dal dialog ───────────────────────────
    if st.session_state.get("_fac_confirmed"):
        st.session_state["_fac_confirmed"] = False
        _a_fac = st.session_state.get("_fac_dialog_data", {})
        if _a_fac and not _limite:
            # Trova il file nel pool e marcalo come copia_fedele
            _fac_hash = _a_fac.get("file_hash")
            for _idx_f, _ef in enumerate(st.session_state.analisi_docs_list):
                if _ef["file_hash"] == _fac_hash:
                    st.session_state.analisi_docs_list[_idx_f]["confirmed"] = True
                    st.session_state.analisi_docs_list[_idx_f]["file_mode"] = "copia_fedele"
                    break
            st.session_state.file_mode        = "copia_fedele"
            st.session_state["_facsimile_mode"] = True
            _consolida_info()
            _info_fac      = st.session_state.info_consolidate
            _ha_griglia_fac = _a_fac.get("ha_tabella_punti", False)
            _pt_fac = 100
            if isinstance(_a_fac.get("punti_totali_rilevati"), (int, float)) and _a_fac["punti_totali_rilevati"] > 0:
                _pt_fac = int(_a_fac["punti_totali_rilevati"])
            _mat_fac = _info_fac.get("materia", "Matematica")
            _scu_fac = _info_fac.get("scuola", SCUOLE[0])
            _n_fac   = max(1, min(int(_a_fac.get("num_esercizi_rilevati") or 4), 15))
            argomento_fac, note_fac = compila_contesto_generazione(
                analisi=_info_fac,
                file_mode="copia_fedele",
                istruzioni_extra="",
                argomento_override=None,
            )
            note_fac = (
                "╔══════════════════════════════════════════════════════════════╗\n"
                "║  ⚠️  ISTRUZIONE CRITICA — FACSIMILE: DATI COMPLETAMENTE NUOVI  ║\n"
                "╚══════════════════════════════════════════════════════════════╝\n"
                "Stai generando un FACSIMILE della verifica allegata.\n"
                "REGOLA ASSOLUTA: struttura identica, stessi punteggi totali, stessa materia e argomento; "
                "tutti i dati numerici e testuali COMPLETAMENTE DIVERSI.\n"
                "NON usare gli stessi valori nemmeno come riferimento.\n"
                "Il docente NON deve riconoscere i dati originali.\n"
            ) + "\n\n" + note_fac
            _s_es_fac, _imgs_es_fac = _build_prompt_esercizi([], _n_fac, _pt_fac, True)
            _prog_fac = st.empty()
            _lancia_generazione(
                materia_scelta=_mat_fac,
                argomento=argomento_fac,
                difficolta=_scu_fac,
                durata_scelta="1 ora",
                num_esercizi_totali=_n_fac,
                punti_totali=_pt_fac,
                mostra_punteggi=True,
                con_griglia=_ha_griglia_fac or True,
                note_generali=note_fac,
                s_es=_s_es_fac,
                imgs_es=_imgs_es_fac,
                file_ispirazione=st.session_state.get("file_ispirazione"),
                mathpix_context=st.session_state.get("mathpix_context"),
                prog_placeholder=_prog_fac,
            )
            return

    # ── Toast post-analisi file (mostrato una volta sola dopo il rerun) ──────────
    _toast_msg = st.session_state.pop("_toast_analisi", None)
    if _toast_msg:
        st.toast(f"✅ Documento analizzato — {_toast_msg}", icon="🔬")

    # ═════════════════════════════════════════════════════════════════════════
    #  FORM PRINCIPALE — colonna sinistra (form) | colonna destra (upload)
    # ═════════════════════════════════════════════════════════════════════════
    if True:
        _prev = st.session_state.gen_params or {}
        # ── IDEA #1: carica defaults silenti come fallback ────────────────
        _udef = _load_user_defaults()

        if True:  # blocco unico -- layout a singola colonna
            # ── Dashboard: sezione form (layout bilanciato) ───────────────────────
            # Section header rimosso per evitare ripetizioni

            _col_m, _col_s = st.columns(2, gap="small")
            _mat_list = MATERIE + ["✏️ Altra materia..."]
            _mat_prev = _prev.get("materia") or _udef.get("materia", "Matematica")
            _mat_idx  = _mat_list.index(_mat_prev) if _mat_prev in _mat_list else 0
            _scu_prev = _prev.get("difficolta") or _udef.get("scuola", "")
            _scu_idx  = SCUOLE.index(_scu_prev) if _scu_prev in SCUOLE else 0

            # Auto-fill da analisi file se disponibile
            _info_cons = st.session_state.info_consolidate
            _mat_autofilled = False
            _scu_autofilled = False
            if _info_cons.get("materia") and _info_cons["materia"] in _mat_list:
                _mat_idx = _mat_list.index(_info_cons["materia"])
                _mat_autofilled = True
            if _info_cons.get("scuola") and _info_cons["scuola"] in SCUOLE:
                _scu_idx = SCUOLE.index(_info_cons["scuola"])
                _scu_autofilled = True

            with _col_m:
                st.markdown('<div class="opt-label">Materia ✱</div>', unsafe_allow_html=True)
                _sel_m = st.selectbox(
                    "Materia", _mat_list, index=_mat_idx,
                    label_visibility="collapsed", key="sel_materia_b",
                    help="Materia della verifica. Se hai caricato un file, viene rilevata automaticamente.",
                )
                materia_scelta = (
                    st.text_input("Scrivi materia:", key="_mat_custom_b",
                                  label_visibility="collapsed").strip() or "Matematica"
                    if _sel_m == "✏️ Altra materia..."
                    else (_sel_m or "Matematica")
                )
            with _col_s:
                st.markdown('<div class="opt-label">Tipo di scuola ✱</div>', unsafe_allow_html=True)
                difficolta = st.selectbox(
                    "Scuola", SCUOLE, index=_scu_idx,
                    help="Tipo di scuola e livello. Se hai caricato un file, viene rilevato automaticamente.",
                    label_visibility="collapsed", key="sel_scuola_b",
                )

            # Section header rimosso per evitare ripetizioni
            _auto_arg = _info_cons.get("contenuto_argomento", "")
            _arg_source = st.session_state.get("_pb_argomento_source")
            if _auto_arg and _arg_source != "manual":
                _current = st.session_state.get("argomento_area_b", "")
                if _current != _auto_arg:
                    st.session_state["argomento_area_b"] = _auto_arg
                # Badge arricchito con materia + tipo rilevati
                _badge_mat  = _info_cons.get("materia", "")
                _badge_tipo = _info_cons.get("tipo_documento", "")
                _badge_extras = []
                if _badge_mat:
                    _badge_extras.append(f"<strong>{_badge_mat}</strong>")
                if _badge_tipo:
                    _badge_extras.append(_badge_tipo.replace("_", " "))
                _badge_extra_str = (" · " + " · ".join(_badge_extras)) if _badge_extras else ""
                st.markdown(
                    f'<div class="context-sync-badge">'
                    f'✅ Compilato automaticamente dal file caricato{_badge_extra_str}'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            _arg_default = ""
            if _arg_source == "manual":
                _arg_default = st.session_state.get("_pb_argomento_manual_val", "")
            elif _auto_arg:
                _arg_default = _auto_arg
            argomento_raw = st.text_area(
                "argomento",
                value=_arg_default,
                placeholder="es. Equazioni di secondo grado\nes. La Rivoluzione Francese\nes. Il ciclo dell'acqua",
                height=105,
                label_visibility="collapsed",
                key="argomento_area_b",
            )

            # ── Traccia modifica manuale argomento ────────────────────────────────
            _auto_arg_ref = _info_cons.get("contenuto_argomento", "")
            argomento = argomento_raw.strip()
            if argomento and argomento != _auto_arg_ref:
                st.session_state["_pb_argomento_source"] = "manual"
                st.session_state["_pb_argomento_manual_val"] = argomento
            elif not argomento and st.session_state.get("_pb_argomento_source") == "manual":
                st.session_state["_pb_argomento_source"] = None

            _prefs = st.session_state._docente_prefs.get(materia_scelta, {})
            if not _prefs and st.session_state.utente and materia_scelta in MATERIE:
                _prefs = _carica_docente_preferenze(st.session_state.utente.id, materia_scelta)
                st.session_state._docente_prefs[materia_scelta] = _prefs

            # Calcola default num_esercizi (serve dentro l'expander)
            _n_default = _udef.get("num_esercizi", 4)
            if _info_cons.get("num_esercizi_rilevati"):
                try:
                    _n_default = max(1, min(int(_info_cons["num_esercizi_rilevati"]), 15))
                except (ValueError, TypeError):
                    pass

            # Section header rimosso per evitare ripetizioni
            _n_opts = list(range(1, 16))
            _n_idx  = (_n_opts.index(_n_default) if _n_default in _n_opts else 3)
            num_esercizi = st.selectbox(
                "Numero esercizi",
                options=_n_opts,
                index=_n_idx,
                label_visibility="collapsed",
                key="sel_num_es_b",
                format_func=lambda x: f"{x} esercizi",
            )

            # ── Divisore sottile prima di Personalizzazione ──────────────────────
            st.markdown('<div class="divider-minimal"></div>', unsafe_allow_html=True)
            # ── Personalizzazione Avanzata — st.expander standard ────────────────
            # Defaults da session state (validi anche quando expander è chiuso)
            note_extra   = st.session_state.get("_pers_note", "")
            mostra_punteggi = st.session_state.get("_pers_punteggi", _udef.get("mostra_punteggi", True))
            con_griglia  = mostra_punteggi
            punti_totali = st.session_state.get("_pers_pt", _udef.get("punti_totali", 100))

            with st.expander("✏️ Aggiungi istruzioni o preferenze (opzionale)", expanded=False):

                if _prefs.get("stile_desc"):
                    st.markdown(
                        f'<div style="background:{T["hint_bg"]};border:1px solid {T["hint_border"]};'
                        f'border-radius:8px;padding:.4rem .7rem;font-size:.9rem;color:{T["hint_text"]};'
                        f'font-family:DM Sans,sans-serif;margin-bottom:.7rem;">'
                        f'Preferenze salvate per <b>{materia_scelta}</b>: {_prefs["stile_desc"]}'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

                # ── Note aggiuntive — DENTRO l'expander ──────────────────────────
                st.markdown('<div class="opt-label">Note aggiuntive <span style="font-weight:400;opacity:.55;">— opzionale</span></div>', unsafe_allow_html=True)
                note_extra = st.text_area(
                    "Note AI",
                    placeholder=NOTE_PLACEHOLDER if isinstance(NOTE_PLACEHOLDER, str) else NOTE_PLACEHOLDER.get(materia_scelta, ""),
                    value=note_extra,
                    height=80,
                    label_visibility="collapsed",
                    key="note_area_b",
                )
                st.session_state["_pers_note"] = note_extra
                st.markdown("<div style='height:.3rem'></div>", unsafe_allow_html=True)

                _tog = st.toggle(
                    "Aggiungi punteggi e griglia di valutazione",
                    value=mostra_punteggi, key="toggle_punteggi_b",
                )
                mostra_punteggi = _tog
                con_griglia = _tog
                st.session_state["_pers_punteggi"] = _tog
                
                # Calcola punti totali: priorità file > sessione > default
                punti_totali = 100
                if _tog:
                    # Prova a usare i punti rilevati dal file
                    _pt_rilevati = _info_cons.get("punti_totali_rilevati")
                    if isinstance(_pt_rilevati, (int, float)) and _pt_rilevati > 0:
                        punti_totali = int(_pt_rilevati)
                    else:
                        # Fallback: sessione o default
                        punti_totali = st.session_state.get("_pers_pt", _udef.get("punti_totali", 100))
                    
                    _pt_opts = list(range(10, 105, 5))
                    _pt_idx  = _pt_opts.index(punti_totali) if punti_totali in _pt_opts else (_pt_opts.index(100) if 100 in _pt_opts else len(_pt_opts) - 1)
                    
                    # Mostra info se i punti sono rilevati dal file
                    if isinstance(_pt_rilevati, (int, float)) and _pt_rilevati > 0:
                        st.markdown('<div class="opt-label">Punti totali <span style="font-size:.75rem;opacity:.7;">(rilevati dal file)</span></div>', unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="opt-label">Punti totali</div>', unsafe_allow_html=True)
                    
                    punti_totali = st.selectbox(
                        "Punti totali", options=_pt_opts, index=_pt_idx,
                        label_visibility="collapsed", key="sel_punti_b",
                        format_func=lambda x: f"{x} pt",
                    )
                    st.session_state["_pers_pt"] = punti_totali

                # Struttura esercizi custom
                st.markdown('<div class="opt-label" style="margin-top:.5rem;">Struttura esercizi</div>', unsafe_allow_html=True)
                with st.expander("Definisci tipo e contenuto di ogni esercizio", expanded=False):
                    n_custom = len(st.session_state.esercizi_custom)
                    n_liberi = max(0, num_esercizi - n_custom)
                    if n_custom >= num_esercizi:
                        st.warning(f"Limite raggiunto ({n_custom}/{num_esercizi}).")
                    elif n_custom > 0:
                        st.success(f"✅ {n_custom} definiti + {n_liberi} liberi = {num_esercizi}")

                    _to_remove = None
                    for _i, _ex in enumerate(st.session_state.esercizi_custom):
                        st.markdown(f"**Esercizio {_i+1}**")
                        _tipo_val = _ex.get("tipo", "Aperto")
                        _tipo_idx = TIPI_ESERCIZIO.index(_tipo_val) if _tipo_val in TIPI_ESERCIZIO else 0
                        _t = st.selectbox(
                            "Tipo", TIPI_ESERCIZIO,
                            index=_tipo_idx,
                            key=f"tipo_b_{_i}",
                        )
                        st.session_state.esercizi_custom[_i]["tipo"] = _t
                        _d = st.text_area(
                            "Desc", value=_ex.get("descrizione", ""),
                            key=f"desc_b_{_i}", height=70,
                            label_visibility="collapsed",
                        )
                        st.session_state.esercizi_custom[_i]["descrizione"] = _d
                        _c1, _c2 = st.columns([3, 1])
                        with _c1:
                            _img = st.file_uploader(
                                "Immagine", type=["png", "jpg", "jpeg"],
                                key=f"img_b_{_i}", label_visibility="collapsed",
                            )
                            if _img:
                                st.session_state.esercizi_custom[_i]["immagine"] = _img
                            if st.session_state.esercizi_custom[_i].get("immagine"):
                                st.image(st.session_state.esercizi_custom[_i]["immagine"], width=55)
                        with _c2:
                            if st.button("🗑 Rimuovi", key=f"rm_b_{_i}", use_container_width=True):
                                _to_remove = _i
                        st.divider()

                    if _to_remove is not None:
                        st.session_state.esercizi_custom.pop(_to_remove)
                        st.rerun()

                    if st.button(
                        "＋ Aggiungi esercizio",
                        disabled=len(st.session_state.esercizi_custom) >= num_esercizi,
                        key="add_es_b",
                    ):
                        st.session_state.esercizi_custom.append(
                            {"tipo": "Aperto", "descrizione": "", "immagine": None}
                        )
                        st.rerun()

            # ── Expander upload documento ──────────────────────────────────────
            _lista_b_curr_pre = st.session_state.analisi_docs_list
            _n_docs = len(_lista_b_curr_pre)
            _upload_label = (
                f"📎 {_n_docs} documento{'i' if _n_docs > 1 else ''} caricato{'i' if _n_docs > 1 else ''}"
                if _n_docs else "📎 Carica un documento (opzionale)"
            )
            with st.expander(_upload_label, expanded=bool(_n_docs)):

                _lista_b = st.session_state.analisi_docs_list
                _upload_key_b = f"pb_file_up_{len(_lista_b)}"
                st.markdown('<div class="file-uploader-compact file-uploader-narrow">', unsafe_allow_html=True)
                _file_b = st.file_uploader(
                    "Inserisci materiale",
                    type=["pdf", "png", "jpg", "jpeg"],
                    key=_upload_key_b,
                    label_visibility="collapsed",
                    help="Carica una verifica, appunti o un capitolo. L'AI analizza il contenuto e aggiorna i campi automaticamente.",
                )
                st.markdown('</div>', unsafe_allow_html=True)

                if _file_b:
                    _fb_bytes = _file_b.getvalue()
                    _fb_hash  = hash(_fb_bytes)
                    _existing_b = {d["file_hash"] for d in _lista_b}
                    if _fb_hash not in _existing_b:
                        _ph_b = st.empty()
                        _ph_b.markdown(
                            '<div class="ocr-skeleton-wrap">'
                            '<div class="ocr-skeleton-header">'
                            '<div class="ocr-skeleton-icon">🔬</div>'
                            '<div style="flex:1">'
                            '<div class="ocr-skeleton-title">Analisi AI in corso…</div>'
                            '<div class="ocr-skeleton-sub">Lettura · Identificazione · Classificazione</div>'
                            '</div></div>'
                            '<div class="ocr-skeleton-steps">'
                            '<div class="ocr-skeleton-step ocr-step-active"><span>📖</span> Lettura</div>'
                            '<div class="ocr-skeleton-step"><span>🧠</span> Argomento</div>'
                            '<div class="ocr-skeleton-step"><span>🏷️</span> Tipo</div>'
                            '</div>'
                            '<div class="ocr-skeleton-doc">'
                            '<div class="ocr-skeleton-scan"></div>'
                            '<div class="ocr-skeleton-line" style="width:90%"></div>'
                            '<div class="ocr-skeleton-line" style="width:70%"></div>'
                            '</div></div>',
                            unsafe_allow_html=True,
                        )
                        st.session_state.file_ispirazione = _file_b
                        _esegui_analisi_documento(_fb_bytes, _file_b.type or "image/png", _file_b.name)
                        _ph_b.empty()
                        if st.session_state.get("_pb_argomento_source") != "manual":
                            st.session_state["_pb_argomento_source"] = None
                    else:
                        st.toast("File già presente.", icon="ℹ️")

                _lista_b_curr = st.session_state.analisi_docs_list

                if not _lista_b_curr:
                    st.markdown(
                        f'<div style="background:{T["hint_bg"]};border:1.5px solid {T["hint_border"]};'
                        f'border-radius:12px;padding:1.2rem;margin:.8rem 0;">'
                        f'<div style="text-align:center;">'
                        f'<div style="font-size:2rem;margin-bottom:.5rem;">📄</div>'
                        f'<div style="font-size:.9rem;font-weight:600;color:{T["hint_text"]};margin-bottom:.3rem;">'
                        f'Nessun file ancora caricato</div>'
                        f'<div style="font-size:.8rem;color:{T["hint_text"]};line-height:1.4;">'
                        f'Carica <strong>appunti, libro di testo o una verifica precedente</strong> —<br>'
                        f'l\'AI la userà come riferimento per generare gli esercizi.</div>'
                        f'</div></div>',
                        unsafe_allow_html=True,
                    )
                else:
                    _MODO_OPTIONS = {
                        "base_conoscenza":   "📚 Usa come fonte",
                        "includi_esercizio": "✏️ Riadatta esercizi",
                    }
                    _rimuovi_idx = None

                    for _fi, _fentry in enumerate(_lista_b_curr):
                        _fhash_str = str(_fentry["file_hash"])
                        _fa        = _fentry.get("analisi", {})
                        _fa_mat    = _fa.get("materia", "")
                        _fa_es     = _fa.get("num_esercizi_rilevati") or 0

                        _tags = _compute_file_tags(_fa)
                        _tag_class_map = {
                            "tipo": "doc-tag-tipo", "content": "doc-tag-content",
                            "formula": "doc-tag-formula", "grafico": "doc-tag-grafico",
                        }
                        _tags_html = "".join(
                            f'<span class="doc-tag {_tag_class_map.get(k,"doc-tag-content")}">{ico} {lbl}</span>'
                            for ico, lbl, k in _tags
                        ) if _tags else ""

                        _meta_parts = []
                        if _fa_mat:
                            _meta_parts.append(f"<strong>{_fa_mat}</strong>")
                        if _fa_es:
                            _meta_parts.append(f"{_fa_es} es.")
                        _meta_str = " · ".join(_meta_parts)

                        _fname_display = _fentry["file_name"]
                        if len(_fname_display) > 30:
                            _fname_display = _fname_display[:27] + "…"

                        _meta_span = f'<span class="fpc-meta">{_meta_str}</span>' if _meta_str else ""
                        st.markdown(
                            f'<div class="file-pool-card">'
                            f'  <div class="fpc-header">'
                            f'    <span class="fpc-name">📄 {_fname_display}</span>'
                            f'    {_meta_span}'
                            f'  </div>'
                            + (f'  <div class="doc-tags">{_tags_html}</div>' if _tags_html else '')
                            + '</div>',
                            unsafe_allow_html=True,
                        )

                        _modo_prev = _fentry.get("file_mode", "base_conoscenza")
                        if _modo_prev not in _MODO_OPTIONS:
                            _modo_prev = "base_conoscenza"
                        _sel_modo = st.radio(
                            f"Modalità file {_fi}",
                            options=list(_MODO_OPTIONS.keys()),
                            index=list(_MODO_OPTIONS.keys()).index(_modo_prev),
                            format_func=lambda x: _MODO_OPTIONS[x],
                            key=f"pb_mode_{_fhash_str}",
                            horizontal=True,
                            label_visibility="collapsed",
                        )
                        if _sel_modo != _lista_b_curr[_fi].get("file_mode"):
                            st.session_state.analisi_docs_list[_fi]["file_mode"] = _sel_modo
                            st.session_state.analisi_docs_list[_fi]["confirmed"] = (_sel_modo != "ignora")
                            _consolida_info()

                        if _sel_modo == "includi_esercizio":
                            if _fa_es > 1:
                                _hint_txt = (
                                    f'L\'AI riprende la struttura dei <strong>{_fa_es} esercizi</strong> '
                                    f'del file e genera valori completamente nuovi.'
                                )
                            elif _fa_es == 1:
                                _hint_txt = "L'AI riprende la struttura delle domande del file e cambia i valori."
                            else:
                                _hint_txt = "L'AI riadatta le domande del file inserendo dati e contesti nuovi."
                        else:
                            _hint_txt = (
                                "L'AI legge il documento e crea esercizi <strong>originali</strong> "
                                "sull'argomento trattato."
                            )
                        _hint_cls = "file-includi-hint" if _sel_modo == "includi_esercizio" else "file-fonte-hint"
                        st.markdown(
                            f'<div class="{_hint_cls}">💡 {_hint_txt}</div>',
                            unsafe_allow_html=True,
                        )

                        st.markdown('<div class="fpc-delete-row">', unsafe_allow_html=True)
                        if st.button("✕ rimuovi", key=f"pb_rm_{_fhash_str}_{_fi}",
                                     help="Rimuovi questo file dal pool"):
                            _rimuovi_idx = _fi
                        st.markdown('</div>', unsafe_allow_html=True)

                    if _rimuovi_idx is not None:
                        _rimosso = st.session_state.analisi_docs_list.pop(_rimuovi_idx)
                        st.session_state.istruzioni_per_file.pop(str(_rimosso.get("file_hash")), None)
                        _consolida_info()
                        if st.session_state.get("_pb_argomento_source") != "manual":
                            st.session_state["_pb_argomento_source"] = None
                            if not st.session_state.analisi_docs_list:
                                st.session_state.info_consolidate = {}
                        st.rerun()

            # ── CTA: Genera Bozza ─────────────────────────────────────────────────
            _manca_arg = not argomento
            st.markdown("<div style='height:.9rem'></div>", unsafe_allow_html=True)

            if _manca_arg and not _limite:
                st.markdown(
                    f'<div style="text-align:center;font-size:.82rem;color:{T["warn"]};'
                    f'font-family:DM Sans,sans-serif;margin-bottom:.3rem;">'
                    f'Inserisci l\'argomento per continuare.</div>',
                    unsafe_allow_html=True,
                )

            st.markdown('<div class="cta-genera-wrap">', unsafe_allow_html=True)
            genera_btn = st.button(
                "🚀  Genera Bozza",
                use_container_width=True,
                type="primary",
                disabled=_limite or _manca_arg,
                key="genera_btn_b",
                help="Avvia la generazione AI della verifica. Potrai modificare ogni singolo esercizio prima di scaricare il PDF.",
            )
            st.markdown('</div>', unsafe_allow_html=True)

            # Placeholder progress bar — apparirà subito sotto il pulsante
            _prog_placeholder = st.empty()
            if _limite:
                st.markdown(
                    f'<div style="text-align:center;font-size:.82rem;color:#EF4444;'
                    f'font-family:DM Sans,sans-serif;font-weight:600;margin-top:.4rem;">'
                    f'⛔ Limite mensile raggiunto.</div>',
                    unsafe_allow_html=True,
                )
            
            # Avviso PDF non disponibile
            if not LATEX_AVAILABLE:
                st.markdown(
                    f'<div style="background:#FEF3C7;border:1px solid #F59E0B;border-radius:8px;'
                    f'padding:.8rem;margin:.5rem 0;">'
                    f'<div style="text-align:center;font-size:.85rem;color:#92400E;font-weight:600;">'
                    f'⚠️ PDF non disponibile - LaTeX non installato</div>'
                    f'<div style="text-align:center;font-size:.75rem;color:#B45309;margin-top:.2rem;">'
                    f'Potrai generare la verifica ma non scaricare il PDF</div></div>',
                    unsafe_allow_html=True,
                )
            # ── Back link ─────────────────────────────────────────────────────────
            if _render_back_button("← Indietro", key="btn_back_b"):
                st.session_state.input_percorso = None
                st.rerun()

    # ── Costruisci nota finale con istruzioni per-file ────────────────────────
    _istr_per_file_testi = []
    for _fentry in st.session_state.analisi_docs_list:
        _fh_str = str(_fentry["file_hash"])
        _istr = st.session_state.istruzioni_per_file.get(_fh_str, "").strip()
        if _istr:
            _istr_per_file_testi.append(f"[File: {_fentry['file_name']}] {_istr}")
    _istruzioni_combinate = "\n".join(_istr_per_file_testi)

    note_extra_raw = st.session_state.get("note_area_b", "")
    if note_extra_raw and _istruzioni_combinate:
        note_extra_finale = note_extra_raw + "\n\n" + _istruzioni_combinate


    elif _istruzioni_combinate:
        note_extra_finale = _istruzioni_combinate
    else:
        note_extra_finale = note_extra_raw

    return (
        argomento,
        materia_scelta,
        difficolta,
        mostra_punteggi,
        con_griglia,
        punti_totali,
        num_esercizi,
        note_extra_finale,
        genera_btn,
        _prog_placeholder,
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  _render_stage_input()  ← AGGIUNGERE routing per "FACSIMILE" (linea ~2471)
#
#  Nel blocco if/elif della funzione esistente, aggiungere PRIMA di "if percorso == 'A'":
#
#      if percorso == "FACSIMILE":
#          _render_facsimile_dedicato()
#          return
#
# ═══════════════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════════════
#  SESSION STATE INIT PATCH (~linea 519 main.py)
#  Aggiungere nel blocco di inizializzazione:
#
#      if "_pb_argomento_source"    not in st.session_state:
#          st.session_state["_pb_argomento_source"]     = None
#      if "_pb_argomento_manual_val" not in st.session_state:
#          st.session_state["_pb_argomento_manual_val"] = ""
# ═══════════════════════════════════════════════════════════════════════════════


def _lancia_generazione(
    materia_scelta: str,
    argomento: str,
    difficolta: str,
    durata_scelta: str,
    num_esercizi_totali: int,
    punti_totali: int,
    mostra_punteggi: bool,
    con_griglia: bool,
    note_generali: str,
    s_es: str,
    imgs_es: list,
    file_ispirazione=None,
    mathpix_context: str | None = None,
    prog_placeholder=None,          # st.empty() creato nel form, vicino al pulsante
):
    """
    Funzione condivisa dai due percorsi: lancia genera_verifica,
    aggiorna session_state e transita a STAGE_REVIEW.
    """
    calibrazione = CALIBRAZIONE_SCUOLA.get(difficolta, "")
    _t_start = time.time()
    _n_steps = 5   # titolo · esercizi · QA · PDF · salvataggio
    _step    = [0]
    # Usa il placeholder passato (vicino al pulsante) oppure crea uno nuovo
    _prog    = prog_placeholder if prog_placeholder is not None else st.empty()

    def _avanza(testo):
        _step[0] += 1
        perc  = int(min(_step[0] / _n_steps, 0.97) * 100)
        _acc  = T["accent"]
        _bg   = T["border"]
        _txt  = T["text2"]
        _prog.markdown(
            f'<div style="margin:.6rem 0 1rem 0;padding:.7rem 1rem;'
            f'background:{T["card"]};border:1px solid {T["border2"]};'
            f'border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,.05);">'
            f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">'
            f'<div style="width:8px;height:8px;border-radius:50%;background:{_acc};'
            f'animation:pulse-dot 1.2s ease-in-out infinite;flex-shrink:0;"></div>'
            f'<div style="font-size:.85rem;font-weight:600;color:{_txt};'
            f'font-family:DM Sans,sans-serif;">{testo}</div>'
            f'<div style="margin-left:auto;font-size:.75rem;color:{_txt};opacity:.6;">{perc}%</div>'
            f'</div>'
            f'<div style="background:{_bg};border-radius:100px;height:6px;overflow:hidden;">'
            f'<div style="background:linear-gradient(90deg,{_acc},{_acc}cc);'
            f'width:{perc}%;height:100%;border-radius:100px;transition:width .5s cubic-bezier(.4,0,.2,1);"></div>'
            f'</div></div>',
            unsafe_allow_html=True
        )

    # ── Routing intelligente modello ──────────────────────────────────────────
    # Se la sidebar ha restituito un modello specifico (admin/pro/gold), lo usa.
    # Altrimenti usa il routing automatico basato su piano + materia.
    _piano_corrente = st.session_state.get("piano_utente", "free")
    if _is_admin:
        _piano_corrente = "admin"
    _modello_id_eff = modello_id  # da sidebar
    # Verifica che il modello selezionato sia coerente con il piano (protezione lato server)
    # Usa sempre gli ID definiti in config.MODELLI_DISPONIBILI per evitare drift tra codice e config.
    _id_free  = MODELLI_DISPONIBILI["⚡ Flash 2.5 Lite (veloce · Free)"]["id"]
    _ids_all  = {v["id"] for v in MODELLI_DISPONIBILI.values()}
    _ids_pro  = {
        v["id"]
        for v in MODELLI_DISPONIBILI.values()
        if v.get("piano") in ("free", "pro")
    }
    _modello_validi_per_piano = {
        "free":  {_id_free},
        "pro":   _ids_pro,
        "gold":  _ids_all,
        "admin": _ids_all,
    }
    if _modello_id_eff not in _modello_validi_per_piano.get(_piano_corrente, set()):
        # Fallback sicuro
        _modello_id_eff = get_model_id_per_piano(_piano_corrente, materia_scelta)

    try:
        model_obj = genai.GenerativeModel(_modello_id_eff)
        ris = genera_verifica(
            model=model_obj, materia=materia_scelta, argomento=argomento,
            difficolta=difficolta, calibrazione=calibrazione, durata=durata_scelta,
            num_esercizi=num_esercizi_totali, punti_totali=punti_totali,
            mostra_punteggi=mostra_punteggi, con_griglia=con_griglia,
            doppia_fila=False, bes_dsa=False, perc_ridotta=25,
            bes_dsa_b=False, genera_soluzioni=False,
            note_generali=note_generali, istruzioni_esercizi=s_es,
            immagini_esercizi=imgs_es, file_ispirazione=file_ispirazione,
            mathpix_context=mathpix_context,
            on_progress=_avanza,
        )

        def _agg(fid, d):
            v = st.session_state.verifiche[fid]
            if d.get("latex"): v["latex"] = v["latex_originale"] = d["latex"]
            if d.get("pdf"):   v["pdf"] = d["pdf"]; v["pdf_ts"] = time.time(); v["preview"] = True
            if fid == "S":
                if d.get("testo"): v["testo"] = d["testo"]
                if d.get("latex"): v["latex"] = d["latex"]
                if d.get("pdf"):   v["pdf"]   = d["pdf"]

        _agg("A", ris["A"]); _agg("B", ris["B"])
        _agg("R", ris["R"]); _agg("RB", ris["RB"])
        _agg("S", ris["S"])

        st.session_state.gen_time_sec = int(time.time() - _t_start)
        st.session_state.gen_params = {
            "materia": materia_scelta, "difficolta": difficolta,
            "argomento": ris["titolo"], "durata": durata_scelta,
            "num_esercizi": num_esercizi_totali, "punti_totali": punti_totali,
            "mostra_punteggi": mostra_punteggi, "con_griglia": con_griglia,
            "perc_ridotta": 25, "modello_id": _modello_id_eff,
        }

        preamble, blocks = extract_blocks(st.session_state.verifiche["A"]["latex"])
        st.session_state.review_preamble  = preamble
        st.session_state.review_blocks    = blocks
        st.session_state.review_sel_idx   = 0
        st.session_state.last_materia     = materia_scelta
        st.session_state.last_argomento   = ris["titolo"]

        if st.session_state.verifiche["A"]["pdf"]:
            imgs, _ = pdf_to_images_bytes(st.session_state.verifiche["A"]["pdf"])
            st.session_state.preview_images = imgs or []

        _prog.markdown(
            '<div style="margin:.6rem 0 1rem 0;">'
            '<div style="font-size:.82rem;font-weight:600;color:' + T["success"] + ';'
            'font-family:DM Sans,sans-serif;margin-bottom:6px;">'
            '✅ Bozza pronta! Ora puoi rivedere gli esercizi.</div>'
            '<div style="background:' + T["border"] + ';border-radius:100px;height:8px;overflow:hidden;">'
            '<div style="background:' + T["success"] + ';width:100%;height:100%;border-radius:100px;"></div>'
            '</div></div>',
            unsafe_allow_html=True
        )
        time.sleep(0.7)
        _prog.empty()

        try:
            supabase_admin.table("verifiche_storico").insert({
                "user_id":        st.session_state.utente.id,
                "materia":        materia_scelta,
                "argomento":      ris["titolo"],
                "scuola":         difficolta,
                "latex_a":        ris["A"]["latex"] or None,
                "latex_b":        None,
                "latex_r":        None,
                "modello":        _modello_id_eff,
                "num_esercizi":   num_esercizi_totali,
                # ── Campi percorso/upload (recuperati dallo session_state)
                "percorso_scelto": st.session_state.get("input_percorso"),
                "file_mode":       st.session_state.get("file_mode"),
            }).execute()
            st.session_state._storico_refresh += 1
            st.toast("✅ Bozza salvata!", icon="💾")
        except Exception as _e:
            st.warning(f"⚠️ Salvataggio storico non riuscito: {_e}")

        # ── IDEA #1: Salva preferenze silenti dopo generazione riuscita ────
        _save_user_defaults_silent(
            materia=materia_scelta, scuola=difficolta,
            num_esercizi=num_esercizi_totali,
            mostra_punteggi=mostra_punteggi,
            punti_totali=punti_totali,
        )

        # ── Transita a STAGE_PREVIEW (anteprima rapida) invece di STAGE_REVIEW
        st.session_state.stage = STAGE_PREVIEW
        st.rerun()

    except Exception as _e:
        _prog.empty()
        st.error(f"❌ Errore durante la generazione: {_e}")


# ═══════════════════════════════════════════════════════════════════════════════
#  STAGE_INPUT — orchestratore principale
# ═══════════════════════════════════════════════════════════════════════════════

def _render_facsimile_dedicato():
    """
    Pagina Facsimile Rapido — Percorso dedicato:
    Solo un'area di upload, poi AI analizza e genera la variante.
    """
    # ── Header pagina ─────────────────────────────────────────────────────────
    st.markdown(
        f'<div class="facsimile-page-wrap">'
        f'<span class="facsimile-page-icon">⚡</span>'
        f'<div class="facsimile-page-title">Facsimile Istantaneo</div>'
        f'<div class="facsimile-page-desc">'
        f'Carica la verifica che vuoi replicare. '
        f'L\'AI mantiene struttura e punteggi, '
        f'cambia tutti i dati e i numeri.'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Area upload ───────────────────────────────────────────────────────────
    _fac_lista = st.session_state.analisi_docs_list

    if not _fac_lista:
        st.markdown(
            f'<div class="facsimile-page-uploader">'
            f'<div style="text-align:center;margin-bottom:.6rem;">'
            f'<div style="font-size:.82rem;font-weight:700;color:#9F7AEA;'
            f'font-family:DM Sans,sans-serif;margin-bottom:.3rem;">'
            f'📂 Inserisci la verifica originale</div>'
            f'<div style="font-size:.75rem;color:{T["text2"]};font-family:DM Sans,sans-serif;">'
            f'PDF, immagine o foto della verifica stampata</div>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    _fac_upload_key = f"fac_upload_{len(_fac_lista)}"
    _fac_file = st.file_uploader(
        "Carica verifica originale",
        type=["pdf", "png", "jpg", "jpeg"],
        key=_fac_upload_key,
        label_visibility="collapsed",
        help="Carica la verifica che vuoi replicare — anche una foto.",
    )

    if _fac_file:
        _fb = _fac_file.getvalue()
        _fhash = hash(_fb)
        _existing = {d["file_hash"] for d in _fac_lista}
        if _fhash not in _existing:
            _fac_ph = st.empty()
            _fac_ph.markdown(
                f'<div class="ocr-skeleton-wrap">'
                f'  <div class="ocr-skeleton-header">'
                f'    <div class="ocr-skeleton-icon">⚡</div>'
                f'    <div>'
                f'      <div class="ocr-skeleton-title">Analisi verifica in corso…</div>'
                f'      <div class="ocr-skeleton-sub">Struttura · Punteggi · Esercizi</div>'
                f'    </div>'
                f'  </div>'
                f'  <div class="ocr-skeleton-doc">'
                f'    <div class="ocr-skeleton-scan"></div>'
                f'    <div class="ocr-skeleton-line" style="width:90%"></div>'
                f'    <div class="ocr-skeleton-line" style="width:68%"></div>'
                f'    <div class="ocr-skeleton-line" style="width:82%"></div>'
                f'  </div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            st.session_state.file_ispirazione = _fac_file
            st.session_state["_facsimile_mode"] = True
            _esegui_analisi_documento(_fb, _fac_file.type or "image/png", _fac_file.name)
            _fac_ph.empty()

    # ── Recap file caricato + analisi punteggi ────────────────────────────────
    if _fac_lista:
        _fac_entry = _fac_lista[-1]
        _fac_analisi = _fac_entry.get("analisi", {})
        _fac_nome = _fac_entry["file_name"]
        _fac_tipo = _fac_analisi.get("tipo_documento", "altro")
        _fac_mat = _fac_analisi.get("materia", "")
        _fac_arg = _fac_analisi.get("contenuto_argomento", "")
        _fac_pt = _fac_analisi.get("num_esercizi_rilevati", "?")

        _tipo_icon = {"verifica": "📋", "appunti": "📒"}.get(_fac_tipo, "📄")

        st.markdown(
            f'<div class="file-item-b" style="border:2px solid #7C3AED55;margin-bottom:.75rem;">'
            f'  <div class="file-item-b-header">'
            f'    <span class="file-item-b-icon">{_tipo_icon}</span>'
            f'    <span class="file-item-b-name">{_fac_nome}</span>'
            f'    <span class="file-item-b-badge file-item-b-badge-verifica">'
            f'      {_fac_tipo.replace("_"," ").title()}'
            f'    </span>'
            f'  </div>'
            + (
                f'<div style="font-size:.78rem;color:{T["text2"]};'
                f'font-family:DM Sans,sans-serif;line-height:1.5;">'
                + (f'<strong>{_fac_mat}</strong> · ' if _fac_mat else "")
                + (_fac_arg[:80] + ("…" if len(_fac_arg) > 80 else "") if _fac_arg else "")
                + f'</div>'
                if _fac_mat or _fac_arg else ""
            )
            + f'</div>',
            unsafe_allow_html=True,
        )

        # ── Analisi punteggi ─────────────────────────────────────────────────
        _ha_griglia = _fac_analisi.get("ha_tabella_punti", False)
        if _ha_griglia:
            st.markdown(
                f'<div style="background:{T["success"]}18;border:1px solid {T["success"]}44;'
                f'border-radius:9px;padding:.5rem .85rem;margin-bottom:.6rem;'
                f'font-size:.8rem;color:{T["success"]};font-family:DM Sans,sans-serif;'
                f'display:flex;align-items:center;gap:.5rem;">'
                f'<span>✅</span> '
                f'Tabella punti rilevata — il totale sarà mantenuto identico nella variante.'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div style="background:{T["warn"]}18;border:1px solid {T["warn"]}44;'
                f'border-radius:9px;padding:.5rem .85rem;margin-bottom:.6rem;'
                f'font-size:.8rem;color:{T["warn"]};font-family:DM Sans,sans-serif;'
                f'display:flex;align-items:center;gap:.5rem;">'
                f'<span>ℹ️</span> '
                f'Nessuna tabella punti rilevata. '
                f'Vuoi aggiungerne una?</div>',
                unsafe_allow_html=True,
            )
            _add_griglia = st.toggle(
                "Genera tabella di valutazione automaticamente",
                value=True,
                key="fac_add_griglia",
            )

        # ── Pulsante Genera ───────────────────────────────────────────────────
        st.markdown("<div style='height:.4rem'></div>", unsafe_allow_html=True)
        st.markdown('<div class="cta-genera-wrap">', unsafe_allow_html=True)
        _fac_gen_btn = st.button(
            "⚡  Genera Variante",
            use_container_width=True,
            type="primary",
            key="btn_fac_genera",
            disabled=_limite,
        )
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="cta-hint-below">'
            f'<span>🔒</span> <span>Stessa struttura · Dati completamente nuovi</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

        if _limite:
            st.markdown(
                f'<div style="text-align:center;font-size:.82rem;color:#EF4444;'
                f'font-family:DM Sans,sans-serif;margin-top:.3rem;">'
                f'⛔ Limite mensile raggiunto.</div>',
                unsafe_allow_html=True,
            )

        if _fac_gen_btn and not _limite:
            # Conferma il file e transita al wizard
            _fac_idx = next(
                (i for i, e in enumerate(st.session_state.analisi_docs_list)
                 if e["file_hash"] == _fac_entry["file_hash"]),
                0,
            )
            st.session_state.analisi_docs_list[_fac_idx]["confirmed"] = True
            st.session_state.analisi_docs_list[_fac_idx]["file_mode"] = "copia_fedele"
            st.session_state.file_mode = "copia_fedele"
            st.session_state["_facsimile_mode"] = True
            _consolida_info()

            # Lancia generazione diretta
            _info = st.session_state.info_consolidate
            _con_griglia_fac = _ha_griglia or st.session_state.get("fac_add_griglia", True)
            argomento_fac, note_fac = compila_contesto_generazione(
                analisi=_info,
                file_mode="copia_fedele",
                istruzioni_extra="",
                argomento_override=None,
            )

            # ── OVERRIDE FACSIMILE: forza l'AI a produrre dati COMPLETAMENTE NUOVI ──
            _facsimile_override = (
                "╔══════════════════════════════════════════════════════════════╗\n"
                "║  ⚠️  ISTRUZIONE CRITICA — FACSIMILE: DATI COMPLETAMENTE NUOVI  ║\n"
                "╚══════════════════════════════════════════════════════════════╝\n"
                "Stai generando un FACSIMILE della verifica allegata.\n"
                "REGOLA ASSOLUTA E NON NEGOZIABILE:\n"
                "  • La struttura (numero esercizi, tipologie, numero sotto-punti) "
                "deve essere IDENTICA all'originale.\n"
                "  • Tutti i dati specifici (numeri, coefficienti, equazioni, funzioni, "
                "date, nomi propri, misure, unità) devono essere COMPLETAMENTE DIVERSI.\n"
                "  • NON usare gli stessi valori numerici nemmeno come riferimento.\n"
                "  • Il testo degli enunciati deve essere riscritto — NON copiare nemmeno "
                "una frase dall'originale.\n"
                "  • L'AI deve produrre dati NUOVI e DIVERSI al 100% — se l'originale "
                "ha x=3, la variante deve usare un numero diverso (es. x=7 o x=-2).\n"
                "  • Se ci sono grafici nell'originale, genera grafici TikZ con funzioni DIVERSE.\n"
                "  • Il docente NON deve essere in grado di riconoscere i dati originali.\n"
            )
            # Prepend override alla nota (massima priorità sulle altre istruzioni)
            note_fac = _facsimile_override + "\n\n" + note_fac

            _mat_fac = _info.get("materia", "Matematica")
            _scu_fac = _info.get("scuola", SCUOLE[0])
            _n_fac = _info.get("num_esercizi_rilevati", 4) or 4
            _n_fac = max(1, min(int(_n_fac), 15))
            _calibr_fac = CALIBRAZIONE_SCUOLA.get(_scu_fac, "")

            s_es_fac, imgs_es_fac = _build_prompt_esercizi(
                [], _n_fac, 100, True
            )
            _lancia_generazione(
                materia_scelta=_mat_fac,
                argomento=argomento_fac,
                difficolta=_scu_fac,
                durata_scelta="1 ora",
                num_esercizi_totali=_n_fac,
                punti_totali=100,
                mostra_punteggi=True,
                con_griglia=_con_griglia_fac,
                note_generali=note_fac,
                s_es=s_es_fac,
                imgs_es=imgs_es_fac,
                file_ispirazione=st.session_state.get("file_ispirazione"),
                mathpix_context=st.session_state.get("mathpix_context"),
            )
            return

    # ── Back link ─────────────────────────────────────────────────────────────
    if _render_back_button("← Torna alla scelta percorso", key="btn_back_fac"):
        _reset_percorso()
        st.session_state.input_percorso = None
        st.session_state["_facsimile_mode"] = False
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
#  _render_percorso_b_form()  ← SOSTITUISCE la versione esistente (linea 2097)
# ═══════════════════════════════════════════════════════════════════════════════


def _render_stage_input():
    percorso = st.session_state.get("input_percorso")

    # ── QA MODE ───────────────────────────────────────────────────────────────
    if percorso == "QA" or st.session_state.get("qa_mode", False):
        _render_qa_section()
        return

    # ── BIVIO ─────────────────────────────────────────────────────────────────
    if percorso is None:
        _render_bivio()
        return

    # ── PERCORSO FACSIMILE ──────────────────────────────────────────────────────
    if percorso == "FACSIMILE":
        _render_facsimile_dedicato()
        return

    # ── PERCORSO A ────────────────────────────────────────────────────────────
    if percorso == "A":
        _render_percorso_a_wizard()
        return

    # ── PERCORSO LIBERA → reindirizza a B (form manuale) ─────────────────────
    if percorso == "LIBERA":
        st.session_state.input_percorso = "B"
        st.rerun()

    # ── PERCORSO B ────────────────────────────────────────────────────────────
    if percorso == "B":
        (
            argomento, materia_scelta, difficolta,
            mostra_punteggi, con_griglia, punti_totali,
            num_esercizi_totali, note_extra, genera_btn,
            _prog_ph_b,
        ) = _render_percorso_b_form()

        if not genera_btn or _limite:
            return

        if not argomento:
            return

        # ── Idea #8: se template selezionato, inietta struttura nelle note ──
        _tmpl_sel_id = st.session_state.get("_template_sel")
        _tmpl_nota_extra = ""
        if _tmpl_sel_id:
            _TMPL_MAP = {
                "classico_misto":     "Struttura: 1 esercizio aperto (3 sottopunti), 1 scelta multipla (4 domande), 1 vero/falso (5 affermazioni).",
                "stem_calcolo":       "Struttura: 3 esercizi numerici aperti. Es.1: problema con 4 sottopunti. Es.2: applicativo con 3 sottopunti. Es.3: dimostrazione/verifica con 2 sottopunti.",
                "letterario":         "Struttura: 1 comprensione testo (3 domande), 1 analisi/commento (3 domande), 1 completamento (5 lacune), 1 scelta multipla teorica (4 domande).",
                "breve_bes":          "Struttura semplificata BES/DSA: 1 vero/falso (4 affermazioni brevi), 1 scelta multipla (3 domande chiare), 1 completamento (4 spazi). Linguaggio diretto, frasi brevi.",
                "interrogazione_orale": "Struttura per orale: 1 domanda aperta ampia, 3 domande di approfondimento mirate, 1 domanda di collegamento interdisciplinare. Formato lista domande.",
                "ripasso_veloce":     "Struttura quiz rapido: 6 scelte multiple (1 risposta corretta su 4), 6 vero/falso. Domande brevi, nessun esercizio aperto.",
            }
            _tmpl_nota_extra = _TMPL_MAP.get(_tmpl_sel_id, "")

        _note_finale = note_extra
        if _tmpl_nota_extra:
            _note_finale = (_tmpl_nota_extra + "\n\n" + note_extra).strip()

        s_es, imgs_es = _build_prompt_esercizi(
            st.session_state.esercizi_custom,
            num_esercizi_totali,
            punti_totali if mostra_punteggi else 0,
            mostra_punteggi,
        )

        # ── Estrai file "includi_esercizio" → vision input ─────────────────────
        # I file marcati come "esercizio da inserire" vengono passati come immagini
        # al modello vision affinché l'esercizio compaia OBBLIGATORIAMENTE nell'output.
        _imgs_esercizio: list = []
        _note_esercizi_inclusi: list = []
        for _idx_fe, _fe in enumerate(st.session_state.analisi_docs_list):
            if _fe.get("file_mode") == "includi_esercizio":
                _fb = _fe.get("file_bytes")
                _fm = _fe.get("mime_type", "image/png")
                if _fb:
                    _imgs_esercizio.append({
                        "idx":       _idx_fe + 1,
                        "data":      _fb,
                        "mime_type": _fm,
                    })
                _istr_fe = st.session_state.istruzioni_per_file.get(str(_fe["file_hash"]), "").strip()
                _nota_fe = f"File '{_fe['file_name']}' — esercizio da includere obbligatoriamente"
                if _istr_fe:
                    _nota_fe += f": {_istr_fe}"
                _note_esercizi_inclusi.append(_nota_fe)

        # Combina immagini: prima quelle da includi_esercizio, poi quelle da esercizi_custom
        imgs_es_finale = _imgs_esercizio + imgs_es

        # Aggiungi alle note generali le istruzioni per gli esercizi obbligatori
        if _note_esercizi_inclusi:
            _nota_includi = (
                "\n\n╔═══════════════════════════════════════════════╗\n"
                "║ ⚠️ ESERCIZI DA INCLUDERE OBBLIGATORIAMENTE     ║\n"
                "╚═══════════════════════════════════════════════╝\n"
                + "\n".join(_note_esercizi_inclusi)
                + "\nL'immagine allegata contiene l'esercizio. Trascrivilo fedelmente in LaTeX "
                "come Esercizio 1 e genera gli esercizi restanti normalmente."
            )
            _note_finale = (_note_finale + _nota_includi).strip() if _note_finale else _nota_includi.strip()
        else:
            imgs_es_finale = imgs_es

        _lancia_generazione(
            materia_scelta=materia_scelta,
            argomento=argomento,
            difficolta=difficolta,
            durata_scelta="1 ora",
            num_esercizi_totali=num_esercizi_totali,
            punti_totali=punti_totali,
            mostra_punteggi=mostra_punteggi,
            con_griglia=con_griglia,
            note_generali=_note_finale,
            s_es=s_es,
            imgs_es=imgs_es_finale,
            file_ispirazione=None,
            mathpix_context=None,
            prog_placeholder=_prog_ph_b,
        )
        return





# ═══════════════════════════════════════════════════════════════════════════════
#  STAGE_PREVIEW — Anteprima rapida post-generazione (Fase 2.5)
# ═══════════════════════════════════════════════════════════════════════════════

def _render_stage_preview():
    """
    Mostra un'anteprima della verifica appena generata.
    Il docente sceglie se andare direttamente al salvataggio finale
    oppure entrare nell'editor dei blocchi (STAGE_REVIEW).
    """
    gp             = st.session_state.get("gen_params", {})
    materia_str    = gp.get("materia", "")
    argomento_str  = gp.get("argomento", "Verifica")
    scuola_str     = gp.get("difficolta", "")
    vA             = st.session_state.verifiche.get("A", {})
    preview_imgs   = st.session_state.get("preview_images", [])

    # ── Header ────────────────────────────────────────────────────────────────
    _h_acc  = T["accent"]
    _h_acc2 = T.get("accent2", _h_acc)
    st.markdown(
        f'<div style="background:linear-gradient(135deg,{_h_acc} 0%,{_h_acc2} 100%);'
        f'border-radius:14px;padding:1.2rem 1.8rem;margin-bottom:1.2rem;text-align:center;">'
        f'<div style="font-family:DM Sans,sans-serif;font-size:1.4rem;font-weight:900;'
        f'color:#fff;margin-bottom:.3rem;">📄 Anteprima Verifica</div>'
        f'<div style="font-size:.95rem;color:#ffffffd0;font-family:DM Sans,sans-serif;">'
        + materia_str + ' · ' + scuola_str + ' · ' + argomento_str +
        f'</div></div>',
        unsafe_allow_html=True
    )

    # ── Preview PDF — 80% larghezza, con navigazione ─────────────────────────
    if preview_imgs:
        n_prev = len(preview_imgs)
        cur_page = st.session_state.get("preview_page", 0)
        # Clamp in caso di cambio verifica
        cur_page = max(0, min(cur_page, n_prev - 1))

        # Immagine larga all'80% della colonna (colonne [1,8,1])
        _img_l, _img_c, _img_r = st.columns([1, 8, 1])
        with _img_c:
            st.image(preview_imgs[cur_page], use_container_width=True)

        # Barra navigazione solo se più pagine
        if n_prev > 1:
            st.markdown("<div style='height:.4rem'></div>", unsafe_allow_html=True)
            _nav_l, _nav_info, _nav_r = st.columns([1, 2, 1])
            with _nav_l:
                st.markdown('<div class="page-nav-btn-wrap"></div>', unsafe_allow_html=True)
                if st.button("◀ Precedente", key="prev_page_btn",
                             disabled=(cur_page == 0),
                             use_container_width=True):
                    st.session_state.preview_page = cur_page - 1
                    st.rerun()
            with _nav_info:
                st.markdown(
                    f'<div style="text-align:center;font-size:.78rem;font-weight:500;'
                    f'color:{T["muted"]};font-family:DM Sans,sans-serif;'
                    f'padding:.45rem 0;">Pagina {cur_page + 1} di {n_prev}</div>',
                    unsafe_allow_html=True
                )
            with _nav_r:
                st.markdown('<div class="page-nav-btn-wrap"></div>', unsafe_allow_html=True)
                if st.button("Successiva ▶", key="next_page_btn",
                             disabled=(cur_page == n_prev - 1),
                             use_container_width=True):
                    st.session_state.preview_page = cur_page + 1
                    st.rerun()
    elif vA.get("latex"):
        with st.expander("Anteprima LaTeX (PDF non disponibile)", expanded=True):
            st.code(vA["latex"][:3000], language="latex")
    else:
        st.info("Anteprima non disponibile.")

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    # ── Due pulsanti di scelta — restyle ──────────────────────────────────────
    col_ok, col_edit = st.columns(2, gap="medium")

    with col_ok:
        # Card verde
        st.markdown(
            f'<div style="border:2px solid {T["success"]};border-radius:16px;'
            f'padding:1.1rem 1.3rem;background:{T["card"]};'
            f'display:flex;flex-direction:column;gap:.5rem;">'
            f'<div style="font-size:1.6rem;line-height:1;">✅</div>'
            f'<div style="font-weight:800;font-size:1rem;color:{T["success"]};'
            f'font-family:DM Sans,sans-serif;">Perfetta così</div>'
            f'<div style="font-size:.78rem;color:{T["muted"]};line-height:1.45;">'
            f'Vai direttamente al download — nessuna modifica.</div>'
            f'</div>',
            unsafe_allow_html=True
        )
        st.markdown("<div style='height:.4rem'></div>", unsafe_allow_html=True)
        if st.button("Scarica PDF", use_container_width=True,
                     type="primary", key="preview_ok",
                     help="Vai direttamente al download del PDF — la verifica è pronta."):
            st.session_state.stage = STAGE_FINAL
            st.rerun()

    with col_edit:
        # Card arancio
        st.markdown(
            f'<div style="border:2px solid {T["accent"]};border-radius:16px;'
            f'padding:1.1rem 1.3rem;background:{T["card"]};'
            f'display:flex;flex-direction:column;gap:.5rem;">'
            f'<div style="font-size:1.6rem;line-height:1;">✏️</div>'
            f'<div style="font-weight:800;font-size:1rem;color:{T["accent"]};'
            f'font-family:DM Sans,sans-serif;">Voglio modificarla</div>'
            f'<div style="font-size:.78rem;color:{T["muted"]};line-height:1.45;">'
            f'Apri l\'editor e cambia i singoli esercizi con l\'AI.</div>'
            f'</div>',
            unsafe_allow_html=True
        )
        st.markdown("<div style='height:.4rem'></div>", unsafe_allow_html=True)
        if st.button("Apri editor", use_container_width=True,
                     key="preview_edit",
                     help="Apri l'editor interattivo per rifinire testo, punteggi e struttura di ogni esercizio."):
            st.session_state.stage = STAGE_REVIEW
            st.rerun()

    st.markdown("<br/>", unsafe_allow_html=True)

    # ── Link "torna alla configurazione" ────────────────────────────────────
    if st.button("← Ricomincia da capo", key="preview_back",
                 help="Cancella questa verifica e torna all'inizio per crearne una nuova."):
        for _k in ("stage", "verifiche", "gen_params", "review_blocks",
                   "review_preamble", "preview_images", "last_preview_ts", "input_percorso",
                   "dialogo_stato", "analisi_doc", "file_mode"):
            if _k in st.session_state:
                del st.session_state[_k]
        for _k in list(st.session_state.keys()):
            if _k.startswith("_undo_block_") or _k.startswith("item_pt_"):
                del st.session_state[_k]
        st.session_state.stage = STAGE_INPUT
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
#  STAGE_REVIEW
# ═══════════════════════════════════════════════════════════════════════════════

def _render_stage_review():
    gp              = st.session_state.gen_params
    blocks          = st.session_state.review_blocks
    materia_str     = gp.get("materia","")
    scuola_str      = gp.get("difficolta","")
    argomento_str   = gp.get("argomento","Verifica")
    mostra_punteggi = gp.get("mostra_punteggi", True)
    punti_totali    = gp.get("punti_totali", 100)
    con_griglia     = gp.get("con_griglia", False)
    modello_rw      = gp.get("modello_id", modello_id)
    n_blocks        = len(blocks)

    # ── Iniezione CSS diretta: risolve expander neri + bottoni problematici ──
    # Questa tecnica (style tag inline) bypassa i limiti di specificità di Streamlit
    # che altrimenti sovrascrive con color-scheme:dark e --background-color nero.
    st.markdown(f"""
<style>
/* ── EXPANDER: header + content area ─────────────────────────────────── */
html body div[data-testid="stAppViewContainer"] details[data-testid="stExpander"],
html body .stApp details[data-testid="stExpander"] {{
  background: {T["card"]} !important;
  background-color: {T["card"]} !important;
  border: 2px solid {T["border2"]} !important;
  border-radius: 14px !important;
  overflow: hidden !important;
  margin-bottom: .5rem !important;
  color-scheme: light !important;
  --background-color: {T["card"]} !important;
}}
html body div[data-testid="stAppViewContainer"] details[data-testid="stExpander"] > summary,
html body .stApp details[data-testid="stExpander"] > summary {{
  background: {T["card"]} !important;
  background-color: {T["card"]} !important;
  color: {T["text"]} !important;
  -webkit-text-fill-color: {T["text"]} !important;
  font-family: 'DM Sans', sans-serif !important;
  font-weight: 700 !important;
  font-size: .9rem !important;
  padding: .85rem 1.1rem !important;
  border-radius: 12px !important;
  color-scheme: light !important;
}}
html body div[data-testid="stAppViewContainer"] details[data-testid="stExpander"] > summary *,
html body .stApp details[data-testid="stExpander"] > summary span,
html body .stApp details[data-testid="stExpander"] > summary p,
html body .stApp details[data-testid="stExpander"] > summary div {{
  color: {T["text"]} !important;
  -webkit-text-fill-color: {T["text"]} !important;
  background: transparent !important;
}}
html body div[data-testid="stAppViewContainer"] details[data-testid="stExpander"] > summary svg *,
html body .stApp details[data-testid="stExpander"] > summary svg * {{
  fill: {T["text2"]} !important;
  stroke: {T["text2"]} !important;
}}
/* Summary APERTO */
html body div[data-testid="stAppViewContainer"] details[data-testid="stExpander"][open] > summary,
html body .stApp details[data-testid="stExpander"][open] > summary {{
  background: linear-gradient(135deg, {T["accent"]} 0%, {T["accent2"]} 100%) !important;
  background-color: {T["accent"]} !important;
  color: #fff !important;
  -webkit-text-fill-color: #fff !important;
  border-radius: 12px 12px 0 0 !important;
  color-scheme: light !important;
}}
html body div[data-testid="stAppViewContainer"] details[data-testid="stExpander"][open] > summary *,
html body .stApp details[data-testid="stExpander"][open] > summary span,
html body .stApp details[data-testid="stExpander"][open] > summary p,
html body .stApp details[data-testid="stExpander"][open] > summary div {{
  color: #fff !important;
  -webkit-text-fill-color: #fff !important;
  background: transparent !important;
}}
html body div[data-testid="stAppViewContainer"] details[data-testid="stExpander"][open] > summary svg *,
html body .stApp details[data-testid="stExpander"][open] > summary svg * {{
  fill: #fff !important;
  stroke: #fff !important;
}}
/* Content div */
html body div[data-testid="stAppViewContainer"] details[data-testid="stExpander"] > div,
html body .stApp details[data-testid="stExpander"] > div,
html body .stApp details[data-testid="stExpander"] > div[data-testid="stExpanderDetails"] {{
  background: {T["card"]} !important;
  background-color: {T["card"]} !important;
  --background-color: {T["card"]} !important;
  color-scheme: light !important;
  padding: 1rem 1.1rem 1.2rem !important;
  border-radius: 0 0 12px 12px !important;
}}
html body .stApp details[data-testid="stExpander"] > div * {{
  color-scheme: light !important;
}}
html body .stApp details[data-testid="stExpander"] > div p,
html body .stApp details[data-testid="stExpander"] > div label,
html body .stApp details[data-testid="stExpander"] > div span:not(.site-header-ai),
html body .stApp details[data-testid="stExpander"] > div small {{
  color: {T["text"]} !important;
  -webkit-text-fill-color: {T["text"]} !important;
}}
/* Pulsanti dentro expander */
html body .stApp details[data-testid="stExpander"] .stButton > button {{
  background: {T["card"]} !important;
  background-color: {T["card"]} !important;
  color: {T["text"]} !important;
  -webkit-text-fill-color: {T["text"]} !important;
  border: 1.5px solid {T["border2"]} !important;
  border-radius: 10px !important;
  color-scheme: light !important;
}}
html body .stApp details[data-testid="stExpander"] .stButton > button:hover {{
  background: {T["hover"]} !important;
  background-color: {T["hover"]} !important;
  color: {T["accent"]} !important;
  -webkit-text-fill-color: {T["accent"]} !important;
  border-color: {T["accent"]} !important;
}}
html body .stApp details[data-testid="stExpander"] .stButton > button[kind="primary"],
html body .stApp details[data-testid="stExpander"] .stButton > button[data-testid*="primary"] {{
  background: linear-gradient(135deg, {T["accent"]} 0%, {T["accent2"]} 100%) !important;
  background-color: {T["accent"]} !important;
  color: #fff !important;
  -webkit-text-fill-color: #fff !important;
  border-color: transparent !important;
  box-shadow: 0 3px 14px {T["accent"]}44 !important;
}}
/* Input/textarea dentro expander */
html body .stApp details[data-testid="stExpander"] input,
html body .stApp details[data-testid="stExpander"] textarea {{
  background: {T["bg2"]} !important;
  background-color: {T["bg2"]} !important;
  color: {T["text"]} !important;
  -webkit-text-fill-color: {T["text"]} !important;
  border: 1.5px solid {T["border"]} !important;
  color-scheme: light !important;
}}
/* NumberInput +/- buttons */
html body .stApp details[data-testid="stExpander"] [data-testid="stNumberInput"] button {{
  background: {T["bg2"]} !important;
  background-color: {T["bg2"]} !important;
  color: {T["text"]} !important;
  -webkit-text-fill-color: {T["text"]} !important;
  color-scheme: light !important;
}}

/* ── Coppia pulsanti azioni esercizio (Genera variante + Cambia esercizio)
   Entrambi usano lo stile outline-accent: bordo teal, sfondo trasparente.
   Il marker .btn-outline-accent-marker è inserito prima di CIASCUN button.
   ─────────────────────────────────────────────────────────────────────── */
[data-testid="stVerticalBlock"] > div:has(.btn-outline-accent-marker) + div button,
.element-container:has(.btn-outline-accent-marker) + .element-container button {{
  background: transparent !important;
  background-color: transparent !important;
  color: {T["accent"]} !important;
  -webkit-text-fill-color: {T["accent"]} !important;
  border: 1.5px solid {T["accent"]} !important;
  border-radius: 10px !important;
  font-weight: 700 !important;
  font-size: .88rem !important;
  min-height: 48px !important;
  box-shadow: none !important;
  color-scheme: light !important;
}}
[data-testid="stVerticalBlock"] > div:has(.btn-outline-accent-marker) + div button:hover,
.element-container:has(.btn-outline-accent-marker) + .element-container button:hover {{
  background: {T["accent_light"]} !important;
  background-color: {T["accent_light"]} !important;
  color: {T["accent"]} !important;
  -webkit-text-fill-color: {T["accent"]} !important;
  box-shadow: 0 2px 12px {T["accent"]}22 !important;
}}
</style>""", unsafe_allow_html=True)

    # ── JS DOM injection: unico modo affidabile per battere gli inline style
    # di Streamlit sul <summary>. window.parent.document accede al DOM reale.
    _c_card    = T["card"]
    _c_text    = T["text"]
    _c_text2   = T["text2"]
    _c_muted   = T["muted"]
    _c_accent  = T["accent"]
    _c_accent2 = T["accent2"]
    _c_border2 = T["border2"]
    _c_hover   = T["hover"]
    _c_bg2     = T["bg2"]
    components.html(f"""
<script>
(function() {{
  var doc = window.parent.document;

  function applyExpanderStyles() {{
    doc.querySelectorAll('details[data-testid="stExpander"]').forEach(function(exp) {{
      // Container
      exp.style.setProperty('background', '{_c_card}', 'important');
      exp.style.setProperty('background-color', '{_c_card}', 'important');
      exp.style.setProperty('border', '2px solid {_c_border2}', 'important');
      exp.style.setProperty('border-radius', '14px', 'important');
      exp.style.setProperty('overflow', 'hidden', 'important');
      exp.style.setProperty('margin-bottom', '.5rem', 'important');

      // Summary
      var summary = exp.querySelector(':scope > summary');
      if (summary) {{
        if (exp.open) {{
          summary.style.setProperty('background', 'linear-gradient(135deg,{_c_accent} 0%,{_c_accent2} 100%)', 'important');
          summary.style.setProperty('background-color', '{_c_accent}', 'important');
          summary.style.setProperty('color', '#ffffff', 'important');
          summary.style.setProperty('-webkit-text-fill-color', '#ffffff', 'important');
          summary.style.setProperty('border-radius', '12px 12px 0 0', 'important');
        }} else {{
          summary.style.setProperty('background', '{_c_card}', 'important');
          summary.style.setProperty('background-color', '{_c_card}', 'important');
          summary.style.setProperty('color', '{_c_text}', 'important');
          summary.style.setProperty('-webkit-text-fill-color', '{_c_text}', 'important');
          summary.style.setProperty('border-radius', '12px', 'important');
        }}
        summary.style.setProperty('font-family', 'DM Sans, sans-serif', 'important');
        summary.style.setProperty('font-weight', '700', 'important');
        summary.style.setProperty('font-size', '.9rem', 'important');
        summary.style.setProperty('padding', '.85rem 1.1rem', 'important');

        // Summary children text
        summary.querySelectorAll('span, p, div').forEach(function(el) {{
          if (exp.open) {{
            el.style.setProperty('color', '#ffffff', 'important');
            el.style.setProperty('-webkit-text-fill-color', '#ffffff', 'important');
          }} else {{
            el.style.setProperty('color', '{_c_text}', 'important');
            el.style.setProperty('-webkit-text-fill-color', '{_c_text}', 'important');
          }}
          el.style.setProperty('background', 'transparent', 'important');
        }});

        // SVG arrow
        summary.querySelectorAll('svg, svg *').forEach(function(el) {{
          if (exp.open) {{
            el.style.setProperty('fill', '#ffffff', 'important');
            el.style.setProperty('stroke', '#ffffff', 'important');
          }} else {{
            el.style.setProperty('fill', '{_c_text2}', 'important');
            el.style.setProperty('stroke', '{_c_text2}', 'important');
          }}
        }});

        // Re-apply on toggle
        if (!exp.__toggleBound) {{
          exp.__toggleBound = true;
          exp.addEventListener('toggle', function() {{
            setTimeout(applyExpanderStyles, 10);
          }});
        }}
      }}

      // Content div
      var contentDiv = exp.querySelector(':scope > div');
      if (contentDiv) {{
        contentDiv.style.setProperty('background', '{_c_card}', 'important');
        contentDiv.style.setProperty('background-color', '{_c_card}', 'important');
        contentDiv.style.setProperty('padding', '1rem 1.1rem 1.2rem', 'important');
        contentDiv.style.setProperty('border-radius', '0 0 12px 12px', 'important');
        // Text inside content
        contentDiv.querySelectorAll('p, label, span:not([class*="site-header"]), small').forEach(function(el) {{
          el.style.setProperty('color', '{_c_text}', 'important');
          el.style.setProperty('-webkit-text-fill-color', '{_c_text}', 'important');
        }});
        // Inputs/textarea inside content
        contentDiv.querySelectorAll('input, textarea').forEach(function(el) {{
          el.style.setProperty('background', '{_c_bg2}', 'important');
          el.style.setProperty('background-color', '{_c_bg2}', 'important');
          el.style.setProperty('color', '{_c_text}', 'important');
          el.style.setProperty('-webkit-text-fill-color', '{_c_text}', 'important');
          el.style.setProperty('border', '1.5px solid {_c_border2}', 'important');
        }});
        // Buttons inside content (secondary)
        contentDiv.querySelectorAll('.stButton > button').forEach(function(btn) {{
          if (!btn.dataset.kind || btn.dataset.kind !== 'primary') {{
            btn.style.setProperty('background', '{_c_card}', 'important');
            btn.style.setProperty('background-color', '{_c_card}', 'important');
            btn.style.setProperty('color', '{_c_text}', 'important');
            btn.style.setProperty('-webkit-text-fill-color', '{_c_text}', 'important');
            btn.style.setProperty('border', '1.5px solid {_c_border2}', 'important');
            btn.style.setProperty('border-radius', '10px', 'important');
          }}
        }});
      }}
    }});
  }}

  // Run immediately
  applyExpanderStyles();

  // Watch for any DOM changes (Streamlit re-renders)
  var observer = new MutationObserver(function(mutations) {{
    var relevant = mutations.some(function(m) {{
      return Array.from(m.addedNodes).some(function(n) {{
        return n.nodeType === 1 && (n.matches && n.matches('details') ||
               (n.querySelector && n.querySelector('details[data-testid="stExpander"]') !== null));
      }});
    }});
    if (relevant) applyExpanderStyles();
  }});
  observer.observe(doc.body, {{ childList: true, subtree: true }});
}})();
</script>
""", height=0, scrolling=False)

    st.markdown(
        '<div style="background:linear-gradient(135deg,#1E3A5F 0%,#2563EB 100%);'
        'border-radius:16px;padding:1.1rem 1.4rem;margin-bottom:.9rem;">'
        '<div style="display:flex;align-items:center;gap:14px;">'
        '<span style="font-size:2rem;">✏️</span>'
        '<div style="flex:1;">'
        '<div style="font-family:DM Sans,sans-serif;font-size:1.35rem;font-weight:900;color:#fff;letter-spacing:-.01em;">'
        'Revisione Bozza</div>'
        '<div style="font-size:1rem;color:#ffffffcc;margin-top:3px;">'
        + materia_str + ' · ' + scuola_str + ' · ' + argomento_str + '</div>'
        '</div>'
        '<div style="background:#ffffff22;border:1px solid #ffffff44;border-radius:18px;'
        'padding:5px 15px;font-size:.88rem;font-weight:800;color:#fff;white-space:nowrap;">'
        + str(n_blocks) + ' esercizi</div>'
        '</div>'
        '<div style="font-size:.88rem;color:#ffffff99;margin-top:.5rem;padding-top:.45rem;'
        'border-top:1px solid #ffffff22;">'
        'Seleziona l\'esercizio, modifica con l\'AI o cambia i dati. '
        'Premi <strong style="color:#fff;">Conferma e genera PDF</strong> quando sei soddisfatto.'
        '</div></div>',
        unsafe_allow_html=True
    )

    if not blocks:
        st.warning("⚠️ Nessun esercizio trovato. Torna indietro e rigenera.")
        if st.button("← Torna alla configurazione",
                     help="Torna al form di configurazione per cambiare materia, argomento o numero di esercizi."):
            st.session_state.stage = STAGE_INPUT; st.rerun()
        return

    # Rimuovi il prefisso "Esercizio N:" o "Esercizio N. " già presente nel titolo
    def _clean_title(title: str) -> str:
        return re.sub(r'^Esercizio\s*\d+\s*[:\.\-]\s*', '', title, flags=re.IGNORECASE).strip()

    labels = [f"Esercizio {i+1}: {_clean_title(b['title'])}" for i, b in enumerate(blocks)]

    idx = st.session_state.review_sel_idx
    if idx >= n_blocks: idx = 0

    sel_label = st.selectbox(
        "Seleziona esercizio da rivedere:",
        labels, index=idx, key="review_selectbox"
    )
    idx = labels.index(sel_label)
    st.session_state.review_sel_idx = idx

    # ── Badge punteggio totale calcolato live ─────────────────────────────────
    if mostra_punteggi:
        _latex_live = reconstruct_latex(
            st.session_state.review_preamble,
            st.session_state.review_blocks,
        )
        _totale_live = conta_punti_latex(_latex_live)
        _ok   = _totale_live == punti_totali
        _diff = _totale_live - punti_totali
        _icon  = "✅" if _ok else ("⬆️" if _diff > 0 else "⬇️")
        _color = T["success"] if _ok else T["warn"]
        _label = f"{_totale_live} pt" if _ok else f"{_totale_live} pt ({_diff:+d} pt rispetto al target)"
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:10px;'
            f'background:{_color}18;border:1.5px solid {_color}44;'
            f'border-radius:10px;padding:.5rem 1rem;margin-bottom:.6rem;">'
            f'<span style="font-size:1rem;">{_icon}</span>'
            f'<span style="font-family:\'DM Sans\',sans-serif;font-size:.88rem;'
            f'font-weight:700;color:{_color};">'
            f'Punteggio totale calcolato: <strong>{_label}</strong>'
            f'</span>'
            f'<span style="font-size:.8rem;color:{T["muted"]};margin-left:auto;">'
            f'Target: {punti_totali} pt'
            f'</span></div>',
            unsafe_allow_html=True,
        )
        if not _ok:
            logger.info(
                "STAGE_REVIEW: totale live=%d pt, target=%d pt, diff=%+d pt",
                _totale_live, punti_totali, _diff,
            )

    block = blocks[idx]
    title = block["title"]
    body  = block["body"]

    # ══════════════════════════════════════════════════════════════════════════
    #  LAYOUT DUE COLONNE
    #  Sinistra [2]: box unico — KaTeX + Modifica AI + Ricalibra Punteggi
    #  Destra   [3]: anteprima PDF una pagina alla volta con navigazione ◀▶
    # ══════════════════════════════════════════════════════════════════════════
    col_left, col_pdf = st.columns([2, 3], gap="medium")

    # ── COLONNA SINISTRA ──────────────────────────────────────────────────────
    with col_left:
        with st.container(border=True):

            # ── Anteprima KaTeX dell'esercizio selezionato ───────────────────
            katex_html = _make_katex_html(title, body, T)
            est_height = max(220, min(550, 160 + len(body) // 4))
            components.html(katex_html, height=est_height, scrolling=True)

            if re.search(r"\\begin\{(tikzpicture|axis)\}", body):
                st.info("📊 Questo esercizio contiene un grafico — sarà visibile nel PDF scaricato.")

            # ── Pulsante ANNULLA MODIFICA ─────────────────────────────────
            _undo_key = f"_undo_block_{idx}"
            if _undo_key in st.session_state:
                _undo_backup = st.session_state[_undo_key]
                _undo_col1, _undo_col2 = st.columns([1, 2])
                with _undo_col1:
                    st.markdown(
                        f'''<style>
  [data-testid="stVerticalBlock"] > div:has(.undo-btn-marker) + div > div > button,
  [data-testid="stVerticalBlock"] > div:has(.undo-btn-marker) + div button {{
    background: transparent !important;
    background-color: transparent !important;
    color: {T["accent"]} !important;
    -webkit-text-fill-color: {T["accent"]} !important;
    border: 1.5px solid {T["accent"]} !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    box-shadow: none !important;
  }}
  [data-testid="stVerticalBlock"] > div:has(.undo-btn-marker) + div > div > button:hover,
  [data-testid="stVerticalBlock"] > div:has(.undo-btn-marker) + div button:hover {{
    background: {T["accent_light"]} !important;
    background-color: {T["accent_light"]} !important;
    color: {T["accent2"]} !important;
    -webkit-text-fill-color: {T["accent2"]} !important;
  }}
</style>
<div class="undo-btn-marker" style="display:none;height:0;line-height:0"></div>''',
                        unsafe_allow_html=True
                    )
                    if st.button(
                        "↩️ Annulla modifica",
                        key=f"undo_btn_{idx}",
                        use_container_width=True,
                        help="Ripristina la versione dell'esercizio precedente alla modifica"
                    ):
                        st.session_state.review_blocks[idx] = dict(_undo_backup)
                        del st.session_state[_undo_key]
                        # Pulisci item_pt_ keys per questo esercizio
                        for _k in list(st.session_state.keys()):
                            if _k.startswith(f"item_pt_{idx}_"):
                                del st.session_state[_k]
                        if "recalibra_pts" in st.session_state:
                            del st.session_state["recalibra_pts"]
                        _undo_latex = reconstruct_latex(
                            st.session_state.review_preamble,
                            st.session_state.review_blocks
                        )
                        _undo_latex = fix_items_environment(_undo_latex)
                        _undo_latex = rimuovi_vspace_corpo(_undo_latex)
                        if mostra_punteggi:
                            _undo_latex = rimuovi_punti_subsection(_undo_latex)
                            _undo_latex = prepara_esercizi_aperti(_undo_latex, punti_totali)
                            _undo_latex = riscala_punti(_undo_latex, punti_totali)
                        if con_griglia:
                            _undo_latex = inietta_griglia(_undo_latex, punti_totali)
                        st.session_state.verifiche["A"]["latex"]           = _undo_latex
                        st.session_state.verifiche["A"]["latex_originale"] = _undo_latex
                        _undo_pdf, _ = compila_pdf(_undo_latex)
                        if _undo_pdf:
                            st.session_state.verifiche["A"]["pdf"]    = _undo_pdf
                            st.session_state.verifiche["A"]["pdf_ts"] = time.time()
                            st.session_state.verifiche["A"]["preview"] = True
                            _undo_imgs, _ = pdf_to_images_bytes(_undo_pdf)
                            st.session_state.preview_images = _undo_imgs or []
                            st.session_state.preview_page   = 0
                        st.toast("↩️ Modifica annullata — versione precedente ripristinata!", icon="↩️")
                        time.sleep(0.2); st.rerun()
                with _undo_col2:
                    st.markdown(
                        f'<div style="font-size:.72rem;color:{T["muted"]};font-family:DM Sans,sans-serif;'
                        f'padding:.3rem 0;line-height:1.4;">'
                        f'🕐 Versione precedente disponibile</div>',
                        unsafe_allow_html=True
                    )

            # ── Pulsanti Quick Regen — senza label ridondante ─────────────
            _qr_col1, _qr_col2 = st.columns(2, gap="small")
            with _qr_col1:
                st.markdown(
                    '<div class="btn-outline-accent-marker" style="display:none;height:0;line-height:0"></div>',
                    unsafe_allow_html=True
                )
                quick_regen = st.button(
                    "Cambia i numeri",
                    key=f"quick_regen_{idx}",
                    use_container_width=True,
                    help="Genera nuovi valori e dati numerici mantenendo la stessa struttura dell'esercizio.",
                )
            with _qr_col2:
                st.markdown(
                    '<div class="btn-outline-accent-marker" style="display:none;height:0;line-height:0"></div>',
                    unsafe_allow_html=True
                )
                cambia_tutto = st.button(
                    "Cambia esercizio",
                    key=f"cambia_tutto_{idx}",
                    use_container_width=True,
                    help="Genera un esercizio completamente diverso in struttura e tipologia, mantenendo argomento e pertinenza didattica",
                )
            # Placeholder feedback immediato — sotto i pulsanti, nella colonna sinistra
            _action_ph = st.empty()
            if quick_regen:
                _action_ph.info(f"Generazione variante esercizio {idx+1}…")
            elif cambia_tutto:
                _action_ph.info(f"Generazione nuovo esercizio {idx+1}…")

            st.markdown("<div style='height:.4rem'></div>", unsafe_allow_html=True)

            # ── Modifica con AI — fuori dall'expander, sempre visibile ────────
            st.markdown(
                '<div style="font-size:.95rem;color:' + T["text2"] + ';margin-bottom:.5rem;'
                'font-family:DM Sans,sans-serif;line-height:1.5;">'
                'Descrivi la modifica — l\'AI rigenererà solo questo esercizio.'
                '</div>'
                '<div style="font-size:.9rem;color:' + T["warn"] + ';margin-bottom:.7rem;'
                'font-family:DM Sans,sans-serif;font-weight:600;'
                'background:' + T["warn"] + '18;border:1px solid ' + T["warn"] + '44;'
                'border-radius:8px;padding:.4rem .7rem;">'
                'Per cambiare i punteggi usa il pannello qui sotto.</div>',
                unsafe_allow_html=True
            )
            istruzione = st.text_area(
                f"Modifica esercizio {idx+1}",
                placeholder="es. Aumenta la difficoltà · Cambia i numeri · Converti in Vero/Falso · Aggiungi un sottopunto",
                key=f"rw_istr_{idx}",
                label_visibility="collapsed",
                height=80,
            )
            rigenera = st.button(
                "✏️ Applica modifica", key=f"rw_btn_{idx}",
                use_container_width=True, disabled=not istruzione.strip(),
                type="primary",
                help="L'AI applica le tue istruzioni e rigenera solo questo esercizio, senza modificare gli altri.",
            )
            # ── Placeholder feedback immediato sotto il pulsante cliccato ─────
            _loading_ph = st.empty()
            if rigenera and istruzione.strip():
                _istr_low_quick = istruzione.lower()
                if any(kw in _istr_low_quick for kw in _SCORE_KEYWORDS):
                    _loading_ph.warning(
                        "⚠️ **Hai menzionato punteggi / punti.**\n\n"
                        "Per modificare i punti usa il pannello **⚖️ Ricalibra Punteggi** "
                        "qui sopra — imposta i valori desiderati e premi **Applica Punteggi**. "
                        "Il pannello AI è riservato alle modifiche al contenuto (testo, difficoltà, formato)."
                    )
                else:
                    _loading_ph.info(f"Elaborazione in corso — modifico l'esercizio {idx+1}…")


    # ── COLONNA DESTRA — anteprima PDF una pagina alla volta ─────────────────
    with col_pdf:
        st.markdown(
            '<div style="font-size:.72rem;font-weight:700;color:' + T["muted"] + ';'
            'text-transform:uppercase;letter-spacing:.05em;margin-bottom:.5rem;">'
            '📄 Anteprima PDF completo</div>',
            unsafe_allow_html=True
        )
        # Controlla se il PDF è cambiato e aggiorna le preview se necessario
        vA = st.session_state.verifiche.get("A", {})
        current_pdf_ts = vA.get("pdf_ts")
        last_preview_ts = st.session_state.get("last_preview_ts", 0)
        
        # Se il timestamp del PDF è più recente dell'ultima preview, rigenera le immagini
        if current_pdf_ts and current_pdf_ts > last_preview_ts:
            vA_pdf = vA.get("pdf")
            if vA_pdf:
                try:
                    new_imgs, _ = pdf_to_images_bytes(vA_pdf)
                    st.session_state.preview_images = new_imgs or []
                    st.session_state.last_preview_ts = current_pdf_ts
                    logger.info(f"Preview images aggiornate - timestamp PDF: {current_pdf_ts}")
                except Exception as e:
                    logger.error(f"Errore aggiornamento preview: {e}")
        
        imgs = st.session_state.preview_images
        if imgs:
            n_pages  = len(imgs)
            _pg = max(0, min(st.session_state.get("preview_page", 0), n_pages - 1))

            st.image(imgs[_pg], use_container_width=True)

            if n_pages > 1:
                st.markdown("<div style='height:.2rem'></div>", unsafe_allow_html=True)
                _pc, _pm, _pn = st.columns([1, 2, 1])
                with _pc:
                    if st.button("◀", key="prev_pg", use_container_width=True,
                                 disabled=(_pg == 0)):
                        st.session_state.preview_page = _pg - 1; st.rerun()
                with _pm:
                    st.markdown(
                        f'<div style="text-align:center;font-size:.75rem;font-weight:600;'
                        f'color:{T["text2"]};font-family:DM Sans,sans-serif;padding:.35rem 0;">'
                        f'Pag. {_pg+1} / {n_pages}</div>',
                        unsafe_allow_html=True
                    )
                with _pn:
                    if st.button("▶", key="next_pg", use_container_width=True,
                                 disabled=(_pg == n_pages - 1)):
                        st.session_state.preview_page = _pg + 1; st.rerun()
        else:
            vA_pdf = st.session_state.verifiche["A"].get("pdf")
            if vA_pdf:
                b64 = base64.b64encode(vA_pdf).decode()
                st.markdown(
                    '<iframe src="data:application/pdf;base64,' + b64 + '#toolbar=0&navpanes=0&scrollbar=1" '
                    'style="width:100%;height:560px;border:none;border-radius:8px;"></iframe>',
                    unsafe_allow_html=True
                )
            else:
                st.caption("Anteprima non disponibile.")

    # ── IDEA #3: Quick Regen — variante rapida handler ──────────────────────
    if quick_regen:
        _pts_custom_qr = st.session_state.get("recalibra_pts", [])
        if _pts_custom_qr and len(_pts_custom_qr) == n_blocks:
            _qr_target_pts = int(_pts_custom_qr[idx])
        else:
            _qr_target_pts = parse_pts_from_block_body(body)

        if mostra_punteggi and _qr_target_pts > 0:
            _qr_punti_nota = (
                f"Assegna esattamente {_qr_target_pts} pt in totale a questo esercizio, "
                f"distribuendoli tra i sotto-punti con il formato (N pt) su ogni \\item. "
                f"La somma DEVE essere {_qr_target_pts} pt."
            )
        elif mostra_punteggi:
            _qr_punti_nota = f"Mantieni il formato (X pt) su ogni \\item."
        else:
            _qr_punti_nota = "NON inserire punteggi (X pt)."

        _qr_prompt = (
            f"Sei un docente esperto di {materia_str} e LaTeX.\n"
            f"Devi creare una VARIANTE di questo esercizio: cambia i dati numerici, "
            f"i nomi delle variabili, i valori specifici — mantenendo IDENTICA "
            f"la struttura, la tipologia e il livello di difficoltà.\n\n"
            f"MATERIA: {materia_str}\n"
            f"ARGOMENTO: {argomento_str}\n"
            f"⚠️ L'esercizio DEVE restare su '{argomento_str}' in '{materia_str}'.\n\n"
            f"ESERCIZIO ORIGINALE:\n\\subsection*{{{title}}}\n{body}\n\n"
            f"REGOLE:\n"
            f"- Cambia SOLO i dati (numeri, coefficienti, nomi, valori) — "
            f"NON la struttura, NON il tipo, NON la difficoltà.\n"
            f"- Se ci sono grafici TikZ/pgfplots, DEVI generare codice TikZ COMPLETO aggiornato ai nuovi dati. "
              f"NON usare \\includegraphics{{placeholder}} né commenti '%% inserire grafico'.\n"
            f"- NON inserire MAI commenti LaTeX (%% ...) nel corpo degli esercizi.\n"
            f"- Mantieni lo STESSO numero di sotto-punti.\n"
            f"- {_qr_punti_nota}\n"
            f"- Restituisci SOLO il blocco \\subsection*{{...}} con la variante.\n"
            f"- NON includere preambolo o \\begin{{document}}.\n"
            f"OUTPUT: SOLO codice LaTeX del blocco esercizio."
        )
        st.session_state[f"_undo_block_{idx}"] = dict(st.session_state.review_blocks[idx])
        _action_ph.empty()
        with _action_ph.status(f"Generazione variante esercizio {idx+1}…", expanded=True) as _qr_st:
            try:
                _qr_model = genai.GenerativeModel(modello_rw)
                _qr_resp = _qr_model.generate_content(_qr_prompt)
                _qr_nuovo = _qr_resp.text.replace("```latex","").replace("```","").strip()
                _qr_m = re.match(r"\\subsection\*\{([^}]*)\}(.*)", _qr_nuovo, re.DOTALL)
                if _qr_m:
                    _qr_new_title = _qr_m.group(1)
                    _qr_new_body  = _qr_m.group(2).strip()
                else:
                    _qr_new_title = title
                    _qr_new_body  = _qr_nuovo
                _qr_new_title = re.sub(r'\s*\(\d+\s*pt\)', '', _qr_new_title).strip()
                if mostra_punteggi and _qr_target_pts > 0:
                    _qr_new_body = riscala_single_block(_qr_new_title, _qr_new_body, _qr_target_pts)
                st.session_state.review_blocks[idx]["title"] = _qr_new_title
                st.session_state.review_blocks[idx]["body"]  = _qr_new_body
                if "recalibra_pts" in st.session_state:
                    del st.session_state["recalibra_pts"]
                _qr_latex = reconstruct_latex(
                    st.session_state.review_preamble,
                    st.session_state.review_blocks
                )
                _qr_latex = fix_items_environment(_qr_latex)
                _qr_latex = rimuovi_vspace_corpo(_qr_latex)
                _qr_latex = rimuovi_punti_subsection(_qr_latex)
                if con_griglia:
                    _qr_latex = inietta_griglia(_qr_latex, punti_totali)
                st.session_state.verifiche["A"]["latex"]           = _qr_latex
                st.session_state.verifiche["A"]["latex_originale"] = _qr_latex
                _qr_pdf, _ = compila_pdf(_qr_latex)
                if _qr_pdf:
                    st.session_state.verifiche["A"]["pdf"]    = _qr_pdf
                    st.session_state.verifiche["A"]["pdf_ts"] = time.time()
                    st.session_state.verifiche["A"]["preview"] = True
                    _qr_imgs, _ = pdf_to_images_bytes(_qr_pdf)
                    st.session_state.preview_images = _qr_imgs or []
                    st.session_state.preview_page   = 0
                _qr_st.update(label="Variante pronta!", state="complete", expanded=False)
                st.toast(f"Variante esercizio {idx+1} generata!", icon="✅")
                time.sleep(0.3); st.rerun()
            except Exception as _qr_e:
                st.error(f"Errore: {_qr_e}")

    # ── Logica modifica AI ────────────────────────────────────────────────────
    if rigenera and istruzione.strip():
        _istr_low = istruzione.lower()

        # ── Rilevamento richieste punteggio ───────────────────────────────────
        # L'avviso è già mostrato inline sotto il pulsante (via _loading_ph).
        _is_score_req = any(kw in _istr_low for kw in _SCORE_KEYWORDS)
        if not _is_score_req:
            # ── Regen AI con preservazione punti ─────────────────────────────
            # Cattura i punti correnti dell'esercizio PRIMA della regen.
            # Se recalibra_pts è stato già impostato dall'utente usa quello,
            # altrimenti legge dal corpo del blocco corrente.
            _pts_custom = st.session_state.get("recalibra_pts", [])
            if _pts_custom and len(_pts_custom) == n_blocks:
                _exercise_target_pts = int(_pts_custom[idx])
            else:
                _exercise_target_pts = parse_pts_from_block_body(body)

            # Il prompt dice all'AI quanti pt deve assegnare a questo esercizio.
            # La funzione riscala_single_block lo corregge deterministicamente dopo.
            if mostra_punteggi and _exercise_target_pts > 0:
                punti_nota = (
                    f"Assegna esattamente {_exercise_target_pts} pt in totale a questo esercizio, "
                    f"distribuendoli tra i sotto-punti con il formato (N pt) su ogni \\item. "
                    f"La somma DEVE essere {_exercise_target_pts} pt."
                )
            elif mostra_punteggi:
                punti_nota = (
                    f"Mantieni il formato (X pt) su ogni \\item. "
                    f"La somma totale dei punti DEVE essere esattamente {punti_totali} pt."
                )
            else:
                punti_nota = "NON inserire punteggi (X pt)."

            # Rileva se l'esercizio originale ha un grafico (TikZ/pgfplots)
            _ha_grafico = bool(re.search(r'\\\\begin\{(tikzpicture|axis|pgfpicture)\}', body))
            _grafici_rule_rw = (
                "- GRAFICI: l'esercizio originale contiene un grafico TikZ/pgfplots. "
                "SE la modifica lo richiede o mantiene il grafico, DEVI generare CODICE TikZ COMPLETO e FUNZIONANTE. "
                "NON scrivere mai commenti come '% qui andrebbe il grafico' o '% inserire figura' o '\\includegraphics{placeholder}'. "
                "Il grafico DEVE essere codice LaTeX compilabile. Se non puoi generarlo, rimuovi la richiesta grafica dall'esercizio."
                if _ha_grafico else
                "- NON aggiungere \\includegraphics, placeholder o commenti '% qui andrebbe'. "
                "Se l'istruzione richiede un grafico, usare SOLO codice TikZ/pgfplots completo e compilabile."
            )
            _prompt_rw = (
                f"Sei un docente esperto di {materia_str} e LaTeX.\n"
                f"Devi MODIFICARE questo esercizio secondo l'istruzione del docente, "
                f"ma SENZA MAI cambiare la materia o l'argomento della verifica.\n\n"
                f"MATERIA: {materia_str}\n"
                f"ARGOMENTO DELLA VERIFICA: {argomento_str}\n"
                f"⚠️ REGOLA ASSOLUTA E INVIOLABILE: l'esercizio deve restare su '{argomento_str}' "
                f"in '{materia_str}'. NON introdurre mai argomenti diversi (es. se la verifica è "
                f"sulla Parabola non generare studio di funzione, derivate, integrali ecc.).\n\n"
                f"ESERCIZIO ORIGINALE:\n\\subsection*{{{title}}}\n{body}\n\n"
                f"ISTRUZIONE DEL DOCENTE: {istruzione.strip()}\n\n"
                f"REGOLE FONDAMENTALI:\n"
                f"- LUNGHEZZA MASSIMA: l'esercizio modificato non deve superare le 8-10 righe di testo.\n"
                f"- VIETATO ASSOLUTO: NON inserire MAI soluzioni, risposte o risultati.\n"
                f"- VIETATO MAPPE E DIAGRAMMI: NON generare MAI mappe, diagrammi spaziali o geografici.\n"
                f"- Applica SOLO la modifica richiesta. NON riscrivere da zero, modifica l'esistente.\n"
                f"- Mantieni OBBLIGATORIAMENTE l'argomento '{argomento_str}'.\n"
                f"- Restituisci SOLO il blocco \\subsection*{{...}} con il nuovo esercizio.\n"
                f"- Mantieni struttura LaTeX (\\subsection*, enumerate, \\item[a]), ecc).\n"
                f"- {punti_nota}\n"
                f"- {_grafici_rule_rw}\n"
                f"- NON inserire MAI commenti LaTeX (%% ...) nel corpo degli esercizi.\n"
                f"- NON includere preambolo o \\begin{{document}}.\n"
                f"OUTPUT: SOLO codice LaTeX del blocco esercizio."
            )
            st.session_state[f"_undo_block_{idx}"] = dict(st.session_state.review_blocks[idx])
            _loading_ph.empty()
            with _loading_ph.status(f"Modifica esercizio {idx+1} in corso…", expanded=True) as _rw_st:
                try:
                    model_rw_obj = genai.GenerativeModel(modello_rw)
                    resp  = model_rw_obj.generate_content(_prompt_rw)
                    nuovo = resp.text.replace("```latex","").replace("```","").strip()
                    m_rw  = re.match(r"\\subsection\*\{([^}]*)\}(.*)", nuovo, re.DOTALL)
                    if m_rw:
                        new_title = m_rw.group(1)
                        new_body  = m_rw.group(2).strip()
                    else:
                        new_title = title
                        new_body  = nuovo

                    # Rimuovi eventuale (N pt) che l'AI ha messo nel titolo
                    new_title = re.sub(r'\s*\(\d+\s*pt\)', '', new_title).strip()

                    # Correzione deterministica dei punti: porta la somma esatta
                    # al valore che aveva l'esercizio prima della modifica AI.
                    if mostra_punteggi and _exercise_target_pts > 0:
                        new_body = riscala_single_block(new_title, new_body, _exercise_target_pts)

                    st.session_state.review_blocks[idx]["title"] = new_title
                    st.session_state.review_blocks[idx]["body"]  = new_body

                    # Reset pannello ricalibra: rilegge i punteggi aggiornati
                    if "recalibra_pts" in st.session_state:
                        del st.session_state["recalibra_pts"]

                    # Fix: ricompila il PDF e aggiorna la preview dopo la modifica
                    _latex_rw = reconstruct_latex(
                        st.session_state.review_preamble,
                        st.session_state.review_blocks
                    )
                    _latex_rw = fix_items_environment(_latex_rw)
                    _latex_rw = rimuovi_vspace_corpo(_latex_rw)
                    _latex_rw = rimuovi_punti_subsection(_latex_rw)
                    if con_griglia:
                        _latex_rw = inietta_griglia(_latex_rw, punti_totali)
                    st.session_state.verifiche["A"]["latex"]           = _latex_rw
                    st.session_state.verifiche["A"]["latex_originale"] = _latex_rw
                    _pdf_rw, _err_rw = compila_pdf(_latex_rw)
                    if _pdf_rw:
                        st.session_state.verifiche["A"]["pdf"]    = _pdf_rw
                        st.session_state.verifiche["A"]["pdf_ts"] = time.time()
                        st.session_state.verifiche["A"]["preview"] = True
                        _imgs_rw, _ = pdf_to_images_bytes(_pdf_rw)
                        st.session_state.preview_images = _imgs_rw or []
                        st.session_state.preview_page   = 0

                    _rw_st.update(label="Modifica applicata!", state="complete", expanded=False)
                    time.sleep(0.4); st.rerun()
                except Exception as e:
                    st.error(f"Errore: {e}")

    # ── Logica "Cambia totalmente" — struttura diversa, argomento uguale ─────
    if cambia_tutto:
        _ct_pts = st.session_state.get("recalibra_pts", [])
        _ct_target_pts = (
            int(_ct_pts[idx]) if _ct_pts and len(_ct_pts) == n_blocks
            else parse_pts_from_block_body(body)
        )
        _ct_punti_nota = (
            f"Assegna esattamente {_ct_target_pts} pt totali, distribuendoli tra i sotto-punti con (N pt) su ogni \\item."
            if mostra_punteggi and _ct_target_pts > 0
            else ("Mantieni formato (X pt) su ogni \\item." if mostra_punteggi else "NON inserire punteggi.")
        )
        # Raccgli gli altri esercizi per controllo duplicati
        _altri_esercizi = []
        for j, block in enumerate(st.session_state.review_blocks):
            if j != idx:  # Salta l'esercizio da sostituire
                _altri_esercizi.append(f"\\subsection*{{{block['title']}}}\n{block['body'][:200]}...")
        
        _altri_testo = "\n".join(_altri_esercizi) if _altri_esercizi else "Nessun altro esercizio presente."
        
        _prompt_ct = (
            f"Sei un docente esperto di {materia_str} e LaTeX.\n"
            f"Genera un esercizio COMPLETAMENTE DIVERSO — diverso in struttura, tipologia e contenuto specifico — "
            f"ma che rimanga strettamente pertinente all'argomento e agli obiettivi didattici della verifica.\n\n"
            f"MATERIA: {materia_str}\n"
            f"ARGOMENTO DELLA VERIFICA: {argomento_str}\n"
            f"ESERCIZIO DA SOSTITUIRE (struttura e tipo da NON replicare):\n\\subsection*{{{title}}}\n{body}\n\n"
            f"ALTRI ESERCIZI GIA PRESENTI (da NON duplicare concettualmente):\n{_altri_testo}\n\n"
            f"REGOLE FONDAMENTALI:\n"
            f"- LUNGHEZZA MASSIMA: il nuovo esercizio non deve superare le 8-10 righe di testo.\n"
            f"- VIETATO ASSOLUTO: NON inserire MAI soluzioni, risposte o risultati. MAI scrivere '= X', 'la risposta è', 'il risultato è'.\n"
            f"- VIETATO MAPPE E DIAGRAMMI: NON generare MAI mappe, diagrammi spaziali o geografici.\n"
            f"- CONTROLLO DUPLICATI: ANALIZZA gli altri esercizi sopra. NON generare un esercizio che testi "
              f"lo stesso concetto matematico o la stessa abilità. Ogni esercizio deve essere UNICO concettualmente.\n"
            f"- MANTENIMENTO DIFFICOLTÀ: se questo è l'Esercizio 1 (Saperi Essenziali), deve rimanere accessibile e risolvibile in 5-8 minuti. "
              f"NON aumentare la difficoltà o la complessità.\n"
            f"- Cambia TIPO di esercizio (es. da calcolo numerico a dimostrazione, da aperto a V/F, ecc.).\n"
            f"- Cambia i concetti specifici testati, scegliendo aspetti diversi ma coerenti con '{argomento_str}'.\n"
            f"- L'esercizio DEVE restare su '{argomento_str}' in '{materia_str}'. NON introdurre altri argomenti.\n"
            f"- Restituisci SOLO il blocco \\subsection*{{...}} con il nuovo esercizio.\n"
            f"- Mantieni la struttura LaTeX (\\subsection*, enumerate, \\item[a]), ecc).\n"
            f"- {_ct_punti_nota}\n"
            f"- Se includi un grafico, usa SOLO codice TikZ/pgfplots COMPLETO e COMPILABILE. "
              f"NON usare \\includegraphics{{placeholder}} né commenti '%% inserire figura'.\n"
            f"- NON inserire MAI commenti LaTeX (%% ...) nel corpo degli esercizi.\n"
            f"- NON includere preambolo o \\begin{{document}}.\n"
        )
        st.session_state[f"_undo_block_{idx}"] = dict(st.session_state.review_blocks[idx])
        _action_ph.empty()
        with _action_ph.status(f"Generazione nuovo esercizio {idx+1}…", expanded=True) as _ct_st:
            try:
                _ct_model = genai.GenerativeModel(MODEL_FAST_ID)
                _ct_resp = _ct_model.generate_content(
                    [_prompt_ct],
                    generation_config=genai.GenerationConfig(temperature=0.95),
                ).text.strip()
                if _ct_resp.startswith("```"):
                    _ct_resp = re.sub(r"^```[a-z]*\n?", "", _ct_resp)
                    _ct_resp = re.sub(r"\n?```$", "", _ct_resp)
                _ct_m = re.match(r"\\subsection\*\{([^}]*)\}(.*)", _ct_resp, re.DOTALL)
                if _ct_m:
                    _ct_title = _ct_m.group(1)
                    _ct_body  = _ct_m.group(2).strip()
                    _ct_title = re.sub(r'\s*\(\d+\s*pt\)', '', _ct_title).strip()
                else:
                    _ct_title = title
                    _ct_body  = _ct_resp
                if mostra_punteggi and _ct_target_pts > 0:
                    _ct_body = riscala_single_block(_ct_title, _ct_body, _ct_target_pts)
                st.session_state.review_blocks[idx] = {
                    "title": _ct_title or title,
                    "body":  _ct_body,
                }
                _ct_latex = reconstruct_latex(
                    st.session_state.review_preamble,
                    st.session_state.review_blocks
                )
                _ct_latex = fix_items_environment(_ct_latex)
                _ct_latex = rimuovi_vspace_corpo(_ct_latex)
                _ct_latex = rimuovi_punti_subsection(_ct_latex)
                if con_griglia:
                    _ct_latex = inietta_griglia(_ct_latex, punti_totali)
                st.session_state.verifiche["A"]["latex"]           = _ct_latex
                st.session_state.verifiche["A"]["latex_originale"] = _ct_latex
                _ct_pdf, _ = compila_pdf(_ct_latex)
                if _ct_pdf:
                    st.session_state.verifiche["A"]["pdf"]    = _ct_pdf
                    st.session_state.verifiche["A"]["pdf_ts"] = time.time()
                    st.session_state.verifiche["A"]["preview"] = True
                    _ct_imgs, _ = pdf_to_images_bytes(_ct_pdf)
                    st.session_state.preview_images = _ct_imgs or []
                    st.session_state.preview_page   = 0
                _ct_st.update(label="Esercizio cambiato!", state="complete", expanded=False)
                st.toast(f"Esercizio {idx+1} cambiato!", icon="✅")
                time.sleep(0.3); st.rerun()
            except Exception as _ct_e:
                st.error(f"Errore: {_ct_e}")


    # ── Ricalibra Punteggi — sopra il pulsante Conferma ──────────────────
    if mostra_punteggi and n_blocks > 0:
        with st.expander("⚖️ Ricalibra Punteggi", expanded=False):

            # ── Intestazione compatta ──────────────────────────────────────
            st.markdown(
                f'<div class="rc-header-desc">'
                f'Imposta i punti per ogni sottopunto. '
                f'Il pulsante si sblocca quando il totale è esattamente '
                f'<strong>{punti_totali} pt</strong>.'
                f'</div>',
                unsafe_allow_html=True
            )

            # ── Raccogli tutti i sottopunti di tutti gli esercizi ──────────
            _all_new_item_pts = {}
            _grand_total_rc   = 0

            for _i, _b in enumerate(st.session_state.review_blocks):
                _items_rc = parse_items_from_block(_b["body"], _b.get("title", ""))
                _title_rc = re.sub(r"\s*\(\d+\s*pt\)", "", _b["title"]).strip()
                _title_short = (_title_rc[:45] + "…") if len(_title_rc) > 45 else _title_rc

                # Debug: mostra cosa viene rilevato
                print(f"DEBUG: Es {_i+1} - Title: {_title_rc}")
                print(f"DEBUG: Es {_i+1} - Items found: {len(_items_rc)}")
                for j, (label, text, pts) in enumerate(_items_rc):
                    print(f"  Item {j+1}: {label} - {pts}pt - {text[:30]}...")

                if not _items_rc:
                    _all_new_item_pts[_i] = []
                    continue

                _ex_new_pts_rc = []

                # ── Exercise header ────────────────────────────────────────
                st.markdown(
                    f'<div class="rc-ex-header">'
                    f'<span class="rc-ex-num">Es. {_i+1}</span>'
                    f'<span class="rc-ex-title">{_title_short}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )

                # ── Items: 2 per row, selectbox compatto ───────────────────
                _n_items_rc = len(_items_rc)
                _ex_item_vals = {}  # abs_idx -> int
                _max_sel = min(punti_totali, 40)
                for _row_start in range(0, _n_items_rc, 2):
                    _row_slice = _items_rc[_row_start:_row_start + 2]
                    _row_cols = st.columns(len(_row_slice), gap="medium")
                    for _ci, (_rc_col, (_lbl, _short, _cur_pt)) in enumerate(
                        zip(_row_cols, _row_slice)
                    ):
                        _abs_j = _row_start + _ci
                        _item_key = f"item_pt_{_i}_{_abs_j}"
                        with _rc_col:
                            _q_disp = (
                                (_short[:26] + "…") if len(_short or "") > 26
                                else (_short or "")
                            )
                            st.markdown(
                                f'<div class="rc-item-chip">'
                                f'<span class="rc-item-badge">{_lbl}</span>'
                                + (f'<span class="rc-item-text-sm">{_q_disp}</span>'
                                   if _q_disp else '')
                                + '</div>',
                                unsafe_allow_html=True,
                            )
                            st.markdown(
                                '<div class="rc-sel-wrap">', unsafe_allow_html=True
                            )
                            _sel_val = st.selectbox(
                                f"pt {_lbl}",
                                options=list(range(0, _max_sel + 1)),
                                index=min(_cur_pt, _max_sel),
                                key=_item_key,
                                label_visibility="collapsed",
                            )
                            st.markdown('</div>', unsafe_allow_html=True)
                            _ex_item_vals[_abs_j] = int(_sel_val)
                for _j in range(_n_items_rc):
                    _ex_new_pts_rc.append(_ex_item_vals.get(_j, 0))

                _ex_subtotal = sum(_ex_new_pts_rc)
                _grand_total_rc += _ex_subtotal
                _all_new_item_pts[_i] = _ex_new_pts_rc

                # ── Subtotal per exercise ──────────────────────────────────
                st.markdown(
                    f'<div class="rc-ex-subtotal">'
                    f'Subtotale Es. {_i+1}: <strong>{_ex_subtotal} pt</strong>'
                    f'</div>',
                    unsafe_allow_html=True
                )

            # ── Barra totale ───────────────────────────────────────────────
            _rc_ok   = (_grand_total_rc == punti_totali)
            _rc_diff = _grand_total_rc - punti_totali
            _rc_diff_str = ("+" if _rc_diff > 0 else "") + str(_rc_diff)

            st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)
            if _rc_ok:
                st.markdown(
                    '<div class="recalibra-sum-ok">'
                    f'✅ Totale: <strong>{_grand_total_rc} pt</strong> = {punti_totali} pt'
                    '</div>',
                    unsafe_allow_html=True
                )
            else:
                _missing = abs(_rc_diff)
                _direction = "in eccesso" if _rc_diff > 0 else "mancanti"
                st.markdown(
                    '<div class="recalibra-sum-err">'
                    f'⚠️ Totale: <strong>{_grand_total_rc} pt</strong> — '
                    f'{_missing} pt {_direction} rispetto a {punti_totali} pt'
                    '</div>',
                    unsafe_allow_html=True
                )

            st.markdown("<div style='height:.3rem'></div>", unsafe_allow_html=True)
            if st.button(
                "✅ Applica Punteggi e Rigenera PDF" if _rc_ok else
                f"Totale {_grand_total_rc} pt — aggiusta per sbloccare",
                key="rc_applica",
                disabled=not _rc_ok,
                use_container_width=True,
                type="primary",
            ):
                # Applica item pts direttamente ai blocchi
                for _i, _b in enumerate(st.session_state.review_blocks):
                    if _all_new_item_pts.get(_i):
                        _new_body_rc = apply_item_pts_to_body(
                            _b["body"], _all_new_item_pts[_i]
                        )
                        st.session_state.review_blocks[_i]["body"] = _new_body_rc
                        # Aggiorna titolo col subtotale
                        _clean_rc = re.sub(r"\s*\(\d+\s*pt\)", "",
                                           _b["title"]).strip()
                        _ex_tot_rc = sum(_all_new_item_pts[_i])
                        st.session_state.review_blocks[_i]["title"] = (
                            f"{_clean_rc} ({_ex_tot_rc} pt)"
                        )

                _latex_rc = reconstruct_latex(
                    st.session_state.review_preamble,
                    st.session_state.review_blocks
                )
                _latex_rc = fix_items_environment(_latex_rc)
                _latex_rc = rimuovi_vspace_corpo(_latex_rc)
                _latex_rc = rimuovi_punti_subsection(_latex_rc)
                # NON chiamare riscala_punti_custom: i pt sono già esatti per item
                if con_griglia:
                    _latex_rc = inietta_griglia(_latex_rc, punti_totali)

                st.session_state.verifiche["A"]["latex"]           = _latex_rc
                st.session_state.verifiche["A"]["latex_originale"] = _latex_rc

                with st.spinner("Ricompilazione PDF con i nuovi punteggi…"):
                    _pdf_rc, _err_rc = compila_pdf(_latex_rc)
                if _pdf_rc:
                    st.session_state.verifiche["A"]["pdf"]     = _pdf_rc
                    st.session_state.verifiche["A"]["pdf_ts"]  = time.time()
                    st.session_state.verifiche["A"]["preview"] = True
                    _imgs_rc, _ = pdf_to_images_bytes(_pdf_rc)
                    st.session_state.preview_images = _imgs_rc or []
                    st.session_state.preview_page   = 0
                    _new_preamble, _new_blocks = extract_blocks(_latex_rc)
                    if _new_blocks:
                        st.session_state.review_preamble = _new_preamble
                        st.session_state.review_blocks   = _new_blocks
                    # Reset item_pt_ keys — si reinizializzeranno dai nuovi dati
                    for _kk in list(st.session_state.keys()):
                        if re.match(r"^item_pt_\d+_\d+$", _kk):
                            del st.session_state[_kk]
                    if "recalibra_pts" in st.session_state:
                        del st.session_state["recalibra_pts"]
                    st.toast("✅ Punteggi applicati — PDF aggiornato!", icon="⚖️")
                    st.rerun()
                else:
                    if "TikZ" in _err_rc:
                        st.error("❌ Errore nel grafico TikZ. L'AI ha generato un grafico complesso non valido.")
                        st.info("💡 Suggerimento: prova a rigenerare l'esercizio o usa 'Cambia esercizio' per ottenere una versione senza grafici complessi.")
                    else:
                        st.error("❌ Errore di compilazione LaTeX.")
                    with st.expander("Log errore"):
                        st.text(_err_rc)

    # ── Pulsante CONFERMA — oro, piena larghezza ──────────────────────────────
    st.markdown("<div style='height:.8rem'></div>", unsafe_allow_html=True)
    st.markdown('<div class="btn-confirm-gold">', unsafe_allow_html=True)
    confirm_pdf = st.button(
        "🎯 Conferma e genera PDF finale",
        type="primary",
        use_container_width=True,
        key="btn_confirm_final"
    )
    st.markdown('</div>', unsafe_allow_html=True)

    if confirm_pdf:
        with st.spinner("Generazione PDF finale in corso… potrebbe richiedere qualche secondo"):
            latex_final = reconstruct_latex(
                st.session_state.review_preamble,
                st.session_state.review_blocks
            )
            latex_final = fix_items_environment(latex_final)
            latex_final = rimuovi_vspace_corpo(latex_final)
            if mostra_punteggi:
                latex_final = rimuovi_punti_subsection(latex_final)
                latex_final = prepara_esercizi_aperti(latex_final, punti_totali)
                _pts_custom = st.session_state.get("recalibra_pts", [])
                if _pts_custom and len(_pts_custom) == n_blocks:
                    latex_final = riscala_punti_custom(latex_final, _pts_custom)
                else:
                    latex_final = riscala_punti(latex_final, punti_totali)
            if con_griglia:
                latex_final = inietta_griglia(latex_final, punti_totali)

            st.session_state.verifiche["A"]["latex"]           = latex_final
            st.session_state.verifiche["A"]["latex_originale"] = latex_final

            pdf_bytes, err = compila_pdf(latex_final)
            if pdf_bytes:
                st.session_state.verifiche["A"]["pdf"]     = pdf_bytes
                st.session_state.verifiche["A"]["pdf_ts"]  = time.time()
                st.session_state.verifiche["A"]["preview"] = True
                imgs_f, _ = pdf_to_images_bytes(pdf_bytes)
                st.session_state.preview_images = imgs_f or []
                st.session_state.preview_page   = 0
                st.session_state.stage = STAGE_FINAL
                st.rerun()
            else:
                if err and "TikZ" in err:
                    st.error("❌ Errore nel grafico TikZ. L'AI ha generato un grafico complesso non valido.")
                    st.info("💡 Suggerimento: prova a rigenerare la verifica o usa 'Cambia esercizio' per rimuovere grafici problematici.")
                else:
                    st.error("❌ Errore di compilazione PDF.")
                with st.expander("Log errore"): st.text(err)

    # ── Pulsante RICONFIGURA — piccolo, discreto, sotto ───────────────────────
    st.markdown("<div style='height:.4rem'></div>", unsafe_allow_html=True)
    st.markdown('<div class="btn-riconfigura-small">', unsafe_allow_html=True)
    if st.button("← Riconfigura", use_container_width=False, key="btn_riconfigura"):
        st.session_state.stage = STAGE_INPUT; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  STAGE_FINAL
# ═══════════════════════════════════════════════════════════════════════════════

def _render_stage_final():
    gp   = st.session_state.gen_params
    vA   = st.session_state.verifiche["A"]
    vB   = st.session_state.verifiche["B"]
    vR   = st.session_state.verifiche["R"]
    vRB  = st.session_state.verifiche["RB"]
    vS   = st.session_state.verifiche["S"]

    arg_str      = gp.get("argomento","Verifica")
    mat_str      = gp.get("materia","")
    scu_str      = gp.get("difficolta","")
    con_griglia  = gp.get("con_griglia", False)
    mod_id       = gp.get("modello_id", modello_id)

    # ── Helper skeleton animato ───────────────────────────────────────────────
    def _skeleton_html(icon, title, sub):
        return (
            f'<div class="ocr-skeleton-wrap">'
            f'  <div class="ocr-skeleton-header">'
            f'    <div class="ocr-skeleton-icon">{icon}</div>'
            f'    <div>'
            f'      <div class="ocr-skeleton-title">{title}</div>'
            f'      <div class="ocr-skeleton-sub">{sub}</div>'
            f'    </div>'
            f'  </div>'
            f'  <div class="ocr-skeleton-doc">'
            f'    <div class="ocr-skeleton-scan"></div>'
            f'    <div class="ocr-skeleton-line" style="width:88%;animation-delay:.0s"></div>'
            f'    <div class="ocr-skeleton-line" style="width:70%;animation-delay:.2s"></div>'
            f'    <div class="ocr-skeleton-line" style="width:82%;animation-delay:.4s"></div>'
            f'  </div>'
            f'</div>'
        )

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown(
        f'<div style="'
        f'background:linear-gradient(160deg,{T["success"]}22 0%,{T["card"]} 55%,{T["accent"]}12 100%);'
        f'border:1.5px solid {T["success"]}55;border-radius:20px;'
        f'padding:2rem 1.8rem 1.3rem;margin-bottom:1rem;text-align:center;'
        f'box-shadow:0 4px 32px {T["success"]}20,0 1px 8px {T["success"]}12;">'
        f'<div style="font-size:3rem;line-height:1;margin-bottom:.7rem;'
        f'filter:drop-shadow(0 2px 10px {T["success"]}66);">🎉</div>'
        f'<div style="font-family:DM Sans,sans-serif;font-size:1.6rem;font-weight:900;'
        f'color:{T["text"]};letter-spacing:-.025em;margin-bottom:.4rem;line-height:1.15;">'
        f'La verifica è pronta!</div>'
        f'<div style="font-size:.9rem;color:{T["text2"]};font-family:DM Sans,sans-serif;'
        f'letter-spacing:.01em;">'
        + mat_str + ' &nbsp;·&nbsp; ' + scu_str + ' &nbsp;·&nbsp; ' + arg_str +
        f'</div>'
        f'<div style="font-size:.74rem;color:{T["muted"]};margin-top:1rem;padding-top:.7rem;'
        f'border-top:1px solid {T["border"]}66;font-family:DM Sans,sans-serif;">'
        f'⚠️ Controlla sempre il contenuto prima di distribuire agli studenti.'
        f'</div></div>',
        unsafe_allow_html=True
    )

    # (timer badges rimossi — non necessari per il docente)

    # ═══════════════════════════════════════════════════════════════════════════
    #  DOWNLOAD PRINCIPALE — pulsante CTA oro, piena larghezza
    # ═══════════════════════════════════════════════════════════════════════════
    _fname_a = arg_str + "_FilaA"
    if vA.get("pdf"):
        st.markdown(
            '<div class="dl-cta-wrap">',
            unsafe_allow_html=True,
        )
        st.download_button(
            label=f"✅  PDF PRONTO — CLICCA PER SCARICARE  ·  {_stima(vA['pdf'])}",
            data=vA["pdf"],
            file_name=_fname_a + ".pdf",
            mime="application/pdf",
            use_container_width=True,
            key="dl_pdf_hero_A",
            help="Scarica il PDF della verifica Fila A, già formattato e pronto per la stampa.",
        )
        st.markdown('</div>', unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════════════════
    #  VARIANTI — 4 card in colonna
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown(
        f'<div class="variant-section-label">GENERA ULTERIORI VERSIONI DELLA VERIFICA</div>',
        unsafe_allow_html=True
    )
    _vc1, _vc2, _vc3, _vc4, _vc5 = st.columns(5, gap="medium")

    # ── FILA B ────────────────────────────────────────────────────────────────
    with _vc1:
        _b_pdf = vB.get("pdf")
        _b_lat = vB.get("latex")

        st.markdown(
            f'<div class="variant-card variant-card-blue">'
            f'  <div class="variant-card-header">'
            f'    <span class="variant-card-icon">📋</span>'
            f'    <span class="variant-card-title">Fila B</span>'
            f'  </div>'
            f'  <div class="variant-card-desc">Stessa struttura, stessi punteggi — solo i dati cambiano. Pronta in secondi.</div>'
            f'</div>',
            unsafe_allow_html=True
        )
        if _b_pdf:
            st.download_button(
                f"⬇ Scarica Fila B (PDF) · {_stima(_b_pdf)}",
                data=_b_pdf, file_name=arg_str+"_FilaB.pdf",
                mime="application/pdf", use_container_width=True, key="dl_pdf_B_v2",
            )
        elif _b_lat:
            if st.button("📄 Crea PDF Fila B", key="compile_B_v2",
                         use_container_width=True, type="primary"):
                with st.spinner("Compilazione PDF Fila B in corso…"):
                    _pdf_bc, _ = compila_pdf(_b_lat)
                if _pdf_bc:
                    st.session_state.verifiche["B"]["pdf"] = _pdf_bc; st.rerun()
        else:
            if st.button("⚡ Genera Fila B", key="one_click_B_v2",
                         use_container_width=True, type="primary"):
                st.session_state["_gen_fila_b"] = True; st.rerun()

        if st.session_state.get("_gen_fila_b"):
            st.session_state["_gen_fila_b"] = False
            _ph_b = st.empty()
            _ph_b.markdown(_skeleton_html("⚡", "Generazione Fila B…",
                           "Cambio numeri · Verifica coerenza · Controllo qualità"), unsafe_allow_html=True)
            try:
                _mod_b = genai.GenerativeModel(mod_id)
                _latex_b_new = _mod_b.generate_content(
                    [prompt_variante_rapida(vA.get("latex",""), mat_str)],
                    generation_config=genai.GenerationConfig(temperature=0.7),
                ).text.strip()
                if _latex_b_new.startswith("```"):
                    _latex_b_new = re.sub(r"^```[a-z]*\n?","",_latex_b_new)
                    _latex_b_new = re.sub(r"\n?```$","",_latex_b_new)
                _pdf_b_new, _ = compila_pdf(_latex_b_new)
                st.session_state.verifiche["B"]["latex"] = _latex_b_new
                if _pdf_b_new: st.session_state.verifiche["B"]["pdf"] = _pdf_b_new
                _ph_b.empty(); st.toast("✅ Fila B pronta!", icon="⚡"); st.rerun()
            except Exception as _e:
                _ph_b.empty(); st.error(f"Errore: {_e}")

    # ── BES/DSA ───────────────────────────────────────────────────────────────
    with _vc2:
        _r_pdf = vR.get("pdf")
        _r_lat = vR.get("latex")

        st.markdown(
            f'<div class="variant-card variant-card-violet">'
            f'  <div class="variant-card-header">'
            f'    <span class="variant-card-icon">🌟</span>'
            f'    <span class="variant-card-title">Versione BES/DSA</span>'
            f'  </div>'
            f'  <div class="variant-card-desc">Per studenti con Bisogni Educativi Speciali o DSA: linguaggio semplificato, struttura alleggerita, stessi obiettivi.</div>'
            f'</div>',
            unsafe_allow_html=True
        )
        if _r_pdf:
            st.download_button(
                f"⬇ Scarica BES/DSA (PDF) · {_stima(_r_pdf)}",
                data=_r_pdf, file_name=arg_str+"_BES_FilaA.pdf",
                mime="application/pdf", use_container_width=True, key="dl_pdf_R_v2",
            )
        elif _r_lat:
            if st.button("📄 Crea PDF BES/DSA", key="compile_R_v2",
                         use_container_width=True, type="primary"):
                with st.spinner("Compilazione PDF BES/DSA in corso…"):
                    _pdf_rc, _ = compila_pdf(_r_lat)
                if _pdf_rc:
                    st.session_state.verifiche["R"]["pdf"] = _pdf_rc; st.rerun()
        else:
            if st.button("🌟 Genera BES/DSA", key="one_click_R_v2",
                         use_container_width=True, type="primary"):
                st.session_state["_gen_bes"] = True; st.rerun()

        if st.session_state.get("_gen_bes"):
            st.session_state["_gen_bes"] = False
            _ph_r = st.empty()
            _ph_r.markdown(_skeleton_html("🌟","Versione BES/DSA…","Semplificazione · Adattamento"),
                           unsafe_allow_html=True)
            try:
                res_r = _genera_variante("R", mod_id, gp, vA)
                st.session_state.verifiche["R"] = {**vR, **res_r}
                _ph_r.empty(); st.toast("✅ BES/DSA pronta!", icon="🌟"); st.rerun()
            except Exception as _e:
                _ph_r.empty(); st.error(f"Errore: {_e}")

    # ── SOLUZIONI ─────────────────────────────────────────────────────────────
    with _vc3:
        _s_pdf = vS.get("pdf")
        _s_lat = vS.get("latex")

        st.markdown(
            f'<div class="variant-card variant-card-green">'
            f'  <div class="variant-card-header">'
            f'    <span class="variant-card-icon">📝</span>'
            f'    <span class="variant-card-title">Soluzioni</span>'
            f'  </div>'
            f'  <div class="variant-card-desc">Documento riservato al docente con risposte complete e svolgimenti.</div>'
            f'</div>',
            unsafe_allow_html=True
        )
        if _s_pdf:
            st.download_button(
                f"⬇ Scarica Soluzioni (PDF) · {_stima(_s_pdf)}",
                data=_s_pdf, file_name=arg_str+"_Soluzioni.pdf",
                mime="application/pdf", use_container_width=True, key="dl_pdf_S_v2",
            )
        elif _s_lat:
            if st.button("📄 Crea PDF Soluzioni", key="compile_S_v2",
                         use_container_width=True, type="primary"):
                with st.spinner("Compilazione PDF Soluzioni in corso…"):
                    _pdf_sc, _ = compila_pdf(_s_lat)
                if _pdf_sc:
                    st.session_state.verifiche["S"]["pdf"] = _pdf_sc; st.rerun()
        else:
            if st.button("✅ Genera Soluzioni", key="one_click_S_v2",
                         use_container_width=True, type="primary"):
                st.session_state["_gen_sol"] = True; st.rerun()

        if st.session_state.get("_gen_sol"):
            st.session_state["_gen_sol"] = False
            _ph_s = st.empty()
            _ph_s.markdown(_skeleton_html("✅","Generazione soluzioni…","Svolgimenti · Risposte"),
                           unsafe_allow_html=True)
            try:
                res_s = _genera_variante("S", mod_id, gp, vA)
                st.session_state.verifiche["S"] = {**vS, **res_s}
                _ph_s.empty(); st.toast("✅ Soluzioni pronte!", icon="✅"); st.rerun()
            except Exception as _e:
                _ph_s.empty(); st.error(f"Errore: {_e}")

    # ── GENERA DOCX — 5a card ──────────────────────────────────────────────
    with _vc5:
        _docx_a   = vA.get("docx")
        _docx_key = "_docx_gen_A_card"
        st.markdown(
            f'<div class="variant-card variant-card-teal">'
            f'  <div class="variant-card-header">'
            f'    <span class="variant-card-icon">📝</span>'
            f'    <span class="variant-card-title">Formato Word</span>'
            f'  </div>'
            f'  <div class="variant-card-desc">Documento .docx modificabile, compatibile con Microsoft Word e Google Docs.</div>'
            f'</div>',
            unsafe_allow_html=True
        )
        if _docx_a:
            st.download_button(
                f"⬇ Scarica Word (.docx) · {_stima(_docx_a)}",
                data=_docx_a,
                file_name=arg_str + "_FilaA.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
                key="dl_docx_A_card",
            )
        elif vA.get("latex"):
            if st.button("📝 Genera Word", key="gen_docx_A_card",
                         use_container_width=True, type="primary"):
                st.session_state[_docx_key] = True
            if st.session_state.get(_docx_key, False):
                with st.spinner("Conversione in formato Word in corso… (30–60 sec)"):
                    try:
                        _db, _emsg = latex_to_docx_via_ai(vA["latex"], con_griglia=con_griglia)
                    except Exception as _e:
                        _db, _emsg = None, str(_e)
                st.session_state[_docx_key] = False
                if _db:
                    st.session_state.verifiche["A"]["docx"] = _db; st.rerun()
                else:
                    st.error(f"Errore Word: {_emsg or 'nessun dettaglio'}")
        else:
            st.caption("PDF non ancora disponibile")

    # ── GRIGLIA DI VALUTAZIONE — 4a card one-click ──────────────────────────
    with _vc4:
        _rub_ready = bool(st.session_state.get('rubrica_testo'))
        st.markdown(
            f'<div class="variant-card variant-card-orange">'
            f'  <div class="variant-card-header">'
            f'    <span class="variant-card-icon">📊</span>'
            f'    <span class="variant-card-title">Griglia di Valutazione</span>'
            f'  </div>'
            f'  <div class="variant-card-desc">Griglia voti per competenze con indicatori. Allineata alle Linee Guida MIM.</div>'
            f'</div>',
            unsafe_allow_html=True
        )
        if _rub_ready:
            # Genera DOCX al volo se non ancora cached
            if not st.session_state.get('_rubrica_docx'):
                _docx_bytes = _rubrica_to_docx(
                    st.session_state.rubrica_testo,
                    materia=mat_str,
                    livello=scu_str,
                    argomento=arg_str,
                )
                if _docx_bytes:
                    st.session_state['_rubrica_docx'] = _docx_bytes
            _rub_docx = st.session_state.get('_rubrica_docx')
            if _rub_docx:
                st.download_button(
                    '⬇ Scarica Griglia (.docx)',
                    data=_rub_docx,
                    file_name=arg_str + '_GrigliaValutazione.docx',
                    mime='application/vnd.openxmlformats-officedocument'
                         '.wordprocessingml.document',
                    key='dl_rubrica_docx_v2', use_container_width=True,
                )
            else:
                st.download_button(
                    '⬇ Scarica griglia (.txt)',
                    data=st.session_state.rubrica_testo.encode('utf-8'),
                    file_name=arg_str + '_Griglia.txt',
                    mime='text/plain', key='dl_rubrica_v2', use_container_width=True,
                )
        else:
            if st.button('📊 Genera Griglia', key='btn_gen_griglia_v2',
                         use_container_width=True, type='primary'):
                st.session_state._rubrica_gen = True
                st.rerun()
        if st.session_state.get('_rubrica_gen') and not _rub_ready:
            st.session_state['_rubrica_gen'] = False
            _rph = st.empty()
            _rph.info('📊 Generazione griglia in corso…')
            try:
                _mr = genai.GenerativeModel(mod_id)
                _pr = prompt_rubrica_valutazione(
                    corpo_latex=vA.get('latex', ''), materia=mat_str,
                    livello=scu_str, punti_totali=gp.get('punti_totali', 100),
                )
                _rr = _mr.generate_content(
                    [_pr], generation_config=genai.GenerationConfig(temperature=0.5))
                st.session_state.rubrica_testo = _rr.text.strip()
                _rph.empty(); st.toast('Griglia pronta!', icon='📊'); st.rerun()
            except Exception as _er:
                _rph.empty(); st.error(f'Errore: {_er}')

    # ═══════════════════════════════════════════════════════════════════════════
    #  IDEA #5 — CONDIVIDI CON IL DIPARTIMENTO
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown("<div style='height:.7rem'></div>", unsafe_allow_html=True)

    _share_code = st.session_state._share_code
    _latex_a_share = vA.get("latex", "")

    if _latex_a_share:
        st.markdown(
            f'<div class="share-dept-card">'
            f'  <div class="share-dept-header">'
            f'    <span class="share-dept-icon">📤</span>'
            f'    <div class="share-dept-title-wrap">'
            f'      <div class="share-dept-title">Condividi con il Dipartimento</div>'
            f'      <div class="share-dept-subtitle">'
            f'I colleghi potranno visualizzare la tua verifica e generare la propria variante con un click.'
            f'      </div>'
            f'    </div>'
            f'  </div>'
            f'</div>',
            unsafe_allow_html=True
        )

        if _share_code:
            # Link già generato — mostra con copy
            _share_full_url = f"{SHARE_URL}?share={_share_code}"
            st.markdown(
                f'<div class="share-link-box">'
                f'  <div class="share-link-status">'
                f'    <span class="share-link-dot"></span>'
                f'    Link attivo · valido per 30 giorni dalla creazione'
                f'  </div>'
                f'  <div class="share-link-url">{_share_full_url}</div>'
                f'</div>',
                unsafe_allow_html=True
            )
            _sh_c1, _sh_c2 = st.columns([3, 1])
            with _sh_c1:
                # Copy button via components.html
                components.html(
                    "<style>body{margin:0;padding:0;background:transparent}"
                    f".cb{{background:{T['accent']};color:#0D1117;border:none;border-radius:8px;"
                    "padding:8px 16px;cursor:pointer;font-size:.82rem;font-weight:700;"
                    "font-family:DM Sans,sans-serif;width:100%;transition:all .15s}"
                    f".cb:hover{{filter:brightness(1.12);transform:translateY(-1px)}}"
                    f".cb.ok{{background:{T['success']};color:#fff}}</style>"
                    f"<button class='cb' id='cpb' onclick='doCopy()'>📋 Copia link</button>"
                    "<script>function doCopy(){"
                    f"var t=document.createElement('textarea');t.value='{_share_full_url}';"
                    "t.style.cssText='position:fixed;opacity:0';document.body.appendChild(t);"
                    "t.select();var ok=false;try{ok=document.execCommand('copy')}catch(e){}"
                    "document.body.removeChild(t);var b=document.getElementById('cpb');"
                    "if(ok){b.className='cb ok';b.innerText='✅ Copiato!';"
                    "setTimeout(function(){b.className='cb';b.innerText='📋 Copia link'},2500)}"
                    "}</script>",
                    height=42,
                )
            with _sh_c2:
                if st.button("🔄", key="share_new_link", help="Genera un nuovo link. Attenzione: il link precedente smetterà di funzionare."):
                    st.session_state._share_code = None
                    st.rerun()

            st.markdown(
                f'<div style="font-size:.7rem;color:{T["muted"]};margin-top:.3rem;'
                f'font-family:DM Sans,sans-serif;line-height:1.4;">'
                f'👥 Quando un collega apre il link, vede un\'anteprima e può generare '
                f'la propria variante con dati nuovi — senza accedere alla tua verifica originale.'
                f'</div>',
                unsafe_allow_html=True
            )
        else:
            # Genera link
            if st.button("📤 Genera link di condivisione", key="btn_share_gen",
                         use_container_width=True):
                st.session_state._share_generating = True
                st.rerun()

            if st.session_state.get("_share_generating"):
                st.session_state._share_generating = False
                with st.spinner("📤 Creazione link di condivisione…"):
                    _new_code = _create_share_link(
                        latex_a=_latex_a_share,
                        materia=mat_str,
                        argomento=arg_str,
                        scuola=scu_str,
                        num_esercizi=gp.get("num_esercizi", 4),
                    )
                if _new_code:
                    st.session_state._share_code = _new_code
                    st.toast("📤 Link di condivisione creato!", icon="📤")
                    st.rerun()
                else:
                    st.error("Errore nella creazione del link. Riprova.")

    # ── Sezioni secondarie collassabili ───────────────────────────────────────
    st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)

    # Controlla se il PDF è cambiato e aggiorna le preview se necessario
    current_pdf_ts = vA.get("pdf_ts")
    last_preview_ts = st.session_state.get("last_preview_ts", 0)
    
    # Se il timestamp del PDF è più recente dell'ultima preview, rigenera le immagini
    if current_pdf_ts and current_pdf_ts > last_preview_ts:
        vA_pdf = vA.get("pdf")
        if vA_pdf:
            try:
                new_imgs, _ = pdf_to_images_bytes(vA_pdf)
                st.session_state.preview_images = new_imgs or []
                st.session_state.last_preview_ts = current_pdf_ts
                logger.info(f"Preview images aggiornate (final page) - timestamp PDF: {current_pdf_ts}")
            except Exception as e:
                logger.error(f"Errore aggiornamento preview (final page): {e}")
    
    imgs = st.session_state.preview_images
    if imgs or vA.get("pdf"):
        with st.expander("📄 Anteprima PDF", expanded=False):
            if imgs:
                cols_prev = st.columns(min(3, len(imgs)))
                for pi, img_b in enumerate(imgs[:3]):
                    with cols_prev[pi]:
                        st.image(img_b, use_container_width=True, caption=f"Pagina {pi+1}")
                if len(imgs) > 3:
                    st.caption(f"…e altre {len(imgs)-3} pagine nel file PDF scaricato.")
            elif vA.get("pdf"):
                b64 = base64.b64encode(vA["pdf"]).decode()
                st.markdown(
                    '<iframe src="data:application/pdf;base64,' + b64 + '#toolbar=0&navpanes=0" '
                    'style="width:100%;height:520px;border:none;border-radius:8px;"></iframe>',
                    unsafe_allow_html=True
                )

    # Altri formati (DOCX, .tex) — se disponibili
    _ha_extra = vA.get("latex") or vB.get("latex") or vR.get("latex") or vS.get("latex")
    if _ha_extra:
        with st.expander("📝 Altri formati (Word, LaTeX)", expanded=False):
            def _show_extra_formats(fid, v, fname_suffix):
                if not v.get("latex"):
                    return
                fname = arg_str + "_" + fname_suffix
                _docx_key = "_docx_gen_" + fid
                st.markdown(f'<div class="s3-card-label">{fname_suffix.replace("_"," ")}</div>',
                            unsafe_allow_html=True)
                if v.get("docx"):
                    st.download_button(
                        f"📝 Word · {_stima(v['docx'])}",
                        data=v["docx"], file_name=fname+".docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True, key="dl_docx_"+fid+"_extra"
                    )
                else:
                    if st.button(f"📝 Genera Word — {fname_suffix.replace('_',' ')}",
                                 key="gen_docx_"+fid+"_extra", use_container_width=True):
                        st.session_state[_docx_key] = True
                    if st.session_state.get(_docx_key, False):
                        with st.spinner("Conversione in formato Word in corso…"):
                            try:
                                db, error_msg = latex_to_docx_via_ai(v["latex"], con_griglia=con_griglia)
                            except Exception as e:
                                db = None
                                error_msg = str(e)
                        st.session_state[_docx_key] = False
                        if db:
                            st.session_state.verifiche[fid]["docx"] = db; st.rerun()
                        else:
                            st.error(f"Conversione Word non riuscita: {error_msg or 'nessun dettaglio disponibile'}")
                st.download_button(
                    f"⬇ LaTeX sorgente (.tex)",
                    data=v["latex"].encode("utf-8"), file_name=fname+".tex",
                    mime="text/plain", use_container_width=True, key="dl_tex_"+fid+"_extra",
                )
            _ef_c1, _ef_c2 = st.columns(2)
            with _ef_c1:
                _show_extra_formats("A", vA, "FilaA")
                if vR.get("latex"): _show_extra_formats("R", vR, "BES_FilaA")
            with _ef_c2:
                if vB.get("latex"): _show_extra_formats("B", vB, "FilaB")
                if vRB.get("latex"): _show_extra_formats("RB", vRB, "BES_FilaB")
                if vS.get("latex"): _show_extra_formats("S", vS, "Soluzioni")


        # Link feedback
    st.markdown(
        '<div style="margin-top:14px;text-align:center;font-size:.78rem;'
        'font-family:DM Sans,sans-serif;color:' + T["muted"] + ';">'
        'Qualcosa non va o hai un suggerimento? '
        '<a href="' + FEEDBACK_FORM_URL + '" target="_blank" '
        'style="color:' + T["accent"] + ';font-weight:600;">Lasciaci un feedback 💬</a>'
        '</div>',
        unsafe_allow_html=True
    )

    # ── Navigazione finale — in fondo alla pagina ─────────────────────────────
    st.markdown("<div style='height:1.4rem'></div>", unsafe_allow_html=True)
    _nav_c1, _nav_c2 = st.columns([1, 2])
    with _nav_c1:
        if _render_back_button("←", key="btn_back_final"):
            st.session_state.stage = STAGE_REVIEW
            st.rerun()
    with _nav_c2:
        if st.button("🆕 Genera nuova verifica", type="primary",
                     use_container_width=True, key="btn_new_s3_bottom"):
            st.session_state.stage            = STAGE_INPUT
            st.session_state["_prev_stage"]   = None
            st.session_state.input_percorso   = None
            for _k in list(st.session_state.keys()):
                if _k.startswith("_undo_block_") or _k.startswith("item_pt_"):
                    del st.session_state[_k]
            st.session_state.verifiche         = {
                "A": _vf(), "B": _vf(), "R": _vf(), "RB": _vf(),
                "S": {"latex": None, "testo": None, "pdf": None},
            }
            st.session_state.review_preamble   = ""
            st.session_state.review_blocks     = []
            st.session_state.review_sel_idx    = 0
            st.session_state.gen_params        = {}
            st.session_state.preview_images    = []
            st.session_state.preview_page      = 0
            st.session_state.last_preview_ts   = 0
            st.session_state.esercizi_custom       = []
            st.session_state._saved_to_storico     = False
            st.session_state["_es_custom_da_file"] = {}
            st.session_state.rubrica_testo         = None
            st.session_state["_rubrica_pdf"]       = None
            st.session_state["_rubrica_docx"]      = None
            st.session_state._rubrica_gen          = False
            st.session_state._template_sel         = None
            st.session_state._variant_rapida_gen   = False
            st.session_state["_gen_fila_b"]        = False
            st.session_state["_gen_bes"]           = False
            st.session_state["_gen_sol"]           = False
            st.session_state.analisi_docs_list  = []
            st.session_state.info_consolidate   = {}
            st.session_state["wizard_step"]     = "upload"
            st.session_state["_analisi_rifiuto"] = None
            st.session_state["_facsimile_mode"] = False
            st.session_state.qa_mode            = False
            st.session_state._share_code        = None
            st.session_state._share_generating   = False
            st.rerun()
    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  ROUTING
# ═══════════════════════════════════════════════════════════════════════════════

# ── IDEA #5: Intercetta link condiviso ?share=CODE ────────────────────────────
_share_param = st.query_params.get("share", None)
_share_view_active = False

if _share_param and isinstance(_share_param, str) and len(_share_param) >= 6:
    _shared_record = _load_shared_verifica(_share_param)
    if _shared_record:
        _share_view_active = True
        _sh_mat  = _shared_record.get("materia", "")
        _sh_arg  = _shared_record.get("argomento", "")
        _sh_scu  = _shared_record.get("scuola", "")
        _sh_lat  = _shared_record.get("latex_a", "")
        _sh_date = _shared_record.get("created_at", "")[:10]
        _sh_n_es = _shared_record.get("num_esercizi", "?")

        st.markdown(
            f'<div class="shared-view-banner">'
            f'  <div class="shared-view-header">'
            f'    <span style="font-size:1.5rem;">📤</span>'
            f'    <div>'
            f'      <div class="shared-view-title">Verifica condivisa da un collega</div>'
            f'      <div class="shared-view-meta">'
            f'{_sh_mat} · {_sh_scu} · {_sh_arg}'
            f'      </div>'
            f'    </div>'
            f'  </div>'
            f'  <div class="shared-view-badges">'
            f'    <span class="shared-view-badge">📝 {_sh_n_es} esercizi</span>'
            f'    <span class="shared-view-badge">📅 {_sh_date}</span>'
            f'    <span class="shared-view-badge">🔒 Solo lettura</span>'
            f'  </div>'
            f'</div>',
            unsafe_allow_html=True
        )

        # Compila PDF per anteprima
        if _sh_lat:
            _sh_pdf, _sh_err = compila_pdf(_sh_lat)
            if _sh_pdf:
                _sh_imgs, _ = pdf_to_images_bytes(_sh_pdf)
                if _sh_imgs:
                    st.markdown(
                        f'<div style="font-size:.72rem;font-weight:700;color:{T["muted"]};'
                        f'text-transform:uppercase;letter-spacing:.05em;margin-bottom:.5rem;">'
                        f'📄 Anteprima verifica</div>',
                        unsafe_allow_html=True
                    )
                    _sh_cols = st.columns(min(3, len(_sh_imgs)))
                    for _shi, _sh_img in enumerate(_sh_imgs[:3]):
                        with _sh_cols[_shi]:
                            st.image(_sh_img, use_container_width=True, caption=f"Pag. {_shi+1}")

                st.download_button(
                    f"📄  Scarica PDF originale",
                    data=_sh_pdf, file_name=f"{_sh_arg}_condivisa.pdf",
                    mime="application/pdf", use_container_width=True,
                    key="dl_shared_pdf",
                )

            st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)

            # CTA: genera la tua variante
            st.markdown(
                f'<div class="shared-cta-card">'
                f'  <div class="shared-cta-icon">🎲</div>'
                f'  <div class="shared-cta-title">Genera la tua variante</div>'
                f'  <div class="shared-cta-desc">'
                f'Crea una versione con dati nuovi e stessa struttura — '
                f'perfetta come Fila B per la tua classe.'
                f'  </div>'
                f'</div>',
                unsafe_allow_html=True
            )

            if st.session_state.utente:
                # Utente autenticato → può generare variante
                if st.button("🎲 Genera la mia variante", type="primary",
                             use_container_width=True, key="btn_shared_variant"):
                    _increment_clone_count(_share_param)
                    st.session_state.verifiche["A"]["latex"] = _sh_lat
                    st.session_state.verifiche["A"]["latex_originale"] = _sh_lat
                    if _sh_pdf:
                        st.session_state.verifiche["A"]["pdf"] = _sh_pdf
                        st.session_state.verifiche["A"]["preview"] = True
                        _sh_imgs_2, _ = pdf_to_images_bytes(_sh_pdf)
                        st.session_state.preview_images = _sh_imgs_2 or []
                    _sh_pre, _sh_blks = extract_blocks(_sh_lat)
                    if _sh_blks:
                        st.session_state.review_preamble = _sh_pre
                        st.session_state.review_blocks = _sh_blks
                    st.session_state.gen_params = {
                        "materia":    _sh_mat, "difficolta": _sh_scu,
                        "argomento":  _sh_arg, "num_esercizi": _sh_n_es,
                        "mostra_punteggi": True, "punti_totali": 100,
                        "con_griglia": True,
                    }
                    st.session_state.stage = STAGE_FINAL
                    # Genera Fila B automaticamente
                    st.session_state["_gen_fila_b"] = True
                    st.query_params.clear()
                    st.rerun()
            else:
                st.info(
                    "🔐 Per generare la tua variante, accedi con il tuo account VerificAI. "
                    "È gratis!"
                )
                if st.button("🔐 Accedi per generare", use_container_width=True, key="btn_shared_login"):
                    st.query_params.clear()
                    st.rerun()

            st.markdown(
                f'<div style="text-align:center;font-size:.72rem;color:{T["muted"]};'
                f'font-family:DM Sans,sans-serif;margin-top:1rem;">'
                f'Link condiviso con VerificAI · <a href="{SHARE_URL}" '
                f'style="color:{T["accent"]};">Crea la tua prima verifica gratis →</a>'
                f'</div>',
                unsafe_allow_html=True
            )
    else:
        st.warning("⚠️ Link di condivisione non valido o scaduto.")
        if st.button("← Torna alla home", key="btn_shared_back"):
            st.query_params.clear()
            st.rerun()

if not _share_view_active:
    # Mostra sticky header solo quando NON si è sulla landing iniziale E NON sulla pagina "Le tue verifiche"
    _show_bc = not (
        (st.session_state.stage == STAGE_INPUT
        and st.session_state.get("input_percorso") is None)
        or st.session_state.stage == STAGE_MIE_VERIFICHE
    )
    if _show_bc:
        _render_sticky_header(T)
        _render_step_progress(T)
    else:
        # Sulla landing o pagina "Le tue verifiche": rimuovi l'eventuale sticky header rimasto
        components.html("""
<script>
(function() {
  var doc = window.parent.document;
  var old = doc.getElementById('_vai_sticky_hdr');
  if (old) old.remove();
  // Ripristina padding-top del container
  var main = doc.querySelector('.main .block-container');
  if (main) main.style.paddingTop = '';
})();
</script>""", height=0)

# ── SCROLL TO TOP on stage change ─────────────────────────────────────────────
_current_stage = st.session_state.stage
_prev_stage = st.session_state.get("_prev_stage", None)
if _prev_stage != _current_stage:
    st.session_state["_prev_stage"] = _current_stage
    components.html(
        "<script>"
        "(function(){"
        "var tries=0,max=12;"
        "function scrollTop(){"
        "  var d=window.parent.document;"
        "  var targets=["
        "    d.querySelector('.main'),"
        "    d.querySelector('.main .block-container'),"
        "    d.querySelector('[data-testid=\"stAppViewContainer\"]'),"
        "    d.querySelector('[data-testid=\"stMainBlockContainer\"]'),"
        "    d.documentElement,"
        "    d.body"
        "  ];"
        "  targets.forEach(function(t){if(t){t.scrollTop=0;}});"
        "  window.parent.scrollTo({top:0,left:0,behavior:'instant'});"
        "  if(tries++<max)setTimeout(scrollTop,120);"
        "}"
        "scrollTop();"
        "var bc=window.parent.document.querySelector('.main .block-container');"
        "if(bc){bc.classList.remove('stage-enter');void bc.offsetWidth;"
        "bc.classList.add('stage-enter');"
        "setTimeout(function(){bc.classList.remove('stage-enter');},500);}"
        "})();"
        "</script>",
        height=0
    )

if not _share_view_active:
    _current = _current_stage
    if   _current == STAGE_INPUT:   _render_stage_input()
    elif _current == STAGE_PREVIEW: _render_stage_preview()
    elif _current == STAGE_REVIEW:  _render_stage_review()
    elif _current == STAGE_FINAL:   _render_stage_final()
    elif _current == STAGE_MIE_VERIFICHE: _render_le_tue_verifiche()


# ── FOOTER ────────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="app-footer">'
    '⚠️ Le verifiche generate dall\'AI sono suggerimenti didattici — '
    'rivedi sempre il contenuto prima di distribuirlo.<br>'
    '<span style="opacity:.5;">VerificAI · Versione Beta</span>'
    '</div>',
    unsafe_allow_html=True
)

components.html(
    "<style>body{margin:0;padding:0;background:transparent}"
    "#sb{background:none;border:none;cursor:pointer;color:" + T["accent"] + ";"
    "font-weight:600;font-size:.72rem;font-family:DM Sans,sans-serif;"
    "padding:0;display:block;margin:0 auto;text-align:center;width:100%}"
    "#sb:hover{text-decoration:underline}</style>"
    "<button id='sb' onclick='copyL()'>🔗 Condividi con i colleghi</button>"
    "<script>"
    "function copyL(){"
    "var u='" + SHARE_URL + "';"
    "var b=document.getElementById('sb');"
    "var t=document.createElement('textarea');"
    "t.value=u;t.style.cssText='position:fixed;top:0;left:0;opacity:0';"
    "document.body.appendChild(t);t.focus();t.select();"
    "var ok=false;try{ok=document.execCommand('copy')}catch(e){}"
    "document.body.removeChild(t);"
    "if(ok){b.innerText='✅ Link copiato!';setTimeout(function(){b.innerText='🔗 Condividi con i colleghi'},2000)}"
    "else{b.innerText=u}}"
    "</script>",
    height=30
)
