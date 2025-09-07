#!/usr/bin/env python3
import sys
import os

# Add the source directory to Python path
sys.path.insert(0, '/home/tom/github/dynapsys/dynadock/src')

try:
    from dynadock.cli import cli
    cli()
except ImportError as e:
    print(f"Error importing dynadock: {e}")
    sys.exit(1)
except Exception as e:
    print(f"Error running dynadock: {e}")
    sys.exit(1)
