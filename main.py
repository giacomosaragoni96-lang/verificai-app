import streamlit as st
import os
import subprocess
import tempfile
import base64
import re
import io
import time
import google.generativeai as genai
from dotenv import load_dotenv

# ── CONFIGURAZIONE ──────────────────────────────────────────────────────────────
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    st.error("⚠️ Chiave API mancante! Crea un file .env con: GOOGLE_API_KEY=la_tua_chiave")
    st.stop()
genai.configure(api_key=API_KEY)

APP_NAME    = "VerificAI"
APP_ICON    = "📝"
APP_TAGLINE = "Crea verifiche su misura in pochi secondi"
SHARE_URL   = "https://verificai.streamlit.app"

# ── TEMI ─────────────────────────────────────────────────────────────────────────
THEMES = {
    "light": {
        "bg":           "#F7F7F5",
        "bg2":          "#FFFFFF",
        "card":         "#FFFFFF",
        "card2":        "#F0EFEB",
        "border":       "#E5E4DF",
        "border2":      "#D1D0CA",
        "text":         "#1A1915",
        "text2":        "#4A4840",
        "muted":        "#8C8A82",
        "accent":       "#D97706",
        "accent_light": "#FEF3C7",
        "accent2":      "#059669",
        "success":      "#059669",
        "warn":         "#D97706",
        "err":          "#DC2626",
        "shadow":       "0 1px 3px rgba(0,0,0,.08), 0 1px 2px rgba(0,0,0,.05)",
        "shadow_md":    "0 4px 12px rgba(0,0,0,.08)",
        "input_bg":     "#FFFFFF",
        "hover":        "#F0EFEB",
    },
    "dark": {
        "bg":           "#0F0F0E",
        "bg2":          "#1A1916",
        "card":         "#1A1916",
        "card2":        "#232320",
        "border":       "#2E2D28",
        "border2":      "#3D3C36",
        "text":         "#F5F4EF",
        "text2":        "#C8C6BC",
        "muted":        "#6B6960",
        "accent":       "#F59E0B",
        "accent_light": "#292215",
        "accent2":      "#10B981",
        "success":      "#10B981",
        "warn":         "#F59E0B",
        "err":          "#EF4444",
        "shadow":       "0 1px 3px rgba(0,0,0,.3)",
        "shadow_md":    "0 4px 16px rgba(0,0,0,.4)",
        "input_bg":     "#232320",
        "hover":        "#232320",
    },
}

if "theme" not in st.session_state:
    st.session_state.theme = "light"
T = THEMES[st.session_state.theme]

MODELLI_DISPONIBILI = {
    "⚡ Flash 2.5 Lite (velocissimo)": "gemini-2.5-flash-lite",
    "⚡ Flash 2.5 (bilanciato)":        "gemini-2.5-flash",
    "🧠 Pro 2.5 (massima qualità)":     "gemini-2.5-pro",
}

SCUOLE = [
    "Scuola Primaria (Elementari)",
    "Scuola Secondaria I grado (Medie)",
    "Liceo Scientifico",
    "Liceo non Scientifico",
    "Istituto Tecnico",
    "Istituto Professionale",
]

CALIBRAZIONE_SCUOLA = {
    "Scuola Primaria (Elementari)": (
        "Livello: Scuola Primaria (6-11 anni). Usa linguaggio semplice, frasi brevi, numeri piccoli (entro 1000). "
        "Almeno un esercizio visivo o di completamento. Niente simboli algebrici o formule."
    ),
    "Scuola Secondaria I grado (Medie)": (
        "Livello: Scuola Media (11-14 anni). Difficoltà intermedia: frazioni, proporzioni, geometria base, prime equazioni. "
        "Un esercizio legato alla vita quotidiana degli studenti."
    ),
    "Liceo Scientifico": (
        "Livello: Liceo Scientifico (14-19 anni). Difficoltà elevata: dimostrazioni, calcolo, notazione avanzata. "
        "Almeno un esercizio che richiede 'dimostrare' o 'giustificare'. Un raccordo interdisciplinare."
    ),
    "Liceo non Scientifico": (
        "Livello: Liceo umanistico/classico/linguistico (14-19 anni). Enfasi su definizioni, argomentazione, analisi. "
        "Formule semplici se presenti. Almeno un collegamento storico-culturale."
    ),
    "Istituto Tecnico": (
        "Livello: Istituto Tecnico (14-19 anni). Orientamento pratico-professionale. "
        "Almeno un esercizio su caso lavorativo reale con unità di misura tecniche."
    ),
    "Istituto Professionale": (
        "Livello: Istituto Professionale (14-19 anni). Esercizi concreti, step guidati, contesto lavorativo esplicito. "
        "Evita calcoli astratti. Almeno un esercizio che simula una situazione professionale reale."
    ),
}

MATERIE = [
    "Matematica", "Fisica", "Chimica", "Biologia", "Scienze della Terra",
    "Italiano", "Storia", "Geografia", "Latino", "Greco",
    "Inglese", "Francese", "Spagnolo", "Tedesco",
    "Filosofia", "Storia dell'Arte", "Musica",
    "Informatica", "Economia", "Diritto",
    "Educazione Civica", "Scienze Motorie",
]

NOTE_PLACEHOLDER = {
    "Matematica":         "es. Includi un esercizio sul teorema di Pitagora e due problemi algebrici.",
    "Fisica":             "es. Un esercizio sulla seconda legge di Newton, uno sul moto uniformemente accelerato.",
    "Chimica":            "es. Bilanciamento di reazioni ed esercizi sulla mole.",
    "Biologia":           "es. Struttura della cellula e ciclo cellulare. Privilegia la comprensione.",
    "Scienze della Terra":"es. Tettonica a placche e ciclo delle rocce. Schema da completare.",
    "Italiano":           "es. Analisi del testo narrativo, figure retoriche. Testo di circa 15 righe.",
    "Storia":             "es. Prima Guerra Mondiale: cause, fasi, conseguenze. Includi una fonte.",
    "Geografia":          "es. Climi e biomi. Una domanda su cartina muta e una su dati demografici.",
    "Latino":             "es. Versione dal De Bello Gallico (40-50 parole). Declinazioni I e II.",
    "Greco":              "es. Versione da Lisia (30-40 parole). Presente e imperfetto attivo.",
    "Inglese":            "es. Reading comprehension (150 parole), present perfect, short writing task.",
    "Francese":           "es. Compréhension écrite, passé composé, production écrite guidée.",
    "Spagnolo":           "es. Comprensión lectora, pretérito indefinido vs imperfecto, escritura breve.",
    "Tedesco":            "es. Leseverstehen, Perfekt und Präteritum, kurze Schreibaufgabe.",
    "Filosofia":          "es. Problema mente-corpo in Cartesio vs Spinoza. Una domanda aperta e una di definizione.",
    "Storia dell'Arte":   "es. Impressionismo: tecnica e confronto Monet/Renoir. Analisi di un'opera.",
    "Musica":             "es. Sonata classica e confronto Mozart/Beethoven. Domande di teoria.",
    "Informatica":        "es. Bubble sort e selection sort. Pseudocodice e complessità computazionale.",
    "Economia":           "es. Domanda e offerta, elasticità dei prezzi. Un esercizio numerico.",
    "Diritto":            "es. Fonti del diritto e gerarchia normativa. Un caso pratico.",
    "Educazione Civica":  "es. Struttura della Costituzione italiana. Diritti e doveri dei cittadini.",
    "Scienze Motorie":    "es. Apparato muscolare e scheletrico. Norme di sicurezza in palestra.",
}

TIPI_ESERCIZIO = ["Aperto", "Scelta multipla", "Vero/Falso", "Completamento"]

# ── FUNZIONI ORIGINALI (invariate) ───────────────────────────────────────────────
def parse_esercizi(latex):
    esercizi = []
    ex_blocks = re.split(r'\\subsection\*\{', latex)[1:]
    for i, block in enumerate(ex_blocks):
        header_match = re.match(r'([^}]*)', block)
        header = header_match.group(1) if header_match else f"Es {i+1}"
        if any(x in header for x in ["Sezione", "Chiusa", "Risposta", "Quesiti"]):
            num_label = "A"
        else:
            num_match = re.search(r'(?:Esercizio\s+)?(\d+)', header)
            num_label = num_match.group(1) if num_match else str(i + 1)
        items_found = []
        lines = block.split('\n')
        for li, line in enumerate(lines):
            item_match = re.search(r'\\item\[([^\]]+)\]', line)
            if not item_match:
                continue
            raw_label = item_match.group(1)
            # Costruisce la finestra di testo: dalla riga corrente
            # fino alla riga prima del prossimo \item (max 8 righe)
            window_lines = []
            for lj in range(li, min(li + 8, len(lines))):
                # Fermati se troviamo un nuovo \item (diverso da quello corrente)
                if lj > li and re.search(r'\\item\[', lines[lj]):
                    break
                window_lines.append(lines[lj])
            search_window = '\n'.join(window_lines)
            pt_match = re.search(r'\((\d+(?:[.,]\d+)?)\s*pt\)', search_window)
            if not pt_match:
                continue
            punti = pt_match.group(1)
            clean_label = raw_label.replace('*', '').strip()
            items_found.append((clean_label, punti))
        if items_found:
            esercizi.append({'num': num_label, 'items': items_found})
    return esercizi

