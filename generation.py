# generation.py
# Contiene tutta la logica di generazione AI.
# Nessuna dipendenza da Streamlit — la progress bar viene aggiornata
# tramite il callback on_progress(testo: str).
#
# NUOVO: genera_verifica_streaming() — genera il corpo con streaming visibile
# e restituisce i blocchi esercizi uno a uno tramite on_block(idx, latex_blocco).

import re
import time
import logging

logger = logging.getLogger(__name__)

from prompts import (
    prompt_titolo,
    prompt_corpo_verifica,
    prompt_controllo_qualita,
    prompt_versione_b,
    prompt_versione_ridotta,
    prompt_soluzioni,
    prompt_analisi_documento,
    prompt_variante_rapida,
)

# prompt_rigenera_blocco potrebbe non essere ancora in prompts.py (deploy graduale)
try:
    from prompts import prompt_rigenera_blocco
except ImportError:
    def prompt_rigenera_blocco(
        materia: str,
        blocco_latex: str,
        istruzione: str,
        mostra_punteggi: bool,
    ) -> str:
        punti_nota = (
            "Mantieni il formato (X pt) su ogni \\item come nell'originale. "
            "Non è necessario che i punti sommino a un totale preciso — verranno ribilanciati automaticamente."
            if mostra_punteggi
            else "NON inserire punteggi (X pt)."
        )
        return (
            f"Sei un docente esperto di {materia} e LaTeX. "
            f"Devi rigenerare SOLO questo esercizio della verifica, secondo l'istruzione del docente.\n\n"
            f"ESERCIZIO ORIGINALE:\n{blocco_latex}\n\n"
            f"ISTRUZIONE DEL DOCENTE:\n{istruzione}\n\n"
            f"REGOLE:\n"
            f"- Restituisci SOLO il blocco \\subsection*{{...}} con il nuovo esercizio.\n"
            f"- Mantieni la stessa struttura LaTeX (\\subsection*, \\begin{{enumerate}}, \\item[a)], ecc.).\n"
            f"- Ogni esercizio deve avere ALMENO un \\item[a)] con la sua richiesta.\n"
            f"- {punti_nota}\n"
            f"- NON includere preambolo, \\documentclass o \\begin{{document}}.\n"
            f"- NON aggiungere commenti o spiegazioni fuori dal LaTeX.\n"
            f"- TERMINA il blocco con una riga vuota (non con \\end{{document}}).\n"
            f"OUTPUT: SOLO codice LaTeX del blocco esercizio."
        )
from latex_utils import (
    compila_pdf, inietta_griglia, riscala_punti, riscala_punti_custom,
    fix_items_environment, rimuovi_vspace_corpo, pulisci_corpo_latex,
    rimuovi_punti_subsection, pdf_to_images_bytes,
    extract_blocks, reconstruct_latex, extract_corpo, extract_preambolo,
    parse_pts_from_block_body, valida_totale, riscala_single_block,
    parse_items_from_block, apply_item_pts_to_body,
    prepara_esercizi_aperti, conta_punti_latex,
    migliora_spaziatura_sottopunti, clean_tikz_spoilers, normalizza_labels_numerici, semplifica_item_singoli, limita_altezza_grafici, assicura_punti_visibili, aggiungi_spaziatura_grafici_tabelle,
)


# ── HELPER INTERNO ────────────────────────────────────────────────────────────────

def _validate_content_quality(corpo: str, materia: str, num_esercizi: int, punti_totali: int) -> float:
    """
    Valuta la qualità del contenuto generato con score 0-1.
    Controlla: coerenza, completezza, formato LaTeX, punteggi.
    """
    score = 0.0
    max_score = 5.0
    
    # 1. Controllo numero esercizi
    esercizi_trovati = len(re.findall(r"\\subsection\*", corpo))
    if esercizi_trovati == num_esercizi:
        score += 1.0
    elif 0.5 * num_esercizi <= esercizi_trovati <= 1.5 * num_esercizi:
        score += 0.5
    
    # 2. Controllo struttura LaTeX
    if "\\begin{enumerate}" in corpo and "\\item" in corpo:
        score += 1.0
    elif "\\item" in corpo:
        score += 0.5
    
    # 3. Controllo punteggi (se richiesti)
    if punti_totali > 0:
        punti_matches = re.findall(r"\(\s*(\d+(?:[.,]\d+)?)\s*pt\s*\)", corpo)
        if punti_matches:
            somma_punti = sum(float(p.replace(',', '.')) for p in punti_matches)
            if abs(somma_punti - punti_totali) <= 1:
                score += 1.0
            elif abs(somma_punti - punti_totali) <= 3:
                score += 0.5
    
    # 4. Controllo coerenza minima
    if len(corpo.strip()) > 200:  # Lunghezza minima
        score += 1.0
    elif len(corpo.strip()) > 100:
        score += 0.5
    
    # 5. Controllo errori LaTeX gravi
    errori_gravi = ["\\begin{document}", "\\end{document}", "\\documentclass"]
    if not any(err in corpo for err in errori_gravi):
        score += 1.0
    
    return score / max_score


def _prompt_controllo_qualita_migliorato(
    materia: str, difficolta: str, corpo: str, mostra_punteggi: bool, punti_totali: int
) -> str:
    """
    Prompt di controllo qualità migliorato con focus su correzioni specifiche.
    """
    return (
        f"Sei un docente esperto di {materia}. Analizza e correggi questa verifica.\n\n"
        f"MATERIA: {materia}\n"
        f"DIFFICOLTÀ: {difficolta}\n"
        f"PUNTI TOTALI: {punti_totali}\n"
        f"PUNTEGGI VISIBILI: {'Sì' if mostra_punteggi else 'No'}\n\n"
        f"VERIFICA DA CORREGGERE:\n{corpo}\n\n"
        f"PRIORITÀ DI CORREZIONE:\n"
        f"1. Verifica che ogni esercizio abbia senso e sia completo\n"
        f"2. Correggi errori di grammatica e sintassi\n"
        f"3. Assicura che i punteggi siano corretti e sommino a {punti_totali}\n"
        f"4. Verifica che la struttura LaTeX sia corretta\n"
        f"5. Elimina esercizi ripetitivi o troppo simili\n\n"
        f"RESTITUISCI SOLO il LaTeX corretto, senza commenti o spiegazioni.\n"
    )


def _safe_generate_improved(model, prompt_or_parts, step_name: str = "API", retries: int = 3, 
                           incremental: bool = False) -> any:
    """
    Versione migliorata di _safe_generate con retry incrementale e errori specifici.
    """
    last_exc: Exception | None = None
    for attempt in range(1 + retries):
        try:
            if attempt > 1 and incremental:
                # Aggiungi istruzioni di correzione basate sull'errore precedente
                if isinstance(prompt_or_parts, list):
                    prompt_or_parts[0] += f"\n\nATTENZIONE: Tentativo {attempt}/{retries+1}. "
                    if "timeout" in str(last_exc).lower():
                        prompt_or_parts[0] += "Sii più conciso e vai dritto al punto."
                    elif "quota" in str(last_exc).lower():
                        prompt_or_parts[0] += "Riduci la complessità della risposta."
                    elif "content" in str(last_exc).lower():
                        prompt_or_parts[0] += "Evita contenuti sensibili o inappropriati."
            
            return model.generate_content(prompt_or_parts)
        except Exception as e:
            last_exc = e
            if attempt < retries:
                wait_time = 2 ** attempt  # 2s, 4s, 8s
                logger.warning(f"{step_name} tentativo {attempt} fallito: {e}. Retry in {wait_time}s...")
                time.sleep(wait_time)
    
    # Messaggio di errore specifico
    error_msg = f"{step_name}: {last_exc}"
    if "timeout" in str(last_exc).lower():
        error_msg += " (Suggerimento: ridurre la complessità della richiesta)"
    elif "quota" in str(last_exc).lower():
        error_msg += " (Suggerimento: provare un modello più leggero)"
    elif "content" in str(last_exc).lower():
        error_msg += " (Suggerimento: riformulare la richiesta)"
    
    raise RuntimeError(error_msg) from last_exc


