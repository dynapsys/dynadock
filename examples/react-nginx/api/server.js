const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const morgan = require('morgan');

const app = express();
const PORT = process.env.PORT || 3001;

// Middleware
app.use(helmet({
  contentSecurityPolicy: false // Disable for development
}));
app.use(cors({
  origin: process.env.FRONTEND_URL || '*',
  credentials: true
}));
app.use(morgan('combined'));
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    service: 'api',
    timestamp: new Date().toISOString(),
    uptime: process.uptime()
  });
});

// Sample API endpoints
app.get('/api/data', (req, res) => {
  res.json({
    message: 'Hello from the API!',
    data: {
      users: 1234,
      orders: 567,
      revenue: '$12,345',
      status: 'operational'
    },
    timestamp: new Date().toISOString(),
    source: 'Node.js API Backend'
  });
});

app.get('/api/status', (req, res) => {
  res.json({
    api: 'running',
    database: 'simulated',
    cache: 'simulated',
    version: '1.0.0',
    environment: process.env.NODE_ENV || 'development'
  });
});

// Sample POST endpoint
app.post('/api/data', (req, res) => {
  const { name, message } = req.body;
  
  res.json({
    success: true,
    message: 'Data received successfully',
    received: {
      name: name || 'Anonymous',
      message: message || 'No message',
      timestamp: new Date().toISOString()
    }
  });
});

// Error handling middleware
app.use((err, req, res, next) => {
  console.error('Error:', err);
  res.status(500).json({
    error: 'Internal Server Error',
    message: err.message
  });
});

// 404 handler
app.use('*', (req, res) => {
  res.status(404).json({
    error: 'Not Found',
    message: 'The requested endpoint does not exist',
    path: req.originalUrl
  });
});

// Start server
app.listen(PORT, '0.0.0.0', () => {
  console.log(`🚀 API Server running on port ${PORT}`);
  console.log(`🌐 Environment: ${process.env.NODE_ENV || 'development'}`);
  console.log(`🔗 Frontend URL: ${process.env.FRONTEND_URL || 'not specified'}`);
});
