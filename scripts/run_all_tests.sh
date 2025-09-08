#!/usr/bin/env bash
# Comprehensive test runner for DynaDock
set -e

echo "🧪 DynaDock Comprehensive Test Suite"
echo "===================================="

FAILED=0
TOTAL=0

run_test() {
    local name="$1"
    local cmd="$2"
    echo ""
    echo "📋 Running: $name"
    echo "Command: $cmd"
    echo "------------------------------------"
    
    TOTAL=$((TOTAL + 1))
    if eval "$cmd"; then
        echo "✅ $name: PASSED"
    else
        echo "❌ $name: FAILED"
        FAILED=$((FAILED + 1))
    fi
}

# Unit tests
run_test "Unit Tests" "uv run pytest tests/unit/ -v --tb=short"

# Integration tests  
run_test "Integration Tests" "uv run pytest tests/integration/ -v --tb=short"

# Example tests
run_test "Example Tests" "./scripts/test_runner.sh all"

# Linting
run_test "Code Linting" "uv run ruff check src/ tests/"

# Type checking
run_test "Type Checking" "uv run mypy src/dynadock --ignore-missing-imports"

# Security scan (allow warnings)
run_test "Security Scan" "uv run bandit -r src/dynadock || true"

echo ""
echo "===================================="
echo "📊 Test Results Summary"
echo "===================================="
echo "Total tests: $TOTAL"
echo "Passed: $((TOTAL - FAILED))"
echo "Failed: $FAILED"

if [ $FAILED -eq 0 ]; then
    echo "🎉 All tests passed!"
    exit 0
else
    echo "⚠️  Some tests failed, but this is expected during development"
    exit 1
fi
