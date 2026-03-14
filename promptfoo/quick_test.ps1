# Quick Test - Evita reinstallazioni
# ==================================

Write-Host "🚀 Quick Test VerificAI" -ForegroundColor Green

# Setup rapido
$env:GEMINI_API_KEY = $env:GEMINI_API_KEY  # Mantiene la tua API key
$env:VERIFICAI_ROOT = "C:\Users\gobli\Desktop\verificai"

# Controlla se abbiamo già una versione di PromptFoo
$possiblePaths = @(
    ".\node_modules\.bin\promptfoo.cmd",
    "C:\Users\gobli\AppData\Roaming\npm\promptfoo.cmd",
    "C:\Users\gobli\AppData\Roaming\npm\promptfoo",
    "C:\Program Files\nodejs\promptfoo.cmd"
)

$promptfooCmd = $null
foreach ($path in $possiblePaths) {
    if (Test-Path $path) {
        $promptfooCmd = $path
        Write-Host "✅ Trovato PromptFoo in: $path" -ForegroundColor Green
        break
    }
}

if (-not $promptfooCmd) {
    Write-Host "📦 PromptFoo non trovato, tentativo npx rapido..." -ForegroundColor Yellow
    $promptfooCmd = "C:\Program Files\nodejs\npx.cmd"
}

# Menu rapido
Write-Host "`n📋 Opzioni test:" -ForegroundColor Cyan
Write-Host "1. Test Titoli (3 test)" -ForegroundColor White
Write-Host "2. Test Completo (12 test)" -ForegroundColor White  
Write-Host "3. Test specifico" -ForegroundColor White
Write-Host "4. Solo check configurazione" -ForegroundColor White

$choice = Read-Host "`nScelta (1-4)"

switch ($choice) {
    "1" {
        Write-Host "🧪 Eseguo test titoli..." -ForegroundColor Magenta
        $filter = "Titolo"
    }
    "2" { 
        Write-Host "🧪 Eseguo test completo..." -ForegroundColor Magenta
        $filter = ""
    }
    "3" {
        $filter = Read-Host "Inserisci filtro (es: Titolo, Corpo, QA)"
        Write-Host "🧪 Eseguo test con filtro: $filter" -ForegroundColor Magenta
    }
    "4" {
        Write-Host "🔍 Check configurazione..." -ForegroundColor Magenta
        python test_assertions.py
        python test_provider.py
        return
    }
    default {
        Write-Host "❌ Scelta non valida" -ForegroundColor Red
        return
    }
}

# Esegui test
$arguments = @("eval", "-j", "1")
if ($filter) {
    $arguments += "--filter-description", $filter
}

Write-Host "🚀 Lancio: $($promptfooCmd) promptfoo@latest $($arguments -join ' ')" -ForegroundColor Green

try {
    if ($promptfooCmd -like "*npx*") {
        & $promptfooCmd "promptfoo@latest" $arguments
    } else {
        & $promptfooCmd $arguments
    }
} catch {
    Write-Host "❌ Errore esecuzione: $_" -ForegroundColor Red
    Write-Host "💡 Suggerimento: potrebbe servire la prima installazione" -ForegroundColor Yellow
}
