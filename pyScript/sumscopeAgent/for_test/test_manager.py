import os
import sys
import json
import time # type: ignore
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
sys.path.append(base_dir)
# from src.database.database_manager import EmbeddingStorage
from query_service import *

# 原有命令处理...
print("🚀 开始测试数据库...")

# 测试数据库创建
test_db_name = "test0"
test_db_path = os.path.join(base_dir, "./db_date")
user_name = 'testuser'

# 测试增删改查 
# storage = EmbeddingStorage(user_name, test_db_path, 1024)
default_db_config = {
    'user_name': user_name,
    'db_path': test_db_path,
}
# 测试添加服务器
def test_add_server():
    print("💻 测试添加服务器...")
    server_data = {
        "serverName": "测试服务器",
        "serverBaseUrl": "127.0.0.1"
    }
    print(f"输入数据: {server_data}")
    # result = storage.process_manager("server", "add", **server_data)
    result = add_server(json.dumps({**server_data, **default_db_config}, ensure_ascii=False))
    print(f"输出结果: {result}")
    if json.loads(result)['status']=='success': 
        print("✅ 添加服务器成功")
    else:
        print("❌ 添加服务器失败")
    return result

# 测试获取服务器
def test_get_server(server_id):
    print("💻 测试获取服务器...")
    # result = storage.process_manager("server", "get", serverId=server_id)
    # print(f"输入参数 server_id: {server_id}")
    # print(f"输出结果: {result}")
    
    server_id = "all"
    # result = storage.process_manager("server", "get", serverId=server_id)
    result = query_server(json.dumps({"serverId": server_id}|default_db_config, ensure_ascii=False))
    print(f"输入参数 server_id: {server_id}")
    print(f"输出结果: {result}")
    if json.loads(result)['status']=='success':
        print("✅ 获取服务器成功")
    else:
        print("❌ 获取服务器失败")

# 测试更新服务器
def test_update_server(server_id):
    print("💻 测试更新服务器...")
    updated_data = {
        "serverName": "更新后的服务器名称",
        "serverBaseUrl": "127.0.0.2",
        "serverId": server_id,
    }
    print(f"输入数据: {updated_data}, server_id: {server_id}")
    # result = storage.process_manager("server", "update", serverId=server_id, **updated_data)
    result = update_server(json.dumps(updated_data|default_db_config, ensure_ascii=False))
    print(f"输出结果: {result}")
    if json.loads(result)['status']=='success':
        print("✅ 更新服务器成功")
    else:
        print("❌ 更新服务器失败")

# 测试删除服务器
def test_delete_server(server_id):
    print("💻 测试删除服务器...")
    delete_data = {
        "serverId": server_id
    }
    # result = storage.process_manager("server", "delete", serverId=server_id)
    result = delete_server(json.dumps(delete_data|default_db_config, ensure_ascii=False))
    print(f"输入参数 server_id: {server_id}")
    print(f"输出结果: {result}")
    if json.loads(result)['status']=='success':
        print("✅ 删除服务器成功")
    else:
        print("❌ 删除服务器失败")

# 测试添加模型
def test_add_model():
    print("📦 测试添加模型...")
    model_data = {
        "modelName": "测试模型",
        "serverId": 1
    }
    print(f"输入数据: {model_data}")
    # result = storage.process_manager("model", "add", **model_data)
    result = add_model(json.dumps(model_data|default_db_config, ensure_ascii=False))
    print(f"输出结果: {result}")
    if json.loads(result)['status']=='success':
        print("✅ 添加模型成功")
    else:
        print("❌ 添加模型失败")
    return result

# 测试获取模型
def test_get_model(model_id):
    print("📦 测试获取模型...")
    # get_params = {
    #     "serverId": "all",
    #     "modelId": model_id
    # }
    # result = storage.process_manager("model", "get", **get_params)
    # print(f"输入参数 server_id:{'all'}, model_id: {model_id}")
    # print(f"输出结果: {result}")
    
    # get_params = {
    #     "serverId": "all",
    #     "modelId": "all" 
    # }
    # result = storage.process_manager("model", "get", **get_params)
    # print(f"输入参数 server_id:{'all'}, model_id: {'all'}")
    # print(f"输出结果: {result}")
    
    get_params = {
        "serverId": 1,
        "modelId": "all" 
    }
    # result = storage.process_manager("model", "get", **get_params)
    result = query_model(json.dumps(get_params|default_db_config, ensure_ascii=False))
    print(f"输入参数 server_id:{1}, model_id: {'all'}")
    print(f"输出结果: {result}")
    if json.loads(result)['status']=='success':
        print("✅ 获取模型成功")
    else:
        print("❌ 获取模型失败")

