import logging
from logging.handlers import RotatingFileHandler
import os

_configured_loggers = set()


def setup_logger(name, log_file='logs/bot.log', level=logging.INFO):
    """
    Configura um logger com rotação de arquivos.

    OTIMIZAÇÃO DE LATÊNCIA:
    - Idempotente: se 'name' já foi configurado, devolve o mesmo logger
      SEM adicionar handlers novamente. Antes, cada import re-chamava
      setup_logger() e empilhava handlers duplicados -> cada linha de log
      era escrita em disco N vezes (amplificação de I/O síncrono no hot path).
    - propagate=False: evita que a mensagem suba pro root logger e seja
      escrita de novo.
    - delay=True no RotatingFileHandler: só abre o arquivo no primeiro emit.
    """
    logger = logging.getLogger(name)

    # Já configurado nesta sessão -> não duplica handlers
    if name in _configured_loggers:
        return logger

    os.makedirs('logs', exist_ok=True)

    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)-15s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding='utf-8',
        delay=True,
    )
    handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger.setLevel(level)
    logger.handlers.clear()  # segurança extra contra duplicação
    logger.addHandler(handler)
    logger.addHandler(console_handler)
    logger.propagate = False

    _configured_loggers.add(name)
    return logger
