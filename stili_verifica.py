"""
stili_verifica.py — lo «stile» grafico del PDF della verifica (senza Streamlit).

Il contenuto non cambia: cambiano caratteri, colori, titoli degli esercizi e piccoli dettagli dell'intestazione. Ogni stile è un
blocco di comandi LaTeX che si inserisce nel preambolo (applica_stile): usa SOLO pacchetti già presenti con
texlive-latex-extra e texlive-fonts-recommended (titlesec, xcolor, tikz, sansmath, psnfss, psnfss), quindi niente da installare.

L'intestazione «\\begin{center}\\textbf{\\large Verifica di …}» resta identica, perché il logo della scuola, la Fila B e la ricompilazione
la riconoscono da quel testo: lo stile aggiunge decorazioni PRIMA dell'intestazione (`inizio`) e non dopo (extract_corpo ripartirebbe
dal primo \\end{center} e le duplicherebbe).
"""

STILE_PREDEFINITO = "classico"

STILI = {
    "classico": {
        "nome": "Classico",
        "descrizione": "Il carattere dei documenti scientifici: sobrio, adatto a ogni materia.",
        "pre": "", "inizio": "", "corpo": None, "margine": None,
    },
    "moderno": {
        "nome": "Moderno",
        "descrizione": "Carattere senza grazie, titoli blu con filetto sotto e una barra colorata in cima.",
        "corpo": None, "margine": None,
        "pre": (
            "\\usepackage[T1]{fontenc}\n\\usepackage[scaled=.92]{helvet}\n\\renewcommand{\\familydefault}{\\sfdefault}\n"
            "\\usepackage{sansmath}\n\\everymath{\\sansmath}\\everydisplay{\\sansmath}\n"
            "\\usepackage{xcolor}\n\\definecolor{acc}{HTML}{1D4ED8}\n\\definecolor{accchiaro}{HTML}{93B4F5}\n"
            "\\usepackage{titlesec}\n"
            "\\titleformat{\\subsection}[block]{\\bfseries\\large\\color{acc}}{}{0pt}{}[\\vspace{.3ex}{\\color{accchiaro}\\titlerule[.8pt]}]\n"
            "\\titlespacing*{\\subsection}{0pt}{1.3ex plus .4ex}{.9ex}\n"
        ),
        "inizio": "\\noindent{\\color{acc}\\rule{\\linewidth}{3.5pt}}\\par\\vspace{3mm}\n",
    },
    "elegante": {
        "nome": "Elegante",
        "descrizione": "Palatino, titoli in maiuscoletto color terracotta con filetto sottile: un aspetto da libro.",
        "corpo": None, "margine": None,
        "pre": (
            "\\usepackage[T1]{fontenc}\n\\usepackage{mathpazo}\n\\linespread{1.05}\n"
            "\\usepackage{xcolor}\n\\definecolor{acc}{HTML}{7C2D12}\n"
            "\\usepackage{titlesec}\n"
            "\\titleformat{\\subsection}[block]{\\scshape\\large\\color{acc}}{}{0pt}{}[\\vspace{.3ex}{\\color{acc!45}\\titlerule[.5pt]}]\n"
            "\\titlespacing*{\\subsection}{0pt}{1.4ex plus .4ex}{.9ex}\n"
        ),
        "inizio": ("\\noindent{\\color{acc}\\rule{\\linewidth}{.7pt}}\\par\\vspace{-1.6mm}"
                   "\\noindent{\\color{acc}\\rule{\\linewidth}{.3pt}}\\par\\vspace{3mm}\n"),
    },
    "riquadri": {
        "nome": "Scolastico a riquadri",
        "descrizione": "Carattere Bookman, ogni esercizio apre con un riquadro colorato; bande verde acqua e arancio in cima.",
        "corpo": None, "margine": None,
        "pre": (
            "\\usepackage[T1]{fontenc}\n\\usepackage{bookman}\n"
            "\\usepackage{xcolor}\n\\definecolor{acc}{HTML}{0F766E}\n\\definecolor{acc2}{HTML}{F59E0B}\n"
            "\\usepackage{tikz}\n\\usepackage{titlesec}\n"
            "\\newcommand{\\exbox}[1]{\\tikz[baseline=(t.base)]\\node[fill=acc,text=white,rounded corners=4pt,inner xsep=8pt,inner ysep=4pt](t){\\bfseries\\normalsize #1};}\n"
            "\\titleformat{\\subsection}{}{}{0pt}{\\exbox}\n"
            "\\titlespacing*{\\subsection}{0pt}{1.5ex plus .4ex}{1.1ex}\n"
        ),
        "inizio": ("\\noindent{\\color{acc}\\rule{\\linewidth}{6pt}}\\par\\vspace{-1mm}"
                   "\\noindent{\\color{acc2}\\rule{\\linewidth}{2pt}}\\par\\vspace{3mm}\n"),
    },
    "essenziale": {
        "nome": "Essenziale",
        "descrizione": "Times, caratteri e margini più piccoli: sta in meno pagine, ideale per stampare in fretta.",
        "corpo": "11pt", "margine": "1.3cm",
        "pre": (
            "\\usepackage[T1]{fontenc}\n\\usepackage{mathptmx}\n"
            "\\usepackage{titlesec}\n"
            "\\titleformat{\\subsection}[block]{\\bfseries\\normalsize}{}{0pt}{}[\\vspace{.25ex}{\\titlerule[.4pt]}]\n"
            "\\titlespacing*{\\subsection}{0pt}{1.0ex plus .2ex}{.5ex}\n"
            "\\setlength{\\parskip}{2pt plus1pt minus1pt}\n"
        ),
        "inizio": "",
    },
    "leggibile": {
        "nome": "Alta leggibilità",
        "descrizione": "Pensato per DSA: carattere senza grazie più grande, più spazio tra le righe, testo non giustificato. Occupa più pagine.",
        "corpo": None, "margine": "1.8cm",
        "pre": (
            "\\usepackage[T1]{fontenc}\n\\usepackage[scaled=.92]{helvet}\n\\renewcommand{\\familydefault}{\\sfdefault}\n"
            "\\usepackage{sansmath}\n\\everymath{\\sansmath}\\everydisplay{\\sansmath}\n"
            "\\usepackage{titlesec}\n"
            "\\titleformat{\\subsection}{\\bfseries\\Large}{}{0pt}{}\n"
            "\\titlespacing*{\\subsection}{0pt}{2.2ex plus .5ex}{1.3ex}\n"
            "\\setlength{\\parskip}{8pt plus 2pt}\n\\setlength{\\parindent}{0pt}\n\\raggedright\n"
        ),
        "inizio": "\\fontsize{13.5pt}{19pt}\\selectfont\n",
    },
}


