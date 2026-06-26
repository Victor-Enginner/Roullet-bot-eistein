import os
from typing import Dict, Optional
from storage.database import Database

class StrategyAnalytics:
    """
    Módulo de analytics para estratégias.
    Observa resultados e gera insights detalhados.
    """
    def __init__(self, db: Optional[Database] = None):
        self.db = db if db else Database()
        self.session_id: Optional[int] = None

    def set_session(self, session_id: int):
        self.session_id = session_id

    def register(self, strategy_id: int, result: str, strategy_name: str = "Strategy") -> Optional[str]:
        """
        Registra o desfecho e retorna a mensagem de analytics formatada.
        """
        if result not in ['WIN_ENTRY', 'WIN_PROTECTION', 'LOSS']:
            return None

        # Nome único da estratégia baseada no número
        full_name = f"{strategy_name} #{strategy_id}"

        # 1. Salva no banco de dados para persistência global
        self.db.save_result(result, full_name, self.session_id)
            
        # 2. Busca estatísticas históricas completas
        stats = self.db.get_strategy_stats(full_name)
        
        return self._format_analytics_message(strategy_id, stats)

    def _format_analytics_message(self, strategy_id: int, stats: dict) -> str:
        """Gera o box visual de analytics conforme solicitado"""
        total = stats['total']
        win_entry = stats['win_entry']
        win_protection = stats['win_protection']
        win_total = stats['win_total']
        losses = stats['losses']
        
        accuracy = (win_total / total * 100) if total > 0 else 0
        # Score ponderado: Volume + Assertividade
        confidence_score = accuracy * (min(total, 20) / 20)
        
        # Estrutura visual idêntica ao solicitado
        lines = [
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"📊 ANALYTICS | Strategy #{strategy_id}",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"🔹 Execuções: {total}",
            f"✅ Wins:      {win_total}",
            f"   • Primeira: {win_entry}",
            f"   • Proteção: {win_protection}",
            f"❌ Losses:     {losses}",
            "──────────────────────────────",
            f"📈 Taxa:       {accuracy:.1f}%",
            f"⭐️ Score:      {confidence_score:.1f}%",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ]
        
        return "\n".join(lines)

    def get_highest_probability_numbers(self, limit: int = 5) -> str:
        """
        Implementação futura: Analisa o DB para ver quais números 
        têm o melhor score histórico para sugerir entradas.
        """
        # Por enquanto mantendo estrutura para o usuário saber que estamos trabalhando nisso
        return "🔍 Análise de probabilidade em estruturação..."

# Instância Singleton exportada
analytics = StrategyAnalytics()
