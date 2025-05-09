import pandas as pd
import asyncio
from typing import List, Dict
import os
from utils.prepare_metadata.prepare_metadata_for_one_sheet import prepare_metadata_for_one_sheet
from utils.common_utils.dynamic_semaphore import get_dynamic_semaphore
# from utils.logging_utils.logging_config import sheet_name_var
import logging
logger = logging.getLogger(__name__)


async def prepare_all_metadata(file_path: str, custom_instructions: str = "") -> List[Dict]:
    # logger.info(f"========= Phase 1: Metadata creation for all sheets=========")
    # start_time = asyncio.get_event_loop().time()
    xls = pd.ExcelFile(file_path)
    dynamic_concurrency = get_dynamic_semaphore()
    sem = asyncio.Semaphore(dynamic_concurrency)

    async def prepare_with_limit(sheet_name):
        # sheet_name_var.set(sheet_name) #TODO:
        async with sem:
            try:
                return await asyncio.to_thread(
                    prepare_metadata_for_one_sheet, file_path, sheet_name, custom_instructions
                )
            except Exception as e:
                logger.warning(f"⚠️ Error preparing metadata for sheet '{sheet_name}': {e}")
                return (sheet_name, e)

    tasks = [prepare_with_limit(sheet_name) for sheet_name in xls.sheet_names]
    results = await asyncio.gather(*tasks)

    metadata_list = []
    failed_sheets = []

    for result in results:
        if isinstance(result, tuple) and isinstance(result[1], Exception):
            failed_sheets.append({"sheet_name": result[0], "error": str(result[1])})
        else:
            metadata_list.append(result)

    if failed_sheets:
        logger.warning(f"⚠️ {len(failed_sheets)} sheets failed during metadata preparation:")
        for failure in failed_sheets:
            logger.warning(f" - Sheet: {failure['sheet_name']}, Error: {failure['error']}")

    # elapsed_time = asyncio.get_event_loop().time() - start_time
    # logger.info(f"=========Phase 1 completed: Prepared metadata for {len(metadata_list)} sheets in {elapsed_time:.2f} seconds=========")

    return metadata_list



if __name__ == "__main__":
    from utils.logging_utils.logging_config import setup_logging
    setup_logging()
    logging.getLogger("httpx").setLevel(logging.WARNING)  #### suppress HTTP 200 logs

    
    file_path = os.path.join("inputs", "R4_ELECTRICAL OFFER  CITCO (2).xlsx")
    custom_instructions = ""

    metadata_list = asyncio.run(prepare_all_metadata(file_path, custom_instructions))

    for meta in metadata_list:
        print(f" - Sheet: {meta['sheet_name']}, Output Folder: {meta['output_folder']}")

