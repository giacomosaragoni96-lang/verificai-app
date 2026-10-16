# prompts.py
# Ogni funzione costruisce e restituisce un prompt (stringa).
# Nessuna dipendenza da Streamlit o da stato globale.


def prompt_titolo(materia: str, argomento: str) -> str:
    return (
        f"Sei un docente. Crea un titolo professionale e conciso per una verifica scolastica.\n"
        f"Materia: {materia}\n"
        f"Argomento inserito dall'utente (potrebbe avere errori ortografici o essere informale): \"{argomento}\"\n"
        f"Restituisci SOLO il titolo senza virgolette, senza punteggiatura finale, "
        f"senza prefissi come 'Verifica di'. Esempio: 'Le equazioni di secondo grado'"
    )


def prompt_corpo_verifica(
    materia: str,
    argomento: str,
    calibrazione: str,
    durata: str,
    num_esercizi: int,
    punti_totali: int,
    mostra_punteggi: bool,
    con_griglia: bool,
    note_generali: str,
    istruzioni_esercizi: str,
    e_mat: bool,
    titolo_header: str,
    preambolo_fisso: str,
    mathpix_context: str | None = None,
) -> str:
    s_note = (
        f"\n\n═══════════════════════════════════════════\n"
        f"ISTRUZIONI PRIORITARIE DEL DOCENTE — RISPETTA QUESTE PRIMA DI TUTTO:\n"
        f"{note_generali.strip()}\n"
        f"Queste istruzioni hanno la PRECEDENZA ASSOLUTA su TUTTO il resto di questo prompt: struttura-tipo, piano dettagliato, ruoli, "
        f"livelli di difficoltà, numero di richieste, distribuzione dei punti, esercizio per l'eccellenza, regole di stile. Se c'è un "
        f"conflitto vince SEMPRE il docente e il resto si adatta (mai il contrario): ciò che chiede va fatto bene e per primo. "
        f"Se dicono come aprire la verifica "
        f"(«parti con…») vale quello, anche rispetto a «Saperi Essenziali»; se chiedono di evitare qualcosa "
        f"(dimostrazioni, date precise, calcoli con i vettori…) NON farlo in nessun esercizio, nemmeno con verbi come "
        f"«dimostra», «mostra che», «verifica che».\n"
        f"═══════════════════════════════════════════\n"
    ) if note_generali.strip() else ""

    # ── CONTESTO MATHPIX OCR ──────────────────────────────────────────────────
    # Se il docente ha caricato un documento (verifica precedente, libro, appunti)
    # e Mathpix ha estratto il testo matematico, lo iniettiamo come contesto ad
    # alta priorità. Tronchiamo a 3000 chars per non saturare la context window.
    _MAX_MATHPIX_CHARS = 3000
    if mathpix_context and mathpix_context.strip():
        _mctx = mathpix_context.strip()
        if len(_mctx) > _MAX_MATHPIX_CHARS:
            _mctx = _mctx[:_MAX_MATHPIX_CHARS] + "\n… [contesto troncato per brevità]"
        s_mathpix = (
            f"\n\n╔══════════════════════════════════════════════════════════╗\n"
            f"║  DOCUMENTO DI RIFERIMENTO — ESTRATTO DA MATHPIX OCR       ║\n"
            f"╚══════════════════════════════════════════════════════════╝\n"
            f"Il docente ha allegato un documento (verifica precedente / libro / appunti).\n"
            f"Di seguito il suo contenuto matematico estratto con OCR preciso.\n"
            f"ISTRUZIONI D'USO:\n"
            f"• Analizza lo STILE degli esercizi (tipologia, livello, formulazione).\n"
            f"• Usa la stessa TERMINOLOGIA e la stessa struttura grammaticale.\n"
            f"• Rispetta il LIVELLO DI DIFFICOLTÀ implicito nel documento.\n"
            f"• NON copiare esercizi pari pari — generane di nuovi ISPIRATI al documento.\n"
            f"• Se il documento contiene formule/grafici, prendi spunto per i dati.\n"
            f"• Mantieni coerenza con gli argomenti trattati nel documento.\n\n"
            f"CONTENUTO OCR:\n"
            f"{'─' * 60}\n"
            f"{_mctx}\n"
            f"{'─' * 60}\n"
        )
    else:
        s_mathpix = ""

    if mostra_punteggi:
        punti_rule = (
            f"- PUNTEGGI — REGOLA ASSOLUTA E INVIOLABILE:\n"
            f"  * Ogni \\item DEVE avere \"(X pt)\" sulla stessa riga, subito dopo il testo.\n"
            f"  * Formato ESATTO e UNICO: (X pt) — es: \\item[a)] Risolvi l'equazione. (5 pt)\n"
            f"  * NON usare: [X pt], X punti, X p., pt X, (Xpt), o qualsiasi altro formato.\n"
            f"  * SOMMA TOTALE TASSATIVA: la somma di TUTTI i (X pt) di TUTTI gli esercizi deve essere\n"
            f"    ESATTAMENTE {punti_totali} pt. NON {punti_totali-1}, NON {punti_totali+1}. ESATTAMENTE {punti_totali}.\n"
            f"  * PRIMA DI TERMINARE: somma mentalmente tutti i (X pt) che hai scritto. Se non fa {punti_totali}, correggi.\n"
            f"  * PESO DEI PUNTI: NON dare lo stesso punteggio a tutto. Gli ESERCIZI valgono cifre DIVERSE (l'esercizio centrale il 35-50% "
            f"del totale, l'apertura poco) e dentro ogni esercizio le richieste crescono di valore con la difficoltà:\n"
            f"    - richieste facili: circa 3-6 pt; medie: 6-10 pt; difficili: 10-16 pt;\n"
            f"    - domande chiuse (scelta multipla, vero/falso, completamento): poco, circa 2-5 pt ciascuna (i vero/falso i più bassi), "
            f"tutte insieme al massimo circa un terzo del totale;\n"
            f"    - uno studio completo di funzione o un problema di modellizzazione in UNA richiesta: circa 20-30 pt;\n"
            f"    - l'esercizio per l'eccellenza: 3-10 pt.\n"
            f"    Più difficile e più lungo = più punti. Usa numeri interi.\n"
            f"  * NON inserire punti nel titolo \\subsection*, SOLO nei \\item.\n"
            f"  * REGOLA CRITICA: se un esercizio ha un solo sottopunto, usa comunque \\item[a)] con il suo punteggio.\n"
            f"    NON lasciare MAI un esercizio senza \\item con punteggio — la tabella punteggi sarà inutilizzabile."
        )
    else:
        punti_rule = "- NON inserire punti (X pt) in nessun esercizio né sottopunto."

    griglia_rule = (
        "- NON generare la griglia (sarà aggiunta automaticamente dopo)."
        if con_griglia
        else "- NON generare nessuna tabella punteggi."
    )

    multi_rule = "- NON includere esercizi multidisciplinari."
    
    tabelle_rule = (
        "- TABELLE LaTeX — REGOLA ASSOLUTA:\n"
        "  * PRIMA di ogni ambiente tabella (\\begin{tabular}, \\begin{array}, \\begin{table})\n"
        "    lascia SEMPRE una riga vuota. Questo garantisce che la tabella sia su una riga separata.\n"
        "  * Esempio CORRETTO:\n"
        "    \"Testo della domanda.\n\n"
        "    \\\\begin{tabular}{|c|c|}\n"
        "    \\\\hline\n"
        "    ...\n"
        "    \\\\end{tabular}\"\n"
        "  * Esempio SBAGLIATO:\n"
        "    \"Testo della domanda. \\\\begin{tabular}{|c|c|}\"\n"
        "  * Questa regola evita che le tabelle escano fuori dal margine o si sovrappongano al testo."
    )

    if e_mat:
        grafici_rule = (
            "- GRAFICI: mostra SOLO grafici di funzioni (parabole, rette, curve) con la riga [[GRAFICO: y = ... | x da A a B]] "
            "(niente codice TikZ: il programma disegna il grafico; formato nella regola GRAFICI DI FUNZIONI).\n"
            "  ⛔ VIETATI GRAFICI COMPLESSI: NON generare MAI linee del tempo, diagrammi di flusso, "
            "alberi genealogici, organigrammi, mappe geografiche, diagrammi spaziali o altri grafici non matematici. "
            "Questi spesso falliscono la compilazione e non sono adatti a verifiche scolastiche.\n"
            "  ⛔ MAPPE E DIAGRAMMI SPAZIALI: NON generare MAI mappe, planimetrie, diagrammi geografici "
            "o rappresentazioni spaziali. Se l'esercizio richiede una mappa, descrivila testualmente "
            "senza codice TikZ.\n"
            "  ⛔ NON generare MAI codice TikZ se l'esercizio chiede allo studente di DISEGNARE UN GRAFICO DA ZERO "
            "basato su calcoli (es. \"traccia il grafico della funzione dopo aver calcolato vertice e intersezioni\").\n"
            "  ⛔ Se l'esercizio richiede PRIMA calcoli e POI disegnare: fornisci solo i calcoli, senza TikZ.\n"
            "  ✅ GENERA GRAFICO se il testo chiede di ANALIZZARE/OSSERVARE/STUDIARE un grafico fornito come DATO. "
            "In questo caso il grafico non è uno spoiler ma un dato di partenza.\n"
            "  ✅ GENERA GRAFICO se l'esercizio fornisce già l'equazione e chiede solo di analizzare il grafico risultante.\n"
            "  ⛔ Se l'esercizio usa parole come 'rappresenta graficamente' DOPO calcoli: scrivi SOLO il testo della richiesta.\n"
            "  ✅ Se l'esercizio dice 'dal grafico si osservi', 'analizza il seguente grafico', 'studio del grafico': GENERA il grafico.\n"
            "  ⛔ ANNOTAZIONI ANTI-SPOILER: quando il grafico è un DATO fornito, NON aggiungere sul grafico"
            " etichette o \\node con le quantità che le domande chiedono di determinare.\n"
            "  Esempi vietati: coordinate del vertice ($V(x_v, y_v)$), equazione dell'asse di simmetria"
            " (\"asse x=k\"), coordinate di intersezioni con gli assi, massimi, minimi.\n"
            "  Il grafico mostra SOLO la curva e gli assi cartesiani con scala numerica (lo disegna il programma).\n"
            "  ⛔ TESTO TECNICO VIETATO: NON scrivere mai nel testo dell'esercizio frasi come"
            " \"ottenuto con TikZ\", \"generato con TikZ\", \"grafico TikZ\", \"prodotto con pgfplots\""
            " o qualsiasi altra menzione dello strumento di generazione.\n"
            "  Usa solo: \"Si osservi il seguente grafico:\" oppure \"Dal grafico riportato di seguito:\"\n"
            "  ⚠️ CONTROLLO QUALITÀ: la riga [[GRAFICO: ...]] deve contenere una funzione di x valida e l'intervallo.\n"
            "  📊 PER ESERCIZI MATEMATICI: se l'esercizio coinvolge funzioni, equazioni, o analisi grafica, "
            "è RACCOMANDATO includere un grafico (riga [[GRAFICO: ...]]) come dato di partenza per l'analisi."
        )
    else:
        grafici_rule = ""

    # ── Regola diversità tipologie — in base al numero di esercizi ─────────────
    # Gli esercizi «chiusi» (scelta multipla, vero/falso, completamento) contano INSIEME: in una verifica vera ce ne sono
    # uno o due, il resto sono esercizi aperti (calcolo, problemi, analisi, domande a risposta aperta).
    max_chiusi = 1 if num_esercizi <= 4 else (2 if num_esercizi <= 7 else 3)
    if num_esercizi <= 2:
        diversita_rule = (
            "- VARIETÀ TIPOLOGIE: con soli 1-2 esercizi usa domande aperte articolate "
            "in più sottopunti (a, b, c…) che coprono sia la procedura sia la comprensione concettuale."
        )
    else:
        diversita_rule = (
            "- TIPOLOGIE — REGOLA FONDAMENTALE: una verifica vera è fatta soprattutto di esercizi APERTI "
            "(calcolo, problemi, dimostrazioni, analisi, domande a risposta aperta, confronti).\n"
            f"  • Gli esercizi CHIUSI sono tre tipologie: scelta multipla, vero/falso, completamento. In TUTTA la verifica ce ne sono "
            f"AL MASSIMO {max_chiusi} IN TOTALE (le tre tipologie contano insieme): "
            f"{'uno solo, di una sola tipologia' if max_chiusi == 1 else ('due al massimo, di tipologie diverse, oppure uno solo' if max_chiusi == 2 else 'tre al massimo, di tipologie diverse')}. "
            + ("MAI tutti e tre i tipi chiusi nella stessa verifica.\n" if max_chiusi <= 2 else "\n")
            + f"  • Tutti gli altri esercizi (almeno {num_esercizi - max_chiusi}) sono APERTI.\n"
            "  • Per una materia umanistica gli esercizi aperti sono: definizioni, spiegazioni, analisi di un fenomeno o di una fonte, "
            "confronti, collegamenti, commento.\n"
            "  • Disponi gli esercizi in ordine di difficoltà crescente: i primi sono di applicazione diretta, gli ultimi impegnativi "
            "(più passaggi, ragionamento, problemi articolati). Se le istruzioni sul primo esercizio dicono che è «di base», quello resta facile.\n"
            "  • L'ordine segue la tassonomia di Bloom: ricorda → comprendi → applica → analizza."
        )

    return (
        f"Sei un docente esperto di {materia} e LaTeX. Genera SOLO il corpo degli esercizi "
        f"(senza preambolo, senza \\documentclass, senza \\begin{{document}}) per una verifica su: {argomento}.\n"
        f"{ f'Punti totali da distribuire: {punti_totali} pt.' if mostra_punteggi else ''}\n"
        f"{s_mathpix}"
        f"{istruzioni_esercizi}\n"
        f"\n{rampe_esempio(materia, argomento)}"
        f"\nCALIBRAZIONE LIVELLO E TEMPO:\n"
        f"{calibrazione}\n"
        f"- DURATA PREVISTA: {durata}. Regola la lunghezza dei calcoli, il numero di incognite e la complessità "
        f"testuale in modo che {num_esercizi} esercizi siano agevolmente fattibili nel tempo scelto.\n"
        f"- BILANCIAMENTO CONTESTO E MODELLAZIONE: NON esagerare con i problemi applicati alla realtà o fortemente "
        f"interdisciplinari. MASSIMO 1 o 2 esercizi possono essere contestualizzati. I restanti DEVONO essere "
        f"esercizi canonici, diretti e focalizzati sulla procedura pura.\n"
        f"{diversita_rule}\n"
        f"- UN SOLO TIPO PER ESERCIZIO — REGOLA ASSOLUTA: ogni esercizio ha UNA sola tipologia per tutti i suoi sottopunti "
        f"(tutto aperto, oppure tutto scelta multipla, oppure tutto Vero/Falso, oppure tutto completamento). "
        f"MAI mischiare tipologie nello stesso esercizio (es. «Vero, Falso o Completamento», «Scelta multipla e Vero/Falso»): "
        f"per usare un'altra tipologia crea un esercizio separato. Il titolo nomina quella tipologia sola.\n"
        f"- DOMANDE SEMPRE NUMERATE: in un esercizio con più domande (anche a scelta multipla) TUTTE le domande sono "
        f"\\item[a)], \\item[b)], … dello STESSO \\begin{{enumerate}}[a)], compresa la prima; le opzioni A-D stanno in un "
        f"enumerate annidato dentro la domanda. Mai una domanda scritta fuori dall'elenco.\n"
        f"- REGISTRO LINGUISTICO: il testo degli esercizi è CHIARO e DIRETTO, senza giri di parole.\n"
        f"- {REGOLA_CONSEGNE_BREVI}\n"
        f"- VIETATO ASSOLUTO: NON inserire MAI le soluzioni, le risposte o i risultati negli esercizi. "
        f"MAI scrivere frasi come 'la risposta è...', 'il risultato è...', 'soluzione:', '= X', 'quindi X', "
        f"'infatti X', 'cioè X', 'cioè X', 'dunque X'. L'esercizio deve terminare con la domanda, senza alcun accenno alla risposta.\n"
        f"- VIETATO ASSOLUTO: NON inserire MAI spiegazioni, dimostrazioni complete o passaggi risolutivi. "
        f"Lo studente deve produrre tutto il ragionamento.\n"
        f"- DATI PULITI — REGOLA ASSOLUTA: prima di scrivere ogni esercizio, risolvilo mentalmente tu stesso. "
        f"Scegli SOLO dati che portano a risultati interi o frazioni semplici, anche nei passaggi intermedi: se c'è "
        f"un'equazione di secondo grado da risolvere (anche dentro un problema di fisica o di realtà, per esempio "
        f"l'incontro di due corpi) calcola il discriminante e controlla che sia un quadrato perfetto; niente radici "
        f"irrazionali, decimali lunghi o v² non quadrati, a meno che l'esercizio non lo chieda. MAI scegliere dati che rendono "
        f"un sistema contraddittorio, sovradeterminato o senza soluzione unica (a meno che non sia esplicitamente "
        f"richiesto). Se un esercizio chiede di trovare un'equazione soddisfacendo N condizioni, verifica che le "
        f"N condizioni siano compatibili tra loro.\n"
        f"- CONTROLLO DUPLICATI: ogni esercizio deve essere CONCEPTUALMENTE UNICO. NON generare esercizi "
        f"che testino lo stesso concetto matematico con dati diversi. Esempio: se l'Esercizio 1 chiede di risolvere "
        f"un'equazione di secondo grado, l'Esercizio 3 NON può chiedere di risolvere un'altra equazione di secondo grado. "
        f"Deve testare un'abilità diversa (es. studio di funzione, geometria, probabilità). Non riusare nemmeno gli stessi dati "
        f"di un altro esercizio (stessi numeri, stessa funzione o lo stesso grafico con altro nome: per esempio un grafico velocità-tempo "
        f"con gli stessi valori del problema della frenata).\n"
        f"- DIFFICOLTÀ E PROFONDITÀ — REGOLA FONDAMENTALE: una verifica deve accertare se lo studente ha CAPITO, non solo se sa "
        f"ripetere una procedura. Gli esercizi sono in ordine di difficoltà crescente. Dentro ogni esercizio le richieste salgono di "
        f"livello: le prime di applicazione diretta, poi con un passaggio in più o un caso particolare, le ultime impegnative "
        f"(più passaggi, ragionamento, un parametro o un caso da discutere). Gli ultimi esercizi devono essere davvero "
        f"impegnativi. Evita esercizi da prima lezione fatti di calcoli banali e ripetitivi. "
        f"Se le istruzioni sul primo esercizio lo indicano come «di base», quello resta semplice e diretto.\n"
        f"- SCALA DI DIFFICOLTÀ: pochi esercizi ma che coprono TUTTA la scala: alcuni semplici (accertano le basi), alcuni di media "
        f"difficoltà, alcuni difficili. Nel complesso lo studente deve impiegare tempo e ragionare: una verifica risolvibile "
        f"in pochi minuti è sbagliata.\n"
        f"- PASSAGGI CHE RIVELANO LA COMPRENSIONE: scegli i dati in modo che servano i passaggi in cui gli studenti sbagliano di "
        f"più, perché è lì che si capisce se hanno capito. Non dare mai casi in cui basta applicare la procedura a occhi chiusi. "
        f"Esempi (matematica): nelle equazioni fratte metti denominatori con segno opposto o fattori da scomporre (per esempio x - 3 "
        f"in un termine e 9 - x nell'altro, così che si debba cambiare segno; un denominatore x² - 9 che va scomposto), e almeno "
        f"un caso in cui una soluzione trovata va scartata perché viola le condizioni di esistenza; nelle disequazioni un fattore "
        f"con molteplicità o un caso senza soluzioni; nei radicali le condizioni di esistenza e i segni; nei problemi un dato "
        f"inutile o da ricavare. Esempi (altre materie): un caso limite, un'eccezione, un concetto che si confonde con un altro. "
        f"I numeri restano puliti, ma la STRUTTURA dell'esercizio deve richiedere ragionamento.\n"
        f"- STRUTTURA DEGLI ESERCIZI: ogni esercizio è un ARGOMENTO e ha di norma 3-5 richieste (a, b, c, d, e) BREVI, di tipo o caso "
        f"DIVERSO dello stesso argomento, in ordine di difficoltà crescente; l'esercizio più importante può averne fino a 6-8. Esempio per le "
        f"equazioni fratte: a) denominatori da scomporre; b) denominatori di segno opposto (x - 3 e 9 - x); c) una soluzione da scartare; "
        f"d) una di grado superiore. Per le disequazioni: una fratta, una a prodotto, un sistema di tre. Mai un esercizio con una sola "
        f"richiesta, tranne lo studio completo di una funzione, un problema di modellizzazione o l'esercizio per l'eccellenza. Se nelle "
        f"istruzioni c'è una STRUTTURA-TIPO o un PIANO, seguili. Le richieste sono BREVI (una formula o una frase): a renderle difficili "
        f"sono i dati e il tipo, non la lunghezza del testo.\n"
        f"- LE RICHIESTE DIFFICILI DEVONO ESSERLO DAVVERO: la più difficile dell'esercizio centrale e l'esercizio per l'eccellenza devono "
        f"mettere in difficoltà anche uno studente preparato. Le richieste facili restano facili: serve una scala vera, dal banale al "
        f"quasi proibitivo.\n"
        f"- {REGOLA_DIFFICOLTA_VERA}\n"
        f"- VERO/FALSO fatto bene: il titolo dell'esercizio contiene le parole «Vero o Falso»; circa metà delle affermazioni sono "
        f"false; niente «sempre», «mai», «necessariamente», «esclusivamente» che rendono ambigua la risposta; almeno una falsa deve "
        f"richiedere di pensare a un controesempio. Ogni richiesta è UNA affermazione da giudicare (mai «Spiega…» dentro un Vero/Falso) "
        f"e si chiude con le caselle indicate sotto. Il segno $ racchiude solo le formule, mai le frasi in italiano.\n"
        f"- FONTI E BRANI (materie umanistiche): se un esercizio chiede di commentare, analizzare o leggere un brano, una fonte o un "
        f"documento, il TESTO del brano (una citazione breve e reale, in un blocco \\begin{{quote}}…\\end{{quote}}) deve comparire "
        f"nell'esercizio stesso: mai rimandare a una fonte che lo studente non ha sotto gli occhi. Riporta il testo ESATTO, "
        f"parola per parola, solo se lo conosci con certezza; se non sei sicuro, scegli un passo più breve che conosci bene. "
        f"Due tipi di domanda, da non confondere: (1) domande SUL brano (comprensione, analisi, lessico, stile): la risposta si ricava "
        f"dal testo riportato, e non attribuire al brano parole o dettagli che non contiene; (2) domande di CONTESTO (cosa succede "
        f"dopo, come reagisce un personaggio, cause e conseguenze, collegamenti con ciò che gli studenti hanno studiato dell'opera o "
        f"del periodo): vanno benissimo e sono anzi preziose, ma devono essere formulate come tali (per esempio «Nel seguito dell'episodio…», "
        f"«In base a ciò che hai studiato…»), così che nessuno le cerchi nel brano.\n"
        f"- PROBLEMA DI REALTÀ ORIGINALE: se il docente non indica la situazione, NON usare i classici più ripetuti "
        f"(l'agricoltore che recinta un orto contro un muro, il sasso lanciato dal balcone) né le loro varianti con un altro nome "
        f"(parco giochi, giardino, fiera, campo, pollaio… con una recinzione di lunghezza fissa e un muro): inventa un contesto "
        f"diverso e concreto.\n"
        f"- DATE E DETTAGLI (materie umanistiche): le date degli eventi cardine (una firma, una battaglia, un armistizio, una "
        f"rivoluzione) si possono chiedere, anche con giorno e mese se l'evento è noto per quella data. Non riempire la verifica di "
        f"date e dettagli minori (numeri di articoli o commi, nomi secondari): meglio cause, conseguenze, personaggi chiave, concetti. "
        f"Se il docente scrive di evitare le date, o di chiederne molte, segui lui.\n"
        f"- DOMANDE APERTE: bastano il testo e il punteggio; lo studente scrive su un foglio a parte, quindi NON lasciare righe né spazi vuoti.\n"
        f"- RILEGGI PRIMA DI CONSEGNARE: nessun refuso, nessuna parola inventata o forma scorretta (controlla ogni parola dell'italiano).\n"
        f"REGOLE TASSATIVE SUI GRAFICI — LOGICA ANTI-SPOILER:\n"
        f"- Se l'esercizio chiede allo studente di 'disegnare', 'rappresentare graficamente', 'tracciare',\n"
        f"  'costruire' o qualsiasi variante → NON inserire NESSUNA riga [[GRAFICO: ...]] in quell'esercizio.\n"
        f"  Questo vale anche se solo una parte dell'esercizio lo richiede.\n"
        f"- Inserisci la riga [[GRAFICO: ...]] SOLO se il grafico è un DATO fornito (es. 'dal grafico seguente...').\n"
        f"- COERENZA GRAFICI: se il testo scrive 'si osservi il seguente grafico' o 'dalla figura', il grafico DEVE\n"
        f"  comparire subito dopo come riga [[GRAFICO: y = ... | x da A a B]] (MAI codice TikZ).\n"
        f"  Mai un rimando a un grafico senza il grafico.\n"
        f"- AUTOCONTROLLO: prima di scrivere [[GRAFICO: ...]], verifica che il testo NON contenga\n"
        f"  'rappresenta', 'disegna', 'traccia', 'graficamente', 'costruisci'. Se sì: stop, niente grafico.\n"
        f"- FORMATO DELLA RIGA GRAFICO: {REGOLA_GRAFICO_CURVE}\n"
        f"- ANNOTAZIONI SUL GRAFICO: il grafico DEVE mostrare SOLO la curva e gli assi con scala numerica.\n"
        f"  Vietato annotare: vertice ($V(...)$), asse di simmetria ('asse x=k'), intersezioni con gli assi,\n"
        f"  massimi, minimi — se queste quantità sono oggetto di domanda. Lo studente le deve trovare da solo.\n"
        f"- TESTO TECNICO VIETATO: MAI scrivere 'ottenuto con TikZ', 'generato con TikZ', 'grafico TikZ',\n"
        f"  'prodotto con pgfplots' o simili. Usa solo: 'Si osservi il seguente grafico:'\n"
        f"\nREGOLE LATEX (TASSATIVE):\n"
        f"{griglia_rule}\n"
        f"{punti_rule}\n"
        f"- NUMERO ESERCIZI: genera ESATTAMENTE {num_esercizi} blocchi \\subsection*. CONTA i tuoi blocchi prima di chiudere.\n"
        f"- Titoli: \\subsection*{{Esercizio N: Titolo}}\n"
        f"- REGOLA SOTTOPUNTI (TASSATIVA):\n"
        f"  • Esercizio con UNA SOLA richiesta → scrivi il testo DIRETTAMENTE sotto \\subsection*, "
        f"SENZA \\begin{{enumerate}} e SENZA \\item. Esempio corretto:\n"
        f"    \\subsection*{{Esercizio 2: Equazione}}\n"
        f"    Trovare l'equazione della parabola che passa per A(1,0), B(-1,4), C(2,1). (10 pt)\n"
        f"  • Esercizio con DUE O PIÙ richieste → usa \\begin{{enumerate}}[a)] con \\item[a)], \\item[b)], \\item[c)] ecc.\n"
        f"  • ETICHETTE: usa SEMPRE e SOLO a) b) c) — MAI 1) 2) 3) né i) ii) iii).\n"
        f"  • VIETATO: \\item senza label esplicita tra parentesi quadre.\n"
        f"- PRIMO ESERCIZIO: nell'Esercizio 1 NON inserire MAI il simbolo (*) su nessun sottopunto.\n"
        f"{multi_rule}\n"
        f"{tabelle_rule}\n"
        f"- Scelta multipla: le opzioni DEVONO stare in un \\begin{{enumerate}}[a)] SEPARATO dopo la domanda.\n"
        f"- Vero/Falso: $\\square$ \\textbf{{V}} $\\quad\\square$ \\textbf{{F}}\n"
        f"- Completamento: \\underline{{\\hspace{{3cm}}}}\n"
        f"{grafici_rule}\n"
        f"{s_note}"
        f"\nFORMATO OUTPUT: restituisci SOLO i blocchi \\subsection*{{...}} con relativi esercizi.\n"
        f"NIENTE preambolo, NIENTE \\documentclass, NIENTE \\begin{{document}}: l'unica riga di struttura ammessa "
        f"è \\end{{document}}, da scrivere UNA volta sola come ultima riga.\n"
        f"SOLO CODICE LATEX del corpo."
    )


