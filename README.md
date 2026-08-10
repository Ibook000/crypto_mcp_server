# Crypto MCP Server 🚀

加密货币市场数据 MCP（Model Context Protocol）服务器，提供实时行情、K 线数据、资金费率与行业新闻查询工具，并配套自研 **MCP Client 库** 与 **LLM 编排层**，可直接被任意 Agent 作为工具调用。

> 适用场景：量化交易分析、市场监控、加密货币研究、Agent 工具调用生态建设。

---

## ✨ 核心能力

- **实时行情**：单币种 / 批量加密货币价格查询（数据源：Binance）
- **K 线数据**：多时间周期（1m - 1M）历史 K 线，含开/高/低/收/成交量
- **资金费率**：永续合约资金费率历史，支持自定义条数
- **市场深度**：订单簿买卖盘数据（Asks / Bids）
- **深度搜索**：Tavily advanced search + LLM 结构化总结（`deepsearch_mcp_server.py`）
- **行业新闻**：整合 Odaily / NewsAPI 多源新闻
- **天气扩展**：模块化扩展示例（`weather_mcp_server.py`）
- **可视化管理**：FastAPI WebUI 管理后台（`webui_fastapi.py`）
- **多 Server 编排**：Client 支持同时注册多个 MCP Server 并统一调用
- **重试退避**：Client 内置指数退避重试，应对 API 速率限制

---

## 🏗 系统架构

```
Agent / 用户
      │  stdio (MCP 协议)
      ▼
┌─────────────────────┐        ┌──────────────────┐
│  MCP Client 库      │◄──────►│  FastAPI WebUI   │
│  (mcp_client.py)    │        │  (可视化管理)     │
└────────┬────────────┘        └──────────────────┘
         │  stdio
         ▼
┌─────────────────────┐
│   MCP Server 层     │
│  FastMCP / @mcp.tool│
├─────────────────────┤
│ crypto_mcp_server   │  行情 / K 线 / 资金费率 / 深度
│ deepsearch_server   │  深度搜索 + LLM 总结
│ weather_server      │  模块化扩展示例
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│   LLM 编排层        │  Moonshot / OpenRouter
│   (重试退避)         │  exponential backoff
└─────────────────────┘
```

---

## 📂 项目结构

| 文件 | 说明 |
|------|------|
| `crypto_mcp_server.py` | 加密货币 MCP Server 核心：异步数据获取 + 工具注册 |
| `deepsearch_mcp_server.py` | 深度搜索 MCP Server（Tavily + LLM 总结） |
| `mcp_client.py` | **自研 MCP Client 库**：连接管理、多 Server 注册、重试退避、LLM 编排 |
| `weather_mcp_server.py` | 模块化扩展示例（OpenWeather） |
| `webui_fastapi.py` | FastAPI 可视化管理后台 |
| `config.json` | LLM / 重试参数配置（密钥请通过 `.env`） |
| `mcp.json` | MCP Server 启动配置 |
| `.env.example` | 环境变量模板（复制为 `.env` 后填写） |
| `requirements.txt` | Python 依赖 |
| `static/` `templates/` | WebUI 静态资源与模板 |

---

## 🚀 快速开始

### 1. 克隆与安装

```bash
git clone https://github.com/Ibook000/crypto_mcp_server.git
cd crypto_mcp_server
pip install -r requirements.txt
```

### 2. 配置密钥（安全方式）

```bash
cp .env.example .env
# 编辑 .env，填入你的真实密钥
```

需要的密钥：

| 环境变量 | 用途 | 获取 |
|----------|------|------|
| `NEWS_API_KEY` | NewsAPI 行业新闻搜索 | https://newsapi.org |
| `TAVILY_API_KEY` | deepsearch 深度搜索 | https://tavily.com |
| `OPENROUTER_API_KEY` | deepsearch LLM 总结 | https://openrouter.ai |
| `OPENAI_API_KEY` | mcp_client LLM 编排（Moonshot 兼容） | https://platform.moonshot.cn |
| `OPENWEATHER_API_KEY` | 天气模块 | https://openweathermap.org |

> ⚠️ `.env` 已加入 `.gitignore`，切勿提交。代码通过 `os.environ.get()` 读取密钥，无明文硬编码。

### 3. 启动 MCP Server

```bash
python crypto_mcp_server.py          # 加密货币行情
python deepsearch_mcp_server.py      # 深度搜索
python weather_mcp_server.py         # 天气
```

每个 Server 以 `stdio` 方式运行，可被任意 MCP 兼容的 Agent（Claude Code、Codex 等）调用。

### 4. 通过 Client 调用（Python）

```python
from mcp_client import MCPClient
import asyncio

client = MCPClient()

async def main():
    for server_name in client.mcp_servers.keys():
        await client.connect_to_server(server_name)
    result = await client.process_query("BTC 现在的价格是多少？")
    print(result)

asyncio.run(main())
```

### 5. 启动 WebUI 管理后台

```bash
python webui_fastapi.py
# 浏览器访问 http://localhost:8000
```

---

## 🛠 可用 MCP 工具（crypto_mcp_server.py）

| 工具 | 说明 |
|------|------|
| `query_crypto_price` | 查询单个币种当前价格（如 `BTCUSDT`） |
| `query_batch_crypto_prices` | 批量查询多个币种价格 |
| `query_crypto_klines` | 查询 K 线数据（周期 `1m`-`1M`，数量最多 1000） |
| `query_funding_rate` | 查询永续合约资金费率 |
| `query_order_book` | 查询市场深度（订单簿） |
| `query_crypto_news` | 查询加密货币行业新闻（Odaily） |
| `query_crypto_news_search` | 通过 NewsAPI 搜索新闻 |

---

## 🔧 技术要点

- **异步数据获取**：`httpx` + `asyncio`，支持批量并行查询
- **模块化扩展**：新增数据源只需实现 `fetch_xxx` + `format_xxx` + `@mcp.tool()`
- **重试退避**：Client 内置指数退避重试（`max_retries` / `retry_delay` / `max_delay`）
- **多传输模式**：`stdio` 标准 I/O，兼容主流 Agent 平台
- **错误容错**：所有数据获取函数均返回结构化错误信息，格式化函数有边界校验

---

## 📸 效果展示

WebUI 管理后台截图见 `webui.png` / `webui1.png`。

---

## License

MIT