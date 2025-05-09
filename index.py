from typing import Tuple
import asyncio
import logging

logger = logging.getLogger(__name__)


async def BOQ_EXTRACTOR_SERVICE(file_path: str, custom_instructions: str = "") -> Tuple[str, str, float, float, list]:
    from utils.prepare_metadata.prepare_metadata_for_all_sheets import prepare_all_metadata
    from utils.process_schedule.process_all_schedules import run_all_sheets
    from utils.combine_output.combine_outputs_across_sheets import combine_boq_outputs_across_sheets
    from utils.common_utils.token_utils import log_cost_and_processing_time

    # Phase 1: Prepare all metadata
    metadata_list = await prepare_all_metadata(file_path, custom_instructions)

    # Phase 2: Process all schedules
    prompt_tokens, completion_tokens, elapsed_time, sheet_errors = await run_all_sheets(file_path)

    # Phase 3: Log cost and time
    aggregate_cost_usd, total_processing_time = log_cost_and_processing_time(file_path, prompt_tokens, completion_tokens, elapsed_time)

    # Phase 4: Combine output files
    combined_json_path, combined_excel_path = combine_boq_outputs_across_sheets(file_path)

    return combined_json_path, combined_excel_path, aggregate_cost_usd, total_processing_time, sheet_errors


if __name__ == "__main__":
    file_path = "/home/student2/Documents/GitHub/1st_AI_Project_Kothari/boq_extraction_2/pipeline_copy_2/inputs/R4_ELECTRICAL OFFER  CITCO (2).xlsx"
    custom_instructions = ""  # optional

    from utils.logging_utils.logging_config import setup_logging
    setup_logging()
    logging.getLogger("httpx").setLevel(logging.WARNING)  # Suppress HTTP 200 logs

    combined_json_path, combined_excel_path, aggregate_cost_usd, total_processing_time, sheet_errors = asyncio.run(
        BOQ_EXTRACTOR_SERVICE(file_path, custom_instructions)
    )

    print("\n✅ Final Combined Output Paths:")
    print(f"📄 JSON: {combined_json_path}")
    print(f"📄 Excel: {combined_excel_path}")
    print(f"💵 Total Cost: ${aggregate_cost_usd:.5f}")
    print(f"⏱️ Total Processing Time: {total_processing_time:.2f} seconds")

    if sheet_errors:
        print(f"⚠️ Sheets with errors:")
        for err in sheet_errors:
            print(f"  • Sheet: {err['sheet']}, Error: {err['error']}")