def _pulisci_risposta(testo: str) -> str:
    return testo.replace("```latex", "").replace("```", "").strip()


def _safe_generate(model, prompt_or_parts, step_name: str = "API", retries: int = 2):
    """
    Wrapper che mantiene compatibilità ma usa la versione migliorata.
    """
    return _safe_generate_improved(model, prompt_or_parts, step_name, retries, incremental=True)


def _testo_to_latex_body(testo: str) -> str:
    body = ""
    for line in testo.split("\n"):
        ls = line.strip()
        if not ls:
            body += "\n\\vspace{0.15cm}\n"
        elif re.match(r"^#{1,3}\s", ls):
            heading = re.sub(r"^#+\s*", "", ls)
            body += f"\n\\subsection*{{{heading}}}\n"
        elif re.match(r"^Esercizio\s+\d+", ls, re.IGNORECASE):
            body += f"\n\\subsection*{{{ls}}}\n"
        elif re.match(r"^[a-z]\)\s", ls):
            body += f"\\noindent\\textbf{{{ls[:2]}}} {ls[2:].strip()}\n\n"
        else:
            body += ls + "\n"
    return body


def _costruisci_preambolo(
    materia: str,
    titolo_clean: str,
    titolo_variante: str,   # es. "Versione A", "Versione B", "" se nessuna
    e_mat: bool,
) -> str:
    nota_bes = "Svolgere tutti gli esercizi mostrando i passaggi."
    titolo_header = (
        f"Verifica di {materia}: {titolo_clean}"
        + (f" — {titolo_variante}" if titolo_variante else "")
    )
    pgfplots_pkg = (
        "\\usepackage{pgfplots}\n\\pgfplotsset{compat=1.18}\n\\usepackage{tikz}"
        if e_mat else ""
    )
    return (
        f"\\documentclass[12pt,a4paper]{{article}}\n"
        f"\\usepackage[utf8]{{inputenc}}\n"
        f"\\usepackage[italian]{{babel}}\n"
        f"\\usepackage{{amsmath,amsfonts,amssymb,geometry,array,multicol,enumerate,adjustbox,wasysym}}\n"
        f"{pgfplots_pkg}\n"
        f"\\geometry{{margin=1.5cm}}\n"
        f"\\setlength{{\\parskip}}{{3pt plus1pt minus1pt}}\n"
        f"\\pagestyle{{empty}}\n"
        f"\\begin{{document}}\n"
        f"\\begin{{center}}\n"
        f"  \\textbf{{\\large {titolo_header}}} \\\\\n"
        f"  \\vspace{{0.3cm}}\n"
        f"  \\small \\textbf{{Nome:}} \\underline{{\\hspace{{6cm}}}} "
        f"\\quad \\textbf{{Classe e Data:}} \\underline{{\\hspace{{4cm}}}} \\\\\n"
        f"  \\vspace{{0.3cm}}\n"
        f"  \\textit{{\\small {nota_bes}}}\n"
        f"\\end{{center}}\n"
    ), titolo_header


def _rimuovi_tutti_punteggi(latex: str) -> str:
    """
    Rimozione deterministica di tutti i punteggi (X pt) dal LaTeX.
    Usata come guardia quando mostra_punteggi=False, a prescindere da
    ciò che il modello AI ha generato.
    """
    # Rimuovi pattern come (5 pt), (10 pt), (10 punti), etc. — inline
    latex = re.sub(r"\s*\(\s*\d+\s*(?:pt|punt(?:i|o)?|p\.)\s*\)", "", latex)
    return latex


def _assembla_e_compila(
    preambolo: str,
    corpo: str,
    mostra_punteggi: bool,
    punti_totali: int,
    con_griglia: bool,
) -> tuple[str, bytes | None]:
    """
    Assembla preambolo + corpo, applica le trasformazioni post-processing,
    compila in PDF. Restituisce (latex_finale, pdf_bytes_o_None).
    """
    latex = preambolo + clean_tikz_spoilers(corpo)
    latex = fix_items_environment(latex)
    latex = normalizza_labels_numerici(latex)   # 1) 2) 3) → a) b) c)
    latex = semplifica_item_singoli(latex)       # enumerate 1 solo item → testo diretto
    latex = migliora_spaziatura_sottopunti(latex) # migliora spaziatura tra sottopunti
    latex = aggiungi_spaziatura_grafici_tabelle(latex) # aggiunge spaziatura prima di grafici/tabelle
    latex = limita_altezza_grafici(latex)       # limita altezza dei grafici
    latex = rimuovi_vspace_corpo(latex)
    if mostra_punteggi:
        corpo_pulito = extract_corpo(latex)
        corpo_con_punti = assicura_punti_visibili(corpo_pulito, punti_totali)
        latex = preambolo + corpo_con_punti
        latex = rimuovi_punti_subsection(latex)
        # ── CRITICO: prima di riscala_punti, inietta placeholder pts
        # negli esercizi senza \item (domande aperte, esercizi singoli).
        # Senza questo step quei blocchi non hanno (N pt) → riscala_punti
        # li ignora → griglia mostra '—' e il totale è sbagliato.
        latex = prepara_esercizi_aperti(latex, punti_totali)
        latex = riscala_punti(latex, punti_totali)
    else:
        # Guardia deterministica: rimuove punteggi residui anche se l'AI li ha inseriti
        latex = _rimuovi_tutti_punteggi(latex)

    latex_final = inietta_griglia(latex, punti_totali) if (con_griglia and mostra_punteggi) else latex
    
    # Tentativo di compilazione con diagnostica migliorata
    pdf, error_msg = compila_pdf(latex_final)
    
    if pdf is None:
        logger.error(f"Compilazione PDF fallita: {error_msg}")
        
        # Analisi dell'errore per fornire diagnostica specifica
        if "tikz" in str(error_msg).lower():
            logger.warning("Errore TikZ rilevato, provo a rimuovere elementi grafici complessi")
            latex_simplified = clean_tikz_spoilers(latex_final, aggressive=True)
            pdf, _ = compila_pdf(latex_simplified)
            if pdf:
                logger.info("PDF generato con TikZ semplificato")
                return latex_simplified, pdf
        
        if "table" in str(error_msg).lower() or "tabular" in str(error_msg).lower():
            logger.warning("Errore tabella rilevato, provo a semplificare le tabelle")
            latex_no_tables = re.sub(r'\\begin\{tabular\}.*?\\end\{tabular\}', '[Tabella]', latex_final, flags=re.DOTALL)
            pdf, _ = compila_pdf(latex_no_tables)
            if pdf:
                logger.info("PDF generato con tabelle semplificate")
                return latex_no_tables, pdf
        
        # Fallback senza griglia
        if con_griglia and mostra_punteggi:
            logger.warning("Tento fallback senza griglia di punteggi")
            pdf, _ = compila_pdf(latex)
            if pdf:
                logger.info("PDF generato senza griglia")
                return latex, pdf
        
        # Ultimo fallback: versione minimale
        logger.warning("Tento versione minimale del LaTeX")
        latex_minimal = _crea_versione_minimale(latex_final, error_msg)
        pdf, _ = compila_pdf(latex_minimal)
        if pdf:
            logger.info("PDF generato con versione minimale")
            return latex_minimal, pdf
        
        logger.error("Tutti i tentativi di compilazione falliti")
        return latex_final, None

    return latex_final, pdf


