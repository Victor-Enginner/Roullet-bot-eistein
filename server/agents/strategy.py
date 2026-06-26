import importlib
import os
import sys

# Variável em memória para rastrear o preset de estratégias ativo
ACTIVE_PRESET = "default_terminals"

def select_strategy_menu():
    """
    Exibe um menu de seleção interativo no terminal na inicialização do bot.
    """
    global ACTIVE_PRESET
    print("\n" + "=" * 60)
    print("🧠 EINSTEIN AI ROULETTE - SELETOR DE ESTRATÉGIA")
    print("=" * 60)
    print(" Selecione o preset de estratégias que deseja rodar:")
    print(" [1] Terminais Clássicos (Original - 100% Estável)")
    print(" [2] Super Assertiva (Nova Estratégia Personalizável)")
    print("=" * 60)
    
    try:
        # Pergunta ao usuário
        choice = input(" Digite o número (1 ou 2) e aperte ENTER [Padrão: 1]: ").strip()
        if not choice or choice == "1":
            ACTIVE_PRESET = "default_terminals"
        elif choice == "2":
            ACTIVE_PRESET = "super_assertiva"
        else:
            print(" ⚠️ Opção inválida. Usando preset padrão: Terminais Clássicos.")
            ACTIVE_PRESET = "default_terminals"
    except (EOFError, KeyboardInterrupt):
        # Fallback seguro para ambientes automatizados, testes ou interrupções
        ACTIVE_PRESET = "default_terminals"
        
    print(f"✅ ESTRATÉGIA ATIVA: {ACTIVE_PRESET.upper()}\n")

def get_active_strategy_preset() -> dict:
    """
    Importa dinamicamente a tabela de estratégias com base no preset ativo.
    """
    global ACTIVE_PRESET
    try:
        module = importlib.import_module(f"strategy.presets.{ACTIVE_PRESET}")
        return getattr(module, "ESTRATEGIAS")
    except Exception as e:
        # Fallback definitivo para a clássica estável em caso de qualquer exceção
        from strategy.presets import default_terminals
        return default_terminals.ESTRATEGIAS

def pick_strategy(last_number: int, history: list[int] = None) -> dict:
    """
    Escolhe a estratégia baseada no último número a partir do preset ativo.
    Suporta resolução dinâmica de contexto/histórico se o preset selecionado for 'super_assertiva'.
    """
    global ACTIVE_PRESET
    if ACTIVE_PRESET == "super_assertiva":
        try:
            # Importa dinamicamente a lógica inteligente da super_assertiva
            module = importlib.import_module("strategy.presets.super_assertiva")
            if hasattr(module, "resolve_strategy"):
                return module.resolve_strategy(last_number, history)
        except Exception as e:
            import logging
            logging.getLogger("server.agents.strategy").warning(
                f"Erro ao computar resolve_strategy dinâmico: {e}"
            )
            
    estrategias_ativas = get_active_strategy_preset()
    return estrategias_ativas.get(last_number, {})
