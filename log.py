import logging


def _get_logger():
    log = logging.getLogger('log')
    log.setLevel(logging.INFO)
    file_handler = logging.FileHandler("flask.log")
    file_handler.setFormatter(logging.Formatter('[%(levelname)s][%(asctime)s][%(filename)s:%(lineno)d] - %(message)s',
                                                datefmt='%Y-%m-%d %H:%M:%S'))
    log.addHandler(file_handler)
    log.setLevel(logging.DEBUG)
    return log


# 日志句柄
logger = _get_logger()
