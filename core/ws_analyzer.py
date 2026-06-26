import websocket
import json
import time
import threading
from datetime import datetime

# ==============================================================================
# 🕵️ PRAGMATIC PLAY WEBSOCKET ANALYZER
# ==============================================================================
# Este script NÃO é o bot. É uma ferramenta de ENGENHARIA REVERSA.
# Ele conecta, escuta e "bonifica" o log para encontrarmos o padrão exato.
# ==============================================================================

# ⚠️ OBTER URL ATUALIZADO NO DEVTOOLS (Aba Network -> WS) ⚠️
WS_URL = "wss://gs5.pragmaticplaylive.net/game?tableId=..."

def on_message(ws, message):
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    
    # 1. Tenta identificar se é Socket.IO ou JSON Puro
    # Socket.IO começa com numeros (0, 2, 3, 40, 42...)
    prefix = ""
    clean_msg = message
    
    if len(message) > 0 and message[0].isdigit():
        # É provável Socket.IO
        # Ex: 42["gameMessage",{"type":"gameResult"...}]
        # Vamos tentar achar o JSON dentro
        try:
            bracket_index = message.find('[')
            if bracket_index != -1:
                prefix = message[:bracket_index] # "42"
                clean_msg = message[bracket_index:] # ["gameMessage", ...]
        except:
            pass

    try:
        data = json.loads(clean_msg)
        display_log(timestamp, prefix, data, len(message))
    except:
        # Não é JSON, loga cru
        print(f"[{timestamp}] 📡 RAW (Non-JSON): {message[:100]}...")

def display_log(timestamp, prefix, data, size):
    """Filtra e exibe colorido o que importa"""
    
    # Converte para string para buscar palavras-chave
    str_data = json.dumps(data)
    
    # 🔍 PALAVRAS-CHAVE QUE INDICAM RESULTADO
    keywords = ["gameResult", "winner", "winning", "outcome", "score", "result", "history"]
    
    is_relevant = any(k in str_data for k in keywords)
    
    if is_relevant:
        print("\n" + "="*80)
        print(f"[{timestamp}] 🎯 MENSAGEM CRÍTICA ENCONTRADA ({size} bytes)")
        print(f"Prefix: {prefix}")
        print("-" * 20)
        # Pretty print do JSON
        print(json.dumps(data, indent=2))
        print("="*80 + "\n")
    
    elif "ping" in str_data or "pong" in str_data or "heartbeat" in str_data:
         print(f"[{timestamp}] 💓 Heartbeat")
    
    else:
         print(f"[{timestamp}] ℹ️ Info: {str_data[:100]}...")

def on_error(ws, error):
    print(f"❌ Erro: {error}")

def on_close(ws, close_status_code, close_msg):
    print("⚠️ Conexão fechada")

def on_open(ws):
    print("\n✅ CONECTADO AO WEBSOCKET!")
    print("⏳ Aguardando mensagens... (Gire a roleta no navegador para gerar tráfego)\n")

if __name__ == "__main__":
    print("🔬 INICIANDO ANÁLISE DE PROTOCOLO...")
    print(f"🔗 Target: {WS_URL} (Verifique se atualizou o URL no código!)")
    
    # Debug trace
    # websocket.enableTrace(True)
    
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
