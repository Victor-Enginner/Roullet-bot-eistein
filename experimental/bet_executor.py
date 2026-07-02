# ⚠️⚠️⚠️ AVISO CRÍTICO - NÃO EXECUTAR EM PRODUÇÃO ⚠️⚠️⚠️
# Esta classe realiza cliques programáticos de aposta com dinheiro real.
# As coordenadas de clique estão INCOMPLETAS (só 6 de 37 números mapeados).
# Pode causar perda financeira se executado acidentalmente.
# Use apenas em ambiente de teste/sandbox com coordenadas completas.
# Movido para experimental/ em 2026-07-01 via SPRINT 0.
# ⚠️⚠️⚠️

from playwright.sync_api import Page


class BetExecutor:
    """Execução de apostas via clique coordenado em tela."""

    def __init__(self, page: Page):
        self.page = page

        self.number_map = {
            # Exemplo de coordenadas (ajustar para o layout da mesa em uso)
            0: (500, 800),
            1: (580, 760),
            2: (640, 760),
            3: (700, 760),
            4: (760, 760),
            5: (820, 760),
            # ... mapeie sua mesa completa conforme necessário ...
        }

    def click_bet(self, number: int, amount: float = 1.0):
        if number not in self.number_map:
            raise ValueError(f"Número {number} não mapeado para clique.")

        x, y = self.number_map[number]

        # Clicar no número escolhido
        self.page.mouse.click(x, y, delay=10)

        # Definir valor da aposta no campo de entrada do UI
        # JSON do `amount` pode variar de site para site
        try:
            # Exemplo de seletor comum; ajuste conforme o site
            self.page.fill("input[data-test='bet-input']", str(amount))
        except Exception:
            pass

        # Confirmação do valor e envio
        try:
            self.page.click("button[data-test='place-bet']", timeout=3000)
        except Exception:
            pass

        return True
