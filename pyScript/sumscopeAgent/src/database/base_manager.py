from datetime import datetime # type: ignore
import struct # type: ignore
import os, sys
import sqlite3
import json
import logging as log  # 新增日志模块
from abc import ABC # type: ignore
import uuid # type: ignore
import base64 # type: ignore

base_path = os.path.join(os.path.dirname(__file__), "../../")
sys.path.append(base_path)
from configs import configs
config_path = os.path.join(base_path, 'configs')

class DatabaseManager(ABC):
    """数据库管理基类"""
    def __init__(self, conn):
        self.conn = conn
        self.conn.row_factory = sqlite3.Row  # 使查询结果转为字典格式
        
    def execute(self, query: str, params=()):
        """执行SQL语句并返回游标"""
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return cursor


class ServerManager(DatabaseManager):
    """服务器管理"""
    def create_table(self):
        self.execute("""
            CREATE TABLE IF NOT EXISTS server (
                serverId INTEGER PRIMARY KEY AUTOINCREMENT,
                serverName TEXT UNIQUE,
                serverState INTEGER,
                serverBaseUrl TEXT,
                serverChatUrl TEXT,
                serverApiKey TEXT,
                serverCreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()
        # 判断表的数据量
        cursor = self.execute("SELECT COUNT(*) FROM server")
        count = cursor.fetchone()[0]
        if count == 0:
            log.info("✅ server表为空，插入默认配置")
            self.insert_defaults()
    
    def insert_defaults(self):
        """插入默认服务器配置"""
        config_file = os.path.join(config_path, configs.server_file)
        with open(config_file, 'r', encoding='utf-8') as f:
            servers = json.load(f)
        intsert_num = 0 
        for server in servers:
            self.execute(
                "INSERT OR IGNORE INTO server (serverName, serverState, serverBaseUrl, serverChatUrl, serverApiKey) VALUES (?,?,?,?,?)",
                (server['serverName'], server['serverState'], server['serverBaseUrl'], 
                 server['serverChatUrl'], server['serverApiKey'])
            )
            intsert_num += 1
        self.conn.commit()
        log.info(f"✅ 成功插入{intsert_num}条默认服务器配置")
        return intsert_num
    
    def add_server(self, **kwargs) -> int:
        server_state = kwargs.get('serverState', 0)
        server_name = kwargs.get('serverName')
        base_url = kwargs.get('serverBaseUrl', '')
        if base_url.endswith("#"):
            chat_url = base_url[:-1]
        elif base_url.endswith("/"):
            chat_url = base_url + "chat/completions"
        elif not base_url.endswith("/"):
            chat_url = base_url + "/v1/chat/completions"
        # chat_url = chat_url.replace("//", "/")
        api_key = kwargs.get('serverApiKey', '')
        if server_name:
            """添加新服务器，返回新创建的serverId"""
            cursor = self.conn.cursor()
            # 查询是否已存在同名服务器
            cursor.execute("SELECT serverId FROM server WHERE serverName = ?", (server_name,))
            existing_server = cursor.fetchone()
            if existing_server:
                log.warning(f"⏩ 跳过服务器添加：已存在同名服务器 '{server_name}'")
                return self.get_server(existing_server['serverId'])
            cursor.execute(
                "INSERT INTO server (serverName, serverState, serverBaseUrl, serverChatUrl, serverApiKey) VALUES (?,?,?,?,?)",
                (server_name, server_state, base_url, chat_url, api_key)
            )
            self.conn.commit()
            log.info(f"✅ 成功添加新服务器：{server_name}")
            return self.get_server(cursor.lastrowid)
        else:
            log.error(f"❌ 服务器添加失败：缺少必要参数['server_name']")
            raise ValueError("服务器添加失败：缺少必要参数['server_name']")
            return 0
    
    def delete_server(self, server_id: int) -> bool:
        """根据serverId删除服务器"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM server WHERE serverId = ?", (server_id,))
        self.conn.commit()
        if cursor.rowcount > 0:
            log.info(f"✅ 成功删除服务器：serverId={server_id}")
        else:
            log.warning(f"⏩ 删除服务器失败：serverId={server_id} 不存在")
        return cursor.rowcount

    def update_server(self, server_id: int, **kwargs):
        """更新服务器信息，可更新字段：serverName, serverBaseUrl, serverChatUrl, serverApiKey"""
        allowed_fields = {'serverName', 'serverState', 'serverBaseUrl', 'serverChatUrl', 'serverApiKey'}
        if kwargs.get('serverBaseUrl'):
            base_url = kwargs.get('serverBaseUrl')
            if base_url.endswith("#"):
                chat_url = base_url[:-1]
            elif base_url.endswith("/"):
                chat_url = base_url + "chat/completions"
            elif not base_url.endswith("/"):
                chat_url = base_url + "/v1/chat/completions"
            kwargs['serverChatUrl'] = chat_url
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        cursor = self.conn.cursor()
        set_clause = ", ".join([f"{k} = ?" for k in updates])
        values = list(updates.values()) + [server_id]
        cursor.execute(f"UPDATE server SET {set_clause} WHERE serverId = ?", values)
        self.conn.commit()
        log.info(f"✅ 成功更新服务器：serverId={server_id}")
        return self.get_server(server_id)

    def get_server(self, server_id: int|str) -> dict:
        """根据serverId获取服务器信息"""
        if server_id == "all":
            log.info("✅ 获取所有服务器信息")
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM server")
            return [dict(row) for row in cursor.fetchall()]
        elif type(server_id) == int or server_id.isdigit():
            server_id = int(server_id)
            log.info(f"✅ 获取服务器信息：serverId={server_id}")
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM server WHERE serverId = ?", (server_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        else:
            log.error(f"❌ 获取服务器信息失败：serverId={server_id} 不存在")
            return None


