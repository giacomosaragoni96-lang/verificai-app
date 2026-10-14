# ── config.py ──────────────────────────────────────────────────────────────────
# Tutte le costanti dell'app. Nessuna logica, nessun import di streamlit.
# ───────────────────────────────────────────────────────────────────────────────

# ── APP ────────────────────────────────────────────────────────────────────────
APP_NAME          = "VerificAI"
APP_ICON          = "📝"
APP_TAGLINE       = "Crea verifiche su misura in pochi secondi"
SHARE_URL         = "https://verificai.streamlit.app"
FEEDBACK_FORM_URL = "https://forms.gle/KNu8v8iDVUiGkQUL8"

# ── LIMITI E RUOLI ─────────────────────────────────────────────────────────────
LIMITE_MENSILE = 5
ADMIN_EMAILS   = {"giacomosaragoni96@gmail.com"}

# Limiti per piano free
FREE_PLAN_LIMITS = {
    "verifiche_mensili": 5,
    "modello_ai": "gemini-2.5-flash-lite"
}

# ── PIANI E FUNZIONI ───────────────────────────────────────────────────────────
# Interruttore della monetizzazione: SPENTO = ogni funzione è aperta a tutti (comportamento di oggi).
# Con l'interruttore acceso le funzioni elencate in FUNZIONI_PRO richiedono il piano Pro.
MONETIZZAZIONE_ATTIVA = True
# Inviti tra colleghi: per ogni amico che si iscrive e completa la prima verifica, chi invita guadagna verifiche con tutto il Pro
BONUS_PER_INVITO = 2
MAX_INVITI_CON_BONUS = 5
FUNZIONI_PRO = ("fila_b", "bes", "soluzioni", "word", "griglia", "logo", "scheda", "zip", "materiale")

# Come si chiamano le funzioni nei messaggi «con Pro puoi…»
ETICHETTE_FUNZIONI = {
    "fila_b": "la Fila B", "bes": "la versione BES/DSA", "soluzioni": "le soluzioni", "word": "il file Word",
    "griglia": "la griglia di valutazione", "logo": "il logo della scuola",
    "scheda": "la scheda di allenamento", "zip": "il kit completo in un solo file",
    "materiale": "la verifica a partire dai tuoi appunti o da una verifica già fatta",
}
# Dati del fornitore per le pagine legali (Termini, Rimborsi, Privacy). Indirizzo e partita IVA: compaiono solo se compilati.
# LEGALE_PRONTO = True fa comparire i link a Termini e Rimborsi nell'app: da accendere solo dopo la revisione delle bozze.
LEGALE = {
    "nome": "Giacomo Saragoni",
    "email": "verificai.support@gmail.com",
    "indirizzo": "",
    "partita_iva": "",
    "aggiornamento": "14 ottobre 2026",
}
LEGALE_PRONTO = True
# Tetto di sicurezza contro abusi e costi anomali: al massimo tante verifiche in quanti minuti (per utente, admin escluso)
TETTO_BREVE = {"verifiche": 6, "minuti": 10}
# Facciate massime consigliate per una verifica (si stampa su 2 fogli fronte-retro); oltre: avviso e riduzione
MAX_FACCIATE = 2
# Esportazione Word: spenta finche' la conversione non e' affidabile (testo, scelte multiple, grafici e tabella si perdevano)
WORD_ATTIVO = False
PREZZO_PRO_ANNUALE = 39                 # euro, 12 mesi dall'attivazione (pagamento unico)
CHECKOUT_URL_PRO = "https://verificai.lemonsqueezy.com/checkout/buy/cd7d56f4-10c1-4807-bc2f-90dffa200268"   # prodotto di PROVA (test mode)
# ID del negozio e del prodotto Lemon Squeezy: una licenza vale solo se sono questi (None = nessun codice accettato).
# Compaiono nel dettaglio tecnico (solo admin) al primo tentativo di attivazione.
LEMON_STORE_ID = 497699
LEMON_PRODUCT_ID = 1439308   # prodotto di PROVA: al passaggio in live va sostituito

