# ── webhooks.py ───────────────────────────────────────────────────────────────────
# Gestione webhook Stripe per eventi di pagamento e abbonamenti
# ───────────────────────────────────────────────────────────────────────────────

import streamlit as st
import logging
from typing import Dict, Any
from supabase import Client

from payments import handle_webhook_event
from subscription_management import get_subscription_manager

# Configurazione logger
logger = logging.getLogger(__name__)


def handle_stripe_webhook(request_data: Dict[str, Any], supabase: Client) -> Dict[str, Any]:
    """
    Gestisce webhook events da Stripe e aggiorna database.
    
    Args:
        request_data: Dati della richiesta (body, headers, etc.)
        supabase: Client Supabase
        
    Returns:
        Dict con risultato elaborazione
    """
    try:
        # Estrai payload e signature
        payload = request_data.get('body', '')
        sig_header = request_data.get('headers', {}).get('stripe-signature', '')
        
        if not payload or not sig_header:
            logger.error("Webhook mancante: payload o signature")
            return {
                'success': False,
                'error': 'Dati webhook incompleti',
                'status_code': 400
            }
        
        # Processa evento con Stripe
        result = handle_webhook_event(payload, sig_header)
        
        if not result['success']:
            logger.error(f"Errore elaborazione webhook: {result.get('error')}")
            return {
                'success': False,
                'error': result.get('error'),
                'status_code': 400
            }
        
        # Gestisci eventi specifici
        event_type = result.get('event')
        subscription_manager = get_subscription_manager(supabase)
        
        if event_type == 'checkout.completed':
            return _handle_checkout_completed_webhook(result, subscription_manager)
        elif event_type == 'payment.succeeded':
            return _handle_payment_succeeded_webhook(result, subscription_manager)
        elif event_type == 'payment.failed':
            return _handle_payment_failed_webhook(result, subscription_manager)
        elif event_type == 'subscription.deleted':
            return _handle_subscription_deleted_webhook(result, subscription_manager)
        elif event_type == 'subscription.updated':
            return _handle_subscription_updated_webhook(result, subscription_manager)
        else:
            logger.info(f"Evento webhook non gestito: {event_type}")
            return {
                'success': True,
                'message': f'Evento {event_type} ricevuto ma non gestito',
                'status_code': 200
            }
    
    except Exception as e:
        logger.error(f"Errore critico webhook: {e}")
        return {
            'success': False,
            'error': 'Errore interno server',
            'status_code': 500
        }


def _handle_checkout_completed_webhook(result: Dict[str, Any], 
                                   subscription_manager) -> Dict[str, Any]:
    """Gestisce webhook checkout completato"""
    user_id = result.get('user_id')
    plan_id = result.get('plan_id')
    subscription_id = result.get('subscription_id')
    
    if not all([user_id, plan_id, subscription_id]):
        logger.error("Dati incompleti in checkout.completed webhook")
        return {
            'success': False,
            'error': 'Dati incompleti',
            'status_code': 400
        }
    
    # Crea abbonamento nel database
    success = subscription_manager.create_subscription(
        user_id=user_id,
        stripe_subscription_id=subscription_id,
        plan_id=plan_id,
        status='active'
    )
    
    if success:
        logger.info(f"Abbonamento creato da webhook: utente {user_id}, piano {plan_id}")
        return {
            'success': True,
            'message': 'Abbonamento creato con successo',
            'status_code': 200
        }
    else:
        logger.error(f"Errore creazione abbonamento da webhook: utente {user_id}")
        return {
            'success': False,
            'error': 'Errore creazione abbonamento',
            'status_code': 500
        }


def _handle_payment_succeeded_webhook(result: Dict[str, Any], 
                                  subscription_manager) -> Dict[str, Any]:
    """Gestisce webhook pagamento riuscito"""
    subscription_id = result.get('subscription_id')
    
    if not subscription_id:
        logger.error("subscription_id mancante in payment.succeeded webhook")
        return {
            'success': False,
            'error': 'Dati incompleti',
            'status_code': 400
        }
    
    # Aggiorna stato abbonamento
    success = subscription_manager.update_subscription_status(
        stripe_subscription_id=subscription_id,
        status='active'
    )
    
    if success:
        logger.info(f"Stato abbonamento aggiornato da webhook: {subscription_id}")
        return {
            'success': True,
            'message': 'Pagamento processato con successo',
            'status_code': 200
        }
    else:
        logger.error(f"Errore aggiornamento abbonamento da webhook: {subscription_id}")
        return {
            'success': False,
            'error': 'Errore aggiornamento abbonamento',
            'status_code': 500
        }


