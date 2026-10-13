# ── subscription_management.py ───────────────────────────────────────────────────────
# Lettura abbonamento utente da Supabase e limiti del piano.
# Il piano si assegna a mano scrivendo la riga nella tabella `subscriptions`.
# ───────────────────────────────────────────────────────────────────────────────

import logging
from typing import Optional, Dict, Any
from supabase import Client

from config import FREE_PLAN_LIMITS

# Configurazione logger
logger = logging.getLogger(__name__)

# Nomi mostrati per i piani a pagamento
_PLAN_NAMES = {
    'pro': 'VerificAI Pro',
    'premium': 'VerificAI Premium',
}


class SubscriptionManager:
    """Legge gli abbonamenti utente da Supabase e calcola i limiti del piano"""

    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client

    def get_user_subscription(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Recupera l'abbonamento attivo di un utente.

        Args:
            user_id: ID utente Supabase

        Returns:
            Dict con dati abbonamento (piano free se non c'è nulla di attivo)
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

                return {
                    'id': subscription['id'],
                    'user_id': subscription['user_id'],
                    'status': subscription['status'],
                    'plan_id': subscription['plan_id'],
                    'plan_name': _PLAN_NAMES.get(subscription['plan_id'], 'Free'),
                    'current_period_end': subscription['current_period_end'],
                    'cancel_at_period_end': subscription['cancel_at_period_end'],
                    'features': [],
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
                    'message': f'Hai raggiunto il limite di {limits["verifiche_mensili"]} verifiche mensili.'
                }


# Funzioni helper per compatibilità
def get_subscription_manager(supabase_client: Client) -> SubscriptionManager:
    """Restituisce istanza del SubscriptionManager"""
    return SubscriptionManager(supabase_client)
