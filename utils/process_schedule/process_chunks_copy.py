import os
import json
import asyncio
import pandas as pd
from typing import List, Tuple, Dict
import logging

from utils.llm_interface.calling import llm_call_basic_with_llmcallfailure_exception
from utils.prompts.user_prompts import user_prompt_basic
# from utils.prompts.variant_extraction_prompts import system_prompt_product_entries_my_version
# from utils.prompts.variant_extraction_prompts import system_prompt_product_entries_v2n
from utils.prompts.variant_extraction_prompts import system_prompt_product_entries_v2n_2
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
    boundaries_folder: str,
    chunk_output_folder: str,
    boq_context_md: str,
    boq_header_md: str,
    # context_from_previous_chunk: str,
    # last_extracted_product_entry_from_previous_chunk: Dict,
    section_context_from_last_extracted_product_block_in_previous_chunk: str,
    last_extracted_product_block_in_previous_chunk: Dict,
    is_first_chunk: bool,
    is_last_chunk: bool
) -> Tuple[int, int, Dict, str]:
    end_row = min(start_row + chunk_size, len(df_schedule))

    # Format batch into markdown table
    markdown_table = format_batch_as_markdown(
        df_schedule, boq_header_md,
        start_idx=start_row, batch_size=chunk_size
    )

    original_rows_info = {
        "row_range": [df_schedule.iloc[start_row].name, df_schedule.iloc[end_row - 1].name],
        "original_rows": df_schedule.iloc[start_row:end_row].to_dict(orient="records")
    }

    # system_prompt = system_prompt_product_entries_my_version 
    # system_prompt = system_prompt_product_entries_v2n
    system_prompt = system_prompt_product_entries_v2n_2
    user_prompt = user_prompt_basic.format(text=f"Markdown Table: \n{markdown_table}")
    if not is_first_chunk:
        # if last_extracted_product_entry_from_previous_chunk:
        #     user_prompt = f"""last_extracted_product_entry_from_previous_chunk: {last_extracted_product_entry_from_previous_chunk}\n\n""" + user_prompt
        # if context_from_previous_chunk:
        #     user_prompt = f"""context_from_previous_chunk: {context_from_previous_chunk}\n\n""" + user_prompt
        if last_extracted_product_block_in_previous_chunk:
            user_prompt = f"""last_extracted_product_block_in_previous_chunk: {last_extracted_product_block_in_previous_chunk}\n\n""" + user_prompt
        if section_context_from_last_extracted_product_block_in_previous_chunk:
            user_prompt = f"""section_context_from_last_extracted_product_block_in_previous_chunk: {section_context_from_last_extracted_product_block_in_previous_chunk}\n\n""" + user_prompt

    content, tokens_used = llm_call_basic_with_llmcallfailure_exception(
        system_prompt,
        user_prompt
    )

    if start_row==20 or start_row==40: 
        print(f"start_row: {start_row}")
        print(f"user_prompt: {user_prompt}")
        print(f"content: {content}")

    # Extract product entries from product blocks
    final_product_entries = []
    last_extracted_product_block_in_previous_chunk = content["product_blocks"][-1]
    section_context_from_last_extracted_product_block_in_previous_chunk= last_extracted_product_block_in_previous_chunk.get("section_context_for_this_product_block", "")

    for block in content["product_blocks"][:-1]:
        section_context = block["section_context_for_this_product_block"]
        # is_group = block["is_group"]
        
        for variant in block["list_of_product_variants"]:
            variant_entry = {
                "section_context_for_this_product_block": section_context,
                **variant,  # unpack existing fields
                # "is_group": is_group
            }
            final_product_entries.append(variant_entry)

    

    final_output = {
        "sheet_name": sheet_name,
        "boq_context": boq_context_md,
        # "product_entries": content.get("product_entries", []),
        "product_entries": final_product_entries,       # this is the final product entries when extracting product entries from product blocks
        "original_rows_info": original_rows_info,
        "token_usage": {
            "prompt_tokens": tokens_used[0],
            "completion_tokens": tokens_used[1]
        }
    }

    output_path = os.path.join(chunk_output_folder, f"page_output_{start_row}_{end_row}.json")
    save_output_json(output_path, final_output)

    output_path_dropped_last_product_entry = os.path.join(boundaries_folder, f"page_output_dropped_last_product_entry_{start_row}_{end_row}.json")

    # when extracting product entries from product blocks
    if final_product_entries:
        if not last_extracted_product_block_in_previous_chunk: # very defensive
            logging.info(f"Processed rows {start_row} to {end_row}")
            return None, None, tokens_used[0], tokens_used[1]
        elif last_extracted_product_block_in_previous_chunk:
            if not is_last_chunk:
                save_output_json(output_path_dropped_last_product_entry, final_output)
            elif is_last_chunk:
                for variant in last_extracted_product_block_in_previous_chunk["list_of_product_variants"]:
                    variant_entry = {
                        "section_context_for_this_product_block": section_context_from_last_extracted_product_block_in_previous_chunk,
                        **variant,  # unpack existing fields
                        # "is_group": is_group
                    }
                    final_product_entries.append(variant_entry)
                
                final_output_ = {
                    "sheet_name": sheet_name,
                    "boq_context": boq_context_md,
                    "product_entries": final_product_entries,       # this is the final product entries when extracting product entries from product blocks
                    "original_rows_info": original_rows_info,
                    "token_usage": {
                        "prompt_tokens": tokens_used[0],
                        "completion_tokens": tokens_used[1]
                    }
                }

                save_output_json(output_path_dropped_last_product_entry, final_output_)
            logging.info(f"Processed rows {start_row} to {end_row}")
            return section_context_from_last_extracted_product_block_in_previous_chunk, last_extracted_product_block_in_previous_chunk, tokens_used[0], tokens_used[1]
    else:
        logging.info(f"No product entries found on this page")
        logging.info(f"Processed rows {start_row} to {end_row}")
        return None, None, tokens_used[0], tokens_used[1]

    # when extracting product entries directly
    # if content.get("product_entries"):
    #     last_product_entry = content["product_entries"][-1]
    #     context_from_previous_chunk= last_product_entry.get("context", "")
    #     if not last_product_entry:
    #         logging.info(f"Processed rows {start_row} to {end_row}")
    #         return None, None, tokens_used[0], tokens_used[1]
    #     elif last_product_entry:
    #         if not is_last_chunk:
    #             final_output_dropped_last_product_entry = content["product_entries"][:-1]
    #             final_output_dropped_last_product_entry = {
    #                 "sheet_name": sheet_name,
    #                 "boq_context": boq_context_md,
    #                 "product_entries": final_output_dropped_last_product_entry,
    #                 "original_rows_info": original_rows_info,
    #                 "token_usage": {
    #                     "prompt_tokens": tokens_used[0],
    #                     "completion_tokens": tokens_used[1]
    #                 }
    #                 }
    #             save_output_json(output_path_dropped_last_product_entry, final_output_dropped_last_product_entry)
    #         else:        
    #             save_output_json(output_path_dropped_last_product_entry, final_output)
    #         logging.info(f"Processed rows {start_row} to {end_row}")
    #         return context_from_previous_chunk, last_product_entry, tokens_used[0], tokens_used[1]    
    # else:
    #     logger.warning("No product entires found on this page")
    #     logging.info(f"Processed rows {start_row} to {end_row}")
    #     return None, None, tokens_used[0], tokens_used[1]


