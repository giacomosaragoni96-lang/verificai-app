# VerificAI PromptFoo Test Runner - Windows PowerShell
# ====================================================

# Setup environment variables
$env:GEMINI_API_KEY = "LA_MIA_CHIAVE"
$env:VERIFICAI_ROOT = "C:\Users\gobli\Desktop\verificai"

Write-Host "🚀 Avvio test suite VerificAI con PromptFoo..." -ForegroundColor Green
Write-Host "Environment variables configurate" -ForegroundColor Yellow

# Change to promptfoo directory
Set-Location "C:\Users\gobli\Desktop\verificai\promptfoo"

# Run tests
Write-Host "Esecuzione test sequenziali (-j 1)..." -ForegroundColor Cyan
promptfoo eval -j 1

# Show results
Write-Host "Apri risultati nel browser con: promptfoo view" -ForegroundColor Magenta
