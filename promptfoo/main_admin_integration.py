"""
CODICE DA AGGIUNGERE A main.py PER INTEGRAZIONE PANNELLO ADMIN
"""

# 1. AGGIUNGI QUESTO IMPORT IN CIMA AL FILE
# ===============================================================================
from promptfoo.admin_test_panel import render_admin_page
# ===============================================================================


# 2. AGGIUNGI QUESTO CODICE DOPO GLI IMPORT PRINCIPALI
# ===============================================================================
# Inizializza session state per admin
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'home'
# ===============================================================================


# 3. AGGIUNGI QUESTO CODICE NELLA SIDEBAR (dopo il tuo menu esistente)
# ===============================================================================
# Menu Admin - aggiungi dopo il tuo menu esistente nella sidebar
st.sidebar.markdown("---")

# Sezione Admin
if st.session_state.is_admin:
    st.sidebar.markdown("### 🔧 Amministrazione")
    
    if st.sidebar.button("🔧 Pannello Admin Test Suite", key="admin_panel_btn"):
        st.session_state.current_page = 'admin'
        st.rerun()
    
    if st.sidebar.button("🚪 Logout Admin", key="admin_logout"):
        st.session_state.is_admin = False
        st.session_state.current_page = 'home'
        st.success("✅ Logout effettuato")
        st.rerun()
else:
    st.sidebar.markdown("### 🔐 Accesso Admin")
    
    with st.sidebar.expander("Login Admin"):
        password = st.text_input("Password:", type="password", key="admin_password")
        
        if st.button("🔐 Login", key="admin_login_btn"):
            if password == "admin123":  # In produzione usa sistema più sicuro
                st.session_state.is_admin = True
                st.success("✅ Accesso admin abilitato!")
                st.rerun()
            elif password:
                st.error("❌ Password errata!")
        
        st.caption("Password di test: admin123")
# ===============================================================================


# 4. AGGIUNGI QUESTO CODICE ALLA LOGICA DELLE PAGINE (prima del tuo codice esistente)
# ===============================================================================
# Gestione pagina Admin
if st.session_state.current_page == 'admin':
    if st.session_state.is_admin:
        render_admin_page()
    else:
        st.error("⛔ Accesso negato. Privilegi admin richiesti.")
        st.session_state.current_page = 'home'
        st.rerun()
else:
    # IL TUO CODICE ESISTENTE VA QUI SOTTO
    # Mantieni la tua logica esistente per le altre pagine
    pass
# ===============================================================================


# 5. ESEMPIO COMPLETO - SOSTITUISCI LA TUA LOGICA DI NAVIGAZIONE ESISTENTE
# ===============================================================================
# Esempio di come integrare con la tua logica esistente

# La tua funzione main() o logica principale potrebbe assomigliare a questo:

def main_with_admin():
    """Esempio di main() con admin integrato"""
    
    # Tuo codice esistente...
    st.set_page_config(page_title="VerificAI", layout="wide")
    
    # Session state (se non l'hai già)
    if 'is_admin' not in st.session_state:
        st.session_state.is_admin = False
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 'home'
    
    # La tua sidebar esistente + menu admin
    with st.sidebar:
        st.markdown("### 🎯 VerificAI")
        
        # Il tuo menu esistente
        page = st.selectbox(
            "Navigazione:",
            ["🏠 Home", "📝 Genera Verifica", "📚 I Miei Documenti", "⚙️ Impostazioni"]
        )
        
        # Menu admin (aggiunto)
        st.sidebar.markdown("---")
        
        if st.session_state.is_admin:
            st.sidebar.markdown("### 🔧 Amministrazione")
            if st.sidebar.button("🔧 Pannello Admin Test Suite"):
                st.session_state.current_page = 'admin'
                st.rerun()
            
            if st.sidebar.button("🚪 Logout Admin"):
                st.session_state.is_admin = False
                st.session_state.current_page = 'home'
                st.rerun()
        else:
            st.sidebar.markdown("### 🔐 Accesso Admin")
            password = st.sidebar.text_input("Password:", type="password")
            if st.sidebar.button("🔐 Login"):
                if password == "admin123":
                    st.session_state.is_admin = True
                    st.success("✅ Accesso admin!")
                    st.rerun()
                else:
                    st.sidebar.error("❌ Password errata!")
    
    # Logica pagine
    if st.session_state.current_page == 'admin':
        render_admin_page()
    else:
        # Il tuo codice esistente per le pagine normali
        if page == "🏠 Home":
            st.title("🏠 Benvenuto in VerificAI")
            # ... tuo codice home ...
            
        elif page == "📝 Genera Verifica":
            st.title("📝 Genera Nuova Verifica")
            # ... tuo codice generazione ...
            
        elif page == "📚 I Miei Documenti":
            st.title("📚 I Miei Documenti")
            # ... tuo codice documenti ...
            
        elif page == "⚙️ Impostazioni":
            st.title("⚙️ Impostazioni")
            # ... tuo codice impostazioni ...

# Se hai già una funzione main(), aggiungi solo le parti necessarie
# ===============================================================================

# ISTRUZIONI FINALI:
# 1. Copia l'import in cima al file
# 2. Aggiungi il codice session state dopo gli import
# 3. Aggiungi il menu admin nella sidebar
# 4. Aggiungi la logica pagina admin prima del tuo codice esistente
# 5. Testa con: streamlit run main.py
# 6. Accedi con password: admin123
