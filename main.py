import streamlit as st
import os
import subprocess
import tempfile
import base64
import re
import io
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

T = {
    "bg": "#0e1117", "card": "#1e2130", "border": "#2e3250",
    "text": "#e8eaf0", "muted": "#8b90a8", "accent": "#4f8ef7",
    "accent2": "#7c5cbf", "success": "#2d9e6b", "warn": "#d4860a",
    "label_color": "#c5c9e0",
}

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

# ── GRIGLIA ─────────────────────────────────────────────────────────────────────
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
        for line in block.split('\n'):
            m = re.search(r'\\item(?:\[([^\]]+)\])?\s*.*?\((\d+(?:[.,]\d+)?)\s*pt\)', line)
            if m:
                raw_label = m.group(1) or ''
                punti = m.group(2)
                clean_label = raw_label.replace('*', '').strip() if raw_label else str(len(items_found) + 1)
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
    """
    Garantisce che almeno `percentuale` dei sottopunti \\item abbiano asterisco.
    Trasforma i sottopunti più in fondo (generalmente i più difficili) aggiungendo *.
    """
    # Trova tutti gli \item con label tipo [a)] [b)] ecc.
    pattern = r'(\\item\[([a-zA-Z]+)(\*?)\)\])'
    tutti = list(re.finditer(pattern, latex))
    if not tutti:
        return latex

    n_totale = len(tutti)
    n_con_asterisco = sum(1 for m in tutti if m.group(3) == '*')
    n_necessari = max(1, int(n_totale * percentuale + 0.999))  # arrotonda su

    if n_con_asterisco >= n_necessari:
        return latex  # già ok

    n_da_aggiungere = n_necessari - n_con_asterisco
    # Aggiungi asterisco agli item senza asterisco, preferendo gli ultimi di ogni esercizio
    candidati = [m for m in tutti if m.group(3) != '*']
    # Prendi gli ultimi N candidati (più difficili = ultimi sottopunti)
    da_modificare = candidati[-n_da_aggiungere:]

    # Sostituisci da destra per non invalidare gli offset
    for m in reversed(da_modificare):
        lettera = m.group(2)
        replacement = f'\\item[{lettera}*)]'
        latex = latex[:m.start()] + replacement + latex[m.end():]

    return latex


def fix_items_environment(latex):
    """Wrappa item nudi (fuori da enumerate/itemize) in begin{enumerate}[a)].
    Traccia SOLO enumerate/itemize, non document/center/tabular."""
    import re as _r
    lines = latex.split('\n')
    result = []
    # Conta solo ambienti list-like (enumerate, itemize)
    list_depth = 0
    in_bare_block = False
    for line in lines:
        stripped = line.strip()
        list_opens  = len(_r.findall(r'\\begin\{(?:enumerate|itemize)', line))
        list_closes = len(_r.findall(r'\\end\{(?:enumerate|itemize)', line))
        # Un item è "nudo" se non siamo dentro enumerate/itemize
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
    # 1. Rimuoviamo eventuali griglie vecchie per evitare duplicati
    latex = re.sub(
        r'(\\vspace\{[^}]+\}\s*)?\\begin\{center\}\s*\\textbf\{Griglia[^}]*\}.*?\\end\{center\}',
        '', latex, flags=re.DOTALL
    )
    # 2. Generiamo la nuova griglia
    griglia = build_griglia_latex(parse_esercizi(latex), punti_totali)
    # 3. Inserimento: prima di \end{document}, o in fondo
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
    return None, "pdf2image non installato e pdftoppm non trovato. Esegui: pip install pdf2image"

def _make_tc_xml(text, width_dxa, bold=False, gridSpan=1):
    """Crea <w:tc> XML con merge fisico corretto (gridSpan + cella singola)."""
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
    """Sovrascrive il tblGrid con le larghezze reali delle colonne (evita valori negativi)."""
    old_grid = tbl_el.find(_qn('w:tblGrid'))
    if old_grid is not None:
        tbl_el.remove(old_grid)
    new_grid = _OE('w:tblGrid')
    for w in col_widths:
        gc = _OE('w:gridCol')
        gc.set(_qn('w:w'), str(max(1, w)))
        new_grid.append(gc)
    # Il tblGrid deve stare subito dopo tblPr
    tbl_pr = tbl_el.find(_qn('w:tblPr'))
    if tbl_pr is not None:
        tbl_pr.addnext(new_grid)
    else:
        tbl_el.insert(0, new_grid)


