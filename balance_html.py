# Script completo per bilanciare tutti i tag HTML nel file main.py

import re

def balance_html_tags(file_path):
    """Bilancia tutti i tag HTML nel file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Trova la funzione _render_le_tue_verifiche
    start = content.find('def _render_le_tue_verifiche():')
    end = content.find('\ndef ', start + 1)
    if end == -1:
        end = len(content)
    
    func_content = content[start:end]
    
    # Sostituisci tutte le f-string HTML nella funzione
    def fix_f_string(match):
        f_content = match.group(1)
        
        # Conta i div aperti e chiusi
        open_divs = len(re.findall(r'<div', f_content))
        close_divs = len(re.findall(r'</div>', f_content))
        
        # Calcola quanti div mancano
        missing_closes = open_divs - close_divs
        
        if missing_closes > 0:
            # Aggiungi i div mancanti alla fine
            closes_needed = '\n' + '                </div>\n' * missing_closes
            # Inserisci prima della chiusura della f-string
            f_content = f_content.rstrip() + closes_needed
        
        return f"st.markdown(f'''{f_content}''', unsafe_allow_html=True)"
    
    # Applica la correzione a tutte le f-string HTML
    fixed_func = re.sub(
        r'st\.markdown\(f\'\'\'(.*?)\'\'\', unsafe_allow_html=True\)',
        fix_f_string,
        func_content,
        flags=re.DOTALL
    )
    
    # Sostituisci la funzione nel contenuto originale
    new_content = content[:start] + fixed_func + content[end:]
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("Tag HTML bilanciati con successo!")

if __name__ == "__main__":
    balance_html_tags(r"c:\Users\gobli\Desktop\verificai\main.py")
