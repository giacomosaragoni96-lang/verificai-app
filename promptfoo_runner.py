#!/usr/bin/env python3
"""
Pagina semplice per lanciare test PromptFoo con output chiari
"""

import streamlit as st
import subprocess
import json
import os
from datetime import datetime
import sys

def render_promptfoo_runner():
    """Pagina dedicata per test PromptFoo"""
    
    st.markdown("""
    <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                padding: 2rem; border-radius: 10px; margin-bottom: 2rem;'>
        <h1 style='color: white; margin: 0;'>🧪 Test Suite PromptFoo</h1>
        <p style='color: white; margin: 0.5rem 0 0 0;'>Lancia e analizza test PromptFoo con output chiari</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar con opzioni
    with st.sidebar:
        st.markdown("### ⚙️ Opzioni Test")
        
        # Selezione test
        test_type = st.selectbox(
            "Tipo di Test:",
            ["🎯 Test Rapido", "📊 Test Completo", "🔍 Analisi Singolo", "🚀 Test Reali"]
        )
        
        # Filtro materia (se disponibile)
        if test_type in ["🎯 Test Rapido", "📊 Test Completo"]:
            materia_filter = st.selectbox(
                "Filtra per Materia:",
                ["Tutte", "Matematica", "Italiano", "Fisica", "Storia", "Inglese", "Chimica"]
            )
        
        # Opzioni output
        show_details = st.checkbox("Mostra Dettagli Completi", value=True)
        save_results = st.checkbox("Salva Risultati", value=True)
        
        st.markdown("---")
        st.markdown("### 📁 File Disponibili")
        
        # Mostra file PromptFoo disponibili
        promptfoo_dir = "promptfoo"
        if os.path.exists(promptfoo_dir):
            files = [f for f in os.listdir(promptfoo_dir) if f.endswith(('.py', '.yaml', '.json'))]
            if files:
                st.write("**File trovati:**")
                for file in sorted(files):
                    st.write(f"📄 {file}")
            else:
                st.write("Nessun file PromptFoo trovato")
        else:
            st.write("Directory promptfoo non trovata")
    
    # Area principale
    if test_type == "🎯 Test Rapido":
        render_test_rapido(show_details, save_results)
    elif test_type == "📊 Test Completo":
        render_test_completo(show_details, save_results, materia_filter)
    elif test_type == "🔍 Analisi Singolo":
        render_analisi_singolo(show_details, save_results)
    elif test_type == "🚀 Test Reali":
        render_test_reali(show_details, save_results)

def render_test_rapido(show_details, save_results):
    """Test rapido su Matematica"""
    st.markdown("## 🎯 Test Rapido - Matematica")
    
    if st.button("🚀 Lancia Test Rapido", type="primary"):
        with st.spinner("🔄 Esecuzione test rapido in corso..."):
            try:
                # Lancia test_fix.py
                result = subprocess.run([
                    sys.executable, "promptfoo/test_fix.py"
                ], capture_output=True, text=True, cwd=".")
                
                # Mostra output
                st.markdown("### 📄 Output Test")
                st.code(result.stdout, language="text")
                
                if result.stderr:
                    st.markdown("### ⚠️ Errori/Warnings")
                    st.code(result.stderr, language="text")
                
                # Status
                if result.returncode == 0:
                    st.success("✅ Test completato con successo!")
                else:
                    st.error(f"❌ Test fallito (exit code: {result.returncode})")
                
                # Salva risultati
                if save_results:
                    save_test_result("test_rapido", result.stdout, result.stderr, result.returncode)
                
            except Exception as e:
                st.error(f"❌ Errore esecuzione: {e}")

def render_test_completo(show_details, save_results, materia_filter):
    """Test completo comprehensive"""
    st.markdown("## 📊 Test Completo - Comprehensive Suite")
    
    if st.button("🚀 Lancia Test Completo", type="primary"):
        with st.spinner("🔄 Esecuzione test completo in corso..."):
            try:
                # Lancia comprehensive_test_suite.py
                result = subprocess.run([
                    sys.executable, "promptfoo/comprehensive_test_suite.py"
                ], capture_output=True, text=True, cwd=".")
                
                # Mostra output
                st.markdown("### 📄 Output Test Completo")
                st.code(result.stdout, language="text")
                
                if result.stderr:
                    st.markdown("### ⚠️ Errori/Warnings")
                    st.code(result.stderr, language="text")
                
                # Status
                if result.returncode == 0:
                    st.success("✅ Test completo terminato!")
                    
                    # Analizza risultati se disponibili
                    analyze_comprehensive_results(result.stdout, show_details)
                else:
                    st.error(f"❌ Test fallito (exit code: {result.returncode})")
                
                # Salva risultati
                if save_results:
                    save_test_result("test_completo", result.stdout, result.stderr, result.returncode)
                
            except Exception as e:
                st.error(f"❌ Errore esecuzione: {e}")

def render_analisi_singolo(show_details, save_results):
    """Analisi test singolo"""
    st.markdown("## 🔍 Analisi Test Singolo")
    
    # Seleziona file di analisi
    analysis_files = [
        ("test_analysis.py", "Analisi completa test"),
        ("show_passing_test.py", "Mostra test passanti"),
        ("test_real_verification.py", "Test su verifica reale"),
    ]
    
    selected_file = st.selectbox(
        "Seleziona Analisi:",
        [f"{name} - {desc}" for name, desc in analysis_files]
    )
    
    file_name = selected_file.split(" - ")[0]
    
    if st.button("🔍 Esegui Analisi", type="primary"):
        with st.spinner(f"🔄 Esecuzione {file_name} in corso..."):
            try:
                result = subprocess.run([
                    sys.executable, f"promptfoo/{file_name}"
                ], capture_output=True, text=True, cwd=".")
                
                # Mostra output
                st.markdown("### 📄 Output Analisi")
                st.code(result.stdout, language="text")
                
                if result.stderr:
                    st.markdown("### ⚠️ Errori/Warnings")
                    st.code(result.stderr, language="text")
                
                # Status
                if result.returncode == 0:
                    st.success("✅ Analisi completata!")
                else:
                    st.error(f"❌ Analisi fallita (exit code: {result.returncode})")
                
                # Salva risultati
                if save_results:
                    save_test_result(f"analisi_{file_name}", result.stdout, result.stderr, result.returncode)
                
            except Exception as e:
                st.error(f"❌ Errore esecuzione: {e}")

def render_test_reali(show_details, save_results):
    """Test su verifiche reali"""
    st.markdown("## 🚀 Test Verifiche Reali")
    
    if st.button("🚀 Genera e Testa Verifiche Reali", type="primary"):
        with st.spinner("🔄 Generazione verifiche reali in corso..."):
            try:
                # Genera direttamente le verifiche reali senza usare il sistema esterno
                from prompts import prompt_corpo_verifica
                from config import CALIBRAZIONE_SCUOLA
                import google.generativeai as genai
                import json
                from datetime import datetime
                import os
                
                # Scenari di test reali
                real_scenarios = [
                    {
                        "name": "Matematica_Tecnico_Equazioni",
                        "materia": "Matematica",
                        "livello": "Istituto Tecnico Tecnologico/Industriale",
                        "argomento": "Equazioni di secondo grado",
                        "durata": "50 minuti",
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
                        "durata": "90 minuti",
                        "num_esercizi": 4,
                        "punti_totali": 100,
                        "mostra_punteggi": True,
                        "con_griglia": True,
                        "e_mat": False
                    },
                    {
                        "name": "Fisica_Liceo_Meccanica",
                        "materia": "Fisica",
                        "livello": "Liceo Scientifico",
                        "argomento": "Leggi di Newton",
                        "durata": "60 minuti",
                        "num_esercizi": 3,
                        "punti_totali": 100,
                        "mostra_punteggi": True,
                        "con_griglia": True,
                        "e_mat": True
                    }
                ]
                
                # Crea directory se non esiste
                os.makedirs("real_verifications", exist_ok=True)
                
                generated_count = 0
                
                for scenario in real_scenarios:
                    try:
                        # Calibrazione
                        calibrazione = CALIBRAZIONE_SCUOLA.get(scenario['livello'], "")
                        
                        # Parametri prompt
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
                        
                        # Genera prompt
                        prompt = prompt_corpo_verifica(**prompt_params)
                        
                        # Chiama API
                        model = genai.GenerativeModel('gemini-2.5-flash-lite')
                        response = model.generate_content(prompt)
                        output = response.text
                        
                        # Salva test
                        test_data = {
                            "scenario": scenario,
                            "prompt_used": prompt,
                            "output": output,
                            "timestamp": datetime.now().isoformat(),
                            "tokens": {
                                "prompt": len(prompt),
                                "completion": len(output),
                                "total": len(prompt) + len(output)
                            }
                        }
                        
                        filename = f"real_verifications/{scenario['name']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                        with open(filename, 'w', encoding='utf-8') as f:
                            json.dump(test_data, f, indent=2, ensure_ascii=False)
                        
                        generated_count += 1
                        
                    except Exception as e:
                        st.warning(f"⚠️ Errore generazione {scenario['name']}: {e}")
                        continue
                
                st.success(f"✅ Generati {generated_count} verifiche reali su {len(real_scenarios)}!")
                st.info("📂 Verifiche salvate in real_verifications/")
                
                # Mostra verifiche generate
                show_real_verifications()
                
                # Salva risultati
                if save_results:
                    save_test_result("test_reali", f"Generate {generated_count} verifiche", "", 0)
                
            except Exception as e:
                st.error(f"❌ Errore generazione verifiche reali: {e}")
                st.info("💡 Verifica che le API siano configurate correttamente")

def analyze_comprehensive_results(output, show_details):
    """Analizza risultati del test completo"""
    try:
        # Cerca file risultati
        result_files = [
            "promptfoo/comprehensive_test_results.json",
            "promptfoo/enhanced_test_results.json"
        ]
        
        for file_path in result_files:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    results = json.load(f)
                
                st.markdown("### 📊 Analisi Risultati")
                
                # Metriche generali
                if 'summary' in results:
                    summary = results['summary']
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Test Totali", summary.get('total', 0))
                    with col2:
                        st.metric("Passati", summary.get('passed', 0))
                    with col3:
                        st.metric("Falliti", summary.get('failed', 0))
                
                # Dettagli test
                if show_details and 'detailed_results' in results:
                    st.markdown("#### 📋 Dettagli Test")
                    for test in results['detailed_results'][:10]:  # Primi 10
                        status = "✅" if test.get('status') == 'passed' else "❌"
                        st.write(f"{status} **{test.get('test_name', 'Unknown')}** - {test.get('category', 'N/A')}")
                
                break
    
    except Exception as e:
        st.warning(f"⚠️ Impossibile analizzare risultati: {e}")

def show_real_verifications():
    """Mostra verifiche reali generate"""
    try:
        real_dir = "real_verifications"
        if os.path.exists(real_dir):
            files = [f for f in os.listdir(real_dir) if f.endswith('.json')]
            
            if files:
                st.markdown("### 📄 Verifiche Reali Generate")
                
                for file in sorted(files)[-3:]:  # Ultime 3
                    with open(f"{real_dir}/{file}", 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    scenario = data.get('scenario', {})
                    st.markdown(f"#### 📝 {scenario.get('name', file)}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Materia:** {scenario.get('materia', 'N/A')}")
                        st.write(f"**Livello:** {scenario.get('livello', 'N/A')}")
                    with col2:
                        st.write(f"**Esercizi:** {scenario.get('num_esercizi', 'N/A')}")
                        st.write(f"**Punti:** {scenario.get('punti_totali', 'N/A')}")
                    
                    # Preview output
                    output = data.get('output', '')
                    if output:
                        st.code(output[:300] + "..." if len(output) > 300 else output, language='latex')
                    
                    st.markdown("---")
    
    except Exception as e:
        st.warning(f"⚠️ Impossibile mostrare verifiche reali: {e}")

def save_test_result(test_name, stdout, stderr, returncode):
    """Salva risultati del test"""
    try:
        os.makedirs("test_results", exist_ok=True)
        
        result_data = {
            "test_name": test_name,
            "timestamp": datetime.now().isoformat(),
            "returncode": returncode,
            "stdout": stdout,
            "stderr": stderr,
            "success": returncode == 0
        }
        
        filename = f"test_results/{test_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, indent=2, ensure_ascii=False)
        
        st.info(f"💾 Risultati salvati in {filename}")
    
    except Exception as e:
        st.warning(f"⚠️ Impossibile salvare risultati: {e}")

# Funzione principale per integrare in main.py
def render_promptfoo_page():
    """Renderizza pagina PromptFoo - da chiamare in main.py"""
    render_promptfoo_runner()
