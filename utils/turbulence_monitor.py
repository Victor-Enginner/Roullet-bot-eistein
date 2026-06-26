import time
from typing import Dict
from utils.logger import setup_logger

logger = setup_logger("turbulence")


class TurbulenceMonitor:
    """
    Monitor de Turbulência - Modelo PAUSA OPERACOES

    REGRA ABSOLUTA:
    - Detectar turbulência → Pausar sinais + Alertar
    - Retomar operações quando normalizar
    """

    def __init__(self, bot):
        self.bot = bot
        self.turbulence_active = False
        self.paused = False  # New: flag to pause signal sending
        self.last_alert_time = 0
        self.alert_cooldown = 300  # 5 minutos entre alertas idênticos

    def update(self, has_turbulence: bool, info: Dict) -> bool:
        """
        Atualiza estado de turbulência.
        Pausa operações durante turbulência e retoma quando normalizar.
        Retorna True se turbulência foi detectada.
        """
        if has_turbulence and not self.turbulence_active:
            # Turbulência iniciou: enviar alerta e pausar
            now = time.time()
            if now - self.last_alert_time > self.alert_cooldown:
                categories = info.get("categories", [])
                cat_str = "\n".join([f"• {c}" for c in categories])

                msg = (
                    "🚨 ALERTA DE RISCO - MERCADO TURBULENTO\n\n"
                    "⚠️ DETECÇÃO DE PADRÃO ATÍPICO\n"
                    "⚠️ Sequência ou desvio identificado!\n\n"
                    f"{cat_str}\n\n"
                    "📢 AVISO: Espere o momento de respiração!\n"
                    "Operações pausadas até normalização."
                )
                self.bot.enviar_evento("TURBULENCE", msg)
                self.last_alert_time = now
                self.turbulence_active = True
                self.paused = True
                logger.info(
                    f"🌪️ Turbulência detectada, operações pausadas: {categories}"
                )

        elif not has_turbulence and self.turbulence_active:
            # Turbulência acabou: enviar alerta de normalização e retomar
            msg = (
                "✅ NORMALIZAÇÃO DETECTADA\n\n"
                "🌤️ Mercado voltou ao padrão normal.\n"
                "Retomando operações."
            )
            self.bot.enviar_evento("NORMALIZED", msg)
            self.turbulence_active = False
            self.paused = False
            logger.info("🌤️ Turbulência normalizada, operações retomadas")

        return self.turbulence_active
