"""
stili_verifica.py — lo «stile» grafico del PDF della verifica (senza Streamlit).

Il contenuto non cambia: cambiano i caratteri e il formato dei titoli degli esercizi. Ogni stile è un blocco di comandi LaTeX che si
inserisce nel preambolo (applica_stile): usa SOLO pacchetti già presenti con texlive-latex-extra e texlive-fonts-recommended
(titlesec, sansmath, psnfss), quindi niente da installare. Tutto in nero: i docenti stampano in bianco e nero.

Stili: «classico» (quello di sempre), «moderno» (carattere senza grazie, titoli neri) e «leggibile» (alta leggibilità per DSA: non
si sceglie per tutta la verifica ma si scarica come versione a parte, vedi cambia_stile).

L'intestazione «\\begin{center}\\textbf{\\large Verifica di …}» resta identica, perché il logo della scuola, la Fila B e la ricompilazione
la riconoscono da quel testo. I blocchi di stile sono racchiusi tra righe-commento (_MARCA_*) così si possono togliere e sostituire.
"""
import re

STILE_PREDEFINITO = "classico"

_MARCA_PRE = ("%%STILE-INIZIO\n", "%%STILE-FINE\n")
_MARCA_DOC = ("%%STILE-DOC-INIZIO\n", "%%STILE-DOC-FINE\n")

STILI = {
    "classico": {
        "nome": "Classico",
        "descrizione": "Il carattere dei documenti scientifici: sobrio, adatto a ogni materia.",
        "pre": "", "inizio": "", "corpo": None, "margine": None,
    },
    "moderno": {
        "nome": "Moderno",
        "descrizione": "Carattere senza grazie, pulito, con i titoli degli esercizi in nero (si stampa bene in bianco e nero).",
        "corpo": None, "margine": None,
        "pre": (
            "\\usepackage[T1]{fontenc}\n\\usepackage[scaled=.92]{helvet}\n\\renewcommand{\\familydefault}{\\sfdefault}\n"
            "\\usepackage{sansmath}\n\\everymath{\\sansmath}\\everydisplay{\\sansmath}\n"
            "\\usepackage{titlesec}\n"
            "\\titleformat{\\subsection}[block]{\\bfseries\\large}{}{0pt}{}\n"
            "\\titlespacing*{\\subsection}{0pt}{1.5ex plus .4ex}{.9ex}\n"
        ),
        "inizio": "",
    },
    "leggibile": {
        "nome": "Alta leggibilità",
        "descrizione": "Per DSA: carattere senza grazie un po' più grande, più spazio tra le righe, testo non giustificato.",
        "corpo": None, "margine": "1.7cm",
        "pre": (
            "\\usepackage[T1]{fontenc}\n\\usepackage[scaled=.92]{helvet}\n\\renewcommand{\\familydefault}{\\sfdefault}\n"
            "\\usepackage{sansmath}\n\\everymath{\\sansmath}\\everydisplay{\\sansmath}\n"
            "\\usepackage{titlesec}\n"
            "\\titleformat{\\subsection}[block]{\\bfseries\\large}{}{0pt}{}\n"
            "\\titlespacing*{\\subsection}{0pt}{2ex plus .5ex}{1.1ex}\n"
            "\\setlength{\\parskip}{6pt plus 2pt}\n\\setlength{\\parindent}{0pt}\n\\raggedright\n"
        ),
        "inizio": "\\fontsize{12.5pt}{17.5pt}\\selectfont\n",
    },
}

# stili tra cui sceglie il docente per tutta la verifica (l'alta leggibilità è una versione a parte)
STILI_SCELTA = ("classico", "moderno")


def stili_disponibili() -> list:
    """[(id, nome)] nell'ordine in cui si mostrano."""
    return [(k, STILI[k]["nome"]) for k in STILI_SCELTA]


def descrizione_stile(stile: str) -> str:
    return STILI.get(stile or STILE_PREDEFINITO, STILI[STILE_PREDEFINITO])["descrizione"]


def _togli_blocchi(latex: str) -> str:
    for ini, fine in (_MARCA_PRE, _MARCA_DOC):
        latex = re.sub(re.escape(ini) + r".*?" + re.escape(fine), "", latex, flags=re.DOTALL)
    return latex


def applica_stile(preambolo: str, stile: str | None) -> str:
    """Il preambolo (o l'intero LaTeX) con lo stile scelto. Stile sconosciuto o «classico» = invariato."""
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
    blocco_pre = (_MARCA_PRE[0] + s["pre"] + _MARCA_PRE[1]) if s["pre"] else ""
    blocco_doc = (_MARCA_DOC[0] + s["inizio"] + _MARCA_DOC[1]) if s["inizio"] else ""
    return testa.rstrip("\n") + "\n" + blocco_pre + marcatore + "\n" + blocco_doc + coda.lstrip("\n")


def cambia_stile(latex: str, stile: str | None) -> str:
    """
    Lo stesso LaTeX con un altro stile (per esempio la versione ad alta leggibilità di una verifica già fatta): toglie lo stile
    di prima, rimette carattere e margini di base e applica il nuovo. Il logo e il contenuto non cambiano.
    """
    base = _togli_blocchi(latex or "")
    base = re.sub(r"(\\documentclass\[)\d+pt", lambda m: m.group(1) + "12pt", base, count=1)
    base = re.sub(r"\\geometry\{margin=[^}]*\}", lambda m: "\\geometry{margin=1.5cm}", base, count=1)
    return applica_stile(base, stile)
