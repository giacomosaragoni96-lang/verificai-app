-- ───────────────────────────────────────────────────────────────────────────────
-- Classi del docente: una colonna in più in verifiche_storico (da eseguire a mano nell'editor SQL di Supabase).
-- Senza questa colonna l'app funziona lo stesso: la classe semplicemente non viene salvata.
-- Il profilo (preferenze e elenco delle classi) NON richiede migrazioni: sta già in docente_preferenze (materia = '__profilo__').
-- ───────────────────────────────────────────────────────────────────────────────
ALTER TABLE verifiche_storico ADD COLUMN IF NOT EXISTS classe TEXT;
CREATE INDEX IF NOT EXISTS idx_verifiche_storico_classe ON verifiche_storico(user_id, classe);
