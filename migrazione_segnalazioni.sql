-- ───────────────────────────────────────────────────────────────────────────────
-- Segnalazioni ANONIME di verifiche venute male («Qualcosa non va in questa verifica?»)
-- Da eseguire a mano nell'editor SQL di Supabase. Nessun user_id, nessuna email, nessun IP.
-- Scrive solo il server (chiave di servizio); le policy non ci sono, quindi gli utenti non leggono né scrivono.
-- ───────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS segnalazioni (
    id          BIGSERIAL PRIMARY KEY,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    nota        TEXT,                -- cosa non va, scritto dal docente
    esercizio   INT,                 -- numero dell'esercizio segnalato (vuoto = tutta la verifica)
    materia     TEXT,
    scuola      TEXT,
    argomento   TEXT,
    modello     TEXT,                -- modello AI usato per la generazione
    piano       TEXT,                -- free / pro / admin
    latex       TEXT,                -- testo della verifica, senza logo (solo se il docente ha lasciato la spunta)
    debug       TEXT                 -- prompt, risposta del modello, consumi (idem)
);
CREATE INDEX IF NOT EXISTS idx_segnalazioni_created ON segnalazioni(created_at DESC);

ALTER TABLE segnalazioni ENABLE ROW LEVEL SECURITY;

-- Per leggerle: Table editor di Supabase, oppure
--   SELECT id, created_at, materia, modello, piano, esercizio, nota FROM segnalazioni ORDER BY id DESC;
-- Per scaricare una segnalazione intera copia il contenuto di `debug` in un file .txt: ha lo stesso formato del debug admin.
