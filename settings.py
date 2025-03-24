# settings.py
import configparser
import dataclasses
import json
import os
import logging
from utils import resource_path

@dataclasses.dataclass
class Config:
    API_URL: str = "https://api.tarkov.dev/graphql"
    CACHE_TTL: int = 3600
    REQUEST_DELAY: float = 0.2
    MAX_RETRIES: int = 3
    LOG_FILE: str = "logs/screenshot_ingestor.log"
    LOG_LEVEL: int = logging.INFO
    SETTINGS_FILE: str = "data/settings.ini"
    AUTOCORRECT_FILE: str = "data/autocorrect_rules.json"
    ITEM_NAMES_FILE: str = "data/item_names.json"
    FUZZY_MATCH_THRESHOLD: int = 80
    DEFAULT_IMAGE_WIDTH: int = 500
    DEFAULT_IMAGE_HEIGHT: int = 500

class AppSettings:
    def __init__(self, settings_file: str = Config.SETTINGS_FILE):
        self.config = configparser.ConfigParser()
        self.settings_file = resource_path(settings_file)
        self.ocr_use_gpu: bool = True
        self.use_item_corrections: bool = True
        self.load_settings()

    def load_settings(self):
        try:
            self.config.read(self.settings_file)
            self.ocr_use_gpu = self.config.getboolean("Settings", "ocr_use_gpu", fallback=True)
            self.use_item_corrections = self.config.getboolean("Settings", "use_item_corrections", fallback=True)
            logging.info("Settings loaded successfully from INI.")
        except Exception as e:
            logging.error(f"Error loading settings: {e}", exc_info=True)
            self.save_settings()

    def save_settings(self):
        self.config["Settings"] = {
            "ocr_use_gpu": str(self.ocr_use_gpu),
            "use_item_corrections": str(self.use_item_corrections),
        }
        try:
            with open(self.settings_file, "w") as configfile:
                self.config.write(configfile)
            logging.info("Settings saved successfully to INI.")
        except Exception as e:
            logging.error(f"Error saving settings: {e}", exc_info=True)

def load_autocorrect_rules(filename: str = Config.AUTOCORRECT_FILE) -> dict:
    try:
        with open(resource_path(filename), 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error loading autocorrect rules: {e}", exc_info=True)
        return {}

def load_item_name_lookup(filename: str = Config.ITEM_NAMES_FILE) -> dict:
    try:
        with open(resource_path(filename), 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error loading item names: {e}", exc_info=True)
        return {}