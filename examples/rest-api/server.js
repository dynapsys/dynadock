const express = require('express');
const { Client } = require('pg');
const redis = require('redis');
const cors = require('cors');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(helmet());
app.use(cors());
app.use(express.json());

// Rate limiting
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100 // limit each IP to 100 requests per windowMs
});
app.use('/api/', limiter);

// Database connections
let pgClient;
let redisClient;

async function connectDatabases() {
  // PostgreSQL
  pgClient = new Client({
    connectionString: process.env.POSTGRES_DSN || process.env.DATABASE_URL
  });

  // Handle asynchronous errors
  pgClient.on('error', (err) => {
    console.error('PostgreSQL client error:', err);
  });
  
  try {
    await pgClient.connect();
    console.log('✅ Connected to PostgreSQL');
  } catch (err) {
    console.error('❌ PostgreSQL connection error:', err);
  }

  // Redis
  redisClient = redis.createClient({
    url: process.env.REDIS_URL
  });
  
  redisClient.on('error', (err) => console.error('❌ Redis Client Error', err));
  
  try {
    await redisClient.connect();
    console.log('✅ Connected to Redis');
  } catch (err) {
    console.error('❌ Redis connection error:', err);
  }
}

// Routes
app.get('/', (req, res) => {
  res.json({
    message: 'DynaDock REST API Example',
    version: '1.0.0',
    endpoints: {
      health: '/health',
      users: '/api/users',
      cache: '/api/cache/:key'
    }
  });
});

app.get('/health', async (req, res) => {
  const health = {
    status: 'ok',
    timestamp: new Date().toISOString(),
    services: {
      api: 'healthy',
      postgres: 'unknown',
      redis: 'unknown'
    }
  };

  // Check PostgreSQL
  try {
    await pgClient.query('SELECT 1');
    health.services.postgres = 'healthy';
  } catch (err) {
    health.services.postgres = 'unhealthy';
    health.status = 'degraded';
  }

  // Check Redis
  try {
    await redisClient.ping();
    health.services.redis = 'healthy';
  } catch (err) {
    health.services.redis = 'unhealthy';
    health.status = 'degraded';
  }

  const statusCode = health.status === 'ok' ? 200 : 503;
  res.status(statusCode).json(health);
});

// API endpoints
app.get('/api/users', async (req, res) => {
  try {
    const result = await pgClient.query('SELECT * FROM users LIMIT 10');
    
    // Cache in Redis
    await redisClient.setEx('users:latest', 60, JSON.stringify(result.rows));
    
    res.json({
      count: result.rows.length,
      users: result.rows
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/api/users', async (req, res) => {
  const { name, email } = req.body;
  
  if (!name || !email) {
    return res.status(400).json({ error: 'Name and email are required' });
  }
  
  try {
    const result = await pgClient.query(
      'INSERT INTO users (name, email, created_at) VALUES ($1, $2, NOW()) RETURNING *',
      [name, email]
    );
    
    // Invalidate cache
    await redisClient.del('users:latest');
    
    res.status(201).json(result.rows[0]);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get('/api/cache/:key', async (req, res) => {
  try {
    const value = await redisClient.get(req.params.key);
    if (value) {
      res.json({ key: req.params.key, value: JSON.parse(value) });
    } else {
      res.status(404).json({ error: 'Key not found' });
    }
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/api/cache/:key', async (req, res) => {
  const { value, ttl = 3600 } = req.body;
  
  try {
    await redisClient.setEx(req.params.key, ttl, JSON.stringify(value));
    res.json({ key: req.params.key, value, ttl });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Start server
async function start() {
  await connectDatabases();
  
  app.listen(PORT, () => {
    console.log(`🚀 REST API Server running on port ${PORT}`);
    console.log(`📚 API Documentation: http://localhost:${PORT}`);
  });
}

start().catch(console.error);
