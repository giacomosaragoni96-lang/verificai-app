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
        f"═══════════════════════════════════════════\n"
    ) if note_generali.strip() else ""

    # ── CONTESTO MATHPIX OCR ──────────────────────────────────────────────────
    # Se il docente ha caricato un documento (verifica precedente, libro, appunti)
    # e Mathpix ha estratto il testo matematico, lo iniettiamo come contesto ad
    # alta priorità. Il modello deve usarlo come riferimento per stile, struttura
    # e terminologia — NON copiarlo letteralmente.
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
        f"• Se il documento contiene formule/grafici, prendi spunto per i dati.\n\n"
        f"CONTENUTO OCR:\n"
        f"{'─' * 60}\n"
        f"{mathpix_context.strip()}\n"
        f"{'─' * 60}\n"
    ) if mathpix_context and mathpix_context.strip() else ""

    if mostra_punteggi:
        punti_rule = (
            f"- PUNTEGGI — REGOLA ASSOLUTA E INVIOLABILE:\n"
            f"  * Ogni \\item DEVE avere \"(X pt)\" sulla stessa riga, subito dopo il testo.\n"
            f"  * Formato ESATTO e UNICO: (X pt) — es: \\item[a)] Risolvi l'equazione. (5 pt)\n"
            f"  * NON usare: [X pt], X punti, X p., pt X, (Xpt), o qualsiasi altro formato.\n"
            f"  * SOMMA TOTALE TASSATIVA: la somma di TUTTI i (X pt) di TUTTI gli esercizi deve essere\n"
            f"    ESATTAMENTE {punti_totali} pt. NON {punti_totali-1}, NON {punti_totali+1}. ESATTAMENTE {punti_totali}.\n"
            f"  * PRIMA DI TERMINARE: somma mentalmente tutti i (X pt) che hai scritto. Se non fa {punti_totali}, correggi.\n"
            f"  * Distribuisci i punti in modo proporzionale alla difficoltà.\n"
            f"  * NON inserire punti nel titolo \\subsection*, SOLO nei \\item.\n"
            f"  * REGOLA CRITICA: se un esercizio ha un solo sottopunto, usa comunque \\item[a)] con il suo punteggio.\n"
            f"    NON lasciare MAI un esercizio senza \\item con punteggio — la griglia di valutazione sarà inutilizzabile."
        )
    else:
        punti_rule = "- NON inserire punti (X pt) in nessun esercizio né sottopunto."

    griglia_rule = (
        "- NON generare la griglia (sarà aggiunta automaticamente dopo)."
        if con_griglia
        else "- NON generare nessuna griglia di valutazione."
    )

    multi_rule = "- NON includere esercizi multidisciplinari."

    if e_mat:
        grafici_rule = (
            "- GRAFICI pgfplots: quando il grafico è un DATO fornito allo studente "
            "(es. 'osserva il grafico della parabola e determina...', 'dal grafico ricava...'), "
            "DEVI obbligatoriamente generarlo con pgfplots/tikzpicture. "
            "Esempio per parabola: \\begin{tikzpicture}\\begin{axis}[width=7cm,height=5.5cm,"
            "axis lines=center,xlabel=$x$,ylabel=$y$,grid=both,xtick={-4,...,4},ytick={-4,...,4}]"
            "\\addplot[blue,thick,domain=-3:3,samples=100]{x^2-2*x-3}; \\end{axis}\\end{tikzpicture} "
            "MI RACCOMANDO NON lasciare MAI spazio extra per disegnare se lo studente deve disegnare lui il grafico, lo fara sul suo foglio."
        )
    else:
        grafici_rule = ""

    return (
        f"Sei un docente esperto di {materia} e LaTeX. Genera SOLO il corpo degli esercizi "
        f"(senza preambolo, senza \\documentclass, senza \\begin{{document}}) per una verifica su: {argomento}.\n"
        f"{ f'Punti totali da distribuire: {punti_totali} pt.' if mostra_punteggi else ''}\n"
        f"{s_mathpix}"
        f"{s_note}"
        f"{istruzioni_esercizi}\n"
        f"\nCALIBRAZIONE LIVELLO E TEMPO:\n"
        f"{calibrazione}\n"
        f"- DURATA PREVISTA: {durata}. Regola la lunghezza dei calcoli, il numero di incognite e la complessità "
        f"testuale in modo che {num_esercizi} esercizi siano agevolmente fattibili nel tempo scelto.\n"
        f"- BILANCIAMENTO CONTESTO E MODELLAZIONE: NON esagerare con i problemi applicati alla realtà o fortemente "
        f"interdisciplinari. MASSIMO 1 o 2 esercizi possono essere contestualizzati. I restanti DEVONO essere "
        f"esercizi canonici, diretti e focalizzati sulla procedura pura.\n"
        f"- REGISTRO LINGUISTICO — REGOLA ASSOLUTA: il testo degli esercizi deve essere CONCISO e DIRETTO.\n"
        f"- DATI PULITI — REGOLA ASSOLUTA: prima di scrivere ogni esercizio, risolvilo mentalmente tu stesso. "
        f"Scegli SOLO dati che portano a risultati interi o frazioni semplici. MAI scegliere dati che rendono "
        f"un sistema contraddittorio, sovradeterminato o senza soluzione unica (a meno che non sia esplicitamente "
        f"richiesto). Se un esercizio chiede di trovare un'equazione soddisfacendo N condizioni, verifica che le "
        f"N condizioni siano compatibili tra loro.\n"
        f"REGOLE TASSATIVE SUI GRAFICI (LOGICA ANTI-SPOILER):\n"
        f"- Se l'esercizio richiede allo studente di 'disegnare', 'rappresentare graficamente', 'tracciare' o "
        f"'costruire' una figura/grafico, NON generare il codice TikZ.\n"
        f"- Genera un grafico (TikZ) SOLO se esso è un dato di partenza necessario fornito dal docente.\n"
        f"\nREGOLE LATEX (TASSATIVE):\n"
        f"{griglia_rule}\n"
        f"{punti_rule}\n"
        f"- NUMERO ESERCIZI: genera ESATTAMENTE {num_esercizi} blocchi \\subsection*. CONTA i tuoi blocchi prima di chiudere.\n"
        f"- Titoli: \\subsection*{{Esercizio N: Titolo}}\n"
        f"- SOTTOPUNTI OBBLIGATORI — REGOLA ASSOLUTA: ogni esercizio DEVE avere ALMENO UN \\item con label esplicita "
        f"tra parentesi quadre (es. \\item[a)]). NON è mai accettabile un esercizio con solo testo e senza \\item. "
        f"Se un esercizio ha una sola richiesta, usa comunque \\item[a)]. "
        f"Se ne ha due, \\item[a)] e \\item[b)]. E così via.\n"
        f"- PROTEZIONE ESERCIZIO 1 (Saperi Essenziali): nell'Esercizio 1 NON inserire MAI il simbolo (*) su nessun sottopunto.\n"
        f"{multi_rule}\n"
        f"- Scelta multipla: le opzioni DEVONO stare in un \\begin{{enumerate}}[a)] SEPARATO dopo la domanda.\n"
        f"- Vero/Falso: $\\square$ \\textbf{{V}} $\\quad\\square$ \\textbf{{F}}\n"
        f"- Completamento: \\underline{{\\hspace{{3cm}}}}\n"
        f"{grafici_rule}\n"
        f"\nFORMATO OUTPUT: restituisci SOLO i blocchi \\subsection*{{...}} con relativi esercizi.\n"
        f"TERMINA con \\end{{document}}.\n"
        f"NIENTE preambolo, NIENTE \\documentclass, NIENTE \\begin{{document}}.\n"
        f"SOLO CODICE LATEX del corpo."
    )


