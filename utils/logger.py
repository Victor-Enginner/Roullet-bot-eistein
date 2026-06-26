import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logger(name, log_file='logs/bot.log', level=logging.INFO):
    """
    Configura um logger com rotação de arquivos (Voice hook removido - modo visual)
    """
    
    os.makedirs('logs', exist_ok=True)
    
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)-15s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    handler = RotatingFileHandler(
        log_file,
        maxBytes=5*1024*1024,
        backupCount=3,
        encoding='utf-8'
    )
    handler.setFormatter(formatter)
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    logger.addHandler(console_handler)
    
    return logger

