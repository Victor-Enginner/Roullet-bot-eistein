"""
Diagnóstico automático do monitor.
Verifica todos os componentes sem precisar de interação manual.
"""

import sys
import os
import json
import time
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def section(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def check(label, ok, detail=""):
    icon = "[OK]" if ok else "[FALHOU]"
    print(f"  {icon} {label}")
    if detail:
        print(f"         {detail}")

# 1. Verifica import do monitor
section("1. IMPORT DO MONITOR")
try:
    from core.monitor import GameMonitor
    check("Import do GameMonitor", True, f"Classe: {GameMonitor}")
except Exception as e:
    check("Import do GameMonitor", False, str(e))
    sys.exit(1)

# 2. Verifica configurações
section("2. CONFIGURACOES")
try:
    from config.settings import Settings
    check("Settings carregadas", True)
    check("DB_PATH existe?", os.path.exists(str(Settings.DB_PATH)), str(Settings.DB_PATH))
    check("BROWSER_PROFILE_DIR existe?", os.path.exists(str(Settings.BROWSER_PROFILE_DIR)), str(Settings.BROWSER_PROFILE_DIR))
    check("FORBIDDEN_NUMBERS", True, str(Settings.FORBIDDEN_NUMBERS))
except Exception as e:
    check("Settings", False, str(e))

# 3. Verifica ESTRATEGIAS
section("3. ESTRATEGIAS")
try:
    from strategy.presets.default_terminals import ESTRATEGIAS
    from estrategias import BLACKLIST
    check("Total de estrategias", len(ESTRATEGIAS) == 37, f"{len(ESTRATEGIAS)}/37")
    check("BLACKLIST", True, str(BLACKLIST))

    # Verifica numeros reativados
    reativados = [0, 5, 8, 10]
    for n in reativados:
        if n in BLACKLIST:
            check(f"  Numero {n} removido da BLACKLIST", False, f"Ainda esta em {BLACKLIST}")
        else:
            check(f"  Numero {n} removido da BLACKLIST", True)

    reativados_forbidden = [0, 5, 8, 10]
    for n in reativados_forbidden:
        if n in Settings.FORBIDDEN_NUMBERS:
            check(f"  Numero {n} removido do FORBIDDEN", False)
        else:
            check(f"  Numero {n} removido do FORBIDDEN", True)
except Exception as e:
    check("Estrategias", False, str(e))

# 4. Verifica Engine + IA
section("4. ENGINE COM IA")
try:
    from server.services.engine import run_engine, AI_ENABLED
    check("Engine importado", True)
    check("IA habilitada no codigo?", AI_ENABLED, "Flag AI_ENABLED")
except Exception as e:
    check("Engine", False, str(e))

# 5. Verifica biblioteca ollama
section("5. BIBLIOTECA OLLAMA PYTHON")
try:
    import ollama
    check("Biblioteca 'ollama' instalada", True, f"Modulo: {ollama}")
except ImportError:
    check("Biblioteca 'ollama' instalada", False, "Rode: pip install ollama")

# 6. Verifica servidor Ollama
section("6. SERVIDOR OLLAMA")
try:
    import requests
    r = requests.get("http://127.0.0.1:11434/api/tags", timeout=5)
    if r.status_code == 200:
        data = r.json()
        models = [m["name"] for m in data.get("models", [])]
        check("Ollama respondendo", True, f"Status 200, modelos: {models}")
        check("llama3.1:8b disponivel", "llama3.1:8b" in models)
    else:
        check("Ollama respondendo", False, f"Status {r.status_code}")
except Exception as e:
    check("Ollama rodando?", False, f"Erro: {e}")
    print("\n  >>> Se Ollama nao esta rodando, abra outro terminal e execute: ollama serve")

# 7. Testa o agente de IA
section("7. TESTE DO AGENTE IA")
try:
    from ai.ollama_agent import OllamaAnalyst
    analyst = OllamaAnalyst(timeout=15.0)
    available = analyst.is_available()
    check("OllamaAnalyst disponivel", available)

    if available:
        print("\n  >>> Testando consulta real (pode levar 5-10s na primeira vez)...")
        resp = analyst.analyze(
            history=[23, 7, 0, 12, 35, 23, 14, 2, 31, 0, 18, 29, 7, 28, 32, 15, 3, 24, 36, 11],
            base=23,
            strategy=ESTRATEGIAS[23],
            stats={"directGreen": 5, "protectionGreen": 2, "loss": 3},
            analysis={
                "hot_numbers": [(23, 5), (7, 4), (0, 4), (2, 3)],
                "cold_numbers": [(15, 0), (16, 0)],
                "terminal_dominance": {0: 4, 3: 6, 7: 4},
                "frequency": {},
            },
            current_number=23,
        )
        if resp:
            check("IA respondeu", True, f"should_enter={resp.should_enter}, confidence={resp.confidence}%, risk={resp.risk_level}")
            print(f"         Razao: {resp.reasoning}")
        else:
            check("IA respondeu", False, "Retornou None (erro ou timeout)")
except Exception as e:
    check("Agente IA", False, str(e))

# 8. Verifica logs recentes
section("8. LOGS RECENTES")
log_dir = "logs"
if os.path.exists(log_dir):
    logs = sorted([f for f in os.listdir(log_dir) if f.startswith("debug_after_manual_enter")], reverse=True)
    if logs:
        latest = logs[0]
        check(f"Ultimo log de debug", True, latest)
        try:
            with open(os.path.join(log_dir, latest), "r", encoding="utf-8") as f:
                data = json.load(f)
            # Mostra informacoes uteis
            if "url" in data:
                check("  URL da pagina", True, str(data.get("url"))[:100])
            if "title" in data:
                check("  Titulo", True, str(data.get("title"))[:100])
            if "seletores_encontrados" in data:
                check("  Seletores encontrados", True, str(data.get("seletores_encontrados")))
        except Exception as e:
            print(f"  Erro ao ler log: {e}")
    else:
        check("Logs de debug", False, "Nenhum encontrado")

# 9. Verifica processos Chrome
section("9. PROCESSOS CHROME")
try:
    import subprocess
    result = subprocess.run(["tasklist", "/FI", "IMAGENAME eq chrome.exe"], capture_output=True, text=True, timeout=5)
    if "chrome.exe" in result.stdout:
        lines = [l for l in result.stdout.split("\n") if "chrome.exe" in l]
        check(f"Chrome rodando", True, f"{len(lines)} processos")
    else:
        check("Chrome rodando", False, "Nenhum processo")
except Exception as e:
    check("Verificar Chrome", False, str(e))

print("\n" + "=" * 70)
print("  DIAGNOSTICO CONCLUIDO")
print("=" * 70)
