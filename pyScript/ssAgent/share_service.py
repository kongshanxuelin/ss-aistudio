import shutil
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

# 发送请求到远程 API
def send_request(action, target, params):
    payload = {
        "action": action,
        "target": target,
        "params": params
    }
    response = requests.post(REMOTE_API_URL, json=payload)
    return response

# 处理 `agents` 表数据并上传
def add_share_agents(conn, agentId, remote_knowledgeIds, user_name, remote_agent_id=False):
    cursor = conn.cursor()
    cursor.execute("SELECT agentName, prompt, description, knowledgeIdList, chatParams FROM agents WHERE agentId=?", (agentId,))
    agent = cursor.fetchall()

    agent_name, prompt, description, knowledge_ids, chat_params = agent[0]
    
    if remote_agent_id:
        params = {
            "agentName": user_name + "_" + agent_name,
            'agentId':remote_agent_id,
            "prompt": prompt,
            "createBy": user_name,
            "description": description,
            "chatParams": chat_params,
            "localAgentId": agentId
        }
        agent_response = send_request("update", "agent", params)
    else:
        params = {
            "agentName": user_name + "_" + agent_name,
            "prompt": prompt,
            "createBy": user_name,
            "description": description,
            "knowledgeIdList": remote_knowledgeIds,
            "chatParams": chat_params,
            "localAgentId": agentId
        }
        agent_response = send_request("add", "agent", params)
    if agent_response.status_code == 200:
        return agent_response.json()
    else:
        log.error(f"Failed to share agent {agentId}. Status code: {agent_response.status_code}, Error: {agent_response.text}")
        return dict(status="error", error_info=agent_response.text, result_info=None)

# 处理 `knowledge` 表数据并上传
def add_share_knowledge(conn, knowledgeId, user_name):
    cursor = conn.cursor()
    cursor.execute("SELECT knowledgeName, chunkSize, chunkOverlap, queryThreshold, maxCount FROM knowledge WHERE knowledgeId=?", (knowledgeId,))
    knowledge = cursor.fetchall()
    
    name, chunk_size, chunk_overlap, query_threshold, max_count = knowledge[0]
    params = {
        "knowledgeName": user_name+"_"+name,
        "chunkSize": chunk_size,
        "chunkOverlap": chunk_overlap,
        "queryThreshold": query_threshold,
        "maxCount": max_count
    }
    knowledge_response = send_request("add", "knowledge", params)
    if knowledge_response.status_code == 200:
        return knowledge_response.json()
    else:
        log.error(f"Failed to share knowledge {knowledgeId}. Status code: {knowledge_response.status_code}, Error: {knowledge_response.text}")
        return dict(status="error", error_info=knowledge_response.text, result_info=None)

# 处理 `documents` 表数据并上传
def add_share_documents(conn, knowledgeId, remote_knowledgeId, remote_file_path):
    """D:\desktop\work\localpy\./db_date\tmpFile\40f350b2-b27a-5a62-9c65-defd8144a31a.pdf"""
    cursor = conn.cursor()
    cursor.execute("SELECT docId, fileName, fileType, fileHash, cachePath, parentId, segmentNum FROM documents WHERE knowledgeId=?", (knowledgeId, ))
    dirs = cursor.fetchall()

    all_result = []
    success_count = 0
    for dir in dirs:
        doc_id, file_name, file_type, file_hash, cache_path, parent_id, segment_num = dir
        remote_cache_path = os.path.join(remote_file_path, cache_path.split("tmpFile")[-1].lstrip("\\/"))
        params = {
            "knowledgeId": remote_knowledgeId,
            "docId": doc_id,
            "fileName": file_name,
            "fileType": file_type,
            "fileHash": file_hash,
            "cachePath": remote_cache_path,
            "parentId": parent_id,
            "segmentNum": segment_num
        }
        doc_response = send_request("add", "document", params)
        if doc_response.status_code == 200:
            success_count += 1
            all_result.append(doc_response.json())
        else:
            all_result.append(dict(status="error", error_info=doc_response.text, result_info=None))
    log.info(f"{success_count}/{len(dirs)} documents uploaded successfully.")
    return all_result

