"""
Sistema di Training AI basato su esercizi verifiche approvati
Integra con il sistema di generazione per migliorare la qualità
"""

import sqlite3
import random
from datetime import datetime
from typing import List, Dict, Any, Optional

DB_PATH = "admin_valutazioni.db"

def get_approved_examples_for_prompt(materia: str, argomento: str, livello: str, limit: int = 3) -> str:
    """
    Carica esempi approvati per arricchire il prompt di generazione
    
    Args:
        materia: Materia richiesta
        argomento: Argomento specifico
        livello: Livello scolastico
        limit: Numero massimo di esempi da includere
    
    Returns:
        Stringa formattata con esempi da includere nel prompt
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Query per esempi approvati con rotazione
        cursor.execute('''
            SELECT titolo_esercizio, contenuto_esercizio, punteggio_massimo, numero_usi
            FROM esercizi_approvati 
            WHERE materia = ? AND argomento = ? AND livello = ?
            ORDER BY numero_usi ASC, RANDOM()
            LIMIT ?
        ''', (materia, argomento, livello, limit))
        
        risultati = cursor.fetchall()
        
        if not risultati:
            return ""
        
        # Formatta esempi per il prompt
        esempi_formattati = ""
        for i, (titolo, contenuto, punteggio, usi) in enumerate(risultati, 1):
            esempi_formattati += f"""
ESEMPIO APPROVATO {i} (Punteggio: {punteggio} pt):
{titolo}

{contenuto.strip()[:800]}{"..." if len(contenuto) > 800 else ""}

---
"""
        
        # Aggiorna contatore utilizzi
        for risultato in risultati:
            cursor.execute('''
                UPDATE esercizi_approvati 
                SET numero_usi = numero_usi + 1 
                WHERE titolo_esercizio = ? AND contenuto_esercizio = ?
            ''', (risultato[0], risultato[1]))
        
        conn.commit()
        conn.close()
        
        return esempi_formattati.strip()
        
    except Exception as e:
        print(f"Errore caricando esempi approvati: {e}")
        return ""

def get_approved_verification_structure(materia: str, argomento: str, livello: str) -> Optional[Dict]:
    """
    Ottiene la struttura di una verifica approvata come template
    
    Args:
        materia: Materia richiesta
        argomento: Argomento specifico
        livello: Livello scolastico
    
    Returns:
        Dizionario con struttura della verifica approvata
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Cerca verifica approvata con stessa materia-argomento-livello
        cursor.execute('''
            SELECT titolo_verifica, contenuto_completo, numero_esercizi
            FROM verifiche_approvate 
            WHERE materia = ? AND argomento = ? AND livello = ?
            ORDER BY RANDOM()
            LIMIT 1
        ''', (materia, argomento, livello))
        
        risultato = cursor.fetchone()
        conn.close()
        
        if risultato:
            return {
                'titolo': risultato[0],
                'contenuto': risultato[1],
                'numero_esercizi': risultato[2]
            }
        
        return None
        
    except Exception as e:
        print(f"Errore caricando struttura verifica: {e}")
        return None

def enhance_generation_prompt_with_approved(base_prompt: str, materia: str, argomento: str, livello: str) -> str:
    """
    Arricchisce il prompt di generazione con esempi approvati
    
    Args:
        base_prompt: Prompt base di generazione
        materia: Materia richiesta
        argomento: Argomento specifico
        livello: Livello scolastico
    
    Returns:
        Prompt arricchito con esempi approvati
    """
    # Carica esempi di esercizi approvati
    esempi_esercizi = get_approved_examples_for_prompt(materia, argomento, livello, limit=3)
    
    # Carica struttura verifica approvata
    struttura_verifica = get_approved_verification_structure(materia, argomento, livello)
    
    # Costruisci prompt arricchito
    enhanced_prompt = base_prompt
    
    if esempi_esercizi:
        enhanced_prompt += f"""

ESEMPI DI ESERCIZI APPROVATI PER QUESTO ARGOMENTO:
{esempi_esercizi}

Segui lo stile, la struttura e il livello di difficoltà degli esempi approvati sopra.
Mantieni la stessa qualità e appropriatezza per studenti di {livello}.
"""
    
    if struttura_verifica:
        enhanced_prompt += f"""

STRUTTURA VERIFICA APPROVATA DI RIFERIMENTO:
Titolo: {struttura_verifica['titolo']}
Numero esercizi: {struttura_verifica['numero_esercizi']}

Segui una struttura simile per organizzare la verifica.
"""
    
    # Aggiungi istruzioni finali
    enhanced_prompt += """

IMPORTANTE: Basati sugli esempi approvati per garantire alta qualità.
"""
    
    return enhanced_prompt

