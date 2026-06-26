import websocket
import json
import time
from datetime import datetime
import re

# ==============================================================================
# 🕵️ PLAYTECH WEBSOCKET ANALYZER
# ==============================================================================
# Ferramenta para identificar o protocolo da Roleta Brasileira (Playtech)
# ==============================================================================

# ⚠️ SUBSTITUA PELO URL DO WEBSOCKET DA ROLETA BRASILEIRA ⚠️
WS_URL = "wss://..."

def decode_message(message):
    """
    Tenta decodificar mensagens Playtech / Socket.IO
    Muitas vezes vêm no formato: '42["evento", payload]'
    """
    prefix = ""
    payload = message
    
    # 1. Padrão Socket.IO (números seguidos de JSON array)
    match = re.match(r'^(\d+)(.*)', message)
    if match:
        prefix = match.group(1)
        content = match.group(2)
        
        # Se for um array JSON
        if content.startswith('[') and content.endswith(']'):
            try:
                parsed = json.loads(content)
                return prefix, parsed
            except:
                pass
                
    # 2. JSON Puro
    try:
        parsed = json.loads(message)
        return "JSON", parsed
    except:
        pass
        
    return "RAW", message

def on_message(ws, message):
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    prefix, data = decode_message(message)
    
    # Filtro de interesse
    is_interesting = False
    str_dump = str(data)
    
    # Palavras-chave típicas de resultado em Playtech
    # "win", "result", "outcome", "history", "last"
    keywords = ["win", "won", "result", "outcome", "number", "score", "value"]
    
    if any(k in str_dump.lower() for k in keywords):
        is_interesting = True
        
    if is_interesting:
        print("\n" + "="*80)
        print(f"[{timestamp}] 🎯 MENSAGEM RELEVANTE DETECTADA ({prefix})")
        if isinstance(data, (dict, list)):
            print(json.dumps(data, indent=2))
        else:
            print(data)
        print("="*80)
    elif "ping" in str_dump or "pong" in str_dump or prefix == "2" or prefix == "3":
        # Keep-alive do Socket.IO (2=ping, 3=pong)
        print(f"[{timestamp}] 💓 Heartbeat ({prefix})")
    else:
        print(f"[{timestamp}] ℹ️  {str_dump[:150]}...")

def on_error(ws, error):
    print(f"❌ Erro: {error}")

def on_close(ws, close_status_code, close_msg):
    print("⚠️ Conexão fechada")

def on_open(ws):
    print("\n✅ CONECTADO AO WS PLAYTECH!")
    print("⏳ Aguardando mensagens... (Gire a roleta no site para testar)\n")

if __name__ == "__main__":
    print("🔬 ANALISADOR DE PROTOCOLO PLAYTECH")
    print(f"🔗 Alvo: {WS_URL}")
    print("👉 Copie o URL do DevTools (Network -> WS) e edite este arquivo.")
    
    ws = websocket.WebSocketApp(WS_URL,
                                on_open=on_open,
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close,
                                header={
                                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                                    "Origin": "https://geralbet.bet.br"
                                })
    ws.run_forever()
