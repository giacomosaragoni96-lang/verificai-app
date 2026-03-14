# ── test_item_spacing.py ─────────────────────────────────────────────────────
# Test specifico per la spaziatura degli item nei sottopunti
# ───────────────────────────────────────────────────────────────────────────────

import re
from latex_utils import migliora_spaziatura_sottopunti

def test_item_spacing():
    """Test specifico per la spaziatura degli item."""
    
    # Test LaTeX con item attaccati (problema reale)
    test_latex = r"""
\subsection*{Esercizio 1: Concetti Base}
Si consideri la parabola di equazione $y = 2x^2 - 4x + 1$.
\begin{enumerate}[a)]
    \item L'equazione è scritta in forma canonica ($y = ax^2 + bx + c$). Chi sono i coefficienti $a$, $b$ e $c$? (3 pt)\item Il coefficiente $a$ è positivo o negativo? Cosa ci dice questo sulla concavità della parabola? (4 pt)\item Calcolare le coordinate del vertice della parabola utilizzando le formule $x_v = -\frac{b}{2a}$ e $y_v = -\frac{\Delta}{4a}$, dove $\Delta = b^2 - 4ac$. (8 pt)\item Determinare le coordinate dei punti di intersezione della parabola con l'asse y. (5 pt)
\end{enumerate}

\subsection*{Esercizio 2: Problema}
Trovare l'equazione della parabola con asse di simmetria parallelo all'asse y, sapendo che passa per i punti $A(1, 2)$, $B(0, 1)$ e $C(-1, 4)$. (20 pt)
"""
    
    print("🔍 Test Spaziatura Item Sottopunti")
    print("=" * 50)
    
    print("\n📋 Test originale (con problemi):")
    print("-" * 30)
    lines = test_latex.split('\n')
    for i, line in enumerate(lines[5:15], 5):  # Mostra solo le righe rilevanti
        if line.strip():
            print(f"{i:2d}: {line}")
    
    # Applica la funzione di spaziatura
    processed = migliora_spaziatura_sottopunti(test_latex)
    
    print("\n✅ Dopo il processing:")
    print("-" * 30)
    processed_lines = processed.split('\n')
    for i, line in enumerate(processed_lines[5:20], 5):  # Mostra più righe per vedere la differenza
        if line.strip():
            print(f"{i:2d}: {line}")
    
    # Test specifici
    print("\n🔍 Test Specifici:")
    
    # 1. Verifica che gli item abbiano spaziatura
    item_pattern = r'\\item\[[^\]]+\]'
    original_items = re.findall(item_pattern, test_latex)
    processed_items = re.findall(item_pattern, processed)
    
    print(f"   - Item originali: {len(original_items)}")
    print(f"   - Item processati: {len(processed_items)}")
    
    # 2. Verifica spaziatura tra item
    item_transitions = len(re.findall(r'\\item\[[^\]]+\].*?\n\s*\n\\item', processed, re.DOTALL))
    print(f"   - Transizioni item con spaziatura: {item_transitions}")
    
    # 3. Verifica newline multipli
    double_newlines = processed.count('\n\n')
    single_newlines = processed.count('\n')
    print(f"   - Newline doppi: {double_newlines}")
    print(f"   - Newline totali: {single_newlines}")
    
    # 4. Verifica spaziatura dopo subsection
    subsection_spacing = len(re.findall(r'\\subsection\*\{[^}]+\}\n\n', processed))
    print(f"   - Spaziatura dopo subsection: {subsection_spacing}")
    
    # Test di validazione
    tests = {
        "Item separati da newline doppi": item_transitions >= 3,
        "Spaziatura dopo subsection presente": subsection_spacing >= 2,
        "Newline doppi presenti": double_newlines > 5,
        "Numero item preservato": len(original_items) == len(processed_items)
    }
    
    print("\n📊 Risultati Test:")
    for test_name, result in tests.items():
        status = "✅" if result else "❌"
        print(f"   {status} {test_name}")
    
    # Mostra un esempio specifico
    print("\n📄 Esempio dettagliato (Esercizio 1):")
    print("-" * 40)
    
    # Estrai solo l'Esercizio 1
    esercizio1_match = re.search(r'\\subsection\*\{Esercizio 1[^}]*\}(.*?)\\end\{enumerate\}', processed, re.DOTALL)
    if esercizio1_match:
        esercizio1_text = esercizio1_match.group(1)
        print(esercizio1_text.strip())
    
    # Riassunto finale
    passed_tests = sum(tests.values())
    total_tests = len(tests)
    
    print(f"\n🎯 Riassunto: {passed_tests}/{total_tests} test passati")
    
    if passed_tests == total_tests:
        print("🎉 Spaziatura item funzionante correttamente!")
        return True
    else:
        print("⚠️ Alcuni problemi di spaziatura rimangono.")
        return False

if __name__ == "__main__":
    test_item_spacing()
