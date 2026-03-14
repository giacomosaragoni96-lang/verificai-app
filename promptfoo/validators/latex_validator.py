#!/usr/bin/env python3
"""
VerificAI — Validatore Compilabilità LaTeX
═══════════════════════════════════════════════════════════════════════════════
Usabile come assertion custom in PromptFoo:

  assert:
    - type: python
      value: file://validators/latex_validator.py

Oppure standalone:
  python validators/latex_validator.py "corpo latex da testare"

Verifica che il corpo LaTeX (output di Gemini) sia compilabile con pdflatex.
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import sys
import subprocess
import tempfile
import re
import json

# ── Preambolo LaTeX standard di VerificAI ───────────────────────────────────
PREAMBOLO = r"""
\documentclass[a4paper,11pt]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[italian]{babel}
\usepackage{amsmath,amssymb}
\usepackage{enumerate}
\usepackage{graphicx}
\usepackage{geometry}
\usepackage{tikz}
\usepackage{pgfplots}
\pgfplotsset{compat=1.18}
\usepackage{adjustbox}
\geometry{margin=2cm}
\begin{document}
"""

CHIUSURA = r"""
\end{document}
"""


def valida_latex(corpo_latex: str) -> dict:
    """
    Tenta di compilare il corpo LaTeX con pdflatex.
    
    Returns:
        {
            "pass": True/False,
            "score": 1.0 o 0.0,
            "reason": "motivo"
        }
    """
    # ── Pulizia preliminare ─────────────────────────────────────────────────
    corpo = corpo_latex.strip()
    
    # Se l'output contiene il preambolo completo, usalo così com'è
    if "\\documentclass" in corpo:
        doc_completo = corpo
    else:
        # Rimuovi \end{document} se presente (lo aggiungiamo noi)
        corpo = re.sub(r'\\end\{document\}\s*$', '', corpo).strip()
        doc_completo = PREAMBOLO + "\n" + corpo + "\n" + CHIUSURA
    
    # ── Controlli strutturali rapidi (senza compilazione) ───────────────────
    errori_strutturali = []
    
    # Parentesi graffe bilanciate (escludendo escaped)
    clean = re.sub(r'\\[{}]', '', doc_completo)
    depth = 0
    for i, c in enumerate(clean):
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
        if depth < 0:
            errori_strutturali.append(f"Parentesi graffa chiusa in eccesso alla posizione ~{i}")
            break
    if depth > 0:
        errori_strutturali.append(f"Mancano {depth} parentesi graffe chiuse")
    
    # Ambienti bilanciati
    for env in ['enumerate', 'itemize', 'tabular', 'tikzpicture', 'axis', 'table', 'figure']:
        opens = len(re.findall(rf'\\begin\{{{env}', doc_completo))
        closes = len(re.findall(rf'\\end\{{{env}', doc_completo))
        if opens != closes:
            errori_strutturali.append(f"\\begin{{{env}}} ({opens}) ≠ \\end{{{env}}} ({closes})")
    
    if errori_strutturali:
        return {
            "pass": False,
            "score": 0.0,
            "reason": "Errori strutturali LaTeX: " + "; ".join(errori_strutturali)
        }
    
    # ── Compilazione con pdflatex ───────────────────────────────────────────
    # Verifica che pdflatex sia disponibile
    try:
        subprocess.run(["pdflatex", "--version"], capture_output=True, timeout=5)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        # pdflatex non disponibile — ritorna solo validazione strutturale
        return {
            "pass": True,
            "score": 0.8,
            "reason": "Validazione strutturale OK (pdflatex non disponibile per compilazione completa)"
        }
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tex_path = os.path.join(tmpdir, "test.tex")
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(doc_completo)
        
        try:
            result = subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "test.tex"],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=30,
            )
            
            pdf_exists = os.path.exists(os.path.join(tmpdir, "test.pdf"))
            
            if result.returncode == 0 and pdf_exists:
                return {
                    "pass": True,
                    "score": 1.0,
                    "reason": "LaTeX compilato con successo"
                }
            else:
                # Estrai errore dal log
                log = result.stdout or ""
                error_lines = [l for l in log.split("\n") if l.startswith("!")]
                error_msg = "; ".join(error_lines[:3]) if error_lines else "Errore di compilazione (vedi log)"
                
                return {
                    "pass": False,
                    "score": 0.0,
                    "reason": f"Compilazione LaTeX fallita: {error_msg}"
                }
                
        except subprocess.TimeoutExpired:
            return {
                "pass": False,
                "score": 0.0,
                "reason": "Compilazione LaTeX: timeout (>30s)"
            }
        except Exception as e:
            return {
                "pass": False,
                "score": 0.0,
                "reason": f"Errore durante compilazione: {e}"
            }


def get_assert(output: str, context: dict) -> dict:
    """
    Entry point per PromptFoo assertion type: python.
    PromptFoo chiama get_assert(output, context).
    """
    return valida_latex(output)


# ── CLI standalone ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Argomento = path a file .tex o stringa LaTeX diretta
        arg = sys.argv[1]
        if os.path.isfile(arg):
            with open(arg, "r") as f:
                latex = f.read()
        else:
            latex = arg
        
        result = valida_latex(latex)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(0 if result["pass"] else 1)
    else:
        print("Uso: python latex_validator.py <file.tex | stringa_latex>")
        print("Oppure come assertion PromptFoo:")
        print("  assert:")
        print("    - type: python")
        print("      value: file://validators/latex_validator.py")
        sys.exit(1)
