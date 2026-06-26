import time
import logging
from playwright.sync_api import sync_playwright
from config.settings import Settings

logger = logging.getLogger('url_finder')

def discover_livedistributed_url(timeout=60):
    """
    Usa Playwright para abrir a página e interceptar a URL que contém 'livedistributed'.
    Retorna a URL encontrada ou None se expirar.
    """
    logger.info("🔍 Iniciando busca automática de endpoint dinâmico...")
    
    discovered_url = None

    with sync_playwright() as p:
        # Lança o navegador (pode ser headless ou não, mas para o usuário ver é melhor não ser)
        browser = p.chromium.launch(headless=Settings.HEADLESS)
        context = browser.new_context(viewport={'width': 1280, 'height': 720})
        page = context.new_page()

        def handle_request(request):
            nonlocal discovered_url
            url = request.url
            if "livedistributed" in url and not discovered_url:
                logger.info(f"✅ Endpoint detectado via Request: {url}")
                discovered_url = url

        def handle_websocket(ws):
            nonlocal discovered_url
            url = ws.url
            if "livedistributed" in url and not discovered_url:
                logger.info(f"✅ Endpoint detectado via WebSocket: {url}")
                discovered_url = url

        # Registra os interceptadores
        page.on("request", handle_request)
        page.on("websocket", handle_websocket)

        try:
            # Navega para a página inicial
            target_url = "https://geralbet.bet.br/"
            logger.info(f"Navegando para {target_url}...")
            page.goto(target_url, wait_until="networkidle", timeout=30000)
            
            print("\n" + "!"*60)
            print("🤖 SISTEMA DE CAPTURA AUTOMÁTICA ATIVO")
            print("!"*60)
            print("1. Por favor, navegue até a Roleta Brasileira (Playtech)")
            print("2. O bot irá capturar o link 'livedistributed' automaticamente")
            print(f"3. Aguardando por até {timeout} segundos...")
            print("!"*60 + "\n")

            start_time = time.time()
            while time.time() - start_time < timeout:
                if discovered_url:
                    break
                time.sleep(1)

        except Exception as e:
            logger.error(f"Erro durante a captura de URL: {e}")
        finally:
            browser.close()

    if discovered_url:
        # Se for WebSocket, geralmente o Playwright retorna o URL completo
        # Se for um link de polling, também.
        return discovered_url
    else:
        logger.warning("⚠️ Tempo expirado. Nenhuma URL 'livedistributed' foi encontrada.")
        return None

if __name__ == "__main__":
    # Teste rápido
    logging.basicConfig(level=logging.INFO)
    url = discover_livedistributed_url(timeout=30)
    if url:
        print(f"\n🚀 SUCESSO! URL Encontrada: {url}")
    else:
        print("\n❌ Falha ao encontrar a URL.")
