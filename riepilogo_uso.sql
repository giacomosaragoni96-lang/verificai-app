-- ───────────────────────────────────────────────────────────────────────────────
-- Riepilogo d'uso per la prova pubblica. Query da incollare una per volta nell'editor SQL di Supabase.
-- Tutto aggregato: nessuna query mostra email o nomi. Sostituisci l'email dell'admin (la tua) dove serve.
-- Tabelle usate: auth.users (iscrizioni), verifiche_storico (verifiche create), usage_events (funzioni),
-- segnalazioni (verifiche segnalate).
-- ───────────────────────────────────────────────────────────────────────────────

-- 0) Chi conta come «tester»: tutti tranne te. Cambia l'email qui sotto in tutte le query che hanno ADMIN.
--    (le verifiche eliminate dall'utente restano contate: `deleted_at` serve solo a nasconderle nell'elenco)

-- 1) ISCRIZIONI per giorno (e quante hanno confermato l'email)
SELECT date_trunc('day', created_at)::date AS giorno,
       count(*)                                       AS iscritti,
       count(*) FILTER (WHERE email_confirmed_at IS NOT NULL) AS email_confermate
FROM auth.users
WHERE email <> 'giacomosaragoni96@gmail.com'          -- ADMIN
GROUP BY 1 ORDER BY 1 DESC;

-- 2) IMBUTO: da iscritti a utenti che tornano
WITH tester AS (
    SELECT id FROM auth.users WHERE email <> 'giacomosaragoni96@gmail.com'          -- ADMIN
), per_utente AS (
    SELECT t.id, count(v.id) AS verifiche
    FROM tester t LEFT JOIN verifiche_storico v ON v.user_id = t.id
    GROUP BY t.id
)
SELECT count(*)                                  AS iscritti,
       count(*) FILTER (WHERE verifiche >= 1)    AS con_1_verifica,
       count(*) FILTER (WHERE verifiche >= 2)    AS con_2_verifiche,
       count(*) FILTER (WHERE verifiche >= 3)    AS con_3_o_piu,
       round(100.0 * count(*) FILTER (WHERE verifiche >= 1) / NULLIF(count(*), 0), 1) AS perc_hanno_creato,
       round(100.0 * count(*) FILTER (WHERE verifiche >= 2) / NULLIF(count(*) FILTER (WHERE verifiche >= 1), 0), 1) AS perc_ne_creano_una_seconda
FROM per_utente;

-- 3) QUANTO CI METTONO a creare la prima verifica dopo l'iscrizione (mediana e media, in ore)
WITH prima AS (
    SELECT u.id, u.created_at AS iscritto, min(v.created_at) AS prima_verifica
    FROM auth.users u JOIN verifiche_storico v ON v.user_id = u.id
    WHERE u.email <> 'giacomosaragoni96@gmail.com'          -- ADMIN
    GROUP BY u.id, u.created_at
)
SELECT count(*) AS utenti,
       round((percentile_cont(0.5) WITHIN GROUP (ORDER BY extract(epoch FROM prima_verifica - iscritto)) / 3600)::numeric, 2) AS mediana_ore,
       round((avg(extract(epoch FROM prima_verifica - iscritto)) / 3600)::numeric, 2) AS media_ore
FROM prima;

-- 4) RITORNO: quante persone usano l'app in giorni diversi (1, 2, 3+ giorni)
WITH giorni AS (
    SELECT v.user_id, count(DISTINCT v.created_at::date) AS giorni_attivi
    FROM verifiche_storico v JOIN auth.users u ON u.id = v.user_id
    WHERE u.email <> 'giacomosaragoni96@gmail.com'          -- ADMIN
    GROUP BY v.user_id
)
SELECT giorni_attivi, count(*) AS utenti FROM giorni GROUP BY 1 ORDER BY 1;

-- 5) FUNZIONI USATE negli ultimi 30 giorni: quante volte e da quante persone diverse
--    (tipi: verifica, modifica, fila_b, bes, soluzioni, griglia, scheda, word, condivisione, materiale)
SELECT e.tipo,
       count(*)                  AS volte,
       count(DISTINCT e.user_id) AS persone
FROM usage_events e JOIN auth.users u ON u.id = e.user_id
WHERE e.created_at > now() - interval '30 days'
  AND u.email <> 'giacomosaragoni96@gmail.com'          -- ADMIN
GROUP BY e.tipo ORDER BY persone DESC, volte DESC;

-- 6) QUALI FUNZIONI usano chi ha creato almeno una verifica (percentuale di utenti per funzione)
WITH attivi AS (
    SELECT DISTINCT v.user_id FROM verifiche_storico v JOIN auth.users u ON u.id = v.user_id
    WHERE u.email <> 'giacomosaragoni96@gmail.com'          -- ADMIN
)
SELECT e.tipo,
       count(DISTINCT e.user_id) AS persone,
       round(100.0 * count(DISTINCT e.user_id) / (SELECT count(*) FROM attivi), 1) AS perc_degli_attivi
FROM usage_events e JOIN attivi a ON a.user_id = e.user_id
GROUP BY e.tipo ORDER BY persone DESC;

-- 7) MODIFICHE agli esercizi: quante per verifica e quante verifiche arrivano al tetto (10)
WITH m AS (
    SELECT verifica_id, count(*) AS modifiche
    FROM usage_events WHERE tipo = 'modifica' AND verifica_id IS NOT NULL
    GROUP BY verifica_id
)
SELECT count(*)                               AS verifiche_con_modifiche,
       round(avg(modifiche), 1)               AS modifiche_medie,
       max(modifiche)                         AS massimo,
       count(*) FILTER (WHERE modifiche >= 10) AS arrivate_al_tetto_free
FROM m;

-- 8) COSA CREANO: materie, scuole, modelli e percorso scelto (solo tester)
SELECT v.materia, v.scuola, v.modello, count(*) AS verifiche
FROM verifiche_storico v JOIN auth.users u ON u.id = v.user_id
WHERE u.email <> 'giacomosaragoni96@gmail.com'          -- ADMIN
GROUP BY 1, 2, 3 ORDER BY verifiche DESC;

-- 9) SEGNALAZIONI ricevute (le più recenti per prime; `debug` è il file completo da passarmi)
SELECT id, created_at, materia, modello, piano, esercizio, left(nota, 120) AS nota
FROM segnalazioni ORDER BY id DESC LIMIT 50;

-- 10) COSTO STIMATO dell'uso (stima, non fatturazione: costi medi per azione misurati/stimati a ottobre 2026)
SELECT e.tipo, count(*) AS volte,
       round((count(*) * CASE e.tipo
           WHEN 'verifica'  THEN 0.0055 WHEN 'modifica' THEN 0.0025 WHEN 'fila_b'   THEN 0.010
           WHEN 'bes'       THEN 0.008  WHEN 'soluzioni' THEN 0.015 WHEN 'griglia'  THEN 0.005
           WHEN 'scheda'    THEN 0.05   ELSE 0 END)::numeric, 3) AS dollari_stimati
FROM usage_events e JOIN auth.users u ON u.id = e.user_id
WHERE e.created_at > now() - interval '30 days' AND u.email <> 'giacomosaragoni96@gmail.com'          -- ADMIN
GROUP BY e.tipo ORDER BY dollari_stimati DESC;