def prompt_controllo_qualita(
    materia: str,
    difficolta: str,
    corpo_latex: str,
    mostra_punteggi: bool = True,
    punti_totali: int = 100,
) -> str:
    if mostra_punteggi:
        punti_check = (
            f"CONTROLLO PUNTEGGI OBBLIGATORIO:\n"
            f"1. Conta quanti \\item ci sono nel corpo.\n"
            f"2. Somma TUTTI i valori (X pt) presenti.\n"
            f"3. La somma DEVE essere ESATTAMENTE {punti_totali} pt.\n"
            f"4. Ogni \\item DEVE avere esattamente un '(X pt)' alla fine.\n"
            f"5. Se la somma non è {punti_totali}, ribilancia i punteggi proporzionalmente.\n"
            f"6. NON inserire (X pt) nei titoli \\subsection* — solo negli \\item.\n\n"
        )
    else:
        punti_check = (
            "CONTROLLO PUNTEGGI: questa verifica NON deve avere punteggi.\n"
            "Se trovi qualsiasi occorrenza di '(X pt)', '(X punti)' o simili, RIMUOVILE tutte.\n"
            "NON aggiungere punteggi in nessun caso.\n\n"
        )
    return (
        f"Sei un docente esperto di {materia} e devi fare un CONTROLLO DI QUALITÀ RIGOROSO su questa verifica "
        f"scolastica prima che venga consegnata agli studenti.\n\n"
        f"MATERIA: {materia}\n"
        f"LIVELLO: {difficolta}\n"
        f"VERIFICA DA CONTROLLARE:\n{corpo_latex}\n\n"
        f"COMPITO: analizza OGNI esercizio e OGNI sottopunto. Per ciascuno verifica:\n\n"
        f"1. CORRETTEZZA MATEMATICA / DISCIPLINARE: i dati sono coerenti? L'esercizio ha UNA soluzione determinata "
        f"e corretta? Se risolvo l'esercizio io stesso, ottengo una risposta pulita e sensata?\n"
        f"   - Esempi di ERRORI GRAVI: sistema sovradeterminato o contraddittorio, dati incoerenti (es. due condizioni "
        f"incompatibili), risposta che richiede conoscenze non adatte al livello, calcoli che portano a risultati assurdi.\n\n"
        f"2. ADEGUATEZZA AL LIVELLO ({difficolta}): la complessità è appropriata per questo tipo di scuola?\n\n"
        f"3. UNIVOCITÀ: la domanda ha una sola risposta corretta e non è ambigua?\n\n"
        f"4. COERENZA LATEX: le parentesi graffe sono bilanciate? Gli ambienti enumerate/itemize sono aperti e chiusi "
        f"correttamente? Non ci sono comandi LaTeX non validi?\n\n"
        f"5. SCELTA MULTIPLA: se presente, ogni domanda a scelta multipla deve avere ESATTAMENTE 4 opzioni "
        f"e UNA SOLA risposta corretta. Le opzioni devono essere distinte e plausibili.\n\n"
        f"SE trovi problemi: CORREGGILI DIRETTAMENTE modificando i dati dell'esercizio finché l'esercizio sia "
        f"corretto, sensato e risolvibile. NON eliminare esercizi, correggili.\n\n"
        f"{punti_check}"
        f"SE tutto è corretto: restituisci il testo IDENTICO senza modifiche.\n\n"
        f"REGOLE OUTPUT:\n"
        f"- Restituisci SOLO il corpo LaTeX corretto (\\subsection* ecc.), senza preambolo.\n"
        f"- Mantieni ESATTAMENTE la stessa struttura LaTeX (\\item[a)], \\item[b)], ecc.).\n"
        f"- Assicurati che ogni esercizio con più sottopunti usi \\item[a)] \\item[b)] ecc. (MAI 1) 2) 3)).\n"
        f"- Esercizi con una sola richiesta: testo diretto senza enumerate né \\item[a)].\n"
        f"  (le righe [[GRAFICO: ...]] che restano vanno lasciate IDENTICHE)\n"
        f"- ANTI-SPOILER GRAFICI: se un esercizio contiene un grafico (riga [[GRAFICO: ...]] o TikZ) E il testo usa\n"
        f"  'rappresenta', 'disegna', 'traccia', 'graficamente', 'costruisci' → RIMUOVI il grafico.\n"
        f"- NON aggiungere commenti, spiegazioni o note al di fuori del LaTeX.\n"
        f"- TERMINA con \\end{{document}}.\n"
        f"- Se hai modificato dati, mantieni la stessa difficoltà complessiva e lo stesso tipo di esercizio."
    )


