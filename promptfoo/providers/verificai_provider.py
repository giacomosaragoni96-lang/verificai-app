"""
VerificAI — Custom PromptFoo Provider
═══════════════════════════════════════════════════════════════════════════════
Questo provider ricostruisce i prompt ESATTAMENTE come fa l'app,
chiamando le funzioni reali di prompts.py.

PromptFoo chiama call_api(prompt, options, context) dove:
  - prompt: il contenuto del file .txt (noi usiamo solo il tipo come marker)
  - options: configurazione del provider
  - context: contiene context.vars con le variabili del test case
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import sys
import json

# ── Aggiungi la root del progetto al path per importare prompts.py ──────────
# IMPORTANTE: adatta questo path alla posizione reale del tuo progetto
PROJECT_ROOT = os.environ.get("VERIFICAI_ROOT", os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ── Import delle funzioni prompt reali ──────────────────────────────────────
from prompts import (
    prompt_titolo,
    prompt_corpo_verifica,
    prompt_controllo_qualita,
    prompt_versione_b,
    prompt_versione_ridotta,
    prompt_soluzioni,
    prompt_variante_rapida,
    prompt_rigenera_blocco,
)
from config import CALIBRAZIONE_SCUOLA


def _build_prompt(prompt_type: str, vars_dict: dict) -> str:
    """
    Costruisce il prompt esatto come farebbe generation.py,
    a partire dal tipo e dalle variabili del test case.
    """
    pt = prompt_type.strip().lower()

    if pt == "titolo":
        return prompt_titolo(
            materia=vars_dict["materia"],
            argomento=vars_dict["argomento"],
        )

    if pt == "corpo":
        livello = vars_dict.get("livello", "Generico")
        calibrazione = CALIBRAZIONE_SCUOLA.get(livello, CALIBRAZIONE_SCUOLA["Generico"])
        e_mat = vars_dict.get("e_mat", False)
        mostra_punteggi = vars_dict.get("mostra_punteggi", True)

        # Preambolo fisso semplificato (non serve il vero preambolo per testare il prompt)
        preambolo = "\\documentclass[a4paper,11pt]{article}\\usepackage[utf8]{inputenc}"

        return prompt_corpo_verifica(
            materia=vars_dict["materia"],
            argomento=vars_dict["argomento"],
            calibrazione=calibrazione,
            durata=vars_dict.get("durata", "60 minuti"),
            num_esercizi=int(vars_dict.get("num_esercizi", 5)),
            punti_totali=int(vars_dict.get("punti_totali", 100)),
            mostra_punteggi=_to_bool(mostra_punteggi),
            con_griglia=_to_bool(vars_dict.get("con_griglia", False)),
            note_generali=vars_dict.get("note_generali", ""),
            istruzioni_esercizi=vars_dict.get("istruzioni_esercizi", ""),
            e_mat=_to_bool(e_mat),
            titolo_header=vars_dict.get("titolo_header", "Verifica"),
            preambolo_fisso=preambolo,
            mathpix_context=vars_dict.get("mathpix_context", None),
        )

    if pt == "qa":
        return prompt_controllo_qualita(
            materia=vars_dict["materia"],
            difficolta=vars_dict.get("livello", "Generico"),
            corpo_latex=vars_dict["corpo_latex"],
            mostra_punteggi=_to_bool(vars_dict.get("mostra_punteggi", True)),
            punti_totali=int(vars_dict.get("punti_totali", 100)),
        )

    if pt == "versione_b":
        return prompt_versione_b(
            corpo_latex=vars_dict["corpo_latex"],
        )

    if pt == "ridotta":
        return prompt_versione_ridotta(
            corpo_latex=vars_dict["corpo_latex"],
            materia=vars_dict["materia"],
            perc_ridotta=int(vars_dict.get("perc_ridotta", 30)),
            mostra_punteggi=_to_bool(vars_dict.get("mostra_punteggi", True)),
            punti_totali=int(vars_dict.get("punti_totali", 100)),
            versione_label=vars_dict.get("versione_label", ""),
        )

    if pt == "soluzioni":
        return prompt_soluzioni(
            corpo_latex=vars_dict["corpo_latex"],
            materia=vars_dict["materia"],
            versione_label=vars_dict.get("versione_label", ""),
        )

    if pt == "variante_rapida":
        return prompt_variante_rapida(
            corpo_latex=vars_dict["corpo_latex"],
            materia=vars_dict["materia"],
        )

    if pt == "rigenera_blocco":
        return prompt_rigenera_blocco(
            materia=vars_dict["materia"],
            blocco_latex=vars_dict["blocco_latex"],
            istruzione=vars_dict["istruzione"],
            mostra_punteggi=_to_bool(vars_dict.get("mostra_punteggi", True)),
        )

    raise ValueError(
        f"prompt_type sconosciuto: '{pt}'. "
        f"Usa: titolo, corpo, qa, versione_b, ridotta, soluzioni, variante_rapida, rigenera_blocco"
    )


def _to_bool(val) -> bool:
    """Converte stringhe YAML/JSON in bool Python."""
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.lower() in ("true", "1", "yes", "sì")
    return bool(val)


def call_api(prompt: str, options: dict, context: dict) -> dict:
    """
    Entry point chiamato da PromptFoo.

    Ritorna: { "output": "...", "tokenUsage": {...} }
    """
    import google.generativeai as genai

    # ── Configura Gemini ────────────────────────────────────────────────────
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return {"error": "GEMINI_API_KEY non impostata. Esporta: export GEMINI_API_KEY=..."}

    genai.configure(api_key=api_key)

    # ── Determina il modello ────────────────────────────────────────────────
    model_id = options.get("config", {}).get("model_id", "gemini-2.5-flash-lite")
    temperature = options.get("config", {}).get("temperature", 0.7)

    model = genai.GenerativeModel(
        model_name=model_id,
        generation_config=genai.GenerationConfig(
            temperature=temperature,
            max_output_tokens=4096,
        ),
    )

    # ── Costruisci il prompt reale ──────────────────────────────────────────
    vars_dict = context.get("vars", {})
    prompt_type = vars_dict.get("prompt_type", "corpo")

    try:
        real_prompt = _build_prompt(prompt_type, vars_dict)
    except Exception as e:
        return {"error": f"Errore costruzione prompt: {e}"}

    # ── Chiama Gemini ───────────────────────────────────────────────────────
    try:
        response = model.generate_content(real_prompt)
        output_text = response.text or ""

        token_usage = {}
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            um = response.usage_metadata
            token_usage = {
                "prompt": getattr(um, "prompt_token_count", 0),
                "completion": getattr(um, "candidates_token_count", 0),
                "total": getattr(um, "total_token_count", 0),
            }

        return {
            "output": output_text,
            "tokenUsage": token_usage,
        }
    except Exception as e:
        return {"error": f"Errore API Gemini: {e}"}
