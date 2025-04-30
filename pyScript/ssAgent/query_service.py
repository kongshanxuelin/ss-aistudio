import json
import os
from pathlib import Path
import struct # type: ignore
from share_service import send_request
from src.logs import get_logger
get_logger()
import logging as log

from src.database.database_manager import EmbeddingStorage
from src.api.embedding_client import EmbeddingClient

def similarity_query(
    all_config: str|dict
) -> str:
    import numpy as np
    if type(all_config) == str:
        all_config = json.loads(all_config)
    text = all_config['text']
    model_id = all_config.get('modelId', None)
    storage = EmbeddingStorage(all_config['user_name'], all_config['db_path'])
    try:
        ## AgentId 获取模型信息
        agent_info = storage.process_manager("agent", "get", agentId=all_config['agentId'])
        if agent_info is None:
            log.error(f"AgentId: {all_config['agentId']} 不存在")
            output_result = {
                "status": "error",
                "error_info": f"AgentId: {all_config['agentId']} 不存在",
                "result_info": None 
            }
            return json.dumps(output_result, ensure_ascii=False)
        elif agent_info['knowledgeIdList'] is None or agent_info['knowledgeIdList']=="":
            output_result = {
                "status": "error",
                "error_info": "请先配置知识库",
                "result_info": None
            }
            return json.dumps(output_result, ensure_ascii=False)
        # 获取知识库信息
        knowledge_id_list = [int(kid) for kid in agent_info['knowledgeIdList'].split(",")]
        if model_id is None:
            # 选择第一个作为model_id
            model_info = storage.process_manager("knowledge", "get", knowledgeId=knowledge_id_list[0])
            model_id = model_info['embeddingModelId']
            
        # 获取模型配置
        cursor = storage.model_manager.execute("""
            select t1.modelName, t2.serverBaseUrl, t2.serverApiKey FROM models t1
            left join server t2 on t1.serverId = t2.serverId where t1.modelId =?
        """, (model_id,))
        api_config = dict(cursor.fetchone())
        api_config['serverEmbeddingUrl'] = api_config['serverBaseUrl']+'/v1/embeddings'
        if api_config['serverBaseUrl']=='https://api.siliconflow.cn' and not api_config['serverApiKey']:
            log.warning("使用默认模型的ApiKey")
            api_config['serverApiKey'] = 'sk-lcmgoofhdtzibdjvizbzzuyuvmwnuzavvdrabokwstieedal'
        if api_config['modelName'].lower() != "ollama" and api_config['serverApiKey'] =='':
            output_result = {
                "status": "error",
                "error_info": "请先配置模型的ApiKey",
                "result_info": None
            }
            return json.dumps(output_result, ensure_ascii=False)
        log.info(f"get model_id: {model_id}, knowledge_id_list: {knowledge_id_list}")
        
        embedding_client = EmbeddingClient(api_config['serverEmbeddingUrl'], api_config['serverApiKey'], api_config['modelName'])
        # Get the embedding for the input text
        query_embedding = embedding_client.get_embedding(text)
        embedding_length = len(query_embedding)

        # 获取所有embeddingss
        cursor = storage.knowledge_manager.execute("""
                SELECT t2.fileName, t1.docId, t1.textContent, t1.embeddingData, t2.cachePath
                FROM embeddings t1
                LEFT JOIN documents t2 on t1.docId = t2.docId WHERE t1.knowledgeId in ({knowledgeIds})
            """.format(knowledgeIds=','.join([f"{d}" for d in knowledge_id_list])))
        # 使用struct解包二进制数据
        all_embeddings_data = [[row[0],row[1],row[2],list(struct.unpack(f'{embedding_length}f', row['embeddingData'])),row[4]] 
                               for row in cursor.fetchall()]
        if all_embeddings_data == []:
            log.info(f"❌ 数据库 {knowledge_id_list} 未找到相关知识")
            return []
        log.info(f"get all_embeddings_data length: {len(all_embeddings_data)}")
        all_file_name = [d[0] for d in all_embeddings_data]
        all_doc_id = [d[1] for d in all_embeddings_data]
        all_content = [d[2] for d in all_embeddings_data]
        all_embeddings = [d[3] for d in all_embeddings_data]
        all_file_path = [d[4] for d in all_embeddings_data]
        
        # 矩阵相乘
        query_embedding = np.array(query_embedding).reshape(1, -1)
        all_embeddings = np.array(all_embeddings)
        similarities = np.dot(query_embedding, all_embeddings.T)
        
        # 找到大于threshold最相似的max_count个向量，按照从大到小相似度排序, 同时保留doc_id和content，最终结果用json列表格式返回
        sorted_indices = np.argsort(similarities[0])[::-1]  # 降序排列索引
        # 获取知识库信息
        cursor = storage.knowledge_manager.execute("""
            SELECT queryThreshold, maxCount FROM knowledge WHERE knowledgeId in ({knowledgeIds})
            """.format(knowledgeIds=','.join([f"{d}" for d in knowledge_id_list])))
        knowledge_data = cursor.fetchall()
        threshold = knowledge_data[0][0]
        max_count = knowledge_data[0][1]
        qualified_indices = [i for i in sorted_indices if similarities[0][i] >= threshold][:max_count]
        log.info(f"threshold is {threshold}, max_count is {max_count}, get qualified_indices length: {len(qualified_indices)}")
        for idx in qualified_indices:
            temp_content = all_content[idx]
            temp_cache_path = Path(os.path.join(os.path.dirname(all_file_path[idx]), "images")).as_posix()
            if "<cache_images_path>" in temp_content:
                # log.info(f"find <cache_images_path> in content, replace it to {temp_cache_path}")
                temp_content = temp_content.replace("<cache_images_path>", temp_cache_path)
            all_content[idx] = temp_content
        # 构建包含完整信息的结果列表
        results = []
        for idx in qualified_indices:
            results.append({
                "docId": all_doc_id[idx],
                "fileName": all_file_name[idx],
                "content": all_content[idx],
                "cachePath": all_file_path[idx],
                "similarity": float(similarities[0][idx]),
            })
        output_result = {
            "status": "success",
            "error_info": None,
            "result_info": results
        }
        log.info(json.dumps(output_result, ensure_ascii=False))
        return json.dumps(output_result, ensure_ascii=False)
    except Exception as e:
        log.error(f"Error performing similarity query: {e}")
        return json.dumps({
            "status": "error",
            "error_info": str(e),
            "result_info": None
        }, ensure_ascii=False)
    finally:
        storage.close()

