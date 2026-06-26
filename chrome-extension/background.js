// Einstein Roulette AI HUD - Background Script (Service Worker)
chrome.action.onClicked.addListener((tab) => {
    // Send toggle message to content script on the active tab
    if (tab && tab.id) {
        chrome.tabs.sendMessage(tab.id, { action: "toggleHUD" }).catch(err => {
            console.log("Não é possível injetar em páginas internas do Chrome:", err);
        });
    }
});
