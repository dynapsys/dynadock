#!/usr/bin/env python3
"""Test domain accessibility verification."""

import subprocess
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dynadock.cli import verify_domain_access, console

# Test with sample data
test_ports = {
    "web": 8000,
    "api": 8001,
    "db": 5432
}

print("Testing domain verification functionality:\n")
print("=" * 50)

# Test without TLS
print("\n1. Testing without TLS (http):")
verify_domain_access(test_ports, "local.dev", False)

print("\n" + "=" * 50)

# Test with TLS
print("\n2. Testing with TLS (https):")
verify_domain_access(test_ports, "local.dev", True)

print("\n" + "=" * 50)
print("\nDomain verification test complete!")
