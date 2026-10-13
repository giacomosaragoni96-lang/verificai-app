-- ============================================================================
-- VerificAI — Modelli di verifica
-- Da eseguire UNA VOLTA in Supabase: SQL Editor → New query → incolla tutto → Run.
-- Sicuro da rilanciare (IF NOT EXISTS). Non tocca nessuna tabella dell'app.
-- Le tabelle non hanno policy: le legge e le scrive solo il server dell'app (service role).
-- ============================================================================

create extension if not exists pgcrypto;

-- Una verifica caricata (il file)
create table if not exists banca_fonti (
    id            uuid primary key default gen_random_uuid(),
    nome          text not null,                 -- nome del file
    tipo          text not null,                 -- verifica
    titolo        text,
    materia       text,
    scuola        text,                          -- Elementari | Medie | Professionale | Tecnico | Liceo
    hash          text unique,                   -- impronta del contenuto: evita di caricare due volte lo stesso file
    nota_livelli  text,
    created_at    timestamptz not null default now()
);

-- Struttura di una verifica (sezioni, quesiti, punti, facoltativi, codice LaTeX) da usare come modello
create table if not exists banca_modelli (
    id          uuid primary key default gen_random_uuid(),
    fonte_id    uuid references banca_fonti(id) on delete cascade,
    nome        text not null,
    materia     text,
    scuola      text,
    struttura   jsonb not null,
    approvato   boolean not null default false,
    created_at  timestamptz not null default now()
);

-- Sicurezza: nessun accesso dal browser; solo il server (service role) bypassa queste regole.
alter table banca_fonti   enable row level security;
alter table banca_modelli enable row level security;

-- ----------------------------------------------------------------------------
-- OPZIONALE — se avevi già eseguito il vecchio banca_esercizi.sql e vuoi togliere gli esercizi
-- caricati (la banca di esercizi è stata abbandonata). Togli i due trattini davanti alle righe e premi Run:
--
-- drop table if exists banca_esercizi;
-- delete from banca_fonti where tipo <> 'verifica';
-- ----------------------------------------------------------------------------
