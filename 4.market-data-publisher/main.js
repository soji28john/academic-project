// Market Data Publisher Service for Kubernetes deployment
// Receives orders and executions from Order Manager, maintains order book, and broadcasts updates via WebSocket
import express from 'express';
import http from 'http';
import { WebSocketServer, WebSocket } from 'ws';

const PORT = process.env.PORT || 3003;
// Use root path for WebSocket to simplify external client connections
const WS_PATH = process.env.WS_PATH || '/';

const orderBook = new Map();

const app = express();
const server = http.createServer(app);
const wss = new WebSocketServer({ server, path: WS_PATH });

app.use(express.json());

// Health endpoints for Kubernetes probes
app.get('/healthz', (req, res) => {
  res.status(200).send('OK');
});

app.get('/readyz', (req, res) => {
  // Check if WebSocket server is operational
  if (wss && server.listening) {
    res.status(200).send('READY');
  } else {
    res.status(503).send('Service not ready');
  }
});

// Handle WebSocket connections
wss.on('connection', (ws, req) => {
  console.log('Dashboard client connected from:', req.socket.remoteAddress);
  
  // Send current order book state to newly connected client
  if (orderBook.size > 0) {
    ws.send(JSON.stringify({
      type: 'orderBookUpdate',
      orderBook: Object.fromEntries(orderBook)
    }));
  }
  
  ws.on('close', () => {
    console.log('Dashboard client disconnected');
  });
  
  ws.on('error', (error) => {
    console.error('WebSocket error:', error.message);
  });
});

// Broadcast helper function
function broadcast(data) {
  const msg = JSON.stringify(data);
  wss.clients.forEach((client) => {
    if (client.readyState === WebSocket.OPEN) {
      client.send(msg);
    }
  });
}

// POST /data endpoint - receives orders and executions from Order Manager
app.post('/data', (req, res) => {
  try {
    const { order, askExecutions, bidExecutions } = req.body;

    // Handle incoming order
    if (order) {
      if (!orderBook.has(order.symbol)) {
        orderBook.set(order.symbol, { asks: [], bids: [] });
      }
      const book = orderBook.get(order.symbol);
      if (order.side === 'ask') {
        book.asks.push(order);
        // Sort asks by price (ascending - best ask first)
        book.asks.sort((a, b) => a.price - b.price);
      } else if (order.side === 'bid') {
        book.bids.push(order);
        // Sort bids by price (descending - best bid first)
        book.bids.sort((a, b) => b.price - a.price);
      } else {
        console.error('Market Data Publisher - Invalid order side:', order.side);
        return res.status(400).send('Invalid order side');
      }
      console.log(`Market Data Publisher - Order added: ${order.symbol} ${order.side} ${order.quantity}@${order.price}`);
    }

    // Handle executions (remove filled orders from order book)
    if (askExecutions && askExecutions.length > 0) {
      const symbol = askExecutions[0].symbol;
      const book = orderBook.get(symbol);
      if (book) {
        askExecutions.forEach(exec => {
          const index = book.asks.findIndex(o => o.orderId === exec.orderId);
          if (index !== -1) {
            book.asks.splice(index, 1);
            console.log(`Market Data Publisher - Ask execution removed: ${exec.orderId}`);
          }
        });
      }
    }

    if (bidExecutions && bidExecutions.length > 0) {
      const symbol = bidExecutions[0].symbol;
      const book = orderBook.get(symbol);
      if (book) {
        bidExecutions.forEach(exec => {
          const index = book.bids.findIndex(o => o.orderId === exec.orderId);
          if (index !== -1) {
            book.bids.splice(index, 1);
            console.log(`Market Data Publisher - Bid execution removed: ${exec.orderId}`);
          }
        });
      }
    }

    // Broadcast updated order book to all connected clients
    broadcast({
      type: 'orderBookUpdate',
      orderBook: Object.fromEntries(orderBook),
      timestamp: new Date().toISOString()
    });

    res.status(200).send('Data processed and published');

  } catch (err) {
    console.error('Market Data Publisher - Error processing data:', err);
    res.status(500).send('Internal Server Error');
  }
});

// Graceful shutdown handling
let isShuttingDown = false;

function gracefulShutdown() {
  if (isShuttingDown) return;
  isShuttingDown = true;
  
  console.log('Market Data Publisher - Shutting down gracefully...');
  
  // Close all WebSocket connections
  wss.clients.forEach(client => {
    if (client.readyState === WebSocket.OPEN) {
      client.close(1001, 'Server shutting down');
    }
  });
  
  // Close WebSocket server
  wss.close(() => {
    console.log('WebSocket server closed');
    
    // Close HTTP server
    server.close(() => {
      console.log('HTTP server closed');
      process.exit(0);
    });
  });
  
  // Force shutdown after 10 seconds
  setTimeout(() => {
    console.error('Could not close gracefully, forcing shutdown');
    process.exit(1);
  }, 10000);
}

process.on('SIGTERM', gracefulShutdown);
process.on('SIGINT', gracefulShutdown);

// Handle uncaught exceptions
process.on('uncaughtException', (error) => {
  console.error('Uncaught Exception:', error);
  gracefulShutdown();
});

process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
  gracefulShutdown();
});

// Start server
server.listen(PORT, () => {
  console.log(`Market Data Publisher running on port ${PORT}`);
  console.log(`WebSocket available at ws://localhost:${PORT}${WS_PATH}`);
});