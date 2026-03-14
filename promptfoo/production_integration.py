#!/usr/bin/env python3
"""
VerificAI Production Integration - Sistema Completo per Produzione
Integra comprehensive test suite con PromptFoo per produzione
"""

import os
import sys
import json
import subprocess
import time
from datetime import datetime

# Setup
PROJECT_ROOT = os.environ.get("VERIFICAI_ROOT", "C:\\Users\\gobli\\Desktop\\verificai")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

sys.path.insert(0, os.path.dirname(__file__))

def run_production_integration():
    """Integrazione completa del test suite in produzione"""
    
    print("🚀 VERIFICAI PRODUCTION INTEGRATION")
    print("=" * 80)
    print("🔧 Integrazione comprehensive test suite + PromptFoo per produzione")
    print(f"🔑 API Key: {'✅ Impostata' if os.environ.get('GEMINI_API_KEY') else '❌ Mancante'}")
    print(f"📅 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Step 1: Verifica ambiente
    print("📋 STEP 1: Verifica Ambiente")
    print("-" * 40)
    
    env_checks = {
        "GEMINI_API_KEY": os.environ.get('GEMINI_API_KEY'),
        "VERIFICAI_ROOT": os.environ.get('VERIFICAI_ROOT'),
        "Python": sys.version.split()[0],
        "PromptFoo": check_promptfoo_availability()
    }
    
    for check, value in env_checks.items():
        status = "✅" if value else "❌"
        print(f"  {status} {check}: {value if value else 'Non configurato'}")
    
    if not all([env_checks["GEMINI_API_KEY"], env_checks["VERIFICAI_ROOT"]]):
        print("\n❌ Ambiente non configurato correttamente")
        return False
    
    print()
    
    # Step 2: Test rapido con comprehensive suite
    print("📋 STEP 2: Test Rapido Comprehensive Suite")
    print("-" * 40)
    
    # Test solo high priority per verifica rapida
    high_priority_tests = [
        {
            "name": "[Matematica] Istituto Tecnico - Equazioni",
            "vars": {
                "prompt_type": "corpo", "materia": "Matematica", "argomento": "Equazioni di secondo grado",
                "livello": "Istituto Tecnico Tecnologico/Industriale", "durata": "50 minuti",
                "num_esercizi": 4, "punti_totali": 80, "mostra_punteggi": True, "e_mat": True
            }
        },
        {
            "name": "[Inglese] Liceo - Grammar",
            "vars": {
                "prompt_type": "corpo", "materia": "Inglese", "argomento": "Present Perfect vs Past Simple",
                "livello": "Liceo Scientifico", "durata": "45 minuti", "num_esercizi": 5,
                "punti_totali": 80, "mostra_punteggi": True
            }
        },
        {
            "name": "[Titolo] Test Rapido",
            "vars": {"prompt_type": "titolo", "materia": "Matematica", "argomento": "derivate"}
        }
    ]
    
    from providers.verificai_provider import call_api
    
    quick_results = []
    for test in high_priority_tests:
        print(f"  🧪 {test['name']}")
        
        try:
            options = {"config": {"model_id": "gemini-2.5-flash-lite", "temperature": 0.7}}
            context = {"vars": test["vars"]}
            
            result = call_api("test", options, context)
            
            if "error" in result:
                print(f"    ❌ Errore: {result['error']}")
                quick_results.append(False)
            else:
                output = result.get("output", "")
                usage = result.get("tokenUsage", {})
                print(f"    ✅ Output: {len(output)} chars, {usage.get('total', 0)} tokens")
                quick_results.append(True)
                
        except Exception as e:
            print(f"    ❌ Errore: {e}")
            quick_results.append(False)
    
    quick_success_rate = sum(quick_results) / len(quick_results) * 100
    print(f"\n  📊 Quick Test Success Rate: {quick_success_rate:.1f}%")
    
    if quick_success_rate < 80:
        print("  ⚠️ Test rapidi falliti - procedere con cautela")
    else:
        print("  ✅ Test rapidi superati - procedere con integrazione")
    
    print()
    
    # Step 3: Prepara PromptFoo configuration
    print("📋 STEP 3: Prepara PromptFoo Configuration")
    print("-" * 40)
    
    # Copia enhanced config per produzione
    enhanced_config = "enhanced_promptfooconfig.yaml"
    production_config = "production_promptfooconfig.yaml"
    
    try:
        if os.path.exists(enhanced_config):
            import shutil
            shutil.copy2(enhanced_config, production_config)
            print(f"  ✅ Configuration copiata: {production_config}")
        else:
            print(f"  ❌ Configuration non trovata: {enhanced_config}")
            return False
    except Exception as e:
        print(f"  ❌ Errore copia configuration: {e}")
        return False
    
    print()
    
    # Step 4: Esecuzione PromptFoo Production
    print("📋 STEP 4: Esecuzione PromptFoo Production")
    print("-" * 40)
    
    # Esegui PromptFoo con configuration di produzione
    cmd = [
        "C:\\Program Files\\nodejs\\npx.cmd",
        "promptfoo@latest",
        "eval",
        "-c", production_config,
        "-j", "1",
        "--no-cache"
    ]
    
    print(f"  🚀 Comando: {' '.join(cmd)}")
    print()
    
    try:
        # Esegui PromptFoo
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)  # 5 min timeout
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        print(f"  ⏱️  Execution time: {execution_time:.1f} seconds")
        print(f"  📤 Return code: {result.returncode}")
        
        if result.stdout:
            print("  📄 STDOUT:")
            print("  " + "\n  ".join(result.stdout.split('\n')[-20:]))  # Ultime 20 righe
        
        if result.stderr:
            print("  ❌ STDERR:")
            print("  " + "\n  ".join(result.stderr.split('\n')[-10:]))  # Ultime 10 righe
        
        promptfoo_success = result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("  ⏰ Timeout: PromptFoo execution timed out (5 min)")
        promptfoo_success = False
    except Exception as e:
        print(f"  ❌ Errore esecuzione PromptFoo: {e}")
        promptfoo_success = False
    
    print()
    
    # Step 5: Analisi risultati
    print("📋 STEP 5: Analisi Risultati Finali")
    print("-" * 40)
    
    # Cerca risultati PromptFoo
    results_file = None
    for file in os.listdir('.'):
        if file.startswith('promptfoo_results_') and file.endswith('.json'):
            results_file = file
            break
    
    if results_file and os.path.exists(results_file):
        try:
            with open(results_file, 'r', encoding='utf-8') as f:
                promptfoo_results = json.load(f)
            
            print(f"  📊 Risultati PromptFoo trovati: {results_file}")
            print(f"  📈 Total tests: {promptfoo_results.get('results', {}).get('total', 'N/A')}")
            print(f"  ✅ Passed: {promptfoo_results.get('results', {}).get('pass', 'N/A')}")
            print(f"  ❌ Failed: {promptfoo_results.get('results', {}).get('fail', 'N/A')}")
            
            # Calcola success rate
            total = promptfoo_results.get('results', {}).get('total', 0)
            passed = promptfoo_results.get('results', {}).get('pass', 0)
            if total > 0:
                success_rate = (passed / total) * 100
                print(f"  📊 Success Rate: {success_rate:.1f}%")
                
                if success_rate >= 80:
                    print("  🎉 EXCELLENT: Produzione ready!")
                elif success_rate >= 60:
                    print("  ✅ GOOD: Produzione accettabile")
                else:
                    print("  ⚠️ NEEDS WORK: Produzione da migliorare")
            
        except Exception as e:
            print(f"  ❌ Errore lettura risultati: {e}")
            promptfoo_results = None
    else:
        print("  ⚠️ Nessun file risultati PromptFoo trovato")
        promptfoo_results = None
    
    print()
    
    # Step 6: Report finale
    print("📋 STEP 6: Report Finale Integrazione")
    print("=" * 80)
    
    integration_status = {
        "environment": all([env_checks["GEMINI_API_KEY"], env_checks["VERIFICAI_ROOT"]]),
        "quick_tests": quick_success_rate >= 80,
        "configuration": os.path.exists(production_config),
        "promptfoo": promptfoo_success,
        "results": promptfoo_results is not None
    }
    
    all_passed = all(integration_status.values())
    
    print("🔍 Status Integrazione:")
    for component, status in integration_status.items():
        icon = "✅" if status else "❌"
        print(f"  {icon} {component.capitalize()}: {'OK' if status else 'FAIL'}")
    
    print()
    if all_passed:
        print("🎉 INTEGRAZIONE COMPLETATA CON SUCCESSO!")
        print("🚀 VerificAI è pronto per produzione!")
        print()
        print("📋 Prossimi passi:")
        print("  1. Usa PromptFoo per test continui")
        print("  2. Monitora performance con comprehensive suite")
        print("  3. Integra in CI/CD pipeline")
        print("  4. Setup alerting per test falliti")
    else:
        print("⚠️ INTEGRAZIONE PARZIALE - Alcuni componenti da verificare")
        print()
        print("🔧 Azioni correttive:")
        if not integration_status["environment"]:
            print("  - Configura environment variables (GEMINI_API_KEY, VERIFICAI_ROOT)")
        if not integration_status["quick_tests"]:
            print("  - Verifica provider e API connection")
        if not integration_status["promptfoo"]:
            print("  - Controlla installazione PromptFoo e configuration")
        if not integration_status["results"]:
            print("  - Verifica output directory e permissions")
    
    return all_passed

def check_promptfoo_availability():
    """Verifica se PromptFoo è disponibile"""
    try:
        result = subprocess.run(
            ["C:\\Program Files\\nodejs\\npx.cmd", "promptfoo@latest", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except:
        return None

if __name__ == "__main__":
    run_production_integration()
