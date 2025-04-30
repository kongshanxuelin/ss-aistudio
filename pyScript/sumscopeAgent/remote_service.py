import os
import hashlib # type: ignore
import sqlite3
import json
import requests
import logging as log
from src.api.sockit import sio
from src.logs import get_logger
get_logger()
from configs.remote_configs import *
from src.database.base_manager import RemoteFileBManager

def check_usename_password(
    username: str,
    password: str 
):
    username_hash = hashlib.sha256(username.encode()).hexdigest()
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    if username_hash == REMOTE_USER_HASH and password_hash == REMOTE_PASSWORD_HASH:
        return True
    else:
        return False

def remote_similarity_query(
    all_config: str|dict
) -> str:
    # all_config:text, user_name, db_path, agentId
    if type(all_config) == str:
        all_config = json.loads(all_config)
    # Check if database exists
    target_db_path = os.path.join(all_config['db_path'], f"{all_config['user_name']}.db")
    if not os.path.exists(target_db_path):
        log.error(f"数据库 {target_db_path} 不存在")
        return json.dumps({
            "status": "error",
            "error_info": f"数据库 {target_db_path} 不存在",
            "result_info": None
        }, ensure_ascii=False)
    conn = sqlite3.connect(os.path.join(all_config['db_path'], f"{all_config['user_name']}.db"))
    try:
        remote_file_manager = RemoteFileBManager(conn)
        text = all_config['text']
        cursor = remote_file_manager.execute("""
            select agentId, agentName, knowledgeIdList FROM agents WHERE agentId =?""", (all_config['agentId'],))
        agent_data = dict(cursor.fetchone())
        fileId_list = [int(kid) for kid in agent_data['knowledgeIdList'].split(",")]
        log.info(f"agent_id: {all_config['agentId']}, agent_data: {agent_data}, fileId_list: {fileId_list}")
        
        # 获取 TopK 和 Threshold
        cursor = remote_file_manager.execute("""
            SELECT TopK, Threshold FROM remote_files WHERE FileId IN ({})
        """.format(','.join(['?'] * len(fileId_list))), tuple(fileId_list))
        file_data = cursor.fetchall()
        top_k = file_data[0][0]
        threshold = file_data[0][1]
        log.info(f"top_k: {top_k}, threshold: {threshold}")
        
        playload = {
            "query": text,
            "file_id": fileId_list,
            "embedding_model": "default",
            "db_name": REMOTE_DB, 
            "search_limit": top_k,
            "search_threshold": threshold
        }
        response = requests.post(remote_base_url+"similarity-query", json=playload)
        response_json = response.json()
        
        if response_json['code'] == 200 and response_json['msg']=='问题检索成功':
            all_content = response_json['result']['content_pages']

        results = []
        for idx, content in enumerate(all_content):
            results.append({
                "docId": content['file_id'],
                "content": content['content'],
                "fileName": content['file_name'],
                "similarity": round(content['score'], 4),
            })
        log.info(f'remote similarity success, get {len(results)} contents')
        output_result = {
            "status": "success",
            "error_info": None,
            "result_info": results
        }
        return json.dumps(output_result, ensure_ascii=False)
    except Exception as e:
        log.info(f"Error performing remote similarity query: {e}")
        return json.dumps({
            "status": "error",
            "error_info": str(e),
            "result_info": None
        }, ensure_ascii=False)
    finally:
        conn.close()

