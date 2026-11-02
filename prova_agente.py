"""
prova_agente.py — prova da riga di comando dell'agente (agente.py) con l'AI vera: diciassette richieste di esempio, dalla più chiara alla più strana.
Serve a vedere se capisce, se chiede solo ciò che manca e se compila i campi giusti. Usa GOOGLE_API_KEY del file .env (non la stampa).

    python prova_agente.py

Costa circa un centesimo in tutto. Non fa parte dell'app.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv

load_dotenv()
for f in (sys.stdout, sys.stderr):
    f.reconfigure(encoding="utf-8")

import agente
import ai_client
from config import MODEL_FLASH_ID

if not os.getenv("GOOGLE_API_KEY"):
    sys.exit("manca GOOGLE_API_KEY nel .env")
ai_client.configura()
modello = ai_client.crea_modello(MODEL_FLASH_ID).per("agente")

CLASSI = [{"nome": "3ªB", "scuola": "Liceo Scientifico", "note": "classe vivace, livello medio-alto"},
          {"nome": "1ªA", "scuola": "Scuola Secondaria I grado (Medie)", "note": ""}]
ULTIME = [{"argomento": "Le equazioni di primo grado", "materia": "Matematica", "scuola": "Liceo Scientifico", "classe": "3ªB"}]
BASE = {"classi": CLASSI, "ultime": ULTIME, "predefiniti": {"materia": "Matematica", "scuola": "Liceo Scientifico"},
        "preferenze": ["Consegne brevi e con linguaggio semplice."], "bloccate": []}

CASI = [
    ("home", "disequazioni di secondo grado per la 3b con fila B e soluzioni, 5 esercizi, un problema sul traffico", {}),
    ("home", "verifica", {}),
    ("home", "una cosa sulla seconda guerra mondiale", {}),
    ("home", "come l'ultima ma più difficile", {}),
    ("home", "ho una verifica già scritta in word da sistemare", {}),
    ("home", "voglio mettere un esercizio del mio libro, ho la foto", {}),
    ("home", "verifica di inglese sul present perfect, facile, senza punteggi, no eccellenza, per la 1a", {}),
    ("home", "mi fai i compiti per casa di mio figlio?", {}),
    ("final", "togli l'ultimo esercizio e rendi più facile il secondo", {"verifica": {"argomento": "Le equazioni di primo grado", "materia": "Matematica", "scuola": "Liceo Scientifico", "classe": "3ªB",
                                                                                    "esercizi": ["Equazioni intere", "Equazioni fratte", "Problema", "Per l'eccellenza"], "pronte": []}}),
    ("final", "preparami la B, le soluzioni e una versione per un'alunna con DSA", {"verifica": {"argomento": "Le equazioni", "materia": "Matematica", "scuola": "Liceo Scientifico",
                                                                                                "esercizi": ["Equazioni intere", "Problema"], "pronte": ["B"]}}),
    ("final", "cambia il titolo in Verifica di recupero", {"verifica": {"argomento": "Le equazioni", "materia": "Matematica", "esercizi": ["Equazioni"], "pronte": []}}),
    ("final", "rifai il terzo più difficile, togli l'ultimo e metti 30 punti al primo", {"verifica": {"argomento": "Le equazioni", "materia": "Matematica", "scuola": "Liceo Scientifico", "classe": "3ªB",
                                                                                                       "esercizi": ["Equazioni intere", "Equazioni fratte", "Problema", "Per l'eccellenza"], "pronte": [], "punti_totali": 100}}),
    ("final", "aggiungi un problema sul traffico e scrivi la classe 3B con la data 15 novembre", {"verifica": {"argomento": "Le equazioni", "materia": "Matematica", "esercizi": ["Equazioni", "Problema"], "pronte": [], "punti_totali": 100}}),
    ("home", "ti allego la mia verifica in pdf, togli l'esercizio 4 e impaginala", {"allegato": {"nome": "verifica_3B.pdf", "tipo": "application/pdf", "n": 1}}),
    ("final", "lascia solo le equazioni lineari", {"verifica": {"argomento": "Equazioni (recupero)", "materia": "Matematica", "scuola": "Liceo Scientifico",
                                                              "esercizi": ["Equazioni lineari", "Equazioni lineari fratte", "Equazioni con valore assoluto", "Equazioni razionali", "Problema"], "pronte": [], "punti_totali": 100}}),
    ("final", "no, fai 5 esercizi", {"verifica": {"argomento": "Equazioni (recupero)", "materia": "Matematica", "scuola": "Liceo Scientifico",
                                                  "esercizi": ["Equazioni lineari"], "pronte": [], "punti_totali": 100}}),
    ("final", "fammi una verifica nuova sui polinomi per la 2a", {"verifica": {"argomento": "Le equazioni", "materia": "Matematica", "esercizi": ["Equazioni"], "pronte": []}}),
]

for stage, testo, extra in CASI:
    ctx = {**BASE, **extra}
    chat = [{"ruolo": "utente", "testo": testo, "stage": stage}]
    d = agente.interpreta(modello, chat, ctx, stage, 0)
    c = {k: v for k, v in d["crea"].items() if v not in (None, "")}
    print(f"\n[{stage}] «{testo}»\n  → {d['azione']}" + (" (RIPIEGO)" if d.get("ripiego") else ""))
    if d["messaggio"]:
        print("  msg:", d["messaggio"])
    if d["domanda"]:
        print("  domanda:", d["domanda"], d["opzioni"])
    if d["azione"] == "crea":
        print("  crea:", json.dumps(c, ensure_ascii=False), "| versioni:", d["versioni"])
    if d["azione"] == "versioni":
        print("  versioni:", d["versioni"], d["per_chi"])
    if d["azione"] == "modifica" or (d["azione"] == "impagina" and d["modifica"]):
        print("  modifica:", d["modifica"])
    if d["azione"] == "operazioni":
        print("  operazioni:", [(o["tipo"], (o["indice"] + 1) if o["indice"] is not None else None, o["punti"] or o["istruzione"] or o["classe"] or o["data"]) for o in d["operazioni"]])
    if d["assunzioni"]:
        print("  assunzioni:", d["assunzioni"])

print("\nchiamate:", len(ai_client.riepilogo_uso()))
for r in ai_client.riepilogo_uso()[-1:]:
    print({k: r[k] for k in r if k in ("modello", "compito", "costo_usd", "secondi")})
