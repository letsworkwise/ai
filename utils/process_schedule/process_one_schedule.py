import os
import pandas as pd
from typing import Dict, Tuple
import logging

from utils.boq_context_extraction.folder_helpers import create_output_folder, create_intermediate_results_folders
from utils.process_schedule.generate_chunk_ranges import generate_and_save_chunk_ranges
from utils.process_schedule.process_chunks_copy import process_all_chunks
from utils.process_schedule.merge_outputs import merge_final_outputs

logger = logging.getLogger(__name__)

def process_one_schedule(metadata: Dict) -> Tuple[int, int]:
    sheet_name = metadata["sheet_name"]
    output_folder = metadata["output_folder"]
    schedule_path = metadata["schedule_path"]
    boq_context_md = metadata["context_md"]
    boq_header_md = metadata["header_md"]
    tokens_used_ctx = metadata.get("tokens_used_ctx", (0, 0))  # (prompt_tokens, completion_tokens)

    # --- Ensure folders exist ---
    create_output_folder(metadata["file_path"], metadata["sheet_name"])
    create_intermediate_results_folders(output_folder)

    # --- Step 1: Process all chunks ---
    chunk_ranges, token_chunks_prompt, token_chunks_completion = process_all_chunks(
        schedule_path, output_folder, sheet_name, boq_context_md, boq_header_md, chunk_size = 30
    )

    # --- Step 3: Merge final output ---
    merge_final_outputs(
        output_folder,
        chunk_ranges,
        sheet_name,
        boq_context_md,
        boq_header_md
    )

    # --- Final token counts ---
    total_prompt_tokens = tokens_used_ctx[0] + token_chunks_prompt
    total_completion_tokens = tokens_used_ctx[1] + token_chunks_completion

    logger.info(f"✅ Completed processing sheet: {sheet_name}")

    return total_prompt_tokens, total_completion_tokens


if __name__ == "__main__":
    import json
    import os
    from utils.logging_utils.logging_config import setup_logging

    setup_logging()
    logging.getLogger("httpx").setLevel(logging.WARNING)  # Suppress HTTP 200 logs

    # 🛠️ Update this to your sheet's output folder
    # output_folder = "/home/student2/Documents/GitHub/1st_AI_Project_Kothari/boq_extraction_2/pipeline_copy_2/outputs/R4_ELECTRICAL_OFFER__CITCO__2_/FIRE_PUMP_ROOM"
    output_folder = "/home/student2/Documents/GitHub/1st_AI_Project_Kothari/boq_extraction_2/pipeline_copy_2/outputs/Miraj-BOQ_Electrical___Instrumentation/Table_2"

    # Load metadata.json
    metadata_path = os.path.join(output_folder, "metadata.json")
    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    # # In case metadata is missing some fields manually add if needed
    # metadata["output_folder"] = output_folder
    # metadata["schedule_path"] = os.path.join(output_folder, "schedule_only.xlsx")
    # metadata["file_path"] = "dummy_file_path.xlsx"  # 🛠️ Dummy for create_output_folder

    # Now call the full processing function
    prompt_tokens, completion_tokens = process_one_schedule(metadata)

    print(f"\n✅ Sheet processed successfully!")
    print(f"🧮 Total Prompt Tokens Used: {prompt_tokens}")
    print(f"🧮 Total Completion Tokens Used: {completion_tokens}")
