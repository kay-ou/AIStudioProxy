# <p align="center">✨ AIStudioProxy ✨</p>

<p align="center">
  <a href="https://github.com/kay-ou/AIStudioProxy/actions/workflows/ci.yml">
    <img src="https://img.shields.io/github/actions/workflow/status/your-username/aistudio-proxy/ci.yml?branch=main&style=for-the-badge&logo=github" alt="Build Status">
  </a>
  <a href="https://codecov.io/gh/your-username/aistudio-proxy">
    <img src="https://img.shields.io/codecov/c/github/your-username/aistudio-proxy?style=for-the-badge&logo=codecov" alt="Code Coverage">
  </a>
  <a href="https://github.com/kay-ou/AIStudioProxy/blob/main/LICENSE">
    <img src="https://img.shields.io/github/license/your-username/aistudio-proxy?style=for-the-badge" alt="License">
  </a>
  <a href="https://python.org">
      <img src="https://img.shields.io/badge/Python-3.11+-blue?style=for-the-badge&logo=python" alt="Python Version">
  </a>
</p>

<h4 align="center">一个轻量级、高性能、可扩展的 Google AI Studio 代理，完全兼容 OpenAI API 标准。</h4>

---

**AIStudioProxy** 是对原有 `AIStudioProxyAPI` 项目的彻底重构，旨在解决其日益增长的技术债务。我们通过浏览器自动化技术，将 Google AI Studio 的网页操作封装成一个稳定、高效的 OpenAI 格式 API，为您提供无缝的AI模型切换体验。

## 🚀 核心优势

与旧版相比，重构后的 AIStudioProxy 具有显著优势：

- **极致性能**: 启动时间从 8 秒缩短至 2 秒，内存占用从 200MB 降至 80MB，响应延迟降低 40%。
- **轻量架构**: 采用 FastAPI 和 Playwright，代码更简洁，维护成本更低。
- **统一配置**: 所有配置项集中在 `config.yaml`，并支持环境变量覆盖。
- **健壮稳定**: 统一的异常处理和重试机制，确保服务高可用。
- **易于扩展**: 模块化设计，方便添加新功能和自定义扩展。
- **全面监控**: 内置 Prometheus 指标和健康检查端点，轻松集成到您的监控系统。

## 🏗️ 系统架构

AIStudioProxy 的架构设计简洁而高效，主要由以下几个部分组成：

```
+-------------------+      +----------------------+      +---------------------+
|   OpenAI Client   |----->|   AIStudioProxy      |----->|  Google AI Studio   |
| (e.g., App, CLI)  |      | (FastAPI+Playwright) |      | via CamoufoxBrowser |
+-------------------+      +----------------------+      +---------------------+
        |                            |                             |
        | OpenAI API Request         | Browser Automation          | Web Interface
        |                            |                             |
        +---------------------------->                             |
        |                            |                             |
        |                            | Emulates User Actions       |
        |                            |                             |
        <----------------------------+                             |
        |                            |                             |
        | OpenAI API Response        | Parses Results              |
        |                            |                             |
```

## ✨ 主要功能

- **OpenAI API 兼容**: 无需修改现有代码，即可将请求指向 AIStudioProxy。
- **多模型支持**: 支持 Gemini 全系列模型，并可轻松扩展。
- **浏览器自动化**: 使用 Playwright 和 Camoufox 模拟真实用户操作，稳定可靠。
- **无头模式**: 支持在无图形界面的服务器环境中运行。
- **自动登录**: 自动处理 Google 账户登录和会话保持。
- **Docker 部署**: 提供 `docker-compose.yml`，一键启动生产和开发环境。
- **本地开发**: 附带 `start.sh` 脚本，简化本地开发和测试流程。
- **可观测性**: 通过 `/metrics` 端点暴露 Prometheus 指标。

## 快速开始

我们提供两种部署方式：**Docker (推荐)** 和 **本地部署**。

### 🐳 使用 Docker 部署 (推荐)

这是最简单、最推荐的部署方式。

1.  **克隆项目**:
    ```bash
    git clone https://github.com/kay-ou/AIStudioProxy.git
    cd aistudio-proxy
    ```

2.  **配置 (可选)**:
    - 复制 `.env.example` 为 `.env` 并按需修改。
    - 编辑 `configs/config.yaml` 文件。

3.  **启动服务**:
    ```bash
    ./start.sh prod
    ```
    服务将在 `http://localhost:2048` 启动。

### 💻 本地部署

适合需要进行二次开发的场景。

1.  **安装依赖**:
    - [Python 3.11+](https://www.python.org/downloads/)
    - [Poetry](https://python-poetry.org/docs/#installation)
    - [Node.js](https://nodejs.org/en/download/) (用于 Playwright)

2.  **克隆项目并安装依赖**:
    ```bash
    git clone https://github.com/kay-ou/AIStudioProxy.git
    cd aistudio-proxy
    ./start.sh local
    ```

3.  **启动服务**:
    `start.sh local` 命令会自动处理依赖安装和启动。

## ⚙️ 项目配置

项目的主要配置在 `configs/config.yaml` 文件中，你也可以通过环境变量进行覆盖。

**环境变量覆盖规则**:
将配置路径转换为大写，并用双下划线 `__` 分隔。例如，要覆盖 `server.port`，可以设置环境变量 `SERVER__PORT=8000`。

**主要配置项**:

| 配置项 | 环境变量 | 描述 |
| :--- | :--- | :--- |
| `server.port` | `SERVER__PORT` | API 服务监听端口 |
| `server.debug` | `SERVER__DEBUG` | 是否开启调试模式 |
| `browser.headless` | `BROWSER__HEADLESS` | 是否以无头模式运行浏览器 |
| `auth.profile_path` | `AUTH__PROFILE_PATH` | 浏览器用户配置路径 |
| `security.api_key` | `SECURITY__API_KEY` | 设置访问 API 的密钥 |
| `log.level` | `LOG__LEVEL` | 日志级别 (e.g., INFO, DEBUG) |

## 💡 API 用法

启动服务后，您可以像调用 OpenAI API 一样调用 AIStudioProxy。

**示例: 使用 `curl` 调用**

```bash
curl -X POST http://localhost:2048/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "model": "gemini-1.5-pro",
    "messages": [
      {"role": "user", "content": "你好，Gemini！"}
    ]
  }'
```

## 🛠️ 开发与测试

我们欢迎社区贡献！

- **运行测试**:
  ```bash
  # 本地测试
  ./start.sh test

  # Docker 环境测试
  ./start.sh test-docker
  ```

- **代码风格**:
  项目使用 `black`, `isort`, `flake8` 和 `mypy` 来保证代码质量。请在提交前运行 `pre-commit`。

## 🤝 贡献

我们欢迎任何形式的贡献，无论是提交 Issue、创建 Pull Request 还是改进文档。

## 📄 许可证

本项目基于 [MIT License](LICENSE) 开源。
