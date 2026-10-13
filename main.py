# ── main.py — VerificAI ──────────────────────────────────────────────────────
# Macchina a tre stati:
#   STAGE_INPUT  → configurazione snella + tasto Genera
#   STAGE_REVIEW → revisione esercizio (selectbox + KaTeX + PDF strip)
#   STAGE_FINAL  → download PDF primario + varianti on-demand + secondari small
# ─────────────────────────────────────────────────────────────────────────────

import streamlit as st
import streamlit.components.v1 as components
import base64
import copy
import logging
import re
import os
import time
from datetime import datetime, timezone

import google.generativeai as genai

from sidebar import render_sidebar
from generation import (
    genera_verifica, analizza_documento_caricato, compila_contesto_generazione,
    rigenera_singolo_blocco,
)
from prompts import (
    prompt_versione_b, prompt_versione_ridotta, prompt_soluzioni,
    prompt_rubrica_valutazione, prompt_variante_rapida, istruzione_livello_esercizio,
    REGOLA_SOTTOPUNTI_MODIFICA, REGOLA_GRAFICO_CURVE,
)
from docx_export import latex_to_docx_via_ai, _rubrica_to_docx
from latex_utils import (
    compila_pdf, compila_pdf_sicuro, inietta_griglia, riscala_punti, riscala_punti_custom,
    fix_items_environment, rimuovi_vspace_corpo, pulisci_corpo_latex,
    rimuovi_punti_subsection, pdf_to_images_bytes,
    extract_blocks, reconstruct_latex, extract_corpo, extract_preambolo,
    parse_pts_from_block_body, riscala_single_block,
    parse_items_from_block, apply_item_pts_to_body,
    prepara_esercizi_aperti, conta_punti_latex,
    migliora_spaziatura_sottopunti, limita_altezza_grafici, aggiungi_spaziatura_grafici_tabelle,
    normalizza_sottopunti_inline, bilancia_punti, esercizi_con_grafico_mancante,
)
from config import (
    APP_NAME, APP_ICON, SHARE_URL, FEEDBACK_FORM_URL,
    LIMITE_MENSILE, ADMIN_EMAILS, MODELLI_DISPONIBILI, THEMES,
    SCUOLE, CALIBRAZIONE_SCUOLA, MATERIE, esempio_richiesta, TIPI_ESERCIZIO,
    DURATE, DURATA_DEFAULT, parametri_durata, etichetta_durata,
    MODEL_FAST_ID, get_model_id_per_piano, THEME_LABELS,
)
from dotenv import load_dotenv
from supabase import create_client, Client
from auth import mostra_auth, ripristina_sessione
from styles import get_css, _is_light_color
from ui_helpers import (
    _make_katex_html, _render_sticky_header,
    _render_step_progress,
    STAGE_INPUT, STAGE_PREVIEW, STAGE_REVIEW, STAGE_FINAL,
    _reset_label, _render_limite_raggiunto, _mostra_errore, _mostra_errore_pdf,
    separa_argomento_e_note,
)

logger = logging.getLogger("verificai.main")

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
STAGE_MIE_VERIFICHE = "MIE_VERIFICHE"  # pagina "Le tue verifiche"

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title=APP_NAME,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── SUPABASE ──────────────────────────────────────────────────────────────────
# Temporaneamente disabilitato per test - creare il file .streamlit/secrets.toml per abilitare
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    SUPABASE_SERVICE_KEY = st.secrets["SUPABASE_SERVICE_KEY"]
    supabase_admin: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    SUPABASE_ENABLED = True
except Exception as e:
    # Fallback per test senza database
    supabase = None
    supabase_admin = None
    SUPABASE_ENABLED = False
    logger.error(f"Database Supabase non configurato: {e}")
    st.warning("⚠️ Il database non è raggiungibile: lo storico e il salvataggio non funzioneranno.")

# ── TEMA — inizializzazione ───────────────────────────────────────────────────
# Temi disponibili: carta (default) e notte. Una chiave non più presente (sessioni vecchie) → carta.
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
    # Temporaneamente usa una API key fittizia per testare l'interfaccia
    API_KEY = "test_api_key_temporanea"
    st.warning("⚠️ API Google temporaneamente non configurata - la generazione non funzionerà ma puoi testare l'interfaccia")
genai.configure(api_key=API_KEY)

# ── VERIFICA DISPONIBILITÀ LATEX ─────────────────────────────────────────────────
# Sarà fatto dopo l'autenticazione per essere visibile all'utente

# ── AUTENTICAZIONE ────────────────────────────────────────────────────────────
if "utente" not in st.session_state:
    st.session_state.utente = None

# Ripristina sessione esistente
if st.session_state.utente is None:
    ripristina_sessione(supabase)

# Mostra auth se non loggato
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




# ── Post-processing LaTeX unico ────────────────────────────────────────────────

def _postprocessa_latex(latex: str, mostra_punteggi: bool, punti_totali: int,
                        riscala_totale: bool = False, punti_custom: list | None = None,
                        con_griglia: bool = False) -> str:
    """
    Post-processing deterministico unico (stringa → stringa) per ogni modifica:
    sistema gli ambienti, le spaziature e i grafici, toglie i punti dai titoli e, se
    riscala_totale, riporta la somma dei punti a punti_totali (o ai punti_custom per
    esercizio). con_griglia inietta la tabella dei punteggi (chi aggiunge
    \\end{document} dopo passa False e la inietta da sé).
    """
    latex = normalizza_sottopunti_inline(latex)   # "a) … b) …" nel paragrafo → elenco
    latex = fix_items_environment(latex)
    latex = migliora_spaziatura_sottopunti(latex)
    latex = aggiungi_spaziatura_grafici_tabelle(latex)
    latex = limita_altezza_grafici(latex)
    latex = rimuovi_vspace_corpo(latex)
    latex = rimuovi_punti_subsection(latex)
    # Il totale deve essere SEMPRE punti_totali: se dopo una modifica non lo è
    # (es. 90 invece di 100) si ridistribuisce, come fa la generazione iniziale.
    if mostra_punteggi and (riscala_totale or conta_punti_latex(latex) != punti_totali):
        latex = prepara_esercizi_aperti(latex, punti_totali)
        if punti_custom:
            latex = riscala_punti_custom(latex, punti_custom)
        else:
            latex = riscala_punti(latex, punti_totali)
    if con_griglia:
        latex = inietta_griglia(latex, punti_totali)
    return latex


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
        # La griglia viene iniettata da _compile, dopo \end{document}.
        return _postprocessa_latex(corpo, mostra_punteggi, punti_totali, riscala_totale=True)

    def _compile(latex: str):
        if "\\end{document}" not in latex:
            latex += "\n\\end{document}"
        if con_griglia:
            latex = inietta_griglia(latex, punti_totali)
        pdf, _, latex = compila_pdf_sicuro(latex)
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
            "\\fancyhead[C]{{\\color{red!70!black}\\textbf{\\large SOLUZIONI - DOCUMENTO RISERVATO}}}\n"
            "\\fancyfoot[C]{{\\tiny \\textit{Documento confidenziale - Vietata la distribuzione agli studenti}} \\quad {\\small Pagina \\thepage}}\n"
            "\\definecolor{solcolor}{RGB}{220,38,38}\n"
            "\\setlength{\\parindent}{0pt}\n"
            "\\setlength{\\parskip}{0.8em plus 0.3em minus 0.2em}\n"
            "\\begin{document}\n"
            "\\begin{center}\n"
            "  {\\color{solcolor}\\rule{\\textwidth}{2pt}} \\\\[0.3cm]\n"
            "  {\\color{solcolor}\\textbf{\\LARGE " + titolo_s + "}} \\\\[0.2cm]\n"
            "  {\\large \\textbf{\\textit{Documento Riservato al Docente}}} \\\\[0.1cm]\n"
            "  {\\small \\textit{Vietata la distribuzione agli studenti}} \\\\[0.4cm]\n"
            "  {\\color{solcolor}\\rule{\\textwidth}{1pt}} \\\\[1cm]\n"
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
if "gen_time_sec"      not in st.session_state: st.session_state.gen_time_sec = None
# ── Idea #19: Rubrica valutazione ────────────────────────────────────────────
if "rubrica_testo"     not in st.session_state: st.session_state.rubrica_testo = None
if "_rubrica_gen"      not in st.session_state: st.session_state._rubrica_gen = False
if "_rubrica_pdf"      not in st.session_state: st.session_state["_rubrica_pdf"] = None
if "_rubrica_docx"     not in st.session_state: st.session_state["_rubrica_docx"] = None
if "file_ispirazione"  not in st.session_state: st.session_state.file_ispirazione = None
# Analisi documento caricato
if "analisi_doc"          not in st.session_state: st.session_state.analisi_doc = None
# Lista di analisi accumulate da più file: [{"file_name","file_hash","analisi","file_mode","confirmed"}, ...]
if "analisi_docs_list"    not in st.session_state: st.session_state.analisi_docs_list = []
# Stato info consolidate ricavate da tutti i file
if "info_consolidate"     not in st.session_state: st.session_state.info_consolidate = {}
# Istruzioni per file (key = file_hash → testo istruzione)
if "istruzioni_per_file"  not in st.session_state: st.session_state.istruzioni_per_file = {}
# Percorso utente: None (home) | "B" (form di creazione)
if "input_percorso"       not in st.session_state: st.session_state.input_percorso = None
# Modalità uso file scelta dall'utente dopo l'analisi
if "file_mode"            not in st.session_state: st.session_state.file_mode = None
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
if "_fac_dialog_data"      not in st.session_state: st.session_state["_fac_dialog_data"]      = {}
if "_fac_confirmed"        not in st.session_state: st.session_state["_fac_confirmed"]        = False
# File di materiale caricato (analizzato solo quando si preme "Crea verifica")
if "_file_materiale"       not in st.session_state: st.session_state["_file_materiale"]       = None
if "_up_ciclo"             not in st.session_state: st.session_state["_up_ciclo"]             = 0
if "_pb_argomento_source"    not in st.session_state: st.session_state["_pb_argomento_source"] = None
if "_pb_argomento_manual_val" not in st.session_state: st.session_state["_pb_argomento_manual_val"] = ""

# ── CONTATORI E GESTIONE ABBONAMENTI ────────────────────────────────────────
_verifiche_mese = _get_verifiche_mese(st.session_state.utente.id) if st.session_state.utente else 0
_is_admin       = st.session_state.utente.email in ADMIN_EMAILS if st.session_state.utente else False

