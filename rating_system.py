# ── rating_system.py ───────────────────────────────────────────────────────────
# Sistema di rating silenzioso per verifiche generate
# ───────────────────────────────────────────────────────────────────────────────

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional
import streamlit as st
from supabase import Client

logger = logging.getLogger("verificai.rating")


def render_feedback_buttons(supabase_admin: Client, user_id: str, 
                          verifica_content: str, materia: str, livello: str,
                          key_prefix: str = "feedback") -> None:
    """
    Renderizza pulsanti di feedback semplici e silenziosi.
    """
    # Genera ID univoco per questa verifica
    verifica_id = f"{key_prefix}_{uuid.uuid4().hex[:8]}"
    
    # Salva temporaneamente il contenuto per feedback
    if 'pending_feedback' not in st.session_state:
        st.session_state.pending_feedback = {}
    
    st.session_state.pending_feedback[verifica_id] = {
        'content': verifica_content,
        'materia': materia,
        'livello': livello
    }
    
    # Layout pulsanti
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("👍 Buono", key=f"good_{verifica_id}", use_container_width=True):
            if _save_feedback_rating(supabase_admin, user_id, verifica_id, 'good'):
                st.success("✅ Grazie per il feedback!")
                st.balloons()
            else:
                st.error("❌ Errore nel salvataggio")
            st.rerun()
    
    with col2:
        if st.button("👎 Non buono", key=f"bad_{verifica_id}", use_container_width=True):
            if _save_feedback_rating(supabase_admin, user_id, verifica_id, 'bad'):
                st.success("✅ Grazie per il feedback!")
            else:
                st.error("❌ Errore nel salvataggio")
            st.rerun()
    
    with col3:
        st.markdown("<small style='color: #666; line-height: 2.5;'>Aiutaci a migliorare</small>", 
                   unsafe_allow_html=True)


def _save_feedback_rating(supabase_admin: Client, user_id: str, 
                        verifica_id: str, rating: str) -> bool:
    """
    Salva rating di feedback nel database.
    """
    try:
        from training_data import save_feedback
        
        # Recupera dati pending
        pending = st.session_state.get('pending_feedback', {})
        if verifica_id not in pending:
            logger.error(f"Nessun dato pending per verifica_id: {verifica_id}")
            return False
        
        data = pending[verifica_id]
        
        # Salva feedback
        success = save_feedback(
            supabase_admin=supabase_admin,
            user_id=user_id,
            verifica_content=data['content'],
            rating=rating,
            materia=data['materia'],
            livello=data['livello']
        )
        
        if success:
            # Rimuovi dai pending
            del st.session_state.pending_feedback[verifica_id]
            
            # Aggiorna stats utente
            _update_user_feedback_stats(user_id, rating)
        
        return success
        
    except Exception as e:
        logger.error(f"Errore salvataggio rating: {e}")
        return False


def _update_user_feedback_stats(user_id: str, rating: str) -> None:
    """
    Aggiorna statistiche feedback utente in session state.
    """
    try:
        if 'quality_stats' not in st.session_state:
            st.session_state.quality_stats = {'excellent': 0, 'good': 0, 'sufficient': 0, 'poor': 0}
        
        # Mappa rating a categorie esistenti
        if rating == 'good':
            st.session_state.quality_stats['excellent'] += 1
        else:  # 'bad'
            st.session_state.quality_stats['poor'] += 1
            
    except Exception as e:
        logger.warning(f"Errore aggiornamento stats: {e}")


def get_feedback_summary(supabase_admin: Client, user_id: Optional[str] = None) -> dict:
    """
    Recupera riassunto feedback per analytics interne.
    """
    try:
        query = supabase_admin.table('ai_feedback').select('*')
        
        if user_id:
            query = query.eq('user_id', user_id)
        
        result = query.execute()
        
        if not result.data:
            return {'total': 0, 'good': 0, 'bad': 0, 'rate': 0.0}
        
        total = len(result.data)
        good = sum(1 for item in result.data if item.get('rating') == 'good')
        bad = total - good
        rate = good / total if total > 0 else 0.0
        
        return {
            'total': total,
            'good': good,
            'bad': bad,
            'rate': rate
        }
        
    except Exception as e:
        logger.error(f"Errore recupero summary: {e}")
        return {'total': 0, 'good': 0, 'bad': 0, 'rate': 0.0}


def render_feedback_stats_admin(supabase_admin: Client) -> None:
    """
    Renderizza statistiche feedback per admin (interne).
    """
    try:
        # Stats generali
        general_stats = get_feedback_summary(supabase_admin)
        
        # Stats per materia
        materia_stats = {}
        materie = ['Matematica', 'Fisica', 'Italiano', 'Storia', 'Geografia', 'Chimica']
        
        for materia in materie:
            result = supabase_admin.table('ai_feedback')\
                .select('rating')\
                .eq('materia', materia)\
                .execute()
            
            if result.data:
                total = len(result.data)
                good = sum(1 for item in result.data if item.get('rating') == 'good')
                materia_stats[materia] = {
                    'total': total,
                    'good': good,
                    'rate': good / total if total > 0 else 0.0
                }
        
        # Display stats (solo per admin)
        if st.session_state.get('is_admin', False):
            st.markdown("### 📊 Training Analytics (Admin Only)")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Feedback Totali", general_stats['total'])
            with col2:
                st.metric("Feedback Positivi", general_stats['good'])
            with col3:
                st.metric("Tasso Positività", f"{general_stats['rate']:.1%}")
            
            # Stats per materia
            if materia_stats:
                st.markdown("#### 📈 Feedback per Materia")
                for materia, stats in materia_stats.items():
                    if stats['total'] > 0:
                        st.write(f"**{materia}**: {stats['good']}/{stats['total']} ({stats['rate']:.1%})")
        
    except Exception as e:
        logger.error(f"Errore rendering stats admin: {e}")


def has_user_given_feedback_today(supabase_admin: Client, user_id: str) -> bool:
    """
    Controlla se utente ha già dato feedback oggi.
    """
    try:
        from datetime import timedelta
        
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        result = supabase_admin.table('ai_feedback')\
            .select('created_at')\
            .eq('user_id', user_id)\
            .gte('created_at', today.isoformat())\
            .limit(1)\
            .execute()
        
        return len(result.data) > 0
        
    except Exception as e:
        logger.error(f"Errore controllo feedback oggi: {e}")
        return False


def should_show_feedback_prompt(supabase_admin: Client, user_id: str) -> bool:
    """
    Determina se mostrare prompt feedback (limita frequenza).
    """
    try:
        # Mostra solo se non ha dato feedback oggi
        if has_user_given_feedback_today(supabase_admin, user_id):
            return False
        
        # Mostra solo se ha generato almeno 2 verifiche oggi
        from datetime import timedelta
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        
        result = supabase_admin.table('verifiche_storico')\
            .select('created_at')\
            .eq('user_id', user_id)\
            .gte('created_at', today.isoformat())\
            .execute()
        
        return len(result.data) >= 2
        
    except Exception as e:
        logger.error(f"Errore determinazione show feedback: {e}")
        return True  # Default: mostra


def render_feedback_prompt(supabase_admin: Client, user_id: str) -> None:
    """
    Renderizza prompt per feedback se appropriato.
    """
    if should_show_feedback_prompt(supabase_admin, user_id):
        st.info("💡 **Aiutaci a migliorare!** Valuta la qualità di questa verifica con i pulsanti sottostanti.")
