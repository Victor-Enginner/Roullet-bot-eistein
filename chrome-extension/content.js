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
                        <div class="einstein-hologram-portrait" style="background-image: url('${einsteinImgUrl}');"></div>
                        <div class="einstein-hologram-alert">PARADOXO DE EINSTEIN</div>
                        <div class="einstein-hologram-quote">"Ninguém vence a roleta... exceto nós."</div>
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

    // Connect to local Socket.io bridge
    function connectSocket() {
        logToConsole("Tentando estabelecer conexão com o bridge...");
        
        // io is globally available because we load socket.io.min.js first in manifest content scripts
        if (typeof io === "undefined") {
            logToConsole("Erro: Socket.io client não carregado.", "error");
            return;
        }

        socket = io(serverUrl, {
            reconnectionAttempts: 10,
            reconnectionDelay: 2000
        });

        const statusDot = shadowRoot.getElementById("statusDot");

        socket.on("connect", () => {
            logToConsole("Conectado ao servidor da ponte!", "success");
            if (statusDot) statusDot.className = "einstein-hud-dot connected";
        });

        socket.on("disconnect", () => {
            logToConsole("Desconectado do servidor da ponte.", "error");
            if (statusDot) statusDot.className = "einstein-hud-dot";
            resetSignalUI();
        });

        // Receive real-time signals from the Python/TypeScript bridge
        socket.on("signal", (signal) => {
            processSignal(signal);
        });
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
        
        // 2. Determine state and colors
        if (signal.strategy) {
            // New active entry signal
            logToConsole(`Entrada confirmada! Estratégia: ${signal.strategy}`, "success");
            
            if (entryVal) entryVal.textContent = signal.strategy;
            if (leituraVal) leituraVal.textContent = signal.leitura || "Leitura de IA ativa.";
            if (protectionVal) protectionVal.textContent = signal.protection || "Cobrir Zero";
            if (signalStateLabel) signalStateLabel.textContent = "SINAL ATIVO";

            // Apply suggested Kelly size
            const kellyPercent = signal.kelly_stake || 1.0;
            if (kellyVal) kellyVal.textContent = `${kellyPercent.toFixed(1)}%`;
            if (kellyBarFill) {
                // Kelly is usually between 0.5% and 3.0%. Map 3% to 100% width
                const widthPercent = Math.min(100, (kellyPercent / 3.0) * 100);
                kellyBarFill.style.width = `${widthPercent}%`;
            }

            // Style Card & Container Glow
            hudContainer.className = "einstein-hud-container glow-green";
            if (signalCard) {
                signalCard.className = "einstein-signal-card active-signal";
            }

            // 3. Trigger Albert Einstein Easter Egg Hologram on high confidence signals
            let confidence = signal.confidence || 0;
            if (confidence > 0 && confidence <= 1.0) {
                confidence = confidence * 100; // Convert 0.9 to 90
            }
            if (confidence >= 90 || kellyPercent >= 2.5) {
                triggerEinsteinEasterEgg();
            }

        } else if (signal.is_protection) {
            // Martingale protection round
            logToConsole(`Rodada de Cobertura / Martingale ativa!`, "warn");
            
            if (entryVal) entryVal.textContent = "COBERTURA ACT";
            if (leituraVal) leituraVal.textContent = "Aguardando confirmação do green.";
            if (signalStateLabel) signalStateLabel.textContent = "PROTEÇÃO";
            
            hudContainer.className = "einstein-hud-container glow-magenta";
            if (signalCard) {
                signalCard.className = "einstein-signal-card active-protection";
            }
        } else {
            // Reset state (Win/Loss or normal monitoring)
            logToConsole("Mesa normalizada. Monitorando...");
            resetSignalUI();
        }
    }

    // Trigger winking Einstein overlay screen
    function triggerEinsteinEasterEgg() {
        const einsteinHologram = shadowRoot.getElementById("einsteinHologram");
        if (!einsteinHologram) return;

        logToConsole("Einstein Mode: Desafiando a física clássica!", "warn");
        
        // Activate overlay
        einsteinHologram.classList.add("active");
        hudContainer.classList.add("glow-yellow");

        // Automatically hide it after 3.5 seconds so user can see coordinates again
        setTimeout(() => {
            einsteinHologram.classList.remove("active");
            hudContainer.classList.remove("glow-yellow");
        }, 3500);
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

        hudContainer.className = "einstein-hud-container";
        if (signalCard) signalCard.className = "einstein-signal-card";
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
        }
    });

    // Initialize extension
    initUI();
    connectSocket();

})();
