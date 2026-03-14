# Test manuale VerificAI PromptFoo - PowerShell
# ===========================================

Write-Host "🚀 Setup ambiente..." -ForegroundColor Green

# Environment variables
$env:GEMINI_API_KEY = "LA_MIA_CHIAVE"
$env:VERIFICAI_ROOT = "C:\Users\gobli\Desktop\verificai"

Write-Host "✅ Environment variables impostate" -ForegroundColor Yellow
Write-Host "📁 Directory: $(Get-Location)" -ForegroundColor Cyan

# Test del provider Python
Write-Host "🧪 Test provider Python..." -ForegroundColor Magenta
python test_provider.py

# Se PromptFoo è installato, lancia i test
$nodejs = "C:\Program Files\nodejs\node.exe"
if (Test-Path $nodejs) {
    Write-Host "🟢 Node.js trovato, lancio PromptFoo..." -ForegroundColor Green
    
    # Prova a eseguire PromptFoo
    try {
        & "C:\Program Files\nodejs\npx.cmd" promptfoo@latest eval --filter-description "Titolo"
    } catch {
        Write-Host "⚠️ Errore PromptFoo: $_" -ForegroundColor Red
        Write-Host "💡 Suggerimento: potresti dover attendere l'installazione completa" -ForegroundColor Yellow
    }
} else {
    Write-Host "❌ Node.js non trovato in $nodejs" -ForegroundColor Red
}

Write-Host "🏁 Test completato!" -ForegroundColor Green
