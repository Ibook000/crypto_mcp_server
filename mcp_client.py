import asyncio
import os
import json
import time
from typing import Optional
from contextlib import AsyncExitStack
import logging

from openai import AsyncOpenAI, RateLimitError
import random

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client



class MCPClient:
    def __init__(self):
        """Initialize MCP client with config and MCP server list."""
        self.exit_stack = AsyncExitStack()
        
        # Logging setup
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
        
        # Read main config
        with open('config.json', 'r') as f:
            config = json.load(f)
        
        # Read MCP server config
        try:
            with open('mcp.json', 'r') as f:
                mcp_config = json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError("mcp.json not found in project root")
        except json.JSONDecodeError:
            raise ValueError("Invalid mcp.json syntax")

        self.openai_api_key = config.get('openai_api_key') or os.environ.get('OPENAI_API_KEY', '')
        self.base_url = config.get('base_url') or os.environ.get('MOONSHOT_BASE_URL', 'https://api.moonshot.cn/v1')
        self.model = config.get('model')  # Default model
        self.mcp_servers = mcp_config.get('mcpServers', {})  # Load all MCP server configs
        self.max_retries = config.get('max_retries', 3)  # Max retry attempts
        self.retry_delay = config.get('retry_delay', 1)  # Base retry delay (seconds)
        self.max_delay = config.get('max_delay', 60)  # Max retry delay (seconds)
        
        if not self.openai_api_key:
            raise ValueError("OpenAI API key not found. Set openai_api_key in config.json or OPENAI_API_KEY in .env")
        if not self.mcp_servers:
            raise ValueError("No MCP server configuration found. Check mcp.json")
        
        self.client = AsyncOpenAI(api_key=self.openai_api_key, base_url=self.base_url) # Create OpenAI async client
        self.session: Optional[ClientSession] = None
        self.servers = {}
        self.exit_stack = AsyncExitStack()
        self.conversation_history = []  # Conversation history storage        

    async def connect_to_server(self, server_name: str):
        """Connect to an MCP server by name and list available tools."""
        # Get server config
        server_config = self.mcp_servers.get(server_name)
        if not server_config:
            raise ValueError(f"Server '{server_name}' not found in mcp.json\nAvailable servers: {list(self.mcp_servers.keys())}")

        # Build server params
        server_params = StdioServerParameters(
            command=server_config['command'],
            args=server_config['args'],
            env=None
        )

        # Start MCP server and establish communication
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        stdio, write = stdio_transport
        # Create and store session
        session = await self.exit_stack.enter_async_context(ClientSession(stdio, write))
        self.servers[server_name] = session
        
        # Initialize and list tools
        await session.initialize()
        response = await session.list_tools()
        tools = response.tools
        print(f"\n{server_name} tools:", [tool.name for tool in tools])


        
    def _calculate_delay(self, attempt: int, base_delay: float = None) -> float:
        """Calculate exponential backoff delay."""
        if base_delay is None:
            base_delay = self.retry_delay
        
        # Exponential backoff + jitter
        delay = min(base_delay * (2 ** attempt) + random.uniform(0, 1), self.max_delay)
        return delay

    async def _call_with_retry(self, func, *args, **kwargs):
        """API call wrapper with retry mechanism."""
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except RateLimitError as e:
                last_exception = e
                if attempt < self.max_retries:
                    delay = self._calculate_delay(attempt)
                    self.logger.warning(f"Rate limit hit (attempt {attempt + 1}/{self.max_retries + 1}), retrying in {delay:.1f}s...")
                    await asyncio.sleep(delay)
                else:
                    self.logger.error(f"Max retries ({self.max_retries + 1}) exceeded, aborting")
                    raise
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries and "429" in str(e):
                    delay = self._calculate_delay(attempt)
                    self.logger.warning(f"Possible rate limit (attempt {attempt + 1}/{self.max_retries + 1}), retrying in {delay:.1f}s...")
                    await asyncio.sleep(delay)
                else:
                    raise
        
        raise last_exception

    async def process_query(self, query: str) -> str:
        """
        Process a query through the LLM with MCP tool calling (Function Calling).
        Includes rate-limit handling, retry mechanism, and conversation memory.
        """
        # Append user query to history
        self.conversation_history.append({"role": "user", "content": query})
        
        # List all connected server tools
        all_tools = []
        for server_name, session in self.servers.items():
            try:
                response = await session.list_tools()
                server_tools = [{
                    **tool.model_dump(),
                    "server_name": server_name  # Tag with server name
                } for tool in response.tools]
                all_tools.extend(server_tools)
                print(f"\n{server_name} tools:", [t['name'] for t in server_tools])
            except Exception as e:
                print(f"Failed to get tools from {server_name}: {str(e)}")
        
        if not all_tools:
            raise ValueError("No tools available from any MCP server")
        
        available_tools = [{
              "type": "function",
              "function": {
                  "name": f"{tool['server_name']}_{tool['name']}",  # Add server name prefix
                  "description": f"[{tool['server_name']}] {tool['description']}",  # Note server source
                  "input_schema": tool['inputSchema']
              }
          } for tool in all_tools]
        
        # Multi-turn tool call loop
        while True:
            try:
                # Call API with retry and full conversation history
                response = await self._call_with_retry(
                    self.client.chat.completions.create,
                    model=self.model,            
                    messages=self.conversation_history,  # Full conversation history
                    tools=available_tools,
                    max_tokens=4000  # Limit tokens to avoid extra cost
                )
                
                content = response.choices[0]
                # Append model response to history
                self.conversation_history.append(content.message.model_dump())
                
                if content.finish_reason == "tool_calls":
                    # Handle all tool calls
                    for tool_call in content.message.tool_calls:
                        full_tool_name = tool_call.function.name
                        tool_args = json.loads(tool_call.function.arguments)
                        
                        # Parse server and tool name
                        if '_' in full_tool_name:
                            server_name, tool_name = full_tool_name.split('_', 1)
                            session = self.servers.get(server_name)
                            if not session:
                                raise ValueError(f"No session found for server '{server_name}'")
                        else:
                            raise ValueError(f"Invalid tool name format, expected 'server_name_tool_name': {full_tool_name}")
                        
                        # Execute tool and log result
                        print(f"\nExecuting tool: {tool_name} (args: {tool_args})")
                        result = await session.call_tool(tool_name, tool_args)
                        tool_response = result.content[0].text
                        print(f"Tool result: {tool_response}")  # Show abbreviated result
                        
                        # Append tool result to history
                        self.conversation_history.append({
                            "role": "tool",
                            "content": tool_response,
                            "tool_call_id": tool_call.id,
                        })
                        
                        # Brief delay between tool calls to avoid rate limits
                        await asyncio.sleep(0.5)
                else:
                    # Task complete, return final result
                    return content.message.content
                    
            except RateLimitError as e:
                self.logger.error(f"Rate limit error: {str(e)}")
                return "Request failed due to API rate limiting. Please try again later."
            except Exception as e:
                self.logger.error(f"Query processing error: {str(e)}")
                return f"Query processing error: {str(e)}"
    
    async def chat_loop(self):
        """Run the interactive chat loop."""
        print("\nMCP Client started. Type 'quit' to exit, 'reset' to clear history")

        while True:
            try:
                query = input("\n: ").strip()
                if query.lower() == 'quit':
                    break
                elif query.lower() == 'reset':
                    self.reset_conversation()
                    continue
                
                response = await self.process_query(query)  # Send user input to OpenAI API
                print(f"\n: {response}")

            except Exception as e:
                print(f"\nError: {str(e)}")

    async def cleanup(self):
        """Clean up resources."""
        await self.exit_stack.aclose()
    
    def reset_conversation(self):
        """Reset conversation history."""
        self.conversation_history.clear()
        print("Conversation history cleared.")

async def main():
    client = MCPClient()
    try:
        # Connect all MCP servers
        print("Connecting to MCP servers...")
        for server_name in client.mcp_servers.keys():
            try:
                await client.connect_to_server(server_name)
                print(f"Connected to {server_name}")
            except Exception as e:
                print(f"Failed to connect to {server_name}: {str(e)}")

        if not client.servers:
            print("No MCP servers connected, exiting")
            return

        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    import sys
    asyncio.run(main())