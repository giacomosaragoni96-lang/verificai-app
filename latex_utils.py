# ── latex_utils.py ─────────────────────────────────────────────────────────────
# Funzioni pure per parsing, manipolazione e compilazione LaTeX/PDF.
# Nessuna dipendenza da Streamlit — importabili e testabili in isolamento.
#
# Import in app.py:
#   from latex_utils import (
#       compila_pdf, inietta_griglia, riscala_punti,
#       fix_items_environment, rimuovi_vspace_corpo, pulisci_corpo_latex,
#       rimuovi_punti_subsection, parse_esercizi, build_griglia_latex,
#       pdf_to_images_bytes,
#   )
# ───────────────────────────────────────────────────────────────────────────────

import os
import re
import io
import subprocess
import tempfile


# ── PARSING ESERCIZI ───────────────────────────────────────────────────────────

def parse_esercizi(latex: str) -> list:
    """
    Analizza il LaTeX e restituisce una lista di esercizi con i loro punteggi.
    Ogni elemento: {'num': str, 'items': [(label, punti), ...]}
    """
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
            item_label_match = re.search(r'\\item\[([^\]]+)\]', line)
            item_plain_match = re.search(r'\\item(?!\[)', line)

            if not item_label_match and not item_plain_match:
                continue

            if item_label_match:
                raw_label = item_label_match.group(1).replace('*', '').strip()
            else:
                raw_label = lettere[lettera_idx % 26] + ")"
                lettera_idx += 1

            window_lines = []
            for lj in range(li, min(li + 15, len(lines))):
                if lj > li and re.search(r'\\item(?:\[|(?!\w))', lines[lj]):
                    break
                window_lines.append(lines[lj])
            search_window = '\n'.join(window_lines)
            search_window = re.sub(
                r'\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}', '',
                search_window, flags=re.DOTALL
            )

            pt_match = re.search(
                r'[\(\[]?\s*(\d+(?:[.,]\d+)?)\s*(?:pt|punt[io]|p\.?)\s*[\)\]]?',
                search_window, re.IGNORECASE
            )
            if not pt_match:
                continue

            items_found.append((raw_label, pt_match.group(1)))

        if items_found:
            esercizi.append({'num': num_label, 'items': items_found})
        else:
            pt_global = re.search(
                r'[\(\[]?\s*(\d+(?:[.,]\d+)?)\s*(?:pt|punt[io]|p\.?)\s*[\)\]]?',
                block, re.IGNORECASE
            )
            if pt_global:
                esercizi.append({'num': num_label, 'items': [('', pt_global.group(1))]})

    return esercizi


def build_griglia_latex(esercizi: list, punti_totali: int) -> str:
    """
    Genera il codice LaTeX della griglia di valutazione a partire
    dalla lista restituita da parse_esercizi().
    """
    if not esercizi:
        return ""

    col_spec = "|l|" + "".join("c|" * len(ex['items']) for ex in esercizi) + "c|"

    row_es = "\\textbf{Es.}" + "".join(
        f" & \\multicolumn{{{len(ex['items'])}}}{{c||}}{{\\textbf{{{ex['num']}}}}}"
        for ex in esercizi
    ) + " & \\textbf{Tot} \\\\ \\hline"

    row_sotto = "\\textbf{Sotto.}" + "".join(
        f" & {label if label else '—'}"
        for ex in esercizi for label, _ in ex['items']
    ) + " & \\\\ \\hline"

    row_max = "\\textbf{Max}" + "".join(
        f" & {pts}" for ex in esercizi for _, pts in ex['items']
    ) + f" & {punti_totali} \\\\ \\hline"

    total_cols = sum(len(ex['items']) for ex in esercizi) + 1
    row_punti = "\\textbf{Punti}" + " &" * total_cols + " \\\\ \\hline"

    return (
        "% GRIGLIA\n\\begin{center}\n\\textbf{Griglia di Valutazione}\\\\[0.3cm]\n"
        "{\\renewcommand{\\arraystretch}{1.8}\n"
        f"\\adjustbox{{max width=\\textwidth}}{{\n"
        f"\\begin{{tabular}}{{{col_spec}}}\n\\hline\n"
        f"{row_es}\n{row_sotto}\n{row_max}\n{row_punti}\n"
        f"\\end{{tabular}}\n}}}}\n\\end{{center}}"
    )


