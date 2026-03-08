# ── latex_utils.py ─────────────────────────────────────────────────────────────
# Funzioni pure per parsing, manipolazione e compilazione LaTeX/PDF.
# Nessuna dipendenza da Streamlit — importabili e testabili in isolamento.
# ───────────────────────────────────────────────────────────────────────────────

import logging
import os
import re
import io
import subprocess
import tempfile

logger = logging.getLogger("verificai.latex_utils")

# Pattern canonico per (N pt) — robusto a spazi extra dell'AI
_PT_PATTERN = re.compile(r'\(\s*(\d+(?:[.,]\d+)?)\s*pt\s*\)', re.IGNORECASE)


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
            # Esclude falsi positivi come F(2, 1) cercando solo valori seguiti da 'pt'
            pt_global = re.search(
                r'[\(\[]?\s*(\d+(?:[.,]\d+)?)\s*pt\b\s*[\)\]]?',
                block, re.IGNORECASE
            )
            if pt_global:
                # Punteggio globale: label='' (stringa vuota) per distinguerlo
                # dal segnaposto '—'. build_griglia_latex mostra '—' per label falsy.
                # Il widget ricalibra include questi item perché '' != '—'.
                esercizi.append({'num': num_label, 'items': [('', pt_global.group(1))]})
            else:
                # Nessun punteggio trovato — segnaposto; verrà distribuito da riscala_punti
                esercizi.append({'num': num_label, 'items': [('—', '—')]})

    return esercizi


# ── BLOCK EXTRACTION & RECONSTRUCTION (usato da main e sidebar) ───────────────

def extract_blocks(latex: str) -> tuple:
    """Estrae preambolo e lista di blocchi {title, body} da LaTeX (split su \\subsection*)."""
    parts = re.split(r"(?=\\subsection\*\{)", latex)
    if len(parts) <= 1:
        return latex, []
    preamble = parts[0]
    blocks = []
    for raw in parts[1:]:
        m = re.match(r"\\subsection\*\{([^}]*)\}(.*)", raw, re.DOTALL)
        if m:
            body = m.group(2)
            body = re.sub(r"\s*\\end\{document\}\s*$", "", body)
            body = re.sub(r"\s*\\vfill.*$", "", body, flags=re.DOTALL)
            body = re.sub(r"\s*%\s*GRIGLIA.*$", "", body, flags=re.DOTALL)
            body = body.rstrip()
            blocks.append({"title": m.group(1), "body": body})
    return preamble, blocks


def reconstruct_latex(preamble: str, blocks: list) -> str:
    """Ricostruisce LaTeX da preambolo e lista di blocchi."""
    r = preamble
    for b in blocks:
        r += f"\\subsection*{{{b['title']}}}\n{b['body']}\n\n"
    if "\\end{document}" not in r:
        r += "\n\\end{document}"
    return r


def extract_corpo(latex: str) -> str:
    """Estrae solo il corpo esercizi (dopo \\end{center}) dal LaTeX completo."""
    m = re.search(r"\\end\{center\}(.*?)(?=\\end\{document\})", latex, re.DOTALL)
    return m.group(1).strip() if m else ""


def extract_preambolo(latex: str) -> str:
    """Estrae il preambolo fino a \\end{center} incluso."""
    m = re.search(r"^(.*?\\end\{center\})", latex, re.DOTALL)
    return m.group(1) + "\n" if m else ""


# ── SCORE PARSING PER BLOCCO (UI Ricalibra Punteggi) ───────────────────────────

def parse_pts_from_block_body(body: str) -> int:
    """Somma tutti i (N pt) nel corpo del blocco."""
    # Pattern più completo per catturare anche decimali e virgole
    pt_pattern = re.compile(r'\((\d+(?:[.,]\d+)?)\s*pt\)', re.IGNORECASE)
    points = pt_pattern.findall(body)
    total = sum(int(float(p.replace(',', '.'))) for p in points)
    return total


