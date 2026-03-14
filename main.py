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
    migliora_spaziatura_sottopunti, limita_altezza_grafici, assicura_punti_visibili, aggiungi_spaziatura_grafici_tabelle,
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
        corpo = migliora_spaziatura_sottopunti(corpo)
        corpo = aggiungi_spaziatura_grafici_tabelle(corpo)
        corpo = limita_altezza_grafici(corpo)
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
        <div class="landing-hero-unified" style="padding: 1.5rem 1rem 1rem;">
                    <h2 class="landing-headline-xl" style="margin: 0 0 0.1rem 0 !important;">
            Crea verifiche professionali<br>
            <span class="landing-headline-accent-xl">in pochi secondi</span>
          </h2>
          <p class="landing-sub-xl" style="margin: 0 auto 1.5rem !important;">
            Scegli materia, livello e argomento.<br>
            L'AI costruisce la verifica, tu la revisioni e scarichi.
          </p>
        </div>
        ''',
        unsafe_allow_html=True,
    )

    # ── CTA principale — più prominente ─────────────────────────────────────────────
    st.markdown('<div style="margin: 2rem 0;"></div>', unsafe_allow_html=True)
    _c1, _c2, _c3 = st.columns([1.5, 2, 1.5])
    with _c2:
        if st.button(
            "🚀 **Crea Verifica Ora**",
            key="btn_genera_verifica_home",
            use_container_width=True,
            type="primary",
            help="Scegli materia e argomento, crea in 30 secondi",
        ):
            st.session_state.input_percorso = "B"
            st.rerun()

    # ── Feature pills — più leggibili per docenti ───────────────────────────────
    st.markdown('<div style="margin: 1.5rem 0;"></div>', unsafe_allow_html=True)
    st.markdown(
        '''
        <div class="tally-features" style="gap: 12px; flex-wrap: wrap; justify-content: center;">
          <span class="tally-feat-pill" style="background: #f0f9ff; color: #0369a1; padding: 8px 16px; font-weight: 600;">
            📄 PDF Stampabile
          </span>
          <span class="tally-feat-pill" style="background: #f0f9ff; color: #0369a1; padding: 8px 16px; font-weight: 600;">
            🎲 Fila A e B
          </span>
          <span class="tally-feat-pill" style="background: #f0f9ff; color: #0369a1; padding: 8px 16px; font-weight: 600;">
            ⭐ Versione BES
          </span>
          <span class="tally-feat-pill" style="background: #f0f9ff; color: #0369a1; padding: 8px 16px; font-weight: 600;">
            ✏️ DOCX Modificabile
          </span>
          <span class="tally-feat-pill" style="background: #f0f9ff; color: #0369a1; padding: 8px 16px; font-weight: 600;">
            📋 Soluzioni
          </span>
          <span class="tally-feat-pill" style="background: #f0f9ff; color: #0369a1; padding: 8px 16px; font-weight: 600;">
            📊 Griglia Valutazione
          </span>
        </div>
        ''',
        unsafe_allow_html=True,
    )

    # ── Feature cards ─────────────────────────────────────

    # ── Feature cards — 6 card, 2 righe ─────────────────────────────────────
    st.markdown("<div style='height:2rem'></div>", unsafe_allow_html=True)
    
    # Sezione Dashboard (prima degli esempi)
    st.markdown("---")
    st.markdown('<div style="margin: 0.5rem 0;"></div>', unsafe_allow_html=True)
    
    st.markdown(
        """
        <div style="text-align: center; margin-bottom: 2rem;">
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
    st.markdown('<div style="text-align: center; margin-top: 2rem;">', unsafe_allow_html=True)
    if st.button("📄 Gestisci Le Tue Verifiche →", type="primary", use_container_width=True):
        st.session_state.stage = STAGE_MIE_VERIFICHE
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div style="margin: 1.5rem 0;"></div>', unsafe_allow_html=True)

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

# Sostituzione completa della funzione _render_le_tue_verifiche con HTML semplificato


    """
    Pagina "Le tue verifiche" - Versione semplificata senza HTML complesso
    """
    # Pulsante per tornare indietro
    if st.button("← Torna Indietro", key="back_from_mie_verifiche"):
        st.session_state.stage = STAGE_INPUT
        st.session_state.input_percorso = None
        st.rerun()
    
    # Header
    st.markdown("""
    <div style="text-align: center; margin-bottom: 2rem;">
        <h1 style="font-size: 2rem; font-weight: 700; color: #1f2937;">
            📄 Le Tue Verifiche
        </h1>
        <p style="font-size: 1.1rem; color: #6b7280;">
            Gestisci, visualizza e scarica tutte le verifiche che hai creato
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Carica dati
    stats = _get_verifiche_stats()
    verifiche = _load_user_verifiche()
    
    # Stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Totali", stats['totali'])
    with col2:
        st.metric("Questo mese", stats['questo_mese'])
    with col3:
        st.metric("Materie", stats['materie'])
    with col4:
        st.metric("Qualità", f"⭐ {stats['qualita_media']}")
    
    st.markdown("---")
    
    # Filtri
    col_search, col_materia, col_ordine = st.columns([3, 2, 2])
    with col_search:
        search_query = st.text_input("🔍 Cerca...", placeholder="Cerca verifica...")
    
    # Filtra e mostra verifiche
    if verifiche:
        for i, verifica in enumerate(verifiche):
            # Card semplice per ogni verifica
            with st.container():
                st.markdown(f"""
                <div style="
                    border: 2px solid #e5e7eb;
                    border-radius: 12px;
                    padding: 1rem;
                    margin-bottom: 1rem;
                    background: white;
                ">
                    <h3 style="color: #1f2937; margin: 0 0 0.5rem 0;">
                        {verifica.get('argomento', 'Verifica senza titolo')}
                    </h3>
                    <p style="color: #6b7280; margin: 0.5rem 0;">
                        📚 {verifica.get('materia', 'Sconosciuta')} • 
                        🏫 {verifica.get('scuola', 'Non specificata')} • 
                        📝 {verifica.get('num_esercizi', '?')} esercizi
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                # Bottoni azione
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    if st.button(f"👁️ Anteprima", key=f"preview_{verifica.get('id')}_{i}"):
                        st.success("Anteprima generata!")
                        if verifica.get("latex_a"):
                            try:
                                pdf_bytes, error = compila_pdf(verifica["latex_a"])
                                if pdf_bytes:
                                    images, _ = pdf_to_images_bytes(pdf_bytes)
                                    for j, img in enumerate(images[:3]):
                                        st.image(img, caption=f"Pagina {j+1}", width=800)
                            except Exception as e:
                                st.error(f"Errore: {e}")
                
                with col2:
                    if st.button(f"📄 PDF", key=f"download_{verifica.get('id')}_{i}"):
                        st.info("Download PDF...")
                
                with col3:
                    if st.button(f"🎲 Facsimile", key=f"facsimile_{verifica.get('id')}_{i}"):
                        st.info("Creazione facsimile...")
                
                with col4:
                    if st.button(f"🗑️ Elimina", key=f"delete_{verifica.get('id')}_{i}"):
                        st.warning("Conferma eliminazione...")
                
                st.markdown("---")
    else:
        st.info("📝 Nessuna verifica trovata. Inizia a creare la tua prima verifica!")
        
        if st.button("🆕 Crea Nuova Verifica", type="primary"):
            st.session_state.stage = STAGE_INPUT
            st.session_state.input_percorso = None
            st.rerun()
