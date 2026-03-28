# ── payments.py ──────────────────────────────────────────────────────────────────
# Gestione pagamenti e abbonamenti Stripe per VerificAI
# ───────────────────────────────────────────────────────────────────────────────

import os
import stripe
import streamlit as st
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from config import STRIPE_PLANS

# Configurazione logger
logger = logging.getLogger(__name__)

# Inizializza Stripe
try:
    STRIPE_SECRET_KEY = st.secrets.get("STRIPE_SECRET_KEY", os.getenv("STRIPE_SECRET_KEY"))
    STRIPE_PUBLISHABLE_KEY = st.secrets.get("STRIPE_PUBLISHABLE_KEY", os.getenv("STRIPE_PUBLISHABLE_KEY"))
    STRIPE_WEBHOOK_SECRET = st.secrets.get("STRIPE_WEBHOOK_SECRET", os.getenv("STRIPE_WEBHOOK_SECRET"))
    
    # Debug: mostra stato chiavi (solo in development)
    logger.info(f"Stripe keys check - Secret: {'✓' if STRIPE_SECRET_KEY else '✗'}, Publishable: {'✓' if STRIPE_PUBLISHABLE_KEY else '✗'}")
    logger.info(f"Secret key preview: {STRIPE_SECRET_KEY[:10]}..." if STRIPE_SECRET_KEY else "No secret key")
    logger.info(f"Publishable key preview: {STRIPE_PUBLISHABLE_KEY[:10]}..." if STRIPE_PUBLISHABLE_KEY else "No publishable key")
    
    if STRIPE_SECRET_KEY:
        stripe.api_key = STRIPE_SECRET_KEY
        STRIPE_ENABLED = True
        logger.info("Stripe inizializzato correttamente")
    else:
        STRIPE_ENABLED = False
        logger.warning("Stripe non configurato - chiavi API mancanti")
        
except Exception as e:
    STRIPE_ENABLED = False
    logger.error(f"Errore inizializzazione Stripe: {e}")


def create_checkout_session(user_id: str, plan_id: str, success_url: str, cancel_url: str, user_email: str = None) -> Optional[Dict[str, Any]]:
    """
    Crea una sessione di checkout Stripe per l'upgrade del piano.
    
    Args:
        user_id: ID utente Supabase
        plan_id: ID del piano ('pro' o 'premium')
        success_url: URL di redirect dopo pagamento successo
        cancel_url: URL di redirect se utente cancella
        user_email: Email utente (opzionale)
        
    Returns:
        Dict con session_id e checkout_url, o None se errore
    """
    if not STRIPE_ENABLED:
        logger.error("Stripe non abilitato - impossibile creare checkout session")
        return None
        
    if plan_id not in STRIPE_PLANS:
        logger.error(f"Piano non valido: {plan_id}")
        return None
        
    try:
        logger.info(f"Creazione checkout session per user_id: {user_id}, plan: {plan_id}")
        
        plan_config = STRIPE_PLANS[plan_id]
        
        # Crea o recupera cliente Stripe
        from subscription_management import get_subscription_manager
        import os
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
        
        if supabase_url and supabase_key:
            from supabase import create_client
            supabase = create_client(supabase_url, supabase_key)
            subscription_manager = get_subscription_manager(supabase)
            customer_id = subscription_manager.get_or_create_stripe_customer(user_id, user_email or "")
        else:
            customer_id = None
        
        logger.info(f"Cliente Stripe: {customer_id}")
        
        # Verifica che il price_id sia configurato
        price_id = plan_config.get("price_id")
        
        if not price_id:
            logger.error(f"Price_id non configurato per il piano {plan_id}")
            return None
        
        logger.info(f"Price ID: {price_id}")
        
        # Crea sessione checkout
        checkout_session_data = {
            'payment_method_types': ['card'],
            'line_items': [{
                'price': price_id,
                'quantity': 1,
            }],
            'mode': 'subscription',
            'success_url': success_url,
            'cancel_url': cancel_url,
            'client_reference_id': user_id,
            'metadata': {
                'plan_id': plan_id,
                'user_id': user_id,
                'app': 'verificai'
            },
            'subscription_data': {
                'metadata': {
                    'plan_id': plan_id,
                    'user_id': user_id,
                    'app': 'verificai'
                }
            }
        }
        
        logger.info(f"Parametri sessione: {checkout_session_data}")
        
        # Aggiungi customer_id se disponibile
        if customer_id:
            checkout_session_data['customer'] = customer_id
            checkout_session_data['customer_email'] = None  # Non necessario se customer specificato
        elif user_email:
            checkout_session_data['customer_email'] = user_email
        
        checkout_session = stripe.checkout.Session.create(**checkout_session_data)
        
        logger.info(f"Checkout session creata: {checkout_session.id} per utente {user_id}, piano {plan_id}")
        
        return {
            'session_id': checkout_session.id,
            'checkout_url': checkout_session.url
        }
        
    except stripe.error.StripeError as e:
        logger.error(f"Errore Stripe creazione checkout: {e}")
        return None
    except Exception as e:
        logger.error(f"Errore generico creazione checkout: {e}")
        return None


