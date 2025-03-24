# ocr.py
import easyocr
from PIL import Image
from io import BytesIO
import logging

class OCRProcessor:
    def __init__(self, use_gpu: bool = True):
        """
        Initialize the OCR processor with optional GPU support.
        
        Args:
            use_gpu (bool): Whether to use GPU for OCR processing. Defaults to True.
        """
        self.reader = easyocr.Reader(['en'], gpu=use_gpu)
        logging.info(f"OCR reader initialized with GPU: {use_gpu}")

    def extract_text(self, image: Image.Image) -> list:
        """
        Extracts text from an image.

        Args:
            image (PIL.Image.Image): The image to process.

        Returns:
            list: List of OCR results (bbox, text, probability).

        Raises:
            Exception: If OCR processing fails.
        """
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