# image_processing.py
import logging
import cv2
import numpy as np
from PIL import Image, ImageTk, UnidentifiedImageError
from typing import Optional
from config import Config, AppState


class ImageDisplay:
    def __init__(self, image_label, set_status_callback):
        self.image_label = image_label
        self.set_status = set_status_callback
        self.img: Optional[Image.Image] = None
        self.tk_img: Optional[ImageTk.PhotoImage] = None

    def process_and_display_image(self, img: Image.Image) -> bool:
        """Processes and displays an image in the image_label widget."""
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
        """Loads an image from various sources and preprocesses it."""
        try:
            if isinstance(image_source, str):
                test_img = cv2.imread(image_source)
                if test_img is None:
                    raise ValueError(f"OpenCV could not load image: {image_source}")
                img = Image.open(image_source)
                img_cv = cv2.imread(image_source, cv2.IMREAD_GRAYSCALE)
                img_cv = cv2.adaptiveThreshold(img_cv, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
                img = Image.fromarray(img_cv)
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