def _build_griglia_xml(doc, row_es, row_sotto, row_max, PAGE_W_DXA=9638):
    """Tabella griglia con riga Es. costruita da XML puro → merge fisicamente corretto."""
    from docx.oxml.ns import qn as _qn
    from docx.oxml import OxmlElement as _OE
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Pt

    n_cols = len(row_es)
    row_punti = ["Punti"] + [""] * (n_cols - 1)

    # Calcola larghezze colonne
    first_col = 1400
    last_col = 900
    n_mid = max(1, n_cols - 2)
    available = PAGE_W_DXA - first_col - last_col
    mid_col = max(400, available // n_mid)
    col_widths = [first_col] + [mid_col] * n_mid + [last_col]
    # Aggiusta per far quadrare esattamente il totale
    diff = PAGE_W_DXA - sum(col_widths)
    col_widths[-1] += diff  # aggiusta sull'ultima colonna (Tot)

    def _setup_tbl(tbl, total_w, widths):
        """Imposta tblPr (larghezza, layout fisso, margini celle=0) e sovrascrive tblGrid."""
        tbl_el = tbl._tbl
        tbl_pr = tbl_el.find(_qn('w:tblPr'))
        if tbl_pr is None:
            tbl_pr = _OE('w:tblPr'); tbl_el.insert(0, tbl_pr)
        # tblW
        tbl_w = _OE('w:tblW')
        tbl_w.set(_qn('w:w'), str(total_w)); tbl_w.set(_qn('w:type'), 'dxa')
        ex = tbl_pr.find(_qn('w:tblW'))
        if ex is not None: tbl_pr.remove(ex)
        tbl_pr.append(tbl_w)
        # tblLayout fixed
        tbl_lay = _OE('w:tblLayout'); tbl_lay.set(_qn('w:type'), 'fixed')
        ex2 = tbl_pr.find(_qn('w:tblLayout'))
        if ex2 is not None: tbl_pr.remove(ex2)
        tbl_pr.append(tbl_lay)
        # tblCellMar = 50 DXA (margine minimo per leggibilità)
        tbl_cm = _OE('w:tblCellMar')
        for side in ('top', 'left', 'bottom', 'right'):
            cm_el = _OE(f'w:{side}')
            cm_el.set(_qn('w:w'), '50'); cm_el.set(_qn('w:type'), 'dxa')
            tbl_cm.append(cm_el)
        ex3 = tbl_pr.find(_qn('w:tblCellMar'))
        if ex3 is not None: tbl_pr.remove(ex3)
        tbl_pr.append(tbl_cm)
        # Sovrascrive tblGrid con larghezze reali
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

    # Righe 1-3: Sotto., Max, Punti
    for r_idx, riga in enumerate([row_sotto, row_max, row_punti], start=1):
        for c_idx in range(n_cols):
            val = riga[c_idx] if c_idx < len(riga) else ''
            _fill_cell(tbl.cell(r_idx, c_idx), val,
                       bold=(c_idx == 0),
                       w=col_widths[c_idx] if c_idx < len(col_widths) else mid_col)

    # Riga 0 (Es.): raggruppa per esercizio con run-length encoding
    # row_es formato: ["Es.", "1","1","1","2","2","Tot"]
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

    # Sostituisci riga 0 con celle XML con merge fisico corretto
    tr_el = tbl.rows[0]._tr
    for tc_el in list(tr_el.findall(_qn('w:tc'))):
        tr_el.remove(tc_el)
    for label, span, width in groups:
        tr_el.append(_make_tc_xml(label, width, bold=True, gridSpan=span))

    return tbl


def _strip_latex_math(text):
    """Converte formule LaTeX in testo leggibile (rimuove $...$ e comandi)."""
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

def _parse_latex_to_data(codice_latex):
    """Parsa direttamente il LaTeX in struttura dati senza usare l'AI."""
    import re as _r

    data = {'titolo': '', 'intestazione_nota': '', 'esercizi': []}

    # Titolo
    m = _r.search(r'\\textbf\{\\large ([^}]+)\}', codice_latex)
    if m:
        data['titolo'] = _strip_latex_math(m.group(1).strip())

    # Nota BES/DSA
    m2 = _r.search(r'\\textit\{\\small ([^}]+)\}', codice_latex)
    if m2:
        data['intestazione_nota'] = m2.group(1).strip()

    # Dividi per esercizi (\subsection*)
    blocks = _r.split(r'\\subsection\*\{', codice_latex)
    for block in blocks[1:]:
        header_end = block.find('}')
        if header_end == -1:
            continue
        titolo_ex = _strip_latex_math(block[:header_end].strip())
        body = block[header_end+1:]

        # Testo introduttivo prima del primo enumerate/item
        markers = ['\\item[', '\\begin{enumerate}', '\\begin{itemize}']
        positions = [body.find(x) for x in markers if body.find(x) != -1]
        intro_end = min(positions) if positions else len(body)
        testo_intro = _strip_latex_math(body[:intro_end].strip())

        sottopunti = []

        # Strategia: trova tutti i blocchi \begin{enumerate}[a)] ... \end{enumerate}
        # con eventuali opzioni \hspace dopo
        enum_pattern = _r.compile(
            r'\\begin\{enumerate\}\[a\)\]\s*'
            r'(.*?)'
            r'\\end\{enumerate\}'
            r'((?:\s*\\hspace\{[^}]+\}\s*[A-Da-d]\)[^\n\\]*(?:\\\\)?\n?)*)',
            _r.DOTALL
        )

        for em in enum_pattern.finditer(body):
            items_block = em.group(1)
            hspace_block = em.group(2).strip()

            # Estrai tutti gli \item[label)] dal blocco
            item_matches = list(_r.finditer(
                r'\\item\[([^\]]+)\]\s*(.*?)(?=\\item\[|$)',
                items_block, _r.DOTALL
            ))

            for i, im in enumerate(item_matches):
                label = im.group(1).strip()
                raw_text = im.group(2).strip()
                opzioni = []

                # Se questo è l'unico item nel blocco, le opzioni potrebbero essere
                # nel blocco hspace che segue \end{enumerate}
                if len(item_matches) == 1 and hspace_block:
                    hspace_opts = _r.findall(
                        r'\\hspace\{[^}]+\}\s*[A-Da-d]\)\s*([^\n\\]+)',
                        hspace_block
                    )
                    opzioni = [_strip_latex_math(o.strip()) for o in hspace_opts if o.strip()]

                # Cerca opzioni anche dentro raw_text (formato \begin{enumerate}[a)] annidato)
                if not opzioni:
                    inner = _r.search(
                        r'\\begin\{enumerate\}\[a\)\](.*?)\\end\{enumerate\}',
                        raw_text, _r.DOTALL
                    )
                    if inner:
                        for opt in _r.findall(r'\\item\s*(.*?)(?=\\item|$)', inner.group(1), _r.DOTALL):
                            opt_c = _strip_latex_math(opt.strip())
                            if opt_c: opzioni.append(opt_c)
                        raw_text = raw_text[:inner.start()].strip()

                testo_clean = _strip_latex_math(raw_text)
                testo_clean = _r.sub(r'\\vspace\{[^}]+\}', '', testo_clean).strip()

                if label:
                    sottopunti.append({
                        'label': label,
                        'testo': testo_clean if testo_clean else '—',
                        'opzioni': opzioni
                    })

        if titolo_ex or sottopunti:
            data['esercizi'].append({
                'titolo': titolo_ex,
                'testo_intro': testo_intro,
                'sottopunti': sottopunti
            })

    return data

def latex_to_docx_via_ai(codice_latex, model, con_griglia=True):
    """Converte LaTeX → DOCX tramite parsing diretto (no AI, no JSON)."""
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

        # Titolo
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        rt = p.add_run(data.get('titolo', 'Verifica'))
        rt.bold = True; rt.font.size = Pt(14)

        # ── Intestazione: 2 celle invisibili ──
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
            [("Nome e Cognome: ", "______________")],
            [("Classe: ", "______"), ("   Data: ", "______")],
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

        # Nota BES
        nota = data.get('intestazione_nota', '')
        if nota:
            p3 = doc.add_paragraph(); p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r3 = p3.add_run(nota); r3.italic = True; r3.font.size = Pt(10)
        doc.add_paragraph()

        # ── Esercizi ─────────────────────────────────────────────────────────────
        for ex in data.get('esercizi', []):
            pe = doc.add_paragraph()
            rt = pe.add_run(ex.get('titolo', '')); rt.bold = True; rt.font.size = Pt(12)
            intro = ex.get('testo_intro', '').strip()
            if intro:
                pi = doc.add_paragraph(intro); pi.paragraph_format.space_after = Pt(4)
            for sp in ex.get('sottopunti', []):
                label = sp.get('label', '').strip()
                testo = sp.get('testo', '').strip()
                opzioni = sp.get('opzioni', [])
                ps = doc.add_paragraph()
                ps.paragraph_format.left_indent = Cm(0.5)
                ps.paragraph_format.space_after = Pt(2)
                rl = ps.add_run(label + "  "); rl.bold = True
                ps.add_run(testo if testo and testo != '—' else '')
                if opzioni:
                    for opt in opzioni:
                        po = doc.add_paragraph()
                        po.paragraph_format.left_indent = Cm(1.5)
                        po.paragraph_format.space_after = Pt(1)
                        po.add_run(str(opt))
                    doc.add_paragraph("").paragraph_format.space_after = Pt(4)
                else:
                    doc.add_paragraph("").paragraph_format.space_after = Pt(14)
            doc.add_paragraph()

        # ── Griglia ──────────────────────────────────────────────────────────────
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
                tot_pts = sum(float(x.replace(',','.')) for x in row_max[1:] if x.replace(',','.').replace('.','').isdigit() or (x.replace(',','.').replace('.','').replace('-','').isdigit()))
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

# ── SESSION STATE ────────────────────────────────────────────────────────────────
st.set_page_config(page_title=APP_NAME, page_icon=APP_ICON, layout="wide")

def _vf():
    return {'latex': '', 'pdf': None, 'preview': False,
            'soluzioni_latex': '', 'soluzioni_pdf': None, 'docx': None}

if 'verifiche'       not in st.session_state: st.session_state.verifiche = {'A': _vf(), 'B': _vf()}
if 'esercizi_custom' not in st.session_state: st.session_state.esercizi_custom = []

# ── SIDEBAR ──────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
    <div style="font-size:1.15rem;font-weight:800;color:{T['text']};
                letter-spacing:-0.3px;margin-bottom:1.2rem;">
        ⚙️ Impostazioni
    </div>
    """, unsafe_allow_html=True)

    # ── Sezione: Classe ──
    st.markdown(f'<div class="sb-section-label">🏫 Classe</div>', unsafe_allow_html=True)
    difficolta = st.selectbox("livello", SCUOLE, index=2, label_visibility="collapsed")

    # ── Sezione: Opzioni verifica ──
    st.markdown(f'<div class="sb-section-label" style="margin-top:1.1rem;">📋 Opzioni verifica</div>', unsafe_allow_html=True)
    bes_dsa      = st.checkbox("Supporto BES/DSA", value=True,
                               help="Contrassegna con (*) i sottopunti facoltativi per studenti certificati.")
    doppia_fila  = st.checkbox("Genera Versione A e B", value=False,
                               help="Genera una seconda versione fac-simile con dati diversi.")
    correzione_step = st.checkbox("Correzione Step-by-Step", value=False,
                                  help="PDF separato: soluzioni rapide + svolgimento completo.")

    # ── Sezione: Esercizio Multidisciplinare ──
    st.markdown(f'<div class="sb-section-label" style="margin-top:1.1rem;">🔗 Interdisciplinare</div>', unsafe_allow_html=True)
    esercizio_multidisciplinare = st.checkbox(
        "Includi 1 esercizio interdisciplinare",
        value=False,
        help="Incluso nel totale esercizi, non aggiunto in più. Usa solo strumenti già noti agli studenti."
    )
    if esercizio_multidisciplinare:
        materia2_scelta = st.text_input(
            "Collega con (materia/disciplina):",
            placeholder="es. Fisica, Storia, Arte, Economia...",
            key="materia2_input"
        )
        materia2_scelta = materia2_scelta.strip() or None
        difficolta_multi = st.select_slider(
            "Difficoltà esercizio:",
            options=["Facile", "Media", "Alta"],
            value="Media",
            key="diff_multi_slider"
        )
    else:
        materia2_scelta  = None
        difficolta_multi = None

    # ── Sezione: Punteggi ──
    st.markdown(f'<div class="sb-section-label" style="margin-top:1.1rem;">🏆 Punteggi e Griglia</div>', unsafe_allow_html=True)
    mostra_punteggi = st.checkbox("Mostra punteggi per esercizio", value=True,
                                  help="Se disattivato, la verifica non mostrerà i punti per ogni sottopunto.")
    con_griglia     = st.checkbox("Includi griglia di valutazione", value=True,
                                  help="Se disattivato, la verifica non avrà la griglia finale.")
    punti_totali = st.number_input("Punti totali", min_value=10, max_value=200, value=100, step=5,
                                   disabled=not mostra_punteggi,
                                   help="Punti totali da distribuire tra gli esercizi.")

    # ── Sezione: Modello AI ──
    st.markdown(f'<div class="sb-section-label" style="margin-top:1.1rem;">🤖 Modello AI</div>', unsafe_allow_html=True)
    modello_id = MODELLI_DISPONIBILI[
        st.selectbox("modello", list(MODELLI_DISPONIBILI.keys()), label_visibility="collapsed")
    ]

# ── CSS DINAMICO ─────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
  /* Reset e base */
  .stApp {{ background-color: {T['bg']} !important; }}
  .block-container {{
    padding-top: 3rem !important;
    padding-left: 3rem !important;
    padding-right: 3rem !important;
    max-width: 1200px !important;
  }}

  /* Nascondi anchor links sui titoli markdown */
  .stMarkdown h1 a, .stMarkdown h2 a, .stMarkdown h3 a,
  .stMarkdown h4 a, .stMarkdown h5 a, .stMarkdown h6 a {{
    display: none !important;
  }}

  /* Label dei widget — più grandi e più visibili */
  .stTextInput label p,
  .stSelectbox label p {{
    font-size: 1.05rem !important;
    font-weight: 600 !important;
    color: {T['label_color']} !important;
  }}

  /* Rimpicciolisci il drag&drop uploader */
  [data-testid="stFileUploader"] section {{
    padding: 0.6rem 1rem !important;
    min-height: unset !important;
  }}
  [data-testid="stFileUploader"] section > div {{
    gap: 0.3rem !important;
  }}
  [data-testid="stFileUploadDropzone"] {{
    padding: 0.5rem 0.8rem !important;
  }}
  [data-testid="stFileUploadDropzone"] p {{
    font-size: 0.82rem !important;
    margin: 0 !important;
  }}
  [data-testid="stFileUploadDropzone"] small {{
    font-size: 0.72rem !important;
  }}

  /* Header app */
  .app-header {{
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 2px;
    padding-top: 0;
  }}
  .app-title {{
    font-size: 2rem;
    font-weight: 800;
    color: {T['text']};
    line-height: 1.2;
    letter-spacing: -0.5px;
    margin: 0;
  }}
  .app-share {{
    display: inline-flex;
    align-items: center;
    gap: 4px;
    border: 1px solid {T['border']};
    border-radius: 20px;
    padding: 3px 11px;
    font-size: 0.75rem;
    color: {T['muted']};
    background: {T['card']};
    text-decoration: none;
    white-space: nowrap;
    transition: border-color 0.2s;
  }}
  .app-share:hover {{ border-color: {T['accent']}; color: {T['accent']}; }}
  .app-tagline {{
    color: {T['muted']};
    font-size: 0.85rem;
    margin: 2px 0 1.4rem 0;
  }}

  /* Sezione heading dentro expander */
  .section-heading {{
    font-size: 1rem;
    font-weight: 700;
    color: {T['text']};
    margin: 0.6rem 0 0.3rem 0;
    display: flex;
    align-items: center;
    gap: 6px;
  }}

  /* Caption/hint personalizzato */
  .hint-text {{
    font-size: 0.8rem;
    color: {T['muted']};
    margin-top: 3px;
    margin-bottom: 6px;
  }}

  /* ── SIDEBAR SECTION LABELS ── */
  .sb-section-label {{
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: {T['muted']};
    margin-bottom: 0.35rem;
    padding-bottom: 0.25rem;
    border-bottom: 1px solid {T['border']};
  }}
</style>
""", unsafe_allow_html=True)

