import os
import pandas as pd
import asyncio
import json
from typing import Tuple, List

# from utils.logging_utils.logging_config import sheet_name_var
from utils.prepare_metadata.prepare_metadata_for_one_sheet import prepare_metadata_for_one_sheet
from utils.process_schedule.process_one_schedule import process_one_schedule
from utils.boq_context_extraction.folder_helpers import create_output_folder
from utils.common_utils.dynamic_semaphore import get_dynamic_semaphore

import logging
logger = logging.getLogger(__name__)

async def run_all_sheets(file_path: str, custom_instructions: str = "") -> Tuple[int, int, float, List[dict]]:
    start_time = asyncio.get_event_loop().time()
    # logger.info(f"========= Phase 2: Schedules processing for all sheets=========")

    xls = pd.ExcelFile(file_path)

    total_prompt_tokens = 0
    total_completion_tokens = 0
    sheet_errors = []

    dynamic_concurrency = get_dynamic_semaphore()
    sem = asyncio.Semaphore(dynamic_concurrency)
    # sem = asyncio.Semaphore(3)  # Limit concurrency if needed

    async def run_single_sheet(sheet_name: str):
        # sheet_name_var.set(sheet_name)
        async with sem:
            try:
                # metadata = prepare_metadata_for_one_sheet(file_path, sheet_name, custom_instructions)
                output_folder = create_output_folder(file_path, sheet_name)
                # Load metadata.json
                metadata_path = os.path.join(output_folder, "metadata.json")
                with open(metadata_path, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
                prompt_tokens, completion_tokens = await asyncio.to_thread(process_one_schedule, metadata)
                return prompt_tokens, completion_tokens, None
            except Exception as e:
                return 0, 0, str(e)

    tasks = [run_single_sheet(sheet) for sheet in xls.sheet_names]
    results = await asyncio.gather(*tasks)

    for sheet_name, result in zip(xls.sheet_names, results):
        prompt_tokens, completion_tokens, error = result
        if error:
            logger.warning(f"⚠️ Skipping sheet '{sheet_name}' due to error: {error}")
            sheet_errors.append({"sheet": sheet_name, "error": error})
        else:
            total_prompt_tokens += prompt_tokens
            total_completion_tokens += completion_tokens

    elapsed_time = asyncio.get_event_loop().time() - start_time    

    # logger.info(f"=========Phase 2 completed: All sheets processed in {elapsed_time:.2f} seconds=========")

    return total_prompt_tokens, total_completion_tokens, elapsed_time, sheet_errors


if __name__ == "__main__":
    import asyncio
    from utils.logging_utils.logging_config import setup_logging

    setup_logging()

    file_path = "/path/to/your/full_boQ_file.xlsx"  # 🛠️ Change this

    results = asyncio.run(run_all_sheets(file_path))
    prompt_tokens, completion_tokens, elapsed_time, sheet_errors = results

    print("\n✅ All sheets processed!")
    print(f"🧮 Total Prompt Tokens Used: {prompt_tokens}")
    print(f"🧮 Total Completion Tokens Used: {completion_tokens}")
    print(f"⏱️ Total Time: {elapsed_time:.2f} seconds")
    if sheet_errors:
        print(f"⚠️ Sheets with errors: {sheet_errors}")
