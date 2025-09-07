# Microservices Architecture Example

This example demonstrates a complete microservices architecture with multiple services, databases, message queues, and monitoring tools using DynaDock.

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐
│   User Browser  │    │  Mobile Device  │
└─────────┬───────┘    └─────────┬───────┘
          │                      │
          └──────────┬───────────┘
                     │
              ┌──────▼──────┐
              │    Kong     │ :8000 (API Gateway)
              │  (Gateway)  │
              └──────┬──────┘
                     │
    ┌────────────────┼────────────────┐
    │                │                │
┌───▼───┐       ┌────▼────┐      ┌────▼────┐
│ Auth  │ :3001 │  User   │:3002 │Product  │:3003
│Service│       │ Service │      │ Service │
└───┬───┘       └────┬────┘      └────┬────┘
    │                │                │
┌───▼───┐       ┌────▼────┐      ┌────▼────┐
│ Redis │       │Postgres │      │ MongoDB │
└───────┘       └─────────┘      └─────────┘

┌─────────────────┐    ┌─────────────────┐
│  Order Service  │    │ Notification    │
│     :3004       │    │   Service       │
│                 │    │     :3005       │
└─────────┬───────┘    └─────────┬───────┘
          │                      │
    ┌─────▼─────┐          ┌─────▼─────┐
    │ Postgres  │          │ RabbitMQ  │
    └───────────┘          └───────────┘

┌─────────────────┐    ┌─────────────────┐
│  Elasticsearch  │    │    Grafana      │
│     :9200       │    │     :3000       │
└─────────────────┘    └─────────────────┘
```

## 🚀 Services

### Core Application Services
- **🔐 Auth Service** (port 3001): JWT-based authentication with Redis sessions
- **👤 User Service** (port 3002): User management with PostgreSQL and Redis caching  
- **📦 Product Service** (port 3003): Product catalog with MongoDB and Elasticsearch search
- **🛒 Order Service** (port 3004): Order processing with PostgreSQL and RabbitMQ events
- **📧 Notification Service** (port 3005): Email/SMS notifications via RabbitMQ

### Infrastructure Services
- **🌐 Kong Gateway** (port 8000): API Gateway with routing and load balancing
- **🗄️ PostgreSQL**: Primary database for users and orders
- **🍃 MongoDB**: Document store for products and catalog
- **🔍 Elasticsearch**: Search engine for product discovery
- **🐰 RabbitMQ**: Message broker for async communication
- **📊 Redis**: Caching and session storage
- **📈 Prometheus**: Metrics collection
- **📊 Grafana**: Monitoring dashboards
- **📧 MailHog**: Email testing tool

## 🏃 Quick Start

### Standard Mode
```bash
cd examples/microservices
dynadock up --domain microservices.dynadock.lan --enable-tls
```

### 🌐 LAN-Visible Mode (Access from any device)
```bash
cd examples/microservices
sudo dynadock up --lan-visible
```

## 🌐 Access URLs

### Standard Mode
- **🌐 API Gateway**: https://gateway.microservices.dynadock.lan
- **🔐 Auth Service**: https://auth-service.microservices.dynadock.lan
- **👤 User Service**: https://user-service.microservices.dynadock.lan
- **📦 Product Service**: https://product-service.microservices.dynadock.lan
- **🛒 Order Service**: https://order-service.microservices.dynadock.lan
- **📧 Notification Service**: https://notification-service.microservices.dynadock.lan
- **📊 Grafana**: https://grafana.microservices.dynadock.lan
- **🐰 RabbitMQ Management**: https://rabbitmq.microservices.dynadock.lan
- **📧 MailHog**: https://mailhog.microservices.dynadock.lan

### LAN-Visible Mode
After starting with `--lan-visible`, access services directly via IP:
- **API Gateway**: http://192.168.1.100:8000
- **Individual Services**: http://192.168.1.10X:300X
- **Monitoring Tools**: Direct IP access from any device

## 🔗 API Endpoints

### Authentication Service (:3001)
```bash
# Login
curl -X POST http://localhost:3001/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"secret"}'