# famiglia_modello: «lite» o «flash» (NON un ID): il modello vero lo sceglie get_model_id_per_piano
# e lo risolve ai_client nel più recente della famiglia.
# Il tetto del Pro oggi è illimitato (piano assegnato a mano); al lancio diventerà 100 al mese.
PIANI = {
    "free": {"tetto_mensile": LIMITE_MENSILE, "famiglia_modello": "lite",  "funzioni": ()},
    "pro":  {"tetto_mensile": float("inf"),   "famiglia_modello": "flash", "funzioni": FUNZIONI_PRO},
}

# ── MODELLI AI ─────────────────────────────────────────────────────────────────
MODELLI_DISPONIBILI = {
    "⚡ Flash 2.5 Lite (veloce · Free)": {
        "id":    "gemini-2.5-flash-lite",
        "piano": "free",
    },
    "⚡ Flash 2.5 (bilanciato · Pro)": {
        "id":    "gemini-2.5-flash",
        "piano": "pro",
    },
    "🧠 Pro 2.5 (STEM/Gold)": {
        "id":    "gemini-2.5-pro",
        "piano": "gold",
    },
}

MODEL_FAST_ID = "gemini-2.5-flash-lite"
MODEL_FLASH_ID = "gemini-2.5-flash"

# ── COSTI E ROUTING DEI MODELLI ───────────────────────────────────────────────
# Prezzi in USD per milione di token (input, output). L'output include i token di
# "ragionamento" dei modelli 2.5: sono quelli che pesano di più sul costo.
PREZZI_USD_PER_MILIONE = {
    "gemini-2.5-flash-lite": (0.10, 0.40),
    "gemini-2.5-flash":      (0.30, 2.50),
    "gemini-2.5-pro":        (1.25, 10.00),
    "gemini-3.5-flash-lite": (0.30, 2.50),
}
# Stima per i modelli della serie 3.x non elencati sopra (famiglia → input, output).
PREZZI_STIMATI_GEN3 = {"lite": (0.30, 2.50), "flash": (0.50, 3.00), "pro": (2.00, 12.00)}

# Tetto ai token di ragionamento per i compiti che servono davvero: ragionare senza limite
# su Flash e Pro costa ~25.000 token a verifica (misurato dal report di fatturazione).
# Per Flash-Lite il ragionamento resta spento (comportamento predefinito).
RAGIONAMENTO_ALTO = {"gemini-2.5-flash": 2048, "gemini-2.5-pro": 4096}

# Controllo qualità: se il punteggio strutturale della bozza è almeno questo (0-1), la seconda
# chiamata all'AI (che riscrive tutto il testo e costa quasi quanto la generazione) viene saltata.
# None = esegui sempre il controllo. Il punteggio misura struttura, numero di esercizi e somma dei
# punti: NON la correttezza matematica.
QA_SALTA_SE_PUNTEGGIO_ALMENO = 1.0

# compito → (quale modello, ragionamento)
#   modello: "piano" = quello del piano dell'utente · "medio" = Flash (Lite se il piano è Free,
#            mai Pro) · "veloce" = sempre Flash-Lite
#   ragionamento: "alto" = RAGIONAMENTO_ALTO · numero = tetto in token · 0 = spento · None = predefinito
COMPITI_AI = {
    "titolo":            ("veloce", 0),
    "corpo":             ("piano",  "alto"),
    "soluzioni":         ("piano",  "alto"),
    "controllo_qualita": ("medio",  0),
    "variante":          ("medio",  1024),   # Fila B, BES/DSA, versione ridotta
    "modifica":          ("medio",  1024),   # più facile/difficile, cambia i numeri, modifica libera
    "griglia":           ("medio",  0),
    "cambio_esercizio":  ("veloce", None),
    "analisi_file":      ("veloce", None),
    "scheda":            ("medio",  1024),   # scheda di allenamento: una chiamata per sezione
    "autoverifica":      ("flash",  3072),   # risolve gli esercizi e corregge gli errori: SEMPRE Flash, anche col piano Free
}

