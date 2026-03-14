"""
Sistema di valutazione dettagliata per esercizi VerificAI
Permette di valutare singoli esercizi e salvarli in database con tagging
"""

import streamlit as st
import json
import os
from datetime import datetime
from typing import Dict, List, Any
import re
import sqlite3
from pathlib import Path

# Configurazione database
DB_PATH = "valutazioni_esercizi.db"

def init_database():
    """Inizializza il database per le valutazioni"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Tabella esercizi valutati
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS esercizi_valutati (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_verifica TEXT,
            materia TEXT,
            argomento TEXT,
            numero_esercizio INTEGER,
            titolo_esercizio TEXT,
            contenuto_esercizio TEXT,
            punteggio_assegnato REAL,
            punteggio_massimo REAL,
            feedback TEXT,
            commenti TEXT,
            tag_difficolta TEXT,
            tag_competenze TEXT,
            data_valutazione TEXT,
            valutatore TEXT,
            UNIQUE(id_verifica, numero_esercizio)
        )
    ''')
    
    # Tabella statistiche
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS statistiche_valutazioni (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            materia TEXT,
            argomento TEXT,
            media_punteggi REAL,
            numero_esercizi INTEGER,
            data_aggiornamento TEXT,
            UNIQUE(materia, argomento)
        )
    ''')
    
    conn.commit()
    conn.close()

def estrai_esercizi_da_latex(latex_content: str) -> List[Dict[str, Any]]:
    """Estrae gli esercizi dal LaTeX"""
    esercizi = []
    
    # Trova tutti i \subsection*
    pattern = r'\\subsection\*\{([^}]+)\}(.*?)(?=\\subsection\*|\\end\{document\}|$)'
    matches = re.findall(pattern, latex_content, re.DOTALL)
    
    for i, (titolo, contenuto) in enumerate(matches, 1):
        # Estrae punteggio dal titolo se presente
        punteggio_match = re.search(r'\((\d+)\s*pt\)', titolo)
        punteggio_massimo = int(punteggio_match.group(1)) if punteggio_match else 10
        
        # Pulisce il titolo
        titolo_pulito = re.sub(r'\s*\(\d+\s*pt\)\s*$', '', titolo).strip()
        
        esercizi.append({
            'numero': i,
            'titolo': titolo_pulito,
            'contenuto': contenuto.strip(),
            'punteggio_massimo': punteggio_massimo
        })
    
    return esercizi

def salva_valutazione(valutazione: Dict[str, Any]):
    """Salva una valutazione nel database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO esercizi_valutati 
            (id_verifica, materia, argomento, numero_esercizio, titolo_esercizio, 
             contenuto_esercizio, punteggio_assegnato, punteggio_massimo, feedback, 
             commenti, tag_difficolta, tag_competenze, data_valutazione, valutatore)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            valutazione['id_verifica'],
            valutazione['materia'],
            valutazione['argomento'],
            valutazione['numero_esercizio'],
            valutazione['titolo_esercizio'],
            valutazione['contenuto_esercizio'],
            valutazione['punteggio_assegnato'],
            valutazione['punteggio_massimo'],
            valutazione['feedback'],
            valutazione['commenti'],
            valutazione['tag_difficolta'],
            valutazione['tag_competenze'],
            valutazione['data_valutazione'],
            valutazione['valutatore']
        ))
        
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Errore salvando valutazione: {e}")
        return False
    finally:
        conn.close()

