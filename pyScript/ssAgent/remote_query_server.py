import sqlite3
import json
import struct # type: ignore
import requests
import zipfile
import os
from src.logs import get_logger
get_logger()
import logging as log
from configs.configs import REMOTE_SERVER_URL, REMOTE_API_URL, REMOTE_QUERY_URL
from src.database.database_manager import EmbeddingStorage
from share_service import send_request


# 新增装饰器在文件顶部
def db_operation(op_type: str, entity: str, require_fields: list = None):
    """通用数据库操作装饰器
    Args:
        op_type: 操作类型 (query|add|update|delete)
        entity: 操作实体 (server|model|agent|knowledge|document)
        require_fields: 必填字段列表
    """
    def decorator(func):
        def wrapper(db_config):
            try:
                # 统一处理输入配置
                if isinstance(db_config, str):
                    db_config = json.loads(db_config)
                
                # 校验必填字段
                if require_fields:
                    missing = [field for field in require_fields if field not in db_config]
                    if missing:
                        raise ValueError(f"缺少必填字段: {missing}")
                
                # 根据操作类型调用不同方法
                if op_type == "query":
                    response = send_request("query", entity, db_config)
                elif op_type == "add":
                    response = send_request("add", entity, db_config)
                elif op_type == "update":
                    response = send_request("update", entity, db_config)
                elif op_type == "delete":
                    response = send_request("delete", entity, db_config)
                else:
                    raise ValueError(f"无效的操作类型: {op_type}")

                if response.status_code == 200:
                    return json.dumps(response.json(), ensure_ascii=False)

            except Exception as e:
                return json.dumps({
                    "status": "error",
                    "error_info": str(e),
                    "result_info": None
                }, ensure_ascii=False)
        return wrapper
    return decorator

@db_operation(op_type="query", entity="agent")
def remote_query_agent(db_config): pass

@db_operation(op_type="query", entity="knowledge")
def remote_query_knowledge(db_config): pass

@db_operation(op_type="query", entity="document", require_fields=["knowledgeId", "docId"])
def remote_query_document(db_config): pass

@db_operation(op_type="query", entity="embedding", require_fields=["knowledgeId", "docId"])
def remote_query_embedding(db_config): pass

@db_operation(op_type="add", entity="agent", require_fields=["agentName", "prompt", "createBy"])
def remote_add_agent(db_config): pass

@db_operation(op_type="add", entity="knowledge", require_fields=["knowledgeName"])
def remote_add_knowledge(db_config): pass

@db_operation(op_type="add", entity="document", require_fields=["knowledgeId", "docId", "fileName", "fileType", "fileHash", "segmentNum"])
def remote_add_document(db_config): pass

@db_operation(op_type="delete", entity="agent", require_fields=["agentId"])
def remote_delete_agent(db_config): pass
@db_operation(op_type="delete", entity="knowledge", require_fields=["knowledgeId"])
def remote_delete_knowledge(db_config): pass
@db_operation(op_type="delete", entity="document", require_fields=["knowledgeId", "docId"])
def remote_delete_document(db_config): pass

@db_operation(op_type="update", entity="agent", require_fields=["agentId"])
def remote_update_agent(db_config): pass
@db_operation(op_type="update", entity="knowledge", require_fields=["knowledgeId"])
def remote_update_knowledge(db_config): pass

def remote_query_similarity(db_config: str|dict) -> dict:
    """查询远程知识库的相似度"""
    try:
        if type(db_config) == str:
            db_config = json.loads(db_config)
        db_config['agentId'] = db_config['shareAgentId']
        if db_config['text'] == "xxx":
            query_config = {
                "text": db_config['text'],
                "agentId": db_config['agentId'],
            }
            result = {
                "status": "success",
                "error_info": None,
                "result_info": f'curl -X POST {REMOTE_QUERY_URL} -H "Content-Type: application/json" -d \'{json.dumps(query_config, ensure_ascii=False)}\''

            }
            return json.dumps(result)
        response = requests.post(REMOTE_QUERY_URL, json=db_config)
        if response.status_code == 200:
            log.info(f"查询远程知识库成功: {response.json()}")
        else:
            log.error(f"查询远程知识库失败: {response.text}")
        if db_config['text'] == "xxx":
            temp_res = response.json()
            temp_res['result_info'] = f"curl -X POST {REMOTE_QUERY_URL} -H 'Content-Type: application/json' -d '{json.dumps(db_config, ensure_ascii=False)}'"
            return json.dumps(temp_res, ensure_ascii=False)
        else:
            return json.dumps(response.json(), ensure_ascii=False)
    except Exception as e:
        log.error(f"查询远程知识库失败: {str(e)}", exc_info=True)
        return json.dumps({"status": "error", "error_info": str(e)}, ensure_ascii=False)
    

# if __name__ == "__main__":
#     # 测试用例
#     # 1. 查询agent
#     agent_config = {
#         "agentId": "all",
#     }
#     result = remote_query_agent(agent_config)
#     print(type(result))
#     result = json.loads(result)
#     print(result['status'])
#     print(result['error_info'])
#     # print(result['result_info'])
#     for ind, res in enumerate(result['result_info']):
#         print(f"{ind}: {res}")
        
#     agent_config = {
#         "agentId": 2,
#         "createBy": "testuser"
#     }
#     result = remote_query_agent(agent_config)
#     print(result)
#     result = json.loads(result)
#     print(result['status'])
#     print(result['error_info'])
#     print(result['result_info'])
    
#     print("#######################################")
#     # 2. 查询knowledge
#     knowledge_config = {
#         "knowledgeId": "all",
#     }
#     result = remote_query_knowledge(knowledge_config)
#     print(type(result))
#     result = json.loads(result)
#     print(result['status'])
#     print(result['error_info'])
#     for ind, res in enumerate(result['result_info']):
#         print(f"{ind}: {res}")
        
#     query_config = {
#         # 'agentId': share_agent_id,
#         'shareAgentId': "100000002",
#         'text': "qb最优报价里面如何调整经纪商顺序",
#         'createBy': "testuser",
#     }    
#     query_res = remote_query_similarity(json.dumps(query_config, ensure_ascii=False))
#     print("######################\n")
#     if query_res['status'] == "error":
#         print(query_res['error_info'])
#     else:
#         for res in query_res['result_info']:
#             print(res)