# Autoverifica degli esercizi nelle materie scientifiche (autoverifica.py). Costo: circa 1-2 centesimi a verifica.
AUTOVERIFICA_ATTIVA = True

# ── SCHEDA DI ALLENAMENTO ─────────────────────────────────────────────────────
# ~40 esercizi graduati, una sezione per ogni esercizio della verifica (scheda.py).
SCHEDA = {
    "esercizi_totali": 40,
    "min_per_sezione": 4,
    "max_per_sezione": 12,
    "max_sezioni": 8,        # con più esercizi nella verifica si raggruppano a coppie
    "parallelo": 4,          # chiamate all'AI in contemporanea
}

# Etichetta «Pro» sulle funzioni del kit: spenta finché non parte la monetizzazione.
MOSTRA_BADGE_PRO = False


def scegli_modello_per_compito(compito: str, model_id_piano: str):
    """Restituisce (model_id, tetto_ragionamento) per un compito, dato il modello del piano."""
    tipo, ragionamento = COMPITI_AI.get(compito, ("piano", None))
    if tipo == "veloce":
        model_id = MODEL_FAST_ID
    elif tipo == "flash":
        model_id = MODEL_FLASH_ID
    elif tipo == "medio":
        model_id = MODEL_FAST_ID if model_id_piano == MODEL_FAST_ID else MODEL_FLASH_ID
    else:
        model_id = model_id_piano
    if model_id == MODEL_FAST_ID:
        return model_id, (0 if ragionamento == 0 else None)   # Lite: spento solo dove richiesto
    if ragionamento == "alto":
        ragionamento = RAGIONAMENTO_ALTO.get(model_id)
    return model_id, ragionamento

NOTA_ISTRUZIONI_STEM = "Svolgere tutti gli esercizi mostrando i passaggi."
NOTA_ISTRUZIONI_UMANISTICA = "Rispondere a tutte le richieste in modo chiaro e completo."


def nota_istruzioni_verifica(materia: str) -> str:
    """Frase sotto l'intestazione della verifica: «mostrando i passaggi» vale per le materie scientifiche, non per Storia o Italiano."""
    return NOTA_ISTRUZIONI_STEM if (materia or "") in MATERIE_STEM else NOTA_ISTRUZIONI_UMANISTICA


MATERIE_STEM = {
    "Matematica", "Fisica", "Chimica", "Informatica",
    "Scienze della Terra", "Biologia",
}

def get_model_id_per_piano(piano: str, materia: str = "") -> str:
    is_stem = materia in MATERIE_STEM
    if piano == "gold" or (piano == "admin" and is_stem):
        return MODELLI_DISPONIBILI["🧠 Pro 2.5 (STEM/Gold)"]["id"]
    if piano in ("pro", "admin"):
        return MODELLI_DISPONIBILI["⚡ Flash 2.5 (bilanciato · Pro)"]["id"]
    return MODEL_FAST_ID

# ── DIFFICOLTÀ DEGLI ESERCIZI PER TIPO DI SCUOLA ──────────────────────────────
# Livelli normalizzati: 1 = base, 2 = medio, 3 = sfida (le "stelle" dei libri; le fonti con altre
# scale, per esempio 5 livelli, vengono ricondotte a questi tre).
# Per ogni scuola: (quota ★1, quota ★2, quota ★3) di una verifica, e il tetto di esercizi da ★3
# (None = nessun tetto). Le quote si applicano al numero di esercizi con arrotondamento ai resti
# maggiori. Dove il tetto esiste, un ★3 compare solo se la verifica ha almeno
# MIN_ESERCIZI_PER_3_STELLE esercizi; va sempre in fondo (ordine crescente).
DISTRIBUZIONE_DIFFICOLTA = {
    "Scuola Primaria (Elementari)":             ((1.0, 0.0, 0.0), 0),
    "Scuola Secondaria I grado (Medie)":        ((0.6, 0.4, 0.0), 0),
    "Liceo Scientifico":                        ((0.0, 0.6, 0.4), None),
    "Liceo Classico":                           ((0.0, 0.7, 0.3), None),
    "Liceo Linguistico":                        ((0.0, 0.8, 0.2), 1),
    "Liceo delle Scienze Umane":                ((0.0, 0.8, 0.2), 1),
    "Liceo Artistico":                          ((0.2, 0.7, 0.1), 1),
    "Istituto Tecnico Tecnologico/Industriale": ((0.2, 0.6, 0.2), 2),
    "Istituto Tecnico Economico":               ((0.3, 0.6, 0.1), 1),
    "Istituto Tecnico Agrario/Ambientale":      ((0.3, 0.6, 0.1), 1),
    "Istituto Professionale":                   ((0.4, 0.4, 0.2), 1),
    "Generico":                                 ((0.3, 0.5, 0.2), 1),
}
MIN_ESERCIZI_PER_3_STELLE = 4

