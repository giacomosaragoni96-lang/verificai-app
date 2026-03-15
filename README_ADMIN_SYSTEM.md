# 🔧 Admin Test & Valutazione System - VerificAI

## 🎯 **Obiettivo del Sistema**

Sistema completo **admin-only** per testare 30 verifiche casuali e valutare esercizi/verifiche approvati. Gli esercizi approvati vengono accumulati in database e usati per migliorare l'AI nel tempo.

---

## 🏗️ **Architettura del Sistema**

### **Componenti Principali**
1. **Admin Test System** - Interfaccia principale per admin
2. **Test Engine** - Esecuzione test su 30 verifiche
3. **Valutazione System** - Approvazione SI/NO esercizi e verifiche
4. **Database Approvati** - Archivio esercizi/verifiche approvati
5. **AI Training Integration** - Sistema di learning loop

### **Flusso Principale**
```
Admin → Lancia 30 Test → Vedi Risultati → Valuta Verifiche → Approva SI/NO → Database → AI Training
```

---

## 📊 **Database Structure**

### **Database 1: `admin_valutazioni.db`**

#### **Tabella `esercizi_approvati`**
```sql
CREATE TABLE esercizi_approvati (
    id INTEGER PRIMARY KEY,
    materia TEXT,              -- Matematica, Fisica...
    argomento TEXT,            -- Trigonometria, pH...
    livello TEXT,              -- Scuola Media, Liceo...
    titolo_esercizio TEXT,     -- Titolo esercizio
    contenuto_esercizio TEXT,   -- Contenuto completo
    punteggio_massimo REAL,    -- Punteggio massimo
    id_verifica TEXT,          -- ID verifica origine
    data_approvazione TEXT,    -- Timestamp approvazione
    valutatore TEXT,           -- Admin che ha approvato
    numero_usi INTEGER DEFAULT 0 -- Volte usato per AI training
);
```

#### **Tabella `verifiche_approvate`**
```sql
CREATE TABLE verifiche_approvate (
    id INTEGER PRIMARY KEY,
    id_verifica TEXT,          -- ID univoco verifica
    materia TEXT,
    argomento TEXT,
    livello TEXT,
    titolo_verifica TEXT,     -- Titolo completo verifica
    contenuto_completo TEXT,   -- LaTeX completo
    numero_esercizi INTEGER,  -- Numero esercizi
    data_approvazione TEXT,
    valutatore TEXT
);
```

#### **Tabella `statistiche_approvati`**
```sql
CREATE TABLE statistiche_approvati (
    id INTEGER PRIMARY KEY,
    materia TEXT,
    argomento TEXT,
    livello TEXT,
    totale_esercizi INTEGER,  -- Esercizi approvati
    totale_verifiche INTEGER, -- Verifiche approvate
    ultimo_aggiornamento TEXT
);
```

### **Database 2: `test_results.db`**

#### **Tabella `test_results`**
```sql
CREATE TABLE test_results (
    id INTEGER PRIMARY KEY,
    test_session_id TEXT,      -- ID sessione test
    materia TEXT,
    argomento TEXT,
    livello TEXT,
    id_verifica TEXT,
    esito_test TEXT,           -- 'PASS', 'FAIL', 'PARTIAL'
    punteggio_test REAL,       -- Score 0-10
    dettagli_test TEXT,        -- Dettagli esito
    data_test TEXT
);
```

#### **Tabella `test_sessions`**
```sql
CREATE TABLE test_sessions (
    id TEXT PRIMARY KEY,        -- Session ID
    data_sessione TEXT,
    totale_verifiche INTEGER,
    pass_count INTEGER,
    fail_count INTEGER,
    partial_count INTEGER,
    punteggio_medio REAL
);
```

---

## 🚀 **Come Usare il Sistema**

### **1. Accesso Admin**
```python
# Solo admin possono accedere
ADMIN_EMAILS = ["admin@verificai.ai", "g.saragoni96@gmail.com"]

# Verifica automatica accesso
def check_admin_access():
    if st.session_state.utente.email not in ADMIN_EMAILS:
        st.error("⛔ Accesso negato. Privilegi amministrativi richiesti.")
        st.stop()
```

### **2. Avvio Sistema**
```bash
# Avvia il sistema admin
streamlit run admin_test_system.py
```

### **3. Workflow Completo**

#### **Step 1: Lancia Test**
1. Vai su "🧪 Lancia Test"
2. Configura materia, argomento, livello
3. Clicca "🚀 Genera 30 Verifiche di Test"
4. Clicca "▶️ Esegui Tutti i Test"

#### **Step 2: Vedi Risultati**
1. Vai su "📋 Risultati Test"
2. Seleziona sessione test
3. Vedi statistiche: PASS/FAIL/PARTIAL
4. Clicca "✅ Valuta" per le verifiche interessanti

