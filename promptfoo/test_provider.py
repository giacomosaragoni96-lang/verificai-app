#!/usr/bin/env python3
"""
Test semplice per verificare che il provider funzioni
"""

import os
import sys

# Aggiungi la root del progetto al path
PROJECT_ROOT = os.environ.get("VERIFICAI_ROOT", "C:\\Users\\gobli\\Desktop\\verificai")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import del provider
sys.path.insert(0, os.path.dirname(__file__))
from providers.verificai_provider import _build_prompt

def test_provider():
    """Test del provider con un caso semplice"""
    print("🧪 Test del provider VerificAI...")
    
    # Test caso titolo
    vars_dict = {
        "prompt_type": "titolo",
        "materia": "Matematica", 
        "argomento:": "le derivate"
    }
    
    try:
        prompt = _build_prompt("titolo", vars_dict)
        print(f"✅ Titolo generato: {prompt[:100]}...")
        
        # Test caso corpo
        vars_dict = {
            "prompt_type": "corpo",
            "materia": "Matematica",
            "argomento": "Derivate",
            "livello": "Liceo Scientifico",
            "durata": "60 minuti",
            "num_esercizi": 5,
            "punti_totali": 100,
            "mostra_punteggi": True,
            "con_griglia": True,
            "e_mat": True
        }
        
        prompt = _build_prompt("corpo", vars_dict)
        print(f"✅ Corpo generato: {len(prompt)} caratteri")
        
        print("🎉 Provider funzionante!")
        return True
        
    except Exception as e:
        print(f"❌ Errore: {e}")
        return False

if __name__ == "__main__":
    test_provider()
