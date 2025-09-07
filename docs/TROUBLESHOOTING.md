# DynaDock Troubleshooting Guide

## 🔧 Common Issues and Solutions

### Port Conflicts

#### Problem: "Port 80 is already in use"

```bash
Error: bind: address already in use
```

**Solution:**

1. Check what's using port 80:
```bash
sudo lsof -i :80
# or
sudo netstat -tulpn | grep :80
```

2. Stop conflicting service:
```bash
# If it's another Docker container
docker ps | grep ":80->"
docker stop <container_id>

# If it's a system service (like Apache/Nginx)
sudo systemctl stop apache2
# or
sudo systemctl stop nginx
```

3. Use a different port:
```bash
dynadock up --port-range 8000-9000
```

#### Problem: "Port range exhausted"

**Solution:**

1. Increase port range:
```bash
dynadock up --port-range 3000-5000
```

2. Or reduce number of services:
```bash
dynadock up --scale api=2  # Instead of default
```

### DNS Resolution Issues

#### Problem: "Cannot access *.dynadock.lan domains"

**Solution 1: Add to /etc/hosts**

```bash
# Add these lines to /etc/hosts
127.0.0.1 api.dynadock.lan
127.0.0.1 frontend.dynadock.lan
127.0.0.1 postgres.dynadock.lan
```

**Solution 2: Use dnsmasq (recommended)**

```bash
# Ubuntu/Debian
sudo apt-get install dnsmasq

# Configure dnsmasq
echo "address=/.dynadock.lan/127.0.0.1" | sudo tee /etc/dnsmasq.d/dynadock.lan.conf

# Restart dnsmasq
sudo systemctl restart dnsmasq
```

**Solution 3: Use localhost with port**

```bash
# Instead of https://api.dynadock.lan
# Use http://localhost:3001
```

### TLS/SSL Certificate Issues

#### Problem: "Certificate error in browser"

**Solution:**

1. For self-signed certificates (development):
```bash
# Chrome: Type "thisisunsafe" on the error page
# Firefox: Click "Advanced" > "Accept the Risk and Continue"
```

2. For Let's Encrypt (production):
```bash
# Ensure domain is publicly accessible
dynadock up --enable-tls --domain yourdomain.com

# Check Caddy logs
dynadock logs caddy
```

#### Problem: "Failed to obtain certificate"

**Solution:**

1. Check domain DNS:
```bash
dig yourdomain.com
nslookup yourdomain.com
```

2. Ensure ports 80 and 443 are accessible:
```bash
# Check firewall
sudo ufw status
sudo iptables -L
```

3. Use staging environment first:
```yaml
# .dynadock.yaml
caddy:
  staging: true  # Use Let's Encrypt staging
```

### Docker Issues

#### Problem: "Cannot connect to Docker daemon"

**Solution:**

1. Check Docker service:
```bash
sudo systemctl status docker
sudo systemctl start docker
```

2. Add user to docker group:
```bash
sudo usermod -aG docker $USER
# Log out and back in
```

3. Check Docker socket:
```bash
ls -la /var/run/docker.sock
sudo chmod 666 /var/run/docker.sock  # Temporary fix
```

#### Problem: "No space left on device"

**Solution:**

1. Clean Docker resources:
```bash
# Remove unused containers
docker container prune -f

# Remove unused images
docker image prune -a -f

# Remove unused volumes
docker volume prune -f

# Remove everything unused
docker system prune -a --volumes -f
```

2. Check disk space:
```bash
df -h
du -sh /var/lib/docker
```

### Service Connection Issues

#### Problem: "Service cannot connect to database"

**Solution:**

1. Check service health:
```bash
dynadock ps
docker ps
```

2. Verify environment variables:
```bash
# Check .env.dynadock
cat .env.dynadock

# Check service environment
docker exec <container_id> env
```

3. Test connection manually:
```bash
# PostgreSQL
docker exec -it <postgres_container> psql -U user -d dbname

# MySQL
docker exec -it <mysql_container> mysql -u root -p

# Redis
docker exec -it <redis_container> redis-cli ping
```

4. Check network:
```bash
# List networks
docker network ls

# Inspect network
docker network inspect <network_name>
```

#### Problem: "Health check failing"

**Solution:**

1. Check health check command:
```bash
# See health status
docker ps
docker inspect <container_id> | grep -A 10 Health
```

2. Test health endpoint manually:
```bash
docker exec <container_id> curl localhost:3000/health
```