def _crea_versione_minimale(latex: str, errore: str) -> str:
    """
    Crea una versione minimale del LaTeX quando la compilazione fallisce.
    """
    try:
        # Estrai il corpo principale
        corpo_match = re.search(r'\\begin\{document\}(.*?)\\end\{document\}', latex, re.DOTALL)
        if corpo_match:
            corpo = corpo_match.group(1)
        else:
            corpo = latex
        
        # Rimuovi elementi problematici
        corpo_semplificato = re.sub(r'\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}', '[Grafico]', corpo, flags=re.DOTALL)
        corpo_semplificato = re.sub(r'\\begin\{tabular\}.*?\\end\{tabular\}', '[Tabella]', corpo_semplificato, flags=re.DOTALL)
        corpo_semplificato = re.sub(r'\\begin\{table\}.*?\\end\{table\}', '', corpo_semplificato, flags=re.DOTALL)
        
        # Ricostruisci il LaTeX minimale
        preambolo_minimale = (
            "\\documentclass[12pt,a4paper]{article}\n"
            "\\usepackage[utf8]{inputenc}\n"
            "\\usepackage[italian]{babel}\n"
            "\\usepackage{amsmath,amsfonts,amssymb}\n"
            "\\geometry{margin=2cm}\n"
            "\\pagestyle{empty}\n"
            "\\begin{document}\n"
        )
        
        return preambolo_minimale + corpo_semplificato + "\n\\end{document}"
        
    except Exception as e:
        logger.error(f"Errore nella creazione versione minimale: {e}")
        return (
            "\\documentclass[12pt,a4paper]{article}\n"
            "\\usepackage[utf8]{inputenc}\n"
            "\\usepackage[italian]{babel}\n"
            "\\begin{document}\n"
            f"\\textbf{{Errore di compilazione}}\\newline\\newline"
            f"La verifica non è stata compilata a causa di: {errore[:200]}...\n"
            "\\end{document}"
        )


def _tronca_al_numero_giusto(corpo: str, num_esercizi: int) -> str:
    """Rimuove i blocchi \\subsection* in eccesso."""
    _sub_pat = re.escape(chr(92) + "subsection*{")
    splits = re.split(f"({_sub_pat})", corpo)
    n_blocchi = (len(splits) - 1) // 2
    if n_blocchi <= num_esercizi:
        return corpo
    testa = splits[0]
    parti = []
    for b in range(num_esercizi):
        parti.append(splits[1 + b * 2])
        parti.append(splits[2 + b * 2])
    troncato = testa + "".join(parti)
    _end_pat = re.escape(chr(92) + "end{document}")
    troncato = re.sub(_end_pat + r".*$", "", troncato, flags=re.DOTALL).rstrip()
    return troncato + "\n" + chr(92) + "end{document}"


def _split_blocchi(corpo: str) -> list[str]:
    """
    Divide il corpo LaTeX in blocchi, uno per ogni \\subsection*.
    Restituisce (prefix, lista_blocchi) dove ogni blocco inizia con \\subsection*{...}.
    """
    # re.escape garantisce che il backslash letterale venga cercato correttamente
    _pattern = f"(?={re.escape(chr(92) + 'subsection*{')})"
    parts = re.split(_pattern, corpo)

    _marker = chr(92) + "subsection*{"   # stringa: \subsection*{
    blocchi = []
    prefix = ""
    for p in parts:
        if p.strip().startswith(_marker):
            blocchi.append(p)
        else:
            prefix += p
    return prefix, blocchi


def _assembla_corpo_da_blocchi(blocchi: list[str]) -> str:
    """Riassembla i blocchi in un corpo LaTeX completo."""
    corpo = "\n".join(b.rstrip() for b in blocchi)
    # Rimuovi \end{document} residui dai singoli blocchi, poi aggiungi alla fine
    _end_doc = re.escape(chr(92) + "end{document}")
    corpo = re.sub(_end_doc, "", corpo).rstrip()
    return corpo + "\n" + chr(92) + "end{document}"


# ── FUNZIONE STREAMING PER BLOCCO ─────────────────────────────────────────────────

def genera_corpo_streaming(
    model,
    materia: str,
    argomento: str,
    calibrazione: str,
    durata: str,
    num_esercizi: int,
    punti_totali: int,
    mostra_punteggi: bool,
    con_griglia: bool,
    note_generali: str,
    istruzioni_esercizi: str,
    immagini_esercizi: list,
    file_ispirazione=None,
    titolo_header: str = "",
    preambolo: str = "",
    e_mat: bool = False,
    mathpix_context: str | None = None,
    on_token=None,      # callback(token: str) -> None  chiamato per ogni chunk testo
    on_done=None,       # callback(corpo_latex: str) -> None  chiamato al completamento
) -> str:
    """
    Genera il corpo della verifica con streaming token per token.
    Chiama on_token(chunk) per ogni frammento di testo in arrivo.
    Al completamento chiama on_done(corpo_latex) e ritorna il corpo.
    """
    inp = [
        prompt_corpo_verifica(
            materia, argomento, calibrazione, durata,
            num_esercizi, punti_totali, mostra_punteggi,
            con_griglia, note_generali, istruzioni_esercizi,
            e_mat, titolo_header, preambolo,
            mathpix_context=mathpix_context,
        )
    ]
    if file_ispirazione:
        inp.append({"mime_type": file_ispirazione.type, "data": file_ispirazione.getvalue()})
        inp[0] += "\nPrendi spunto dal file allegato per stile e livello."
    for im in immagini_esercizi:
        inp.append({"mime_type": im["mime_type"], "data": im["data"]})
        inp[0] += f"\nUsa l'immagine come riferimento per l'Esercizio {im['idx']}."

    testo_completo = ""
    try:
        response = model.generate_content(inp, stream=True)
        for chunk in response:
            if chunk.text:
                testo_completo += chunk.text
                if on_token:
                    on_token(chunk.text)
    except Exception:
        # Fallback senza streaming
        response = model.generate_content(inp)
        testo_completo = response.text
        if on_token:
            on_token(testo_completo)

    corpo = pulisci_corpo_latex(_pulisci_risposta(testo_completo))
    if on_done:
        on_done(corpo)
    return corpo


def rigenera_singolo_blocco(
    model,
    materia: str,
    blocco_latex: str,
    istruzione: str,
    mostra_punteggi: bool,
    on_token=None,
) -> str:
    """
    Rigenera un singolo blocco \\subsection* secondo l'istruzione.
    Ritorna il nuovo blocco latex.
    """
    testo_completo = ""
    try:
        response = model.generate_content(
            prompt_rigenera_blocco(materia, blocco_latex, istruzione, mostra_punteggi),
            stream=True,
        )
        for chunk in response:
            if chunk.text:
                testo_completo += chunk.text
                if on_token:
                    on_token(chunk.text)
    except Exception:
        response = model.generate_content(
            prompt_rigenera_blocco(materia, blocco_latex, istruzione, mostra_punteggi)
        )
        testo_completo = response.text
        if on_token:
            on_token(testo_completo)

    return pulisci_corpo_latex(_pulisci_risposta(testo_completo))


