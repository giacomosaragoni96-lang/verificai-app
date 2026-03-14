# ── test_post_processing.py ─────────────────────────────────────────────────
# Test per verificare il funzionamento del post-processing LaTeX
# ───────────────────────────────────────────────────────────────────────────────

import re
from latex_utils import aggiungi_spaziatura_grafici_tabelle, migliora_spaziatura_sottopunti, limita_altezza_grafici

def test_post_processing():
    """Test del post-processing LaTeX."""
    
    # Test LaTeX con problemi
    test_latex = r"""
\documentclass[12pt,a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage[italian]{babel}
\usepackage{amsmath,amsfonts,amssymb}
\geometry{margin=2cm}
\pagestyle{empty}
\begin{document}

\begin{center}
  \textbf{\large Verifica di Matematica: Grafico della parabola} \\
  \vspace{0.3cm}
  \small \textbf{Nome:} \underline{\hspace{6cm}} \quad \textbf{Classe e Data:} \underline{\hspace{4cm}} \\
  \vspace{0.3cm}
  \textit{\small Svolgere tutti gli esercizi mostrando i passaggi.}
\end{center}
\subsection*{Esercizio 1: Concetti Base della Parabola}
Si consideri la parabola di equazione $y = 2x^2 - 4x + 1$.
\begin{enumerate}[a)]
    \item L'equazione è scritta in forma canonica ($y = ax^2 + bx + c$). Chi sono i coefficienti $a$, $b$ e $c$? (3 pt)
    \item Il coefficiente $a$ è positivo o negativo? Cosa ci dice questo sulla concavità della parabola? (4 pt)
    \item Calcolare le coordinate del vertice della parabola utilizzando le formule $x_v = -\frac{b}{2a}$ e $y_v = -\frac{\Delta}{4a}$, dove $\Delta = b^2 - 4ac$. (8 pt)
    \item Determinare le coordinate dei punti di intersezione della parabola con l'asse y. (5 pt)
\end{enumerate}

\subsection*{Esercizio 2: Determinazione dell'Equazione di una Parabola}
Trovare l'equazione della parabola con asse di simmetria parallelo all'asse y, sapendo che passa per i punti $A(1, 2)$, $B(0, 1)$ e $C(-1, 4)$. (20 pt)

\subsection*{Esercizio 3: Studio di una Parabola con Grafico Fornito}
Si osservi il seguente grafico di una parabola.

[Grafico]

\begin{enumerate}[a)]
    \item Determinare le coordinate del vertice della parabola dal grafico. (5 pt)
    \item Indicare le coordinate dei punti di intersezione della parabola con l'asse y. (5 pt)
    \item Scrivere l'equazione della parabola, verificando che sia coerente con il grafico osservato. (10 pt)
\end{enumerate}

\subsection*{Esercizio 4: Posizione Reciproca tra Retta e Parabola}
Data la parabola di equazione $y = x^2 - 3x + 2$ e la retta di equazione $y = x - 1$.
\begin{enumerate}[a)]
    \item Determinare le coordinate dei punti di intersezione tra la retta e la parabola, risolvendo il sistema di equazioni. (10 pt)
    \item Stabilire se la retta è secante, tangente o esterna alla parabola. (5 pt)
    \item Calcolare la distanza tra i punti di intersezione trovati. (5 pt)
\end{enumerate}

\subsection*{Esercizio 5: Vero o Falso}
Stabilire se le seguenti affermazioni riguardanti una parabola di equazione $y = ax^2 + bx + c$ sono Vere (V) o False (F).
\begin{enumerate}[a)]
    \item Se $a < 0$, la parabola ha concavità rivolta verso l'alto. (3 pt) $\square$ \textbf{V} $\quad\square$ \textbf{F}
    \item Il vertice di una parabola ha sempre coordinate intere. (3 pt) $\square$ \textbf{V} $\quad\square$ \textbf{F}
    \item Se il discriminante $\Delta = b^2 - 4ac$ è positivo, la parabola interseca l'asse x in due punti distinti. (4 pt) $\square$ \textbf{V} $\quad\square$ \textbf{F}
    \item L'asse di simmetria di una parabola è sempre una retta verticale. (4 pt) $\square$ \textbf{V} $\quad\square$ \textbf{F}
    \item La parabola $y = x^2 + 1$ non interseca mai l'asse x. (3 pt) $\square$ \textbf{V} $\quad\square$ \textbf{F}
    \item Se una parabola passa per l'origine $(0,0)$, allora il termine noto $c$ è nullo. (3 pt) $\square$ \textbf{V} $\quad\square$ \textbf{F}
\end{enumerate}
\vfill
% GRIGLIA
\begin{center}
\textbf{Tabella Punteggi}\\[0.3cm]
{\renewcommand{\arraystretch}{1.8}
\adjustbox{max width=\textwidth}{
[Tabella]
}}
\end{center}

\end{document}
"""
    
    print("🔍 Test Post-Processing LaTeX")
    print("=" * 50)
    
    # Test 1: Sostituzione placeholder
    print("\n1. Test Sostituzione Placeholder...")
    processed = aggiungi_spaziatura_grafici_tabelle(test_latex)
    
    if "[Grafico]" not in processed:
        print("✅ Placeholder [Grafico] sostituito")
    else:
        print("❌ Placeholder [Grafico] non sostituito")
    
    if "[Tabella]" not in processed:
        print("✅ Placeholder [Tabella] sostituito")
    else:
        print("❌ Placeholder [Tabella] non sostituito")
    
    # Test 2: Spaziatura sottopunti
    print("\n2. Test Spaziatura Sottopunti...")
    processed_spacing = migliora_spaziatura_sottopunti(test_latex)
    
    # Controlla se ci sono spaziature appropriate
    subsection_count = len(re.findall(r'\\subsection\*', processed_spacing))
    double_newlines = len(re.findall(r'\n\n', processed_spacing))
    
    print(f"   - Subsections trovate: {subsection_count}")
    print(f"   - Doppi newline: {double_newlines}")
    
    if double_newlines > 10:  # Dovrebbe averne parecchie dopo il processing
        print("✅ Spaziatura migliorata")
    else:
        print("❌ Spaziatura non migliorata")
    
    # Test 3: Limiti grafici
    print("\n3. Test Limiti Grafici...")
    test_tikz = r"""
    \begin{tikzpicture}
    \begin{axis}
    \addplot{x^2};
    \end{axis}
    \end{tikzpicture}
    """
    
    processed_graph = limita_altezza_grafici(test_tikz)
    
    if "height=5cm" in processed_graph and "width=9cm" in processed_graph:
        print("✅ Limiti grafici applicati")
    else:
        print("❌ Limiti grafici non applicati")
    
    # Test 4: Processing completo
    print("\n4. Test Processing Completo...")
    final_processed = test_latex
    final_processed = aggiungi_spaziatura_grafici_tabelle(final_processed)
    final_processed = migliora_spaziatura_sottopunti(final_processed)
    final_processed = limita_altezza_grafici(final_processed)
    
    # Verifiche finali
    checks = {
        "Placeholder [Grafico] rimosso": "[Grafico]" not in final_processed,
        "Placeholder [Tabella] rimosso": "[Tabella]" not in final_processed,
        "TikZ graph inserito": "\\begin{tikzpicture}" in final_processed,
        "Tabella inserita": "\\begin{tabular}" in final_processed,
        "Spaziatura migliorata": final_processed.count('\n\n') > test_latex.count('\n\n'),
        "Limiti grafici presenti": "height=5cm" in final_processed
    }
    
    for check, result in checks.items():
        status = "✅" if result else "❌"
        print(f"   {status} {check}")
    
    # Salva risultato per ispezione
    with open("test_output.tex", "w", encoding="utf-8") as f:
        f.write(final_processed)
    
    print(f"\n📄 Risultato salvato in 'test_output.tex' per ispezione")
    
    # Riassunto
    passed_checks = sum(checks.values())
    total_checks = len(checks)
    
    print(f"\n📊 Risultati: {passed_checks}/{total_checks} test passati")
    
    if passed_checks == total_checks:
        print("🎉 Tutti i test passati! Post-processing funzionante.")
        return True
    else:
        print("⚠️ Alcuni test falliti. Controlla i problemi.")
        return False

if __name__ == "__main__":
    test_post_processing()
