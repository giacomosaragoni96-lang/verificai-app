# Script per correggere i tag HTML non chiusi nel file main.py

import re

def fix_unclosed_html_tags(file_path):
    """Corregge i tag HTML non chiusi nel file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Cerca e corregge i tag div non chiusi nelle f-string
    lines = content.split('\n')
    fixed_lines = []
    
    for i, line in enumerate(lines):
        # Se è una riga che inizia con <div e non ha chiusura
        if '<div style=' in line and not line.strip().endswith('</div>'):
            # Aggiungi la chiusura del div
            if 'st.markdown(' in line and "''', unsafe_allow_html=True)" in line:
                # È la fine di una f-string, aggiungi i div mancanti prima
                line = line.replace("''', unsafe_allow_html=True)", "                        </div>\n                    </div>\n                </div>\n            ''', unsafe_allow_html=True)")
        fixed_lines.append(line)
    
    fixed_content = '\n'.join(fixed_lines)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(fixed_content)
    
    print("Tag HTML corretti con successo!")

if __name__ == "__main__":
    fix_unclosed_html_tags(r"c:\Users\gobli\Desktop\verificai\main.py")
