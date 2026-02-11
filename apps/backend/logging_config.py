import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logging():
    # Create a logger
    logger = logging.getLogger('backend_logger')
    logger.setLevel(logging.INFO)
    
    # Create a formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create a console handler (always works)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Try to add file handler if we can write to the directory
    try:
        # Use /app/logs directory inside container (writable by appuser)
        log_dir = '/app/logs'
        
        # Create logs directory if it doesn't exist
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, 'backend.log')
        file_handler = RotatingFileHandler(log_file, maxBytes=1024*1024*5, backupCount=2)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.info(f"File logging enabled: {log_file}")
    except (PermissionError, OSError) as e:
        # If file logging fails (e.g., in restricted environments), just log to console
        logger.warning(f"File logging disabled due to: {e}. Logging to console only.")
    
    return logger

logger = setup_logging()