def conta_punti_latex(latex: str) -> int:
    """
    Conta la somma di tutti i marcatori (N pt) nel LaTeX.
    Usa lo stesso pattern di riscala_punti — il valore restituito riflette
    esattamente ciò che l'utente vedrà nel documento.
    """
    valori = [float(v.replace(',', '.')) for v in _PT_PATTERN.findall(latex)]
    return int(round(sum(valori)))


def valida_totale(pts_list: list, target: int) -> tuple:
    """Ricalcola somma da zero, forza int. Restituisce (somma, ok, diff)."""
    somma = sum(int(p) for p in pts_list)
    return somma, (somma == target), (somma - target)


def riscala_single_block(title: str, body: str, target_pts: int) -> str:
    """Applica riscala_punti_custom su un singolo blocco, portando la somma a target_pts."""
    if target_pts <= 0:
        return body
    mini = f"\\subsection*{{{title}}}\n{body}"
    fixed = riscala_punti_custom(mini, [target_pts])
    m = re.match(r'[^\n]*\n(.*)', fixed, re.DOTALL)
    return m.group(1) if m else body


def parse_items_from_block(body: str, title: str = "") -> list:
    """
    Parse sottopunti da corpo LaTeX (e opz. titolo).
    Restituisce list di (label, short_text, pts) per il widget Ricalibra Punteggi.
    """
    auto_labels = list('abcdefghijklmnopqrstuvwxyz')
    items = []

    # Prima prova: item con label esplicito [a)], [b)], ecc.
    labeled = list(re.finditer(r'\\item\[([^\]]+)\]([^{]*?)(?=\\item|\Z)', body, re.DOTALL))
    if labeled:
        for m in labeled:
            label = m.group(1).strip()
            text = m.group(2).strip()
            pts_m = re.search(r'\((\d+(?:[.,]\d+)?)\s*pt\)', text)
            pts = int(float(pts_m.group(1).replace(',', '.'))) if pts_m else 0
            clean = re.sub(r'\(\d+(?:[.,]\d+?)?\s*pt\)', '', text).strip()
            clean = re.sub(r'\s+', ' ', clean)
            clean = re.sub(r'\\[a-zA-Z]+\{[^}]*\}', '', clean)
            clean = re.sub(r'\$[^$]*\$', '[formula]', clean)
            short = (clean[:42] + '\u2026') if len(clean) > 42 else clean
            items.append((label, short, pts))
        return items

    # Seconda prova: item senza label, auto-generati a), b), c)
    # Cerca \item seguito da testo fino al prossimo \item o fine del blocco
    auto_items = list(re.finditer(r'\\item\s+([^{]*?)(?=\\item|\Z)', body, re.DOTALL))
    if auto_items:
        auto_idx = 0
        for m in auto_items:
            text = m.group(1).strip()
            if not text:  # Salta item vuoti
                continue
            pts_m = re.search(r'\((\d+(?:[.,]\d+)?)\s*pt\)', text)
            pts = int(float(pts_m.group(1).replace(',', '.'))) if pts_m else 0
            clean = re.sub(r'\(\d+(?:[.,]\d+?)?\s*pt\)', '', text).strip()
            clean = re.sub(r'\s+', ' ', clean)
            clean = re.sub(r'\\[a-zA-Z]+\{[^}]*\}', '', clean)
            clean = re.sub(r'\$[^$]*\$', '[formula]', clean)
            short = (clean[:42] + '\u2026') if len(clean) > 42 else clean
            label = auto_labels[auto_idx] + ')' if auto_idx < len(auto_labels) else f'{auto_idx+1})'
            items.append((label, short, pts))
            auto_idx += 1

        if items:
            return items

    # Terza prova: fallback - cerca qualsiasi \item
    fallback_items = list(re.finditer(r'\\item[^\n]*', body))
    if fallback_items:
        auto_idx = 0
        for m in fallback_items:
            text = m.group(0).replace('\\item', '').strip()
            if not text:  # Salta item vuoti
                continue
            pts_m = re.search(r'\((\d+(?:[.,]\d+)?)\s*pt\)', text)
            pts = int(float(pts_m.group(1).replace(',', '.'))) if pts_m else 0
            clean = re.sub(r'\(\d+(?:[.,]\d+?)?\s*pt\)', '', text).strip()
            clean = re.sub(r'\s+', ' ', clean)
            clean = re.sub(r'\\[a-zA-Z]+\{[^}]*\}', '', clean)
            clean = re.sub(r'\$[^$]*\$', '[formula]', clean)
            short = (clean[:42] + '\u2026') if len(clean) > 42 else clean
            label = auto_labels[auto_idx] + ')' if auto_idx < len(auto_labels) else f'{auto_idx+1})'
            items.append((label, short, pts))
            auto_idx += 1

    if items:
        return items

    # Ultimo fallback: controlla il titolo
    if title:
        pt_title = re.search(r'\((\d+(?:[.,]\d+)?)\s*pt\)', title)
        if pt_title:
            pts = int(float(pt_title.group(1).replace(',', '.')))
            clean_title = re.sub(r'\s*\(\d+(?:[.,]\d+?)?\s*pt\)', '', title).strip()
            clean_title = re.sub(r'\s+', ' ', clean_title)
            short = (clean_title[:42] + '\u2026') if len(clean_title) > 42 else clean_title
            items.append(("—", short, pts))
            return items

    pt_in_body = re.findall(r'\((\d+)\s*pt\)', body)
    if pt_in_body:
        total = sum(int(p) for p in pt_in_body)
        short = (body.strip()[:42] + '\u2026') if len(body.strip()) > 42 else body.strip()
        short = re.sub(r'\s+', ' ', re.sub(r'\\[a-zA-Z]+\{[^}]*\}', '', short))
        short = re.sub(r'\$[^$]*\$', '[formula]', short)
        items.append(("—", short or "Esercizio", total))
        return items

    return items


