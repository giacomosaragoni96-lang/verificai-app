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


def _scroll_to_top():
    """Forza scroll-to-top con JS multi-selettore — chiamare all'inizio di ogni stage render."""
    components.html(
        "<script>"
        "(function(){"
        "var n=0;"
        "function top(){"
        "  var sels=['[data-testid=\"stMainBlockContainer\"]',"
        "    '[data-testid=\"stAppViewContainer\"]',"
        "    '.stMainBlockContainer','.main','section.main'];"
        "  sels.forEach(function(s){"
        "    var el=window.parent.document.querySelector(s);"
        "    if(el){el.scrollTop=0;el.scrollTo({top:0,behavior:'instant'});}"
        "  });"
        "  window.parent.scrollTo({top:0,behavior:'instant'});"
        "  if(n++<10)setTimeout(top,50);"
        "}"
        "top();"
        "})();"
        "</script>",
        height=1
    )


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


# Pattern regex per rilevare richieste di modifica punteggi.
# Usa \b (word-boundary) per evitare falsi positivi come "sottopunto" che contiene "punto".
_SCORE_PATTERN = re.compile(
    r'\b(punti|punteggio|punteggi|punto|voto|voti|score|valutazione|peso)\b'
    r'|\b\d+\s*pt\b'
    r'|(?<!\w)%(?!\w)',
    re.IGNORECASE
)


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
# ── Idea #1: Preferenze silenti (materia, scuola, num_esercizi, punteggi) ────
if "_user_defaults"       not in st.session_state: st.session_state._user_defaults = None
if "_user_defaults_loaded" not in st.session_state: st.session_state._user_defaults_loaded = False
# ── Idea #5: Condivisione con dipartimento ──────────────────────────────────
if "_share_code"          not in st.session_state: st.session_state._share_code = None
if "_share_generating"    not in st.session_state: st.session_state._share_generating = False
# ── Idea #3: Quick regen state ──────────────────────────────────────────────
if "_quick_regen_idx"     not in st.session_state: st.session_state._quick_regen_idx = None
if "_facsimile_mode"      not in st.session_state: st.session_state["_facsimile_mode"] = False
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

# ── CSS + FEEDBACK ────────────────────────────────────────────────────────────
st.markdown(get_css(T), unsafe_allow_html=True)
# Anchor invisibile all'inizio della pagina — usato come target per scroll-to-top
st.markdown('<div id="verificai-top" style="position:absolute;top:0;left:0;height:0;width:0;"></div>',
            unsafe_allow_html=True)
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

