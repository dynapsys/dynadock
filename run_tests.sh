#!/bin/bash
#
# Comprehensive Test Script for DynaDock
#
# This script automates the process of:
# 1. Building a dedicated Docker image for testing.
# 2. Running all tests (linting, unit, integration) inside the container.
# 3. Verifying a real-world example that requires sudo permissions.
#
# To run this script, execute: sudo bash run_tests.sh

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Configuration ---
IMAGE_NAME="dynadock-test"
CONTAINER_NAME="dynadock-test-runner"

# --- Helper Functions ---
info() {
    echo -e "\033[0;34m[INFO] $1\033[0m"
}

success() {
    echo -e "\033[0;32m[SUCCESS] $1\033[0m"
}

error() {
    echo -e "\033[0;31m[ERROR] $1\033[0m" >&2
    exit 1
}

# --- Main Script ---

# 1. Build the Test Docker Image
info "Building the Docker test image ('$IMAGE_NAME')..."
docker build -f Dockerfile.test -t "$IMAGE_NAME" . || error "Docker image build failed."
success "Docker test image built successfully."

# 2. Run the Tests Inside the Container
info "Running the test container ('$CONTAINER_NAME')..."
info "This will mount the project directory and the Docker socket."

# We use docker run with --rm to automatically clean up the container on exit.
# The script inside the container will execute all necessary test commands.
docker run --rm --name "$CONTAINER_NAME" \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v "$(pwd)":/home/tester/dynadock \
    "$IMAGE_NAME" /bin/bash -c '
    set -e
    echo -e "\033[0;34m[INFO] Inside container: Running Makefile tests...\033[0m"
    
    # Run standard checks
    make format
    make lint
    make test
    
    echo -e "\033[0;32m[SUCCESS] Makefile tests passed.\033[0m"
    echo -e "\033[0;34m[INFO] Inside container: Testing LAN-visible mode (requires sudo)...\033[0m"
    
    # Navigate to an example and test a sudo command
    cd examples/fullstack
    sudo dynadock up --lan-visible
    
    echo -e "\033[0;34m[INFO] Checking service status...\033[0m"
    dynadock ps
    
    echo -e "\033[0;34m[INFO] Tearing down the services...\033[0m"
    dynadock down -v
    
    echo -e "\033[0;32m[SUCCESS] LAN-visible mode test completed successfully.\033[0m"
'

# Final success message
success "All tests completed successfully! The environment is working as expected."
