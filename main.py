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
    compila_pdf, inietta_griglia, riscala_punti,
    fix_items_environment, rimuovi_vspace_corpo, pulisci_corpo_latex,
    rimuovi_punti_subsection, pdf_to_images_bytes,
)
from config import (
    APP_NAME, APP_ICON, APP_TAGLINE, SHARE_URL, FEEDBACK_FORM_URL,
    LIMITE_MENSILE, ADMIN_EMAILS, MODELLI_DISPONIBILI, THEMES,
    SCUOLE, CALIBRAZIONE_SCUOLA, MATERIE, NOTE_PLACEHOLDER, TIPI_ESERCIZIO,
)
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

# ── TEMA (sempre scuro) ───────────────────────────────────────────────────────
if "theme" not in st.session_state:
    st.session_state.theme = "dark"
T = THEMES[st.session_state.theme]

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
            body = re.sub(r"\s*\\end\{document\}\s*$", "", m.group(2)).rstrip()
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

    # 8. Comandi LaTeX generici con argomento (conservativi: non toccare math)
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
        righe.append(f"DISTRIBUZIONE PUNTI (totale ESATTO: {punti_totali} pt):")
        for i in range(num_totale):
            righe.append(f"  - Esercizio {i+1}: circa {pts[i]} pt")
        righe.append(f"La somma di TUTTI i (X pt) DEVE essere ESATTAMENTE {punti_totali} pt.")

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
if "esercizi_custom"   not in st.session_state: st.session_state.esercizi_custom = []
if "last_materia"      not in st.session_state: st.session_state.last_materia = None
if "last_argomento"    not in st.session_state: st.session_state.last_argomento = None
if "_storico_refresh"  not in st.session_state: st.session_state._storico_refresh = 0
if "_preferiti"        not in st.session_state: st.session_state._preferiti = set()
if "_storico_page"     not in st.session_state: st.session_state._storico_page = 1
if "_onboarding_done"  not in st.session_state: st.session_state._onboarding_done = False

# ── CONTATORI ─────────────────────────────────────────────────────────────────
_verifiche_mese = _get_verifiche_mese(st.session_state.utente.id) if st.session_state.utente else 0
_is_admin       = st.session_state.utente.email in ADMIN_EMAILS if st.session_state.utente else False
_limite         = (not _is_admin) and (_verifiche_mese >= LIMITE_MENSILE)

# ── CSS + FEEDBACK ────────────────────────────────────────────────────────────
st.markdown(get_css(T), unsafe_allow_html=True)
# Modifica FAB: Alzato z-index e bottom per non coprire elementi Streamlit
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
)
modello_id = settings.get("modello_id", "gemini-2.5-flash-lite")

# ── HERO ──────────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="top-bar"><div class="top-bar-hint">'
    '← Impostazioni: modello AI, storico verifiche, logout'
    '</div></div>',
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
    steps = [("01","Configura",STAGE_INPUT),("02","Revisione",STAGE_REVIEW),("03","Download",STAGE_FINAL)]
    completed = {STAGE_INPUT: stage in (STAGE_REVIEW,STAGE_FINAL),
                 STAGE_REVIEW: stage == STAGE_FINAL, STAGE_FINAL: False}
    html = (
        '<div style="display:flex;align-items:center;gap:8px;padding:.65rem 1rem;'
        'margin-bottom:1.2rem;background:' + T["bg2"] + ';border:1px solid ' + T["border"] + ';'
        'border-radius:12px;flex-wrap:nowrap;">'
    )
    for i, (num, label, s) in enumerate(steps):
        is_active = s == stage
        is_done   = completed[s]
        if is_active:
            cb, cb2, cc, lc, lw, op = T["accent"], T["accent"], "#fff", T["accent"], "800", "1"
            icon = num
        elif is_done:
            cb, cb2, cc, lc, lw, op = T["success"], T["success"], "#fff", T["success"], "600", "1"
            icon = "✓"
        else:
            cb, cb2, cc, lc, lw, op = T["bg2"], T["border2"], T["muted"], T["muted"], "500", ".5"
            icon = num
        html += (
            '<div style="display:flex;align-items:center;gap:6px;opacity:' + op + ';">'
            '<div style="background:' + cb + ';border:1.5px solid ' + cb2 + ';'
            'border-radius:50%;width:26px;height:26px;display:flex;align-items:center;'
            'justify-content:center;font-size:.68rem;font-weight:800;'
            'color:' + cc + ';flex-shrink:0;">' + icon + '</div>'
            '<span style="font-size:.8rem;font-weight:' + lw + ';color:' + lc + ';'
            'font-family:DM Sans,sans-serif;white-space:nowrap;">' + label + '</span>'
            '</div>'
        )
        if i < 2:
            lc2 = T["success"] if is_done else T["border"]
            html += (
                '<div style="flex:1;height:1.5px;background:' + lc2 + ';'
                'min-width:16px;max-width:56px;opacity:.6;"></div>'
            )
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  STAGE_INPUT
# ═══════════════════════════════════════════════════════════════════════════════

