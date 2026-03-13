# ── training_dashboard.py ─────────────────────────────────────────────────────
# Dashboard admin per monitorare il sistema di training AI silenzioso
# ───────────────────────────────────────────────────────────────────────────────

import streamlit as st
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from supabase import Client

logger = logging.getLogger("verificai.training_dashboard")


def render_training_dashboard(supabase_admin: Client):
    """
    Renderizza dashboard admin per monitorare il training AI.
    Solo visibile agli admin.
    """
    if not st.session_state.get('is_admin', False):
        return
    
    st.markdown("---")
    st.markdown("## 🤖 Training AI Dashboard (Admin Only)")
    
    # Recupera dati training
    try:
        from background_training import get_training_dashboard_data
        dashboard_data = get_training_dashboard_data(supabase_admin)
        
        # Stats principali
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Feedback Totali", 
                dashboard_data.get('total_feedback', 0),
                delta=None
            )
        
        with col2:
            st.metric(
                "Feedback Positivi", 
                dashboard_data.get('good_feedback', 0),
                delta=None
            )
        
        with col3:
            satisfaction = dashboard_data.get('overall_satisfaction', 0)
            st.metric(
                "Soddisfazione", 
                f"{satisfaction:.1%}",
                delta=None
            )
        
        with col4:
            st.metric(
                "Pattern Training", 
                dashboard_data.get('total_patterns', 0),
                delta=None
            )
        
        # Stats recenti
        col1, col2 = st.columns(2)
        
        with col1:
            recent_feedback = dashboard_data.get('recent_feedback', 0)
            st.metric(
                "Feedback Ultimi 7 giorni", 
                recent_feedback,
                delta=None
            )
        
        with col2:
            recent_sat = dashboard_data.get('recent_satisfaction', 0)
            st.metric(
                "Soddisfazione Recente", 
                f"{recent_sat:.1%}",
                delta=None
            )
        
        # Background processor status
        bg_status = dashboard_data.get('background_status')
        if bg_status:
            st.markdown("### 🔧 Sistema Background")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                status_icon = "🟢" if bg_status.get('running') else "🔴"
                st.metric("Status", f"{status_icon} {'Running' if bg_status.get('running') else 'Stopped'}")
            
            with col2:
                thread_icon = "🟢" if bg_status.get('thread_alive') else "🔴"
                st.metric("Thread", f"{thread_icon} {'Alive' if bg_status.get('thread_alive') else 'Dead'}")
            
            with col3:
                last_update = bg_status.get('last_update')
                if last_update:
                    update_time = datetime.fromisoformat(last_update.replace('Z', '+00:00'))
                    time_ago = datetime.now(timezone.utc) - update_time
                    hours_ago = time_ago.total_seconds() / 3600
                    st.metric("Last Update", f"{hours_ago:.1f}h fa")
                else:
                    st.metric("Last Update", "Mai")
        
        # Feedback per materia
        st.markdown("### 📊 Feedback per Materia")
        _render_materia_feedback(supabase_admin)
        
        # Andamento temporale
        st.markdown("### 📈 Andamento Temporale")
        _render_temporal_trends(supabase_admin)
        
        # Pattern più efficaci
        st.markdown("### 🎯 Pattern Training Efficaci")
        _render_effective_patterns(supabase_admin)
        
    except Exception as e:
        logger.error(f"Errore rendering dashboard: {e}")
        st.error(f"Errore nel caricamento della dashboard: {e}")


def _render_materia_feedback(supabase_admin: Client):
    """
    Renderizza statistiche feedback per materia.
    """
    try:
        materie = ['Matematica', 'Fisica', 'Italiano', 'Storia', 'Geografia', 'Chimica', 'Informatica']
        
        materia_stats = {}
        for materia in materie:
            result = supabase_admin.table('ai_feedback')\
                .select('rating')\
                .eq('materia', materia)\
                .execute()
            
            if result.data:
                total = len(result.data)
                good = sum(1 for item in result.data if item.get('rating') == 'good')
                satisfaction = good / total if total > 0 else 0
                
                materia_stats[materia] = {
                    'total': total,
                    'good': good,
                    'satisfaction': satisfaction
                }
        
        # Mostra solo materie con dati
        if materia_stats:
            for materia, stats in materia_stats.items():
                if stats['total'] > 0:
                    st.write(f"**{materia}**: {stats['good']}/{stats['total']} ({stats['satisfaction']:.1%})")
        else:
            st.info("Nessun dato disponibile per materia")
            
    except Exception as e:
        logger.error(f"Errore rendering materia feedback: {e}")
        st.error("Errore nel caricamento statistiche per materia")


def _render_temporal_trends(supabase_admin: Client):
    """
    Renderizza andamento temporale del feedback.
    """
    try:
        # Recupera metriche ultimi 30 giorni
        thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        
        result = supabase_admin.table('training_metrics')\
            .select('*')\
            .eq('metric_type', 'daily_satisfaction_rate')\
            .gte('date_recorded', thirty_days_ago)\
            .order('date_recorded', desc=True)\
            .limit(30)\
            .execute()
        
        if result.data:
            # Prepara dati per grafico
            dates = []
            satisfaction_rates = []
            
            for item in reversed(result.data):  # In ordine cronologico
                dates.append(item['date_recorded'])
                satisfaction_rates.append(item['metric_value'])
            
            # Grafico semplice con testo
            if dates and satisfaction_rates:
                latest_rate = satisfaction_rates[-1]
                avg_rate = sum(satisfaction_rates) / len(satisfaction_rates)
                
                st.write(f"**Tasso soddisfazione ultimi 30 giorni**: {avg_rate:.1%}")
                st.write(f"**Ultimo giorno**: {latest_rate:.1%}")
                st.write(f"**Trend**: {'📈 Miglioramento' if latest_rate > avg_rate else '📉 Calo'}")
            else:
                st.info("Nessun dato storico disponibile")
        else:
            st.info("Nessun dato storico disponibile")
            
    except Exception as e:
        logger.error(f"Errore rendering temporal trends: {e}")
        st.error("Errore nel caricamento andamento temporale")


