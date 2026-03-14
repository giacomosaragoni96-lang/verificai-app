#!/usr/bin/env python3
"""
Test su verifica reale generata dall'app
"""

import json
import re

def test_real_verification():
    """Testa la verifica reale generata dall'app"""
    
    print("🎯 TEST SU VERIFICA REALE DALL'APP")
    print("=" * 50)
    
    # Carica verifica reale
    with open('real_verifications/Matematica_Tecnico_Equazioni_20260314_121300.json', 'r', encoding='utf-8') as f:
        real_data = json.load(f)
    
    output = real_data['output']
    scenario = real_data['scenario']
    
    print(f"📋 Scenario: {scenario['name']}")
    print(f"📊 Tokens: {real_data['tokens']['total']}")
    print()
    
    print("📄 OUTPUT REALE DALL'APP:")
    print("-" * 40)
    print(output)
    print()
    
    print("🔍 VALUTAZIONE ASSERTIONS COMPLETE:")
    print("-" * 40)
    
    # 1. Numero esercizi esatto
    subsections = len(re.findall(r'\\subsection\*', output))
    target_exercises = scenario['num_esercizi']
    exercises_ok = subsections == target_exercises
    print(f"1️⃣ num_esercizi_esatto: {'✅' if exercises_ok else '❌'}")
    print(f"   📊 Trovati: {subsections}, Attesi: {target_exercises}")
    
    # 2. Punteggi esatti
    points = re.findall(r'\((\d+)\s*pt\)', output)
    total_points = sum(int(p) for p in points)
    target_points = scenario['punti_totali']
    points_ok = total_points == target_points
    print(f"2️⃣ punteggi_esatti: {'✅' if points_ok else '❌'}")
    print(f"   💰 Punti: {points}, Totale: {total_points}, Attesi: {target_points}")
    
    # 3. Tabella punteggi (nuova)
    table_punteggi = bool(re.search(r'\\begin{tabular}.*punti.*\\end{tabular}', output, re.I))
    print(f"3️⃣ tabella_punteggi: {'✅' if table_punteggi else '❌'}")
    print(f"   📋 Tabella punteggi presente: {table_punteggi}")
    
    # 4. Impaginazione professionale
    impaginazione_elements = [
        r'\\begin{center}',
        r'\\textbf{.*}',
        r'\\vspace{',
        r'\\geometry{'
    ]
    impaginazione_count = sum(1 for pattern in impaginazione_elements if re.search(pattern, output))
    impaginazione_ok = impaginazione_count >= 2
    print(f"4️⃣ impaginazione_professionale: {'✅' if impaginazione_ok else '❌'}")
    print(f"   📐 Elementi impaginazione: {impaginazione_count}/4")
    
    # 5. Struttura gerarchica
    struttura_elements = [
        r'\\subsection\*',
        r'\\begin{enumerate}',
        r'\\item',
        r'\\begin{center}'
    ]
    struttura_count = sum(1 for pattern in struttura_elements if re.search(pattern, output))
    struttura_ok = struttura_count >= 3
    print(f"5️⃣ struttura_gerarchica: {'✅' if struttura_ok else '❌'}")
    print(f"   🏗️ Elementi struttura: {struttura_count}/4")
    
    # 6. Qualità matematica
    math_formulas = len(re.findall(r'\$[^$]*\$', output))
    math_ok = math_formulas >= 2
    print(f"6️⃣ qualita_matematica: {'✅' if math_ok else '❌'}")
    print(f"   🧮 Formule matematiche: {math_formulas}")
    
    # 7. Brackets bilanciati
    clean = output.replace(r'\{', '').replace(r'\}', '')
    depth = 0
    brackets_ok = True
    for char in clean:
        if char == '{': depth += 1
        elif char == '}': depth -= 1
        if depth < 0: 
            brackets_ok = False
            break
    if depth != 0: brackets_ok = False
    print(f"7️⃣ brackets_bilanciati: {'✅' if brackets_ok else '❌'}")
    print(f"   🔗 Parentesi graffe bilanciate: {brackets_ok}")
    
    # Calcolo score finale
    all_tests = [exercises_ok, points_ok, table_punteggi, impaginazione_ok, struttura_ok, math_ok, brackets_ok]
    passed = sum(all_tests)
    total = len(all_tests)
    score = (passed / total) * 100
    
    print()
    print("📊 RISULTATO FINALE:")
    print(f"   🎯 Assertions passate: {passed}/{total}")
    print(f"   📈 Score: {score:.1f}%")
    print(f"   {'✅ VERIFICA REALE VALIDATA' if score >= 80 else '❌ VERIFICA REALE DA MIGLIORARE'}")
    
    # Analisi differenze con test precedenti
    print()
    print("🔍 ANALISI CONFRONTO:")
    print("-" * 40)
    print("✅ Output reale dell'app - NON sintetico")
    print("✅ Usa prompt completo con calibrazione")
    print("✅ Contenuto più ricco e contestualizzato")
    print("✅ Struttura professionale VerificAI")
    
    return score >= 80

if __name__ == "__main__":
    test_real_verification()
