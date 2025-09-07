# React + Nginx + API Example

This example demonstrates a modern React frontend served by Nginx with a Node.js API backend, showcasing full-stack web application deployment with DynaDock.

## 🚀 Features

- **React 18** frontend with modern hooks
- **Nginx** reverse proxy and static file serving
- **Node.js + Express** API backend
- **Health checks** for all services
- **CORS support** for API communication
- **Production-ready** build pipeline

## 📦 Services

- **frontend**: React app built and served by Nginx (port 80)
- **api**: Node.js Express API server (port 3001)
- **nginx**: Nginx reverse proxy combining frontend + API (port 8080)

## 🏃 Quick Start

### Standard Mode
```bash
cd examples/react-nginx
dynadock up --domain react.local --enable-tls
```

### 🌐 LAN-Visible Mode (Access from any device)
```bash
cd examples/react-nginx
sudo dynadock up --lan-visible
```

## 🌐 Access URLs

### Standard Mode
- **Full App**: https://nginx.react.local (or http://localhost:8080)
- **Frontend Only**: https://frontend.react.local
- **API Only**: https://api.react.local

### LAN-Visible Mode
After starting with `--lan-visible`, you'll see direct IP addresses like:
- **Full App**: http://192.168.1.100:8080 (accessible from phones, tablets, other computers)
- **Frontend**: http://192.168.1.101:80
- **API**: http://192.168.1.102:3001

## 🔗 API Endpoints

The React app automatically connects to these API endpoints:

- `GET /api/health` - API health status
- `GET /api/data` - Sample data endpoint
- `GET /api/status` - Service status
- `POST /api/data` - Sample POST endpoint

## 🧪 Testing the Application

### Health Checks
```bash
# Check all services
dynadock health

# Manual API test
curl http://localhost:3001/health
```

### Frontend Features
The React app includes:
- **Real-time API status** monitoring
- **Automatic reconnection** handling
- **Mobile-responsive** design
- **Error handling** and display

### LAN-Visible Testing
1. **Start services**: `sudo dynadock up --lan-visible`
2. **Note the IP addresses** shown in the output
3. **Test from mobile device**:
   - Connect phone/tablet to same WiFi
   - Open browser and visit the IP (e.g., `http://192.168.1.100:8080`)
   - See real-time API connection status
   - Test works without any DNS configuration!

## 🔧 Development

### Build and Deploy
```bash
# Frontend development
cd frontend
npm start  # Development server

# API development
cd api
npm run dev  # Nodemon auto-reload

# Full stack with DynaDock
dynadock up --domain react.local
```

### Logs and Debugging
```bash
# View all service logs
dynadock logs

# Specific service logs
dynadock exec --service frontend --command "nginx -T"
dynadock exec --service api --command "npm run dev"
```

### Service Management
```bash
# Check status
dynadock ps

# Stop services
dynadock down -v
```

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐
│   User Browser  │    │  Mobile Device  │
└─────────┬───────┘    └─────────┬───────┘
          │                      │
          └──────────┬───────────┘
                     │
              ┌──────▼──────┐
              │    Nginx    │ :8080
              │ (Proxy+LB)  │
              └──────┬──────┘
                     │
          ┌──────────┼──────────┐
          │                     │
    ┌─────▼─────┐         ┌─────▼─────┐
    │  Frontend │ :80     │    API    │ :3001
    │  (React)  │         │ (Node.js) │
    └───────────┘         └───────────┘
```

## 🔒 Security Features

- **Helmet.js** security headers
- **CORS** configuration
- **Input validation**
- **Non-root containers**
- **Health check endpoints**

## 📱 Mobile-First Design

The React app is designed to work perfectly on:
- 📱 **Smartphones** (iOS/Android)
- 📟 **Tablets** (iPad/Android tablets)  
- 💻 **Laptops** (Windows/Mac/Linux)
- 🖥️ **Desktops** (Any modern browser)

## 🌟 LAN-Visible Benefits

When using `--lan-visible` mode:
- **No DNS setup** required
- **Instant access** from any device
- **Perfect for demos** and testing
- **Great for team collaboration**
- **Works across platforms** seamlessly

## 🚀 Production Considerations

For production deployment:
1. **Enable HTTPS** with real certificates
2. **Configure proper CORS** origins
3. **Set production environment** variables
4. **Add monitoring** and logging
5. **Implement authentication** if needed
6. **Use external databases** instead of in-memory data

## 🧪 Advanced Testing

```bash
# Load testing
curl -X POST http://localhost:3001/api/data \
  -H "Content-Type: application/json" \
  -d '{"name":"test","message":"hello"}'

# API performance
time curl http://localhost:3001/api/data

# Frontend bundle analysis
npm run build
npx serve -s build
```
