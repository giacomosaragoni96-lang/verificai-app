# Fix per il problema del codice HTML visualizzato come testo grezzo

# Il problema è che i tag HTML nel file main.py non sono chiusi correttamente
# Alle righe 2296-2297 manca la chiusura dei tag div

# Codice corretto da sostituire:
"""
                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem;">
                        </div>
                    </div>
                </div>
            ''', unsafe_allow_html=True)
"""

# Invece del codice attuale che è:
"""
                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem;">
            ''', unsafe_allow_html=True)
"""

# Manca la chiusura dei tag div e questo causa la visualizzazione del codice HTML come testo grezzo
