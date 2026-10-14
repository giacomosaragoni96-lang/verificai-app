-- ── migrazione_inviti.sql ───────────────────────────────────────────────────────────
-- Inviti tra colleghi. Da eseguire UNA VOLTA in Supabase Dashboard > SQL Editor (si può rieseguire senza danni).
--
-- codici_invito : il codice personale di ogni docente (nel link ?ref=CODICE)
-- inviti        : chi ha invitato chi; "convalidato_il" si riempie quando l'invitato completa la sua prima verifica
-- bonus_usati   : le verifiche create con un credito bonus (tutto il piano Pro su quella verifica)
--
-- Le tre tabelle si scrivono SOLO dal server (chiave di servizio): RLS attiva e nessuna policy per gli utenti.
-- ───────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.codici_invito (
    user_id   UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    codice    TEXT NOT NULL UNIQUE,
    creato_il TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.inviti (
    id             BIGSERIAL PRIMARY KEY,
    invitante_id   UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    invitato_id    UUID NOT NULL UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,   -- un utente si invita una volta sola
    creato_il      TIMESTAMPTZ NOT NULL DEFAULT now(),
    convalidato_il TIMESTAMPTZ,
    CHECK (invitante_id <> invitato_id)
);
CREATE INDEX IF NOT EXISTS idx_inviti_invitante ON public.inviti (invitante_id);

CREATE TABLE IF NOT EXISTS public.bonus_usati (
    verifica_id BIGINT PRIMARY KEY,                      -- una verifica consuma un solo credito
    user_id     UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    creato_il   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_bonus_usati_user ON public.bonus_usati (user_id);

ALTER TABLE public.codici_invito ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.inviti        ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.bonus_usati   ENABLE ROW LEVEL SECURITY;

-- Controllo: tabelle create e nessuna policy (devono risultare 0 righe)
SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename IN ('codici_invito', 'inviti', 'bonus_usati');
SELECT tablename, policyname FROM pg_policies WHERE schemaname = 'public' AND tablename IN ('codici_invito', 'inviti', 'bonus_usati');
