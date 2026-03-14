# ── main_storico_redesign.py ───────────────────────────────────────────────────
# Nuova implementazione della pagina storico verifiche con design moderno
# ───────────────────────────────────────────────────────────────────────────────

def _render_le_tue_verifiche():
    """
    Pagina "Le tue verifiche" - Gestione verifiche create dall'utente
    Design completamente ridisegnato con card ben separate e anteprime grandi
    """
    # Pulsante per tornare indietro
    col_back, col_center = st.columns([1, 4])
    with col_back:
        if st.button("← Torna Indietro", key="back_from_mie_verifiche", 
                     help="Torna alla pagina principale"):
            st.session_state.stage = STAGE_INPUT
            st.session_state.input_percorso = None
            st.rerun()
    
    # Header professionale
    st.markdown(
        """
        <div style="text-align: center; margin-bottom: 3rem;">
            <h1 style="font-size: 2.5rem; font-weight: 800; color: #1f2937; margin-bottom: 0.5rem; letter-spacing: -0.02em;">
                📄 Le Tue Verifiche
            </h1>
            <p style="font-size: 1.2rem; color: #6b7280; font-weight: 400;">
                Gestisci, visualizza e scarica tutte le verifiche che hai creato
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    # Carica dati reali
    stats = _get_verifiche_stats()
    verifiche = _load_user_verifiche()
    
    # Stats in alto con design moderno
    col1, col2, col3, col4 = st.columns(4, gap="1rem")
    
    with col1:
        st.markdown(
            f"""
            <div style="
                background: linear-gradient(135deg, #3b82f6, #1d4ed8);
                border-radius: 16px;
                padding: 2rem 1.5rem;
                text-align: center;
                color: white;
                box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
                transition: transform 0.2s ease;
            " onmouseover="this.style.transform='translateY(-2px)'" 
               onmouseout="this.style.transform='translateY(0)'">
                <div style="font-size: 2.5rem; font-weight: 800; margin-bottom: 0.5rem;">{stats['totali']}</div>
                <div style="font-size: 0.95rem; opacity: 0.95; font-weight: 500;">Totali</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    
    with col2:
        st.markdown(
            f"""
            <div style="
                background: linear-gradient(135deg, #10b981, #059669);
                border-radius: 16px;
                padding: 2rem 1.5rem;
                text-align: center;
                color: white;
                box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
                transition: transform 0.2s ease;
            " onmouseover="this.style.transform='translateY(-2px)'" 
               onmouseout="this.style.transform='translateY(0)'">
                <div style="font-size: 2.5rem; font-weight: 800; margin-bottom: 0.5rem;">{stats['questo_mese']}</div>
                <div style="font-size: 0.95rem; opacity: 0.95; font-weight: 500;">Questo mese</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    
    with col3:
        st.markdown(
            f"""
            <div style="
                background: linear-gradient(135deg, #f59e0b, #d97706);
                border-radius: 16px;
                padding: 2rem 1.5rem;
                text-align: center;
                color: white;
                box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3);
                transition: transform 0.2s ease;
            " onmouseover="this.style.transform='translateY(-2px)'" 
               onmouseout="this.style.transform='translateY(0)'">
                <div style="font-size: 2.5rem; font-weight: 800; margin-bottom: 0.5rem;">{stats['materie']}</div>
                <div style="font-size: 0.95rem; opacity: 0.95; font-weight: 500;">Materie</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    
    with col4:
        st.markdown(
            f"""
            <div style="
                background: linear-gradient(135deg, #8b5cf6, #7c3aed);
                border-radius: 16px;
                padding: 2rem 1.5rem;
                text-align: center;
                color: white;
                box-shadow: 0 4px 12px rgba(139, 92, 246, 0.3);
                transition: transform 0.2s ease;
            " onmouseover="this.style.transform='translateY(-2px)'" 
               onmouseout="this.style.transform='translateY(0)'">
                <div style="font-size: 2.5rem; font-weight: 800; margin-bottom: 0.5rem;">{stats['qualita_media']}</div>
                <div style="font-size: 0.95rem; opacity: 0.95; font-weight: 500;">Qualità ⭐</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    
    st.markdown('<div style="margin: 2rem 0;"></div>', unsafe_allow_html=True)
    
    # Filtri e ricerca con design migliorato
    st.markdown(
        """
        <div style="
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 2rem;
        ">
            <div style="font-size: 1.1rem; font-weight: 600; color: #374151; margin-bottom: 1rem;">
                🔍 Filtra e Cerca
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    col_search, col_materia, col_ordine = st.columns([3, 2, 2], gap="1rem")
    
    with col_search:
        search_query = st.text_input("🔍 Cerca verifica...", placeholder="Cerca per materia, argomento...", 
                                   label_visibility="collapsed")
    
    # Materie uniche dalle verifiche reali
    materie_real = ["Tutte"] + sorted(list(set([v.get("materia", "Sconosciuta") for v in verifiche if v.get("materia")])))
    with col_materia:
        materia_filter = st.selectbox("📚 Materia", materie_real, label_visibility="collapsed")
    
    with col_ordine:
        ordine_filter = st.selectbox("📅 Ordina per", ["Più recenti", "Più vecchie", "Alfabetico", "Materia"], 
                                   label_visibility="collapsed")
    
    # Filtra le verifiche
    verifiche_filtrate = verifiche.copy()
    
    if search_query:
        verifiche_filtrate = [v for v in verifiche_filtrate if 
            search_query.lower() in v.get("materia", "").lower() or 
            search_query.lower() in v.get("argomento", "").lower()]
    
    if materia_filter != "Tutte":
        verifiche_filtrate = [v for v in verifiche_filtrate if v.get("materia") == materia_filter]
    
    # Ordina le verifiche
    if ordine_filter == "Più recenti":
        verifiche_filtrate.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    elif ordine_filter == "Più vecchie":
        verifiche_filtrate.sort(key=lambda x: x.get("created_at", ""))
    elif ordine_filter == "Alfabetico":
        verifiche_filtrate.sort(key=lambda x: x.get("argomento", ""))
    elif ordine_filter == "Materia":
        verifiche_filtrate.sort(key=lambda x: x.get("materia", ""))
    
    # Mostra verifiche reali con design completamente nuovo
    if verifiche_filtrate:
        for i, verifica in enumerate(verifiche_filtrate):
            # Formatta data
            data_formattata = "Data non disponibile"
            if verifica.get("created_at"):
                try:
                    created_dt = datetime.fromisoformat(verifica["created_at"].replace('Z', '+00:00'))
                    data_formattata = created_dt.strftime("%d/%m/%Y")
                except:
                    pass
            
            # Container principale per ogni verifica - DESIGN MODERNO
            st.markdown(f'''
            <div style="
                background: white;
                border: 2px solid #e5e7eb;
                border-radius: 20px;
                padding: 0;
                margin-bottom: 2.5rem;
                box-shadow: 0 8px 25px rgba(0, 0, 0, 0.08);
                transition: all 0.3s ease;
                overflow: hidden;
                position: relative;
            " onmouseover="this.style.boxShadow='0 12px 35px rgba(0, 0, 0, 0.12)'; this.style.borderColor='#d1d5db'; this.style.transform='translateY(-2px)';" 
               onmouseout="this.style.boxShadow='0 8px 25px rgba(0, 0, 0, 0.08)'; this.style.borderColor='#e5e7eb'; this.style.transform='translateY(0)';">
                
                <!-- Header della verifica -->
                <div style="
                    background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
                    border-bottom: 2px solid #e5e7eb;
                    padding: 2rem;
                    position: relative;
                ">
                    <div style="display: flex; justify-content: space-between; align-items: start;">
                        <div style="flex: 1;">
                            <h3 style="font-size: 1.6rem; font-weight: 800; color: #1f2937; margin: 0 0 1rem 0; line-height: 1.3; letter-spacing: -0.01em;">
                                {verifica.get('argomento', 'Verifica senza titolo')}
                            </h3>
                            <div style="display: flex; gap: 0.75rem; flex-wrap: wrap;">
                                <span style="background: #eff6ff; color: #1d4ed8; padding: 0.5rem 1.2rem; border-radius: 25px; font-size: 0.9rem; font-weight: 600; border: 1px solid #dbeafe;">
                                    📚 {verifica.get('materia', 'Sconosciuta')}
                                </span>
                                <span style="background: #f0fdf4; color: #059669; padding: 0.5rem 1.2rem; border-radius: 25px; font-size: 0.9rem; font-weight: 600; border: 1px solid #dcfce7;">
                                    🏫 {verifica.get('scuola', 'Non specificata')}
                                </span>
                                <span style="background: #fefce8; color: #ca8a04; padding: 0.5rem 1.2rem; border-radius: 25px; font-size: 0.9rem; font-weight: 600; border: 1px solid #fef3c7;">
                                    📝 {verifica.get('num_esercizi', '?')} esercizi
                                </span>
                                <span style="background: #f3f4f6; color: #6b7280; padding: 0.5rem 1.2rem; border-radius: 25px; font-size: 0.9rem; font-weight: 600; border: 1px solid #e5e7eb;">
                                    📅 {data_formattata}
                                </span>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Body con azioni organizzate -->
                <div style="padding: 2rem;">
                    
                    <!-- Sezione Anteprima -->
                    <div style="margin-bottom: 2rem;">
                        <div style="font-size: 1.2rem; font-weight: 700; color: #374151; margin-bottom: 1rem; display: flex; align-items: center; gap: 0.5rem;">
                            👁️ Anteprima
                        </div>
            ''', unsafe_allow_html=True)
            
            # Pulsante anteprima
            col_preview = st.columns([1])[0]
            with col_preview:
                if st.button(f"👁️ Genera Anteprima", key=f"preview_{verifica.get('id')}_{i}", 
                           use_container_width=True, type="secondary"):
                    if verifica.get("latex_a"):
                        # Compila PDF per anteprima
                        try:
                            pdf_bytes, error = compila_pdf(verifica["latex_a"])
                            if pdf_bytes:
                                # Converti in immagini per anteprima
                                images, _ = pdf_to_images_bytes(pdf_bytes)
                                if images:
                                    st.success("📄 Anteprima generata!")
                                    
                                    # Mostra anteprima GRANDE e ben visibile
                                    st.markdown('''
                                    <div style="
                                        border: 3px solid #e5e7eb;
                                        border-radius: 16px;
                                        padding: 2rem;
                                        background: white;
                                        margin: 2rem 0;
                                        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
                                    ">
                                        <div style="font-size: 1.2rem; font-weight: 700; color: #374151; margin-bottom: 1.5rem; text-align: center;">
                                            📄 Anteprima Verifica
                                        </div>
                                    ''', unsafe_allow_html=True)
                                    
                                    for j, img in enumerate(images[:3]):  # Max 3 pagine
                                        st.image(img, caption=f"Pagina {j+1}", width=1000, use_container_width=False)
                                    
                                    st.markdown('</div>', unsafe_allow_html=True)
                                else:
                                    st.error("⚠️ Impossibile generare anteprima immagini")
                            else:
                                st.error(f"⚠️ Errore compilazione PDF: {error}")
                        except Exception as e:
                            st.error(f"⚠️ Errore anteprima: {e}")
                    else:
                        st.warning("⚠️ Contenuto LaTeX non disponibile per questa verifica")
            
            st.markdown(f'''
                    </div>
                    
                    <!-- Sezione Download -->
                    <div style="margin-bottom: 2rem;">
                        <div style="font-size: 1.2rem; font-weight: 700; color: #374151; margin-bottom: 1rem; display: flex; align-items: center; gap: 0.5rem;">
                            📄 Download
                        </div>
            ''', unsafe_allow_html=True)
            
            # Pulsante download
            col_download = st.columns([1])[0]
            with col_download:
                pdf_disabled = not LATEX_AVAILABLE
                pdf_help = "Non disponibile: LaTeX non è installato" if pdf_disabled else "Scarica la verifica in formato PDF"
                
                if st.button(f"📄 Scarica PDF", key=f"download_{verifica.get('id')}_{i}", 
                           disabled=pdf_disabled, help=pdf_help, use_container_width=True):
                    if verifica.get("latex_a"):
                        try:
                            pdf_bytes, error = compila_pdf(verifica["latex_a"])
                            if pdf_bytes:
                                # Nome file
                                filename = f"{verifica.get('argomento', 'verifica').replace(' ', '_').replace('/', '_')}_{data_formattata.replace('/', '')}.pdf"
                                st.download_button(
                                    label="⬇️ Click per scaricare",
                                    data=pdf_bytes,
                                    file_name=filename,
                                    mime="application/pdf",
                                    use_container_width=True,
                                    key=f"final_dl_{verifica.get('id')}_{i}"
                                )
                            else:
                                st.error(f"⚠️ Errore compilazione PDF: {error}")
                        except Exception as e:
                            st.error(f"⚠️ Errore download: {e}")
                    else:
                        st.warning("⚠️ Contenuto LaTeX non disponibile per questa verifica")
            
            st.markdown(f'''
                    </div>
                    
                    <!-- Sezione Azioni -->
                    <div style="margin-bottom: 1rem;">
                        <div style="font-size: 1.2rem; font-weight: 700; color: #374151; margin-bottom: 1rem; display: flex; align-items: center; gap: 0.5rem;">
                            ⚙️ Azioni Rapide
                        </div>
                        
                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem;">
            ''', unsafe_allow_html=True)
            
            # Bottoni azioni in grid
            col_actions = st.columns([1, 1, 1, 1])
            
            with col_actions[0]:
                if st.button(f"🎲 Parti da questa", key=f"facsimile_{verifica.get('id')}_{i}", 
                           use_container_width=True):
                    if verifica.get("latex_a"):
                        try:
                            # Carica la verifica come template per facsimile
                            st.session_state.verifiche["A"]["latex"] = verifica["latex_a"]
                            st.session_state.verifiche["A"]["latex_originale"] = verifica["latex_a"]
                            
                            # Compila PDF per preview
                            pdf_bytes, error = compila_pdf(verifica["latex_a"])
                            if pdf_bytes:
                                st.session_state.verifiche["A"]["pdf"] = pdf_bytes
                                st.session_state.verifiche["A"]["preview"] = True
                                
                                # Genera immagini per preview
                                images, _ = pdf_to_images_bytes(pdf_bytes)
                                st.session_state.preview_images = images or []
                            
                            # Estrai blocchi per review
                            pre, blocks = extract_blocks(verifica["latex_a"])
                            if blocks:
                                st.session_state.review_preamble = pre
                                st.session_state.review_blocks = blocks
                            
                            # Imposta parametri di generazione basati sulla verifica originale
                            st.session_state.gen_params = {
                                "materia": verifica.get("materia", "Matematica"),
                                "difficolta": verifica.get("scuola", "Liceo Scientifico"),
                                "argomento": verifica.get("argomento", "Verifica"),
                                "num_esercizi": verifica.get("num_esercizi", 5),
                                "mostra_punteggi": True,
                                "punti_totali": 100,
                                "con_griglia": True,
                            }
                            
                            # Attiva modalità facsimile e vai a preview
                            st.session_state._facsimile_mode = True
                            st.session_state.stage = STAGE_PREVIEW
                            st.session_state._prev_stage = None
                            st.session_state.input_percorso = None
                            
                            st.success("🎲 Facsimile generato! Vai alla preview per creare la tua variante.")
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"⚠️ Errore generazione facsimile: {e}")
                    else:
                        st.warning("⚠️ Contenuto LaTeX non disponibile per questa verifica")
            
            with col_actions[1]:
                if st.button(f"✏️ Rinomina", key=f"rename_btn_{verifica.get('id')}_{i}", 
                           use_container_width=True):
                    st.session_state[f"rename_{verifica.get('id')}"] = True
                    st.rerun()
            
            with col_actions[2]:
                if st.button(f"🗑️ Elimina", key=f"delete_{verifica.get('id')}_{i}", 
                           use_container_width=True):
                    # Conferma eliminazione
                    if f"confirm_delete_{verifica.get('id')}" not in st.session_state:
                        st.session_state[f"confirm_delete_{verifica.get('id')}"] = False
                    
                    if not st.session_state[f"confirm_delete_{verifica.get('id')}"]:
                        st.session_state[f"confirm_delete_{verifica.get('id')}"] = True
                        st.warning("⚠️ Sei sicuro? Click di nuovo per confermare l'eliminazione.")
                        st.rerun()
                    else:
                        # Elimina dal database
                        try:
                            res = supabase_admin.table("verifiche_storico")\
                                .delete()\
                                .eq("id", verifica.get("id"))\
                                .execute()
                            
                            if res.data:
                                st.success("✅ Verifica eliminata con successo!")
                                del st.session_state[f"confirm_delete_{verifica.get('id')}"]
                                st.rerun()
                            else:
                                st.error("⚠️ Errore durante l'eliminazione")
                        except Exception as e:
                            st.error(f"⚠️ Errore eliminazione: {e}")
                        finally:
                            if f"confirm_delete_{verifica.get('id')}" in st.session_state:
                                del st.session_state[f"confirm_delete_{verifica.get('id')}"]
            
            with col_actions[3]:
                if st.button(f"🔗 Condividi", key=f"share_{verifica.get('id')}_{i}", 
                           use_container_width=True):
                    link = _genera_link_condivisione(verifica.get("id"))
                    if link:
                        st.success("🔗 Link generato!")
                        st.markdown(
                            f"""
                            <div style="
                                background: #f0fdf4;
                                border: 2px solid #86efac;
                                border-radius: 12px;
                                padding: 1.5rem;
                                margin: 1rem 0;
                            ">
                                <div style="font-size: 1rem; color: #059669; margin-bottom: 0.75rem; font-weight: 600;">
                                    📋 Link da condividere:
                                </div>
                                <div style="
                                    background: white;
                                    border: 2px solid #d1d5db;
                                    border-radius: 8px;
                                    padding: 1rem;
                                    font-family: monospace;
                                    font-size: 0.9rem;
                                    word-break: break-all;
                                ">
                                    {link}
                                </div>
                                <div style="margin-top: 1rem;">
                                    <button onclick="navigator.clipboard.writeText('{link}')" 
                                            style="
                                                background: #059669;
                                                color: white;
                                                border: none;
                                                padding: 0.5rem 1rem;
                                                border-radius: 8px;
                                                font-size: 0.9rem;
                                                cursor: pointer;
                                                font-weight: 600;
                                            ">
                                        📋 Copia link
                                    </button>
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
            
            st.markdown(f'''
                        </div>
                    </div>
                </div>
                
                <!-- Footer -->
                <div style="
                    background: #f8fafc;
                    border-top: 2px solid #e5e7eb;
                    padding: 1.5rem 2rem;
                    font-size: 0.9rem;
                    color: #6b7280;
                    text-align: center;
                    font-weight: 500;
                ">
                    ID: {verifica.get('id', 'N/A')} | Creato il {data_formattata}
                </div>
            </div>
            ''', unsafe_allow_html=True)
            
            # Sezione rinomina (se attiva)
            if st.session_state.get(f"rename_{verifica.get('id')}", False):
                st.markdown('''
                <div style="
                    background: #f8fafc;
                    border: 2px solid #e2e8f0;
                    border-radius: 12px;
                    padding: 2rem;
                    margin: 1rem 0;
                ">
                    <div style="font-size: 1.1rem; font-weight: 600; color: #374151; margin-bottom: 1rem;">
                        ✏️ Rinomina Verifica
                    </div>
                ''', unsafe_allow_html=True)
                
                col_input, col_save, col_cancel = st.columns([2, 1, 1])
                with col_input:
                    nuovo_nome = st.text_input(
                        "Nuovo nome:",
                        value=verifica.get("argomento", ""),
                        key=f"rename_input_{verifica.get('id')}_{i}",
                        label_visibility="collapsed"
                    )
                with col_save:
                    if st.button("💾 Salva", key=f"save_rename_{verifica.get('id')}_{i}", use_container_width=True):
                        if nuovo_nome.strip():
                            result = _rinomina_verifica(verifica.get("id"), nuovo_nome.strip())
                            if result:
                                st.success("✅ Nome aggiornato!")
                                del st.session_state[f"rename_{verifica.get('id')}"]
                                st.rerun()
                with col_cancel:
                    if st.button("❌ Annulla", key=f"cancel_rename_{verifica.get('id')}_{i}", use_container_width=True):
                        del st.session_state[f"rename_{verifica.get('id')}"]
                        st.rerun()
                
                st.markdown('</div>', unsafe_allow_html=True)
            
            # Sezione conferma eliminazione (se attiva)
            if st.session_state.get(f"confirm_delete_{verifica.get('id')}", False):
                st.markdown('''
                <div style="
                    background: #fef2f2;
                    border: 2px solid #fecaca;
                    border-radius: 12px;
                    padding: 2rem;
                    margin: 1rem 0;
                    text-align: center;
                ">
                    <div style="font-size: 1.2rem; font-weight: 700; color: #dc2626; margin-bottom: 1rem;">
                        ⚠️ Conferma Eliminazione
                    </div>
                    <div style="font-size: 1rem; color: #7f1d1d; margin-bottom: 1.5rem;">
                        Sei sicuro di voler eliminare questa verifica? Questa azione non può essere annullata.
                    </div>
                ''', unsafe_allow_html=True)
                
                col_confirm, col_abort = st.columns([1, 1])
                with col_confirm:
                    if st.button("🗑️ Sì, Elimina", key=f"confirm_delete_yes_{verifica.get('id')}", use_container_width=True):
                        # Esegui eliminazione
                        try:
                            res = supabase_admin.table("verifiche_storico")\
                                .delete()\
                                .eq("id", verifica.get("id"))\
                                .execute()
                            
                            if res.data:
                                st.success("✅ Verifica eliminata con successo!")
                                del st.session_state[f"confirm_delete_{verifica.get('id')}"]
                                st.rerun()
                            else:
                                st.error("⚠️ Errore durante l'eliminazione")
                        except Exception as e:
                            st.error(f"⚠️ Errore eliminazione: {e}")
                        finally:
                            if f"confirm_delete_{verifica.get('id')}" in st.session_state:
                                del st.session_state[f"confirm_delete_{verifica.get('id')}"]
                
                with col_abort:
                    if st.button("❌ Annulla", key=f"abort_delete_{verifica.get('id')}", use_container_width=True):
                        del st.session_state[f"confirm_delete_{verifica.get('id')}"]
                        st.rerun()
                
                st.markdown('</div>', unsafe_allow_html=True)
    
    else:
        # Messaggio quando non ci sono verifiche
        st.markdown('''
        <div style="
            background: #f8fafc;
            border: 2px solid #e2e8f0;
            border-radius: 16px;
            padding: 3rem;
            text-align: center;
            margin: 2rem 0;
        ">
            <div style="font-size: 3rem; margin-bottom: 1rem;">📝</div>
            <div style="font-size: 1.3rem; font-weight: 600; color: #374151; margin-bottom: 0.5rem;">
                Nessuna verifica trovata
            </div>
            <div style="font-size: 1rem; color: #6b7280;">
                Inizia a creare la tua prima verifica!
            </div>
        </div>
        ''', unsafe_allow_html=True)
