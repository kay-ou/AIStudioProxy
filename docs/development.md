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
│  │ POST /v1/chat/completions                               │ │
│  │ GET  /v1/models                                         │ │
│  │ GET  /health                                            │ │
│  └─────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  Core Engine                                                │
│  ┌─────────────────┬─────────────────┬─────────────────┐    │
│  │ Request Handler │ Response Parser │ Error Handler   │    │
│  │ - Validate req  │ - Extract text  │ - Retry logic   │    │
│  │ - Format params │ - Stream parse  │ - Fallback      │    │
│  │ - Queue manage  │ - Format resp   │ - Logging       │    │
│  └─────────────────┴─────────────────┴─────────────────┘    │
├─────────────────────────────────────────────────────────────┤
│  Browser Layer                                              │
│  ┌─────────────────┬─────────────────┬─────────────────┐    │
│  │ Browser Manager │ Page Controller │ Auth Manager    │    │
│  │ - Launch browser│ - Send message  │ - Load profile  │    │
│  │ - Manage pages  │ - Switch model  │ - Handle auth   │    │
│  │ - Health check  │ - Get response  │ - Session keep  │    │
│  └─────────────────┴─────────────────┴─────────────────┘    │
├─────────────────────────────────────────────────────────────┤
│  Infrastructure                                             │
│  ┌─────────────────┬─────────────────┬─────────────────┐    │
│  │ Configuration   │ Logging         │ Monitoring      │    │
│  │ - Pydantic cfg  │ - Structured    │ - Health check  │    │
│  │ - Env variables │ - JSON format   │ - Metrics       │    │
│  │ - Validation    │ - Log rotation  │ - Alerts        │    │
│  └─────────────────┴─────────────────┴─────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### 核心设计原则

1. **单一职责** - 每个模块只负责一个明确的功能
2. **依赖注入** - 通过构造函数注入依赖，便于测试
3. **异步优先** - 全异步架构，提高并发性能
4. **配置驱动** - 通过配置文件控制所有行为
5. **错误优雅** - 统一的错误处理和恢复机制

## 📁 项目结构

```
aistudio-proxy/
├── src/
│   ├── api/                        # API层
│   │   ├── __init__.py
│   │   ├── app.py                  # FastAPI应用
│   │   ├── routes.py               # 路由定义
│   │   ├── middleware.py           # 中间件
│   │   └── models.py               # API数据模型
│   ├── core/                       # 核心引擎
│   │   ├── __init__.py
│   │   ├── handler.py              # 请求处理器
│   │   ├── parser.py               # 响应解析器
│   │   └── errors.py               # 错误处理
│   ├── browser/                    # 浏览器层
│   │   ├── __init__.py
│   │   ├── manager.py              # 浏览器管理器
│   │   ├── controller.py           # 页面控制器
│   │   └── auth.py                 # 认证管理器
│   ├── utils/                      # 工具模块
│   │   ├── __init__.py
│   │   ├── config.py               # 配置管理
│   │   ├── logger.py               # 日志工具
│   │   └── helpers.py              # 辅助函数
│   └── main.py                     # 主入口
├── tests/                          # 测试用例
│   ├── unit/                       # 单元测试
│   ├── integration/                # 集成测试
│   └── conftest.py                 # 测试配置
├── configs/                        # 配置文件
│   ├── config.yaml                 # 主配置
│   └── models.yaml                 # 模型配置
├── docker/                         # Docker相关
│   ├── Dockerfile
│   └── docker-compose.yml
├── docs/                           # 文档
│   ├── api.md                      # API文档
│   ├── deployment.md               # 部署文档
│   └── development.md              # 开发文档
├── scripts/                        # 脚本工具
│   ├── setup.sh                    # 环境设置
│   └── run.sh                      # 启动脚本
├── pyproject.toml                  # 项目配置
├── .env.example                    # 环境变量模板
├── .gitignore
└── README.md
```