def build_griglia_latex(esercizi, punti_totali):
    if not esercizi:
        return ""
    col_spec = "|l|" + "".join("c|" * len(ex['items']) + "|" for ex in esercizi) + "c|"
    row_es = "\\textbf{Es.}" + "".join(
        f" & \\multicolumn{{{len(ex['items'])}}}{{c||}}{{\\textbf{{{ex['num']}}}}}"
        for ex in esercizi
    ) + " & \\textbf{Tot} \\\\ \\hline"
    row_sotto = "\\textbf{Sotto.}" + "".join(
        f" & {label}" for ex in esercizi for label, _ in ex['items']
    ) + " & \\\\ \\hline"
    row_max = "\\textbf{Max}" + "".join(
        f" & {pts}" for ex in esercizi for _, pts in ex['items']
    ) + f" & {punti_totali} \\\\ \\hline"
    total_cols = sum(len(ex['items']) for ex in esercizi) + 1
    row_punti = "\\textbf{Punti}" + " &" * total_cols + " \\\\ \\hline"
    return (
        "% GRIGLIA\n\\begin{center}\n\\textbf{Griglia di Valutazione}\\\\[0.3cm]\n"
        "{\\renewcommand{\\arraystretch}{1.8}\n"
        f"\\adjustbox{{max width=\\textwidth}}{{\n\\begin{{tabular}}{{{col_spec}}}\n\\hline\n"
        f"{row_es}\n{row_sotto}\n{row_max}\n{row_punti}\n\\end{{tabular}}\n}}}}\n\\end{{center}}"
    )

def inietta_asterischi_bes(latex, percentuale=0.25):
    pattern = r'(\\item\[([a-zA-Z]+)(\*?)\)\])'
    tutti = list(re.finditer(pattern, latex))
    if not tutti:
        return latex
    n_totale = len(tutti)
    n_con_asterisco = sum(1 for m in tutti if m.group(3) == '*')
    n_necessari = max(1, int(n_totale * percentuale + 0.999))
    if n_con_asterisco >= n_necessari:
        return latex
    n_da_aggiungere = n_necessari - n_con_asterisco
    candidati = [m for m in tutti if m.group(3) != '*']
    da_modificare = candidati[-n_da_aggiungere:]
    for m in reversed(da_modificare):
        lettera = m.group(2)
        replacement = f'\\item[{lettera}*)]'
        latex = latex[:m.start()] + replacement + latex[m.end():]
    return latex

def fix_items_environment(latex):
    import re as _r
    lines = latex.split('\n')
    result = []
    list_depth = 0
    in_bare_block = False
    for line in lines:
        stripped = line.strip()
        list_opens  = len(_r.findall(r'\\begin\{(?:enumerate|itemize)', line))
        list_closes = len(_r.findall(r'\\end\{(?:enumerate|itemize)', line))
        is_bare_item = bool(_r.match(r'\\item\[', stripped)) and list_depth == 0
        if is_bare_item and not in_bare_block:
            result.append(r'\begin{enumerate}[a)]')
            in_bare_block = True
        elif not is_bare_item and in_bare_block:
            result.append(r'\end{enumerate}')
            in_bare_block = False
        result.append(line)
        list_depth = max(0, list_depth + list_opens - list_closes)
    if in_bare_block:
        result.append(r'\end{enumerate}')
    return '\n'.join(result)

def inietta_griglia(latex, punti_totali):
    latex = re.sub(
        r'(\\vspace\{[^}]+\}\s*)?\\begin\{center\}\s*\\textbf\{Griglia[^}]*\}.*?\\end\{center\}',
        '', latex, flags=re.DOTALL
    )
    griglia = build_griglia_latex(parse_esercizi(latex), punti_totali)
    if "\\end{document}" in latex:
        return latex.replace("\\end{document}", f"\n\\vfill\n{griglia}\n\\end{{document}}")
    else:
        return latex + f"\n\\vfill\n{griglia}\n\\end{{document}}"

def compila_pdf(codice_latex):
    with tempfile.TemporaryDirectory() as tmpdir:
        tex = os.path.join(tmpdir, "v.tex")
        pdf = os.path.join(tmpdir, "v.pdf")
        with open(tex, "w", encoding="utf-8") as f:
            f.write(codice_latex)
        r = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "-output-directory", tmpdir, tex],
            capture_output=True
        )
        if os.path.exists(pdf):
            return open(pdf, "rb").read(), None
        return None, r.stdout.decode()

def pdf_to_images_bytes(pdf_bytes):
    try:
        from pdf2image import convert_from_bytes as cfb
        pages = cfb(pdf_bytes, dpi=150)
        out = []
        for p in pages:
            buf = io.BytesIO(); p.save(buf, "PNG"); out.append(buf.getvalue())
        return out, None
    except Exception:
        pass
    try:
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "in.pdf")
            with open(src, "wb") as f:
                f.write(pdf_bytes)
            subprocess.run(
                ["pdftoppm", "-png", "-r", "150", src, os.path.join(d, "p")],
                capture_output=True, check=True
            )
            imgs = sorted(f for f in os.listdir(d) if f.startswith("p") and f.endswith(".png"))
            if imgs:
                return [open(os.path.join(d, f), "rb").read() for f in imgs], None
    except Exception as e:
        return None, str(e)
    return None, "pdf2image non installato e pdftoppm non trovato."

def _make_tc_xml(text, width_dxa, bold=False, gridSpan=1):
    from docx.oxml.ns import qn as _qn
    from docx.oxml import OxmlElement as _OE
    tc = _OE('w:tc')
    tcPr = _OE('w:tcPr')
    tc.append(tcPr)
    if gridSpan > 1:
        gs = _OE('w:gridSpan')
        gs.set(_qn('w:val'), str(gridSpan))
        tcPr.append(gs)
    tcW = _OE('w:tcW')
    tcW.set(_qn('w:w'), str(width_dxa))
    tcW.set(_qn('w:type'), 'dxa')
    tcPr.append(tcW)
    p = _OE('w:p'); tc.append(p)
    pPr = _OE('w:pPr'); p.append(pPr)
    jc = _OE('w:jc'); jc.set(_qn('w:val'), 'center'); pPr.append(jc)
    if text:
        r_el = _OE('w:r'); p.append(r_el)
        if bold:
            rPr = _OE('w:rPr'); b_el = _OE('w:b'); rPr.append(b_el); r_el.append(rPr)
        t = _OE('w:t'); t.text = str(text); r_el.append(t)
    return tc

def _fix_tbl_grid(tbl_el, col_widths, _qn, _OE):
    old_grid = tbl_el.find(_qn('w:tblGrid'))
    if old_grid is not None:
        tbl_el.remove(old_grid)
    new_grid = _OE('w:tblGrid')
    for w in col_widths:
        gc = _OE('w:gridCol')
        gc.set(_qn('w:w'), str(max(1, w)))
        new_grid.append(gc)
    tbl_pr = tbl_el.find(_qn('w:tblPr'))
    if tbl_pr is not None:
        tbl_pr.addnext(new_grid)
    else:
        tbl_el.insert(0, new_grid)

