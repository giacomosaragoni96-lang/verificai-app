#!/usr/bin/env python3
"""
Pagina PromptFoo semplice e chiara - solo le opzioni utili
"""

import streamlit as st
import subprocess
import json
import os
from datetime import datetime
import sys

def render_promptfoo_simple():
    """Pagina semplice per test PromptFoo"""
    
    st.markdown("""
    <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                padding: 2rem; border-radius: 10px; margin-bottom: 2rem;'>
        <h1 style='color: white; margin: 0;'>🧪 Test Suite VerificAI</h1>
        <p style='color: white; margin: 0.5rem 0 0 0;'>Test rapidi e chiari per le verifiche scolastiche</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Opzioni principali
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🎯 Test Rapido", type="primary", use_container_width=True):
            run_test_rapido()
    
    with col2:
        if st.button("📊 Test Completo", type="primary", use_container_width=True):
            run_test_completo()
    
    with col3:
        if st.button("🚀 Test Reali", type="primary", use_container_width=True):
            run_test_reali()
    
    st.markdown("---")
    
    # Spiegazione chiara
    st.markdown("## 📋 Cosa Puoi Fare")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        ### 🎯 Test Rapido
        **Test veloce su Matematica**
        - Verifica punteggi esatti
        - Controlla numero esercizi  
        - Output immediato
        """)
    
    with col2:
        st.markdown("""
        ### 📊 Test Completo
        **Test su tutte le materie**
        - Matematica, Italiano, Fisica
        - Metriche complete
        - Analisi dettagliata
        """)
    
    with col3:
        st.markdown("""
        ### 🚀 Test Reali
        **Verifiche come dall'app**
        - 3 scenari completi
        - Output LaTeX reale
        - Salvataggio automatico
        """)
    
    # Risultati recenti
    st.markdown("---")
    st.markdown("## 📂 Risultati Recenti")
    
    show_recent_results()

def run_test_rapido():
    """Esegue test rapido"""
    with st.spinner("🔄 Esecuzione test rapido..."):
        try:
            result = subprocess.run([
                sys.executable, "promptfoo/test_fix.py"
            ], capture_output=True, text=True, cwd=".")
            
            st.markdown("### 🎯 Risultati Test Rapido")
            
            if result.returncode == 0:
                st.success("✅ Test completato!")
                st.code(result.stdout, language="text")
            else:
                st.error("❌ Test fallito")
                st.code(result.stderr, language="text")
                
        except Exception as e:
            st.error(f"❌ Errore: {e}")