def prompt_versione_b(corpo_latex: str) -> str:
    return (
        f"Versione B: stessa struttura, cambia dati e quesiti. "
        f"SOLO corpo esercizi (\\subsection* ecc.), SENZA preambolo/\\documentclass/\\begin{{document}}. "
        f"Sostituisci 'Versione A' con 'Versione B'. TERMINA con \\end{{document}}. SOLO LATEX.\n\n"
        f"RICORDA: ogni esercizio deve avere almeno un \\item[a)] con punteggio (X pt).\n\n"
        f"{corpo_latex}"
    )


def prompt_versione_ridotta(
    corpo_latex: str,
    materia: str,
    perc_ridotta: int,
    mostra_punteggi: bool,
    punti_totali: int,
    versione_label: str = "",
    max_da_togliere: int | None = None,
    totale_sottopunti: int | None = None,
    istruzioni_docente: str = "",
) -> str:
    _v_tag = f" ({versione_label})" if versione_label else ""
    punti_str = (
        f"Ridistribuisci i punti in modo che la somma sia ESATTAMENTE {punti_totali} pt. totali."
        if mostra_punteggi
        else "NON inserire punteggi."
    )
    # Con un tetto esplicito la riduzione è leggera: la versione resta quasi identica all'originale.
    if (istruzioni_docente or "").strip():
        riduzione = (
            "Il docente ha scritto come vuole semplificarla: «" + istruzioni_docente.strip() + "». Segui QUESTE istruzioni, "
            "hanno la precedenza su ogni altra regola. TUTTI gli esercizi restano, nello stesso ordine; puoi semplificare le frasi, i "
            "numeri e le richieste, e togliere qualche sottopunto solo se serve davvero a seguire le istruzioni. "
            "Non aggiungere esercizi nuovi e non cambiare l'argomento."
        )
    elif max_da_togliere is not None:
        tetto = (
            f"La verifica ha {totale_sottopunti} sottopunti: elimina AL MASSIMO {max_da_togliere} "
            f"sottopunti in tutto (circa il {perc_ridotta}%), NON di più. "
            if totale_sottopunti else
            f"Elimina AL MASSIMO {max_da_togliere} sottopunti in tutto, NON di più. "
        )
        riduzione = (
            f"La struttura deve restare quasi identica all'originale: TUTTI gli esercizi restano, "
            f"con le stesse richieste e lo stesso ordine. {tetto}"
            f"Non togliere più di 1 sottopunto per esercizio e non svuotare nessun esercizio. "
            f"Se togli qualcosa, parti dai sottopunti più complessi."
        )
    else:
        riduzione = (
            f"La struttura deve essere simile all'originale ma con circa il {perc_ridotta}% di sottopunti IN MENO "
            f"rispetto al totale.\n"
            f"Scegli quali sottopunti eliminare partendo dai più complessi. Mantieni sempre almeno 1 sottopunto per esercizio."
        )
    return (
        f"Sei un docente esperto. Hai già generato questa verifica{_v_tag}:\n\n"
        f"{corpo_latex}\n\n"
        f"Devi creare una versione RIDOTTA per studenti con sostegno o certificazione (BES/DSA/NAI).\n"
        f"{riduzione}\n"
        f"{punti_str}\n"
        f"NON copiare né riscrivere la tabella dei punteggi / griglia finale: viene aggiunta in automatico.\n"
        f"IMPORTANTE: PRIMA di ogni \\begin{{tabular}} lascia SEMPRE una riga vuota per evitare\n"
        f"sovrapposizioni con il testo. Le tabelle devono essere su righe separate.\n"
        f"NON aggiungere nessun simbolo (*), nessuna nota BES, nessuna indicazione che si tratta di una verifica ridotta.\n"
        f"TERMINA con \\end{{document}}.\n"
        f"SOLO CODICE LATEX del corpo (\\subsection* ecc.), senza preambolo."
    )


def prompt_soluzioni(
    corpo_latex: str,
    materia: str,
    versione_label: str = "",
) -> str:
    _v_tag = f" — {versione_label}" if versione_label else ""
    return (
        f"Sei un docente di {materia}. Fornisci le soluzioni SINTETICHE della seguente verifica{_v_tag}.\n\n"
        f"{corpo_latex}\n\n"
        f"REGOLE FERREE — RISPETTALE ALLA LETTERA:\n"
        f"- Per ogni esercizio scrivi 'Esercizio N: [Titolo]' poi le soluzioni in ordine a), b), c)...\n"
        f"- CALCOLI: mostra SOLO i passaggi essenziali. Niente testo narrativo. Solo la catena di calcolo.\n"
        f"- DOMANDE APERTE / TEORICHE: MASSIMO 3-4 RIGHE. Sii telegraficamente conciso.\n"
        f"- SCELTA MULTIPLA / VERO-FALSO: una riga sola: 'Risposta: X — perché [motivazione breve].'\n"
        f"- NON riscrivere mai il testo della domanda originale, vai diretto alla soluzione.\n"
        f"- SE UN ESERCIZIO HA DATI INCOERENTI O ERRATI: scrivi 'Dati da rivedere: [problema in una riga]' e passa avanti.\n"
        f"- Usa $...$ per le formule matematiche inline.\n"
        f"- Risposta totale per esercizio: MASSIMO 15-20 righe inclusi tutti i sottopunti.\n"
        f"- Rispondi con testo strutturato, senza preambolo LaTeX."
    )


def prompt_modifica(latex_originale: str, richiesta: str) -> str:
    return (
        f"Sei un docente esperto di LaTeX. Ti viene fornita una verifica già generata e una richiesta di modifica.\n\n"
        f"VERIFICA ORIGINALE:\n{latex_originale}\n\n"
        f"RICHIESTA DI MODIFICA:\n{richiesta}\n\n"
        f"ISTRUZIONI:\n"
        f"- Applica SOLO le modifiche richieste\n"
        f"- Mantieni la struttura LaTeX esistente\n"
        f"- NON rigenerare da zero, modifica l'esistente\n"
        f"- Mantieni lo stesso preambolo e intestazione\n"
        f"- Se la modifica riguarda punteggi, ricalcola la somma totale\n"
        f"- Esercizi con una richiesta: testo diretto senza enumerate/\\item. Con più richieste: \\item[a)] \\item[b)] ecc. MAI 1) 2) 3).\n"
        f"- Restituisci il codice LaTeX completo modificato\n"
        f"- TERMINA con \\end{{document}}\n\n"
        f"OUTPUT: SOLO codice LaTeX completo, senza ```latex né spiegazioni."
    )


def prompt_rigenera_blocco(
    materia: str,
    blocco_latex: str,
    istruzione: str,
    mostra_punteggi: bool,
) -> str:
    punti_nota = (
        "Mantieni il formato (X pt) su ogni \\item come nell'originale. "
        "Non è necessario che i punti sommino a un totale preciso — verranno ribilanciati automaticamente."
        if mostra_punteggi
        else "NON inserire punteggi (X pt)."
    )
    return (
        f"Sei un docente esperto di {materia} e LaTeX. "
        f"Devi rigenerare SOLO questo esercizio della verifica, secondo l'istruzione del docente.\n\n"
        f"ESERCIZIO ORIGINALE:\n{blocco_latex}\n\n"
        f"ISTRUZIONE DEL DOCENTE:\n{istruzione}\n\n"
        f"REGOLE:\n"
        f"- Restituisci SOLO il blocco \\subsection*{{...}} con il nuovo esercizio.\n"
        f"- SOTTOPUNTI: una sola richiesta → testo diretto senza enumerate/\\item. "
        f"Due o più richieste → \\begin{{enumerate}}[a)] con \\item[a)] \\item[b)] ecc. MAI 1) 2) 3).\n"
        f"- {punti_nota}\n"
        f"- NON includere preambolo, \\documentclass o \\begin{{document}}.\n"
        f"- NON aggiungere commenti o spiegazioni fuori dal LaTeX.\n"
        f"- TERMINA il blocco con una riga vuota (non con \\end{{document}}).\n"
        f"OUTPUT: SOLO codice LaTeX del blocco esercizio."
    )


def prompt_nuovo_esercizio(
    materia: str,
    argomento: str,
    scuola: str,
    esercizi_esistenti: str,
    numero: int,
    mostra_punteggi: bool,
    punti: int,
) -> str:
    """Un esercizio in più per una verifica già scritta (pulsante «Aggiungi un esercizio»)."""
    punti_nota = (
        f"Assegna circa {punti} pt in totale, con il formato (N pt) alla fine di ogni \\item "
        f"(i punti verranno ribilanciati sul totale della verifica)."
        if mostra_punteggi
        else "NON inserire punteggi (X pt)."
    )
    return (
        f"Sei un docente esperto di {materia} e LaTeX. Aggiungi UN esercizio nuovo a una verifica "
        f"per {scuola}.\n\n"
        f"ARGOMENTO DELLA VERIFICA: {argomento}\n\n"
        f"ESERCIZI GIÀ PRESENTI (da NON ripetere nemmeno concettualmente):\n{esercizi_esistenti}\n\n"
        f"REGOLE:\n"
        f"- L'esercizio deve restare su '{argomento}' in '{materia}', con livello adatto a {scuola}.\n"
        f"- Scegli un tipo e un aspetto diversi da quelli già presenti.\n"
        f"- Titolo nel formato \\subsection*{{Esercizio {numero}: titolo breve}}.\n"
        f"- {REGOLA_CONSEGNE_BREVI}\n"
        f"- VIETATO inserire soluzioni, risposte o risultati.\n"
        f"- {REGOLA_SOTTOPUNTI_MODIFICA}\n"
        f"- {punti_nota}\n"
        f"- {REGOLA_GRAFICO_CURVE}\n"
        f"- Se includi un grafico usa SOLO la riga [[GRAFICO: ...]] (mai codice TikZ).\n"
        f"- NON inserire commenti LaTeX (%) nel corpo.\n"
        f"- NON includere preambolo, \\documentclass o \\begin{{document}}.\n"
        f"OUTPUT: SOLO il blocco \\subsection*{{...}} dell'esercizio, in LaTeX."
    )


SEPARATORE_SCHEDA = "====="


def prompt_scheda_sezione(
    materia: str,
    scuola: str,
    argomento: str,
    titolo_esercizio: str,
    corpo_esercizio: str,
    livelli: list,
    calibrazione: str = "",
) -> str:
    """
    Esercizi di allenamento per UNA sezione della scheda: stesso tipo di richiesta di un esercizio
    della verifica, dati diversi, difficoltà secondo la sequenza `livelli` (1, 2, 3).
    La risposta è una serie di blocchi separati da una riga di «=====».
    """
    n = len(livelli)
    elenco = ", ".join(f"{i + 1}: livello {liv}" for i, liv in enumerate(livelli))
    calib = f"\nLIVELLO DELLA CLASSE: {calibrazione.strip()}\n" if calibrazione and calibrazione.strip() else ""
    return (
        f"Sei un docente esperto di {materia} e LaTeX. Prepara una SCHEDA DI ALLENAMENTO che gli studenti di {scuola} "
        f"svolgeranno PRIMA della verifica sull'argomento «{argomento}».\n"
        f"{calib}\n"
        f"Questo è uno degli esercizi della VERIFICA (serve solo per capire il tipo di richiesta, NON copiarlo):\n"
        f"«{titolo_pulito(titolo_esercizio)}»\n{corpo_esercizio}\n\n"
        f"Scrivi esattamente {n} esercizi di allenamento sullo STESSO tipo di richiesta, con dati, numeri e situazioni DIVERSI, "
        f"in quest'ordine di difficoltà ({elenco}):\n"
        f"- livello 1 (★): applicazione diretta della regola o della definizione, pochi passaggi, numeri semplici;\n"
        f"- livello 2 (★★): esercizio tipico da verifica, più passaggi o due idee da combinare;\n"
        f"- livello 3 (★★★): sfida: un ragionamento in più (problema di realtà, parametro, caso particolare), "
        f"ma risolvibile da uno studente preparato in pochi minuti.\n\n"
        f"REGOLE:\n"
        f"- Scrivi SOLO il testo di ciascun esercizio, in LaTeX, senza numero e senza stelle: li aggiunge il programma.\n"
        f"- Separa un esercizio dal successivo con una riga contenente soltanto {SEPARATORE_SCHEDA}\n"
        f"- Ogni esercizio: 1-4 righe. Con più richieste usa \\begin{{enumerate}}[a)] con \\item[a)], \\item[b)], al massimo 3; "
        f"con una richiesta sola, testo diretto.\n"
        f"- {REGOLA_SOTTOPUNTI_MODIFICA}\n"
        f"- NIENTE soluzioni, risposte, risultati o suggerimenti. NIENTE punteggi. NIENTE titoli (\\subsection) né preambolo.\n"
        f"- Niente grafici, a meno che l'esercizio della verifica ne abbia uno: in quel caso al massimo 2 esercizi con grafico, "
        f"seguendo queste regole: {REGOLA_GRAFICO_CURVE}\n"
        f"- Ogni esercizio deve essere diverso dagli altri e risolvibile con i dati scritti.\n"
        f"- Nessun commento LaTeX (%), nessun Markdown, nessuna spiegazione fuori dagli esercizi.\n"
        f"OUTPUT: SOLO i {n} esercizi in LaTeX separati da {SEPARATORE_SCHEDA}"
    )


