import time
from dataclasses import dataclass
from datetime import datetime
from utils.logger import setup_logger

logger = setup_logger('metrics')

@dataclass
class Metrics:
    """Métricas de performance do bot"""
    start_time: float
    numbers_detected: int = 0
    errors_count: int = 0
    last_number_time: float = 0
    page_recoveries: int = 0
    telegram_failures: int = 0
    green_count: int = 0
    red_count: int = 0
    
    def uptime_seconds(self) -> float:
        """Retorna tempo de execução em segundos"""
        return time.time() - self.start_time
    
    def uptime_formatted(self) -> str:
        """Retorna tempo de execução formatado"""
        seconds = int(self.uptime_seconds())
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours:02d}h:{minutes:02d}m:{secs:02d}s"
    
    def time_since_last_number(self) -> float:
        """Segundos desde o último número detectado"""
        if self.last_number_time == 0:
            return 0
        return time.time() - self.last_number_time
    
    def report(self) -> str:
        """Gera relatório completo"""
        return f"""
╔══════════════════════════════════════╗
║     MÉTRICAS DO BOT - RELATÓRIO      ║
╠══════════════════════════════════════╣
║ Uptime:              {self.uptime_formatted():16s} ║
║ Números detectados:  {self.numbers_detected:16d} ║
║ Erros totais:        {self.errors_count:16d} ║
║ Recuperações:        {self.page_recoveries:16d} ║
║ Falhas Telegram:     {self.telegram_failures:16d} ║
║ Último número há:    {int(self.time_since_last_number()):13d}s ║
╚══════════════════════════════════════╝
"""
    
    def log_report(self):
        """Imprime e loga o relatório"""
        report = self.report()
        print(report)
        logger.info(f"Métricas - Uptime: {self.uptime_formatted()}, Números: {self.numbers_detected}, Erros: {self.errors_count}")


class HealthMonitor:
    """Monitor de saúde do sistema"""
    
    ALERT_THRESHOLD_NO_NUMBER = 300
    ALERT_THRESHOLD_ERRORS = 50
    
    def __init__(self, metrics: Metrics):
        self.metrics = metrics
        self.alerts_sent = 0
        self.last_alert_time = 0
        
    def check_health(self) -> tuple[bool, str]:
        """
        Retorna (is_healthy, reason)
        """
        if self.metrics.time_since_last_number() > self.ALERT_THRESHOLD_NO_NUMBER:
            return False, f"Nenhum número detectado há {int(self.metrics.time_since_last_number())}s"
        
        if self.metrics.errors_count > self.ALERT_THRESHOLD_ERRORS:
            return False, f"Muitos erros: {self.metrics.errors_count}"
        
        return True, "Sistema saudável"
    
    def alert_if_needed(self):
        """Envia alerta se necessário (evita spam)"""
        is_healthy, reason = self.check_health()
        
        if not is_healthy:
            if time.time() - self.last_alert_time > 120:
                logger.warning(f"⚠️ ALERTA DE SAÚDE: {reason}")
                self.alerts_sent += 1
                self.last_alert_time = time.time()
                return True
        
        return False
