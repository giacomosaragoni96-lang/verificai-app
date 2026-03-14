"""
Dashboard completo per monitoraggio del sistema di qualità esercizi
"""

import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json

def render_quality_dashboard():
    """Dashboard principale per sistema qualità"""
    
    st.set_page_config(
        page_title="Quality Dashboard - VerificAI",
        layout="wide",
        page_icon="🌟"
    )
    
    st.title("🌟 VerificAI Quality Dashboard")
    st.markdown("Monitoraggio del sistema di qualità esercizi e training AI")
    
    # Sidebar filtri
    with st.sidebar:
        st.header("🔍 Filtri")
        
        # Periodo tempo
        periodo = st.selectbox(
            "Periodo",
            ["Ultimi 7 giorni", "Ultimi 30 giorni", "Ultimi 3 mesi", "Tutto"],
            key="periodo_filter"
        )
        
        # Materia
        materie = get_available_subjects()
        materia_sel = st.selectbox("Materia", ["Tutte"] + materie, key="materia_filter")
        
        # Livello
        livelli = get_available_levels()
        livello_sel = st.selectbox("Livello", ["Tutti"] + livelli, key="livello_filter")
    
    # Main content
    render_overview_stats(periodo, materia_sel, livello_sel)
    
    st.markdown("---")
    
    # Tabs per diverse visualizzazioni
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Panoramica", "🌟 Banca Qualità", "🤖 Training AI", "📈 Trend"])
    
    with tab1:
        render_panoramica_generale(periodo, materia_sel, livello_sel)
    
    with tab2:
        render_banca_qualita_dettagli(materia_sel, livello_sel)
    
    with tab3:
        render_training_ai_metrics()
    
    with tab4:
        render_trend_analisi(periodo, materia_sel, livello_sel)

def get_available_subjects():
    """Ottieni lista materie disponibili"""
    try:
        conn = sqlite3.connect("valutazioni_esercizi.db")
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT materia FROM esercizi_qualita ORDER BY materia")
        materie = [row[0] for row in cursor.fetchall()]
        conn.close()
        return materie
    except:
        return []

def get_available_levels():
    """Ottieni lista livelli disponibili"""
    try:
        conn = sqlite3.connect("valutazioni_esercizi.db")
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT livello FROM esercizi_qualita ORDER BY livello")
        livelli = [row[0] for row in cursor.fetchall()]
        conn.close()
        return livelli
    except:
        return []

def get_date_filter(periodo):
    """Ottieni filtro data basato sul periodo"""
    now = datetime.now()
    if periodo == "Ultimi 7 giorni":
        return now - timedelta(days=7)
    elif periodo == "Ultimi 30 giorni":
        return now - timedelta(days=30)
    elif periodo == "Ultimi 3 mesi":
        return now - timedelta(days=90)
    else:
        return None

def render_overview_stats(periodo, materia, livello):
    """Statistiche overview principali"""
    
    date_filter = get_date_filter(periodo)
    
    try:
        conn = sqlite3.connect("valutazioni_esercizi.db")
        
        # Query base con filtri
        base_query = "SELECT COUNT(*) FROM esercizi_qualita WHERE 1=1"
        params = []
        
        if date_filter:
            base_query += " AND data_valutazione >= ?"
            params.append(date_filter.isoformat())
        
        if materia != "Tutte":
            base_query += " AND materia = ?"
            params.append(materia)
        
        if livello != "Tutti":
            base_query += " AND livello = ?"
            params.append(livello)
        
        cursor = conn.cursor()
        
        # Statistiche principali
        cursor.execute(base_query, params)
        total_quality = cursor.fetchone()[0]
        
        # Valutazioni totali
        total_query = base_query.replace("esercizi_qualita", "esercizi_valutati")
        cursor.execute(total_query, params)
        total_evaluated = cursor.fetchone()[0]
        
        # Qualità media
        cursor.execute(f"SELECT AVG(qualita_score) FROM esercizi_qualita WHERE 1=1", params)
        avg_quality = cursor.fetchone()[0] or 0
        
        # Tasso qualità
        quality_rate = (total_quality / total_evaluated * 100) if total_evaluated > 0 else 0
        
        conn.close()
        
        # Metric cards
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "🌟 Esercizi Qualità",
                total_quality,
                delta="↑ 12%" if total_quality > 0 else None
            )
        
        with col2:
            st.metric(
                "📝 Valutazioni Totali",
                total_evaluated,
                delta="↑ 8%" if total_evaluated > 0 else None
            )
        
        with col3:
            st.metric(
                "📊 Tasso Qualità",
                f"{quality_rate:.1f}%",
                delta="↑ 2.3%" if quality_rate > 0 else None
            )
        
        with col4:
            st.metric(
                "⭐ Qualità Media",
                f"{avg_quality:.3f}",
                delta="↑ 0.05" if avg_quality > 0 else None
            )
        
    except Exception as e:
        st.error(f"Errore caricando statistiche: {e}")

