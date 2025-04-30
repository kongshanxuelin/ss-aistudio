import asyncio
import os, sys
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client
from contextlib import asynccontextmanager, AsyncExitStack # type: ignore
import logging as log
base_path = os.path.join(os.path.dirname(__file__), "../../")
sys.path.append(base_path)
from src.database.database_manager import EmbeddingStorage

# 增加环境路径的设置
os.environ['PYTHONPATH'] = os.path.join(base_path, "third_part/bin")
os.environ['PATH'] = os.path.join(base_path, "third_part/bin") + os.pathsep + os.environ['PATH']

active_mcp_services = {}  # 记录正在运行的MCP服务 {mcpUid: 服务实例}
params_mcp_services = {}  # 记录参数配置 {mcpUid: 配置参数}

class MCPClient:
    def __init__(self, db_config):
        if type(db_config) == str:
            db_config = json.loads(db_config)
        self.mac_manager = EmbeddingStorage(db_config['user_name'], db_config['db_path']).mcp_manager
        # self.exit_stack = AsyncExitStack()
        self.session_contexts = {}

    async def connect_to_stdio_server(self, server_id, config):
        exit_stack = AsyncExitStack()
        await exit_stack.__aenter__()
        server_params = StdioServerParameters(
            command=config['mcpCommand'],
            args=json.loads(config['mcpArgs']),
            env=json.loads(config.get('mcpEnvs', '{}'))
        )
        params_mcp_services[server_id] = config
        
        # 为每个服务器创建独立连接
        stdio_transport = await exit_stack.enter_async_context(stdio_client(server_params))
        stdio, write = stdio_transport
        session = await exit_stack.enter_async_context(ClientSession(stdio, write))
        await session.initialize()
        self.session_contexts[server_id] = exit_stack
        
        # 存储会话并用服务器ID作为键
        active_mcp_services[server_id] = session    
        log.info(f"\n已连接到stdio服务器 {config['mcpName']}，支持工具: {[tool.name for tool in (await session.list_tools()).tools]}")
        self.mac_manager.add_mcp(mcpUid=server_id, mcpActivate=True)

    async def connect_to_sse_server(self, server_id: str, config: dict):
        """连接到SSE服务器"""
        exit_stack = AsyncExitStack()
        await exit_stack.__aenter__()
        server_url = config['mcpBaseUrl']
        params_mcp_services[server_id] = config
        streams_context = sse_client(url=server_url)        
        streams = await exit_stack.enter_async_context(streams_context)
        session_context = ClientSession(*streams)        
        session = await exit_stack.enter_async_context(session_context)
        self.session_contexts[server_id] = exit_stack      
        await session.initialize()        
        # List available tools
        active_mcp_services[server_id] = session 
        log.info(f"\n已连接到SSE服务器 {config['mcpName']}，支持工具: {[tool.name for tool in (await session.list_tools()).tools]}")
        self.mac_manager.add_mcp(mcpUid=server_id, mcpActivate=True)

    async def service_monitor(self):
        """接口1：服务状态同步（从数据库获取最新状态）"""
        try:
            # 从数据库获取所有激活的MCP服务
            db_services = self.mac_manager.get_mcp('all')
            active_in_db = {s['mcpUid']: s for s in db_services if s.get('mcpActivate', False)}
            
            # 关闭多余服务
            for uid in set(active_mcp_services) - set(active_in_db):
                await self._stop_service(uid)
                self.mac_manager.add_mcp(mcpUid=uid, mcpActivate=False)
                log.info(f"已关闭多余服务: {uid}")
            
            # 启动新增服务
            for uid, config in active_in_db.items():
                if uid not in active_mcp_services:
                    await self._start_service(uid, config)
                    print(f"已启动新增服务: {uid}")
                else:
                    await self._restart_service(uid, strict=False)
                    print(f"已重启服务: {uid}")
            log.info(f"服务状态同步完成，当前运行服务: {list(active_mcp_services.keys())}")
            return {"code": 200, "message":None, "result":{"message":"同步完成", "running_services": list(active_mcp_services.keys())}}
        except Exception as e:
            log.error(f"服务状态同步出错: {e}")
            return {"code": 400, "message": str(e), "result":None}

    async def control_service(self, mcpUid: str, action: str):
        """接口2：服务控制开关"""
        try:
            if action == "start":
                if mcpUid not in active_mcp_services:
                    config = self.mac_manager.get_mcp(mcp_uid=mcpUid)
                    config['mcpActivate'] = True
                    await self._start_service(mcpUid, config)
            elif action == "stop":
                await self._stop_service(mcpUid)
                self.mac_manager.add_mcp(mcpUid=mcpUid, mcpActivate=False)
            log.info(f"服务 {mcpUid} 已{action}")
            return {"code": 200, "result":{"action": action, "mcpUid": mcpUid}}
        except Exception as e:
            log.error(f"控制服务 {mcpUid} 时出错: {e}")
            return {"code": 400, "message": str(e), "result":None}
        
    async def list_tools(self, mcpUids="all"):
        available_tools = []
        global active_mcp_services
        try:
            for sname, session in active_mcp_services.items():
                if mcpUids != "all" and sname not in mcpUids:
                    continue
                response = await session.list_tools()
                session_tools = response.tools
            
                available_tools += [{
                    "type": "function",
                    "function": {
                        "name": sname+"_:_"+tool.name,
                        "description": tool.description.strip(),
                        "parameters": tool.inputSchema or {
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    }
                } for tool in session_tools if tool.inputSchema is not None]
            log.info(f"get all[Available tools: {[t['function']['name'] for t in available_tools]}]")
            return {"code": 200, "message":None, "result": available_tools}
        except Exception as e:
            log.error(f"获取工具列表时出错: {e}")
            return {"code": 400, "message": str(e), "result":None}
        

    async def execute_service(self, tool_calls_list:str):
        """接口3：执行服务功能"""
        from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall,Function
        if type(tool_calls_list) == str:
            try:
                tool_calls_list = json.loads(tool_calls_list)
            except:
                tool_calls_list = eval(tool_calls_list)
        try:
            messages = []
            for tool_call in tool_calls_list:
                if type(tool_call) == dict:
                    tool_id = tool_call['id']
                    tool_name = tool_call['function']['name']
                    arguments = tool_call['function']['arguments']
                else:
                    tool_id = tool_call.id
                    tool_name = tool_call.function.name
                    arguments = tool_call.function.arguments
                if tool_name is None:
                    continue
                tool_args = json.loads(arguments)
                sname,fun_name = tool_name.split("_:_", maxsplit=2)
            
                # 执行工具
                log.info(f"[Calling tool {tool_name} with args {tool_args}]")
                result = await active_mcp_services[sname].call_tool(fun_name, tool_args)
                # print(f"\n\n[Calling tool {tool_name} with args {tool_args}]\nget result: {result.content[0].text}\n\n")
                log.info(f"****[Calling result: {result.content[0].text}]****")

                messages.append({
                    "role": "assistant",
                    "tool_calls": [{
                        "id": tool_id,
                        "type": "function",
                        "function": {
                            "name": tool_name,
                            "arguments": json.dumps(tool_args)
                        }
                    }]
                })
                
                messages.append({
                    "role": "tool",
                    "content": result.content[0].text,
                    "tool_call_id": tool_id,
                })
            return {"code": 200, "message":None, "result": messages}
        except Exception as e:
            log.error(f"执行服务功能时出错: {e}")
            return {"code": 400, "message": str(e), "result": None}

    async def _start_service(self, uid: str, config: dict):
        """启动单个服务"""
        if config['mcpType'] == 'stdio':
            await self.connect_to_stdio_server(uid, config)
        elif config['mcpType'] == 'sse':
            await self.connect_to_sse_server(uid, config)
    
    async def _restart_service(self, uid: str, strict: bool = False):
        """关闭服务"""
        config = self.mac_manager.get_mcp(mcp_uid=uid)
        config['mcpActivate'] = True
        if uid in active_mcp_services:
            if strict:
                await self._stop_service(uid)
                await self._start_service(uid, config)
            else:
                if config['mcpType'] == 'stdio' and (config['mcpCommand'] != params_mcp_services[uid]['mcpCommand'] or 
                                                     config['mcpArgs'] != params_mcp_services[uid]['mcpArgs'] or
                                                     config['mcpEnvs']!= params_mcp_services[uid]['mcpEnvs']):
                    await self._stop_service(uid)
                    await self._start_service(uid, config)
                    log.info(f"已重启服务: {uid}")   
                elif config['mcpType'] =='sse' and (config['mcpBaseUrl']!= params_mcp_services[uid]['mcpBaseUrl']):
                    await self._stop_service(uid)
                    await self._start_service(uid, config)
                    log.info(f"已重启服务: {uid}")
            log.info(f"已重启服务: {uid}")
        else:
            log.info(f"服务未启动: {uid}")
            await self._start_service(uid, config)
            
    async def _stop_service(self, uid: str):
        """停止单个服务"""
        global active_mcp_services, params_mcp_services
        session = active_mcp_services.get(uid)
        if session:
            try:
                await session.__aexit__(None, None, None)
            except Exception as e:
                log.warning(f"关闭 session 异常: {e}")
            log.info(f"已关闭会话 {uid}")

        # 🔻 关闭对应的 ExitStack
        exit_stack = self.session_contexts.pop(uid, None)
        if exit_stack:
            try:
                await exit_stack.aclose()
            except Exception as e:
                log.warning(f"关闭 exit_stack 异常: {e}")
            log.info(f"已释放上下文资源: {uid}")
        
        # 清理配置参数
        active_mcp_services.pop(uid, None)
        params_mcp_services.pop(uid, None)
        log.info(f"已停止服务: {uid}")
            
    async def cleanup(self):
        """显式关闭所有已建立的会话连接"""
        print("\n🛑 正在关闭所有服务器连接...")
        for uid in list(active_mcp_services):
            await self._stop_service(uid)
        active_mcp_services.clear()
        params_mcp_services.clear()
        self.session_contexts.clear()
        log.info("所有服务器连接已关闭")

