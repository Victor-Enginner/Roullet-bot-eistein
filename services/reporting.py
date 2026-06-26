from datetime import datetime, timedelta
from typing import List, Tuple, Dict
from storage.database import Database

class ReportingSystem:
    """
    Sistema de agregação de dados e geração de relatórios.
    Foca em funções puras para cálculo e formatação rigorosa.
    """
    
    def __init__(self, db: Database):
        self.db = db

    def get_daily_report(self) -> str:
        """Gera o relatório do dia atual."""
        today = datetime.now().strftime("%Y-%m-%d")
        return self._generate_period_report(today, today, f"PLACAR DO DIA - {datetime.now().strftime('%d/%m/%Y')}")

    def get_weekly_report(self, clean: bool = True) -> str:
        """Gera o relatório da semana atual (ISO week)."""
        now = datetime.now()
        start_of_week = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")
        end_of_week = now.strftime("%Y-%m-%d")
        return self._generate_period_report(start_of_week, end_of_week, "RESUMO SEMANAL", clean=clean)

    def get_monthly_report(self, clean: bool = True) -> str:
        """Gera o relatório do mês atual."""
        now = datetime.now()
        start_of_month = now.replace(day=1).strftime("%Y-%m-%d")
        end_of_month = now.strftime("%Y-%m-%d")
        return self._generate_period_report(start_of_month, end_of_month, f"RESUMO MENSAL - {now.strftime('%m/%Y')}", clean=clean)

    def _generate_period_report(self, start_date: str, end_date: str, title: str, clean: bool = False) -> str:
        """Função mestre para consolidação de dados por período."""
        raw_results = self.db.get_results_by_period(start_date, end_date)
        
        if not raw_results:
            return f"🔴 {title} 🔴\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\nNenhum dado registrado no período."

        wins = 0
        losses = 0
        current_streak = 0
        max_streak = 0
        strategy_stats: Dict[str, Dict[str, int]] = {}

        for event_type, strategy_name, _, _ in raw_results:
            # 1. Contagem Geral
            if event_type in ['WIN_ENTRY', 'WIN_PROTECTION']:
                wins += 1
                current_streak += 1
                if current_streak > max_streak:
                    max_streak = current_streak
            else:
                losses += 1
                current_streak = 0

            # 2. Breakdown por Estratégia
            if not clean:
                if strategy_name not in strategy_stats:
                    strategy_stats[strategy_name] = {'w': 0, 'l': 0}
                
                if event_type in ['WIN_ENTRY', 'WIN_PROTECTION']:
                    strategy_stats[strategy_name]['w'] += 1
                else:
                    strategy_stats[strategy_name]['l'] += 1

        total = wins + losses
        accuracy = (wins / total * 100) if total > 0 else 0
        
        # 3. Comentário Neutro
        comment = self._get_neutral_comment(accuracy, total)

        # 4. Formatação do Template Telegram
        lines = [
            f"🔴 {title} 🔴",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "📊 RESULTADO GERAL",
            f"🟢 {wins} Wins | 🔴 {losses} Losses",
            f"🎯 Taxa de acerto: {accuracy:.1f}%",
            f"🔥 Maior sequência: {max_streak} greens",
        ]

        if not clean:
            lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            lines.append("📈 DESEMPENHO POR ESTRATÉGIA")
            # Ordena estratégias por volume
            sorted_strategies = sorted(strategy_stats.items(), key=lambda x: (x[1]['w'] + x[1]['l']), reverse=True)
            
            for name, stats in sorted_strategies:
                s_total = stats['w'] + stats['l']
                s_acc = (stats['w'] / s_total * 100) if s_total > 0 else 0
                lines.append(f"{name}")
                lines.append(f"  {stats['w']}W / {stats['l']}L • {s_acc:.1f}%")

        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append(f"💬 {comment}")
        lines.append("🌙 Até amanhã!")

        return "\n".join(lines)

    def _get_neutral_comment(self, accuracy: float, total: int) -> str:
        """Gera comentário neutro baseado na performance real."""
        if total < 5:
            return "Amostragem reduzida"
        
        if accuracy >= 90:
            return "Alta estabilidade"
        elif accuracy >= 80:
            return "Dia consistente"
        elif accuracy >= 65:
            return "Dia volátil"
        else:
            return "Baixa assertividade"
