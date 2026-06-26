from datetime import datetime
from typing import Dict, Optional

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
    
    return (
        "🍀Entrada Confirmada🍀\n"
        f"🕒 {time_now}\n"
        f"📍 Número base: {numero}\n\n"
        f"🎯 Entrada:\n{entrada}\n\n"
        f"🛡️ Proteção:\n{cobertura}\n\n"
        f"🧠 Leitura: {leitura}\n\n"
        "⏱️ Gestão:\nAté 3 proteções.\nSem insistência."
    )
    
def format_legacy_message(numero: int, dados: Dict) -> str:
    """
    Formato antigo para compatibilidade com gerar_mensagem_por_numero
    """
    return (
        "✅ LEITURA CONFIRMADA\n\n"
        f"📍 Número base: {numero}\n"
        f"🧠 Leitura: {dados['leitura']}\n\n"
        f"🎯 Entrada:\n{dados['entrada']}\n\n"
        f"🛡️ Proteção:\n{dados['cobertura']}\n\n"
        "⏱️ Gestão:\n"
        "Até 3 proteções.\n"
        "Sem insistência."
    )
