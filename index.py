import asyncio
import logging

from services.boq_extractor_service import BOQ_EXTRACTOR_SERVICE
from services.product_search_service import PRODUCT_MATCHING_SERVICE
from utils.logging_utils.logging_config import setup_logging
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)


async def run_full_pipeline(file_path: str, custom_instructions: str = ""):
    logger.info("🚀 Starting full BOQ + Product Matching pipeline...")

    # Phase 1: BOQ Extraction
    logger.info("🔧 Step 1: Extracting structured BOQ entries...")
    (
        extracted_json,
        extracted_excel,
        extraction_cost,
        extraction_time,
        extraction_errors
    ) = await BOQ_EXTRACTOR_SERVICE(file_path, custom_instructions)

    logger.info(f"✅ Extraction done. JSON: {extracted_json}, Excel: {extracted_excel}")
    logger.info("================================================================")

    # Phase 2: Product Matching
    logger.info("🧠 Step 2: Matching product entries to product DB...")
    (
        matched_json,
        matched_excel,
        matching_cost,
        matching_time,
        matching_errors
    ) = await PRODUCT_MATCHING_SERVICE(file_path)

    logger.info(f"✅ Matching done. JSON: {matched_json}, Excel: {matched_excel}")
    logger.info("================================================================")

    # Final Summary
    total_cost = extraction_cost + matching_cost
    total_time = extraction_time + matching_time
    all_errors = extraction_errors + matching_errors

    logger.info("📊 Pipeline Summary:")
    logger.info(f"💰 Total Cost: ${total_cost:.4f}")
    logger.info(f"⏱️ Total Time: {total_time:.2f} seconds")
    if all_errors:
        logger.warning("⚠️ Errors occurred in the following sheets:")
        for err in all_errors:
            logger.warning(f"  • Sheet: {err.get('sheet') or err.get('sheet_name')}, Error: {err.get('error')}")

    return {
        "extracted_json": extracted_json,
        "matched_json": matched_json,
        "total_cost_usd": total_cost,
        "total_processing_time": total_time,
        "errors": all_errors,
    }


if __name__ == "__main__":
    # Choose file
    # file_path = "/home/student2/Documents/GitHub/1st_AI_Project_Kothari/boq_extraction_2/pipeline_copy_2/inputs/BOQ-BPIL-FG WAREHOUSE-GODOWN-COLORANT (1).xlsx"
    # file_path = "/home/student2/Documents/GitHub/1st_AI_Project_Kothari/boq_extraction_2/pipeline_copy_2/inputs/BOQ.xlsx"
    # file_path = "/home/student2/Documents/GitHub/1st_AI_Project_Kothari/boq_extraction_2/pipeline_copy_2/inputs/Miraj-BOQ Electrical & Instrumentation.xlsx"
    file_path = "inputs/Miraj-BOQ Electrical Works.xlsx"
    custom_instructions = ""

    # Setup logging
    setup_logging()
    logging.getLogger("httpx").setLevel(logging.WARNING)

    # Run it
    results = asyncio.run(run_full_pipeline(file_path, custom_instructions))

    print("\n🎯 Final Output Paths:")
    print(f"🗂️ Extracted JSON: {results['extracted_json']}")
    print(f"🔗 Matched JSON: {results['matched_json']}")
    print(f"💰 Total Cost: ${results['total_cost_usd']:.4f}")
    print(f"⏱️ Total Time: {results['total_processing_time']:.2f} seconds")

    if results["errors"]:
        print("⚠️ Sheets with errors:")
        for err in results["errors"]:
            print(f"  • Sheet: {err.get('sheet') or err.get('sheet_name')}, Error: {err.get('error')}")