def render_panoramica_generale(periodo, materia, livello):
    """Panoramica generale con grafici"""
    
    try:
        conn = sqlite3.connect("valutazioni_esercizi.db")
        
        # Distribuzione per materia
        query_materie = """
        SELECT materia, COUNT(*) as count, AVG(qualita_score) as avg_score
        FROM esercizi_qualita 
        WHERE 1=1
        """
        params = []
        
        date_filter = get_date_filter(periodo)
        if date_filter:
            query_materie += " AND data_valutazione >= ?"
            params.append(date_filter.isoformat())
        
        if materia != "Tutte":
            query_materie += " AND materia = ?"
            params.append(materia)
        
        query_materie += " GROUP BY materia ORDER BY count DESC"
        
        df_materie = pd.read_sql_query(query_materie, conn, params=params)
        
        if not df_materie.empty:
            # Grafico a barre materie
            fig = px.bar(
                df_materie, 
                x='materia', 
                y='count',
                title='Esercizi Qualità per Materia',
                color='avg_score',
                color_continuous_scale='Viridis'
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        # Distribuzione qualità
        query_qualita = """
        SELECT 
            CASE 
                WHEN qualita_score >= 0.9 THEN 'Eccellente (≥0.9)'
                WHEN qualita_score >= 0.8 THEN 'Buono (0.8-0.9)'
                WHEN qualita_score >= 0.7 THEN 'Sufficiente (0.7-0.8)'
                ELSE 'Da migliorare (<0.7)'
            END as quality_range,
            COUNT(*) as count
        FROM esercizi_qualita 
        WHERE 1=1
        """
        
        params_qualita = []
        if date_filter:
            query_qualita += " AND data_valutazione >= ?"
            params_qualita.append(date_filter.isoformat())
        
        if materia != "Tutte":
            query_qualita += " AND materia = ?"
            params_qualita.append(materia)
        
        query_qualita += " GROUP BY quality_range ORDER BY count DESC"
        
        df_qualita = pd.read_sql_query(query_qualita, conn, params=params_qualita)
        
        if not df_qualita.empty:
            # Pie chart qualità
            fig = px.pie(
                df_qualita, 
                values='count', 
                names='quality_range',
                title='Distribuzione Qualità Esercizi'
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        conn.close()
        
    except Exception as e:
        st.error(f"Errore panoramica generale: {e}")

def render_banca_qualita_dettagli(materia, livello):
    """Dettaglio banca esercizi qualità"""
    
    st.subheader("🌟 Banca Esercizi Qualità")
    
    try:
        conn = sqlite3.connect("valutazioni_esercizi.db")
        
        # Query dettagliata
        query = """
        SELECT materia, argomento, livello, titolo_esercizio, 
               qualita_score, feedback, data_valutazione, valutatore,
               numero_usi, ultima_usa
        FROM esercizi_qualita 
        WHERE 1=1
        """
        
        params = []
        if materia != "Tutte":
            query += " AND materia = ?"
            params.append(materia)
        
        if livello != "Tutti":
            query += " AND livello = ?"
            params.append(livello)
        
        query += " ORDER BY qualita_score DESC, data_valutazione DESC"
        
        df = pd.read_sql_query(query, conn, params=params)
        
        if df.empty:
            st.info("📝 Nessun esercizio di qualità trovato con i filtri selezionati")
            return
        
        # Statistiche banca
        st.markdown("### 📊 Statistiche Banca Dati")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Esercizi Totali", len(df))
        with col2:
            st.metric("Qualità Media", f"{df['qualita_score'].mean():.3f}")
        with col3:
            st.metric("Argomenti Coperti", df['argomento'].nunique())
        
        # Tabella dettagliata
        st.markdown("### 📋 Esercizi Qualità")
        
        # Formatta colonne per visualizzazione
        df_display = df.copy()
        df_display['qualita_score'] = df_display['qualita_score'].round(3)
        df_display['data_valutazione'] = pd.to_datetime(df_display['data_valutazione']).dt.strftime('%Y-%m-%d')
        df_display['ultima_usa'] = pd.to_datetime(df_display['ultima_usa']).dt.strftime('%Y-%m-%d') if df_display['ultima_usa'].notna().any() else 'Mai'
        
        # Color coding per qualità
        def color_quality(score):
            if score >= 0.9:
                return 'background-color: #d4edda'
            elif score >= 0.8:
                return 'background-color: #fff3cd'
            elif score >= 0.7:
                return 'background-color: #f8d7da'
            else:
                return 'background-color: #f5c6cb'
        
        # Stile tabella
        st.dataframe(
            df_display.style.applymap(color_quality, subset=['qualita_score']),
            use_container_width=True,
            height=400
        )
        
        # Export funzionalità
        if st.button("📥 Esporta Banca Qualità (JSON)"):
            corpus = export_training_corpus_filtered(df)
            st.download_button(
                "Scarica Corpus JSON",
                data=json.dumps(corpus, indent=2, ensure_ascii=False),
                file_name=f"quality_corpus_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
        
        conn.close()
        
    except Exception as e:
        st.error(f"Errore banca qualità: {e}")

def render_training_ai_metrics():
    """Metriche training AI"""
    
    st.subheader("🤖 Training AI Metrics")
    
    try:
        conn = sqlite3.connect("valutazioni_esercizi.db")
        
        # Statistiche training
        cursor = conn.cursor()
        
        # Esercizi più usati
        cursor.execute("""
            SELECT titolo_esercizio, materia, argomento, numero_usi, qualita_score
            FROM esercizi_qualita 
            WHERE numero_usi > 0
            ORDER BY numero_usi DESC, qualita_score DESC
            LIMIT 10
        """)
        
        top_used = cursor.fetchall()
        
        if top_used:
            st.markdown("### 🔝 Esercizi Più Usati per Training")
            
            for i, (titolo, materia, argomento, usi, score) in enumerate(top_used, 1):
                with st.expander(f"{i}. {titolo} (Usi: {usi}, Score: {score:.3f})"):
                    st.write(f"**Materia:** {materia}")
                    st.write(f"**Argomento:** {argomento}")
                    st.write(f"**Qualità:** {score:.3f}")
                    st.write(f"**Volte usato:** {usi}")
        
        # Coverage analysis
        cursor.execute("""
            SELECT materia, COUNT(DISTINCT argomento) as argomenti_coperti,
                   COUNT(*) as esercizi_totali
            FROM esercizi_qualita 
            GROUP BY materia
            ORDER BY esercizi_totali DESC
        """)
        
        coverage = cursor.fetchall()
        
        if coverage:
            st.markdown("### 📊 Coverage per Materia")
            
            df_coverage = pd.DataFrame(coverage, columns=['Materia', 'Argomenti Coperti', 'Esercizi Totali'])
            
            fig = px.scatter(
                df_coverage,
                x='Argomenti Coperti',
                y='Esercizi Totali',
                color='Materia',
                size='Esercizi Totali',
                title='Coverage Training AI: Argomenti vs Esercizi'
            )
            fig.update_layout(height=500)
            st.plotly_chart(fig, use_container_width=True)
        
        conn.close()
        
    except Exception as e:
        st.error(f"Errore training metrics: {e}")

def render_trend_analisi(periodo, materia, livello):
    """Analisi trend nel tempo"""
    
    st.subheader("📈 Analisi Trend Qualità")
    
    try:
        conn = sqlite3.connect("valutazioni_esercizi.db")
        
        # Trend qualità nel tempo
        query_trend = """
        SELECT DATE(data_valutazione) as date, 
               COUNT(*) as esercizi,
               AVG(qualita_score) as avg_quality
        FROM esercizi_qualita 
        WHERE 1=1
        """
        
        params = []
        date_filter = get_date_filter(periodo)
        if date_filter:
            query_trend += " AND data_valutazione >= ?"
            params.append(date_filter.isoformat())
        
        if materia != "Tutte":
            query_trend += " AND materia = ?"
            params.append(materia)
        
        query_trend += " GROUP BY DATE(data_valutazione) ORDER BY date"
        
        df_trend = pd.read_sql_query(query_trend, conn, params=params)
        
        if not df_trend.empty:
            # Line chart trend qualità
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=df_trend['date'],
                y=df_trend['avg_quality'],
                mode='lines+markers',
                name='Qualità Media',
                line=dict(color='blue', width=2),
                marker=dict(size=6)
            ))
            
            fig.add_trace(go.Scatter(
                x=df_trend['date'],
                y=df_trend['esercizi'],
                mode='lines+markers',
                name='Esercizi Giornalieri',
                yaxis='y2',
                line=dict(color='green', width=2),
                marker=dict(size=6)
            ))
            
            fig.update_layout(
                title='Trend Qualità Esercizi nel Tempo',
                xaxis_title='Data',
                yaxis_title='Qualità Media',
                yaxis2=dict(title='Esercizi Giornalieri', overlaying='y', side='right'),
                height=500,
                legend=dict(x=0.01, y=0.99)
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        conn.close()
        
    except Exception as e:
        st.error(f"Errore analisi trend: {e}")

def export_training_corpus_filtered(df):
    """Esporta corpus filtrato"""
    
    corpus = {
        'metadata': {
            'export_date': datetime.now().isoformat(),
            'total_exercises': len(df),
            'description': 'Filtered quality exercises corpus'
        },
        'exercises': []
    }
    
    for _, row in df.iterrows():
        corpus['exercises'].append({
            'subject': row['materia'],
            'topic': row['argomento'],
            'level': row['livello'],
            'title': row['titolo_esercizio'],
            'quality_score': row['qualita_score'],
            'feedback': row['feedback'],
            'times_used': row['numero_usi'],
            'last_used': row['ultima_usa']
        })
    
    return corpus

if __name__ == "__main__":
    render_quality_dashboard()
