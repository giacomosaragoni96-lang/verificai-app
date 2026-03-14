#!/usr/bin/env python3
"""
Sistema Completo per Test Verifiche Reali VerificAI
1. Genera verifiche nell'app e le cattura
2. Sistema per salvare output reali
3. Integrazione test nel flusso dell'app
"""

import os
import sys
import json
import subprocess
from datetime import datetime
from pathlib import Path

# Setup
PROJECT_ROOT = os.environ.get("VERIFICAI_ROOT", "C:\\Users\\gobli\\Desktop\\verificai")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

sys.path.insert(0, os.path.dirname(__file__))

class RealVerificationTestSystem:
    def __init__(self):
        self.captured_outputs = []
        self.test_results = []
        self.output_dir = Path("real_verifications")
        self.output_dir.mkdir(exist_ok=True)
        
    def generate_real_verifications(self):
        """1. Genera verifiche reali usando l'app"""
        print("🎯 FASE 1: GENERAZIONE VERIFICHE REALI")
        print("=" * 50)
        
        # Scenari di test reali
        real_scenarios = [
            {
                "name": "Matematica_Tecnico_Equazioni",
                "materia": "Matematica",
                "livello": "Istituto Tecnico Tecnologico/Industriale",
                "argomento": "Equazioni di secondo grado",
                "num_esercizi": 4,
                "punti_totali": 80,
                "mostra_punteggi": True,
                "con_griglia": True,
                "e_mat": True
            },
            {
                "name": "Italiano_Liceo_AnalisiTesto",
                "materia": "Italiano", 
                "livello": "Liceo Scientifico",
                "argomento": "Analisi del testo poetico",
                "num_esercizi": 4,
                "punti_totali": 100,
                "mostra_punteggi": True,
                "con_griglia": True
            },
            {
                "name": "Fisica_Liceo_Meccanica",
                "materia": "Fisica",
                "livello": "Liceo Scientifico", 
                "argomento": "Leggi di Newton",
                "num_esercizi": 3,
                "punti_totali": 100,
                "mostra_punteggi": True,
                "e_mat": True
            }
        ]
        
        for scenario in real_scenarios:
            print(f"📝 Generazione: {scenario['name']}")
            
            # Simula il flusso completo dell'app
            try:
                from providers.verificai_provider import call_api
                from prompts import prompt_corpo_verifica
                
                # Usa le stesse funzioni dell'app
                calibrazione = self._get_calibrazione(scenario['livello'])
                
                # Parametri completi per prompt_corpo_verifica
                prompt_params = {
                    "materia": scenario['materia'],
                    "argomento": scenario['argomento'],
                    "calibrazione": calibrazione,
                    "durata": scenario['durata'],
                    "num_esercizi": scenario['num_esercizi'],
                    "punti_totali": scenario['punti_totali'],
                    "mostra_punteggi": scenario['mostra_punteggi'],
                    "con_griglia": scenario.get('con_griglia', False),
                    "note_generali": "",
                    "istruzioni_esercizi": "",
                    "e_mat": scenario.get('e_mat', False),
                    "titolo_header": "",
                    "preambolo_fisso": "",
                    "mathpix_context": None
                }
                
                prompt = prompt_corpo_verifica(**prompt_params)
                
                # Chiama Gemini come l'app
                options = {"config": {"model_id": "gemini-2.5-flash-lite", "temperature": 0.7}}
                context = {"vars": scenario}
                
                result = call_api("test", options, context)
                output = result.get("output", "")
                
                # Salva output reale
                output_data = {
                    "scenario": scenario,
                    "prompt_used": prompt,
                    "output": output,
                    "timestamp": datetime.now().isoformat(),
                    "tokens": result.get("tokenUsage", {})
                }
                
                # Salva su file
                filename = f"{scenario['name']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                filepath = self.output_dir / filename
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(output_data, f, indent=2, ensure_ascii=False)
                
                self.captured_outputs.append(output_data)
                print(f"   ✅ Salvato: {filename}")
                print(f"   📊 Tokens: {result.get('tokenUsage', {}).get('total', 0)}")
                
            except Exception as e:
                print(f"   ❌ Errore: {e}")
        
        print(f"\n🎉 Generate {len(self.captured_outputs)} verifiche reali!")
        return self.captured_outputs
    
    def create_capture_system(self):
        """2. Sistema per catturare output reali"""
        print("\n🔧 FASE 2: SISTEMA CAPTURE OUTPUT REALI")
        print("=" * 50)
        
        # Crea sistema di monitoraggio
        capture_system = {
            "monitoring": {
                "output_directory": str(self.output_dir),
                "auto_capture": True,
                "timestamp_format": "%Y%m%d_%H%M%S",
                "backup_enabled": True
            },
            "validation_rules": {
                "required_sections": ["\\subsection*", "\\begin{enumerate}", "\\item"],
                "required_elements": ["pt", "punti", "esercizi"],
                "quality_checks": ["brackets_bilanciati", "spaziatura_operatori"]
            },
            "integration_points": [
                "main.py -> dopo generazione",
                "docx_export.py -> prima export", 
                "generation.py -> dopo prompt"
            ]
        }
        
        # Salva configurazione sistema
        config_file = self.output_dir / "capture_system_config.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(capture_system, f, indent=2, ensure_ascii=False)
        
        print("✅ Sistema capture configurato")
        print(f"📁 Directory output: {self.output_dir}")
        print(f"⚙️ Configurazione: {config_file}")
        
        return capture_system
    
    def integrate_app_tests(self):
        """3. Integrazione test nel flusso dell'app"""
        print("\n🔗 FASE 3: INTEGRAZIONE TEST NELL'APP")
        print("=" * 50)
        
        # Crea modulo di integrazione per l'app
        integration_code = '''"""
VerificAI Real Test Integration - Da aggiungere a main.py
"""

import os
import json
from datetime import datetime
from pathlib import Path

def capture_real_verification(output, scenario_vars, stage="generation"):
    """Cattura output reale durante generazione app"""
    
    # Directory per output reali
    output_dir = Path("real_verifications")
    output_dir.mkdir(exist_ok=True)
    
    # Dati da catturare
    capture_data = {
        "scenario_vars": scenario_vars,
        "output": output,
        "stage": stage,
        "timestamp": datetime.now().isoformat(),
        "user_session": os.environ.get("VERIFICAI_SESSION", "unknown")
    }
    
    # Salva con timestamp
    filename = f"real_capture_{stage}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = output_dir / filename
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(capture_data, f, indent=2, ensure_ascii=False)
    
    return filepath

def validate_real_output(output, scenario_vars):
    """Valida output reale con assertions complete"""
    
    import re
    
    validation_results = {
        "scenario": scenario_vars.get("materia", "unknown"),
        "timestamp": datetime.now().isoformat(),
        "assertions": {},
        "overall_score": 0
    }
    
    # Assertions complete
    assertions_passed = 0
    total_assertions = 0
    
    # 1. Numero esercizi esatto
    subsections = len(re.findall(r'\\\\subsection\\*', output))
    target_exercises = scenario_vars.get("num_esercizi", 0)
    exercises_ok = subsections == target_exercises
    validation_results["assertions"]["num_esercizi_esatto"] = {
        "passed": exercises_ok,
        "found": subsections,
        "expected": target_exercises
    }
    total_assertions += 1
    if exercises_ok: assertions_passed += 1
    
    # 2. Punteggi esatti
    points = re.findall(r'\\((\\d+)\\s*pt\\)', output)
    total_points = sum(int(p) for p in points)
    target_points = scenario_vars.get("punti_totali", 0)
    points_ok = total_points == target_points
    validation_results["assertions"]["punteggi_esatti"] = {
        "passed": points_ok,
        "found": points,
        "total": total_points,
        "expected": target_points
    }
    total_assertions += 1
    if points_ok: assertions_passed += 1
    
    # 3. Tabella punteggi (nuova assertion)
    table_punteggi = bool(re.search(r'\\\\begin\\{tabular\\}.*punti.*\\\\end\\{tabular\\}', output, re.I))
    validation_results["assertions"]["tabella_punteggi"] = {
        "passed": table_punteggi,
        "found": table_punteggi
    }
    total_assertions += 1
    if table_punteggi: assertions_passed += 1
    
    # 4. Impaginazione professionale
    impaginazione_elements = [
        r'\\\\begin\\{center\\}',
        r'\\\\textbf\\{.*\\\\}',
        r'\\\\vspace\\{',
        r'\\\\geometry\\{'
    ]
    impaginazione_ok = any(re.search(pattern, output) for pattern in impaginazione_elements)
    validation_results["assertions"]["impaginazione_professionale"] = {
        "passed": impaginazione_ok,
        "elements_found": len([p for p in impaginazione_elements if re.search(p, output)])
    }
    total_assertions += 1
    if impaginazione_ok: assertions_passed += 1
    
    # 5. Struttura gerarchica
    struttura_elements = [
        r'\\\\subsection\\*',
        r'\\\\begin\\{enumerate\\}',
        r'\\\\item',
        r'\\\\begin\\{center\\}'
    ]
    struttura_count = sum(1 for pattern in struttura_elements if re.search(pattern, output))
    struttura_ok = struttura_count >= 3
    validation_results["assertions"]["struttura_gerarchica"] = {
        "passed": struttura_ok,
        "elements_count": struttura_count
    }
    total_assertions += 1
    if struttura_ok: assertions_passed += 1
    
    # Calcola score finale
    validation_results["overall_score"] = (assertions_passed / total_assertions) * 100
    validation_results["assertions_passed"] = assertions_passed
    validation_results["assertions_total"] = total_assertions
    
    return validation_results

# In main.py, aggiungi dopo generazione:
# capture_real_verification(output, user_vars, "generation")
# validation = validate_real_output(output, user_vars)
'''
        
        # Salva modulo integrazione
        integration_file = self.output_dir / "app_integration.py"
        with open(integration_file, 'w', encoding='utf-8') as f:
            f.write(integration_code)
        
        print("✅ Modulo integrazione creato")
        print(f"📄 File: {integration_file}")
        print("📋 Istruzioni per aggiungere a main.py incluse")
        
        return integration_file
    
    def _get_calibrazione(self, livello):
        """Ottiene calibrazione dal sistema VerificAI"""
        try:
            from config import CALIBRAZIONE_SCUOLA
            return CALIBRAZIONE_SCUOLA.get(livello, "")
        except:
            return ""
    
    def run_complete_system(self):
        """Esegue il sistema completo"""
        print("🚀 SISTEMA COMPLETO TEST VERIFICHE REALI")
        print("=" * 60)
        print("1. Generazione verifiche reali dall'app")
        print("2. Sistema capture output reali") 
        print("3. Integrazione test nel flusso app")
        print()
        
        # Fase 1: Generazione
        real_outputs = self.generate_real_verifications()
        
        # Fase 2: Sistema capture
        capture_system = self.create_capture_system()
        
        # Fase 3: Integrazione
        integration_file = self.integrate_app_tests()
        
        # Report finale
        print("\n📊 REPORT FINALE SISTEMA COMPLETO")
        print("=" * 60)
        print(f"✅ Verifiche reali generate: {len(real_outputs)}")
        print(f"✅ Sistema capture configurato: {self.output_dir}")
        print(f"✅ Modulo integrazione: {integration_file}")
        print()
        print("🎯 PROSSIMI PASSI:")
        print("1. Aggiungi app_integration.py a main.py")
        print("2. Testa con verifiche reali generate")
        print("3. Monitora output directory")
        print("4. Analizza risultati validazione")
        
        return {
            "real_outputs": len(real_outputs),
            "capture_system": capture_system,
            "integration_file": str(integration_file),
            "output_directory": str(self.output_dir)
        }

if __name__ == "__main__":
    system = RealVerificationTestSystem()
    results = system.run_complete_system()
