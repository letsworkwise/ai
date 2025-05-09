from typing import Tuple
import logging
import asyncio

logger = logging.getLogger(__name__)

async def PRODUCT_MATCHING_SERVICE(file_path: str) -> Tuple[str, str, float, float, list]:
    from utils.product_search.match_entries_for_all_sheets import match_entries_for_all_sheets
    from utils.combine_output.combine_outputs_across_sheets import combine_outputs_across_sheets
    from utils.common_utils.token_utils import log_cost_and_processing_time

    # Phase 1: Run product matching for all sheets
    matching_summary = await match_entries_for_all_sheets(file_path)
    prompt_tokens = matching_summary["total_prompt_tokens"]
    completion_tokens = matching_summary["total_completion_tokens"]
    total_time = matching_summary["total_time"]
    sheet_errors = matching_summary.get("errors", []) #TODO: need to aggregate errors across sheets and across products

    # Phase 2: Log cost and time
    aggregate_cost_usd, total_processing_time = log_cost_and_processing_time(
        file_path, prompt_tokens, completion_tokens, elapsed_time=total_time
    )

    # Phase 3: Combine product match outputs
    combined_json_path, combined_excel_path = combine_outputs_across_sheets(
        file_path, match_filename="final_product_entries_with_matches.json"
    )

    return combined_json_path, combined_excel_path, aggregate_cost_usd, total_processing_time, sheet_errors



if __name__ == "__main__":
    import os
    from utils.logging_utils.logging_config import setup_logging
    setup_logging()

    file_path = "/home/student2/Documents/GitHub/1st_AI_Project_Kothari/boq_extraction_2/pipeline_copy_2/inputs/BOQ-BPIL-FG WAREHOUSE-GODOWN-COLORANT (1).xlsx"
    summary = asyncio.run(PRODUCT_MATCHING_SERVICE(file_path))

    print("\n🎯 Product matching complete:")
    print(f"📄 JSON: {summary[0]}")
    print(f"📄 Excel: {summary[1]}")
    print(f"💰 Total Cost: ${summary[2]:.5f}")
    print(f"⏱️ Processing Time: {summary[3]:.2f} seconds")
    if summary[4]:
        print("⚠️ Sheet Errors:")
        for err in summary[4]:
            print(f"  - {err}")
