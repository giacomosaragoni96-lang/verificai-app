"""
prova_generazione.py — prova da riga di comando della generazione con l'AI vera.

Serve per vedere, senza passare dall'interfaccia, come se la cava un modello su richieste diverse:
costo, token, punteggi, PDF compilato. Usa la chiave GOOGLE_API_KEY del file .env (non la stampa).

    python prova_generazione.py                       # tutti gli scenari con il modello del piano free
    python prova_generazione.py --modello gemini-2.5-flash
    python prova_generazione.py --scenario fisica     # un solo scenario

I PDF finiscono nella cartella prove_output/ (ignorata da git). Ogni scenario costa pochi centesimi.
"""
import argparse
import os
import re
import sys
import time

from dotenv import load_dotenv

load_dotenv()

for _flusso in (sys.stdout, sys.stderr):      # la console di Windows non stampa le frecce
    try:
        _flusso.reconfigure(encoding="utf-8")
    except Exception:
        pass

import ai_client                                    # noqa: E402
from config import MODEL_FAST_ID                     # noqa: E402
from generation import genera_verifica               # noqa: E402
from latex_utils import conta_punti_latex            # noqa: E402

SCENARI = {
    "parabola": dict(
        materia="Matematica", scuola="Liceo Scientifico",
        argomento="Equazioni di secondo grado e parabola\n- 4 esercizi, difficoltà crescente\n"
                  "- includi un grafico da leggere (senza scrivere l'equazione sul grafico)\n- usa numeri interi",
        esercizi=4, grafico=True),
    "funzioni": dict(
        materia="Matematica", scuola="Liceo Scientifico",
        argomento="Studio di funzione: dominio, limiti, derivata prima, massimi e minimi\n"
                  "- 3 esercizi di cui uno con grafico probabile della funzione da disegnare a partire dai dati",
        esercizi=3, grafico=True),
    "fratte": dict(
        materia="Matematica", scuola="Liceo Scientifico",
        argomento="Equazioni e disequazioni fratte",
        esercizi=4, grafico=False),
    "fisica": dict(
        materia="Fisica", scuola="Liceo Scientifico",
        argomento="Cinematica: moto rettilineo uniformemente accelerato\n- un problema con grafico velocità-tempo da leggere\n"
                  "- un vero/falso e un problema di sorpasso tra due auto",
        esercizi=4, grafico=True),
    "chimica": dict(
        materia="Chimica", scuola="Istituto Tecnico",
        argomento="Stechiometria e bilanciamento delle reazioni\n- niente tabelle periodiche da consultare\n- una scelta multipla",
        esercizi=4, grafico=False),
    "italiano": dict(
        materia="Italiano", scuola="Scuola Secondaria di Primo Grado",
        argomento="Analisi del testo narrativo: narratore, personaggi, tempo e luogo\n- un breve brano inventato incluso nella verifica",
        esercizi=3, grafico=False),
}


def esegui(nome: str, sc: dict, model_id: str, cartella: str):
    ai_client.azzera_uso()
    modello = ai_client.crea_modello(model_id)
    t0 = time.time()
    try:
        r = genera_verifica(
            model=modello, materia=sc["materia"], argomento=sc["argomento"], difficolta=sc["scuola"],
            calibrazione="", durata="1 ora", num_esercizi=sc["esercizi"], punti_totali=100,
            mostra_punteggi=True, con_griglia=True, doppia_fila=False, bes_dsa=False, perc_ridotta=None,
            bes_dsa_b=False, genera_soluzioni=False, note_generali="", istruzioni_esercizi="",
            immagini_esercizi=[],
        )
    except Exception as e:                           # noqa: BLE001
        print(f"[{nome}] ERRORE: {str(e)[:300]}")
        return
    secondi = time.time() - t0
    latex = r["A"]["latex"] or ""
    pdf = r["A"]["pdf"]
    uso = ai_client.riepilogo_uso()
    costo = sum(u["costo_usd"] for u in uso)
    tok_in = sum(u["input"] for u in uso)
    tok_out = sum(u["output"] + u["pensiero"] for u in uso)
    n_es = len(re.findall(r"\\subsection\*", latex))
    ha_grafico = bool(re.search(r"\\begin\{(?:tikzpicture|axis)\}", latex))
    nomi = ", ".join(sorted({u["modello"].replace("gemini-", "") for u in uso}))
    print(f"[{nome}] {secondi:4.0f}s | modelli: {nomi} | chiamate: {sum(u['chiamate'] for u in uso)} | "
          f"token in/out: {tok_in}/{tok_out} | ~${costo:.4f}")
    print(f"        esercizi: {n_es}/{sc['esercizi']} | punti: {conta_punti_latex(latex)}/100 | "
          f"PDF: {'sì' if pdf else 'NO'} | grafico: {'sì' if ha_grafico else 'no'}"
          f"{' (richiesto!)' if sc['grafico'] and not ha_grafico else ''}")
    if pdf:
        percorso = os.path.join(cartella, f"{nome}.pdf")
        with open(percorso, "wb") as f:
            f.write(pdf)
        print(f"        → {percorso}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modello", default=MODEL_FAST_ID, help="modello del piano (default: Flash-Lite, piano free)")
    ap.add_argument("--scenario", choices=sorted(SCENARI), help="un solo scenario")
    a = ap.parse_args()
    if not os.getenv("GOOGLE_API_KEY"):
        sys.exit("Manca GOOGLE_API_KEY: mettila nel file .env (vedi le istruzioni) e riprova.")
    ai_client.configura()
    cartella = "prove_output"
    os.makedirs(cartella, exist_ok=True)
    print(f"Modello del piano: {a.modello}\n")
    for nome, sc in SCENARI.items():
        if a.scenario and nome != a.scenario:
            continue
        esegui(nome, sc, a.modello, cartella)
    sost = ai_client.modelli_sostituiti()
    if sost:
        print("\nModelli sostituiti perché ritirati:", sost)


if __name__ == "__main__":
    main()