3. Increase health check timeout:
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
  interval: 30s
  timeout: 30s  # Increase timeout
  retries: 5    # Increase retries
  start_period: 60s  # More time to start
```

### Performance Issues

#### Problem: "Services starting slowly"

**Solution:**

1. Increase resource limits:
```yaml
services:
  app:
    deploy:
      resources:
        limits:
          cpus: '1.0'    # Increase CPU
          memory: 1024M  # Increase memory
```

2. Use cached volumes for development:
```yaml
volumes:
  - ./src:/app/src:cached  # macOS performance
```

3. Build images beforehand:
```bash
docker-compose build --parallel
dynadock up
```

#### Problem: "High memory usage"

**Solution:**

1. Set memory limits:
```yaml
services:
  app:
    deploy:
      resources:
        limits:
          memory: 512M
```

2. Monitor memory usage:
```bash
docker stats
```

### Caddy Reverse Proxy Issues

#### Problem: "502 Bad Gateway"

**Solution:**

1. Check if service is running:
```bash
docker ps
dynadock logs <service_name>
```

2. Verify Caddy configuration:
```bash
docker exec caddy cat /etc/caddy/Caddyfile
```

3. Check Caddy logs:
```bash
dynadock logs caddy
docker logs caddy --tail 50
```

4. Ensure service is on correct network:
```bash
docker inspect <service_name> | grep NetworkMode
```

#### Problem: "Caddy not routing to service"

**Solution:**

1. Regenerate Caddy config:
```bash
dynadock down
dynadock up --enable-tls
```

2. Check service labels:
```bash
docker inspect <service_name> | grep Labels
```

### Environment Variable Issues

#### Problem: "Environment variables not loading"

**Solution:**

1. Check file existence:
```bash
ls -la .env.dynadock
cat .env.dynadock
```

2. Verify in container:
```bash
docker exec <container_id> printenv
```

3. Force regeneration:
```bash
rm .env.dynadock
dynadock up
```

#### Problem: "Password authentication failed"

**Solution:**

1. Check generated passwords:
```bash
grep PASSWORD .env.dynadock
```

2. Ensure consistent passwords:
```yaml
services:
  app:
    environment:
      - DB_PASSWORD=${DB_PASSWORD}  # Same variable
  postgres:
    environment:
      - POSTGRES_PASSWORD=${DB_PASSWORD}  # Same variable
```

## 📊 Debugging Commands

### Useful Docker Commands

```bash
# View all containers (including stopped)
docker ps -a

# View container logs
docker logs <container_name> --tail 100 -f

# Execute command in container
docker exec -it <container_name> /bin/sh

# Inspect container
docker inspect <container_name>

# View container processes
docker top <container_name>

# View resource usage
docker stats
```

### DynaDock Debug Mode

```bash
# Run with debug output
DEBUG=1 dynadock up

# Verbose logging
dynadock up --verbose

# Dry run (show what would happen)
dynadock up --dry-run
```

### Network Debugging

```bash
# Test connectivity between containers
docker exec <container1> ping <container2>

# Check DNS resolution
docker exec <container> nslookup <service_name>

# Check open ports
docker exec <container> netstat -tulpn

# Trace network path
docker exec <container> traceroute <target>
```

## 🆘 Getting Help

### Collect Debug Information

When reporting issues, include:

1. **System information:**
```bash
uname -a
docker version
docker-compose version
dynadock --version
```

2. **Configuration files:**
```bash
cat docker-compose.yaml
cat .dynadock.yaml
cat .env.dynadock
```

3. **Logs:**
```bash
dynadock logs > dynadock.log
docker ps -a > containers.log
docker network ls > networks.log
```

4. **Error messages:**
```bash
# Full error output
dynadock up 2>&1 | tee error.log
```

### Community Support

- **GitHub Issues**: [github.com/dynapsys/dynadock/issues](https://github.com/dynapsys/dynadock/issues)
- **Discussions**: [github.com/dynapsys/dynadock/discussions](https://github.com/dynapsys/dynadock/discussions)
- **Documentation**: [docs.dynadock.dev](https://docs.dynadock.dev)

## 🔄 Reset and Clean Start

If all else fails, try a clean start:

```bash
# 1. Stop everything
dynadock down -v

# 2. Clean Docker
docker system prune -a --volumes -f

# 3. Remove DynaDock files
rm -f .env.dynadock
rm -f Caddyfile
rm -rf .dynadock/

# 4. Start fresh
dynadock up --enable-tls
```
