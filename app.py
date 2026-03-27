#!/usr/bin/env python3
"""
VerificAI - Entry point per Streamlit Cloud
"""

import sys
import os

# Aggiungi la directory corrente al Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importa e avvia l'app principale
if __name__ == "__main__":
    import main
    # Il main.py si occuperà di tutto