def _build_griglia_xml(doc, row_es, row_sotto, row_max, PAGE_W_DXA=9638):
    from docx.oxml.ns import qn as _qn
    from docx.oxml import OxmlElement as _OE
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Pt

    n_cols = len(row_es)
    row_punti = ["Punti"] + [""] * (n_cols - 1)

    first_col = 1400
    last_col = 900
    n_mid = max(1, n_cols - 2)
    available = PAGE_W_DXA - first_col - last_col
    mid_col = max(400, available // n_mid)
    col_widths = [first_col] + [mid_col] * n_mid + [last_col]
    diff = PAGE_W_DXA - sum(col_widths)
    col_widths[-1] += diff

    def _setup_tbl(tbl, total_w, widths):
        tbl_el = tbl._tbl
        tbl_pr = tbl_el.find(_qn('w:tblPr'))
        if tbl_pr is None:
            tbl_pr = _OE('w:tblPr'); tbl_el.insert(0, tbl_pr)
        tbl_w = _OE('w:tblW')
        tbl_w.set(_qn('w:w'), str(total_w)); tbl_w.set(_qn('w:type'), 'dxa')
        ex = tbl_pr.find(_qn('w:tblW'))
        if ex is not None: tbl_pr.remove(ex)
        tbl_pr.append(tbl_w)
        tbl_lay = _OE('w:tblLayout'); tbl_lay.set(_qn('w:type'), 'fixed')
        ex2 = tbl_pr.find(_qn('w:tblLayout'))
        if ex2 is not None: tbl_pr.remove(ex2)
        tbl_pr.append(tbl_lay)
        tbl_cm = _OE('w:tblCellMar')
        for side in ('top', 'left', 'bottom', 'right'):
            cm_el = _OE(f'w:{side}')
            cm_el.set(_qn('w:w'), '50'); cm_el.set(_qn('w:type'), 'dxa')
            tbl_cm.append(cm_el)
        ex3 = tbl_pr.find(_qn('w:tblCellMar'))
        if ex3 is not None: tbl_pr.remove(ex3)
        tbl_pr.append(tbl_cm)
        _fix_tbl_grid(tbl_el, widths, _qn, _OE)

    def _fill_cell(cell, text, bold=False, w=None, font_pt=9):
        cell.text = str(text)
        cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in cell.paragraphs[0].runs:
            run.font.size = Pt(font_pt)
            if bold: run.bold = True
        if w is not None:
            tc = cell._tc; tcPr = tc.get_or_add_tcPr()
            tcW = _OE('w:tcW'); tcW.set(_qn('w:w'), str(w)); tcW.set(_qn('w:type'), 'dxa')
            ex = tcPr.find(_qn('w:tcW'))
            if ex is not None: tcPr.remove(ex)
            tcPr.append(tcW)

    tbl = doc.add_table(rows=4, cols=n_cols)
    tbl.style = 'Table Grid'
    _setup_tbl(tbl, PAGE_W_DXA, col_widths)

    for r_idx, riga in enumerate([row_sotto, row_max, row_punti], start=1):
        for c_idx in range(n_cols):
            val = riga[c_idx] if c_idx < len(riga) else ''
            _fill_cell(tbl.cell(r_idx, c_idx), val,
                       bold=(c_idx == 0),
                       w=col_widths[c_idx] if c_idx < len(col_widths) else mid_col)

    groups = []
    c = 0
    while c < n_cols:
        val = row_es[c] if c < len(row_es) else ''
        if c == 0 or c == n_cols - 1:
            groups.append((val, 1, col_widths[c]))
            c += 1
        else:
            span = 1
            while (c + span < n_cols - 1 and
                   c + span < len(row_es) and
                   row_es[c + span] == val):
                span += 1
            total_w = sum(col_widths[c:c + span])
            groups.append((val, span, total_w))
            c += span

    tr_el = tbl.rows[0]._tr
    for tc_el in list(tr_el.findall(_qn('w:tc'))):
        tr_el.remove(tc_el)
    for label, span, width in groups:
        tr_el.append(_make_tc_xml(label, width, bold=True, gridSpan=span))

    return tbl

def _strip_latex_math(text):
    import re as _r
    if not text: return text
    text = _r.sub(r'\$\$(.+?)\$\$', lambda m: m.group(1).strip(), text, flags=_r.DOTALL)
    text = _r.sub(r'\$(.+?)\$',    lambda m: m.group(1).strip(), text)
    text = _r.sub(r'\\mathcal\{([^}]+)\}', r'\1', text)
    text = _r.sub(r'\\mathbf\{([^}]+)\}',  r'\1', text)
    text = _r.sub(r'\\mathrm\{([^}]+)\}',  r'\1', text)
    text = _r.sub(r'\\text\{([^}]+)\}',    r'\1', text)
    text = _r.sub(r'\\frac\{([^}]+)\}\{([^}]+)\}', r'(\1)/(\2)', text)
    text = _r.sub(r'\\sqrt\{([^}]+)\}',    r'sqrt(\1)', text)
    text = _r.sub(r'\^\{([^}]+)\}',         r'^\1', text)
    text = _r.sub(r'_\{([^}]+)\}',          r'_\1', text)
    for fr, to in [
        ("\\\\leq", "\u2264"), ("\\\\geq", "\u2265"), ("\\\\neq", "\u2260"),
        ("\\\\approx","\u2248"), ("\\\\cdot","\u00b7"), ("\\\\times","\u00d7"),
        ("\\\\pm","\u00b1"),  ("\\\\infty","\u221e"), ("\\\\alpha","\u03b1"),
        ("\\\\beta","\u03b2"), ("\\\\gamma","\u03b3"), ("\\\\delta","\u03b4"),
        ("\\\\theta","\u03b8"), ("\\\\pi","\u03c0"), ("\\\\sin","sin"),
        ("\\\\cos","cos"), ("\\\\tan","tan"), ("\\\\log","log"),
        ("\\\\ln","ln"), ("\\\\lim","lim"), ("\\\\forall","\u2200"),
        ("\\\\exists","\u2203"), ("\\\\in","\u2208"), ("\\\\notin","\u2209"),
        ("\\\\subset","\u2282"), ("\\\\cup","\u222a"), ("\\\\cap","\u2229"),
        ("\\\\emptyset","\u2205"), ("^2","\u00b2"), ("^3","\u00b3"),
        ("\\\\left(","("), ("\\\\right)",")"),
        ("\\\\left[","["), ("\\\\right]","]"),
    ]:
        text = text.replace(fr, to)
    text = _r.sub(r'\\[a-zA-Z]+\{([^}]*)\}', r'\1', text)
    text = _r.sub(r'\\[a-zA-Z]+', '', text)
    text = text.replace('{', '').replace('}', '')
    return text.strip()

def _clean_latex_line(text):
    import re as _r
    if not text:
        return ''
    text = _r.sub(r'\\vspace\*?\{[^}]*\}', '', text)
    text = _r.sub(r'\\hspace\*?\{[^}]*\}', '', text)
    text = _r.sub(r'\\noindent\b', '', text)
    text = _r.sub(r'\\newline\b', '', text)
    text = _r.sub(r'\\\\(\s)', r'\1', text)
    text = _r.sub(r'\\\\\s*$', '', text, flags=_r.MULTILINE)
    for cmd in ('textbf', 'textit', 'emph', 'underline', 'textrm', 'texttt'):
        text = _r.sub(rf'\\{cmd}\{{([^}}]*)\}}', r'\1', text)
    text = _r.sub(r'\\(?:small|large|Large|LARGE|huge|Huge|normalsize|footnotesize)\b', '', text)
    return _strip_latex_math(text).strip()


def _parse_latex_to_data(codice_latex):
    import re as _r
    data = {'titolo': '', 'intestazione_nota': '', 'esercizi': []}

    m = _r.search(r'\\textbf\{\\large ([^}]+)\}', codice_latex)
    if m:
        data['titolo'] = _clean_latex_line(m.group(1))

    m2 = _r.search(r'\\textit\{\\small ([^}]+)\}', codice_latex)
    if m2:
        data['intestazione_nota'] = m2.group(1).strip()

    body_start = codice_latex.find('\\end{center}')
    if body_start == -1:
        body_start = 0
    else:
        body_start += len('\\end{center}')
    corpus = codice_latex[body_start:]
    corpus = corpus.replace('\\end{document}', '')

    blocks = _r.split(r'\\subsection\*\s*\{', corpus)

    for block in blocks[1:]:
        brace_depth = 0
        header_end = 0
        for ci, ch in enumerate(block):
            if ch == '{': brace_depth += 1
            elif ch == '}':
                if brace_depth == 0:
                    header_end = ci
                    break
                brace_depth -= 1
        titolo_ex = _clean_latex_line(block[:header_end])
        body = block[header_end+1:]

        first_item = len(body)
        for marker in [r'\\item[', r'\\begin{enumerate}', r'\\begin{itemize}']:
            idx = body.find(marker.replace('\\\\','\\'))
            if idx != -1 and idx < first_item:
                first_item = idx
        raw_intro = body[:first_item]
        raw_intro = _r.sub(r'\\begin\{tabular\}.*?\\end\{tabular\}', '', raw_intro, flags=_r.DOTALL)
        raw_intro = _r.sub(r'\\begin\{center\}.*?\\end\{center\}', '', raw_intro, flags=_r.DOTALL)
        testo_intro = _clean_latex_line(raw_intro)

        sottopunti = []

        enum_pat = _r.compile(
            r'\\begin\{enumerate\}\s*\[a\)\]\s*(.*?)\\end\{enumerate\}',
            _r.DOTALL
        )
        used_ranges = []

        for em in enum_pat.finditer(body):
            used_ranges.append((em.start(), em.end()))
            items_block = em.group(1)

            item_pat = _r.compile(
                r'\\item\[([^\]]+)\]\s*(.*?)(?=\\item\[|$)',
                _r.DOTALL
            )
            for im in item_pat.finditer(items_block):
                label = im.group(1).strip()
                raw_text = im.group(2).strip()
                opzioni = []

                inner_enum = _r.search(
                    r'\\begin\{enumerate\}\s*\[a\)\](.*?)\\end\{enumerate\}',
                    raw_text, _r.DOTALL
                )
                if inner_enum:
                    for opt_m in _r.finditer(r'\\item\s+(.*?)(?=\\item|$)', inner_enum.group(1), _r.DOTALL):
                        opt_c = _clean_latex_line(opt_m.group(1))
                        if opt_c: opzioni.append(opt_c)
                    raw_text = raw_text[:inner_enum.start()].strip()

                vf_pairs = _r.findall(r'\$\\square\$\s*\\textbf\{([VF])\}', raw_text)
                if vf_pairs:
                    opzioni = [f"☐ {v}" for v in vf_pairs]
                    raw_text = _r.sub(r'\$\\square\$\s*\\textbf\{[VF]\}\s*(?:\\quad)?', '', raw_text).strip()

                testo_clean = _clean_latex_line(raw_text)
                testo_clean = _r.sub(r'\n{2,}', '\n', testo_clean).strip()

                if label:
                    sottopunti.append({
                        'label': label,
                        'testo': testo_clean if testo_clean else '',
                        'opzioni': opzioni,
                        'punti': _estrai_punti(label + ' ' + testo_clean)
                    })

        if not sottopunti:
            for im in _r.finditer(
                r'\\item\[([^\]]+)\]\s*(.*?)(?=\\item\[|\\end\{|$)',
                body, _r.DOTALL
            ):
                label = im.group(1).strip()
                raw_text = im.group(2).strip()
                skip = any(s <= im.start() <= e for s, e in used_ranges)
                if skip: continue
                opzioni = []
                inner_enum = _r.search(
                    r'\\begin\{enumerate\}\s*\[a\)\](.*?)\\end\{enumerate\}',
                    raw_text, _r.DOTALL
                )
                if inner_enum:
                    for opt_m in _r.finditer(r'\\item\s+(.*?)(?=\\item|$)', inner_enum.group(1), _r.DOTALL):
                        opt_c = _clean_latex_line(opt_m.group(1))
                        if opt_c: opzioni.append(opt_c)
                    raw_text = raw_text[:inner_enum.start()].strip()
                testo_clean = _clean_latex_line(raw_text)
                testo_clean = _r.sub(r'\n{2,}', '\n', testo_clean).strip()
                if label:
                    sottopunti.append({
                        'label': label,
                        'testo': testo_clean if testo_clean else '',
                        'opzioni': opzioni,
                        'punti': _estrai_punti(label + ' ' + testo_clean)
                    })

        if titolo_ex or sottopunti:
            data['esercizi'].append({
                'titolo': titolo_ex,
                'testo_intro': testo_intro,
                'sottopunti': sottopunti
            })
    return data


def _estrai_punti(text):
    import re as _r
    m = _r.search(r'\((\d+(?:[.,]\d+)?)\s*pt\)', text)
    return m.group(1) if m else ''

def latex_to_docx_via_ai(codice_latex, model, con_griglia=True):
    try:
        from docx import Document as DocxDocument
        from docx.shared import Pt, Cm
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.oxml.ns import qn as _qn
        from docx.oxml import OxmlElement as _OE
    except ImportError:
        return None, "python-docx non installato. Esegui: pip install python-docx"

    try:
        data = _parse_latex_to_data(codice_latex)
    except Exception as e:
        import traceback
        return None, f"Errore parsing LaTeX: {e}\n{traceback.format_exc()}"

    try:
        doc = DocxDocument()
        MARGIN_CM = 1.5
        PAGE_W_DXA = int((21.0 - 2 * MARGIN_CM) / 2.54 * 1440)
        GRIGLIA_W_DXA = PAGE_W_DXA - 80

        for section in doc.sections:
            section.page_width    = Cm(21.0)
            section.page_height   = Cm(29.7)
            section.left_margin   = Cm(MARGIN_CM); section.right_margin  = Cm(MARGIN_CM)
            section.top_margin    = Cm(MARGIN_CM); section.bottom_margin = Cm(MARGIN_CM)

        style = doc.styles['Normal']
        style.font.name = 'Arial'; style.font.size = Pt(11)

        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        rt = p.add_run(data.get('titolo', 'Verifica'))
        rt.bold = True; rt.font.size = Pt(14)

        _cw = [int(PAGE_W_DXA * 0.62), PAGE_W_DXA - int(PAGE_W_DXA * 0.62)]
        hdr_tbl = doc.add_table(rows=1, cols=2)
        hdr_el = hdr_tbl._tbl
        tblPr_h = hdr_el.find(_qn('w:tblPr'))
        if tblPr_h is None:
            tblPr_h = _OE('w:tblPr'); hdr_el.insert(0, tblPr_h)
        for tag_h, attrs_h in [
            ('w:tblW',      {'w:w': str(PAGE_W_DXA), 'w:type': 'dxa'}),
            ('w:tblLayout', {'w:type': 'fixed'}),
        ]:
            el_h = _OE(tag_h)
            for k_h, v_h in attrs_h.items(): el_h.set(_qn(k_h), v_h)
            ex_h = tblPr_h.find(_qn(tag_h))
            if ex_h is not None: tblPr_h.remove(ex_h)
            tblPr_h.append(el_h)
        tblB_h = _OE('w:tblBorders')
        for side_h in ('top','left','bottom','right','insideH','insideV'):
            b_h = _OE(f'w:{side_h}'); b_h.set(_qn('w:val'), 'nil'); tblB_h.append(b_h)
        ex_b_h = tblPr_h.find(_qn('w:tblBorders'))
        if ex_b_h is not None: tblPr_h.remove(ex_b_h)
        tblPr_h.append(tblB_h)
        _fix_tbl_grid(hdr_el, _cw, _qn, _OE)
        hdr_cells_data = [
            [("Nome: ", "_______________________________")],
            [("Classe e Data: ", "______________________")],
        ]
        for ci_h, runs in enumerate(hdr_cells_data):
            cell_h = hdr_tbl.cell(0, ci_h)
            tc_h = cell_h._tc; tcPr_h = tc_h.get_or_add_tcPr()
            tcW_h = _OE('w:tcW'); tcW_h.set(_qn('w:w'), str(_cw[ci_h])); tcW_h.set(_qn('w:type'),'dxa')
            ex_w_h = tcPr_h.find(_qn('w:tcW'))
            if ex_w_h is not None: tcPr_h.remove(ex_w_h)
            tcPr_h.append(tcW_h)
            tcBdr_h = _OE('w:tcBorders')
            for s_h in ('top','left','bottom','right'):
                b2_h = _OE(f'w:{s_h}'); b2_h.set(_qn('w:val'),'nil'); tcBdr_h.append(b2_h)
            ex_bdr_h = tcPr_h.find(_qn('w:tcBorders'))
            if ex_bdr_h is not None: tcPr_h.remove(ex_bdr_h)
            tcPr_h.append(tcBdr_h)
            p_h = cell_h.paragraphs[0]
            for lbl_h, line_h in runs:
                r1_h = p_h.add_run(lbl_h); r1_h.bold = True; r1_h.font.size = Pt(10)
                r2_h = p_h.add_run(line_h); r2_h.font.size = Pt(10)

        nota = data.get('intestazione_nota', '')
        if nota:
            p3 = doc.add_paragraph(); p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r3 = p3.add_run(nota); r3.italic = True; r3.font.size = Pt(10)
        doc.add_paragraph()

        for ex in data.get('esercizi', []):
            pe = doc.add_paragraph()
            pe.paragraph_format.space_before = Pt(10)
            pe.paragraph_format.space_after = Pt(3)
            rt = pe.add_run(ex.get('titolo', '')); rt.bold = True; rt.font.size = Pt(12)
            intro = ex.get('testo_intro', '').strip()
            if intro:
                pi = doc.add_paragraph(intro)
                pi.paragraph_format.space_before = Pt(0)
                pi.paragraph_format.space_after = Pt(3)
            for sp in ex.get('sottopunti', []):
                label = sp.get('label', '').strip()
                testo = sp.get('testo', '').strip()
                opzioni = sp.get('opzioni', [])
                ps = doc.add_paragraph()
                ps.paragraph_format.left_indent = Cm(0.4)
                ps.paragraph_format.space_before = Pt(2)
                ps.paragraph_format.space_after = Pt(2)
                rl = ps.add_run(label + "  "); rl.bold = True; rl.font.size = Pt(11)
                if testo:
                    ps.add_run(testo).font.size = Pt(11)
                if opzioni:
                    for opt in opzioni:
                        po = doc.add_paragraph()
                        po.paragraph_format.left_indent = Cm(1.2)
                        po.paragraph_format.space_before = Pt(0)
                        po.paragraph_format.space_after = Pt(1)
                        po.add_run(str(opt)).font.size = Pt(11)
                if not opzioni:
                    pr = doc.add_paragraph()
                    pr.paragraph_format.left_indent = Cm(0.4)
                    pr.paragraph_format.space_before = Pt(1)
                    pr.paragraph_format.space_after = Pt(8)

        esercizi_parsed = parse_esercizi(codice_latex) if con_griglia else []
        if con_griglia and esercizi_parsed:
            pg = doc.add_paragraph()
            rg = pg.add_run("Griglia di Valutazione"); rg.bold = True; rg.font.size = Pt(12)
            pg.alignment = WD_ALIGN_PARAGRAPH.CENTER; pg.paragraph_format.space_before = Pt(12)

            n_sotto_totali = sum(len(ex['items']) for ex in esercizi_parsed)
            if n_sotto_totali > 12:
                row_es = ["Es."]
                row_max = ["Max"]
                for ex in esercizi_parsed:
                    row_es.append(f"Es. {ex['num']}")
                    tot_ex = 0
                    for _, pts in ex['items']:
                        try: tot_ex += float(pts.replace(',','.'))
                        except: pass
                    row_max.append(str(int(tot_ex)) if tot_ex == int(tot_ex) else str(round(tot_ex,1)))
                row_es.append("Tot")
                tot_pts = sum(float(x.replace(',','.')) for x in row_max[1:] if x.replace(',','.').replace('.','').isdigit())
                row_max.append(str(int(tot_pts)) if tot_pts == int(tot_pts) else str(round(tot_pts,1)))
                row_sotto_c = [""] * len(row_es)
                _build_griglia_xml(doc, row_es, row_sotto_c, row_max, GRIGLIA_W_DXA)
            else:
                row_es = ["Es."]; row_sotto = ["Sotto."]; row_max = ["Max"]
                for ex in esercizi_parsed:
                    for label_clean, pts in ex['items']:
                        lbl = label_clean.replace('*','').replace(')','').strip()[:3]
                        row_es.append(str(ex['num']))
                        row_sotto.append(lbl)
                        row_max.append(str(pts))
                row_es.append("Tot"); row_sotto.append("")
                tot_pts = 0
                for x in row_max[1:]:
                    try: tot_pts += float(x.replace(',','.'))
                    except: pass
                row_max.append(str(int(tot_pts)) if tot_pts == int(tot_pts) else str(round(tot_pts,1)))
                if len(row_es) >= 3:
                    _build_griglia_xml(doc, row_es, row_sotto, row_max, GRIGLIA_W_DXA)

        buf = io.BytesIO(); doc.save(buf)
        return buf.getvalue(), None

    except Exception as e:
        import traceback
        return None, f"Errore DOCX: {e}\n{traceback.format_exc()}"

def costruisci_prompt_esercizi(esercizi_custom, num_totale, punti_totali):
    n_liberi = max(0, num_totale - len(esercizi_custom))
    righe = [f"\nSTRUTTURA ESERCIZI (totale: {num_totale}):"]
    immagini = []
    for i, ex in enumerate(esercizi_custom, 1):
        tipo, desc = ex['tipo'], ex['descrizione'].strip()
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
        righe.append(f"- Genera altri {n_liberi} esercizi liberi coerenti con l'argomento.")
    righe.append(f"Distribuisci {punti_totali} pt in modo equilibrato.")
    return "\n".join(righe), immagini

# ── HELPER: formato tempo relativo ───────────────────────────────────────────────
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
    """Stima dimensione leggibile."""
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
            'pdf_ts': None, 'docx_ts': None}

