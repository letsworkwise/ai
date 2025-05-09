import os
import json
from typing import List, Tuple, Dict
import logging

from utils.llm_interface.calling import llm_call_basic_with_llmcallfailure_exception
from utils.prompts.variant_merging_prompts import (
    system_prompt_merge_product_entries, make_user_prompt_for_merge
)

logger = logging.getLogger(__name__)

# --- Helper Functions ---

def load_chunk_output(chunk_output_folder: str, start: int, end: int) -> Dict:
    file_path = os.path.join(chunk_output_folder, f"page_output_{start}_{end}.json")
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_chunk_output(chunk_output_folder: str, start: int, end: int, data: Dict):
    file_path = os.path.join(chunk_output_folder, f"page_output_{start}_{end}.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_two_chunks(chunk_output_folder: str, chunk_ranges: List[Tuple[int, int]], i: int) -> Tuple[Dict, Dict, int, int, int, int]:
    start1, end1 = chunk_ranges[i]
    start2, end2 = chunk_ranges[i + 1]
    data1 = load_chunk_output(chunk_output_folder, start1, end1)
    data2 = load_chunk_output(chunk_output_folder, start2, end2)
    return data1, data2, start1, end1, start2, end2

def prepare_boundary_merge_request(data1: Dict, data2: Dict) -> Tuple[Dict, List[Dict]]:
    last_entry = data1["products"][-1] if data1["products"] else None
    spec_only_entries = [prod for prod in data2["products"] if prod.get("is_only_product_specs_entry") == "Y"] or None
    return last_entry, spec_only_entries

def call_llm_for_boundary_merge(last_entry: Dict, spec_only_entries: List[Dict]) -> Tuple[List[Dict], Tuple[int, int]]:
    user_prompt = make_user_prompt_for_merge(last_entry, spec_only_entries)
    response, tokens_used = llm_call_basic_with_llmcallfailure_exception(
        system_prompt_merge_product_entries,
        user_prompt
    )
    corrected_entries = response.get("products", [])
    return corrected_entries, tokens_used

def merge_boundary_entries(data1: Dict, data2: Dict, corrected_entries: List[Dict], is_first_pair: bool, is_last_pair: bool) -> Tuple[Dict, Dict]:
    if is_first_pair:
        data1["products"] = data1["products"][:-1]
    else:
        data1["products"] = [prod for prod in data1["products"] if prod.get("is_only_product_specs_entry") != "Y"][:-1]

    data1["products"].extend(corrected_entries)

    if is_last_pair:
        data2["products"] = [prod for prod in data2["products"] if prod.get("is_only_product_specs_entry") != "Y"]
        return data1, data2
    else:
        return data1, None

def save_corrected_chunks(boundaries_folder: str, start1: int, end1: int, start2: int, end2: int, updated_data1: Dict, updated_data2: Dict):
    file1 = os.path.join(boundaries_folder, f"page_output_{start1}_{end1}.json")
    with open(file1, "w", encoding="utf-8") as f1:
        json.dump(updated_data1, f1, indent=2, ensure_ascii=False)

    if updated_data2:
        file2 = os.path.join(boundaries_folder, f"page_output_{start2}_{end2}.json")
        with open(file2, "w", encoding="utf-8") as f2:
            json.dump(updated_data2, f2, indent=2, ensure_ascii=False)
