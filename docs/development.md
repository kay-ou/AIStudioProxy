# AIStudioProxy 重写项目架构与实现路线

## 📋 项目概述

**AIStudioProxy** 是对现有AIStudioProxy项目的完全重写，专注于提供一个**轻量级、高性能、易维护**的Google AI Studio代理服务，通过浏览器自动化技术将AI Studio包装成标准的OpenAI API格式。

### 🎯 重写目标

- **代码量减少85%** (15,000行 → 2,000行)
- **启动时间减少75%** (8-12秒 → 2-3秒)
- **内存占用减少60%** (200MB → 80MB)
- **依赖减少80%** (42个 → 8个)
- **维护复杂度降低90%**

### 🔍 核心功能保留

1. **浏览器自动化** - Playwright + Camoufox 控制AI Studio
2. **OpenAI API兼容** - 标准的 `/v1/chat/completions` 端点
3. **模型管理** - 支持Gemini系列模型切换
4. **认证管理** - Google账户认证和会话保持
5. **流式响应** - 支持Server-Sent Events流式输出

## 🏗️ 新架构设计

### 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    AIStudioProxy                         │
├─────────────────────────────────────────────────────────────┤
│  API Layer (FastAPI)                                       │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ POST /v1/chat/completions (API Key Auth)                │ │
│  │ GET  /v1/models                                         │ │
│  │ GET  /health                                            │ │
│  └─────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  Core Engine                                                │
│  ┌──────────────────────────┬──────────────────────────┐    │
│  │ RequestHandler           │ ResponseFormatter        │    │
│  │ - Concurrency control    │ - Format OpenAI response │    │
│  │ - Orchestrates flow      │ - Handle streaming       │    │
│  │ - Manages browser pages  │ - Token counting         │    │
│  └──────────────────────────┴──────────────────────────┘    │
├─────────────────────────────────────────────────────────────┤
│  Browser Layer                                              │
│  ┌──────────────────────────┬──────────────────────────┐    │
│  │ BrowserManager           │ PageController           │    │
│  │ - Launch/stop browser    │ - Send message           │    │
│  │ - Manage page pool       │ - Switch model           │    │
│  │ - Health check           │ - Get/Stream response    │    │
│  └──────────────────────────┴──────────────────────────┘    │
├─────────────────────────────────────────────────────────────┤
│  Infrastructure & Utilities                                 │
│  ┌─────────────────┬─────────────────┬─────────────────┐    │
│  │ Configuration   │ Logging         │ Services/Utils  │    │
│  │ - Pydantic cfg  │ - Structured    │ - KeepAlive     │    │
│  │ - Env variables │ - JSON format   │ - Retry Logic   │    │
│  └─────────────────┴─────────────────┴─────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### 核心设计原则

1. **单一职责** - 每个模块只负责一个明确的功能。
2. **依赖注入** - 通过构造函数注入依赖，便于测试。
3. **异步优先** - 全异步架构，提高并发性能。
4. **配置驱动** - 通过配置文件控制所有行为。
5. **错误优雅** - 统一的错误处理和重试机制。

## 📁 项目结构

```
aistudio-proxy/
├── src/
│   ├── aistudioproxy/
│   │   ├── api/                      # API层
│   │   │   ├── __init__.py
│   │   │   ├── app.py                # FastAPI应用
│   │   │   ├── routes.py             # 路由定义
│   │   │   ├── middleware.py         # 中间件
│   │   │   ├── models.py             # API数据模型
│   │   │   └── security.py           # API密钥认证
│   │   ├── browser/                  # 浏览器层
│   │   │   ├── __init__.py
│   │   │   ├── manager.py            # 浏览器管理器
│   │   │   └── page_controller.py    # 页面交互与控制
│   │   ├── core/                     # 核心引擎
│   │   │   ├── __init__.py
│   │   │   └── handler.py            # 请求处理器
│   │   ├── services/                 # 后台服务
│   │   │   ├── __init__.py
│   │   │   └── keep_alive.py         # 浏览器会话保持
│   │   ├── utils/                    # 工具模块
│   │   │   ├── __init__.py
│   │   │   ├── config.py             # 配置管理
│   │   │   ├── logger.py             # 日志工具
│   │   │   ├── response_formatter.py # 响应格式化工具
│   │   │   └── retry.py              # 重试工具
│   │   └── main.py                   # 主入口
├── tests/                            # 测试用例
├── configs/                          # 配置文件
├── docker/                           # Docker相关
├── docs/                             # 文档
├── scripts/                          # 脚本工具
├── pyproject.toml                    # 项目配置
├── .env.example                      # 环境变量模板
└── README.md
```