# Categorie di scuola della banca esercizi (poche, per non complicare il caricamento).
CATEGORIE_SCUOLA = ["Elementari", "Medie", "Professionale", "Tecnico", "Liceo"]


def categoria_scuola(scuola: str):
    """Dal tipo di scuola scelto nell'app alla categoria della banca (None se «Generico»)."""
    s = (scuola or "").lower()
    if "primaria" in s or "elementari" in s:
        return "Elementari"
    if "i grado" in s or "medie" in s:
        return "Medie"
    if "professionale" in s:
        return "Professionale"
    if "tecnico" in s:
        return "Tecnico"
    if "liceo" in s:
        return "Liceo"
    return None


def distribuzione_difficolta(scuola: str, n: int) -> dict:
    """Quanti esercizi per livello in una verifica di n esercizi: {1: x, 2: y, 3: z}."""
    perc, tetto3 = DISTRIBUZIONE_DIFFICOLTA.get(scuola, DISTRIBUZIONE_DIFFICOLTA["Generico"])
    perc = list(perc)
    if tetto3 is not None and n < MIN_ESERCIZI_PER_3_STELLE and perc[2] > 0:
        # verifica troppo corta per una sfida: la quota va al livello medio (o base)
        perc[1 if perc[1] > 0 else 0] += perc[2]
        perc[2] = 0.0
    quote = [n * p for p in perc]
    base = [int(q) for q in quote]
    resto = n - sum(base)
    candidati = sorted((i for i in range(3) if perc[i] > 0), key=lambda i: (-(quote[i] - base[i]), i))
    for i in candidati[:resto]:
        base[i] += 1
    if tetto3 is not None and base[2] > tetto3:
        eccesso = base[2] - tetto3
        base[2] = tetto3
        base[1 if perc[1] > 0 else 0] += eccesso
    if (tetto3 is not None and tetto3 >= 1 and perc[2] > 0 and n >= MIN_ESERCIZI_PER_3_STELLE
            and base[2] == 0):
        da = 0 if base[0] > 0 else 1
        base[da] -= 1
        base[2] = 1
    return {1: base[0], 2: base[1], 3: base[2]}


def sequenza_difficolta(scuola: str, n: int) -> list:
    """I livelli della verifica in ordine di svolgimento (dal più facile al più difficile)."""
    d = distribuzione_difficolta(scuola, n)
    return [1] * d[1] + [2] * d[2] + [3] * d[3]


def livello_normalizzato(livello: int, livelli_della_fonte: int) -> int:
    """Riconduce un livello (1..L) della fonte a 1-3. Con 3 livelli o meno è l'identità."""
    if livelli_della_fonte <= 3:
        return max(1, min(3, int(livello)))
    import math
    return max(1, min(3, math.ceil(int(livello) * 3 / livelli_della_fonte)))


# ── TEMA UI ─────────────────────────────────────────────────────────────────────
# Tema default: Carta (light) + opzione Notte (dark)
# ───────────────────────────────────────────────────────────────────────────────

