// Einstein Roulette AI HUD - Background Script (Service Worker)
chrome.action.onClicked.addListener((tab) => {
    if (tab && tab.id) {
        // Tenta enviar a mensagem para o content script
        chrome.tabs.sendMessage(tab.id, { action: "toggleHUD" }).catch(err => {
            console.log("Falha ao comunicar com o content script. Injetando dinamicamente...");
            
            // Injeta o CSS e JS em tempo de execução
            chrome.scripting.executeScript({
                target: { tabId: tab.id },
                files: ["socket.io.min.js", "content.js"]
            }).then(() => {
                chrome.scripting.insertCSS({
                    target: { tabId: tab.id },
                    files: ["hud.css"]
                });
                console.log("Injetado com sucesso! Abrindo HUD...");
                
                // Aguarda 250ms para inicialização e envia o sinal de abertura
                setTimeout(() => {
                    chrome.tabs.sendMessage(tab.id, { action: "toggleHUD" }).catch(e => {
                        console.log("Erro ao forçar abertura pós-injeção:", e);
                    });
                }, 250);
            }).catch(injectErr => {
                console.log("Não é possível injetar nesta página (páginas internas são bloqueadas):", injectErr);
            });
        });
    }
});
