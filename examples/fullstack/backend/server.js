const express = require('express');
const { Client } = require('pg');
const redis = require('redis');
const cors = require('cors');
const helmet = require('helmet');
const jwt = require('jsonwebtoken');
const bcrypt = require('bcryptjs');
const { body, validationResult } = require('express-validator');
const rateLimit = require('express-rate-limit');
const winston = require('winston');

const app = express();
const PORT = process.env.PORT || 5000;

// Logger setup
const logger = winston.createLogger({
  level: 'info',
  format: winston.format.json(),
  transports: [
    new winston.transports.Console({
      format: winston.format.simple()
    })
  ]
});

// Middleware
app.use(helmet());
app.use(cors());
app.use(express.json());

// Rate limiting
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 100
});
app.use('/api/', limiter);

// Database connections
let pgClient;
let redisClient;

async function connectDatabases() {
  // PostgreSQL
  pgClient = new Client({
    connectionString: process.env.DATABASE_URL
  });
  
  try {
    await pgClient.connect();
    await initDatabase();
    logger.info('✅ Connected to PostgreSQL');
  } catch (err) {
    logger.error('❌ PostgreSQL connection error:', err);
  }

  // Redis
  redisClient = redis.createClient({
    url: process.env.REDIS_URL
  });
  
  redisClient.on('error', (err) => logger.error('❌ Redis Client Error', err));
  
  try {
    await redisClient.connect();
    logger.info('✅ Connected to Redis');
  } catch (err) {
    logger.error('❌ Redis connection error:', err);
  }
}

// Initialize database
async function initDatabase() {
  await pgClient.query(`
    CREATE TABLE IF NOT EXISTS users (
      id SERIAL PRIMARY KEY,
      email VARCHAR(255) UNIQUE NOT NULL,
      password VARCHAR(255) NOT NULL,
      name VARCHAR(255),
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
  `);
  
  await pgClient.query(`
    CREATE TABLE IF NOT EXISTS todos (
      id SERIAL PRIMARY KEY,
      user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
      title VARCHAR(255) NOT NULL,
      completed BOOLEAN DEFAULT false,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
  `);
}

// JWT middleware
function authenticateToken(req, res, next) {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1];
  
  if (!token) {
    return res.status(401).json({ error: 'Access denied' });
  }
  
  jwt.verify(token, process.env.JWT_SECRET, (err, user) => {
    if (err) {
      return res.status(403).json({ error: 'Invalid token' });
    }
    req.user = user;
    next();
  });
}

// Routes
app.get('/api', (req, res) => {
  res.json({
    message: 'DynaDock Fullstack API',
    version: '1.0.0',
    endpoints: {
      health: '/api/health',
      auth: {
        register: 'POST /api/auth/register',
        login: 'POST /api/auth/login',
        profile: 'GET /api/auth/profile'
      },
      todos: {
        list: 'GET /api/todos',
        create: 'POST /api/todos',
        update: 'PUT /api/todos/:id',
        delete: 'DELETE /api/todos/:id'
      }
    }
  });
});