THEMES = {
    # ═══════════════════════════════════════════════════════════════════════
    #  CARTA — Ultra-clean Paper White  (Linear light · Stripe · GitHub light) - DEFAULT
    #  Massima leggibilità · blue accent autorevole · tipografia precisa
    # ═══════════════════════════════════════════════════════════════════════
    "carta": {
        # Superfici — bianco-carta con micro-warmth, non freddo
        "bg":         "#FAFAFA",
        "bg2":        "#F2F3F5",
        "card":       "#FFFFFF",
        "card2":      "#F8F9FA",

        # Testo — near-black quasi neutro, massimo contrasto
        "text":       "#0F1117",
        "text2":      "#4A5166",
        "muted":      "#7A8299",

        # Bordi — minimal, ultra-sottili
        "border":     "#E2E5EB",
        "border2":    "#CDD1D9",

        # Accent — Blue autorevole (sistema, fiducia, azione)
        "accent":       "#2563EB",
        "accent2":      "#1D4ED8",
        "accent_light": "#EFF6FF",

        # Interazione
        "hover":      "#F8FAFC",

        # Semantici — calibrati per light theme
        "success":    "#059669",
        "warn":       "#D97706",
        "error":      "#DC2626",

        # Ombre — ultra-morbide, professionali
        "shadow":     "0 1px 2px rgba(15,17,23,.04)",
        "shadow_md":  "0 4px 20px rgba(15,17,23,.08), 0 1px 3px rgba(15,17,23,.04)",
        "shadow_soft": "0 12px 40px rgba(15,17,23,.06), 0 2px 8px rgba(15,17,23,.03)",

        # Design system
        "radius_sm":  "8px",
        "radius_md":  "12px",
        "radius_lg":  "16px",

        # Sidebar — chiara, in tono con la pagina
        "sidebar_bg":      "#F3F4F6",
        "sidebar_border":  "#E2E5EA",
        "sidebar_accent":  "#2563EB",
        "sidebar_input_bg":  "#FFFFFF",
        "sidebar_input_text": "#0F1117",
        "sidebar_muted":   "#6B7280",

        # Hint boxes
        "hint_bg":      "#EFF6FF",
        "hint_border":  "#BFDBFE",
        "hint_text":    "#1D4ED8",
    },

    # ═══════════════════════════════════════════════════════════════════════
    #  NOTTE — Dark Midnight Blue  (opzione dark)
    # ═══════════════════════════════════════════════════════════════════════
    "notte": {
        # Superfici
        "bg":         "#0D1117",
        "bg2":        "#161B22",
        "card":       "#1C2128",
        "card2":      "#21262D",

        # Testo
        "text":       "#E6EDF3",
        "text2":      "#8B949E",
        "muted":      "#6E7681",

        # Bordi
        "border":     "#30363D",
        "border2":    "#3D444D",

        # Accent — Blu elettrico
        "accent":       "#58A6FF",
        "accent2":      "#79C0FF",
        "accent_light": "#0D2340",

        # Interazione
        "hover":      "#1F2937",

        # Semantici
        "success":    "#3FB950",
        "warn":       "#D29922",
        "error":      "#F85149",

        # Ombre
        "shadow":     "0 1px 3px rgba(0,0,0,.35)",
        "shadow_md":  "0 4px 24px rgba(0,0,0,.50)",
        "shadow_soft": "0 8px 32px rgba(0,0,0,.25), 0 2px 8px rgba(0,0,0,.15)",

        # Design system (Minimal SaaS)
        "radius_sm":  "8px",
        "radius_md":  "12px",
        "radius_lg":  "16px",

        # Sidebar
        "sidebar_bg":      "linear-gradient(180deg, #010409 0%, #0D1117 100%)",
        "sidebar_border":  "#21262D",
        "sidebar_accent":  "#79C0FF",
        "sidebar_input_bg":  "#0D1117",
        "sidebar_input_text": "#E6EDF3",
        "sidebar_muted":   "#8B949E",

        # Hint boxes
        "hint_bg":      "#0D2340",
        "hint_border":  "#1F4070",
        "hint_text":    "#79C0FF",
    },
}

THEME_LABELS = {
    "carta": "📄 Carta",
    "notte": "🌙 Notte",
}

