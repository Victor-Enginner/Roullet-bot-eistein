import json
import threading
import time
import re
import websocket
from utils.logger import setup_logger

logger = setup_logger('playtech_ws')

class PlaytechMonitor:
    """
    Monitor WebSocket OTIMIZADO para Roletas Playtech.
    Suporta protocolo Socket.IO (frames 42[...]) e JSON puro.
    """
    
    # ⚠️ SUBSTITUA PELO URL CORRETO DO WEBSOCKET PLAYTECH ⚠️
    # Geralmente algo como: wss://live-casino.playtech.com/...
    WS_URL = "wss://SEU_URL_PLAYTECH_AQUI"
    
    def __init__(self):
        self.ws = None
        self.ws_thread = None
        self.running = False
        self.latest_number = None
        self.last_process_token = None # Pode ser ID do round ou timestamp
        self.lock = threading.Lock()

    def start(self):
        logger.info("Iniciando monitor WebSocket (Playtech)...")
        self.running = True
        self.ws_thread = threading.Thread(target=self._run_ws, daemon=True)
        self.ws_thread.start()

    def _run_ws(self):
        while self.running:
            try:
                self.ws = websocket.WebSocketApp(
                    self.WS_URL,
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close,
                    header={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
                        "Origin": "https://geralbet.bet.br"
                    }
                )
                self.ws.run_forever(ping_interval=25, ping_timeout=10)
            except Exception as e:
                logger.error(f"Erro thread WS Playtech: {e}")
                time.sleep(5)
            
            if self.running:
                logger.info("Reconectando WS Playtech em 5s...")
                time.sleep(5)

    def _on_open(self, ws):
        logger.info("✅ WS Playtech Conectado!")
        # Protocolo Socket.IO pede handshake as vezes (2probe)
        # ws.send("2probe") 

    def _decode_socket_io(self, message):
        """Extrai payload de mensagens Socket.IO '42[...]'"""
        match = re.match(r'^(\d+)(.*)', message)
        if match:
            # prefix = match.group(1) # ex: 42
            content = match.group(2)
            if content.startswith('[') and content.endswith(']'):
                try:
                    return json.loads(content)
                except:
                    pass
        return None

    def _on_message(self, ws, message):
        try:
            # Decodifica se for Socket.IO ou JSON puro
            data = None
            if message.startswith('{'):
                data = json.loads(message)
            else:
                data = self._decode_socket_io(message)
                
            if not data:
                return

            # --- LÓGICA DE EXTRAÇÃO (Customizável pelo Usuário) ---
            # Exemplo genérico de estrutura Playtech (Socket.IO array)
            # ["game-result", { "result": { "outcome": 32 } , "id": "..." }]
            
            event_name = ""
            payload = {}
            
            if isinstance(data, list) and len(data) >= 2:
                event_name = data[0]
                payload = data[1]
                
            elif isinstance(data, dict):
                event_name = data.get("type", "")
                payload = data
            
            # FILTRO DE EVENTO VÁLIDO (Adapte conforme o Analyzer)
            # Hipótese: Evento 'result' ou contendo 'wins'
            
            numero = None
            token = None
            
            # --- ZONA DE SUPOSIÇÃO DO PROTOCOLO (AJUSTE AQUI) ---
            if event_name == "game_result" or "result" in event_name:
                # Tenta achar número em campos comuns
                if "value" in payload: numero = payload["value"]
                elif "score" in payload: numero = payload["score"]
                elif "outcome" in payload: numero = payload["outcome"]
                elif "winner" in payload: numero = payload["winner"]
                
                # Token para anti-duplicação
                token = payload.get("id") or payload.get("roundId") or payload.get("timestamp")
            # ----------------------------------------------------
            
            if numero is not None:
                with self.lock:
                    # Verifica duplicação (por ID de round ou mudança de valor)
                    is_new = False
                    if token and token != self.last_process_token:
                        is_new = True
                    elif str(numero) != str(self.latest_number): # Falback se não tiver ID
                        is_new = True
                        
                    if is_new:
                        self.latest_number = str(numero)
                        self.last_process_token = token
                        logger.info(f"🎰 WS Playtech: Número capturado: {self.latest_number}")
                        
        except Exception as e:
            logger.error(f"Erro parser WS Playtech: {e}")

    def _on_error(self, ws, error):
        logger.error(f"❌ Erro WS: {error}")

    def _on_close(self, ws, code, msg):
        logger.warning("⚠️ WS Fechado")

    def watch(self) -> dict:
        with self.lock:
            return {
                "number": self.latest_number,
                "token": self.last_process_token
            }

    def stop(self):
        self.running = False
        if self.ws: self.ws.close()