# query
def query_server(db_config):
    try:
        if type(db_config) == str:
            db_config = json.loads(db_config)
        storage = EmbeddingStorage(db_config['user_name'], db_config['db_path'])
        result = storage.process_manager("server", "get", serverId=db_config.get("serverId", "all"))
        return json.dumps({"status": "success", "error_info": None, "result_info":result}, ensure_ascii=False)
    except Exception as e:
        log.error(f"Error performing query server: {e}")
        return json.dumps({"status": "error", "error_info": str(e), "result_info":None}, ensure_ascii=False)

def query_model(db_config):
    try:
        if type(db_config) == str:
            db_config = json.loads(db_config)
        storage = EmbeddingStorage(db_config['user_name'], db_config['db_path'])
        result = storage.process_manager("model", "get", serverId=db_config["serverId"],modelId=db_config.get("modelId", "all"))
        return json.dumps({"status": "success", "error_info": None, "result_info":result}, ensure_ascii=False)
    except Exception as e:
        log.error(f"Error performing query model: {e}")
        return json.dumps({"status": "error", "error_info": str(e), "result_info":None}, ensure_ascii=False)

def query_default_model(db_config):
    try:
        if type(db_config) == str:
            db_config = json.loads(db_config)
        storage = EmbeddingStorage(db_config['user_name'], db_config['db_path'])
        # 获取目前的默认模型，包括问答的默认模型(embeddingModel=0)，向量化的默认模型(embeddingModel=1)
        result = storage.process_manager("model", "get_default", embeddingModel=db_config["embeddingModel"])
        return json.dumps({"status": "success", "error_info": None, "result_info":result}, ensure_ascii=False)
    except Exception as e:
        log.error(f"Error performing query default model: {e}") 
        return json.dumps({"status": "error", "error_info": str(e), "result_info":None}, ensure_ascii=False)

