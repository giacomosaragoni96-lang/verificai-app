# ── main.py — VerificAI ──────────────────────────────────────────────────────
# Macchina a tre stati:
#   STAGE_INPUT  → configurazione snella + tasto Genera
#   STAGE_REVIEW → revisione esercizio (selectbox + KaTeX + PDF strip)
#   STAGE_FINAL  → download PDF primario + varianti on-demand + secondari small
# ─────────────────────────────────────────────────────────────────────────────

import streamlit as st
import streamlit.components.v1 as components
import base64
import io
import zipfile
import copy
import logging
import re
import os
import time
from datetime import datetime, timezone

from ai_client import crea_modello, configura as configura_ai, riepilogo_uso

from sidebar import render_sidebar
from generation import (
    genera_verifica, analizza_documento_caricato, compila_contesto_generazione,
    rigenera_singolo_blocco,
)
from prompts import (
    prompt_versione_b, prompt_versione_ridotta, prompt_soluzioni,
    prompt_rubrica_valutazione, prompt_variante_rapida, istruzione_livello_esercizio,
    prompt_nuovo_esercizio,
    REGOLA_SOTTOPUNTI_MODIFICA, REGOLA_GRAFICO_CURVE,
)
from docx_export import latex_to_docx_via_ai, _rubrica_to_docx
from scheda import genera_scheda
from subscription_management import calcola_entitlements, get_subscription_manager
from ui_upgrade import render_upgrade
from ui_legale import render_termini, render_rimborsi
from licenze import attiva_licenza, riconvalida_se_serve
from latex_utils import (
    conta_pagine_pdf, riduci_a_pagine, compila_pdf, compila_pdf_sicuro, inietta_griglia, rimuovi_griglia, inserisci_logo, copia_intestazione_con_logo, rimuovi_logo_b64, riscala_punti, riscala_punti_custom,
    fix_items_environment, rifinisci_scelta_multipla_e_vf, rimuovi_vspace_corpo, pulisci_corpo_latex,
    rimuovi_punti_subsection, pdf_to_images_bytes,
    extract_blocks, reconstruct_latex, extract_corpo, extract_preambolo,
    parse_pts_from_block_body, riscala_single_block,
    parse_items_from_block, apply_item_pts_to_body,
    prepara_esercizi_aperti, conta_punti_latex,
    migliora_spaziatura_sottopunti, limita_altezza_grafici, aggiungi_spaziatura_grafici_tabelle,
    normalizza_sottopunti_inline, bilancia_punti, esercizi_con_grafico_mancante,
)
from config import (
    APP_NAME, APP_ICON, SHARE_URL, FEEDBACK_FORM_URL,
    LIMITE_MENSILE, ADMIN_EMAILS, MODELLI_DISPONIBILI, THEMES,
    SCUOLE, CALIBRAZIONE_SCUOLA, MATERIE, esempio_richiesta, TIPI_ESERCIZIO,
    DURATE, DURATA_DEFAULT, parametri_durata, etichetta_durata,
    MOSTRA_BADGE_PRO, MONETIZZAZIONE_ATTIVA, ETICHETTE_FUNZIONI, LEGALE_PRONTO, TETTO_BREVE, MAX_FACCIATE, WORD_ATTIVO,
    MODEL_FAST_ID, get_model_id_per_piano, THEME_LABELS,
)
from dotenv import load_dotenv
from supabase import create_client, Client
from auth import mostra_auth, ripristina_sessione
from styles import get_css, _is_light_color
from ui_banca import render_banca
from ui_helpers import (
    render_privacy,
    _make_katex_html,
    STAGE_INPUT, STAGE_PREVIEW, STAGE_REVIEW, STAGE_FINAL,
    _reset_label, _render_limite_raggiunto, _mostra_errore, _mostra_errore_pdf,
    separa_argomento_e_note, _esc, spazio, messaggio,
)

logger = logging.getLogger("verificai.main")

# ── ST_YLED (opzionale — sticky_header + split_button) ───────────────────────
# pip install st-styled | https://github.com/EvobyteDigitalBiology/st-styled
# Se non installato: fallback nativo (CSS injection + st.popover)
try:
    import st_yled as _styl
    _STYLED_AVAILABLE = True
except ImportError:
    _styl = None
    _STYLED_AVAILABLE = False


# ── COSTANTI STAGE ────────────────────────────────────────────────────────────
STAGE_MIE_VERIFICHE = "MIE_VERIFICHE"  # pagina "Le tue verifiche"
STAGE_UPGRADE = "UPGRADE"               # pagina «Passa a Pro»
STAGE_BANCA = "BANCA"                   # pagina "Banca esercizi" (solo admin)

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title=APP_NAME,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── SUPABASE ──────────────────────────────────────────────────────────────────
# Temporaneamente disabilitato per test - creare il file .streamlit/secrets.toml per abilitare
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    SUPABASE_SERVICE_KEY = st.secrets["SUPABASE_SERVICE_KEY"]
    supabase_admin: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    SUPABASE_ENABLED = True
except Exception as e:
    # Fallback per test senza database
    supabase = None
    supabase_admin = None
    SUPABASE_ENABLED = False
    logger.error(f"Database Supabase non configurato: {e}")
    st.warning("⚠️ Il database non è raggiungibile: lo storico e il salvataggio non funzioneranno.")

# ── TEMA — inizializzazione ───────────────────────────────────────────────────
# Temi disponibili: carta (default) e notte. Una chiave non più presente (sessioni vecchie) → carta.
if "theme" not in st.session_state:
    st.session_state.theme = "carta"

_theme_key = st.session_state.theme
# Fallback: qualsiasi chiave non più presente in THEMES → carta
if _theme_key not in THEMES:
    _theme_key = list(THEMES.keys())[0]   # sempre "carta"
    st.session_state.theme = _theme_key
T = THEMES[_theme_key]

# ── CONFIGURAZIONE API ────────────────────────────────────────────────────────
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    # Temporaneamente usa una API key fittizia per testare l'interfaccia
    API_KEY = "test_api_key_temporanea"
    st.warning("⚠️ API Google temporaneamente non configurata - la generazione non funzionerà ma puoi testare l'interfaccia")
configura_ai(API_KEY)

# ── VERIFICA DISPONIBILITÀ LATEX ─────────────────────────────────────────────────
# Sarà fatto dopo l'autenticazione per essere visibile all'utente

# ── Pagina pubblica: informativa sulla privacy (richiesta da Google per il login) ──
# Solo testo statico, visibile senza accedere; non dà accesso a nessuna funzione dell'app.
if st.query_params.get("pagina") in ("privacy", "termini", "rimborsi"):
    st.markdown(get_css(T), unsafe_allow_html=True)
    _pag = st.query_params.get("pagina")
    if _pag == "termini":
        render_termini(T)
    elif _pag == "rimborsi":
        render_rimborsi(T)
    else:
        render_privacy(T, FEEDBACK_FORM_URL)
    st.stop()

# ── AUTENTICAZIONE ────────────────────────────────────────────────────────────
if "utente" not in st.session_state:
    st.session_state.utente = None

# Ripristina sessione esistente
if st.session_state.utente is None:
    ripristina_sessione(supabase)

# Mostra auth se non loggato
if st.session_state.utente is None:
    mostra_auth(supabase)
    st.stop()

# ── VERIFICA DISPONIBILITÀ LATEX (dopo autenticazione) ─────────────────────────────
try:
    import subprocess
    result = subprocess.run(["pdflatex", "--version"], capture_output=True, text=True, timeout=5)
    if result.returncode != 0:
        st.error("⚠️ **PDF non disponibile** - LaTeX (pdflatex) non è installato correttamente in questo ambiente. La generazione PDF non funzionerà.")
        LATEX_AVAILABLE = False
    else:
        LATEX_AVAILABLE = True
except (FileNotFoundError, subprocess.TimeoutExpired):
    st.error("⚠️ **PDF non disponibile** - LaTeX non è installato in questo ambiente. La generazione PDF non sarà disponibile.")
    LATEX_AVAILABLE = False


# ═══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _get_verifiche_mese(user_id):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    primo = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
    try:
        res = supabase_admin.table("verifiche_storico")\
            .select("id", count="exact")\
            .eq("user_id", user_id)\
            .gte("created_at", primo).execute()
        return res.count or 0
    except Exception as e:
        # None = «non lo so»: chi ha un tetto non può creare finché il conteggio non torna (mai 0)
        logger.warning("_get_verifiche_mese failed for %s: %s", user_id, e)
        return None


def _verifiche_recenti(user_id):
    """Verifiche create dall'utente negli ultimi TETTO_BREVE['minuti'] minuti; None se non si legge (non blocca)."""
    from datetime import datetime, timedelta, timezone
    da = (datetime.now(timezone.utc) - timedelta(minutes=TETTO_BREVE["minuti"])).isoformat()
    try:
        res = supabase_admin.table("verifiche_storico").select("id", count="exact")\
            .eq("user_id", user_id).gte("created_at", da).execute()
        return res.count or 0
    except Exception as e:
        logger.warning("_verifiche_recenti failed for %s: %s", user_id, e)
        return None


def _puo_generare_ora():
    """(ok, motivo): ricalcola il tetto mensile adesso. Chi ha un tetto non crea se il conteggio non si legge."""
    if _is_admin or not st.session_state.utente:
        return True, ""
    uid = st.session_state.utente.id
    n = _get_verifiche_mese(uid)
    ent = calcola_entitlements(_abbonamento_utente(uid), n, False)
    if ent.errore_conteggio:
        return False, "Non riesco a controllare il tuo utilizzo mensile in questo momento. Riprova tra qualche istante."
    if ent.limite_raggiunto:
        return False, f"Hai usato le {int(ent.tetto_mensile)} verifiche di questo mese. Tornano a disposizione il mese prossimo."
    recenti = _verifiche_recenti(uid)
    if recenti is not None and recenti >= TETTO_BREVE["verifiche"]:
        return False, (f"Hai creato {recenti} verifiche in pochi minuti. Aspetta qualche minuto e riprova: "
                       "serve a tenere il servizio veloce per tutti.")
    return True, ""


def _giorni_al_reset():
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    if now.month == 12:
        reset = now.replace(year=now.year + 1, month=1, day=1,
                            hour=0, minute=0, second=0, microsecond=0)
    else:
        reset = now.replace(month=now.month + 1, day=1,
                            hour=0, minute=0, second=0, microsecond=0)
    d = reset - now
    return d.days, d.seconds // 3600


def _dl(*args, **kwargs):
    """st.download_button senza rerun al clic: scaricare non deve ricaricare tutta la pagina."""
    kwargs.setdefault("on_click", "ignore")
    return st.download_button(*args, **kwargs)


def _stima(b):
    if not b: return "—"
    kb = len(b) / 1024
    return f"{kb:.0f} KB" if kb < 1024 else f"{kb/1024:.1f} MB"


def _rubrica_to_pdf(rubrica_testo: str, materia: str = "", livello: str = "") -> bytes | None:
    """Converte il testo Markdown della rubrica di valutazione in PDF via LaTeX/pdflatex."""
    try:
        import re as _re
        from latex_utils import compila_pdf

        def _esc(t: str) -> str:
            t = t.replace('\\', r'\textbackslash{}')
            for a, b in [
                ('&',  r'\&'), ('%', r'\%'), ('#', r'\#'),
                ('_',  r'\_'), ('^', r'\^{}'), ('~', r'\~{}'),
                ('{',  r'\{'), ('}', r'\}'), ('$', r'\$'),
            ]:
                t = t.replace(a, b)
            return t

        def _md2tex(t: str) -> str:
            return _re.sub(r'\*\*([^*]+)\*\*', r'\\textbf{\1}', t)

        meta_esc = _esc(f"{materia} · {livello}") if (materia or livello) else ""

        # ── Strip AI preamble: skip everything before the first ## / ### ────────
        lines_raw = rubrica_testo.strip().split("\n")
        start_idx = 0
        for _i, _l in enumerate(lines_raw):
            if _l.strip().startswith("## ") or _l.strip().startswith("### "):
                start_idx = _i
                break
        lines_raw = lines_raw[start_idx:]

        body_lines: list[str] = []
        in_list   = False
        prev_blank = False   # collapse consecutive blank lines

        for line in lines_raw:
            s = line.strip()

            # ── Blank line ────────────────────────────────────────────────────
            if not s:
                if in_list:
                    body_lines.append(r'\end{itemize}')
                    in_list = False
                if not prev_blank:          # only one vspace per blank group
                    body_lines.append(r'\vspace{5pt}')
                prev_blank = True
                continue
            prev_blank = False

            # ── Top-level section marker (skip, title is in the header) ───────
            if s.startswith("## "):
                continue

            # ── ### Sub-section (Legenda fasce / Indicatori per esercizio) ────
            if s.startswith("### "):
                if in_list:
                    body_lines.append(r'\end{itemize}')
                    in_list = False
                body_lines.append(
                    f'\\section*{{{_md2tex(_esc(s[4:]))}}}'
                )

            # ── Bullet item (handles "- " and "  - " after strip) ────────────
            elif s.startswith("- ") or s.startswith("* "):
                if not in_list:
                    body_lines.append(
                        r'\begin{itemize}[noitemsep,topsep=2pt,leftmargin=1.4em]'
                    )
                    in_list = True
                body_lines.append(f'  \\item {_md2tex(_esc(s[2:]))}')

            # ── Bold line: **full** OR **partial** (extra text) ───────────────
            elif s.startswith("**") and "**" in s[2:]:
                if in_list:
                    body_lines.append(r'\end{itemize}')
                    in_list = False
                tex_line = _md2tex(_esc(s))
                body_lines.append(
                    r'\vspace{4pt}' '\n'
                    r'\noindent ' + tex_line + r'\\[-1pt]'
                )

            # ── Plain paragraph ───────────────────────────────────────────────
            else:
                if in_list:
                    body_lines.append(r'\end{itemize}')
                    in_list = False
                body_lines.append(_md2tex(_esc(s)))

        if in_list:
            body_lines.append(r'\end{itemize}')

        latex = (
            r'\documentclass[a4paper,11pt]{article}' '\n'
            r'\usepackage[utf8]{inputenc}' '\n'
            r'\usepackage[T1]{fontenc}' '\n'
            r'\usepackage[italian]{babel}' '\n'
            r'\usepackage[top=2cm,bottom=2cm,left=2.2cm,right=2.2cm]{geometry}' '\n'
            r'\usepackage[dvipsnames]{xcolor}' '\n'
            r'\usepackage{titlesec}' '\n'
            r'\usepackage{enumitem}' '\n'
            r'\usepackage{microtype}' '\n'
            r'\definecolor{rubTeal}{HTML}{0A8F72}' '\n'
            r'\definecolor{rubDark}{HTML}{1A2E25}' '\n'
            r'\definecolor{rubGray}{HTML}{6B7280}' '\n'
            r'\titleformat{\section}{\normalsize\bfseries\color{rubTeal}}'
            r'{}{0em}{}[\vspace{-3pt}{\color{rubTeal!40}\hrule height 0.5pt}\vspace{1pt}]' '\n'
            r'\titlespacing*{\section}{0pt}{10pt}{4pt}' '\n'
            r'\setlength{\parskip}{3pt}\setlength{\parindent}{0pt}' '\n'
            r'\pagestyle{empty}' '\n'
            r'\begin{document}' '\n'
            r'\begin{center}' '\n'
            r'{\large\bfseries\color{rubTeal} Rubrica di Valutazione}\\[3pt]' '\n'
            + (f'{{\\small\\color{{rubGray}} {meta_esc}}}\\\\[3pt]\n' if meta_esc else '')
            + r'{\color{rubTeal}\rule{\linewidth}{1.4pt}}' '\n'
            r'\end{center}' '\n'
            r'\vspace{4pt}' '\n'
            + '\n'.join(body_lines) + '\n'
            r'\end{document}'
        )

        pdf_bytes, _ = compila_pdf(latex)
        return pdf_bytes
    except Exception as e:
        logger.warning("_rubrica_to_pdf failed: %s", e)
        return None


def _vf():
    return {"latex": "", "pdf": None, "preview": False,
            "docx": None, "pdf_ts": None, "docx_ts": None, "latex_originale": ""}


# _render_back_button → moved to ui_helpers.py


# Parole chiave che indicano che l'utente sta chiedendo una modifica ai punteggi.
# In quel caso il prompt AI viene bloccato e viene mostrato un suggerimento
# a usare il pannello Ricalibra Punteggi.
_SCORE_KEYWORDS = {
    'pt', 'punt', 'punti', 'punteggio', 'punteggi', 'punto',
    'voto', 'voti', 'score', 'valut', 'peso', 'perc', '%',
    '5 pt', '10 pt', '15 pt', '20 pt', '25 pt', '30 pt',
}




# ── Post-processing LaTeX unico ────────────────────────────────────────────────

def _postprocessa_latex(latex: str, mostra_punteggi: bool, punti_totali: int,
                        riscala_totale: bool = False, punti_custom: list | None = None,
                        con_griglia: bool = False) -> str:
    """
    Post-processing deterministico unico (stringa → stringa) per ogni modifica:
    sistema gli ambienti, le spaziature e i grafici, toglie i punti dai titoli e, se
    riscala_totale, riporta la somma dei punti a punti_totali (o ai punti_custom per
    esercizio). con_griglia inietta la tabella dei punteggi (chi aggiunge
    \\end{document} dopo passa False e la inietta da sé).
    """
    latex = normalizza_sottopunti_inline(latex)   # "a) … b) …" nel paragrafo → elenco
    latex = fix_items_environment(latex)
    latex = rifinisci_scelta_multipla_e_vf(latex)
    latex = migliora_spaziatura_sottopunti(latex)
    latex = aggiungi_spaziatura_grafici_tabelle(latex)
    latex = limita_altezza_grafici(latex)
    latex = rimuovi_vspace_corpo(latex)
    latex = rimuovi_punti_subsection(latex)
    # Il totale deve essere SEMPRE punti_totali: se dopo una modifica non lo è
    # (es. 90 invece di 100) si ridistribuisce, come fa la generazione iniziale.
    if mostra_punteggi and (riscala_totale or conta_punti_latex(latex) != punti_totali):
        latex = prepara_esercizi_aperti(latex, punti_totali)
        if punti_custom:
            latex = riscala_punti_custom(latex, punti_custom)
        else:
            latex = riscala_punti(latex, punti_totali)
    if con_griglia:
        latex = inietta_griglia(latex, punti_totali)
    return latex


# ── On-demand variant generation ───────────────────────────────────────────────

def _genera_variante(tipo: str, model_id: str, gp: dict, vA: dict) -> dict:
    model_v = crea_modello(model_id)
    mostra_punteggi = gp.get("mostra_punteggi", True)
    punti_totali    = gp.get("punti_totali", 100)
    con_griglia     = gp.get("con_griglia", False)
    materia         = gp.get("materia", "")
    perc_ridotta    = gp.get("perc_ridotta", 20)
    argomento       = gp.get("argomento", "")

    latex_a    = vA.get("latex", "")
    corpo_a    = extract_corpo(latex_a)
    preamb_a   = extract_preambolo(latex_a)

    def _post(corpo: str) -> str:
        # La griglia viene iniettata da _compile, dopo \end{document}.
        return _postprocessa_latex(corpo, mostra_punteggi, punti_totali, riscala_totale=True)

    def _compile(latex: str):
        if "\\end{document}" not in latex:
            latex += "\n\\end{document}"
        if con_griglia:
            latex = inietta_griglia(latex, punti_totali)
        pdf, _, latex = compila_pdf_sicuro(latex)
        return latex, pdf

    if tipo == "B":
        try:
            resp   = model_v.per("variante").generate_content(prompt_versione_b(corpo_a))
        except Exception as e:
            raise RuntimeError(f"Variante B: {e}") from e
        corpo  = pulisci_corpo_latex(resp.text.replace("```latex","").replace("```","").strip())
        corpo  = _post(corpo)
        preamb = preamb_a.replace("Versione A", "Versione B")
        if "Versione B" not in preamb:
            preamb = re.sub(r"(Verifica[^\\]*?)(\\\\)", r"\1 — Versione B\2", preamb, count=1)
        latex, pdf = _compile(preamb + "\n" + corpo)
        return {**_vf(), "latex": latex, "pdf": pdf, "preview": bool(pdf),
                "latex_originale": latex}

    if tipo == "R":
        # La riduzione è leggera (al massimo il 20% dei sottopunti): si calcola il tetto qui e lo
        # si fa rispettare, perché l'AI da sola tendeva a tagliare metà della verifica.
        corpo_sa = rimuovi_griglia(corpo_a)
        n_sotto  = len(re.findall(r"\\item\b", corpo_sa))
        n_max    = n_sotto * perc_ridotta // 100

        def _chiedi(extra: str = "") -> str:
            r = model_v.per("variante").generate_content(
                prompt_versione_ridotta(corpo_sa, materia, perc_ridotta, mostra_punteggi,
                                        punti_totali, max_da_togliere=n_max,
                                        totale_sottopunti=n_sotto) + extra)
            return pulisci_corpo_latex(r.text.replace("```latex", "").replace("```", "").strip())

        try:
            corpo = _chiedi()
            tolti = n_sotto - len(re.findall(r"\\item\b", corpo))
            # Ha tagliato troppo: fino a due nuovi tentativi, sempre più espliciti; se nessuno
            # rispetta il tetto si tiene quello che ha tolto meno sottopunti.
            for _tent in range(2):
                if tolti <= n_max:
                    break
                _nuovo = _chiedi(
                    f"\n\nATTENZIONE: nel tentativo precedente hai eliminato {tolti} sottopunti, "
                    f"ma il massimo consentito è {n_max}. Rimetti i sottopunti più semplici "
                    f"finché non ne togli al massimo {n_max}. Conserva TUTTI gli esercizi."
                )
                _tolti_nuovo = n_sotto - len(re.findall(r"\\item\b", _nuovo))
                if _tolti_nuovo < tolti:
                    corpo, tolti = _nuovo, _tolti_nuovo
        except Exception as e:
            raise RuntimeError(f"Verifica ridotta: {e}") from e
        corpo = rimuovi_griglia(corpo)
        corpo = _post(corpo)
        latex, pdf = _compile(preamb_a + "\n" + corpo)
        return {**_vf(), "latex": latex, "pdf": pdf, "preview": bool(pdf),
                "latex_originale": latex}

    if tipo == "S":
        try:
            resp     = model_v.per("soluzioni").generate_content(prompt_soluzioni(corpo_a, materia))
        except Exception as e:
            raise RuntimeError(f"Soluzioni: {e}") from e
        testo    = resp.text.strip()
        titolo_s = "Soluzioni — " + materia + ": " + argomento
        latex_s  = (
            "\\documentclass[12pt,a4paper]{article}\n"
            "\\usepackage[utf8]{inputenc}\n"
            "\\usepackage[italian]{babel}\n"
            "\\usepackage{amsmath,amsfonts,amssymb,geometry}\n"
            "\\usepackage{fancyhdr}\n"
            "\\usepackage{lastpage}\n"
            "\\usepackage{xcolor}\n"
            "\\usepackage{tcolorbox}\n"
            "\\tcbuselibrary{skins,breakable}\n"
            "\\geometry{margin=2.5cm,top=3cm,bottom=3cm}\n"
            "\\pagestyle{fancy}\n"
            "\\fancyhf{}\n"
            "\\renewcommand{\\headrulewidth}{0pt}\n"
            "\\renewcommand{\\footrulewidth}{0pt}\n"
            "\\fancyhead[C]{{\\color{red!70!black}\\textbf{\\large SOLUZIONI - DOCUMENTO RISERVATO}}}\n"
            "\\fancyfoot[C]{{\\tiny \\textit{Documento confidenziale - Vietata la distribuzione agli studenti}} \\quad {\\small Pagina \\thepage}}\n"
            "\\definecolor{solcolor}{RGB}{220,38,38}\n"
            "\\setlength{\\parindent}{0pt}\n"
            "\\setlength{\\parskip}{0.8em plus 0.3em minus 0.2em}\n"
            "\\begin{document}\n"
            "\\begin{center}\n"
            "  {\\color{solcolor}\\rule{\\textwidth}{2pt}} \\\\[0.3cm]\n"
            "  {\\color{solcolor}\\textbf{\\LARGE " + titolo_s + "}} \\\\[0.2cm]\n"
            "  {\\large \\textbf{\\textit{Documento Riservato al Docente}}} \\\\[0.1cm]\n"
            "  {\\small \\textit{Vietata la distribuzione agli studenti}} \\\\[0.4cm]\n"
            "  {\\color{solcolor}\\rule{\\textwidth}{1pt}} \\\\[1cm]\n"
            "\\end{center}\n"
            + testo + "\n\\end{document}"
        )
        pdf_s, _ = compila_pdf(latex_s)
        return {"latex": latex_s, "pdf": pdf_s, "testo": testo}

    return {}


# ── Prompt costruzione esercizi ────────────────────────────────────────────────

def _build_prompt_esercizi(esercizi_custom, num_totale, punti_totali, mostra_punteggi):
    n_liberi = max(0, num_totale - len(esercizi_custom))
    righe = [
        f"STRUTTURA ESERCIZI — REGOLA ASSOLUTA:",
        f"Genera ESATTAMENTE {num_totale} esercizi.",
        f"Ogni esercizio è \\subsection*{{Esercizio N: Titolo}}.",
    ]
    immagini = []
    if mostra_punteggi and num_totale > 0:
        pts_b = punti_totali // num_totale
        resto = punti_totali - pts_b * num_totale
        pts   = [pts_b] * num_totale
        if resto: pts[0] += resto
        righe.append(
            f"DISTRIBUZIONE PUNTI — VINCOLO TASSATIVO:\n"
            f"Il punteggio totale della verifica DEVE essere ESATTAMENTE {punti_totali} pt.\n"
            f"REGOLA FONDAMENTALE: NON scrivere MAI il punteggio totale nell'intestazione\n"
            f"dell'esercizio (es. NO '(20pt)' dopo 'Esercizio 1: ...').\n"
            f"Assegna i punti SOLO ai singoli \\item o sottopunti (a), b), c) ecc.) in modo che\n"
            f"la somma sia ESATTAMENTE {punti_totali} pt. Non aggiungere, non togliere nemmeno 1 pt.\n"
            f"Indicazione di partenza (adattala liberamente ma rispetta il totale):"
        )
        for i in range(num_totale):
            righe.append(f"  - Esercizio {i+1}: circa {pts[i]} pt")
        righe.append(
            f"VERIFICA OBBLIGATORIA PRIMA DI RISPONDERE: somma tutti i (X pt) scritti "
            f"nel tuo output. Se la somma ≠ {punti_totali} pt, correggi i punti."
        )

    if not esercizi_custom:
        righe.append(
            f"PRIMO ESERCIZIO: 'Saperi Essenziali' — concetti base, NO simbolo (*)."
            f" Gli esercizi 2–{num_totale} approfondiscono."
        )
    righe.append(f"DETTAGLIO ({num_totale} totali):")
    for i, ex in enumerate(esercizi_custom, 1):
        tipo, desc = ex.get("tipo","Aperto"), ex.get("descrizione","").strip()
        riga = f"- Esercizio {i} [{tipo}]" + (f": {desc}" if desc else "")
        if ex.get("immagine"):
            riga += f" — usa immagine allegata"
            immagini.append({"idx": i, "data": ex["immagine"].getvalue(),
                             "mime_type": ex["immagine"].type})
        if tipo == "Scelta multipla":
            riga += " — \\begin{enumerate}[a)] \\item ... \\end{enumerate}"
        elif tipo == "Vero/Falso":
            riga += " — $\\square$ V $\\quad\\square$ F per ogni affermazione"
        elif tipo == "Completamento":
            riga += " — \\underline{\\hspace{3cm}} per gli spazi"
        righe.append(riga)
    if n_liberi > 0:
        s = len(esercizi_custom) + 1
        righe.append(f"- Esercizi {s}–{num_totale}: genera tu {n_liberi} esercizi coerenti.")
    return "\n".join(righe), immagini


# ═══════════════════════════════════════════════════════════════════════════════
#  SESSION STATE INIT
# ═══════════════════════════════════════════════════════════════════════════════

if "stage"             not in st.session_state: st.session_state.stage = STAGE_INPUT
if "verifiche"         not in st.session_state:
    st.session_state.verifiche = {
        "A": _vf(), "B": _vf(), "R": _vf(), "RB": _vf(),
        "S": {"latex": None, "testo": None, "pdf": None},
        "SC": {"latex": None, "pdf": None, "n": 0, "avvisi": []},
    }
if "review_preamble"   not in st.session_state: st.session_state.review_preamble = ""
if "review_blocks"     not in st.session_state: st.session_state.review_blocks = []
if "review_sel_idx"    not in st.session_state: st.session_state.review_sel_idx = 0
if "gen_params"        not in st.session_state: st.session_state.gen_params = {}
if "preview_images"    not in st.session_state: st.session_state.preview_images = []
if "preview_page"      not in st.session_state: st.session_state.preview_page = 0
if "last_preview_ts"   not in st.session_state: st.session_state.last_preview_ts = 0
if "esercizi_custom"   not in st.session_state: st.session_state.esercizi_custom = []
if "last_materia"      not in st.session_state: st.session_state.last_materia = None
if "last_argomento"    not in st.session_state: st.session_state.last_argomento = None
if "_storico_refresh"  not in st.session_state: st.session_state._storico_refresh = 0
if "_preferiti"        not in st.session_state: st.session_state._preferiti = set()
if "_storico_page"     not in st.session_state: st.session_state._storico_page = 1
if "gen_time_sec"      not in st.session_state: st.session_state.gen_time_sec = None
# ── Idea #19: Rubrica valutazione ────────────────────────────────────────────
if "rubrica_testo"     not in st.session_state: st.session_state.rubrica_testo = None
if "_rubrica_gen"      not in st.session_state: st.session_state._rubrica_gen = False
if "_rubrica_pdf"      not in st.session_state: st.session_state["_rubrica_pdf"] = None
if "_rubrica_docx"     not in st.session_state: st.session_state["_rubrica_docx"] = None
if "file_ispirazione"  not in st.session_state: st.session_state.file_ispirazione = None
# Analisi documento caricato
if "analisi_doc"          not in st.session_state: st.session_state.analisi_doc = None
# Lista di analisi accumulate da più file: [{"file_name","file_hash","analisi","file_mode","confirmed"}, ...]
if "analisi_docs_list"    not in st.session_state: st.session_state.analisi_docs_list = []
# Stato info consolidate ricavate da tutti i file
if "info_consolidate"     not in st.session_state: st.session_state.info_consolidate = {}
# Istruzioni per file (key = file_hash → testo istruzione)
if "istruzioni_per_file"  not in st.session_state: st.session_state.istruzioni_per_file = {}
# Percorso utente: None (home) | "B" (form di creazione)
if "input_percorso"       not in st.session_state: st.session_state.input_percorso = None
# Modalità uso file scelta dall'utente dopo l'analisi
if "file_mode"            not in st.session_state: st.session_state.file_mode = None
# Preferenze docente (caricate da Supabase)
if "_docente_prefs"       not in st.session_state: st.session_state._docente_prefs = {}
# ── Idea #1: Preferenze silenti (materia, scuola, num_esercizi, punteggi) ────
if "_user_defaults"       not in st.session_state: st.session_state._user_defaults = None
if "_user_defaults_loaded" not in st.session_state: st.session_state._user_defaults_loaded = False
# ── Idea #5: Condivisione con dipartimento ──────────────────────────────────
if "_share_code"          not in st.session_state: st.session_state._share_code = None
if "_share_generating"    not in st.session_state: st.session_state._share_generating = False
# ── Idea #3: Quick regen state ──────────────────────────────────────────────
if "_quick_regen_idx"     not in st.session_state: st.session_state._quick_regen_idx = None
if "_facsimile_mode"        not in st.session_state: st.session_state["_facsimile_mode"]        = False
if "_fac_dialog_data"      not in st.session_state: st.session_state["_fac_dialog_data"]      = {}
if "_fac_confirmed"        not in st.session_state: st.session_state["_fac_confirmed"]        = False
# File di materiale caricato (analizzato solo quando si preme "Crea verifica")
if "_file_materiale"       not in st.session_state: st.session_state["_file_materiale"]       = None
if "_up_ciclo"             not in st.session_state: st.session_state["_up_ciclo"]             = 0
if "_pb_argomento_source"    not in st.session_state: st.session_state["_pb_argomento_source"] = None
if "_pb_argomento_manual_val" not in st.session_state: st.session_state["_pb_argomento_manual_val"] = ""