# Verify token
curl -X POST http://localhost:3001/verify \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### User Service (:3002)
```bash
# Get all users
curl http://localhost:3002/users

# Create user
curl -X POST http://localhost:3002/users \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","first_name":"John","last_name":"Doe"}'

# Get user by ID
curl http://localhost:3002/users/1
```

### Product Service (:3003)
```bash
# Get all products
curl http://localhost:3003/products

# Search products
curl http://localhost:3003/search/products?q=laptop

# Create product
curl -X POST http://localhost:3003/products \
  -H "Content-Type: application/json" \
  -d '{"name":"Laptop","description":"Gaming laptop","category":"electronics","price":999.99,"sku":"LAP001"}'
```

### Order Service (:3004)
```bash
# Create order
curl -X POST http://localhost:3004/orders \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "items": [{"product_id": "LAP001", "quantity": 1}],
    "shipping_address": {
      "street": "123 Main St",
      "city": "Anytown",
      "state": "ST",
      "zip": "12345",
      "country": "US"
    }
  }'

# Get orders
curl http://localhost:3004/orders

# Update order status
curl -X PATCH http://localhost:3004/orders/1/status \
  -H "Content-Type: application/json" \
  -d '{"status":"confirmed","notes":"Order confirmed"}'
```

### Notification Service (:3005)
```bash
# Send email
curl -X POST http://localhost:3005/email \
  -H "Content-Type: application/json" \
  -d '{"to":"test@example.com","subject":"Test","html":"<h1>Hello</h1>"}'

# Test notification
curl -X POST http://localhost:3005/test \
  -H "Content-Type: application/json" \
  -d '{"type":"email","to":"test@example.com"}'
```

## 🧪 Testing the System

### Health Checks
```bash
# Check all services
dynadock health

# Individual service health
curl http://localhost:3001/health  # Auth
curl http://localhost:3002/health  # User
curl http://localhost:3003/health  # Product
curl http://localhost:3004/health  # Order
curl http://localhost:3005/health  # Notification
```

### End-to-End Workflow
```bash
# 1. Login and get token
TOKEN=$(curl -s -X POST http://localhost:3001/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"secret"}' | jq -r '.token')

# 2. Create a user
curl -X POST http://localhost:3002/users \
  -H "Content-Type: application/json" \
  -d '{"email":"customer@example.com","first_name":"Jane","last_name":"Smith"}'

# 3. Create a product
curl -X POST http://localhost:3003/products \
  -H "Content-Type: application/json" \
  -d '{"name":"Smartphone","description":"Latest model","category":"electronics","price":799.99,"sku":"PHONE001","stock":50}'

# 4. Place an order (triggers notifications)
curl -X POST http://localhost:3004/orders \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "items": [{"product_id": "PHONE001", "quantity": 1}],
    "shipping_address": {
      "street": "456 Oak St",
      "city": "Somewhere",
      "state": "CA",
      "zip": "90210",
      "country": "US"
    }
  }'

# 5. Check MailHog for notification email
# Visit http://localhost:8025 (or LAN IP:8025)
```

### LAN-Visible Testing
1. **Start services**: `sudo dynadock up --lan-visible`
2. **Note the IP addresses** from the output
3. **Test from mobile device**:
   - Connect to same WiFi network
   - Access API Gateway: `http://192.168.1.100:8000`
   - Use mobile app or Postman to test APIs
   - Check MailHog UI: `http://192.168.1.XXX:8025`
   - Monitor with Grafana: `http://192.168.1.XXX:3000`

## 🔧 Development

### Service Logs
```bash
# View all logs
dynadock logs

# Specific service logs
dynadock logs --service auth-service
dynadock logs --service user-service
dynadock logs --service product-service
```

