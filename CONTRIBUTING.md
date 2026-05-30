# Contributing to DuckDB Weather Analytics

Thank you for your interest in contributing to this project. This document explains how to set up the development environment and contribute effectively.

---

## Prerequisites

Before contributing, make sure you have the following installed:

- Python 3.11+
- pip
- Git

---

## Getting Started

**1. Fork and clone the repository**

```bash
git clone https://github.com/YOUR-USERNAME/duckdb-analytics.git
cd duckdb-analytics
```

**2. Create a feature branch**

```bash
git checkout -b feat/your-feature-name
```

**3. Install dependencies**

```bash
pip install -r requirements.txt
```

**4. Configure environment variables**

```bash
cp .env.example .env
# Edit .env with your PostgreSQL credentials
```

---

## Running the Project

**Run analytics with sample data (no PostgreSQL needed)**

```bash
python main.py analyse --use-sample
```

**Run with real PostgreSQL data**

```bash
python main.py analyse
```

**Run data quality validation**

```bash
python main.py validate --use-sample
```

---

## Code Standards

**Run tests before every commit:**

```bash
python -m pytest tests/ -v
```

All 29 tests must pass before submitting a pull request.

**Naming conventions:**
- Functions: lowercase with underscores — e.g. `run_all_queries`
- Classes: PascalCase — e.g. `DataValidator`
- Constants: uppercase — e.g. `TRACKED_CITIES`

**Adding a new analytical query:**
1. Add the query method to `src/queries/weather_queries.py`
2. Add it to the `run_all` method
3. Add a corresponding test in `tests/test_queries.py`

**Adding a new validation check:**
1. Add the check method to `src/validators/data_validator.py`
2. Add it to the `run_all` method
3. Add a corresponding test in `tests/test_validator.py`

---

## Submitting a Pull Request

1. Run all tests and make sure they pass
2. Commit with a clear message:
type: short description

Detail 1
Detail 2


Types: `feat`, `fix`, `docs`, `test`, `refactor`

3. Push your branch and open a pull request against `main`
4. Describe what you changed and why

---

## Author

**Ojong Bessong NKONGHO**
Data Engineering Student — DSTI School of Engineering, Paris

[![LinkedIn](https://img.shields.io/badge/LinkedIn-nkongho--ojong-0077B5?style=flat&logo=linkedin)](https://linkedin.com/in/nkongho-ojong)
[![GitHub](https://img.shields.io/badge/GitHub-OjongBessongNKONGHO-181717?style=flat&logo=github)](https://github.com/OjongBessongNKONGHO)
