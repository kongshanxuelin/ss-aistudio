import socketio
import logging as log

# 创建SocketIO客户端（使用WebSocket传输）
sio = socketio.Client()
# 添加重连配置
sio.reconnection_delay = 5  # 5秒重试间隔
sio.reconnection_attempts = 3  # 最大重试次数

@sio.event
def connect():
    print("成功连接到服务器")


# 添加错误处理
@sio.event
def connect_error(data):
    print("连接失败:", data)

@sio.event
def client_connect(data):
    print(f'收到服务器连接确认: {data}')
    
# @sio.event
# def progress_update(data):
#     # 结构化打印
#     # log.info(f"[进度更新] 文件ID {data['file_id']}")
#     # print(f"所属知识库: {data['collection_code']}")
#     # print(f"当前进度: {data['progress']}%")
#     # # print(f"状态描述: {data['msg']}")
#     # # print(f"完成状态: {'成功' if data['status'] == 1 else '进行中'}")
#     # print("-" * 40)  # 分隔线
    
#     # 原始数据打印（调试用）
#     log.info(f"原始数据:{data}, 当前进度:{data['progress']}")
#     print(f"原始数据:{data}, 当前进度:{data['progress']}")
    
#     # 调用外部回调
#     progress_callback(data)  # <- 新增回调调用
    
#     # 自动断开逻辑
#     if data['progress'] == 100:
#         print("检测到进度完成，主动断开连接...")
#         sio.disconnect()
@sio.event
def disconnect():
    print("与服务器断开连接")


if __name__ == '__main__':

    try:
        # 连接到服务器（地址需替换为实际服务端IP）
        sio.connect('https://ai-doc-nn.qeubee.cn/', 
                transports=['websocket'],)
        sio.wait()  # 保持连接
    except Exception as e:
        print(f"连接失败: {str(e)}")