def _handle_payment_failed_webhook(result: Dict[str, Any], 
                               subscription_manager) -> Dict[str, Any]:
    """Gestisce webhook pagamento fallito"""
    subscription_id = result.get('subscription_id')
    
    if not subscription_id:
        logger.error("subscription_id mancante in payment.failed webhook")
        return {
            'success': False,
            'error': 'Dati incompleti',
            'status_code': 400
        }
    
    # Aggiorna stato abbonamento
    success = subscription_manager.update_subscription_status(
        stripe_subscription_id=subscription_id,
        status='past_due'
    )
    
    if success:
        logger.warning(f"Pagamento fallito registrato: {subscription_id}")
        # TODO: Inviare notifica email all'utente
        return {
            'success': True,
            'message': 'Fallimento pagamento registrato',
            'status_code': 200
        }
    else:
        logger.error(f"Errore registrazione fallimento pagamento: {subscription_id}")
        return {
            'success': False,
            'error': 'Errore registrazione fallimento',
            'status_code': 500
        }


def _handle_subscription_deleted_webhook(result: Dict[str, Any], 
                                    subscription_manager) -> Dict[str, Any]:
    """Gestisce webhook cancellazione abbonamento"""
    subscription_id = result.get('subscription_id')
    user_id = result.get('user_id')
    
    if not subscription_id:
        logger.error("subscription_id mancante in subscription.deleted webhook")
        return {
            'success': False,
            'error': 'Dati incompleti',
            'status_code': 400
        }
    
    # Elimina abbonamento dal database
    success = subscription_manager.delete_subscription(subscription_id)
    
    if success:
        logger.info(f"Abbonamento eliminato da webhook: {subscription_id}")
        # TODO: Inviare email di conferma cancellazione
        return {
            'success': True,
            'message': 'Abbonamento cancellato con successo',
            'status_code': 200
        }
    else:
        logger.error(f"Errore eliminazione abbonamento da webhook: {subscription_id}")
        return {
            'success': False,
            'error': 'Errore eliminazione abbonamento',
            'status_code': 500
        }


def _handle_subscription_updated_webhook(result: Dict[str, Any], 
                                    subscription_manager) -> Dict[str, Any]:
    """Gestisce webhook aggiornamento abbonamento"""
    subscription_id = result.get('subscription_id')
    status = result.get('status')
    
    if not subscription_id or not status:
        logger.error("Dati incompleti in subscription.updated webhook")
        return {
            'success': False,
            'error': 'Dati incompleti',
            'status_code': 400
        }
    
    # Aggiorna stato abbonamento
    success = subscription_manager.update_subscription_status(
        stripe_subscription_id=subscription_id,
        status=status
    )
    
    if success:
        logger.info(f"Abbonamento aggiornato da webhook: {subscription_id} → {status}")
        return {
            'success': True,
            'message': 'Abbonamento aggiornato con successo',
            'status_code': 200
        }
    else:
        logger.error(f"Errore aggiornamento abbonamento da webhook: {subscription_id}")
        return {
            'success': False,
            'error': 'Errore aggiornamento abbonamento',
            'status_code': 500
        }


def create_webhook_endpoint():
    """
    Crea endpoint Streamlit per webhook Stripe.
    Da chiamare in main.py con @st.cache_data.
    """
    if st.secrets.get("STRIPE_WEBHOOK_SECRET"):
        return True
    else:
        logger.warning("Webhook Stripe non configurato - STRIPE_WEBHOOK_SECRET mancante")
        return False


def validate_webhook_request(request) -> bool:
    """
    Valida che la richiesta webhook provenga da Stripe.
    
    Args:
        request: Oggetto richiesta Streamlit
        
    Returns:
        True se valida, False altrimenti
    """
    # Verifica content-type
    content_type = request.headers.get('content-type', '')
    if 'application/json' not in content_type:
        logger.error(f"Content-type non valido: {content_type}")
        return False
    
    # Verifica signature header
    sig_header = request.headers.get('stripe-signature')
    if not sig_header:
        logger.error("Stripe signature header mancante")
        return False
    
    return True
