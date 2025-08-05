"""
FastAPI-based Web UI for MCP Client
"""
import asyncio
import json
from typing import Dict, Any, List
from fastapi import FastAPI, Request, Form, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

from mcp_client import MCPClient

# Initialize FastAPI app
app = FastAPI(title="MCP Client Web UI", description="Web interface for MCP Client")
app.mount("/static", StaticFiles(directory="static"), name="static")
# Initialize templates
templates = Jinja2Templates(directory="templates")

# Global MCP client instance
mcp_client = None

@app.on_event("startup")
async def startup_event():
    """Initialize MCP client on startup"""
    global mcp_client
    try:
        mcp_client = MCPClient()
        # Connect to all MCP servers asynchronously
        print("正在连接所有MCP服务器...")
        connect_tasks = []
        for server_name in mcp_client.mcp_servers.keys():
            connect_tasks.append(connect_to_server_async(server_name))
        
        # Wait for all connections to complete
        await asyncio.gather(*connect_tasks, return_exceptions=True)
        
        if not mcp_client.servers:
            print("❌ 没有成功连接到任何MCP服务器")
    except Exception as e:
        print(f"❌ 初始化MCP客户端失败: {str(e)}")

async def connect_to_server_async(server_name: str):
    """Connect to a server asynchronously"""
    global mcp_client
    try:
        await mcp_client.connect_to_server(server_name)
        print(f"✅ 成功连接到 {server_name}")
    except Exception as e:
        print(f"⚠️ 连接 {server_name} 失败: {str(e)}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global mcp_client
    if mcp_client:
        await mcp_client.cleanup()

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serve the main chat interface"""
    # Get available servers and tools
    servers_info = []
    if mcp_client:
        for server_name in mcp_client.servers.keys():
            try:
                session = mcp_client.servers[server_name]
                response = await session.list_tools()
                tools = [tool.name for tool in response.tools]
                servers_info.append({
                    "name": server_name,
                    "tools": tools
                })
            except Exception as e:
                print(f"⚠️ 获取 {server_name} 工具列表失败: {str(e)}")
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "servers": servers_info
    })

@app.post("/chat")
async def chat(query: str = Form(...)):
    """Process chat messages"""
    if not mcp_client:
        return {"error": "MCP客户端未初始化"}
    
    try:
        # Process the query using MCP client
        response = await mcp_client.process_query(query)
        return {"response": response}
    except Exception as e:
        return {"error": f"处理查询时发生错误: {str(e)}"}

@app.post("/reset")
async def reset_conversation():
    """Reset conversation history"""
    if mcp_client:
        mcp_client.reset_conversation()
        return {"status": "对话历史已清除"}
    return {"error": "MCP客户端未初始化"}

@app.get("/servers")
async def list_servers():
    """List available servers and their tools"""
    servers_info = []
    if mcp_client:
        for server_name in mcp_client.servers.keys():
            try:
                session = mcp_client.servers[server_name]
                response = await session.list_tools()
                tools = [tool.name for tool in response.tools]
                servers_info.append({
                    "name": server_name,
                    "tools": tools
                })
            except Exception as e:
                print(f"⚠️ 获取 {server_name} 工具列表失败: {str(e)}")
    return {"servers": servers_info}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)