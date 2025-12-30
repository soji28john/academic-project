// Order Manager Service for Kubernetes deployment
const express = require('express');

// Import matching engine components
const matchingEngineModule = require('./matching-engine');
const MatchingEngine = matchingEngineModule.MatchingEngine;
const EngineOrder = matchingEngineModule.EngineOrder;

const app = express();
app.use(express.json());

// Environment variables
const PORT = process.env.PORT || 3002;
const MARKET_DATA_PUBLISHER_URL = process.env.MARKET_DATA_PUBLISHER_URL || 'http://market-data-publisher-service:3003/data';
const STOCK_SYMBOLS = (process.env.STOCK_SYMBOLS || 'AAPL,AMZN,GOOGL,MSFT').split(',');

// Initialize matching engine and counters
let matchingEngine;
let orderCounter = 0;
let secnumCounter = 0; // Sequential number for orders

try {
  matchingEngine = new MatchingEngine(STOCK_SYMBOLS);
  console.log('Matching engine initialized with symbols:', STOCK_SYMBOLS);
} catch (error) {
  console.error('Failed to initialize matching engine:', error.message);
  process.exit(1);
}

// Graceful shutdown handling
let shuttingDown = false;
let server;

process.on('SIGTERM', () => {
  console.log('Order Manager - SIGTERM received. Shutting down gracefully...');
  shuttingDown = true;
  server.close(() => {
    console.log('Order Manager - Server closed. Exiting.');
    process.exit(0);
  });
});

// Health endpoints for Kubernetes probes
app.get('/healthz', (req, res) => {
  if (shuttingDown) {
    return res.status(503).send('Service shutting down');
  }
  res.status(200).send('OK');
});

app.get('/readyz', (req, res) => {
  if (shuttingDown) {
    return res.status(503).send('Service shutting down');
  }
  res.status(200).send('READY');
});

// Receive parsed order record from Client Gateway
app.post('/order', async (req, res) => {
  if (shuttingDown) {
    return res.status(503).send('Service shutting down');
  }

  try {
    console.log('Order Manager - Received order:', req.body);

    // Extract only the required fields, ignore: user_id, timestamp_ns, trader_type
    const { symbol, side, price, quantity } = req.body;

    // Validate required fields
    if (
      typeof symbol !== 'string' ||
      typeof side !== 'string' ||
      typeof price !== 'number' ||
      typeof quantity !== 'number'
    ) {
      console.error('Order Manager - Missing or invalid required fields');
      return res.status(400).send('Missing or invalid required fields');
    }

    // Generate sequential secnum for this order
    const secnum = ++secnumCounter;

    // Create EngineOrder with the required fields + sequential secnum
    const order = new EngineOrder(symbol, side, price, quantity, secnum);
    order.orderId = ++orderCounter;

    console.log(`Order Manager - Processing order ${order.orderId} (secnum: ${secnum}): ${symbol} ${side} ${quantity}@${price}`);

    // Store the original order for sending to Market Data Publisher
    const originalOrderForMDP = { ...order };

    // Execute matching engine - this is synchronous and will call the callback with executions
    matchingEngine.execute(order, async (askExecutions, bidExecutions) => {
      try {
        if ((askExecutions && askExecutions.length > 0) || (bidExecutions && bidExecutions.length > 0)) {
          const execPayload = { 
            askExecutions: askExecutions || [], 
            bidExecutions: bidExecutions || [] 
          };
          console.log('Order Manager - Sending executions:', execPayload);

          // Send executions to Market Data Publisher
          const execRes = await fetch(MARKET_DATA_PUBLISHER_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(execPayload),
          });

          if (!execRes.ok) {
            console.error(`Order Manager - Execution post error: ${execRes.status} ${execRes.statusText}`);
          } else {
            console.log('Order Manager - Executions sent successfully');
          }
        }
      } catch (error) {
        console.error('Order Manager - Error sending executions:', error.message);
      }
    });

    // Send original order to Market Data Publisher (this happens immediately after execute call)
    try {
      const orderPayload = { order: originalOrderForMDP };
      console.log('Order Manager - Sending order to Market Data Publisher:', orderPayload);

      const orderRes = await fetch(MARKET_DATA_PUBLISHER_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(orderPayload),
      });

      if (!orderRes.ok) {
        console.error(`Order Manager - Order post error: ${orderRes.status} ${orderRes.statusText}`);
      } else {
        console.log('Order Manager - Order sent successfully to Market Data Publisher');
      }
    } catch (error) {
      console.error('Order Manager - Error sending order to Market Data Publisher:', error.message);
    }

    // Respond to Client Gateway immediately (don't wait for matching engine callback)
    res.status(200).send('Order processed and sent to Market Data Publisher');

  } catch (error) {
    console.error('Order Manager - Internal error:', error.message);
    console.error('Error details:', error.stack);
    res.status(500).send('Internal Server Error: ' + error.message);
  }
});

// Start server
server = app.listen(PORT, () => {
  console.log(`Order Manager is running on port ${PORT}`);
  console.log(`Market Data Publisher URL: ${MARKET_DATA_PUBLISHER_URL}`);
});

// Handle uncaught exceptions
process.on('uncaughtException', (error) => {
  console.error('Uncaught Exception:', error);
  process.exit(1);
});

process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
  process.exit(1);
});