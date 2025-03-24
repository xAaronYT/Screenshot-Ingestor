# main.py
import logging
import logging.handlers
import sys
from ui import ScreenshotIngestorApp
from settings import Config

def setup_logging():
    """Sets up the logging configuration."""
    log_file_path = Config.LOG_FILE
    logging.basicConfig(
        level=Config.LOG_LEVEL,
        format='%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s',
        filename=log_file_path
    )
    handler = logging.handlers.RotatingFileHandler(
        log_file_path, maxBytes=1024*1024, backupCount=5)
    logging.getLogger('').addHandler(handler)
    logging.info("Application started.")

if __name__ == "__main__":
    setup_logging()
    
    try:
        import easyocr
    except ImportError as e:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        tk.messagebox.showerror("Error",
                               f"EasyOCR is not installed. Please install it by running: pip install easyocr\nOriginal Error: {e}")
        logging.critical("EasyOCR not installed. Application exiting.", exc_info=True)
        sys.exit(1)

    app = ScreenshotIngestorApp()
    app.run()