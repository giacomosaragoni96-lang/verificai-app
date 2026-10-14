-- ── migrazione_monetizzazione_fase0.sql ─────────────────────────────────────────────
-- Fase 0 della monetizzazione: basi sicure. Da eseguire UNA VOLTA in
-- Supabase Dashboard > SQL Editor (si può rieseguire senza danni).
--
-- 1) Toglie agli utenti la possibilità di scrivere in abbonamenti, pagamenti e profili
--    (oggi una policy permetterebbe a ognuno di darsi da solo il piano Pro).
--    L'app scrive con la chiave di servizio, che ignora le policy: non cambia nulla per lei.
-- 2) Aggiunge le colonne che serviranno alle licenze (nessuna è obbligatoria).
-- 3) Si assicura che esista `deleted_at` nello storico (eliminazione «logica»: una verifica
--    eliminata dall'elenco continua a contare nel tetto mensile).
-- 4) Crea il registro degli eventi d'uso `usage_events` (per tetti, costi e metriche).
-- ───────────────────────────────────────────────────────────────────────────────

DO $$
BEGIN
    -- 1) policy di scrittura degli utenti: via
    IF to_regclass('public.subscriptions') IS NOT NULL THEN
        EXECUTE 'DROP POLICY IF EXISTS "Users can insert own subscriptions" ON public.subscriptions';
        EXECUTE 'DROP POLICY IF EXISTS "Users can update own subscriptions" ON public.subscriptions';
        EXECUTE 'DROP POLICY IF EXISTS "Users can delete own subscriptions" ON public.subscriptions';

        -- 2) colonne per le licenze
        EXECUTE 'ALTER TABLE public.subscriptions ADD COLUMN IF NOT EXISTS provider TEXT DEFAULT ''manual''';
        EXECUTE 'ALTER TABLE public.subscriptions ADD COLUMN IF NOT EXISTS licenza_istanza_id TEXT';
        EXECUTE 'ALTER TABLE public.subscriptions ADD COLUMN IF NOT EXISTS ultima_verifica_licenza TIMESTAMPTZ';
        EXECUTE 'ALTER TABLE public.subscriptions ADD COLUMN IF NOT EXISTS interval TEXT';
    END IF;

    IF to_regclass('public.payments') IS NOT NULL THEN
        EXECUTE 'DROP POLICY IF EXISTS "Users can insert own payments" ON public.payments';
    END IF;

    IF to_regclass('public.user_profiles') IS NOT NULL THEN
        EXECUTE 'DROP POLICY IF EXISTS "Users can insert own profile" ON public.user_profiles';
        EXECUTE 'DROP POLICY IF EXISTS "Users can update own profile" ON public.user_profiles';
    END IF;
END $$;

-- 3) eliminazione logica nello storico
ALTER TABLE verifiche_storico ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
CREATE INDEX IF NOT EXISTS idx_verifiche_storico_user_created ON verifiche_storico(user_id, created_at);

-- 4) registro degli eventi d'uso (solo inserimenti, solo dal server)
CREATE TABLE IF NOT EXISTS usage_events (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    tipo TEXT NOT NULL,                 -- verifica, fila_b, bes, soluzioni, word, scheda, paywall…
    modello TEXT,                       -- modello AI effettivamente usato
    costo_usd NUMERIC(10, 5),           -- costo stimato
    verifica_id BIGINT,                 -- verifica a cui si riferisce (se c'è)
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_usage_events_user_created ON usage_events(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_usage_events_tipo ON usage_events(tipo);

-- RLS attiva e NESSUNA policy: gli utenti non leggono né scrivono; il server usa la chiave di servizio.
ALTER TABLE usage_events ENABLE ROW LEVEL SECURITY;

-- Controllo finale: policy rimaste su subscriptions (devono esserci solo letture)
SELECT tablename, policyname, cmd
FROM pg_policies
WHERE schemaname = 'public' AND tablename IN ('subscriptions', 'payments', 'user_profiles', 'usage_events')
ORDER BY tablename, policyname;
