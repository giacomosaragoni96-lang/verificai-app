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
# Tema unico: Notte (Dark Midnight Blue).
# ───────────────────────────────────────────────────────────────────────────────

THEMES = {
    # ═══════════════════════════════════════════════════════════════════════
    #  NOTTE — Dark Midnight Blue  (default)
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

        # Hint boxes
        "hint_bg":      "#0D2340",
        "hint_border":  "#1F4070",
        "hint_text":    "#79C0FF",
    },

    # ═══════════════════════════════════════════════════════════════════════
    #  CHIARO (Giorno) — Elegant light: cream, warm gray, teal accent
    #  Palette: Cream #FAF9F7, Warm Gray, Teal #0D9488, Slate sidebar
    # ═══════════════════════════════════════════════════════════════════════
    "chiaro": {
        # Superfici — cream e bianco caldo, nessun grigio freddo
        "bg":         "#F5F4F0",     # Warm cream — base elegante
        "bg2":        "#EBE9E4",     # secondo livello
        "card":       "#FFFFFF",     # card bianca pura
        "card2":      "#FAFAF9",     # overlay leggermente caldo

        # Testo — charcoal caldo, massima leggibilità
        "text":       "#1C1917",     # Warm black
        "text2":      "#44403C",     # secondario
        "muted":      "#78716C",     # stone muted

        # Bordi — sottili, caldi
        "border":     "#E7E5E4",     # stone 200
        "border2":    "#D6D3D1",     # stone 300

        # Accent — Teal elegante (non verde piatto)
        "accent":       "#0D9488",   # Teal 600
        "accent2":      "#0F766E",   # Teal 700 (hover)
        "accent_light": "#CCFBF1",   # Teal 100 — pill/hint

        # Interazione
        "hover":      "#F0FDFA",     # Teal 50

        # Semantici
        "success":    "#059669",     # Emerald 600
        "warn":       "#D97706",     # Amber 600
        "error":      "#DC2626",     # Red 600

        # Ombre — morbide, eleganti
        "shadow":     "0 1px 2px rgba(28,25,23,.06)",
        "shadow_md":  "0 4px 20px rgba(28,25,23,.08), 0 1px 3px rgba(28,25,23,.04)",
        "shadow_soft": "0 12px 40px rgba(28,25,23,.06), 0 2px 8px rgba(28,25,23,.03)",

        # Design system
        "radius_sm":  "8px",
        "radius_md":  "12px",
        "radius_lg":  "16px",

        # Sidebar — slate scuro elegante, accent teal
        "sidebar_bg":      "linear-gradient(180deg, #1E293B 0%, #0F172A 100%)",
        "sidebar_border":  "#334155",
        "sidebar_accent":  "#2DD4BF",   # Teal 400
        "sidebar_input_bg":  "#1E293B",
        "sidebar_input_text": "#E2E8F0",

        # Hint boxes
        "hint_bg":      "#CCFBF1",
        "hint_border":  "#5EEAD4",
        "hint_text":    "#0F766E",
    },

    # ═══════════════════════════════════════════════════════════════════════
    #  FORESTA — Elegant paper/sage: calm, study, nature, professional
    #  Palette: Paper #F5F7F4, Sage #E8EDE4, Forest #166534, Deep green sidebar
    # ═══════════════════════════════════════════════════════════════════════
    "foresta": {
        # Superfici — carta e sage chiarissimo, non cielo azzurro
        "bg":         "#F2F5F0",     # Paper — verde-grigio molto chiaro
        "bg2":        "#E8EDE4",     # Sage chiaro
        "card":       "#FFFFFF",     # carta bianca
        "card2":      "#F8FAF6",     # overlay con hint verde

        # Testo — inchiostro verde scuro (forest ink)
        "text":       "#1A2E1A",     # Forest black
        "text2":      "#2D4A2D",     # secondario
        "muted":      "#527352",     # muted sage

        # Bordi — sottili, verdi neutri
        "border":     "#D1DED1",     # bordo sage
        "border2":    "#B5C9B5",     # bordo più marcato

        # Accent — Forest green elegante
        "accent":       "#166534",   # Green 800 — forest
        "accent2":      "#15803D",   # Green 700 (hover)
        "accent_light": "#DCFCE7",   # Green 100 — pill/hint

        # Interazione
        "hover":      "#ECFDF5",     # Green 50

        # Semantici
        "success":    "#15803D",     # Green 700
        "warn":       "#CA8A04",     # Yellow 700
        "error":      "#B91C1C",     # Red 700

        # Ombre — morbide, naturali
        "shadow":     "0 1px 2px rgba(22,101,52,.06)",
        "shadow_md":  "0 4px 20px rgba(22,101,52,.08), 0 1px 3px rgba(22,101,52,.04)",
        "shadow_soft": "0 12px 40px rgba(22,101,52,.06), 0 2px 8px rgba(22,101,52,.03)",

        # Design system
        "radius_sm":  "8px",
        "radius_md":  "12px",
        "radius_lg":  "16px",

        # Sidebar — forest scuro, elegante
        "sidebar_bg":      "linear-gradient(180deg, #14532D 0%, #052E16 100%)",
        "sidebar_border":  "#166534",
        "sidebar_accent":  "#86EFAC",   # Green 300
        "sidebar_input_bg":  "#14532D",
        "sidebar_input_text": "#BBF7D0",

        # Hint boxes
        "hint_bg":      "#DCFCE7",
        "hint_border":  "#86EFAC",
        "hint_text":    "#166534",
    },

    # ═══════════════════════════════════════════════════════════════════════
    #  SANGUE — Crimson Editorial  (dramatic, noir, ink-on-black)
    #  Palette: Wine-black bg · Vivid crimson accent · rose-white text
    # ═══════════════════════════════════════════════════════════════════════
    "sangue": {
        "bg":         "#0C0608",
        "bg2":        "#160A0C",
        "card":       "#1E0D11",
        "card2":      "#260F15",
        "text":       "#F5E8EC",
        "text2":      "#C4909B",
        "muted":      "#8A5562",
        "border":     "#3A1820",
        "border2":    "#4F2430",
        "accent":       "#E53E5E",
        "accent2":      "#FF6080",
        "accent_light": "#3A0B14",
        "hover":      "#1F0B0F",
        "success":    "#4ADE80",
        "warn":       "#FBBF24",
        "error":      "#FF8C8C",
        "shadow":     "0 1px 3px rgba(0,0,0,.55)",
        "shadow_md":  "0 4px 24px rgba(0,0,0,.70)",
        "shadow_soft": "0 8px 32px rgba(12,6,8,.75), 0 2px 8px rgba(0,0,0,.35)",
        "radius_sm":  "8px",
        "radius_md":  "12px",
        "radius_lg":  "16px",
        "sidebar_bg":       "linear-gradient(180deg, #060203 0%, #0C0608 100%)",
        "sidebar_border":   "#3A1820",
        "sidebar_accent":   "#FF6080",
        "sidebar_input_bg":  "#160A0C",
        "sidebar_input_text": "#F5E8EC",
        "hint_bg":      "#3A0B14",
        "hint_border":  "#8B1A2F",
        "hint_text":    "#FF6080",
    },

    # ═══════════════════════════════════════════════════════════════════════
    #  ABISSO — Bioluminescent Abyss  (deep ocean, alien, futuristic)
    #  Palette: Ocean-black bg · Acid cyan-green accent · pale aqua text
    # ═══════════════════════════════════════════════════════════════════════
    "abisso": {
        "bg":         "#020D10",
        "bg2":        "#061620",
        "card":       "#0A1F2A",
        "card2":      "#0E2A38",
        "text":       "#C5F5E8",
        "text2":      "#5EC8A8",
        "muted":      "#2E8A6C",
        "border":     "#0E3040",
        "border2":    "#145060",
        "accent":       "#00FFBE",
        "accent2":      "#22FFD4",
        "accent_light": "#00261A",
        "hover":      "#071A22",
        "success":    "#22C55E",
        "warn":       "#FBBF24",
        "error":      "#FF6B6B",
        "shadow":     "0 1px 3px rgba(0,0,0,.55)",
        "shadow_md":  "0 4px 24px rgba(0,0,0,.70)",
        "shadow_soft": "0 8px 32px rgba(2,13,16,.75), 0 2px 8px rgba(0,0,0,.35)",
        "radius_sm":  "8px",
        "radius_md":  "12px",
        "radius_lg":  "16px",
        "sidebar_bg":       "linear-gradient(180deg, #010609 0%, #020D10 100%)",
        "sidebar_border":   "#0E3040",
        "sidebar_accent":   "#22FFD4",
        "sidebar_input_bg":  "#061620",
        "sidebar_input_text": "#C5F5E8",
        "hint_bg":      "#00261A",
        "hint_border":  "#006644",
        "hint_text":    "#00FFBE",
    },

    # ═══════════════════════════════════════════════════════════════════════
    #  TOKIO — Tokyo Neon  (cyberpunk, night city, ultra-vibrant)
    #  Palette: Purple-black bg · Hot magenta accent · violet-white text
    # ═══════════════════════════════════════════════════════════════════════
    "tokio": {
        "bg":         "#0C0B14",
        "bg2":        "#13111E",
        "card":       "#1A1828",
        "card2":      "#20203A",
        "text":       "#F0E8FF",
        "text2":      "#B89EE8",
        "muted":      "#7A6AA8",
        "border":     "#2A2445",
        "border2":    "#363060",
        "accent":       "#FF2D78",
        "accent2":      "#FF61A0",
        "accent_light": "#3A0820",
        "hover":      "#18142A",
        "success":    "#4ADE80",
        "warn":       "#FBBF24",
        "error":      "#FF6060",
        "shadow":     "0 1px 3px rgba(0,0,0,.55)",
        "shadow_md":  "0 4px 24px rgba(0,0,0,.70)",
        "shadow_soft": "0 8px 32px rgba(12,11,20,.75), 0 2px 8px rgba(0,0,0,.35)",
        "radius_sm":  "8px",
        "radius_md":  "12px",
        "radius_lg":  "16px",
        "sidebar_bg":       "linear-gradient(180deg, #060510 0%, #0C0B14 100%)",
        "sidebar_border":   "#2A2445",
        "sidebar_accent":   "#FF61A0",
        "sidebar_input_bg":  "#13111E",
        "sidebar_input_text": "#F0E8FF",
        "hint_bg":      "#3A0820",
        "hint_border":  "#8B1045",
        "hint_text":    "#FF61A0",
    },

    # ═══════════════════════════════════════════════════════════════════════
    #  SABBIA — Desert Gold  (archaeological, parchment, timeless)
    #  Palette: Warm near-black bg · Burnished gold accent · parchment text
    # ═══════════════════════════════════════════════════════════════════════
    "sabbia": {
        "bg":         "#0E0C07",
        "bg2":        "#181510",
        "card":       "#201D14",
        "card2":      "#29261B",
        "text":       "#F8EDCD",
        "text2":      "#C9AC72",
        "muted":      "#8A7248",
        "border":     "#382F16",
        "border2":    "#4E4220",
        "accent":       "#D4A043",
        "accent2":      "#E8B85A",
        "accent_light": "#281C00",
        "hover":      "#1A1809",
        "success":    "#52C47A",
        "warn":       "#E85D04",
        "error":      "#E54B4B",
        "shadow":     "0 1px 3px rgba(0,0,0,.55)",
        "shadow_md":  "0 4px 24px rgba(0,0,0,.70)",
        "shadow_soft": "0 8px 32px rgba(14,12,7,.75), 0 2px 8px rgba(0,0,0,.35)",
        "radius_sm":  "8px",
        "radius_md":  "12px",
        "radius_lg":  "16px",
        "sidebar_bg":       "linear-gradient(180deg, #060503 0%, #0E0C07 100%)",
        "sidebar_border":   "#382F16",
        "sidebar_accent":   "#E8B85A",
        "sidebar_input_bg":  "#181510",
        "sidebar_input_text": "#F8EDCD",
        "hint_bg":      "#281C00",
        "hint_border":  "#704A0C",
        "hint_text":    "#E8B85A",
    },

    # ═══════════════════════════════════════════════════════════════════════
    #  GLITCH — Neon Cyber  (hacker terminal, synthwave, electric)
    #  Palette: True black bg · Electric lime accent · neon-tinted text
    # ═══════════════════════════════════════════════════════════════════════
    "glitch": {
        "bg":         "#080808",
        "bg2":        "#101010",
        "card":       "#181818",
        "card2":      "#202020",
        "text":       "#EEFFEE",
        "text2":      "#7AE08A",
        "muted":      "#3D8A4A",
        "border":     "#1C2C1C",
        "border2":    "#2A402A",
        "accent":       "#39FF14",
        "accent2":      "#70FF45",
        "accent_light": "#0A1A0A",
        "hover":      "#101A10",
        "success":    "#50E850",
        "warn":       "#FFD700",
        "error":      "#FF3131",
        "shadow":     "0 1px 3px rgba(0,0,0,.60)",
        "shadow_md":  "0 4px 24px rgba(0,0,0,.75)",
        "shadow_soft": "0 8px 32px rgba(8,8,8,.80), 0 2px 8px rgba(0,0,0,.40)",
        "radius_sm":  "8px",
        "radius_md":  "12px",
        "radius_lg":  "16px",
        "sidebar_bg":       "linear-gradient(180deg, #050505 0%, #080808 100%)",
        "sidebar_border":   "#1C2C1C",
        "sidebar_accent":   "#70FF45",
        "sidebar_input_bg":  "#101010",
        "sidebar_input_text": "#EEFFEE",
        "hint_bg":      "#0A1A0A",
        "hint_border":  "#1A4A1A",
        "hint_text":    "#39FF14",
    },

    # ═══════════════════════════════════════════════════════════════════════
    #  MARMO — Marble  (minimal, ultra-refined, cool monochrome)
    #  Palette: Dark cool-gray bg · Slate-violet accent · pearl text
    # ═══════════════════════════════════════════════════════════════════════
    "marmo": {
        "bg":         "#111118",
        "bg2":        "#18181F",
        "card":       "#1E1E28",
        "card2":      "#242430",
        "text":       "#EEEEF8",
        "text2":      "#9898B8",
        "muted":      "#606080",
        "border":     "#28283C",
        "border2":    "#363650",
        "accent":       "#8888CC",
        "accent2":      "#AAAAEE",
        "accent_light": "#14143A",
        "hover":      "#1A1A25",
        "success":    "#68D498",
        "warn":       "#D4B060",
        "error":      "#CC6680",
        "shadow":     "0 1px 3px rgba(0,0,0,.50)",
        "shadow_md":  "0 4px 24px rgba(0,0,0,.65)",
        "shadow_soft": "0 8px 32px rgba(17,17,24,.70), 0 2px 8px rgba(0,0,0,.30)",
        "radius_sm":  "8px",
        "radius_md":  "12px",
        "radius_lg":  "16px",
        "sidebar_bg":       "linear-gradient(180deg, #0A0A12 0%, #111118 100%)",
        "sidebar_border":   "#28283C",
        "sidebar_accent":   "#AAAAEE",
        "sidebar_input_bg":  "#18181F",
        "sidebar_input_text": "#EEEEF8",
        "hint_bg":      "#14143A",
        "hint_border":  "#383870",
        "hint_text":    "#AAAAEE",
    },

    # ═══════════════════════════════════════════════════════════════════════
    #  VULCANO — Lava  (volcanic, explosive, high-energy)
    #  Palette: Volcanic rock bg · Lava orange accent · fire-lit cream text
    # ═══════════════════════════════════════════════════════════════════════
    "vulcano": {
        "bg":         "#0C0804",
        "bg2":        "#181008",
        "card":       "#201610",
        "card2":      "#281E14",
        "text":       "#FFF0DC",
        "text2":      "#D4A060",
        "muted":      "#956840",
        "border":     "#3A2010",
        "border2":    "#502C14",
        "accent":       "#FF6B00",
        "accent2":      "#FF8C2A",
        "accent_light": "#2A0E00",
        "hover":      "#1C1008",
        "success":    "#52C47A",
        "warn":       "#FFE042",
        "error":      "#FF4040",
        "shadow":     "0 1px 3px rgba(0,0,0,.55)",
        "shadow_md":  "0 4px 24px rgba(0,0,0,.70)",
        "shadow_soft": "0 8px 32px rgba(12,8,4,.75), 0 2px 8px rgba(0,0,0,.35)",
        "radius_sm":  "8px",
        "radius_md":  "12px",
        "radius_lg":  "16px",
        "sidebar_bg":       "linear-gradient(180deg, #060402 0%, #0C0804 100%)",
        "sidebar_border":   "#3A2010",
        "sidebar_accent":   "#FF8C2A",
        "sidebar_input_bg":  "#181008",
        "sidebar_input_text": "#FFF0DC",
        "hint_bg":      "#2A0E00",
        "hint_border":  "#7C3A00",
        "hint_text":    "#FF8C2A",
    },

    # ═══════════════════════════════════════════════════════════════════════
    #  SPAZIO — Deep Space  (stellar, cosmic, mysterious)
    #  Palette: Space-black bg · Star gold accent · stellar pale text
    # ═══════════════════════════════════════════════════════════════════════
    "spazio": {
        "bg":         "#08070F",
        "bg2":        "#10101A",
        "card":       "#161626",
        "card2":      "#1E1E32",
        "text":       "#F0EEFF",
        "text2":      "#9898D4",
        "muted":      "#5C5A8C",
        "border":     "#20203A",
        "border2":    "#2C2C50",
        "accent":       "#FFD700",
        "accent2":      "#FFE55A",
        "accent_light": "#20180A",
        "hover":      "#141428",
        "success":    "#52D8A0",
        "warn":       "#FF8C60",
        "error":      "#FF6080",
        "shadow":     "0 1px 3px rgba(0,0,0,.55)",
        "shadow_md":  "0 4px 24px rgba(0,0,0,.70)",
        "shadow_soft": "0 8px 32px rgba(8,7,15,.75), 0 2px 8px rgba(0,0,0,.35)",
        "radius_sm":  "8px",
        "radius_md":  "12px",
        "radius_lg":  "16px",
        "sidebar_bg":       "linear-gradient(180deg, #04040A 0%, #08070F 100%)",
        "sidebar_border":   "#20203A",
        "sidebar_accent":   "#FFE55A",
        "sidebar_input_bg":  "#10101A",
        "sidebar_input_text": "#F0EEFF",
        "hint_bg":      "#20180A",
        "hint_border":  "#604010",
        "hint_text":    "#FFD700",
    },

    # ═══════════════════════════════════════════════════════════════════════
    #  RUBINO — Ruby Rose  (luxury, editorial, jewel-toned)
    #  Palette: Dark wine-violet bg · Deep rose accent · pale rose text
    # ═══════════════════════════════════════════════════════════════════════
    "rubino": {
        "bg":         "#0C0610",
        "bg2":        "#140C1A",
        "card":       "#1C1224",
        "card2":      "#241A2E",
        "text":       "#F8E8F8",
        "text2":      "#C890C8",
        "muted":      "#8A5890",
        "border":     "#2E1840",
        "border2":    "#3E2255",
        "accent":       "#FF1493",
        "accent2":      "#FF55AA",
        "accent_light": "#380A28",
        "hover":      "#18102A",
        "success":    "#4ADE80",
        "warn":       "#FBBF24",
        "error":      "#FF5050",
        "shadow":     "0 1px 3px rgba(0,0,0,.55)",
        "shadow_md":  "0 4px 24px rgba(0,0,0,.70)",
        "shadow_soft": "0 8px 32px rgba(12,6,16,.75), 0 2px 8px rgba(0,0,0,.35)",
        "radius_sm":  "8px",
        "radius_md":  "12px",
        "radius_lg":  "16px",
        "sidebar_bg":       "linear-gradient(180deg, #06030A 0%, #0C0610 100%)",
        "sidebar_border":   "#2E1840",
        "sidebar_accent":   "#FF55AA",
        "sidebar_input_bg":  "#140C1A",
        "sidebar_input_text": "#F8E8F8",
        "hint_bg":      "#380A28",
        "hint_border":  "#8B1060",
        "hint_text":    "#FF55AA",
    },

    # ═══════════════════════════════════════════════════════════════════════
    #  MENTA — Neon Mint  (hacker terminal, fresh, electric)
    #  Palette: Dark teal-black bg · Electric mint accent · aqua-white text
    # ═══════════════════════════════════════════════════════════════════════
    "menta": {
        "bg":         "#030E0C",
        "bg2":        "#081A16",
        "card":       "#0D2420",
        "card2":      "#122E2A",
        "text":       "#D8FFF4",
        "text2":      "#60D4B0",
        "muted":      "#2E9A7A",
        "border":     "#0E3A30",
        "border2":    "#165040",
        "accent":       "#00E5A8",
        "accent2":      "#22FFD0",
        "accent_light": "#00281E",
        "hover":      "#081E1A",
        "success":    "#4ADE80",
        "warn":       "#FFD060",
        "error":      "#FF5560",
        "shadow":     "0 1px 3px rgba(0,0,0,.55)",
        "shadow_md":  "0 4px 24px rgba(0,0,0,.70)",
        "shadow_soft": "0 8px 32px rgba(3,14,12,.75), 0 2px 8px rgba(0,0,0,.35)",
        "radius_sm":  "8px",
        "radius_md":  "12px",
        "radius_lg":  "16px",
        "sidebar_bg":       "linear-gradient(180deg, #010806 0%, #030E0C 100%)",
        "sidebar_border":   "#0E3A30",
        "sidebar_accent":   "#22FFD0",
        "sidebar_input_bg":  "#081A16",
        "sidebar_input_text": "#D8FFF4",
        "hint_bg":      "#00281E",
        "hint_border":  "#006644",
        "hint_text":    "#00E5A8",
    },
}

THEME_LABELS = {
    "notte":    "🌙 Notte",
    "chiaro":   "☀️ Giorno",
    "foresta":  "🌿 Foresta",
    "sangue":   "🩸 Sangue",
    "abisso":   "🌊 Abisso",
    "tokio":    "⚡ Tokio",
    "sabbia":   "🏜️ Sabbia",
    "glitch":   "💚 Glitch",
    "marmo":    "🪨 Marmo",
    "vulcano":  "🌋 Vulcano",
    "spazio":   "⭐ Spazio",
    "rubino":   "💎 Rubino",
    "menta":    "🌿 Menta",
}

DEFAULT_THEME = "notte"

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