# ── FUNZIONE PRINCIPALE ───────────────────────────────────────────────────────────

def genera_verifica(
    model,
    materia: str,
    argomento: str,
    difficolta: str,
    calibrazione: str,
    durata: str,
    num_esercizi: int,
    punti_totali: int,
    mostra_punteggi: bool,
    con_griglia: bool,
    doppia_fila: bool,
    bes_dsa: bool,
    perc_ridotta: int | None,
    bes_dsa_b: bool,
    genera_soluzioni: bool,
    note_generali: str,
    istruzioni_esercizi: str,   # stringa da costruisci_prompt_esercizi()
    immagini_esercizi: list,    # lista di {'idx', 'data', 'mime_type'}
    file_ispirazione=None,      # oggetto file Streamlit o None
    mathpix_context: str | None = None,   # LaTeX estratto da Mathpix OCR
    on_progress=None,           # callback(testo: str) -> None
) -> dict:
    """
    Genera la verifica e restituisce un dizionario con le chiavi:
        'titolo'  : str
        'A'       : {'latex': str, 'pdf': bytes|None}
        'B'       : {'latex': str, 'pdf': bytes|None}   (se doppia_fila)
        'R'       : {'latex': str, 'pdf': bytes|None}   (se bes_dsa)
        'RB'      : {'latex': str, 'pdf': bytes|None}   (se bes_dsa_b)
        'S'       : {'latex': str, 'pdf': bytes|None, 'testo': str}  (se genera_soluzioni)
    """

    def _avanza(testo: str):
        if on_progress:
            on_progress(testo)

    e_mat = any(
        k in materia.lower()
        for k in ["matem", "fis", "chim", "inform", "elettr", "meccan"]
    )

    risultato = {
        "titolo": "",
        "A": {"latex": "", "pdf": None},
        "B": {"latex": "", "pdf": None},
        "R": {"latex": "", "pdf": None},
        "RB": {"latex": "", "pdf": None},
        "S": {"latex": "", "pdf": None, "testo": ""},
    }

    # ── 1. TITOLO ─────────────────────────────────────────────────────────────
    _avanza("✍️  Elaborazione titolo…")
    resp_titolo = _safe_generate(model, prompt_titolo(materia, argomento), "Generazione titolo")
    titolo_clean = resp_titolo.text.strip().strip('"').strip("'").strip()
    if not titolo_clean:
        titolo_clean = argomento.strip()
    risultato["titolo"] = titolo_clean

    # ── 2. PREAMBOLO FILA A ───────────────────────────────────────────────────
    titolo_variante_a = "Versione A" if doppia_fila else ""
    preambolo_a, titolo_header_a = _costruisci_preambolo(
        materia, titolo_clean, titolo_variante_a, e_mat
    )

    # ── 3. CORPO ESERCIZI (FILA A) ────────────────────────────────────────────
    _avanza("🧠  Generazione esercizi in corso…")

    inp = [
        prompt_corpo_verifica(
            materia, argomento, calibrazione, durata,
            num_esercizi, punti_totali, mostra_punteggi,
            con_griglia, note_generali, istruzioni_esercizi,
            e_mat, titolo_header_a, preambolo_a,
            mathpix_context=mathpix_context,
        )
    ]
    if file_ispirazione:
        inp.append({"mime_type": file_ispirazione.type, "data": file_ispirazione.getvalue()})
        inp[0] += "\nPrendi spunto dal file allegato per stile e livello."
    for im in immagini_esercizi:
        inp.append({"mime_type": im["mime_type"], "data": im["data"]})
        inp[0] += f"\nUsa l'immagine come riferimento per l'Esercizio {im['idx']}."

    ra = _safe_generate(model, inp, "Generazione esercizi")
    corpo_a = pulisci_corpo_latex(_pulisci_risposta(ra.text))

    # ── 4. CONTROLLO QUALITÀ MIGLIORATO ────────────────────────────────────────────
    _avanza("🔎  Controllo qualità e validazione contenuto…")
    
    # Validazione semantica del contenuto generato
    validation_score = _validate_content_quality(corpo_a, materia, num_esercizi, punti_totali)
    logger.info(f"Score validazione contenuto: {validation_score}")
    
    # Salva il validation score nel risultato per tracking
    risultato["_validation_score"] = validation_score
    
    # Se il punteggio è basso, genera un nuovo contenuto
    if validation_score < 0.6:
        logger.warning("Qualità contenuto insufficiente, rigenerazione con prompt semplificato...")
        rc = _safe_generate(
            model,
            _prompt_controllo_qualita_migliorato(materia, difficolta, corpo_a, mostra_punteggi, punti_totali),
            "Controllo qualità migliorato",
        )
        corpo_corretto = pulisci_corpo_latex(_pulisci_risposta(rc.text))
        
        # Validazione del contenuto corretto
        new_score = _validate_content_quality(corpo_corretto, materia, num_esercizi, punti_totali)
        if new_score > validation_score:
            logger.info(f"Qualità migliorata: {validation_score} → {new_score}")
            corpo_a = corpo_corretto
        else:
            logger.warning("Il controllo qualità non ha migliorato il contenuto, mantengo l'originale")
    else:
        logger.info("Qualità contenuto accettabile, procedo con il controllo standard")
        rc = _safe_generate(
            model,
            prompt_controllo_qualita(materia, difficolta, corpo_a, mostra_punteggi, punti_totali),
            "Controllo qualità",
        )
        corpo_corretto = pulisci_corpo_latex(_pulisci_risposta(rc.text))

    n_orig = len(re.findall(r"\\subsection\*", corpo_a))
    n_corr = len(re.findall(r"\\subsection\*", corpo_corretto))
    # Accetta la versione QA solo se il conteggio blocchi rimane identico
    if corpo_corretto and n_corr == n_orig:
        corpo_a = corpo_corretto

    corpo_a = _tronca_al_numero_giusto(corpo_a, num_esercizi)
    _avanza("🖨️  Compilazione PDF…")
    latex_a, pdf_a = _assembla_e_compila(
        preambolo_a, corpo_a, mostra_punteggi, punti_totali, con_griglia
    )
    risultato["A"] = {"latex": latex_a, "pdf": pdf_a}

    # ── 6. VERIFICA RIDOTTA A ─────────────────────────────────────────────────
    if bes_dsa and perc_ridotta:
        _avanza("⛳ Generazione verifica ridotta…")
        rb_bes = _safe_generate(
            model,
            prompt_versione_ridotta(corpo_a, materia, perc_ridotta, mostra_punteggi, punti_totali),
            "Verifica ridotta A",
        )
        corpo_r = pulisci_corpo_latex(_pulisci_risposta(rb_bes.text))
        latex_r, pdf_r = _assembla_e_compila(
            preambolo_a, corpo_r, mostra_punteggi, punti_totali, con_griglia
        )
        risultato["R"] = {"latex": latex_r, "pdf": pdf_r}

    # ── 7. FILA B ─────────────────────────────────────────────────────────────
    corpo_b = ""
    preambolo_b = ""
    if doppia_fila:
        _avanza("📄  Generazione Versione B…")
        rb = _safe_generate(
            model,
            prompt_variante_rapida(corpo_a, materia),
            "Variante B",
        )
        corpo_b = pulisci_corpo_latex(_pulisci_risposta(rb.text))

        preambolo_b, _ = _costruisci_preambolo(materia, titolo_clean, "Versione B", e_mat)

        _avanza("🖨️  PDF Versione B…")
        latex_b, pdf_b = _assembla_e_compila(
            preambolo_b, corpo_b, mostra_punteggi, punti_totali, con_griglia
        )
        risultato["B"] = {"latex": latex_b, "pdf": pdf_b}

        # ── 8. VERIFICA RIDOTTA B ─────────────────────────────────────────────
        if bes_dsa_b and perc_ridotta and corpo_b:
            _avanza("⛳ Generazione verifica ridotta Fila B…")
            rb_bes_b = _safe_generate(
                model,
                prompt_versione_ridotta(
                    corpo_b, materia, perc_ridotta, mostra_punteggi, punti_totali, "Fila B"
                ),
                "Verifica ridotta B",
            )
            corpo_rb = pulisci_corpo_latex(_pulisci_risposta(rb_bes_b.text))
            preambolo_rb, _ = _costruisci_preambolo(
                materia, titolo_clean, "Versione B Ridotta", e_mat
            )
            latex_rb, pdf_rb = _assembla_e_compila(
                preambolo_rb, corpo_rb, mostra_punteggi, punti_totali, con_griglia
            )
            risultato["RB"] = {"latex": latex_rb, "pdf": pdf_rb}

    # ── 9. SOLUZIONI ──────────────────────────────────────────────────────────
    if genera_soluzioni:
        _avanza("📋 Generazione soluzioni…")

        label_a = "Fila A" if doppia_fila else ""
        rs_a = _safe_generate(model, prompt_soluzioni(corpo_a, materia, label_a), "Soluzioni A")
        testo_sol_a = rs_a.text.strip()

        testo_sol_b = ""
        if doppia_fila and corpo_b:
            rs_b = _safe_generate(model, prompt_soluzioni(corpo_b, materia, "Fila B"), "Soluzioni B")
            testo_sol_b = rs_b.text.strip()

        titolo_sol = f"Soluzioni — {materia}: {titolo_clean}"
        latex_sol_body = ""
        if testo_sol_b:
            latex_sol_body += "\\section*{Fila A}\n"
        latex_sol_body += _testo_to_latex_body(testo_sol_a)
        if testo_sol_b:
            latex_sol_body += "\n\\newpage\n\\section*{Fila B}\n"
            latex_sol_body += _testo_to_latex_body(testo_sol_b)

        testo_completo = testo_sol_a
        if testo_sol_b:
            testo_completo += "\n\n---\n\n## Fila B\n\n" + testo_sol_b

        latex_sol = (
            f"\\documentclass[11pt,a4paper]{{article}}\n"
            f"\\usepackage[utf8]{{inputenc}}\n"
            f"\\usepackage[italian]{{babel}}\n"
            f"\\usepackage{{amsmath,amsfonts,amssymb,geometry}}\n"
            f"\\geometry{{margin=2cm}}\n"
            f"\\setlength{{\\parskip}}{{4pt}}\n"
            f"\\pagestyle{{empty}}\n"
            f"\\begin{{document}}\n"
            f"\\begin{{center}}\n"
            f"  \\textbf{{\\large {titolo_sol}}} \\\\\n"
            f"  \\vspace{{0.2cm}}\n"
            f"  {{\\small \\textit{{Documento riservato al docente — non distribuire agli studenti}}}}\n"
            f"\\end{{center}}\n"
            f"\\vspace{{0.4cm}}\n"
            f"{latex_sol_body}\n"
            f"\\end{{document}}"
        )
        pdf_sol, _ = compila_pdf(latex_sol)
        risultato["S"] = {"latex": latex_sol, "pdf": pdf_sol, "testo": testo_completo}

    return risultato


