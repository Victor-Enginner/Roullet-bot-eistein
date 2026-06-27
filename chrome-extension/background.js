// Einstein Roulette AI HUD - Background Script (Service Worker)
const serverWsUrl = "ws://localhost:4000";
let socket = null;
let isConnected = false;

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

// Broadcast messages to all content script frames
function broadcastToTabs(message) {
    chrome.tabs.query({}, (tabs) => {
        for (let tab of tabs) {
            if (tab.id) {
                chrome.tabs.sendMessage(tab.id, message).catch(() => {
                    // Ignore errors for tabs without content scripts
                });
            }
        }
    });
}

// Initialize connection
connectSocket();

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
        console.log("Background: Keep-alive port connected.");
        port.onDisconnect.addListener(() => {
            console.log("Background: Keep-alive port disconnected.");
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
