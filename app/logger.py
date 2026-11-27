import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

# Define the log directory and file
LOG_DIR = Path("app/logs")
LOG_FILE = LOG_DIR / "app.log"

def setup_logger(name: str = "app", level: int = logging.INFO):
    """
    Sets up a logger with both console and file handlers.
    """
    # Ensure the log directory exists
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Create a custom logger
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Prevent adding handlers multiple times if the logger is already configured
    if not logger.handlers:
        # Create handlers
        c_handler = logging.StreamHandler(sys.stdout)
        f_handler = RotatingFileHandler(LOG_FILE, maxBytes=10*1024*1024, backupCount=5)
        
        c_handler.setLevel(level)
        f_handler.setLevel(level)

        # Create formatters and add it to handlers
        c_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        f_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        c_handler.setFormatter(c_format)
        f_handler.setFormatter(f_format)

        # Add handlers to the logger
        logger.addHandler(c_handler)
        logger.addHandler(f_handler)

    return logger

# Initialize the default logger
logger = setup_logger()
