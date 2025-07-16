# Crypto MCP Server 🚀

加密货币市场数据MCP服务器，提供实时价格、K线数据、资金费率和行业新闻查询功能。

## ✨ 功能特点
- 支持单个/批量加密货币价格查询
- 提供K线数据获取（多种时间周期）
- 永续合约资金费率历史查询
- 加密货币行业新闻聚合（今日/昨日）
- 缓存机制优化性能，减少API请求
- 模块化设计，易于扩展新功能

## 📂 文件结构与说明

| 文件名 | 描述 |
|--------|------|
| `crypto_mcp_server.py` | 核心服务器实现，注册加密货币数据查询工具，处理API请求和响应格式化 |
| `mcp_client.py` | MCP客户端库，提供连接服务器、调用工具和处理响应的便捷接口 |
| `weather_mcp_server.py` | 天气查询MCP服务器示例，展示如何扩展实现新的MCP服务 |
| `config.json` | 应用配置文件，存储API密钥和服务参数 |
| `mcp.json` | MCP服务器配置，定义服务启动参数和端口设置 |

## 🚀 快速开始

1. 启动MCP服务器
```bash
python crypto_mcp_server.py
```

2. 通过MCP客户端调用工具（示例）
```python
from mcp.client import MCPClient

client = MCPClient()
price = client.call("query_crypto_price", symbol="BTCUSDT")
print(price)
```

## 🛠️ 可用工具列表

| 工具名称 | 参数 | 描述 |
|---------|------|------|
| `query_crypto_price` | `symbol`: 交易对（如BTCUSDT） | 获取单个加密货币当前价格 |
| `query_batch_crypto_prices` | `symbols`: 交易对列表 | 批量获取多个加密货币价格 |
| `query_crypto_klines` | `symbol`, `interval`, `limit` | 获取K线数据 |
| `query_funding_rate` | `symbol`, `limit` | 获取资金费率历史数据 |
| `query_crypto_news` | `length`: 0(今日)/1(昨日) | 获取加密货币行业新闻 |

## 📝 示例输出

### 价格查询
```
交易对: BTCUSDT
价格: 30000.00 USDT
```

### K线数据
```
🕰️ K线数据列表（时间从旧到新）：
--------------------------------------------------------------------
时间                 开盘       最高       最低       收盘       交易量
--------------------------------------------------------------------
2023-07-01 00:00:00  29800.00   30200.00   29700.00   30000.00   1250.50
```

## 🔧 开发指南

### 添加新工具
1. 在`BinanceAPI`或`NewsAPI`类中实现新的数据源方法
2. 创建对应的格式化函数
3. 使用`@mcp.tool()`装饰器注册新工具

## 📄 许可证
[MIT](LICENSE)