-- ───────────────────────────────────────────────────────────────────────────────
-- Commenti ANONIMI lasciati dopo uno scarico («Com'è andata?»)
-- Da eseguire a mano nell'editor SQL di Supabase. Nessun user_id, nessuna email, nessun IP.
-- Scrive solo il server (chiave di servizio); senza policy gli utenti non leggono né scrivono.
-- ───────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS commenti_app (
    id          BIGSERIAL PRIMARY KEY,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    commento    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_commenti_app_created ON commenti_app(created_at DESC);

ALTER TABLE commenti_app ENABLE ROW LEVEL SECURITY;

-- Per leggerli: SELECT created_at, commento FROM commenti_app ORDER BY id DESC;
