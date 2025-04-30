import time
import os
import sys

base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
sys.path.append(base_dir)

from main_service import create_database


def test_main(start=0, end=10):
    # 原有命令处理...
    print("🚀 开始集成测试...")

    test_db_name = "pdftest-1"
    test_db_path = os.path.join(base_dir, "./db_date")
    if start <= 0 and end > 0:
        start_1_time = time.time()
        print(f"\n1. 测试创建数据库 {test_db_name}...")
        if create_database(test_db_path, test_db_name, 1024):
            print(f"✅ 数据库创建成功 @ {test_db_path}/{test_db_name}.db, use time: {time.time() - start_1_time:.2f}s")

if __name__ == "__main__":
    test_main(0, 4)