class ModelManager(DatabaseManager):
    """模型管理"""
    def create_table(self):
        self.execute("""
            CREATE TABLE IF NOT EXISTS models (
                modelId INTEGER PRIMARY KEY AUTOINCREMENT,
                modelName TEXT,
                serverId INTEGER,
                defaultModel BOOL,
                embeddingModel BOOL,
                maxTokens INTEGER DEFAULT 8192,
                ModelCreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (serverId) REFERENCES server(serverId)
            )"""
        )
        self.conn.commit()
        # 判断表的数据量
        cursor = self.execute("SELECT COUNT(*) FROM models")
        count = cursor.fetchone()[0]
        if count == 0:
            log.info("✅ models表为空，插入默认配置")
            self.insert_defaults()
    
    def insert_defaults(self):
        """插入默认模型配置"""
        config_file = os.path.join(config_path, configs.models_file)
        with open(config_file, 'r', encoding='utf-8') as f:
            models = json.load(f)
        
        insert_num = 0
        for model in models:
            self.execute(
                "INSERT OR IGNORE INTO models (modelName, serverId, defaultModel, embeddingModel, maxTokens) VALUES (?,?,?,?,?)",
                (model['modelName'], model['serverId'], model['defaultModel'], model['embeddingModel'], model['maxTokens'])
            )
            insert_num += 1
        self.conn.commit()
        log.info(f"✅ 成功插入 {insert_num} 条默认模型配置")
        return insert_num
        
    def add_model(self, **kwargs, ) -> int:
        model_name = kwargs.get('modelName')
        server_id = kwargs.get('serverId')
        is_default = kwargs.get('defaultModel', 0)
        is_embedding = kwargs.get('embeddingModel', 0)
        max_tokens = kwargs.get('maxTokens', 8192)
        if model_name and server_id:
            """添加新模型，返回新创建的modelId"""
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO models (modelName, serverId, defaultModel, embeddingModel, maxTokens) VALUES (?,?,?,?,?)",
                (model_name, server_id, is_default, is_embedding, max_tokens)
            )
            self.conn.commit()
            log.info(f"✅ 模型添加成功：{model_name}")
            return self.get_model(server_id=server_id, model_id=cursor.lastrowid)
        else:
            log.info(f"❌ 模型添加失败：缺少必要参数['model_name', 'server_name']")
            raise ValueError("模型添加失败：缺少必要参数['model_name','server_name']")
            return 0

    def delete_model(self, model_id: int) -> bool:
        """根据modelId删除模型"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM models WHERE modelId = ?", (model_id,))
        self.conn.commit()
        if cursor.rowcount > 0:
            log.info(f"✅ 成功删除模型：modelId={model_id}")
        else:
            log.warning(f"⏩ 删除模型失败：modelId={model_id} 不存在")
        return cursor.rowcount

    def update_default_model(self, model_id: int):
        cursor = self.conn.cursor()
        # 设置 默认 模型，只能有一个
        embeddingModel = cursor.execute("SELECT embeddingModel FROM models WHERE modelId = ?", (model_id, )).fetchone()
        
        # 将所有的默认模型设置为False
        cursor.execute("UPDATE models SET defaultModel = 0 WHERE embeddingModel = ?", (embeddingModel['embeddingModel'], ))
        # 然后设置特定记录的 defaultModel 为1
        cursor.execute("UPDATE models SET defaultModel = 1 WHERE modelId = ?", (model_id,))
        self.conn.commit()
        log.info(f"✅ 成功更新默认模型：modelId={model_id}")
        return self.get_model(server_id="all", model_id=model_id)


    def get_model(self, server_id: int|str, model_id: int|str) -> dict:
        """根据modelId获取模型信息"""
        if type(model_id) == int or model_id.isdigit():
            model_id = int(model_id)
            log.info(f"✅ 获取模型信息：modelId={model_id}")
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM models WHERE modelId = ?", (model_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        elif server_id == "all" and model_id == "all":
            log.info("✅ 获取所有模型信息")
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM models")
            return [dict(row) for row in cursor.fetchall()]
        elif (type(server_id) == int or server_id.isdigit()) and model_id == "all":
            server_id = int(server_id)
            log.info(f"✅ 获取服务器 {server_id} 下的所有模型信息")
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM models WHERE serverId =?", (server_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_default_model(self, embeddingModel=0) -> dict:
        """获取默认模型"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM models WHERE defaultModel = 1 AND embeddingModel = ?", (embeddingModel,))
        row = cursor.fetchone()
        if not row:
            log.warning("⏩ 获取默认模型失败：默认模型不存在")
        elif embeddingModel == 1:
            log.info(f"✅ 获取默认嵌入模型：{row['modelName']}")
        else:
            log.info(f"✅ 获取默认模型：{row['modelName']}")
        return dict(row) if row else None
     
        