## 🔧 技术栈选型

### 核心依赖 (仅8个)
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

### 1. 配置管理 (src/utils/config.py)
```python
from pydantic import BaseSettings
from typing import Optional, List

class BrowserConfig(BaseSettings):
    headless: bool = True
    port: int = 9222
    timeout: int = 30000
    
class ServerConfig(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 2048
    workers: int = 1
    
class AuthConfig(BaseSettings):
    profile_path: Optional[str] = None
    auto_login: bool = True
    
class Config(BaseSettings):
    server: ServerConfig = ServerConfig()
    browser: BrowserConfig = BrowserConfig()
    auth: AuthConfig = AuthConfig()
    
    # 支持的模型列表
    supported_models: List[str] = [
        "gemini-2.5-pro",
        "gemini-2.5-flash",
        "gemini-1.5-pro",
        "gemini-1.5-flash"
    ]
    
    class Config:
        env_file = ".env"
        env_nested_delimiter = "__"

# 全局配置实例
config = Config()
```

### 2. 浏览器管理器 (src/browser/manager.py)
```python
from playwright.async_api import async_playwright, Browser, Page
from typing import Optional
import asyncio

class BrowserManager:
    def __init__(self, config: BrowserConfig):
        self.config = config
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self._playwright = None
        
    async def start(self) -> None:
        """启动浏览器"""
        self._playwright = await async_playwright().start()
        
        # 启动Camoufox浏览器
        self.browser = await self._playwright.chromium.launch(
            headless=self.config.headless,
            args=[f"--remote-debugging-port={self.config.port}"]
        )
        
        # 创建页面
        self.page = await self.browser.new_page()
        
        # 导航到AI Studio
        await self.page.goto("https://aistudio.google.com/app/prompts/new")
        
    async def stop(self) -> None:
        """停止浏览器"""
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()
        if self._playwright:
            await self._playwright.stop()
            
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            if not self.page:
                return False
            await self.page.evaluate("document.title")
            return True
        except Exception:
            return False
```

### 3. 页面控制器 (src/browser/controller.py)
```python
from playwright.async_api import Page
from typing import AsyncIterator
import asyncio

class PageController:
    def __init__(self, page: Page):
        self.page = page
        
    async def send_message(self, message: str, model: str = "gemini-2.5-pro") -> str:
        """发送消息并获取响应"""
        # 1. 切换模型
        await self._switch_model(model)
        
        # 2. 输入消息
        await self._input_message(message)
        
        # 3. 发送请求
        await self._send_request()
        
        # 4. 等待响应
        response = await self._wait_for_response()
        
        return response
        
    async def send_message_stream(self, message: str, model: str = "gemini-2.5-pro") -> AsyncIterator[str]:
        """流式发送消息"""
        # 发送消息
        await self.send_message(message, model)
        
        # 流式读取响应
        async for chunk in self._stream_response():
            yield chunk
            
    async def _switch_model(self, model: str) -> None:
        """切换AI模型"""
        # 实现模型切换逻辑
        pass
        
    async def _input_message(self, message: str) -> None:
        """输入消息到文本框"""
        # 实现消息输入逻辑
        pass
        
    async def _send_request(self) -> None:
        """发送请求"""
        # 实现发送逻辑
        pass
        
    async def _wait_for_response(self) -> str:
        """等待完整响应"""
        # 实现响应等待逻辑
        pass
        
    async def _stream_response(self) -> AsyncIterator[str]:
        """流式读取响应"""
        # 实现流式响应逻辑
        pass
```

