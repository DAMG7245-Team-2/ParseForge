import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logging():
    # Create a logger
    logger = logging.getLogger('backend_logger')
    logger.setLevel(logging.INFO)

    # Create a formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Create a file handler
    log_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'backend.log')
    file_handler = RotatingFileHandler(log_file, maxBytes=1024*1024*5, backupCount=2)
    file_handler.setFormatter(formatter)

    # Create a console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Add the handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

logger = setup_logging()