# ── FIX E PULIZIA LATEX ────────────────────────────────────────────────────────

def fix_items_environment(latex: str) -> str:
    """
    Avvolge \item[...] orfani (fuori da enumerate/itemize)
    in un ambiente enumerate[a)] per evitare errori LaTeX.
    """
    lines = latex.split('\n')
    result = []
    list_depth = 0
    in_bare_block = False

    for line in lines:
        stripped = line.strip()
        list_opens  = len(re.findall(r'\\begin\{(?:enumerate|itemize)', line))
        list_closes = len(re.findall(r'\\end\{(?:enumerate|itemize)', line))
        is_bare_item = bool(re.match(r'\\item\[', stripped)) and list_depth == 0

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


def rimuovi_vspace_corpo(latex: str) -> str:
    """
    Rimuove i comandi di spaziatura verticale/orizzontale dal corpo
    degli esercizi (dopo il primo \subsection*), lasciando intatto il preambolo.
    """
    idx = latex.find('\\subsection*')
    if idx == -1:
        return latex

    preambolo = latex[:idx]
    corpo = latex[idx:]
    corpo = re.sub(r'\\vspace\*?\{[^}]*\}', '', corpo)
    corpo = re.sub(r'\\hspace\*?\{[^}]*\}', '', corpo)
    corpo = re.sub(r'\\(?:big|med|small)skip\b', '', corpo)
    corpo = re.sub(r'\n{3,}', '\n\n', corpo)

    return preambolo + corpo


def pulisci_corpo_latex(testo: str) -> str:
    """
    Rimuove preambolo, \documentclass, \begin{document} e intestazioni
    dal testo restituito dall'AI, mantenendo solo il corpo degli esercizi.
    Aggiunge sempre \end{document} in fondo.
    """
    idx = testo.find('\\subsection*')
    if idx == -1:
        testo = re.sub(r'^.*?\\begin\{document\}[^\n]*\n?', '', testo, flags=re.DOTALL)
        while re.match(r'^\s*\\begin\{center\}', testo):
            testo = re.sub(
                r'^\s*\\begin\{center\}.*?\\end\{center\}\s*', '',
                testo, flags=re.DOTALL
            )
    else:
        testo = testo[idx:]

    testo = re.sub(r'\\end\{document\}.*$', '', testo, flags=re.DOTALL).rstrip()
    testo += "\n\\end{document}"
    return testo


def rimuovi_punti_subsection(latex: str) -> str:
    """
    Rimuove i punteggi "(X pt)" dai titoli \subsection* (dove non devono stare).
    I punteggi rimangono solo dentro i \item.
    """
    latex = re.sub(
        r'(\\subsection\*\{[^}]*\}[^\n]*)\s*\((\d+(?:[.,]\d+)?)\s*pt\)',
        r'\1',
        latex
    )
    latex = re.sub(
        r'(\\subsection\*\{[^}]*\})\s*\n\s*\(\d+(?:[.,]\d+)?\s*pt\)\s*\n',
        r'\1\n',
        latex
    )
    return latex