### 4. API路由 (src/api/routes.py)
```python
from fastapi import APIRouter, HTTPException
from aistudioproxy.api.models import ChatCompletionRequest, ChatCompletionResponse
from aistudioproxy.core.handler import RequestHandler

router = APIRouter()
handler = RequestHandler()

@router.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest) -> ChatCompletionResponse:
    """OpenAI兼容的聊天完成端点"""
    try:
        if request.stream:
            return await handler.handle_stream_request(request)
        else:
            return await handler.handle_request(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/v1/models")
async def list_models():
    """列出可用模型"""
    return {
        "object": "list",
        "data": [
            {
                "id": model,
                "object": "model",
                "created": 1677610602,
                "owned_by": "google"
            }
            for model in config.supported_models
        ]
    }

@router.get("/health")
async def health_check():
    """健康检查端点"""
    healthy = await handler.health_check()
    if healthy:
        return {"status": "healthy"}
    else:
        raise HTTPException(status_code=503, detail="Service unhealthy")
```

### 5. 主应用 (src/main.py)
```python
import asyncio
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from aistudioproxy.api.routes import router
from aistudioproxy.browser.manager import BrowserManager
from aistudioproxy.utils.config import config
from aistudioproxy.utils.logger import setup_logger

# 全局浏览器管理器
browser_manager = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global browser_manager
    
    # 启动时初始化
    setup_logger()
    browser_manager = BrowserManager(config.browser)
    await browser_manager.start()
    
    yield
    
    # 关闭时清理
    if browser_manager:
        await browser_manager.stop()

# 创建FastAPI应用
app = FastAPI(
    title="AIStudio Proxy",
    description="Lightweight Google AI Studio proxy with OpenAI API compatibility",
    version="0.1.0",
    lifespan=lifespan
)

# 注册路由
app.include_router(router)

def main():
    """主函数"""
    uvicorn.run(
        "aistudioproxy.main:app",
        host=config.server.host,
        port=config.server.port,
        workers=config.server.workers,
        reload=False
    )

if __name__ == "__main__":
    main()
```

## 🚀 开发路线图

### 第1周: 项目基础搭建
**目标**: 建立项目结构和基础框架

**任务清单**:
- [ ] 项目初始化 (pyproject.toml, 目录结构)
- [ ] 配置系统实现 (Pydantic Settings)
- [ ] 日志系统搭建 (structlog)
- [ ] FastAPI应用框架
- [ ] 基础测试框架
- [ ] Docker配置

**验收标准**:
```bash
# 项目可以启动
python -m aistudioproxy.main

# 健康检查通过
curl http://localhost:2048/health
```

### 第2周: 浏览器自动化核心
**目标**: 实现浏览器管理和页面控制

**任务清单**:
- [ ] 浏览器管理器实现
- [ ] Camoufox启动和配置
- [ ] 页面导航和初始化
- [ ] 基础页面操作封装
- [ ] 错误处理和重试机制

**验收标准**:
```python
# 浏览器可以成功启动并导航到AI Studio
browser = BrowserManager(config.browser)
await browser.start()
assert await browser.health_check() == True
```

### 第3周: 认证和模型管理
**目标**: 实现用户认证和模型切换

**任务清单**:
- [ ] 认证文件加载和管理
- [ ] 自动登录流程
- [ ] 模型切换逻辑
- [ ] 会话保持机制
- [ ] 认证状态监控

**验收标准**:
```python
# 认证和模型切换正常工作
auth_manager = AuthManager(config.auth)
await auth_manager.login()
controller = PageController(browser.page)
await controller.switch_model("gemini-2.5-pro")
```

### 第4周: 消息处理和响应解析
**目标**: 实现完整的消息发送和响应处理

**任务清单**:
- [ ] 消息输入和发送逻辑
- [ ] 响应等待和解析
- [ ] 流式响应处理
- [ ] 错误响应处理
- [ ] 响应格式标准化

**验收标准**:
```python
# 消息发送和响应解析正常
response = await controller.send_message("Hello")
assert response is not None
assert len(response) > 0
```

### 第5周: API接口实现
**目标**: 实现OpenAI兼容的API接口

**任务清单**:
- [ ] API数据模型定义
- [ ] 请求处理器实现
- [ ] 响应格式转换
- [ ] 流式响应支持
- [ ] 错误处理和状态码