def stili_disponibili() -> list:
    """[(id, nome)] nell'ordine in cui si mostrano."""
    return [(k, v["nome"]) for k, v in STILI.items()]


def descrizione_stile(stile: str) -> str:
    return STILI.get(stile or STILE_PREDEFINITO, STILI[STILE_PREDEFINITO])["descrizione"]


def applica_stile(preambolo: str, stile: str | None) -> str:
    """Il preambolo (fino a \\end{center} dell'intestazione) con lo stile scelto. Stile sconosciuto o «classico» = invariato."""
    import re
    s = STILI.get(stile or STILE_PREDEFINITO)
    if not s or stile in (None, "", STILE_PREDEFINITO):
        return preambolo
    marcatore = "\\begin{document}"
    if marcatore not in preambolo:
        return preambolo
    testa, coda = preambolo.split(marcatore, 1)
    if s.get("corpo"):
        testa = re.sub(r"(\\documentclass\[)\d+pt", lambda m: m.group(1) + s["corpo"], testa, count=1)
    if s.get("margine"):
        testa = re.sub(r"\\geometry\{margin=[^}]*\}", lambda m: "\\geometry{margin=" + s["margine"] + "}", testa, count=1)
    testa = testa.rstrip("\n") + "\n" + s["pre"]
    return testa + marcatore + "\n" + s["inizio"] + coda.lstrip("\n")
