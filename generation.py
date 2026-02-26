# generation.py
# Contiene tutta la logica di generazione AI.
# Nessuna dipendenza da Streamlit — la progress bar viene aggiornata
# tramite il callback on_progress(testo: str).

import re
import time

from prompts import (
    prompt_titolo,
    prompt_corpo_verifica,
    prompt_controllo_qualita,
    prompt_versione_b,
    prompt_versione_ridotta,
    prompt_soluzioni,
)
from latex_utils import (
    compila_pdf,
    inietta_griglia,
    riscala_punti,
    fix_items_environment,
    rimuovi_vspace_corpo,
    pulisci_corpo_latex,
    rimuovi_punti_subsection,
)


# ── HELPER INTERNO ────────────────────────────────────────────────────────────────

def _pulisci_risposta(testo: str) -> str:
    return testo.replace("```latex", "").replace("```", "").strip()


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
    hspace6 = "{6cm}"
    hspace4 = "{4cm}"
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
        f"  \\small \\textbf{{Nome:}} \\underline{{\\hspace{hspace6}}} "
        f"\\quad \\textbf{{Classe e Data:}} \\underline{{\\hspace{hspace4}}} \\\\\n"
        f"  \\vspace{{0.3cm}}\n"
        f"  \\textit{{\\small {nota_bes}}}\n"
        f"\\end{{center}}\n"
    ), titolo_header


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
    latex = preambolo + corpo
    latex = fix_items_environment(latex)
    latex = rimuovi_vspace_corpo(latex)
    if mostra_punteggi:
        latex = rimuovi_punti_subsection(latex)
        latex = riscala_punti(latex, punti_totali)

    latex_final = inietta_griglia(latex, punti_totali) if con_griglia else latex
    pdf, _ = compila_pdf(latex_final)

    if pdf is None and con_griglia:
        # fallback senza griglia
        pdf, _ = compila_pdf(latex)

    return latex_final, pdf


def _tronca_al_numero_giusto(corpo: str, num_esercizi: int) -> str:
    """Rimuove i blocchi \\subsection* in eccesso."""
    splits = re.split(r"(\\subsection\*\{)", corpo)
    n_blocchi = (len(splits) - 1) // 2
    if n_blocchi <= num_esercizi:
        return corpo
    testa = splits[0]
    parti = []
    for b in range(num_esercizi):
        parti.append(splits[1 + b * 2])
        parti.append(splits[2 + b * 2])
    troncato = testa + "".join(parti)
    troncato = re.sub(r"\\end\{document\}.*$", "", troncato, flags=re.DOTALL).rstrip()
    return troncato + "\n\\end{document}"


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
    resp_titolo = model.generate_content(prompt_titolo(materia, argomento))
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
        )
    ]
    if file_ispirazione:
        inp.append({"mime_type": file_ispirazione.type, "data": file_ispirazione.getvalue()})
        inp[0] += "\nPrendi spunto dal file allegato per stile e livello."
    for im in immagini_esercizi:
        inp.append({"mime_type": im["mime_type"], "data": im["data"]})
        inp[0] += f"\nUsa l'immagine come riferimento per l'Esercizio {im['idx']}."

    ra = model.generate_content(inp)
    corpo_a = pulisci_corpo_latex(_pulisci_risposta(ra.text))

    # ── 4. CONTROLLO QUALITÀ ──────────────────────────────────────────────────
    _avanza("🔎  Controllo qualità e correzione errori…")
    rc = model.generate_content(
        prompt_controllo_qualita(materia, difficolta, corpo_a)
    )
    corpo_corretto = pulisci_corpo_latex(_pulisci_risposta(rc.text))

    n_orig = len(re.findall(r"\\subsection\*", corpo_a))
    n_corr = len(re.findall(r"\\subsection\*", corpo_corretto))
    if corpo_corretto and n_corr == n_orig:
        corpo_a = corpo_corretto

    corpo_a = _tronca_al_numero_giusto(corpo_a, num_esercizi)

    # ── 5. ASSEMBLA E COMPILA FILA A ──────────────────────────────────────────
    _avanza("🖨️  Compilazione PDF…")
    latex_a, pdf_a = _assembla_e_compila(
        preambolo_a, corpo_a, mostra_punteggi, punti_totali, con_griglia
    )
    risultato["A"] = {"latex": latex_a, "pdf": pdf_a}

    # ── 6. VERIFICA RIDOTTA A ─────────────────────────────────────────────────
    if bes_dsa and perc_ridotta:
        _avanza("⛳ Generazione verifica ridotta…")
        rb_bes = model.generate_content(
            prompt_versione_ridotta(corpo_a, materia, perc_ridotta, mostra_punteggi, punti_totali)
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
        rb = model.generate_content(prompt_versione_b(corpo_a))
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
            rb_bes_b = model.generate_content(
                prompt_versione_ridotta(
                    corpo_b, materia, perc_ridotta, mostra_punteggi, punti_totali, "Fila B"
                )
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
        rs_a = model.generate_content(prompt_soluzioni(corpo_a, materia, label_a))
        testo_sol_a = rs_a.text.strip()

        testo_sol_b = ""
        if doppia_fila and corpo_b:
            rs_b = model.generate_content(prompt_soluzioni(corpo_b, materia, "Fila B"))
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