# 处理 `embeddings` 表数据并上传
def add_share_embeddings(conn, knowledgeId, remote_knowledgeId, remote_file_path):
    """{"source": "D:\\desktop\\work\\localpy\\./db_date\\tmpFile\\40f350b2-b27a-5a62-9c65-defd8144a31a.pdf", 
    "knowledgeId": 1, 
    "docId": "40f350b2-b27a-5a62-9c65-defd8144a31a", 
    "index": 0, 
    "create_time": "2025-03-27 10:20:21", 
    "type": "LangChainFileProcessor"}
    """
    all_result = []
    success_count = 0
    cursor = conn.cursor()
    cursor.execute("SELECT docId FROM documents WHERE knowledgeId=? AND fileType<>'dir'", (knowledgeId, ))
    docId_list = [doc[0] for doc in cursor.fetchall()]
    
    for doc_id in docId_list:
        cursor.execute("SELECT segmentIndex, textContent, embeddingData, metaData FROM embeddings WHERE knowledgeId=? AND docId=? ORDER BY segmentIndex", (knowledgeId, doc_id))
        doc_embeddings = cursor.fetchall()
        text_list, embedding_list, metadata_list = [], [], []
        for emb in doc_embeddings:
            segment_index, text_content, embedding_data, meta_data = emb
            meta_data_json = json.loads(meta_data) if meta_data else {}
            if meta_data_json:
                meta_data_json["source"] = os.path.join(remote_file_path, meta_data_json["source"].split("tmpFile")[-1].lstrip("\\/"))
                meta_data_json["knowledgeId"] = remote_knowledgeId
                meta_data_json['index'] = segment_index
            text_list.append(text_content)
            embedding_list.append(list(struct.unpack(f'{len(embedding_data)//4}f', embedding_data)))  
            metadata_list.append(json.dumps(meta_data_json, ensure_ascii=False) if meta_data_json else "")
        params = {
            "knowledge_id": remote_knowledgeId,
            "doc_id": doc_id,
            "text_list": text_list,
            "embedding_list": embedding_list, 
            "metadata_list": metadata_list
        }
        emb_response = send_request("add", "embedding", params)
        if emb_response.status_code == 200:
            success_count += 1
            all_result.append(emb_response.json())
        else:
            all_result.append(dict(status="error", error_info=emb_response.text, result_info=None))
    log.info(f"{success_count}/{len(docId_list)} embeddings uploaded successfully.")
    return all_result

def get_documents_info(conn, knowledge_ids):
    # 获取所有knowledgeId的docId
    cursor = conn.cursor()
    cursor.execute("SELECT docId, cachePath, parentid, fileType FROM documents WHERE knowledgeId in (?) ORDER BY createdAt", (','.join(knowledge_ids), ))
    dirs = cursor.fetchall()
    file_list = [dir[1] for dir in dirs if dir[2] is None]
    return file_list

