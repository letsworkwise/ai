import os
import json
from typing import List, Tuple
import logging

from utils.boq_context_extraction.folder_helpers import create_output_folder

logger = logging.getLogger(__name__)

def get_chunk_ranges(total_rows: int, chunk_size: int) -> List[Tuple[int, int]]:
    return [(i, min(i + chunk_size, total_rows)) for i in range(0, total_rows, chunk_size)]

def generate_and_save_chunk_ranges(
    schedule_path: str,
    output_folder: str,
    chunk_size: int = 20
) -> List[Tuple[int, int]]:

    # Double-check folders exist
    # create_output_folder(output_folder, sheet_name="dummy")  # sheet_name unused here safely

    # Load schedule
    import pandas as pd
    df_schedule = pd.read_excel(schedule_path)

    total_rows = len(df_schedule)
    chunk_ranges = get_chunk_ranges(total_rows, chunk_size)

    # Save chunk_ranges to JSON
    chunking_folder = os.path.join(output_folder, "chunking")
    chunk_ranges_path = os.path.join(chunking_folder, "chunk_ranges.json")

    with open(chunk_ranges_path, "w", encoding="utf-8") as f:
        json.dump(chunk_ranges, f, indent=2)

    logger.info(f"✅ Saved {len(chunk_ranges)} chunk ranges to {chunk_ranges_path}")

    return chunk_ranges



if __name__ == "__main__":
    schedule_path = "/home/student2/Documents/GitHub/1st_AI_Project_Kothari/boq_extraction_2/pipeline copy/outputs/R4_ELECTRICAL_OFFER__CITCO__2_/FIRE_PUMP_ROOM/schedule_only.xlsx"
    output_folder = "/home/student2/Documents/GitHub/1st_AI_Project_Kothari/boq_extraction_2/pipeline copy/outputs/R4_ELECTRICAL_OFFER__CITCO__2_/FIRE_PUMP_ROOM"
    chunk_size = 20

    generate_and_save_chunk_ranges(schedule_path, output_folder, chunk_size)

