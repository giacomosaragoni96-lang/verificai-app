"""
Sistema Admin Test & Valutazione - VerificAI
Tool completo per test di 30 verifiche e valutazione esercizi
Accessibile solo agli amministratori
"""

import streamlit as st
import sqlite3
import json
import random
from datetime import datetime
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import List, Dict, Any

# Configurazione database
DB_PATH = "admin_valutazioni.db"
TEST_DB_PATH = "test_results.db"

# Admin emails
ADMIN_EMAILS = ["admin@verificai.ai", "g.saragoni96@gmail.com"]

# Stile CSS
CSS_STYLE = """
<style>
.admin-header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 2rem;
    border-radius: 16px;
    margin-bottom: 2rem;
    text-align: center;
}
.test-card {
    background: #f8f9fa;
    border: 1px solid #dee2e6;
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 1rem;
}
.test-card.pass {
    border-left: 4px solid #28a745;
}
.test-card.fail {
    border-left: 4px solid #dc3545;
}
.valutazione-card {
    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 1rem;
}
.metric-card {
    background: white;
    border-radius: 8px;
    padding: 1rem;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    text-align: center;
}
</style>
"""

def check_admin_access():
    """Verifica se l'utente è admin"""
    if not st.session_state.get('utente'):
        st.error("⛔ Accesso negato. Effettua il login come amministratore.")
        st.stop()
    
    user_email = st.session_state.utente.email
    if user_email not in ADMIN_EMAILS:
        st.error("⛔ Accesso negato. Privilegi amministrativi richiesti.")
        st.stop()
    
    return True

