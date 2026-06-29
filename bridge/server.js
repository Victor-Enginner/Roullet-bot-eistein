const express = require('express');
const { createServer } = require('http');
const WebSocket = require('ws');
const cors = require('cors');

const app = express();
const port = 4000;

app.use(cors());
app.use(express.json());

const server = createServer(app);
const wss = new WebSocket.Server({ server });

// Guarda o último sinal "de verdade" (não status_tick) para REPLAY em quem
// reconectar. Se um sinal chegou durante um micro-gap do socket, o cliente
// ainda o recebe assim que reconecta (dentro da janela). Evita "sinal perdido".
let lastSignal = null;

app.post('/api/webhook/signal', (req, res) => {
  const signal = req.body;

  if (signal && !signal.status_tick) {
    lastSignal = { signal, at: Date.now() };
  }

  let delivered = 0;
  wss.clients.forEach((client) => {
    if (client.readyState === WebSocket.OPEN) {
      client.send(JSON.stringify(signal));
      delivered++;
    }
  });
  res.json({ status: 'received', delivered });
});

wss.on('connection', (ws) => {
  ws.isAlive = true;
  ws.on('pong', () => { ws.isAlive = true; });
  console.log('Client connected');

  // REPLAY: se há um sinal recente (< 8s), reenvia para o cliente que acabou
  // de (re)conectar. Cobre o caso de um sinal ter chegado enquanto o service
  // worker estava reacordando. O cliente deduplica por timestamp.
  if (lastSignal && (Date.now() - lastSignal.at) < 8000) {
    try { ws.send(JSON.stringify(lastSignal.signal)); } catch (e) {}
  }

  ws.on('close', () => console.log('Client disconnected'));
});

// KEEP-ALIVE (anti-suspensão MV3): enviar uma mensagem WS a cada 20s mantém o
// service worker do Chrome vivo (atividade WS reseta o timer de inatividade de
// 30s). Sem isso, o background dorme e o socket cai a cada ~30s -> sinais
// atrasam. Mandamos um {type:"ping"} que o background ignora.
const KEEPALIVE_MS = 20000;
setInterval(() => {
  const ping = JSON.stringify({ type: 'ping', t: Date.now() });
  wss.clients.forEach((client) => {
    if (client.readyState === WebSocket.OPEN) {
      try { client.send(ping); } catch (e) {}
    }
  });
}, KEEPALIVE_MS);

// HEARTBEAT a nível de protocolo: derruba sockets zumbis (que não respondem
// pong) para a lista de clientes não acumular conexões mortas.
const HEARTBEAT_MS = 25000;
setInterval(() => {
  wss.clients.forEach((ws) => {
    if (ws.isAlive === false) return ws.terminate();
    ws.isAlive = false;
    try { ws.ping(); } catch (e) {}
  });
}, HEARTBEAT_MS);

server.listen(port, () => {
  console.log(`Bridge server running on port ${port} (keep-alive ${KEEPALIVE_MS}ms)`);
});
