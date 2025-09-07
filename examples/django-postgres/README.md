# Django + PostgreSQL + Redis Example

This example demonstrates a complete Django web application with PostgreSQL database and Redis for caching and background tasks.

## 🚀 Features

- **Django 4.2+** web framework
- **PostgreSQL 15** database
- **Redis 7** for caching and Celery backend
- **Celery** for background task processing
- **Health checks** for all services
- **Production-ready** configuration with WhiteNoise

## 📦 Services

- **web**: Django application server (port 8000)
- **db**: PostgreSQL database (port 5432)
- **redis**: Redis server (port 6379)
- **worker**: Celery background worker

## 🏃 Quick Start

### Standard Mode
```bash
cd examples/django-postgres
dynadock up --domain django.local --enable-tls
```

### 🌐 LAN-Visible Mode (Access from any device)
```bash
cd examples/django-postgres
sudo dynadock up --lan-visible
```

## 🌐 Access URLs

### Standard Mode
- **Web App**: https://web.django.local (or http://localhost:8000)
- **Admin**: https://web.django.local/admin/
- **Health Check**: https://web.django.local/health/

### LAN-Visible Mode
After starting with `--lan-visible`, you'll see direct IP addresses like:
- **Web App**: http://192.168.1.100:8000 (accessible from phones, tablets, other computers)
- **Admin**: http://192.168.1.100:8000/admin/
- **Health Check**: http://192.168.1.100:8000/health/

## 🔧 Development

### Database Setup
```bash
# Run migrations
dynadock exec --service web --command "python manage.py migrate"

# Create superuser
dynadock exec --service web --command "python manage.py createsuperuser"

# Collect static files
dynadock exec --service web --command "python manage.py collectstatic --noinput"
```

### Background Tasks
The Celery worker is automatically started and connected to Redis. You can add tasks in your Django app:

```python
from celery import shared_task

@shared_task
def my_background_task():
    # Your background processing here
    pass
```

## 📊 Monitoring

### Check Service Health
```bash
dynadock health
```

### View Logs
```bash
# All services
dynadock logs

# Specific service
dynadock exec --service web --command "tail -f /app/django.log"
```

### Database Access
```bash
# PostgreSQL shell
dynadock exec --service db --command "psql -U postgres -d django_app"

# Redis CLI
dynadock exec --service redis --command "redis-cli"
```

## 🛠️ Configuration

Environment variables are automatically generated:
- `SECRET_KEY`: Django secret key
- `POSTGRES_PASSWORD`: Database password
- `DATABASE_URL`: Complete database connection string
- `REDIS_URL`: Redis connection string

## 🔄 Production Deployment

For production, update the following:
1. Set `DEBUG=False` in environment
2. Configure proper `ALLOWED_HOSTS`
3. Use a production WSGI server (Gunicorn included)
4. Set up proper static file serving
5. Configure database backups

## 🧪 Testing the LAN-Visible Feature

1. **Start services**: `sudo dynadock up --lan-visible`
2. **Note the IP addresses** shown in the output
3. **Test from another device**: 
   - Connect phone/tablet to same WiFi
   - Open browser and visit the IP address (e.g., `http://192.168.1.100:8000`)
   - No additional configuration needed!

## 🔒 Security Notes

- LAN-visible mode only exposes services within your local network
- For internet access, use standard mode with proper domain configuration
- Always use HTTPS in production environments
- Change default passwords and secrets for production use
