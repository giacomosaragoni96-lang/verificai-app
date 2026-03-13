# ── training_data.py ─────────────────────────────────────────────────────────────
# Sistema di raccolta dati silenzioso per training AI
# ───────────────────────────────────────────────────────────────────────────────

import re
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from supabase import Client

logger = logging.getLogger("verificai.training")


def analyze_exercise_features(latex_content: str) -> Dict[str, Any]:
    """
    Estrae caratteristiche automatiche da una verifica per analisi.
    Analisi strutturale del contenuto LaTeX.
    """
    features = {
        'num_esercizi': 0,
        'has_punteggi': False,
        'has_grafici': False,
        'has_tabelle': False,
        'avg_difficulty': 0.0,
        'exercise_types': [],
        'structure_score': 0.0,
        'content_quality': 0.0,
        'materia_indicators': [],
        'livello_complexity': 0.0
    }
    
    try:
        # Conta esercizi (subsection)
        subsections = re.findall(r'\\subsection\*\{([^}]+)\}', latex_content)
        features['num_esercizi'] = len(subsections)
        
        # Controlla presenza punteggi
        pt_patterns = [
            r'\(\s*\d+(?:[.,]\d+)?\s*pt\s*\)',
            r'\[\s*\d+(?:[.,]\d+)?\s*pt\s*\]',
            r'\d+(?:[.,]\d+)?\s*pt',
            r'punti?:\s*\d+',
            r'valore:\s*\d+'
        ]
        features['has_punteggi'] = any(re.search(pattern, latex_content, re.IGNORECASE) for pattern in pt_patterns)
        
        # Controlla presenza grafici
        features['has_grafici'] = bool(re.search(r'\\begin\{tikzpicture\}', latex_content))
        
        # Controlla presenza tabelle
        features['has_tabelle'] = bool(re.search(r'\\begin\{tabular\}', latex_content))
        
        # Analisi tipi esercizi
        exercise_types = []
        if re.search(r'\\begin\{tikzpicture\}', latex_content):
            exercise_types.append('grafico')
        if re.search(r'\\begin\{tabular\}', latex_content):
            exercise_types.append('tabella')
        if re.search(r'calcola|risolvi|determina', latex_content, re.IGNORECASE):
            exercise_types.append('calcolo')
        if re.search(r'dimostra|spiega|giustifica', latex_content, re.IGNORECASE):
            exercise_types.append('teoria')
        if re.search(r'disegna|rappresenta|traccia', latex_content, re.IGNORECASE):
            exercise_types.append('disegno')
        features['exercise_types'] = list(set(exercise_types))
        
        # Stima difficoltà basata su indicatori
        difficulty_indicators = 0
        if features['has_grafici']:
            difficulty_indicators += 1
        if features['has_tabelle']:
            difficulty_indicators += 1
        if 'teoria' in exercise_types:
            difficulty_indicators += 2
        if features['num_esercizi'] > 5:
            difficulty_indicators += 1
        
        features['avg_difficulty'] = min(5.0, difficulty_indicators)
        
        # Score di struttura (0-1)
        structure_score = 0.0
        if features['num_esercizi'] > 0:
            structure_score += 0.2
        if features['has_punteggi']:
            structure_score += 0.3
        if len(subsections) == features['num_esercizi']:
            structure_score += 0.3
        if re.search(r'\\item\s*\[', latex_content):
            structure_score += 0.2
        features['structure_score'] = min(1.0, structure_score)
        
        # Score qualità contenuto (0-1)
        quality_score = 0.0
        if len(latex_content) > 500:
            quality_score += 0.2
        if features['num_esercizi'] >= 3:
            quality_score += 0.2
        if features['has_punteggi']:
            quality_score += 0.3
        if not re.search(r'\\item\s*\[\s*\]', latex_content):  # No item vuoti
            quality_score += 0.3
        features['content_quality'] = min(1.0, quality_score)
        
        # Indicatori materia (basati su keywords)
        content_lower = latex_content.lower()
        materia_keywords = {
            'matematica': ['equazione', 'funzione', 'deriva', 'integra', 'calcola', 'risolvi', 'grafico'],
            'fisica': ['forza', 'velocità', 'accelerazione', 'energia', 'lavoro', 'potenza'],
            'chimica': ['reazione', 'molecola', 'atomo', 'legame', 'concentrazione'],
            'italiano': ['testo', 'autore', 'opera', 'analisi', 'commento', 'grammatica'],
            'storia': ['anno', 'secolo', 'periodo', 'evento', 'guerra', 'trattato'],
            'geografia': ['paese', 'città', 'continente', 'fiume', 'montagna', 'clima']
        }
        
        for materia, keywords in materia_keywords.items():
            if sum(1 for kw in keywords if kw in content_lower) >= 2:
                features['materia_indicators'].append(materia)
        
        # Complessità livello (basata su vocabolario e struttura)
        complexity_indicators = 0
        if len(re.findall(r'\\[a-zA-Z]+\{[^}]+\}', latex_content)) > 10:  # Molti comandi LaTeX
            complexity_indicators += 1
        if features['num_esercizi'] > 4:
            complexity_indicators += 1
        if features['avg_difficulty'] > 3:
            complexity_indicators += 1
        features['livello_complexity'] = min(5.0, complexity_indicators + 1)
        
    except Exception as e:
        logger.warning(f"Errore analisi features: {e}")
    
    return features


