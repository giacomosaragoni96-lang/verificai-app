# 🤖 Sistema Training AI per VerificAI

Sistema completo di training silenzioso per migliorare automaticamente la qualità delle verifiche generate attraverso il feedback degli utenti.

## 🎯 Concetto

**"Fire and Forget" Training**: L'utente dà solo un feedback semplice (👍/👎) e l'AI impara automaticamente senza interfacce complesse.

## 📋 Componenti

### 1. Raccolta Dati Silenziosa
- **Pulsanti Feedback**: Solo due pulsanti 👍 "Buono" / 👎 "Non buono"
- **Posizionamento**: Sotto ogni verifica generata (fasi REVIEW e FINAL)
- **Storage Automatico**: Salvataggio invisibile nel database
- **Feature Extraction**: Analisi automatica delle caratteristiche delle verifiche

### 2. Learning Automatico
- **Pattern Recognition**: Identifica schemi ricorrenti in esercizi buoni/mediocri
- **Few-shot Learning**: Integrazione esempi positivi nei prompt
- **Negative Patterns**: Riconoscimento pattern da evitare
- **Dynamic Enhancement**: Adattamento continuo basato su feedback

### 3. Background Processing
- **Aggiornamento Automatico**: Ogni ora analizza i nuovi feedback
- **Pattern Extraction**: Genera nuovi pattern di training
- **Cleanup**: Rimozione dati vecchi per performance
- **Metrics**: Tracking satisfaction e improvement

## 🏗️ Architettura

### Database Schema
```sql
ai_feedback          -- Feedback utente (good/bad + features)
training_patterns    -- Pattern di training (positive/negative)
training_metrics     -- Metriche performance
```

### Moduli Python
- `training_data.py` - Analisi features e pattern extraction
- `rating_system.py` - UI feedback silenzioso
- `prompt_enhancer.py` - Integrazione training nei prompt
- `background_training.py` - Processo background automatico
- `training_dashboard.py` - Dashboard admin per monitoraggio

## 🚀 Setup

### 1. Database
```bash
# Esegui script setup
python setup_training_database.py

# O manualmente:
# 1. Vai a Supabase Dashboard
# 2. SQL Editor
# 3. Esegui training_schema.sql
```

### 2. Dipendenze
```bash
# Le dipendenze sono già incluse in requirements.txt
# - supabase (database)
# - streamlit (UI)
# - google-generativeai (AI)
```

### 3. Configurazione
Il sistema si attiva automaticamente all'avvio dell'app se il database è configurato correttamente.

## 🔄 Flusso Training

### 1. Generazione Verifica
- Utente genera verifica normalmente
- Sistema analizza features automaticamente
- Prompt enhancement se training data disponibile

### 2. Feedback Utente
- Utente vede pulsanti 👍/👎
- Click → salvataggio automatico
- "Grazie per il feedback!" → fine interazione

### 3. Background Learning
- Ogni ora: analisi feedback recenti
- Estrazione pattern positivi/negativi
- Aggiornamento prompt templates
- Tracking metrics

### 4. Improvement Continuo
- Esempi positivi integrati nei prompt
- Pattern negativi evitati automaticamente
- Qualità migliora nel tempo

## 📊 Dashboard Admin

Accessibile dalla sidebar per utenti admin:

### Metrics
- Feedback totali e positivi
- Tasso soddisfazione
- Pattern training generati
- Status background processor

### Controlli
- Aggiornamento manuale pattern
- Cleanup dati vecchi
- Export dati training
- Monitoraggio andamento

## 🔧 Configurazione Avanzata

### Threshold Training
```python
# In prompt_enhancer.py
MIN_EXAMPLES_FOR_ENHANCEMENT = 5  # Minimo esempi per attivare training
```

### Background Processing
```python
# In background_training.py
UPDATE_INTERVAL_HOURS = 1          # Frequenza aggiornamenti
DATA_RETENTION_DAYS = 90          # Retention dati
```

### Feature Extraction
```python
# In training_data.py
FEATURE_WEIGHTS = {
    'structure_score': 0.3,
    'content_quality': 0.4,
    'has_punteggi': 0.2,
    'has_grafici': 0.1
}
```

## 📈 Success Metrics

### Qualità Output
- Aumento satisfaction rate
- Riduzione revisioni necessarie
- Miglioramento validation score

### Adoption
- % utenti che danno feedback
- Frequenza feedback per utente
- Training data growth rate

### Performance
- Tempo generazione
- Accuracy miglioramento
- Resource usage

## 🛡️ Sicurezza e Privacy

### Data Protection
- Solo admin possono accedere dati training
- Anonimizzazione feedback utente
- Retention limitata (90 giorni)

### Access Control
- RLS policies su tutte le tabelle
- Admin-only dashboard e controlli
- Secure API endpoints

## 🔍 Troubleshooting

### Common Issues

#### 1. Training non si attiva
```
Check: Database tables exist?
Check: Supabase credentials?
Check: Admin permissions?
```

#### 2. Feedback non salva
```
Check: User logged in?
Check: Supabase connection?
Check: Table permissions?
```

#### 3. Pattern non aggiornano
```
Check: Background processor running?
Check: Recent feedback available?
Check: No errors in logs?
```

### Debug Mode
```python
# Attiva logging dettagliato
import logging
logging.getLogger("verificai.training").setLevel(logging.DEBUG)
```

## 🚀 Futuri Miglioramenti

### Short Term
- [ ] A/B testing con/without training
- [ ] Multi-dimensional rating (difficoltà, chiarezza, etc.)
- [ ] Export avanzato con analytics

### Long Term
- [ ] Federated learning tra scuole
- [ ] Personalizzazione per docente
- [ ] Integration con LMS systems

## 📞 Support

Per problemi o domande:
1. Controlla logs dell'app
2. Verifica dashboard admin
3. Controlla configurazione Supabase
4. GitHub issues per bug report

---

**Nota**: Questo sistema è progettato per essere completamente trasparente all'utente finale. L'obiettivo è migliorare la qualità delle verifiche generata senza aggiungere complessità all'esperienza utente.
