const express = require('express');
const { MongoClient } = require('mongodb');
const { Client } = require('@elastic/elasticsearch');
const cors = require('cors');
const helmet = require('helmet');
const Joi = require('joi');

const app = express();
const PORT = process.env.SERVICE_PORT || 3003;

// MongoDB connection
let db;
const mongoUrl = process.env.MONGODB_URL || 'mongodb://localhost:27017/products';

// Elasticsearch connection
const esClient = new Client({
  node: process.env.ELASTICSEARCH_URL || 'http://localhost:9200'
});

// Connect to MongoDB
async function connectMongo() {
  try {
    const client = new MongoClient(mongoUrl);
    await client.connect();
    db = client.db();
    console.log('✅ Connected to MongoDB');
    
    // Create indexes
    await db.collection('products').createIndex({ name: 'text', description: 'text' });
    await db.collection('products').createIndex({ category: 1, status: 1 });
    await db.collection('products').createIndex({ price: 1 });
    
  } catch (error) {
    console.error('❌ MongoDB connection failed:', error.message);
  }
}

connectMongo();

// Middleware
app.use(helmet());
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Validation schemas
const productSchema = Joi.object({
  name: Joi.string().min(1).max(200).required(),
  description: Joi.string().max(2000).required(),
  category: Joi.string().required(),
  price: Joi.number().positive().required(),
  currency: Joi.string().length(3).default('USD'),
  sku: Joi.string().required(),
  stock: Joi.number().integer().min(0).default(0),
  images: Joi.array().items(Joi.string().uri()).default([]),
  tags: Joi.array().items(Joi.string()).default([]),
  specifications: Joi.object().default({}),
  dimensions: Joi.object({
    length: Joi.number().positive(),
    width: Joi.number().positive(),
    height: Joi.number().positive(),
    weight: Joi.number().positive()
  }).optional(),
  status: Joi.string().valid('active', 'inactive', 'draft').default('active')
});

// Health check
app.get('/health', async (req, res) => {
  try {
    // Check MongoDB connection
    const mongoStatus = db ? 'connected' : 'disconnected';
    
    // Check Elasticsearch connection
    let esStatus = 'disconnected';
    try {
      await esClient.ping();
      esStatus = 'connected';
    } catch (error) {
      // ES connection failed
    }
    
    res.json({
      status: 'healthy',
      service: 'product-service',
      timestamp: new Date().toISOString(),
      uptime: process.uptime(),
      mongodb: mongoStatus,
      elasticsearch: esStatus
    });
  } catch (error) {
    res.status(503).json({
      status: 'unhealthy',
      service: 'product-service',
      error: error.message
    });
  }
});

