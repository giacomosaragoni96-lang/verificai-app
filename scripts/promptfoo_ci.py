#!/usr/bin/env python3
"""
PromptFoo CI/CD Integration
Automazione per test automatici su modifiche a prompts.py
"""

import os
import sys
import subprocess
import json
import time
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def run_promptfoo_tests():
    """Esegue la suite completa di test PromptFoo"""
    print("🧪 Avvio test PromptFoo CI/CD...")
    
    # Change to promptfoo directory
    promptfoo_dir = project_root / "promptfoo"
    if not promptfoo_dir.exists():
        print("❌ Directory promptfoo non trovata")
        return False
    
    os.chdir(promptfoo_dir)
    
    try:
        # Run tests
        result = subprocess.run([
            "promptfoo", "eval", "-j", "1", "--no-cache"
        ], capture_output=True, text=True, timeout=300)
        
        print("📊 Output PromptFoo:")
        print(result.stdout)
        
        if result.stderr:
            print("⚠️ Warnings/Errori:")
            print(result.stderr)
        
        # Parse results
        success = result.returncode == 0
        
        # Try to extract metrics
        try:
            results_file = promptfoo_dir / "output" / "latest.json"
            if results_file.exists():
                with open(results_file, 'r') as f:
                    data = json.load(f)
                
                total_tests = len(data.get('results', []))
                passed_tests = sum(1 for r in data.get('results', []) if r.get('success'))
                failed_tests = total_tests - passed_tests
                
                print(f"📈 Risultati: {passed_tests}/{total_tests} passati")
                
                if failed_tests > 0:
                    print(f"❌ {failed_tests} test falliti:")
                    for result in data.get('results', []):
                        if not result.get('success'):
                            print(f"  - {result.get('description', 'Unknown')}")
                
                success = failed_tests == 0
            else:
                print("⚠️ Impossibile trovare risultati dettagliati")
                
        except Exception as e:
            print(f"⚠️ Errore parsing risultati: {e}")
        
        return success
        
    except subprocess.TimeoutExpired:
        print("❌ Timeout test PromptFoo")
        return False
    except FileNotFoundError:
        print("❌ PromptFoo non installato. Installa con: pip install promptfoo")
        return False
    except Exception as e:
        print(f"❌ Errore imprevisto: {e}")
        return False

def check_prompts_changed():
    """Verifica se prompts.py è stato modificato"""
    try:
        # Get git status for prompts.py
        result = subprocess.run([
            "git", "diff", "--name-only", "HEAD~1", "HEAD"
        ], capture_output=True, text=True, cwd=project_root)
        
        changed_files = result.stdout.strip().split('\n')
        return 'prompts.py' in changed_files
        
    except Exception:
        # Fallback: check if prompts.py exists and has recent modifications
        prompts_file = project_root / "prompts.py"
        if prompts_file.exists():
            # Check if modified in last hour
            mtime = prompts_file.stat().st_mtime
            return (time.time() - mtime) < 3600
        return False

def generate_ci_report(success: bool, test_results: dict = None):
    """Genera un report CI/CD"""
    timestamp = datetime.now().isoformat()
    
    report = {
        "timestamp": timestamp,
        "success": success,
        "trigger": "prompts.py modified",
        "results": test_results or {}
    }
    
    # Save report
    reports_dir = project_root / "promptfoo_ci_reports"
    reports_dir.mkdir(exist_ok=True)
    
    report_file = reports_dir / f"ci_report_{timestamp.replace(':', '-')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"📋 Report salvato: {report_file}")
    return report_file

def main():
    """Funzione principale CI/CD"""
    print("🚀 PromptFoo CI/CD Integration")
    print("=" * 50)
    
    # Check if prompts.py changed
    if not check_prompts_changed():
        print("ℹ️ prompts.py non modificato - skip test")
        return 0
    
    print("📝 prompts.py modificato - esecuzione test...")
    
    # Run tests
    success = run_promptfoo_tests()
    
    # Generate report
    report_file = generate_ci_report(success)
    
    if success:
        print("✅ Tutti i test passati - commit approvato!")
        return 0
    else:
        print("❌ Test falliti - commit bloccato!")
        print("🔧 Correggi i problemi e riprova")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
