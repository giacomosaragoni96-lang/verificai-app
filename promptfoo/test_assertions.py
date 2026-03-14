#!/usr/bin/env python3
"""
Test delle assertion JavaScript che abbiamo sostituito
"""

def test_javascript_assertions():
    """Test delle assertion JavaScript convertite in Python per validazione"""
    
    print("🧪 Test assertion JavaScript...")
    
    # Test 1: Livello medie appropriato
    def test_livello_medie(output):
        import re
        words = output.lower().split()
        complex_words = [w for w in words if len(w) > 8 or re.search(r'mente|zione|sione', w)]
        sentences = [s.strip() for s in output.split('.!?') if s.strip()]
        avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences) if sentences else 0
        return len(complex_words) <= 5 and avg_sentence_length <= 15
    
    output_medie = "Questo è un testo semplice per le scuole medie. Le frasi sono brevi e chiare."
    result1 = test_livello_medie(output_medie)
    print(f"✅ Livello medie: {result1}")
    
    # Test 2: Anti-spoiler grafici
    def test_anti_spoiler(output):
        import re
        has_drawing_prompt = re.search(r'disegnare|rappresentare.*grafic|tracciare.*grafic|disegna.*funzione', output, re.I)
        has_tikz = re.search(r'tikzpicture|pgfplots|\\begin\{tikz', output, re.I)
        return not (has_drawing_prompt and has_tikz)
    
    output_spoiler = "Disegna il grafico della funzione ma non includere codice TikZ."
    result2 = test_anti_spoiler(output_spoiler)
    print(f"✅ Anti-spoiler: {result2}")
    
    # Test 3: Varietà tipologie
    def test_varieta_tipologie(output):
        import re
        has_open = re.search(r'\?[^?]*$', output, re.M) or re.search(r'spiega|descrivi|motiva|analizza', output, re.I)
        has_multiple = re.search(r'\([^)]*\)[^)]*\([^)]*\)', output) or re.search(r'a\)|b\)|c\)|d\)', output, re.I)
        has_true_false = re.search(r'vero|falso|V|F\s*\)', output, re.I) or re.search(r'\\\(V\|F\\\)', output, re.I)
        has_completion = re.search(r'___|\.{3,}|completa|riempi', output, re.I)
        types = sum([bool(has_open), bool(has_multiple), bool(has_true_false), bool(has_completion)])
        return types >= 2
    
    output_varieta = "Rispondi alle domande: a) Qual è la capitale? b) Vero o falso: 2+2=4? Completa: 2+2=__"
    result3 = test_varieta_tipologie(output_varieta)
    print(f"✅ Varietà tipologie: {result3}")
    
    # Test 4: Livello professionale
    def test_livello_professionale(output):
        import re
        sentences = [s.strip() for s in output.split('.!?') if s.strip()]
        avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences) if sentences else 0
        complex_words = re.findall(r'\b[a-z]{10,}\b', output.lower())
        abstract_concepts = re.search(r'teorema|postulato|assioma|ipotesi|dimostrazione', output, re.I)
        return avg_sentence_length <= 18 and len(complex_words) <= 3 and not abstract_concepts
    
    output_prof = "Usa calcoli semplici e pratici. Risolvi problemi concreti della vita quotidiana."
    result4 = test_livello_professionale(output_prof)
    print(f"✅ Livello professionale: {result4}")
    
    # Test 5: Livello primaria
    def test_livello_primaria(output):
        import re
        sentences = [s.strip() for s in output.split('.!?') if s.strip()]
        avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences) if sentences else 0
        simple_words = re.search(r'mela|gatto|scuola|casa|gioco|numero|conta|aggiungi|togli', output, re.I)
        complex_terms = re.search(r'derivata|integrale|teorema|algoritmo|funzione', output, re.I)
        return avg_sentence_length <= 12 and simple_words and not complex_terms
    
    output_primaria = "Conta le mele nel cesto. Aggiungi e togli numeri semplici."
    result5 = test_livello_primaria(output_primaria)
    print(f"✅ Livello primaria: {result5}")
    
    # Test 6: Correzione problemi
    def test_correzione_problemi(output):
        import re
        has_impossible_correction = re.search(r'impossibile|nessuna soluzione|non.*soluzione|vuoto', output, re.I)
        has_score_correction = re.search(r'punteggi|somma|totale.*100|35.*100', output, re.I)
        return bool(has_impossible_correction or has_score_correction)
    
    output_correzione = "L'equazione x²+1=0 non ha soluzioni reali. I punteggi totali dovrebbero essere 100."
    result6 = test_correzione_problemi(output_correzione)
    print(f"✅ Correzione problemi: {result6}")
    
    # Riepilogo
    all_passed = all([result1, result2, result3, result4, result5, result6])
    print(f"\n🎉 Risultato finale: {'✅ Tutti PASS' if all_passed else '❌ Qualche FAIL'}")
    return all_passed

if __name__ == "__main__":
    test_javascript_assertions()
