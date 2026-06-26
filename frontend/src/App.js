import React, { useState, useEffect } from 'react';
import { io } from 'socket.io-client';
import './App.css';

const socket = io('http://localhost:8000');

function App() {
  const [signals, setSignals] = useState([]);
  const [numbers, setNumbers] = useState([]);
  const [stats, setStats] = useState({});
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    // Socket connection
    socket.on('connect', () => {
      setIsConnected(true);
    });

    socket.on('disconnect', () => {
      setIsConnected(false);
    });

    // Listen for signals
    socket.on('signal', (signal) => {
      setSignals(prev => [signal, ...prev.slice(0, 9)]); // Keep last 10
    });

    // Load initial data
    fetchSignals();
    fetchNumbers();
    fetchStats();

    return () => {
      socket.off('connect');
      socket.off('disconnect');
      socket.off('signal');
    };
  }, []);

  const fetchSignals = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/signals/recent');
      const data = await response.json();
      setSignals(data.signals);
    } catch (error) {
      console.error('Error fetching signals:', error);
    }
  };

  const fetchNumbers = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/numbers/recent');
      const data = await response.json();
      setNumbers(data.numbers);
    } catch (error) {
      console.error('Error fetching numbers:', error);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/statistics');
      const data = await response.json();
      setStats(data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>🎰 Skynet Signal Platform</h1>
        <div className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
          {isConnected ? '🟢 Connected' : '🔴 Disconnected'}
        </div>
      </header>

      <main className="dashboard">
        <div className="stats-grid">
          <div className="stat-card">
            <h3>Total Numbers</h3>
            <p className="stat-number">{stats.total_numbers || 0}</p>
          </div>
          <div className="stat-card">
            <h3>Signals Today</h3>
            <p className="stat-number">{stats.signals_today || 0}</p>
          </div>
          <div className="stat-card">
            <h3>Success Rate</h3>
            <p className="stat-number">{stats.success_rate ? `${stats.success_rate.toFixed(1)}%` : '0%'}</p>
          </div>
          <div className="stat-card">
            <h3>Uptime</h3>
            <p className="stat-number">{stats.uptime_hours || 0}h</p>
          </div>
        </div>

        <div className="content-grid">
          <div className="panel">
            <h2>📊 Recent Signals</h2>
            <div className="signals-list">
              {signals.length === 0 ? (
                <p className="no-data">No signals yet...</p>
              ) : (
                signals.map((signal, index) => (
                  <div key={signal.id || index} className="signal-item">
                    <div className="signal-header">
                      <span className="signal-number">#{signal.number}</span>
                      <span className={`signal-type ${signal.signal_type.toLowerCase()}`}>
                        {signal.signal_type}
                      </span>
                      <span className="signal-confidence">
                        {Math.round(signal.confidence * 100)}%
                      </span>
                    </div>
                    <div className="signal-details">
                      <span>Strategy: {signal.strategy}</span>
                      <span>Risk: {signal.risk_level}</span>
                      <span>Gales: {signal.gales}</span>
                    </div>
                    <div className="signal-time">
                      {new Date(signal.timestamp).toLocaleTimeString()}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="panel">
            <h2>🎲 Recent Numbers</h2>
            <div className="numbers-grid">
              {numbers.slice(0, 20).map((num, index) => (
                <div key={index} className={`number-item ${num.color?.toLowerCase()}`}>
                  {num.number}
                </div>
              ))}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;