DEFAULT_THEME = "carta"

# ── SCUOLE E CALIBRAZIONE ──────────────────────────────────────────────────────
SCUOLE = [
    "Generico",
    "Scuola Primaria (Elementari)",
    "Scuola Secondaria I grado (Medie)",
    "Liceo Scientifico",
    "Liceo Classico",
    "Liceo Linguistico",
    "Liceo delle Scienze Umane",
    "Liceo Artistico",
    "Istituto Tecnico Tecnologico/Industriale",
    "Istituto Tecnico Economico",
    "Istituto Tecnico Agrario/Ambientale",
    "Istituto Professionale",
]

CALIBRAZIONE_SCUOLA = {
    "Generico": (
        "Livello NON specificato: adatta autonomamente difficoltà, registro linguistico e complessità, "
        "se non specificato consulta indicazioni nazionali e cerca di capire l'argomento indicato quando "
        "viene trattato nella scuola italiana per capire il contesto. "
        "in base all'argomento e alle istruzioni del docente. "
        "Se l'argomento suggerisce un livello (es. 'derivate' → superiori, 'addizioni' → primaria), "
        "calibra di conseguenza. "
        "Usa un linguaggio chiaro, diretto e professionale. Nessun vincolo di scuola."
    ),
    "Scuola Primaria (Elementari)": (
        "Scuola primaria (6–11 anni): linguaggio semplice e diretto, frasi brevi, "
        "esercizi concreti e vicini alla realtà quotidiana. "
        "Niente simbolismi astratti, formule o tecnicismi. "
        "Struttura: massimo 4-5 esercizi brevi, pochi sotto-punti."
    ),
    "Scuola Secondaria I grado (Medie)": (
        "Scuola media (11–14 anni): linguaggio chiaro e accessibile, "
        "contenuti ancorati ai programmi ministeriali. "
        "Esercizi graduati: dal semplice al complesso. "
        "Niente dimostrazioni avanzate o calcoli complessi fuori programma."
    ),
    "Liceo Scientifico": (
        "Liceo scientifico (14–19 anni): rigore scientifico e matematico, "
        "uso appropriato di notazioni formali (ℝ, ∀, ∃, etc.). "
        "Può includere dimostrazioni, problemi aperti, ragionamento deduttivo. "
        "Livello: programma MIUR liceo scientifico."
    ),
    "Liceo Classico": (
        "Liceo classico (14–19 anni): rigore umanistico e linguistico, "
        "attenzione alla proprietà di linguaggio e all'argomentazione. "
        "Per materie scientifiche: livello base-intermedio. "
        "Può includere analisi testuale, traduzioni, riflessioni critiche."
    ),
    "Liceo Linguistico": (
        "Liceo linguistico (14–19 anni): focus su competenze comunicative, "
        "analisi del testo e produzione scritta. "
        "Possibile inclusione di esercizi in L2 se materia linguistica. "
        "Livello: programma MIUR liceo linguistico."
    ),
    "Liceo delle Scienze Umane": (
        "Liceo scienze umane (14–19 anni): taglio pedagogico, sociologico, psicologico. "
        "Testo riflessivo, connessioni interdisciplinari. "
        "Evita tecnicismi matematici avanzati."
    ),
    "Liceo Artistico": (
        "Liceo artistico (14–19 anni): taglio creativo-espressivo, "
        "attenzione alla dimensione estetica e progettuale. "
        "Per materie teoriche: approccio descrittivo e contestualizzante."
    ),
    "Istituto Tecnico Tecnologico/Industriale": (
        "ITI / ITIS (14–19 anni): approccio applicativo e tecnico-pratico. "
        "Problemi reali, calcoli ingegneristici di base, schemi, dimensionamenti. "
        "Linguaggio tecnico appropriato. Livello: programma MIUR ITI."
    ),
    "Istituto Tecnico Economico": (
        "ITE / ITEC (14–19 anni): approccio economico-aziendale, "
        "analisi di dati, bilanci semplificati, casi aziendali. "
        "Linguaggio economico-giuridico appropriato."
    ),
    "Istituto Tecnico Agrario/Ambientale": (
        "ITA (14–19 anni): approccio scientifico-applicativo in ambito agrario, "
        "biologico, ambientale. Terminologia tecnica di settore."
    ),
    "Istituto Professionale": (
        "Istituto professionale (14–19 anni): approccio pratico-laboratoriale, "
        "contenuti essenziali e immediatamente applicabili. "
        "Linguaggio semplice e diretto. Evita astrazioni eccessive."
    ),
}

