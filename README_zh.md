# Caption-Mate

[English](README.md) | [中文](README_zh.md)

智能字幕管理工具，专为NAS设备设计，支持AI语义匹配和多数据源字幕集成。

## 特性

- **🤖 AI智能匹配**: 使用DeepSeek/OpenAI进行语义匹配，准确匹配视频和字幕文件
- **📁 NAS深度集成**: 通过SMB/CIFS协议无缝连接您的NAS设备
- **🔍 双匹配模式**: AI语义匹配和传统正则匹配两种模式可选
- **📊 多数据源支持**: ASSRT（中文内容优先）和OpenSubtitles（国际内容）自动切换
- **⚡ 批量处理**: 智能匹配整个视频库，支持用户确认和预览
- **🎯 智能过滤**: 自动跳过已有字幕的视频，可调节相似度阈值
- **🌐 多语言支持**: 同时下载多种语言字幕
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

### 字幕下载

```bash
# 自动模式：扫描并下载
uv run caption-mate auto /电影 --dry-run

# 手动下载特定视频字幕
uv run caption-mate subtitles download /电影/示例.mp4

# 批量处理
uv run caption-mate subtitles batch /电影
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

# 字幕数据源
assrt:
  api_token: "your_assrt_token"    # 中文内容
opensubtitles:
  api_key: "your_opensubtitles_key" # 国际内容
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
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   字幕数据源     │◀───│   下载引擎        │◀───│   匹配结果       │
│ (ASSRT/OpenSubs)│    │                  │    │  (用户确认)      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### 核心组件

- **NAS客户端**: SMB/CIFS连接管理
- **视频扫描器**: 递归视频文件发现
- **字幕匹配器**: AI语义匹配 + 正则回退
- **多源引擎**: ASSRT（中文）+ OpenSubtitles（国际）
- **安全操作**: 干运行预览 + 用户确认

## API配置

### AI匹配模式配置

设置OpenAI兼容API（推荐DeepSeek）：

```bash
export OAI_MODEL="deepseek-reasoner"
export OAI_API_KEY="your_api_key"
export OAI_BASE_URL="https://api.deepseek.com"
```

### 字幕数据源

**ASSRT（中文内容）**:

```bash
uv run caption-mate config set assrt.api_token "your_32_char_token"
```

**OpenSubtitles（国际内容）**:

```bash
uv run caption-mate config set opensubtitles.api_key "your_api_key"
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

## 字幕数据源对比

### ASSRT（默认优先）

- **优势**: 中文字幕资源丰富，社区活跃
- **搜索方式**: 基于文本搜索
- **语言支持**: 中文、英文、日韩等多种语言
- **特点**: 对中文影视作品支持最佳
- **限制**: 需要注册获取API token，有速率限制

### OpenSubtitles

- **优势**: 国际化字幕资源，支持哈希匹配
- **搜索方式**: 文件哈希匹配 + 文本搜索
- **语言支持**: 全球多种语言
- **特点**: 哈希匹配准确度最高
- **限制**: 需要API key，对中文资源相对较少

### 使用建议

- **中文内容**: 优先使用ASSRT，AI模式效果更佳
- **国外内容**: OpenSubtitles提供更好支持
- **最佳效果**: 不指定provider，让系统自动尝试所有数据源
- **复杂命名**: 使用AI模式处理混合语言和复杂命名规则

## 贡献

欢迎贡献代码！请随时提交Pull Request。

## 许可证

MIT许可证 - 详见LICENSE文件。