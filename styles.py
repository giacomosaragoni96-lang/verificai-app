def get_css(T: dict) -> str:
    _SB_BORDER = "#2a2926"
    _SB_MUTED  = "#8a8880"
    _SB_TEXT   = "#e8e6e0"
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
    max-width: 780px !important;
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

  /* ════ SIDEBAR ════ */
  [data-testid="stSidebar"] {{
    background: #141412 !important;
    border-right: 1px solid {_SB_BORDER} !important;
  }}
  .sidebar-title {{
    font-family: 'DM Sans', sans-serif;
    font-size: 1.1rem !important;
    font-weight: 800 !important;
    letter-spacing: -0.01em;
    color: #f5f3ed !important;
    margin: 0.5rem 0 1.2rem 0;
    padding-bottom: 0.6rem;
    border-bottom: 1px solid {_SB_BORDER};
  }}
  [data-testid="stSidebar"] .block-container {{
    padding: 1.5rem 1.2rem !important;
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
  [data-testid="stSidebar"] .stCheckbox [data-testid="stCheckbox"] span:first-child {{
    background-color: {T['input_bg']} !important;
    border: 1.5px solid {T['border2']} !important;
    border-radius: 5px !important;
  }}
  [data-testid="stSidebar"] .stTextInput input,
  [data-testid="stSidebar"] .stNumberInput input {{
    background: #232320 !important;
    border: 1.5px solid #3d3c36 !important;
    border-radius: 8px !important;
    color: #f5f3ed !important;
  }}
  [data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] > div:first-child {{
    background: #232320 !important;
    border: 1.5px solid #3d3c36 !important;
    border-radius: 8px !important;
  }}
  [data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] span {{
    color: #f5f3ed !important;
  }}
  [data-testid="stSidebar"] .stRadio label {{
    color: {_SB_TEXT} !important;
  }}
  [data-testid="stSidebar"] .stRadio [data-testid="stMarkdownContainer"] p {{
    color: {_SB_TEXT} !important;
  }}
  [data-testid="stSidebar"] .stButton button {{
    background: #232320 !important;
    color: #f5f3ed !important;
    border: 1.5px solid #3d3c36 !important;
    border-radius: 8px !important;
  }}
  [data-testid="stSidebar"] .stButton button:hover {{
    background: #2e2d28 !important;
    border-color: #5a5950 !important;
  }}
  [data-testid="stSidebar"] .stSelectSlider [data-testid="stMarkdownContainer"] p {{
    color: {_SB_TEXT} !important;
  }}
  [data-testid="stSidebar"] .section-label {{
    color: #5a5950 !important;
    border-bottom-color: {_SB_BORDER} !important;
  }}
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

  [data-testid="stSidebar"] .sidebar-label,
  .sidebar-label {{
    font-size: 0.72rem !important;
    font-weight: 800 !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    color: #D97706 !important;
    margin: 1rem 0 0.5rem 0 !important;
    padding-bottom: 0.35rem !important;
    border-bottom: 2px solid #3a3320 !important;
    display: block !important;
  }}

  [data-testid="stSidebar"] .logout-btn-wrap div.stButton > button,
  [data-testid="stSidebar"] .logout-btn-wrap .stButton button,
  [data-testid="stSidebar"] .logout-btn-wrap button {{
    background: transparent !important;
    color: #f87171 !important;
    border: 1px solid #5c2222 !important;
    border-radius: 8px !important;
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    padding: 6px 14px !important;
    width: auto !important;
    min-height: unset !important;
    box-shadow: none !important;
    transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease !important;
    letter-spacing: 0.02em !important;
  }}
  [data-testid="stSidebar"] .logout-btn-wrap div.stButton > button:hover,
  [data-testid="stSidebar"] .logout-btn-wrap .stButton button:hover,
  [data-testid="stSidebar"] .logout-btn-wrap button:hover {{
    background: #2a0f0f !important;
    border-color: #f87171 !important;
    color: #fca5a5 !important;
    box-shadow: 0 0 0 1px #5c2222 !important;
  }}

  h1, h2, h3 {{
    font-family: 'DM Sans', sans-serif !important;
    color: {T['text']} !important;
    letter-spacing: -0.02em;
  }}

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
    font-size: 96px !important;
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
    background: linear-gradient(135deg, {T['accent']} 0%, #FF8C00 100%);
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

  div.stButton > button[kind="primary"] {{
    background: #D97706 !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    transition: transform 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275), box-shadow 0.2s ease, filter 0.2s ease !important;
    box-shadow: 0 2px 12px rgba(217,119,6,0.35) !important;
    display: block !important;
  }}
  div.stButton > button[kind="primary"]:hover {{
    transform: scale(1.05) !important;
    box-shadow: 0 10px 25px rgba(217,119,6,0.5) !important;
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

  .dl-card {{
    background: #FFFFFF !important;
    padding: 1.2rem;
    border-radius: 15px;
    border: 1px solid #E0E0E0;
    text-align: center;
    margin-bottom: 1rem;
  }}
  .dl-label {{
    font-size: 0.85rem;
    color: #666;
    margin-bottom: 0.8rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }}
  .hint-docx {{
    font-size: 0.78rem;
    color: #888;
    line-height: 1.3;
    margin-top: 12px;
    font-style: italic;
    text-align: left;
    border-top: 1px solid #EEE;
    padding-top: 8px;
  }}

  .output-card {{
    background: {T['card']} !important;
    border: 1.5px solid {T['border2']} !important;
    border-radius: 16px !important;
    padding: 0 !important;
    margin-bottom: 1.5rem !important;
    overflow: hidden !important;
    box-shadow: {T['shadow_md']} !important;
  }}
  .output-card > div {{
    padding: 1.2rem !important;
  }}
  .stDownloadButton button,
  [data-testid="stDownloadButton"] button,
  .stButton [data-testid="baseButton-secondary"],
  .stButton button[kind="secondary"],
  button[data-testid="baseButton-secondary"] {{
    background: {T['card']} !important;
    color: {T['text']} !important;
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
    transform: translateY(-3px) !important;
    box-shadow: 0 6px 20px rgba(217,119,6,0.18) !important;
    color: {T['text']} !important;
  }}

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
  .tex-download {{
    opacity: 0.7 !important;
    transition: opacity 0.2s ease, transform 0.2s ease !important;
  }}
  .tex-download:hover {{
    opacity: 1 !important;
    transform: translateX(3px) !important;
  }}
  .hint-docx {{
    background: {T['accent_light']} !important;
    border-left: 3px solid {T['accent']} !important;
    border-radius: 8px !important;
    padding: 10px 14px !important;
    margin-top: 8px !important;
    font-size: 0.8rem !important;
    color: {T['text2']} !important;
    line-height: 1.5 !important;
  }}
  .hint-docx strong {{
    color: {T['accent']} !important;
  }}
  .section-action-label {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-size: 0.7rem;
    font-weight: 800;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: {T['muted']};
    margin-bottom: 0.8rem;
    padding-bottom: 0.5rem;
    border-bottom: 2px solid {T['border']};
  }}
  .section-action-label::before {{
    content: '';
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: {T['accent']};
    display: inline-block;
  }}

  .compact-uploader [data-testid="stFileUploader"] section {{
    padding: 0 !important;
    border: none !important;
    background: transparent !important;
    min-height: unset !important;
  }}
  .compact-uploader [data-testid="stFileUploadDropzone"] {{
    display: none !important;
  }}
  .compact-uploader [data-testid="stFileUploader"] button {{
    background: {T['card2']} !important;
    color: {T['text2']} !important;
    border: 1px solid {T['border2']} !important;
    border-radius: 8px !important;
    font-size: 0.8rem !important;
    padding: 6px 14px !important;
  }}
  .compact-uploader [data-testid="stFileUploader"] button:hover {{
    border-color: {T['accent']} !important;
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
    border-color: #5a5950 !important;
    background: {T['card2']} !important;
    box-shadow: none !important;
    transform: translateY(-1px) !important;
  }}

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

  .ai-hint {{
    display: flex;
    align-items: center;
    gap: 9px;
    background: {T['accent_light']};
    border: 1px solid {T['accent']}55;
    border-radius: 10px;
    padding: 9px 14px;
    font-size: 0.78rem;
    color: {T['text2']};
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

  .genera-section {{
    margin-top: 2.2rem;
    margin-bottom: 0.5rem;
  }}

  /* Etichetta opzione uniforme dentro Personalizza */
  .opt-label {{
    font-size: 0.72rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.06em !important;
    text-transform: uppercase !important;
    color: {T['text2']} !important;
    margin: 0.9rem 0 0.35rem 0 !important;
    display: block !important;
    font-family: 'DM Sans', sans-serif !important;
  }}

  /* Pulsante secondario con stile accent — usato per Riconfigura e Rivedi */
  .btn-secondary-accent div.stButton > button,
  .btn-secondary-accent .stButton > button {{
    background: transparent !important;
    color: {T['accent']} !important;
    border: 2px solid {T['accent']} !important;
    border-radius: 12px !important;
    font-weight: 700 !important;
    font-size: 1rem !important;
    padding: 0.6rem 1rem !important;
    min-height: 46px !important;
    height: 46px !important;
    box-shadow: 0 2px 8px {T['accent']}22 !important;
    transition: background 0.18s ease, box-shadow 0.18s ease, transform 0.18s ease !important;
  }}
  .btn-secondary-accent div.stButton > button:hover,
  .btn-secondary-accent .stButton > button:hover {{
    background: {T['accent_light']} !important;
    box-shadow: 0 4px 16px {T['accent']}40 !important;
    transform: translateY(-1px) !important;
  }}

  /* Forza primary button alla stessa altezza */
  .btn-equal-primary div.stButton > button[kind="primary"],
  .btn-equal-primary .stButton > button[kind="primary"],
  div.stButton > button[kind="primary"] {{
    min-height: 46px !important;
    height: 46px !important;
    padding: 0.6rem 1rem !important;
    font-size: 1rem !important;
  }}

  /* Pulsante download principale Fila A — verde brillante, più grande */
  .dl-primary-btn .stDownloadButton button,
  .dl-primary-btn [data-testid="stDownloadButton"] button {{
    background: linear-gradient(135deg, #16a34a 0%, #15803d 100%) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 12px !important;
    font-size: 1.05rem !important;
    font-weight: 800 !important;
    padding: 1rem 1.4rem !important;
    min-height: 54px !important;
    box-shadow: 0 4px 18px rgba(22,163,74,0.45) !important;
    letter-spacing: 0.01em !important;
    transition: all 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275) !important;
    width: 100% !important;
  }}
  .dl-primary-btn .stDownloadButton button:hover,
  .dl-primary-btn [data-testid="stDownloadButton"] button:hover {{
    transform: scale(1.03) translateY(-2px) !important;
    box-shadow: 0 8px 28px rgba(22,163,74,0.55) !important;
    filter: brightness(1.08) !important;
  }}

  /* Floater fase: desktop = top-right, mobile = bottom-right */
  .stage-floater {{
    position: fixed;
    top: 4.5rem;
    right: 1.2rem;
    z-index: 9999;
    background: {T['card']};
    border: 1.5px solid {T['border']};
    border-radius: 14px;
    padding: .7rem 1.1rem .65rem 1.1rem;
    box-shadow: 0 4px 24px rgba(0,0,0,.35);
    min-width: 155px;
    backdrop-filter: blur(8px);
  }}
  @media (max-width: 640px) {{
    .stage-floater {{
      top: auto;
      bottom: 4.5rem;
      right: .8rem;
    }}
  }}

  /* "Ho capito" button — stile link discreto */
  ._ob_dismiss_wrap div.stButton > button,
  ._ob_dismiss_wrap .stButton > button {{
    background: transparent !important;
    color: {T['muted']} !important;
    border: 1px solid {T['border']} !important;
    border-radius: 8px !important;
    font-size: 0.72rem !important;
    font-weight: 600 !important;
    padding: 4px 12px !important;
    min-height: 28px !important;
    height: 28px !important;
    box-shadow: none !important;
    width: auto !important;
  }}
  ._ob_dismiss_wrap div.stButton > button:hover {{
    color: {T['text2']} !important;
    border-color: {T['accent']} !important;
    background: {T['accent_light']} !important;
  }}

  .genera-hint {{
    text-align: center;
    font-size: 0.73rem;
    color: {T['muted']};
    margin-top: 0.6rem;
    font-family: 'DM Sans', sans-serif;
    letter-spacing: 0.02em;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 5px;
  }}

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
  .stSlider label p {{
    color: {T['text2']} !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.01em;
    text-transform: uppercase;
  }}
  .stSlider [data-baseweb="slider"] [data-testid="stSliderThumbValue"] {{
    color: {T['text']} !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
  }}

  .stAlert {{
    border-radius: 10px !important;
    border: none !important;
  }}
  .stAlert p,
  .stAlert span,
  .stAlert div,
  [data-testid="stAlert"] p,
  [data-testid="stAlert"] span,
  [data-testid="stAlert"] div {{
      color: #1a1915 !important;
      opacity: 1 !important;
  }}

  .stProgress > div > div {{
    background: {T['accent']} !important;
    border-radius: 100px !important;
  }}
  .stProgress > div {{
    background: {T['border']} !important;
    border-radius: 100px !important;
    height: 6px !important;
  }}

  .stSubheader {{
    font-family: 'DM Sans', sans-serif !important;
    font-size: 1.15rem !important;
    font-weight: 700 !important;
    color: {T['text']} !important;
  }}

  .status-bar {{
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 14px;
    background: {T['card2']};
    border: 1px solid {T['border']};
    border-radius: 8px;
    font-size: 0.78rem;
    color: {T['muted']};
    margin-top: 0.5rem;
    font-family: 'DM Sans', sans-serif;
  }}
  .status-bar .dot {{
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: {T['success']};
    flex-shrink: 0;
  }}
  .status-bar strong {{
    color: {T['text2']};
    font-weight: 600;
  }}

  .pdf-preview-wrap {{
    margin-top: 1rem;
    border: 1px solid {T['border']};
    border-radius: 14px;
    overflow: hidden;
    box-shadow: {T['shadow_md']};
    background: {T['card2']};
  }}

  .top-bar {{
    display: flex;
    align-items: center;
    justify-content: flex-start;
    gap: 0.75rem;
    margin-bottom: 1.2rem;
  }}
  .top-bar-hint {{
    display: none;
  }}
  @media (max-width: 640px) {{
    .top-bar-hint {{
      display: inline-flex;
      align-items: center;
      gap: 5px;
      background: {T['accent_light']};
      border: 1px solid {T['accent']};
      border-radius: 20px;
      padding: 5px 12px;
      font-size: 0.72rem;
      color: {T['accent']};
      font-weight: 600;
      white-space: nowrap;
    }}
  }}

  .fab-link {{
    position: fixed;
    bottom: 1.5rem;
    right: 1.5rem;
    top: auto !important;
    z-index: 9999;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: {T['accent']};
    color: #ffffff !important;
    text-decoration: none !important;
    border-radius: 50px;
    padding: 8px 14px;
    font-family: 'DM Sans', sans-serif;
    font-size: 0.78rem;
    font-weight: 700;
    box-shadow: 0 4px 18px rgba(217,119,6,0.40);
    transition: transform 0.15s ease, filter 0.15s ease, box-shadow 0.15s ease;
    white-space: nowrap;
    max-height: 40px;
  }}
  .fab-link:hover {{
    transform: translateY(-2px);
    filter: brightness(1.1);
    box-shadow: 0 6px 22px rgba(217,119,6,0.55);
    color: #ffffff !important;
  }}
  @media (max-width: 640px) {{
    .fab-link {{
      bottom: 4.5rem;
      right: 0.8rem;
      padding: 7px 12px;
      font-size: 0.73rem;
    }}
  }}

  .disclaimer {{
    display: flex;
    align-items: flex-start;
    gap: 8px;
    padding: 8px 12px;
    background: {T['card2']};
    border: 1px solid {T['border']};
    border-left: 3px solid {T['muted']};
    border-radius: 8px;
    font-size: 0.74rem;
    color: {T['muted']};
    font-family: 'DM Sans', sans-serif;
    line-height: 1.45;
    margin-bottom: 1rem;
  }}
  .disclaimer-icon {{ flex-shrink: 0; font-size: 0.9rem; margin-top: 1px; }}

  .app-footer {{
    text-align: center;
    font-size: 0.72rem;
    color: {T['muted']};
    font-family: 'DM Sans', sans-serif;
    margin-top: 3rem;
    padding-top: 1.2rem;
    border-top: 1px solid {T['border']};
    line-height: 1.6;
  }}

  .user-pill {{
    display: flex;
    align-items: center;
    gap: 10px;
    background: #1e1d1b;
    border: 1px solid #2e2d28;
    border-radius: 12px;
    padding: 10px 14px;
    margin-top: 0.5rem;
  }}
  .user-avatar {{
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: linear-gradient(135deg, #D97706, #FF8C00);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.85rem;
    font-weight: 800;
    color: white;
    flex-shrink: 0;
    font-family: 'DM Sans', sans-serif;
  }}
  .user-info {{
    flex: 1;
    min-width: 0;
  }}
  .user-email {{
    font-size: 0.78rem;
    font-weight: 600;
    color: #e8e6e0 !important;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    font-family: 'DM Sans', sans-serif;
  }}
  .user-role {{
    font-size: 0.65rem;
    color: #6b6960 !important;
    font-family: 'DM Sans', sans-serif;
    margin-top: 1px;
  }}

  .monthly-bar {{
    background: #1e1d1b;
    border: 1px solid #2e2d28;
    border-radius: 10px;
    padding: 10px 14px;
    margin-bottom: 0.5rem;
    font-family: 'DM Sans', sans-serif;
  }}
  .monthly-bar-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 6px;
  }}
  .monthly-bar-label {{
    font-size: 0.72rem;
    font-weight: 700;
    color: #8a8880 !important;
    text-transform: uppercase;
    letter-spacing: 0.07em;
  }}
  .monthly-bar-count {{
    font-size: 0.78rem;
    font-weight: 800;
    color: #e8e6e0 !important;
  }}
  .monthly-bar-count.limit-near {{ color: #F59E0B !important; }}
  .monthly-bar-count.limit-reached {{ color: #EF4444 !important; }}
  .monthly-progress {{
    height: 5px;
    background: #2e2d28;
    border-radius: 100px;
    overflow: hidden;
  }}
  .monthly-progress-fill {{
    height: 100%;
    border-radius: 100px;
    transition: width 0.4s ease;
  }}

  @media (max-width: 640px) {{
    .block-container {{
      padding: 4.5rem 1rem 3rem !important;
    }}
    .hero-title {{ font-size: 56px !important; }}
    .hero-sub {{ font-size: 0.95rem !important; }}
    .hero-wrap {{ margin-bottom: 1.5rem; padding-bottom: 1.2rem; }}
    .top-bar {{
      justify-content: center;
      gap: 0.5rem;
    }}
    .stTextInput input,
    .stNumberInput input {{
      font-size: 1rem !important;
      padding: 14px 16px !important;
      min-height: 52px !important;
      height: 52px !important;
      line-height: 1.4 !important;
      box-sizing: border-box !important;
    }}
    .stTextInput > div > div {{
      min-height: 52px !important;
    }}
    .stTextInput input::placeholder,
    .stNumberInput input::placeholder {{
      font-size: 1rem !important;
      opacity: 1 !important;
    }}
    .stSelectbox [data-baseweb="select"] > div:first-child {{
      padding: 12px 14px !important;
      min-height: 50px !important;
      height: auto !important;
    }}
    .stSelectbox [data-baseweb="select"] span,
    .stSelectbox [data-baseweb="select"] div {{
      font-size: 0.95rem !important;
      white-space: nowrap !important;
      overflow: hidden !important;
      text-overflow: ellipsis !important;
    }}
    [data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] > div:first-child {{
      min-height: 48px !important;
      padding: 10px 12px !important;
    }}
    [data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] span {{
      font-size: 0.85rem !important;
      color: #f5f3ed !important;
    }}
    .stTextArea textarea {{
      font-size: 0.95rem !important;
    }}
    .stButton button {{
      min-height: 48px !important;
      font-size: 1rem !important;
    }}
    [data-testid="stSidebar"] .block-container {{
      padding: 1rem !important;
    }}
    .stDownloadButton button {{
      width: 100% !important;
      min-height: 48px !important;
    }}
  }}

  @media (min-width: 641px) and (max-width: 1024px) {{
    .block-container {{
      padding: 1.5rem 1.5rem 3rem !important;
      max-width: 900px !important;
    }}
  }}

  [data-testid="stSidebar"] .stButton > button,
  [data-testid="stSidebar"] .stButton > button[kind="secondary"],
  [data-testid="stSidebar"] button[data-testid="baseButton-secondary"],
  [data-testid="stSidebar"] .stDownloadButton button,
  [data-testid="stSidebar"] [data-testid="stDownloadButton"] button {{
    background: #1e1d1b !important;
    color: #e8e6e0 !important;
    border: 1.5px solid #3d3c36 !important;
    border-radius: 8px !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    box-shadow: none !important;
    transform: none !important;
    padding: 8px 14px !important;
    min-height: 36px !important;
    width: 100% !important;
  }}
  [data-testid="stSidebar"] .stButton > button:hover,
  [data-testid="stSidebar"] .stButton > button[kind="secondary"]:hover,
  [data-testid="stSidebar"] button[data-testid="baseButton-secondary"]:hover,
  [data-testid="stSidebar"] .stDownloadButton button:hover,
  [data-testid="stSidebar"] [data-testid="stDownloadButton"] button:hover {{
    background: #2a2926 !important;
    border-color: #D97706 !important;
    color: #f5f3ed !important;
    transform: none !important;
    box-shadow: none !important;
  }}

  [data-testid="stSidebar"] [data-testid="stExpander"] {{
    background: #1e1d1b !important;
    border: 1px solid #2e2d28 !important;
    border-radius: 10px !important;
  }}
  [data-testid="stSidebar"] [data-testid="stExpander"] summary {{
    background: #1e1d1b !important;
    color: #c8c6bc !important;
    font-size: 0.82rem !important;
    padding: 0.7rem 1rem !important;
  }}
  [data-testid="stSidebar"] [data-testid="stExpander"] summary:hover {{
    background: #2a2926 !important;
    color: #f5f3ed !important;
  }}
  [data-testid="stSidebar"] [data-testid="stExpander"] > div > div {{
    background: #1e1d1b !important;
    padding: 0.4rem 1rem 0.8rem !important;
  }}
  [data-testid="stSidebar"] [data-testid="stExpander"] p,
  [data-testid="stSidebar"] [data-testid="stExpander"] span {{
    color: #c8c6bc !important;
  }}

  [data-testid="stSidebar"] [data-testid="stExpander"] .stButton > button,
  [data-testid="stSidebar"] [data-testid="stExpander"] div.stButton > button,
  [data-testid="stSidebar"] [data-testid="stExpander"] button[kind="secondary"],
  [data-testid="stSidebar"] [data-testid="stExpander"] button {{
    background: #2a2926 !important;
    background-color: #2a2926 !important;
    color: #c8c6bc !important;
    border: 1px solid #3a3834 !important;
    border-radius: 8px !important;
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    padding: 5px 12px !important;
    min-height: unset !important;
    box-shadow: none !important;
    transition: background 0.15s, border-color 0.15s, color 0.15s !important;
    width: 100% !important;
  }}
  [data-testid="stSidebar"] [data-testid="stExpander"] .stButton > button:hover,
  [data-testid="stSidebar"] [data-testid="stExpander"] div.stButton > button:hover {{
    background: #353330 !important;
    background-color: #353330 !important;
    border-color: {T['accent']} !important;
    color: {T['accent']} !important;
    box-shadow: none !important;
    transform: none !important;
  }}
  [data-testid="stSidebar"] [data-testid="stExpander"] .elimina-btn .stButton > button,
  [data-testid="stSidebar"] [data-testid="stExpander"] .elimina-btn button {{
    background: #1e1008 !important;
    background-color: #1e1008 !important;
    border-color: #5c2222 !important;
    color: #f87171 !important;
  }}
  [data-testid="stSidebar"] [data-testid="stExpander"] .elimina-btn .stButton > button:hover,
  [data-testid="stSidebar"] [data-testid="stExpander"] .elimina-btn button:hover {{
    background: #2a0f0f !important;
    background-color: #2a0f0f !important;
    border-color: #f87171 !important;
    color: #fca5a5 !important;
  }}
  [data-testid="stSidebar"] [data-testid="stExpander"] .stella-btn .stButton > button,
  [data-testid="stSidebar"] [data-testid="stExpander"] .stella-btn button {{
    background: #1e1d1b !important;
    background-color: #1e1d1b !important;
    border-color: #4a4020 !important;
    color: #9a8a50 !important;
    font-size: 1rem !important;
    padding: 3px 8px !important;
    width: auto !important;
  }}
  [data-testid="stSidebar"] [data-testid="stExpander"] .stella-btn-on .stButton > button,
  [data-testid="stSidebar"] [data-testid="stExpander"] .stella-btn-on button {{
    background: #2a2010 !important;
    background-color: #2a2010 !important;
    border-color: {T['accent']} !important;
    color: #F59E0B !important;
    width: auto !important;
  }}

  [data-testid="stSidebar"] .logout-btn-wrap .stButton > button,
  [data-testid="stSidebar"] .logout-btn-wrap button {{
    background: transparent !important;
    color: #f87171 !important;
    border: 1px solid #5c2222 !important;
    border-radius: 8px !important;
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    padding: 6px 14px !important;
    width: auto !important;
    min-height: unset !important;
    box-shadow: none !important;
  }}
  [data-testid="stSidebar"] .logout-btn-wrap .stButton > button:hover,
  [data-testid="stSidebar"] .logout-btn-wrap button:hover {{
    background: #2a0f0f !important;
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
</style>

"""
