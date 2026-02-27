import streamlit as st
from datetime import datetime, timezone

def render_sidebar(
    supabase_admin, 
    utente, 
    verifiche_mese_count, 
    is_admin, 
    limite_raggiunto, 
    T, 
    SCUOLE,           # mantenuto per compatibilità firma, non più usato qui
    MODELLI_DISPONIBILI, 
    LIMITE_MENSILE,
    giorni_al_reset_func,
    compila_pdf_func,
    supabase_client
) -> dict:
    
    with st.sidebar:
        st.markdown('<div class="sidebar-title">Impostazioni</div>', unsafe_allow_html=True)

        # ── MODELLO AI ────────────────────────────────────────────────────────────
        st.markdown('<div class="sidebar-label">Modello AI</div>', unsafe_allow_html=True)
        if is_admin:
            _sel_modello = st.selectbox(
                "modello",
                list(MODELLI_DISPONIBILI.keys()),
                label_visibility="collapsed"
            )
            modello_id = MODELLI_DISPONIBILI[_sel_modello]["id"]
        else:
            _nomi_display = []
            for _k, _v in MODELLI_DISPONIBILI.items():
                if _v["pro"]:
                    _nomi_display.append(_k + "  🔒")
                else:
                    _nomi_display.append(_k)
            
            _sel_display = st.selectbox(
                "modello",
                _nomi_display,
                index=0,
                label_visibility="collapsed"
            )
            _sel_raw = _sel_display.replace("  🔒", "")
            _info = MODELLI_DISPONIBILI[_sel_raw]
            
            if _info["pro"]:
                st.markdown(
                    f'<div style="font-size:0.74rem;color:{T["muted"]};padding:4px 0 2px 2px;'
                    f'font-family:DM Sans,sans-serif;">🔒 Disponibile solo per gli amministratori.</div>',
                    unsafe_allow_html=True
                )
                modello_id = MODELLI_DISPONIBILI["⚡ Flash 2.5 Lite (velocissimo)"]["id"]
            else:
                modello_id = _info["id"]

        # ── ASPETTO ───────────────────────────────────────────────────────────────
        st.markdown('<div class="sidebar-label" style="margin-top:1rem;">Aspetto</div>', unsafe_allow_html=True)
        tema_sel = st.radio(
            "tema",
            ["☀️ Chiaro", "🌙 Scuro"],
            index=0 if st.session_state.theme == "light" else 1,
            horizontal=True,
            label_visibility="collapsed"
        )
        new_theme = "light" if "Chiaro" in tema_sel else "dark"
        if new_theme != st.session_state.theme:
            st.session_state.theme = new_theme
            st.rerun()

        # ── CONTATORE MENSILE ─────────────────────────────────────────────────────
        st.markdown('<div class="sidebar-label" style="margin-top:1.5rem;">Utilizzo mensile</div>', unsafe_allow_html=True)
        _perc_uso = min(100, int(verifiche_mese_count / LIMITE_MENSILE * 100))
        _color_bar = "#EF4444" if limite_raggiunto else ("#F59E0B" if _perc_uso >= 70 else "#10B981")
        _count_class = "limit-reached" if limite_raggiunto else ("limit-near" if _perc_uso >= 70 else "")
        
        _gg_reset, _hh_reset = giorni_al_reset_func()
        
        if _gg_reset == 0:
            _reset_str = f"Reset tra {_hh_reset}h"
        elif _gg_reset == 1:
            _reset_str = f"Reset domani"
        else:
            _reset_str = f"Reset tra {_gg_reset}gg"

        st.markdown(f"""
        <div class="monthly-bar">
          <div class="monthly-bar-header">
            <span class="monthly-bar-label">Verifiche questo mese</span>
            <span class="monthly-bar-count {_count_class}">{verifiche_mese_count} / {LIMITE_MENSILE}</span>
          </div>
          <div class="monthly-progress">
            <div class="monthly-progress-fill" style="width:{_perc_uso}%;background:{_color_bar};"></div>
          </div>
          <div style="text-align:right;font-size:0.68rem;color:#6b6960;margin-top:4px;font-family:'DM Sans',sans-serif;">
            🔄 {_reset_str}
          </div>
        </div>
        """, unsafe_allow_html=True)
        
        if limite_raggiunto:
            st.warning(f"Limite mensile raggiunto ({LIMITE_MENSILE} verifiche). {_reset_str}.")

        # ── STORICO VERIFICHE ─────────────────────────────────────────────────────
        st.markdown('<div class="sidebar-label" style="margin-top:1rem;">Le mie verifiche</div>', unsafe_allow_html=True)

        _refresh_key = st.session_state._storico_refresh
        _page_size = 5
        _storico_limit = st.session_state._storico_page * _page_size
        
        try:
            storico = supabase_admin.table("verifiche_storico")\
                .select("id, materia, argomento, created_at, latex_a, latex_b, latex_r, scuola")\
                .eq("user_id", st.session_state.utente.id)\
                .is_("deleted_at", "null")\
                .order("created_at", desc=True)\
                .limit(_storico_limit + 1)\
                .execute()

            if storico.data:
                _ha_altri = len(storico.data) > _storico_limit
                dati_pagina = storico.data[:_storico_limit]
                _pref = st.session_state._preferiti
                
                def _sort_key(v):
                    return (0 if v['id'] in _pref else 1, v['created_at'])
                
                dati_ordinati = sorted(dati_pagina, key=_sort_key)

                for v in dati_ordinati:
                    data_str = v['created_at'][:10]
                    is_pref = v['id'] in _pref
                    star_ico = "★" if is_pref else "☆"
                    star_label_prefix = "⭐ " if is_pref else ""
                    label = f"{star_label_prefix}{v['materia']} — {v['argomento'][:20]}{'...' if len(v['argomento'])>20 else ''}"
                    
                    with st.expander(f"{label} ({data_str})"):
                        if v.get('scuola'):
                            st.caption(f"{v['scuola'][:35]}")

                        _col_star, _col_spacer = st.columns([1, 3])
                        with _col_star:
                            st.markdown(f'<div class="{"stella-btn-on" if is_pref else "stella-btn"}">', unsafe_allow_html=True)
                            if st.button(star_ico, key=f"star_{v['id']}_{_refresh_key}"):
                                if v['id'] in st.session_state._preferiti:
                                    st.session_state._preferiti.discard(v['id'])
                                else:
                                    st.session_state._preferiti.add(v['id'])
                                st.rerun()
                            st.markdown('</div>', unsafe_allow_html=True)

                        if v.get('latex_a'):
                            if st.button("♻ Ricarica Fila A", key=f"reload_a_{v['id']}_{_refresh_key}", use_container_width=True):
                                st.session_state.verifiche['A']['latex'] = v['latex_a']
                                pdf, _ = compila_pdf_func(v['latex_a'])
                                if pdf:
                                    st.session_state.verifiche['A']['pdf'] = pdf
                                    st.session_state.verifiche['A']['preview'] = True
                                st.rerun()
                        
                        if v.get('latex_b'):
                            if st.button("♻ Ricarica Fila B", key=f"reload_b_{v['id']}_{_refresh_key}", use_container_width=True):
                                st.session_state.verifiche['B']['latex'] = v['latex_b']
                                pdf, _ = compila_pdf_func(v['latex_b'])
                                if pdf:
                                    st.session_state.verifiche['B']['pdf'] = pdf
                                    st.session_state.verifiche['B']['preview'] = True
                                st.rerun()

                        st.markdown('<div class="elimina-btn">', unsafe_allow_html=True)
                        if st.button("Elimina", key=f"del_{v['id']}_{_refresh_key}", use_container_width=True):
                            try:
                                supabase_admin.table("verifiche_storico")\
                                    .update({"deleted_at": datetime.now(timezone.utc).isoformat()})\
                                    .eq("id", v['id'])\
                                    .execute()
                                st.session_state._preferiti.discard(v['id'])
                                st.session_state._storico_refresh += 1
                                st.toast("Verifica rimossa.", icon="🗑️")
                                st.rerun()
                            except Exception as del_err:
                                st.error(f"Errore: {del_err}")
                        st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.caption("Nessuna verifica salvata ancora.")

            if storico.data and _ha_altri:
                if st.button("Carica altre verifiche", key="storico_load_more", use_container_width=True):
                    st.session_state._storico_page += 1
                    st.rerun()
            elif storico.data and st.session_state._storico_page > 1:
                st.caption(f"Tutte le {len(dati_pagina)} verifiche caricate.")

        except Exception as e:
            st.caption("Storico non disponibile.")

        # ── USER PILL + LOGOUT ────────────────────────────────────────────────────
        st.markdown("---")
        email_utente = utente.email or ""
        iniziale = email_utente[0].upper() if email_utente else "?"
        st.markdown(f"""
        <div class="user-pill">
          <div class="user-avatar">{iniziale}</div>
          <div class="user-info">
            <div class="user-email">{email_utente}</div>
            <div class="user-role">Docente · Piano gratuito</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div style="height:0.5rem;"></div>', unsafe_allow_html=True)
        st.markdown('<div class="logout-btn-wrap">', unsafe_allow_html=True)
        if st.button("↩ Esci dall'account", key="logout_btn"):
            from auth import cancella_sessione_cookie
            cancella_sessione_cookie()
            supabase_client.auth.sign_out()
            st.session_state.utente = None
            st.session_state.pop("_sb_access_token", None)
            st.session_state.pop("_sb_refresh_token", None)
            st.session_state._token_check_done = False
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    return {
        'modello_id': modello_id,
    }
