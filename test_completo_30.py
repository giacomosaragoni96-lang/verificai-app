#!/usr/bin/env python3
"""
Test Completo: 30 verifiche random + analisi PromptFoo + PDF finale
"""

import streamlit as st
import json
import os
import sys
from datetime import datetime
import re  # 🔧 FIX: Import mancante!
import random  # 🔧 FIX: Import mancante per scenari!
from pathlib import Path
import subprocess
from pathlib import Path

# Setup
PROJECT_ROOT = os.environ.get("VERIFICAI_ROOT", "C:\\Users\\gobli\\Desktop\\verificai")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

sys.path.insert(0, os.path.dirname(__file__))

def render_test_completo_30():
    """Renderizza pagina test completo 30 verifiche"""
    
    print("🚀 INIZIO render_test_completo_30()")
    
    st.markdown("""
    <div style="text-align: center; padding: 2rem 0;">
        <h1>🧪 TEST COMPLETO VERIFICAI</h1>
        <p>Test automatico del sistema di generazione verifiche con analisi completa</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Inizializza stato del test
    if 'test_30_results' not in st.session_state:
        st.session_state.test_30_results = None
    if 'test_30_running' not in st.session_state:
        st.session_state.test_30_running = False
    
    print(f"📊 Stato test: results={st.session_state.test_30_results is not None}, running={st.session_state.test_30_running}")
    
    # Se ci sono già risultati, li mostra
    if st.session_state.test_30_results:
        print("📋 Mostra risultati esistenti")
        mostra_risultati_finali(st.session_state.test_30_results)
        
        # Pulsante per nuovo test
        if st.button("🔄 LANCIA NUOVO TEST - 5 VERIFICHE", type="secondary", use_container_width=True, key="new_test_5"):
            print("🔄 Pulsante nuovo test cliccato")
            st.session_state.test_30_results = None
            st.session_state.test_30_running = True
            st.rerun()
        
        # Pulsante database
        if st.button("🗄️ GESTISCI DATABASE VERIFICHE", type="primary", use_container_width=True, key="manage_db_results"):
            st.session_state.show_database = True
            st.rerun()
        return
    
    # Se il test è in esecuzione, mostra progress
    if st.session_state.test_30_running:
        print("🔄 Test in esecuzione - avvia generazione")
        with st.spinner("🔄 Inizializzazione test completo..."):
            # Crea directory
            os.makedirs("test_30_verifiche", exist_ok=True)
            os.makedirs("test_30_verifiche/pdfs", exist_ok=True)
            
            # Configurazione scenari random
            scenari_random = genera_scenari_random(5)  # RIDOTTO DA 30 A 5 PER TEST VELOCI
            
            # Progress tracking
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            risultati = []
            
            for i, scenario in enumerate(scenari_random):
                # Aggiorna progress
                progress = (i + 1) / 5  # AGGIORNATO A 5 VERIFICHE
                progress_bar.progress(progress)
                status_text.text(f"🔄 Generazione verifica {i+1}/5: {scenario['materia']} - {scenario['argomento']}")
                
                try:
                    # 1. Genera verifica con l'app
                    print(f"🔄 Inizio generazione verifica {i+1}/5")
                    result = genera_verifica_reale(scenario)
                    
                    print(f"📊 Risultato generazione: {result['success']}")
                    
                    if result['success']:
                        print("✅ Generazione riuscita, procedo con analisi...")
                        
                        # 2. Analizza con PromptFoo
                        # Estrai il contenuto LaTeX dal dizionario
                        latex_content = result['output'].get('latex', '') if isinstance(result['output'], dict) else str(result['output'])
                        analisi = analizza_con_promptfoo(latex_content, scenario)
                        
                        # 3. Genera PDF
                        print("📄 Generazione PDF...")
                        pdf_result = genera_pdf_verifica(latex_content, scenario)
                        
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
                            "timestamp": datetime.now().isoformat(),
                            "latex_completo": pdf_result.get("latex_content", latex_content)
                        }
                        
                        risultati.append(risultato_completo)
                        
                        # Salva singola verifica (versione JSON-safe)
                        risultato_json_safe = make_json_safe({
                            "id": i + 1,
                            "scenario": scenario,
                            "generazione": result,
                            "analisi": analisi,
                            "pdf": pdf_result,
                            "punteggio_finale": punteggio_finale,
                            "timestamp": datetime.now().isoformat(),
                            "latex_completo": pdf_result.get("latex_content", latex_content)
                        })
                        
                        filename = f"test_30_verifiche/verifica_{i+1:02d}_{scenario['materia']}_{scenario['livello'].replace(' ', '_')}.json"
                        with open(filename, 'w', encoding='utf-8') as f:
                            json.dump(risultato_json_safe, f, indent=2, ensure_ascii=False)
                        
                        print(f"💾 Verifica {i+1} salvata in {filename}")
                    
                    else:
                        print(f"❌ Errore generazione verifica {i+1}: {result.get('error', 'Errore sconosciuto')}")
                        if 'traceback' in result:
                            print(f"🔍 Traceback: {result['traceback']}")
                        continue
                
                except Exception as e:
                    print(f"❌ Errore generale verifica {i+1}: {e}")
                    import traceback
                    print(f"🔍 Traceback generale: {traceback.format_exc()}")
                    continue
            
            # Completa progress
            progress_bar.progress(1.0)
            status_text.text("✅ Test completato!")
            
            # Salva risultati in session state
            st.session_state.test_30_results = risultati
            st.session_state.test_30_running = False
            
            # Integra nel database
            with st.spinner("🔄 Salvataggio nel database..."):
                from verifiche_database import integra_database_in_test
                aggiunte = integra_database_in_test(risultati)
                st.success(f"✅ {aggiunte} verifiche aggiunte al database!")
            
            # NON fare rerun - lascia che Streamlit mostri i risultati naturalmente
    
    # Mostra database se richiesto
    if st.session_state.get('show_database', False):
        from verifiche_database import render_database_manager
        render_database_manager()
        
        if st.button("← Torna al Test", type="secondary", key="back_to_test"):
            st.session_state.show_database = False
            st.rerun()
        return
    
    # Pulsanti principali
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🚀 LANCIA TEST COMPLETO - 5 VERIFICHE", type="primary", use_container_width=True, key="start_test_5"):
            print("🚀 PULSANTE START TEST CLICCATO!")
            st.session_state.test_30_running = True
            st.rerun()
    
    with col2:
        if st.button("🗄️ GESTISCI DATABASE VERIFICHE", type="secondary", use_container_width=True, key="manage_db"):
            st.session_state.show_database = True
            st.rerun()

def genera_scenari_random(n):
    """Genera n scenari random realistici per VerificAI"""
    
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
    
    durate_realistiche = ["30 minuti", "45 minuti", "1 ora", "1 ora e 30 minuti", "2 ore"]
    
    scenari = []
    
    for i in range(n):
        materia = random.choice(materie)
        livello = random.choice(livelli)
        argomento = random.choice(argomenti_per_materia[materia])
        
        scenario = {
            "materia": materia,
            "livello": livello,
            "argomento": argomento,
            "num_esercizi": random.randint(2, 8),  # Range realistico
            "punti_totali": random.choice([30, 40, 50, 60, 80, 100, 120, 150]),  # Multipli di 10 realistici
            "durata": random.choice(durate_realistiche),
            "mostra_punteggi": random.random() < 0.9,  # 90% come nell'app
            "con_griglia": random.random() < 0.7   # 70% come nell'app
        }
        
        scenari.append(scenario)
    
    return scenari

def genera_verifica_reale(scenario):
    """Genera una verifica reale usando il sistema completo dell'app"""
    
    print(f"🔄 INIZIO GENERA_VERIFICA_REALE - Scenario: {scenario['materia']} - {scenario['argomento']}")
    
    try:
        from generation import genera_verifica
        from config import CALIBRAZIONE_SCUOLA
        import google.generativeai as genai
        
        # Calibrazione
        calibrazione = CALIBRAZIONE_SCUOLA.get(scenario['livello'], "")
        print(f"📋 Calibrazione: {calibrazione[:100]}...")
        
        # Usa lo stesso modello dell'app
        model = genai.GenerativeModel('gemini-2.5-flash-lite')
        print("🤖 Modello creato")
        
        # Genera con il sistema completo dell'app
        print("🚀 Chiamata genera_verifica()...")
        
        # DEBUG: Stampa parametri prima della chiamata
        print(f"📋 Parametri genera_verifica:")
        print(f"  - materia: {scenario['materia']}")
        print(f"  - argomento: {scenario['argomento']}")
        print(f"  - num_esercizi: {scenario['num_esercizi']}")
        print(f"  - punti_totali: {scenario['punti_totali']}")
        print(f"  - mostra_punteggi: {scenario['mostra_punteggi']}")
        print(f"  - con_griglia: {scenario['con_griglia']}")
        print(f"  - durata: {scenario['durata']}")
        
        # 🛠️ FIX: Genera istruzioni esercizi come fa l'app!
        print("🔧 Generazione istruzioni esercizi...")
        try:
            # Importa la funzione dall'app principale
            import sys
            sys.path.insert(0, PROJECT_ROOT)
            from main import _build_prompt_esercizi
            
            istruzioni_esercizi, immagini_esercizi = _build_prompt_esercizi(
                esercizi_custom=[],  # Nessun esercizio custom per test
                num_totale=scenario['num_esercizi'],
                punti_totali=scenario['punti_totali'],
                mostra_punteggi=scenario['mostra_punteggi']
            )
            print(f"✅ Istruzioni generate: {len(istruzioni_esercizi)} caratteri")
            print(f"📄 Preview istruzioni: {istruzioni_esercizi[:200]}...")
            
        except Exception as e:
            print(f"⚠️ Errore generazione istruzioni: {e}")
            # Fallback: istruzioni minime
            istruzioni_esercizi = f"Genera ESATTAMENTE {scenario['num_esercizi']} esercizi. Ogni esercizio è \\subsection*{{Esercizio N: Titolo}}."
            immagini_esercizi = []
        
        # 🛠️ DEBUG: Verifica parametri critici
        print(f"🔍 CONTROLLO PARAMETRI CRITICI:")
        print(f"  - materia: '{scenario['materia']}' (type: {type(scenario['materia'])})")
        print(f"  - argomento: '{scenario['argomento']}' (type: {type(scenario['argomento'])})")
        print(f"  - difficolta: 'media' (type: {type('media')})")
        print(f"  - calibrazione: '{calibrazione[:100]}...' (type: {type(calibrazione)})")
        print(f"  - durata: '{scenario['durata']}' (type: {type(scenario['durata'])})")
        print(f"  - num_esercizi: {scenario['num_esercizi']} (type: {type(scenario['num_esercizi'])})")
        print(f"  - punti_totali: {scenario['punti_totali']} (type: {type(scenario['punti_totali'])})")
        print(f"  - mostra_punteggi: {scenario['mostra_punteggi']} (type: {type(scenario['mostra_punteggi'])})")
        print(f"  - con_griglia: {scenario['con_griglia']} (type: {type(scenario['con_griglia'])})")
        print(f"  - note_generali: '' (type: {type('')})")
        print(f"  - istruzioni_esercizi: {len(istruzioni_esercizi)} caratteri (type: {type(istruzioni_esercizi)})")
        print(f"  - immagini_esercizi: {len(immagini_esercizi)} elementi")
        
        # 🛠️ DEBUG: Test con parametri minimali come l'app
        print(f"🚀 Chiamata genera_verifica con parametri test...")
        
        result = genera_verifica(
            model=model,
            materia=scenario['materia'],
            argomento=scenario['argomento'],
            difficolta="media",  # Default
            calibrazione=calibrazione,
            durata=scenario['durata'],
            num_esercizi=scenario['num_esercizi'],
            punti_totali=scenario['punti_totali'],
            mostra_punteggi=scenario['mostra_punteggi'],
            con_griglia=scenario['con_griglia'],
            doppia_fila=False,
            bes_dsa=False,
            perc_ridotta=25,
            bes_dsa_b=False,
            genera_soluzioni=False,
            note_generali="",  # Vuoto per test
            istruzioni_esercizi=istruzioni_esercizi,  # 🛠️ FIX: Istruzioni proper!
            immagini_esercizi=immagini_esercizi,
            file_ispirazione=None,
            mathpix_context=None,
        )
        
        print(f"📊 genera_verifica() completata - Tipo risultato: {type(result)}")
        
        # DEBUG: Stampa l'output completo per diagnosi
        print(f" DEBUG - Output completo:")
        print(f"Tipo: {type(result)}")
        if isinstance(result, dict):
            print(f"Chiavi: {list(result.keys())}")
            
            # Cerca il LaTeX in diverse posizioni possibili
            latex_output = ""
            if 'latex' in result:
                latex_output = result['latex']
                print(f" Trovato latex in root")
            elif 'A' in result and isinstance(result['A'], dict) and 'latex' in result['A']:
                latex_output = result['A']['latex']
                print(f" Trovato latex in A['latex']")
                
                # DEBUG APPROFONDITO - Analisi del contenuto
                print(f"🔍 ANALISI DETTAGLIATA CONTENUTO:")
                print(f"  - Lunghezza totale: {len(latex_output)} caratteri")
                print(f"  - Contiene \\begin{{document}}: {'\\begin{document}' in latex_output}")
                print(f"  - Contiene \\end{{document}}: {'\\end{document}' in latex_output}")
                print(f"  - Contiene esercizi (\\subsection): {'\\subsection' in latex_output}")
                print(f"  - Numero di \\subsection: {len(re.findall(r'\\\\subsection', latex_output))}")
                
                # Controlla se c'è solo l'header
                if '\\begin{document}' in latex_output and '\\end{document}' in latex_output:
                    # Estrai il corpo tra begin e end
                    begin_idx = latex_output.find('\\begin{document}')
                    end_idx = latex_output.find('\\end{document}')
                    corpo = latex_output[begin_idx:end_idx]
                    print(f"  - Corpo documento: {len(corpo)} caratteri")
                    print(f"  - Corpo vuoto o solo spazi: {corpo.strip() == ''}")
                    
                    # Stampa il corpo per debug
                    if corpo.strip():
                        print(f"  - Contenuto corpo (primi 200 char):")
                        print(f"    {corpo[:200]}")
                    else:
                        print(f"  - ❌ CORPO VUOTO! Solo header presente")
                        
            elif 'B' in result and isinstance(result['B'], dict) and 'latex' in result['B']:
                latex_output = result['B']['latex']
                print(f" Trovato latex in B['latex']")
            else:
                print(f"❌ Nessun latex trovato!")
                # Stampa contenuto di A e B per debug
                if 'A' in result:
                    print(f"Contenuto A: {type(result['A'])} - {list(result['A'].keys()) if isinstance(result['A'], dict) else 'Not dict'}")
                if 'B' in result:
                    print(f"Contenuto B: {type(result['B'])} - {list(result['B'].keys()) if isinstance(result['B'], dict) else 'Not dict'}")
            
            if latex_output:
                print(f"LaTeX preview (primi 500 char):")
                print(latex_output[:500])
        else:
            print(f"Output raw: {str(result)[:500]}")
        
        print(f" Generazione completata. Lunghezza output: {len(result)}")
        
        return {
            "success": True,
            "output": result,
            "prompt_used": "Sistema completo VerificAI",
            "tokens": len(result)
        }
        
    except Exception as e:
        print(f"❌ Errore generazione: {e}")
        import traceback
        print(f"🔍 Traceback: {traceback.format_exc()}")
        
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }

