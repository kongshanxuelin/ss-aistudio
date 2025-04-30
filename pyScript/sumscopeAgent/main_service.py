from datetime import datetime # type: ignore
import os
import hashlib # type: ignore
import uuid # type: ignore
import json

import shutil # type: ignore
from query_service import similarity_query
from src.logs import get_logger
get_logger()
import logging as log
import PyBridge

from src.database.database_manager import EmbeddingStorage
from src.api.embedding_client import EmbeddingClient
from src.processors.file_processor import LangChainFileProcessor
process_type = ["txt", "pdf", "html", "csv", "md", "docx", "pptx", "xlsx", "epub", "json"]

def create_database(all_config: str|dict) -> bool:
    if type(all_config) == str:
        all_config = json.loads(all_config)
    user_name = all_config['user_name']
    db_path = all_config['db_path']
    db_emb_len = all_config['emb_len']
    os.makedirs(db_path, exist_ok=True)  
    storage = EmbeddingStorage(user_name, db_path, db_emb_len)
    try:
        # 修改数据库名称为固定值
        storage._create_tables()
        result = {
            "status": "success",
            "error_info": None,
            "result_info": "create success"
        }
        log.info("数据库创建成功: user=%s, path=%s", user_name, db_path)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        log.error("数据库创建失败: %s", str(e), exc_info=True)
        result = {
            "status": "failed",
            "error_info": str(e),
            "result_info": "create_database failed"
        }
        return json.dumps(result, ensure_ascii=False)
    finally:
        storage.close()


