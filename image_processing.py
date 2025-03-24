# image_processing.py
import logging
import cv2
from PIL import Image, ImageTk, UnidentifiedImageError
from typing import Optional
from settings import Config
from enums import AppState

class ImageDisplay:
    def __init__(self, image_label, set_status_callback):
        self.image_label = image_label
        self.set_status = set_status_callback
        self.img: Optional[Image.Image] = None  # Original image for both display and OCR
        self.tk_img: Optional[ImageTk.PhotoImage] = None

    def process_and_display_image(self, img: Image.Image) -> bool:
        """Processes and displays the original image in the image_label widget."""
        try:
            img.thumbnail((Config.DEFAULT_IMAGE_WIDTH, Config.DEFAULT_IMAGE_HEIGHT))
            self.tk_img = ImageTk.PhotoImage(img)
            self.image_label.config(image=self.tk_img)
            self.image_label.image = self.tk_img
            self.img = img
            return True
        except Exception as e:
            logging.error(f"Error processing/displaying image: {e}", exc_info=True)
            self.set_status(AppState.ERROR, "Error processing/displaying image.")
            return False

    def load_and_process_image(self, image_source, filename: Optional[str] = None) -> bool:
        """Loads an image for display and OCR without preprocessing."""
        try:
            if isinstance(image_source, str):
                img = Image.open(image_source)
                if cv2.imread(image_source) is None:  # Basic validation
                    raise ValueError(f"OpenCV could not load image: {image_source}")
            elif isinstance(image_source, Image.Image):
                img = image_source
            else:
                raise ValueError("Unsupported image source type")

            if self.process_and_display_image(img):
                self.set_status(AppState.READY, f"Image loaded: {filename or 'Clipboard Image'}")
                return True
            return False

        except (FileNotFoundError, UnidentifiedImageError, ValueError) as e:
            self.set_status(AppState.ERROR, f"Error loading image: {e}")
            logging.error(f"Error loading image: {e}", exc_info=True)
            return False

    def clear(self):
        """Clears the displayed image."""
        self.image_label.config(image=None)
        self.image_label.image = None
        self.img = None
        self.tk_img = None