# Crypto MCP Server 🚀

> **2025 年 7 月 · MCP 协议发布之初的首批实践之一**  
> 在 Model Context Protocol 刚公开时就投入开发的早期 MCP Server，国内较早的 MCP 探索项目之一。

一套完整的加密货币市场数据 MCP 服务端 + 客户端工具链。提供实时行情、K 线、资金费率、市场深度、行业新闻和深度搜索能力，可直接被任何 MCP 兼容的 Agent 作为工具调用。

---

## 背景

2025 年 7 月，Anthropic 开源了 MCP（Model Context Protocol）协议。当时市面上几乎没有现成的 MCP Server 实现，文档和工具链都不完善。这个项目就是在那个阶段开始的——从零搭建 MCP Server 框架、实现 stdio 传输、注册工具、编写客户端库，算是国内最早一批把 MCP 跑起来的尝试。

项目结构保留了早期的探索痕迹：有专门的 MCP Client 库（`mcp_client.py`），有 LLM 编排层，也有后来追加的 WebUI 管理后台。不是最优雅的代码，但每一行都是当时真实踩坑的记录。

---

## 功能一览

| 功能 | 说明 |
|------|------|
| **实时行情** | 单币种 / 批量查询最新价格（数据源：Binance） |
| **K 线数据** | 多时间周期历史 K 线，含开/高/低/收/成交量 |
| **资金费率** | 永续合约资金费率历史 |
| **市场深度** | 订单簿买卖盘数据（Asks / Bids） |
| **行业新闻** | 整合 Odaily 快讯 + NewsAPI 多源搜索 |
| **深度搜索** | Tavily 搜索 + LLM 结构化总结 |
| **天气查询** | 模块化扩展示例 |
| **WebUI 后台** | FastAPI 可视化管理界面 |
| **多 Server 编排** | 同时注册多个 MCP Server，统一通过 LLM 调度 |
| **重试退避** | 内置指数退避 + 随机抖动，应对 API 限流 |

---

## 系统架构

```
Agent / 用户
      │  stdio (MCP 协议)
      ▼
┌───────────────────────┐        ┌──────────────────┐
│  MCP Client 库        │◄──────►│  FastAPI WebUI   │
│  (mcp_client.py)      │        │  (可视化管理)     │
└──────────┬────────────┘        └──────────────────┘
           │  stdio
           ▼
┌───────────────────────┐
│   MCP Server 层       │
│  FastMCP / @mcp.tool  │
├───────────────────────┤
│ crypto_mcp_server     │  行情 / K 线 / 资金费率 / 深度
│ deepsearch_server     │  深度搜索 + LLM 总结
│ weather_server        │  模块化扩展示例
└───────────────────────┘
           │
           ▼
┌───────────────────────┐
│   LLM 编排层          │  Moonshot / OpenRouter
│   (重试退避)           │  exponential backoff
└───────────────────────┘
```

---

## 项目结构

```
crypto_mcp_server.py        # 行情 MCP Server（核心）
deepsearch_mcp_server.py    # 深度搜索 MCP Server
weather_mcp_server.py       # 天气 MCP Server（示例）
mcp_client.py               # MCP Client 库（LLM 编排 + 重试退避）
webui_fastapi.py            # FastAPI WebUI 后台
static/                     # WebUI 前端资源
templates/                  # WebUI 页面模板
config.json                 # LLM 参数配置
mcp.json                    # MCP Server 启动配置
.env.example                # 环境变量模板
requirements.txt            # Python 依赖
```

---

## 快速开始

### 1. 安装

```bash
git clone https://github.com/Ibook000/crypto_mcp_server.git
cd crypto_mcp_server
pip install -r requirements.txt
```

### 2. 配置密钥

```bash
cp .env.example .env
```

编辑 `.env` 填入你的密钥：

| 变量 | 用途 | 获取地址 |
|------|------|----------|
| `NEWS_API_KEY` | Odaily / NewsAPI 行业新闻搜索 | https://newsapi.org |
| `TAVILY_API_KEY` | deepsearch 深度搜索 | https://tavily.com |
| `OPENROUTER_API_KEY` | deepsearch LLM 总结 | https://openrouter.ai |
| `OPENAI_API_KEY` | Client LLM 编排（Moonshot 兼容） | https://platform.moonshot.cn |
| `OPENWEATHER_API_KEY` | 天气模块 | https://openweathermap.org |

> ⚠️ `.env` 已加入 `.gitignore`，不会提交到仓库。代码统一通过 `os.environ.get()` 读取。

### 3. 启动 MCP Server

```bash
python crypto_mcp_server.py          # 加密货币行情
python deepsearch_mcp_server.py      # 深度搜索
python weather_mcp_server.py         # 天气
```

每个 Server 以 `stdio` 方式运行，可被任意 MCP 兼容的 Agent（Claude Code、Cursor、Codex 等）调用。

### 4. 通过 Client 调用

```python
from mcp_client import MCPClient
import asyncio

client = MCPClient()

async def main():
    for name in client.mcp_servers:
        await client.connect_to_server(name)
    result = await client.process_query("BTC 现在的价格是多少？")
    print(result)

asyncio.run(main())
```

### 5. 启动 WebUI

```bash
python webui_fastapi.py
# 打开 http://localhost:8000
```

---

## MCP 工具一览

### crypto_mcp_server.py

| 工具 | 说明 |
|------|------|
| `query_crypto_price` | 查询单个币种价格 |
| `query_batch_crypto_prices` | 批量查询多个币种价格 |
| `query_crypto_klines` | 查询 K 线数据（1m–1M，最多 1000 条） |
| `query_funding_rate` | 查询永续合约资金费率 |
| `query_order_book` | 查询市场深度（订单簿） |
| `query_crypto_news` | 查询行业快讯（Odaily） |
| `query_crypto_news_search` | 搜索新闻（NewsAPI） |

### deepsearch_mcp_server.py

| 工具 | 说明 |
|------|------|
| `deep_search` | 执行深度搜索，返回结构化结果 |
| `deep_search_and_summarize` | 深度搜索 + LLM 总结为 MD 报告 |

---

## WebUI 截图

WebUI 管理后台基于 FastAPI 构建，支持多 Server 连接监控和对话式查询。

![WebUI 主界面](webui.png)

![WebUI 对话界面](webui1.png)

---

## 技术要点

- **MCP 协议**：基于 `stdio` 传输，使用 `FastMCP` + `@mcp.tool()` 注册工具
- **异步 I/O**：`httpx` + `asyncio`，单币种和批量请求都支持
- **重试退避**：Client 内置指数退避 + 随机抖动，应对 API 限流
- **容错设计**：所有数据获取函数返回结构化错误，格式化函数有边界校验
- **模块化扩展**：新增数据源只需实现 `fetch_xxx` + `format_xxx` + `@mcp.tool()` 三步

---

## License

MIT