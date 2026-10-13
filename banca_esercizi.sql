-- ============================================================================
-- VerificAI — Banca esercizi
-- Da eseguire UNA VOLTA in Supabase: SQL Editor → New query → incolla tutto → Run.
-- Sicuro da rilanciare (IF NOT EXISTS). Non tocca nessuna tabella esistente.
-- Le tabelle non hanno policy: le legge e le scrive solo il server dell'app (service role).
-- ============================================================================

create extension if not exists pgcrypto;

-- Un file caricato (verifica, scheda, appunti, libro)
create table if not exists banca_fonti (
    id            uuid primary key default gen_random_uuid(),
    nome          text not null,                 -- nome del file
    tipo          text not null,                 -- verifica | scheda | appunti | pdf
    titolo        text,
    materia       text,
    scuola        text,                          -- tipo di scuola a cui è destinata (come nell'app)
    hash          text unique,                   -- impronta del contenuto: evita di caricare due volte lo stesso file
    nota_livelli  text,
    created_at    timestamptz not null default now()
);

-- Un esercizio (o un esempio svolto) della banca
create table if not exists banca_esercizi (
    id                  uuid primary key default gen_random_uuid(),
    fonte_id            uuid references banca_fonti(id) on delete cascade,
    numero              text,                    -- numero scritto nel testo (es. "12" o "2.a)")
    sezione             text,                    -- sezione/capitolo di provenienza
    ruolo               text not null default 'esercizio',   -- esercizio | esempio_svolto
    testo_latex         text not null,
    opzioni             jsonb not null default '[]'::jsonb,  -- opzioni di risposta (scelta multipla)
    soluzione_latex     text,
    difficolta          smallint check (difficolta between 1 and 3),   -- 1 base, 2 medio, 3 sfida
    difficolta_origine  text,                    -- da dove viene la difficoltà (livello della fonte o stima AI)
    argomento           text,
    tecniche            text[] not null default '{}',
    tipo                text,                    -- aperto | scelta_multipla | vero_falso | completamento | problema
    punti               integer,
    facoltativo         boolean not null default false,
    ha_figura           boolean not null default false,
    materia             text,
    scuola              text,
    approvato           boolean not null default false,       -- false = in attesa di revisione
    created_at          timestamptz not null default now()
);

create index if not exists banca_esercizi_fonte_idx   on banca_esercizi (fonte_id);
create index if not exists banca_esercizi_filtro_idx  on banca_esercizi (materia, difficolta) where approvato;

-- Struttura di una verifica (sezioni, quesiti, punti, facoltativi) da usare come modello
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
alter table banca_fonti    enable row level security;
alter table banca_esercizi enable row level security;
alter table banca_modelli  enable row level security;
