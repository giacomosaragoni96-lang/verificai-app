#!/usr/bin/env python3
"""
Enhanced VerificAI Test Driver - Content + Layout + Readability
"""

import os
import sys
import json
from datetime import datetime

# Setup
PROJECT_ROOT = os.environ.get("VERIFICAI_ROOT", "C:\\Users\\gobli\\Desktop\\verificai")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

sys.path.insert(0, os.path.dirname(__file__))

def run_enhanced_test_suite():
    """Test suite completa con valutazione impaginazione e leggibilità"""
    
    print("🚀 VERIFICAI ENHANCED TEST SUITE v2.0")
    print("=" * 70)
    print("📋 Focus: Contenuto + Impaginazione + Leggibilità + Formattazione")
    print(f"🔑 API Key: {'✅ Impostata' if os.environ.get('GEMINI_API_KEY') else '❌ Mancante'}")
    print(f"📅 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    from providers.verificai_provider import call_api
    
    # Enhanced test cases con focus su impaginazione
    enhanced_tests = [
        {
            "name": "[Titolo] Matematica derivate",
            "vars": {"prompt_type": "titolo", "materia": "Matematica", "argomento": "le derivate"},
            "category": "Titoli",
            "assertions": ["length_check", "no_quotes", "no_period"]
        },
        {
            "name": "[Corpo] Matematica Derivate — Struttura Completa",
            "vars": {
                "prompt_type": "corpo", "materia": "Matematica", "argomento": "Derivate",
                "livello": "Liceo Scientifico", "durata": "60 minuti", "num_esercizi": 5,
                "punti_totali": 100, "mostra_punteggi": True, "con_griglia": True, "e_mat": True
            },
            "category": "Corpo + Impaginazione",
            "assertions": ["struttura_sottopunti", "leggibilita_paragrafi", "qualita_matematica", "spaziatura_appropriata", "punteggi_esatti", "num_esercizi_esatto"]
        },
        {
            "name": "[Corpo] Italiano Medie — Leggibilità Ottimizzata",
            "vars": {
                "prompt_type": "corpo", "materia": "Italiano", "argomento": "Analisi del periodo",
                "livello": "Scuola Secondaria I grado (Medie)", "durata": "45 minuti",
                "num_esercizi": 4, "punti_totali": 80, "mostra_punteggi": True
            },
            "category": "Corpo + Leggibilità",
            "assertions": ["livello_medie_ottimizzato", "sottopunti_chiar", "leggibilita_ragazzi", "punteggi_esatti", "num_esercizi_esatto"]
        },
        {
            "name": "[Corpo] Fisica — Formattazione Scientifica",
            "vars": {
                "prompt_type": "corpo", "materia": "Fisica", "argomento": "Leggi di Newton",
                "livello": "Liceo Scientifico", "durata": "50 minuti", "num_esercizi": 3,
                "punti_totali": 0, "mostra_punteggi": False, "e_mat": True
            },
            "category": "Corpo + Formattazione",
            "assertions": ["notazione_fisica", "equilibrio_testo_formule", "punteggi_esatti_zero", "num_esercizi_esatto"]
        },
        {
            "name": "[Regola] Anti-spoiler grafici avanzato",
            "vars": {
                "prompt_type": "corpo", "materia": "Matematica",
                "argomento": "Studio di funzione con rappresentazione grafica",
                "livello": "Liceo Scientifico", "num_esercizi": 3
            },
            "category": "Regole Avanzate",
            "assertions": ["anti_spoiler_grafici", "spazio_disegno"]
        },
        {
            "name": "[Regola] Qualità tipografica LaTeX",
            "vars": {
                "prompt_type": "corpo", "materia": "Matematica", "argomento": "Equazioni e sistemi",
                "livello": "Istituto Tecnico Tecnologico/Industriale", "num_esercizi": 4
            },
            "category": "Regole Avanzate",
            "assertions": ["brackets_bilanciati", "enumerate_bilanciati", "spaziatura_operatori"]
        },
        {
            "name": "[Regola] Varietà tipologie avanzata",
            "vars": {
                "prompt_type": "corpo", "materia": "Storia", "argomento": "La Prima Guerra Mondiale",
                "livello": "Liceo Scientifico", "num_esercizi": 6
            },
            "category": "Regole Avanzate",
            "assertions": ["varietà_tipologie_avanzata"]
        },
        {
            "name": "[Format] Impaginazione professionale completa",
            "vars": {
                "prompt_type": "corpo", "materia": "Informatica", 
                "argomento": "Algoritmi e strutture dati", "livello": "Liceo Scientifico",
                "durata": "60 minuti", "num_esercizi": 4, "punti_totali": 100,
                "mostra_punteggi": True, "con_griglia": True, "e_mat": True
            },
            "category": "Format Professionale",
            "assertions": ["struttura_gerarchica", "qualita_tipografica_professionale", "leggibilita_ottimale", "punteggi_esatti", "num_esercizi_esatto"]
        }
    ]
    
    # Enhanced assertion functions
    def run_assertion(output, assertion_type, test_vars=None):
        """Execute enhanced assertion checks"""
        
        if assertion_type == "length_check":
            return len(output.strip()) < 80 and len(output.strip()) > 3
        elif assertion_type == "no_quotes":
            return '"' not in output
        elif assertion_type == "no_period":
            return not output.strip().endswith('.')
        elif assertion_type == "struttura_sottopunti":
            has_enumerate = r'\begin{enumerate}' in output
            has_items = r'\item' in output
            subpoints = len([x for x in output.split() if x.startswith(r'\item')])
            return has_enumerate and has_items and subpoints >= 3
        elif assertion_type == "leggibilita_paragrafi":
            paragraphs = [p for p in output.split('\n\n') if p.strip()]
            long_paragraphs = [p for p in paragraphs if len(p) > 300]
            return len(paragraphs) >= 3 and len(long_paragraphs) == 0
        elif assertion_type == "qualita_matematica":
            inline_math = len([x for x in output.split() if x.startswith('$') and x.endswith('$')])
            return inline_math >= 2
        elif assertion_type == "spaziatura_appropriata":
            empty_lines = len([line for line in output.split('\n') if not line.strip()])
            return 2 <= empty_lines <= 8
        elif assertion_type == "livello_medie_ottimizzato":
            words = output.lower().split()
            complex_words = [w for w in words if len(w) > 10 or any(x in w for x in ['mente', 'zione', 'sione'])]
            sentences = [s.strip() for s in output.split('.!?') if s.strip()]
            avg_len = sum(len(s.split()) for s in sentences) / len(sentences) if sentences else 0
            return len(complex_words) <= 8 and avg_len <= 18
        elif assertion_type == "sottopunti_chiar":
            simple_subpoints = len([x for x in output.split() if any(x.startswith(prefix) for prefix in [r'\item a)', r'\item b)', r'\item 1.', r'\item 2.'])])
            return simple_subpoints >= 2 and (r'\begin{enumerate}' in output or r'\begin{itemize}' in output)
        elif assertion_type == "leggibilita_ragazzi":
            sentences = [s.strip() for s in output.split('.!?') if s.strip()]
            long_sentences = [s for s in sentences if len(s.split()) > 20]
            very_long_paragraphs = [p for p in output.split('\n\n') if len(p) > 250]
            return len(long_sentences) <= 1 and len(very_long_paragraphs) == 0
        elif assertion_type == "notazione_fisica":
            formulas = len([x for x in output.split() if x.startswith('$') and x.endswith('$')])
            vectors = len([x for x in output.split() if r'\vec{' in x or r'\mathbf{' in x])
            units = len([x for x in output.split() if r'\text{' in x or r'\mathrm{' in x])
            return formulas >= 2 or vectors >= 1 or units >= 1
        elif assertion_type == "equilibrio_testo_formule":
            text_lines = [line for line in output.split('\n') if not any(c in line for c in ['$', '\\']) and line.strip()]
            formula_lines = [line for line in output.split('\n') if any(c in line for c in ['$', '\\'])]
            return len(text_lines) >= 5 and len(formula_lines) >= 2
        elif assertion_type == "anti_spoiler_grafici":
            has_drawing = any(word in output.lower() for word in ['disegnare', 'rappresentare grafic', 'tracciare grafic'])
            has_tikz = any(word in output for word in ['tikzpicture', 'pgfplots', r'\begin{tikz'])
            return not (has_drawing and has_tikz)
        elif assertion_type == "spazio_disegno":
            has_drawing = any(word in output.lower() for word in ['disegnare', 'rappresentare grafic'])
            has_space = any(word in output for word in ['spazio', 'vspace', r'\\[', r'\\]'])
            return has_drawing and has_space
        elif assertion_type == "brackets_bilanciati":
            clean = output.replace(r'\{', '').replace(r'\}', '')
            depth = 0
            for char in clean:
                if char == '{': depth += 1
                elif char == '}': depth -= 1
                if depth < 0: return False
            return depth == 0
        elif assertion_type == "enumerate_bilanciati":
            begin_count = output.count(r'\begin{enumerate}')
            end_count = output.count(r'\end{enumerate}')
            return begin_count == end_count
        elif assertion_type == "spaziatura_operatori":
            import re
            good_spacing = bool(re.search(r'\s*[+\-*/=]\s*', output))
            bad_spacing = bool(re.search(r'[a-z][+\-*/][a-z]|[0-9][+\-*/][a-z]', output, re.I))
            return good_spacing and not bad_spacing
        elif assertion_type == "varietà_tipologie_avanzata":
            has_open = '?' in output or any(word in output.lower() for word in ['spiega', 'descrivi', 'motiva', 'analizza', 'commenta'])
            has_multiple = ')' in output and any(x in output for x in ['a)', 'b)', 'c)', 'd)'])
            has_true_false = any(word in output for word in ['vero', 'falso', 'V)', 'F)'])
            has_completion = any(word in output for word in ['___', '...', 'completa', 'riempi'])
            has_matching = any(word in output.lower() for word in ['abbina', 'associa', 'collega'])
            has_timeline = any(word in output.lower() for word in ['cronologia', 'timeline', 'ordina'])
            
            types = sum([has_open, has_multiple, has_true_false, has_completion, has_matching, has_timeline])
            return types >= 3
        elif assertion_type == "struttura_gerarchica":
            has_sections = r'\subsection*' in output
            has_enumerates = r'\begin{enumerate}' in output
            has_items = r'\item' in output
            has_subitems = len([x for x in output.split() if any(x.startswith(prefix) for prefix in [r'\item a)', r'\item b)'])]) >= 2
            has_spacing = r'\\' in output or r'\vspace' in output
            return all([has_sections, has_enumerates, has_items, has_subitems, has_spacing])
        elif assertion_type == "qualita_tipografica_professionale":
            lines = output.split('\n')
            empty_lines = len([line for line in lines if not line.strip()])
            has_proper_spacing = 2 <= empty_lines <= 6
            has_no_orphans = not any(line.strip() and len(line.strip()) < 10 for line in lines)
            has_math_mode = '$' in output
            return has_proper_spacing and has_no_orphans and has_math_mode
        elif assertion_type == "leggibilita_ottimale":
            text_content = re.sub(r'\$[^$]*\$', '', output)
            text_content = re.sub(r'\\[a-zA-Z]+\{[^}]*\}', '', text_content)
            text_words = len([w for w in text_content.split() if len(w) > 3])
            math_content = ''.join([x for x in output.split() if x.startswith('$') and x.endswith('$')])
            math_complexity = len(math_content)
            return text_words >= 50 and 20 <= math_complexity <= 200
        elif assertion_type == "punteggi_esatti":
            # Controllo esatto dei punteggi basato sulle variabili del test
            import re
            # Estrae tutti i punteggi nel formato (X pt)
            matches = re.findall(r'\((\d+)\s*pt\)', output)
            total_points = sum(int(m) for m in matches)
            # Usa il punteggio totale dalle variabili del test
            target_points = test_vars.get('punti_totali', 100) if test_vars else 100
            return total_points == target_points
        elif assertion_type == "punteggi_esatti_zero":
            # Controllo che non ci siano punteggi (per test senza punteggi)
            import re
            matches = re.findall(r'\((\d+)\s*pt\)', output)
            return len(matches) == 0
        elif assertion_type == "num_esercizi_esatto":
            # Controllo esatto del numero di esercizi basato sulle variabili del test
            import re
            # Estrae tutti i \subsection* che rappresentano esercizi
            matches = re.findall(r'\\subsection\*', output)
            num_exercises = len(matches)
            # Usa il numero di esercizi dalle variabili del test
            target_exercises = test_vars.get('num_esercizi', 5) if test_vars else 5
            return num_exercises == target_exercises
        else:
            return True  # Default pass
    
    # Execute enhanced test suite
    results = {
        "total_tests": len(enhanced_tests),
        "passed": 0,
        "failed": 0,
        "categories": {},
        "detailed_results": []
    }
    
    for i, test in enumerate(enhanced_tests, 1):
        print(f"🧪 Test {i}/{len(enhanced_tests)}: {test['name']}")
        print(f"   📂 Categoria: {test['category']}")
        
        try:
            # Call provider
            options = {"config": {"model_id": "gemini-2.5-flash-lite", "temperature": 0.7}}
            context = {"vars": test["vars"]}
            
            result = call_api("test", options, context)
            
            if "error" in result:
                print(f"   ❌ Errore API: {result['error']}")
                results["failed"] += 1
                continue
            
            output = result.get("output", "")
            usage = result.get("tokenUsage", {})
            
            print(f"   📤 Output: {len(output)} chars, {usage.get('total', 0)} tokens")
            
            # Run enhanced assertions
            passed_assertions = 0
            total_assertions = len(test["assertions"])
            
            for assertion in test["assertions"]:
                if run_assertion(output, assertion, test["vars"]):
                    passed_assertions += 1
            
            print(f"   🔍 Assertions: {passed_assertions}/{total_assertions} PASS")
            
            # Category tracking
            category = test["category"]
            if category not in results["categories"]:
                results["categories"][category] = {"passed": 0, "total": 0}
            results["categories"][category]["total"] += 1
            
            if passed_assertions == total_assertions:
                print(f"   ✅ RISULTATO: PASS")
                results["passed"] += 1
                results["categories"][category]["passed"] += 1
                status = "PASS"
            else:
                print(f"   ❌ RISULTATO: FAIL")
                results["failed"] += 1
                status = "FAIL"
            
            # Store detailed result
            results["detailed_results"].append({
                "test_name": test["name"],
                "category": category,
                "status": status,
                "assertions_passed": passed_assertions,
                "assertions_total": total_assertions,
                "tokens": usage.get("total", 0),
                "output_length": len(output)
            })
            
        except Exception as e:
            print(f"   ❌ Errore: {e}")
            results["failed"] += 1
        
        print()
    
    # Final report
    print("📊 REPORT FINALE ENHANCED TEST SUITE")
    print("=" * 70)
    print(f"✅ PASS: {results['passed']}/{results['total_tests']}")
    print(f"❌ FAIL: {results['failed']}/{results['total_tests']}")
    print(f"📈 SUCCESS RATE: {(results['passed']/results['total_tests'])*100:.1f}%")
    print()
    
    print("📋 RISULTATI PER CATEGORIA:")
    for category, cat_results in results["categories"].items():
        cat_rate = (cat_results["passed"]/cat_results["total"])*100
        print(f"   📂 {category}: {cat_results['passed']}/{cat_results['total']} ({cat_rate:.1f}%)")
    
    print()
    print("🎯 OBIETTIVI RAGGIUNTI:")
    objectives = []
    
    if results["passed"] >= results["total_tests"] * 0.8:
        objectives.append("✅ Qualità complessiva eccellente")
    if any(cat["passed"] == cat["total"] for cat in results["categories"].values()):
        objectives.append("✅ Almeno una categoria perfetta")
    if results["passed"] >= results["total_tests"] * 0.9:
        objectives.append("🎉 Test suite ready per produzione")
    
    for obj in objectives:
        print(f"   {obj}")
    
    # Save results
    results_file = "enhanced_test_results.json"
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 Risultati salvati in: {results_file}")
    
    return results["failed"] == 0

if __name__ == "__main__":
    import re
    run_enhanced_test_suite()