# ── HINT SIDEBAR MINIMALE (solo fuori dalla landing) ─────────────────────────
_on_landing = (
    st.session_state.stage == STAGE_INPUT
    and st.session_state.get("input_percorso") is None
)
if not _on_landing:
    st.markdown(
        '<div class="hero-wrap"><div class="hero-left">'
        '<h1 class="hero-title">'
        '<span class="hero-icon">' + APP_ICON + '</span>'
        ' Verific<span class="hero-ai">AI</span>'
        '</h1>'
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
    # ── 3-step progress: Impostazioni → Revisione → Scarica ──
    steps = [
        ("01", "Impostazioni", STAGE_INPUT),
        ("02", "Revisione",    STAGE_REVIEW),
        ("03", "Scarica",      STAGE_FINAL),
    ]
    # Map PREVIEW → same visual as INPUT (still in step 1 → 2 transition)
    _visual_stage = STAGE_REVIEW if stage == STAGE_PREVIEW else stage
    completed = {
        STAGE_INPUT:  _visual_stage in (STAGE_REVIEW, STAGE_FINAL),
        STAGE_REVIEW: _visual_stage == STAGE_FINAL,
        STAGE_FINAL:  False,
    }
    # ── Pill container
    html = (
        '<div class="breadcrumb-wrap">'
        '<div class="breadcrumb-pill" style="display:inline-flex;align-items:center;gap:10px;'
        'padding:.7rem 1.6rem;'
        'background:' + T["card"] + ';border:1.5px solid ' + T["border"] + ';'
        'border-radius:100px;box-shadow:' + T.get("shadow_md", "0 4px 20px rgba(0,0,0,.08)") + ';">'
    )
    for i, (num, label, s) in enumerate(steps):
        is_active = s == _visual_stage
        is_done   = completed.get(s, False)
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
        if i < len(steps) - 1:
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
    except Exception:
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
    except Exception:
        pass


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
    except Exception:
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
    Home page: logo + titolo MOLTO GRANDE centrato, un solo CTA.
    """

    # ── Logo + headline unificati, tutto centrato ─────────────────────────────
    st.markdown(
        f'''
        <div class="landing-hero-unified">
          <div class="landing-logo-row">
            <span class="landing-logo-icon-xl">{APP_ICON}</span>
            <span class="landing-logo-name-xl">Verific<span class="landing-logo-ai-xl">AI</span></span>
            <span class="landing-logo-beta-xl">Beta</span>
          </div>
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

    # ── CTA unico — centrato ─────────────────────────────────────────────────
    _c1, _c2, _c3 = st.columns([1.4, 2, 1.4])
    with _c2:
        if st.button(
            "Genera Verifica  →",
            key="btn_genera_verifica_home",
            use_container_width=True,
            type="primary",
        ):
            st.session_state.input_percorso = "B"
            st.rerun()

    # ── Feature chips ─────────────────────────────────────────────────────────
    st.markdown(
        f'''
        <div class="tally-features">
          <span class="tally-feat">📄 PDF pronto da stampare</span>
          <span class="tally-feat-sep">·</span>
          <span class="tally-feat">🔢 Punteggi calibrati</span>
          <span class="tally-feat-sep">·</span>
          <span class="tally-feat">⭐ Versione BES/DSA</span>
          <span class="tally-feat-sep">·</span>
          <span class="tally-feat">🎲 Fila A e B</span>
          <span class="tally-feat-sep">·</span>
          <span class="tally-feat">✏️ DOCX modificabile</span>
        </div>
        ''',
        unsafe_allow_html=True,
    )

# ═══════════════════════════════════════════════════════════════════════════════
#  _render_facsimile_dedicato()  ← NUOVA funzione, aggiungere prima di _render_stage_input
# ═══════════════════════════════════════════════════════════════════════════════


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
                    f'<div class="ocr-skeleton-wrap">' +
                    f'  <div class="ocr-skeleton-header">' +
                    f'    <div class="ocr-skeleton-icon">🔬</div>' +
                    f'    <div>' +
                    f'      <div class="ocr-skeleton-title">Analisi AI in corso…</div>' +
                    f'      <div class="ocr-skeleton-sub">Lettura · Riconoscimento · Classificazione</div>' +
                    f'    </div>' +
                    f'  </div>' +
                    f'  <div class="ocr-skeleton-doc">' +
                    f'    <div class="ocr-skeleton-scan"></div>' +
                    f'    <div class="ocr-skeleton-line" style="width:88%"></div>' +
                    f'    <div class="ocr-skeleton-line" style="width:72%"></div>' +
                    f'    <div class="ocr-skeleton-line" style="width:91%"></div>' +
                    f'  </div></div>',
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
        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
        _bbc1, _bbc2, _bbc3 = st.columns([3, 2, 3])
        with _bbc2:
            if st.button("← Cambia percorso", key="btn_back_wiz_upload",
                         use_container_width=True):
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
        _ic1, _ic2 = st.columns([3, 1], gap="small")
        with _ic1:
            _can_confirm = True
            if _sel_intent == "custom" and not _custom_istr:
                _can_confirm = False
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
        with _ic2:
            if st.button("← Indietro", key="wiz_intent_back",
                         use_container_width=True):
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
            st.markdown('<div class="opt-label">Argomento della verifica</div>', unsafe_allow_html=True)
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
                    st.markdown('<div class="opt-label">Materia</div>', unsafe_allow_html=True)
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
                    st.markdown('<div class="opt-label">Tipo di scuola</div>', unsafe_allow_html=True)
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
            st.markdown('<div class="opt-label">N° esercizi</div>', unsafe_allow_html=True)
            num_esercizi = st.selectbox(
                "N° esercizi", options=_es_opts, index=_es_idx_r,
                label_visibility="collapsed", key="rev_num_es",
                format_func=lambda x: f"{x} eserc.",
            )
        with _rp2:
            st.markdown('<div class="opt-label">Punti totali</div>', unsafe_allow_html=True)
            _pt_opts = list(range(10, 105, 5))
            punti_totali = st.selectbox(
                "Punti", options=_pt_opts,
                index=_pt_opts.index(100) if 100 in _pt_opts else len(_pt_opts)-1,
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
        genera_btn = st.button(
            "🚀  Genera Bozza",
            use_container_width=True,
            type="primary",
            disabled=_limite or _manca_ancora,
            key="rev_genera_btn",
        )
        if _manca_ancora and not _limite:
            st.markdown(
                f'<div style="font-size:.75rem;color:{T["warn"]};text-align:center;margin-top:.3rem;">' +
                f'Inserisci l\'argomento per continuare.</div>',
                unsafe_allow_html=True
            )
        if _limite:
            st.markdown(
                '<div style="text-align:center;font-size:.82rem;color:#EF4444;margin-top:.4rem;">' +
                '⛔ Limite mensile raggiunto.</div>',
                unsafe_allow_html=True
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


def _render_percorso_b_form():
    """
    Percorso B — Layout a due colonne (3:1):
    ┌─────────────────────────────────┬────────────────┐
    │  IL PROGETTO (col. principale)  │  MATERIALE     │
    │  Materia · Scuola · Argomento  │  Facsimile     │
    │  N° Esercizi · Note             │  Uploader      │
    │  ─────────────────────────────  │  File Recap    │
    │  🚀 GENERA BOZZA                │                │
    └─────────────────────────────────┴────────────────┘
    """

    # ── Onboarding hint banner (full width) ───────────────────────────────────
    st.markdown(
        f'<div class="onboarding-hint-banner">'
        f'<div class="onboarding-hint-icon">💡</div>'
        f'<div class="onboarding-hint-body">'
        f'<div class="onboarding-hint-title">'
        f'Più dettagli fornisci, più la verifica rispecchierà le tue aspettative'
        f'</div>'
        f'<div class="onboarding-hint-desc">'
        f'Specifica l\'argomento con esempi concreti, scegli il tipo di scuola '
        f'e — se vuoi — allega materiale nella colonna destra. '
        f'<strong>Potrai sempre modificare i singoli esercizi generati.</strong>'
        f'</div>'
        f'<div class="onboarding-hint-tags">'
        f'<span class="onboarding-hint-tag">✏️ Modifica ogni esercizio</span>'
        f'<span class="onboarding-hint-tag">📐 Punteggi automatici</span>'
        f'<span class="onboarding-hint-tag">📄 Export PDF + DOCX</span>'
        f'</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Due colonne: 3 (form) + 1 (materiale) ────────────────────────────────
    col_main, col_side = st.columns([3, 1], gap="large")

    # ═════════════════════════════════════════════════════════════════════════
    #  COLONNA SINISTRA — IL PROGETTO
    # ═════════════════════════════════════════════════════════════════════════
    with col_main:

        _prev = st.session_state.gen_params or {}
        # ── IDEA #1: carica defaults silenti come fallback ────────────────
        _udef = _load_user_defaults()

        # ── Section header: Materia & Scuola ──────────────────────────────────
        st.markdown(
            f'<div class="form-section-header">'
            f'<div class="form-section-dot"></div>'
            f'<span class="form-section-title">Materia e tipo di scuola</span>'
            f'<div class="form-section-line"></div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        _col_m, _col_s = st.columns(2, gap="small")
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

        # ── Section header: Argomento ─────────────────────────────────────────
        st.markdown(
            f'<div class="form-section-header" style="margin-top:1.4rem;">'
            f'<div class="form-section-dot"></div>'
            f'<span class="form-section-title">Argomento della verifica</span>'
            f'<div class="form-section-line"></div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Badge auto-rilevato se argomento viene dai file
        _auto_arg = _info_cons.get("contenuto_argomento", "")
        _arg_source = st.session_state.get("_pb_argomento_source")
        if _auto_arg and _arg_source != "manual":
            st.markdown(
                f'<div class="context-sync-badge">'
                f'✅ Argomento rilevato dal file caricato'
                f'</div>',
                unsafe_allow_html=True,
            )

        # Valore default: argomento dai file (se non già modificato manualmente)
        _arg_default = ""
        if _arg_source == "manual":
            _arg_default = st.session_state.get("_pb_argomento_manual_val", "")
        elif _auto_arg:
            _arg_default = _auto_arg

        st.markdown('<div class="argomento-field-wrap">', unsafe_allow_html=True)
        argomento_raw = st.text_area(
            "argomento",
            value=_arg_default,
            placeholder="es. Equazioni di secondo grado\nes. La Rivoluzione Francese\nes. Il ciclo dell'acqua",
            height=105,
            label_visibility="collapsed",
            key="argomento_area_b",
        )
        st.markdown('</div>', unsafe_allow_html=True)

        # Traccia se l'utente ha modificato manualmente l'argomento
        argomento = argomento_raw.strip()
        if argomento and argomento != _auto_arg:
            st.session_state["_pb_argomento_source"] = "manual"
            st.session_state["_pb_argomento_manual_val"] = argomento
        elif not argomento and _arg_source == "manual":
            st.session_state["_pb_argomento_source"] = None

        # ── Personalizzazione Avanzata (num esercizi + note + punteggi + struttura) ──
        _prefs = st.session_state._docente_prefs.get(materia_scelta, {})
        if not _prefs and st.session_state.utente and materia_scelta in MATERIE:
            _prefs = _carica_docente_preferenze(st.session_state.utente.id, materia_scelta)
            st.session_state._docente_prefs[materia_scelta] = _prefs

        st.markdown('<div class="personalizza-wrap">', unsafe_allow_html=True)
        with st.expander("⚙️ Personalizzazione Avanzata", expanded=False):
            if _prefs.get("stile_desc"):
                st.markdown(
                    f'<div style="background:{T["hint_bg"]};border:1px solid {T["hint_border"]};'
                    f'border-radius:8px;padding:.4rem .7rem;font-size:.78rem;color:{T["hint_text"]};'
                    f'font-family:DM Sans,sans-serif;margin-bottom:.6rem;">'
                    f'✨ Preferenze salvate per <b>{materia_scelta}</b>: {_prefs["stile_desc"]}'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            # ── Numero di esercizi ─────────────────────────────────────────
            st.markdown(
                f'<div class="form-section-header" style="margin-top:.4rem;">'
                f'<div class="form-section-dot"></div>'
                f'<span class="form-section-title">Numero di esercizi</span>'
                f'<div class="form-section-line"></div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            _n_default = _udef.get("num_esercizi", 4)
            if _info_cons.get("num_esercizi_rilevati"):
                try:
                    _n_default = max(1, min(int(_info_cons["num_esercizi_rilevati"]), 15))
                except (ValueError, TypeError):
                    pass
            num_esercizi = st.slider(
                "Numero esercizi",
                min_value=1, max_value=15, value=_n_default,
                label_visibility="collapsed", key="sel_num_es_b",
            )

            # ── Note libere per l'AI ───────────────────────────────────────
            st.markdown(
                f'<div class="form-section-header" style="margin-top:.9rem;">'
                f'<div class="form-section-dot" style="background:{T["muted"]};'
                f'box-shadow:none;opacity:.6;"></div>'
                f'<span class="form-section-title" style="color:{T["muted"]};">'
                f'Note per l\'AI <span style="font-weight:400;letter-spacing:0;">'
                f'— opzionale</span></span>'
                f'<div class="form-section-line" style="background:linear-gradient(90deg,'
                f'{T["border"]} 0%,transparent 100%);"></div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            st.markdown('<div class="note-field-wrap">', unsafe_allow_html=True)
            note_extra = st.text_area(
                "Note AI",
                placeholder=NOTE_PLACEHOLDER.get(materia_scelta, ""),
                height=72,
                label_visibility="collapsed",
                key="note_area_b",
            )
            st.markdown('</div>', unsafe_allow_html=True)

            # ── Punteggi ──────────────────────────────────────────────────
            _tog = st.toggle(
                "Aggiungi punteggi e tabella punteggi",
                value=_udef.get("mostra_punteggi", True), key="toggle_punteggi_b",
            )
            mostra_punteggi = _tog
            con_griglia = _tog
            punti_totali = 100
            if _tog:
                _pt_opts = list(range(10, 105, 5))
                _pt_saved = _udef.get("punti_totali", 100)
                _pt_idx  = _pt_opts.index(_pt_saved) if _pt_saved in _pt_opts else (_pt_opts.index(100) if 100 in _pt_opts else len(_pt_opts) - 1)
                st.markdown('<div class="opt-label">Punti totali</div>', unsafe_allow_html=True)
                punti_totali = st.selectbox(
                    "Punti totali", options=_pt_opts, index=_pt_idx,
                    label_visibility="collapsed", key="sel_punti_b",
                    format_func=lambda x: f"{x} pt",
                )

            # Struttura esercizi custom
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

        st.markdown('</div>', unsafe_allow_html=True)

        # ── CTA: Genera Bozza ─────────────────────────────────────────────────
        _manca_arg = not argomento
        st.markdown("<div style='height:.9rem'></div>", unsafe_allow_html=True)

        # Hint SOPRA il pulsante
        if not _manca_arg and not _limite:
            st.markdown(
                f'<div class="cta-hint-above">'
                f'<span>✏️</span>'
                f'<span>Potrai modificare ogni singolo esercizio dopo la generazione</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

        st.markdown('<div class="cta-genera-wrap">', unsafe_allow_html=True)
        genera_btn = st.button(
            "🚀  Genera Bozza",
            use_container_width=True,
            type="primary",
            disabled=_limite or _manca_arg,
            key="genera_btn_b",
        )
        st.markdown('</div>', unsafe_allow_html=True)

        # Placeholder progress bar — apparirà subito sotto il pulsante
        _prog_placeholder = st.empty()

        if _manca_arg and not _limite:
            st.markdown(
                f'<div style="text-align:center;font-size:.82rem;color:{T["warn"]};'
                f'font-family:DM Sans,sans-serif;margin-top:.3rem;">'
                f'Inserisci l\'argomento per continuare.</div>',
                unsafe_allow_html=True,
            )
        if _limite:
            st.markdown(
                f'<div style="text-align:center;font-size:.82rem;color:#EF4444;'
                f'font-family:DM Sans,sans-serif;font-weight:600;margin-top:.4rem;">'
                f'⛔ Limite mensile raggiunto.</div>',
                unsafe_allow_html=True,
            )

    # ── Back link — piccolo e in fondo ────────────────────────────────────────
    st.markdown("<div style='height:2.5rem'></div>", unsafe_allow_html=True)
    _bk1, _bk2, _bk3 = st.columns([2, 1, 2])
    with _bk2:
        if st.button("← Indietro", key="btn_back_b", use_container_width=True):
            st.session_state.input_percorso = None
            st.rerun()

    # ═════════════════════════════════════════════════════════════════════════
    #  COLONNA DESTRA — MATERIALE & UPLOAD
    # ═════════════════════════════════════════════════════════════════════════
    with col_side:
        _lista_b = st.session_state.analisi_docs_list

        # ── Box 1: Facsimile shortcut (solo se nessun file) ──────────────────
        if not _lista_b:
            st.markdown(
                f'<div class="side-box">'
                f'  <div class="side-box-header">'
                f'    <span class="side-box-badge side-box-badge-violet">⚡ RAPIDO</span>'
                f'  </div>'
                f'  <div class="side-box-title">Hai già una verifica da replicare?</div>'
                f'  <div class="side-box-desc">'
                f'Carica la verifica originale e ottieni una variante con dati nuovi '
                f'e stessa struttura. Senza compilare nessun campo.'
                f'  </div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            st.markdown('<div class="facsimile-shortcut-btn">', unsafe_allow_html=True)
            if st.button("⚡ Crea Facsimile", key="btn_fac_shortcut",
                         use_container_width=True):
                st.session_state.input_percorso = "FACSIMILE"
                st.session_state["_analisi_rifiuto"] = None
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)

        # ── Box 2: Materiale di studio + upload ──────────────────────────────
        st.markdown(
            f'<div class="side-box">'
            f'  <div class="side-box-title side-box-title-flex">'
            f'    <span class="side-box-dot"></span>'
            f'    Materiale di studio'
            f'  </div>'
            f'  <div class="side-box-desc">'
            f'✍️ Inserisci verifiche, appunti, foto a mano o PDF. '
            f"L'IA riconosce perfettamente la tua scrittura!"
            f'  </div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Uploader (chiave dinamica per forzare reset dopo aggiunta)
        _upload_key_b = f"pb_file_up_{len(_lista_b)}"
        st.markdown('<div class="file-uploader-compact">', unsafe_allow_html=True)
        _file_b = st.file_uploader(
            "Inserisci materiale",
            type=["pdf", "png", "jpg", "jpeg"],
            key=_upload_key_b,
            label_visibility="collapsed",
            help="PDF, immagini, foto di appunti. Puoi aggiungerne più di uno.",
        )
        st.markdown('</div>', unsafe_allow_html=True)

        if _file_b:
            _fb_bytes = _file_b.getvalue()
            _fb_hash  = hash(_fb_bytes)
            _existing_b = {d["file_hash"] for d in _lista_b}
            if _fb_hash not in _existing_b:
                _ph_b = st.empty()
                _ph_b.markdown(
                    f'<div class="ocr-skeleton-wrap">'
                    f'  <div class="ocr-skeleton-header">'
                    f'    <div class="ocr-skeleton-icon">🔬</div>'
                    f'    <div>'
                    f'      <div class="ocr-skeleton-title">Analisi AI…</div>'
                    f'      <div class="ocr-skeleton-sub">Lettura · Classificazione</div>'
                    f'    </div>'
                    f'  </div>'
                    f'  <div class="ocr-skeleton-doc">'
                    f'    <div class="ocr-skeleton-scan"></div>'
                    f'    <div class="ocr-skeleton-line" style="width:90%"></div>'
                    f'    <div class="ocr-skeleton-line" style="width:70%"></div>'
                    f'  </div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                st.session_state.file_ispirazione = _file_b
                _esegui_analisi_documento(_fb_bytes, _file_b.type or "image/png", _file_b.name)
                _ph_b.empty()
                # Auto-sync argomento se non già inserito manualmente
                if st.session_state.get("_pb_argomento_source") != "manual":
                    st.session_state["_pb_argomento_source"] = None  # refresh da info_consolidate
            else:
                st.info("File già presente nel pool.", icon="ℹ️")

        # ── Recap file caricati ───────────────────────────────────────────────
        if _lista_b:
            st.markdown("<div style='height:.3rem'></div>", unsafe_allow_html=True)
            st.markdown(
                f'<div style="font-size:.7rem;font-weight:700;letter-spacing:.07em;'
                f'text-transform:uppercase;color:{T["muted"]};font-family:DM Sans,sans-serif;'
                f'margin-bottom:.4rem;">'
                f'File nel pool ({len(_lista_b)})'
                f'</div>',
                unsafe_allow_html=True,
            )

            _MODO_OPTIONS = {
                "base_conoscenza":    "📚 Fonte di studio",
                "includi_esercizio":  "✏️ Esercizio da inserire",
            }
            _TIPO_ICONS = {
                "verifica": "📋", "appunti": "📒",
                "libro": "📚", "misto": "📄",
                "esercizi_sciolti": "📝", "esercizio_singolo": "✏️",
            }
            _TIPO_BADGE_CLASS = {
                "verifica": "file-item-b-badge-verifica",
                "appunti":  "file-item-b-badge-appunti",
            }

            _rimuovi_idx = None
            for _fi, _fentry in enumerate(_lista_b):
                _fhash_str = str(_fentry["file_hash"])
                _fanalisi  = _fentry.get("analisi", {})
                _ftipo     = _fanalisi.get("tipo_documento", "altro")
                _fbadge_c  = _TIPO_BADGE_CLASS.get(_ftipo, "file-item-b-badge-altro")
                _ficon     = _TIPO_ICONS.get(_ftipo, "📄")
                _ftipo_lbl = _ftipo.replace("_", " ").title()

                st.markdown(
                    f'<div class="file-item-b">'
                    f'  <div class="file-item-b-header">'
                    f'    <span class="file-item-b-icon">{_ficon}</span>'
                    f'    <span class="file-item-b-name">{_fentry["file_name"][:28]}'
                    f'{"…" if len(_fentry["file_name"]) > 28 else ""}</span>'
                    f'    <span class="file-item-b-badge {_fbadge_c}">{_ftipo_lbl}</span>'
                    f'  </div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

                # ── Riepilogo analisi AI (cosa ha capito) ─────────────────────
                _fa = _fentry.get("analisi", {})
                _fa_mat = _fa.get("materia", "")
                _fa_arg = _fa.get("contenuto_argomento", "")
                _fa_es  = _fa.get("num_esercizi_rilevati")
                _fa_desc_parts = []
                if _fa_mat:
                    _fa_desc_parts.append(f"<strong>{_fa_mat}</strong>")
                if _fa_arg:
                    _fa_desc_parts.append(_fa_arg[:60] + ("…" if len(_fa_arg) > 60 else ""))
                if _fa_es:
                    _fa_desc_parts.append(f"{_fa_es} esercizi rilevati")
                if _fa_desc_parts:
                    st.markdown(
                        f'<div class="file-ai-summary">'
                        f'<span class="file-ai-summary-icon">🤖</span>'
                        f'<span class="file-ai-summary-text">{" · ".join(_fa_desc_parts)}</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

                # Dropdown: come usare il file
                _modo_prev = _fentry.get("file_mode", "base_conoscenza")
                # Normalizza vecchie modalità non più disponibili
                if _modo_prev not in _MODO_OPTIONS:
                    _modo_prev = "base_conoscenza"
                _modo_opts = list(_MODO_OPTIONS.keys())
                _modo_idx  = _modo_opts.index(_modo_prev)
                st.markdown(
                    f'<div class="file-item-b-mode-label">Come usarlo</div>',
                    unsafe_allow_html=True,
                )
                _sel_modo = st.selectbox(
                    f"Modalità uso file {_fi}",
                    options=_modo_opts,
                    index=_modo_idx,
                    format_func=lambda x: _MODO_OPTIONS[x],
                    key=f"pb_mode_{_fhash_str}",
                    label_visibility="collapsed",
                )
                # Aggiorna file_mode in lista
                if _sel_modo != _lista_b[_fi].get("file_mode"):
                    st.session_state.analisi_docs_list[_fi]["file_mode"] = _sel_modo
                    st.session_state.analisi_docs_list[_fi]["confirmed"] = (_sel_modo != "ignora")
                    _consolida_info()

                # ── Hint contestuale per "esercizio da inserire" ───────────────
                if _sel_modo == "includi_esercizio":
                    st.markdown(
                        f'<div class="file-includi-hint">'
                        f'📌 L\'AI inserirà questo esercizio come <strong>Esercizio 1</strong>. '
                        f'Nelle note sotto specifica se vuoi <strong>stessi dati</strong> '
                        f'o <strong>dati diversi</strong> (stessa struttura, numeri cambiati).'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

                # Istruzioni specifiche per il file (espandibile)
                _istr_prev = st.session_state.istruzioni_per_file.get(_fhash_str, "")
                _placeholder_istr = (
                    "es. Stessi dati, oppure: Cambia i valori numerici mantenendo la struttura…"
                    if _sel_modo == "includi_esercizio"
                    else "es. Usa solo il secondo esercizio…"
                )
                _istr_new  = st.text_area(
                    f"Istruzioni file {_fi}",
                    value=_istr_prev,
                    placeholder=_placeholder_istr,
                    height=56,
                    key=f"pb_istr_{_fhash_str}",
                    label_visibility="collapsed",
                )
                if _istr_new != _istr_prev:
                    st.session_state.istruzioni_per_file[_fhash_str] = _istr_new

                # Pulsante Rimuovi — discreto, in fondo alla card
                st.markdown('<div class="file-item-b-delete">', unsafe_allow_html=True)
                if st.button(f"✕ Rimuovi", key=f"pb_rm_{_fhash_str}_{_fi}",
                              use_container_width=True):
                    _rimuovi_idx = _fi
                st.markdown('</div>', unsafe_allow_html=True)

            # ── Gestione rimozione ────────────────────────────────────────────
            if _rimuovi_idx is not None:
                _rimosso = st.session_state.analisi_docs_list.pop(_rimuovi_idx)
                _rimosso_hash = _rimosso.get("file_hash")
                # Rimuovi istruzioni associate
                st.session_state.istruzioni_per_file.pop(str(_rimosso_hash), None)
                _consolida_info()
                # Reset argomento se era auto-rilevato da questo file
                if st.session_state.get("_pb_argomento_source") != "manual":
                    st.session_state["_pb_argomento_source"] = None
                    # Se non ci sono più file, pulisce l'argomento auto
                    if not st.session_state.analisi_docs_list:
                        st.session_state.info_consolidate = {}
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
    _n_steps = 4
    _step    = [0]
    # Usa il placeholder passato (vicino al pulsante) oppure crea uno nuovo
    _prog    = prog_placeholder if prog_placeholder is not None else st.empty()

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
    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    _fb1, _fb2, _fb3 = st.columns([2, 3, 2])
    with _fb2:
        st.markdown('<div class="btn-back-discrete">', unsafe_allow_html=True)
        if st.button("← Torna alla scelta percorso", key="btn_back_fac",
                     use_container_width=True):
            _reset_percorso()
            st.session_state.input_percorso = None
            st.session_state["_facsimile_mode"] = False
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)


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
    _scroll_to_top()
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
        # Centra e limita la larghezza delle immagini per non occupare tutto lo schermo
        _pc_l, _pc_m, _pc_r = st.columns([0.5, 3, 0.5])
        with _pc_m:
            if n_prev == 1:
                st.image(preview_imgs[0], use_container_width=True)
            else:
                st.image(preview_imgs[0], use_container_width=True, caption="Pagina 1")
                for _pi in range(1, n_prev, 2):
                    _pp1, _pp2 = st.columns(2, gap="small")
                    with _pp1:
                        st.image(preview_imgs[_pi], use_container_width=True,
                                 caption=f"Pagina {_pi + 1}")
                    with _pp2:
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
    _scroll_to_top()
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

            # ── IDEA #3: Variante rapida / Esercizio diverso ──────────────
            st.markdown(
                '<div class="quick-regen-row">'
                '<div class="quick-regen-label">'
                '🔄 <strong>Modifica veloce</strong>'
                '<span class="quick-regen-hint">'
                '<b>Cambia i dati</b>: stessa struttura, numeri diversi &nbsp;·&nbsp; '
                '<b>Esercizio diverso</b>: stessa difficoltà, approccio nuovo'
                '</span>'
                '</div>'
                '</div>',
                unsafe_allow_html=True
            )
            _qr_col1, _qr_col2 = st.columns(2, gap="small")
            with _qr_col1:
                quick_regen = st.button(
                    "🔄 Cambia i dati",
                    key=f"quick_regen_{idx}",
                    use_container_width=True,
                    help="Stessa struttura e difficoltà, solo i dati numerici cambiano",
                )
            with _qr_col2:
                cambia_esercizio = st.button(
                    "🎯 Esercizio diverso",
                    key=f"cambia_es_{idx}",
                    use_container_width=True,
                    help="Stesso argomento e difficoltà, struttura completamente diversa",
                )
            # Placeholder per feedback veloce (rimane nella colonna sinistra)
            _qr_status_ph = st.empty()

            st.markdown("<div style='height:.4rem'></div>", unsafe_allow_html=True)

            # ── Expander: Modifica con AI ──────────────────────────────────────
            with st.expander("✏️ Modifica con AI", expanded=False):
                st.markdown(
                    '<div style="font-size:.76rem;color:' + T["text2"] + ';margin-bottom:.5rem;'
                    'font-family:DM Sans,sans-serif;line-height:1.45;">'
                    'Descrivi la modifica — l\'AI rigenererà solo questo esercizio.<br>'
                    '<span style="color:' + T["muted"] + ';font-size:.7rem;">'
                    '⚠️ Per cambiare i <strong>punteggi</strong> usa il pannello <em>⚖️ Ricalibra Punteggi</em> qui sotto.</span>'
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
                # Placeholder per feedback AI modifica (dentro la colonna sinistra)
                _rw_status_ph = st.empty()

            # ── Expander: Ricalibra Punteggi ──────────────────────────────────
            if mostra_punteggi and n_blocks > 0:
                with st.expander("⚖️ Ricalibra Punteggi", expanded=True):
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

    # ── IDEA #3: Quick Regen — variante rapida handler ──────────────────────
    if quick_regen or cambia_esercizio:
        _pts_custom_qr = st.session_state.get("recalibra_pts", [])
        if _pts_custom_qr and len(_pts_custom_qr) == n_blocks:
            _qr_target_pts = int(_pts_custom_qr[idx])
        else:
            _qr_target_pts = _parse_pts_from_block_body(body)

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

        if quick_regen:
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
                f"- Se ci sono grafici TikZ/pgfplots, adatta i parametri ai nuovi dati.\n"
                f"- Mantieni lo STESSO numero di sotto-punti.\n"
                f"- {_qr_punti_nota}\n"
                f"- Restituisci SOLO il blocco \\subsection*{{...}} con la variante.\n"
                f"- NON includere preambolo o \\begin{{document}}.\n"
                f"OUTPUT: SOLO codice LaTeX del blocco esercizio."
            )
            _spin_label = f"🔄 Cambio dati esercizio {idx+1}…"
        else:  # cambia_esercizio
            _qr_prompt = (
                f"Sei un docente esperto di {materia_str} e LaTeX.\n"
                f"Devi creare un ESERCIZIO COMPLETAMENTE NUOVO sullo stesso argomento, "
                f"con struttura e approccio diversi rispetto all'originale, mantenendo "
                f"lo stesso livello di difficoltà e punteggio totale.\n\n"
                f"MATERIA: {materia_str}\n"
                f"ARGOMENTO: {argomento_str}\n"
                f"⚠️ L'esercizio DEVE restare su '{argomento_str}' in '{materia_str}'.\n\n"
                f"ESERCIZIO ORIGINALE (da cui NON devi copiare la struttura):\n"
                f"\\subsection*{{{title}}}\n{body}\n\n"
                f"REGOLE:\n"
                f"- Crea un esercizio con approccio DIVERSO (es. cambia il tipo di domanda, "
                f"  usa un contesto applicativo diverso, scegli un'altra modalità di risoluzione).\n"
                f"- Mantieni lo stesso livello di difficoltà e lo stesso numero di sotto-punti.\n"
                f"- {_qr_punti_nota}\n"
                f"- Restituisci SOLO il blocco \\subsection*{{...}} con il nuovo esercizio.\n"
                f"- NON includere preambolo o \\begin{{document}}.\n"
                f"OUTPUT: SOLO codice LaTeX del blocco esercizio."
            )
            _spin_label = f"🎯 Generazione esercizio diverso {idx+1}…"

        _qr_status_ph.info(f"⏳ {_spin_label}")
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
                _qr_new_body = _riscala_single_block(_qr_new_title, _qr_new_body, _qr_target_pts)
                st.session_state.review_blocks[idx]["title"] = _qr_new_title
            st.session_state.review_blocks[idx]["body"]  = _qr_new_body
            if "recalibra_pts" in st.session_state:
                del st.session_state["recalibra_pts"]
            _qr_latex = _reconstruct_latex(
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
            _icon = "🔄" if quick_regen else "🎯"
            _label = "Variante" if quick_regen else "Esercizio diverso"
            st.toast(f"{_icon} {_label} esercizio {idx+1} generato!", icon=_icon)
            time.sleep(0.3); st.rerun()
        except Exception as _qr_e:
            _qr_status_ph.error(f"❌ Errore: {_qr_e}")

    # ── Logica modifica AI ────────────────────────────────────────────────────
    if rigenera and istruzione.strip():
        _istr_low = istruzione.lower()

        # ── Rilevamento richieste punteggio ───────────────────────────────────
        # Se l'utente chiede di cambiare punti/punteggio reindirizza al pannello.
        _is_score_req = bool(_SCORE_PATTERN.search(_istr_low))
        if _is_score_req:
            _rw_status_ph.warning(
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
            _rw_status_ph.info(f"⏳ Rigenerando esercizio {idx+1}…")
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

                # Ricompila il PDF e aggiorna la preview dopo la modifica
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

                st.toast(f"✅ Esercizio {idx+1} modificato!", icon="✅")
                time.sleep(0.4); st.rerun()
            except Exception as e:
                _rw_status_ph.error(f"❌ Errore: {e}")

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
    _scroll_to_top()
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
        '<div style="background:linear-gradient(120deg,#059669 0%,#0284C7 100%);'
        'border-radius:16px;padding:1rem 1.3rem;margin-bottom:.9rem;">'
        '<div style="display:flex;align-items:center;gap:12px;">'
        '<span style="font-size:1.8rem;">🎉</span>'
        '<div style="flex:1;">'
        '<div style="font-family:DM Sans,sans-serif;font-size:1rem;font-weight:900;color:#fff;">La verifica è pronta!</div>'
        '<div style="font-size:.73rem;color:#ffffffcc;margin-top:2px;">' + mat_str + ' · ' + scu_str + ' · ' + arg_str + '</div>'
        '</div></div>'
        '<div style="font-size:.69rem;color:#ffffffaa;margin-top:.45rem;padding-top:.4rem;border-top:1px solid #ffffff22;">'
        '⚠️ Controlla sempre il contenuto prima di distribuire agli studenti.'
        '</div></div>',
        unsafe_allow_html=True
    )

    # ── Badge timer ───────────────────────────────────────────────────────────
    _gen_sec = st.session_state.get("gen_time_sec")
    _n_es    = gp.get("num_esercizi", 4)
    _risparmio_min = max(10, _n_es * 8)
    if _gen_sec:
        _t_label = (f"{_gen_sec}s" if _gen_sec < 60 else f"{_gen_sec // 60}m {_gen_sec % 60}s")
        st.markdown(
            f'<div style="display:flex;gap:.5rem;margin-bottom:.7rem;flex-wrap:wrap;">'
            f'<span style="background:{T["card2"]};border:1px solid {T["border"]};border-radius:8px;'
            f'padding:.28rem .75rem;font-size:.72rem;font-weight:700;color:{T["success"]};'
            f'font-family:DM Sans,sans-serif;">⚡ Generata in {_t_label}</span>'
            f'<span style="background:{T["card2"]};border:1px solid {T["border"]};border-radius:8px;'
            f'padding:.28rem .75rem;font-size:.72rem;font-weight:700;color:{T["text2"]};'
            f'font-family:DM Sans,sans-serif;">🕐 ~{_risparmio_min} min risparmiati</span>'
            f'</div>',
            unsafe_allow_html=True
        )

    # ═══════════════════════════════════════════════════════════════════════════
    #  DOWNLOAD PRINCIPALE
    # ═══════════════════════════════════════════════════════════════════════════
    _fname_a = arg_str + "_FilaA"
    if vA.get("pdf"):
        st.markdown("<div style='margin-bottom:.8rem;'>", unsafe_allow_html=True)
        st.download_button(
            label=f"📄  Scarica Verifica PDF  ·  {_stima(vA['pdf'])}",
            data=vA["pdf"], file_name=_fname_a + ".pdf",
            mime="application/pdf", use_container_width=True, key="dl_pdf_hero_A",
        )
        st.markdown('</div>', unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════════════════
    #  VARIANTI — 4 card in griglia 2×2
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown(
        f'<div style="font-size:.66rem;font-weight:800;color:{T["muted"]};letter-spacing:.08em;'
        f'font-family:DM Sans,sans-serif;margin-bottom:.45rem;">VARIANTI — UN CLICK PER GENERARE E SCARICARE</div>',
        unsafe_allow_html=True
    )
    _vc1, _vc2 = st.columns(2, gap="medium")
    _vc3, _vc4 = st.columns(2, gap="medium")

    # ── FILA B ────────────────────────────────────────────────────────────────
    with _vc1:
        _b_pdf = vB.get("pdf")
        _b_lat = vB.get("latex")

        st.markdown(
            f'<div class="one-click-variant-card">'
            f'  <div class="one-click-body">'
            f'    <div class="one-click-title">📋 Fila B</div>'
            f'    <div class="one-click-desc">Stessa struttura, stessi punteggi — solo i dati cambiano. Pronta in secondi.</div>'
            f'  </div>'
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
            if st.button("📄 Compila PDF Fila B", key="compile_B_v2",
                         use_container_width=True, type="primary"):
                with st.spinner("Compilazione…"):
                    _pdf_bc, _ = compila_pdf(_b_lat)
                if _pdf_bc:
                    st.session_state.verifiche["B"]["pdf"] = _pdf_bc; st.rerun()
        else:
            if st.button("⚡ Genera Fila B — One Click", key="one_click_B_v2",
                         use_container_width=True, type="primary"):
                st.session_state["_gen_fila_b"] = True; st.rerun()

        if st.session_state.get("_gen_fila_b"):
            st.session_state["_gen_fila_b"] = False
            _ph_b = st.empty()
            _ph_b.markdown(_skeleton_html("⚡", "Generazione Fila B…",
                           "Cambio dati · Anti-spoiler · QA coerenza"), unsafe_allow_html=True)
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
            f'<div class="one-click-variant-card">'
            f'  <div class="one-click-body">'
            f'    <div class="one-click-title">🌟 Versione BES/DSA</div>'
            f'    <div class="one-click-desc">Linguaggio semplificato, struttura alleggerita. Stessi obiettivi didattici.</div>'
            f'  </div>'
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
            if st.button("📄 Compila PDF BES/DSA", key="compile_R_v2",
                         use_container_width=True, type="primary"):
                with st.spinner("Compilazione…"):
                    _pdf_rc, _ = compila_pdf(_r_lat)
                if _pdf_rc:
                    st.session_state.verifiche["R"]["pdf"] = _pdf_rc; st.rerun()
        else:
            if st.button("🌟 Genera BES/DSA — One Click", key="one_click_R_v2",
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
            f'<div class="one-click-variant-card">'
            f'  <div class="one-click-body">'
            f'    <div class="one-click-title">✅ Soluzioni</div>'
            f'    <div class="one-click-desc">Documento riservato al docente con risposte complete e svolgimenti.</div>'
            f'  </div>'
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
            if st.button("📄 Compila PDF Soluzioni", key="compile_S_v2",
                         use_container_width=True, type="primary"):
                with st.spinner("Compilazione…"):
                    _pdf_sc, _ = compila_pdf(_s_lat)
                if _pdf_sc:
                    st.session_state.verifiche["S"]["pdf"] = _pdf_sc; st.rerun()
        else:
            if st.button("✅ Genera Soluzioni — One Click", key="one_click_S_v2",
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

    # ── RUBRICA DI VALUTAZIONE (MIM) — 4ª card ────────────────────────────────
    _punti_tot_r = gp.get("punti_totali", 100)
    _latex_a_r   = vA.get("latex", "")

    with _vc4:
        st.markdown(
            f'<div class="one-click-variant-card">'
            f'  <div class="one-click-body">'
            f'    <div class="one-click-title">📊 Rubrica di Valutazione</div>'
            f'    <div class="one-click-desc">Indicatori qualitativi per fascia di voto, allineati alle Linee Guida MIM.</div>'
            f'  </div>'
            f'</div>',
            unsafe_allow_html=True
        )
        if st.session_state.rubrica_testo:
            # Rubrica già generata — mostra download e rigenera
            st.download_button(
                "⬇ Scarica Rubrica (.txt)",
                data=st.session_state.rubrica_testo.encode("utf-8"),
                file_name=arg_str + "_Rubrica.txt", mime="text/plain",
                key="dl_rubrica_card", use_container_width=True,
            )
            if st.button("🔄 Rigenera Rubrica", key="btn_rigenera_rubrica_card",
                         use_container_width=True):
                st.session_state.rubrica_testo = None
                st.session_state._rubrica_gen  = False
                st.rerun()
            # Anteprima rubrica in expander
            with st.expander("👁 Visualizza rubrica", expanded=False):
                def _md_to_html(text: str) -> str:
                    import re as _re
                    t = text
                    t = _re.sub(r'^### (.+)$', r'<h3>\1</h3>', t, flags=_re.MULTILINE)
                    t = _re.sub(r'^## (.+)$',  r'<h2>\1</h2>', t, flags=_re.MULTILINE)
                    t = _re.sub(r'^# (.+)$',   r'<h1>\1</h1>', t, flags=_re.MULTILINE)
                    t = _re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', t)
                    t = _re.sub(r'\*(.+?)\*',     r'<em>\1</em>', t)
                    lines = t.split('\n'); out = []; in_table = False
                    for line in lines:
                        if '|' in line and line.strip().startswith('|'):
                            cells = [c.strip() for c in line.strip().strip('|').split('|')]
                            if not in_table:
                                out.append('<table style="width:100%;border-collapse:collapse;font-size:.8rem;">')
                                in_table = True
                            if all(set(c) <= set('-: ') for c in cells): continue
                            row = ''.join(f'<td style="border:1px solid #444;padding:4px 8px;">{c}</td>' for c in cells)
                            out.append(f'<tr>{row}</tr>')
                        else:
                            if in_table: out.append('</table>'); in_table = False
                            out.append(line)
                    if in_table: out.append('</table>')
                    t = '\n'.join(out)
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
        else:
            if st.button("📊 Genera Rubrica MIM", key="btn_gen_rubrica_card",
                         use_container_width=True, type="primary"):
                st.session_state._rubrica_gen = True
                st.rerun()
            if st.session_state.get("_rubrica_gen"):
                st.session_state._rubrica_gen = False
                _rub_ph = st.empty()
                _rub_ph.markdown(
                    _skeleton_html("📊", "Generazione rubrica…", "Indicatori · Fasce di voto · MIM"),
                    unsafe_allow_html=True
                )
                try:
                    _mod_rub = genai.GenerativeModel(mod_id)
                    _prompt_rub = prompt_rubrica_valutazione(
                        corpo_latex=_latex_a_r, materia=mat_str,
                        livello=scu_str, punti_totali=_punti_tot_r,
                    )
                    _resp_rub = _mod_rub.generate_content(
                        [_prompt_rub], generation_config=genai.GenerationConfig(temperature=0.5),
                    )
                    st.session_state.rubrica_testo = _resp_rub.text.strip()
                    _rub_ph.empty(); st.toast("✅ Rubrica generata!", icon="📊"); st.rerun()
                except Exception as _e_rub:
                    _rub_ph.empty(); st.error(f"Errore generazione rubrica: {_e_rub}")

    # ── Navigazione ───────────────────────────────────────────────────────────
    st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)
    _nav_l, _nav_c, _nav_r = st.columns([1, 2, 1])
    with _nav_c:
        if st.button("🆕 Nuova verifica", type="primary",
                     use_container_width=True, key="btn_new_s3_top"):
            # Reset completo — l'utente riparte dalla Home come nuovo accesso
            st.session_state.stage            = STAGE_INPUT
            st.session_state["_prev_stage"]   = None
            st.session_state.input_percorso   = None          # → torna al bivio
            # Dati verifica
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
            st.session_state["_gen_fila_b"]        = False
            st.session_state["_gen_bes"]           = False
            st.session_state["_gen_sol"]           = False
            # Dati upload / wizard percorso A
            st.session_state.analisi_docs_list  = []
            st.session_state.info_consolidate   = {}
            st.session_state["wizard_step"]     = "upload"
            st.session_state["_analisi_rifiuto"] = None
            st.session_state["_facsimile_mode"] = False
            # QA mode
            st.session_state.qa_mode            = False
            # Share
            st.session_state._share_code        = None
            st.session_state._share_generating   = False
            st.rerun()

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
                f'    Link attivo · scade tra 30 giorni'
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
                    ".cb{background:#D97706;color:#fff;border:none;border-radius:8px;"
                    "padding:8px 16px;cursor:pointer;font-size:.82rem;font-weight:700;"
                    "font-family:DM Sans,sans-serif;width:100%;transition:all .15s}"
                    ".cb:hover{background:#B45309;transform:translateY(-1px)}"
                    ".cb.ok{background:#059669}</style>"
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
                if st.button("🔄", key="share_new_link", help="Genera nuovo link"):
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
                        with st.spinner("Conversione Word…"):
                            db, _ = latex_to_docx_via_ai(v["latex"], con_griglia=con_griglia)
                        st.session_state[_docx_key] = False
                        if db:
                            st.session_state.verifiche[fid]["docx"] = db; st.rerun()
                        else:
                            st.error("Errore Word")
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
                    _sh_pre, _sh_blks = _extract_blocks(_sh_lat)
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
    # Mostra breadcrumb solo quando NON si è sulla landing iniziale
    _show_bc = not (
        st.session_state.stage == STAGE_INPUT
        and st.session_state.get("input_percorso") is None
    )
    if _show_bc:
        _render_breadcrumb()

# ── SCROLL TO TOP on stage change ─────────────────────────────────────────────
# Strategia: inietta anchor #top-anchor al top della pagina (prima del contenuto)
# e quando lo stage cambia, forza scroll con JS multi-selettore + retry loop.
_current_stage = st.session_state.stage
_prev_stage = st.session_state.get("_prev_stage", None)
if _prev_stage != _current_stage:
    st.session_state["_prev_stage"] = _current_stage
    components.html(
        "<script>"
        "(function(){"
        "var n=0;"
        "function top(){"
        "  var sels=['[data-testid=\"stMainBlockContainer\"]',"
        "    '[data-testid=\"stAppViewContainer\"]',"
        "    '.stMainBlockContainer','.main','section.main'];"
        "  sels.forEach(function(s){"
        "    var el=window.parent.document.querySelector(s);"
        "    if(el){el.scrollTop=0;el.scrollTo({top:0,behavior:'instant'});}"
        "  });"
        "  window.parent.scrollTo({top:0,behavior:'instant'});"
        "  if(n++<8)setTimeout(top,60);"
        "}"
        "top();"
        "})();"
        "</script>",
        height=1
    )

if not _share_view_active:
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
