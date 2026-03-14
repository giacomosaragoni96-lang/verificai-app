# PromptFoo per VerificAI — Guida Completa

## Cos'è e Perché Serve

PromptFoo è un framework di **testing automatizzato per prompt AI**. Per VerificAI, risolve un problema critico: oggi modifichi `prompts.py` "alla cieca", sperando che il nuovo prompt funzioni meglio del precedente. Non hai modo di sapere se un cambio ha:
- Rotto la generazione di punteggi
- Introdotto placeholder LaTeX
- Abbassato la qualità didattica per un certo livello scolastico
- Sbilanciato il numero di esercizi

Con PromptFoo, **ogni modifica a prompts.py viene validata automaticamente** contro una suite di test che verifica struttura LaTeX, punteggi, anti-spoiler, calibrazione per livello e qualità didattica.

---

## Setup (5 minuti)

### Step 1: Installa le dipendenze

```bash
pip install promptfoo google-generativeai
```

### Step 2: Imposta le variabili d'ambiente

```bash
# La tua chiave API Gemini (stessa che usi in st.secrets)
export GEMINI_API_KEY=AIzaSy...la_tua_chiave...

# Il percorso dove si trovano prompts.py e config.py del tuo progetto
export VERIFICAI_ROOT=/Users/giacomo/Desktop/verificai
```

**Per renderlo permanente**, aggiungi queste righe al tuo `~/.zshrc` o `~/.bashrc`:

```bash
echo 'export GEMINI_API_KEY=la_tua_chiave' >> ~/.zshrc
echo 'export VERIFICAI_ROOT=/percorso/al/progetto' >> ~/.zshrc
source ~/.zshrc
```

### Step 3: Posiziona la cartella `promptfoo/`

Copia l'intera cartella `promptfoo/` nella **root del tuo progetto** VerificAI, così:

```
verificai/
├── main.py
├── prompts.py          ← PromptFoo testa QUESTE funzioni
├── config.py
├── generation.py
├── ...
└── promptfoo/          ← NUOVA CARTELLA
    ├── promptfooconfig.yaml
    ├── run_tests.sh
    ├── prompts/
    │   └── verificai.txt
    └── providers/
        └── verificai_provider.py
```

### Step 4: Esegui il primo test

```bash
cd promptfoo/
chmod +x run_tests.sh
./run_tests.sh
```

Oppure direttamente:

```bash
cd promptfoo/
promptfoo eval -j 1
```

### Step 5: Visualizza i risultati

```bash
promptfoo view
```

Si apre un browser con una **matrice interattiva** dove vedi:
- ✅ Test passati (verde)
- ❌ Test falliti (rosso)
- Il testo dell'output per ogni test
- Le metriche custom (somma punti, conteggio esercizi, ecc.)

---

## Come Funziona

### Architettura

```
promptfooconfig.yaml          → Definisce i test case e le assertion
        ↓
providers/verificai_provider.py → Chiama le funzioni REALI di prompts.py
        ↓
prompts.py (il TUO file)       → Genera il prompt esatto
        ↓
Google Gemini API              → Produce l'output
        ↓
Assertion (YAML)               → Verifica automaticamente l'output
```

**Il punto chiave**: il provider Python importa e chiama `prompt_corpo_verifica()`, `prompt_titolo()`, ecc. **direttamente dal tuo `prompts.py`**. Non c'è una copia dei prompt — testi esattamente quello che va in produzione.

### Tipi di Assertion

| Tipo | Cosa verifica | Esempio |
|------|--------------|---------|
| `contains` | L'output contiene questa stringa | `\subsection*` presente |
| `not-contains` | L'output NON contiene | No `\documentclass` |
| `icontains` | Contiene (case-insensitive) | "Rivoluzione" trovato |
| `javascript` | Logica custom JS | Conteggio esercizi = 5 |
| `llm-rubric` | Un LLM giudica la qualità | "Livello adeguato per medie?" |
| `metric` | Registra un valore numerico | `somma_punti: 98` |

### I 12 Test Inclusi

| # | Test | Cosa verifica |
|---|------|--------------|
| 1 | Titolo Matematica | No "Verifica di", no virgolette, lunghezza OK |
| 2 | Titolo con errore | Corregge "rivoluzzione" → "Rivoluzione" |
| 3 | Titolo Inglese | Concisione |
| 4 | Corpo Mat LS | Struttura, 5 esercizi, punteggi ~100, no placeholder |
| 5 | Corpo Italiano Medie | 4 esercizi, livello adeguato 11-14 anni |
| 6 | Corpo Fisica no punti | 3 esercizi, ZERO punteggi |
| 7 | Anti-spoiler grafici | No TikZ se chiede "disegna" |
| 8 | Brackets bilanciati | `{` e `}` pari, enumerate aperti=chiusi |
| 9 | Varietà tipologie | ≥2 tipologie diverse su 6 esercizi |
| 10 | Calibrazione Prof. | Linguaggio semplice per Ist. Professionale |
| 11 | Calibrazione Primaria | Adeguato per 6-11 anni |
| 12 | QA corregge errore | Rileva x²+1=0 in R e punteggi sbagliati |

---

## Workflow Quotidiano

### Prima di modificare prompts.py

```bash
cd promptfoo/
promptfoo eval -j 1          # baseline: tutti i test passano?
```

### Dopo aver modificato prompts.py

