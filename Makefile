# ─────────────────────────────────────────────
# DuckDB Weather Analytics — Makefile
# ─────────────────────────────────────────────

.PHONY: help install analyse validate export test clean

help:
	@echo "Available commands:"
	@echo "  make install   - Install dependencies"
	@echo "  make analyse   - Run all analytical queries using sample data"
	@echo "  make validate  - Run data quality validation"
	@echo "  make export    - Run analytics and export to Parquet"
	@echo "  make test      - Run unit tests"
	@echo "  make clean     - Remove generated data files and logs"

install:
	pip install -r requirements.txt

analyse:
	python main.py analyse --use-sample

validate:
	python main.py validate --use-sample

export:
	python main.py analyse --use-sample --export

test:
	python -m pytest tests/ -v

clean:
	rm -rf data/raw/*
	rm -rf data/processed/*
	rm -rf data/reports/*
	rm -rf logs/*
	rm -rf __pycache__
	rm -rf src/__pycache__
	find . -name "*.pyc" -delete
	find . -name "*.duckdb" -delete
	find . -name "*.duckdb.wal" -delete
	@echo "Clean complete"