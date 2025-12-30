// Exchange Dashboard
// src/Dashboard.js
import React, { useEffect, useState, useRef, useCallback } from 'react';
import { Bar, Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, BarElement, PointElement, LineElement, Title, Tooltip, Legend);

// ===== CONFIG =====
const AVG_PRICE_INTERVAL_MS = 2 * 1000; 
const MAX_HISTORY_POINTS = 30;
const CHART_WIDTH = 900;
const CHART_HEIGHT = 400;
const WS_URL = process.env.REACT_APP_WS_URL || 'ws://localhost:30040/';
// ===================

const toFixed2 = n => Number(n).toFixed(2);

// Fixed cumulative calculation functions
function calculateCumulativeBids(bids) {
  // Sort bids in descending order (highest price first)
  const sortedBids = bids.sort((a, b) => b[0] - a[0]);
  
  // Calculate cumulative from highest to lowest price
  let cumulative = 0;
  const cumulativeBids = sortedBids.map(([price, quantity]) => {
    cumulative += quantity;
    return [price, cumulative];
  });
  
  return cumulativeBids;
}

function calculateCumulativeAsks(asks) {
  // Sort asks in ascending order (lowest price first)
  const sortedAsks = asks.sort((a, b) => a[0] - b[0]);
  
  // Calculate cumulative from lowest to highest price
  let cumulative = 0;
  const cumulativeAsks = sortedAsks.map(([price, quantity]) => {
    cumulative += quantity;
    return [price, cumulative];
  });
  
  return cumulativeAsks;
}

function aggregateByPrice(orders) {
  const map = new Map();
  orders.forEach(o => {
    const price = Number(o.price), qty = Number(o.quantity);
    if (isFinite(price) && isFinite(qty)) {
      map.set(price, (map.get(price) || 0) + qty);
    }
  });
  return map;
}

function buildOrderBook(book) {
  const bids = Array.from(aggregateByPrice(book.bids || []));
  const asks = Array.from(aggregateByPrice(book.asks || []));

  // Calculate cumulative quantities
  const cumulativeBids = calculateCumulativeBids([...bids]);
  const cumulativeAsks = calculateCumulativeAsks([...asks]);

  // Get top bids and asks
  const bidTop = cumulativeBids.slice(0, 12).sort((a, b) => a[0] - b[0]); // Sort by price ascending for display
  const askTop = cumulativeAsks.slice(0, 12);

  const bestBid = bidTop.length > 0 ? bidTop[bidTop.length - 1][0] : null;
  const bestAsk = askTop.length > 0 ? askTop[0][0] : null;
  const mid = (bestBid && bestAsk) ? (bestBid + bestAsk) / 2 : (bestBid ?? bestAsk ?? 0);

  const labels = [...bidTop.map(([p]) => toFixed2(p)), 'MID', ...askTop.map(([p]) => toFixed2(p))];
  const qtys = [...bidTop.map(([, q]) => q), 0, ...askTop.map(([, q]) => q)];
  const colors = [
    ...Array(bidTop.length).fill('rgba(0, 200, 83, 0.85)'),
    'rgba(255, 206, 86, 1)',
    ...Array(askTop.length).fill('rgba(244, 67, 54, 0.85)')
  ];

  const step = 50;
  const maxQty = Math.max(...qtys.filter(q => q !== 0), 0);
  const yMax = Math.max(step, Math.ceil(maxQty / step) * step);

  return { labels, qtys, colors, yMax, step, mid, bestBid, bestAsk };
}