def create_customer_portal_session(customer_id: str, return_url: str) -> Optional[str]:
    """
    Crea una sessione per il Customer Portal Stripe.
    
    Args:
        customer_id: ID cliente Stripe
        return_url: URL di ritorno dopo gestione abbonamento
        
    Returns:
        URL del customer portal o None se errore
    """
    if not STRIPE_ENABLED:
        return None
        
    try:
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )
        
        logger.info(f"Customer portal session creata: {session.id}")
        return session.url
        
    except stripe.error.StripeError as e:
        logger.error(f"Errore Stripe customer portal: {e}")
        return None
    except Exception as e:
        logger.error(f"Errore generico customer portal: {e}")
        return None


def cancel_subscription(subscription_id: str) -> bool:
    """
    Cancella un abbonamento Stripe alla fine del periodo corrente.
    
    Args:
        subscription_id: ID abbonamento Stripe
        
    Returns:
        True se successo, False altrimenti
    """
    if not STRIPE_ENABLED:
        return False
        
    try:
        stripe.Subscription.modify(
            subscription_id,
            cancel_at_period_end=True
        )
        
        logger.info(f"Abbonamento {subscription_id} impostato per cancellazione fine periodo")
        return True
        
    except stripe.error.StripeError as e:
        logger.error(f"Errore Stripe cancellazione abbonamento: {e}")
        return False
    except Exception as e:
        logger.error(f"Errore generico cancellazione abbonamento: {e}")
        return False


def get_subscription_status(subscription_id: str) -> Optional[Dict[str, Any]]:
    """
    Recupera lo stato di un abbonamento Stripe.
    
    Args:
        subscription_id: ID abbonamento Stripe
        
    Returns:
        Dict con stato abbonamento o None se errore
    """
    if not STRIPE_ENABLED:
        return None
        
    try:
        subscription = stripe.Subscription.retrieve(subscription_id)
        
        return {
            'id': subscription.id,
            'status': subscription.status,
            'current_period_end': subscription.current_period_end,
            'cancel_at_period_end': subscription.cancel_at_period_end,
            'plan_id': subscription.metadata.get('plan_id'),
            'user_id': subscription.metadata.get('user_id')
        }
        
    except stripe.error.StripeError as e:
        logger.error(f"Errore Stripe recupero stato abbonamento: {e}")
        return None
    except Exception as e:
        logger.error(f"Errore generico recupero stato abbonamento: {e}")
        return None


