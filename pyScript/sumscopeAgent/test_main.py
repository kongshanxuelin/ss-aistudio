import time
import os
import sys
import uuid
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
print(base_dir)
sys.path.append(base_dir)
from main_service import process_file, create_database, similarity_query, delete_file

def test_main(start=0, end=10):
    # 原有命令处理...
    print("🚀 开始集成测试...")
    
    # 测试数据库创建
    test_db_name = "pdftest-1"
    test_db_path = os.path.join(base_dir, "./db_date")
    if start <= 0 and end > 0:
        start_1_time = time.time()
        print(f"\n1. 测试创建数据库 {test_db_name}...")
        if create_database(test_db_path, test_db_name, 1024):
            print(f"✅ 数据库创建成功 @ {test_db_path}/{test_db_name}.db, use time: {time.time() - start_1_time:.2f}s")
    
    test_file_list = ["test.pdf", "test.html", "test.csv", "test.txt", "test.md", "test.docx", "test.pptx", "test.xlsx", "test.epub", "test.json"]  # 需要真实测试文件
    # test_file_list = ["test.epub", "test.html", "test.json"]  # 需要真实测试文件
    test_file_path = os.path.join(base_dir, "./test_file")
    api_config = {
            'api_url': 'https://api.siliconflow.cn/v1/embeddings',
            'api_key': 'sk-lcmgoofhdtzibdjvizbzzuyuvmwnuzavvdrabokwstieedal',    # 需要替换有效API密钥
            'model': 'BAAI/bge-m3'
        }
    db_config = {
        'db_path': test_db_path,
        'db_name': test_db_name,
        'db_emb_len': 1024,
        'chunk_size': 1024,
        'overlap': 256
    }
    if start <= 1 and end > 1:
        # 测试文件处理
        strat_2_time = time.time()
        print("\n2. 测试文件处理功能...")
        success_count = 0
        for test_file in test_file_list:
            db_config['doc_id'] = str(uuid.uuid5(uuid.NAMESPACE_DNS, "/".join([db_config['db_path'],db_config['db_name'],os.path.join(test_file_path, test_file)])))
            process_result = process_file(os.path.join(test_file_path, test_file), api_config, db_config)
            print(f"处理结果：{process_result}")
            if process_result["status"] == "success":
                success_count += 1
        print(f"🆗 成功处理 {success_count}/{len(test_file_list)} 个文件, all use time: {time.time() - strat_2_time:.2f}s")
    
    if start <= 2 and end > 2:
        # 测试相似度查询
        start_3_time = time.time()
        print("\n3. 测试相似度查询...")
        test_query = "深度学习 大模型"
        results = similarity_query(
            text=test_query,
            api_config=api_config,
            db_config=db_config,
            search_config={
                'threshold': 0.3,
                'max_count': 3
            }
        )
        print(f"use time: {time.time() - start_3_time:.2f}s, 找到 {len(results)} 条相关结果：")
        for i, res in enumerate(results[:3]):
            print(f"✅ {i+1}. 相似度 {res['similarity']:.2f} | doc_id: {res['doc_id']} | 内容片段: {res['content'][:60]}...")
    
    # 新增删除测试阶段
    if start <= 3 and end > 3:
        start_4_time = time.time()
        print("\n4. 测试文档删除功能...")
        # 随机选择一个文档进行删除测试
        test_file = test_file_list[1]
        db_config["doc_id"] = str(uuid.uuid5(uuid.NAMESPACE_DNS, "/".join([db_config['db_path'],db_config['db_name'],os.path.join(test_file_path, test_file)])))
        del_result = delete_file(db_config=db_config)
        print(f"删除结果：{del_result}")
        if del_result["status"] == "success":
            print(f"✅ 成功删除文档 {test_file_list[1]}")
        print(f"删除测试用时: {time.time() - start_4_time:.2f}s")

        
    print("\n🎉 集成测试完成！")
    
    
if __name__ == "__main__":
    test_main(0, 4)