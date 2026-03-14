# Sostituzione completa della funzione _render_le_tue_verifiche con HTML semplificato

def _render_le_tue_verifiche_simple():
    """
    Pagina "Le tue verifiche" - Versione semplificata senza HTML complesso
    """
    # Pulsante per tornare indietro
    if st.button("← Torna Indietro", key="back_from_mie_verifiche"):
        st.session_state.stage = STAGE_INPUT
        st.session_state.input_percorso = None
        st.rerun()
    
    # Header
    st.markdown("""
    <div style="text-align: center; margin-bottom: 2rem;">
        <h1 style="font-size: 2rem; font-weight: 700; color: #1f2937;">
            📄 Le Tue Verifiche
        </h1>
        <p style="font-size: 1.1rem; color: #6b7280;">
            Gestisci, visualizza e scarica tutte le verifiche che hai creato
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Carica dati
    stats = _get_verifiche_stats()
    verifiche = _load_user_verifiche()
    
    # Stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Totali", stats['totali'])
    with col2:
        st.metric("Questo mese", stats['questo_mese'])
    with col3:
        st.metric("Materie", stats['materie'])
    with col4:
        st.metric("Qualità", f"⭐ {stats['qualita_media']}")
    
    st.markdown("---")
    
    # Filtri
    col_search, col_materia, col_ordine = st.columns([3, 2, 2])
    with col_search:
        search_query = st.text_input("🔍 Cerca...", placeholder="Cerca verifica...")
    
    # Filtra e mostra verifiche
    if verifiche:
        for i, verifica in enumerate(verifiche):
            # Card semplice per ogni verifica
            with st.container():
                st.markdown(f"""
                <div style="
                    border: 2px solid #e5e7eb;
                    border-radius: 12px;
                    padding: 1rem;
                    margin-bottom: 1rem;
                    background: white;
                ">
                    <h3 style="color: #1f2937; margin: 0 0 0.5rem 0;">
                        {verifica.get('argomento', 'Verifica senza titolo')}
                    </h3>
                    <p style="color: #6b7280; margin: 0.5rem 0;">
                        📚 {verifica.get('materia', 'Sconosciuta')} • 
                        🏫 {verifica.get('scuola', 'Non specificata')} • 
                        📝 {verifica.get('num_esercizi', '?')} esercizi
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                # Bottoni azione
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    if st.button(f"👁️ Anteprima", key=f"preview_{verifica.get('id')}_{i}"):
                        st.success("Anteprima generata!")
                        if verifica.get("latex_a"):
                            try:
                                pdf_bytes, error = compila_pdf(verifica["latex_a"])
                                if pdf_bytes:
                                    images, _ = pdf_to_images_bytes(pdf_bytes)
                                    for j, img in enumerate(images[:3]):
                                        st.image(img, caption=f"Pagina {j+1}", width=800)
                            except Exception as e:
                                st.error(f"Errore: {e}")
                
                with col2:
                    if st.button(f"📄 PDF", key=f"download_{verifica.get('id')}_{i}"):
                        st.info("Download PDF...")
                
                with col3:
                    if st.button(f"🎲 Facsimile", key=f"facsimile_{verifica.get('id')}_{i}"):
                        st.info("Creazione facsimile...")
                
                with col4:
                    if st.button(f"🗑️ Elimina", key=f"delete_{verifica.get('id')}_{i}"):
                        st.warning("Conferma eliminazione...")
                
                st.markdown("---")
    else:
        st.info("📝 Nessuna verifica trovata. Inizia a creare la tua prima verifica!")
        
        if st.button("🆕 Crea Nuova Verifica", type="primary"):
            st.session_state.stage = STAGE_INPUT
            st.session_state.input_percorso = None
            st.rerun()