def process_file(all_config: str|dict) -> any:
    if type(all_config) == str:
        all_config = json.loads(all_config)
    file_path_list = all_config['file_path']
    if type(file_path_list) == str:
        file_path_list = [file_path_list]
    knowledge_id = all_config['knowledgeId']
    model_id = all_config.get('modelId', None)
    parent_id = None
    # Check if database exists
    abs_db_path = os.path.join(all_config['db_path'], f"{all_config['user_name']}.db")
    if not os.path.exists(abs_db_path):
        return json.dumps({
            "status": "error",
            "error_info": f"Database {abs_db_path} does not exist",
            "result_info": None
        }, ensure_ascii=False)
    storage = EmbeddingStorage(all_config['user_name'], all_config['db_path'])
    result_info = []
    cache_dir = os.path.join(all_config['db_path'], 'tmpFile', str(knowledge_id))
    try:
        if all_config.get('isDir'):
            if len(file_path_list) > 1:
                log.warning("isDir=True, but file_path_list has more than one element, only the first element will be processed")
            dir_path = file_path_list[0]
            log.info("开始处理目录: %s", dir_path)
            dir_hash = hashlib.sha256(dir_path.encode()).hexdigest()
            file_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, "/".join([str(knowledge_id),dir_path,dir_hash])))
            # 在数据目录下新增一个目录，目录名为 docId
            cache_dir = os.path.join(cache_dir, file_id)
            os.makedirs(cache_dir, exist_ok=True)
            dir_add_config = {
                "knowledgeId": knowledge_id,
                "docId": file_id,
                "fileType": "dir",
                "fileHash": dir_hash,
                "fileName": dir_path,
                "segmentNum": 0,
                "cachePath": cache_dir,
            }
            dir_add_result = storage.process_manager("document", "add", **dir_add_config)
            if dir_add_result:
                parent_id = dir_add_result['docId']
                file_path_list = [os.path.join(dir_path, file) for file in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, file))]
                result_info.append(dir_add_result | {"file_status": 1})
            else:
                file_path_list = []
                result_info.append(dir_add_config | {"file_status": 0})
                
        log.info("开始处理文件: %s", file_path_list)
        # model_id
        if model_id is None:
            kenowlwdge_info = storage.process_manager("knowledge", "get", knowledgeId=knowledge_id)
            model_id = kenowlwdge_info['embeddingModelId']
        
        # Initialize components
        cursor = storage.model_manager.execute("""
            select t1.modelName, t2.serverBaseUrl, t2.serverApiKey FROM models t1
            left join server t2 on t1.serverId = t2.serverId where t1.modelId =?
        """, (model_id,))
        api_config = dict(cursor.fetchone())
        api_config['serverEmbeddingUrl'] = api_config['serverBaseUrl']+'/v1/embeddings'
        if (api_config['serverApiKey'] is None or api_config['serverApiKey'] == '') and (api_config['serverBaseUrl'] == 'https://api.siliconflow.cn'):
            log.warning("使用默认模型的ApiKey")
            api_config['serverApiKey'] = 'sk-lcmgoofhdtzibdjvizbzzuyuvmwnuzavvdrabokwstieedal'
        elif (api_config['serverApiKey'] is None or api_config['serverApiKey'] == ''):
            log.warning("未配置模型的ApiKey")
            return json.dumps({
                "status": "error",
                "error_info": f"未配置模型的ApiKey",
                "result_info": None 
            }, ensure_ascii=False)
        embedding_client = EmbeddingClient(api_config['serverEmbeddingUrl'], api_config['serverApiKey'], api_config['modelName'])
        log.info(f"EmbeddingClient: {embedding_client}, modelName: {api_config['modelName']}, serverBaseUrl: {api_config['serverBaseUrl']}, serverApiKey: {api_config['serverApiKey']}")
        
        # KnowledgeId
        cursor = storage.knowledge_manager.execute("""
            select chunkSize, chunkOverlap FROM knowledge t1 where t1.knowledgeId =?
        """, (knowledge_id,))
        knowledge_config = dict(cursor.fetchone())
        file_processor = LangChainFileProcessor(chunk_size=knowledge_config['chunkSize'], overlap=knowledge_config['chunkOverlap'])
        log.info(f"LangChainFileProcessor: {file_processor}, chunk_size: {knowledge_config['chunkSize']}, overlap: {knowledge_config['chunkOverlap']}")
        
        processId = PyBridge.try_process(str(knowledge_id), len(file_path_list), all_config.get('isDir', False))
        #processer = PyBridge.PyProcessObject()
        #processer.set_total(len(file_path_list))
        #processer.set_value(0)
        log.info("before PyBridge.start_process")
        #processer = PyBridge.start_process(len(file_path_list))
        #processer = PyBridge.PyProcessObject()
        #processer.set_total(len(file_path_list))
        log.info("after PyBridge.start_process")
        success_count = 0
        for file_ind, file_path in enumerate(file_path_list):
            # get file type
            _, ext = os.path.splitext(file_path)
            file_type = ext[1:] if ext else ""
            if file_type not in process_type:
                log.warning(f"{file_path} 的文件类型不支持: {file_type}")
                result_info.append({
                    "docId": "",
                    "segmentNum": 0,
                    "fileName": os.path.basename(file_path),
                    "file_status": 0
                })
                continue

            # Read and hash the file
            with open(file_path, 'rb') as file:
                file_content = file.read()
                file_hash = hashlib.sha256(file_content).hexdigest()

            # Parse the file
            file_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, "/".join([str(knowledge_id),file_path,file_hash])))
            doc_id = all_config.get('docId', file_uuid)

            # 拷贝到 cache_dir 路径下
            tmp_file_path = os.path.join(cache_dir, f"{doc_id}.{file_type}")
            os.makedirs(os.path.dirname(tmp_file_path), exist_ok=True)
            shutil.copyfile(file_path, tmp_file_path)
            
            parsed_chunks = file_processor.parse(tmp_file_path, file_type)
            log.info("文件解析完成 共分割为%d个段落", len(parsed_chunks))

            # Generate embeddings and save them
            text_list = []
            embedding_list = []
            metadata_list = []
            create_time = datetime.now()
            for ind, chunk in enumerate(parsed_chunks):
                segment = chunk.page_content
                embedding = embedding_client.get_embedding(segment)
                if type(embedding) == str:
                    embedding = eval(embedding)
                metadata = {"source":tmp_file_path, "knowledgeId":knowledge_id,"docId":doc_id, "index":ind,  
                            "create_time": create_time.strftime("%Y-%m-%d %H:%M:%S"),
                            "type":file_processor.__class__.__name__}
                text_list.append(segment)
                embedding_list.append(embedding)
                metadata_list.append(metadata)
            # 先document 后 embedding
            doc_result = storage.save_document(knowledge_id, doc_id, os.path.basename(file_path), file_type, file_hash, len(parsed_chunks), tmp_file_path, parent_id)
            emb_result = storage.save_embedding(knowledge_id, doc_id, text_list, embedding_list, metadata_list)
            log.info("存储结果: 文档元数据[%s] 嵌入数据[%s]", doc_result, emb_result)
            
            if len(parsed_chunks)>0 and emb_result and doc_result:
                result_info.append(doc_result | {"file_status": 1})
                success_count += 1
                log.info("文件处理成功: %s 分段数: %d", file_path, len(parsed_chunks))
            else:
                result_info.append({
                    "docId": doc_id,
                    "segmentNum": len(parsed_chunks),
                    "fileName": os.path.basename(file_path),
                    "file_status": 0
                })
                log.warning(f"文件处理失败: {file_path}, get result: chunks_num={len(parsed_chunks)}, doc_result={doc_result}, emb_result={emb_result}")
            #processer.set_value(file_ind + 1)
            PyBridge.process_value(processId, file_ind + 1)

            # yield json.dumps({
            #     "status": "process",
            #     "error_info": None,
            #     "processed_task": file_ind+1,
            #     "total_task": len(file_path_list),
            #     "result_info": result_info
            # }, ensure_ascii=False)
        #processer.finish(1, "")
        PyBridge.finish_process(processId, 1, "")
        result = {
            "status": "success",
            "error_info": None,
            "result_info": result_info
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        log.error("文件处理异常: %s", str(e), exc_info=True)
        result =  {
            "status": "error",
            "error_info": str(e),
            "result_info": None
        }
        return json.dumps(result, ensure_ascii=False)
    finally:
        storage.close()

def delete_file(db_config: str|dict) -> dict:
    if type(db_config) == str:
        db_config = json.loads(db_config)
    result = {
        "status": "",
        "error_info": None,
        "result_info": None
    }
    # Check if database exists
    abs_db_path = os.path.join(db_config['db_path'], f"{db_config['user_name']}.db")
    if not os.path.exists(abs_db_path):
        return json.dumps({
            "status": "error",
            "error_info": f"Database {abs_db_path} does not exist",
            "result_info": None
        }, ensure_ascii=False)
    storage = EmbeddingStorage(db_config['user_name'], db_config['db_path'])
    try:
        file_info = storage.process_manager("document", "get", **db_config)
        if file_info is None:
            result["status"] = "error"
            result["error_info"] = f"文档 {db_config['knowledgeId']}/{db_config['docId']} 不存在"
            return json.dumps(result, ensure_ascii=False)
        ifDir = file_info.get('fileType') == "dir"
        if ifDir:
            # 删除目录下的所有文件
            log.info("删除目录请求: knowledgeId=%s docId=%s, dirName=%s", db_config['knowledgeId'], db_config['docId'], file_info['fileName'])
            cache_dir = file_info['cachePath']
            if os.path.exists(cache_dir):
                shutil.rmtree(cache_dir)
            # 删除目录配置
            delete_dir_result = storage.delete_document(db_config['knowledgeId'], db_config['docId'])
            if delete_dir_result:
                log.info("目录删除成功")
            delete_result = storage.delete_dir_document(db_config['knowledgeId'], db_config['docId'])
            if delete_result:
                result["status"] = "success"
                result["result_info"] = delete_result
            else:
                result["status"] = "error"
                result["error_info"] = f"目录 {db_config['knowledgeId']}/{db_config['docId']} 删除失败，可能目录下不存在文件"
        else:
            log.info("删除文档请求: knowledgeId=%s docId=%s, fileName=%s", db_config['knowledgeId'], db_config['docId'], file_info['fileName'])
            cache_dir = file_info['cachePath']
            if os.path.exists(cache_dir):
                os.remove(cache_dir)
            delete_result = storage.delete_document(db_config['knowledgeId'], db_config['docId'])
            if delete_result:
                result["status"] = "success"
                result["result_info"] = delete_result
            else:
                result["status"] = "error"
                result["error_info"] = f"文档 {db_config['knowledgeId']}/{db_config['docId']} 删除失败，可能不存在"
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        log.error("删除文档异常: %s", str(e), exc_info=True)
        return json.dumps({"status": "error", "error_info": str(e), "result_info":None}, ensure_ascii=False)
    finally:
        storage.close()


if __name__ == "__main__":
    pass