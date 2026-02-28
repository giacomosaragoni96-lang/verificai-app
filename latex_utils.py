# ── latex_utils.py ─────────────────────────────────────────────────────────────
# Funzioni pure per parsing, manipolazione e compilazione LaTeX/PDF.
# Nessuna dipendenza da Streamlit — importabili e testabili in isolamento.
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
    TUTTI gli esercizi appaiono nella griglia, anche senza punti espliciti.
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
            # Esercizio con sottopunti e punteggi espliciti
            esercizi.append({'num': num_label, 'items': items_found})
        else:
            # Cerca punteggio globale nell'intero blocco
            pt_global = re.search(
                r'[\(\[]?\s*(\d+(?:[.,]\d+)?)\s*(?:pt|punt[io]|p\.?)\s*[\)\]]?',
                block, re.IGNORECASE
            )
            if pt_global:
                # Ha un punteggio globale ma nessun sottopunto
                esercizi.append({'num': num_label, 'items': [('', pt_global.group(1))]})
            else:
                # Nessun punteggio trovato — lo includiamo comunque con '—'
                esercizi.append({'num': num_label, 'items': [('', '—')]})

    return esercizi


def build_griglia_latex(esercizi: list, punti_totali: int) -> str:
    """
    Genera il codice LaTeX della griglia di valutazione a partire
    dalla lista restituita da parse_esercizi().
    Tutti gli esercizi appaiono, quelli senza punti mostrano '—'.
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
        "% GRIGLIA\n\\begin{center}\n\\textbf{Griglia Punteggi}\\\\[0.3cm]\n"
        "{\\renewcommand{\\arraystretch}{1.8}\n"
        f"\\adjustbox{{max width=\\textwidth}}{{\n"
        f"\\begin{{tabular}}{{{col_spec}}}\n\\hline\n"
        f"{row_es}\n{row_sotto}\n{row_max}\n{row_punti}\n"
        f"\\end{{tabular}}\n}}}}\n\\end{{center}}"
    )


# ── FIX E PULIZIA LATEX ────────────────────────────────────────────────────────

def fix_items_environment(latex: str) -> str:
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
    r"""
    Rimuove annotazioni (N pt) dai titoli \subsection*.
    Gestisce tre casi:
      1. DENTRO le graffe: \subsection*{Titolo (18 pt)}   <- causa dimezzamento
      2. DOPO le graffe stessa riga: \subsection*{Titolo} (18 pt)
      3. Riga successiva
    """
    # Caso 1 — dentro le graffe (il piu' comune dopo riscala_punti globale)
    latex = re.sub(
        r'(\\subsection\*\{[^}]*?)\s*\(\d+(?:[.,]\d+)?\s*pt\)(\s*\})',
        r'\1\2', latex
    )
    # Caso 2 — dopo le graffe, stessa riga
    latex = re.sub(
        r'(\\subsection\*\{[^}]*\}[^\n]*?)\s*\(\d+(?:[.,]\d+)?\s*pt\)([^\n]*)',
        r'\1\2', latex
    )
    # Caso 3 — riga successiva
    latex = re.sub(
        r'(\\subsection\*\{[^}]*\})\s*\n\s*\(\d+(?:[.,]\d+)?\s*pt\)\s*\n',
        r'\1\n', latex
    )
    return latex


def riscala_punti(latex: str, punti_totali_target: int) -> str:
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


def riscala_punti_custom(latex: str, pts_per_esercizio: list) -> str:
    r"""
    Assegna punti custom per esercizio distribuendo proporzionalmente tra gli item.
    pts_per_esercizio: lista di int, uno per ogni subsection*.

    Bug-fix critico: la ricerca (N pt) avviene SOLO nel corpo (dopo la prima
    riga header), escludendo il titolo \subsection*{...} che puo' contenere
    un (N pt) aggiunto da riscala_punti globale. Senza questo fix la somma
    trovata era doppia -> fattore 0.5 -> tutti i valori dimezzati.
    """
    pts_per_esercizio = [int(p) for p in pts_per_esercizio]

    parts = re.split(r'(?=\\subsection\*\{)', latex)
    if len(parts) <= 1:
        return latex

    preamble = parts[0]
    blocks   = parts[1:]
    result   = []

    for i, block in enumerate(blocks):
        if i >= len(pts_per_esercizio):
            result.append(block)
            continue
        target = pts_per_esercizio[i]

        # Separa header (prima riga) dal corpo
        hm          = re.match(r'[^\n]*\n', block)
        header_end  = hm.end() if hm else 0
        header_text = block[:header_end]
        body_text   = block[header_end:]

        pattern = re.compile(r'\((\d+(?:[.,]\d+)?)\s*pt\)')
        matches = list(pattern.finditer(body_text))
        if not matches:
            result.append(block)
            continue
        valori = [float(m.group(1).replace(',', '.')) for m in matches]
        somma  = sum(valori)
        if somma == 0:
            result.append(block)
            continue

        nuovi     = [v / somma * target for v in valori]
        nuovi_int = [int(v) for v in nuovi]
        resto     = target - sum(nuovi_int)

        frazioni = sorted(
            range(len(nuovi)), key=lambda k: nuovi[k] - nuovi_int[k],
            reverse=(resto > 0)
        )
        for k in range(abs(int(round(resto)))):
            nuovi_int[frazioni[k % len(frazioni)]] += (1 if resto > 0 else -1)
        nuovi_int = [max(0, v) for v in nuovi_int]

        new_body = body_text
        offset   = 0
        for j, m in enumerate(matches):
            vecchio  = m.group(0)
            nuovo    = f"({nuovi_int[j]} pt)"
            s = m.start() + offset
            e = m.end()   + offset
            new_body = new_body[:s] + nuovo + new_body[e:]
            offset  += len(nuovo) - len(vecchio)

        result.append(header_text + new_body)

    return preamble + ''.join(result)


def inietta_griglia(latex: str, punti_totali: int) -> str:
    # Rimuovi griglia preesistente
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

    # Controlla se il totale reale (escludendo '—') differisce dal target
    try:
        tot_reale = sum(
            float(pts.replace(',', '.'))
            for ex in esercizi for _, pts in ex['items']
            if pts != '—'
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
