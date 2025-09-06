#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, '/home/tom/github/dynapsys/dynadock/src')

from dynadock.cli import cli

if __name__ == "__main__":
    # Add debugging
    print("Arguments:", sys.argv[1:])
    
    # Run CLI with arguments
    sys.argv = ['test_cli.py'] + sys.argv[1:]
    cli()
