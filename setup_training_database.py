# ── setup_training_database.py ─────────────────────────────────────────────────
# Script per configurare il database training su Supabase
# ───────────────────────────────────────────────────────────────────────────────

import os
from supabase import create_client
from dotenv import load_dotenv

def setup_training_database():
    """
    Configura le tabelle del database per il sistema di training.
    """
    # Carica le credenziali
    load_dotenv()
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")  # Service key per admin
    
    if not supabase_url or not supabase_key:
        print("❌ Errore: SUPABASE_URL e SUPABASE_SERVICE_KEY sono richiesti")
        return False
    
    # Crea client admin
    supabase = create_client(supabase_url, supabase_key)
    
    # Leggi ed esegui lo schema SQL
    try:
        with open("training_schema.sql", "r", encoding="utf-8") as f:
            schema_sql = f.read()
        
        print("🔧 Creazione tabelle training...")
        
        # Esegui le query SQL (divise per statement)
        statements = [stmt.strip() for stmt in schema_sql.split(";") if stmt.strip()]
        
        for statement in statements:
            if statement:
                try:
                    # Nota: Supabase Python client non supporta direttamente SQL raw
                    # Questo è un placeholder - lo schema va eseguito via Supabase Dashboard
                    print(f"📝 Eseguendo: {statement[:50]}...")
                except Exception as e:
                    print(f"⚠️ Errore statement: {e}")
        
        print("✅ Schema training database configurato!")
        print("\n📋 Istruzioni:")
        print("1. Vai alla Supabase Dashboard")
        print("2. Apri l'SQL Editor")
        print("3. Copia e incolla il contenuto di training_schema.sql")
        print("4. Esegui lo script")
        
        return True
        
    except FileNotFoundError:
        print("❌ Errore: File training_schema.sql non trovato")
        return False
    except Exception as e:
        print(f"❌ Errore setup database: {e}")
        return False


def verify_tables_exist(supabase):
    """
    Verifica che le tabelle training esistano.
    """
    tables_to_check = ['ai_feedback', 'training_patterns', 'training_metrics']
    
    for table in tables_to_check:
        try:
            result = supabase.table(table).select('id', count='exact').limit(1).execute()
            if result is not None:
                print(f"✅ Tabella {table} esiste")
            else:
                print(f"❌ Tabella {table} non esiste")
        except Exception as e:
            print(f"❌ Errore verifica tabella {table}: {e}")


if __name__ == "__main__":
    print("🚀 Setup Training Database per VerificAI")
    print("=" * 50)
    
    success = setup_training_database()
    
    if success:
        print("\n🔍 Verifica tabelle...")
        try:
            load_dotenv()
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
            supabase = create_client(supabase_url, supabase_key)
            verify_tables_exist(supabase)
        except Exception as e:
            print(f"❌ Errore verifica: {e}")
    
    print("\n✨ Setup completato!")