# Piano senza limite mensile (admin, pro, premium): deciso dal risultato di
# can_generate_verification, non dal nome del piano.
_illimitato = _is_admin

# Carica informazioni abbonamento utente
try:
    from subscription_management import get_subscription_manager
    subscription_manager = get_subscription_manager(supabase_admin)
    user_subscription = subscription_manager.get_user_subscription(st.session_state.utente.id)
    
    # Salva in session_state per uso in altre parti dell'app
    st.session_state.piano_utente = user_subscription['plan_id']
    st.session_state.abbonamento_attivo = user_subscription
    
    # Verifica limiti basandosi sul piano
    limits_check = subscription_manager.can_generate_verification(
        st.session_state.utente.id, 
        _verifiche_mese
    )
    _limite = not _is_admin and not limits_check['can_generate']
    _illimitato = _is_admin or limits_check.get('remaining') == float('inf')

except ImportError:
    # Fallback sistema vecchio se modulo non disponibile
    _limite = (not _is_admin) and (_verifiche_mese >= LIMITE_MENSILE)
    st.session_state.piano_utente = "free"
    st.session_state.abbonamento_attivo = None
except Exception as e:
    logger.error(f"Errore caricamento abbonamento: {e}")
    _limite = (not _is_admin) and (_verifiche_mese >= LIMITE_MENSILE)
    st.session_state.piano_utente = "free"
    st.session_state.abbonamento_attivo = None

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
    f'}}'
    f'}}'
    f'try{{new MutationObserver(fx).observe(d.body,{{subtree:true,attributes:true,childList:true}});}}catch(err){{}}'
    f'fx();'
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
    limite_raggiunto=_limite, T=T,
    MODELLI_DISPONIBILI=MODELLI_DISPONIBILI, LIMITE_MENSILE=LIMITE_MENSILE,
    giorni_al_reset_func=_giorni_al_reset, supabase_client=supabase,
    contatto_url=FEEDBACK_FORM_URL, illimitato=_illimitato,
    THEMES=THEMES, THEME_LABELS=THEME_LABELS,
)
modello_id = settings.get("modello_id", "gemini-2.5-flash-lite")

# Se il tema è cambiato dalla sidebar, aggiorna T
if settings.get("theme_changed"):
    T = THEMES[st.session_state.theme]
    st.rerun()

# Flag per sapere se siamo sulla landing (usato da breadcrumb e header)
_on_landing = (st.session_state.stage == STAGE_INPUT)   # la creazione è anche la home

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
                                punti_totali: int, durata: str | None = None) -> None:
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
    if durata in DURATE:
        defaults["durata"] = durata      # Breve / Standard / Lunga (stesso campo jsonb)
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
#  HELPERS — CREAZIONE E ANALISI FILE
# ═══════════════════════════════════════════════════════════════════════════════

