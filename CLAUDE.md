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
- Abbonamenti (solo lettura): `subscription_management.py` (piano utente e limiti), `database_schema.sql`
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
`ADMIN_EMAILS`). `gold` esiste nel codice ma non è raggiungibile; `premium` oggi cade sul ramo free.
Modello: lo sceglie la sidebar in base al piano; `config.get_model_id_per_piano` è solo un ripiego
se il modello scelto non è valido per il piano. Free = flash-lite; pro = sempre gemini-2.5-flash
(nessun upgrade STEM); gemini-2.5-pro solo per gold e per admin con materia in `MATERIE_STEM`;
admin può scegliere a mano qualsiasi modello.
Limite mensile: lo decide `subscription_manager.can_generate_verification` (`FREE_PLAN_LIMITS`,
illimitato per pro/premium; contatore su `verifiche_storico`). `LIMITE_MENSILE` è solo il ripiego
se il caricamento dell'abbonamento fallisce. Admin escluso.

DOCX: `docx_export.py` converte il LaTeX (oggi passando da Gemini) e costruisce il file con python-docx.

## Piani e abbonamenti

Il codice Stripe è stato rimosso: l'app non incassa né scrive abbonamenti, legge soltanto la
tabella `subscriptions` (`subscription_management.get_user_subscription`, status `active`/`trialing`).
Il piano si assegna a mano dal database Supabase con una riga in `subscriptions`:
`user_id`, `plan_id` = `pro`, `status` = `active`, `stripe_subscription_id` con un
valore segnaposto univoco `manual-<uuid>` (la colonna è `NOT NULL UNIQUE` nello schema).
Assegnare solo `pro`: `premium` non va assegnato finché non viene allineato (oggi la sidebar
lo tratta come free, mentre `get_user_plan_limits` lo tratta come illimitato).
Per togliere il piano si porta `status` a `canceled`. Senza riga attiva l'utente è `free`.
Non si toccano lo schema né le tabelle dal codice dell'app.

## Problemi noti (audit ottobre 2026, da correggere)

- `generation.py`: `_crea_versione_minimale` usa `\geometry` senza il pacchetto.
- `generation.py`: `e_mat` cerca "fis" e include Educazione Fisica; usare `MATERIE_STEM`.
- `generation.py`: testo di prompt fuori da `prompts.py`; `genera_verifica` e
  `genera_verifica_streaming` sono quasi duplicate.
- `prompts.py`: nell'esempio tabelle `\\\\begin` produce `\\begin` (LaTeX errato per il modello).
- `main.py`: `_get_verifiche_mese` ritorna 0 in caso di errore Supabase, quindi il contatore si azzera e il limite mensile viene aggirato.
- `main.py`: `_lancia_generazione` non ricontrolla il limite mensile; lo fa solo il `disabled` del pulsante Genera.

## Lingua

Codice, commenti, stringhe UI e prompt sono in italiano.