# Preset de Estratégias: Super Assertiva (Inteligente por Análise de Histórico)
# Este arquivo implementa o estudo de famílias de terminais, gêmeos e espelhos com verificação contextual.
import logging

logger = logging.getLogger("strategy.super_assertiva")

# Dicionário estático para compatibilidade retroativa e testes básicos
ESTRATEGIAS = {i: {} for i in range(37)}

def resolve_strategy(last_number: int, history: list[int] = None) -> dict:
    """
    Executa a estratégia baseada na análise de tendência de histórico
    e priorização de espelhos/gêmeos.
    """
    if not history:
        return {}

    # Certifica-se de que temos o histórico recente para analisar a tendência
    history_slice = history[-8:]
    if len(history_slice) < 3:
        return {}

    # --- 1. ESTRATÉGIA ESPELHOS & GÊMEOS (PRIORIDADE MÁXIMA) ---
    twins = {11, 22, 33}
    mirrors = {12, 21, 13, 31, 23, 32}
    
    # Se o último número for um espelho ou gêmeo, gera entrada imediata (prioridade)
    if last_number in twins or last_number in mirrors:
        logger.info(f"🔮 [Espelhos & Gêmeos] Gatilho confirmado no número base: {last_number}!")
        return {
            "leitura": "🚨 ESPELHOS & GÊMEOS ATIVOS: Mesa confirmou leitura de invertidos/gêmeos.",
            "entrada": "11, 12, 13, 21, 22, 23, 31, 32, 33",
            "cobertura": "3, 9, 36, 35, 27, 30, 8, 10, 4, 2, 26"
        }

    # --- 2. ESTRATÉGIA DE FAMÍLIAS DE TERMINAIS ---
    families = {
        "3_6_9": {
            "terminals": {3, 6, 9},
            "entrada": "3, 6, 9, 13, 16, 19, 23, 26, 29, 33, 36",
            "cobertura": "15, 32, 27, 18, 22, 8, 31, 35",
            "leitura": "🚨 FAMÍLIA 3-6-9 ATIVA: Mesa mostrando leitura forte em 3-6-9."
        },
        "2_5_8": {
            "terminals": {2, 5, 8},
            "entrada": "2, 5, 8, 12, 15, 18, 22, 25, 28, 32, 35",
            "cobertura": "7, 29, 26, 3, 23, 10, 21, 17",
            "leitura": "🚨 FAMÍLIA 2-5-8 ATIVA: Leitura confirma padrão 2-5-8."
        },
        "6_3_2": {
            "terminals": {6, 3, 2},
            "entrada": "6, 3, 2, 16, 13, 12, 26, 23, 22, 36, 33, 32",
            "cobertura": "11, 15, 21, 31, 35, 27, 9",
            "leitura": "🚨 FAMÍLIA 6-3-2 ATIVA: Leitura clara em terminais 6-3-2."
        },
        "0_5_7": {
            "terminals": {0, 5, 7},
            "entrada": "0, 5, 7, 10, 15, 17, 20, 25, 27, 30, 35",
            "cobertura": "26, 33, 28, 23, 12, 8, 11, 36, 13",
            "leitura": "🚨 FAMÍLIA 0-5-7 ATIVA: Mesa puxando terminais 0-5-7."
        }
    }

    last_terminal = last_number % 10
    matching_families = []

    # Identifica quais famílias se alinham com o último terminal sorteado
    for name, config in families.items():
        if last_terminal in config["terminals"]:
            # Conta a recorrência dessa família nos últimos 8 giros (tendência de histórico)
            hits = sum(1 for num in history_slice if (num % 10) in config["terminals"])
            matching_families.append((name, hits, config))

    if not matching_families:
        return {}

    # Escolhe a família com maior tendência no histórico
    matching_families.sort(key=lambda x: x[1], reverse=True)
    best_family, hits_count, best_config = matching_families[0]

    # Exige que a tendência esteja forte no histórico recente (>= 3 ocorrências nos últimos 8 giros)
    if hits_count >= 3:
        logger.info(f"🔥 [Famílias] Gatilho confirmado na família {best_family} ({hits_count} ocorrências no histórico)!")
        return {
            "leitura": best_config["leitura"],
            "entrada": best_config["entrada"],
            "cobertura": best_config["cobertura"]
        }

    # Se a mesa não estiver aderente à tendência recente, pula o sinal para segurança
    return {}
