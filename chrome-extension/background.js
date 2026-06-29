// Einstein Roulette AI HUD - Background Script (Service Worker)
const serverWsUrl = "ws://localhost:4000";
let socket = null;
let isConnected = false;

// OTIMIZAÇÃO: rastreia apenas as abas que de fato têm o HUD ativo (via porta
// keep-alive). Evita o chrome.tabs.query({}) em TODAS as abas a cada sinal
// (status_tick dispara a cada giro -> varredura global desnecessária).
const activeTabs = new Set();

// Connect to native WebSocket bridge
function connectSocket() {
    if (socket && (socket.readyState === WebSocket.CONNECTING || socket.readyState === WebSocket.OPEN)) {
        return;
    }

    console.log("Background: Conectando ao bridge local...");
    socket = new WebSocket(serverWsUrl);

    socket.onopen = () => {
        console.log("Background: Conectado ao bridge local!");
        isConnected = true;
        broadcastToTabs({ type: "connection_status", connected: true });
    };

    socket.onmessage = (event) => {
        try {
            const signal = JSON.parse(event.data);
            // Keep-alive da ponte: só serve pra manter o service worker acordado.
            // Não é um sinal de roleta -> ignora (não repassa às abas).
            if (signal && signal.type === "ping") {
                return;
            }
            console.log("Background: Sinal recebido do bridge:", signal);
            broadcastToTabs({ type: "signal", signal: signal });
        } catch (e) {
            console.error("Erro ao fazer parse do sinal:", e);
        }
    };

    socket.onclose = () => {
        console.log("Background: Desconectado do bridge. Reabrando conexão em 3s...");
        isConnected = false;
        broadcastToTabs({ type: "connection_status", connected: false });
        
        // Reconnect loop
        setTimeout(connectSocket, 3000);
    };

    socket.onerror = (err) => {
        console.log("Background: Erro de WebSocket local:", err);
    };
}

// Broadcast messages only to tabs that have the HUD content script active.
function broadcastToTabs(message) {
    if (activeTabs.size === 0) {
        // Fallback raro (ex.: 1º sinal antes do keep-alive registrar a aba):
        // varre uma vez e deixa o keep-alive popular activeTabs daí em diante.
        chrome.tabs.query({}, (tabs) => {
            for (let tab of tabs) {
                if (tab.id) {
                    chrome.tabs.sendMessage(tab.id, message).catch(() => {});
                }
            }
        });
        return;
    }
    for (const tabId of activeTabs) {
        chrome.tabs.sendMessage(tabId, message).catch(() => {
            // Aba fechou/navegou sem disparar onDisconnect: remove do set.
            activeTabs.delete(tabId);
        });
    }
}

// Initialize connection
connectSocket();

// BACKSTOP anti-suspensão MV3: um alarme periódico acorda o service worker e
// garante que o socket esteja conectado. Combinado com o ping de 20s da ponte,
// elimina os ciclos de "reconectado a cada ~30s" que atrasavam os sinais.
chrome.alarms.create("einstein-keepalive", { periodInMinutes: 0.4 }); // ~24s
chrome.alarms.onAlarm.addListener((alarm) => {
    if (alarm.name !== "einstein-keepalive") return;
    if (!socket || socket.readyState === WebSocket.CLOSED || socket.readyState === WebSocket.CLOSING) {
        console.log("Background: [alarm] socket caído, reconectando...");
        connectSocket();
    } else if (socket.readyState === WebSocket.OPEN) {
        // Atividade leve pra reforçar o keep-alive do worker.
        try { socket.send(JSON.stringify({ type: "ping_client" })); } catch (e) {}
    }
});

// Connect on events
chrome.runtime.onStartup.addListener(connectSocket);
chrome.runtime.onInstalled.addListener(connectSocket);

// Listen to messages from content scripts (e.g. status requests)
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.action === "request_status") {
        sendResponse({ connected: isConnected });
    }
});

// Keep-alive port connection to prevent suspension in MV3
chrome.runtime.onConnect.addListener((port) => {
    if (port.name === "einstein-hud-keepalive") {
        const tabId = port.sender && port.sender.tab && port.sender.tab.id;
        if (tabId) activeTabs.add(tabId);
        console.log("Background: Keep-alive port connected. Aba:", tabId);
        port.onDisconnect.addListener(() => {
            if (tabId) activeTabs.delete(tabId);
            console.log("Background: Keep-alive port disconnected. Aba:", tabId);
        });
    }
});

// Handles toolbar icon clicks to toggle HUD
chrome.action.onClicked.addListener((tab) => {
    if (tab && tab.id) {
        // Tenta enviar mensagem de toggle
        chrome.tabs.sendMessage(tab.id, { action: "toggleHUD" }).catch(err => {
            console.log("Content script não inicializado na aba. Injetando...");
            
            // Injeta o content script em tempo de execução
            chrome.scripting.executeScript({
                target: { tabId: tab.id, allFrames: true },
                files: ["content.js"]
            }).then(() => {
                chrome.scripting.insertCSS({
                    target: { tabId: tab.id, allFrames: true },
                    files: ["hud.css"]
                });
                
                // Aguarda inicialização e envia status e abertura
                setTimeout(() => {
                    chrome.tabs.sendMessage(tab.id, { action: "toggleHUD" }).catch(() => {});
                    chrome.tabs.sendMessage(tab.id, { type: "connection_status", connected: isConnected }).catch(() => {});
                }, 250);
            }).catch(injectErr => {
                console.log("Injeção bloqueada (aba interna do Chrome):", injectErr);
            });
        });
    }
});
