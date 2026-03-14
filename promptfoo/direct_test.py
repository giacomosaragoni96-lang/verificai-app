#!/usr/bin/env python3
"""
Test diretto del provider con Gemini API
"""

import os
import sys

# Setup path
PROJECT_ROOT = os.environ.get("VERIFICAI_ROOT", "C:\\Users\\gobli\\Desktop\\verificai")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

sys.path.insert(0, os.path.dirname(__file__))

def test_direct_gemini():
    """Test diretto con Gemini"""
    print("🧪 Test diretto provider VerificAI + Gemini...")
    
    try:
        from providers.verificai_provider import call_api
        
        # Test caso titolo
        context = {
            "vars": {
                "prompt_type": "titolo",
                "materia": "Matematica",
                "argomento": "le derivate"
            }
        }
        
        options = {
            "config": {
                "model_id": "gemini-2.5-flash-lite",
                "temperature": 0.7
            }
        }
        
        prompt = "test"  # dummy prompt, il provider usa solo context.vars
        
        print("📞 Chiamata a Gemini...")
        result = call_api(prompt, options, context)
        
        if "error" in result:
            print(f"❌ Errore: {result['error']}")
            return False
        
        output = result.get("output", "")
        usage = result.get("tokenUsage", {})
        
        print(f"✅ Risposta Gemini: {output[:100]}...")
        print(f"📊 Token usage: {usage}")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Imposta API key se non c'è
    if not os.environ.get("GEMINI_API_KEY"):
        print("⚠️ GEMINI_API_KEY non impostata, uso placeholder")
        os.environ["GEMINI_API_KEY"] = "test_key"
    
    test_direct_gemini()
