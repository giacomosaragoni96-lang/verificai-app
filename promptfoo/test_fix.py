#!/usr/bin/env python3
"""
Test rapido della modifica ai prompt per il fix dei punti
"""

import os
import sys
import re

# Setup
PROJECT_ROOT = os.environ.get("VERIFICAI_ROOT", "C:\\Users\\gobli\\Desktop\\verificai")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

sys.path.insert(0, os.path.dirname(__file__))

def test_prompt_fix():
    """Test della modifica per il fix dei punti"""
    
    print("🧪 TEST MODIFICA PROMPT - Fix Punteggi")
    print("=" * 50)
    
    from providers.verificai_provider import call_api
    
    # Test case critico
    options = {"config": {"model_id": "gemini-2.5-flash-lite", "temperature": 0.7}}
    context = {"vars": {
        "prompt_type": "corpo", "materia": "Matematica", "argomento": "Derivate",
        "livello": "Liceo Scientifico", "durata": "60 minuti", "num_esercizi": 5,
        "punti_totali": 100, "mostra_punteggi": True, "con_griglia": True, "e_mat": True
    }}
    
    try:
        result = call_api("test", options, context)
        
        if "error" in result:
            print(f"❌ Errore API: {result['error']}")
            return False
        
        output = result.get("output", "")
        usage = result.get("tokenUsage", {})
        
        # Analisi output
        subsections = len(re.findall(r'\\subsection\*', output))
        points = re.findall(r'\((\d+)\s*pt\)', output)
        total_points = sum(int(p) for p in points)
        
        print(f"📤 Output: {len(output)} chars, {usage.get('total', 0)} tokens")
        print(f"📊 Metriche:")
        print(f"   - Subsections (esercizi): {subsections}")
        print(f"   - Punti trovati: {points}")
        print(f"   - Totale punti: {total_points}")
        print()
        
        # Verifica fix
        exercises_ok = subsections == 5
        points_ok = total_points == 100
        
        print(f"🔍 Verifica:")
        print(f"   - Esercizi: {subsections}/5 {'✅' if exercises_ok else '❌'}")
        print(f"   - Punti: {total_points}/100 {'✅' if points_ok else '❌'}")
        print()
        
        if exercises_ok and points_ok:
            print("🎉 FIX RIUSCITO! Il problema del doppio conteggio è risolto.")
            return True
        else:
            print("⚠️ Il fix non è completo. Analisi output:")
            
            # Analisi dettagliata
            lines = output.split('\n')
            for i, line in enumerate(lines[:20], 1):
                if 'pt' in line or '\\subsection*' in line:
                    print(f"   {i}: {line.strip()}")
            
            return False
            
    except Exception as e:
        print(f"❌ Errore test: {e}")
        return False

if __name__ == "__main__":
    test_prompt_fix()
