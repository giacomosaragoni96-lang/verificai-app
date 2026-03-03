def get_css(T: dict) -> str:
    """
    Restituisce il CSS dell'app adattato dinamicamente al tema T.
    Tutti i colori vengono estratti dal dizionario T passato come argomento.

    DESIGN SYSTEM v2 — Principi:
    • Gerarchia visiva con accenti di colore mirati (no "tutto bianco" / "tutto nero")
    • Font grandi e leggibili per docenti non tecnici
    • Effetti di caricamento professionali
    • Linguaggio non tecnico (hint, label)
    """
    _SB_ACCENT = T.get("sidebar_accent", "#D97706")
    _SB_BG_CSS = T.get("sidebar_bg", "linear-gradient(180deg, #111110 0%, #0e0e0d 100%)")
    _SB_BORDER = T.get("sidebar_border", "#252420")
    _SB_MUTED  = "#8a8880"
    _SB_TEXT   = "#e8e6e0"

    _is_light = _is_light_color(T["bg"])
    _btn_primary_bg = T["accent"]

    # Accent derived colors
    _acc = T["accent"]
    _acc_soft = _acc + "18"
    _acc_med  = _acc + "33"
    _acc_ring = _acc + "44"

    # Surface elevation tokens
    _surf_raised = T.get("card", T["bg2"])
    _surf_overlay = T.get("card2", T["bg2"])

    return f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;0,800;0,900;1,400&display=swap');
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

  *, *::before, *::after {{ box-sizing: border-box; }}

  .stApp {{
    background-color: {T['bg']} !important;
    font-family: 'DM Sans', 'Inter', sans-serif;
    color: {T['text']};
    transition: background-color 0.3s ease, color 0.3s ease;
  }}

  .block-container {{
    padding: 4.5rem 1.5rem 4rem !important;
    max-width: 1400px !important;
    margin: 0 auto !important;
  }}

  #MainMenu, footer {{ visibility: hidden; }}
  .stDecoration {{ display: none; }}

  header[data-testid="stHeader"] {{
    background-color: {T['bg']}ee !important;
    backdrop-filter: blur(12px) !important;
    -webkit-backdrop-filter: blur(12px) !important;
    border-bottom: 1px solid {T['border']} !important;
  }}

  header button svg {{
    fill: {T['text']} !important;
    color: {T['text']} !important;
    stroke: {T['text']} !important;
  }}
  header button {{
    background: {T['card']} !important;
    border: 1.5px solid {T['border2']} !important;
    border-radius: 8px !important;
    color: {T['text']} !important;
  }}
  header button:hover {{
    background: {T['hover']} !important;
    border-color: {_acc} !important;
  }}
  header button:hover svg {{
    fill: {_acc} !important;
  }}
  .stMarkdown h1 a, .stMarkdown h2 a, .stMarkdown h3 a {{ display: none !important; }}

  /* ════════════════════════════════════════════════════════════════════════
     SIDEBAR — Fixed Dark Premium
     ════════════════════════════════════════════════════════════════════════ */
  [data-testid="stSidebar"] {{
    background: {_SB_BG_CSS} !important;
    border-right: 1px solid {_SB_BORDER} !important;
  }}
  .sidebar-title {{
    font-family: 'DM Sans', sans-serif;
    font-size: .95rem !important;
    font-weight: 800 !important;
    letter-spacing: -0.01em;
    color: #f5f3ed !important;
    margin: 0 0 1.2rem 0;
    padding: .6rem 0 .8rem 0;
    border-bottom: 1px solid {_SB_BORDER};
    display: flex;
    align-items: center;
    gap: 7px;
  }}
  [data-testid="stSidebar"] .block-container {{
    padding: 1.4rem 1.1rem !important;
    max-width: 100% !important;
  }}
  [data-testid="stSidebar"] p,
  [data-testid="stSidebar"] span,
  [data-testid="stSidebar"] label,
  [data-testid="stSidebar"] div {{
    color: {_SB_TEXT} !important;
  }}
  [data-testid="stSidebar"] .stTextInput label p,
  [data-testid="stSidebar"] .stSelectbox label p,
  [data-testid="stSidebar"] .stNumberInput label p {{
    color: {_SB_MUTED} !important;
    font-size: 0.7rem !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    font-weight: 700 !important;
  }}
  [data-testid="stSidebar"] .stCheckbox label {{
    color: {_SB_TEXT} !important;
    font-size: 0.9rem !important;
  }}
  [data-testid="stSidebar"] .stTextInput input,
  [data-testid="stSidebar"] .stNumberInput input {{
    background: #1a1916 !important;
    border: 1px solid {_SB_BORDER} !important;
    border-radius: 8px !important;
    color: #f5f3ed !important;
    font-size: 0.88rem !important;
  }}
  [data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] > div:first-child {{
    background: #1a1916 !important;
    border: 1px solid {_SB_BORDER} !important;
    border-radius: 8px !important;
  }}
  [data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] span {{
    color: #e8e6e0 !important;
    font-size: 0.88rem !important;
  }}
  [data-testid="stSidebar"] .stRadio label,
  [data-testid="stSidebar"] .stRadio [data-testid="stMarkdownContainer"] p {{
    color: {_SB_TEXT} !important;
  }}
  [data-testid="stSidebar"] .stButton button {{
    background: #1c1b18 !important;
    color: #d8d6ce !important;
    border: 1px solid {_SB_BORDER} !important;
    border-radius: 8px !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
  }}
  [data-testid="stSidebar"] .stButton button:hover {{
    background: #28261f !important;
    border-color: {_SB_ACCENT} !important;
    color: #f5f3ed !important;
  }}
  [data-testid="stSidebar"] .stSelectSlider [data-testid="stMarkdownContainer"] p {{
    color: {_SB_TEXT} !important;
  }}
  [data-testid="stSidebar"] .section-label {{
    color: #4a4840 !important;
    border-bottom-color: {_SB_BORDER} !important;
  }}

  /* Sidebar toggle button */
  [data-testid="collapsedControl"] {{
    top: 0.75rem !important;
    left: 0.75rem !important;
    z-index: 999 !important;
  }}
  [data-testid="collapsedControl"] button {{
    background: {T['card']} !important;
    border: 2px solid {_acc} !important;
    border-radius: 10px !important;
    color: {_acc} !important;
    width: 40px !important;
    height: 40px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    box-shadow: 0 2px 12px {_acc_med} !important;
    transition: transform 0.15s ease, box-shadow 0.15s ease, background 0.15s ease !important;
    padding: 0 !important;
  }}
  [data-testid="collapsedControl"] button:hover {{
    background: {_acc} !important;
    box-shadow: 0 4px 18px {_acc_ring} !important;
    transform: scale(1.08) !important;
  }}
  [data-testid="collapsedControl"] button:hover svg {{
    fill: #ffffff !important;
    color: #ffffff !important;
    stroke: #ffffff !important;
  }}
  [data-testid="collapsedControl"] button svg {{
    fill: {_acc} !important;
    color: {_acc} !important;
    stroke: {_acc} !important;
    width: 18px !important;
    height: 18px !important;
  }}

  [data-testid="stSidebar"] .sidebar-label,
  .sidebar-label {{
    font-size: 0.65rem !important;
    font-weight: 800 !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
    color: {_SB_ACCENT} !important;
    margin: 1.1rem 0 0.45rem 0 !important;
    font-family: 'DM Sans', sans-serif !important;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     HERO / HEADER
     ════════════════════════════════════════════════════════════════════════ */
  .hero-wrap {{
    display: flex; align-items: center; justify-content: space-between;
    margin-bottom: 1.8rem; padding: 0 0 1rem 0;
    border-bottom: 1px solid {T['border']};
  }}
  .hero-left {{
    display: flex; flex-direction: column; gap: 4px;
  }}
  .hero-title {{
    font-family: 'DM Sans', sans-serif;
    font-size: 1.7rem; font-weight: 900; line-height: 1.1;
    letter-spacing: -0.03em;
    color: {T['text']};
    display: flex; align-items: center; gap: 8px;
    margin: 0; padding: 0;
  }}
  .hero-icon {{ font-size: 1.5rem; }}
  .hero-ai {{
    background: linear-gradient(135deg, {_acc}, {T.get('accent2', _acc)});
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }}
  .hero-sub {{
    font-size: .85rem; color: {T['text2']};
    margin: 0; font-weight: 400; line-height: 1.4;
  }}
  .hero-beta {{
    display: inline-block;
    font-size: .6rem; font-weight: 700;
    letter-spacing: .08em; text-transform: uppercase;
    background: {_acc_soft};
    color: {_acc}; border: 1px solid {_acc_ring};
    border-radius: 20px; padding: 2px 10px;
    margin-top: 4px;
  }}

  .sidebar-hint-inline {{
    font-size: .7rem; color: {T['muted']};
    font-family: 'DM Sans', sans-serif;
    margin-bottom: .2rem;
    opacity: .7;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     GLOBAL — Form Inputs
     ════════════════════════════════════════════════════════════════════════ */
  [data-testid="stTextInput"] input,
  [data-testid="stTextArea"] textarea {{
    background: {_surf_overlay} !important;
    border: 1.5px solid {T['border']} !important;
    border-radius: 10px !important;
    color: {T['text']} !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: .92rem !important;
    padding: 12px 14px !important;
    transition: border-color .2s ease, box-shadow .2s ease !important;
  }}
  [data-testid="stTextInput"] input:focus,
  [data-testid="stTextArea"] textarea:focus {{
    border-color: {_acc} !important;
    box-shadow: 0 0 0 3px {_acc_soft} !important;
    outline: none !important;
  }}
  [data-testid="stTextInput"] input::placeholder,
  [data-testid="stTextArea"] textarea::placeholder {{
    color: {T['muted']} !important; opacity: .8 !important;
  }}

  [data-testid="stSelectbox"] [data-baseweb="select"] > div:first-child {{
    background: {_surf_overlay} !important;
    border: 1.5px solid {T['border2']} !important;
    border-radius: 10px !important;
    box-shadow: 0 1px 3px rgba(0,0,0,.06) !important;
  }}
  [data-testid="stSelectbox"] [data-baseweb="select"] > div:first-child:focus-within,
  [data-testid="stSelectbox"] [data-baseweb="select"] > div:first-child:hover {{
    border-color: {_acc} !important;
    box-shadow: 0 0 0 3px {_acc_soft} !important;
  }}
  [data-testid="stSelectbox"] [data-baseweb="select"] span {{
    color: {T['text']} !important;
    font-size: .92rem !important;
    font-family: 'DM Sans', sans-serif !important;
  }}
  /* Dropdown option list */
  [data-baseweb="popover"] [data-baseweb="menu"] {{
    background: {T['card']} !important;
    border: 1.5px solid {T['border2']} !important;
    border-radius: 10px !important;
    box-shadow: 0 8px 32px rgba(0,0,0,.12) !important;
  }}
  [data-baseweb="popover"] [role="option"] {{
    background: {T['card']} !important;
    color: {T['text']} !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: .9rem !important;
  }}
  [data-baseweb="popover"] [role="option"]:hover,
  [data-baseweb="popover"] [aria-selected="true"] {{
    background: {_acc_soft} !important;
    color: {_acc} !important;
  }}

  .stCheckbox label span[data-baseweb="checkbox"] {{
    border-color: {T['border2']} !important;
  }}

  /* Labels */
  [data-testid="stTextInput"] label p,
  [data-testid="stTextArea"] label p,
  [data-testid="stSelectbox"] label p {{
    color: {T['text2']} !important;
    font-size: .82rem !important;
    font-weight: 600 !important;
    font-family: 'DM Sans', sans-serif !important;
  }}

  /* Toggle */
  [data-testid="stCheckbox"] label {{
    font-size: .88rem !important;
    font-family: 'DM Sans', sans-serif !important;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     BUTTONS — Primary & Secondary
     ════════════════════════════════════════════════════════════════════════ */
  div.stButton > button[kind="primary"],
  div.stButton > button[data-testid="stBaseButton-primary"] {{
    background: linear-gradient(135deg, {_acc}, {T.get('accent2', _acc)}) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 12px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 800 !important;
    font-size: .95rem !important;
    min-height: 50px !important;
    letter-spacing: -.01em !important;
    box-shadow: 0 4px 20px {_acc_ring} !important;
    transition: filter .15s ease, box-shadow .2s ease, transform .15s ease !important;
  }}
  div.stButton > button[kind="primary"]:hover,
  div.stButton > button[data-testid="stBaseButton-primary"]:hover {{
    filter: brightness(1.08) !important;
    box-shadow: 0 6px 28px {_acc}55 !important;
    transform: translateY(-1px) !important;
  }}
  div.stButton > button[kind="primary"]:active {{
    transform: translateY(0) !important;
    box-shadow: 0 2px 12px {_acc_med} !important;
  }}
  div.stButton > button[kind="primary"]:disabled {{
    opacity: .45 !important;
    box-shadow: none !important;
    filter: none !important;
    transform: none !important;
  }}

  div.stButton > button[kind="secondary"],
  div.stButton > button:not([kind="primary"]) {{
    background: {_surf_raised} !important;
    color: {T['text']} !important;
    border: 1.5px solid {T['border']} !important;
    border-radius: 10px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 600 !important;
    font-size: .88rem !important;
    min-height: 44px !important;
    transition: background .15s ease, border-color .15s ease, box-shadow .15s ease !important;
  }}
  div.stButton > button[kind="secondary"]:hover,
  div.stButton > button:not([kind="primary"]):hover {{
    background: {T['hover']} !important;
    border-color: {_acc} !important;
    box-shadow: 0 2px 12px {_acc_soft} !important;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     PROGRESS BAR (Breadcrumb)
     ════════════════════════════════════════════════════════════════════════ */
  .breadcrumb-wrap {{
    display: flex; justify-content: center; margin-bottom: 1.6rem;
  }}
  .breadcrumb-pill {{
    display: inline-flex; align-items: center; gap: 10px;
    padding: .7rem 1.6rem;
    background: {T['card']};
    border: 1.5px solid {T['border']};
    border-radius: 100px;
    box-shadow: {T.get('shadow_md', '0 4px 20px rgba(0,0,0,.08)')};
  }}

  /* ════════════════════════════════════════════════════════════════════════
     HOME LANDING
     ════════════════════════════════════════════════════════════════════════ */
  .home-landing-wrap {{
    text-align: center;
    margin-bottom: 2rem;
    padding: 1.2rem 0 .5rem;
  }}
  .home-landing-title {{
    font-family: 'DM Sans', sans-serif;
    font-size: 1.6rem;
    font-weight: 900;
    letter-spacing: -0.03em;
    color: {T['text']};
    margin-bottom: .5rem;
  }}
  .home-landing-desc {{
    font-size: .92rem;
    color: {T['text2']};
    font-family: 'DM Sans', sans-serif;
    max-width: 520px;
    margin: 0 auto;
    line-height: 1.55;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     LANDING HERO — Logo MOLTO GRANDE + headline centrati
     ════════════════════════════════════════════════════════════════════════ */

  /* Wrapper unico centrato — tutto in una colonna */
  .landing-hero-unified {{
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    padding: 3rem 1rem 1.2rem;
    max-width: 800px;
    margin: 0 auto;
  }}

  /* Riga logo: emoji + nome + badge */
  .landing-logo-row {{
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 14px;
    margin-bottom: 1.6rem;
  }}
  .landing-logo-icon-xl {{
    font-size: 3.6rem;
    line-height: 1;
  }}
  .landing-logo-name-xl {{
    font-family: 'DM Sans', sans-serif;
    font-size: clamp(2.4rem, 6vw, 3.8rem);
    font-weight: 900;
    letter-spacing: -0.05em;
    color: {T['text']};
    line-height: 1;
  }}
  .landing-logo-ai-xl {{
    background: linear-gradient(135deg, {_acc}, {T.get('accent2', _acc)});
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }}
  .landing-logo-beta-xl {{
    font-size: .62rem;
    font-weight: 800;
    letter-spacing: .1em;
    text-transform: uppercase;
    background: {_acc_soft};
    color: {_acc};
    border: 1px solid {_acc_med};
    border-radius: 20px;
    padding: 4px 10px;
    align-self: flex-start;
    margin-top: 6px;
    font-family: 'DM Sans', sans-serif;
  }}

  /* Headline grande */
  .landing-headline-xl {{
    font-family: 'DM Sans', sans-serif;
    font-size: clamp(2rem, 4.5vw, 3rem);
    font-weight: 900;
    line-height: 1.12;
    letter-spacing: -0.04em;
    color: {T['text']};
    margin: 0 0 1.1rem 0;
    padding: 0;
    text-align: center;
  }}
  .landing-headline-accent-xl {{
    background: linear-gradient(135deg, {_acc}, {T.get('accent2', _acc)}cc);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }}

  /* Sottotitolo — centrato, leggibile */
  .landing-sub-xl {{
    font-size: 1.05rem;
    color: {T['text2']};
    font-family: 'DM Sans', sans-serif;
    line-height: 1.65;
    text-align: center;
    max-width: 480px;
    margin: 0 auto 0;
  }}

  /* Classi legacy mantenute per compatibilità */
  .landing-logo-wrap {{ display:none; }}
  .tally-hero {{ text-align:center; padding:2rem 1rem 1.4rem; max-width:700px; margin:0 auto; }}
  .tally-eyebrow {{ display:none; }}
  .tally-headline {{
    font-family:'DM Sans',sans-serif; font-size:clamp(2.2rem,5vw,3.2rem);
    font-weight:900; line-height:1.1; letter-spacing:-0.04em;
    color:{T['text']}; margin:0 0 1.1rem 0; padding:0;
  }}
  .tally-headline-accent {{
    background:linear-gradient(135deg,{_acc},{T.get('accent2',_acc)}cc);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;
  }}
  .tally-sub {{
    font-size:1rem; color:{T['text2']}; font-family:'DM Sans',sans-serif;
    line-height:1.6; margin:0 auto; max-width:480px; text-align:center;
  }}

  /* CTA button wrapper */
  .tally-cta-wrap {{
    margin: 1.8rem auto .5rem;
    max-width: 420px;
  }}
  .tally-cta-wrap button[kind="primary"],
  .tally-cta-wrap button[data-testid="baseButton-primary"] {{
    font-size: 1.05rem !important;
    font-weight: 800 !important;
    padding: .85rem 2rem !important;
    height: auto !important;
    min-height: 54px !important;
    border-radius: 14px !important;
    letter-spacing: -.01em !important;
    box-shadow: 0 6px 28px {_acc}44 !important;
    transition: transform .15s ease, box-shadow .15s ease !important;
  }}
  .tally-cta-wrap button[kind="primary"]:hover,
  .tally-cta-wrap button[data-testid="baseButton-primary"]:hover {{
    transform: translateY(-2px) !important;
    box-shadow: 0 10px 36px {_acc}55 !important;
  }}

  /* Feature strip */
  .tally-features {{
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: center;
    gap: 6px 4px;
    margin: 1.4rem auto 0;
    max-width: 640px;
    padding-bottom: .5rem;
  }}
  .tally-feat {{
    font-size: .75rem;
    font-weight: 600;
    font-family: 'DM Sans', sans-serif;
    color: {T['text2']};
    white-space: nowrap;
  }}
  .tally-feat-sep {{
    font-size: .75rem;
    color: {T['border2']};
    margin: 0 2px;
  }}

  /* Feature pill-cards — landing page */
  .feature-pills-row {{
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: center;
    gap: 10px 8px;
    margin: 1.4rem 0 0;
    width: 100%;
    padding-bottom: .5rem;
  }}
  .feature-pill {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: {T['card']};
    border: 1.5px solid {T['border']};
    border-radius: 100px;
    padding: 5px 14px 5px 10px;
    box-shadow: 0 1px 4px rgba(0,0,0,.06);
    transition: transform .12s ease, box-shadow .12s ease;
  }}
  .feature-pill:hover {{
    transform: translateY(-1px);
    box-shadow: 0 3px 10px rgba(0,0,0,.10);
  }}
  .feature-pill-icon {{
    font-size: 1rem;
    line-height: 1;
  }}
  .feature-pill-label {{
    font-size: .8rem;
    font-weight: 700;
    font-family: 'DM Sans', sans-serif;
    color: {T['text']};
    white-space: nowrap;
  }}

  /* Social proof (compatibilità) */
  .tally-proof {{ display: none; }}
  .tally-proof-dot {{ display: none; }}

  /* ════════════════════════════════════════════════════════════════════════
     CHOICE CARDS — Bivio iniziale "Parto da zero" / "Ho già una verifica"
     ════════════════════════════════════════════════════════════════════════ */
  .choice-card {{
    background: {T['card']};
    border: 2px solid {T['border2']};
    border-radius: 20px;
    padding: 1.6rem 1.4rem 1.1rem;
    display: flex;
    flex-direction: column;
    gap: .55rem;
    min-height: 190px;
    transition: border-color .2s ease, box-shadow .2s ease, transform .15s ease;
    margin-bottom: .65rem;
    animation: fadeSlideUp .3s ease both;
  }}
  .choice-card:hover {{
    transform: translateY(-2px);
    box-shadow: 0 8px 32px rgba(0,0,0,.10);
  }}
  .choice-card-primary {{
    border-color: {_acc}55;
    box-shadow: 0 2px 16px {_acc}14;
  }}
  .choice-card-primary:hover {{
    border-color: {_acc}99;
    box-shadow: 0 8px 32px {_acc}22;
  }}
  .choice-card-secondary {{
    border-color: {T['border2']};
  }}
  .choice-card-icon {{
    font-size: 2rem;
    line-height: 1;
  }}
  .choice-card-title {{
    font-family: 'DM Sans', sans-serif;
    font-size: 1.1rem;
    font-weight: 900;
    letter-spacing: -.02em;
    color: {T['text']};
    line-height: 1.15;
  }}
  .choice-card-desc {{
    font-size: .83rem;
    color: {T['text2']};
    font-family: 'DM Sans', sans-serif;
    line-height: 1.55;
    flex: 1;
  }}
  .choice-card-chips {{
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
    margin-top: .1rem;
  }}
  .choice-chip {{
    font-size: .65rem;
    font-weight: 700;
    font-family: 'DM Sans', sans-serif;
    letter-spacing: .02em;
    background: {_acc_soft};
    color: {_acc};
    border: 1px solid {_acc_ring};
    border-radius: 20px;
    padding: 2px 9px;
    white-space: nowrap;
  }}
  .choice-card-secondary .choice-chip {{
    background: {T.get('card2', T['card'])};
    color: {T['text2']};
    border-color: {T['border']};
  }}

  /* ════════════════════════════════════════════════════════════════════════
     BREADCRUMB STEPS — Nativo st.columns con bottoni reali
     ════════════════════════════════════════════════════════════════════════ */
  .breadcrumb-wrap {{
    margin: .8rem 0 .6rem;
    padding: .1rem 0;
  }}

  /* Step completato — avvolge il bottone Streamlit */
  .bc-step-done button,
  .bc-step-done [data-testid="baseButton-secondary"] {{
    background: {T.get('card2', T['card'])} !important;
    border: 1.5px solid {T['success']}55 !important;
    color: {T['success']} !important;
    font-size: .78rem !important;
    font-weight: 700 !important;
    font-family: 'DM Sans', sans-serif !important;
    border-radius: 100px !important;
    padding: .25rem .6rem !important;
    min-height: 32px !important;
    height: 32px !important;
    letter-spacing: .01em !important;
    transition: background .15s, border-color .15s, transform .12s !important;
  }}
  .bc-step-done button:hover,
  .bc-step-done [data-testid="baseButton-secondary"]:hover {{
    background: {T['success']}18 !important;
    border-color: {T['success']}99 !important;
    transform: translateY(-1px) !important;
  }}

  /* Step attivo */
  .bc-step-active {{
    display: flex;
    align-items: center;
    gap: 7px;
    padding: .25rem .3rem;
  }}
  .bc-num {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 24px; height: 24px;
    border-radius: 50%;
    background: {_acc};
    color: #fff;
    font-size: .68rem; font-weight: 800;
    flex-shrink: 0;
    box-shadow: 0 2px 8px {_acc}44;
  }}
  .bc-label {{
    font-size: .82rem; font-weight: 800;
    color: {_acc};
    font-family: 'DM Sans', sans-serif;
    white-space: nowrap;
  }}

  /* Step futuro */
  .bc-step-future {{
    display: flex;
    align-items: center;
    gap: 7px;
    padding: .25rem .3rem;
    opacity: .35;
  }}
  .bc-num-future {{
    background: {T['border2']};
    color: {T['muted']};
    box-shadow: none;
  }}
  .bc-label-future {{
    color: {T['muted']};
    font-weight: 500;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     SIDE-BOX — Colonna destra form (sostituisce facsimile-shortcut + side-panel-card)
     ════════════════════════════════════════════════════════════════════════ */
  .side-box {{
    background: {T['card']};
    border: 1.5px solid {T['border2']};
    border-radius: 14px;
    padding: 1rem 1.1rem .9rem;
    margin-bottom: .5rem;
    box-shadow: {T.get('shadow', '0 1px 3px rgba(0,0,0,.04)')};
  }}
  .side-box-header {{
    margin-bottom: .45rem;
  }}
  .side-box-badge {{
    font-size: .58rem;
    font-weight: 800;
    letter-spacing: .08em;
    text-transform: uppercase;
    border-radius: 20px;
    padding: 3px 9px;
    display: inline-block;
  }}
  .side-box-badge-violet {{
    background: #7C3AED18;
    color: #8B5CF6;
    border: 1px solid #7C3AED33;
  }}
  .side-box-title {{
    font-size: .88rem;
    font-weight: 800;
    color: {T['text']};
    font-family: 'DM Sans', sans-serif;
    margin-bottom: .35rem;
  }}
  .side-box-title-flex {{
    display: flex;
    align-items: center;
    gap: 8px;
  }}
  .side-box-dot {{
    width: 7px; height: 7px;
    border-radius: 50%;
    background: {_acc};
    box-shadow: 0 0 6px {_acc_med};
    flex-shrink: 0;
  }}
  .side-box-desc {{
    font-size: .78rem;
    color: {T['text2']};
    font-family: 'DM Sans', sans-serif;
    line-height: 1.55;
  }}

  /* ── File AI summary (cosa ha capito l'AI) ── */
  .file-ai-summary {{
    display: flex;
    align-items: flex-start;
    gap: 6px;
    background: {_acc_soft};
    border: 1px solid {_acc_med};
    border-radius: 8px;
    padding: .4rem .7rem;
    margin: .35rem 0 .45rem;
    font-size: .74rem;
    color: {T['text2']};
    font-family: 'DM Sans', sans-serif;
    line-height: 1.45;
  }}
  .file-ai-summary-icon {{
    flex-shrink: 0;
    font-size: .82rem;
    margin-top: .05rem;
  }}
  .file-ai-summary-text {{
    flex: 1;
  }}

  /* ── Hint "esercizio da inserire" ── */
  .file-includi-hint {{
    background: {T.get('hint_bg', '#FEF3C7')};
    border: 1px solid {T.get('hint_border', '#FDE68A')};
    border-radius: 8px;
    padding: .45rem .75rem;
    margin: .3rem 0 .4rem;
    font-size: .74rem;
    color: {T.get('hint_text', '#92400E')};
    font-family: 'DM Sans', sans-serif;
    line-height: 1.5;
  }}

  /* ── Percorso Card ── */
  .mcard {{
    background: {T['card']};
    border: 2px solid {T['border2']};
    border-radius: 16px;
    padding: 1.3rem 1.2rem 1.1rem;
    position: relative;
    transition: border-color .2s ease, box-shadow .2s ease, transform .2s ease;
    min-height: 220px;
    display: flex;
    flex-direction: column;
    gap: .4rem;
  }}
  .mcard:hover {{
    transform: translateY(-2px);
    box-shadow: 0 8px 32px rgba(0,0,0,.08);
  }}
  .mcard-badge {{
    position: absolute; top: -10px; right: 14px;
    font-size: .6rem; font-weight: 800;
    letter-spacing: .06em; text-transform: uppercase;
    padding: 3px 10px;
    border-radius: 20px;
    color: #fff;
  }}
  .mcard-icon {{
    font-size: 1.6rem;
    margin-bottom: .2rem;
  }}
  .mcard-title {{
    font-family: 'DM Sans', sans-serif;
    font-size: 1.05rem;
    font-weight: 900;
    letter-spacing: -0.01em;
  }}
  .mcard-desc {{
    font-size: .82rem;
    color: {T['text2']};
    font-family: 'DM Sans', sans-serif;
    line-height: 1.55;
    flex: 1;
  }}
  .mcard-hint {{
    font-size: .72rem;
    color: {T['muted']};
    font-style: italic;
    line-height: 1.4;
    margin-top: .3rem;
  }}
  .mcard-chips {{
    display: flex; flex-wrap: wrap; gap: 6px;
    margin-top: .5rem;
  }}
  .mcard-chip {{
    font-size: .65rem;
    font-weight: 600;
    font-family: 'DM Sans', sans-serif;
    background: {_surf_overlay};
    border: 1px solid {T['border']};
    border-radius: 20px;
    padding: 3px 10px;
    color: {T['text2']};
    white-space: nowrap;
  }}

  /* ── Facsimile Card — Viola/Accento speciale ── */
  .fac-card {{
    background: linear-gradient(135deg, #7C3AED14, {T['card']});
    border: 2px solid #7C3AED44;
    border-radius: 18px;
    padding: 1.1rem 1.4rem;
    display: flex;
    align-items: center;
    gap: 1rem;
    transition: border-color .2s ease, box-shadow .2s ease;
  }}
  .fac-card:hover {{
    border-color: #7C3AED88;
    box-shadow: 0 4px 24px #7C3AED22;
  }}
  .fac-badge {{
    font-size: .6rem; font-weight: 800;
    letter-spacing: .08em; text-transform: uppercase;
    color: #A78BFA;
    margin-bottom: .15rem;
  }}
  .fac-title {{
    font-family: 'DM Sans', sans-serif;
    font-size: 1.05rem;
    font-weight: 900;
    color: {T['text']};
    margin-bottom: .15rem;
  }}
  .fac-desc {{
    font-size: .82rem;
    color: {T['text2']};
    font-family: 'DM Sans', sans-serif;
    line-height: 1.5;
  }}

  /* viola button override */
  .mbtn-viola button {{
    background: linear-gradient(135deg,#7C3AED,#6D28D9) !important;
    color: #fff !important; border: none !important;
    border-radius: 12px !important; font-weight: 700 !important;
    font-size: .92rem !important;
    box-shadow: 0 4px 20px #7C3AED44 !important;
  }}
  .mbtn-viola button:hover {{
    background: linear-gradient(135deg,#A78BFA,#7C3AED) !important;
    box-shadow: 0 6px 28px #7C3AED66 !important;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     FORM SECTION HEADERS — Percorso B
     ════════════════════════════════════════════════════════════════════════ */
  .form-section-header {{
    display: flex; align-items: center; gap: 10px;
    margin-bottom: .6rem;
  }}
  .form-section-dot {{
    width: 8px; height: 8px;
    border-radius: 50%;
    background: {_acc};
    flex-shrink: 0;
    box-shadow: 0 0 8px {_acc_med};
  }}
  .form-section-title {{
    font-size: .75rem; font-weight: 800;
    letter-spacing: .07em;
    text-transform: uppercase;
    color: {T['text']};
    font-family: 'DM Sans', sans-serif;
    white-space: nowrap;
  }}
  .form-section-line {{
    flex: 1; height: 1px;
    background: linear-gradient(90deg, {T['border2']}, transparent);
  }}

  .opt-label {{
    font-size: .72rem;
    font-weight: 800;
    letter-spacing: .06em;
    text-transform: uppercase;
    color: {T['muted']};
    font-family: 'DM Sans', sans-serif;
    margin-bottom: 4px;
  }}

  /* ── Sistema tipografico globale unificato ── */
  .type-eyebrow {{
    font-size: .68rem; font-weight: 800;
    letter-spacing: .1em; text-transform: uppercase;
    color: {T['muted']};
    font-family: 'DM Sans', sans-serif;
    margin-bottom: .3rem;
  }}
  .type-section-heading {{
    font-size: 1rem; font-weight: 900;
    letter-spacing: -.02em;
    color: {T['text']};
    font-family: 'DM Sans', sans-serif;
    line-height: 1.2;
    margin: 0 0 .35rem 0;
  }}
  .type-body {{
    font-size: .85rem; font-weight: 400;
    color: {T['text2']};
    font-family: 'DM Sans', sans-serif;
    line-height: 1.6;
  }}
  .type-hint {{
    font-size: .72rem; font-weight: 500;
    color: {T['muted']};
    font-family: 'DM Sans', sans-serif;
    font-style: italic;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     ONBOARDING HINT BANNER (Percorso B top)
     ════════════════════════════════════════════════════════════════════════ */
  .onboarding-hint-banner {{
    display: flex;
    align-items: flex-start;
    gap: 1rem;
    background: linear-gradient(135deg, {_acc_soft}, {T['card']});
    border: 1.5px solid {_acc_ring};
    border-radius: 16px;
    padding: 1rem 1.3rem;
    margin-bottom: 1.2rem;
  }}
  .onboarding-hint-icon {{
    font-size: 1.4rem;
    flex-shrink: 0;
    padding-top: 2px;
  }}
  .onboarding-hint-body {{
    flex: 1;
  }}
  .onboarding-hint-title {{
    font-size: .92rem;
    font-weight: 800;
    color: {T['text']};
    font-family: 'DM Sans', sans-serif;
    margin-bottom: .3rem;
    line-height: 1.3;
  }}
  .onboarding-hint-desc {{
    font-size: .8rem;
    color: {T['text2']};
    font-family: 'DM Sans', sans-serif;
    line-height: 1.55;
  }}
  .onboarding-hint-tags {{
    display: flex; flex-wrap: wrap; gap: 6px; margin-top: .5rem;
  }}
  .onboarding-hint-tag {{
    font-size: .65rem; font-weight: 600;
    background: {T['card']};
    border: 1px solid {T['border']};
    border-radius: 20px;
    padding: 3px 10px;
    color: {T['text2']};
  }}

  /* ════════════════════════════════════════════════════════════════════════
     CTA GENERA — High Impact Button Wrap
     ════════════════════════════════════════════════════════════════════════ */
  .cta-genera-wrap button {{
    min-height: 56px !important;
    font-size: 1.05rem !important;
    font-weight: 900 !important;
    letter-spacing: -.01em !important;
    border-radius: 14px !important;
  }}
  .cta-hint-above {{
    display: flex; align-items: center; justify-content: center;
    gap: .4rem;
    font-size: .76rem;
    color: {T['muted']};
    font-family: 'DM Sans', sans-serif;
    margin-bottom: .55rem;
    text-align: center;
  }}
  .cta-hint-below {{
    display: flex; align-items: center; justify-content: center;
    gap: .4rem;
    font-size: .76rem;
    color: {T['muted']};
    font-family: 'DM Sans', sans-serif;
    margin-top: .4rem;
    text-align: center;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     BACK BUTTON micro — piccolo, muted, in fondo
     ════════════════════════════════════════════════════════════════════════ */
  /* Stile per il pulsante "← Indietro" in fondo al form (colonne plain) */
  [data-testid="stHorizontalBlock"] .stButton button[data-testid*="btn_back"],
  .stButton > button[data-testid*="btn_back"] {{
    background: transparent !important;
    color: {T['muted']} !important;
    border: 1px solid {T['border']} !important;
    font-size: .78rem !important;
    font-weight: 500 !important;
    min-height: 30px !important;
    padding: 0 .7rem !important;
    box-shadow: none !important;
    border-radius: 8px !important;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     SIDE PANEL — Right column
     ════════════════════════════════════════════════════════════════════════ */
  .side-panel-card {{
    background: {_surf_raised};
    border: 1.5px solid {T['border']};
    border-radius: 14px;
    padding: .85rem 1rem .6rem;
    margin-bottom: .3rem;
  }}
  .side-panel-card-title {{
    font-size: .82rem; font-weight: 800;
    color: {T['text']};
    font-family: 'DM Sans', sans-serif;
    display: flex; align-items: center; gap: 8px;
  }}
  .side-panel-card-title-dot {{
    width: 6px; height: 6px;
    border-radius: 50%;
    background: {_acc};
    box-shadow: 0 0 6px {_acc_med};
  }}

  .upload-hint-compact {{
    font-size: .78rem;
    color: {T['text2']};
    font-family: 'DM Sans', sans-serif;
    line-height: 1.5;
    padding: .4rem 0 .6rem;
  }}

  .file-uploader-compact {{
    margin-bottom: .5rem;
  }}
  .file-uploader-compact [data-testid="stFileUploader"] {{
    border-radius: 12px !important;
  }}

  /* ═══ Facsimile Shortcut (sidebar col) ═══ */
  .facsimile-shortcut {{
    background: linear-gradient(135deg, #7C3AED12, {T['card']});
    border: 1.5px solid #7C3AED33;
    border-radius: 14px;
    padding: .85rem 1rem;
    margin-bottom: .6rem;
  }}
  .facsimile-shortcut-badge {{
    font-size: .58rem; font-weight: 800;
    letter-spacing: .08em; text-transform: uppercase;
    color: #A78BFA; margin-bottom: .3rem;
  }}
  .facsimile-shortcut-question {{
    font-size: .88rem; font-weight: 800;
    color: {T['text']}; font-family: 'DM Sans', sans-serif;
    margin-bottom: .3rem;
  }}
  .facsimile-shortcut-desc {{
    font-size: .75rem; color: {T['text2']};
    font-family: 'DM Sans', sans-serif; line-height: 1.5;
  }}
  .facsimile-shortcut-btn button {{
    background: linear-gradient(135deg,#7C3AED,#6D28D9) !important;
    color: #fff !important; border: none !important;
    font-weight: 700 !important; font-size: .84rem !important;
    border-radius: 10px !important;
    box-shadow: 0 3px 14px #7C3AED33 !important;
  }}
  .facsimile-shortcut-btn button:hover {{
    background: linear-gradient(135deg,#A78BFA,#7C3AED) !important;
    box-shadow: 0 4px 20px #7C3AED55 !important;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     FILE ITEMS — Compact list (Percorso B sidebar)
     ════════════════════════════════════════════════════════════════════════ */
  .file-item-b {{
    background: {_surf_overlay};
    border: 1.5px solid {T['border']};
    border-radius: 12px;
    padding: .55rem .8rem;
    margin-bottom: .3rem;
    transition: border-color .15s ease;
  }}
  .file-item-b:hover {{
    border-color: {_acc_ring};
  }}
  .file-item-b-header {{
    display: flex; align-items: center; gap: .4rem;
    flex-wrap: nowrap;
  }}
  .file-item-b-icon {{ font-size: .9rem; flex-shrink: 0; }}
  .file-item-b-name {{
    font-size: .78rem; font-weight: 700;
    color: {T['text']}; font-family: 'DM Sans', sans-serif;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    flex: 1; min-width: 0;
  }}
  .file-item-b-badge {{
    font-size: .58rem; font-weight: 700;
    padding: 2px 7px; border-radius: 5px;
    white-space: nowrap; flex-shrink: 0;
  }}
  .file-item-b-badge-verifica {{
    background: #3B82F618; color: #3B82F6;
    border: 1px solid #3B82F633;
  }}
  .file-item-b-badge-appunti {{
    background: #10B98118; color: #10B981;
    border: 1px solid #10B98133;
  }}
  .file-item-b-badge-altro {{
    background: {T['border2']}44; color: {T['text2']};
    border: 1px solid {T['border2']};
  }}
  .file-item-b-mode-label {{
    font-size: .68rem; font-weight: 600;
    color: {T['muted']}; font-family: 'DM Sans', sans-serif;
    margin: .2rem 0 .15rem;
  }}
  .file-item-b-delete {{
    margin-top: .25rem;
  }}
  .file-item-b-delete button {{
    min-height: 28px !important;
    font-size: .7rem !important;
    color: {T['muted']} !important;
    background: transparent !important;
    border: 1px dashed {T['border']} !important;
    border-radius: 6px !important;
    opacity: .7;
    transition: opacity .15s, color .15s, border-color .15s !important;
  }}
  .file-item-b-delete button:hover {{
    opacity: 1;
    color: #EF4444 !important;
    border-color: #EF4444 !important;
    background: #EF444408 !important;
  }}

  /* ═══ Context sync badge ═══ */
  .context-sync-badge {{
    display: inline-flex; align-items: center; gap: 6px;
    font-size: .72rem; font-weight: 600;
    color: {T['success']}; font-family: 'DM Sans', sans-serif;
    background: {T['success']}14;
    border: 1px solid {T['success']}33;
    border-radius: 8px; padding: 4px 10px;
    margin-bottom: .4rem;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     OCR SKELETON LOADING — Premium Effect
     ════════════════════════════════════════════════════════════════════════ */
  @keyframes shimmer {{
    0% {{ background-position: -200% 0; }}
    100% {{ background-position: 200% 0; }}
  }}
  @keyframes scanLine {{
    0% {{ top: 0; opacity: 1; }}
    80% {{ top: 92%; opacity: .7; }}
    100% {{ top: 92%; opacity: 0; }}
  }}
  @keyframes pulse-dot {{
    0%, 100% {{ opacity: .4; }}
    50% {{ opacity: 1; }}
  }}

  .ocr-skeleton-wrap {{
    background: {_surf_raised};
    border: 1.5px solid {T['border']};
    border-radius: 16px;
    padding: 1.1rem 1.2rem;
    margin: .6rem 0;
    overflow: hidden;
  }}
  .ocr-skeleton-header {{
    display: flex; align-items: center; gap: .75rem;
    margin-bottom: .8rem;
  }}
  .ocr-skeleton-icon {{
    font-size: 1.4rem;
    animation: pulse-dot 1.2s ease-in-out infinite;
  }}
  .ocr-skeleton-title {{
    font-size: .88rem; font-weight: 800;
    color: {T['text']}; font-family: 'DM Sans', sans-serif;
  }}
  .ocr-skeleton-sub {{
    font-size: .72rem; color: {T['muted']};
    font-family: 'DM Sans', sans-serif;
    margin-top: 1px;
  }}
  .ocr-skeleton-doc {{
    background: {T['bg']};
    border: 1px solid {T['border']};
    border-radius: 10px;
    padding: .9rem 1rem;
    position: relative;
    overflow: hidden;
  }}
  .ocr-skeleton-scan {{
    position: absolute; top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent, {_acc}, transparent);
    animation: scanLine 2s ease-in-out infinite;
  }}
  .ocr-skeleton-line {{
    height: 10px;
    border-radius: 6px;
    margin-bottom: 8px;
    background: linear-gradient(90deg,
      {T['border']} 25%, {T['border2']} 50%, {T['border']} 75%);
    background-size: 200% 100%;
    animation: shimmer 1.5s ease-in-out infinite;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     OCR HINT BANNER
     ════════════════════════════════════════════════════════════════════════ */
  .ocr-hint-banner {{
    display: flex; align-items: flex-start; gap: .9rem;
    background: linear-gradient(135deg, {T.get('hint_bg', _surf_raised)}, {T['card']});
    border: 1.5px solid {T.get('hint_border', T['border'])};
    border-radius: 16px;
    padding: .9rem 1.1rem;
    margin-bottom: .8rem;
  }}
  .ocr-hint-icon {{ font-size: 1.3rem; flex-shrink: 0; }}
  .ocr-hint-body {{ flex: 1; }}
  .ocr-hint-title {{
    font-size: .88rem; font-weight: 800;
    color: {T['text']}; font-family: 'DM Sans', sans-serif;
    margin-bottom: .2rem;
  }}
  .ocr-hint-desc {{
    font-size: .78rem; color: {T['text2']};
    font-family: 'DM Sans', sans-serif; line-height: 1.5;
  }}
  .ocr-hint-tags {{
    display: flex; flex-wrap: wrap; gap: 5px; margin-top: .45rem;
  }}
  .ocr-hint-tag {{
    font-size: .63rem; font-weight: 600;
    background: {T['card']}; border: 1px solid {T['border']};
    border-radius: 20px; padding: 3px 9px;
    color: {T['text2']};
  }}

  /* ════════════════════════════════════════════════════════════════════════
     FACSIMILE PAGE
     ════════════════════════════════════════════════════════════════════════ */
  .facsimile-page-wrap {{
    text-align: center;
    padding: .6rem 0 1rem;
    margin-bottom: .6rem;
  }}
  .facsimile-page-icon {{
    font-size: 2rem;
    display: block;
    margin-bottom: .3rem;
  }}
  .facsimile-page-title {{
    font-family: 'DM Sans', sans-serif;
    font-size: 1.4rem; font-weight: 900;
    color: #A78BFA;
    letter-spacing: -.02em;
    margin-bottom: .3rem;
  }}
  .facsimile-page-desc {{
    font-size: .88rem;
    color: {T['text2']};
    font-family: 'DM Sans', sans-serif;
    max-width: 480px;
    margin: 0 auto;
    line-height: 1.55;
  }}
  .facsimile-page-uploader {{
    background: {_surf_raised};
    border: 2px dashed #7C3AED44;
    border-radius: 18px;
    padding: 1.3rem 1.2rem;
    margin-bottom: .5rem;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     RECALIBRA PUNTEGGI
     ════════════════════════════════════════════════════════════════════════ */
  .recalibra-sum-ok {{
    font-size: .78rem; font-weight: 600;
    color: {T['success']}; font-family: 'DM Sans', sans-serif;
    background: {T['success']}14;
    border: 1px solid {T['success']}33;
    border-radius: 8px; padding: .4rem .7rem;
    margin-top: .3rem;
  }}
  .recalibra-sum-err {{
    font-size: .78rem; font-weight: 600;
    color: {T['warn']}; font-family: 'DM Sans', sans-serif;
    background: {T['warn']}14;
    border: 1px solid {T['warn']}33;
    border-radius: 8px; padding: .4rem .7rem;
    margin-top: .3rem;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     RUBRICA (Valutazione MIM)
     ════════════════════════════════════════════════════════════════════════ */
  .rubrica-wrap {{
    background: {_surf_overlay};
    border: 1.5px solid {T['border']};
    border-radius: 14px;
    padding: .8rem 1rem;
    margin-bottom: .6rem;
  }}
  .rubrica-header {{
    display: flex; align-items: center; gap: .5rem;
    margin-bottom: .5rem;
  }}
  .rubrica-title {{
    font-size: .88rem; font-weight: 800;
    color: {T['text']}; font-family: 'DM Sans', sans-serif;
  }}
  .rubrica-badge {{
    font-size: .6rem; font-weight: 700;
    background: {_acc_soft}; color: {_acc};
    border: 1px solid {_acc_ring};
    border-radius: 20px; padding: 2px 8px;
    margin-left: auto;
  }}
  .rubrica-content {{
    font-size: .8rem; color: {T['text2']};
    font-family: 'DM Sans', sans-serif;
    line-height: 1.6;
  }}


  /* ════════════════════════════════════════════════════════════════════════
     STAGE_FINAL — Variant Cards (Fila B, BES/DSA, Soluzioni, Rubrica)
     Altezza minima uniforme + layout flex per allineare i bottoni in fondo.
     ════════════════════════════════════════════════════════════════════════ */
  .one-click-variant-card {{
    background: {T['card']};
    border: 1.5px solid {T['border2']};
    border-radius: 16px;
    padding: 1.1rem 1.1rem .85rem;
    margin-bottom: .75rem;
    min-height: 110px;
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
    transition: border-color .2s ease, box-shadow .2s ease, transform .15s ease;
    animation: fadeSlideUp .3s ease both;
  }}
  .one-click-variant-card:hover {{
    border-color: {_acc}66;
    box-shadow: 0 4px 20px {_acc}18;
    transform: translateY(-1px);
  }}
  .one-click-body {{
    flex: 1;
    display: flex;
    flex-direction: column;
  }}
  .one-click-title {{
    font-family: 'DM Sans', sans-serif;
    font-size: .95rem; font-weight: 900;
    letter-spacing: -.01em;
    color: {T['text']};
    margin-bottom: .3rem;
  }}
  .one-click-desc {{
    font-size: .78rem; font-weight: 400;
    color: {T['text2']};
    font-family: 'DM Sans', sans-serif;
    line-height: 1.5;
    flex: 1;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     FAB — Floating feedback button
     ════════════════════════════════════════════════════════════════════════ */
  .fab-link {{
    position: fixed; bottom: 1.2rem; right: 1.2rem;
    z-index: 998;
    background: {T['card']};
    color: {T['text2']} !important;
    font-size: .72rem; font-weight: 700;
    font-family: 'DM Sans', sans-serif;
    padding: .45rem .85rem;
    border-radius: 100px;
    border: 1.5px solid {T['border']};
    box-shadow: {T.get('shadow_md', '0 4px 20px rgba(0,0,0,.08)')};
    text-decoration: none !important;
    transition: border-color .15s ease, box-shadow .15s ease, transform .15s ease;
  }}
  .fab-link:hover {{
    border-color: {_acc};
    color: {_acc} !important;
    box-shadow: 0 4px 24px {_acc_soft};
    transform: translateY(-2px);
  }}

  /* ════════════════════════════════════════════════════════════════════════
     FOOTER
     ════════════════════════════════════════════════════════════════════════ */
  .app-footer {{
    text-align: center;
    font-size: .72rem;
    color: {T['muted']};
    font-family: 'DM Sans', sans-serif;
    padding: 1.5rem 0 .5rem;
    line-height: 1.6;
    border-top: 1px solid {T['border']};
    margin-top: 2rem;
  }}
  /* ════════════════════════════════════════════════════════════════════════
     DARK MODE — Profondità e contrasto aumentati
     Queste regole sovrascrivono le globali per il tema scuro.
     Controllato dal tema T: border più luminosi, shadow più forti.
     ════════════════════════════════════════════════════════════════════════ */
  .dark-card-elevated {{
    background: {T.get('card2', T['card'])};
    border: 1px solid {T['border2']};
    border-radius: 14px;
    box-shadow: {T.get('shadow_md', '0 4px 24px rgba(0,0,0,.35)')};
  }}

  /* Rende card in Streamlit con bordi più leggibili in dark */
  [data-theme="dark"] [data-testid="stVerticalBlock"] > div:first-child {{
    border-color: {T['border2']} !important;
  }}

  /* Dividers più visibili in dark */
  .dark-divider {{
    height: 1px;
    background: linear-gradient(90deg,
      transparent 0%,
      {T['border2']} 20%,
      {T['border2']} 80%,
      transparent 100%
    );
    margin: 1rem 0;
    opacity: .7;
  }}

  /* Section label con glow sottile in dark (accent tenue) */
  .form-section-dot {{
    box-shadow: 0 0 6px {_acc}66, 0 0 2px {_acc};
  }}



  /* ════════════════════════════════════════════════════════════════════════
     EXPANDER — Streamlit override
     ════════════════════════════════════════════════════════════════════════ */
  details[data-testid="stExpander"] {{
    background: {_surf_raised} !important;
    border: 1.5px solid {T['border']} !important;
    border-radius: 14px !important;
  }}
  details[data-testid="stExpander"] summary {{
    font-family: 'DM Sans', sans-serif !important;
    font-size: .88rem !important;
    font-weight: 700 !important;
    color: {T['text']} !important;
  }}
  details[data-testid="stExpander"] summary:hover {{
    color: {_acc} !important;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     FILE UPLOADER — Streamlit override
     ════════════════════════════════════════════════════════════════════════ */
  [data-testid="stFileUploader"] {{
    background: {_surf_overlay} !important;
    border: 2px dashed {T['border2']} !important;
    border-radius: 14px !important;
    padding: .8rem !important;
    transition: border-color .2s ease !important;
  }}
  [data-testid="stFileUploader"]:hover {{
    border-color: {_acc_ring} !important;
  }}
  [data-testid="stFileUploader"] section > button {{
    background: {_acc} !important;
    color: #fff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
    font-size: .82rem !important;
  }}
  [data-testid="stFileUploader"] small {{
    color: {T['muted']} !important;
    font-family: 'DM Sans', sans-serif !important;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     TOAST — Streamlit override
     ════════════════════════════════════════════════════════════════════════ */
  [data-testid="stToast"] {{
    background: {T['card']} !important;
    border: 1.5px solid {T['border']} !important;
    border-radius: 14px !important;
    box-shadow: 0 8px 32px rgba(0,0,0,.15) !important;
  }}
  [data-testid="stToast"] [data-testid="stMarkdownContainer"] {{
    color: {T['text']} !important;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     BACK BUTTON — Discrete link style (piccolo, muted, in fondo)
     ════════════════════════════════════════════════════════════════════════ */
  .btn-back-discrete > div.stButton > button,
  .btn-back-discrete .stButton > button {{
    background: transparent !important;
    color: {T['muted']} !important;
    border: 1px solid transparent !important;
    border-radius: 8px !important;
    font-size: .76rem !important;
    font-weight: 500 !important;
    min-height: 28px !important;
    padding: 0 .8rem !important;
    box-shadow: none !important;
    transform: none !important;
    transition: color .12s ease, border-color .12s ease !important;
    width: auto !important;
  }}
  .btn-back-discrete > div.stButton > button:hover,
  .btn-back-discrete .stButton > button:hover {{
    color: {T['text2']} !important;
    border-color: {T['border2']} !important;
    background: {T['hover']} !important;
    transform: none !important;
    box-shadow: none !important;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     TEMPLATE GALLERY (optional)
     ════════════════════════════════════════════════════════════════════════ */
  .tmpl-gallery-wrap {{
    display: flex; flex-wrap: wrap; gap: 8px;
    margin: .5rem 0;
  }}
  .tmpl-card {{
    background: {_surf_overlay};
    border: 1.5px solid {T['border']};
    border-radius: 10px;
    padding: .5rem .7rem;
    cursor: pointer;
    transition: border-color .15s, box-shadow .15s;
    flex: 0 1 calc(50% - 4px);
    min-width: 130px;
  }}
  .tmpl-card:hover {{
    border-color: {_acc_ring};
    box-shadow: 0 2px 12px {_acc_soft};
  }}
  .tmpl-card-sel {{
    border-color: {_acc} !important;
    background: {_acc_soft} !important;
  }}
  .tmpl-card-title {{
    font-size: .76rem; font-weight: 700;
    color: {T['text']}; font-family: 'DM Sans', sans-serif;
    margin-bottom: 2px;
  }}
  .tmpl-card-desc {{
    font-size: .66rem;
    color: {T['muted']}; font-family: 'DM Sans', sans-serif;
    line-height: 1.4;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     DOWNLOAD BUTTONS
     ════════════════════════════════════════════════════════════════════════ */
  [data-testid="stDownloadButton"] > button {{
    background: {_surf_raised} !important;
    border: 1.5px solid {T['border']} !important;
    border-radius: 10px !important;
    color: {T['text']} !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 700 !important;
    font-size: .85rem !important;
    transition: border-color .15s ease, background .15s ease !important;
  }}
  [data-testid="stDownloadButton"] > button:hover {{
    border-color: {_acc} !important;
    background: {T['hover']} !important;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     GENERATING PROGRESS — Animated bar
     ════════════════════════════════════════════════════════════════════════ */
  @keyframes progress-pulse {{
    0%, 100% {{ opacity: .7; }}
    50% {{ opacity: 1; }}
  }}
  .gen-progress-wrap {{
    margin: .6rem 0 1rem;
  }}
  .gen-progress-label {{
    font-size: .82rem; font-weight: 600;
    color: {T['text2']};
    font-family: 'DM Sans', sans-serif;
    margin-bottom: 6px;
    animation: progress-pulse 1.5s ease-in-out infinite;
  }}
  .gen-progress-bar {{
    background: {T['border']};
    border-radius: 100px;
    height: 8px;
    overflow: hidden;
  }}
  .gen-progress-fill {{
    background: linear-gradient(90deg, {_acc}, {_acc}cc);
    height: 100%;
    border-radius: 100px;
    transition: width .4s ease;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     FEATURE #3 — Quick Regen (variante rapida one-click)
     ════════════════════════════════════════════════════════════════════════ */
  .quick-regen-row {{
    display: flex;
    align-items: center;
    gap: .6rem;
    padding: .55rem .75rem;
    background: linear-gradient(135deg, {_acc}12, {_acc}06);
    border: 1px dashed {_acc}40;
    border-radius: 10px;
    margin: .5rem 0 .3rem 0;
  }}
  .quick-regen-label {{
    font-size: .78rem;
    color: {T['text']};
    font-family: 'DM Sans', sans-serif;
    line-height: 1.45;
  }}
  .quick-regen-label strong {{
    color: {_acc};
    font-weight: 800;
  }}
  .quick-regen-hint {{
    display: block;
    font-size: .68rem;
    color: {T['muted']};
    font-weight: 400;
    margin-top: 1px;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     FEATURE #5 — Condivisione Dipartimento
     ════════════════════════════════════════════════════════════════════════ */

  /* Card principale */
  .share-dept-card {{
    background: linear-gradient(135deg, {T['card']} 0%, {T['card2']} 100%);
    border: 2px solid {_acc}30;
    border-radius: 16px;
    padding: 1rem 1.2rem;
    margin-bottom: .8rem;
    position: relative;
    overflow: hidden;
  }}
  .share-dept-card::before {{
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, {_acc}, #7C3AED, {_acc});
    background-size: 200% 100%;
    animation: gradientSlide 3s ease infinite;
  }}
  @keyframes gradientSlide {{
    0%,100% {{ background-position: 0% 50%; }}
    50% {{ background-position: 100% 50%; }}
  }}
  .share-dept-header {{
    display: flex;
    align-items: flex-start;
    gap: .8rem;
  }}
  .share-dept-icon {{
    font-size: 1.6rem;
    flex-shrink: 0;
    margin-top: 2px;
  }}
  .share-dept-title-wrap {{
    flex: 1;
  }}
  .share-dept-title {{
    font-size: .92rem;
    font-weight: 800;
    color: {T['text']};
    font-family: 'DM Sans', sans-serif;
  }}
  .share-dept-subtitle {{
    font-size: .74rem;
    color: {T['text2']};
    line-height: 1.5;
    margin-top: 3px;
  }}

  /* Link box (dopo generazione) */
  .share-link-box {{
    background: {T['bg2']};
    border: 1px solid {T['border']};
    border-radius: 10px;
    padding: .6rem .9rem;
    margin: .6rem 0;
  }}
  .share-link-status {{
    display: flex;
    align-items: center;
    gap: .4rem;
    font-size: .68rem;
    color: {T['success']};
    font-weight: 600;
    font-family: 'DM Sans', sans-serif;
    margin-bottom: .35rem;
  }}
  .share-link-dot {{
    width: 6px; height: 6px;
    border-radius: 50%;
    background: {T['success']};
    animation: pulse-dot 2s ease infinite;
    flex-shrink: 0;
  }}
  .share-link-url {{
    font-size: .76rem;
    color: {_acc};
    font-family: 'DM Sans', monospace;
    word-break: break-all;
    font-weight: 600;
    padding: .3rem .5rem;
    background: {_acc}08;
    border-radius: 6px;
    border: 1px solid {_acc}20;
  }}

  /* Shared view (colleghi che aprono il link) */
  .shared-view-banner {{
    background: linear-gradient(135deg, #7C3AED20, {_acc}15);
    border: 2px solid #7C3AED40;
    border-radius: 16px;
    padding: 1.1rem 1.3rem;
    margin-bottom: 1rem;
  }}
  .shared-view-header {{
    display: flex;
    align-items: center;
    gap: .8rem;
    margin-bottom: .7rem;
  }}
  .shared-view-title {{
    font-size: 1.05rem;
    font-weight: 900;
    color: {T['text']};
    font-family: 'DM Sans', sans-serif;
  }}
  .shared-view-meta {{
    font-size: .76rem;
    color: {T['text2']};
    margin-top: 2px;
  }}
  .shared-view-badges {{
    display: flex;
    flex-wrap: wrap;
    gap: .4rem;
  }}
  .shared-view-badge {{
    background: {T['card2']};
    border: 1px solid {T['border']};
    border-radius: 20px;
    padding: .2rem .65rem;
    font-size: .68rem;
    font-weight: 600;
    color: {T['text2']};
    font-family: 'DM Sans', sans-serif;
  }}

  /* CTA variante (per colleghi) */
  .shared-cta-card {{
    background: linear-gradient(135deg, {_acc}12, {_acc}06);
    border: 2px solid {_acc}35;
    border-radius: 14px;
    padding: 1rem 1.2rem;
    margin: .7rem 0;
    text-align: center;
  }}
  .shared-cta-icon {{
    font-size: 1.8rem;
    margin-bottom: .3rem;
  }}
  .shared-cta-title {{
    font-size: .95rem;
    font-weight: 800;
    color: {_acc};
    font-family: 'DM Sans', sans-serif;
    margin-bottom: .3rem;
  }}
  .shared-cta-desc {{
    font-size: .76rem;
    color: {T['text2']};
    line-height: 1.5;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     STORICO — Sidebar migliorato
     ════════════════════════════════════════════════════════════════════════ */

  /* Card verifica nello storico */
  .storico-card {{
    background: #1A1917;
    border: 1px solid #2A2923;
    border-radius: 10px;
    padding: .6rem .75rem;
    margin-bottom: .5rem;
    transition: border-color .2s, background .2s;
  }}
  .storico-card:hover {{
    border-color: {_acc}50;
    background: #1E1D1A;
  }}
  .storico-card-top {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: .25rem;
  }}
  .storico-card-mat {{
    font-size: .76rem;
    font-weight: 700;
    color: #d8d6ce;
    font-family: 'DM Sans', sans-serif;
  }}
  .storico-card-date {{
    font-size: .62rem;
    color: #6b6960;
    font-family: 'DM Sans', sans-serif;
    white-space: nowrap;
  }}
  .storico-card-arg {{
    font-size: .72rem;
    color: #9b9890;
    font-family: 'DM Sans', sans-serif;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    margin-bottom: .3rem;
  }}
  .storico-card-meta {{
    display: flex;
    align-items: center;
    gap: .3rem;
    font-size: .62rem;
    color: #6b6960;
    font-family: 'DM Sans', sans-serif;
    margin-bottom: .3rem;
  }}
  .storico-card-scu {{
    color: #7b7970;
  }}
  .storico-card-nes {{
    color: #6b6960;
  }}
  .storico-card-badges {{
    display: flex;
    gap: .3rem;
    flex-wrap: wrap;
  }}
  /* Filtro materia chips (sidebar) */
  .storico-filter {{
    display: flex;
    align-items: center;
    gap: .3rem;
    margin-bottom: .5rem;
    flex-wrap: wrap;
  }}
  .storico-filter-chip {{
    font-size: .62rem;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 10px;
    border: 1px solid #2A2923;
    background: transparent;
    color: #8b8980;
    font-family: 'DM Sans', sans-serif;
  }}
  .storico-filter-chip-active {{
    background: {_acc}20;
    border-color: {_acc};
    color: {_acc};
  }}
  /* Stella e delete in storico */
  .stella-btn, .stella-btn-on {{
    margin: 0;
  }}
  .stella-btn button, .stella-btn-on button {{
    background: transparent !important;
    border: none !important;
    padding: 2px 4px !important;
    font-size: .82rem !important;
    min-height: auto !important;
    line-height: 1 !important;
  }}
  .stella-btn-on button {{
    color: {_acc} !important;
  }}
  .elimina-btn button {{
    background: transparent !important;
    border: 1px dashed #3a3930 !important;
    padding: 2px 6px !important;
    font-size: .72rem !important;
    min-height: auto !important;
    opacity: .5;
    transition: all .15s;
  }}
  .elimina-btn button:hover {{
    opacity: 1;
    border-color: #EF4444 !important;
    color: #EF4444 !important;
  }}

  /* ════════════════════════════════════════════════════════════════════════
     RESPONSIVE
     ════════════════════════════════════════════════════════════════════════ */
  /* ── Tablet: 768px → un po' più stretto ── */
  @media (max-width: 767px) {{
    .onboarding-hint-banner {{
      flex-direction: column;
      gap: .6rem;
    }}
    .facsimile-shortcut {{
      display: none;
    }}
    .hero-title {{
      font-size: 1.3rem;
    }}
    .home-landing-title {{
      font-size: 1.3rem;
    }}
    .mcard {{
      min-height: auto;
    }}
    .landing-headline-xl {{
      font-size: clamp(1.6rem, 7vw, 2.4rem);
    }}
    .landing-logo-name-xl {{
      font-size: clamp(2rem, 8vw, 3rem);
    }}
    .feature-pills-row {{
      gap: 6px;
    }}
    .feature-pill-label {{
      font-size: .72rem;
    }}
  }}

  /* ── Mobile stretto: < 640px — single-column layout ── */
  @media (max-width: 640px) {{
    /* Hero landing */
    .landing-hero-unified {{
      padding: 1.4rem 1rem;
    }}
    .landing-headline-xl {{
      font-size: 1.55rem;
      letter-spacing: -.025em;
    }}
    .landing-logo-icon-xl {{
      font-size: 2.6rem;
    }}
    .landing-logo-name-xl {{
      font-size: 2rem;
    }}
    .landing-sub-xl {{
      font-size: .88rem;
    }}

    /* Feature pills — impila su 2 per riga */
    .feature-pills-row {{
      gap: 5px;
      max-width: 100%;
    }}
    .feature-pill {{
      padding: 4px 10px 4px 8px;
    }}
    .feature-pill-label {{
      font-size: .7rem;
    }}

    /* Form sections */
    .form-section-title {{
      font-size: .68rem;
    }}
    .opt-label {{
      font-size: .65rem;
    }}

    /* Card varianti — full width stacked */
    .one-click-variant-card {{
      min-height: auto;
      padding: .9rem .85rem .7rem;
    }}
    .one-click-title {{
      font-size: .88rem;
    }}
    .one-click-desc {{
      font-size: .74rem;
    }}

    /* Breadcrumb — riduci font */
    .breadcrumb-wrap {{
      overflow-x: auto;
      padding-bottom: .3rem;
    }}

    /* Expander summary più grande (touch target) */
    details[data-testid="stExpander"] summary {{
      font-size: .95rem !important;
      padding: .7rem .8rem !important;
      min-height: 44px;
    }}

    /* Pulsanti — altezza touch-friendly */
    [data-testid="baseButton-primary"],
    [data-testid="baseButton-secondary"],
    button[kind="primary"],
    button[kind="secondary"] {{
      min-height: 44px !important;
      font-size: .88rem !important;
    }}

    /* Nascondi elementi decorativi pesanti su mobile */
    .sidebar-hint-inline {{
      display: none;
    }}

    /* Hero wrap non-landing */
    .hero-wrap .hero-sub {{
      display: none;
    }}
    .hero-title {{
      font-size: 1.15rem;
    }}
    .hero-beta {{
      display: none;
    }}
  }}

  /* ═══════════════════════════════════════════════════════════════════════
     IDEA #3 — QUICK REGEN (variante rapida)
     ═══════════════════════════════════════════════════════════════════════ */

  .quick-regen-row {{
    display: flex;
    align-items: center;
    gap: 8px;
    padding: .5rem .6rem;
    background: linear-gradient(135deg, {T.get("card2", T["card"])} 0%, {T["card"]} 100%);
    border: 1px dashed {T["accent"]}55;
    border-radius: 10px;
    margin-bottom: .4rem;
  }}
  .quick-regen-label {{
    font-size: .78rem;
    font-family: 'DM Sans', sans-serif;
    color: {T["text2"]};
    line-height: 1.4;
  }}
  .quick-regen-label strong {{
    color: {T["accent"]};
  }}
  .quick-regen-hint {{
    display: block;
    font-size: .68rem;
    color: {T["muted"]};
    font-weight: 400;
    margin-top: 1px;
  }}

  /* ═══════════════════════════════════════════════════════════════════════
     IDEA #5 — SHARE WITH DEPARTMENT
     ═══════════════════════════════════════════════════════════════════════ */

  .share-dept-card {{
    background: linear-gradient(135deg, {T.get("card2", T["card"])} 0%, {T["card"]} 100%);
    border: 1px solid {T["border"]};
    border-radius: 14px;
    padding: 1rem 1.2rem;
    margin-bottom: .6rem;
  }}
  .share-dept-header {{
    display: flex;
    align-items: flex-start;
    gap: 12px;
  }}
  .share-dept-icon {{
    font-size: 1.5rem;
    flex-shrink: 0;
    margin-top: 2px;
  }}
  .share-dept-title-wrap {{
    flex: 1;
  }}
  .share-dept-title {{
    font-family: 'DM Sans', sans-serif;
    font-size: .92rem;
    font-weight: 800;
    color: {T["text"]};
    margin-bottom: 4px;
  }}
  .share-dept-subtitle {{
    font-size: .76rem;
    color: {T["text2"]};
    line-height: 1.45;
  }}

  .share-link-box {{
    background: {T.get("card2", T["card"])};
    border: 2px solid {T["success"]}44;
    border-radius: 10px;
    padding: .7rem .9rem;
    margin-bottom: .5rem;
  }}
  .share-link-status {{
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: .7rem;
    font-weight: 700;
    color: {T["success"]};
    font-family: 'DM Sans', sans-serif;
    margin-bottom: 6px;
  }}
  .share-link-dot {{
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: {T["success"]};
    animation: pulse-dot 2s ease-in-out infinite;
  }}
  .share-link-url {{
    font-size: .72rem;
    color: {T["muted"]};
    font-family: 'DM Sans', monospace;
    word-break: break-all;
    padding: .3rem .5rem;
    background: {T["bg"]};
    border-radius: 6px;
    border: 1px solid {T["border"]};
  }}

  /* ── Shared view (link aperto da collega) ──────────────────────── */
  .shared-view-banner {{
    background: linear-gradient(135deg, {T.get("card2", T["card"])} 0%, {T["card"]} 100%);
    border: 2px solid {T["accent"]}55;
    border-radius: 16px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 1rem;
  }}
  .shared-view-header {{
    display: flex;
    align-items: center;
    gap: 14px;
    margin-bottom: .7rem;
  }}
  .shared-view-title {{
    font-family: 'DM Sans', sans-serif;
    font-size: 1.05rem;
    font-weight: 900;
    color: {T["accent"]};
  }}
  .shared-view-meta {{
    font-size: .78rem;
    color: {T["text2"]};
    margin-top: 2px;
  }}
  .shared-view-badges {{
    display: flex;
    gap: .4rem;
    flex-wrap: wrap;
  }}
  .shared-view-badge {{
    background: {T.get("card2", T["card"])};
    border: 1px solid {T["border"]};
    border-radius: 8px;
    padding: .2rem .6rem;
    font-size: .7rem;
    font-weight: 600;
    color: {T["text2"]};
    font-family: 'DM Sans', sans-serif;
  }}
  .shared-cta-card {{
    background: linear-gradient(135deg, #D97706 0%, #B45309 100%);
    border-radius: 14px;
    padding: 1.1rem 1.3rem;
    margin-bottom: .7rem;
    text-align: center;
  }}
  .shared-cta-icon {{
    font-size: 1.8rem;
    margin-bottom: .3rem;
  }}
  .shared-cta-title {{
    font-family: 'DM Sans', sans-serif;
    font-size: 1rem;
    font-weight: 900;
    color: #fff;
    margin-bottom: .3rem;
  }}
  .shared-cta-desc {{
    font-size: .78rem;
    color: #ffffffcc;
    line-height: 1.45;
  }}

  /* ═══════════════════════════════════════════════════════════════════════
     STORICO — Card redesign
     ═══════════════════════════════════════════════════════════════════════ */

  .storico-card {{
    margin-top: .6rem;
    padding: .45rem .5rem .35rem;
    border-bottom: 1px solid #252420;
    border-left: 3px solid transparent;
    transition: border-left-color .15s;
  }}
  .storico-card:hover {{
    border-left-color: {T["accent"]};
  }}
  .storico-card-top {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 2px;
  }}
  .storico-card-mat {{
    font-size: .78rem;
    font-weight: 700;
    color: #d8d6ce;
    font-family: 'DM Sans', sans-serif;
  }}
  .storico-card-date {{
    font-size: .62rem;
    color: #6b6960;
    font-family: 'DM Sans', sans-serif;
  }}
  .storico-card-arg {{
    font-size: .74rem;
    color: #9b9890;
    font-family: 'DM Sans', sans-serif;
    margin-bottom: 3px;
    line-height: 1.3;
  }}
  .storico-card-meta {{
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: .64rem;
    color: #5e5d56;
    font-family: 'DM Sans', sans-serif;
  }}
  .storico-card-scu {{
    background: #1a1917;
    padding: 1px 6px;
    border-radius: 4px;
    border: 1px solid #2a2924;
  }}
  .storico-card-nes {{
    opacity: .8;
  }}
  .storico-card-badges {{
    display: flex;
    gap: 3px;
    margin-top: 4px;
  }}

</style>
"""


def _is_light_color(hex_color: str) -> bool:
    """Restituisce True se il colore è chiaro (luminosità > 0.5)."""
    try:
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        return luminance > 0.5
    except Exception:
        return False
