# 🚀 Setup Stripe per VerificAI

Guida completa per configurare l'integrazione Stripe in VerificAI.

## 📋 Prerequisiti

1. **Account Stripe** - Registrati su [stripe.com](https://stripe.com)
2. **Modalità Test** - Usa le chiavi di test per sviluppo
3. **Supabase Database** - Database già configurato

## 🔧 Configurazione Database

Esegui lo schema SQL in `database_schema.sql` nel tuo database Supabase:

```sql
-- Vai in Supabase Dashboard > SQL Editor
-- Copia e incolla il contenuto di database_schema.sql
-- Esegui lo script
```

Questo creerà:
- `subscriptions` - Abbonamenti utente
- `payments` - Storico pagamenti  
- `plans` - Piani disponibili
- Indici e RLS policies per sicurezza

## 🔑 Configurazione Chiavi Stripe

### 1. Ottieni Chiavi API

Vai in [Stripe Dashboard > Developers > API keys](https://dashboard.stripe.com/apikeys):

- **Publishable key**: `pk_test_...` (visibile nel frontend)
- **Secret key**: `sk_test_...` (server-side, MAI nel frontend)
- **Webhook signing secret**: Genera dopo creare webhook

### 2. Configura in Streamlit Secrets

Nel file `.streamlit/secrets.toml` (locale) o in Streamlit Cloud Secrets:

```toml
STRIPE_PUBLISHABLE_KEY = "pk_test_..."
STRIPE_SECRET_KEY = "sk_test_..."
STRIPE_WEBHOOK_SECRET = "whsec_..."
BASE_URL = "https://tua-app.streamlit.app"
```

## 💳 Configurazione Prodotti e Prezzi

### 1. Crea Prodotti in Stripe Dashboard

Vai in [Stripe Dashboard > Products](https://dashboard.stripe.com/products):

#### Prodotto 1: VerificAI Pro
- **Nome**: "VerificAI Pro"
- **Descrizione**: "Abbonamento mensile per verifiche illimitate"
- **Prezzo**: €9.99/mese
- **Currency**: EUR
- **Intervallo**: month

#### Prodotto 2: VerificAI Premium  
- **Nome**: "VerificAI Premium"
- **Descrizione**: "Abbonamento premium con tutte le funzionalità"
- **Prezzo**: €19.99/mese
- **Currency**: EUR
- **Intervallo**: month

### 2. Aggiorna Price IDs in Config

Copia i Price ID generati (es. `price_1M2...`) e aggiornali in `config.py`:

```python
STRIPE_PLANS = {
    "pro": {
        "name": "VerificAI Pro",
        "price_id": "price_1M2...",  # ← INCOLLA QUI
        "amount": 999,
        "currency": "eur",
        "interval": "month",
        # ...
    },
    "premium": {
        "name": "VerificAI Premium", 
        "price_id": "price_1N3...",  # ← INCOLLA QUI
        "amount": 1999,
        "currency": "eur",
        "interval": "month",
        # ...
    }
}
```

## 🔄 Configurazione Webhook

### 1. Crea Endpoint Webhook

Vai in [Stripe Dashboard > Developers > Webhooks](https://dashboard.stripe.com/webhooks):

- **Endpoint URL**: `https://tua-app.streamlit.app?webhook=stripe`
- **Events to listen**: Seleziona questi eventi:
  - `checkout.session.completed`
  - `invoice.payment_succeeded`
  - `invoice.payment_failed`
  - `customer.subscription.deleted`
  - `customer.subscription.updated`

### 2. Configura Webhook Secret

Dopo aver creato il webhook, copia il **Signing secret** (inizia con `whsec_...`) e aggiungilo ai secrets Streamlit.

## 🧪 Test dell'Integrazione

### 1. Test Checkout

1. Avvia l'app in locale: `streamlit run main.py`
2. Login come utente test
3. Clicca "Passa a Pro - €9.99/mese"
4. Dovresti essere reindirizzato a Stripe Checkout
5. Usa carte di test Stripe:
   - **Successo**: 4242 4242 4242 4242
   - **Fallimento**: 4000 0000 0000 0002

### 2. Test Webhook

1. Usa [Stripe CLI](https://stripe.com/docs/stripe-cli) per test locali:
   ```bash
   stripe listen --forward-to localhost:8501?webhook=stripe
   ```
2. Oppure usa webhook di test in dashboard Stripe
3. Verifica che i dati vengano salvati in Supabase

### 3. Test Flusso Completo

1. Utente free → genera 5 verifiche → vede limite
2. Upgrade a Pro → checkout successo → abbonamento attivo
3. Verifiche illimitate disponibili
4. Cancella abbonamento → torna a free

## 🚀 Deploy in Produzione

### 1. Aggiorna Chiavi Production

Sostituisci le chiavi test con quelle production:

```toml
STRIPE_PUBLISHABLE_KEY = "pk_live_..."
STRIPE_SECRET_KEY = "sk_live_..."
```

### 2. Aggiorna Webhook URL

Cambia l'URL webhook in Stripe Dashboard:
- **Endpoint**: `https://verificai.streamlit.app?webhook=stripe`

### 3. Test Produzione

- Usa carte di test reali (small amounts)
- Verifica flusso completo
- Monitora dashboard Stripe per transazioni

## 📊 Monitoraggio e Troubleshooting

### Log Importanti

L'app logga eventi critici:
- Creazione checkout session
- Eventi webhook processati
- Errori Stripe
- Aggiornamenti abbonamenti

### Dashboard Stripe

Monitora:
- **Payments** - Transazioni e stati
- **Customers** - Utenti registrati
- **Subscriptions** - Abbonamenti attivi/cancellati
- **Webhooks** - Eventi e errori

### Common Issues

1. **Webhook non ricevuti**: Controlla URL e signing secret
2. **Checkout fallisce**: Verifica price_id e chiavi API
3. **RLS errors**: Controlla policies database Supabase
4. **CORS errors**: Verifica BASE_URL configurato correttamente

## 🔒 Sicurezza

- **MAI** esporre secret key nel frontend
- **SEMPRE** validare webhook signatures
- **USARE** RLS policies su Supabase
- **MONITORARE** transazioni sospette

## 📞 Supporto

Per problemi tecnici:
1. Controlla logs Streamlit e Stripe
2. Verifica configurazione secrets
3. Testa con Stripe CLI
4. Controlla documentazione Stripe ufficiale

---

## ✅ Checklist Pre-Launch

- [ ] Database schema eseguito
- [ ] Chiavi API configurate
- [ ] Prodotti e prezzi creati
- [ ] Price IDs aggiornati in config.py
- [ ] Webhook configurato e testato
- [ ] Checkout flow testato
- [ ] Gestione abbonamenti testata
- [ ] Logs monitoring attivo
- [ ] Documentazione utente aggiornata

Una volta completata questa checklist, l'integrazione Stripe sarà pronta per la produzione!
