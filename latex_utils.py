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

# Pattern canonico per (N pt) — robusto a spazi extra dell'AI e formati alternativi
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
    if m:
        corpo = m.group(1).strip()
        # DEBUG: Stampa cosa viene estratto
        print(f"🔍 DEBUG extract_corpo: estratti {len(corpo)} caratteri")
        if corpo:
            print(f"📄 Contenuto estratto (primi 200): {corpo[:200]}")
            # 🔥 RIMUOVI EVENTUALI \begin{document} residui dal corpo
            corpo = re.sub(r"\\begin\{document\}", "", corpo)
            corpo = re.sub(r"\\documentclass\[.*?\]\{.*?\}", "", corpo)
            corpo = re.sub(r"\\usepackage\[.*?\]\{.*?\}", "", corpo)
            corpo = corpo.strip()
            print(f"🧹 Corpo pulito: {len(corpo)} caratteri")
        else:
            print(f"❌ CORPO VUOTO estratto!")
        return corpo
    else:
        print(f"❌ Nessun match trovato in extract_corpo!")
        return ""


def extract_preambolo(latex: str) -> str:
    """Estrae il preambolo fino a \\end{center} incluso."""
    m = re.search(r"^(.*?\\end\{center\})", latex, re.DOTALL)
    return m.group(1) + "\n" if m else ""


# ── SCORE PARSING PER BLOCCO (UI Ricalibra Punteggi) ───────────────────────────