def update_document_files(conn, knowledge_ids):
    cursor = conn.cursor()
    for knowledge_id in knowledge_ids:
        query_message = "SELECT docId, cachePath, parentid, fileType, knowledgeId FROM documents WHERE knowledgeId = ? ORDER BY createdAt"
        log.info(f"query_message: {query_message}")
        cursor.execute(query_message, (knowledge_id, ))
        dirs = cursor.fetchall()
        #log.info(f"dirs: {dirs}")
        if len(dirs) == 0:
            continue
        all_doc_ids = [[d[0],d[4],d[1]] for d in dirs]
        #log.info(f"cache_path: {all_doc_ids}")
        cache_path = os.path.join(all_doc_ids[0][2].split("tmpFile")[0].lstrip("\\/"), "tmpFile")
        doc_ids = [d[0] for d in all_doc_ids if str(d[1]) == str(knowledge_id)]
        log.info(f"update document files for knowledge_id: {knowledge_id}, dict_ids: {len(doc_ids)}")
        # 删除 cache_path+"/"+knowledge_id 目录下的所有不在all_doc中的文件
        knowledge_dir = os.path.join(cache_path, str(knowledge_id))
        for file in os.listdir(knowledge_dir):
            try:
                file_id, file_ext = os.path.splitext(file)
            except:
                file_id = file
            if file == "images":
                temp_images = os.path.join(knowledge_dir, file)
                for image_name in os.listdir(temp_images):
                    if image_name not in doc_ids:
                        shutil.rmtree(os.path.join(temp_images, image_name))
                        log.info(os.path.join(temp_images, image_name))
            elif file_id in doc_ids:
                file_path = os.path.join(knowledge_dir, file)
                temp_images = os.path.join(file_path, "images")
                if os.path.exists(temp_images):
                    for image_name in os.listdir(temp_images):
                        if image_name not in doc_ids:
                            shutil.rmtree(os.path.join(temp_images, image_name))
                            log.info(os.path.join(temp_images, image_name))
            else:
                file_path = os.path.join(knowledge_dir, file)
                if os.path.isfile(file_path):
                    os.remove(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                log.info(file_path)


def create_zip(file_list, zip_path):
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for item in file_list:
            if os.path.isdir(item):
                # 递归添加目录
                for root, _, files in os.walk(item):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, start=os.path.dirname(file_list[0]))
                        zipf.write(file_path, arcname)
            else:
                arcname = os.path.basename(item)
                zipf.write(item, arcname)
    print(f"文件已打包至 {zip_path}")

# 上传压缩包到远程服务器
def upload_zip(zip_path, create_user, agent_id):
    with open(zip_path, 'rb') as f:
        files = {'file': (zip_path, f, 'application/zip')}
        data = {
            "create_user": create_user,
            "agent_id": agent_id
        }
        response = requests.post(REMOTE_SERVER_URL, data=data, files=files)
    
    if response.status_code == 200:
        result = response.json()
        log.info("远程服务器返回的解压路径:", result['result_info']["extract_dir"])
        return result
    else:
        log.info("上传失败:", response.text)
        return 0


