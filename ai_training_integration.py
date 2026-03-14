"""
Integrazione del sistema di training AI con esercizi qualità
Modifica i prompt per includere esempi di alta qualità
"""

import sqlite3
from datetime import datetime

def crea_prompt_con_esempi(materia, argomento, livello, num_esercizi, punti_totali):
    """Crea prompt arricchito con esempi di qualità"""
    
    # Carica esempi di qualità
    esempi = carica_esempi_qualita_formattati(materia, argomento, livello, limit=3)
    
    # Prompt base
    prompt_base = f"""
Genera ESATTAMENTE {num_esercizi} esercizi di {materia} - {argomento} per livello {livello}.
Il punteggio totale deve essere ESATTAMENTE {punti_totali} pt.
"""
    
    # Aggiungi esempi se disponibili
    if esempi:
        prompt_esempi = f"""
ESEMPI DI ALTA QUALITÀ PER QUESTO ARGOMENTO:
{esempi}

Segui lo stile, la struttura e il livello di difficoltà degli esempi sopra.
Mantieni la stessa qualità e appropriatezza per studenti di {livello}.
"""
        return prompt_base + prompt_esempi
    else:
        return prompt_base + "\nNota: Nessun esempio di qualità disponibile per questo argomento. Basati sulle migliori pratiche didattiche."

def carica_esempi_qualita_formattati(materia, argomento, livello, limit=3):
    """Carica e formatta esempi di qualità per il prompt"""
    
    DB_PATH = "valutazioni_esercizi.db"
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT titolo_esercizio, contenuto_esercizio, qualita_score
            FROM esercizi_qualita 
            WHERE materia = ? AND argomento = ? AND livello = ?
            ORDER BY qualita_score DESC, numero_usi ASC, RANDOM()
            LIMIT ?
        ''', (materia, argomento, livello, limit))
        
        risultati = cursor.fetchall()
        
        if not risultati:
            return ""
        
        esempi_formattati = ""
        for i, (titolo, contenuto, score) in enumerate(risultati, 1):
            esempi_formattati += f"""
ESEMPIO {i} (Qualità: {score:.3f}):
{titolo}

{contenuto.strip()[:500]}{"..." if len(contenuto) > 500 else ""}

---
"""
        
        # Aggiorna contatore usi
        for risultato in risultati:
            cursor.execute('''
                UPDATE esercizi_qualita 
                SET numero_usi = numero_usi + 1, ultima_usa = ?
                WHERE titolo_esercizio = ? AND contenuto_esercizio = ?
            ''', (datetime.now().isoformat(), risultato[0], risultato[1]))
        
        conn.commit()
        conn.close()
        
        return esempi_formattati.strip()
        
    except Exception as e:
        print(f"Errore caricando esempi qualità: {e}")
        return ""

def aggiorna_prompt_generation(gp):
    """Aggiorna il prompt di generazione con esempi di qualità"""
    
    materia = gp.get('materia', '')
    argomento = gp.get('argomento', '')
    livello = gp.get('difficolta', 'Media')
    num_esercizi = gp.get('num_esercizi', 3)
    punti_totali = gp.get('punti_totali', 30)
    
    # Crea prompt migliorato
    prompt_migliorato = crea_prompt_con_esempi(
        materia, argomento, livello, num_esercizi, punti_totali
    )
    
    return prompt_migliorato

def get_training_statistics():
    """Ottiene statistiche sul training AI"""
    
    DB_PATH = "valutazioni_esercizi.db"
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Statistiche generali
        cursor.execute("SELECT COUNT(*) FROM esercizi_qualita")
        total_quality = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM esercizi_valutati")
        total_evaluated = cursor.fetchone()[0]
        
        cursor.execute("SELECT AVG(qualita_score) FROM esercizi_qualita")
        avg_quality = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT COUNT(DISTINCT materia) FROM esercizi_qualita")
        subject_coverage = cursor.fetchone()[0]
        
        # Top materie
        cursor.execute("""
            SELECT materia, COUNT(*) as count 
            FROM esercizi_qualita 
            GROUP BY materia 
            ORDER BY count DESC 
            LIMIT 5
        """)
        top_subjects = cursor.fetchall()
        
        conn.close()
        
        return {
            'total_quality': total_quality,
            'total_evaluated': total_evaluated,
            'quality_rate': (total_quality / total_evaluated * 100) if total_evaluated > 0 else 0,
            'avg_quality': avg_quality,
            'subject_coverage': subject_coverage,
            'top_subjects': top_subjects
        }
        
    except Exception as e:
        print(f"Errore statistiche training: {e}")
        return {}

def export_training_corpus():
    """Esporta il corpus completo di esercizi qualità per training esterno"""
    
    DB_PATH = "valutazioni_esercizi.db"
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT materia, argomento, livello, titolo_esercizio, 
                   contenuto_esercizio, qualita_score, feedback
            FROM esercizi_qualita 
            ORDER BY qualita_score DESC
        ''')
        
        risultati = cursor.fetchall()
        
        corpus = {
            'metadata': {
                'export_date': datetime.now().isoformat(),
                'total_exercises': len(risultati),
                'description': 'Corpus of high-quality exercises for AI training'
            },
            'exercises': []
        }
        
        for materia, argomento, livello, titolo, contenuto, score, feedback in risultati:
            corpus['exercises'].append({
                'subject': materia,
                'topic': argomento,
                'level': livello,
                'title': titolo,
                'content': contenuto,
                'quality_score': score,
                'feedback': feedback
            })
        
        conn.close()
        return corpus
        
    except Exception as e:
        print(f"Errore export corpus: {e}")
        return {}

def suggest_improvements():
    """Suggerisce miglioramenti basati sui dati di qualità"""
    
    stats = get_training_statistics()
    
    suggestions = []
    
    # Copertura materie
    if stats.get('subject_coverage', 0) < 5:
        suggestions.append("📚 Espandi la copertura delle materie - attualmente solo {} materie".format(stats.get('subject_coverage', 0)))
    
    # Tasso qualità
    if stats.get('quality_rate', 0) < 30:
        suggestions.append("🎯 Migliora il tasso di qualità - solo {:.1f}% degli esercizi sono di alta qualità".format(stats.get('quality_rate', 0)))
    
    # Qualità media
    if stats.get('avg_quality', 0) < 0.8:
        suggestions.append("⭐ Aumenta la qualità media - attualmente {:.3f}".format(stats.get('avg_quality', 0)))
    
    # Gap argomenti
    if stats.get('total_quality', 0) < 100:
        suggestions.append("📈 Accumula più esercizi - attualmente {} esercizi di qualità".format(stats.get('total_quality', 0)))
    
    return suggestions

# Funzione di integrazione principale da chiamare nel sistema di generazione
def enhance_generation_with_quality_examples(gp, prompt_base):
    """Enhance generation prompt with quality examples"""
    
    # Aggiungi esempi di qualità al prompt
    prompt_enhanced = aggiorna_prompt_generation(gp)
    
    # Log per debugging
    print(f"🤖 Enhanced prompt with quality examples for {gp.get('materia', '')} - {gp.get('argomento', '')}")
    
    return prompt_enhanced