def get_training_statistics() -> Dict[str, Any]:
    """
    Ottiene statistiche sul training AI
    
    Returns:
        Dizionario con statistiche complete
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Statistiche generali
        cursor.execute("SELECT COUNT(*) FROM esercizi_approvati")
        total_exercises = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM verifiche_approvate")
        total_verifications = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT materia) FROM esercizi_approvati")
        subject_coverage = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT argomento) FROM esercizi_approvati")
        topic_coverage = cursor.fetchone()[0]
        
        # Utilizzo esempi
        cursor.execute("SELECT AVG(numero_usi) FROM esercizi_approvati WHERE numero_usi > 0")
        avg_usage = cursor.fetchone()[0] or 0
        
        # Top materie
        cursor.execute("""
            SELECT materia, COUNT(*) as count 
            FROM esercizi_approvati 
            GROUP BY materia 
            ORDER BY count DESC 
            LIMIT 5
        """)
        top_subjects = cursor.fetchall()
        
        conn.close()
        
        return {
            'total_exercises': total_exercises,
            'total_verifications': total_verifications,
            'subject_coverage': subject_coverage,
            'topic_coverage': topic_coverage,
            'avg_usage': avg_usage,
            'top_subjects': top_subjects
        }
        
    except Exception as e:
        print(f"Errore statistiche training: {e}")
        return {}

def suggest_improvements() -> List[str]:
    """
    Suggerisce miglioramenti basati sulle statistiche
    
    Returns:
        Lista di suggerimenti
    """
    stats = get_training_statistics()
    suggestions = []
    
    if stats['total_exercises'] < 50:
        suggestions.append("📝 Accumula più esercizi approvati - attualmente solo {}".format(stats['total_exercises']))
    
    if stats['subject_coverage'] < 5:
        suggestions.append("📚 Espandi copertura materie - attualmente solo {}".format(stats['subject_coverage']))
    
    if stats['avg_usage'] < 2:
        suggestions.append("🔄 Aumenta rotazione esempi - uso medio: {:.1f}".format(stats['avg_usage']))
    
    if stats['total_verifications'] < 20:
        suggestions.append("📋 Approva più verifiche complete - attualmente solo {}".format(stats['total_verifications']))
    
    return suggestions

def export_approved_corpus() -> Dict[str, Any]:
    """
    Esporta il corpus completo di esercizi approvati
    
    Returns:
        Dizionario con corpus esportabile
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        
        # Esercizi approvati
        esercizi_df = pd.read_sql_query("""
            SELECT materia, argomento, livello, titolo_esercizio, 
                   contenuto_esercizio, punteggio_massimo, data_approvazione
            FROM esercizi_approvati 
            ORDER BY data_approvazione DESC
        """, conn)
        
        # Verifiche approvate
        verifiche_df = pd.read_sql_query("""
            SELECT materia, argomento, livello, titolo_verifica, 
                   contenuto_completo, numero_esercizi, data_approvazione
            FROM verifiche_approvate 
            ORDER BY data_approvazione DESC
        """, conn)
        
        conn.close()
        
        corpus = {
            'metadata': {
                'export_date': datetime.now().isoformat(),
                'total_exercises': len(esercizi_df),
                'total_verifications': len(verifiche_df),
                'description': 'Corpus of approved exercises and verifications for AI training'
            },
            'exercises': esercizi_df.to_dict('records') if not esercizi_df.empty else [],
            'verifications': verifiche_df.to_dict('records') if not verifiche_df.empty else []
        }
        
        return corpus
        
    except Exception as e:
        print(f"Errore export corpus: {e}")
        return {}

