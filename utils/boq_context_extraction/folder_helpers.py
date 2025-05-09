import os
import logging

logger = logging.getLogger(__name__)

def create_output_folder(file_path: str, sheet_name: str) -> str:
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    safe_base = "".join(c if c.isalnum() or c in ("_", "-") else "_" for c in base_name)
    safe_sheet = "".join(c if c.isalnum() or c in ("_", "-") else "_" for c in sheet_name)
    output_folder = os.path.join("outputs", safe_base, safe_sheet)
    os.makedirs(output_folder, exist_ok=True)

    return output_folder

def create_intermediate_results_folders(output_folder: str) -> str:
    # Also create subfolders - although this is used for chunking, boundaries and final output, and not in boq_context_extraction
    chunking_folder = os.path.join(output_folder, "chunking", "chunk_outputs")
    boundaries_folder = os.path.join(output_folder, "boundaries")
    final_output_folder = os.path.join(output_folder, "final_output")

    os.makedirs(chunking_folder, exist_ok=True)
    os.makedirs(boundaries_folder, exist_ok=True)
    os.makedirs(final_output_folder, exist_ok=True)

    return chunking_folder, boundaries_folder, final_output_folder