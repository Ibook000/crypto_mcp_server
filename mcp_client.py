import asyncio
import os
import json
import time
from typing import Optional
from contextlib import AsyncExitStack
import logging

from openai import OpenAI, RateLimitError
import random

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client



class MCPClient:
    def __init__(self):
        """初始化 MCP 客户端，加载配置文件和MCP服务器列表"""
        self.exit_stack = AsyncExitStack()
        
        # 设置日志
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
        
        # 读取主配置文件
        with open('config.json', 'r') as f:
            config = json.load(f)
        
        # 读取MCP服务器配置
        try:
            with open('mcp.json', 'r') as f:
                mcp_config = json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError("❌ mcp.json文件不存在，请确保该文件在项目根目录")
        except json.JSONDecodeError:
            raise ValueError("❌ mcp.json格式错误，请检查JSON语法")
        
        self.openai_api_key = config.get('openai_api_key')
        self.base_url = config.get('base_url')
        self.model = config.get('model')  # 默认模型
        self.mcp_servers = mcp_config.get('mcpServers', {})  # 加载所有MCP服务器配置
        self.max_retries = config.get('max_retries', 3)  # 最大重试次数
        self.retry_delay = config.get('retry_delay', 1)  # 基础重试延迟（秒）
        self.max_delay = config.get('max_delay', 60)  # 最大重试延迟（秒）
        
        if not self.openai_api_key:
            raise ValueError("❌ 未找到 OpenAI API Key，请在 config.json 文件中设置 openai_api_key")
        if not self.mcp_servers:
            raise ValueError("❌ 未找到MCP服务器配置，请检查mcp.json文件")
        
        self.client = OpenAI(api_key=self.openai_api_key, base_url=self.base_url) # 创建OpenAI client
        self.session: Optional[ClientSession] = None
        self.servers = {}
        self.exit_stack = AsyncExitStack()
        self.conversation_history = []  # 用于存储对话历史        

    async def connect_to_server(self, server_name: str):
        """根据服务器名称连接到指定的MCP服务器并列出可用工具"""
        # 获取服务器配置
        server_config = self.mcp_servers.get(server_name)
        if not server_config:
            raise ValueError(f"❌ 未找到名为 '{server_name}' 的MCP服务器配置，请检查mcp.json\n可用服务器: {list(self.mcp_servers.keys())}")

        # 构建服务器参数
        server_params = StdioServerParameters(
            command=server_config['command'],
            args=server_config['args'],
            env=None
        )

        # 启动 MCP 服务器并建立通信
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        stdio, write = stdio_transport
        # 创建并存储会话
        session = await self.exit_stack.enter_async_context(ClientSession(stdio, write))
        self.servers[server_name] = session
        
        # 初始化并获取工具列表
        await session.initialize()
        response = await session.list_tools()
        tools = response.tools
        print(f"\n{server_name} 服务器支持工具:", [tool.name for tool in tools])


        
    def _calculate_delay(self, attempt: int, base_delay: float = None) -> float:
        """计算指数退避延迟时间"""
        if base_delay is None:
            base_delay = self.retry_delay
        
        # 指数退避 + 随机抖动
        delay = min(base_delay * (2 ** attempt) + random.uniform(0, 1), self.max_delay)
        return delay

    async def _call_with_retry(self, func, *args, **kwargs):
        """带重试机制的API调用包装器"""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except RateLimitError as e:
                last_exception = e
                if attempt < self.max_retries:
                    delay = self._calculate_delay(attempt)
                    self.logger.warning(f"⚠️ 速率限制错误 (尝试 {attempt + 1}/{self.max_retries + 1})，等待 {delay:.1f} 秒后重试...")
                    await asyncio.sleep(delay)
                else:
                    self.logger.error(f"❌ 达到最大重试次数 ({self.max_retries + 1})，放弃重试")
                    raise
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries and "429" in str(e):
                    delay = self._calculate_delay(attempt)
                    self.logger.warning(f"⚠️ 可能的速率限制错误 (尝试 {attempt + 1}/{self.max_retries + 1})，等待 {delay:.1f} 秒后重试...")
                    await asyncio.sleep(delay)
                else:
                    raise
        
        raise last_exception

    async def process_query(self, query: str) -> str:
        """
        使用大模型处理查询并调用可用的 MCP 工具 (Function Calling)
        包含速率限制处理和重试机制，以及对话历史记忆功能
        """
        # 将用户查询添加到对话历史
        self.conversation_history.append({"role": "user", "content": query})
        
        # 列出所有已连接服务器的工具
        all_tools = []
        for server_name, session in self.servers.items():
            try:
                response = await session.list_tools()
                server_tools = [{
                    **tool.model_dump(),
                    "server_name": server_name  # 添加服务器名称标识
                } for tool in response.tools]
                all_tools.extend(server_tools)
                print(f"\n{server_name} 服务器支持工具:", [t['name'] for t in server_tools])
            except Exception as e:
                print(f"⚠️ 获取 {server_name} 工具列表失败: {str(e)}")
        
        if not all_tools:
            raise ValueError("❌ 未从任何MCP服务器获取到工具")
        
        available_tools = [{
              "type": "function",
              "function": {
                  "name": f"{tool['server_name']}_{tool['name']}",  # 添加服务器前缀
                  "description": f"[{tool['server_name']}] {tool['description']}",  # 注明服务器来源
                  "input_schema": tool['inputSchema']
              }
          } for tool in all_tools]
        
        # 循环处理多轮工具调用，直到任务完成
        while True:
            try:
                # 使用重试机制调用API，传递包含历史的完整对话
                response = await self._call_with_retry(
                    self.client.chat.completions.create,
                    model=self.model,            
                    messages=self.conversation_history,  # 使用完整的对话历史
                    tools=available_tools,
                    max_tokens=4000  # 限制token数量以避免额外费用
                )
                
                content = response.choices[0]
                # 将模型响应添加到对话历史
                self.conversation_history.append(content.message.model_dump())
                
                if content.finish_reason == "tool_calls":
                    # 处理所有工具调用
                    for tool_call in content.message.tool_calls:
                        full_tool_name = tool_call.function.name
                        tool_args = json.loads(tool_call.function.arguments)
                        
                        # 解析服务器名称和工具名称
                        if '_' in full_tool_name:
                            server_name, tool_name = full_tool_name.split('_', 1)
                            session = self.servers.get(server_name)
                            if not session:
                                raise ValueError(f"❌ 未找到服务器 '{server_name}' 的连接会话")
                        else:
                            raise ValueError(f"❌ 工具名称格式错误，应为 'server_name_tool_name': {full_tool_name}")
                        
                        # 执行工具并记录结果
                        print(f"\n🔧 正在执行工具: {tool_name} (参数: {tool_args})")
                        result = await session.call_tool(tool_name, tool_args)
                        tool_response = result.content[0].text
                        print(f"✅ 工具返回结果: {tool_response}")  # 显示部分结果
                        
                        # 将工具结果添加到对话历史
                        self.conversation_history.append({
                            "role": "tool",
                            "content": tool_response,
                            "tool_call_id": tool_call.id,
                        })
                        
                        # 在工具调用之间添加短暂延迟以避免速率限制
                        await asyncio.sleep(0.5)
                else:
                    # 任务完成，返回最终结果
                    return content.message.content
                    
            except RateLimitError as e:
                self.logger.error(f"❌ 速率限制错误: {str(e)}")
                return "抱歉，由于API速率限制，暂时无法处理您的请求。请稍后再试。"
            except Exception as e:
                self.logger.error(f"❌ 处理查询时发生错误: {str(e)}")
                return f"处理查询时发生错误: {str(e)}"
    
    async def chat_loop(self):
        """运行交互式聊天循环"""
        print("\n🤖 MCP 客户端已启动！输入 'quit' 退出，输入 'reset' 清除对话历史")

        while True:
            try:
                query = input("\n😊: ").strip()
                if query.lower() == 'quit':
                    break
                elif query.lower() == 'reset':
                    self.reset_conversation()
                    continue
                
                response = await self.process_query(query)  # 发送用户输入到 OpenAI API
                print(f"\n🤖: {response}")

            except Exception as e:
                print(f"\n⚠️ 发生错误: {str(e)}")

    async def cleanup(self):
        """清理资源"""
        await self.exit_stack.aclose()
    
    def reset_conversation(self):
        """重置对话历史"""
        self.conversation_history.clear()
        print("🔄 对话历史已清除")

async def main():
    client = MCPClient()
    try:
        # 连接所有MCP服务器
        print("正在连接所有MCP服务器...")
        for server_name in client.mcp_servers.keys():
            try:
                await client.connect_to_server(server_name)
                print(f"✅ 成功连接到 {server_name}")
            except Exception as e:
                print(f"⚠️ 连接 {server_name} 失败: {str(e)}")

        if not client.servers:
            print("❌ 没有成功连接到任何MCP服务器，程序退出")
            return

        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    import sys
    asyncio.run(main())