def titolo_pulito(titolo: str) -> str:
    """Titolo di un esercizio senza «Esercizio N:» davanti né punteggio."""
    import re as _re
    t = _re.sub(r"^\s*Esercizio\s*\d+\s*[:.\-–]\s*", "", titolo or "", flags=_re.IGNORECASE)
    return _re.sub(r"\s*\(\d+\s*pt\)", "", t).strip()


# Regole condivise dai prompt delle modifiche a un solo esercizio (main.py).
REGOLA_SOTTOPUNTI_MODIFICA = (
    "SOTTOPUNTI: con due o più richieste usa \\begin{enumerate}[a)] con \\item[a)], \\item[b)], ... "
    "(un \\item per richiesta e il punteggio (N pt) alla fine di ogni \\item). "
    "NON scrivere mai a) b) dentro un paragrafo di testo. Con una sola richiesta: testo diretto, senza enumerate."
)

REGOLA_DIFFICOLTA_VERA = (
    "PARTI SEMPRE DA UN LIVELLO ALTO: chi usa questo strumento ha già fatto lezione e vuole mettere alla prova studenti preparati; è meglio "
    "una verifica troppo impegnativa che banale (il docente la semplifica con «Più facile», non il contrario). "
    "DIFFICOLTÀ VERA — COME SI MISURA: una richiesta FACILE non è mai banale: richiede già 2 passaggi (per l'algebra NON una disequazione "
    "o equazione di primo grado semplice, NON un prodotto notevole o una differenza di quadrati immediati; per esempio un trinomio da "
    "scomporre con coefficienti non unitari, o una frazione algebrica con due fattori da studiare). Una MEDIA ha 3-4 passaggi (una "
    "scomposizione, un caso particolare, più condizioni, la somma di due frazioni). Una DIFFICILE ha ALMENO il doppio della media: più "
    "operazioni combinate (per l'algebra: somme o differenze di 2-3 frazioni algebriche con denominatori diversi da scomporre, prodotti o "
    "quozienti di frazioni, radicali o valori assoluti insieme a frazioni, condizioni di esistenza non banali), oppure una trappola, oppure "
    "una discussione. NON è difficile un polinomio di terzo grado da scomporre, né la stessa richiesta con numeri più grandi. Per ogni "
    "materia: la richiesta difficile mette insieme più concetti o obbliga a decidere come procedere. Il PARAMETRO (k, a, m…) è un'abilità avanzata: compare solo se l'argomento lo prevede e MAI in una richiesta facile "
    "o media. Dentro un esercizio la difficoltà non scende mai."
)

REGOLA_CONSEGNE_BREVI = (
    "CONSEGNE E RICHIESTE SNELLE — REGOLA FONDAMENTALE: ogni esercizio ha UNA riga di consegna, standard e breve, come sui libri di testo "
    "(«Risolvi le seguenti disequazioni.», «Semplifica le seguenti espressioni.», «Calcola i seguenti limiti.»). Quando TUTTE le richieste "
    "di un esercizio sono dello stesso tipo (tutte equazioni, tutte disequazioni, tutti limiti, derivate, scomposizioni, espressioni, "
    "radicali…) la consegna sta in UNA riga sopra l'elenco e ogni richiesta è SOLO la formula, senza "
    "parole davanti: NIENTE «risolvi», «determina», «studia il segno», «imposta le condizioni di esistenza», «scomponi in fattori», "
    "«prestando attenzione ai segni», «con coefficienti frazionari», «di grado superiore». Il metodo e il nome del tipo di esercizio li "
    "devono riconoscere gli studenti. "
    "SBAGLIATO: «Risolvi la seguente disequazione fratta di grado superiore, effettuando raccoglimenti successivi e prestando attenzione alla "
    "regola dei segni: (x^3-x^2-9x+9)/(x^2-5x+6) < 0». GIUSTO: consegna «Risolvi le seguenti disequazioni.» e la richiesta "
    "\\(\\displaystyle \\frac{x^3-x^2-9x+9}{x^2-5x+6}<0\\). "
    "Aggiungi parole SOLO se cambiano davvero il compito (per esempio «riportando unicamente il risultato», «indicando la forma "
    "indeterminata iniziale») e SOLO nella consegna, mai ripetute in ogni richiesta. Nelle richieste che sono solo formule scrivi "
    "\\(\\displaystyle …\\) così le frazioni si leggono bene. Fuori dal calcolo (problemi con una situazione, brani, analisi, domande "
    "aperte) la richiesta può essere una frase, ma diretta, senza spiegare come rispondere. "
    "ATTENZIONE, DUE CASI IN CUI LA FORMULA NUDA NON VA BENE: (1) quando i compiti dell'esercizio sono DIVERSI (per esempio una richiesta "
    "chiede le condizioni di esistenza e un'altra una disequazione) ogni richiesta dice cosa fare in poche parole («Determina le condizioni "
    "di esistenza di …», «Risolvi la disequazione: …»), senza una consegna generica che non vale per tutte; (2) se l'esercizio ha UNA sola "
    "richiesta (anche quello per l'eccellenza) scrivi sempre cosa fare prima della formula, in una frase breve («Discuti, al variare di k, "
    "la disequazione: …»): mai la sola formula. "
    "Le NOTE del piano (se ci sono) sono per te: non copiarne le parole nel testo dell'esercizio."
)

REGOLA_GRAFICO_CURVE = (
    "GRAFICI DI FUNZIONI: NON scrivere codice TikZ/pgfplots. Per mostrare il grafico di una funzione scrivi, "
    "su una riga a sé subito dopo il testo, SOLO questa specifica (il programma disegna il grafico): "
    "[[GRAFICO: y = <funzione di x> | x da <A> a <B>]] (forma da seguire: la funzione e i numeri li scegli TU, "
    "adatti all'esercizio e DIVERSI da ogni esempio; non copiare mai una funzione d'esempio). "
    "Dentro la specifica: funzione di x scritta in chiaro (potenza con ^, moltiplicazione con * o accostata, "
    "frazioni con /, funzioni sqrt, sin, cos, tan, ln, exp, abs), poi | e l'intervallo scritto ESATTAMENTE «x da A a B» "
    "(sempre «da» e «a», mai «to»). L'intervallo deve coprire TUTTI i valori che le domande usano: se si chiede lo spazio "
    "fino a t = 5 s, arriva almeno a 5. Anche quando la grandezza non è x (per esempio velocità in funzione del tempo) scrivi "
    "la funzione con x e aggiungi in fondo i nomi degli assi: [[GRAFICO: y = <funzione di x> | x da <A> a <B> | assi t, v]] "
    "(prima l'asse orizzontale). "
    "Più curve nello stesso grafico: separale con ; (al massimo 3). "
    "Asintoti tratteggiati (solo se li chiede il docente o se non sono la risposta di una domanda): aggiungi in fondo "
    "| asintoti x = 2, y = 1 (verticali «x = numero», orizzontali o obliqui «y = espressione»); MAI scriverli come codice TikZ. "
    "Scegli un intervallo che mostri bene le caratteristiche della curva (vertice, intersezioni). "
    "La funzione deve essere ESATTAMENTE quella a cui si riferiscono le domande. "
    "UTILITÀ DEL GRAFICO: un grafico dato deve SERVIRE. Le richieste devono obbligare a LEGGERLO (vertice, zeri, segno, valori in un punto, "
    "crescenza, intervalli) o a ricavarne la funzione (segno di a, valore di c, equazione). Se scrivi nel testo l'equazione della funzione "
    "disegnata e le domande si risolvono con la sola formula, il grafico è inutile: o togli il grafico, o togli l'equazione dal testo e "
    "chiedi di ricavarla dal disegno. MAI dare insieme grafico ed equazione per poi fare domande risolvibili solo con l'equazione. "
    "Niente grafici che non siano funzioni (istogrammi, mappe, schemi): descrivili con una tabella o a parole. "
    "Sul grafico niente legenda né equazione scritta nel testo: sono la risposta. "
    "Nel testo prima del grafico dì sempre cosa rappresentano gli assi, con le unità di misura nelle materie scientifiche "
    "(per esempio «velocità v in m/s in funzione del tempo t in s»). "
    "COERENZA: se il testo dice «si osservi il seguente grafico» o «dalla figura», la riga [[GRAFICO: ...]] "
    "DEVE comparire subito dopo; se non puoi darla, riscrivi la domanda senza rimandare a un grafico."
)


def istruzione_livello_esercizio(piu_difficile: bool, argomento: str) -> str:
    """
    Istruzione fissa per "Più facile" / "Più difficile", da passare a
    prompt_rigenera_blocco come ISTRUZIONE DEL DOCENTE (lavora su un solo esercizio).
    """
    if piu_difficile:
        cambio = (
            "Rendi questo esercizio PIÙ DIFFICILE: usa numeri meno immediati, "
            "richiedi un passaggio di ragionamento in più e chiedi di giustificare i risultati."
        )
    else:
        cambio = (
            "Rendi questo esercizio PIÙ FACILE: semplifica i numeri, riduci la complessità "
            "dei calcoli e usa una formulazione più guidata."
        )
    return (
        f"{cambio} Mantieni lo stesso argomento ('{argomento}'), la stessa tipologia di "
        f"esercizio e lo stesso numero di sottopunti. Non inserire soluzioni, risposte o commenti. "
        f"{REGOLA_SOTTOPUNTI_MODIFICA} "
        f"Se l'esercizio contiene un grafico, mantienilo come riga [[GRAFICO: ...]] (aggiorna la funzione se cambi i dati)."
        f"{REGOLA_GRAFICO_CURVE}"
    )


def prompt_analisi_documento(
    materie_valide: list[str],
    mathpix_context: str | None = None,
) -> str:
    """
    Prompt per l'estrazione avanzata di metadati da un documento caricato.
    Risponde SOLO con JSON — nessun testo extra.
    Schema esteso: tipo_documento, esercizi_trovati[], ha_grafici,
    modalita_uso_consigliata, separazione netta contenuto/stile.
    """
    materie_str = ", ".join(f'"{m}"' for m in materie_valide)

    ctx_block = (
        f"\n\nTESTO OCR ESTRATTO DAL DOCUMENTO (alta fedeltà matematica):\n"
        f"{'─'*60}\n{mathpix_context.strip()}\n{'─'*60}\n"
        if mathpix_context and mathpix_context.strip()
        else ""
    )

    return (
        f"Sei un analizzatore esperto di documenti didattici italiani. "
        f"Ricevi un file caricato da un docente. La tua PRIMA responsabilità è valutare "
        f"se il contenuto è PERTINENTE a un contesto scolastico/educativo.\n"
        f"{ctx_block}"
        f"\nRISPONDI ESCLUSIVAMENTE con un oggetto JSON valido — "
        f"nessun testo prima/dopo, nessun markdown, nessun ```json.\n\n"
        f"SCHEMA OBBLIGATORIO (usa null per i campi non determinabili):\n"
        f"{{\n"
        f'  "pertinente": <true se il documento è scolastico/educativo; false se completamente estraneo (ricevute, foto personali, menu, documenti aziendali, ecc.)>,\n'
        f'  "messaggio_rifiuto": "<SOLO se pertinente=false: messaggio gentile specifico. Altrimenti null>",\n'
        f'  "messaggio_proattivo": "<SOLO se pertinente=true: messaggio breve in italiano che descrive cosa hai trovato, max 2 frasi, tono da assistente scolastico. NON usare emoji nel messaggio.>",\n'
        f'  "tipo_documento": "<UNA di queste 6 opzioni ESATTE — scegli con attenzione:\n'
        f'    - esercizio_singolo: UNO o DUE esercizi isolati (foto di un problema, un singolo esercizio ritagliato o fotografato, max 2 esercizi senza struttura da verifica)\n'
        f'    - esercizi_sciolti: raccolta di 3 o più esercizi NON organizzati come verifica formale (no intestazione, no punteggi totali, no struttura da compito)\n'
        f'    - verifica: documento formale con struttura da compito scolastico (intestazione con nome/data/classe, titolo, punteggi assegnati agli esercizi, più sezioni numerate)\n'
        f'    - appunti: appunti scritti a mano o digitati, schemi, mappe, riassunti, dispense\n'
        f'    - libro: pagine di libro, capitoli, paragrafi con teoria ed esercizi misti\n'
        f'    - misto: documento che combina più tipologie impossibili da classificare nelle precedenti>",\n'
        f'  "materia": "<una di: {materie_str}, oppure null>",\n'
        f'  "scuola": "<una di: Scuola Media, Liceo Scientifico, Liceo Classico, '
        f'Liceo Linguistico, Istituto Tecnico, Istituto Professionale, Università, oppure null>",\n'
        f'  "contenuto_argomento": "<SOLO l\'argomento disciplinare trattato, max 12 parole — '
        f'es. \'parabola e funzione quadratica\'. NON descrivere struttura, SOLO argomento>",\n'
        f'  "stile_desc": "<SOLO struttura/impaginazione — es. \'4 esercizi aperti, 3 sottopunti, '
        f'punteggi assenti, linguaggio formale\'. NON menzionare l\'argomento>",\n'
        f'  "tipi_domande": ["<tipi tra: Aperto, Scelta multipla, Vero/Falso, Completamento>"],\n'
        f'  "num_item_medi": <int, media sottopunti per esercizio, 0 se n/a>,\n'
        f'  "num_esercizi_rilevati": <int, numero esercizi trovati, 0 se n/a>,\n'
        f'  "ha_grafici": <true se contiene grafici, schemi o immagini integrate>,\n'
        f'  "ha_formule": <true se contiene formule matematiche>,\n'
        f'  "ha_punteggi": <true se la verifica ha punteggi annotati su singoli esercizi o sottopunti '
        f'(es. "(5 pt)", "(3 punti)", "/10", marcature tipo "5p" sui margini). '
        f'Non richiede una tabella formale — bastano annotazioni sui singoli item.>,\n'
        f'  "ha_tabella_punti": <true SOLO se la verifica ha una tabella/griglia di valutazione '
        f'esplicita (es. "Tabella Punteggi", "Griglia di valutazione", tabella con colonne '
        f'Es.1/Max/Punti). false se i punteggi sono solo annotati sugli esercizi senza tabella.>,\n'
        f'  "punti_totali_rilevati": <int con la somma totale dei punti se determinabile con certezza '
        f'(es. 100 se gli esercizi sommano a 100, 30 se è su 30). null se non determinabile.>,\n'
        f'  "esercizi_trovati": [\n'
        f'    {{\n'
        f'      "numero": <int 1-based>,\n'
        f'      "testo_breve": "<prime 15 parole del testo, oppure null>",\n'
        f'      "tipo": "<Aperto|Scelta multipla|Vero/Falso|Completamento>",\n'
        f'      "ha_dati_numerici": <true se ha numeri specifici riutilizzabili>\n'
        f'    }}\n'
        f'  ],\n'
        f'  "modalita_uso_consigliata": "<una di: base_conoscenza | stile_e_struttura | copia_fedele | includi_esercizio>",\n'
        f'  "motivazione_uso": "<1 frase che spiega il perché della modalità>",\n'
        f'  "confidence": <float 0.0-1.0>\n'
        f"}}\n\n"
        f"REGOLE CRITICHE PER tipo_documento — LEGGI CON ATTENZIONE:\n"
        f"- Se vedi UNO o DUE esercizi (anche con sottopunti) senza intestazione formale → esercizio_singolo\n"
        f"- Se vedi una raccolta di esercizi numerati (3+) senza struttura da compito → esercizi_sciolti\n"
        f"- Se vedi un documento con intestazione (Nome:___ Data:___), titolo e più sezioni numerate → verifica\n"
        f"- Se vedi testo scritto a mano o digitato come riassunto/schema → appunti\n"
        f"- Il tipo sbagliato INVALIDA tutta l'analisi: scegli con la massima precisione.\n"
        f"REGOLE CRITICHE PER i campi punteggio — LEGGI CON ATTENZIONE:\n"
        f"- 'ha_punteggi': metti true se vedi QUALSIASI annotazione tipo (5 pt), 5p, /10, '3 punti', "
        f"anche su singoli item. Non è necessaria una tabella — bastano i punteggi inline.\n"
        f"- 'ha_tabella_punti': metti true SOLO se esiste una TABELLA SEPARATA di valutazione, "
        f"tipicamente in fondo alla verifica con righe tipo 'Es.1 | Es.2 | Totale | Voto'. "
        f"NON confonderla con i punteggi annotati accanto agli esercizi.\n"
        f"- 'punti_totali_rilevati': somma TUTTI i punteggi visibili. Esempio: se vedi (5 pt)+(10 pt)+(8 pt) "
        f"scrivi 23. Se c'è scritto 'Totale: 100 pt' scrivi 100. null SOLO se davvero impossibile.\n"
        f"REGOLE per modalita_uso_consigliata:\n"
        f"- appunti, libro → base_conoscenza\n"
        f"- verifica → stile_e_struttura\n"
        f"- esercizi_sciolti → stile_e_struttura\n"
        f"- esercizio_singolo → includi_esercizio\n"
        f"- 'contenuto_argomento' e 'stile_desc' NON si sovrappongono mai.\n"
        f"- 'esercizi_trovati' può essere [] se non ci sono esercizi numerati.\n"
        f"- NON inventare. SOLO JSON."
    )