# ── HEADER ───────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="app-header">
  <span class="app-title">{APP_ICON} {APP_NAME}</span>
  <a href="{SHARE_URL}" class="app-share" target="_blank">🔗 Condividi</a>
</div>
<p class="app-tagline">{APP_TAGLINE}</p>
""", unsafe_allow_html=True)

# ── FORM: argomento + materia (sempre visibili) ───────────────────────────────────
c1, c2 = st.columns([3, 1])
with c1:
    argomento = st.text_input("📚 Argomento della verifica",
                              placeholder="es. Le equazioni di secondo grado")
with c2:
    _materie_select = MATERIE + ["✏️ Altra materia..."]
    _materia_idx = st.session_state.get('_materia_sel_idx', 0)
    _materia_sel = st.selectbox(
        "📖 Materia",
        _materie_select,
        index=_materia_idx,
        help="Seleziona la materia o scegli 'Altra materia...' per scriverla.",
        key="_materia_selectbox"
    )
    if _materia_sel == "✏️ Altra materia...":
        materia_scelta = st.text_input(
            "Scrivi la materia:",
            placeholder="es. Economia Aziendale...",
            key="_materia_custom_input",
            label_visibility="collapsed"
        ).strip() or "Matematica"
    else:
        materia_scelta = _materia_sel if _materia_sel else "Matematica"

# ── TENDINA PERSONALIZZAZIONE ─────────────────────────────────────────────────────
if "personalizza_open" not in st.session_state:
    st.session_state.personalizza_open = False
with st.expander("✏️  Personalizza la verifica  *(opzionale)*",
                 expanded=st.session_state.personalizza_open):

    # Istruzioni AI
    st.markdown('<div class="section-heading">🎯 Istruzioni specifiche per l\'AI</div>',
                unsafe_allow_html=True)
    note_generali = st.text_area(
        "note", label_visibility="collapsed",
        placeholder=NOTE_PLACEHOLDER.get(materia_scelta,
            "es. Argomenti da privilegiare, tipo di esercizi, livello di difficoltà..."),
        height=95
    )

    # File riferimento
    st.markdown('<div class="section-heading">📂 File di riferimento</div>',
                unsafe_allow_html=True)
    col_up, _ = st.columns([2, 1])
    with col_up:
        file_ispirazione = st.file_uploader(
            "file", type=['pdf', 'png', 'jpg', 'jpeg'], label_visibility="collapsed"
        )
    st.markdown(
        '<div class="hint-text">💡 PDF o immagine del libro/verifica precedente. '
        "L'AI prenderà spunto senza copiarlo.</div>",
        unsafe_allow_html=True
    )

    # Struttura esercizi (senza divisore)
    st.markdown('<div class="section-heading">📝 Struttura degli esercizi</div>',
                unsafe_allow_html=True)
    col_n1, _ = st.columns([1, 2])
    with col_n1:
        num_esercizi_totali = st.number_input(
            "Numero totale esercizi", min_value=1, max_value=15, value=4,
            help="Esercizi totali (inclusi quelli specifici sotto)"
        )
    # ── Sub-expander esercizi specifici ─────────────────────────────────────────
    with st.expander("🎯  Definisci esercizi specifici", expanded=False):
        n_custom = len(st.session_state.esercizi_custom)
        n_liberi = max(0, num_esercizi_totali - n_custom)

        # Messaggio stato DENTRO questo sub-expander
        if n_custom == 0:
            st.info(f"💡 Tutti i {num_esercizi_totali} esercizi saranno generati dall'AI. "
                    "Aggiungi esercizi specifici qui sotto se vuoi controllarne alcuni.")
        elif n_custom >= num_esercizi_totali:
            st.warning(f"⚠️ {n_custom}/{num_esercizi_totali} specifici — totale raggiunto. "
                       "Aumenta il numero sopra.")
        else:
            st.success(f"✅ {n_custom} specifici + {n_liberi} liberi all'AI = {num_esercizi_totali} totali")

        if st.session_state.esercizi_custom:
            # Header colonne
            hc1, hc2, hc3, hc4 = st.columns([1, 3, 2, 0.4])
            hc1.caption("Tipo"); hc2.caption("Descrizione"); hc3.caption("Immagine rif."); hc4.caption("")
            to_remove = None
            for i, ex in enumerate(st.session_state.esercizi_custom):
                # Header numerato per ogni esercizio
                st.markdown(
                    f'<div style="font-size:0.82rem;font-weight:700;color:{T["accent"]};'
                    f'margin-top:0.7rem;margin-bottom:0.2rem;letter-spacing:0.03em;">'
                    f'ESERCIZIO {i+1}</div>',
                    unsafe_allow_html=True
                )
                ca, cb, cc, cd = st.columns([1, 3, 2, 0.4])
                with ca:
                    t = st.selectbox("t", TIPI_ESERCIZIO,
                                     index=TIPI_ESERCIZIO.index(ex['tipo']),
                                     key=f"tipo_{i}", label_visibility="collapsed")
                    st.session_state.esercizi_custom[i]['tipo'] = t
                with cb:
                    d = st.text_input("d", value=ex['descrizione'],
                                      placeholder="es. Risolvi l'equazione...",
                                      key=f"desc_{i}", label_visibility="collapsed")
                    st.session_state.esercizi_custom[i]['descrizione'] = d
                with cc:
                    img = st.file_uploader("i", type=['png','jpg','jpeg'],
                                           key=f"img_{i}", label_visibility="collapsed")
                    if img: st.session_state.esercizi_custom[i]['immagine'] = img
                    if st.session_state.esercizi_custom[i].get('immagine'):
                        st.image(st.session_state.esercizi_custom[i]['immagine'], width=75)
                with cd:
                    st.write("")  # allineamento verticale
                    if st.button("✕", key=f"rm_{i}"): to_remove = i
            if to_remove is not None:
                st.session_state.esercizi_custom.pop(to_remove); st.rerun()

        can_add = len(st.session_state.esercizi_custom) < num_esercizi_totali
        if st.button("＋ Aggiungi esercizio specifico", disabled=not can_add,
                     help="Aggiungi un esercizio di cui vuoi definire tipo e contenuto" if can_add
                     else "Totale raggiunto — aumenta il numero sopra"):
            st.session_state.esercizi_custom.append(
                {'tipo': 'Aperto', 'descrizione': '', 'immagine': None})
            st.rerun()

# ── GENERA ───────────────────────────────────────────────────────────────────────
st.write("")
_, cg, _ = st.columns([1, 1, 1])
with cg:
    genera_btn = st.button("🚀  GENERA VERIFICA", use_container_width=True, type="primary")


# ── LOGICA GENERAZIONE ────────────────────────────────────────────────────────────
if genera_btn:
    st.session_state.personalizza_open = False  # chiudi expander alla generazione
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

        # ── Progress bar unificata ───────────────────────────────────────────────
        _n_steps = 3 + (1 if correzione_step else 0) + (2 if doppia_fila else 0)
        _step = [0]
        _pbar = st.progress(0, text="✍️ Elaborazione titolo...")

        def _avanza(testo):
            _step[0] += 1
            _pbar.progress(min(_step[0] / _n_steps, 1.0), text=testo)

        # ── Genera titolo corretto con AI ────────────────────────────────────────
        titolo_resp = model.generate_content(
            f"Sei un docente. Crea un titolo professionale e conciso per una verifica scolastica.\n"
            f"Materia: {materia}\n"
            f"Argomento inserito dall'utente (potrebbe avere errori ortografici o essere informale): \"{argomento}\"\n"
            f"Restituisci SOLO il titolo senza virgolette, senza punteggiatura finale, "
            f"senza prefissi come \'Verifica di\'. Esempio: \'Le equazioni di secondo grado\'"
        )
        titolo_clean = titolo_resp.text.strip().strip('"').strip("'").strip()
        if not titolo_clean:
            titolo_clean = argomento.strip()
        _avanza("⚙️ Generazione esercizi...")

        # Istruzione BES/DSA rafforzata
        bes_rule = ""
        if bes_dsa:
            bes_rule = (
                "- BES/DSA OBBLIGATORIO: almeno il 25% dei sottopunti DEVE avere asterisco.\n"
                "  USA ESATTAMENTE questo formato: \\item[a*)] — lettera, asterisco, parentesi chiusa.\n"
                "  NON usare \\item[a.] NE \\item[a*] NE \\item[a.)] — SOLO \\item[a*)]\n"
                "  Scegli i sottopunti più complessi. Con 4 sottopunti: minimo 1 con *. Con 8+: minimo 2 con *.\n"
                "  IMPORTANTE: conta i sottopunti totali, calcola il 25% e assicurati di mettere asterisco su quel numero minimo PRIMA di terminare.\n"
                "  ESEMPIO CORRETTO con 4 sottopunti: \\item[a)] ... \\item[b)] ... \\item[c*)] ... \\item[d)] ..."
            )
        else:
            bes_rule = "- Nessun asterisco BES/DSA."

        # Istruzione punteggi
        punti_rule = ""
        if mostra_punteggi:
            punti_rule = f"- Ogni \\item DEVE avere \"(X pt)\" sulla stessa riga. Totale: {punti_totali} pt."
        else:
            punti_rule = "- NON inserire punti (X pt) in nessun esercizio né sottopunto."

        # Istruzione multidisciplinare
        multi_rule = ""
        if esercizio_multidisciplinare:
            materia2_str = f" con {materia2_scelta}" if materia2_scelta else " (scegli tu la disciplina più adatta)"
            diff_multi_str = f" Difficoltà dell'esercizio: {difficolta_multi}." if difficolta_multi else ""
            multi_rule = (
                f"- ESERCIZIO MULTIDISCIPLINARE: uno degli esercizi INCLUSI NEL TOTALE deve collegare "
                f"{materia}{materia2_str}.{diff_multi_str}\n"
                "  IMPORTANTE: usa SOLO strumenti già acquisiti dagli studenti. "
                "Niente formule nuove o concetti non ancora visti nel programma."
            )
        else:
            multi_rule = "- NON includere esercizi multidisciplinari."

        # Istruzione griglia
        griglia_rule = ("- NON generare la griglia (sarà aggiunta automaticamente)."
                        if con_griglia else "- NON generare nessuna griglia di valutazione.")

        # Costruiamo il preambolo fisso — l'AI non lo deve generare
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
  \\small \\textbf{{Nome e Cognome:}} \\hrulefill \\quad \\textbf{{Classe:}} \\hrulefill \\quad \\textbf{{Data:}} \\hrulefill \\\\
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
  CORRETTO: \\item[a)] Testo (5 pt) — SBAGLIATO: \\item Testo (5 pt)
{bes_rule}
{multi_rule}
- Scelta multipla: le opzioni DEVONO stare in un \\begin{enumerate}[a)] SEPARATO dopo la riga della domanda. FORMATO OBBLIGATORIO:
  \\item[a)] Testo domanda (5 pt)
  \\begin{enumerate}[a)]
    \\item Prima opzione
    \\item Seconda opzione
    \\item Terza opzione
    \\item Quarta opzione
  \\end{enumerate}
  MAI usare \\hspace per le opzioni. MAI mettere A) B) C) D) sulla riga della domanda.
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

        _avanza("🖨️ Compilazione PDF...")
        pdf_auto, err_auto = compila_pdf(latex_a_final)
        if pdf_auto:
            st.session_state.verifiche['A']['pdf'] = pdf_auto
            st.session_state.verifiche['A']['preview'] = True

        if correzione_step:
            _avanza("📝 Generazione soluzioni...")
            ps = (f"Risolvi questa verifica come docente correttore. Stesso preambolo.\n"
                  f"Titolo: 'Soluzioni — {titolo_clean}'. Niente griglia.\n"
                  f"1. \\subsection*{{Soluzioni Rapide}}: solo risultati finali, una riga per sottopunto.\n"
                  f"2. \\subsection*{{Svolgimento Dettagliato}}: \\subsubsection*{{Esercizio N}} + passaggi.\n"
                  f"SOLO CODICE LATEX.\n\n{latex_a}")
            rs = model.generate_content(ps)
            st.session_state.verifiche['A']['soluzioni_latex'] = (
                rs.text.replace("```latex","").replace("```","").strip())

        if doppia_fila:
            _avanza("📄 Generazione Versione B...")
            rb = model.generate_content(
                f"Versione B: stessa struttura, cambia dati e quesiti. "
                f"Restituisci SOLO il corpo degli esercizi (\\subsection* ecc.), "
                f"SENZA preambolo, SENZA \\documentclass, SENZA \\begin{{document}}. "
                f"Sostituisci 'Versione A' con 'Versione B' dove presente. "
                f"TERMINA con \\end{{document}}. SOLO LATEX.\n\n{corpo_latex}")
            corpo_latex_b = rb.text.replace("```latex","").replace("```","").strip()
            corpo_latex_b = re.sub(r'^.*?\\begin\{document\}[^\n]*\n?', '', corpo_latex_b, flags=re.DOTALL)
            corpo_latex_b = re.sub(r'^\\begin\{center\}.*?\\end\{center\}\s*', '', corpo_latex_b, flags=re.DOTALL)
            if "\\end{document}" not in corpo_latex_b:
                corpo_latex_b += "\n\\end{document}"
            preambolo_b = preambolo_fisso.replace(titolo_header, titolo_header.replace("Versione A", "Versione B") if "Versione A" in titolo_header else titolo_header + " — Versione B")
            latex_b = preambolo_b + corpo_latex_b
            latex_b = fix_items_environment(latex_b)
            if bes_dsa:
                latex_b = inietta_asterischi_bes(latex_b, percentuale=0.25)
            latex_b_final = inietta_griglia(latex_b, punti_totali) if con_griglia else latex_b
            st.session_state.verifiche['B'] = {**_vf(), 'latex': latex_b_final}

            _avanza("🖨️ Compilazione PDF Versione B...")
            pdf_b_auto, _ = compila_pdf(latex_b_final)
            if pdf_b_auto:
                st.session_state.verifiche['B']['pdf'] = pdf_b_auto
                st.session_state.verifiche['B']['preview'] = True
            if correzione_step:
                rsb = model.generate_content(
                    "Stessa struttura soluzioni (Rapide + Dettagliato). SOLO LATEX.\n\n" + latex_b)
                st.session_state.verifiche['B']['soluzioni_latex'] = (
                    rsb.text.replace("```latex","").replace("```","").strip())

        _pbar.progress(1.0, text="✅ Fatto!")
        st.success("✅ Verifica generata!"); st.rerun()

    except Exception as e:
        st.error(f"❌ Errore: {e}")

# ── OUTPUT ────────────────────────────────────────────────────────────────────────
if st.session_state.verifiche['A']['latex']:
    st.divider()
    _df  = doppia_fila   if 'doppia_fila'  in dir() else False
    _arg = titolo_clean  if 'titolo_clean' in dir() else (argomento if 'argomento' in dir() else 'verifica')
    _mid = modello_id    if 'modello_id'   in dir() else "gemini-2.5-flash"

    attive = ['A','B'] if _df and st.session_state.verifiche['B']['latex'] else ['A']
    cols   = st.columns(len(attive))

    for idx, fid in enumerate(attive):
        v = st.session_state.verifiche[fid]
        with cols[idx]:
            st.subheader(f"{APP_ICON} {'Versione ' + fid if _df else 'La tua verifica'}")

            # Riga 1: PDF | DOCX affiancati
            btn1, btn2 = st.columns(2)
            with btn1:
                if v['pdf']:
                    st.download_button("📥 Scarica PDF", v['pdf'],
                        file_name=f"Verifica_{_arg}_{fid}.pdf", mime="application/pdf",
                        use_container_width=True, key=f"dl_{fid}")
                else:
                    if st.button("📥 Scarica PDF", key=f"dlc_{fid}", use_container_width=True):
                        with st.spinner("Compilazione..."):
                            pdf, err = compila_pdf(v['latex'])
                        if pdf:
                            st.session_state.verifiche[fid]['pdf'] = pdf; st.rerun()
                        else:
                            st.error("Errore PDF")
                            with st.expander("Log"): st.text(err)
            with btn2:
                if v['docx']:
                    st.download_button("📝 Scarica Word", v['docx'],
                        file_name=f"Verifica_{_arg}_{fid}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True, key=f"dld_{fid}")
                else:
                    # Genera e offre download diretto senza secondo click
                    _docx_gen_key = f"_docx_generating_{fid}"
                    if st.button("📝 Genera Word (.docx)", key=f"dldc_{fid}", use_container_width=True):
                        st.session_state[_docx_gen_key] = True
                    if st.session_state.get(_docx_gen_key, False):
                        with st.spinner("⏳ Conversione in Word..."):
                            _m = genai.GenerativeModel(_mid)
                            db, de = latex_to_docx_via_ai(v['latex'], _m, con_griglia=con_griglia)
                        if db:
                            st.session_state.verifiche[fid]['docx'] = db
                            st.session_state[_docx_gen_key] = False
                            st.download_button("⬇️ Scarica Word ora", db,
                                file_name=f"Verifica_{_arg}_{fid}.docx",
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                use_container_width=True, key=f"dld_now_{fid}")
                        else:
                            st.session_state[_docx_gen_key] = False
                            st.error("Errore conversione Word")
                            with st.expander("Log"): st.text(de)

            # Riga 2: Soluzioni (se presenti)
            if v['soluzioni_latex']:
                if v['soluzioni_pdf']:
                    st.download_button("✅ Scarica Soluzioni", v['soluzioni_pdf'],
                        file_name=f"Soluzioni_{_arg}_{fid}.pdf", mime="application/pdf",
                        use_container_width=True, key=f"dls_{fid}")
                else:
                    if st.button("✅ Compila Soluzioni", key=f"cs_{fid}", use_container_width=True):
                        with st.spinner("Compilazione..."):
                            sp, se = compila_pdf(v['soluzioni_latex'])
                        if sp:
                            st.session_state.verifiche[fid]['soluzioni_pdf'] = sp; st.rerun()
                        else:
                            st.error("Errore soluzioni")
                            with st.expander("Log"): st.text(se)

            if v['preview'] and v['pdf']:
                b64 = base64.b64encode(v['pdf']).decode()
                st.markdown(
                    f'<iframe src="data:application/pdf;base64,{b64}" width="100%" height="700px"'
                    f' style="border:1px solid {T["border"]};border-radius:8px;"></iframe>',
                    unsafe_allow_html=True)



            with st.expander(f"🛠️ Editor LaTeX {fid}"):
                st.session_state.verifiche[fid]['latex'] = st.text_area(
                    "Codice:", value=v['latex'], height=300, key=f"ed_{fid}")
                if v['soluzioni_latex']:
                    st.session_state.verifiche[fid]['soluzioni_latex'] = st.text_area(
                        "Soluzioni:", value=v['soluzioni_latex'], height=200, key=f"eds_{fid}")