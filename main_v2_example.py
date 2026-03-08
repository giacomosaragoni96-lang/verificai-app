# ── main_v2_example.py — VerificAI Professional UX Integration Example ─────
# Esempio di come integrare il nuovo design system professionale
# Questo file mostra l'applicazione pratica dei nuovi componenti
# ───────────────────────────────────────────────────────────────────────────────

import streamlit as st
import time
from styles_v2 import get_professional_css
from layout_components import (
    render_professional_header,
    render_content_section,
    render_form_section,
    render_progress_steps,
    render_action_buttons,
    render_info_card,
    render_loading_section
)

# ── CONFIGURAZIONE PROFESSIONALE ───────────────────────────────────────────────
st.set_page_config(
    page_title="VerificAI - Piattaforma Professionale per Verifiche Scolastiche",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Applica CSS professionale
st.markdown(get_professional_css({}), unsafe_allow_html=True)

# ── STAGE DEFINITIONS ───────────────────────────────────────────────────────────
STAGE_INPUT = "INPUT"
STAGE_REVIEW = "REVIEW" 
STAGE_FINAL = "FINAL"

# ── INIZIALIZZAZIONE SESSIONE ───────────────────────────────────────────────────
if "current_stage" not in st.session_state:
    st.session_state.current_stage = STAGE_INPUT

if "verification_data" not in st.session_state:
    st.session_state.verification_data = {}

# ── HEADER PROFESSIONALE ─────────────────────────────────────────────────────────
stage_steps = [
    {"name": STAGE_INPUT, "label": "Configurazione", "status": "active"},
    {"name": STAGE_REVIEW, "label": "Revisione", "status": "pending"},
    {"name": STAGE_FINAL, "label": "Download", "status": "pending"}
]

render_professional_header(
    title="VerificAI",
    subtitle="Piattaforma professionale per la creazione di verifiche scolastiche personalizzate",
    stage=st.session_state.current_stage,
    stage_steps=stage_steps
)

# ── MAIN CONTENT ───────────────────────────────────────────────────────────────
if st.session_state.current_stage == STAGE_INPUT:
    
    # Progress indicators
    render_progress_steps(
        current_step=1,
        total_steps=3,
        step_labels=["Configurazione", "Revisione", "Download"]
    )
    
    # Form principale
    form_fields = {
        "materia": {
            "type": "select",
            "label": "Materia",
            "options": ["Matematica", "Italiano", "Fisica", "Chimica", "Storia", "Geografia"],
            "required": True,
            "help": "Seleziona la materia della verifica"
        },
        "argomento": {
            "type": "text",
            "label": "Argomento specifico",
            "required": True,
            "help": "Specifica l'argomento trattato (es. 'Equazioni di secondo grado')"
        },
        "livello": {
            "type": "select",
            "label": "Livello scolastico",
            "options": ["Scuola Secondaria di Primo Grado", "Scuola Secondaria di Secondo Grado"],
            "required": True
        },
        "num_esercizi": {
            "type": "number",
            "label": "Numero esercizi",
            "default": 5,
            "required": True,
            "help": "Numero di esercizi da includere nella verifica"
        },
        "tipologia": {
            "type": "multiselect",
            "label": "Tipologia esercizi",
            "options": ["Scelta multipla", "Vero/Falso", "Risposta aperta", "Problemi", "Grafici"],
            "default": ["Scelta multipla", "Vero/Falso"],
            "help": "Seleziona le tipologie di esercizi desiderate"
        },
        "istruzioni": {
            "type": "textarea",
            "label": "Istruzioni aggiuntive (opzionale)",
            "help": "Aggiungi istruzioni specifiche per la generazione",
            "default": ""
        }
    }
    
    submitted = render_form_section(
        title="Configurazione Verifica",
        fields=form_fields,
        submit_text="🚀 Genera Verifica",
        submit_disabled=False
    )
    
    if submitted:
        # Simulazione generazione
        render_loading_section("Sto generando la verifica personalizzata...")
        time.sleep(2)
        
        # Aggiorna session state
        st.session_state.current_stage = STAGE_REVIEW
        st.session_state.verification_data = {
            "materia": st.session_state.materia,
            "argomento": st.session_state.argomento,
            "livello": st.session_state.livello,
            "num_esercizi": st.session_state.num_esercizi,
            "tipologia": st.session_state.tipologia
        }
        st.rerun()

elif st.session_state.current_stage == STAGE_REVIEW:
    
    # Progress indicators
    render_progress_steps(
        current_step=2,
        total_steps=3,
        step_labels=["Configurazione", "Revisione", "Download"]
    )
    
    # Info card con riepilogo
    render_info_card(
        title="Riepilogo Configurazione",
        content=f"""
        <strong>Materia:</strong> {st.session_state.verification_data.get('materia', 'N/A')}<br>
        <strong>Argomento:</strong> {st.session_state.verification_data.get('argomento', 'N/A')}<br>
        <strong>Livello:</strong> {st.session_state.verification_data.get('livello', 'N/A')}<br>
        <strong>Esercizi:</strong> {st.session_state.verification_data.get('num_esercizi', 'N/A')}<br>
        <strong>Tipologie:</strong> {', '.join(st.session_state.verification_data.get('tipologia', []))}
        """,
        icon="📋",
        variant="info"
    )
    
    # Sezione anteprima
    render_content_section(
        title="Anteprima Verifica",
        content="""
        <div style="padding: 2rem; background: #F9FAFB; border-radius: 0.5rem; border: 1px solid #E5E7EB;">
            <h3 style="color: #111827; margin-bottom: 1rem;">Verifica di Matematica</h3>
            <p style="color: #6B7280; margin-bottom: 1rem;">Classe: 3ª Media - Durata: 60 minuti</p>
            
            <div style="margin-bottom: 2rem;">
                <h4 style="color: #111827; margin-bottom: 0.5rem;">Esercizio 1</h4>
                <p style="color: #374151; margin-bottom: 1rem;">Risolvi la seguente equazione di secondo grado:</p>
                <div style="background: white; padding: 1rem; border-radius: 0.25rem; border: 1px solid #E5E7EB; font-family: monospace;">
                    x² + 5x - 6 = 0
                </div>
            </div>
            
            <div style="margin-bottom: 2rem;">
                <h4 style="color: #111827; margin-bottom: 0.5rem;">Esercizio 2</h4>
                <p style="color: #374151; margin-bottom: 1rem;">Indica se le seguenti affermazioni sono vere o false:</p>
                <div style="background: white; padding: 1rem; border-radius: 0.25rem; border: 1px solid #E5E7EB;">
                    <div style="margin-bottom: 0.5rem;">□ Il prodotto di due numeri negativi è negativo</div>
                    <div style="margin-bottom: 0.5rem;">□ La somma di due numeri positivi è sempre positiva</div>
                    <div>□ La radice quadrata di 16 è 4</div>
                </div>
            </div>
        </div>
        """,
        subtitle="Anteprima generata automaticamente in base alla configurazione",
        status="success"
    )
    
    # Action buttons
    render_action_buttons(
        primary_action={
            "label": "✅ Approva e Continua",
            "key": "approve_continue",
            "help": "Approva la verifica e procedi al download"
        },
        secondary_actions=[
            {
                "label": "✏️ Modifica",
                "key": "edit_verification",
                "help": "Torna indietro per modificare la configurazione"
            },
            {
                "label": "🔄 Rigenera",
                "key": "regenerate",
                "help": "Genera una nuova versione della verifica"
            }
        ]
    )
    
    if st.button("✅ Approva e Continua", key="approve_final"):
        st.session_state.current_stage = STAGE_FINAL
        st.rerun()

elif st.session_state.current_stage == STAGE_FINAL:
    
    # Progress indicators
    render_progress_steps(
        current_step=3,
        total_steps=3,
        step_labels=["Configurazione", "Revisione", "Download"]
    )
    
    # Success card
    render_info_card(
        title="Verifica Generata con Successo!",
        content="""
        La tua verifica personalizzata è pronta per il download. Puoi scaricare il file PDF 
        pronto per la stampa e, se desideri, anche il formato Word per modifiche aggiuntive.
        """,
        icon="🎉",
        variant="success"
    )
    
    # Download section
    render_content_section(
        title="Download File",
        content="""
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
            <div style="padding: 1.5rem; background: #F9FAFB; border: 1px solid #E5E7EB; border-radius: 0.5rem; text-align: center;">
                <div style="font-size: 2rem; margin-bottom: 0.5rem;">📄</div>
                <h4 style="color: #111827; margin-bottom: 0.5rem;">PDF</h4>
                <p style="color: #6B7280; font-size: 0.875rem; margin-bottom: 1rem;">Formato pronto per la stampa</p>
                <button style="background: #0B6BCB; color: white; border: none; padding: 0.5rem 1rem; border-radius: 0.375rem; font-weight: 500; cursor: pointer;">
                    Download PDF
                </button>
            </div>
            <div style="padding: 1.5rem; background: #F9FAFB; border: 1px solid #E5E7EB; border-radius: 0.5rem; text-align: center;">
                <div style="font-size: 2rem; margin-bottom: 0.5rem;">📝</div>
                <h4 style="color: #111827; margin-bottom: 0.5rem;">Word</h4>
                <p style="color: #6B7280; font-size: 0.875rem; margin-bottom: 1rem;">Formato modificabile</p>
                <button style="background: white; color: #111827; border: 1px solid #E5E7EB; padding: 0.5rem 1rem; border-radius: 0.375rem; font-weight: 500; cursor: pointer;">
                    Download Word
                </button>
            </div>
        </div>
        """,
        subtitle="Scegli il formato preferito per il download"
    )
    
    # Additional options
    render_content_section(
        title="Opzioni Aggiuntive",
        content="""
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
            <div style="padding: 1rem; background: #F3F4F6; border-radius: 0.5rem;">
                <h5 style="color: #111827; margin-bottom: 0.5rem;">📚 Griglia Valutazione</h5>
                <p style="color: #6B7280; font-size: 0.875rem;">Genera griglia di valutazione personalizzata</p>
                <button style="margin-top: 0.5rem; background: white; color: #111827; border: 1px solid #E5E7EB; padding: 0.25rem 0.75rem; border-radius: 0.25rem; font-size: 0.875rem; cursor: pointer;">
                    Genera
                </button>
            </div>
            <div style="padding: 1rem; background: #F3F4F6; border-radius: 0.5rem;">
                <h5 style="color: #111827; margin-bottom: 0.5rem;">🔑 Soluzioni</h5>
                <p style="color: #6B7280; font-size: 0.875rem;">Scarica la guida con le soluzioni</p>
                <button style="margin-top: 0.5rem; background: white; color: #111827; border: 1px solid #E5E7EB; padding: 0.25rem 0.75rem; border-radius: 0.25rem; font-size: 0.875rem; cursor: pointer;">
                    Scarica
                </button>
            </div>
        </div>
        """,
        subtitle="Strumenti aggiuntivi per la gestione della verifica"
    )
    
    # Final actions
    render_action_buttons(
        primary_action={
            "label": "🔄 Crea Nuova Verifica",
            "key": "create_new",
            "help": "Inizia a creare una nuova verifica"
        },
        secondary_actions=[
            {
                "label": "📊 Salva nel Profilo",
                "key": "save_profile",
                "help": "Salva questa verifica nel tuo profilo"
            }
        ]
    )
    
    if st.button("🔄 Crea Nuova Verifica", key="restart"):
        # Reset session state
        st.session_state.current_stage = STAGE_INPUT
        st.session_state.verification_data = {}
        st.rerun()

# ── SIDEBAR PROFESSIONALE ─────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="sidebar-header">
        <div class="sidebar-logo">📝 Verific<span>AI</span></div>
        <p style="color: white; text-align: center; margin: 0; font-size: 0.875rem;">
            Piattaforma Professionale
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Stats section
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown("**Statistiche Mensili**")
    st.markdown(f"""
    <div style="display: flex; justify-content: space-between; margin: 1rem 0;">
        <span style="color: white;">Verifiche create</span>
        <span style="color: #0B6BCB; font-weight: 600;">12</span>
    </div>
    <div style="display: flex; justify-content: space-between; margin: 1rem 0;">
        <span style="color: white;">Limite disponibile</span>
        <span style="color: #10B981; font-weight: 600;">∞</span>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Recent activity
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown("**Attività Recente**")
    
    recent_items = [
        "Verifica Matematica - 2 ore fa",
        "Verifica Italiano - Ieri",
        "Verifica Fisica - 3 giorni fa"
    ]
    
    for item in recent_items:
        st.markdown(f"""
        <div style="padding: 0.5rem 0; border-bottom: 1px solid rgba(255,255,255,0.1); font-size: 0.875rem; color: rgba(255,255,255,0.8);">
            {item}
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Settings
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown("**Impostazioni**")
    
    if st.button("⚙️ Preferenze", key="sidebar_settings"):
        st.info("Apertura impostazioni...")
    
    if st.button("📚 Guida", key="sidebar_help"):
        st.info("Apertura guida...")
    
    if st.button("🚪 Logout", key="sidebar_logout"):
        st.info("Logout in corso...")
    
    st.markdown('</div>', unsafe_allow_html=True)
