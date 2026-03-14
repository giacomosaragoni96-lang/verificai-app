"""
Esempio di come integrare il pannello admin in main.py
"""

import streamlit as st

# 1. Importa il pannello admin
from promptfoo.admin_test_panel import render_admin_page

def main():
    # ... tuo codice esistente main.py ...
    
    # 2. Aggiungi controllo admin nella sidebar
    with st.sidebar:
        st.markdown("---")
        
        # Menu admin (solo per admin)
        if st.session_state.get('is_admin', False):
            if st.button("🔧 Pannello Admin", key="admin_panel_btn"):
                st.session_state.current_page = 'admin'
                st.rerun()
        else:
            # Login admin (semplice per test)
            if st.button("🔐 Login Admin", key="admin_login"):
                # Per test: password semplice "admin123"
                password = st.text_input("Password Admin:", type="password", key="admin_password")
                if password == "admin123":
                    st.session_state.is_admin = True
                    st.success("✅ Accesso admin abilitato!")
                    st.rerun()
                elif password:
                    st.error("❌ Password errata!")
    
    # 3. Logica di navigazione pagine
    current_page = st.session_state.get('current_page', 'home')
    
    if current_page == 'admin':
        # Mostra pannello admin solo se admin
        if st.session_state.get('is_admin', False):
            render_admin_page()
        else:
            st.error("⛔ Accesso negato. Privilegi admin richiesti.")
            st.session_state.current_page = 'home'
            st.rerun()
    else:
        # ... tuo codice esistente per altre pagine ...
        pass

# Esempio completo minimalista:
def admin_integration_example():
    """Esempio completo di integrazione"""
    
    st.set_page_config(page_title="VerificAI", layout="wide")
    
    # Session state
    if 'is_admin' not in st.session_state:
        st.session_state.is_admin = False
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 'home'
    
    # Sidebar con menu admin
    with st.sidebar:
        st.markdown("### 🎯 VerificAI")
        
        # Menu normale
        page = st.selectbox(
            "Navigazione:",
            ["🏠 Home", "📝 Genera Verifica", "📚 I Miei Documenti", "⚙️ Impostazioni"]
        )
        
        st.markdown("---")
        
        # Sezione admin
        if st.session_state.is_admin:
            st.markdown("### 🔧 Amministrazione")
            if st.button("🔧 Pannello Admin Test Suite"):
                st.session_state.current_page = 'admin'
                st.rerun()
            
            if st.button("🚪 Logout Admin"):
                st.session_state.is_admin = False
                st.session_state.current_page = 'home'
                st.rerun()
        else:
            st.markdown("### 🔐 Accesso Admin")
            password = st.text_input("Password:", type="password")
            if st.button("Login"):
                if password == "admin123":  # In produzione usa sistema sicuro
                    st.session_state.is_admin = True
                    st.success("✅ Accesso admin abilitato!")
                    st.rerun()
                else:
                    st.error("❌ Password errata!")
    
    # Logica pagine
    if st.session_state.current_page == 'admin':
        render_admin_page()
    else:
        # Tuo codice normale app
        if page == "🏠 Home":
            st.title("🏠 Benvenuto in VerificAI")
            st.write("App per generazione verifiche scolastiche")
            
        elif page == "📝 Genera Verifica":
            st.title("📝 Genera Nuova Verifica")
            # ... tuo codice generazione ...
            
        elif page == "📚 I Miei Documenti":
            st.title("📚 I Miei Documenti")
            # ... tuo codice documenti ...
            
        elif page == "⚙️ Impostazioni":
            st.title("⚙️ Impostazioni")
            # ... tuo codice impostazioni ...

if __name__ == "__main__":
    admin_integration_example()
