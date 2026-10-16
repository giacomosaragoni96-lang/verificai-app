-- ───────────────────────────────────────────────────────────────────────────────
-- Contatore ANONIMO delle aperture dell'app (quante persone arrivano dai post, da quale link)
-- Da eseguire a mano nell'editor SQL di Supabase. Nessun user_id, nessuna email, nessun IP.
-- Scrive solo il server (chiave di servizio); le policy non ci sono, quindi gli utenti non leggono né scrivono.
-- ───────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS aperture_app (
    id          BIGSERIAL PRIMARY KEY,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    src         TEXT NOT NULL DEFAULT 'diretto',   -- da ?src= del link (gruppo1, gruppo2…) o «diretto»
    tappa       TEXT NOT NULL DEFAULT 'login'      -- «login» = ha visto la schermata di accesso
);
CREATE INDEX IF NOT EXISTS idx_aperture_app_created ON aperture_app(created_at DESC);

ALTER TABLE aperture_app ENABLE ROW LEVEL SECURITY;

-- Per leggerle (aperture, iscrizioni e verifiche per link; gli «accessi» sono quelli già in usage_events):
--   SELECT src, count(*) AS aperture, date_trunc('day', min(created_at)) AS dal
--   FROM aperture_app GROUP BY src ORDER BY aperture DESC;
--   SELECT replace(tipo,'accesso:','') AS src, count(*) AS accessi FROM usage_events WHERE tipo LIKE 'accesso:%' GROUP BY 1;
