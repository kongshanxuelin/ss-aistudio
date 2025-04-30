import shutil
import os, sys
import sqlite3
import struct # type: ignore
import logging as log
base_path = os.path.join(os.path.dirname(__file__), "../../")
sys.path.append(base_path)
from src.database.base_manager import (DocumentManager, EmbeddingManager, KnowledgeManager, 
                                       ModelManager, ServerManager, AgentManager, 
                                       SessionoManager, HistortManager, MCPManager
                                       )
config_path = os.path.join(base_path, 'configs')

class EmbeddingStorage():
    def __init__(self, user_name, db_path, embedding_length=1024):
        os.makedirs(db_path, exist_ok=True)
        # 固定数据库文件名
        self.db_path = db_path
        self.conn = sqlite3.connect(os.path.join(db_path, f"{user_name}.db"))
        self.embedding_length = embedding_length
        self.server_manager = ServerManager(self.conn)
        self.model_manager = ModelManager(self.conn)
        self.agent_manager = AgentManager(self.conn)
        self.knowledge_manager = KnowledgeManager(self.conn)
        self.document_manager = DocumentManager(self.conn)
        self.embedding_manager = EmbeddingManager(self.conn)
        self.session_manager = SessionoManager(self.conn)
        self.history_manager = HistortManager(self.conn)
        self.mcp_manager = MCPManager(self.conn)
        
    def _create_tables(self): 
        self.server_manager.create_table()
        self.model_manager.create_table()
        self.agent_manager.create_table()
        self.knowledge_manager.create_table()
        self.document_manager.create_table()
        self.embedding_manager.create_table(self.embedding_length)
        self.session_manager.create_table()
        self.history_manager.create_table()
        self.mcp_manager.create_table()
        log.info("Tables created successfully.")
        
        # self.insert_defaults()
        log.info("Default data inserted successfully.")

    def insert_defaults(self):
        self.server_manager.insert_defaults()
        self.model_manager.insert_defaults()
        self.agent_manager.insert_defaults()

    def process_manager(self, table, fun, **kwargs):
        log.info(f"process_manager: table:`{table}` fun:`{fun}` kwargs:`{kwargs}`")
        if table == "server":
            if fun == "add":
                return self.server_manager.add_server(**kwargs)
            elif fun == "get":
                return self.server_manager.get_server(kwargs['serverId'])
            elif fun == "update":
                return self.server_manager.update_server(kwargs['serverId'], **kwargs)
            elif fun == "delete":
                return self.server_manager.delete_server(kwargs['serverId'])
        elif table == "model":
            if fun == "add":
                return self.model_manager.add_model(**kwargs)
            elif fun == "get":
                return self.model_manager.get_model(kwargs['serverId'], kwargs['modelId'])
            elif fun == "get_default":
                return self.model_manager.get_default_model(kwargs['embeddingModel'])
            elif fun == "update_default":
                return self.model_manager.update_default_model(kwargs['modelId'])
            elif fun == "delete":
                return self.model_manager.delete_model(kwargs['modelId'])
        elif table == "agent":
            if fun == "add":
                return self.agent_manager.add_agent(**kwargs)
            elif fun == "get":
                return self.agent_manager.get_agent(kwargs['agentId'])
            elif fun == "update":
                return self.agent_manager.update_agent(kwargs['agentId'], **kwargs)
            elif fun == "delete":
                return self.agent_manager.delete_agent(kwargs['agentId'])
        elif table == "knowledge":
            if fun == "add":
                return self.knowledge_manager.add_knowledge(**kwargs)
            elif fun == "get":
                return self.knowledge_manager.get_knowledge(kwargs['knowledgeId'])
            elif fun == "update":
                return self.knowledge_manager.update_knowledge(kwargs['knowledgeId'], **kwargs)
            elif fun == "delete":
                log.info("⏩ use delete_knowledge")
                return self.delete_kwowledge(kwargs['knowledgeId'])
                
        elif table == "document":
            if fun == "add":
                return self.document_manager.add_document(**kwargs)
            elif fun == "get":
                return self.document_manager.get_document(kwargs['knowledgeId'], kwargs['docId'])
            elif fun == "update":
                log.info("❌ document not support update")
            elif fun == "delete":
                log.info("⏩ use delete_document")
                return self.delete_document(kwargs['knowledgeId'], kwargs['docId'])
        elif table == "embedding":
            if fun == "get":
                return self.embedding_manager.get_embedding(kwargs['knowledgeId'], kwargs['docId'])
        elif table == "session":
            if fun == "add":
                return self.session_manager.add_session(**kwargs)
            elif fun == "get":
                return self.session_manager.get_session(kwargs['sessionId'])
            elif fun == "update":
                return self.session_manager.update_session(kwargs['sessionId'], **kwargs)
            elif fun == "delete":
                return self.session_manager.delete_session(kwargs['sessionId'])
        elif table == "history":
            if fun == "add":
                return self.history_manager.add_history(**kwargs)
            elif fun == "get":
                return self.history_manager.get_history(kwargs['sessionId'], kwargs.get('historyId',"all"), show_count=kwargs.get('show_count',10), last_time=kwargs.get('last_time',None))
            elif fun == "update":
                # 不建议修改
                # return self.history_manager.update_history(kwargs['historyId'], **kwargs)
                log.info("❌ history not support update")
            elif fun == "delete":
                return self.history_manager.delete_history(kwargs['historyId'])
            elif fun == "clear":
                return self.history_manager.clear_history(kwargs['sessionId'])
        elif table == "mcp":
            if fun == "add":
                return self.mcp_manager.add_mcp(**kwargs)
            elif fun == "get":
                return self.mcp_manager.get_mcp(kwargs.get('mcpUid', 'all'))
            elif fun == "update_form_json":
                return self.mcp_manager.update_from_json(kwargs['file_path'])
            elif fun == "update_json_file":
                return self.mcp_manager.update_json_file(kwargs['file_path'])
            elif fun == "update":
                return self.mcp_manager.add_mcp(**kwargs)
            elif fun == "delete":
                return self.mcp_manager.delete_mcp(kwargs['mcpUid'])
            
            

    def save_embedding(self, knowledge_id, doc_id, text_list, embedding_list, metadata_list):
        try:
            res = self.embedding_manager.add_embeddings(knowledge_id, doc_id, text_list, embedding_list, metadata_list)
            log.info(f"✅ 成功插入{len(text_list)}条嵌入数据，DB:{knowledge_id}, 文档ID：{doc_id}")
            return res
        except sqlite3.Error as e:
            log.error(f"❌ 插入嵌入数据失败：{str(e)}")
            return 0

    def save_document(self, knowledge_id, doc_id, file_name, file_type, file_hash, segment_num, cache_path='', parent_id=None):
        try:
            # 新增重复性检查
            if self.get_document_by_hash(knowledge_id, file_name, file_hash):
                log.info(f"⏩ DB:{knowledge_id},文档{file_name}已存在，更新数据。Hash：{file_hash}")
                # 删除数据
                self.delete_document(knowledge_id, doc_id)

            # 明确指定插入列（排除自动生成的 created_at）
            result = self.document_manager.add_document(knowledgeId=knowledge_id, docId=doc_id, fileName=file_name, 
                                               fileType=file_type, fileHash=file_hash, segmentNum=segment_num,
                                               cachePath=cache_path, parentId=parent_id)
            log.info(f"✅ 成功保存文档 {file_name}，DB: {knowledge_id}, ID：{doc_id}")
            return result
        except sqlite3.Error as e:
            log.error(f"❌ 保存文档失败：{str(e)}")
            return 0
    
    def delete_kwowledge(self, knowledge_id: str) -> bool:
        """删除指定知识库"""
        try:
            knowledge_dir = os.path.join(self.db_path, "tmpFile", str(knowledge_id))
            if os.path.exists(knowledge_dir):
                shutil.rmtree(knowledge_dir)
            res1 = self.embedding_manager.delete_embedding(knowledge_id, doc_id="all")
            log.info(f"删除知识库：{knowledge_id} 相关向量， result： 删除 {res1} 条数据")
            res2 = self.document_manager.delete_document(knowledge_id, doc_id="all")
            log.info(f"删除知识库：{knowledge_id} 相关文档， result： 删除 {res2} 条数据")
            res3 = self.knowledge_manager.delete_knowledge(knowledge_id)
            log.info(f"删除知识库：{knowledge_id} 相关信息， result： 删除 {res3} 条数据")
            return res1 or res2 or res3
        except sqlite3.Error as e:
            self.conn.rollback()
            log.error(f"❌ 删除知识库失败：{str(e)}")
            return False
    
    def delete_document(self, knowledge_id: str, doc_id: str) -> bool:
        """删除指定文档"""
        try:
            res1 = self.embedding_manager.delete_embedding(knowledge_id, doc_id=doc_id)
            log.info(f"删除知识库：{knowledge_id} 中文档：{doc_id} 相关向量， result： 删除 {res1} 条数据")
            res2 = self.document_manager.delete_document(knowledge_id, doc_id=doc_id)
            log.info(f"删除知识库：{knowledge_id} 中文档：{doc_id} 相关文档， result： 删除 {res2} 条数据")
            # return res1 or res2
            return res2
        except sqlite3.Error as e:
            self.conn.rollback()
            log.error(f"❌ 删除文档失败：{str(e)}")
            return False
    
    def delete_dir_document(self, knowledge_id: str, parent_id: str) -> bool:
        """删除指定目录下的所有文档"""
        try:
            # 获取 document 下 parent_id 对应的所有 docid
            doc_infos = self.get_dir_document(knowledge_id, parent_id)
            doc_ids = [doc_info['docId'] for doc_info in doc_infos]
            log.info(f"删除知识库：{knowledge_id} 目录：{parent_id} 相关文档， doc_ids： {doc_ids}")
            res1 = self.embedding_manager.delete_dir_embedding(knowledge_id, doc_ids)
            log.info(f"删除知识库：{knowledge_id} 目录：{parent_id} 相关向量， result： 删除 {res1} 条数据")
            res2 = self.document_manager.delete_dir_document(knowledge_id, parent_id)
            log.info(f"删除知识库：{knowledge_id} 目录：{parent_id} 相关文档， result： 删除 {res2} 条数据")
            # return res1 or res2
            return res2
        except sqlite3.Error as e:
            self.conn.rollback()
            log.error(f"❌ 删除目录下的文档失败：{str(e)}")
            return False
    
        
    def get_all_embeddings(self, dbs: list[str]):
        """从数据库读取所有嵌入数据并反序列化"""
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                SELECT docId, textContent, embeddingData
                FROM embeddings WHERE knowledgeId in ({knowledgeIds})
            """.format(knowledgeIds=','.join([f"{d}" for d in dbs])))
            # 使用struct解包二进制数据
            log.info(f"✅ 成功读取嵌入数据，DB:{dbs}")
            return [[row[0],row[1],list(struct.unpack(f'{self.embedding_length}f', row[2]))] 
                    for row in cursor.fetchall()]
        except sqlite3.Error as e:
            log.error(f"❌ 读取嵌入数据失败：{str(e)}")
            return []

    def get_document_by_hash(self, knowledge_id, file_name, file_hash):
        cursor = self.conn.cursor()
        # 在查询条件中添加database字段
        cursor.execute("""SELECT * FROM documents WHERE knowledgeId = ? AND fileName = ? AND fileHash = ?""", 
                    (knowledge_id, file_name, file_hash))
        log.info(f"✅ 成功读取文档，DB:{knowledge_id}, name: {file_name}, Hash：{file_hash}")
        return cursor.fetchone()
    
    def get_dir_document(self, knowledge_id, parent_id):
        # 获取所有文档信息
        cursor = self.conn.cursor()
        # 在查询条件中添加database字段
        cursor.execute("""SELECT * FROM documents WHERE knowledgeId =? AND parentId =?""",
                    (knowledge_id, parent_id))
        log.info(f"✅ 成功读取文档，DB:{knowledge_id}, parent_id: {parent_id}")
        return [dict(row) for row in cursor.fetchall()]
    
    
    def close(self):
        log.info("关闭数据库连接")
        self.conn.close()
    

if __name__ == "__main__":
    pass
    