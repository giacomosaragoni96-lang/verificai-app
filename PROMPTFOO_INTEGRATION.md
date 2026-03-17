# PromptFoo Integration - VerificAI

## 🚀 Sistema Completo di Test Automatici

Abbiamo completamente integrato PromptFoo in VerificAI con un sistema di test automatici, CI/CD e dashboard di monitoraggio.

---

## 📋 Componenti del Sistema

### 1. Interfaccia Unificata (`promptfoo_unified.py`)
- **Test Rapidi**: Matematica, Italiano, Fisica con un click
- **Test Completi**: Suite completa su tutte le materie con filtri
- **Test Reali**: Generazione verifiche reali come dall'app
- **Analisi Risultati**: Metriche e trend storici
- **Dashboard**: Monitoraggio avanzato con grafici

### 2. CI/CD Automation (`scripts/promptfoo_ci.py`)
- **Pre-commit Hook**: Test automatici su ogni modifica a `prompts.py`
- **CI Reports**: Salvataggio automatico dei risultati
- **Regression Detection**: Identifica cali di qualità

### 3. Dashboard Monitoraggio (`promptfoo_dashboard.py`)
- **Andamento Temporale**: Grafici success rate nel tempo
- **Analisi per Materia**: Performance per singola materia
- **Regression Analysis**: Detection automatica regressioni
- **Export Reports**: CSV, JSON per analisi esterne

---

## 🎯 Come Usare

### Accesso Rapido
1. **Dalla Home**: Clicca "🧪 Test Prompt" 
2. **Test Immediato**: Scegli "🎯 Test Rapidi" → "🧮 Test Matematica"
3. **Risultati**: Vedi subito se i prompt funzionano correttamente

### Test Completi
1. **Tab "📊 Test Completi"**
2. **Filtra** per materia/livello se necessario
3. **Esegui** suite completa
4. **Analizza** risultati dettagliati

### Monitoraggio Continuo
1. **Tab "📋 Dashboard"** per analisi avanzate
2. **CI/CD automatico** su ogni commit a `prompts.py`
3. **Report storici** in `promptfoo_ci_reports/`

---

## 🔄 Workflow Sviluppo

### Prima di Modificare `prompts.py`
```bash
# Esegui test baseline
cd promptfoo/
promptfoo eval -j 1
```

### Dopo Modifiche
```bash
# Test automatici via pre-commit hook
git add prompts.py
git commit -m "Fix: migliorato prompt matematica"
# → Test eseguiti automaticamente
```

### Se Test Falliscono
```bash
# Bypass temporaneo (solo per emergenze)
git commit --no-verify -m "Fix: corretto test failure"
```

---

## 📊 Metriche Monitorate

### Qualità Prompt
- **Success Rate**: % test passati
- **Esercizi Corretti**: Numero esercizi generati vs target
- **Punteggi Esatti**: Somma punti vs target
- **Struttura LaTeX**: Validazione brackets/ambienti

### Stabilità nel Tempo
- **Trend**: Andamento quality (positivo/negativo)
- **Volatilità**: Variazione day-to-day
- **Regressioni**: Cali significativi di performance
- **Stabilità**: Consistenza dei risultati

### Performance per Materia
- **Matematica**: Test equazioni, derivate, geometria
- **Italiano**: Analisi testo, grammatica, comprensione
- **Fisica**: Meccanica, termodinamica, elettromagnetismo
- **Altre**: Storia, Inglese, Chimica (espandibile)

---

## 🚨 Allarmi e Notifiche

### Regression Detection
- **Calo > 20%** success rate → Allarme automatico
- **Fallimenti consecutivi** → Notifica dashboard
- **Materia critica** → Priorità alta

### CI/CD Failures
- **Pre-commit block**: Commit rifiutato se test falliscono
- **Report dettagliato**: Cosa è fallito e perché
- **Fix guidance**: Suggerimenti per correzione

---

## 📁 Struttura File

```
verificai/
├── promptfoo_unified.py          # Interfaccia principale
├── promptfoo_dashboard.py        # Dashboard avanzata
├── scripts/
│   └── promptfoo_ci.py          # Automazione CI/CD
├── .git/hooks/
│   └── pre-commit               # Hook Git
├── promptfoo/
│   ├── promptfooconfig.yaml    # Suite test base
│   ├── tests_pipeline.yaml     # Test estesi
│   └── providers/              # Configurazione API
├── promptfoo_ci_reports/        # Report CI/CD (auto)
├── test_results/               # Risultati test (auto)
└── real_verifications/         # Test reali (auto)
```

---

## ⚙️ Configurazione

### Test Suite Base
File: `promptfoo/promptfooconfig.yaml`
- **12 test** essenziali
- **Assertions** JavaScript per metriche precise
- **Materie**: Matematica, Italiano, Fisica, Storia

### Test Suite Estesa
File: `promptfoo/tests_pipeline.yaml`
- **Versione B**: Test varianti
- **Ridotta BES**: Test accessibilità
- **Soluzioni**: Test risposte corrette
- **Edge cases**: 1 esercizio, 10 esercizi, etc.

### CI/CD Configuration
File: `scripts/promptfoo_ci.py`
- **Timeout**: 300 secondi
- **Cache**: Disabilitato per test consistenti
- **Report**: Automatici in JSON

---

## 🔧 Troubleshooting

### Test Falliscono
1. **Check output**: Vedere messaggi errore specifici
2. **Validate prompts**: Controllare sintassi prompts.py
3. **Run manual**: `promptfoo eval -j 1` per debug
4. **Fix one-by-one**: Risolvere test singoli prima di commit

### Dashboard Non Funziona
1. **Install dependencies**: `pip install plotly pandas`
2. **Check data**: Esegui alcuni test prima
3. **Refresh**: Riavvia Streamlit app

### CI/CD Non si Attiva
1. **Check hook**: `.git/hooks/pre-commit` deve essere eseguibile
2. **Git status**: Verifica che `prompts.py` sia cambiato
3. **Permissions**: Su Windows: `icacls` per permissions

---

## 🚀 Prossimi Passi

### Espansione Suite Test
- **Chimica**: Reazioni chimiche, stechiometria
- **Storia**: Analisi fonti, contesto storico
- **Inglese**: Grammar, reading comprehension

### Integrazione Avanzata
- **Slack notifications**: Allarmi in canale dev
- **Performance metrics**: Tempo risposta API
- **Cost tracking**: Monitoraggio costi API

### Machine Learning
- **Predictive analysis**: Previsione regressioni
- **Auto-fix**: Suggerimenti automatici
- **Quality scoring**: Punteggio complessivo qualità

---

## 📞 Supporto

### Issues Comuni
- **PromptFoo install**: `pip install promptfoo`
- **API key setup**: `export GEMINI_API_KEY=...`
- **Dependencies**: `pip install plotly pandas`

### Documentation
- **PromptFoo docs**: https://promptfoo.dev/docs
- **VerificAI wiki**: Internal documentation
- **Examples**: `promptfoo/examples/`

---

## 🎉 Benefici Ottenuti

### Sviluppo Più Veloce
- **Feedback immediato** su modifiche prompt
- **Test automatici** senza sforzo manuale
- **Regression prevention** prima del deploy

### Qualità Garantita
- **Metriche oggettive** sulla qualità
- **Monitoraggio continuo** nel tempo
- **Allarmi proattivi** per problemi

### Team Collaboration
- **Report condivisibili** per team
- **Storia modifiche** tracciata
- **Standard qualitativi** uniformi

---

*Questo sistema trasforma VerificAI in un'applicazione enterprise-grade con test automatici, CI/CD e monitoraggio avanzato della qualità.*
