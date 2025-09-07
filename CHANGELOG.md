# Changelog

All notable changes to DynaDock will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2025-01-07

### Added
- **Enhanced Verbose Logging System**: Comprehensive logging across all DynaDock components
  - Added `--verbose/-v` flag to CLI for detailed debug output
  - Structured logging with timestamps and component identification
  - Log files automatically saved to `.dynadock/dynadock.log`
  - Enhanced logging in DockerManager, NetworkManager, CaddyConfig, EnvGenerator, and PortAllocator

### Enhanced
- **HTTPS Testing Framework**: Major improvements to testing and diagnostics
  - Enhanced `network_analyzer.py` with verbose logging, timing metrics, and structured output
  - Improved `browser_tester.py` with detailed Playwright operation logging
  - Added comprehensive diagnostic scripts:
    - `detailed_test_3_cases.py`: Full-featured comprehensive testing
    - `working_detailed_test.py`: Simplified reliable version
    - `simple_network_test.py`: Basic network connectivity tests
    - `comprehensive_diagnostic_report.py`: Complete diagnostic suite with JSON reporting

### Improved
- **Network Detection**: Enhanced DNS resolution, TCP connectivity, and port scanning diagnostics
- **SSL Certificate Validation**: Detailed SSL certificate inspection with timing information
- **System Analysis**: Comprehensive Docker container, port, and hosts file analysis
- **Performance Metrics**: Timing information for all network and system operations
- **Error Diagnostics**: Clear failure identification with specific error details

### Testing
- **Three-Domain Test Coverage**: Comprehensive testing for:
  - `http://localhost:8000` (direct localhost access)
  - `https://frontend.local.dev` (frontend local domain)
  - `https://mailhog.local.dev` (MailHog local domain)
- **Screenshot Verification**: Browser-based visual proof of service accessibility
- **Structured Reporting**: JSON output with detailed statistics and recommendations

### Technical
- **Logging Infrastructure**: Centralized logging configuration with file and console output
- **Debug Capabilities**: Extensive debug information for troubleshooting and maintenance
- **Component Traceability**: Each component now provides detailed operation logs

## [1.0.0] - Previous Release

### Added
- Initial DynaDock release
- Dynamic Docker Compose orchestration
- Automatic port allocation
- Caddy reverse proxy integration  
- TLS certificate management with mkcert
- Virtual network interface management
- /etc/hosts automatic configuration
- CLI interface with rich output
- Comprehensive testing framework
- Docker container lifecycle management
- Environment variable generation
- CORS configuration support
- Service health checking
- Domain verification system
