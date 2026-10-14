"""
ui_legale.py — pagine pubbliche «Termini di servizio» e «Rimborsi e recesso» (si aprono con ?pagina=termini
e ?pagina=rimborsi, senza accedere). Solo testo statico; i dati del fornitore stanno in config.LEGALE.

BOZZE: vanno riviste (commercialista / consulente) prima di linkarle dall'app e dal checkout.
"""
import streamlit as st

from config import LEGALE, PREZZO_PRO_ANNUALE, LIMITE_MENSILE


def _titolo(T: dict, titolo: str) -> None:
    st.markdown(
        f'<div style="max-width:760px;margin:0 auto;font-family:DM Sans,sans-serif;'
        f'color:{T["text"]};line-height:1.6;">'
        f'<h1 style="font-size:1.9rem;font-weight:800;margin:1rem 0 .2rem;">{titolo}</h1>'
        f'<div style="color:{T["muted"]};font-size:.9rem;margin-bottom:1.5rem;">'
        f'VerificAI · ultimo aggiornamento: {LEGALE["aggiornamento"]}</div></div>',
        unsafe_allow_html=True,
    )


def _fornitore() -> str:
    """Riga con i dati del fornitore: indirizzo e partita IVA compaiono solo se compilati."""
    righe = [f"**Fornitore del servizio:** {LEGALE['nome']}"]
    if LEGALE.get("indirizzo"):
        righe.append(f"**Sede:** {LEGALE['indirizzo']}")
    if LEGALE.get("partita_iva"):
        righe.append(f"**Partita IVA:** {LEGALE['partita_iva']}")
    righe.append(f"**Contatto e assistenza:** {LEGALE['email']}")
    return "  \n".join(righe)


def render_termini(T: dict) -> None:
    _titolo(T, "Termini di servizio")
    _c1, _c2, _c3 = st.columns([1, 6, 1])
    with _c2:
        st.markdown(f"""
{_fornitore()}

### 1. Il servizio
VerificAI è un servizio web per docenti che genera verifiche scolastiche con l'aiuto dell'intelligenza
artificiale e le rende disponibili in PDF e in altri formati. Usando il servizio accetti questi termini.

### 2. Account
Per usare VerificAI serve un account personale (email o accesso con Google). Sei responsabile della
riservatezza delle tue credenziali. L'account è per un solo docente e non va condiviso.

### 3. Piani
- **Free:** gratuito, fino a {LIMITE_MENSILE} verifiche al mese, con il modello AI base. La **prima verifica** di ogni account
  include, una sola volta, tutte le funzioni del piano Pro.
- **Pro:** {PREZZO_PRO_ANNUALE} € per un anno scolastico (pagamento unico, senza rinnovo automatico), con il modello AI
  più accurato e le funzioni extra (Fila B, versione BES/DSA, soluzioni, file Word, griglia di valutazione,
  scheda di allenamento, logo della scuola, creazione da un file caricato). Il piano dura 365 giorni dall'attivazione.

Funzioni, limiti e prezzi possono cambiare: le modifiche non riguardano il periodo già pagato.

### 4. Acquisto e codice di licenza
L'acquisto del piano Pro avviene tramite **Lemon Squeezy**, che agisce come venditore e gestisce pagamento, imposte e
fatture. Dopo il pagamento ricevi un **codice di licenza**: va incollato nella pagina «Passa a Pro» e vale per un solo
account. Non vediamo né conserviamo i dati della tua carta. Se il pagamento viene rimborsato o contestato,
il codice può essere disattivato e l'account torna al piano Free.

### 5. Contenuti generati dall'intelligenza artificiale
Le verifiche sono prodotte da un modello di intelligenza artificiale e **possono contenere errori**
(di calcolo, di contenuto o di impaginazione). Prima di usarle con gli studenti **devi controllarle**: la
responsabilità didattica e della correzione resta tua. Non garantiamo che i contenuti siano privi di errori
né adatti a ogni scopo.

### 6. Uso consentito
Usa il servizio per la tua attività didattica. Non inserire dati personali degli studenti (nomi, voti,
valutazioni individuali) e non usare il servizio per attività illecite, per aggirare i limiti del piano o per
rivendere l'accesso. Possiamo sospendere gli account che violano questi termini.

### 7. Contenuti e diritti
Le verifiche che crei sono tue e puoi usarle per la tua didattica. Resta nostro il software e il marchio VerificAI.
Dichiari di avere il diritto di usare i file che carichi.

### 8. Responsabilità
Il servizio è fornito «così com'è». Nei limiti consentiti dalla legge non rispondiamo di danni indiretti
o di interruzioni del servizio. Restano ferme le tutele che la legge riconosce ai consumatori.

### 9. Recesso e rimborsi
Si applica la pagina [Rimborsi e recesso](?pagina=rimborsi).

### 10. Dati personali
Si applica l'[Informativa sulla privacy](?pagina=privacy).

### 11. Legge applicabile e contatti
Questi termini sono regolati dalla legge italiana. Per qualsiasi domanda scrivi a **{LEGALE['email']}**.
""")


def render_rimborsi(T: dict) -> None:
    _titolo(T, "Rimborsi e recesso")
    _c1, _c2, _c3 = st.columns([1, 6, 1])
    with _c2:
        st.markdown(f"""
{_fornitore()}

### Rimborso entro 14 giorni
Se acquisti il piano Pro e non sei soddisfatto, puoi chiedere il **rimborso integrale entro 14 giorni
dall'acquisto**, scrivendo a **{LEGALE['email']}** dall'indirizzo email dell'acquisto, oppure dalla ricevuta di
Lemon Squeezy. Non serve spiegare il motivo.

### Come funziona
- Il pagamento e il rimborso sono gestiti da **Lemon Squeezy**: il rimborso torna sullo stesso metodo di pagamento
  e può richiedere alcuni giorni per comparire sull'estratto conto.
- Quando il rimborso è effettuato, il codice di licenza viene disattivato e l'account torna al piano Free
  (entro 24 ore).
- Le verifiche già create restano tue.

### Diritto di recesso dei consumatori
Se acquisti come consumatore, hai il diritto di recedere entro 14 giorni dall'acquisto senza indicare il motivo.
Il rimborso previsto sopra coincide con questo diritto.

### Contatti
Per qualsiasi problema con un acquisto scrivi a **{LEGALE['email']}**.
""")
