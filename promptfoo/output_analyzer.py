#!/usr/bin/env python3
"""
Analisi Dettagliata Output Falliti - VerificAI Enhanced Test Suite
"""

import os
import sys
import re
from datetime import datetime

# Setup
PROJECT_ROOT = os.environ.get("VERIFICAI_ROOT", "C:\\Users\\gobli\\Desktop\\verificai")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

sys.path.insert(0, os.path.dirname(__file__))

def analyze_failed_outputs():
    """Analisi dettagliata degli output dei test falliti"""
    
    print("🔍 ANALISI DETTAGLIATA OUTPUT FALLITI")
    print("=" * 70)
    print("📋 Focus: Perché Gemini non rispetta i valori esatti?")
    print(f"📅 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    from providers.verificai_provider import call_api
    
    # Test case critici da analizzare
    critical_tests = [
        {
            "name": "[Corpo] Matematica Derivate — Struttura Completa",
            "vars": {
                "prompt_type": "corpo", "materia": "Matematica", "argomento": "Derivate",
                "livello": "Liceo Scientifico", "durata": "60 minuti", "num_esercizi": 5,
                "punti_totali": 100, "mostra_punteggi": True, "con_griglia": True, "e_mat": True
            },
            "expected": {"num_esercizi": 5, "punti_totali": 100}
        },
        {
            "name": "[Corpo] Italiano Medie — Leggibilità Ottimizzata",
            "vars": {
                "prompt_type": "corpo", "materia": "Italiano", "argomento": "Analisi del periodo",
                "livello": "Scuola Secondaria I grado (Medie)", "durata": "45 minuti",
                "num_esercizi": 4, "punti_totali": 80, "mostra_punteggi": True
            },
            "expected": {"num_esercizi": 4, "punti_totali": 80}
        },
        {
            "name": "[Corpo] Fisica — Formattazione Scientifica",
            "vars": {
                "prompt_type": "corpo", "materia": "Fisica", "argomento": "Leggi di Newton",
                "livello": "Liceo Scientifico", "durata": "50 minuti", "num_esercizi": 3,
                "punti_totali": 0, "mostra_punteggi": False, "e_mat": True
            },
            "expected": {"num_esercizi": 3, "punti_totali": 0}
        }
    ]
    
    def extract_metrics(output):
        """Estrae metriche dall'output"""
        subsections = len(re.findall(r'\\subsection\*', output))
        points = re.findall(r'\((\d+)\s*pt\)', output)
        total_points = sum(int(p) for p in points)
        has_points = len(points) > 0
        
        return {
            "subsections": subsections,
            "points_list": points,
            "total_points": total_points,
            "has_points": has_points,
            "output_length": len(output)
        }
    
    def analyze_structure(output):
        """Analizza la struttura dell'output"""
        lines = output.split('\n')
        sections = []
        current_section = None
        
        for line in lines:
            if r'\subsection*' in line:
                current_section = {"title": line.strip(), "content": []}
                sections.append(current_section)
            elif current_section and line.strip():
                current_section["content"].append(line.strip())
        
        return sections
    
    for i, test in enumerate(critical_tests, 1):
        print(f"🧪 ANALISI TEST {i}: {test['name']}")
        print(f"   📊 Atteso: {test['expected']}")
        print()
        
        try:
            # Ottieni output da Gemini
            options = {"config": {"model_id": "gemini-2.5-flash-lite", "temperature": 0.7}}
            context = {"vars": test["vars"]}
            
            result = call_api("test", options, context)
            
            if "error" in result:
                print(f"   ❌ Errore API: {result['error']}")
                continue
            
            output = result.get("output", "")
            usage = result.get("tokenUsage", {})
            
            # Analisi metriche
            metrics = extract_metrics(output)
            sections = analyze_structure(output)
            
            print(f"   📤 Output: {metrics['output_length']} chars, {usage.get('total', 0)} tokens")
            print(f"   📊 Metriche estratte:")
            print(f"      - Subsections (esercizi): {metrics['subsections']}")
            print(f"      - Punti trovati: {metrics['points_list']}")
            print(f"      - Totale punti: {metrics['total_points']}")
            print(f"      - Ha punti: {metrics['has_points']}")
            print()
            
            # Confronto con attesi
            expected = test["expected"]
            exercises_match = metrics["subsections"] == expected["num_esercizi"]
            points_match = metrics["total_points"] == expected["punti_totali"]
            
            print(f"   🔍 Confronto:")
            print(f"      - Esercizi: {metrics['subsections']} vs {expected['num_esercizi']} {'✅' if exercises_match else '❌'}")
            print(f"      - Punti: {metrics['total_points']} vs {expected['punti_totali']} {'✅' if points_match else '❌'}")
            print()
            
            # Analisi dettagliata sezioni
            print(f"   📋 Struttura sezioni ({len(sections)} trovate):")
            for j, section in enumerate(sections[:3], 1):  # Prime 3 sezioni
                print(f"      {j}. {section['title']}")
                if section['content']:
                    first_line = section['content'][0] if section['content'] else "Nessun contenuto"
                    # Estrai punti da questa sezione
                    section_points = re.findall(r'\((\d+)\s*pt\)', first_line)
                    if section_points:
                        print(f"         Punti: {section_points}")
                    print(f"         Preview: {first_line[:100]}...")
                print()
            
            # Problemi identificati
            problems = []
            if not exercises_match:
                if metrics["subsections"] < expected["num_esercizi"]:
                    problems.append(f"Meno esercizi del richiesto ({metrics['subsections']} < {expected['num_esercizi']})")
                else:
                    problems.append(f"Pù esercizi del richiesto ({metrics['subsections']} > {expected['num_esercizi']})")
            
            if not points_match:
                if expected["punti_totali"] == 0 and metrics["has_points"]:
                    problems.append(f"Punti presenti quando non dovrebbero esserci ({metrics['total_points']} pt)")
                elif expected["punti_totali"] > 0 and metrics["total_points"] == 0:
                    problems.append(f"Nessun punto quando dovrebbero esserci (atteso {expected['punti_totali']} pt)")
                elif metrics["total_points"] != expected["punti_totali"]:
                    problems.append(f"Totale punti sbagliato ({metrics['total_points']} ≠ {expected['punti_totali']})")
            
            if problems:
                print(f"   ⚠️ Problemi identificati:")
                for problem in problems:
                    print(f"      - {problem}")
            else:
                print(f"   ✅ Nessun problema identificato")
            
            print()
            print("─" * 70)
            print()
            
        except Exception as e:
            print(f"   ❌ Errore analisi: {e}")
            print()
    
    # Analisi finale e raccomandazioni
    print("🎯 RACCOMANDAZIONI PER MIGLIORARE I PROMPT")
    print("=" * 70)
    
    recommendations = [
        {
            "problem": "Numero esercizi non rispettato",
            "cause": "Gemini non conta esattamente i \\subsection*",
            "solution": "Aggiungere nel prompt: 'Genera ESATTAMENTE {num_esercizi} esercizi, ognuno con \\subsection*'"
        },
        {
            "problem": "Totale punti non esatto",
            "cause": "Gemini distribuisce punti in modo approssimativo",
            "solution": "Aggiungere nel prompt: 'La SOMMA TOTALE dei punti deve essere ESATTAMENTE {punti_totali}'"
        },
        {
            "problem": "Punti presenti quando non dovrebbero",
            "cause": "Gemini ignora mostra_punteggi: false",
            "solution": "Aggiungere nel prompt: 'NON includere punteggi (X pt) se mostra_punteggi è false'"
        },
        {
            "problem": "Distribuzione punti non bilanciata",
            "cause": "Gemini non calcola correttamente la distribuzione",
            "solution": "Aggiungere nel prompt: 'Distribuisci i punti in modo che la somma sia esatta'"
        }
    ]
    
    for i, rec in enumerate(recommendations, 1):
        print(f"📝 {i}. {rec['problem']}")
        print(f"   🔍 Causa: {rec['cause']}")
        print(f"   💡 Soluzione: {rec['solution']}")
        print()
    
    print("🎯 AZIONI IMMEDIATE:")
    print("   1. Modificare prompts.py con istruzioni più precise")
    print("   2. Aggiungere controlli espliciti nel prompt")
    print("   3. Testare con le nuove istruzioni")
    print("   4. Verificare miglioramento nei test successivi")

if __name__ == "__main__":
    analyze_failed_outputs()
