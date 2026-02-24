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
FEEDBACK_FORM_URL = "https://forms.gle/KNu8v8iDVUiGkQUL8"

MODELLI_DISPONIBILI = {
    "⚡ Flash 2.5 Lite (velocissimo)": "gemini-2.5-flash-lite",
    "⚡ Flash 2.5 (bilanciato)":        "gemini-2.5-flash",
    "🧠 Pro 2.5 (massima qualità)":     "gemini-2.5-pro",
}

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

SCUOLE = [
    "Scuola Primaria (Elementari)",
    "Scuola Secondaria I grado (Medie)",
    "Liceo Scientifico",
    "Liceo non Scientifico",
    "Istituto Tecnico",
    "Istituto Professionale",
]

CALIBRAZIONE_SCUOLA = {
    "Scuola Primaria": (
        "Target: 6-11 anni. Linguaggio ludico-concreto. "
        "Contesto: Vita quotidiana familiare, gioco, spesa. "
        "Usa frasi brevi e numeri entro il 1000. Evita simboli astratti, preferisci il testo narrativo."
    ),
    "Scuola Secondaria I grado": (
        "Target: 11-14 anni. Linguaggio in transizione verso il tecnico. "
        "Contesto: Scuola, sport, socialità, prime esplorazioni scientifiche. "
        "Difficoltà bilanciata: calcolo procedurale e primi problemi logici con frazioni e variabili."
    ),
    "Liceo Scientifico": (
        "Target: 14-19 anni. Linguaggio rigoroso e accademico. "
        "Contesto: Ricerca scientifica, astrazione pura, modellizzazione complessa. "
        "Livello elevato: stimola il ragionamento deduttivo e la giustificazione dei passaggi."
    ),
    "Liceo non Scientifico": (
        "Target: 14-19 anni. Linguaggio colto e argomentativo. "
        "Contesto: Storia delle idee, filosofia, analisi critica della realtà. "
        "Bilanciamento: Matematica vista come linguaggio logico, non solo come calcolo meccanico."
    ),
    "Istituto Tecnico": (
        "Target: 14-19 anni. Linguaggio tecnico-professionale. "
        "Contesto: Azienda, laboratorio, tecnologia, economia reale. "
        "Enfasi: Applicazione pratica dei teoremi a scenari lavorativi e dati reali."
    ),
    "Istituto Professionale": (
        "Target: 14-19 anni. Linguaggio pratico e operativo. "
        "Contesto: Situazioni lavorative simulate, compiti di realtà, problem solving guidato. "
        "Supporto: Suddividi i problemi complessi in step chiari ed espliciti."
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

TIPI_ESERCIZIO = ["Aperto", "Scelta multipla", "Vero/Falso", "Completamento", "Interdisciplinare"]

# ── FUNZIONI ───────────────────────────────────────────────────────────────────

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
        lettere = 'abcdefghijklmnopqrstuvwxyz'
        lettera_idx = 0

        for li, line in enumerate(lines):
            # Cerca \item[label] OPPURE \item semplice
            item_label_match = re.search(r'\\item\[([^\]]+)\]', line)
            item_plain_match = re.search(r'\\item(?!\[)', line)

            if not item_label_match and not item_plain_match:
                continue

            # Determina la label
            if item_label_match:
                raw_label = item_label_match.group(1).replace('*', '').strip()
            else:
                raw_label = lettere[lettera_idx % 26] + ")"
                lettera_idx += 1

            # Finestra di ricerca per i punti
            window_lines = []
            for lj in range(li, min(li + 15, len(lines))):
                if lj > li and (re.search(r'\\item(?:\[|(?!\w))', lines[lj])):
                    break
                window_lines.append(lines[lj])
            search_window = '\n'.join(window_lines)
            search_window = re.sub(
                r'\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}', '',
                search_window, flags=re.DOTALL
            )

            # Riconosce: (2 pt), (2pt), (2 punti), [2 pt], 2 pt
            pt_match = re.search(
                r'[\(\[]?\s*(\d+(?:[.,]\d+)?)\s*(?:pt|punt[io]|p\.?)\s*[\)\]]?',
                search_window, re.IGNORECASE
            )
            if not pt_match:
                continue

            punti = pt_match.group(1)
            items_found.append((raw_label, punti))

        if items_found:
            esercizi.append({'num': num_label, 'items': items_found})
    return esercizi

def build_griglia_latex(esercizi, punti_totali):
    if not esercizi:
        return ""
    col_spec = "|l|" + "".join("c|" * len(ex['items']) for ex in esercizi) + "c|"
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
    
def rimuovi_vspace_corpo(latex):
    """Rimuove tutti i \vspace e \hspace dal corpo degli esercizi."""
    # Rimuove \vspace{...} e \vspace*{...} ovunque nel corpo
    latex = re.sub(r'\\vspace\*?\{[^}]*\}', '', latex)
    # Rimuove \hspace{...} e \hspace*{...}
    latex = re.sub(r'\\hspace\*?\{[^}]*\}', '', latex)
    # Rimuove \bigskip, \medskip, \smallskip
    latex = re.sub(r'\\(?:big|med|small)skip\b', '', latex)
    # Rimuove righe vuote eccessive lasciate dalla rimozione
    latex = re.sub(r'\n{3,}', '\n\n', latex)
    return latex

def pulisci_corpo_latex(testo):
    """Rimuove tutto ciò che precede il primo \subsection*"""
    # Trova il primo \subsection*
    idx = testo.find('\\subsection*')
    if idx == -1:
        # Se non c'è \subsection*, rimuove almeno preambolo e intestazione
        testo = re.sub(r'^.*?\\begin\{document\}[^\n]*\n?', '', testo, flags=re.DOTALL)
        while re.match(r'^\s*\\begin\{center\}', testo):
            testo = re.sub(r'^\s*\\begin\{center\}.*?\\end\{center\}\s*', '', testo, flags=re.DOTALL)
    else:
        # Tronca tutto ciò che viene prima del primo \subsection*
        testo = testo[idx:]
    # Assicura \end{document} finale
    testo = re.sub(r'\\end\{document\}.*$', '', testo, flags=re.DOTALL).rstrip()
    testo += "\n\\end{document}"
    return testo

def rimuovi_punti_subsection(latex):
    """
    Rimuove i (X pt) che compaiono subito dopo \subsection*{...},
    lasciando solo quelli nei \item.
    """
    # Rimuove (X pt) sulla stessa riga di \subsection* o nella riga immediatamente dopo
    latex = re.sub(
        r'(\\subsection\*\{[^}]*\}[^\n]*)\s*\((\d+(?:[.,]\d+)?)\s*pt\)',
        r'\1',
        latex
    )
    # Rimuove una riga che contiene SOLO (X pt) subito dopo \subsection*
    latex = re.sub(
        r'(\\subsection\*\{[^}]*\})\s*\n\s*\(\d+(?:[.,]\d+)?\s*pt\)\s*\n',
        r'\1\n',
        latex
    )
    return latex

def riscala_punti(latex, punti_totali_target):
    """
    Trova tutti i (X pt) nel corpo, li riscala proporzionalmente
    in modo che la somma sia ESATTAMENTE punti_totali_target.
    """
    pattern = re.compile(r'\((\d+(?:[.,]\d+)?)\s*pt\)')
    matches = list(pattern.finditer(latex))
    if not matches:
        return latex

    valori = [float(m.group(1).replace(',', '.')) for m in matches]
    somma_attuale = sum(valori)
    if somma_attuale == 0:
        return latex

    # Riscala proporzionalmente
    fattore = punti_totali_target / somma_attuale
    nuovi_valori = [v * fattore for v in valori]

    # Arrotonda mantenendo il totale esatto
    nuovi_interi = [int(v) for v in nuovi_valori]
    resti = [(nuovi_valori[i] - nuovi_interi[i], i) for i in range(len(nuovi_valori))]
    differenza = punti_totali_target - sum(nuovi_interi)
    resti.sort(reverse=True)
    for i in range(int(round(differenza))):
        nuovi_interi[resti[i][1]] += 1

    # Sostituisci nel LaTeX
    risultato = latex
    offset = 0
    for i, m in enumerate(matches):
        vecchio = m.group(0)
        nuovo = f"({nuovi_interi[i]} pt)"
        start = m.start() + offset
        end = m.end() + offset
        risultato = risultato[:start] + nuovo + risultato[end:]
        offset += len(nuovo) - len(vecchio)

    return risultato
    
def inietta_griglia(latex, punti_totali):
    latex = re.sub(
        r'(\\vspace\{[^}]+\}\s*)?% GRIGLIA.*?\\end\{center\}',
        '', latex, flags=re.DOTALL
    )
    latex = re.sub(
        r'(\\vspace\{[^}]+\}\s*)?\\begin\{center\}\s*\\textbf\{Griglia[^}]*\}.*?\\end\{center\}',
        '', latex, flags=re.DOTALL
    )

    esercizi = parse_esercizi(latex)
    if not esercizi:
        return latex

    griglia = build_griglia_latex(esercizi, punti_totali)

    try:
        tot_reale = sum(
            float(pts.replace(',', '.'))
            for ex in esercizi for _, pts in ex['items']
        )
        if abs(tot_reale - punti_totali) > 0.5:
            griglia = build_griglia_latex(esercizi, int(tot_reale) if tot_reale == int(tot_reale) else round(tot_reale, 1))
    except Exception:
        pass

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
    text = _r.sub(r'\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}', '[Grafico]', text, flags=_r.DOTALL)
    text = _r.sub(r'\\begin\{axis\}.*?\\end\{axis\}', '[Grafico]', text, flags=_r.DOTALL)
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

        body = _r.sub(r'\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}', '\n[Grafico]\n', body, flags=_r.DOTALL)
        body = _r.sub(r'\\begin\{axis\}.*?\\end\{axis\}', '\n[Grafico]\n', body, flags=_r.DOTALL)

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


def latex_to_docx_via_ai(codice_latex, con_griglia=True):
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
            righe.append(f"  - Esercizio {i_ex+1}: circa {pts_per_ex[i_ex]} pt (distribuisci tra i sottopunti)")
        righe.append(f"REGOLA CRITICA: la somma di TUTTI i (X pt) nei sottopunti DEVE essere ESATTAMENTE {punti_totali} pt.")

    ha_primo_custom = len(esercizi_custom) > 0
    if not ha_primo_custom:
        righe.append(
            f"\nREGOLA PRIMO ESERCIZIO (Esercizio 1 — SEMPRE presente, NON modificabile):\n"
            f"Il primo esercizio DEVE chiamarsi 'Saperi Essenziali' e coprire i concetti fondamentali\n"
            f"dell'argomento che TUTTI gli studenti devono conoscere (definizioni, concetti base, formule\n"
            f"chiave, fatti imprescindibili). NON inserire mai il simbolo (*) in questo esercizio:\n"
            f"è obbligatorio per tutti, nessuna esclusione. Calibra il livello di difficoltà in modo\n"
            f"accessibile. Gli esercizi {2}–{num_totale} possono approfondire e variare."
        )

    righe.append(f"\nDETTAGLIO ESERCIZI ({num_totale} totali):")
    for i, ex in enumerate(esercizi_custom, 1):
        tipo, desc = ex.get('tipo', 'Aperto'), ex.get('descrizione', '').strip()
        if tipo == "Interdisciplinare" and ex.get('materia2'):
            tipo = f"Interdisciplinare con {ex['materia2']} (difficoltà: {ex.get('difficolta_multi','Media')})"
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
        start_idx = len(esercizi_custom) + 1
        end_idx   = num_totale
        righe.append(f"- Esercizi {start_idx}–{end_idx}: genera tu {n_liberi} esercizi coerenti con l'argomento.")
    return "\n".join(righe), immagini


# ── HELPER ───────────────────────────────────────────────────────────────────────
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


if 'verifiche' not in st.session_state: st.session_state.verifiche = {'A': _vf(), 'B': _vf(), 'R': _vf()}
if 'esercizi_custom' not in st.session_state: st.session_state.esercizi_custom = []
if 'last_materia'    not in st.session_state: st.session_state.last_materia = None
if 'last_argomento'  not in st.session_state: st.session_state.last_argomento = None
if 'last_gen_ts'     not in st.session_state: st.session_state.last_gen_ts = None

# ── CSS GLOBALE ──────────────────────────────────────────────────────────────────
is_dark = (st.session_state.theme == "dark")

# Colori fissi sidebar (sempre dark)
_SB_LABEL   = "#c8c6bc"   
_SB_MUTED   = "#8a8880"
_SB_BORDER  = "#2a2926"
_SB_TEXT    = "#e8e6e0"   

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

  header[data-testid="stHeader"] {{
    background-color: {T['bg']} !important;
    border-bottom: 1px solid {T['border']} !important;
  }}

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

  /* ════ SIDEBAR ════ */
  [data-testid="stSidebar"] {{
    background: #141412 !important;
    border-right: 1px solid {_SB_BORDER} !important;
  }}
  .sidebar-title {{
    font-family: 'DM Sans', sans-serif;
    font-size: 1.1rem !important;
    font-weight: 800 !important;
    letter-spacing: -0.01em;
    color: #f5f3ed !important;
    margin: 0.5rem 0 1.2rem 0;
    padding-bottom: 0.6rem;
    border-bottom: 1px solid {_SB_BORDER};
  }}
  .sidebar-label {{
    font-size: 0.75rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.06em !important;
    text-transform: uppercase !important;
    color: {_SB_LABEL} !important;
    margin: 0.8rem 0 0.4rem 0;
    padding-bottom: 0.25rem;
    border-bottom: 1px solid {_SB_BORDER};
  }}
  [data-testid="stSidebar"] .block-container {{
    padding: 1.5rem 1.2rem !important;
    max-width: 100% !important;
  }}
  [data-testid="stSidebar"] p,
  [data-testid="stSidebar"] span,
  [data-testid="stSidebar"] label,
  [data-testid="stSidebar"] div {{
    color: {_SB_TEXT} !important;
  }}
  [data-testid="stSidebar"] .stTextInput label p,
  [data-testid="stSidebar"] .stSelectbox label p,
  [data-testid="stSidebar"] .stNumberInput label p {{
    color: {_SB_MUTED} !important;
    font-size: 0.7rem !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    font-weight: 700 !important;
  }}
  [data-testid="stSidebar"] .stCheckbox label {{
    color: {_SB_TEXT} !important;
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
    color: #f5f3ed !important;
  }}
  [data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] > div:first-child {{
    background: #232320 !important;
    border: 1.5px solid #3d3c36 !important;
    border-radius: 8px !important;
  }}
  [data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] span {{
    color: #f5f3ed !important;
  }}
  [data-testid="stSidebar"] .stRadio label {{
    color: {_SB_TEXT} !important;
  }}
  [data-testid="stSidebar"] .stRadio [data-testid="stMarkdownContainer"] p {{
    color: {_SB_TEXT} !important;
  }}
  [data-testid="stSidebar"] .stButton button {{
    background: #232320 !important;
    color: #f5f3ed !important;
    border: 1.5px solid #3d3c36 !important;
    border-radius: 8px !important;
  }}
  [data-testid="stSidebar"] .stButton button:hover {{
    background: #2e2d28 !important;
    border-color: #5a5950 !important;
  }}
  [data-testid="stSidebar"] .stSelectSlider [data-testid="stMarkdownContainer"] p {{
    color: {_SB_TEXT} !important;
  }}
  [data-testid="stSidebar"] .section-label {{
    color: #5a5950 !important;
    border-bottom-color: {_SB_BORDER} !important;
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

  /* ── HERO ── */
  .hero-wrap {{
    margin-bottom: 2.5rem;
    padding-bottom: 1.8rem;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-direction: column;
    flex-wrap: wrap;
    gap: 0;
    position: relative;
  }}
  .hero-wrap::after {{
    content: '';
    position: absolute;
    bottom: 0;
    left: 50%;
    transform: translateX(-50%);
    width: 100%;
    height: 1px;
    background: linear-gradient(
      90deg,
      transparent 0%,
      {T['border2']} 20%,
      {T['accent']} 50%,
      {T['border2']} 80%,
      transparent 100%
    );
  }}
  .hero-left {{ flex: 1; min-width: 200px; text-align: center; }}
  @keyframes iconBounce {{
    0%   {{ transform: rotate(0deg) scale(1); }}
    15%  {{ transform: rotate(-12deg) scale(1.15); }}
    30%  {{ transform: rotate(8deg) scale(1.1); }}
    45%  {{ transform: rotate(-6deg) scale(1.05); }}
    60%  {{ transform: rotate(3deg) scale(1.02); }}
    75%  {{ transform: rotate(-1deg) scale(1.01); }}
    100% {{ transform: rotate(0deg) scale(1); }}
  }}
  @keyframes badgePop {{
    0%   {{ opacity: 0; transform: translateY(6px); }}
    100% {{ opacity: 1; transform: translateY(0); }}
  }}
  @keyframes subFadeIn {{
    0%   {{ opacity: 0; transform: translateY(4px); }}
    100% {{ opacity: 1; transform: translateY(0); }}
  }}
  .hero-title {{
    font-family: 'DM Sans', sans-serif;
    font-size: 96px !important;
    font-weight: 900 !important;
    color: {T['text']};
    line-height: 1.0;
    margin: 0 0 0.15rem 0;
    letter-spacing: -0.04em;
    display: inline-flex;
    align-items: center;
    gap: 0;
    justify-content: center;
  }}
  .hero-icon {{
    display: inline-block;
    margin-right: 0.3em;
    animation: iconBounce 1.1s ease 0.2s both;
    transform-origin: center bottom;
  }}
  .hero-ai {{
    background: linear-gradient(135deg, {T['accent']} 0%, #FF8C00 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    animation: badgePop 0.6s ease 0.5s both;
  }}
  .hero-sub {{
    font-size: 1.05rem;
    color: {T['text2']};
    margin: 0 0 0.55rem 0;
    font-weight: 500;
    letter-spacing: -0.01em;
    animation: subFadeIn 0.5s ease 0.35s both;
    opacity: 0;
  }}
  .hero-beta {{
    display: inline-block;
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: {T['muted']};
    background: {T['card2']};
    border: 1px solid {T['border2']};
    border-radius: 100px;
    padding: 2px 10px;
    font-family: 'DM Sans', sans-serif;
    animation: badgePop 0.5s ease 0.75s both;
    opacity: 0;
  }}
  .hero-right {{
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-shrink: 0;
    padding-top: 4px;
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

 /* ════ BOTTONE PRIMARIO (Genera Verifica - VERSIONE FORZATA) ════ */
  div.stButton > button[kind="primary"] {{
    background: #D97706 !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    transition: transform 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275), box-shadow 0.2s ease, filter 0.2s ease !important;
    box-shadow: 0 2px 12px rgba(217,119,6,0.35) !important;
    display: block !important;
  }}

  div.stButton > button[kind="primary"]:hover {{
    transform: scale(1.05) !important; /* Ingrandimento del 5% */
    box-shadow: 0 10px 25px rgba(217,119,6,0.5) !important;
    filter: brightness(1.1) !important;
    border: none !important;
  }}

  div.stButton > button[kind="primary"]:active {{
    transform: scale(0.98) !important; /* Si schiaccia quando clicchi */
  }}

  /* ── STILE CARD DOWNLOAD (Mantieni queste per il blocco 3) ── */
  .dl-card {{
    background: #FFFFFF !important;
    padding: 1.2rem;
    border-radius: 15px;
    border: 1px solid #E0E0E0;
    text-align: center;
    margin-bottom: 1rem;
  }}
  .dl-label {{
    font-size: 0.85rem;
    color: #666;
    margin-bottom: 0.8rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }}
  .hint-docx {{
    font-size: 0.78rem;
    color: #888;
    line-height: 1.3;
    margin-top: 12px;
    font-style: italic;
    text-align: left;
    border-top: 1px solid #EEE;
    padding-top: 8px;
  }}
  /* ── BOTTONI SECONDARI E DOWNLOAD UNIFICATI ── */
  .stDownloadButton button,
  [data-testid="stDownloadButton"] button,
  .stButton [data-testid="baseButton-secondary"],
  .stButton button[kind="secondary"],
  button[data-testid="baseButton-secondary"] {{
    background: {T['card']} !important;
    color: {T['text']} !important;
    border: 1.5px solid {T['border2']} !important;
    border-radius: 12px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 1.05rem !important;
    font-weight: 700 !important;
    padding: 1rem 1.4rem !important;
    transition: border-color 0.18s ease, box-shadow 0.18s ease, transform 0.18s ease !important;
    letter-spacing: 0.01em !important;
    box-shadow: 0 2px 6px rgba(0,0,0,0.04) !important;
    width: 100% !important;
  }}
  .stDownloadButton button:hover,
  [data-testid="stDownloadButton"] button:hover,
  .stButton [data-testid="baseButton-secondary"]:hover,
  button[data-testid="baseButton-secondary"]:hover {{
    background: {T['hover']} !important;
    border-color: {T['accent']} !important;
    transform: translateY(-3px) !important;
    box-shadow: 0 6px 20px rgba(217,119,6,0.18) !important;
    color: {T['text']} !important;
  }}

  /* ── COMPACT UPLOADER ── */
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

  /* ── TEX DOWNLOAD ── */
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
    box-shadow: none !important;
    transform: none !important;
  }}
  .tex-btn-wrap .stDownloadButton button:hover,
  .tex-btn-wrap [data-testid="stDownloadButton"] button:hover {{
    color: {T['text2']} !important;
    border-color: #5a5950 !important;
    background: {T['card2']} !important;
    box-shadow: none !important;
    transform: translateY(-1px) !important;
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

  /* ── EXPANDER HEADING ── */
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
  .stAlert p,
  .stAlert span,
  .stAlert div,
  [data-testid="stAlert"] p,
  [data-testid="stAlert"] span,
  [data-testid="stAlert"] div {{
      color: #1a1915 !important;
      opacity: 1 !important;
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

  /* ── STATUS BAR ── */
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

  /* ── PDF PREVIEW ── */
  .pdf-preview-wrap {{
    margin-top: 1rem;
    border: 1px solid {T['border']};
    border-radius: 14px;
    overflow: hidden;
    box-shadow: {T['shadow_md']};
    background: {T['card2']};
  }}

  /* ── TOP BAR ── */
  .top-bar {{
    display: flex;
    align-items: center;
    justify-content: flex-start;
    gap: 0.75rem;
    margin-bottom: 1.2rem;
  }}
  .top-bar-hint {{
    display: none;
  }}
  @media (max-width: 640px) {{
    .top-bar-hint {{
      display: inline-flex;
      align-items: center;
      gap: 5px;
      background: {T['accent_light']};
      border: 1px solid {T['accent']};
      border-radius: 20px;
      padding: 5px 12px;
      font-size: 0.72rem;
      color: {T['accent']};
      font-weight: 600;
      white-space: nowrap;
    }}
  }}

  /* ── FEEDBACK BUTTON (FAB) ── */
  .fab-link {{
    position: fixed;
    top: 4.5rem;
    right: 1.5rem;
    z-index: 9999;
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: {T['accent']};
    color: #ffffff !important;
    text-decoration: none !important;
    border-radius: 50px;
    padding: 10px 18px;
    font-family: 'DM Sans', sans-serif;
    font-size: 0.84rem;
    font-weight: 700;
    box-shadow: 0 4px 18px rgba(217,119,6,0.40);
    transition: transform 0.15s ease, filter 0.15s ease;
    white-space: nowrap;
  }}
  .fab-link:hover {{
    transform: translateY(-2px);
    filter: brightness(1.1);
    color: #ffffff !important;
  }}
  @media (max-width: 640px) {{
    .fab-link {{
      top: 4rem;
      right: 0.8rem;
      padding: 8px 14px;
      font-size: 0.78rem;
    }}
  }}

  /* ── DISCLAIMER ── */
  .disclaimer {{
    display: flex;
    align-items: flex-start;
    gap: 8px;
    padding: 8px 12px;
    background: {T['card2']};
    border: 1px solid {T['border']};
    border-left: 3px solid {T['muted']};
    border-radius: 8px;
    font-size: 0.74rem;
    color: {T['muted']};
    font-family: 'DM Sans', sans-serif;
    line-height: 1.45;
    margin-bottom: 1rem;
  }}
  .disclaimer-icon {{ flex-shrink: 0; font-size: 0.9rem; margin-top: 1px; }}

  /* ── APP FOOTER ── */
  .app-footer {{
    text-align: center;
    font-size: 0.72rem;
    color: {T['muted']};
    font-family: 'DM Sans', sans-serif;
    margin-top: 3rem;
    padding-top: 1.2rem;
    border-top: 1px solid {T['border']};
    line-height: 1.6;
  }}

  /* ═══ MOBILE ═══ */
  @media (max-width: 640px) {{
    .block-container {{
      padding: 4.5rem 1rem 3rem !important;
    }}
    .hero-title {{ font-size: 56px !important; }}
    .hero-sub {{ font-size: 0.95rem !important; }}
    .hero-wrap {{ margin-bottom: 1.5rem; padding-bottom: 1.2rem; }}
    .top-bar {{
      justify-content: center;
      gap: 0.5rem;
    }}
    .stTextInput input,
    .stNumberInput input {{
      font-size: 1rem !important;
      padding: 14px 16px !important;
      min-height: 52px !important;
      height: 52px !important;
      line-height: 1.4 !important;
      box-sizing: border-box !important;
    }}
    .stTextInput > div > div {{
      min-height: 52px !important;
    }}
    .stTextInput input::placeholder,
    .stNumberInput input::placeholder {{
      font-size: 1rem !important;
      opacity: 1 !important;
    }}
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
    [data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] > div:first-child {{
      min-height: 48px !important;
      padding: 10px 12px !important;
    }}
    [data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] span {{
      font-size: 0.85rem !important;
      color: #f5f3ed !important;
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
</style>
""", unsafe_allow_html=True)

# ── FEEDBACK BUTTON ──────────────────────────────────────────────────────────────
st.markdown(f"""
<a class="fab-link" href="{FEEDBACK_FORM_URL}" target="_blank" rel="noopener noreferrer"
   onclick="window.open(this.href,'_blank','noopener,noreferrer'); return false;">
  💬 &nbsp; Feedback & Bug
</a>
""", unsafe_allow_html=True)

# ── SIDEBAR ──────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-title">⚙️ Impostazioni</div>', unsafe_allow_html=True)

    st.markdown('<div class="sidebar-label">🏫 Classe</div>', unsafe_allow_html=True)
    st.caption("ℹ️ Attenzione: questa scelta influenza radicalmente il lessico, i riferimenti teorici e la complessità matematica degli esercizi.")
    difficolta = st.selectbox("livello", SCUOLE, index=3, label_visibility="collapsed")

    st.markdown('<div class="sidebar-label" style="margin-top:1rem;">📋 Opzioni</div>', unsafe_allow_html=True)
    bes_dsa = st.checkbox(
    "Genera versione ridotta (sostegno/certificazioni)",
    value=False,
    help="Verrà generato un secondo file identico ma con una percentuale di esercizi in meno, scelti tra i più complessi. I punteggi verranno ricalcolati automaticamente."
    )
    perc_ridotta = None
    if bes_dsa:
        perc_ridotta = st.select_slider(
            "Esercizi da rimuovere",
            help="Es. 20% = verranno eliminati circa 1 esercizio ogni 5, partendo dai più complessi",
            options=[10, 20, 30],
            value=20,
            format_func=lambda x: f"-{x}%",
            
    )
    doppia_fila     = st.checkbox("Genera Versione A e B (due varianti)", value=False)
    correzione_step = st.checkbox("Includi soluzioni passo per passo", value=False)

    esercizio_multidisciplinare = False
    materia2_scelta  = None
    difficolta_multi = None

    st.markdown('<div class="sidebar-label" style="margin-top:1rem;">🏆 Punteggi</div>', unsafe_allow_html=True)
    mostra_punteggi = st.checkbox("Mostra punteggio per esercizio", value=False)
    con_griglia     = st.checkbox("Includi griglia di valutazione", value=False)
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

# ── TOPBAR ───────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="top-bar">
  <div class="top-bar-hint">⚙️ Tocca &nbsp;<strong>&gt;&gt;</strong>&nbsp; qui sopra per le impostazioni</div>
</div>
""", unsafe_allow_html=True)

# ── HEADER ───────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="hero-wrap">
  <div class="hero-left">
    <h1 class="hero-title"><span class="hero-icon">{APP_ICON}</span> Verific<span class="hero-ai">AI</span></h1>
    <p class="hero-sub">{APP_TAGLINE}</p>
    <span class="hero-beta">Versione Beta</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ── FORM PRINCIPALE ───────────────────────────────────────────────────────────────
st.info("💡 **Suggerimento:** Più sei preciso nei dettagli (Argomento, Note aggiuntive, Stile desiderato), più l'AI capirà le tue esigenze e genererà una verifica vicina alle tue aspettative. Sfrutta a pieno le opzioni se hai in mente qualcosa di specifico!", icon="🧠")

st.markdown('<div class="expander-heading">📖 Materia</div>', unsafe_allow_html=True)
_materie_select = MATERIE + ["✏️ Altra materia..."]
_materia_sel = st.selectbox("Materia", _materie_select, index=0, label_visibility="collapsed")
if _materia_sel == "✏️ Altra materia...":
    materia_scelta = st.text_input("Scrivi materia:", placeholder="es. Economia Aziendale, Scienze Naturali...",
                                   key="_materia_custom_input", label_visibility="collapsed").strip() or "Matematica"
else:
    materia_scelta = _materia_sel or "Matematica"

st.markdown('<div style="height:0.8rem;"></div>', unsafe_allow_html=True)

st.markdown('<div class="expander-heading">📚 Argomento della verifica</div>', unsafe_allow_html=True)
argomento_area = st.text_area(
    "argomento",
    placeholder="es. Le equazioni di secondo grado\nes. La Rivoluzione Francese",
    height=90,
    label_visibility="collapsed",
    key="argomento_area"
)
argomento = argomento_area.strip()

st.markdown('<div style="height:0.8rem;"></div>', unsafe_allow_html=True)

with st.expander("✏️  Personalizza la verifica  *(opzionale)*"):

    st.markdown(f'<div class="expander-heading">⏱️ Tempistiche e Struttura</div>', unsafe_allow_html=True)
    _c_dur, _c_num = st.columns(2)
    with _c_dur:
        durata_scelta = st.selectbox(
            "Durata della verifica",
            ["30 min", "1 ora", "1 ora e 30 min", "2 ore"],
            index=1,
            help="L'AI calcolerà la lunghezza dei calcoli e la complessità dei passaggi per far completare la verifica in questo tempo."
        )
    with _c_num:
        num_esercizi_totali = st.slider(
            "Numero di esercizi in verifica",
            min_value=1, max_value=15, value=4,
            help="Trascina per scegliere il numero totale di esercizi."
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
                t = st.selectbox("Tipo esercizio", TIPI_ESERCIZIO,
                                 index=TIPI_ESERCIZIO.index(ex.get('tipo', 'Aperto')),
                                 key=f"tipo_{i}", label_visibility="visible")
                st.session_state.esercizi_custom[i]['tipo'] = t

                if t == "Interdisciplinare":
                    m2 = st.text_input(
                        "Materia collegata",
                        value=ex.get('materia2', ''),
                        placeholder="es. Fisica, Storia dell'Arte, Informatica...",
                        key=f"materia2_{i}", label_visibility="visible"
                    )
                    st.session_state.esercizi_custom[i]['materia2'] = m2
                    df2 = st.select_slider(
                        "Difficoltà collegamento",
                        options=["Facile", "Media", "Alta"],
                        value=ex.get('difficolta_multi', 'Media'),
                        key=f"diff_multi_{i}"
                    )
                    st.session_state.esercizi_custom[i]['difficolta_multi'] = df2

                d = st.text_input("Descrizione dell'esercizio (opzionale)",
                                  value=ex.get('descrizione', ''),
                                  placeholder="es. Risolvi ax²+bx+c=0 mostrando i passaggi",
                                  key=f"desc_{i}", label_visibility="visible")
                st.session_state.esercizi_custom[i]['descrizione'] = d
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
            st.session_state.esercizi_custom.append({'tipo': 'Aperto', 'descrizione': '', 'immagine': None, 'materia2': '', 'difficolta_multi': 'Media'})
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

# ── LOGICA GENERAZIONE ───────────────────────────────────────────────────────────
if genera_btn:
    if not argomento.strip():
        st.warning("⚠️ Inserisci l'argomento della verifica."); st.stop()
    try:
        model        = genai.GenerativeModel(modello_id)
        materia      = materia_scelta.strip() or "Matematica"
        e_mat        = any(k in materia.lower() for k in ["matem","fis","chim","inform","elettr","meccan"])
        nota_bes = "Svolgere tutti gli esercizi mostrando i passaggi."
        calibrazione = CALIBRAZIONE_SCUOLA.get(difficolta, "")
        s_note       = f"\nNOTE DOCENTE: {note_generali.strip()}" if note_generali.strip() else ""
        s_es, imgs_es = costruisci_prompt_esercizi(
            st.session_state.esercizi_custom, num_esercizi_totali,
            punti_totali if mostra_punteggi else 0, mostra_punteggi)
        titolo_a = "Versione A" if doppia_fila else ""

        _n_steps = 3 + (1 if correzione_step else 0) + (2 if doppia_fila else 0)
        _step    = [0]
        _prog    = st.empty()

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

        _avanza("✍️  Elaborazione titolo…")

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
        _avanza("🧠  Generazione esercizi in corso…")

        bes_rule = "- NON inserire mai il simbolo (*) accanto a nessun sottopunto."

        if mostra_punteggi:
            punti_rule = (
                f"- PUNTEGGI OBBLIGATORI: ogni \\item DEVE avere \"(X pt)\" SULLA STESSA RIGA, subito dopo il testo.\n"
                f"- Formato ESATTO e UNICO accettato: (X pt) — esempio: \\item[a)] Risolvi l'equazione. (3 pt)\n"
                f"- NON usare formati alternativi come [X pt], X punti, X p., pt X, ecc.\n"
                f"- La somma di TUTTI i (X pt) deve essere ESATTAMENTE {punti_totali} pt. CONTROLLA prima di terminare.\n"
                f"- Distribuisci i punti in modo che sia facile ottenere almeno 60% svolgendo le parti più semplici.\n"
                f"- NON inserire punti nel titolo \\subsection*, SOLO nei \\item.\n"
                f"- Se dimentichi il punteggio anche su UN SOLO \\item, la griglia di valutazione sarà incompleta."
            )
        else:
            punti_rule = "- NON inserire punti (X pt) in nessun esercizio né sottopunto."

        if esercizio_multidisciplinare:
            materia2_str   = f" con {materia2_scelta}" if materia2_scelta else " (scegli tu la disciplina più adatta)"
            diff_multi_str = f" Difficoltà: {difficolta_multi}." if difficolta_multi else ""
            multi_rule = (
                f"- ESERCIZIO MULTIDISCIPLINARE: uno degli esercizi INCLUSI NEL TOTALE deve collegare "
                f"{materia}{materia2_str}.{diff_multi_str}\n"
                "  Usa SOLO strumenti già acquisiti dagli studenti."
            )
        else:
            multi_rule = "- NON includere esercizi multidisciplinari."

        griglia_rule = ("- NON generare la griglia (sarà aggiunta automaticamente dopo)."
                        if con_griglia else "- NON generare nessuna griglia di valutazione.")

        if e_mat:
            grafici_rule = (
                "- GRAFICI pgfplots: quando il grafico è un DATO fornito allo studente "
                "(es. 'osserva il grafico della parabola e determina...', 'dal grafico ricava...'), "
                "DEVI obbligatoriamente generarlo con pgfplots/tikzpicture. "
                "Esempio per parabola: \\begin{tikzpicture}\\begin{axis}[width=7cm,height=5.5cm,"
                "axis lines=center,xlabel=$x$,ylabel=$y$,grid=both,xtick={-4,...,4},ytick={-4,...,4}]"
                "\\addplot[blue,thick,domain=-3:3,samples=100]{x^2-2*x-3}; \\end{axis}\\end{tikzpicture} "
                "MI RACCOMANDO NON lasciare MAI spazio extra per disegnare se lo studente deve disegnare lui il grafico, lo fara sul suo foglio."
            )
            pgfplots_pkg = "\\usepackage{pgfplots}\n\\pgfplotsset{compat=1.18}\n\\usepackage{tikz}"
        else:
            grafici_rule = ""
            pgfplots_pkg = ""

        titolo_header = f"Verifica di {materia}: {titolo_clean}" + (f" — {titolo_a}" if titolo_a else "")
        _hspace6 = "{6cm}"
        _hspace4 = "{4cm}"

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
  \\small \\textbf{{Nome:}} \\underline{{\\hspace{_hspace6}}} \\quad \\textbf{{Classe e Data:}} \\underline{{\\hspace{_hspace4}}} \\\\
  \\vspace{{0.3cm}}
  \\textit{{\\small {nota_bes}}}
\\end{{center}}
"""

        prompt_a = f"""Sei un docente esperto di {materia} e LaTeX. Genera SOLO il corpo degli esercizi (senza preambolo, senza \\documentclass, senza \\begin{{document}}) per una verifica su: {argomento}.
{f'Punti totali da distribuire: {punti_totali} pt.' if mostra_punteggi else ''}

CALIBRAZIONE LIVELLO E TEMPO:
{calibrazione}
- DURATA PREVISTA: {durata_scelta}. Regola la lunghezza dei calcoli, il numero di incognite e la complessità testuale in modo che {num_esercizi_totali} esercizi siano agevolmente fattibili nel tempo scelto.
- BILANCIAMENTO CONTESTO E MODELLAZIONE: NON esagerare con i problemi applicati alla realtà o fortemente interdisciplinari (es. non inserire scenari ingegneristici o fisici su tutti gli esercizi di matematica). MASSIMO 1 o 2 esercizi possono essere fortemente contestualizzati. I restanti DEVONO essere esercizi canonici, diretti e focalizzati sulla procedura pura per non sovraccaricare cognitivamente lo studente.

REGOLE TASSATIVE SUI GRAFICI (LOGICA ANTI-SPOILER):
- Se l'esercizio richiede esplicitamente allo studente di "disegnare", "rappresentare graficamente", "tracciare" o "costruire" una figura/grafico, NON generare il codice TikZ del grafico risolto.
- In questi casi, limita l'output al testo della consegna e lascia lo spazio bianco per lo svolgimento usando \\vspace{{5cm}} o una griglia vuota.
- Genera un grafico (TikZ) SOLO se esso è un dato di partenza necessario fornito dal docente (es. "Dato il seguente grafico, ricava i dati...").

{s_note}
{s_es}

REGOLE LATEX (TASSATIVE):
{griglia_rule}
{punti_rule}
- NUMERO ESERCIZI: genera ESATTAMENTE {num_esercizi_totali} blocchi \\subsection*. CONTA i tuoi blocchi prima di chiudere. Se ne hai di più, elimina i superflui. Se ne hai di meno, aggiungine.
- Titoli: \\subsection*{{Esercizio N: Titolo}}
- SOTTOPUNTI OBBLIGATORI: usa SEMPRE \\item[a)] \\item[b)] \\item[c)] ecc. con label ESPLICITA tra parentesi quadre.
- PROTEZIONE ESERCIZIO 1 (Saperi Essenziali): nell'Esercizio 1 NON inserire MAI il simbolo (*) su nessun sottopunto. È obbligatorio per tutti gli studenti senza eccezioni.
{multi_rule}
- Scelta multipla: le opzioni DEVONO stare in un \\begin{{enumerate}}[a)] SEPARATO dopo la domanda.
- Vero/Falso: $\\square$ \\textbf{{V}} $\\quad\\square$ \\textbf{{F}}
- Completamento: \\underline{{\\hspace{{3cm}}}}
{grafici_rule}

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
        _avanza("⚙️  Elaborazione LaTeX…")

        corpo_latex = ra.text.replace("```latex","").replace("```","").strip()
        corpo_latex = pulisci_corpo_latex(corpo_latex)

        # ── GUARDIA: tronca esercizi in eccesso ──────────────────────────────
        splits = re.split(r'(\\subsection\*\{)', corpo_latex)
        n_blocchi = (len(splits) - 1) // 2
        if n_blocchi > num_esercizi_totali:
            testa = splits[0]
            blocchi_da_tenere = []
            for b in range(num_esercizi_totali):
                blocchi_da_tenere.append(splits[1 + b*2])
                blocchi_da_tenere.append(splits[2 + b*2])
            corpo_troncato = testa + "".join(blocchi_da_tenere)
            corpo_troncato = re.sub(r'\\end\{document\}.*$', '', corpo_troncato, flags=re.DOTALL).rstrip()
            corpo_latex = corpo_troncato + "\n\\end{document}"

        latex_a = preambolo_fisso + corpo_latex
        latex_a = fix_items_environment(latex_a)
        latex_a = rimuovi_vspace_corpo(latex_a)
        if mostra_punteggi:
            latex_a = rimuovi_punti_subsection(latex_a)
            latex_a = riscala_punti(latex_a, punti_totali)

        if con_griglia:
            latex_a_final = inietta_griglia(latex_a, punti_totali)
        else:
            latex_a_final = latex_a

        st.session_state.verifiche['A'] = {**_vf(), 'latex': latex_a_final}

        _avanza("🖨️  Compilazione PDF…")
        pdf_auto, err_auto = compila_pdf(latex_a_final)
        if pdf_auto:
            st.session_state.verifiche['A']['pdf']     = pdf_auto
            st.session_state.verifiche['A']['pdf_ts']  = time.time()
            st.session_state.verifiche['A']['preview'] = True
        else:
            if con_griglia:
                pdf_fallback, _ = compila_pdf(latex_a)
                if pdf_fallback:
                    st.session_state.verifiche['A']['pdf']     = pdf_fallback
                    st.session_state.verifiche['A']['pdf_ts']  = time.time()
                    st.session_state.verifiche['A']['preview'] = True
                    st.warning("⚠️ La griglia di valutazione non è stata inclusa nel PDF (errore di compilazione). Scarica il .tex per debug.")

        if correzione_step:
            _avanza("📝  Generazione soluzioni…")
            ps = (f"Risolvi questa verifica come docente correttore. Stesso preambolo.\n"
                  f"Titolo: 'Soluzioni — {titolo_clean}'. Niente griglia.\n"
                  f"1. \\subsection*{{Soluzioni Rapide}}: solo risultati finali.\n"
                  f"2. \\subsection*{{Svolgimento Dettagliato}}: passaggi completi.\n"
                  f"SOLO CODICE LATEX.\n\n{latex_a}")
            rs = model.generate_content(ps)
            st.session_state.verifiche['A']['soluzioni_latex'] = (
                rs.text.replace("```latex","").replace("```","").strip())



        # ── VERIFICA RIDOTTA BES/DSA ─────────────────────────────────────────────────
        if bes_dsa and perc_ridotta:
            _avanza(" ⛳ Generazione verifica ridotta…")

            prompt_ridotta = f"""Sei un docente esperto. Hai già generato questa verifica:

        {corpo_latex}

        Devi creare una versione RIDOTTA per studenti con sostegno o certificazione (BES/DSA/NAI).
        La struttura deve essere simile all'originale ma con circa il {perc_ridotta}% di sottopunti IN MENO rispetto al totale.
        Scegli quali sottopunti eliminare partendo dai più complessi, astratti o che richiedono più passaggi di calcolo.
        Mantieni sempre almeno 1 sottopunto per esercizio.
        Mantieni i sottopunti più semplici e diretti.
        {'Ridistribuisci i punti in modo che la somma sia ESATTAMENTE ' + str(punti_totali) + ' pt. totali. Ogni sottopunto mantenuto deve avere il suo (X pt).' if mostra_punteggi else 'NON inserire punteggi.'}
        NON aggiungere nessun simbolo (*), nessuna nota BES, nessuna indicazione che si tratta di una verifica ridotta.
        La verifica deve sembrare una verifica normale, semplicemente più breve.
        TERMINA con \\end{{document}}.
        SOLO CODICE LATEX del corpo (\\subsection* ecc.), senza preambolo."""

            rb_bes = model.generate_content(prompt_ridotta)
            corpo_latex_ridotta = rb_bes.text.replace("```latex", "").replace("```", "").strip()
            corpo_latex_ridotta = pulisci_corpo_latex(corpo_latex_ridotta)
                    
            latex_ridotta = preambolo_fisso + corpo_latex_ridotta
            latex_ridotta = fix_items_environment(latex_ridotta)
            latex_ridotta = rimuovi_vspace_corpo(latex_ridotta)
            if mostra_punteggi:
                latex_ridotta = rimuovi_punti_subsection(latex_ridotta)
                latex_ridotta = riscala_punti(latex_ridotta, punti_totali)   
                
            if con_griglia:
                latex_ridotta_final = inietta_griglia(latex_ridotta, punti_totali)
            else:
                latex_ridotta_final = latex_ridotta
        
            st.session_state.verifiche['R'] = {**_vf(), 'latex': latex_ridotta_final}
        
            pdf_r, err_r = compila_pdf(latex_ridotta_final)
            if pdf_r:
                st.session_state.verifiche['R']['pdf']    = pdf_r
                st.session_state.verifiche['R']['pdf_ts'] = time.time()
                st.session_state.verifiche['R']['preview'] = True
            else:
                if con_griglia:
                    pdf_r_fallback, _ = compila_pdf(latex_ridotta)
                    if pdf_r_fallback:
                        st.session_state.verifiche['R']['pdf']     = pdf_r_fallback
                        st.session_state.verifiche['R']['pdf_ts']  = time.time()
                        st.session_state.verifiche['R']['preview'] = True
                        st.warning("⚠️ La griglia non è stata inclusa nella verifica ridotta (errore compilazione).")


        



        
        
        if doppia_fila:
            _avanza("📄  Generazione Versione B…")
            rb = model.generate_content(
                f"Versione B: stessa struttura, cambia dati e quesiti. "
                f"SOLO corpo esercizi (\\subsection* ecc.), SENZA preambolo/\\documentclass/\\begin{{document}}. "
                f"Sostituisci 'Versione A' con 'Versione B'. TERMINA con \\end{{document}}. SOLO LATEX.\n\n{corpo_latex}")
            corpo_latex_b = rb.text.replace("```latex","").replace("```","").strip()
            corpo_latex_b = pulisci_corpo_latex(corpo_latex_b)
                
            preambolo_b = preambolo_fisso.replace(
                titolo_header,
                titolo_header.replace("Versione A","Versione B") if "Versione A" in titolo_header
                else titolo_header + " — Versione B"
            )
            latex_b = preambolo_b + corpo_latex_b
            latex_b = fix_items_environment(latex_b)
            latex_b = rimuovi_vspace_corpo(latex_b)
            if mostra_punteggi:
                latex_b = rimuovi_punti_subsection(latex_b)
                latex_b = riscala_punti(latex_b, punti_totali)
                
            if con_griglia:
                latex_b_final = inietta_griglia(latex_b, punti_totali)
            else:
                latex_b_final = latex_b

            st.session_state.verifiche['B'] = {**_vf(), 'latex': latex_b_final}

            _avanza("🖨️  PDF Versione B…")
            pdf_b_auto, _ = compila_pdf(latex_b_final)
            if pdf_b_auto:
                st.session_state.verifiche['B']['pdf']     = pdf_b_auto
                st.session_state.verifiche['B']['pdf_ts']  = time.time()
                st.session_state.verifiche['B']['preview'] = True
            else:
                if con_griglia:
                    pdf_b_fallback, _ = compila_pdf(latex_b)
                    if pdf_b_fallback:
                        st.session_state.verifiche['B']['pdf'] = pdf_b_fallback
                        st.session_state.verifiche['B']['pdf_ts'] = time.time()
                        st.session_state.verifiche['B']['preview'] = True

            if correzione_step:
                rsb = model.generate_content(
                    "Stessa struttura soluzioni (Rapide + Dettagliato). SOLO LATEX.\n\n" + latex_b)
                st.session_state.verifiche['B']['soluzioni_latex'] = (
                    rsb.text.replace("```latex","").replace("```","").strip())

        _prog.markdown(f"""
<div style="margin:0.6rem 0 1rem 0;">
  <div style="font-size:0.82rem;font-weight:600;color:{T['success']};
              font-family:'DM Sans',sans-serif;margin-bottom:6px;">✅  Verifica pronta!</div>
  <div style="background:{T['border']};border-radius:100px;height:8px;overflow:hidden;">
    <div style="background:{T['success']};width:100%;height:100%;border-radius:100px;"></div>
  </div>
</div>
""", unsafe_allow_html=True)
        time.sleep(0.7)
        _prog.empty()

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

    attive = ['A','B'] if _df and st.session_state.verifiche['B']['latex'] else ['A']
    if st.session_state.verifiche['R']['latex']:
        attive.append('R')

    for idx, fid in enumerate(attive):
        v = st.session_state.verifiche[fid]
        if idx > 0:
            st.divider()
        with st.container():
            if fid == 'R':
                label_ver = "Verifica Ridotta"
            elif _df:
                label_ver = f"Versione {fid}"
            else:
                label_ver = "La tua verifica"
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:0.75rem;">
              <span style="font-family:'DM Sans',sans-serif;font-size:1.1rem;
                           font-weight:700;color:{T['text']};">{APP_ICON} {label_ver}</span>
              <span class="chip">Pronta</span>
            </div>
            <div class="disclaimer">
              <span class="disclaimer-icon">⚠️</span>
              <span>Le verifiche generate sono <strong>suggerimenti</strong>. Rivedi sempre il contenuto prima della distribuzione — il docente è responsabile del materiale finale.</span>
            </div>
            """, unsafe_allow_html=True)

            # --- DOWNLOAD PDF ---
            if v['pdf']:
                pdf_size = _stima_dimensione(v['pdf'])
                st.download_button(
                    label=f"📄 Scarica PDF — Alta qualità ({pdf_size})",
                    data=v['pdf'],
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

            # --- DOWNLOAD WORD + AVVISO ---
            if v['docx']:
                docx_size = _stima_dimensione(v['docx'])
                st.download_button(
                    label=f"📝 Scarica File Word Modificabile ({docx_size})",
                    data=v['docx'],
                    file_name=f"Verifica_{_arg}_{fid}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                    key=f"dld_{fid}"
                )
                # AVVISO WORD
                st.markdown(f"""
                    <div class="hint-docx" style="margin-top: -10px; margin-bottom: 15px;">
                        💡 <b>Nota:</b> La versione Word è modificabile ma ha una resa grafica inferiore. 
                        I grafici complessi di funzione (TikZ/Plot) non compaiono in Word e vanno aggiunti a mano.
                    </div>
                """, unsafe_allow_html=True)
            else:
                _docx_gen_key = f"_docx_generating_{fid}"
                if st.button("📝 Genera File Word Modificabile", key=f"dldc_{fid}", use_container_width=True):
                    st.session_state[_docx_gen_key] = True
                if st.session_state.get(_docx_gen_key, False):
                    with st.spinner("⏳ Conversione Word…"):
                        db, de = latex_to_docx_via_ai(v['latex'], con_griglia=con_griglia)
                    if db:
                        st.session_state.verifiche[fid]['docx'] = db
                        st.session_state.verifiche[fid]['docx_ts'] = time.time()
                        st.session_state[_docx_gen_key] = False
                        st.rerun()
                    else:
                        st.session_state[_docx_gen_key] = False
                        st.error("Errore Word")
                        with st.expander("Log"): st.text(de)

            # --- SOLUZIONI ---
            if v['soluzioni_latex']:
                st.write("")
                if v['soluzioni_pdf']:
                    sol_size = _stima_dimensione(v['soluzioni_pdf'])
                    st.download_button(
                        label=f"✅ Scarica Soluzioni Step-by-Step ({sol_size})",
                        data=v['soluzioni_pdf'],
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

            # --- PREVIEW ---
            if v['preview'] and v['pdf']:
                with st.expander("👁 Anteprima PDF", expanded=False):
                    b64 = base64.b64encode(v['pdf']).decode()
                    st.markdown(f"""
                    <iframe src="data:application/pdf;base64,{b64}#toolbar=0&navpanes=0&scrollbar=1"
                            style="width:100%;height:500px;border:none;border-radius:8px;display:block;"></iframe>
                    """, unsafe_allow_html=True)

            # --- SORGENTE TEX ---
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
                
# ── FOOTER ───────────────────────────────────────────────────────────────────────
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
    background: none;
    border: none;
    cursor: pointer;
    color: {T['accent']};
    font-weight: 600;
    font-size: 0.72rem;
    font-family: 'DM Sans', sans-serif;
    padding: 0;
    display: block;
    margin: 0 auto;
    text-align: center;
    width: 100%;
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
  ta.focus();
  ta.select();
  var ok = false;
  try {{ ok = document.execCommand("copy"); }} catch(e) {{}}
  document.body.removeChild(ta);
  if (ok) {{
    btn.innerText = "✅ Link copiato!";
    setTimeout(function() {{ btn.innerText = "🔗 Condividi con i colleghi"; }}, 2000);
  }} else {{
    btn.innerText = url;
  }}
}}
</script>
""", height=30)




























