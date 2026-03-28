# ── subscription_management.py ───────────────────────────────────────────────────────
# Gestione abbonamenti utente e integrazione con database Supabase
# ───────────────────────────────────────────────────────────────────────────────

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from supabase import Client

from config import STRIPE_PLANS, FREE_PLAN_LIMITS

# Configurazione logger
logger = logging.getLogger(__name__)


class SubscriptionManager:
    """Gestisce gli abbonamenti utente con Supabase e Stripe"""
    
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client
    
    def get_user_subscription(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Recupera l'abbonamento attivo di un utente.
        
        Args:
            user_id: ID utente Supabase
            
        Returns:
            Dict con dati abbonamento o None
        """
        try:
            # Cerca abbonamento attivo
            response = self.supabase.table('subscriptions') \
                .select('*') \
                .eq('user_id', user_id) \
                .in_('status', ['active', 'trialing']) \
                .order('created_at', desc=True) \
                .limit(1) \
                .execute()
            
            if response.data:
                subscription = response.data[0]
                plan_config = STRIPE_PLANS.get(subscription['plan_id'])
                
                return {
                    'id': subscription['id'],
                    'user_id': subscription['user_id'],
                    'stripe_subscription_id': subscription['stripe_subscription_id'],
                    'status': subscription['status'],
                    'plan_id': subscription['plan_id'],
                    'plan_name': plan_config['name'] if plan_config else 'Free',
                    'current_period_end': subscription['current_period_end'],
                    'cancel_at_period_end': subscription['cancel_at_period_end'],
                    'features': plan_config['features'] if plan_config else [],
                    'created_at': subscription['created_at']
                }
            
            # Nessun abbonamento attivo → piano free
            return self._get_free_plan_info(user_id)
            
        except Exception as e:
            logger.error(f"Errore recupero abbonamento utente {user_id}: {e}")
            return self._get_free_plan_info(user_id)
    
    def _get_free_plan_info(self, user_id: str) -> Dict[str, Any]:
        """Restituisce informazioni piano free"""
        return {
            'id': None,
            'user_id': user_id,
            'stripe_subscription_id': None,
            'status': 'free',
            'plan_id': 'free',
            'plan_name': 'VerificAI Free',
            'current_period_end': None,
            'cancel_at_period_end': False,
            'features': [
                f"{FREE_PLAN_LIMITS['verifiche_mensili']} verifiche al mese",
                "Modello Flash Lite",
                "Funzionalità base"
            ],
            'created_at': None
        }
    
    def create_subscription(self, user_id: str, stripe_subscription_id: str, 
                         plan_id: str, status: str = 'active') -> bool:
        """
        Crea un nuovo abbonamento nel database.
        
        Args:
            user_id: ID utente Supabase
            stripe_subscription_id: ID abbonamento Stripe
            plan_id: ID piano ('pro' o 'premium')
            status: Stato abbonamento
            
        Returns:
            True se successo, False altrimenti
        """
        try:
            # Recupera dati abbonamento da Stripe per il periodo
            from payments import get_subscription_status
            stripe_sub = get_subscription_status(stripe_subscription_id)
            
            subscription_data = {
                'user_id': user_id,
                'stripe_subscription_id': stripe_subscription_id,
                'plan_id': plan_id,
                'status': status,
                'current_period_end': datetime.fromtimestamp(
                    stripe_sub['current_period_end'], 
                    timezone.utc
                ).isoformat() if stripe_sub else None,
                'cancel_at_period_end': stripe_sub.get('cancel_at_period_end', False) if stripe_sub else False,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            response = self.supabase.table('subscriptions').insert(subscription_data).execute()
            
            if response.data:
                logger.info(f"Abbonamento creato: utente {user_id}, piano {plan_id}")
                return True
            else:
                logger.error(f"Errore creazione abbonamento: nessun dato restituito")
                return False
                
        except Exception as e:
            logger.error(f"Errore creazione abbonamento utente {user_id}: {e}")
            return False
    
    def update_subscription_status(self, stripe_subscription_id: str, 
                                status: str) -> bool:
        """
        Aggiorna lo stato di un abbonamento.
        
        Args:
            stripe_subscription_id: ID abbonamento Stripe
            status: Nuovo stato
            
        Returns:
            True se successo, False altrimenti
        """
        try:
            response = self.supabase.table('subscriptions') \
                .update({'status': status}) \
                .eq('stripe_subscription_id', stripe_subscription_id) \
                .execute()
            
            if response.data:
                logger.info(f"Abbonamento aggiornato: {stripe_subscription_id} → {status}")
                return True
            else:
                logger.warning(f"Nessun abbonamento trovato per aggiornare: {stripe_subscription_id}")
                return False
                
        except Exception as e:
            logger.error(f"Errore aggiornamento abbonamento {stripe_subscription_id}: {e}")
            return False
    
    def cancel_subscription(self, user_id: str, stripe_subscription_id: str) -> bool:
        """
        Cancella un abbonamento (impostato per cancellazione fine periodo).
        
        Args:
            user_id: ID utente Supabase
            stripe_subscription_id: ID abbonamento Stripe
            
        Returns:
            True se successo, False altrimenti
        """
        try:
            # Aggiorna database
            response = self.supabase.table('subscriptions') \
                .update({'cancel_at_period_end': True}) \
                .eq('user_id', user_id) \
                .eq('stripe_subscription_id', stripe_subscription_id) \
                .execute()
            
            if response.data:
                logger.info(f"Abbonamento impostato per cancellazione: utente {user_id}")
                return True
            else:
                logger.error(f"Errore impostazione cancellazione abbonamento utente {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"Errore cancellazione abbonamento utente {user_id}: {e}")
            return False
    
    def delete_subscription(self, stripe_subscription_id: str) -> bool:
        """
        Elimina completamente un abbonamento dal database.
        
        Args:
            stripe_subscription_id: ID abbonamento Stripe
            
        Returns:
            True se successo, False altrimenti
        """
        try:
            response = self.supabase.table('subscriptions') \
                .delete() \
                .eq('stripe_subscription_id', stripe_subscription_id) \
                .execute()
            
            if response.data:
                logger.info(f"Abbonamento eliminato: {stripe_subscription_id}")
                return True
            else:
                logger.warning(f"Nessun abbonamento trovato per eliminare: {stripe_subscription_id}")
                return False
                
        except Exception as e:
            logger.error(f"Errore eliminazione abbonamento {stripe_subscription_id}: {e}")
            return False
    
    def get_user_plan_limits(self, user_id: str) -> Dict[str, Any]:
        """
        Restituisce i limiti del piano utente.
        
        Args:
            user_id: ID utente Supabase
            
        Returns:
            Dict con limiti del piano
        """
        subscription = self.get_user_subscription(user_id)
        plan_id = subscription['plan_id']
        
        if plan_id == 'free':
            return {
                'verifiche_mensili': FREE_PLAN_LIMITS['verifiche_mensili'],
                'modello_ai': FREE_PLAN_LIMITS['modello_ai'],
                'unlimited': False
            }
        elif plan_id == 'pro':
            return {
                'verifiche_mensili': float('inf'),  # Illimitate
                'modello_ai': 'gemini-2.5-flash',
                'unlimited': True
            }
        elif plan_id == 'premium':
            return {
                'verifiche_mensili': float('inf'),  # Illimitate
                'modello_ai': 'gemini-2.5-pro',
                'unlimited': True
            }
        else:
            # Fallback a free
            return {
                'verifiche_mensili': FREE_PLAN_LIMITS['verifiche_mensili'],
                'modello_ai': FREE_PLAN_LIMITS['modello_ai'],
                'unlimited': False
            }
    
    def can_generate_verification(self, user_id: str, current_month_count: int) -> Dict[str, Any]:
        """
        Verifica se l'utente può generare una verifica.
        
        Args:
            user_id: ID utente Supabase
            current_month_count: Numero verifiche generate nel mese corrente
            
        Returns:
            Dict con risultato e messaggio
        """
        limits = self.get_user_plan_limits(user_id)
        
        if limits['unlimited']:
            return {
                'can_generate': True,
                'remaining': float('inf'),
                'message': 'Verifiche illimitate con il tuo piano'
            }
        else:
            remaining = limits['verifiche_mensili'] - current_month_count
            
            if remaining > 0:
                return {
                    'can_generate': True,
                    'remaining': remaining,
                    'message': f'Ti restano {remaining} {"verifica" if remaining == 1 else "verifiche"} questo mese'
                }
            else:
                return {
                    'can_generate': False,
                    'remaining': 0,
                    'message': f'Hai raggiunto il limite di {limits["verifiche_mensili"]} verifiche mensili. Passa a Pro per continuare!'
                }
    
    def get_subscription_history(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Recupera lo storico abbonamenti di un utente.
        
        Args:
            user_id: ID utente Supabase
            
        Returns:
            Lista di abbonamenti storici
        """
        try:
            response = self.supabase.table('subscriptions') \
                .select('*') \
                .eq('user_id', user_id) \
                .order('created_at', desc=True) \
                .execute()
            
            subscriptions = []
            for sub in response.data:
                plan_config = STRIPE_PLANS.get(sub['plan_id'])
                subscriptions.append({
                    'id': sub['id'],
                    'plan_id': sub['plan_id'],
                    'plan_name': plan_config['name'] if plan_config else 'Free',
                    'status': sub['status'],
                    'created_at': sub['created_at'],
                    'current_period_end': sub['current_period_end'],
                    'cancel_at_period_end': sub['cancel_at_period_end']
                })
            
            return subscriptions
            
        except Exception as e:
            logger.error(f"Errore recupero storico abbonamenti utente {user_id}: {e}")
            return []
    
    def record_payment(self, user_id: str, stripe_session_id: str, 
                     amount: int, currency: str, status: str) -> bool:
        """
        Registra un pagamento nel database.
        
        Args:
            user_id: ID utente Supabase
            stripe_session_id: ID sessione Stripe
            amount: Importo in centesimi
            currency: Valuta
            status: Stato pagamento
            
        Returns:
            True se successo, False altrimenti
        """
        try:
            payment_data = {
                'user_id': user_id,
                'stripe_session_id': stripe_session_id,
                'amount': amount,
                'currency': currency,
                'status': status,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            response = self.supabase.table('payments').insert(payment_data).execute()
            
            if response.data:
                logger.info(f"Pagamento registrato: utente {user_id}, importo {amount/100}€")
                return True
            else:
                logger.error(f"Errore registrazione pagamento utente {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"Errore registrazione pagamento utente {user_id}: {e}")
            return False


# Funzioni helper per compatibilità
def get_subscription_manager(supabase_client: Client) -> SubscriptionManager:
    """Restituisce istanza del SubscriptionManager"""
    return SubscriptionManager(supabase_client)
