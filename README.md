# 设备运行数据分析系统

## 项目简介

这是一个用于设备运行数据分析的系统，支持上传MDB/SQL数据库文件，并通过AI进行智能分析。

## 功能特性

- **跨平台支持**: Windows、Linux、macOS 均可运行
- **文件解析**: 支持 MDB、ACCDB、SQL、BAK 等数据库文件格式
- **AI分析**: 支持 DeepSeek API 和本地 Ollama 模型（可切换）
- **数据浏览**: 分页查看各表数据
- **历史记录**: 保存分析历史

## 快速启动

### 1. 后端服务

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

### 2. 前端服务

```bash
cd frontend
npm install
npm run dev
```

## 访问地址

- 前端: http://localhost:5174
- 后端API文档: http://localhost:8001/docs

## 配置说明

后端配置文件 `.env` 中可以配置:

- `DEEPSEEK_API_KEY`: DeepSeek API密钥
- `OLLAMA_BASE_URL`: 本地Ollama服务地址
- `USE_LOCAL_MODEL`: 是否默认使用本地模型

## 文件格式支持

| 格式 | 说明 | 跨平台支持 |
|------|------|-----------|
| .mdb | Microsoft Access 97-2003 | ✅ 自动检测 |
| .accdb | Microsoft Access 2007+ | ✅ 自动检测 |
| .sql | MySQL SQL转储文件 | ✅ 纯Python |
| .bak | SQL Server备份文件 | ⚠️ 需要SQL Server |

## MDB文件跨平台解析方案

本系统支持两种MDB解析方式，会**自动检测**可用方案：

### 方案1: pyodbc (Windows优先)
- **Windows**: 需要安装 Access 驱动
- **Linux/macOS**: 需要安装 ODBC 驱动管理器 + Access ODBC 驱动

### 方案2: mdb-tools (Linux/macOS优先)
这是**跨平台最佳方案**，无需安装Access驱动：

#### Linux 安装:
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install mdb-tools

# CentOS/RHEL
sudo yum install mdb-tools

# Arch Linux
sudo pacman -S mdbtools
```

#### macOS 安装:
```bash
brew install mdbtools
```

#### Windows 安装:
```bash
# 使用 Chocolatey
choco install mdbtools

# 或者下载预编译二进制
# https://github.com/mdbtools/mdbtools/releases
```

### 自动检测逻辑
系统会按以下顺序自动选择解析方案：
1. **Windows**: 优先尝试 pyodbc → 失败则尝试 mdb-tools
2. **Linux/macOS**: 优先尝试 mdb-tools → 失败则尝试 pyodbc

## 系统架构

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   前端Vue3   │────▶│  FastAPI    │────▶│   AI模型    │
│  Element+   │     │  后端服务    │     │ DeepSeek/  │
│             │     │             │     │  Ollama    │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  SQLite    │
                    │  数据库    │
                    └─────────────┘
```

## 桌面客户端

桌面客户端正在开发中，可使用 Web 版本作为替代。

## 部署到Linux服务器

在Linux服务器上部署时，确保：

1. 安装 mdb-tools: `sudo apt-get install mdb-tools`
2. 配置 DeepSeek API Key 或部署 Ollama
3. 使用 Gunicorn + Nginx 部署:
```bash
pip install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app
```