# ── CONTATORI E GESTIONE ABBONAMENTI ────────────────────────────────────────
_is_admin       = st.session_state.utente.email in ADMIN_EMAILS if st.session_state.utente else False
st.session_state["_admin_diagnostica"] = _is_admin   # gli errori mostrano il dettaglio tecnico solo all'admin
_verifiche_mese = _get_verifiche_mese(st.session_state.utente.id) if st.session_state.utente else 0   # None se non riesce


@st.cache_data(ttl=60, show_spinner=False)
def _abbonamento_utente(user_id: str) -> dict:
    """Abbonamento dell'utente, in cache per un minuto (non si rilegge a ogni clic)."""
    riconvalida_se_serve(supabase_admin, user_id)     # licenza Lemon Squeezy: ricontrollo ogni 24 ore
    return get_subscription_manager(supabase_admin).get_user_subscription(user_id)


# Piano, tetto e funzioni dell'utente: un'unica fonte (subscription_management.calcola_entitlements).
# Se l'abbonamento non si legge si resta Free (mai Pro per un guasto); se il conteggio non si legge
# per chi ha un tetto la creazione è bloccata con un messaggio «riprova», non con «limite raggiunto».
def _prima_verifica_id(user_id: str):
    """
    (ok, id): id della PRIMA verifica mai creata dall'utente (anche eliminata), None se non ne ha.
    ok=False se non si riesce a leggere: in quel caso niente assaggio (mai Pro per un guasto).
    Una volta trovata la si ricorda nella sessione.
    """
    _k = "_prima_verifica"
    _c = st.session_state.get(_k)
    if _c and _c[0] == user_id and _c[1] is not None:
        return True, _c[1]
    try:
        res = supabase_admin.table("verifiche_storico").select("id")            .eq("user_id", user_id).order("created_at").limit(1).execute()
        _id = (res.data or [{}])[0].get("id") if res.data else None
        st.session_state[_k] = (user_id, _id)
        return True, _id
    except Exception as e:
        logger.warning("_prima_verifica_id failed for %s: %s", user_id, e)
        return False, None


def _assaggio_attivo() -> bool:
    """True se la verifica su cui lavora l'utente è la sua prima in assoluto (tutto il Pro, una volta sola)."""
    if not MONETIZZAZIONE_ATTIVA or _is_admin or not st.session_state.utente:
        return False
    ok, prima = _prima_verifica_id(st.session_state.utente.id)
    if not ok:
        return False
    if prima is None:
        return True                         # non ha ancora creato nulla: quella che sta per creare è la prima
    return str(st.session_state.get("_storico_id")) == str(prima)


SIM_NUOVO = "Utente nuovo (prima verifica)"
SIM_FREE = "Utente Free (dopo la prima)"
SIM_PRO = "Utente Pro"
# Solo l'admin: «Strumenti admin → Vedi l'app come» mostra l'app come la vedrebbe un altro utente
_SIM = st.session_state.get("sb_simula_piano") if _is_admin else None
if _SIM in (SIM_NUOVO, SIM_FREE, SIM_PRO):
    _ASSAGGIO = (_SIM == SIM_NUOVO)
    _abb_sim = {"plan_id": "pro", "current_period_end": None} if _SIM == SIM_PRO else None
    ENT = calcola_entitlements(_abb_sim, _verifiche_mese, False, _ASSAGGIO)
else:
    _SIM = None
    _ASSAGGIO = _assaggio_attivo()
    try:
        ENT = calcola_entitlements(_abbonamento_utente(st.session_state.utente.id), _verifiche_mese, _is_admin, _ASSAGGIO)
    except Exception as e:
        logger.error(f"Errore caricamento abbonamento: {e}")
        ENT = calcola_entitlements(None, _verifiche_mese, _is_admin, _ASSAGGIO)

# l'assaggio sceglie il modello come il Pro; l'admin si riconosce da _is_admin
st.session_state.piano_utente = "pro" if ENT.assaggio else (ENT.piano if ENT.piano != "admin" else "free")
_limite = ENT.limite_raggiunto
_blocco_conteggio = ENT.errore_conteggio
_illimitato = ENT.illimitato
_restanti = ENT.restanti
_TETTO_MENSILE = int(ENT.tetto_mensile) if not ENT.illimitato else LIMITE_MENSILE


def _registra_evento(tipo: str, modello: str | None = None, verifica_id=None, costo_usd: float | None = None) -> None:
    """Scrive un evento d'uso in `usage_events` (tetti, costi, metriche). Mai bloccante: un errore si ignora."""
    if not st.session_state.utente or supabase_admin is None:
        return
    try:
        supabase_admin.table("usage_events").insert({
            "user_id": st.session_state.utente.id, "tipo": tipo, "modello": modello,
            "costo_usd": costo_usd, "verifica_id": verifica_id,
        }).execute()
    except Exception as e:
        logger.warning("usage_events non scritto (%s): %s", tipo, e)


def _vai_a_upgrade(funzione: str | None = None) -> None:
    """Porta alla pagina «Passa a Pro» ricordando da dove si arriva."""
    st.session_state["_upgrade_da"] = st.session_state.stage
    st.session_state["_upgrade_funzione"] = funzione
    _registra_evento("paywall:" + (funzione or "pagina"), verifica_id=st.session_state.get("_storico_id"))
    st.session_state.stage = STAGE_UPGRADE
    st.rerun()


_CSS_BANNER_PIANO = """
<style>
/* Striscia blu per chi non ha Pro: contenitore con chiave (classe st-key-banner_piano_*, stabile tra le versioni) */
html body .stApp [class*="st-key-banner_piano_"] {
  background:#2563EB !important; border-radius:10px; padding:.55rem .85rem .65rem !important;
  margin:.2rem 0 .6rem; gap:.3rem !important;
}
/* Streamlit toglie 1rem in fondo al markdown: il riempimento lo ripristina */
html body .stApp [class*="st-key-banner_piano_"] .bp-wrap { padding-bottom:1rem; }
html body .stApp [class*="st-key-banner_piano_"] .bp-t {
  font-family:'DM Sans',sans-serif; font-weight:700; font-size:.9rem; line-height:1.3; color:#fff;
}
html body .stApp [class*="st-key-banner_piano_"] .bp-s {
  font-family:'DM Sans',sans-serif; font-size:.8rem; line-height:1.4; color:rgba(255,255,255,.92); margin-top:.15rem;
}
html body .stApp [class*="st-key-banner_piano_"] button {
  background:#fff !important; border:0 !important; border-radius:8px !important; min-height:0 !important;
  padding:.25rem .8rem !important; width:auto !important;
}
html body .stApp [class*="st-key-banner_piano_"] button p,
html body .stApp [class*="st-key-banner_piano_"] button span {
  color:#1D4ED8 !important; font-weight:700 !important; font-size:.82rem !important; margin:0 !important; line-height:1.2 !important;
}
html body .stApp [class*="st-key-banner_piano_"] button:hover { background:#EFF6FF !important; }
</style>
"""


_PASSI_GUIDA = {
    "input": [
        {"id": "arg", "titolo": "Scrivi l'argomento",
         "testo": "Nel riquadro scrivi di cosa parla la verifica e, se vuoi, cosa includere o evitare.",
         "target": [".st-key-argomento_area_b [data-baseweb=\"textarea\"]", ".st-key-argomento_area_b textarea"]},
        {"id": "opz", "titolo": "Prova anche il logo e un tuo file",
         "testo": "Apri «Altre opzioni»: puoi mettere il logo della tua scuola e partire da un tuo file (appunti o una verifica da rifare). "
                  "Sono funzioni Pro, gratis solo in questa prima verifica.",
         "target": ['[data-testid="stExpander"]:has(.g-altre)']},
        {"id": "crea", "titolo": "Crea la verifica",
         "testo": "Premi «Crea verifica»: in circa un minuto è pronta.",
         "target": [".st-key-genera_btn_b button"]},
    ],
    "final": [
        {"id": "mod", "titolo": "Controlla e modifica gli esercizi",
         "testo": "Leggi la verifica: puoi cambiare un esercizio, aggiungerne o toglierne, e scaricare il PDF.",
         "target": None},
        {"id": "kit", "titolo": "Crea tutto il kit",
         "testo": "Con «Prepara tutto il kit» ottieni Fila B, versione BES/DSA, soluzioni e scheda di allenamento. "
                  "Sono gratis solo per questa verifica.",
         "target": [".st-key-kit_tutto button"]},
        {"id": "zip", "titolo": "Scarica tutto in un solo file",
         "testo": "«Scarica tutto (ZIP)» raccoglie la verifica e tutte le versioni create. È un'occasione unica: "
                  "dalla prossima verifica Fila B, BES/DSA, soluzioni e scheda sono solo con Pro.",
         "target": [".st-key-dl_kit_zip button"]},
    ],
}

_CSS_GUIDA = """
<style>
@keyframes gpulse { 0%,100% { box-shadow:0 0 0 0 rgba(245,158,11,0); } 50% { box-shadow:0 0 0 7px rgba(245,158,11,.6); } }
/* guida: testo più leggibile e pulsanti discreti, bianchi sul blu */
html body .stApp [class*="st-key-banner_piano_"] .g-t { font-family:'DM Sans',sans-serif; font-weight:800; font-size:1rem; line-height:1.3; color:#fff; }
html body .stApp [class*="st-key-banner_piano_"] .g-s { font-family:'DM Sans',sans-serif; font-size:.88rem; line-height:1.5; color:#fff; margin-top:.15rem; }
html body .stApp [class*="st-key-banner_piano_"] .g-k { font-family:'DM Sans',sans-serif; font-size:.78rem; color:rgba(255,255,255,.85); }
html body .stApp [class*="st-key-guida_"] { width:auto !important; flex:0 0 auto !important; }
html body .stApp [class*="st-key-guida_"] button {
  background:rgba(255,255,255,.14) !important; border:1px solid rgba(255,255,255,.55) !important; border-radius:999px !important;
  min-height:0 !important; height:auto !important; padding:.18rem .75rem !important; width:auto !important; box-shadow:none !important;
}
html body .stApp [class*="st-key-guida_"] button p,
html body .stApp [class*="st-key-guida_"] button span { color:#fff !important; font-weight:700 !important; font-size:.8rem !important; margin:0 !important; line-height:1.2 !important; }
html body .stApp [class*="st-key-guida_"] button:hover:not(:disabled) { background:rgba(255,255,255,.28) !important; }
html body .stApp [class*="st-key-guida_"] button:disabled { opacity:.4 !important; }
html body .stApp [class*="st-key-guida_nascondi"] button { background:transparent !important; border-color:transparent !important; }
html body .stApp [class*="st-key-guida_nascondi"] button p,
html body .stApp [class*="st-key-guida_nascondi"] button span { font-weight:500 !important; text-decoration:underline; opacity:.85; }
</style>
"""


def _html_separatore() -> str:
    """Linea sottile tra le sezioni di «Altre opzioni»."""
    return (f'<div style="height:1px;background:{T["border2"]};opacity:.9;margin:1.2rem 0 .7rem;"></div>')


def _guida_vai(dove: str, i: int) -> None:
    st.session_state["_guida_manuale"] = {"dove": dove, "i": i}


def _guida_nascondi() -> None:
    st.session_state["_guida_nascosta"] = True


def _stato_guida(dove: str):
    """(passo automatico, stati «fatto» per passo) secondo quello che l'utente ha già fatto."""
    if dove == "input":
        scritto = bool((st.session_state.get("argomento_area_b") or "").strip())
        logo = bool(_logo_scuola())
        file_ = bool(st.session_state.get("_file_materiale"))
        fatti = [scritto, logo or file_, False]
        auto = 0 if not scritto else 1
    else:
        v = st.session_state.get("verifiche") or {}
        extra = [bool((v.get(k) or {}).get("pdf") or (v.get(k) or {}).get("latex")) for k in ("B", "S", "R")]
        extra.append(bool((v.get("SC") or {}).get("pdf")))
        fatti = [False, sum(extra) >= 2, sum(extra) >= 4]
        auto = 2 if sum(extra) >= 3 else (1 if any(extra) else 0)
    return auto, fatti


def _guida_benvenuto(dove: str, slot) -> None:
    """
    Guida a passi (a «slider») per chi crea la prima verifica, con tutte le funzioni Pro sbloccate: scrivere l'argomento,
    provare logo e file, creare, modificare, creare il kit e scaricare lo ZIP. Il passo avanza da solo secondo quello che
    l'utente fa; con ‹ › si può scorrere a mano. L'elemento da usare nel passo attuale pulsa in giallo.
    Tutto lo stile e l'evidenziazione stanno nello stesso blocco di testo della striscia: nessun elemento in più che allunghi la pagina.
    """
    passi = _PASSI_GUIDA[dove]
    auto, fatti = _stato_guida(dove)
    man = st.session_state.get("_guida_manuale")
    i = man["i"] if (man and man.get("dove") == dove and 0 <= man["i"] < len(passi)) else auto
    p = passi[i]
    n_tot = len(_PASSI_GUIDA["input"]) + len(_PASSI_GUIDA["final"])
    n_corr = i + 1 + (len(_PASSI_GUIDA["input"]) if dove == "final" else 0)
    puntini = "".join(
        f'<span style="display:inline-block;width:{18 if k == i else 7}px;height:7px;border-radius:4px;margin-right:4px;'
        f'background:rgba(255,255,255,{1 if k == i else .4});"></span>' for k in range(len(passi)))
    spunta = " ✓" if fatti[i] else ""
    titolo = ("🎁 Regalo di benvenuto: la prima verifica è tutta Pro" if dove == "input"
              else "🎁 Regalo di benvenuto: tutto il Pro su questa verifica")
    evidenzia = ""
    if p["target"]:
        regole = ", ".join(f"html body .stApp {t}" for t in p["target"])
        evidenzia = f"<style>{regole} {{animation:gpulse 1.5s ease-in-out infinite;border-radius:10px;}}</style>"
    with slot.container(key=f"banner_piano_{dove}"):
        st.markdown(
            _CSS_BANNER_PIANO + _CSS_GUIDA + evidenzia +
            f'<div class="bp-wrap" style="padding-bottom:.2rem;">'
            f'<div class="g-t">{titolo}</div>'
            f'<div class="g-k" style="margin-top:.3rem;">Passo {n_corr} di {n_tot} &nbsp;{puntini}</div>'
            f'<div class="g-t" style="margin-top:.55rem;font-size:1.05rem;">{p["titolo"]}{spunta}</div>'
            f'<div class="g-s">{p["testo"]}</div></div>',
            unsafe_allow_html=True,
        )
        c1, c2, c3, _vuoto = st.columns([1.1, 1.1, 1.9, 2], gap="small")
        c1.button("‹ Indietro", key=f"guida_prec_{dove}", disabled=(i == 0), on_click=_guida_vai, args=(dove, i - 1))
        c2.button("Avanti ›", key=f"guida_succ_{dove}", disabled=(i == len(passi) - 1), on_click=_guida_vai, args=(dove, i + 1))
        c3.button("Nascondi la guida", key=f"guida_nascondi_{dove}", on_click=_guida_nascondi)


def _banner_piano(dove: str) -> None:
    """
    Striscia blu in cima alla pagina per chi non ha Pro (stesso stile per tutti):
    prima verifica = regalo di benvenuto (cosa può fare e cosa cambia dopo);
    piano Free = invito a passare a Pro, con il pulsante dentro la striscia. dove = "input" | "final".
    Sta in un segnaposto (st.empty) che si svuota quando il banner non serve: così non resta mai a schermo.
    """
    _slot = st.empty()
    if not MONETIZZAZIONE_ATTIVA or (_is_admin and not _SIM) or ENT.piano != "free":
        _slot.empty()
        return
    if ENT.assaggio and not st.session_state.get("_guida_nascosta"):
        _guida_benvenuto(dove, _slot)
        return
    if ENT.assaggio:
        if dove == "input":
            _titolo = "🎁 Regalo di benvenuto: la prima verifica è tutta Pro"
            _testo = ("Usi il modello migliore e puoi creare tutto: Fila B, BES/DSA, soluzioni, griglia, scheda, logo. "
                      "Dalla seconda: modello più veloce (può sbagliare) e funzioni extra solo con Pro.")
        else:
            _titolo = "🎁 Regalo di benvenuto: hai tutto il Pro su questa verifica"
            _testo = ("Crea ora Fila B, BES/DSA, soluzioni, griglia e scheda. "
                      "Dalla prossima verifica restano solo con Pro.")
    else:
        _titolo = "Passa al piano Pro"
        _testo = ("Esercizi scritti dal modello AI più accurato e, per ogni verifica, il kit completo per la classe: "
                  "Fila B, versione BES/DSA, soluzioni, griglia di valutazione, scheda di allenamento e logo della scuola."
                  if dove == "input" else
                  "Con Pro questa verifica può avere anche Fila B, versione BES/DSA, soluzioni, griglia, "
                  "scheda di allenamento, e gli esercizi sono scritti dal modello AI più accurato.")
    st.markdown(_CSS_BANNER_PIANO, unsafe_allow_html=True)
    with _slot.container(key=f"banner_piano_{dove}"):
        st.markdown(
            f'<div class="bp-wrap"><div class="bp-t">{_titolo}</div>'
            f'<div class="bp-s">{_testo}</div></div>',
            unsafe_allow_html=True,
        )
        if not ENT.assaggio:
            if st.button("Scopri Pro", key=f"banner_pro_{dove}", icon=":material/workspace_premium:"):
                _vai_a_upgrade(None)


def _pro_bloccato(funzione: str) -> bool:
    """True se la funzione richiede Pro e l'utente non ce l'ha (sempre False a monetizzazione spenta)."""
    return not ENT.puo(funzione)


def _pulsante_pro(funzione: str, key: str, testo: str = "Con Pro") -> None:
    """Al posto dell'azione di una funzione Pro: un pulsante che porta alla pagina di confronto."""
    if st.button(f"🔒 {testo}", key=key, use_container_width=True, type="secondary",
                 help=f"Per avere {ETICHETTE_FUNZIONI.get(funzione, 'questa funzione')} serve il piano Pro."):
        _vai_a_upgrade(funzione)

# ── CSS + FEEDBACK ────────────────────────────────────────────
st.markdown(get_css(T), unsafe_allow_html=True)

# ── JS fix expander open header ─────────────────────────────────
# st.markdown non esegue <script>. components.html usa un iframe sandbox con
# allow-same-origin che permette window.parent.document → accesso al DOM reale.
_theme_is_light = _is_light_color(T.get("bg", "#000000"))
_exp_fix_bg   = T.get("accent_light", "#E0F2FE")
_exp_fix_fg   = T.get("accent", "#0D9488")
_exp_fix_bdr  = T.get("accent", "#0D9488") + "44"
_btn_fix_bg   = T.get("card", T.get("bg2", "#FFFFFF"))
_btn_fix_fg   = T.get("text", "#0F1117")
_btn_fix_bdr  = T.get("border2", "#CDD1D9")
_is_lt        = "1" if _theme_is_light else ""
components.html(
    f'<script>'
    f'(function(){{'
    f'var p=window.parent,d=p&&p.document;'
    f'if(!d)return;'
    f'var isLight="{_is_lt}";'
    f'var ebg="{_exp_fix_bg}",efg="{_exp_fix_fg}",ebd="1px solid {_exp_fix_bdr}";'
    f'var btnBg="{_btn_fix_bg}",btnFg="{_btn_fix_fg}",btnBd="1.5px solid {_btn_fix_bdr}";'
    f'var ESEL=\'[data-testid="stExpander"] details[open]>summary,[data-testid="stExpander"][open]>summary\';'
    f'var BSEL=\'[data-testid="stButton"]>button,div.stButton>button\';'
    f'function fx(){{'
    f'if(isLight){{'
    # Fix ALL secondary buttons with aggressive inline styles
    f'var allSecBtns = d.querySelectorAll('
    f'  \'button[data-testid="stBaseButton-secondary"],'
    f'  \'button[kind="secondary"],'
    f'  \'div.stButton > button:not([kind="primary"]):not([data-testid*="primary"]),'
    f'  \'[data-testid="stButton"] > button:not([data-testid*="primary"])'
    f');'
    f'allSecBtns.forEach(function(e){{'
    f'  if(e.closest(\'[data-testid="stSidebar"]\'))return;'
    f'  var dt = (e.getAttribute("data-testid")||"").toLowerCase();'
    f'  var kd = (e.getAttribute("kind")||"").toLowerCase();'
    f'  if(dt.indexOf("primary")!==-1||kd==="primary")return;'
    f'  e.style.setProperty("background","{T.get("card", T["bg2"])}","important");'
    f'  e.style.setProperty("background-color","{T.get("card", T["bg2"])}","important");'
    f'  e.style.setProperty("color","{T["text"]}","important");'
    f'  e.style.setProperty("-webkit-text-fill-color","{T["text"]}","important");'
    f'  e.style.setProperty("border","1.5px solid {T["border2"]}","important");'
    f'  e.style.setProperty("border-radius","8px","important");'
    f'}});'
    f'}}'
    f'}}'
    f'try{{new MutationObserver(fx).observe(d.body,{{subtree:true,attributes:true,childList:true}});}}catch(err){{}}'
    f'fx();'
    f'}})();'
    f'</script>',
    height=0,
    scrolling=False,
)
st.markdown(
    '<a class="fab-link" href="' + FEEDBACK_FORM_URL + '" target="_blank" '
    'rel="noopener noreferrer">💬 Feedback</a>',
    unsafe_allow_html=True
)

# ── ST_YLED — init + global styles ────────────────────────────────────────────
# Personalizza bottoni primari, input e form a livello globale via st_yled.set()
if _STYLED_AVAILABLE:
    try:
        _styl.init()
        # Pulsanti primari — colore coerente con il tema
        _styl.set("button", "border_radius", "12px")
        _styl.set("button", "font_size", "0.95rem")
        # Input
        _styl.set("text_input", "border_radius", "12px")
        _styl.set("text_area",  "border_radius", "12px")
    except Exception:
        pass

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
settings   = render_sidebar(
    supabase_admin=supabase_admin, utente=st.session_state.utente,
    verifiche_mese_count=_verifiche_mese or 0, is_admin=_is_admin,
    limite_raggiunto=_limite, T=T,
    MODELLI_DISPONIBILI=MODELLI_DISPONIBILI, LIMITE_MENSILE=_TETTO_MENSILE,
    giorni_al_reset_func=_giorni_al_reset, supabase_client=supabase,
    contatto_url=FEEDBACK_FORM_URL, illimitato=_illimitato,
    THEMES=THEMES, THEME_LABELS=THEME_LABELS,
)
modello_id = settings.get("modello_id", "gemini-2.5-flash-lite")

# Se il tema è cambiato dalla sidebar, aggiorna T
if settings.get("theme_changed"):
    T = THEMES[st.session_state.theme]
    st.rerun()

# Flag per sapere se siamo sulla landing (usato da breadcrumb e header)
_on_landing = (st.session_state.stage == STAGE_INPUT)   # la creazione è anche la home

# ── HEADER UNIFICATO — visibile solo sulla landing ────────────────────────────
if _on_landing:
    st.markdown(
        '<div class="site-header">'
        '  <a class="site-header-logo" href="/" target="_self">'
        '    <span class="site-header-icon">' + APP_ICON + '</span>'
        '    <span class="site-header-name">Verific<span class="site-header-ai">AI</span></span>'
        '    <span class="site-header-beta">Beta</span>'
        '  </a>'
        '</div>',
        unsafe_allow_html=True
    )









# ═══════════════════════════════════════════════════════════════════════════════
#  PREFERENZE DOCENTE — Supabase helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _carica_docente_preferenze(user_id: str, materia: str) -> dict:
    """
    Carica le preferenze salvate per una materia specifica.
    Ritorna {} se non trovate o se si verifica un errore.
    """
    try:
        res = supabase_admin.table("docente_preferenze") \
            .select("preferenze") \
            .eq("user_id", user_id) \
            .eq("materia", materia) \
            .limit(1).execute()
        if res.data:
            return res.data[0].get("preferenze") or {}
    except Exception as e:
        logger.warning("_carica_docente_preferenze failed for %s/%s: %s", user_id, materia, e)
    return {}


def _salva_docente_preferenze(materia: str, prefs: dict) -> None:
    """
    Salva/aggiorna le preferenze del docente per una materia (upsert).
    Operazione non bloccante — i fallimenti vengono silenziosamente loggati.
    """
    from datetime import datetime, timezone
    if not st.session_state.utente:
        return
    try:
        supabase_admin.table("docente_preferenze").upsert({
            "user_id":    st.session_state.utente.id,
            "materia":    materia,
            "preferenze": prefs,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }, on_conflict="user_id,materia").execute()
        # Aggiorna cache locale
        st.session_state._docente_prefs[materia] = prefs
    except Exception as e:
        logger.warning("_salva_docente_preferenze failed for %s: %s", materia, e)



# ═══════════════════════════════════════════════════════════════════════════════
#  IDEA #1 — PREFERENZE SILENTI (salva/carica defaults form utente)
# ═══════════════════════════════════════════════════════════════════════════════

def _load_user_defaults() -> dict:
    """
    Carica le preferenze form silenti dell'utente da Supabase.
    Chiave: user_id con materia='__defaults__'.
    Restituisce {} se non trovate.
    Viene chiamata UNA volta all'avvio e cachata in session_state.
    """
    if st.session_state._user_defaults_loaded:
        return st.session_state._user_defaults or {}
    if not st.session_state.utente:
        return {}
    try:
        res = supabase_admin.table("docente_preferenze") \
            .select("preferenze") \
            .eq("user_id", st.session_state.utente.id) \
            .eq("materia", "__defaults__") \
            .limit(1).execute()
        defaults = res.data[0].get("preferenze", {}) if res.data else {}
        st.session_state._user_defaults = defaults
        st.session_state._user_defaults_loaded = True
        return defaults
    except Exception as e:
        logger.warning("_load_user_defaults failed: %s", e)
        st.session_state._user_defaults_loaded = True
        return {}


def _save_user_defaults_silent(materia: str, scuola: str,
                                num_esercizi: int, mostra_punteggi: bool,
                                punti_totali: int, durata: str | None = None) -> None:
    """
    Salva silenziosamente i defaults del form.
    Chiamata dopo ogni generazione o quando i campi cambiano.
    Non-blocking: errori ignorati.
    """
    from datetime import datetime, timezone
    if not st.session_state.utente:
        return
    defaults = {
        "materia": materia,
        "scuola": scuola,
        "num_esercizi": num_esercizi,
        "mostra_punteggi": mostra_punteggi,
        "punti_totali": punti_totali,
    }
    if durata in DURATE:
        defaults["durata"] = durata      # Breve / Standard / Lunga (stesso campo jsonb)
    # Evita write se nulla è cambiato
    cached = st.session_state._user_defaults or {}
    if cached == defaults:
        return
    try:
        supabase_admin.table("docente_preferenze").upsert({
            "user_id":    st.session_state.utente.id,
            "materia":    "__defaults__",
            "preferenze": defaults,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }, on_conflict="user_id,materia").execute()
        st.session_state._user_defaults = defaults
    except Exception as e:
        logger.warning("_save_user_defaults failed: %s", e)


# ═══════════════════════════════════════════════════════════════════════════════
#  IDEA #5 — CONDIVISIONE CON IL DIPARTIMENTO
# ═══════════════════════════════════════════════════════════════════════════════

def _generate_share_code() -> str:
    """Genera un codice breve univoco per la condivisione (6 caratteri alfanumerici)."""
    import hashlib
    seed = f"{time.time()}-{st.session_state.utente.id}-{id(st.session_state)}"
    return hashlib.sha256(seed.encode()).hexdigest()[:8].upper()


def _create_share_link(latex_a: str, materia: str, argomento: str,
                        scuola: str, num_esercizi: int) -> str | None:
    """
    Salva la verifica nella tabella shared_verifiche e restituisce il codice.
    TTL: 30 giorni. Restituisce None in caso di errore.
    """
    from datetime import datetime, timezone, timedelta
    if not st.session_state.utente or not latex_a:
        return None
    code = _generate_share_code()
    try:
        now = datetime.now(timezone.utc)
        supabase_admin.table("shared_verifiche").insert({
            "short_code":    code,
            "user_id":       st.session_state.utente.id,
            "latex_a":       latex_a,
            "materia":       materia,
            "argomento":     argomento,
            "scuola":        scuola,
            "num_esercizi":  num_esercizi,
            "created_at":    now.isoformat(),
            "expires_at":    (now + timedelta(days=30)).isoformat(),
            "view_count":    0,
            "clone_count":   0,
        }).execute()
        return code
    except Exception as e:
        logger.warning("_generate_share_code / _create_share_record failed: %s", e)
        return None


def _load_shared_verifica(code: str) -> dict | None:
    """
    Carica una verifica condivisa dal codice. Restituisce il record o None.
    Incrementa il view_count.
    """
    try:
        res = supabase_admin.table("shared_verifiche") \
            .select("*") \
            .eq("short_code", code) \
            .limit(1).execute()
        if not res.data:
            return None
        record = res.data[0]
        # Incrementa view_count
        try:
            supabase_admin.table("shared_verifiche") \
                .update({"view_count": (record.get("view_count", 0) or 0) + 1}) \
                .eq("short_code", code).execute()
        except Exception:
            pass
        return record
    except Exception:
        return None


def _increment_clone_count(code: str) -> None:
    """Incrementa il contatore cloni per una verifica condivisa."""
    try:
        res = supabase_admin.table("shared_verifiche") \
            .select("clone_count") \
            .eq("short_code", code) \
            .limit(1).execute()
        current = res.data[0].get("clone_count", 0) if res.data else 0
        supabase_admin.table("shared_verifiche") \
            .update({"clone_count": (current or 0) + 1}) \
            .eq("short_code", code).execute()
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════════════════
#  HELPERS — CREAZIONE E ANALISI FILE
# ═══════════════════════════════════════════════════════════════════════════════

def _esegui_analisi_documento(file_bytes: bytes, mime_type: str, file_name: str):
    """
    Lancia analisi AI sul file e popola st.session_state.analisi_doc.
    Chiama st.rerun() alla fine per aggiornare il dialogo.
    """
    file_hash = hash(file_bytes)
    ad = st.session_state.analisi_doc or {}
    if ad.get("file_hash") == file_hash:
        return  # già analizzato — evita ri-analisi su rerun

    # Analisi AI metadati — usa sempre Flash Lite (task leggero ed economico)
    try:
        _model_fast = crea_modello(MODEL_FAST_ID, "analisi_file")
        result = analizza_documento_caricato(
            model=_model_fast,
            file_bytes=file_bytes,
            mime_type=mime_type,
            materie_valide=MATERIE,
        )
        result["file_hash"] = file_hash
        result["file_name"] = file_name

        # ── GUARDRAIL: file non pertinente ────────────────────────────────────
        if not result.get("pertinente", True):
            # Segna il documento come non pertinente ma NON lo aggiunge alla lista.
            # Salviamo il messaggio di rifiuto in un key temporaneo per mostrarlo nell'UI.
            st.session_state["_analisi_rifiuto"] = {
                "file_name": file_name,
                "messaggio": result.get("messaggio_rifiuto")
                    or "Questo file non sembra materiale scolastico. "
                       "Carica una verifica, appunti, un capitolo del libro o una foto della lavagna.",
            }
            st.rerun()

        st.session_state.analisi_doc    = result
        st.session_state.file_mode     = result.get("modalita_uso_consigliata", "stile_e_struttura")

        # Pre-popola scuola se rilevata
        if result.get("scuola") and result["scuola"] in SCUOLE:
            st.session_state._analisi_scuola = result["scuola"]

        # Pre-popola materia preferenze Supabase
        if result.get("materia") and result["materia"] in MATERIE and st.session_state.utente:
            prefs = _carica_docente_preferenze(st.session_state.utente.id, result["materia"])
            st.session_state._docente_prefs[result["materia"]] = prefs

        # ── Aggiorna lista multi-file ─────────────────────────────────────────
        # Aggiunge alla lista se non già presente (by hash); lo marca come
        # "in attesa di conferma" (confirmed=False).
        _existing_hashes = {d["file_hash"] for d in st.session_state.analisi_docs_list}
        if file_hash not in _existing_hashes:
            st.session_state.analisi_docs_list.append({
                "file_hash":  file_hash,
                "file_name":  file_name,
                "file_bytes": file_bytes,   # ← bytes grezzi per vision AI
                "mime_type":  mime_type,    # ← mime per vision AI
                "analisi":    result,
                "file_mode":  result.get("modalita_uso_consigliata", "stile_e_struttura"),
                "confirmed":  False,   # attende conferma modalità
            })
        # Retrocompatibilità: slot singolo usato da compila_contesto_generazione
        st.session_state.analisi_doc = result
        _consolida_info()

        # Al prossimo render (prima dei widget) materia e scuola rilevate riempiono i menu
        st.session_state["_applica_analisi"] = True

        # ── Prepara toast da mostrare al prossimo render ────────────────────────
        _det_materia = result.get("materia", "")
        _det_arg     = result.get("contenuto_argomento", "")
        _det_tipo    = result.get("tipo_documento", "")
        _toast_parts = []
        if _det_materia:
            _toast_parts.append(f"**Materia:** {_det_materia}")
        if _det_arg:
            _short_arg = _det_arg[:60] + "…" if len(_det_arg) > 60 else _det_arg
            _toast_parts.append(f"**Argomento:** {_short_arg}")
        if _det_tipo and _det_tipo != "verifica":
            _toast_parts.append(f"**Tipo:** {_det_tipo.replace('_', ' ').title()}")
        st.session_state["_toast_analisi"] = " · ".join(_toast_parts) if _toast_parts else "Documento analizzato."

        st.rerun()
    except Exception as e:
        logger.error(f"Analisi documento non riuscita: {e}", exc_info=True)
        st.warning("Non sono riuscito a leggere il file. Compila i campi a mano oppure prova con un altro file.", icon="🔬")


