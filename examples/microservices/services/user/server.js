const express = require('express');
const { Pool } = require('pg');
const redis = require('redis');
const cors = require('cors');
const helmet = require('helmet');
const Joi = require('joi');
const axios = require('axios');

const app = express();
const PORT = process.env.SERVICE_PORT || 3002;

// Database connection
const pool = new Pool({
  connectionString: process.env.DATABASE_URL || 'postgresql://user:password@localhost:5432/userdb'
});

// Redis client
let redisClient;
(async () => {
  try {
    redisClient = redis.createClient({
      url: process.env.REDIS_URL || 'redis://localhost:6379'
    });
    await redisClient.connect();
    console.log('✅ Connected to Redis');
  } catch (error) {
    console.error('❌ Redis connection failed:', error.message);
  }
})();

// Initialize database tables
async function initDatabase() {
  try {
    await pool.query(`
      CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        email VARCHAR(255) UNIQUE NOT NULL,
        first_name VARCHAR(100) NOT NULL,
        last_name VARCHAR(100) NOT NULL,
        phone VARCHAR(50),
        address JSONB,
        preferences JSONB DEFAULT '{}',
        status VARCHAR(20) DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);

    await pool.query(`
      CREATE TABLE IF NOT EXISTS user_profiles (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        avatar_url VARCHAR(500),
        bio TEXT,
        date_of_birth DATE,
        occupation VARCHAR(100),
        company VARCHAR(100),
        website VARCHAR(200),
        social_links JSONB DEFAULT '{}',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);

    console.log('✅ Database tables initialized');
  } catch (error) {
    console.error('❌ Database initialization failed:', error.message);
  }
}

initDatabase();

// Middleware
app.use(helmet());
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Validation schemas
const userSchema = Joi.object({
  email: Joi.string().email().required(),
  first_name: Joi.string().min(1).max(100).required(),
  last_name: Joi.string().min(1).max(100).required(),
  phone: Joi.string().max(50).optional(),
  address: Joi.object().optional(),
  preferences: Joi.object().optional()
});

const profileSchema = Joi.object({
  avatar_url: Joi.string().uri().optional(),
  bio: Joi.string().max(1000).optional(),
  date_of_birth: Joi.date().optional(),
  occupation: Joi.string().max(100).optional(),
  company: Joi.string().max(100).optional(),
  website: Joi.string().uri().optional(),
  social_links: Joi.object().optional()
});

// Health check
app.get('/health', async (req, res) => {
  try {
    // Check database connection
    const dbResult = await pool.query('SELECT 1');
    const dbStatus = dbResult ? 'connected' : 'disconnected';
    
    res.json({
      status: 'healthy',
      service: 'user-service',
      timestamp: new Date().toISOString(),
      uptime: process.uptime(),
      database: dbStatus,
      redis: redisClient?.isReady ? 'connected' : 'disconnected'
    });
  } catch (error) {
    res.status(503).json({
      status: 'unhealthy',
      service: 'user-service',
      error: error.message
    });
  }
});

// Get all users
app.get('/users', async (req, res) => {
  try {
    const { page = 1, limit = 20, status, search } = req.query;
    const offset = (page - 1) * limit;
    
    let query = `
      SELECT u.*, p.avatar_url, p.bio 
      FROM users u 
      LEFT JOIN user_profiles p ON u.id = p.user_id
      WHERE 1=1
    `;
    const params = [];
    
    if (status) {
      query += ` AND u.status = $${params.length + 1}`;
      params.push(status);
    }
    
    if (search) {
      query += ` AND (u.first_name ILIKE $${params.length + 1} OR u.last_name ILIKE $${params.length + 1} OR u.email ILIKE $${params.length + 1})`;
      params.push(`%${search}%`);
    }
    
    query += ` ORDER BY u.created_at DESC LIMIT $${params.length + 1} OFFSET $${params.length + 2}`;
    params.push(limit, offset);
    
    const result = await pool.query(query, params);
    
    // Get total count
    let countQuery = 'SELECT COUNT(*) FROM users WHERE 1=1';
    const countParams = [];
    
    if (status) {
      countQuery += ` AND status = $${countParams.length + 1}`;
      countParams.push(status);
    }
    
    if (search) {
      countQuery += ` AND (first_name ILIKE $${countParams.length + 1} OR last_name ILIKE $${countParams.length + 1} OR email ILIKE $${countParams.length + 1})`;
      countParams.push(`%${search}%`);
    }
    
    const countResult = await pool.query(countQuery, countParams);
    const total = parseInt(countResult.rows[0].count);
    
    res.json({
      users: result.rows,
      pagination: {
        page: parseInt(page),
        limit: parseInt(limit),
        total,
        pages: Math.ceil(total / limit)
      }
    });
    
  } catch (error) {
    console.error('Get users error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get user by ID
app.get('/users/:id', async (req, res) => {
  try {
    const { id } = req.params;
    
    // Try Redis cache first
    if (redisClient?.isReady) {
      const cached = await redisClient.get(`user:${id}`);
      if (cached) {
        return res.json(JSON.parse(cached));
      }
    }
    
    const result = await pool.query(`
      SELECT u.*, p.* 
      FROM users u 
      LEFT JOIN user_profiles p ON u.id = p.user_id
      WHERE u.id = $1
    `, [id]);
    
    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'User not found' });
    }
    
    const user = result.rows[0];
    
    // Cache in Redis
    if (redisClient?.isReady) {
      await redisClient.setEx(`user:${id}`, 300, JSON.stringify(user));
    }
    
    res.json(user);
    
  } catch (error) {
    console.error('Get user error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Create user
app.post('/users', async (req, res) => {
  try {
    const { error, value } = userSchema.validate(req.body);
    if (error) {
      return res.status(400).json({ error: error.details[0].message });
    }
    
    const { email, first_name, last_name, phone, address, preferences } = value;
    
    const result = await pool.query(`
      INSERT INTO users (email, first_name, last_name, phone, address, preferences)
      VALUES ($1, $2, $3, $4, $5, $6)
      RETURNING *
    `, [email, first_name, last_name, phone, address, preferences]);
    
    const newUser = result.rows[0];
    
    // Invalidate cache
    if (redisClient?.isReady) {
      await redisClient.del('users:*');
    }
    
    res.status(201).json({
      success: true,
      user: newUser
    });
    
  } catch (error) {
    if (error.code === '23505') { // Unique violation
      return res.status(409).json({ error: 'Email already exists' });
    }
    
    console.error('Create user error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Update user
app.put('/users/:id', async (req, res) => {
  try {
    const { id } = req.params;
    const { error, value } = userSchema.validate(req.body, { allowUnknown: true });
    
    if (error) {
      return res.status(400).json({ error: error.details[0].message });
    }
    
    const fields = Object.keys(value);
    const values = Object.values(value);
    const setClause = fields.map((field, index) => `${field} = $${index + 2}`).join(', ');
    
    const result = await pool.query(`
      UPDATE users 
      SET ${setClause}, updated_at = CURRENT_TIMESTAMP
      WHERE id = $1
      RETURNING *
    `, [id, ...values]);
    
    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'User not found' });
    }
    
    // Invalidate cache
    if (redisClient?.isReady) {
      await redisClient.del(`user:${id}`);
    }
    
    res.json({
      success: true,
      user: result.rows[0]
    });
    
  } catch (error) {
    console.error('Update user error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Delete user
app.delete('/users/:id', async (req, res) => {
  try {
    const { id } = req.params;
    
    const result = await pool.query('DELETE FROM users WHERE id = $1 RETURNING *', [id]);
    
    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'User not found' });
    }
    
    // Invalidate cache
    if (redisClient?.isReady) {
      await redisClient.del(`user:${id}`);
    }
    
    res.json({
      success: true,
      message: 'User deleted successfully'
    });
    
  } catch (error) {
    console.error('Delete user error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Update user profile
app.put('/users/:id/profile', async (req, res) => {
  try {
    const { id } = req.params;
    const { error, value } = profileSchema.validate(req.body);
    
    if (error) {
      return res.status(400).json({ error: error.details[0].message });
    }
    
    // Check if user exists
    const userCheck = await pool.query('SELECT id FROM users WHERE id = $1', [id]);
    if (userCheck.rows.length === 0) {
      return res.status(404).json({ error: 'User not found' });
    }
    
    const fields = Object.keys(value);
    const values = Object.values(value);
    
    // Upsert profile
    const result = await pool.query(`
      INSERT INTO user_profiles (user_id, ${fields.join(', ')})
      VALUES ($1, ${fields.map((_, index) => `$${index + 2}`).join(', ')})
      ON CONFLICT (user_id) 
      DO UPDATE SET 
        ${fields.map((field, index) => `${field} = $${index + 2}`).join(', ')},
        updated_at = CURRENT_TIMESTAMP
      RETURNING *
    `, [id, ...values]);
    
    // Invalidate cache
    if (redisClient?.isReady) {
      await redisClient.del(`user:${id}`);
    }
    
    res.json({
      success: true,
      profile: result.rows[0]
    });
    
  } catch (error) {
    console.error('Update profile error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// User statistics
app.get('/stats', async (req, res) => {
  try {
    const stats = await pool.query(`
      SELECT 
        COUNT(*) as total_users,
        COUNT(CASE WHEN status = 'active' THEN 1 END) as active_users,
        COUNT(CASE WHEN status = 'inactive' THEN 1 END) as inactive_users,
        COUNT(CASE WHEN created_at >= CURRENT_DATE - INTERVAL '30 days' THEN 1 END) as new_users_30d
      FROM users
    `);
    
    res.json({
      statistics: stats.rows[0]
    });
    
  } catch (error) {
    console.error('Stats error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Error handling middleware
app.use((err, req, res, next) => {
  console.error('Unhandled error:', err);
  res.status(500).json({ error: 'Internal server error' });
});

// 404 handler
app.use('*', (req, res) => {
  res.status(404).json({ error: 'Endpoint not found' });
});

// Graceful shutdown
process.on('SIGTERM', async () => {
  console.log('Shutting down gracefully...');
  if (redisClient) await redisClient.quit();
  await pool.end();
  process.exit(0);
});

// Start server
app.listen(PORT, '0.0.0.0', () => {
  console.log(`👤 User Service running on port ${PORT}`);
  console.log(`🌍 Environment: ${process.env.NODE_ENV || 'development'}`);
});
