#!/usr/bin/env python3
"""
Dashboard PromptFoo per monitoraggio qualità nel tempo
"""

import streamlit as st
import json
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from pathlib import Path

def render_promptfoo_dashboard():
    """Dashboard principale per monitoraggio PromptFoo"""
    
    st.markdown("""
    <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                padding: 2rem; border-radius: 10px; margin-bottom: 2rem;'>
        <h1 style='color: white; margin: 0;'>📊 Dashboard PromptFoo</h1>
        <p style='color: white; margin: 0.5rem 0 0 0;'>Monitoraggio qualità verifiche nel tempo</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Carica dati
    ci_data = load_ci_reports()
    test_data = load_test_results()
    
    if not ci_data and not test_data:
        st.info("📂 Nessun dato disponibile. Esegui alcuni test PromptFoo per vedere la dashboard.")
        return
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📈 Panoramica", 
        "🔍 Analisi Dettagliata", 
        "⚠️ Regressioni", 
        "📋 Report"
    ])
    
    with tab1:
        render_overview(ci_data, test_data)
    
    with tab2:
        render_detailed_analysis(ci_data, test_data)
    
    with tab3:
        render_regression_analysis(ci_data, test_data)
    
    with tab4:
        render_reports(ci_data, test_data)

def load_ci_reports():
    """Carica report CI/CD"""
    reports = []
    reports_dir = Path("promptfoo_ci_reports")
    
    if not reports_dir.exists():
        return reports
    
    for file in reports_dir.glob("ci_report_*.json"):
        try:
            with open(file, 'r') as f:
                data = json.load(f)
                reports.append(data)
        except Exception:
            continue
    
    return sorted(reports, key=lambda x: x.get('timestamp', ''), reverse=True)

def load_test_results():
    """Carica risultati test"""
    results = []
    
    # Carica da test_results
    for dir_name in ["test_results", "real_verifications"]:
        dir_path = Path(dir_name)
        if not dir_path.exists():
            continue
        
        for file in dir_path.glob("*.json"):
            try:
                with open(file, 'r') as f:
                    data = json.load(f)
                    data['source_file'] = str(file)
                    results.append(data)
            except Exception:
                continue
    
    return sorted(results, key=lambda x: x.get('timestamp', ''), reverse=True)

def render_overview(ci_data, test_data):
    """Panoramica generale"""
    st.markdown("## 📈 Panoramica Qualità")
    
    # Metriche principali
    col1, col2, col3, col4 = st.columns(4)
    
    # Total tests
    total_tests = len(test_data)
    passed_tests = sum(1 for t in test_data if t.get('passed', False))
    success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    
    with col1:
        st.metric("Test Totali", total_tests)
    
    with col2:
        st.metric("Test Passati", passed_tests)
    
    with col3:
        st.metric("Success Rate", f"{success_rate:.1f}%")
    
    with col4:
        # CI success rate
        ci_passed = sum(1 for c in ci_data if c.get('success', False))
        ci_total = len(ci_data)
        ci_rate = (ci_passed / ci_total * 100) if ci_total > 0 else 0
        st.metric("CI Success", f"{ci_rate:.1f}%")
    
    # Grafico andamento
    st.markdown("### 📊 Andamento nel Tempo")
    
    if ci_data:
        # Prepara dati per grafico
        df_ci = pd.DataFrame(ci_data)
        df_ci['timestamp'] = pd.to_datetime(df_ci['timestamp'])
        df_ci['date'] = df_ci['timestamp'].dt.date
        
        # Success rate giornaliero
        daily_stats = df_ci.groupby('date').agg({
            'success': ['count', 'sum']
        }).reset_index()
        daily_stats.columns = ['date', 'total', 'passed']
        daily_stats['success_rate'] = (daily_stats['passed'] / daily_stats['total'] * 100).round(1)
        
        fig = px.line(
            daily_stats, 
            x='date', 
            y='success_rate',
            title='Success Rate CI/CD nel Tempo',
            labels={'success_rate': 'Success Rate (%)', 'date': 'Data'}
        )
        fig.update_layout(yaxis=dict(range=[0, 100]))
        st.plotly_chart(fig, use_container_width=True)
    
    # Test per materia
    st.markdown("### 📚 Qualità per Materia")
    
    if test_data:
        materie_stats = {}
        for test in test_data:
            materia = test.get('materia', 'Sconosciuta')
            if materia not in materie_stats:
                materie_stats[materia] = {'total': 0, 'passed': 0}
            materie_stats[materia]['total'] += 1
            if test.get('passed', False):
                materie_stats[materia]['passed'] += 1
        
        # Calcola success rate
        for materia in materie_stats:
            total = materie_stats[materia]['total']
            passed = materie_stats[materia]['passed']
            materie_stats[materia]['success_rate'] = (passed / total * 100) if total > 0 else 0
        
        df_materie = pd.DataFrame([
            {'Materia': m, **stats} 
            for m, stats in materie_stats.items()
        ]).sort_values('success_rate', ascending=False)
        
        fig = px.bar(
            df_materie,
            x='Materia',
            y='success_rate',
            title='Success Rate per Materia',
            labels={'success_rate': 'Success Rate (%)', 'Materia': 'Materia'}
        )
        fig.update_layout(yaxis=dict(range=[0, 100]))
        st.plotly_chart(fig, use_container_width=True)

def render_detailed_analysis(ci_data, test_data):
    """Analisi dettagliata"""
    st.markdown("## 🔍 Analisi Dettagliata")
    
    # Filtri
    col1, col2 = st.columns(2)
    
    with col1:
        materia_filter = st.selectbox(
            "Filtra per materia:",
            ["Tutte"] + sorted(list(set(t.get('materia', 'Sconosciuta') for t in test_data))),
            key="detail_materia"
        )
    
    with col2:
        days_filter = st.selectbox(
            "Periodo:",
            ["7 giorni", "30 giorni", "90 giorni", "Tutti"],
            key="detail_period"
        )
    
    # Filtra dati
    filtered_data = filter_test_data(test_data, materia_filter, days_filter)
    
    if not filtered_data:
        st.info("📂 Nessun dato corrispondente ai filtri")
        return
    
    # Tabella dettagliata
    st.markdown("### 📋 Risultati Dettagliati")
    
    df_data = []
    for test in filtered_data:
        df_data.append({
            'Timestamp': test.get('timestamp', '')[:19],
            'Materia': test.get('materia', 'N/A'),
            'Livello': test.get('livello', 'N/A'),
            'Status': '✅ PASSATO' if test.get('passed', False) else '❌ FALLITO',
            'Esercizi': f"{test.get('actual_esercizi', test.get('esercizi', 'N/A'))}/{test.get('num_esercizi', test.get('target_esercizi', 'N/A'))}",
            'Punti': f"{test.get('actual_punti', test.get('punti', 'N/A'))}/{test.get('punti_totali', test.get('target_punti', 'N/A'))}"
        })
    
    df = pd.DataFrame(df_data)
    st.dataframe(df, use_container_width=True)
    
    # Analisi fallimenti
    st.markdown("### 🚨 Analisi Fallimenti")
    
    failures = [t for t in filtered_data if not t.get('passed', False)]
    
    if failures:
        st.write(f"**{len(failures)} test falliti:**")
        
        for failure in failures[:10]:  # Primi 10
            with st.expander(f"❌ {failure.get('materia', 'N/A')} - {failure.get('timestamp', '')[:10]}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Materia:** {failure.get('materia', 'N/A')}")
                    st.write(f"**Livello:** {failure.get('livello', 'N/A')}")
                    st.write(f"**Errore:** {failure.get('error', 'Fallimento generico')}")
                
                with col2:
                    st.write(f"**Esercizi:** {failure.get('actual_esercizi', 'N/A')}/{failure.get('num_esercizi', 'N/A')}")
                    st.write(f"**Punti:** {failure.get('actual_punti', 'N/A')}/{failure.get('punti_totali', 'N/A')}")
                
                # Output se disponibile
                output = failure.get('output_preview', '')
                if output:
                    st.code(output[:300] + "..." if len(output) > 300 else output, language='latex')
    else:
        st.success("✅ Nessun fallimento nel periodo selezionato!")

def render_regression_analysis(ci_data, test_data):
    """Analisi regressioni"""
    st.markdown("## ⚠️ Analisi Regressioni")
    
    # Identifica potenziali regressioni
    regressions = find_regressions(test_data)
    
    if regressions:
        st.warning(f"🚨 Trovate {len(regressions)} potenziali regressioni:")
        
        for regression in regressions:
            with st.expander(f"📉 {regression['materia']} - {regression['period']}"):
                st.write(f"**Materia:** {regression['materia']}")
                st.write(f"**Periodo:** {regression['period']}")
                st.write(f"**Trend:** {regression['trend']}")
                st.write(f"**Dettagli:** {regression['details']}")
                
                # Grafico del trend
                if 'data' in regression:
                    df_trend = pd.DataFrame(regression['data'])
                    fig = px.line(
                        df_trend,
                        x='timestamp',
                        y='success_rate',
                        title=f'Trend {regression["materia"]}'
                    )
                    st.plotly_chart(fig, use_container_width=True)
    else:
        st.success("✅ Nessuna regressione rilevata!")
    
    # Test stabilità
    st.markdown("### 🧪 Test di Stabilità")
    
    stability_score = calculate_stability_score(test_data)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Stabilità", f"{stability_score:.1f}%")
    
    with col2:
        # Volatilità
        volatility = calculate_volatility(test_data)
        st.metric("Volatilità", f"{volatility:.1f}%")
    
    with col3:
        # Trend generale
        trend = calculate_overall_trend(test_data)
        trend_emoji = "📈" if trend > 0 else "📉" if trend < 0 else "➡️"
        st.metric("Trend Generale", f"{trend_emoji} {trend:+.1f}%")

def render_reports(ci_data, test_data):
    """Report esportabili"""
    st.markdown("## 📋 Report ed Esportazione")
    
    # Report riassuntivo
    st.markdown("### 📊 Report Riassuntivo")
    
    # Calcola metriche
    total_tests = len(test_data)
    passed_tests = sum(1 for t in test_data if t.get('passed', False))
    success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    
    # Statistiche per materia
    materie_stats = {}
    for test in test_data:
        materia = test.get('materia', 'Sconosciuta')
        if materia not in materie_stats:
            materie_stats[materia] = {'total': 0, 'passed': 0}
        materie_stats[materia]['total'] += 1
        if test.get('passed', False):
            materie_stats[materia]['passed'] += 1
    
    # Mostra report
    st.markdown(f"""
    **Report PromptFoo - {datetime.now().strftime('%d/%m/%Y %H:%M')}**
    
    **Metriche Generali:**
    - Test Totali: {total_tests}
    - Test Passati: {passed_tests}
    - Success Rate: {success_rate:.1f}%
    
    **Performance per Materia:**
    """)
    
    for materia, stats in sorted(materie_stats.items()):
        rate = (stats['passed'] / stats['total'] * 100) if stats['total'] > 0 else 0
        st.write(f"- **{materia}**: {stats['passed']}/{stats['total']} ({rate:.1f}%)")
    
    # Pulsanti esportazione
    st.markdown("### 📤 Esporta Dati")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📄 Esporta CSV", use_container_width=True):
            csv_data = export_csv(test_data)
            st.download_button(
                label="💾 Download CSV",
                data=csv_data,
                file_name=f"promptfoo_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
    
    with col2:
        if st.button("📋 Esporta JSON", use_container_width=True):
            json_data = json.dumps({
                'ci_reports': ci_data,
                'test_results': test_data,
                'generated_at': datetime.now().isoformat()
            }, indent=2)
            st.download_button(
                label="💾 Download JSON",
                data=json_data,
                file_name=f"promptfoo_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
    
    with col3:
        if st.button("📈 Esporta Report PDF", use_container_width=True):
            st.info("📄 Funzione PDF in sviluppo - usa CSV/JSON per ora")

# Funzioni di supporto
def filter_test_data(test_data, materia_filter, days_filter):
    """Filtra dati test in base ai criteri"""
    filtered = test_data.copy()
    
    # Filtra per materia
    if materia_filter != "Tutte":
        filtered = [t for t in filtered if t.get('materia') == materia_filter]
    
    # Filtra per periodo
    if days_filter != "Tutti":
        days_map = {"7 giorni": 7, "30 giorni": 30, "90 giorni": 90}
        days = days_map[days_filter]
        cutoff_date = datetime.now() - timedelta(days=days)
        
        filtered = [
            t for t in filtered 
            if datetime.fromisoformat(t.get('timestamp', '').replace('Z', '+00:00')) > cutoff_date
        ]
    
    return filtered

def find_regressions(test_data):
    """Identifica potenziali regressioni"""
    regressions = []
    
    # Analisi per materia
    materie = list(set(t.get('materia', 'Sconosciuta') for t in test_data))
    
    for materia in materie:
        materia_tests = [t for t in test_data if t.get('materia') == materia]
        
        if len(materia_tests) < 5:  # Skip se pochi dati
            continue
        
        # Calcola trend ultimi test
        recent_tests = sorted(materia_tests, key=lambda x: x.get('timestamp', ''))[-10:]
        recent_rates = [1 if t.get('passed', False) else 0 for t in recent_tests]
        
        # Semplice detection trend negativo
        if len(recent_rates) >= 3:
            recent_avg = sum(recent_rates[-3:]) / 3
            older_avg = sum(recent_rates[-6:-3]) / 3 if len(recent_rates) >= 6 else recent_avg
            
            if recent_avg < older_avg - 0.2:  # Calo > 20%
                regressions.append({
                    'materia': materia,
                    'period': 'ultimi 10 test',
                    'trend': 'negativo',
                    'details': f'Calo success rate da {older_avg:.1%} a {recent_avg:.1%}',
                    'data': [
                        {
                            'timestamp': t.get('timestamp', ''),
                            'success_rate': 1 if t.get('passed', False) else 0
                        }
                        for t in recent_tests
                    ]
                })
    
    return regressions

def calculate_stability_score(test_data):
    """Calcola punteggio di stabilità"""
    if not test_data:
        return 0
    
    # Stabilità basata su consistenza dei risultati
    materie = list(set(t.get('materia', 'Sconosciuta') for t in test_data))
    stability_scores = []
    
    for materia in materie:
        materia_tests = [t for t in test_data if t.get('materia') == materia]
        
        if len(materia_tests) < 2:
            continue
        
        success_rates = [1 if t.get('passed', False) else 0 for t in materia_tests]
        avg_rate = sum(success_rates) / len(success_rates)
        
        # Stabilità = consistenza con la media
        variance = sum((r - avg_rate) ** 2 for r in success_rates) / len(success_rates)
        stability = max(0, 100 - (variance * 100))  # Convert variance to stability score
        
        stability_scores.append(stability)
    
    return sum(stability_scores) / len(stability_scores) if stability_scores else 0

def calculate_volatility(test_data):
    """Calcola volatilità dei test"""
    if len(test_data) < 2:
        return 0
    
    # Volatilità basata su variazione day-to-day
    dates = {}
    for test in test_data:
        date = test.get('timestamp', '')[:10]  # YYYY-MM-DD
        if date not in dates:
            dates[date] = {'total': 0, 'passed': 0}
        dates[date]['total'] += 1
        if test.get('passed', False):
            dates[date]['passed'] += 1
    
    if len(dates) < 2:
        return 0
    
    # Calcola rates giornalieri
    daily_rates = []
    for date_data in dates.values():
        rate = date_data['passed'] / date_data['total'] if date_data['total'] > 0 else 0
        daily_rates.append(rate)
    
    # Volatilità = deviazione standard delle rates
    avg_rate = sum(daily_rates) / len(daily_rates)
    variance = sum((r - avg_rate) ** 2 for r in daily_rates) / len(daily_rates)
    
    return (variance ** 0.5) * 100  # Convert to percentage

def calculate_overall_trend(test_data):
    """Calcolo trend generale"""
    if len(test_data) < 2:
        return 0
    
    # Dividi in due periodi
    sorted_tests = sorted(test_data, key=lambda x: x.get('timestamp', ''))
    mid_point = len(sorted_tests) // 2
    
    first_half = sorted_tests[:mid_point]
    second_half = sorted_tests[mid_point:]
    
    first_rate = sum(1 if t.get('passed', False) else 0 for t in first_half) / len(first_half)
    second_rate = sum(1 if t.get('passed', False) else 0 for t in second_half) / len(second_half)
    
    return (second_rate - first_rate) * 100

def export_csv(test_data):
    """Esporta dati in formato CSV"""
    import csv
    import io
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        'timestamp', 'materia', 'livello', 'passed', 
        'actual_esercizi', 'target_esercizi',
        'actual_punti', 'target_punti'
    ])
    
    # Data
    for test in test_data:
        writer.writerow([
            test.get('timestamp', ''),
            test.get('materia', ''),
            test.get('livello', ''),
            test.get('passed', ''),
            test.get('actual_esercizi', test.get('esercizi', '')),
            test.get('num_esercizi', test.get('target_esercizi', '')),
            test.get('actual_punti', test.get('punti', '')),
            test.get('punti_totali', test.get('target_punti', ''))
        ])
    
    return output.getvalue()

# Funzione principale per integrazione
def render_dashboard_page():
    """Renderizza dashboard PromptFoo"""
    render_promptfoo_dashboard()