def make_json_safe(obj):
    """Rimuove dati non JSON-serializzabili da un dizionario"""
    import json
    from datetime import datetime
    
    if isinstance(obj, dict):
        return {k: make_json_safe(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_json_safe(item) for item in obj]
    elif isinstance(obj, (bytes, bytearray)):
        return f"<BYTES:{len(obj)}>"
    elif isinstance(obj, datetime):
        return obj.isoformat()
    else:
        return obj

def analizza_con_promptfoo(output, scenario):
    """Analisi output con stile PromptFoo focalizzato su VerificAI"""
    
    import re
    
    analisi = {
        "esercizi": {},
        "punteggi": {},
        "struttura": {},
        "tabella": {},
        "griglia": {},
        "latex": {}
    }
    
    # 1. Analisi esercizi (30 punti)
    subsections = len(re.findall(r'\\subsection\*', output))
    esercizi_trovati = subsections
    esercizi_attesi = scenario['num_esercizi']
    analisi['esercizi'] = {
        "trovati": esercizi_trovati,
        "attesi": esercizi_attesi,
        "corretti": esercizi_trovati == esercizi_attesi,
        "punteggio": 30 if esercizi_trovati == esercizi_attesi else 0
    }
    
    # 2. Analisi punteggi (30 punti)
    points = re.findall(r'\((\d+)\s*pt\)', output)
    total_points = sum(int(p) for p in points)
    punti_attesi = scenario['punti_totali']
    analisi['punteggi'] = {
        "trovati": total_points,
        "attesi": punti_attesi,
        "corretti": total_points == punti_attesi,
        "punteggio": 30 if total_points == punti_attesi else 0
    }
    
    # 3. Analisi struttura gerarchica (20 punti)
    struttura_elements = [
        r'\\subsection\*',     # Esercizi
        r'\\begin{enumerate}',  # Liste numerate
        r'\\item',             # Item delle liste
        r'\\begin{center}',    # Elementi centrati
        r'\\textbf{',          # Testo grassetto
        r'\\vspace{'           # Spaziatura verticale
    ]
    
    struttura_count = sum(1 for pattern in struttura_elements if re.search(pattern, output))
    analisi['struttura'] = {
        "elementi_trovati": struttura_count,
        "elementi_attesi": 4,  # Minimo 4 elementi per struttura decente
        "adeguata": struttura_count >= 4,
        "punteggio": 20 if struttura_count >= 4 else 10
    }
    
    # 4. Analisi tabella punteggi (10 punti) - solo se richiesto
    if scenario['mostra_punteggi']:
        tabella_punteggi = bool(re.search(r'\\begin{tabular}.*punti.*\\end{tabular}', output, re.I))
        analisi['tabella'] = {
            "richiesta": True,
            "presente": tabella_punteggi,
            "punteggio": 10 if tabella_punteggi else 0
        }
    else:
        analisi['tabella'] = {
            "richiesta": False,
            "presente": False,
            "punteggio": 10  # Punti pieni se non richiesta
        }
    
    # 5. Analisi griglia (5 punti) - solo se richiesta
    if scenario['con_griglia']:
        griglia_presente = bool(re.search(r'\\begin{tikzpicture}.*\\end{tikzpicture}', output, re.DOTALL))
        analisi['griglia'] = {
            "richiesta": True,
            "presente": griglia_presente,
            "punteggio": 5 if griglia_presente else 0
        }
    else:
        analisi['griglia'] = {
            "richiesta": False,
            "presente": False,
            "punteggio": 5  # Punti pieni se non richiesta
        }
    
    # 6. Validità LaTeX (5 punti)
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
        "punteggio": 5 if brackets_ok else 0
    }
    
    return analisi

