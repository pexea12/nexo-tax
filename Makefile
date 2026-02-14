.PHONY: test lint typecheck check fmt run audit

test:
	uv run pytest tests/ -v

lint:
	uv run ruff check nexo_tax/ tests/

typecheck:
	uv run ty check nexo_tax/ tests/

fmt:
	uv run ruff format nexo_tax/ tests/

check: lint typecheck test

run:
	uv run nexo-tax data/nexo_2024.csv data/nexo_2025.csv --year 2024 2025

audit:
	uv run nexo-tax data/nexo_2024.csv data/nexo_2025.csv --year 2024 2025 --audit-csv
