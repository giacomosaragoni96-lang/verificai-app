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
import re
import os
import time
import google.generativeai as genai

from sidebar import render_sidebar
from generation import genera_verifica, analizza_documento_caricato, compila_contesto_generazione
from prompts import (
    prompt_versione_b, prompt_versione_ridotta, prompt_soluzioni,
    prompt_modifica, prompt_qa_verifica,
    prompt_rubrica_valutazione, prompt_da_template, prompt_variante_rapida,
)
from docx_export import latex_to_docx_via_ai
from latex_utils import (
    compila_pdf, inietta_griglia, riscala_punti, riscala_punti_custom,
    fix_items_environment, rimuovi_vspace_corpo, pulisci_corpo_latex,
    rimuovi_punti_subsection, pdf_to_images_bytes,
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

# ── MATHPIX OCR (opzionale — degradazione graceful se non configurato) ────────
try:
    import mathpix_utils as _mpx
    _MATHPIX_AVAILABLE = True
except ImportError:
    _mpx = None
    _MATHPIX_AVAILABLE = False


# ── COSTANTI STAGE ────────────────────────────────────────────────────────────
STAGE_INPUT   = "INPUT"
STAGE_PREVIEW = "PREVIEW"   # ← NUOVO: anteprima rapida post-generazione
STAGE_REVIEW  = "REVIEW"
STAGE_FINAL   = "FINAL"

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
if "theme" not in st.session_state:
    st.session_state.theme = "chiaro"

_theme_key = st.session_state.theme
# Compatibilità con vecchie sessioni
if _theme_key not in THEMES:
    _theme_key = "chiaro"
    st.session_state.theme = _theme_key
T = THEMES[_theme_key]

# ── CONFIGURAZIONE API ────────────────────────────────────────────────────────
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    st.error("⚠️ Chiave API mancante! Crea un file .env con GOOGLE_API_KEY=...")
    st.stop()
genai.configure(api_key=API_KEY)

# ── AUTENTICAZIONE ────────────────────────────────────────────────────────────
if "utente" not in st.session_state:
    st.session_state.utente = None
if st.session_state.utente is None:
    ripristina_sessione(supabase)
    if st.session_state.utente is None:
        mostra_auth(supabase)
        st.stop()


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
    d = reset - now
    return d.days, d.seconds // 3600


def _stima(b):
    if not b: return "—"
    kb = len(b) / 1024
    return f"{kb:.0f} KB" if kb < 1024 else f"{kb/1024:.1f} MB"


def _vf():
    return {"latex": "", "pdf": None, "preview": False,
            "docx": None, "pdf_ts": None, "docx_ts": None, "latex_originale": ""}


# ── Block parsing ─────────────────────────────────────────────────────────────

def _extract_blocks(latex: str) -> tuple:
    parts = re.split(r"(?=\\subsection\*\{)", latex)
    if len(parts) <= 1:
        return latex, []
    preamble = parts[0]
    blocks = []
    for raw in parts[1:]:
        m = re.match(r"\\subsection\*\{([^}]*)\}(.*)", raw, re.DOTALL)
        if m:
            body = m.group(2)
            # Rimuovi \end{document}
            body = re.sub(r"\s*\\end\{document\}\s*$", "", body)
            # Rimuovi la griglia di valutazione (tabella finale) e tutto ciò che segue \vfill
            # La griglia è iniettata dopo \vfill % GRIGLIA o semplicemente dopo \vfill
            body = re.sub(r"\s*\\vfill.*$", "", body, flags=re.DOTALL)
            # Rimuovi anche eventuali \begin{tabular} residui (griglia senza \vfill)
            body = re.sub(r"\s*%\s*GRIGLIA.*$", "", body, flags=re.DOTALL)
            body = body.rstrip()
            blocks.append({"title": m.group(1), "body": body})
    return preamble, blocks


def _reconstruct_latex(preamble: str, blocks: list) -> str:
    r = preamble
    for b in blocks:
        r += f"\\subsection*{{{b['title']}}}\n{b['body']}\n\n"
    if "\\end{document}" not in r:
        r += "\n\\end{document}"
    return r


def _extract_corpo(latex: str) -> str:
    """Estrae solo il corpo esercizi (dopo \\end{center}) dal LaTeX completo."""
    m = re.search(r"\\end\{center\}(.*?)(?=\\end\{document\})", latex, re.DOTALL)
    return m.group(1).strip() if m else ""


def _extract_preambolo(latex: str) -> str:
    """Estrae il preambolo fino a \\end{center} incluso."""
    m = re.search(r"^(.*?\\end\{center\})", latex, re.DOTALL)
    return m.group(1) + "\n" if m else ""


# ── Score helpers ──────────────────────────────────────────────────────────────

def _parse_pts_from_block_body(body: str) -> int:
    """Somma tutti i (N pt) nel CORPO del blocco, escludendo il titolo."""
    return sum(int(p) for p in re.findall(r'\((\d+)\s*pt\)', body))


def _valida_totale(pts_list: list, target: int) -> tuple:
    """Ricalcola somma da zero, forza int. Restituisce (somma, ok, diff)."""
    somma = sum(int(p) for p in pts_list)
    return somma, (somma == target), (somma - target)


def _riscala_single_block(title: str, body: str, target_pts: int) -> str:
    """
    Applica riscala_punti_custom su un singolo blocco (titolo + corpo),
    preservando le proporzioni tra gli item e portando la somma a target_pts.
    Usato dopo ogni regen AI per ripristinare i punti corretti dell'esercizio.
    """
    if target_pts <= 0:
        return body
    mini = f"\\subsection*{{{title}}}\n{body}"
    fixed = riscala_punti_custom(mini, [target_pts])
    m = re.match(r'[^\n]*\n(.*)', fixed, re.DOTALL)
    return m.group(1) if m else body


# Parole chiave che indicano che l'utente sta chiedendo una modifica ai punteggi.
# In quel caso il prompt AI viene bloccato e viene mostrato un suggerimento
# a usare il pannello Ricalibra Punteggi.
_SCORE_KEYWORDS = {
    'pt', 'punt', 'punti', 'punteggio', 'punteggi', 'punto',
    'voto', 'voti', 'score', 'valut', 'peso', 'perc', '%',
    '5 pt', '10 pt', '15 pt', '20 pt', '25 pt', '30 pt',
}


# ── KaTeX HTML renderer ────────────────────────────────────────────────────────

def _make_katex_html(title: str, body: str, T: dict, height_hint: int = 400) -> str:
    t = body

    # 1. TikZ → placeholder
    t = re.sub(r"\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}",
               '<div class="graph-ph">📊 Grafico TikZ — visibile nel PDF finale</div>',
               t, flags=re.DOTALL)
    t = re.sub(r"\\begin\{axis\}.*?\\end\{axis\}", "", t, flags=re.DOTALL)
    t = re.sub(r"\\begin\{pgfpicture\}.*?\\end\{pgfpicture\}",
               '<div class="graph-ph">📊 Grafico pgf — visibile nel PDF finale</div>',
               t, flags=re.DOTALL)

    # 2. Display math \[...\] → $$...$$
    t = re.sub(r"\\\[(.*?)\\\]", r"$$\1$$", t, flags=re.DOTALL)
    t = re.sub(r"\\begin\{(align\*?|equation\*?|gather\*?|multline\*?)\}(.*?)\\end\{\1\}",
               r"$$\2$$", t, flags=re.DOTALL)

    # 3. Liste
    t = re.sub(r"\\begin\{enumerate\}(\[[^\]]*\])?\s*", "<ol>", t)
    t = re.sub(r"\\end\{enumerate\}", "</ol>", t)
    t = re.sub(r"\\begin\{itemize\}\s*", "<ul>", t)
    t = re.sub(r"\\end\{itemize\}", "</ul>", t)
    t = re.sub(r"\\item\[([^\]]+)\]\s*", r'<li><span class="lbl">\1</span>&ensp;', t)
    t = re.sub(r"\\item\s*", "<li>", t)

    # 4. Formattazione testo
    t = re.sub(r"\\textbf\{([^}]*)\}", r"<strong>\1</strong>", t)
    t = re.sub(r"\\textit\{([^}]*)\}", r"<em>\1</em>", t)
    t = re.sub(r"\\emph\{([^}]*)\}", r"<em>\1</em>", t)
    t = re.sub(r"\\underline\{([^}]*)\}", r"<u>\1</u>", t)

    # 5. Spazi e riempitivi
    t = re.sub(r"\\underline\{\\hspace\{[^}]*\}\}", '<span class="blank">___________</span>', t)
    t = re.sub(r"\\hspace\*?\{[^}]*\}", "&ensp;&ensp;", t)
    t = re.sub(r"\\vspace\*?\{[^}]*\}", "<br>", t)
    t = re.sub(r"\\\\", "<br>", t)
    t = re.sub(r"\\newline\b", "<br>", t)

    # 6. Comandi comuni
    t = re.sub(r"\\noindent\s*", "", t)
    t = re.sub(r"\\quad\b", "&emsp;", t)
    t = re.sub(r"\\qquad\b", "&emsp;&emsp;", t)
    t = re.sub(r"\\ldots\b|\\dots\b", "…", t)
    t = re.sub(r"\\newpage\b|\\clearpage\b", "<hr>", t)
    t = re.sub(r"\\medskip\b|\\bigskip\b", "<br>", t)
    t = re.sub(r"\\smallskip\b", "", t)

    # 7. Rimuovi \begin/\end non-math residui
    math_envs = r"(math|equation|align|gather|multline|pmatrix|bmatrix|vmatrix|cases)"
    t = re.sub(r"\\begin\{(?!" + math_envs + r")[^}]*\}", "", t)
    t = re.sub(r"\\end\{(?!" + math_envs + r")[^}]*\}", "", t)

    # 8. Comandi LaTeX generici con argomento
    t = re.sub(r"\\(?:small|large|Large|huge|Huge|normalsize|centering)\b", "", t)
    t = re.sub(r"\\[a-zA-Z]+\*?\{([^}$]{0,80})\}", r"\1", t)

    # 9. Paragrafi
    t = re.sub(r"\n\n+", "</p><p>", t)
    t = t.replace("\n", " ")
    t = re.sub(r"\s{3,}", " ", t)

    safe_title = html_lib.escape(title)
    bg       = T["bg2"]
    card     = T.get("card2", T["bg2"])
    fg       = T["text"]
    fg2      = T["text2"]
    acc      = T["accent"]
    bdr      = T["border"]
    muted    = T["muted"]

    katex_css  = "https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css"
    katex_js   = "https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"
    render_js  = "https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"

    html_out = (
        "<!DOCTYPE html><html><head><meta charset='UTF-8'>"
        "<link rel='stylesheet' href='" + katex_css + "'>"
        "<script src='" + katex_js + "'></script>"
        "<script src='" + render_js + "'></script>"
        "<style>"
        "*{box-sizing:border-box;margin:0;padding:0}"
        "body{font-family:-apple-system,DM Sans,sans-serif;background:" + bg + ";"
        "color:" + fg + ";font-size:15px;line-height:1.75;padding:4px 0 12px 0}"
        ".t{font-size:.95rem;font-weight:800;color:" + acc + ";padding:8px 14px;"
        "background:" + card + ";border-left:3px solid " + acc + ";"
        "margin-bottom:10px;border-radius:0 6px 6px 0}"
        ".b{padding:2px 10px}"
        "ol,ul{padding-left:1.5em;margin:6px 0}"
        "li{margin:5px 0}"
        ".lbl{font-weight:700;color:" + acc + "}"
        ".blank{display:inline-block;border-bottom:1.5px solid " + fg2 + ";"
        "min-width:110px;margin:0 3px}"
        ".graph-ph{background:" + card + ";border:1.5px dashed " + bdr + ";"
        "border-radius:8px;padding:14px;text-align:center;color:" + muted + ";"
        "font-size:.85rem;margin:10px 0}"
        "p{margin:5px 0}"
        "strong{color:" + fg + "}"
        ".katex-display{overflow-x:auto;padding:6px 0}"
        "hr{border:none;border-top:1px solid " + bdr + ";margin:10px 0}"
        "</style></head><body>"
        "<div class='t'>" + safe_title + "</div>"
        "<div class='b'><p>" + t + "</p></div>"
        "<script>"
        "window.addEventListener('load',function(){"
        "renderMathInElement(document.body,{"
        "delimiters:["
        "{left:'$$',right:'$$',display:true},"
        "{left:'$',right:'$',display:false}"
        "],"
        "throwOnError:false"
        "});"
        "});"
        "</script>"
        "</body></html>"
    )
    return html_out


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
    corpo_a    = _extract_corpo(latex_a)
    preamb_a   = _extract_preambolo(latex_a)

    def _post(corpo: str) -> str:
        corpo = fix_items_environment(corpo)
        corpo = rimuovi_vspace_corpo(corpo)
        if mostra_punteggi:
            corpo = rimuovi_punti_subsection(corpo)
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
        resp   = model_v.generate_content(prompt_versione_b(corpo_a))
        corpo  = pulisci_corpo_latex(resp.text.replace("```latex","").replace("```","").strip())
        corpo  = _post(corpo)
        preamb = preamb_a.replace("Versione A", "Versione B")
        if "Versione B" not in preamb:
            preamb = re.sub(r"(Verifica[^\\]*?)(\\\\)", r"\1 — Versione B\2", preamb, count=1)
        latex, pdf = _compile(preamb + "\n" + corpo)
        return {**_vf(), "latex": latex, "pdf": pdf, "preview": bool(pdf),
                "latex_originale": latex}

    if tipo == "R":
        resp  = model_v.generate_content(
            prompt_versione_ridotta(corpo_a, materia, perc_ridotta,
                                    mostra_punteggi, punti_totali))
        corpo = pulisci_corpo_latex(resp.text.replace("```latex","").replace("```","").strip())
        corpo = _post(corpo)
        latex, pdf = _compile(preamb_a + "\n" + corpo)
        return {**_vf(), "latex": latex, "pdf": pdf, "preview": bool(pdf),
                "latex_originale": latex}

    if tipo == "S":
        resp     = model_v.generate_content(prompt_soluzioni(corpo_a, materia))
        testo    = resp.text.strip()
        titolo_s = "Soluzioni — " + materia + ": " + argomento
        latex_s  = (
            "\\documentclass[11pt,a4paper]{article}\n"
            "\\usepackage[utf8]{inputenc}\n"
            "\\usepackage[italian]{babel}\n"
            "\\usepackage{amsmath,amsfonts,amssymb,geometry}\n"
            "\\geometry{margin=2cm}\n"
            "\\pagestyle{empty}\n"
            "\\begin{document}\n"
            "\\begin{center}\n"
            "  \\textbf{\\large " + titolo_s + "} \\\\\n"
            "  {\\small \\textit{Documento riservato al docente}}\n"
            "\\end{center}\n"
            "\\vspace{0.4cm}\n"
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
            f"Assegna i punti a ogni singolo \\item o sottopunto in modo che la somma sia\n"
            f"ESATTAMENTE {punti_totali} pt. Non aggiungere, non togliere nemmeno 1 pt.\n"
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
if "_facsimile_mode"      not in st.session_state: st.session_state["_facsimile_mode"] = False

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

# ── CSS + FEEDBACK ────────────────────────────────────────────────────────────
st.markdown(get_css(T), unsafe_allow_html=True)
st.markdown(
    '<a class="fab-link" href="' + FEEDBACK_FORM_URL + '" target="_blank" '
    'rel="noopener noreferrer">💬 Feedback</a>',
    unsafe_allow_html=True
)

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
settings   = render_sidebar(
    supabase_admin=supabase_admin, utente=st.session_state.utente,
    verifiche_mese_count=_verifiche_mese, is_admin=_is_admin,
    limite_raggiunto=_limite, T=T, SCUOLE=SCUOLE,
    MODELLI_DISPONIBILI=MODELLI_DISPONIBILI, LIMITE_MENSILE=LIMITE_MENSILE,
    giorni_al_reset_func=_giorni_al_reset, compila_pdf_func=compila_pdf,
    supabase_client=supabase, current_stage=st.session_state.stage,
    THEMES=THEMES, THEME_LABELS=THEME_LABELS,
    extract_blocks_func=_extract_blocks,
    pdf_to_images_func=pdf_to_images_bytes,
)
modello_id = settings.get("modello_id", "gemini-2.5-flash-lite")

# Se il tema è cambiato dalla sidebar, aggiorna T
if settings.get("theme_changed"):
    T = THEMES[st.session_state.theme]
    st.rerun()

# ── HINT SIDEBAR MINIMALE (top-left, fuori dal flusso) ───────────────────────
st.markdown(
    '<div class="sidebar-hint-inline">'
    '☰ Impostazioni, storico e logout'
    '</div>',
    unsafe_allow_html=True
)
st.markdown(
    '<div class="hero-wrap"><div class="hero-left">'
    '<h1 class="hero-title"><span class="hero-icon">' + APP_ICON + '</span>'
    ' Verific<span class="hero-ai">AI</span></h1>'
    '<p class="hero-sub">' + APP_TAGLINE + '</p>'
    '<span class="hero-beta">Versione Beta</span>'
    '</div></div>',
    unsafe_allow_html=True
)


# ═══════════════════════════════════════════════════════════════════════════════
#  BREADCRUMB
# ═══════════════════════════════════════════════════════════════════════════════

def _render_breadcrumb():
    stage = st.session_state.stage
    steps = [
        ("01", "Configura",  STAGE_INPUT),
        ("02", "Anteprima",  STAGE_PREVIEW),
        ("03", "Revisione",  STAGE_REVIEW),
        ("04", "Download",   STAGE_FINAL),
    ]
    completed = {
        STAGE_INPUT:   stage in (STAGE_PREVIEW, STAGE_REVIEW, STAGE_FINAL),
        STAGE_PREVIEW: stage in (STAGE_REVIEW, STAGE_FINAL),
        STAGE_REVIEW:  stage == STAGE_FINAL,
        STAGE_FINAL:   False,
    }
    # Contenitore centrato e compatto
    html = (
        '<div style="display:flex;justify-content:center;margin-bottom:1.6rem;">'
        '<div style="display:inline-flex;align-items:center;gap:10px;'
        'padding:.7rem 1.6rem;'
        'background:' + T["card"] + ';border:1.5px solid ' + T["border"] + ';'
        'border-radius:100px;box-shadow:' + T["shadow_md"] + ';">'
    )
    for i, (num, label, s) in enumerate(steps):
        is_active = s == stage
        is_done   = completed[s]
        if is_active:
            cb, cc, lc, lw = T["accent"], "#fff", T["accent"], "800"
            icon = num
        elif is_done:
            cb, cc, lc, lw = T["success"], "#fff", T["success"], "700"
            icon = "✓"
        else:
            cb, cc, lc, lw = T["border2"], T["muted"], T["muted"], "500"
            icon = num
        _op = "1" if (is_active or is_done) else ".4"
        html += (
            '<div style="display:flex;align-items:center;gap:7px;opacity:' + _op + ';">'
            '<div style="background:' + cb + ';border-radius:50%;'
            'width:28px;height:28px;display:flex;align-items:center;'
            'justify-content:center;font-size:.72rem;font-weight:800;'
            'color:' + cc + ';flex-shrink:0;box-shadow:0 2px 8px ' + cb + '44;">' + icon + '</div>'
            '<span style="font-size:.88rem;font-weight:' + lw + ';color:' + lc + ';'
            'font-family:DM Sans,sans-serif;white-space:nowrap;letter-spacing:-.01em;">' + label + '</span>'
            '</div>'
        )
        if i < 2:
            _sep_c = T["success"] if is_done else T["border2"]
            html += (
                '<div style="width:28px;height:1.5px;background:' + _sep_c + ';'
                'opacity:.4;flex-shrink:0;border-radius:2px;"></div>'
            )
    html += "</div></div>"
    st.markdown(html, unsafe_allow_html=True)


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
    except Exception:
        pass
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
    st.markdown(
        f'<div style="text-align:center;">'
        f'<span style="font-size:.72rem;color:{T["muted"]};font-family:DM Sans,sans-serif;">'
        f'Vuoi creare una verifica invece di analizzarla?'
        f'</span></div>',
        unsafe_allow_html=True
    )
    _qa_back_c1, _qa_back_c2, _qa_back_c3 = st.columns([3, 2, 3])
    with _qa_back_c2:
        if st.button("← Torna al menu", key="btn_back_qa",
                     use_container_width=True):
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
                "analisi":    result,
                "file_mode":  result.get("modalita_uso_consigliata", "stile_e_struttura"),
                "confirmed":  False,   # attende conferma modalità
            })
        # Retrocompatibilità: slot singolo usato da compila_contesto_generazione
        st.session_state.analisi_doc = result
        _consolida_info()
        st.rerun()
    except Exception as e:
        st.warning(f"⚠️ Analisi non riuscita: {e}. Compila i campi manualmente.", icon="🔬")


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
    Landing page: scelta tra Percorso A (Ho materiale), Percorso B (Parti da zero),
    e Facsimile Istantaneo (carica verifica → genera bozza variante).
    I box descrizione SONO i pulsanti (via CSS overlay).
    """
    st.markdown(
        f'<div style="text-align:center;padding:.8rem 0 1rem;">'
        f'<div style="font-size:1.1rem;font-weight:900;color:{T["text"]};'
        f'font-family:DM Sans,sans-serif;letter-spacing:-.02em;margin-bottom:.3rem;">'
        f'Come vuoi creare la verifica?'
        f'</div>'
        f'<div style="font-size:.8rem;color:{T["muted"]};font-family:DM Sans,sans-serif;">'
        f'Scegli il percorso più adatto a te'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    # CSS per card-button gigante con hover
    st.markdown(
        f"""
        <style>
        .bivio-btn-wrap {{position:relative;}}
        .bivio-btn-wrap button[kind="primary"],
        .bivio-btn-wrap button[kind="secondary"] {{
            position:absolute!important;inset:0!important;
            width:100%!important;height:100%!important;
            opacity:0!important;cursor:pointer!important;
            z-index:10!important;
        }}
        .bivio-card {{
            background:{T["card"]};
            border:2px solid {T["border2"]};
            border-radius:20px;
            padding:1.8rem 1.5rem 1.5rem;
            min-height:260px;
            display:flex;flex-direction:column;gap:.6rem;
            cursor:pointer;
            transition:transform .18s ease, box-shadow .18s ease, border-color .18s ease;
            position:relative;
        }}
        .bivio-card:hover {{
            transform:scale(1.035);
            box-shadow:0 12px 40px {T["accent"]}33;
            border-color:{T["accent"]}88;
        }}
        .bivio-card.primary {{
            background:linear-gradient(145deg,{T["accent_light"]} 0%,{T["card"]} 60%);
            border-color:{T["accent"]};
            box-shadow:0 4px 24px {T["accent"]}22;
        }}
        .bivio-card.primary:hover {{
            transform:scale(1.04);
            box-shadow:0 16px 48px {T["accent"]}44;
        }}
        .bivio-badge {{
            position:absolute;top:-.8rem;left:1.1rem;
            background:{T["accent"]};color:#fff;
            font-size:.62rem;font-weight:800;
            padding:3px 10px;border-radius:100px;
            font-family:DM Sans,sans-serif;letter-spacing:.04em;
        }}
        .bivio-chip {{
            font-size:.65rem;background:{T["card2"]};
            border-radius:5px;padding:2px 8px;color:{T["text2"]};
            display:inline-block;margin:1px;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

    col_a, col_b = st.columns(2, gap="medium")

    # ── Percorso A ────────────────────────────────────────────────────────────
    with col_a:
        st.markdown(
            f'<div class="bivio-card primary">'
            f'<div class="bivio-badge">✦ CONSIGLIATO</div>'
            f'<div style="font-size:2.4rem;margin-bottom:.1rem;">📂</div>'
            f'<div style="font-size:1.05rem;font-weight:900;color:{T["accent"]};'
            f'font-family:DM Sans,sans-serif;line-height:1.2;">'
            f'Carica il tuo materiale'
            f'</div>'
            f'<div style="font-size:.8rem;color:{T["text2"]};font-family:DM Sans,sans-serif;'
            f'line-height:1.6;flex:1;">'
            f'Hai una verifica precedente, appunti o un capitolo del libro?'
            f'<br><br>'
            f'<span style="color:{T["accent"]};font-weight:700;">'
            f'L\'AI legge il materiale</span> e genera automaticamente una nuova verifica '
            f'nello stesso stile, sullo stesso argomento — o su uno nuovo.'
            f'</div>'
            f'<div style="display:flex;flex-wrap:wrap;gap:.3rem;margin-top:.3rem;">'
            f'<span class="bivio-chip">📝 Verifiche</span>'
            f'<span class="bivio-chip">📒 Appunti</span>'
            f'<span class="bivio-chip">📚 Libri</span>'
            f'<span class="bivio-chip">📷 Foto lavagna</span>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True
        )
        if st.button(
            "📂  Ho materiale da caricare →",
            key="btn_percorso_a",
            use_container_width=True,
            type="primary",
        ):
            st.session_state.input_percorso = "A"
            st.session_state["_analisi_rifiuto"] = None
            st.rerun()

    # ── Percorso B ────────────────────────────────────────────────────────────
    with col_b:
        st.markdown(
            f'<div class="bivio-card">'
            f'<div style="font-size:2.4rem;margin-bottom:.1rem;">✍️</div>'
            f'<div style="font-size:1.05rem;font-weight:900;color:{T["text"]};'
            f'font-family:DM Sans,sans-serif;line-height:1.2;">'
            f'Configurazione manuale'
            f'</div>'
            f'<div style="font-size:.8rem;color:{T["text2"]};font-family:DM Sans,sans-serif;'
            f'line-height:1.6;flex:1;">'
            f'Compila tu stesso materia, livello e argomento.'
            f'<br><br>'
            f'Controllo totale su struttura, punteggi e tipi di esercizi — '
            f'<span style="font-weight:700;color:{T["text"]};">nessun upload richiesto.</span>'
            f'</div>'
            f'<div style="display:flex;flex-wrap:wrap;gap:.3rem;margin-top:.3rem;">'
            f'<span class="bivio-chip">⚙️ Configurazione libera</span>'
            f'<span class="bivio-chip">🎯 Struttura custom</span>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True
        )
        if st.button(
            "✍️  Configura manualmente →",
            key="btn_percorso_b",
            use_container_width=True,
        ):
            st.session_state.input_percorso = "B"
            st.rerun()

    # ── Facsimile Istantaneo ─────────────────────────────────────────────────
    st.markdown("<div style='height:.9rem'></div>", unsafe_allow_html=True)
    st.markdown(
        f'<div style="text-align:center;font-size:.75rem;font-weight:700;'
        f'color:{T["muted"]};font-family:DM Sans,sans-serif;margin-bottom:.5rem;">'
        f'oppure'
        f'</div>',
        unsafe_allow_html=True
    )

    col_fac1, col_fac2, col_fac3 = st.columns([1, 4, 1])
    with col_fac2:
        st.markdown(
            f'<div class="bivio-card" style="min-height:auto;padding:1.3rem 1.5rem;'
            f'border:2px dashed {T["border2"]};border-radius:16px;'
            f'background:linear-gradient(135deg,{T["card2"]} 0%,{T["card"]} 100%);">'
            f'<div style="display:flex;align-items:center;gap:1rem;">'
            f'<div style="font-size:2rem;flex-shrink:0;">⚡</div>'
            f'<div style="flex:1;">'
            f'<div style="font-size:.95rem;font-weight:900;color:{T["text"]};'
            f'font-family:DM Sans,sans-serif;margin-bottom:.25rem;">'
            f'Crea Facsimile Istantaneo'
            f'</div>'
            f'<div style="font-size:.77rem;color:{T["text2"]};font-family:DM Sans,sans-serif;line-height:1.5;">'
            f'Carica una verifica esistente → l\'AI genera subito una variante con dati diversi, '
            f'pronta per la revisione. <span style="color:{T["accent"]};font-weight:700;">Zero configurazione.</span>'
            f'</div>'
            f'</div>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True
        )
        if st.button(
            "⚡ Crea Facsimile da verifica esistente →",
            key="btn_facsimile_home",
            use_container_width=True,
        ):
            st.session_state.input_percorso = "A"
            st.session_state["_analisi_rifiuto"] = None
            st.session_state["_facsimile_mode"] = True
            st.rerun()


def _render_percorso_a_upload():
    """
    Percorso A — pagina unica multi-file.
    """
    # lista e info usati in tutta la funzione
    lista: list = st.session_state.analisi_docs_list
    info   = st.session_state.info_consolidate

    # ── Facsimile mode banner ─────────────────────────────────────────────────
    _is_facsimile_mode = st.session_state.get("_facsimile_mode", False)
    if _is_facsimile_mode:
        st.markdown(
            f'<div style="background:linear-gradient(135deg,{T["accent_light"]},{T["card"]});'
            f'border:2px solid {T["accent"]};border-radius:14px;'
            f'padding:.75rem 1rem;margin-bottom:.75rem;'
            f'display:flex;align-items:center;gap:.8rem;">'
            f'<span style="font-size:1.4rem;">⚡</span>'
            f'<div>'
            f'<div style="font-size:.88rem;font-weight:900;color:{T["accent"]};'
            f'font-family:DM Sans,sans-serif;margin-bottom:.1rem;">Modalità Facsimile Istantaneo</div>'
            f'<div style="font-size:.74rem;color:{T["text2"]};font-family:DM Sans,sans-serif;line-height:1.4;">'
            f'Carica la verifica da cui vuoi creare una variante. L\'AI genererà automaticamente '
            f'un facsimile con dati diversi, pronto per la revisione.'
            f'</div>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    # ─────────────────────────────────────────────────────────────────────────
    # SEZIONE 0 — Banner onboarding con OCR hint (mostrato solo se lista vuota)
    # ─────────────────────────────────────────────────────────────────────────
    _is_light_theme = _is_light_color(T["bg"])
    if not lista:
        # Banner OCR con hint prominente
        st.markdown(
            f'<div class="ocr-hint-banner">'
            f'<div class="ocr-hint-icon">✍️</div>'
            f'<div class="ocr-hint-body">'
            f'<div class="ocr-hint-title">Carica qualsiasi materiale — anche a mano!</div>'
            f'<div class="ocr-hint-desc">'
            f'Il sistema è <strong>estremamente performante</strong> nel riconoscere la scrittura manuale: '
            f'basta una foto del foglio. Funziona anche con schemi, appunti, fotocopie o pagine di libro.'
            f'</div>'
            f'<div class="ocr-hint-tags">'
            f'<span class="ocr-hint-tag">✍️ Scrittura a mano</span>'
            f'<span class="ocr-hint-tag">📸 Foto lavagna</span>'
            f'<span class="ocr-hint-tag">📄 Fotocopie</span>'
            f'<span class="ocr-hint-tag">📚 Libro di testo</span>'
            f'<span class="ocr-hint-tag">🖨️ PDF stampati</span>'
            f'</div>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True
        )
        # Mini-guida in 3 passi (compatta)
        st.markdown(
            f'<div style="background:{T["bg2"]};border:1px solid {T["border"]};'
            f'border-radius:10px;padding:.55rem .9rem;margin-bottom:.5rem;">'
            f'<div style="display:flex;align-items:center;flex-wrap:wrap;gap:6px 16px;">'
            f'<div style="display:flex;align-items:center;gap:5px;">'
            f'<span style="font-size:.7rem;font-weight:800;color:{T["accent"]};">1.</span>'
            f'<span style="font-size:.7rem;color:{T["text2"]};">Carica il materiale</span>'
            f'</div>'
            f'<span style="font-size:.62rem;color:{T["border2"]};">→</span>'
            f'<div style="display:flex;align-items:center;gap:5px;">'
            f'<span style="font-size:.7rem;font-weight:800;color:{T["accent"]};">2.</span>'
            f'<span style="font-size:.7rem;color:{T["text2"]};">L\'AI analizza e classifica</span>'
            f'</div>'
            f'<span style="font-size:.62rem;color:{T["border2"]};">→</span>'
            f'<div style="display:flex;align-items:center;gap:5px;">'
            f'<span style="font-size:.7rem;font-weight:800;color:{T["accent"]};">3.</span>'
            f'<span style="font-size:.7rem;color:{T["text2"]};">Genera e scarica il PDF</span>'
            f'</div>'
            f'</div></div>',
            unsafe_allow_html=True
        )

    # ─────────────────────────────────────────────────────────────────────────
    # BANNER RIFIUTO (guardrail)
    # ─────────────────────────────────────────────────────────────────────────
    _rifiuto = st.session_state.get("_analisi_rifiuto")
    if _rifiuto:
        st.markdown(
            f'<div style="background:linear-gradient(135deg,#3B0000,#1C0000);'
            f'border:2px solid #FF453A;border-radius:14px;'
            f'padding:.9rem 1.1rem;margin-bottom:.8rem;'
            f'display:flex;align-items:flex-start;gap:.8rem;">'
            f'<div>'
            f'<div style="font-size:.85rem;font-weight:800;color:#FF453A;'
            f'font-family:DM Sans,sans-serif;margin-bottom:.2rem;">'
            f'File non riconosciuto come materiale scolastico</div>'
            f'<div style="font-size:.75rem;color:#FFBBB8;font-family:DM Sans,sans-serif;line-height:1.5;">'
            f'{_rifiuto.get("messaggio", "Carica una verifica, appunti, capitoli del libro o la foto di un esercizio.")}'
            f'</div>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True
        )
        if st.button("Chiudi avviso", key="btn_chiudi_rifiuto"):
            st.session_state["_analisi_rifiuto"] = None
            st.rerun()

    # ─────────────────────────────────────────────────────────────────────────
    # SEZIONE 1 — Area Upload
    # ─────────────────────────────────────────────────────────────────────────
    _n_file = len(lista)
    _is_light_theme = _is_light_color(T["bg"])
    if _n_file > 0:
        st.markdown(
            f'<div style="font-size:.75rem;color:{T["muted"]};font-family:DM Sans,sans-serif;'
            f'margin-bottom:.3rem;">{_n_file} file caricato/i — aggiungi altro o prosegui</div>',
            unsafe_allow_html=True
        )

    # Uploader
    _upload_key = f"file_up_{len(lista)}"
    file_doc = st.file_uploader(
        "Carica documento",
        type=["pdf", "png", "jpg", "jpeg"],
        key=_upload_key,
        label_visibility="collapsed",
    )

    # Avvia analisi se file nuovo
    _new_bytes: bytes | None = None
    _new_mime  = "image/png"
    _new_name  = ""
    if file_doc:
        _new_bytes = file_doc.getvalue()
        _new_mime  = file_doc.type or "image/png"
        _new_name  = file_doc.name
        st.session_state.file_ispirazione = file_doc

    if _new_bytes is not None:
        _hash_new = hash(_new_bytes)
        _hashes_esistenti = {d["file_hash"] for d in lista}
        if _hash_new not in _hashes_esistenti:
            # ── IDEA #11: Skeleton OCR animato ────────────────────────────────
            _ocr_placeholder = st.empty()
            _ocr_placeholder.markdown(
                f'<div class="ocr-skeleton-wrap">'
                f'  <div class="ocr-skeleton-header">'
                f'    <div class="ocr-skeleton-icon">🔬</div>'
                f'    <div>'
                f'      <div class="ocr-skeleton-title">Analisi AI in corso…</div>'
                f'      <div class="ocr-skeleton-sub">'
                f'        Lettura documento · Riconoscimento scrittura · Classificazione'
                f'      </div>'
                f'    </div>'
                f'  </div>'
                f'  <div class="ocr-skeleton-doc">'
                f'    <div class="ocr-skeleton-scan"></div>'
                f'    <div class="ocr-skeleton-line" style="width:88%;animation-delay:.0s"></div>'
                f'    <div class="ocr-skeleton-line" style="width:72%;animation-delay:.15s"></div>'
                f'    <div class="ocr-skeleton-line" style="width:95%;animation-delay:.3s"></div>'
                f'    <div class="ocr-skeleton-line" style="width:61%;animation-delay:.45s"></div>'
                f'    <div class="ocr-skeleton-line" style="width:83%;animation-delay:.6s"></div>'
                f'  </div>'
                f'  <div class="ocr-skeleton-step" style="animation-delay:.2s">'
                f'    <div class="ocr-skeleton-dot"></div>'
                f'    Estrazione testo e formule (OCR)…'
                f'  </div>'
                f'</div>',
                unsafe_allow_html=True
            )
            _esegui_analisi_documento(_new_bytes, _new_mime, _new_name)
            _ocr_placeholder.empty()

    # ─────────────────────────────────────────────────────────────────────────
    # SEZIONE 2 — Lista file caricati
    # ─────────────────────────────────────────────────────────────────────────
    # Etichette per le opzioni del dropdown (per verifica e esercizi)
    # Etichette per le opzioni del dropdown — 3 opzioni senza "consigliato"
    _OPZIONI_LABEL = {
        "stile_e_struttura":    "Copia Stile/Parametri — stesso formato, argomento diverso",
        "copia_fedele":         "Crea Facsimile — stesso schema, dati diversi",
        "base_conoscenza":      "Usa come fonte di concetti",
        "includi_esercizio":    "Estrai Esercizi Singoli — includi nella verifica",
        "esercizio_simile":     "Estrai Esercizi Singoli — crea versione con dati diversi",
    }
    # Etichette brevi per la pill (dopo conferma)
    _OPZIONI_LABEL_BREVE = {
        "stile_e_struttura":    "Copia Stile",
        "copia_fedele":         "Facsimile",
        "base_conoscenza":      "Fonte concetti",
        "includi_esercizio":    "Estrai esercizi",
        "esercizio_simile":     "Estrai esercizi",
    }
    # Tipi che NON mostrano il dropdown — auto-assegnati
    _TIPI_AUTO = {"appunti", "libro", "misto"}
    # Opzioni per tipo (solo per tipi che mostrano il dropdown) — NO "consigliato"
    _OPZIONI_PER_TIPO = {
        "verifica":         ["copia_fedele", "stile_e_struttura"],
        "esercizi_sciolti": ["stile_e_struttura", "includi_esercizio", "base_conoscenza"],
        "esercizio_singolo":["includi_esercizio", "esercizio_simile"],
    }
    # Badge icona per tipo documento
    _TIPO_EMOJI = {
        "verifica":          "verifica",
        "appunti":           "appunti",
        "libro":             "libro",
        "esercizi_sciolti":  "esercizi",
        "esercizio_singolo": "esercizio",
        "misto":             "documento",
    }
    # Badge colore CSS class per tipo (light/dark-aware)
    _TIPO_BADGE_CLASS = {
        "verifica":          "doc-type-verifica",
        "appunti":           "doc-type-appunti",
        "libro":             "doc-type-libro",
        "esercizi_sciolti":  "doc-type-esercizi",
        "esercizio_singolo": "doc-type-esercizi",
        "misto":             "doc-type-misto",
    }

    _da_rimuovere = []

    for _i, entry in enumerate(lista):
        a          = entry["analisi"]
        confermato = entry["confirmed"]
        fname      = entry["file_name"]
        fmode      = entry["file_mode"]
        fhash      = entry["file_hash"]
        tipo_doc   = a.get("tipo_documento", "altro")
        arg_f      = a.get("contenuto_argomento") or ""
        scuola_f   = a.get("scuola") or ""
        materia_f  = a.get("materia") or ""
        msg_pro    = a.get("messaggio_proattivo") or ""
        _tipo_label = _TIPO_EMOJI.get(tipo_doc, "documento")
        _mode_label = _OPZIONI_LABEL.get(fmode, fmode)
        _modalita_ai = a.get("modalita_uso_consigliata", "stile_e_struttura")
        _e_tipo_auto = tipo_doc in _TIPI_AUTO

        if confermato:
            # ── Pill compatta: file confermato — con label utilizzo, senza X ingombrante ──
            _mode_breve = _OPZIONI_LABEL_BREVE.get(fmode, fmode)
            # classificazione badge colore
            _badge_class = _TIPO_BADGE_CLASS.get(tipo_doc, "doc-type-misto")
            # Classificazione intelligente: badge speciale per verifica vs esercizi
            _classif_badge = ""
            if tipo_doc == "verifica":
                _classif_badge = (
                    f'<span class="classif-verifica">📋 Verifica</span>'
                )
            elif tipo_doc in ("esercizi_sciolti", "esercizio_singolo"):
                _n_es = len(a.get("esercizi_trovati") or [])
                _es_label = f"{_n_es} esercizi rilevati" if _n_es > 1 else (f"{_n_es} esercizio rilevato" if _n_es == 1 else "Esercizi")
                _classif_badge = (
                    f'<span class="classif-esercizi">📝 {_es_label}</span>'
                )
            st.markdown(
                f'<div style="background:{T["card"]};border:1px solid {T["border"]};'
                f'border-radius:10px;padding:.5rem .85rem;'
                f'display:flex;align-items:center;gap:.5rem;flex-wrap:wrap;">'
                f'<span style="font-size:.75rem;font-weight:700;color:{T["text"]};'
                f'font-family:DM Sans,sans-serif;max-width:180px;overflow:hidden;'
                f'text-overflow:ellipsis;white-space:nowrap;">{fname}</span>'
                f'{_classif_badge}'
                f'<span style="font-size:.62rem;background:{T["hint_bg"]};color:{T["hint_text"]};'
                f'border:1px solid {T["hint_border"]};'
                f'border-radius:5px;padding:2px 8px;font-weight:600;white-space:nowrap;">'
                f'{_mode_breve}</span>'
                + (f'<span style="font-size:.62rem;color:{T["muted"]};margin-left:auto;'
                   f'max-width:120px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">'
                   f'{(arg_f[:30]+"…") if len(arg_f)>30 else arg_f}</span>' if arg_f else "") +
                f'</div>',
                unsafe_allow_html=True
            )

        else:
            # ── Card espansa: messaggio AI + scelta utilizzo ──────────────────
            _card_parts = []
            _card_parts.append(
                f'<div style="background:{T["card"]};border:2px solid {T["accent"]}44;'
                f'border-radius:14px;padding:.75rem 1rem;margin-bottom:.3rem;">'
            )
            # Header file con tipo badge
            _card_parts.append(
                f'<div style="display:flex;align-items:center;gap:.5rem;margin-bottom:.5rem;">'
                f'<span style="font-size:.8rem;font-weight:700;color:{T["text"]};'
                f'font-family:DM Sans,sans-serif;">{fname}</span>'
                f'<span style="font-size:.62rem;background:{T["accent_light"]};color:{T["accent"]};'
                f'border-radius:4px;padding:1px 6px;font-weight:700;margin-left:auto;">'
                f'{_tipo_label}</span>'
                f'</div>'
            )
            # Chips info rilevate (senza emoji nei testi)
            _chips_html = ""
            if materia_f:
                _chips_html += (
                    f'<span style="font-size:.67rem;background:{T["card2"]};border-radius:5px;'
                    f'padding:2px 7px;color:{T["text2"]};">{materia_f}</span>'
                )
            if scuola_f:
                _chips_html += (
                    f'<span style="font-size:.67rem;background:{T["card2"]};border-radius:5px;'
                    f'padding:2px 7px;color:{T["text2"]};">{scuola_f}</span>'
                )
            if arg_f:
                _arg_short = (arg_f[:45] + "…") if len(arg_f) > 45 else arg_f
                _chips_html += (
                    f'<span style="font-size:.67rem;background:{T["card2"]};border-radius:5px;'
                    f'padding:2px 7px;color:{T["text2"]};">{_arg_short}</span>'
                )
            if _chips_html:
                _card_parts.append(
                    f'<div style="display:flex;flex-wrap:wrap;gap:.3rem;margin-bottom:.5rem;">'
                    + _chips_html +
                    f'</div>'
                )
            # Messaggio proattivo AI (senza emoji)
            if msg_pro:
                _card_parts.append(
                    f'<div style="background:linear-gradient(135deg,{T["hint_bg"]},{T["card"]});'
                    f'border:1px solid {T["hint_border"]};border-radius:9px;'
                    f'padding:.5rem .75rem;margin-bottom:.5rem;">'
                    f'<span style="font-size:.77rem;color:{T["hint_text"]};'
                    f'font-family:DM Sans,sans-serif;line-height:1.5;">'
                    f'{msg_pro}</span>'
                    f'</div>'
                )
            _card_parts.append("</div>")
            st.markdown("".join(_card_parts), unsafe_allow_html=True)

            # ── Scelta utilizzo: CONDIZIONALE sul tipo documento ──────────────
            if _e_tipo_auto:
                # Appunti / Libro / Misto → nessun dropdown, auto "base_conoscenza"
                if fmode != "base_conoscenza":
                    st.session_state.analisi_docs_list[_i]["file_mode"] = "base_conoscenza"
                _new_mode = "base_conoscenza"
                st.markdown(
                    f'<div style="font-size:.73rem;color:{T["text2"]};'
                    f'font-family:DM Sans,sans-serif;margin:.15rem 0 .4rem;'
                    f'padding:.3rem .6rem;background:{T["card2"]};border-radius:7px;'
                    f'border-left:3px solid {T["accent"]};">'
                    f'<span style="color:{T["muted"]};">Utilizzo:</span> '
                    f'<strong style="color:{T["text"]};">Fonte di concetti per la verifica</strong> '
                    f'<span style="color:{T["muted"]};">'
                    f'— l\'AI userà i contenuti come base per le domande</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )
            else:
                # Verifica / Esercizi → mostra dropdown con opzioni specifiche
                _ops_keys = _OPZIONI_PER_TIPO.get(tipo_doc, ["stile_e_struttura"])
                _ops_labels = []
                for k in _ops_keys:
                    lbl = _OPZIONI_LABEL.get(k, k)
                    _ops_labels.append(lbl)

                # Label contestuale sopra il dropdown
                if tipo_doc == "verifica":
                    _dropdown_title = "Come vuoi usare questa verifica?"
                elif tipo_doc == "esercizio_singolo":
                    _dropdown_title = "Come vuoi usare questo esercizio?"
                else:
                    _dropdown_title = "Come vuoi usare questi esercizi?"

                st.markdown(
                    f'<div style="font-size:.74rem;font-weight:600;color:{T["text2"]};'
                    f'margin:.15rem 0 .2rem 0;">{_dropdown_title}</div>',
                    unsafe_allow_html=True
                )
                _cur_idx_m = _ops_keys.index(fmode) if fmode in _ops_keys else 0
                _sel_lab = st.selectbox(
                    f"Modalità file {_i}",
                    options=_ops_labels,
                    index=_cur_idx_m,
                    label_visibility="collapsed",
                    key=f"mode_sel_{_i}",
                )
                _new_mode = _ops_keys[_ops_labels.index(_sel_lab)]
                if _new_mode != fmode:
                    st.session_state.analisi_docs_list[_i]["file_mode"] = _new_mode
                    st.rerun()

            # Box istruzioni aggiuntive
            _hint_istr = {
                "stile_e_struttura":    "es. Mantieni la struttura a 4 esercizi, cambia argomento",
                "copia_fedele":         "es. Cambia i valori numerici mantenendo lo stesso schema",
                "base_conoscenza":      "es. Concentrati sui concetti del paragrafo 3.2",
                "includi_esercizio":    "es. Rendi i numeri più semplici, aggiungi un sottopunto",
                "esercizio_simile":     "es. Mantieni la struttura ma usa dati completamente diversi",
            }.get(_new_mode, "es. Indica come vuoi usare questo documento…")

            _istr_key = f"istr_file_{fhash}"
            _cur_istr = st.session_state.istruzioni_per_file.get(str(fhash), "")
            _nuova_istr = st.text_area(
                f"Istruzioni file {_i}",
                value=_cur_istr,
                placeholder=_hint_istr,
                height=64,
                label_visibility="collapsed",
                key=_istr_key,
            ).strip()
            if _nuova_istr != _cur_istr:
                st.session_state.istruzioni_per_file[str(fhash)] = _nuova_istr

            # Bottoni Conferma / Rimuovi
            st.markdown("<div style='height:.2rem'></div>", unsafe_allow_html=True)
            _cc, _cx, _csp = st.columns([4, 2, 1], gap="small")
            with _cc:
                if st.button("Usa questo file", key=f"conf_{_i}",
                             use_container_width=True, type="primary"):
                    # In facsimile mode, auto-force copia_fedele for verifica docs
                    _mode_to_save = _new_mode
                    if st.session_state.get("_facsimile_mode") and tipo_doc == "verifica":
                        _mode_to_save = "copia_fedele"
                    st.session_state.analisi_docs_list[_i]["confirmed"] = True
                    st.session_state.analisi_docs_list[_i]["file_mode"] = _mode_to_save
                    st.session_state.istruzioni_per_file[str(fhash)] = _nuova_istr
                    st.session_state.file_mode = _mode_to_save
                    _consolida_info()
                    st.rerun()
            with _cx:
                if st.button("Rimuovi", key=f"rm_{_i}",
                             use_container_width=True):
                    _da_rimuovere.append(_i)

        st.markdown("<div style='height:.15rem'></div>", unsafe_allow_html=True)

    # Applica rimozioni
    if _da_rimuovere:
        for _idx in sorted(_da_rimuovere, reverse=True):
            _fh = str(st.session_state.analisi_docs_list[_idx]["file_hash"])
            st.session_state.analisi_docs_list.pop(_idx)
            st.session_state.istruzioni_per_file.pop(_fh, None)
        _consolida_info()
        if st.session_state.analisi_docs_list:
            st.session_state.analisi_doc = st.session_state.analisi_docs_list[0]["analisi"]
        else:
            st.session_state.analisi_doc = None
            st.session_state.info_consolidate = {}
        # ── Reset dinamico del contesto argomento: se la lista cambia,
        # il campo argomento si sincronizza sul nuovo contenuto. ────────────
        # _consolida_info aggiorna direttamente session_state.info_consolidate
        _consolida_info()
        # Resetta anche il campo argomento UI (se l'utente lo aveva modificato manualmente)
        for _k in ["ob_argomento", "sel_argomento_a"]:
            if _k in st.session_state:
                del st.session_state[_k]
        st.rerun()

    # Nessun file ancora
    if not lista:
        return

    # Stop se qualche file non è ancora confermato
    _non_conf = [e for e in lista if not e["confirmed"]]
    if _non_conf:
        return

    # ─────────────────────────────────────────────────────────────────────────
    # SEZIONE 3 — Info consolidate + campi obbligatori mancanti
    # ─────────────────────────────────────────────────────────────────────────
    info = st.session_state.info_consolidate
    arg_cons     = info.get("contenuto_argomento") or ""
    scuola_cons  = info.get("scuola") or ""
    materia_cons = info.get("materia") or ""

    # Chip riepilogo — "Rilevato dai file"
    _chips = []
    if materia_cons: _chips.append(("Materia",    materia_cons))
    if scuola_cons:  _chips.append(("Scuola",     scuola_cons))
    if arg_cons:     _chips.append(("Argomento",  (arg_cons[:45]+"…") if len(arg_cons)>45 else arg_cons))

    if _chips:
        st.markdown(
            f'<div style="margin:.5rem 0 .4rem;">'
            f'<div style="font-size:.72rem;font-weight:700;color:{T["muted"]};'
            f'font-family:DM Sans,sans-serif;margin-bottom:.3rem;">💡 Rilevato dai file:</div>'
            f'<div style="display:flex;flex-wrap:wrap;gap:.35rem;">'
            + "".join(
                f'<span style="font-size:.72rem;background:{T["card"]};border:1px solid {T["border"]};'
                f'border-radius:6px;padding:3px 10px;color:{T["text2"]};">'
                f'<span style="color:{T["muted"]};font-size:.66rem;">{lbl}:</span> {val}</span>'
                for lbl, val in _chips
            ) +
            f'</div></div>',
            unsafe_allow_html=True
        )

    st.markdown(
        f'<div style="height:1px;background:{T["border"]};margin:.4rem 0 .7rem;'
        f'border-radius:1px;"></div>',
        unsafe_allow_html=True
    )

    # Campi obbligatori mancanti
    _manca_argomento = not arg_cons
    _manca_scuola    = not scuola_cons
    _manca_materia   = not materia_cons

    if _manca_argomento or _manca_scuola or _manca_materia:
        st.markdown(
            f'<div style="background:{T["hint_bg"]};border:1px solid {T["hint_border"]};'
            f'border-radius:10px;padding:.55rem .85rem;margin-bottom:.7rem;">'
            f'<div style="font-size:.73rem;font-weight:700;color:{T["hint_text"]};'
            f'margin-bottom:.3rem;">💡 Alcune info non sono state ricavate dai file — '
            f'compilale qui:</div></div>',
            unsafe_allow_html=True
        )

    _col_obbligatori = []
    if _manca_argomento: _col_obbligatori.append("argomento")
    if _manca_scuola:    _col_obbligatori.append("scuola")
    if _manca_materia:   _col_obbligatori.append("materia")

    _val_argomento = arg_cons
    _val_scuola    = scuola_cons
    _val_materia   = materia_cons

    if _col_obbligatori:
        _cols_ob = st.columns(len(_col_obbligatori), gap="small")
        for _j, _campo in enumerate(_col_obbligatori):
            with _cols_ob[_j]:
                if _campo == "argomento":
                    st.markdown('<div class="opt-label">Argomento verifica ✱</div>',
                                unsafe_allow_html=True)
                    _val_argomento = st.text_input(
                        "Argomento", placeholder="es. Equazioni di secondo grado",
                        label_visibility="collapsed", key="ob_argomento"
                    ).strip()
                elif _campo == "scuola":
                    st.markdown('<div class="opt-label">Tipo di scuola ✱</div>',
                                unsafe_allow_html=True)
                    _val_scuola = st.selectbox(
                        "Scuola", SCUOLE, index=0,
                        label_visibility="collapsed", key="ob_scuola"
                    )
                elif _campo == "materia":
                    st.markdown('<div class="opt-label">Materia ✱</div>',
                                unsafe_allow_html=True)
                    _mat_opts = MATERIE + ["Altra materia…"]
                    _val_materia_sel = st.selectbox(
                        "Materia", _mat_opts, index=0,
                        label_visibility="collapsed", key="ob_materia"
                    )
                    if _val_materia_sel == "Altra materia…":
                        _val_materia = st.text_input(
                            "Scrivi materia", label_visibility="collapsed",
                            key="ob_materia_custom"
                        ).strip() or "Matematica"
                    else:
                        _val_materia = _val_materia_sel

    # ─────────────────────────────────────────────────────────────────────────
    # SEZIONE 4+5 — Impostazioni (expander collassabile)
    # ─────────────────────────────────────────────────────────────────────────
    _fmode_prevalente = lista[0]["file_mode"] if lista else "stile_e_struttura"
    _hint_box = {
        "stile_e_struttura":    "es. Aumenta la difficoltà, mantieni 4 esercizi",
        "base_conoscenza":      "es. Concentrati sulla definizione e sulle applicazioni pratiche",
        "copia_fedele":         "es. Rendi le domande leggermente più difficili",
        "includi_esercizio":    "es. Rendi il testo più semplice, mantieni la struttura",
        "esercizio_simile":     "es. Usa dati completamente diversi",
    }.get(_fmode_prevalente, "es. Indica preferenze su tipo esercizi, livello, stile…")

    with st.expander("⚙️ Impostazioni verifica", expanded=False):
        st.markdown(
            f'<div style="font-size:.78rem;font-weight:700;color:{T["text"]};'
            f'font-family:DM Sans,sans-serif;margin-bottom:.2rem;">'
            f'Indicazioni aggiuntive per l\'AI <span style="font-weight:400;color:{T["muted"]};">(opzionale)</span>'
            f'</div>',
            unsafe_allow_html=True
        )
        istruzioni_extra = st.text_area(
            "Note", placeholder=_hint_box, height=72,
            label_visibility="collapsed", key="percorso_a_istruzioni",
        ).strip()

        st.markdown(
            f'<div style="height:1px;background:{T["border"]};margin:.55rem 0 .55rem;'
            f'border-radius:1px;"></div>',
            unsafe_allow_html=True
        )

        _mat_list  = MATERIE + ["Altra materia..."]
        _mat_idx   = _mat_list.index(_val_materia) if _val_materia in _mat_list else 0
        _scu_idx   = SCUOLE.index(_val_scuola) if _val_scuola in SCUOLE else 0
        _es_default = info.get("num_esercizi_rilevati", 4) or 4
        _es_default = max(1, min(int(_es_default), 15))
        _es_options = list(range(1, 16))
        _es_idx     = _es_options.index(_es_default) if _es_default in _es_options else 3

        st.markdown(
            f'<div style="font-size:.78rem;font-weight:800;color:{T["text"]};'
            f'font-family:DM Sans,sans-serif;margin-bottom:.4rem;">Parametri verifica</div>',
            unsafe_allow_html=True
        )

        # Prima riga: Argomento (full-width o con materia)
        _col_arg, _col_m = st.columns([3, 2], gap="small")
        with _col_arg:
            st.markdown('<div class="opt-label">Argomento della verifica</div>',
                        unsafe_allow_html=True)
            _argomento_input = st.text_input(
                "Argomento",
                value=_val_argomento or arg_cons,
                placeholder="es. Equazioni di secondo grado",
                label_visibility="collapsed",
                key="sel_argomento_a",
            ).strip()
            if _argomento_input:
                _val_argomento = _argomento_input
        with _col_m:
            st.markdown('<div class="opt-label">Materia</div>', unsafe_allow_html=True)
            _sel_m = st.selectbox(
                "Materia", _mat_list, index=_mat_idx,
                label_visibility="collapsed", key="sel_materia_a",
            )
            materia_scelta = (
                st.text_input("Scrivi materia:", key="_mat_custom_a",
                              label_visibility="collapsed").strip() or "Matematica"
                if _sel_m == "Altra materia..."
                else (_sel_m or "Matematica")
            )

        # Seconda riga: Scuola + Esercizi
        _col_s, _col_n = st.columns(2, gap="small")
        with _col_s:
            st.markdown('<div class="opt-label">Tipo di scuola</div>', unsafe_allow_html=True)
            difficolta = st.selectbox(
                "Scuola", SCUOLE, index=_scu_idx,
                label_visibility="collapsed", key="sel_scuola_a",
            )
        with _col_n:
            st.markdown('<div class="opt-label">N° esercizi</div>', unsafe_allow_html=True)
            num_esercizi = st.selectbox(
                "Numero esercizi", options=_es_options, index=_es_idx,
                label_visibility="collapsed", key="sel_num_es_a",
                format_func=lambda x: f"{x} eserc.",
            )

        # Punteggi
        mostra_punteggi = True
        con_griglia     = True
        punti_totali    = 100
        _tog = st.toggle("Aggiungi punteggi e griglia", value=True, key="toggle_punteggi_a")
        mostra_punteggi = _tog
        con_griglia     = _tog
        if _tog:
            _pt_opts = list(range(10, 105, 5))
            _pt_idx  = _pt_opts.index(100) if 100 in _pt_opts else len(_pt_opts) - 1
            st.markdown('<div class="opt-label">Punti totali</div>', unsafe_allow_html=True)
            punti_totali = st.selectbox(
                "Punti totali", options=_pt_opts, index=_pt_idx,
                label_visibility="collapsed", key="sel_punti_a",
                format_func=lambda x: f"{x} pt",
            )

    # ─────────────────────────────────────────────────────────────────────────
    # SEZIONE 5b — Esercizi personalizzati da file (se rilevati, solo per modi non-facsimile)
    # ─────────────────────────────────────────────────────────────────────────
    # Raccoglie tutti gli esercizi trovati dai file confermati
    # SKIP esercizi se tutti i file sono in modalità facsimile (copia_fedele)
    _tutti_facsimile = all(
        e["file_mode"] == "copia_fedele" for e in lista if e["confirmed"]
    ) if lista else False

    _tutti_esercizi_trovati = []
    if not _tutti_facsimile:
        for _entry in lista:
            if _entry["confirmed"] and _entry["file_mode"] not in ("ignora",):
                _es_list = _entry["analisi"].get("esercizi_trovati") or []
                for _ex in _es_list:
                    _tutti_esercizi_trovati.append({
                        "file_name": _entry["file_name"],
                        "file_hash": _entry["file_hash"],
                        "esercizio": _ex,
                    })

    if _tutti_esercizi_trovati:
        # Recupera quanti sono già stati marcati per inclusione
        _es_custom_da_file = st.session_state.get("_es_custom_da_file", {})
        st.markdown(
            f'<div style="height:1px;background:{T["border"]};margin:.3rem 0 .6rem;'
            f'border-radius:1px;"></div>',
            unsafe_allow_html=True
        )
        # Label "Utilizzato come materiale di supporto" per i file base_conoscenza/appunti
        _file_supporto = [e for e in lista if e["confirmed"] and e["file_mode"] in ("base_conoscenza",)]
        if _file_supporto:
            st.markdown(
                f'<div style="font-size:.68rem;color:{T["muted"]};font-family:DM Sans,sans-serif;'
                f'padding:.2rem .1rem .4rem;font-style:italic;">'
                + ", ".join(f'"{e["file_name"]}"' for e in _file_supporto) +
                f' — <span style="color:{T["hint_text"]};">utilizzato come materiale di supporto</span>'
                f'</div>',
                unsafe_allow_html=True
            )

        with st.expander(
            f"✏️ {len(_tutti_esercizi_trovati)} esercizio/i rilevato/i — opzioni di estrazione",
            expanded=len(_tutti_esercizi_trovati) <= 3,
        ):
            st.markdown(
                f'<div style="font-size:.74rem;color:{T["text2"]};font-family:DM Sans,sans-serif;'
                f'line-height:1.5;padding:.2rem 0 .5rem;">'
                f'Esercizi identificati nei file caricati. Seleziona quelli da includere nella nuova verifica.'
                f'</div>',
                unsafe_allow_html=True
            )
            for _ei, _ex_entry in enumerate(_tutti_esercizi_trovati):
                _ex      = _ex_entry["esercizio"]
                _ex_num  = _ex.get("numero", _ei + 1)
                _ex_tipo = _ex.get("tipo", "Aperto")
                _ex_testo = _ex.get("testo_breve") or "—"
                _ex_num_dati = _ex.get("ha_dati_numerici", False)
                _ex_key_incl = f"incl_es_{_ei}"
                _ex_key_note = f"note_es_{_ei}"
                _ex_key_hash = str(_ex_entry["file_hash"]) + f"_{_ei}"

                st.markdown(
                    f'<div class="es-recap-card">'
                    f'<div class="es-recap-header">'
                    f'<span class="es-recap-num">Esercizio {_ex_num}</span>'
                    f'<span class="es-recap-tipo">{_ex_tipo}</span>'
                    + (f'<span style="font-size:.63rem;background:{T["card"]};border-radius:4px;'
                       f'padding:1px 6px;color:{T["muted"]};">🔢 numeri</span>'
                       if _ex_num_dati else "") +
                    f'<span class="es-recap-source">da {_ex_entry["file_name"]}</span>'
                    f'</div>'
                    f'<div class="es-recap-testo">«{(_ex_testo[:120]+"…") if len(_ex_testo)>120 else _ex_testo}»</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )
                _incl = st.toggle(
                    f"Includi nella verifica",
                    value=_es_custom_da_file.get(_ex_key_hash, {}).get("includi", False),
                    key=_ex_key_incl,
                )
                if _incl:
                    _note_es = st.text_area(
                        "Note per questo esercizio",
                        value=_es_custom_da_file.get(_ex_key_hash, {}).get("note", ""),
                        placeholder="es. Rendi i numeri diversi · Aumenta la difficoltà · Aggiungi un sottopunto",
                        height=60,
                        label_visibility="visible",
                        key=_ex_key_note,
                    ).strip()
                else:
                    _note_es = ""
                # Salva in session state
                if "_es_custom_da_file" not in st.session_state:
                    st.session_state["_es_custom_da_file"] = {}
                st.session_state["_es_custom_da_file"][_ex_key_hash] = {
                    "includi": _incl,
                    "note": _note_es,
                    "testo": _ex_testo,
                    "tipo": _ex_tipo,
                    "numero": _ex_num,
                }
                st.markdown("<div style='height:.1rem'></div>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────────────────
    # SEZIONE 6 — Pulsante Genera
    # ─────────────────────────────────────────────────────────────────────────
    # Argomento finale: da text_input sezione 5 o da info consolidate
    _arg_finale    = _val_argomento or arg_cons
    _scuola_finale = difficolta
    _manca_ancora  = not _arg_finale

    st.markdown("<div style='height:.3rem'></div>", unsafe_allow_html=True)

    genera_btn = st.button(
        "Genera Bozza",
        use_container_width=True,
        type="primary",
        disabled=_limite or _manca_ancora,
        key="genera_btn_a",
    )
    if _manca_ancora and not _limite:
        st.markdown(
            f'<div style="font-size:.75rem;color:{T["warn"]};text-align:center;margin-top:.3rem;">'
            f'Inserisci l\'argomento della verifica per continuare.</div>',
            unsafe_allow_html=True
        )
    if _limite:
        st.markdown(
            '<div style="text-align:center;font-size:.82rem;color:#EF4444;margin-top:.4rem;">'
            '⛔ Limite mensile raggiunto.</div>',
            unsafe_allow_html=True
        )

    if genera_btn and not _limite and not _manca_ancora:
        # Consolida istruzioni per-file con le note globali
        _istr_per_file_testi = []
        for entry in lista:
            _fh_str = str(entry["file_hash"])
            _istr = st.session_state.istruzioni_per_file.get(_fh_str, "").strip()
            if _istr:
                _istr_per_file_testi.append(
                    f"[File: {entry['file_name']}] {_istr}"
                )

        # Aggiungi note esercizi personalizzati da file
        _es_custom_sel = st.session_state.get("_es_custom_da_file", {})
        _es_da_includere_note = []
        for _ex_key, _ex_data in _es_custom_sel.items():
            if _ex_data.get("includi"):
                _ex_desc = f"Esercizio {_ex_data['numero']} [{_ex_data['tipo']}]: «{_ex_data['testo']}»"
                if _ex_data.get("note"):
                    _ex_desc += f" — Istruzione docente: {_ex_data['note']}"
                _es_da_includere_note.append(_ex_desc)
        if _es_da_includere_note:
            _istr_per_file_testi.append(
                "ESERCIZI DA INCLUDERE (adattali mantenendo l'argomento della nuova verifica):\n"
                + "\n".join(f"• {x}" for x in _es_da_includere_note)
            )

        _istruzioni_combinate = "\n".join(_istr_per_file_testi)
        if istruzioni_extra:
            _istruzioni_combinate = (
                istruzioni_extra + ("\n\n" + _istruzioni_combinate if _istruzioni_combinate else "")
            )

        _ad_merged = dict(st.session_state.info_consolidate)
        if _arg_finale:
            _ad_merged["contenuto_argomento"] = _arg_finale
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
            argomento_override=_arg_finale if _manca_argomento else None,
        )
        s_es, imgs_es = _build_prompt_esercizi(
            st.session_state.esercizi_custom,
            num_esercizi,
            punti_totali if mostra_punteggi else 0,
            mostra_punteggi,
        )
        if _ad_merged.get("confidence", 0) >= 0.70 and materia_scelta in MATERIE:
            _salva_docente_preferenze(materia_scelta, {
                "scuola": difficolta,
                "stile_desc": _ad_merged.get("stile_desc"),
                "tipi_esercizi_preferiti": _ad_merged.get("tipi_domande"),
                "num_item_medi": _ad_merged.get("num_item_medi"),
            })
        _file_isp = (
            st.session_state.get(f"file_up_{len(lista)-1}") or
            st.session_state.get("file_ispirazione")
        )
        st.session_state.dialogo_stato = "confermato"
        _lancia_generazione(
            materia_scelta=materia_scelta,
            argomento=argomento_gen,
            difficolta=difficolta,
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

    # ── Torna indietro — in fondo alla pagina ────────────────────────────────
    st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)
    _ba1, _ba2, _ba3 = st.columns([3, 2, 3])
    with _ba2:
        if st.button("← Cambia percorso", key="btn_back_a_upload",
                     use_container_width=True):
            _reset_percorso()
            st.session_state["_facsimile_mode"] = False
            st.rerun()


def _render_dialogo_conferma():
    """Deprecato — ora tutto in _render_percorso_a_upload()."""
    _render_percorso_a_upload()


def _render_percorso_a_configura(num_esercizi_totali_ref: list):
    """Deprecato — ora tutto in _render_percorso_a_upload()."""
    # Questo path non dovrebbe più essere raggiunto.
    # Restituisce valori di default sicuri per evitare crash.
    return ("", "Matematica", "Generico", True, True, 100, False)


def _render_percorso_b_form():
    """
    Percorso B: form tradizionale pulito, senza upload.
    Restituisce tutti i parametri necessari a genera_verifica().
    """
    # ── Nota: template gallery rimossa per semplicità ──────────────────────────

    # Indicatore modalità manuale (header compatto)
    st.markdown(
        f'<div style="background:{T["card"]};border:1px solid {T["border"]};'
        f'border-radius:10px;padding:.5rem .85rem;margin-bottom:.8rem;'
        f'display:flex;align-items:center;gap:.6rem;">'
        f'<span style="font-size:1rem;">✍️</span>'
        f'<div>'
        f'<div style="font-size:.8rem;font-weight:700;color:{T["text"]};'
        f'font-family:DM Sans,sans-serif;">Configurazione manuale</div>'
        f'<div style="font-size:.68rem;color:{T["muted"]};font-family:DM Sans,sans-serif;">'
        f'Compila i campi — nessun upload disponibile in questa modalità</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    _prev = st.session_state.gen_params or {}

    # Materia + Scuola
    st.markdown(
        f'<div class="step-label">'
        f'<span class="step-title">Materia e tipo di scuola</span>'
        f'<span class="step-line"></span>'
        f'</div>',
        unsafe_allow_html=True
    )
    _col_m, _col_s = st.columns(2)
    _mat_list = MATERIE + ["✏️ Altra materia..."]
    _mat_prev = _prev.get("materia", "Matematica")
    _mat_idx  = _mat_list.index(_mat_prev) if _mat_prev in _mat_list else 0
    _scu_prev = _prev.get("difficolta", "")
    _scu_idx  = SCUOLE.index(_scu_prev) if _scu_prev in SCUOLE else 0

    with _col_m:
        _sel_m = st.selectbox(
            "Materia", _mat_list, index=_mat_idx,
            label_visibility="collapsed", key="sel_materia_b",
        )
        materia_scelta = (
            st.text_input("Scrivi materia:", key="_mat_custom_b",
                          label_visibility="collapsed").strip() or "Matematica"
            if _sel_m == "✏️ Altra materia..."
            else (_sel_m or "Matematica")
        )
    with _col_s:
        difficolta = st.selectbox(
            "Scuola", SCUOLE, index=_scu_idx,
            label_visibility="collapsed", key="sel_scuola_b",
        )

    # Argomento
    st.markdown(
        f'<div class="ai-hint"><span class="ai-hint-icon">💡</span>'
        f'<span><strong>Suggerimento:</strong> più dettagli = verifica più precisa. '
        f'"Equazioni di II grado con discriminante" funziona meglio di "algebra".</span>'
        f'</div>'
        f'<div class="step-label">'
        f'<span class="step-title">Argomento della verifica</span>'
        f'<span class="step-line"></span>'
        f'</div>',
        unsafe_allow_html=True
    )
    argomento = st.text_area(
        "argomento",
        placeholder=(
            "es. Le equazioni di secondo grado\n"
            "es. La Rivoluzione Francese\n"
            "es. Il ciclo dell'acqua"
        ),
        height=90, label_visibility="collapsed", key="argomento_area_b",
    ).strip()

    # Numero esercizi — slider sopra il pulsante
    st.markdown("<div style='height:.4rem'></div>", unsafe_allow_html=True)
    st.markdown(
        f'<div class="opt-label" style="margin-bottom:3px;">Numero di esercizi</div>',
        unsafe_allow_html=True
    )
    num_esercizi = st.slider(
        "Numero esercizi",
        min_value=1, max_value=15, value=4,
        label_visibility="collapsed", key="sel_num_es_b",
    )

    st.markdown("<div style='height:.4rem'></div>", unsafe_allow_html=True)
    genera_btn = st.button(
        "🚀  Genera Bozza",
        use_container_width=True,
        type="primary",
        disabled=_limite,
        key="genera_btn_b",
    )

    if _limite:
        st.markdown(
            '<div style="text-align:center;font-size:.82rem;color:#EF4444;margin-top:.4rem;'
            'font-family:DM Sans,sans-serif;font-weight:600;">'
            '⛔ Limite mensile raggiunto.'
            '</div>',
            unsafe_allow_html=True
        )

    # Personalizzazione Avanzata
    _prefs = st.session_state._docente_prefs.get(materia_scelta, {})
    if not _prefs and st.session_state.utente and materia_scelta in MATERIE:
        _prefs = _carica_docente_preferenze(st.session_state.utente.id, materia_scelta)
        st.session_state._docente_prefs[materia_scelta] = _prefs

    with st.expander("Personalizzazione Avanzata ⚙️", expanded=False):
        if _prefs.get("stile_desc"):
            st.markdown(
                f'<div style="background:{T["hint_bg"]};border:1px solid {T["hint_border"]};'
                f'border-radius:8px;padding:.4rem .7rem;font-size:.72rem;color:{T["hint_text"]};'
                f'font-family:DM Sans,sans-serif;margin-bottom:.6rem;">'
                f'✨ Preferenze salvate per <b>{materia_scelta}</b>: {_prefs["stile_desc"]}'
                f'</div>',
                unsafe_allow_html=True
            )

        _tog = st.toggle(
            "Aggiungi punteggi e griglia di valutazione",
            value=True, key="toggle_punteggi_b",
        )
        mostra_punteggi = _tog
        con_griglia     = _tog
        punti_totali    = 100
        if _tog:
            _pt_opts = list(range(10, 105, 5))
            _pt_idx  = _pt_opts.index(100) if 100 in _pt_opts else len(_pt_opts) - 1
            st.markdown('<div class="opt-label">Punti totali</div>', unsafe_allow_html=True)
            punti_totali = st.selectbox(
                "Punti totali", options=_pt_opts, index=_pt_idx,
                label_visibility="collapsed", key="sel_punti_b",
                format_func=lambda x: f"{x} pt",
            )

        st.markdown('<div class="opt-label">Struttura esercizi</div>', unsafe_allow_html=True)
        with st.expander("Definisci tipo e contenuto di ogni esercizio", expanded=False):
            n_custom = len(st.session_state.esercizi_custom)
            n_liberi = max(0, num_esercizi - n_custom)
            if n_custom == 0:
                st.info(f"Tutti i {num_esercizi} esercizi generati liberamente dall'AI.")
            elif n_custom >= num_esercizi:
                st.warning(f"Limite raggiunto ({n_custom}/{num_esercizi}).")
            else:
                st.success(f"✅ {n_custom} definiti + {n_liberi} liberi = {num_esercizi}")

            _to_remove = None
            for _i, _ex in enumerate(st.session_state.esercizi_custom):
                st.markdown(f"**Esercizio {_i+1}**")
                _t = st.selectbox(
                    "Tipo", TIPI_ESERCIZIO,
                    index=TIPI_ESERCIZIO.index(_ex.get("tipo", "Aperto")),
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
                        "Immagine", type=["png","jpg","jpeg"],
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

        st.markdown('<div class="opt-label">Note per l\'AI</div>', unsafe_allow_html=True)
        note_extra = st.text_area(
            "Note AI",
            placeholder=NOTE_PLACEHOLDER.get(materia_scelta, ""),
            height=65, key="note_area_b", label_visibility="collapsed",
        )

    # ── Torna indietro — in fondo alla pagina ────────────────────────────────
    st.markdown("<div style='height:.8rem'></div>", unsafe_allow_html=True)
    _bb1, _bb2, _bb3 = st.columns([3, 2, 3])
    with _bb2:
        if st.button("← Cambia percorso", key="btn_back_b",
                     use_container_width=True):
            st.session_state.input_percorso = None
            st.rerun()

    return (
        argomento, materia_scelta, difficolta,
        mostra_punteggi, con_griglia, punti_totali,
        num_esercizi, note_extra, genera_btn,
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
    mathpix_context: str | None = None,
):
    """
    Funzione condivisa dai due percorsi: lancia genera_verifica,
    aggiorna session_state e transita a STAGE_REVIEW.
    """
    calibrazione = CALIBRAZIONE_SCUOLA.get(difficolta, "")
    _t_start = time.time()
    _n_steps = 4
    _step    = [0]
    _prog    = st.empty()

    def _avanza(testo):
        _step[0] += 1
        perc      = int(min(_step[0] / _n_steps, 0.97) * 100)
        _acc      = T["accent"]
        _acc_fade = _acc + "cc"
        _prog.markdown(
            '<div style="margin:.6rem 0 1rem 0;">'
            '<div style="font-size:.82rem;font-weight:600;color:' + T["text2"] + ';'
            'font-family:DM Sans,sans-serif;margin-bottom:6px;">' + testo + '</div>'
            '<div style="background:' + T["border"] + ';border-radius:100px;height:8px;overflow:hidden;">'
            '<div style="background:linear-gradient(90deg,' + _acc + ',' + _acc_fade + ');'
            'width:' + str(perc) + '%;height:100%;border-radius:100px;transition:width .4s ease;"></div>'
            '</div></div>',
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
    _modello_validi_per_piano = {
        "free":  {"gemini-2.5-flash-lite-preview-06-17"},
        "pro":   {"gemini-2.5-flash-lite-preview-06-17", "gemini-2.5-flash-preview-05-20"},
        "gold":  {v["id"] for v in MODELLI_DISPONIBILI.values()},
        "admin": {v["id"] for v in MODELLI_DISPONIBILI.values()},
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

        preamble, blocks = _extract_blocks(st.session_state.verifiche["A"]["latex"])
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

        # ── Transita a STAGE_PREVIEW (anteprima rapida) invece di STAGE_REVIEW
        st.session_state.stage = STAGE_PREVIEW
        st.rerun()

    except Exception as _e:
        _prog.empty()
        st.error(f"❌ Errore durante la generazione: {_e}")


# ═══════════════════════════════════════════════════════════════════════════════
#  STAGE_INPUT — orchestratore principale
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

    # ── PERCORSO A ────────────────────────────────────────────────────────────
    if percorso == "A":
        _render_percorso_a_upload()
        return

    # ── PERCORSO B ────────────────────────────────────────────────────────────
    if percorso == "B":
        (
            argomento, materia_scelta, difficolta,
            mostra_punteggi, con_griglia, punti_totali,
            num_esercizi_totali, note_extra, genera_btn,
        ) = _render_percorso_b_form()

        if not genera_btn or _limite:
            return

        if not argomento:
            st.warning("⚠️ Inserisci l'argomento della verifica.")
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
            imgs_es=imgs_es,
            file_ispirazione=None,
            mathpix_context=None,
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
    st.markdown(
        '<div style="background:linear-gradient(120deg,#D97706 0%,#16a34a 100%);'
        'border-radius:14px;padding:1rem 1.4rem;margin-bottom:1.2rem;">'
        '<div style="display:flex;align-items:center;gap:12px;">'
        '<span style="font-size:1.6rem;">📄</span>'
        '<div>'
        '<div style="font-family:DM Sans,sans-serif;font-size:1.05rem;font-weight:900;color:#fff;">'
        'Anteprima Verifica</div>'
        '<div style="font-size:.75rem;color:#ffffffcc;">'
        + materia_str + ' · ' + scuola_str + ' · ' + argomento_str +
        '</div></div></div></div>',
        unsafe_allow_html=True
    )

    # ── Preview PDF — tutte le pagine ────────────────────────────────────────
    if preview_imgs:
        n_prev = len(preview_imgs)
        if n_prev == 1:
            st.image(preview_imgs[0], use_container_width=True)
        else:
            # Due o più pagine: prima in full-width, resto a coppie fianco a fianco
            st.image(preview_imgs[0], use_container_width=True,
                     caption="Pagina 1")
            for _pi in range(1, n_prev, 2):
                _pc1, _pc2 = st.columns(2, gap="small")
                with _pc1:
                    st.image(preview_imgs[_pi], use_container_width=True,
                             caption=f"Pagina {_pi + 1}")
                with _pc2:
                    if _pi + 1 < n_prev:
                        st.image(preview_imgs[_pi + 1], use_container_width=True,
                                 caption=f"Pagina {_pi + 2}")
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
                     type="primary", key="preview_ok"):
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
                     key="preview_edit"):
            st.session_state.stage = STAGE_REVIEW
            st.rerun()

    st.markdown("<br/>", unsafe_allow_html=True)

    # ── Link "torna alla configurazione" ────────────────────────────────────
    if st.button("← Ricomincia da capo", key="preview_back"):
        for _k in ("stage", "verifiche", "gen_params", "review_blocks",
                   "review_preamble", "preview_images", "input_percorso",
                   "dialogo_stato", "analisi_doc", "file_mode"):
            if _k in st.session_state:
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

    st.markdown(
        '<div style="background:linear-gradient(135deg,' + T["accent_light"] + ' 0%,' + T["card"] + ' 100%);'
        'border:2px solid ' + T["accent"] + ';border-radius:16px;overflow:hidden;margin-bottom:1.2rem;">'
        '<div style="background:linear-gradient(120deg,#D97706 0%,#16a34a 100%);padding:.85rem 1.2rem;">'
        '<div style="display:flex;align-items:center;gap:12px;">'
        '<span style="font-size:1.5rem;">✏️</span>'
        '<div style="flex:1;">'
        '<div style="font-family:DM Sans,sans-serif;font-size:1rem;font-weight:900;color:#fff;'
        'text-shadow:0 1px 4px rgba(0,0,0,.25);">'
        'Revisione Bozza</div>'
        '<div style="font-size:.72rem;color:#fff;opacity:.9;margin-top:1px;">'
        + materia_str + ' · ' + scuola_str + ' · ' + argomento_str + '</div>'
        '</div>'
        '<div style="background:#ffffff25;border:1px solid #ffffff40;border-radius:20px;'
        'padding:4px 12px;font-size:.68rem;font-weight:700;color:#fff;">'
        + str(n_blocks) + ' ESERCIZI</div>'
        '</div></div>'
        '<div style="padding:.75rem 1.2rem;background:' + T["card"] + ';">'
        '<div style="font-size:.8rem;color:' + T["text2"] + ';line-height:1.5;">'
        'Seleziona l\'esercizio dal menu. Il testo appare nell\'anteprima qui sotto, '
        'seguito dalla visualizzazione PDF del documento completo. '
        'Usa il campo di modifica per richiedere cambiamenti — l\'AI rigenererà solo l\'esercizio selezionato. '
        'Quando sei soddisfatto, premi <strong>Conferma e genera PDF</strong>.'
        '</div></div></div>',
        unsafe_allow_html=True
    )

    # ── IDEA #3: Smart Preview hint ──────────────────────────────────────────
    st.markdown(
        f'<div class="smart-preview-hint">'
        f'  <span style="font-size:1rem;flex-shrink:0;">💡</span>'
        f'  <div>'
        f'    <strong>Modifica in tempo reale:</strong> seleziona un esercizio, '
        f'    scrivi la tua istruzione nel campo di testo e premi '
        f'    <strong>Rigenera esercizio</strong> — l\'AI aggiorna solo quel blocco '
        f'    senza toccare il resto. L\'anteprima PDF si aggiorna dopo ogni modifica confermata.'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True
    )

    if not blocks:
        st.warning("⚠️ Nessun esercizio trovato. Torna indietro e rigenera.")
        if st.button("← Torna alla configurazione"):
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

    st.markdown(
        '<div style="font-size:.72rem;color:' + T["muted"] + ';margin-top:-.3rem;margin-bottom:.5rem;">'
        '💡 Seleziona un esercizio dal menu per visualizzarlo e modificarlo.'
        '</div>',
        unsafe_allow_html=True
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
                st.info("📊 Grafici TikZ/pgfplots visibili nel PDF finale.")

            st.markdown("<div style='height:.4rem'></div>", unsafe_allow_html=True)

            # ── Expander: Modifica con AI ──────────────────────────────────────
            with st.expander("✏️ Modifica con AI", expanded=False):
                st.markdown(
                    '<div style="font-size:.76rem;color:' + T["text2"] + ';margin-bottom:.5rem;'
                    'font-family:DM Sans,sans-serif;line-height:1.45;">'
                    'Descrivi la modifica — l\'AI rigenererà solo questo esercizio.<br>'
                    '<span style="color:' + T["muted"] + ';font-size:.7rem;">'
                    '⚠️ Per cambiare i <strong>punteggi</strong> usa il pannello qui sotto.</span>'
                    '</div>',
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
                    "✏️ Applica Modifica", key=f"rw_btn_{idx}",
                    use_container_width=True, disabled=not istruzione.strip()
                )
                # Fix: messaggio di elaborazione visibile subito sotto il pulsante
                if rigenera and istruzione.strip():
                    st.info(f"⏳ Elaborazione in corso — sto modificando l'esercizio {idx+1}…")

            # ── Expander: Ricalibra Punteggi ──────────────────────────────────
            if mostra_punteggi and n_blocks > 0:
                with st.expander("⚖️ Ricalibra Punteggi", expanded=False):
                    st.markdown(
                        '<div style="font-size:.74rem;color:' + T["text2"] + ';margin-bottom:.7rem;'
                        'font-family:DM Sans,sans-serif;line-height:1.45;">'
                        'Modifica i punti per esercizio. <strong>Applica</strong> si attiva '
                        'quando la somma = <strong>' + str(punti_totali) + ' pt</strong>.'
                        '</div>',
                        unsafe_allow_html=True
                    )

                    # _cur_pts dal CORPO (non dal titolo) → evita default 0 post-regen
                    _cur_pts = [
                        _parse_pts_from_block_body(b["body"])
                        for b in st.session_state.review_blocks
                    ]

                    _rc_key = "recalibra_pts"
                    if _rc_key not in st.session_state or len(st.session_state[_rc_key]) != n_blocks:
                        st.session_state[_rc_key] = list(_cur_pts)

                    _pt_options_rc = list(range(0, punti_totali + 1))
                    _new_pts = []
                    _ncols_rc = min(n_blocks, 2)
                    _cols_rc  = st.columns(_ncols_rc)
                    for _i, _b in enumerate(st.session_state.review_blocks):
                        _title_short = re.sub(r"\s*\(\d+\s*pt\)", "", _b["title"]).strip()
                        _title_short = (_title_short[:22] + "…") if len(_title_short) > 22 else _title_short
                        with _cols_rc[_i % _ncols_rc]:
                            st.markdown(
                                f'<div style="font-size:.72rem;font-weight:700;color:{T["text2"]};'
                                f'font-family:DM Sans,sans-serif;margin-bottom:1px;">Es. {_i+1}</div>'
                                f'<div style="font-size:.64rem;color:{T["muted"]};font-family:DM Sans,sans-serif;'
                                f'margin-bottom:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">'
                                f'{_title_short}</div>',
                                unsafe_allow_html=True
                            )
                            _v = st.selectbox(
                                f"Punti es. {_i+1}",
                                options=_pt_options_rc,
                                index=min(int(st.session_state[_rc_key][_i]), punti_totali),
                                key=f"rc_pts_{_i}",
                                label_visibility="collapsed",
                                format_func=lambda x: f"{x} pt",
                            )
                            _new_pts.append(_v)

                    st.session_state[_rc_key] = [int(v) for v in _new_pts]
                    _somma, _ok, _diff = _valida_totale(_new_pts, punti_totali)

                    if _ok:
                        st.markdown(
                            '<div class="recalibra-sum-ok">'
                            '✅ Somma: <strong>' + str(_somma) + ' pt</strong>'
                            ' = ' + str(punti_totali) + ' pt'
                            '</div>',
                            unsafe_allow_html=True
                        )
                    else:
                        _diff_str = ("+" if _diff > 0 else "") + str(_diff)
                        st.markdown(
                            '<div class="recalibra-sum-err">'
                            '⚠️ Somma: <strong>' + str(_somma) + ' pt</strong>'
                            ' (' + _diff_str + ' rispetto a ' + str(punti_totali) + ' pt)'
                            '</div>',
                            unsafe_allow_html=True
                        )

                    st.markdown("<div style='height:.3rem'></div>", unsafe_allow_html=True)

                    if st.button(
                        "✅ Applica Punteggi e Rigenera PDF" if _ok else
                        f"⛔ Applica Punteggi (somma: {_somma} ≠ {punti_totali} pt)",
                        key="rc_applica",
                        disabled=not _ok,
                        use_container_width=True,
                        type="primary",
                    ):
                        for _i in range(n_blocks):
                            _clean = re.sub(r"\s*\(\d+\s*pt\)", "",
                                            st.session_state.review_blocks[_i]["title"]).strip()
                            st.session_state.review_blocks[_i]["title"] = f"{_clean} ({_new_pts[_i]} pt)"

                        _latex_rc = _reconstruct_latex(
                            st.session_state.review_preamble,
                            st.session_state.review_blocks
                        )
                        _latex_rc = fix_items_environment(_latex_rc)
                        _latex_rc = rimuovi_vspace_corpo(_latex_rc)
                        _latex_rc = rimuovi_punti_subsection(_latex_rc)
                        _latex_rc = riscala_punti_custom(_latex_rc, _new_pts)
                        if con_griglia:
                            _latex_rc = inietta_griglia(_latex_rc, punti_totali)

                        st.session_state.verifiche["A"]["latex"]           = _latex_rc
                        st.session_state.verifiche["A"]["latex_originale"] = _latex_rc

                        with st.spinner("⏳ Ricompilazione PDF…"):
                            _pdf_rc, _err_rc = compila_pdf(_latex_rc)
                        if _pdf_rc:
                            st.session_state.verifiche["A"]["pdf"]     = _pdf_rc
                            st.session_state.verifiche["A"]["pdf_ts"]  = time.time()
                            st.session_state.verifiche["A"]["preview"] = True
                            _imgs_rc, _ = pdf_to_images_bytes(_pdf_rc)
                            st.session_state.preview_images = _imgs_rc or []
                            st.session_state.preview_page   = 0
                            _new_preamble, _new_blocks = _extract_blocks(_latex_rc)
                            if _new_blocks:
                                st.session_state.review_preamble = _new_preamble
                                st.session_state.review_blocks   = _new_blocks
                            if _rc_key in st.session_state:
                                del st.session_state[_rc_key]
                            st.toast("✅ Punteggi applicati — PDF aggiornato!", icon="⚖️")
                            st.rerun()
                        else:
                            st.error("❌ Errore di compilazione.")
                            with st.expander("Log errore"):
                                st.text(_err_rc)

    # ── COLONNA DESTRA — anteprima PDF una pagina alla volta ─────────────────
    with col_pdf:
        st.markdown(
            '<div style="font-size:.72rem;font-weight:700;color:' + T["muted"] + ';'
            'text-transform:uppercase;letter-spacing:.05em;margin-bottom:.5rem;">'
            '📄 Anteprima PDF completo</div>',
            unsafe_allow_html=True
        )
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

    # ── Logica modifica AI ────────────────────────────────────────────────────
    if rigenera and istruzione.strip():
        _istr_low = istruzione.lower()

        # ── Rilevamento richieste punteggio ───────────────────────────────────
        # Se l'utente chiede di cambiare punti/punteggio reindirizza al pannello.
        _is_score_req = any(kw in _istr_low for kw in _SCORE_KEYWORDS)
        if _is_score_req:
            st.warning(
                "⚠️ **Hai menzionato punteggi / punti.**\n\n"
                "Per modificare i punti usa il pannello **⚖️ Ricalibra Punteggi** "
                "qui sopra — imposta i valori desiderati e premi **Applica Punteggi**. "
                "Il pannello AI è riservato alle modifiche al contenuto (testo, difficoltà, formato)."
            )
        else:
            # ── Regen AI con preservazione punti ─────────────────────────────
            # Cattura i punti correnti dell'esercizio PRIMA della regen.
            # Se recalibra_pts è stato già impostato dall'utente usa quello,
            # altrimenti legge dal corpo del blocco corrente.
            _pts_custom = st.session_state.get("recalibra_pts", [])
            if _pts_custom and len(_pts_custom) == n_blocks:
                _exercise_target_pts = int(_pts_custom[idx])
            else:
                _exercise_target_pts = _parse_pts_from_block_body(body)

            # Il prompt dice all'AI quanti pt deve assegnare a questo esercizio.
            # La funzione _riscala_single_block lo corregge deterministicamente dopo.
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
                f"REGOLE:\n"
                f"- Applica SOLO la modifica richiesta. NON riscrivere da zero, modifica l'esistente.\n"
                f"- Mantieni OBBLIGATORIAMENTE l'argomento '{argomento_str}'.\n"
                f"- Restituisci SOLO il blocco \\subsection*{{...}} con il nuovo esercizio.\n"
                f"- Mantieni struttura LaTeX (\\subsection*, enumerate, \\item[a)], ecc.).\n"
                f"- {punti_nota}\n"
                f"- NON includere preambolo o \\begin{{document}}.\n"
                f"OUTPUT: SOLO codice LaTeX del blocco esercizio."
            )
            with st.spinner(f"⏳ Rigenerando esercizio {idx+1} e aggiornando PDF…"):
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
                        new_body = _riscala_single_block(new_title, new_body, _exercise_target_pts)

                    st.session_state.review_blocks[idx]["title"] = new_title
                    st.session_state.review_blocks[idx]["body"]  = new_body

                    # Reset pannello ricalibra: rilegge i punteggi aggiornati
                    if "recalibra_pts" in st.session_state:
                        del st.session_state["recalibra_pts"]

                    # Fix: ricompila il PDF e aggiorna la preview dopo la modifica
                    _latex_rw = _reconstruct_latex(
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

                    st.success(f"✅ Esercizio {idx+1} rigenerato — punteggio preservato ({_exercise_target_pts} pt).")
                    time.sleep(0.4); st.rerun()
                except Exception as e:
                    st.error(f"❌ Errore: {e}")

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
        with st.spinner("⏳ Compilazione PDF finale…"):
            latex_final = _reconstruct_latex(
                st.session_state.review_preamble,
                st.session_state.review_blocks
            )
            latex_final = fix_items_environment(latex_final)
            latex_final = rimuovi_vspace_corpo(latex_final)
            if mostra_punteggi:
                latex_final = rimuovi_punti_subsection(latex_final)
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

    st.markdown(
        '<div style="background:linear-gradient(135deg,' + T["accent_light"] + ' 0%,' + T["card"] + ' 100%);'
        'border:2px solid ' + T["success"] + ';border-radius:16px;overflow:hidden;margin-bottom:1.3rem;">'
        '<div style="background:linear-gradient(120deg,#059669 0%,#0284C7 100%);padding:.85rem 1.2rem;">'
        '<div style="display:flex;align-items:center;gap:12px;">'
        '<span style="font-size:1.5rem;">🎉</span>'
        '<div style="flex:1;">'
        '<div style="font-family:DM Sans,sans-serif;font-size:1rem;font-weight:900;color:#fff;'
        'text-shadow:0 1px 4px rgba(0,0,0,.2);">'
        'Verifica pronta!</div>'
        '<div style="font-size:.72rem;color:#fff;opacity:.9;margin-top:1px;">'
        + mat_str + ' · ' + scu_str + ' · ' + arg_str + '</div>'
        '</div></div></div>'
        '<div style="padding:.7rem 1.2rem;background:' + T["card"] + ';">'
        '<div style="display:flex;align-items:center;gap:8px;font-size:.78rem;color:' + T["text2"] + ';line-height:1.5;">'
        '<span style="font-size:1rem;">⚠️</span>'
        '<span>Controlla sempre il contenuto prima di distribuire agli studenti. '
        'Il docente è responsabile del materiale finale.</span>'
        '</div></div></div>',
        unsafe_allow_html=True
    )

    # ── Badge timer + risparmio tempo ────────────────────────────────────────
    _gen_sec = st.session_state.get("gen_time_sec")
    _n_es    = gp.get("num_esercizi", 4)
    _risparmio_min = max(10, _n_es * 8)  # ~8 min per esercizio fatto manualmente
    if _gen_sec:
        _t_label = (f"{_gen_sec}s" if _gen_sec < 60
                    else f"{_gen_sec // 60}m {_gen_sec % 60}s")
        st.markdown(
            f'<div style="display:flex;gap:.6rem;margin-bottom:1rem;flex-wrap:wrap;">'
            f'<div style="background:#0A2010;border:1px solid #1A4A28;border-radius:8px;'
            f'padding:.35rem .8rem;display:flex;align-items:center;gap:.4rem;">'
            f'<span style="font-size:.9rem;">⚡</span>'
            f'<span style="font-size:.75rem;font-weight:700;color:#34D399;'
            f'font-family:DM Sans,sans-serif;">Generata in {_t_label}</span>'
            f'</div>'
            f'<div style="background:#0A1A30;border:1px solid #1A3A5A;border-radius:8px;'
            f'padding:.35rem .8rem;display:flex;align-items:center;gap:.4rem;">'
            f'<span style="font-size:.9rem;">🕐</span>'
            f'<span style="font-size:.75rem;font-weight:700;color:#60AAEE;'
            f'font-family:DM Sans,sans-serif;">~{_risparmio_min} min risparmiati vs. manuale</span>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    # ── Pulsanti azione principali con gerarchia ──────────────────────────────
    st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)
    st.markdown(
        '<div class="s3-section-title">Azioni rapide</div>',
        unsafe_allow_html=True
    )

    # CSS pulsanti gerarchici
    st.markdown(
        f"""
        <style>
        /* Download PDF — bottone primario XXL */
        div[data-testid="stDownloadButton"] .dl-hero > button {{
            font-size:1.05rem!important; font-weight:900!important;
            padding:1rem 1.5rem!important; border-radius:14px!important;
            background:linear-gradient(135deg,{T["accent"]},{T["accent"]}cc)!important;
            box-shadow:0 6px 24px {T["accent"]}44!important;
            letter-spacing:.01em!important;
        }}
        /* Varianti — bottoni secondari */
        .btn-variant-row button {{
            font-weight:700!important;border-radius:10px!important;
            padding:.6rem .8rem!important;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

    # 1. Download PDF Principale — XXL hero button
    if vA.get("pdf"):
        _fname_a = arg_str + "_FilaA"
        st.markdown(
            f'<div style="background:linear-gradient(135deg,{T["accent"]}18,{T["card"]});'
            f'border:2px solid {T["accent"]}55;border-radius:16px;padding:1rem 1.2rem;'
            f'margin-bottom:.7rem;">'
            f'<div style="font-size:.72rem;font-weight:700;color:{T["accent"]};'
            f'font-family:DM Sans,sans-serif;letter-spacing:.06em;margin-bottom:.35rem;">'
            f'⬇ DOWNLOAD PRINCIPALE</div>',
            unsafe_allow_html=True
        )
        st.download_button(
            label=f"📄  Scarica Verifica PDF  ·  {_stima(vA['pdf'])}",
            data=vA["pdf"],
            file_name=_fname_a + ".pdf",
            mime="application/pdf",
            use_container_width=True,
            key="dl_pdf_hero_A",
        )
        st.markdown('</div>', unsafe_allow_html=True)

    # 2. Pulsanti varianti — riga prominente
    st.markdown(
        f'<div style="font-size:.72rem;font-weight:700;color:{T["muted"]};'
        f'font-family:DM Sans,sans-serif;letter-spacing:.05em;margin-bottom:.35rem;">'
        f'VARIANTI E AGGIUNTE</div>',
        unsafe_allow_html=True
    )
    _vcol1, _vcol2, _vcol3 = st.columns(3, gap="small")
    with _vcol1:
        _has_b = bool(vB.get("latex"))
        if _has_b:
            if vB.get("pdf"):
                st.download_button(
                    f"📄 Fila B · {_stima(vB['pdf'])}",
                    data=vB["pdf"], file_name=arg_str+"_FilaB.pdf",
                    mime="application/pdf", use_container_width=True, key="dl_pdf_B_action",
                )
        else:
            if st.button("⚡ Genera Fila B", use_container_width=True, key="gen_var_B_action",
                         help="Stessa struttura, dati diversi"):
                with st.spinner("Generazione Fila B…"):
                    try:
                        res = _genera_variante("B", mod_id, gp, vA)
                        st.session_state.verifiche["B"] = {**st.session_state.verifiche["B"], **res}
                        st.rerun()
                    except Exception as e:
                        st.error(f"Errore: {e}")
    with _vcol2:
        _has_r = bool(vR.get("latex"))
        if _has_r:
            if vR.get("pdf"):
                st.download_button(
                    f"🌟 BES/DSA · {_stima(vR['pdf'])}",
                    data=vR["pdf"], file_name=arg_str+"_BES_FilaA.pdf",
                    mime="application/pdf", use_container_width=True, key="dl_pdf_R_action",
                )
        else:
            if st.button("🌟 Genera BES/DSA", use_container_width=True, key="gen_var_R_action"):
                with st.spinner("Generazione BES/DSA…"):
                    try:
                        res = _genera_variante("R", mod_id, gp, vA)
                        st.session_state.verifiche["R"] = {**st.session_state.verifiche["R"], **res}
                        st.rerun()
                    except Exception as e:
                        st.error(f"Errore: {e}")
    with _vcol3:
        _has_s = bool(vS.get("pdf") or vS.get("testo"))
        if _has_s:
            if vS.get("pdf"):
                st.download_button(
                    f"✅ Soluzioni · {_stima(vS.get('pdf', b''))}",
                    data=vS["pdf"], file_name=arg_str+"_Soluzioni.pdf",
                    mime="application/pdf", use_container_width=True, key="dl_pdf_S_action",
                )
        else:
            if st.button("✅ Genera Soluzioni", use_container_width=True, key="gen_var_S_action"):
                with st.spinner("Generazione soluzioni…"):
                    try:
                        res = _genera_variante("S", mod_id, gp, vA)
                        st.session_state.verifiche["S"] = {**st.session_state.verifiche["S"], **res}
                        st.rerun()
                    except Exception as e:
                        st.error(f"Errore: {e}")

    # 3. Nuova verifica / Rivedi — riga secondaria
    st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)
    _nav_c1, _nav_c2 = st.columns([1, 1], gap="small")
    with _nav_c1:
        if st.button(
            "🆕 Nuova verifica",
            type="primary",
            use_container_width=True,
            key="btn_new_s3_top",
        ):
            st.session_state.stage            = STAGE_INPUT
            st.session_state["_prev_stage"]   = None
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
            st.session_state.esercizi_custom       = []
            st.session_state._saved_to_storico     = False
            st.session_state["_es_custom_da_file"] = {}
            st.session_state.rubrica_testo         = None
            st.session_state._rubrica_gen          = False
            st.session_state._template_sel         = None
            st.session_state._variant_rapida_gen   = False
            st.session_state["_facsimile_mode"]    = False
            st.rerun()
    with _nav_c2:
        if st.button("← Rivedi esercizi", use_container_width=True, key="btn_rev_s3_top"):
            st.session_state.stage = STAGE_REVIEW
            st.rerun()

    st.markdown("<div style='height:.8rem'></div>", unsafe_allow_html=True)
    _has_fila_b_already = bool(vB.get("latex"))
    if not _has_fila_b_already:
        st.markdown(
            f'<div class="one-click-variant-card">'
            f'  <div>'
            f'    <span class="one-click-badge">⚡ ONE-CLICK</span>'
            f'  </div>'
            f'  <div class="one-click-body">'
            f'    <div class="one-click-title">Genera Fila B istantaneamente</div>'
            f'    <div class="one-click-desc">'
            f'      Stessa struttura, stessi punteggi — solo i dati numerici cambiano. '
            f'      Pronto in secondi, nessuna configurazione richiesta.'
            f'    </div>'
            f'  </div>'
            f'</div>',
            unsafe_allow_html=True
        )
        if st.button(
            "⚡ Genera Fila B — One Click",
            key="one_click_variant_top",
            use_container_width=True,
            type="primary",
        ):
            st.session_state._variant_rapida_gen = True
            st.rerun()

        # Gestione generazione variante rapida
        if st.session_state.get("_variant_rapida_gen"):
            st.session_state._variant_rapida_gen = False
            _ocr_ph = st.empty()
            _ocr_ph.markdown(
                f'<div class="ocr-skeleton-wrap">'
                f'  <div class="ocr-skeleton-header">'
                f'    <div class="ocr-skeleton-icon">⚡</div>'
                f'    <div>'
                f'      <div class="ocr-skeleton-title">Generazione Fila B in corso…</div>'
                f'      <div class="ocr-skeleton-sub">Cambio dati numerici · Anti-spoiler grafico · QA coerenza</div>'
                f'    </div>'
                f'  </div>'
                f'  <div class="ocr-skeleton-doc">'
                f'    <div class="ocr-skeleton-scan"></div>'
                f'    <div class="ocr-skeleton-line" style="width:90%;animation-delay:.0s"></div>'
                f'    <div class="ocr-skeleton-line" style="width:70%;animation-delay:.2s"></div>'
                f'    <div class="ocr-skeleton-line" style="width:85%;animation-delay:.4s"></div>'
                f'  </div>'
                f'</div>',
                unsafe_allow_html=True
            )
            try:
                _mod_obj_vr = genai.GenerativeModel(mod_id)
                _latex_a    = vA.get("latex", "")
                _prmpt_vr   = prompt_variante_rapida(_latex_a, mat_str)
                _resp_vr    = _mod_obj_vr.generate_content(
                    [_prmpt_vr],
                    generation_config=genai.GenerationConfig(temperature=0.7),
                )
                _latex_b_new = _resp_vr.text.strip()
                # Rimuovi eventuali backtick
                if _latex_b_new.startswith("```"):
                    _latex_b_new = re.sub(r"^```[a-z]*\n?", "", _latex_b_new)
                    _latex_b_new = re.sub(r"\n?```$", "", _latex_b_new)
                from latex_utils import compila_pdf as _cpdf
                _pdf_b_new, _ = _cpdf(_latex_b_new)
                st.session_state.verifiche["B"]["latex"] = _latex_b_new
                if _pdf_b_new:
                    st.session_state.verifiche["B"]["pdf"] = _pdf_b_new
                _ocr_ph.empty()
                st.toast("✅ Fila B generata!", icon="⚡")
                st.rerun()
            except Exception as _e_vr:
                _ocr_ph.empty()
                st.error(f"Errore generazione Fila B: {_e_vr}")

    else:
        # Fila B già generata — mostra badge
        st.markdown(
            f'<div style="display:inline-flex;align-items:center;gap:.5rem;'
            f'background:{T["success"]}18;border:1.5px solid {T["success"]}55;'
            f'border-radius:8px;padding:.35rem .85rem;margin-bottom:.7rem;'
            f'font-size:.78rem;font-weight:700;color:{T["success"]};font-family:DM Sans,sans-serif;">'
            f'✓ Fila B disponibile — vedi sezione download'
            f'</div>',
            unsafe_allow_html=True
        )

    # 1. PREVIEW
    st.markdown(
        '<div class="s3-section-title">Anteprima</div>',
        unsafe_allow_html=True
    )
    imgs = st.session_state.preview_images
    if imgs or vA.get("pdf"):
        with st.expander("Mostra anteprima PDF completo", expanded=True):
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
                    '<iframe src="data:application/pdf;base64,' + b64 + '#toolbar=0&navpanes=0&scrollbar=1" '
                    'style="width:100%;height:540px;border:none;border-radius:8px;"></iframe>',
                    unsafe_allow_html=True
                )
    else:
        st.info("Anteprima non disponibile.")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── DOWNLOAD SECTION ──────────────────────────────────────────────────────
    st.markdown(
        '<div class="s3-section-title">Scarica e condividi</div>',
        unsafe_allow_html=True
    )

    def _primary_card_unified(label_file, icon, fid, v, suffix, label_custom=None, is_primary=False):
        if not (v.get("latex") or v.get("pdf") or v.get("testo")):
            return
        fname = arg_str + "_" + suffix
        btn_label = label_custom if label_custom else f"Scarica {label_file} (PDF)"

        st.markdown(
            '<div class="s3-card-label">' + label_file + '</div>',
            unsafe_allow_html=True
        )

        # ── PDF ──────────────────────────────────────────────────────────────
        if v.get("pdf"):
            # Tutti i PDF primari usano il colore accent
            st.markdown('<div class="dl-accent-btn">', unsafe_allow_html=True)
            st.download_button(
                label=f"⬇  {btn_label} · {_stima(v['pdf'])}",
                data=v["pdf"], file_name=fname + ".pdf", mime="application/pdf",
                use_container_width=True, key="dl_pdf_" + fid,
            )
            st.markdown('</div>', unsafe_allow_html=True)
        elif v.get("latex"):
            if st.button(f"Compila PDF — {label_file}", key="gen_pdf_" + fid, use_container_width=True):
                with st.spinner("Compilazione…"):
                    pdf_b, _ = compila_pdf(v["latex"])
                if pdf_b:
                    st.session_state.verifiche[fid]["pdf"] = pdf_b
                    st.session_state.verifiche[fid]["pdf_ts"] = time.time()
                    st.rerun()
                else:
                    st.error("Errore PDF")

        # ── Anteprima soluzioni ───────────────────────────────────────────────
        if v.get("testo") and fid == "S":
            with st.expander("Mostra soluzioni"):
                st.markdown(v["testo"])

        # ── Altri formati (DOCX + .tex) ───────────────────────────────────────
        if v.get("latex"):
            with st.expander("Altri formati"):
                _docx_key = "_docx_gen_" + fid
                if v.get("docx"):
                    st.download_button(
                        "📝 Scarica Word · " + _stima(v["docx"]),
                        data=v["docx"], file_name=fname + ".docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True, key="dl_docx_" + fid
                    )
                else:
                    if st.button("📝 Genera Word (.docx)", key="gen_docx_" + fid, use_container_width=True):
                        st.session_state[_docx_key] = True
                    if st.session_state.get(_docx_key, False):
                        with st.spinner("Conversione Word…"):
                            db, de = latex_to_docx_via_ai(v["latex"], con_griglia=con_griglia)
                        st.session_state[_docx_key] = False
                        if db:
                            st.session_state.verifiche[fid]["docx"] = db; st.rerun()
                        else:
                            st.error("Errore Word")
                st.markdown('<div class="tex-btn-wrap">', unsafe_allow_html=True)
                st.download_button(
                    "⬇ Sorgente LaTeX (.tex)",
                    data=v["latex"].encode("utf-8"),
                    file_name=fname + ".tex", mime="text/plain",
                    key="dl_tex_" + fid,
                    help="Sorgente LaTeX per editor esterno",
                    use_container_width=True,
                )
                st.markdown('</div>', unsafe_allow_html=True)

    col_dl_left, col_dl_right = st.columns(2)
    with col_dl_left:
        _primary_card_unified("Verifica", "📄", "A", vA, "FilaA", "Scarica verifica (PDF)", is_primary=True)
        if vR.get("latex"):
            _primary_card_unified("BES / DSA — A", "🌟", "R", vR, "BES_FilaA", "Scarica BES/DSA (PDF)")
    with col_dl_right:
        if vB.get("latex"):
            _primary_card_unified("Verifica — Fila B", "📄", "B", vB, "FilaB", "Scarica Fila B (PDF)")
        if vRB.get("latex"):
            _primary_card_unified("BES / DSA — B", "🌟", "RB", vRB, "BES_FilaB", "Scarica BES/DSA Fila B (PDF)")
        if vS.get("pdf") or vS.get("testo"):
            _primary_card_unified("Soluzioni", "✅", "S", vS, "Soluzioni", "Scarica Soluzioni (PDF)")


    # ── IDEA #19: Rubrica di Valutazione AI ───────────────────────────────────
    st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)
    st.markdown(
        '<div class="s3-section-title">Rubrica di Valutazione</div>',
        unsafe_allow_html=True
    )

    _punti_tot_r = gp.get("punti_totali", 100)
    _latex_a_r   = vA.get("latex", "")

    if st.session_state.rubrica_testo:
        # Rubrica già generata — mostrala
        # Inline markdown → HTML (no external 'markdown' package needed)
        def _md_to_html(text: str) -> str:
            import re as _re
            t = text
            # Headers
            t = _re.sub(r'^### (.+)$', r'<h3>\1</h3>', t, flags=_re.MULTILINE)
            t = _re.sub(r'^## (.+)$',  r'<h2>\1</h2>', t, flags=_re.MULTILINE)
            t = _re.sub(r'^# (.+)$',   r'<h1>\1</h1>', t, flags=_re.MULTILINE)
            # Bold / italic
            t = _re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', t)
            t = _re.sub(r'\*(.+?)\*',     r'<em>\1</em>', t)
            # Tables: detect lines with |
            lines = t.split('\n')
            out = []
            in_table = False
            for line in lines:
                if '|' in line and line.strip().startswith('|'):
                    cells = [c.strip() for c in line.strip().strip('|').split('|')]
                    if not in_table:
                        out.append('<table style="width:100%;border-collapse:collapse;font-size:.8rem;">')
                        in_table = True
                    if all(set(c) <= set('-: ') for c in cells):
                        continue  # separator row
                    row = ''.join(f'<td style="border:1px solid #444;padding:4px 8px;">{c}</td>'
                                  for c in cells)
                    out.append(f'<tr>{row}</tr>')
                else:
                    if in_table:
                        out.append('</table>')
                        in_table = False
                    out.append(line)
            if in_table:
                out.append('</table>')
            t = '\n'.join(out)
            # Paragraphs
            t = _re.sub(r'\n\n+', '</p><p>', t)
            return '<p>' + t + '</p>'

        try:
            _rubrica_html = _md_to_html(st.session_state.rubrica_testo)
        except Exception:
            _rubrica_html = st.session_state.rubrica_testo.replace("\n", "<br>")

        st.markdown(
            f'<div class="rubrica-wrap">'
            f'  <div class="rubrica-header">'
            f'    <span style="font-size:1.1rem;">📊</span>'
            f'    <div class="rubrica-title">Rubrica di Valutazione</div>'
            f'    <span class="rubrica-badge">MIM — per competenze</span>'
            f'  </div>'
            f'  <div class="rubrica-content">{_rubrica_html}</div>'
            f'</div>',
            unsafe_allow_html=True
        )
        _col_r1, _col_r2 = st.columns([2, 1])
        with _col_r1:
            st.download_button(
                "⬇ Scarica rubrica (.txt)",
                data=st.session_state.rubrica_testo.encode("utf-8"),
                file_name=arg_str + "_Rubrica.txt",
                mime="text/plain",
                key="dl_rubrica_txt",
                use_container_width=True,
            )
        with _col_r2:
            if st.button("🔄 Rigenera", key="btn_rigenera_rubrica", use_container_width=True):
                st.session_state.rubrica_testo = None
                st.session_state._rubrica_gen  = False
                st.rerun()
    else:
        # Rubrica non ancora generata
        st.markdown(
            f'<div style="background:{T["card2"]};border:1px solid {T["border"]};'
            f'border-radius:10px;padding:.7rem 1rem;margin-bottom:.6rem;'
            f'font-size:.78rem;color:{T["text2"]};font-family:DM Sans,sans-serif;line-height:1.55;">'
            f'<strong style="color:{T["text"]};">Genera automaticamente</strong> una rubrica di valutazione '
            f'con indicatori qualitativi per fascia di voto, allineata alle Linee Guida MIM '
            f'sulla valutazione per competenze.'
            f'</div>',
            unsafe_allow_html=True
        )
        if st.button(
            "📊 Genera Rubrica di Valutazione",
            key="btn_gen_rubrica",
            use_container_width=True,
        ):
            st.session_state._rubrica_gen = True
            st.rerun()

        if st.session_state.get("_rubrica_gen"):
            st.session_state._rubrica_gen = False
            _rub_ph = st.empty()
            _rub_ph.markdown(
                f'<div class="ocr-skeleton-wrap">'
                f'  <div class="ocr-skeleton-header">'
                f'    <div class="ocr-skeleton-icon">📊</div>'
                f'    <div>'
                f'      <div class="ocr-skeleton-title">Generazione rubrica in corso…</div>'
                f'      <div class="ocr-skeleton-sub">Analisi esercizi · Fasce di voto · Indicatori MIM</div>'
                f'    </div>'
                f'  </div>'
                f'  <div class="ocr-skeleton-doc">'
                f'    <div class="ocr-skeleton-scan"></div>'
                f'    <div class="ocr-skeleton-line" style="width:88%"></div>'
                f'    <div class="ocr-skeleton-line" style="width:65%"></div>'
                f'    <div class="ocr-skeleton-line" style="width:80%"></div>'
                f'  </div>'
                f'</div>',
                unsafe_allow_html=True
            )
            try:
                _mod_rub = genai.GenerativeModel(mod_id)
                _prompt_rub = prompt_rubrica_valutazione(
                    corpo_latex=_latex_a_r,
                    materia=mat_str,
                    livello=scu_str,
                    punti_totali=_punti_tot_r,
                )
                _resp_rub = _mod_rub.generate_content(
                    [_prompt_rub],
                    generation_config=genai.GenerationConfig(temperature=0.5),
                )
                st.session_state.rubrica_testo = _resp_rub.text.strip()
                _rub_ph.empty()
                st.toast("✅ Rubrica generata!", icon="📊")
                st.rerun()
            except Exception as _e_rub:
                _rub_ph.empty()
                st.error(f"Errore generazione rubrica: {_e_rub}")

    # ── Genera Varianti on-demand (altri formati / docx) ─────────────────────
    # I pulsanti principali varianti sono già nella sezione Azioni Rapide sopra.
    # Qui mostriamo gli altri formati download (DOCX, .tex) se disponibili.

    # ── Pulsanti di navigazione ────────────────────────────────────────────────
    # (già presenti nella sezione Azioni Rapide)

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


# ═══════════════════════════════════════════════════════════════════════════════
#  ROUTING
# ═══════════════════════════════════════════════════════════════════════════════

_render_breadcrumb()

# ── SCROLL TO TOP on stage change ─────────────────────────────────────────────
_current_stage = st.session_state.stage
_prev_stage = st.session_state.get("_prev_stage", None)
if _prev_stage != _current_stage:
    st.session_state["_prev_stage"] = _current_stage
    components.html(
        "<script>"
        "(function(){"
        "var tries=0;"
        "function scroll(){"
        "  var m=window.parent.document.querySelector('.main');"
        "  if(m){m.scrollTop=0;}"
        "  var a=window.parent.document.querySelector('[data-testid=\"stAppViewContainer\"]');"
        "  if(a){a.scrollTop=0;}"
        "  window.parent.scrollTo(0,0);"
        "  if(tries++<5)setTimeout(scroll,80);"
        "}"
        "scroll();"
        "})();"
        "</script>",
        height=0
    )

_current = _current_stage
if   _current == STAGE_INPUT:   _render_stage_input()
elif _current == STAGE_PREVIEW: _render_stage_preview()
elif _current == STAGE_REVIEW:  _render_stage_review()
elif _current == STAGE_FINAL:   _render_stage_final()


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
