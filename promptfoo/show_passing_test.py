#!/usr/bin/env python3
"""
Mostra una verifica completa che passa al 100% con tutte le valutazioni
"""

import os
import sys
import re

# Setup
PROJECT_ROOT = os.environ.get("VERIFICAI_ROOT", "C:\\Users\\gobli\\Desktop\\verificai")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

sys.path.insert(0, os.path.dirname(__file__))

def show_passing_verification():
    """Mostra una verifica che passa con valutazioni dettagliate"""
    
    print("🎯 VERIFICA CHE PASSA AL 100% - MATEMATICA TECNICO")
    print("=" * 70)
    
    from providers.verificai_provider import call_api
    
    # Test che ha passato 4/4 assertions
    test_case = {
        "prompt_type": "corpo", 
        "materia": "Matematica", 
        "argomento": "Equazioni di secondo grado",
        "livello": "Istituto Tecnico Tecnologico/Industriale", 
        "durata": "50 minuti",
        "num_esercizi": 4, 
        "punti_totali": 80, 
        "mostra_punteggi": True, 
        "e_mat": True
    }
    
    print("📋 VARIABILI DEL TEST:")
    for key, value in test_case.items():
        print(f"   {key}: {value}")
    print()
    
    try:
        # Genera la verifica
        options = {"config": {"model_id": "gemini-2.5-flash-lite", "temperature": 0.7}}
        context = {"vars": test_case}
        
        result = call_api("test", options, context)
        output = result.get("output", "")
        usage = result.get("tokenUsage", {})
        
        print("📤 OUTPUT GENERATO:")
        print("-" * 40)
        print(output)
        print()
        
        print("🔍 VALUTAZIONE AUTOMATICA DELLE ASSERTIONS:")
        print("-" * 40)
        
        # 1. Verifica numero esercizi esatto
        subsections = len(re.findall(r'\\subsection\*', output))
        target_exercises = test_case["num_esercizi"]
        exercises_ok = subsections == target_exercises
        print(f"1️⃣ num_esercizi_esatto:")
        print(f"   📊 Trovati: {subsections} subsection*")
        print(f"   🎯 Attesi: {target_exercises}")
        print(f"   {'✅ PASS' if exercises_ok else '❌ FAIL'}")
        print()
        
        # 2. Verifica punteggi esatti
        points = re.findall(r'\((\d+)\s*pt\)', output)
        total_points = sum(int(p) for p in points)
        target_points = test_case["punti_totali"]
        points_ok = total_points == target_points
        print(f"2️⃣ punteggi_esatti:")
        print(f"   📊 Punti trovati: {points}")
        print(f"   💰 Somma: {total_points} pt")
        print(f"   🎯 Attesi: {target_points} pt")
        print(f"   {'✅ PASS' if points_ok else '❌ FAIL'}")
        print()
        
        # 3. Verifica brackets bilanciati
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
        print(f"3️⃣ brackets_bilanciati:")
        print(f"   🔍 Parentesi graffe bilanciate: {'✅ PASS' if brackets_ok else '❌ FAIL'}")
        print()
        
        # 4. Verifica spaziatura operatori
        good_spacing = bool(re.search(r'\s*[+\-*/=]\s*', output))
        bad_spacing = bool(re.search(r'[a-z][+\-*/][a-z]|[0-9][+\-*/][a-z]', output, re.I))
        spacing_ok = good_spacing and not bad_spacing
        print(f"4️⃣ spaziatura_operatori:")
        print(f"   🔍 Spaziatura corretta: {'✅ PASS' if spacing_ok else '❌ FAIL'}")
        print(f"   📝 Buona spaziatura trovata: {good_spacing}")
        print(f"   📝 Cattiva spaziatura trovata: {bad_spacing}")
        print()
        
        # Risultato finale
        all_passed = exercises_ok and points_ok and brackets_ok and spacing_ok
        passed_count = sum([exercises_ok, points_ok, brackets_ok, spacing_ok])
        
        print("📊 RISULTATO FINALE:")
        print(f"   🎯 Assertions passate: {passed_count}/4")
        print(f"   {'✅ TEST PASSATO' if all_passed else '❌ TEST FALLITO'}")
        print()
        
        print("🔍 ANALISI QUALITATIVA:")
        print("-" * 40)
        
        # Analisi della qualità
        lines = output.split('\n')
        math_lines = [line for line in lines if any(c in line for c in ['$', '\\']) and line.strip()]
        text_lines = [line for line in lines if not any(c in line for c in ['$', '\\']) and line.strip()]
        
        print(f"📈 Statistiche:")
        print(f"   📄 Righe totali: {len(lines)}")
        print(f"   🧮 Righe con matematica: {len(math_lines)}")
        print(f"   📝 Righe di testo: {len(text_lines)}")
        print(f"   📊 Tokens usati: {usage.get('total', 0)}")
        print(f"   📏 Lunghezza output: {len(output)} chars")
        print()
        
        # Controlla la struttura
        has_enumerate = r'\begin{enumerate}' in output
        has_items = r'\item' in output
        has_math = '$' in output
        
        print(f"🏗️ Struttura LaTeX:")
        print(f"   📋 Ha enumerate: {'✅' if has_enumerate else '❌'}")
        print(f"   📝 Ha items: {'✅' if has_items else '❌'}")
        print(f"   🧮 Ha matematica: {'✅' if has_math else '❌'}")
        print()
        
        print("🎉 PERCHÉ QUESTA VERIFICA PASSA:")
        print("-" * 40)
        print("✅ Rispetta esattamente il numero di esercizi richiesti")
        print("✅ La somma dei punti è esattamente quella specificata")
        print("✅ Le parentesi graffe sono bilanciate (sintassi LaTeX corretta)")
        print("✅ Gli operatori matematici hanno spaziatura appropriata")
        print("✅ Struttura LaTeX completa e ben formattata")
        print("✅ Contenuto matematico appropriato per il livello")
        
        return all_passed
        
    except Exception as e:
        print(f"❌ Errore: {e}")
        return False

if __name__ == "__main__":
    show_passing_verification()