def prompt_qa_verifica(
    materia: str = "",
    livello: str = "",
) -> str:
    """
    Prompt per la Modalità QA — analisi critica di una verifica esistente.
    Il documento viene passato come attachment (immagine o PDF) nel messaggio API.
    Restituisce un report testuale strutturato, NON JSON.
    """
    ctx_mat = f"Materia dichiarata: {materia}. " if materia else ""
    ctx_liv = f"Livello scolastico: {livello}. " if livello else ""

    return (
        f"Sei un esperto revisore didattico. {ctx_mat}{ctx_liv}"
        f"Analizza questa verifica scolastica caricata dal docente e produci un "
        f"**REPORT DI REVISIONE** strutturato.\n\n"
        f"SEZIONI OBBLIGATORIE DEL REPORT:\n\n"
        f"## 1. Panoramica\n"
        f"- Materia e argomento rilevati\n"
        f"- Numero e tipologia degli esercizi\n"
        f"- Punteggio totale dichiarato (se presente)\n\n"
        f"## 2. Errori e Problemi Critici\n"
        f"Per ogni problema trovato:\n"
        f"- [ERRORE/AMBIGUITÀ/INCONSISTENZA] Esercizio N, punto X — descrizione del problema\n"
        f"- Proposta di correzione (in una riga)\n"
        f"Tipi di problemi da cercare:\n"
        f"- Dati matematicamente incoerenti o esercizi senza soluzione unica\n"
        f"- Testo ambiguo che ammette più interpretazioni\n"
        f"- Punteggi che non sommano al totale dichiarato\n"
        f"- Prerequisiti non adeguati al livello scolastico\n"
        f"- Errori grammaticali o ortografici nel testo degli esercizi\n"
        f"- Istruzioni contraddittorie o incomplete\n\n"
        f"## 3. Valutazione Complessiva\n"
        f"- Difficoltà generale: Molto facile / Adeguata / Difficile / Molto difficile\n"
        f"- Bilanciamento tra esercizi (troppo simili? troppo eterogenei?)\n"
        f"- Tempo stimato di svolgimento vs tempo disponibile (se dichiarato)\n\n"
        f"## 4. Suggerimenti di Miglioramento\n"
        f"- Max 3-4 suggerimenti concreti e prioritizzati\n\n"
        f"## 5. Valutazione Finale\n"
        f"Voto qualitativo: ⭐ (da revisionare completamente) / ⭐⭐ (necessita correzioni) / "
        f"⭐⭐⭐ (buona con piccoli fix) / ⭐⭐⭐⭐ (ottima, pronta)\n"
        f"Motivazione in 2 righe.\n\n"
        f"REGOLE:\n"
        f"- Sii diretto e specifico — il docente vuole sapere esattamente cosa sistemare.\n"
        f"- Se non trovi problemi in una sezione, scrivilo esplicitamente ('Nessun problema rilevato').\n"
        f"- Usa italiano corretto e tono professionale ma non accademico.\n"
        f"- NON riscrivere il testo degli esercizi per intero.\n"
        f"- Il report deve essere leggibile in 2-3 minuti."
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  IDEA #19 — Rubrica di Valutazione AI-Generata
# ═══════════════════════════════════════════════════════════════════════════════

def prompt_rubrica_valutazione(
    corpo_latex: str,
    materia: str,
    livello: str,
    punti_totali: int,
) -> str:
    """
    Genera una griglia di valutazione professionale per competenze.
    Output: formato pipe-delimited per costruire tabelle Word/PDF.
    """
    return (
        f"Sei un esperto di didattica e valutazione scolastica italiana. "
        f"Crea una GRIGLIA DI VALUTAZIONE PROFESSIONALE per competenze per un docente "
        f"di {materia} ({livello}).\n\n"
        f"VERIFICA (LaTeX, estratto):\n{corpo_latex[:2500]}\n\n"
        f"PUNTEGGIO TOTALE: {punti_totali} pt\n\n"
        f"GENERA ESCLUSIVAMENTE questo formato pipe-delimited, senza NESSUN altro testo:\n\n"
        f"FASCE:\n"
        f"Eccellente|[es. 91-{punti_totali} pt]|9-10"
        f"|[comprensione eccellente, max 12 parole]"
        f"|[applicazione eccellente, max 12 parole]"
        f"|[esposizione eccellente, max 10 parole]\n"
        f"Buono|[range pt]|7-8"
        f"|[comprensione buona, max 12 parole]"
        f"|[applicazione buona, max 12 parole]"
        f"|[esposizione buona, max 10 parole]\n"
        f"Sufficiente|[range pt]|6"
        f"|[comprensione sufficiente, max 12 parole]"
        f"|[applicazione sufficiente, max 12 parole]"
        f"|[esposizione sufficiente, max 10 parole]\n"
        f"Insufficiente|[range pt]|<6"
        f"|[comprensione insufficiente, max 12 parole]"
        f"|[applicazione insufficiente, max 12 parole]"
        f"|[esposizione insufficiente, max 10 parole]\n\n"
        f"ESERCIZI:\n"
        f"[N]|[titolo breve, max 5 parole]|[X pt]"
        f"|[criterio principale valutato, max 8 parole]"
        f"|[risposta eccellente, max 15 parole]"
        f"|[risposta sufficiente, max 15 parole]\n"
        f"(una riga per ogni esercizio trovato nella verifica)\n\n"
        f"REGOLE TASSATIVE:\n"
        f"- Inizia DIRETTAMENTE con 'FASCE:' — zero testo prima.\n"
        f"- Usa SOLO righe pipe. Nessuna riga vuota extra, nessun markdown.\n"
        f"- Calcola i range punti proporzionalmente su {punti_totali} pt totali.\n"
        f"- Voti: Eccellente=9-10, Buono=7-8, Sufficiente=6, Insufficiente=<6.\n"
        f"- Linguaggio professionale e diretto, adatto a docenti italiani.\n"
        f"- Non riscrivere gli esercizi per intero, solo il criterio valutato."
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  IDEA #8 — Template Gallery (prompt per generazione da template)
# ═══════════════════════════════════════════════════════════════════════════════

def prompt_da_template(
    template: dict,
    materia: str,
    livello: str,
    argomento_custom: str,
    punti_totali: int,
    mostra_punteggi: bool,
    con_griglia: bool,
    calibrazione: str,
    preambolo_fisso: str,
) -> str:
    """
    Genera una verifica a partire da un template predefinito della gallery.
    Il template definisce struttura, tipi di esercizi e numero di item.
    """
    es_desc = "\n".join(
        f"  - Esercizio {i+1}: {e['tipo']} — {e['desc']} ({e.get('items',3)} sottopunti)"
        for i, e in enumerate(template.get("esercizi", []))
    )
    punti_rule = (
        f"- La somma di TUTTI i (X pt) deve essere ESATTAMENTE {punti_totali}. "
        f"Distribuisci proporzionalmente alla difficoltà di ogni esercizio."
        if mostra_punteggi
        else "- NON inserire punteggi (X pt) in nessun punto."
    )
    griglia_rule = (
        "- NON generare la tabella punteggi (sarà aggiunta automaticamente)."
        if con_griglia else
        "- NON generare nessuna griglia."
    )
    return (
        f"Sei un docente esperto di {materia} ({livello}). "
        f"Genera una verifica scolastica professionale in LaTeX.\n\n"
        f"TEMPLATE: {template.get('nome', 'Standard')}\n"
        f"Argomento: {argomento_custom}\n"
        f"Calibrazione livello: {calibrazione}\n\n"
        f"STRUTTURA OBBLIGATORIA — rispetta esattamente:\n{es_desc}\n\n"
        f"REGOLE LATEX:\n"
        f"- Usa ESATTAMENTE questo preambolo senza modifiche:\n{preambolo_fisso}\n"
        f"- Struttura ogni esercizio con \\subsection*{{Esercizio N — Titolo}}\n"
        f"- Ogni esercizio usa \\begin{{enumerate}}[a)] ... \\end{{enumerate}}\n"
        f"- Ogni \\item deve avere testo completo e autonomo\n"
        f"{punti_rule}\n"
        f"{griglia_rule}\n"
        f"- TERMINA con \\end{{document}}\n"
        f"- OUTPUT: SOLO codice LaTeX completo, senza ```latex né spiegazioni."
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  IDEA #2 — One-Click Variant (prompt per variante numerica rapida)
# ═══════════════════════════════════════════════════════════════════════════════

def prompt_variante_rapida(
    corpo_latex: str,
    materia: str,
) -> str:
    """
    Genera una Fila B cambiando SOLO i dati numerici e le opzioni di risposta.
    Mantiene struttura, tipologia e difficoltà identiche all'originale.
    """
    return (
        f"Sei un docente esperto di {materia} e LaTeX. "
        f"Genera una Variante (Fila B) della seguente verifica.\n\n"
        f"VERIFICA ORIGINALE:\n{corpo_latex}\n\n"
        f"REGOLE FERREE — VIOLAZIONE = OUTPUT INUTILIZZABILE:\n"
        f"1. STRUTTURA: mantieni IDENTICI numero esercizi, numero sottopunti, tipologie.\n"
        f"2. DATI NUMERICI: cambia TUTTI i valori numerici (coefficienti, misure, date, ecc.).\n"
        f"   I nuovi dati devono dare risultati 'puliti' (interi o frazioni semplici).\n"
        f"3. SCELTA MULTIPLA: cambia tutte le opzioni mantenendo una sola corretta.\n"
        f"4. VERO/FALSO: inverti almeno il 50% delle risposte (cambia i dati di conseguenza).\n"
        f"5. PUNTEGGI: mantieni IDENTICA la distribuzione dei (X pt) originali.\n"
        f"6. ANTI-SPOILER: NON inserire le soluzioni. Se ci sono grafici, cambia i parametri\n"
        f"   della curva ma NON indicare dove passa.\n"
        f"7. TABELLE: PRIMA di ogni \\begin{{tabular}} lascia SEMPRE una riga vuota per evitare\n"
        f"   sovrapposizioni con il testo. Le tabelle devono essere su righe separate.\n"
        f"8. INTESTAZIONE: nella riga Nome/Classe/Data aggiungi 'Fila B' visibile.\n"
        f"9. COHERENZA: verifica che i nuovi dati siano matematicamente coerenti\n"
        f"   (niente radici di negativi, divisioni per zero, misure impossibili).\n\n"
        f"OUTPUT: SOLO codice LaTeX completo identico nella struttura, "
        f"con \\end{{document}} finale. Nessuna spiegazione."
    )


# ── Autoverifica degli esercizi (materie scientifiche) ─────────────────────────────
def prompt_autoverifica(materia: str, scuola: str, esercizi: list) -> str:
    """
    Chiede all'AI di RISOLVERE ogni esercizio e di segnalare solo gli errori certi.
    esercizi = [(numero, testo_latex), ...]. La risposta è un JSON.
    """
    elenco = "\n\n".join(f"=== ESERCIZIO {n} ===\n{t}" for n, t in esercizi)
    return (
        f"Sei un revisore severo di verifiche di {materia} per: {scuola}.\n"
        f"Per OGNI esercizio qui sotto: RISOLVILO davvero, con tutti i calcoli, poi controlla che sia corretto e ben posto.\n\n"
        f"{elenco}\n\n"
        f"SEGNALA ok=false SOLO per errori CERTI di questi tipi:\n"
        f"1. Dati incoerenti o impossibili: il problema non ha soluzione, oppure ha una soluzione diversa da quella che la richiesta "
        f"presuppone (es. un'equazione senza soluzioni reali dove si chiede di trovarle, punti incompatibili con il tipo di curva, "
        f"due punti con la stessa ascissa per una parabola con asse verticale, un parametro che non può esistere).\n"
        f"2. Scelta multipla: nessuna opzione corretta, più di un'opzione corretta, opzioni duplicate.\n"
        f"3. Vero/falso: un'affermazione né vera né falsa, ambigua o dipendente da dati mancanti.\n"
        f"4. Completamento: più risposte ugualmente corrette o nessuna.\n"
        f"5. Grafico: la riga [[GRAFICO: ...]] non corrisponde ai dati o alle domande dell'esercizio (funzione diversa, "
        f"intervallo che non mostra i punti richiesti).\n"
        f"6. Testo incompleto: frase senza richiesta, sottopunto che non chiede nulla.\n"
        f"7. Dati scomodi: una richiesta di calcolo il cui risultato è chiaramente non pulito per uno studente (radice irrazionale, "
        f"discriminante che non è un quadrato perfetto, decimali lunghi, v² non quadrato) quando l'esercizio presuppone numeri semplici. "
        f"Non è un errore se l'esercizio chiede esplicitamente radici o decimali, o se è proprio Δ<0 / assenza di soluzioni il punto. "
        f"Nel «problema» scrivi il risultato scomodo e nel «suggerimento» quali dati cambiare per ottenere numeri interi.\n"
        f"Non segnalare questioni di stile, difficoltà o formulazione. Nel dubbio: ok=true.\n\n"
        f"Rispondi SOLO con questo JSON (nessun altro testo):\n"
        f'{{"esercizi": [{{"num": <numero>, "ok": true|false, "problema": "<una frase: cosa non va, con i numeri>", '
        f'"suggerimento": "<come correggere, ad esempio quali dati cambiare>"}}]}}\n'
        f"Includi TUTTI gli esercizi, nell'ordine."
    )


def prompt_correggi_esercizio(materia: str, argomento: str, blocco_latex: str, problema: str, suggerimento: str,
                              mostra_punteggi: bool) -> str:
    """Riscrive UN esercizio per eliminare un errore trovato dall'autoverifica, mantenendo tipo e punteggi."""
    punti = ("Mantieni ESATTAMENTE gli stessi punteggi (N pt) di ogni sottopunto."
             if mostra_punteggi else "Non inserire punteggi.")
    return (
        f"Sei un docente esperto di {materia}. Questo esercizio, per una verifica su '{argomento}', contiene un ERRORE.\n\n"
        f"ESERCIZIO:\n{blocco_latex}\n\n"
        f"ERRORE TROVATO: {problema}\n"
        f"SUGGERIMENTO: {suggerimento}\n\n"
        f"Riscrivi LO STESSO esercizio correggendo l'errore:\n"
        f"- stessa tipologia, stesso titolo \\subsection*{{...}}, stesso numero di sottopunti, stesso livello di difficoltà;\n"
        f"- cambia i dati (numeri, funzioni, opzioni) quanto basta perché l'esercizio sia corretto e risolvibile;\n"
        f"- {punti}\n"
        f"- {REGOLA_SOTTOPUNTI_MODIFICA}\n"
        f"- {REGOLA_GRAFICO_CURVE}\n"
        f"- Scelta multipla: ESATTAMENTE una opzione corretta, opzioni distinte e plausibili.\n"
        f"- Nessuna soluzione, risposta o commento. Nessun commento LaTeX (%).\n"
        f"OUTPUT: SOLO il blocco \\subsection*{{...}} corretto, in LaTeX."
    )


def prompt_modifica_verifica(
    materia: str,
    argomento: str,
    blocchi: str,
    richiesta: str,
    mostra_punteggi: bool = True,
    punti_totali: int = 100,
) -> str:
    """Modifica «al volo» di tutta la verifica da una richiesta scritta dal docente (es. «semplifica il primo esercizio»).
    blocchi = gli esercizi attuali, ciascuno come \\subsection*{...} seguito dal corpo; le figure sono segnaposto [[FIGURA n]]."""
    punti = (
        f"Ogni \\item ha il punteggio nel formato (N pt) sulla stessa riga; la somma di tutti i punti deve restare {punti_totali} pt."
        if mostra_punteggi else "NON inserire punteggi (N pt)."
    )
    return (
        f"Sei un docente esperto di {materia} e LaTeX. Hai davanti una verifica sull'argomento «{argomento}» e una RICHIESTA "
        f"del docente per modificarla.\n\n"
        f"RICHIESTA DEL DOCENTE:\n«{richiesta.strip()}»\n\n"
        f"VERIFICA ATTUALE (esercizi in LaTeX):\n{blocchi}\n\n"
        f"COSA FARE:\n"
        f"- Applica SOLO ciò che il docente chiede. Gli esercizi che la richiesta non riguarda li ricopi IDENTICI, parola per parola.\n"
        f"- Se chiede di rendere un esercizio più facile o più difficile, o di cambiarne i dati o il tipo, riscrivi quell'esercizio; "
        f"se chiede di togliere un esercizio, omettilo; se chiede di aggiungerne uno, scrivilo nuovo (sull'argomento della verifica) "
        f"e mettilo dove richiesto, altrimenti in fondo.\n"
        f"- Se la richiesta non riguarda la modifica di questa verifica o non è realizzabile, NON modificare nulla e rispondi "
        f"con la sola riga: NESSUNA_MODIFICA: <motivo in una frase, in italiano>.\n"
        f"- I segnaposto [[FIGURA n]] sono grafici già pronti: lasciali ESATTAMENTE dove sono, dentro lo stesso esercizio. "
        f"Se togli l'esercizio, togli anche il suo segnaposto. Se serve un grafico nuovo o diverso, usa la regola dei grafici qui sotto.\n"
        f"- Numera gli esercizi di nuovo in ordine: \\subsection*{{Esercizio 1: titolo}}, \\subsection*{{Esercizio 2: titolo}}, ...\n"
        f"- {punti}\n"
        f"- {REGOLA_SOTTOPUNTI_MODIFICA}\n"
        f"- {REGOLA_GRAFICO_CURVE}\n"
        f"- {REGOLA_CONSEGNE_BREVI}\n"
        f"- Richieste in ordine di difficoltà crescente; dati puliti (numeri interi o frazioni semplici).\n"
        f"- Nessuna soluzione, risposta o commento. Nessun commento LaTeX (%). Niente preambolo, niente \\begin{{document}}, "
        f"niente \\end{{document}}.\n\n"
        f"OUTPUT: TUTTI gli esercizi della verifica modificata, ciascuno come \\subsection*{{...}} seguito dal suo corpo, "
        f"oppure la riga NESSUNA_MODIFICA. Solo codice LaTeX."
    )


# ── STRUTTURA-TIPO DELLA VERIFICA ─────────────────────────────────────────────
# Modellata su verifiche vere di matematica del triennio: 4-6 esercizi, uno CENTRALE che vale molto (35-50% dei punti) con
# 4-8 richieste a rampa, un'apertura breve, un esercizio di lettura/analisi, un problema, e in fondo un esercizio «per
# l'eccellenza» (pochi punti, molto difficile). I punti non sono mai uguali tra gli esercizi.

# Pesi (in %) per ruolo, per numero di esercizi «normali» (senza quello per l'eccellenza). Ruoli: A apertura, C centrale,
# M medio, G lettura/analisi, P problema.
_PESI_STRUTTURA = {
    1: [("C", 100)],
    2: [("A", 30), ("C", 70)],
    3: [("A", 15), ("C", 50), ("G", 35)],
    4: [("A", 12), ("C", 40), ("G", 25), ("P", 23)],
    5: [("A", 10), ("C", 34), ("M", 20), ("G", 22), ("P", 14)],
    6: [("A", 8), ("C", 30), ("M", 14), ("G", 22), ("C", 14), ("P", 12)],
    7: [("A", 8), ("C", 26), ("M", 12), ("G", 20), ("C", 12), ("M", 12), ("P", 10)],
}

_DESCRIZIONE_STUDIO = (
    "STUDIO COMPLETO di una funzione (dominio, simmetrie, intersezioni, segno, limiti e asintoti, derivata e monotonia se "
    "l'argomento le include, grafico qualitativo) oppure lettura di un grafico con molte richieste brevi: è MOLTO impegnativo, "
    "pesa 25-30 punti, e può essere UNA richiesta unica con consegna brevissima («Studia la funzione … e rappresentane il "
    "grafico qualitativo»)"
)

_DESCRIZIONE_RUOLO = {
    "A": "APERTURA BREVE: poche richieste dirette ma NON banali (una domanda teorica/definizione o un calcolo diretto che richiede comunque 2 passaggi, mai un esempio da prima lezione)",
    "C": "ESERCIZIO CENTRALE: l'abilità principale dell'argomento, 4-8 richieste brevi a rampa, dalla più facile a una DAVVERO difficile",
    "M": "esercizio di difficoltà MEDIA: 2-4 richieste, dal diretto al leggermente articolato",
    "G": "SECONDO TIPO di esercizi dell'argomento (un'altra famiglia di casi) oppure LETTURA/ANALISI (un grafico, dei dati, un testo, una fonte): 2-6 richieste brevi, di difficoltà media o alta",
    "P": "PROBLEMA, CASO o QUESITO DI SINTESI di ragionamento (un problema applicato, un caso da analizzare, un confronto argomentato): 1-3 richieste, difficile",
}


def _arrotonda_a_somma(valori: list, totale: int) -> list:
    """Interi che sommano esattamente a totale, in proporzione a valori (il resto va ai più grandi)."""
    somma = sum(valori) or 1
    quote = [v * totale / somma for v in valori]
    base = [int(q) for q in quote]
    resto = totale - sum(base)
    for i in sorted(range(len(valori)), key=lambda i: -(quote[i] - base[i]))[:max(resto, 0)]:
        base[i] += 1
    return base


_PAROLE_STUDIO_FUNZIONE = ("funzion", "limit", "derivat", "asintot", "continuit", "dominio", "integral")


def struttura_verifica(num_totale: int, punti_totali: int, primo_base: bool = False, eccellenza: bool = True,
                       argomento: str = "") -> list:
    """
    Struttura-tipo di una verifica di num_totale esercizi: [{"ruolo", "descrizione", "punti"}] (la somma dei punti fa punti_totali).
    Con eccellenza=True l'ULTIMO esercizio è quello «per l'eccellenza» (3-10 punti circa il 6%) e conta tra i num_totale.
    """
    num_totale = max(1, int(num_totale))
    ecc = bool(eccellenza) and num_totale >= 3
    normali = num_totale - (1 if ecc else 0)
    pesi = _PESI_STRUTTURA.get(min(normali, 7))
    if normali > 7:                                   # oltre 7: gli esercizi in più sono medi
        pesi = pesi[:-1] + [("M", 8)] * (normali - 7) + pesi[-1:]
    studio = any(k in (argomento or "").lower() for k in _PAROLE_STUDIO_FUNZIONE)
    if studio:                                        # lo studio completo di una funzione pesa molto (25-30%)
        pesi = [(r, max(w, 28) if r == "G" else w) for r, w in pesi]
    ruoli = [r for r, _ in pesi]
    punti_ecc = min(10, max(3, round(punti_totali * 0.06))) if ecc else 0
    punti = _arrotonda_a_somma([w for _, w in pesi], punti_totali - punti_ecc)
    if primo_base and ruoli:
        ruoli[0] = "B"
    voci = []
    for r, p in zip(ruoli, punti):
        d = ("APERTURA: un ripasso FACILE dei concetti base (poche richieste dirette)" if r == "B" else _DESCRIZIONE_RUOLO[r])
        if r == "G" and studio:
            d = _DESCRIZIONE_STUDIO
        voci.append({"ruolo": r, "descrizione": d, "punti": p})
    if ecc:
        voci.append({"ruolo": "E", "punti": punti_ecc, "descrizione":
                     "ESERCIZIO PER L'ECCELLENZA, ultimo e facoltativo (titolo «Per l'eccellenza»): MOLTO difficile, un problema che richiede "
                     "un'idea o un ragionamento non standard (modellizzazione, parametro, caso da discutere), 1-2 richieste"})
    return voci


# Rampe di difficoltà d'esempio, per far capire il livello (NON da copiare): chiave = parole dell'argomento.
_RAMPE_ESEMPIO = [
    (("fratt", "frazioni algebriche", "frazionari"),
     "equazioni fratte: (1) 3/x + 1/(2x) = 7 · (2) 2/(x-1) - 3/(x+2) = 1/(x²+x-2) · "
     "(3) x/(x²-4x+4) - 5/(x²-4) = 1/(x+2), con C.E. e una soluzione da scartare · "
     "(4) (1/(x²-x) - 2/(x²-1)) : (x-3)/(x³-x) + 1/(x-1) = x/(x+1), con scomposizioni e divisione di frazioni"),
    (("esponenzial",),
     "equazioni esponenziali: (1) 5^x = 25√5/∛5 · (2) 2·3^x + (5/3)·3^x = 11√3 · (3) 4·5^x = 3^(x+2), che richiede i logaritmi · "
     "(4) 9^x - 10·3^x + 9 = 0, per sostituzione"),
    (("logaritm",),
     "logaritmi: (1) calcolo con le proprietà: log₂12 + ½log₂9 - log₂18 · (2) dominio di ln(x²-x-6) + ln(9-x) · "
     "(3) log₃(x+2) - log₃x = 1 · (4) log₂²x - 3log₂x = -2 · (5) 3·2^(x+1) = 5^x"),
    (("derivat",),
     "derivate: (1) 3x⁴ - 2/x + √x · (2) (x²-2x)eˣ · (3) ln(x²/(x-1)) · (4) x²eˣ/(x+2) · (5) √(x² + eˣ) · "
     "poi la retta tangente a una funzione fratta in un punto"),
    (("limit", "asintot", "continuit"),
     "limiti: (1) lim (2x³-5x+1)/(x³+2x²) per x→+∞, solo il risultato · (2) lim (x²-5x+6)/(x²-4) per x→2, con passaggi · "
     "(3) lim (√(x²+4x) - x) per x→+∞ · (4) lim (1 - 3/(2x))^x per x→+∞ · (5) lim ln(1+3x²)/(x·sin x) per x→0"),
    (("dominio", "domini", "funzioni reali"),
     "domini: (1) ln(x²-x-6) · (2) ∛(x+1)/√(x²-5x+4) · (3) x/(x·ln(x+3)), con ln al denominatore · (4) ln(√(x-1) - 1) · "
     "(5) √((|3x-1| - |x+2|)/(x²-x-6))"),
    (("scompos", "polinom"),
     "scomposizioni: (1) 4x²y + 8xy · (2) ab + 3a - 2b - 6 · (3) x² - 3x - 10 · (4) 2y² - 7y - 4 · (5) x³ + 1/8 · "
     "(6) x³ - 9x - x² + 9 · (7) 4a² - 4b² + 8bc - 4c²"),
    (("disequaz",),
     "disequazioni (questo è il LIVELLO MINIMO, non andare sotto): (1) facile non banale: (x²-5x+6)/(x²-1) ≤ 0 · "
     "(2) media: (x+1)/(x-2) - 3/(x+2) ≥ 0, somma di due frazioni · (3) media: (x³-4x²-x+4)/(x²-9) ≥ 0, con scomposizione per raccoglimento · "
     "(4) difficile: x/(x²-4) - 1/(x-2) < 2/(x+2) - 1, somma di frazioni con denominatori da scomporre · "
     "(5) difficile: (x³-3x²-x+3)/(x²-4x+3) · (x+2)/(x²-1) ≤ 0, prodotto di frazioni con fattori da scomporre e ripetuti · "
     "(6) difficile: un sistema di tre disequazioni di tipo diverso (fratta, a prodotto, con valore assoluto)"),
    (("radical", "razionalizz"),
     "radicali: (1) semplificare √18 + √50 - √8 · (2) razionalizzare 2/√3 · (3) razionalizzare 1/(√x - √y) · "
     "(4) semplificare un'espressione con radicali letterali e condizioni di esistenza"),
    (("cinematica", "moto"),
     "cinematica: (1) accelerazione da due dati di velocità e tempo · (2) spazio percorso da un grafico v-t · "
     "(3) frenata con spazio e tempo di arresto · (4) due corpi: quando e dove si incontrano (equazione di secondo grado con discriminante quadrato perfetto)"),
    (("storia", "geografia"),
     "storia: (1) collocare un evento (quando, dove, chi) · (2) spiegare una causa o una conseguenza · (3) confrontare due fenomeni o due fonti · "
     "(4) valutare un'interpretazione e argomentarla con i fatti"),
    (("italiano", "letteratura", "antologia"),
     "italiano: (1) comprensione letterale del testo · (2) lessico e figure retoriche · (3) narratore, punto di vista, temi · "
     "(4) interpretazione e confronto con un altro testo, produzione argomentata"),
    (("inglese", "francese", "spagnolo", "tedesco", "lingua"),
     "lingue: (1) vocabolario e completamento · (2) grammatica in contesto · (3) comprensione di un testo con risposte aperte · "
     "(4) produzione scritta guidata con vincoli di forma e lessico"),
    (("scienze", "biologia", "chimica", "terra"),
     "scienze: (1) definizione o riconoscimento · (2) applicazione di una legge o formula a un caso · (3) problema con più passaggi o un dato da ricavare · "
     "(4) interpretazione di un esperimento o di un grafico, previsione motivata"),
    (("informatica", "programmazione", "sistemi"),
     "informatica: (1) leggere un frammento di codice · (2) completare un algoritmo · (3) scrivere una funzione con più casi · "
     "(4) analizzare correttezza e complessità, o trovare un errore nascosto"),
    (("diritto", "economia", "arte", "filosofia"),
     "materie di rielaborazione: (1) definire un concetto · (2) collegarlo a un esempio · (3) confrontare due teorie, norme o autori · "
     "(4) valutare un caso nuovo argomentando"),
]

_RAMPA_GENERICA = (
    "per qualsiasi materia: (a) riconoscere o definire · (b) applicare in un caso standard · (c) caso con un'eccezione, un dato da "
    "ricavare o un passaggio che si sbaglia facilmente · (d) collegare due concetti o affrontare una situazione nuova"
)


def rampe_esempio(materia: str, argomento: str) -> str:
    """Testo con 1-2 rampe di difficoltà d'esempio adatte all'argomento (o quella generica)."""
    t = f"{materia} {argomento}".lower()
    trovate = [r for chiavi, r in _RAMPE_ESEMPIO if any(c in t for c in chiavi)][:2]
    if not trovate:
        trovate = [_RAMPA_GENERICA]
    return ("ESEMPI DI RAMPA DI DIFFICOLTÀ (servono SOLO a capire il livello: NON copiarli, inventa esercizi nuovi con altri dati):\n"
            + "\n".join(f"  • {r}" for r in trovate) + "\n")


def prompt_piano_verifica(
    materia: str,
    argomento: str,
    scuola: str,
    calibrazione: str,
    durata: str,
    scheletro: list,
    note_docente: str = "",
    max_chiusi: int = 1,
) -> str:
    """Prompt del PIANO: l'AI non scrive esercizi, decide solo titolo, tipo e richieste (con livello e nota) di ogni esercizio.
    scheletro = [{"ruolo", "descrizione", "punti"}] deciso dal codice (struttura_verifica). Risposta: solo JSON."""
    righe = []
    for i, v in enumerate(scheletro, 1):
        righe.append(f"  Esercizio {i} (circa {v['punti']} pt): {v['descrizione']}")
    note = (
        "\nISTRUZIONI DEL DOCENTE — PRECEDENZA ASSOLUTA: se chiedono qualcosa sul numero, l'ordine, il tipo, l'argomento, la difficoltà o "
        "i punti di esercizi e richieste, o un modo preciso di fare un esercizio, il piano le rispetta ALLA LETTERA; lo scheletro, i ruoli, "
        "i livelli e le regole qui sotto si adattano a quello che chiede il docente, mai il contrario:\n" + note_docente.strip() + "\n"
        if (note_docente or "").strip() else ""
    )
    return (
        f"Sei un docente esperto di {materia}. Devi PROGETTARE (non scrivere) una verifica sull'argomento «{argomento}» "
        f"per {scuola or 'la scuola indicata'}. Durata prevista: {durata}.\n"
        f"{calibrazione}\n{note}\n"
        f"SCHELETRO GIÀ DECISO (ruoli e punti non si cambiano; gli esercizi sono {len(scheletro)}, nello stesso ordine):\n"
        + "\n".join(righe) + "\n\n"
        f"{rampe_esempio(materia, argomento)}\n"
        f"COSA DECIDERE, per ogni esercizio:\n"
        f"- titolo: breve, di quello che l'esercizio verifica (mai «Saperi essenziali»);\n"
        f"- tipo: «aperto» (quasi sempre), oppure «vero_falso», «scelta_multipla», «completamento»: al massimo {max_chiusi} esercizi "
        f"chiusi in tutta la verifica, e mai l'esercizio centrale né quello per l'eccellenza;\n"
        f"- richieste: la lista delle richieste (a, b, c…), ciascuna con un livello da 1 a 3 e una nota brevissima (al massimo 15 parole) "
        f"su COSA verifica davvero, compresa l'eventuale trappola. Le note sono INTERNE, per chi scriverà gli esercizi: non diventano "
        f"parole del testo (le richieste di calcolo saranno solo formule).\n"
        f"LIVELLI (valgono per ogni materia): 1 = ricordare o applicare in modo diretto; 2 = un passaggio in più, un caso particolare, "
        f"una spiegazione; 3 = più concetti insieme, una trappola, un ragionamento non standard, un'analisi o una valutazione: deve "
        f"essere DAVVERO difficile, non solo più lungo.\n"
        f"{REGOLA_DIFFICOLTA_VERA}\n"
        f"Per ogni richiesta di livello 3 la nota dice COSA la rende davvero difficile (per esempio «somma di tre frazioni con denominatori "
        f"da scomporre», «caso da discutere», «confronto tra due fonti»).\n"
        f"REGOLE:\n"
        f"- Dentro un esercizio i livelli non scendono mai (dal più facile al più difficile).\n"
        f"- Numero di richieste: apertura 1-4; centrale 4-8 (a rampa, dalla più facile a una davvero difficile); medio 2-4; "
        f"secondo tipo o lettura/analisi 2-6 (1 sola solo per lo studio completo di una funzione); problema 2-3; eccellenza 1-2 (tutte di livello 3).\n"
        f"- Nell'insieme: circa il 25% di richieste facili (ma non banali), 45% medie, 30% difficili. L'esercizio per l'eccellenza è molto difficile.\n"
        f"- Le note nominano i passaggi che rivelano la comprensione, quelli in cui gli studenti sbagliano di più (un segno da cambiare, una "
        f"condizione da controllare, un'eccezione, un dato da ricavare, un concetto che si confonde con un altro).\n"
        f"- Esercizi diversi verificano cose diverse: niente richieste che ripetono lo stesso concetto con altri numeri.\n"
        f"- Non scrivere esercizi, dati, formule risolte né soluzioni: solo il piano.\n"
        f"- «docente_vincola»: scrivi true SOLO se le istruzioni del docente dicono qualcosa sul numero, l'ordine, il tipo, l'argomento, la "
        f"difficoltà o i punti degli esercizi o delle richieste, o un modo preciso di fare un esercizio (in quel caso le regole sui livelli, "
        f"sul mix di difficoltà e sul numero di richieste valgono solo dove non contraddicono il docente). Scrivi false se non ci sono "
        f"istruzioni o se riguardano solo lo stile (numeri interi, niente dimostrazioni, niente date…).\n"
        f"- «punti»: SOLO se il docente ha indicato i punti di un esercizio, scrivi il suo valore in quell'esercizio; altrimenti omettilo.\n\n"
        f"OUTPUT: SOLO un oggetto JSON valido, senza altro testo, in questa forma (esattamente {len(scheletro)} esercizi):\n"
        f'{{"docente_vincola": false, "esercizi": [{{"titolo": "...", "tipo": "aperto", "richieste": [{{"livello": 1, "nota": "..."}}, '
        f'{{"livello": 3, "nota": "..."}}]}}]}}'
    )


def prompt_ritocco_difficolta(materia: str, argomento: str, corpo: str, piano_testo: str) -> str:
    """Secondo sguardo sulla difficoltà: l'AI confronta il livello REALE di ogni richiesta con quello del piano e riscrive solo
    le richieste fuori livello (le difficili troppo facili, i parametri tra le facili, l'ordine che scende). Risposta: tutti gli esercizi."""
    return (
        f"Sei un docente esperto di {materia}. Qui sotto c'è una verifica sull'argomento «{argomento}» (esercizi in LaTeX) e il PIANO dei "
        f"livelli di difficoltà che doveva rispettare.\n\n"
        f"PIANO:\n{piano_testo}\n\n"
        f"VERIFICA:\n{corpo}\n\n"
        f"COMPITO: controlla ogni richiesta e correggi SOLO quelle il cui livello REALE non corrisponde al piano:\n"
        f"- le richieste DIFFICILI (e tutto l'esercizio per l'eccellenza) devono essere veramente difficili: se sono troppo semplici "
        f"RISCRIVILE più impegnative (altri dati, stesso argomento e stessa forma), con più operazioni, termini e concetti.\n"
        f"- le richieste FACILI non devono essere BANALI: se una facile è un solo passaggio (per esempio una disequazione di primo grado "
        f"semplice, un prodotto notevole immediato) RISCRIVILA come facile non banale (almeno 2 passaggi). Il livello di partenza deve essere "
        f"ALTO: se hai dubbi, alza di una tacca.\n"
        f"- le richieste FACILI e MEDIE che sono davvero troppo difficili (per esempio con un parametro) vanno semplificate.\n"
        f"- le parti che il piano indica come «volute dal docente» (per esempio un'apertura di base) restano come sono, anche se semplici.\n"
        f"- se dentro un esercizio una richiesta più difficile viene prima di una più facile, riordina o riscrivi in modo che la "
        f"difficoltà non scenda mai.\n"
        f"- le richieste già giuste le ricopi IDENTICHE, parola per parola.\n\n"
        f"REGOLE:\n- {REGOLA_DIFFICOLTA_VERA}\n- {REGOLA_CONSEGNE_BREVI}\n"
        f"- NON cambiare il numero di esercizi, né il numero di richieste di ogni esercizio, né i titoli, né le consegne esistenti (puoi solo "
        f"AGGIUNGERE una consegna dove manca, secondo la regola sulle consegne). NON toccare i punti "
        f"(N pt), le caselle V/F, i grafici ([[GRAFICO: ...]] o TikZ).\n"
        f"- Le richieste riscritte devono avere una soluzione ben definita e dati puliti (numeri interi o frazioni semplici).\n"
        f"- Nessuna soluzione, risposta o commento.\n\n"
        f"OUTPUT: la verifica COMPLETA, dall'inizio, nello stesso formato (solo i blocchi \\subsection*{{...}} con i loro corpi), senza altro testo."
    )


# ── ESERCIZIO DA UNA FOTO (esercizio_foto.py) ─────────────────────────────────────────────────────────────────
# Il docente fotografa un esercizio del libro e lo vuole nella verifica. Tre prompt: leggere, ricontrollare, correggere.
# Il formato di risposta NON è JSON: il LaTeX dentro un JSON perde le barre rovesciate (\f, \t, \b diventano caratteri di controllo).

_MARCATORI_FOTO = (
    "FORMATO DELLA RISPOSTA (rispettalo alla lettera, niente altro testo fuori da questo formato, niente blocchi di codice):\n"
    "===ESERCIZIO===\n"
    "TITOLO: titolo breve dell'esercizio, 2-6 parole, senza «Esercizio n»\n"
    "FIGURA: nessuna | grafico_funzione | figura_geometrica | tabella | non_riproducibile\n"
    "DUBBI: una cosa poco leggibile o incerta per riga (e come l'hai letta), oppure la sola parola «nessuno»\n"
    "TESTO:\n"
    "<il testo dell'esercizio in LaTeX, vedi regole>\n"
    "===FINE===\n"
    "(ripeti il blocco per ogni esercizio). Se la foto non si può leggere con sicurezza scrivi invece una sola riga: "
    "PROBLEMA: spiegazione breve e gentile di cosa non va (foto sfocata, tagliata, scritto a mano illeggibile…) e di come rifarla."
)

_REGOLE_TRASCRIZIONE = (
    "REGOLE DI TRASCRIZIONE (sono tassative):\n"
    "1. FEDELTÀ TOTALE. Copia ogni numero, segno, esponente, indice, simbolo, unità di misura e parola ESATTAMENTE come stampati. "
    "NON risolvere l'esercizio, NON correggerlo, NON migliorarlo, NON semplificarlo, NON cambiare i dati, NON riformulare la consegna. "
    "Se un dato non è leggibile con sicurezza scrivi la tua lettura migliore e annotala in DUBBI: mai inventare, mai «aggiustare» perché torni.\n"
    "2. DA TOGLIERE (non fanno parte dell'esercizio): il numero o la sigla del libro (es. «215», «Es. 12», «p. 87»), le stelline o i livelli di "
    "difficoltà, i simboli grafici del libro (icone, «Esercizio svolto», «Suggerimento»), e SOPRATTUTTO le soluzioni o i risultati stampati "
    "o scritti a penna (es. «[x = 3]», «R: …», «[−2; 5]»): la verifica non deve contenere le risposte. Se l'esercizio è già svolto, "
    "trascrivi solo il testo della consegna.\n"
    "3. STRUTTURA. Una consegna in testa, poi le richieste a), b), c)… come "
    "\\begin{enumerate}[a)] \\item … \\end{enumerate} (se nel libro non ci sono richieste numerate, solo il testo). "
    "Formule dentro \\( … \\) (con \\displaystyle per frazioni, limiti e somme), formule isolate in \\[ … \\]. Percentuali come \\%. "
    "Nel testo non usare \\documentclass, \\usepackage, \\begin{document}, \\input, \\include, \\write né \\subsection: solo il corpo dell'esercizio. "
    "NON scrivere punteggi (N pt): li aggiunge il programma.\n"
    "4. FIGURE. Valuta con cura la figura dell'esercizio, se c'è:\n"
    "   - GRAFICO DI FUNZIONE (la funzione è nel testo o si legge con certezza dal grafico): scrivi su una riga a sé, dove sta nel libro, "
    "SOLO [[GRAFICO: y = <funzione di x> | x da <A> a <B>]] (funzione in chiaro, potenze con ^, frazioni con /; intervallo «x da A a B»; "
    "più curve separate da «;»; asintoti disegnati nel libro: aggiungi in fondo | asintoti x = 2, y = 1). Mai codice TikZ per i grafici di funzioni. "
    "Se il grafico NON ha una formula e devi ricostruirla dalle sue caratteristiche (zeri, asintoti, vertice, punti), usa la funzione più "
    "semplice che le rispetta TUTTE e scrivilo in DUBBI («grafico ricostruito: controlla che corrisponda»). Se non riesci a ricostruirlo con "
    "sicurezza scrivi FIGURA: non_riproducibile.\n"
    "   - FIGURA GEOMETRICA semplice (triangoli, cerchi, rette, angoli, poligoni, solidi in prospettiva semplice, vettori): disegnala con un "
    "\\begin{center}\\begin{tikzpicture}[scale=…] … \\end{tikzpicture}\\end{center} pulito, con le STESSE etichette del libro (A, B, C, "
    "misure, angoli) e proporzioni coerenti con le misure date; FIGURA: figura_geometrica. Se è troppo complessa per riprodurla con "
    "fedeltà: FIGURA: non_riproducibile.\n"
    "   - TABELLA di dati: ricostruiscila con \\begin{tabular}…, ogni cella ESATTAMENTE come nel libro; FIGURA: tabella.\n"
    "   - Quadro, fotografia, cartina, schema o circuito complessi, disegni a mano libera, qualsiasi immagine che non puoi rifare IDENTICA: "
    "FIGURA: non_riproducibile. In quel caso scrivi comunque il testo e al posto della figura la riga [[FIGURA NON RIPRODUCIBILE]]. "
    "NON sostituire mai una figura con una tua figura «simile» e NON inventare dati.\n"
    "5. PIÙ ESERCIZI nella stessa foto: un blocco ===ESERCIZIO=== per ciascuno, nell'ordine in cui compaiono. Un esercizio spezzato su due "
    "foto è UN solo esercizio. Ignora ciò che non è un esercizio (teoria, esempi svolti, pubblicità, margini).\n"
    "6. Lingua: quella del testo originale (di norma italiano); non tradurre.\n"
)


def prompt_leggi_esercizi_foto(materia: str, scuola: str, n_immagini: int, max_esercizi: int = 3) -> str:
    contesto = ""
    if (materia or "").strip():
        contesto = f"Materia della verifica: {materia.strip()}" + (f" · scuola: {scuola.strip()}" if (scuola or "").strip() else "") + ".\n"
    return (
        "Sei un trascrittore estremamente accurato di esercizi scolastici. Ricevi "
        + ("una foto" if n_immagini == 1 else f"{n_immagini} foto")
        + " (o pagine) di un libro di testo o di un foglio di esercizi: un docente vuole inserire "
        "quell'esercizio IDENTICO in una sua verifica. Il tuo compito è trascriverlo in LaTeX senza cambiare nulla di ciò che chiede.\n"
        + contesto
        + f"Trascrivi al massimo {max_esercizi} esercizi (i più evidenti o i primi); gli altri ignorali.\n\n"
        + _REGOLE_TRASCRIZIONE + "\n" + _MARCATORI_FOTO
    )


def prompt_ricontrolla_trascrizione(esercizi_testo: str, n_immagini: int, tieni_punti: bool = False) -> str:
    """Secondo sguardo, indipendente: confronta la trascrizione con l'immagine e corregge ciò che non coincide."""
    return (
        "Sei un revisore severo. Qui sotto trovi la TRASCRIZIONE LaTeX di uno o più esercizi, fatta da un altro assistente guardando "
        + ("la foto allegata" if n_immagini == 1 else "le foto allegate")
        + ". Confrontala con l'immagine, esercizio per esercizio, e cerca ogni differenza: numeri, segni, esponenti, indici, frazioni "
        "(numeratore e denominatore), simboli (≤ ≥ < >), parole, unità, richieste a) b) c) mancanti o in più, dati di tabelle, "
        "etichette e misure delle figure, intervalli, funzioni dei grafici. Controlla anche che NON siano rimaste soluzioni o risultati "
        "del libro, il numero dell'esercizio o le stelline.\n"
        "Per ogni esercizio rispondi con questo formato, nello stesso ordine:\n"
        "===ESERCIZIO===\n"
        "ESITO: ok | corretto\n"
        "DIFFERENZE: una per riga («era X, nella foto è Y»), oppure «nessuna»\n"
        "TESTO:\n"
        "<il testo LaTeX COMPLETO, già corretto; se l'esito è «ok» ricopialo identico>\n"
        "===FINE===\n"
        + ("I punteggi (N pt) alla fine delle richieste sono VOLUTI: non toglierli; controllali sul foglio e correggili se diversi. " if tieni_punti else "")
        + "Correggi SOLO ciò che differisce dalla foto: non riscrivere, non risolvere, non abbellire. Non toccare il formato delle righe "
        "[[GRAFICO: …]] se la funzione è giusta. Se non sei sicuro di una differenza, lascia il testo com'è e scrivila come dubbio nelle "
        "DIFFERENZE con la parola «DUBBIO».\n\n"
        "TRASCRIZIONE DA CONTROLLARE:\n" + esercizi_testo
    )


def prompt_correggi_trascrizione(testo_latex: str, richiesta: str, n_immagini: int) -> str:
    """Il docente ha visto la trascrizione e dice cosa non va: si corregge guardando di nuovo la foto."""
    return (
        "Hai trascritto in LaTeX l'esercizio di "
        + ("una foto" if n_immagini == 1 else "alcune foto")
        + " (allegate). Il docente ha controllato il risultato e segnala un errore. Riguarda la foto e correggi SOLO ciò che segnala "
        "(e le conseguenze dirette), senza toccare il resto: la trascrizione deve restare fedele alla foto.\n"
        "Rispetta le stesse regole: niente soluzioni o risultati del libro, niente punteggi, solo il corpo dell'esercizio, grafici di "
        "funzioni con [[GRAFICO: y = … | x da A a B]], figure geometriche in TikZ, tabelle con tabular.\n"
        f"SEGNALAZIONE DEL DOCENTE: {richiesta.strip()}\n\n"
        "TRASCRIZIONE ATTUALE:\n" + testo_latex + "\n\n"
        "Rispondi SOLO con:\n===ESERCIZIO===\nTITOLO: …\nFIGURA: nessuna | grafico_funzione | figura_geometrica | tabella | non_riproducibile\n"
        "DUBBI: … oppure «nessuno»\nTESTO:\n<il testo LaTeX corretto>\n===FINE==="
    )


def testo_esercizi_fissi(fissi: list) -> str:
    """Nota per chi scrive la verifica: ci sono esercizi del docente, già pronti, che il programma inserirà al posto giusto."""
    if not fissi:
        return ""
    righe = [
        "ESERCIZI DEL DOCENTE GIÀ PRONTI (tratti dal suo libro): NON scriverli e NON riscriverli, li inserisce il programma. "
        "Tu scrivi SOLO gli altri esercizi. Per coerenza: non ripetere lo stesso tipo di richiesta e gli stessi dati, "
        "e tieni il livello di difficoltà degli esercizi che scrivi vicino a quello di questi:"
    ]
    for f in fissi:
        righe.append(f"- «{(f.get('titolo') or 'Esercizio').strip()}»: " + (f.get("riassunto") or "").strip())
    return "\n".join(righe)


def prompt_esercizi_mancanti(materia: str, argomento: str, calibrazione: str, corpo: str, n_regolari: int,
                             con_eccellenza: bool, mostra_punteggi: bool) -> str:
    """Rete di sicurezza: la verifica ha meno esercizi di quanti richiesti. Si scrivono SOLO quelli che mancano."""
    voci = []
    if n_regolari > 0:
        voci.append(f"{n_regolari} " + ("esercizio normale" if n_regolari == 1 else "esercizi normali"))
    if con_eccellenza:
        voci.append("1 esercizio «Per l'eccellenza»: facoltativo, MOLTO difficile (un problema che richiede un'idea o un ragionamento "
                    "non standard), 1-2 richieste, circa 3-10 pt")
    return (
        f"Sei un docente di {materia}. Qui sotto c'è una verifica sull'argomento «{argomento}» a cui MANCANO degli esercizi. "
        f"Scrivi SOLO quelli che mancano: {' e '.join(voci)}.\n"
        "- NON riscrivere né ripetere gli esercizi che ci sono già: usa tipi di richiesta e dati DIVERSI.\n"
        "- Livello di difficoltà e stile come quelli già presenti" + (f" ({calibrazione.strip()})" if (calibrazione or "").strip() else "") + ".\n"
        "- Formato: ogni esercizio è \\subsection*{Esercizio N: Titolo} seguito dal corpo in LaTeX, con le richieste come "
        "\\begin{enumerate}[a)] \\item … \\end{enumerate}; numeri progressivi dopo quelli esistenti; l'esercizio «Per l'eccellenza» per ultimo "
        "(titolo «Per l'eccellenza»).\n"
        + ("- Ogni \\item deve avere (X pt) sulla stessa riga, formato ESATTO (X pt); scegli tu i valori (circa 3-10 pt per richiesta).\n"
           if mostra_punteggi else "- NON scrivere punteggi.\n")
        + f"- {REGOLA_CONSEGNE_BREVI}\n"
        f"- {REGOLA_GRAFICO_CURVE}\n"
        "- Rispondi SOLO con il LaTeX dei blocchi mancanti: niente preambolo, niente \\end{document}, niente spiegazioni.\n\n"
        "VERIFICA ESISTENTE:\n" + corpo
    )


# ── VERIFICA GIÀ SCRITTA DAL DOCENTE, DA IMPAGINARE BENE (impagina.py) ───────────────────────────────────────────

_ECCEZIONI_VERIFICA_COMPLETA = (
    "ECCEZIONI PER QUESTA VERIFICA COMPLETA (valgono al posto delle regole sopra dove sono in contrasto):\n"
    "- Le foto o le pagine sono UNA verifica intera, spesso fatta con screenshot e ritagli messi insieme, con stili e caratteri diversi. "
    "Trascrivi TUTTI gli esercizi, nell'ordine in cui compaiono, uno per blocco ===ESERCIZIO===. Non saltarne nessuno, non unirne due, non cambiarne l'ordine.\n"
    "- INTESTAZIONE E CORNICE: ignora (non trascrivere) il nome della scuola e il logo, le righe «Nome / Classe / Data», il voto, la tabella o la griglia "
    "finale dei punteggi, le frasi generali tipo «svolgere tutti gli esercizi» o «tempo a disposizione». Il numero dell'esercizio («Esercizio 3», «3.») "
    "NON va nel testo: lo mette il programma. Se l'esercizio ha un titolo o un tema scritto (es. «Equazioni di secondo grado») mettilo in TITOLO, "
    "altrimenti lascia TITOLO vuoto.\n"
    "- PUNTEGGI: se nel foglio ci sono i punti delle richieste (es. «[2 punti]», «(0,5)», «2 pt», «3p»), riportali alla fine di OGNI richiesta nel "
    "formato (N pt), con il punto per i decimali (es. (0.5 pt)). Se non ci sono, NON inventarli e non scrivere nulla.\n"
    "- Mantieni la struttura di ciascun esercizio: la stessa consegna, le stesse richieste con le stesse lettere o numeri, nello stesso ordine; "
    "scelta multipla con le stesse opzioni, vero/falso con le stesse affermazioni, tabelle con gli stessi dati. NON risolvere, NON correggere gli errori "
    "(se vedi un errore nel testo del docente trascrivilo com'è e segnalalo in DUBBI), NON aggiungere né togliere richieste.\n"
    "- Prima di tutti i blocchi scrivi due righe: VERIFICA_TITOLO: il titolo o l'argomento della verifica come compare (o la sola parola «nessuno») e "
    "PUNTI_TOTALI: il totale scritto sul foglio (solo il numero, o «nessuno»).\n"
)


def prompt_leggi_verifica_completa(materia: str, scuola: str, n_immagini: int, max_esercizi: int = 12) -> str:
    contesto = ""
    if (materia or "").strip():
        contesto = f"Materia: {materia.strip()}" + (f" · scuola: {scuola.strip()}" if (scuola or "").strip() else "") + ".\n"
    return (
        "Sei un trascrittore estremamente accurato di verifiche scolastiche. Ricevi "
        + ("una foto o un PDF" if n_immagini == 1 else f"{n_immagini} foto o PDF")
        + " con la verifica di un docente, scritta o impaginata male. Il docente la vuole IDENTICA nel contenuto, ma impaginata bene: "
        "il tuo compito è trascrivere tutti gli esercizi in LaTeX senza cambiare nulla di ciò che chiedono.\n"
        + contesto
        + f"La verifica ha al massimo {max_esercizi} esercizi.\n\n"
        + _REGOLE_TRASCRIZIONE + "\n" + _ECCEZIONI_VERIFICA_COMPLETA + "\n"
        + _MARCATORI_FOTO.replace("TITOLO: titolo breve dell'esercizio, 2-6 parole, senza «Esercizio n»",
                                  "TITOLO: titolo breve dell'esercizio (2-6 parole, senza «Esercizio n»), oppure vuoto se non ne ha uno")
    )


def prompt_correggi_verifica(testo_latex: str, richiesta: str, n_immagini: int) -> str:
    """Il docente ha visto la verifica trascritta e dice cosa non va: si riguardano le foto e si corregge SOLO quello."""
    return (
        "Hai trascritto in LaTeX la verifica di " + ("una foto" if n_immagini == 1 else "alcune foto") + " (allegate). Il docente ha controllato "
        "il risultato e segnala un errore. Riguarda le foto e correggi SOLO ciò che segnala (e le conseguenze dirette), senza toccare il resto: "
        "la trascrizione deve restare fedele all'originale, con TUTTI gli esercizi nello stesso ordine.\n"
        "Stesse regole di prima: niente soluzioni, grafici di funzioni con [[GRAFICO: y = … | x da A a B]], figure geometriche in TikZ, tabelle con "
        "tabular, punteggi (N pt) solo dove ci sono sul foglio.\n"
        f"SEGNALAZIONE DEL DOCENTE: {richiesta.strip()}\n\n"
        "TRASCRIZIONE ATTUALE:\n" + testo_latex + "\n\n"
        "Rispondi con TUTTI gli esercizi, uno per blocco, nel formato:\n===ESERCIZIO===\nTITOLO: … (o vuoto)\nFIGURA: nessuna | grafico_funzione | "
        "figura_geometrica | tabella | non_riproducibile\nDUBBI: … oppure «nessuno»\nTESTO:\n<il testo LaTeX>\n===FINE==="
    )


def prompt_controlla_errori_verifica(esercizi_testo: str, materia: str) -> str:
    """Un secondo lettore, solo sul TESTO già trascritto: segnala errori oggettivi nella verifica del docente (mai modifiche di gusto)."""
    return (
        f"Sei un docente di {materia or 'scuola'} che rilegge la verifica di un collega prima che venga stampata. Qui sotto ci sono gli esercizi "
        "in LaTeX. Segnala SOLO errori oggettivi e certi: dati o calcoli sbagliati o incoerenti, richieste impossibili o che si contraddicono, "
        "consegna che non corrisponde alle richieste, refusi evidenti, formule malformate, dati mancanti senza i quali l'esercizio non si può svolgere. "
        "NON segnalare questioni di stile, di difficoltà, di gusto o di formulazione alternativa. Se non sei sicuro, non segnalare. Al massimo 5 note.\n"
        "Se non trovi errori certi rispondi con la sola parola NESSUNO.\n"
        "Per ogni errore usa questo formato:\n"
        "===NOTA===\n"
        "ESERCIZIO: il numero dell'esercizio (1, 2, 3…)\n"
        "PROBLEMA: una frase che dice cosa non va\n"
        "PROPOSTA: una frase che dice cosa cambieresti\n"
        "TESTO_CORRETTO:\n"
        "<l'INTERO esercizio in LaTeX, identico all'originale tranne la correzione: stesse richieste, stessa struttura, stessi punteggi (N pt)>\n"
        "===FINE===\n\n"
        "ESERCIZI:\n" + esercizi_testo
    )
