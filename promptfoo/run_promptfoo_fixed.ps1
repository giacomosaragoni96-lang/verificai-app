# VerificAI PromptFoo Runner - Installazione Locale
# ===============================================

param(
    [string]$Filter = "",
    [string]$ApiKey = "",
    [switch]$NoCache
)

Write-Host "VerificAI PromptFoo Test Runner" -ForegroundColor Green

# Imposta environment variables
if ($ApiKey) {
    $env:GEMINI_API_KEY = $ApiKey
    Write-Host "API Key impostata" -ForegroundColor Yellow
} elseif (-not $env:GEMINI_API_KEY) {
    Write-Host "ATTENZIONE: GEMINI_API_KEY non impostata" -ForegroundColor Yellow
}

$env:VERIFICAI_ROOT = "C:\Users\gobli\Desktop\verificai"

# Controlla se PromptFoo e gia installato localmente
$localPromptfoo = ".\node_modules\.bin\promptfoo.cmd"
if (Test-Path $localPromptfoo) {
    Write-Host "PromptFoo locale trovato" -ForegroundColor Green
    $promptfooCmd = $localPromptfoo
} else {
    Write-Host "PromptFoo non trovato, uso npx..." -ForegroundColor Yellow
    $promptfooCmd = "C:\Program Files\nodejs\npx.cmd"
}

# Costruisci il comando
$arguments = @("promptfoo@latest", "eval", "-j", "1")
if ($Filter) {
    $arguments += "--filter-description", $Filter
}
if ($NoCache) {
    $arguments += "--no-cache"
}

Write-Host "Esecuzione: $($promptfooCmd) $($arguments -join ' ')" -ForegroundColor Cyan

# Esegui
try {
    if ($promptfooCmd -eq $localPromptfoo) {
        & $localPromptfoo $arguments[2..($arguments.Length-1)]
    } else {
        & $promptfooCmd $arguments
    }
} catch {
    Write-Host "Errore: $_" -ForegroundColor Red
    Write-Host "Suggerimento: la prima volta potrebbe richiedere installazione" -ForegroundColor Yellow
}

Write-Host "Test completato!" -ForegroundColor Green
