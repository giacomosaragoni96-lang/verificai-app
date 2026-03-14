# Script per rimuovere i commenti HTML dal file main.py

import re

def remove_html_comments(file_path):
    """Rimuove tutti i commenti HTML dal file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Rimuove i commenti HTML (sia multilinea che singola linea)
    content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("Commenti HTML rimossi con successo!")

if __name__ == "__main__":
    remove_html_comments(r"c:\Users\gobli\Desktop\verificai\main.py")