def apply_item_pts_to_body(body: str, new_pts_list: list) -> str:
    """Sostituisce (X pt) su ogni \\item (o unico (N pt) nel body) con i valori da new_pts_list."""
    if not new_pts_list:
        return body
    count = [0]

    def replacer(m):
        line = m.group(0)
        i = count[0]
        count[0] += 1
        if i < len(new_pts_list):
            line = re.sub(r'\s*\(\d+\s*pt\)', '', line).rstrip()
            line += f' ({new_pts_list[i]} pt)'
        return line

    if re.search(r'\\item\[', body):
        return re.sub(r'\\item\[[^\]]*\][^\n]*', replacer, body)
    if re.search(r'\\item\s+', body):
        return re.sub(r'\\item\s+[^\n]+', replacer, body)
    if len(new_pts_list) == 1:
        return re.sub(r'\(\d+\s*pt\)', f'({new_pts_list[0]} pt)', body, count=1)
    return body


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
        "% GRIGLIA\n\\begin{center}\n\\textbf{Tabella Punteggi}\\\\[0.3cm]\n"
        "{\\renewcommand{\\arraystretch}{1.8}\n"
        f"\\adjustbox{{max width=\\textwidth}}{{\n"
        f"\\begin{{tabular}}{{{col_spec}}}\n\\hline\n"
        f"{row_es}\n{row_sotto}\n{row_max}\n{row_punti}\n"
        f"\\end{{tabular}}\n}}}}\n\\end{{center}}"
    )


# ── FIX E PULIZIA LATEX ────────────────────────────────────────────────────────