def share_agent_data(db_config: str|dict) -> dict:
    if type(db_config) == str:
        db_config = json.loads(db_config)
    agentId = db_config["agentId"]
    user_name = db_config["user_name"]
    db_path = db_config["db_path"]
    result = {
        "status": "",
        "error_info": None,
        "result_info": None
    }
    # 检查数据库是否存在
    abs_db_path = os.path.join(db_path, f"{user_name}.db")
    if not os.path.exists(os.path.join(db_path, f"{user_name}.db")):
        log.error(f"Database {abs_db_path} does not exist")
        result["status"] = "error"
        result["error_info"] = f"Database {abs_db_path} does not exist"
        return json.dumps(result, ensure_ascii=False)

    storage = EmbeddingStorage(user_name, db_path)
    conn = storage.conn

    try:
        knowledgeIdlist = []
        # 获取agent下所有的knowledgeId
        log.info(f"开始同步agentId: {agentId}的数据...")
        cursor = conn.cursor()
        cursor.execute("SELECT knowledgeIdList, shareAgentId FROM agents WHERE agentId=?", (agentId,))
        agent_info = cursor.fetchall()
        share_agent_id = agent_info[0][1]
        knowledge_ids = agent_info[0][0].split(",")
        if share_agent_id is not None:
            log.warning(f"该agent已同步过，请更新！, 远程AgentId: {share_agent_id}")
            result["status"] = "error"
            result["error_info"] = f"该agent已同步过，请更新！, 远程AgentId: {share_agent_id}"
            result["result_info"] = {"agentId": share_agent_id}
            return json.dumps(result, ensure_ascii=False)

        if len(knowledge_ids) == 0:
            log.warning(f"该agent下没有知识库，只上传智能体！")
            agent_res = add_share_agents(conn, agentId, "", user_name)
            if agent_res:
                result["status"] = "success"
                result["result_info"] = agent_res
            else:
                result["status"] = "error"
            return json.dumps(result, ensure_ascii=False)
        
        # 获取所有文件路径 和解析的文件 docId
        # file_list = get_documents_info(conn, knowledge_ids)
        # 根据数据库中的文件信息更新本地路径
        update_document_files(conn, knowledge_ids)
        
        log.info(f"开始打包并上传文件...")
        zip_file = os.path.join(db_path, 'tmpFile', f"{user_name}_{agentId}.zip")
        file_list = [os.path.join(db_path, 'tmpFile', str(f)) for f in knowledge_ids]
        create_zip(file_list, zip_file)
        upload_res = upload_zip(zip_file, user_name, agentId)
        if upload_res:
            remote_file_path = upload_res['result_info']["extract_dir"]
            log.info(f"文件上传成功，解压路径: {remote_file_path}，删除本地打包文件")
            os.remove(zip_file)
        # 
        all_knowledge = 0
        success_knowledge = 0
        all_document = 0
        success_document = 0
        all_emb = 0
        success_emb = 0
        for knowledge_id in knowledge_ids:
            all_knowledge += 1
            remote_knowledge_info = add_share_knowledge(conn, knowledge_id, user_name)
            log.info(f"knowledge_id:{knowledge_id} 上传知识库完成，结果：{remote_knowledge_info}")
            if remote_knowledge_info["status"] == "success":
                success_knowledge += 1
            remote_knowledgeId = remote_knowledge_info['result_info']["knowledgeId"]
            knowledgeIdlist.append(remote_knowledgeId)
            # 获取所有knowledgeId的docId
            doc_res = add_share_documents(conn, knowledge_id, remote_knowledgeId, remote_file_path)
            emb_res = add_share_embeddings(conn, knowledge_id, remote_knowledgeId, remote_file_path)
            all_document += len(doc_res)
            all_emb += len(emb_res)
            temp_count = 0
            for res in doc_res:
                if res["status"] == "success":
                    temp_count += 1
            success_document += temp_count
            log.info(f"knowledge_id:{knowledge_id} 上传文件完成，处理 {temp_count}/{len(doc_res)} 条, 结果：{doc_res}")
            temp_count = 0
            for res in emb_res:
                if res["status"] == "success":
                    temp_count += 1
            success_emb += temp_count
            log.info(f"knowledge_id:{knowledge_id} 上传embedding完成，处理 {temp_count}/{len(emb_res)} 条, 结果：{emb_res}")
            # print(doc_res, emb_res)
        knowledgeIdlist = ",".join([str(know_id) for know_id in knowledgeIdlist])
        log.info(f"knowledge 同步完成！结果:{knowledgeIdlist}, 完成处理文件/目录：{success_document}/{all_document}, 完成处理embedding：{success_emb}/{all_emb}")
        agent_res = add_share_agents(conn, agentId, knowledgeIdlist, user_name)
        log.info(f"\n数据同步完成！结果:{agent_res}")
        if agent_res is not None:
            remote_agentId = agent_res["result_info"]["agentId"]
            log.info(f"agent 共享成功，得到远程的AgentID: {remote_agentId}")
            cursor.execute(f"UPDATE agents SET shareAgentId=? WHERE agentId = ?", (remote_agentId, agentId))
            conn.commit()
            return json.dumps(agent_res, ensure_ascii=False)
        else:
            log.error(f"agent 共享失败，错误信息：{agent_res}")
            return json.dumps(agent_res, ensure_ascii=False)
    except Exception as e:
        log.error(f"同步失败，错误信息：{e}")
        result["status"] = "error"
        result["error_info"] = f"同步失败，错误信息：{e}"
        return json.dumps(result, ensure_ascii=False)
    finally:
        storage.close()


