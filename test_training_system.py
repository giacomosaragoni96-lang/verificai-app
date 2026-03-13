# ── test_training_system.py ─────────────────────────────────────────────────────
# Test per verificare il funzionamento del sistema di training AI
# ───────────────────────────────────────────────────────────────────────────────

import logging
import sys
import os

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_imports():
    """Test che tutti i moduli training si importino correttamente."""
    print("🔍 Test import moduli training...")
    
    try:
        from training_data import analyze_exercise_features, save_feedback, update_training_patterns
        print("✅ training_data.py importato")
    except ImportError as e:
        print(f"❌ Errore import training_data.py: {e}")
        return False
    
    try:
        from rating_system import render_feedback_buttons, render_feedback_prompt
        print("✅ rating_system.py importato")
    except ImportError as e:
        print(f"❌ Errore import rating_system.py: {e}")
        return False
    
    try:
        from prompt_enhancer import enhance_prompt_with_training, should_use_training_enhancement
        print("✅ prompt_enhancer.py importato")
    except ImportError as e:
        print(f"❌ Errore import prompt_enhancer.py: {e}")
        return False
    
    try:
        from background_training import BackgroundTrainingProcessor
        print("✅ background_training.py importato")
    except ImportError as e:
        print(f"❌ Errore import background_training.py: {e}")
        return False
    
    try:
        from training_dashboard import render_training_dashboard
        print("✅ training_dashboard.py importato")
    except ImportError as e:
        print(f"❌ Errore import training_dashboard.py: {e}")
        return False
    
    return True


def test_feature_extraction():
    """Test l'estrazione delle caratteristiche da LaTeX."""
    print("\n🔍 Test feature extraction...")
    
    try:
        from training_data import analyze_exercise_features
        
        # Test LaTeX content
        test_latex = r"""
\subsection*{Esercizio 1}
\begin{enumerate}
\item[a)] Risolvi l'equazione $2x + 3 = 7$ (5 pt)
\item[b)] Calcola l'integrale $\int x^2 dx$ (3 pt)
\end{enumerate}

\begin{tikzpicture}
\begin{axis}
\addplot{sin(x)};
\end{axis}
\end{tikzpicture}
"""
        
        features = analyze_exercise_features(test_latex)
        
        # Verifiche base
        assert features['num_esercizi'] == 1, f"Atteso 1 esercizio, got {features['num_esercizi']}"
        assert features['has_punteggi'] == True, "Atteso punteggi presenti"
        assert features['has_grafici'] == True, "Atteso grafici presenti"
        assert 'grafico' in features['exercise_types'], "Atteso tipo grafico"
        
        print("✅ Feature extraction test passato")
        print(f"   - Esercizi: {features['num_esercizi']}")
        print(f"   - Punteggi: {features['has_punteggi']}")
        print(f"   - Grafici: {features['has_grafici']}")
        print(f"   - Tipi: {features['exercise_types']}")
        print(f"   - Score struttura: {features['structure_score']:.2f}")
        print(f"   - Score qualità: {features['content_quality']:.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore feature extraction: {e}")
        return False


def test_prompt_enhancement():
    """Test l'enhancement dei prompt."""
    print("\n🔍 Test prompt enhancement...")
    
    try:
        from prompt_enhancer import enhance_prompt_with_training, should_use_training_enhancement
        
        # Test base
        base_prompt = "Genera una verifica di matematica su equazioni."
        enhanced = enhance_prompt_with_training(base_prompt, "Matematica", "Medie", None)
        
        # Senza database dovrebbe restituire prompt base
        assert base_prompt in enhanced, "Enhanced prompt dovrebbe contenere base prompt"
        
        print("✅ Prompt enhancement test passato")
        print(f"   - Base prompt: {len(base_prompt)} caratteri")
        print(f"   - Enhanced: {len(enhanced)} caratteri")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore prompt enhancement: {e}")
        return False


def test_background_processor():
    """Test il background processor."""
    print("\n🔍 Test background processor...")
    
    try:
        from background_training import BackgroundTrainingProcessor
        
        # Mock supabase client
        class MockSupabase:
            def table(self, name):
                return self
            
            def select(self, *args):
                return self
            
            def execute(self):
                return type('Result', (), {'data': []})()
            
            def insert(self, data):
                return self
            
            def delete(self):
                return self
            
            def lt(self, field, value):
                return self
            
            def gte(self, field, value):
                return self
            
            def order(self, field, direction):
                return self
            
            def limit(self, count):
                return self
        
        mock_supabase = MockSupabase()
        processor = BackgroundTrainingProcessor(mock_supabase)
        
        # Test status
        status = processor.get_status()
        assert 'running' in status, "Status dovrebbe contenere 'running'"
        assert 'last_update' in status, "Status dovrebbe contenere 'last_update'"
        
        print("✅ Background processor test passato")
        print(f"   - Status: {status}")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore background processor: {e}")
        return False


def test_rating_system():
    """Test il sistema di rating."""
    print("\n🔍 Test rating system...")
    
    try:
        from rating_system import get_feedback_summary
        
        # Mock supabase
        class MockSupabase:
            def table(self, name):
                return self
            
            def select(self, *args):
                return self
            
            def execute(self):
                return type('Result', (), {'data': []})()
        
        mock_supabase = MockSupabase()
        summary = get_feedback_summary(mock_supabase)
        
        # Verifiche base
        assert 'total' in summary, "Summary dovrebbe contenere 'total'"
        assert 'good' in summary, "Summary dovrebbe contenere 'good'"
        assert 'rate' in summary, "Summary dovrebbe contenere 'rate'"
        
        print("✅ Rating system test passato")
        print(f"   - Summary: {summary}")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore rating system: {e}")
        return False


def run_all_tests():
    """Esegue tutti i test."""
    print("🚀 Test Sistema Training AI per VerificAI")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_feature_extraction,
        test_prompt_enhancement,
        test_background_processor,
        test_rating_system,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test fallito con eccezione: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Risultati: {passed}/{total} test passati")
    
    if passed == total:
        print("🎉 Tutti i test passati! Sistema training pronto.")
        return True
    else:
        print("⚠️ Alcuni test falliti. Controlla gli errori sopra.")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