def remote_process_file(
    all_config: str|dict
) -> str:
    if type(all_config) == str:
        all_config = json.loads(all_config)
    
    file_path = all_config['file_path']
    file_name = os.path.basename(file_path)
    if not check_usename_password(all_config['user_name'], all_config['password']):
        log.error(f"用户名或密码错误")
        return json.dumps({
            "status": "error",
            "error_info": "用户名或密码错误",
            "result_info": {
                "docId": None,
                "segments_count": 0,
                "fileName": file_name
            } 
        })
        
    # Check if database exists
    target_db_path = os.path.join(all_config['db_path'], f"{all_config['user_name']}.db")
    if not os.path.exists(target_db_path):
        log.error(f"数据库 {target_db_path} 不存在")
        return json.dumps({
            "status": "error",
            "error_info": f"数据库 {target_db_path} 不存在",
            "result_info": {
                "docId": None,
                "segments_count": 0,
                "fileName": file_name
            }
        }, ensure_ascii=False)
    try:
        # 获取文件路径，
        data = {
            "collection_code": REMOTE_DB,
            "embedding_model": REMOTE_EMBEDDING_MODEL,
            "user_name": all_config['user_name']
        }
        
        # 上传文件
        files = {
            "file": (file_name, open(file_path, "rb"), "application/pdf")
        }
        # 发送 POST 请求
        response = requests.post(f"{remote_base_url}/upload-file", data=data, files=files)
        response_json = response.json()
        if response_json['code'] == 200 and response_json['msg']=='File uploaded successfully':
            file_id = response_json['result']
        else:
            return json.dumps({
                "status": "error",
                "error_info": response_json['msg'],
                "result_info": {
                    "docId": None,
                    "segments_count": 0,
                    "fileName": file_name
                }
            }, ensure_ascii=False)
        log.info(f"remote upload file success, file_id: {file_id}")
        
        # 插入数据库
        conn = sqlite3.connect(os.path.join(all_config['db_path'], f"{all_config['user_name']}.db"))
        remote_file_manager = RemoteFileBManager(conn)
        insert_data= {
            'FileName': file_name,
            'FileId': file_id
        }
        add_file_result = remote_file_manager.add_file(**insert_data)     
        log.info(f"add file success, file_id: {file_id}")
        
        try:
            # 连接到服务器（地址需替换为实际服务端IP）
            sio.connect('https://ai-doc-nn.qeubee.cn/', 
                    transports=['websocket'],)
            @sio.event 
            def progress_update(data):
                """通用事件处理器"""
                print(f"原始数据:{data}, 当前进度:{data['progress']}")
                global process, chunk_num
                process = data['progress']
                if data['progress'] == 100:
                    chunk_num = int(data['msg'].split("page_nums: ")[-1])
                    print("检测到进度完成，主动断开连接...")
                    sio.disconnect()
            # 新增超时计时器 (600秒 = 10分钟)
            from threading import Timer # type: ignore
            timeout_timer = Timer(600.0, sio.disconnect)
            timeout_timer.start()
            
            sio.wait()  # 保持连接
            timeout_timer.cancel()  # 连接正常完成时取消计时器
            log.info(f"连接成功, 进程到{process}")
        except Exception as e:
            log.error(f"连接失败: {str(e)}")
            sio.disconnect()
        finally:
            if 'timeout_timer' in locals():
                timeout_timer.cancel()  # 确保清理计时器
                sio.disconnect()

        if add_file_result and process==100:
            result = {
                "status": "success",
                "error_info": None,
                "result_info": {
                    "docId": file_id,
                    "segments_count": chunk_num,
                    "fileName": file_name
                }
            }
            return json.dumps(result, ensure_ascii=False)
        else:
            result = {
                "status": "error",
                "error_info": f"文件处理失败, 进程到{process}",
                "result_info": {
                    "docId": None,
                    "segments_count": 0,
                    "fileName": file_name
                }
            }
            return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        log.error(f"Error processing file: {e}")
        result =  {
            "status": "error",
            "error_info": str(e),
            "result_info": {
                "docId": None,
                "segments_count": 0,
                "fileName": file_name
            }
        }
        return json.dumps(result, ensure_ascii=False)
    finally:
        pass

def remote_save_config(db_config: str|dict) -> dict:
    if type(db_config) == str:
        db_config = json.loads(db_config)

    if not check_usename_password(all_config['user_name'], all_config['password']):
        log.error("用户名或密码错误")
        return json.dumps({
            "status": "error",
            "error_info": "用户名或密码错误",
            "result_info": None
        })
        
    # Check if database exists
    target_db_path = os.path.join(all_config['db_path'], f"{all_config['user_name']}.db")
    if not os.path.exists(target_db_path):
        log.error(f"数据库 {target_db_path} 不存在")
        return json.dumps({
            "status": "error",
            "error_info": f"数据库 {target_db_path} 不存在",
            "result_info": None
        }, ensure_ascii=False)
    try:
        result = {
            "status": "",
            "error_info": None,
            "result_info": None
        }
        conn = sqlite3.connect(os.path.join(all_config['db_path'], f"{all_config['user_name']}.db"))
        remote_file_manager = RemoteFileBManager(conn)

        save_result = remote_file_manager.save_config()
        result["result_info"] = save_result
        result["status"] = "success"
        log.info(f"save config success, result: {save_result}")
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        result["error_info"] = str(e)
        result["status"] = "error"
        log.error(f"Error saving config: {e}")
        return json.dumps(result, ensure_ascii=False)
    

