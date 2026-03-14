#!/usr/bin/env python3
"""
Pannello Admin VerificAI - Test Suite Management
Da integrare in main.py come pagina admin riservata
"""

import streamlit as st
import json
import os
import sys
from datetime import datetime
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Setup
PROJECT_ROOT = os.environ.get("VERIFICAI_ROOT", "C:\\Users\\gobli\\Desktop\\verificai")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

sys.path.insert(0, os.path.dirname(__file__))

class AdminTestPanel:
    def __init__(self):
        self.test_dir = Path("real_verifications")
        self.results_dir = Path("test_results")
        self.test_dir.mkdir(exist_ok=True)
        self.results_dir.mkdir(exist_ok=True)
        
    def render_admin_panel(self):
        """Renderizza il pannello admin completo"""
        
        st.set_page_config(
            page_title="Admin - Test Suite VerificAI",
            page_icon="🔧",
            layout="wide"
        )
        
        # Header admin
        st.markdown("""
        <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 2rem; border-radius: 10px; margin-bottom: 2rem;'>
            <h1 style='color: white; margin: 0;'>🔧 Pannello Admin - Test Suite VerificAI</h1>
            <p style='color: white; margin: 0.5rem 0 0 0;'>Gestione completa test verifiche e qualità output</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Sidebar navigazione
        with st.sidebar:
            st.markdown("### 📋 Navigazione")
            page = st.selectbox(
                "Seleziona sezione:",
                ["🎯 Dashboard", "🧪 Nuovo Test", "📊 Storico Test", "🔍 Analisi Output", "⚙️ Configurazione"]
            )
            
            st.markdown("---")
            st.markdown("### 📈 Statistiche Rapide")
            self.render_sidebar_stats()
        
        # Renderizza pagina selezionata
        if page == "🎯 Dashboard":
            self.render_dashboard()
        elif page == "🧪 Nuovo Test":
            self.render_new_test()
        elif page == "📊 Storico Test":
            self.render_test_history()
        elif page == "🔍 Analisi Output":
            self.render_output_analysis()
        elif page == "⚙️ Configurazione":
            self.render_configuration()
    
    def render_sidebar_stats(self):
        """Statistiche rapide nella sidebar"""
        try:
            # Conta test esistenti
            test_files = list(self.test_dir.glob("*.json"))
            results_files = list(self.results_dir.glob("*.json"))
            
            st.metric("Test Generati", len(test_files))
            st.metric("Risultati Salvati", len(results_files))
            
            # Calcola success rate medio
            if results_files:
                scores = []
                for file in results_files:
                    try:
                        with open(file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            if 'score' in data:
                                scores.append(data['score'])
                    except:
                        continue
                
                if scores:
                    avg_score = sum(scores) / len(scores)
                    st.metric("Score Medio", f"{avg_score:.1f}%")
            
        except Exception as e:
            st.error(f"Errore statistiche: {e}")
    
    def render_dashboard(self):
        """Dashboard principale con overview"""
        st.markdown("## 🎯 Dashboard Test Suite")
        
        # Metriche principali
        col1, col2, col3, col4 = st.columns(4)
        
        try:
            test_files = list(self.test_dir.glob("*.json"))
            results_files = list(self.results_dir.glob("*.json"))
            
            with col1:
                st.metric("📝 Test Totali", len(test_files))
            
            with col2:
                st.metric("📊 Risultati", len(results_files))
            
            with col3:
                # Ultimo test
                if test_files:
                    latest_test = max(test_files, key=os.path.getctime)
                    latest_time = datetime.fromtimestamp(os.path.getctime(latest_test))
                    st.metric("⏰ Ultimo Test", latest_time.strftime("%H:%M"))
                else:
                    st.metric("⏰ Ultimo Test", "Nessuno")
            
            with col4:
                # Success rate
                if results_files:
                    scores = []
                    for file in results_files:
                        try:
                            with open(file, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                                if 'score' in data:
                                    scores.append(data['score'])
                        except:
                            continue
                    
                    if scores:
                        avg_score = sum(scores) / len(scores)
                        st.metric("📈 Success Rate", f"{avg_score:.1f}%")
                else:
                    st.metric("📈 Success Rate", "N/A")
        
        except Exception as e:
            st.error(f"Errore dashboard: {e}")
        
        # Grafici
        st.markdown("### 📊 Andamento Test")
        
        # Grafico andamento score
        if results_files:
            try:
                scores_data = []
                for file in sorted(results_files):
                    with open(file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if 'score' in data and 'timestamp' in data:
                            scores_data.append({
                                'timestamp': data['timestamp'],
                                'score': data['score'],
                                'scenario': data.get('scenario', 'Unknown')
                            })
                
                if scores_data:
                    df_scores = pd.DataFrame(scores_data)
                    df_scores['timestamp'] = pd.to_datetime(df_scores['timestamp'])
                    
                    fig = px.line(
                        df_scores, 
                        x='timestamp', 
                        y='score',
                        color='scenario',
                        title="Andamento Score Test nel Tempo",
                        markers=True
                    )
                    st.plotly_chart(fig, use_container_width=True)
            
            except Exception as e:
                st.error(f"Errore grafico: {e}")
        
        # Test recenti
        st.markdown("### 📋 Test Recenti")
        
        if test_files:
            recent_tests = sorted(test_files, key=os.path.getctime, reverse=True)[:5]
            
            for test_file in recent_tests:
                try:
                    with open(test_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    scenario = data.get('scenario', {})
                    tokens = data.get('tokens', {})
                    
                    with st.expander(f"📝 {scenario.get('name', 'Unknown')} - {test_file.name}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write(f"**Materia:** {scenario.get('materia', 'N/A')}")
                            st.write(f"**Livello:** {scenario.get('livello', 'N/A')}")
                            st.write(f"**Esercizi:** {scenario.get('num_esercizi', 'N/A')}")
                            st.write(f"**Punti:** {scenario.get('punti_totali', 'N/A')}")
                        
                        with col2:
                            st.write(f"**Tokens Totali:** {tokens.get('total', 'N/A')}")
                            st.write(f"**Data:** {data.get('timestamp', 'N/A')}")
                        
                        # Preview output
                        output = data.get('output', '')
                        if output:
                            st.markdown("**📄 Preview Output:**")
                            st.code(output[:500] + "..." if len(output) > 500 else output, language='latex')
                        
                        # Pulsanti azione
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            if st.button(f"🔍 Analizza", key=f"analyze_{test_file.name}"):
                                self.analyze_single_test(test_file)
                        with col2:
                            if st.button(f"📊 Valuta", key=f"evaluate_{test_file.name}"):
                                self.evaluate_single_test(test_file)
                        with col3:
                            if st.button(f"🗑️ Elimina", key=f"delete_{test_file.name}"):
                                os.remove(test_file)
                                st.rerun()
                
                except Exception as e:
                    st.error(f"Errore caricamento test {test_file.name}: {e}")
        else:
            st.info("Nessun test trovato. Vai alla sezione '🧪 Nuovo Test' per generarne.")
    
    def render_new_test(self):
        """Pagina per generare nuovi test"""
        st.markdown("## 🧪 Genera Nuovo Test")
        
        # Form configurazione test
        with st.form("new_test_form"):
            st.markdown("### 📋 Configurazione Test")
            
            col1, col2 = st.columns(2)
            
            with col1:
                materia = st.selectbox(
                    "Materia",
                    ["Matematica", "Italiano", "Fisica", "Storia", "Inglese", "Chimica", "Informatica"]
                )
                
                livello = st.selectbox(
                    "Livello",
                    ["Scuola Primaria", "Scuola Media", "Liceo Scientifico", 
                     "Istituto Tecnico Tecnologico/Industriale", "Istituto Professionale"]
                )
                
                argomento = st.text_input("Argomento", "Equazioni di secondo grado")
            
            with col2:
                num_esercizi = st.number_input("Numero Esercizi", min_value=1, max_value=10, value=4)
                punti_totali = st.number_input("Punti Totali", min_value=10, max_value=200, value=80, step=10)
                durata = st.text_input("Durata", "50 minuti")
            
            col1, col2 = st.columns(2)
            with col1:
                mostra_punteggi = st.checkbox("Mostra Punteggi", value=True)
                con_griglia = st.checkbox("Con Griglia", value=True)
            with col2:
                e_mat = st.checkbox("Formule Matematiche", value=True)
                test_name = st.text_input("Nome Test (opzionale)", "")
            
            submitted = st.form_submit_button("🚀 Genera Test", type="primary")
            
            if submitted:
                self.generate_new_test(
                    materia, livello, argomento, num_esercizi, 
                    punti_totali, durata, mostra_punteggi, con_griglia, e_mat, test_name
                )
    
    def generate_new_test(self, materia, livello, argomento, num_esercizi, 
                         punti_totali, durata, mostra_punteggi, con_griglia, e_mat, test_name):
        """Genera un nuovo test"""
        
        with st.spinner("🔄 Generazione test in corso..."):
            try:
                from providers.verificai_provider import call_api
                from prompts import prompt_corpo_verifica
                
                # Scenario test
                scenario = {
                    "name": test_name or f"{materia}_{livello}_{argomento.replace(' ', '_')}",
                    "materia": materia,
                    "livello": livello,
                    "argomento": argomento,
                    "durata": durata,
                    "num_esercizi": num_esercizi,
                    "punti_totali": punti_totali,
                    "mostra_punteggi": mostra_punteggi,
                    "con_griglia": con_griglia,
                    "e_mat": e_mat
                }
                
                # Genera prompt
                from config import CALIBRAZIONE_SCUOLA
                calibrazione = CALIBRAZIONE_SCUOLA.get(livello, "")
                
                prompt_params = {
                    "materia": materia,
                    "argomento": argomento,
                    "calibrazione": calibrazione,
                    "durata": durata,
                    "num_esercizi": num_esercizi,
                    "punti_totali": punti_totali,
                    "mostra_punteggi": mostra_punteggi,
                    "con_griglia": con_griglia,
                    "note_generali": "",
                    "istruzioni_esercizi": "",
                    "e_mat": e_mat,
                    "titolo_header": "",
                    "preambolo_fisso": "",
                    "mathpix_context": None
                }
                
                prompt = prompt_corpo_verifica(**prompt_params)
                
                # Chiama API
                options = {"config": {"model_id": "gemini-2.5-flash-lite", "temperature": 0.7}}
                context = {"vars": scenario}
                
                result = call_api("test", options, context)
                output = result.get("output", "")
                
                # Salva test
                test_data = {
                    "scenario": scenario,
                    "prompt_used": prompt,
                    "output": output,
                    "timestamp": datetime.now().isoformat(),
                    "tokens": result.get("tokenUsage", {})
                }
                
                filename = f"{scenario['name']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                filepath = self.test_dir / filename
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(test_data, f, indent=2, ensure_ascii=False)
                
                st.success(f"✅ Test generato e salvato: {filename}")
                
                # Mostra preview
                st.markdown("### 📄 Preview Test Generato")
                st.code(output, language='latex')
                
                # Valutazione automatica
                st.markdown("### 🔍 Valutazione Automatica")
                evaluation = self.evaluate_test_output(output, scenario)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Assertions Passate", f"{evaluation['passed']}/{evaluation['total']}")
                with col2:
                    st.metric("Score", f"{evaluation['score']:.1f}%")
                
                # Dettagli assertions
                for assertion, result in evaluation['assertions'].items():
                    status = "✅" if result['passed'] else "❌"
                    st.write(f"{status} **{assertion}**: {result.get('details', '')}")
                
                # Salva valutazione
                evaluation['scenario'] = scenario
                evaluation['timestamp'] = datetime.now().isoformat()
                evaluation['test_file'] = filename
                
                eval_filename = f"evaluation_{scenario['name']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                eval_filepath = self.results_dir / eval_filename
                
                with open(eval_filepath, 'w', encoding='utf-8') as f:
                    json.dump(evaluation, f, indent=2, ensure_ascii=False)
                
            except Exception as e:
                st.error(f"❌ Errore generazione test: {e}")
    
    def evaluate_test_output(self, output, scenario):
        """Valuta output del test"""
        import re
        
        evaluation = {
            "assertions": {},
            "passed": 0,
            "total": 0,
            "score": 0
        }
        
        # 1. Numero esercizi
        subsections = len(re.findall(r'\\subsection\*', output))
        target_exercises = scenario.get('num_esercizi', 0)
        exercises_ok = subsections == target_exercises
        evaluation['assertions']['num_esercizi_esatto'] = {
            "passed": exercises_ok,
            "details": f"Trovati: {subsections}, Attesi: {target_exercises}"
        }
        evaluation['total'] += 1
        if exercises_ok: evaluation['passed'] += 1
        
        # 2. Punteggi esatti
        points = re.findall(r'\((\d+)\s*pt\)', output)
        total_points = sum(int(p) for p in points)
        target_points = scenario.get('punti_totali', 0)
        points_ok = total_points == target_points
        evaluation['assertions']['punteggi_esatti'] = {
            "passed": points_ok,
            "details": f"Punti: {points}, Totale: {total_points}, Attesi: {target_points}"
        }
        evaluation['total'] += 1
        if points_ok: evaluation['passed'] += 1
        
        # 3. Qualità matematica
        math_formulas = len(re.findall(r'\$[^$]*\$', output))
        math_ok = math_formulas >= 2 if scenario.get('e_mat') else True
        evaluation['assertions']['qualita_matematica'] = {
            "passed": math_ok,
            "details": f"Formule: {math_formulas}"
        }
        evaluation['total'] += 1
        if math_ok: evaluation['passed'] += 1
        
        # 4. Brackets bilanciati
        clean = output.replace(r'\{', '').replace(r'\}', '')
        depth = 0
        brackets_ok = True
        for char in clean:
            if char == '{': depth += 1
            elif char == '}': depth -= 1
            if depth < 0: 
                brackets_ok = False
                break
        if depth != 0: brackets_ok = False
        evaluation['assertions']['brackets_bilanciati'] = {
            "passed": brackets_ok,
            "details": "Parentesi graffe bilanciate"
        }
        evaluation['total'] += 1
        if brackets_ok: evaluation['passed'] += 1
        
        # Calcola score
        if evaluation['total'] > 0:
            evaluation['score'] = (evaluation['passed'] / evaluation['total']) * 100
        
        return evaluation
    
    def render_test_history(self):
        """Pagina storico test"""
        st.markdown("## 📊 Storico Test Completo")
        
        # Filtri
        col1, col2, col3 = st.columns(3)
        with col1:
            materia_filter = st.selectbox("Filtra per Materia", ["Tutte"] + ["Matematica", "Italiano", "Fisica", "Storia", "Inglese", "Chimica", "Informatica"])
        with col2:
            livello_filter = st.selectbox("Filtra per Livello", ["Tutti"] + ["Scuola Primaria", "Scuola Media", "Liceo Scientifico", "Istituto Tecnico Tecnologico/Industriale", "Istituto Professionale"])
        with col3:
            sort_by = st.selectbox("Ordina per", ["Data", "Score", "Materia"])
        
        # Carica risultati
        results_files = list(self.results_dir.glob("*.json"))
        
        if results_files:
            results_data = []
            for file in results_files:
                try:
                    with open(file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        results_data.append({
                            'file': file.name,
                            'timestamp': data.get('timestamp', ''),
                            'scenario': data.get('scenario', {}),
                            'score': data.get('score', 0),
                            'passed': data.get('passed', 0),
                            'total': data.get('total', 0)
                        })
                except:
                    continue
            
            # Filtri
            if materia_filter != "Tutte":
                results_data = [r for r in results_data if r['scenario'].get('materia') == materia_filter]
            if livello_filter != "Tutti":
                results_data = [r for r in results_data if r['scenario'].get('livello') == livello_filter]
            
            # Ordinamento
            if sort_by == "Data":
                results_data.sort(key=lambda x: x['timestamp'], reverse=True)
            elif sort_by == "Score":
                results_data.sort(key=lambda x: x['score'], reverse=True)
            elif sort_by == "Materia":
                results_data.sort(key=lambda x: x['scenario'].get('materia', ''))
            
            # Tabella risultati
            if results_data:
                df = pd.DataFrame(results_data)
                
                # Formatta tabella
                display_df = df[['file', 'timestamp', 'scenario', 'score', 'passed', 'total']].copy()
                display_df['Materia'] = df['scenario'].apply(lambda x: x.get('materia', 'N/A'))
                display_df['Livello'] = df['scenario'].apply(lambda x: x.get('livello', 'N/A'))
                display_df['Data'] = pd.to_datetime(df['timestamp']).dt.strftime('%d/%m/%Y %H:%M')
                display_df['Score %'] = df['score'].apply(lambda x: f"{x:.1f}%")
                display_df['Assertions'] = df.apply(lambda x: f"{x['passed']}/{x['total']}", axis=1)
                
                # Mostra tabella
                st.dataframe(
                    display_df[['Data', 'Materia', 'Livello', 'Score %', 'Assertions']],
                    use_container_width=True
                )
                
                # Grafico distribuzione score
                st.markdown("### 📈 Distribuzione Score")
                fig = px.histogram(
                    df, 
                    x='score', 
                    nbins=10,
                    title="Distribuzione Score Test",
                    labels={'score': 'Score %', 'count': 'Numero Test'}
                )
                st.plotly_chart(fig, use_container_width=True)
                
            else:
                st.info("Nessun risultato trovato con i filtri selezionati.")
        else:
            st.info("Nessun risultato di test trovato.")
    
    def render_output_analysis(self):
        """Analisi dettagliata output"""
        st.markdown("## 🔍 Analisi Dettagliata Output")
        
        # Seleziona test da analizzare
        test_files = list(self.test_dir.glob("*.json"))
        
        if test_files:
            selected_file = st.selectbox(
                "Seleziona Test da Analizzare",
                test_files,
                format_func=lambda x: x.name
            )
            
            if selected_file:
                try:
                    with open(selected_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    scenario = data.get('scenario', {})
                    output = data.get('output', '')
                    
                    # Info test
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Materia", scenario.get('materia', 'N/A'))
                    with col2:
                        st.metric("Livello", scenario.get('livello', 'N/A'))
                    with col3:
                        st.metric("Esercizi", scenario.get('num_esercizi', 'N/A'))
                    
                    # Output completo
                    st.markdown("### 📄 Output Completo")
                    st.code(output, language='latex')
                    
                    # Statistiche output
                    st.markdown("### 📊 Statistiche Output")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Caratteri", len(output))
                    with col2:
                        st.metric("Righe", len(output.split('\n')))
                    with col3:
                        st.metric("Formule", output.count('$') // 2)
                    with col4:
                        st.metric("Subsections", output.count('\\subsection*'))
                    
                    # Valutazione dettagliata
                    st.markdown("### 🔍 Valutazione Dettagliata")
                    evaluation = self.evaluate_test_output(output, scenario)
                    
                    for assertion, result in evaluation['assertions'].items():
                        with st.expander(f"{'✅' if result['passed'] else '❌'} {assertion}"):
                            st.write(result['details'])
                    
                    # Score finale
                    st.markdown("### 📈 Score Finale")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Assertions Passate", f"{evaluation['passed']}/{evaluation['total']}")
                    with col2:
                        st.metric("Score Totale", f"{evaluation['score']:.1f}%")
                
                except Exception as e:
                    st.error(f"Errore caricamento test: {e}")
        else:
            st.info("Nessun test trovato. Genera nuovi test dalla sezione '🧪 Nuovo Test'.")
    
    def render_configuration(self):
        """Pagina configurazione"""
        st.markdown("## ⚙️ Configurazione Sistema Test")
        
        # Configurazione assertions
        st.markdown("### 📋 Assertions Configurate")
        
        assertions_config = {
            "num_esercizi_esatto": {
                "descrizione": "Verifica numero esatto di esercizi (\\subsection*)",
                "abilitato": True,
                "peso": 25
            },
            "punteggi_esatti": {
                "descrizione": "Verifica somma esatta punteggi",
                "abilitato": True,
                "peso": 25
            },
            "qualita_matematica": {
                "descrizione": "Verifica presenza formule matematiche",
                "abilitato": True,
                "peso": 20
            },
            "brackets_bilanciati": {
                "descrizione": "Verifica parentesi graffe bilanciate",
                "abilitato": True,
                "peso": 15
            },
            "tabella_punteggi": {
                "descrizione": "Verifica presenza tabella punteggi",
                "abilitato": False,
                "peso": 10
            },
            "impaginazione_professionale": {
                "descrizione": "Verifica layout professionale",
                "abilitato": False,
                "peso": 5
            }
        }
        
        for name, config in assertions_config.items():
            with st.expander(f"{'✅' if config['abilitato'] else '❌'} {name}"):
                st.write(config['descrizione'])
                col1, col2 = st.columns(2)
                with col1:
                    st.checkbox("Abilitato", value=config['abilitato'], key=f"enabled_{name}")
                with col2:
                    st.number_input("Peso", value=config['peso'], key=f"weight_{name}")
        
        # Pulizia dati
        st.markdown("### 🗑️ Pulizia Dati")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Elimina Tutti i Test", type="secondary"):
                if st.session_state.get('confirm_delete_tests', False):
                    # Elimina tutti i test
                    for file in self.test_dir.glob("*.json"):
                        os.remove(file)
                    st.success("✅ Tutti i test eliminati")
                    st.session_state['confirm_delete_tests'] = False
                    st.rerun()
                else:
                    st.session_state['confirm_delete_tests'] = True
                    st.warning("⚠️ Conferma eliminazione cliccando di nuovo")
        
        with col2:
            if st.button("🗑️ Elimina Tutti i Risultati", type="secondary"):
                if st.session_state.get('confirm_delete_results', False):
                    # Elimina tutti i risultati
                    for file in self.results_dir.glob("*.json"):
                        os.remove(file)
                    st.success("✅ Tutti i risultati eliminati")
                    st.session_state['confirm_delete_results'] = False
                    st.rerun()
                else:
                    st.session_state['confirm_delete_results'] = True
                    st.warning("⚠️ Conferma eliminazione cliccando di nuovo")
        
        # Export/Import
        st.markdown("### 📤 Export/Import Dati")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📤 Export Dati Test"):
                # Crea zip con tutti i dati
                import zipfile
                zip_path = "test_data_export.zip"
                with zipfile.ZipFile(zip_path, 'w') as zipf:
                    for file in self.test_dir.glob("*.json"):
                        zipf.write(file, file.name)
                    for file in self.results_dir.glob("*.json"):
                        zipf.write(file, file.name)
                
                st.success(f"✅ Dati esportati in {zip_path}")
        
        with col2:
            uploaded_file = st.file_uploader("📥 Import Dati Test", type=['zip'])
            if uploaded_file:
                # Importa dati da zip
                with zipfile.ZipFile(uploaded_file) as zipf:
                    zipf.extractall(".")
                st.success("✅ Dati importati con successo")
    
    def analyze_single_test(self, test_file):
        """Analizza singolo test"""
        # Implementazione analisi dettagliata
        pass
    
    def evaluate_single_test(self, test_file):
        """Valuta singolo test"""
        # Implementazione valutazione
        pass

# Funzione principale da chiamare in main.py
def render_admin_page():
    """Renderizza pagina admin - da aggiungere a main.py"""
    
    # Verifica permessi admin (semplice per ora)
    if not st.session_state.get('is_admin', False):
        st.error("⛔ Accesso negato. Privilegi admin richiesti.")
        return
    
    # Renderizza pannello admin
    admin_panel = AdminTestPanel()
    admin_panel.render_admin_panel()

# Esempio di integrazione in main.py:
"""
if user_is_admin and st.sidebar.button("🔧 Admin Panel"):
    render_admin_page()
"""
