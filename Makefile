.PHONY: install
install:
	uv sync
	uv run pre-commit install
	ln -s .venv/bin/activate activate

.PHONY: init
init:
	uv run caption-mate config init

.PHONY: test
test:
	uv run caption-mate nas test

.PHONY: tree
tree:
	uv run caption-mate nas tree

.PHONY: ls
ls:
	uv run caption-mate nas ls

.PHONY: scan
scan:
	uv run caption-mate nas scan
	
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