def remote_delete_file(db_config: str|dict) -> dict:
    if type(db_config) == str:
        db_config = json.loads(db_config)
    file_id = db_config['fileId']
    if file_id is None or file_id =="":
        log.error("fileId 不能为空")
        return json.dumps({
            "status": "error",
            "error_info": "fileId 不能为空",
            "result_info": None
        })
    if not check_usename_password(all_config['user_name'], all_config['password']):
        log.error(f"用户名或密码错误")
        return json.dumps({
            "status": "error",
            "error_info": "用户名或密码错误",
            "result_info": None
        })
    # Check if database exists
    target_db_path = os.path.join(all_config['db_path'], f"{all_config['user_name']}.db")
    if not os.path.exists(target_db_path):
        log.error(f"数据库 {target_db_path} 不存在")
        return json.dumps({
            "status": "error",
            "error_info": f"数据库 {target_db_path} 不存在",
            "result_info": None
        }, ensure_ascii=False)    
    try:
        conn = sqlite3.connect(os.path.join(all_config['db_path'], f"{all_config['user_name']}.db"))
        remote_file_manager = RemoteFileBManager(conn)
        delete_result = remote_file_manager.delete_file(file_id)
        
        data = {
            "collection_code": REMOTE_DB,
            "file_id": file_id
        }
        response = requests.post(f"{remote_base_url}/delete_milvus_file", json=data)
        response_json = response.json()
        log.info(response_json)
        if delete_result and response_json['code'] == 200:
            result = {
                "status": "success",
                "error_info": None,
                "result_info": file_id
            }
            return json.dumps(result, ensure_ascii=False)
        else:
            result = {
                "status": "error",
                "error_info": f"删除远程文件 {file_id} 失败, delete_result: {delete_result}, response_json: {response_json}",
                "result_info": file_id
            }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        log.error(f"Error deleting file: {e}")
        return json.dumps({"status": "error", "error_info": str(e), "result_info":None}, ensure_ascii=False)


if __name__ == "__main__":
    pass
    # 测试上传文件
    all_config = {
        # file_path, user_name, db_path
        "file_path": r"D:\desktop\work\localpy\test_file\test.pdf",
        "user_name": "admin",
        "db_path": r"D:\desktop\work\localpy\db_date",
        "password": "123456"
    }
    result = remote_process_file(json.dumps(all_config,ensure_ascii=False))
    print(result)
    file_id = json.loads(result)['result_info']['docId']
    print(file_id)
    
    
    all_config = {
        # text, user_name, db_path, agentId 
        "text": "六盘水市开发投资有限公司财务状况",
        "user_name": "admin",
        "db_path": r"D:\desktop\work\localpy\db_date",
        "agentId": 780
    }
    # 测试相似度查询
    query_result = remote_similarity_query(json.dumps(all_config,ensure_ascii=False))
    for res in json.loads(query_result)['result_info']:
        print(res)
    
    # 测试删除文件
    all_config = {
        # fileId, user_name, db_path
        "fileId": file_id,
        "user_name": "admin",
        "password": "123456",
        "db_path": r"D:\desktop\work\localpy\db_date", 
    }
    result = remote_delete_file(json.dumps(all_config,ensure_ascii=False))
    print(result)
    
    
    # 测试保存当前配置
    all_config = {
        # user_name, db_path
        "user_name": "admin",
        "password": "123456",
        "db_path": r"D:\desktop\work\localpy\db_date"
    }
    result = remote_save_config(json.dumps(all_config,ensure_ascii=False))
    print(result)