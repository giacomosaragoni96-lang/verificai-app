# 📝 Sistema di Valutazione Dettagliata Esercizi

## 🎯 Obiettivo

Sistema completo per valutare singolarmente gli esercizi generati da VerificAI e salvarli in un database con tagging materia-argomento.

## 📋 Funzionalità

### ✅ Valutazione Singoli Esercizi
- **Valutazione individuale** di ogni esercizio
- **Assegnazione punteggi** personalizzati
- **Feedback dettagliato** per ogni esercizio
- **Commenti specifici** e note del valutatore

### ✅ Database con Tagging
- **Salvataggio automatico** in database SQLite
- **Tag materia-argomento** per categorizzazione
- **Ricerca e filtraggio** avanzati
- **Statistiche dettagliate** per materia-argomento

### ✅ Interfaccia Utente
- **Form intuitivo** per valutazione rapida
- **Visualizzazione esercizi** in formato LaTeX
- **Metriche in tempo reale** (percentuali, media)
- **Export JSON** per analisi esterne

## 🚀 Installazione e Utilizzo

### 1. File Principali
```
📁 valutazione_esercizi.py     # Sistema completo valutazione
📁 integrazione_valutazione.py # Integrazione con app principale
📁 README_VALUTAZIONE.md       # Documentazione
```

### 2. Avvio Sistema Standalone
```bash
streamlit run valutazione_esercizi.py
```

### 3. Integrazione in VerificAI
```python
# In main.py, aggiungi dopo generazione verifica
from integrazione_valutazione import aggiungi_pulsante_valutazione

# Dopo la generazione riuscita:
aggiungi_pulsante_valutazione(result, scenario)
```

## 📊 Struttura Database

### Tabella: `esercizi_valutati`
| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `id` | INTEGER | ID univoco |
| `id_verifica` | TEXT | ID della verifica |
| `materia` | TEXT | Materia (es. Matematica) |
| `argomento` | TEXT | Argomento (es. Trigonometria) |
| `numero_esercizio` | INTEGER | Numero esercizio |
| `titolo_esercizio` | TEXT | Titolo esercizio |
| `contenuto_esercizio` | TEXT | Contenuto LaTeX |
| `punteggio_assegnato` | REAL | Punteggio dato |
| `punteggio_massimo` | REAL | Punteggio massimo |
| `feedback` | TEXT | Feedback generale |
| `commenti` | TEXT | Commenti specifici |
| `tag_difficolta` | TEXT | Difficoltà |
| `tag_competenze` | TEXT | Competenze |
| `data_valutazione` | TEXT | Data valutazione |
| `valutatore` | TEXT | Nome valutatore |

## 🎯 Flusso di Valutazione

### 1. **Estrazione Esercizi**
```python
# Estrae automaticamente esercizi dal LaTeX
esercizi = estrai_esercizi_da_latex(latex_content)
```

### 2. **Form Valutazione**
- **Punteggio assegnato** (0 - punteggio massimo)
- **Feedback** (Eccellente/Insufficiente)
- **Difficoltà** (Molto facile - Molto difficile)
- **Competenze** (Comprensione/Applicazione/Analisi)
- **Commenti** personalizzati

### 3. **Salvataggio Database**
```python
# Salva automaticamente tutte le valutazioni
for valutazione in valutazioni_salvate:
    salva_valutazione(valutazione)
```

### 4. **Statistiche**
- **Media punteggi** per materia-argomento
- **Distribuzione feedback** e difficoltà
- **Trend temporali** valutazioni

## 🔍 Funzionalità Avanzate

### 📈 Statistiche Dettagliate
```python
# Ottieni statistiche per materia-argomento
statistiche = get_statistiche_materia_argomenti()
```

### 🔍 Ricerca Avanzata
- **Filtri per materia/argomento**
- **Range punteggi**
- **Feedback specifici**
- **Date valutazione**