def wrappa_esercizi_senza_item(latex: str) -> str:
    r"""
    Post-processing deterministico: converte esercizi senza \item in \item[a)].

    Mantenuta per compatibilità. Il pipeline principale usa
    prepara_esercizi_aperti() che è più robusta.
    """
    parts = re.split(r'(\\subsection\*\{[^}]*\})', latex)
    if len(parts) <= 1:
        return latex

    result = [parts[0]]

    for i in range(1, len(parts), 2):
        header = parts[i]
        body   = parts[i+1] if i+1 < len(parts) else ''

        # Se il corpo ha già almeno un \item → non toccare
        if re.search(r'\\item', body):
            result.append(header + body)
            continue

        # Estrai testo utile del corpo
        body_clean = re.sub(r'\\end\{document\}.*$', '', body, flags=re.DOTALL)
        body_clean = re.sub(r'\\vfill.*$', '', body_clean, flags=re.DOTALL)
        body_clean = body_clean.strip()

        if not body_clean:
            result.append(header + body)
            continue

        # Recupera pts dal testo se presenti, altrimenti placeholder 10
        # (riscala_punti li riscalerà proporzionalmente con gli altri \item)
        pts_match = re.search(r'\((\d+)\s*pt\)', body_clean)
        pts_val   = int(pts_match.group(1)) if pts_match else 10
        body_no_pts = re.sub(r'\s*\(\d+\s*pt\)', '', body_clean).rstrip().lstrip('\n')

        new_body = (
            f'\n\\begin{{enumerate}}[a)]\n'
            f'\\item[a)] {body_no_pts} ({pts_val} pt)\n'
            f'\\end{{enumerate}}\n'
        )
        end_doc = '\n\\end{document}' if '\\end{document}' in body else ''
        result.append(header + new_body + end_doc)

    return ''.join(result)


def prepara_esercizi_aperti(latex: str, punti_totali: int) -> str:
    r"""
    Pre-processing obbligatorio da chiamare PRIMA di riscala_punti().

    Problema: gli esercizi senza \item (domanda aperta, esercizio singolo)
    non hanno marcatori (N pt) → riscala_punti li ignora → la griglia mostra '—'
    e il totale risultante è sbagliato.

    Soluzione: per ogni blocco \subsection* senza \item E senza (N pt):
      1. Calcola un placeholder proporzionale (punti_totali / n_esercizi_totali)
      2. Wrappa il corpo in \begin{enumerate}[a)] \item[a)] corpo (N pt) \end{enumerate}

    Dopo questo step, riscala_punti() trova TUTTI i (N pt) e riscala correttamente
    l'intero documento a punti_totali — esercizi con e senza sotto-punti inclusi.
    """
    # Splittiamo per header mantenendo i separatori
    parts = re.split(r'(\\subsection\*\{[^}]*\})', latex)
    if len(parts) <= 1:
        return latex

    n_total_ex = (len(parts) - 1) // 2
    if n_total_ex == 0:
        return latex

    # Placeholder proporzionale — riscala_punti lo riscalerà al valore esatto
    pts_placeholder = max(1, round(punti_totali / n_total_ex))

    result = [parts[0]]
    for i in range(1, len(parts), 2):
        header = parts[i]
        body   = parts[i + 1] if i + 1 < len(parts) else ''

        # Ha già almeno un \item → ha già (N pt) → non toccare
        if re.search(r'\\item', body):
            result.append(header + body)
            continue

        # Ha già (N pt) nel corpo senza \item → ha pts espliciti → non toccare
        if re.search(r'\(\d+\s*pt\)', body):
            result.append(header + body)
            continue

        # ── Nessun \item e nessun (N pt) → aggiungi solo tag pt, NO enumerate ──
        body_clean = re.sub(r'\\end\{document\}.*$', '', body, flags=re.DOTALL)
        body_clean = re.sub(r'\\vfill.*$',           '', body_clean, flags=re.DOTALL)
        body_clean = body_clean.strip()

        if not body_clean:
            result.append(header + body)
            continue

        end_doc = '\n\\end{document}' if '\\end{document}' in body else ''
        result.append(header + f'\n{body_clean} ({pts_placeholder} pt)\n' + end_doc)

    return ''.join(result)


