# ── prompt_enhancer.py ─────────────────────────────────────────────────────────
# Sistema di enhancement automatico dei prompt con training data
# ───────────────────────────────────────────────────────────────────────────────

import logging
import json
from typing import Dict, List, Optional
from supabase import Client

logger = logging.getLogger("verificai.prompt_enhancer")


def enhance_prompt_with_training(base_prompt: str, materia: str, livello: str, 
                               supabase_admin: Client) -> str:
    """
    Integra esempi e pattern di training nel prompt base.
    """
    try:
        enhanced_prompt = base_prompt
        
        # Recupera esempi positivi rilevanti
        positive_examples = get_relevant_training_examples(
            supabase_admin, 'positive', materia, livello, limit=2
        )
        
        # Recupera pattern negativi da evitare
        negative_patterns = get_relevant_training_patterns(
            supabase_admin, 'negative', materia, livello
        )
        
        # Aggiungi esempi positivi se disponibili
        if positive_examples:
            examples_section = format_positive_examples(positive_examples)
            enhanced_prompt += f"\n\n{examples_section}"
        
        # Aggiungi pattern negativi se disponibili
        if negative_patterns:
            patterns_section = format_negative_patterns(negative_patterns)
            enhanced_prompt += f"\n\n{patterns_section}"
        
        # Aggiungi istruzioni di qualità basate su training
        quality_instructions = generate_quality_instructions(materia, livello, supabase_admin)
        if quality_instructions:
            enhanced_prompt += f"\n\n{quality_instructions}"
        
        return enhanced_prompt
        
    except Exception as e:
        logger.error(f"Errore enhancement prompt: {e}")
        return base_prompt


def get_relevant_training_examples(supabase_admin: Client, pattern_type: str,
                                  materia: str, livello: str, limit: int = 3) -> List[str]:
    """
    Recupera esempi di training rilevanti.
    """
    try:
        # Prima cerca esempi specifici materia/livello
        result = supabase_admin.table('ai_feedback')\
            .select('verifica_content')\
            .eq('rating', 'good' if pattern_type == 'positive' else 'bad')\
            .eq('materia', materia)\
            .eq('livello', livello)\
            .order('created_at', desc=True)\
            .limit(limit)\
            .execute()
        
        examples = [item['verifica_content'] for item in result.data if item.get('verifica_content')]
        
        # Se non ci sono abbastanza esempi specifici, cerca per materia sola
        if len(examples) < limit:
            additional_limit = limit - len(examples)
            result_materia = supabase_admin.table('ai_feedback')\
                .select('verifica_content')\
                .eq('rating', 'good' if pattern_type == 'positive' else 'bad')\
                .eq('materia', materia)\
                .neq('livello', livello)\
                .order('created_at', desc=True)\
                .limit(additional_limit)\
                .execute()
            
            additional_examples = [item['verifica_content'] for item in result_materia.data 
                                if item.get('verifica_content')]
            examples.extend(additional_examples)
        
        return examples[:limit]
        
    except Exception as e:
        logger.error(f"Errore recupero esempi training: {e}")
        return []


def get_relevant_training_patterns(supabase_admin: Client, pattern_type: str,
                                 materia: str, livello: str) -> List[Dict]:
    """
    Recupera pattern di training rilevanti.
    """
    try:
        # Cerca pattern specifici materia/livello
        result = supabase_admin.table('training_patterns')\
            .select('*')\
            .eq('pattern_type', pattern_type)\
            .eq('materia', materia)\
            .eq('livello', livello)\
            .order('effectiveness_score', desc=True)\
            .limit(3)\
            .execute()
        
        patterns = result.data
        
        # Se non ci sono pattern specifici, cerca per materia sola
        if not patterns:
            result_materia = supabase_admin.table('training_patterns')\
                .select('*')\
                .eq('pattern_type', pattern_type)\
                .eq('materia', materia)\
                .order('effectiveness_score', desc=True)\
                .limit(3)\
                .execute()
            
            patterns = result_materia.data
        
        return patterns if patterns else []
        
    except Exception as e:
        logger.error(f"Errore recupero pattern training: {e}")
        return []


def format_positive_examples(examples: List[str]) -> str:
    """
    Formatta esempi positivi per inclusione nel prompt.
    """
    if not examples:
        return ""
    
    examples_text = "## ESEMPI DI RIFERIMENTO (Verifiche di alta qualità)\n\n"
    
    for i, example in enumerate(examples, 1):
        # Estrai solo i primi 1000 caratteri per evitare prompt troppo lunghi
        truncated_example = example[:1000] + "..." if len(example) > 1000 else example
        
        examples_text += f"### Esempio {i}:\n"
        examples_text += f"```\n{truncated_example}\n```\n\n"
    
    examples_text += "**Istruzione:** Usa questi esempi come riferimento per struttura, stile e qualità.\n"
    examples_text += "**Attenzione:** Non copiare letteralmente, ma ispirati alla struttura e approccio.\n"
    
    return examples_text


