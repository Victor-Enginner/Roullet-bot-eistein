
document.addEventListener('DOMContentLoaded', () => {
    // --- CONFIGURAÇÃO GERAL E VARIÁVEIS DE ESTADO ---
    let WEBSOCKET_URL = 'ws://localhost:8765'; // Endereço fixo de teste
    let TOKEN = 'win_secret_2024'; // Token fixo
    const DEFAULT_RATE = 1.0;
    
    const LAST_SIGNAL = document.getElementById('last-number') || document.getElementById('ultimo-sinal');
    const HISTORY_LIST = document.getElementById('history-list') || document.getElementById('historico-lista');
    const VOICE_SPEED_FIELD = document.getElementById('cfg-rate');
    
    let socket;
    let vozAtivada = true;
    let voicesLoaded = false;

    // Verifica DOM
    if (!LAST_SIGNAL) console.warn('Elemento #last-number não encontrado');
    if (!HISTORY_LIST) console.warn('Elemento #history-list não encontrado');

    // Carrega voices
    window.speechSynthesis.onvoiceschanged = () => { voicesLoaded = true; };

    // --- FUNÇÃO DE VOZ INDESTRUTÍVEL ---
    function falar(texto) {
        console.log('🎤 Tentativa de fala:', texto);
        
        if (!('speechSynthesis' in window) || !voicesLoaded) {
            console.error("SpeechSynthesis não pronto ou não suportado.");
            return;
        }
        
        if (!vozAtivada) {
            console.log("Voz desativada.");
            return;
        }

        window.speechSynthesis.cancel();
        
        const rate = (VOICE_SPEED_FIELD ? parseFloat(VOICE_SPEED_FIELD.value) : DEFAULT_RATE) || DEFAULT_RATE;
        console.log('Velocidade usada:', rate);
        
        const utterance = new SpeechSynthesisUtterance(texto);
        utterance.lang = 'pt-BR';
        utterance.rate = rate;
        utterance.pitch = 0.9;
        utterance.volume = 1.0;
        
        const ptVoices = window.speechSynthesis.getVoices().filter(v => v.lang.startsWith('pt'));
        if (ptVoices.length > 0) {
            utterance.voice = ptVoices[0];
        }
        
        utterance.onstart = () => console.log('🔊 Fala INICIADA');
        utterance.onend = () => console.log('✅ Fala CONCLUÍDA');
        utterance.onerror = (e) => console.error('❌ Erro fala:', e.error, '| Clique na tela!');
        
        window.speechSynthesis.speak(utterance);
    }

    // --- WEBSOCKET INDestrutível ---
    function connectWebSocket() {
        console.log('🔄 Conectando WS:', WEBSOCKET_URL);
        socket = new WebSocket(WEBSOCKET_URL);

        socket.onopen = () => {
            console.log('✅ WS ABERTO');
            socket.send(JSON.stringify({ type: 'auth', token: TOKEN }));
            console.log('🔑 TOKEN enviado:', TOKEN);
        };

        socket.onmessage = (event) => {
            console.log('📦 Pacote Bruto Recebido:', event.data); // PRIMEIRA LINHA!
            
            try {
                const message = JSON.parse(event.data);
                
                if (message.type === 'signal') {
                    console.log('🚨 SINAL válido:', message);
                    
                    // UI segura
                    if (LAST_SIGNAL) {
                        LAST_SIGNAL.textContent = message.number;
                    }
                    
                    // Histórico seguro
                    if (HISTORY_LIST) {
                        const item = document.createElement('li');
                        item.textContent = `${message.number} (${message.strategy})`;
                        HISTORY_LIST.insertBefore(item, HISTORY_LIST.firstChild);
                        
                        if (HISTORY_LIST.children.length > 20) HISTORY_LIST.removeChild(HISTORY_LIST.lastChild);
                    }
                    
                    // Fala
                    falar(`Número ${message.number}. Estratégia ${message.strategy}`);
                } else {
                    console.log('Mensagem não-signal:', message.type);
                }
            } catch (parseError) {
                console.error('❌ JSON inválido:', parseError, '| Bruto:', event.data);
            }
        };

        socket.onclose = () => {
            console.log('🔌 WS fechado. Reconecta 3s...');
            setTimeout(connectWebSocket, 3000);
        };

        socket.onerror = (err) => console.error('❌ WS erro:', err);
    }

    // Bypass áudio
    document.addEventListener('click', () => {
        console.log('👆 Tela clicada - Áudio liberado!');
    }, {once: true});

    // Toggle voz global
    window.toggleVoice = () => {
        vozAtivada = !vozAtivada;
        console.log('Voz', vozAtivada ? 'ATIVADA' : 'DESATIVADA');
    };

    // Inicializa
    connectWebSocket();
    console.log('🚀 PWA inicializado. Clique para áudio!');
});


