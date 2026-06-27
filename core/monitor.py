import time
import json
from datetime import datetime
from playwright.sync_api import sync_playwright, Error
from config.settings import Settings
from utils.logger import setup_logger

logger = setup_logger('monitor')

class GameMonitor:
    """
    Monitor robusto para capturar números da Roleta Brasileira (Playtech)
    
    FONTE OFICIAL: .roulette-history_extended__items--DIvtr
    - Container persistente (não é destruído pelo React)
    - Contém ~500 resultados históricos
    - Atualizado via append (não replace)
    - Monitorado via MutationObserver
    
    Singleton: Apenas 1 instância por sessão
    """

    # Singleton Guard
    _instance = None
    _active = False

    # FONTE OFICIAL — cadeia de fallback (resiliente a mudança de hash)
    EXTENDED_SELECTORS = [
        ".roulette-history_line",                         # Timeline padrão (novo)
        "[class*='roulette-history_line']",               # Timeline (hash-proof)
        "[class*='roulette-history_extended__items']",    # Estendido (hash-proof)
        "[class*='roulette-history_extended']",           # Fallback amplo
        "[data-testid='roulette-history-extended']",      # data-testid
    ]
    
    # Seletores para tentar abrir o histórico estendido
    HISTORY_TOGGLE_SELECTORS = [
        "[class*='roulette-history_toggle']",
        "[class*='history-extended']",
        "[class*='roulette-history_button']",
        "[class*='history_toggle']",
        "[class*='history-button']",
        "button[class*='history']",
    ]
    
    NUMBER_SELECTORS = [
        "[data-automation-locator='field.lastHistoryItem'] .history-item-value__text", # Recomendado (Estável)
        "[data-automation-locator='field.lastHistoryItem'] div",                      # Fallback resiliente
        ".roulette-history_line [class*='history-item-value__text']",                # Timeline segura
        "[class*='history-item-value__text']",                                       # Parcial (hash-proof)
        "[class*='history-item-value_last']",                                        # Último item
        "[class*='history-item-value']",                                             # Fallback amplo
    ]

    def __new__(cls):
        if cls._instance is not None and cls._active:
            logger.warning("🚨 INSTÂNCIA DUPLICADA DETECTADA! Retornando instância existente.")
            return cls._instance
        instance = super().__new__(cls)
        cls._instance = instance
        return instance

    def __init__(self):
        if GameMonitor._active:
            return
        self.playwright = None
        self.context = None
        self.page = None
        self.last_number = None
        self.watch_count = 0
        self.working_number_selector = None
        self.working_extended_selector = None
        self.working_frame = None
        self.observer_active = False
        self.websocket_urls = []
        self.websocket_frames = []
        self.failed_requests = []
        self.console_errors = []
        self.last_activity_time = time.time()

    def start(self):
        """Inicia o navegador com perfil persistente (Singleton)"""
        if GameMonitor._active:
            logger.warning("🚨 Monitor já ativo! Ignorando start() duplicado.")
            return True
        GameMonitor._active = True
        logger.info(f"Iniciando monitor (Headless: {Settings.HEADLESS})...")
        try:
            self.playwright = sync_playwright().start()
            
            self.context = self.playwright.chromium.launch_persistent_context(
                user_data_dir=str(Settings.BROWSER_PROFILE_DIR),
                headless=False,
                viewport=None,
                args=[
                    "--start-maximized",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-features=IsolateOrigins,site-per-process",
                ],
            )
            self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
            self._attach_debug_listeners()
            
            logger.info("Navegando para a Home da GeralBet...")
            self.page.goto("https://geralbet.bet.br/", timeout=60000)
            
            print("\n" + "="*50)
            print("🛑 PAUSA PARA OPERAÇÃO MANUAL 🛑")
            print("="*50)
            print("1️⃣  Faça LOGIN na GeralBet")
            print("2️⃣  Navegue até: Cassino ao Vivo > Roleta Brasileira")
            print("3️⃣  Aguarde a roleta CARREGAR TOTALMENTE")
            print("4️⃣  ABRA O HISTÓRICO ESTENDIDO (clique no ícone de histórico)")
            print("="*50)
            
            input("👉 Quando a roleta estiver aparecendo, pressione ENTER para iniciar...")
            
            print("⏳ Sincronizando sistema...")
            self.page.wait_for_load_state("load")
            self._dump_debug_state("after_manual_enter")
            
            self._discover_extended_container()
            return True
            
        except Exception as e:
            logger.error(f"Erro ao iniciar GameMonitor: {e}")
            self._dump_debug_state("start_error")
            self.stop()
            return False

    def _attach_debug_listeners(self):
        """Coleta sinais úteis sem precisar abrir o DevTools."""
        def on_websocket(ws):
            self.websocket_urls.append(ws.url)
            logger.info(f"🌐 WebSocket detectado: {ws.url}")

            def remember_frame(direction, payload):
                text = str(payload)
                self.websocket_frames.append({
                    "direction": direction,
                    "url": ws.url,
                    "payload_start": text[:2000],
                })
                if len(self.websocket_frames) > 100:
                    self.websocket_frames = self.websocket_frames[-100:]

            ws.on("framereceived", lambda payload: remember_frame("received", payload))
            ws.on("framesent", lambda payload: remember_frame("sent", payload))

        def on_request_failed(request):
            failure = request.failure or ""
            entry = {"url": request.url, "method": request.method, "failure": failure}
            self.failed_requests.append(entry)
            if len(self.failed_requests) > 50:
                self.failed_requests = self.failed_requests[-50:]

        def on_console(message):
            if message.type in ("error", "warning"):
                self.console_errors.append({"type": message.type, "text": message.text})
                if len(self.console_errors) > 50:
                    self.console_errors = self.console_errors[-50:]

        self.page.on("websocket", on_websocket)
        self.page.on("requestfailed", on_request_failed)
        self.page.on("console", on_console)

    def _dump_debug_state(self, label):
        """Salva estado da página para diagnosticar iframe/DOM travado."""
        if not self.page:
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"debug_{label}_{timestamp}"
        json_path = Settings.LOGS_DIR / f"{base_name}.json"
        screenshot_path = Settings.LOGS_DIR / f"{base_name}.png"

        selector_counts = {}
        selectors = self.EXTENDED_SELECTORS + self.NUMBER_SELECTORS + self.HISTORY_TOGGLE_SELECTORS
        frames_info = []

        try:
            self.page.screenshot(path=str(screenshot_path), full_page=True)
        except Exception as e:
            logger.warning(f"Não foi possível salvar screenshot de debug: {e}")

        for index, frame in enumerate(self.page.frames):
            frame_info = {
                "index": index,
                "url": frame.url,
                "name": frame.name,
                "title": None,
                "body_text_start": None,
                "selector_counts": {},
            }
            try:
                frame_info["title"] = frame.title()
            except Exception:
                pass
            try:
                text = frame.locator("body").inner_text(timeout=1500)
                frame_info["body_text_start"] = text[:1200]
            except Exception:
                pass
            for selector in selectors:
                try:
                    count = frame.locator(selector).count()
                    frame_info["selector_counts"][selector] = count
                    selector_counts[selector] = selector_counts.get(selector, 0) + count
                except Exception:
                    frame_info["selector_counts"][selector] = None
            frames_info.append(frame_info)

        payload = {
            "label": label,
            "page_url": self.page.url,
            "screenshot": str(screenshot_path),
            "websocket_urls": self.websocket_urls[-50:],
            "websocket_frames": self.websocket_frames[-100:],
            "failed_requests": self.failed_requests[-50:],
            "console_errors": self.console_errors[-50:],
            "selector_counts_total": selector_counts,
            "frames": frames_info,
        }

        try:
            json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            logger.info(f"🧪 Debug salvo em: {json_path}")
            logger.info(f"🖼️ Screenshot salvo em: {screenshot_path}")
        except Exception as e:
            logger.warning(f"Não foi possível salvar JSON de debug: {e}")

    def _find_in_frames(self, selector, all=False):
        """Busca um seletor com cache de frame (Otimizado usando Locator API)"""
        if self.working_frame:
            try:
                handles = self.working_frame.locator(selector).element_handles()
                if handles:
                    return handles if all else handles[0]
                else:
                    self.working_frame = None
            except Exception:
                self.working_frame = None

        try:
            handles = self.page.locator(selector).element_handles()
            if handles:
                return handles if all else handles[0]
        except Exception:
            pass

        for frame in self.page.frames:
            try:
                handles = frame.locator(selector).element_handles()
                if handles:
                    self.working_frame = frame
                    return handles if all else handles[0]
            except Exception:
                continue

        return [] if all else None

    def _find_extended_container(self):
        """Tenta encontrar o container estendido usando a cadeia de fallback"""
        if self.working_extended_selector:
            container = self._find_in_frames(self.working_extended_selector)
            if container:
                return container

        for selector in self.EXTENDED_SELECTORS:
            container = self._find_in_frames(selector)
            if container:
                if selector != self.working_extended_selector:
                    logger.info(f"✅ Container encontrado com seletor: {selector}")
                    self.working_extended_selector = selector
                return container
        return None

    def _try_open_extended_history(self):
        """Tenta abrir o painel de histórico estendido clicando no botão de toggle"""
        logger.info("🔍 Tentando abrir o histórico estendido programaticamente...")
        for selector in self.HISTORY_TOGGLE_SELECTORS:
            try:
                toggle = self._find_in_frames(selector)
                if toggle:
                    toggle.click()
                    logger.info(f"🖱️ Clicou em: {selector}")
                    time.sleep(2)
                    # Verifica se o container apareceu
                    container = self._find_extended_container()
                    if container:
                        logger.info("✅ Histórico estendido aberto com sucesso!")
                        return True
            except Exception as e:
                logger.debug(f"Toggle {selector} falhou: {e}")
                continue
        return False

    def _discover_extended_container(self):
        """
        Aguarda o container estendido usando cadeia de fallback.
        Resiliente a mudanças de hash nos nomes de classe CSS.
        """
        logger.info("🔍 Buscando container ESTENDIDO (cadeia de fallback ativa)")
        logger.info(f"🔒 Singleton Status: active={GameMonitor._active}, instance_id={id(self)}")
        logger.info(f"📋 Seletores disponíveis: {self.EXTENDED_SELECTORS}")
        
        attempt = 0
        while True:
            attempt += 1
            
            # Busca o container com cadeia de fallback
            container = self._find_extended_container()
            if container:
                logger.info(f"✅ Container ESTENDIDO encontrado na tentativa {attempt}!")
                logger.info(f"🎯 Seletor que funcionou: {self.working_extended_selector}")
                break
            
            # A cada 5 tentativas, tenta abrir programaticamente
            if attempt % 5 == 0:
                self._try_open_extended_history()
                
            # Log a cada 10 tentativas
            if attempt % 10 == 0:
                self._dump_debug_state(f"container_not_found_attempt_{attempt}")
                logger.warning(f"⏳ Tentativa {attempt}: Container estendido não encontrado. Verifique se o histórico está aberto.")
                print(f"\n⚠️ ATENÇÃO: O histórico estendido ainda não foi encontrado (tentativa {attempt})")
                print("   → Certifique-se de que o painel de histórico está ABERTO na roleta.\n")
            else:
                logger.info(f"Tentativa {attempt}: Aguardando container estendido...")
            
            time.sleep(2)
        
        # Container encontrado → Configura MutationObserver
        self._setup_mutation_observer()
        
        # Descobre seletor de números dentro do container
        container = self._find_extended_container()
        if container:
            for selector in self.NUMBER_SELECTORS:
                try:
                    elements = container.query_selector_all(selector)
                    if elements:
                        self.working_number_selector = selector
                        logger.info(f"✅ Números encontrados com: {selector} ({len(elements)} itens)")
                        break
                except:
                    continue
        
        if not self.working_number_selector:
            logger.warning("⚠️ Nenhum seletor de número funcionou. Usando padrão.")
            self.working_number_selector = self.NUMBER_SELECTORS[0]

    def _setup_mutation_observer(self):
        """Configura um MutationObserver PERSISTENTE no container estendido"""
        logger.info("🚀 Configurando MutationObserver no container estendido...")
        
        container = self._find_extended_container()
        if not container:
            logger.error("❌ Container estendido não encontrado para configurar observer.")
            return

        observer_script = """
        (target) => {
            // Limpa observer anterior se existir
            if (window.antigravity_observer) {
                window.antigravity_observer.disconnect();
            }
            
            window.antigravity_new_spin = false;
            window.antigravity_last_number = "";
            window.antigravity_observer_count = 0;
            
            if (target) {
                const observer = new MutationObserver((mutations) => {
                    for (let mutation of mutations) {
                        for (let node of mutation.addedNodes) {
                            if (node.nodeType === 1) {
                                const textElem = node.querySelector("[data-automation-locator='field.lastHistoryItem'] [class*='history-item-value__text']") ||
                                                 node.querySelector("[class*='history-item-value__text']") || 
                                                 node.querySelector("[class*='history-item-value']") ||
                                                 node;
                                const val = textElem.innerText ? textElem.innerText.trim() : '';
                                if (val && !isNaN(val)) {
                                    window.antigravity_last_number = val;
                                    window.antigravity_new_spin = true;
                                    window.antigravity_observer_count++;
                                }
                            }
                        }
                    }
                });
                window.antigravity_observer = observer;
                observer.observe(target, { childList: true, subtree: true });
                console.log('MutationObserver Antigravity ativo no container estendido.');
                return true;
            } else {
                console.error('Container estendido inválido para observer!');
                return false;
            }
        }
        """
        try:
            result = container.evaluate(observer_script)
            if result:
                self.observer_active = True
                logger.info("✅ MutationObserver ATIVO no container estendido.")
            else:
                logger.error("❌ Falha ao configurar MutationObserver: container inválido.")
        except Exception as e:
            logger.error(f"Erro ao configurar MutationObserver: {e}")

    def watch(self):
        """
        Monitora novos números.
        Prioridade: MutationObserver (event-driven) > Polling DOM (fallback)
        """
        try:
            self.watch_count += 1
            
            # Simulação periódica de atividade para evitar desconexão (a cada 3 minutos)
            if time.time() - self.last_activity_time > 180:
                self.simulate_activity()
                self.last_activity_time = time.time()
                
            target_frame = self.working_frame if self.working_frame else self.page
            
            # 1. PRIORIDADE: MutationObserver (event-driven, sem delay)
            if self.observer_active:
                try:
                    has_new = target_frame.evaluate("window.antigravity_new_spin")
                    if has_new:
                        valor = target_frame.evaluate("window.antigravity_last_number")
                        target_frame.evaluate("window.antigravity_new_spin = false")
                        if valor and str(valor).strip().isdigit():
                            self.last_number = str(valor).strip()
                            logger.info(f"✅ [Observer] Número novo detectado: {self.last_number}")
                            return self.last_number
                    elif self.last_number is not None:
                        return None  # Sem mutação detectada
                except Exception as e:
                    if self.watch_count % 20 == 0:
                        logger.warning(f"Observer check falhou: {e}. Tentando reconectar...")
                        self._reconnect_observer()

            # 2. FALLBACK: Polling DOM (apenas se observer não funcionar)
            container = self._find_extended_container()
            if not container:
                if self.watch_count % 40 == 0:
                    logger.warning("Container estendido não encontrado. Verificando...")
                return None

            if self.working_number_selector:
                try:
                    numbers = container.query_selector_all(self.working_number_selector)
                    if numbers:
                        valor = numbers[0].inner_text().strip()
                        if valor.isdigit() and valor != self.last_number:
                            self.last_number = valor
                            logger.info(f"✅ [Polling] Número novo detectado: {valor}")
                            return valor
                except:
                    pass
            return None

        except Exception as e:
            if self.watch_count % 40 == 0:
                logger.error(f"Erro em watch(): {e}")
            return None
    def get_initial_history(self) -> list[int]:
        """Extrai todos os números históricos visíveis na tela de uma vez para inicialização"""
        container = self._find_extended_container()
        if not container:
            return []
        try:
            # Seletores candidatos para histórico amplo
            candidates = [
                ".roulette-history_line [class*='history-item-value__text']",
                "[class*='history-item-value__text']",
                "[class*='history-item-value']",
            ]
            if self.working_number_selector:
                candidates.append(self.working_number_selector)

            best_elements = []
            best_selector = None
            for sel in candidates:
                try:
                    elements = container.query_selector_all(sel)
                    if elements and len(elements) > len(best_elements):
                        best_elements = elements
                        best_selector = sel
                except Exception as e:
                    logger.debug(f"Falha ao consultar seletor de histórico '{sel}': {e}")

            if not best_elements:
                logger.warning("⚠️ Nenhum elemento de histórico encontrado com os seletores.")
                return []

            logger.info(f"📊 [History] Seletor '{best_selector}' escolhido. Encontrou {len(best_elements)} elementos.")

            numeros = []
            for el in best_elements:
                text = el.inner_text().strip()
                if text.isdigit():
                    numeros.append(int(text))
            
            # Os números vêm do mais novo (topo/esquerda) para o mais antigo.
            # Invertemos para que fiquem em ordem cronológica (antigo -> novo).
            numeros.reverse()
            logger.info(f"📊 [History] Extraídos {len(numeros)} números históricos da roleta para inicialização.")
            return numeros
        except Exception as e:
            logger.warning(f"Erro ao extrair histórico inicial: {e}")
            return []

    def _reconnect_observer(self):
        """Tenta reconectar o MutationObserver se ele perdeu a conexão"""
        logger.info("🔄 Reconectando MutationObserver...")
        container = self._find_extended_container()
        if container:
            self._setup_mutation_observer()
        else:
            logger.warning("Container estendido não encontrado para reconexão.")
            self.observer_active = False

    def simulate_activity(self):
        """Simula atividade segura do usuário para evitar desconexão por inatividade"""
        if not self.page:
            return
        try:
            import random
            # 1. Movimento de mouse em área central neutra (segura)
            x = random.randint(200, 600)
            y = random.randint(200, 600)
            self.page.mouse.move(x, y)
            
            # 2. Pressiona tecla neutra
            self.page.keyboard.press("Shift")
            
            # 3. Pequeno scroll (desce e sobe)
            self.page.mouse.wheel(0, 50)
            time.sleep(0.2)
            self.page.mouse.wheel(0, -50)
            
            logger.info("🔄 [Antidisconnect] Atividade simulada com sucesso (Movimento, Teclado e Scroll).")
        except Exception as e:
            logger.debug(f"Erro ao simular atividade do usuário: {e}")

    def get_current_dealer(self) -> str:
        """Tenta encontrar o nome do crupiê (dealer) ativo na tela"""
        selectors = [
            "[class*='dealer-name']",
            "[class*='dealerName']",
            "[class*='presenter-name']",
            "[class*='presenterName']",
            "[class*='croupier-name']",
            "[class*='croupierName']",
            "[data-automation-locator*='dealer']",
            "[data-automation-locator*='presenter']",
        ]
        for sel in selectors:
            try:
                el = self._find_in_frames(sel)
                if el:
                    name = el.inner_text()
                    # Remove prefixos comuns
                    for prefix in ("Crupiê:", "Dealer:", "Presenter:", "Apresentador:"):
                        name = name.replace(prefix, "")
                    name = name.strip()
                    if name:
                        return name
            except:
                continue
        return "Default"

    def stop(self):
        logger.info("Encerrando monitor...")
        GameMonitor._active = False
        self.observer_active = False
        try:
            if self.context: self.context.close()
            if self.playwright: self.playwright.stop()
        except: pass