def fix_items_environment(latex: str) -> str:
    """
    Assicura che ogni \\item[...] nudo (fuori da un ambiente enumerate/itemize)
    venga avvolto in \\begin{enumerate}[a)] ... \\end{enumerate}.
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


def converti_header_esercizi(latex):
    """
    Converte \\subsection*{Esercizio N: Titolo} in \\noindent\\textbf{Esercizio N:}
    per la compilazione PDF. Chiamare solo al momento della compilazione.
    """
    parts = re.split(r'(\\subsection\*\{[^}]*\})', latex)
    if len(parts) <= 1:
        return latex
    result = [parts[0]]
    for idx, i in enumerate(range(1, len(parts), 2)):
        header = parts[i]
        body = parts[i + 1] if i + 1 < len(parts) else ''
        num_match = re.search(r'\b(\d+)\b', header)
        n = num_match.group(1) if num_match else str(idx + 1)
        spacer = '\\vspace{0.6cm}\n' if idx > 0 else ''
        result.append(spacer + '\\noindent\\textbf{Esercizio ' + n + ':}' + body)
    return ''.join(result)


def normalizza_labels_numerici(latex):
    """
    Converte etichette \\item[1)] \\item[2)] in \\item[a)] \\item[b)] ecc.
    """
    _map = {str(i): chr(ord('a') + i - 1) for i in range(1, 27)}
    def _sub(m):
        lettera = _map.get(m.group(1))
        return '\\item[' + lettera + ')]' if lettera else m.group(0)
    return re.sub(r'\\item\[(\d+)\)\]', _sub, latex)


def semplifica_item_singoli(latex):
    """
    Se un \\begin{enumerate} contiene esattamente un solo \\item,
    rimuove l'ambiente e scrive il testo direttamente.
    """
    def _collapse(m):
        inner = m.group(1)
        if len(re.findall(r'\\item\[', inner)) != 1:
            return m.group(0)
        item_text = re.sub(r'^\s*\\item\[[^\]]*\]\s*', '', inner.strip())
        return '\n' + item_text + '\n'
    return re.sub(
        r'\\begin\{enumerate\}(?:\[[^\]]*\])?\n(.*?)\\end\{enumerate\}',
        _collapse, latex, flags=re.DOTALL
    )


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
    """
    Riscala proporzionalmente tutti i marcatori (N pt) in modo che la loro
    somma sia ESATTAMENTE punti_totali_target.

    Algoritmo:
    1. Trova tutti i (N pt) con regex robusta (spazi opzionali).
    2. Calcola il fattore di scala.
    3. Applica floor a ogni valore scalato.
    4. Distribuisce il "resto" agli item con la frazione più alta.
    5. Garanzia finale: se per qualsiasi motivo la somma != target,
       aggiusta l'item con valore massimo (mai lasciare totale errato).
    """
    matches = list(_PT_PATTERN.finditer(latex))
    if not matches:
        logger.warning(
            "riscala_punti: nessun marcatore (N pt) trovato — LaTeX invariato. "
            "Verificare che prepara_esercizi_aperti sia stato chiamato prima."
        )
        return latex

    valori = [float(m.group(1).replace(',', '.')) for m in matches]
    somma_attuale = sum(valori)
    if somma_attuale == 0:
        logger.warning("riscala_punti: somma attuale è 0, skip.")
        return latex

    fattore      = punti_totali_target / somma_attuale
    nuovi_valori = [v * fattore for v in valori]
    nuovi_interi = [int(v) for v in nuovi_valori]          # floor per positivi
    resti        = [(nuovi_valori[i] - nuovi_interi[i], i) for i in range(len(nuovi_valori))]
    differenza   = punti_totali_target - sum(nuovi_interi)  # sempre int >= 0
    resti.sort(reverse=True)

    # Distribuisce il resto agli item con frazione residua più alta
    n_resti = len(resti)
    for i in range(differenza):
        nuovi_interi[resti[i % n_resti][1]] += 1

    # ── Garanzia matematica assoluta ────────────────────────────────────────
    # Protegge da edge-case di floating point: se la somma non è esatta,
    # corregge aggiungendo/sottraendo dal valore più grande.
    _somma_finale = sum(nuovi_interi)
    if _somma_finale != punti_totali_target:
        _delta   = punti_totali_target - _somma_finale
        _idx_max = nuovi_interi.index(max(nuovi_interi))
        nuovi_interi[_idx_max] += _delta
        logger.info(
            "riscala_punti: correzione finale %+d pt applicata a item #%d "
            "(edge-case floating point)",
            _delta, _idx_max + 1,
        )

    # ── Log di debug per ogni item ───────────────────────────────────────────
    logger.info(
        "riscala_punti: %d marcatori trovati — somma originale %.1f pt → target %d pt",
        len(matches), somma_attuale, punti_totali_target,
    )
    for i, (val_orig, val_nuovo) in enumerate(zip(valori, nuovi_interi)):
        logger.info("  item %2d: %.1f pt → %d pt", i + 1, val_orig, val_nuovo)
    logger.info(
        "riscala_punti: TOTALE FINALE = %d pt  [target = %d pt]  ✓",
        sum(nuovi_interi), punti_totali_target,
    )

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

        matches = list(_PT_PATTERN.finditer(body_text))
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

        # Garanzia: la somma per questo blocco deve essere esattamente target
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

# ── VALIDATE TIKZ CODE ────────────────────────────────────────────────────────

def validate_tikz_code(latex: str) -> tuple[bool, str]:
    """
    Valida il codice TikZ per errori comuni che causano fallimenti di compilazione.
    Restituisce (is_valid, error_message).
    """
    # Trova tutti i blocchi tikzpicture
    tikz_blocks = re.findall(r'\\begin\{tikzpicture\}(.*?)\\end\{tikzpicture\}', latex, re.DOTALL)
    
    for i, block in enumerate(tikz_blocks):
        # Controlla begin/end bilanciati
        begin_count = len(re.findall(r'\\begin\{([^}]+)\}', block))
        end_count = len(re.findall(r'\\end\{([^}]+)\}', block))
        
        if begin_count != end_count:
            return False, f"Errore nel blocco TikZ {i+1}: numero di \\begin e \\end non bilanciati ({begin_count} vs {end_count})"
        
        # Controlla caratteri problematici
        if '—' in block or '–' in block:  # trattini speciali
            return False, f"Errore nel blocco TikZ {i+1}: caratteri speciali non compatibili (—, –)"
        
        # Controlla parentesi graffe non bilanciate
        brace_count = block.count('{') - block.count('}')
        if brace_count != 0:
            return False, f"Errore nel blocco TikZ {i+1}: parentesi graffe non bilanciate"
        
        # Controlla comandi incompleti o sospetti
        suspicious_patterns = [
            r'\\node\s*\[.*?\]\s*at\s*\([^)]*$',  # \node senza coordinate complete
            r'\\draw\s*\([^)]*$',  # \draw incompleto
            r'\\begin\{axis\}[^}]*$',  # \begin{axis} senza chiusura
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, block, re.MULTILINE):
                return False, f"Errore nel blocco TikZ {i+1}: comando incompleto o sospetto"
    
    return True, ""

# ── CLEAN TIKZ SPOILERS ────────────────────────────────────────────────────────

def clean_tikz_spoilers(latex: str) -> str:
    """
    Rimuove due classi di artefatti dall'output AI che spollerebbero le risposte:

    1. Testo tecnico nel corpo della verifica (fuori da tikzpicture):
       frasi come "ottenuto con TikZ", "generato con TikZ", "grafico TikZ", ecc.
       Sostituisce la frase incriminata con una formulazione neutra oppure la
       rimuove del tutto se è solo una parentetica.

    2. Annotazioni \node dentro tikzpicture che etichettano quantità "risposta":
       - coordinate del vertice  (es. \node at (0,2) {$V(0,2)$})
       - equazione dell'asse di simmetria (es. \node {asse x=0})
       - etichette di punti con coordinate esplicite usate come risposta
    """
    # ── 1. Testo tecnico nel corpo ────────────────────────────────────────────
    # Pattern: "ottenuto/generato/prodotto con TikZ/pgfplots/PGF" (varie forme)
    _tech_pattern = re.compile(
        r',?\s*(?:ottenuto|generato|prodotto|creato|disegnato)\s+con\s+'
        r'(?:TikZ|tikz|pgfplots|PGFPlots|PGF|LaTeX)\b[^.;,\n]*',
        re.IGNORECASE,
    )
    latex = _tech_pattern.sub('', latex)

    # Rimuovi la frase completa se contiene solo il riferimento tecnico
    # es. "Si osservi il grafico ottenuto con TikZ di seguito." →
    #     "Si osservi il seguente grafico."
    latex = re.sub(
        r'(?i)(Si osservi[^.]*?)(?:,?\s*(?:ottenuto|generato|prodotto)\s+con\s+'
        r'(?:TikZ|tikz|pgfplots)\s*,?)([^.]*\.)',
        r'\1\2',
        latex,
    )

    # ── 2. \node spoiler dentro tikzpicture ──────────────────────────────────
    # Trova tutti i blocchi tikzpicture e pulisce i \node con valori-risposta
    def _clean_tikz_block(m: re.Match) -> str:
        block = m.group(0)
        # Pattern per \node che etichettano vertice, asse o coordinate esplicite:
        # \node[...] at (...) {$V(...)} o \node {...asse x=...} o label con V(
        spoiler_node = re.compile(
            r'\\node\b[^;]*?\{[^}]*?'
            r'(?:'
            r'[Vv]ertice|[Vv]ertex'             # "Vertice" / "vertex"
            r'|\\text\{[Aa]sse\}|[Aa]sse\s+x\s*=' # "asse x=..."
            r'|[Aa]xis\s+x\s*='
            r'|\$\s*[Vv]\s*\('                   # "$V("  — label vertice math
            r'|\$\s*x\s*=\s*[-\d]'               # "$x = 0" — asse simmetria
            r')\s*[^}]*\}\s*;',
            re.DOTALL,
        )
        block = spoiler_node.sub('', block)
        # Rimuovi anche \node con fill=red/blue/green che indicano punto speciale
        # e hanno coordinate che coincidono con un dato matematico evidenziato
        block = re.sub(
            r'\\node\s*\[[^\]]*(?:fill|draw)\s*=\s*\w+[^\]]*\]\s+at\s*'
            r'\([^)]+\)\s*\{[^}]*\$[^}]+\$[^}]*\}\s*;',
            '',
            block,
        )
        return block

    latex = re.sub(
        r'\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}',
        _clean_tikz_block,
        latex,
        flags=re.DOTALL,
    )
    return latex


# ── FIX TIKZ LABELS ───────────────────────────────────────────────────────────

def fix_tikz_labels(latex: str) -> str:
    """
    Corregge un bug frequente dell'AI nella generazione TikZ:
    i valori math nei label TikZ con virgole NON sono wrappati in {} e questo
    fa sì che TikZ interpreti la virgola come separatore di chiavi.

    Esempio rotto:   [label=right:$A(2,3)$]
    Esempio corretto:[label=right:{$A(2,3)$}]

    Applica il wrap a TUTTI i valori label=X:$...$, non solo quelli con virgola,
    per robustezza (parentesi, segni, etc. possono causare parsing ambiguo).
    """
    # Pattern: label=<qualcosa>:<espressione_math>
    # dove <espressione_math> = $...$ NON già wrappata in {}
    # Il lookahead negativo (?<!\{) e (?!\}) evita doppio-wrap.
    latex = re.sub(
        r'(label\s*=\s*[^:,\]\s{]+\s*:\s*)(?!\{)(\$[^$\n]+\$)',
        r'\1{\2}',
        latex
    )
    # Caso aggiuntivo: label={above right}:$...$  (direction già in {})
    # già gestito dal pattern sopra, ma aggiungiamo il caso con spazi
    latex = re.sub(
        r'(label\s*=\s*\{[^}]+\}\s*:\s*)(?!\{)(\$[^$\n]+\$)',
        r'\1{\2}',
        latex
    )
    return latex


# ── COMPILAZIONE PDF ───────────────────────────────────────────────────────────

def compila_pdf(codice_latex: str) -> tuple[bytes | None, str | None]:
    # Applica fix pre-compilazione: rimuovi spoiler TikZ, poi fix label math
    codice_latex = clean_tikz_spoilers(codice_latex)
    codice_latex = fix_tikz_labels(codice_latex)
    
    # Validazione codice TikZ per catturare errori comuni
    is_valid, error_msg = validate_tikz_code(codice_latex)
    if not is_valid:
        logger.error(f"Validazione TikZ fallita: {error_msg}")
        return None, f"Errore nel codice TikZ: {error_msg}"

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