**验收标准**:
```bash
# OpenAI API兼容测试
curl -X POST http://localhost:2048/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-2.5-pro",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

### 第6周: 性能优化和稳定性
**目标**: 优化性能和提高稳定性

**任务清单**:
- [ ] 并发处理优化
- [ ] 内存使用优化
- [ ] 错误恢复机制
- [ ] 健康检查完善
- [ ] 监控指标添加

**验收标准**:
- 启动时间 < 3秒
- 内存占用 < 100MB
- 并发50请求无错误

### 第7周: 测试和文档
**目标**: 完善测试覆盖和文档

**任务清单**:
- [ ] 单元测试编写
- [ ] 集成测试编写
- [ ] API文档生成
- [ ] 部署文档编写
- [ ] 用户使用指南

**验收标准**:
- 测试覆盖率 > 80%
- 所有API有文档
- 部署文档完整

### 第8周: 发布准备
**目标**: 准备正式发布

**任务清单**:
- [ ] 代码审查和重构
- [ ] 性能基准测试
- [ ] 安全检查
- [ ] 发布流程测试
- [ ] 社区准备

**验收标准**:
- 所有测试通过
- 性能指标达标
- 文档完整
- 可以一键部署

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

## 🛠️ 实施最佳实践

### 代码质量保证

#### 1. 类型检查配置 (pyproject.toml)
```toml
[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
warn_unreachable = true
strict_equality = true
```

#### 2. 代码格式化配置
```toml
[tool.black]
line-length = 88
target-version = ['py311']
include = '\.pyi?$'

[tool.isort]
profile = "black"
multi_line_output = 3
line_length = 88
```

#### 3. 测试配置
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "--strict-markers",
    "--strict-config",
    "--cov=src",
    "--cov-report=term-missing",
    "--cov-report=html",
    "--cov-fail-under=80"
]
```

### 错误处理策略

#### 1. 自定义异常类 (src/core/errors.py)
```python
class AIStudioProxyError(Exception):
    """基础异常类"""
    pass

class BrowserError(AIStudioProxyError):
    """浏览器相关错误"""
    pass

class AuthenticationError(AIStudioProxyError):
    """认证相关错误"""
    pass

class ModelNotFoundError(AIStudioProxyError):
    """模型不存在错误"""
    pass

class RateLimitError(AIStudioProxyError):
    """速率限制错误"""
    pass
```

#### 2. 重试机制
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def send_message_with_retry(self, message: str) -> str:
    """带重试的消息发送"""
    try:
        return await self._send_message(message)
    except BrowserError as e:
        logger.warning(f"Browser error, retrying: {e}")
        raise
```

### 性能优化技巧

#### 1. 连接池管理
```python
class BrowserPool:
    """浏览器连接池"""
    def __init__(self, max_size: int = 5):
        self.max_size = max_size
        self.pool: List[BrowserManager] = []
        self.semaphore = asyncio.Semaphore(max_size)

    async def acquire(self) -> BrowserManager:
        await self.semaphore.acquire()
        if self.pool:
            return self.pool.pop()
        return await self._create_browser()

    async def release(self, browser: BrowserManager):
        self.pool.append(browser)
        self.semaphore.release()
```

#### 2. 响应缓存
```python
from functools import lru_cache
import hashlib

class ResponseCache:
    def __init__(self, max_size: int = 100):
        self.cache = {}
        self.max_size = max_size

    def get_cache_key(self, message: str, model: str) -> str:
        content = f"{message}:{model}"
        return hashlib.md5(content.encode()).hexdigest()

    async def get(self, key: str) -> Optional[str]:
        return self.cache.get(key)

    async def set(self, key: str, value: str):
        if len(self.cache) >= self.max_size:
            # 简单的LRU实现
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
        self.cache[key] = value
```

### 监控和日志

#### 1. 结构化日志 (src/utils/logger.py)
```python
import structlog
from typing import Any, Dict

def setup_logger() -> None:
    """设置结构化日志"""
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

logger = structlog.get_logger()
```

#### 2. 指标收集
```python
from prometheus_client import Counter, Histogram, Gauge
import time

# 定义指标
REQUEST_COUNT = Counter('requests_total', 'Total requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('request_duration_seconds', 'Request duration')
ACTIVE_CONNECTIONS = Gauge('active_connections', 'Active connections')

class MetricsMiddleware:
    async def __call__(self, request, call_next):
        start_time = time.time()
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path
        ).inc()

        response = await call_next(request)

        REQUEST_DURATION.observe(time.time() - start_time)
        return response
```

### 部署配置

#### 1. Dockerfile
```dockerfile
FROM python:3.11-slim

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# 安装Playwright依赖
RUN pip install playwright
RUN playwright install chromium
RUN playwright install-deps chromium

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY pyproject.toml .
COPY README.md .

# 安装Python依赖
RUN pip install .

# 复制源代码
COPY src/ src/
COPY configs/ configs/

# 暴露端口
EXPOSE 2048

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:2048/health || exit 1

# 启动命令
CMD ["python", "-m", "aistudioproxy.main"]
```

#### 2. docker-compose.yml
```yaml
version: '3.8'

services:
  aistudio-proxy:
    build: .
    ports:
      - "2048:2048"
    environment:
      - SERVER__HOST=0.0.0.0
      - SERVER__PORT=2048
      - BROWSER__HEADLESS=true
    volumes:
      - ./auth:/app/auth:ro
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:2048/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

### 安全考虑

#### 1. 输入验证
```python
from pydantic import validator, Field

class ChatCompletionRequest(BaseModel):
    model: str = Field(..., regex=r'^gemini-[a-z0-9.-]+$')
    messages: List[Message] = Field(..., min_items=1, max_items=100)
    max_tokens: Optional[int] = Field(None, ge=1, le=4096)
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)

    @validator('messages')
    def validate_messages(cls, v):
        total_length = sum(len(msg.content) for msg in v)
        if total_length > 100000:  # 100KB限制
            raise ValueError("Messages too long")
        return v
```

#### 2. 速率限制
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@router.post("/v1/chat/completions")
@limiter.limit("10/minute")
async def chat_completions(request: Request, chat_request: ChatCompletionRequest):
    # 处理逻辑
    pass
```

## 🚀 快速开始指南

### 1. 环境准备
```bash
# 克隆项目
git clone https://github.com/your-username/aistudio-proxy.git
cd aistudio-proxy

# 安装依赖
pip install -e .

# 安装Playwright浏览器
playwright install chromium
```

### 2. 配置设置
```bash
# 复制环境变量模板
cp .env.example .env

# 编辑配置
vim .env
```

### 3. 启动服务
```bash
# 开发模式
python -m aistudioproxy.main

# 生产模式
uvicorn aistudioproxy.main:app --host 0.0.0.0 --port 2048

# Docker方式
docker-compose up -d
```

### 4. 测试API
```bash
# 健康检查
curl http://localhost:2048/health

# 聊天测试
curl -X POST http://localhost:2048/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-2.5-pro",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

## 📚 开发指南

### 贡献流程
1. Fork项目
2. 创建功能分支
3. 编写代码和测试
4. 提交Pull Request

### 代码规范
- 使用Black格式化代码
- 通过mypy类型检查
- 测试覆盖率 > 80%
- 遵循PEP 8规范

### 调试技巧
```python
# 启用调试模式
export DEBUG=true

# 查看详细日志
export LOG_LEVEL=DEBUG

# 浏览器可视化调试
export BROWSER__HEADLESS=false
```

这个重写项目将成为一个**真正轻量级、高性能**的AI Studio代理服务，为用户提供简洁而强大的AI服务接入能力。通过遵循这个详细的架构和实现路线，你将能够构建出一个高质量、易维护的现代化AI代理服务。
