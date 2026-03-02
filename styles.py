def get_css(T: dict) -> str:
    """
    Restituisce il CSS dell'app adattato dinamicamente al tema T.
    Tutti i colori vengono estratti dal dizionario T passato come argomento.
    """
    # Sidebar: i colori vengono estratti dal tema (chiave sidebar_*).
    # Fallback ai valori dark storici per retrocompatibilità con temi senza queste chiavi.
    _SB_ACCENT = T.get("sidebar_accent", "#D97706")
    _SB_BG_CSS = T.get("sidebar_bg",     "linear-gradient(180deg, #111110 0%, #0e0e0d 100%)")
    _SB_BORDER = T.get("sidebar_border", "#252420")
    _SB_MUTED  = "#8a8880"
    _SB_TEXT   = "#e8e6e0"

    # Calcola se il tema è light (background chiaro) per aggiustare
    # alcuni colori del pulsante primary
    _is_light = _is_light_color(T["bg"])
    _btn_primary_bg = T["accent"]

    return f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;0,800;0,900;1,400&display=swap');

  *, *::before, *::after {{ box-sizing: border-box; }}

  .stApp {{
    background-color: {T['bg']} !important;
    font-family: 'DM Sans', sans-serif;
    color: {T['text']};
    transition: background-color 0.25s ease, color 0.25s ease;
  }}

  .block-container {{
    padding: 5rem 1.5rem 4rem !important;
    max-width: 1400px !important;
    margin: 0 auto !important;
  }}

  #MainMenu, footer {{ visibility: hidden; }}
  .stDecoration {{ display: none; }}

  header[data-testid="stHeader"] {{
    background-color: {T['bg']} !important;
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
    border-color: {T['accent']} !important;
  }}
  header button:hover svg {{
    fill: {T['accent']} !important;
  }}
  .stMarkdown h1 a, .stMarkdown h2 a, .stMarkdown h3 a {{ display: none !important; }}

  /* ════ SIDEBAR — Dark Premium ════ */
  /* Palette fissa dark, indipendente dal tema pagina */
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
  /* Testo globale sidebar */
  [data-testid="stSidebar"] p,
  [data-testid="stSidebar"] span,
  [data-testid="stSidebar"] label,
  [data-testid="stSidebar"] div {{
    color: {_SB_TEXT} !important;
  }}
  /* Label dei widget */
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
  /* Inputs */
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
  /* Pulsanti standard sidebar */
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
    border: 2px solid {T['accent']} !important;
    border-radius: 10px !important;
    color: {T['accent']} !important;
    width: 40px !important;
    height: 40px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    box-shadow: 0 2px 12px {T['accent']}33 !important;
    transition: transform 0.15s ease, box-shadow 0.15s ease, background 0.15s ease !important;
    padding: 0 !important;
  }}
  [data-testid="collapsedControl"] button:hover {{
    background: {T['accent']} !important;
    box-shadow: 0 4px 18px {T['accent']}55 !important;
    transform: scale(1.08) !important;
  }}
  [data-testid="collapsedControl"] button:hover svg {{
    fill: #ffffff !important;
    color: #ffffff !important;
    stroke: #ffffff !important;
  }}
  [data-testid="collapsedControl"] button svg {{
    fill: {T['accent']} !important;
    color: {T['accent']} !important;
    stroke: {T['accent']} !important;
    width: 18px !important;
    height: 18px !important;
  }}

  /* ── Sidebar section labels ── */
  [data-testid="stSidebar"] .sidebar-label,
  .sidebar-label {{
    font-size: 0.65rem !important;
    font-weight: 800 !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
    color: {_SB_ACCENT} !important;
    margin: 1.1rem 0 0.45rem 0 !important;
    padding-bottom: 0.3rem !important;
    border-bottom: 1px solid {_SB_BORDER} !important;
    display: flex !important;
    align-items: center !important;
    gap: 5px !important;
  }}

  /* ── Logout button ── */
  [data-testid="stSidebar"] .logout-btn-wrap div.stButton > button,
  [data-testid="stSidebar"] .logout-btn-wrap .stButton button,
  [data-testid="stSidebar"] .logout-btn-wrap button {{
    background: transparent !important;
    color: #f87171 !important;
    border: 1px solid #3d1515 !important;
    border-radius: 8px !important;
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    padding: 6px 14px !important;
    width: 100% !important;
    min-height: unset !important;
    box-shadow: none !important;
    transition: background 0.15s ease, border-color 0.15s ease !important;
    letter-spacing: 0.02em !important;
  }}
  [data-testid="stSidebar"] .logout-btn-wrap div.stButton > button:hover,
  [data-testid="stSidebar"] .logout-btn-wrap .stButton button:hover,
  [data-testid="stSidebar"] .logout-btn-wrap button:hover {{
    background: #1f0a0a !important;
    border-color: #f87171 !important;
    color: #fca5a5 !important;
  }}

  /* ════ TESTO GLOBALE — forza colore su tutti i widget (fix tema chiaro) ════ */
  .stApp p,
  .stApp span:not([class*="sidebar"]),
  .stApp div:not([data-testid="stSidebar"] *),
  .stMarkdown p,
  .stMarkdown span,
  [data-testid="stMarkdownContainer"] p,
  [data-testid="stMarkdownContainer"] span,
  [data-testid="stText"] p,
  .stText p {{
    color: {T['text']} !important;
  }}

  /* Toggle help text / hint accanto ai toggle ✓ — fix chiave tema chiaro */
  .stCheckbox + div p,
  .stToggle + div p,
  [data-testid="stWidgetLabel"] p,
  [data-testid="stWidgetLabel"] span,
  [data-testid="InputInstructions"] {{
    color: {T['text2']} !important;
  }}

  /* Caption e testo small dei widget */
  small, .stCaption, .stCaption p,
  [data-testid="stCaptionContainer"],
  [data-testid="stCaptionContainer"] p {{
    color: {T['muted']} !important;
  }}

  /* Testo del selectbox e dei suoi option */
  .stSelectbox [data-baseweb="select"] [data-value],
  .stSelectbox [data-baseweb="select"] span,
  .stSelectbox label p {{
    color: {T['text']} !important;
  }}

  h1, h2, h3 {{
    font-family: 'DM Sans', sans-serif !important;
    color: {T['text']} !important;
    letter-spacing: -0.02em;
  }}

  /* ════ HERO ════ */
  .hero-wrap {{
    margin-bottom: 2.5rem;
    padding-bottom: 1.8rem;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-direction: column;
    flex-wrap: wrap;
    gap: 0;
    position: relative;
  }}
  .hero-left {{ flex: 1; min-width: 200px; text-align: center; }}
  @keyframes iconBounce {{
    0%   {{ transform: rotate(0deg) scale(1); }}
    15%  {{ transform: rotate(-12deg) scale(1.15); }}
    30%  {{ transform: rotate(8deg) scale(1.1); }}
    45%  {{ transform: rotate(-6deg) scale(1.05); }}
    60%  {{ transform: rotate(3deg) scale(1.02); }}
    75%  {{ transform: rotate(-1deg) scale(1.01); }}
    100% {{ transform: rotate(0deg) scale(1); }}
  }}
  @keyframes badgePop {{
    0%   {{ opacity: 0; transform: translateY(6px); }}
    100% {{ opacity: 1; transform: translateY(0); }}
  }}
  @keyframes subFadeIn {{
    0%   {{ opacity: 0; transform: translateY(4px); }}
    100% {{ opacity: 1; transform: translateY(0); }}
  }}
  .hero-title {{
    font-family: 'DM Sans', sans-serif;
    font-size: 108px !important;
    font-weight: 900 !important;
    color: {T['text']};
    line-height: 1.0;
    margin: 0 0 0.15rem 0;
    letter-spacing: -0.04em;
    display: inline-flex;
    align-items: center;
    gap: 0;
    justify-content: center;
  }}
  .hero-icon {{
    display: inline-block;
    margin-right: 0.3em;
    animation: iconBounce 1.1s ease 0.2s both;
    transform-origin: center bottom;
  }}
  .hero-ai {{
    background: linear-gradient(135deg, {T['accent']} 0%, {T['accent2']} 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    animation: badgePop 0.6s ease 0.5s both;
  }}
  .hero-sub {{
    font-size: 1.05rem;
    color: {T['text2']};
    margin: 0 0 0.55rem 0;
    font-weight: 500;
    letter-spacing: -0.01em;
    animation: subFadeIn 0.5s ease 0.35s both;
    opacity: 0;
  }}
  .hero-beta {{
    display: inline-block;
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: {T['muted']};
    background: {T['card2']};
    border: 1px solid {T['border2']};
    border-radius: 100px;
    padding: 2px 10px;
    font-family: 'DM Sans', sans-serif;
    animation: badgePop 0.5s ease 0.75s both;
    opacity: 0;
  }}

  /* ════ SIDEBAR HINT MINIMALE (in alto a sinistra) ════ */
  .sidebar-hint-inline {{
    position: fixed;
    top: .6rem;
    left: 3.8rem;
    z-index: 900;
    font-size: .68rem;
    font-weight: 500;
    color: {T['muted']};
    font-family: 'DM Sans', sans-serif;
    letter-spacing: .01em;
    pointer-events: none;
    white-space: nowrap;
  }}

  /* ════ INPUTS ════ */
  .stTextInput label p,
  .stSelectbox label p,
  .stNumberInput label p,
  .stTextArea label p,
  .stFileUploader label p {{
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    color: {T['text2']} !important;
    letter-spacing: 0.01em;
    text-transform: uppercase;
    margin-bottom: 4px !important;
  }}

  .stTextInput input,
  .stNumberInput input {{
    background: {T['input_bg']} !important;
    border: 1.5px solid {T['border']} !important;
    border-radius: 10px !important;
    color: {T['text']} !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.95rem !important;
    padding: 14px 16px !important;
    min-height: 52px !important;
    height: 52px !important;
    box-sizing: border-box !important;
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
  }}
  .stTextInput input::placeholder,
  .stNumberInput input::placeholder {{
    color: {T['muted']} !important;
    opacity: 1 !important;
  }}
  .stTextInput input:focus,
  .stNumberInput input:focus {{
    border-color: {T['accent']} !important;
    box-shadow: 0 0 0 3px {T['accent_light']} !important;
    outline: none !important;
  }}
  .stTextArea textarea {{
    background: {T['input_bg']} !important;
    border: 1.5px solid {T['border']} !important;
    border-radius: 10px !important;
    color: {T['text']} !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.9rem !important;
    padding: 10px 14px !important;
  }}
  .stTextArea textarea::placeholder {{
    color: {T['muted']} !important;
    opacity: 1 !important;
  }}
  .stTextArea textarea:focus {{
    border-color: {T['accent']} !important;
    box-shadow: 0 0 0 3px {T['accent_light']} !important;
  }}

  .stSelectbox [data-baseweb="select"] > div:first-child {{
    background: {T['input_bg']} !important;
    border: 1.5px solid {T['border']} !important;
    border-radius: 10px !important;
    color: {T['text']} !important;
  }}
  .stSelectbox [data-baseweb="select"] span {{
    color: {T['text']} !important;
  }}

  .stCheckbox label {{
    color: {T['text']} !important;
    font-size: 0.9rem !important;
    font-family: 'DM Sans', sans-serif !important;
  }}
  .stCheckbox [data-testid="stCheckbox"] span:first-child {{
    background-color: {T['input_bg']} !important;
    border: 1.5px solid {T['border2']} !important;
    border-radius: 5px !important;
  }}

  /* ════ BUTTONS ════ */
  div.stButton > button[kind="primary"] {{
    background: {_btn_primary_bg} !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    transition: transform 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275), box-shadow 0.2s ease, filter 0.2s ease !important;
    box-shadow: 0 2px 12px {T['accent']}55 !important;
    display: block !important;
    min-height: 46px !important;
    padding: 0.6rem 1rem !important;
    font-size: 1rem !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 700 !important;
  }}
  div.stButton > button[kind="primary"]:hover {{
    transform: scale(1.05) !important;
    box-shadow: 0 10px 25px {T['accent']}55 !important;
    filter: brightness(1.1) !important;
    border: none !important;
  }}
  div.stButton > button[kind="primary"]:active {{
    transform: scale(0.98) !important;
  }}
  div.stButton > button[kind="primary"]:disabled {{
    background: #9CA3AF !important;
    box-shadow: none !important;
    transform: none !important;
    filter: none !important;
    cursor: not-allowed !important;
    opacity: 0.7 !important;
  }}

  .stDownloadButton button,
  [data-testid="stDownloadButton"] button,
  .stButton [data-testid="baseButton-secondary"],
  .stButton button[kind="secondary"],
  button[data-testid="baseButton-secondary"] {{
    background: {T['card']} !important;
    color: {T['text2']} !important;
    border: 1.5px solid {T['border2']} !important;
    border-radius: 12px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 1.05rem !important;
    font-weight: 700 !important;
    padding: 1rem 1.4rem !important;
    transition: border-color 0.18s ease, box-shadow 0.18s ease, transform 0.18s ease !important;
    letter-spacing: 0.01em !important;
    box-shadow: 0 2px 6px rgba(0,0,0,0.04) !important;
    width: 100% !important;
  }}
  .stDownloadButton button:hover,
  [data-testid="stDownloadButton"] button:hover,
  .stButton [data-testid="baseButton-secondary"]:hover,
  button[data-testid="baseButton-secondary"]:hover {{
    background: {T['hover']} !important;
    border-color: {T['accent']} !important;
    color: {T['accent']} !important;
    transform: translateY(-3px) !important;
    box-shadow: 0 6px 20px {T['accent']}28 !important;
  }}

  /* ════ DOWNLOAD ACCENT BUTTON (PDF primario) ════ */
  .dl-accent-btn .stDownloadButton button,
  .dl-accent-btn [data-testid="stDownloadButton"] button {{
    background: linear-gradient(135deg, {T['accent']} 0%, {T['accent']}cc 100%) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 14px !important;
    font-size: 1.1rem !important;
    font-weight: 800 !important;
    padding: 1rem 1.6rem !important;
    min-height: 56px !important;
    letter-spacing: .01em !important;
    box-shadow: 0 4px 24px {T['accent']}55 !important;
    transition: all .2s cubic-bezier(.175,.885,.32,1.275) !important;
    width: 100% !important;
  }}
  .dl-accent-btn .stDownloadButton button:hover,
  .dl-accent-btn [data-testid="stDownloadButton"] button:hover {{
    filter: brightness(1.12) !important;
    box-shadow: 0 8px 32px {T['accent']}77 !important;
    transform: translateY(-2px) scale(1.01) !important;
  }}

  /* ════ ACTION CARD ════ */
  .action-card {{
    background: {T['card']} !important;
    border: 2px solid {T['border']} !important;
    border-radius: 14px !important;
    padding: 1.2rem !important;
    margin-bottom: 1rem !important;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
    position: relative !important;
    overflow: hidden !important;
  }}
  .action-card::before {{
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 4px;
    height: 100%;
    background: linear-gradient(180deg, {T['accent']} 0%, {T['accent']}00 100%);
    opacity: 0;
    transition: opacity 0.25s ease;
  }}
  .action-card:hover {{
    border-color: {T['accent']}88 !important;
    box-shadow: 0 8px 24px {T['accent']}15 !important;
    transform: translateY(-2px) !important;
  }}
  .action-card:hover::before {{
    opacity: 1;
  }}
  .action-card .stDownloadButton button,
  .action-card .stButton button {{
    background: linear-gradient(135deg, {T['accent']} 0%, {T['accent']}ee 100%) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 12px !important;
    font-size: 1rem !important;
    font-weight: 700 !important;
    padding: 1rem 1.5rem !important;
    box-shadow: 0 4px 14px {T['accent']}35 !important;
    transition: all 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275) !important;
  }}
  .action-card .stDownloadButton button:hover,
  .action-card .stButton button:hover {{
    transform: scale(1.03) !important;
    box-shadow: 0 6px 20px {T['accent']}50 !important;
    filter: brightness(1.08) !important;
  }}
  .action-card .stDownloadButton button:active,
  .action-card .stButton button:active {{
    transform: scale(0.98) !important;
  }}
  .action-card [data-testid="stExpander"] {{
    background: transparent !important;
    border: 2px dashed {T['border2']} !important;
    border-radius: 12px !important;
    transition: all 0.2s ease !important;
  }}
  .action-card [data-testid="stExpander"]:hover {{
    border-color: {T['accent']} !important;
    background: {T['accent_light']} !important;
  }}
  .action-card [data-testid="stExpander"] summary {{
    background: transparent !important;
    color: {T['text']} !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    padding: 1rem 1.2rem !important;
  }}
  .action-card [data-testid="stExpander"] summary:hover {{
    color: {T['accent']} !important;
  }}
  .action-card [data-testid="stExpander"] summary svg {{
    color: {T['accent']} !important;
  }}

  .tex-btn-wrap .stDownloadButton button,
  .tex-btn-wrap [data-testid="stDownloadButton"] button {{
    background: transparent !important;
    color: {T['muted']} !important;
    border: 1px solid {T['border']} !important;
    border-radius: 6px !important;
    font-size: 0.72rem !important;
    font-weight: 500 !important;
    padding: 0.3rem 0.7rem !important;
    width: 100% !important;
    box-shadow: none !important;
    transform: none !important;
  }}
  .tex-btn-wrap .stDownloadButton button:hover,
  .tex-btn-wrap [data-testid="stDownloadButton"] button:hover {{
    color: {T['text2']} !important;
    border-color: {T['border2']} !important;
    background: {T['card2']} !important;
    box-shadow: none !important;
    transform: translateY(-1px) !important;
  }}

  /* ════ EXPANDER ════ */
  [data-testid="stExpander"] {{
    background: {T['card']} !important;
    border: 1px solid {T['border']} !important;
    border-radius: 12px !important;
    margin-bottom: 0.75rem !important;
    overflow: hidden;
  }}
  [data-testid="stExpander"] summary {{
    padding: 0.85rem 1.1rem !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    color: {T['text']} !important;
    background: {T['card']} !important;
  }}
  [data-testid="stExpander"] summary:hover {{
    background: {T['hover']} !important;
  }}
  [data-testid="stExpander"] > div > div {{
    padding: 0.5rem 1.1rem 1rem !important;
  }}

  hr {{
    border: none;
    border-top: 1px solid {T['border']} !important;
    margin: 2rem 0 !important;
  }}

  [data-testid="stFileUploader"] section {{
    background: {T['card2']} !important;
    border: 1.5px dashed {T['border2']} !important;
    border-radius: 10px !important;
    padding: 0.75rem 1rem !important;
    min-height: unset !important;
  }}
  [data-testid="stFileUploader"] section > div {{ gap: 0.3rem !important; }}
  [data-testid="stFileUploadDropzone"] p,
  [data-testid="stFileUploadDropzone"] span,
  [data-testid="stFileUploadDropzone"] small,
  [data-testid="stFileUploader"] span,
  [data-testid="stFileUploader"] small,
  [data-testid="stFileUploader"] p {{
    color: {T['text2']} !important;
    opacity: 1 !important;
  }}
  [data-testid="stFileUploadDropzone"] button,
  [data-testid="stFileUploader"] button {{
    color: {T['accent']} !important;
    font-weight: 600 !important;
  }}
  [data-testid="stFileUploadDropzone"] svg {{
    fill: {T['muted']} !important;
    color: {T['muted']} !important;
  }}

  .chip {{
    display: inline-flex;
    align-items: center;
    gap: 4px;
    background: {T['accent_light']};
    color: {T['accent']};
    border: 1px solid {T['accent']};
    border-radius: 100px;
    padding: 2px 10px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
  }}

  .expander-heading {{
    font-size: 0.75rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.04em !important;
    text-transform: uppercase !important;
    color: {T['text2']} !important;
    margin: 1rem 0 0.4rem 0 !important;
    padding: 4px 10px !important;
    background: {T['card2']} !important;
    border-left: 3px solid {T['accent']} !important;
    border-radius: 0 6px 6px 0 !important;
    display: block !important;
  }}

  /* ════ STEP LABELS ════ */
  .step-label {{
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 2.2rem 0 0.75rem 0;
    font-family: 'DM Sans', sans-serif;
  }}
  .step-num {{
    width: 26px;
    height: 26px;
    border-radius: 50%;
    background: {T['accent']};
    color: #ffffff;
    font-size: 0.68rem;
    font-weight: 900;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    letter-spacing: 0;
    box-shadow: 0 2px 8px {T['accent']}55;
  }}
  .step-title {{
    font-size: 0.82rem;
    font-weight: 800;
    letter-spacing: 0.07em;
    text-transform: uppercase;
    color: {T['text']};
  }}
  .step-line {{
    flex: 1;
    height: 1px;
    background: linear-gradient(90deg, {T['border2']} 0%, transparent 100%);
  }}

  /* ════ AI HINT — leggibile su qualsiasi tema ════ */
  .ai-hint {{
    display: flex;
    align-items: center;
    gap: 9px;
    background: {T.get('hint_bg', T['accent_light'])};
    border: 1px solid {T.get('hint_border', T['accent'] + '55')};
    border-radius: 10px;
    padding: 9px 14px;
    font-size: 0.78rem;
    color: {T.get('hint_text', T['text2'])};
    margin: 1.8rem 0 0.6rem 0;
    font-family: 'DM Sans', sans-serif;
    line-height: 1.4;
  }}
  .ai-hint-icon {{ font-size: 1rem; flex-shrink: 0; }}
  .ai-hint strong {{ color: {T['accent']}; font-weight: 700; }}

  .modifica-hint {{
    display: flex;
    align-items: flex-start;
    gap: 10px;
    background: {T['bg2']};
    border: 1px solid {T['border']};
    border-left: 3px solid {T['accent']};
    border-radius: 10px;
    padding: 10px 14px;
    margin-bottom: 0.75rem;
    font-size: 0.8rem;
    color: {T['text2']};
    font-family: 'DM Sans', sans-serif;
    line-height: 1.5;
  }}
  .modifica-hint-icon {{ font-size: 1rem; flex-shrink: 0; margin-top: 1px; }}
  .modifica-hint strong {{ color: {T['text']}; font-weight: 700; }}

  /* ════ PERSONALIZZA EXPANDER ════ */
  .personalizza-wrap [data-testid="stExpander"] {{
    border: 1.5px solid {T['accent']}44 !important;
    border-radius: 14px !important;
    background: {T['card']} !important;
    box-shadow: 0 2px 16px {T['accent']}0f !important;
  }}
  .personalizza-wrap [data-testid="stExpander"] summary {{
    background: {T['accent_light']} !important;
    color: {T['text']} !important;
    font-weight: 700 !important;
    font-size: 0.92rem !important;
    padding: 1rem 1.2rem !important;
  }}
  .personalizza-wrap [data-testid="stExpander"] summary:hover {{
    background: {T['accent_light']} !important;
    filter: brightness(0.96);
  }}
  .personalizza-wrap [data-testid="stExpander"] summary svg {{
    color: {T['accent']} !important;
    fill: {T['accent']} !important;
  }}
  .personalizza-wrap [data-testid="stExpander"] > div > div {{
    padding: 1rem 1.2rem 1.2rem !important;
  }}

  /* ════ GENERA SECTION ════ */
  .genera-section {{
    margin-top: 2.2rem;
    margin-bottom: 0.5rem;
  }}

  /* ════ ONBOARDING — messaggio statico, sottile ════ */
  .onboard-guide {{
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 6px 10px;
    background: {T['bg2']};
    border: 1px solid {T['border']};
    border-radius: 10px;
    padding: .45rem .9rem;
    margin-bottom: .9rem;
    font-family: 'DM Sans', sans-serif;
  }}
  .onboard-step {{
    display: flex;
    align-items: center;
    gap: 5px;
    font-size: .7rem;
    color: {T['muted']};
    white-space: nowrap;
  }}
  .onboard-num {{
    font-size: .68rem;
    font-weight: 800;
    color: {T['accent']};
  }}
  .onboard-sep {{
    font-size: .62rem;
    color: {T['muted']};
    opacity: .5;
  }}

  .opt-label {{
    font-size: 0.72rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.06em !important;
    text-transform: uppercase !important;
    color: {T['text2']} !important;
    margin: 0.7rem 0 0.3rem 0 !important;
    display: block !important;
    font-family: 'DM Sans', sans-serif !important;
  }}

  /* ════ PULSANTE SECONDARIO OUTLINE ════ */
  .btn-secondary-accent div.stButton > button,
  .btn-secondary-accent .stButton > button {{
    background: transparent !important;
    color: {T['accent']} !important;
    border: 1.5px solid {T['accent']}88 !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: .88rem !important;
    padding: 0.45rem 1rem !important;
    min-height: 38px !important;
    box-shadow: none !important;
    transition: border-color .15s ease, color .15s ease !important;
  }}
  .btn-secondary-accent div.stButton > button:hover,
  .btn-secondary-accent .stButton > button:hover {{
    border-color: {T['accent']} !important;
    background: {T['accent_light']} !important;
  }}

  /* ════ STAGE 3 SECTION TITLES ════ */
  .s3-section-title {{
    font-size: .68rem;
    font-weight: 800;
    letter-spacing: .1em;
    text-transform: uppercase;
    color: {T['muted']};
    margin: 1.1rem 0 .65rem 0;
    padding-bottom: .4rem;
    border-bottom: 1px solid {T['border']};
    display: flex;
    align-items: center;
    gap: 7px;
    font-family: 'DM Sans', sans-serif;
  }}
  .s3-section-title::before {{
    content: '';
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: {T['accent']};
    display: inline-block;
    flex-shrink: 0;
  }}

  .s3-card-label {{
    font-size: .65rem;
    font-weight: 700;
    letter-spacing: .09em;
    text-transform: uppercase;
    color: {T['muted']};
    margin: .8rem 0 .35rem 0;
    font-family: 'DM Sans', sans-serif;
  }}

  /* ════ HINT DOCX ════ */
  .hint-docx {{
    background: {T.get('hint_bg', T['accent_light'])} !important;
    border-left: 3px solid {T['accent']} !important;
    border-radius: 8px !important;
    padding: 10px 14px !important;
    margin-top: 8px !important;
    font-size: 0.8rem !important;
    color: {T.get('hint_text', T['text2'])} !important;
    line-height: 1.5 !important;
  }}
  .hint-docx strong {{
    color: {T['accent']} !important;
  }}

  /* ════ MISC ════ */
  .section-label {{
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: {T['muted']};
    margin: 1.2rem 0 0.5rem 0;
    padding-bottom: 0.3rem;
    border-bottom: 1px solid {T['border']};
  }}

  .hint {{
    font-size: 0.78rem;
    color: {T['muted']};
    margin-top: 4px;
    line-height: 1.4;
  }}

  .stSelectSlider [data-testid="stMarkdownContainer"] p {{
    color: {T['text']} !important;
    font-size: 0.88rem !important;
  }}
  .stSlider [data-baseweb="slider"] [role="slider"] {{
    background: {T['accent']} !important;
    border-color: {T['accent']} !important;
  }}
  .stSlider [data-baseweb="slider"] div[data-testid="stTickBar"] {{
    color: {T['muted']} !important;
  }}

  .stToggle [data-baseweb="toggle"] {{
    background: {T['border2']} !important;
    border-radius: 100px !important;
    transition: background 0.2s ease;
  }}
  .stToggle [data-baseweb="toggle"][aria-checked="true"] {{
    background: {T['accent']} !important;
  }}
  /* Etichetta e testo toggle — visibile su tema chiaro E scuro */
  .stToggle span,
  .stToggle label,
  .stToggle p,
  .stToggle [data-testid="stWidgetLabel"] p,
  .stToggle [data-testid="stMarkdownContainer"] p {{
    color: {T['text']} !important;
    font-size: 0.88rem !important;
    font-family: 'DM Sans', sans-serif !important;
  }}
  /* Testo help (? tooltip) accanto a toggle e checkbox */
  [data-testid="stTooltipIcon"] {{
    opacity: 0.7;
  }}
  [data-testid="stTooltipIcon"] svg {{
    fill: {T['muted']} !important;
    color: {T['muted']} !important;
  }}
  /* Messaggio di help/hint inline accanto ai widget (testo dopo ✓) */
  .stCheckbox [data-testid="stMarkdownContainer"] p,
  .stCheckbox label p,
  .stCheckbox label span,
  [data-baseweb="checkbox"] span,
  [data-baseweb="checkbox"] p,
  [data-baseweb="checkbox"] label {{
    color: {T['text']} !important;
    font-family: 'DM Sans', sans-serif !important;
  }}
  /* Caption/help text sotto i widget */
  .stTextInput .stCaption, .stSelectbox .stCaption,
  [data-testid="stWidgetLabel"] small,
  [data-testid="stCaptionContainer"] p,
  .stCaption p,
  [data-testid="InputInstructions"] p {{
    color: {T['muted']} !important;
  }}

  .stRadio [data-testid="stMarkdownContainer"] p {{
    color: {T['text']} !important;
    font-size: 0.9rem !important;
    font-family: 'DM Sans', sans-serif !important;
  }}
  .stRadio > div {{ gap: 6px !important; }}
  .stRadio [role="radio"] {{
    background: {T['input_bg']} !important;
    border: 1.5px solid {T['border2']} !important;
    border-radius: 50% !important;
  }}
  .stRadio [role="radio"][aria-checked="true"] {{
    border-color: {T['accent']} !important;
    background: {T['accent']} !important;
  }}

  /* ════ TOASTS / ALERTS ════ */
  .stAlert {{
    border-radius: 10px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.88rem !important;
  }}

  /* ════ FAB FEEDBACK (in alto a destra) ════ */
  .fab-link {{
    position: fixed;
    top: .55rem;
    right: 1rem;
    z-index: 9998;
    background: {T['card']};
    border: 1.5px solid {T['border2']};
    color: {T['text2']};
    text-decoration: none;
    font-family: 'DM Sans', sans-serif;
    font-size: 0.72rem;
    font-weight: 600;
    padding: 5px 11px;
    border-radius: 100px;
    box-shadow: 0 2px 10px rgba(0,0,0,.15);
    transition: border-color 0.15s ease, color 0.15s ease, box-shadow 0.15s ease;
    backdrop-filter: blur(8px);
    white-space: nowrap;
    width: auto;
  }}
  .fab-link:hover {{
    border-color: {T['accent']};
    color: {T['accent']};
    box-shadow: 0 4px 14px {T['accent']}33;
  }}

  /* ════ APP FOOTER ════ */
  .app-footer {{
    text-align: center;
    font-size: 0.72rem;
    color: {T['muted']};
    font-family: 'DM Sans', sans-serif;
    padding: 1.5rem 0 0.5rem 0;
    line-height: 1.6;
    border-top: 1px solid {T['border']};
    margin-top: 2rem;
  }}

  /* ════ MONTHLY BAR ════ */
  .monthly-bar {{
    background: #161513;
    border: 1px solid #252320;
    border-radius: 10px;
    padding: 0.7rem 0.85rem;
    margin: 0.4rem 0 0 0;
  }}
  .monthly-bar-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 7px;
  }}
  .monthly-bar-label {{
    font-size: 0.7rem;
    font-weight: 600;
    color: #9B9890;
    font-family: 'DM Sans', sans-serif;
    letter-spacing: .03em;
  }}
  .monthly-bar-count {{
    font-size: 0.72rem;
    font-weight: 800;
    color: #D4D2CA;
    font-family: 'DM Sans', sans-serif;
    letter-spacing: 0.03em;
  }}
  .monthly-bar-count.limit-reached {{ color: #ef4444; }}
  .monthly-bar-count.limit-near    {{ color: #D97706; }}
  .monthly-progress {{
    background: #252320;
    border-radius: 100px;
    height: 4px;
    overflow: hidden;
  }}
  .monthly-progress-fill {{
    height: 100%;
    border-radius: 100px;
    transition: width 0.5s ease;
  }}

  /* ════ USER PILL ════ */
  .user-pill {{
    display: flex;
    align-items: center;
    gap: 10px;
    background: #161513;
    border: 1px solid #252320;
    border-radius: 12px;
    padding: 0.6rem 0.85rem;
    margin: 0.5rem 0;
  }}
  .user-avatar {{
    width: 32px; height: 32px;
    border-radius: 50%;
    background: linear-gradient(135deg, #D97706, #16a34a);
    color: #ffffff;
    font-size: 0.82rem;
    font-weight: 800;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    font-family: 'DM Sans', sans-serif;
    box-shadow: 0 2px 8px rgba(217,119,6,.4);
  }}
  .user-info {{ flex: 1; min-width: 0; }}
  .user-email {{
    font-size: 0.76rem;
    font-weight: 600;
    color: #d8d6ce;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    font-family: 'DM Sans', sans-serif;
  }}
  .user-role {{
    font-size: 0.63rem;
    color: #4e4c44;
    font-family: 'DM Sans', sans-serif;
    margin-top: 2px;
    font-weight: 500;
  }}

  /* ════ SIDEBAR STORICO BUTTONS ════ */
  [data-testid="stSidebar"] .stButton > button,
  [data-testid="stSidebar"] .stButton > button[kind="secondary"],
  [data-testid="stSidebar"] button[data-testid="baseButton-secondary"],
  [data-testid="stSidebar"] .stDownloadButton button,
  [data-testid="stSidebar"] [data-testid="stDownloadButton"] button {{
    background: #191815 !important;
    color: #c8c6bc !important;
    border: 1px solid #272522 !important;
    border-radius: 8px !important;
    font-size: 0.8rem !important;
    font-weight: 600 !important;
    box-shadow: none !important;
    transform: none !important;
    padding: 7px 12px !important;
    min-height: 34px !important;
    width: 100% !important;
    letter-spacing: .01em !important;
  }}
  [data-testid="stSidebar"] .stButton > button:hover,
  [data-testid="stSidebar"] .stButton > button[kind="secondary"]:hover,
  [data-testid="stSidebar"] button[data-testid="baseButton-secondary"]:hover,
  [data-testid="stSidebar"] .stDownloadButton button:hover,
  [data-testid="stSidebar"] [data-testid="stDownloadButton"] button:hover {{
    background: #221f18 !important;
    border-color: #D97706 !important;
    color: #f5c842 !important;
    transform: none !important;
    box-shadow: none !important;
  }}

  /* ── Storico expanders ── */
  [data-testid="stSidebar"] [data-testid="stExpander"] {{
    background: #161513 !important;
    border: 1px solid #222018 !important;
    border-radius: 10px !important;
    margin-bottom: 4px !important;
  }}
  [data-testid="stSidebar"] [data-testid="stExpander"] summary {{
    background: #161513 !important;
    color: #b0ae9e !important;
    font-size: 0.8rem !important;
    font-weight: 600 !important;
    padding: 0.6rem 0.9rem !important;
    letter-spacing: .01em !important;
  }}
  [data-testid="stSidebar"] [data-testid="stExpander"] summary:hover {{
    background: #1f1d18 !important;
    color: #e8e6e0 !important;
  }}
  [data-testid="stSidebar"] [data-testid="stExpander"] > div > div {{
    background: #161513 !important;
    padding: 0.4rem 0.9rem 0.75rem !important;
  }}
  [data-testid="stSidebar"] [data-testid="stExpander"] p,
  [data-testid="stSidebar"] [data-testid="stExpander"] span {{
    color: #b0ae9e !important;
  }}

  /* Buttons inside storico expanders */
  [data-testid="stSidebar"] [data-testid="stExpander"] .stButton > button,
  [data-testid="stSidebar"] [data-testid="stExpander"] div.stButton > button,
  [data-testid="stSidebar"] [data-testid="stExpander"] button {{
    background: #1f1d18 !important;
    color: #a8a698 !important;
    border: 1px solid #2e2a22 !important;
    border-radius: 7px !important;
    font-size: 0.76rem !important;
    font-weight: 600 !important;
    padding: 5px 10px !important;
    min-height: 30px !important;
    box-shadow: none !important;
    width: 100% !important;
  }}
  [data-testid="stSidebar"] [data-testid="stExpander"] .stButton > button:hover,
  [data-testid="stSidebar"] [data-testid="stExpander"] div.stButton > button:hover {{
    background: #D97706 !important;
    border-color: #D97706 !important;
    color: #fff !important;
  }}
  /* Elimina button */
  [data-testid="stSidebar"] [data-testid="stExpander"] .elimina-btn .stButton > button,
  [data-testid="stSidebar"] [data-testid="stExpander"] .elimina-btn button {{
    background: transparent !important;
    border-color: #3d1515 !important;
    color: #f87171 !important;
  }}
  [data-testid="stSidebar"] [data-testid="stExpander"] .elimina-btn .stButton > button:hover,
  [data-testid="stSidebar"] [data-testid="stExpander"] .elimina-btn button:hover {{
    background: #1f0a0a !important;
    border-color: #f87171 !important;
    color: #fca5a5 !important;
  }}
  /* Stella button */
  [data-testid="stSidebar"] [data-testid="stExpander"] .stella-btn .stButton > button,
  [data-testid="stSidebar"] [data-testid="stExpander"] .stella-btn button {{
    background: transparent !important;
    border-color: #3a3420 !important;
    color: #7a7040 !important;
    font-size: 1rem !important;
    padding: 2px 6px !important;
    width: auto !important;
    min-height: unset !important;
  }}
  [data-testid="stSidebar"] [data-testid="stExpander"] .stella-btn-on .stButton > button,
  [data-testid="stSidebar"] [data-testid="stExpander"] .stella-btn-on button {{
    background: #2a1e06 !important;
    border-color: #D97706 !important;
    color: #F59E0B !important;
    width: auto !important;
    min-height: unset !important;
  }}

  /* Logout final overrides (avoid conflicts) */
  [data-testid="stSidebar"] .logout-btn-wrap .stButton > button,
  [data-testid="stSidebar"] .logout-btn-wrap button {{
    background: transparent !important;
    color: #f87171 !important;
    border: 1px solid #3d1515 !important;
    border-radius: 8px !important;
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    padding: 6px 14px !important;
    width: 100% !important;
    min-height: unset !important;
    box-shadow: none !important;
  }}
  [data-testid="stSidebar"] .logout-btn-wrap .stButton > button:hover,
  [data-testid="stSidebar"] .logout-btn-wrap button:hover {{
    background: #1f0a0a !important;
    border-color: #f87171 !important;
    color: #fca5a5 !important;
    box-shadow: none !important;
    transform: none !important;
  }}

  @keyframes tooltipSlideIn {{
    0%   {{ opacity: 0; transform: translateX(-12px); }}
    15%  {{ opacity: 1; transform: translateX(4px); }}
    25%  {{ opacity: 1; transform: translateX(0); }}
    75%  {{ opacity: 1; transform: translateX(0); }}
    90%  {{ opacity: 0; transform: translateX(-8px); }}
    100% {{ opacity: 0; transform: translateX(-8px); }}
  }}
  .sidebar-tooltip {{
    position: fixed;
    top: 0.9rem;
    left: 3.8rem;
    z-index: 9998;
    display: flex;
    align-items: center;
    gap: 7px;
    background: {T['accent']};
    color: #ffffff;
    font-family: 'DM Sans', sans-serif;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.02em;
    padding: 7px 13px 7px 10px;
    border-radius: 20px;
    box-shadow: 0 4px 18px {T['accent']}55;
    pointer-events: none;
    white-space: nowrap;
    animation: tooltipSlideIn 4.5s ease forwards;
  }}
  .sidebar-tooltip::before {{
    content: '';
    position: absolute;
    left: -6px;
    top: 50%;
    transform: translateY(-50%);
    border-width: 5px 6px 5px 0;
    border-style: solid;
    border-color: transparent {T['accent']} transparent transparent;
  }}

  /* ════ OCR HINT BANNER — banner suggerimento upload con scrittura a mano ════ */
  .ocr-hint-banner {{
    background: linear-gradient(135deg, {T['accent']}18 0%, {T['card2']} 100%);
    border: 1.5px solid {T['accent']}55;
    border-radius: 14px;
    padding: 0.85rem 1.1rem;
    margin-bottom: 0.75rem;
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
    position: relative;
    overflow: hidden;
  }}
  .ocr-hint-banner::after {{
    content: '';
    position: absolute;
    top: 0; right: 0;
    width: 60px; height: 100%;
    background: linear-gradient(90deg, transparent, {T['accent']}08);
    pointer-events: none;
  }}
  .ocr-hint-icon {{
    font-size: 1.6rem;
    flex-shrink: 0;
    line-height: 1;
    margin-top: 2px;
  }}
  .ocr-hint-body {{
    flex: 1;
    min-width: 0;
  }}
  .ocr-hint-title {{
    font-size: 0.82rem;
    font-weight: 800;
    color: {T['accent']};
    font-family: 'DM Sans', sans-serif;
    margin-bottom: 0.2rem;
    letter-spacing: 0.01em;
  }}
  .ocr-hint-desc {{
    font-size: 0.73rem;
    color: {T['text2']};
    font-family: 'DM Sans', sans-serif;
    line-height: 1.5;
  }}
  .ocr-hint-desc strong {{
    color: {T['text']};
    font-weight: 700;
  }}
  .ocr-hint-tags {{
    display: flex;
    flex-wrap: wrap;
    gap: 0.3rem;
    margin-top: 0.45rem;
  }}
  .ocr-hint-tag {{
    font-size: 0.65rem;
    font-weight: 700;
    background: {T['accent']}22;
    color: {T['accent']};
    border: 1px solid {T['accent']}44;
    border-radius: 100px;
    padding: 2px 9px;
    letter-spacing: 0.04em;
    text-transform: uppercase;
  }}

  /* ════ DOC TYPE BADGE — badge tipo documento nella lista file ════ */
  .doc-type-verifica  {{ background: #0D3D2B !important; color: #34D399 !important; border: 1px solid #34D39944 !important; }}
  .doc-type-esercizi  {{ background: #1A2D4A !important; color: #60A5FA !important; border: 1px solid #60A5FA44 !important; }}
  .doc-type-esercizio {{ background: #1A2D4A !important; color: #60A5FA !important; border: 1px solid #60A5FA44 !important; }}
  .doc-type-appunti   {{ background: #2D1A3A !important; color: #C084FC !important; border: 1px solid #C084FC44 !important; }}
  .doc-type-libro     {{ background: #2A1F0A !important; color: #FCD34D !important; border: 1px solid #FCD34D44 !important; }}
  .doc-type-misto     {{ background: #1C1C1E !important; color: #9CA3AF !important; border: 1px solid #4A4A4C44 !important; }}
  /* Light mode overrides for doc badges */
  .doc-type-verifica-light  {{ background: #D1FAE5 !important; color: #065F46 !important; border: 1px solid #6EE7B7 !important; }}
  .doc-type-esercizi-light  {{ background: #DBEAFE !important; color: #1E40AF !important; border: 1px solid #93C5FD !important; }}
  .doc-type-appunti-light   {{ background: #EDE9FE !important; color: #5B21B6 !important; border: 1px solid #C4B5FD !important; }}
  .doc-type-libro-light     {{ background: #FEF3C7 !important; color: #92400E !important; border: 1px solid #FDE68A !important; }}

  /* ════ DOC PILL CONFIRMED — pill file confermato con label uso ════ */
  .doc-pill-confirmed {{
    background: {T['card']};
    border: 1px solid {T['border']};
    border-radius: 10px;
    padding: 0.5rem 0.85rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-wrap: wrap;
  }}
  .doc-pill-confirmed:hover {{
    border-color: {T['border2']};
    background: {T['bg2']};
  }}
  .doc-pill-fname {{
    font-size: 0.76rem;
    font-weight: 700;
    color: {T['text']};
    font-family: 'DM Sans', sans-serif;
    max-width: 200px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }}
  .doc-pill-arg {{
    font-size: 0.63rem;
    color: {T['muted']};
    font-family: 'DM Sans', sans-serif;
    margin-left: auto;
    flex-shrink: 0;
  }}
  .doc-pill-label-uso {{
    font-size: 0.62rem;
    font-weight: 600;
    background: {T['hint_bg']};
    color: {T['hint_text']};
    border: 1px solid {T['hint_border']};
    border-radius: 5px;
    padding: 2px 8px;
    white-space: nowrap;
    letter-spacing: 0.02em;
  }}

  /* ════ CLASSIFICAZIONE BADGE — verifica vs esercizi ════ */
  .classif-verifica {{
    display: inline-flex; align-items: center; gap: 5px;
    background: {T['success']}18;
    border: 1.5px solid {T['success']}66;
    border-radius: 8px;
    padding: 3px 10px;
    font-size: 0.72rem;
    font-weight: 700;
    color: {T['success']};
    font-family: 'DM Sans', sans-serif;
    letter-spacing: 0.03em;
  }}
  .classif-esercizi {{
    display: inline-flex; align-items: center; gap: 5px;
    background: {T['accent']}15;
    border: 1.5px solid {T['accent']}66;
    border-radius: 8px;
    padding: 3px 10px;
    font-size: 0.72rem;
    font-weight: 700;
    color: {T['accent']};
    font-family: 'DM Sans', sans-serif;
    letter-spacing: 0.03em;
  }}

  /* ════ ESERCIZI RECAP CARDS — card per ogni esercizio rilevato ════ */
  .es-recap-card {{
    background: {T['card2']};
    border: 1px solid {T['border']};
    border-left: 3px solid {T['accent']};
    border-radius: 0 10px 10px 0;
    padding: 0.55rem 0.85rem;
    margin-bottom: 0.45rem;
  }}
  .es-recap-card:hover {{
    border-left-color: {T['accent']};
    box-shadow: 0 2px 10px {T['accent']}15;
  }}
  .es-recap-header {{
    display: flex;
    align-items: center;
    gap: 0.45rem;
    flex-wrap: wrap;
    margin-bottom: 0.3rem;
  }}
  .es-recap-num {{
    font-size: 0.78rem;
    font-weight: 800;
    color: {T['accent']};
    font-family: 'DM Sans', sans-serif;
  }}
  .es-recap-tipo {{
    font-size: 0.63rem;
    background: {T['accent_light']};
    color: {T['accent']};
    border-radius: 4px;
    padding: 1px 7px;
    font-weight: 700;
  }}
  .es-recap-source {{
    font-size: 0.62rem;
    color: {T['muted']};
    margin-left: auto;
    font-family: 'DM Sans', sans-serif;
  }}
  .es-recap-testo {{
    font-size: 0.75rem;
    color: {T['text2']};
    font-family: 'DM Sans', sans-serif;
    font-style: italic;
    line-height: 1.45;
    margin-top: 0.1rem;
  }}

  /* ════ DELETE BAR — barra di gestione/eliminazione in fondo alla lista ════ */
  .delete-bar {{
    background: {T['bg2']};
    border: 1px solid {T['border']};
    border-radius: 10px;
    padding: 0.5rem 0.8rem;
    margin-top: 0.6rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
  }}
  .delete-bar-label {{
    font-size: 0.72rem;
    color: {T['muted']};
    font-family: 'DM Sans', sans-serif;
    letter-spacing: 0.03em;
  }}

  /* ════ SEZIONE TITOLI UPLOAD con accento ════ */
  .upload-section-header {{
    display: flex;
    align-items: center;
    gap: 0.6rem;
    margin-bottom: 0.5rem;
  }}
  .upload-section-dot {{
    width: 8px; height: 8px;
    border-radius: 50%;
    background: {T['accent']};
    box-shadow: 0 0 6px {T['accent']}88;
    flex-shrink: 0;
  }}
  .upload-section-title {{
    font-size: 0.82rem;
    font-weight: 800;
    color: {T['text']};
    font-family: 'DM Sans', sans-serif;
    letter-spacing: 0.01em;
  }}
  .upload-section-sub {{
    font-size: 0.7rem;
    color: {T['text2']};
    font-family: 'DM Sans', sans-serif;
    margin-left: auto;
    flex-shrink: 0;
  }}

  /* ════ OPZIONE MENU DROPDOWN — stile migliorato ════ */
  .opzione-menu-row {{
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.35rem 0;
  }}
  .opzione-menu-icon {{
    font-size: 0.9rem;
    flex-shrink: 0;
    width: 20px;
    text-align: center;
  }}
  .opzione-menu-label {{
    font-size: 0.78rem;
    font-weight: 600;
    color: {T['text']};
    font-family: 'DM Sans', sans-serif;
  }}

  /* ════ OVERFLOW — impedisce scroll orizzontale su mobile/tablet ════ */
  html, body {{
    overflow-x: hidden !important;
    max-width: 100vw !important;
  }}
  .stApp {{
    overflow-x: hidden !important;
    max-width: 100vw !important;
  }}
  /* Tutti i container non escono dal viewport */
  .block-container,
  [data-testid="stAppViewContainer"],
  [data-testid="stVerticalBlock"],
  [data-testid="stHorizontalBlock"] {{
    max-width: 100% !important;
    box-sizing: border-box !important;
  }}

  /* ════ RESPONSIVE ════ */
  /* ── Mobile ≤640px ── */
  @media (max-width: 640px) {{
    .hero-title {{ font-size: 52px !important; }}
    /* Breadcrumb pill compatto su mobile */
    .breadcrumb-pill {{
      padding: .45rem .9rem !important;
      gap: 6px !important;
    }}
    .breadcrumb-pill .bc-label {{
      font-size: .72rem !important;
    }}
    .breadcrumb-pill .bc-circle {{
      width: 22px !important;
      height: 22px !important;
      font-size: .6rem !important;
    }}
    .breadcrumb-pill .bc-sep {{
      width: 16px !important;
    }}
    .block-container {{
      padding: 3.5rem 0.75rem 2.5rem !important;
      width: 100% !important;
      max-width: 100% !important;
      zoom: 1 !important;
    }}
    .stTextInput input, .stNumberInput input {{
      min-height: 48px !important;
      height: 48px !important;
      line-height: 1.4 !important;
      font-size: 0.95rem !important;
    }}
    .stTextInput > div > div {{ min-height: 48px !important; }}
    .stTextInput input::placeholder,
    .stNumberInput input::placeholder {{ font-size: 0.95rem !important; opacity: 1 !important; }}
    .stSelectbox [data-baseweb="select"] > div:first-child {{
      padding: 10px 12px !important;
      min-height: 46px !important;
      height: auto !important;
    }}
    .stTextArea textarea {{ font-size: 0.9rem !important; }}
    .stButton button {{ min-height: 46px !important; font-size: 0.95rem !important; }}
    [data-testid="stSidebar"] .block-container {{ padding: 1rem !important; }}
    .stDownloadButton button {{ width: 100% !important; min-height: 46px !important; }}
  }}

  /* ── Tablet piccolo 641–767px ── */
  @media (min-width: 641px) and (max-width: 767px) {{
    .block-container {{
      padding: 1.5rem 1rem 2.5rem !important;
      max-width: 100% !important;
      zoom: 1 !important;
    }}
  }}

  /* ── Tablet grande 768–1024px ── */
  @media (min-width: 768px) and (max-width: 1024px) {{
    .block-container {{
      padding: 1.5rem 1.5rem 3rem !important;
      max-width: 900px !important;
      zoom: 1 !important;
    }}
  }}

  /* ════ PUNTEGGIO MODIFICA (Stage 2) ════ */
  .score-edit-wrap .stNumberInput input {{
    font-size: 0.9rem !important;
    min-height: 36px !important;
    height: 36px !important;
    padding: 6px 10px !important;
    text-align: center !important;
  }}
  .score-edit-wrap label {{ display: none !important; }}

  /* ════ PANNELLO RICALIBRA PUNTEGGI ════ */
  .recalibra-panel {{
    background: {T['card']};
    border: 2px solid {T['border2']};
    border-radius: 14px;
    padding: 1.1rem 1.2rem 1.2rem 1.2rem;
    margin: 1.2rem 0 .8rem 0;
  }}
  .recalibra-title {{
    font-family: 'DM Sans', sans-serif;
    font-size: .78rem;
    font-weight: 800;
    letter-spacing: .07em;
    text-transform: uppercase;
    color: {T['accent']};
    margin-bottom: .75rem;
    display: flex;
    align-items: center;
    gap: 7px;
  }}
  .recalibra-title::before {{
    content: '';
    width: 6px; height: 6px;
    border-radius: 50%;
    background: {T['accent']};
    flex-shrink: 0;
    display: inline-block;
  }}
  .recalibra-row {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    padding: .4rem .1rem;
    border-bottom: 1px solid {T['border']};
    font-family: 'DM Sans', sans-serif;
    font-size: .83rem;
    color: {T['text2']};
  }}
  .recalibra-row:last-of-type {{ border-bottom: none; }}
  .recalibra-sum-ok {{
    display: flex; align-items: center; gap: 8px;
    background: {T['success']}18;
    border: 1.5px solid {T['success']};
    border-radius: 10px;
    padding: .55rem 1rem;
    margin-top: .75rem;
    font-size: .82rem;
    font-weight: 700;
    color: {T['success']};
    font-family: 'DM Sans', sans-serif;
  }}
  .recalibra-sum-err {{
    display: flex; align-items: center; gap: 8px;
    background: {T['err']}12;
    border: 1.5px solid {T['err']};
    border-radius: 10px;
    padding: .55rem 1rem;
    margin-top: .75rem;
    font-size: .82rem;
    font-weight: 700;
    color: {T.get('hint_text', T['err'])};
    font-family: 'DM Sans', sans-serif;
  }}

  /* ════ PULSANTE CONFERMA ORO — full-width, colore ambra ════ */
  .btn-confirm-gold div.stButton > button,
  .btn-confirm-gold .stButton > button {{
    background: linear-gradient(135deg, #F59E0B 0%, #D97706 100%) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 14px !important;
    font-size: 1.08rem !important;
    font-weight: 800 !important;
    min-height: 54px !important;
    padding: 0.75rem 1.5rem !important;
    box-shadow: 0 4px 20px #F59E0B55 !important;
    transition: all .2s cubic-bezier(.175,.885,.32,1.275) !important;
    letter-spacing: .01em !important;
    width: 100% !important;
  }}
  .btn-confirm-gold div.stButton > button:hover,
  .btn-confirm-gold .stButton > button:hover {{
    filter: brightness(1.08) !important;
    box-shadow: 0 8px 32px #F59E0B77 !important;
    transform: translateY(-2px) scale(1.01) !important;
  }}
  .btn-confirm-gold div.stButton > button:active,
  .btn-confirm-gold .stButton > button:active {{
    transform: scale(0.98) !important;
  }}

  /* ════ PULSANTE RICONFIGURA PICCOLO ════ */
  .btn-riconfigura-small div.stButton > button,
  .btn-riconfigura-small .stButton > button {{
    background: transparent !important;
    color: {T['muted']} !important;
    border: 1px solid {T['border']} !important;
    border-radius: 8px !important;
    font-size: .78rem !important;
    font-weight: 500 !important;
    min-height: 32px !important;
    padding: 0.25rem 0.75rem !important;
    box-shadow: none !important;
    width: auto !important;
    display: inline-block !important;
  }}
  .btn-riconfigura-small div.stButton > button:hover,
  .btn-riconfigura-small .stButton > button:hover {{
    color: {T['text2']} !important;
    border-color: {T['border2']} !important;
    background: {T['hover']} !important;
  }}

  /* ════ Bottoni RIMUOVI / X — compatti nel layout pill ════ */
  [data-testid="stHorizontalBlock"] > [data-testid="column"]:last-child > [data-testid="stVerticalBlock"] button,
  [data-testid="stHorizontalBlock"] > [data-testid="column"]:last-child button[kind="secondary"] {{
    min-height: 28px !important;
    max-height: 30px !important;
    height: 28px !important;
    padding: 0 7px !important;
    font-size: .72rem !important;
    line-height: 1 !important;
    align-self: center !important;
    margin-top: 3px !important;
    background: transparent !important;
    color: {T['muted']} !important;
    border: 1px solid {T['border2']} !important;
    border-radius: 6px !important;
  }}
  [data-testid="stHorizontalBlock"] > [data-testid="column"]:last-child button[kind="secondary"]:hover {{
    border-color: #EF4444 !important;
    color: #EF4444 !important;
  }}

  /* ════ ZOOM 110% su desktop largo ≥1025px ════ */
  @media (min-width: 1025px) {{
    .block-container {{
      zoom: 1.1;
      max-width: 955px !important;
    }}
  }}

  /* ════ Bottoni secondari (back / rimuovi) piccoli e discreti ════ */
  /* Applica a tutti i button dentro colonne molto strette (ratio 1/12 o 1/9) */
  div[data-testid="column"]:has(> div > div > div > div > button[kind="secondary"]) button[kind="secondary"],
  div[data-testid="stButton"] > button[kind="secondary"] {{
    font-size: .72rem !important;
    padding: 3px 10px !important;
    min-height: 0 !important;
    height: auto !important;
    line-height: 1.4 !important;
    border-radius: 7px !important;
    color: {T['muted']} !important;
    border-color: {T['border2']} !important;
    background: transparent !important;
    white-space: nowrap;
  }}

  /* ═══════════════════════════════════════════════════════════════════
     IDEA #11 — SKELETON OCR ANIMATO
     Mostra un'animazione "lettura documento" durante l'analisi AI.
  ═══════════════════════════════════════════════════════════════════ */

  @keyframes skeletonPulse {{
    0%   {{ opacity: .35; transform: scaleX(.92); }}
    50%  {{ opacity: .85; transform: scaleX(1); }}
    100% {{ opacity: .35; transform: scaleX(.92); }}
  }}
  @keyframes scanLine {{
    0%   {{ top: 6px; opacity: .9; }}
    100% {{ top: calc(100% - 6px); opacity: .3; }}
  }}
  @keyframes fadeInUp {{
    from {{ opacity: 0; transform: translateY(10px); }}
    to   {{ opacity: 1; transform: translateY(0); }}
  }}
  @keyframes badgePop {{
    0%   {{ opacity: 0; transform: translateY(-6px) scale(.92); }}
    70%  {{ transform: translateY(2px) scale(1.03); }}
    100% {{ opacity: 1; transform: translateY(0) scale(1); }}
  }}
  @keyframes pulseGlow {{
    0%, 100% {{ box-shadow: 0 0 0 0 {T['accent']}44; }}
    50%       {{ box-shadow: 0 0 0 8px {T['accent']}00; }}
  }}

  .ocr-skeleton-wrap {{
    background: {T['card']};
    border: 1.5px solid {T['border']};
    border-radius: 14px;
    padding: 1.1rem 1.3rem 1rem;
    margin: .6rem 0 1rem;
    position: relative;
    overflow: hidden;
  }}
  .ocr-skeleton-header {{
    display: flex;
    align-items: center;
    gap: .65rem;
    margin-bottom: .9rem;
  }}
  .ocr-skeleton-icon {{
    font-size: 1.3rem;
    animation: skeletonPulse 1.4s ease-in-out infinite;
  }}
  .ocr-skeleton-title {{
    font-size: .82rem;
    font-weight: 700;
    color: {T['text']};
    font-family: DM Sans, sans-serif;
  }}
  .ocr-skeleton-sub {{
    font-size: .7rem;
    color: {T['muted']};
    font-family: DM Sans, sans-serif;
    margin-top: 1px;
  }}
  .ocr-skeleton-doc {{
    background: {T['card2']};
    border: 1px solid {T['border']};
    border-radius: 8px;
    padding: .7rem .9rem;
    position: relative;
    overflow: hidden;
  }}
  .ocr-skeleton-scan {{
    position: absolute;
    left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent, {T['accent']}cc, transparent);
    animation: scanLine 1.8s linear infinite;
    pointer-events: none;
  }}
  .ocr-skeleton-line {{
    height: 8px;
    border-radius: 100px;
    background: {T['border2']};
    margin-bottom: 7px;
    transform-origin: left center;
    animation: skeletonPulse 1.6s ease-in-out infinite;
  }}
  .ocr-skeleton-step {{
    display: flex;
    align-items: center;
    gap: .5rem;
    margin-top: .75rem;
    font-size: .72rem;
    font-weight: 600;
    color: {T['accent']};
    font-family: DM Sans, sans-serif;
    animation: fadeInUp .4s ease both;
  }}
  .ocr-skeleton-dot {{
    width: 7px; height: 7px;
    border-radius: 50%;
    background: {T['accent']};
    animation: skeletonPulse 1s ease-in-out infinite;
    flex-shrink: 0;
  }}

  /* Badge classificazione — animazione entrata */
  .classif-badge-animated {{
    animation: badgePop .45s cubic-bezier(.34,1.56,.64,1) both;
  }}

  /* Bottone primario con pulse quando abilitato */
  .genera-ready-btn > button {{
    animation: pulseGlow 2.2s ease-in-out infinite !important;
  }}

  /* ═══════════════════════════════════════════════════════════════════
     IDEA #2 — ONE-CLICK VARIANT
     Badge e card per la generazione rapida Fila B
  ═══════════════════════════════════════════════════════════════════ */

  .one-click-variant-card {{
    background: linear-gradient(135deg, {T['card2']} 0%, {T['card']} 100%);
    border: 2px solid {T['accent']};
    border-radius: 14px;
    padding: .95rem 1.1rem;
    margin-bottom: .8rem;
    display: flex;
    align-items: flex-start;
    gap: .85rem;
    position: relative;
    overflow: hidden;
  }}
  .one-click-variant-card::before {{
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, {T['accent']}, {T['accent']}66);
    border-radius: 14px 14px 0 0;
  }}
  .one-click-badge {{
    background: {T['accent']};
    color: #fff;
    font-size: .6rem;
    font-weight: 800;
    padding: 3px 9px;
    border-radius: 100px;
    letter-spacing: .06em;
    font-family: DM Sans, sans-serif;
    white-space: nowrap;
    flex-shrink: 0;
    margin-top: 2px;
  }}
  .one-click-body {{
    flex: 1;
  }}
  .one-click-title {{
    font-size: .88rem;
    font-weight: 800;
    color: {T['accent']};
    font-family: DM Sans, sans-serif;
    line-height: 1.2;
    margin-bottom: .2rem;
  }}
  .one-click-desc {{
    font-size: .74rem;
    color: {T['text2']};
    font-family: DM Sans, sans-serif;
    line-height: 1.5;
  }}

  /* ═══════════════════════════════════════════════════════════════════
     HOME CARD BUTTONS — selettori posizionali per colonna (Streamlit-compatible)
     Identificazione tramite presenza di .mcard-blu nella riga di 3 colonne
  ═══════════════════════════════════════════════════════════════════ */

  /* Colonna 1 (BLU) — Creazione guidata */
  div[data-testid="stHorizontalBlock"]:has(.mcard-blu) > div[data-testid="column"]:nth-child(1) button,
  .mbtn-blu button {{
    background: linear-gradient(135deg, #3B82F6, #2563EB) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: 700 !important;
    font-size: .88rem !important;
    box-shadow: 0 4px 16px #3B82F644 !important;
    transition: background .2s ease, box-shadow .2s ease !important;
  }}
  div[data-testid="stHorizontalBlock"]:has(.mcard-blu) > div[data-testid="column"]:nth-child(1) button:hover,
  .mbtn-blu button:hover {{
    background: linear-gradient(135deg, #60A5FA, #3B82F6) !important;
    box-shadow: 0 6px 24px #3B82F666 !important;
  }}

  /* Colonna 2 (VERDE) — Descrizione libera */
  div[data-testid="stHorizontalBlock"]:has(.mcard-blu) > div[data-testid="column"]:nth-child(2) button,
  .mbtn-verde button {{
    background: linear-gradient(135deg, #10B981, #059669) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: 700 !important;
    font-size: .88rem !important;
    box-shadow: 0 4px 16px #10B98144 !important;
    transition: background .2s ease, box-shadow .2s ease !important;
  }}
  div[data-testid="stHorizontalBlock"]:has(.mcard-blu) > div[data-testid="column"]:nth-child(2) button:hover,
  .mbtn-verde button:hover {{
    background: linear-gradient(135deg, #34D399, #10B981) !important;
    box-shadow: 0 6px 24px #10B98166 !important;
  }}

  /* Colonna 3 (ARANCIO) — Genera da file */
  div[data-testid="stHorizontalBlock"]:has(.mcard-blu) > div[data-testid="column"]:nth-child(3) button,
  .mbtn-arancio button {{
    background: linear-gradient(135deg, #F59E0B, #D97706) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: 700 !important;
    font-size: .88rem !important;
    box-shadow: 0 4px 16px #F59E0B44 !important;
    transition: background .2s ease, box-shadow .2s ease !important;
  }}
  div[data-testid="stHorizontalBlock"]:has(.mcard-blu) > div[data-testid="column"]:nth-child(3) button:hover,
  .mbtn-arancio button:hover {{
    background: linear-gradient(135deg, #FCD34D, #F59E0B) !important;
    box-shadow: 0 6px 24px #F59E0B66 !important;
  }}

  /* VIOLA — Facsimile istantaneo */
  .mbtn-viola button,
  .mbtn-viola button:focus,
  .mbtn-viola button:active {{
    background: linear-gradient(135deg, #7C3AED, #6D28D9) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: 700 !important;
    font-size: .9rem !important;
    box-shadow: 0 4px 18px #7C3AED44 !important;
    transition: background .18s ease, box-shadow .18s ease !important;
  }}
  .mbtn-viola button:hover {{
    background: linear-gradient(135deg, #A78BFA, #7C3AED) !important;
    box-shadow: 0 6px 28px #7C3AED66 !important;
  }}

  /* ═══════════════════════════════════════════════════════════════════
     IDEA #8 — TEMPLATE GALLERY
  ═══════════════════════════════════════════════════════════════════ */

  .template-gallery-header {{
    display: flex;
    align-items: center;
    gap: .65rem;
    margin-bottom: 1rem;
  }}
  .template-gallery-title {{
    font-size: .95rem;
    font-weight: 800;
    color: {T['text']};
    font-family: DM Sans, sans-serif;
  }}
  .template-gallery-sub {{
    font-size: .72rem;
    color: {T['muted']};
    font-family: DM Sans, sans-serif;
    margin-top: 1px;
  }}
  .template-card {{
    background: {T['card']};
    border: 1.5px solid {T['border']};
    border-radius: 12px;
    padding: .85rem 1rem;
    cursor: pointer;
    transition: border-color .15s ease, box-shadow .15s ease;
    height: 100%;
    display: flex;
    flex-direction: column;
    gap: .4rem;
  }}
  .template-card:hover {{
    border-color: {T['accent']};
    box-shadow: 0 4px 18px {T['accent']}22;
  }}
  .template-card.selected {{
    border-color: {T['accent']};
    background: linear-gradient(135deg, {T['accent_light']} 0%, {T['card']} 100%);
    box-shadow: 0 2px 12px {T['accent']}33;
  }}
  .template-icon {{
    font-size: 1.4rem;
    line-height: 1;
  }}
  .template-name {{
    font-size: .82rem;
    font-weight: 800;
    color: {T['text']};
    font-family: DM Sans, sans-serif;
    line-height: 1.2;
  }}
  .template-meta {{
    font-size: .68rem;
    color: {T['muted']};
    font-family: DM Sans, sans-serif;
    line-height: 1.4;
  }}
  .template-tags {{
    display: flex;
    flex-wrap: wrap;
    gap: .25rem;
    margin-top: .2rem;
  }}
  .template-tag {{
    font-size: .6rem;
    background: {T['card2']};
    border: 1px solid {T['border']};
    border-radius: 5px;
    padding: 1px 7px;
    color: {T['text2']};
    font-family: DM Sans, sans-serif;
  }}
  .template-selected-badge {{
    display: inline-flex;
    align-items: center;
    gap: .4rem;
    background: {T['accent']}18;
    border: 1.5px solid {T['accent']}55;
    border-radius: 8px;
    padding: .4rem .85rem;
    font-size: .78rem;
    font-weight: 700;
    color: {T['accent']};
    font-family: DM Sans, sans-serif;
    margin-bottom: .6rem;
    animation: fadeInUp .3s ease both;
  }}

  /* ═══════════════════════════════════════════════════════════════════
     IDEA #19 — RUBRICA DI VALUTAZIONE
  ═══════════════════════════════════════════════════════════════════ */

  .rubrica-wrap {{
    background: {T['card']};
    border: 1.5px solid {T['border']};
    border-left: 4px solid {T['success']};
    border-radius: 0 12px 12px 0;
    padding: 1rem 1.2rem;
    margin-top: .8rem;
    animation: fadeInUp .35s ease both;
  }}
  .rubrica-header {{
    display: flex;
    align-items: center;
    gap: .6rem;
    margin-bottom: .65rem;
  }}
  .rubrica-title {{
    font-size: .85rem;
    font-weight: 800;
    color: {T['success']};
    font-family: DM Sans, sans-serif;
  }}
  .rubrica-badge {{
    background: {T['success']}18;
    border: 1px solid {T['success']}55;
    border-radius: 100px;
    padding: 2px 9px;
    font-size: .62rem;
    font-weight: 700;
    color: {T['success']};
    font-family: DM Sans, sans-serif;
    letter-spacing: .04em;
  }}
  .rubrica-content {{
    font-size: .78rem;
    color: {T['text2']};
    font-family: DM Sans, sans-serif;
    line-height: 1.65;
  }}
  .rubrica-content h2, .rubrica-content h3 {{
    font-size: .82rem;
    font-weight: 700;
    color: {T['text']};
    margin: .7rem 0 .25rem;
  }}
  .rubrica-content strong {{
    color: {T['accent']};
    font-weight: 700;
  }}
  .rubrica-content ul, .rubrica-content ol {{
    margin: .2rem 0 .2rem 1.1rem;
    padding: 0;
  }}
  .rubrica-content li {{
    margin-bottom: .15rem;
  }}

  /* ═══════════════════════════════════════════════════════════════════
     IDEA #3 — SMART PREVIEW HINT
     Banner informativo nell'editor blocchi
  ═══════════════════════════════════════════════════════════════════ */

  .smart-preview-hint {{
    background: linear-gradient(135deg, {T['card2']} 0%, {T['card']} 100%);
    border: 1px solid {T['border']};
    border-left: 3px solid {T['accent']};
    border-radius: 0 10px 10px 0;
    padding: .55rem .9rem;
    margin-bottom: .7rem;
    display: flex;
    align-items: flex-start;
    gap: .5rem;
    font-size: .72rem;
    color: {T['text2']};
    font-family: DM Sans, sans-serif;
    line-height: 1.5;
  }}
  .smart-preview-hint strong {{
    color: {T['accent']};
  }}

  /* ═══════════════════════════════════════════════════════════════════
     FIX WORKFLOW — Login page gradient top bar + CTA hierarchy
  ═══════════════════════════════════════════════════════════════════ */

  /* Pulsante primario principale con ombra accent più pronunciata */
  div.stButton > button[kind="primary"] {{
    box-shadow: 0 4px 20px {T['accent']}55 !important;
    transition: box-shadow .2s ease, filter .15s ease !important;
  }}
  div.stButton > button[kind="primary"]:hover {{
    box-shadow: 0 6px 28px {T['accent']}77 !important;
    filter: brightness(1.08) !important;
  }}

</style>

  /* ╔══════════════════════════════════════════════════════════════════════
     ██  RESTYLING STRATEGICO — MODULO CREAZIONE VERIFICHE
     ██  Gerarchia visiva · Due Colonne · Tipografia ≥16px · Accenti
     ╚══════════════════════════════════════════════════════════════════════ */

  /* ════ TIPOGRAFIA PRINCIPALE — min 16px per docenti ════ */
  .stTextInput input,
  .stNumberInput input {{
    font-size: 1rem !important;
    min-height: 52px !important;
  }}
  .stTextArea textarea {{
    font-size: 1rem !important;
    line-height: 1.6 !important;
  }}
  .stSelectbox [data-baseweb="select"] span {{
    font-size: 1rem !important;
  }}
  .stCheckbox label,
  .stToggle label,
  .stToggle span,
  .stRadio [data-testid="stMarkdownContainer"] p {{
    font-size: 1rem !important;
  }}

  /* ════ ONBOARDING HINT BANNER — tutta la larghezza, in alto nel form ════ */
  .onboarding-hint-banner {{
    display: flex;
    align-items: flex-start;
    gap: 1rem;
    background: linear-gradient(135deg, {T['accent']}14 0%, {T['card2']} 60%, {T['card']} 100%);
    border: 1.5px solid {T['accent']}44;
    border-radius: 16px;
    padding: 1rem 1.3rem;
    margin-bottom: 1.4rem;
    position: relative;
    overflow: hidden;
  }}
  .onboarding-hint-banner::before {{
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, {T['accent']}, {T['accent2']});
    border-radius: 16px 16px 0 0;
  }}
  .onboarding-hint-icon {{
    font-size: 1.6rem;
    flex-shrink: 0;
    margin-top: 1px;
    line-height: 1;
  }}
  .onboarding-hint-body {{
    flex: 1;
    min-width: 0;
  }}
  .onboarding-hint-title {{
    font-size: 1rem;
    font-weight: 800;
    color: {T['text']};
    font-family: 'DM Sans', sans-serif;
    margin-bottom: .25rem;
    letter-spacing: -.01em;
  }}
  .onboarding-hint-desc {{
    font-size: .9rem;
    color: {T['text2']};
    font-family: 'DM Sans', sans-serif;
    line-height: 1.55;
  }}
  .onboarding-hint-desc strong {{ color: {T['accent']}; font-weight: 700; }}
  .onboarding-hint-tags {{
    display: flex;
    flex-wrap: wrap;
    gap: .3rem;
    margin-top: .5rem;
  }}
  .onboarding-hint-tag {{
    font-size: .72rem;
    font-weight: 700;
    background: {T['accent']}22;
    color: {T['accent']};
    border: 1px solid {T['accent']}44;
    border-radius: 100px;
    padding: 2px 10px;
    letter-spacing: .03em;
    font-family: 'DM Sans', sans-serif;
  }}

  /* ════ FORM SECTION HEADERS — intestazioni sezione con dot accent ════ */
  .form-section-header {{
    display: flex;
    align-items: center;
    gap: .7rem;
    margin: 1.6rem 0 .75rem 0;
    font-family: 'DM Sans', sans-serif;
  }}
  .form-section-dot {{
    width: 9px; height: 9px;
    border-radius: 50%;
    background: {T['accent']};
    box-shadow: 0 0 8px {T['accent']}77;
    flex-shrink: 0;
  }}
  .form-section-title {{
    font-size: .78rem;
    font-weight: 800;
    letter-spacing: .08em;
    text-transform: uppercase;
    color: {T['accent']};
    font-family: 'DM Sans', sans-serif;
    white-space: nowrap;
  }}
  .form-section-line {{
    flex: 1;
    height: 1.5px;
    background: linear-gradient(90deg, {T['accent']}55 0%, transparent 100%);
    border-radius: 2px;
  }}

  /* ════ CTA GENERA BOZZA — grande, alto contrasto, hint ════ */
  .cta-genera-wrap {{
    margin-top: 1.8rem;
    position: relative;
  }}
  .cta-genera-wrap > div.stButton > button[kind="primary"] {{
    min-height: 60px !important;
    font-size: 1.1rem !important;
    font-weight: 900 !important;
    letter-spacing: .02em !important;
    border-radius: 16px !important;
    box-shadow: 0 6px 28px {T['accent']}55 !important;
    background: linear-gradient(135deg, {T['accent']} 0%, {T['accent2']} 100%) !important;
    color: #fff !important;
    transition: transform .2s cubic-bezier(.175,.885,.32,1.275),
                box-shadow .2s ease,
                filter .2s ease !important;
  }}
  .cta-genera-wrap > div.stButton > button[kind="primary"]:hover {{
    transform: translateY(-3px) scale(1.02) !important;
    box-shadow: 0 10px 36px {T['accent']}77 !important;
    filter: brightness(1.07) !important;
  }}
  .cta-genera-wrap > div.stButton > button[kind="primary"]:active {{
    transform: translateY(0) scale(0.98) !important;
  }}
  .cta-genera-wrap > div.stButton > button[kind="primary"]:disabled {{
    background: {T['border2']} !important;
    box-shadow: none !important;
    transform: none !important;
    opacity: .55 !important;
    cursor: not-allowed !important;
  }}
  .cta-hint-below {{
    display: flex;
    align-items: center;
    gap: .4rem;
    justify-content: center;
    margin-top: .5rem;
    font-size: .78rem;
    color: {T['muted']};
    font-family: 'DM Sans', sans-serif;
  }}
  .cta-hint-below span {{ opacity: .6; }}

  /* ════ SIDE PANEL — colonna destra del form a due colonne ════ */
  .side-panel {{
    position: sticky;
    top: 1rem;
  }}
  .side-panel-card {{
    background: {T['card']};
    border: 1.5px solid {T['border']};
    border-radius: 14px;
    padding: 1rem 1rem .85rem;
    margin-bottom: 1rem;
    transition: border-color .15s ease, box-shadow .15s ease;
  }}
  .side-panel-card:hover {{
    border-color: {T['border2']};
  }}
  .side-panel-card-title {{
    font-size: .78rem;
    font-weight: 800;
    letter-spacing: .07em;
    text-transform: uppercase;
    color: {T['text2']};
    font-family: 'DM Sans', sans-serif;
    margin-bottom: .65rem;
    display: flex;
    align-items: center;
    gap: .45rem;
  }}
  .side-panel-card-title-dot {{
    width: 7px; height: 7px;
    border-radius: 50%;
    background: {T['accent']};
    flex-shrink: 0;
  }}

  /* ════ FACSIMILE SHORTCUT — box viola nella colonna destra ════ */
  .facsimile-shortcut {{
    background: linear-gradient(135deg, #7C3AED1A 0%, {T['card']} 100%);
    border: 2px solid #7C3AED88;
    border-radius: 14px;
    padding: .85rem 1rem;
    margin-bottom: 1rem;
    display: flex;
    flex-direction: column;
    gap: .5rem;
    transition: border-color .15s ease, box-shadow .15s ease;
  }}
  .facsimile-shortcut:hover {{
    border-color: #7C3AED;
    box-shadow: 0 6px 24px #7C3AED22;
  }}
  .facsimile-shortcut-badge {{
    display: inline-flex;
    align-items: center;
    gap: .25rem;
    background: #7C3AED;
    color: #fff;
    font-size: .58rem;
    font-weight: 800;
    padding: 2px 8px;
    border-radius: 100px;
    letter-spacing: .06em;
    font-family: 'DM Sans', sans-serif;
    width: fit-content;
  }}
  .facsimile-shortcut-question {{
    font-size: .85rem;
    font-weight: 800;
    color: #9F7AEA;
    font-family: 'DM Sans', sans-serif;
    line-height: 1.35;
  }}
  .facsimile-shortcut-desc {{
    font-size: .75rem;
    color: {T['text2']};
    font-family: 'DM Sans', sans-serif;
    line-height: 1.45;
  }}
  /* Pulsante viola facsimile shortcut */
  .facsimile-shortcut-btn > div.stButton > button,
  .facsimile-shortcut-btn .stButton > button {{
    background: #7C3AED !important;
    color: #fff !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    font-size: .85rem !important;
    min-height: 40px !important;
    padding: .5rem .9rem !important;
    box-shadow: 0 4px 16px #7C3AED44 !important;
    transition: all .18s ease !important;
    width: 100% !important;
  }}
  .facsimile-shortcut-btn > div.stButton > button:hover {{
    background: #9F5CFF !important;
    box-shadow: 0 6px 22px #7C3AED66 !important;
    transform: translateY(-1px) !important;
  }}

  /* ════ FILE ITEM COMPACT — card file nella colonna destra ════ */
  .file-item-b {{
    background: {T['card2']};
    border: 1.5px solid {T['border']};
    border-radius: 12px;
    padding: .75rem .9rem .65rem;
    margin-bottom: .6rem;
    transition: border-color .12s ease;
  }}
  .file-item-b:hover {{
    border-color: {T['accent']}66;
  }}
  .file-item-b-header {{
    display: flex;
    align-items: center;
    gap: .5rem;
    margin-bottom: .4rem;
  }}
  .file-item-b-icon {{
    font-size: 1rem;
    flex-shrink: 0;
    line-height: 1;
  }}
  .file-item-b-name {{
    font-size: .78rem;
    font-weight: 700;
    color: {T['text']};
    font-family: 'DM Sans', sans-serif;
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }}
  .file-item-b-badge {{
    font-size: .6rem;
    font-weight: 700;
    padding: 2px 7px;
    border-radius: 6px;
    letter-spacing: .04em;
    white-space: nowrap;
    flex-shrink: 0;
    font-family: 'DM Sans', sans-serif;
  }}
  .file-item-b-badge-verifica {{
    background: {T['success']}22;
    color: {T['success']};
    border: 1px solid {T['success']}44;
  }}
  .file-item-b-badge-appunti {{
    background: #C084FC22;
    color: #A855F7;
    border: 1px solid #C084FC44;
  }}
  .file-item-b-badge-altro {{
    background: {T['card']};
    color: {T['muted']};
    border: 1px solid {T['border2']};
  }}
  .file-item-b-mode-label {{
    font-size: .68rem;
    font-weight: 700;
    letter-spacing: .05em;
    text-transform: uppercase;
    color: {T['muted']};
    font-family: 'DM Sans', sans-serif;
    margin-bottom: 3px;
  }}
  /* Dropdown e textarea dentro file-item-b */
  .file-item-b .stSelectbox [data-baseweb="select"] > div:first-child {{
    background: {T['card']} !important;
    border: 1px solid {T['border']} !important;
    min-height: 38px !important;
    font-size: .82rem !important;
  }}
  .file-item-b .stSelectbox [data-baseweb="select"] span {{
    font-size: .82rem !important;
  }}
  .file-item-b .stTextArea textarea {{
    font-size: .82rem !important;
    min-height: 56px !important;
    background: {T['card']} !important;
    border-color: {T['border']} !important;
  }}
  /* Pulsante Rimuovi discreto */
  .file-item-b-delete > div.stButton > button,
  .file-item-b-delete .stButton > button {{
    background: transparent !important;
    color: {T['muted']} !important;
    border: 1px solid {T['border']} !important;
    border-radius: 7px !important;
    font-size: .7rem !important;
    font-weight: 600 !important;
    min-height: 28px !important;
    padding: 0 8px !important;
    box-shadow: none !important;
    transform: none !important;
    width: 100% !important;
    transition: color .12s ease, border-color .12s ease !important;
  }}
  .file-item-b-delete > div.stButton > button:hover,
  .file-item-b-delete .stButton > button:hover {{
    color: #EF4444 !important;
    border-color: #EF4444 !important;
    background: #EF444408 !important;
    box-shadow: none !important;
    transform: none !important;
  }}

  /* ════ UPLOAD HINT — colonna destra, hint OCR ════ */
  .upload-hint-compact {{
    background: linear-gradient(135deg, {T['accent']}12 0%, {T['card2']} 100%);
    border: 1px dashed {T['accent']}55;
    border-radius: 10px;
    padding: .65rem .9rem;
    margin-bottom: .75rem;
    font-size: .78rem;
    color: {T['text2']};
    font-family: 'DM Sans', sans-serif;
    line-height: 1.5;
  }}
  .upload-hint-compact strong {{ color: {T['accent']}; font-weight: 700; }}

  /* File uploader compact */
  .file-uploader-compact [data-testid="stFileUploader"] section {{
    padding: .5rem .75rem !important;
    min-height: unset !important;
  }}
  .file-uploader-compact [data-testid="stFileUploadDropzone"] {{
    min-height: unset !important;
  }}

  /* ════ CONTEXT SYNC BADGE — banner argomento auto-rilevato ════ */
  .context-sync-badge {{
    display: inline-flex;
    align-items: center;
    gap: .5rem;
    background: {T['success']}18;
    border: 1.5px solid {T['success']}44;
    border-radius: 8px;
    padding: .35rem .75rem;
    font-size: .72rem;
    font-weight: 700;
    color: {T['success']};
    font-family: 'DM Sans', sans-serif;
    margin-bottom: .4rem;
    animation: fadeInUp .3s ease both;
  }}

  /* ════ HOME LANDING — nuovo CTA unico ════ */
  .home-landing-wrap {{
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1.2rem;
    padding: 1.5rem 0 2rem;
    text-align: center;
  }}
  .home-landing-title {{
    font-size: 1.3rem;
    font-weight: 900;
    color: {T['text']};
    font-family: 'DM Sans', sans-serif;
    letter-spacing: -.02em;
  }}
  .home-landing-desc {{
    font-size: 1rem;
    color: {T['text2']};
    font-family: 'DM Sans', sans-serif;
    max-width: 560px;
    line-height: 1.6;
  }}
  /* Pulsante CTA home */
  .home-cta-btn > div.stButton > button[kind="primary"] {{
    min-height: 58px !important;
    font-size: 1.15rem !important;
    font-weight: 900 !important;
    border-radius: 18px !important;
    padding: .8rem 2.5rem !important;
    background: linear-gradient(135deg, {T['accent']} 0%, {T['accent2']} 100%) !important;
    box-shadow: 0 8px 32px {T['accent']}55 !important;
    letter-spacing: .02em !important;
    color: #fff !important;
    animation: pulseGlow 3s ease-in-out infinite !important;
  }}
  .home-cta-btn > div.stButton > button[kind="primary"]:hover {{
    transform: translateY(-3px) scale(1.03) !important;
    box-shadow: 0 12px 40px {T['accent']}77 !important;
    filter: brightness(1.1) !important;
    animation: none !important;
  }}

  /* ════ BIVIO MIGLIORATO — card più compatte e chiare ════ */
  .mcard {{
    background: {T['card']};
    border-radius: 16px;
    padding: 1.2rem 1.1rem 1rem;
    border: 2px solid {T['border']};
    height: 100%;
    display: flex;
    flex-direction: column;
    gap: .55rem;
    transition: border-color .18s ease, box-shadow .18s ease, transform .18s ease;
    position: relative;
    overflow: hidden;
  }}
  .mcard:hover {{
    transform: translateY(-4px);
    box-shadow: 0 12px 32px rgba(0,0,0,.15);
  }}
  .mcard-badge {{
    display: inline-flex;
    align-items: center;
    gap: .25rem;
    color: #fff;
    font-size: .6rem;
    font-weight: 800;
    padding: 2px 9px;
    border-radius: 100px;
    letter-spacing: .06em;
    font-family: 'DM Sans', sans-serif;
    width: fit-content;
    margin-bottom: .1rem;
  }}
  .mcard-icon {{
    font-size: 1.8rem;
    line-height: 1;
    flex-shrink: 0;
  }}
  .mcard-title {{
    font-size: 1.05rem;
    font-weight: 900;
    font-family: 'DM Sans', sans-serif;
    line-height: 1.2;
    letter-spacing: -.01em;
  }}
  .mcard-desc {{
    font-size: .88rem;
    color: {T['text2']};
    font-family: 'DM Sans', sans-serif;
    line-height: 1.55;
    flex: 1;
  }}
  .mcard-hint {{
    font-size: .75rem;
    color: {T['muted']};
    font-family: 'DM Sans', sans-serif;
    font-style: italic;
    border-top: 1px solid {T['border']};
    padding-top: .5rem;
    margin-top: auto;
  }}
  .mcard-chips {{
    display: flex;
    flex-wrap: wrap;
    gap: .25rem;
    margin-top: .1rem;
  }}
  .mcard-chip {{
    font-size: .68rem;
    background: {T['card2']};
    color: {T['text2']};
    border: 1px solid {T['border']};
    border-radius: 6px;
    padding: 2px 8px;
    font-family: 'DM Sans', sans-serif;
    font-weight: 600;
  }}
  /* Hover effect colori */
  .mcard-blu:hover   {{ border-color: #3B82F6 !important; box-shadow: 0 12px 32px #3B82F622 !important; }}
  .mcard-verde:hover {{ border-color: #10B981 !important; box-shadow: 0 12px 32px #10B98122 !important; }}
  .mcard-arancio:hover {{ border-color: #F59E0B !important; box-shadow: 0 12px 32px #F59E0B22 !important; }}

  /* ════ FACSIMILE DEDICATO PAGE — pagina rapida con solo upload ════ */
  .facsimile-page-wrap {{
    max-width: 580px;
    margin: 0 auto;
    text-align: center;
    padding: 1rem 0;
  }}
  .facsimile-page-icon {{
    font-size: 3rem;
    margin-bottom: .5rem;
    display: block;
  }}
  .facsimile-page-title {{
    font-size: 1.5rem;
    font-weight: 900;
    color: {T['text']};
    font-family: 'DM Sans', sans-serif;
    margin-bottom: .4rem;
    letter-spacing: -.02em;
  }}
  .facsimile-page-desc {{
    font-size: 1rem;
    color: {T['text2']};
    font-family: 'DM Sans', sans-serif;
    line-height: 1.6;
    margin-bottom: 1.5rem;
  }}
  /* Area upload centrale facsimile */
  .facsimile-page-uploader {{
    background: linear-gradient(135deg, #7C3AED14 0%, {T['card2']} 100%);
    border: 2.5px dashed #7C3AED88;
    border-radius: 18px;
    padding: 1.5rem 1.5rem 1rem;
    margin-bottom: 1rem;
    transition: border-color .15s ease;
  }}
  .facsimile-page-uploader:hover {{ border-color: #7C3AED; }}

  /* ════ PROGRESS BAR GENERAZIONE — improved ════ */
  .gen-progress-wrap {{
    background: {T['card']};
    border: 1.5px solid {T['border']};
    border-radius: 14px;
    padding: 1.2rem 1.4rem;
    margin: .8rem 0 1.2rem;
    animation: fadeInUp .3s ease both;
  }}
  .gen-progress-label {{
    font-size: .9rem;
    font-weight: 700;
    color: {T['text']};
    font-family: 'DM Sans', sans-serif;
    margin-bottom: .7rem;
    display: flex;
    align-items: center;
    gap: .5rem;
  }}
  .gen-progress-label-dot {{
    width: 8px; height: 8px;
    border-radius: 50%;
    background: {T['accent']};
    animation: pulseGlow 1.2s ease-in-out infinite;
    flex-shrink: 0;
  }}

  /* ════ ARGOMENTO FIELD ENHANCED — campo principale, visibilità ════ */
  .argomento-field-wrap .stTextArea textarea {{
    font-size: 1rem !important;
    min-height: 100px !important;
    border-left: 3px solid {T['accent']} !important;
    border-radius: 0 10px 10px 0 !important;
    padding-left: 14px !important;
    background: {T['card2']} !important;
  }}
  .argomento-field-wrap .stTextArea textarea:focus {{
    border-color: {T['accent']} !important;
    border-left-width: 4px !important;
    box-shadow: 0 0 0 3px {T['accent_light']} !important;
  }}

  /* ════ NOTA EXTRA — campo note con stile discreto ════ */
  .note-field-wrap .stTextArea textarea {{
    font-size: .9rem !important;
    font-style: italic;
    min-height: 72px !important;
    background: {T['card']} !important;
    border-style: dashed !important;
  }}

  /* ════ BACK BUTTON DISCRETE ════ */
  .btn-back-discrete > div.stButton > button,
  .btn-back-discrete .stButton > button {{
    background: transparent !important;
    color: {T['muted']} !important;
    border: 1px solid {T['border']} !important;
    border-radius: 9px !important;
    font-size: .8rem !important;
    font-weight: 500 !important;
    min-height: 34px !important;
    padding: 0 .85rem !important;
    box-shadow: none !important;
    transform: none !important;
    transition: color .12s ease, border-color .12s ease !important;
    width: 100% !important;
  }}
  .btn-back-discrete > div.stButton > button:hover,
  .btn-back-discrete .stButton > button:hover {{
    color: {T['text2']} !important;
    border-color: {T['border2']} !important;
    background: {T['hover']} !important;
    transform: none !important;
    box-shadow: none !important;
  }}

  /* ════ RESPONSIVE — due colonne form su tablet ════ */
  @media (max-width: 767px) {{
    .onboarding-hint-banner {{
      flex-direction: column;
      gap: .6rem;
    }}
    .facsimile-shortcut {{
      display: none;  /* Nasconde shortcut su mobile, accesso via percorso A */
    }}
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
