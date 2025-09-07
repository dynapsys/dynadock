# DynaDock Enhanced Testing Framework

## Overview

The DynaDock testing framework has been completely refactored from a single monolithic script (`test_domains_headless.py` - 598 lines) into a modular, maintainable system with enhanced logging, diagnostics, and automated repair capabilities.

## Architecture

### Core Modules

#### 1. Network Analyzer (`src/dynadock/testing/network_analyzer.py`)
- **Purpose**: Detailed network connectivity analysis
- **Features**:
  - DNS resolution testing
  - TCP connection verification
  - Port scanning and availability checks
  - SSL certificate inspection
  - Comprehensive error reporting

```python
from src.dynadock.testing.network_analyzer import analyze_network_connectivity
result = analyze_network_connectivity('https://frontend.dynadock.lan')
# Returns: {'hostname', 'port', 'scheme', 'tcp_connect', 'dns_resolution', 'port_scan', 'ssl_cert_info'}
```

#### 2. System Checker (`src/dynadock/testing/system_checker.py`)
- **Purpose**: System and Docker environment status verification
- **Features**:
  - Docker container status and health
  - Port availability and listening services
  - `/etc/hosts` file analysis
  - Process monitoring

```python
from src.dynadock.testing.system_checker import check_system_status
status = check_system_status()
# Returns: {'containers', 'ports_listening', 'hosts_file', 'processes'}
```

#### 3. Browser Tester (`src/dynadock/testing/browser_tester.py`)
- **Purpose**: Headless browser testing with comprehensive diagnostics
- **Features**:
  - Playwright-based browser automation
  - Screenshot capture with automatic cleanup
  - Network request/response monitoring
  - Console log capture
  - SSL error detection
  - Performance metrics

```python
from src.dynadock.testing.browser_tester import test_domain_headless
result = await test_domain_headless('https://frontend.dynadock.lan')
# Returns: {'success', 'status', 'load_time', 'screenshot_path', 'errors', 'ssl_errors', 'network_requests', 'console_logs'}
```

#### 4. Auto Repair (`src/dynadock/testing/auto_repair.py`)
- **Purpose**: Automatic detection and repair of common issues
- **Features**:
  - Docker container restart attempts
  - Caddy service management
  - Port conflict detection
  - `/etc/hosts` file repair suggestions

```python
from src.dynadock.testing.auto_repair import auto_repair_issues
repairs = auto_repair_issues(['container not running', 'port conflict'])
# Returns: List of repair attempt results
```

### Test Runners

#### 1. Simple Test Runner (`test_domains_simple.py`)
- **Purpose**: Main comprehensive test orchestrator
- **Features**:
  - 6-phase testing workflow
  - Rich console output with progress bars
  - Detailed test results table
  - Comprehensive JSON report generation
  - Automatic screenshot management

#### 2. Minimal Test Runner (`test_domains_minimal.py`)
- **Purpose**: Lightweight testing without rich console
- **Use Case**: Debugging and CI/CD environments

#### 3. Production Test Runner (`test_runner.py`)
- **Purpose**: Production-ready framework testing
- **Features**:
  - Module import verification
  - Functionality testing
  - Environment validation
  - Integration testing
  - Comprehensive reporting

## Testing Workflow

### Phase 1: System Analysis
```
🖥️  Analyzing system status...
   📊 Docker containers: 3 running
   🌐 Listening ports: 5 detected
   📝 Hosts file entries: 4 local domains
   🔍 Process status: All services active
```

### Phase 2: Network Analysis
```
🌐 Analyzing network connectivity...
   🔍 DNS Resolution: frontend.dynadock.lan → 127.0.0.1
   🔗 TCP Connect: Port 443 accessible
   🔒 SSL Certificate: Valid (mkcert)
```

### Phase 3: Browser Testing
```
🌍 Running headless browser tests...
   📸 Screenshot: ✅ Saved (test_screenshots/frontend_local_dev.png)
   ⚡ Performance: 1.2s load time
   📊 Network: 15 requests, 0 failures
   🔒 Security: HTTPS verified
```

### Phase 4: Auto-Repair
```
🔧 Auto-repair & issue resolution...
   🛠️  Container restart: ✅ dynadock-caddy restarted
   🏠 Hosts file: ✅ All entries present
```

