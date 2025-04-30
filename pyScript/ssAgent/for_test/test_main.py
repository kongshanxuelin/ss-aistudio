import json
import time # type: ignore
import os
import sys
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
# print(base_dir)
sys.path.append(base_dir)
from query_service import similarity_query, query_knowledge, add_knowledge, update_server
from main_service import process_file, create_database, delete_file
from src.database.database_manager import EmbeddingStorage

# 新建一个测试的知识库
# 测试数据库创建
test_db_name = "pdftest2"
test_db_path = os.path.join(base_dir, "./db_date")
emb_len = 1024
user_name = "testuser"
if not os.path.exists(test_db_path):
    print(f"数据库路径不存在，将创建路径：{test_db_path}")
# 测试增删改查 
storage = EmbeddingStorage(user_name, test_db_path, emb_len)
model_id = 1
knowledge_id = 1

def test_main(start=0, end=10):
    # 原有命令处理...
    print("🚀 开始集成测试...")
    global model_id, knowledge_id
    
    if start <= 0 and end > 0:
        start_1_time = time.time()
        print(f"\n1. 测试创建数据库 {test_db_name}...")
        config_1 = {
            "user_name": user_name,
            "db_path": test_db_path,
            "emb_len": emb_len,
        }
        if create_database(json.dumps(config_1, ensure_ascii=False)):
            print(f"✅ 数据库创建成功 @ {test_db_path}/{user_name}.db, use time: {time.time() - start_1_time:.2f}s")
        # # 跟新serverAPI
        # update_result = update_server(json.dumps({
        #     "user_name": user_name, 
        #     "db_path": test_db_path,
        #     "serverId": 1,
        #     "serverApiKey": "sk-lcmgoofhdtzibdjvizbzzuyuvmwnuzavvdrabokwstieedal"
        # }))
        # print(f"update_result: {update_result}")
        knowledge_data = {
            "knowledgeName": test_db_name,
            "embeddingModelId": model_id,
        }
        know_info = query_knowledge(json.dumps(config_1|{"knowledgeId":knowledge_id}, ensure_ascii=False))
        know_info = json.loads(know_info)
        if know_info['result_info'] is None or know_info['result_info']==[]:
            knowledge_result = add_knowledge(json.dumps(config_1|knowledge_data, ensure_ascii=False)) 
            knowledge_id = json.loads(knowledge_result)['result_info']['knowledgeId']
            print(f"✅ 知识库创建成功，knowledgeId: {knowledge_id}")
    if end<=1:
        return
    
    test_file_list = ["test.pdf", "test.html", "test.csv", "test.txt", "test.md", "test.docx", "test.pptx", "test.xlsx", "test.epub", "test.json"]  # 需要真实测试文件
    # test_file_list = ["test.epub", "test.html", "test.json"]  # 需要真实测试文件
    test_file_path = os.path.join(base_dir, "./test_file")

    if start <= 1 and end > 1:
        # 测试文件处理
        strat_2_time = time.time()
        print("\n2. 测试文件处理功能...")
        success_count = 0
        # for test_file in test_file_list:
        if 1:
            config_2 = {
                'user_name': user_name,
                'db_path': test_db_path,
                # "file_path": os.path.join(test_file_path, test_file),
                "file_path": [os.path.join(test_file_path, test_file) for test_file in test_file_list],
                'knowledgeId': knowledge_id,
                # 'modelId': 1
                'isDir': False
            }
            process_result = process_file(json.dumps(config_2, ensure_ascii=False))
            if type(process_result) == str:
                process_result = json.loads(process_result)
            print(f"处理结果：{process_result}")
            for res in process_result["result_info"]:
                if res["file_status"] == 1:
                    success_count += 1
        print(f"🆗 成功处理 {success_count}/{len(test_file_list)} 个文件, all use time: {time.time() - strat_2_time:.2f}s")
        
        
        strat_2_time_1 = time.time()
        print("\n2-1. 测试目录处理功能...")
        success_count = 0
        # for test_file in test_file_list:
        if 1:
            config_2 = {
                'user_name': user_name,
                'db_path': test_db_path,
                "file_path": [os.path.join(base_dir, "test_file", "sdp帮助")],
                # "file_path": [os.path.join(base_dir, "test_file", "help")],
                # "file_path": [os.path.join(base_dir, "test_file")],
                'knowledgeId': knowledge_id,
                # 'modelId': 1
                'isDir': True
            }
            process_result = process_file(json.dumps(config_2, ensure_ascii=False))
            if type(process_result) == str:
                process_result = json.loads(process_result)
            print(f"处理结果：{process_result}")
            for res in process_result["result_info"]:
                if res["file_status"] == 1:
                    success_count += 1
            nums = len(process_result["result_info"])
        print(f"🆗 成功处理 {success_count}/{nums} 个文件, all use time: {time.time() - strat_2_time_1:.2f}s")
    
    
    if start <= 2 and end > 2:
        # 测试相似度查询
        start_3_time = time.time()
        print("\n3. 测试相似度查询...")
        test_query = "深度学习 大模型"
        config_3 = {
            'user_name': user_name,
            'db_path': test_db_path,
            "text": test_query,
            # "modelId": 1,
            "agentId": 2
        }
        results = similarity_query(
            json.dumps(config_3, ensure_ascii=False),
        )
        if type(results) == str:
            results = json.loads(results)['result_info']
        if results:
            print(f"use time: {time.time() - start_3_time:.2f}s, 找到 {len(results)} 条相关结果：")
            for i, res in enumerate(results[:]):
                print(f"✅ {i+1}. 相似度 {res['similarity']:.2f} | docId: {res['docId']} | fileName: {res['fileName']} | cachePath: {res['cachePath']} | 内容片段: {res['content'][:60]}...")
        
    # 新增删除测试阶段
    if start <= 3 and end > 3:
        start_4_time = time.time()
        print("\n4. 测试文档删除功能...")
        # 随机选择一个文档进行删除测试
        db_config = {
            'user_name': user_name,
            'db_path': test_db_path,
            'knowledgeId': 1,
            'docId': '603cbeb0-35f8-5d86-8e00-b123e9e42b3d'
        }
        del_result = delete_file(db_config=json.dumps(db_config, ensure_ascii=False))
        if type(del_result) == str:
            del_result = json.loads(del_result)
        print(f"删除结果：{del_result}")
        if del_result["status"] == "success":
            print(f"✅ 成功删除文档 {del_result['result_info']}")
        print(f"删除测试用时: {time.time() - start_4_time:.2f}s")
        
        # start_4_time = time.time()
        # print("\n4-1. 测试目录删除功能...")
        # # 随机选择一个文档进行删除测试
        # db_config = {
        #     'user_name': user_name,
        #     'db_path': test_db_path,
        #     'knowledgeId': 1,
        #     # 'docId': '3df94dc1-46d7-5a36-bb36-aff77b28e47c'
        #     'docId': 'fa1627ca-03ab-5b4b-8c0e-35fa22bce018'
        # }
        # del_result = delete_file(db_config=json.dumps(db_config, ensure_ascii=False))
        # if type(del_result) == str:
        #     del_result = json.loads(del_result)
        # print(f"删除结果：{del_result}")
        # if del_result["status"] == "success":
        #     print(f"✅ 成功删除目录 {del_result['result_info']}")
        # print(f"删除测试用时: {time.time() - start_4_time:.2f}s")

        
    print("\n🎉 集成测试完成！")
    
    
if __name__ == "__main__":
    test_main(0,1)