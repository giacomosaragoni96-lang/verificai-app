# ── layout_components.py — VerificAI Professional Layout Components ────────
# Componenti riutilizzabili per layout professionale con gerarchia visiva
# Focus: Flusso logico per educatori, chiarezza e professionalità
# ───────────────────────────────────────────────────────────────────────────────

import streamlit as st
from typing import Optional, Dict, Any, List
import time

def render_professional_header(
    title: str,
    subtitle: Optional[str] = None,
    stage: Optional[str] = None,
    stage_steps: Optional[List[Dict[str, Any]]] = None
) -> None:
    """
    Header professionale con gerarchia chiara e indicatori di stage
    
    Args:
        title: Titolo principale (H1)
        subtitle: Sottotitolo descrittivo
        stage: Stage corrente (es. "INPUT", "REVIEW", "FINAL")
        stage_steps: Lista di dizionari con {name: str, status: str}
    """
    st.markdown("""
    <div class="main-header">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
            <div>
                <h1 style="margin: 0; font-size: 2.5rem; font-weight: 700; color: #111827;">
                    📝 Verific<span style="background: linear-gradient(135deg,#0B6BCB,#C3E9FB);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;">AI</span>
                </h1>
    """, unsafe_allow_html=True)
    
    if subtitle:
        st.markdown(f"""
                <p style="margin: 0; color: #6B7280; font-size: 1.125rem; margin-top: 0.5rem;">
                    {subtitle}
                </p>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Stage indicators
    if stage and stage_steps:
        st.markdown('<div style="display: flex; gap: 1rem; align-items: center;">', unsafe_allow_html=True)
        
        for i, step in enumerate(stage_steps):
            is_active = step.get("name") == stage
            is_completed = step.get("status") == "completed"
            
            dot_class = "stage-dot active" if is_active else "stage-dot completed" if is_completed else "stage-dot"
            text_color = "#0B6BCB" if is_active else "#10B981" if is_completed else "#6B7280"
            font_weight = "600" if is_active else "400"
            
            st.markdown(f"""
                <div style="display: flex; align-items: center; gap: 0.5rem;">
                    <div class="{dot_class}"></div>
                    <span style="color: {text_color}; font-weight: {font_weight}; font-size: 0.875rem;">
                        {step.get("label", step.get("name"))}
                    </span>
                </div>
            """, unsafe_allow_html=True)
            
            if i < len(stage_steps) - 1:
                st.markdown('<div style="width: 2rem; height: 1px; background: #E5E7EB;"></div>', unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)


def render_content_section(
    title: str,
    content: Any,
    subtitle: Optional[str] = None,
    status: Optional[str] = None,
    collapsible: bool = False
) -> None:
    """
    Sezione contenuto con design professionale e gerarchia
    
    Args:
        title: Titolo della sezione (H2)
        content: Contenuto da mostrare
        subtitle: Sottotitolo descrittivo
        status: Stato per indicatore colorato
        collapsible: Se rendere la sezione collapsible
    """
    section_id = f"section_{title.lower().replace(' ', '_')}"
    
    if collapsible:
        with st.expander(title, expanded=True):
            if subtitle:
                st.markdown(f"<p style='color: #6B7280; margin-bottom: 1rem;'>{subtitle}</p>", unsafe_allow_html=True)
            
            if status:
                _render_status_indicator(status)
            
            st.markdown('<div class="fade-in">', unsafe_allow_html=True)
            st.write(content)
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="content-section slide-up">', unsafe_allow_html=True)
        
        st.markdown(f"<h2 style='margin: 0 0 1rem 0;'>{title}</h2>", unsafe_allow_html=True)
        
        if subtitle:
            st.markdown(f"<p style='color: #6B7280; margin-bottom: 1rem;'>{subtitle}</p>", unsafe_allow_html=True)
        
        if status:
            _render_status_indicator(status)
        
        st.write(content)
        
        st.markdown('</div>', unsafe_allow_html=True)


def render_form_section(
    title: str,
    fields: Dict[str, Any],
    submit_text: str = "Genera Verifica",
    submit_disabled: bool = False
) -> bool:
    """
    Sezione form con layout professionale e validazione visiva
    
    Args:
        title: Titolo del form
        fields: Dizionario con {field_name: field_config}
        submit_text: Testo bottone submit
        submit_disabled: Se disabilitare bottone
    
    Returns:
        bool: True se form submitted
    """
    st.markdown(f'<div class="content-section">', unsafe_allow_html=True)
    st.markdown(f"<h2 style='margin: 0 0 1.5rem 0;'>{title}</h2>", unsafe_allow_html=True)
    
    submitted = False
    
    with st.form(key=f"form_{title.lower().replace(' ', '_')}"):
        for field_name, field_config in fields.items():
            field_type = field_config.get("type", "text")
            field_label = field_config.get("label", field_name.replace("_", " ").title())
            field_help = field_config.get("help", "")
            field_options = field_config.get("options", [])
            field_default = field_config.get("default", "")
            field_required = field_config.get("required", False)
            
            # Label con indicatore required
            label_html = f"{field_label}"
            if field_required:
                label_html += ' <span style="color: #EF4444;">*</span>'
            
            st.markdown(f'<div class="form-label">{label_html}</div>', unsafe_allow_html=True)
            
            if field_type == "text":
                st.text_input(
                    "",
                    key=field_name,
                    help=field_help,
                    value=field_default
                )
            elif field_type == "textarea":
                st.text_area(
                    "",
                    key=field_name,
                    help=field_help,
                    value=field_default
                )
            elif field_type == "select":
                st.selectbox(
                    "",
                    options=field_options,
                    key=field_name,
                    help=field_help
                )
            elif field_type == "multiselect":
                st.multiselect(
                    "",
                    options=field_options,
                    key=field_name,
                    help=field_help
                )
            elif field_type == "number":
                st.number_input(
                    "",
                    key=field_name,
                    help=field_help,
                    value=field_default
                )
            
            st.markdown('<div style="margin-bottom: 1rem;"></div>', unsafe_allow_html=True)
        
        # Submit button
        st.markdown('<div style="margin-top: 2rem;">', unsafe_allow_html=True)
        submitted = st.form_submit_button(
            submit_text,
            disabled=submit_disabled,
            use_container_width=True
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    return submitted


def render_status_indicator(status: str, message: Optional[str] = None) -> None:
    """
    Indicatore di stato con colori semantici
    
    Args:
        status: Tipo di stato (success, warning, error, info)
        message: Messaggio opzionale
    """
    status_classes = {
        "success": "status-success",
        "warning": "status-warning", 
        "error": "status-error",
        "info": "status-info"
    }
    
    status_class = status_classes.get(status, "status-info")
    
    if message:
        st.markdown(f'<div class="{status_class}">{message}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="{status_class}">Stato: {status.title()}</div>', unsafe_allow_html=True)


def render_progress_steps(
    current_step: int,
    total_steps: int,
    step_labels: List[str]
) -> None:
    """
    Barra di progresso steps con design professionale
    
    Args:
        current_step: Step corrente (1-based)
        total_steps: Numero totale di steps
        step_labels: Label per ogni step
    """
    progress_percentage = (current_step / total_steps) * 100
    
    st.markdown(f"""
    <div style="margin-bottom: 2rem;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
            <span style="font-size: 0.875rem; color: #6B7280; font-weight: 500;">
                Passo {current_step} di {total_steps}
            </span>
            <span style="font-size: 0.875rem; color: #6B7280;">
                {progress_percentage:.0f}%
            </span>
        </div>
        <div style="background: #E5E7EB; border-radius: 0.5rem; height: 0.5rem; overflow: hidden;">
            <div style="background: #0B6BCB; height: 100%; width: {progress_percentage}%; transition: width 0.3s ease; border-radius: 0.5rem;"></div>
        </div>
        <div style="display: flex; justify-content: space-between; margin-top: 0.5rem;">
    """, unsafe_allow_html=True)
    
    for i, label in enumerate(step_labels):
        is_completed = i < current_step - 1
        is_current = i == current_step - 1
        
        color = "#10B981" if is_completed else "#0B6BCB" if is_current else "#6B7280"
        weight = "600" if is_current else "400"
        
        st.markdown(f"""
            <span style="font-size: 0.75rem; color: {color}; font-weight: {weight};">
                {label}
            </span>
        """, unsafe_allow_html=True)
    
    st.markdown("</div></div>", unsafe_allow_html=True)


def render_action_buttons(
    primary_action: Dict[str, Any],
    secondary_actions: Optional[List[Dict[str, Any]]] = None
) -> None:
    """
    Gruppo di action buttons con gerarchia visiva chiara
    
    Args:
        primary_action: Dict con {label, key, disabled, help}
        secondary_actions: Lista di dicts con stessa struttura
    """
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.button(
            primary_action.get("label", "Azione Principale"),
            key=primary_action.get("key"),
            disabled=primary_action.get("disabled", False),
            help=primary_action.get("help", ""),
            use_container_width=True
        )
    
    with col2:
        if secondary_actions:
            for action in secondary_actions:
                st.button(
                    action.get("label", "Azione Secondaria"),
                    key=action.get("key"),
                    help=action.get("help", ""),
                    use_container_width=True
                )


def render_info_card(
    title: str,
    content: str,
    icon: str = "ℹ️",
    variant: str = "info"
) -> None:
    """
    Card informativa con design professionale
    
    Args:
        title: Titolo della card
        content: Contenuto testuale
        icon: Icona emoji
        variant: Variante (info, success, warning, error)
    """
    variant_colors = {
        "info": {"bg": "#3B82F615", "border": "#3B82F630", "text": "#3B82F6"},
        "success": {"bg": "#10B98115", "border": "#10B98130", "text": "#10B981"},
        "warning": {"bg": "#F59E0B15", "border": "#F59E0B30", "text": "#F59E0B"},
        "error": {"bg": "#EF444415", "border": "#EF444430", "text": "#EF4444"}
    }
    
    colors = variant_colors.get(variant, variant_colors["info"])
    
    st.markdown(f"""
    <div class="content-section" style="background: {colors['bg']}; border: 1px solid {colors['border']}; padding: 1.5rem;">
        <div style="display: flex; align-items: flex-start; gap: 1rem;">
            <div style="font-size: 1.5rem;">{icon}</div>
            <div style="flex: 1;">
                <h3 style="margin: 0 0 0.5rem 0; color: {colors['text']}; font-size: 1.125rem; font-weight: 600;">
                    {title}
                </h3>
                <p style="margin: 0; color: #6B7280; line-height: 1.6;">
                    {content}
                </p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_loading_section(message: str = "Elaborazione in corso...") -> None:
    """
    Sezione loading con skeleton animation professionale
    """
    st.markdown(f"""
    <div class="content-section">
        <div style="text-align: center; padding: 3rem 0;">
            <div style="margin-bottom: 1rem;">
                <div style="display: inline-block; width: 40px; height: 40px; border: 3px solid #E5E7EB; border-top: 3px solid #0B6BCB; border-radius: 50%; animation: spin 1s linear infinite;"></div>
            </div>
            <p style="color: #6B7280; font-weight: 500;">{message}</p>
            <div style="margin-top: 2rem; text-align: left;">
                <div class="loading-skeleton" style="height: 20px; width: 80%; margin-bottom: 0.5rem;"></div>
                <div class="loading-skeleton" style="height: 20px; width: 100%; margin-bottom: 0.5rem;"></div>
                <div class="loading-skeleton" style="height: 20px; width: 60%;"></div>
            </div>
        </div>
    </div>
    <style>
    @keyframes spin {{
        0% {{ transform: rotate(0deg); }}
        100% {{ transform: rotate(360deg); }}
    }}
    </style>
    """, unsafe_allow_html=True)


def _render_status_indicator(status: str) -> None:
    """Helper interno per renderizzare indicatori di stato"""
    status_messages = {
        "success": "✅ Operazione completata",
        "warning": "⚠️ Attenzione richiesta",
        "error": "❌ Errore rilevato",
        "info": "ℹ️ Informazione"
    }
    
    message = status_messages.get(status, f"Stato: {status}")
    render_status_indicator(status, message)
