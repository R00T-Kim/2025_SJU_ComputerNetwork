import logging
import os

def get_logger(name):
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        logger.addHandler(ch)

        # Ensure logs are written to server.log in the project root
        # Get the directory of the current logger.py file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Go up two levels to reach the project root (from src/utils to project_root)
        project_root = os.path.dirname(os.path.dirname(current_dir))
        log_file_path = os.path.join(project_root, "server.log")
        
        fh = logging.FileHandler(log_file_path)
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(formatter)
        logger.addHandler(fh)
    return logger