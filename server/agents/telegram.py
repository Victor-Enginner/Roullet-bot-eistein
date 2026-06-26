def format_telegram_message(signal: dict) -> str:
    """
    Formata a mensagem para envio no Telegram.
    Inclui tag de IA quando o agente foi consultado.
    """
    base = signal["base"]
    strategy = signal["strategy"]

    entrada = strategy.get("entrada", "")
    cobertura = strategy.get("cobertura", "")
    protecao = cobertura.split("/")[0].strip() if "/" in cobertura else cobertura

    # Header normal
    header = "🚨 SINALZINHO GRATUITO 🚨\n🎰 ROLETA AO VIVO"

    # Bloco IA (se disponível)
    ai_block = ""
    if signal.get("ai_used") and signal.get("ai_decision"):
        risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(
            signal.get("risk_level", "medium"), "🟡"
        )
        ai_block = f"""

🧠 IA ({signal["ai_decision"].get("confidence", 0)}% • risco {risk_emoji}):
{signal["ai_decision"].get("reasoning", "")}"""

    kelly_stake = signal.get("kelly_stake", 1.0)
    dealer = signal.get("dealer", "Default")
    gestao = f"\n\n💰 Gestão Sugerida: Ficha Base de {kelly_stake:.1f}% da Banca\n👤 Crupiê: {dealer}"

    return f"""
{header}

🎯 Base: {base}

📍 {entrada}

🛡 {protecao} (aparte){ai_block}

⏱ 3 proteções{gestao}
""".strip()
