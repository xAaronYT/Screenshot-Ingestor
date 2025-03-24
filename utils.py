# utils.py
import os
import sys
import logging

def resource_path(relative_path: str) -> str:
    """Get absolute path to resource, works for dev and for PyInstaller."""
    try:
        base_path = sys._MEIPASS
        logging.debug(f"Running as executable. _MEIPASS: {base_path}")
    except AttributeError:
        base_path = os.path.abspath(".")
        logging.debug(f"Running as script. Base path: {base_path}")
    full_path = os.path.join(base_path, relative_path)
    logging.debug(f"Resolved resource path: {full_path}")
    return full_path

def preprocess_search_term(term: str) -> str:
    """Preprocesses a search term, preserving spaces and some punctuation."""
    term = term.strip()
    # Keep alphanumeric, spaces, and some punctuation (e.g., hyphens)
    term = ''.join(c for c in term if c.isalnum() or c in " -")
    return term  # Don't lowsercase here; let autocorrect_term handle case