def genera_pdf_verifica(output, scenario):
    """Genera PDF della verifica con LaTeX completo"""
    
    try:
        # Crea LaTeX completo con header e footer
        latex_completo = crea_latex_completo(output, scenario)
        
        # Salva file LaTeX completo
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
                    "pdf_size": os.path.getsize(pdf_file) if os.path.exists(pdf_file) else 0,
                    "latex_content": latex_completo  # Salviamo anche il contenuto completo
                }
            else:
                return {
                    "success": False,
                    "error": "Compilazione LaTeX fallita",
                    "latex_error": result.stderr,
                    "latex_content": latex_completo  # Per debug
                }
        
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Timeout compilazione PDF",
                "latex_content": latex_completo
            }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "latex_content": latex_completo if 'latex_completo' in locals() else output
        }

def crea_latex_completo(output, scenario):
    """Crea documento LaTeX completo e valido"""
    
    # Header completo con tutti i package necessari
    latex_header = r"""\documentclass[12pt,a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage[italian]{babel}
\usepackage[T1]{fontenc}
\usepackage{amsmath,amssymb,amsthm}
\usepackage{geometry}
\geometry{a4paper, margin=2cm, top=2.5cm, bottom=2.5cm}
\usepackage{graphicx}
\usepackage{tikz}
\usetikzlibrary{shapes,arrows,positioning}
\usepackage{array}
\usepackage{booktabs}
\usepackage{longtable}
\usepackage{multicol}
\usepackage{enumitem}
\usepackage{xcolor}

\pagestyle{empty}
\begin{document}

"""
    
    # Titolo e intestazione (senza f-string per evitare problemi)
    titolo = r"""\begin{center}
{\Large \textbf{""" + scenario['materia'] + r""" - """ + scenario['argomento'] + r"""}}\\[0.5cm]
{\normalsize """ + scenario['livello'] + r""" - """ + scenario['durata'] + r"""}\\[0.5cm]
{\small Verifica di valutazione}
\end{center}

\vspace{1cm}

"""
    
    # Footer
    latex_footer = r"""

\end{document}"""
    
    # Combina tutto
    latex_completo = latex_header + titolo + output + latex_footer
    
    return latex_completo