def _esegui_analisi_documento(file_bytes: bytes, mime_type: str, file_name: str):
    """
    Lancia analisi AI sul file e popola st.session_state.analisi_doc.
    Chiama st.rerun() alla fine per aggiornare il dialogo.
    """
    file_hash = hash(file_bytes)
    ad = st.session_state.analisi_doc or {}
    if ad.get("file_hash") == file_hash:
        return  # già analizzato — evita ri-analisi su rerun

    # Analisi AI metadati — usa sempre Flash Lite (task leggero ed economico)
    try:
        _model_fast = genai.GenerativeModel(MODEL_FAST_ID)
        result = analizza_documento_caricato(
            model=_model_fast,
            file_bytes=file_bytes,
            mime_type=mime_type,
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
        st.session_state.file_mode     = result.get("modalita_uso_consigliata", "stile_e_struttura")

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

        # Al prossimo render (prima dei widget) materia e scuola rilevate riempiono i menu
        st.session_state["_applica_analisi"] = True

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
        logger.error(f"Analisi documento non riuscita: {e}", exc_info=True)
        st.warning("Non sono riuscito a leggere il file. Compila i campi a mano oppure prova con un altro file.", icon="🔬")


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
        _mostra_errore("Non sono riuscito a caricare le tue verifiche", e)
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
        _mostra_errore("Non sono riuscito a rinominare la verifica", e)
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
        _mostra_errore("Non sono riuscito a creare il link di condivisione", e)
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
        f"""
        <div style="text-align: center; margin-bottom: 2rem;">
            <h1 style="font-size: 2.5rem; font-weight: 700; color: {T['text']}; margin-bottom: 0.5rem;">
                Le Tue Verifiche
            </h1>
            <p style="font-size: 1.2rem; color: {T['muted']};">
                Gestisci, visualizza e scarica tutte le verifiche che hai creato
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    # Carica dati reali
    stats = _get_verifiche_stats()
    verifiche = _load_user_verifiche()
    
    # Riepilogo su una riga (al posto delle quattro card colorate)
    st.markdown(
        f'<div style="text-align:center;margin:-.4rem 0 1.4rem;font-family:DM Sans,sans-serif;'
        f'font-size:.95rem;color:{T["text2"]};">'
        f'<strong style="color:{T["text"]};">{stats["totali"]}</strong> verifiche in tutto &nbsp;·&nbsp; '
        f'<strong style="color:{T["text"]};">{stats["questo_mese"]}</strong> questo mese</div>',
        unsafe_allow_html=True,
    )

    # Filtri e ricerca
    col_search, col_materia, col_ordine = st.columns([3, 2, 2])
    
    with col_search:
        search_query = st.text_input("Cerca", placeholder="Cerca per materia o argomento…")
    
    # Materie uniche dalle verifiche reali
    materie_real = ["Tutte"] + sorted(list(set([v.get("materia", "Sconosciuta") for v in verifiche if v.get("materia")])))
    with col_materia:
        materia_filter = st.selectbox("Materia", materie_real)
    
    with col_ordine:
        ordine_filter = st.selectbox("Ordina per", ["Più recenti", "Più vecchie", "Alfabetico", "Materia"])
    
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
    
    # Mostra verifiche reali — a blocchi di 8 ("Mostra altre"): con centinaia di verifiche
    # il vecchio elenco completo creava migliaia di pulsanti a ogni clic.
    _n_mostra = max(8, int(st.session_state.get("_storico_mostra", 8)))
    if verifiche_filtrate:
        for i, verifica in enumerate(verifiche_filtrate[:_n_mostra]):
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
                        background: {T['card']};
                        border: 1px solid {T['border']};
                        border-radius: 12px;
                        padding: 1.1rem 1.3rem;
                        margin-bottom: .6rem;
                        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
                        transition: box-shadow 0.2s;
                    " onmouseover="this.style.boxShadow='0 4px 12px rgba(0, 0, 0, 0.15)'" onmouseout="this.style.boxShadow='0 1px 3px rgba(0, 0, 0, 0.1)'">
                        <div style="display: flex; justify-content: space-between; align-items: start;">
                            <div>
                                <h3 style="font-size: 1.12rem; font-weight: 700; color: {T['text']}; margin: 0 0 0.55rem 0; padding: 0;">
                                    {verifica.get('argomento', 'Verifica senza titolo')}
                                </h3>
                                <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
                                    <span style="background: {T['accent_light']}; color: {T['accent']}; padding: 0.25rem 0.75rem; border-radius: 20px; font-size: 0.8rem; font-weight: 500;">
                                        📚 {verifica.get('materia', 'Sconosciuta')}
                                    </span>
                                    <span style="background: {T['success']}22; color: {T['success']}; padding: 0.25rem 0.75rem; border-radius: 20px; font-size: 0.8rem; font-weight: 500;">
                                        🏫 {verifica.get('scuola', 'Non specificata')}
                                    </span>
                                    <span style="background: {T['warn']}22; color: {T['warn']}; padding: 0.25rem 0.75rem; border-radius: 20px; font-size: 0.8rem; font-weight: 500;">
                                        📝 {verifica.get('num_esercizi', '?')} esercizi
                                    </span>
                                    <span style="background: {T['bg2']}; color: {T['muted']}; padding: 0.25rem 0.75rem; border-radius: 20px; font-size: 0.8rem; font-weight: 500;">
                                        📅 {data_formattata}
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                
                # Azioni principali in primo piano; Rinomina ed Elimina nel menu "⋯".
                # I nomi colN restano quelli del codice sotto; l'ordine a schermo è:
                # Apri e modifica (col3) · Scarica PDF (col2) · Anteprima (col1) · Condividi (col7) · ⋯ (col4)
                col3, col2, col1, col7, col4 = st.columns([1.35, 1, 1, 1, 0.5])
                col4 = col4.popover("⋯", help="Rinomina o elimina questa verifica")

                with col1:
                    if st.button("Anteprima", icon=":material/visibility:", use_container_width=True, key=f"preview_{verifica.get('id')}_{i}"):
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
                                        st.error("Non sono riuscito a creare l'anteprima. Riprova.", icon="⚠️")
                                else:
                                    _mostra_errore_pdf(error, "questa verifica")
                            except Exception as e:
                                _mostra_errore("Non sono riuscito a creare l'anteprima", e)
                        else:
                            st.warning("⚠️ Contenuto LaTeX non disponibile per questa verifica")
                
                with col2:
                    pdf_disabled = not LATEX_AVAILABLE
                    pdf_help = "Non disponibile: LaTeX non è installato" if pdf_disabled else "Scarica la verifica in formato PDF"
                    
                    if st.button("Scarica PDF", icon=":material/download:", use_container_width=True, key=f"download_{verifica.get('id')}_{i}", 
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
                                    _mostra_errore_pdf(error, "questa verifica")
                            except Exception as e:
                                _mostra_errore("Non sono riuscito a preparare il PDF", e)
                        else:
                            st.warning("⚠️ Contenuto LaTeX non disponibile per questa verifica")
                
                with col3:
                    if st.button("Apri e modifica", icon=":material/edit_note:", use_container_width=True, key=f"facsimile_{verifica.get('id')}_{i}", type="primary"):
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
                                st.session_state.stage = STAGE_FINAL
                                st.session_state._prev_stage = None
                                st.session_state.input_percorso = None
                                st.rerun()
                                
                            except Exception as e:
                                _mostra_errore("Non sono riuscito ad aprire questa verifica", e)
                        else:
                            st.warning("⚠️ Contenuto LaTeX non disponibile per questa verifica")
                
                with col4:
                    _vid = verifica.get("id")
                    # Rinomina
                    nuovo_nome = st.text_input(
                        "Nome della verifica",
                        value=verifica.get("argomento", ""),
                        key=f"rename_input_{_vid}_{i}",
                    )
                    if st.button("💾 Salva nome", key=f"save_rename_{_vid}_{i}", use_container_width=True):
                        if nuovo_nome.strip() and _rinomina_verifica(_vid, nuovo_nome.strip()):
                            st.rerun()
                    st.divider()
                    # Elimina: conferma esplicita in due passaggi
                    if not st.session_state.get(f"confirm_delete_{_vid}", False):
                        if st.button("🗑️ Elimina", key=f"delete_{_vid}_{i}", use_container_width=True):
                            st.session_state[f"confirm_delete_{_vid}"] = True
                            st.rerun()
                    else:
                        st.warning("Eliminare definitivamente questa verifica?")
                        _c_si, _c_no = st.columns(2)
                        if _c_si.button("Sì, elimina", key=f"delete_yes_{_vid}_{i}", type="primary", use_container_width=True):
                            try:
                                res = supabase_admin.table("verifiche_storico").delete().eq("id", _vid).execute()
                                st.session_state.pop(f"confirm_delete_{_vid}", None)
                                if res.data:
                                    st.rerun()
                                else:
                                    st.error("Non sono riuscito a eliminare la verifica. Riprova.", icon="⚠️")
                            except Exception as e:
                                _mostra_errore("Non sono riuscito a eliminare la verifica", e)
                        if _c_no.button("No", key=f"delete_no_{_vid}_{i}", use_container_width=True):
                            st.session_state.pop(f"confirm_delete_{_vid}", None)
                            st.rerun()

                with col7:
                    # Condivisione
                    if st.button("Condividi", icon=":material/link:", use_container_width=True, key=f"share_{verifica.get('id')}_{i}"):
                        link = _genera_link_condivisione(verifica.get("id"))
                        if link:
                            st.success("🔗 Link generato!")
                            st.markdown(
                                f"""
                                <div style="
                                    background: {T['success']}18;
                                    border: 1px solid {T['success']};
                                    border-radius: 8px;
                                    padding: 1rem;
                                    margin: 0.5rem 0;
                                ">
                                    <div style="font-size: 0.9rem; color: {T['success']}; margin-bottom: 0.5rem;">
                                        📋 Link da condividere:
                                    </div>
                                    <div style="
                                        background: {T['card']}; color: {T['text']};
                                        border: 1px solid {T['border2']};
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
                                                    background: {T['success']};
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
                if i < min(len(verifiche_filtrate), _n_mostra) - 1:
                    st.markdown("<div style='height:1.1rem'></div>", unsafe_allow_html=True)
        if len(verifiche_filtrate) > _n_mostra:
            if st.button(f"Mostra altre ({len(verifiche_filtrate) - _n_mostra})", key="storico_mostra_altre", use_container_width=True):
                st.session_state["_storico_mostra"] = _n_mostra + 8
                st.rerun()
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


class _FileInMemoria:
    """File caricato tenuto in memoria: stessa interfaccia minima di un UploadedFile
    (type, name, getvalue) per genera_verifica, ma non dipende dal widget di upload."""

    def __init__(self, dati: bytes, mime: str, nome: str):
        self._dati, self.type, self.name = dati, mime, nome

    def getvalue(self) -> bytes:
        return self._dati


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

    # ── Materia e scuola rilevate dal file (applicate prima di creare i widget) ──
    if st.session_state.pop("_applica_analisi", False):
        _ic0 = st.session_state.info_consolidate
        if _ic0.get("materia") in MATERIE:
            st.session_state["sel_materia_b"] = _ic0["materia"]
        if _ic0.get("scuola") in SCUOLE:
            st.session_state["sel_scuola_b"] = _ic0["scuola"]

    # ── Generazione facsimile: scelta «Rifai questa verifica con dati nuovi» ──
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
                file_ispirazione=(
                    _FileInMemoria(_fm_fac["bytes"], _fm_fac["mime"], _fm_fac["name"])
                    if (_fm_fac := st.session_state.get("_file_materiale")) else None
                ),
                prog_placeholder=_prog_fac,
            )
            # La generazione fallita non fa rerun: restituisce valori neutri (nessun avvio)
            return ("", "Matematica", SCUOLE[0], True, True, 100, _n_fac, "", False,
                    _prog_fac, "1 ora", DURATA_DEFAULT)

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

            # Avanzamento: subito sotto il titolo (in basso, sotto il pulsante, non si vedeva)
            _prog_placeholder = st.empty()

            _mat_list = MATERIE + ["✏️ Altra materia..."]
            _mat_prev = _prev.get("materia") or _udef.get("materia", "Matematica")
            _mat_idx  = _mat_list.index(_mat_prev) if _mat_prev in _mat_list else 0
            _scu_prev = _prev.get("difficolta") or _udef.get("scuola", "")
            _scu_idx  = SCUOLE.index(_scu_prev) if _scu_prev in SCUOLE else 0

            # Auto-fill da analisi file se disponibile
            _info_cons = st.session_state.info_consolidate
            if _info_cons.get("materia") and _info_cons["materia"] in _mat_list:
                _mat_idx = _mat_list.index(_info_cons["materia"])
            if _info_cons.get("scuola") and _info_cons["scuola"] in SCUOLE:
                _scu_idx = SCUOLE.index(_info_cons["scuola"])

            # Materia e scuola già note (ultima verifica): una riga compatta con "cambia";
            # alla prima visita restano visibili entrambi i menu.
            _mat_ora = st.session_state.get("sel_materia_b", _mat_list[_mat_idx])
            _scu_ora = st.session_state.get("sel_scuola_b", SCUOLE[_scu_idx])
            if _udef.get("materia") and _udef.get("scuola"):
                _box_ms = st.expander(f"{_mat_ora} · {_scu_ora}  —  cambia", expanded=False, icon=":material/school:")
            else:
                _box_ms = st.container()
            with _box_ms:
                _col_m, _col_s = st.columns(2, gap="small")

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
            # ── RICHIESTA UNICA: argomento + indicazioni nello stesso riquadro ─────────
            st.markdown(
                '<div class="opt-label">Cosa vuoi nella verifica? ✱ '
                '<span class="opt-hint">Argomento nella prima riga, poi cosa includere o evitare</span></div>',
                unsafe_allow_html=True,
            )
            _esempio = esempio_richiesta(materia_scelta)

            # Controlla se c'è già un valore in session state per evitare il warning
            if "argomento_area_b" not in st.session_state:
                argomento_raw = st.text_area(
                    "richiesta",
                    value=_arg_default,
                    placeholder=_esempio,
                    height=190,
                    label_visibility="collapsed",
                    key="argomento_area_b",
                )
            else:
                argomento_raw = st.text_area(
                    "richiesta",
                    placeholder=_esempio,
                    height=190,
                    label_visibility="collapsed",
                    key="argomento_area_b",
                )

            # ── Traccia modifica manuale del riquadro ─────────────────────────────
            _auto_arg_ref = _info_cons.get("contenuto_argomento", "")
            _richiesta = argomento_raw.strip()
            if _richiesta and _richiesta != _auto_arg_ref:
                st.session_state["_pb_argomento_source"] = "manual"
                st.session_state["_pb_argomento_manual_val"] = _richiesta
            elif not _richiesta and st.session_state.get("_pb_argomento_source") == "manual":
                st.session_state["_pb_argomento_source"] = None
            # prima riga = argomento (titolo e prompt); righe successive = indicazioni
            argomento, _note_dal_riquadro = separa_argomento_e_note(_richiesta)

            _prefs = st.session_state._docente_prefs.get(materia_scelta, {})
            if not _prefs and st.session_state.utente and materia_scelta in MATERIE:
                _prefs = _carica_docente_preferenze(st.session_state.utente.id, materia_scelta)
                st.session_state._docente_prefs[materia_scelta] = _prefs

            # ── DURATA: un solo scatto sceglie numero di esercizi e tempo previsto ──────
            _nomi_dur = list(DURATE)
            # Si parte sempre da «Standard»: la lunghezza cambia da verifica a verifica,
            # non ha senso ereditare quella dell'ultima volta.
            _dur_salvata = DURATA_DEFAULT
            st.markdown('<div class="opt-label">Quanto deve essere lunga?</div>', unsafe_allow_html=True)
            durata_nome = st.radio(
                "Durata", _nomi_dur, index=_nomi_dur.index(_dur_salvata),
                format_func=lambda n: etichetta_durata(n, difficolta),
                horizontal=True, key="sel_durata_b", label_visibility="collapsed",
            )
            _par_dur   = parametri_durata(durata_nome, difficolta)
            durata_str = _par_dur["durata"]

            # Numero di esercizi di partenza: quello della durata scelta. Con «Rifai questa
            # verifica» numero di esercizi e punti vengono dal file (vedi il ramo facsimile).
            _n_default = _par_dur["num_esercizi"]
            _n_opts = list(range(1, 16))
            _n_idx  = (_n_opts.index(_n_default) if _n_default in _n_opts else 3)

            # ── Divisore sottile prima di Personalizzazione ──────────────────────
            st.markdown('<div class="divider-minimal"></div>', unsafe_allow_html=True)
            # ── Personalizzazione Avanzata — st.expander standard ────────────────
            # Defaults da session state (validi anche quando expander è chiuso)
            mostra_punteggi = st.session_state.get("_pers_punteggi", _udef.get("mostra_punteggi", True))
            con_griglia  = mostra_punteggi
            punti_totali = st.session_state.get("_pers_pt", _udef.get("punti_totali", 100))

            with st.expander("Altre opzioni (numero esercizi, punteggi, struttura)", expanded=False, icon=":material/tune:"):

                st.markdown('<div class="opt-label">Numero esatto di esercizi</div>', unsafe_allow_html=True)
                num_esercizi = st.selectbox(
                    "Numero esercizi",
                    options=_n_opts,
                    index=_n_idx,
                    label_visibility="collapsed",
                    key=f"sel_num_es_b_{durata_nome}",   # cambia con la durata: riparte dal preset
                    format_func=lambda x: f"{x} esercizi",
                )

                if _prefs.get("stile_desc"):
                    st.markdown(
                        f'<div style="background:{T["hint_bg"]};border:1px solid {T["hint_border"]};'
                        f'border-radius:8px;padding:.4rem .7rem;font-size:.9rem;color:{T["hint_text"]};'
                        f'font-family:DM Sans,sans-serif;margin-bottom:.7rem;">'
                        f'Preferenze salvate per <b>{materia_scelta}</b>: {_prefs["stile_desc"]}'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

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

            # ── Hai già del materiale? Upload + tre scelte (l'AI legge il file solo al clic) ──
            _rifiuto = st.session_state.pop("_analisi_rifiuto", None)
            if _rifiuto:
                # file non scolastico: lo tolgo e spiego perché
                st.session_state["_file_materiale"] = None
                st.session_state.file_ispirazione = None
                st.session_state["_up_ciclo"] += 1
                st.warning(_rifiuto.get("messaggio") or "Questo file non sembra materiale scolastico.", icon="📎")
            _fm = st.session_state.get("_file_materiale")
            with st.expander("Hai già del materiale? (opzionale)", expanded=bool(_fm), icon=":material/attach_file:"):
                if not _fm:
                    _up = st.file_uploader(
                        "Carica appunti, una verifica o un foglio di esercizi",
                        type=["pdf", "png", "jpg", "jpeg"],
                        key=f"pb_file_up_{st.session_state['_up_ciclo']}",
                        help="PDF o foto. Il file viene letto quando premi «Crea verifica».",
                    )
                    if _up:
                        _bytes_up = _up.getvalue()
                        st.session_state["_file_materiale"] = {
                            "bytes": _bytes_up, "mime": _up.type or "image/png",
                            "name": _up.name, "hash": hash(_bytes_up),
                        }
                        st.session_state.file_ispirazione = _FileInMemoria(
                            _bytes_up, _up.type or "image/png", _up.name)
                        st.rerun()
                else:
                    _nome_f = _fm["name"] if len(_fm["name"]) <= 38 else _fm["name"][:35] + "…"
                    st.markdown(
                        f'<div class="file-pool-card"><div class="fpc-header">'
                        f'<span class="fpc-name">📄 {_nome_f}</span></div></div>',
                        unsafe_allow_html=True,
                    )
                    _SCELTE_MATERIALE = {
                        "base_conoscenza":   "📚 Prendi spunto dai miei appunti",
                        "includi_esercizio": "✏️ Includi questi esercizi nella verifica",
                        "copia_fedele":      "🔁 Rifai questa verifica con dati nuovi",
                    }
                    _scelta_mat = st.radio(
                        "Cosa vuoi fare con questo file?",
                        options=list(_SCELTE_MATERIALE),
                        format_func=lambda k: _SCELTE_MATERIALE[k],
                        key="sel_materiale_b",
                    )
                    _SUGGERIMENTI_MATERIALE = {
                        "base_conoscenza":   "Esercizi nuovi sugli argomenti del tuo materiale, nello stesso livello.",
                        "includi_esercizio": "Gli esercizi del file entrano nella verifica; l'AI crea gli altri.",
                        "copia_fedele":      "Stessa struttura e stessi punteggi del file, con numeri e testi nuovi "
                                             "(il numero di esercizi e i punti vengono dal file).",
                    }
                    st.caption(_SUGGERIMENTI_MATERIALE[_scelta_mat])
                    if st.button("✕ Togli il file", key="pb_rm_materiale"):
                        for _k_rm in ("_file_materiale", "analisi_doc", "file_mode", "file_ispirazione"):
                            st.session_state[_k_rm] = None
                        st.session_state.analisi_docs_list = []
                        st.session_state.info_consolidate = {}
                        st.session_state.istruzioni_per_file = {}
                        st.session_state["_up_ciclo"] += 1
                        if st.session_state.get("_pb_argomento_source") != "manual":
                            st.session_state["_pb_argomento_source"] = None
                        st.rerun()

            # ── CTA: Genera Bozza ─────────────────────────────────────────────────
            _manca_arg = not argomento and not _fm
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
                "🚀  Crea verifica",
                use_container_width=True,
                type="primary",
                disabled=_limite or _manca_arg,
                key="genera_btn_b",
                help="Avvia la generazione AI della verifica. Potrai modificare ogni singolo esercizio prima di scaricare il PDF.",
            )
            st.markdown('</div>', unsafe_allow_html=True)

            if _limite:
                _render_limite_raggiunto(
                    T, LIMITE_MENSILE, _reset_label(*_giorni_al_reset()), FEEDBACK_FORM_URL,
                )

            # Avviso PDF non disponibile
            if not LATEX_AVAILABLE:
                st.markdown(
                    '<div style="background:' + T["warn"] + '22;border:1px solid ' + T["warn"] + ';border-radius:8px;'
                    f'padding:.8rem;margin:.5rem 0;">'
                    '<div style="text-align:center;font-size:.85rem;color:' + T["warn"] + ';font-weight:600;">'
                    f'⚠️ PDF non disponibile - LaTeX non installato</div>'
                    '<div style="text-align:center;font-size:.75rem;color:' + T["warn"] + ';margin-top:.2rem;">'
                    f'Potrai generare la verifica ma non scaricare il PDF</div></div>',
                    unsafe_allow_html=True,
                )

    # ── Costruisci nota finale con istruzioni per-file ────────────────────────
    _istr_per_file_testi = []
    for _fentry in st.session_state.analisi_docs_list:
        _fh_str = str(_fentry["file_hash"])
        _istr = st.session_state.istruzioni_per_file.get(_fh_str, "").strip()
        if _istr:
            _istr_per_file_testi.append(f"[File: {_fentry['file_name']}] {_istr}")
    _istruzioni_combinate = "\n".join(_istr_per_file_testi)

    note_extra_raw = _note_dal_riquadro
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
        durata_str,
        durata_nome,
    )


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
    prog_placeholder=None,         # st.empty() creato nel form, vicino al pulsante
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
            on_progress=_avanza,
        )

        if "_validation_score" in ris:
            logger.info(f"Validation score: {ris['_validation_score']}")

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
            st.session_state.preview_page   = 0
            st.session_state.last_preview_ts = st.session_state.verifiche["A"].get("pdf_ts") or 0

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
            logger.warning(f"Salvataggio storico non riuscito: {_e}")
            st.warning("⚠️ La bozza è pronta, ma non sono riuscito a salvarla nello storico.")

        # ── IDEA #1: Salva preferenze silenti dopo generazione riuscita ────
        _save_user_defaults_silent(
            materia=materia_scelta, scuola=difficolta,
            num_esercizi=num_esercizi_totali,
            mostra_punteggi=mostra_punteggi,
            punti_totali=punti_totali,
            durata=next((n for n, v in DURATE.items() if v["durata"] == durata_scelta), None),
        )

        # ── Vai alla schermata del risultato (anteprima + download + modifica)
        st.session_state.stage = STAGE_FINAL
        st.rerun()

    except Exception as _e:
        _prog.empty()
        _mostra_errore(
            "Non sono riuscito a creare la verifica", _e,
            riprova_flag="_riprova_genera", riprova_key="riprova_genera",
        )