# 测试更新模型
def test_update_model(model_id):
    print("📦 测试更新模型...")
    updated_data = {
        "modelName": "更新后的模型名称",
        "serverId": 2,
        "modelId": model_id,
    }
    print(f"输入数据: {updated_data}, model_id: {model_id}")
    # result = storage.process_manager("model", "update_default", modelId=model_id, **updated_data)
    result = update_model(json.dumps(updated_data|default_db_config, ensure_ascii=False))
    print(f"输出结果: {result}")
    if json.loads(result)['status']=='success':
        print("✅ 更新模型成功")
    else:
        print("❌ 更新模型失败")
        
def test_get_default_model():
    print("📦 测试获取默认模型...")
    # result = storage.process_manager("model", "get_default", embeddingModel=0)
    default_model_data={
        "embeddingModel": 0
    }
    result = query_default_model(json.dumps(default_model_data|default_db_config, ensure_ascii=False))
    print(f"chat默认模型输出结果: {result}")
    default_model_data={
        "embeddingModel": 1
    }
    # result = storage.process_manager("model", "get_default", embeddingModel=1)
    result = query_default_model(json.dumps(default_model_data|default_db_config, ensure_ascii=False))
    print(f"embedding默认模型输出结果: {result}")
    if json.loads(result)['status']=='success':
        print("✅ 获取默认模型成功")
    else:
        print("❌ 获取默认模型失败")

# 测试删除模型
def test_delete_model(model_id):
    print("📦 测试删除模型...")
    model_data = {
        "modelId": model_id
    }
    # result = storage.process_manager("model", "delete", modelId=model_id)
    result = delete_model(json.dumps(model_data|default_db_config, ensure_ascii=False))
    print(f"输入参数 model_id: {model_id}")
    print(f"输出结果: {result}")
    if json.loads(result)['status']=='success':
        print("✅ 删除模型成功")
    else:
        print("❌ 删除模型失败")

# 测试添加智能体
def test_add_agent():
    print("🤖 测试添加智能体...")
    # agent_data = {
    #     "agentName": "远程智能体",
    #     "prompt": "你是一个文档助手，善于从提供的知识库中获取答案",
    #     "isLocal": 0,
    #     "knowledgeId": "32769"
    # }
    agent_data = {
        "agentName": "测试智能体",
        "prompt": "测试"
    }
    print(f"输入数据: {agent_data}")
    # result = storage.process_manager("agent", "add", **agent_data)
    result = add_agent(json.dumps(agent_data|default_db_config, ensure_ascii=False))
    print(f"输出结果: {result}")
    if json.loads(result)['status']=='success':
        print("✅ 添加智能体成功")
    else:
        print("❌ 添加智能体失败")
    return result

# 测试获取智能体
def test_get_agent(agent_id):
    print("🤖 测试获取智能体...")
    # result = storage.process_manager("agent", "get", agentId=agent_id)
    # print(f"输入参数 agent_id: {agent_id}")
    # print(f"输出结果: {result}")
    
    # agent_id = "all"
    agent_data = {
        "agentId": "all"
    }
    # result = storage.process_manager("agent", "get", agentId=agent_id)
    result = query_agent(json.dumps(agent_data|default_db_config, ensure_ascii=False))
    print(f"输入参数 agent_id: {agent_id}")
    # print(f"输出结果: {result[:200]}")
    # print(f"输出结果: {result}")
    if json.loads(result)['status']=='success':
        print("✅ 获取智能体成功")
        for res in json.loads(result)['result_info']:
            print(f"## {res}")
    else:
        print("❌ 获取智能体失败")

