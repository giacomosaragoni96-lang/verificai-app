#!/usr/bin/env python3
"""
Analisi dettagliata dei test per capire come vengono valutate le verifiche
"""

import os
import sys
import json

# Setup
PROJECT_ROOT = os.environ.get("VERIFICAI_ROOT", "C:\\Users\\gobli\\Desktop\\verificai")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

sys.path.insert(0, os.path.dirname(__file__))

def analyze_test_results():
    """Analisi dettagliata dei risultati dei test"""
    
    print("🔍 ANALISI DETTAGLIATA TEST VERIFICAI")
    print("=" * 60)
    
    # Carica risultati
    with open('comprehensive_test_results.json', 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    print(f"📊 Overview: {results['passed']}/{results['total_tests']} test superati")
    print()
    
    # Analisi test passati
    print("✅ TEST PASSATI - ANALISI DETTAGLIATA")
    print("-" * 40)
    
    passed_tests = [t for t in results['detailed_results'] if t['status'] == 'PASS']
    
    for test in passed_tests:
        print(f"🎯 {test['test_name']}")
        print(f"   📂 Categoria: {test['category']}")
        print(f"   📊 Assertions: {test['assertions_passed']}/{test['assertions_total']}")
        print(f"   📤 Output: {test['output_length']} chars, {test['tokens']} tokens")
        print()
    
    # Analisi test falliti
    print("❌ TEST FALLITI - ANALISI PROBLEMI")
    print("-" * 40)
    
    failed_tests = [t for t in results['detailed_results'] if t['status'] == 'FAIL']
    
    # Mostra i primi 3 test falliti più significativi
    high_priority_failed = [t for t in failed_tests if t['priority'] == 'High'][:3]
    
    for test in high_priority_failed:
        print(f"⚠️ {test['test_name']}")
        print(f"   📂 Categoria: {test['category']} | Priorità: {test['priority']}")
        print(f"   📊 Assertions: {test['assertions_passed']}/{test['assertions_total']}")
        print(f"   📤 Output: {test['output_length']} chars, {test['tokens']} tokens")
        
        # Calcola fall rate
        fail_rate = ((test['assertions_total'] - test['assertions_passed']) / test['assertions_total']) * 100
        print(f"   📉 Fall rate: {fail_rate:.1f}%")
        print()
    
    # Esempio di output reale
    print("📄 ESEMPIO OUTPUT REALE - Test Passato")
    print("-" * 40)
    
    from providers.verificai_provider import call_api
    
    # Test che ha passato al 100%
    test_example = {
        "prompt_type": "corpo", "materia": "Matematica", "argomento": "Derivate",
        "livello": "Liceo Scientifico", "durata": "60 minuti", "num_esercizi": 5,
        "punti_totali": 100, "mostra_punteggi": True, "con_griglia": True, "e_mat": True
    }
    
    try:
        options = {"config": {"model_id": "gemini-2.5-flash-lite", "temperature": 0.7}}
        context = {"vars": test_example}
        
        result = call_api("test", options, context)
        output = result.get("output", "")
        
        print("📝 Output LaTeX generato:")
        print("-" * 20)
        print(output[:800] + "..." if len(output) > 800 else output)
        print()
        
        # Analisi dell'output
        import re
        subsections = len(re.findall(r'\\subsection\*', output))
        points = re.findall(r'\((\d+)\s*pt\)', output)
        total_points = sum(int(p) for p in points)
        
        print("🔍 Analisi automatica:")
        print(f"   📊 Esercizi trovati: {subsections}")
        print(f"   💰 Punti trovati: {points}")
        print(f"   💰 Totale punti: {total_points}")
        print(f"   ✅ Corrisponde alle attese: {subsections == 5 and total_points == 100}")
        
    except Exception as e:
        print(f"❌ Errore esempio: {e}")
    
    print()
    print("🎯 COME FUNZIONA LA VALUTAZIONE:")
    print("-" * 40)
    print("1. 📋 Ogni test ha variabili specifiche (materia, livello, punteggi)")
    print("2. 🤖 Gemini genera output LaTeX basato sulle variabili")
    print("3. 🔍 Le assertions verificano:")
    print("   - Numero esatto di esercizi (\\subsection*)")
    print("   - Somma esatta dei punti (100, 80, 0, etc.)")
    print("   - Qualità del contenuto (formule, struttura, leggibilità)")
    print("4. ✅ Test PASS se tutte le assertions sono soddisfatte")
    print("5. 📊 Report completo salvato in JSON per analisi")

if __name__ == "__main__":
    analyze_test_results()
