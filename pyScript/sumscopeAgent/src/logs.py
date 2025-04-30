import os
import logging
from logging.handlers import RotatingFileHandler # type: ignore
import sys
import io
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))

def get_logger():
    # 在文件开头添加日志配置
    log_dir = os.path.join(base_dir, 'log')
    os.makedirs(log_dir, exist_ok=True)

    # 获取根日志记录器
    logger = logging.getLogger()
    if logger.handlers:  # 避免重复添加handler
        return logger
    
    # 文件日志
    log_handler = RotatingFileHandler(
        filename=os.path.join(log_dir, f'service.log'),
        maxBytes=10*1024*1024,
        backupCount=30,
        encoding='utf-8'
    )
    log_handler.setFormatter(logging.Formatter(
        '%(asctime)s - [%(filename)s:%(lineno)d] - %(levelname)s - %(message)s'
    ))
    
    # 控制台日志（可选）
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        '%(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    ))

    class StreamToLogger(io.TextIOBase):
        """
        重定向标准输出到日志记录的代理类
        """
        def __init__(self, original_std, logger):
            self.original_std = original_std
            self.logger = logger
            self.buffer = ''

        def write(self, message):
            self.original_std.write(message)
            if message.strip():
                self.buffer += message
                if '\n' in self.buffer:
                    parts = self.buffer.split('\n')
                    for part in parts[:-1]:
                        if part.strip():
                            self.logger.info(part)
                    self.buffer = parts[-1]

        def flush(self):
            if self.buffer.strip():
                self.logger.info(self.buffer)
                self.buffer = ''
            self.original_std.flush()

    logger.setLevel(logging.INFO)
    logger.addHandler(log_handler)
    # logger.addHandler(console_handler)  # 按需开启
    
    # 在设置完日志处理器后添加重定向
    if not logger.handlers:
        # 创建代理对象并重定向标准输出
        sys.stdout = StreamToLogger(sys.stdout, logger)
    
    return logger  # 添加返回语句