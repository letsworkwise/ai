import os
import time
import pandas as pd
import json
from typing import Dict
import asyncio

from utils.boq_context_extraction.excel_helpers import load_and_clean_excel, save_output_excel
from utils.boq_context_extraction.folder_helpers import create_output_folder
from utils.boq_context_extraction.llm_helpers import extract_boq_context
from utils.boq_context_extraction.header_helpers import load_first_n_rows_as_markdown, find_header_start_idx, find_max_column_idx
import logging
logger = logging.getLogger(__name__)

def prepare_metadata_for_one_sheet(file_path: str, sheet_name: str, custom_instructions: str = "") -> Dict:
    start_time = time.time()

    # Step 1: Create output folder for this sheet
    output_folder = create_output_folder(file_path, sheet_name)

    # Step 2: Load and clean sheet
    cleaned_df = load_and_clean_excel(file_path, sheet_name)

    # Step 3: Extract context and header
    first_rows_md = load_first_n_rows_as_markdown(cleaned_df, num_rows=20)
    content, tokens_used_ctx = extract_boq_context(first_rows_md, custom_instructions)

    header_md = content.get("header_rows", "")
    context_md = content.get("context_rows", "")

    # Step 4: Find schedule start and isolate the product schedule
    # if context_md == "":
    #     schedule_start_idx = 0
    # else:
    schedule_start_idx = find_header_start_idx(cleaned_df, header_md)
    max_col_idx = find_max_column_idx(cleaned_df, header_md)
    
    # Defensive slicing to keep only real columns
    df_schedule = cleaned_df.iloc[schedule_start_idx:, :max_col_idx].reset_index(drop=True)

    schedule_path = os.path.join(output_folder, "schedule_only.xlsx")
    save_output_excel(schedule_path, df_schedule)
    logger.info(f"✅ Schedule saved to {schedule_path}")

    # Step 5: Save extracted metadata into a small JSON
    metadata = {
        "file_path": file_path,
        "sheet_name": sheet_name,
        "output_folder": output_folder,
        "schedule_path": schedule_path,
        "context_md": context_md,
        "header_md": header_md,
        "schedule_start_idx": schedule_start_idx,
        "max_col_idx": max_col_idx,
        "tokens_used_ctx": tokens_used_ctx,
    }

    metadata_path = os.path.join(output_folder, "metadata.json")
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"✅ Metadata prepared for sheet '{sheet_name}' in {time.time() - start_time:.2f}s")

    return metadata



if __name__ == "__main__":
    file_path = os.path.join("inputs", "R4_ELECTRICAL OFFER  CITCO (2).xlsx")
    sheet_name = "FIRE PUMP ROOM"
    custom_instructions = ""

    metadata = prepare_metadata_for_one_sheet(file_path, sheet_name, custom_instructions)

    logger.info("\n✅ Returned Metadata:")
    for k, v in metadata.items():
        logger.info(f"{k}: {v}")