// Get all products with search and filtering
app.get('/products', async (req, res) => {
  try {
    const {
      page = 1,
      limit = 20,
      category,
      status = 'active',
      minPrice,
      maxPrice,
      search,
      sortBy = 'created_at',
      sortOrder = 'desc'
    } = req.query;

    const skip = (page - 1) * parseInt(limit);
    const query = { status };

    if (category) query.category = category;
    if (minPrice || maxPrice) {
      query.price = {};
      if (minPrice) query.price.$gte = parseFloat(minPrice);
      if (maxPrice) query.price.$lte = parseFloat(maxPrice);
    }

    if (search) {
      query.$text = { $search: search };
    }

    const sortOptions = {};
    sortOptions[sortBy] = sortOrder === 'desc' ? -1 : 1;

    const products = await db.collection('products')
      .find(query)
      .sort(sortOptions)
      .skip(skip)
      .limit(parseInt(limit))
      .toArray();

    const total = await db.collection('products').countDocuments(query);

    res.json({
      products,
      pagination: {
        page: parseInt(page),
        limit: parseInt(limit),
        total,
        pages: Math.ceil(total / parseInt(limit))
      }
    });

  } catch (error) {
    console.error('Get products error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get product by ID
app.get('/products/:id', async (req, res) => {
  try {
    const { id } = req.params;
    
    const product = await db.collection('products').findOne({ 
      $or: [
        { _id: new (require('mongodb')).ObjectId(id) },
        { sku: id }
      ]
    });

    if (!product) {
      return res.status(404).json({ error: 'Product not found' });
    }

    res.json(product);

  } catch (error) {
    console.error('Get product error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Create product
app.post('/products', async (req, res) => {
  try {
    const { error, value } = productSchema.validate(req.body);
    if (error) {
      return res.status(400).json({ error: error.details[0].message });
    }

    // Check if SKU already exists
    const existingProduct = await db.collection('products').findOne({ sku: value.sku });
    if (existingProduct) {
      return res.status(409).json({ error: 'SKU already exists' });
    }

    const newProduct = {
      ...value,
      created_at: new Date(),
      updated_at: new Date()
    };

    const result = await db.collection('products').insertOne(newProduct);
    newProduct._id = result.insertedId;

    // Index in Elasticsearch
    try {
      await esClient.index({
        index: 'products',
        id: result.insertedId.toString(),
        body: {
          name: newProduct.name,
          description: newProduct.description,
          category: newProduct.category,
          tags: newProduct.tags,
          price: newProduct.price
        }
      });
    } catch (esError) {
      console.warn('Elasticsearch indexing failed:', esError.message);
    }

    res.status(201).json({
      success: true,
      product: newProduct
    });

  } catch (error) {
    console.error('Create product error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Update product
app.put('/products/:id', async (req, res) => {
  try {
    const { id } = req.params;
    const { error, value } = productSchema.validate(req.body, { allowUnknown: true });

    if (error) {
      return res.status(400).json({ error: error.details[0].message });
    }

    value.updated_at = new Date();

    const result = await db.collection('products').findOneAndUpdate(
      { _id: new (require('mongodb')).ObjectId(id) },
      { $set: value },
      { returnDocument: 'after' }
    );

    if (!result.value) {
      return res.status(404).json({ error: 'Product not found' });
    }

    // Update Elasticsearch
    try {
      await esClient.update({
        index: 'products',
        id: id,
        body: {
          doc: {
            name: value.name,
            description: value.description,
            category: value.category,
            tags: value.tags,
            price: value.price
          }
        }
      });
    } catch (esError) {
      console.warn('Elasticsearch update failed:', esError.message);
    }

    res.json({
      success: true,
      product: result.value
    });

  } catch (error) {
    console.error('Update product error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Delete product
app.delete('/products/:id', async (req, res) => {
  try {
    const { id } = req.params;

    const result = await db.collection('products').findOneAndDelete({
      _id: new (require('mongodb')).ObjectId(id)
    });

    if (!result.value) {
      return res.status(404).json({ error: 'Product not found' });
    }

    // Remove from Elasticsearch
    try {
      await esClient.delete({
        index: 'products',
        id: id
      });
    } catch (esError) {
      console.warn('Elasticsearch deletion failed:', esError.message);
    }

    res.json({
      success: true,
      message: 'Product deleted successfully'
    });

  } catch (error) {
    console.error('Delete product error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Advanced search using Elasticsearch
app.get('/search/products', async (req, res) => {
  try {
    const { q, category, minPrice, maxPrice, page = 1, limit = 20 } = req.query;

    const searchBody = {
      query: {
        bool: {
          must: [],
          filter: []
        }
      },
      from: (page - 1) * parseInt(limit),
      size: parseInt(limit)
    };

    if (q) {
      searchBody.query.bool.must.push({
        multi_match: {
          query: q,
          fields: ['name^2', 'description', 'tags']
        }
      });
    }

    if (category) {
      searchBody.query.bool.filter.push({
        term: { category: category }
      });
    }

    if (minPrice || maxPrice) {
      const priceRange = {};
      if (minPrice) priceRange.gte = parseFloat(minPrice);
      if (maxPrice) priceRange.lte = parseFloat(maxPrice);
      
      searchBody.query.bool.filter.push({
        range: { price: priceRange }
      });
    }

    const searchResult = await esClient.search({
      index: 'products',
      body: searchBody
    });

    const productIds = searchResult.body.hits.hits.map(hit => 
      new (require('mongodb')).ObjectId(hit._id)
    );

    const products = await db.collection('products')
      .find({ _id: { $in: productIds } })
      .toArray();

    res.json({
      products,
      total: searchResult.body.hits.total.value,
      pagination: {
        page: parseInt(page),
        limit: parseInt(limit),
        total: searchResult.body.hits.total.value,
        pages: Math.ceil(searchResult.body.hits.total.value / parseInt(limit))
      }
    });

  } catch (error) {
    console.error('Search error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get categories
app.get('/categories', async (req, res) => {
  try {
    const categories = await db.collection('products').distinct('category', { status: 'active' });
    res.json({ categories });
  } catch (error) {
    console.error('Get categories error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Product statistics
app.get('/stats', async (req, res) => {
  try {
    const stats = await db.collection('products').aggregate([
      {
        $group: {
          _id: null,
          totalProducts: { $sum: 1 },
          activeProducts: { $sum: { $cond: [{ $eq: ['$status', 'active'] }, 1, 0] } },
          averagePrice: { $avg: '$price' },
          totalStock: { $sum: '$stock' },
          categoryCounts: { $push: '$category' }
        }
      }
    ]).toArray();

    const categoryStats = await db.collection('products').aggregate([
      { $match: { status: 'active' } },
      {
        $group: {
          _id: '$category',
          count: { $sum: 1 },
          averagePrice: { $avg: '$price' }
        }
      }
    ]).toArray();

    res.json({
      statistics: stats[0] || {},
      categoryBreakdown: categoryStats
    });

  } catch (error) {
    console.error('Stats error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Update stock
app.patch('/products/:id/stock', async (req, res) => {
  try {
    const { id } = req.params;
    const { quantity, operation = 'set' } = req.body;

    if (typeof quantity !== 'number') {
      return res.status(400).json({ error: 'Quantity must be a number' });
    }

    let updateOperation;
    if (operation === 'add') {
      updateOperation = { $inc: { stock: quantity } };
    } else if (operation === 'subtract') {
      updateOperation = { $inc: { stock: -quantity } };
    } else {
      updateOperation = { $set: { stock: quantity } };
    }

    updateOperation.$set = { updated_at: new Date() };

    const result = await db.collection('products').findOneAndUpdate(
      { _id: new (require('mongodb')).ObjectId(id) },
      updateOperation,
      { returnDocument: 'after' }
    );

    if (!result.value) {
      return res.status(404).json({ error: 'Product not found' });
    }

    res.json({
      success: true,
      product: result.value
    });

  } catch (error) {
    console.error('Update stock error:', error);
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

// Start server
app.listen(PORT, '0.0.0.0', () => {
  console.log(`📦 Product Service running on port ${PORT}`);
  console.log(`🌍 Environment: ${process.env.NODE_ENV || 'development'}`);
});
