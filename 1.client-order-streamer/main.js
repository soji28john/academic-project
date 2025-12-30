//* This file reads the client orders and emits requests to the specified endpoint URL (Port 3001)

const assert = require('assert');
const fs = require('fs');
const split2 = require('split2');
const file_path = './market_simulation_orders-6h.csv';

const CLIENT_GATEWAY_URL = 'http://localhost:30010/order'; // Forwarding NodePort destination of Client Gateway

// Parses one CSV line into a JSON order object
function parseLine(line) {
    const fields_array = line.split(',');
    assert.strictEqual(fields_array.length, 7, 'Expected 7 fields!');
    return {
        user_id: fields_array[0],
        timestamp_ns: fields_array[1],
        price: parseFloat(fields_array[2]),
        symbol: fields_array[3],
        quantity: parseInt(fields_array[4], 10),
        side: fields_array[5],
        trader_type: fields_array[6],
    };
}

// Sends parsed order to CLIENT_GATEWAY_URL
async function send(order_line) {
    const parsedOrder = parseLine(order_line);

    try {
        const res = await fetch(CLIENT_GATEWAY_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(parsedOrder),
        });

        if (res.ok) {
            console.log(`Successfully sent order: ${JSON.stringify(parsedOrder)}`);
        } else {
            console.error(`Failed to send order: ${res.status} ${res.statusText}`);
        }
    } catch (err) {
        console.error(`Error sending order: ${err.message}`);
        console.error('Attempted URL:', CLIENT_GATEWAY_URL);
        console.error('Order data:', parsedOrder);
    }
}

// Reads CSV file and sends each line sequentially
async function processFileContents(csv_filepath) {
    const order_stream = fs
        .createReadStream(csv_filepath, { encoding: 'utf-8' })
        .pipe(split2());

    for await (const line of order_stream) {
        if (line.trim()) {
            await send(line);
        }
    }

    console.log('Finished processing file. All orders sent.');
    process.exit(0); // terminate after sending all orders
}

// Start processing
processFileContents(file_path);