class AgentManager(DatabaseManager):
    """智能体管理"""
    def create_table(self):
        self.execute("""
            CREATE TABLE IF NOT EXISTS agents (
                agentId INTEGER PRIMARY KEY AUTOINCREMENT,
                agentName TEXT,
                prompt TEXT,
                description TEXT,
                isLocal BOOL,
                knowledgeIdList TEXT,
                groupName TEXT,
                chatParams TEXT,
                chatModelId INTEGER,
                shareAgentId INTEGER,
                agentCreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        self.conn.commit()
        # 判断表的数据量
        cursor = self.execute("SELECT COUNT(*) FROM agents")
        count = cursor.fetchone()[0]
        if count == 0:
            log.info("✅ Agents表为空，插入默认服务器配置")
            self.insert_defaults()
    
    def insert_defaults(self):
        """插入默认模型配置"""
        config_file = os.path.join(config_path, configs.agents_file)
        with open(config_file, 'r', encoding='utf-8') as f:
            agents = json.load(f)
        insert_num = 0
        for agent in agents:
            isLocal = agent.get("isLocal", False)
            knowledgeIdList = agent.get("knowledgeIdList", "")
            groupName = str(agent.get("group", ""))
            chatParams = agent.get("chatParams", json.dumps(configs.default_chat_config, ensure_ascii=False))
            self.execute("""INSERT OR IGNORE INTO agents (agentName, prompt, description, isLocal, knowledgeIdList, groupName, chatParams) VALUES (?,?,?,?,?,?,?)""",
                (agent['name'], agent['prompt'], agent['description'], isLocal, knowledgeIdList, groupName, chatParams))
            insert_num += 1
        self.conn.commit()
        log.info(f"✅ 成功插入 {insert_num} 条默认智能体配置")
        return insert_num
    
    def add_agent(self, **kwargs) -> bool:
        agent_name = kwargs.get('agentName')
        prompt = kwargs.get('prompt', '')
        description = kwargs.get('description', '')
        is_local = kwargs.get('isLocal', True)
        knowledge_ids = kwargs.get('knowledgeIdList', "")
        group_name = kwargs.get('groupName', "")
        chat_params = kwargs.get("chatParams", json.dumps(configs.default_chat_config, ensure_ascii=False))
        if agent_name:
            """添加新Agent"""
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO agents (agentName, prompt, description, isLocal, knowledgeIdList, groupName, chatParams) VALUES (?,?,?,?,?,?,?)",
                (agent_name, prompt, description, is_local, knowledge_ids, group_name, chat_params)
            )
            self.conn.commit()
            log.info(f"✅ Agent添加成功：{agent_name}")
            return self.get_agent(cursor.lastrowid)
        else:
            log.info(f"❌ Agent添加失败：缺少必要参数['agent_name', 'prompt']")
            raise ValueError("Agent添加失败：缺少必要参数['agent_name', 'prompt']")
            return 0

    def delete_agent(self, agent_id: int) -> bool:
        """根据复合主键删除Agent"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM agents WHERE agentId = ?", (agent_id, ))
        self.conn.commit()
        if cursor.rowcount > 0:
            log.info(f"✅ 成功删除Agent：agentId={agent_id}")
        else:
            log.warning(f"⏩ 删除Agent失败：agentId={agent_id} 不存在")
        return cursor.rowcount

    def update_agent(self, agent_id: int, **kwargs) -> bool:
        """更新Agent"""
        allowed_fields = {'agentName', 'prompt', 'description', 'knowledgeIdList', 'groupName', 'chatParams', 'chatModelId'}
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        cursor = self.conn.cursor()
        set_clause = ", ".join([f"{k} = ?" for k in updates])
        values = list(updates.values()) + [agent_id]
        cursor.execute(f"UPDATE agents SET {set_clause} WHERE agentId = ?", values)
        self.conn.commit()
        log.info(f"✅ 成功更新Agent：agentId={agent_id}")
        return self.get_agent(agent_id)

    def get_agent(self, agent_id: int|str) -> dict:
        """根据复合主键获取Agent信息"""
        if agent_id == "all":
            log.info("✅ 获取所有Agent信息")
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM agents")
            return [dict(row) for row in cursor.fetchall()]
        elif type(agent_id) == int or agent_id.isdigit():
            agent_id = int(agent_id)
            log.info(f"✅ 获取Agent信息：agentId={agent_id}")
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM agents WHERE agentId = ?", (agent_id, ))
            row = cursor.fetchone()
            return dict(row) if row else None


