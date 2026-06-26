import requests
import time
from utils.logger import setup_logger
from services.telegram_events import get_sticker_id, is_sticker_enabled

logger = setup_logger('telegram')

class TelegramBot:
    def __init__(self, token, chat_id):
        self.token = token
        self.chat_id = chat_id
        self.session = requests.Session() # Mantém conexão viva (Keep-Alive) para reduzir latência
        logger.info(f"TelegramBot inicializado para chat_id: {chat_id}")

    def enviar(self, msg) -> bool:
        """Envia mensagem NORMAL (prioridade padrão)"""
        return self._send_internal(msg, timeout=10)
        
    def enviar_imediato(self, msg) -> bool:
        """Envia mensagem CRÍTICA (alta prioridade, timeout curto)"""
        # Usa a mesma session, mas semanticamente indica prioridade
        return self._send_internal(msg, timeout=5)

    def enviar_evento(self, event_key, msg, imediato=False) -> bool:
        """Envia uma mensagem de evento e, se configurado, o sticker vinculado."""
        ok = self.enviar_imediato(msg) if imediato else self.enviar(msg)

        sticker_id = get_sticker_id(event_key)
        if ok and sticker_id and is_sticker_enabled():
            sticker_ok = self.enviar_sticker(sticker_id)
            if not sticker_ok:
                logger.warning(f"Sticker do evento {event_key} não foi enviado.")

        return ok

    def _send_internal(self, msg, timeout) -> bool:
        """Método interno de envio usando Session"""
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        data = {"chat_id": self.chat_id, "text": msg, "parse_mode": "HTML"}
        try:
            logger.debug(f"Enviando mensagem ao Telegram (timeout={timeout}s)...")
            response = self.session.post(url, data=data, timeout=timeout)
            
            if response.status_code == 200:
                logger.info("Mensagem enviada com sucesso")
                return True
            else:
                logger.warning(f"Telegram retornou código {response.status_code}: {response.text}")
                return False
        except requests.Timeout:
            logger.error(f"Timeout ao enviar mensagem (>{timeout}s)")
            return False
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem: {e}", exc_info=True)
            return False

    def enviar_sticker(self, sticker_id) -> bool:
        """Envia um sticker pelo ID"""
        url = f"https://api.telegram.org/bot{self.token}/sendSticker"
        data = {"chat_id": self.chat_id, "sticker": sticker_id}
        try:
            response = self.session.post(url, data=data, timeout=10)
            if response.status_code == 200:
                logger.info("Sticker enviado com sucesso")
                return True

            logger.warning(
                f"Telegram retornou código {response.status_code} ao enviar sticker: {response.text}"
            )
            return False
        except Exception as e:
            logger.error(f"Erro ao enviar sticker: {e}")
            return False

    def start_listener(self, reporting_system):
        """Inicia listener em segundo plano para comandos"""
        import threading
        self.reporting = reporting_system
        self.last_update_id = 0
        
        # Faz um primeiro check para limpar mensagens antigas
        try:
            resp = self.session.get(f"https://api.telegram.org/bot{self.token}/getUpdates", timeout=5).json()
            if resp.get("ok") and resp.get("result"):
                self.last_update_id = resp["result"][-1]["update_id"]
        except:
            pass

        self.listener_thread = threading.Thread(target=self._listener_loop, daemon=True)
        self.listener_thread.start()
        logger.info("Listener de comandos Telegram iniciado.")

    def _listener_loop(self):
        """Loop de polling para comandos"""
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
        """Processa uma atualização do Telegram"""
        if "message" not in update:
            return
            
        msg = update["message"]
        chat_info = msg.get("chat", {})
        chat_id = str(chat_info.get("id"))
        text = msg.get("text", "")
        username = msg.get("from", {}).get("username", "unknown")

        logger.info(f"📩 Mensagem recebida de {username} (Chat: {chat_id}): {text}")

        # Só responde se for o chat_id autorizado OU se for um chat_id que enviou um comando
        # Para facilitar, vamos permitir que ele responda no chat de onde veio a mensagem
        # se o comando for válido, mas vamos manter a restrição original se preferir.
        # No entanto, se o user_id for diferente do CHAT_ID do .env, ele vai ignorar.
        
        if chat_id != str(self.chat_id):
            logger.debug(f"⚠️ Chat ID {chat_id} não autorizado (Esperado: {self.chat_id})")
            return

        # Limpa o comando (trata /comando@bot_name)
        cmd = text.split('@')[0].lower()

        if cmd == "/semanal":
            logger.info(f"📊 Processando /semanal para chat {chat_id}")
            report = self.reporting.get_weekly_report(clean=True)
            self.enviar(report)
        elif cmd == "/mensal":
            logger.info(f"📊 Processando /mensal para chat {chat_id}")
            report = self.reporting.get_monthly_report(clean=True)
            self.enviar(report)