if 'verifiche'       not in st.session_state: st.session_state.verifiche = {'A': _vf(), 'B': _vf()}
if 'esercizi_custom' not in st.session_state: st.session_state.esercizi_custom = []
# Status bar state
if 'last_materia'    not in st.session_state: st.session_state.last_materia = None
if 'last_argomento'  not in st.session_state: st.session_state.last_argomento = None
if 'last_gen_ts'     not in st.session_state: st.session_state.last_gen_ts = None

# ── CSS GLOBALE ──────────────────────────────────────────────────────────────────
is_dark = (st.session_state.theme == "dark")

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

  /* Header: stessa bg dell'app, così il bottone sidebar si vede sempre */
  header[data-testid="stHeader"] {{
    background-color: {T['bg']} !important;
    border-bottom: 1px solid {T['border']} !important;
  }}

  /* Forza colore icona/bottone toggle sidebar con specificity massima */
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

  /* ════════════════════════════════════
     SIDEBAR
     ════════════════════════════════════ */
  [data-testid="stSidebar"] {{
    background: #141412 !important;
    border-right: 1px solid #2a2926 !important;
  }}

  /* Titolo principale sidebar */
  .sidebar-title {{
    font-family: 'DM Sans', sans-serif;
    font-size: 1.1rem !important;
    font-weight: 800 !important;
    letter-spacing: -0.01em;
    color: #f0ede6 !important;
    margin: 0.5rem 0 1.2rem 0;
    padding-bottom: 0.6rem;
    border-bottom: 1px solid #2a2926;
  }}

  /* Etichette sezione sidebar — più visibili */
  .sidebar-label {{
    font-size: 0.75rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.06em !important;
    text-transform: uppercase !important;
    color: #b0ad9f !important;
    margin: 0.8rem 0 0.4rem 0;
    padding-bottom: 0.25rem;
    border-bottom: 1px solid #2a2926;
  }}
  [data-testid="stSidebar"] .block-container {{
    padding: 1.5rem 1.2rem !important;
    max-width: 100% !important;
  }}
  [data-testid="stSidebar"] p,
  [data-testid="stSidebar"] span,
  [data-testid="stSidebar"] label,
  [data-testid="stSidebar"] div {{
    color: #d4d2c9 !important;
  }}
  [data-testid="stSidebar"] .stTextInput label p,
  [data-testid="stSidebar"] .stSelectbox label p,
  [data-testid="stSidebar"] .stNumberInput label p {{
    color: #8a8880 !important;
    font-size: 0.7rem !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    font-weight: 700 !important;
  }}
  [data-testid="stSidebar"] .stCheckbox label {{
    color: #d4d2c9 !important;
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
    color: #f0ede6 !important;
  }}
  [data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] > div:first-child {{
    background: #232320 !important;
    border: 1.5px solid #3d3c36 !important;
    border-radius: 8px !important;
  }}
  [data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] span {{
    color: #f0ede6 !important;
  }}
  [data-testid="stSidebar"] .stRadio label {{
    color: #d4d2c9 !important;
  }}
  [data-testid="stSidebar"] .stRadio [data-testid="stMarkdownContainer"] p {{
    color: #d4d2c9 !important;
  }}
  [data-testid="stSidebar"] .stButton button {{
    background: #232320 !important;
    color: #f0ede6 !important;
    border: 1.5px solid #3d3c36 !important;
    border-radius: 8px !important;
  }}
  [data-testid="stSidebar"] .stButton button:hover {{
    background: #2e2d28 !important;
    border-color: #5a5950 !important;
  }}
  [data-testid="stSidebar"] .stSelectSlider [data-testid="stMarkdownContainer"] p {{
    color: #d4d2c9 !important;
  }}
  [data-testid="stSidebar"] .section-label {{
    color: #5a5950 !important;
    border-bottom-color: #2a2926 !important;
  }}
  [data-testid="collapsedControl"] {{
    color: {T['text']} !important;
    top: 1rem !important;
  }}

  /* ── TYPOGRAPHY ── */
  h1, h2, h3 {{
    font-family: 'DM Sans', sans-serif !important;
    color: {T['text']} !important;
    letter-spacing: -0.02em;
  }}

  /* ── HERO HEADER ── */
  .hero-wrap {{
    margin-bottom: 2.5rem;
    padding-bottom: 1.5rem;
    border-bottom: 1px solid {T['border']};
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 0.75rem;
  }}
  .hero-left {{ flex: 1; min-width: 200px; }}
  .hero-title {{
    font-family: 'DM Sans', sans-serif;
    font-size: clamp(1.6rem, 5vw, 2.2rem);
    font-weight: 800;
    color: {T['text']};
    line-height: 1.15;
    margin: 0 0 0.3rem 0;
    letter-spacing: -0.03em;
  }}
  .hero-sub {{
    font-size: 0.9rem;
    color: {T['muted']};
    margin: 0;
    font-weight: 400;
  }}
  .hero-right {{
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-shrink: 0;
    padding-top: 4px;
  }}
  .share-link {{
    font-size: 0.72rem;
    font-weight: 500;
    color: {T['muted']};
    text-decoration: none;
    letter-spacing: 0.01em;
    opacity: 0.7;
    transition: all 0.2s ease;
    white-space: nowrap;
    border-bottom: 1px dashed {T['border2']};
    padding-bottom: 1px;
  }}
  .share-link:hover {{
    color: {T['accent']};
    opacity: 1;
    border-bottom-color: {T['accent']};
  }}
  @media (max-width: 640px) {{
    .share-link {{ display: none; }}
  }}

  /* ── LABELS ── */
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

  /* ── INPUTS ── */
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

  /* ── SELECTBOX ── */
  .stSelectbox [data-baseweb="select"] > div:first-child {{
    background: {T['input_bg']} !important;
    border: 1.5px solid {T['border']} !important;
    border-radius: 10px !important;
    color: {T['text']} !important;
  }}
  .stSelectbox [data-baseweb="select"] span {{
    color: {T['text']} !important;
  }}

  /* ── CHECKBOXES ── */
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

  /* ════════════════════════════════════
     BOTTONE PRIMARIO
     ════════════════════════════════════ */
  .stButton [data-testid="baseButton-primary"],
  .stButton button[kind="primary"],
  button[data-testid="baseButton-primary"] {{
    background: #D97706 !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 12px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 1rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.01em !important;
    padding: 0.8rem 2rem !important;
    transition: transform 0.15s ease, filter 0.15s ease !important;
    box-shadow: 0 2px 12px rgba(217,119,6,0.35) !important;
  }}
  .stButton [data-testid="baseButton-primary"]:hover,
  button[data-testid="baseButton-primary"]:hover {{
    filter: brightness(1.08) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 18px rgba(217,119,6,0.45) !important;
  }}

  /* ── BOTTONI SECONDARI ── */
  .stButton [data-testid="baseButton-secondary"],
  .stButton button[kind="secondary"],
  button[data-testid="baseButton-secondary"] {{
    background: {T['card']} !important;
    color: {T['text']} !important;
    border: 1.5px solid {T['border2']} !important;
    border-radius: 10px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.88rem !important;
    font-weight: 600 !important;
    padding: 0.6rem 1.2rem !important;
    transition: all 0.15s ease !important;
  }}
  .stButton [data-testid="baseButton-secondary"]:hover,
  button[data-testid="baseButton-secondary"]:hover {{
    background: {T['hover']} !important;
    border-color: {T['accent']} !important;
    color: {T['text']} !important;
  }}

  /* ── COMPACT UPLOADER — solo bottone, no drag&drop ── */
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

  /* ── TEX DOWNLOAD — piccolo e discreto ── */
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
  }}
  .tex-btn-wrap .stDownloadButton button:hover,
  .tex-btn-wrap [data-testid="stDownloadButton"] button:hover {{
    color: {T['text2']} !important;
    border-color: #5a5950 !important;
    background: {T['card2']} !important;
  }}

  /* ── DOWNLOAD BUTTONS ── */
  .stDownloadButton button,
  [data-testid="stDownloadButton"] button {{
    background: {T['card']} !important;
    color: {T['text']} !important;
    border: 1.5px solid {T['border2']} !important;
    border-radius: 10px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.88rem !important;
    font-weight: 600 !important;
    padding: 0.6rem 1.2rem !important;
    transition: all 0.15s ease !important;
  }}
  .stDownloadButton button:hover,
  [data-testid="stDownloadButton"] button:hover {{
    background: {T['hover']} !important;
    border-color: {T['accent']} !important;
  }}

  /* ── EXPANDER ── */
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

  /* ── CARD OUTPUT ── */
  .output-card {{
    background: {T['card']};
    border: 1px solid {T['border']};
    border-radius: 16px;
    padding: 1.5rem;
    box-shadow: {T['shadow']};
  }}
  .output-title {{
    font-family: 'DM Sans', sans-serif;
    font-size: 1.1rem;
    font-weight: 700;
    color: {T['text']};
    margin: 0 0 1rem 0;
  }}

  /* ── BADGE CHIP ── */
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

  /* ── SECTION LABELS ── */
  /* Headings visibili dentro le tendine */
  .expander-heading {{
    font-size: 0.8rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.03em !important;
    text-transform: uppercase !important;
    color: {T['text']} !important;
    margin: 1rem 0 0.4rem 0 !important;
    padding: 5px 10px !important;
    background: {T['card2']} !important;
    border-left: 3px solid {T['accent']} !important;
    border-radius: 0 6px 6px 0 !important;
    display: block !important;
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

  /* ════════════════════════════════════
     STATUS BAR
     ════════════════════════════════════ */
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

  /* ════════════════════════════════════
     DOWNLOAD CARD
     ════════════════════════════════════ */
  .dl-card {{
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 16px;
    background: {T['card']};
    border: 1.5px solid {T['border']};
    border-radius: 12px;
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
    margin-bottom: 8px;
  }}
  .dl-card:hover {{
    border-color: {T['accent']};
    box-shadow: 0 2px 12px rgba(217,119,6,0.12);
  }}
  .dl-card-icon {{
    font-size: 1.6rem;
    line-height: 1;
    flex-shrink: 0;
  }}
  .dl-card-body {{
    flex: 1;
    min-width: 0;
  }}
  .dl-card-title {{
    font-weight: 700;
    font-size: 0.9rem;
    color: {T['text']};
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }}
  .dl-card-meta {{
    font-size: 0.72rem;
    color: {T['muted']};
    margin-top: 1px;
  }}

  /* ════════════════════════════════════
     PDF PREVIEW COMPATTA
     ════════════════════════════════════ */
  .pdf-preview-wrap {{
    margin-top: 1rem;
    border: 1px solid {T['border']};
    border-radius: 14px;
    overflow: hidden;
    box-shadow: {T['shadow_md']};
    background: {T['card2']};
  }}
  .pdf-preview-header {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 14px;
    background: {T['card']};
    border-bottom: 1px solid {T['border']};
    font-size: 0.78rem;
    font-weight: 600;
    color: {T['text2']};
  }}
  .pdf-preview-frame {{
    width: 100%;
    height: 480px;
    border: none;
    display: block;
    overflow: auto;
  }}

  /* ════════════════════════════════════
     SIDEBAR HINT — solo mobile
     ════════════════════════════════════ */
  .sidebar-hint-mobile {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: {T['accent_light']};
    border: 1px solid {T['accent']};
    border-radius: 20px;
    padding: 5px 14px;
    font-size: 0.75rem;
    color: {T['accent']};
    margin-bottom: 1rem;
    font-weight: 600;
    white-space: nowrap;
    max-width: fit-content;
  }}

  /* ═══ MOBILE ═══ */
  @media (max-width: 640px) {{
    .block-container {{
      padding: 4.5rem 1rem 3rem !important;
    }}
    .hero-title {{ font-size: 1.75rem !important; }}
    .hero-wrap {{ margin-bottom: 1.5rem; padding-bottom: 1.2rem; }}

    /* Nessuna colonna affiancata su mobile - layout già lineare */

    /* Input e select: altezza adeguata e testo visibile */
    .stTextInput input,
    .stNumberInput input {{
      font-size: 1rem !important;
      padding: 14px 16px !important;
      min-height: 52px !important;
      height: 52px !important;
      line-height: 1.4 !important;
      box-sizing: border-box !important;
    }}
    /* Forza altezza contenitore input */
    .stTextInput > div > div {{
      min-height: 52px !important;
    }}
    .stTextInput input::placeholder,
    .stNumberInput input::placeholder {{
      font-size: 1rem !important;
      opacity: 1 !important;
    }}
    /* Selectbox: fix altezza sia nel main che nella sidebar */
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
    /* Sidebar selectbox specifico */
    [data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] > div:first-child {{
      min-height: 48px !important;
      padding: 10px 12px !important;
    }}
    [data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] span {{
      font-size: 0.85rem !important;
      color: #f0ede6 !important;
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
    .output-card {{ padding: 1rem; }}
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

  .stSpinner > div {{
    border-top-color: {T['accent']} !important;
  }}
</style>
""", unsafe_allow_html=True)

# ── SIDEBAR ──────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-title">⚙️ Impostazioni</div>', unsafe_allow_html=True)

    st.markdown('<div class="sidebar-label">🏫 Classe</div>', unsafe_allow_html=True)
    difficolta = st.selectbox("livello", SCUOLE, index=2, label_visibility="collapsed")

    st.markdown('<div class="sidebar-label" style="margin-top:1rem;">📋 Opzioni</div>', unsafe_allow_html=True)
    bes_dsa         = st.checkbox("Supporto BES/DSA", value=True,
                    help="Circa il 25% dei sottopunti vengono contrassegnati con * e resi facoltativi per gli studenti con certificazione BES/DSA. L'intestazione della verifica indica il significato dell'asterisco.")
    doppia_fila     = st.checkbox("Genera Versione A e B (due varianti)", value=False)
    correzione_step = st.checkbox("Includi soluzioni passo per passo", value=False)

    st.markdown('<div class="sidebar-label" style="margin-top:1rem;">🔗 Interdisciplinare</div>', unsafe_allow_html=True)
    esercizio_multidisciplinare = st.checkbox("Aggiungi un esercizio collegato ad altra materia", value=False)
    if esercizio_multidisciplinare:
        materia2_scelta = st.text_input("Collega con:", placeholder="es. Fisica, Storia...", key="materia2_input").strip() or None
        difficolta_multi = st.select_slider("Difficoltà:", options=["Facile","Media","Alta"], value="Media", key="diff_multi_slider")
    else:
        materia2_scelta  = None
        difficolta_multi = None

    st.markdown('<div class="sidebar-label" style="margin-top:1rem;">🏆 Punteggi</div>', unsafe_allow_html=True)
    mostra_punteggi = st.checkbox("Mostra punteggio per esercizio", value=True)
    con_griglia     = st.checkbox("Includi griglia di valutazione", value=True)
    punti_totali    = st.number_input("Punti totali", min_value=10, max_value=200, value=100, step=5,
                                      disabled=not mostra_punteggi)

    st.markdown('<div class="sidebar-label" style="margin-top:1rem;">🤖 Modello AI</div>', unsafe_allow_html=True)
    modello_id = MODELLI_DISPONIBILI[
        st.selectbox("modello", list(MODELLI_DISPONIBILI.keys()), label_visibility="collapsed")
    ]

    st.markdown('<div class="sidebar-label" style="margin-top:1.5rem;">🎨 Aspetto</div>', unsafe_allow_html=True)
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

# ── HINT SIDEBAR MOBILE (sopra il titolo) ────────────────────────────────────────
st.markdown("""
<div class="sidebar-hint-mobile">
  ⚙️ &nbsp; Apri <strong>&gt;&gt;</strong> per le impostazioni
</div>
""", unsafe_allow_html=True)

# ── HEADER ───────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="hero-wrap">
  <div class="hero-left">
    <h1 class="hero-title">{APP_ICON} {APP_NAME}</h1>
    <p class="hero-sub">{APP_TAGLINE}</p>
  </div>
  <div class="hero-right">
    <a href="{SHARE_URL}" class="share-link" target="_blank">
      Condividi questo strumento con i colleghi →
    </a>
  </div>
</div>
""", unsafe_allow_html=True)

# ── HINT SIDEBAR MOBILE ───────────────────────────────────────────────────────────


# ── FORM PRINCIPALE ───────────────────────────────────────────────────────────────
st.markdown('<div class="expander-heading">📚 Argomento della verifica</div>', unsafe_allow_html=True)
argomento_area = st.text_area(
    "argomento",
    placeholder="es. Le equazioni di secondo grado\nes. La Rivoluzione Francese",
    height=90,
    label_visibility="collapsed",
    key="argomento_area"
)
argomento = argomento_area.strip()
st.markdown('<div style="height:1.2rem;"></div>', unsafe_allow_html=True)
st.markdown('<div class="expander-heading" style="margin-top:0.8rem;">📖 Materia</div>', unsafe_allow_html=True)
_materie_select = MATERIE + ["✏️ Altra materia..."]
_materia_sel = st.selectbox("Materia", _materie_select, index=0, label_visibility="collapsed")
if _materia_sel == "✏️ Altra materia...":
    materia_scelta = st.text_input("Scrivi materia:", placeholder="es. Economia Aziendale, Scienze Naturali...",
                                   key="_materia_custom_input", label_visibility="collapsed").strip() or "Matematica"
else:
    materia_scelta = _materia_sel or "Matematica"

with st.expander("✏️  Personalizza la verifica  *(opzionale)*"):

    st.markdown(f'<div class="expander-heading">📝 Struttura esercizi</div>', unsafe_allow_html=True)
    num_esercizi_totali = st.slider(
        "Numero di esercizi in verifica",
        min_value=1, max_value=15, value=4,
        help="Trascina per scegliere il numero di esercizi"
    )

    with st.expander("🎯 Specifica il tipo di ogni esercizio (opzionale)"):
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
                # Tipo esercizio
                t = st.selectbox("Tipo esercizio", TIPI_ESERCIZIO,
                                 index=TIPI_ESERCIZIO.index(ex['tipo']),
                                 key=f"tipo_{i}", label_visibility="visible")
                st.session_state.esercizi_custom[i]['tipo'] = t
                # Descrizione
                d = st.text_input("Descrizione dell'esercizio (opzionale)",
                                  value=ex['descrizione'],
                                  placeholder="es. Risolvi ax²+bx+c=0 mostrando i passaggi",
                                  key=f"desc_{i}", label_visibility="visible")
                st.session_state.esercizi_custom[i]['descrizione'] = d
                # Allegato + rimuovi sulla stessa riga
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
            st.session_state.esercizi_custom.append({'tipo': 'Aperto', 'descrizione': '', 'immagine': None})
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

# ── BOTTONE GENERA ────────────────────────────────────────────────────────────────
st.write("")
genera_btn = st.button("🚀  Genera Verifica", use_container_width=True, type="primary")

# ── STATUS BAR (sotto il bottone) ────────────────────────────────────────────────


# ── LOGICA GENERAZIONE ───────────────────────────────────────────────────────────
if genera_btn:
    if not argomento.strip():
        st.warning("⚠️ Inserisci l'argomento della verifica."); st.stop()
    try:
        model        = genai.GenerativeModel(modello_id)
        materia      = materia_scelta.strip() or "Matematica"
        e_mat        = any(k in materia.lower() for k in ["matem","fis","chim","inform","elettr","meccan"])
        nota_bes     = ("I sottopunti (*) sono facoltativi per studenti con certificazione."
                        if bes_dsa else "Svolgere tutti gli esercizi mostrando i passaggi.")
        calibrazione = CALIBRAZIONE_SCUOLA.get(difficolta, "")
        s_note       = f"\nNOTE DOCENTE: {note_generali.strip()}" if note_generali.strip() else ""
        s_es, imgs_es = costruisci_prompt_esercizi(
            st.session_state.esercizi_custom, num_esercizi_totali, punti_totali if mostra_punteggi else 0)
        titolo_a = "Versione A" if doppia_fila else ""

        # ── Spinner unico — nessuna progress bar ──────────────────────────────
        with st.spinner("✍️ Generazione in corso…"):

            titolo_resp = model.generate_content(
                f"Sei un docente. Crea un titolo professionale e conciso per una verifica scolastica.\n"
                f"Materia: {materia}\n"
                f"Argomento inserito dall'utente (potrebbe avere errori ortografici o essere informale): \"{argomento}\"\n"
                f"Restituisci SOLO il titolo senza virgolette, senza punteggiatura finale, "
                f"senza prefissi come 'Verifica di'. Esempio: 'Le equazioni di secondo grado'"
            )
            titolo_clean = titolo_resp.text.strip().strip('"').strip("'").strip()
            if not titolo_clean:
                titolo_clean = argomento.strip()

            bes_rule = ""
            if bes_dsa:
                bes_rule = (
                    "- BES/DSA OBBLIGATORIO: almeno il 25% dei sottopunti DEVE avere asterisco.\n"
                    "  USA ESATTAMENTE questo formato: \\item[a*)] — lettera, asterisco, parentesi chiusa.\n"
                    "  NON usare \\item[a.] NE \\item[a*] NE \\item[a.)] — SOLO \\item[a*)]\n"
                    "  Scegli i sottopunti più complessi.\n"
                    "  IMPORTANTE: conta i sottopunti totali, calcola il 25% e assicurati di mettere asterisco su quel numero minimo PRIMA di terminare.\n"
                )
            else:
                bes_rule = "- Nessun asterisco BES/DSA."

            punti_rule = (f"- Ogni \\item DEVE avere \"(X pt)\" sulla stessa riga. Totale: {punti_totali} pt."
                          if mostra_punteggi else "- NON inserire punti (X pt) in nessun esercizio né sottopunto.")

            multi_rule = ""
            if esercizio_multidisciplinare:
                materia2_str = f" con {materia2_scelta}" if materia2_scelta else " (scegli tu la disciplina più adatta)"
                diff_multi_str = f" Difficoltà: {difficolta_multi}." if difficolta_multi else ""
                multi_rule = (
                    f"- ESERCIZIO MULTIDISCIPLINARE: uno degli esercizi INCLUSI NEL TOTALE deve collegare "
                    f"{materia}{materia2_str}.{diff_multi_str}\n"
                    "  Usa SOLO strumenti già acquisiti dagli studenti."
                )
            else:
                multi_rule = "- NON includere esercizi multidisciplinari."

            griglia_rule = ("- NON generare la griglia (sarà aggiunta automaticamente)."
                            if con_griglia else "- NON generare nessuna griglia di valutazione.")

            pgfplots_pkg = "\\usepackage{pgfplots}\n\\pgfplotsset{compat=1.18}" if e_mat else ""
            titolo_header = f"Verifica di {materia}: {titolo_clean}" + (f" — {titolo_a}" if titolo_a else "")
            preambolo_fisso = f"""\\documentclass[12pt,a4paper]{{article}}
\\usepackage[utf8]{{inputenc}}
\\usepackage[italian]{{babel}}
\\usepackage{{amsmath,amsfonts,amssymb,geometry,array,multicol,enumerate,adjustbox,wasysym}}
{pgfplots_pkg}
\\geometry{{margin=1.5cm}}
\\setlength{{\\parskip}}{{3pt plus1pt minus1pt}}
\\pagestyle{{empty}}
\\begin{{document}}
\\begin{{center}}
  \\textbf{{\\large {titolo_header}}} \\\\
  \\vspace{{0.3cm}}
  \\small \\textbf{{Nome:}} \\underline{{\\hspace{{6cm}}}} \\quad \\textbf{{Classe e Data:}} \\underline{{\\hspace{{4cm}}}} \\\\
  \\vspace{{0.3cm}}
  \\textit{{\\small {nota_bes}}}
\\end{{center}}
"""

            prompt_a = f"""Sei un docente esperto di {materia} e LaTeX. Genera SOLO il corpo degli esercizi (senza preambolo, senza \\documentclass, senza \\begin{{document}}) per una verifica su: {argomento}.
{f'Punti totali: {punti_totali}.' if mostra_punteggi else ''}

CALIBRAZIONE LIVELLO:
{calibrazione}
{s_note}
{s_es}

REGOLE LATEX (TASSATIVE):
{griglia_rule}
{punti_rule}
- Titoli: \\subsection*{{Esercizio N: Titolo{' (TOT pt)' if mostra_punteggi else ''}}}
- SOTTOPUNTI OBBLIGATORI: usa SEMPRE \\item[a)] \\item[b)] \\item[c)] ecc. con label ESPLICITA tra parentesi quadre. NON usare \\begin{{enumerate}}[a)] con item senza label. Ogni \\item DEVE avere [lettera)] esplicito.
{bes_rule}
{multi_rule}
- Scelta multipla: le opzioni DEVONO stare in un \\begin{{enumerate}}[a)] SEPARATO dopo la riga della domanda.
- Vero/Falso: $\\square$ \\textbf{{V}} $\\quad\\square$ \\textbf{{F}}
- Completamento: \\underline{{\\hspace{{3cm}}}}
{'- Grafici pgfplots: solo se già forniti. Per disegnare usa \\vspace{4cm}.' if e_mat else ''}

FORMATO OUTPUT: restituisci SOLO i blocchi \\subsection*{{...}} con relativi esercizi.
TERMINA con \\end{{document}}.
NIENTE preambolo, NIENTE \\documentclass, NIENTE \\begin{{document}}.
SOLO CODICE LATEX del corpo."""

            inp = [prompt_a]
            if file_ispirazione:
                inp.append({"mime_type": file_ispirazione.type, "data": file_ispirazione.getvalue()})
                inp[0] += "\nPrendi spunto dal file allegato per stile e livello."
            for im in imgs_es:
                inp.append({"mime_type": im['mime_type'], "data": im['data']})
                inp[0] += f"\nUsa l'immagine come riferimento per l'Esercizio {im['idx']}."

            ra = model.generate_content(inp)
            corpo_latex = ra.text.replace("```latex","").replace("```","").strip()
            corpo_latex = re.sub(r'^.*?\\begin\{document\}[^\n]*\n?', '', corpo_latex, flags=re.DOTALL)
            corpo_latex = re.sub(r'^\\begin\{center\}.*?\\end\{center\}\s*', '', corpo_latex, flags=re.DOTALL)
            if "\\end{document}" not in corpo_latex:
                corpo_latex += "\n\\end{document}"
            latex_a = preambolo_fisso + corpo_latex
            latex_a = fix_items_environment(latex_a)
            if bes_dsa:
                latex_a = inietta_asterischi_bes(latex_a, percentuale=0.25)
            latex_a_final = inietta_griglia(latex_a, punti_totali) if con_griglia else latex_a
            st.session_state.verifiche['A'] = {**_vf(), 'latex': latex_a_final}

            pdf_auto, err_auto = compila_pdf(latex_a_final)
            if pdf_auto:
                st.session_state.verifiche['A']['pdf'] = pdf_auto
                st.session_state.verifiche['A']['pdf_ts'] = time.time()
                st.session_state.verifiche['A']['preview'] = True

            if correzione_step:
                ps = (f"Risolvi questa verifica come docente correttore. Stesso preambolo.\n"
                      f"Titolo: 'Soluzioni — {titolo_clean}'. Niente griglia.\n"
                      f"1. \\subsection*{{Soluzioni Rapide}}: solo risultati finali.\n"
                      f"2. \\subsection*{{Svolgimento Dettagliato}}: passaggi completi.\n"
                      f"SOLO CODICE LATEX.\n\n{latex_a}")
                rs = model.generate_content(ps)
                st.session_state.verifiche['A']['soluzioni_latex'] = (
                    rs.text.replace("```latex","").replace("```","").strip())

            if doppia_fila:
                rb = model.generate_content(
                    f"Versione B: stessa struttura, cambia dati e quesiti. "
                    f"SOLO corpo esercizi (\\subsection* ecc.), SENZA preambolo/\\documentclass/\\begin{{document}}. "
                    f"Sostituisci 'Versione A' con 'Versione B'. TERMINA con \\end{{document}}. SOLO LATEX.\n\n{corpo_latex}")
                corpo_latex_b = rb.text.replace("```latex","").replace("```","").strip()
                corpo_latex_b = re.sub(r'^.*?\\begin\{document\}[^\n]*\n?', '', corpo_latex_b, flags=re.DOTALL)
                corpo_latex_b = re.sub(r'^\\begin\{center\}.*?\\end\{center\}\s*', '', corpo_latex_b, flags=re.DOTALL)
                if "\\end{document}" not in corpo_latex_b:
                    corpo_latex_b += "\n\\end{document}"
                preambolo_b = preambolo_fisso.replace(
                    titolo_header,
                    titolo_header.replace("Versione A","Versione B") if "Versione A" in titolo_header
                    else titolo_header + " — Versione B"
                )
                latex_b = preambolo_b + corpo_latex_b
                latex_b = fix_items_environment(latex_b)
                if bes_dsa:
                    latex_b = inietta_asterischi_bes(latex_b, percentuale=0.25)
                latex_b_final = inietta_griglia(latex_b, punti_totali) if con_griglia else latex_b
                st.session_state.verifiche['B'] = {**_vf(), 'latex': latex_b_final}

                pdf_b_auto, _ = compila_pdf(latex_b_final)
                if pdf_b_auto:
                    st.session_state.verifiche['B']['pdf'] = pdf_b_auto
                    st.session_state.verifiche['B']['pdf_ts'] = time.time()
                    st.session_state.verifiche['B']['preview'] = True
                if correzione_step:
                    rsb = model.generate_content(
                        "Stessa struttura soluzioni (Rapide + Dettagliato). SOLO LATEX.\n\n" + latex_b)
                    st.session_state.verifiche['B']['soluzioni_latex'] = (
                        rsb.text.replace("```latex","").replace("```","").strip())

        # Salva status bar info
        st.session_state.last_materia   = materia
        st.session_state.last_argomento = titolo_clean
        st.session_state.last_gen_ts    = time.time()

        st.rerun()

    except Exception as e:
        st.error(f"❌ Errore: {e}")

# ── OUTPUT ────────────────────────────────────────────────────────────────────────
if st.session_state.verifiche['A']['latex']:
    st.divider()
    _df  = doppia_fila   if 'doppia_fila'  in dir() else False
    _arg = st.session_state.last_argomento or (argomento if 'argomento' in dir() else 'verifica')
    _mid = modello_id    if 'modello_id'   in dir() else "gemini-2.5-flash"

    attive = ['A','B'] if _df and st.session_state.verifiche['B']['latex'] else ['A']
    cols   = st.columns(len(attive))

    for idx, fid in enumerate(attive):
        v = st.session_state.verifiche[fid]
        with cols[idx]:
            label_ver = f"Versione {fid}" if _df else "La tua verifica"
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:1rem;">
              <span style="font-family:'DM Sans',sans-serif;font-size:1.1rem;
                           font-weight:700;color:{T['text']};">{APP_ICON} {label_ver}</span>
              <span class="chip">Pronta</span>
            </div>
            """, unsafe_allow_html=True)

            # ── Download cards ────────────────────────────────────────────────
            # PDF card
            if v['pdf']:
                pdf_size = _stima_dimensione(v['pdf'])
                st.markdown(f"""
                <div class="dl-card">
                  <div class="dl-card-icon">📄</div>
                  <div class="dl-card-body">
                    <div class="dl-card-title">PDF — Alta qualità</div>
                    <div class="dl-card-meta">{pdf_size}</div>
                  </div>
                </div>
                """, unsafe_allow_html=True)
                st.download_button(
                    "⬇️ Scarica PDF",
                    v['pdf'],
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

            # Word card
            if v['docx']:
                docx_size = _stima_dimensione(v['docx'])
                st.markdown(f"""
                <div class="dl-card">
                  <div class="dl-card-icon">📝</div>
                  <div class="dl-card-body">
                    <div class="dl-card-title">File Modificabile Word</div>
                    <div class="dl-card-meta">{docx_size}</div>
                  </div>
                </div>
                """, unsafe_allow_html=True)
                st.download_button(
                    "⬇️ Scarica Word",
                    v['docx'],
                    file_name=f"Verifica_{_arg}_{fid}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                    key=f"dld_{fid}"
                )
            else:
                _docx_gen_key = f"_docx_generating_{fid}"
                if st.button("📝 File Modificabile Word", key=f"dldc_{fid}", use_container_width=True):
                    st.session_state[_docx_gen_key] = True
                if st.session_state.get(_docx_gen_key, False):
                    with st.spinner("⏳ Conversione Word…"):
                        _m = genai.GenerativeModel(_mid)
                        db, de = latex_to_docx_via_ai(v['latex'], _m, con_griglia=con_griglia)
                    if db:
                        st.session_state.verifiche[fid]['docx'] = db
                        st.session_state.verifiche[fid]['docx_ts'] = time.time()
                        st.session_state[_docx_gen_key] = False
                        st.rerun()
                    else:
                        st.session_state[_docx_gen_key] = False
                        st.error("Errore Word")
                        with st.expander("Log"): st.text(de)

            # Soluzioni
            if v['soluzioni_latex']:
                st.write("")
                if v['soluzioni_pdf']:
                    sol_size = _stima_dimensione(v['soluzioni_pdf'])
                    st.markdown(f"""
                    <div class="dl-card">
                      <div class="dl-card-icon">✅</div>
                      <div class="dl-card-body">
                        <div class="dl-card-title">Soluzioni Step-by-Step</div>
                        <div class="dl-card-meta">{sol_size}</div>
                      </div>
                    </div>
                    """, unsafe_allow_html=True)
                    st.download_button(
                        "⬇️ Scarica Soluzioni",
                        v['soluzioni_pdf'],
                        file_name=f"Soluzioni_{_arg}_{fid}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                        key=f"dls_{fid}"
                    )
                else:
                    if st.button("✅ Compila Soluzioni", key=f"cs_{fid}", use_container_width=True):
                        with st.spinner("Compilazione…"):
                            sp, se = compila_pdf(v['soluzioni_latex'])
                        if sp:
                            st.session_state.verifiche[fid]['soluzioni_pdf'] = sp
                            st.rerun()
                        else:
                            with st.expander("Log"): st.text(se)

            # ── Anteprima PDF a tenda ────────────────────────────────────────
            if v['preview'] and v['pdf']:
                with st.expander("👁 Anteprima PDF", expanded=True):
                    b64 = base64.b64encode(v['pdf']).decode()
                    st.markdown(f"""
                    <iframe
                      src="data:application/pdf;base64,{b64}#toolbar=0&navpanes=0&scrollbar=1"
                      style="width:100%;height:500px;border:none;border-radius:8px;display:block;"
                    ></iframe>
                    """, unsafe_allow_html=True)

            # ── Download LaTeX sorgente ──────────────────────────────────
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