class KnowledgeManager(DatabaseManager):
    """知识库管理"""
    def create_table(self):
        self.execute("""
            CREATE TABLE IF NOT EXISTS knowledge (
                knowledgeId INTEGER PRIMARY KEY AUTOINCREMENT,
                knowledgeName TEXT,
                embeddingModelId INTEGER,
                chunkSize INTEGER Default 256,
                chunkOverlap INTEGER Default 32,
                queryThreshold REAL Default 0.5,
                maxCount INTEGER Default 6,
                knowledgeCreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (embeddingModelId) REFERENCES models(modelId)
            )"""
        )
    
    def add_knowledge(self, **kwargs) -> int:
        knowledge_name = kwargs.get('knowledgeName')
        embedding_model_id = kwargs.get('embeddingModelId')
        chunk_size = kwargs.get('chunkSize', 256)
        chunk_overlap = kwargs.get('chunkOverlap', 32)
        query_threshold = kwargs.get('queryThreshold', 0.5)
        max_count = kwargs.get('maxCount', 8)
        
        if knowledge_name and embedding_model_id:
            """添加新知识库，返回新创建的knowledgeId"""
            cursor = self.conn.cursor()
            # 查询是否存在同名知识库，如果是返回同名知识库信息
            cursor.execute("SELECT * FROM knowledge WHERE knowledgeName =?", (knowledge_name,))
            existing_knowledge = cursor.fetchone()
            if existing_knowledge:
                log.info(f"❌ 知识库添加失败：已存在同名知识库 '{knowledge_name}'")
                return dict(existing_knowledge)
            cursor.execute(
                "INSERT INTO knowledge (knowledgeName, embeddingModelId, chunkSize, chunkOverlap, queryThreshold, maxCount) VALUES (?,?,?,?,?,?)",
                (knowledge_name, embedding_model_id, chunk_size, chunk_overlap, query_threshold, max_count)
            )
            self.conn.commit()
            log.info(f"✅ 知识库添加成功：{knowledge_name}")
            return self.get_knowledge(cursor.lastrowid)
        else:
            log.info(f"❌ 知识库添加失败：缺少必要参数['knowledge_name', 'embedding_model_id']")
            raise ValueError("知识库添加失败：缺少必要参数['knowledge_name', 'embedding_model_id']")
            return 0
    
    def delete_knowledge(self, knowledge_id: int) -> bool:
        """根据knowledgeId删除知识库"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM knowledge WHERE knowledgeId =?", (knowledge_id,))
        self.conn.commit()
        if cursor.rowcount > 0:
            log.info(f"✅ 成功删除知识库：knowledgeId={knowledge_id}")
        else:
            log.warning(f"⏩ 删除知识库失败：knowledgeId={knowledge_id} 不存在")
        return cursor.rowcount
    
    def update_knowledge(self, knowledge_id: int, **kwargs) -> bool:
        """更新知识库信息，可更新字段：knowledgeName, embeddingModelId, chunkSize, chunkOverlap, queryThreshold, maxCount"""
        allowed_fields = {'knowledgeName', 'chunkSize', 'chunkOverlap', 'queryThreshold', 'maxCount'}
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}

        cursor = self.conn.cursor()
        set_clause = ", ".join([f"{k} =?" for k in updates])
        values = list(updates.values()) + [knowledge_id]
        cursor.execute(f"UPDATE knowledge SET {set_clause} WHERE knowledgeId =?", values)
        self.conn.commit()
        log.info(f"✅ 成功更新知识库：knowledgeId={knowledge_id}")
        return self.get_knowledge(knowledge_id)
    
    def get_knowledge(self, knowledge_id: int|str) -> dict:
        """根据knowledgeId获取知识库信息"""
        if knowledge_id == "all":
            log.info("✅ 获取所有知识库信息")
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM knowledge")
            return [dict(row) for row in cursor.fetchall()]
        elif type(knowledge_id) == int or knowledge_id.isdigit():
            knowledge_id = int(knowledge_id)
            log.info(f"✅ 获取知识库信息：knowledgeId={knowledge_id}")
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM knowledge WHERE knowledgeId =?", (knowledge_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

class DocumentManager(DatabaseManager):
    """文档管理"""
    def create_table(self):
        self.execute(
            """CREATE TABLE IF NOT EXISTS documents (
                knowledgeId INTEGER,
                docId TEXT,
                fileName TEXT NOT NULL,
                fileType TEXT,
                fileHash TEXT NOT NULL,
                cachePath TEXT,
                parentId TEXT,
                segmentNum INTEGER NOT NULL,
                createdAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (knowledgeId, docId) FOREIGN KEY (knowledgeId) REFERENCES knowledge(knowledgeId)
            )"""
        )
    
    def add_document(self, **kwargs) -> int:
        knowledge_id = kwargs.get('knowledgeId')
        doc_id = kwargs.get('docId')
        file_name = kwargs.get('fileName')
        file_type = kwargs.get('fileType')
        file_hash = kwargs.get('fileHash')
        segment_num = kwargs.get('segmentNum')
        cache_path = kwargs.get('cachePath', '')
        parent_id = kwargs.get('parentId', None)
        
        if not knowledge_id or not doc_id or not file_name or not file_type or not file_hash or segment_num is None:
            log.error(f"❌ 文档添加失败：缺少必要参数['knowledge_id', 'doc_id', 'file_name', 'file_type', 'file_hash', 'segment_num']")
            raise ValueError("文档添加失败：缺少必要参数['knowledge_id', 'doc_id', 'file_name', 'file_type', 'file_hash','segment_num']")
            return 0
        """添加新文档，返回新创建的docId"""
        cursor = self.conn.cursor()
        # 判断是否已经存在
        cursor.execute("SELECT * FROM documents WHERE knowledgeId =? AND docId =?", (knowledge_id, doc_id))
        existing_document = cursor.fetchone()
        if existing_document:
            log.warning(f"⏩ 文档添加跳过：已存在同名文档 '{doc_id}'")
            return self.get_document(knowledge_id=knowledge_id, doc_id=doc_id)
        cursor.execute(
            "INSERT INTO documents (knowledgeId, docId, fileName, fileType, fileHash, segmentNum, cachePath, parentId) VALUES (?,?,?,?,?,?,?,?)",
            (knowledge_id, doc_id, file_name, file_type, file_hash, segment_num, cache_path, parent_id)
        )
        self.conn.commit()
        if cursor.lastrowid>0:
            log.info(f"✅ 文档添加成功：{doc_id}")
            return self.get_document(knowledge_id=knowledge_id, doc_id=doc_id)
        else:
            log.info(f"❌ 文档添加失败：{doc_id}")
            raise ValueError(f"文档添加失败：{doc_id}")
            return 0

    def delete_document(self, knowledge_id: int, doc_id: str) -> bool:
        if doc_id == "all":
            log.info(f"✅ 删除所有文档：knowledgeId={knowledge_id}")
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM documents WHERE knowledgeId =?", (knowledge_id,))
            self.conn.commit()
            return cursor.rowcount
        else:   
            """根据knowledgeId和docId删除文档"""
            log.info(f"✅ 删除文档：knowledgeId={knowledge_id} docId={doc_id}")
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM documents WHERE knowledgeId =? AND docId =?", (knowledge_id, doc_id))
            self.conn.commit()
            return cursor.rowcount
        
    def delete_dir_document(self, knowledge_id: int, parent_id: str) -> bool:
        """根据knowledgeId和parentId删除文档"""
        log.info(f"✅ 删除目录下所有文档：knowledgeId={knowledge_id} parentId={parent_id}")
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM documents WHERE knowledgeId =? AND parentId =?", (knowledge_id, parent_id))
        self.conn.commit()
        return cursor.rowcount
        

    def get_document(self, knowledge_id: int|str, doc_id: str|str) -> dict:
        """根据knowledgeId和docId获取文档信息"""
        if knowledge_id=="all" and doc_id == "all":
            log.info("✅ 获取所有文档信息")
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM documents")
            return [dict(row) for row in cursor.fetchall()]
        elif knowledge_id != "all" and doc_id == "all":
            log.info(f"✅ 获取知识库信息：knowledgeId={knowledge_id}")
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM documents WHERE knowledgeId =?", (knowledge_id,))
            return [dict(row) for row in cursor.fetchall()]
        else:
            cursor = self.conn.cursor()
            if knowledge_id == "all":
                log.info(f"✅ 获取文档信息：docId={doc_id}")
                cursor.execute("SELECT * FROM documents WHERE docId =? LIMIT 1", (doc_id,))
            else:
                log.info(f"✅ 获取文档信息：knowledgeId={knowledge_id} docId={doc_id}")
                cursor.execute("SELECT * FROM documents WHERE knowledgeId =? AND docId =?", (knowledge_id, doc_id))
            row = cursor.fetchone()
            return dict(row) if row else None
        
class EmbeddingManager(DatabaseManager):
    """嵌入管理"""
    def create_table(self, embedding_length=1024):
        self.execute("""
            CREATE TABLE IF NOT EXISTS embeddings (
                embeddingId INTEGER PRIMARY KEY AUTOINCREMENT,
                knowledgeId INTEGER,
                docId TEXT,
                segmentIndex INTEGER,
                textContent TEXT,
                embeddingData F32_BLOB ({ll}),
                metaData TEXT,
                FOREIGN KEY (knowledgeId, docId) REFERENCES documents(knowledgeId, docId)
            )""".format(ll = embedding_length)
        )
        
    def add_embeddings(self, knowledge_id, doc_id, text_list, embedding_list, metadata_list):
        cursor = self.conn.cursor()
        # 判断 doc_id 是否已经存在，如果存在则删除之前的，用新的内容覆盖
        cursor.execute("""DELETE FROM embeddings WHERE docId = ? AND knowledgeId = ?""", (doc_id, knowledge_id))
        # 添加列名指定和序列化处理
        assert len(text_list) == len(embedding_list) == len(metadata_list)
        for i in range(len(text_list)):
            text = text_list[i]
            embedding = embedding_list[i]
            metadata = metadata_list[i]
            if type(embedding) == list:
                embedding = sqlite3.Binary(struct.pack(f'{len(embedding)}f', *embedding))
            
            serialized_metadata = json.dumps(metadata)
            # 在插入语句中添加database字段
            cursor.execute("""INSERT INTO embeddings 
                (knowledgeId, docId, segmentIndex, textContent, embeddingData, metaData)
                VALUES (?, ?, ?, ?, ?, ?)""", 
                (knowledge_id, doc_id, i, text, embedding,
                    # sqlite3.Binary(struct.pack(f'{len(embedding)}f', *embedding)), 
                    serialized_metadata))
            if (i+1) % 200 == 0:
                self.conn.commit()
        self.conn.commit()        
        log.info(f"✅ 添加嵌入成功：{len(text_list)}")
        return len(text_list)


    def delete_embedding(self, knowledge_id, doc_id):
        cursor = self.conn.cursor()
        if doc_id == "all":
            log.info(f"✅ 删除所有嵌入：knowledgeId={knowledge_id}")
            cursor.execute("DELETE FROM embeddings WHERE knowledgeId =?", (knowledge_id,))
            self.conn.commit()
            return cursor.rowcount
        else:
            log.info(f"✅ 删除嵌入：knowledgeId={knowledge_id} docId={doc_id}")
            cursor.execute("""DELETE FROM embeddings WHERE docId =? AND knowledgeId =?""", (doc_id, knowledge_id))
            self.conn.commit()
            return cursor.rowcount
    
    def delete_dir_embedding(self, knowledge_id, doc_ids):
        cursor = self.conn.cursor()
        log.info(f"✅ 删除嵌入：knowledgeId={knowledge_id} docIds={doc_ids}")
        cursor.execute("""DELETE FROM embeddings WHERE knowledgeId =? AND docId IN ({})""".format(','.join(['?']*len(doc_ids))), (knowledge_id, *doc_ids))
        self.conn.commit()
        return cursor.rowcount
        
    def get_embedding(self, knowledge_id, doc_id):
        cursor = self.conn.cursor()
        if doc_id == "all":
            log.info(f"✅ 获取所有嵌入：knowledgeId={knowledge_id}")
            cursor.execute("SELECT * FROM embeddings WHERE knowledgeId =?", (knowledge_id,))
            return [dict(row) for row in cursor.fetchall()]
        else:
            log.info(f"✅ 获取嵌入：knowledgeId={knowledge_id} docId={doc_id}")
            cursor.execute("""SELECT * FROM embeddings WHERE docId =? AND knowledgeId =?""", (doc_id, knowledge_id))
            return [dict(row) for row in cursor.fetchall()]

class SessionoManager(DatabaseManager):
    """会话管理"""
    def create_table(self):
        self.execute("""
            CREATE TABLE IF NOT EXISTS session (
                sessionId INTEGER PRIMARY KEY AUTOINCREMENT,
                sessionName TEXT,
                agentId INTEGER,
                chatModelId INTEGER,
                chatParams TEXT,
                createdTime TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        self.conn.commit()
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM session WHERE sessionName = '默认会话'"
        )
        self.conn.commit()
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO session (sessionName) VALUES (?)", 
                ("默认会话",)
            )
            self.conn.commit()
            log.info(f"✅ 默认会话添加成功：默认会话")
    
    def add_session(self, **kwargs) -> int:
        session_name = kwargs.get('sessionName')
        agent_id = kwargs.get('agentId')
        model_id = kwargs.get('chatModelId', "")   # chat model
        chat_params = kwargs.get('chatParams', "")  
        cursor = self.conn.cursor()
        if session_name and agent_id:
            """添加新会话，返回新创建的sessionId"""
            cursor.execute(
                "INSERT INTO session (sessionName, agentId, chatModelId, chatParams) VALUES (?,?,?,?)",
                (session_name, agent_id, model_id, chat_params)
            )
            self.conn.commit()
            log.info(f"✅ 会话添加成功：{session_name}")
            return self.get_session(cursor.lastrowid)
        else:
            log.error(f"❌ 会话添加失败：缺少必要参数['session_name', 'agent_id', 'model_id']")
            raise ValueError("缺少必要参数['session_name', 'agent_id', 'model_id']")
            return 0
        
    
    def delete_session(self, session_id: int) -> bool:
        """根据sessionId删除会话"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM session WHERE sessionId =?", (session_id,))
        self.conn.commit()
        if cursor.rowcount > 0:
            log.info(f"✅ 成功删除会话：sessionId={session_id}")
        else:
            log.warning(f"⏩ 删除会话失败：sessionId={session_id} 不存在")
        return cursor.rowcount

    def update_session(self, session_id: int, **kwargs) -> bool:
        """更新会话信息，可更新字段：sessionName, agentId, chatModelId, chatParams"""
        allowed_fields = {'sessionName', 'agentId', 'chatModelId', 'chatParams'}
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}

        cursor = self.conn.cursor()
        set_clause = ", ".join([f"{k} =?" for k in updates])
        values = list(updates.values()) + [session_id]
        cursor.execute(f"UPDATE session SET {set_clause} WHERE sessionId =?", values)
        self.conn.commit()
        log.info(f"✅ 成功更新会话：sessionId={session_id}")
        return self.get_session(session_id)
    
    def get_session(self, session_id: int|str) -> dict:
        """根据sessionId获取会话信息"""
        if session_id == "all":
            log.info("✅ 获取所有会话信息")
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM session")
            return [dict(row) for row in cursor.fetchall()]
        elif type(session_id) == int or session_id.isdigit():
            session_id = int(session_id)
            log.info(f"✅ 获取会话信息：sessionId={session_id}")
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM session WHERE sessionId =?", (session_id,))
            row = cursor.fetchone()
            return dict(row) if row else None


class HistortManager(DatabaseManager):
    """历史对话消息管理"""
    def create_table(self):
        self.execute("""
            CREATE TABLE IF NOT EXISTS history (
                historyId INTEGER PRIMARY KEY AUTOINCREMENT,
                sessionId INTEGER,
                singleMessage TEXT,
                answerMeta TEXT,
                lastTime TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                createdTime TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()
        
    def add_history(self, **kwargs) -> int:
        """添加会话信息"""
        session_id = kwargs.get('sessionId')
        single_message = kwargs.get('singleMessage')
        answer_meta = kwargs.get('answerMeta')
        last_time = kwargs.get('lastTime', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        if session_id and single_message:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO history (sessionId, singleMessage, answerMeta, lastTime) VALUES (?,?,?,?)",
                (session_id, single_message, answer_meta, last_time)
            )
            self.conn.commit()
            log.info(f"✅ 历史对话添加成功：sessionId={session_id}")
            return self.get_history(session_id=session_id, history_id=cursor.lastrowid)
        else:
            log.info(f"❌ 历史对话添加失败：缺少必要参数['session_id', 'single_message']")
            raise ValueError("缺少必要参数['session_id','single_message']")
            return 0
    
    def delete_history(self, history_id: int) -> bool:
        """根据historyId删除历史对话"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM history WHERE historyId =?", (history_id,))
        self.conn.commit()
        if cursor.rowcount > 0:
            log.info(f"✅ 成功删除历史对话：historyId={history_id}")
        else:
            log.warning(f"⏩ 删除历史对话失败：historyId={history_id} 不存在")
        return cursor.rowcount

    def update_history(self, history_id: int, **kwargs) -> bool:
        """更新历史对话信息，可更新字段：sessionId, singleMessage, answerMeta, lastTime"""
        allowed_fields = {'sessionId', 'singleMessage', 'answerMeta', 'lastTime'}
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        cursor = self.conn.cursor()
        set_clause = ", ".join([f"{k} =?" for k in updates])
        values = list(updates.values()) + [history_id]
        cursor.execute(f"UPDATE history SET {set_clause} WHERE historyId =?", values)
        self.conn.commit()
        log.info(f"✅ 成功更新历史对话：historyId={history_id}")
        return self.get_history(history_id)
        

    def get_history(self, session_id: int|str, history_id: int|str, show_count=10, last_time=None) -> dict:
        """根据sessionId和historyId获取历史对话信息"""
        if session_id == "all" and history_id == "all":
            log.info("✅ 获取所有历史对话信息")
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM history")
            return [dict(row) for row in cursor.fetchall()]
        elif type(session_id) == int or session_id.isdigit():
            session_id = int(session_id)
            if type(history_id) == int or history_id.isdigit():
                history_id = int(history_id)
                log.info(f"✅ 获取历史对话信息：sessionId={session_id} historyId={history_id}")
                cursor = self.conn.cursor()
                cursor.execute("SELECT * FROM history WHERE sessionId =? AND historyId =?", (session_id, history_id))
                row = cursor.fetchone()
                return dict(row) if row else None
            else:
                if last_time:
                    log.info(f"✅ 获取last_time={last_time}之前的 top{show_count} 条历史对话信息：sessionId={session_id}")
                    cursor = self.conn.cursor()
                    cursor.execute("SELECT * FROM history WHERE sessionId =? AND lastTime < ? ORDER BY lastTime DESC LIMIT ?", (session_id, last_time, show_count))
                    return sorted([dict(row) for row in cursor.fetchall()], key=lambda x: x['lastTime'])
                else:
                    log.info(f"✅ 获取 top{show_count} 条历史对话信息：sessionId={session_id}")
                    cursor = self.conn.cursor()
                    cursor.execute("SELECT * FROM history WHERE sessionId =? ORDER BY lastTime DESC LIMIT ?", (session_id, show_count))
                    return sorted([dict(row) for row in cursor.fetchall()], key=lambda x: x['lastTime'])
        else:
            log.info(f"❌ 获取历史对话信息失败：缺少必要参数['session_id', 'history_id']")
            raise ValueError("session_id and history_id must be int or str")
            return 0
    
    def clear_history(self, session_id: int) -> bool:
        """根据sessionId清空历史对话"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM history WHERE sessionId =?", (session_id,))
        self.conn.commit()
        if cursor.rowcount > 0:
            log.info(f"✅ 成功清空历史对话：sessionId={session_id}")
        else:
            log.warning(f"⏩ 清空历史对话失败：sessionId={session_id} 不存在")
        return cursor.rowcount