# ── FUNZIONE STREAMING COMPLETA (per flusso ibrido) ───────────────────────────────

def genera_verifica_streaming(
    model,
    materia: str,
    argomento: str,
    difficolta: str,
    calibrazione: str,
    durata: str,
    num_esercizi: int,
    punti_totali: int,
    mostra_punteggi: bool,
    con_griglia: bool,
    doppia_fila: bool,
    bes_dsa: bool,
    perc_ridotta: int | None,
    bes_dsa_b: bool,
    genera_soluzioni: bool,
    note_generali: str,
    istruzioni_esercizi: str,
    immagini_esercizi: list,
    file_ispirazione=None,
    mathpix_context: str | None = None,   # LaTeX estratto da Mathpix OCR
    on_progress=None,       # callback(testo: str) — aggiorna barra stato
    on_token=None,          # callback(token: str) — chunk streaming live
    on_corpo_grezzo=None,   # callback(corpo_latex: str) — corpo grezzo prima del QA
    on_blocchi=None,        # callback(lista_blocchi: list[str]) — dopo split in blocchi
) -> dict:
    """
    Versione streaming del flusso principale.
    Genera il corpo con streaming visibile, poi esegue QA, split in blocchi
    e assembla. Restituisce lo stesso dict di genera_verifica().

    Callbacks:
      on_token(chunk)           → ogni frammento testo durante la generazione
      on_corpo_grezzo(corpo)    → corpo completo dopo cleanup, prima del QA
      on_blocchi(blocchi)       → lista dei blocchi dopo split (uno per esercizio)
    """

    def _avanza(testo: str):
        if on_progress:
            on_progress(testo)

    e_mat = any(
        k in materia.lower()
        for k in ["matem", "fis", "chim", "inform", "elettr", "meccan"]
    )

    risultato = {
        "titolo": "",
        "A": {"latex": "", "pdf": None},
        "B": {"latex": "", "pdf": None},
        "R": {"latex": "", "pdf": None},
        "RB": {"latex": "", "pdf": None},
        "S": {"latex": "", "pdf": None, "testo": ""},
        "blocchi_a": [],   # NUOVO: blocchi esercizi fila A
    }

    # ── 1. TITOLO ─────────────────────────────────────────────────────────────
    _avanza("✍️  Elaborazione titolo…")
    resp_titolo = _safe_generate(model, prompt_titolo(materia, argomento), "Generazione titolo")
    titolo_clean = resp_titolo.text.strip().strip('"').strip("'").strip()
    if not titolo_clean:
        titolo_clean = argomento.strip()
    risultato["titolo"] = titolo_clean

    # ── 2. PREAMBOLO FILA A ───────────────────────────────────────────────────
    titolo_variante_a = "Versione A" if doppia_fila else ""
    preambolo_a, titolo_header_a = _costruisci_preambolo(
        materia, titolo_clean, titolo_variante_a, e_mat
    )
    risultato["_preambolo_a"] = preambolo_a
    risultato["_e_mat"] = e_mat
    risultato["_titolo_clean"] = titolo_clean

    # ── 3. CORPO CON STREAMING ────────────────────────────────────────────────
    _avanza("🧠  Generazione esercizi in corso…")

    inp = [
        prompt_corpo_verifica(
            materia, argomento, calibrazione, durata,
            num_esercizi, punti_totali, mostra_punteggi,
            con_griglia, note_generali, istruzioni_esercizi,
            e_mat, titolo_header_a, preambolo_a,
            mathpix_context=mathpix_context,
        )
    ]
    if file_ispirazione:
        inp.append({"mime_type": file_ispirazione.type, "data": file_ispirazione.getvalue()})
        inp[0] += "\nPrendi spunto dal file allegato per stile e livello."
    for im in immagini_esercizi:
        inp.append({"mime_type": im["mime_type"], "data": im["data"]})
        inp[0] += f"\nUsa l'immagine come riferimento per l'Esercizio {im['idx']}."

    testo_grezzo = ""
    try:
        response = model.generate_content(inp, stream=True)
        for chunk in response:
            if chunk.text:
                testo_grezzo += chunk.text
                if on_token:
                    on_token(chunk.text)
    except Exception:
        response = model.generate_content(inp)
        testo_grezzo = response.text
        if on_token:
            on_token(testo_grezzo)

    corpo_a = pulisci_corpo_latex(_pulisci_risposta(testo_grezzo))

    if on_corpo_grezzo:
        on_corpo_grezzo(corpo_a)

    # ── 4. CONTROLLO QUALITÀ ──────────────────────────────────────────────────
    _avanza("🔎  Controllo qualità e correzione errori…")
    rc = _safe_generate(
        model,
        prompt_controllo_qualita(materia, difficolta, corpo_a, mostra_punteggi, punti_totali),
        "Controllo qualità",
    )
    corpo_corretto = pulisci_corpo_latex(_pulisci_risposta(rc.text))
    n_orig = len(re.findall(r"\\subsection\*", corpo_a))
    n_corr = len(re.findall(r"\\subsection\*", corpo_corretto))
    if corpo_corretto and n_corr == n_orig:
        corpo_a = corpo_corretto
    corpo_a = _tronca_al_numero_giusto(corpo_a, num_esercizi)

    # ── 5. SPLIT IN BLOCCHI ───────────────────────────────────────────────────
    _, blocchi = _split_blocchi(corpo_a)
    risultato["blocchi_a"] = blocchi
    if on_blocchi:
        on_blocchi(blocchi)

    # ── 6. ASSEMBLA E COMPILA FILA A ──────────────────────────────────────────
    _avanza("🖨️  Compilazione PDF…")
    latex_a, pdf_a = _assembla_e_compila(
        preambolo_a, corpo_a, mostra_punteggi, punti_totali, con_griglia
    )
    risultato["A"] = {"latex": latex_a, "pdf": pdf_a}

    # ── 7. VERIFICA RIDOTTA A ─────────────────────────────────────────────────
    if bes_dsa and perc_ridotta:
        _avanza("⛳ Generazione verifica ridotta…")
        rb_bes = _safe_generate(
            model,
            prompt_versione_ridotta(corpo_a, materia, perc_ridotta, mostra_punteggi, punti_totali),
            "Verifica ridotta A",
        )
        corpo_r = pulisci_corpo_latex(_pulisci_risposta(rb_bes.text))
        latex_r, pdf_r = _assembla_e_compila(
            preambolo_a, corpo_r, mostra_punteggi, punti_totali, con_griglia
        )
        risultato["R"] = {"latex": latex_r, "pdf": pdf_r}

    # ── 8. FILA B ─────────────────────────────────────────────────────────────
    corpo_b = ""
    preambolo_b = ""
    if doppia_fila:
        _avanza("📄  Generazione Versione B…")
        rb = _safe_generate(model, prompt_variante_rapida(corpo_a, materia), "Variante B")
        corpo_b = pulisci_corpo_latex(_pulisci_risposta(rb.text))

        preambolo_b, _ = _costruisci_preambolo(materia, titolo_clean, "Versione B", e_mat)

        _avanza("🖨️  PDF Versione B…")
        latex_b, pdf_b = _assembla_e_compila(
            preambolo_b, corpo_b, mostra_punteggi, punti_totali, con_griglia
        )
        risultato["B"] = {"latex": latex_b, "pdf": pdf_b}

        # Ridotta B
        if bes_dsa_b and perc_ridotta and corpo_b:
            _avanza("⛳ Generazione verifica ridotta Fila B…")
            rb_bes_b = _safe_generate(
                model,
                prompt_versione_ridotta(
                    corpo_b, materia, perc_ridotta, mostra_punteggi, punti_totali, "Fila B"
                ),
                "Verifica ridotta B",
            )
            corpo_rb = pulisci_corpo_latex(_pulisci_risposta(rb_bes_b.text))
            preambolo_rb, _ = _costruisci_preambolo(
                materia, titolo_clean, "Versione B Ridotta", e_mat
            )
            latex_rb, pdf_rb = _assembla_e_compila(
                preambolo_rb, corpo_rb, mostra_punteggi, punti_totali, con_griglia
            )
            risultato["RB"] = {"latex": latex_rb, "pdf": pdf_rb}

    # ── 9. SOLUZIONI ──────────────────────────────────────────────────────────
    if genera_soluzioni:
        _avanza("📋 Generazione soluzioni…")

        label_a = "Fila A" if doppia_fila else ""
        rs_a = _safe_generate(model, prompt_soluzioni(corpo_a, materia, label_a), "Soluzioni A")
        testo_sol_a = rs_a.text.strip()

        testo_sol_b = ""
        if doppia_fila and corpo_b:
            rs_b = _safe_generate(model, prompt_soluzioni(corpo_b, materia, "Fila B"), "Soluzioni B")
            testo_sol_b = rs_b.text.strip()

        titolo_sol = f"Soluzioni — {materia}: {titolo_clean}"
        latex_sol_body = ""
        if testo_sol_b:
            latex_sol_body += "\\section*{Fila A}\n"
        latex_sol_body += _testo_to_latex_body(testo_sol_a)
        if testo_sol_b:
            latex_sol_body += "\n\\newpage\n\\section*{Fila B}\n"
            latex_sol_body += _testo_to_latex_body(testo_sol_b)

        testo_completo = testo_sol_a
        if testo_sol_b:
            testo_completo += "\n\n---\n\n## Fila B\n\n" + testo_sol_b

        latex_sol = (
            f"\\documentclass[11pt,a4paper]{{article}}\n"
            f"\\usepackage[utf8]{{inputenc}}\n"
            f"\\usepackage[italian]{{babel}}\n"
            f"\\usepackage{{amsmath,amsfonts,amssymb,geometry}}\n"
            f"\\geometry{{margin=2cm}}\n"
            f"\\setlength{{\\parskip}}{{4pt}}\n"
            f"\\pagestyle{{empty}}\n"
            f"\\begin{{document}}\n"
            f"\\begin{{center}}\n"
            f"  \\textbf{{\\large {titolo_sol}}} \\\\\n"
            f"  \\vspace{{0.2cm}}\n"
            f"  {{\\small \\textit{{Documento riservato al docente — non distribuire agli studenti}}}}\n"
            f"\\end{{center}}\n"
            f"\\vspace{{0.4cm}}\n"
            f"{latex_sol_body}\n"
            f"\\end{{document}}"
        )
        pdf_sol, _ = compila_pdf(latex_sol)
        risultato["S"] = {"latex": latex_sol, "pdf": pdf_sol, "testo": testo_completo}

    return risultato


