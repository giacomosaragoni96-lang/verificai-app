-- ── database_schema.sql ─────────────────────────────────────────────────────────────
-- Schema per integrazione Stripe e gestione abbonamenti in VerificAI
-- Esegui in Supabase Dashboard > SQL Editor
-- ───────────────────────────────────────────────────────────────────────────────

-- Tabella abbonamenti utente
CREATE TABLE IF NOT EXISTS subscriptions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    stripe_subscription_id VARCHAR(255) UNIQUE NOT NULL,
    plan_id VARCHAR(50) NOT NULL CHECK (plan_id IN ('free', 'pro', 'premium')),
    status VARCHAR(50) NOT NULL CHECK (status IN ('active', 'trialing', 'past_due', 'canceled', 'unpaid', 'incomplete', 'incomplete_expired', 'free')),
    current_period_end TIMESTAMP WITH TIME ZONE,
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indici per performance
CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_stripe_id ON subscriptions(stripe_subscription_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status);
CREATE INDEX IF NOT EXISTS idx_subscriptions_plan_id ON subscriptions(plan_id);

-- Tabella pagamenti
CREATE TABLE IF NOT EXISTS payments (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    stripe_session_id VARCHAR(255) UNIQUE NOT NULL,
    amount INTEGER NOT NULL, -- Importo in centesimi
    currency VARCHAR(3) NOT NULL DEFAULT 'eur',
    status VARCHAR(50) NOT NULL CHECK (status IN ('pending', 'succeeded', 'failed', 'canceled')),
    payment_method VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indici per performance
CREATE INDEX IF NOT EXISTS idx_payments_user_id ON payments(user_id);
CREATE INDEX IF NOT EXISTS idx_payments_stripe_session ON payments(stripe_session_id);
CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);
CREATE INDEX IF NOT EXISTS idx_payments_created_at ON payments(created_at);

-- Tabella piani abbonamento (per gestione futura)
CREATE TABLE IF NOT EXISTS plans (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    plan_id VARCHAR(50) UNIQUE NOT NULL CHECK (plan_id IN ('free', 'pro', 'premium')),
    name VARCHAR(100) NOT NULL,
    stripe_price_id VARCHAR(255) UNIQUE,
    amount INTEGER NOT NULL, -- Importo in centesimi
    currency VARCHAR(3) NOT NULL DEFAULT 'eur',
    interval VARCHAR(20) NOT NULL DEFAULT 'month' CHECK (interval IN ('month', 'year')),
    features JSONB NOT NULL DEFAULT '[]',
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indici per performance
CREATE INDEX IF NOT EXISTS idx_plans_plan_id ON plans(plan_id);
CREATE INDEX IF NOT EXISTS idx_plans_active ON plans(active);

-- RLS (Row Level Security) per subscriptions
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;

-- Policy: utenti possono vedere solo i propri abbonamenti
CREATE POLICY "Users can view own subscriptions" ON subscriptions
    FOR SELECT USING (auth.uid() = user_id);

-- Policy: utenti possono inserire solo i propri abbonamenti
CREATE POLICY "Users can insert own subscriptions" ON subscriptions
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Policy: utenti possono aggiornare solo i propri abbonamenti
CREATE POLICY "Users can update own subscriptions" ON subscriptions
    FOR UPDATE USING (auth.uid() = user_id);

-- Policy: utenti possono eliminare solo i propri abbonamenti
CREATE POLICY "Users can delete own subscriptions" ON subscriptions
    FOR DELETE USING (auth.uid() = user_id);

-- RLS per payments
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;

-- Policy: utenti possono vedere solo i propri pagamenti
CREATE POLICY "Users can view own payments" ON payments
    FOR SELECT USING (auth.uid() = user_id);

-- Policy: utenti possono inserire solo i propri pagamenti
CREATE POLICY "Users can insert own payments" ON payments
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- RLS per plans (sola lettura pubblica per utenti autenticati)
ALTER TABLE plans ENABLE ROW LEVEL SECURITY;

-- Policy: tutti gli utenti autenticati possono vedere i piani attivi
CREATE POLICY "Authenticated users can view active plans" ON plans
    FOR SELECT USING (active = true);

-- Trigger per updated_at automatico
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger per subscriptions
CREATE TRIGGER update_subscriptions_updated_at 
    BEFORE UPDATE ON subscriptions 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Trigger per payments
CREATE TRIGGER update_payments_updated_at 
    BEFORE UPDATE ON payments 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Trigger per plans
CREATE TRIGGER update_plans_updated_at 
    BEFORE UPDATE ON plans 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Inserimento piani di default
INSERT INTO plans (plan_id, name, amount, currency, interval, features) VALUES
('free', 'VerificAI Free', 0, 'eur', 'month', 
 '["5 verifiche al mese", "Modello Flash Lite", "Funzionalità base"]'),
('pro', 'VerificAI Pro', 999, 'eur', 'month',
 '["Verifiche illimitate", "Modello Flash 2.5", "Fila B anti-copia", "BES/DSA", "Soluzioni docente"]'),
('premium', 'VerificAI Premium', 1999, 'eur', 'month',
 '["Tutte le funzionalità Pro", "Modello Pro 2.5 per materie STEM", "Priorità supporto", "Export avanzati"]')
ON CONFLICT (plan_id) DO NOTHING;

-- Colonna aggiuntiva per gli utenti (se non esiste già)
-- Aggiunge campo per stripe_customer_id nella tabella auth.users
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'users' 
        AND column_name = 'stripe_customer_id'
    ) THEN
        ALTER TABLE auth.users 
        ADD COLUMN stripe_customer_id VARCHAR(255);
    END IF;
END $$;

-- Indice per stripe_customer_id
CREATE INDEX IF NOT EXISTS idx_users_stripe_customer_id ON auth.users(stripe_customer_id);

-- Commenti per documentazione
COMMENT ON TABLE subscriptions IS 'Abbonamenti utente con integrazione Stripe';
COMMENT ON TABLE payments IS 'Storico pagamenti effettuati tramite Stripe';
COMMENT ON TABLE plans IS 'Piani abbonamento disponibili';

-- View per abbonamenti attuali degli utenti
CREATE OR REPLACE VIEW user_current_subscription AS
SELECT DISTINCT ON (s.user_id)
    s.user_id,
    s.id as subscription_id,
    s.plan_id,
    s.status,
    s.current_period_end,
    s.cancel_at_period_end,
    p.name as plan_name,
    p.features,
    s.created_at
FROM subscriptions s
LEFT JOIN plans p ON s.plan_id = p.plan_id
WHERE s.status IN ('active', 'trialing', 'free')
ORDER BY s.user_id, s.created_at DESC;

COMMENT ON VIEW user_current_subscription IS 'Vista per abbonamento corrente di ogni utente';
