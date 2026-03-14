#!/usr/bin/env python3
"""
Crea PDF completo della verifica che passa al 100%
"""

import os
import sys
import subprocess
from datetime import datetime

# Setup
PROJECT_ROOT = os.environ.get("VERIFICAI_ROOT", "C:\\Users\\gobli\\Desktop\\verificai")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

sys.path.insert(0, os.path.dirname(__file__))

def create_pdf_from_test():
    """Crea PDF completo della verifica Matematica Tecnico"""
    
    print("🎯 CREAZIONE PDF VERIFICA MATEMATICA TECNICO")
    print("=" * 50)
    
    from providers.verificai_provider import call_api
    
    # Test case che passa al 100%
    test_case = {
        "prompt_type": "corpo", 
        "materia": "Matematica", 
        "argomento": "Equazioni di secondo grado",
        "livello": "Istituto Tecnico Tecnologico/Industriale", 
        "durata": "50 minuti",
        "num_esercizi": 4, 
        "punti_totali": 80, 
        "mostra_punteggi": True, 
        "e_mat": True
    }
    
    try:
        # Genera la verifica
        options = {"config": {"model_id": "gemini-2.5-flash-lite", "temperature": 0.7}}
        context = {"vars": test_case}
        
        result = call_api("test", options, context)
        latex_content = result.get("output", "")
        
        print("📝 LaTeX generato, creazione PDF...")
        
        # Crea documento LaTeX completo
        latex_document = f"""\\documentclass[12pt,a4paper]{{article}}
\\usepackage[utf8]{{inputenc}}
\\usepackage[italian]{{babel}}
\\usepackage{{amsmath,amssymb,amsfonts}}
\\usepackage{{geometry}}
\\usepackage{{fancyhdr}}
\\usepackage{{lastpage}}

\\geometry{{a4paper, margin=2.5cm}}
\\pagestyle{{fancy}}
\\fancyhf{{}}
\\rhead{{Verifica di Matematica}}
\\lhead{{Istituto Tecnico Tecnologico/Industriale}}
\\cfoot{{Pagina \\thepage/\\pagelast}}

\\begin{{document}}

\\begin{{center}}
\\textbf{{\\large VERIFICA DI MATEMATICA}}\\\\[0.5cm]
\\textbf{{Equazioni di secondo grado}}\\\\[0.3cm]
\\textbf{{Istituto Tecnico Tecnologico/Industriale}}\\\\[0.3cm]
\\textbf{{Durata: 50 minuti - Punteggio totale: 80 punti}}
\\end{{center}}

\\vspace{{0.5cm}}

{latex_content}

\\end{{document}}
"""
        
        # Salva file LaTeX
        latex_file = "verifica_matematica_tecnico.tex"
        with open(latex_file, 'w', encoding='utf-8') as f:
            f.write(latex_document)
        
        print(f"📄 File LaTeX salvato: {latex_file}")
        
        # Compila con pdflatex
        print("🔧 Compilazione con pdflatex...")
        
        try:
            # Prima compilazione
            result1 = subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", latex_file],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result1.returncode == 0:
                print("✅ Prima compilazione completata")
                
                # Seconda compilazione per riferimenti
                result2 = subprocess.run(
                    ["pdflatex", "-interaction=nonstopmode", latex_file],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result2.returncode == 0:
                    pdf_file = latex_file.replace('.tex', '.pdf')
                    if os.path.exists(pdf_file):
                        file_size = os.path.getsize(pdf_file)
                        print(f"🎉 PDF creato con successo!")
                        print(f"📄 File: {pdf_file}")
                        print(f"📏 Dimensione: {file_size} bytes")
                        
                        # Mostra anche il contenuto LaTeX
                        print("\n📝 CONTENUTO COMPLETO DELLA VERIFICA:")
                        print("=" * 60)
                        print(latex_content)
                        print("=" * 60)
                        
                        return pdf_file
                    else:
                        print("❌ File PDF non trovato dopo compilazione")
                else:
                    print("❌ Errore seconda compilazione:")
                    print(result2.stderr)
            else:
                print("❌ Errore prima compilazione:")
                print(result1.stderr)
                
        except subprocess.TimeoutExpired:
            print("❌ Timeout compilazione LaTeX")
        except FileNotFoundError:
            print("❌ pdflatex non trovato. Installa MiKTeX o TeX Live")
        except Exception as e:
            print(f"❌ Errore compilazione: {e}")
            
        return None
        
    except Exception as e:
        print(f"❌ Errore generazione: {e}")
        return None

if __name__ == "__main__":
    pdf_file = create_pdf_from_test()
    if pdf_file:
        print(f"\n🎯 Puoi aprire il PDF: {pdf_file}")
        print("📂 Oppure cercalo nella cartella corrente")
