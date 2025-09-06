#!/bin/bash

# Test domain verification with dynadock

echo "========================================="
echo "Testing DynaDock Domain Verification"
echo "========================================="

cd examples/simple-web

echo -e "\n1. Cleaning up any existing services..."
dynadock down -v 2>/dev/null

echo -e "\n2. Starting services with domain verification..."
echo "Watch for curl checks after startup:"
echo "-----------------------------------------"

# Start services and capture output
dynadock up --enable-tls --detach 2>&1 | tee /tmp/dynadock_output.txt

echo -e "\n3. Manual verification with curl:"
echo "-----------------------------------------"

# Get ports from .env.dynadock
if [ -f .env.dynadock ]; then
    source .env.dynadock
    
    echo "Testing localhost access:"
    echo "  Web service on localhost:${WEB_PORT}:"
    curl -s -o /dev/null -w "    HTTP Status: %{http_code}\n" http://localhost:${WEB_PORT}
    
    echo "  API service on localhost:${API_PORT}:"
    curl -s -o /dev/null -w "    HTTP Status: %{http_code}\n" http://localhost:${API_PORT}
    
    echo -e "\nTesting domain access (will fail without /etc/hosts entries):"
    echo "  web.local.dev:"
    curl -s -o /dev/null -w "    HTTP Status: %{http_code}\n" -k --connect-timeout 2 https://web.local.dev 2>/dev/null || echo "    Failed (expected without /etc/hosts entry)"
    
    echo "  api.local.dev:"
    curl -s -o /dev/null -w "    HTTP Status: %{http_code}\n" -k --connect-timeout 2 https://api.local.dev 2>/dev/null || echo "    Failed (expected without /etc/hosts entry)"
fi

echo -e "\n4. Checking /etc/hosts for domain entries:"
echo "-----------------------------------------"
if grep -q "local.dev" /etc/hosts; then
    echo "Found local.dev entries in /etc/hosts:"
    grep "local.dev" /etc/hosts
else
    echo "No local.dev entries found in /etc/hosts"
    echo "To enable domain access, add these lines to /etc/hosts:"
    echo "  127.0.0.1 web.local.dev"
    echo "  127.0.0.1 api.local.dev"
fi

echo -e "\n5. Cleaning up..."
dynadock down -v

echo -e "\nTest complete!"