```bash
promptfoo eval -j 1          # regressione: qualcosa si è rotto?
promptfoo view               # confronta visivamente prima/dopo
```

### Testare un caso specifico

```bash
# Solo test titoli
promptfoo eval --filter-description "Titolo"

# Solo test matematica
promptfoo eval --filter-description "Mat"

# Solo test QA
promptfoo eval --filter-description "QA"
```

---

## Come Aggiungere Nuovi Test

Apri `promptfooconfig.yaml` e aggiungi un blocco sotto `tests:`:

```yaml
  - description: "[Corpo] Chimica Mole — ITI"
    vars:
      prompt_type: corpo
      materia: Chimica
      argomento: "La mole e il numero di Avogadro"
      livello: "Istituto Tecnico Tecnologico/Industriale"
      durata: "50 minuti"
      num_esercizi: 4
      punti_totali: 80
      mostra_punteggi: true
      con_griglia: false
      e_mat: true
    assert:
      - type: javascript
        value: "(output.match(/\\\\subsection\\*/g) || []).length === 4"
      - type: llm-rubric
        value: |
          Chimica per ITI: PASS se esercizi applicativi e linguaggio tecnico
          appropriato. FAIL se troppo teorico o livello sbagliato.
```

### Regola d'oro per i nuovi test

Ogni volta che trovi un bug nell'output (es. "ha generato un placeholder"), **aggiungi un test che lo cattura**:

```yaml
  - description: "[Regression] Bug #42 — placeholder includegraphics"
    vars:
      prompt_type: corpo
      materia: Matematica
      argomento: "Geometria analitica"
      livello: Liceo Scientifico
      # ... resto vars ...
    assert:
      - type: not-icontains
        value: "\\includegraphics{placeholder}"
      - type: not-icontains
        value: "inserisci qui il grafico"
```

Così quel bug **non potrà mai più tornare** senza che il test lo segnali.

---

## Costi

- **PromptFoo**: €0 (open-source MIT, gira locale)
- **API Gemini Flash Lite**: ~€0.01-0.03 per test case
- **Suite completa (12 test)**: ~€0.15-0.35 per run
- **Suggerimento**: esegui la suite 2-3 volte al giorno durante lo sviluppo attivo

---

## Troubleshooting

| Problema | Soluzione |
|----------|----------|
| `ModuleNotFoundError: prompts` | Imposta `export VERIFICAI_ROOT=/percorso/corretto` |
| `GEMINI_API_KEY non impostata` | `export GEMINI_API_KEY=la_tua_chiave` |
| Timeout su Gemini | Aumenta `timeout` nel YAML o usa `-j 1` |
| Rate limiting | Usa `promptfoo eval -j 1 --delay 2000` |
| `llm-rubric` fallisce | Normale: i giudizi LLM hanno varianza. Riesegui. |

---

## File nella Cartella

```
promptfoo/
├── promptfooconfig.yaml      ← Test suite principale (12 test)
├── tests_pipeline.yaml       ← Test suite estesa (Vers.B, Ridotta, Soluzioni, Edge)
├── run_tests.sh              ← Script setup + esecuzione
├── README.md                 ← Questa guida
├── .env.example              ← Template variabili d'ambiente
├── prompts/
│   └── verificai.txt         ← Marker prompt (il provider costruisce il vero prompt)
├── providers/
│   └── verificai_provider.py ← Custom provider: chiama prompts.py + Gemini API
└── validators/
    └── latex_validator.py    ← Validatore compilabilità LaTeX
```

---

## Suite Estesa: Pipeline Completa

Oltre ai 12 test base, c'è `tests_pipeline.yaml` che testa l'intera pipeline:

```bash
# Esegui i test di pipeline
promptfoo eval -c tests_pipeline.yaml -j 1
```

Include test per:
- **Versione B**: cambia dati ma mantiene struttura e punteggi
- **Ridotta BES/DSA**: meno sottopunti, no etichetta "BES/DSA"
- **Soluzioni**: risposte sintetiche e matematicamente corrette
- **Rigenerazione blocco**: trasforma un esercizio su richiesta docente
- **Variante rapida**: Fila B one-click
- **Edge cases**: 1 esercizio, 10 esercizi, note docente, materie non-STEM

---

## Validatore LaTeX

Il file `validators/latex_validator.py` verifica la compilabilità dell'output in 2 passaggi:

1. **Validazione strutturale** (sempre): parentesi graffe bilanciate, ambienti aperti/chiusi
2. **Compilazione pdflatex** (se disponibile): prova a compilare il documento con un preambolo standard

Si usa come assertion nei test:
```yaml
assert:
  - type: python
    value: file://validators/latex_validator.py
```

Oppure standalone:
```bash
python validators/latex_validator.py "corpo_latex_da_testare"
python validators/latex_validator.py file_output.tex
```

> **Nota**: su macchine senza `pdflatex` installato (es. Streamlit Cloud), il validatore
> esegue comunque la validazione strutturale e ritorna pass con score 0.8 invece di 1.0.

---

## Prossimi Passi Consigliati

1. **Esegui la suite base** → identifica i test che falliscono → quelli sono i tuoi prompt da migliorare
2. **Aggiungi test di regressione** per ogni bug che trovi in produzione
3. **Espandi la matrice materie × livelli** per coprire le combinazioni più usate dai docenti
4. **Integra nel tuo workflow Git**: prima di ogni commit a `prompts.py`, esegui `promptfoo eval`