class MCPManager(DatabaseManager):
    """MCP管理"""
    def create_table(self):
        self.execute("""
            CREATE TABLE IF NOT EXISTS mcp (
                mcpId INTEGER PRIMARY KEY AUTOINCREMENT,
                mcpUid TEXT UNIQUE,
                mcpName TEXT,
                mcpType TEXT,
                mcpActivate boolean DEFAULT 0,
                mcpDescription TEXT,
                mcpBaseUrl TEXT,
                mcpHeaders TEXT,
                mcpCommand TEXT,
                mcpRegistryUrl TEXT,
                mcpArgs TEXT,
                mcpEnvs TEXT,
                mcpCreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()
        
    def generate_uid(self) -> str:
        """
        Generate a 22-character unique identifier (UID) based on the current time and UUID.

        Returns:
            str: A 22-character UID.
        """
        #  Generate a UUID based on the current time and Convert the UUID to bytes
        uid = uuid.uuid1()  # UUID version 1 (based on timestamp and MAC address)
        uid_bytes = uid.bytes

        # Encode the bytes using URL-safe Base64 encoding
        uid_base64 = base64.urlsafe_b64encode(uid_bytes).decode("utf-8")
        return uid_base64.rstrip("=")[:21]
    
    def add_mcp(self, **kwargs) -> int:
        """添加MCP信息"""
        # uid 默认16位的uid，根据当前时间通过uuid配置生成
        mcp_uid = kwargs.get('mcpUid', self.generate_uid())
        # 查询uid是否存在
        query_res = self.get_mcp(mcp_uid)
        if query_res:
            log.info(f"MCPmcpUid={mcp_uid} 已存在， 在上面修改")
            # 可更新字段：mcpName, mcpType, mcpActivate, mcpDescription, mcpBaseUrl, 
            # mcpHeaders, mcpCommand, mcpRegistryUrl, mcpArgs, mcpEnvs
            allowed_fields = {'mcpName', 'mcpType', 'mcpActivate', 'mcpDescription', 'mcpBaseUrl',
                'mcpHeaders','mcpCommand','mcpRegistryUrl','mcpArgs','mcpEnvs'}
            updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
            if 'mcpRegistryUrl' in updates and updates['mcpRegistryUrl'] and updates['mcpRegistryUrl'] in configs.registryUrl:
                updates['mcpRegistryUrl'] = configs.registryUrl.get(updates['mcpRegistryUrl'], "")
            cursor = self.conn.cursor()
            set_clause = ", ".join([f"{k} =?" for k in updates])
            values = list(updates.values()) + [mcp_uid]
            cursor.execute(f"UPDATE mcp SET {set_clause} WHERE mcpUid =?", values)
            self.conn.commit()
            log.info(f"✅ 成功更新mcp信息：mcp_uid={mcp_uid}")
            return self.get_mcp(mcp_uid)
        else:
            # insert 对应字段
            allowed_fields = {'mcpUid', 'mcpName', 'mcpType', 'mcpActivate', 'mcpDescription', 'mcpBaseUrl',
                'mcpHeaders','mcpCommand','mcpRegistryUrl','mcpArgs','mcpEnvs'}
            inserts = {k: v for k, v in kwargs.items() if k in allowed_fields}
            if 'mcpRegistryUrl' in inserts and inserts['mcpRegistryUrl'] and inserts['mcpRegistryUrl'] in configs.registryUrl:
                inserts['mcpRegistryUrl'] = configs.registryUrl.get(inserts['mcpRegistryUrl'], "")
            inserts['mcpUid'] = mcp_uid
            cursor = self.conn.cursor()
            set_clause = ", ".join([f"{k}" for k in inserts])
            values = list(inserts.values())
            cursor.execute(f"INSERT INTO mcp ({set_clause}) VALUES ({','.join(['?']*len(values))})", values)
            self.conn.commit()
            log.info(f"✅ 成功添加mcp信息：mcp_uid={mcp_uid}")
            return self.get_mcp(mcp_uid)
    
    def delete_mcp(self, mcp_uid: str) -> bool:
        cursor = self.conn.cursor()
        # 查询是否有mcpUid对应的数据
        cursor.execute("SELECT * FROM mcp WHERE mcpUid =?", (mcp_uid,))
        if not cursor.fetchone():
            log.warning(f"⏩ 删除mcp失败：mcpUid={mcp_uid} 不存在")
            return 0
        cursor.execute("DELETE FROM mcp WHERE mcpUid =?", (mcp_uid,))
        self.conn.commit()
        if cursor.rowcount > 0:
            log.info(f"✅ 成功删除mcp信息：mcpUid={mcp_uid}")
        else:
            log.warning(f"⏩ 删除mcp失败：mcpUid={mcp_uid} 不存在")
        return cursor.rowcount
        
    def update_json_file(self, file_path):
        try:
            query_result = self.get_mcp(mcp_uid="all")
            mcp_data = {"mcpServers": {}}
            for item in query_result:
                new_item = {}
                if item['mcpType'] == "sse":
                    # 保留的字段：mcpUid, mcpName, mcpType, mcpActivate, mcpDescription, mcpBaseUrl,mcpHeaders
                    keep_fields = ['mcpName', 'mcpType', 'mcpActivate', 'mcpDescription', 'mcpBaseUrl','mcpHeaders']
                    new_item = {k: v for k, v in item.items() if k in keep_fields}
                    if new_item.get('mcpHeaders'):
                        try:
                            new_item['mcpHeaders'] = json.loads(item['mcpHeaders'])
                        except:
                            new_item['mcpHeaders'] = dict(pair.strip().split("=", 1) for pair in item['mcpHeaders'].split("\n") if "=" in pair)
                    mcp_data['mcpServers'][item['mcpUid']] = new_item
                elif item['mcpType'] == "stdio":
                    # 保留字段：mcpUid, mcpName, mcpType, mcpActivate, mcpDescription, mcpCommand, mcpRegistryUrl, mcpArgs, mcpEnvs
                    keep_fields = ['mcpName','mcpType','mcpActivate','mcpDescription','mcpCommand','mcpRegistryUrl','mcpArgs','mcpEnvs']
                    new_item = {k: v for k, v in item.items() if k in keep_fields}
                    if new_item.get('mcpArgs'):
                        try:
                            new_item['mcpArgs'] = json.loads(item['mcpArgs'])
                        except:
                            new_item['mcpArgs'] = [s.strip() for s in item['mcpArgs'].split("\n")]
                    if new_item.get('mcpEnvs'):
                        try:
                            new_item['mcpEnvs'] = json.loads(new_item['mcpEnvs'])
                        except:
                            new_item['mcpEnvs'] = dict(pair.strip().split("=", 1) for pair in new_item['mcpEnvs'].split("\n") if "=" in pair)
                    mcp_data['mcpServers'][item['mcpUid']] = new_item
                else:
                    pass
                mcp_data['mcpActivate'] = bool(new_item.get('mcpActivate', False))
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(mcp_data, f, ensure_ascii=False, indent=4)
                log.info(f"✅ 成功更新mcp配置文件：{file_path}")
            return self.get_mcp(mcp_uid="all")
        except Exception as e:
            log.error(f"❌ 更新mcp配置文件失败：{e}")
            raise e
            
    def update_from_json(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                mcp_data = json.load(f)
            # 更新文件
            if list(mcp_data) != ['mcpServers']:
                log.error(f"❌ {file_path} mcp配置文件格式错误")
                raise ValueError("mcp配置文件格式错误")
            mcp_uid_list = list(mcp_data['mcpServers'].keys())
            # 删除数据库中所有不在mcp_uid_list的mcp信息
            all_mcp = self.get_mcp(mcp_uid="all")
            del_mcp_uid = [item['mcpUid'] for item in all_mcp if item['mcpUid'] not in mcp_uid_list]
            for mcp_uid in del_mcp_uid:
                self.delete_mcp(mcp_uid)
            log.info(f"✅ 成功删除mcp多余的信息成功：{del_mcp_uid}")
            # 剩下的mcp信息更新到数据库
            for mcp_uid, mcp_info in mcp_data['mcpServers'].items():
                if mcp_info['mcpType'] == "sse":
                    # 保留的字段：mcpUid, mcpName, mcpType, mcpActivate, mcpDescription, mcpBaseUrl,mcpHeaders
                    keep_fields = ['mcpUid', 'mcpName','mcpType','mcpActivate','mcpDescription','mcpBaseUrl','mcpHeaders']
                    other_fields = ['mcpCommand','mcpRegistryUrl','mcpArgs','mcpEnvs']
                    new_item = {k: v for k, v in mcp_info.items() if k in keep_fields}
                    new_item = {**new_item, **{k: None for k in other_fields}}
                    new_item['mcpHeaders'] = json.dumps(new_item['mcpHeaders']) if new_item.get('mcpHeaders') else "{}"
                    self.add_mcp(**new_item)
                elif mcp_info['mcpType'] == "stdio":
                    # 保留字段：mcpUid, mcpName, mcpType, mcpActivate, mcpDescription, mcpCommand, mcpRegistryUrl, mcpArgs, mcpEnvs
                    keep_fields = ['mcpUid','mcpName','mcpType','mcpActivate','mcpDescription','mcpCommand','mcpRegistryUrl','mcpArgs','mcpEnvs']
                    other_fields = ['mcpBaseUrl','mcpHeaders']
                    new_item = {k: v for k, v in mcp_info.items() if k in keep_fields}
                    new_item = {**new_item, **{k: None for k in other_fields}}
                    if 'mcpRegistryUrl' in new_item and mcp_info['mcpRegistryUrl'] and mcp_info['mcpRegistryUrl'] in configs.registryUrl:
                        new_item['mcpRegistryUrl'] = configs.registryUrl.get(new_item['mcpRegistryUrl'], "")
                    new_item['mcpArgs'] = json.dumps(new_item['mcpArgs']) if new_item.get('mcpArgs') else "[]"
                    new_item['mcpEnvs'] = json.dumps(new_item['mcpEnvs']) if new_item.get('mcpEnvs') else "{}"
                    self.add_mcp(**new_item)
                else:
                    pass
            log.info(f"✅ 成功更新mcp数据库信息：{file_path}")
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(mcp_data, f, ensure_ascii=False, indent=4)
                log.info("JSON file has been cleaned and updated successfully.")
            return self.get_mcp(mcp_uid="all")
        except Exception as e:
            log.error(f"❌ 更新mcp数据库信息失败：{e}")
            raise e
            
    def get_mcp(self, mcp_uid:str) -> dict:
        """根据mcpId获取MCP信息"""
        if mcp_uid == "all":
            log.info("✅ 获取所有MCP信息")
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM mcp")
            return [dict(row) for row in cursor.fetchall()]
        else:
            log.info(f"✅ 获取MCP信息：mcpUid={mcp_uid}")
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM mcp WHERE mcpUid =?", (mcp_uid,))
            row = cursor.fetchone()
            return dict(row) if row else None
        
        