def _render_stage_input():

    # ── ONBOARDING ────────────────────────────────────────────────────────────
    if not st.session_state._onboarding_done:
        if st.query_params.get("_ob") == "done":
            st.session_state._onboarding_done = True
            st.query_params.pop("_ob", None)
            st.rerun()
        st.markdown(
            '<div style="background:linear-gradient(135deg,' + T["accent_light"] + ' 0%,' + T["card"] + ' 100%);'
            'border:1.5px solid ' + T["accent"] + ';border-radius:14px;'
            'padding:1rem 1.4rem .8rem 1.4rem;margin-bottom:.8rem;font-family:DM Sans,sans-serif;">'
            '<div style="font-size:.85rem;font-weight:800;color:' + T["text"] + ';margin-bottom:.6rem;">Benvenuto in VerificAI 👋</div>'
            '<div style="font-size:.78rem;color:' + T["text2"] + ';line-height:1.6;margin-bottom:.7rem;">'
            'Segui le tre fasi indicate nella barra qui sopra:<br>'
            '<span style="color:' + T["accent"] + ';font-weight:700;">① Configura</span> — scegli materia, scuola e argomento, poi premi <em>Genera</em>.<br>'
            '<span style="color:' + T["accent"] + ';font-weight:700;">② Revisione</span> — leggi la bozza, modifica i singoli esercizi se vuoi.<br>'
            '<span style="color:' + T["accent"] + ';font-weight:700;">③ Download</span> — scarica PDF, Word e genera varianti (Fila B, BES/DSA, Soluzioni).'
            '</div>'
            '<a href="?_ob=done" style="font-size:.72rem;color:' + T["muted"] + ';text-decoration:underline;font-family:DM Sans,sans-serif;">Ho capito →</a>'
            '</div>',
            unsafe_allow_html=True
        )

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
        '<span><strong>Suggerimento:</strong> più dettagli fornisci, più la verifica sarà precisa e su misura. '
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
    with st.expander("⚙️ Opzioni verifica", expanded=False):

        # Numero esercizi
        st.markdown(
            '<div style="font-size:.78rem;color:' + T["text2"] + ';margin-bottom:4px;">'
            '<strong>Quanti esercizi</strong> vuoi nella verifica?'
            '</div>',
            unsafe_allow_html=True
        )
        num_esercizi_totali = st.slider(
            "Numero esercizi", min_value=1, max_value=15, value=4,
            label_visibility="collapsed"
        )
        durata_scelta = "1 ora"

        st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)

        # Punteggi + Griglia unificati
        st.markdown(
            '<div style="font-size:.78rem;color:' + T["text2"] + ';margin-bottom:4px;">'
            '<strong>Punteggi e griglia</strong> di valutazione'
            '</div>',
            unsafe_allow_html=True
        )
        punteggi_e_griglia = st.toggle(
            "Aggiungi punteggi e griglia di valutazione",
            value=True,
            help="Aggiunge (X pt) a ogni sottopunto e genera la tabella di valutazione in fondo"
        )
        mostra_punteggi = punteggi_e_griglia
        con_griglia     = punteggi_e_griglia
        if punteggi_e_griglia:
            punti_totali = st.slider(
                "Punti totali", min_value=10, max_value=100, value=100, step=5,
                help="I punti verranno distribuiti automaticamente tra gli esercizi"
            )
        else:
            punti_totali = 100

        st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)

        # Personalizza singoli esercizi
        st.markdown(
            '<div style="font-size:.78rem;color:' + T["text2"] + ';margin-bottom:4px;">'
            '<strong>Personalizza i singoli esercizi</strong> (opzionale)'
            '</div>',
            unsafe_allow_html=True
        )
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
                t = st.selectbox("Tipo", TIPI_ESERCIZIO,
                                 index=TIPI_ESERCIZIO.index(ex.get("tipo","Aperto")),
                                 key=f"tipo_{i}")
                st.session_state.esercizi_custom[i]["tipo"] = t
                d = st.text_input("Descrizione (opzionale)",
                                  value=ex.get("descrizione",""),
                                  placeholder="es. Risolvi l'equazione ax²+bx+c=0",
                                  key=f"desc_{i}")
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
                st.divider()  # Inserito st.divider() come richiesto al posto della linea HR piccola

            if to_remove is not None:
                st.session_state.esercizi_custom.pop(to_remove); st.rerun()

            if st.button("＋ Aggiungi esercizio",
                         disabled=len(st.session_state.esercizi_custom) >= num_esercizi_totali):
                st.session_state.esercizi_custom.append(
                    {"tipo":"Aperto","descrizione":"","immagine":None})
                st.rerun()

        # Note AI piccole, sotto tutto
        st.markdown("<div style='height:.4rem'></div>", unsafe_allow_html=True)
        note_generali = st.text_area(
            "💬 Note per l'AI (opzionale)",
            placeholder=NOTE_PLACEHOLDER.get(materia_scelta,
                         "es. Includi domande sulla definizione, formula e applicazione..."),
            height=68, key="note_area"
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
    else:
        st.markdown(
            '<div class="genera-hint">'
            '<strong style="color:' + T["text2"] + ';">Verrà generata:</strong>'
            ' 📄 Verifica Fila A · Le varianti (Fila B, BES/DSA, Soluzioni) si aggiungono dopo'
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
                immagini_esercizi=imgs_es, file_ispirazione=None,
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
            st.session_state._onboarding_done = True
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
        '<div style="background:' + T["accent"] + ';padding:.85rem 1.2rem;">'
        '<div style="display:flex;align-items:center;gap:12px;">'
        '<span style="font-size:1.5rem;">✏️</span>'
        '<div style="flex:1;">'
        '<div style="font-family:DM Sans,sans-serif;font-size:1rem;font-weight:900;color:#fff;">'
        'Revisione Bozza</div>'
        '<div style="font-size:.72rem;color:#fff;opacity:.85;margin-top:1px;">'
        + materia_str + ' · ' + scuola_str + ' · ' + argomento_str + '</div>'
        '</div>'
        '<div style="background:#ffffff22;border:1px solid #ffffff33;border-radius:20px;'
        'padding:4px 12px;font-size:.68rem;font-weight:700;color:#fff;">'
        + str(n_blocks) + ' ESERCIZI</div>'
        '</div></div>'
        '<div style="padding:.75rem 1.2rem;background:' + T["card"] + ';">'
        '<div style="font-size:.8rem;color:' + T["text2"] + ';line-height:1.5;">'
        'Seleziona un esercizio dal menu, leggi la preview con le formule renderizzate, '
        'poi chiedi all\'AI di <strong>rigenerarlo</strong> se necessario. '
        'Quando sei soddisfatto, premi <strong>Conferma e genera PDF</strong>.'
        '</div></div></div>',
        unsafe_allow_html=True
    )

    if not blocks:
        st.warning("⚠️ Nessun esercizio trovato. Torna indietro e rigenera.")
        if st.button("← Torna alla configurazione"):
            st.session_state.stage = STAGE_INPUT; st.rerun()
        return

    labels = [f"Esercizio {i+1}: {b['title']}" for i, b in enumerate(blocks)]

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
        '💡 Leggi l\'esercizio a sinistra — se qualcosa non va, scrivilo sotto e premi <strong>Modifica</strong>.'
        '</div>',
        unsafe_allow_html=True
    )

    block = blocks[idx]
    title = block["title"]
    body  = block["body"]

    col_ktx, col_pdf = st.columns([3, 2], gap="medium")

    with col_ktx:
        katex_html = _make_katex_html(title, body, T)
        est_height = max(280, min(700, 180 + len(body) // 4))
        components.html(katex_html, height=est_height, scrolling=True)

        if re.search(r"\\begin\{(tikzpicture|axis)\}", body):
            st.info("📊 Questo esercizio contiene grafici TikZ/pgfplots che non si "
                    "possono mostrare qui — sono visibili nel PDF finale.")

    with col_pdf:
        st.markdown(
            '<div style="font-size:.72rem;font-weight:700;color:' + T["muted"] + ';'
            'text-transform:uppercase;letter-spacing:.05em;margin-bottom:.5rem;">'
            '📄 Anteprima PDF completo</div>',
            unsafe_allow_html=True
        )
        imgs = st.session_state.preview_images
        if imgs:
            for pi, img_bytes in enumerate(imgs):
                st.image(img_bytes, use_container_width=True, caption=f"Pagina {pi+1}")
        else:
            vA_pdf = st.session_state.verifiche["A"].get("pdf")
            if vA_pdf:
                b64 = base64.b64encode(vA_pdf).decode()
                st.markdown(
                    '<iframe src="data:application/pdf;base64,' + b64 + '#toolbar=0&navpanes=0&scrollbar=1" '
                    'style="width:100%;height:500px;border:none;border-radius:8px;"></iframe>',
                    unsafe_allow_html=True
                )
            else:
                st.caption("Anteprima non disponibile.")

    st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)
    st.markdown(
        '<div style="font-size:.78rem;color:' + T["text2"] + ';margin-bottom:.4rem;">'
        '<strong>Vuoi cambiare qualcosa?</strong> '
        'Descrivi la modifica e l\'AI rigenererà solo questo esercizio.</div>',
        unsafe_allow_html=True
    )
    col_inp, col_btn = st.columns([4, 1])
    with col_inp:
        istruzione = st.text_area(
            f"Modifica esercizio {idx+1}",
            placeholder="es. Aumenta la difficoltà · Cambia i numeri · Converti in Vero/Falso · Aggiungi un sottopunto",
            key=f"rw_istr_{idx}",
            label_visibility="collapsed",
            height=90,
        )
    with col_btn:
        st.markdown("<div style='height:2.1rem'></div>", unsafe_allow_html=True)
        rigenera = st.button("✏️ Modifica", key=f"rw_btn_{idx}",
                             use_container_width=True, disabled=not istruzione.strip())

    if rigenera and istruzione.strip():
        punti_nota = (
            "Mantieni il formato (X pt) su ogni \\item. "
            "I punti totali verranno ribilanciati automaticamente."
            if mostra_punteggi else "NON inserire punteggi (X pt)."
        )
        _prompt_rw = (
            f"Sei un docente esperto di {materia_str} e LaTeX.\n"
            f"Rigenera SOLO questo esercizio secondo l'istruzione.\n\n"
            f"ESERCIZIO ORIGINALE:\n\\subsection*{{{title}}}\n{body}\n\n"
            f"ISTRUZIONE: {istruzione.strip()}\n\n"
            f"REGOLE:\n"
            f"- Restituisci SOLO il blocco \\subsection*{{...}} con il nuovo esercizio.\n"
            f"- Mantieni struttura LaTeX (\\subsection*, enumerate, \\item[a)], ecc.).\n"
            f"- {punti_nota}\n"
            f"- NON includere preambolo o \\begin{{document}}.\n"
            f"OUTPUT: SOLO codice LaTeX del blocco esercizio."
        )
        with st.spinner(f"⏳ Rigenerando esercizio {idx+1}…"):
            try:
                model_rw_obj = genai.GenerativeModel(modello_rw)
                resp = model_rw_obj.generate_content(_prompt_rw)
                nuovo = resp.text.replace("```latex","").replace("```","").strip()
                m = re.match(r"\\subsection\*\{([^}]*)\}(.*)", nuovo, re.DOTALL)
                if m:
                    st.session_state.review_blocks[idx]["title"] = m.group(1)
                    st.session_state.review_blocks[idx]["body"]  = m.group(2).strip()
                else:
                    st.session_state.review_blocks[idx]["body"] = nuovo
                st.success(f"✅ Esercizio {idx+1} rigenerato!")
                time.sleep(0.4); st.rerun()
            except Exception as e:
                st.error(f"❌ Errore: {e}")

    st.markdown("<div style='height:.4rem'></div>", unsafe_allow_html=True)
    st.markdown(
        '<div style="text-align:center;font-size:.78rem;color:' + T["muted"] + ';padding:.3rem 0;">'
        + str(idx+1) + ' di ' + str(n_blocks) + ' esercizi</div>',
        unsafe_allow_html=True
    )
    st.divider()

    col_back, col_confirm = st.columns([1, 2])
    with col_back:
        if st.button("← Riconfigura", use_container_width=True):
            st.session_state.stage = STAGE_INPUT; st.rerun()
    with col_confirm:
        if st.button("✅ Conferma e genera PDF finale", type="primary", use_container_width=True):
            with st.spinner("⏳ Compilazione PDF finale…"):
                latex_final = _reconstruct_latex(
                    st.session_state.review_preamble,
                    st.session_state.review_blocks
                )
                latex_final = fix_items_environment(latex_final)
                latex_final = rimuovi_vspace_corpo(latex_final)
                if mostra_punteggi:
                    latex_final = rimuovi_punti_subsection(latex_final)
                    latex_final = riscala_punti(latex_final, punti_totali)
                if con_griglia:
                    latex_final = inietta_griglia(latex_final, punti_totali)

                st.session_state.verifiche["A"]["latex"]          = latex_final
                st.session_state.verifiche["A"]["latex_originale"] = latex_final

                pdf_bytes, err = compila_pdf(latex_final)
                if pdf_bytes:
                    st.session_state.verifiche["A"]["pdf"]     = pdf_bytes
                    st.session_state.verifiche["A"]["pdf_ts"]  = time.time()
                    st.session_state.verifiche["A"]["preview"] = True
                    imgs, _ = pdf_to_images_bytes(pdf_bytes)
                    st.session_state.preview_images = imgs or []
                    st.session_state.stage = STAGE_FINAL
                    st.rerun()
                else:
                    st.error("❌ Errore di compilazione PDF.")
                    with st.expander("Log errore"): st.text(err)


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
        '<div style="background:' + T["success"] + ';padding:.85rem 1.2rem;">'
        '<div style="display:flex;align-items:center;gap:12px;">'
        '<span style="font-size:1.5rem;">🎉</span>'
        '<div style="flex:1;">'
        '<div style="font-family:DM Sans,sans-serif;font-size:1rem;font-weight:900;color:#fff;">'
        'Verifica Pronta!</div>'
        '<div style="font-size:.72rem;color:#fff;opacity:.85;margin-top:1px;">'
        + mat_str + ' · ' + scu_str + ' · ' + arg_str + '</div>'
        '</div></div></div>'
        '<div style="padding:.7rem 1.2rem;background:' + T["card"] + ';">'
        '<div style="font-size:.78rem;color:' + T["text2"] + ';line-height:1.5;">'
        '⚠️ Controlla sempre il contenuto prima di distribuire agli studenti. '
        'Il docente è responsabile del materiale finale.'
        '</div></div></div>',
        unsafe_allow_html=True
    )

    # 1. PREVIEW SOPRA
    st.markdown("### 👁 Anteprima")
    imgs = st.session_state.preview_images
    if imgs or vA.get("pdf"):
        with st.expander("Mostra anteprima PDF completo", expanded=True):
            if imgs:
                # Mostriamo le pagine di preview in griglia o orizzontali per risparmiare spazio verticale
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

    # 2. DOWNLOAD E VARIANTI SOTTO
    st.markdown("### 📥 Download e Varianti")

    def _primary_card_unified(label_file, icon, fid, v, suffix, label_custom=None):
        if not (v.get("latex") or v.get("pdf") or v.get("testo")):
            return
        fname = arg_str + "_" + suffix
        btn_label = label_custom if label_custom else f"Scarica {label_file} (PDF)"
        
        # Container unificato
        st.markdown(
            '<div style="background:' + T["bg2"] + ';border:1.5px solid ' + T["border"] + ';'
            'border-radius:12px;padding:.8rem 1rem;margin-bottom:.75rem;">',
            unsafe_allow_html=True
        )

        # ── PDF ──────────────────────────────────────────────────────────────
        if v.get("pdf"):
            st.download_button(
                label=f"📥 {btn_label} · {_stima(v['pdf'])}",
                data=v["pdf"], file_name=fname + ".pdf", mime="application/pdf",
                use_container_width=True, key="dl_pdf_" + fid, type="primary"
            )
        elif v.get("latex"):
            if st.button(f"📄 Compila PDF ({label_file})", key="gen_pdf_" + fid, use_container_width=True):
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
            with st.expander("👁 Mostra soluzioni"):
                st.markdown(v["testo"])

        # ── DOCX ─────────────────────────────────────────────────────────────
        if v.get("latex"):
            _docx_key = "_docx_gen_" + fid
            st.markdown("<div style='height:.35rem'></div>", unsafe_allow_html=True)
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

            # .tex download discreto
            col_tex, _ = st.columns([1, 3])
            with col_tex:
                st.download_button(
                    "⬇ .tex",
                    data=v["latex"].encode("utf-8"),
                    file_name=fname + ".tex", mime="text/plain",
                    key="dl_tex_" + fid,
                    help="Sorgente LaTeX per editor esterno",
                    use_container_width=True,
                )

        st.markdown("</div>", unsafe_allow_html=True)

    # Rendiamo su due colonne solo i blocchi di download generati, così sono ordinati sotto
    col_dl_left, col_dl_right = st.columns(2)
    with col_dl_left:
        _primary_card_unified("Verifica — Fila A", "📄", "A", vA, "FilaA", "Scarica Verifica Fila A (PDF)")
        if vR.get("latex"):
            _primary_card_unified("Versione BES/DSA — Fila A", "🌟", "R", vR, "BES_FilaA", "Scarica Vers. BES/DSA Fila A (PDF)")
    
    with col_dl_right:
        if vB.get("latex"):
            _primary_card_unified("Verifica — Fila B", "📄", "B", vB, "FilaB", "Scarica Verifica Fila B (PDF)")
        if vRB.get("latex"):
            _primary_card_unified("Versione BES/DSA — Fila B", "🌟", "RB", vRB, "BES_FilaB", "Scarica Vers. BES/DSA Fila B (PDF)")
        if vS.get("pdf") or vS.get("testo"):
            _primary_card_unified("Soluzioni", "✅", "S", vS, "Soluzioni", "Scarica Soluzioni (PDF)")


    # ── Genera Varianti on-demand ─────────────────────────────────────────
    st.markdown(
        '<div style="font-size:.78rem;font-weight:700;color:' + T["text2"] + ';'
        'margin:.6rem 0 .4rem 0;">✨ Aggiungi varianti</div>',
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

    # ── Pulsanti di navigazione & Feedback Footer ─────────────────────────────────────────
    st.markdown("<div style='height:.8rem'></div>", unsafe_allow_html=True)
    col_rev, col_new = st.columns(2)
    with col_rev:
        if st.button("← Rivedi esercizi", use_container_width=True):
            st.session_state.stage = STAGE_REVIEW; st.rerun()
    with col_new:
        if st.button("🆕 Nuova Verifica", type="primary", use_container_width=True):
            st.session_state.stage           = STAGE_INPUT
            st.session_state.verifiche        = {
                "A": _vf(), "B": _vf(), "R": _vf(), "RB": _vf(),
                "S": {"latex": None, "testo": None, "pdf": None},
            }
            st.session_state.review_preamble  = ""
            st.session_state.review_blocks    = []
            st.session_state.review_sel_idx   = 0
            st.session_state.gen_params       = {}
            st.session_state.preview_images   = []
            st.session_state.esercizi_custom  = []
            st.rerun()

    # Link feedback abbassato alla fine della pagina (Stage 3)
    st.markdown(
        '<div style="margin-top: 15px; text-align: center; font-size: 0.8rem; font-family: DM Sans, sans-serif;">'
        'Qualcosa non va o hai un suggerimento? '
        '<a href="' + FEEDBACK_FORM_URL + '" target="_blank" style="color:' + T["accent"] + '; font-weight: 600;">Lasciaci un feedback 💬</a>'
        '</div>',
        unsafe_allow_html=True
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  ROUTING
# ═══════════════════════════════════════════════════════════════════════════════

_render_breadcrumb()

# ── FLOATING STAGE INDICATOR ──────────────────────────────────────────────────
_stage_labels = {
    STAGE_INPUT:  ("01", "Configura",  33),
    STAGE_REVIEW: ("02", "Revisione",  66),
    STAGE_FINAL:  ("03", "Download",  100),
}
_sn, _sl, _sp = _stage_labels.get(st.session_state.stage, ("01", "Configura", 33))
st.markdown(
    '<div style="position:fixed;bottom:1.2rem;right:1.2rem;z-index:9999;'
    'background:' + T["card"] + ';border:1.5px solid ' + T["border"] + ';'
    'border-radius:14px;padding:.7rem 1.1rem .65rem 1.1rem;'
    'box-shadow:0 4px 24px rgba(0,0,0,.35);min-width:160px;backdrop-filter:blur(8px);">'
    '<div style="font-size:.6rem;font-weight:800;color:' + T["muted"] + ';'
    'text-transform:uppercase;letter-spacing:.08em;margin-bottom:5px;">Fase attuale</div>'
    '<div style="display:flex;align-items:center;gap:7px;margin-bottom:7px;">'
    '<div style="background:' + T["accent"] + ';border-radius:50%;width:22px;height:22px;'
    'display:flex;align-items:center;justify-content:center;font-size:.65rem;'
    'font-weight:900;color:#fff;flex-shrink:0;">' + _sn + '</div>'
    '<span style="font-size:.8rem;font-weight:700;color:' + T["text"] + ';">' + _sl + '</span>'
    '</div>'
    '<div style="background:' + T["border"] + ';border-radius:100px;height:5px;overflow:hidden;">'
    '<div style="background:linear-gradient(90deg,' + T["accent"] + ',' + T["accent"] + 'aa);'
    'width:' + str(_sp) + '%;height:100%;border-radius:100px;"></div>'
    '</div>'
    '<div style="font-size:.6rem;color:' + T["muted"] + ';margin-top:4px;text-align:right;">'
    + str(_sp) + '% completato</div>'
    '</div>',
    unsafe_allow_html=True
)

_current = st.session_state.stage
if   _current == STAGE_INPUT:  _render_stage_input()
elif _current == STAGE_REVIEW: _render_stage_review()
elif _current == STAGE_FINAL:  _render_stage_final()


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