def query_agent(db_config):
    try:
        if type(db_config) == str:
            db_config = json.loads(db_config)
        storage = EmbeddingStorage(db_config['user_name'], db_config['db_path'])
        agentId_info = db_config.get("agentId")
        if agentId_info == "remote":
            response = send_request("query", "agent", {"agentId": "all", "createBy": "all"})
            if response.status_code == 200:
                return json.dumps(response.json(), ensure_ascii=False)
            else:
                log.error(f"Error performing query remote agent: {response.txt}")
                return json.dumps({"status": "error", "error_info": "query remote agent error", "result_info":None}, ensure_ascii=False)
        elif agentId_info == "local":
            result = storage.process_manager("agent", "get", agentId=db_config.get("agentId", "all"))
            return json.dumps({"status": "success", "error_info": None, "result_info":result}, ensure_ascii=False)
        else:
            result = storage.process_manager("agent", "get", agentId=db_config.get("agentId", "all"))
            try:
                response = send_request("query", "agent", {"agentId": "all", "createBy": "all"})
                log.info(f"query remote agent success:{response.text}")
                if response.status_code == 200:
                    remote_result = response.json()["result_info"]
                    result.extend(remote_result)
                else:
                    log.error(f"Error performing query remote agent: {response.txt}")
                    return json.dumps({"status": "error", "error_info": "query remote agent error", "result_info":None}, ensure_ascii=False)
            except Exception as e:
                log.error(f"Error performing query remote agent: {e}")
                
            return json.dumps({"status": "success", "error_info": None, "result_info":result}, ensure_ascii=False)
    except Exception as e:
        log.error(f"Error performing query agent: {e}")
        return json.dumps({"status": "error", "error_info": str(e), "result_info":None}, ensure_ascii=False)
    
def query_knowledge(db_config):
    try:
        if type(db_config) == str:
            db_config = json.loads(db_config)
        storage = EmbeddingStorage(db_config['user_name'], db_config['db_path'])
        result = storage.process_manager("knowledge", "get", knowledgeId=db_config.get("knowledgeId", "all"))
        return json.dumps({"status": "success", "error_info": None, "result_info":result}, ensure_ascii=False)
    except Exception as e:
        log.error(f"Error performing query knowledge: {e}")
        return json.dumps({"status": "error", "error_info": str(e), "result_info":None}, ensure_ascii=False)

def query_document(db_config):
    try:
        if type(db_config) == str:
            db_config = json.loads(db_config)
        storage = EmbeddingStorage(db_config['user_name'], db_config['db_path'])
        result = storage.process_manager("document", "get", knowledgeId=db_config["knowledgeId"], docId=db_config.get("docId", "all"))
        return json.dumps({"status": "success", "error_info": None, "result_info":result}, ensure_ascii=False)
    except Exception as e:
        log.error(f"Error performing query document: {e}")
        return json.dumps({"status": "error", "error_info": str(e), "result_info":None}, ensure_ascii=False)
    
# add
def add_server(db_config):
    try:
        if type(db_config) == str:
            db_config = json.loads(db_config)
        storage = EmbeddingStorage(db_config['user_name'], db_config['db_path'])
        # require:serverName, serverBaseUrl 
        # opinion:serverApiKey
        result = storage.process_manager("server", "add", **db_config)  
        return json.dumps({"status": "success", "error_info": None, "result_info":result}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "error_info": str(e), "result_info":None}, ensure_ascii=False)

def add_model(db_config):
    try:
        if type(db_config) == str:
            db_config = json.loads(db_config)
        storage = EmbeddingStorage(db_config['user_name'], db_config['db_path'])
        # require:modelName, serverId
        # opinion:defaultModel, embeddingModel, maxTokens
        result = storage.process_manager("model", "add", **db_config)
        return json.dumps({"status": "success", "error_info": None, "result_info":result}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "error_info": str(e), "result_info":None}, ensure_ascii=False)

def add_agent(db_config):
    try:
        if type(db_config) == str:
            db_config = json.loads(db_config)
        storage = EmbeddingStorage(db_config['user_name'], db_config['db_path'])
        # require:agentName, prompt
        # opinion:description, isLocal, knowledgeIdList, groupName
        result = storage.process_manager("agent", "add", **db_config)
        return json.dumps({"status": "success", "error_info": None, "result_info":result}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "error_info": str(e), "result_info":None}, ensure_ascii=False)