def init_databases():
    """Inizializza i database necessari"""
    
    # Database valutazioni esercizi approvati
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS esercizi_approvati (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            materia TEXT,
            argomento TEXT,
            livello TEXT,
            titolo_esercizio TEXT,
            contenuto_esercizio TEXT,
            punteggio_massimo REAL,
            id_verifica TEXT,
            data_approvazione TEXT,
            valutatore TEXT,
            numero_usi INTEGER DEFAULT 0,
            UNIQUE(materia, argomento, titolo_esercizio, contenuto_esercizio)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS verifiche_approvate (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_verifica TEXT,
            materia TEXT,
            argomento TEXT,
            livello TEXT,
            titolo_verifica TEXT,
            contenuto_completo TEXT,
            numero_esercizi INTEGER,
            data_approvazione TEXT,
            valutatore TEXT,
            UNIQUE(id_verifica)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS statistiche_approvati (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            materia TEXT,
            argomento TEXT,
            livello TEXT,
            totale_esercizi INTEGER,
            totale_verifiche INTEGER,
            ultimo_aggiornamento TEXT,
            UNIQUE(materia, argomento, livello)
        )
    ''')
    
    conn.commit()
    conn.close()
    
    # Database test results
    conn = sqlite3.connect(TEST_DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS test_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            test_session_id TEXT,
            materia TEXT,
            argomento TEXT,
            livello TEXT,
            id_verifica TEXT,
            esito_test TEXT,  # 'PASS', 'FAIL', 'PARTIAL'
            punteggio_test REAL,
            dettagli_test TEXT,
            data_test TEXT,
            UNIQUE(test_session_id, id_verifica)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS test_sessions (
            id TEXT PRIMARY KEY,
            data_sessione TEXT,
        totale_verifiche INTEGER,
        pass_count INTEGER,
        fail_count INTEGER,
        partial_count INTEGER,
        punteggio_medio REAL
        )
    ''')
    
    conn.commit()
    conn.close()

def render_admin_header():
    """Header admin"""
    st.markdown(CSS_STYLE, unsafe_allow_html=True)
    st.markdown("""
    <div class="admin-header">
        <h1>🔧 Admin Test & Valutazione System</h1>
        <p>Sistema completo per test di verifiche e valutazione esercizi</p>
    </div>
    """, unsafe_allow_html=True)

def render_dashboard():
    """Dashboard principale"""
    render_admin_header()
    
    # Sidebar navigation
    with st.sidebar:
        st.title("🧭 Navigazione")
        page = st.selectbox(
            "Scegli pagina:",
            ["🏠 Dashboard", "🧪 Lancia Test", "📋 Risultati Test", "✅ Valutazione Esercizi", "📊 Statistiche", "🗄️ Database Approvati"]
        )
    
    # Renderizza pagina selezionata
    if page == "🏠 Dashboard":
        render_dashboard_overview()
    elif page == "🧪 Lancia Test":
        render_lancia_test()
    elif page == "📋 Risultati Test":
        render_risultati_test()
    elif page == "✅ Valutazione Esercizi":
        render_valutazione_esercizi()
    elif page == "📊 Statistiche":
        render_statistiche()
    elif page == "🗄️ Database Approvati":
        render_database_approvati()

def render_dashboard_overview():
    """Panoramica dashboard"""
    st.title("📊 Panoramica Sistema")
    
    # Metriche principali
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        esercizi_approvati = get_count_esercizi_approvati()
        st.metric("📝 Esercizi Approvati", esercizi_approvati)
    
    with col2:
        verifiche_approvate = get_count_verifiche_approvate()
        st.metric("📋 Verifiche Approvate", verifiche_approvate)
    
    with col3:
        test_totali = get_count_test_totali()
        st.metric("🧪 Test Totali", test_totali)
    
    with col4:
        quality_rate = get_quality_rate()
        st.metric("📈 Quality Rate", f"{quality_rate:.1f}%")
    
    # Grafici recenti
    col1, col2 = st.columns(2)
    
    with col1:
        render_andamento_approvazioni()
    
    with col2:
        render_distribuzione_materie()
    
    # Azioni rapide
    st.markdown("---")
    st.subheader("🚀 Azioni Rapide")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🧪 Lancia Nuovo Test", type="primary", use_container_width=True):
            st.session_state.current_page = "🧪 Lancia Test"
            st.rerun()
    
    with col2:
        if st.button("✅ Valuta Esercizi", use_container_width=True):
            st.session_state.current_page = "✅ Valutazione Esercizi"
            st.rerun()
    
    with col3:
        if st.button("📊 Vedi Statistiche", use_container_width=True):
            st.session_state.current_page = "📊 Statistiche"
            st.rerun()

def render_lancia_test():
    """Pagina per lanciare test su 30 verifiche"""
    st.title("🧪 Lancia Test su 30 Verifiche")
    
    # Configurazione test
    with st.expander("⚙️ Configurazione Test", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            materia = st.selectbox(
                "Materia:",
                ["Matematica", "Fisica", "Chimica", "Italiano", "Storia", "Inglese", "Informatica"],
                key="test_materia"
            )
            
            argomento = st.text_input(
                "Argomento:",
                value="Trigonometria",
                key="test_argomento"
            )
        
        with col2:
            livello = st.selectbox(
                "Livello:",
                ["Scuola Media", "Liceo", "Istituto Tecnico"],
                key="test_livello"
            )
            
            num_esercizi = st.number_input(
                "Esercizi per verifica:",
                min_value=1,
                max_value=10,
                value=3,
                key="test_num_esercizi"
            )
        
        punti_totali = st.number_input(
            "Punti totali:",
            min_value=10,
            max_value=100,
            value=30,
            key="test_punti"
        )
    
    # Generazione parametri
    if st.button("🚀 Genera 30 Verifiche di Test", type="primary", use_container_width=True):
        with st.spinner("Generazione 30 verifiche in corso..."):
            # Genera 30 set di parametri casuali
            test_params = []
            for i in range(30):
                params = {
                    'materia': materia,
                    'argomento': argomento,
                    'difficolta': livello,
                    'num_esercizi': num_esercizi,
                    'punti_totali': punti_totali,
                    'test_id': f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{i+1:02d}"
                }
                test_params.append(params)
            
            st.session_state.test_params = test_params
            st.session_state.test_session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            st.success(f"✅ Generati {len(test_params)} test pronti per l'esecuzione!")
    
    # Esecuzione test
    if 'test_params' in st.session_state and st.session_state.test_params:
        st.markdown("---")
        st.subheader("🎯 Esecuzione Test")
        
        if st.button("▶️ Esegui Tutti i Test", type="primary", use_container_width=True):
            execute_all_tests()
    
    # Risultati test
    if 'test_results' in st.session_state:
        render_test_results_summary()

def execute_all_tests():
    """Esegue tutti i test configurati"""
    test_params = st.session_state.test_params
    session_id = st.session_state.test_session_id
    
    with st.spinner("Esecuzione test in corso..."):
        results = []
        pass_count = 0
        fail_count = 0
        partial_count = 0
        total_score = 0
        
        for i, params in enumerate(test_params):
            # Simula esecuzione test (sostituire con logica reale)
            result = simulate_test_execution(params)
            results.append(result)
            
            # Aggiorna contatori
            if result['esito'] == 'PASS':
                pass_count += 1
            elif result['esito'] == 'FAIL':
                fail_count += 1
            else:
                partial_count += 1
            
            total_score += result['punteggio']
            
            # Progress bar
            progress = (i + 1) / len(test_params)
            st.progress(progress, f"Test {i+1}/{len(test_params)} - {result['esito']}")
        
        # Salva risultati nel database
        save_test_session(session_id, results, pass_count, fail_count, partial_count, total_score/len(results))
        
        st.session_state.test_results = results
        st.success(f"✅ Completati {len(results)} test! PASS: {pass_count}, FAIL: {fail_count}, PARTIAL: {partial_count}")

def simulate_test_execution(params):
    """Simula l'esecuzione di un test (sostituire con logica reale)"""
    import random
    
    # Simula esito test basato su parametri
    base_success = 0.7  # 70% base success rate
    
    # Aggiungi variazione basata su complessità
    if params['materia'] == 'Matematica':
        base_success -= 0.1
    elif params['materia'] == 'Italiano':
        base_success += 0.1
    
    # Random factor
    success_prob = base_success + random.uniform(-0.2, 0.2)
    success_prob = max(0, min(1, success_prob))
    
    if random.random() < success_prob:
        esito = 'PASS'
        score = random.uniform(8, 10)
    elif random.random() < 0.3:
        esito = 'PARTIAL'
        score = random.uniform(6, 8)
    else:
        esito = 'FAIL'
        score = random.uniform(0, 6)
    
    return {
        'test_id': params['test_id'],
        'materia': params['materia'],
        'argomento': params['argomento'],
        'livello': params['difficolta'],
        'esito': esito,
        'punteggio': score,
        'dettagli': f"Test eseguito con successo. Score: {score:.1f}/10"
    }

def save_test_session(session_id, results, pass_count, fail_count, partial_count, avg_score):
    """Salva i risultati della sessione di test"""
    conn = sqlite3.connect(TEST_DB_PATH)
    cursor = conn.cursor()
    
    # Salva sessione
    cursor.execute('''
        INSERT OR REPLACE INTO test_sessions 
        (id, data_sessione, totale_verifiche, pass_count, fail_count, partial_count, punteggio_medio)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (session_id, datetime.now().isoformat(), len(results), pass_count, fail_count, partial_count, avg_score))
    
    # Salva risultati individuali
    for result in results:
        cursor.execute('''
            INSERT OR REPLACE INTO test_results 
            (test_session_id, materia, argomento, livello, id_verifica, esito_test, punteggio_test, dettagli_test, data_test)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            session_id,
            result['materia'],
            result['argomento'],
            result['livello'],
            result['test_id'],
            result['esito'],
            result['punteggio'],
            result['dettagli'],
            datetime.now().isoformat()
        ))
    
    conn.commit()
    conn.close()

def render_test_results_summary():
    """Riepilogo risultati test"""
    results = st.session_state.test_results
    
    st.markdown("---")
    st.subheader("📊 Riepilogo Risultati Test")
    
    # Statistiche
    pass_count = sum(1 for r in results if r['esito'] == 'PASS')
    fail_count = sum(1 for r in results if r['esito'] == 'FAIL')
    partial_count = sum(1 for r in results if r['esito'] == 'PARTIAL')
    avg_score = sum(r['punteggio'] for r in results) / len(results)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("✅ PASS", pass_count, delta=f"{pass_count/len(results)*100:.1f}%")
    with col2:
        st.metric("❌ FAIL", fail_count, delta=f"{fail_count/len(results)*100:.1f}%")
    with col3:
        st.metric("⚠️ PARTIAL", partial_count, delta=f"{partial_count/len(results)*100:.1f}%")
    with col4:
        st.metric("📈 Score Medio", f"{avg_score:.2f}")
    
    # Grafico distribuzione
    fig = px.pie(
        values=[pass_count, fail_count, partial_count],
        names=['PASS', 'FAIL', 'PARTIAL'],
        title='Distribuzione Risultati Test'
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Lista risultati dettagliati
    st.markdown("---")
    st.subheader("📋 Risultati Dettagliati")
    
    for result in results:
        card_class = "test-card pass" if result['esito'] == 'PASS' else "test-card fail" if result['esito'] == 'FAIL' else "test-card"
        
        st.markdown(f"""
        <div class="{card_class}">
            <h4>{result['test_id']} - {result['esito']}</h4>
            <p><strong>Materia:</strong> {result['materia']} | <strong>Argomento:</strong> {result['argomento']} | <strong>Livello:</strong> {result['livello']}</p>
            <p><strong>Score:</strong> {result['punteggio']:.2f}/10</p>
            <p><strong>Dettagli:</strong> {result['dettagli']}</p>
        </div>
        """, unsafe_allow_html=True)

def render_risultati_test():
    """Pagina risultati test"""
    st.title("📋 Risultati Test")
    
    # Carica tutte le sessioni di test
    conn = sqlite3.connect(TEST_DB_PATH)
    sessions_df = pd.read_sql_query("SELECT * FROM test_sessions ORDER BY data_sessione DESC", conn)
    conn.close()
    
    if sessions_df.empty:
        st.info("📝 Nessuna sessione di test trovata. Lancia un nuovo test per vedere i risultati.")
        return
    
    # Selettore sessione
    session_options = [f"{row['id']} - {row['data_sessione']} (Score: {row['punteggio_medio']:.2f})" for _, row in sessions_df.iterrows()]
    selected_session = st.selectbox("Seleziona sessione:", session_options)
    
    if selected_session:
        session_id = selected_session.split(" - ")[0]
        
        # Carica risultati della sessione
        conn = sqlite3.connect(TEST_DB_PATH)
        results_df = pd.read_sql_query(
            "SELECT * FROM test_results WHERE test_session_id = ? ORDER BY punteggio_test DESC", 
            conn, 
            params=(session_id,)
        )
        conn.close()
        
        # Dettagli sessione
        session_info = sessions_df[sessions_df['id'] == session_id].iloc[0]
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📅 Data", session_info['data_sessione'].split('T')[0])
        with col2:
            st.metric("📊 Score Medio", f"{session_info['punteggio_medio']:.2f}")
        with col3:
            st.metric("✅ PASS", session_info['pass_count'])
        with col4:
            st.metric("❌ FAIL", session_info['fail_count'])
        
        # Risultati dettagliati
        st.markdown("---")
        st.subheader("📋 Risultati Dettagliati")
        
        for _, result in results_df.iterrows():
            with st.expander(f"📝 {result['id_verifica']} - {result['esito_test']} ({result['punteggio_test']:.2f}/10)"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Materia:** {result['materia']}")
                    st.write(f"**Argomento:** {result['argomento']}")
                    st.write(f"**Livello:** {result['livello']}")
                
                with col2:
                    st.write(f"**Esito:** {result['esito_test']}")
                    st.write(f"**Punteggio:** {result['punteggio_test']:.2f}/10")
                    st.write(f"**Data:** {result['data_test']}")
                
                st.write(f"**Dettagli:** {result['dettagli_test']}")
                
                # Pulsante per valutare
                if st.button(f"✅ Valuta Questa Verifica", key=f"valuta_{result['id_verifica']}"):
                    st.session_state.verify_to_evaluate = result
                    st.session_state.current_page = "✅ Valutazione Esercizi"
                    st.rerun()

def render_valutazione_esercizi():
    """Pagina valutazione esercizi"""
    st.title("✅ Valutazione Esercizi")
    
    # Verifica se c'è una verifica da valutare
    if 'verify_to_evaluate' in st.session_state:
        verify_result = st.session_state.verify_to_evaluate
        render_single_verification_evaluation(verify_result)
    else:
        # Mostra elenco verifiche da valutare
        render_verification_list()

def render_single_verification_evaluation(verify_result):
    """Valutazione di una singola verifica"""
    st.markdown("---")
    st.subheader(f"📝 Valutazione Verifica: {verify_result['id_verifica']}")
    
    # Info verifica
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Materia", verify_result['materia'])
    with col2:
        st.metric("Argomento", verify_result['argomento'])
    with col3:
        st.metric("Livello", verify_result['livello'])
    with col4:
        st.metric("Score Test", f"{verify_result['punteggio_test']:.2f}")
    
    # Simula contenuto verifica (sostituire con logica reale)
    verifica_content = simulate_verification_content(verify_result)
    
    st.markdown("### 📄 Contenuto Verifica")
    st.code(verifica_content, language='latex')
    
    # Valutazione
    st.markdown("### 🎯 Valutazione")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Valutazione verifica intera
        approve_verify = st.radio(
            "Approva Verifica Intera:",
            ["✅ SI", "❌ NO"],
            key="approve_verify"
        )
        
        if approve_verify == "✅ SI":
            commenti_verify = st.text_area(
                "Commenti verifica:",
                key="commenti_verify",
                placeholder="Note sulla verifica..."
            )
    
    with col2:
        # Valutazione esercizi singoli
        st.markdown("**Valutazione Esercizi Singoli:**")
        
        # Simula 3 esercizi
        for i in range(3):
            exercise_approved = st.radio(
                f"Esercizio {i+1}:",
                ["✅ SI", "❌ NO"],
                key=f"exercise_{i}"
            )
    
    # Pulsanti azione
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("💾 Salva Valutazione", type="primary"):
            save_evaluation_result(verify_result, approve_verify == "✅ SI")
            st.success("✅ Valutazione salvata!")
            del st.session_state.verify_to_evaluate
            st.rerun()
    
    with col2:
        if st.button("⏭️ Prossima Verifica"):
            load_next_verification()
    
    with col3:
        if st.button("🔙 Torna Elenco"):
            del st.session_state.verify_to_evaluate
            st.rerun()

def simulate_verification_content(verify_result):
    """Simula il contenuto di una verifica"""
    return f"""
\\documentclass{{article}}
\\usepackage{{amsmath}}
\\begin{{document}}

\\title{{{verify_result['materia']} - {verify_result['argomento']}}}
\\author{{VerificAI}}
\\date{{\\today}}

\\maketitle

\\subsection*{{Esercizio 1: Definizioni (10 pt)}}
Spiega il concetto di {verify_result['argomento'].lower()} e fornisci un esempio pratico.

\\subsection*{{Esercizio 2: Problema Applicato (10 pt)}}
Risolvi il seguente problema relativo a {verify_result['argomento'].lower()}:
[Contenuto problema...]

\\subsection*{{Esercizio 3: Dimostrazione (10 pt)}}
Dimostra la proprietà fondamentale di {verify_result['argomento'].lower()}.

\\end{{document}}
"""

def save_evaluation_result(verify_result, approved):
    """Salva il risultato della valutazione"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if approved:
        # Salva come approvata
        cursor.execute('''
            INSERT OR REPLACE INTO verifiche_approvate 
            (id_verifica, materia, argomento, livello, titolo_verifica, contenuto_completo, numero_esercizi, data_approvazione, valutatore)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            verify_result['id_verifica'],
            verify_result['materia'],
            verify_result['argomento'],
            verify_result['livello'],
            f"Verifica {verify_result['materia']} - {verify_result['argomento']}",
            simulate_verification_content(verify_result),
            3,  # Numero esercizi
            datetime.now().isoformat(),
            st.session_state.utente.email if st.session_state.get('utente') else 'admin'
        ))
        
        # Salva anche esercizi singoli (approvati di default)
        for i in range(3):
            cursor.execute('''
                INSERT OR REPLACE INTO esercizi_approvati 
                (materia, argomento, livello, titolo_esercizio, contenuto_esercizio, punteggio_massimo, id_verifica, data_approvazione, valutatore)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                verify_result['materia'],
                verify_result['argomento'],
                verify_result['livello'],
                f"Esercizio {i+1}: {verify_result['argomento']}",
                f"Contenuto esercizio {i+1} su {verify_result['argomento']}",
                10.0,
                verify_result['id_verifica'],
                datetime.now().isoformat(),
                st.session_state.utente.email if st.session_state.get('utente') else 'admin'
            ))
        
        # Aggiorna statistiche
        update_statistics(verify_result['materia'], verify_result['argomento'], verify_result['livello'])
    
    conn.commit()
    conn.close()

def update_statistics(materia, argomento, livello):
    """Aggiorna le statistiche degli approvati"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Calcola statistiche attuali
    cursor.execute('''
        SELECT COUNT(*), COUNT(DISTINCT id_verifica) 
        FROM esercizi_approvati 
        WHERE materia = ? AND argomento = ? AND livello = ?
    ''', (materia, argomento, livello))
    
    totale_esercizi, totale_verifiche = cursor.fetchone()
    
    cursor.execute('''
        INSERT OR REPLACE INTO statistiche_approvati 
        (materia, argomento, livello, totale_esercizi, totale_verifiche, ultimo_aggiornamento)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (materia, argomento, livello, totale_esercizi, totale_verifiche, datetime.now().isoformat()))
    
    conn.commit()
    conn.close()

def render_verification_list():
    """Mostra elenco verifiche da valutare"""
    st.markdown("### 📋 Elenco Verifiche da Valutare")
    
    # Carizza risultati test recenti
    conn = sqlite3.connect(TEST_DB_PATH)
    results_df = pd.read_sql_query(
        "SELECT * FROM test_results WHERE esito_test != 'FAIL' ORDER BY punteggio_test DESC LIMIT 50", 
        conn
    )
    conn.close()
    
    if results_df.empty:
        st.info("📝 Nessuna verifica da valutare. Esegui prima un test.")
        return
    
    # Filtri
    col1, col2, col3 = st.columns(3)
    with col1:
        materia_filter = st.selectbox("Filtra Materia:", ["Tutte"] + list(results_df['materia'].unique()))
    with col2:
        argomento_filter = st.selectbox("Filtra Argomento:", ["Tutti"] + list(results_df['argomento'].unique()))
    with col3:
        livello_filter = st.selectbox("Filtra Livello:", ["Tutti"] + list(results_df['livello'].unique()))
    
    # Applica filtri
    filtered_df = results_df.copy()
    if materia_filter != "Tutte":
        filtered_df = filtered_df[filtered_df['materia'] == materia_filter]
    if argomento_filter != "Tutti":
        filtered_df = filtered_df[filtered_df['argomento'] == argomento_filter]
    if livello_filter != "Tutti":
        filtered_df = filtered_df[filtered_df['livello'] == livello_filter]
    
    # Lista verifiche
    for _, result in filtered_df.iterrows():
        with st.expander(f"📝 {result['id_verifica']} - {result['materia']} - {result['argomento']} ({result['punteggio_test']:.2f}/10)"):
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                st.write(f"**ID:** {result['id_verifica']}")
                st.write(f"**Materia:** {result['materia']}")
                st.write(f"**Argomento:** {result['argomento']}")
                st.write(f"**Livello:** {result['livello']}")
            
            with col2:
                st.metric("Score", f"{result['punteggio_test']:.2f}")
                st.write(f"**Esito:** {result['esito_test']}")
            
            with col3:
                if st.button("✅ Valuta", key=f"valuta_list_{result['id_verifica']}"):
                    st.session_state.verify_to_evaluate = result.to_dict()
                    st.session_state.current_page = "✅ Valutazione Esercizi"
                    st.rerun()

def load_next_verification():
    """Carica la prossima verifica da valutare"""
    conn = sqlite3.connect(TEST_DB_PATH)
    cursor = conn.cursor()
    
    # Trova prossima verifica non valutata
    cursor.execute('''
        SELECT * FROM test_results 
        WHERE esito_test != 'FAIL' 
        AND id_verifica NOT IN (SELECT id_verifica FROM verifiche_approvate)
        ORDER BY punteggio_test DESC 
        LIMIT 1
    ''')
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        columns = [desc[0] for desc in cursor.description]
        verify_dict = dict(zip(columns, result))
        st.session_state.verify_to_evaluate = verify_dict
        st.rerun()
    else:
        st.info("📝 Nessuna altra verifica da valutare.")

def render_statistiche():
    """Pagina statistiche"""
    st.title("📊 Statistiche Sistema")
    
    # Tabs per diverse statistiche
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Overview", "📝 Esercizi", "📋 Verifiche", "🧪 Test"])
    
    with tab1:
        render_statistiche_overview()
    
    with tab2:
        render_statistiche_esercizi()
    
    with tab3:
        render_statistiche_verifiche()
    
    with tab4:
        render_statistiche_test()

def render_statistiche_overview():
    """Statistiche overview"""
    st.subheader("📈 Panoramica Generale")
    
    # Metriche principali
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        esercizi = get_count_esercizi_approvati()
        st.metric("📝 Esercizi Approvati", esercizi)
    
    with col2:
        verifiche = get_count_verifiche_approvate()
        st.metric("📋 Verifiche Approvate", verifiche)
    
    with col3:
        quality_rate = get_quality_rate()
        st.metric("📈 Quality Rate", f"{quality_rate:.1f}%")
    
    with col4:
        test_totali = get_count_test_totali()
        st.metric("🧪 Test Eseguiti", test_totali)
    
    # Grafici
    col1, col2 = st.columns(2)
    
    with col1:
        render_andamento_approvazioni()
    
    with col2:
        render_distribuzione_materie()

def render_statistiche_esercizi():
    """Statistiche esercizi"""
    st.subheader("📝 Statistiche Esercizi Approvati")
    
    conn = sqlite3.connect(DB_PATH)
    
    # Distribuzione per materia
    materie_df = pd.read_sql_query("""
        SELECT materia, COUNT(*) as count 
        FROM esercizi_approvati 
        GROUP BY materia 
        ORDER BY count DESC
    """, conn)
    
    if not materie_df.empty:
        fig = px.bar(materie_df, x='materia', y='count', title='Esercizi per Materia')
        st.plotly_chart(fig, use_container_width=True)
    
    # Distribuzione per argomento
    argomenti_df = pd.read_sql_query("""
        SELECT argomento, COUNT(*) as count 
        FROM esercizi_approvati 
        GROUP BY argomento 
        ORDER BY count DESC 
        LIMIT 10
    """, conn)
    
    if not argomenti_df.empty:
        fig = px.bar(argomenti_df, x='argomento', y='count', title='Top 10 Argomenti')
        st.plotly_chart(fig, use_container_width=True)
    
    conn.close()

def render_statistiche_verifiche():
    """Statistiche verifiche"""
    st.subheader("📋 Statistiche Verifiche Approvate")
    
    conn = sqlite3.connect(DB_PATH)
    
    # Andamento approvazioni nel tempo
    verifiche_df = pd.read_sql_query("""
        SELECT DATE(data_approvazione) as date, COUNT(*) as count 
        FROM verifiche_approvate 
        GROUP BY DATE(data_approvazione) 
        ORDER BY date
    """, conn)
    
    if not verifiche_df.empty:
        fig = px.line(verifiche_df, x='date', y='count', title='Approvazioni Giornaliere')
        st.plotly_chart(fig, use_container_width=True)
    
    conn.close()

def render_statistiche_test():
    """Statistiche test"""
    st.subheader("🧪 Statistiche Test")
    
    conn = sqlite3.connect(TEST_DB_PATH)
    
    # Sessioni test
    sessions_df = pd.read_sql_query("""
        SELECT * FROM test_sessions 
        ORDER BY data_sessione DESC 
        LIMIT 20
    """, conn)
    
    if not sessions_df.empty:
        # Andamento score medio
        fig = px.line(sessions_df, x='data_sessione', y='punteggio_medio', title='Score Medio Test nel Tempo')
        st.plotly_chart(fig, use_container_width=True)
        
        # Distribuzione esiti
        esiti_df = pd.DataFrame({
            'Esito': ['PASS', 'FAIL', 'PARTIAL'],
            'Count': [sessions_df['pass_count'].sum(), sessions_df['fail_count'].sum(), sessions_df['partial_count'].sum()]
        })
        
        fig = px.pie(esiti_df, values='Count', names='Esito', title='Distribuzione Esiti Test')
        st.plotly_chart(fig, use_container_width=True)
    
    conn.close()

def render_database_approvati():
    """Database degli approvati"""
    st.title("🗄️ Database Esercizi Approvati")
    
    # Tabs
    tab1, tab2 = st.tabs(["📝 Esercizi", "📋 Verifiche"])
    
    with tab1:
        render_database_esercizi()
    
    with tab2:
        render_database_verifiche()

def render_database_esercizi():
    """Database esercizi"""
    st.subheader("📝 Esercizi Approvati")
    
    conn = sqlite3.connect(DB_PATH)
    esercizi_df = pd.read_sql_query("""
        SELECT materia, argomento, livello, titolo_esercizio, punteggio_massimo, 
               data_approvazione, valutatore, numero_usi
        FROM esercizi_approvati 
        ORDER BY data_approvazione DESC
    """, conn)
    conn.close()
    
    if esercizi_df.empty:
        st.info("📝 Nessun esercizio approvato.")
        return
    
    # Filtri
    col1, col2, col3 = st.columns(3)
    with col1:
        materia_filter = st.selectbox("Filtra Materia:", ["Tutte"] + list(esercizi_df['materia'].unique()))
    with col2:
        argomento_filter = st.selectbox("Filtra Argomento:", ["Tutti"] + list(esercizi_df['argomento'].unique()))
    with col3:
        livello_filter = st.selectbox("Filtra Livello:", ["Tutti"] + list(esercizi_df['livello'].unique()))
    
    # Applica filtri
    filtered_df = esercizi_df.copy()
    if materia_filter != "Tutte":
        filtered_df = filtered_df[filtered_df['materia'] == materia_filter]
    if argomento_filter != "Tutti":
        filtered_df = filtered_df[filtered_df['argomento'] == argomento_filter]
    if livello_filter != "Tutti":
        filtered_df = filtered_df[filtered_df['livello'] == livello_filter]
    
    st.dataframe(filtered_df, use_container_width=True)
    
    # Export
    if st.button("📥 Esporta Esercizi (CSV)"):
        csv = filtered_df.to_csv(index=False)
        st.download_button(
            "Scarica CSV",
            csv,
            "esercizi_approvati.csv",
            "text/csv"
        )

def render_database_verifiche():
    """Database verifiche"""
    st.subheader("📋 Verifiche Approvate")
    
    conn = sqlite3.connect(DB_PATH)
    verifiche_df = pd.read_sql_query("""
        SELECT materia, argomento, livello, titolo_verifica, numero_esercizi,
               data_approvazione, valutatore
        FROM verifiche_approvate 
        ORDER BY data_approvazione DESC
    """, conn)
    conn.close()
    
    if verifiche_df.empty:
        st.info("📋 Nessuna verifica approvata.")
        return
    
    st.dataframe(verifiche_df, use_container_width=True)
    
    # Export
    if st.button("📥 Esporta Verifiche (CSV)"):
        csv = verifiche_df.to_csv(index=False)
        st.download_button(
            "Scarica CSV",
            csv,
            "verifiche_approvate.csv",
            "text/csv"
        )

# Funzioni helper
def get_count_esercizi_approvati():
    """Conteggio esercizi approvati"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM esercizi_approvati")
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_count_verifiche_approvate():
    """Conteggio verifiche approvate"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM verifiche_approvate")
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_count_test_totali():
    """Conteggio test totali"""
    conn = sqlite3.connect(TEST_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM test_results")
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_quality_rate():
    """Calcola quality rate"""
    conn = sqlite3.connect(TEST_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM test_results WHERE esito_test = 'PASS'")
    pass_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM test_results")
    total_count = cursor.fetchone()[0]
    conn.close()
    return (pass_count / total_count * 100) if total_count > 0 else 0

def render_andamento_approvazioni():
    """Grafico andamento approvazioni"""
    conn = sqlite3.connect(DB_PATH)
    
    # Ultime 30 giornate
    approvazioni_df = pd.read_sql_query("""
        SELECT DATE(data_approvazione) as date, COUNT(*) as count 
        FROM esercizi_approvati 
        WHERE data_approvazione >= date('now', '-30 days')
        GROUP BY DATE(data_approvazione) 
        ORDER BY date
    """, conn)
    
    conn.close()
    
    if not approvazioni_df.empty:
        fig = px.line(approvazioni_df, x='date', y='count', title='Approvazioni Ultimi 30 Giorni')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("📝 Nessun dato disponibile per il grafico.")

def render_distribuzione_materie():
    """Grafico distribuzione materie"""
    conn = sqlite3.connect(DB_PATH)
    materie_df = pd.read_sql_query("""
        SELECT materia, COUNT(*) as count 
        FROM esercizi_approvati 
        GROUP BY materia 
        ORDER BY count DESC
    """, conn)
    conn.close()
    
    if not materie_df.empty:
        fig = px.pie(materie_df, values='count', names='materia', title='Distribuzione per Materia')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("📝 Nessun dato disponibile per il grafico.")

# Main execution
def main():
    """Funzione principale"""
    # Inizializza session state
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "🏠 Dashboard"
    
    # Verifica accesso admin
    check_admin_access()
    
    # Inizializza database
    init_databases()
    
    # Rendering dashboard
    render_dashboard()

if __name__ == "__main__":
    main()
