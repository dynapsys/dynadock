import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [apiStatus, setApiStatus] = useState('loading');
  const [apiData, setApiData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const checkApiStatus = async () => {
      try {
        const response = await axios.get('/api/health');
        setApiStatus('connected');
        setApiData(response.data);
        setError(null);
      } catch (err) {
        setApiStatus('error');
        setError(err.message);
      }
    };

    checkApiStatus();
    const interval = setInterval(checkApiStatus, 30000); // Check every 30 seconds

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="App">
      <header className="App-header">
        <h1>🚀 React + Nginx + API Example</h1>
        <p>Powered by DynaDock</p>
        
        <div className="status-section">
          <h2>🔗 API Connection Status</h2>
          <div className={`status-indicator ${apiStatus}`}>
            {apiStatus === 'loading' && '⏳ Checking API...'}
            {apiStatus === 'connected' && '✅ API Connected'}
            {apiStatus === 'error' && '❌ API Error'}
          </div>
          
          {apiData && (
            <div className="api-data">
              <h3>📊 API Response:</h3>
              <pre>{JSON.stringify(apiData, null, 2)}</pre>
            </div>
          )}
          
          {error && (
            <div className="error-message">
              <h3>⚠️ Error Details:</h3>
              <code>{error}</code>
            </div>
          )}
        </div>

        <div className="info-section">
          <h2>🌐 Access Information</h2>
          <p>This React app is served by Nginx and communicates with a Node.js API backend.</p>
          
          <h3>📱 LAN-Visible Mode:</h3>
          <p>When started with <code>sudo dynadock up --lan-visible</code>, this app becomes accessible from:</p>
          <ul>
            <li>📱 Smartphones and tablets</li>
            <li>💻 Other computers on the network</li>
            <li>🖥️ Any device with a web browser</li>
          </ul>
          <p>No DNS configuration required!</p>
        </div>

        <div className="endpoints-section">
          <h2>🔗 Available Endpoints</h2>
          <ul>
            <li><strong>Frontend:</strong> / (this page)</li>
            <li><strong>API Health:</strong> /api/health</li>
            <li><strong>API Data:</strong> /api/data</li>
            <li><strong>Frontend Health:</strong> /health</li>
          </ul>
        </div>
      </header>
    </div>
  );
}

export default App;