def update_agent_data_online(db_config: str|dict) -> dict:
    """更新已存在的Agent数据"""
    if type(db_config) == str:
        db_config = json.loads(db_config)
    
    agentId = db_config["agentId"]
    user_name = db_config["user_name"]
    db_path = db_config["db_path"]
    
    result = {
        "status": "",
        "error_info": None,
        "result_info": None
    }
    
    # 检查数据库是否存在
    abs_db_path = os.path.join(db_path, f"{user_name}.db")
    if not os.path.exists(abs_db_path):
        log.error(f"Database {abs_db_path} does not exist")
        result.update(status="error", error_info=f"Database {abs_db_path} does not exist")
        return json.dumps(result, ensure_ascii=False)

    storage = EmbeddingStorage(user_name, db_path)
    conn = storage.conn

    try:
        log.info(f"开始更新agentId: {agentId}的数据...")
        cursor = conn.cursor()
        
        # 获取远程AgentID和知识库列表
        cursor.execute("SELECT knowledgeIdList, shareAgentId FROM agents WHERE agentId=?", (agentId,))
        knowledge_list, share_agent_id = cursor.fetchone()
        
        if not share_agent_id:
            log.error("该Agent未同步过，请先执行共享操作")
            result.update(status="error", error_info="该Agent未同步过，请先执行共享操作")
            return json.dumps(result, ensure_ascii=False)
            
        knowledge_ids = knowledge_list.split(",")
        log.info(f"需要更新的知识库数量: {len(knowledge_ids)}")
        if len(knowledge_ids) == 0:
            log.warning("该Agent下没有知识库，无需更新")
            result.update(status="error", error_info="该Agent下没有知识库，无需更新")
            return json.dumps(result, ensure_ascii=False)

        # 文件打包上传（复用原有逻辑）
        # file_list = get_documents_info(conn, knowledge_ids)
        update_document_files(conn, knowledge_ids)
        zip_file = os.path.join(db_path, 'tmpFile', f"UPDATE_{user_name}_{agentId}.zip")
        file_list = [os.path.join(db_path, 'tmpFile', str(f)) for f in knowledge_ids]
        create_zip(file_list, zip_file)
        upload_res = upload_zip(zip_file, user_name, agentId)
        
        if not upload_res:
            result.update(status="error", error_info="文件上传失败")
            return json.dumps(result, ensure_ascii=False)
            
        remote_file_path = upload_res['result_info']["extract_dir"]
        log.info(f"文件更新成功，新解压路径: {remote_file_path}")
        os.remove(zip_file)

        # 遍历更新文档和embedding
        success_counts = {"document": 0, "embedding": 0, "knowledge": 0}
        total_counts = {"document": 0, "embedding": 0, "knowledge": 0}
        
        # 远程接口获取对应的远程knowledge信息
        params = {
            "agentId": share_agent_id,
            "createBy": user_name
        }
        agent_response = send_request("query", "agent", params)
        if agent_response.status_code != 200:
            log.error(f"获取远程Agent信息失败: {agent_response.text}")
            result.update(status="error", error_info=f"获取远程Agent信息失败: {agent_response.text}")
            return json.dumps(result, ensure_ascii=False)
        remote_knowledge_list = agent_response.json()['result_info']['knowledgeIdList']
        remote_knowledge_ids = remote_knowledge_list.split(",")
        agent_res = add_share_agents(conn, agentId, remote_knowledge_ids, user_name, share_agent_id)
        log.info(f"update agent 成功，得到远程的AgentID: {share_agent_id}, result: {agent_res}")
        try:
            assert len(knowledge_ids) == len(remote_knowledge_ids)
        except AssertionError:
            log.error(f"本地知识库数量与远程知识库数量不一致，本地：{len(knowledge_ids)}，远程：{len(remote_knowledge_ids)}")
            result.update(status="error", error_info=f"本地知识库数量与远程知识库数量不一致，本地：{len(knowledge_ids)}，远程：{len(remote_knowledge_ids)}")
            raise ValueError("本地知识库数量和远程知识库数量不一致，请取消分享后重新分享")
        
        for knowledge_id,remote_knowledge_id in zip(knowledge_ids, remote_knowledge_ids):
            if not remote_knowledge_id:
                log.warning(f"知识库 {knowledge_id} 未同步过，跳过更新")
                continue
            
            document_response= send_request('query', 'document', {"knowledgeId": remote_knowledge_id, "docId":"all"})
            if document_response.status_code!= 200 or document_response.json()['status']!='success':
                log.error(f"获取远程知识库信息失败: {document_response.text}")
                result.update(status="error", error_info=f"获取远程知识库信息失败: {document_response.text}")
                continue
            else:
                success_counts['knowledge'] += 1
                log.info(f"远程知识库ID: {remote_knowledge_id} 信息获取成功")
            knowledge_info = document_response.json()['result_info']
            for info_ in knowledge_info:
                remote_doc_id = info_['docId']
                doc_response = send_request('delete', 'document', {"knowledgeId": remote_knowledge_id, "docId": remote_doc_id})
                if doc_response.status_code!= 200 or doc_response.json()['status']!='success':
                    log.error(f"删除远程文档 {remote_doc_id} 失败: {doc_response.text}")
                    continue
                
            # 获取所有knowledgeId的docId
            doc_res = add_share_documents(conn, knowledge_id, remote_knowledge_id, remote_file_path)
            emb_res = add_share_embeddings(conn, knowledge_id, remote_knowledge_id, remote_file_path)
            temp_count = 0
            for res in doc_res:
                if res["status"] == "success":
                    temp_count += 1
            success_counts["document"] += temp_count
            total_counts["document"] += len(doc_res)
            print(f"knowledge_id:{knowledge_id} 上传文件完成，处理 {temp_count}/{len(doc_res)} 条, 结果：{doc_res}")
            temp_count = 0
            for res in emb_res:
                if res["status"] == "success":
                    temp_count += 1
            success_counts["embedding"] += temp_count
            total_counts["embedding"] += len(emb_res)
            print(f"knowledge_id:{knowledge_id} 上传embedding完成，处理 {temp_count}/{len(emb_res)} 条, 结果：{emb_res}")

        # 更新后agentId信息
        agent_response = send_request("query", "agent", {"agentId": share_agent_id, "createBy": user_name})
        if agent_response.status_code!= 200 or agent_response.json()['status']!='success':
            log.error(f"获取远程Agent信息失败: {agent_response.text}")
            result.update(status="error", error_info=f"获取远程Agent信息失败: {agent_response.text}")
            return json.dumps(result, ensure_ascii=False)
        else:
            log.info(f"远程AgentID: {share_agent_id} 信息获取成功")
            agent_info = agent_response.json()['result_info']

        # 生成最终结果
        result.update(
            status="success",
            result_info={
                "updated_documents": f"{success_counts['document']}/{total_counts['document']}",
                "updated_embeddings": f"{success_counts['embedding']}/{total_counts['embedding']}",
                "remote_agent_id": share_agent_id
            } | agent_info
        )
        log.info(f"数据更新完成！文档成功率: {success_counts['document']/total_counts['document']:.1%}, "
                f"Embedding成功率: {success_counts['embedding']/total_counts['embedding']:.1%}")
        
    except Exception as e:
        log.error(f"更新失败: {str(e)}", exc_info=True)
        result.update(status="error", error_info=str(e))
    finally:
        storage.close()
    
    return json.dumps(result, ensure_ascii=False)

