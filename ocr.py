# ocr.py
import easyocr
from PIL import Image
from io import BytesIO
import logging
from settings import AppSettings

class OCRProcessor:
    def __init__(self, settings: AppSettings):
        self.settings = settings
        self.reader = easyocr.Reader(['en'], gpu=self.settings.ocr_use_gpu)
        logging.info(f"OCR reader initialized with GPU: {self.settings.ocr_use_gpu}")

    def extract_text(self, image: Image.Image) -> list:
        """Extracts text from an image."""
        try:
            if hasattr(image, 'filename'):
                results = self.reader.readtext(image.filename)
            else:
                buffered = BytesIO()
                image.save(buffered, format="JPEG")
                results = self.reader.readtext(buffered.getvalue())
            return results
        except Exception as e:
            logging.error(f"Error during OCR: {e}", exc_info=True)
            raise