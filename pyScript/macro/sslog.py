import os, sys, logging, datetime
from logging.handlers import TimedRotatingFileHandler, QueueHandler, QueueListener
from multiprocessing import Queue

log_queue = Queue(-1)
queue_listener = ""

tm = datetime.datetime.now().strftime("%Y%m%d")
curr_path = os.getcwd()
log_dir = curr_path + "\\Log"
log_file = log_dir + "\\PY_" + tm + ".log"
if not os.path.exists(log_dir):
    os.makedirs(log_dir, exist_ok = True)

def set_formatter():
    fmt="%(asctime)s %(levelname)s %(filename)s line %(lineno)d[%(funcName)s] %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"
    return logging.Formatter(fmt, datefmt=datefmt)

def set_stream_handle(formatter: logging.Formatter):
    stream_handle = logging.StreamHandler(sys.stdout)
    stream_handle.setLevel(logging.INFO)
    stream_handle.setFormatter(formatter)
    return stream_handle

def set_file_handle(formatter: logging.Formatter):
    file_handle = TimedRotatingFileHandler(log_file, when="midnight", backupCount=5, encoding="utf-8")
    file_handle.setLevel(logging.INFO)
    file_handle.setFormatter(formatter)
    return file_handle

def set_queue_handle():
    queue_handle = QueueHandler(log_queue)
    queue_handle.setLevel(logging.INFO)
    return queue_handle

def close_log_queue():
    global queue_listener
    if queue_listener:
        queue_listener.stop()

def get_logger(name = "sslogger", level = logging.INFO):
    logger = logging.getLogger(name)
    logger.setLevel(level)
    formatter = set_formatter()
    queue_handle = set_queue_handle()
    stream_handle = set_stream_handle(formatter)
    file_handle = set_file_handle(formatter)
    logger.addHandler(queue_handle)

    global queue_listener
    if not queue_listener:
        queue_listener = QueueListener(log_queue, stream_handle, file_handle, respect_handler_level=True)
        queue_listener.start()
    return logger

sslogger = get_logger()

if __name__ == '__main__':
    sslogger.info("test")
    close_log_queue()
    
