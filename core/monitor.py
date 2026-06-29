import os
import time
import json
import base64
import threading
import collections
from datetime import datetime
from playwright.sync_api import sync_playwright, Error
from config.settings import Settings
from utils.logger import setup_logger

# Decodificador do protobuf Playtech (fonte PRIMÁRIA do número no modo híbrido).
# Import tolerante: se falhar, o monitor cai 100% no DOM/MutationObserver.
try:
    from core.playtech_decoder import parse_frame, extract_roulette_number, get_path
    _DECODER_OK = True
except Exception as _dec_err:  # pragma: no cover
    _DECODER_OK = False

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

        # Sink em disco dos frames BRUTOS do WebSocket ptielive (protobuf).
        # Serializa as gravações (os callbacks do Playwright são single-thread,
        # mas o lock protege caso múltiplos WS disparem em sequência).
        self._ptielive_frames_path = Settings.PTIELIVE_FRAMES_FILE
        self._ptielive_lock = threading.Lock()

        # PUSH event-driven: o MutationObserver (JS) empurra o número direto
        # para esta fila via binding 'antigravityPush' -> zero polling CDP.
        # No modo híbrido, o protobuf também alimenta ESTA MESMA fila.
        self._spin_queue = collections.deque(maxlen=50)
        self._spin_lock = threading.Lock()
        self._binding_ready = False

        # --- Detecção HÍBRIDA: protobuf (primário) + DOM (fallback) ---
        # round_ids de gameRoundOver já ingeridos (dedup da fonte protobuf).
        self._seen_rounds = set()
        # timestamp da última entrega do protobuf (saúde da fonte primária).
        self._last_protobuf_ts = 0.0
        # quantos números o protobuf já entregou (>0 => fonte primária viva).
        self._protobuf_count = 0
        # estado de fallback (p/ logar só na transição, sem spam).
        self._fallback_active = False
        self._PROTOBUF_HEALTHY_WINDOW = Settings.PROTOBUF_HEALTHY_WINDOW

        # Cache do crupiê (raramente muda): evita varrer 8 seletores em todos
        # os frames a cada giro (eram dezenas de round-trips CDP por número).
        self._dealer_cache = "Default"
        self._dealer_cache_time = 0.0
        self._DEALER_TTL = 30.0

        # --- AUTO-RECONEXÃO (transmissão caiu / age gate) ---
        self._no_container_count = 0      # checagens seguidas sem o container
        self._last_recovery_time = 0.0    # cooldown entre tentativas de recuperação
        self._RECOVERY_COOLDOWN = 30.0

    def _push_spin(self, value):
        """Callback do binding JS (DOM): número novo direto do MutationObserver.

        No modo híbrido, o DOM é FALLBACK: se o protobuf (fonte primária) já
        entregou um número há pouco, o do DOM é redundante e é descartado
        (evita contagem dupla). O DOM só passa quando o protobuf está em
        silêncio — aí o fallback reassume sozinho.
        """
        try:
            s = str(value).strip()
            if not s.isdigit():
                return
            with self._spin_lock:
                if Settings.PROTOBUF_PRIMARY and self._protobuf_count > 0:
                    silence = time.time() - self._last_protobuf_ts
                    if silence < self._PROTOBUF_HEALTHY_WINDOW:
                        # Protobuf saudável já cobriu esta rodada -> descarta DOM.
                        if self._fallback_active:
                            self._fallback_active = False
                            logger.info("✅ [Híbrido] Protobuf normalizado — DOM volta a standby.")
                        return
                    # Protobuf em silêncio prolongado -> FALLBACK para o DOM.
                    if not self._fallback_active:
                        self._fallback_active = True
                        logger.warning(
                            f"⚠️ [Fallback] Protobuf em silêncio há {silence:.0f}s — "
                            "usando DOM/MutationObserver."
                        )
                self._spin_queue.append(s)
        except Exception:
            pass

    def _ingest_ptielive_frame(self, raw_bytes):
        """Fonte PRIMÁRIA: extrai o número sorteado de um frame protobuf do
        gateway ielive e o empurra para a fila (mesma fila do DOM).

        Usa só 'gameRoundOver' (mensagem autoritativa de fim de rodada) e
        deduplica por round_id (#3.11) — garante exatamente 1 número por rodada,
        sem leitura dupla (que o DOM ocasionalmente comete).
        """
        if not (_DECODER_OK and Settings.PROTOBUF_PRIMARY) or not raw_bytes:
            return
        try:
            frame = parse_frame(raw_bytes)
            mtype = frame.get("type") or ""
            if "gameRoundOver" not in mtype:
                return
            num = extract_roulette_number(raw_bytes)
            if num is None:
                return
            rid = get_path(frame.get("payload") or [], (11,))
            round_id = rid[0] if rid else None
            with self._spin_lock:
                if round_id is not None and round_id in self._seen_rounds:
                    return  # rodada já ingerida
                if round_id is not None:
                    self._seen_rounds.add(round_id)
                    if len(self._seen_rounds) > 500:
                        self._seen_rounds = set(list(self._seen_rounds)[-250:])
                self._spin_queue.append(str(num))
                self._last_protobuf_ts = time.time()
                self._protobuf_count += 1
            logger.info(f"🎯 [Protobuf] Rodada {round_id}: número {num} (fonte primária)")
        except Exception as e:
            logger.debug(f"Falha ao ingerir frame protobuf: {e}")

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

            # PUSH event-driven: expõe o binding ANTES de navegar, para ficar
            # disponível como init-script em todos os frames (incl. iframes da
            # Playtech). O observer JS chama window.antigravityPush(numero).
            try:
                self.context.expose_binding(
                    "antigravityPush",
                    lambda source, value: self._push_spin(value),
                )
                self._binding_ready = True
                logger.info("✅ Binding 'antigravityPush' exposto (detecção event-driven).")
            except Exception as bind_err:
                logger.warning(f"Não foi possível expor binding de push (usando fallback): {bind_err}")

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

            # Só os frames do gateway Playtech carregam o protobuf do sorteio;
            # avaliado uma vez por WS pois a URL é fixa ao longo da conexão.
            is_ptielive = "ptielive" in (ws.url or "")

            def remember_frame(direction, payload):
                # Mantém o comportamento em memória (truncado) p/ os demais dumps.
                text = str(payload)
                self.websocket_frames.append({
                    "direction": direction,
                    "url": ws.url,
                    "payload_start": text[:2000],
                })
                if len(self.websocket_frames) > 100:
                    self.websocket_frames = self.websocket_frames[-100:]

            def on_frame(direction, payload):
                remember_frame(direction, payload)
                if is_ptielive:
                    # FONTE PRIMÁRIA (ao vivo): só frames recebidos (resultado
                    # vem do servidor) e binários (protobuf). Extrai o número
                    # direto do stream antes mesmo de renderizar na tela.
                    if direction == "received" and isinstance(payload, (bytes, bytearray)):
                        self._ingest_ptielive_frame(bytes(payload))
                    # Captura opcional p/ análise offline (mesma de antes).
                    if Settings.CAPTURE_PTIELIVE_FRAMES:
                        self._write_ptielive_frame(direction, ws.url, payload)

            ws.on("framereceived", lambda payload: on_frame("received", payload))
            ws.on("framesent", lambda payload: on_frame("sent", payload))

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

    def _write_ptielive_frame(self, direction, url, payload):
        """Grava UM frame BRUTO do WS ptielive em logs/ptielive_frames.jsonl.

        Uma linha = um objeto JSON, com o payload completo (sem truncar) em
        base64. Esse arquivo é o input exato de tools/pb_correlate.py, que
        decodifica o protobuf e crava qual campo carrega o número sorteado.

        O payload do Playwright pode vir como bytes (frame binário) ou str
        (frame de texto). Bytes são codificados crus; str é codificada em
        UTF-8 antes do base64 — em ambos os casos sem perda.
        """
        try:
            if isinstance(payload, (bytes, bytearray)):
                raw = bytes(payload)
            else:
                raw = str(payload).encode("utf-8")

            record = {
                "direction": direction,
                "url": url,
                "ts": int(time.time() * 1000),
                "payload_b64": base64.b64encode(raw).decode("ascii"),
            }
            line = json.dumps(record, ensure_ascii=False)

            # open-per-write + flush: garante que cada frame sobreviva a um crash.
            with self._ptielive_lock:
                with open(self._ptielive_frames_path, "a", encoding="utf-8") as fh:
                    fh.write(line + "\n")
                    fh.flush()
        except Exception as e:
            logger.debug(f"Falha ao gravar frame ptielive no jsonl: {e}")

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
                                    window.antigravity_observer_count++;
                                    // PUSH event-driven: empurra direto pro Python (zero polling).
                                    // Se o binding não existir, cai no flag (compat).
                                    if (typeof window.antigravityPush === 'function') {
                                        try { window.antigravityPush(val); }
                                        catch (e) { window.antigravity_new_spin = true; }
                                    } else {
                                        window.antigravity_new_spin = true;
                                    }
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
            
            # Simulação periódica de atividade para evitar desconexão (a cada 90s)
            if time.time() - self.last_activity_time > 90:
                self.simulate_activity()
                self.last_activity_time = time.time()
                
            target_frame = self.working_frame if self.working_frame else self.page

            # 0. CAMINHO RÁPIDO: fila de PUSH (event-driven, ZERO round-trip CDP).
            # O observer JS já entregou o número via binding; só drenamos aqui.
            with self._spin_lock:
                if self._spin_queue:
                    valor = self._spin_queue.popleft()
                    self.last_number = valor
                    logger.info(f"✅ [Push] Número novo detectado: {valor}")
                    return valor

            # 1. PRIORIDADE: MutationObserver via flag (fallback se push falhar)
            if self.observer_active:
                try:
                    # OTIMIZAÇÃO: lê o flag, captura o valor e reseta o flag em
                    # UMA única chamada CDP (antes eram 3 round-trips por número).
                    # Cada evaluate() é uma ida-e-volta pelo protocolo DevTools
                    # (~1-5ms); a 10Hz isso somava ~30ms/giro à toa.
                    valor = target_frame.evaluate(
                        "() => { if (window.antigravity_new_spin) {"
                        " const v = window.antigravity_last_number;"
                        " window.antigravity_new_spin = false; return v; } return null; }"
                    )
                    if valor is not None and str(valor).strip().isdigit():
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
                # DETECÇÃO DE QUEDA: o container (histórico) sumiu por várias
                # checagens seguidas -> a transmissão caiu (age gate/reload).
                # Dispara a recuperação automática.
                self._no_container_count += 1
                if self._no_container_count >= 30:  # ~6s seguidos sem container
                    self._recover_connection()
                    self._no_container_count = 0
                if self.watch_count % 40 == 0:
                    logger.warning("Container estendido não encontrado. Verificando...")
                return None
            self._no_container_count = 0  # container presente -> conexão viva

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

    def _dismiss_blockers(self):
        """Fecha popups que bloqueiam a roleta (age gate '18 anos', cookies)."""
        if not self.page:
            return
        textos = ["Sim", "✓ Sim", "Aceitar tudo", "Aceitar", "Concordo", "Entendi"]
        contextos = [self.page]
        try:
            contextos += list(self.page.frames)
        except Exception:
            pass
        for ctx in contextos:
            for t in textos:
                try:
                    loc = ctx.get_by_text(t, exact=True)
                    if loc.count() > 0 and loc.first.is_visible(timeout=300):
                        loc.first.click(timeout=1500)
                        logger.info(f"🟢 [Recover] Popup fechado: '{t}'")
                        time.sleep(0.4)
                except Exception:
                    continue

    def _recover_connection(self):
        """Reconecta sozinho quando a transmissão cai (age gate / reload da página)."""
        now = time.time()
        if now - self._last_recovery_time < self._RECOVERY_COOLDOWN:
            return
        self._last_recovery_time = now
        logger.warning("🔌 [Recover] Transmissão caiu — recuperando conexão automaticamente...")
        try:
            # 1. Fecha popups (age gate, cookies)
            self._dismiss_blockers()

            # 2. Se saiu da roleta, re-navega para a URL do jogo (perfil persistente = já logado)
            game_url = os.getenv("GAME_URL") or "https://geralbet.bet.br/games/playtech/roleta-brasileira"
            try:
                cur = (self.page.url or "").lower()
            except Exception:
                cur = ""
            if "roleta" not in cur and "playtech" not in cur:
                logger.info(f"🔄 [Recover] Re-navegando para {game_url}")
                try:
                    self.page.goto(game_url, timeout=60000)
                except Exception as nav_err:
                    logger.warning(f"[Recover] Erro ao re-navegar: {nav_err}")
                time.sleep(3)
                self._dismiss_blockers()

            try:
                self.page.wait_for_load_state("load", timeout=30000)
            except Exception:
                pass
            time.sleep(2)
            self._dismiss_blockers()

            # 3. Re-descobre o container e religa o observer
            self.working_frame = None
            container = self._find_extended_container()
            if not container:
                self._try_open_extended_history()
                container = self._find_extended_container()
            if container:
                self._setup_mutation_observer()
                logger.info("✅ [Recover] Reconectado — observer reativado. Voltando a monitorar.")
            else:
                logger.warning("⚠️ [Recover] Ainda sem histórico. Nova tentativa no próximo ciclo.")
        except Exception as e:
            logger.error(f"[Recover] Falha na recuperação: {e}")

    def get_current_dealer(self) -> str:
        """Tenta encontrar o nome do crupiê (dealer) ativo na tela (com cache TTL)"""
        now = time.time()
        # Cache: o crupiê muda a cada ~20-40 min, não a cada giro. Reaproveita.
        if now - self._dealer_cache_time < self._DEALER_TTL:
            return self._dealer_cache

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
        # Atualiza o timestamp do cache ANTES da busca: mesmo que não ache nada,
        # evitamos repetir a varredura cara a cada giro durante o TTL.
        self._dealer_cache_time = now
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
                        self._dealer_cache = name
                        return name
            except:
                continue
        # Não encontrou: mantém o último conhecido (ou "Default") por todo o TTL.
        return self._dealer_cache

    def stop(self):
        logger.info("Encerrando monitor...")
        GameMonitor._active = False
        self.observer_active = False
        try:
            if self.context: self.context.close()
            if self.playwright: self.playwright.stop()
        except: pass