def ricompila_da_blocchi(
    blocchi: list[str],
    preambolo: str,
    mostra_punteggi: bool,
    punti_totali: int,
    con_griglia: bool,
) -> tuple[str, bytes | None]:
    """
    Riassembla i blocchi modificati e ricompila il PDF.
    Usata dopo rigenerazione selettiva di uno o più blocchi.
    """
    corpo = _assembla_corpo_da_blocchi(blocchi)
    return _assembla_e_compila(preambolo, corpo, mostra_punteggi, punti_totali, con_griglia)


# ── ANALISI DOCUMENTO CARICATO ───────────────────────────────────────────────────

def analizza_documento_caricato(
    model,
    file_bytes: bytes,
    mime_type: str,
    mathpix_context: str | None = None,
    materie_valide: list | None = None,
) -> dict:
    """
    Analizza un documento caricato (immagine o PDF) usando un modello veloce.
    Restituisce lo schema esteso: tipo_documento, contenuto_argomento, stile_desc,
    esercizi_trovati[], ha_grafici, modalita_uso_consigliata, confidence.

    Parametri
    ---------
    model           : GenerativeModel (usare Flash Lite per velocità)
    file_bytes      : bytes del file
    mime_type       : MIME type (es. "image/png", "application/pdf")
    mathpix_context : LaTeX estratto da Mathpix OCR (opzionale)
    materie_valide  : lista materie accettate (da config.MATERIE)

    Ritorno
    -------
    dict con chiavi: tipo_documento, materia, scuola, contenuto_argomento,
                     stile_desc, tipi_domande, num_item_medi, num_esercizi_rilevati,
                     ha_grafici, ha_formule, esercizi_trovati, modalita_uso_consigliata,
                     motivazione_uso, confidence
    """
    import json as _json

    if materie_valide is None:
        materie_valide = [
            "Matematica", "Fisica", "Chimica", "Biologia", "Italiano",
            "Storia", "Geografia", "Inglese", "Filosofia", "Informatica",
        ]

    testo_prompt = prompt_analisi_documento(
        materie_valide=materie_valide,
        mathpix_context=mathpix_context,
    )

    inp = [testo_prompt, {"mime_type": mime_type, "data": file_bytes}]

    try:
        resp = model.generate_content(inp)
        raw  = resp.text.strip() if resp.text else ""
    except Exception as exc:
        raise Exception(f"Chiamata modello fallita: {exc}") from exc

    # Rimuovi eventuali fence ```json ... ```
    raw = re.sub(r"^```(?:json)?", "", raw, flags=re.MULTILINE).strip()
    raw = re.sub(r"```$",          "", raw, flags=re.MULTILINE).strip()

    # Parsing JSON con fallback estrazione parziale
    try:
        data = _json.loads(raw)
    except _json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            try:
                data = _json.loads(m.group(0))
            except _json.JSONDecodeError as exc2:
                raise Exception(
                    f"Risposta non è JSON valido: {raw[:200]}"
                ) from exc2
        else:
            raise Exception(f"Nessun JSON nella risposta: {raw[:200]}")

    # Normalizzazione
    _tipi_validi = {"Aperto", "Scelta multipla", "Vero/Falso", "Completamento"}
    _modalita_valide = {
        "stile_e_struttura", "base_conoscenza", "copia_fedele", "difficolta_e_livello"
    }
    _tipo_doc_validi = {"verifica", "appunti", "libro", "esercizi_sciolti", "misto", "altro"}

    # Normalizza esercizi_trovati
    raw_es = data.get("esercizi_trovati") or []
    esercizi_trovati = []
    for e in raw_es[:10]:  # cap a 10 per sicurezza
        if isinstance(e, dict):
            esercizi_trovati.append({
                "numero":           int(e.get("numero") or len(esercizi_trovati) + 1),
                "testo_breve":      (str(e.get("testo_breve") or ""))[:120] or None,
                "tipo":             e.get("tipo") if e.get("tipo") in _tipi_validi else "Aperto",
                "ha_dati_numerici": bool(e.get("ha_dati_numerici", False)),
            })

    modalita = data.get("modalita_uso_consigliata") or ""
    if modalita not in _modalita_valide:
        # Inferenza fallback: appunti/libro → base_conoscenza, verifica → stile_e_struttura
        tipo_doc_raw = (data.get("tipo_documento") or "").lower()
        if tipo_doc_raw in ("appunti", "libro"):
            modalita = "base_conoscenza"
        elif tipo_doc_raw == "verifica":
            modalita = "stile_e_struttura"
        else:
            modalita = "stile_e_struttura"

    tipo_doc = data.get("tipo_documento") or "altro"
    if tipo_doc not in _tipo_doc_validi:
        tipo_doc = "altro"

    materia = data.get("materia") or None
    if materia and materia not in materie_valide:
        materia = None

    # ── Pertinenza — guardrail per file non scolastici ───────────────────────
    # Default: se il campo manca, assumiamo pertinente=True (safe fallback).
    pertinente_raw = data.get("pertinente")
    if isinstance(pertinente_raw, bool):
        pertinente = pertinente_raw
    elif isinstance(pertinente_raw, str):
        pertinente = pertinente_raw.lower() not in ("false", "0", "no")
    else:
        pertinente = True  # fallback sicuro

    messaggio_rifiuto   = (data.get("messaggio_rifiuto") or None) if not pertinente else None
    messaggio_proattivo = (data.get("messaggio_proattivo") or None) if pertinente else None

    result = {
        "pertinente":                pertinente,
        "messaggio_rifiuto":         messaggio_rifiuto,
        "messaggio_proattivo":       messaggio_proattivo,
        "tipo_documento":            tipo_doc,
        "materia":                   materia,
        "scuola":                    data.get("scuola") or None,
        "contenuto_argomento":       (data.get("contenuto_argomento") or None),
        "stile_desc":                (data.get("stile_desc") or None),
        "tipi_domande":              [t for t in (data.get("tipi_domande") or []) if t in _tipi_validi],
        "num_item_medi":             int(data.get("num_item_medi") or 0),
        "num_esercizi_rilevati":     int(data.get("num_esercizi_rilevati") or 0),
        "ha_grafici":                bool(data.get("ha_grafici", False)),
        "ha_formule":                bool(data.get("ha_formule", False)),
        # ── Campi scoring (NUOVO) ─────────────────────────────────────────────
        "ha_punteggi":               bool(data.get("ha_punteggi", False)),
        "ha_tabella_punti":          bool(data.get("ha_tabella_punti", False)),
        "punti_totali_rilevati":     (
            int(data["punti_totali_rilevati"])
            if isinstance(data.get("punti_totali_rilevati"), (int, float))
            and data["punti_totali_rilevati"] > 0
            else None
        ),
        # ─────────────────────────────────────────────────────────────────────
        "esercizi_trovati":          esercizi_trovati,
        "modalita_uso_consigliata":  modalita,
        "motivazione_uso":           (data.get("motivazione_uso") or None),
        "confidence":                max(0.0, min(1.0, float(data.get("confidence") or 0.0))),
    }
    return result