def add_knowledge(db_config):
    try:
        if type(db_config) == str:
            db_config = json.loads(db_config)
        storage = EmbeddingStorage(db_config['user_name'], db_config['db_path'])
        # require:knowledgeName, embeddingModelId
        # opinion:chunkSize, chunkOverlap, queryThreshold, maxCount
        result = storage.process_manager("knowledge", "add", **db_config)
        os.makedirs(os.path.join(db_config['db_path'], "tmpFile", str(result['knowledgeId'])), exist_ok=True)
        return json.dumps({"status": "success", "error_info": None, "result_info":result}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "error_info": str(e), "result_info":None}, ensure_ascii=False)

# 不要单独调用
def add_document(db_config):
    try:
        if type(db_config) == str:
            db_config = json.loads(db_config)
        storage = EmbeddingStorage(db_config['user_name'], db_config['db_path'])
        # require:knowledgeId, docId, fileName, fileType, fileHash, segmentNum
        # opinion:filePath, fileSize, fileStatus, createTime, updateTime
        result = storage.process_manager("document", "add", **db_config)
        return json.dumps({"status": "success", "error_info": None, "result_info":result}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "error_info": str(e), "result_info":None}, ensure_ascii=False)

# update
def update_server(db_config):
    try:
        if type(db_config) == str:
            db_config = json.loads(db_config)
        storage = EmbeddingStorage(db_config['user_name'], db_config['db_path'])
        # update paraments: serverName, serverBaseUrl, serverChatUrl, serverApiKey
        result = storage.process_manager("server", "update", **db_config)
        return json.dumps({"status": "success", "error_info": None, "result_info":result}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "error_info": str(e), "result_info":None}, ensure_ascii=False)

# 模型只能更新是否是默认模型，其它配置无法修改
def update_default_model(db_config):
    try:
        if type(db_config) == str:
            db_config = json.loads(db_config)
        storage = EmbeddingStorage(db_config['user_name'], db_config['db_path'])
        # 将对应modelId设置为默认模型
        result = storage.process_manager("model", "update_default", modelId=db_config["modelId"])
        return json.dumps({"status": "success", "error_info": None, "result_info":result}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "error_info": str(e), "result_info":None}, ensure_ascii=False)

def update_agent(db_config):
    try:
        if type(db_config) == str:
            db_config = json.loads(db_config)
        storage = EmbeddingStorage(db_config['user_name'], db_config['db_path'])
        # update paraments: agentName, prompt, description, knowledgeIdList, groupName
        result = storage.process_manager("agent", "update", **db_config)
        return json.dumps({"status": "success", "error_info": None, "result_info":result}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "error_info": str(e), "result_info":None}, ensure_ascii=False)

def update_knowledge(db_config):
    try:
        if type(db_config) == str:
            db_config = json.loads(db_config)
        storage = EmbeddingStorage(db_config['user_name'], db_config['db_path'])
        # update paraments: knowledgeName, embeddingModelId, chunkSize, chunkOverlap, queryThreshold, maxCount
        result = storage.process_manager("knowledge", "update", **db_config)
        return json.dumps({"status": "success", "error_info": None, "result_info":result}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "error_info": str(e), "result_info":None}, ensure_ascii=False)

# delete
def delete_server(db_config):
    try:
        if type(db_config) == str:
            db_config = json.loads(db_config)
        storage = EmbeddingStorage(db_config['user_name'], db_config['db_path'])
        result = storage.process_manager("server", "delete", serverId=db_config["serverId"])
        return json.dumps({"status": "success", "error_info": None, "result_info":result}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "error_info": str(e), "result_info":None}, ensure_ascii=False)

def delete_model(db_config):
    try:
        if type(db_config) == str:
            db_config = json.loads(db_config)
        storage = EmbeddingStorage(db_config['user_name'], db_config['db_path'])
        result = storage.process_manager("model", "delete", modelId=db_config["modelId"])
        return json.dumps({"status": "success", "error_info": None, "result_info":result}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "error_info": str(e), "result_info":None}, ensure_ascii=False)

