# ── subscription_management.py ───────────────────────────────────────────────────────
# Piano dell'utente e cosa può fare (sola lettura da Supabase).
# Il piano si assegna a mano scrivendo la riga nella tabella `subscriptions`
# (e, in futuro, la scrive solo il processo di attivazione della licenza: mai l'utente).
#
# calcola_entitlements() è una funzione pura (nessun database, nessun Streamlit): dato
# l'abbonamento letto e il numero di verifiche del mese dice piano, tetto e funzioni.
# ───────────────────────────────────────────────────────────────────────────────

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from supabase import Client

from config import (
    FREE_PLAN_LIMITS, FUNZIONI_PRO, MONETIZZAZIONE_ATTIVA, PIANI,
)

logger = logging.getLogger(__name__)

# Nomi mostrati per i piani a pagamento
_PLAN_NAMES = {
    'pro': 'VerificAI Pro',
    'premium': 'VerificAI Premium',
}


def _scaduto(fine_periodo) -> bool:
    """True se la data di fine periodo è passata (None = senza scadenza, es. piano assegnato a mano)."""
    if not fine_periodo:
        return False
    try:
        fine = datetime.fromisoformat(str(fine_periodo).replace("Z", "+00:00"))
        if fine.tzinfo is None:
            fine = fine.replace(tzinfo=timezone.utc)
        return fine < datetime.now(timezone.utc)
    except Exception:
        logger.warning("Data di fine periodo non leggibile: %r", fine_periodo)
        return False


@dataclass(frozen=True)
class Entitlements:
    """Cosa può fare un utente adesso. Si crea con calcola_entitlements()."""
    piano: str                          # "free" | "pro" | "admin"
    scadenza: Optional[str]             # fine del periodo pagato (None se non applicabile)
    tetto_mensile: float                # verifiche al mese (inf = senza tetto)
    verifiche_mese: Optional[int]       # già create questo mese; None = non si è riusciti a contarle
    famiglia_modello: str               # "lite" | "flash"  (mai un ID di modello)
    funzioni: frozenset
    assaggio: bool = False              # sta lavorando sulla sua prima verifica: tutto il Pro

    @property
    def illimitato(self) -> bool:
        return self.tetto_mensile == float("inf")

    @property
    def errore_conteggio(self) -> bool:
        """Il conteggio non è disponibile: per chi ha un tetto si blocca la creazione (mai «0»)."""
        return self.verifiche_mese is None and self.piano != "admin" and not self.illimitato

    @property
    def restanti(self) -> Optional[int]:
        if self.illimitato or self.verifiche_mese is None:
            return None
        return max(0, int(self.tetto_mensile - self.verifiche_mese))

    @property
    def limite_raggiunto(self) -> bool:
        return (self.piano != "admin" and not self.illimitato
                and self.verifiche_mese is not None and self.verifiche_mese >= self.tetto_mensile)

    def puo(self, funzione: str) -> bool:
        """Con la monetizzazione spenta tutto è aperto; da accesa contano le funzioni del piano."""
        if not MONETIZZAZIONE_ATTIVA or self.piano == "admin":
            return True
        return funzione in self.funzioni


def calcola_entitlements(abbonamento: Optional[Dict[str, Any]], verifiche_mese: Optional[int],
                         is_admin: bool = False, assaggio: bool = False) -> Entitlements:
    """
    abbonamento    : dict di SubscriptionManager.get_user_subscription (o None)
    verifiche_mese : verifiche create nel mese; None se il conteggio non è riuscito
    assaggio       : la verifica su cui sta lavorando è la prima in assoluto dell'utente: per un utente
                     free vale tutto il Pro (funzioni e modello), ma il tetto mensile resta quello free
    """
    if is_admin:
        return Entitlements("admin", None, float("inf"), verifiche_mese, "flash", frozenset(FUNZIONI_PRO))
    piano = (abbonamento or {}).get("plan_id") or "free"
    if piano == "premium":          # non si vende ancora: vale come Pro finché non viene allineato
        piano = "pro"
    scadenza = (abbonamento or {}).get("current_period_end")
    if piano != "free" and _scaduto(scadenza):
        logger.info("Abbonamento scaduto (%s): piano free", scadenza)
        piano = "free"
    if piano not in PIANI:
        piano = "free"
    cfg = PIANI[piano]
    if assaggio and piano == "free":
        return Entitlements(
            piano, None, float(cfg["tetto_mensile"]), verifiche_mese,
            PIANI["pro"]["famiglia_modello"], frozenset(PIANI["pro"]["funzioni"]), True,
        )
    return Entitlements(
        piano, scadenza if piano != "free" else None, float(cfg["tetto_mensile"]),
        verifiche_mese, cfg["famiglia_modello"], frozenset(cfg["funzioni"]),
    )


class SubscriptionManager:
    """Legge gli abbonamenti utente da Supabase."""

    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client

    def get_user_subscription(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Recupera l'abbonamento attivo di un utente (piano free se non c'è nulla di attivo,
        anche in caso di errore: non si regala Pro per un guasto).
        """
        try:
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


# Funzioni helper per compatibilità
def get_subscription_manager(supabase_client: Client) -> SubscriptionManager:
    """Restituisce istanza del SubscriptionManager"""
    return SubscriptionManager(supabase_client)
