# ui.py
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk, ImageGrab
import cv2
import threading
import logging
from enum import Enum
from settings import AppSettings, Config, load_autocorrect_rules, load_item_name_lookup
from ocr import OCRProcessor
from api import TarkovAPI
from utils import preprocess_search_term
from fuzzywuzzy import process

class AppState(Enum):
    READY = "Ready"
    LOADING = "Loading..."
    PROCESSING = "Processing..."
    SEARCHING = "Searching Tarkov.dev..."
    COMPLETED = "Completed"
    ERROR = "Error"

class ImageDisplay:
    def __init__(self, image_label):
        self.image_label = image_label
        self.img = None
        self.tk_img = None

    def process_and_display_image(self, img: Image.Image) -> bool:
        try:
            img.thumbnail((Config.DEFAULT_IMAGE_WIDTH, Config.DEFAULT_IMAGE_HEIGHT))
            self.tk_img = ImageTk.PhotoImage(img)
            self.image_label.config(image=self.tk_img)
            self.image_label.image = self.tk_img
            self.img = img
            return True
        except Exception as e:
            logging.error(f"Error processing/displaying image: {e}", exc_info=True)
            return False

    def load_and_process_image(self, image_source, filename=None, set_status=None):
        try:
            if isinstance(image_source, str):
                img_cv = cv2.imread(image_source, cv2.IMREAD_GRAYSCALE)
                img_cv = cv2.adaptiveThreshold(img_cv, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
                img = Image.fromarray(img_cv)
            elif isinstance(image_source, Image.Image):
                img = image_source
            else:
                raise ValueError("Unsupported image source type")
            if self.process_and_display_image(img):
                set_status(AppState.READY, message=f"Image loaded: {filename or 'Clipboard Image'}")
                return True
            return False
        except Exception as e:
            logging.error(f"Error loading image: {e}", exc_info=True)
            set_status(AppState.ERROR, message="Error loading image")
            return False

    def clear(self):
        self.image_label.config(image=None)
        self.image_label.image = None
        self.img = None
        self.tk_img = None

class ScreenshotIngestorApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Screenshot Ingestor")
        self.root.geometry("1080x720")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.settings = AppSettings()
        self.api = TarkovAPI()
        self.ocr = OCRProcessor(self.settings)
        self.autocorrect_rules = load_autocorrect_rules()
        self.item_name_lookup = load_item_name_lookup()

        self.setup_ui()

    def setup_ui(self):
        menubar = tk.Menu(self.root)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Exit", command=self.on_closing)
        menubar.add_cascade(label="File", menu=filemenu)
        self.root.config(menu=menubar)

        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=10)
        tk.Button(button_frame, text="Load Screenshot", command=self.load_image).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Paste from Clipboard", command=self.paste_from_clipboard).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Clear", command=self.clear_all).pack(side=tk.LEFT, padx=5)

        self.image_label = tk.Label(self.root)
        self.image_label.pack(pady=10)
        self.image_display = ImageDisplay(self.image_label)

        self.extracted_text_box = tk.Text(self.root, height=10, width=80)
        self.extracted_text_box.pack(pady=10)

        self.progress_bar = ttk.Progressbar(self.root, length=800, mode="indeterminate")
        self.progress_bar.pack(pady=5)

        self.tarkov_results_text = tk.Text(self.root, height=10, width=80, state=tk.DISABLED)
        self.tarkov_results_text.pack(pady=10)

        self.status_label = tk.Label(self.root, text="Ready")
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

    def set_status(self, state: AppState, message: str = None):
        status_text = f"{state.value}" + (f" - {message}" if message else "")
        self.status_label.config(text=status_text)
        self.root.update_idletasks()
        logging.info(f"Status updated to: {status_text}")

    def load_image(self):
        filename = filedialog.askopenfilename(filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.gif;*.bmp;*.webp"), ("All files", "*.*")])
        if filename:
            self.image_display.load_and_process_image(filename, filename=filename, set_status=self.set_status)
            self.extract_text()

    def paste_from_clipboard(self):
        clipboard_content = ImageGrab.grabclipboard()
        if isinstance(clipboard_content, Image.Image):
            self.image_display.load_and_process_image(clipboard_content, set_status=self.set_status)
            self.extract_text()

    def extract_text(self):
        if not self.image_display.img:
            self.set_status(AppState.READY, "No image loaded.")
            return
        self.set_status(AppState.PROCESSING, "Extracting text...")
        self.progress_bar.start()

        def do_ocr():
            try:
                results = self.ocr.extract_text(self.image_display.img)
                extracted_text = ""
                corrected_lines = []
                for (_, text, _) in results:
                    preprocessed = preprocess_search_term(text)
                    corrected = self.autocorrect_term(preprocessed)
                    corrected_lines.append(corrected)
                    extracted_text += corrected + "\n"
                self.extracted_text_box.delete("1.0", tk.END)
                self.extracted_text_box.insert(tk.END, extracted_text)
                self.set_status(AppState.COMPLETED, "Text extracted successfully!")
                self.search_tarkov_dev(corrected_lines)
            except Exception as e:
                self.set_status(AppState.ERROR, f"Error during OCR: {e}")
            finally:
                self.progress_bar.stop()

        threading.Thread(target=do_ocr, daemon=True).start()

    def autocorrect_term(self, term: str) -> str:
        term = term.lower()
        if term in self.autocorrect_rules:
            return self.autocorrect_rules[term]
        if self.settings.use_item_corrections and self.item_name_lookup:
            best_match, score = process.extractOne(term, self.item_name_lookup.keys())
            if score >= Config.FUZZY_MATCH_THRESHOLD:
                return best_match
        return term

    def search_tarkov_dev(self, item_names: list):
        self.set_status(AppState.SEARCHING, "Searching Tarkov.dev...")
        self.progress_bar.start()
        self.tarkov_results_text.config(state=tk.NORMAL)
        self.tarkov_results_text.delete("1.0", tk.END)

        item_counts = {}
        for item_name in item_names:
            corrected = self.autocorrect_term(preprocess_search_term(item_name))
            item_counts[corrected] = item_counts.get(corrected, 0) + 1

        for item_name, count in item_counts.items():
            item_data = self.api.get_item_data(item_name)
            if item_data:
                self.tarkov_results_text.insert(tk.END, f"Item: {item_name} (x{count})\n")
                for item in item_data:
                    self.tarkov_results_text.insert(tk.END, f"  Name: {item['name']}\n  Avg Price: {item['avg24hPrice']}\n")
            else:
                self.tarkov_results_text.insert(tk.END, f"Item: {item_name} (x{count}) - No data found\n")

        self.tarkov_results_text.config(state=tk.DISABLED)
        self.set_status(AppState.COMPLETED, "Search completed.")
        self.progress_bar.stop()

    def clear_all(self):
        self.image_display.clear()
        self.extracted_text_box.delete("1.0", tk.END)
        self.tarkov_results_text.delete("1.0", tk.END)
        self.set_status(AppState.READY)

    def on_closing(self):
        self.settings.save_settings()
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            self.root.destroy()
            logging.info("Application closed.")

    def run(self):
        self.root.mainloop()