def get_recommended_examples(materia: str, argomento: str, livello: str, count: int = 5) -> List[Dict]:
    """
    Ottiene esempi raccomandati per un specifico argomento
    
    Args:
        materia: Materia richiesta
        argomento: Argomento specifico
        livello: Livello scolastico
        count: Numero di esempi da restituire
    
    Returns:
        Lista di dizionari con esempi raccomandati
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Query per esempi raccomandati
        cursor.execute('''
            SELECT titolo_esercizio, contenuto_esercizio, punteggio_massimo, 
                   data_approvazione, numero_usi
            FROM esercizi_approvati 
            WHERE materia = ? AND argomento = ? AND livello = ?
            ORDER BY 
                CASE WHEN numero_usi = 0 THEN 0 ELSE numero_usi END,
                data_approvazione DESC
            LIMIT ?
        ''', (materia, argomento, livello, count))
        
        risultati = cursor.fetchall()
        conn.close()
        
        esempi = []
        for titolo, contenuto, punteggio, data, usi in risultati:
            esempi.append({
                'titolo': titolo,
                'contenuto': contenuto,
                'punteggio_massimo': punteggio,
                'data_approvazione': data,
                'numero_usi': usi,
                'priority': 'high' if usi == 0 else 'medium'
            })
        
        return esempi
        
    except Exception as e:
        print(f"Errore ottenendo esempi raccomandati: {e}")
        return []

def update_usage_statistics(exercise_id: int, used_in_generation: bool = True):
    """
    Aggiorna le statistiche di utilizzo per un esercizio
    
    Args:
        exercise_id: ID dell'esercizio
        used_in_generation: Se è stato usato nella generazione
    """
    if not used_in_generation:
        return
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE esercizi_approvati 
            SET numero_usi = numero_usi + 1,
                ultimo_uso = ?
            WHERE id = ?
        ''', (datetime.now().isoformat(), exercise_id))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"Errore aggiornando statistiche utilizzo: {e}")

def get_training_quality_metrics() -> Dict[str, float]:
    """
    Calcola metriche di qualità del training
    
    Returns:
        Dizionario con metriche di qualità
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Diversità esempi per materia
        cursor.execute('''
            SELECT materia, COUNT(DISTINCT argomento) as diversity
            FROM esercizi_approvati 
            GROUP BY materia
        ''')
        diversity_results = cursor.fetchall()
        
        avg_diversity = sum(r[1] for r in diversity_results) / len(diversity_results) if diversity_results else 0
        
        # Tasso di utilizzo
        cursor.execute('''
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN numero_usi > 0 THEN 1 END) as used
            FROM esercizi_approvati
        ''')
        total, used = cursor.fetchone()
        
        usage_rate = (used / total * 100) if total > 0 else 0
        
        # Copertura argomenti
        cursor.execute("SELECT COUNT(DISTINCT argomento) FROM esercizi_approvati")
        topic_coverage = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'diversity_score': avg_diversity,
            'usage_rate': usage_rate,
            'topic_coverage': topic_coverage,
            'overall_quality': (avg_diversity + usage_rate + topic_coverage) / 3
        }
        
    except Exception as e:
        print(f"Errore metriche qualità: {e}")
        return {'diversity_score': 0, 'usage_rate': 0, 'topic_coverage': 0, 'overall_quality': 0}

# Funzione principale per integrazione
def integrate_ai_training():
    """
    Funzione principale per integrare il training AI nel sistema VerificAI
    
    Questa funzione deve essere chiamata nel sistema di generazione principale
    """
    def enhance_prompt_wrapper(base_prompt, materia, argomento, livello):
        """Wrapper per integrare con il sistema esistente"""
        return enhance_generation_prompt_with_approved(base_prompt, materia, argomento, livello)
    
    def get_training_info():
        """Ottiene informazioni sul training corrente"""
        return {
            'statistics': get_training_statistics(),
            'quality_metrics': get_training_quality_metrics(),
            'suggestions': suggest_improvements()
        }
    
    return {
        'enhance_prompt': enhance_prompt_wrapper,
        'get_info': get_training_info,
        'export_corpus': export_approved_corpus,
        'get_examples': get_recommended_examples
    }

# Esempio di utilizzo
if __name__ == "__main__":
    # Test delle funzioni
    print("🧪 Test Sistema Training AI")
    
    # Statistiche
    stats = get_training_statistics()
    print(f"📊 Statistiche: {stats}")
    
    # Metriche qualità
    quality = get_training_quality_metrics()
    print(f"📈 Metriche qualità: {quality}")
    
    # Suggerimenti
    suggestions = suggest_improvements()
    print(f"💡 Suggerimenti: {suggestions}")
    
    # Test arricchimento prompt
    base_prompt = "Genera 3 esercizi di Matematica - Trigonometria per Liceo"
    enhanced = enhance_generation_prompt_with_approved(base_prompt, "Matematica", "Trigonometria", "Liceo")
    print(f"✨ Prompt arricchito: {len(enhanced)} caratteri")