def process_all_chunks(
    schedule_path: str,
    output_folder: str,
    sheet_name: str,
    boq_context_md: str,
    boq_header_md: str,
    chunk_size: int = 20
) -> Tuple[List[Tuple[int, int]], int, int]:

    df_schedule = pd.read_excel(schedule_path)
    chunk_ranges = generate_and_save_chunk_ranges(schedule_path, output_folder, chunk_size)
    chunk_output_folder = os.path.join(output_folder, "chunking", "chunk_outputs")
    boundaries_folder = os.path.join(output_folder, "boundaries")

    total_prompt_tokens = 0
    total_completion_tokens = 0
    # last_product_entry = "dummy_string"
    # context_from_previous_chunk = "dummy_string"
    section_context_from_last_extracted_product_block_in_previous_chunk = "dummy_string"
    last_extracted_product_block_in_previous_chunk = "dummy_string"
    

    for idx, (start_idx, _) in enumerate(chunk_ranges):
        if start_idx==20 or start_idx==40:
            print(f"start_idx: {start_idx}")
            # print(f"last_product_entry: {last_product_entry}")
            # print(f"context_from_previous_chunk: {context_from_previous_chunk}")
            print(f"section_context_from_last_extracted_product_block_in_previous_chunk: {section_context_from_last_extracted_product_block_in_previous_chunk}")
            print(f"last_extracted_product_block_in_previous_chunk: {last_extracted_product_block_in_previous_chunk}")

        if last_extracted_product_block_in_previous_chunk is not None:
            section_context_from_last_extracted_product_block_in_previous_chunk, last_extracted_product_block_in_previous_chunk, \
            prompt_tokens, completion_tokens = call_llm_for_one_chunk(
                df_schedule, start_idx, chunk_size, sheet_name,
                boundaries_folder, chunk_output_folder,
                boq_context_md, boq_header_md,
                section_context_from_last_extracted_product_block_in_previous_chunk,
                last_extracted_product_block_in_previous_chunk,
                is_first_chunk=(idx == 0),
                is_last_chunk=(idx==len(chunk_ranges)-1)
            )

        # if last_product_entry is not None:
        #     context_from_previous_chunk, last_product_entry, prompt_tokens, completion_tokens = call_llm_for_one_chunk(
        #                                                 df_schedule, start_idx, chunk_size, sheet_name,
        #                                                 boundaries_folder, chunk_output_folder,
        #                                                 boq_context_md, boq_header_md,
        #                                                 context_from_previous_chunk,
        #                                                 last_product_entry,
        #                                                 is_first_chunk=(idx == 0),
        #                                                 is_last_chunk=(idx==len(chunk_ranges)-1)
        #                                                 )
            
            total_prompt_tokens += prompt_tokens
            total_completion_tokens += completion_tokens
        else:
            # logger.info(f"Skipping further processing on this sheet {sheet_name}\n because either content.get('product_entries') or content['product_entries'][-1] is None")
            logger.info(f"Skipping further processing on this sheet {sheet_name}\n because last_extracted_product_block_in_previous_chunk is None")
    return chunk_ranges, total_prompt_tokens, total_completion_tokens


if __name__ == "__main__":
    import asyncio
    from utils.logging_utils.logging_config import setup_logging
    setup_logging()
    logging.getLogger("httpx").setLevel(logging.WARNING)

    output_folder = "/home/student2/Documents/GitHub/1st_AI_Project_Kothari/boq_extraction_2/pipeline_copy_2/outputs/R4_ELECTRICAL_OFFER__CITCO__2_/FIRE_PUMP_ROOM"
    schedule_path = os.path.join(output_folder, "schedule_only.xlsx")
    sheet_name = "FIRE PUMP ROOM"
    chunk_size = 20

    metadata_path = os.path.join(output_folder, "metadata.json")
    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    boq_context_md = metadata.get("context_md", "")
    boq_header_md = metadata.get("header_md", "")

    chunk_ranges, total_prompt_tokens, total_completion_tokens = process_all_chunks(
        schedule_path, output_folder, sheet_name,
        boq_context_md, boq_header_md, chunk_size
    )
    print(f"Total prompt tokens: {total_prompt_tokens}")
    print(f"Total completion tokens: {total_completion_tokens}")