def close_agent_data(db_config: str|dict) -> dict:
    if type(db_config) == str:
        db_config = json.loads(db_config)
    user_name = db_config["user_name"]
    db_path = db_config["db_path"]
    result = {
        "status": "",
        "error_info": None,
        "result_info": None
    }
    agentId = db_config.get("agentId", None)
    share_agent_id = db_config.get("shareAgentId", None)
    if agentId is None and share_agent_id is None:
        log.error("agentId 和 shareAgentId 不能同时为空")
        result["status"] = "error"
        result["error_info"] = "agentId 和 shareAgentId 不能同时为空"
        return json.dumps(result, ensure_ascii=False)

    #检查数据库是否存在
    abs_db_path = os.path.join(db_path, f"{user_name}.db")
    if not os.path.exists(abs_db_path):
        log.error(f"Database {abs_db_path} does not exist")
        result["status"] = "error"
        result["error_info"] = f"Database {abs_db_path} does not exist"
        return json.dumps(result, ensure_ascii=False)
    
    # 获取远程的agentId
    storage = EmbeddingStorage(user_name, db_path)
    conn = storage.conn
    
    try:
        cursor = conn.cursor()
        if agentId is not None:
            log.info(f"通过本地agentId: {agentId} 找到远程的agentId")
            cursor.execute("SELECT shareAgentId FROM agents WHERE agentId=?", (agentId,))
            agent_info = cursor.fetchall()
            share_agent_id = agent_info[0][0]
        elif share_agent_id is not None:
            log.info(f"通过远程agentId: {share_agent_id} 找到本地的agentId")
            agent_response = send_request("query", "agent", {"agentId": share_agent_id, "createBy": user_name})
            if agent_response.status_code == 200:
                agent_info = agent_response.json()['result_info']
                agentId = agent_info['localAgentId']
            else:
                log.error(f"获取本地agentId失败: {agent_response.text}")
                result["status"] = "error"
                result["error_info"] = f"获取本地agentId失败: {agent_response.text}"
                return json.dumps(result, ensure_ascii=False)
            
        log.info(f"开始关闭agentId: 本地agentId: {agentId}， 远程agentId: {share_agent_id}")
        if share_agent_id is None:
            log.warning(f"该agent未同步过，请同步！")
            result["status"] = "error"
            result["error_info"] = f"该agent未同步过，请同步！"
            return json.dumps(result, ensure_ascii=False)
        # 删除远程的agent
        params = {
            "agentId": share_agent_id,
            "localAgentId": agentId,
            "createBy": user_name,
        }
        agent_response = send_request("close", "agent", params)
        if agent_response.status_code == 200:
            log.info(f"关闭共享成功，结果：{agent_response.json()}")
            # result["status"] = "success"
            # result["result_info"] = agent_response.json()['result_info']
            cursor.execute(f"UPDATE agents SET shareAgentId=? WHERE agentId =?", (None, agentId))
            conn.commit()
            return json.dumps(agent_response.json(), ensure_ascii=False)
        else:
            log.error(f"关闭共享失败，错误信息：{agent_response.text}")
            # result["status"] = "error"
            # result["error_info"] = agent_response.json()['error_info']
            return json.dumps(agent_response.json(), ensure_ascii=False)
    except Exception as e:
        log.error(f"关闭共享失败，错误信息：{e}")
        result["status"] = "error"
        result["error_info"] = f"关闭共享失败，错误信息：{e}"
        return json.dumps(result, ensure_ascii=False)
    finally:
        storage.close()
   


# 执行同步任务
# if __name__ == "__main__":
#     agentId = 2
#     user_name = "testuser"
#     db_config = {
#         "agentId": agentId,
#         "user_name": user_name,
#         "db_path": "D:\\desktop\\work\\localpy\\db_date"
#     }
#     share_res = share_agent_data(json.dumps(db_config, ensure_ascii=False))
#     print("######################\n", share_res)
    
#     share_agent_id = json.loads(share_res)['result_info']['agentId']

#     # update_res = update_agent_data_onine(json.dumps(db_config, ensure_ascii=False))
#     # print("######################\n", update_res)

#     db_config = {
#         # "agentId": agentId,
#         "shareAgentId": share_agent_id,
#         "user_name": user_name,
#         "db_path": "D:\\desktop\\work\\localpy\\db_date"
#     }
#     close_res = close_agent_data(json.dumps(db_config, ensure_ascii=False))
#     print("######################\n", close_res)