### Phase 5: Report Generation
```
📊 Final report generation...
   ✅ Success rate: 4/4 (100%)
   📸 Screenshots: 4 saved in test_screenshots/
   📊 Detailed report: test_report.json
```

## Key Improvements

### 1. Modularity
- **Before**: 598-line monolithic script
- **After**: 4 focused modules (50-120 lines each)
- **Benefits**: Easier testing, maintenance, and reuse

### 2. Enhanced Logging
- **Before**: Basic print statements
- **After**: Rich console output with progress bars, tables, and panels
- **Benefits**: Better visibility and debugging

### 3. Automated Cleanup
- **Before**: Manual screenshot management
- **After**: Automatic cleanup before each test run
- **Benefits**: No stale artifacts, cleaner test environment

### 4. Comprehensive Diagnostics
- **Before**: Basic connectivity checks
- **After**: Network analysis, SSL inspection, performance metrics
- **Benefits**: Faster issue identification and resolution

### 5. Auto-Repair Capabilities
- **Before**: Manual issue resolution
- **After**: Automatic detection and repair attempts
- **Benefits**: Reduced manual intervention, faster recovery

## Usage Examples

### Quick Module Test
```bash
cd /home/tom/github/dynapsys/dynadock
python3 test_domains_minimal.py
```

### Full Test Suite
```bash
python3 test_domains_simple.py
```

### Framework Validation
```bash
python3 test_runner.py
```

### Unit Tests
```bash
python3 tests/unit/test_testing_modules.py
```

## Configuration

### Test Domains
Default test domains in `test_domains_simple.py`:
- `https://frontend.dynadock.lan/`
- `https://mailhog.dynadock.lan/`
- `https://backend.dynadock.lan/health`
- `http://localhost:8000/`

### Screenshots
- **Directory**: `test_screenshots/`
- **Format**: PNG, full-page captures
- **Naming**: `{domain}_{timestamp}.png`
- **Cleanup**: Automatic before each test run

### Reports
- **File**: `test_report.json`
- **Content**: Comprehensive test results, system analysis, repair attempts
- **Format**: Structured JSON with metadata and statistics

## Dependencies

### Required Packages
```bash
pip install rich playwright
playwright install  # Browser binaries
```

### System Dependencies
- Docker (for container management)
- curl (for network testing)
- mkcert (for HTTPS certificates)

## Troubleshooting

### Common Issues

#### 1. Module Import Errors
```bash
# Ensure you're in the project root
cd /home/tom/github/dynapsys/dynadock
python3 -c "import sys; sys.path.insert(0, '.'); from src.dynadock.testing.network_analyzer import analyze_network_connectivity; print('✅ Imports working')"
```

#### 2. Playwright Not Installed
```bash
pip install playwright
playwright install
```

#### 3. Docker Not Running
```bash
sudo systemctl start docker
docker ps  # Verify containers are running
```

#### 4. Missing Hosts Entries
The auto-repair module will detect and suggest the required entries:
```
127.0.0.1 frontend.dynadock.lan
127.0.0.1 mailhog.dynadock.lan
127.0.0.1 backend.dynadock.lan
```

## Performance Metrics

### Before Refactoring
- **Single file**: 598 lines
- **Test time**: ~60 seconds
- **Error visibility**: Limited
- **Maintenance**: Difficult due to monolithic structure

### After Refactoring
- **Modular structure**: 4 modules (~300 total lines)
- **Test time**: ~45 seconds (optimized)
- **Error visibility**: Comprehensive diagnostics
- **Maintenance**: Easy due to separation of concerns
- **Test coverage**: Enhanced with unit tests

## Future Enhancements

1. **Parallel Testing**: Run multiple domain tests concurrently
2. **CI/CD Integration**: GitHub Actions workflow integration
3. **Monitoring**: Real-time monitoring dashboard
4. **Advanced Repair**: More sophisticated auto-repair mechanisms
5. **Performance Benchmarking**: Historical performance tracking

## CLI Helper Integration

The testing framework integrates with the refactored CLI helpers:

### Verification Helper (`src/dynadock/cli_helpers/verification.py`)
- Domain accessibility verification
- URL testing with curl
- `/etc/hosts` entry suggestions

### Display Helper (`src/dynadock/cli_helpers/display.py`)
- Service status tables
- Formatted log messages
- Console output utilities

This creates a comprehensive ecosystem of modular, maintainable testing and diagnostic tools for the DynaDock local development environment.