def run_test_completo():
    """Esegue test completo senza dipendenze problematiche"""
    with st.spinner("🔄 Esecuzione test completo..."):
        try:
            # Eseguiamo un test completo diretto senza usare comprehensive_test_suite.py
            from prompts import prompt_corpo_verifica
            from config import CALIBRAZIONE_SCUOLA
            import google.generativeai as genai
            import json
            from datetime import datetime
            
            st.markdown("### 📊 Test Completo - Tutte le Materie")
            
            # Scenari completi per tutte le materie
            scenarios = [
                {
                    "name": "Matematica_Equazioni",
                    "materia": "Matematica",
                    "livello": "Istituto Tecnico",
                    "argomento": "Equazioni di secondo grado",
                    "num_esercizi": 4,
                    "punti_totali": 80
                },
                {
                    "name": "Italiano_Analisi",
                    "materia": "Italiano",
                    "livello": "Liceo Scientifico", 
                    "argomento": "Analisi testo poetico",
                    "num_esercizi": 4,
                    "punti_totali": 100
                },
                {
                    "name": "Fisica_Meccanica",
                    "materia": "Fisica",
                    "livello": "Liceo Scientifico",
                    "argomento": "Leggi di Newton",
                    "num_esercizi": 3,
                    "punti_totali": 100
                }
            ]
            
            results = []
            passed = 0
            
            for scenario in scenarios:
                try:
                    with st.spinner(f"🔄 Test {scenario['name']}..."):
                        # Genera prompt
                        calibrazione = CALIBRAZIONE_SCUOLA.get(scenario['livello'], "")
                        
                        prompt_params = {
                            "materia": scenario['materia'],
                            "argomento": scenario['argomento'],
                            "calibrazione": calibrazione,
                            "durata": "60 minuti",
                            "num_esercizi": scenario['num_esercizi'],
                            "punti_totali": scenario['punti_totali'],
                            "mostra_punteggi": True,
                            "con_griglia": True,
                            "note_generali": "",
                            "istruzioni_esercizi": "",
                            "e_mat": scenario['materia'] in ["Matematica", "Fisica"],
                            "titolo_header": "",
                            "preambolo_fisso": "",
                            "mathpix_context": None
                        }
                        
                        prompt = prompt_corpo_verifica(**prompt_params)
                        
                        # Chiama API
                        model = genai.GenerativeModel('gemini-2.5-flash-lite')
                        response = model.generate_content(prompt)
                        output = response.text
                        
                        # Valutazione
                        import re
                        subsections = len(re.findall(r'\\subsection\*', output))
                        points = re.findall(r'\((\d+)\s*pt\)', output)
                        total_points = sum(int(p) for p in points)
                        
                        # Check pass/fail
                        esercizi_ok = subsections == scenario['num_esercizi']
                        punti_ok = total_points == scenario['punti_totali']
                        test_passed = esercizi_ok and punti_ok
                        
                        if test_passed:
                            passed += 1
                        
                        results.append({
                            "name": scenario['name'],
                            "materia": scenario['materia'],
                            "passed": test_passed,
                            "esercizi": f"{subsections}/{scenario['num_esercizi']}",
                            "punti": f"{total_points}/{scenario['punti_totali']}"
                        })
                        
                        # Mostra risultato
                        status = "✅" if test_passed else "❌"
                        st.write(f"{status} **{scenario['name']}** - {scenario['materia']}")
                        
                        with st.expander(f"Dettagli {scenario['name']}"):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.write(f"**Esercizi:** {subsections}/{scenario['num_esercizi']} {'✅' if esercizi_ok else '❌'}")
                                st.write(f"**Punti:** {total_points}/{scenario['punti_totali']} {'✅' if punti_ok else '❌'}")
                            with col2:
                                st.write(f"**Status:** {'PASSATO' if test_passed else 'FALLITO'}")
                                st.write(f"**Materia:** {scenario['materia']}")
                            
                            # Preview output
                            st.code(output[:300] + "..." if len(output) > 300 else output, language='latex')
                
                except Exception as e:
                    st.warning(f"⚠️ Errore {scenario['name']}: {e}")
                    results.append({
                        "name": scenario['name'],
                        "materia": scenario['materia'],
                        "passed": False,
                        "error": str(e)
                    })
            
            # Mostra metriche finali
            st.markdown("### 📊 Risultati Finali")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Test Totali", len(results))
            with col2:
                st.metric("Passati", passed)
            with col3:
                success_rate = (passed / len(results)) * 100 if results else 0
                st.metric("Success Rate", f"{success_rate:.1f}%")
            
            # Tabella risultati
            st.markdown("#### 📋 Tabella Risultati")
            for result in results:
                if result.get('passed'):
                    st.success(f"✅ {result['name']} - {result['materia']} - {result.get('esercizi', 'N/A')} - {result.get('punti', 'N/A')}")
                else:
                    st.error(f"❌ {result['name']} - {result['materia']} - {result.get('error', 'Fallito')}")
            
        except Exception as e:
            st.error(f"❌ Errore test completo: {e}")

