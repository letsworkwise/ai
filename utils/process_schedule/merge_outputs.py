import os
import json
import pandas as pd
from typing import List, Tuple, Dict

from utils.boq_context_extraction.excel_helpers import save_output_excel
from utils.common_utils.json_helpers import save_output_json

import logging
logger = logging.getLogger(__name__)

# def load_corrected_chunk(boundaries_folder: str, start: int, end: int) -> List[Dict]:
#     file_path = os.path.join(boundaries_folder, f"page_output_dropped_last_product_entry_{start}_{end}.json")
#     try:
#         with open(file_path, "r", encoding="utf-8") as f:
#             data = json.load(f)
#         return data.get("product_entries", [])
#     except FileNotFoundError:
#         logger.warning(f"Missing corrected chunk output: {file_path}")
#         return []
#     except json.JSONDecodeError:
#         logger.error(f"Corrupted JSON in corrected chunk: {file_path}")
#         return []
#     except Exception as e:
#         logger.error(f"Unexpected error loading corrected chunk: {file_path}, Error: {str(e)}")
#         return []

def load_chunk(chunking_output_folder: str, start: int, end: int) -> List[Dict]:
    file_path = os.path.join(chunking_output_folder, f"page_output_{start}_{end}.json")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("product_entries", [])
    except FileNotFoundError:
        logger.warning(f"Missing chunk output: {file_path}")
        return []
    except json.JSONDecodeError:
        logger.error(f"Corrupted JSON in chunk: {file_path}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error loading chunk: {file_path}, Error: {str(e)}")
        return []

def merge_final_outputs(
    output_folder: str,
    chunk_ranges: List[Tuple[int, int]],
    sheet_name: str,
    boq_context_md: str,
    boq_header_md: str
):
    # boundaries_folder = os.path.join(output_folder, "boundaries")
    chunking_folder = os.path.join(output_folder, "chunking", "chunk_outputs")
    final_output_folder = os.path.join(output_folder, "final_output")

    final_products = []

    # for start, end in chunk_ranges:
    #     chunk_products = load_corrected_chunk(boundaries_folder, start, end)
    #     final_products.extend(chunk_products)

    for start, end in chunk_ranges:
        # chunk_products = load_corrected_chunk(chunking_folder, start, end)
        chunk_products = load_chunk(chunking_folder, start, end)
        final_products.extend(chunk_products)

    # Save final merged outputs
    final_json_path = os.path.join(final_output_folder, "final_product_entries.json")
    final_excel_path = os.path.join(final_output_folder, "final_product_entries.xlsx")

    save_output_json(final_json_path, {
        "sheet_name": sheet_name,
        "boq_context": boq_context_md,
        "header_rows": boq_header_md,
        "products_entries": final_products
    })

    save_output_excel(final_excel_path, final_products)

    logger.info(f"✅ Merged final output saved at {final_json_path} and {final_excel_path}")




if __name__ == "__main__":
    import os
    import json
    from utils.logging_utils.logging_config import setup_logging

    setup_logging()
    logging.getLogger("httpx").setLevel(logging.WARNING)  # suppress HTTP 200 logs

    # Change this path to your sheet's output folder
    output_folder = "/home/student2/Documents/GitHub/1st_AI_Project_Kothari/boq_extraction_2/pipeline copy/outputs/R4_ELECTRICAL_OFFER__CITCO__2_/FIRE_PUMP_ROOM"

    # Paths
    chunk_ranges_path = os.path.join(output_folder, "chunking", "chunk_ranges.json")
    metadata_path = os.path.join(output_folder, "metadata.json")

    # Load required files
    with open(chunk_ranges_path, "r", encoding="utf-8") as f:
        chunk_ranges = json.load(f)

    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    # Merge and save
    merge_final_outputs(
        output_folder=output_folder,
        chunk_ranges=chunk_ranges,
        sheet_name=metadata["sheet_name"],
        boq_context_md=metadata["context_md"],
        boq_header_md=metadata["header_md"]
    )
