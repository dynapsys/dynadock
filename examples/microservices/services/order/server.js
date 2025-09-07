const express = require('express');
const { Pool } = require('pg');
const amqp = require('amqplib');
const cors = require('cors');
const helmet = require('helmet');
const Joi = require('joi');
const axios = require('axios');
const { v4: uuidv4 } = require('uuid');

const app = express();
const PORT = process.env.SERVICE_PORT || 3004;

// Database connection
const pool = new Pool({
  connectionString: process.env.DATABASE_URL || 'postgresql://user:password@localhost:5432/orderdb'
});

// RabbitMQ connection
let channel;
async function connectRabbitMQ() {
  try {
    const connection = await amqp.connect(process.env.RABBITMQ_URL || 'amqp://localhost:5672');
    channel = await connection.createChannel();
    
    // Declare exchanges and queues
    await channel.assertExchange('orders', 'topic', { durable: true });
    await channel.assertQueue('order.notifications', { durable: true });
    await channel.assertQueue('order.processing', { durable: true });
    
    console.log('✅ Connected to RabbitMQ');
  } catch (error) {
    console.error('❌ RabbitMQ connection failed:', error.message);
  }
}

connectRabbitMQ();

// Initialize database tables
async function initDatabase() {
  try {
    await pool.query(`
      CREATE TABLE IF NOT EXISTS orders (
        id SERIAL PRIMARY KEY,
        order_number VARCHAR(50) UNIQUE NOT NULL,
        user_id INTEGER NOT NULL,
        status VARCHAR(20) DEFAULT 'pending',
        total_amount DECIMAL(10,2) NOT NULL,
        currency VARCHAR(3) DEFAULT 'USD',
        shipping_address JSONB NOT NULL,
        billing_address JSONB,
        payment_method VARCHAR(50),
        payment_status VARCHAR(20) DEFAULT 'pending',
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);

    await pool.query(`
      CREATE TABLE IF NOT EXISTS order_items (
        id SERIAL PRIMARY KEY,
        order_id INTEGER REFERENCES orders(id) ON DELETE CASCADE,
        product_id VARCHAR(50) NOT NULL,
        product_name VARCHAR(200) NOT NULL,
        quantity INTEGER NOT NULL,
        unit_price DECIMAL(10,2) NOT NULL,
        total_price DECIMAL(10,2) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);

    await pool.query(`
      CREATE TABLE IF NOT EXISTS order_history (
        id SERIAL PRIMARY KEY,
        order_id INTEGER REFERENCES orders(id) ON DELETE CASCADE,
        status VARCHAR(20) NOT NULL,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
const orderSchema = Joi.object({
  user_id: Joi.number().integer().positive().required(),
  items: Joi.array().items(Joi.object({
    product_id: Joi.string().required(),
    quantity: Joi.number().integer().positive().required()
  })).min(1).required(),
  shipping_address: Joi.object({
    street: Joi.string().required(),
    city: Joi.string().required(),
    state: Joi.string().required(),
    zip: Joi.string().required(),
    country: Joi.string().required()
  }).required(),
  billing_address: Joi.object({
    street: Joi.string().required(),
    city: Joi.string().required(),
    state: Joi.string().required(),
    zip: Joi.string().required(),
    country: Joi.string().required()
  }).optional(),
  payment_method: Joi.string().optional(),
  notes: Joi.string().max(1000).optional()
});

// Helper function to publish messages
async function publishMessage(exchange, routingKey, message) {
  if (channel) {
    try {
      await channel.publish(exchange, routingKey, Buffer.from(JSON.stringify(message)));
    } catch (error) {
      console.error('Failed to publish message:', error);
    }
  }
}

// Helper function to fetch product details
async function fetchProductDetails(productId) {
  try {
    const response = await axios.get(`${process.env.PRODUCT_SERVICE_URL || 'http://localhost:3003'}/products/${productId}`);
    return response.data;
  } catch (error) {
    console.error(`Failed to fetch product ${productId}:`, error.message);
    return null;
  }
}

// Helper function to verify user exists
async function verifyUser(userId) {
  try {
    const response = await axios.get(`${process.env.USER_SERVICE_URL || 'http://localhost:3002'}/users/${userId}`);
    return response.data;
  } catch (error) {
    console.error(`Failed to verify user ${userId}:`, error.message);
    return null;
  }
}

// Health check
app.get('/health', async (req, res) => {
  try {
    // Check database connection
    const dbResult = await pool.query('SELECT 1');
    const dbStatus = dbResult ? 'connected' : 'disconnected';
    
    res.json({
      status: 'healthy',
      service: 'order-service',
      timestamp: new Date().toISOString(),
      uptime: process.uptime(),
      database: dbStatus,
      rabbitmq: channel ? 'connected' : 'disconnected'
    });
  } catch (error) {
    res.status(503).json({
      status: 'unhealthy',
      service: 'order-service',
      error: error.message
    });
  }
});

// Get all orders
app.get('/orders', async (req, res) => {
  try {
    const { page = 1, limit = 20, status, user_id } = req.query;
    const offset = (page - 1) * limit;
    
    let query = `
      SELECT o.*, 
             json_agg(
               json_build_object(
                 'id', oi.id,
                 'product_id', oi.product_id,
                 'product_name', oi.product_name,
                 'quantity', oi.quantity,
                 'unit_price', oi.unit_price,
                 'total_price', oi.total_price
               )
             ) as items
      FROM orders o
      LEFT JOIN order_items oi ON o.id = oi.order_id
      WHERE 1=1
    `;
    const params = [];
    
    if (status) {
      query += ` AND o.status = $${params.length + 1}`;
      params.push(status);
    }
    
    if (user_id) {
      query += ` AND o.user_id = $${params.length + 1}`;
      params.push(user_id);
    }
    
    query += ` GROUP BY o.id ORDER BY o.created_at DESC LIMIT $${params.length + 1} OFFSET $${params.length + 2}`;
    params.push(limit, offset);
    
    const result = await pool.query(query, params);
    
    // Get total count
    let countQuery = 'SELECT COUNT(*) FROM orders WHERE 1=1';
    const countParams = [];
    
    if (status) {
      countQuery += ` AND status = $${countParams.length + 1}`;
      countParams.push(status);
    }
    
    if (user_id) {
      countQuery += ` AND user_id = $${countParams.length + 1}`;
      countParams.push(user_id);
    }
    
    const countResult = await pool.query(countQuery, countParams);
    const total = parseInt(countResult.rows[0].count);
    
    res.json({
      orders: result.rows,
      pagination: {
        page: parseInt(page),
        limit: parseInt(limit),
        total,
        pages: Math.ceil(total / limit)
      }
    });
    
  } catch (error) {
    console.error('Get orders error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get order by ID
app.get('/orders/:id', async (req, res) => {
  try {
    const { id } = req.params;
    
    const orderResult = await pool.query(`
      SELECT * FROM orders WHERE id = $1
    `, [id]);
    
    if (orderResult.rows.length === 0) {
      return res.status(404).json({ error: 'Order not found' });
    }
    
    const order = orderResult.rows[0];
    
    // Get order items
    const itemsResult = await pool.query(`
      SELECT * FROM order_items WHERE order_id = $1
    `, [id]);
    
    // Get order history
    const historyResult = await pool.query(`
      SELECT * FROM order_history WHERE order_id = $1 ORDER BY created_at DESC
    `, [id]);
    
    order.items = itemsResult.rows;
    order.history = historyResult.rows;
    
    res.json(order);
    
  } catch (error) {
    console.error('Get order error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Create order
app.post('/orders', async (req, res) => {
  const client = await pool.connect();
  
  try {
    const { error, value } = orderSchema.validate(req.body);
    if (error) {
      return res.status(400).json({ error: error.details[0].message });
    }
    
    const { user_id, items, shipping_address, billing_address, payment_method, notes } = value;
    
    // Verify user exists
    const user = await verifyUser(user_id);
    if (!user) {
      return res.status(400).json({ error: 'Invalid user ID' });
    }
    
    await client.query('BEGIN');
    
    // Fetch product details and calculate total
    let totalAmount = 0;
    const orderItems = [];
    
    for (const item of items) {
      const product = await fetchProductDetails(item.product_id);
      if (!product) {
        await client.query('ROLLBACK');
        return res.status(400).json({ error: `Product ${item.product_id} not found` });
      }
      
      if (product.stock < item.quantity) {
        await client.query('ROLLBACK');
        return res.status(400).json({ error: `Insufficient stock for product ${product.name}` });
      }
      
      const itemTotal = product.price * item.quantity;
      totalAmount += itemTotal;
      
      orderItems.push({
        product_id: item.product_id,
        product_name: product.name,
        quantity: item.quantity,
        unit_price: product.price,
        total_price: itemTotal
      });
    }
    
    // Generate order number
    const orderNumber = `ORD-${Date.now()}-${Math.random().toString(36).substr(2, 9).toUpperCase()}`;
    
    // Create order
    const orderResult = await client.query(`
      INSERT INTO orders (order_number, user_id, total_amount, shipping_address, billing_address, payment_method, notes)
      VALUES ($1, $2, $3, $4, $5, $6, $7)
      RETURNING *
    `, [orderNumber, user_id, totalAmount, shipping_address, billing_address || shipping_address, payment_method, notes]);
    
    const order = orderResult.rows[0];
    
    // Create order items
    for (const item of orderItems) {
      await client.query(`
        INSERT INTO order_items (order_id, product_id, product_name, quantity, unit_price, total_price)
        VALUES ($1, $2, $3, $4, $5, $6)
      `, [order.id, item.product_id, item.product_name, item.quantity, item.unit_price, item.total_price]);
    }
    
    // Create order history entry
    await client.query(`
      INSERT INTO order_history (order_id, status, notes)
      VALUES ($1, $2, $3)
    `, [order.id, 'pending', 'Order created']);
    
    await client.query('COMMIT');
    
    // Publish order created event
    await publishMessage('orders', 'order.created', {
      orderId: order.id,
      orderNumber: order.order_number,
      userId: user_id,
      totalAmount: totalAmount,
      items: orderItems
    });
    
    // Get complete order data
    order.items = orderItems;
    
    res.status(201).json({
      success: true,
      order
    });
    
  } catch (error) {
    await client.query('ROLLBACK');
    console.error('Create order error:', error);
    res.status(500).json({ error: 'Internal server error' });
  } finally {
    client.release();
  }
});

// Update order status
app.patch('/orders/:id/status', async (req, res) => {
  try {
    const { id } = req.params;
    const { status, notes } = req.body;
    
    const validStatuses = ['pending', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled'];
    if (!validStatuses.includes(status)) {
      return res.status(400).json({ error: 'Invalid status' });
    }
    
    const result = await pool.query(`
      UPDATE orders 
      SET status = $1, updated_at = CURRENT_TIMESTAMP
      WHERE id = $2
      RETURNING *
    `, [status, id]);
    
    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Order not found' });
    }
    
    const order = result.rows[0];
    
    // Add to order history
    await pool.query(`
      INSERT INTO order_history (order_id, status, notes)
      VALUES ($1, $2, $3)
    `, [id, status, notes || `Status changed to ${status}`]);
    
    // Publish status update event
    await publishMessage('orders', 'order.status.updated', {
      orderId: order.id,
      orderNumber: order.order_number,
      oldStatus: order.status,
      newStatus: status,
      userId: order.user_id
    });
    
    res.json({
      success: true,
      order
    });
    
  } catch (error) {
    console.error('Update order status error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Cancel order
app.post('/orders/:id/cancel', async (req, res) => {
  try {
    const { id } = req.params;
    const { reason } = req.body;
    
    const result = await pool.query(`
      UPDATE orders 
      SET status = 'cancelled', updated_at = CURRENT_TIMESTAMP
      WHERE id = $1 AND status IN ('pending', 'confirmed')
      RETURNING *
    `, [id]);
    
    if (result.rows.length === 0) {
      return res.status(400).json({ error: 'Order cannot be cancelled' });
    }
    
    const order = result.rows[0];
    
    // Add to order history
    await pool.query(`
      INSERT INTO order_history (order_id, status, notes)
      VALUES ($1, $2, $3)
    `, [id, 'cancelled', reason || 'Order cancelled by request']);
    
    // Publish cancellation event
    await publishMessage('orders', 'order.cancelled', {
      orderId: order.id,
      orderNumber: order.order_number,
      userId: order.user_id,
      reason: reason
    });
    
    res.json({
      success: true,
      message: 'Order cancelled successfully',
      order
    });
    
  } catch (error) {
    console.error('Cancel order error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Order statistics
app.get('/stats', async (req, res) => {
  try {
    const stats = await pool.query(`
      SELECT 
        COUNT(*) as total_orders,
        COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_orders,
        COUNT(CASE WHEN status = 'confirmed' THEN 1 END) as confirmed_orders,
        COUNT(CASE WHEN status = 'processing' THEN 1 END) as processing_orders,
        COUNT(CASE WHEN status = 'shipped' THEN 1 END) as shipped_orders,
        COUNT(CASE WHEN status = 'delivered' THEN 1 END) as delivered_orders,
        COUNT(CASE WHEN status = 'cancelled' THEN 1 END) as cancelled_orders,
        SUM(total_amount) as total_revenue,
        AVG(total_amount) as average_order_value,
        COUNT(CASE WHEN created_at >= CURRENT_DATE - INTERVAL '30 days' THEN 1 END) as orders_last_30d
      FROM orders
    `);
    
    const topProducts = await pool.query(`
      SELECT 
        product_id,
        product_name,
        SUM(quantity) as total_quantity,
        SUM(total_price) as total_revenue
      FROM order_items oi
      JOIN orders o ON oi.order_id = o.id
      WHERE o.status != 'cancelled'
      GROUP BY product_id, product_name
      ORDER BY total_quantity DESC
      LIMIT 10
    `);
    
    res.json({
      statistics: stats.rows[0],
      topProducts: topProducts.rows
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
  if (channel) await channel.close();
  await pool.end();
  process.exit(0);
});

// Start server
app.listen(PORT, '0.0.0.0', () => {
  console.log(`🛒 Order Service running on port ${PORT}`);
  console.log(`🌍 Environment: ${process.env.NODE_ENV || 'development'}`);
});
