#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
#  VerificAI — PromptFoo Setup & Run
# ═══════════════════════════════════════════════════════════════════════════════
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# ── Colori output ───────────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  VerificAI — PromptFoo Test Suite${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
echo ""

# ── 1. Verifica GEMINI_API_KEY ──────────────────────────────────────────────
if [ -z "$GEMINI_API_KEY" ]; then
    echo -e "${RED}❌ GEMINI_API_KEY non impostata!${NC}"
    echo ""
    echo "   Esegui prima:"
    echo "   export GEMINI_API_KEY=la_tua_chiave_gemini"
    echo ""
    echo "   La trovi su: https://aistudio.google.com/apikey"
    exit 1
fi
echo -e "${GREEN}✅ GEMINI_API_KEY trovata${NC}"

# ── 2. Verifica VERIFICAI_ROOT ──────────────────────────────────────────────
if [ -z "$VERIFICAI_ROOT" ]; then
    # Prova a trovare prompts.py nella directory parent
    if [ -f "../prompts.py" ]; then
        export VERIFICAI_ROOT="$(cd .. && pwd)"
    elif [ -f "../../prompts.py" ]; then
        export VERIFICAI_ROOT="$(cd ../.. && pwd)"
    else
        echo -e "${RED}❌ VERIFICAI_ROOT non impostata e prompts.py non trovato!${NC}"
        echo ""
        echo "   Esegui prima:"
        echo "   export VERIFICAI_ROOT=/percorso/al/tuo/progetto"
        echo "   (la cartella dove si trova prompts.py)"
        exit 1
    fi
fi

if [ ! -f "$VERIFICAI_ROOT/prompts.py" ]; then
    echo -e "${RED}❌ prompts.py non trovato in $VERIFICAI_ROOT${NC}"
    exit 1
fi
echo -e "${GREEN}✅ VERIFICAI_ROOT = $VERIFICAI_ROOT${NC}"

# ── 3. Verifica dipendenze ──────────────────────────────────────────────────
if ! command -v promptfoo &> /dev/null; then
    echo -e "${YELLOW}⚠️  promptfoo non trovato. Installazione...${NC}"
    pip install promptfoo 2>/dev/null || npm install -g promptfoo
fi
echo -e "${GREEN}✅ promptfoo installato${NC}"

python3 -c "import google.generativeai" 2>/dev/null || {
    echo -e "${YELLOW}⚠️  google-generativeai non trovato. Installazione...${NC}"
    pip install google-generativeai
}
echo -e "${GREEN}✅ google-generativeai installato${NC}"

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Avvio test suite...${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
echo ""

# ── 4. Esegui i test ────────────────────────────────────────────────────────
# -j 1 = sequenziale (evita rate limiting Gemini)
# --no-cache = forza nuove chiamate API
promptfoo eval -j 1 "$@"

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Test completati! Apri i risultati con:${NC}"
echo -e "${GREEN}  promptfoo view${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
