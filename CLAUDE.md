# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**VerificAI** is an Italian Streamlit web app for teachers to generate custom school exam/quiz documents ("verifiche") using Google Gemini AI. It outputs LaTeX-compiled PDFs and Word documents.

## Running the App

```bash
# Install Python dependencies
pip install -r requirements.txt

# Run the Streamlit app (local dev)
streamlit run main.py

# Deployed at https://verificai.streamlit.app
# Dev container (Python 3.11) exposes port 8501
```

System packages required (see `packages.txt`): `texlive-latex-extra`, `texlive-fonts-recommended`, `texlive-lang-italian`, `poppler-utils`, `pandoc` — needed for PDF compilation and document conversion.

There are **no tests, no CI/CD, no linter config**. The only validation is `python -c "import py_compile; py_compile.compile('file.py', doraise=True)"`.

## Architecture

The app is a **monolithic Streamlit app** with clean module separation. All UI state lives in `st.session_state`. The main flow is a 5-stage state machine in `main.py`:

```
INPUT → PREVIEW → REVIEW → FINAL → Export (PDF / DOCX)
              ↗
  MIE_VERIFICHE (standalone page: saved history)
```

The INPUT stage itself is a sub-router with multiple paths:
- **Percorso A** — Upload-driven wizard (file → AI analysis → generation)
- **Percorso B** — Manual form (subject, topic, exercises → generation)
- **Percorso FACSIMILE** — Reproduce an existing exam from uploaded file
- **QA mode** — Ask questions about uploaded documents

### Module Boundaries

| Layer | Modules | Streamlit dependency |
|-------|---------|---------------------|
| **UI** | `main.py`, `sidebar.py`, `ui_helpers.py`, `styles.py`, `auth.py` | Yes |
| **Business logic** | `generation.py` | **No** — pure functions, testable standalone |
| **Document pipeline** | `latex_utils.py`, `docx_export.py` | **No** — pure functions |
| **Configuration** | `config.py`, `prompts.py` | **No** — constants and prompt templates |

This separation is intentional: `generation.py`, `latex_utils.py`, and `docx_export.py` must never import Streamlit.

### CSS / Theming

`styles.py` generates a single large CSS string via `get_css(T: dict)` where `T` is a theme dictionary from `config.py`. There are **7 themes** (carta, notte, oceano, foresta, tramonto, lavanda, cioccolato). The sidebar always has a dark background regardless of theme — sidebar text colors must always be light.

Streamlit's internal CSS uses `color-scheme: dark` and CSS custom properties that bleed through. The CSS in `styles.py` fights this with high-specificity selectors and `!important`. The `_is_light_color()` helper determines if a hex color is light/dark for adaptive styling (e.g., expander headers).

`ui_helpers.py` injects additional HTML/JS via `st.markdown(unsafe_allow_html=True)` and `components.html()` for features Streamlit doesn't natively support (sticky header, KaTeX math rendering, step progress bar).

### AI Model Routing

Three subscription tiers control which Gemini model is used (`config.py: get_model_id_per_piano`):
- **Free** → `gemini-2.5-flash-lite` (fixed)
- **Pro** → `gemini-2.5-flash` (upgrades to Pro for STEM subjects)
- **Gold** → `gemini-2.5-pro` (full access)

STEM subjects (`MATERIE_STEM` in config.py) get automatic model upgrades for Pro users.

### Document Pipeline

```
AI (Gemini) → LaTeX source → pdflatex → PDF
                           → Gemini conversion → DOCX
                           → TikZ extraction → PNG rendering
```

`latex_utils.py` handles: parsing exercises into blocks (`extract_blocks`), point scaling (`riscala_punti`), grid injection, PDF compilation. Points are parsed from `(N pt)` patterns and can be redistributed across exercises.

`docx_export.py` converts LaTeX → DOCX by sending the LaTeX to Gemini for markdown conversion, then building the DOCX via `python-docx`. TikZ/pgfplots diagrams are rendered to PNG via `pdflatex` + `pdf2image`.

## Key Architectural Decisions

- **`generation.py` has no Streamlit imports** — it's the only module that can be called standalone/tested without a Streamlit context.
- **Auth is token-based** via URL query param `?rt=TOKEN` (not cookies) for Streamlit Cloud compatibility.
- **Monthly generation limit** (`LIMITE_MENSILE = 5`) enforced via Supabase counter, bypassed for admin emails.
- **LaTeX is the intermediate format** — the app generates LaTeX, compiles to PDF, and converts to DOCX from LaTeX.
- **School-type calibration** — `CALIBRAZIONE_SCUOLA` in config.py maps 13 school types to detailed prompt context (cognitive level, vocabulary, complexity).
- **Optional dependencies degrade gracefully** — Mathpix OCR and `st_yled` are imported with try/except; features disable silently if missing.

## External Services

- **Google Gemini API** (`GOOGLE_API_KEY`) — AI generation engine
- **Supabase** — auth, session storage, usage tracking (credentials in `.streamlit/secrets.toml`)
- **Mathpix** — optional OCR for uploaded documents; app degrades gracefully if credentials missing

## Language

The entire codebase, UI strings, comments, and config are **in Italian**. All AI prompts generate Italian-language content.
