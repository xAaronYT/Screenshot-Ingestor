# api.py
import requests
import json
import time
import threading
from typing import Optional, List
from settings import Config
import logging

class TarkovAPI:
    def __init__(self):
        self.cache = {}
        self.lock = threading.Lock()

    def get_item_data(self, item_name: str) -> Optional[List[dict]]:
        """Fetches item data from the API, using a cache."""
        item_name = item_name.strip()
        with self.lock:
            if item_name in self.cache:
                cached_data, timestamp = self.cache[item_name]
                if time.time() - timestamp < Config.CACHE_TTL:
                    logging.debug(f"Cache hit for {item_name}")
                    return cached_data
                else:
                    logging.debug(f"Cache expired for {item_name}")
                    del self.cache[item_name]

        logging.info(f"Fetching data from API for {item_name}")
        query = """
        query itemsByName($name: String!) {
          itemsByName(name: $name) {
            name
            shortName
            avg24hPrice
            basePrice
            wikiLink
          }
        }
        """
        variables = {"name": item_name}

        for attempt in range(Config.MAX_RETRIES):
            try:
                response = requests.post(Config.API_URL, json={'query': query, 'variables': variables})
                response.raise_for_status()
                data = response.json()
                item_data = data.get('data', {}).get('itemsByName', [])
                with self.lock:
                    if item_name.lower() == "diary":
                        item_data = [item for item in item_data if "slim diary" not in item["name"].lower()]
                    self.cache[item_name] = (item_data, time.time())
                time.sleep(Config.REQUEST_DELAY)
                return item_data
            except Exception as e:
                logging.error(f"API error for {item_name} (Attempt {attempt + 1}/{Config.MAX_RETRIES}): {e}", exc_info=True)
                if attempt + 1 == Config.MAX_RETRIES:
                    return None