# ═══════════════════════════════════════════════════════════════════════════════
#  STAGE_INPUT — orchestratore principale
# ═══════════════════════════════════════════════════════════════════════════════


def _render_stage_input():
    # La schermata di creazione e' anche la home: titolo breve + form.
    st.markdown(
        f'<div class="vf-narrow" style="text-align:center;padding:.2rem 0 1rem;">'
        f'<div style="font-family:DM Sans,sans-serif;font-size:1.7rem;font-weight:800;'
        f'letter-spacing:-.025em;color:{T["text"]};line-height:1.15;">Crea la tua verifica</div>'
        f'<div style="font-size:.98rem;color:{T["text2"]};margin-top:.35rem;'
        f'font-family:DM Sans,sans-serif;">Scrivi cosa ti serve: al resto pensa l’AI.</div></div>',
        unsafe_allow_html=True,
    )

    (
        argomento, materia_scelta, difficolta,
        mostra_punteggi, con_griglia, punti_totali,
        num_esercizi_totali, note_extra, genera_btn,
        _prog_ph_b, durata_str, durata_nome,
    ) = _render_percorso_b_form()

    _riprova      = st.session_state.pop("_riprova_genera", False)
    _dopo_analisi = st.session_state.pop("_genera_dopo_analisi", False)
    if not (genera_btn or _riprova or _dopo_analisi) or _limite:
        return

    # La barra di avanzamento sta in alto: porto la pagina in cima così si vede subito
    components.html(
        "<script>(function(){var d=window.parent.document;"
        "[\"[data-testid='stMain']\",\"section.main\",\"[data-testid='stAppViewContainer']\"]"
        ".forEach(function(q){var e=d.querySelector(q);if(e&&e.scrollTo)e.scrollTo({top:0,behavior:'smooth'});});"
        "window.parent.scrollTo({top:0,behavior:'smooth'});})();</script>",
        height=0,
    )

    # ── Il file viene letto dall'AI solo adesso (1 chiamata, solo se si crea davvero) ──
    _fm    = st.session_state.get("_file_materiale")
    _voce  = next((e for e in st.session_state.analisi_docs_list
                   if _fm and e["file_hash"] == _fm["hash"]), None)
    if _fm and _voce is None:
        st.session_state["_genera_dopo_analisi"] = True
        with _prog_ph_b.container(), st.spinner("Leggo il tuo file…"):
            _esegui_analisi_documento(_fm["bytes"], _fm["mime"], _fm["name"])
        # Se arriviamo qui la lettura non è andata a buon fine (nessun rerun): niente di fatto
        st.session_state.pop("_genera_dopo_analisi", None)
        return

    # ── Applica la scelta fatta sul file ──────────────────────────────────────
    _scelta_mat = None
    if _voce is not None:
        _scelta_mat = st.session_state.get("sel_materiale_b", "base_conoscenza")
        _voce["file_mode"] = _scelta_mat
        _voce["confirmed"] = True
        st.session_state.file_mode = _scelta_mat
        _consolida_info()
        if _scelta_mat == "copia_fedele":
            # «Rifai questa verifica»: numero di esercizi e punti vengono dal file
            st.session_state["_fac_dialog_data"] = {**_voce["analisi"], "file_hash": _voce["file_hash"]}
            st.session_state["_fac_confirmed"] = True
            st.rerun()

    if not argomento:
        st.warning(
            "Non ho capito l'argomento dal file: scrivilo nel riquadro «Cosa vuoi nella verifica?».",
            icon="✍️",
        )
        return

    _note_finale = note_extra

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
        durata_scelta=durata_str,
        num_esercizi_totali=num_esercizi_totali,
        punti_totali=punti_totali,
        mostra_punteggi=mostra_punteggi,
        con_griglia=con_griglia,
        note_generali=_note_finale,
        s_es=s_es,
        imgs_es=imgs_es_finale,
        # «Prendi spunto dai miei appunti»: il file viene davvero allegato alla richiesta
        file_ispirazione=(_FileInMemoria(_fm["bytes"], _fm["mime"], _fm["name"])
                          if (_scelta_mat == "base_conoscenza" and _fm) else None),
        prog_placeholder=_prog_ph_b,
    )
    return



