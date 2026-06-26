const express = require('express');
const { createServer } = require('http');
const { Server } = require('socket.io');
const cors = require('cors');

const app = express();
const port = 4000;

app.use(cors());
app.use(express.json());

const server = createServer(app);
const io = new Server(server, {
  cors: {
    origin: "*",
    methods: ["GET", "POST"]
  }
});

app.post('/api/webhook/signal', (req, res) => {
  const signal = req.body;
  // Broadcast to WebSocket clients
  io.emit('signal', signal);
  res.json({ status: 'received', signal });
});

io.on('connection', (socket) => {
  console.log('Client connected:', socket.id);

  socket.on('disconnect', () => {
    console.log('Client disconnected:', socket.id);
  });
});

server.listen(port, () => {
  console.log(`Bridge server running on port ${port}`);
});
