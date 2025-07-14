# AIStudioProxy 用户使用指南

欢迎使用 AIStudioProxy！本指南将帮助您快速安装、配置和使用本项目。

## 目录

- [1. 简介](#1-简介)
- [2. 核心功能](#2-核心功能)
- [3. 安装与部署](#3-安装与部署)
  - [先决条件](#先决条件)
  - [使用 Docker (推荐)](#使用-docker-推荐)
  - [本地开发环境](#本地开发环境)
- [4. 配置详解](#4-配置详解)
  - [配置文件](#配置文件)
  - [环境变量覆盖](#环境变量覆盖)
  - [配置项说明](#配置项说明)
- [5. API 使用方法](#5-api-使用方法)
  - [获取 API 密钥](#获取-api-密钥)
  - [Curl 示例](#curl-示例)
  - [Python 示例](#python-示例)
- [6. 故障排查 (FAQ)](#6-故障排查-faq)
- [7. 参与贡献](#7-参与贡献)
- [8. 许可证](#8-许可证)

---

## 1. 简介

AIStudioProxy 是一个轻量级、高性能、可扩展的 Google AI Studio 代理，它将 AI Studio 的网页操作封装成一个完全兼容 OpenAI API 标准的服务。

无论您是想将现有的 OpenAI 应用无缝切换到 Gemini 模型，还是希望在一个统一的接口后使用多种模型，AIStudioProxy 都能为您提供稳定、高效的解决方案。

## 2. 核心功能

- **OpenAI API 兼容**: 无需修改现有代码，即可将请求指向 AIStudioProxy。
- **多模型支持**: 支持 Gemini 全系列模型，并可轻松扩展。
- **浏览器自动化**: 使用 Playwright 和 Camoufox 模拟真实用户操作，稳定可靠。
- **无头模式**: 支持在无图形界面的服务器环境中运行。
- **自动登录**: 自动处理 Google 账户登录和会话保持。
- **Docker 部署**: 提供 `docker-compose.yml`，一键启动生产和开发环境。
- **可观测性**: 通过 `/metrics` 端点暴露 Prometheus 指标。

---

## 3. 安装与部署

您可以选择使用 Docker 进行一键部署，或在本地手动设置开发环境。

### 先决条件

- **通用**: `git`
- **本地部署**:
  - [Python 3.11+](https://www.python.org/downloads/)
  - [Poetry](https://python-poetry.org/docs/#installation) (Python 包管理器)
  - [Node.js](https://nodejs.org/en/download/) (Playwright 依赖)

### 使用 Docker (推荐)

这是最简单、最推荐的部署方式，所有依赖都已在 Docker 镜像中预装。

1.  **克隆项目**:
    ```bash
    git clone https://github.com/kay-ou/AIStudioProxy.git
    cd AIStudioProxy
    ```

2.  **配置 (可选)**:
    - 复制 `.env.example` 为 `.env` 并按需修改。
    - 编辑 `configs/config.yaml` 文件。详情请见 [配置详解](#4-配置详解) 章节。

3.  **启动服务**:
    ```bash
    # 启动生产环境
    ./start.sh prod

    # 查看日志
    docker-compose logs -f
    ```
    服务启动后，将在 `http://localhost:2048` (或您配置的端口) 上监听请求。

### 本地开发环境

适合需要进行二次开发或调试的场景。

1.  **克隆项目**:
    ```bash
    git clone https://github.com/kay-ou/AIStudioProxy.git
    cd AIStudioProxy
    ```

2.  **安装依赖并启动**:
    `start.sh` 脚本会自动处理所有依赖安装和环境设置。
    ```bash
    # 这将安装 Python & Node.js 依赖，并启动服务
    ./start.sh local
    ```
    该脚本会使用 Poetry 创建虚拟环境，安装 Playwright 及其浏览器驱动，最后启动 FastAPI 应用。

---

## 4. 配置详解

### 配置文件

项目的主要配置位于 `configs/config.yaml`。我们建议您通过环境变量来覆盖配置，而不是直接修改此文件，以便于版本更新。

### 环境变量覆盖

您可以通过设置环境变量来覆盖 `config.yaml` 中的任何配置。规则如下：

- 将配置路径转换为 **大写**。
- 使用 **双下划线 `__`** 代替层级分隔符 `.`。

**示例**:
要覆盖 `server.port`，设置环境变量 `SERVER__PORT=8000`。
要覆盖 `browser.headless`，设置环境变量 `BROWSER__HEADLESS=false`。

### 配置项说明

| 分类 | 配置项 | 环境变量 | 描述 | 默认值 |
| :--- | :--- | :--- | :--- | :--- |
| **Server** | `server.host` | `SERVER__HOST` | 服务监听的主机地址 | `0.0.0.0` |
| | `server.port` | `SERVER__PORT` | 服务监听的端口 | `2048` |
| | `server.workers` | `SERVER__WORKERS` | Uvicorn工作进程数 | `1` |
| | `server.debug` | `SERVER__DEBUG` | 是否开启FastAPI调试模式 | `false` |
| **Browser** | `browser.headless` | `BROWSER__HEADLESS` | 是否以无头模式运行浏览器 | `true` |
| | `browser.port` | `BROWSER__PORT` | 浏览器远程调试端口 | `9222` |
| | `browser.timeout` | `BROWSER__TIMEOUT` | Playwright操作的默认超时时间(毫秒) | `30000` |
| | `browser.initial_pool_size` | `BROWSER__INITIAL_POOL_SIZE` | 启动时创建的浏览器页面池大小 | `5` |
| **Auth** | `auth.profile_path` | `AUTH__PROFILE_PATH` | 浏览器用户配置文件的路径 | `null` |
| | `auth.auto_login` | `AUTH__AUTO_LOGIN` | 是否尝试自动登录 | `true` |
| | `auth.session_timeout` | `AUTH__SESSION_TIMEOUT` | 会话超时时间(秒) | `3600` |
| | `auth.cookie_path` | `AUTH__COOKIE_PATH` | 存储登录cookies的文件路径 | `null` |
| **Log** | `log.level` | `LOG__LEVEL` | 日志级别 (e.g., INFO, DEBUG) | `INFO` |
| | `log.format` | `LOG__FORMAT` | 日志格式 (json 或 console) | `json` |
| **Performance**| `performance.max_concurrent_requests` | `PERFORMANCE__MAX_CONCURRENT_REQUESTS` | 最大并发请求数 | `50` |
| | `performance.request_timeout` | `PERFORMANCE__REQUEST_TIMEOUT` | 请求处理的超时时间(秒) | `60` |
| **Security** | `security.api_keys` | `SECURITY__API_KEYS` | 有效的API密钥列表 | `["your-secret-api-key-here"]` |
| | `security.rate_limit` | `SECURITY__RATE_LIMIT` | 每分钟的请求速率限制 | `100` |
| **Models** | `supported_models` | `SUPPORTED_MODELS` | 支持的Gemini模型列表 | `[...]` |

---

## 5. API 使用方法

AIStudioProxy 实现了与 OpenAI API 完全兼容的接口。您可以像使用 OpenAI API 一样使用它。

### 获取 API 密钥

您需要在 `configs/config.yaml` 的 `api.keys` 列表中设置至少一个 API 密钥，或者通过 `API__KEYS` 环境变量来设置。

**示例 `config.yaml`**:
```yaml
api:
  keys:
    - "my-secret-key-1"
    - "my-secret-key-2"
```

在发送请求时，请将所选的密钥放入 `Authorization` 请求头中。

### Curl 示例

```bash
curl -X POST http://localhost:2048/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer my-secret-key-1" \
  -d '{
    "model": "gemini-1.5-pro",
    "messages": [
      {"role": "user", "content": "你好，Gemini！请介绍一下你自己。"}
    ],
    "stream": false
  }'
```

### Python 示例

确保您已安装 `openai` 库 (`pip install openai`)。

```python
import openai

# 指向 AIStudioProxy 服务
client = openai.OpenAI(
    base_url="http://localhost:2048/v1",
    api_key="my-secret-key-1"  # 使用您配置的密钥
)

try:
    # 非流式请求
    print("--- Non-Streaming Request ---")
    chat_completion = client.chat.completions.create(
        model="gemini-1.5-pro",
        messages=[
            {"role": "user", "content": "写一首关于宇宙的短诗。"}
        ],
        max_tokens=100,
        temperature=0.7,
    )
    print(chat_completion.choices[0].message.content)

    # 流式请求
    print("\n--- Streaming Request ---")
    stream = client.chat.completions.create(
        model="gemini-1.5-flash",
        messages=[
            {"role": "user", "content": "从1数到10，并用文字描述每个数字。"}
        ],
        stream=True,
    )
    for chunk in stream:
        content = chunk.choices[0].delta.content
        if content:
            print(content, end="", flush=True)
    print()

except openai.APIError as e:
    print(f"An API error occurred: {e}")

```

---

*本指南正在编写中，将逐步完善更多章节内容。*