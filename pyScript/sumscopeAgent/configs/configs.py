server_file = "server.json"
agents_file = "agents.json"
models_file = "models.json"
remote_configs_file = "remote_file.json"
REMOTE_API_URL = "http://192.168.10.30:5000/api/operation"
REMOTE_QUERY_URL = "http://192.168.10.30:5000/api/similarity-search"
REMOTE_SERVER_URL = "http://192.168.10.30:5000/api/upload_zip"

default_chat_config = {
    "temperature": 0.7, 
    "top_k": 50,    
    "top_p": 0.7,       
    "frequency_penalty": 0,
    "last_N": 5
}

# 文件路径占位符
pos_text = "<cache_images_path>"

registryUrl = {
    "清华大学": "https://pypi.tuna.tsinghua.edu.cn/simple",
    "阿里云": "http://mirrors.aliyun.com/pypi/simple/",
    "中国科学技术大学": "https://mirrors.ustc.edu.cn/pypi/simple/",
    "华为云": "https://repo.huaweicloud.com/repository/pypi/simple/",
    "腾讯云": "https://mirrors.cloud.tencent.com/pypi/simple/",
    "淘宝npmmirror": "https://registry.npmmirror.com",
}

MCO_SERVER_PORT=8910