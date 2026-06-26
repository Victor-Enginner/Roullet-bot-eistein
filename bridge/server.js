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

app.post('/api/webhook/signal', (req, res) => {
  const signal = req.body;
  // Broadcast signal to all native WebSocket clients
  wss.clients.forEach((client) => {
    if (client.readyState === WebSocket.OPEN) {
      client.send(JSON.stringify(signal));
    }
  });
  res.json({ status: 'received', signal });
});

wss.on('connection', (ws) => {
  console.log('Client connected');
  ws.on('close', () => {
    console.log('Client disconnected');
  });
});

server.listen(port, () => {
  console.log(`Bridge server running on port ${port}`);
});
