# ui.py
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageGrab
import threading
import logging
from settings import AppSettings, Config, load_autocorrect_rules, load_item_name_lookup
from ocr import OCRProcessor
from api import TarkovAPI
from utils import preprocess_search_term
from fuzzywuzzy import process
from image_processing import ImageDisplay
from enums import AppState

class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tip_window or not self.text:
            return
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                         background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                         font=("Arial", "8", "normal"))
        label.pack(ipadx=1)

    def hide_tip(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
        self.tip_window = None

class ScreenshotIngestorApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Screenshot Ingestor")
        self.root.geometry("1080x720")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.resizable(True, True)
        self.root.configure(bg="#f0f0f0")

        # Define a style for buttons
        self.style = ttk.Style()
        self.style.configure("TButton", font=("Arial", 10))
        self.style.map("TButton",
                       background=[("active", "#d0d0d0")],
                       foreground=[("active", "#000000")])

        self.settings = AppSettings()
        self.api = TarkovAPI()
        self.ocr = OCRProcessor(self.settings.ocr_use_gpu)
        self.autocorrect_rules = load_autocorrect_rules()
        self.item_name_lookup = load_item_name_lookup()

        self.setup_ui()

    def setup_ui(self):
        # Menu
        menubar = tk.Menu(self.root)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Exit", command=self.on_closing)
        settingsmenu = tk.Menu(menubar, tearoff=0)
        self.gpu_var = tk.BooleanVar(value=self.settings.ocr_use_gpu)
        settingsmenu.add_checkbutton(label="Use GPU for OCR", variable=self.gpu_var, command=self.toggle_gpu)
        menubar.add_cascade(label="File", menu=filemenu)
        menubar.add_cascade(label="Settings", menu=settingsmenu)
        self.root.config(menu=menubar)

        # Main frames
        left_frame = tk.Frame(self.root, bg="#f0f0f0", bd=1, relief=tk.SUNKEN)
        left_frame.pack(side=tk.LEFT, padx=10, pady=10, fill=tk.Y)
        right_frame = tk.Frame(self.root, bg="#f0f0f0", bd=1, relief=tk.SUNKEN)
        right_frame.pack(side=tk.RIGHT, padx=10, pady=10, expand=True, fill=tk.BOTH)

        # Left: Image display
        tk.Label(left_frame, text="Screenshot", font=("Arial", 12, "bold"), bg="#f0f0f0").pack()
        self.image_label = tk.Label(left_frame, bg="#f0f0f0")
        self.image_label.pack()
        self.image_display = ImageDisplay(self.image_label, self.set_status)

        # Right: Controls and output
        button_frame = tk.Frame(right_frame, bg="#f0f0f0")
        button_frame.pack(fill=tk.X, pady=(0, 10))
        load_btn = ttk.Button(button_frame, text="Load Screenshot", command=self.load_image, width=15, style="TButton")
        load_btn.pack(side=tk.LEFT, padx=5)
        Tooltip(load_btn, "Load an image file")

        paste_btn = ttk.Button(button_frame, text="Paste from Clipb", command=self.paste_from_clipboard, width=15, style="TButton")
        paste_btn.pack(side=tk.LEFT, padx=5)
        Tooltip(paste_btn, "Paste an image from clipboard")

        clear_btn = ttk.Button(button_frame, text="Clear", command=self.clear_all, width=15, style="TButton")
        clear_btn.pack(side=tk.LEFT, padx=5)
        Tooltip(clear_btn, "Clear all fields")

        copy_results_btn = ttk.Button(button_frame, text="Copy Results", command=self.copy_results, width=15, style="TButton")
        copy_results_btn.pack(side=tk.LEFT, padx=5)
        Tooltip(copy_results_btn, "Copy API results to clipboard")

        copy_extracted_btn = ttk.Button(button_frame, text="Copy Extracted", command=self.copy_extracted_text, width=15, style="TButton")
        copy_extracted_btn.pack(side=tk.LEFT, padx=5)
        Tooltip(copy_extracted_btn, "Copy extracted text to clipboard")

        # Extracted text with label and scrollbar
        extracted_frame = tk.Frame(right_frame, bg="#f0f0f0")
        extracted_frame.pack(pady=5, fill=tk.BOTH, expand=True)
        tk.Label(extracted_frame, text="Extracted Text", font=("Arial", 12, "bold"), bg="#f0f0f0").pack(anchor="w")
        self.extracted_text_box = tk.Text(extracted_frame, height=10, width=80, font=("Arial", 12), bg="#e8e8e8")
        scrollbar1 = tk.Scrollbar(extracted_frame, command=self.extracted_text_box.yview)
        self.extracted_text_box.config(yscrollcommand=scrollbar1.set)
        self.extracted_text_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar1.pack(side=tk.RIGHT, fill=tk.Y)

        # Tarkov results with label and scrollbar
        results_frame = tk.Frame(right_frame, bg="#f0f0f0")
        results_frame.pack(pady=5, fill=tk.BOTH, expand=True)
        tk.Label(results_frame, text="Tarkov API Results", font=("Arial", 12, "bold"), bg="#f0f0f0").pack(anchor="w")
        self.tarkov_results_text = tk.Text(results_frame, height=10, width=80, font=("Arial", 12), state=tk.DISABLED, bg="#e8e8e8")
        scrollbar2 = tk.Scrollbar(results_frame, command=self.tarkov_results_text.yview)
        self.tarkov_results_text.config(yscrollcommand=scrollbar2.set)
        self.tarkov_results_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar2.pack(side=tk.RIGHT, fill=tk.Y)

        # Bottom: Progress and status
        status_frame = tk.Frame(self.root, bg="#d0d0d0", bd=2, relief=tk.RAISED)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=2)
        self.status_label = tk.Label(status_frame, text="Ready", font=("Arial", 14, "bold"), bg="#d0d0d0")
        self.status_label.pack(fill=tk.X, padx=10, pady=5)
        self.progress_bar = ttk.Progressbar(self.root, length=1000, mode="indeterminate")
        self.progress_bar.pack(side=tk.BOTTOM, pady=5)

    def set_status(self, state: AppState, message: str = None):
        status_text = f"{state.value}" + (f" - {message}" if message else "")
        self.status_label.config(text=status_text)
        colors = {
            AppState.READY: ("green", "#e0ffe0"),
            AppState.PROCESSING: ("blue", "#e0e0ff"),
            AppState.COMPLETED: ("green", "#e0ffe0"),
            AppState.ERROR: ("red", "#ffe0e0"),
            AppState.SEARCHING: ("blue", "#e0e0ff"),
            AppState.LOADING: ("blue", "#e0e0ff")
        }
        fg_color, bg_color = colors.get(state, ("black", "#d0d0d0"))
        self.status_label.config(fg=fg_color, bg=bg_color)
        self.status_label.master.config(bg=bg_color)
        self.root.update_idletasks()
        logging.info(f"Status updated to: {status_text}")

    def toggle_gpu(self):
        self.settings.ocr_use_gpu = self.gpu_var.get()
        self.ocr = OCRProcessor(self.settings.ocr_use_gpu)
        self.settings.save_settings()
        self.set_status(AppState.READY, f"OCR GPU set to: {self.settings.ocr_use_gpu}")

    def copy_results(self):
        results = self.tarkov_results_text.get("1.0", tk.END).strip()
        if not results:
            self.set_status(AppState.ERROR, "No results to copy.")
            return
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(results)
            self.root.update()
            self.set_status(AppState.COMPLETED, "API results copied to clipboard.")
        except Exception as e:
            self.set_status(AppState.ERROR, f"Error copying results: {e}")

    def copy_extracted_text(self):
        text = self.extracted_text_box.get("1.0", tk.END).strip()
        if not text:
            self.set_status(AppState.ERROR, "No extracted text to copy.")
            return
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.root.update()
            self.set_status(AppState.COMPLETED, "Extracted text copied to clipboard.")
        except Exception as e:
            self.set_status(AppState.ERROR, f"Error copying extracted text: {e}")

    def load_image(self):
        filename = filedialog.askopenfilename(filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.gif;*.bmp;*.webp"), ("All files", "*.*")])
        if filename:
            self.image_display.load_and_process_image(filename, filename=filename)
            self.extract_text()

    def paste_from_clipboard(self):
        clipboard_content = ImageGrab.grabclipboard()
        if isinstance(clipboard_content, Image.Image):
            self.image_display.load_and_process_image(clipboard_content)
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
        term_lower = term.lower()
        if term_lower in self.autocorrect_rules:
            return self.autocorrect_rules[term_lower]
        if self.settings.use_item_corrections and self.item_name_lookup:
            best_match, score = process.extractOne(term_lower, self.item_name_lookup.keys())
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
                logging.warning(f"No API data found for item: {item_name}")

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