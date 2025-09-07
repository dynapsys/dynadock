const express = require('express');
const amqp = require('amqplib');
const nodemailer = require('nodemailer');
const cors = require('cors');
const helmet = require('helmet');
const Joi = require('joi');
const axios = require('axios');

const app = express();
const PORT = process.env.SERVICE_PORT || 3005;

// Email transporter configuration
const transporter = nodemailer.createTransporter({
  host: process.env.SMTP_HOST || 'localhost',
  port: process.env.SMTP_PORT || 1025,
  secure: false, // true for 465, false for other ports
  auth: process.env.SMTP_USER ? {
    user: process.env.SMTP_USER,
    pass: process.env.SMTP_PASS
  } : undefined
});

// RabbitMQ connection
let channel;
let connection;

async function connectRabbitMQ() {
  try {
    connection = await amqp.connect(process.env.RABBITMQ_URL || 'amqp://localhost:5672');
    channel = await connection.createChannel();
    
    // Declare exchanges and queues
    await channel.assertExchange('orders', 'topic', { durable: true });
    await channel.assertQueue('order.notifications', { durable: true });
    
    // Bind queue to exchange
    await channel.bindQueue('order.notifications', 'orders', 'order.*');
    
    // Start consuming messages
    await channel.consume('order.notifications', processNotification, { noAck: false });
    
    console.log('✅ Connected to RabbitMQ and consuming messages');
  } catch (error) {
    console.error('❌ RabbitMQ connection failed:', error.message);
    // Retry connection after 5 seconds
    setTimeout(connectRabbitMQ, 5000);
  }
}

connectRabbitMQ();

// Middleware
app.use(helmet());
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Validation schemas
const emailSchema = Joi.object({
  to: Joi.string().email().required(),
  subject: Joi.string().required(),
  text: Joi.string().optional(),
  html: Joi.string().optional(),
  template: Joi.string().optional(),
  data: Joi.object().optional()
});

const smsSchema = Joi.object({
  to: Joi.string().required(),
  message: Joi.string().required()
});

// Email templates
const emailTemplates = {
  orderCreated: {
    subject: 'Order Confirmation - {{orderNumber}}',
    html: `
      <h2>Thank you for your order!</h2>
      <p>Your order <strong>{{orderNumber}}</strong> has been successfully created.</p>
      <p><strong>Total Amount:</strong> ${{totalAmount}}</p>
      <p><strong>Status:</strong> {{status}}</p>
      <p>We'll keep you updated on your order status.</p>
      <br>
      <p>Best regards,<br>Your E-commerce Team</p>
    `
  },
  orderStatusUpdated: {
    subject: 'Order Update - {{orderNumber}}',
    html: `
      <h2>Order Status Update</h2>
      <p>Your order <strong>{{orderNumber}}</strong> status has been updated.</p>
      <p><strong>New Status:</strong> {{newStatus}}</p>
      <p><strong>Updated At:</strong> {{updatedAt}}</p>
      <br>
      <p>Best regards,<br>Your E-commerce Team</p>
    `
  },
  orderCancelled: {
    subject: 'Order Cancellation - {{orderNumber}}',
    html: `
      <h2>Order Cancelled</h2>
      <p>Your order <strong>{{orderNumber}}</strong> has been cancelled.</p>
      <p><strong>Reason:</strong> {{reason}}</p>
      <p>If you have any questions, please contact our support team.</p>
      <br>
      <p>Best regards,<br>Your E-commerce Team</p>
    `
  },
  welcome: {
    subject: 'Welcome to Our Platform!',
    html: `
      <h2>Welcome {{firstName}}!</h2>
      <p>Thank you for joining our platform. We're excited to have you on board!</p>
      <p>You can now start exploring our products and services.</p>
      <br>
      <p>Best regards,<br>Your Team</p>
    `
  }
};

// Template rendering function
function renderTemplate(template, data) {
  let rendered = template;
  Object.keys(data).forEach(key => {
    const regex = new RegExp(`{{${key}}}`, 'g');
    rendered = rendered.replace(regex, data[key]);
  });
  return rendered;
}

// Process notification from RabbitMQ
async function processNotification(msg) {
  if (!msg) return;
  
  try {
    const notification = JSON.parse(msg.content.toString());
    console.log('📩 Processing notification:', notification);
    
    // Get user details for email
    let userEmail = 'user@example.com'; // Default fallback
    try {
      const userResponse = await axios.get(`${process.env.USER_SERVICE_URL || 'http://localhost:3002'}/users/${notification.userId}`);
      userEmail = userResponse.data.email;
    } catch (error) {
      console.warn('Could not fetch user email:', error.message);
    }
    
    // Process different notification types
    switch (msg.fields.routingKey) {
      case 'order.created':
        await sendOrderCreatedNotification(userEmail, notification);
        break;
      case 'order.status.updated':
        await sendOrderStatusNotification(userEmail, notification);
        break;
      case 'order.cancelled':
        await sendOrderCancelledNotification(userEmail, notification);
        break;
      default:
        console.log('Unknown notification type:', msg.fields.routingKey);
    }
    
    // Acknowledge message
    channel.ack(msg);
    
  } catch (error) {
    console.error('Error processing notification:', error);
    // Reject and requeue message
    channel.nack(msg, false, true);
  }
}

