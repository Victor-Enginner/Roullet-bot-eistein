from datetime import datetime
from dataclasses import dataclass
from typing import Optional

@dataclass
class DailyStats:
    wins: int = 0
    losses: int = 0
    current_streak: int = 0
    max_streak: int = 0
    last_report_date: Optional[str] = None
    
    # Horário de envio (HH:MM)
    REPORT_TIME: str = "23:59"

    def register_win(self):
        self.wins += 1
        self.current_streak += 1
        if self.current_streak > self.max_streak:
            self.max_streak = self.current_streak

    def register_loss(self):
        self.losses += 1
        self.current_streak = 0
        
    def get_report_text(self) -> str:
        total = self.wins + self.losses
        percentual = (self.wins / total * 100) if total > 0 else 0.0
        date_str = datetime.now().strftime("%d/%m/%Y")
        
        return (
            f"🟡 PLACAR DO DIA - {date_str} 🟡\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📊 RESULTADO GERAL\n\n"
            f"   🟢 {self.wins} Wins   |   🔴 {self.losses} Losses\n\n"
            f"   🎯 Taxa de acerto: {percentual:.1f}%\n"
            f"   🔥 Maior sequência: {self.max_streak} wins\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "💬 Dia excelente!\n"
            "🌙 Até amanhã!"
        )
        
    def should_send_report(self) -> bool:
        """
        Verifica se deve enviar o relatório.
        Retorna True se:
        1. A hora atual corresponde ao REPORT_TIME (minuto exato)
        2. Ainda não foi enviado hoje
        """
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        current_date = now.strftime("%Y-%m-%d")
        
        if current_time == self.REPORT_TIME:
            if self.last_report_date != current_date:
                return True
                
        return False
        
    def mark_reported(self):
        """Marca o dia de hoje como reportado e reseta contadores para o próximo ciclo"""
        self.last_report_date = datetime.now().strftime("%Y-%m-%d")
        self.reset()
        
    def reset(self):
        self.wins = 0
        self.losses = 0
        self.current_streak = 0
        self.max_streak = 0
