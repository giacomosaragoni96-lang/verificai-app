-- ───────────────────────────────────────────────────────────────────────────────
-- Questionario dei tester (pagina ?pagina=questionario). ANONIMO: nessun user_id, nessun IP.
-- Da eseguire a mano nell'editor SQL di Supabase. Scrive solo il server (chiave di servizio):
-- RLS attiva e nessuna policy, quindi gli utenti non leggono né scrivono.
-- ───────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS questionario_tester (
    id                BIGSERIAL PRIMARY KEY,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    versione          INT NOT NULL DEFAULT 1,      -- versione delle domande (se un giorno le cambiamo)
    risposte          JSONB NOT NULL,              -- {"tempo_da_zero": "1–2 ore", "utile": 4, "vw_caro": 45, ...}
    email_facoltativa TEXT                         -- solo se la persona l'ha scritta per essere avvisata
);
CREATE INDEX IF NOT EXISTS idx_questionario_created ON questionario_tester(created_at DESC);

ALTER TABLE questionario_tester ENABLE ROW LEVEL SECURITY;

-- Per leggerle: Table editor di Supabase, oppure le query «QUESTIONARIO» in riepilogo_uso.sql.