def delete_agent(db_config):
    try:
        if type(db_config) == str:
            db_config = json.loads(db_config)
        storage = EmbeddingStorage(db_config['user_name'], db_config['db_path'])
        result = storage.process_manager("agent", "delete", agentId=db_config["agentId"])
        return json.dumps({"status": "success", "error_info": None, "result_info":result}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "error_info": str(e), "result_info":None}, ensure_ascii=False)

def delete_knowledge(db_config):
    try:
        if type(db_config) == str:
            db_config = json.loads(db_config)
        storage = EmbeddingStorage(db_config['user_name'], db_config['db_path'])
        result = storage.process_manager("knowledge", "delete", knowledgeId=db_config["knowledgeId"])
        return json.dumps({"status": "success", "error_info": None, "result_info":result}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "error_info": str(e), "result_info":None}, ensure_ascii=False)

def delete_document(db_config):
    try:
        if type(db_config) == str:
            db_config = json.loads(db_config)
        storage = EmbeddingStorage(db_config['user_name'], db_config['db_path'])
        result = storage.process_manager("document", "delete", knowledgeId=db_config["knowledgeId"], docId=db_config["docId"])
        return json.dumps({"status": "success", "error_info": None, "result_info":result}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "error_info": str(e), "result_info":None}, ensure_ascii=False)

def query_embedding(db_config):
    try:
        if type(db_config) == str:
            db_config = json.loads(db_config)
        storage = EmbeddingStorage(db_config['user_name'], db_config['db_path'])
        result = storage.process_manager("document", "get", knowledgeId=db_config["knowledgeId"], docId=db_config["docId"])
        return json.dumps({"status": "success", "error_info": None, "result_info":result}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "error_info": str(e), "result_info":None}, ensure_ascii=False)
    
def add_session(db_config):
    try:
        if type(db_config) == str:
            db_config = json.loads(db_config)
        storage = EmbeddingStorage(db_config['user_name'], db_config['db_path'])
        result = storage.process_manager("session", "add", **db_config)
        return json.dumps({"status": "success", "error_info": None, "result_info":result}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "error_info": str(e), "result_info":None}, ensure_ascii=False)
    
def query_session(db_config):
    try:
        if type(db_config) == str:
            db_config = json.loads(db_config)
        storage = EmbeddingStorage(db_config['user_name'], db_config['db_path'])
        result = storage.process_manager("session", "get", sessionId=db_config.get("sessionId", "all"))
        return json.dumps({"status": "success", "error_info": None, "result_info":result}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "error_info": str(e), "result_info":None}, ensure_ascii=False)

def delete_session(db_config):
    try:
        if type(db_config) == str:
            db_config = json.loads(db_config)
        storage = EmbeddingStorage(db_config['user_name'], db_config['db_path'])
        # 先删除session中的所有message
        clear_result = clear_history(db_config)
        result = storage.process_manager("session", "delete", sessionId=db_config["sessionId"])
        return json.dumps({"status": "success", "error_info": None, "result_info":result}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "error_info": str(e), "result_info":None}, ensure_ascii=False)
    
def update_session(db_config):
    try:
        if type(db_config) == str:
            db_config = json.loads(db_config)
        storage = EmbeddingStorage(db_config['user_name'], db_config['db_path'])
        result = storage.process_manager("session", "update", **db_config)
        return json.dumps({"status": "success", "error_info": None, "result_info":result}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "error_info": str(e), "result_info":None}, ensure_ascii=False)

def query_history(db_config):
    try:
        if type(db_config) == str:
            db_config = json.loads(db_config)
        storage = EmbeddingStorage(db_config['user_name'], db_config['db_path'])
        # require: sessionId, historyId, 
        # opinion: show_count, last_time
        result = storage.process_manager("history", "get", **db_config)
        return json.dumps({"status": "success", "error_info": None, "result_info":result}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "error_info": str(e), "result_info":None}, ensure_ascii=False)

def add_history(db_config):
    try:
        if type(db_config) == str:
            db_config = json.loads(db_config)
        storage = EmbeddingStorage(db_config['user_name'], db_config['db_path'])
        result = storage.process_manager("history", "add", **db_config)
        return json.dumps({"status": "success", "error_info": None, "result_info":result}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "error_info": str(e), "result_info":None}, ensure_ascii=False)

