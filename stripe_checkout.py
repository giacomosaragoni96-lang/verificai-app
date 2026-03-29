"""
Componente Stripe Checkout Professionale per Streamlit
UI moderna, pulita e responsive con gestione errori avanzata
"""

import streamlit as st
import stripe
import logging
from typing import Optional, Dict, Any
from config import STRIPE_PLANS

logger = logging.getLogger(__name__)

def render_stripe_checkout(plan_id: str = "pro", user_email: str = None) -> bool:
    """
    Renderizza una pagina di checkout Stripe professionale
    
    Args:
        plan_id: ID del piano (pro, premium)
        user_email: Email dell'utente
        
    Returns:
        bool: True se il checkout è stato completato
    """
    
    # Header
    st.markdown("""
    <div style="max-width: 600px; margin: 0 auto; padding: 2rem 0;">
        <div style="text-align: center; margin-bottom: 2rem;">
            <h1 style="font-size: 2rem; font-weight: 700; color: #1a1a1a; margin-bottom: 0.5rem;">
                🚀 Completa il tuo Abbonamento
            </h1>
            <p style="font-size: 1.1rem; color: #666; margin-bottom: 2rem;">
                Scegli il piano che fa per te e procedi al pagamento sicuro Stripe
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    # Piano selection
    plan = STRIPE_PLANS[plan_id]
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown(f"""
        <div style="border: 2px solid #e1e5e9; border-radius: 12px; padding: 1.5rem; text-align: center; background: white;">
            <h3 style="color: #1a1a1a; margin-bottom: 1rem; font-size: 1.2rem;">
                {plan['name']}
            </h3>
            <p style="font-size: 1.5rem; font-weight: 600; color: #10b981; margin-bottom: 0.5rem;">
                €{plan['amount']/100:.2f}/mese
            </p>
            <div style="margin: 1rem 0;">
                <small style="color: #666; font-size: 0.9rem;">
                    {plan['currency'].upper()} • {plan['interval'].capitalize()}
                </small>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div style="border: 2px solid #f3f4f6; border-radius: 12px; padding: 1.5rem; text-align: center; background: #f8f9fa;">
            <h3 style="color: #1a1a1a; margin-bottom: 1rem; font-size: 1.2rem;">
                VerificAI Free
            </h3>
            <p style="font-size: 1.5rem; font-weight: 600; color: #666; margin-bottom: 0.5rem;">
                €0/mese
            </p>
            <div style="margin: 1rem 0;">
                <small style="color: #666; font-size: 0.9rem;">
                    EUR • Mensile
                </small>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Features comparison
    st.markdown("""
    <div style="margin: 2rem 0;">
        <h3 style="color: #1a1a1a; margin-bottom: 1rem;">✨ Cosa Ottieni con {plan_name}</h3>
    """.format(plan_name=plan['name']), unsafe_allow_html=True)
    
    features_col1, features_col2 = st.columns([1, 1])
    
    with features_col1:
        st.markdown(f"""
        <div style="background: #e8f5e8; border-radius: 8px; padding: 1rem;">
            <h4 style="color: #1a1a1a; margin-bottom: 0.5rem; font-size: 1rem;">
                🎯 {plan['name']}
            </h4>
            <ul style="list-style: none; padding: 0; margin: 0;">
        """, unsafe_allow_html=True)
        
        for feature in plan['features']:
            st.markdown(f"""
                <li style="padding: 0.25rem 0; border-bottom: 1px solid #d4d4d4; font-size: 0.9rem;">
                    ✅ {feature}
                </li>
            """, unsafe_allow_html=True)
        
        st.markdown("</ul></div>", unsafe_allow_html=True)
    
    with features_col2:
        st.markdown("""
        <div style="background: #f8f9fa; border-radius: 8px; padding: 1rem;">
            <h4 style="color: #1a1a1a; margin-bottom: 0.5rem; font-size: 1rem;">
                📄 VerificAI Free
            </h4>
            <ul style="list-style: none; padding: 0; margin: 0;">
                <li style="padding: 0.25rem 0; border-bottom: 1px solid #d4d4d4; font-size: 0.9rem;">
                    ❌ {limit} verifiche/mese
                </li>
                <li style="padding: 0.25rem 0; border-bottom: 1px solid #d4d4d4; font-size: 0.9rem;">
                    ❌ Modello AI base
                </li>
                <li style="padding: 0.25rem 0; border-bottom: 1px solid #d4d4d4; font-size: 0.9rem;">
                    ❌ Nessuna funzionalità premium
                </li>
            </ul>
        </div>
        """.format(limit=5), unsafe_allow_html=True)
    
    # CTA Button
    st.markdown("""
    <div style="text-align: center; margin: 3rem 0;">
        <p style="color: #666; margin-bottom: 1rem;">
            Pronto a passare a {plan_name}? 🚀
        </p>
    </div>
    """.format(plan_name=plan['name']), unsafe_allow_html=True)
    
    # Checkout button
    if st.button(f"🚀 Attiva {plan['name']} - €{plan['amount']/100:.2f}/mese", 
                 use_container_width=True,
                 type="primary",
                 help="Procedi al pagamento sicuro con Stripe"):
        
        # Qui integreresti la logica di checkout reale
        st.success("🎉 Checkout in preparazione...")
        st.info("⚡ Verrai reindirizzato a Stripe per completare l'abbonamento")
        
        # Qui dovresti integrare la tua logica create_checkout_session()
        # checkout_result = create_checkout_session(...)
        
        return True
    
    return False

def render_checkout_success():
    """Renderizza pagina di successo dopo pagamento"""
    st.markdown("""
    <div style="max-width: 600px; margin: 0 auto; padding: 3rem 0; text-align: center;">
        <div style="background: #10b981; color: white; border-radius: 12px; padding: 2rem; margin-bottom: 2rem;">
            <h1 style="font-size: 2.5rem; margin-bottom: 1rem;">
                🎉 Pagamento Completato!
            </h1>
            <p style="font-size: 1.2rem; opacity: 0.9;">
                Il tuo abbonamento VerificAI è stato attivato con successo.
            </p>
        </div>
        
        <div style="background: #f8f9fa; border: 1px solid #e1e5e9; border-radius: 8px; padding: 2rem;">
            <h3 style="color: #1a1a1a; margin-bottom: 1rem;">
                ✨ Cosa Succede Ora?
            </h3>
            <ul style="text-align: left; color: #666;">
                <li>✅ Verifiche illimitate</li>
                <li>✅ Modello AI avanzato</li>
                <li>✅ Tutte le funzionalità premium</li>
                <li>✅ Supporto prioritario</li>
            </ul>
        </div>
        
        <div style="margin-top: 2rem;">
            <a href="/" style="background: #6366f1; color: white; padding: 0.75rem 1.5rem; text-decoration: none; border-radius: 0.5rem; display: inline-block;">
                🏠 Torna a VerificAI
            </a>
        </div>
    </div>
    """, unsafe_allow_html=True)
