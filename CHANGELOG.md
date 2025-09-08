# Changelog

All notable changes to DynaDock will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2025-09-08

### Added
- Fixed all `mypy` type errors for a clean build.
- Updated documentation with dynamic badges, author information, and contribution guide.
- Enhanced `Makefile` with a robust `clean` command to handle root-owned files.
- Added `.gitignore` rules for generated files to prevent dirty working directory issues.

### Fixed
- Resolved issues with publishing workflow by ensuring a clean working directory.
- Updated domain references to be consistent across documentation.

### Known Issues
- CLI entry point may have import issues after PyPI installation.
- Pytest configuration needs adjustment for proper test execution.
- Examples require validation and potential updates.

## [1.1.0] - 2024-09-07

### Added
- **Enhanced Logging System**: Added comprehensive `--verbose/-v` flag support across all components
- **Detailed CLI Logging**: Step-by-step operation logging with timing metrics
- **Comprehensive Diagnostic Framework**: Advanced network analysis, system checking, and performance monitoring
- **Log File Output**: Automatic log file generation in `.dynadock/dynadock.log`
- **Structured Error Reporting**: Clear, actionable error messages with debugging information

### Enhanced
- **DockerManager**: Added verbose logging for all Docker operations and commands
- **NetworkManager**: Enhanced logging for virtual interface management and network operations
- **CaddyConfig**: Detailed logging for configuration generation and template processing
- **EnvGenerator**: Verbose logging for environment variable generation and processing
- **PortAllocator**: Enhanced logging for port allocation and conflict resolution

### Improved
- **Testing Framework**: Comprehensive diagnostic tools with timing metrics and detailed reporting
- **Debug Capabilities**: Enhanced troubleshooting with network connectivity analysis
- **Performance Monitoring**: Added timing metrics for all major operations
- **User Experience**: Clear progress indicators and detailed operation feedback

### Fixed
- **Test Structure**: Removed duplicate domain test files and reorganized diagnostic scripts
- **Project Organization**: Moved diagnostic files to dedicated `diagnostics/` directory
- **Makefile**: Fixed `publish` target by removing missing `repair-docs` dependency

### Technical Details
- Enhanced logging implemented across all core components
- Centralized logging configuration with file output support
- Advanced diagnostic capabilities for network and system analysis
- Comprehensive testing framework with performance metrics
- Structured JSON reporting for automated analysis

### Known Issues
- CLI entry point may have import issues after PyPI installation
- Pytest configuration needs adjustment for proper test execution
- Examples require validation and potential updates

### Diagnostic Framework
- **Performance Metrics**: Timing information for all network and system operations
- **Error Diagnostics**: Clear failure identification with specific error details
- **Three-Domain Test Coverage**: Comprehensive testing for:
  - `http://localhost:8000` (direct localhost access)
  - `https://frontend.dynadock.lan` (frontend local domain)
  - `https://mailhog.dynadock.lan` (MailHog local domain)
- **Screenshot Verification**: Browser-based visual proof of service accessibility
- **Structured Reporting**: JSON output with detailed statistics and recommendations

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