def delete_history(db_config):
    try:
        if type(db_config) == str:
            db_config = json.loads(db_config)
        storage = EmbeddingStorage(db_config['user_name'], db_config['db_path'])
        result = storage.process_manager("history", "delete", historyId=db_config["historyId"])
        return json.dumps({"status": "success", "error_info": None, "result_info":result}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "error_info": str(e), "result_info":None}, ensure_ascii=False)

def clear_history(db_config):
    try:
        if type(db_config) == str:
            db_config = json.loads(db_config)
        storage = EmbeddingStorage(db_config['user_name'], db_config['db_path'])
        result = storage.process_manager("history", "clear", sessionId=db_config["sessionId"])
        return json.dumps({"status": "success", "error_info": None, "result_info":result}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "error_info": str(e), "result_info":None}, ensure_ascii=False)

def add_mcp(db_config):
    try:
        if type(db_config) == str:
            db_config = json.loads(db_config)
        storage = EmbeddingStorage(db_config['user_name'], db_config['db_path'])
        result = storage.process_manager("mcp", "add", **db_config)
        return json.dumps({"status": "success", "error_info": None, "result_info":result}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "error_info": str(e), "result_info":None}, ensure_ascii=False)

def update_mcp(db_config):
    try:
        if type(db_config) == str:
            db_config = json.loads(db_config)
        storage = EmbeddingStorage(db_config['user_name'], db_config['db_path'])
        result = storage.process_manager("mcp", "update", **db_config)
        return json.dumps({"status": "success", "error_info": None, "result_info":result}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "error_info": str(e), "result_info":None}, ensure_ascii=False)

def delete_mcp(db_config):
    try:
        if type(db_config) == str:
            db_config = json.loads(db_config)
        storage = EmbeddingStorage(db_config['user_name'], db_config['db_path'])
        result = storage.process_manager("mcp", "delete", mcpUid=db_config["mcpUid"])
        return json.dumps({"status": "success", "error_info": None, "result_info":result}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "error_info": str(e), "result_info":None}, ensure_ascii=False)

def query_mcp(db_config):
    try:
        if type(db_config) == str:
            db_config = json.loads(db_config)
        storage = EmbeddingStorage(db_config['user_name'], db_config['db_path'])
        result = storage.process_manager("mcp", "get", mcpUid=db_config.get("mcpUid", "all"))
        return json.dumps({"status": "success", "error_info": None, "result_info":result}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "error_info": str(e), "result_info":None}, ensure_ascii=False)

def json_update_mcp(db_config):
    try:
        if type(db_config) == str:
            db_config = json.loads(db_config)
        storage = EmbeddingStorage(db_config['user_name'], db_config['db_path'])
        result = storage.process_manager("mcp", "update_form_json", file_path=db_config["file_path"])
        return json.dumps({"status": "success", "error_info": None, "result_info":result}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "error_info": str(e), "result_info":None}, ensure_ascii=False)

def update_json_mcp(db_config):
    try:
        if type(db_config) == str:
            db_config = json.loads(db_config)
        storage = EmbeddingStorage(db_config['user_name'], db_config['db_path'])
        result = storage.process_manager("mcp", "update_json_file", file_path=db_config["file_path"])
        return json.dumps({"status": "success", "error_info": None, "result_info":result}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "error_info": str(e), "result_info":None}, ensure_ascii=False)