def _consolida_info():
    """
    Ricalcola info_consolidate da tutti i file in analisi_docs_list.
    Priorità: file_mode confermato > ordine inserimento.
    Campi chiave: argomento, scuola, materia.
    """
    lista = st.session_state.analisi_docs_list
    merged: dict = {}
    for entry in lista:
        a = entry.get("analisi", {})
        # Priorità: prendi il primo valore non-vuoto trovato
        for campo in ("materia", "scuola", "contenuto_argomento",
                      "stile_desc", "tipi_domande", "ha_grafici",
                      "ha_formule", "num_esercizi_rilevati", "tipo_documento"):
            if campo not in merged or not merged[campo]:
                v = a.get(campo)
                if v:
                    merged[campo] = v
    # Scuola dalla chiave dedicata (più affidabile)
    if st.session_state.get("_analisi_scuola"):
        merged["scuola"] = st.session_state._analisi_scuola
    st.session_state.info_consolidate = merged


def _load_user_verifiche():
    """
    Carica tutte le verifiche dell'utente da Supabase
    """
    if not st.session_state.utente:
        return []

    try:
        return _elenco_verifiche(st.session_state.utente.id, st.session_state._storico_refresh)
    except Exception as e:
        _mostra_errore("Non sono riuscito a caricare le tue verifiche", e)
        return []


@st.cache_data(ttl=120, show_spinner=False)
def _elenco_verifiche(user_id: str, refresh: int) -> list:
    """Elenco leggero dello storico (senza il LaTeX, che pesa): una query ogni 2 minuti
    o appena cambia `_storico_refresh` (nuova verifica, rinomina, eliminazione)."""
    res = supabase_admin.table("verifiche_storico")\
        .select("id,argomento,materia,scuola,num_esercizi,created_at")\
        .eq("user_id", user_id)\
        .is_("deleted_at", "null")\
        .order("created_at", desc=True)\
        .execute()
    return res.data or []


@st.cache_data(ttl=300, show_spinner=False)
def _contenuto_verifica(user_id: str, verifica_id) -> dict:
    """LaTeX di una verifica dello storico (Fila A e, se salvate, Fila B e BES/DSA)."""
    res = supabase_admin.table("verifiche_storico")\
        .select("latex_a,latex_b,latex_r")\
        .eq("id", verifica_id).eq("user_id", user_id)\
        .limit(1).execute()
    return (res.data or [{}])[0]


@st.cache_data(ttl=600, max_entries=20, show_spinner=False)
def _pdf_da_latex(latex: str):
    """Compila (una volta sola per testo) il PDF di una verifica già salvata: (pdf, errore)."""
    return compila_pdf(latex)

def _latex_per_ai(latex: str) -> str:
    """LaTeX senza il logo (dati base64 e immagine): all'AI non serve e peserebbe decine di KB."""
    latex = rimuovi_logo_b64(latex or "")
    return re.sub(r"\\includegraphics\[[^\]]*\]\{logo_scuola\.png\}", "", latex)


# ── Logo della scuola (salvato per utente in docente_preferenze, materia "__logo__") ──
def _logo_scuola():
    """Logo salvato ({'b64', 'tipo', 'attivo'}) o None; si legge dal database una volta per sessione."""
    if not st.session_state.get("_logo_scuola_caricato"):
        prefs = {}
        if st.session_state.utente:
            prefs = _carica_docente_preferenze(st.session_state.utente.id, "__logo__")
        st.session_state["_logo_scuola"] = prefs if prefs.get("b64") else None
        st.session_state["_logo_scuola_caricato"] = True
    return st.session_state.get("_logo_scuola")


def _salva_logo(prefs) -> None:
    st.session_state["_logo_scuola"] = prefs or None
    st.session_state["_logo_scuola_caricato"] = True
    _salva_docente_preferenze("__logo__", prefs or {})


def _prepara_logo(dati: bytes):
    """Immagine caricata → PNG su fondo bianco, ridotto (al massimo ~110 KB), in base64. None se illeggibile."""
    try:
        from PIL import Image, ImageChops
        im = Image.open(io.BytesIO(dati))
        im.load()
        if im.mode in ("RGBA", "LA", "P"):
            im = im.convert("RGBA")
            fondo = Image.new("RGBA", im.size, (255, 255, 255, 255))
            fondo.alpha_composite(im)
            im = fondo
        im = im.convert("RGB")
        # Sfondo quasi bianco → bianco puro (toglie il riquadro grigiastro dei JPG) e via i
        # margini bianchi: così il logo si allinea al bordo e la sua altezza è quella vera.
        im = im.point(lambda v: 255 if v > 238 else v)
        riquadro = ImageChops.difference(im, Image.new("RGB", im.size, (255, 255, 255))).getbbox()
        if riquadro:
            x0, y0, x1, y1 = riquadro
            im = im.crop((max(0, x0 - 4), max(0, y0 - 4), min(im.width, x1 + 4), min(im.height, y1 + 4)))
        for larghezza in (700, 500, 350):
            r = im if im.width <= larghezza else im.resize(
                (larghezza, max(1, int(im.height * larghezza / im.width))), Image.LANCZOS)
            buf = io.BytesIO()
            r.save(buf, "PNG", optimize=True)
            if len(buf.getvalue()) <= 110_000:
                # Formato scelto dalla forma: un'immagine molto più larga che alta è un logo con il
                # nome della scuola (largo), una più quadrata è il solo simbolo (piccolo).
                tipo = "largo" if im.width / max(1, im.height) >= 3.0 else "piccolo"
                return base64.b64encode(buf.getvalue()).decode(), tipo
    except Exception as e:
        logger.warning(f"Logo non leggibile: {e}")
    return None


# Da aumentare ogni volta che cambia il layout dell'intestazione col logo (latex_utils.inserisci_logo):
# fa parte della chiave della cache, così un'anteprima vecchia non resta in memoria dopo un aggiornamento.
_LAYOUT_LOGO = 5


@st.cache_data(ttl=3600, max_entries=24, show_spinner=False)
def _anteprima_intestazione(b64: str, tipo: str, attivo: bool, materia: str, scala: float = 1.0,
                            layout: int = _LAYOUT_LOGO):
    """
    Immagine REALE dell'intestazione della verifica (logo + titolo + riga Nome/Classe): si
    compila con pdflatex la stessa intestazione che finirà nel PDF e si ritaglia la parte alta.
    Una volta sola per logo (cache). None se la compilazione non riesce: meglio nessuna
    anteprima che un'anteprima diversa dal risultato.
    """
    try:
        from PIL import Image
        from generation import _costruisci_preambolo
        pre, _ = _costruisci_preambolo(materia, "titolo della verifica", "", False)
        latex = pre + "\\end{document}\n"
        if attivo:
            latex = inserisci_logo(latex, tipo, b64, scala)
        pdf, _err = compila_pdf(latex)
        imgs, _ = pdf_to_images_bytes(pdf) if pdf else (None, None)
        if not imgs:
            return None
        im = Image.open(io.BytesIO(imgs[0])).convert("RGB")
        w, h = im.size
        im = im.crop((int(w * 0.05), int(h * 0.025), int(w * 0.95), int(h * 0.185)))
        buf = io.BytesIO()
        im.save(buf, "PNG")
        return buf.getvalue()
    except Exception as e:
        logger.warning(f"Anteprima intestazione non riuscita: {e}")
        return None


def _salva_variante_storico(colonna: str, latex: str) -> None:
    """Aggiunge Fila B ("latex_b") o BES/DSA ("latex_r") alla riga dello storico della verifica
    in corso, così non si perdono quando si crea una nuova verifica. Un errore si ignora."""
    _id = st.session_state.get("_storico_id")
    if not (_id and latex and st.session_state.utente):
        return
    try:
        supabase_admin.table("verifiche_storico").update({colonna: latex})\
            .eq("id", _id).eq("user_id", st.session_state.utente.id).execute()
        _contenuto_verifica.clear()
    except Exception as e:
        logger.warning(f"Salvataggio {colonna} nello storico non riuscito: {e}")


def _rinomina_verifica(verifica_id: int, nuovo_nome: str):
    """
    Rinomina una verifica nel database
    """
    try:
        res = supabase_admin.table("verifiche_storico")\
            .update({"argomento": nuovo_nome})\
            .eq("id", verifica_id)\
            .eq("user_id", st.session_state.utente.id)\
            .execute()
        st.session_state._storico_refresh += 1

        return res.data if res.data else None
    except Exception as e:
        _mostra_errore("Non sono riuscito a rinominare la verifica", e)
        return None

def _genera_link_condivisione(verifica_id: int):
    """
    Genera un link di condivisione per una verifica
    """
    try:
        # Carica la verifica
        res = supabase_admin.table("verifiche_storico")\
            .select("*")\
            .eq("id", verifica_id)\
            .eq("user_id", st.session_state.utente.id)\
            .limit(1)\
            .execute()
        
        if not res.data:
            return None
        
        verifica = res.data[0]

        # Stesso salvataggio della schermata del risultato: titolo, materia, scadenza a 30 giorni
        code = _create_share_link(
            latex_a=verifica.get("latex_a"),
            materia=verifica.get("materia", ""),
            argomento=verifica.get("argomento", ""),
            scuola=verifica.get("scuola", ""),
            num_esercizi=verifica.get("num_esercizi") or 0,
        )
        if not code:
            raise RuntimeError("creazione del link non riuscita")

        return f"{SHARE_URL}?share={code}"

    except Exception as e:
        _mostra_errore("Non sono riuscito a creare il link di condivisione", e)
        return None

def _get_verifiche_stats():
    """
    Calcola le statistiche delle verifiche dell'utente
    """
    verifiche = _load_user_verifiche()
    
    if not verifiche:
        return {
            "totali": 0,
            "questo_mese": 0,
            "materie": set(),
            "esercizi_totali": 0,
            "qualita_media": 0.0
        }
    
    now = datetime.now(timezone.utc)
    primo_mese = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    materie = set()
    questo_mese_count = 0
    esercizi_totali = 0
    
    for v in verifiche:
        if v.get("materia"):
            materie.add(v["materia"])
        
        # Somma esercizi
        if v.get("num_esercizi"):
            esercizi_totali += v["num_esercizi"]
        
        # Conta verifiche di questo mese
        created_at = v.get("created_at")
        if created_at:
            try:
                created_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                if created_dt >= primo_mese:
                    questo_mese_count += 1
            except:
                pass
    
    return {
        "totali": len(verifiche),
        "questo_mese": questo_mese_count,
        "materie": len(materie),
        "esercizi_totali": esercizi_totali,
        "qualita_media": 4.8  # Placeholder - si può calcolare da feedback reali
    }

def _apri_verifica_salvata(verifica: dict, contenuto: dict) -> bool:
    """
    Carica una verifica dello storico nella schermata del risultato (anteprima, download,
    modifica). Parte da uno stato pulito, così nulla della verifica aperta prima si mescola
    a questa; Fila B e BES/DSA tornano disponibili se erano state salvate.
    """
    latex_a = contenuto.get("latex_a")
    if not latex_a:
        return False
    st.session_state.verifiche = {
        "A": _vf(), "B": _vf(), "R": _vf(), "RB": _vf(),
        "S": {"latex": None, "testo": None, "pdf": None},
        "SC": {"latex": None, "pdf": None, "n": 0, "avvisi": []},
    }
    _pulisci_stato_revisione()
    st.session_state.rubrica_testo = None
    st.session_state["_rubrica_docx"] = None
    st.session_state._share_code = None
    va = st.session_state.verifiche["A"]
    va["latex"] = va["latex_originale"] = latex_a
    for fid, col in (("B", "latex_b"), ("R", "latex_r")):
        if contenuto.get(col):
            st.session_state.verifiche[fid]["latex"] = contenuto[col]
    pdf_bytes, _err = _pdf_da_latex(latex_a)
    st.session_state.preview_images = []
    if pdf_bytes:
        va["pdf"] = pdf_bytes
        va["pdf_ts"] = time.time()
        va["preview"] = True
        images, _ = pdf_to_images_bytes(pdf_bytes)
        st.session_state.preview_images = images or []
        st.session_state.last_preview_ts = va["pdf_ts"]
    pre, blocks = extract_blocks(latex_a)
    st.session_state.review_preamble = pre if blocks else ""
    st.session_state.review_blocks = blocks or []
    st.session_state.review_sel_idx = 0
    st.session_state.gen_params = {
        "materia": verifica.get("materia", "Matematica"),
        "difficolta": verifica.get("scuola", "Liceo Scientifico"),
        "argomento": verifica.get("argomento", "Verifica"),
        "num_esercizi": verifica.get("num_esercizi", 5),
        "mostra_punteggi": True,
        "punti_totali": 100,
        "con_griglia": True,
        "modello_id": modello_id,
    }
    st.session_state["_storico_id"] = verifica.get("id")
    st.session_state._facsimile_mode = True
    st.session_state.stage = STAGE_FINAL
    st.session_state._prev_stage = None
    st.session_state.input_percorso = None
    return True


