import os
import json
import asyncio
from uuid import uuid4
from utils.product_search.match_engine import match_product_entry
from utils.product_search.utils_native.utils import normalize_name
from utils.boq_context_extraction.folder_helpers import create_output_folder, create_intermediate_results_folders
import logging
logger = logging.getLogger(__name__)

MAX_CONCURRENT_SEARCHES = 10

def match_single_entry(entry, i, search_logs_folder):
    try:
        result = match_product_entry(i, entry, log_dir=search_logs_folder)

        return {
            "index": i,
            "fetched_product_name": result["top_match"]["match_details"]["raw_product_name"],
            "list_of_product_ids": result["top_match"]["match_details"].get("list_of_product_ids", []),
            "prompt_tokens": result["prompt_tokens"],
            "completion_tokens": result["completion_tokens"]
        }    
    except Exception as e:
        logger.error(f"⚠️ Matching failed for entry {i}: {e}")
        return None

async def match_entries_for_sheet(metadata: dict):
    file_path = metadata["file_path"]
    sheet_name = metadata["sheet_name"]
    output_folder = create_output_folder(file_path, sheet_name)
    _, _, final_output_folder, search_logs_folder = create_intermediate_results_folders(output_folder)

    original_path = os.path.join(final_output_folder, "final_product_entries.json")
    updated_path = os.path.join(final_output_folder, "final_product_entries_with_matches.json")

    with open(original_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    products = data.get("products_entries", []) # This products list is a reference to the list inside data
    sem = asyncio.Semaphore(MAX_CONCURRENT_SEARCHES)

    async def limited(entry, i):
        async with sem:
            return await asyncio.to_thread(match_single_entry, entry, i, search_logs_folder)

    tasks = [limited(entry, i) for i, entry in enumerate(products)]
    results = await asyncio.gather(*tasks)
    # print(results)
    total_prompt_tokens = 0
    total_completion_tokens = 0

    for r in results:
        if r is None:
            continue
        i = r["index"]
        products[i]["index"] = i
        products[i]["list_of_product_ids"] = r["list_of_product_ids"]
        products[i]["fetched_product_name"] = r["fetched_product_name"]
        total_prompt_tokens += r["prompt_tokens"]
        total_completion_tokens += r["completion_tokens"]

    # Write to a new file (don’t overwrite original)
    with open(updated_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return total_prompt_tokens, total_completion_tokens


if __name__ == "__main__":

    output_folder = "/home/student2/Documents/GitHub/1st_AI_Project_Kothari/boq_extraction_2/pipeline_copy_2/outputs/Miraj-BOQ_Electrical___Instrumentation/Table_2"

    # Load metadata.json
    metadata_path = os.path.join(output_folder, "metadata.json")
    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    results = asyncio.run(match_entries_for_sheet(metadata))
    print(results)
