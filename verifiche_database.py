#!/usr/bin/env python3
"""
Database Verifiche - Sistema di archiviazione e valutazione
"""

import json
import os
from datetime import datetime
import streamlit as st

class VerificheDatabase:
    """Database per archiviare e gestire le verifiche generate"""
    
    def __init__(self, db_file="verifiche_database.json"):
        self.db_file = db_file
        self.db = self._load_database()
    
    def _load_database(self):
        """Carica database da file"""
        if os.path.exists(self.db_file):
            try:
                with open(self.db_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {"verifiche": [], "stats": {}}
        else:
            return {"verifiche": [], "stats": {}}
    
    def _save_database(self):
        """Salva database su file"""
        with open(self.db_file, 'w', encoding='utf-8') as f:
            json.dump(self.db, f, indent=2, ensure_ascii=False)
    
    def add_verifica(self, verifica_data):
        """Aggiunge una nuova verifica al database"""
        
        # Crea ID univoco
        verifica_id = f"V{len(self.db['verifiche']) + 1:04d}"
        
        # Prepara dati verifica
        nuova_verifica = {
            "id": verifica_id,
            "timestamp": datetime.now().isoformat(),
            "scenario": verifica_data["scenario"],
            "output": verifica_data["output"],
            "analisi": verifica_data["analisi"],
            "pdf_result": verifica_data.get("pdf_result", {}),
            "punteggio_finale": verifica_data["punteggio_finale"],
            "status": "pending",  # pending, approved, rejected
            "user_feedback": None,
            "user_rating": None,  # 1-5 stelle
            "tags": [],
            "quality_score": None,  # calcolato dopo feedback utente
            "archived": False
        }
        
        self.db["verifiche"].append(nuova_verifica)
        self._save_database()
        
        return verifica_id
    
    def update_verifica_status(self, verifica_id, status, user_feedback=None, user_rating=None, tags=None):
        """Aggiorna status di una verifica"""
        
        for verifica in self.db["verifiche"]:
            if verifica["id"] == verifica_id:
                verifica["status"] = status
                verifica["user_feedback"] = user_feedback
                verifica["user_rating"] = user_rating
                if tags:
                    verifica["tags"] = tags
                
                # Calcola quality score basato su rating utente e analisi
                if user_rating is not None:
                    analisi_score = verifica["punteggio_finale"] / 100  # 0-1
                    user_score = user_rating / 5  # 0-1
                    verifica["quality_score"] = (analisi_score * 0.7 + user_score * 0.3) * 100
                
                self._save_database()
                return True
        
        return False
    
    def get_verifiche(self, status=None, materia=None, archived=False):
        """Ottiene verifiche con filtri"""
        
        verifiche = self.db["verifiche"]
        
        # Filtra per archived
        if not archived:
            verifiche = [v for v in verifiche if not v["archived"]]
        
        # Filtra per status
        if status:
            verifiche = [v for v in verifiche if v.get("status") == status]
        
        # Filtra per materia
        if materia and materia != "Tutte":
            verifiche = [v for v in verifiche if v["scenario"]["materia"] == materia]
        
        return sorted(verifiche, key=lambda x: x["timestamp"], reverse=True)
    
    def get_stats(self):
        """Ottiene statistiche del database"""
        
        verifiche = self.db["verifiche"]
        
        stats = {
            "totali": len(verifiche),
            "pending": len([v for v in verifiche if v.get("status") == "pending"]),
            "approved": len([v for v in verifiche if v.get("status") == "approved"]),
            "rejected": len([v for v in verifiche if v.get("status") == "rejected"]),
            "media_voti": sum([v["punteggio_finale"] for v in verifiche]) / len(verifiche) if verifiche else 0
        }
        
        return stats

def render_database_manager():
    """Renderizza interfaccia gestione database"""
    
    st.markdown("""
    <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                padding: 2rem; border-radius: 10px; margin-bottom: 2rem;'>
        <h1 style='color: white; margin: 0;'>🗄️ Database Verifiche</h1>
        <p style='color: white; margin: 0.5rem 0 0 0;'>Archivia e valuta le verifiche generate</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Inizializza database
    if 'verifiche_db' not in st.session_state:
        st.session_state.verifiche_db = VerificheDatabase()
    
    db = st.session_state.verifiche_db
    
    # Stats dashboard
    stats = db.get_stats()
    
    st.markdown("## 📊 Statistiche Database")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📝 Totali", stats["totali"])
    with col2:
        st.metric("✅ Approvate", stats["approved"])
    with col3:
        st.metric("⏳ In attesa", stats["pending"])
    with col4:
        st.metric("❌ Rifiutate", stats["rejected"])
    
    # Tabella verifiche
    st.markdown("## 📋 Verifiche da Valutare")
    
    verifiche = db.get_verifiche(status="pending")
    
    if not verifiche:
        st.info("📂 Nessuna verifica in attesa di valutazione")
        return
    
    # Mostra verifiche pending
    for i, verifica in enumerate(verifiche[:10]):  # Prime 10 per non sovraccaricare
        with st.expander(f"⏳ {verifica['id']}: {verifica['scenario']['materia']} - {verifica['scenario']['argomento']} - Voto: {verifica['punteggio_finale']}/100"):
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**📋 Info Verifica:**")
                st.write(f"- **ID:** {verifica['id']}")
                st.write(f"- **Materia:** {verifica['scenario']['materia']}")
                st.write(f"- **Livello:** {verifica['scenario']['livello']}")
                st.write(f"- **Argomento:** {verifica['scenario']['argomento']}")
                st.write(f"- **Esercizi:** {verifica['scenario']['num_esercizi']}")
                st.write(f"- **Punti:** {verifica['scenario']['punti_totali']}")
            
            with col2:
                st.markdown("**🔍 Analisi Automatica:**")
                analisi = verifica["analisi"]
                st.write(f"- Esercizi: {analisi['esercizi']['trovati']}/{analisi['esercizi']['attesi']} {'✅' if analisi['esercizi']['corretti'] else '❌'}")
                st.write(f"- Punteggi: {analisi['punteggi']['trovati']}/{analisi['punteggi']['attesi']} {'✅' if analisi['punteggi']['corretti'] else '❌'}")
                st.write(f"- Struttura: {analisi['struttura']['elementi_trovati']} elementi {'✅' if analisi['struttura']['adeguata'] else '❌'}")
                st.write(f"- Tabella: {'Presente' if analisi['tabella']['presente'] else 'Assente'}")
                st.write(f"- Griglia: {'Presente' if analisi['griglia']['presente'] else 'Assente'}")
            
            # Azioni utente
            st.markdown("**🎯 Valutazione Finale:**")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button(f"✅ Approva {verifica['id']}", key=f"approve_{verifica['id']}"):
                    db.update_verifica_status(verifica['id'], "approved")
                    st.success("✅ Verifica approvata!")
                    st.rerun()
            
            with col2:
                if st.button(f"❌ Rifiuta {verifica['id']}", key=f"reject_{verifica['id']}"):
                    db.update_verifica_status(verifica['id'], "rejected")
                    st.error("❌ Verifica rifiutata!")
                    st.rerun()
            
            with col3:
                if st.button(f"👀 Anteprima {verifica['id']}", key=f"preview_{verifica['id']}"):
                    st.code(verifica['output'][:300] + "..." if len(verifica['output']) > 300 else verifica['output'], language='latex')
            
            st.markdown("---")
    
    if len(verifiche) > 10:
        st.info(f"📄 Mostrate prime 10 di {len(verifiche)} verifiche in attesa")

# Funzione per integrare nel test 30 verifiche
def integra_database_in_test(test_results):
    """Integra i risultati del test nel database"""
    
    db = VerificheDatabase()
    aggiunte = 0
    
    for risultato in test_results:
        try:
            # Prepara dati per database
            verifica_data = {
                "scenario": risultato["scenario"],
                "output": risultato["generazione"]["output"],
                "analisi": risultato["analisi"],
                "pdf_result": risultato.get("pdf", {}),
                "punteggio_finale": risultato["punteggio_finale"]
            }
            
            # Aggiungi al database
            db.add_verifica(verifica_data)
            aggiunte += 1
            
        except Exception as e:
            print(f"Errore aggiunta verifica {risultato.get('id', 'unknown')}: {e}")
    
    return aggiunte