def calcola_punteggio_finale(analisi, pdf_result):
    """Calcola punteggio finale VerificAI-realista da 0 a 100"""
    
    punteggio = 0
    
    # Punteggi analisi (max 100 punti)
    punteggio += analisi['esercizi']['punteggio']    # 30 punti
    punteggio += analisi['punteggi']['punteggio']      # 30 punti
    punteggio += analisi['struttura']['punteggio']    # 20 punti
    punteggio += analisi['tabella']['punteggio']      # 10 punti
    punteggio += analisi['griglia']['punteggio']      # 5 punti
    punteggio += analisi['latex']['punteggio']        # 5 punti
    
    # PDF è bonus, non parte del voto
    # if pdf_result['success']:
    #     punteggio += 0  # Non influisce sul voto
    
    return min(punteggio, 100)

def mostra_risultati_finali(risultati):
    """Mostra risultati finali del test completo"""
    
    import os
    
    st.markdown("---")
    st.markdown("## 📊 RISULTATI FINALI - 30 VERIFICHE")
    
    if not risultati:
        st.error("❌ Nessuna verifica generata con successo")
        return
    
    # Metriche generali VerificAI-focused
    totali = len(risultati)
    punteggi = [r['punteggio_finale'] for r in risultati]
    media = sum(punteggi) / len(punteggi)
    pdf_rate = len([r for r in risultati if r['pdf']['success']]) / totali * 100
    success_rate = len([r for r in risultati if r['punteggio_finale'] >= 70]) / totali * 100
    
    # Parametri accuracy
    esercizi_corretti = len([r for r in risultati if r['analisi']['esercizi']['corretti']])
    punti_corretti = len([r for r in risultati if r['analisi']['punteggi']['corretti']])
    param_accuracy = ((esercizi_corretti + punti_corretti) / (totali * 2)) * 100
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📝 Verifiche Totali", totali)
    with col2:
        st.metric("📈 Voto Medio", f"{media:.1f}/100")
    with col3:
        st.metric("🎯 Success Rate", f"{success_rate:.1f}%")
    with col4:
        st.metric("⚙️ Param Accuracy", f"{param_accuracy:.1f}%")
    
    # PDF Rate separato
    st.metric("📄 PDF Generati", f"{pdf_rate:.1f}%")
    
    # Grafico distribuzione punteggi (senza plotly)
    st.markdown("### 📊 Distribuzione Punteggi")
    
    # Crea dati per istogramma
    punteggi = [r['punteggio_finale'] for r in risultati]
    
    # Crea intervalli
    intervalli = [(0, 50), (50, 60), (60, 70), (70, 80), (80, 90), (90, 100)]
    conteggi = []
    etichette = []
    
    for min_val, max_val in intervalli:
        conteggio = len([p for p in punteggi if min_val <= p < max_val])
        conteggi.append(conteggio)
        if max_val == 100:
            etichette.append(f"{min_val}-100")
        else:
            etichette.append(f"{min_val}-{max_val-1}")
    
    # Mostra istogramma con bar chart di Streamlit
    import pandas as pd
    df = pd.DataFrame({
        'Intervallo': etichette,
        'Numero Verifiche': conteggi
    })
    
    st.bar_chart(df.set_index('Intervallo')['Numero Verifiche'])
    
    # Statistiche aggiuntive
    st.markdown("### 📈 Statistiche Aggiuntive")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Voto Minimo", min(punteggi))
    with col2:
        st.metric("Voto Massimo", max(punteggi))
    with col3:
        st.metric("Mediana", sorted(punteggi)[len(punteggi)//2])
    
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
                st.markdown("**🔍 Analisi VerificAI:**")
                st.write(f"- Esercizi: {risultato['analisi']['esercizi']['trovati']}/{risultato['analisi']['esercizi']['attesi']} {'✅' if risultato['analisi']['esercizi']['corretti'] else '❌'}")
                st.write(f"- Punteggi: {risultato['analisi']['punteggi']['trovati']}/{risultato['analisi']['punteggi']['attesi']} {'✅' if risultato['analisi']['punteggi']['corretti'] else '❌'}")
                st.write(f"- Struttura: {risultato['analisi']['struttura']['elementi_trovati']} elementi {'✅' if risultato['analisi']['struttura']['adeguata'] else '❌'}")
                st.write(f"- Tabella: {'Richiesta' if risultato['analisi']['tabella']['richiesta'] else 'Non richiesta'} - {'✅' if risultato['analisi']['tabella']['presente'] else '❌' if risultato['analisi']['tabella']['richiesta'] else '✅'}")
                st.write(f"- Griglia: {'Richiesta' if risultato['analisi']['griglia']['richiesta'] else 'Non richiesta'} - {'✅' if risultato['analisi']['griglia']['presente'] else '❌' if risultato['analisi']['griglia']['richiesta'] else '✅'}")
                st.write(f"- LaTeX: {'✅' if risultato['analisi']['latex']['brackets_bilanciati'] else '❌'}")
            
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
            with st.expander(f"📄 Preview Output Completo - {risultato['id']}"):
                # Mostra codice LaTeX completo
                latex_completo = risultato.get('latex_completo', risultato['generazione']['output'])
                
                st.markdown("**📝 Codice LaTeX Completo:**")
                st.code(latex_completo, language='latex')
                
                # Mostra preview renderizzata
                st.markdown("**📄 Preview Renderizzata:**")
                try:
                    # Estrai titolo ed esercizi principali
                    import re
                    
                    # Cerca esercizi
                    esercizi = re.findall(r'\\subsection\*\{([^}]+)\}', latex_completo)
                    punti = re.findall(r'\((\d+)\s*pt\)', latex_completo)
                    
                    st.markdown(f"**📋 Struttura Verifica:**")
                    st.write(f"- **Materia:** {risultato['scenario']['materia']}")
                    st.write(f"- **Esercizi trovati:** {len(esercizi)}")
                    st.write(f"- **Punti totali:** {sum(int(p) for p in punti)}")
                    st.write(f"- **Lunghezza LaTeX:** {len(latex_completo)} caratteri")
                    st.write(f"- **Contiene \\end{{document}}:** {'✅' if '\\end{document}' in latex_completo else '❌'}")
                    
                    if esercizi:
                        st.markdown("**📝 Esercizi:**")
                        for i, esercizio in enumerate(esercizi[:5], 1):  # Primi 5
                            st.write(f"{i}. {esercizio}")
                        if len(esercizi) > 5:
                            st.write(f"... e altri {len(esercizi) - 5} esercizi")
                    
                except Exception as e:
                    st.warning(f"⚠️ Preview non disponibile: {e}")
                
                # Mostra info PDF con pulsante apertura
                if risultato.get('pdf', {}).get('success'):
                    pdf_file = risultato['pdf']['pdf_file']
                    pdf_size = risultato['pdf']['pdf_size']
                    
                    st.success(f"📄 PDF generato: {os.path.basename(pdf_file)} ({pdf_size} bytes)")
                    
                    # Pulsanti per PDF
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(f"👁️ Apri PDF {risultato['id']}", key=f"open_pdf_{risultato['id']}"):
                            try:
                                import webbrowser
                                import os
                                webbrowser.open(f'file://{os.path.abspath(pdf_file)}')
                                st.success(f"📂 PDF aperto nel browser")
                            except Exception as e:
                                st.error(f"❌ Errore apertura PDF: {e}")
                    
                    with col2:
                        if st.button(f"💾 Scarica PDF {risultato['id']}", key=f"download_pdf_{risultato['id']}"):
                            try:
                                with open(pdf_file, 'rb') as f:
                                    st.download_button(
                                        label=f"⬇️ Download {os.path.basename(pdf_file)}",
                                        data=f.read(),
                                        file_name=os.path.basename(pdf_file),
                                        mime="application/pdf"
                                    )
                            except Exception as e:
                                st.error(f"❌ Errore download PDF: {e}")
                else:
                    st.error(f"❌ PDF fallito: {risultato['pdf'].get('error', 'Errore sconosciuto')}")
                    
                    # Mostra errore LaTeX se disponibile
                    if 'latex_error' in risultato['pdf']:
                        st.markdown("**🔍 Errore LaTeX:**")
                        st.code(risultato['pdf']['latex_error'][:500], language='text')
    
    # Salva risultati completi VerificAI-focused
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    risultati_file = f"test_30_verifiche/risultati_completi_{timestamp}.json"
    
    with open(risultati_file, 'w', encoding='utf-8') as f:
        json.dump(make_json_safe({
            "timestamp": datetime.now().isoformat(),
            "totali": totali,
            "media_voto": media,
            "success_rate": success_rate,
            "param_accuracy": param_accuracy,
            "pdf_rate": pdf_rate,
            "risultati": risultati
        }), f, indent=2, ensure_ascii=False)
    
    st.info(f"💾 Risultati VerificAI salvati in: {risultati_file}")

# Funzione principale per integrare in main.py
def render_test_30_page():
    """Renderizza pagina test 30 verifiche"""
    render_test_completo_30()