# ── MATERIE ────────────────────────────────────────────────────────────────────
MATERIE = [
    "Matematica", "Fisica", "Chimica", "Biologia",
    "Scienze della Terra", "Informatica",
    "Italiano", "Latino", "Greco", "Storia", "Geografia",
    "Filosofia", "Inglese", "Francese", "Spagnolo", "Tedesco",
    "Arte e Immagine", "Musica", "Educazione Fisica",
    "Economia Aziendale", "Diritto", "Tecnologia",
    "Scienze Umane", "Psicologia", "Sociologia",
    "Religione", "Altra materia",
]

MATERIE_ICONS = {
    "Matematica": "📐", "Fisica": "⚛️", "Chimica": "🧪", "Biologia": "🧬",
    "Scienze della Terra": "🌍", "Informatica": "💻",
    "Italiano": "✍️", "Latino": "🏛️", "Greco": "🏺", "Storia": "📜",
    "Geografia": "🗺️", "Filosofia": "🤔", "Inglese": "🇬🇧",
    "Francese": "🇫🇷", "Spagnolo": "🇪🇸", "Tedesco": "🇩🇪",
    "Arte e Immagine": "🎨", "Musica": "🎵", "Educazione Fisica": "⚽",
    "Economia Aziendale": "📊", "Diritto": "⚖️", "Tecnologia": "🔧",
    "Scienze Umane": "🧠", "Psicologia": "💭", "Sociologia": "👥",
    "Religione": "✝️", "Altra materia": "📚",
}

# Esempio completo mostrato in trasparenza nel riquadro "Cosa vuoi nella verifica?":
# prima riga = argomento, righe successive = cosa includere o evitare.
ESEMPI_RICHIESTA = {
    "Matematica": (
        "Es. Equazioni di secondo grado e parabola\n"
        "Parti con un esercizio di calcolo diretto, poi aumenta piano piano la difficoltà.\n"
        "Metti un vero o falso sui concetti essenziali, un esercizio a risposta aperta in cui spiegare un ragionamento "
        "e un problema di realtà, con una situazione di vita quotidiana.\n"
        "Includi un grafico da leggere e interpretare.\n"
        "Evita le dimostrazioni e usa numeri interi, per non perdere tempo nei calcoli."
    ),
    "Fisica": (
        "Es. Il moto rettilineo uniformemente accelerato\n"
        "Parti da una domanda sui concetti essenziali (vero o falso), poi un esercizio di calcolo con i dati già pronti.\n"
        "Aggiungi un problema con una situazione reale, come un'auto che frena o un ascensore, "
        "e un grafico velocità-tempo da interpretare.\n"
        "Chiedi almeno una volta di spiegare a parole il perché del risultato.\n"
        "Evita il calcolo con i vettori e fai indicare sempre le unità di misura."
    ),
    "Italiano": (
        "Es. I Promessi Sposi, capitoli 1-8\n"
        "Parti con qualche domanda di comprensione sul testo, poi un'analisi dei personaggi principali.\n"
        "Metti un vero o falso sulla trama, una domanda aperta in cui spiegare con parole proprie "
        "e un breve brano da commentare.\n"
        "Includi una domanda sul lessico e una su chi racconta la storia.\n"
        "Evita domande che richiedono solo di ricordare a memoria."
    ),
}
ESEMPIO_RICHIESTA_DEFAULT = (
    "Es. Il Rinascimento in Italia\n"
    "Parti con domande dirette sui fatti principali, poi aumenta piano piano la difficoltà.\n"
    "Metti un vero o falso sui concetti essenziali, due domande aperte in cui spiegare con parole proprie "
    "e un breve brano o una fonte da commentare.\n"
    "Includi un esercizio che chieda di collegare cause e conseguenze.\n"
    "Evita date troppo precise e curiosità secondarie, e usa un linguaggio chiaro, adatto alla classe."
)


