import queue
import threading
import time

import requests

from utils.logger import setup_logger
from services.telegram_events import get_sticker_id, is_sticker_enabled

logger = setup_logger('telegram')

# Sentinela para encerrar o worker
_STOP = object()


class TelegramBot:
    """
    Cliente Telegram NÃO-BLOQUEANTE.

    OTIMIZAÇÃO DE LATÊNCIA (gargalo #1 do hot path):
    Antes, enviar()/enviar_imediato() faziam requests.post() SÍNCRONO dentro
    do loop principal (timeout de 5-10s). Cada número detectado podia travar
    o pipeline por segundos esperando o round-trip da API do Telegram.

    Agora os envios apenas ENFILEIRAM a mensagem (operação O(1), microssegundos)
    e um worker dedicado em background drena a fila e faz o POST. O loop
    principal nunca mais bloqueia em rede do Telegram.

    A API pública (enviar, enviar_imediato, enviar_evento, enviar_sticker,
    start_listener) foi mantida idêntica para não quebrar os callers.
    Para envios que PRECISAM ser garantidos antes de sair (ex.: relatório de
    encerramento), use enviar_blocking() ou chame flush() antes do exit.
    """

    def __init__(self, token, chat_id):
        self.token = token
        self.chat_id = chat_id
        self.session = requests.Session()  # Keep-Alive p/ reduzir latência por envio

        self._q: "queue.Queue" = queue.Queue(maxsize=1000)
        self._worker = threading.Thread(target=self._drain_loop, daemon=True)
        self._worker.start()

        logger.info(f"TelegramBot (async) inicializado para chat_id: {chat_id}")

    # ------------------------------------------------------------------ #
    # API pública (não-bloqueante)
    # ------------------------------------------------------------------ #
    def enviar(self, msg) -> bool:
        """Enfileira mensagem NORMAL. Retorna imediatamente."""
        return self._enqueue(("message", msg, 10))

    def enviar_imediato(self, msg) -> bool:
        """Enfileira mensagem CRÍTICA. Retorna imediatamente."""
        return self._enqueue(("message", msg, 5))

    def enviar_evento(self, event_key, msg, imediato=False) -> bool:
        """Enfileira a mensagem e, se configurado, o sticker vinculado."""
        self._enqueue(("message", msg, 5 if imediato else 10))
        sticker_id = get_sticker_id(event_key)
        if sticker_id and is_sticker_enabled():
            self._enqueue(("sticker", sticker_id, 10))
        return True

    def enviar_sticker(self, sticker_id) -> bool:
        """Enfileira um sticker. Retorna imediatamente."""
        return self._enqueue(("sticker", sticker_id, 10))

    def enviar_blocking(self, msg, timeout=10) -> bool:
        """
        Envio SÍNCRONO (bloqueante). Use apenas fora do hot path —
        ex.: relatório de encerramento, onde precisamos do envio garantido.
        """
        return self._send_message(msg, timeout)

    # ------------------------------------------------------------------ #
    # Fila / worker
    # ------------------------------------------------------------------ #
    def _enqueue(self, item) -> bool:
        try:
            self._q.put_nowait(item)
            return True
        except queue.Full:
            # Em sobrecarga extrema, descarta o mais antigo p/ não bloquear o bot
            try:
                self._q.get_nowait()
                self._q.put_nowait(item)
            except Exception:
                pass
            logger.warning("Fila do Telegram cheia — mensagem antiga descartada.")
            return False

    def _drain_loop(self):
        while True:
            item = self._q.get()
            if item is _STOP:
                self._q.task_done()
                return
            try:
                kind, payload, timeout = item
                if kind == "message":
                    self._send_message(payload, timeout)
                elif kind == "sticker":
                    self._send_sticker(payload, timeout)
            except Exception as e:
                logger.error(f"Erro no worker do Telegram: {e}")
            finally:
                self._q.task_done()

    def flush(self, timeout: float = 8.0) -> None:
        """Espera a fila esvaziar (use antes de encerrar o processo)."""
        deadline = time.time() + timeout
        while not self._q.empty() and time.time() < deadline:
            time.sleep(0.05)

    # ------------------------------------------------------------------ #
    # I/O real (roda só no worker / em enviar_blocking)
    # ------------------------------------------------------------------ #
    def _send_message(self, msg, timeout) -> bool:
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        data = {"chat_id": self.chat_id, "text": msg, "parse_mode": "HTML"}
        try:
            response = self.session.post(url, data=data, timeout=timeout)
            if response.status_code == 200:
                return True
            logger.warning(f"Telegram código {response.status_code}: {response.text}")
            return False
        except requests.Timeout:
            logger.error(f"Timeout ao enviar mensagem (>{timeout}s)")
            return False
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem: {e}")
            return False

    # Mantido por compatibilidade (alguns módulos podem chamar _send_internal)
    def _send_internal(self, msg, timeout) -> bool:
        return self._send_message(msg, timeout)

    def _send_sticker(self, sticker_id, timeout=10) -> bool:
        url = f"https://api.telegram.org/bot{self.token}/sendSticker"
        data = {"chat_id": self.chat_id, "sticker": sticker_id}
        try:
            response = self.session.post(url, data=data, timeout=timeout)
            if response.status_code == 200:
                return True
            logger.warning(f"Telegram código {response.status_code} (sticker): {response.text}")
            return False
        except Exception as e:
            logger.error(f"Erro ao enviar sticker: {e}")
            return False

    # ------------------------------------------------------------------ #
    # Listener de comandos (inalterado)
    # ------------------------------------------------------------------ #
    def start_listener(self, reporting_system):
        """Inicia listener em segundo plano para comandos"""
        self.reporting = reporting_system
        self.last_update_id = 0

        try:
            resp = self.session.get(
                f"https://api.telegram.org/bot{self.token}/getUpdates", timeout=5
            ).json()
            if resp.get("ok") and resp.get("result"):
                self.last_update_id = resp["result"][-1]["update_id"]
        except Exception:
            pass

        self.listener_thread = threading.Thread(target=self._listener_loop, daemon=True)
        self.listener_thread.start()
        logger.info("Listener de comandos Telegram iniciado.")

    def _listener_loop(self):
        while True:
            try:
                url = f"https://api.telegram.org/bot{self.token}/getUpdates"
                params = {"offset": self.last_update_id + 1, "timeout": 30}
                response = self.session.get(url, params=params, timeout=35)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("ok"):
                        for update in data.get("result", []):
                            self.last_update_id = update["update_id"]
                            self._handle_update(update)
            except Exception as e:
                logger.error(f"Erro no listener Telegram: {e}")
                time.sleep(10)
            time.sleep(1)

    def _handle_update(self, update):
        if "message" not in update:
            return
        msg = update["message"]
        chat_info = msg.get("chat", {})
        chat_id = str(chat_info.get("id"))
        text = msg.get("text", "")
        username = msg.get("from", {}).get("username", "unknown")

        logger.info(f"📩 Mensagem recebida de {username} (Chat: {chat_id}): {text}")

        if chat_id != str(self.chat_id):
            logger.debug(f"⚠️ Chat ID {chat_id} não autorizado (Esperado: {self.chat_id})")
            return

        cmd = text.split('@')[0].lower()
        if cmd == "/semanal":
            report = self.reporting.get_weekly_report(clean=True)
            self.enviar(report)
        elif cmd == "/mensal":
            report = self.reporting.get_monthly_report(clean=True)
            self.enviar(report)
        elif cmd == "/vies":
            # Caça-viés: qui-quadrado + persistência em todo o histórico.
            try:
                from analytics.vies_hunter import analisar_vies
                self.enviar(analisar_vies())
            except Exception as e:
                logger.error(f"Erro no /vies: {e}")
                self.enviar("🔬 Caça-viés falhou ao rodar. Veja o log.")
        elif cmd == "/quentes":
            # Números quentes: frequência na janela recente de giros salvos no banco.
            try:
                from analytics.hot_numbers import get_hot_numbers
                top, sample_size = get_hot_numbers()
                if sample_size == 0:
                    self.enviar("🔥 Números quentes: ainda não há giros salvos no banco.")
                else:
                    lista = ", ".join(f"{numero}({contagem}x)" for numero, contagem in top)
                    self.enviar(
                        f"🔥 Números quentes (últimos {sample_size} giros salvos): {lista}"
                    )
            except Exception as e:
                logger.error(f"Erro no /quentes: {e}")
                self.enviar("🔥 Números quentes falhou ao rodar. Veja o log.")