# 测试更新智能体
def test_update_agent(agent_id):
    print("🤖 测试更新智能体...")
    updated_data = {
        "agentName": "更新后的智能体名称",
        "prompt": "新测试型",
        "agentId": agent_id
    }
    print(f"输入数据: {updated_data}, agent_id: {agent_id}")
    # result = storage.process_manager("agent", "update", **updated_data)
    result = update_agent(json.dumps(updated_data|default_db_config, ensure_ascii=False))
    print(f"输出结果: {result}")
    if json.loads(result)['status']=='success':
        print("✅ 更新智能体成功")
    else:
        print("❌ 更新智能体失败")

# 测试删除智能体
def test_delete_agent(agent_id):
    print("🤖 测试删除智能体...")
    agent_data = {
        "agentId": agent_id
    }
    # result = storage.process_manager("agent", "delete", agentId=agent_id)
    result = delete_agent(json.dumps(agent_data|default_db_config, ensure_ascii=False))
    print(f"输入参数 agent_id: {agent_id}")
    print(f"输出结果: {result}")
    if json.loads(result)['status']=='success':
        print("✅ 删除智能体成功")
    else:
        print("❌ 删除智能体失败")

# 测试添加知识
def test_add_knowledge():
    print("📚 测试添加知识...")
    knowledge_data = {
        "knowledgeName": "测试知识",
        "embeddingModelId": "1"
    }
    print(f"输入数据: {knowledge_data}")
    # result = storage.process_manager("knowledge", "add", **knowledge_data)
    result = add_knowledge(json.dumps(knowledge_data|default_db_config, ensure_ascii=False))
    print(f"输出结果: {result}")
    if json.loads(result)['status']=='success':
        print("✅ 添加知识成功")
    else:
        print("❌ 添加知识失败")
    return result

# 测试获取知识
def test_get_knowledge(knowledge_id):
    print("📚 测试获取知识...")
    # result = storage.process_manager("knowledge", "get", knowledgeId=knowledge_id)
    # print(f"输入参数 knowledge_id: {knowledge_id}")
    # print(f"输出结果: {result}")

    # knowledge_id = "all"
    knowledge_data = {
        "knowledgeId": "all" 
    }
    # result = storage.process_manager("knowledge", "get", knowledgeId=knowledge_id)
    result = query_knowledge(json.dumps(knowledge_data|default_db_config, ensure_ascii=False))
    print(f"输入参数 knowledge_id: {knowledge_id}")
    print(f"输出结果: {result}")
    if json.loads(result)['status']=='success':
        print("✅ 获取知识成功")
    else:
        print("❌ 获取知识失败")

# 测试更新知识
def test_update_knowledge(knowledge_id):
    print("📚 测试更新知识...")
    updated_data = {
        "knowledgeName": "更新后的知识名称",
        "embeddingModelId": "新描述",
        "knowledgeId": knowledge_id
    }
    print(f"输入数据: {updated_data}, knowledge_id: {knowledge_id}")
    # result = storage.process_manager("knowledge", "update", knowledgeId=knowledge_id, **updated_data)
    result = update_knowledge(json.dumps(updated_data|default_db_config, ensure_ascii=False))
    print(f"输出结果: {result}")
    if json.loads(result)['status']=='success':
        print("✅ 更新知识成功")
    else:
        print("❌ 更新知识失败")

# 测试删除知识
def test_delete_knowledge(knowledge_id):
    print("📚 测试删除知识...")
    knowledge_data = {
        "knowledgeId": knowledge_id
    }
    # result = storage.process_manager("knowledge", "delete", knowledgeId=knowledge_id)
    result = delete_knowledge(json.dumps(knowledge_data|default_db_config, ensure_ascii=False))
    print(f"输入参数 knowledge_id: {knowledge_id}")
    print(f"输出结果: {result}")
    if json.loads(result)['status']=='success':
        print("✅ 删除知识成功")
    else:
        print("❌ 删除知识失败")

# 测试添加文档
def test_add_document(knowledge_id, doc_id):
    print("📄 测试添加文档...")
    document_data = {
        "knowledgeId": knowledge_id,
        "docId": doc_id,
        "fileName": "内容",
        "fileType": "txt",
        "fileHash": "哈希",
        "segmentNum": 1
    }
    print(f"输入数据: {document_data}")
    # result = storage.process_manager("document", "add", **document_data)
    result = add_document(json.dumps(document_data|default_db_config, ensure_ascii=False))
    print(f"输出结果: {result}")
    if json.loads(result)['status']=='success':
        print("✅ 添加文档成功")
    else:
        print("❌ 添加文档失败")
    return result