## 🔧 技术栈选型

### 核心依赖
```toml
[project]
name = "aistudio-proxy"
version = "0.1.0"
description = "Lightweight Google AI Studio proxy with OpenAI API compatibility"

dependencies = [
    # Web框架
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    
    # 数据验证
    "pydantic>=2.8.0",
    "pydantic-settings>=2.4.0",
    
    # 浏览器自动化
    "playwright>=1.45.0",
    "camoufox>=0.4.0",
    
    # 工具库
    "pyyaml>=6.0.0",
    "structlog>=24.0.0",
    "tenacity>=8.5.0", # 用于重试
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "black>=24.0.0",
    "mypy>=1.8.0",
]
```

### 性能目标
- **启动时间**: < 3秒
- **内存占用**: < 100MB
- **响应延迟**: < 100ms (不含AI处理时间)
- **并发支持**: > 50 并发请求
- **可用性**: > 99%

## 💻 核心模块实现

### 1. 浏览器管理器 (src/aistudioproxy/browser/manager.py)
负责启动、管理和关闭 Playwright 浏览器实例。它维护一个页面池，以支持并发请求，并提供健康检查来监控浏览器状态。

### 2. 页面控制器 (src/aistudioproxy/browser/page_controller.py)
封装了所有与 AI Studio 页面的具体交互逻辑。
- **模型切换**: `switch_model`
- **消息发送**: `send_message`
- **响应获取**: `wait_for_response` (非流式) 和 `start_streaming_response` (流式)
- **状态检查**: `is_logged_in`, `is_error_response`
- **健壮性**: 内置了基于 `tenacity` 的异步重试逻辑。

### 3. 请求处理器 (src/aistudioproxy/core/handler.py)
作为应用的核心，协调 API 请求和浏览器操作。
- **并发控制**: 使用 `asyncio.Semaphore` 限制并发请求。
- **请求路由**: 根据请求是否为流式 (`request.stream`)，调用不同的处理方法。
- **页面管理**: 从 `BrowserManager` 获取和释放页面。
- **响应格式化**: 调用 `response_formatter` 来构建最终的 OpenAI 兼容响应。

### 4. API 安全 (src/aistudioproxy/api/security.py)
提供 API 密钥认证。它通过 `APIKeyHeader` 从 `Authorization` 头中提取 `Bearer` 令牌，并与配置文件中的有效密钥进行比较。

### 5. 主应用 (src/aistudioproxy/main.py)
项目的入口点。负责：
- 解析命令行参数。
- 加载和覆盖配置。
- 初始化日志系统。
- 设置信号处理程序以实现优雅停机。
- 启动 `uvicorn` 服务器。

## 🚀 开发路线图

### 第1-6周: 核心功能开发 (已完成)
- [x] 项目基础搭建
- [x] 浏览器自动化核心
- [x] 认证和模型管理
- [x] 消息处理和响应解析
- [x] API接口实现
- [x] 性能优化和稳定性

### 第7周: 测试和文档
**目标**: 完善测试覆盖和文档
- [ ] **集成测试编写**
- [x] **API文档生成**
- [x] **部署文档编写**
- [ ] **用户使用指南**
- [x] **文档更新** - 根据最终代码实现更新开发文档和TODO列表

### 第8周: 发布准备
**目标**: 准备正式发布
- [ ] **代码审查和重构**
- [ ] **性能基准测试**
- [ ] **安全检查**
- [ ] **发布流程测试**
- [ ] **社区准备**

## 📊 成功指标

### 技术指标
- **代码行数**: < 2,000行
- **启动时间**: < 3秒
- **内存占用**: < 100MB
- **测试覆盖率**: > 80%
- **API响应时间**: < 100ms

### 功能指标
- **模型支持**: 支持所有Gemini模型
- **API兼容性**: 100% OpenAI API兼容
- **稳定性**: 连续运行24小时无崩溃
- **并发性能**: 支持50并发请求

### 质量指标
- **代码质量**: 通过mypy类型检查
- **文档完整性**: 100% API文档覆盖
- **部署便利性**: 支持Docker一键部署
- **用户体验**: 5分钟内完成部署