def _render_le_tue_verifiche():
    """
    Pagina "Le mie verifiche" - Gestione verifiche create dall'utente
    """
    # Torna dove si era (es. alla verifica in corso), altrimenti al form di creazione
    _dove = st.session_state.get("_stage_prima")
    if _dove not in (STAGE_FINAL, STAGE_REVIEW) or not st.session_state.get("gen_params"):
        _dove = STAGE_INPUT
    _c_indietro, _ = st.columns([1, 3])
    with _c_indietro:
        if st.button("← Indietro", key="back_from_mie_verifiche",
                     help="Torna a quello che stavi facendo", use_container_width=True):
            st.session_state.stage = _dove
            st.rerun()

    st.markdown(
        f"""
        <div style="text-align:center;margin:.2rem 0 1rem;">
            <div style="font-family:DM Sans,sans-serif;font-size:1.7rem;font-weight:800;
                        letter-spacing:-.025em;color:{T['text']};line-height:1.15;">Le mie verifiche</div>
            <div style="font-size:.9rem;color:{T['text2']};font-family:DM Sans,sans-serif;margin-top:.35rem;">
                Riapri, scarica o condividi le verifiche che hai creato.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Carica dati reali (elenco leggero, in cache: il LaTeX si legge solo quando serve)
    stats = _get_verifiche_stats()
    verifiche = _load_user_verifiche()
    _uid = st.session_state.utente.id

    if not verifiche:
        st.markdown(
            f'<div style="text-align:center;padding:2rem 1rem;border:1px dashed {T["border2"]};'
            f'border-radius:14px;color:{T["text2"]};font-family:DM Sans,sans-serif;">'
            f'<div style="font-size:1.05rem;font-weight:700;color:{T["text"]};margin-bottom:.3rem;">'
            f'Non hai ancora creato verifiche</div>'
            f'Appena ne crei una la trovi qui, pronta da riaprire.</div>',
            unsafe_allow_html=True,
        )
        _, _c_prima, _ = st.columns([1, 2, 1])
        with _c_prima:
            if st.button("Crea la tua prima verifica", type="primary", use_container_width=True,
                         icon=":material/add:", key="storico_prima"):
                st.session_state.stage = STAGE_INPUT
                st.rerun()
        return

    # Riepilogo su una riga
    st.markdown(
        f'<div style="text-align:center;margin:0 0 1.2rem;font-family:DM Sans,sans-serif;'
        f'font-size:.95rem;color:{T["text2"]};">'
        f'<strong style="color:{T["text"]};">{stats["totali"]}</strong> verifiche in tutto &nbsp;·&nbsp; '
        f'<strong style="color:{T["text"]};">{stats["questo_mese"]}</strong> questo mese</div>',
        unsafe_allow_html=True,
    )

    # Filtri e ricerca
    col_search, col_materia, col_ordine = st.columns([3, 2, 2])

    with col_search:
        search_query = st.text_input("Cerca", placeholder="Cerca per materia o argomento…")

    # Materie uniche dalle verifiche reali
    materie_real = ["Tutte"] + sorted(list(set([v.get("materia", "Sconosciuta") for v in verifiche if v.get("materia")])))
    with col_materia:
        materia_filter = st.selectbox("Materia", materie_real)

    with col_ordine:
        ordine_filter = st.selectbox("Ordina per", ["Più recenti", "Più vecchie", "Alfabetico", "Materia"])

    # Filtra le verifiche
    verifiche_filtrate = verifiche.copy()

    if search_query:
        _q = search_query.lower()
        verifiche_filtrate = [v for v in verifiche_filtrate if
            _q in (v.get("materia") or "").lower() or
            _q in (v.get("argomento") or "").lower()]

    if materia_filter != "Tutte":
        verifiche_filtrate = [v for v in verifiche_filtrate if v.get("materia") == materia_filter]

    # Ordina le verifiche
    if ordine_filter == "Più recenti":
        verifiche_filtrate.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    elif ordine_filter == "Più vecchie":
        verifiche_filtrate.sort(key=lambda x: x.get("created_at") or "")
    elif ordine_filter == "Alfabetico":
        verifiche_filtrate.sort(key=lambda x: (x.get("argomento") or "").lower())
    elif ordine_filter == "Materia":
        verifiche_filtrate.sort(key=lambda x: x.get("materia") or "")

    # Mostra verifiche reali — a blocchi di 8 ("Mostra altre"): con centinaia di verifiche
    # il vecchio elenco completo creava migliaia di pulsanti a ogni clic.
    _n_mostra = max(8, int(st.session_state.get("_storico_mostra", 8)))
    if not verifiche_filtrate:
        st.info("Nessuna verifica corrisponde alla ricerca: prova a cancellare i filtri.", icon="🔎")
        return

    for i, verifica in enumerate(verifiche_filtrate[:_n_mostra]):
        _vid = verifica.get("id")
        # Formatta data
        data_formattata = "Data non disponibile"
        if verifica.get("created_at"):
            try:
                created_dt = datetime.fromisoformat(verifica["created_at"].replace('Z', '+00:00'))
                data_formattata = created_dt.strftime("%d/%m/%Y")
            except Exception:
                pass

        with st.container():
            # Titolo, materia in evidenza, il resto in una riga sola
            st.markdown(
                f"""
                <div style="background:{T['card']};border:1px solid {T['border']};border-radius:12px;
                            padding:1rem 1.3rem;margin-bottom:.5rem;">
                    <div style="font-size:1.08rem;font-weight:700;color:{T['text']};margin:0 0 .45rem 0;">
                        {_esc(verifica.get('argomento') or 'Verifica senza titolo')}
                    </div>
                    <div style="display:flex;gap:.6rem;flex-wrap:wrap;align-items:center;
                                font-size:.88rem;color:{T['text2']};">
                        <span style="background:{T['accent_light']};color:{T['accent']};padding:.2rem .7rem;
                                     border-radius:20px;font-weight:600;">
                            {_esc(verifica.get('materia') or 'Sconosciuta')}</span>
                        <span>{_esc(verifica.get('scuola') or 'Scuola non indicata')}
                              · {_esc(verifica.get('num_esercizi') or '?')} esercizi
                              · {_esc(data_formattata)}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Azioni principali in primo piano; Rinomina ed Elimina nel menu "⋯".
            c_apri, c_pdf, c_prev, c_share, c_menu = st.columns([1.35, 1, 1, 1, 0.5])

            with c_apri:
                if st.button("Apri e modifica", icon=":material/edit_note:", use_container_width=True,
                             key=f"facsimile_{_vid}_{i}", type="primary"):
                    try:
                        _cont = _contenuto_verifica(_uid, _vid)
                        if _apri_verifica_salvata(verifica, _cont):
                            st.rerun()
                        else:
                            st.warning("Il contenuto di questa verifica non è disponibile.", icon="⚠️")
                    except Exception as e:
                        _mostra_errore("Non sono riuscito ad aprire questa verifica", e)

            with c_pdf:
                _nome_pdf = re.sub(r"[^\w\-]+", "_", verifica.get("argomento") or "verifica").strip("_")[:60]

                def _pdf_al_clic(_v=_vid):
                    # il PDF si prepara solo quando si preme (e una volta sola per testo, in cache)
                    _lat = _contenuto_verifica(_uid, _v).get("latex_a")
                    _pdf, _err = _pdf_da_latex(_lat) if _lat else (None, "manca il contenuto")
                    if not _pdf:
                        logger.error(f"PDF storico {_v}: {str(_err)[:500]}")
                        raise RuntimeError(
                            "Non sono riuscito a creare il PDF di questa verifica. "
                            "Riprova oppure aprila con «Apri e modifica»."
                        )
                    return _pdf

                _dl(
                    "Scarica PDF", data=_pdf_al_clic,
                    file_name=f"{_nome_pdf}_{data_formattata.replace('/', '')}.pdf",
                    mime="application/pdf", icon=":material/download:",
                    use_container_width=True, key=f"download_{_vid}_{i}",
                    disabled=not LATEX_AVAILABLE,
                    help="Non disponibile: LaTeX non è installato" if not LATEX_AVAILABLE
                         else "Scarica la verifica in formato PDF",
                )

            with c_prev:
                if st.button("Anteprima", icon=":material/visibility:", use_container_width=True,
                             key=f"preview_{_vid}_{i}"):
                    try:
                        _lat = _contenuto_verifica(_uid, _vid).get("latex_a")
                        if not _lat:
                            st.warning("Il contenuto di questa verifica non è disponibile.", icon="⚠️")
                        else:
                            with st.spinner("Preparo l'anteprima…"):
                                pdf_bytes, error = _pdf_da_latex(_lat)
                                images, _ = pdf_to_images_bytes(pdf_bytes) if pdf_bytes else (None, None)
                            if images:
                                with st.expander("Anteprima", expanded=True):
                                    for j, img in enumerate(images[:3]):  # max 3 pagine
                                        st.image(img, caption=f"Pagina {j+1}", use_container_width=True)
                            elif pdf_bytes:
                                st.error("Non sono riuscito a creare l'anteprima. Riprova.", icon="⚠️")
                            else:
                                _mostra_errore_pdf(error, "questa verifica")
                    except Exception as e:
                        _mostra_errore("Non sono riuscito a creare l'anteprima", e)

            with c_share:
                if st.button("Condividi", icon=":material/link:", use_container_width=True,
                             key=f"share_{_vid}_{i}"):
                    link = _genera_link_condivisione(_vid)
                    if link:
                        st.caption("Link per i colleghi (vale 30 giorni): copialo con l'icona a destra.")
                        st.code(link, language=None)

            with c_menu.popover("⋯", help="Rinomina o elimina questa verifica"):
                nuovo_nome = st.text_input(
                    "Nome della verifica",
                    value=verifica.get("argomento", ""),
                    key=f"rename_input_{_vid}_{i}",
                )
                if st.button("Salva nome", icon=":material/save:", key=f"save_rename_{_vid}_{i}",
                             use_container_width=True):
                    if nuovo_nome.strip() and _rinomina_verifica(_vid, nuovo_nome.strip()):
                        st.rerun()
                st.divider()
                # Elimina: conferma esplicita in due passaggi
                if not st.session_state.get(f"confirm_delete_{_vid}", False):
                    if st.button("Elimina", icon=":material/delete:", key=f"delete_{_vid}_{i}",
                                 use_container_width=True):
                        st.session_state[f"confirm_delete_{_vid}"] = True
                        st.rerun()
                else:
                    st.warning("Eliminare definitivamente questa verifica?")
                    _c_si, _c_no = st.columns(2)
                    if _c_si.button("Sì, elimina", key=f"delete_yes_{_vid}_{i}", type="primary", use_container_width=True):
                        try:
                            # Eliminazione «logica»: sparisce dall'elenco ma continua a contare nel tetto
                            # mensile (altrimenti basterebbe eliminare le verifiche per averne altre gratis).
                            res = supabase_admin.table("verifiche_storico")\
                                .update({"deleted_at": datetime.now(timezone.utc).isoformat()})\
                                .eq("id", _vid).eq("user_id", _uid).is_("deleted_at", "null").execute()
                            st.session_state.pop(f"confirm_delete_{_vid}", None)
                            if res.data:
                                st.session_state._storico_refresh += 1
                                st.rerun()
                            else:
                                st.error("Non sono riuscito a eliminare la verifica. Riprova.", icon="⚠️")
                        except Exception as e:
                            _mostra_errore("Non sono riuscito a eliminare la verifica", e)
                    if _c_no.button("No", key=f"delete_no_{_vid}_{i}", use_container_width=True):
                        st.session_state.pop(f"confirm_delete_{_vid}", None)
                        st.rerun()

            spazio("lg")

    if len(verifiche_filtrate) > _n_mostra:
        if st.button(f"Mostra altre ({len(verifiche_filtrate) - _n_mostra})", key="storico_mostra_altre", use_container_width=True):
            st.session_state["_storico_mostra"] = _n_mostra + 8
            st.rerun()

class _FileInMemoria:
    """File caricato tenuto in memoria: stessa interfaccia minima di un UploadedFile
    (type, name, getvalue) per genera_verifica, ma non dipende dal widget di upload."""

    def __init__(self, dati: bytes, mime: str, nome: str):
        self._dati, self.type, self.name = dati, mime, nome

    def getvalue(self) -> bytes:
        return self._dati


def _render_percorso_b_form(_prog_placeholder):
    """
    Percorso B — Layout a colonna singola con upload inline:
    ┌─────────────────────────────────────────────────┐
    │  Materia  │  Scuola                              │
    │  Argomento (2/3)  │  📎 Documento (1/3)          │
    │  N° Esercizi                                     │
    │  ⚙️ Personalizzazione Avanzata (expander)        │
    │  🚀 GENERA BOZZA                                 │
    └─────────────────────────────────────────────────┘
    """

    # ── Materia e scuola rilevate dal file (applicate prima di creare i widget) ──
    if st.session_state.pop("_applica_analisi", False):
        _ic0 = st.session_state.info_consolidate
        if _ic0.get("materia") in MATERIE:
            st.session_state["sel_materia_b"] = _ic0["materia"]
        if _ic0.get("scuola") in SCUOLE:
            st.session_state["sel_scuola_b"] = _ic0["scuola"]

    # ── Generazione facsimile: scelta «Rifai questa verifica con dati nuovi» ──
    if st.session_state.get("_fac_confirmed"):
        st.session_state["_fac_confirmed"] = False
        _a_fac = st.session_state.get("_fac_dialog_data", {})
        if _a_fac and not _limite:
            # Trova il file nel pool e marcalo come copia_fedele
            _fac_hash = _a_fac.get("file_hash")
            for _idx_f, _ef in enumerate(st.session_state.analisi_docs_list):
                if _ef["file_hash"] == _fac_hash:
                    st.session_state.analisi_docs_list[_idx_f]["confirmed"] = True
                    st.session_state.analisi_docs_list[_idx_f]["file_mode"] = "copia_fedele"
                    break
            st.session_state.file_mode        = "copia_fedele"
            st.session_state["_facsimile_mode"] = True
            _consolida_info()
            _info_fac      = st.session_state.info_consolidate
            _ha_griglia_fac = _a_fac.get("ha_tabella_punti", False)
            _pt_fac = 100
            if isinstance(_a_fac.get("punti_totali_rilevati"), (int, float)) and _a_fac["punti_totali_rilevati"] > 0:
                _pt_fac = int(_a_fac["punti_totali_rilevati"])
            _mat_fac = _info_fac.get("materia", "Matematica")
            _scu_fac = _info_fac.get("scuola", SCUOLE[0])
            _n_fac   = max(1, min(int(_a_fac.get("num_esercizi_rilevati") or 4), 15))
            argomento_fac, note_fac = compila_contesto_generazione(
                analisi=_info_fac,
                file_mode="copia_fedele",
                istruzioni_extra="",
                argomento_override=None,
            )
            note_fac = (
                "╔══════════════════════════════════════════════════════════════╗\n"
                "║  ⚠️  ISTRUZIONE CRITICA — FACSIMILE: DATI COMPLETAMENTE NUOVI  ║\n"
                "╚══════════════════════════════════════════════════════════════╝\n"
                "Stai generando un FACSIMILE della verifica allegata.\n"
                "REGOLA ASSOLUTA: struttura identica, stessi punteggi totali, stessa materia e argomento; "
                "tutti i dati numerici e testuali COMPLETAMENTE DIVERSI.\n"
                "NON usare gli stessi valori nemmeno come riferimento.\n"
                "Il docente NON deve riconoscere i dati originali.\n"
            ) + "\n\n" + note_fac
            _s_es_fac, _imgs_es_fac = _build_prompt_esercizi([], _n_fac, _pt_fac, True)
            _prog_fac = st.empty()
            _lancia_generazione(
                materia_scelta=_mat_fac,
                argomento=argomento_fac,
                difficolta=_scu_fac,
                durata_scelta="1 ora",
                num_esercizi_totali=_n_fac,
                punti_totali=_pt_fac,
                mostra_punteggi=True,
                con_griglia=_ha_griglia_fac or True,
                note_generali=note_fac,
                s_es=_s_es_fac,
                imgs_es=_imgs_es_fac,
                file_ispirazione=(
                    _FileInMemoria(_fm_fac["bytes"], _fm_fac["mime"], _fm_fac["name"])
                    if (_fm_fac := st.session_state.get("_file_materiale")) else None
                ),
                prog_placeholder=_prog_fac,
            )
            # La generazione fallita non fa rerun: restituisce valori neutri (nessun avvio)
            return ("", "Matematica", SCUOLE[0], True, True, 100, _n_fac, "", False,
                    _prog_fac, "1 ora", DURATA_DEFAULT)

    # ── Toast post-analisi file (mostrato una volta sola dopo il rerun) ──────────
    _toast_msg = st.session_state.pop("_toast_analisi", None)
    if _toast_msg:
        st.toast(f"✅ Documento analizzato — {_toast_msg}", icon="🔬")

    # ═════════════════════════════════════════════════════════════════════════
    #  FORM PRINCIPALE — colonna sinistra (form) | colonna destra (upload)
    # ═════════════════════════════════════════════════════════════════════════
    if True:
        _prev = st.session_state.gen_params or {}
        # ── IDEA #1: carica defaults silenti come fallback ────────────────
        _udef = _load_user_defaults()

        if True:  # blocco unico -- layout a singola colonna
            # ── Dashboard: sezione form (layout bilanciato) ───────────────────────
            # Section header rimosso per evitare ripetizioni

            # L'avanzamento e gli errori stanno in cima alla pagina: il segnaposto
            # (_prog_placeholder) lo crea _render_stage_input, fuori da questo form.

            _mat_list = MATERIE + ["✏️ Altra materia..."]
            _mat_prev = _prev.get("materia") or _udef.get("materia", "Matematica")
            _mat_idx  = _mat_list.index(_mat_prev) if _mat_prev in _mat_list else 0
            _scu_prev = _prev.get("difficolta") or _udef.get("scuola", "")
            _scu_idx  = SCUOLE.index(_scu_prev) if _scu_prev in SCUOLE else 0

            # Auto-fill da analisi file se disponibile
            _info_cons = st.session_state.info_consolidate
            if _info_cons.get("materia") and _info_cons["materia"] in _mat_list:
                _mat_idx = _mat_list.index(_info_cons["materia"])
            if _info_cons.get("scuola") and _info_cons["scuola"] in SCUOLE:
                _scu_idx = SCUOLE.index(_info_cons["scuola"])

            # Materia e scuola già note (ultima verifica): una riga compatta con "cambia";
            # alla prima visita restano visibili entrambi i menu.
            _mat_ora = st.session_state.get("sel_materia_b", _mat_list[_mat_idx])
            _scu_ora = st.session_state.get("sel_scuola_b", SCUOLE[_scu_idx])
            if _udef.get("materia") and _udef.get("scuola"):
                _box_ms = st.expander(f"{_mat_ora} · {_scu_ora}  —  cambia", expanded=False, icon=":material/school:")
            else:
                _box_ms = st.container()
            with _box_ms:
                _col_m, _col_s = st.columns(2, gap="small")

            with _col_m:
                st.markdown('<div class="opt-label">Materia ✱</div>', unsafe_allow_html=True)
                _sel_m = st.selectbox(
                    "Materia", _mat_list, index=_mat_idx,
                    label_visibility="collapsed", key="sel_materia_b",
                    help="Materia della verifica. Se hai caricato un file, viene rilevata automaticamente.",
                )
                materia_scelta = (
                    st.text_input("Scrivi materia:", key="_mat_custom_b",
                                  label_visibility="collapsed").strip() or "Matematica"
                    if _sel_m == "✏️ Altra materia..."
                    else (_sel_m or "Matematica")
                )
            with _col_s:
                st.markdown('<div class="opt-label">Tipo di scuola ✱</div>', unsafe_allow_html=True)
                difficolta = st.selectbox(
                    "Scuola", SCUOLE, index=_scu_idx,
                    help="Tipo di scuola e livello. Se hai caricato un file, viene rilevato automaticamente.",
                    label_visibility="collapsed", key="sel_scuola_b",
                )

            # Section header rimosso per evitare ripetizioni
            _auto_arg = _info_cons.get("contenuto_argomento", "")
            _arg_source = st.session_state.get("_pb_argomento_source")
            if _auto_arg and _arg_source != "manual":
                _current = st.session_state.get("argomento_area_b", "")
                if _current != _auto_arg:
                    st.session_state["argomento_area_b"] = _auto_arg
                # Badge arricchito con materia + tipo rilevati
                _badge_mat  = _info_cons.get("materia", "")
                _badge_tipo = _info_cons.get("tipo_documento", "")
                _badge_extras = []
                if _badge_mat:
                    _badge_extras.append(f"<strong>{_badge_mat}</strong>")
                if _badge_tipo:
                    _badge_extras.append(_badge_tipo.replace("_", " "))
                _badge_extra_str = (" · " + " · ".join(_badge_extras)) if _badge_extras else ""
                st.markdown(
                    f'<div class="context-sync-badge">'
                    f'✅ Compilato automaticamente dal file caricato{_badge_extra_str}'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            _arg_default = ""
            if _arg_source == "manual":
                _arg_default = st.session_state.get("_pb_argomento_manual_val", "")
            elif _auto_arg:
                _arg_default = _auto_arg
            # ── RICHIESTA UNICA: argomento + indicazioni nello stesso riquadro ─────────
            st.markdown(
                '<div class="opt-label">Cosa vuoi nella verifica? ✱ '
                '<span class="opt-hint">Argomento nella prima riga, poi cosa includere o evitare</span></div>',
                unsafe_allow_html=True,
            )
            _esempio = esempio_richiesta(materia_scelta)

            # Controlla se c'è già un valore in session state per evitare il warning
            if "argomento_area_b" not in st.session_state:
                argomento_raw = st.text_area(
                    "Cosa vuoi nella verifica? (obbligatorio)",
                    value=_arg_default,
                    placeholder=_esempio,
                    height=110,
                    label_visibility="collapsed",
                    key="argomento_area_b",
                )
            else:
                argomento_raw = st.text_area(
                    "Cosa vuoi nella verifica? (obbligatorio)",
                    placeholder=_esempio,
                    height=110,
                    label_visibility="collapsed",
                    key="argomento_area_b",
                )

            # ── Traccia modifica manuale del riquadro ─────────────────────────────
            _auto_arg_ref = _info_cons.get("contenuto_argomento", "")
            _richiesta = argomento_raw.strip()
            if _richiesta and _richiesta != _auto_arg_ref:
                st.session_state["_pb_argomento_source"] = "manual"
                st.session_state["_pb_argomento_manual_val"] = _richiesta
            elif not _richiesta and st.session_state.get("_pb_argomento_source") == "manual":
                st.session_state["_pb_argomento_source"] = None
            # prima riga = argomento (titolo e prompt); righe successive = indicazioni
            argomento, _note_dal_riquadro = separa_argomento_e_note(_richiesta)

            _prefs = st.session_state._docente_prefs.get(materia_scelta, {})
            if not _prefs and st.session_state.utente and materia_scelta in MATERIE:
                _prefs = _carica_docente_preferenze(st.session_state.utente.id, materia_scelta)
                st.session_state._docente_prefs[materia_scelta] = _prefs

            # ── Divisore sottile prima di Personalizzazione ──────────────────────
            st.markdown('<div class="divider-minimal"></div>', unsafe_allow_html=True)
            # ── Personalizzazione Avanzata — st.expander standard ────────────────
            # Defaults da session state (validi anche quando expander è chiuso)
            mostra_punteggi = st.session_state.get("_pers_punteggi", _udef.get("mostra_punteggi", True))
            con_griglia  = mostra_punteggi
            punti_totali = st.session_state.get("_pers_pt", _udef.get("punti_totali", 100))

            # ── Hai già del materiale? Upload + tre scelte (l'AI legge il file solo al clic) ──
            _rifiuto = st.session_state.pop("_analisi_rifiuto", None)
            if _rifiuto:
                # file non scolastico: lo tolgo e spiego perché
                st.session_state["_file_materiale"] = None
                st.session_state.file_ispirazione = None
                st.session_state["_up_ciclo"] += 1
                st.warning(_rifiuto.get("messaggio") or "Questo file non sembra materiale scolastico.", icon="📎")
            _fm = st.session_state.get("_file_materiale")
            with st.expander("Altre opzioni (lunghezza, materiale, punteggi, logo)", expanded=bool(_fm), icon=":material/tune:"):
                st.markdown('<span class="g-altre" style="display:none"></span>', unsafe_allow_html=True)
                # ── DURATA: un solo scatto sceglie numero di esercizi e tempo previsto ──────
                _nomi_dur = list(DURATE)
                # Si parte sempre da «Standard»: la lunghezza cambia da verifica a verifica,
                # non ha senso ereditare quella dell'ultima volta.
                _dur_salvata = DURATA_DEFAULT
                durata_nome = _dur_salvata   # la lunghezza si sceglie col numero di esercizi (sotto)
                _par_dur   = parametri_durata(durata_nome, difficolta)
                durata_str = _par_dur["durata"]

                # Numero di esercizi di partenza: quello della durata scelta. Con «Rifai questa
                # verifica» numero di esercizi e punti vengono dal file (vedi il ramo facsimile).
                _n_default = _par_dur["num_esercizi"]
                _n_opts = list(range(3, 11))      # meno di 3 o piu' di 10 esercizi non sono una verifica
                _n_idx  = (_n_opts.index(_n_default) if _n_default in _n_opts else 3)


                st.markdown('<div class="opt-label">Quanti esercizi nella verifica?</div>', unsafe_allow_html=True)
                num_esercizi = st.selectbox(
                    "Numero esercizi",
                    options=_n_opts,
                    index=_n_idx,
                    label_visibility="collapsed",
                    key=f"sel_num_es_b_{durata_nome}",   # cambia con la durata: riparte dal preset
                    format_func=lambda x: f"{x} esercizi",
                )

                _tog = st.toggle(
                    "Mostra i punti accanto a ogni domanda",
                    value=mostra_punteggi, key="toggle_punteggi_b",
                )
                mostra_punteggi = _tog
                con_griglia = _tog
                st.session_state["_pers_punteggi"] = _tog
                
                # Calcola punti totali: priorità file > sessione > default
                punti_totali = 100
                if _tog:
                    # Prova a usare i punti rilevati dal file
                    _pt_rilevati = _info_cons.get("punti_totali_rilevati")
                    if isinstance(_pt_rilevati, (int, float)) and _pt_rilevati > 0:
                        punti_totali = int(_pt_rilevati)
                    else:
                        # Fallback: sessione o default
                        punti_totali = st.session_state.get("_pers_pt", _udef.get("punti_totali", 100))
                    
                    _pt_opts = list(range(10, 105, 5))
                    _pt_idx  = _pt_opts.index(punti_totali) if punti_totali in _pt_opts else (_pt_opts.index(100) if 100 in _pt_opts else len(_pt_opts) - 1)
                    
                    # Mostra info se i punti sono rilevati dal file
                    if isinstance(_pt_rilevati, (int, float)) and _pt_rilevati > 0:
                        st.markdown('<div class="opt-label">Punti totali <span style="font-size:.75rem;opacity:.7;">(rilevati dal file)</span></div>', unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="opt-label">Punti totali</div>', unsafe_allow_html=True)
                    
                    punti_totali = st.selectbox(
                        "Punti totali", options=_pt_opts, index=_pt_idx,
                        label_visibility="collapsed", key="sel_punti_b",
                        format_func=lambda x: f"{x} pt",
                    )
                    st.session_state["_pers_pt"] = punti_totali

                st.markdown(_html_separatore() + '<div class="opt-label">Hai già del materiale? (opzionale)</div>', unsafe_allow_html=True)
                if _pro_bloccato("materiale") and not _fm:
                    st.caption("Carica appunti o una verifica già fatta e VerificAI ne crea una nuova, con dati diversi: "
                               "è una funzione del piano Pro.")
                    _pulsante_pro("materiale", "pro_materiale", "Carica un file con Pro")
                elif not _fm:
                    _up = st.file_uploader(
                        "Carica appunti, una verifica o un foglio di esercizi",
                        type=["pdf", "png", "jpg", "jpeg"],
                        key=f"pb_file_up_{st.session_state['_up_ciclo']}",
                        help="PDF o foto. Il file viene letto quando premi «Crea verifica».",
                    )
                    if _up:
                        _bytes_up = _up.getvalue()
                        st.session_state["_file_materiale"] = {
                            "bytes": _bytes_up, "mime": _up.type or "image/png",
                            "name": _up.name, "hash": hash(_bytes_up),
                        }
                        st.session_state.file_ispirazione = _FileInMemoria(
                            _bytes_up, _up.type or "image/png", _up.name)
                        st.rerun()
                else:
                    _nome_f = _fm["name"] if len(_fm["name"]) <= 38 else _fm["name"][:35] + "…"
                    st.markdown(
                        f'<div class="file-pool-card"><div class="fpc-header">'
                        f'<span class="fpc-name">📄 {_nome_f}</span></div></div>',
                        unsafe_allow_html=True,
                    )
                    _SCELTE_MATERIALE = {
                        "base_conoscenza":   "📚 Prendi spunto dai miei appunti",
                        "includi_esercizio": "✏️ Includi questi esercizi nella verifica",
                        "copia_fedele":      "🔁 Rifai questa verifica con dati nuovi",
                    }
                    _scelta_mat = st.radio(
                        "Cosa vuoi fare con questo file?",
                        options=list(_SCELTE_MATERIALE),
                        format_func=lambda k: _SCELTE_MATERIALE[k],
                        key="sel_materiale_b",
                    )
                    _SUGGERIMENTI_MATERIALE = {
                        "base_conoscenza":   "Esercizi nuovi sugli argomenti del tuo materiale, nello stesso livello.",
                        "includi_esercizio": "Gli esercizi del file entrano nella verifica; l'AI crea gli altri.",
                        "copia_fedele":      "Stessa struttura e stessi punteggi del file, con numeri e testi nuovi "
                                             "(il numero di esercizi e i punti vengono dal file).",
                    }
                    st.caption(_SUGGERIMENTI_MATERIALE[_scelta_mat])
                    if st.button("✕ Togli il file", key="pb_rm_materiale"):
                        for _k_rm in ("_file_materiale", "analisi_doc", "file_mode", "file_ispirazione"):
                            st.session_state[_k_rm] = None
                        st.session_state.analisi_docs_list = []
                        st.session_state.info_consolidate = {}
                        st.session_state.istruzioni_per_file = {}
                        st.session_state["_up_ciclo"] += 1
                        if st.session_state.get("_pb_argomento_source") != "manual":
                            st.session_state["_pb_argomento_source"] = None
                        st.rerun()

                # ── Logo della scuola: si carica una volta, poi compare in tutte le verifiche ──
                st.markdown(_html_separatore() + '<div class="opt-label">Logo della scuola (opzionale)</div>',
                            unsafe_allow_html=True)
                _logo_s = _logo_scuola()
                _logo_bloccato = _pro_bloccato("logo")
                if _logo_bloccato:
                    st.caption("Il logo della tua scuola sull'intestazione è una funzione del piano Pro.")
                    _pulsante_pro("logo", "pro_logo", "Logo della scuola con Pro")
                elif _logo_s:
                    _attivo_nuovo = st.toggle("Metti il logo nelle verifiche",
                                              value=_logo_s.get("attivo", True), key="logo_attivo_b")
                    if _attivo_nuovo != _logo_s.get("attivo", True):
                        _salva_logo({**_logo_s, "attivo": _attivo_nuovo})
                    _etichette_scala = {0.75: "Più piccolo", 1.0: "Normale", 1.25: "Più grande"}
                    _scala_salvata = float(_logo_s.get("scala", 1.0))
                    _scala_nuova = st.select_slider(
                        "Dimensione del logo", options=list(_etichette_scala),
                        value=_scala_salvata if _scala_salvata in _etichette_scala else 1.0,
                        format_func=_etichette_scala.get, key="logo_scala_b",
                    )
                    if _scala_nuova != _scala_salvata:
                        _salva_logo({**_logo_s, "scala": _scala_nuova})
                    # Anteprima immediata dell'intestazione: niente generazione sprecata
                    with st.spinner("Preparo l'anteprima dell'intestazione…"):
                        _img_int = _anteprima_intestazione(
                            _logo_s["b64"], _logo_s.get("tipo", "largo"), _attivo_nuovo, materia_scelta,
                            _scala_nuova, _LAYOUT_LOGO)
                    if _img_int:
                        st.image(_img_int, width=560)
                        st.caption("Intestazione come sarà nel PDF (il titolo sarà quello della tua verifica).")
                    if st.button("Cambia o togli il logo", key="logo_togli", icon=":material/delete:"):
                        _salva_logo(None)
                        st.rerun()
                    st.caption("Vale per le nuove verifiche e per la Fila B; nel file Word non compare.")
                else:
                    _logo_up = st.file_uploader(
                        "Carica il logo della tua scuola (PNG o JPG)", type=["png", "jpg", "jpeg"],
                        key="logo_up_b", help="Si salva sul tuo account: lo carichi una volta sola.",
                    )
                    st.caption("Meglio un'immagine nitida (almeno 600 px di larghezza) con sfondo bianco o "
                               "trasparente. Margini e formato (largo o piccolo) li sistema da solo il programma; "
                               "dopo il caricamento vedi subito l'anteprima dell'intestazione.")
                    if _logo_up is not None:
                        _esito_logo = _prepara_logo(_logo_up.getvalue())
                        if _esito_logo:
                            _salva_logo({"b64": _esito_logo[0], "tipo": _esito_logo[1], "attivo": True})
                            st.rerun()
                        else:
                            st.warning("Non riesco a leggere questa immagine: prova con un PNG o un JPG più piccolo.")

            # ── CTA: Genera Bozza ─────────────────────────────────────────────────
            _manca_arg = not argomento and not _fm
            spazio("lg")

            st.markdown('<div class="cta-genera-wrap">', unsafe_allow_html=True)
            genera_btn = st.button(
                "🚀  Crea verifica",
                use_container_width=True,
                type="primary",
                disabled=_limite or _blocco_conteggio or _manca_arg,
                key="genera_btn_b",
                help=("Scrivi prima l'argomento nel riquadro per continuare." if (_manca_arg and not _limite) else
                      "Avvia la generazione AI della verifica. Potrai modificare ogni singolo esercizio prima di scaricare il PDF."),
            )
            st.markdown('</div>', unsafe_allow_html=True)

            if _limite:
                _render_limite_raggiunto(
                    T, _TETTO_MENSILE, _reset_label(*_giorni_al_reset()), FEEDBACK_FORM_URL,
                    pro_cb=(lambda: _vai_a_upgrade(None)) if MONETIZZAZIONE_ATTIVA else None, pro_key="form",
                )
            elif _blocco_conteggio:
                messaggio("avviso", "Non riesco a controllare il tuo utilizzo mensile in questo momento. "
                                    "Riprova tra qualche istante.")
            elif not _illimitato and _restanti is not None:
                # il contatore sta anche nella sidebar, ma di solito è chiusa
                st.markdown(
                    f'<div style="text-align:center;font-size:.85rem;color:{T["text2"]};'
                    f'font-family:DM Sans,sans-serif;margin-top:.4rem;">'
                    f'Ti {"resta" if _restanti == 1 else "restano"} <b>{_restanti}</b> '
                    f'{"verifica" if _restanti == 1 else "verifiche"} gratuit{"a" if _restanti == 1 else "e"} '
                    f'questo mese.</div>',
                    unsafe_allow_html=True,
                )

            # Avviso PDF non disponibile
            if not LATEX_AVAILABLE:
                messaggio("avviso", "Il PDF non è disponibile su questo server (manca LaTeX): "
                                    "puoi creare la verifica ma non scaricare il PDF.")

    # ── Costruisci nota finale con istruzioni per-file ────────────────────────
    _istr_per_file_testi = []
    for _fentry in st.session_state.analisi_docs_list:
        _fh_str = str(_fentry["file_hash"])
        _istr = st.session_state.istruzioni_per_file.get(_fh_str, "").strip()
        if _istr:
            _istr_per_file_testi.append(f"[File: {_fentry['file_name']}] {_istr}")
    _istruzioni_combinate = "\n".join(_istr_per_file_testi)

    note_extra_raw = _note_dal_riquadro
    if note_extra_raw and _istruzioni_combinate:
        note_extra_finale = note_extra_raw + "\n\n" + _istruzioni_combinate


    elif _istruzioni_combinate:
        note_extra_finale = _istruzioni_combinate
    else:
        note_extra_finale = note_extra_raw

    return (
        argomento,
        materia_scelta,
        difficolta,
        mostra_punteggi,
        con_griglia,
        punti_totali,
        num_esercizi,
        note_extra_finale,
        genera_btn,
        _prog_placeholder,
        durata_str,
        durata_nome,
    )


def _lancia_generazione(
    materia_scelta: str,
    argomento: str,
    difficolta: str,
    durata_scelta: str,
    num_esercizi_totali: int,
    punti_totali: int,
    mostra_punteggi: bool,
    con_griglia: bool,
    note_generali: str,
    s_es: str,
    imgs_es: list,
    file_ispirazione=None,
    prog_placeholder=None,         # st.empty() creato nel form, vicino al pulsante
):
    """
    Funzione condivisa dai due percorsi: lancia genera_verifica,
    aggiorna session_state e transita a STAGE_REVIEW.
    """
    # Ricontrollo del limite al momento di partire (non solo il pulsante disabilitato): copre doppio
    # clic, schede aperte in parallelo e un conteggio che prima non era disponibile.
    _ok_gen, _motivo_gen = _puo_generare_ora()
    if not _ok_gen:
        st.session_state["_esito_gen"] = {"testo": _motivo_gen}
        st.rerun()

    calibrazione = CALIBRAZIONE_SCUOLA.get(difficolta, "")
    _t_start = time.time()
    _n_steps = 4   # titolo · esercizi · controllo · PDF
    _step    = [0]
    # Usa il placeholder passato (in cima alla pagina) oppure crea uno nuovo
    _prog    = prog_placeholder if prog_placeholder is not None else st.empty()

    def _passo_leggibile(testo: str) -> str:
        """Traduce il messaggio interno della pipeline in una frase per il docente."""
        t = (testo or "").lower()
        if "titolo" in t:
            return "Scelgo il titolo"
        if "esercizi" in t and "generazione" in t:
            return "Scrivo gli esercizi"
        if "controllo" in t or "qualit" in t:
            return "Ricontrollo gli esercizi"
        if "pdf" in t:
            return "Preparo il PDF"
        return "Ancora un momento"

    def _avanza(testo):
        _step[0] += 1
        perc  = int(min(_step[0] / _n_steps, 0.95) * 100)
        _acc  = T["accent"]
        _bg   = T["border"]
        _txt  = T["text2"]
        _prog.markdown(
            f'<style>@keyframes vf-scorri{{0%{{background-position:200% 0}}100%{{background-position:-200% 0}}}}</style>'
            f'<div role="status" aria-live="polite" style="margin:.4rem 0 1.2rem 0;padding:1.1rem 1.3rem;'
            f'background:{T["card"]};border:1px solid {T["border2"]};border-radius:14px;">'
            f'<div style="font-family:DM Sans,sans-serif;font-size:1.05rem;font-weight:800;'
            f'color:{T["text"]};margin-bottom:.15rem;">Sto creando la tua verifica…</div>'
            f'<div style="font-size:.9rem;color:{_txt};font-family:DM Sans,sans-serif;margin-bottom:.8rem;">'
            f'{_esc(_passo_leggibile(testo))} · di solito ci vuole circa un minuto. '
            f'Non toccare e non chiudere la pagina.</div>'
            f'<div style="background:{_bg};border-radius:100px;height:8px;overflow:hidden;">'
            f'<div style="width:{perc}%;height:100%;border-radius:100px;'
            f'background:linear-gradient(90deg,{_acc},{_acc}88,{_acc});background-size:200% 100%;'
            f'animation:vf-scorri 2.2s linear infinite;transition:width .5s ease;"></div>'
            f'</div></div>',
            unsafe_allow_html=True
        )

    # ── Routing intelligente modello ──────────────────────────────────────────
    # Se la sidebar ha restituito un modello specifico (admin/pro/gold), lo usa.
    # Altrimenti usa il routing automatico basato su piano + materia.
    _piano_corrente = st.session_state.get("piano_utente", "free")
    if _is_admin:
        _piano_corrente = "admin"
    _modello_id_eff = modello_id  # da sidebar
    # Verifica che il modello selezionato sia coerente con il piano (protezione lato server)
    # Usa sempre gli ID definiti in config.MODELLI_DISPONIBILI per evitare drift tra codice e config.
    _id_free  = MODELLI_DISPONIBILI["⚡ Flash 2.5 Lite (veloce · Free)"]["id"]
    _ids_all  = {v["id"] for v in MODELLI_DISPONIBILI.values()}
    _ids_pro  = {
        v["id"]
        for v in MODELLI_DISPONIBILI.values()
        if v.get("piano") in ("free", "pro")
    }
    _modello_validi_per_piano = {
        "free":  {_id_free},
        "pro":   _ids_pro,
        "gold":  _ids_all,
        "admin": _ids_all,
    }
    if _modello_id_eff not in _modello_validi_per_piano.get(_piano_corrente, set()):
        # Fallback sicuro
        _modello_id_eff = get_model_id_per_piano(_piano_corrente, materia_scelta)

    try:
        model_obj = crea_modello(_modello_id_eff)
        ris = genera_verifica(
            model=model_obj, materia=materia_scelta, argomento=argomento,
            difficolta=difficolta, calibrazione=calibrazione, durata=durata_scelta,
            num_esercizi=num_esercizi_totali, punti_totali=punti_totali,
            mostra_punteggi=mostra_punteggi, con_griglia=con_griglia,
            doppia_fila=False, bes_dsa=False, perc_ridotta=20,
            bes_dsa_b=False, genera_soluzioni=False,
            note_generali=note_generali, istruzioni_esercizi=s_es,
            immagini_esercizi=imgs_es, file_ispirazione=file_ispirazione,
            on_progress=_avanza,
        )
        st.session_state["_autoverifica"] = ris.get("_autoverifica")

        # Logo della scuola: se l'utente ne ha uno attivo va nell'intestazione della Fila A
        # (e quindi anche nelle versioni che ne derivano); si ricompila il PDF con il logo.
        _logo_s = _logo_scuola()
        if _logo_s and _logo_s.get("attivo", True) and ris["A"].get("latex") and not _pro_bloccato("logo"):
            _lat_logo = inserisci_logo(ris["A"]["latex"], _logo_s.get("tipo", "largo"), _logo_s["b64"],
                                         float(_logo_s.get("scala", 1.0)))
            if _lat_logo != ris["A"]["latex"]:
                _pdf_logo, _err_logo, _lat_logo = compila_pdf_sicuro(_lat_logo)
                if _pdf_logo:
                    ris["A"]["latex"], ris["A"]["pdf"] = _lat_logo, _pdf_logo
                else:
                    logger.warning(f"Logo non applicato: {str(_err_logo)[:300]}")

        if "_validation_score" in ris:
            logger.info(f"Validation score: {ris['_validation_score']}")

        def _agg(fid, d):
            v = st.session_state.verifiche[fid]
            if d.get("latex"): v["latex"] = v["latex_originale"] = d["latex"]
            if d.get("pdf"):   v["pdf"] = d["pdf"]; v["pdf_ts"] = time.time(); v["preview"] = True
            if fid == "S":
                if d.get("testo"): v["testo"] = d["testo"]
                if d.get("latex"): v["latex"] = d["latex"]
                if d.get("pdf"):   v["pdf"]   = d["pdf"]

        _agg("A", ris["A"]); _agg("B", ris["B"])
        _agg("R", ris["R"]); _agg("RB", ris["RB"])
        _agg("S", ris["S"])

        st.session_state.gen_time_sec = int(time.time() - _t_start)
        st.session_state.gen_params = {
            "materia": materia_scelta, "difficolta": difficolta,
            "argomento": ris["titolo"], "durata": durata_scelta,
            "num_esercizi": num_esercizi_totali, "punti_totali": punti_totali,
            "mostra_punteggi": mostra_punteggi, "con_griglia": con_griglia,
            "perc_ridotta": 20, "modello_id": _modello_id_eff,
        }

        preamble, blocks = extract_blocks(st.session_state.verifiche["A"]["latex"])
        st.session_state.review_preamble  = preamble
        st.session_state.review_blocks    = blocks
        st.session_state.review_sel_idx   = 0
        st.session_state.last_materia     = materia_scelta
        st.session_state.last_argomento   = ris["titolo"]

        if st.session_state.verifiche["A"]["pdf"]:
            imgs, _ = pdf_to_images_bytes(st.session_state.verifiche["A"]["pdf"])
            st.session_state.preview_images = imgs or []
            st.session_state.preview_page   = 0
            st.session_state.last_preview_ts = st.session_state.verifiche["A"].get("pdf_ts") or 0

        _prog.empty()

        try:
            _ris_ins = supabase_admin.table("verifiche_storico").insert({
                "user_id":        st.session_state.utente.id,
                "materia":        materia_scelta,
                "argomento":      ris["titolo"],
                "scuola":         difficolta,
                "latex_a":        ris["A"]["latex"] or None,
                "latex_b":        None,
                "latex_r":        None,
                "modello":        _modello_id_eff,
                "num_esercizi":   num_esercizi_totali,
                # ── Campi percorso/upload (recuperati dallo session_state)
                "percorso_scelto": st.session_state.get("input_percorso"),
                "file_mode":       st.session_state.get("file_mode"),
            }).execute()
            st.session_state._storico_refresh += 1
            # id della riga appena creata: serve per aggiungerle poi Fila B e BES/DSA
            st.session_state["_storico_id"] = (_ris_ins.data or [{}])[0].get("id")
            _registra_evento("verifica", modello=_modello_id_eff, verifica_id=st.session_state["_storico_id"])
            # st.toast/st.warning qui si perderebbero con il rerun: li mostra la schermata del risultato
            st.session_state["_toast_dopo"] = ("Salvata in «Le mie verifiche»", "💾")
        except Exception as _e:
            logger.warning(f"Salvataggio storico non riuscito: {_e}")
            st.session_state["_avviso_dopo"] = (
                "La verifica è pronta, ma non sono riuscito a salvarla in «Le mie verifiche»: "
                "scarica subito il PDF."
            )

        # ── IDEA #1: Salva preferenze silenti dopo generazione riuscita ────
        _save_user_defaults_silent(
            materia=materia_scelta, scuola=difficolta,
            num_esercizi=num_esercizi_totali,
            mostra_punteggi=mostra_punteggi,
            punti_totali=punti_totali,
            durata=next((n for n, v in DURATE.items() if v["durata"] == durata_scelta), None),
        )

        # ── Vai alla schermata del risultato (anteprima + download + modifica)
        st.session_state.stage = STAGE_FINAL
        st.rerun()

    except Exception as _e:
        # L'errore si mostra in cima alla pagina, sopra il form (che il rerun ridisegna):
        # sotto il pulsante non si vedrebbe, perché la pagina è scorsa in alto.
        _prog.empty()
        st.session_state["_esito_gen"] = {
            "azione": "Non sono riuscito a creare la verifica", "exc": _e,
        }
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
#  STAGE_INPUT — orchestratore principale
# ═══════════════════════════════════════════════════════════════════════════════


def _render_stage_input():
    # La schermata di creazione e' anche la home: titolo breve + form.
    st.markdown(
        f'<div class="vf-narrow" style="text-align:center;padding:0 0 .2rem;">'
        f'<div style="font-family:DM Sans,sans-serif;font-size:1.55rem;font-weight:800;'
        f'letter-spacing:-.02em;color:{T["text"]};line-height:1.15;">Crea la tua verifica</div>'
        f'<div style="font-size:.84rem;font-weight:400;color:{T["text2"]};margin-top:.15rem;'
        f'font-family:DM Sans,sans-serif;">Scrivi l’argomento: in un minuto la verifica è pronta.</div></div>',
        unsafe_allow_html=True,
    )

    _banner_piano("input")

    # In cima: attesa della generazione ed eventuale errore dell'ultimo tentativo
    _prog_ph_b = st.empty()
    _esito = st.session_state.pop("_esito_gen", None)
    if _esito:
        with _prog_ph_b.container():
            if _esito.get("testo"):          # rifiuto prima di iniziare (limite o conteggio non disponibile)
                messaggio("avviso", _esito["testo"], icon="⚠️")
            else:
                _mostra_errore(
                    _esito["azione"], _esito["exc"],
                    riprova_flag="_riprova_genera", riprova_key="riprova_genera",
                )

    # Il form sta in un contenitore svuotabile: durante la generazione sparisce, così un clic
    # o un tocco per sbaglio non riavvia la pagina e non fa perdere la richiesta.
    _form_ph = st.empty()
    with _form_ph.container():
        (
            argomento, materia_scelta, difficolta,
            mostra_punteggi, con_griglia, punti_totali,
            num_esercizi_totali, note_extra, genera_btn,
            _prog_fac_ph, durata_str, durata_nome,
        ) = _render_percorso_b_form(_prog_ph_b)

    _riprova      = st.session_state.pop("_riprova_genera", False)
    _dopo_analisi = st.session_state.pop("_genera_dopo_analisi", False)
    if not (genera_btn or _riprova or _dopo_analisi) or _limite or _blocco_conteggio:
        return

    # La barra di avanzamento sta in alto: porto la pagina in cima così si vede subito
    components.html(
        "<script>(function(){var d=window.parent.document;"
        "[\"[data-testid='stMain']\",\"section.main\",\"[data-testid='stAppViewContainer']\"]"
        ".forEach(function(q){var e=d.querySelector(q);if(e&&e.scrollTo)e.scrollTo({top:0,behavior:'smooth'});});"
        "window.parent.scrollTo({top:0,behavior:'smooth'});})();</script>",
        height=0,
    )

    # ── Il file viene letto dall'AI solo adesso (1 chiamata, solo se si crea davvero) ──
    _fm    = st.session_state.get("_file_materiale")
    _voce  = next((e for e in st.session_state.analisi_docs_list
                   if _fm and e["file_hash"] == _fm["hash"]), None)
    if _fm and _voce is None:
        st.session_state["_genera_dopo_analisi"] = True
        with _prog_ph_b.container(), st.spinner("Leggo il tuo file…"):
            _esegui_analisi_documento(_fm["bytes"], _fm["mime"], _fm["name"])
        # Se arriviamo qui la lettura non è andata a buon fine (nessun rerun): niente di fatto
        st.session_state.pop("_genera_dopo_analisi", None)
        return

    # ── Applica la scelta fatta sul file ──────────────────────────────────────
    _scelta_mat = None
    if _voce is not None:
        _scelta_mat = st.session_state.get("sel_materiale_b", "base_conoscenza")
        _voce["file_mode"] = _scelta_mat
        _voce["confirmed"] = True
        st.session_state.file_mode = _scelta_mat
        _consolida_info()
        if _scelta_mat == "copia_fedele":
            # «Rifai questa verifica»: numero di esercizi e punti vengono dal file
            st.session_state["_fac_dialog_data"] = {**_voce["analisi"], "file_hash": _voce["file_hash"]}
            st.session_state["_fac_confirmed"] = True
            st.rerun()

    if not argomento:
        st.warning(
            "Non ho capito l'argomento dal file: scrivilo nel riquadro «Cosa vuoi nella verifica?».",
            icon="✍️",
        )
        return

    _note_finale = note_extra

    s_es, imgs_es = _build_prompt_esercizi(
        st.session_state.esercizi_custom,
        num_esercizi_totali,
        punti_totali if mostra_punteggi else 0,
        mostra_punteggi,
    )

    # ── Estrai file "includi_esercizio" → vision input ─────────────────────
    # I file marcati come "esercizio da inserire" vengono passati come immagini
    # al modello vision affinché l'esercizio compaia OBBLIGATORIAMENTE nell'output.
    _imgs_esercizio: list = []
    _note_esercizi_inclusi: list = []
    for _idx_fe, _fe in enumerate(st.session_state.analisi_docs_list):
        if _fe.get("file_mode") == "includi_esercizio":
            _fb = _fe.get("file_bytes")
            _fm = _fe.get("mime_type", "image/png")
            if _fb:
                _imgs_esercizio.append({
                    "idx":       _idx_fe + 1,
                    "data":      _fb,
                    "mime_type": _fm,
                })
            _istr_fe = st.session_state.istruzioni_per_file.get(str(_fe["file_hash"]), "").strip()
            _nota_fe = f"File '{_fe['file_name']}' — esercizio da includere obbligatoriamente"
            if _istr_fe:
                _nota_fe += f": {_istr_fe}"
            _note_esercizi_inclusi.append(_nota_fe)

    # Combina immagini: prima quelle da includi_esercizio, poi quelle da esercizi_custom
    imgs_es_finale = _imgs_esercizio + imgs_es

    # Aggiungi alle note generali le istruzioni per gli esercizi obbligatori
    if _note_esercizi_inclusi:
        _nota_includi = (
            "\n\n╔═══════════════════════════════════════════════╗\n"
            "║ ⚠️ ESERCIZI DA INCLUDERE OBBLIGATORIAMENTE     ║\n"
            "╚═══════════════════════════════════════════════╝\n"
            + "\n".join(_note_esercizi_inclusi)
            + "\nL'immagine allegata contiene l'esercizio. Trascrivilo fedelmente in LaTeX "
            "come Esercizio 1 e genera gli esercizi restanti normalmente."
        )
        _note_finale = (_note_finale + _nota_includi).strip() if _note_finale else _nota_includi.strip()
    else:
        imgs_es_finale = imgs_es

    _form_ph.empty()   # da qui il form non c'è più: resta solo la card di attesa
    _lancia_generazione(
        materia_scelta=materia_scelta,
        argomento=argomento,
        difficolta=difficolta,
        durata_scelta=durata_str,
        num_esercizi_totali=num_esercizi_totali,
        punti_totali=punti_totali,
        mostra_punteggi=mostra_punteggi,
        con_griglia=con_griglia,
        note_generali=_note_finale,
        s_es=s_es,
        imgs_es=imgs_es_finale,
        # «Prendi spunto dai miei appunti»: il file viene davvero allegato alla richiesta
        file_ispirazione=(_FileInMemoria(_fm["bytes"], _fm["mime"], _fm["name"])
                          if (_scelta_mat == "base_conoscenza" and _fm) else None),
        prog_placeholder=_prog_ph_b,
    )
    return



# ═══════════════════════════════════════════════════════════════════════════════
#  STAGE_REVIEW
# ═══════════════════════════════════════════════════════════════════════════════

def _ricompila_verifica_a(mostra_punteggi: bool, con_griglia: bool, punti_totali: int,
                          riscala_totale: bool = False, punti_custom: list | None = None,
                          rileggi_blocchi: bool = False, blocco_modificato: int | None = None):
    """
    Ricostruisce il LaTeX della Fila A da review_blocks, applica il post-processing
    deterministico (_postprocessa_latex), compila il PDF e aggiorna session_state
    (latex, pdf, anteprima).

    riscala_totale=True ridistribuisce i punti su tutta la verifica (serve quando cambia
    il numero di esercizi o si confermano i punteggi); in tal caso review_blocks viene
    riletto dal LaTeX risultante (lo stesso succede con rileggi_blocchi=True).
    punti_custom: punti per esercizio scelti dal docente.
    blocco_modificato: indice dell'esercizio appena riscritto; se il totale non torna a
    punti_totali, è lui ad assorbire la differenza (gli altri esercizi non cambiano).
    Ritorna (pdf_bytes | None, errore).
    """
    if mostra_punteggi and blocco_modificato is not None:
        _bl = st.session_state.review_blocks
        if 0 <= blocco_modificato < len(_bl):
            _altri = sum(parse_pts_from_block_body(b["body"])
                         for j, b in enumerate(_bl) if j != blocco_modificato)
            _serve = punti_totali - _altri
            _mod = _bl[blocco_modificato]
            _pts_mod = parse_pts_from_block_body(_mod["body"])
            if _serve > 0 and _pts_mod == 0:
                # la risposta AI non ha punteggi: li assegno io (divisi in parti uguali)
                _n_item = len(re.findall(r"\\item\b", _mod["body"]))
                if _n_item:
                    _mod["body"] = apply_item_pts_to_body(
                        _mod["body"], bilancia_punti([1] * _n_item, _serve))
                else:
                    _mod["body"] = _mod["body"].rstrip() + f" ({_serve} pt)"
            elif _serve > 0 and _pts_mod != _serve:
                _mod["body"] = riscala_single_block(_mod["title"], _mod["body"], _serve)
    # Difesa: un \end{document} dentro un esercizio taglierebbe tutti i successivi.
    for _b in st.session_state.review_blocks:
        _b["body"] = re.sub(r"\s*\\end\{document\}.*$", "", _b["body"], flags=re.DOTALL)
    latex = reconstruct_latex(
        st.session_state.review_preamble, st.session_state.review_blocks,
    )
    latex = _postprocessa_latex(
        latex, mostra_punteggi, punti_totali,
        riscala_totale=riscala_totale, punti_custom=punti_custom, con_griglia=con_griglia,
    )

    va = st.session_state.verifiche["A"]
    latex_prima = va.get("latex")
    # Compila prima: se un grafico esce rotto (errori TikZ) viene sostituito da un segnaposto
    # e il LaTeX effettivo cambia.
    latex_inviato = latex
    pdf, err, latex = compila_pdf_sicuro(latex)
    va["latex"] = va["latex_originale"] = latex
    # Fila B, BES/DSA, Soluzioni e Word derivano dalla Fila A: se la A è cambiata non sono più
    # coerenti (es. un esercizio eliminato tornerebbe nella versione BES) e vanno rifatte.
    if pdf and latex_prima and latex != latex_prima and any(
        (st.session_state.verifiche.get(f) or {}).get("latex") for f in ("B", "R", "RB", "S", "SC")
    ):
        for _f in ("B", "R", "RB"):
            st.session_state.verifiche[_f] = _vf()
        st.session_state.verifiche["S"] = {"latex": None, "testo": None, "pdf": None}
        st.session_state.verifiche["SC"] = {"latex": None, "pdf": None, "n": 0, "avvisi": []}
        va["docx"] = None
        st.session_state.rubrica_testo = None
        st.session_state["_rubrica_docx"] = None
        st.session_state["_avviso_dopo"] = (
            "Hai modificato la verifica: Fila B, BES/DSA, Soluzioni e scheda di allenamento già create "
            "non valgono più e vanno rigenerate dalla nuova versione."
        )
    # Se i punti sono stati ridistribuiti o un grafico è stato sostituito, i blocchi vanno
    # riletti dal LaTeX finale (altrimenti l'editor mostrerebbe i valori vecchi).
    if latex != latex_inviato:
        rileggi_blocchi = True
    if mostra_punteggi and not (riscala_totale or rileggi_blocchi):
        rileggi_blocchi = sum(parse_pts_from_block_body(b["body"])
                              for b in st.session_state.review_blocks) != punti_totali
    if riscala_totale or rileggi_blocchi:
        _pre, _blocchi = extract_blocks(latex)
        if _blocchi:
            st.session_state.review_preamble = _pre
            st.session_state.review_blocks   = _blocchi

    if pdf:
        va["pdf"]     = pdf
        va["pdf_ts"]  = time.time()
        va["preview"] = True
        imgs, _ = pdf_to_images_bytes(pdf)
        st.session_state.preview_images  = imgs or []
        st.session_state.preview_page    = 0
        st.session_state.last_preview_ts = va["pdf_ts"]   # anteprima già allineata al PDF
    return pdf, err


def _applica_punti_a_blocchi(righe: list, punti: list) -> None:
    """
    Scrive in review_blocks i punti scelti nella tabella "Cambia i punteggi".
    righe[k] = (indice esercizio, indice sottopunto); punti[k] = punti di quella riga.
    Il titolo di ogni esercizio riporta il subtotale.
    """
    per_esercizio: dict = {}
    for (i, j), v in zip(righe, punti):
        per_esercizio.setdefault(i, {})[j] = v
    for i, valori in per_esercizio.items():
        lista = [valori[j] for j in sorted(valori)]
        blocco = st.session_state.review_blocks[i]
        blocco["body"] = apply_item_pts_to_body(blocco["body"], lista)
        titolo = re.sub(r"\s*\(\d+\s*pt\)", "", blocco["title"]).strip()
        blocco["title"] = f"{titolo} ({sum(lista)} pt)"


def _pulisci_stato_revisione():
    """Cancella i valori per-esercizio (punteggi, undo, conferme) quando cambia la struttura."""
    for _k in list(st.session_state.keys()):
        if (_k.startswith("item_pt_") or _k.startswith("_undo_block_")
                or _k in ("recalibra_pts", "_conf_elimina", "review_selectbox")):
            del st.session_state[_k]


def _rigenera_esercizio_guidato(idx, istruzione, etichetta, materia, argomento, modello,
                                mostra_punteggi, con_griglia, punti_totali, status_ph):
    """
    "Più facile" / "Più difficile": rigenera un solo esercizio con un'istruzione fissa
    (rigenera_singolo_blocco → prompt_rigenera_blocco), riporta i punti all'originale,
    ricompila il PDF. Il backup per "Annulla modifica" è salvato prima della chiamata.
    """
    blocchi = st.session_state.review_blocks
    n_blocks = len(blocchi)
    title, body = blocchi[idx]["title"], blocchi[idx]["body"]
    _pts = st.session_state.get("recalibra_pts", [])
    target = int(_pts[idx]) if _pts and len(_pts) == n_blocks else parse_pts_from_block_body(body)

    st.session_state[f"_undo_block_{idx}"] = dict(blocchi[idx])
    with status_ph.status(f"{etichetta} l'esercizio {idx+1}…", expanded=True) as stato:
        try:
            nuovo = rigenera_singolo_blocco(
                crea_modello(modello).per("modifica"), materia,
                f"\\subsection*{{{title}}}\n{body}", istruzione, mostra_punteggi,
            )
            # rigenera_singolo_blocco ripulisce la risposta con pulisci_corpo_latex, che in
            # coda aggiunge \end{document}: va tolto, altrimenti la verifica finirebbe
            # a questo esercizio e quelli successivi sparirebbero dal PDF.
            nuovo = re.sub(r"\\end\{document\}.*$", "", nuovo, flags=re.DOTALL).strip()
            m = re.match(r"\\subsection\*\{([^}]*)\}(.*)", nuovo, re.DOTALL)
            new_title = m.group(1) if m else title
            new_body  = m.group(2).strip() if m else nuovo.strip()
            new_title = re.sub(r"\s*\(\d+\s*pt\)", "", new_title).strip() or title
            # Se il titolo originale era numerato ("Esercizio 3: …") e la risposta no, lo ripristina
            _pref = re.match(r"^(Esercizio\s*\d+\s*[:.\-]\s*)", title, flags=re.IGNORECASE)
            if _pref and not re.match(r"^Esercizio\s*\d+", new_title, flags=re.IGNORECASE):
                new_title = _pref.group(1) + new_title
            if mostra_punteggi and target > 0:
                new_body = riscala_single_block(new_title, new_body, target)
            blocchi[idx]["title"] = new_title
            blocchi[idx]["body"]  = new_body
            st.session_state.pop("recalibra_pts", None)

            pdf, err = _ricompila_verifica_a(mostra_punteggi, con_griglia, punti_totali, blocco_modificato=idx)
            if not pdf:
                stato.update(label="PDF non aggiornato", state="error", expanded=False)
                _mostra_errore(
                    "Ho modificato l'esercizio ma non sono riuscito a rifare il PDF", err,
                    consiglio="Premi «Annulla modifica» per tornare indietro, poi riprova.",
                )
                return
            stato.update(label="Esercizio aggiornato!", state="complete", expanded=False)
            st.toast(f"Esercizio {idx+1} aggiornato!", icon="✅")
            st.rerun()
        except Exception as e:
            stato.update(label="Modifica non riuscita", state="error", expanded=False)
            _mostra_errore("Non sono riuscito a modificare questo esercizio", e)


def _elimina_esercizio(idx, mostra_punteggi, con_griglia, punti_totali) -> bool:
    """
    Elimina un esercizio, rinumera i titoli, ridistribuisce i punti sul totale e
    ricompila. Se il PDF non si compila ripristina lo stato precedente.
    """
    backup_blocchi = copy.deepcopy(st.session_state.review_blocks)
    backup_pre     = st.session_state.review_preamble
    va             = st.session_state.verifiche["A"]
    backup_latex   = (va.get("latex"), va.get("latex_originale"))

    blocchi = st.session_state.review_blocks
    del blocchi[idx]
    for i, b in enumerate(blocchi):
        b["title"] = re.sub(
            r"^(Esercizio\s*)\d+", lambda m, n=i + 1: f"{m.group(1)}{n}",
            b["title"], flags=re.IGNORECASE,
        )
    pdf, err = _ricompila_verifica_a(mostra_punteggi, con_griglia, punti_totali, riscala_totale=True)
    if not pdf:
        st.session_state.review_blocks   = backup_blocchi
        st.session_state.review_preamble = backup_pre
        va["latex"], va["latex_originale"] = backup_latex
        _mostra_errore_pdf(err, "questa verifica")
        return False
    _pulisci_stato_revisione()
    st.session_state.review_sel_idx = min(idx, len(st.session_state.review_blocks) - 1)
    st.session_state.gen_params["num_esercizi"] = len(st.session_state.review_blocks)
    st.session_state.force_preview_refresh = True
    return True


def _aggiungi_esercizio(mostra_punteggi, con_griglia, punti_totali, materia, argomento,
                        scuola, modello) -> bool:
    """
    Aggiunge in fondo un esercizio nuovo (stesso argomento, diverso dagli altri), ridistribuisce
    i punti sul totale e ricompila. Se qualcosa va storto ripristina lo stato precedente.
    """
    blocchi = st.session_state.review_blocks
    n = len(blocchi)
    if n >= 15:
        st.warning("Una verifica può avere al massimo 15 esercizi.", icon="⚠️")
        return False
    esistenti = "\n".join(f"- {b['title']}: {b['body'][:160].strip()}…" for b in blocchi)
    prompt = prompt_nuovo_esercizio(
        materia, argomento, scuola, esistenti, n + 1, mostra_punteggi,
        max(5, punti_totali // (n + 1)),
    )
    backup_blocchi = copy.deepcopy(blocchi)
    backup_pre     = st.session_state.review_preamble
    va             = st.session_state.verifiche["A"]
    backup_latex   = (va.get("latex"), va.get("latex_originale"))
    try:
        testo = crea_modello(modello).per("modifica").generate_content(prompt).text
        testo = testo.replace("```latex", "").replace("```", "").strip()
        testo = re.sub(r"\\end\{document\}.*$", "", testo, flags=re.DOTALL).strip()
        m = re.match(r"\\subsection\*\{([^}]*)\}(.*)", testo, re.DOTALL)
        titolo = re.sub(r"\s*\(\d+\s*pt\)", "", m.group(1)).strip() if m else f"Esercizio {n + 1}"
        corpo = m.group(2).strip() if m else testo
        if not re.match(r"^Esercizio\s*\d+", titolo, flags=re.IGNORECASE):
            titolo = f"Esercizio {n + 1}: {titolo}"
        blocchi.append({"title": titolo, "body": corpo})
        pdf, err = _ricompila_verifica_a(mostra_punteggi, con_griglia, punti_totali, riscala_totale=True)
    except Exception as e:
        pdf, err = None, e
    if not pdf:
        st.session_state.review_blocks   = backup_blocchi
        st.session_state.review_preamble = backup_pre
        va["latex"], va["latex_originale"] = backup_latex
        _mostra_errore("Non sono riuscito ad aggiungere l'esercizio", err,
                       consiglio="Non ho cambiato nulla: riprova.")
        return False
    _pulisci_stato_revisione()
    st.session_state.review_sel_idx = len(st.session_state.review_blocks) - 1
    st.session_state.gen_params["num_esercizi"] = len(st.session_state.review_blocks)
    st.session_state.force_preview_refresh = True
    return True


def _render_stage_review():
    gp              = st.session_state.gen_params
    blocks          = st.session_state.review_blocks
    materia_str     = gp.get("materia","")
    scuola_str      = gp.get("difficolta","")
    argomento_str   = gp.get("argomento","Verifica")
    mostra_punteggi = gp.get("mostra_punteggi", True)
    punti_totali    = gp.get("punti_totali", 100)
    con_griglia     = gp.get("con_griglia", False)
    modello_rw      = gp.get("modello_id", modello_id)
    n_blocks        = len(blocks)

    # ── Iniezione CSS diretta: risolve expander neri + bottoni problematici ──
    # Questa tecnica (style tag inline) bypassa i limiti di specificità di Streamlit
    # che altrimenti sovrascrive con color-scheme:dark e --background-color nero.
    st.markdown(f"""
<style>
/* ── EXPANDER: header + content area ─────────────────────────────────── */
html body div[data-testid="stAppViewContainer"] details[data-testid="stExpander"],
html body .stApp details[data-testid="stExpander"] {{
  background: {T["card"]} !important;
  background-color: {T["card"]} !important;
  border: 2px solid {T["border2"]} !important;
  border-radius: 14px !important;
  overflow: hidden !important;
  margin-bottom: .5rem !important;
  color-scheme: light !important;
  --background-color: {T["card"]} !important;
}}
html body div[data-testid="stAppViewContainer"] details[data-testid="stExpander"] > summary,
html body .stApp details[data-testid="stExpander"] > summary {{
  background: {T["card"]} !important;
  background-color: {T["card"]} !important;
  color: {T["text"]} !important;
  -webkit-text-fill-color: {T["text"]} !important;
  font-family: 'DM Sans', sans-serif !important;
  font-weight: 700 !important;
  font-size: .9rem !important;
  padding: .85rem 1.1rem !important;
  border-radius: 12px !important;
  color-scheme: light !important;
}}
html body div[data-testid="stAppViewContainer"] details[data-testid="stExpander"] > summary *,
html body .stApp details[data-testid="stExpander"] > summary span,
html body .stApp details[data-testid="stExpander"] > summary p,
html body .stApp details[data-testid="stExpander"] > summary div {{
  color: {T["text"]} !important;
  -webkit-text-fill-color: {T["text"]} !important;
  background: transparent !important;
}}
html body div[data-testid="stAppViewContainer"] details[data-testid="stExpander"] > summary svg *,
html body .stApp details[data-testid="stExpander"] > summary svg * {{
  fill: {T["text2"]} !important;
  stroke: {T["text2"]} !important;
}}
/* Summary APERTO */
html body div[data-testid="stAppViewContainer"] details[data-testid="stExpander"][open] > summary,
html body .stApp details[data-testid="stExpander"][open] > summary {{
  background: linear-gradient(135deg, {T["accent"]} 0%, {T["accent2"]} 100%) !important;
  background-color: {T["accent"]} !important;
  color: #fff !important;
  -webkit-text-fill-color: #fff !important;
  border-radius: 12px 12px 0 0 !important;
  color-scheme: light !important;
}}
html body div[data-testid="stAppViewContainer"] details[data-testid="stExpander"][open] > summary *,
html body .stApp details[data-testid="stExpander"][open] > summary span,
html body .stApp details[data-testid="stExpander"][open] > summary p,
html body .stApp details[data-testid="stExpander"][open] > summary div {{
  color: #fff !important;
  -webkit-text-fill-color: #fff !important;
  background: transparent !important;
}}
html body div[data-testid="stAppViewContainer"] details[data-testid="stExpander"][open] > summary svg *,
html body .stApp details[data-testid="stExpander"][open] > summary svg * {{
  fill: #fff !important;
  stroke: #fff !important;
}}
/* Content div */
html body div[data-testid="stAppViewContainer"] details[data-testid="stExpander"] > div,
html body .stApp details[data-testid="stExpander"] > div,
html body .stApp details[data-testid="stExpander"] > div[data-testid="stExpanderDetails"] {{
  background: {T["card"]} !important;
  background-color: {T["card"]} !important;
  --background-color: {T["card"]} !important;
  color-scheme: light !important;
  padding: 1rem 1.1rem 1.2rem !important;
  border-radius: 0 0 12px 12px !important;
}}
html body .stApp details[data-testid="stExpander"] > div * {{
  color-scheme: light !important;
}}
html body .stApp details[data-testid="stExpander"] > div p,
html body .stApp details[data-testid="stExpander"] > div label,
html body .stApp details[data-testid="stExpander"] > div span:not(.site-header-ai),
html body .stApp details[data-testid="stExpander"] > div small {{
  color: {T["text"]} !important;
  -webkit-text-fill-color: {T["text"]} !important;
}}
/* Pulsanti dentro expander */
html body .stApp details[data-testid="stExpander"] .stButton > button {{
  background: {T["card"]} !important;
  background-color: {T["card"]} !important;
  color: {T["text"]} !important;
  -webkit-text-fill-color: {T["text"]} !important;
  border: 1.5px solid {T["border2"]} !important;
  border-radius: 10px !important;
  color-scheme: light !important;
}}
html body .stApp details[data-testid="stExpander"] .stButton > button:hover {{
  background: {T["hover"]} !important;
  background-color: {T["hover"]} !important;
  color: {T["accent"]} !important;
  -webkit-text-fill-color: {T["accent"]} !important;
  border-color: {T["accent"]} !important;
}}
html body .stApp details[data-testid="stExpander"] .stButton > button[kind="primary"],
html body .stApp details[data-testid="stExpander"] .stButton > button[data-testid*="primary"] {{
  background: linear-gradient(135deg, {T["accent"]} 0%, {T["accent2"]} 100%) !important;
  background-color: {T["accent"]} !important;
  color: #fff !important;
  -webkit-text-fill-color: #fff !important;
  border-color: transparent !important;
  box-shadow: 0 3px 14px {T["accent"]}44 !important;
}}
/* Input/textarea dentro expander */
html body .stApp details[data-testid="stExpander"] input,
html body .stApp details[data-testid="stExpander"] textarea {{
  background: {T["bg2"]} !important;
  background-color: {T["bg2"]} !important;
  color: {T["text"]} !important;
  -webkit-text-fill-color: {T["text"]} !important;
  border: 1.5px solid {T["border"]} !important;
  color-scheme: light !important;
}}
/* NumberInput +/- buttons */
html body .stApp details[data-testid="stExpander"] [data-testid="stNumberInput"] button {{
  background: {T["bg2"]} !important;
  background-color: {T["bg2"]} !important;
  color: {T["text"]} !important;
  -webkit-text-fill-color: {T["text"]} !important;
  color-scheme: light !important;
}}

/* ── Coppia pulsanti azioni esercizio (Genera variante + Cambia esercizio)
   Entrambi usano lo stile outline-accent: bordo teal, sfondo trasparente.
   Il marker .btn-outline-accent-marker è inserito prima di CIASCUN button.
   ─────────────────────────────────────────────────────────────────────── */
[data-testid="stVerticalBlock"] > div:has(.btn-outline-accent-marker) + div button,
.element-container:has(.btn-outline-accent-marker) + .element-container button {{
  background: transparent !important;
  background-color: transparent !important;
  color: {T["accent"]} !important;
  -webkit-text-fill-color: {T["accent"]} !important;
  border: 1.5px solid {T["accent"]} !important;
  border-radius: 10px !important;
  font-weight: 700 !important;
  font-size: .88rem !important;
  min-height: 48px !important;
  box-shadow: none !important;
  color-scheme: light !important;
}}
[data-testid="stVerticalBlock"] > div:has(.btn-outline-accent-marker) + div button:hover,
.element-container:has(.btn-outline-accent-marker) + .element-container button:hover {{
  background: {T["accent_light"]} !important;
  background-color: {T["accent_light"]} !important;
  color: {T["accent"]} !important;
  -webkit-text-fill-color: {T["accent"]} !important;
  box-shadow: 0 2px 12px {T["accent"]}22 !important;
}}
</style>""", unsafe_allow_html=True)

    # ── JS DOM injection: unico modo affidabile per battere gli inline style
    # di Streamlit sul <summary>. window.parent.document accede al DOM reale.
    _c_card    = T["card"]
    _c_text    = T["text"]
    _c_text2   = T["text2"]
    _c_accent  = T["accent"]
    _c_accent2 = T["accent2"]
    _c_border2 = T["border2"]
    _c_bg2     = T["bg2"]
    components.html(f"""
<script>
(function() {{
  var doc = window.parent.document;

  function applyExpanderStyles() {{
    doc.querySelectorAll('details[data-testid="stExpander"]').forEach(function(exp) {{
      // Container
      exp.style.setProperty('background', '{_c_card}', 'important');
      exp.style.setProperty('background-color', '{_c_card}', 'important');
      exp.style.setProperty('border', '2px solid {_c_border2}', 'important');
      exp.style.setProperty('border-radius', '14px', 'important');
      exp.style.setProperty('overflow', 'hidden', 'important');
      exp.style.setProperty('margin-bottom', '.5rem', 'important');

      // Summary
      var summary = exp.querySelector(':scope > summary');
      if (summary) {{
        if (exp.open) {{
          summary.style.setProperty('background', 'linear-gradient(135deg,{_c_accent} 0%,{_c_accent2} 100%)', 'important');
          summary.style.setProperty('background-color', '{_c_accent}', 'important');
          summary.style.setProperty('color', '#ffffff', 'important');
          summary.style.setProperty('-webkit-text-fill-color', '#ffffff', 'important');
          summary.style.setProperty('border-radius', '12px 12px 0 0', 'important');
        }} else {{
          summary.style.setProperty('background', '{_c_card}', 'important');
          summary.style.setProperty('background-color', '{_c_card}', 'important');
          summary.style.setProperty('color', '{_c_text}', 'important');
          summary.style.setProperty('-webkit-text-fill-color', '{_c_text}', 'important');
          summary.style.setProperty('border-radius', '12px', 'important');
        }}
        summary.style.setProperty('font-family', 'DM Sans, sans-serif', 'important');
        summary.style.setProperty('font-weight', '700', 'important');
        summary.style.setProperty('font-size', '.9rem', 'important');
        summary.style.setProperty('padding', '.85rem 1.1rem', 'important');

        // Summary children text
        summary.querySelectorAll('span, p, div').forEach(function(el) {{
          if (exp.open) {{
            el.style.setProperty('color', '#ffffff', 'important');
            el.style.setProperty('-webkit-text-fill-color', '#ffffff', 'important');
          }} else {{
            el.style.setProperty('color', '{_c_text}', 'important');
            el.style.setProperty('-webkit-text-fill-color', '{_c_text}', 'important');
          }}
          el.style.setProperty('background', 'transparent', 'important');
        }});

        // SVG arrow
        summary.querySelectorAll('svg, svg *').forEach(function(el) {{
          if (exp.open) {{
            el.style.setProperty('fill', '#ffffff', 'important');
            el.style.setProperty('stroke', '#ffffff', 'important');
          }} else {{
            el.style.setProperty('fill', '{_c_text2}', 'important');
            el.style.setProperty('stroke', '{_c_text2}', 'important');
          }}
        }});

        // Re-apply on toggle
        if (!exp.__toggleBound) {{
          exp.__toggleBound = true;
          exp.addEventListener('toggle', function() {{
            setTimeout(applyExpanderStyles, 10);
          }});
        }}
      }}

      // Content div
      var contentDiv = exp.querySelector(':scope > div');
      if (contentDiv) {{
        contentDiv.style.setProperty('background', '{_c_card}', 'important');
        contentDiv.style.setProperty('background-color', '{_c_card}', 'important');
        contentDiv.style.setProperty('padding', '1rem 1.1rem 1.2rem', 'important');
        contentDiv.style.setProperty('border-radius', '0 0 12px 12px', 'important');
        // Text inside content
        contentDiv.querySelectorAll('p, label, span:not([class*="site-header"]), small').forEach(function(el) {{
          el.style.setProperty('color', '{_c_text}', 'important');
          el.style.setProperty('-webkit-text-fill-color', '{_c_text}', 'important');
        }});
        // Inputs/textarea inside content
        contentDiv.querySelectorAll('input, textarea').forEach(function(el) {{
          el.style.setProperty('background', '{_c_bg2}', 'important');
          el.style.setProperty('background-color', '{_c_bg2}', 'important');
          el.style.setProperty('color', '{_c_text}', 'important');
          el.style.setProperty('-webkit-text-fill-color', '{_c_text}', 'important');
          el.style.setProperty('border', '1.5px solid {_c_border2}', 'important');
        }});
        // Buttons inside content (secondary)
        contentDiv.querySelectorAll('.stButton > button').forEach(function(btn) {{
          if (!btn.dataset.kind || btn.dataset.kind !== 'primary') {{
            btn.style.setProperty('background', '{_c_card}', 'important');
            btn.style.setProperty('background-color', '{_c_card}', 'important');
            btn.style.setProperty('color', '{_c_text}', 'important');
            btn.style.setProperty('-webkit-text-fill-color', '{_c_text}', 'important');
            btn.style.setProperty('border', '1.5px solid {_c_border2}', 'important');
            btn.style.setProperty('border-radius', '10px', 'important');
          }}
        }});
      }}
    }});
  }}

  // Run immediately
  applyExpanderStyles();

  // Watch for any DOM changes (Streamlit re-renders)
  var observer = new MutationObserver(function(mutations) {{
    var relevant = mutations.some(function(m) {{
      return Array.from(m.addedNodes).some(function(n) {{
        return n.nodeType === 1 && (n.matches && n.matches('details') ||
               (n.querySelector && n.querySelector('details[data-testid="stExpander"]') !== null));
      }});
    }});
    if (relevant) applyExpanderStyles();
  }});
  observer.observe(doc.body, {{ childList: true, subtree: true }});
}})();
</script>
""", height=0, scrolling=False)

    st.markdown(
        f'<div style="text-align:center;margin:.2rem 0 1rem;">'
        f'<div style="font-family:DM Sans,sans-serif;font-size:1.7rem;font-weight:800;'
        f'color:{T["text"]};letter-spacing:-.025em;line-height:1.15;">Modifica gli esercizi</div>'
        f'<div style="font-size:.9rem;color:{T["text2"]};font-family:DM Sans,sans-serif;margin-top:.35rem;">'
        f'{_esc(materia_str)} · {_esc(scuola_str)} · {_esc(argomento_str)} · {n_blocks} esercizi<br>'
        f'Ogni modifica rifà subito il PDF: quando hai finito torna al download.</div></div>',
        unsafe_allow_html=True
    )

    if not blocks:
        st.warning("⚠️ Nessun esercizio trovato. Torna indietro e rigenera.")
        if st.button("← Torna alla configurazione",
                     help="Torna al form di configurazione per cambiare materia, argomento o numero di esercizi."):
            st.session_state.stage = STAGE_INPUT; st.rerun()
        return

    # Rimuovi il prefisso "Esercizio N:" o "Esercizio N. " già presente nel titolo
    def _clean_title(title: str) -> str:
        return re.sub(r'^Esercizio\s*\d+\s*[:\.\-]\s*', '', title, flags=re.IGNORECASE).strip()

    labels = [f"Esercizio {i+1}: {_clean_title(b['title'])}" for i, b in enumerate(blocks)]

    idx = st.session_state.review_sel_idx
    if idx >= n_blocks: idx = 0

    # ◀ ▶ per scorrere gli esercizi; la tendina resta per saltare a uno qualsiasi
    _rv_p, _rv_s, _rv_n = st.columns([1, 7, 1], vertical_alignment="bottom", gap="small")
    with _rv_p:
        if st.button("◀", key="rev_prec", use_container_width=True, disabled=(idx <= 0),
                     help="Esercizio precedente"):
            st.session_state["review_selectbox"] = labels[idx - 1]
            st.session_state.review_sel_idx = idx - 1
            st.rerun()
    with _rv_n:
        if st.button("▶", key="rev_succ", use_container_width=True, disabled=(idx >= n_blocks - 1),
                     help="Esercizio successivo"):
            st.session_state["review_selectbox"] = labels[idx + 1]
            st.session_state.review_sel_idx = idx + 1
            st.rerun()
    with _rv_s:
        sel_label = st.selectbox(
            "Esercizio da modificare",
            labels, index=idx, key="review_selectbox"
        )
    idx = labels.index(sel_label)
    st.session_state.review_sel_idx = idx

    # ── Badge punteggio totale calcolato live ─────────────────────────────────
    if mostra_punteggi:
        _latex_live = reconstruct_latex(
            st.session_state.review_preamble,
            st.session_state.review_blocks,
        )
        _totale_live = conta_punti_latex(_latex_live)
        _ok   = _totale_live == punti_totali
        _diff = _totale_live - punti_totali
        _icon  = "✅" if _ok else ("⬆️" if _diff > 0 else "⬇️")
        _color = T["success"] if _ok else T["warn"]
        _label = f"{_totale_live} pt" if _ok else f"{_totale_live} pt ({_diff:+d} pt rispetto al target)"
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:10px;'
            f'background:{_color}18;border:1.5px solid {_color}44;'
            f'border-radius:10px;padding:.5rem 1rem;margin-bottom:.6rem;">'
            f'<span style="font-size:1rem;">{_icon}</span>'
            f'<span style="font-family:\'DM Sans\',sans-serif;font-size:.88rem;'
            f'font-weight:700;color:{_color};">'
            f'Punteggio totale calcolato: <strong>{_label}</strong>'
            f'</span>'
            f'<span style="font-size:.8rem;color:{T["muted"]};margin-left:auto;">'
            f'Target: {punti_totali} pt'
            f'</span></div>',
            unsafe_allow_html=True,
        )
        if not _ok:
            logger.info(
                "STAGE_REVIEW: totale live=%d pt, target=%d pt, diff=%+d pt",
                _totale_live, punti_totali, _diff,
            )

    block = blocks[idx]
    title = block["title"]
    body  = block["body"]

    # ══════════════════════════════════════════════════════════════════════════
    #  LAYOUT DUE COLONNE
    #  Sinistra [2]: box unico — KaTeX + azioni esercizio + Altre modifiche
    #  Destra   [3]: anteprima PDF una pagina alla volta con navigazione ◀▶
    # ══════════════════════════════════════════════════════════════════════════
    col_left, col_pdf = st.columns([2, 3], gap="medium")

    # ── COLONNA SINISTRA ──────────────────────────────────────────────────────
    with col_left:
        with st.container(border=True):

            # ── Anteprima KaTeX dell'esercizio selezionato ───────────────────
            katex_html = _make_katex_html(title, body, T)
            est_height = max(220, min(550, 160 + len(body) // 4))
            components.html(katex_html, height=est_height, scrolling=True)

            if re.search(r"\\begin\{(tikzpicture|axis)\}", body):
                st.info("📊 Questo esercizio contiene un grafico — sarà visibile nel PDF scaricato.")
            elif idx in esercizi_con_grafico_mancante(blocks):
                st.warning(
                    "Questo esercizio rimanda a un grafico che non è stato disegnato. "
                    "Premi «Cambia esercizio» per riprovare, oppure correggi il testo in «Altre modifiche».",
                    icon="📉",
                )

            # ── Pulsante ANNULLA MODIFICA ─────────────────────────────────
            _undo_key = f"_undo_block_{idx}"
            if _undo_key in st.session_state:
                _undo_backup = st.session_state[_undo_key]
                _undo_col1, _undo_col2 = st.columns([1, 2])
                with _undo_col1:
                    st.markdown(
                        f'''<style>
  [data-testid="stVerticalBlock"] > div:has(.undo-btn-marker) + div > div > button,
  [data-testid="stVerticalBlock"] > div:has(.undo-btn-marker) + div button {{
    background: transparent !important;
    background-color: transparent !important;
    color: {T["accent"]} !important;
    -webkit-text-fill-color: {T["accent"]} !important;
    border: 1.5px solid {T["accent"]} !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    box-shadow: none !important;
  }}
  [data-testid="stVerticalBlock"] > div:has(.undo-btn-marker) + div > div > button:hover,
  [data-testid="stVerticalBlock"] > div:has(.undo-btn-marker) + div button:hover {{
    background: {T["accent_light"]} !important;
    background-color: {T["accent_light"]} !important;
    color: {T["accent2"]} !important;
    -webkit-text-fill-color: {T["accent2"]} !important;
  }}
</style>
<div class="undo-btn-marker" style="display:none;height:0;line-height:0"></div>''',
                        unsafe_allow_html=True
                    )
                    if st.button(
                        "↩️ Annulla modifica",
                        key=f"undo_btn_{idx}",
                        use_container_width=True,
                        help="Ripristina la versione dell'esercizio precedente alla modifica"
                    ):
                        st.session_state.review_blocks[idx] = dict(_undo_backup)
                        del st.session_state[_undo_key]
                        # Pulisci item_pt_ keys per questo esercizio
                        for _k in list(st.session_state.keys()):
                            if _k.startswith(f"item_pt_{idx}_"):
                                del st.session_state[_k]
                        if "recalibra_pts" in st.session_state:
                            del st.session_state["recalibra_pts"]
                        _undo_pdf, _undo_err = _ricompila_verifica_a(
                            mostra_punteggi, con_griglia, punti_totali, riscala_totale=True,
                        )
                        if _undo_pdf:
                            st.toast("↩️ Modifica annullata — versione precedente ripristinata!", icon="↩️")
                            st.rerun()
                        else:
                            _mostra_errore_pdf(_undo_err, "questa verifica")
                with _undo_col2:
                    st.markdown(
                        f'<div style="font-size:.72rem;color:{T["muted"]};font-family:DM Sans,sans-serif;'
                        f'padding:.3rem 0;line-height:1.4;">'
                        f'🕐 Versione precedente disponibile</div>',
                        unsafe_allow_html=True
                    )

            # ── Azioni sull'esercizio: rigenera, numeri, più facile/difficile, elimina ──
            _marker = '<div class="btn-outline-accent-marker" style="display:none;height:0;line-height:0"></div>'
            # Prima ciò che si usa più spesso (livello), poi le sostituzioni, in fondo l'azione distruttiva
            _lv_col1, _lv_col2 = st.columns(2, gap="small")
            with _lv_col1:
                st.markdown(_marker, unsafe_allow_html=True)
                piu_facile = st.button(
                    "Più facile", key=f"piu_facile_{idx}", use_container_width=True,
                    help="Semplifica numeri e calcoli, mantenendo lo stesso argomento.",
                )
            with _lv_col2:
                st.markdown(_marker, unsafe_allow_html=True)
                piu_difficile = st.button(
                    "Più difficile", key=f"piu_difficile_{idx}", use_container_width=True,
                    help="Numeri meno immediati e un passaggio di ragionamento in più.",
                )
            _qr_col1, _qr_col2 = st.columns(2, gap="small")
            with _qr_col1:
                st.markdown(_marker, unsafe_allow_html=True)
                quick_regen = st.button(
                    "Cambia i numeri",
                    key=f"quick_regen_{idx}",
                    use_container_width=True,
                    help="Stesso esercizio con valori e dati numerici nuovi.",
                )
            with _qr_col2:
                st.markdown(_marker, unsafe_allow_html=True)
                cambia_tutto = st.button(
                    "Cambia esercizio",
                    key=f"cambia_tutto_{idx}",
                    use_container_width=True,
                    help="Un esercizio completamente diverso, sullo stesso argomento.",
                )
            st.caption("«Cambia i numeri» tiene lo stesso esercizio con dati nuovi; "
                       "«Cambia esercizio» ne propone uno diverso sullo stesso argomento.")
            _ea_c1, _ea_c2 = st.columns(2, gap="small")
            with _ea_c1:
                aggiungi = st.button(
                    "Aggiungi un esercizio", key=f"aggiungi_{idx}", type="tertiary",
                    icon=":material/add:", disabled=(n_blocks >= 15),
                    help="Crea un esercizio nuovo in fondo e ridistribuisce i punti.",
                )
            with _ea_c2:
                elimina = st.button(
                    "Elimina questo esercizio", key=f"elimina_{idx}", type="tertiary",
                    icon=":material/delete:", disabled=(n_blocks <= 1),
                    help="Toglie questo esercizio e ridistribuisce i punti sugli altri.",
                )
            if elimina:
                st.session_state["_conf_elimina"] = idx
            elif st.session_state.get("_conf_elimina") not in (None, idx):
                st.session_state.pop("_conf_elimina", None)

            elimina_si = False
            if st.session_state.get("_conf_elimina") == idx:
                st.warning(
                    f"Eliminare l'esercizio {idx+1}? I punti verranno ridistribuiti sugli altri esercizi."
                )
                _el_c1, _el_c2 = st.columns(2, gap="small")
                with _el_c1:
                    elimina_si = st.button("Sì, elimina", key=f"elimina_si_{idx}",
                                           type="primary", use_container_width=True)
                with _el_c2:
                    if st.button("No, tienilo", key=f"elimina_no_{idx}", use_container_width=True):
                        st.session_state.pop("_conf_elimina", None)
                        st.rerun()

            # Placeholder feedback immediato — sotto i pulsanti, nella colonna sinistra
            _action_ph = st.empty()
            if quick_regen:
                _action_ph.info(f"Generazione variante esercizio {idx+1}…")
            elif cambia_tutto:
                _action_ph.info(f"Generazione nuovo esercizio {idx+1}…")

            spazio("sm")

            # ── Altre modifiche — descrizione libera, chiusa di default ──────────
            with st.expander("✏️ Altre modifiche", expanded=False):
                st.markdown(
                    '<div style="font-size:.95rem;color:' + T["text2"] + ';margin-bottom:.5rem;'
                    'font-family:DM Sans,sans-serif;line-height:1.5;">'
                    'Descrivi la modifica — l\'AI rigenererà solo questo esercizio. '
                    'I punteggi si cambiano più sotto, in «Cambia i punteggi».'
                    '</div>',
                    unsafe_allow_html=True
                )
                istruzione = st.text_area(
                    f"Modifica esercizio {idx+1}",
                    placeholder="es. Converti in Vero/Falso · Aggiungi un sottopunto · Usa un contesto di vita quotidiana",
                    key=f"rw_istr_{idx}",
                    label_visibility="collapsed",
                    height=80,
                )
                rigenera = st.button(
                    "✏️ Applica modifica", key=f"rw_btn_{idx}",
                    use_container_width=True, disabled=not istruzione.strip(),
                    type="primary",
                    help="L'AI applica le tue istruzioni e rigenera solo questo esercizio, senza modificare gli altri.",
                )
                # ── Placeholder feedback immediato sotto il pulsante cliccato ─────
                _loading_ph = st.empty()
                if rigenera and istruzione.strip():
                    _istr_low_quick = istruzione.lower()
                    if any(kw in _istr_low_quick for kw in _SCORE_KEYWORDS):
                        _loading_ph.warning(
                            "⚠️ **Hai menzionato punteggi / punti.**\n\n"
                            "Per modificare i punti usa il pannello **⚖️ Cambia i punteggi** "
                            "qui sotto — imposta i valori desiderati e premi **Applica Punteggi**. "
                            "Questo campo è riservato alle modifiche al contenuto (testo, difficoltà, formato)."
                        )
                    else:
                        _loading_ph.info(f"Elaborazione in corso — modifico l'esercizio {idx+1}…")


    # ── COLONNA DESTRA — anteprima PDF una pagina alla volta ─────────────────
    with col_pdf:
        st.markdown(
            '<div style="font-size:.72rem;font-weight:700;color:' + T["muted"] + ';'
            'text-transform:uppercase;letter-spacing:.05em;margin-bottom:.5rem;">'
            '📄 Anteprima PDF completo</div>',
            unsafe_allow_html=True
        )
        # Controlla se il PDF è cambiato e aggiorna le preview se necessario
        vA = st.session_state.verifiche.get("A", {})
        current_pdf_ts = vA.get("pdf_ts")
        last_preview_ts = st.session_state.get("last_preview_ts", 0)
        
        # LOGICA AGGRESSIVA: forza sempre l'aggiornamento se c'è un PDF recente
        force_update = False
        
        # Condizione 0: force refresh esplicito
        if st.session_state.get("force_preview_refresh", False):
            force_update = True
            logger.info("FORCE REFRESH: flag force_preview_refresh rilevato")
            # Resetta il flag dopo l'uso
            st.session_state.force_preview_refresh = False
        
        # Condizione 1: timestamp più recente
        elif current_pdf_ts and current_pdf_ts > last_preview_ts:
            force_update = True
            
        # Condizione 2: se il timestamp del PDF è molto recente (ultimi 5 secondi)
        elif current_pdf_ts and (time.time() - current_pdf_ts) < 5:
            force_update = True
            
        # Condizione 3: se non ci sono immagini preview ma c'è un PDF
        elif current_pdf_ts and not st.session_state.get("preview_images"):
            force_update = True
        
        if force_update:
            vA_pdf = vA.get("pdf")
            if vA_pdf:
                try:
                    logger.info(f"FORZATURA AGGIORNAMENTO PREVIEW - PDF ts: {current_pdf_ts}, Last preview: {last_preview_ts}")
                    new_imgs, _ = pdf_to_images_bytes(vA_pdf)
                    st.session_state.preview_images = new_imgs or []
                    st.session_state.last_preview_ts = current_pdf_ts
                    logger.info(f"Preview images aggiornate FORZATAMENTE - {len(new_imgs) if new_imgs else 0} pagine")
                except Exception as e:
                    logger.error(f"Errore aggiornamento preview forzato: {e}")
            else:
                logger.warning("PDF ts presente ma nessun PDF disponibile per preview")
        
        imgs = st.session_state.preview_images
        if imgs:
            n_pages  = len(imgs)
            _pg = max(0, min(st.session_state.get("preview_page", 0), n_pages - 1))

            # Forza refresh dell'immagine (st.image non supporta key)
            st.image(imgs[_pg], use_container_width=True)

            if n_pages > 1:
                spazio("xs")
                _pc, _pm, _pn = st.columns([1, 2, 1])
                with _pc:
                    if st.button("◀", key="prev_pg", use_container_width=True,
                                 disabled=(_pg == 0)):
                        st.session_state.preview_page = _pg - 1; st.rerun()
                with _pm:
                    st.markdown(
                        f'<div style="text-align:center;font-size:.75rem;font-weight:600;'
                        f'color:{T["text2"]};font-family:DM Sans,sans-serif;padding:.35rem 0;">'
                        f'Pag. {_pg+1} / {n_pages}</div>',
                        unsafe_allow_html=True
                    )
                with _pn:
                    if st.button("▶", key="next_pg", use_container_width=True,
                                 disabled=(_pg == n_pages - 1)):
                        st.session_state.preview_page = _pg + 1; st.rerun()
        else:
            vA_pdf = st.session_state.verifiche["A"].get("pdf")
            if vA_pdf:
                b64 = base64.b64encode(vA_pdf).decode()
                st.markdown(
                    '<iframe src="data:application/pdf;base64,' + b64 + '#toolbar=0&navpanes=0&scrollbar=1" '
                    'style="width:100%;height:560px;border:none;border-radius:8px;"></iframe>',
                    unsafe_allow_html=True
                )
            else:
                st.caption("Anteprima non disponibile.")

    # ── IDEA #3: Quick Regen — variante rapida handler ──────────────────────
    if quick_regen:
        _pts_custom_qr = st.session_state.get("recalibra_pts", [])
        if _pts_custom_qr and len(_pts_custom_qr) == n_blocks:
            _qr_target_pts = int(_pts_custom_qr[idx])
        else:
            _qr_target_pts = parse_pts_from_block_body(body)

        if mostra_punteggi and _qr_target_pts > 0:
            _qr_punti_nota = (
                f"Assegna esattamente {_qr_target_pts} pt in totale a questo esercizio, "
                f"distribuendoli tra i sotto-punti con il formato (N pt) su ogni \\item. "
                f"La somma DEVE essere {_qr_target_pts} pt."
            )
        elif mostra_punteggi:
            _qr_punti_nota = f"Mantieni il formato (X pt) su ogni \\item."
        else:
            _qr_punti_nota = "NON inserire punteggi (X pt)."

        _qr_prompt = (
            f"Sei un docente esperto di {materia_str} e LaTeX.\n"
            f"Devi creare una VARIANTE di questo esercizio: cambia i dati numerici, "
            f"i nomi delle variabili, i valori specifici — mantenendo IDENTICA "
            f"la struttura, la tipologia e il livello di difficoltà.\n\n"
            f"MATERIA: {materia_str}\n"
            f"ARGOMENTO: {argomento_str}\n"
            f"⚠️ L'esercizio DEVE restare su '{argomento_str}' in '{materia_str}'.\n\n"
            f"ESERCIZIO ORIGINALE:\n\\subsection*{{{title}}}\n{body}\n\n"
            f"REGOLE:\n"
            f"- Cambia SOLO i dati (numeri, coefficienti, nomi, valori) — "
            f"NON la struttura, NON il tipo, NON la difficoltà.\n"
            f"- Se ci sono grafici TikZ/pgfplots, DEVI generare codice TikZ COMPLETO aggiornato ai nuovi dati. "
              f"NON usare \\includegraphics{{placeholder}} né commenti '%% inserire grafico'.\n"
            f"- NON inserire MAI commenti LaTeX (%% ...) nel corpo degli esercizi.\n"
            f"- Mantieni lo STESSO numero di sotto-punti.\n"
            f"- {REGOLA_SOTTOPUNTI_MODIFICA}\n"
            f"- {REGOLA_GRAFICO_CURVE}\n"
            f"- {_qr_punti_nota}\n"
            f"- Restituisci SOLO il blocco \\subsection*{{...}} con la variante.\n"
            f"- NON includere preambolo o \\begin{{document}}.\n"
            f"OUTPUT: SOLO codice LaTeX del blocco esercizio."
        )
        st.session_state[f"_undo_block_{idx}"] = dict(st.session_state.review_blocks[idx])
        _action_ph.empty()
        with _action_ph.status(f"Generazione variante esercizio {idx+1}…", expanded=True) as _qr_st:
            try:
                _qr_model = crea_modello(modello_rw).per("modifica")
                _qr_resp = _qr_model.generate_content(_qr_prompt)
                _qr_nuovo = _qr_resp.text.replace("```latex","").replace("```","").strip()
                _qr_m = re.match(r"\\subsection\*\{([^}]*)\}(.*)", _qr_nuovo, re.DOTALL)
                if _qr_m:
                    _qr_new_title = _qr_m.group(1)
                    _qr_new_body  = _qr_m.group(2).strip()
                else:
                    _qr_new_title = title
                    _qr_new_body  = _qr_nuovo
                _qr_new_title = re.sub(r'\s*\(\d+\s*pt\)', '', _qr_new_title).strip()
                if mostra_punteggi and _qr_target_pts > 0:
                    _qr_new_body = riscala_single_block(_qr_new_title, _qr_new_body, _qr_target_pts)
                st.session_state.review_blocks[idx]["title"] = _qr_new_title
                st.session_state.review_blocks[idx]["body"]  = _qr_new_body
                if "recalibra_pts" in st.session_state:
                    del st.session_state["recalibra_pts"]
                _qr_pdf, _ = _ricompila_verifica_a(mostra_punteggi, con_griglia, punti_totali, blocco_modificato=idx)
                if not _qr_pdf:
                    _qr_st.update(label="PDF non aggiornato", state="error", expanded=False)
                    _mostra_errore(
                        "Ho cambiato i numeri ma non sono riuscito a rifare il PDF", "compilazione PDF",
                        consiglio="Premi «Annulla modifica» per tornare indietro, poi riprova.",
                    )
                else:
                    _qr_st.update(label="Variante pronta!", state="complete", expanded=False)
                    st.toast(f"Variante esercizio {idx+1} generata!", icon="✅")
                    st.rerun()
            except Exception as _qr_e:
                _qr_st.update(label="Variante non riuscita", state="error", expanded=False)
                _mostra_errore("Non sono riuscito a cambiare i numeri di questo esercizio", _qr_e)

    # ── Più facile / Più difficile — un solo esercizio, istruzione fissa ──────
    if piu_facile or piu_difficile:
        _action_ph.empty()
        _rigenera_esercizio_guidato(
            idx,
            istruzione_livello_esercizio(bool(piu_difficile), argomento_str),
            "Rendo più difficile" if piu_difficile else "Rendo più facile",
            materia_str, argomento_str, modello_rw,
            mostra_punteggi, con_griglia, punti_totali, _action_ph,
        )

    # ── Aggiungi un esercizio ─────────────────────────────────────────────────
    if aggiungi:
        _action_ph.empty()
        with st.spinner("Creo un nuovo esercizio e ridistribuisco i punti…"):
            _ok_ag = _aggiungi_esercizio(mostra_punteggi, con_griglia, punti_totali,
                                         materia_str, argomento_str, scuola_str, modello_rw)
        if _ok_ag:
            st.toast("Esercizio aggiunto in fondo", icon="➕")
            st.rerun()

    # ── Elimina esercizio (dopo conferma) ─────────────────────────────────────
    if elimina_si:
        with st.spinner("Elimino l'esercizio e ricalcolo i punti…"):
            _ok_el = _elimina_esercizio(idx, mostra_punteggi, con_griglia, punti_totali)
        if _ok_el:
            st.toast("Esercizio eliminato", icon="🗑️")
            st.rerun()

    # ── Logica modifica AI ────────────────────────────────────────────────────
    if rigenera and istruzione.strip():
        _istr_low = istruzione.lower()

        # ── Rilevamento richieste punteggio ───────────────────────────────────
        # L'avviso è già mostrato inline sotto il pulsante (via _loading_ph).
        _is_score_req = any(kw in _istr_low for kw in _SCORE_KEYWORDS)
        if not _is_score_req:
            # ── Regen AI con preservazione punti ─────────────────────────────
            # Cattura i punti correnti dell'esercizio PRIMA della regen.
            # Se recalibra_pts è stato già impostato dall'utente usa quello,
            # altrimenti legge dal corpo del blocco corrente.
            _pts_custom = st.session_state.get("recalibra_pts", [])
            if _pts_custom and len(_pts_custom) == n_blocks:
                _exercise_target_pts = int(_pts_custom[idx])
            else:
                _exercise_target_pts = parse_pts_from_block_body(body)

            # Il prompt dice all'AI quanti pt deve assegnare a questo esercizio.
            # La funzione riscala_single_block lo corregge deterministicamente dopo.
            if mostra_punteggi and _exercise_target_pts > 0:
                punti_nota = (
                    f"Assegna esattamente {_exercise_target_pts} pt in totale a questo esercizio, "
                    f"distribuendoli tra i sotto-punti con il formato (N pt) su ogni \\item. "
                    f"La somma DEVE essere {_exercise_target_pts} pt."
                )
            elif mostra_punteggi:
                punti_nota = (
                    f"Mantieni il formato (X pt) su ogni \\item. "
                    f"La somma totale dei punti DEVE essere esattamente {punti_totali} pt."
                )
            else:
                punti_nota = "NON inserire punteggi (X pt)."

            # Rileva se l'esercizio originale ha un grafico (TikZ/pgfplots)
            _ha_grafico = bool(re.search(r'\\begin\{(tikzpicture|axis|pgfpicture)\}', body))
            _grafici_rule_rw = (
                "- GRAFICI: l'esercizio originale contiene un grafico. "
                "SE la modifica lo richiede o mantiene il grafico, scrivi al suo posto UNA riga [[GRAFICO: y = ... | x da A a B]] "
                "con la funzione giusta (NON codice TikZ: lo disegna il programma). "
                "NON scrivere mai commenti come '% qui andrebbe il grafico' o '% inserire figura' o '\\includegraphics{placeholder}'. "
                "Se non puoi dare la funzione, rimuovi la richiesta grafica dall'esercizio."
                if _ha_grafico else
                "- NON aggiungere \\includegraphics, placeholder o commenti '% qui andrebbe'. "
                "Se l'istruzione richiede il grafico di una funzione, usare SOLO la riga [[GRAFICO: y = ... | x da A a B]] (mai codice TikZ)."
            )
            _prompt_rw = (
                f"Sei un docente esperto di {materia_str} e LaTeX.\n"
                f"Devi MODIFICARE questo esercizio secondo l'istruzione del docente, "
                f"ma SENZA MAI cambiare la materia o l'argomento della verifica.\n\n"
                f"MATERIA: {materia_str}\n"
                f"ARGOMENTO DELLA VERIFICA: {argomento_str}\n"
                f"⚠️ REGOLA ASSOLUTA E INVIOLABILE: l'esercizio deve restare su '{argomento_str}' "
                f"in '{materia_str}'. NON introdurre mai argomenti diversi (es. se la verifica è "
                f"sulla Parabola non generare studio di funzione, derivate, integrali ecc.).\n\n"
                f"ESERCIZIO ORIGINALE:\n\\subsection*{{{title}}}\n{body}\n\n"
                f"ISTRUZIONE DEL DOCENTE: {istruzione.strip()}\n\n"
                f"REGOLE FONDAMENTALI:\n"
                f"- LUNGHEZZA MASSIMA: l'esercizio modificato non deve superare le 8-10 righe di testo.\n"
                f"- VIETATO ASSOLUTO: NON inserire MAI soluzioni, risposte o risultati.\n"
                f"- VIETATO MAPPE E DIAGRAMMI: NON generare MAI mappe, diagrammi spaziali o geografici.\n"
                f"- Applica SOLO la modifica richiesta. NON riscrivere da zero, modifica l'esistente.\n"
                f"- Mantieni OBBLIGATORIAMENTE l'argomento '{argomento_str}'.\n"
                f"- Restituisci SOLO il blocco \\subsection*{{...}} con il nuovo esercizio.\n"
                f"- Mantieni struttura LaTeX (\\subsection*, enumerate, \\item[a]), ecc).\n"
                f"- {REGOLA_SOTTOPUNTI_MODIFICA}\n"
                f"- {punti_nota}\n"
                f"- {_grafici_rule_rw}\n"
                f"- {REGOLA_GRAFICO_CURVE}\n"
                f"- NON inserire MAI commenti LaTeX (%% ...) nel corpo degli esercizi.\n"
                f"- NON includere preambolo o \\begin{{document}}.\n"
                f"OUTPUT: SOLO codice LaTeX del blocco esercizio."
            )
            st.session_state[f"_undo_block_{idx}"] = dict(st.session_state.review_blocks[idx])
            _loading_ph.empty()
            
            _loading_ph.info(f"Modifico l'esercizio {idx+1}… ci vogliono pochi secondi.", icon="⏳")
            try:
                model_rw_obj = crea_modello(modello_rw).per("modifica")
                resp  = model_rw_obj.generate_content(_prompt_rw)
                nuovo = resp.text.replace("```latex","").replace("```","").strip()
                m_rw  = re.match(r"\\subsection\*\{([^}]*)\}(.*)", nuovo, re.DOTALL)
                if m_rw:
                    new_title = m_rw.group(1)
                    new_body  = m_rw.group(2).strip()
                else:
                    new_title = title
                    new_body  = nuovo

                    # Rimuovi eventuale (N pt) che l'AI ha messo nel titolo
                new_title = re.sub(r'\s*\(\d+\s*pt\)', '', new_title).strip()

                # Correzione deterministica dei punti: porta la somma esatta
                # al valore che aveva l'esercizio prima della modifica AI.
                if mostra_punteggi and _exercise_target_pts > 0:
                    new_body = riscala_single_block(new_title, new_body, _exercise_target_pts)

                st.session_state.review_blocks[idx]["title"] = new_title
                st.session_state.review_blocks[idx]["body"]  = new_body

                # Reset pannello ricalibra: rilegge i punteggi aggiornati
                if "recalibra_pts" in st.session_state:
                    del st.session_state["recalibra_pts"]

                # Ricompila il PDF e aggiorna la preview dopo la modifica
                _pdf_rw, _err_rw = _ricompila_verifica_a(mostra_punteggi, con_griglia, punti_totali, blocco_modificato=idx)
                logger.info(f"COMPILAZIONE PDF POST-MODIFICA - Success: {_pdf_rw is not None}, Error: {_err_rw}")
                if _pdf_rw:
                    st.session_state.force_preview_refresh = True

                    # (nessun messaggio di successo qui: il rerun lo cancellerebbe; basta il toast)
                    st.toast(f"Esercizio {idx+1} aggiornato!", icon="✅"); st.rerun()
                else:
                    _loading_ph.empty()
                    _mostra_errore(
                        "Ho modificato l'esercizio ma non sono riuscito a rifare il PDF", _err_rw,
                        consiglio="Premi «Annulla modifica» per tornare indietro, poi riprova.",
                    )
            except Exception as e:
                _loading_ph.empty()
                _mostra_errore(
                    "Non sono riuscito ad applicare la modifica", e,
                    consiglio="Prova a riformulare la richiesta con parole diverse.",
                )

    # ── Logica "Cambia totalmente" — struttura diversa, argomento uguale ─────
    if cambia_tutto:
        _ct_pts = st.session_state.get("recalibra_pts", [])
        _ct_target_pts = (
            int(_ct_pts[idx]) if _ct_pts and len(_ct_pts) == n_blocks
            else parse_pts_from_block_body(body)
        )
        _ct_punti_nota = (
            f"Assegna esattamente {_ct_target_pts} pt totali, distribuendoli tra i sotto-punti con (N pt) su ogni \\item."
            if mostra_punteggi and _ct_target_pts > 0
            else ("Mantieni formato (X pt) su ogni \\item." if mostra_punteggi else "NON inserire punteggi.")
        )
        # Raccgli gli altri esercizi per controllo duplicati
        _altri_esercizi = []
        for j, block in enumerate(st.session_state.review_blocks):
            if j != idx:  # Salta l'esercizio da sostituire
                _altri_esercizi.append(f"\\subsection*{{{block['title']}}}\n{block['body'][:200]}...")
        
        _altri_testo = "\n".join(_altri_esercizi) if _altri_esercizi else "Nessun altro esercizio presente."
        
        _prompt_ct = (
            f"Sei un docente esperto di {materia_str} e LaTeX.\n"
            f"Genera un esercizio COMPLETAMENTE DIVERSO — diverso in struttura, tipologia e contenuto specifico — "
            f"ma che rimanga strettamente pertinente all'argomento e agli obiettivi didattici della verifica.\n\n"
            f"MATERIA: {materia_str}\n"
            f"ARGOMENTO DELLA VERIFICA: {argomento_str}\n"
            f"ESERCIZIO DA SOSTITUIRE (struttura e tipo da NON replicare):\n\\subsection*{{{title}}}\n{body}\n\n"
            f"ALTRI ESERCIZI GIA PRESENTI (da NON duplicare concettualmente):\n{_altri_testo}\n\n"
            f"REGOLE FONDAMENTALI:\n"
            f"- LUNGHEZZA MASSIMA: il nuovo esercizio non deve superare le 8-10 righe di testo.\n"
            f"- VIETATO ASSOLUTO: NON inserire MAI soluzioni, risposte o risultati. MAI scrivere '= X', 'la risposta è', 'il risultato è'.\n"
            f"- VIETATO MAPPE E DIAGRAMMI: NON generare MAI mappe, diagrammi spaziali o geografici.\n"
            f"- CONTROLLO DUPLICATI: ANALIZZA gli altri esercizi sopra. NON generare un esercizio che testi "
              f"lo stesso concetto matematico o la stessa abilità. Ogni esercizio deve essere UNICO concettualmente.\n"
            f"- MANTENIMENTO DIFFICOLTÀ: se questo è l'Esercizio 1 (Saperi Essenziali), deve rimanere accessibile e risolvibile in 5-8 minuti. "
              f"NON aumentare la difficoltà o la complessità.\n"
            f"- Cambia TIPO di esercizio (es. da calcolo numerico a dimostrazione, da aperto a V/F, ecc.).\n"
            f"- Cambia i concetti specifici testati, scegliendo aspetti diversi ma coerenti con '{argomento_str}'.\n"
            f"- L'esercizio DEVE restare su '{argomento_str}' in '{materia_str}'. NON introdurre altri argomenti.\n"
            f"- Restituisci SOLO il blocco \\subsection*{{...}} con il nuovo esercizio.\n"
            f"- Mantieni la struttura LaTeX (\\subsection*, enumerate, \\item[a]), ecc).\n"
            f"- {REGOLA_SOTTOPUNTI_MODIFICA}\n"
            f"- {_ct_punti_nota}\n"
            f"- Se includi un grafico, usa SOLO codice TikZ/pgfplots COMPLETO e COMPILABILE. "
              f"NON usare \\includegraphics{{placeholder}} né commenti '%% inserire figura'.\n"
            f"- {REGOLA_GRAFICO_CURVE}\n"
            f"- NON inserire MAI commenti LaTeX (%% ...) nel corpo degli esercizi.\n"
            f"- NON includere preambolo o \\begin{{document}}.\n"
        )
        st.session_state[f"_undo_block_{idx}"] = dict(st.session_state.review_blocks[idx])
        _action_ph.empty()
        with _action_ph.status(f"Generazione nuovo esercizio {idx+1}…", expanded=True) as _ct_st:
            try:
                _ct_model = crea_modello(MODEL_FAST_ID, "cambio_esercizio")
                _ct_resp = _ct_model.generate_content(
                    [_prompt_ct],
                    generation_config={"temperature": 0.95},
                ).text.strip()
                if _ct_resp.startswith("```"):
                    _ct_resp = re.sub(r"^```[a-z]*\n?", "", _ct_resp)
                    _ct_resp = re.sub(r"\n?```$", "", _ct_resp)
                _ct_m = re.match(r"\\subsection\*\{([^}]*)\}(.*)", _ct_resp, re.DOTALL)
                if _ct_m:
                    _ct_title = _ct_m.group(1)
                    _ct_body  = _ct_m.group(2).strip()
                    _ct_title = re.sub(r'\s*\(\d+\s*pt\)', '', _ct_title).strip()
                else:
                    _ct_title = title
                    _ct_body  = _ct_resp
                if mostra_punteggi and _ct_target_pts > 0:
                    _ct_body = riscala_single_block(_ct_title, _ct_body, _ct_target_pts)
                st.session_state.review_blocks[idx] = {
                    "title": _ct_title or title,
                    "body":  _ct_body,
                }
                _ct_pdf, _ = _ricompila_verifica_a(mostra_punteggi, con_griglia, punti_totali, blocco_modificato=idx)
                if not _ct_pdf:
                    _ct_st.update(label="PDF non aggiornato", state="error", expanded=False)
                    _mostra_errore(
                        "Ho cambiato l'esercizio ma non sono riuscito a rifare il PDF", "compilazione PDF",
                        consiglio="Premi «Annulla modifica» per tornare indietro, poi riprova.",
                    )
                else:
                    _ct_st.update(label="Esercizio cambiato!", state="complete", expanded=False)
                    st.toast(f"Esercizio {idx+1} cambiato!", icon="✅")
                    st.rerun()
            except Exception as _ct_e:
                _ct_st.update(label="Cambio non riuscito", state="error", expanded=False)
                _mostra_errore("Non sono riuscito a cambiare questo esercizio", _ct_e)


    # ── Cambia i punteggi — una tabella unica, totale sempre ribilanciato ─────
    if mostra_punteggi and n_blocks > 0:
        with st.expander("⚖️ Cambia i punteggi", expanded=False):
            _righe, _dati = [], []          # _righe[k] = (esercizio, sottopunto)
            for _i, _b in enumerate(st.session_state.review_blocks):
                _items_rc = parse_items_from_block(_b["body"], _b.get("title", ""))
                _tit = _clean_title(re.sub(r"\s*\(\d+\s*pt\)", "", _b["title"]))
                for _j, (_lbl, _short, _pt) in enumerate(_items_rc):
                    _testo = (_short or "").strip()
                    if _testo in ("", "[formula]"):
                        # riga fatta solo di formula: "[formula]" non dice nulla al docente
                        _testo = "(formula)" if _pt else "(opzione di risposta)"
                    _righe.append((_i, _j))
                    _dati.append({
                        "Esercizio": f"{_i+1}. {_tit[:30]}" if _j == 0 else "",
                        "Richiesta": (f"{_lbl} {_testo[:70]}…" if len(_testo) > 70
                                      else f"{_lbl} {_testo}").strip(),
                        "Punti": int(_pt),
                    })

            if not _dati:
                st.caption("Nessun punteggio da modificare in questa verifica.")
            else:
                st.markdown(
                    f'<div style="font-size:.88rem;color:{T["text2"]};margin-bottom:.4rem;'
                    f'font-family:DM Sans,sans-serif;">Cambia i numeri nella colonna <b>Punti</b>. '
                    f'Il totale deve fare <b>{punti_totali} pt</b>: se non torna, '
                    f'lo ribilancio io quando applichi.</div>',
                    unsafe_allow_html=True,
                )
                _firma = abs(hash(tuple((d["Esercizio"], d["Richiesta"], d["Punti"]) for d in _dati)))
                _tab = st.data_editor(
                    _dati,
                    key=f"rc_editor_{_firma}",   # nuova chiave se i punti cambiano da fuori
                    hide_index=True,
                    use_container_width=True,
                    disabled=["Esercizio", "Richiesta"],
                    column_config={
                        "Esercizio": st.column_config.TextColumn("Esercizio", width="medium"),
                        "Richiesta": st.column_config.TextColumn("Richiesta", width="large"),
                        "Punti": st.column_config.NumberColumn(
                            "Punti", min_value=0, max_value=punti_totali, step=1,
                            format="%d", required=True, width="small"),
                    },
                )
                _tab_righe = _tab.to_dict("records") if hasattr(_tab, "to_dict") else list(_tab)

                def _intero(v):
                    try:
                        return max(0, int(v))
                    except (TypeError, ValueError):
                        return 0

                _nuovi = [_intero(r.get("Punti")) for r in _tab_righe]
                _totale_rc = sum(_nuovi)
                _per_es_sub = {}
                for (_i, _j), _v in zip(_righe, _nuovi):
                    _per_es_sub[_i] = _per_es_sub.get(_i, 0) + _v
                _sub_txt = " · ".join(f"Es. {_i+1}: {_p} pt" for _i, _p in sorted(_per_es_sub.items()))

                if _totale_rc == punti_totali:
                    st.success(f"Totale: {_totale_rc} pt — perfetto.   ({_sub_txt})", icon="✅")
                else:
                    st.warning(
                        f"Totale: {_totale_rc} pt invece di {punti_totali}. "
                        f"Premendo «Applica» ribilancio tutto a {punti_totali} pt in proporzione.   ({_sub_txt})",
                        icon="⚖️",
                    )

                if st.button("✅ Applica punteggi", key="rc_applica",
                             use_container_width=True, type="primary"):
                    _finali = _nuovi if _totale_rc == punti_totali else bilancia_punti(_nuovi, punti_totali)
                    _applica_punti_a_blocchi(_righe, _finali)

                    with st.spinner("Ricompilazione PDF con i nuovi punteggi…"):
                        _pdf_rc, _err_rc = _ricompila_verifica_a(
                            mostra_punteggi, con_griglia, punti_totali, rileggi_blocchi=True,
                        )
                    if _pdf_rc:
                        for _kk in list(st.session_state.keys()):
                            if _kk.startswith("rc_editor_") or re.match(r"^item_pt_\d+_\d+$", _kk):
                                del st.session_state[_kk]
                        st.session_state.pop("recalibra_pts", None)
                        st.toast(
                            "✅ Punteggi applicati" + ("" if _totale_rc == punti_totali
                                                       else f" (ribilanciati a {punti_totali} pt)"),
                            icon="⚖️",
                        )
                        st.rerun()
                    else:
                        _mostra_errore_pdf(_err_rc, "questa verifica")

    # ── Pulsante principale della schermata: torna al PDF ─────────────────────
    spazio("md")
    confirm_pdf = st.button(
        "Fatto: torna al PDF",
        icon=":material/check:",
        type="primary",
        use_container_width=True,
        key="btn_confirm_final"
    )

    if confirm_pdf:
        with st.spinner("Preparo il PDF aggiornato… ancora qualche secondo"):
            _pts_custom = st.session_state.get("recalibra_pts", [])
            pdf_bytes, err = _ricompila_verifica_a(
                mostra_punteggi, con_griglia, punti_totali, riscala_totale=True,
                punti_custom=_pts_custom if _pts_custom and len(_pts_custom) == n_blocks else None,
            )
            if pdf_bytes:
                st.session_state.stage = STAGE_FINAL
                st.rerun()
            else:
                _mostra_errore_pdf(err, "questa verifica")

    # ── Pulsante RICONFIGURA — piccolo, discreto, sotto ───────────────────────
    spazio("sm")
    st.markdown('<div class="btn-riconfigura-small">', unsafe_allow_html=True)
    if st.button("← Ricomincia da capo", use_container_width=False, key="btn_riconfigura"):
        st.session_state["_conf_ricomincia"] = True
    st.markdown('</div>', unsafe_allow_html=True)
    if st.session_state.get("_conf_ricomincia"):
        st.warning("Tornando al form si perdono le modifiche fatte agli esercizi. La verifica originale resta in «Le mie verifiche».")
        _rc1, _rc2 = st.columns(2, gap="small")
        with _rc1:
            if st.button("Sì, ricomincia", key="btn_ricomincia_si", use_container_width=True):
                st.session_state.pop("_conf_ricomincia", None)
                st.session_state.stage = STAGE_INPUT; st.rerun()
        with _rc2:
            if st.button("No, resta qui", key="btn_ricomincia_no", use_container_width=True):
                st.session_state.pop("_conf_ricomincia", None)
                st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
#  STAGE_FINAL
# ═══════════════════════════════════════════════════════════════════════════════

def _nome_base_file(materia: str, argomento: str) -> str:
    """Nome di file sicuro: «Matematica_Le_frazioni_algebriche»."""
    return re.sub(r"[^\w\-]+", "_", f"{materia}_{argomento}").strip("_")[:60] or "verifica"


def _elementi_kit(argomento, materia, vA, vB, vR, vS, vSC, rubrica_docx) -> list:
    """I documenti già pronti del kit: [{"etichetta", "nome_file", "dati"}] (PDF e Word)."""
    base = _nome_base_file(materia, argomento)
    voci = (
        ("Fila A", "_FilaA.pdf", vA.get("pdf")),
        ("Fila B", "_FilaB.pdf", vB.get("pdf")),
        ("BES/DSA", "_BES_FilaA.pdf", vR.get("pdf")),
        ("Soluzioni", "_Soluzioni.pdf", vS.get("pdf")),
        ("Scheda di allenamento", "_Scheda_allenamento.pdf", (vSC or {}).get("pdf")),
        ("Word", "_FilaA.docx", vA.get("docx") if WORD_ATTIVO else None),
        ("Griglia", "_Griglia.docx", rubrica_docx),
    )
    return [{"etichetta": e, "nome_file": base + n, "dati": d} for e, n, d in voci if d]


def _zip_kit(elementi: list) -> bytes:
    """Tutti i documenti pronti in un solo file ZIP (libreria standard, nessuna dipendenza)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for e in elementi:
            z.writestr(e["nome_file"], e["dati"])
    return buf.getvalue()


def _render_stage_final():
    gp   = st.session_state.gen_params
    vA   = st.session_state.verifiche["A"]
    vB   = st.session_state.verifiche["B"]
    vR   = st.session_state.verifiche["R"]
    vRB  = st.session_state.verifiche["RB"]
    vS   = st.session_state.verifiche["S"]

    arg_str      = gp.get("argomento","Verifica")
    mat_str      = gp.get("materia","")
    scu_str      = gp.get("difficolta","")
    con_griglia  = gp.get("con_griglia", False)
    mod_id       = gp.get("modello_id", modello_id)

    # ── Helper skeleton animato ───────────────────────────────────────────────
    def _skeleton_html(icon, title, sub):
        return (
            f'<div class="ocr-skeleton-wrap">'
            f'  <div class="ocr-skeleton-header">'
            f'    <div class="ocr-skeleton-icon">{icon}</div>'
            f'    <div>'
            f'      <div class="ocr-skeleton-title">{title}</div>'
            f'      <div class="ocr-skeleton-sub">{sub}</div>'
            f'    </div>'
            f'  </div>'
            f'  <div class="ocr-skeleton-doc">'
            f'    <div class="ocr-skeleton-scan"></div>'
            f'    <div class="ocr-skeleton-line" style="width:88%;animation-delay:.0s"></div>'
            f'    <div class="ocr-skeleton-line" style="width:70%;animation-delay:.2s"></div>'
            f'    <div class="ocr-skeleton-line" style="width:82%;animation-delay:.4s"></div>'
            f'  </div>'
            f'</div>'
        )

    # ── Anteprima aggiornata se il PDF è cambiato (modifiche nell'editor) ─────
    _pdf_ts   = vA.get("pdf_ts")
    _last_ts  = st.session_state.get("last_preview_ts", 0)
    _riallinea = (
        st.session_state.pop("force_preview_refresh", False)
        or (_pdf_ts and _pdf_ts > _last_ts)
        or (_pdf_ts and not st.session_state.get("preview_images"))
    )
    if _riallinea and vA.get("pdf"):
        try:
            _imgs_new, _ = pdf_to_images_bytes(vA["pdf"])
            st.session_state.preview_images  = _imgs_new or []
            st.session_state.last_preview_ts = _pdf_ts or time.time()
        except Exception as _e:
            logger.error(f"Errore aggiornamento anteprima (final): {_e}")

    # ── Messaggi lasciati dalla schermata precedente (un rerun li avrebbe cancellati) ──
    _toast_d = st.session_state.pop("_toast_dopo", None)
    if _toast_d:
        st.toast(_toast_d[0], icon=_toast_d[1])
    _avviso_d = st.session_state.pop("_avviso_dopo", None)
    if _avviso_d:
        st.warning(_avviso_d, icon="⚠️")

    _banner_piano("final")

    # ── Autoverifica degli esercizi (materie scientifiche): cosa ha trovato e corretto ──
    _av = st.session_state.get("_autoverifica") or {}
    if _av.get("irrisolti"):
        _righe = "\n".join(f"- **Esercizio {x['num']}**: {x['problema']}" for x in _av["irrisolti"])
        st.warning("Il controllo automatico non è sicuro di questi esercizi: verificali prima di usarli.\n\n" + _righe, icon="🧮")
    if _av.get("corretti"):
        _nums = ", ".join(str(n) for n in _av["corretti"])
        st.caption(f"🧮 Controllo automatico: ho corretto l'esercizio {_nums} (i dati non erano coerenti).")
    elif _av.get("eseguita") and not _av.get("irrisolti"):
        st.caption("🧮 Controllo automatico eseguito: nessun errore trovato negli esercizi.")

    # ── Più di 2 facciate: avviso e riduzione (si stampa su 2 fogli fronte-retro, non su 3) ──
    _n_pag = conta_pagine_pdf(vA.get("pdf"))
    if _n_pag and _n_pag > MAX_FACCIATE:
        _cp1, _cp2 = st.columns([4.2, 1.6], vertical_alignment="center", gap="small")
        _cp1.warning(f"La verifica occupa {_n_pag} facciate. Di solito ne bastano {MAX_FACCIATE}: puoi ridurre carattere e margini "
                     f"oppure togliere un esercizio.", icon="📄")
        if _cp2.button("Riduci a 2 facciate", key="riduci_facciate", use_container_width=True):
            with st.spinner("Riduco l'impaginazione…"):
                _rid = riduci_a_pagine(vA.get("latex") or "", MAX_FACCIATE)
            if _rid:
                vA["latex"], vA["pdf"], _ = _rid
                vA["pdf_ts"] = time.time()
                st.session_state["_toast_dopo"] = (f"Ora la verifica sta in {_rid[2]} facciate", "📄")
            else:
                st.session_state["_avviso_dopo"] = ("Anche riducendo carattere e margini la verifica resta su più di "
                                                    f"{MAX_FACCIATE} facciate: togli un esercizio o accorcia i testi.")
            st.rerun()

    # ── Intestazione compatta ─────────────────────────────────────────────────
    st.markdown(
        f'<div style="text-align:center;margin:.2rem 0 1.1rem;">'
        f'<div style="font-family:DM Sans,sans-serif;font-size:1.7rem;font-weight:800;'
        f'color:{T["text"]};letter-spacing:-.025em;line-height:1.15;">'
        f'<span style="display:inline-flex;align-items:center;justify-content:center;width:1.6rem;height:1.6rem;'
        f'border-radius:50%;background:{T["success"]};color:#fff;font-size:1rem;margin-right:.55rem;'
        f'vertical-align:.12em;">✓</span>La verifica è pronta</div>'
        f'<div style="font-size:.9rem;color:{T["text2"]};font-family:DM Sans,sans-serif;margin-top:.35rem;">'
        + _esc(mat_str) + ' &nbsp;·&nbsp; ' + _esc(scu_str) + ' &nbsp;·&nbsp; ' + _esc(arg_str) +
        f'</div></div>',
        unsafe_allow_html=True
    )

    # ═══════════════════════════════════════════════════════════════════════════
    #  AZIONI PRINCIPALI — sopra l'anteprima: sempre in vista, anche su telefono
    # ═══════════════════════════════════════════════════════════════════════════
    _fname_a = arg_str + "_FilaA"
    # Tre pulsanti della stessa altezza e sulla stessa linea: niente contenitori HTML attorno
    # a uno solo di essi (i margini extra lo sfalsavano), l'altezza è fissata dalla chiave.
    st.markdown(
        '<style>html body .stApp .st-key-az_principali button{min-height:52px !important;'
        'height:52px !important;margin:0 !important;transform:none !important;'
        'font-size:1rem !important;font-weight:700 !important;border-radius:12px !important;}'
        'html body .stApp .st-key-az_principali [data-testid="stDownloadButton"],'
        'html body .stApp .st-key-az_principali [data-testid="stButton"]{margin:0 !important;}</style>',
        unsafe_allow_html=True,
    )
    _box_az = st.container(key="az_principali")
    _az_dl, _az_mod, _az_new = _box_az.columns([1.3, 1, 1], gap="small", vertical_alignment="center")
    with _az_dl:
        if vA.get("pdf"):
            _dl(
                label=f"⬇  Scarica PDF  ·  {_stima(vA['pdf'])}",
                data=vA["pdf"],
                file_name=_fname_a + ".pdf",
                mime="application/pdf",
                use_container_width=True,
                type="primary",
                key="dl_pdf_hero_A",
                on_click="ignore",
                help="Scarica il PDF della verifica, già formattato e pronto per la stampa.",
            )
        else:
            st.warning("Il PDF non è ancora pronto. Apri «Modifica gli esercizi»: ogni modifica lo rifà.")
    with _az_mod:
        if st.button("Modifica gli esercizi", icon=":material/edit:", key="final_edit",
                     use_container_width=True,
                     help="Cambia, rendi più facile o più difficile, o elimina i singoli esercizi."):
            st.session_state.stage = STAGE_REVIEW
            st.rerun()
    with _az_new:
        if st.button("Nuova verifica", icon=":material/add:", key="btn_new_top",
                     use_container_width=True):
            _nuova_verifica()
    st.markdown(
        f'<div style="text-align:center;font-size:.85rem;color:{T["text2"]};margin:.5rem 0 1rem;'
        f'line-height:1.5;font-family:DM Sans,sans-serif;">Controlla sempre il contenuto prima di '
        f'distribuirlo agli studenti. La verifica è salvata in «Le mie verifiche».</div>'
        f'<div style="text-align:center;margin:0 0 .8rem;"><span style="display:inline-block;'
        f'background:{T["accent_light"]};color:{T["accent"]};border-radius:999px;padding:.3rem .9rem;'
        f'font-size:.85rem;font-weight:700;font-family:DM Sans,sans-serif;">'
        f'↓ Più in basso: Soluzioni, Fila B, versione BES/DSA e griglia</span></div>',
        unsafe_allow_html=True
    )

    _senza_grafico = esercizi_con_grafico_mancante(st.session_state.get("review_blocks", []))
    if _senza_grafico:
        st.warning(
            "Attenzione: l'esercizio " + ", ".join(str(i + 1) for i in _senza_grafico)
            + " cita un grafico che nel PDF non c'è. Apri «Modifica gli esercizi» e usa «Cambia esercizio».",
            icon="📉",
        )

    # ── Anteprima: tutte le pagine una sotto l'altra ──────────────────────────
    _, _col_prev, _ = st.columns([1, 3, 1])
    with _col_prev:
        _imgs_f = st.session_state.get("preview_images") or []
        if _imgs_f:
            for _n_p, _img_p in enumerate(_imgs_f, start=1):
                st.image(_img_p, use_container_width=True,
                         caption=f"Pagina {_n_p} di {len(_imgs_f)}" if len(_imgs_f) > 1 else None)
        elif vA.get("pdf"):
            _b64 = base64.b64encode(vA["pdf"]).decode()
            st.markdown(
                '<iframe src="data:application/pdf;base64,' + _b64 + '#toolbar=0&navpanes=0" '
                'style="width:100%;height:620px;border:none;border-radius:8px;"></iframe>',
                unsafe_allow_html=True
            )
        else:
            st.caption("Anteprima non disponibile.")

    # ═══════════════════════════════════════════════════════════════════════════
    #  IL KIT COMPLETO — Fila B, BES/DSA, soluzioni, griglia, Word, scheda di allenamento
    # ═══════════════════════════════════════════════════════════════════════════
    # Etichetta «Pro» sulle funzioni del kit: spenta finché non parte la monetizzazione
    _PRO = (
        f' <span style="font-size:.62rem;font-weight:800;letter-spacing:.06em;color:{T["accent"]};'
        f'border:1px solid {T["accent"]};border-radius:6px;padding:1px 6px;vertical-align:middle;">PRO</span>'
        if MOSTRA_BADGE_PRO else ""
    )
    vSC = st.session_state.verifiche.get("SC") or {"latex": None, "pdf": None, "n": 0, "avvisi": []}

    # Coda di «Prepara tutto il kit»: un elemento per volta, perché ogni creazione fa un rerun
    _flag_kit = {"B": "_gen_fila_b", "R": "_gen_bes", "S": "_gen_sol", "SC": "_gen_scheda"}
    _coda_kit = st.session_state.get("_kit_coda") or []
    if _coda_kit and not any(st.session_state.get(f) for f in _flag_kit.values()):
        _prossimo = _coda_kit.pop(0)
        st.session_state["_kit_coda"] = _coda_kit
        st.session_state[_flag_kit[_prossimo]] = True
    _kit_in_corso = bool(_coda_kit) or any(st.session_state.get(f) for f in _flag_kit.values())

    st.markdown(
        f'<div class="variant-section-label" style="margin-top:.4rem;">IL KIT COMPLETO PER LA TUA CLASSE</div>'
        f'<div style="font-size:.9rem;color:{T["text2"]};font-family:DM Sans,sans-serif;margin:-.2rem 0 .7rem;">'
        f'Tutto pronto a partire dalla stessa verifica: versioni, soluzioni e una scheda per allenarsi.</div>',
        unsafe_allow_html=True
    )
    _kit_pronti = _elementi_kit(arg_str, mat_str, vA, vB, vR, vS, vSC, st.session_state.get("_rubrica_docx"))
    _kit_mancanti = [k for k, presente in (
        ("B", vB.get("pdf") or vB.get("latex")), ("R", vR.get("pdf") or vR.get("latex")),
        ("S", vS.get("pdf") or vS.get("latex")), ("SC", vSC.get("pdf")),
    ) if not presente]
    _kc1, _kc2 = st.columns(2, gap="small")
    with _kc1:
        if _pro_bloccato("zip"):
            _pulsante_pro("zip", "pro_kit", "Prepara tutto il kit con Pro")
        elif st.button("Prepara tutto il kit", icon=":material/auto_awesome:", key="kit_tutto",
                     use_container_width=True, disabled=(not _kit_mancanti) or _kit_in_corso,
                     help="Crea Fila B, BES/DSA, Soluzioni e scheda di allenamento, una dopo l'altra "
                          "(circa un minuto). Quello che c'è già non si rifà."):
            st.session_state["_kit_coda"] = [k for k in ("B", "R", "S", "SC") if k in _kit_mancanti]
            st.rerun()
    with _kc2:
        if len(_kit_pronti) >= 2 and not _pro_bloccato("zip"):
            _dl("Scarica tutto (ZIP)", data=lambda: _zip_kit(_kit_pronti),
                file_name=_nome_base_file(mat_str, arg_str) + "_kit.zip", mime="application/zip",
                icon=":material/folder_zip:", use_container_width=True, key="dl_kit_zip",
                help="Tutti i documenti pronti in un solo file.")
    if _kit_in_corso:
        st.markdown(
            f'<div role="status" style="margin:.6rem 0;padding:.7rem 1rem;border:1px solid {T["border2"]};'
            f'border-radius:12px;background:{T["card"]};font-size:.9rem;color:{T["text2"]};'
            f'font-family:DM Sans,sans-serif;">⏳ Sto preparando il kit'
            + (f' (ancora {len(_coda_kit)} dopo questo passaggio)' if _coda_kit else '')
            + '. Ci vuole circa un minuto: non toccare la pagina.</div>',
            unsafe_allow_html=True
        )
    if _kit_pronti:
        st.markdown(
            f'<div style="font-size:.85rem;color:{T["text2"]};font-family:DM Sans,sans-serif;margin:.3rem 0 .6rem;">'
            f'Pronti nel kit: <b>{_esc(" · ".join(e["etichetta"] for e in _kit_pronti))}</b></div>',
            unsafe_allow_html=True
        )

    # Una riga per documento (titolo + descrizione a sinistra, azione a destra), per gruppo
    st.markdown(f'<div class="variant-section-label" style="margin-top:.6rem;">Per la verifica</div>',
                unsafe_allow_html=True)
    _rw = []
    for _k_riga in range(5):
        if _k_riga == 2 and not WORD_ATTIVO:
            # riga del Word: spenta (conversione non affidabile). Il codice resta, ma scrive in contenitori nascosti.
            st.markdown('<style>[class*="st-key-word_nascosto"]{display:none !important;}</style>', unsafe_allow_html=True)
            _rw.append((st.container(key="word_nascosto_a"), st.container(key="word_nascosto_b")))
            continue
        with st.container(border=True):
            _rw.append(st.columns([3.4, 1.6], vertical_alignment="center", gap="medium"))
    # Ordine a schermo: Soluzioni, Fila B, Word, BES/DSA, Griglia (le più richieste per prime)
    (_vc3, _vb3), (_vc1, _vb1), (_vc5, _vb5), (_vc2, _vb2), (_vc4, _vb4) = _rw
    st.markdown(f'<div class="variant-section-label" style="margin-top:.9rem;">Per la classe</div>',
                unsafe_allow_html=True)
    with st.container(border=True):
        _vc6, _vb6 = st.columns([3.4, 1.6], vertical_alignment="center", gap="medium")

    # ── FILA B ────────────────────────────────────────────────────────────────
    with _vc1:
        _b_pdf = vB.get("pdf")
        _b_lat = vB.get("latex")

        st.markdown(
            f'<div class="variant-card variant-card-blue">'
            f'  <div class="variant-card-header">'
            f'    <span class="variant-card-icon">📋</span>'
            f'    <span class="variant-card-title">Fila B{_PRO}</span>'
            f'  </div>'
            f'  <div class="variant-card-desc">Stessa struttura e stessi punteggi con dati diversi, contro la copiatura. Pronta in pochi secondi.</div>'
            f'</div>',
            unsafe_allow_html=True
        )
        with _vb1:
            if _b_pdf:
                _dl(
                    f"⬇ Scarica Fila B (PDF) · {_stima(_b_pdf)}",
                    data=_b_pdf, file_name=arg_str+"_FilaB.pdf",
                    mime="application/pdf", use_container_width=True, key="dl_pdf_B_v2",
                )
            elif _b_lat:
                if st.button("📄 Crea PDF Fila B", key="compile_B_v2",
                             use_container_width=True, type="secondary"):
                    with st.spinner("Compilazione PDF Fila B in corso…"):
                        _pdf_bc, _ = compila_pdf(_b_lat)
                    if _pdf_bc:
                        st.session_state.verifiche["B"]["pdf"] = _pdf_bc; st.rerun()
            elif _pro_bloccato("fila_b"):
                _pulsante_pro("fila_b", "pro_fila_b")
            else:
                if st.button("⚡ Genera Fila B", key="one_click_B_v2",
                             use_container_width=True, type="secondary"):
                    st.session_state["_gen_fila_b"] = True; st.rerun()

        if st.session_state.get("_gen_fila_b"):
            st.session_state["_gen_fila_b"] = False
            _ph_b = st.empty()
            _ph_b.markdown(_skeleton_html("⚡", "Generazione Fila B…",
                           "Cambio numeri · Verifica coerenza · Controllo qualità"), unsafe_allow_html=True)
            try:
                _mod_b = crea_modello(mod_id).per("variante")
                _latex_b_new = _mod_b.generate_content(
                    [prompt_variante_rapida(_latex_per_ai(vA.get("latex","")), mat_str)],
                    generation_config={"temperature": 0.7},
                ).text.strip()
                if _latex_b_new.startswith("```"):
                    _latex_b_new = re.sub(r"^```[a-z]*\n?","",_latex_b_new)
                    _latex_b_new = re.sub(r"\n?```$","",_latex_b_new)
                # il logo della Fila A passa anche alla Fila B (intestazione della A + esercizi della B)
                _latex_b_new = copia_intestazione_con_logo(vA.get("latex", ""), _latex_b_new)
                _pdf_b_new, _ = compila_pdf(_latex_b_new)
                st.session_state.verifiche["B"]["latex"] = _latex_b_new
                _salva_variante_storico("latex_b", _latex_b_new)
                _registra_evento("fila_b", modello=mod_id, verifica_id=st.session_state.get("_storico_id"))
                if _pdf_b_new: st.session_state.verifiche["B"]["pdf"] = _pdf_b_new
                _ph_b.empty()
                if _pdf_b_new:
                    st.toast("✅ Fila B pronta!", icon="⚡")
                else:
                    st.toast("Fila B creata, ma il PDF non è ancora pronto: premi «Crea PDF Fila B».", icon="⚠️")
                st.rerun()
            except Exception as _e:
                _ph_b.empty()
                st.session_state["_kit_coda"] = []   # un errore ferma la coda del kit
                _mostra_errore("Non sono riuscito a creare la Fila B", _e,
                               riprova_flag="_gen_fila_b", riprova_key="riprova_fila_b")

    # ── BES/DSA ───────────────────────────────────────────────────────────────
    with _vc2:
        _r_pdf = vR.get("pdf")
        _r_lat = vR.get("latex")

        st.markdown(
            f'<div class="variant-card variant-card-violet">'
            f'  <div class="variant-card-header">'
            f'    <span class="variant-card-icon">🌟</span>'
            f'    <span class="variant-card-title">Versione BES/DSA{_PRO}</span>'
            f'  </div>'
            f'  <div class="variant-card-desc">Per studenti con BES o DSA: linguaggio più semplice e struttura alleggerita.</div>'
            f'</div>',
            unsafe_allow_html=True
        )
        with _vb2:
            if _r_pdf:
                _dl(
                    f"⬇ Scarica BES/DSA (PDF) · {_stima(_r_pdf)}",
                    data=_r_pdf, file_name=arg_str+"_BES_FilaA.pdf",
                    mime="application/pdf", use_container_width=True, key="dl_pdf_R_v2",
                )
            elif _r_lat:
                if st.button("📄 Crea PDF BES/DSA", key="compile_R_v2",
                             use_container_width=True, type="secondary"):
                    with st.spinner("Compilazione PDF BES/DSA in corso…"):
                        _pdf_rc, _ = compila_pdf(_r_lat)
                    if _pdf_rc:
                        st.session_state.verifiche["R"]["pdf"] = _pdf_rc; st.rerun()
            elif _pro_bloccato("bes"):
                _pulsante_pro("bes", "pro_bes")
            else:
                if st.button("🌟 Genera BES/DSA", key="one_click_R_v2",
                             use_container_width=True, type="secondary"):
                    st.session_state["_gen_bes"] = True; st.rerun()

        if st.session_state.get("_gen_bes"):
            st.session_state["_gen_bes"] = False
            _ph_r = st.empty()
            _ph_r.markdown(_skeleton_html("🌟","Versione BES/DSA…","Semplificazione · Adattamento"),
                           unsafe_allow_html=True)
            try:
                res_r = _genera_variante("R", mod_id, gp, vA)
                st.session_state.verifiche["R"] = {**vR, **res_r}
                _salva_variante_storico("latex_r", res_r.get("latex"))
                _registra_evento("bes", modello=mod_id, verifica_id=st.session_state.get("_storico_id"))
                _ph_r.empty(); st.toast("✅ BES/DSA pronta!", icon="🌟"); st.rerun()
            except Exception as _e:
                _ph_r.empty()
                st.session_state["_kit_coda"] = []   # un errore ferma la coda del kit
                _mostra_errore("Non sono riuscito a creare la versione BES/DSA", _e,
                               riprova_flag="_gen_bes", riprova_key="riprova_bes")

    # ── SOLUZIONI ─────────────────────────────────────────────────────────────
    with _vc3:
        _s_pdf = vS.get("pdf")
        _s_lat = vS.get("latex")

        st.markdown(
            f'<div class="variant-card variant-card-green">'
            f'  <div class="variant-card-header">'
            f'    <span class="variant-card-icon">📝</span>'
            f'    <span class="variant-card-title">Soluzioni{_PRO}</span>'
            f'  </div>'
            f'  <div class="variant-card-desc">Risposte e svolgimenti riservati al docente: niente correzione da preparare a mano.</div>'
            f'</div>',
            unsafe_allow_html=True
        )
        with _vb3:
            if _s_pdf:
                _dl(
                    f"⬇ Scarica Soluzioni (PDF) · {_stima(_s_pdf)}",
                    data=_s_pdf, file_name=arg_str+"_Soluzioni.pdf",
                    mime="application/pdf", use_container_width=True, key="dl_pdf_S_v2",
                )
            elif _s_lat:
                if st.button("📄 Crea PDF Soluzioni", key="compile_S_v2",
                             use_container_width=True, type="secondary"):
                    with st.spinner("Compilazione PDF Soluzioni in corso…"):
                        _pdf_sc, _ = compila_pdf(_s_lat)
                    if _pdf_sc:
                        st.session_state.verifiche["S"]["pdf"] = _pdf_sc; st.rerun()
            elif _pro_bloccato("soluzioni"):
                _pulsante_pro("soluzioni", "pro_soluzioni")
            else:
                if st.button("✅ Genera Soluzioni", key="one_click_S_v2",
                             use_container_width=True, type="secondary"):
                    st.session_state["_gen_sol"] = True; st.rerun()

        if st.session_state.get("_gen_sol"):
            st.session_state["_gen_sol"] = False
            _ph_s = st.empty()
            _ph_s.markdown(_skeleton_html("✅","Generazione soluzioni…","Svolgimenti · Risposte"),
                           unsafe_allow_html=True)
            try:
                res_s = _genera_variante("S", mod_id, gp, vA)
                st.session_state.verifiche["S"] = {**vS, **res_s}
                _ph_s.empty(); st.toast("✅ Soluzioni pronte!", icon="✅"); st.rerun()
            except Exception as _e:
                _ph_s.empty()
                st.session_state["_kit_coda"] = []   # un errore ferma la coda del kit
                _mostra_errore("Non sono riuscito a creare le soluzioni", _e,
                               riprova_flag="_gen_sol", riprova_key="riprova_sol")

    # ── GENERA DOCX — 5a card ──────────────────────────────────────────────
    with _vc5:
        _docx_a   = vA.get("docx")
        _docx_key = "_docx_gen_A_card"
        st.markdown(
            f'<div class="variant-card variant-card-teal">'
            f'  <div class="variant-card-header">'
            f'    <span class="variant-card-icon">📝</span>'
            f'    <span class="variant-card-title">Formato Word{_PRO}</span>'
            f'  </div>'
            f'  <div class="variant-card-desc">File .docx modificabile con Word o Google Docs.</div>'
            f'</div>',
            unsafe_allow_html=True
        )
        with _vb5:
            if _docx_a:
                _dl(
                    f"⬇ Scarica Word (.docx) · {_stima(_docx_a)}",
                    data=_docx_a,
                    file_name=arg_str + "_FilaA.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                    key="dl_docx_A_card",
                )
            elif vA.get("latex") and _pro_bloccato("word"):
                _pulsante_pro("word", "pro_word")
            elif vA.get("latex"):
                if st.button("📝 Genera Word", key="gen_docx_A_card",
                             use_container_width=True, type="secondary"):
                    st.session_state[_docx_key] = True
                if st.session_state.get(_docx_key, False):
                    with st.spinner("Conversione in formato Word in corso… (30–60 sec)"):
                        try:
                            _db, _emsg = latex_to_docx_via_ai(_latex_per_ai(vA["latex"]), con_griglia=con_griglia)
                        except Exception as _e:
                            _db, _emsg = None, str(_e)
                    st.session_state[_docx_key] = False
                    if _db:
                        st.session_state.verifiche["A"]["docx"] = _db; st.rerun()
                    else:
                        _mostra_errore("Non sono riuscito a creare il file Word", _emsg,
                                       riprova_flag=_docx_key, riprova_key="riprova_word",
                                       consiglio="Riprova: la conversione a volte richiede un secondo tentativo.")
            else:
                st.caption("PDF non ancora disponibile")

    # ── GRIGLIA DI VALUTAZIONE — 4a card one-click ──────────────────────────
    with _vc4:
        _rub_ready = bool(st.session_state.get('rubrica_testo'))
        st.markdown(
            f'<div class="variant-card variant-card-orange">'
            f'  <div class="variant-card-header">'
            f'    <span class="variant-card-icon">📊</span>'
            f'    <span class="variant-card-title">Griglia di Valutazione{_PRO}</span>'
            f'  </div>'
            f'  <div class="variant-card-desc">Griglia di valutazione per competenze (Linee Guida MIM).</div>'
            f'</div>',
            unsafe_allow_html=True
        )
        with _vb4:
            if _rub_ready:
                # Genera DOCX al volo se non ancora cached
                if not st.session_state.get('_rubrica_docx'):
                    _docx_bytes = _rubrica_to_docx(
                        st.session_state.rubrica_testo,
                        materia=mat_str,
                        livello=scu_str,
                        argomento=arg_str,
                    )
                    if _docx_bytes:
                        st.session_state['_rubrica_docx'] = _docx_bytes
                _rub_docx = st.session_state.get('_rubrica_docx')
                if _rub_docx:
                    _dl(
                        '⬇ Scarica Griglia (.docx)',
                        data=_rub_docx,
                        file_name=arg_str + '_GrigliaValutazione.docx',
                        mime='application/vnd.openxmlformats-officedocument'
                             '.wordprocessingml.document',
                        key='dl_rubrica_docx_v2', use_container_width=True,
                    )
                else:
                    _dl(
                        '⬇ Scarica griglia (.txt)',
                        data=st.session_state.rubrica_testo.encode('utf-8'),
                        file_name=arg_str + '_Griglia.txt',
                        mime='text/plain', key='dl_rubrica_v2', use_container_width=True,
                    )
            elif _pro_bloccato("griglia"):
                _pulsante_pro("griglia", "pro_griglia")
            else:
                if st.button('📊 Genera Griglia', key='btn_gen_griglia_v2',
                             use_container_width=True, type="secondary"):
                    st.session_state._rubrica_gen = True
                    st.rerun()
        if st.session_state.get('_rubrica_gen') and not _rub_ready:
            st.session_state['_rubrica_gen'] = False
            _rph = st.empty()
            _rph.info('📊 Generazione griglia in corso…')
            try:
                _mr = crea_modello(mod_id).per("griglia")
                _pr = prompt_rubrica_valutazione(
                    corpo_latex=_latex_per_ai(vA.get("latex", "")), materia=mat_str,
                    livello=scu_str, punti_totali=gp.get('punti_totali', 100),
                )
                _rr = _mr.generate_content(
                    [_pr], generation_config={"temperature": 0.5})
                st.session_state.rubrica_testo = _rr.text.strip()
                _rph.empty(); st.toast('Griglia pronta!', icon='📊'); st.rerun()
            except Exception as _er:
                _rph.empty()
                _mostra_errore("Non sono riuscito a creare la griglia di valutazione", _er,
                               riprova_flag="_rubrica_gen", riprova_key="riprova_griglia")

    # ── SCHEDA DI ALLENAMENTO — per la classe, da dare prima della verifica ──────
    with _vc6:
        st.markdown(
            f'<div class="variant-card variant-card-pink">'
            f'  <div class="variant-card-header">'
            f'    <span class="variant-card-icon">🎯</span>'
            f'    <span class="variant-card-title">Scheda di allenamento{_PRO} '
            f'<span style="font-size:.62rem;font-weight:800;letter-spacing:.06em;color:{T["success"]};'
            f'border:1px solid {T["success"]};border-radius:6px;padding:1px 6px;vertical-align:middle;">NOVITÀ</span></span>'
            f'  </div>'
            f'  <div class="variant-card-desc">Circa 40 esercizi graduati ★ ★★ ★★★ sugli stessi tipi di richiesta '
            f'della verifica, da dare alla classe per allenarsi prima.</div>'
            f'</div>',
            unsafe_allow_html=True
        )
        if vSC.get("avvisi"):
            for _av in vSC["avvisi"][:3]:
                st.caption(f"⚠️ {_av}")
        if vSC.get("pdf") and vSC.get("n"):
            st.caption(f"{vSC['n']} esercizi · controlla sempre il contenuto prima di darla agli studenti.")
    with _vb6:
        if vSC.get("pdf"):
            _dl(
                f"⬇ Scarica scheda (PDF) · {_stima(vSC['pdf'])}",
                data=vSC["pdf"], file_name=_nome_base_file(mat_str, arg_str) + "_Scheda_allenamento.pdf",
                mime="application/pdf", use_container_width=True, key="dl_pdf_SC",
            )
        elif _pro_bloccato("scheda"):
            _pulsante_pro("scheda", "pro_scheda")
        else:
            if st.button("🎯 Crea la scheda", key="one_click_SC", use_container_width=True, type="secondary",
                         disabled=bool(st.session_state.get("_gen_scheda"))):
                st.session_state["_gen_scheda"] = True
                st.rerun()

    if st.session_state.get("_gen_scheda"):
        st.session_state["_gen_scheda"] = False
        _ph_sc = st.empty()

        def _avanza_scheda(testo):
            _ph_sc.markdown(
                _skeleton_html("🎯", "Preparo la scheda di allenamento…",
                               f"{_esc(testo)} · circa 30 secondi, non toccare la pagina"),
                unsafe_allow_html=True)

        _avanza_scheda("Leggo la verifica")
        try:
            _res_sc = genera_scheda(
                crea_modello(mod_id), mat_str, scu_str, arg_str, vA.get("latex", ""),
                on_progress=_avanza_scheda,
            )
            _ph_sc.empty()
            if _res_sc.get("pdf"):
                st.session_state.verifiche["SC"] = {
                    "latex": _res_sc["latex"], "pdf": _res_sc["pdf"],
                    "n": _res_sc["n_esercizi"], "avvisi": _res_sc["avvisi"],
                }
                st.toast("Scheda di allenamento pronta!", icon="🎯")
                st.rerun()
            else:
                st.session_state.pop("_kit_coda", None)
                _mostra_errore("Non sono riuscito a impaginare la scheda", "compilazione PDF",
                               riprova_flag="_gen_scheda", riprova_key="riprova_scheda")
        except Exception as _e:
            _ph_sc.empty()
            st.session_state["_kit_coda"] = []   # un errore ferma la coda: «Prepara tutto il kit» riprende da qui
            _mostra_errore("Non sono riuscito a creare la scheda di allenamento", _e,
                           riprova_flag="_gen_scheda", riprova_key="riprova_scheda")

    # ═══════════════════════════════════════════════════════════════════════════
    #  IDEA #5 — CONDIVIDI CON IL DIPARTIMENTO
    # ═══════════════════════════════════════════════════════════════════════════
    spazio("md")

    _share_code = st.session_state._share_code
    _latex_a_share = vA.get("latex", "")

    if _latex_a_share:
        if _share_code:
            st.markdown(
                f'<div class="share-dept-card">'
                f'  <div class="share-dept-header">'
                f'    <span class="share-dept-icon">📤</span>'
                f'    <div class="share-dept-title-wrap">'
                f'      <div class="share-dept-title">Condividi con il Dipartimento</div>'
                f'      <div class="share-dept-subtitle">'
                f'I colleghi potranno visualizzare la tua verifica e generare la propria variante con un click.'
                f'      </div>'
                f'    </div>'
                f'  </div>'
                f'</div>',
                unsafe_allow_html=True
            )


        if _share_code:
            # Link già generato — mostra con copy
            _share_full_url = f"{SHARE_URL}?share={_share_code}"
            st.markdown(
                f'<div class="share-link-box">'
                f'  <div class="share-link-status">'
                f'    <span class="share-link-dot"></span>'
                f'    Link attivo · valido per 30 giorni dalla creazione'
                f'  </div>'
                f'  <div class="share-link-url">{_share_full_url}</div>'
                f'</div>',
                unsafe_allow_html=True
            )
            _sh_c1, _sh_c2 = st.columns([3, 1])
            with _sh_c1:
                # Copy button via components.html
                components.html(
                    "<style>body{margin:0;padding:0;background:transparent}"
                    f".cb{{background:{T['accent']};color:#0D1117;border:none;border-radius:8px;"
                    "padding:8px 16px;cursor:pointer;font-size:.82rem;font-weight:700;"
                    "font-family:DM Sans,sans-serif;width:100%;transition:all .15s}"
                    f".cb:hover{{filter:brightness(1.12);transform:translateY(-1px)}}"
                    f".cb.ok{{background:{T['success']};color:#fff}}</style>"
                    f"<button class='cb' id='cpb' onclick='doCopy()'>📋 Copia link</button>"
                    "<script>function doCopy(){"
                    f"var u='{_share_full_url}';var b=document.getElementById('cpb');"
                    "if(navigator.clipboard&&navigator.clipboard.writeText){"
                    "navigator.clipboard.writeText(u).then(function(){"
                    "b.className='cb ok';b.innerText='✅ Copiato!';"
                    "setTimeout(function(){b.className='cb';b.innerText='📋 Copia link'},2500)"
                    "}).catch(function(){b.innerText=u})"
                    "}else{b.innerText=u}}</script>",
                    height=42,
                )
            with _sh_c2:
                if st.button("🔄", key="share_new_link", help="Genera un nuovo link. Attenzione: il link precedente smetterà di funzionare."):
                    st.session_state._share_code = None
                    st.rerun()

            st.markdown(
                f'<div style="font-size:.7rem;color:{T["muted"]};margin-top:.3rem;'
                f'font-family:DM Sans,sans-serif;line-height:1.4;">'
                f'👥 Quando un collega apre il link, vede un\'anteprima e può generare '
                f'la propria variante con dati nuovi — senza accedere alla tua verifica originale.'
                f'</div>',
                unsafe_allow_html=True
            )
        else:
            # Genera link: una riga come le altre versioni
            with st.container(border=True):
                _sd1, _sd2 = st.columns([3.4, 1.6], vertical_alignment="center", gap="medium")
                _sd1.markdown(
                    '<div class="variant-card">'
                    '<div class="variant-card-header">'
                    '<span class="variant-card-icon">📤</span>'
                    '<span class="variant-card-title">Condividi con i colleghi</span></div>'
                    '<div class="variant-card-desc">Un link: chi lo apre vede l’anteprima e può generare la propria variante.</div>'
                    '</div>',
                    unsafe_allow_html=True,
                )
                with _sd2:
                    if st.button("Genera link", key="btn_share_gen", use_container_width=True):
                        st.session_state._share_generating = True
                        st.rerun()

            if st.session_state.get("_share_generating"):
                st.session_state._share_generating = False
                with st.spinner("📤 Creazione link di condivisione…"):
                    _new_code = _create_share_link(
                        latex_a=_latex_a_share,
                        materia=mat_str,
                        argomento=arg_str,
                        scuola=scu_str,
                        num_esercizi=gp.get("num_esercizi", 4),
                    )
                if _new_code:
                    st.session_state._share_code = _new_code
                    st.toast("📤 Link di condivisione creato!", icon="📤")
                    st.rerun()
                else:
                    st.error("Errore nella creazione del link. Riprova.")

    # Word per le altre versioni (la Fila A ha già la sua card "Formato Word")
    _ha_extra = vB.get("latex") or vR.get("latex") or vRB.get("latex") or vS.get("latex")
    if _ha_extra:
        with (st.expander("📝 Word delle altre versioni", expanded=False) if WORD_ATTIVO else st.container(key="word_nascosto_c")):
            def _show_extra_formats(fid, v, fname_suffix):
                if not v.get("latex"):
                    return
                fname = arg_str + "_" + fname_suffix
                _docx_key = "_docx_gen_" + fid
                st.markdown(f'<div class="s3-card-label">{fname_suffix.replace("_"," ")}</div>',
                            unsafe_allow_html=True)
                if v.get("docx"):
                    _dl(
                        f"📝 Word · {_stima(v['docx'])}",
                        data=v["docx"], file_name=fname+".docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True, key="dl_docx_"+fid+"_extra"
                    )
                else:
                    if st.button(f"📝 Genera Word — {fname_suffix.replace('_',' ')}",
                                 key="gen_docx_"+fid+"_extra", use_container_width=True):
                        st.session_state[_docx_key] = True
                    if st.session_state.get(_docx_key, False):
                        with st.spinner("Conversione in formato Word in corso…"):
                            try:
                                db, error_msg = latex_to_docx_via_ai(_latex_per_ai(v["latex"]), con_griglia=con_griglia)
                            except Exception as e:
                                db = None
                                error_msg = str(e)
                        st.session_state[_docx_key] = False
                        if db:
                            st.session_state.verifiche[fid]["docx"] = db; st.rerun()
                        else:
                            _mostra_errore("Non sono riuscito a creare il file Word", error_msg,
                                           riprova_flag=_docx_key, riprova_key="riprova_word_"+fid,
                                           consiglio="Riprova: la conversione a volte richiede un secondo tentativo.")
            _ef_c1, _ef_c2 = st.columns(2)
            with _ef_c1:
                if vR.get("latex"): _show_extra_formats("R", vR, "BES_FilaA")
            with _ef_c2:
                if vB.get("latex"): _show_extra_formats("B", vB, "FilaB")
                if vRB.get("latex"): _show_extra_formats("RB", vRB, "BES_FilaB")
                if vS.get("latex"): _show_extra_formats("S", vS, "Soluzioni")


    # Solo admin: sorgente LaTeX della Fila A, da copiare per diagnosticare grafici o impaginazione
    if _is_admin and vA.get("latex"):
        with st.expander("🔧 Strumenti admin — LaTeX sorgente (Fila A)", expanded=False):
            st.caption("Copia da qui il LaTeX se un grafico o l'impaginazione non vanno.")
            st.code(vA["latex"], language="latex")

    spazio("lg")


def _nuova_verifica() -> None:
    """Torna al form di creazione azzerando la verifica in corso (le versioni non salvate si perdono)."""
    st.session_state.stage            = STAGE_INPUT
    st.session_state["_prev_stage"]   = None
    st.session_state.input_percorso   = None
    st.session_state["_autoverifica"] = None
    _pulisci_stato_revisione()
    st.session_state.verifiche         = {
        "A": _vf(), "B": _vf(), "R": _vf(), "RB": _vf(),
        "S": {"latex": None, "testo": None, "pdf": None},
        "SC": {"latex": None, "pdf": None, "n": 0, "avvisi": []},
    }
    st.session_state.review_preamble   = ""
    st.session_state.review_blocks     = []
    st.session_state.review_sel_idx    = 0
    st.session_state.gen_params        = {}
    st.session_state.preview_images    = []
    st.session_state.preview_page      = 0
    st.session_state.last_preview_ts   = 0
    st.session_state.esercizi_custom       = []
    st.session_state.rubrica_testo         = None
    st.session_state["_rubrica_pdf"]       = None
    st.session_state["_rubrica_docx"]      = None
    st.session_state._rubrica_gen          = False
    st.session_state["_gen_fila_b"]       = False
    st.session_state["_gen_bes"]           = False
    st.session_state["_gen_sol"]           = False
    st.session_state["_gen_scheda"]       = False
    st.session_state["_kit_coda"]         = []
    st.session_state.analisi_docs_list  = []
    st.session_state.info_consolidate   = {}
    st.session_state["_analisi_rifiuto"] = None
    st.session_state["_facsimile_mode"] = False
    st.session_state._share_code       = None
    st.session_state._share_generating   = False
    st.session_state.pop("_storico_id", None)
    st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
#  ROUTING
# ═══════════════════════════════════════════════════════════════════════════════

# ── IDEA #5: Intercetta link condiviso ?share=CODE ────────────────────────────
_share_param = st.query_params.get("share", None)
_share_view_active = False

if _share_param and isinstance(_share_param, str) and len(_share_param) >= 6:
    _shared_record = _load_shared_verifica(_share_param)
    if _shared_record:
        _share_view_active = True
        _sh_mat  = _shared_record.get("materia", "")
        _sh_arg  = _shared_record.get("argomento", "")
        _sh_scu  = _shared_record.get("scuola", "")
        _sh_lat  = _shared_record.get("latex_a", "")
        _sh_date = _shared_record.get("created_at", "")[:10]
        _sh_n_es = _shared_record.get("num_esercizi", "?")
        # il titolo lo ha scelto un altro utente: va escapato prima di entrare nell'HTML
        _sh_mat_h, _sh_arg_h, _sh_scu_h = _esc(_sh_mat), _esc(_sh_arg), _esc(_sh_scu)
        _sh_date_h, _sh_n_es_h = _esc(_sh_date), _esc(_sh_n_es)

        st.markdown(
            f'<div class="shared-view-banner">'
            f'  <div class="shared-view-header">'
            f'    <span style="font-size:1.5rem;">📤</span>'
            f'    <div>'
            f'      <div class="shared-view-title">Verifica condivisa da un collega</div>'
            f'      <div class="shared-view-meta">'
            f'{_sh_mat_h} · {_sh_scu_h} · {_sh_arg_h}'
            f'      </div>'
            f'    </div>'
            f'  </div>'
            f'  <div class="shared-view-badges">'
            f'    <span class="shared-view-badge">📝 {_sh_n_es_h} esercizi</span>'
            f'    <span class="shared-view-badge">📅 {_sh_date_h}</span>'
            f'    <span class="shared-view-badge">🔒 Solo lettura</span>'
            f'  </div>'
            f'</div>',
            unsafe_allow_html=True
        )

        # Compila PDF per anteprima
        if _sh_lat:
            _sh_pdf, _sh_err = _pdf_da_latex(_sh_lat)   # in cache: non si ricompila a ogni clic
            if _sh_pdf:
                _sh_imgs, _ = pdf_to_images_bytes(_sh_pdf)
                if _sh_imgs:
                    st.markdown(
                        f'<div style="font-size:.72rem;font-weight:700;color:{T["muted"]};'
                        f'text-transform:uppercase;letter-spacing:.05em;margin-bottom:.5rem;">'
                        f'📄 Anteprima verifica</div>',
                        unsafe_allow_html=True
                    )
                    _sh_cols = st.columns(min(3, len(_sh_imgs)))
                    for _shi, _sh_img in enumerate(_sh_imgs[:3]):
                        with _sh_cols[_shi]:
                            st.image(_sh_img, use_container_width=True, caption=f"Pag. {_shi+1}")

                _dl(
                    f"📄  Scarica PDF originale",
                    data=_sh_pdf, file_name=f"{_sh_arg}_condivisa.pdf",
                    mime="application/pdf", use_container_width=True,
                    key="dl_shared_pdf",
                )

            spazio("sm")

            # CTA: genera la tua variante
            st.markdown(
                f'<div class="shared-cta-card">'
                f'  <div class="shared-cta-icon">🎲</div>'
                f'  <div class="shared-cta-title">Genera la tua variante</div>'
                f'  <div class="shared-cta-desc">'
                f'Crea una versione con dati nuovi e stessa struttura — '
                f'perfetta come Fila B per la tua classe.'
                f'  </div>'
                f'</div>',
                unsafe_allow_html=True
            )

            if st.session_state.utente:
                # Utente autenticato → può generare variante
                if st.button("🎲 Genera la mia variante", type="primary",
                             use_container_width=True, key="btn_shared_variant"):
                    _increment_clone_count(_share_param)
                    st.session_state.verifiche["A"]["latex"] = _sh_lat
                    st.session_state.verifiche["A"]["latex_originale"] = _sh_lat
                    if _sh_pdf:
                        st.session_state.verifiche["A"]["pdf"] = _sh_pdf
                        st.session_state.verifiche["A"]["preview"] = True
                        _sh_imgs_2, _ = pdf_to_images_bytes(_sh_pdf)
                        st.session_state.preview_images = _sh_imgs_2 or []
                    _sh_pre, _sh_blks = extract_blocks(_sh_lat)
                    if _sh_blks:
                        st.session_state.review_preamble = _sh_pre
                        st.session_state.review_blocks = _sh_blks
                    st.session_state.gen_params = {
                        "materia":    _sh_mat, "difficolta": _sh_scu,
                        "argomento":  _sh_arg, "num_esercizi": _sh_n_es,
                        "mostra_punteggi": True, "punti_totali": 100,
                        "con_griglia": True,
                    }
                    st.session_state.stage = STAGE_FINAL
                    # Genera Fila B automaticamente
                    st.session_state["_gen_fila_b"] = True
                    st.query_params.clear()
                    st.rerun()
            else:
                st.info(
                    "🔐 Per generare la tua variante, accedi con il tuo account VerificAI. "
                    "È gratis!"
                )
                if st.button("🔐 Accedi per generare", use_container_width=True, key="btn_shared_login"):
                    st.query_params.clear()
                    st.rerun()

            st.markdown(
                f'<div style="text-align:center;font-size:.72rem;color:{T["muted"]};'
                f'font-family:DM Sans,sans-serif;margin-top:1rem;">'
                f'Link condiviso con VerificAI · <a href="{SHARE_URL}" '
                f'style="color:{T["accent"]};">Crea la tua prima verifica gratis →</a>'
                f'</div>',
                unsafe_allow_html=True
            )
    else:
        st.warning("⚠️ Link di condivisione non valido o scaduto.")
        if st.button("← Torna alla home", key="btn_shared_back"):
            st.query_params.clear()
            st.rerun()

if not _share_view_active:
    # Niente più header fisso né stepper (il titolo di ogni pagina dice già dove si è):
    # si toglie solo quello che una sessione già aperta può avere ancora nella pagina.
    components.html("""
<script>
(function() {
  var doc = window.parent.document;
  var old = doc.getElementById('_vai_sticky_hdr');
  if (old) old.remove();
  var main = doc.querySelector('.main .block-container');
  if (main) main.style.paddingTop = '';
})();
</script>""", height=0)

# ── SCROLL TO TOP on stage change ─────────────────────────────────────────────
_current_stage = st.session_state.stage
_prev_stage = st.session_state.get("_prev_stage", None)
if _prev_stage != _current_stage:
    st.session_state["_prev_stage"] = _current_stage
    components.html(
        "<script>"
        "(function(){"
        "var tries=0,max=12;"
        "function scrollTop(){"
        "  var d=window.parent.document;"
        "  var targets=["
        "    d.querySelector('.main'),"
        "    d.querySelector('.main .block-container'),"
        "    d.querySelector('[data-testid=\"stAppViewContainer\"]'),"
        "    d.querySelector('[data-testid=\"stMainBlockContainer\"]'),"
        "    d.documentElement,"
        "    d.body"
        "  ];"
        "  targets.forEach(function(t){if(t){t.scrollTop=0;}});"
        "  window.parent.scrollTo({top:0,left:0,behavior:'instant'});"
        "  if(tries++<max)setTimeout(scrollTop,120);"
        "}"
        "scrollTop();"
        "var bc=window.parent.document.querySelector('.main .block-container');"
        "if(bc){bc.classList.remove('stage-enter');void bc.offsetWidth;"
        "bc.classList.add('stage-enter');"
        "setTimeout(function(){bc.classList.remove('stage-enter');},500);}"
        "})();"
        "</script>",
        height=0
    )

if not _share_view_active:
    _current = _current_stage
    if _current == STAGE_PREVIEW:   # sessioni aperte prima dell'unione di anteprima e download
        st.session_state.stage = _current = STAGE_FINAL
    if   _current == STAGE_INPUT:   _render_stage_input()
    elif _current == STAGE_REVIEW:  _render_stage_review()
    elif _current == STAGE_FINAL:   _render_stage_final()
    elif _current == STAGE_MIE_VERIFICHE: _render_le_tue_verifiche()
    elif _current == STAGE_UPGRADE:
        def _esci_da_upgrade():
            st.session_state.stage = st.session_state.get("_upgrade_da") or STAGE_INPUT
            st.rerun()
        _gia_usato = (not ENT.assaggio) and ENT.piano == "free" and MONETIZZAZIONE_ATTIVA

        def _attiva_codice(codice):
            esito = attiva_licenza(supabase_admin, st.session_state.utente.id, codice)
            if esito.ok:
                _abbonamento_utente.clear()          # il piano si rilegge subito
                _registra_evento("licenza_attivata")
            return esito.ok, esito.messaggio, esito.dettaglio_admin

        render_upgrade(_esci_da_upgrade, st.session_state.get("_upgrade_funzione"), _gia_usato,
                       e_pro=(ENT.piano == "pro" and not _SIM), email=getattr(st.session_state.utente, "email", None),
                       on_attiva=_attiva_codice, e_admin=_is_admin)
    elif _current == STAGE_BANCA:
        if _is_admin:
            def _esci_dalla_banca():
                st.session_state.stage = STAGE_INPUT
                st.rerun()
            render_banca(supabase_admin, _esci_dalla_banca)
        else:                                   # la banca è riservata all'admin
            st.session_state.stage = STAGE_INPUT
            st.rerun()


# ── FOOTER ────────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="app-footer">'
    'VerificAI · Versione Beta · '
    '<a href="?pagina=privacy" target="_blank" rel="noopener" style="color:inherit;">Privacy</a>'
    + ((' · <a href="?pagina=termini" target="_blank" rel="noopener" style="color:inherit;">Termini</a>'
        ' · <a href="?pagina=rimborsi" target="_blank" rel="noopener" style="color:inherit;">Rimborsi</a>') if LEGALE_PRONTO else '')
    + '</div>',
    unsafe_allow_html=True
)