### 📥 Export Dati
```python
# Export in formato JSON
esporta_valutazioni_json(valutazioni)
```

## 🎛️ Interfaccia Utente

### 📋 Menu Principale
1. **Nuova Valutazione** - Valuta esercizi da LaTeX
2. **Valutazioni Salvate** - Consulta valutazioni esistenti
3. **Statistiche** - Visualizza statistiche dettagliate
4. **Ricerca Avanzata** - Trova valutazioni specifiche

### 🎯 Form Valutazione
```
📝 Esercizio 1: Titolo Esercizio
├── Punteggio: [_____/10 pt]
├── Feedback: [Eccellente ▼]
├── Difficoltà: [Media ▼]
├── Competenze: [☑ Comprensione ☑ Applicazione]
└── Commenti: [________________]
```

## 🔄 Integrazione con VerificAI

### 1. **Aggiungi Pulsante Valutazione**
```python
# In main.py, dopo generazione verifica
if result['success']:
    aggiungi_pulsante_valutazione(result, scenario)
```

### 2. **Menu Laterale**
```python
# Aggiungi al menu principale
aggiungi_menu_valutazione()
```

### 3. **Workflow Completo**
1. ✅ **Genera verifica** con VerificAI
2. ✅ **Clicca "Avvia Valutazione"**
3. ✅ **Compila form** per ogni esercizio
4. ✅ **Salva valutazioni** nel database
5. ✅ **Visualizza statistiche** e trend

## 📊 Esempi Utilizzo

### 🎯 Valutazione Rapida
```python
# Valuta verifica di Matematica
result = genera_verifica_reale(scenario)
aggiungi_pulsante_valutazione(result, scenario)
```

### 📈 Analisi Statistiche
```python
# Analizza performance per materia
statistiche = get_statistiche_materia_argomento()
for chiave, stats in statistiche.items():
    print(f"{chiave}: {stats['media_punteggi']}/10")
```

### 🔍 Ricerca Valutazioni
```python
# Trova tutte le valutazioni di Matematica
valutazioni_matematica = carica_valutazioni(materia="Matematica")
```

## 🎉 Benefici

### ✅ Per Docenti
- **Valutazione strutturata** e coerente
- **Feedback dettagliato** per studenti
- **Analisi trend** performance classe
- **Condivisione** valutazioni tra colleghi

### ✅ Per Studenti
- **Feedback specifico** per ogni esercizio
- **Tracciamento progressi** nel tempo
- **Identificazione aree** miglioramento
- **Preparazione mirata** esami

### ✅ Per Istituto
- **Database centralizzato** valutazioni
- **Statistiche aggregate** per materia
- **Analisi qualità** esercizi
- **Benchmarking** tra classi

## 🔧 Configurazione

### Database
```python
# Database SQLite automatico
DB_PATH = "valutazioni_esercizi.db"
```

### Tag Personalizzati
```python
# Aggiungi nuove competenze
competenze = ["Comprensione", "Applicazione", "Analisi", "Sintesi", "Valutazione", "Creatività", "Problem Solving"]
```

### Scale Valutazione
```python
# Personalizza scale feedback
feedback_options = ["Eccellente", "Buono", "Sufficiente", "Insufficiente", "Da migliorare"]
```

## 🚀 Sviluppi Futuri

- 📊 **Grafici interattivi** per statistiche
- 🎯 **Machine Learning** per suggerimenti valutazione
- 📱 **App mobile** per valutazioni offline
- 🔗 **Integrazione LMS** (Moodle, Google Classroom)
- 📈 **Dashboard principale** per istituto
- 🎓 **Report personalizzati** per studenti

---

## 📞 Supporto

Per assistenza o domande:
1. 📖 Consulta la documentazione
2. 🔍 Controlla esempi utilizzo
3. 📝 Apri issue su GitHub
4. 💬 Contatta supporto tecnico

**Inizia subito a valutare gli esercizi con il sistema completo di VerificAI!** 🎉
