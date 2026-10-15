-- ───────────────────────────────────────────────────────────────────────────────
-- Codici che si ricevono compilando il questionario completo (verifiche con tutte le funzioni).
-- Da eseguire a mano nell'editor SQL di Supabase (si può rieseguire senza danni).
-- Il codice NON è collegato alle risposte del questionario (che restano anonime): `usato_da` si riempie
-- solo quando un utente lo inserisce nell'app. Scrive solo il server: RLS attiva e nessuna policy.
-- ───────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.codici_sblocco (
    codice    TEXT PRIMARY KEY,                                         -- es. VFABCD2345 (si mostra come VF-ABCD-2345)
    creato_il TIMESTAMPTZ NOT NULL DEFAULT now(),
    usato_da  UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    usato_il  TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_codici_sblocco_usato_da ON public.codici_sblocco (usato_da);

ALTER TABLE public.codici_sblocco ENABLE ROW LEVEL SECURITY;

-- Controllo: la tabella esiste e non ha policy (la seconda query deve dare 0 righe)
SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename = 'codici_sblocco';
SELECT tablename, policyname FROM pg_policies WHERE schemaname = 'public' AND tablename = 'codici_sblocco';

-- Per vedere quanti codici sono stati generati e quanti usati:
--   SELECT count(*) AS generati, count(usato_da) AS usati FROM codici_sblocco;
