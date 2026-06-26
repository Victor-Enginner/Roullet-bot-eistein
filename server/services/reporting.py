from server.agents.memory import MemoryAgent


def generate_weekly_report(memory_agent: MemoryAgent) -> str:
    """
    Gera relatório semanal baseado nas estatísticas.
    """
    wins = 0
    losses = 0
    best_streak = 0  # Placeholder, can implement later

    for stats in memory_agent.stats_db.values():
        wins += stats["directGreen"] + stats["protectionGreen"]
        losses += stats["loss"]

    accuracy = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0

    return f"""
🔴 RESUMO SEMANAL 🔴
━━━━━━━━━━━━━━━━━━━━

📊 RESULTADO GERAL
🟢 {wins} Wins | 🔴 {losses} Losses
🎯 Taxa de acerto: {accuracy:.1f}%

━━━━━━━━━━━━━━━━━━━━
💬 Alta estabilidade
""".strip()
