# enums.py
from enum import Enum

class AppState(Enum):
    READY = "Ready"
    LOADING = "Loading..."
    PROCESSING = "Processing..."
    SEARCHING = "Searching Tarkov.dev..."
    COMPLETED = "Completed"
    ERROR = "Error"
