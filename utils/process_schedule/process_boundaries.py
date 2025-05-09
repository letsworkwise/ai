import os
import json
import asyncio
from typing import List, Tuple
import logging

from utils.boq_context_extraction.folder_helpers import create_output_folder
from utils.process_schedule.process_boundaries_helpers import (
    load_two_chunks, merge_boundary_entries, save_corrected_chunks,
    prepare_boundary_merge_request, call_llm_for_boundary_merge
)

logger = logging.getLogger(__name__)


def _process_one_boundary_sync(
    i: int,
    chunk_output_folder: str,
    boundaries_folder: str,
    chunk_ranges: List[Tuple[int, int]]
) -> Tuple[int, int]:
    try:
        data1, data2, start1, end1, start2, end2 = load_two_chunks(chunk_output_folder, chunk_ranges, i)
        last_entry, spec_only_entries = prepare_boundary_merge_request(data1, data2)

        if not last_entry or not spec_only_entries:
            logger.warning(f"No boundary entries for chunks {start1}-{end1} and {start2}-{end2}")
            return 0, 0

        corrected_entries, tokens_used = call_llm_for_boundary_merge(last_entry, spec_only_entries)

        is_first_pair = (i == 0)
        is_last_pair = (i == len(chunk_ranges) - 2)
        updated_data1, updated_data2 = merge_boundary_entries(data1, data2, corrected_entries, is_first_pair, is_last_pair)

        save_corrected_chunks(boundaries_folder, start1, end1, start2, end2, updated_data1, updated_data2)

        return tokens_used

    except Exception as e:
        logger.error(f"Failed boundary merge at index {i}: {e}")
        return 0, 0


async def process_chunk_boundaries(output_folder: str, chunk_ranges: List[Tuple[int, int]]) -> Tuple[int, int]:
    chunk_output_folder = os.path.join(output_folder, "chunking", "chunk_outputs")
    boundaries_folder = os.path.join(output_folder, "boundaries")

    total_prompt_tokens, total_completion_tokens = 0, 0

    async def process_boundary(i: int):
        return await asyncio.to_thread(
            _process_one_boundary_sync,
            i, chunk_output_folder, boundaries_folder, chunk_ranges
        )

    tasks = [process_boundary(i) for i in range(len(chunk_ranges) - 1)]
    results = await asyncio.gather(*tasks)

    for prompt_tokens, completion_tokens in results:
        total_prompt_tokens += prompt_tokens
        total_completion_tokens += completion_tokens

    return total_prompt_tokens, total_completion_tokens


if __name__ == "__main__":
    import asyncio

    from utils.logging_utils.logging_config import setup_logging
    setup_logging()
    logging.getLogger("httpx").setLevel(logging.WARNING)  # Suppress HTTP 200 logs

    output_folder = "/home/student2/Documents/GitHub/1st_AI_Project_Kothari/boq_extraction_2/pipeline copy/outputs/R4_ELECTRICAL_OFFER__CITCO__2_/FIRE_PUMP_ROOM"

    chunk_ranges_path = os.path.join(output_folder, "chunking", "chunk_ranges.json")
    with open(chunk_ranges_path, "r", encoding="utf-8") as f:
        chunk_ranges = json.load(f)

    asyncio.run(process_chunk_boundaries(output_folder, chunk_ranges))
