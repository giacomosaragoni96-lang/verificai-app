import streamlit as st
import base64
import re
import os
import time
import google.generativeai as genai

from sidebar import render_sidebar
from generation import genera_verifica
from prompts import (
    prompt_titolo, prompt_corpo_verifica, prompt_controllo_qualita,
    prompt_versione_b, prompt_versione_ridotta, prompt_soluzioni,
    prompt_modifica,
)
from docx_export import latex_to_docx_via_ai
from latex_utils import (
    compila_pdf, inietta_griglia, riscala_punti,
    fix_items_environment, rimuovi_vspace_corpo, pulisci_corpo_latex,
    rimuovi_punti_subsection, parse_esercizi, build_griglia_latex,
    pdf_to_images_bytes,
)
from config import (
    APP_NAME, APP_ICON, APP_TAGLINE, SHARE_URL, FEEDBACK_FORM_URL,
    LIMITE_MENSILE, ADMIN_EMAILS, MODELLI_DISPONIBILI, THEMES,
    SCUOLE, CALIBRAZIONE_SCUOLA, MATERIE, NOTE_PLACEHOLDER, TIPI_ESERCIZIO,
)
from dotenv import load_dotenv
from supabase import create_client, Client
from auth import mostra_auth, ripristina_sessione, salva_sessione_cookie, cancella_sessione_cookie, get_cookie_controller
from styles import get_css


