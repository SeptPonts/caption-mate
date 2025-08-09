.PHONY: install
install:
	uv sync
	uv run pre-commit install

.PHONY: run
run:
	uv run python src/main.py

.PHONY: format
format:
	uv run ruff format src/
	uv run ruff check --fix src/

.PHONY: lint
lint:
	@echo "Checking code formatting..."
	uv run ruff format --check src/
	uv run ruff check src/
	@echo "Code formatting is correct!"