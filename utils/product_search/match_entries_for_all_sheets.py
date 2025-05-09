
import pandas as pd
import asyncio
import os
import json
from utils.product_search.match_entries_for_sheet_async import match_entries_for_sheet
from utils.boq_context_extraction.folder_helpers import create_output_folder
import logging
logger = logging.getLogger(__name__)

async def match_entries_for_all_sheets(file_path: str):
    start_time = asyncio.get_event_loop().time() 
    xls = pd.ExcelFile(file_path)
    # all_results = []
    total_prompt = 0
    total_completion = 0

    for sheet_name in xls.sheet_names:
        logger.info(f"🔁 Processing sheet: {sheet_name}")
        try:
            output_folder = create_output_folder(file_path, sheet_name)
            metadata_path = os.path.join(output_folder, "metadata.json")
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            prompt, completion = await match_entries_for_sheet(metadata)
            total_prompt += prompt
            total_completion += completion
            # all_results.append({
            #     "sheet_name": sheet_name,
            #     "prompt_tokens": prompt,
            #     "completion_tokens": completion
            # })
        except Exception as e:
            logger.error(f"❌ Failed for sheet {sheet_name}: {e}")
    end_time = asyncio.get_event_loop().time()
    total_time = end_time - start_time
    logger.info(f"🎯 Matching complete for all sheets: {total_time} seconds")
    return {
        "total_prompt_tokens": total_prompt,
        "total_completion_tokens": total_completion,
        "total_time": total_time
        # "per_sheet": all_results
    }


if __name__ == "__main__":
    file_path = "/home/student2/Documents/GitHub/1st_AI_Project_Kothari/boq_extraction_2/pipeline_copy_2/inputs/BOQ-BPIL-FG WAREHOUSE-GODOWN-COLORANT (1).xlsx"
    summary = asyncio.run(match_entries_for_all_sheets(file_path))
    print("\n🎯 Matching complete for all sheets:")
    print(summary)