# 测试获取文档
def test_get_document(knowledge_id, document_id):
    print("📄 测试获取文档...")
    document_data = {
        "knowledgeId": knowledge_id,
        "docId": "all"
    }
    # result = storage.process_manager("document", "get", knowledgeId=knowledge_id, docId=document_id)
    result = query_document(json.dumps(document_data|default_db_config, ensure_ascii=False))
    print(f"输入参数 knowledge_id: {knowledge_id}, document_id: {document_id}")
    print(f"输出结果: {result}")
    if json.loads(result)['status']=='success':
        print("✅ 获取文档成功")
    else:
        print("❌ 获取文档失败")

# 测试删除文档
def test_delete_document(knowledge_id, document_id):
    print("📄 测试删除文档...")
    document_data = {
        "knowledgeId": knowledge_id,
        "docId": document_id
    }
    # result = storage.process_manager("document", "delete", knowledgeId=knowledge_id, docId=document_id)
    result = delete_document(json.dumps(document_data|default_db_config, ensure_ascii=False))
    print(f"输入参数 knowledge_id: {knowledge_id}, document_id: {document_id}")
    print(f"输出结果: {result}")
    if json.loads(result)['status']=='success':
        print("✅ 删除文档成功")
    else:
        print("❌ 删除文档失败")

def test_get_embedding(knowledge_id, document_id):
    print("📄 测试获取文档向量...")
    embedding_data = {
        "knowledgeId": knowledge_id,
        "docId": document_id
    }
    # result = storage.process_manager("embedding", "get", knowledgeId=knowledge_id, docId=document_id)
    result = query_embedding(json.dumps(embedding_data|default_db_config, ensure_ascii=False))
    print(f"输入参数 knowledge_id: {knowledge_id}, document_id: {document_id}")
    print(f"输出结果: {result}")
    if json.loads(result)['status']=='success':
        print("✅ 获取文档向量成功")
    else:
        print("❌ 获取文档向量失败")

def test_add_session():
    print("💬 测试添加会话...")
    session_data = {
        "sessionName": "测试会话",
        "agentId": "1",
        "chatModelId": 2
    }
    print(f"输入数据: {session_data}")
    result = add_session(json.dumps(session_data|default_db_config, ensure_ascii=False))
    print(f"输出结果: {result}")
    if json.loads(result)['status']=='success':
        print("✅ 添加会话成功")
    else:
        print("❌ 添加会话失败")
    return result

def test_get_session(session_id):
    print("💬 测试获取会话...")
    session_data = {
        "sessionId": session_id
    }
    result = query_session(json.dumps(session_data|default_db_config, ensure_ascii=False))
    print(f"输入参数 session_id: {session_id}")
    print(f"输出结果: {result}")
    if json.loads(result)['status']=='success':
        print("✅ 获取会话成功")
    else:
        print("❌ 获取会话失败")

def test_update_session(session_id):
    print("💬 测试更新会话...")
    updated_data = {
        "sessionName": "更新后的会话名称",
        "agentId": 3,
        "chatModelId": 3,
        "sessionId": session_id,
        "temperature": 0.3,
        "topP": 0.9,
        "sessionId": session_id,
    }
    print(f"输入数据: {updated_data}, session_id: {session_id}")
    result = update_session(json.dumps(updated_data|default_db_config, ensure_ascii=False))
    print(f"输出结果: {result}")
    if json.loads(result)['status']=='success':
        print("✅ 更新会话成功")
    else:
        print("❌ 更新会话失败")

def test_delete_session(session_id):
    print("💬 测试删除会话...")
    session_data = {
        "sessionId": session_id
    }
    result = delete_session(json.dumps(session_data|default_db_config, ensure_ascii=False))
    print(f"输入参数 session_id: {session_id}")
    print(f"输出结果: {result}")
    if json.loads(result)['status']=='success':
        print("✅ 删除会话成功")
    else:
        print("❌ 删除会话失败")
        