### Database Access
```bash
# PostgreSQL
dynadock exec --service postgres --command "psql -U user -d userdb"

# MongoDB
dynadock exec --service mongodb --command "mongosh"

# Redis
dynadock exec --service redis --command "redis-cli"
```

### Message Queue
```bash
# RabbitMQ Management UI
# Visit: http://localhost:15672 (guest/guest)

# Check queues
dynadock exec --service rabbitmq --command "rabbitmqctl list_queues"
```

## 📊 Monitoring & Observability

### Grafana Dashboards
- **Service Health**: Individual service metrics
- **Database Performance**: PostgreSQL, MongoDB, Redis metrics
- **API Gateway**: Request rates, response times
- **Message Queue**: RabbitMQ queue depths, message rates

### Prometheus Metrics
- HTTP request metrics from all services
- Database connection pool metrics
- Queue message processing metrics
- Custom business metrics

### Log Aggregation
All services log in JSON format for easy parsing and monitoring.

## 🏗️ Microservices Patterns Demonstrated

### ✅ Communication Patterns
- **🌐 API Gateway**: Centralized entry point with Kong
- **🔄 Service-to-Service**: HTTP/REST communication
- **📨 Event-Driven**: RabbitMQ for async messaging
- **🗄️ Database per Service**: Each service owns its data

### ✅ Data Management
- **📊 CQRS**: Read/write separation in product service  
- **🔍 Search**: Elasticsearch for complex queries
- **💾 Caching**: Redis for performance optimization
- **📝 Event Sourcing**: Order status changes tracked

### ✅ Reliability Patterns
- **🔄 Circuit Breaker**: Graceful service degradation
- **🔁 Retry Logic**: Automatic retry on failures
- **❤️ Health Checks**: Comprehensive service monitoring
- **📈 Observability**: Metrics, logs, and tracing

### ✅ Security Patterns
- **🔐 JWT Authentication**: Stateless authentication
- **🛡️ Rate Limiting**: DDoS protection
- **🔒 HTTPS**: TLS encryption for all endpoints
- **🚫 Input Validation**: Comprehensive data validation

## 🚀 Production Considerations

### Scaling
- **⚖️ Horizontal Scaling**: Add more service instances
- **🗄️ Database Sharding**: Split data across databases
- **⚡ Caching Strategy**: Multi-layer caching approach
- **📊 Load Balancing**: Distribute traffic efficiently

### Monitoring
- **📈 APM Tools**: Application Performance Monitoring
- **🚨 Alerting**: Real-time incident detection
- **📊 Business Metrics**: Track KPIs and conversions
- **🔍 Distributed Tracing**: Request flow visibility

### Security
- **🔑 Secret Management**: Vault or similar solutions
- **🛡️ Network Policies**: Service mesh security
- **🔐 mTLS**: Service-to-service encryption
- **🚫 RBAC**: Role-based access control

## 🌟 LAN-Visible Benefits

When using `--lan-visible` mode:
- **📱 Mobile Testing**: Test APIs from smartphones/tablets
- **👥 Team Collaboration**: Share services across devices  
- **🖥️ Cross-Platform**: Access from Windows/Mac/Linux
- **🚀 Demo Ready**: Instant access for presentations
- **🔧 No Configuration**: Works without DNS setup

## 🧪 Advanced Testing

### Load Testing
```bash
# Install Artillery
npm install -g artillery

# Test API Gateway
artillery quick --count 100 --num 10 http://localhost:8000/health

# Test individual services
artillery quick --count 50 --num 5 http://localhost:3002/users
```

### Integration Testing
```bash
# Run comprehensive test suite
./scripts/run-integration-tests.sh

# Test service dependencies
curl http://localhost:3004/stats  # Should connect to all dependencies
```

### Performance Monitoring
```bash
# Check service metrics
curl http://localhost:9090/metrics

# View in Grafana
# Visit: http://localhost:3000 (admin/admin)
```

This microservices example showcases enterprise-grade architecture patterns and demonstrates how DynaDock simplifies complex multi-service deployments with both local and LAN-visible networking capabilities.
