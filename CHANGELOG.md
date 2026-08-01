# Changelog

## [1.0.0] - 2026-07-24

### Changed
- Renamed project from Convert_MCQ to MCQ-Format-Standardizer
- Unified all naming across codebase, UI, and documentation
- Stripped requirements.txt to runtime-only dependencies
- Refactored monolithic gui/app.py into focused modules (drop_zone, file_manager, converter)

### Added
- MIT License
- GitHub Actions CI (Python 3.10–3.12, flake8, pytest)
- Issue templates (bug report, feature request)
- CONTRIBUTING.md and CODE_OF_CONDUCT.md
- Basic test suite for parser engine
- CHANGELOG.md
- Type hints to parser modules

### Fixed
- Safer sys.path handling in main.py
- Flake8 F824 lint issue with global variable in config.py
- Truncated string in chat_sidebar.py
- Node.js deprecation warnings in CI actions