app.get('/api/health', async (req, res) => {
  const health = {
    status: 'ok',
    timestamp: new Date().toISOString(),
    services: {
      api: 'healthy',
      postgres: 'unknown',
      redis: 'unknown'
    }
  };

  try {
    await pgClient.query('SELECT 1');
    health.services.postgres = 'healthy';
  } catch (err) {
    health.services.postgres = 'unhealthy';
    health.status = 'degraded';
  }

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

// Auth endpoints
app.post('/api/auth/register', [
  body('email').isEmail(),
  body('password').isLength({ min: 6 }),
  body('name').notEmpty()
], async (req, res) => {
  const errors = validationResult(req);
  if (!errors.isEmpty()) {
    return res.status(400).json({ errors: errors.array() });
  }
  
  const { email, password, name } = req.body;
  
  try {
    const hashedPassword = await bcrypt.hash(password, 10);
    
    const result = await pgClient.query(
      'INSERT INTO users (email, password, name) VALUES ($1, $2, $3) RETURNING id, email, name',
      [email, hashedPassword, name]
    );
    
    const token = jwt.sign({ id: result.rows[0].id }, process.env.JWT_SECRET, { expiresIn: '7d' });
    
    res.status(201).json({
      user: result.rows[0],
      token
    });
  } catch (err) {
    if (err.code === '23505') {
      res.status(400).json({ error: 'Email already exists' });
    } else {
      res.status(500).json({ error: err.message });
    }
  }
});

app.post('/api/auth/login', [
  body('email').isEmail(),
  body('password').notEmpty()
], async (req, res) => {
  const errors = validationResult(req);
  if (!errors.isEmpty()) {
    return res.status(400).json({ errors: errors.array() });
  }
  
  const { email, password } = req.body;
  
  try {
    const result = await pgClient.query(
      'SELECT id, email, password, name FROM users WHERE email = $1',
      [email]
    );
    
    if (result.rows.length === 0) {
      return res.status(401).json({ error: 'Invalid credentials' });
    }
    
    const user = result.rows[0];
    const validPassword = await bcrypt.compare(password, user.password);
    
    if (!validPassword) {
      return res.status(401).json({ error: 'Invalid credentials' });
    }
    
    const token = jwt.sign({ id: user.id }, process.env.JWT_SECRET, { expiresIn: '7d' });
    
    delete user.password;
    res.json({
      user,
      token
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get('/api/auth/profile', authenticateToken, async (req, res) => {
  try {
    const result = await pgClient.query(
      'SELECT id, email, name, created_at FROM users WHERE id = $1',
      [req.user.id]
    );
    
    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'User not found' });
    }
    
    res.json(result.rows[0]);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Todos endpoints
app.get('/api/todos', authenticateToken, async (req, res) => {
  try {
    const cacheKey = `todos:${req.user.id}`;
    const cached = await redisClient.get(cacheKey);
    
    if (cached) {
      return res.json(JSON.parse(cached));
    }
    
    const result = await pgClient.query(
      'SELECT * FROM todos WHERE user_id = $1 ORDER BY created_at DESC',
      [req.user.id]
    );
    
    await redisClient.setEx(cacheKey, 60, JSON.stringify(result.rows));
    res.json(result.rows);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/api/todos', authenticateToken, [
  body('title').notEmpty()
], async (req, res) => {
  const errors = validationResult(req);
  if (!errors.isEmpty()) {
    return res.status(400).json({ errors: errors.array() });
  }
  
  const { title } = req.body;
  
  try {
    const result = await pgClient.query(
      'INSERT INTO todos (user_id, title) VALUES ($1, $2) RETURNING *',
      [req.user.id, title]
    );
    
    await redisClient.del(`todos:${req.user.id}`);
    res.status(201).json(result.rows[0]);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.put('/api/todos/:id', authenticateToken, async (req, res) => {
  const { id } = req.params;
  const { title, completed } = req.body;
  
  try {
    const result = await pgClient.query(
      'UPDATE todos SET title = COALESCE($1, title), completed = COALESCE($2, completed) WHERE id = $3 AND user_id = $4 RETURNING *',
      [title, completed, id, req.user.id]
    );
    
    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Todo not found' });
    }
    
    await redisClient.del(`todos:${req.user.id}`);
    res.json(result.rows[0]);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.delete('/api/todos/:id', authenticateToken, async (req, res) => {
  const { id } = req.params;
  
  try {
    const result = await pgClient.query(
      'DELETE FROM todos WHERE id = $1 AND user_id = $2 RETURNING id',
      [id, req.user.id]
    );
    
    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Todo not found' });
    }
    
    await redisClient.del(`todos:${req.user.id}`);
    res.json({ message: 'Todo deleted' });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Start server
async function start() {
  await connectDatabases();
  
  app.listen(PORT, () => {
    logger.info(`🚀 API Server running on port ${PORT}`);
    logger.info(`📚 API Documentation: http://localhost:${PORT}/api`);
  });
}

start().catch(console.error);