def carica_valutazioni(materia: str = None, argomento: str = None) -> List[Dict[str, Any]]:
    """Carica valutazioni dal database con filtri opzionali"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    query = "SELECT * FROM esercizi_valutati WHERE 1=1"
    params = []
    
    if materia:
        query += " AND materia = ?"
        params.append(materia)
    
    if argomento:
        query += " AND argomento = ?"
        params.append(argomento)
    
    query += " ORDER BY data_valutazione DESC"
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    # Converti in dizionari
    valutazioni = []
    for row in rows:
        valutazioni.append({
            'id': row[0],
            'id_verifica': row[1],
            'materia': row[2],
            'argomento': row[3],
            'numero_esercizio': row[4],
            'titolo_esercizio': row[5],
            'contenuto_esercizio': row[6],
            'punteggio_assegnato': row[7],
            'punteggio_massimo': row[8],
            'feedback': row[9],
            'commenti': row[10],
            'tag_difficolta': row[11],
            'tag_competenze': row[12],
            'data_valutazione': row[13],
            'valutatore': row[14]
        })
    
    conn.close()
    return valutazioni

def get_statistiche_materia_argomento() -> Dict[str, Any]:
    """Ottiene statistiche per materia-argomento"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            materia, 
            argomento,
            AVG(punteggio_assegnato) as media_punteggi,
            COUNT(*) as numero_esercizi,
            MAX(data_valutazione) as ultimo_aggiornamento
        FROM esercizi_valutati 
        GROUP BY materia, argomento
        ORDER BY materia, argomento
    ''')
    
    rows = cursor.fetchall()
    conn.close()
    
    statistiche = {}
    for row in rows:
        chiave = f"{row[0]} - {row[1]}"
        statistiche[chiave] = {
            'materia': row[0],
            'argomento': row[1],
            'media_punteggi': round(row[2], 2),
            'numero_esercizi': row[3],
            'ultimo_aggiornamento': row[4]
        }
    
    return statistiche

def render_interfaccia_valutazione():
    """Interfaccia principale per la valutazione"""
    st.title("📝 Valutazione Dettagliata Esercizi")
    
    # Inizializza database
    init_database()
    
    # Sidebar per navigazione
    st.sidebar.title("🎯 Navigazione")
    pagina = st.sidebar.selectbox("Scegli azione", [
        "Nuova Valutazione",
        "Valutazioni Salvate",
        "Statistiche",
        "Ricerca Avanzata"
    ])
    
    if pagina == "Nuova Valutazione":
        render_nuova_valutazione()
    elif pagina == "Valutazioni Salvate":
        render_valutazioni_salvate()
    elif pagina == "Statistiche":
        render_statistiche()
    elif pagina == "Ricerca Avanzata":
        render_ricerca_avanzata()

def render_nuova_valutazione():
    """Interfaccia per nuova valutazione"""
    st.header("📋 Nuova Valutazione")
    
    # Upload del file LaTeX o incolla testo
    input_method = st.radio("Come vuoi inserire il LaTeX?", ["Incolla testo", "Carica file"])
    
    latex_content = ""
    if input_method == "Incolla testo":
        latex_content = st.text_area(
            "Incolla qui il LaTeX completo della verifica:",
            height=300,
            placeholder=r"\documentclass[12pt,a4paper]{article}..."
        )
    else:
        uploaded_file = st.file_uploader("Carica file .tex", type=['tex'])
        if uploaded_file:
            latex_content = uploaded_file.getvalue().decode('utf-8')
    
    if latex_content:
        # Estrai informazioni generali
        materia_match = re.search(r'Verifica di ([^:]+):', latex_content)
        argomento_match = re.search(r': ([^\n]+)', latex_content[latex_content.find('Verifica di'):])
        
        materia = materia_match.group(1) if materia_match else "Sconosciuta"
        argomento = argomento_match.group(1).strip() if argomento_match else "Sconosciuto"
        
        st.info(f"📚 Materia: {materia} | 📖 Argomento: {argomento}")
        
        # Estrai esercizi
        esercizi = estrai_esercizi_da_latex(latex_content)
        
        if not esercizi:
            st.warning("⚠️ Nessun esercizio trovato nel LaTeX")
            return
        
        st.success(f"✅ Trovati {len(esercizi)} esercizi")
        
        # Form per valutazione
        st.subheader("🎯 Valutazione Esercizi")
        
        # ID verifica
        id_verifica = st.text_input(
            "ID Verifica (lascia vuoto per auto-generare):",
            value=f"verifica_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        
        # Valutatore
        valutatore = st.text_input("Nome valutatore:", value="Docente")
        
        valutazioni_salvate = []
        
        for i, esercizio in enumerate(esercizi):
            with st.expander(f"Esercizio {esercizio['numero']}: {esercizio['titolo']}", expanded=True):
                # Mostra contenuto esercizio
                st.markdown("**Contenuto:**")
                st.code(esercizio['contenuto'][:500] + "..." if len(esercizio['contenuto']) > 500 else esercizio['contenuto'], language='latex')
                
                col1, col2 = st.columns(2)
                
                with col1:
                    punteggio_assegnato = st.number_input(
                        f"Punteggio assegnato (max {esercizio['punteggio_massimo']} pt):",
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
                        "Feedback generale:",
                        ["Eccellente", "Buono", "Sufficiente", "Insufficiente", "Da migliorare"],
                        key=f"feedback_{i}"
                    )
                    
                    competenze = st.multiselect(
                        "Competenze valutate:",
                        ["Comprensione", "Applicazione", "Analisi", "Sintesi", "Valutazione", "Creatività"],
                        key=f"competenze_{i}"
                    )
                
                commenti = st.text_area(
                    "Commenti specifici:",
                    key=f"commenti_{i}",
                    placeholder="Inserisci commenti dettagliati su questo esercizio..."
                )
                
                # Salva valutazione per questo esercizio
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
        
        # Pulsante salva tutto
        if st.button("💾 Salva tutte le valutazioni", type="primary"):
            salvati = 0
            for val in valutazioni_salvate:
                if salva_valutazione(val):
                    salvati += 1
            
            if salvati > 0:
                st.success(f"✅ Salvate {salvati} valutazioni!")
            else:
                st.error("❌ Errore nel salvataggio")

def render_valutazioni_salvate():
    """Mostra le valutazioni salvate"""
    st.header("📚 Valutazioni Salvate")
    
    # Filtri
    col1, col2 = st.columns(2)
    with col1:
        materia_filter = st.selectbox("Filtra per materia:", ["Tutte"] + list(set(v['materia'] for v in carica_valutazioni())))
    with col2:
        argomento_filter = st.selectbox("Filtra per argomento:", ["Tutti"] + list(set(v['argomento'] for v in carica_valutazioni())))
    
    # Carica valutazioni con filtri
    valutazioni = carica_valutazioni(
        materia=materia_filter if materia_filter != "Tutte" else None,
        argomento=argomento_filter if argomento_filter != "Tutti" else None
    )
    
    if not valutazioni:
        st.info("Nessuna valutazione trovata")
        return
    
    st.info(f"📊 Trovate {len(valutazioni)} valutazioni")
    
    # Mostra valutazioni
    for val in valutazioni:
        with st.expander(f"{val['materia']} - {val['argomento']} - Esercizio {val['numero_esercizio']}", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"**Esercizio:** {val['titolo_esercizio']}")
                st.markdown(f"**Punteggio:** {val['punteggio_assegnato']}/{val['punteggio_massimo']} pt")
                st.markdown(f"**Feedback:** {val['feedback']}")
                st.markdown(f"**Difficoltà:** {val['tag_difficolta']}")
            
            with col2:
                st.markdown(f"**Valutatore:** {val['valutatore']}")
                st.markdown(f"**Data:** {val['data_valutazione'][:10]}")
                st.markdown(f"**Competenze:** {val['tag_competenze']}")
            
            if val['commenti']:
                st.markdown("**Commenti:**")
                st.write(val['commenti'])
            
            # Mostra contenuto esercizio
            with st.expander("📄 Mostra contenuto esercizio"):
                st.code(val['contenuto_esercizio'], language='latex')

def render_statistiche():
    """Mostra statistiche delle valutazioni"""
    st.header("📊 Statistiche Valutazioni")
    
    statistiche = get_statistiche_materia_argomento()
    
    if not statistiche:
        st.info("Nessuna statistica disponibile")
        return
    
    # Tabella statistiche
    st.subheader("📈 Media punteggi per materia-argomento")
    
    for chiave, stats in statistiche.items():
        with st.expander(f"{chiave}", expanded=False):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Media punteggi", f"{stats['media_punteggi']}/10")
            
            with col2:
                st.metric("Numero esercizi", stats['numero_esercizi'])
            
            with col3:
                st.metric("Ultimo aggiornamento", stats['ultimo_aggiornamento'][:10])
            
            # Grafico andamento (placeholder)
            st.write("📊 Grafico andamento (in sviluppo)")

def render_ricerca_avanzata():
    """Ricerca avanzata nelle valutazioni"""
    st.header("🔍 Ricerca Avanzata")
    
    # Campi ricerca
    col1, col2 = st.columns(2)
    
    with col1:
        search_materia = st.text_input("Cerca materia:")
        search_argomento = st.text_input("Cerca argomento:")
        search_titolo = st.text_input("Cerca nel titolo esercizio:")
    
    with col2:
        min_punteggio = st.number_input("Punteggio minimo:", 0.0, 10.0, 0.0)
        max_punteggio = st.number_input("Punteggio massimo:", 0.0, 10.0, 10.0)
        search_feedback = st.selectbox("Feedback:", ["Tutti", "Eccellente", "Buono", "Sufficiente", "Insufficiente", "Da migliorare"])
    
    if st.button("🔍 Cerca"):
        # Implementa ricerca avanzata
        st.info("🔧 Funzione di ricerca avanzata in sviluppo")

if __name__ == "__main__":
    render_interfaccia_valutazione()
