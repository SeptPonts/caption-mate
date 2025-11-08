# Caption-Mate

[English](README.md) | [中文](README_zh.md)

智能字幕匹配工具，专为NAS设备设计，支持AI语义匹配实现精准的字幕-视频配对。

## 特性

- **🤖 AI智能匹配**: 使用DeepSeek/OpenAI进行语义匹配，准确匹配视频和字幕文件
- **📁 NAS深度集成**: 通过SMB/CIFS协议无缝连接您的NAS设备
- **🔌 MCP集成**: 通过模型上下文协议在Claude Code中直接使用Caption-Mate
- **🔍 双匹配模式**: AI语义匹配和传统正则匹配两种模式可选
- **⚡ 批量处理**: 智能匹配整个视频库，支持用户确认和预览
- **🎯 智能过滤**: 可调节相似度阈值实现精准匹配
- **🌐 多语言支持**: 处理多种语言的字幕文件
- **✅ 安全操作**: 干运行预览和用户确认机制

## 快速开始

### 安装

```bash
git clone https://github.com/SeptPonts/caption-mate.git
cd caption-mate
make install
```

### 配置

```bash
# 初始化配置
uv run caption-mate config init

# 测试NAS连接
uv run caption-mate nas test
```

### 基本使用

```bash
# 智能字幕匹配（AI模式 - 推荐）
uv run caption-mate nas match /电影/第一季 --mode ai --dry-run

# 传统正则匹配
uv run caption-mate nas match /电影/第一季 --mode regex --dry-run

# 预览后执行
uv run caption-mate nas match /电影/第一季 --mode ai
```

## MCP 集成

Caption-Mate 可以通过模型上下文协议（MCP）在 Claude Code 中直接使用，实现对话式字幕管理。

### 什么是 MCP 模式？

MCP 模式允许 Claude 通过自然对话操作您的 NAS 字幕系统：
- **CLI 模式**: 您需要手动输入终端命令
- **MCP 模式**: 您只需描述需求，Claude 自动执行操作

### 安装配置

**方式 1: 快速设置**
```bash
make mcp-install
```

**方式 2: 手动配置**

在 Claude Code 的 MCP 设置中添加：
```json
{
  "caption-mate": {
    "command": "uv",
    "args": ["run", "--directory", "/path/to/caption-mate", "caption-mate-mcp"]
  }
}
```

将 `/path/to/caption-mate` 替换为您的实际项目路径。

### 可用工具

MCP 服务器为 Claude 提供了 5 个工具：

| 工具 | 功能说明 | 主要参数 |
|------|---------|---------|
| `nas_test` | 测试 NAS 连接并列出共享 | 无 |
| `nas_ls` | 列出文件和目录 | `path`, `long`, `pattern` |
| `nas_tree` | 显示目录树结构 | `path`, `depth` |
| `nas_scan` | 扫描视频文件 | `path`, `recursive` |
| `nas_match` | **匹配并重命名字幕** | `path`, `mode`, `threshold`, `dry_run` |

### 使用示例

**交互式工作流程：**

```
您: "检查我的 NAS 是否连接正常"
Claude: [调用 nas_test 工具]
→ 显示连接状态和可用共享

您: "/电影/第一季 里有哪些视频文件？"
Claude: [调用 nas_scan，path="/电影/第一季"]
→ 列出找到的所有视频文件

您: "用 AI 模式匹配字幕，先给我预览一下"
Claude: [调用 nas_match，mode="ai", dry_run=true]
→ 显示计划的字幕匹配方案

您: "看起来不错，执行吧"
Claude: [调用 nas_match，mode="ai", dry_run=false]
→ 重命名字幕文件以匹配视频
```

### MCP 模式 vs CLI 模式对比

| 对比项 | MCP 模式 | CLI 模式 |
|-------|---------|---------|
| **交互方式** | 自然语言对话 | 终端命令 |
| **最适合** | 交互式探索、一次性任务 | 自动化脚本、定时任务 |
| **学习曲线** | 低（只需描述需求） | 中等（需要了解命令） |
| **灵活性** | 高（Claude 理解意图） | 高（完全命令控制） |
| **使用场景** | "查找并匹配所有字幕" | `caption-mate nas match /path --mode ai` |

**何时使用 MCP：**
- 探索 NAS 上的新目录
- 测试不同的匹配阈值
- 一次性清理任务
- 学习工具的使用方法

**何时使用 CLI：**
- 自动化脚本和 cron 定时任务
- 批处理流水线
- CI/CD 集成
- 可重复的工作流程