def parse_pts_from_block_body(body: str) -> int:
    """Somma tutti i (N pt) nel corpo del blocco con pattern migliorati."""
    # Pattern più completo per catturare anche decimali, virgole e formati alternativi
    pt_patterns = [
        r'\((\d+(?:[.,]\d+)?)\s*pt\)',      # (5 pt)
        r'\[(\d+(?:[.,]\d+)?)\s*pt\]',      # [5 pt]
        r'(\d+(?:[.,]\d+)?)\s*pt',           # 5 pt
        r'\((\d+(?:[.,]\d+)?)\s*punti?\)',   # (5 punti)
        r'(\d+(?:[.,]\d+)?)\s*punti?',       # 5 punti
        r'punti:\s*(\d+(?:[.,]\d+)?)',       # punti: 5
        r'valore:\s*(\d+(?:[.,]\d+)?)',      # valore: 5
    ]
    
    total = 0
    found_patterns = []
    
    for pattern in pt_patterns:
        matches = re.findall(pattern, body, re.IGNORECASE)
        if matches:
            points = sum(int(float(p.replace(',', '.'))) for p in matches)
            total += points
            found_patterns.append((pattern, len(matches), points))
            logger.info(f"Trovati {len(matches)} punti con pattern '{pattern}': {points}")
            break  # Usa solo il primo pattern che trova match
    
    # Se non trova punti, cerca nell'header del blocco
    if total == 0:
        header_pt_pattern = r'\\subsection\*\{[^}]*\}\s*\((\d+(?:[.,]\d+)?)\s*pt\)'
        header_match = re.search(header_pt_pattern, body, re.IGNORECASE)
        if header_match:
            total = int(float(header_match.group(1).replace(',', '.')))
            logger.info(f"Trovati punti nell'header: {total}")
    
    logger.info(f"Punti totali nel blocco: {total}")
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
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"=== PARSE ITEMS FROM BLOCK ===")
    logger.info(f"Title: {title}")
    logger.info(f"Body length: {len(body)} characters")
    logger.info(f"Body (first 500 chars): {body[:500]}...")
    logger.info(f"Body (last 200 chars): ...{body[-200:]}")
    
    # Conta occorrenze di \item per debug
    item_count = len(re.findall(r'\\item', body))
    logger.info(f"Total \\item occurrences found: {item_count}")
    
    # Mostra le prime linee per vedere la struttura
    lines = body.split('\n')[:10]
    logger.info(f"First 10 lines:")
    for i, line in enumerate(lines):
        logger.info(f"  {i+1}: {repr(line)}")
    
    auto_labels = list('abcdefghijklmnopqrstuvwxyz')
    items = []

    # Prima prova: item con label esplicito [a)], [b)], ecc.
    # Pattern più flessibile per catturare diversi formati
    labeled_patterns = [
        r'\\item\[([^\]]+)\]([^{]*?)(?=\\item|\Z)',           # Standard: \item[a)] testo
        r'\\item\[([^\]]+)\]\s*([^\n]*?)(?=\\item|\n\n|\Z)',  # Con newline: \item[a)] testo\n
        r'\\item\[([^\]]+)\](.*?)(?=\\item|\n\n|\Z)',         # Lazy match: \item[a)] testo
    ]
    
    labeled = []
    for pattern in labeled_patterns:
        matches = list(re.finditer(pattern, body, re.DOTALL))
        if matches:
            labeled = matches
            logger.info(f"Labeled items found: {len(matches)} with pattern: {pattern}")
            break
    
    if not labeled:
        logger.info(f"No labeled items found with any pattern")
    
    # Controlla se è un esercizio a scelta multipla
    # Pattern: sequenza di item con lettere A), B), C), D) ecc. senza punteggi individuali
    multiple_choice_pattern = r'\\item\s+([A-Z])\)\s*([^(]*?)(?=\\item\s+[A-Z]\)|\\item\s*\(|\\end|\Z)'
    multiple_choice_matches = list(re.finditer(multiple_choice_pattern, body, re.DOTALL))
    
    if multiple_choice_matches and len(multiple_choice_matches) >= 2:
        logger.info(f"Multiple choice question detected: {len(multiple_choice_matches)} options")
        
        # Combina tutte le opzioni in un unico item
        combined_text = ""
        total_points = 0
        question_text = ""
        
        for i, m in enumerate(multiple_choice_matches):
            option_letter = m.group(1)
            option_text = m.group(2).strip()
            
            if i == 0:
                # Prima opzione: cerca il punteggio totale nella domanda
                pts_patterns = [
                    r'\((\d+(?:[.,]\d+)?)\s*pt\)',      # (5 pt)
                    r'\[(\d+(?:[.,]\d+)?)\s*pt\]',      # [5 pt]
                    r'(\d+(?:[.,]\d+)?)\s*pt',           # 5 pt
                    r'\((\d+(?:[.,]\d+)?)\s*punti?\)',   # (5 punti)
                    r'(\d+(?:[.,]\d+)?)\s*punti?',       # 5 punti
                ]
                
                for pattern in pts_patterns:
                    pts_m = re.search(pattern, option_text)
                    if pts_m:
                        total_points = int(float(pts_m.group(1).replace(',', '.')))
                        logger.info(f"Multiple choice total points: {total_points}")
                        # Rimuovi il punteggio dal testo
                        option_text = re.sub(pattern, '', option_text).strip()
                        break
                
                # Estrai la parte della domanda prima delle opzioni
                question_match = re.search(r'^(.*?)(?=\\item\s+[A-Z]\))', body, re.DOTALL)
                if question_match:
                    question_text = question_match.group(1).strip()
                    # Rimuovi il punteggio dalla domanda
                    for pattern in pts_patterns:
                        question_text = re.sub(pattern, '', question_text).strip()
            
            combined_text += f"{option_letter}) {option_text} "
        
        # Crea un unico item per la domanda a scelta multipla
        full_text = f"{question_text}\n{combined_text.strip()}"
        short_text = (full_text[:80] + '\u2026') if len(full_text) > 80 else full_text
        
        logger.info(f"Multiple choice combined item: '{short_text}'")
        items.append(("MCQ", short_text, total_points))
        logger.info(f"Returning 1 multiple choice item")
        return items
    
    if labeled:
        for i, m in enumerate(labeled):
            label = m.group(1).strip()
            text = m.group(2).strip()
            logger.info(f"Labeled item {i+1}: label='{label}', text='{text[:100]}...'")
            logger.info(f"Labeled item {i+1}: full_text_length={len(text)}")
            
            # Prova diversi regex per i punti
            pts_patterns = [
                r'\((\d+(?:[.,]\d+)?)\s*pt\)',      # (5 pt)
                r'\[(\d+(?:[.,]\d+)?)\s*pt\]',      # [5 pt]
                r'(\d+(?:[.,]\d+)?)\s*pt',           # 5 pt
                r'\((\d+(?:[.,]\d+)?)\s*punti?\)',   # (5 punti)
                r'(\d+(?:[.,]\d+)?)\s*punti?',       # 5 punti
                r'(\d+(?:[.,]\d+)?)\s*points?',      # 5 points (inglese)
                r'punti:\s*(\d+(?:[.,]\d+)?)',       # punti: 5
                r'valore:\s*(\d+(?:[.,]\d+)?)',      # valore: 5
            ]
            
            pts_m = None
            pts = 0
            for pattern in pts_patterns:
                pts_m = re.search(pattern, text)
                if pts_m:
                    pts = int(float(pts_m.group(1).replace(',', '.')))
                    logger.info(f"  Points found with pattern '{pattern}': {pts_m.group(1)} -> {pts}pt")
                    break
            
            if not pts_m:
                logger.info(f"  No points found in text with any pattern")
            
            clean = re.sub(r'\(\d+(?:[.,]\d+?)?\s*pt\)', '', text).strip()
            clean = re.sub(r'\s+', ' ', clean)
            clean = re.sub(r'\\[a-zA-Z]+\{[^}]*\}', '', clean)
            clean = re.sub(r'\$[^$]*\$', '[formula]', clean)
            short = (clean[:42] + '\u2026') if len(clean) > 42 else clean
            items.append((label, short, pts))
        logger.info(f"Returning {len(items)} labeled items")
        return items

    # Seconda prova: item senza label, auto-generati a), b), c)
    # Pattern più aggressivi per catturare tutti gli items con spazi
    auto_patterns = [
        r'\\item\s+(.+?)(?=\\item\s+|\\end|\Z)',              # Standard: \item testo (aggressive)
        r'\\item\s+([^\n]*?)(?=\\item|\n\n|\Z)',             # Con newline: \item testo\n
        r'\\item\s*(.*?)(?=\\item|\n\n|\Z)',                  # Lazy match: \item testo
        r'\\item([^\n]*?)(?=\\item|\n\n|\Z)',                 # No space: \itemtesto
        r'\\item\s+(.+?)(?=\\item|\\end|\Z)',                 # Fallback: cattura tutto fino a prossimo \item o \end
    ]
    
    auto_items = []
    for pattern in auto_patterns:
        matches = list(re.finditer(pattern, body, re.DOTALL))
        if matches:
            auto_items = matches
            logger.info(f"Auto items found: {len(matches)} with pattern: {pattern}")
            break
    
    if not auto_items:
        logger.info(f"No auto items found with any pattern")
    
    # Controlla anche qui se è un esercizio a scelta multipla (per auto items)
    if auto_items and len(auto_items) >= 2:
        # Verifica se gli item iniziano con lettere maiuscole seguite da )
        first_texts = [m.group(1).strip() for m in auto_items[:3]]  # Controlla primi 3
        is_multiple_choice = all(re.match(r'^[A-Z]\)\s+', text) for text in first_texts)
        
        if is_multiple_choice:
            logger.info(f"Multiple choice question detected in auto items: {len(auto_items)} options")
            
            # Combina tutte le opzioni in un unico item
            combined_text = ""
            total_points = 0
            question_text = ""
            
            # Estrai il testo prima della prima opzione
            body_parts = body.split('\\item')
            if len(body_parts) > 1:
                question_text = body_parts[0].strip()
                # Cerca il punteggio totale nella domanda
                pts_patterns = [
                    r'\((\d+(?:[.,]\d+)?)\s*pt\)',      # (5 pt)
                    r'\[(\d+(?:[.,]\d+)?)\s*pt\]',      # [5 pt]
                    r'(\d+(?:[.,]\d+)?)\s*pt',           # 5 pt
                    r'\((\d+(?:[.,]\d+)?)\s*punti?\)',   # (5 punti)
                    r'(\d+(?:[.,]\d+)?)\s*punti?',       # 5 punti
                ]
                
                for pattern in pts_patterns:
                    pts_m = re.search(pattern, question_text)
                    if pts_m:
                        total_points = int(float(pts_m.group(1).replace(',', '.')))
                        logger.info(f"Multiple choice total points (auto): {total_points}")
                        # Rimuovi il punteggio dalla domanda
                        question_text = re.sub(pattern, '', question_text).strip()
                        break
            
            # Combina tutte le opzioni
            for i, m in enumerate(auto_items):
                text = m.group(1).strip()
                combined_text += f"{text} "
            
            # Crea un unico item per la domanda a scelta multipla
            full_text = f"{question_text}\n{combined_text.strip()}"
            short_text = (full_text[:80] + '\u2026') if len(full_text) > 80 else full_text
            
            logger.info(f"Multiple choice combined item (auto): '{short_text}'")
            items.append(("MCQ", short_text, total_points))
            logger.info(f"Returning 1 multiple choice item (auto)")
            return items
    
    if auto_items:
        auto_idx = 0
        for i, m in enumerate(auto_items):
            text = m.group(1).strip()
            if not text:  # Salta item vuoti
                continue
            logger.info(f"Auto item {i+1}: text='{text[:100]}...'")
            logger.info(f"Auto item {i+1}: full_text_length={len(text)}")
            
            # Prova diversi regex per i punti
            pts_patterns = [
                r'\((\d+(?:[.,]\d+)?)\s*pt\)',      # (5 pt)
                r'\[(\d+(?:[.,]\d+)?)\s*pt\]',      # [5 pt]
                r'(\d+(?:[.,]\d+)?)\s*pt',           # 5 pt
                r'\((\d+(?:[.,]\d+)?)\s*punti?\)',   # (5 punti)
                r'(\d+(?:[.,]\d+)?)\s*punti?',       # 5 punti
                r'(\d+(?:[.,]\d+)?)\s*points?',      # 5 points (inglese)
                r'punti:\s*(\d+(?:[.,]\d+)?)',       # punti: 5
                r'valore:\s*(\d+(?:[.,]\d+)?)',      # valore: 5
            ]
            
            pts_m = None
            pts = 0
            for pattern in pts_patterns:
                pts_m = re.search(pattern, text)
                if pts_m:
                    pts = int(float(pts_m.group(1).replace(',', '.')))
                    logger.info(f"  Points found with pattern '{pattern}': {pts_m.group(1)} -> {pts}pt")
                    break
            
            if not pts_m:
                logger.info(f"  No points found in text with any pattern")
            
            clean = re.sub(r'\(\d+(?:[.,]\d+?)?\s*pt\)', '', text).strip()
            clean = re.sub(r'\s+', ' ', clean)
            clean = re.sub(r'\\[a-zA-Z]+\{[^}]*\}', '', clean)
            clean = re.sub(r'\$[^$]*\$', '[formula]', clean)
            short = (clean[:42] + '\u2026') if len(clean) > 42 else clean
            label = auto_labels[auto_idx] + ')' if auto_idx < len(auto_labels) else f'{auto_idx+1})'
            items.append((label, short, pts))
            auto_idx += 1

        if items:
            logger.info(f"Returning {len(items)} auto items")
            return items

    # Terza prova: fallback - cerca qualsiasi \item
    # Pattern più aggressivi per catturare tutto
    fallback_patterns = [
        r'\\item\s+(.+?)(?=\\item\s+|\\end|\Z)',         # Aggressive: cattura tutto
        r'\\item[^\n]*',                                    # Standard: \item testo
        r'\\item.*?(?=\\item|\n\n|\Z)',                   # Lazy match fino a prossimo item
        r'\\item\{[^}]*\}[^\n]*',                          # Item con opzioni: \item[label] testo
        r'\\item\s*(.+?)(?=\\item|\\end|\Z)',              # Fallback lazy
    ]
    
    fallback_items = []
    for pattern in fallback_patterns:
        matches = list(re.finditer(pattern, body))
        if matches:
            fallback_items = matches
            logger.info(f"Fallback items found: {len(matches)} with pattern: {pattern}")
            break
    
    if not fallback_items:
        logger.info(f"No fallback items found with any pattern")
    
    if fallback_items:
        auto_idx = 0
        for i, m in enumerate(fallback_items):
            text = m.group(0).replace('\\item', '').strip()
            if not text:  # Salta item vuoti
                continue
            logger.info(f"Fallback item {i+1}: text='{text[:100]}...'")
            logger.info(f"Fallback item {i+1}: full_text_length={len(text)}")
            
            # Prova diversi regex per i punti
            pts_patterns = [
                r'\((\d+(?:[.,]\d+)?)\s*pt\)',      # (5 pt)
                r'\[(\d+(?:[.,]\d+)?)\s*pt\]',      # [5 pt]
                r'(\d+(?:[.,]\d+)?)\s*pt',           # 5 pt
                r'\((\d+(?:[.,]\d+)?)\s*punti?\)',   # (5 punti)
                r'(\d+(?:[.,]\d+)?)\s*punti?',       # 5 punti
                r'(\d+(?:[.,]\d+)?)\s*points?',      # 5 points (inglese)
                r'punti:\s*(\d+(?:[.,]\d+)?)',       # punti: 5
                r'valore:\s*(\d+(?:[.,]\d+)?)',      # valore: 5
            ]
            
            pts_m = None
            pts = 0
            for pattern in pts_patterns:
                pts_m = re.search(pattern, text)
                if pts_m:
                    pts = int(float(pts_m.group(1).replace(',', '.')))
                    logger.info(f"  Points found with pattern '{pattern}': {pts_m.group(1)} -> {pts}pt")
                    break
            
            if not pts_m:
                logger.info(f"  No points found in text with any pattern")
            
            clean = re.sub(r'\(\d+(?:[.,]\d+?)?\s*pt\)', '', text).strip()
            clean = re.sub(r'\s+', ' ', clean)
            clean = re.sub(r'\\[a-zA-Z]+\{[^}]*\}', '', clean)
            clean = re.sub(r'\$[^$]*\$', '[formula]', clean)
            short = (clean[:42] + '\u2026') if len(clean) > 42 else clean
            label = auto_labels[auto_idx] + ')' if auto_idx < len(auto_labels) else f'{auto_idx+1})'
            items.append((label, short, pts))
            auto_idx += 1

    logger.info(f"Final result: {len(items)} items parsed")
    
    # Ultimo fallback: controlla se c'è un punteggio globale nel titolo o nel body
    if not items:
        # Prima controlla nel body (esercizi singoli senza \item)
        pts_body = re.search(r'\((\d+(?:[.,]\d+)?)\s*pt\)', body)
        if pts_body:
            pts = int(float(pts_body.group(1).replace(',', '.')))
            # Estrai il testo principale dell'esercizio
            clean_body = re.sub(r'\s*\(\d+(?:[.,]\d+?)?\s*pt\)', '', body).strip()
            clean_body = re.sub(r'\s+', ' ', clean_body)
            # Rimuovi comandi LaTeX
            clean_body = re.sub(r'\\[a-zA-Z]+\{[^}]*\}', '', clean_body)
            clean_body = re.sub(r'\$[^$]*\$', '[formula]', clean_body)
            short = (clean_body[:42] + '\u2026') if len(clean_body) > 42 else clean_body
            items.append(("—", short or "Esercizio completo", pts))
            logger.info(f"Found global points in body: {pts}pt")
        elif title:
            # Poi controlla nel titolo
            pt_title = re.search(r'\((\d+(?:[.,]\d+)?)\s*pt\)', title)
            if pt_title:
                pts = int(float(pt_title.group(1).replace(',', '.')))
                clean_title = re.sub(r'\s*\(\d+(?:[.,]\d+?)?\s*pt\)', '', title).strip()
                clean_title = re.sub(r'\s+', ' ', clean_title)
                short = (clean_title[:42] + '\u2026') if len(clean_title) > 42 else clean_title
                items.append(("—", short, pts))
                logger.info(f"Found global points in title: {pts}pt")
    
    logger.info(f"Returning {len(items)} items total")
    
    # Debug finale: mostra cosa potrebbe essere stato perso
    if item_count > len(items):
        logger.warning(f"⚠️  {item_count} \\item found but only {len(items)} parsed!")
        logger.warning("This suggests some items are not being captured by any pattern")
        
        # Mostra tutti gli \item trovati per analisi
        all_items = re.findall(r'\\item[^\n]*', body)
        logger.warning("All \\item lines found:")
        for i, item in enumerate(all_items):
            logger.warning(f"  {i+1}: {repr(item)}")
    elif item_count == 0 and body.strip():
        logger.warning("⚠️  No \\item found but body is not empty - checking for other patterns...")
        # Controlla se ci sono altri indicatori di items
        if re.search(r'[a-z]\)|[a-z]\.', body):
            logger.warning("Found a) b) patterns without \\item - this might be the issue")
    
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

    # Nuova riga per punteggio effettivo dello studente
    row_voto = "\\textbf{Voto}" + "".join(
        f" & \\makebox[1.2cm]{{\\hrulefill}}" for ex in esercizi for _, _ in ex['items']
    ) + " & \\makebox[1.2cm]{{\\hrulefill}} \\\\ \\hline"

    return (
        "% GRIGLIA\n\\begin{center}\n\\textbf{Tabella Punteggi}\\\\[0.3cm]\n"
        "{\\renewcommand{\\arraystretch}{1.8}\n"
        f"\\adjustbox{{max width=\\textwidth}}{{\n"
        f"\\begin{{tabular}}{{{col_spec}}}\n\\hline\n"
        f"{row_es}\n{row_sotto}\n{row_max}\n{row_voto}\n"
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
    Aggiunge anche spaziatura appropriata tra gli item.
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
            result.append('')  # Linea vuota per spaziatura
            in_bare_block = False

        result.append(line)
        list_depth = max(0, list_depth + list_opens - list_closes)

    if in_bare_block:
        result.append(r'\end{enumerate}')
        result.append('')  # Linea vuota per spaziatura

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


def assicura_punti_visibili(corpo: str, punti_totali: int) -> str:
    """
    Assicura che i punti siano visibili nel corpo dell'esercizio.
    Se non trova punti, aggiunge un punteggio di default.
    """
    # Controlla se ci sono già punti nel corpo
    if _PT_PATTERN.search(corpo):
        return corpo
    
    # Se non ci sono punti, aggiungi un punteggio di default
    logger.warning("Nessun punto trovato nel corpo, aggiungo punteggio di default")
    
    # Cerca gli esercizi nel corpo
    esercizi = re.findall(r'(\\subsection\*\{[^}]*\})(.*?)(?=\\subsection\*|$)', corpo, re.DOTALL)
    
    if not esercizi:
        return corpo
    
    num_esercizi = len(esercizi)
    punti_per_esercizio = max(1, punti_totali // num_esercizi)
    punti_restanti = punti_totali - (punti_per_esercizio * num_esercizi)
    
    nuovo_corpo = ""
    for i, (header, body) in enumerate(esercizi):
        punti_esercizio = punti_per_esercizio
        if i == num_esercizi - 1:  # Ultimo esercizio
            punti_esercizio += punti_restanti
        
        # Controlla se ci sono item nell'esercizio
        items = re.findall(r'\\item\[[^\]]+\]', body)
        
        if items:
            # Distribuisci i punti tra gli item
            punti_per_item = max(1, punti_esercizio // len(items))
            punti_restanti_item = punti_esercizio - (punti_per_item * len(items))
            
            new_body = body
            for j, item in enumerate(items):
                item_points = punti_per_item
                if j == len(items) - 1:  # Ultimo item
                    item_points += punti_restanti_item
                
                # Aggiungi punti dopo l'item
                item_pattern = re.escape(item) + r'\s*([^\n]*?)(?=\n|$)'
                new_body = re.sub(
                    item_pattern,
                    lambda m: item + m.group(1).strip() + f" ({item_points} pt)",
                    new_body,
                    count=1
                )
            
            nuovo_corpo += header + new_body + "\n\n"
        else:
            # Aggiungi punti alla fine del corpo dell'esercizio
            if body.strip() and not body.strip().endswith(')'):
                body = body.rstrip() + f" ({punti_esercizio} pt)"
            elif not body.strip():
                body = f" ({punti_esercizio} pt)"
            
            nuovo_corpo += header + body + "\n\n"
    
    return nuovo_corpo.strip()


def limita_altezza_grafici(latex: str) -> str:
    """
    Disabilitato: non modifica i grafici TikZ generati dall'AI.
    I grafici generati dall'AI dovrebbero essere già ben formattati.
    """
    # Non fare nulla - mantieni i grafici come generati dall'AI
    return latex


def _calculate_dynamic_limits(func_expr: str) -> dict:
    """
    Calcola limiti dinamici basati sull'espressione della funzione.
    Analizza funzioni comuni per determinare i punti importanti.
    """
    # Default limits
    limits = {"xmin": -6, "xmax": 6, "ymin": -6, "ymax": 6}
    
    try:
        # Pattern per funzioni quadratiche ax^2 + bx + c
        quad_match = re.search(r'([+-]?\d*\.?\d*)\*x\^2\s*([+-]\s*\d*\.?\d*)\*x\s*([+-]\s*\d+\.?\d*)', func_expr)
        if quad_match:
            a = float(quad_match.group(1).replace('+', '') or '1')
            b = float(quad_match.group(2).replace('+', '') or '0')
            c = float(quad_match.group(3).replace('+', '') or '0')
            
            if a != 0:
                # Calcolo vertice
                x_vertex = -b / (2 * a)
                y_vertex = a * x_vertex**2 + b * x_vertex + c
                
                # Calcolo intersezioni con asse x
                discriminant = b**2 - 4*a*c
                if discriminant >= 0:
                    sqrt_disc = discriminant**0.5
                    x1 = (-b - sqrt_disc) / (2*a)
                    x2 = (-b + sqrt_disc) / (2*a)
                
                # Determina range basato su punti importanti
                x_points = [x_vertex]
                if discriminant >= 0:
                    x_points.extend([x1, x2])
                
                x_min = min(x_points) - 2
                x_max = max(x_points) + 2
                
                # Calcola valori y estremi nel range x
                y_test_points = [x_min, x_max, x_vertex]
                if discriminant >= 0:
                    y_test_points.extend([x1, x2])
                
                y_values = [a*x**2 + b*x + c for x in y_test_points]
                y_min = min(y_values) - 2
                y_max = max(y_values) + 2
                
                # Limiti ragionevoli
                limits = {
                    "xmin": max(-8, min(x_min, -4)),
                    "xmax": min(8, max(x_max, 4)),
                    "ymin": max(-8, min(y_min, -4)),
                    "ymax": min(8, max(y_max, 4))
                }
        
        # Pattern per funzioni lineari mx + q
        linear_match = re.search(r'([+-]?\d*\.?\d*)\*x\s*([+-]\s*\d+\.?\d*)', func_expr)
        if linear_match:
            m = float(linear_match.group(1).replace('+', '') or '1')
            q = float(linear_match.group(2).replace('+', '') or '0')
            
            # Calcola valori agli estremi
            y_minus4 = m * -4 + q
            y_plus4 = m * 4 + q
            
            y_min = min(y_minus4, y_plus4, 0) - 2
            y_max = max(y_minus4, y_plus4, 0) + 2
            
            limits = {
                "xmin": -6, "xmax": 6,
                "ymin": max(-8, y_min),
                "ymax": min(8, y_max)
            }
    
    except Exception as e:
        logger.warning(f"Errore nel calcolo limiti dinamici: {e}")
        # Fallback a limiti standard più ampi
        limits = {"xmin": -8, "xmax": 8, "ymin": -8, "ymax": 8}
    
    return limits


def aggiungi_spaziatura_grafici_tabelle(latex: str) -> str:
    """
    Aggiunge spaziatura prima dei grafici e delle tabelle.
    Sostituisce i placeholder con contenuti reali.
    """
    # Sostituisci placeholder [Grafico] con un grafico TikZ di esempio
    latex = re.sub(
        r'\[Grafico\]',
        r'''\\vspace{0.5cm}

\\begin{center}
\\begin{tikzpicture}[scale=0.8]
\\begin{axis}[
    xmin=-4, xmax=4,
    ymin=-2, ymax=6,
    axis lines=middle,
    xlabel=$x$,
    ylabel=$y$,
    grid=major,
    width=8cm,
    height=5cm,
    domain=-4:4,
    samples=100
]
\\addplot[blue, thick] {x^2 - 2*x - 1};
\\addplot[only marks, mark=*, red] coordinates {(1, -2) (3, 2)};
\\end{axis}
\\end{tikzpicture}
\\end{center}

\\vspace{0.3cm}''',
        latex
    )
    
    # Sostituisci placeholder [Tabella] con una tabella punteggi reale
    latex = re.sub(
        r'\[Tabella\]',
        r'''\\begin{tabular}{|c|c|c|}
\\hline
\\textbf{Esercizio} & \\textbf{Punti} & \\textbf{Ottenuti} \\\\
\\hline
Esercizio 1 & 20 pt &  \\\\
\\hline
Esercizio 2 & 20 pt &  \\\\
\\hline
Esercizio 3 & 20 pt &  \\\\
\\hline
Esercizio 4 & 20 pt &  \\\\
\\hline
Esercizio 5 & 20 pt &  \\\\
\\hline
\\textbf{Totale} & \\textbf{100 pt} &  \\\\
\\hline
\\end{tabular}''',
        latex
    )
    
    # Aggiungi spaziatura prima dei grafici TikZ esistenti
    latex = re.sub(
        r'(?<!\n\n)\\begin\{tikzpicture\}',
        r'\n\n\\begin{tikzpicture}',
        latex
    )
    
    # Aggiungi spaziatura prima delle tabelle esistenti
    latex = re.sub(
        r'(?<!\n\n)\\begin\{tabular\}',
        r'\n\n\\begin{tabular}',
        latex
    )
    
    # Aggiungi spaziatura prima degli ambienti table
    latex = re.sub(
        r'(?<!\n\n)\\begin\{table\}',
        r'\n\n\\begin{table}',
        latex
    )
    
    return latex


def migliora_spaziatura_sottopunti(latex: str) -> str:
    """
    Migliora la spaziatura tra i sottopunti degli esercizi.
    Assicura che ci sia spaziatura appropriata tra gli item.
    """
    # Sostituisci direttamente pattern comuni di item attaccati
    latex = latex.replace('\\item[a)]', '\n\\item[a)]')
    latex = latex.replace('\\item[b)]', '\n\\item[b)]')
    latex = latex.replace('\\item[c)]', '\n\\item[c)]')
    latex = latex.replace('\\item[d)]', '\n\\item[d)]')
    latex = latex.replace('\\item[e)]', '\n\\item[e)]')
    latex = latex.replace('\\item[f)]', '\n\\item[f)]')
    latex = latex.replace('\\item[g)]', '\n\\item[g)]')
    latex = latex.replace('\\item[h)]', '\n\\item[h)]')
    
    # Aggiungi spaziatura dopo ogni \item con label (caso critico)
    latex = re.sub(r'(\\item\[[^\]]+\][^\n]*?)(?=\\item)', r'\1\n\n', latex)
    
    # Aggiungi spaziatura dopo ogni \item senza label
    latex = re.sub(r'(\\item\s+[^\n]*?)(?=\\item)', r'\1\n\n', latex)
    
    # Aggiungi spaziatura dopo enumerate environments
    latex = re.sub(r'(\\end\{enumerate\})(?!\s*\n)', r'\1\n\n', latex)
    
    # Aggiungi spaziatura prima di ogni \subsection*
    latex = re.sub(r'(?<!\n\n)\\subsection\*', r'\n\n\\subsection*', latex)
    
    # Aggiungi spaziatura dopo ogni \subsection*
    latex = re.sub(r'(\\subsection\*\{[^}]+\})(?!\s*\n)', r'\1\n\n', latex)
    
    # Rimuovi spaziatura eccessiva (più di 2 linee vuote)
    latex = re.sub(r'\n{3,}', '\n\n', latex)
    
    # Assicura spaziatura prima degli esercizi
    latex = re.sub(r'(?<!\n\n)Si consideri', r'\n\nSi consideri', latex)
    latex = re.sub(r'(?<!\n\n)Trovare', r'\n\nTrovare', latex)
    latex = re.sub(r'(?<!\n\n)Si osservi', r'\n\nSi osservi', latex)
    latex = re.sub(r'(?<!\n\n)Data', r'\n\nData', latex)
    latex = re.sub(r'(?<!\n\n)Stabilire', r'\n\nStabilire', latex)
    
    return latex


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
        # Aggiungi spaziatura appropriata dopo l'item
        return '\n' + item_text + '\n\n'
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

def attempt_tikz_fix(latex: str) -> str:
    """
    Tenta di correggere problemi comuni nel codice TikZ.
    """
    logger.info("Applicando correzioni automatiche TikZ...")
    
    fixed_latex = latex
    
    # Fix 1: Sostituisci trattini speciali con trattini normali
    fixed_latex = fixed_latex.replace('—', '--').replace('–', '-')
    
    # Fix 2: Correggi parentesi graffe non bilanciate semplici
    # Aggiungi graffa di chiusura mancante
    brace_count = fixed_latex.count('{') - fixed_latex.count('}')
    if brace_count > 0:
        fixed_latex += '}' * brace_count
        logger.info(f"✓ Aggiunte {brace_count} graffe di chiusura mancanti")
    
    # Fix 3: Correggi comandi \draw incompleti
    # Aggiungi ; finale se mancante
    fixed_latex = re.sub(r'(\\draw[^;]*?)(?=\n|$)', r'\1;', fixed_latex)
    
    # Fix 3b: Correggi "nodes n..." incompleto in axis
    fixed_latex = re.sub(r'nodes\s+n\.\.\.', 'nodes near coords', fixed_latex)
    fixed_latex = re.sub(r'nodes\s+near\s+coords\s*\.\.\.', 'nodes near coords', fixed_latex)
    fixed_latex = re.sub(r'nodes\s+near\s*$', 'nodes near coords', fixed_latex)
    fixed_latex = re.sub(r'nodes\s+n$', 'nodes near coords', fixed_latex)
    
    # Fix 3c: Correggi altri comandi axis incompleti comuni
    fixed_latex = re.sub(r'bar\s+width\s*=\s*\d+cm\s*$', 'bar width=1cm', fixed_latex)
    fixed_latex = re.sub(r'symbolic\s+x\s+coords\s*=\s*\{[^}]*\s*$', r'\\end{axis}', fixed_latex)
    
    # Fix 3d: Correggi \addplot senza coordinates
    fixed_latex = re.sub(r'(\\addplot\s*\[[^\]]*\])\s*$', r'\1 coordinates {};', fixed_latex)
    
    # Fix 3e: Correggi coordinates vuoti o incompleti
    fixed_latex = re.sub(r'coordinates\s*\{\s*\}', 'coordinates {(0,0)}', fixed_latex)
    fixed_latex = re.sub(r'coordinates\s*\{([^}]*)\s*$', r'coordinates {\1}', fixed_latex)
    
    # Fix 3f: Correggi bar width senza unità
    fixed_latex = re.sub(r'bar\s+width\s*=\s*(\d+\.\d+)\s*$', r'bar width=\1cm', fixed_latex)
    
    # Fix 4: Correggi \node senza coordinate complete
    # Aggiungi coordinate di default se mancanti
    fixed_latex = re.sub(r'(\\node\s*\[.*?\]\s*at\s*\([^)]*)(?=\n|$)', r'\1)', fixed_latex)
    
    # Fix 5: Correggi ambienti axis non chiusi
    # Aggiungi \end{axis} se mancante
    axis_count = len(re.findall(r'\\begin\{axis\}', fixed_latex))
    axis_end_count = len(re.findall(r'\\end\{axis\}', fixed_latex))
    if axis_count > axis_end_count:
        missing_ends = axis_count - axis_end_count
        fixed_latex += '\n\\end{axis}' * missing_ends
        logger.info(f"✓ Aggiunti {missing_ends} \\end{{axis}} mancanti")
    
    # Fix 6: Correggi begin/end bilanciati per altri ambienti
    environments = ['tikzpicture', 'tikzcd', 'axis', 'scope']
    for env in environments:
        begin_count = len(re.findall(f'\\\\begin\\{{{env}\\}}', fixed_latex))
        end_count = len(re.findall(f'\\\\end\\{{{env}\\}}', fixed_latex))
        if begin_count > end_count:
            missing_ends = begin_count - end_count
            fixed_latex += f'\n\\end{{{env}}}' * missing_ends
            logger.info(f"✓ Aggiunti {missing_ends} \\end{{{env}}} mancanti")
    
    # Fix 7: Rimuovi caratteri problematici
    problematic_chars = ['"', '"', ''', ''', '…']
    for char in problematic_chars:
        if char in fixed_latex:
            fixed_latex = fixed_latex.replace(char, '')
            logger.info(f"✓ Rimosso carattere problematico: {repr(char)}")
    
    logger.info("✓ Correzioni TikZ applicate")
    return fixed_latex


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
        
        # Controlla comandi \addplot incompleti
        addplot_count = len(re.findall(r'\\addplot', block))
        coordinates_count = len(re.findall(r'coordinates\s*\{', block))
        if addplot_count > 0 and coordinates_count == 0:
            return False, f"Errore nel blocco TikZ {i+1}: \\addplot senza coordinates"
        
        # Controlla comandi \addplot con coordinates non chiuse
        addplot_coords = re.findall(r'coordinates\s*\{([^}]*)', block, re.DOTALL)
        for coords in addplot_coords:
            if not coords.strip():
                return False, f"Errore nel blocco TikZ {i+1}: \\addplot coordinates vuoto"
        
        # Controlla ambienti axis non chiusi
        axis_begin = len(re.findall(r'\\begin\{axis\}', block))
        axis_end = len(re.findall(r'\\end\{axis\}', block))
        if axis_begin != axis_end:
            return False, f"Errore nel blocco TikZ {i+1}: ambienti axis non bilanciati ({axis_begin} vs {axis_end})"
        
        # Controlla comandi incompleti o sospetti
        suspicious_patterns = [
            r'\\node\s*\[.*?\]\s*at\s*\([^)]*$',  # \node senza coordinate complete
            r'\\draw\s*\([^)]*$',  # \draw incompleto
            r'\\begin\{axis\}[^}]*$',  # \begin{axis} senza chiusura
            r'bar\s+width\s*=\s*\d+\.\d*$',  # bar width senza unità
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, block, re.MULTILINE):
                return False, f"Errore nel blocco TikZ {i+1}: comando incompleto o sospetto"
    
    return True, ""

# ── CLEAN TIKZ SPOILERS ────────────────────────────────────────────────────────

def clean_tikz_spoilers(latex: str, aggressive: bool = False) -> str:
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
    
    3. Se aggressive=True, rimuovi completamente i blocchi TikZ problematici
       (ma preserva i grafici matematici semplici)
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
        r'\\begin\{tikzpicture\}(.*?)\\end\{tikzpicture\}',
        _clean_tikz_block,
        latex,
        flags=re.DOTALL,
    )
    
    # ── 3. Pulizia aggressiva (se richiesta) ───────────────────────────────────
    if aggressive:
        logger.warning("Applicando pulizia TikZ aggressiva...")
        # Rimuovi SOLO i blocchi TikZ complessi problematici, ma preserva i grafici semplici
        complex_tikz_patterns = [
            r'\\begin\{tikzpicture\}.*?\\begin\{axis\}.*?\\end\{axis\}.*?\\end\{tikzpicture\}',  # pgfplots complessi
            r'\\begin\{tikzpicture\}.*?\\addplot.*?\\end\{tikzpicture\}',  # addplot complessi
            r'\\begin\{tikzpicture\}.*?\\draw.*?plot.*?\\end\{tikzpicture\}',  # plot complessi
            r'\\begin\{tikzpicture\}.*?\\node.*?at.*?\$.*?\$.*?\\end\{tikzpicture\}',  # nodi con coordinate matematiche
        ]
        
        # Prima controlla se ci sono grafici matematici semplici da preservare
        simple_graph_pattern = r'\\begin\{tikzpicture\}\[.*?\].*?\\draw.*?domain.*?\\end\{tikzpicture\}'
        simple_graphs = re.findall(simple_graph_pattern, latex, re.DOTALL | re.IGNORECASE)
        
        if simple_graphs:
            logger.info(f"Trovati {len(simple_graphs)} grafici matematici semplici da preservare")
            # Preserva i grafici semplici, rimuovi solo quelli complessi
            for pattern in complex_tikz_patterns:
                matches = re.findall(pattern, latex, re.DOTALL | re.IGNORECASE)
                if matches:
                    logger.info(f"Rimossi {len(matches)} blocchi TikZ complessi")
                    latex = re.sub(pattern, '[Grafico complesso rimosso]', latex, flags=re.DOTALL | re.IGNORECASE)
        else:
            # Se non ci sono grafici semplici, procedi con la rimozione aggressiva
            for pattern in complex_tikz_patterns:
                matches = re.findall(pattern, latex, re.DOTALL | re.IGNORECASE)
                if matches:
                    logger.info(f"Rimossi {len(matches)} blocchi TikZ complessi")
                    latex = re.sub(pattern, '[Grafico complesso rimosso]', latex, flags=re.DOTALL | re.IGNORECASE)
        
        # Rimuovi pacchetti TikZ problematici solo se non ci sono grafici semplici
        if not simple_graphs:
            tikz_packages = [
                r'\\usepackage\{tikz\}',
                r'\\usepackage\{pgfplots\}',
                r'\\usetikzlibrary\{[^}]*\}',
                r'\\pgfplotsset\{[^}]*\}',
            ]
            
            for package in tikz_packages:
                latex = re.sub(package, '', latex, flags=re.IGNORECASE)
                logger.info(f"Rimosso package TikZ: {package}")
        else:
            logger.info("Preservati pacchetti TikZ per i grafici matematici")
    
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


def fix_table_width(latex: str) -> str:
    """
    Sistema le tabelle che escono dai margini aggiungendo adjustbox e righe vuote.
    """
    logger.info("Applicando fix per larghezza tabelle...")
    
    # Prima di tutto: assicura che ci sia una riga vuota prima di ogni \begin{tabular}
    def add_line_breaks_before_tables(text):
        # Pattern per trovare \begin{tabular} non preceduti da riga vuota
        # Controlla se non c'è già \n\n prima del \begin{tabular}
        tabular_pattern = r'(?:[^\n])?\n\\begin\{tabular\}'
        
        def replace_with_linebreak(match):
            # Aggiungi \n\n prima del \begin{tabular}
            return '\n\n\\begin{tabular}'
        
        # Applica più volte per catturare tutti i casi
        fixed_text = re.sub(tabular_pattern, replace_with_linebreak, text)
        
        # Secondo passaggio: gestisce \begin{tabular} a inizio riga senza \n\n prima
        tabular_start_pattern = r'^\s*\\begin\{tabular\}'
        lines = fixed_text.split('\n')
        for i, line in enumerate(lines):
            if re.match(tabular_start_pattern, line):
                # Controlla se la riga precedente è vuota
                if i > 0 and lines[i-1].strip() != '':
                    # Inserisci riga vuota prima
                    lines.insert(i, '')
                    i += 1  # Salta la riga appena inserita
        
        return '\n'.join(lines)
    
    # Applica il fix delle righe vuote
    latex_with_breaks = add_line_breaks_before_tables(latex)
    
    # Pattern più robusto per trovare ambienti tabular
    # Gestisce anche casi con \centering o altri elementi
    tabular_patterns = [
        r'\\begin\{tabular\}([^}]*)\}(.*?)\\end\{tabular\}',
        r'\\begin\{tabular\*\}([^}]*)\}(.*?)\\end\{tabular\*\}',
        r'\\begin\{array\}([^}]*)\}(.*?)\\end\{array\}',
    ]
    
    def wrap_tabular(match, env='tabular'):
        col_spec = match.group(1)
        content = match.group(2)
        # Avvolgi la tabella con adjustbox per limitare la larghezza
        return f'\\adjustbox{{max width={{\\textwidth}}}}{{\\begin{{{env}}}{col_spec}}}{content}\\end{{{env}}}}}'
    
    def fix_latex_tables(text):
        # Prima controlla se c'è già adjustbox in questa sezione
        if '\\adjustbox' in text:
            return text
            
        fixed_text = text
        for pattern in tabular_patterns:
            def replacer(match):
                env = 'tabular' if 'tabular' in match.group(0) else 'array'
                return wrap_tabular(match, env)
            
            # Applica il pattern
            new_text = re.sub(pattern, replacer, fixed_text, flags=re.DOTALL)
            if new_text != fixed_text:
                fixed_text = new_text
                logger.info(f"✓ Tabella sistemata con adjustbox")
        
        return fixed_text
    
    # Applica il fix
    latex_fixed = fix_latex_tables(latex_with_breaks)
    
    # Secondo passaggio: gestisce tabelle dentro \centering o \begin{center}
    center_pattern = r'\\begin\{center\}(.*?)\\end\{center\}'
    
    def fix_center_tables(text):
        def replace_center(match):
            center_content = match.group(1)
            # Applica il fix alle tabelle dentro il center
            fixed_center = fix_latex_tables(center_content)
            if fixed_center != center_content:
                return f'\\begin{{center}}{fixed_center}\\end{{center}}'
            return match.group(0)
        
        return re.sub(center_pattern, replace_center, text, flags=re.DOTALL)
    
    latex_fixed = fix_center_tables(latex_fixed)
    
    # Terzo passaggio: gestisce casi con \centering\par
    centering_pattern = r'(\\centering\s*\\par.*?)(\\begin\{tabular\}.*?\\end\{tabular\})'
    
    def fix_centering_tables(text):
        def replace_centering(match):
            prefix = match.group(1)
            tabular = match.group(2)
            # Applica adjustbox alla tabella
            fixed_tabular = fix_latex_tables(tabular)
            return prefix + fixed_tabular
        
        return re.sub(centering_pattern, replace_centering, text, flags=re.DOTALL)
    
    latex_fixed = fix_centering_tables(latex_fixed)
    
    if latex_fixed != latex:
        logger.info("✓ Tabelle sistemate con adjustbox e righe vuote")
    else:
        logger.info("✓ Nessuna tabella da sistemare")
    
    return latex_fixed


# ── COMPILAZIONE PDF ───────────────────────────────────────────────────────────

def compila_pdf(codice_latex: str) -> tuple[bytes | None, str | None]:
    """
    Compila codice LaTeX in PDF usando pdflatex.
    Restituisce (pdf_bytes, error_message).
    """
    import tempfile
    import subprocess
    import os
    import logging
    import time
    
    logger = logging.getLogger(__name__)
    
    # 🔥 DEBUG: Stampa il LaTeX completo che viene compilato
    print(f"🔥 DEBUG compila_pdf: LaTeX da compilare ({len(codice_latex)} caratteri)")
    print(f"📄 Prime 300 caratteri del LaTeX: {codice_latex[:300]}")
    print(f"📄 Ultimi 300 caratteri del LaTeX: {codice_latex[-300:]}")
    print(f"🔍 Contiene \\begin{{document}}: {codice_latex.count('\\begin{document}')} volte")
    print(f"🔍 Contiene \\end{{document}}: {codice_latex.count('\\end{document}')} volte")
    print(f"🔍 Contiene \\documentclass: {codice_latex.count('\\documentclass')} volte")
    
    # Verifica che pdflatex sia disponibile
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tex_path = os.path.join(tmpdir, "v.tex")
            pdf_path = os.path.join(tmpdir, "v.pdf")

            logger.info(f"Scrittura file LaTeX in: {tex_path}")
            with open(tex_path, "w", encoding="utf-8") as f:
                f.write(codice_latex)
            logger.info("✓ File LaTeX scritto")

            logger.info("Avvio compilazione pdflatex...")
            result = subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", "-output-directory", tmpdir, "-shell-escape", "-disable-installer", tex_path],
                capture_output=True,
                text=True,
                timeout=30
            )

            logger.info(f"Return code: {result.returncode}")
            
            # Controlla se esiste il file log
            log_path = os.path.join(tmpdir, "v.log")
            if os.path.exists(log_path):
                with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                    log_content = f.read()
                    logger.info(f"Contenuto log LaTeX (ultimi 1000 char): {log_content[-1000:]}")

            # Controlla se il PDF è stato generato anche con warnings
            if os.path.exists(pdf_path):
                pdf_size = os.path.getsize(pdf_path)
                if pdf_size > 1000:  # PDF valido (almeno 1KB)
                    logger.info(f"✓ PDF compilato con successo - Dimensione: {pdf_size} bytes")
                    
                    # Se c'è return code != 0 ma il PDF esiste, sono solo warning
                    if result.returncode != 0:
                        logger.warning(f"⚠️ Warnings MiKTeX ignorati - PDF generato comunque (return code: {result.returncode})")
                        # Log dei warnings ma non bloccante
                        stdout_lines = result.stdout.split('\n')[-5:]
                        stderr_lines = result.stderr.split('\n')[-3:]
                        logger.warning(f"⚠️ Warnings: {stdout_lines}")
                        logger.warning(f"⚠️ Warnings: {stderr_lines}")
                        
                        # 🔥 FIX: Ritorna il PDF anche con warning MiKTeX
                        return open(pdf_path, "rb").read(), f"Warning MiKTeX: {result.stderr}"
                    
                    return open(pdf_path, "rb").read(), None
                else:
                    logger.error(f"✗ PDF generato ma troppo piccolo: {pdf_size} bytes")
            
            # Se arriviamo qui, il PDF non esiste o è troppo piccolo
            if result.returncode != 0:
                logger.error(f"✗ Errore pdflatex (codice {result.returncode}): {result.stderr}")
                # Log dettagliato dell'output per debugging
                stdout_lines = result.stdout.split('\n')[-10:]  # Ultime 10 linee
                stderr_lines = result.stderr.split('\n')[-5:]   # Ultime 5 linee
                logger.error(f"✗ Ultime linee stdout: {stdout_lines}")
                logger.error(f"✗ Ultime linee stderr: {stderr_lines}")
                
                # Controlla errori comuni
                if "Emergency stop" in result.stdout:
                    logger.error("✗ Errore grave: Emergency stop")
                elif "Fatal error" in result.stdout:
                    logger.error("✗ Errore fatale LaTeX")
                
                return None, f"Errore durante la compilazione LaTeX: {result.stderr}"
            else:
                return None, "PDF non generato per motivi sconosciuti"

    except subprocess.TimeoutExpired:
        return None, "Timeout durante la compilazione LaTeX"
    except FileNotFoundError:
        return None, "pdflatex non trovato. Assicurati che MiKTeX sia installato"
    except Exception as e:
        return None, f"Errore imprevisto durante la compilazione: {str(e)}"


def pdf_to_images_bytes(pdf_bytes: bytes) -> tuple[list[bytes] | None, str | None]:
    """
    Converte PDF bytes in una lista di immagini PNG bytes.
    Restituisce (list_of_images, error_message).
    """
    logger = logging.getLogger(__name__)
    
    if not pdf_bytes:
        return None, "PDF bytes vuoti"
    
    # Tentativo 1: pdf2image
    try:
        from pdf2image import convert_from_bytes as cfb
        pages = cfb(pdf_bytes, dpi=150)
        out = []
        for p in pages:
            buf = io.BytesIO()
            p.save(buf, "PNG")
            out.append(buf.getvalue())
        logger.info(f"✅ PDF convertito in {len(out)} immagini con pdf2image")
        return out, None
    except Exception as e:
        logger.warning(f"pdf2image fallito: {e}")
    
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
            out = []
            for img in imgs:
                with open(os.path.join(d, img), "rb") as f:
                    out.append(f.read())
            logger.info(f"✅ PDF convertito in {len(out)} immagini con pdftoppm")
            return out, None
    except Exception as e:
        logger.warning(f"pdftoppm fallito: {e}")
    
    return None, "Impossibile convertire PDF in immagini"
