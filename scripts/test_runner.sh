#!/bin/bash
#
# Test runner script for DynaDock examples
# This script runs automated tests for all example applications
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
EXAMPLES_DIR="$PROJECT_ROOT/examples"
TESTS_DIR="$PROJECT_ROOT/tests"

# Function to print colored output
print_color() {
    local color=$1
    shift
    echo -e "${color}$@${NC}"
}

# Function to check prerequisites
check_prerequisites() {
    print_color "$YELLOW" "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_color "$RED" "Error: Docker is not installed"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_color "$RED" "Error: Docker Compose is not installed"
        exit 1
    fi
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_color "$RED" "Error: Python 3 is not installed"
        exit 1
    fi
    
    # Check pytest
    if ! python3 -m pytest --version &> /dev/null; then
        print_color "$YELLOW" "Installing pytest..."
        pip3 install pytest pytest-timeout requests
    fi
    
    print_color "$GREEN" "Prerequisites check passed ✓"
}

# Function to clean up Docker resources
cleanup_docker() {
    print_color "$YELLOW" "Cleaning up Docker resources..."
    
    # Stop all running containers from examples
    for example in "$EXAMPLES_DIR"/*; do
        if [ -d "$example" ] && [ -f "$example/docker-compose.yaml" ]; then
            cd "$example"
            docker-compose down -v 2>/dev/null || true
        fi
    done
    
    # Prune unused resources
    docker system prune -f --volumes
    
    print_color "$GREEN" "Docker cleanup completed ✓"
}

# Function to test a specific example
test_example() {
    local example_name=$1
    local example_path="$EXAMPLES_DIR/$example_name"
    
    if [ ! -d "$example_path" ]; then
        print_color "$RED" "Example '$example_name' not found"
        return 1
    fi
    
    print_color "$YELLOW" "Testing $example_name example..."
    
    cd "$example_path"
    
    # Start services
    print_color "$YELLOW" "Starting services..."
    if ! dynadock up -d; then
        print_color "$RED" "Failed to start services for $example_name"
        dynadock logs
        dynadock down -v
        return 1
    fi
    
    # Wait for services to be ready
    sleep 10
    
    # Run health checks
    print_color "$YELLOW" "Running health checks..."
    if ! dynadock health; then
        print_color "$RED" "Health check failed for $example_name"
        dynadock logs
        dynadock down -v
        return 1
    fi
    
    # Stop services
    print_color "$YELLOW" "Stopping services..."
    dynadock down -v
    
    print_color "$GREEN" "$example_name test passed ✓"
    return 0
}

# Function to run all tests
run_all_tests() {
    local failed_tests=()
    
    print_color "$YELLOW" "Running all example tests..."
    
    # Run pytest tests
    if [ -f "$TESTS_DIR/test_examples.py" ]; then
        print_color "$YELLOW" "Running automated pytest tests..."
        if ! python3 -m pytest "$TESTS_DIR/test_examples.py" -v; then
            failed_tests+=("pytest")
        fi
    fi
    
    # Test each example manually
    for example in "$EXAMPLES_DIR"/*; do
        if [ -d "$example" ] && [ -f "$example/docker-compose.yaml" ]; then
            example_name=$(basename "$example")
            if ! test_example "$example_name"; then
                failed_tests+=("$example_name")
            fi
        fi
    done
    
    # Print summary
    echo
    print_color "$YELLOW" "========================================="
    print_color "$YELLOW" "            TEST SUMMARY"
    print_color "$YELLOW" "========================================="
    
    if [ ${#failed_tests[@]} -eq 0 ]; then
        print_color "$GREEN" "All tests passed! ✓"
        return 0
    else
        print_color "$RED" "Failed tests: ${failed_tests[@]}"
        return 1
    fi
}

# Function to run specific test
run_specific_test() {
    local test_name=$1
    
    case "$test_name" in
        pytest)
            print_color "$YELLOW" "Running pytest tests..."
            python3 -m pytest "$TESTS_DIR/test_examples.py" -v
            ;;
        simple-web|rest-api|fullstack|microservices)
            test_example "$test_name"
            ;;
        *)
            print_color "$RED" "Unknown test: $test_name"
            print_color "$YELLOW" "Available tests: pytest, simple-web, rest-api, fullstack, microservices"
            exit 1
            ;;
    esac
}

# Main function
main() {
    local test_type=${1:-all}
    local clean_after=${2:-true}
    
    print_color "$GREEN" "========================================="
    print_color "$GREEN" "       DynaDock Test Runner"
    print_color "$GREEN" "========================================="
    
    # Check prerequisites
    check_prerequisites
    
    # Clean before tests
    if [ "$clean_after" = "true" ]; then
        cleanup_docker
    fi
    
    # Run tests
    if [ "$test_type" = "all" ]; then
        run_all_tests
    else
        run_specific_test "$test_type"
    fi
    
    local exit_code=$?
    
    # Clean after tests
    if [ "$clean_after" = "true" ]; then
        cleanup_docker
    fi
    
    exit $exit_code
}

# Show usage
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Usage: $0 [test_name] [clean_after]"
    echo ""
    echo "Arguments:"
    echo "  test_name    - Name of specific test to run (default: all)"
    echo "               - Options: all, pytest, simple-web, rest-api, fullstack, microservices"
    echo "  clean_after  - Clean Docker resources after tests (default: true)"
    echo ""
    echo "Examples:"
    echo "  $0              # Run all tests"
    echo "  $0 simple-web   # Run only simple-web example test"
    echo "  $0 all false    # Run all tests without cleaning after"
    exit 0
fi

# Run main function
main "$@"
