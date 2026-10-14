-- ── migrazione_monetizzazione_fase2.sql ─────────────────────────────────────────────
-- Fase 2 (licenze Lemon Squeezy). Da eseguire UNA VOLTA in Supabase Dashboard > SQL Editor
-- (si può rieseguire senza danni). Dopo la fase 0.
--
-- Aggiunge a `subscriptions` il codice di licenza, che serve a ricontrollarlo ogni 24 ore
-- (rimborso o scadenza = torna Free) e a impedire che lo stesso codice sia usato su due account.
-- La tabella resta scrivibile solo dal server (nessuna policy di scrittura per gli utenti).
-- ───────────────────────────────────────────────────────────────────────────────

ALTER TABLE public.subscriptions ADD COLUMN IF NOT EXISTS licenza_chiave TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS idx_subscriptions_licenza_chiave
    ON public.subscriptions (licenza_chiave) WHERE licenza_chiave IS NOT NULL;

-- Controllo: colonne presenti e policy rimaste (devono esserci solo letture)
SELECT column_name FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'subscriptions'
ORDER BY ordinal_position;

SELECT tablename, policyname, cmd FROM pg_policies
WHERE schemaname = 'public' AND tablename = 'subscriptions';
