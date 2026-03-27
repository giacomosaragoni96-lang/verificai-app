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
# Dev container exposes port 8501
```

System packages required (see `packages.txt`): `texlive-latex-extra`, `poppler-utils`, `pandoc` — needed for PDF compilation and document conversion.

## Architecture

The app is a **monolithic Streamlit app** with clean module separation. All UI state lives in `st.session_state`. The main flow is a 4-stage state machine in `main.py`:

```
INPUT → PREVIEW → REVIEW → FINAL → Export (PDF / DOCX)
```

**Core modules (all in root directory):**

| Module | Role |
|--------|------|
| `main.py` | Streamlit entry point, state machine, all UI rendering |
| `generation.py` | AI generation logic — **no Streamlit imports**, pure business logic |
| `latex_utils.py` | LaTeX parsing, validation, PDF compilation via `pdflatex`, point scaling |
| `docx_export.py` | LaTeX → DOCX conversion pipeline using Gemini + TikZ → PNG rendering |
| `prompts.py` | All Gemini prompt templates (generation, QA, variations, solutions) |
| `auth.py` | Supabase JWT auth, token from URL query param `?rt=TOKEN`, usage tracking |
| `config.py` | Constants only — app name, AI model IDs, admin emails, monthly limits |
| `styles.py` | Dynamic CSS generation for light ("giorno") and dark ("notte") themes |
| `sidebar.py` | Sidebar UI: model picker, theme toggle, usage counter, history list |
| `ui_helpers.py` | Reusable UI components: KaTeX math rendering, buttons, progress bars |

## Key Architectural Decisions

- **`generation.py` has no Streamlit imports** — it's the only module that can be called standalone/tested without a Streamlit context.
- **Auth is token-based** via URL query param `?rt=TOKEN` (not cookies) for Streamlit Cloud compatibility.
- **Three AI model tiers**: `gemini-2.5-flash-lite` (Free), `gemini-2.5-flash` (Pro), `gemini-2.5-pro` (STEM/Gold) — controlled by user subscription level.
- **Monthly generation limit** (`LIMITE_MENSILE = 5`) enforced via Supabase counter.
- **LaTeX is the intermediate format** — the app generates LaTeX, compiles to PDF, and converts to DOCX from LaTeX.

## External Services

- **Google Gemini API** (`GOOGLE_API_KEY`) — AI generation engine
- **Supabase** — auth, session storage, usage tracking (credentials in `.streamlit/secrets.toml`)
- **Mathpix** — optional OCR for uploaded documents; app degrades gracefully if credentials missing

## Language

The entire codebase, UI strings, comments, and config are **in Italian**. All AI prompts generate Italian-language content.