def run_test_reali():
    """Esegue test su verifiche reali"""
    with st.spinner("🔄 Generazione verifiche reali..."):
        try:
            # Genera direttamente le verifiche
            from prompts import prompt_corpo_verifica
            from config import CALIBRAZIONE_SCUOLA
            import google.generativeai as genai
            import json
            from datetime import datetime
            
            # Scenari semplificati
            scenarios = [
                {
                    "name": "Matematica_Equazioni",
                    "materia": "Matematica",
                    "livello": "Istituto Tecnico",
                    "argomento": "Equazioni di secondo grado",
                    "num_esercizi": 4,
                    "punti_totali": 80
                },
                {
                    "name": "Italiano_Testo",
                    "materia": "Italiano", 
                    "livello": "Liceo Scientifico",
                    "argomento": "Analisi testo",
                    "num_esercizi": 4,
                    "punti_totali": 100
                }
            ]
            
            os.makedirs("real_verifications", exist_ok=True)
            
            for scenario in scenarios:
                try:
                    # Genera prompt
                    calibrazione = CALIBRAZIONE_SCUOLA.get(scenario['livello'], "")
                    
                    prompt_params = {
                        "materia": scenario['materia'],
                        "argomento": scenario['argomento'],
                        "calibrazione": calibrazione,
                        "durata": "60 minuti",
                        "num_esercizi": scenario['num_esercizi'],
                        "punti_totali": scenario['punti_totali'],
                        "mostra_punteggi": True,
                        "con_griglia": True,
                        "note_generali": "",
                        "istruzioni_esercizi": "",
                        "e_mat": scenario['materia'] == "Matematica",
                        "titolo_header": "",
                        "preambolo_fisso": "",
                        "mathpix_context": None
                    }
                    
                    prompt = prompt_corpo_verifica(**prompt_params)
                    
                    # Chiama API
                    model = genai.GenerativeModel('gemini-2.5-flash-lite')
                    response = model.generate_content(prompt)
                    output = response.text
                    
                    # Salva
                    test_data = {
                        "scenario": scenario,
                        "output": output,
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    filename = f"real_verifications/{scenario['name']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(test_data, f, indent=2, ensure_ascii=False)
                    
                    st.success(f"✅ Generato: {scenario['name']}")
                    
                    # Mostra preview
                    with st.expander(f"📄 {scenario['name']}"):
                        st.code(output[:500] + "..." if len(output) > 500 else output, language='latex')
                        
                        # Valutazione rapida
                        import re
                        subsections = len(re.findall(r'\\subsection\*', output))
                        points = re.findall(r'\((\d+)\s*pt\)', output)
                        total_points = sum(int(p) for p in points)
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Esercizi", subsections)
                        with col2:
                            st.metric("Punti", total_points)
                        with col3:
                            st.metric("Target", f"{scenario['num_esercizi']}/{scenario['punti_totali']}")
                
                except Exception as e:
                    st.warning(f"⚠️ Errore {scenario['name']}: {e}")
            
            st.info("📂 Verifiche salvate in real_verifications/")
            
        except Exception as e:
            st.error(f"❌ Errore generazione: {e}")

def show_comprehensive_metrics():
    """Mostra metriche del test completo"""
    try:
        result_files = [
            "promptfoo/comprehensive_test_results.json",
            "promptfoo/enhanced_test_results.json"
        ]
        
        for file_path in result_files:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    results = json.load(f)
                
                if 'summary' in results:
                    summary = results['summary']
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Totali", summary.get('total', 0))
                    with col2:
                        st.metric("Passati", summary.get('passed', 0))
                    with col3:
                        st.metric("Falliti", summary.get('failed', 0))
                break
    
    except Exception:
        pass

def show_recent_results():
    """Mostra risultati recenti"""
    
    # Cerca risultati recenti
    result_dirs = ["real_verifications", "test_results"]
    
    for dir_name in result_dirs:
        if os.path.exists(dir_name):
            files = [f for f in os.listdir(dir_name) if f.endswith('.json')]
            if files:
                st.markdown(f"### 📁 {dir_name.title()}")
                
                # Mostra ultimi 3 file
                for file in sorted(files)[-3:]:
                    try:
                        with open(f"{dir_name}/{file}", 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        # Estrai info base
                        if 'scenario' in data:
                            scenario = data['scenario']
                            name = scenario.get('name', file.replace('.json', ''))
                            materia = scenario.get('materia', 'N/A')
                            st.write(f"📝 **{name}** - {materia}")
                        else:
                            st.write(f"📝 {file.replace('.json', '')}")
                    
                    except Exception:
                        st.write(f"📝 {file.replace('.json', '')}")
                
                st.markdown("---")

# Funzione principale
def render_promptfoo_page():
    """Renderizza pagina PromptFoo semplice"""
    render_promptfoo_simple()