def handle_webhook_event(payload: str, sig_header: str) -> Dict[str, Any]:
    """
    Processa webhook events da Stripe.
    
    Args:
        payload: Body della richiesta webhook
        sig_header: Header Stripe signature
        
    Returns:
        Dict con risultato elaborazione
    """
    if not STRIPE_ENABLED:
        return {'success': False, 'error': 'Stripe non abilitato'}
        
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
        
        logger.info(f"Webhook ricevuto: {event.type}")
        
        # Gestione eventi principali
        if event.type == 'checkout.session.completed':
            return _handle_checkout_completed(event.data.object)
        elif event.type == 'invoice.payment_succeeded':
            return _handle_payment_succeeded(event.data.object)
        elif event.type == 'invoice.payment_failed':
            return _handle_payment_failed(event.data.object)
        elif event.type == 'customer.subscription.deleted':
            return _handle_subscription_deleted(event.data.object)
        elif event.type == 'customer.subscription.updated':
            return _handle_subscription_updated(event.data.object)
        else:
            logger.info(f"Evento non gestito: {event.type}")
            return {'success': True, 'event': event.type}
            
    except stripe.error.SignatureVerificationError:
        logger.error("Firma webhook non valida")
        return {'success': False, 'error': 'Firma non valida'}
    except Exception as e:
        logger.error(f"Errore elaborazione webhook: {e}")
        return {'success': False, 'error': str(e)}


def _handle_checkout_completed(checkout_session: Dict[str, Any]) -> Dict[str, Any]:
    """Gestisce completamento checkout"""
    user_id = checkout_session.get('client_reference_id')
    subscription_id = checkout_session.get('subscription')
    plan_id = checkout_session.get('metadata', {}).get('plan_id')
    
    logger.info(f"Checkout completato: utente {user_id}, piano {plan_id}, sub {subscription_id}")
    
    # TODO: Salvare in database Supabase
    # _save_subscription_to_db(user_id, subscription_id, plan_id)
    
    return {
        'success': True,
        'event': 'checkout.completed',
        'user_id': user_id,
        'plan_id': plan_id,
        'subscription_id': subscription_id
    }


def _handle_payment_succeeded(invoice: Dict[str, Any]) -> Dict[str, Any]:
    """Gestisce pagamento riuscito"""
    subscription_id = invoice.get('subscription')
    logger.info(f"Pagamento riuscito per abbonamento {subscription_id}")
    
    # TODO: Aggiornare stato in database
    # _update_subscription_status(subscription_id, 'active')
    
    return {
        'success': True,
        'event': 'payment.succeeded',
        'subscription_id': subscription_id
    }


def _handle_payment_failed(invoice: Dict[str, Any]) -> Dict[str, Any]:
    """Gestisce pagamento fallito"""
    subscription_id = invoice.get('subscription')
    logger.warning(f"Pagamento fallito per abbonamento {subscription_id}")
    
    # TODO: Notificare utente e aggiornare database
    # _notify_payment_failed(user_id, subscription_id)
    
    return {
        'success': True,
        'event': 'payment.failed',
        'subscription_id': subscription_id
    }


def _handle_subscription_deleted(subscription: Dict[str, Any]) -> Dict[str, Any]:
    """Gestisce cancellazione abbonamento"""
    subscription_id = subscription.get('id')
    user_id = subscription.get('metadata', {}).get('user_id')
    
    logger.info(f"Abbonamento cancellato: {subscription_id}, utente {user_id}")
    
    # TODO: Aggiornare database a piano free
    # _downgrade_user_to_free(user_id)
    
    return {
        'success': True,
        'event': 'subscription.deleted',
        'subscription_id': subscription_id,
        'user_id': user_id
    }


def _handle_subscription_updated(subscription: Dict[str, Any]) -> Dict[str, Any]:
    """Gestisce aggiornamento abbonamento"""
    subscription_id = subscription.get('id')
    status = subscription.get('status')
    
    logger.info(f"Abbonamento aggiornato: {subscription_id}, status {status}")
    
    # TODO: Aggiornare stato in database
    # _update_subscription_status(subscription_id, status)
    
    return {
        'success': True,
        'event': 'subscription.updated',
        'subscription_id': subscription_id,
        'status': status
    }


def get_stripe_publishable_key() -> Optional[str]:
    """Restituisce la chiave publishable Stripe"""
    return STRIPE_PUBLISHABLE_KEY if STRIPE_ENABLED else None


def is_stripe_enabled() -> bool:
    """Verifica se Stripe è configurato e abilitato"""
    return STRIPE_ENABLED
