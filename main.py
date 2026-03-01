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
from generation import genera_verifica
from prompts import (
    prompt_versione_b, prompt_versione_ridotta, prompt_soluzioni,
    prompt_modifica,
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
)
# THEME_LABELS è definito nel nuovo config.py — fallback per compatibilità
try:
    from config import THEME_LABELS
except ImportError:
    THEME_LABELS = {k: k.replace("_", " ").title() for k in THEMES}
from dotenv import load_dotenv
from supabase import create_client, Client
from auth import mostra_auth, ripristina_sessione, cancella_sessione_cookie
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
if "file_ispirazione"  not in st.session_state: st.session_state.file_ispirazione = None

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
    '<h1 class="hero-title">Verific<span class="hero-ai">AI</span></h1>'
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
    steps = [("01","Configura",STAGE_INPUT),("02","Revisione",STAGE_REVIEW),("03","Download",STAGE_FINAL)]
    completed = {STAGE_INPUT: stage in (STAGE_REVIEW,STAGE_FINAL),
                 STAGE_REVIEW: stage == STAGE_FINAL, STAGE_FINAL: False}
    html = (
        '<div style="display:flex;justify-content:center;margin-bottom:1.6rem;">'
        '<div class="breadcrumb-pill" style="display:inline-flex;align-items:center;gap:10px;'
        'padding:.7rem 1.6rem;'
        'background:' + T["card"] + ';border:1.5px solid ' + T["border"] + ';'
        'border-radius:100px;box-shadow:' + T["shadow_md"] + ';'
        'max-width:calc(100vw - 2rem);overflow:hidden;">'
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
            '<div style="display:flex;align-items:center;gap:6px;opacity:' + _op + ';">'
            '<div class="bc-circle" style="background:' + cb + ';border-radius:50%;'
            'width:28px;height:28px;display:flex;align-items:center;'
            'justify-content:center;font-size:.72rem;font-weight:800;'
            'color:' + cc + ';flex-shrink:0;box-shadow:0 2px 8px ' + cb + '44;">' + icon + '</div>'
            '<span class="bc-label" style="font-size:.82rem;font-weight:' + lw + ';color:' + lc + ';'
            'font-family:DM Sans,sans-serif;white-space:nowrap;letter-spacing:-.01em;">' + label + '</span>'
            '</div>'
        )
        if i < 2:
            _sep_c = T["success"] if is_done else T["border2"]
            html += (
                '<div class="bc-sep" style="width:24px;height:1.5px;background:' + _sep_c + ';'
                'opacity:.4;flex-shrink:0;border-radius:2px;"></div>'
            )
    html += "</div></div>"
    st.markdown(html, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  STAGE_INPUT
# ═══════════════════════════════════════════════════════════════════════════════

def _render_stage_input():

    # ── STEP 1 — MATERIA + SCUOLA ─────────────────────────────────────────────
    st.markdown(
        '<div class="step-label">'
        '<span class="step-title">Materia e Tipo di Scuola</span>'
        '<span class="step-line"></span>'
        '</div>',
        unsafe_allow_html=True
    )

    col_mat, col_scuola = st.columns(2)
    with col_mat:
        _materie_list = MATERIE + ["✏️ Altra materia..."]
        _sel = st.selectbox("Materia", _materie_list, index=0,
                            label_visibility="collapsed", key="sel_materia")
        if _sel == "✏️ Altra materia...":
            materia_scelta = st.text_input("Scrivi materia:", placeholder="es. Economia Aziendale...",
                                           key="_mat_custom", label_visibility="collapsed").strip() or "Matematica"
        else:
            materia_scelta = _sel or "Matematica"

    with col_scuola:
        _prev_scuola = st.session_state.gen_params.get("difficolta", "")
        _idx_s = SCUOLE.index(_prev_scuola) if _prev_scuola in SCUOLE else 0
        difficolta = st.selectbox("Scuola", SCUOLE, index=_idx_s,
                                  label_visibility="collapsed", key="sel_scuola")

    # ── STEP 2 — ARGOMENTO ───────────────────────────────────────────────────
    st.markdown(
        '<div class="ai-hint"><span class="ai-hint-icon">💡</span>'
        '<span><strong>Suggerimento:</strong> più dettagli fornisci, più la verifica sarà precisa. '
        'Es: "equazioni di II grado con discriminante, 2 esercizi applicativi" funziona meglio di "algebra".</span>'
        '</div>'
        '<div class="step-label">'
        '<span class="step-title">Argomento della verifica</span>'
        '<span class="step-line"></span>'
        '</div>',
        unsafe_allow_html=True
    )
    argomento = st.text_area(
        "argomento",
        placeholder="es. Le equazioni di secondo grado\nes. La Rivoluzione Francese\nes. Il ciclo dell'acqua",
        height=95, label_visibility="collapsed", key="argomento_area"
    ).strip()

    # ── STEP 3 — PERSONALIZZA (snello) ────────────────────────────────────────
    st.markdown(
        '<div class="step-label">'
        '<span class="step-title">Personalizza</span>'
        '<span class="step-line"></span>'
        '</div>',
        unsafe_allow_html=True
    )
    st.markdown('<div class="personalizza-wrap">', unsafe_allow_html=True)
    with st.expander("Opzioni verifica", expanded=False):

        # Numero esercizi — selectbox compatta
        _es_options = list(range(1, 16))
        _es_default_idx = _es_options.index(4)
        col_es, col_pts = st.columns(2)
        with col_es:
            st.markdown('<div class="opt-label">Numero esercizi</div>', unsafe_allow_html=True)
            num_esercizi_totali = st.selectbox(
                "Numero esercizi", options=_es_options,
                index=_es_default_idx, label_visibility="collapsed",
                key="sel_num_es", format_func=lambda x: f"{x} esercizi"
            )
        durata_scelta = "1 ora"

        # Punteggi + Griglia
        punteggi_e_griglia = st.toggle(
            "Aggiungi punteggi e griglia di valutazione",
            value=True,
            help="Aggiunge (X pt) a ogni sottopunto e genera la tabella di valutazione in fondo"
        )
        mostra_punteggi = punteggi_e_griglia
        con_griglia     = punteggi_e_griglia
        if punteggi_e_griglia:
            with col_pts:
                _pt_options = list(range(10, 105, 5))
                _pt_default = _pt_options.index(100) if 100 in _pt_options else len(_pt_options)-1
                st.markdown('<div class="opt-label">Punti totali</div>', unsafe_allow_html=True)
                punti_totali = st.selectbox(
                    "Punti totali", options=_pt_options,
                    index=_pt_default, label_visibility="collapsed",
                    key="sel_punti", format_func=lambda x: f"{x} pt"
                )
        else:
            punti_totali = 100

        st.markdown("<div style='height:.3rem'></div>", unsafe_allow_html=True)

        # Struttura esercizi custom
        st.markdown('<div class="opt-label">Struttura esercizi</div>', unsafe_allow_html=True)
        with st.expander("Definisci tipo e contenuto di ogni esercizio"):
            n_custom = len(st.session_state.esercizi_custom)
            n_liberi = max(0, num_esercizi_totali - n_custom)
            if n_custom == 0:
                st.info(f"Tutti i {num_esercizi_totali} esercizi generati liberamente dall'AI.")
            elif n_custom >= num_esercizi_totali:
                st.warning(f"Raggiunto il limite ({n_custom}/{num_esercizi_totali}). Aumenta il numero esercizi.")
            else:
                st.success(f"✅ {n_custom} definiti + {n_liberi} liberi = {num_esercizi_totali} totali")

            to_remove = None
            for i, ex in enumerate(st.session_state.esercizi_custom):
                st.markdown(f"**Esercizio {i+1}**")
                t_ex = st.selectbox("Tipo", TIPI_ESERCIZIO,
                                 index=TIPI_ESERCIZIO.index(ex.get("tipo","Aperto")),
                                 key=f"tipo_{i}")
                st.session_state.esercizi_custom[i]["tipo"] = t_ex
                d = st.text_area("Descrizione",
                                  value=ex.get("descrizione",""),
                                  placeholder="es. Risolvi l'equazione ax²+bx+c=0",
                                  key=f"desc_{i}",
                                  height=80,
                                  label_visibility="collapsed")
                st.session_state.esercizi_custom[i]["descrizione"] = d
                c1, c2 = st.columns([3,1])
                with c1:
                    img = st.file_uploader("📎 Immagine allegata",
                                           type=["png","jpg","jpeg"],
                                           key=f"img_{i}", label_visibility="collapsed")
                    if img: st.session_state.esercizi_custom[i]["immagine"] = img
                    if st.session_state.esercizi_custom[i].get("immagine"):
                        st.image(st.session_state.esercizi_custom[i]["immagine"], width=55)
                with c2:
                    if st.button("🗑 Rimuovi", key=f"rm_{i}", use_container_width=True):
                        to_remove = i
                st.divider()

            if to_remove is not None:
                st.session_state.esercizi_custom.pop(to_remove); st.rerun()

            if st.button("＋ Aggiungi esercizio",
                         disabled=len(st.session_state.esercizi_custom) >= num_esercizi_totali):
                st.session_state.esercizi_custom.append(
                    {"tipo":"Aperto","descrizione":"","immagine":None})
                st.rerun()

        # Note AI
        st.markdown('<div class="opt-label">Note per l\'AI</div>', unsafe_allow_html=True)
        note_generali = st.text_area(
            "Note AI",
            placeholder=NOTE_PLACEHOLDER.get(materia_scelta,
                         "es. Includi domande sulla definizione, formula e applicazione..."),
            height=65, key="note_area", label_visibility="collapsed"
        )

        # ── DOCUMENTO DI ISPIRAZIONE ───────────────────────────────────────────
        _doc_bg      = T.get("card2", T["card"])
        _doc_border  = T.get("border2", T["border"])
        _doc_accent  = T["accent"]
        _doc_text    = T["text2"]
        _doc_muted   = T["muted"]
        _doc_badge_bg   = T.get("accent_light", T["card"])
        st.markdown(
            f'<div style="margin-top:0.9rem;background:{_doc_bg};'
            f'border:1px solid {_doc_border};border-radius:12px;padding:0.75rem 1rem;">'
            f'<div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.35rem;">'
            f'<span style="font-size:1.05rem;">📎</span>'
            f'<span style="font-size:0.8rem;font-weight:700;color:{_doc_accent};'
            f'font-family:DM Sans,sans-serif;letter-spacing:.02em;">'
            f'Documento di ispirazione'
            f'</span>'
            f'<span style="font-size:0.68rem;background:{_doc_badge_bg};color:{_doc_accent};'
            f'border:1px solid {_doc_border};border-radius:4px;padding:1px 6px;'
            f'font-weight:600;margin-left:auto;">Nuovo</span>'
            f'</div>'
            f'<p style="font-size:0.75rem;color:{_doc_muted};margin:0;line-height:1.5;'
            f'font-family:DM Sans,sans-serif;">'
            f'Carica una tua verifica precedente, un capitolo del libro, appunti o una foto della lavagna. '
            f"L'AI la analizzerà per rispettare il tuo stile, coprire gli argomenti giusti e seguire "
            f'le tue istruzioni.'
            f'</p>'
            f'</div>',
            unsafe_allow_html=True
        )

        file_doc = st.file_uploader(
            "Carica documento",
            type=["pdf", "png", "jpg", "jpeg"],
            key="file_ispirazione_upload",
            label_visibility="collapsed",
            help="PDF, immagine JPG/PNG. Max ~10MB. Può essere una verifica precedente, appunti, capitoli del libro.",
        )
        if file_doc:
            st.session_state.file_ispirazione = file_doc
            # Preview compatta
            ftype = file_doc.type or ""
            if "image" in ftype:
                st.image(file_doc, width=80)
            st.markdown(
                f'<div style="font-size:0.72rem;color:#60AAEE;font-family:DM Sans,sans-serif;'
                f'margin-top:2px;">✓ <b>{file_doc.name}</b> caricato — l\'AI lo userà come riferimento</div>',
                unsafe_allow_html=True
            )
        elif st.session_state.file_ispirazione:
            # File caricato in sessione precedente — mantieni
            f_prev = st.session_state.file_ispirazione
            st.markdown(
                f'<div style="font-size:0.72rem;color:#60AAEE;font-family:DM Sans,sans-serif;">'
                f'✓ <b>{f_prev.name}</b> in uso — '
                f'<span style="color:#8C8A82;">ricarica il file per cambiarlo</span></div>',
                unsafe_allow_html=True
            )

    st.markdown("</div>", unsafe_allow_html=True)

    # ── BOTTONE GENERA ────────────────────────────────────────────────────────
    st.markdown('<div class="genera-section">', unsafe_allow_html=True)
    genera_btn = st.button("🚀  Genera Verifica", use_container_width=True,
                           type="primary", disabled=_limite)
    if _limite:
        st.markdown(
            '<div style="text-align:center;font-size:.82rem;color:#EF4444;margin-top:.5rem;'
            'font-family:DM Sans,sans-serif;font-weight:600;">'
            '⛔ Limite di ' + str(LIMITE_MENSILE) + ' verifiche mensili raggiunto.'
            '</div>',
            unsafe_allow_html=True
        )
    st.markdown("</div>", unsafe_allow_html=True)

    # ── LOGICA GENERAZIONE ────────────────────────────────────────────────────
    if genera_btn and not _limite:
        if not argomento:
            st.warning("⚠️ Inserisci l'argomento della verifica.")
            st.stop()

        calibrazione = CALIBRAZIONE_SCUOLA.get(difficolta, "")
        s_es, imgs_es = _build_prompt_esercizi(
            st.session_state.esercizi_custom, num_esercizi_totali,
            punti_totali if mostra_punteggi else 0, mostra_punteggi
        )

        _t_gen_start = time.time()
        _n_steps = 4
        _step = [0]
        _prog = st.empty()

        def _avanza(testo):
            _step[0] += 1
            perc = int(min(_step[0] / _n_steps, 0.97) * 100)
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

        # Determina file di ispirazione: preferisce quello appena caricato
        _file_isp = (
            st.session_state.get("file_ispirazione_upload") or
            st.session_state.get("file_ispirazione")
        )

        try:
            model_obj = genai.GenerativeModel(modello_id)
            ris = genera_verifica(
                model=model_obj, materia=materia_scelta, argomento=argomento,
                difficolta=difficolta, calibrazione=calibrazione, durata=durata_scelta,
                num_esercizi=num_esercizi_totali, punti_totali=punti_totali,
                mostra_punteggi=mostra_punteggi, con_griglia=con_griglia,
                doppia_fila=False, bes_dsa=False, perc_ridotta=25,
                bes_dsa_b=False, genera_soluzioni=False,
                note_generali=note_generali, istruzioni_esercizi=s_es,
                immagini_esercizi=imgs_es, file_ispirazione=_file_isp,
                on_progress=_avanza,
            )

            def _aggiorna(fid, d):
                v = st.session_state.verifiche[fid]
                if d.get("latex"): v["latex"] = v["latex_originale"] = d["latex"]
                if d.get("pdf"):   v["pdf"] = d["pdf"]; v["pdf_ts"] = time.time(); v["preview"] = True
                if fid == "S":
                    if d.get("testo"): v["testo"] = d["testo"]
                    if d.get("latex"): v["latex"] = d["latex"]
                    if d.get("pdf"):   v["pdf"]   = d["pdf"]

            _aggiorna("A", ris["A"]); _aggiorna("B", ris["B"])
            _aggiorna("R", ris["R"]); _aggiorna("RB", ris["RB"])
            _aggiorna("S", ris["S"])

            _gen_elapsed = int(time.time() - _t_gen_start)
            st.session_state.gen_time_sec = _gen_elapsed

            st.session_state.gen_params = {
                "materia": materia_scelta, "difficolta": difficolta,
                "argomento": ris["titolo"], "durata": durata_scelta,
                "num_esercizi": num_esercizi_totali, "punti_totali": punti_totali,
                "mostra_punteggi": mostra_punteggi, "con_griglia": con_griglia,
                "perc_ridotta": 25, "modello_id": modello_id,
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
                'font-family:DM Sans,sans-serif;margin-bottom:6px;">✅ Bozza pronta! Ora puoi rivedere gli esercizi.</div>'
                '<div style="background:' + T["border"] + ';border-radius:100px;height:8px;overflow:hidden;">'
                '<div style="background:' + T["success"] + ';width:100%;height:100%;border-radius:100px;"></div>'
                '</div></div>',
                unsafe_allow_html=True
            )
            time.sleep(0.7); _prog.empty()

            try:
                supabase_admin.table("verifiche_storico").insert({
                    "user_id": st.session_state.utente.id,
                    "materia": materia_scelta, "argomento": ris["titolo"],
                    "scuola": difficolta, "latex_a": ris["A"]["latex"] or None,
                    "latex_b": None, "latex_r": None, "modello": modello_id,
                    "num_esercizi": num_esercizi_totali,
                }).execute()
                st.session_state._storico_refresh += 1
                st.toast("✅ Bozza salvata!", icon="💾")
            except Exception as e:
                st.warning(f"⚠️ Salvataggio storico non riuscito: {e}")

            st.session_state.stage = STAGE_REVIEW
            st.rerun()

        except Exception as e:
            _prog.empty()
            st.error(f"❌ Errore durante la generazione: {e}")


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
            'Anteprima PDF completo</div>',
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
        '<div style="flex:1;">'
        '<div style="font-family:DM Sans,sans-serif;font-size:1rem;font-weight:900;color:#fff;'
        'text-shadow:0 1px 4px rgba(0,0,0,.2);">'
        'Verifica pronta!</div>'
        '<div style="font-size:.72rem;color:#fff;opacity:.9;margin-top:1px;">'
        + mat_str + ' · ' + scu_str + ' · ' + arg_str + '</div>'
        '</div></div></div>'
        '<div style="padding:.7rem 1.2rem;background:' + T["card"] + ';">'
        '<div style="display:flex;align-items:center;gap:8px;font-size:.78rem;color:' + T["text2"] + ';line-height:1.5;">'
        '<span>Controlla sempre il contenuto prima di distribuire agli studenti. '
        'Il docente è responsabile del materiale finale.</span>'
        '</div></div></div>',
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


    # ── Genera Varianti on-demand ──────────────────────────────────────────────
    st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)
    st.markdown(
        '<div class="s3-section-title">Aggiungi varianti</div>',
        unsafe_allow_html=True
    )

    col_v1, col_v2, col_v3 = st.columns(3)
    with col_v1:
        has_b = bool(vB.get("latex"))
        lbl_b = "✓ Fila B" if has_b else "📄 Genera Fila B"
        if not has_b and st.button(lbl_b, use_container_width=True, key="gen_var_B",
                                   help="Genera una seconda versione con dati diversi"):
            with st.spinner("Generazione Fila B…"):
                try:
                    res = _genera_variante("B", mod_id, gp, vA)
                    st.session_state.verifiche["B"] = {**st.session_state.verifiche["B"], **res}
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore: {e}")

    with col_v2:
        has_r = bool(vR.get("latex"))
        lbl_r = "✓ BES/DSA" if has_r else "🌟 Genera BES/DSA"
        if not has_r and st.button(lbl_r, use_container_width=True, key="gen_var_R"):
            with st.spinner("Generazione BES/DSA…"):
                try:
                    res = _genera_variante("R", mod_id, gp, vA)
                    st.session_state.verifiche["R"] = {**st.session_state.verifiche["R"], **res}
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore: {e}")

    with col_v3:
        has_s = bool(vS.get("pdf") or vS.get("testo"))
        lbl_s = "✓ Soluzioni" if has_s else "✅ Genera Soluzioni"
        if not has_s and st.button(lbl_s, use_container_width=True, key="gen_var_S"):
            with st.spinner("Generazione soluzioni…"):
                try:
                    res = _genera_variante("S", mod_id, gp, vA)
                    st.session_state.verifiche["S"] = {**st.session_state.verifiche["S"], **res}
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore: {e}")

    # ── Pulsanti di navigazione ────────────────────────────────────────────────
    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    # "Rivedi esercizi" — riga separata, outline accent
    st.markdown('<div class="btn-secondary-accent">', unsafe_allow_html=True)
    if st.button("← Rivedi esercizi", use_container_width=True, key="btn_rev_s3"):
        st.session_state.stage = STAGE_REVIEW; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)

    # "Nuova verifica" — larghezza piena, primary, in fondo
    if st.button("🆕 Inizia nuova verifica", type="primary", use_container_width=True, key="btn_new_s3"):
        st.session_state.stage            = STAGE_INPUT
        st.session_state["_prev_stage"]   = None  # forza scroll al top
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
        st.session_state.esercizi_custom   = []
        st.session_state._saved_to_storico = False
        st.rerun()

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
        "var n=0;"
        "function s(){"
        "  var doc=window.parent.document;"
        "  var targets=["
        "    doc.querySelector('[data-testid=\"stAppViewContainer\"]'),"
        "    doc.querySelector('.main'),"
        "    doc.querySelector('section.main'),"
        "    doc.documentElement,"
        "    doc.body"
        "  ];"
        "  targets.forEach(function(el){if(el){el.scrollTop=0;}});"
        "  window.parent.scrollTo(0,0);"
        "  window.scrollTo(0,0);"
        "  if(++n<12) setTimeout(s,80);"
        "}"
        "s();"
        "})();"
        "</script>",
        height=0
    )

_current = _current_stage
if   _current == STAGE_INPUT:  _render_stage_input()
elif _current == STAGE_REVIEW: _render_stage_review()
elif _current == STAGE_FINAL:  _render_stage_final()


# ── FOOTER ────────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="app-footer">'
    'Le verifiche generate dall\'AI sono suggerimenti didattici — '
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
