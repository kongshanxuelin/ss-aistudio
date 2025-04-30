import asyncio
import os
import json
import signal
import time
from src.logs import get_logger
get_logger()
import logging as log
from fastapi import FastAPI, BackgroundTasks, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from src.mcps.mcp_client import MCPClient
from contextlib import asynccontextmanager

# 设置环境路径
os.environ['PYTHONPATH'] = os.path.join(os.path.dirname(__file__), "third_part/bin")
os.environ['PATH'] = os.path.join(os.path.dirname(__file__), "third_part/bin") + os.pathsep + os.environ['PATH']

mcp_client_instance = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("🚀 [Lifespan] 服务已启动")
    yield
    if mcp_client_instance:
        log.info("🛑 [Lifespan] 正在关闭 MCPClient...")
        await mcp_client_instance.cleanup()

app = FastAPI(lifespan=lifespan)

# 启用 CORS（可选）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/init")
async def initialize_client(request: Request):
    """
    初始化 MCPClient，传入 db_config (json 格式)
    示例: {
        "db_config": {
            "host": "...",
            "port": ...,
            ...
        }
    }
    """
    global mcp_client_instance
    body = await request.json()
    db_config = body.get("db_config")
    if not db_config:
        raise HTTPException(status_code=400, detail="db_config is required")

    try:
        mcp_client_instance = MCPClient(db_config)
        return {"status": "success", "error_info": None, "success_info": "initialized"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def check_initialized():
    if mcp_client_instance is None:
        raise HTTPException(status_code=400, detail="请先调用 /init 接口进行初始化")


@app.post("/monitor")
async def monitor_services(request: Request):
    if mcp_client_instance is None:
        await initialize_client(request)
    return await mcp_client_instance.service_monitor()

@app.post("/control")
async def control_service(request: Request):
    check_initialized()
    body = await request.json()
    mcpUid = body.get("mcpUid")
    action = body.get("action")
    if action == "start":
        await mcp_client_instance.control_service(mcpUid, action)
        return await mcp_client_instance.list_tools([mcpUid])
    elif action == "stop":
        return await mcp_client_instance.control_service(mcpUid, action)

@app.post("/list_tools")
async def list_tools(request: Request):
    check_initialized()
    body = await request.json()
    mcpUids = body.get("mcpUids", "all")
    return await mcp_client_instance.list_tools(mcpUids)

@app.post("/execute")
async def execute(request: Request):
    check_initialized()
    body = await request.json()
    return await mcp_client_instance.execute_service(body.get("tool_calls_list", '[]'))

@app.get("/health")
async def health_check():
    """
    健康检查接口。
    如果 MCPClient 已初始化，则返回状态信息。
    """
    status = "success"
    mcp_initialized = mcp_client_instance is not None
    return {
        "status": status,
        "error_info": None,
        "result_info": {
            "mcp_initialized": mcp_initialized
        }
    }
    
@app.post("/shutdown")
async def shutdown_service():
    try:
        global mcp_client_instance
        # check_initialized()
        await mcp_client_instance.cleanup()
    except:
        mcp_client_instance = None
    finally:
        #os._exit(0)
        stopHttpServer()

def startHttpServer2(config):
    import threading
    import time
    import uvicorn
    import requests
    if type(config) == str:
        config = json.loads(config)
    port = config.get("port", 8076)
    def threadFunc():
        uvicorn.run("mcp_service:app", host="0.0.0.0", port=port, reload=False)
    thread = threading.Thread(target=threadFunc, daemon=True)
    thread.start()

    response = requests.post(f"http://127.0.0.1:{port}/monitor", json={"db_config": config})
    if response.status_code == 200:
        return json.dumps({"status":"success", "error_info":None, "result_info": response.json()})
    else:
        return json.dumps({"status":"error", "error_info":response.text, "result_info":None})

    # return json.dumps({"status":"success", "error_info":None, "result_info": {}})
def startHttpServer(config):
    import uvicorn
    try:
        uvicorn.run("mcp_service:app", host="0.0.0.0", port=8076, reload=False)
    # import sys, subprocess
    # global server_process
    # if type(config) == str:
    #     config = json.loads(config)
    # python_executable = config.get("python_executable", sys.executable)
    # try:
    #     server_process = subprocess.Popen(
    #         [python_executable, "-m", "uvicorn", "mcp_service:app", "--host", "0.0.0.0", "--port", "8076"],
    #         # creationflags=subprocess.CREATE_NEW_CONSOLE,  # 在新窗口中运行（Windows 专用）
    #         stdout=subprocess.DEVNULL,
    #         stderr=subprocess.DEVNULL
    #     )

    #     # uvicorn.run("mcp_service:app", host="127.0.0.1", port=8076, reload=False)
    #     log.info(f"HTTP Server has been started. PID:{server_process.pid}")
    #     print(f"HTTP Server has been started. PID:{server_process.pid}")
        return json.dumps({"status":"success", "error_info":None, "result_info": {}})
    except Exception as e:
        log.error(f"Failed to start HTTP Server: {e}")
        return json.dumps({"status":"error", "error_info":str(e), "result_info":None})

def stopHttpServer(config):
    global server_process
    # try:
    #     global mcp_client_instance
    #     # check_initialized()
    #     mcp_client_instance.cleanup()
    # except:
    #     mcp_client_instance = None
    if server_process is not None:
        # 尝试优雅地终止子进程
        server_process.terminate()
        try:
            # 等待子进程退出，超时时间为 5 秒
            log.info("Waiting for the server to stop...")
            server_process.wait(timeout=5)
        except subprocess.TimeoutExpired as e:
            # 如果超时仍未退出，强制杀死子进程
            server_process.kill()
        log.info("HTTP Server has been stopped.")
    else:
        log.error("No HTTP Server is running.")

# --- 启动服务（推荐通过命令行启动） ---
if __name__ == "__main__":
    pass
    # import uvicorn
    # uvicorn.run("mcp_service:app", host="0.0.0.0", port=8076, reload=False)
    # startHttpServer()