if __name__ == "__main__":
    # 测试相似度查询
    import time # type: ignore
    # import os
    # base_dir = os.path.abspath(os.path.dirname(__file__))
    # config = {
    #     'user_name': 'testuser',
    #     'db_path': os.path.join(base_dir, "./db_date")
    # }

    # print("测试json update mcp")
    # config['file_path'] = r"D:\desktop\work\localpy\MCP_server\weather\mcp_config.json"
    # json_update_result = json_update_mcp(json.dumps(config, ensure_ascii=False))
    # print("json_update_result:", json_update_result)
    # query_result = query_mcp(json.dumps(config, ensure_ascii=False))
    # print("query_result:", query_result)
    # time.sleep(1)
    
    # print("测试json update mcp")
    # config['file_path'] = r"D:\desktop\work\localpy\MCP_server\weather\mcp_config_new.json"
    # json_update_result = json_update_mcp(json.dumps(config, ensure_ascii=False))
    # print("json_update_result:", json_update_result)
    # query_result = query_mcp(json.dumps(config, ensure_ascii=False))
    # print("query_result:", query_result)
    # time.sleep(1)
    
    # print("测试add mcp")
    # add_result = add_mcp(json.dumps(config, ensure_ascii=False))
    # print("add_result:", add_result)
    # mcp_uid = json.loads(add_result)['result_info']['mcpUid']
    
    # config['mcpUid'] = mcp_uid
    # print("测试query mcp")
    # query_result = query_mcp(json.dumps(config, ensure_ascii=False))
    # print("query_result:", query_result)
    
    # print("测试update mcp")
    # config['mcpName'] = "test_mcp"
    # update_result = update_mcp(json.dumps(config, ensure_ascii=False))
    # print("update_result:", update_result)
    
    # del config['mcpName']
    # print("测试delete mcp")
    # delete_result = delete_mcp(json.dumps(config, ensure_ascii=False))
    # print("delete_result:", delete_result)
    # time.sleep(1)    
    

    # print("测试update json mcp")
    # config['file_path'] = r"D:\desktop\work\localpy\MCP_server\weather\mcp_config_out.json"
    # update_json_result = update_json_mcp(json.dumps(config, ensure_ascii=False))
    # print("update_json_result:", update_json_result)
    # query_result = query_mcp(json.dumps(config, ensure_ascii=False))
    # print("query_result:", query_result)
    # time.sleep(1)
    
        
    # text = "测试"
    # # api_config = {
    # #     'serverEmbeddingUrl': 'https://api.siliconflow.cn/v1/embeddings',
    # #     'serverBaseUrl': 'https://api.siliconflow.cn',
    # #     'serverApiKey': 'sk-lcmgoofhdtzibdjvizbzzuyuvmwnuzavvdrabokwstieedal',
    # #     'modelName': 'BAAI/bge-m3'
    # # }

    # start_3_time = time.time()
    # log.info("\n3. 测试相似度查询...")
    # test_query = "深度学习 大模型"
    # config_3 = {
    #     'user_name': 'testuser',
    #     'db_path': os.path.join(base_dir, "./db_date"),
    #     "text": test_query,
    #     # "modelId": 1,
    #     "agentId": 2
    # }
    # results = similarity_query(
    #     json.dumps(config_3, ensure_ascii=False),
    # )
    # if type(results) == str:
    #     results = json.loads(results)
    # if results['result_info'] is not None:
    #     log.info(f"use time: {time.time() - start_3_time:.2f}s, 找到 {len(results['result_info'])} 条相关结果：")
    #     for i, res in enumerate(results['result_info'][:]):
    #         log.info(f"✅ {i+1}. 相似度 {res['similarity']:.2f} | docId: {res['docId']} | fileName: {res['fileName']} | 内容片段: {res['content'][:60]}...\n")
    # else:
    #     log.info(f"get {results}")
    # # 测试查询
    # db_config = {
    #     'user_name': 'testuser',
    #     'db_path': os.path.join(base_dir, "./db_date"),
    #     'knowledgeId': 1,
    #     'chunkSize': 256,
    #     'chunkOverlap': 32,
    #     'serverId': 1,
    #     'embeddingModel': 1,
    # }
    # log.info("测试查询")
    # log.info("############################\n")
    # log.info(query_server(json.dumps(db_config, ensure_ascii=False)))
    # log.info("############################\n")
    # log.info(query_model(json.dumps(db_config, ensure_ascii=False)))
    # log.info("############################\n")
    # log.info(query_default_model(json.dumps(db_config, ensure_ascii=False)))
    # log.info("############################\n")
    # log.info(query_agent(json.dumps(db_config, ensure_ascii=False))[:150])
    # log.info("############################\n")
    # log.info(query_knowledge(json.dumps(db_config, ensure_ascii=False)))
    # log.info("############################\n")
    # log.info(query_document(json.dumps(db_config, ensure_ascii=False)))
    
    
    