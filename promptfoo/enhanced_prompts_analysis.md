# 🔍 ANALISI PROBLEMI PROMPT - VerificAI Enhanced

## 📊 **RISULTATI ANALISI OUTPUT**

### ✅ **COSA FUNZIONA**
- **Numero esercizi**: 5/5 ✅ PERFETTO
- **Italiano Medie**: 4/4 esercizi + 80/80 punti ✅ PERFETTO  
- **Fisica**: 3/3 esercizi + 0/0 punti ✅ PERFETTO

### ❌ **PROBLEMA CRITICO**
- **Matematica Derivate**: 5/5 esercizi ✅ ma 200/100 punti ❌

## 🔍 **ANALISI DEL PROBLEMA**

### **Output Matematica - Punti Trovati**:
```
['20', '20', '20', '7', '7', '6', '20', '10', '10', '20', '10', '10', '20', '5', '5', '5', '5']
```

**Problema**: Gemini sta aggiungendo **punti multipli per ogni esercizio** invece di un punteggio totale per esercizio.

### **Causa Radice**:
1. Gemini interpreta "distribuisci i punti" come "aggiungi più punti per esercizio"
2. Non capisce che ogni esercizio dovrebbe avere un punteggio totale
3. Sta sommando punti di tutti i sottopunti invece di assegnare un totale per esercizio

## 💡 **SOLUZIONI PROPOSTE**

### **Opzione 1: Istruzioni Ultra-Precise**
Aggiungere nel prompt:
```
- REGOLA CRITICA PUNTEGGI: Ogni esercizio deve avere UN SOLO punteggio totale
- NON aggiungere punti a ogni sottopunto - solo un totale per esercizio
- ESEMPIO CORRETTO: \subsection*{Esercizio 1} (20 pt) seguito da \item[a)... \item[b)... 
- ERRORE DA EVITARE: \item[a)] (10 pt) \item[b)] (10 pt) -> questo crea doppio conteggio!
```

### **Opzione 2: Formato Alternativo**
Cambiare il formato dei punti:
```
- Formato ALTERNATIVO: \subsection*{Esercizio 1: Titolo [20 pt]} 
- In questo modo il punteggio è nel titolo e non viene duplicato
```

### **Opzione 3: Istruzione Matematica Esplicita**
```
- CALCOLO MATEMATICO OBBLIGATORIO: Se hai 5 esercizi e 100 punti totali
  ogni esercizio deve avere circa 20 pt (es: 20, 20, 20, 20, 20)
- NON superare mai il totale di {punti_totali} pt
```

## 🎯 **RACCOMANDAZIONE FINALE**

**Modificare prompts.py** con istruzioni più chiare sul formato dei punti per evitare il doppio conteggio.

Il problema è specifico del **calcolo matematico** che Gemini fa dei punti - non li conta correttamente quando ci sono più sottopunti.
