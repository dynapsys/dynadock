#!/usr/bin/env python3
"""
Minimal test script to debug the silent failure issue
"""

import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, '.')

def main():
    """Minimal test without rich console"""
    print("=== DynaDock Minimal Test ===")
    print(f"Working directory: {os.getcwd()}")
    print(f"Python version: {sys.version}")
    
    # Test basic imports
    try:
        print("Testing imports...")
        from src.dynadock.testing.network_analyzer import analyze_network_connectivity
        from src.dynadock.testing.system_checker import check_system_status  
        from src.dynadock.testing.browser_tester import setup_screenshots_dir
        from src.dynadock.testing.auto_repair import repair_hosts_file
        print("✅ All imports successful")
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False
    
    # Test basic functionality
    print("Testing functionality...")
    
    # Test 1: Network analyzer
    try:
        result = analyze_network_connectivity('http://localhost:8000')
        print(f"✅ Network analyzer: {result['hostname']}:{result['port']}")
    except Exception as e:
        print(f"❌ Network analyzer: {e}")
        return False
    
    # Test 2: System checker
    try:
        status = check_system_status()
        containers = len(status.get('containers', []))
        print(f"✅ System checker: {containers} containers")
    except Exception as e:
        print(f"❌ System checker: {e}")
        return False
    
    # Test 3: Screenshot directory
    try:
        screenshots_dir = setup_screenshots_dir()
        print(f"✅ Screenshot setup: {screenshots_dir}")
    except Exception as e:
        print(f"❌ Screenshot setup: {e}")
        return False
    
    # Test 4: Hosts file check
    try:
        hosts_result = repair_hosts_file()
        print(f"✅ Hosts file check: {hosts_result[:50]}...")
    except Exception as e:
        print(f"❌ Hosts file check: {e}")
        return False
    
    print("✅ All tests passed!")
    return True

if __name__ == "__main__":
    try:
        success = main()
        print(f"Final result: {'SUCCESS' if success else 'FAILED'}")
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