#### **Step 3: Valuta Verifiche**
1. Vedi contenuto completo verifica
2. Decidi approvazione verifica intera: ✅ SI / ❌ NO
3. Decidi approvazione esercizi singoli: ✅ SI / ❌ NO
4. Clicca "💾 Salva Valutazione"

#### **Step 4: Accumula Database**
- **Verifiche approvate** → salvate in `verifiche_approvate`
- **Esercizi approvati** → salvati in `esercizi_approvati`
- **Statistiche** → aggiornate automaticamente

#### **Step 5: AI Training**
- AI usa esempi approvati per generazioni future
- Rotazione automatica esempi
- Qualità migliorata nel tempo

---

## 🎯 **Funzionalità Dettagliate**

### **📋 Dashboard Overview**
- **Metriche principali**: esercizi approvati, verifiche approvate, test totali, quality rate
- **Grafici**: andamento approvazioni, distribuzione materie
- **Azioni rapide**: lancia test, valuta esercizi, vedi statistiche

### **🧪 Lancia Test**
- **Configurazione**: materia, argomento, livello, numero esercizi, punti totali
- **Generazione**: 30 set di parametri casuali
- **Esecuzione**: test simultanei con progress bar
- **Risultati**: statistiche immediate PASS/FAIL/PARTIAL

### **📋 Risultati Test**
- **Sessioni test**: storico completo sessioni
- **Filtraggio**: per materia, argomento, livello
- **Dettagli**: score, esito, note per ogni verifica
- **Azioni**: valuta singola verifica, prossima verifica

### **✅ Valutazione Esercizi**
- **Visualizzazione verifica**: contenuto LaTeX completo
- **Valutazione verifica intera**: ✅ SI / ❌ NO
- **Valutazione esercizi singoli**: ✅ SI / ❌ NO per ogni esercizio
- **Commenti**: note per miglioramenti
- **Salvataggio**: automatico in database approvati

### **📊 Statistiche**
- **Overview**: metriche generali del sistema
- **Esercizi**: distribuzione per materia/argomento
- **Verifiche**: andamento approvazioni nel tempo
- **Test**: performance test, distribuzione esiti

### **🗄️ Database Approvati**
- **Esercizi**: elenco completo esercizi approvati
- **Verifiche**: elenco completo verifiche approvate
- **Filtri**: per materia, argomento, livello
- **Export**: CSV per analisi esterna

---

## 🤖 **AI Training Integration**

### **Come Funziona**
1. **Esempi Approvati**: Database con esercizi validati
2. **Prompt Enhancement**: Arricchisce prompt con esempi
3. **Rotazione**: Usa esempi diversi ogni volta
4. **Learning Loop**: Qualità migliora nel tempo

### **Integrazione nel Sistema Principale**
```python
# In main.py o sistema generazione
from ai_training_from_approved import enhance_generation_prompt_with_approved

# Arricchisci prompt con esempi approvati
enhanced_prompt = enhance_generation_prompt_with_approved(
    base_prompt, materia, argomento, livello
)

# Usa enhanced_prompt per generazione
result = generate_verification(enhanced_prompt)
```

### **Esempio Prompt Arricchito**
```
Genera 3 esercizi di Matematica - Trigonometria per Liceo.

ESEMPI DI ESERCIZI APPROVATI PER QUESTO ARGOMENTO:
ESEMPIO APPROVATO 1 (Punteggio: 10 pt):
Esercizio 1: Calcolo Seno e Coseno
Calcola il seno e il coseno degli angoli seguenti...
[contenuto esercizio approvato]

ESEMPIO APPROVATO 2 (Punteggio: 10 pt):
Esercizio 2: Problemi Applicati
Un edificio di 30m proietta un'ombra di 45m...
[contenuto esercizio approvato]

Segui lo stile, la struttura e il livello di difficoltà degli esempi approvati.
```

---

## 📈 **Metriche di Successo**

### **Target Goals**
| Metrica | Target 1 Mese | Target 3 Mesi | Target 6 Mesi |
|----------|---------------|---------------|---------------|
| Esercizi Approvati | 100+ | 500+ | 1000+ |
| Verifiche Approvate | 30+ | 150+ | 300+ |
| Quality Rate | 70% | 80% | 90% |
| Coverage Argomenti | 20+ | 50+ | 100+ |

### **KPI da Monitorare**
- **Approval Rate**: % verifiche approvate sul totale testate
- **Exercise Quality**: score medio esercizi approvati
- **AI Improvement**: miglioramento generazioni nel tempo
- **Usage Rate**: % esempi approvati usati nel training

---

## 🛠️ **Setup e Deployment**

### **File Principali**
```
📁 admin_test_system.py          # Sistema principale admin
📁 ai_training_from_approved.py  # Integrazione AI training
📁 admin_valutazioni.db           # Database valutazioni
📁 test_results.db               # Database test results
📁 README_ADMIN_SYSTEM.md        # Documentazione
```

