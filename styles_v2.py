# ── styles_v2.py — VerificAI Professional UX Redesign ───────────────────────
# Design System Professionale con gerarchia visiva chiara
# Focus: Educatori (docenti) - non tecnici, bisogno di chiarezza e flusso logico
# ───────────────────────────────────────────────────────────────────────────────

def get_professional_css(T: dict) -> str:
    """
    Design System v3 - Professional Educator Interface
    
    Principi:
    1. Gerarchia visiva chiara (H1 > H2 > H3 > body)
    2. Spaziatura consistente (8px grid)
    3. Colori semantici per stati/emozioni
    4. Micro-interazioni professionali
    5. Accessibilità WCAG AA
    """
    
    # ── Color System ─────────────────────────────────────────────────────────────
    # Primary (Blu professionale)
    primary = {
        "50": "#E8F4FD",  # sfondo leggerissimo
        "100": "#C3E9FB", # hover sfondo
        "500": "#0B6BCB", # primary main
        "600": "#0A5CAD", # primary dark
        "900": "#073B85", # primary darkest
    }
    
    # Semantic colors
    semantic = {
        "success": "#10B981",    # verde positivo
        "warning": "#F59E0B",    # arancione attenzione  
        "error": "#EF4444",      # rosso errore
        "info": "#3B82F6",       # blu informativo
    }
    
    # Neutrals (scala grigia)
    neutrals = {
        "50": "#F9FAFB",   # sfondo principale
        "100": "#F3F4F6",  # card background
        "200": "#E5E7EB",  # borders
        "500": "#6B7280",  # testo secondario
        "900": "#111827",  # testo principale
    }
    
    # ── Typography Scale ───────────────────────────────────────────────────────
    typography = {
        "h1": {"size": "2.5rem", "weight": "700", "line": "1.2"},  # 40px
        "h2": {"size": "2rem", "weight": "600", "line": "1.3"},   # 32px  
        "h3": {"size": "1.5rem", "weight": "600", "line": "1.4"}, # 24px
        "h4": {"size": "1.25rem", "weight": "500", "line": "1.4"}, # 20px
        "body": {"size": "1rem", "weight": "400", "line": "1.6"}, # 16px
        "small": {"size": "0.875rem", "weight": "400", "line": "1.5"}, # 14px
    }
    
    # ── Spacing System (8px grid) ───────────────────────────────────────────────
    spacing = {
        "xs": "0.25rem",   # 4px
        "sm": "0.5rem",    # 8px
        "md": "1rem",      # 16px
        "lg": "1.5rem",    # 24px
        "xl": "2rem",      # 32px
        "2xl": "3rem",     # 48px
        "3xl": "4rem",     # 64px
    }
    
    # ── Shadow System ───────────────────────────────────────────────────────────
    shadows = {
        "sm": "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
        "md": "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
        "lg": "0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)",
        "xl": "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)",
    }
    
    # ── Border Radius ───────────────────────────────────────────────────────────
    radius = {
        "sm": "0.25rem",   # 4px
        "md": "0.375rem",  # 6px
        "lg": "0.5rem",    # 8px
        "xl": "0.75rem",   # 12px
        "2xl": "1rem",     # 16px
    }
    
    # ── Transitions ─────────────────────────────────────────────────────────────
    transitions = {
        "fast": "150ms cubic-bezier(0.4, 0, 0.2, 1)",
        "normal": "200ms cubic-bezier(0.4, 0, 0.2, 1)",
        "slow": "300ms cubic-bezier(0.4, 0, 0.2, 1)",
    }
    
    return f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    /* ── CSS Reset & Base ────────────────────────────────────────────────────── */
    *, *::before, *::after {{
        box-sizing: border-box;
        margin: 0;
        padding: 0;
    }}
    
    .stApp {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        background-color: {neutrals['50']};
        color: {neutrals['900']};
        line-height: 1.6;
    }}
    
    /* ── Typography System ───────────────────────────────────────────────────── */
    .stApp h1 {{
        font-size: {typography['h1']['size']};
        font-weight: {typography['h1']['weight']};
        line-height: {typography['h1']['line']};
        color: {neutrals['900']};
        margin-bottom: {spacing['lg']};
    }}
    
    .stApp h2 {{
        font-size: {typography['h2']['size']};
        font-weight: {typography['h2']['weight']};
        line-height: {typography['h2']['line']};
        color: {neutrals['900']};
        margin: {spacing['xl']} 0 {spacing['lg']} 0;
    }}
    
    .stApp h3 {{
        font-size: {typography['h3']['size']};
        font-weight: {typography['h3']['weight']};
        line-height: {typography['h3']['line']};
        color: {neutrals['900']};
        margin: {spacing['lg']} 0 {spacing['md']} 0;
    }}
    
    .stApp p, .stApp [data-testid="stMarkdownContainer"] p {{
        font-size: {typography['body']['size']};
        font-weight: {typography['body']['weight']};
        line-height: {typography['body']['line']};
        color: {neutrals['900']};
        margin-bottom: {spacing['md']};
    }}
    
    .stApp small, .stApp .caption {{
        font-size: {typography['small']['size']};
        font-weight: {typography['small']['weight']};
        line-height: {typography['small']['line']};
        color: {neutrals['500']};
    }}
    
    /* ── Layout Components ───────────────────────────────────────────────────── */
    .main-header {{
        background: white;
        border-bottom: 1px solid {neutrals['200']};
        padding: {spacing['lg']} {spacing['xl']};
        margin-bottom: {spacing['2xl']};
        box-shadow: {shadows['sm']};
    }}
    
    .content-section {{
        background: white;
        border-radius: {radius['lg']};
        padding: {spacing['xl']};
        margin-bottom: {spacing['lg']};
        box-shadow: {shadows['md']};
        border: 1px solid {neutrals['200']};
    }}
    
    .sidebar-section {{
        background: {neutrals['100']};
        border-radius: {radius['md']};
        padding: {spacing['lg']};
        margin-bottom: {spacing['md']};
        border: 1px solid {neutrals['200']};
    }}
    
    /* ── Button System ───────────────────────────────────────────────────────── */
    .btn-primary {{
        background: {primary['500']};
        color: white;
        border: none;
        border-radius: {radius['md']};
        padding: {spacing['sm']} {spacing['lg']};
        font-weight: 500;
        font-size: {typography['body']['size']};
        cursor: pointer;
        transition: all {transitions['normal']};
        box-shadow: {shadows['sm']};
    }}
    
    .btn-primary:hover {{
        background: {primary['600']};
        box-shadow: {shadows['md']};
        transform: translateY(-1px);
    }}
    
    .btn-secondary {{
        background: white;
        color: {neutrals['900']};
        border: 1px solid {neutrals['200']};
        border-radius: {radius['md']};
        padding: {spacing['sm']} {spacing['lg']};
        font-weight: 500;
        font-size: {typography['body']['size']};
        cursor: pointer;
        transition: all {transitions['normal']};
    }}
    
    .btn-secondary:hover {{
        background: {neutrals['100']};
        border-color: {neutrals['300']};
    }}
    
    /* ── Form Components ──────────────────────────────────────────────────────── */
    .form-group {{
        margin-bottom: {spacing['lg']};
    }}
    
    .form-label {{
        display: block;
        font-weight: 500;
        color: {neutrals['900']};
        margin-bottom: {spacing['xs']};
        font-size: {typography['small']['size']};
    }}
    
    .form-input {{
        width: 100%;
        padding: {spacing['sm']} {spacing['md']};
        border: 1px solid {neutrals['200']};
        border-radius: {radius['md']};
        font-size: {typography['body']['size']};
        transition: all {transitions['normal']};
        background: white;
    }}
    
    .form-input:focus {{
        outline: none;
        border-color: {primary['500']};
        box-shadow: 0 0 0 3px {primary['50']};
    }}
    
    /* ── Status Indicators ─────────────────────────────────────────────────────── */
    .status-success {{
        background: {semantic['success']}15;
        color: {semantic['success']};
        border: 1px solid {semantic['success']}30;
        border-radius: {radius['md']};
        padding: {spacing['sm']} {spacing['md']};
        font-size: {typography['small']['size']};
        font-weight: 500;
    }}
    
    .status-warning {{
        background: {semantic['warning']}15;
        color: {semantic['warning']};
        border: 1px solid {semantic['warning']}30;
        border-radius: {radius['md']};
        padding: {spacing['sm']} {spacing['md']};
        font-size: {typography['small']['size']};
        font-weight: 500;
    }}
    
    .status-error {{
        background: {semantic['error']}15;
        color: {semantic['error']};
        border: 1px solid {semantic['error']}30;
        border-radius: {radius['md']};
        padding: {spacing['sm']} {spacing['md']};
        font-size: {typography['small']['size']};
        font-weight: 500;
    }}
    
    /* ── Professional Sidebar ─────────────────────────────────────────────────── */
    [data-testid="stSidebar"] {{
        background: linear-gradient(180deg, {neutrals['900']} 0%, {neutrals['800']} 100%);
        border-right: 1px solid {neutrals['700']};
    }}
    
    .sidebar-header {{
        padding: {spacing['xl']};
        border-bottom: 1px solid {neutrals['700']};
        margin-bottom: {spacing['lg']};
    }}
    
    .sidebar-logo {{
        font-size: {typography['h2']['size']};
        font-weight: 700;
        color: white;
        text-align: center;
        margin-bottom: {spacing['sm']};
    }}
    
    .sidebar-logo span {{
        background: linear-gradient(135deg, {primary['500']}, {primary['100']});
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }}
    
    /* ── Stage Indicators ─────────────────────────────────────────────────────── */
    .stage-indicator {{
        display: flex;
        align-items: center;
        gap: {spacing['sm']};
        padding: {spacing['md']} {spacing['lg']};
        background: {primary['50']};
        border: 1px solid {primary['200']};
        border-radius: {radius['lg']};
        margin-bottom: {spacing['lg']};
    }}
    
    .stage-dot {{
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: {primary['500']};
    }}
    
    .stage-dot.active {{
        box-shadow: 0 0 0 4px {primary['100']};
    }}
    
    .stage-dot.completed {{
        background: {semantic['success']};
    }}
    
    /* ── Loading States ───────────────────────────────────────────────────────── */
    .loading-skeleton {{
        background: linear-gradient(90deg, {neutrals['200']} 25%, {neutrals['100']} 50%, {neutrals['200']} 75%);
        background-size: 200% 100%;
        animation: loading 1.5s infinite;
        border-radius: {radius['md']};
        height: 20px;
        margin-bottom: {spacing['sm']};
    }}
    
    @keyframes loading {{
        0% {{ background-position: 200% 0; }}
        100% {{ background-position: -200% 0; }}
    }}
    
    /* ── Responsive Design ───────────────────────────────────────────────────── */
    @media (max-width: 768px) {{
        .content-section {{
            padding: {spacing['lg']};
            margin-bottom: {spacing['md']};
        }}
        
        .main-header {{
            padding: {spacing['md']} {spacing['lg']};
        }}
        
        .stApp h1 {{
            font-size: {typography['h2']['size']};
        }}
        
        .stApp h2 {{
            font-size: {typography['h3']['size']};
        }}
    }}
    
    /* ── Streamlit Overrides ─────────────────────────────────────────────────── */
    .stButton > button {{
        background: {primary['500']} !important;
        color: white !important;
        border: none !important;
        border-radius: {radius['md']} !important;
        font-weight: 500 !important;
        transition: all {transitions['normal']} !important;
        box-shadow: {shadows['sm']} !important;
    }}
    
    .stButton > button:hover {{
        background: {primary['600']} !important;
        box-shadow: {shadows['md']} !important;
        transform: translateY(-1px) !important;
    }}
    
    .stSelectbox > div > div {{
        background: white !important;
        border: 1px solid {neutrals['200']} !important;
        border-radius: {radius['md']} !important;
    }}
    
    .stTextArea > div > div > textarea {{
        border: 1px solid {neutrals['200']} !important;
        border-radius: {radius['md']} !important;
        font-family: 'Inter', sans-serif !important;
    }}
    
    .stTextArea > div > div > textarea:focus {{
        border-color: {primary['500']} !important;
        box-shadow: 0 0 0 3px {primary['50']} !important;
    }}
    
    /* ── Professional Animations ───────────────────────────────────────────────── */
    .fade-in {{
        animation: fadeIn 0.3s ease-in;
    }}
    
    @keyframes fadeIn {{
        from {{ opacity: 0; transform: translateY(10px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}
    
    .slide-up {{
        animation: slideUp 0.4s ease-out;
    }}
    
    @keyframes slideUp {{
        from {{ opacity: 0; transform: translateY(20px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}
    
    </style>
    """