def riscala_punti(latex: str, punti_totali_target: int) -> str:
    """
    Riscala tutti i "(X pt)" nel LaTeX in modo che la loro somma
    sia esattamente punti_totali_target, usando arrotondamento intelligente
    (distribuzione del resto per eccesso ai sottopunti con resto maggiore).
    """
    pattern = re.compile(r'\((\d+(?:[.,]\d+)?)\s*pt\)')
    matches = list(pattern.finditer(latex))
    if not matches:
        return latex

    valori = [float(m.group(1).replace(',', '.')) for m in matches]
    somma_attuale = sum(valori)
    if somma_attuale == 0:
        return latex

    fattore      = punti_totali_target / somma_attuale
    nuovi_valori = [v * fattore for v in valori]
    nuovi_interi = [int(v) for v in nuovi_valori]
    resti        = [(nuovi_valori[i] - nuovi_interi[i], i) for i in range(len(nuovi_valori))]
    differenza   = punti_totali_target - sum(nuovi_interi)
    resti.sort(reverse=True)

    for i in range(int(round(differenza))):
        nuovi_interi[resti[i][1]] += 1

    risultato = latex
    offset = 0
    for i, m in enumerate(matches):
        vecchio = m.group(0)
        nuovo   = f"({nuovi_interi[i]} pt)"
        start   = m.start() + offset
        end     = m.end() + offset
        risultato = risultato[:start] + nuovo + risultato[end:]
        offset   += len(nuovo) - len(vecchio)

    return risultato


def inietta_griglia(latex: str, punti_totali: int) -> str:
    """
    Rimuove eventuali griglie preesistenti e inietta una griglia di valutazione
    aggiornata prima di \end{document}.
    """
    # Rimuovi griglia preesistente (generata dall'AI o da una run precedente)
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

    # Controlla se il totale reale differisce dal target e aggiusta
    try:
        tot_reale = sum(
            float(pts.replace(',', '.'))
            for ex in esercizi for _, pts in ex['items']
        )
        if abs(tot_reale - punti_totali) > 0.5:
            griglia = build_griglia_latex(
                esercizi,
                int(tot_reale) if tot_reale == int(tot_reale) else round(tot_reale, 1)
            )
    except Exception:
        pass

    if "\\end{document}" in latex:
        return latex.replace(
            "\\end{document}",
            f"\n\\vfill\n{griglia}\n\\end{{document}}"
        )
    return latex + f"\n\\vfill\n{griglia}\n\\end{{document}}"


# ── COMPILAZIONE PDF ───────────────────────────────────────────────────────────

def compila_pdf(codice_latex: str) -> tuple[bytes | None, str | None]:
    """
    Compila il codice LaTeX con pdflatex e restituisce (pdf_bytes, None)
    in caso di successo, oppure (None, log_errore) in caso di fallimento.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tex_path = os.path.join(tmpdir, "v.tex")
        pdf_path = os.path.join(tmpdir, "v.pdf")

        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(codice_latex)

        result = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "-output-directory", tmpdir, tex_path],
            capture_output=True
        )

        if os.path.exists(pdf_path):
            return open(pdf_path, "rb").read(), None

        return None, result.stdout.decode()


def pdf_to_images_bytes(pdf_bytes: bytes) -> tuple[list | None, str | None]:
    """
    Converte un PDF in una lista di immagini PNG (una per pagina).
    Prova prima con pdf2image, poi con pdftoppm come fallback.
    Restituisce (lista_bytes_png, None) o (None, messaggio_errore).
    """
    # Tentativo 1: pdf2image
    try:
        from pdf2image import convert_from_bytes as cfb
        pages = cfb(pdf_bytes, dpi=150)
        out = []
        for p in pages:
            buf = io.BytesIO()
            p.save(buf, "PNG")
            out.append(buf.getvalue())
        return out, None
    except Exception:
        pass

    # Tentativo 2: pdftoppm (CLI)
    try:
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "in.pdf")
            with open(src, "wb") as f:
                f.write(pdf_bytes)
            subprocess.run(
                ["pdftoppm", "-png", "-r", "150", src, os.path.join(d, "p")],
                capture_output=True, check=True
            )
            imgs = sorted(
                fn for fn in os.listdir(d)
                if fn.startswith("p") and fn.endswith(".png")
            )
            if imgs:
                return [open(os.path.join(d, fn), "rb").read() for fn in imgs], None
    except Exception as e:
        return None, str(e)

    return None, "pdf2image non installato e pdftoppm non trovato."
