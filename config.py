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
}


def scegli_modello_per_compito(compito: str, model_id_piano: str):
    """Restituisce (model_id, tetto_ragionamento) per un compito, dato il modello del piano."""
    tipo, ragionamento = COMPITI_AI.get(compito, ("piano", None))
    if tipo == "veloce":
        model_id = MODEL_FAST_ID
    elif tipo == "medio":
        model_id = MODEL_FAST_ID if model_id_piano == MODEL_FAST_ID else MODEL_FLASH_ID
    else:
        model_id = model_id_piano
    if model_id == MODEL_FAST_ID:
        return model_id, (0 if ragionamento == 0 else None)   # Lite: spento solo dove richiesto
    if ragionamento == "alto":
        ragionamento = RAGIONAMENTO_ALTO.get(model_id)
    return model_id, ragionamento

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
        "Es.\n"
        "Equazioni di secondo grado e parabola\n"
        "- 4 esercizi, difficoltà crescente: il primo di calcolo diretto\n"
        "- includi un grafico da leggere (senza scrivere l'equazione sul grafico)\n"
        "- un problema di realtà e un vero/falso\n"
        "- evita le dimostrazioni e i parametri letterali\n"
        "- usa numeri interi"
    ),
    "Fisica": (
        "Es.\n"
        "Moto rettilineo uniformemente accelerato\n"
        "- 4 esercizi: una formula inversa e un grafico velocità-tempo da interpretare\n"
        "- un problema con dati reali (auto, ascensore)\n"
        "- evita il calcolo vettoriale\n"
        "- esprimi tutto in unità SI e chiedi di indicarle"
    ),
    "Italiano": (
        "Es.\n"
        "Promessi Sposi: capitoli 1-8\n"
        "- 5 domande: comprensione, analisi dei personaggi, un'inferenza\n"
        "- una domanda sul lessico e una sul narratore\n"
        "- includi un breve brano da commentare\n"
        "- evita domande solo mnemoniche"
    ),
}
ESEMPIO_RICHIESTA_DEFAULT = (
    "Es.\n"
    "Il Rinascimento in Italia\n"
    "- 5 esercizi, difficoltà crescente: parti da domande dirette\n"
    "- includi 2 domande aperte e un vero/falso\n"
    "- usa una breve fonte o un brano da commentare\n"
    "- evita date troppo precise e curiosità secondarie\n"
    "- linguaggio chiaro, adatto alla classe"
)


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
