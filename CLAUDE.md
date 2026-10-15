# CLAUDE.md

Guida per Claude Code su questo repository. Rispondi sempre in italiano.

## Progetto

VerificAI: web app Streamlit in italiano con cui i docenti generano verifiche scolastiche
(Gemini -> LaTeX -> PDF/DOCX). Deploy su Streamlit Cloud dal branch `main`
(https://verificai.streamlit.app). Dev container Python 3.11, porta 8501.
Avvio locale: `streamlit run main.py`. Pacchetti di sistema in `packages.txt`
(texlive-latex-extra, texlive-fonts-recommended, texlive-lang-italian, poppler-utils, pandoc).

## Regole rigide (non negoziabili)

- Non rimuovere né aggirare l'autenticazione Supabase (`auth.py`, sessione via `?rt=TOKEN`).
- Nessuna logica di generazione AI in `main.py` e `sidebar.py`: solo interfaccia.
- Nessun `import streamlit` in `generation.py`, `latex_utils.py`, `prompts.py`,
  `docx_export.py`, `config.py`. Devono restare testabili in isolamento.
- I prompt vivono SOLO in `prompts.py`, come funzioni pure che restituiscono stringhe.
- Ogni modifica a `latex_utils.py`, `generation.py` o `prompts.py` deve mantenere il LaTeX
  compilabile con `pdflatex` standard (amsmath, pgfplots, tikz, enumerate, adjustbox, geometry, babel italian).
- Non spostare logica tra livelli e non cambiare le responsabilità dei file senza chiedere.
- Codice compatibile con Streamlit: `st.session_state`, niente storage del browser, attenzione ai rerun.

## Sicurezza

- Non leggere, stampare o loggare `.streamlit/secrets.toml` né chiavi o token di alcun tipo.
- Il LaTeX prodotto dall'AI è input non fidato: non deve poter leggere file o eseguire comandi
  (verificare i flag di `pdflatex` in `latex_utils.py` prima di toccarlo).
- Le tabelle `subscriptions`, `payments`, `user_profiles` si scrivono solo lato server.

## Modo di lavorare

- Mai lavorare su `main`: Streamlit Cloud pubblica quello che c'è lì. Un branch per compito.
- Un compito alla volta. Mostra il diff, niente commit senza che io lo chieda.
- Dopo ogni modifica esegui `python -c "import py_compile; py_compile.compile('FILE', doraise=True)"`
  sui file toccati. Non esistono test né CI.
- Per cambi a generazione o LaTeX: genera una verifica di prova e controlla che il PDF compili.
- Non aggiungere dipendenze né modificare `requirements.txt`/`packages.txt` senza dirmelo.

## Mappa dei file

- UI (usano Streamlit): `main.py`, `sidebar.py`, `ui_helpers.py`, `styles.py`, `auth.py`
- Logica: `generation.py` (pipeline AI), `latex_utils.py` (parsing/compilazione LaTeX), `docx_export.py`
- Modelli di verifica (solo admin, non ancora usati dalla generazione): `banca_import.py` (legge una verifica .tex con
  `estrai_tex.py`, senza AI), `banca.py` (Supabase: tabelle in `modelli_verifica.sql`, da creare a mano), `ui_banca.py` (pagina,
  stage `BANCA`). `config.DISTRIBUZIONE_DIFFICOLTA` = quanti esercizi ★1/★2/★3 per scuola (non ancora usata). La banca di esercizi
  è stata abbandonata. I file in `materiale/` restano fuori da git.
- Prova da riga di comando con l'AI vera: `prova_generazione.py` (scenari di esempio, costi, PDF in `prove_output/`).
- Client AI: `ai_client.py` (adattatore su `google-genai`, senza streamlit): sceglie modello e ragionamento per compito
  (`config.COMPITI_AI`), registra token e costi (`riepilogo_uso`, mostrato nell'expander admin), non riprova sugli errori definitivi.
- Configurazione e prompt: `config.py`, `prompts.py`
- Abbonamenti (solo lettura): `subscription_management.py` (`calcola_entitlements`: piano, tetto e funzioni in un'unica
  fonte, funzione pura), `config.PIANI`/`FUNZIONI_PRO`, `database_schema.sql`, `migrazione_monetizzazione_fase0.sql`
- Licenze Pro (Lemon Squeezy, API pubblica, nessuna chiave segreta): `licenze.py` (senza streamlit). L'app scrive in `subscriptions`
  SOLO dopo aver validato il codice ed essersi assicurata che store/prodotto siano i nostri (`config.LEMON_STORE_ID`/`LEMON_PRODUCT_ID`,
  vuoti = nessun codice accettato); ricontrollo ogni 24 ore (`riconvalida_se_serve`), tolleranza 3 giorni. Migrazione: `migrazione_monetizzazione_fase2.sql`.
- Pagina «Passa a Pro»: `ui_upgrade.py` (stage `UPGRADE`; esempi Lite/Pro in `assets/esempi/free_N.png` e `pro_N.png`).
  Blocchi funzione in `main.py` (`_pro_bloccato`, `_pulsante_pro`, `_vai_a_upgrade`), eventi in `usage_events` (`_registra_evento`).
  Assaggio: la prima verifica di ogni utente free (`_prima_verifica_id`) ha tutto il Pro, modello compreso; tutto spento finché `MONETIZZAZIONE_ATTIVA` è False.
- Inviti tra colleghi: `inviti.py` (senza streamlit, tabelle `codici_invito`/`inviti`/`bonus_usati` in `migrazione_inviti.sql`, da eseguire a mano). Link `?ref=CODICE`; l'invitato si collega solo se nuovo (nessuna verifica); l'invito vale quando completa la prima; chi invita guadagna `config.BONUS_PER_INVITO` verifiche con tutto il Pro (max `MAX_INVITI_CON_BONUS` amici). In `main.py`: `_assaggio_attivo` (`_assaggio_tipo` = prima|bonus), `_info_invito`; pannello nella sidebar. Senza le tabelle tutto resta spento (le funzioni non sollevano).
- Kit/scheda di allenamento: `scheda.py` (logica, senza streamlit), prompt in `prompts.py`
- Segnalazioni ANONIME («Qualcosa non va in questa verifica?», in FINAL): `segnalazioni.py` (senza streamlit), tabella `segnalazioni` in
  `migrazione_segnalazioni.sql` (da eseguire a mano). Mai user_id, email o IP; il debug della generazione (`_debug_gen`) si tiene in sessione per tutti
  ma lo mostra solo l'admin. Casi da analizzare: cartella `materiale/da_analizzare/` (fuori da git).
- Non usati: `extra-streamlit-components` e `streamlit-cookies-controller`
  (solo in requirements, `auth.get_cookie_controller()` è uno stub).
- Mancante: `mathpix_utils.py` è importato da `main.py` ma non esiste, quindi Mathpix è sempre disattivato.

## Architettura

Stati in `main.py`: INPUT -> PREVIEW -> REVIEW -> FINAL -> export (PDF/DOCX), più la pagina
MIE_VERIFICHE (storico). PREVIEW può andare direttamente a FINAL. Con la modalità
condivisione (`_share_view_active`) il router degli stati viene saltato.
L'INPUT (`_render_stage_input`) parte dal bivio (`input_percorso is None`) e ha i percorsi
A (upload guidato), B (form manuale), FACSIMILE, QA; `LIBERA` reindirizza a B.
Tutto lo stato UI sta in `st.session_state`.

Pipeline in `generation.py`: titolo -> corpo esercizi -> controllo qualità -> post-processing
deterministico (fix_items_environment, riscala_punti, inietta_griglia) -> compilazione PDF
-> opzionali (Fila B, versione ridotta BES/DSA, soluzioni).

Piani reali: `free`, `pro`, `premium` (da `subscription_management`) e `admin` (email in
`ADMIN_EMAILS`). `gold` esiste nel codice ma non è raggiungibile; `premium` vale come `pro` (normalizzato in
`calcola_entitlements`).
Modello: lo sceglie la sidebar in base al piano; `config.get_model_id_per_piano` è solo un ripiego
se il modello scelto non è valido per il piano. Free = flash-lite; pro = sempre gemini-2.5-flash
(nessun upgrade STEM); gemini-2.5-pro (costa 3-4 volte Flash, vantaggio non netto) non si sceglie MAI in automatico,
nemmeno per gold o per l'admin: solo l'admin può sceglierlo a mano dalla sidebar. L'autoverifica gira a ragionamento basso
(`config.COMPITI_AI`: 1024; con 3072 la serie 3.x andava al livello alto, 7-9 mila token e fino a 70 s).
Limite mensile: lo decide `calcola_entitlements` (`config.PIANI`: free = `LIMITE_MENSILE`, pro illimitato per ora;
abbonamento scaduto = free). Il contatore conta le righe di `verifiche_storico` **comprese quelle eliminate**:
«Elimina» è logico (`deleted_at`), altrimenti si aggirerebbe il tetto. Se il conteggio non si legge la creazione è
**bloccata** con «riprova» (mai «0»); `_puo_generare_ora()` ricontrolla dentro `_lancia_generazione`. Admin escluso.
Funzioni del Pro (`config.FUNZIONI_PRO`, `ENT.puo("fila_b")`): aperte a tutti finché `MONETIZZAZIONE_ATTIVA` è False.
Il piano dichiara la **famiglia** del modello (lite/flash), mai un ID: lo risolve `ai_client`.
Modifiche con l'AI nella schermata «Modifica gli esercizi» (Più facile, Cambia i numeri, Cambia esercizio, Applica modifica, Aggiungi):
ognuna è una chiamata all'AI e ha un tetto **per verifica** (`config.MODIFICHE_PER_VERIFICA`: free 10, pro e «assaggio» 40, admin nessuno),
contato in `usage_events` (tipo `modifica`, per `verifica_id`) così riaprire la verifica non azzera il conto; se il registro non risponde vale il
contatore della sessione. Eliminare esercizi, cambiare i punteggi e annullare non contano. L'anteprima del singolo esercizio col grafico è
`latex_utils.anteprima_esercizio_png` (compila solo quell'esercizio, in cache per testo).

DOCX: `docx_export.py` converte il LaTeX (oggi passando da Gemini) e costruisce il file con python-docx.

## Piani e abbonamenti

**Prova pubblica (dal 15 ottobre 2026):** `MONETIZZAZIONE_ATTIVA = False` e `LEGALE_PRONTO = False`: ogni funzione è aperta a tutti, nessun prezzo, banner,
invito o link a Termini/Rimborsi; restano i tetti (5 verifiche al mese, 10 modifiche con l'AI per verifica, `TETTO_BREVE`). Il prezzo non si dice: si ricava
dal questionario (domande Van Westendorp). La guida del primo utente (riquadro blu + elementi che lampeggiano, `_guida_benvenuto`) resta accesa anche a pagamenti spenti, con testi senza
regali né piani: la mostra `_banner_piano` a chi è alla sua prima verifica (`_GUIDA_PRIMO`, `_prima_esperienza`). Misure d'uso: `riepilogo_uso.sql`
(query da eseguire a mano in Supabase); questionario dei tester nel sito: pagina pubblica e anonima `?pagina=questionario` (`ui_questionario.py`, domande in `questionario.py`), tabella `questionario_tester` in `migrazione_questionario.sql` (da eseguire a mano), query di lettura in `riepilogo_uso.sql`; il pulsante «Lasciaci un feedback» e il link nel piè di pagina puntano lì; prima del PRIMO download del PDF (poi cookie `vf_mini_ok` di un anno) due domande veloci (tempo risparmiato, utilità) salvate come `versione = 0` — interruttore `config.FEEDBACK_PRIMA_DEL_DOWNLOAD`; i riquadri blu del feedback (`_box_feedback`) sono spenti (`config.MOSTRA_BOX_FEEDBACK`): si chiede il parere solo lì, più il pulsante 💬 e il link nel piè di pagina; gli eventi in `usage_events` sono verifica, modifica, fila_b, bes, soluzioni, griglia, scheda, word, condivisione, materiale. Per tornare ai piani basta riaccendere i due interruttori (la privacy mostra Lemon Squeezy solo con i pagamenti accesi).

Il codice Stripe è stato rimosso: l'app non incassa né scrive abbonamenti, legge soltanto la
tabella `subscriptions` (`subscription_management.get_user_subscription`, status `active`/`trialing`).
Il piano si assegna a mano dal database Supabase con una riga in `subscriptions`:
`user_id`, `plan_id` = `pro`, `status` = `active`, `stripe_subscription_id` con un
valore segnaposto univoco `manual-<uuid>` (la colonna è `NOT NULL UNIQUE` nello schema).
Una riga con `current_period_end` nel passato non vale più (torna free); senza scadenza (piano manuale) vale sempre.
`premium` non si vende: se assegnato vale come `pro`. Le policy RLS non permettono agli utenti di scrivere in
`subscriptions`/`payments`/`user_profiles` (vedi `migrazione_monetizzazione_fase0.sql`, da eseguire in Supabase).
Per togliere il piano si porta `status` a `canceled`. Senza riga attiva l'utente è `free`.
Non si toccano lo schema né le tabelle dal codice dell'app.

## Problemi noti (audit ottobre 2026, da correggere)

- `generation.py`: `_crea_versione_minimale` usa `\geometry` senza il pacchetto.
- `generation.py`: `e_mat` cerca "fis" e include Educazione Fisica; usare `MATERIE_STEM`.
- `generation.py`: testo di prompt fuori da `prompts.py`; `genera_verifica` e
  `genera_verifica_streaming` sono quasi duplicate.
- `prompts.py`: nell'esempio tabelle `\\\\begin` produce `\\begin` (LaTeX errato per il modello).
- (risolti in fase 0 della monetizzazione: conteggio che valeva 0 in errore, limite non ricontrollato, tetto aggirabile
  eliminando le verifiche.)

## Lingua

Codice, commenti, stringhe UI e prompt sono in italiano.