# ═══════════════════════════════════════════════════════════════════════════════
#  STAGE_REVIEW
# ═══════════════════════════════════════════════════════════════════════════════

def _ricompila_verifica_a(mostra_punteggi: bool, con_griglia: bool, punti_totali: int,
                          riscala_totale: bool = False, punti_custom: list | None = None,
                          rileggi_blocchi: bool = False, blocco_modificato: int | None = None):
    """
    Ricostruisce il LaTeX della Fila A da review_blocks, applica il post-processing
    deterministico (_postprocessa_latex), compila il PDF e aggiorna session_state
    (latex, pdf, anteprima).

    riscala_totale=True ridistribuisce i punti su tutta la verifica (serve quando cambia
    il numero di esercizi o si confermano i punteggi); in tal caso review_blocks viene
    riletto dal LaTeX risultante (lo stesso succede con rileggi_blocchi=True).
    punti_custom: punti per esercizio scelti dal docente.
    blocco_modificato: indice dell'esercizio appena riscritto; se il totale non torna a
    punti_totali, è lui ad assorbire la differenza (gli altri esercizi non cambiano).
    Ritorna (pdf_bytes | None, errore).
    """
    if mostra_punteggi and blocco_modificato is not None:
        _bl = st.session_state.review_blocks
        if 0 <= blocco_modificato < len(_bl):
            _altri = sum(parse_pts_from_block_body(b["body"])
                         for j, b in enumerate(_bl) if j != blocco_modificato)
            _serve = punti_totali - _altri
            _mod = _bl[blocco_modificato]
            _pts_mod = parse_pts_from_block_body(_mod["body"])
            if _serve > 0 and _pts_mod == 0:
                # la risposta AI non ha punteggi: li assegno io (divisi in parti uguali)
                _n_item = len(re.findall(r"\\item\b", _mod["body"]))
                if _n_item:
                    _mod["body"] = apply_item_pts_to_body(
                        _mod["body"], bilancia_punti([1] * _n_item, _serve))
                else:
                    _mod["body"] = _mod["body"].rstrip() + f" ({_serve} pt)"
            elif _serve > 0 and _pts_mod != _serve:
                _mod["body"] = riscala_single_block(_mod["title"], _mod["body"], _serve)
    # Difesa: un \end{document} dentro un esercizio taglierebbe tutti i successivi.
    for _b in st.session_state.review_blocks:
        _b["body"] = re.sub(r"\s*\\end\{document\}.*$", "", _b["body"], flags=re.DOTALL)
    latex = reconstruct_latex(
        st.session_state.review_preamble, st.session_state.review_blocks,
    )
    latex = _postprocessa_latex(
        latex, mostra_punteggi, punti_totali,
        riscala_totale=riscala_totale, punti_custom=punti_custom, con_griglia=con_griglia,
    )

    va = st.session_state.verifiche["A"]
    # Compila prima: se un grafico esce rotto (errori TikZ) viene sostituito da un segnaposto
    # e il LaTeX effettivo cambia.
    latex_inviato = latex
    pdf, err, latex = compila_pdf_sicuro(latex)
    va["latex"] = va["latex_originale"] = latex
    # Se i punti sono stati ridistribuiti o un grafico è stato sostituito, i blocchi vanno
    # riletti dal LaTeX finale (altrimenti l'editor mostrerebbe i valori vecchi).
    if latex != latex_inviato:
        rileggi_blocchi = True
    if mostra_punteggi and not (riscala_totale or rileggi_blocchi):
        rileggi_blocchi = sum(parse_pts_from_block_body(b["body"])
                              for b in st.session_state.review_blocks) != punti_totali
    if riscala_totale or rileggi_blocchi:
        _pre, _blocchi = extract_blocks(latex)
        if _blocchi:
            st.session_state.review_preamble = _pre
            st.session_state.review_blocks   = _blocchi

    if pdf:
        va["pdf"]     = pdf
        va["pdf_ts"]  = time.time()
        va["preview"] = True
        imgs, _ = pdf_to_images_bytes(pdf)
        st.session_state.preview_images  = imgs or []
        st.session_state.preview_page    = 0
        st.session_state.last_preview_ts = va["pdf_ts"]   # anteprima già allineata al PDF
    return pdf, err


def _applica_punti_a_blocchi(righe: list, punti: list) -> None:
    """
    Scrive in review_blocks i punti scelti nella tabella "Cambia i punteggi".
    righe[k] = (indice esercizio, indice sottopunto); punti[k] = punti di quella riga.
    Il titolo di ogni esercizio riporta il subtotale.
    """
    per_esercizio: dict = {}
    for (i, j), v in zip(righe, punti):
        per_esercizio.setdefault(i, {})[j] = v
    for i, valori in per_esercizio.items():
        lista = [valori[j] for j in sorted(valori)]
        blocco = st.session_state.review_blocks[i]
        blocco["body"] = apply_item_pts_to_body(blocco["body"], lista)
        titolo = re.sub(r"\s*\(\d+\s*pt\)", "", blocco["title"]).strip()
        blocco["title"] = f"{titolo} ({sum(lista)} pt)"


def _pulisci_stato_revisione():
    """Cancella i valori per-esercizio (punteggi, undo, conferme) quando cambia la struttura."""
    for _k in list(st.session_state.keys()):
        if (_k.startswith("item_pt_") or _k.startswith("_undo_block_")
                or _k in ("recalibra_pts", "_conf_elimina", "review_selectbox")):
            del st.session_state[_k]


def _rigenera_esercizio_guidato(idx, istruzione, etichetta, materia, argomento, modello,
                                mostra_punteggi, con_griglia, punti_totali, status_ph):
    """
    "Più facile" / "Più difficile": rigenera un solo esercizio con un'istruzione fissa
    (rigenera_singolo_blocco → prompt_rigenera_blocco), riporta i punti all'originale,
    ricompila il PDF. Il backup per "Annulla modifica" è salvato prima della chiamata.
    """
    blocchi = st.session_state.review_blocks
    n_blocks = len(blocchi)
    title, body = blocchi[idx]["title"], blocchi[idx]["body"]
    _pts = st.session_state.get("recalibra_pts", [])
    target = int(_pts[idx]) if _pts and len(_pts) == n_blocks else parse_pts_from_block_body(body)

    st.session_state[f"_undo_block_{idx}"] = dict(blocchi[idx])
    with status_ph.status(f"{etichetta} l'esercizio {idx+1}…", expanded=True) as stato:
        try:
            nuovo = rigenera_singolo_blocco(
                genai.GenerativeModel(modello), materia,
                f"\\subsection*{{{title}}}\n{body}", istruzione, mostra_punteggi,
            )
            # rigenera_singolo_blocco ripulisce la risposta con pulisci_corpo_latex, che in
            # coda aggiunge \end{document}: va tolto, altrimenti la verifica finirebbe
            # a questo esercizio e quelli successivi sparirebbero dal PDF.
            nuovo = re.sub(r"\\end\{document\}.*$", "", nuovo, flags=re.DOTALL).strip()
            m = re.match(r"\\subsection\*\{([^}]*)\}(.*)", nuovo, re.DOTALL)
            new_title = m.group(1) if m else title
            new_body  = m.group(2).strip() if m else nuovo.strip()
            new_title = re.sub(r"\s*\(\d+\s*pt\)", "", new_title).strip() or title
            # Se il titolo originale era numerato ("Esercizio 3: …") e la risposta no, lo ripristina
            _pref = re.match(r"^(Esercizio\s*\d+\s*[:.\-]\s*)", title, flags=re.IGNORECASE)
            if _pref and not re.match(r"^Esercizio\s*\d+", new_title, flags=re.IGNORECASE):
                new_title = _pref.group(1) + new_title
            if mostra_punteggi and target > 0:
                new_body = riscala_single_block(new_title, new_body, target)
            blocchi[idx]["title"] = new_title
            blocchi[idx]["body"]  = new_body
            st.session_state.pop("recalibra_pts", None)

            pdf, err = _ricompila_verifica_a(mostra_punteggi, con_griglia, punti_totali, blocco_modificato=idx)
            if not pdf:
                stato.update(label="PDF non aggiornato", state="error", expanded=False)
                _mostra_errore(
                    "Ho modificato l'esercizio ma non sono riuscito a rifare il PDF", err,
                    consiglio="Premi «Annulla modifica» per tornare indietro, poi riprova.",
                )
                return
            stato.update(label="Esercizio aggiornato!", state="complete", expanded=False)
            st.toast(f"Esercizio {idx+1} aggiornato!", icon="✅")
            st.rerun()
        except Exception as e:
            stato.update(label="Modifica non riuscita", state="error", expanded=False)
            _mostra_errore("Non sono riuscito a modificare questo esercizio", e)