// Send order created notification
async function sendOrderCreatedNotification(email, data) {
  const template = emailTemplates.orderCreated;
  const subject = renderTemplate(template.subject, data);
  const html = renderTemplate(template.html, {
    ...data,
    totalAmount: data.totalAmount.toFixed(2),
    status: 'Pending'
  });
  
  await sendEmail({
    to: email,
    subject,
    html
  });
}

// Send order status update notification
async function sendOrderStatusNotification(email, data) {
  const template = emailTemplates.orderStatusUpdated;
  const subject = renderTemplate(template.subject, data);
  const html = renderTemplate(template.html, {
    ...data,
    updatedAt: new Date().toLocaleString()
  });
  
  await sendEmail({
    to: email,
    subject,
    html
  });
}

// Send order cancelled notification
async function sendOrderCancelledNotification(email, data) {
  const template = emailTemplates.orderCancelled;
  const subject = renderTemplate(template.subject, data);
  const html = renderTemplate(template.html, data);
  
  await sendEmail({
    to: email,
    subject,
    html
  });
}

// Send email function
async function sendEmail(emailData) {
  try {
    const result = await transporter.sendMail({
      from: process.env.FROM_EMAIL || 'noreply@example.com',
      ...emailData
    });
    
    console.log('✅ Email sent:', result.messageId);
    return { success: true, messageId: result.messageId };
  } catch (error) {
    console.error('❌ Failed to send email:', error);
    throw error;
  }
}

// Health check
app.get('/health', async (req, res) => {
  try {
    // Test email connection
    let emailStatus = 'disconnected';
    try {
      await transporter.verify();
      emailStatus = 'connected';
    } catch (error) {
      // Email connection failed
    }
    
    res.json({
      status: 'healthy',
      service: 'notification-service',
      timestamp: new Date().toISOString(),
      uptime: process.uptime(),
      email: emailStatus,
      rabbitmq: channel ? 'connected' : 'disconnected'
    });
  } catch (error) {
    res.status(503).json({
      status: 'unhealthy',
      service: 'notification-service',
      error: error.message
    });
  }
});

// Send email endpoint
app.post('/email', async (req, res) => {
  try {
    const { error, value } = emailSchema.validate(req.body);
    if (error) {
      return res.status(400).json({ error: error.details[0].message });
    }
    
    const { to, subject, text, html, template, data } = value;
    
    let emailContent = { to, subject };
    
    if (template && emailTemplates[template]) {
      const templateData = emailTemplates[template];
      emailContent.subject = renderTemplate(templateData.subject, data || {});
      emailContent.html = renderTemplate(templateData.html, data || {});
    } else {
      emailContent.text = text;
      emailContent.html = html;
    }
    
    const result = await sendEmail(emailContent);
    
    res.json({
      success: true,
      messageId: result.messageId
    });
    
  } catch (error) {
    console.error('Send email error:', error);
    res.status(500).json({ error: 'Failed to send email' });
  }
});

// Send SMS endpoint (mock implementation)
app.post('/sms', async (req, res) => {
  try {
    const { error, value } = smsSchema.validate(req.body);
    if (error) {
      return res.status(400).json({ error: error.details[0].message });
    }
    
    const { to, message } = value;
    
    // Mock SMS sending (in production, integrate with SMS provider)
    console.log(`📱 SMS to ${to}: ${message}`);
    
    res.json({
      success: true,
      message: 'SMS sent successfully (mock)'
    });
    
  } catch (error) {
    console.error('Send SMS error:', error);
    res.status(500).json({ error: 'Failed to send SMS' });
  }
});

// Get notification templates
app.get('/templates', (req, res) => {
  res.json({
    templates: Object.keys(emailTemplates).map(key => ({
      name: key,
      subject: emailTemplates[key].subject,
      description: `Template for ${key.replace(/([A-Z])/g, ' $1').toLowerCase()}`
    }))
  });
});

// Test notification endpoint
app.post('/test', async (req, res) => {
  try {
    const { type = 'email', to } = req.body;
    
    if (type === 'email') {
      await sendEmail({
        to: to || 'test@example.com',
        subject: 'Test Notification',
        html: '<h2>Test Email</h2><p>This is a test notification from the notification service.</p>'
      });
      
      res.json({
        success: true,
        message: 'Test email sent successfully'
      });
    } else {
      res.status(400).json({ error: 'Invalid notification type' });
    }
    
  } catch (error) {
    console.error('Test notification error:', error);
    res.status(500).json({ error: 'Failed to send test notification' });
  }
});

// Notification statistics
app.get('/stats', (req, res) => {
  // In a real implementation, you'd track these metrics
  res.json({
    statistics: {
      totalNotifications: 0,
      emailsSent: 0,
      smsSent: 0,
      failedNotifications: 0,
      uptime: process.uptime()
    }
  });
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
  if (connection) await connection.close();
  process.exit(0);
});

// Start server
app.listen(PORT, '0.0.0.0', () => {
  console.log(`📧 Notification Service running on port ${PORT}`);
  console.log(`🌍 Environment: ${process.env.NODE_ENV || 'development'}`);
});