def _render_effective_patterns(supabase_admin: Client):
    """
    Renderizza i pattern di training più efficaci.
    """
    try:
        result = supabase_admin.table('training_patterns')\
            .select('*')\
            .eq('pattern_type', 'positive')\
            .order('effectiveness_score', desc=True)\
            .limit(5)\
            .execute()
        
        if result.data:
            for i, pattern in enumerate(result.data, 1):
                score = pattern.get('effectiveness_score', 0)
                usage = pattern.get('usage_count', 0)
                materia = pattern.get('materia', 'Sconosciuta')
                livello = pattern.get('livello', 'Sconosciuto')
                
                st.write(f"**Pattern {i}** (Score: {score:.2f}, Usage: {usage})")
                st.write(f"Materia: {materia} | Livello: {livello}")
                
                # Mostra features principali
                features = pattern.get('features', {})
                if features:
                    feature_text = []
                    for key, value in features.items():
                        if isinstance(value, bool) and value:
                            feature_text.append(f"✅ {key}")
                        elif isinstance(value, (int, float)) and value > 0.5:
                            feature_text.append(f"📊 {key}: {value:.2f}")
                    
                    if feature_text:
                        st.write(" | ".join(feature_text[:3]))  # Max 3 features
                
                st.write("---")
        else:
            st.info("Nessun pattern di training disponibile")
            
    except Exception as e:
        logger.error(f"Errore rendering effective patterns: {e}")
        st.error("Errore nel caricamento pattern efficaci")


def render_training_controls(supabase_admin: Client):
    """
    Renderizza controlli admin per il sistema di training.
    """
    if not st.session_state.get('is_admin', False):
        return
    
    st.markdown("### 🎛️ Controlli Training")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Aggiorna Pattern Manualmente", key="manual_pattern_update"):
            try:
                from training_data import update_training_patterns
                success = update_training_patterns(supabase_admin)
                
                if success:
                    st.success("✅ Pattern aggiornati con successo!")
                else:
                    st.error("❌ Errore nell'aggiornamento dei pattern")
            except Exception as e:
                st.error(f"Errore: {e}")
    
    with col2:
        if st.button("🧹 Pulizia Dati Vecchi", key="cleanup_old_data"):
            try:
                # Rimuovi feedback più vecchi di 90 giorni
                cutoff_date = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
                
                result = supabase_admin.table('ai_feedback')\
                    .delete()\
                    .lt('created_at', cutoff_date)\
                    .execute()
                
                if result.data:
                    st.success(f"✅ Puliti {len(result.data)} record vecchi")
                else:
                    st.info("Nessun dato vecchio da pulire")
            except Exception as e:
                st.error(f"Errore: {e}")
    
    # Export dati training
    if st.button("📥 Esporta Dati Training", key="export_training_data"):
        try:
            # Recupera tutti i dati di training
            feedback_data = supabase_admin.table('ai_feedback')\
                .select('*')\
                .order('created_at', desc=True)\
                .limit(1000)\
                .execute()
            
            pattern_data = supabase_admin.table('training_patterns')\
                .select('*')\
                .order('effectiveness_score', desc=True)\
                .execute()
            
            # Prepara CSV export
            import csv
            import io
            
            # Feedback CSV
            feedback_csv = io.StringIO()
            if feedback_data.data:
                writer = csv.DictWriter(feedback_csv, fieldnames=['id', 'user_id', 'materia', 'livello', 'rating', 'created_at'])
                writer.writeheader()
                for item in feedback_data.data:
                    writer.writerow({
                        'id': item.get('id', ''),
                        'user_id': item.get('user_id', ''),
                        'materia': item.get('materia', ''),
                        'livello': item.get('livello', ''),
                        'rating': item.get('rating', ''),
                        'created_at': item.get('created_at', '')
                    })
            
            # Pattern CSV
            pattern_csv = io.StringIO()
            if pattern_data.data:
                writer = csv.DictWriter(pattern_csv, fieldnames=['id', 'pattern_type', 'materia', 'livello', 'confidence', 'usage_count', 'effectiveness_score'])
                writer.writeheader()
                for item in pattern_data.data:
                    writer.writerow({
                        'id': item.get('id', ''),
                        'pattern_type': item.get('pattern_type', ''),
                        'materia': item.get('materia', ''),
                        'livello': item.get('livello', ''),
                        'confidence': item.get('confidence', 0),
                        'usage_count': item.get('usage_count', 0),
                        'effectiveness_score': item.get('effectiveness_score', 0)
                    })
            
            st.success("✅ Dati esportati con successo!")
            st.download_button(
                "📥 Download Feedback CSV",
                data=feedback_csv.getvalue(),
                file_name=f"training_feedback_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
            
            st.download_button(
                "📥 Download Pattern CSV", 
                data=pattern_csv.getvalue(),
                file_name=f"training_patterns_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
            
        except Exception as e:
            st.error(f"Errore nell'esportazione: {e}")
