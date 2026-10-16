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
- Aperture ANONIME dell'app (`aperture.py`, senza streamlit, tabella `aperture_app` in `migrazione_aperture.sql`, da eseguire a mano): una riga per sessione quando si vede la schermata di accesso senza essere dentro, con la sola sorgente `?src=` del link (mai user_id, email o IP); serve a capire dove si perde chi arriva dai post. Senza la tabella non succede niente.
- Esercizio del libro da una foto (`esercizio_foto.py`, senza streamlit; prompt in `prompts.py`: `prompt_leggi_esercizi_foto`, `prompt_ricontrolla_trascrizione`, `prompt_correggi_trascrizione`, `testo_esercizi_fissi`): nel form («Hai un esercizio del libro da includere?», `main._blocco_esercizio_foto`) il docente carica foto/PDF; l'AI (compito `foto_esercizio`, sempre Flash) trascrive l'esercizio in LaTeX SENZA risolverlo né toglierlo dalla sua forma (via numeri del libro, stelline e soluzioni stampate), poi un secondo giro lo ricontrolla sulla foto e corregge le differenze; il docente vede la foto accanto a come comparirà e conferma o corregge a parole. Figure: grafici di funzioni (`[[GRAFICO: …]]`), figure geometriche semplici (TikZ) e tabelle si riproducono; un quadro, una fotografia o uno schema complesso NO (`stato_esercizio`: non utilizzabile, mai una figura inventata; niente immagini da internet né ritagli della foto). L'esercizio NON passa dal modello che scrive la verifica: `genera_verifica(esercizi_fissi=…)` fa scrivere all'AI solo gli altri e inserisce il blocco identico dopo controllo qualità e autoverifica (`inserisci_esercizi`, `_con_punti_medi`: peso pari alla media degli altri), poi rinumera. Funzione dei piani come `materiale` (`_pro_bloccato("materiale")`). Sostituisce la vecchia scelta «Includi questi esercizi nella verifica» del file di materiale (il ramo resta nel codice ma non è più raggiungibile). `config.MAX_ESERCIZI_DA_FOTO` = 3.
- Stili grafici del PDF (`stili_verifica.py`, senza streamlit): classico, moderno (Helvetica, titoli neri, niente colori né filetti: si stampa in bianco e nero) — selettore «Stile della verifica» per ora SOLO admin — e «leggibile» (alta leggibilità per DSA: carattere un po' più grande, più spazio, testo non giustificato), che NON si sceglie per tutta la verifica ma si scarica a parte dalla tendina «Versioni della verifica» (`main._blocco_leggibile`, nessuna AI: `cambia_stile` toglie lo stile di prima e applica il nuovo sullo stesso LaTeX, logo compreso; vale per la verifica e per la versione BES/DSA). Gli stili aggiungono al preambolo solo pacchetti psnfss/titlesec/sansmath tra righe-commento `%%STILE-…`; l'intestazione resta identica (logo, Fila B e ricompilazione la riconoscono) e nulla va dopo il primo `\end{center}`. Anteprime in `assets/stili/`. La versione BES/DSA ha due modi: meno richieste (circa 20% in meno) oppure «lo descrivo io» (`_genera_variante(istruzioni=…)`, `prompt_versione_ridotta(istruzioni_docente=…)`: le istruzioni del docente hanno la precedenza e tolgono il tetto sui sottopunti).
- «Impagina la mia verifica» (`impagina.py`, senza streamlit; scheda in cima al form, `main._render_impagina` / `_esegui_impagina`; prompt `prompt_leggi_verifica_completa`, `prompt_correggi_verifica`): il docente carica PDF o foto (fino a 8, anche screenshot messi insieme) di una verifica scritta o impaginata male; l'AI (compito `foto_esercizio`, Flash) trascrive TUTTI gli esercizi in LaTeX senza cambiarli (riusa lettura, secondo controllo e regole di `esercizio_foto.py`, ma TIENE i punteggi del foglio e ignora l'intestazione originale), il docente confronta originale e risultato, corregge a parole se serve e conferma. `genera_da_trascrizione` impagina con intestazione, logo e stile di sempre e restituisce lo stesso dizionario di `genera_verifica`, quindi `_lancia_generazione(generatore=…)` la tratta come una verifica normale (storico, Fila B, BES/DSA, soluzioni, Word). `_assembla_e_compila(fedele=True, punti_fedeli=True)`: niente consegne aggiunte né punti ripesati. Punteggi: «come sul foglio» (i decimali si moltiplicano per 2/4/10/20/100 perché la tabella li vuole interi), «senza» oppure «li assegno io (100)». Figure non riproducibili: l'esercizio non entra, oppure entra con uno spazio vuoto (scelta del docente); mai figure inventate né ritagli dalle pagine. Il commento facoltativo («togli l'esercizio 4», …) si applica dopo con `modifica_verifica_libera`. Funzione dei piani come `materiale`.
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

