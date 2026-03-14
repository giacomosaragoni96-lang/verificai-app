#!/usr/bin/env python3
"""
Test Completo: 30 verifiche random + analisi PromptFoo + PDF finale
"""

import streamlit as st
import random
from datetime import datetime
import json
import os
import subprocess
from pathlib import Path

# Setup
PROJECT_ROOT = os.environ.get("VERIFICAI_ROOT", "C:\\Users\\gobli\\Desktop\\verificai")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

sys.path.insert(0, os.path.dirname(__file__))

def render_test_completo_30():
    """Test completo con 30 verifiche random"""
    
    st.markdown("""
    <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                padding: 2rem; border-radius: 10px; margin-bottom: 2rem;'>
        <h1 style='color: white; margin: 0;'>🧪 Test Completo - 30 Verifiche</h1>
        <p style='color: white; margin: 0.5rem 0 0 0;'>Generazione, analisi e valutazione completa di 30 verifiche random</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Pulsante principale
    if st.button("🚀 LANCIA TEST COMPLETO - 30 VERIFICHE", type="primary", use_container_width=True):
        run_test_completo_30_verifiche()

def run_test_completo_30_verifiche():
    """Esegue il test completo con 30 verifiche"""
    
    with st.spinner("🔄 Inizializzazione test completo..."):
        # Crea directory
        os.makedirs("test_30_verifiche", exist_ok=True)
        os.makedirs("test_30_verifiche/pdfs", exist_ok=True)
        
        # Configurazione scenari random
        scenari_random = genera_scenari_random(30)
        
        # Progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        risultati = []
        
        for i, scenario in enumerate(scenari_random):
            # Aggiorna progress
            progress = (i + 1) / 30
            progress_bar.progress(progress)
            status_text.text(f"🔄 Generazione verifica {i+1}/30: {scenario['materia']} - {scenario['argomento']}")
            
            try:
                # 1. Genera verifica con l'app
                result = genera_verifica_reale(scenario)
                
                if result['success']:
                    # 2. Analizza con PromptFoo
                    analisi = analizza_con_promptfoo(result['output'], scenario)
                    
                    # 3. Genera PDF
                    pdf_result = genera_pdf_verifica(result['output'], scenario)
                    
                    # 4. Calcola punteggio finale
                    punteggio_finale = calcola_punteggio_finale(analisi, pdf_result)
                    
                    # Salva risultato
                    risultato_completo = {
                        "id": i + 1,
                        "scenario": scenario,
                        "generazione": result,
                        "analisi": analisi,
                        "pdf": pdf_result,
                        "punteggio_finale": punteggio_finale,
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    risultati.append(risultato_completo)
                    
                    # Salva singola verifica
                    filename = f"test_30_verifiche/verifica_{i+1:02d}_{scenario['materia']}_{scenario['livello'].replace(' ', '_')}.json"
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(risultato_completo, f, indent=2, ensure_ascii=False)
                
            except Exception as e:
                st.warning(f"⚠️ Errore verifica {i+1}: {e}")
                continue
        
        # Completa progress
        progress_bar.progress(1.0)
        status_text.text("✅ Test completato!")
        
        # Mostra risultati finali
        mostra_risultati_finali(risultati)

def genera_scenari_random(n):
    """Genera n scenari random"""
    
    materie = ["Matematica", "Italiano", "Fisica", "Storia", "Inglese", "Chimica"]
    livelli = ["Scuola Media", "Liceo Scientifico", "Istituto Tecnico", "Liceo Classico"]
    
    argomenti_per_materia = {
        "Matematica": ["Equazioni di secondo grado", "Funzioni", "Geometria piana", "Statistica", "Probabilità", "Trigonometria"],
        "Italiano": ["Analisi del testo poetico", "Grammatica", "Lessico", "Testo argomentativo", "Narrativa", "Poesia"],
        "Fisica": ["Leggi di Newton", "Elettromagnetismo", "Termodinamica", "Ottica", "Meccanica", "Onde"],
        "Storia": ["Storia contemporanea", "Medioevo", "Rinascimento", "Guerra mondiale", "Storia romana", "Risorgimento"],
        "Inglese": ["Reading comprehension", "Grammar", "Vocabulary", "Writing", "Listening skills", "British vs American"],
        "Chimica": ["Chimica organica", "Reazioni chimiche", "Struttura atomica", "Soluzioni", "pH", "Leggi dei gas"]
    }
    
    scenari = []
    
    for i in range(n):
        materia = random.choice(materie)
        livello = random.choice(livelli)
        argomento = random.choice(argomenti_per_materia[materia])
        
        scenario = {
            "materia": materia,
            "livello": livello,
            "argomento": argomento,
            "num_esercizi": random.randint(3, 6),
            "punti_totali": random.choice([60, 80, 100]),
            "durata": random.choice(["45 minuti", "60 minuti", "90 minuti"]),
            "mostra_punteggi": True,
            "con_griglia": random.choice([True, False])
        }
        
        scenari.append(scenario)
    
    return scenari

def genera_verifica_reale(scenario):
    """Genera verifica reale usando il sistema dell'app"""
    
    try:
        from prompts import prompt_corpo_verifica
        from config import CALIBRAZIONE_SCUOLA
        import google.generativeai as genai
        
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
            "con_griglia": scenario['con_griglia'],
            "note_generali": "",
            "istruzioni_esercizi": "",
            "e_mat": scenario['materia'] in ["Matematica", "Fisica", "Chimica"],
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
        
        return {
            "success": True,
            "prompt": prompt,
            "output": output,
            "tokens": len(prompt) + len(output)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def analizza_con_promptfoo(output, scenario):
    """Analizza output con stile PromptFoo"""
    
    import re
    
    analisi = {
        "esercizi": {},
        "punteggi": {},
        "qualita": {},
        "latex": {},
        "contenuto": {}
    }
    
    # 1. Analisi esercizi
    subsections = len(re.findall(r'\\subsection\*', output))
    esercizi_trovati = subsections
    esercizi_attesi = scenario['num_esercizi']
    analisi['esercizi'] = {
        "trovati": esercizi_trovati,
        "attesi": esercizi_attesi,
        "corretti": esercizi_trovati == esercizi_attesi,
        "punteggio": 25 if esercizi_trovati == esercizi_attesi else 0
    }
    
    # 2. Analisi punteggi
    points = re.findall(r'\((\d+)\s*pt\)', output)
    total_points = sum(int(p) for p in points)
    punti_attesi = scenario['punti_totali']
    analisi['punteggi'] = {
        "trovati": total_points,
        "attesi": punti_attesi,
        "corretti": total_points == punti_attesi,
        "punteggio": 25 if total_points == punti_attesi else 0
    }
    
    # 3. Qualità formule matematiche
    if scenario['materia'] in ["Matematica", "Fisica", "Chimica"]:
        math_formulas = len(re.findall(r'\$[^$]*\$', output))
        analisi['qualita']['formule'] = {
            "conteggio": math_formulas,
            "adeguato": math_formulas >= 2,
            "punteggio": 15 if math_formulas >= 2 else 5
        }
    else:
        analisi['qualita']['formule'] = {
            "conteggio": 0,
            "adeguato": True,
            "punteggio": 15
        }
    
    # 4. Qualità LaTeX
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
    
    analisi['latex'] = {
        "brackets_bilanciati": brackets_ok,
        "punteggio": 15 if brackets_ok else 0
    }
    
    # 5. Qualità contenuto
    lunghezza = len(output)
    analisi['contenuto'] = {
        "caratteri": lunghezza,
        "adeguato": 500 <= lunghezza <= 5000,
        "punteggio": 20 if 500 <= lunghezza <= 5000 else 10
    }
    
    return analisi

def genera_pdf_verifica(output, scenario):
    """Genera PDF della verifica"""
    
    try:
        # Crea LaTeX completo
        latex_completo = crea_latex_completo(output, scenario)
        
        # Salva file LaTeX
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        latex_file = f"test_30_verifiche/pdfs/verifica_{timestamp}.tex"
        
        with open(latex_file, 'w', encoding='utf-8') as f:
            f.write(latex_completo)
        
        # Prova a compilare PDF
        try:
            result = subprocess.run([
                "pdflatex", "-interaction=nonstopmode", "-output-directory=test_30_verifiche/pdfs", latex_file
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                pdf_file = latex_file.replace('.tex', '.pdf')
                return {
                    "success": True,
                    "latex_file": latex_file,
                    "pdf_file": pdf_file,
                    "pdf_size": os.path.getsize(pdf_file) if os.path.exists(pdf_file) else 0
                }
            else:
                return {
                    "success": False,
                    "error": "Compilazione LaTeX fallita",
                    "latex_error": result.stderr
                }
        
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Timeout compilazione PDF"
            }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def crea_latex_completo(output, scenario):
    """Crea documento LaTeX completo"""
    
    latex_header = r"""\documentclass[12pt,a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage[italian]{babel}
\usepackage{amsmath,amssymb}
\usepackage{geometry}
\geometry{a4paper, margin=2cm}
\usepackage{graphicx}
\usepackage{tikz}

\begin{document}

\begin{center}
{\Large \textbf{""" + scenario['materia'] + r""" - """ + scenario['argomento'] + r"""}}\\[0.5cm]
{\normalsize """ + scenario['livello'] + r""" - """ + scenario['durata'] + r"""}
\end{center}

\vspace{1cm}

"""
    
    latex_footer = r"""

\end{document}"""
    
    return latex_header + output + latex_footer

def calcola_punteggio_finale(analisi, pdf_result):
    """Calcola punteggio finale da 0 a 100"""
    
    punteggio = 0
    
    # Punteggi analisi (max 75)
    punteggio += analisi['esercizi']['punteggio']  # 25
    punteggio += analisi['punteggi']['punteggio']    # 25
    punteggio += analisi['qualita']['formule']['punteggio']  # 15
    punteggio += analisi['latex']['punteggio']       # 15
    punteggio += analisi['contenuto']['punteggio']    # 20
    
    # Punteggio PDF (max 25)
    if pdf_result['success']:
        punteggio += 25
    else:
        punteggio += 5  # Piccolo bonus anche se PDF fallisce
    
    return min(punteggio, 100)

def mostra_risultati_finali(risultati):
    """Mostra risultati finali del test completo"""
    
    st.markdown("---")
    st.markdown("## 📊 RISULTATI FINALI - 30 VERIFICHE")
    
    if not risultati:
        st.error("❌ Nessuna verifica generata con successo")
        return
    
    # Metriche generali
    totali = len(risultati)
    punteggi = [r['punteggio_finale'] for r in risultati]
    media = sum(punteggi) / len(punteggi)
    success_rate = len([r for r in risultati if r['pdf']['success']]) / totali * 100
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📝 Verifiche Totali", totali)
    with col2:
        st.metric("📈 Punteggio Medio", f"{media:.1f}/100")
    with col3:
        st.metric("📄 PDF Generati", f"{success_rate:.1f}%")
    with col4:
        st.metric("⭐ Success Rate", f"{len([r for r in risultati if r['punteggio_finale'] >= 70])}/{totali}")
    
    # Grafico distribuzione punteggi
    import plotly.express as px
    
    df_punteggi = [{"Verifica": f"V{r['id']}", "Punteggio": r['punteggio_finale']} for r in risultati]
    fig = px.histogram(df_punteggi, x="Punteggio", nbins=10, title="Distribuzione Punteggi")
    st.plotly_chart(fig, use_container_width=True)
    
    # Tabella dettagliata
    st.markdown("### 📋 Tabella Dettagliata Verifiche")
    
    for risultato in risultati:
        with st.expander(f"📝 Verifica {risultato['id']}: {risultato['scenario']['materia']} - {risultato['scenario']['argomento']} - Voto: {risultato['punteggio_finale']}/100"):
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**📋 Scenario:**")
                st.write(f"- Materia: {risultato['scenario']['materia']}")
                st.write(f"- Livello: {risultato['scenario']['livello']}")
                st.write(f"- Argomento: {risultato['scenario']['argomento']}")
                st.write(f"- Esercizi: {risultato['scenario']['num_esercizi']}")
                st.write(f"- Punti: {risultato['scenario']['punti_totali']}")
                st.write(f"- Durata: {risultato['scenario']['durata']}")
            
            with col2:
                st.markdown("**🔍 Analisi PromptFoo:**")
                st.write(f"- Esercizi: {risultato['analisi']['esercizi']['trovati']}/{risultato['analisi']['esercizi']['attesi']} {'✅' if risultato['analisi']['esercizi']['corretti'] else '❌'}")
                st.write(f"- Punteggi: {risultato['analisi']['punteggi']['trovati']}/{risultato['analisi']['punteggi']['attesi']} {'✅' if risultato['analisi']['punteggi']['corretti'] else '❌'}")
                st.write(f"- Formule: {risultato['analisi']['qualita']['formule']['conteggio']} {'✅' if risultato['analisi']['qualita']['formule']['adeguato'] else '❌'}")
                st.write(f"- LaTeX: {'✅' if risultato['analisi']['latex']['brackets_bilanciati'] else '❌'}")
                st.write(f"- Contenuto: {risultato['analisi']['contenuto']['caratteri']} caratteri {'✅' if risultato['analisi']['contenuto']['adeguato'] else '❌'}")
            
            # Punteggio finale
            voto = risultato['punteggio_finale']
            if voto >= 90:
                giudizio = "🏆 ECCELLENTE"
                colore = "green"
            elif voto >= 70:
                giudizio = "✅ BUONO"
                colore = "blue"
            elif voto >= 50:
                giudizio = "⚠️ SUFFICIENTE"
                colore = "orange"
            else:
                giudizio = "❌ INSUFFICIENTE"
                colore = "red"
            
            st.markdown(f"### 🎯 Voto Finale: {voto}/100 - {giudizio}")
            st.progress(voto / 100)
            
            # PDF
            if risultato['pdf']['success']:
                st.success(f"✅ PDF generato: {os.path.basename(risultato['pdf']['pdf_file'])} ({risultato['pdf']['pdf_size']} bytes)")
                if st.button(f"📄 Apri PDF {risultato['id']}", key=f"pdf_{risultato['id']}"):
                    # Qui potresti implementare apertura PDF
                    st.info("📄 Funzione apertura PDF da implementare")
            else:
                st.error(f"❌ PDF fallito: {risultato['pdf']['error']}")
            
            # Preview output
            with st.expander(f"📄 Preview Output LaTeX"):
                st.code(risultato['generazione']['output'][:500] + "..." if len(risultato['generazione']['output']) > 500 else risultato['generazione']['output'], language='latex')
    
    # Salva risultati completi
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    risultati_file = f"test_30_verifiche/risultati_completi_{timestamp}.json"
    
    with open(risultati_file, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "totali": totali,
            "media_punteggio": media,
            "success_rate_pdf": success_rate,
            "risultati": risultati
        }, f, indent=2, ensure_ascii=False)
    
    st.info(f"💾 Risultati completi salvati in: {risultati_file}")

# Funzione principale per integrare in main.py
def render_test_30_page():
    """Renderizza pagina test 30 verifiche"""
    render_test_completo_30()