### **Dependencies**
```python
streamlit>=1.28.0      # Dashboard admin
sqlite3>=3.0.0         # Database
pandas>=1.5.0          # Data analysis
plotly>=5.0.0          # Grafici
datetime>=4.0          # Timestamps
```

### **Setup Iniziale**
```bash
# 1. Installa dipendenze
pip install streamlit pandas plotly

# 2. Avvia sistema admin
streamlit run admin_test_system.py

# 3. Configura email admin in ADMIN_EMAILS
# 4. Inizia a testare e valutare!
```

---

## 🎯 **Best Practices**

### **Per Admin**
1. **Test regolari**: lancia test settimanali per accumulare dati
2. **Valutazione coerente**: usa criteri uniformi per approvazioni
3. **Diversità**: approva esercizi di diversi tipi e difficoltà
4. **Documentazione**: aggiungi commenti utili per miglioramenti

### **Per Sistema**
1. **Backup database**: periodico delle tabelle approvati
2. **Performance monitoring**: tracking metriche sistema
3. **Quality gates**: mantieni standard elevati approvazioni
4. **AI feedback loop**: monitora miglioramento generazioni

---

## 🔄 **Workflow Esempio**

### **Sessione Tipica Admin**
```
09:00 - Apri admin_test_system.py
09:05 - Vai su "🧪 Lancia Test"
09:10 - Configura: Matematica, Trigonometria, Liceo, 3 esercizi, 30 pt
09:15 - "🚀 Genera 30 Verifiche" → "▶️ Esegui Tutti i Test"
09:25 - Risultati: 18 PASS, 8 FAIL, 4 PARTIAL
09:30 - Vai su "📋 Risultati Test"
09:35 - Seleziona sessione, filtra PASS > 8.0
09:40 - Inizia valutazione: "✅ Valuta" prima verifica
09:45 - Vedi contenuto, approva verifica ✅ SI
09:50 - Approva esercizi: E1 ✅ SI, E2 ✅ SI, E3 ❌ NO
09:55 - "💾 Salva Valutazione" → salvati in database
10:00 - "⏭️ Prossima Verifica" → continua ciclo
10:30 - Valutate 5 verifiche, 12 esercizi approvati
10:35 - Vai su "📊 Statistiche" → vedi progresso
10:40 - Vai su "🗄️ Database Approvati" → esporta CSV
10:45 - Fine sessione admin
```

---

## 🎉 **Risultati Attesi**

### **Breve Termine (1 mese)**
- **100+ esercizi approvati** di alta qualità
- **30+ verifiche complete** validate
- **AI migliorata** con esempi reali
- **Processo standardizzato** per valutazione

### **Medio Termine (3 mesi)**
- **500+ esercizi approvati** in database
- **150+ verifiche approvate** complete
- **AI quality rate 80%** su generazioni
- **Coverage completa** materie principali

### **Lungo Termine (6 mesi)**
- **1000+ esercizi approvati** system-wide
- **300+ verifiche approvate** reference
- **AI autonomously high-quality** generazioni
- **Scalable system** per multi-admin

---

## 📞 **Support e Manutenzione**

### **Troubleshooting**
- **Database errors**: controlla permessi file
- **Test failures**: verifica parametri configurazione
- **Performance**: ottimizza query con indici
- **Access issues**: verifica email admin configurate

### **Manutenzione**
- **Weekly**: backup database, pulizia sessioni vecchie
- **Monthly**: review metriche, aggiorna criteri valutazione
- **Quarterly**: export dati, analisi trend, miglioramenti sistema

---

## 🔮 **Future Enhancements**

### **Short Term**
- [ ] Batch evaluation (valuta più verifiche insieme)
- [ ] Advanced filters (per punteggio, difficoltà)
- [ ] Export multi-formato (JSON, XML)
- [ ] Email notifications per admin

### **Medium Term**
- [ ] Multi-admin support con ruoli
- [ ] Advanced AI metrics e analytics
- [ ] Integration con LMS systems
- [ ] Mobile app per valutazioni

### **Long Term**
- [ ] Machine learning per auto-valutazione
- [ ] Predictive analytics per quality
- [ ] Enterprise features e scaling
- [ ] API REST per integrazioni esterne

---

## 🎯 **Conclusione**

L'**Admin Test & Valutazione System** è il prodotto finale che permette:

- ✅ **Test sistematici** su 30 verifiche casuali
- ✅ **Valutazione efficiente** SI/NO esercizi e verifiche
- ✅ **Database curated** di contenuti approvati
- ✅ **AI training** basato su esempi reali
- ✅ **Quality improvement** continuo nel tempo

**Il risultato è un sistema autonomo che migliora costantemente la qualità delle verifiche generate dall'AI!** 🌟

---

*Per supporto o domande, contattare l'amministratore di sistema.* 📧
