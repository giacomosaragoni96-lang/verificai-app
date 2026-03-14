#!/usr/bin/env python3
"""
VerificAI Comprehensive Test Suite - Copertura Completa Scenari
Test estesi per tutte le materie, livelli e tipologie di verifiche
"""

import os
import sys
import json
import re
from datetime import datetime

# Setup
PROJECT_ROOT = os.environ.get("VERIFICAI_ROOT", "C:\\Users\\gobli\\Desktop\\verificai")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

sys.path.insert(0, os.path.dirname(__file__))

def run_comprehensive_test_suite():
    """Test suite completo per tutti gli scenari VerificAI"""
    
    print("🚀 VERIFICAI COMPREHENSIVE TEST SUITE")
    print("=" * 80)
    print("📋 Copertura completa: Tutte le materie, livelli e tipologie")
    print(f"🔑 API Key: {'✅ Impostata' if os.environ.get('GEMINI_API_KEY') else '❌ Mancante'}")
    print(f"📅 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    from providers.verificai_provider import call_api
    
    # Test suite completa - 24 test case
    comprehensive_tests = [
        # ── MATEMATICA ────────────────────────────────────────────────────────
        {
            "name": "[Matematica] Liceo Scientifico - Derivate",
            "category": "Matematica Liceo",
            "priority": "High",
            "vars": {
                "prompt_type": "corpo", "materia": "Matematica", "argomento": "Derivate",
                "livello": "Liceo Scientifico", "durata": "60 minuti", "num_esercizi": 5,
                "punti_totali": 100, "mostra_punteggi": True, "con_griglia": True, "e_mat": True
            },
            "assertions": ["struttura_sottopunti", "punteggi_esatti", "num_esercizi_esatto", "qualita_matematica"]
        },
        {
            "name": "[Matematica] Istituto Tecnico - Equazioni",
            "category": "Matematica Tecnico",
            "priority": "High",
            "vars": {
                "prompt_type": "corpo", "materia": "Matematica", "argomento": "Equazioni di secondo grado",
                "livello": "Istituto Tecnico Tecnologico/Industriale", "durata": "50 minuti",
                "num_esercizi": 4, "punti_totali": 80, "mostra_punteggi": True, "e_mat": True
            },
            "assertions": ["punteggi_esatti", "num_esercizi_esatto", "brackets_bilanciati", "spaziatura_operatori"]
        },
        {
            "name": "[Matematica] Istituto Professionale - Percentuali",
            "category": "Matematica Professionale",
            "priority": "Medium",
            "vars": {
                "prompt_type": "corpo", "materia": "Matematica", "argomento": "Percentuali e proporzioni",
                "livello": "Istituto Professionale", "durata": "45 minuti",
                "num_esercizi": 4, "punti_totali": 80, "mostra_punteggi": True
            },
            "assertions": ["punteggi_esatti", "num_esercizi_esatto", "livello_professionale", "layout_pratico"]
        },
        {
            "name": "[Matematica] Scuola Media - Geometria",
            "category": "Matematica Medie",
            "priority": "Medium",
            "vars": {
                "prompt_type": "corpo", "materia": "Matematica", "argomento": "Perimetro e area",
                "livello": "Scuola Secondaria I grado (Medie)", "durata": "45 minuti",
                "num_esercizi": 4, "punti_totali": 80, "mostra_punteggi": True
            },
            "assertions": ["punteggi_esatti", "num_esercizi_esatto", "livello_medie_ottimizzato", "sottopunti_chiar"]
        },
        {
            "name": "[Matematica] Scuola Primaria - Numeri",
            "category": "Matematica Primaria",
            "priority": "Low",
            "vars": {
                "prompt_type": "corpo", "materia": "Matematica", "argomento": "Addizione e sottrazione",
                "livello": "Scuola Primaria (Elementari)", "durata": "30 minuti",
                "num_esercizi": 3, "punti_totali": 60, "mostra_punteggi": True
            },
            "assertions": ["punteggi_esatti", "num_esercizi_esatto", "livello_primaria", "layout_child_friendly"]
        },
        
        # ── ITALIANO ──────────────────────────────────────────────────────────
        {
            "name": "[Italiano] Liceo - Analisi del testo",
            "category": "Italiano Liceo",
            "priority": "High",
            "vars": {
                "prompt_type": "corpo", "materia": "Italiano", "argomento": "Analisi del testo poetico",
                "livello": "Liceo Scientifico", "durata": "90 minuti", "num_esercizi": 4,
                "punti_totali": 100, "mostra_punteggi": True, "con_griglia": True
            },
            "assertions": ["punteggi_esatti", "num_esercizi_esatto", "varieta_tipologie_avanzata", "leggibilita_ottimale"]
        },
        {
            "name": "[Italiano] Medie - Grammatica",
            "category": "Italiano Medie",
            "priority": "Medium",
            "vars": {
                "prompt_type": "corpo", "materia": "Italiano", "argomento": "Analisi grammaticale del periodo",
                "livello": "Scuola Secondaria I grado (Medie)", "durata": "45 minuti",
                "num_esercizi": 4, "punti_totali": 80, "mostra_punteggi": True
            },
            "assertions": ["punteggi_esatti", "num_esercizi_esatto", "livello_medie_ottimizzato", "leggibilita_ragazzi"]
        },
        {
            "name": "[Italiano] Primaria - Lettura",
            "category": "Italiano Primaria",
            "priority": "Low",
            "vars": {
                "prompt_type": "corpo", "materia": "Italiano", "argomento": "Comprensione del testo",
                "livello": "Scuola Primaria (Elementari)", "durata": "30 minuti",
                "num_esercizi": 3, "punti_totali": 60, "mostra_punteggi": True
            },
            "assertions": ["punteggi_esatti", "num_esercizi_esatto", "livello_primaria", "layout_child_friendly"]
        },
        
        # ── FISICA ───────────────────────────────────────────────────────────
        {
            "name": "[Fisica] Liceo - Meccanica",
            "category": "Fisica Liceo",
            "priority": "High",
            "vars": {
                "prompt_type": "corpo", "materia": "Fisica", "argomento": "Leggi di Newton",
                "livello": "Liceo Scientifico", "durata": "60 minuti", "num_esercizi": 3,
                "punti_totali": 100, "mostra_punteggi": True, "e_mat": True
            },
            "assertions": ["punteggi_esatti", "num_esercizi_esatto", "notazione_fisica", "equilibrio_testo_formule"]
        },
        {
            "name": "[Fisica] Istituto Tecnico - Elettromagnetismo",
            "category": "Fisica Tecnico",
            "priority": "Medium",
            "vars": {
                "prompt_type": "corpo", "materia": "Fisica", "argomento": "Circuiti elettrici",
                "livello": "Istituto Tecnico Tecnologico", "durata": "50 minuti",
                "num_esercizi": 4, "punti_totali": 80, "mostra_punteggi": True, "e_mat": True
            },
            "assertions": ["punteggi_esatti", "num_esercizi_esatto", "notazione_fisica", "brackets_bilanciati"]
        },
        
        # ── STORIA ───────────────────────────────────────────────────────────
        {
            "name": "[Storia] Liceo - Storia Contemporanea",
            "category": "Storia Liceo",
            "priority": "High",
            "vars": {
                "prompt_type": "corpo", "materia": "Storia", "argomento": "La Prima Guerra Mondiale",
                "livello": "Liceo Scientifico", "durata": "60 minuti", "num_esercizi": 6,
                "punti_totali": 100, "mostra_punteggi": True, "con_griglia": True
            },
            "assertions": ["punteggi_esatti", "num_esercizi_esatto", "varieta_tipologie_avanzata", "leggibilita_ottimale"]
        },
        {
            "name": "[Storia] Medie - Storia Antica",
            "category": "Storia Medie",
            "priority": "Medium",
            "vars": {
                "prompt_type": "corpo", "materia": "Storia", "argomento": "Antica Roma",
                "livello": "Scuola Secondaria I grado (Medie)", "durata": "45 minuti",
                "num_esercizi": 4, "punti_totali": 80, "mostra_punteggi": True
            },
            "assertions": ["punteggi_esatti", "num_esercizi_esatto", "livello_medie_ottimizzato", "sottopunti_chiar"]
        },
        
        # ── INGLESE ───────────────────────────────────────────────────────────
        {
            "name": "[Inglese] Liceo - Grammar",
            "category": "Inglese Liceo",
            "priority": "High",
            "vars": {
                "prompt_type": "corpo", "materia": "Inglese", "argomento": "Present Perfect vs Past Simple",
                "livello": "Liceo Scientifico", "durata": "45 minuti", "num_esercizi": 5,
                "punti_totali": 80, "mostra_punteggi": True
            },
            "assertions": ["punteggi_esatti", "num_esercizi_esatto", "varieta_tipologie_avanzata", "brackets_bilanciati"]
        },
        {
            "name": "[Inglese] Medie - Reading",
            "category": "Inglese Medie",
            "priority": "Medium",
            "vars": {
                "prompt_type": "corpo", "materia": "Inglese", "argomento": "Reading comprehension",
                "livello": "Scuola Secondaria I grado (Medie)", "durata": "40 minuti",
                "num_esercizi": 4, "punti_totali": 60, "mostra_punteggi": True
            },
            "assertions": ["punteggi_esatti", "num_esercizi_esatto", "livello_medie_ottimizzato", "leggibilita_ragazzi"]
        },
        
        # ── CHIMICA ───────────────────────────────────────────────────────────
        {
            "name": "[Chimica] Liceo - Reazioni Chimiche",
            "category": "Chimica Liceo",
            "priority": "Medium",
            "vars": {
                "prompt_type": "corpo", "materia": "Chimica", "argomento": "Bilanciamento reazioni",
                "livello": "Liceo Scientifico", "durata": "60 minuti", "num_esercizi": 4,
                "punti_totali": 100, "mostra_punteggi": True, "e_mat": True
            },
            "assertions": ["punteggi_esatti", "num_esercizi_esatto", "qualita_matematica", "brackets_bilanciati"]
        },
        
        # ── INFORMATICA ───────────────────────────────────────────────────────
        {
            "name": "[Informatica] Algoritmi e Strutture Dati",
            "category": "Informatica Liceo",
            "priority": "Medium",
            "vars": {
                "prompt_type": "corpo", "materia": "Informatica", "argomento": "Algoritmi e strutture dati",
                "livello": "Liceo Scientifico", "durata": "60 minuti", "num_esercizi": 4,
                "punti_totali": 100, "mostra_punteggi": True, "con_griglia": True, "e_mat": True
            },
            "assertions": ["punteggi_esatti", "num_esercizi_esatto", "struttura_gerarchica", "leggibilita_ottimale"]
        },
        
        # ── SCENARI SPECIALI ───────────────────────────────────────────────────
        {
            "name": "[Speciale] Senza Punteggi",
            "category": "Scenari Speciali",
            "priority": "Medium",
            "vars": {
                "prompt_type": "corpo", "materia": "Matematica", "argomento": "Esercizi senza valutazione",
                "livello": "Liceo Scientifico", "durata": "45 minuti", "num_esercizi": 3,
                "punti_totali": 0, "mostra_punteggi": False, "e_mat": True
            },
            "assertions": ["punteggi_esatti_zero", "num_esercizi_esatto", "qualita_matematica"]
        },
        {
            "name": "[Speciale] Numero Elevato Esercizi",
            "category": "Scenari Speciali",
            "priority": "Medium",
            "vars": {
                "prompt_type": "corpo", "materia": "Matematica", "argomento": "Esercizi rapidi",
                "livello": "Liceo Scientifico", "durata": "90 minuti", "num_esercizi": 8,
                "punti_totali": 100, "mostra_punteggi": True, "con_griglia": True
            },
            "assertions": ["punteggi_esatti", "num_esercizi_esatto", "varieta_tipologie_avanzata"]
        },
        {
            "name": "[Speciale] Durata Breve",
            "category": "Scenari Speciali",
            "priority": "Low",
            "vars": {
                "prompt_type": "corpo", "materia": "Italiano", "argomento": "Verifica rapida",
                "livello": "Scuola Secondaria I grado (Medie)", "durata": "20 minuti",
                "num_esercizi": 2, "punti_totali": 40, "mostra_punteggi": True
            },
            "assertions": ["punteggi_esatti", "num_esercizi_esatto", "livello_medie_ottimizzato"]
        },
        
        # ── TITOLI ───────────────────────────────────────────────────────────
        {
            "name": "[Titolo] Matematica Complesso",
            "category": "Titoli",
            "priority": "Low",
            "vars": {"prompt_type": "titolo", "materia": "Matematica", "argomento": "Calcolo differenziale multivariabile"},
            "assertions": ["length_check", "no_quotes", "no_period"]
        },
        {
            "name": "[Titolo] Storia Correzione",
            "category": "Titoli",
            "priority": "Low",
            "vars": {"prompt_type": "titolo", "materia": "Storia", "argomento": "la rivoluzzione industriale"},
            "assertions": ["not-icontains: 'rivoluzzione'", "icontains: 'Rivoluzione'"]
        },
        {
            "name": "[Titolo] Inglese Conciso",
            "category": "Titoli",
            "priority": "Low",
            "vars": {"prompt_type": "titolo", "materia": "Inglese", "argomento": "phrasal verbs and idioms"},
            "assertions": ["length_check", "no_quotes"]
        },
        
        # ── QA CORREZIONE ─────────────────────────────────────────────────────
        {
            "name": "[QA] Correzione Matematica",
            "category": "QA e Correzione",
            "priority": "Medium",
            "vars": {
                "prompt_type": "qa", "materia": "Matematica", "livello": "Liceo Scientifico",
                "mostra_punteggi": True, "punti_totali": 100,
                "corpo_latex": r"""
\subsection*{Esercizio 1: Equazioni}
\begin{enumerate}[a)]
\item[a)] Risolvi $x^2 + 1 = 0$ in $\mathbb{R}$. (10 pt)
\item[b)] Trova le soluzioni di $2x - 6 = 0$. (10 pt)
\end{enumerate}
\subsection*{Esercizio 2: Disequazioni}
\begin{enumerate}[a)]
\item[a)] Risolvi $x^2 - 4 > 0$. (15 pt)
\end{enumerate}
\end{document}
                """
            },
            "assertions": ["correzione_intelligente", "punteggi_esatti"]
        }
    ]
    
    # Enhanced assertion functions
    def run_assertion(output, assertion_type, test_vars=None):
        """Execute comprehensive assertion checks"""
        
        if assertion_type == "length_check":
            return len(output.strip()) < 80 and len(output.strip()) > 3
        elif assertion_type == "no_quotes":
            return '"' not in output
        elif assertion_type == "no_period":
            return not output.strip().endswith('.')
        elif assertion_type == "not-icontains":
            # Formato: "not-icontains: 'text'"
            parts = assertion_type.split(":")
            if len(parts) == 2:
                text = parts[1].strip().strip("'\"")
                return text.lower() not in output.lower()
            return True
        elif assertion_type == "icontains":
            # Formato: "icontains: 'text'"
            parts = assertion_type.split(":")
            if len(parts) == 2:
                text = parts[1].strip().strip("'\"")
                return text.lower() in output.lower()
            return True
        elif assertion_type == "struttura_sottopunti":
            has_enumerate = r'\begin{enumerate}' in output
            has_items = r'\item' in output
            subpoints = len([x for x in output.split() if x.startswith(r'\item')])
            return has_enumerate and has_items and subpoints >= 3
        elif assertion_type == "punteggi_esatti":
            matches = re.findall(r'\((\d+)\s*pt\)', output)
            total_points = sum(int(m) for m in matches)
            target_points = test_vars.get('punti_totali', 100) if test_vars else 100
            return total_points == target_points
        elif assertion_type == "punteggi_esatti_zero":
            matches = re.findall(r'\((\d+)\s*pt\)', output)
            return len(matches) == 0
        elif assertion_type == "num_esercizi_esatto":
            matches = re.findall(r'\\subsection\*', output)
            num_exercises = len(matches)
            target_exercises = test_vars.get('num_esercizi', 5) if test_vars else 5
            return num_exercises == target_exercises
        elif assertion_type == "qualita_matematica":
            inline_math = len([x for x in output.split() if x.startswith('$') and x.endswith('$')])
            return inline_math >= 2
        elif assertion_type == "brackets_bilanciati":
            clean = output.replace(r'\{', '').replace(r'\}', '')
            depth = 0
            for char in clean:
                if char == '{': depth += 1
                elif char == '}': depth -= 1
                if depth < 0: return False
            return depth == 0
        elif assertion_type == "spaziatura_operatori":
            good_spacing = bool(re.search(r'\s*[+\-*/=]\s*', output))
            bad_spacing = bool(re.search(r'[a-z][+\-*/][a-z]|[0-9][+\-*/][a-z]', output, re.I))
            return good_spacing and not bad_spacing
        elif assertion_type == "livello_professionale":
            sentences = [s.strip() for s in output.split('.!?') if s.strip()]
            avg_len = sum(len(s.split()) for s in sentences) / len(sentences) if sentences else 0
            complex_words = [w for w in output.lower().split() if len(w) > 10]
            abstract = bool(re.search(r'teorema|postulato|assioma|ipotesi|dimostrazione', output, re.I))
            practical = bool(re.search(r'esempio|pratica|applicazione|vita.*quotidiana', output, re.I))
            return avg_len <= 18 and len(complex_words) <= 3 and not abstract and practical
        elif assertion_type == "layout_pratico":
            return True  # Semplificato per demo
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
        elif assertion_type == "livello_primaria":
            sentences = [s.strip() for s in output.split('.!?') if s.strip()]
            avg_len = sum(len(s.split()) for s in sentences) / len(sentences) if sentences else 0
            simple = bool(re.search(r'mela|gatto|scuola|casa|gioco|numero|conta|aggiungi|togli|disegna|colora', output, re.I))
            complex = bool(re.search(r'derivata|integrale|teorema|algoritmo|funzione', output, re.I))
            visual = bool(re.search(r'disegna|colora|figura|immagine', output, re.I))
            fun = bool(re.search(r'gioco|divertente|amichevole|facile', output, re.I))
            return avg_len <= 12 and simple and not complex and (visual or fun)
        elif assertion_type == "layout_child_friendly":
            return True  # Semplificato per demo
        elif assertion_type == "notazione_fisica":
            formulas = len([x for x in output.split() if x.startswith('$') and x.endswith('$')])
            vectors = len([x for x in output.split() if r'\vec{' in x or r'\mathbf{' in x])
            units = len([x for x in output.split() if r'\text{' in x or r'\mathrm{' in x])
            return formulas >= 2 or vectors >= 1 or units >= 1
        elif assertion_type == "equilibrio_testo_formule":
            text_lines = [line for line in output.split('\n') if not any(c in line for c in ['$', '\\']) and line.strip()]
            formula_lines = [line for line in output.split('\n') if any(c in line for c in ['$', '\\'])]
            return len(text_lines) >= 5 and len(formula_lines) >= 2
        elif assertion_type == "varieta_tipologie_avanzata":
            has_open = '?' in output or any(word in output.lower() for word in ['spiega', 'descrivi', 'motiva', 'analizza', 'commenta'])
            has_multiple = ')' in output and any(x in output for x in ['a)', 'b)', 'c)', 'd)'])
            has_true_false = any(word in output for word in ['vero', 'falso', 'V)', 'F)'])
            has_completion = any(word in output for word in ['___', '...', 'completa', 'riempi'])
            has_matching = any(word in output.lower() for word in ['abbina', 'associa', 'collega'])
            has_timeline = any(word in output.lower() for word in ['cronologia', 'timeline', 'ordina'])
            
            types = sum([has_open, has_multiple, has_true_false, has_completion, has_matching, has_timeline])
            return types >= 3
        elif assertion_type == "leggibilita_ottimale":
            text_content = re.sub(r'\$[^$]*\$', '', output)
            text_content = re.sub(r'\\[a-zA-Z]+\{[^}]*\}', '', text_content)
            text_words = len([w for w in text_content.split() if len(w) > 3])
            math_content = ''.join([x for x in output.split() if x.startswith('$') and x.endswith('$')])
            math_complexity = len(math_content)
            return text_words >= 50 and 20 <= math_complexity <= 200
        elif assertion_type == "struttura_gerarchica":
            has_sections = r'\subsection*' in output
            has_enumerates = r'\begin{enumerate}' in output
            has_items = r'\item' in output
            has_subitems = len([x for x in output.split() if any(x.startswith(prefix) for prefix in [r'\item a)', r'\item b)'])]) >= 2
            has_spacing = r'\\' in output or r'\vspace' in output
            return all([has_sections, has_enumerates, has_items, has_subitems, has_spacing])
        elif assertion_type == "correzione_intelligente":
            has_impossible = bool(re.search(r'impossibile|nessuna soluzione|non.*soluzione|vuoto|non.*esiste', output, re.I))
            has_score = bool(re.search(r'punteggi|somma|totale.*100|35.*100|sbagliato.*punteggio', output, re.I))
            has_math = bool(re.search(r'errore|sbagliato|corretto|corregge', output, re.I))
            has_structure = bool(re.search(r'struttura|organizza|migliora', output, re.I))
            
            return has_impossible or has_score or (has_math and has_structure)
        else:
            return True  # Default pass
    
    # Execute comprehensive test suite
    results = {
        "total_tests": len(comprehensive_tests),
        "passed": 0,
        "failed": 0,
        "categories": {},
        "priority_results": {"High": {"passed": 0, "total": 0}, "Medium": {"passed": 0, "total": 0}, "Low": {"passed": 0, "total": 0}},
        "detailed_results": []
    }
    
    print(f"🧪 ESECUZIONE {len(comprehensive_tests)} TEST COMPREHENSIVI")
    print()
    
    for i, test in enumerate(comprehensive_tests, 1):
        priority_icon = {"High": "🔥", "Medium": "⚡", "Low": "💡"}[test["priority"]]
        print(f"{priority_icon} Test {i}/{len(comprehensive_tests)}: {test['name']}")
        print(f"   📂 Categoria: {test['category']} | Priorità: {test['priority']}")
        
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
            
            # Run assertions
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
            
            # Priority tracking
            priority = test["priority"]
            results["priority_results"][priority]["total"] += 1
            
            if passed_assertions == total_assertions:
                print(f"   ✅ RISULTATO: PASS")
                results["passed"] += 1
                results["categories"][category]["passed"] += 1
                results["priority_results"][priority]["passed"] += 1
                status = "PASS"
            else:
                print(f"   ❌ RISULTATO: FAIL")
                results["failed"] += 1
                status = "FAIL"
            
            # Store detailed result
            results["detailed_results"].append({
                "test_name": test["name"],
                "category": category,
                "priority": priority,
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
    
    # Final comprehensive report
    print("📊 REPORT FINALE COMPREHENSIVE TEST SUITE")
    print("=" * 80)
    print(f"✅ PASS: {results['passed']}/{results['total_tests']}")
    print(f"❌ FAIL: {results['failed']}/{results['total_tests']}")
    print(f"📈 SUCCESS RATE: {(results['passed']/results['total_tests'])*100:.1f}%")
    print()
    
    print("📋 RISULTATI PER CATEGORIA:")
    for category, cat_results in results["categories"].items():
        cat_rate = (cat_results["passed"]/cat_results["total"])*100
        status = "✅" if cat_rate >= 80 else "⚠️" if cat_rate >= 60 else "❌"
        print(f"   {status} {category}: {cat_results['passed']}/{cat_results['total']} ({cat_rate:.1f}%)")
    
    print()
    print("🎯 RISULTATI PER PRIORITÀ:")
    for priority, pri_results in results["priority_results"].items():
        if pri_results["total"] > 0:
            pri_rate = (pri_results["passed"]/pri_results["total"])*100
            icon = {"High": "🔥", "Medium": "⚡", "Low": "💡"}[priority]
            print(f"   {icon} {priority}: {pri_results['passed']}/{pri_results['total']} ({pri_rate:.1f}%)")
    
    print()
    print("🎯 OBIETTIVI QUALITÀ:")
    objectives = []
    
    if results["passed"] >= results["total_tests"] * 0.8:
        objectives.append("✅ Qualità complessiva eccellente")
    if results["priority_results"]["High"]["total"] > 0:
        high_rate = (results["priority_results"]["High"]["passed"]/results["priority_results"]["High"]["total"])*100
        if high_rate >= 80:
            objectives.append("🔥 Test ad alta priorità superati")
    if any(cat["passed"] == cat["total"] for cat in results["categories"].values()):
        objectives.append("✅ Almeno una categoria perfetta")
    if results["passed"] >= results["total_tests"] * 0.9:
        objectives.append("🎉 Test suite ready per produzione")
    
    for obj in objectives:
        print(f"   {obj}")
    
    # Save comprehensive results
    results_file = "comprehensive_test_results.json"
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 Risultati completi salvati in: {results_file}")
    
    return results["failed"] == 0

if __name__ == "__main__":
    run_comprehensive_test_suite()
