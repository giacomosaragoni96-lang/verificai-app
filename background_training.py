# ── background_training.py ─────────────────────────────────────────────────────
# Sistema di background processing per training AI silenzioso
# ───────────────────────────────────────────────────────────────────────────────

import threading
import time
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from supabase import Client

logger = logging.getLogger("verificai.background_training")


class BackgroundTrainingProcessor:
    """
    Processo background che aggiorna automaticamente i pattern di training
    basati sui feedback raccolti.
    """
    
    def __init__(self, supabase_admin: Client):
        self.supabase_admin = supabase_admin
        self.running = False
        self.thread = None
        self.last_update = None
        
    def start(self):
        """Avvia il processo background."""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()
            logger.info("Background training processor avviato")
    
    def stop(self):
        """Ferma il processo background."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Background training processor fermato")
    
    def _run(self):
        """Loop principale del processo background."""
        while self.running:
            try:
                # Esegui aggiornamento ogni ora
                self._update_training_patterns()
                self._cleanup_old_data()
                self._update_metrics()
                
                # Attendi un'ora prima del prossimo aggiornamento
                for _ in range(3600):  # 3600 secondi = 1 ora
                    if not self.running:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"Errore in background training: {e}")
                # Attendi 15 minuti in caso di errore
                for _ in range(900):
                    if not self.running:
                        break
                    time.sleep(1)
    
    def _update_training_patterns(self):
        """Aggiorna i pattern di training basati sui feedback recenti."""
        try:
            from training_data import update_training_patterns
            
            success = update_training_patterns(self.supabase_admin)
            if success:
                self.last_update = datetime.now(timezone.utc)
                logger.info("Pattern di training aggiornati con successo")
            else:
                logger.warning("Fallimento aggiornamento pattern training")
                
        except Exception as e:
            logger.error(f"Errore aggiornamento pattern: {e}")
    
    def _cleanup_old_data(self):
        """Pulizia dati vecchi per mantenere il database performante."""
        try:
            # Rimuovi feedback più vecchi di 90 giorni
            cutoff_date = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
            
            result = self.supabase_admin.table('ai_feedback')\
                .delete()\
                .lt('created_at', cutoff_date)\
                .execute()
            
            if result.data:
                logger.info(f"Puliti {len(result.data)} record vecchi da ai_feedback")
                
        except Exception as e:
            logger.error(f"Errore cleanup dati: {e}")
    
    def _update_metrics(self):
        """Aggiorna le metriche di training."""
        try:
            # Calcola metriche giornaliere
            today = datetime.now(timezone.utc).date()
            
            # Feedback totali oggi
            today_feedback = self.supabase_admin.table('ai_feedback')\
                .select('rating', count='exact')\
                .gte('created_at', today.isoformat())\
                .execute()
            
            if today_feedback.count:
                good_count = sum(1 for item in today_feedback.data if item.get('rating') == 'good')
                total_count = today_feedback.count
                satisfaction_rate = good_count / total_count if total_count > 0 else 0
                
                # Salva metrica
                metric_data = {
                    'metric_type': 'daily_satisfaction_rate',
                    'metric_value': satisfaction_rate,
                    'date_recorded': today.isoformat(),
                    'created_at': datetime.now(timezone.utc).isoformat()
                }
                
                self.supabase_admin.table('training_metrics').insert(metric_data).execute()
                logger.info(f"Metrica satisfaction salvata: {satisfaction_rate:.2%}")
                
        except Exception as e:
            logger.error(f"Errore aggiornamento metriche: {e}")
    
    def get_status(self) -> dict:
        """Restituisce lo stato corrente del processor."""
        return {
            'running': self.running,
            'last_update': self.last_update.isoformat() if self.last_update else None,
            'thread_alive': self.thread.is_alive() if self.thread else False
        }


# Istanza globale del processor
_background_processor: Optional[BackgroundTrainingProcessor] = None


def initialize_background_training(supabase_admin: Client):
    """
    Inizializza il sistema di background training.
    """
    global _background_processor
    
    if _background_processor is None:
        _background_processor = BackgroundTrainingProcessor(supabase_admin)
        _background_processor.start()
        logger.info("Sistema background training inizializzato")
    
    return _background_processor


def get_background_processor() -> Optional[BackgroundTrainingProcessor]:
    """
    Restituisce l'istanza corrente del background processor.
    """
    return _background_processor


def shutdown_background_training():
    """
    Ferma il sistema di background training.
    """
    global _background_processor
    
    if _background_processor:
        _background_processor.stop()
        _background_processor = None
        logger.info("Sistema background training shutdown")


# Funzione per il monitoraggio (solo per admin)
def get_training_dashboard_data(supabase_admin: Client) -> dict:
    """
    Recupera dati per dashboard training (solo admin).
    """
    try:
        # Stats generali
        total_feedback = supabase_admin.table('ai_feedback')\
            .select('id', count='exact')\
            .execute()
        
        good_feedback = supabase_admin.table('ai_feedback')\
            .select('id', count='exact')\
            .eq('rating', 'good')\
            .execute()
        
        total_patterns = supabase_admin.table('training_patterns')\
            .select('id', count='exact')\
            .execute()
        
        # Feedback ultimi 7 giorni
        week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        recent_feedback = supabase_admin.table('ai_feedback')\
            .select('rating', count='exact')\
            .gte('created_at', week_ago)\
            .execute()
        
        # Calcola satisfaction rate recente
        recent_good = sum(1 for item in recent_feedback.data if item.get('rating') == 'good')
        recent_total = recent_feedback.count
        recent_satisfaction = recent_good / recent_total if recent_total > 0 else 0
        
        return {
            'total_feedback': total_feedback.count or 0,
            'good_feedback': good_feedback.count or 0,
            'total_patterns': total_patterns.count or 0,
            'recent_feedback': recent_feedback.count or 0,
            'recent_satisfaction': recent_satisfaction,
            'overall_satisfaction': (good_feedback.count or 0) / (total_feedback.count or 1),
            'background_status': get_background_processor().get_status() if get_background_processor() else None
        }
        
    except Exception as e:
        logger.error(f"Errore recupero dashboard data: {e}")
        return {
            'total_feedback': 0,
            'good_feedback': 0,
            'total_patterns': 0,
            'recent_feedback': 0,
            'recent_satisfaction': 0,
            'overall_satisfaction': 0,
            'background_status': None
        }