def _elimina_esercizio(idx, mostra_punteggi, con_griglia, punti_totali) -> bool:
    """
    Elimina un esercizio, rinumera i titoli, ridistribuisce i punti sul totale e
    ricompila. Se il PDF non si compila ripristina lo stato precedente.
    """
    backup_blocchi = copy.deepcopy(st.session_state.review_blocks)
    backup_pre     = st.session_state.review_preamble
    va             = st.session_state.verifiche["A"]
    backup_latex   = (va.get("latex"), va.get("latex_originale"))

    blocchi = st.session_state.review_blocks
    del blocchi[idx]
    for i, b in enumerate(blocchi):
        b["title"] = re.sub(
            r"^(Esercizio\s*)\d+", lambda m, n=i + 1: f"{m.group(1)}{n}",
            b["title"], flags=re.IGNORECASE,
        )
    pdf, err = _ricompila_verifica_a(mostra_punteggi, con_griglia, punti_totali, riscala_totale=True)
    if not pdf:
        st.session_state.review_blocks   = backup_blocchi
        st.session_state.review_preamble = backup_pre
        va["latex"], va["latex_originale"] = backup_latex
        _mostra_errore_pdf(err, "questa verifica")
        return False
    _pulisci_stato_revisione()
    st.session_state.review_sel_idx = min(idx, len(st.session_state.review_blocks) - 1)
    st.session_state.gen_params["num_esercizi"] = len(st.session_state.review_blocks)
    st.session_state.force_preview_refresh = True
    return True


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
    _c_accent  = T["accent"]
    _c_accent2 = T["accent2"]
    _c_border2 = T["border2"]
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
        '<div style="background:linear-gradient(135deg,' + T["accent2"] + ' 0%,' + T["accent"] + ' 100%);'
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
    #  Sinistra [2]: box unico — KaTeX + azioni esercizio + Altre modifiche
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
            elif idx in esercizi_con_grafico_mancante(blocks):
                st.warning(
                    "Questo esercizio rimanda a un grafico che non è stato disegnato. "
                    "Premi «Rigenera» per riprovare, oppure correggi il testo in «Altre modifiche».",
                    icon="📉",
                )

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
                        _undo_pdf, _undo_err = _ricompila_verifica_a(
                            mostra_punteggi, con_griglia, punti_totali, riscala_totale=True,
                        )
                        if _undo_pdf:
                            st.toast("↩️ Modifica annullata — versione precedente ripristinata!", icon="↩️")
                            st.rerun()
                        else:
                            _mostra_errore_pdf(_undo_err, "questa verifica")
                with _undo_col2:
                    st.markdown(
                        f'<div style="font-size:.72rem;color:{T["muted"]};font-family:DM Sans,sans-serif;'
                        f'padding:.3rem 0;line-height:1.4;">'
                        f'🕐 Versione precedente disponibile</div>',
                        unsafe_allow_html=True
                    )

            # ── Azioni sull'esercizio: rigenera, numeri, più facile/difficile, elimina ──
            _marker = '<div class="btn-outline-accent-marker" style="display:none;height:0;line-height:0"></div>'
            _qr_col1, _qr_col2 = st.columns(2, gap="small")
            with _qr_col1:
                st.markdown(_marker, unsafe_allow_html=True)
                quick_regen = st.button(
                    "Cambia i numeri",
                    key=f"quick_regen_{idx}",
                    use_container_width=True,
                    help="Stesso esercizio con valori e dati numerici nuovi.",
                )
            with _qr_col2:
                st.markdown(_marker, unsafe_allow_html=True)
                cambia_tutto = st.button(
                    "Rigenera",
                    key=f"cambia_tutto_{idx}",
                    use_container_width=True,
                    help="Un esercizio completamente diverso, sullo stesso argomento.",
                )
            _lv_col1, _lv_col2, _lv_col3 = st.columns(3, gap="small")
            with _lv_col1:
                st.markdown(_marker, unsafe_allow_html=True)
                piu_facile = st.button(
                    "Più facile", key=f"piu_facile_{idx}", use_container_width=True,
                    help="Semplifica numeri e calcoli, mantenendo lo stesso argomento.",
                )
            with _lv_col2:
                st.markdown(_marker, unsafe_allow_html=True)
                piu_difficile = st.button(
                    "Più difficile", key=f"piu_difficile_{idx}", use_container_width=True,
                    help="Numeri meno immediati e un passaggio di ragionamento in più.",
                )
            with _lv_col3:
                st.markdown(_marker, unsafe_allow_html=True)
                elimina = st.button(
                    "Elimina", key=f"elimina_{idx}", use_container_width=True,
                    disabled=(n_blocks <= 1),
                    help="Toglie questo esercizio e ridistribuisce i punti sugli altri.",
                )
            if elimina:
                st.session_state["_conf_elimina"] = idx
            elif st.session_state.get("_conf_elimina") not in (None, idx):
                st.session_state.pop("_conf_elimina", None)

            elimina_si = False
            if st.session_state.get("_conf_elimina") == idx:
                st.warning(
                    f"Eliminare l'esercizio {idx+1}? I punti verranno ridistribuiti sugli altri esercizi."
                )
                _el_c1, _el_c2 = st.columns(2, gap="small")
                with _el_c1:
                    elimina_si = st.button("Sì, elimina", key=f"elimina_si_{idx}",
                                           type="primary", use_container_width=True)
                with _el_c2:
                    if st.button("No, tienilo", key=f"elimina_no_{idx}", use_container_width=True):
                        st.session_state.pop("_conf_elimina", None)
                        st.rerun()

            # Placeholder feedback immediato — sotto i pulsanti, nella colonna sinistra
            _action_ph = st.empty()
            if quick_regen:
                _action_ph.info(f"Generazione variante esercizio {idx+1}…")
            elif cambia_tutto:
                _action_ph.info(f"Generazione nuovo esercizio {idx+1}…")

            st.markdown("<div style='height:.4rem'></div>", unsafe_allow_html=True)

            # ── Altre modifiche — descrizione libera, chiusa di default ──────────
            with st.expander("✏️ Altre modifiche", expanded=False):
                st.markdown(
                    '<div style="font-size:.95rem;color:' + T["text2"] + ';margin-bottom:.5rem;'
                    'font-family:DM Sans,sans-serif;line-height:1.5;">'
                    'Descrivi la modifica — l\'AI rigenererà solo questo esercizio.'
                    '</div>'
                    '<div style="font-size:.9rem;color:' + T["warn"] + ';margin-bottom:.7rem;'
                    'font-family:DM Sans,sans-serif;font-weight:600;'
                    'background:' + T["warn"] + '18;border:1px solid ' + T["warn"] + '44;'
                    'border-radius:8px;padding:.4rem .7rem;">'
                    'Per cambiare i punteggi usa «Cambia i punteggi» qui sotto.</div>',
                    unsafe_allow_html=True
                )
                istruzione = st.text_area(
                    f"Modifica esercizio {idx+1}",
                    placeholder="es. Converti in Vero/Falso · Aggiungi un sottopunto · Usa un contesto di vita quotidiana",
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
                            "Per modificare i punti usa il pannello **⚖️ Cambia i punteggi** "
                            "qui sotto — imposta i valori desiderati e premi **Applica Punteggi**. "
                            "Questo campo è riservato alle modifiche al contenuto (testo, difficoltà, formato)."
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
        
        # LOGICA AGGRESSIVA: forza sempre l'aggiornamento se c'è un PDF recente
        force_update = False
        
        # Condizione 0: force refresh esplicito
        if st.session_state.get("force_preview_refresh", False):
            force_update = True
            logger.info("FORCE REFRESH: flag force_preview_refresh rilevato")
            # Resetta il flag dopo l'uso
            st.session_state.force_preview_refresh = False
        
        # Condizione 1: timestamp più recente
        elif current_pdf_ts and current_pdf_ts > last_preview_ts:
            force_update = True
            
        # Condizione 2: se il timestamp del PDF è molto recente (ultimi 5 secondi)
        elif current_pdf_ts and (time.time() - current_pdf_ts) < 5:
            force_update = True
            
        # Condizione 3: se non ci sono immagini preview ma c'è un PDF
        elif current_pdf_ts and not st.session_state.get("preview_images"):
            force_update = True
        
        if force_update:
            vA_pdf = vA.get("pdf")
            if vA_pdf:
                try:
                    logger.info(f"FORZATURA AGGIORNAMENTO PREVIEW - PDF ts: {current_pdf_ts}, Last preview: {last_preview_ts}")
                    new_imgs, _ = pdf_to_images_bytes(vA_pdf)
                    st.session_state.preview_images = new_imgs or []
                    st.session_state.last_preview_ts = current_pdf_ts
                    logger.info(f"Preview images aggiornate FORZATAMENTE - {len(new_imgs) if new_imgs else 0} pagine")
                except Exception as e:
                    logger.error(f"Errore aggiornamento preview forzato: {e}")
            else:
                logger.warning("PDF ts presente ma nessun PDF disponibile per preview")
        
        imgs = st.session_state.preview_images
        if imgs:
            n_pages  = len(imgs)
            _pg = max(0, min(st.session_state.get("preview_page", 0), n_pages - 1))

            # Forza refresh dell'immagine (st.image non supporta key)
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
            f"- {REGOLA_SOTTOPUNTI_MODIFICA}\n"
            f"- {REGOLA_GRAFICO_CURVE}\n"
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
                _qr_pdf, _ = _ricompila_verifica_a(mostra_punteggi, con_griglia, punti_totali, blocco_modificato=idx)
                if not _qr_pdf:
                    _qr_st.update(label="PDF non aggiornato", state="error", expanded=False)
                    _mostra_errore(
                        "Ho cambiato i numeri ma non sono riuscito a rifare il PDF", "compilazione PDF",
                        consiglio="Premi «Annulla modifica» per tornare indietro, poi riprova.",
                    )
                else:
                    _qr_st.update(label="Variante pronta!", state="complete", expanded=False)
                    st.toast(f"Variante esercizio {idx+1} generata!", icon="✅")
                    st.rerun()
            except Exception as _qr_e:
                _qr_st.update(label="Variante non riuscita", state="error", expanded=False)
                _mostra_errore("Non sono riuscito a cambiare i numeri di questo esercizio", _qr_e)

    # ── Più facile / Più difficile — un solo esercizio, istruzione fissa ──────
    if piu_facile or piu_difficile:
        _action_ph.empty()
        _rigenera_esercizio_guidato(
            idx,
            istruzione_livello_esercizio(bool(piu_difficile), argomento_str),
            "Rendo più difficile" if piu_difficile else "Rendo più facile",
            materia_str, argomento_str, modello_rw,
            mostra_punteggi, con_griglia, punti_totali, _action_ph,
        )

    # ── Elimina esercizio (dopo conferma) ─────────────────────────────────────
    if elimina_si:
        with st.spinner("Elimino l'esercizio e ricalcolo i punti…"):
            _ok_el = _elimina_esercizio(idx, mostra_punteggi, con_griglia, punti_totali)
        if _ok_el:
            st.toast("Esercizio eliminato", icon="🗑️")
            st.rerun()

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
                f"- {REGOLA_SOTTOPUNTI_MODIFICA}\n"
                f"- {punti_nota}\n"
                f"- {_grafici_rule_rw}\n"
                f"- {REGOLA_GRAFICO_CURVE}\n"
                f"- NON inserire MAI commenti LaTeX (%% ...) nel corpo degli esercizi.\n"
                f"- NON includere preambolo o \\begin{{document}}.\n"
                f"OUTPUT: SOLO codice LaTeX del blocco esercizio."
            )
            st.session_state[f"_undo_block_{idx}"] = dict(st.session_state.review_blocks[idx])
            _loading_ph.empty()
            
            # Container elegante per la barra di stato
            with _loading_ph.container():
                # Header animato
                st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg, {T['accent2']} 0%, {T['accent']} 100%);
                    border-radius: 12px;
                    padding: 1rem;
                    margin-bottom: 1rem;
                    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.2);
                    animation: pulse 2s infinite;
                ">
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <div style="
                            width: 24px; height: 24px;
                            border: 3px solid rgba(255,255,255,0.3);
                            border-top: 3px solid white;
                            border-radius: 50%;
                            animation: spin 1s linear infinite;
                        "></div>
                        <div style="color: white; font-family: 'DM Sans', sans-serif; font-weight: 600;">
                            🎨 Modifica esercizio {idx+1} in corso...
                        </div>
                    </div>
                    <div style="color: rgba(255,255,255,0.9); font-size: 0.9rem; margin-top: 0.5rem; font-family: 'DM Sans', sans-serif;">
                        L'AI sta analizzando la richiesta e rigenerando l'esercizio...
                    </div>
                </div>
                
                <style>
                @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
                @keyframes pulse {{ 0% {{ opacity: 1; }} 50% {{ opacity: 0.8; }} 100% {{ opacity: 1; }} }}
                </style>
                """, unsafe_allow_html=True)
            
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

                # Ricompila il PDF e aggiorna la preview dopo la modifica
                _pdf_rw, _err_rw = _ricompila_verifica_a(mostra_punteggi, con_griglia, punti_totali, blocco_modificato=idx)
                logger.info(f"COMPILAZIONE PDF POST-MODIFICA - Success: {_pdf_rw is not None}, Error: {_err_rw}")
                if _pdf_rw:
                    st.session_state.force_preview_refresh = True

                    # Messaggio di successo elegante
                    _loading_ph.markdown(f"""
                    <div style="
                        background: linear-gradient(135deg, {T['success']} 0%, {T['success']} 100%);
                        border-radius: 12px;
                        padding: 1rem;
                        box-shadow: 0 4px 15px rgba(16, 185, 129, 0.2);
                        animation: slideIn 0.5s ease-out;
                    ">
                        <div style="display: flex; align-items: center; gap: 12px;">
                            <div style="
                                width: 24px; height: 24px;
                                background: white;
                                border-radius: 50%;
                                display: flex;
                                align-items: center;
                                justify-content: center;
                                font-size: 14px;
                            ">✓</div>
                            <div style="color: white; font-family: 'DM Sans', sans-serif; font-weight: 600;">
                                🎉 Modifica applicata con successo!
                            </div>
                        </div>
                        <div style="color: rgba(255,255,255,0.9); font-size: 0.9rem; margin-top: 0.5rem; font-family: 'DM Sans', sans-serif;">
                            L'esercizio {idx+1} è stato aggiornato e il PDF è stato rigenerato.
                        </div>
                    </div>
                    
                    <style>
                    @keyframes slideIn {{ 
                        0% {{ transform: translateY(-20px); opacity: 0; }} 
                        100% {{ transform: translateY(0); opacity: 1; }} 
                    }}
                    </style>
                    """, unsafe_allow_html=True)
                    
                    st.toast(f"Esercizio {idx+1} aggiornato!", icon="✅"); st.rerun()
                else:
                    _loading_ph.empty()
                    _mostra_errore(
                        "Ho modificato l'esercizio ma non sono riuscito a rifare il PDF", _err_rw,
                        consiglio="Premi «Annulla modifica» per tornare indietro, poi riprova.",
                    )
            except Exception as e:
                _loading_ph.empty()
                _mostra_errore(
                    "Non sono riuscito ad applicare la modifica", e,
                    consiglio="Prova a riformulare la richiesta con parole diverse.",
                )

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
            f"- {REGOLA_SOTTOPUNTI_MODIFICA}\n"
            f"- {_ct_punti_nota}\n"
            f"- Se includi un grafico, usa SOLO codice TikZ/pgfplots COMPLETO e COMPILABILE. "
              f"NON usare \\includegraphics{{placeholder}} né commenti '%% inserire figura'.\n"
            f"- {REGOLA_GRAFICO_CURVE}\n"
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
                _ct_pdf, _ = _ricompila_verifica_a(mostra_punteggi, con_griglia, punti_totali, blocco_modificato=idx)
                if not _ct_pdf:
                    _ct_st.update(label="PDF non aggiornato", state="error", expanded=False)
                    _mostra_errore(
                        "Ho cambiato l'esercizio ma non sono riuscito a rifare il PDF", "compilazione PDF",
                        consiglio="Premi «Annulla modifica» per tornare indietro, poi riprova.",
                    )
                else:
                    _ct_st.update(label="Esercizio cambiato!", state="complete", expanded=False)
                    st.toast(f"Esercizio {idx+1} cambiato!", icon="✅")
                    st.rerun()
            except Exception as _ct_e:
                _ct_st.update(label="Cambio non riuscito", state="error", expanded=False)
                _mostra_errore("Non sono riuscito a cambiare questo esercizio", _ct_e)


    # ── Cambia i punteggi — una tabella unica, totale sempre ribilanciato ─────
    if mostra_punteggi and n_blocks > 0:
        with st.expander("⚖️ Cambia i punteggi", expanded=False):
            _righe, _dati = [], []          # _righe[k] = (esercizio, sottopunto)
            for _i, _b in enumerate(st.session_state.review_blocks):
                _items_rc = parse_items_from_block(_b["body"], _b.get("title", ""))
                _tit = _clean_title(re.sub(r"\s*\(\d+\s*pt\)", "", _b["title"]))
                for _j, (_lbl, _short, _pt) in enumerate(_items_rc):
                    _testo = (_short or "").strip()
                    _righe.append((_i, _j))
                    _dati.append({
                        "Esercizio": f"{_i+1}. {_tit[:30]}" if _j == 0 else "",
                        "Richiesta": (f"{_lbl} {_testo[:46]}…" if len(_testo) > 46
                                      else f"{_lbl} {_testo}").strip(),
                        "Punti": int(_pt),
                    })

            if not _dati:
                st.caption("Nessun punteggio da modificare in questa verifica.")
            else:
                st.markdown(
                    f'<div style="font-size:.88rem;color:{T["text2"]};margin-bottom:.4rem;'
                    f'font-family:DM Sans,sans-serif;">Cambia i numeri nella colonna <b>Punti</b>. '
                    f'Il totale deve fare <b>{punti_totali} pt</b>: se non torna, '
                    f'lo ribilancio io quando applichi.</div>',
                    unsafe_allow_html=True,
                )
                _firma = abs(hash(tuple((d["Esercizio"], d["Richiesta"], d["Punti"]) for d in _dati)))
                _tab = st.data_editor(
                    _dati,
                    key=f"rc_editor_{_firma}",   # nuova chiave se i punti cambiano da fuori
                    hide_index=True,
                    use_container_width=True,
                    disabled=["Esercizio", "Richiesta"],
                    column_config={
                        "Esercizio": st.column_config.TextColumn("Esercizio", width="medium"),
                        "Richiesta": st.column_config.TextColumn("Richiesta", width="large"),
                        "Punti": st.column_config.NumberColumn(
                            "Punti", min_value=0, max_value=punti_totali, step=1,
                            format="%d", required=True, width="small"),
                    },
                )
                _tab_righe = _tab.to_dict("records") if hasattr(_tab, "to_dict") else list(_tab)

                def _intero(v):
                    try:
                        return max(0, int(v))
                    except (TypeError, ValueError):
                        return 0

                _nuovi = [_intero(r.get("Punti")) for r in _tab_righe]
                _totale_rc = sum(_nuovi)
                _per_es_sub = {}
                for (_i, _j), _v in zip(_righe, _nuovi):
                    _per_es_sub[_i] = _per_es_sub.get(_i, 0) + _v
                _sub_txt = " · ".join(f"Es. {_i+1}: {_p} pt" for _i, _p in sorted(_per_es_sub.items()))

                if _totale_rc == punti_totali:
                    st.success(f"Totale: {_totale_rc} pt — perfetto.   ({_sub_txt})", icon="✅")
                else:
                    st.warning(
                        f"Totale: {_totale_rc} pt invece di {punti_totali}. "
                        f"Premendo «Applica» ribilancio tutto a {punti_totali} pt in proporzione.   ({_sub_txt})",
                        icon="⚖️",
                    )

                if st.button("✅ Applica punteggi", key="rc_applica",
                             use_container_width=True, type="primary"):
                    _finali = _nuovi if _totale_rc == punti_totali else bilancia_punti(_nuovi, punti_totali)
                    _applica_punti_a_blocchi(_righe, _finali)

                    with st.spinner("Ricompilazione PDF con i nuovi punteggi…"):
                        _pdf_rc, _err_rc = _ricompila_verifica_a(
                            mostra_punteggi, con_griglia, punti_totali, rileggi_blocchi=True,
                        )
                    if _pdf_rc:
                        for _kk in list(st.session_state.keys()):
                            if _kk.startswith("rc_editor_") or re.match(r"^item_pt_\d+_\d+$", _kk):
                                del st.session_state[_kk]
                        st.session_state.pop("recalibra_pts", None)
                        st.toast(
                            "✅ Punteggi applicati" + ("" if _totale_rc == punti_totali
                                                       else f" (ribilanciati a {punti_totali} pt)"),
                            icon="⚖️",
                        )
                        st.rerun()
                    else:
                        _mostra_errore_pdf(_err_rc, "questa verifica")

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
            _pts_custom = st.session_state.get("recalibra_pts", [])
            pdf_bytes, err = _ricompila_verifica_a(
                mostra_punteggi, con_griglia, punti_totali, riscala_totale=True,
                punti_custom=_pts_custom if _pts_custom and len(_pts_custom) == n_blocks else None,
            )
            if pdf_bytes:
                st.session_state.stage = STAGE_FINAL
                st.rerun()
            else:
                _mostra_errore_pdf(err, "questa verifica")

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

    # ── Anteprima aggiornata se il PDF è cambiato (modifiche nell'editor) ─────
    _pdf_ts   = vA.get("pdf_ts")
    _last_ts  = st.session_state.get("last_preview_ts", 0)
    _riallinea = (
        st.session_state.pop("force_preview_refresh", False)
        or (_pdf_ts and _pdf_ts > _last_ts)
        or (_pdf_ts and not st.session_state.get("preview_images"))
    )
    if _riallinea and vA.get("pdf"):
        try:
            _imgs_new, _ = pdf_to_images_bytes(vA["pdf"])
            st.session_state.preview_images  = _imgs_new or []
            st.session_state.last_preview_ts = _pdf_ts or time.time()
        except Exception as _e:
            logger.error(f"Errore aggiornamento anteprima (final): {_e}")

    # ── Intestazione compatta ─────────────────────────────────────────────────
    st.markdown(
        f'<div style="text-align:center;margin:.2rem 0 1.1rem;">'
        f'<div style="font-family:DM Sans,sans-serif;font-size:1.7rem;font-weight:900;'
        f'color:{T["text"]};letter-spacing:-.025em;line-height:1.15;">'
        f'<span style="display:inline-flex;align-items:center;justify-content:center;width:1.6rem;height:1.6rem;'
        f'border-radius:50%;background:{T["success"]};color:#fff;font-size:1rem;margin-right:.55rem;'
        f'vertical-align:.12em;">✓</span>La verifica è pronta</div>'
        f'<div style="font-size:.9rem;color:{T["text2"]};font-family:DM Sans,sans-serif;margin-top:.35rem;">'
        + mat_str + ' &nbsp;·&nbsp; ' + scu_str + ' &nbsp;·&nbsp; ' + arg_str +
        f'</div></div>',
        unsafe_allow_html=True
    )

    # ═══════════════════════════════════════════════════════════════════════════
    #  RISULTATO — anteprima a sinistra, scarica e modifica a destra
    # ═══════════════════════════════════════════════════════════════════════════
    _fname_a = arg_str + "_FilaA"
    _col_prev, _col_act = st.columns([3, 2], gap="large")

    with _col_prev:
        _imgs_f = st.session_state.get("preview_images") or []
        if _imgs_f:
            _n_pg = len(_imgs_f)
            _pg_f = max(0, min(st.session_state.get("preview_page", 0), _n_pg - 1))
            st.image(_imgs_f[_pg_f], use_container_width=True)
            if _n_pg > 1:
                _pc, _pm, _pn = st.columns([1, 2, 1])
                with _pc:
                    if st.button("◀", key="final_prev_pg", use_container_width=True,
                                 disabled=(_pg_f == 0)):
                        st.session_state.preview_page = _pg_f - 1; st.rerun()
                with _pm:
                    st.markdown(
                        f'<div style="text-align:center;font-size:.78rem;font-weight:600;'
                        f'color:{T["text2"]};font-family:DM Sans,sans-serif;padding:.4rem 0;">'
                        f'Pagina {_pg_f+1} di {_n_pg}</div>',
                        unsafe_allow_html=True
                    )
                with _pn:
                    if st.button("▶", key="final_next_pg", use_container_width=True,
                                 disabled=(_pg_f == _n_pg - 1)):
                        st.session_state.preview_page = _pg_f + 1; st.rerun()
        elif vA.get("pdf"):
            _b64 = base64.b64encode(vA["pdf"]).decode()
            st.markdown(
                '<iframe src="data:application/pdf;base64,' + _b64 + '#toolbar=0&navpanes=0" '
                'style="width:100%;height:620px;border:none;border-radius:8px;"></iframe>',
                unsafe_allow_html=True
            )
        else:
            st.caption("Anteprima non disponibile.")

    with _col_act:
        if vA.get("pdf"):
            st.markdown('<div class="dl-cta-wrap">', unsafe_allow_html=True)
            st.download_button(
                label=f"⬇  Scarica PDF  ·  {_stima(vA['pdf'])}",
                data=vA["pdf"],
                file_name=_fname_a + ".pdf",
                mime="application/pdf",
                use_container_width=True,
                type="primary",
                key="dl_pdf_hero_A",
                help="Scarica il PDF della verifica, già formattato e pronto per la stampa.",
            )
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.warning("Il PDF non è ancora pronto. Apri «Modifica gli esercizi» e premi "
                       "«Conferma e genera PDF finale».")
        st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)
        if st.button("✏️ Modifica gli esercizi", key="final_edit", use_container_width=True,
                     help="Cambia, rendi più facile o più difficile, o elimina i singoli esercizi."):
            st.session_state.stage = STAGE_REVIEW
            st.rerun()
        st.markdown(
            f'<div style="font-size:.78rem;color:{T["muted"]};margin-top:.8rem;line-height:1.5;'
            f'font-family:DM Sans,sans-serif;">⚠️ Controlla sempre il contenuto prima di '
            f'distribuirlo agli studenti.</div>',
            unsafe_allow_html=True
        )

    _senza_grafico = esercizi_con_grafico_mancante(st.session_state.get("review_blocks", []))
    if _senza_grafico:
        st.warning(
            "Attenzione: l'esercizio " + ", ".join(str(i + 1) for i in _senza_grafico)
            + " cita un grafico che nel PDF non c'è. Apri «Modifica gli esercizi» e premi «Rigenera».",
            icon="📉",
        )

    # ═══════════════════════════════════════════════════════════════════════════
    #  ALTRE VERSIONI — Fila B, BES/DSA, soluzioni, griglia, Word
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown(
        f'<div class="variant-section-label">ALTRE VERSIONI DELLA VERIFICA</div>',
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
                _ph_b.empty()
                if _pdf_b_new:
                    st.toast("✅ Fila B pronta!", icon="⚡")
                else:
                    st.toast("Fila B creata, ma il PDF non è ancora pronto: premi «Crea PDF Fila B».", icon="⚠️")
                st.rerun()
            except Exception as _e:
                _ph_b.empty()
                _mostra_errore("Non sono riuscito a creare la Fila B", _e,
                               riprova_flag="_gen_fila_b", riprova_key="riprova_fila_b")

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
                _ph_r.empty()
                _mostra_errore("Non sono riuscito a creare la versione BES/DSA", _e,
                               riprova_flag="_gen_bes", riprova_key="riprova_bes")

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
                _ph_s.empty()
                _mostra_errore("Non sono riuscito a creare le soluzioni", _e,
                               riprova_flag="_gen_sol", riprova_key="riprova_sol")

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
                    _mostra_errore("Non sono riuscito a creare il file Word", _emsg,
                                   riprova_flag=_docx_key, riprova_key="riprova_word",
                                   consiglio="Riprova: la conversione a volte richiede un secondo tentativo.")
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
                _rph.empty()
                _mostra_errore("Non sono riuscito a creare la griglia di valutazione", _er,
                               riprova_flag="_rubrica_gen", riprova_key="riprova_griglia")

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
                    f"var u='{_share_full_url}';var b=document.getElementById('cpb');"
                    "if(navigator.clipboard&&navigator.clipboard.writeText){"
                    "navigator.clipboard.writeText(u).then(function(){"
                    "b.className='cb ok';b.innerText='✅ Copiato!';"
                    "setTimeout(function(){b.className='cb';b.innerText='📋 Copia link'},2500)"
                    "}).catch(function(){b.innerText=u})"
                    "}else{b.innerText=u}}</script>",
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

    # Word per le altre versioni (la Fila A ha già la sua card "Formato Word")
    _ha_extra = vB.get("latex") or vR.get("latex") or vRB.get("latex") or vS.get("latex")
    if _ha_extra:
        with st.expander("📝 Word delle altre versioni", expanded=False):
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
                            _mostra_errore("Non sono riuscito a creare il file Word", error_msg,
                                           riprova_flag=_docx_key, riprova_key="riprova_word_"+fid,
                                           consiglio="Riprova: la conversione a volte richiede un secondo tentativo.")
            _ef_c1, _ef_c2 = st.columns(2)
            with _ef_c1:
                if vR.get("latex"): _show_extra_formats("R", vR, "BES_FilaA")
            with _ef_c2:
                if vB.get("latex"): _show_extra_formats("B", vB, "FilaB")
                if vRB.get("latex"): _show_extra_formats("RB", vRB, "BES_FilaB")
                if vS.get("latex"): _show_extra_formats("S", vS, "Soluzioni")


    # Solo admin: sorgente LaTeX della Fila A, da copiare per diagnosticare grafici o impaginazione
    if _is_admin and vA.get("latex"):
        with st.expander("🔧 Strumenti admin — LaTeX sorgente (Fila A)", expanded=False):
            st.caption("Copia da qui il LaTeX se un grafico o l'impaginazione non vanno.")
            st.code(vA["latex"], language="latex")

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
    _nav_c1, _nav_c2, _nav_c3 = st.columns([1, 2, 1])
    with _nav_c2:
        if st.button("Genera nuova verifica", icon=":material/add:",
                     use_container_width=True, key="btn_new_s3_bottom"):
            st.session_state.stage            = STAGE_INPUT
            st.session_state["_prev_stage"]   = None
            st.session_state.input_percorso   = None
            _pulisci_stato_revisione()
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
            st.session_state.rubrica_testo         = None
            st.session_state["_rubrica_pdf"]       = None
            st.session_state["_rubrica_docx"]      = None
            st.session_state._rubrica_gen          = False
            st.session_state["_gen_fila_b"]       = False
            st.session_state["_gen_bes"]           = False
            st.session_state["_gen_sol"]           = False
            st.session_state.analisi_docs_list  = []
            st.session_state.info_consolidate   = {}
            st.session_state["_analisi_rifiuto"] = None
            st.session_state["_facsimile_mode"] = False
            st.session_state._share_code       = None
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
        st.session_state.stage == STAGE_INPUT
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
    if _current == STAGE_PREVIEW:   # sessioni aperte prima dell'unione di anteprima e download
        st.session_state.stage = _current = STAGE_FINAL
    if   _current == STAGE_INPUT:   _render_stage_input()
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
    "if(navigator.clipboard&&navigator.clipboard.writeText){"
    "navigator.clipboard.writeText(u).then(function(){"
    "b.innerText='✅ Link copiato!';setTimeout(function(){b.innerText='🔗 Condividi con i colleghi'},2000)"
    "}).catch(function(){b.innerText=u})"
    "}else{b.innerText=u}}"
    "</script>",
    height=30
)

