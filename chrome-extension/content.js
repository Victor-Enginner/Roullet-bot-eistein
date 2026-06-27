// Einstein Roulette AI HUD - Chrome Extension Content Script
(function () {
    console.log("🧠 Einstein Roulette AI HUD Content Script loaded!");

    // Prevents double injection
    if (window.einsteinHUDInitialized) return;
    window.einsteinHUDInitialized = true;

    // Config variables
    const serverUrl = "http://localhost:4000";
    let socket = null;
    let hudContainer = null;
    let launcherOrb = null;
    let shadowRoot = null;

    // Create and inject CSS reference into shadow DOM
    const cssUrl = chrome.runtime.getURL("hud.css");
    const einsteinImgUrl = chrome.runtime.getURL("einstein_hologram.png");
    const einsteinThinkingUrl = chrome.runtime.getURL("einstein_thinking.png");
    const einsteinCelebratingUrl = chrome.runtime.getURL("einstein_celebrating.png");

    // Initialize UI
    function initUI() {
        // 1. Create Launcher Orb
        launcherOrb = document.createElement("div");
        launcherOrb.className = "einstein-launcher-orb";
        launcherOrb.innerHTML = "HUD";
        document.body.appendChild(launcherOrb);

        // 2. Create HUD Main Container
        hudContainer = document.createElement("div");
        hudContainer.className = "einstein-hud-container";
        hudContainer.style.display = "none"; // Hidden by default
        document.body.appendChild(hudContainer);

        // 3. Attach Shadow DOM to insulate styles
        shadowRoot = hudContainer.attachShadow({ mode: "open" });

        // Load fonts inside Shadow DOM
        const fontLink = document.createElement("link");
        fontLink.rel = "stylesheet";
        fontLink.href = "https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Orbitron:wght@400;700&display=swap";
        shadowRoot.appendChild(fontLink);

        // Load custom stylesheet
        const styleLink = document.createElement("link");
        styleLink.rel = "stylesheet";
        styleLink.href = cssUrl;
        shadowRoot.appendChild(styleLink);

        // Render HTML structure
        const hudHTML = `
            <div class="einstein-hud-header" id="dragHeader">
                <div class="einstein-hud-title">
                    <span class="einstein-hud-dot" id="statusDot"></span>
                    EINSTEIN AI HUD
                </div>
                <div class="einstein-hud-close" id="closeBtn">×</div>
            </div>
            
            <div class="einstein-hud-body">
                <!-- Info Grid -->
                <div class="einstein-hud-row">
                    <div class="einstein-hud-label">Crupiê</div>
                    <div class="einstein-hud-value" id="croupierVal">Aguardando...</div>
                </div>
                <div class="einstein-hud-row">
                    <div class="einstein-hud-label">Último Giro</div>
                    <div class="einstein-hud-value" id="lastSpinVal">-</div>
                </div>
                
                <!-- Signal Card -->
                <div class="einstein-signal-card" id="signalCard">
                    <div class="einstein-hud-label" id="signalStateLabel">Estado do Sistema</div>
                    <div class="einstein-entry-text" id="entryVal">Monitorando Mesa...</div>
                    <div style="font-size: 11px; margin-top: 4px; color: rgba(255,255,255,0.7);" id="leituraVal">Aguardando sinal verde da IA.</div>
                    
                    <!-- Kelly Gauge -->
                    <div class="einstein-kelly-container" style="margin-top: 8px;">
                        <div class="einstein-hud-row" style="font-size: 11px;">
                            <span class="einstein-hud-label">Gestão Kelly</span>
                            <span id="kellyVal" style="font-weight: bold; color: var(--border-green);">0.0%</span>
                        </div>
                        <div class="einstein-kelly-bar-bg">
                            <div class="einstein-kelly-bar-fill" id="kellyBarFill"></div>
                        </div>
                    </div>

                    <!-- Einstein Hologram Overlay -->
                    <div class="einstein-hologram-overlay" id="einsteinHologram">
                        <div class="einstein-hologram-portrait"></div>
                        <div class="einstein-hologram-alert"></div>
                        <div class="einstein-hologram-quote"></div>
                    </div>
                </div>

                <!-- Protections / Coberturas -->
                <div class="einstein-hud-row">
                    <div class="einstein-hud-label">Proteção</div>
                    <div class="einstein-hud-value" id="protectionVal">-</div>
                </div>
                
                <!-- Terminal Console -->
                <div class="einstein-console" id="consoleLogs">
                    <div class="einstein-console-line success">Einstein HUD V1.0 iniciado.</div>
                    <div class="einstein-console-line">Aguardando conexão com o bridge...</div>
                </div>
            </div>
        `;

        const contentWrapper = document.createElement("div");
        contentWrapper.style.display = "flex";
        contentWrapper.style.flexDirection = "column";
        contentWrapper.innerHTML = hudHTML;
        shadowRoot.appendChild(contentWrapper);

        // Bind events
        bindUIEvents();

        // Inicializa com Einstein pensando
        setHologramState("thinking");
    }

    // Interactive event listeners
    function bindUIEvents() {
        const dragHeader = shadowRoot.getElementById("dragHeader");
        const closeBtn = shadowRoot.getElementById("closeBtn");

        // Toggle visibility
        launcherOrb.addEventListener("click", () => {
            if (hudContainer.style.display === "none") {
                hudContainer.style.display = "flex";
                logToConsole("Painel HUD aberto.");
            } else {
                hudContainer.style.display = "none";
            }
        });

        closeBtn.addEventListener("click", () => {
            hudContainer.style.display = "none";
            logToConsole("Painel HUD minimizado.");
        });

        // Make HUD container draggable
        let pos1 = 0, pos2 = 0, pos3 = 0, pos4 = 0;
        
        dragHeader.onmousedown = dragMouseDown;

        function dragMouseDown(e) {
            e = e || window.event;
            e.preventDefault();
            // Get the mouse cursor position at startup
            pos3 = e.clientX;
            pos4 = e.clientY;
            document.onmouseup = closeDragElement;
            // Call a function whenever the cursor moves
            document.onmousemove = elementDrag;
        }

        function elementDrag(e) {
            e = e || window.event;
            e.preventDefault();
            // Calculate the new cursor position
            pos1 = pos3 - e.clientX;
            pos2 = pos4 - e.clientY;
            pos3 = e.clientX;
            pos4 = e.clientY;
            // Set the element's new position
            hudContainer.style.top = (hudContainer.offsetTop - pos2) + "px";
            hudContainer.style.left = (hudContainer.offsetLeft - pos1) + "px";
        }

        function closeDragElement() {
            // Stop moving when mouse button is released
            document.onmouseup = null;
            document.onmousemove = null;
        }
    }

    // Log helper for custom HUD console
    function logToConsole(text, type = "info") {
        const consoleLogs = shadowRoot.getElementById("consoleLogs");
        if (!consoleLogs) return;

        const line = document.createElement("div");
        line.className = `einstein-console-line ${type}`;
        line.textContent = `[${new Date().toLocaleTimeString()}] ${text}`;
        consoleLogs.appendChild(line);
        consoleLogs.scrollTop = consoleLogs.scrollHeight;
    }

    // Query status from background
    function connectSocket() {
        logToConsole("Tentando estabelecer conexão com o bridge...");
        
        chrome.runtime.sendMessage({ action: "request_status" }, (response) => {
            if (response && response.connected !== undefined) {
                updateConnectionStatus(response.connected);
            }
        });
    }

    function updateConnectionStatus(connected) {
        const statusDot = shadowRoot.getElementById("statusDot");
        if (connected) {
            logToConsole("Conectado ao servidor da ponte!", "success");
            if (statusDot) statusDot.className = "einstein-hud-dot connected";
        } else {
            logToConsole("Desconectado do servidor da ponte.", "error");
            if (statusDot) statusDot.className = "einstein-hud-dot";
            resetSignalUI();
        }
    }

    // --- Web Audio API Synth Sound Generator ---
    let audioCtx = null;

    // Inicializa o AudioContext apenas após a primeira interação do usuário na página
    function initAudioOnGesture() {
        if (!audioCtx) {
            try {
                audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            } catch (e) {
                console.log("Erro ao criar AudioContext:", e);
            }
        }
        if (audioCtx && audioCtx.state === "suspended") {
            audioCtx.resume().catch(() => {});
        }
    }
    document.addEventListener("click", initAudioOnGesture, { once: true, capture: true });
    document.addEventListener("keydown", initAudioOnGesture, { once: true, capture: true });

    function getAudioContext() {
        return audioCtx;
    }

    function playSynthSound(type) {
        try {
            const ctx = getAudioContext();
            if (!ctx || ctx.state === "suspended") {
                // Ignora silenciosamente se o áudio estiver bloqueado pelo navegador por falta de clique
                return;
            }
            const now = ctx.currentTime;
            
            if (type === "signal") {
                // Cyberpunk Bootup Chime (rising high-pitched tones)
                const osc1 = ctx.createOscillator();
                const osc2 = ctx.createOscillator();
                const gain = ctx.createGain();
                
                osc1.type = "sine";
                osc2.type = "triangle";
                
                osc1.frequency.setValueAtTime(587.33, now); // D5
                osc1.frequency.setValueAtTime(880.00, now + 0.15); // A5
                
                osc2.frequency.setValueAtTime(587.33, now);
                osc2.frequency.setValueAtTime(880.00, now + 0.15);
                
                gain.gain.setValueAtTime(0.12, now);
                gain.gain.exponentialRampToValueAtTime(0.001, now + 0.45);
                
                osc1.connect(gain);
                osc2.connect(gain);
                gain.connect(ctx.destination);
                
                osc1.start(now);
                osc2.start(now);
                osc1.stop(now + 0.45);
                osc2.stop(now + 0.45);
            } 
            else if (type === "win") {
                // Win Chime (rapid major arpeggio - satisfying arcade sound)
                const notes = [523.25, 659.25, 783.99, 1046.50]; // C5, E5, G5, C6
                notes.forEach((freq, index) => {
                    const osc = ctx.createOscillator();
                    const gain = ctx.createGain();
                    
                    osc.type = "sine";
                    osc.frequency.setValueAtTime(freq, now + (index * 0.08));
                    
                    gain.gain.setValueAtTime(0.12, now + (index * 0.08));
                    gain.gain.exponentialRampToValueAtTime(0.001, now + (index * 0.08) + 0.4);
                    
                    osc.connect(gain);
                    gain.connect(ctx.destination);
                    
                    osc.start(now + (index * 0.08));
                    osc.stop(now + (index * 0.08) + 0.4);
                });
            }
            else if (type === "protection") {
                // Warning Alert Pulse (descending warning tones)
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                
                osc.type = "sawtooth";
                const filter = ctx.createBiquadFilter();
                filter.type = "lowpass";
                filter.frequency.setValueAtTime(600, now);
                
                osc.frequency.setValueAtTime(392.00, now); // G4
                osc.frequency.setValueAtTime(293.66, now + 0.2); // D4
                
                gain.gain.setValueAtTime(0.08, now);
                gain.gain.exponentialRampToValueAtTime(0.001, now + 0.5);
                
                osc.connect(filter);
                filter.connect(gain);
                gain.connect(ctx.destination);
                
                osc.start(now);
                osc.stop(now + 0.5);
            }
        } catch (e) {
            console.log("Falha ao tocar sintetizador de som:", e);
        }
    }

    // Configuração do Holograma Interativo
    let thinkingInterval = null;
    const thinkingQuotes = [
        "Calculando desvio padrão das rodadas...",
        "Analisando assinatura balística do croupier...",
        "Processando teoria quântica no cilindro...",
        "Mapeando setores vizinhos da mesa...",
        "A imaginação é mais importante que o conhecimento.",
        "Deus não joga dados... mas nós analisamos a mesa.",
        "Verificando margens de proteção de risco...",
        "Avaliando probabilidade residual de acertos...",
        "Calculando Kelly ótimo para alocação...",
        "Calculando desvios e distribuições de Poisson...",
        "Monitorando dispersão estatística..."
    ];

    function setHologramState(state, customAlert = "", customQuote = "") {
        const einsteinHologram = shadowRoot.getElementById("einsteinHologram");
        if (!einsteinHologram) return;
        
        const portrait = einsteinHologram.querySelector(".einstein-hologram-portrait");
        const alertText = einsteinHologram.querySelector(".einstein-hologram-alert");
        const quoteText = einsteinHologram.querySelector(".einstein-hologram-quote");
        
        // Limpa rotações de frases anteriores
        if (thinkingInterval) {
            clearInterval(thinkingInterval);
            thinkingInterval = null;
        }

        // Reseta classes do overlay e remove cores extras do HUD
        einsteinHologram.classList.remove("state-thinking", "state-celebrating", "active");
        if (hudContainer) {
            hudContainer.classList.remove("glow-yellow");
        }

        if (state === "thinking") {
            einsteinHologram.classList.add("state-thinking");
            if (portrait) portrait.style.backgroundImage = `url('${einsteinThinkingUrl}')`;
            if (alertText) alertText.textContent = customAlert || "EINSTEIN PROCESSANDO...";
            
            const getRandomQuote = () => thinkingQuotes[Math.floor(Math.random() * thinkingQuotes.length)];
            if (quoteText) quoteText.textContent = customQuote || `"${getRandomQuote()}"`;

            // Configura rotação a cada 4.5 segundos
            thinkingInterval = setInterval(() => {
                if (einsteinHologram.classList.contains("state-thinking") && quoteText) {
                    quoteText.textContent = `"${getRandomQuote()}"`;
                }
            }, 4500);

        } else if (state === "celebrating") {
            einsteinHologram.classList.add("state-celebrating");
            if (portrait) portrait.style.backgroundImage = `url('${einsteinCelebratingUrl}')`;
            if (alertText) alertText.textContent = customAlert || "GREEN CONFIRMADO!";
            if (quoteText) quoteText.textContent = customQuote || '"E=mc² (Lucro = Massa × Consistência²)"';
            
            if (hudContainer) hudContainer.className = "einstein-hud-container glow-green";
        } else if (state === "easter-egg") {
            einsteinHologram.classList.add("active");
            if (portrait) portrait.style.backgroundImage = `url('${einsteinImgUrl}')`;
            if (alertText) alertText.textContent = customAlert || "PARADOXO DE EINSTEIN";
            if (quoteText) quoteText.textContent = customQuote || '"Ninguém vence a roleta... exceto nós."';
            if (hudContainer) hudContainer.classList.add("glow-yellow");
        } else {
            // Estado oculto (sinal ativo ou cobertura ativa para liberar visão dos dados)
            if (alertText) alertText.textContent = "";
            if (quoteText) quoteText.textContent = "";
        }
    }

    // Update UI elements based on received signals
    function processSignal(signal) {
        console.log("🎯 Sinal recebido no HUD:", signal);

        const croupierVal = shadowRoot.getElementById("croupierVal");
        const lastSpinVal = shadowRoot.getElementById("lastSpinVal");
        const entryVal = shadowRoot.getElementById("entryVal");
        const leituraVal = shadowRoot.getElementById("leituraVal");
        const kellyVal = shadowRoot.getElementById("kellyVal");
        const kellyBarFill = shadowRoot.getElementById("kellyBarFill");
        const protectionVal = shadowRoot.getElementById("protectionVal");
        const signalCard = shadowRoot.getElementById("signalCard");
        const signalStateLabel = shadowRoot.getElementById("signalStateLabel");

        // 1. Basic properties
        if (croupierVal && signal.dealer) croupierVal.textContent = signal.dealer;
        if (lastSpinVal && signal.number !== undefined) lastSpinVal.textContent = signal.number;
        
        // Tratamento de atualização de status (giros e crupiê de rotina)
        if (signal.status_tick) {
            const isCurrentlyActive = signalCard && (
                signalCard.classList.contains("active-signal") ||
                signalCard.classList.contains("active-protection")
            );
            if (!isCurrentlyActive) {
                resetSignalUI();
            }
            return;
        }
        
        // 2. Determine state and colors
        if (signal.strategy) {
            // New active entry signal
            logToConsole(`Entrada confirmada! Estratégia: ${signal.strategy}`, "success");
            playSynthSound("signal"); // Play signal alert sound
            
            // Oculta holograma para mostrar coordenadas do sinal
            setHologramState("hidden");

            if (entryVal) entryVal.textContent = signal.strategy;
            if (leituraVal) leituraVal.textContent = signal.leitura || "Leitura de IA ativa.";
            if (protectionVal) protectionVal.textContent = signal.protection || "Cobrir Zero";
            if (signalStateLabel) signalStateLabel.textContent = "SINAL ATIVO";

            // Apply suggested Kelly size
            const kellyPercent = signal.kelly_stake || 1.0;
            if (kellyVal) kellyVal.textContent = `${kellyPercent.toFixed(1)}%`;
            if (kellyBarFill) {
                const widthPercent = Math.min(100, (kellyPercent / 3.0) * 100);
                kellyBarFill.style.width = `${widthPercent}%`;
            }

            // Style Card & Container Glow
            if (hudContainer) hudContainer.className = "einstein-hud-container glow-green";
            if (signalCard) {
                signalCard.className = "einstein-signal-card active-signal";
            }

            // 3. Trigger Albert Einstein Easter Egg Hologram on high confidence signals
            let confidence = signal.confidence || 0;
            if (confidence > 0 && confidence <= 1.0) {
                confidence = confidence * 100;
            }
            if (confidence >= 90 || kellyPercent >= 2.5) {
                triggerEinsteinEasterEgg();
            }

        } else if (signal.is_protection) {
            // Martingale protection round
            logToConsole(`Rodada de Cobertura / Martingale ativa (G${signal.attempt || 1})!`, "warn");
            playSynthSound("protection"); // Play warning chime
            
            // Oculta holograma para mostrar coordenadas de proteção
            setHologramState("hidden");

            if (entryVal) entryVal.textContent = `COBERTURA G${signal.attempt || 1}`;
            if (leituraVal) leituraVal.textContent = "Aguardando confirmação do green.";
            if (signalStateLabel) signalStateLabel.textContent = "PROTEÇÃO";
            
            if (hudContainer) hudContainer.className = "einstein-hud-container glow-magenta";
            if (signalCard) {
                signalCard.className = "einstein-signal-card active-protection";
            }
        } else {
            // Reset state (Win/Loss or normal monitoring)
            if (signal.reset) {
                if (signal.outcome === "win") {
                    logToConsole("Green confirmado! Parabéns!", "success");
                    playSynthSound("win"); // Play satisfy arcade chime
                    
                    // Mostra holograma de comemoração (olhos 0 0 verdes e língua pra fora)
                    setHologramState("celebrating", "GREEN CONFIRMADO!", '"A relatividade do lucro: Lucro = Massa x Consistência²"');
                    
                    // Retorna para o estado pensando após 4.5 segundos
                    setTimeout(() => {
                        const einsteinHologram = shadowRoot.getElementById("einsteinHologram");
                        if (einsteinHologram && einsteinHologram.classList.contains("state-celebrating")) {
                            resetSignalUI();
                        }
                    }, 4500);
                    return; // Retorna para evitar resetUI imediato
                } else if (signal.outcome === "loss") {
                    logToConsole("Loss registrado. Pausando entradas...", "error");
                } else {
                    logToConsole("Mesa normalizada. Monitorando...");
                }
            }
            resetSignalUI();
        }
    }

    // Trigger winking Einstein overlay screen
    function triggerEinsteinEasterEgg() {
        logToConsole("Einstein Mode: Desafiando a física clássica!", "warn");
        setHologramState("easter-egg");

        // Automatically hide it after 3.0 seconds so user can see coordinates again
        setTimeout(() => {
            const einsteinHologram = shadowRoot.getElementById("einsteinHologram");
            if (einsteinHologram && einsteinHologram.classList.contains("active")) {
                setHologramState("hidden");
            }
        }, 3000);
    }

    // Reset UI to standard monitoring state
    function resetSignalUI() {
        const entryVal = shadowRoot.getElementById("entryVal");
        const leituraVal = shadowRoot.getElementById("leituraVal");
        const kellyVal = shadowRoot.getElementById("kellyVal");
        const kellyBarFill = shadowRoot.getElementById("kellyBarFill");
        const protectionVal = shadowRoot.getElementById("protectionVal");
        const signalCard = shadowRoot.getElementById("signalCard");
        const signalStateLabel = shadowRoot.getElementById("signalStateLabel");

        if (entryVal) entryVal.textContent = "Monitorando Mesa...";
        if (leituraVal) leituraVal.textContent = "Aguardando sinal verde da IA.";
        if (protectionVal) protectionVal.textContent = "-";
        if (kellyVal) kellyVal.textContent = "0.0%";
        if (kellyBarFill) kellyBarFill.style.width = "0%";
        if (signalStateLabel) signalStateLabel.textContent = "Estado do Sistema";

        if (hudContainer) hudContainer.className = "einstein-hud-container";
        if (signalCard) signalCard.className = "einstein-signal-card";
        
        // Ativa o estado de processamento/thinking do Einstein
        setHologramState("thinking");
    }

    // Listen to messages from background service worker
    chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
        if (message.action === "toggleHUD") {
            if (hudContainer) {
                if (hudContainer.style.display === "none") {
                    hudContainer.style.display = "flex";
                    logToConsole("Painel HUD ativado pelo ícone do Chrome.");
                } else {
                    hudContainer.style.display = "none";
                }
            }
        } else if (message.type === "connection_status") {
            updateConnectionStatus(message.connected);
        } else if (message.type === "signal") {
            processSignal(message.signal);
        }
    });

    // Keep MV3 background service worker alive while game tab is active
    let keepAlivePort = null;
    function keepServiceWorkerAlive() {
        // Se a extensão foi recarregada/desativada, o contexto é invalidado.
        // Devemos parar o loop para não inundar o console/erros do Chrome.
        if (!chrome.runtime || !chrome.runtime.id) {
            console.log("HUD: Contexto da extensão invalidado. Parando keep-alive.");
            return;
        }
        if (keepAlivePort) {
            try { keepAlivePort.disconnect(); } catch (e) {}
        }
        try {
            keepAlivePort = chrome.runtime.connect({ name: "einstein-hud-keepalive" });
            keepAlivePort.onDisconnect.addListener(() => {
                if (!chrome.runtime || !chrome.runtime.id) return;
                console.log("HUD: Keep-alive port disconnected. Reconnecting in 1s...");
                setTimeout(keepServiceWorkerAlive, 1000);
            });
        } catch (e) {
            if (!chrome.runtime || !chrome.runtime.id) return;
            console.log("HUD: Erro ao conectar port de keep-alive:", e);
            setTimeout(keepServiceWorkerAlive, 2000);
        }
    }

    // Initialize extension
    initUI();
    connectSocket();
    keepServiceWorkerAlive();

})();
