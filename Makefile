.DEFAULT_GOAL := help

# ============================================================================
# Caption-Mate Makefile
# ============================================================================

.PHONY: help
help:  ## 显示所有可用命令
	@echo "Caption-Mate Makefile Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Usage examples:"
	@echo "  make install             # Install dependencies"
	@echo "  make check               # Run all checks"
	@echo "  make nas-ls DIR=/Movies  # List NAS directory"

# ============================================================================
# Installation & Setup
# ============================================================================

.PHONY: install
install:  ## 安装项目依赖和开发工具
	@echo "📦 Installing dependencies..."
	uv sync
	uv run pre-commit install
	@echo "✅ Installation complete!"

.PHONY: dev
dev: install  ## 开发环境完整设置（别名：install）

.PHONY: init
init:  ## 初始化 Caption-Mate 配置
	uv run caption-mate config init

# ============================================================================
# Code Quality
# ============================================================================

.PHONY: format
format:  ## 格式化代码（src + tests）
	@echo "🎨 Formatting code..."
	uv run ruff format src/ tests/
	uv run ruff check --fix src/ tests/
	@echo "✅ Code formatted!"

.PHONY: lint
lint:  ## 检查代码格式和规范
	@echo "🔍 Checking code formatting..."
	@uv run ruff format --check src/ tests/
	@uv run ruff check src/ tests/
	@echo "✅ Code formatting is correct!"

.PHONY: typecheck
typecheck:  ## 运行类型检查
	@echo "🔍 Running type checks..."
	@uv run python3 -m py_compile src/main.py src/mcp_server.py
	@uv run python3 -m py_compile src/core/*.py
	@uv run python3 -m py_compile src/models/*.py
	@uv run python3 -m py_compile src/cli/commands/*.py
	@echo "✅ Type checks passed!"

.PHONY: check
check: lint typecheck  ## 运行所有检查（lint + typecheck）
	@echo "✅ All checks passed!"

# ============================================================================
# Testing
# ============================================================================

.PHONY: pytest
pytest:  ## 运行 pytest 单元测试
	@echo "🧪 Running tests..."
	uv run pytest tests/ -v

.PHONY: test
test: pytest  ## 运行测试（别名：pytest）

.PHONY: nas-test
nas-test:  ## 测试 NAS 连接
	@echo "🔌 Testing NAS connection..."
	uv run caption-mate nas test

# ============================================================================
# NAS Operations (with parameter support)
# ============================================================================

.PHONY: nas-ls
nas-ls:  ## 列出 NAS 目录（用法：make nas-ls DIR=/Movies）
	@if [ -z "$(DIR)" ]; then \
		echo "❌ Error: DIR is required"; \
		echo "Usage: make nas-ls DIR=/Movies"; \
		exit 1; \
	fi
	uv run caption-mate nas ls "$(DIR)"

.PHONY: nas-tree
nas-tree:  ## 显示 NAS 目录树（用法：make nas-tree DIR=/Movies DEPTH=3）
	@if [ -z "$(DIR)" ]; then \
		echo "❌ Error: DIR is required"; \
		echo "Usage: make nas-tree DIR=/Movies [DEPTH=3]"; \
		exit 1; \
	fi
	uv run caption-mate nas tree "$(DIR)" $(if $(DEPTH),--depth $(DEPTH))

.PHONY: nas-scan
nas-scan:  ## 扫描 NAS 视频文件（用法：make nas-scan DIR=/Movies）
	@if [ -z "$(DIR)" ]; then \
		echo "❌ Error: DIR is required"; \
		echo "Usage: make nas-scan DIR=/Movies [RECURSIVE=1]"; \
		exit 1; \
	fi
	uv run caption-mate nas scan "$(DIR)" $(if $(RECURSIVE),--recursive,--no-recursive)

.PHONY: nas-match
nas-match:  ## 匹配字幕（用法：make nas-match DIR=/Movies MODE=ai）
	@if [ -z "$(DIR)" ]; then \
		echo "❌ Error: DIR is required"; \
		echo "Usage: make nas-match DIR=/Movies [MODE=ai|regex] [THRESHOLD=0.8] [DRY_RUN=1]"; \
		exit 1; \
	fi
	uv run caption-mate nas match "$(DIR)" \
		$(if $(MODE),--mode $(MODE)) \
		$(if $(THRESHOLD),--threshold $(THRESHOLD)) \
		$(if $(DRY_RUN),--dry-run)

# ============================================================================
# MCP Server
# ============================================================================

.PHONY: mcp-dev
mcp-dev:  ## 启动 MCP 服务器（开发模式）
	@echo "🚀 Starting MCP server..."
	uv run caption-mate-mcp

.PHONY: mcp-install
mcp-install:  ## 显示 MCP 安装说明
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

# ============================================================================
# Cleanup
# ============================================================================

.PHONY: clean
clean:  ## 清理缓存和临时文件
	@echo "🧹 Cleaning cache and temporary files..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@rm -rf build/ dist/ .eggs/ 2>/dev/null || true
	@echo "✅ Cleanup complete!"

.PHONY: clean-all
clean-all: clean  ## 深度清理（包括 .venv）
	@echo "🧹 Deep cleaning (removing .venv)..."
	@rm -rf .venv activate
	@echo "✅ Deep cleanup complete!"

# ============================================================================
# Build & Publish (Optional)
# ============================================================================

.PHONY: build
build: clean check  ## 构建分发包
	@echo "📦 Building distribution packages..."
	uv build
	@echo "✅ Build complete!"

.PHONY: publish
publish: build  ## 发布到 PyPI（需要凭据）
	@echo "📤 Publishing to PyPI..."
	uv publish
	@echo "✅ Published!"
