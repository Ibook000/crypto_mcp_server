import json
import httpx
import datetime
import re
from typing import Any
from mcp.server.fastmcp import FastMCP

# 初始化 MCP 服务器
mcp = FastMCP("CryptoServer")

# 币安 API 配置
BINANCE_PRICE_API = "https://api.binance.com/api/v3/ticker/price"
BINANCE_BATCH_PRICE_API = "https://api.binance.com/api/v3/ticker/price"
BINANCE_KLINES_API = "https://api.binance.com/api/v3/klines"
BINANCE_FUNDING_RATE_API = "https://fapi.binance.com/fapi/v1/fundingRate"
# 加密货币新闻 API 配置
ODAILY_NEWS_API = "https://www.odaily.news/v1/openapi/feeds"
USER_AGENT = "crypto-app/1.0"

async def fetch_crypto_price(symbol: str) -> dict[str, Any] | None:
    """
    从币安 API 获取加密货币价格信息。
    :param symbol: 交易对符号（如 BTCUSDT）
    :return: 价格数据字典；若出错返回包含 error 信息的字典
    """
    params = {
        "symbol": symbol
    }
    headers = {"User-Agent": USER_AGENT}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(BINANCE_PRICE_API, params=params, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()  # 返回字典类型
        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP 错误: {e.response.status_code}"}
        except Exception as e:
            return {"error": f"请求失败: {str(e)}"}

async def fetch_crypto_klines(symbol: str, interval: str, limit: int) -> list | dict[str, Any]:
    """
    从币安 API 获取加密货币K线数据。
    :param symbol: 交易对符号（如 BTCUSDT）
    :param interval: 时间周期（如 1m, 5m, 1h, 1d 等常用周期）
    :param limit: 获取K线数量（最大1000）
    :return: K线数据列表；若出错返回包含 error 信息的字典
    """
    # 验证时间周期是否有效
    valid_intervals = {'1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d', '3d', '1w', '1M'}
    if interval not in valid_intervals:
        return {"error": f"无效的时间周期，请使用: {', '.join(valid_intervals)}"}

    # 限制K线数量在1-1000之间
    limit = max(1, min(limit, 1000))

    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    }
    headers = {"User-Agent": USER_AGENT}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(BINANCE_KLINES_API, params=params, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()  # 返回K线数据列表
        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP 错误: {e.response.status_code}"}
        except Exception as e:
            return {"error": f"请求失败: {str(e)}"}

async def fetch_funding_rate(symbol: str, limit: int = 10) -> list | dict[str, Any]:
    """
    从币安 API 获取加密货币资金费率数据。
    :param symbol: 交易对符号（如 BTCUSDT）
    :param limit: 获取记录数量（最大1000）
    :return: 资金费率数据列表；若出错返回包含 error 信息的字典
    """
    # 限制记录数量在1-1000之间
    limit = max(1, min(limit, 1000))

    params = {
        "symbol": symbol,
        "limit": limit
    }
    headers = {"User-Agent": USER_AGENT}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(BINANCE_FUNDING_RATE_API, params=params, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()  # 返回资金费率数据列表
        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP 错误: {e.response.status_code}"}
        except Exception as e:
            return {"error": f"请求失败: {str(e)}"}

async def fetch_crypto_news(length: int = 0) -> dict[str, Any]:
    """
    从Odaily API获取加密货币新闻
    :param length: 0表示今天新闻，1表示昨天新闻
    :return: 新闻数据字典；若出错返回包含error信息的字典
    """
    # 验证参数有效性
    if length not in (0, 1):
        return {"error": "无效的length参数，必须为0或1"}

    params = {
        "length": length
    }
    headers = {
        "User-Agent": USER_AGENT,
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(ODAILY_NEWS_API, params=params, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()  # 返回新闻数据
        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP错误: {e.response.status_code}"}
        except Exception as e:
            return {"error": f"请求失败: {str(e)}"}

async def fetch_batch_crypto_prices(symbols: list) -> list | dict[str, Any]:
    """
    批量从币安 API 获取多个加密货币价格信息。
    :param symbols: 交易对符号列表（如 ["BTCUSDT", "ETHUSDT"]）
    :return: 价格数据列表；若出错返回包含 error 信息的字典
    """
    # 验证交易对格式和数量
    if not isinstance(symbols, list) or len(symbols) == 0:
        return {"error": "请提供有效的交易对列表"}
    
    for symbol in symbols:
        if not re.match(r'^[A-Z0-9]{3,10}$', str(symbol)):
            return {"error": f"无效的交易对格式: {symbol}"}

    params = {
        "symbols": json.dumps(symbols)
    }
    headers = {"User-Agent": USER_AGENT}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(BINANCE_BATCH_PRICE_API, params=params, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()  # 返回价格数据列表
        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP 错误: {e.response.status_code}"}
        except Exception as e:
            return {"error": f"请求失败: {str(e)}"}



def format_crypto_data(data: dict[str, Any] | str) -> str:
    """
    将加密货币价格数据格式化为易读文本。
    :param data: 价格数据（可以是字典或 JSON 字符串）
    :return: 格式化后的价格信息字符串
    """
    # 如果传入的是字符串，则先转换为字典
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception as e:
            return f"无法解析价格数据: {e}"

    # 如果数据中包含错误信息，直接返回错误提示
    if "error" in data:
        return f"⚠️ {data['error']}"

    # 提取数据时做容错处理
    symbol = data.get("symbol", "未知")
    price = data.get("price", "N/A")

    return (
        f"交易对: {symbol}\n"
        f"价格: {price} USDT\n"
    )


def format_crypto_klines(data: list | dict[str, Any] | str) -> str:
    """
    将加密货币K线数据格式化为易读文本。
    :param data: K线数据（可以是列表、字典或 JSON 字符串）
    :return: 格式化后的K线信息字符串
    """
    # 如果传入的是字符串，则先转换为字典/列表
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception as e:
            return f"无法解析K线数据: {e}"

    # 如果数据中包含错误信息，直接返回错误提示
    if isinstance(data, dict) and "error" in data:
        return f"⚠️ {data['error']}"

    # 验证是否为有效的K线数据列表
    if not isinstance(data, list) or (len(data) > 0 and not isinstance(data[0], list)):
        return "❌ 无效的K线数据格式"

    # 格式化K线数据标题
    result = ["🕰️ K线数据列表（时间从旧到新）：\n"]
    result.append("--------------------------------------------------------------------")
    result.append(f"{'时间':<20} {'开盘':<10} {'最高':<10} {'最低':<10} {'收盘':<10} {'交易量'}")
    result.append("--------------------------------------------------------------------")

    # 格式化每条K线数据
    for kline in data:
        # 币安K线数据结构: [开盘时间, 开盘价, 最高价, 最低价, 收盘价, 交易量, ...]
        try:
            timestamp = int(kline[0])
            open_price = float(kline[1])
            high_price = float(kline[2])
            low_price = float(kline[3])
            close_price = float(kline[4])
            volume = float(kline[5])

            # 格式化时间戳为本地时间
            time_str = datetime.datetime.fromtimestamp(timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S')

            # 添加格式化后的K线数据行
            result.append(
                f"{time_str:<20} {open_price:<10.4f} {high_price:<10.4f} {low_price:<10.4f} {close_price:<10.4f} {volume:.2f}"
            )
        except (IndexError, ValueError) as e:
            result.append(f"⚠️ 数据解析错误: {str(e)}")
            continue

    return '\n'.join(result)


def format_funding_rate(data: list | dict[str, Any] | str) -> str:
    """
    将加密货币资金费率数据格式化为易读文本。
    :param data: 资金费率数据（可以是列表、字典或 JSON 字符串）
    :return: 格式化后的资金费率信息字符串
    """
    # 如果传入的是字符串，则先转换为字典/列表
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception as e:
            return f"无法解析资金费率数据: {e}"

    # 如果数据中包含错误信息，直接返回错误提示
    if isinstance(data, dict) and "error" in data:
        return f"⚠️ {data['error']}"

    # 验证是否为有效的资金费率数据列表
    if not isinstance(data, list) or (len(data) > 0 and not isinstance(data[0], dict)):
        return "❌ 无效的资金费率数据格式"

    # 格式化资金费率数据标题
    result = ["💸 资金费率历史数据（时间从旧到新）：\n"]
    result.append("--------------------------------------------------------------------")
    result.append(f"{'时间':<20} {'交易对':<10} {'资金费率':<12} {'收取时间'}")
    result.append("--------------------------------------------------------------------")

    # 格式化每条资金费率数据
    for funding in data:
        try:
            # 提取资金费率数据
            symbol = funding.get("symbol", "未知")
            funding_rate = float(funding.get("fundingRate", 0)) * 100  # 转换为百分比
            funding_time = int(funding.get("fundingTime", 0))
            next_funding_time = int(funding.get("nextFundingTime", 0))

            # 格式化时间戳为本地时间
            time_str = datetime.datetime.fromtimestamp(funding_time / 1000).strftime('%Y-%m-%d %H:%M:%S')
            next_time_str = datetime.datetime.fromtimestamp(next_funding_time / 1000).strftime('%Y-%m-%d %H:%M:%S')

            # 添加格式化后的资金费率数据行
            result.append(
                f"{time_str:<20} {symbol:<10} {funding_rate:>10.4f}%  {next_time_str}"
            )
        except (KeyError, ValueError) as e:
            result.append(f"⚠️ 数据解析错误: {str(e)}")
            continue

    return '\n'.join(result)


def format_crypto_news(data: dict[str, Any] | str) -> str:
    """
    将加密货币新闻数据格式化为易读文本
    :param data: 新闻数据（字典或JSON字符串）
    :return: 格式化后的新闻信息字符串
    """
    # 解析JSON数据
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception as e:
            return f"无法解析新闻数据: {e}"

    # 处理错误情况
    if isinstance(data, dict) and "error" in data:
        return f"⚠️ {data['error']}"

    # 验证数据结构
    if not isinstance(data, dict) or "data" not in data:
        return "❌ 无效的新闻数据格式"

    news_list = data.get("data", [])
    if not news_list:
        return "📰 未找到相关新闻"

    # 格式化新闻内容
    result = ["📋 加密货币新闻摘要：\n"]
    result.append("========================================")
    
    for idx, news in enumerate(news_list, 1):
        try:
            title = news.get("title", "无标题")
            summary = news.get("summary", "无摘要")
            publish_time = news.get("pubDate", "未知时间")
            url = news.get("link", "#")

            result.append(f"{idx}. {title}")
            result.append(f"发布时间: {publish_time}")
            result.append(f"摘要: {summary}")
            result.append(f"链接: {url}")
            result.append("----------------------------------------")
        except Exception as e:
            result.append(f"新闻解析错误: {str(e)}")
            result.append("----------------------------------------")

    return '\n'.join(result)
    """
    将批量加密货币价格数据格式化为易读文本。
    :param data: 价格数据（可以是列表、字典或 JSON 字符串）
    :return: 格式化后的批量价格信息字符串
    """
    # 如果传入的是字符串，则先转换为字典/列表
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception as e:
            return f"无法解析批量价格数据: {e}"

    # 如果数据中包含错误信息，直接返回错误提示
    if isinstance(data, dict) and "error" in data:
        return f"⚠️ {data['error']}"

    # 验证是否为有效的价格数据列表
    if not isinstance(data, list) or (len(data) > 0 and not isinstance(data[0], dict)):
        return "❌ 无效的批量价格数据格式"

    # 格式化批量价格数据标题
    result = ["📊 批量价格查询结果：\n"]
    result.append("----------------------------------------")

    # 格式化每个交易对价格数据
    for item in data:
        try:
            symbol = item.get("symbol", "未知交易对")
            price = item.get("price", "N/A")
            # 尝试将价格转换为浮点数以美化显示
            if price != "N/A":
                price = f"{float(price):.8f}"
            result.append(f"交易对: {symbol}\n价格: {price} USDT")
            result.append("----------------------------------------")
        except (KeyError, ValueError) as e:
            result.append(f"⚠️ {item} 解析错误: {str(e)}")
            result.append("----------------------------------------")

    return '\n'.join(result)


@mcp.tool()
async def query_crypto_price(symbol: str) -> str:
    """
    输入加密货币交易对（如 BTCUSDT），返回当前价格信息。
    :param symbol: 交易对符号（需使用大写，如 BTCUSDT）
    :return: 格式化后的价格信息
    """
    data = await fetch_crypto_price(symbol)
    return format_crypto_data(data)

@mcp.tool()
async def query_crypto_klines(symbol: str, interval: str, limit: int = 100) -> str:
    """
    输入加密货币交易对、时间周期和K线数量，返回过往K线数据。
    :param symbol: 交易对符号（需使用大写，如 BTCUSDT）
    :param interval: 时间周期（如 1m, 5m, 1h, 1d）
    :param limit: 获取K线数量（1-1000，默认100）
    :return: 格式化后的K线信息
    """
    data = await fetch_crypto_klines(symbol, interval, limit)
    return format_crypto_klines(data)

@mcp.tool()
async def query_crypto_news(length: int = 0) -> str:
    """
    通过Odaily的权威加密货币新闻源查询加密货币相关新闻
    :param length: 0 表示今天的新闻，1 表示昨天的新闻，默认 0
    :return: 格式化后的新闻信息
    """
    data = await fetch_crypto_news(length)
    return format_crypto_news(data)

@mcp.tool()
async def query_batch_crypto_prices(symbols: list) -> str:
    """
    批量查询多个加密货币的当前价格。
    :param symbols: 交易对符号列表（需使用大写，如 ["BTCUSDT", "ETHUSDT"]）
    :return: 格式化后的批量价格信息
    """
    data = await fetch_batch_crypto_prices(symbols)
    return format_batch_crypto_data(data)

@mcp.tool()
async def query_funding_rate(symbol: str, limit: int = 10) -> str:
    """
    输入加密货币交易对，返回过往资金费率数据。
    :param symbol: 交易对符号（需使用大写永续合约符号，如 BTCUSDT）
    :param limit: 获取记录数量（1-1000，默认10）
    :return: 格式化后的资金费率信息
    """
    data = await fetch_funding_rate(symbol, limit)
    return format_funding_rate(data)

if __name__ == "__main__":
    # 以标准 I/O 方式运行 MCP 服务器
    mcp.run(transport='stdio')