Struttura-tipo della verifica (`prompts.struttura_verifica`, modellata su verifiche vere di matematica): 4-6 esercizi con ruoli e punti DIVERSI (apertura breve,
esercizio centrale 35-50% dei punti con 4-8 richieste a rampa, esercizio di lettura/analisi o studio di funzione 25-30%, problema, e in fondo «Per l'eccellenza»
3-10 pt, interruttore `toggle_eccellenza` acceso di default; l'esercizio per l'eccellenza si AGGIUNGE agli esercizi scelti). Le rampe di difficoltà d'esempio
(`rampe_esempio`, anonime, per parola chiave dell'argomento) servono solo a calibrare il livello. Il toggle «primo esercizio di base» è stato tolto dall'interfaccia (resta `toggle_primo_base`, sempre spento). L'esercizio per l'eccellenza è DAVVERO in più (scelti 4 → 5): se il modello ne scrive uno in meno, `generation._completa_esercizi_mancanti` fa scrivere solo quello che manca.
Con esercizi scelti a mano o «Rifai questa verifica» la struttura-tipo non si usa (`_build_prompt_esercizi(struttura_tipo=False)`).

Consegne snelle (`prompts.REGOLA_CONSEGNE_BREVI`, usata anche nelle modifiche): UNA riga di consegna per esercizio («Risolvi le seguenti disequazioni.») e, nei calcoli,
richieste fatte della SOLA formula (`\(\displaystyle …\)`), senza «studia il segno», «imposta le C.E.», ecc.; le note del piano sono interne e non si copiano nel testo.

Consegne mancanti (`latex_utils.aggiungi_consegne_mancanti`, rete di sicurezza deterministica in `_assembla_e_compila` e `_postprocessa_latex`): una formula nuda va
bene solo se una riga di consegna copre tutte le richieste dello stesso tipo; con compiti diversi o UNA sola richiesta (anche «Per l'eccellenza») la richiesta riceve
il suo verbo («Risolvi la disequazione:», «Discuti, al variare di k, la disequazione:»). Se non capisce il compito non tocca nulla. Pulizia (`_ripulisci_consegne`): se la consegna in testa copre il compito, toglie la frase («Studia il segno e risolvi…:») davanti alle richieste fatte di
SOLA formula (solo se la frase finisce con i due punti e il compito è lo stesso); senza consegna, con richieste tutte uguali, la porta in testa.

ATTENZIONE: il piano, il controllo della difficoltà e i RUOLI rigidi sono SPENTI (`config.PIANO_ATTIVO = False`, `RUOLI_ESERCIZI_ATTIVI = False`): con le note del piano
e i ruoli i sottopunti diventavano mini-esercizi con descrizione propria. Restano punti DIVERSI per esercizio, l'esercizio «Per l'eccellenza» e le regole di prompt su consegne e difficoltà.
Per riaccenderli: mettere i due flag a True (il codice c'è ed è provato).

PIANO prima del testo (`piano_verifica.py`, senza streamlit, per ogni materia): con la struttura-tipo, dopo il titolo una chiamata breve (compito AI «piano»)
riempie lo scheletro (ruoli e punti decisi dal codice) con titolo, tipo e richieste (livello 1-3 + nota) di ogni esercizio; `normalizza_piano` la controlla
(conteggi, livelli crescenti, mix ~40/40/20, max esercizi chiusi) e calcola i punti per richiesta dal livello; `piano_a_testo` la passa a chi scrive gli
esercizi; `applica_punti_piano` rimette i punti nel LaTeX (in `_assembla_e_compila`). Qualsiasi problema = nessun piano, si genera come prima.
Difficoltà vera (`prompts.REGOLA_DIFFICOLTA_VERA`: livello di PARTENZA ALTO, la richiesta facile non è mai banale (almeno 2 passaggi), mix ~25/45/30, difficile = almeno il doppio delle operazioni della media, mai un parametro nelle richieste facili/medie; l'apertura «di base» voluta dal docente resta semplice) e un
secondo sguardo dopo la scrittura (`generation.ritocca_difficolta`, compito AI «difficolta», solo con un piano e senza vincoli del docente): l'AI riscrive le
richieste fuori livello; la risposta vale solo se la forma è identica (stessi esercizi, richieste e grafici), altrimenti si tiene il testo di prima.
PRECEDENZA AL DOCENTE (regola assoluta): le sue note vincono su struttura, piano, livelli e punti. Se dicono qualcosa sulla struttura (flag `docente_vincola`
dell'AI + parole chiave) il codice NON riscrive livelli, tipi o numero di richieste, usa i punti che il docente indica e non impone i punti per richiesta;
«senza esercizio per l'eccellenza» nelle note spegne l'interruttore.

Modifica rapida in FINAL (box «Vuoi cambiare qualcosa? Chiedilo», sotto l'anteprima, sopra «Scarica PDF»): `main._box_modifica_rapida` (solo interfaccia),
logica in `generation.modifica_verifica_libera` (senza streamlit; i grafici escono come segnaposto `[[FIGURA n]]` e rientrano dopo), prompt in
`prompts.prompt_modifica_verifica`. Conta nel tetto `MODIFICHE_PER_VERIFICA`, rifà il PDF con `_ricompila_verifica_a(riscala_totale=True)`, aggiorna `latex_a`
nello storico; se qualcosa va storto la verifica torna com'era, e «Annulla l'ultima modifica» ripristina la Fila A (le altre versioni vanno rifatte).

Punteggi: il LaTeX salvato tiene «(N pt)» accanto a ogni richiesta (servono per contare, riscalare, modificare); nel PDF (`latex_utils.formatta_punti`,
solo se c'è la «% GRIGLIA») e nel Word si tolgono e restano solo nella tabella in fondo. Le caselle V/F vanno a destra a fine riga (`\hfill`; nel Word tabulazione a destra).

DOCX: `docx_export.latex_to_docx_modificabile` (senza AI): pandoc converte il testo (formule = equazioni di Word), ogni grafico TikZ è compilato a parte
e inserito come immagine centrata, la tabella dei punteggi è una sola tabella stretta con i totali per esercizio, poi rifiniture con python-docx (A4, font,
intestazione, logo). Serve `pandoc` (già in `packages.txt`). Il vecchio `latex_to_docx_via_ai` resta nel file ma non si usa. Pulsante «Versione Word modificabile» in FINAL.

## Piani e abbonamenti

**Prova pubblica (dal 15 ottobre 2026):** `MONETIZZAZIONE_ATTIVA = True` (blocchi delle funzioni accesi: la prima verifica ha tutto, le successive no) ma
`PREZZI_VISIBILI = False`: nessun prezzo, piano Pro, Lemon Squeezy o checkout nell'interfaccia; al posto dello sblocco a pagamento c'è lo SBLOCCO CON IL
QUESTIONARIO: il questionario completo (domande chiave `questionario.OBBLIGATORIE`) rilascia un codice `VF-XXXX-XXXX` (`sblocco.py`, tabella `codici_sblocco`
in `migrazione_sblocco.sql`, NON collegato alle risposte) che l'utente inserisce nella pagina «Sblocca» (`ui_sblocco.py`, stage UPGRADE) e vale
`VERIFICHE_PER_CODICE` verifiche complete (crediti letti da `inviti.riepilogo`, stesso meccanismo dei bonus degli inviti; `INVITI_ATTIVI = False`).
INVITI TRA COLLEGHI ATTIVI (`INVITI_ATTIVI = True`): il questionario completo vale `VERIFICHE_PER_CODICE = 2` verifiche complete e ogni collega che si iscrive col link di invito e crea
la sua prima verifica ne vale altre `BONUS_PER_INVITO = 2` (max `MAX_INVITI_CON_BONUS = 5` colleghi). Il link è `LANDING_URL/?ref=CODICE` (la landing lo passa all'app, con `src=invito`);
interfaccia in `ui_inviti.py` (email con `mailto:`, WhatsApp, link da copiare, contatori, finestra), richiamata dal box «Altre verifiche con tutte le funzioni» (INPUT e FINAL),
dalla pagina «Sblocca» e dalla sidebar. Servono le tabelle di `migrazione_inviti.sql` (da eseguire a mano in Supabase): senza, l'invito non compare.
Restano i tetti (5 verifiche al mese, 10 modifiche con l'AI per verifica, `TETTO_BREVE`). Il prezzo non si dice: si ricava dal questionario (Van Westendorp).
`LEGALE_PRONTO = False`. Per tornare ai piani a pagamento: `PREZZI_VISIBILI = True`. Per l'uso gratuito senza blocchi: `MONETIZZAZIONE_ATTIVA = False`.

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