import os
import json
import asyncio
import pandas as pd
from typing import List, Tuple
import logging

from utils.llm_interface.calling import llm_call_basic_with_llmcallfailure_exception
from utils.prompts.user_prompts import user_prompt_basic
from utils.prompts.variant_extraction_prompts import system_prompt_product_entries_my_version
from utils.boq_context_extraction.folder_helpers import create_output_folder
from utils.common_utils.json_helpers import save_output_json
from utils.common_utils.markdown_helpers import format_batch_as_markdown
from utils.process_schedule.generate_chunk_ranges import generate_and_save_chunk_ranges

logger = logging.getLogger(__name__)

def call_llm_for_one_chunk(
    df_schedule: pd.DataFrame,
    start_row: int,
    chunk_size: int,
    sheet_name: str,
    chunk_output_folder: str,
    boq_context_md: str,
    boq_header_md: str,
    is_first_chunk: bool
) -> Tuple[int, int]:
    end_row = min(start_row + chunk_size, len(df_schedule))

    # Format batch into markdown table
    markdown_table = format_batch_as_markdown(
        df_schedule, boq_header_md,
        start_idx=start_row, batch_size=chunk_size
    )

    # Prepare original rows info
    original_rows_info = {
        "row_range": [df_schedule.iloc[start_row].name, df_schedule.iloc[end_row - 1].name],
        "original_rows": df_schedule.iloc[start_row:end_row].to_dict(orient="records")
    }

    # LLM call
    content, tokens_used = llm_call_basic_with_llmcallfailure_exception(
        system_prompt_product_entries_my_version,
        user_prompt_basic.format(text=markdown_table),
    )

    # Final output structure
    final_output = {
        "sheet_name": sheet_name,
        "boq_context": boq_context_md,
        "products": content.get("products", []),
        "original_rows_info": original_rows_info,
        "token_usage": {
            "prompt_tokens": tokens_used[0],
            "completion_tokens": tokens_used[1]
        }
    }

    output_path = os.path.join(chunk_output_folder, f"page_output_{start_row}_{end_row}.json")
    save_output_json(output_path, final_output)

    return tokens_used[0], tokens_used[1]


async def process_all_chunks(
    schedule_path: str,
    output_folder: str,
    sheet_name: str,
    boq_context_md: str,
    boq_header_md: str,
    chunk_size: int = 20
) -> Tuple[List[Tuple[int, int]], int, int]:
    # create_output_folder(output_folder, sheet_name="dummy")  # Just double-check folders, this has to be at sheet level

    # Load schedule
    df_schedule = pd.read_excel(schedule_path)

    # Generate chunk ranges and save
    chunk_ranges = generate_and_save_chunk_ranges(schedule_path, output_folder, chunk_size)

    chunk_output_folder = os.path.join(output_folder, "chunking", "chunk_outputs")

    total_prompt_tokens, total_completion_tokens = 0, 0

    # Async process each chunk
    async def process_chunk(start_idx, is_first):
        return await asyncio.to_thread(
            call_llm_for_one_chunk,
            df_schedule, start_idx, chunk_size, sheet_name,
            chunk_output_folder, boq_context_md, boq_header_md, is_first
        )

    tasks = [
        process_chunk(start_idx, is_first=(idx == 0))
        for idx, (start_idx, _) in enumerate(chunk_ranges)
    ]

    results = await asyncio.gather(*tasks)

    for prompt_tokens, completion_tokens in results:
        total_prompt_tokens += prompt_tokens
        total_completion_tokens += completion_tokens

    return chunk_ranges, total_prompt_tokens, total_completion_tokens



if __name__ == "__main__":
    import asyncio
    from utils.logging_utils.logging_config import setup_logging
    setup_logging()
    logging.getLogger("httpx").setLevel(logging.WARNING)  #### suppress HTTP 200 logs

    output_folder = "/home/student2/Documents/GitHub/1st_AI_Project_Kothari/boq_extraction_2/pipeline_copy/outputs/R4_ELECTRICAL_OFFER__CITCO__2_/FIRE_PUMP_ROOM"
    schedule_path = os.path.join(output_folder, "schedule_only.xlsx")
    sheet_name = "FIRE_PUMP_ROOM"
    chunk_size = 10

    # Load metadata.json
    metadata_path = os.path.join(output_folder, "metadata.json")
    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    boq_context_md = metadata.get("context_md", "")
    boq_header_md = metadata.get("header_md", "")

    asyncio.run(process_all_chunks(
        schedule_path, output_folder, sheet_name,
        boq_context_md, boq_header_md, chunk_size
    ))