export default function Dashboard() {
  const [wsConnected, setWsConnected] = useState(false);
  const [orderBook, setOrderBook] = useState({});
  const [symbols, setSymbols] = useState([]);
  const [selected, setSelected] = useState('');
  const [avgHist, setAvgHist] = useState({ bids: [], asks: [], times: [] });
  const [connectionError, setConnectionError] = useState(null);
  const ws = useRef(null);
  const lastUpdateRef = useRef(0);
  const orderBookRef = useRef({}); // Ref to store latest order book for WebSocket handler
  const reconnectTimeoutRef = useRef(null);

  // Keep ref in sync with state
  useEffect(() => {
    orderBookRef.current = orderBook;
  }, [orderBook]);

  // WebSocket connection management
  const connectWebSocket = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    try {
      console.log(`Connecting to WebSocket at: ${WS_URL}`);
      ws.current = new WebSocket(WS_URL);
      
      ws.current.onopen = () => {
        console.log('WebSocket connected successfully');
        setWsConnected(true);
        setConnectionError(null);
      };
      
      ws.current.onclose = (event) => {
        console.log('WebSocket disconnected:', event.code, event.reason);
        setWsConnected(false);
        
        // Attempt to reconnect after 3 seconds
        if (!reconnectTimeoutRef.current) {
          reconnectTimeoutRef.current = setTimeout(() => {
            console.log('Attempting to reconnect WebSocket...');
            connectWebSocket();
          }, 3000);
        }
      };
      
      ws.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        setWsConnected(false);
        setConnectionError('Failed to connect to WebSocket server');
      };
      
      ws.current.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data);
          if (msg.type === 'orderBookUpdate') {
            // Merge updates with existing order book data
            setOrderBook(prev => {
              const updated = {...prev};
              Object.keys(msg.orderBook || {}).forEach(symbol => {
                updated[symbol] = msg.orderBook[symbol];
              });
              return updated;
            });
            
            // Update symbols list
            const syms = Object.keys(msg.orderBook || {});
            setSymbols(prev => {
              const newSymbols = [...new Set([...prev, ...syms])];
              return newSymbols;
            });

            if (selected && msg.orderBook[selected]) {
              const { bids = [], asks = [] } = msg.orderBook[selected];
              const avgBid = bids.length ? bids.reduce((s, o) => s + Number(o.price || 0), 0) / bids.length : 0;
              const avgAsk = asks.length ? asks.reduce((s, o) => s + Number(o.price || 0), 0) / asks.length : 0;

              const now = Date.now();
              if (lastUpdateRef.current === 0 || now - lastUpdateRef.current >= AVG_PRICE_INTERVAL_MS) {
                lastUpdateRef.current = now;
                const timeLabel = new Date(now).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

                setAvgHist(prev => {
                  const times = [...prev.times, timeLabel].slice(-MAX_HISTORY_POINTS);
                  const bidsArr = [...prev.bids, avgBid].slice(-MAX_HISTORY_POINTS);
                  const asksArr = [...prev.asks, avgAsk].slice(-MAX_HISTORY_POINTS);
                  return { bids: bidsArr, asks: asksArr, times };
                });
              }
            }
          }
        } catch (err) {
          console.error('Error processing message:', err);
        }
      };
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      setConnectionError('Failed to create WebSocket connection');
      
      // Attempt to reconnect after 5 seconds on creation failure
      reconnectTimeoutRef.current = setTimeout(() => {
        console.log('Retrying WebSocket connection...');
        connectWebSocket();
      }, 5000);
    }
  }, [selected]);

  // WebSocket connection - fixed dependency array
  useEffect(() => {
    connectWebSocket();
    
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [connectWebSocket]);

  // Reset history on symbol change
  useEffect(() => {
    setAvgHist({ bids: [], asks: [], times: [] });
    lastUpdateRef.current = 0;
  }, [selected]);

  const ob = selected && orderBook[selected]
    ? buildOrderBook(orderBook[selected])
    : { labels: [], qtys: [], colors: [], yMax: 50, step: 50, mid: null, bestBid: null, bestAsk: null };

  // Order Book Chart
  const orderBookData = {
    labels: ob.labels,
    datasets: [{ 
      label: 'Cumulative Quantity', 
      data: ob.qtys, 
      backgroundColor: ob.colors,
      borderColor: ob.colors.map(c => c.replace('0.85', '1')),
      borderWidth: 1
    }]
  };
  
  const orderBookOpts = {
    responsive: false,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      title: { 
        display: true, 
        text: selected ? `Order Book — ${selected} | Spread: ${ob.bestBid && ob.bestAsk ? toFixed2(ob.bestAsk - ob.bestBid) : '—'}` : 'Order Book' 
      },
      tooltip: {
        callbacks: {
          title: items => {
            if (items[0]?.label === 'MID') {
              return `Mid: ${ob.mid ? toFixed2(ob.mid) : '—'}`;
            }
            return `Price: ${items[0]?.label}`;
          },
          label: context => `Cumulative Qty: ${context.parsed.y}`
        }
      }
    },
    scales: {
      x: { 
        title: { display: true, text: 'Price Levels' },
        ticks: { autoSkip: false, maxRotation: 30, minRotation: 30 } 
      },
      y: { 
        title: { display: true, text: 'Cumulative Quantity' },
        min: 0, 
        max: ob.yMax, 
        ticks: { stepSize: ob.step } 
      }
    }
  };

  // Avg Prices Chart
  const avgData = {
    labels: avgHist.times,
    datasets: [
      { 
        label: 'Avg Bid', 
        data: avgHist.bids, 
        borderColor: 'rgba(0,200,83,1)', 
        backgroundColor: 'rgba(0,200,83,0.1)', 
        tension: 0.2, 
        pointRadius: 3,
        fill: true
      },
      { 
        label: 'Avg Ask', 
        data: avgHist.asks, 
        borderColor: 'rgba(244,67,54,1)', 
        backgroundColor: 'rgba(244,67,54,0.1)', 
        tension: 0.2, 
        pointRadius: 3,
        fill: true
      }
    ]
  };
  
  const avgOpts = {
    responsive: false,
    maintainAspectRatio: false,
    plugins: { 
      title: { 
        display: true, 
        text: selected ? `Price Evolution — ${selected}` : 'Avg Prices' 
      } 
    },
    scales: { 
      x: { 
        title: { display: true, text: 'Time' },
        ticks: { autoSkip: true, maxRotation: 45 } 
      },
      y: {
        title: { display: true, text: 'Price' }
      }
    }
  };

  return (
    <div style={{ padding: 20 }}>
      <h2>Exchange Dashboard</h2>
      <p>
        Status: <strong style={{ color: wsConnected ? '#0c0' : '#c00' }}>
          {wsConnected ? 'Connected' : 'Disconnected'}
        </strong>
        {connectionError && (
          <span style={{ color: '#c00', marginLeft: '10px' }}>
            Error: {connectionError}
          </span>
        )}
      </p>
      <p style={{ fontSize: '0.9em', color: '#666' }}>
        WebSocket URL: {WS_URL}
      </p>

      <div style={{ marginBottom: 16 }}>
        <label>Select Symbol: </label>
        <select value={selected} onChange={e => setSelected(e.target.value)}>
          <option value="">-- Select --</option>
          {symbols.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>

      {selected && (
        <>
          <div style={{ marginBottom: 10 }}>
            {ob.bestBid && ob.bestAsk && (
              <p>
                Best Bid: <strong>{toFixed2(ob.bestBid)}</strong> | 
                Best Ask: <strong>{toFixed2(ob.bestAsk)}</strong> | 
                Spread: <strong>{toFixed2(ob.bestAsk - ob.bestBid)}</strong>
              </p>
            )}
          </div>
          
          <div style={{ width: CHART_WIDTH, height: CHART_HEIGHT, marginBottom: 20 }}>
            <Bar data={orderBookData} options={orderBookOpts} width={CHART_WIDTH} height={CHART_HEIGHT} />
          </div>

          <div style={{ width: CHART_WIDTH, height: CHART_HEIGHT }}>
            <Line data={avgData} options={avgOpts} width={CHART_WIDTH} height={CHART_HEIGHT} />
          </div>
        </>
      )}
    </div>
  );
}