# ── TOKEN DI DESIGN ─────────────────────────────────────────────────────────────
# Una sola scala per spazi, raggi, ombre e tipografia (i colori stanno in THEMES).
# Chi scrive HTML o CSS nuovo usa questi valori, non numeri a caso.
SPAZIO_REM = {"xs": 0.25, "sm": 0.5, "md": 0.75, "lg": 1.0, "xl": 1.5, "xxl": 2.0}
RAGGIO_PX = {"controllo": 8, "card": 12, "superficie": 16, "chip": 999}
OMBRA = {
    "riposo": "0 1px 3px rgba(0,0,0,.08)",
    "rialzo": "0 4px 16px rgba(0,0,0,.12)",
}
TIPO_REM = {
    "titolo_pagina": 1.7,   # una sola misura per il titolo di ogni pagina
    "sezione": 1.15,
    "testo": 1.0,
    "secondario": 0.875,
    "minimo": 0.8,          # niente testo più piccolo di così
}
AREA_TOCCO_MIN_PX = 44      # altezza minima di ogni controllo interattivo

# Pulsanti: primario (pieno, uno per schermata) · secondario (contorno) ·
# terziario (solo testo, type="tertiary") · distruttivo (terziario con testo rosso).


# Durata della verifica: un solo scatto sceglie numero di esercizi e tempo previsto.
# I punti restano 100 (si cambiano in "Altre opzioni"). Tetto assoluto: 8 esercizi.
DURATE = {
    "Breve":    {"num_esercizi": 3, "durata": "30 minuti"},
    "Standard": {"num_esercizi": 5, "durata": "1 ora"},
    "Lunga":    {"num_esercizi": 8, "durata": "2 ore"},
}
DURATA_DEFAULT = "Standard"
MAX_ESERCIZI_PRESET = 8
MAX_ESERCIZI_PRIMARIA = 5   # CALIBRAZIONE_SCUOLA: "massimo 4-5 esercizi brevi"


def parametri_durata(nome: str, scuola: str = "") -> dict:
    """
    Parametri della durata scelta: {"num_esercizi", "durata", "punti_totali"}.
    Rispetta il tetto di 8 esercizi e quello della scuola primaria (5).
    Nome sconosciuto → durata di default.
    """
    base = DURATE.get(nome) or DURATE[DURATA_DEFAULT]
    tetto = MAX_ESERCIZI_PRIMARIA if "Primaria" in (scuola or "") else MAX_ESERCIZI_PRESET
    return {
        "num_esercizi": max(1, min(base["num_esercizi"], tetto, MAX_ESERCIZI_PRESET)),
        "durata": base["durata"],
        "punti_totali": 100,
    }


def etichetta_durata(nome: str, scuola: str = "") -> str:
    """Testo del selettore: es. 'Standard · 5 esercizi'."""
    p = parametri_durata(nome, scuola)
    n = p["num_esercizi"]
    return f"{nome} · {n} {'esercizio' if n == 1 else 'esercizi'}"


def esempio_richiesta(materia: str) -> str:
    """Esempio in trasparenza per il riquadro della richiesta, scelto in base alla materia."""
    return ESEMPI_RICHIESTA.get(materia, ESEMPIO_RICHIESTA_DEFAULT)


NOTE_PLACEHOLDER = (
    "Es: includi una domanda sulla derivata di sen(x), "
    "aggiungi un grafico con pgfplots, "
    "inserisci almeno 2 esercizi Vero/Falso..."
)

TIPI_ESERCIZIO = [
    "Misto (consigliato)",
    "Solo Vero/Falso",
    "Solo Scelta Multipla",
    "Solo Completamento",
    "Solo Domande aperte",
    "Solo Problemi/Calcoli",
]
