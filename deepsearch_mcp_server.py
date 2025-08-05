import logging
import json
from typing import Dict, Any
from tavily import TavilyClient
import asyncio

from openai import OpenAI
import os

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('deepsearch_mcp_server.log'),
        logging.StreamHandler()
    ]
)
def search(query: str) -> str:
    """
    执行深度调研并返回结构化结果，使用AVILY进行网页搜索获取资料
    :param query: 调研查询关键词或问题
    :param max_results: 最大返回结果数量 (1-20)
    :param sources: 信息来源类型列表，可选值: web, scholar, database, internal
    :return: JSON格式的调研结果
    """
    client=TavilyClient(
        api_key="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",
    )
    response = client.search(
        query=query,
        search_depth="advanced"
    )
    


    #print(response["results"])
    
    return response["results"]
def format_search(data: dict[str, Any] | str) -> str:
    """
    将调研结果格式化为易读文本。
    :param data: 调研结果数据（可以是字典或 JSON 字符串）
    :return: 格式化后的调研结果字符串
    """

    result = ["调研结果摘要：\n"]
    for i in data:
        title=i['title']
        content=i['content']
        url=i['url']
        result.append(
            f"标题：{title}\n内容：{content}\n网址：{url}\n"
        )
    return ''.join(result)  # 将列表转换为字符串后返回

# 初始化 OpenAI 客户端
client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key="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",
)

def summarize_search_results(data: dict[str, Any] | str) -> str:
    """
    总结深度调研搜索的资料，生成 MD 格式的返回结果，并且标注出处 URL。
    使用 OpenAI API 对内容进行智能总结。
    :param data: 调研结果数据（可以是字典或 JSON 字符串）
    :return: MD 格式的总结字符串
    """
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            return "无法解析输入的 JSON 字符串"

    summary = ["# 深度调研搜索资料总结\n"]
    processed = False
    
    for index, item in enumerate(data, start=1):
        if 'title' in item and 'content' in item and 'url' in item:
            title = item['title']
            content = item['content']
            url = item['url']
            try:
                # 调用 OpenAI API 对内容进行总结
                response = client.chat.completions.create(
                    model="google/gemini-2.0-flash-exp:free",
                    messages=[
                        {
                            "role": "system",
                            "content": "根据用户的资料进行深度调研 生成一份md格式的调研报告 并且引用到资料的时候需要在那个位置标注出处URL 并且要求输出5000字以上"
                        },
                        {
                            "role": "user",
                            "content": content
                        }
                    ]
                )
                summarized_content = response.choices[0].message.content
                print(summarized_content)
            except Exception as e:
                logging.error(f"调用 OpenAI API 失败: {e}")
                summarized_content = content

            processed = True
            summary.append(
                f"## {index}. {title}\n\n"
                f"{summarized_content}\n\n"
                f"**出处**：[{url}]({url})\n\n"
            )
        else:
            continue
    
    if not processed:
        summary.append("未找到相关搜索结果。\n")
    
    print(summary)
    return ''.join(summary)  # 添加返回语句，将列表转换为字符串
def save_summary_to_md(summary: str, filename: str = "search_summary.md"):
    """
    将总结内容保存为 MD 文件
    :param summary: 要保存的 MD 格式总结内容
    :param filename: 保存的文件名，默认为 search_summary.md
    """
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(filename) or '.', exist_ok=True)
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(summary)
        logging.info(f"总结内容已保存到 {filename}")
    except Exception as e:
        logging.error(f"保存 MD 文件失败: {e}")

if __name__ == "__main__":
    save_summary_to_md(summarize_search_results(search("今日加密市场新闻")))
