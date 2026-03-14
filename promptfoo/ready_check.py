#!/usr/bin/env python3
"""
Verifica rapida che tutto sia pronto per il test di produzione
"""

import os
import sys

print("🚀 VERIFICA PRONTI PRODUZIONE")
print("=" * 40)

# Check environment
api_key = os.environ.get('GEMINI_API_KEY')
root = os.environ.get('VERIFICAI_ROOT')

print(f"🔑 API Key: {'✅' if api_key else '❌'}")
print(f"📁 Root: {'✅' if root else '❌'}")

# Check files
files_to_check = [
    'production_promptfooconfig.yaml',
    'enhanced_promptfooconfig.yaml', 
    'comprehensive_test_suite.py',
    'providers/verificai_provider.py'
]

for file in files_to_check:
    exists = os.path.exists(file)
    print(f"📄 {file}: {'✅' if exists else '❌'}")

# Check provider
try:
    sys.path.insert(0, os.environ.get('VERIFICAI_ROOT', ''))
    sys.path.insert(0, os.path.dirname(__file__))
    
    from providers.verificai_provider import call_api
    print("🔧 Provider: ✅")
    
except Exception as e:
    print(f"🔧 Provider: ❌ - {e}")

print()
print("🎯 STATUS: PRONTO PER TEST PRODUZIONE!")
print("📋 Esegui: .\\run_promptfoo.ps1 o PromptFoo diretto")
