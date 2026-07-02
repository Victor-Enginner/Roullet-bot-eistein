from datetime import datetime
from typing import Dict, Optional

from config.settings import Settings

# Teto prático de posições na ficha de aposta do cassino (~19-20). Usado
# apenas para EMITIR AVISO — não trunca a lista de números apostados.
MAX_BET_SLOTS = Settings.MAX_BET_SLOTS


def _bet_slots_warning(strategy_data: Dict) -> str:
    """
    Calcula o total de números ÚNICOS entre entrada+proteção e, se exceder
    MAX_BET_SLOTS, devolve uma linha de aviso pronta para concatenar na
    mensagem. Não trunca nem altera a cobertura — só avisa.
    """
    if not strategy_data:
        return ""

    entry_targets = strategy_data.get('entry')
    protection_targets = strategy_data.get('protection')

    # Fallback: quando só temos o dict 'raw' (strings), parseia sob demanda
    # para não exigir que todo chamador já tenha as listas prontas.
    if entry_targets is None or protection_targets is None:
        raw = strategy_data.get('raw', strategy_data)
        try:
            from .parser import parse_strategy_targets, parse_protection_targets
            if entry_targets is None:
                entry_targets = parse_strategy_targets(str(raw.get('entrada', '')))
            if protection_targets is None:
                protection_targets = parse_protection_targets(str(raw.get('cobertura', '')))
        except Exception:
            entry_targets = entry_targets or []
            protection_targets = protection_targets or []

    total_unicos = len(set(entry_targets or []) | set(protection_targets or []))

    if total_unicos > MAX_BET_SLOTS:
        return (
            f"\n\n⚠️ Sinal com {total_unicos} números — pode exceder o limite "
            f"da ficha do cassino (~{MAX_BET_SLOTS})."
        )
    return ""


def format_strategy_message(numero: int, strategy_data: Dict) -> str:
    """
    Gera a mensagem formatada para envio no Telegram.
    """
    if not strategy_data:
        return ""

    raw = strategy_data.get('raw', {})
    leitura = raw.get('leitura', 'N/A')
    entrada = raw.get('entrada', 'N/A')
    cobertura = raw.get('cobertura', 'N/A')

    time_now = datetime.now().strftime("%H:%M")

    aviso = _bet_slots_warning(strategy_data)

    return (
        "🍀Entrada Confirmada🍀\n"
        f"🕒 {time_now}\n"
        f"📍 Número base: {numero}\n\n"
        f"🎯 Entrada:\n{entrada}\n\n"
        f"🛡️ Proteção:\n{cobertura}\n\n"
        f"🧠 Leitura: {leitura}\n\n"
        "⏱️ Gestão:\nAté 3 proteções.\nSem insistência."
        f"{aviso}"
    )

def format_legacy_message(numero: int, dados: Dict) -> str:
    """
    Formato antigo para compatibilidade com gerar_mensagem_por_numero
    """
    aviso = _bet_slots_warning({'raw': dados})

    return (
        "✅ LEITURA CONFIRMADA\n\n"
        f"📍 Número base: {numero}\n"
        f"🧠 Leitura: {dados['leitura']}\n\n"
        f"🎯 Entrada:\n{dados['entrada']}\n\n"
        f"🛡️ Proteção:\n{dados['cobertura']}\n\n"
        "⏱️ Gestão:\n"
        "Até 3 proteções.\n"
        "Sem insistência."
        f"{aviso}"
    )
