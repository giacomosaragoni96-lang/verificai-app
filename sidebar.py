"""
Sidebar funzionante - versione ripristinata e stabile
Ripristinata da commit precedente senza modifiche Stripe
"""

import streamlit as st
import logging
from config import LIMITE_MENSILE, ADMIN_EMAILS

logger = logging.getLogger(__name__)

def render_sidebar(supabase_admin, utente, verifiche_mese_count):
    """Renderizza la sidebar principale con utente, stats e CTA upgrade"""
    
    # Utente e stats cards
    email_utente = utente.email or ""
    iniziale     = email_utente[0].upper() if email_utente else "?"
    
    _piano_label = {
        "admin": "Admin",
        "gold": "Piano Gold",
        "pro":   "Piano Pro",
    }.get(utente.piano if utente else "free", "Piano gratuito")
    
    _piano_icon = {
        "admin": "⚙️",
        "gold": "🌟",
        "pro":   "⚡",
    }.get(utente.piano if utente else "free", "🎓")
    
    # Stats cards semplici
    try:
        if utente is not None and supabase_admin is not None:
            storico_count = (
                supabase_admin.table("verifiche_storico")
                .select("id", count="exact")
                .eq("user_id", utente.id)
                .is_("deleted_at", "null")
                .execute()
            )
            total_verifiche = storico_count.count if storico_count else 0
        else:
            total_verifiche = 0
    except:
        total_verifiche = 0
    
    # Card info-only (nessun onclick — la navigazione è gestita dal pulsante sotto)
    st.markdown(f'''
    <div class="sb-pro-card" style="
        background: linear-gradient(#6366f115, transparent);
        border: 1px solid #6366f144;
        padding: 1rem;
        border-radius: 12px;
        margin-bottom: 0.5rem;
    ">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.5rem;">
            <div style="font-size: 1rem; font-weight: 600; color: #e5e7eb;">
                📚 Le mie verifiche
            </div>
            <div style="background: #6366f1; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.8rem; font-weight: 700;">
                {total_verifiche}
            </div>
        </div>
    </div>
    ''', unsafe_allow_html=True)
    
    if st.button("📄 Apri Storico Completo", key="open_storico", use_container_width=True, type="secondary"):
        st.session_state.stage = "MIE_VERIFICHE"
        st.rerun()
    
    st.markdown('<div class="logout-btn-wrap">', unsafe_allow_html=True)
    if st.button("↩ Esci dall'account", key="logout_btn"):
        from auth import cancella_sessione_cookie
        cancella_sessione_cookie()
        supabase_client.auth.sign_out()
        st.session_state.utente          = None
        st.session_state.supabase       = None
        st.session_state.stage          = "INPUT"
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Validation score tracking
    if hasattr(st.session_state, 'last_validation_score'):
        last_score = st.session_state.last_validation_score
        st.metric("🎯 Ultimo Score", f"{last_score:.2f}", 
                 "Buono" if last_score > 0.7 else "Da migliorare")
    
    # Performance monitoring (Admin only)
    if utente and utente.email in ADMIN_EMAILS and hasattr(st.session_state, 'quality_stats'):
        st.markdown("---")
        st.markdown("### 📊 Qualità Generazione")
        
        stats = st.session_state.quality_stats
        total = sum(stats.values())
        
        if total > 0:
            # Quality metrics
            excellent_rate = stats.get('excellent', 0) / total * 100
            good_rate = stats.get('good', 0) / total * 100
            poor_rate = stats.get('poor', 0) / total * 100
            
            st.metric("📈 Tasso Successo", f"{excellent_rate + good_rate:.1f}%", 
                     f"+{excellent_rate:.1f}% eccellente")
            
            # Visual quality bar
            quality_data = [
                ("👍 Ottima", stats.get('excellent', 0), "#059669"),
                ("👍 Buona", stats.get('good', 0), "#22c55e"), 
                ("😐 Sufficiente", stats.get('sufficient', 0), "#f59e0b"),
                ("👎 Insufficiente", stats.get('poor', 0), "#ef4444")
            ]
            
            for label, count, color in quality_data:
                if count > 0:
                    percentage = count / total * 100
                    st.markdown(f'''
                    <div style="display: flex; justify-content: space-between; align-items: center; margin: 0.2rem 0;">
                        <span style="font-size: 0.8rem;">{label}</span>
                        <span style="font-size: 0.8rem; font-weight: 600;">{count} ({percentage:.0f}%)</span>
                    </div>
                    <div style="background: #e5e7eb; border-radius: 4px; height: 6px; margin: 2px 0;">
                        <div style="background: {color}; width: {percentage}%; height: 100%; border-radius: 4px;"></div>
                    </div>
                    ''', unsafe_allow_html=True)
    
    return {
        "modello_id": "gemini-2.5-flash-lite",
        "theme_changed": False
    }