## 核心命令

### NAS管理

```bash
# 浏览NAS目录
uv run caption-mate nas ls /电影
uv run caption-mate nas tree /电影 --depth 3

# 扫描视频文件
uv run caption-mate nas scan /电影
```

### 智能匹配 (⭐ 核心功能)

```bash
# AI语义匹配（适用于混合内容）
uv run caption-mate nas match /视频路径 --mode ai --threshold 0.8

# 传统正则匹配（快速、基于规则）
uv run caption-mate nas match /视频路径 --mode regex --threshold 0.8

# 执行前预览
uv run caption-mate nas match /视频路径 --mode ai --dry-run

# 强制覆盖现有字幕
uv run caption-mate nas match /视频路径 --mode ai --force
```

### 配置管理

```bash
uv run caption-mate config init          # 交互式配置
uv run caption-mate config show          # 显示当前配置
uv run caption-mate config set nas.host 192.168.1.100
```

## AI模式 vs 正则模式

### AI模式（推荐）

- **适用于**: 混合语言内容、复杂命名的电视剧
- **优势**: 理解语义含义，处理季/集信息，跨语言匹配
- **使用场景**: "The Man in the High Castle S01E01" ↔ "高堡奇人.S01E01.新世界.zh-hans.srt"

### 正则模式（传统）

- **适用于**: 命名规范一致的内容，性能要求高的场景
- **优势**: 处理速度快，结果可预测，无需API依赖
- **使用场景**: 标准发布组格式，清晰的命名模式

## 配置文件

创建 `~/.caption-mate/config.yaml` 或使用环境变量：

```yaml
# AI配置（用于AI匹配模式）
# 环境变量: OAI_MODEL, OAI_API_KEY, OAI_BASE_URL

nas:
  protocol: "smb"
  host: "192.168.1.100"
  username: "your_nas_user"
  password: "your_nas_password"

subtitles:
  languages: ["zh-cn", "en"]
  formats: ["srt", "ass"]
  naming_pattern: "{filename}.{lang}.{ext}"
```

## 使用示例

### 电视剧处理

```bash
# 预览AI匹配电视剧
uv run caption-mate nas match "/电视剧/办公室 第一季" --mode ai --dry-run

# 执行（含用户确认）
uv run caption-mate nas match "/电视剧/办公室 第一季" --mode ai

# 批量处理整部剧集
uv run caption-mate nas scan "/电视剧/办公室" --recursive
uv run caption-mate nas match "/电视剧/办公室" --mode ai --threshold 0.9
```

### 电影收藏

```bash
# 高精度阈值处理电影目录
uv run caption-mate nas match "/电影/动作片" --mode ai --threshold 0.95

# 规范命名使用正则模式
uv run caption-mate nas match "/电影/YIFY" --mode regex --threshold 0.8
```

### 混合内容

```bash
# AI模式擅长处理混合语言内容
uv run caption-mate nas match "/亚洲电影" --mode ai --dry-run
```

## 系统架构

```text
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   NAS客户端      │───▶│   视频扫描器      │───▶│  字幕匹配器      │
│   (SMB/CIFS)    │    │                  │    │  (AI/正则)      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
                                                         ▼
                                                ┌─────────────────┐
                                                │   匹配结果       │
                                                │  (用户确认)      │
                                                └─────────────────┘
```

### 核心组件

- **NAS客户端**: SMB/CIFS连接管理
- **视频扫描器**: 递归视频文件发现
- **字幕匹配器**: AI语义匹配 + 正则回退
- **安全操作**: 干运行预览 + 用户确认

## API配置

### AI匹配模式配置

设置OpenAI兼容API（推荐DeepSeek）：

```bash
export OAI_MODEL="deepseek-reasoner"
export OAI_API_KEY="your_api_key"
export OAI_BASE_URL="https://api.deepseek.com"
```

## 故障排除

### AI模式问题

- 验证API凭据和模型可用性
- 检查到AI服务的网络连接
- 尝试正则模式作为调试回退

### 匹配精度

- 降低 `--threshold` 值获得更多匹配
- 使用 `--dry-run` 预览结果
- AI模式通常在复杂情况下提供更好的精度

### NAS连接

- 验证NAS上已启用SMB/CIFS
- 检查防火墙设置
- 尝试使用IP地址而非主机名

## 开发

```bash
git clone https://github.com/SeptPonts/caption-mate.git
cd caption-mate
make install
make test
```

## 贡献

欢迎贡献代码！请随时提交Pull Request。

## 许可证

MIT许可证 - 详见LICENSE文件。