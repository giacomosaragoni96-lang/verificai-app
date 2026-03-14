"""
Integrazione del sistema di valutazione nell'app principale VerificAI
Aggiunge pulsante e funzionalità di valutazione dopo la generazione
"""

import streamlit as st
import json
from datetime import datetime
from valutazione_esercizi import estrai_esercizi_da_latex, salva_valutazione, init_database

def aggiungi_pulsante_valutazione(result, scenario):
    """Aggiunge pulsante per valutazione dopo generazione riuscita"""
    
    if result and result.get('success') and result.get('output'):
        st.markdown("---")
        st.subheader("📝 Valuta gli Esercizi Generati")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.info("💡 Puoi valutare singolarmente ogni esercizio e salvare le valutazioni nel database")
        
        with col2:
            if st.button("🎯 Avvia Valutazione", type="primary", use_container_width=True):
                # Avvia interfaccia valutazione inline
                render_valutazione_inline(result, scenario)

def render_valutazione_inline(result, scenario):
    """Interfaccia di valutazione integrata nella pagina principale"""
    
    # Inizializza database
    init_database()
    
    st.markdown("### 📋 Valutazione Dettagliata Esercizi")
    
    # Estrai LaTeX dal result
    latex_content = ""
    if isinstance(result['output'], dict):
        if 'A' in result['output']:
            A_value = result['output']['A']
            if isinstance(A_value, dict) and 'latex' in A_value:
                latex_content = A_value['latex']
            elif isinstance(A_value, str):
                latex_content = A_value
    elif isinstance(result['output'], str):
        latex_content = result['output']
    
    if not latex_content:
        st.error("❌ Impossibile estrarre LaTeX dalla verifica")
        return
    
    # Estrai esercizi
    esercizi = estrai_esercizi_da_latex(latex_content)
    
    if not esercizi:
        st.warning("⚠️ Nessun esercizio trovato nel LaTeX")
        return
    
    # Informazioni verifica
    materia = scenario.get('materia', 'Sconosciuta')
    argomento = scenario.get('argomento', 'Sconosciuto')
    
    st.success(f"✅ Trovati {len(esercizi)} esercizi da valutare")
    st.info(f"📚 Materia: {materia} | 📖 Argomento: {argomento}")
    
    # Form valutazione
    with st.form("form_valutazione"):
        st.subheader("🎯 Compila Valutazione")
        
        # ID verifica e valutatore
        col1, col2 = st.columns(2)
        with col1:
            id_verifica = st.text_input(
                "ID Verifica:",
                value=f"verifica_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
        with col2:
            valutatore = st.text_input("Valutatore:", value="Docente")
        
        valutazioni_salvate = []
        
        # Valutazione per ogni esercizio
        for i, esercizio in enumerate(esercizi):
            st.markdown(f"---")
            st.markdown(f"#### Esercizio {esercizio['numero']}: {esercizio['titolo']}")
            
            # Mostra contenuto sintetico
            with st.expander("📄 Mostra contenuto completo", expanded=False):
                st.code(esercizio['contenuto'], language='latex')
            
            # Griglia valutazione
            col1, col2, col3 = st.columns(3)
            
            with col1:
                punteggio_assegnato = st.number_input(
                    f"Punteggio (max {esercizio['punteggio_massimo']} pt):",
                    min_value=0.0,
                    max_value=float(esercizio['punteggio_massimo']),
                    value=float(esercizio['punteggio_massimo']),
                    step=0.5,
                    key=f"punteggio_{i}"
                )
                
                difficolta = st.selectbox(
                    "Difficoltà:",
                    ["Molto facile", "Facile", "Media", "Difficile", "Molto difficile"],
                    key=f"difficolta_{i}"
                )
            
            with col2:
                feedback = st.selectbox(
                    "Feedback:",
                    ["Eccellente", "Buono", "Sufficiente", "Insufficiente", "Da migliorare"],
                    key=f"feedback_{i}"
                )
                
                competenze = st.multiselect(
                    "Competenze:",
                    ["Comprensione", "Applicazione", "Analisi", "Sintesi", "Valutazione", "Creatività"],
                    key=f"competenze_{i}"
                )
            
            with col3:
                # Punteggio percentuale
                percentuale = (punteggio_assegnato / esercizio['punteggio_massimo']) * 100
                st.metric("Percentuale", f"{percentuale:.1f}%")
                
                # Colore basato su percentuale
                if percentuale >= 80:
                    st.success("🟢 Ottimo")
                elif percentuale >= 60:
                    st.warning("🟡 Sufficiente")
                else:
                    st.error("🔴 Da migliorare")
            
            commenti = st.text_area(
                "Commenti specifici:",
                key=f"commenti_{i}",
                placeholder="Note dettagliate su questo esercizio...",
                height=80
            )
            
            # Salva valutazione
            valutazioni_salvate.append({
                'id_verifica': id_verifica,
                'materia': materia,
                'argomento': argomento,
                'numero_esercizio': esercizio['numero'],
                'titolo_esercizio': esercizio['titolo'],
                'contenuto_esercizio': esercizio['contenuto'],
                'punteggio_assegnato': punteggio_assegnato,
                'punteggio_massimo': esercizio['punteggio_massimo'],
                'feedback': feedback,
                'commenti': commenti,
                'tag_difficolta': difficolta,
                'tag_competenze': ', '.join(competenze),
                'data_valutazione': datetime.now().isoformat(),
                'valutatore': valutatore
            })
        
        # Pulsanti azione
        col1, col2, col3 = st.columns(3)
        
        with col1:
            submitted = st.form_submit_button("💾 Salva Valutazioni", type="primary")
        
        with col2:
            if st.form_submit_button("📊 Anteprima Statistiche"):
                mostra_anteprima_statistiche(valutazioni_salvate)
        
        with col3:
            if st.form_submit_button("📥 Esporta JSON"):
                esporta_valutazioni_json(valutazioni_salvate)
        
        # Processa salvataggio
        if submitted:
            salvati = 0
            for val in valutazioni_salvate:
                if salva_valutazione(val):
                    salvati += 1
            
            if salvati > 0:
                st.success(f"✅ Salvate {salvati} valutazioni con successo!")
                st.balloons()
            else:
                st.error("❌ Errore nel salvataggio delle valutazioni")

def mostra_anteprima_statistiche(valutazioni):
    """Mostra anteprima statistiche delle valutazioni"""
    st.markdown("### 📊 Anteprima Statistiche")
    
    if not valutazioni:
        st.warning("Nessuna valutazione da analizzare")
        return
    
    # Calcola statistiche
    totale_esercizi = len(valutazioni)
    totale_punteggio_assegnato = sum(v['punteggio_assegnato'] for v in valutazioni)
    totale_punteggio_massimo = sum(v['punteggio_massimo'] for v in valutazioni)
    media_percentuale = (totale_punteggio_assegnato / totale_punteggio_massimo) * 100
    
    # Metriche principali
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Esercizi valutati", totale_esercizi)
    
    with col2:
        st.metric("Media punteggio", f"{totale_punteggio_assegnato/totale_esercizi:.1f}")
    
    with col3:
        st.metric("Media percentuale", f"{media_percentuale:.1f}%")
    
    with col4:
        st.metric("Punteggio totale", f"{totale_punteggio_assegnato}/{totale_punteggio_massimo}")
    
    # Distribuzione feedback
    feedback_counts = {}
    for val in valutazioni:
        feedback = val['feedback']
        feedback_counts[feedback] = feedback_counts.get(feedback, 0) + 1
    
    st.markdown("#### 📈 Distribuzione Feedback")
    for feedback, count in feedback_counts.items():
        percentage = (count / totale_esercizi) * 100
        st.write(f"**{feedback}:** {count} esercizi ({percentage:.1f}%)")
    
    # Distribuzione difficoltà
    difficolta_counts = {}
    for val in valutazioni:
        diff = val['tag_difficolta']
        difficolta_counts[diff] = difficolta_counts.get(diff, 0) + 1
    
    st.markdown("#### 🎯 Distribuzione Difficoltà")
    for diff, count in difficolta_counts.items():
        percentage = (count / totale_esercizi) * 100
        st.write(f"**{diff}:** {count} esercizi ({percentage:.1f}%)")

def esporta_valutazioni_json(valutazioni):
    """Esporta valutazioni in formato JSON"""
    if not valutazioni:
        st.warning("Nessuna valutazione da esportare")
        return
    
    # Prepara dati per export
    export_data = {
        'info_export': {
            'data_export': datetime.now().isoformat(),
            'totale_esercizi': len(valutazioni),
            'materia': valutazioni[0]['materia'] if valutazioni else 'N/A',
            'argomento': valutazioni[0]['argomento'] if valutazioni else 'N/A'
        },
        'valutazioni': valutazioni
    }
    
    # Converti in JSON
    json_data = json.dumps(export_data, indent=2, ensure_ascii=False)
    
    # Pulsante download
    st.download_button(
        label="📥 Scarica Valutazioni (JSON)",
        data=json_data,
        file_name=f"valutazioni_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json"
    )

def aggiungi_menu_valutazione():
    """Aggiunge voce menu per valutazioni"""
    # Da chiamare nel main.py per aggiungere al menu laterale
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📝 Valutazione")
    
    if st.sidebar.button("🎯 Valutazione Esercizi"):
        st.switch_page("valutazione_esercizi.py")
    
    if st.sidebar.button("📊 Statistiche Valutazioni"):
        st.switch_page("valutazione_esercizi.py")
