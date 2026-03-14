# VERSIONE EMERGENZA - main.py minimo funzionante

import streamlit as st
import pandas as pd
from datetime import datetime

# Configurazione pagina
st.set_page_config(
    page_title="VerificAI",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Stili CSS
st.markdown("""
<style>
.main-header {
    text-align: center;
    padding: 3rem 0;
    background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
    border-radius: 16px;
    margin-bottom: 2rem;
}
.feature-card {
    background: white;
    border: 2px solid #e5e7eb;
    border-radius: 12px;
    padding: 2rem;
    text-align: center;
    transition: all 0.3s ease;
}
.feature-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
}
.cta-button {
    background: linear-gradient(135deg, #3b82f6, #1d4ed8);
    color: white;
    border: none;
    padding: 1rem 2rem;
    border-radius: 8px;
    font-weight: 600;
    font-size: 1.1rem;
    transition: all 0.3s ease;
}
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.title("📚 VerificAI")
    st.markdown("---")
    
    # Stats utente
    st.markdown("### Utilizzo mensile")
    verifiche_mese = 3
    limite_mensile = 10
    perc_uso = (verifiche_mese / limite_mensile) * 100
    
    st.progress(perc_uso / 100)
    st.write(f"{verifiche_mese} / {limite_mensile} verifiche")
    
    st.markdown("---")
    
    # Navigazione
    if st.button("📄 Le Tue Verifiche", key="storico_btn", use_container_width=True):
        st.session_state.page = "storico"
        st.rerun()
    
    if st.button("⚙️ Impostazioni", key="settings_btn", use_container_width=True):
        st.session_state.page = "settings"
        st.rerun()

# Main content
def show_landing():
    st.markdown("""
    <div class="main-header">
        <h1 style="font-size: 3rem; font-weight: 800; color: #1f2937; margin-bottom: 1rem;">
            📚 VerificAI
        </h1>
        <p style="font-size: 1.3rem; color: #6b7280; max-width: 600px; margin: 0 auto;">
            Genera verifiche scolastiche personalizzate con AI. 
            Crea esercizi su misura per le tue lezioni in pochi secondi.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Feature cards
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="feature-card">
            <h3 style="color: #3b82f6; font-size: 1.5rem; margin-bottom: 1rem;">
                🎯 Personalizzazione
            </h3>
            <p style="color: #6b7280;">
                Adatta difficoltà, argomenti e tipologia di esercizi 
                alle esigenze specifiche della tua classe.
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="feature-card">
            <h3 style="color: #10b981; font-size: 1.5rem; margin-bottom: 1rem;">
                ⚡ Generazione Veloce
            </h3>
            <p style="color: #6b7280;">
                Ottieni verifiche complete con soluzioni in pochi secondi, 
                non ore di lavoro.
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="feature-card">
            <h3 style="color: #f59e0b; font-size: 1.5rem; margin-bottom: 1rem;">
                📄 Formati Multipli
            </h3>
            <p style="color: #6b7280;">
                Esporta in PDF, Word o LaTeX. 
                Modifica e adatta come preferisci.
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    # CTA section
    st.markdown("---")
    
    col_center = st.columns([1, 2, 1])
    with col_center[1]:
        st.markdown("""
        <div style="text-align: center; padding: 2rem;">
            <h2 style="color: #1f2937; margin-bottom: 1.5rem;">
                Pronto a creare la tua prima verifica?
            </h2>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🚀 Inizia Subito", type="primary", use_container_width=True):
            st.success("Funzionalità in arrivo! 🚀")
    
    # Stats section
    st.markdown("---")
    st.markdown("### 📊 VerificAI in numeri")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Verifiche Create", "1,234")
    with col2:
        st.metric("Docenti Attivi", "567")
    with col3:
        st.metric("Esercizi Generati", "12,345")
    with col4:
        st.metric("Scuole Coperte", "89")

def show_storico():
    st.title("📄 Le Tue Verifiche")
    st.info("Funzionalità storico in sviluppo...")
    
    if st.button("← Torna alla Home", key="back_to_home"):
        st.session_state.page = "landing"
        st.rerun()

# Page routing
if "page" not in st.session_state:
    st.session_state.page = "landing"

if st.session_state.page == "storico":
    show_storico()
elif st.session_state.page == "settings":
    st.title("⚙️ Impostazioni")
    st.info("Impostazioni in sviluppo...")
    if st.button("← Torna alla Home", key="back_to_home2"):
        st.session_state.page = "landing"
        st.rerun()
else:
    show_landing()
