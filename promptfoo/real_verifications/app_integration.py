"""
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
    subsections = len(re.findall(r'\\subsection\*', output))
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
    points = re.findall(r'\((\d+)\s*pt\)', output)
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
    table_punteggi = bool(re.search(r'\\begin\{tabular\}.*punti.*\\end\{tabular\}', output, re.I))
    validation_results["assertions"]["tabella_punteggi"] = {
        "passed": table_punteggi,
        "found": table_punteggi
    }
    total_assertions += 1
    if table_punteggi: assertions_passed += 1
    
    # 4. Impaginazione professionale
    impaginazione_elements = [
        r'\\begin\{center\}',
        r'\\textbf\{.*\\}',
        r'\\vspace\{',
        r'\\geometry\{'
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
        r'\\subsection\*',
        r'\\begin\{enumerate\}',
        r'\\item',
        r'\\begin\{center\}'
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
