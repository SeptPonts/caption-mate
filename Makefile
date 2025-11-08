.PHONY: install
install:
	uv sync
	uv run pre-commit install
	uv pip install -e .
	ln -sf .venv/bin/activate activate

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

.PHONY: mcp-dev
mcp-dev:
	uv run caption-mate-mcp

.PHONY: mcp-install
mcp-install:
	@echo "=== Caption-Mate MCP Server Installation ==="
	@echo ""
	@echo "Add this to your Claude Code MCP settings:"
	@echo ""
	@echo '{'
	@echo '  "caption-mate": {'
	@echo '    "command": "uv",'
	@echo '    "args": ["run", "--directory", "$(PWD)", "caption-mate-mcp"]'
	@echo '  }'
	@echo '}'
	@echo ""
	@echo "Configuration file location:"
	@echo "  macOS: ~/Library/Application Support/Claude/claude_desktop_config.json"
	@echo "  Linux: ~/.config/Claude/claude_desktop_config.json"
	@echo "  Windows: %APPDATA%\\Claude\\claude_desktop_config.json"
	@echo ""
	@echo "After adding, restart Claude Code to activate the MCP server."