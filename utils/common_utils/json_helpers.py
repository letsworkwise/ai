import json
import logging

logger = logging.getLogger(__name__)

def save_output_json(filepath: str, data: dict):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved output to {filepath}")
