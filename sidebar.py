# ── sidebar.py — VerificAI ───────────────────────────────────────────────────
# Sidebar: Modello AI, Tema, Contatore mensile, Storico, Logout.
# ─────────────────────────────────────────────────────────────────────────────

import logging

import streamlit as st
from ai_client import modelli_sostituiti, riepilogo_uso

from ui_helpers import _reset_label, _render_limite_raggiunto
from config import MONETIZZAZIONE_ATTIVA, PREZZI_VISIBILI, BONUS_PER_INVITO, MAX_INVITI_CON_BONUS
from ui_inviti import render_invito

logger = logging.getLogger("verificai.sidebar")


def render_sidebar(
    supabase_admin,
    utente,
    verifiche_mese_count,
    is_admin,
    limite_raggiunto,
    T,
    MODELLI_DISPONIBILI,
    LIMITE_MENSILE,
    giorni_al_reset_func,
    supabase_client,
    contatto_url: str,
    illimitato: bool = False,
    THEMES: dict = None,
    THEME_LABELS: dict = None,
    invito: dict = None,
) -> dict:

    theme_changed = False

    with st.sidebar:
        # I colori della sidebar seguono il tema (chiara in Carta, scura in Notte);
        # il testo usa sidebar_input_text del tema.
        _sb_text  = T.get("sidebar_input_text", "#E6EDF3")
        _sb_muted = T.get("sidebar_muted", "#94A3B8")
        
        # Ordine a schermo: uso mensile → le mie verifiche → tema → strumenti admin → utente.
        # (il codice sotto resta nell'ordine di calcolo; i contenitori fissano la posizione)
        _c_uso     = st.container()
        _c_storico = st.container()
        _c_admin   = st.container()
        _c_user    = st.container()

        # ── MODELLO AI — scelto dal piano, non dall'utente ───────────────────
        # Free → Flash Lite · Pro → Flash 2.5 · Gold → Pro 2.5.
        # Solo l'admin può scegliere a mano (expander chiuso).
        # Il model_id effettivo viene poi validato in main.py con
        # get_model_id_per_piano(piano, materia) al momento della generazione.
        _piano = "admin" if is_admin else st.session_state.get("piano_utente", "free")

        if is_admin:
            with _c_admin, st.expander("Strumenti admin", expanded=False, icon=":material/build:"):
                _nomi_admin = list(MODELLI_DISPONIBILI.keys())
                _sel_modello = st.selectbox(
                    "Modello",
                    _nomi_admin,
                    key="sb_modello_admin",
                )
                st.selectbox(
                    "Vedi l'app come", ["Io (admin)", "Utente nuovo (prima verifica)", "Utente Free (dopo la prima)", "Utente Pro"],
                    key="sb_simula_piano",
                    help="Solo per provare: mostra blocchi e messaggi come li vedrebbe un altro utente.",
                )
                if st.button("Modelli di verifica", key="open_banca", use_container_width=True,
                             icon=":material/library_books:"):
                    st.session_state.stage = "BANCA"
                    st.rerun()
                if st.button("Cruscotto", key="open_cruscotto", use_container_width=True, icon=":material/monitoring:"):
                    st.session_state.stage = "CRUSCOTTO"
                    st.rerun()
                for _vecchio, _nuovo in modelli_sostituiti().items():
                    st.caption(f"⚠️ {_vecchio} non è più disponibile: uso {_nuovo}")
                # Consumi reali dall'ultimo riavvio (token e costo stimato per compito e modello)
                _uso = riepilogo_uso()
                if _uso:
                    st.caption(f"Costo stimato dall'ultimo riavvio: ${sum(r['costo_usd'] for r in _uso):.3f}")
                    for _r in _uso[:8]:
                        st.caption(
                            f"{_r['compito']} · {_r['modello'].replace('gemini-', '')} · {_r['chiamate']} chiamate · "
                            f"in {_r['input']:,} · out {_r['output'] + _r['pensiero']:,} "
                            f"(di cui ragionamento {_r['pensiero']:,}) · ${_r['costo_usd']:.3f}"
                        )
            modello_id = MODELLI_DISPONIBILI[_sel_modello]["id"]
        else:
            _piano_modello = _piano if _piano in ("pro", "gold") else "free"
            modello_id = next(
                v["id"] for v in MODELLI_DISPONIBILI.values()
                if v["piano"] == _piano_modello
            )

        # ── TEMA ──────────────────────────────────────────────────────────────
        # Il tema scuro non si sceglie più: una sessione rimasta su "notte" torna a Carta.
        if THEMES and st.session_state.get("theme") != list(THEMES.keys())[0]:
            st.session_state.theme = list(THEMES.keys())[0]
            theme_changed = True

        # ── CONTATORE MENSILE ─────────────────────────────────────────────────
        with _c_uso:
            # Piano illimitato → solo il numero del mese; piano free → "X di N" con barra.
            _gg_reset, _hh_reset = giorni_al_reset_func()
            _reset_str = _reset_label(_gg_reset, _hh_reset)

            if illimitato:
                _valore  = f"{verifiche_mese_count}"
                _sotto   = "Illimitate con il tuo piano"
                _barra   = ""
            else:
                _perc_uso  = min(100, int(verifiche_mese_count / LIMITE_MENSILE * 100))
                _color_bar = (T["error"] if limite_raggiunto
                              else (T["warn"] if _perc_uso >= 70 else T["success"]))
                _valore = f"{verifiche_mese_count} di {LIMITE_MENSILE}"
                _sotto  = _reset_str
                _barra  = (
                    f'<div style="background:{T.get("sidebar_border", "#475569")};border-radius:10px;'
                    'overflow:hidden;height:4px;width:100%;position:relative;">'
                    f'<div style="width:{_perc_uso}%;background:{_color_bar};height:100%;'
                    'border-radius:10px;transition:width .6s ease;position:absolute;'
                    'top:0;left:0;"></div></div>'
                )

            st.markdown('<div class="sidebar-label" style="margin-top:.5rem;">Utilizzo mensile</div>',
                        unsafe_allow_html=True)
            st.markdown(
                '<div style="margin-bottom:.6rem;font-family:\'DM Sans\',sans-serif;">'
                '<div style="display:flex;justify-content:space-between;align-items:center;'
                'margin-bottom:.5rem;">'
                f'<span style="font-size:.85rem;font-weight:600;color:{_sb_text};">'
                'Verifiche questo mese</span>'
                f'<span style="font-size:.9rem;font-weight:800;color:{_sb_text};">{_valore}</span>'
                '</div>'
                f'{_barra}'
                f'<div style="text-align:left;font-size:.78rem;font-weight:500;'
                f'color:{_sb_muted};margin-top:6px;">{_sotto}</div>'
                '</div>',
                unsafe_allow_html=True,
            )

            if limite_raggiunto:
                def _vai_pro():
                    st.session_state["_upgrade_da"] = st.session_state.get("stage")
                    st.session_state["_upgrade_funzione"] = None
                    st.session_state.stage = "UPGRADE"
                    st.rerun()

                _render_limite_raggiunto(T, LIMITE_MENSILE, _reset_str, contatto_url,
                                         pro_cb=_vai_pro if (MONETIZZAZIONE_ATTIVA and PREZZI_VISIBILI) else None, pro_key="sb",
                                         text_color=_sb_text)

        # ── LE MIE VERIFICHE — un solo pulsante con il conteggio ──────────────
        with _c_storico:
            total_verifiche = None
            try:
                if utente is not None and supabase_admin is not None:
                    storico_count = (
                        supabase_admin.table("verifiche_storico")
                        .select("id", count="exact")
                        .eq("user_id", utente.id)
                        .is_("deleted_at", "null")
                        .execute()
                    )
                    total_verifiche = storico_count.count if storico_count else 0
            except Exception as _e:
                logger.warning(f"Conteggio storico non disponibile: {_e}")

            _lbl_storico = (
                f"Le mie verifiche ({total_verifiche})"
                if total_verifiche is not None else "Le mie verifiche"
            )
            st.markdown('<div style="height:.9rem"></div>', unsafe_allow_html=True)
            if st.button(_lbl_storico, key="open_storico", use_container_width=True, type="secondary", icon=":material/folder_open:"):
                if st.session_state.get("stage") != "MIE_VERIFICHE":
                    st.session_state["_stage_prima"] = st.session_state.get("stage")   # per tornare indietro
                st.session_state.stage = "MIE_VERIFICHE"
                st.rerun()
            if MONETIZZAZIONE_ATTIVA and not is_admin and st.session_state.get("piano_utente", "free") == "free":
                if st.button("Passa a Pro" if PREZZI_VISIBILI else "Sblocca verifiche complete", key="open_upgrade", use_container_width=True, type="secondary",
                             icon=":material/workspace_premium:" if PREZZI_VISIBILI else ":material/lock_open:"):
                    st.session_state["_upgrade_da"] = st.session_state.get("stage")
                    st.session_state["_upgrade_funzione"] = None
                    st.session_state.stage = "UPGRADE"
                    st.rerun()

        # ── INVITA UN COLLEGA — per ogni amico che crea la sua prima verifica, 2 verifiche con tutto il Pro ──
        if invito:
            with _c_storico, st.expander("Invita un collega", expanded=False, icon=":material/group_add:"):
                render_invito(T, invito, con_titolo=False)

        # ── USER + LOGOUT ─────────────────────────────────────────────────────
        with _c_user:
            if utente is not None:
                email_utente = utente.email or ""
                iniziale     = email_utente[0].upper() if email_utente else "?"
            else:
                email_utente = ""
                iniziale     = "?"

            _piano_label = {
                "admin": "Admin",
                "gold":  "Piano Gold",
                "pro":   "Piano Pro",
            }.get(_piano, "Piano gratuito")
            _piano_icon = {
                "admin": "⚙️",
                "gold":  "🌟",
                "pro":   "⚡",
            }.get(_piano, "🎓")
            st.markdown(f"""
            <div class="user-pill">
              <div class="user-avatar">{iniziale}</div>
              <div class="user-info">
                <div class="user-email">{email_utente}</div>
                <div class="user-role">{_piano_icon} {_piano_label}</div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown('<div class="logout-btn-wrap">', unsafe_allow_html=True)
            if st.button("↩ Esci dall'account", key="logout_btn"):
                from auth import cancella_sessione_cookie
                cancella_sessione_cookie()
                supabase_client.auth.sign_out()
                st.session_state.utente          = None
                st.session_state.supabase       = None
                st.session_state.stage          = "INPUT"
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    return {
        "modello_id":    modello_id,
        "theme_changed": theme_changed,
    }
