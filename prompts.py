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
            f"  * Distribuisci i punti in modo proporzionale alla difficoltà.\n"
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

    if e_mat:
        grafici_rule = (
            "- GRAFICI pgfplots: genera codice TikZ/pgfplots SOLO per grafici matematici standard "
            "(funzioni, parabole, rette, cerchi, istogrammi, grafici a barre).\n"
            "  ⛔ VIETATI GRAFICI COMPLESSI: NON generare MAI linee del tempo, diagrammi di flusso, "
            "alberi genealogici, organigrammi, mappe geografiche, diagrammi spaziali o altri grafici non matematici. "
            "Questi spesso falliscono la compilazione e non sono adatti a verifiche scolastiche.\n"
            "  ⛔ MAPPE E DIAGRAMMI SPAZIALI: NON generare MAI mappe, planimetrie, diagrammi geografici "
            "o rappresentazioni spaziali. Se l'esercizio richiede una mappa, descrivila testualmente "
            "senza codice TikZ.\n"
            "  ⛔ NON generare MAI codice TikZ se il testo chiede allo studente di disegnare, rappresentare,"
            " tracciare o costruire un grafico — questo è uno SPOILER della risposta.\n"
            "  ⛔ Se l'esercizio usa parole come 'rappresenta graficamente', 'disegna', 'traccia', 'costruisci':"
            " scrivi SOLO il testo della richiesta, senza alcun environment tikzpicture o pgfplots."
            " Lo studente disegnerà sul proprio foglio.\n"
            "  ⛔ ANNOTAZIONI ANTI-SPOILER: quando il grafico è un DATO fornito, NON aggiungere sul grafico"
            " etichette o \\node con le quantità che le domande chiedono di determinare.\n"
            "  Esempi vietati: coordinate del vertice ($V(x_v, y_v)$), equazione dell'asse di simmetria"
            " (\"asse x=k\"), coordinate di intersezioni con gli assi, massimi, minimi.\n"
            "  Il grafico DEVE mostrare SOLO la curva e gli assi cartesiani con scala numerica.\n"
            "  ⛔ TESTO TECNICO VIETATO: NON scrivere mai nel testo dell'esercizio frasi come"
            " \"ottenuto con TikZ\", \"generato con TikZ\", \"grafico TikZ\", \"prodotto con pgfplots\""
            " o qualsiasi altra menzione dello strumento di generazione.\n"
            "  Usa solo: \"Si osservi il seguente grafico:\" oppure \"Dal grafico riportato di seguito:\"\n"
            "  ⚠️ CONTROLLO QUALITÀ: prima di scrivere \\begin{tikzpicture}, verifica mentalmente che il codice sia "
            "completo, bilanciato e compilabile. Ogni \\begin{...} deve avere il corrispondente \\end{...}."
        )
    else:
        grafici_rule = ""

    # ── Regola diversità tipologie — in base al numero di esercizi ─────────────
    if num_esercizi <= 2:
        diversita_rule = (
            "- VARIETÀ TIPOLOGIE: con soli 1-2 esercizi usa domande aperte articolate "
            "in più sottopunti (a, b, c…) che coprono sia la procedura sia la comprensione concettuale."
        )
    elif num_esercizi <= 4:
        diversita_rule = (
            "- VARIETÀ TIPOLOGIE PEDAGOGICA: devi mixare ALMENO 2 tipologie diverse tra quelle adatte alla materia:\n"
            "  • Esercizio aperto (calcolo / dimostrazione / analisi)\n"
            "  • Scelta multipla (\\begin{enumerate}[a)] con 4 opzioni) — 1 sola corretta\n"
            "  • Vero/Falso ($\\square$ \\textbf{V} $\\quad\\square$ \\textbf{F})\n"
            "  • Completamento (\\underline{\\hspace{3cm}})\n"
            "  Non clonare la stessa tipologia per tutti gli esercizi.\n"
            "  Disponi gli esercizi dal più semplice al più complesso (facilità decrescente)."
        )
    else:
        diversita_rule = (
            "- VARIETÀ TIPOLOGIE PEDAGOGICA — REGOLA FONDAMENTALE:\n"
            "  Distribuisci le tipologie su tutti gli esercizi per valutare competenze diverse:\n"
            f"  • ~{max(1, num_esercizi // 3)} esercizi aperti (calcolo / dimostrazione / analisi / problema)\n"
            f"  • ~{max(1, num_esercizi // 4)} esercizi a scelta multipla (4 opzioni, 1 sola corretta)\n"
            f"  • ~{max(1, num_esercizi // 5)} esercizi Vero/Falso o completamento\n"
            "  • I restanti: domande di comprensione concettuale, definizioni, esempi.\n"
            "  NON generare 5+ esercizi tutti della stessa tipologia.\n"
            "  L'ordine deve seguire la tassonomia di Bloom: ricorda → comprendi → applica → analizza.\n"
            "  Il primo esercizio deve essere accessibile anche agli studenti in difficoltà."
        )

    return (
        f"Sei un docente esperto di {materia} e LaTeX. Genera SOLO il corpo degli esercizi "
        f"(senza preambolo, senza \\documentclass, senza \\begin{{document}}) per una verifica su: {argomento}.\n"
        f"{ f'Punti totali da distribuire: {punti_totali} pt.' if mostra_punteggi else ''}\n"
        f"{s_mathpix}"
        f"{istruzioni_esercizi}\n"
        f"\nCALIBRAZIONE LIVELLO E TEMPO:\n"
        f"{calibrazione}\n"
        f"- DURATA PREVISTA: {durata}. Regola la lunghezza dei calcoli, il numero di incognite e la complessità "
        f"testuale in modo che {num_esercizi} esercizi siano agevolmente fattibili nel tempo scelto.\n"
        f"- BILANCIAMENTO CONTESTO E MODELLAZIONE: NON esagerare con i problemi applicati alla realtà o fortemente "
        f"interdisciplinari. MASSIMO 1 o 2 esercizi possono essere contestualizzati. I restanti DEVONO essere "
        f"esercizi canonici, diretti e focalizzati sulla procedura pura.\n"
        f"{diversita_rule}\n"
        f"- REGISTRO LINGUISTICO — REGOLA ASSOLUTA: il testo degli esercizi deve essere CONCISO e DIRETTO.\n"
        f"- LUNGHEZZA MASSIMA: ogni esercizio non deve superare le 8-10 righe di testo. "
        f"MAI generare esercizi lunghissimi o prolissi. Vai dritto al punto senza giri di parole.\n"
        f"- VIETATO ASSOLUTO: NON inserire MAI le soluzioni, le risposte o i risultati negli esercizi. "
        f"MAI scrivere frasi come 'la risposta è...', 'il risultato è...', 'soluzione:', '= X', 'quindi X', "
        f"'infatti X', 'cioè X', 'cioè X', 'dunque X'. L'esercizio deve terminare con la domanda, senza alcun accenno alla risposta.\n"
        f"- VIETATO ASSOLUTO: NON inserire MAI spiegazioni, dimostrazioni complete o passaggi risolutivi. "
        f"Lo studente deve produrre tutto il ragionamento.\n"
        f"- DATI PULITI — REGOLA ASSOLUTA: prima di scrivere ogni esercizio, risolvilo mentalmente tu stesso. "
        f"Scegli SOLO dati che portano a risultati interi o frazioni semplici. MAI scegliere dati che rendono "
        f"un sistema contraddittorio, sovradeterminato o senza soluzione unica (a meno che non sia esplicitamente "
        f"richiesto). Se un esercizio chiede di trovare un'equazione soddisfacendo N condizioni, verifica che le "
        f"N condizioni siano compatibili tra loro.\n"
        f"- CONTROLLO DUPLICATI: ogni esercizio deve essere CONCEPTUALMENTE UNICO. NON generare esercizi "
        f"che testino lo stesso concetto matematico con dati diversi. Esempio: se l'Esercizio 1 chiede di risolvere "
        f"un'equazione di secondo grado, l'Esercizio 3 NON può chiedere di risolvere un'altra equazione di secondo grado. "
        f"Deve testare un'abilità diversa (es. studio di funzione, geometria, probabilità).\n"
        f"- DIFFICOLTÀ PROGRESSIVA: l'Esercizio 1 (Saperi Essenziali) deve essere SEMPRE accessibile, "
        f"con procedura diretta e unica. MAI richiedere ragionamenti complessi, multi-step o astrazione elevata. "
        f"L'Esercizio 1 deve essere risolvibile in 5-8 minuti dallo studente medio.\n"
        f"REGOLE TASSATIVE SUI GRAFICI — LOGICA ANTI-SPOILER:\n"
        f"- Se l'esercizio chiede allo studente di 'disegnare', 'rappresentare graficamente', 'tracciare',\n"
        f"  'costruire' o qualsiasi variante → NON generare NESSUN codice TikZ/pgfplots in quell'esercizio.\n"
        f"  Questo vale anche se solo una parte dell'esercizio lo richiede.\n"
        f"- Genera codice TikZ SOLO se il grafico è un DATO fornito (es. 'dal grafico seguente...').\n"
        f"- AUTOCONTROLLO: prima di scrivere \\begin{{tikzpicture}}, verifica che il testo NON contenga\n"
        f"  'rappresenta', 'disegna', 'traccia', 'graficamente', 'costruisci'. Se sì: stop, niente TikZ.\n"
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
        f"- PROTEZIONE ESERCIZIO 1 (Saperi Essenziali): nell'Esercizio 1 NON inserire MAI il simbolo (*) su nessun sottopunto.\n"
        f"{multi_rule}\n"
        f"- Scelta multipla: le opzioni DEVONO stare in un \\begin{{enumerate}}[a)] SEPARATO dopo la domanda.\n"
        f"- Vero/Falso: $\\square$ \\textbf{{V}} $\\quad\\square$ \\textbf{{F}}\n"
        f"- Completamento: \\underline{{\\hspace{{3cm}}}}\n"
        f"{grafici_rule}\n"
        f"{s_note}"
        f"\nFORMATO OUTPUT: restituisci SOLO i blocchi \\subsection*{{...}} con relativi esercizi.\n"
        f"TERMINA con \\end{{document}}.\n"
        f"NIENTE preambolo, NIENTE \\documentclass, NIENTE \\begin{{document}}.\n"
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
        f"- ANTI-SPOILER GRAFICI: se un esercizio contiene codice TikZ/pgfplots E il testo usa\n"
        f"  'rappresenta', 'disegna', 'traccia', 'graficamente', 'costruisci' → RIMUOVI il TikZ.\n"
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
        f"7. INTESTAZIONE: nella riga Nome/Classe/Data aggiungi 'Fila B' visibile.\n"
        f"8. COHERENZA: verifica che i nuovi dati siano matematicamente coerenti\n"
        f"   (niente radici di negativi, divisioni per zero, misure impossibili).\n\n"
        f"OUTPUT: SOLO codice LaTeX completo identico nella struttura, "
        f"con \\end{{document}} finale. Nessuna spiegazione."
    )
