// Client Gateway for Kubernetes deployment
const express = require('express');
const app = express();

// Use PORT from environment or default to 3001 (will be mapped via service)
const PORT = process.env.PORT || 3001;
// Order Manager service URL in Kubernetes cluster
const ORDER_MANAGER_URL = process.env.ORDER_MANAGER_URL || "http://order-manager-service:3002/order";

let server;

// Middleware to parse JSON request bodies
app.use(express.json());

// Health endpoints for Kubernetes liveness/readiness probes
app.get('/healthz', (req, res) => res.status(200).send('OK'));

app.get('/readyz', async (req, res) => {
    try {
        // Use AbortController for timeout functionality
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 5000);
        
        // Simple request to check if Order Manager is responsive
        const resp = await fetch(ORDER_MANAGER_URL, { 
            method: 'HEAD',
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        if (resp.ok) return res.status(200).send('READY');
        res.status(500).send('Downstream not ready');
    } catch (err) {
        console.error('Readiness probe failed:', err.message);
        if (err.name === 'AbortError') {
            res.status(500).send('Downstream timeout');
        } else {
            res.status(500).send('Downstream not reachable');
        }
    }
});

// Route to receive orders from Client Order Streamer
app.post('/order', async (req, res) => {
    console.log('Client Gateway - Received order:', req.body);
    
    const { symbol, side, price, quantity } = req.body;
    // Type-check the order fields (fixed syntax error - removed extra parenthesis)
    if (
        typeof symbol !== 'string' ||
        typeof side !== 'string' ||
        typeof price !== 'number' ||
        typeof quantity !== 'number'
    ) {
        console.log('Client Gateway - Invalid order fields');
        return res.status(400).json({ error: 'Invalid order fields' });
    }

    //console.log('>>> >>> Forwarding order to Order Manager URL:', ORDER_MANAGER_URL);   //Temp for debugging
    try {
        // Forward order to Order Manager
        const forwardResponse = await fetch(ORDER_MANAGER_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(req.body),
        });

        // Read response body once as text, then try parsing JSON
        const rawData = await forwardResponse.text();
        console.log('>>> >>> Next line: const rawData = await forwardResponse.text');
        let data;
        try {
            data = JSON.parse(rawData); // If valid JSON
        } catch (e) {
            data = rawData; // Otherwise fallback to plain text
        }

        if (forwardResponse.ok) {
            res.status(200).send(data);
            //console.log(`!!! >>> Order Manager returned ${forwardResponse.status}: ${data}`);   //Temp for debugging
        } else {
            console.error(`Order Manager returned ${forwardResponse.status}: ${rawData}`);
            res.status(502).send(data || 'Error from Order Manager');
        }

    } catch (error) {
        console.error('Client Gateway - Forwarding error:', error.message);
        res.status(500).json({ error: 'Error forwarding order to Order Manager' });
    }
});

// Start server
server = app.listen(PORT, () => {
    console.log(`Client Gateway running on port ${PORT}`);
    console.log(`Forwarding orders to: ${ORDER_MANAGER_URL}`);
});

// Graceful shutdown for Kubernetes
process.on('SIGTERM', () => {
    console.log('SIGTERM received, shutting down gracefully...');
    server.close(() => {
        console.log('Closed out remaining connections');
        process.exit(0);
    });
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