def prompt_controllo_qualita(
    materia: str,
    difficolta: str,
    corpo_latex: str,
) -> str:
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
        f"2. ADEGUATEZZA AL LIVELLO ({difficolta}): la complessità è appropriata?\n\n"
        f"3. UNIVOCITÀ: la domanda ha una sola risposta corretta e non è ambigua?\n\n"
        f"SE trovi problemi: CORREGGILI DIRETTAMENTE modificando i dati dell'esercizio finché l'esercizio sia "
        f"corretto, sensato e risolvibile. NON eliminare esercizi, correggili.\n\n"
        f"CONTROLLO PUNTEGGI OBBLIGATORIO: prima di restituire il testo, somma TUTTI i (X pt) presenti.\n"
        f"La somma DEVE essere uguale alla somma originale. Se non lo è, ribilancia i punteggi.\n"
        f"Assicurati che ogni \\item abbia esattamente un (X pt) al termine del testo.\n\n"
        f"SE tutto è corretto: restituisci il testo IDENTICO senza modifiche.\n\n"
        f"REGOLE OUTPUT:\n"
        f"- Restituisci SOLO il corpo LaTeX corretto (\\subsection* ecc.), senza preambolo.\n"
        f"- Mantieni ESATTAMENTE la stessa struttura LaTeX (\\item[a)], \\item[b)], ecc.).\n"
        f"- Assicurati che ogni esercizio abbia almeno un \\item con label esplicita e punteggio (X pt).\n"
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
) -> str:
    _v_tag = f" ({versione_label})" if versione_label else ""
    punti_str = (
        f"Ridistribuisci i punti in modo che la somma sia ESATTAMENTE {punti_totali} pt. totali."
        if mostra_punteggi
        else "NON inserire punteggi."
    )
    return (
        f"Sei un docente esperto. Hai già generato questa verifica{_v_tag}:\n\n"
        f"{corpo_latex}\n\n"
        f"Devi creare una versione RIDOTTA per studenti con sostegno o certificazione (BES/DSA/NAI).\n"
        f"La struttura deve essere simile all'originale ma con circa il {perc_ridotta}% di sottopunti IN MENO "
        f"rispetto al totale.\n"
        f"Scegli quali sottopunti eliminare partendo dai più complessi. Mantieni sempre almeno 1 sottopunto per esercizio.\n"
        f"{punti_str}\n"
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
        f"- Ogni esercizio deve mantenere almeno un \\item[a)] con punteggio (X pt)\n"
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
        f"- Mantieni la stessa struttura LaTeX (\\subsection*, \\begin{{enumerate}}, \\item[a)], ecc.).\n"
        f"- Ogni esercizio deve avere ALMENO un \\item[a)] con la sua richiesta.\n"
        f"- {punti_nota}\n"
        f"- NON includere preambolo, \\documentclass o \\begin{{document}}.\n"
        f"- NON aggiungere commenti o spiegazioni fuori dal LaTeX.\n"
        f"- TERMINA il blocco con una riga vuota (non con \\end{{document}}).\n"
        f"OUTPUT: SOLO codice LaTeX del blocco esercizio."
    )