def compila_contesto_generazione(
    analisi: dict,
    file_mode: str,
    istruzioni_extra: str,
    argomento_override: str | None = None,
) -> tuple[str, str]:
    """
    Assembla argomento e note_generali per genera_verifica() dai dati del
    Percorso A (upload intelligente).

    Parametri
    ---------
    analisi           : dict restituito da analizza_documento_caricato()
    file_mode         : come usare il file —
                        "stile_e_struttura" | "base_conoscenza" |
                        "copia_fedele"      | "difficolta_e_livello" |
                        "includi_esercizio" | "ignora"
    istruzioni_extra  : testo libero del docente (box di correzione finale)
    argomento_override: se il docente ha specificato un argomento diverso dal file

    Ritorno
    -------
    (argomento: str, note_generali: str)
    """
    argomento_file = analisi.get("contenuto_argomento") or ""
    stile_desc     = analisi.get("stile_desc") or ""
    tipo_doc       = analisi.get("tipo_documento", "altro")
    ha_grafici     = analisi.get("ha_grafici", False)
    es_trovati     = analisi.get("esercizi_trovati") or []

    # ── Argomento: override del docente ha sempre priorità assoluta ──────────
    argomento = (argomento_override or argomento_file or "").strip()
    if not argomento:
        argomento = "Argomento da specificare"

    # ── Note AI: costruite in base alla modalità ──────────────────────────────
    parti_note: list[str] = []

    if file_mode == "stile_e_struttura":
        parti_note.append(
            "╔══════════════════════════════════════════════════╗\n"
            "║  USO FILE: STILE E STRUTTURA                      ║\n"
            "╚══════════════════════════════════════════════════╝\n"
            "Il docente ha fornito un documento di riferimento PER LO STILE.\n"
            "REGOLA ASSOLUTA: usa il file SOLO come modello di forma, NON di contenuto.\n"
            f"- Replica la struttura: {stile_desc}\n"
            f"- Argomento della nuova verifica: '{argomento}' (DIVERSO dal file, rispetta questo).\n"
            "- NON copiare testo, dati numerici o esercizi specifici dal file.\n"
            "- Adatta il livello di difficoltà percepito nel file."
        )
        if ha_grafici:
            parti_note.append(
                "⚠️ Il file contiene grafici: non includerli se appartengono all'argomento "
                "del file originale — genera grafici solo se pertinenti al nuovo argomento."
            )

    elif file_mode == "base_conoscenza":
        parti_note.append(
            "╔══════════════════════════════════════════════════╗\n"
            "║  USO FILE: BASE DI CONOSCENZA                    ║\n"
            "╚══════════════════════════════════════════════════╝\n"
            "Il docente ha fornito appunti/materiale come BASE CONCETTUALE.\n"
            "- Usa i concetti, le definizioni e gli esempi presenti nel file come fonte.\n"
            f"- Genera esercizi sull'argomento '{argomento}'.\n"
            "- Puoi ispirti alla terminologia usata nel file.\n"
            "- NON copiare esercizi o testo letteralmente."
        )

    elif file_mode == "copia_fedele":
        ha_punteggi    = analisi.get("ha_punteggi", False)
        ha_tab_punti   = analisi.get("ha_tabella_punti", False)
        punti_rilevati = analisi.get("punti_totali_rilevati", None)

        # Costruisci nota scoring specifica e contestuale
        if ha_punteggi and punti_rilevati:
            _nota_scoring = (
                f"- PUNTEGGI: la verifica originale ha punteggi sui sottopunti "
                f"(totale rilevato: {punti_rilevati} pt). "
                f"Replica la distribuzione proporzionale dei punti tra gli esercizi. "
                f"Usa il formato ESATTO (X pt) su ogni \\item."
            )
        elif ha_punteggi:
            _nota_scoring = (
                "- PUNTEGGI: la verifica originale ha punteggi annotati sui sottopunti. "
                "Replica la distribuzione proporzionale. "
                "Usa il formato ESATTO (X pt) su ogni \\item."
            )
        else:
            _nota_scoring = (
                "- PUNTEGGI: la verifica originale NON ha punteggi annotati. "
                "Se ti viene chiesto di aggiungerne, distribuiscili proporzionalmente alla difficoltà."
            )

        if ha_tab_punti:
            _nota_griglia = (
                "- TABELLA PUNTEGGI: la verifica originale ha una tabella di valutazione finale. "
                "NON generarla nel corpo — verrà aggiunta automaticamente."
            )
        else:
            _nota_griglia = ""

        parti_note.append(
            "╔══════════════════════════════════════════════════╗\n"
            "║  USO FILE: COPIA FEDELE (RIELABORAZIONE)         ║\n"
            "╚══════════════════════════════════════════════════╝\n"
            "Il docente vuole una verifica molto simile al file allegato.\n"
            "- Mantieni la stessa struttura, lo stesso numero di esercizi e gli stessi tipi.\n"
            "- Cambia SOLO i dati numerici specifici (numeri, date, nomi propri) per evitare plagio.\n"
            "- Mantieni lo stesso argomento e livello di difficoltà.\n"
            + _nota_scoring
            + ("\n" + _nota_griglia if _nota_griglia else "")
        )
        if ha_grafici:
            parti_note.append(
                "⚠️ NOTA GRAFICI: il file originale contiene grafici. "
                "Genera i grafici TikZ/pgfplots SOLO se l'argomento lo richiede intrinsecamente — "
                "evita grafici puramente decorativi o che richiedono immagini non generabili."
            )

    elif file_mode == "difficolta_e_livello":
        parti_note.append(
            "╔══════════════════════════════════════════════════╗\n"
            "║  USO FILE: SOLO LIVELLO DI DIFFICOLTÀ            ║\n"
            "╚══════════════════════════════════════════════════╝\n"
            "Usa il file SOLO per calibrare la difficoltà e il registro linguistico.\n"
            f"- Genera esercizi sull'argomento '{argomento}' con lo stesso livello.\n"
            "- Ignora struttura e contenuto del file."
        )

    elif file_mode == "includi_esercizio":
        # Esercizio specifico dal file — MASSIMA PRIORITÀ, deve comparire nell'output
        parti_note.append(
            "╔══════════════════════════════════════════════════════════╗\n"
            "║  ⚠️  ISTRUZIONE CRITICA — ESERCIZIO DA INCLUDERE          ║\n"
            "╚══════════════════════════════════════════════════════════╝\n"
            "Il docente ha fornito un'immagine/file contenente UN ESERCIZIO SPECIFICO.\n"
            "REGOLA ASSOLUTA E INVIOLABILE:\n"
            "  • L'esercizio nell'immagine DEVE comparire nella verifica finale — OBBLIGATORIO.\n"
            "  • È VIETATO ignorarlo, parafrasarlo o sostituirlo con uno simile.\n"
            "  • Trascrivi il testo dell'esercizio FEDELMENTE in LaTeX con la stessa struttura.\n"
            "  • Se le istruzioni del docente dicono 'stessi dati': mantieni numeri e dati identici.\n"
            "  • Se le istruzioni del docente dicono 'dati diversi': cambia solo i valori numerici, "
            "mantieni identica la struttura e le tipologie di richiesta.\n"
            "  • Inserisci questo esercizio come PRIMO esercizio (Esercizio 1) della verifica.\n"
            f"  • Genera poi i restanti {max(0, len(es_trovati)-1)} esercizi sull'argomento '{argomento}'."
        )

    # ── Istruzioni extra del docente (massima priorità) ───────────────────────
    if istruzioni_extra.strip():
        parti_note.insert(0,
            "╔══════════════════════════════════════════════════╗\n"
            "║  ISTRUZIONI PRIORITARIE DEL DOCENTE              ║\n"
            "╚══════════════════════════════════════════════════╝\n"
            + istruzioni_extra.strip()
        )

    note_generali = "\n\n".join(parti_note)
    return argomento, note_generali