# ── PAGE CONFIG — DEVE ESSERE IL PRIMO COMANDO STREAMLIT ────────────────────────
st.set_page_config(
    page_title=APP_NAME,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── SUPABASE ──────────────────────────────────────────────────────────────────────
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
SUPABASE_SERVICE_KEY = st.secrets["SUPABASE_SERVICE_KEY"]
supabase_admin: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# ── TEMA ──────────────────────────────────────────────────────────────────────────
if "theme" not in st.session_state:
    st.session_state.theme = "light"
T = THEMES[st.session_state.theme]

# ── CONFIGURAZIONE ────────────────────────────────────────────────────────────────
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    st.error("⚠️ Chiave API mancante! Crea un file .env con: GOOGLE_API_KEY=la_tua_chiave")
    st.stop()
genai.configure(api_key=API_KEY)

# ── AUTENTICAZIONE GATE ───────────────────────────────────────────────────────────
if 'utente' not in st.session_state:
    st.session_state.utente = None

ripristina_sessione(supabase)

if st.session_state.utente is None:
    mostra_auth(supabase)
    st.stop()

# ── FINE GATE ─────────────────────────────────────────────────────────────────────


# ── FUNZIONI UTILITY ──────────────────────────────────────────────────────────────

def _get_verifiche_mese(user_id):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    primo_mese = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
    try:
        res = supabase_admin.table("verifiche_storico") \
            .select("id", count="exact") \
            .eq("user_id", user_id) \
            .gte("created_at", primo_mese) \
            .execute()
        return res.count or 0
    except Exception:
        return 0

def _giorni_al_reset():
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    if now.month == 12:
        reset = now.replace(year=now.year+1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        reset = now.replace(month=now.month+1, day=1, hour=0, minute=0, second=0, microsecond=0)
    delta = reset - now
    giorni = delta.days
    ore    = delta.seconds // 3600
    return giorni, ore

def modifica_verifica_con_ai(latex_originale, richiesta_modifica, model):
    response = model.generate_content(prompt_modifica(latex_originale, richiesta_modifica))
    latex_modificato = response.text.replace("```latex", "").replace("```", "").strip()
    if "\\end{document}" not in latex_modificato:
        latex_modificato += "\n\\end{document}"
    return latex_modificato

def costruisci_prompt_esercizi(esercizi_custom, num_totale, punti_totali, mostra_punteggi):
    n_liberi = max(0, num_totale - len(esercizi_custom))
    righe = [
        f"\nSTRUTTURA ESERCIZI — REGOLA ASSOLUTA:",
        f"Devi generare ESATTAMENTE {num_totale} esercizi, né uno di più né uno di meno.",
        f"Ogni esercizio è un blocco \\subsection*{{Esercizio N: Titolo}}.",
        f"Conta i tuoi \\subsection* prima di terminare: devono essere ESATTAMENTE {num_totale}.",
    ]
    immagini = []

    if mostra_punteggi and num_totale > 0:
        pts_base = punti_totali // num_totale
        resto = punti_totali - pts_base * num_totale
        pts_per_ex = [pts_base] * num_totale
        if resto > 0:
            pts_per_ex[0] += resto
        righe.append(f"\nDISTRIBUZIONE PUNTI SUGGERITA (totale ESATTO: {punti_totali} pt):")
        for i_ex in range(num_totale):
            righe.append(f"  - Esercizio {i_ex+1}: circa {pts_per_ex[i_ex]} pt (distribuisci tra i sottopunti)")
        righe.append(f"REGOLA CRITICA: la somma di TUTTI i (X pt) nei sottopunti DEVE essere ESATTAMENTE {punti_totali} pt.")

    ha_primo_custom = len(esercizi_custom) > 0
    if not ha_primo_custom:
        righe.append(
            f"\nREGOLA PRIMO ESERCIZIO (Esercizio 1 — SEMPRE presente, NON modificabile):\n"
            f"Il primo esercizio DEVE chiamarsi 'Saperi Essenziali' e coprire i concetti fondamentali\n"
            f"dell'argomento che TUTTI gli studenti devono conoscere. NON inserire mai il simbolo (*) qui."
        )

    righe.append(f"\nDETTAGLIO ESERCIZI ({num_totale} totali):")
    for i, ex in enumerate(esercizi_custom, 1):
        tipo, desc = ex.get('tipo', 'Aperto'), ex.get('descrizione', '').strip()
        riga = f"- Esercizio {i} [{tipo}]" + (f": {desc}" if desc else "")
        if ex.get('immagine'):
            riga += f" — vedi immagine allegata per l'esercizio {i}"
            immagini.append({'idx': i, 'data': ex['immagine'].getvalue(),
                             'mime_type': ex['immagine'].type})
        if tipo == "Scelta multipla":
            riga += " — opzioni con \\begin{enumerate}[a)] \\item prima \\item seconda \\end{enumerate}"
        elif tipo == "Vero/Falso":
            riga += " — $\\square$ \\textbf{V} $\\quad\\square$ \\textbf{F} \\quad testo (min 3)"
        elif tipo == "Completamento":
            riga += " — \\underline{\\hspace{3cm}} per gli spazi"
        righe.append(riga)
    if n_liberi > 0:
        start_idx = len(esercizi_custom) + 1
        end_idx   = num_totale
        righe.append(f"- Esercizi {start_idx}–{end_idx}: genera tu {n_liberi} esercizi coerenti.")
    return "\n".join(righe), immagini

def _stima_dimensione(data: bytes) -> str:
    kb = len(data) / 1024
    return f"{kb:.0f} KB" if kb < 1024 else f"{kb/1024:.1f} MB"


# ── SESSION STATE ─────────────────────────────────────────────────────────────────
def _vf():
    return {'latex': '', 'pdf': None, 'preview': False,
            'soluzioni_latex': '', 'soluzioni_pdf': None, 'docx': None,
            'pdf_ts': None, 'docx_ts': None, 'latex_originale': ''}

if 'verifiche' not in st.session_state:
    st.session_state.verifiche = {'A': _vf(), 'B': _vf(), 'R': _vf(), 'RB': _vf(), 'S': {'latex': None, 'testo': None, 'pdf': None}}
if 'esercizi_custom' not in st.session_state: st.session_state.esercizi_custom = []
if 'last_materia'    not in st.session_state: st.session_state.last_materia = None
if 'last_argomento'  not in st.session_state: st.session_state.last_argomento = None
if 'last_gen_ts'     not in st.session_state: st.session_state.last_gen_ts = None
if '_storico_refresh' not in st.session_state: st.session_state._storico_refresh = 0
if '_preferiti' not in st.session_state: st.session_state._preferiti = set()
if '_storico_page' not in st.session_state: st.session_state._storico_page = 1
if '_onboarding_done' not in st.session_state: st.session_state._onboarding_done = False

# ── DATI UTENTE E LIMITI ──────────────────────────────────────────────────────────
_verifiche_mese_count = _get_verifiche_mese(st.session_state.utente.id) if st.session_state.utente else 0
_is_admin = (st.session_state.utente.email in ADMIN_EMAILS) if st.session_state.utente else False
_limite_raggiunto = (not _is_admin) and (_verifiche_mese_count >= LIMITE_MENSILE)

# ── CSS GLOBALE ──────────────────────────────────────────────────────────────────
st.markdown(get_css(T), unsafe_allow_html=True)

# ── SIDEBAR ────────────────────────────────────────────────────────────────────────
try:
    settings = render_sidebar(
        supabase_admin=supabase_admin,
        utente=st.session_state.utente,
        verifiche_mese_count=_verifiche_mese_count,
        is_admin=_is_admin,
        limite_raggiunto=_limite_raggiunto,
        T=T,
        SCUOLE=SCUOLE,
        MODELLI_DISPONIBILI=MODELLI_DISPONIBILI,
        LIMITE_MENSILE=LIMITE_MENSILE,
        giorni_al_reset_func=_giorni_al_reset,
        compila_pdf_func=compila_pdf,
        supabase_client=supabase
    )
    # Dalla sidebar: solo il modello AI
    modello_id = settings.get('modello_id', 'gemini-2.5-flash-lite')

except Exception as e:
    st.error(f"Errore sidebar: {e}")
    st.stop()

# ── TOPBAR ────────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="top-bar">
  <div class="top-bar-hint">
    ← Apri le impostazioni per il modello AI e lo storico verifiche
  </div>
</div>
""", unsafe_allow_html=True)

# ── HEADER ────────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="hero-wrap">
  <div class="hero-left">
    <h1 class="hero-title"><span class="hero-icon">{APP_ICON}</span> Verific<span class="hero-ai">AI</span></h1>
    <p class="hero-sub">{APP_TAGLINE}</p>
    <span class="hero-beta">Versione Beta</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ── ONBOARDING ────────────────────────────────────────────────────────────────────
if not st.session_state._onboarding_done:
    if st.query_params.get("_ob") == "done":
        st.session_state._onboarding_done = True
        st.query_params.pop("_ob", None)
        st.rerun()

    _c_accent       = T['accent']
    _c_text         = T['text']
    _c_text2        = T['text2']
    _c_bg2          = T['bg2']
    _c_border       = T['border']
    _c_card         = T['card']
    _c_accent_light = T['accent_light']
    _c_muted        = T['muted']

    st.markdown(
        f'<div style="background:linear-gradient(135deg,{_c_accent_light} 0%,{_c_card} 100%);'
        f'border:1.5px solid {_c_accent};border-radius:14px;'
        f'padding:1.1rem 1.4rem 0.8rem 1.4rem;margin-bottom:0.8rem;font-family:DM Sans,sans-serif;">'
        f'<div style="display:flex;align-items:flex-start;gap:12px;">'
        f'<div style="flex:1;">'
        f'<div style="font-size:0.9rem;font-weight:800;color:{_c_text};margin-bottom:0.7rem;">Come iniziare</div>'
        f'<div style="display:flex;background:{_c_bg2};border:1px solid {_c_border};border-radius:10px;overflow:hidden;margin-bottom:0.75rem;">'
        f'<div style="flex:1;padding:0.6rem 0.85rem;border-right:1px solid {_c_border};">'
        f'<div style="font-size:0.65rem;font-weight:800;color:{_c_accent};text-transform:uppercase;letter-spacing:0.06em;margin-bottom:3px;">01 · Classe & Materia</div>'
        f'<div style="font-size:0.76rem;color:{_c_text2};">Scegli il livello e la materia</div>'
        f'</div>'
        f'<div style="flex:1;padding:0.6rem 0.85rem;border-right:1px solid {_c_border};">'
        f'<div style="font-size:0.65rem;font-weight:800;color:{_c_accent};text-transform:uppercase;letter-spacing:0.06em;margin-bottom:3px;">02 · Argomento</div>'
        f'<div style="font-size:0.76rem;color:{_c_text2};">Scrivi l\'argomento</div>'
        f'</div>'
        f'<div style="flex:1;padding:0.6rem 0.85rem;">'
        f'<div style="font-size:0.65rem;font-weight:800;color:{_c_accent};text-transform:uppercase;letter-spacing:0.06em;margin-bottom:3px;">03 · Personalizza</div>'
        f'<div style="font-size:0.76rem;color:{_c_text2};">Opzioni avanzate (facoltativo)</div>'
        f'</div>'
        f'</div>'
        f'<div style="text-align:right;">'
        f'<a href="?_ob=done" style="font-size:0.75rem;color:{_c_muted};'
        f'text-decoration:underline;text-underline-offset:2px;cursor:pointer;'
        f'font-family:DM Sans,sans-serif;font-weight:500;">'
        f'Ho capito, non mostrare più →</a>'
        f'</div>'
        f'</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        f'<div style="display:flex;align-items:flex-start;gap:8px;padding:0.6rem 0.9rem;'
        f'margin-bottom:1.2rem;background:{_c_bg2};border-radius:8px;border:1px solid {_c_border};">'
        f'<span style="font-size:0.75rem;color:{_c_muted};line-height:1.45;">'
        f'Le verifiche generate dall\'AI sono <strong style="color:{_c_text2};">suggerimenti didattici</strong>. '
        f'Controlla sempre contenuti e punteggi prima di distribuirle agli studenti.'
        f'</span>'
        f'</div>',
        unsafe_allow_html=True
    )

# ── STEP 1 — CLASSE & MATERIA ─────────────────────────────────────────────────────
st.markdown(f"""
<div class="step-label">
  <span class="step-num">01</span>
  <span class="step-title">Classe e Materia</span>
  <span class="step-line"></span>
</div>
""", unsafe_allow_html=True)

_col_scuola, _col_materia = st.columns(2)
with _col_scuola:
    st.markdown(
        f'<div style="font-size:0.72rem;font-weight:700;color:{T["muted"]};text-transform:uppercase;'
        f'letter-spacing:0.06em;margin-bottom:4px;font-family:DM Sans,sans-serif;">Livello scolastico</div>',
        unsafe_allow_html=True
    )
    difficolta = st.selectbox(
        "Livello scolastico",
        SCUOLE,
        index=SCUOLE.index("Liceo Scientifico") if "Liceo Scientifico" in SCUOLE else 0,
        label_visibility="collapsed",
        key="difficolta_body",
    )
with _col_materia:
    st.markdown(
        f'<div style="font-size:0.72rem;font-weight:700;color:{T["muted"]};text-transform:uppercase;'
        f'letter-spacing:0.06em;margin-bottom:4px;font-family:DM Sans,sans-serif;">Materia</div>',
        unsafe_allow_html=True
    )
    _materie_select = MATERIE + ["✏️ Altra materia..."]
    _materia_sel = st.selectbox("Materia", _materie_select, index=0, label_visibility="collapsed")

if _materia_sel == "✏️ Altra materia...":
    materia_scelta = st.text_input(
        "Scrivi materia:", placeholder="es. Economia Aziendale, Scienze Naturali...",
        key="_materia_custom_input", label_visibility="collapsed"
    ).strip() or "Matematica"
else:
    materia_scelta = _materia_sel or "Matematica"

# ── STEP 2 — ARGOMENTO ────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="ai-hint">
  <span class="ai-hint-icon">💡</span>
  <span><strong>Suggerimento:</strong> più dettagli fornisci nell'argomento e nelle opzioni avanzate, più la verifica sarà precisa e su misura.</span>
</div>
<div class="step-label">
  <span class="step-num">02</span>
  <span class="step-title">Argomento della verifica</span>
  <span class="step-line"></span>
</div>
""", unsafe_allow_html=True)
argomento_area = st.text_area(
    "argomento",
    placeholder="es. Le equazioni di secondo grado\nes. La Rivoluzione Francese",
    height=100,
    label_visibility="collapsed",
    key="argomento_area"
)
argomento = argomento_area.strip()

# ── STEP 3 — PERSONALIZZA ─────────────────────────────────────────────────────────
st.markdown(f"""
<div class="step-label">
  <span class="step-num">03</span>
  <span class="step-title">Personalizza</span>
  <span class="step-line"></span>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="personalizza-wrap">', unsafe_allow_html=True)
with st.expander("Personalizza la verifica"):

    st.markdown(f'<div class="expander-heading">⏱️ Tempistiche e Struttura</div>', unsafe_allow_html=True)
    _c_dur, _c_num = st.columns(2)
    with _c_dur:
        durata_scelta = st.selectbox(
            "Durata della verifica",
            ["30 min", "1 ora", "1 ora e 30 min", "2 ore"],
            index=1,
        )
    with _c_num:
        num_esercizi_totali = st.slider(
            "Numero di esercizi in verifica",
            min_value=1, max_value=15, value=4,
        )

    # ── PUNTEGGI ─────────────────────────────────────────────────────────────────
    st.markdown(f'<div class="expander-heading" style="margin-top:1rem;">🏆 Punteggi</div>', unsafe_allow_html=True)
    _cp1, _cp2, _cp3 = st.columns([2, 2, 2])
    with _cp1:
        mostra_punteggi = st.checkbox("Mostra punteggi per esercizio", value=False, key="mostra_punteggi_body")
    with _cp2:
        con_griglia = st.checkbox("Includi griglia di valutazione", value=False, key="con_griglia_body")
    with _cp3:
        punti_totali = st.number_input(
            "Punti totali", min_value=10, max_value=200, value=100, step=5,
            disabled=not mostra_punteggi, key="punti_totali_body"
        )

st.markdown('</div>', unsafe_allow_html=True)

    
    with st.expander("🎯 Personalizza i singoli esercizi"):
        n_custom = len(st.session_state.esercizi_custom)
        n_liberi = max(0, num_esercizi_totali - n_custom)

        if n_custom == 0:
            st.info(f"Tutti i {num_esercizi_totali} esercizi generati dall'AI.")
        elif n_custom >= num_esercizi_totali:
            st.warning(f"Totale {n_custom}/{num_esercizi_totali} raggiunto — aumenta il numero.")
        else:
            st.success(f"✅ {n_custom} specifici + {n_liberi} liberi = {num_esercizi_totali} totali")

        if st.session_state.esercizi_custom:
            to_remove = None
            for i, ex in enumerate(st.session_state.esercizi_custom):
                st.markdown(f'<div class="expander-heading">Esercizio {i+1}</div>', unsafe_allow_html=True)
                t = st.selectbox("Tipo esercizio", TIPI_ESERCIZIO,
                                 index=TIPI_ESERCIZIO.index(ex.get('tipo', 'Aperto')),
                                 key=f"tipo_{i}", label_visibility="visible")
                st.session_state.esercizi_custom[i]['tipo'] = t

                d = st.text_input("Descrizione dell'esercizio (opzionale)",
                                  value=ex.get('descrizione', ''),
                                  placeholder="es. Risolvi ax²+bx+c=0 mostrando i passaggi",
                                  key=f"desc_{i}", label_visibility="visible")
                st.session_state.esercizi_custom[i]['descrizione'] = d
                _cimg, _cdel = st.columns([3, 1])
                with _cimg:
                    st.markdown('<div class="compact-uploader">', unsafe_allow_html=True)
                    img = st.file_uploader("📎 Immagine allegata",
                                           type=['png','jpg','jpeg'],
                                           key=f"img_{i}", label_visibility="collapsed")
                    st.markdown('</div>', unsafe_allow_html=True)
                    if img: st.session_state.esercizi_custom[i]['immagine'] = img
                    if st.session_state.esercizi_custom[i].get('immagine'):
                        st.image(st.session_state.esercizi_custom[i]['immagine'], width=60)
                with _cdel:
                    st.markdown('<div style="padding-top:4px;">', unsafe_allow_html=True)
                    if st.button("🗑 Rimuovi", key=f"rm_{i}", use_container_width=True):
                        to_remove = i
                    st.markdown('</div>', unsafe_allow_html=True)
                st.markdown('<hr style="margin:0.8rem 0; opacity:0.15;">', unsafe_allow_html=True)
            if to_remove is not None:
                st.session_state.esercizi_custom.pop(to_remove); st.rerun()

        can_add = len(st.session_state.esercizi_custom) < num_esercizi_totali
        if st.button("＋ Aggiungi esercizio specifico", disabled=not can_add):
            st.session_state.esercizi_custom.append({'tipo': 'Aperto', 'descrizione': '', 'immagine': None})
            st.rerun()

    st.markdown(f'<div class="expander-heading" style="margin-top:1rem;">🎯 Istruzioni per l\'AI</div>', unsafe_allow_html=True)
    note_generali = st.text_area(
        "note", label_visibility="collapsed",
        placeholder=NOTE_PLACEHOLDER.get(materia_scelta, "es. Argomenti da privilegiare, tipo di esercizi..."),
        height=80
    )

    st.markdown(f'<div class="expander-heading">📂 File di riferimento</div>', unsafe_allow_html=True)
    st.markdown('<div class="compact-uploader">', unsafe_allow_html=True)
    file_ispirazione = st.file_uploader(
        "📎 Allega PDF o immagine",
        type=['pdf','png','jpg','jpeg'],
        label_visibility="collapsed"
    )
    st.markdown('</div>', unsafe_allow_html=True)

    

# ── BOTTONE GENERA ────────────────────────────────────────────────────────────────
st.markdown('<div class="genera-section">', unsafe_allow_html=True)

genera_btn = st.button(
    "🚀  Genera Verifica",
    use_container_width=True,
    type="primary",
    disabled=_limite_raggiunto
)

if _limite_raggiunto:
    st.markdown(f"""
    <div style="text-align:center;font-size:0.82rem;color:#EF4444;margin-top:0.5rem;
                font-family:'DM Sans',sans-serif;font-weight:600;">
      ⛔ Limite di {LIMITE_MENSILE} verifiche mensili raggiunto. Riprova il mese prossimo.
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown(f"""
    <div class="genera-hint">
      Genera la verifica principale · Versione B, Ridotta e Soluzioni disponibili dopo
    </div>
    """, unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# ── LOGICA GENERAZIONE ────────────────────────────────────────────────────────────
if genera_btn and not _limite_raggiunto:
    if not argomento.strip():
        st.warning("⚠️ Inserisci l'argomento della verifica."); st.stop()
    try:
        model        = genai.GenerativeModel(modello_id)
        materia      = materia_scelta.strip() or "Matematica"
        calibrazione = CALIBRAZIONE_SCUOLA.get(difficolta, "")
        s_es, imgs_es = costruisci_prompt_esercizi(
            st.session_state.esercizi_custom, num_esercizi_totali,
            punti_totali if mostra_punteggi else 0, mostra_punteggi)

        # Al primo giro genera SOLO la fila A (4 step fissi)
        _n_steps = 4
        _step    = [0]
        _t_start = [time.time()]
        _prog    = st.empty()

        def _avanza(testo):
            _step[0] += 1
            perc = int(min(_step[0] / _n_steps, 0.97) * 100)
            _elapsed    = time.time() - _t_start[0]
            _steps_left = max(1, _n_steps - _step[0])
            if _step[0] >= 1 and _elapsed > 2:
                _sec_rimasti = int((_elapsed / _step[0]) * _steps_left)
                if _sec_rimasti > 90:
                    _tempo_str = f"⏱ ~{_sec_rimasti // 60}min {_sec_rimasti % 60:02d}s"
                elif _sec_rimasti > 10:
                    _tempo_str = f"⏱ ancora ~{_sec_rimasti}s"
                else:
                    _tempo_str = "⏱ quasi pronto…"
            else:
                _tempo_str = "⏱ avvio…"

            _prog.markdown(f"""
<div style="margin:0.6rem 0 1rem 0;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
    <div style="font-size:0.82rem;font-weight:600;color:{T['text2']};
                font-family:'DM Sans',sans-serif;">{testo}</div>
    <div style="font-size:0.74rem;color:{T['muted']};font-family:'DM Sans',sans-serif;
                white-space:nowrap;margin-left:12px;">{_tempo_str}</div>
  </div>
  <div style="background:{T['border']};border-radius:100px;height:8px;overflow:hidden;">
    <div style="background:linear-gradient(90deg,{T['accent']},{T['accent']}cc);
                width:{perc}%;height:100%;border-radius:100px;
                transition:width 0.4s ease;"></div>
  </div>
  <div style="text-align:right;font-size:0.68rem;color:{T['muted']};
              font-family:'DM Sans',sans-serif;margin-top:4px;">
    Step {_step[0]} di {_n_steps}
  </div>
</div>
""", unsafe_allow_html=True)

        ris = genera_verifica(
            model=model,
            materia=materia,
            argomento=argomento,
            difficolta=difficolta,
            calibrazione=calibrazione,
            durata=durata_scelta,
            num_esercizi=num_esercizi_totali,
            punti_totali=punti_totali,
            mostra_punteggi=mostra_punteggi,
            con_griglia=con_griglia,
            doppia_fila=False,
            bes_dsa=False,
            perc_ridotta=None,
            bes_dsa_b=False,
            genera_soluzioni=False,
            note_generali=note_generali,
            istruzioni_esercizi=s_es,
            immagini_esercizi=imgs_es,
            file_ispirazione=file_ispirazione,
            on_progress=_avanza,
        )

        def _aggiorna(fid, dati):
            v = st.session_state.verifiche[fid]
            if dati.get('latex'):
                v['latex'] = dati['latex']
                v['latex_originale'] = dati['latex']
            if dati.get('pdf'):
                v['pdf']     = dati['pdf']
                v['pdf_ts']  = time.time()
                v['preview'] = True
            if fid == 'S' and dati.get('testo'):
                v['testo'] = dati['testo']
                v['latex'] = dati.get('latex', '')

        _aggiorna('A', ris['A'])
        # Resetta le varianti in caso di rigenerazione
        st.session_state.verifiche['B'] = _vf()
        st.session_state.verifiche['R'] = _vf()
        st.session_state.verifiche['RB'] = _vf()
        st.session_state.verifiche['S'] = {'latex': None, 'testo': None, 'pdf': None}

        _prog.markdown(f"""
<div style="margin:0.6rem 0 1rem 0;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
    <div style="font-size:0.82rem;font-weight:600;color:{T['success']};
                font-family:'DM Sans',sans-serif;">✅  Verifica pronta!</div>
  </div>
  <div style="background:{T['border']};border-radius:100px;height:8px;overflow:hidden;">
    <div style="background:{T['success']};width:100%;height:100%;border-radius:100px;"></div>
  </div>
</div>
""", unsafe_allow_html=True)
        time.sleep(0.7)
        _prog.empty()

        st.session_state.last_materia   = materia
        st.session_state.last_argomento = ris['titolo']
        st.session_state.last_gen_ts    = time.time()
        st.session_state._onboarding_done = True

        # Salva parametri per uso a posteriori (Versione B, Ridotta, Soluzioni)
        st.session_state['_gen_mostra_punteggi'] = mostra_punteggi
        st.session_state['_gen_con_griglia']     = con_griglia
        st.session_state['_gen_punti_totali']    = punti_totali
        st.session_state['_gen_modello_id']      = modello_id
        st.session_state['_gen_difficolta']      = difficolta
        st.session_state['_gen_materia']         = materia

        try:
            supabase_admin.table("verifiche_storico").insert({
                "user_id":      st.session_state.utente.id,
                "materia":      materia,
                "argomento":    ris['titolo'],
                "scuola":       difficolta,
                "latex_a":      ris['A']['latex'] or None,
                "latex_b":      None,
                "latex_r":      None,
                "modello":      modello_id,
                "num_esercizi": num_esercizi_totali,
            }).execute()
            st.session_state._storico_refresh += 1
            st.toast("✅ Verifica salvata!", icon="💾")
        except Exception as e:
            st.warning(f"⚠️ Salvataggio non riuscito: {e}")

        st.rerun()

    except Exception as e:
        st.error(f"❌ Errore: {e}")


# ── OUTPUT VERIFICA PRINCIPALE ────────────────────────────────────────────────────
if st.session_state.verifiche['A']['latex']:
    st.divider()
    _arg = st.session_state.last_argomento or (argomento if 'argomento' in dir() else 'verifica')
    # Recupera parametri punteggi usati nella generazione
    _mostra_punteggi = st.session_state.get('_gen_mostra_punteggi', False)
    _con_griglia     = st.session_state.get('_gen_con_griglia', False)
    _punti_totali    = st.session_state.get('_gen_punti_totali', 100)
    _modello_id_gen  = st.session_state.get('_gen_modello_id', modello_id)
    _materia_gen     = st.session_state.get('_gen_materia', 'Materia')

    # Mostra verifica A (e B, R, RB se già generate)
    attive = ['A']
    if st.session_state.verifiche['B']['latex']:
        attive.append('B')
    if st.session_state.verifiche['R']['latex']:
        attive.append('R')
    if st.session_state.verifiche['RB']['latex']:
        attive.append('RB')

    for idx, fid in enumerate(attive):
        v = st.session_state.verifiche[fid]
        if idx > 0:
            st.divider()
        with st.container():
            if fid == 'R':
                label_ver = "Verifica Ridotta BES/DSA (Fila A)"
            elif fid == 'RB':
                label_ver = "Verifica Ridotta BES/DSA (Fila B)"
            elif fid == 'B':
                label_ver = "Versione B"
            else:
                label_ver = "La tua verifica"

            st.markdown(f"""
            <div style="background:linear-gradient(135deg, {T['accent_light']} 0%, {T['card']} 100%);
                        border:2px solid {T['accent']};border-radius:16px;padding:0;
                        margin-bottom:1.8rem;overflow:hidden;
                        box-shadow:0 4px 20px {T['accent']}22;">
              <div style="background:{T['accent']};padding:1rem 1.3rem;
                          border-bottom:1px solid {T['accent']};">
                <div style="display:flex;align-items:center;gap:12px;">
                  <span style="font-size:1.8rem;">{APP_ICON}</span>
                  <div style="flex:1;">
                    <div style="font-family:'DM Sans',sans-serif;font-size:1.3rem;
                                font-weight:900;color:#ffffff;letter-spacing:-0.02em;">
                      {label_ver}
                    </div>
                    <div style="font-size:0.75rem;color:#ffffff;opacity:0.85;
                                font-weight:600;margin-top:2px;">
                      Generata con successo
                    </div>
                  </div>
                  <div style="background:#ffffff22;backdrop-filter:blur(10px);
                              border:1px solid #ffffff33;border-radius:20px;
                              padding:6px 16px;font-size:0.72rem;font-weight:700;
                              color:#ffffff;letter-spacing:0.05em;text-transform:uppercase;">
                    ✓ Pronta
                  </div>
                </div>
              </div>
              <div style="padding:1.2rem 1.3rem;background:{T['card']};">
                <div style="display:flex;align-items:flex-start;gap:10px;
                            background:{T['accent_light']};border-left:3px solid {T['accent']};
                            border-radius:8px;padding:12px 16px;">
                  <span style="font-size:1.1rem;flex-shrink:0;">⚠️</span>
                  <span style="font-size:0.82rem;color:{T['text2']};line-height:1.5;">
                    Le verifiche generate sono <strong style="color:{T['text']};">suggerimenti didattici</strong>.
                    Rivedi sempre il contenuto prima della distribuzione — il docente è responsabile del materiale finale.
                  </span>
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            if v['pdf']:
                pdf_size = _stima_dimensione(v['pdf'])
                st.download_button(
                    label=f"📄 Scarica PDF — Alta qualità ({pdf_size})",
                    data=v['pdf'],
                    file_name=f"Verifica_{_arg}_{fid}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    key=f"dl_{fid}"
                )
            else:
                if st.button("📄 Genera PDF", key=f"dlc_{fid}", use_container_width=True):
                    with st.spinner("Compilazione…"):
                        pdf, err = compila_pdf(v['latex'])
                    if pdf:
                        st.session_state.verifiche[fid]['pdf'] = pdf
                        st.session_state.verifiche[fid]['pdf_ts'] = time.time()
                        st.rerun()
                    else:
                        st.error("Errore PDF")
                        with st.expander("Log"): st.text(err)

            st.write("")

            st.markdown(f"""
            <div class="modifica-hint">
              <span>
                <strong>La verifica ti soddisfa?</strong> Scarica il PDF — oppure, se vuoi apportare correzioni
                (cambiare un esercizio, modificare i dati, variare la difficoltà, aggiungere un sottopunto…),
                apri il pannello qui sotto e descrivi nel dettaglio cosa cambiare: più sei preciso, migliore sarà il risultato.
              </span>
            </div>
            """, unsafe_allow_html=True)

            with st.expander("✏️ Modifica questa verifica", expanded=False):
                st.markdown(f"""
                <div style="font-size:0.85rem;color:{T['text2']};margin-bottom:0.8rem;line-height:1.5;">
                    Descrivi le modifiche che vuoi apportare. Esempi:<br>
                    • "Aggiungi un esercizio sulla proprietà distributiva"<br>
                    • "Rimuovi l'esercizio 3"<br>
                    • "Cambia i numeri dell'esercizio 2 con valori più piccoli"<br>
                    • "Aumenta la difficoltà dell'esercizio 4"
                </div>
                """, unsafe_allow_html=True)

                richiesta_modifica = st.text_area(
                    "Cosa vuoi modificare?",
                    height=100,
                    placeholder="es. Sostituisci l'esercizio 2 con un problema sulla velocità media",
                    key=f"modifica_input_{fid}",
                    label_visibility="collapsed"
                )

                col_mod1, col_mod2 = st.columns([1, 1])
                with col_mod1:
                    if st.button("🔄 Applica Modifiche", key=f"modifica_btn_{fid}",
                               use_container_width=True, disabled=not richiesta_modifica.strip()):
                        try:
                            with st.spinner("⏳ Modifica in corso..."):
                                model = genai.GenerativeModel(_modello_id_gen)
                                latex_modificato = modifica_verifica_con_ai(
                                    v['latex'],
                                    richiesta_modifica.strip(),
                                    model
                                )
                                latex_modificato = fix_items_environment(latex_modificato)
                                latex_modificato = rimuovi_vspace_corpo(latex_modificato)
                                if _mostra_punteggi:
                                    latex_modificato = rimuovi_punti_subsection(latex_modificato)
                                    latex_modificato = riscala_punti(latex_modificato, _punti_totali)
                                if _con_griglia:
                                    latex_modificato = inietta_griglia(latex_modificato, _punti_totali)
                                st.session_state.verifiche[fid]['latex'] = latex_modificato
                                pdf_mod, err_mod = compila_pdf(latex_modificato)
                                if pdf_mod:
                                    st.session_state.verifiche[fid]['pdf'] = pdf_mod
                                    st.session_state.verifiche[fid]['pdf_ts'] = time.time()
                                    st.session_state.verifiche[fid]['preview'] = True
                                    st.session_state.verifiche[fid]['docx'] = None
                                    st.success("✅ Modifiche applicate!")
                                    time.sleep(0.8)
                                    st.rerun()
                                else:
                                    st.error("❌ Errore nella compilazione del PDF modificato")
                                    if err_mod:
                                        with st.expander("Log errore"):
                                            st.text(err_mod)
                        except Exception as e:
                            st.error(f"❌ Errore durante la modifica: {str(e)}")

                with col_mod2:
                    ha_originale = 'latex_originale' in v and v.get('latex_originale')
                    if st.button("🗑️ Ripristina Originale", key=f"reset_mod_{fid}",
                               use_container_width=True,
                               disabled=not ha_originale,
                               help="Torna alla versione generata inizialmente"):
                        if ha_originale:
                            st.session_state.verifiche[fid]['latex'] = v['latex_originale']
                            pdf_orig, _ = compila_pdf(v['latex_originale'])
                            if pdf_orig:
                                st.session_state.verifiche[fid]['pdf'] = pdf_orig
                                st.session_state.verifiche[fid]['pdf_ts'] = time.time()
                                st.session_state.verifiche[fid]['docx'] = None
                            st.success("✅ Versione originale ripristinata!")
                            time.sleep(0.5)
                            st.rerun()

            st.write("")

            if v['docx']:
                docx_size = _stima_dimensione(v['docx'])
                st.download_button(
                    label=f"📝 Scarica File Word Modificabile ({docx_size})",
                    data=v['docx'],
                    file_name=f"Verifica_{_arg}_{fid}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                    key=f"dld_{fid}"
                )
                st.markdown(f"""
                    <div class="hint-docx" style="margin-top: -10px; margin-bottom: 15px;">
                        💡 <b>Nota:</b> La versione Word è modificabile ma ha una resa grafica inferiore.
                        I grafici complessi di funzione (TikZ/Plot) non compaiono in Word e vanno aggiunti a mano.
                    </div>
                """, unsafe_allow_html=True)
            else:
                _docx_gen_key = f"_docx_generating_{fid}"
                if st.button("📝 Genera File Word Modificabile", key=f"dldc_{fid}", use_container_width=True):
                    st.session_state[_docx_gen_key] = True
                if st.session_state.get(_docx_gen_key, False):
                    with st.spinner("⏳ Conversione Word…"):
                        db, de = latex_to_docx_via_ai(v['latex'], con_griglia=_con_griglia)
                    if db:
                        st.session_state.verifiche[fid]['docx'] = db
                        st.session_state.verifiche[fid]['docx_ts'] = time.time()
                        st.session_state[_docx_gen_key] = False
                        st.rerun()
                    else:
                        st.session_state[_docx_gen_key] = False
                        st.error("Errore Word")
                        with st.expander("Log"): st.text(de)

            st.write("")

            if v['preview'] and v['pdf']:
                with st.expander("👁 Anteprima PDF", expanded=False):
                    b64 = base64.b64encode(v['pdf']).decode()
                    st.markdown(f"""
                    <iframe src="data:application/pdf;base64,{b64}#toolbar=0&navpanes=0&scrollbar=1"
                            style="width:100%;height:500px;border:none;border-radius:8px;display:block;"></iframe>
                    """, unsafe_allow_html=True)

            _spacer, _tex_col = st.columns([3, 1])
            with _tex_col:
                st.markdown('<div class="tex-btn-wrap">', unsafe_allow_html=True)
                st.download_button(
                    "⬇ Sorgente .tex",
                    data=v['latex'].encode('utf-8'),
                    file_name=f"Verifica_{_arg}_{fid}.tex",
                    mime="text/plain",
                    key=f"dl_tex_{fid}",
                    help="Scarica il sorgente LaTeX per modificarlo"
                )
                st.markdown('</div>', unsafe_allow_html=True)

    # ── ZONA "GENERA ALTRO" (a posteriori) ───────────────────────────────────────
    st.divider()
    st.markdown(f"""
    <div style="background:{T['bg2']};border:1.5px solid {T['border2']};border-radius:14px;
                padding:1.2rem 1.4rem;margin-bottom:1.2rem;">
      <div style="font-size:0.95rem;font-weight:800;color:{T['text']};
                  font-family:'DM Sans',sans-serif;margin-bottom:0.3rem;">
        🎯 Soddisfatto della verifica? Genera anche:
      </div>
      <div style="font-size:0.8rem;color:{T['text2']};font-family:'DM Sans',sans-serif;line-height:1.5;">
        Versione B, Ridotta BES/DSA e Soluzioni vengono generate partendo dalla verifica che hai già approvato — senza ricominciare da capo.
      </div>
    </div>
    """, unsafe_allow_html=True)

    _gc1, _gc2, _gc3 = st.columns(3)

    # ── VERSIONE B ────────────────────────────────────────────────────────────────
    with _gc1:
        _ha_b = bool(st.session_state.verifiche['B']['latex'])
        if _ha_b:
            if st.session_state.verifiche['B']['pdf']:
                st.download_button(
                    "📄 Scarica Versione B",
                    data=st.session_state.verifiche['B']['pdf'],
                    file_name=f"Verifica_{_arg}_B.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    key="dl_b_post"
                )
            else:
                st.info("✅ Versione B pronta (ricompila per PDF)")
        else:
            if st.button("📄 Genera Versione B", use_container_width=True, key="btn_gen_b"):
                with st.spinner("Generazione Versione B…"):
                    try:
                        _model_b = genai.GenerativeModel(_modello_id_gen)
                        _rb = _model_b.generate_content(
                            prompt_versione_b(st.session_state.verifiche['A']['latex'])
                        )
                        _corpo_b = pulisci_corpo_latex(
                            _rb.text.replace("```latex", "").replace("```", "").strip()
                        )
                        # Riusa preambolo di A, sostituisce il corpo
                        _latex_a_base = st.session_state.verifiche['A']['latex']
                        _idx_b = _latex_a_base.find('\\subsection*')
                        if _idx_b > 0:
                            _latex_b_final = _latex_a_base[:_idx_b] + _corpo_b
                        else:
                            _latex_b_final = _corpo_b
                        # Aggiorna etichetta "Versione B" nel titolo
                        _latex_b_final = re.sub(
                            r'(\\textbf\{\\large [^}]+)\}(\s*\\\\)',
                            lambda m: m.group(0).rstrip('\\').rstrip() + ' — Versione B} \\\\',
                            _latex_b_final, count=1
                        )
                        _latex_b_final = fix_items_environment(_latex_b_final)
                        _latex_b_final = rimuovi_vspace_corpo(_latex_b_final)
                        if _mostra_punteggi:
                            _latex_b_final = rimuovi_punti_subsection(_latex_b_final)
                            _latex_b_final = riscala_punti(_latex_b_final, _punti_totali)
                        if _con_griglia:
                            _latex_b_final = inietta_griglia(_latex_b_final, _punti_totali)
                        _pdf_b, _err_b = compila_pdf(_latex_b_final)
                        st.session_state.verifiche['B']['latex'] = _latex_b_final
                        st.session_state.verifiche['B']['latex_originale'] = _latex_b_final
                        if _pdf_b:
                            st.session_state.verifiche['B']['pdf'] = _pdf_b
                            st.session_state.verifiche['B']['preview'] = True
                        st.rerun()
                    except Exception as _e_b:
                        st.error(f"Errore Versione B: {_e_b}")
        st.caption("Stessa verifica con dati diversi, per evitare copiatura tra banchi")

    # ── VERSIONE RIDOTTA BES/DSA ──────────────────────────────────────────────────
    with _gc2:
        _ha_r = bool(st.session_state.verifiche['R']['latex'])
        if _ha_r:
            if st.session_state.verifiche['R']['pdf']:
                st.download_button(
                    "📄 Scarica Versione Ridotta",
                    data=st.session_state.verifiche['R']['pdf'],
                    file_name=f"Verifica_{_arg}_Ridotta.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    key="dl_r_post"
                )
            else:
                st.info("✅ Versione Ridotta pronta (ricompila per PDF)")
        else:
            _perc_r = st.select_slider(
                "Riduzione",
                options=[10, 20, 30], value=20,
                format_func=lambda x: f"-{x}% esercizi",
                key="perc_ridotta_post"
            )
            if st.button("♿ Genera Versione Ridotta", use_container_width=True, key="btn_gen_r"):
                with st.spinner("Generazione versione BES/DSA…"):
                    try:
                        _model_r = genai.GenerativeModel(_modello_id_gen)
                        _rb_r = _model_r.generate_content(prompt_versione_ridotta(
                            st.session_state.verifiche['A']['latex'],
                            _materia_gen,
                            _perc_r,
                            _mostra_punteggi,
                            _punti_totali
                        ))
                        _corpo_r = pulisci_corpo_latex(
                            _rb_r.text.replace("```latex", "").replace("```", "").strip()
                        )
                        _latex_a_base = st.session_state.verifiche['A']['latex']
                        _idx_r = _latex_a_base.find('\\subsection*')
                        _latex_r = (_latex_a_base[:_idx_r] + _corpo_r) if _idx_r > 0 else _corpo_r
                        _latex_r = fix_items_environment(_latex_r)
                        _latex_r = rimuovi_vspace_corpo(_latex_r)
                        if _mostra_punteggi:
                            _latex_r = rimuovi_punti_subsection(_latex_r)
                            _latex_r = riscala_punti(_latex_r, _punti_totali)
                        if _con_griglia:
                            _latex_r = inietta_griglia(_latex_r, _punti_totali)
                        _pdf_r, _ = compila_pdf(_latex_r)
                        st.session_state.verifiche['R']['latex'] = _latex_r
                        st.session_state.verifiche['R']['latex_originale'] = _latex_r
                        if _pdf_r:
                            st.session_state.verifiche['R']['pdf'] = _pdf_r
                            st.session_state.verifiche['R']['preview'] = True
                        st.rerun()
                    except Exception as _e_r:
                        st.error(f"Errore Versione Ridotta: {_e_r}")
        st.caption("Versione alleggerita per studenti BES/DSA/sostegno")

    # ── SOLUZIONI ─────────────────────────────────────────────────────────────────
    with _gc3:
        _ha_s = bool(st.session_state.verifiche['S'].get('testo'))
        if _ha_s:
            v_s = st.session_state.verifiche['S']
            if v_s.get('pdf'):
                st.download_button(
                    "📋 Scarica Soluzioni PDF",
                    data=v_s['pdf'],
                    file_name=f"Soluzioni_{_arg}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    key="dl_sol_post"
                )
            if v_s.get('testo'):
                with st.expander("👁 Mostra soluzioni", expanded=False):
                    st.markdown(v_s['testo'])
        else:
            if st.button("📋 Genera Soluzioni", use_container_width=True, key="btn_gen_sol"):
                with st.spinner("Generazione soluzioni…"):
                    try:
                        _model_s = genai.GenerativeModel(_modello_id_gen)
                        _rs = _model_s.generate_content(prompt_soluzioni(
                            st.session_state.verifiche['A']['latex'],
                            _materia_gen,
                        ))
                        _testo_s = _rs.text.strip()
                        _titolo_s = f"Soluzioni — {_materia_gen}: {_arg}"
                        _latex_s = (
                            f"\\documentclass[11pt,a4paper]{{article}}\n"
                            f"\\usepackage[utf8]{{inputenc}}\n\\usepackage[italian]{{babel}}\n"
                            f"\\usepackage{{amsmath,amsfonts,amssymb,geometry}}\n"
                            f"\\geometry{{margin=2cm}}\n\\setlength{{\\parskip}}{{4pt}}\n"
                            f"\\pagestyle{{empty}}\n\\begin{{document}}\n"
                            f"\\begin{{center}}\n  \\textbf{{\\large {_titolo_s}}} \\\\\n"
                            f"  \\vspace{{0.2cm}}\n"
                            f"  {{\\small \\textit{{Documento riservato al docente — non distribuire agli studenti}}}}\n"
                            f"\\end{{center}}\n\\vspace{{0.4cm}}\n"
                            f"{_testo_s}\n\\end{{document}}"
                        )
                        _pdf_s, _ = compila_pdf(_latex_s)
                        st.session_state.verifiche['S']['testo'] = _testo_s
                        st.session_state.verifiche['S']['latex'] = _latex_s
                        if _pdf_s:
                            st.session_state.verifiche['S']['pdf'] = _pdf_s
                        st.rerun()
                    except Exception as _e_s:
                        st.error(f"Errore Soluzioni: {_e_s}")
        st.caption("Documento riservato al docente, non distribuire agli studenti")

    # Se Versione B esiste, offri anche ridotta B
    if st.session_state.verifiche['B']['latex'] and not st.session_state.verifiche['RB']['latex']:
        st.write("")
        _crb, _csp = st.columns([1, 2])
        with _crb:
            _perc_rb = st.session_state.get('perc_ridotta_post', 20)
            if st.button("♿ Genera Versione Ridotta Fila B", use_container_width=True, key="btn_gen_rb"):
                with st.spinner("Generazione ridotta Fila B…"):
                    try:
                        _model_rb = genai.GenerativeModel(_modello_id_gen)
                        _rb_rb = _model_rb.generate_content(prompt_versione_ridotta(
                            st.session_state.verifiche['B']['latex'],
                            _materia_gen,
                            _perc_rb,
                            _mostra_punteggi,
                            _punti_totali,
                            "Fila B"
                        ))
                        _corpo_rb = pulisci_corpo_latex(
                            _rb_rb.text.replace("```latex", "").replace("```", "").strip()
                        )
                        _latex_b_base = st.session_state.verifiche['B']['latex']
                        _idx_rb = _latex_b_base.find('\\subsection*')
                        _latex_rb = (_latex_b_base[:_idx_rb] + _corpo_rb) if _idx_rb > 0 else _corpo_rb
                        _latex_rb = fix_items_environment(_latex_rb)
                        _latex_rb = rimuovi_vspace_corpo(_latex_rb)
                        if _mostra_punteggi:
                            _latex_rb = rimuovi_punti_subsection(_latex_rb)
                            _latex_rb = riscala_punti(_latex_rb, _punti_totali)
                        _pdf_rb, _ = compila_pdf(_latex_rb)
                        st.session_state.verifiche['RB']['latex'] = _latex_rb
                        if _pdf_rb:
                            st.session_state.verifiche['RB']['pdf'] = _pdf_rb
                        st.rerun()
                    except Exception as _e_rb:
                        st.error(f"Errore Ridotta B: {_e_rb}")

# ── FOOTER ────────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="app-footer">
  ⚠️ Le verifiche generate dall'AI sono suggerimenti didattici — rivedi sempre il contenuto
  prima di distribuirlo agli studenti. Il docente è responsabile del materiale finale.<br>
  <span style="opacity:0.55;">VerificAI · Versione Beta</span>
</div>
""", unsafe_allow_html=True)

import streamlit.components.v1 as components
components.html(f"""
<style>
  body {{ margin: 0; padding: 0; background: transparent; }}
  #share-btn {{
    background: none;
    border: none;
    cursor: pointer;
    color: {T['accent']};
    font-weight: 600;
    font-size: 0.72rem;
    font-family: 'DM Sans', sans-serif;
    padding: 0;
    display: block;
    margin: 0 auto;
    text-align: center;
    width: 100%;
  }}
  #share-btn:hover {{ text-decoration: underline; }}
</style>
<button id="share-btn" onclick="copyLink()">🔗 Condividi con i colleghi</button>
<script>
function copyLink() {{
  var url = "{SHARE_URL}";
  var btn = document.getElementById("share-btn");
  var ta = document.createElement("textarea");
  ta.value = url;
  ta.style.cssText = "position:fixed;top:0;left:0;opacity:0;";
  document.body.appendChild(ta);
  ta.focus();
  ta.select();
  var ok = false;
  try {{ ok = document.execCommand("copy"); }} catch(e) {{}}
  document.body.removeChild(ta);
  if (ok) {{
    btn.innerText = "✅ Link copiato!";
    setTimeout(function() {{ btn.innerText = "🔗 Condividi con i colleghi"; }}, 2000);
  }} else {{
    btn.innerText = url;
  }}
}}
</script>
""", height=30)

