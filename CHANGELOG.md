# Changelog

All notable changes to this project are documented here.

## [1.0.0] - 2026-05-26

### Added
- 8 OLAP analytical queries covering temperature, humidity, wind, anomaly detection and city rankings
- 8 data quality validation checks before any analysis begins
- DuckDB 1.5.3 as the OLAP engine with in-memory vectorised execution
- PostgreSQL connector with retry logic and connection pooling
- Parquet export via PyArrow with Snappy compression
- CLI interface with Click — analyse, validate and export commands
- APScheduler for hourly scheduled analytics runs
- Sample data mode for running analytics without PostgreSQL
- 29 pytest unit tests covering all queries and validators
- GitHub Actions CI pipeline running tests on every push
- Makefile with shortcuts for analyse, validate, export, test and clean
- CONTRIBUTING.md with contribution guidelines
- Mermaid architecture diagram in README