def format_negative_patterns(patterns: List[Dict]) -> str:
    """
    Formatta pattern negativi per inclusione nel prompt.
    """
    if not patterns:
        return ""
    
    patterns_text = "## SCHEMI DA EVITARE (Errori comuni)\n\n"
    
    for i, pattern in enumerate(patterns, 1):
        features = pattern.get('features', {})
        confidence = pattern.get('confidence', 0.0)
        
        patterns_text += f"### Pattern {i} (Confidenza: {confidence:.1%}):\n"
        
        for feature, value in features.items():
            if isinstance(value, bool) and value:
                patterns_text += f"- **Evita:** {feature.replace('_', ' ').title()}\n"
            elif isinstance(value, dict) and 'avg' in value:
                patterns_text += f"- **Attenzione:** {feature.replace('_', ' ').title()} (media: {value['avg']:.1f})\n"
            elif isinstance(value, list) and value:
                patterns_text += f"- **Limita:** {', '.join(value[:3])}\n"
        
        patterns_text += "\n"
    
    patterns_text += "**Istruzione:** Presta attenzione a evitare questi schemi che hanno ricevuto feedback negativo.\n"
    
    return patterns_text


def generate_quality_instructions(materia: str, livello: str, supabase_admin: Client) -> str:
    """
    Genera istruzioni di qualità basate su training data.
    """
    try:
        # Analizza feedback recenti per materia/livello
        from datetime import timedelta
        from training_data import analyze_exercise_features
        
        week_ago = (datetime.now().replace(tzinfo=None) - timedelta(days=7)).isoformat()
        
        result = supabase_admin.table('ai_feedback')\
            .select('features', 'rating')\
            .eq('materia', materia)\
            .eq('livello', livello)\
            .gte('created_at', week_ago)\
            .execute()
        
        if not result.data:
            return ""
        
        # Analizza features di esempi positivi vs negativi
        positive_features = []
        negative_features = []
        
        for item in result.data:
            features = item.get('features', {})
            rating = item.get('rating', '')
            
            if rating == 'good':
                positive_features.append(features)
            elif rating == 'bad':
                negative_features.append(features)
        
        # Genera istruzioni basate su analisi
        instructions = "## ISTRUZIONI DI QUALITÀ SPECIFICHE\n\n"
        
        if positive_features:
            # Calcola features medie degli esempi positivi
            avg_structure = sum(f.get('structure_score', 0) for f in positive_features) / len(positive_features)
            avg_quality = sum(f.get('content_quality', 0) for f in positive_features) / len(positive_features)
            avg_difficulty = sum(f.get('avg_difficulty', 0) for f in positive_features) / len(positive_features)
            
            instructions += f"**Target Qualità:**\n"
            instructions += f"- Struttura: {avg_structure:.1%}\n"
            instructions += f"- Contenuto: {avg_quality:.1%}\n"
            instructions += f"- Difficoltà target: {avg_difficulty:.1f}/5\n\n"
        
        if negative_features:
            # Identifica problemi comuni
            common_issues = []
            if sum(1 for f in negative_features if not f.get('has_punteggi', False)) > len(negative_features) * 0.5:
                common_issues.append("mancanza punteggi")
            if sum(1 for f in negative_features if f.get('structure_score', 0) < 0.5) > len(negative_features) * 0.5:
                common_issues.append("struttura debole")
            if sum(1 for f in negative_features if f.get('content_quality', 0) < 0.5) > len(negative_features) * 0.5:
                common_issues.append("contenuto scarso")
            
            if common_issues:
                instructions += "**Attenzione a:**\n"
                for issue in common_issues:
                    instructions += f"- {issue.title()}\n"
                instructions += "\n"
        
        instructions += "**Obiettivo:** Genera verifiche che ricevono feedback positivo.\n"
        
        return instructions
        
    except Exception as e:
        logger.error(f"Errore generazione quality instructions: {e}")
        return ""


def track_prompt_effectiveness(supabase_admin: Client, prompt_id: str, 
                             feedback_rating: str) -> None:
    """
    Traccia l'efficacia dei prompt enhancement.
    """
    try:
        # Aggiorna usage count dei pattern utilizzati
        # (implementazione futura per A/B testing)
        pass
    except Exception as e:
        logger.error(f"Errore tracking effectiveness: {e}")


def should_use_training_enhancement(supabase_admin: Client, materia: str, 
                                   livello: str) -> bool:
    """
    Determina se usare enhancement basato su training data availability.
    """
    try:
        # Controlla se ci sono abbastanza dati di training
        good_count = supabase_admin.table('ai_feedback')\
            .select('id', count='exact')\
            .eq('rating', 'good')\
            .eq('materia', materia)\
            .eq('livello', livello)\
            .execute()
        
        good_count_num = good_count.count if good_count.count else 0
        
        # Usa enhancement solo se ci sono almeno 5 esempi positivi
        return good_count_num >= 5
        
    except Exception as e:
        logger.error(f"Errore determinazione enhancement: {e}")
        return False


def get_training_stats_summary(supabase_admin: Client) -> Dict:
    """
    Recupera riassunto statistiche training.
    """
    try:
        # Feedback totali
        total_feedback = supabase_admin.table('ai_feedback')\
            .select('id', count='exact')\
            .execute()
        
        # Pattern totali
        total_patterns = supabase_admin.table('training_patterns')\
            .select('id', count='exact')\
            .execute()
        
        # Feedback positivi
        good_feedback = supabase_admin.table('ai_feedback')\
            .select('id', count='exact')\
            .eq('rating', 'good')\
            .execute()
        
        return {
            'total_feedback': total_feedback.count or 0,
            'total_patterns': total_patterns.count or 0,
            'good_feedback': good_feedback.count or 0,
            'training_readiness': (good_feedback.count or 0) >= 50
        }
        
    except Exception as e:
        logger.error(f"Errore stats summary: {e}")
        return {
            'total_feedback': 0,
            'total_patterns': 0,
            'good_feedback': 0,
            'training_readiness': False
        }
