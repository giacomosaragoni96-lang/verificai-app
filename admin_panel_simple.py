"""
Pannello Admin Semplice - Da copiare in main.py
"""

import streamlit as st
import json
import os
from datetime import datetime
from pathlib import Path

def render_simple_admin_panel():
    """Pannello admin semplice integrato"""
    
    st.set_page_config(page_title="Admin - VerificAI", layout="wide")
    
    # Header
    st.markdown("""
    <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                padding: 2rem; border-radius: 10px; margin-bottom: 2rem;'>
        <h1 style='color: white; margin: 0;'>🔧 Pannello Admin VerificAI</h1>
        <p style='color: white; margin: 0.5rem 0 0 0;'>Test Suite Management</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar navigazione
    with st.sidebar:
        st.markdown("### 📋 Navigazione")
        page = st.selectbox(
            "Seleziona sezione:",
            ["🎯 Dashboard", "🧪 Nuovo Test", "📊 Storico Test"]
        )
    
    if page == "🎯 Dashboard":
        render_admin_dashboard()
    elif page == "🧪 Nuovo Test":
        render_new_test()
    elif page == "📊 Storico Test":
        render_test_history()

def render_admin_dashboard():
    """Dashboard admin"""
    st.markdown("## 🎯 Dashboard Test Suite")
    
    # Metriche
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📝 Test Totali", "0")
    with col2:
        st.metric("📊 Risultati", "0")
    with col3:
        st.metric("📈 Success Rate", "N/A")
    with col4:
        st.metric("⏰ Ultimo Test", "Nessuno")
    
    st.info("🚀 Sistema test pronto. Genera nuovi test dalla sezione '🧪 Nuovo Test'")

def render_new_test():
    """Generazione nuovo test"""
    st.markdown("## 🧪 Genera Nuovo Test")
    
    with st.form("new_test_form"):
        st.markdown("### 📋 Configurazione Test")
        
        col1, col2 = st.columns(2)
        
        with col1:
            materia = st.selectbox("Materia", ["Matematica", "Italiano", "Fisica"])
            livello = st.selectbox("Livello", ["Liceo Scientifico", "Istituto Tecnico"])
            argomento = st.text_input("Argomento", "Equazioni di secondo grado")
        
        with col2:
            num_esercizi = st.number_input("Numero Esercizi", 1, 10, 4)
            punti_totali = st.number_input("Punti Totali", 10, 200, 80, 10)
            durata = st.text_input("Durata", "50 minuti")
        
        submitted = st.form_submit_button("🚀 Genera Test", type="primary")
        
        if submitted:
            st.success("✅ Test configurato!")
            st.info("📝 Sistema di generazione test in fase di sviluppo")

def render_test_history():
    """Storico test"""
    st.markdown("## 📊 Storico Test")
    
    st.info("📂 Nessun test trovato. Genera nuovi test dalla sezione '🧪 Nuovo Test'.")

# Funzione principale da chiamare in main.py
def render_admin_page():
    """Renderizza pannello admin - versione semplice"""
    render_simple_admin_panel()