def save_feedback(supabase_admin: Client, user_id: str, verifica_content: str, 
                  rating: str, materia: str, livello: str) -> bool:
    """
    Salva feedback utente nel database training.
    """
    try:
        # Analizza features della verifica
        features = analyze_exercise_features(verifica_content)
        
        # Prepara record per database
        feedback_data = {
            'user_id': user_id,
            'verifica_content': verifica_content[:5000],  # Limita dimensione
            'materia': materia,
            'livello': livello,
            'rating': rating,  # 'good' o 'bad'
            'features': features,
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        # Salva in database
        result = supabase_admin.table('ai_feedback').insert(feedback_data).execute()
        
        if result.data:
            logger.info(f"Feedback salvato: user={user_id}, rating={rating}, materia={materia}")
            return True
        else:
            logger.error("Errore salvataggio feedback: nessun dato restituito")
            return False
            
    except Exception as e:
        logger.error(f"Errore salvataggio feedback: {e}")
        return False


def extract_positive_patterns(feedback_examples: List[Dict]) -> List[Dict]:
    """
    Estrae pattern positivi da esempi votati 'good'.
    """
    patterns = []
    
    try:
        # Analisi features comuni negli esempi positivi
        common_features = {}
        for example in feedback_examples:
            features = example.get('features', {})
            for key, value in features.items():
                if key not in common_features:
                    common_features[key] = []
                common_features[key].append(value)
        
        # Identifica pattern ricorrenti
        positive_patterns = {}
        for feature, values in common_features.items():
            if len(values) >= 3:  # Almeno 3 occorrenze
                if isinstance(values[0], bool):
                    positive_patterns[feature] = sum(values) / len(values) > 0.7
                elif isinstance(values[0], (int, float)):
                    positive_patterns[feature] = sum(values) / len(values)
                elif isinstance(values[0], list):
                    # Per liste, trova elementi comuni
                    all_items = [item for sublist in values for item in sublist]
                    from collections import Counter
                    common_items = [item for item, count in Counter(all_items).items() if count >= len(values) * 0.5]
                    positive_patterns[feature] = common_items
        
        if positive_patterns:
            patterns.append({
                'pattern_type': 'positive',
                'features': positive_patterns,
                'confidence': len(feedback_examples) / 10,  # Confidence basata su numero esempi
                'materia': feedback_examples[0].get('materia'),
                'livello': feedback_examples[0].get('livello')
            })
            
    except Exception as e:
        logger.warning(f"Errore estrazione pattern positivi: {e}")
    
    return patterns


def extract_negative_patterns(feedback_examples: List[Dict]) -> List[Dict]:
    """
    Estrae pattern negativi da esempi votati 'bad'.
    """
    patterns = []
    
    try:
        # Analisi features comuni negli esempi negativi
        common_features = {}
        for example in feedback_examples:
            features = example.get('features', {})
            for key, value in features.items():
                if key not in common_features:
                    common_features[key] = []
                common_features[key].append(value)
        
        # Identifica pattern problematici
        negative_patterns = {}
        for feature, values in common_features.items():
            if len(values) >= 3:  # Almeno 3 occorrenze
                if isinstance(values[0], bool):
                    # Cosa evitare (caratteristiche presenti in >70% esempi negativi)
                    negative_patterns[feature] = sum(values) / len(values) > 0.7
                elif isinstance(values[0], (int, float)):
                    # Range problematico
                    negative_patterns[feature] = {
                        'avg': sum(values) / len(values),
                        'min': min(values),
                        'max': max(values)
                    }
        
        if negative_patterns:
            patterns.append({
                'pattern_type': 'negative',
                'features': negative_patterns,
                'confidence': len(feedback_examples) / 10,
                'materia': feedback_examples[0].get('materia'),
                'livello': feedback_examples[0].get('livello')
            })
            
    except Exception as e:
        logger.warning(f"Errore estrazione pattern negativi: {e}")
    
    return patterns


def store_training_patterns(supabase_admin: Client, patterns: List[Dict]) -> bool:
    """
    Salva pattern di training nel database.
    """
    try:
        for pattern in patterns:
            pattern_data = {
                'pattern_type': pattern['pattern_type'],
                'features': pattern['features'],
                'confidence': pattern['confidence'],
                'materia': pattern.get('materia'),
                'livello': pattern.get('livello'),
                'usage_count': 0,
                'effectiveness_score': 0.0,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            result = supabase_admin.table('training_patterns').insert(pattern_data).execute()
            
        logger.info(f"Salvati {len(patterns)} pattern di training")
        return True
        
    except Exception as e:
        logger.error(f"Errore salvataggio pattern: {e}")
        return False


def get_relevant_examples(supabase_admin: Client, pattern_type: str, 
                         materia: str, livello: str, limit: int = 3) -> List[str]:
    """
    Recupera esempi rilevanti per enhancement prompt.
    """
    try:
        result = supabase_admin.table('ai_feedback')\
            .select('verifica_content')\
            .eq('rating', 'good' if pattern_type == 'positive' else 'bad')\
            .eq('materia', materia)\
            .eq('livello', livello)\
            .order('created_at', desc=True)\
            .limit(limit)\
            .execute()
        
        return [item['verifica_content'] for item in result.data if item.get('verifica_content')]
        
    except Exception as e:
        logger.error(f"Errore recupero esempi: {e}")
        return []


def get_relevant_patterns(supabase_admin: Client, pattern_type: str,
                          materia: str, livello: str) -> List[Dict]:
    """
    Recupera pattern rilevanti per enhancement prompt.
    """
    try:
        result = supabase_admin.table('training_patterns')\
            .select('*')\
            .eq('pattern_type', pattern_type)\
            .eq('materia', materia)\
            .eq('livello', livello)\
            .order('effectiveness_score', desc=True)\
            .limit(5)\
            .execute()
        
        return result.data
        
    except Exception as e:
        logger.error(f"Errore recupero pattern: {e}")
        return []


def update_training_patterns(supabase_admin: Client) -> bool:
    """
    Aggiorna pattern di training basati su feedback recenti.
    """
    try:
        # Recupera feedback recenti (ultimi 7 giorni)
        from datetime import timedelta
        week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        
        # Feedback positivi
        good_result = supabase_admin.table('ai_feedback')\
            .select('*')\
            .eq('rating', 'good')\
            .gte('created_at', week_ago)\
            .execute()
        
        # Feedback negativi
        bad_result = supabase_admin.table('ai_feedback')\
            .select('*')\
            .eq('rating', 'bad')\
            .gte('created_at', week_ago)\
            .execute()
        
        # Estrai e salva pattern
        all_patterns = []
        
        if good_result.data:
            positive_patterns = extract_positive_patterns(good_result.data)
            all_patterns.extend(positive_patterns)
        
        if bad_result.data:
            negative_patterns = extract_negative_patterns(bad_result.data)
            all_patterns.extend(negative_patterns)
        
        if all_patterns:
            store_training_patterns(supabase_admin, all_patterns)
            logger.info(f"Aggiornati {len(all_patterns)} pattern di training")
        
        return True
        
    except Exception as e:
        logger.error(f"Errore aggiornamento pattern: {e}")
        return False