def test_add_history(session_id):
    print("💬 测试添加历史...")
    history_data = {
        "sessionId": session_id,
        "singleMessage": json.dumps({"role": "user", "content": "你好"}, ensure_ascii=False),
        "answerMeta": ""
    }
    print(f"输入数据: {history_data}")
    result = add_history(json.dumps(history_data|default_db_config, ensure_ascii=False))
    print(f"输出结果: {result}")
    time.sleep(1)
    history_data = {
        "sessionId": session_id,
        "singleMessage": json.dumps({"role": "user", "content": "你好，我是ChatGPT"}, ensure_ascii=False),
        "answerMeta": json.dumps([{"docId": 1, "fileName": "1", "content": "1", "similarity": 0.8},
                                  {"docId": 2, "fileName": "2", "content": "2", "similarity": 0.75},
                                  {"docId": 3, "fileName": "3", "content": "3", "similarity": 0.7}], ensure_ascii=False)
    }
    print(f"输入数据: {history_data}")
    result = add_history(json.dumps(history_data|default_db_config, ensure_ascii=False))
    print(f"输出结果: {result}")
    if json.loads(result)['status']=='success':
        print("✅ 添加历史成功")
    else:
        print("❌ 添加历史失败")
    return result

def test_get_history(session_id):
    print("💬 测试获取历史...")
    history_data = {
        "sessionId": session_id,
        "historyId": "all",
        "show_count": 10,
    }
    print(f"输入参数 session_id: {session_id}, history_id: all")
    result = query_history(json.dumps(history_data|default_db_config, ensure_ascii=False))
    print(f"输出结果: {result}")
    if json.loads(result)['status']=='success':
        print("✅ 获取历史成功")
    else:
        print("❌ 获取历史失败")
    
def test_delete_history(session_id):
    print("💬 测试删除历史...")
    history_data = {
        "sessionId": session_id,
        "historyId": "all"
    }
    print(f"输入参数 session_id: {session_id}, history_id: all")
    result = delete_history(json.dumps(history_data|default_db_config, ensure_ascii=False))
    print(f"输出结果: {result}")
    if json.loads(result)['status']=='success':
        print("✅ 删除历史成功"
              )

if __name__ == "__main__":

    # 测试各项功能
    # print("#############################\n")
    # server_result = test_add_server()
    # server_id = json.loads(server_result)['result_info']["serverId"]
    test_get_server("all")
    # test_update_server(server_id)
    # test_delete_server(server_id)
    
    # print("#############################\n")
    # model_result = test_add_model()
    # model_id = json.loads(model_result)['result_info']["modelId"]
    # test_get_model(model_id)
    # test_update_model(model_id)
    # test_get_default_model()
    # test_delete_model(model_id)
    
    # print("#############################\n")
    # agent_result = test_add_agent()
    # agent_id = json.loads(agent_result)['result_info']["agentId"]
    # test_get_agent(agent_id)
    # test_get_agent("all")
    # test_update_agent(agent_id)
    # test_delete_agent(agent_id)
    
    # print("#############################\n")
    # knowledge_result = test_add_knowledge()
    # knowledge_id = json.loads(knowledge_result)['result_info']["knowledgeId"]
    # test_get_knowledge(knowledge_id)
    # test_update_knowledge(knowledge_id)

    # print("#############################\n")
    # document_result = test_add_document(knowledge_id=knowledge_id, doc_id="65c51b40-9d03-63ef-a775d-2fbfe47b75da")
    # document_id = json.loads(document_result)['result_info']["docId"]
    # test_get_document(knowledge_id, document_id)
    # test_delete_document(knowledge_id, document_id)
    
    # # test_get_embedding(knowledge_id, document_id)
    
    # print("#############################\n")
    # test_delete_knowledge(knowledge_id)
    
    # print("#############################\n")
    # session_result = test_add_session()
    # session_id = json.loads(session_result)['result_info']["sessionId"]
    # test_get_session(session_id)
    # test_update_session(session_id)
    
    # print("#############################\n")
    # history_result = test_add_history(session_id)
    # history_id = json.loads(history_result)['result_info']["historyId"]
    # test_get_history(session_id)
    # # test_delete_history(session_id)
    
    # # test_delete_session(session_id)
    # # test_delete_session(1)
    # # test_delete_session(2)
    # # test_delete_session(3)
    # # test_delete_session(4)
