from utils.logging_utils.logging_config import setup_logging
from index import BOQ_EXTRACTOR_SERVICE
from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import FileResponse
import uvicorn
import shutil
import os
import asyncio
import logging
logging.getLogger("httpx").setLevel(logging.WARNING)  #### suppress HTTP 200 logs


app = FastAPI()

logger = logging.getLogger(__name__)

# Arbaz:
# If needed, auto-delete:
# temp file (temp_{file.filename})
# folder outputs/safe_base/ after sending file if you want to run clean


@app.post("/process-boq")
async def process_boq(
    request: Request,
    file: UploadFile = File(...),
    custom_instructions: str = Form("")  # optional user-supplied instructions,
    #Arbaz: TODO: these custom_instructions aren't per sheet though, so be careful
    # Arbaz: Do we need them anyway?
):
    temp_file_path = f"temp_{file.filename}"
    with open(temp_file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        combined_json_path, combined_excel_path, cost_usd, elapsed_time, sheet_errors = await BOQ_EXTRACTOR_SERVICE(temp_file_path, custom_instructions)
        base_folder = os.path.splitext(os.path.basename(temp_file_path))[0]
        safe_base = "".join(c if c.isalnum() or c in ("_", "-") else "_" for c in base_folder)
        base_url = str(request.base_url)

        return {
            "status": "partial_success" if sheet_errors else "success",
            "message": "Some sheets failed to process." if sheet_errors else "BOQ processing complete.",
            "download_json": f"{base_url}download/json?file_name={safe_base}",
            "download_excel": f"{base_url}download/excel?file_name={safe_base}",
            "cost_usd": cost_usd,
            "time_sec": round(elapsed_time, 2),
            "failed_sheets": sheet_errors
        }
    except Exception as e:
        logger.error(f"❌ Error during processing: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


@app.get("/download/json")
async def download_combined_json(file_name: str):
    path = os.path.join("outputs", file_name, "final_product_entries_across_sheets.json")
    if os.path.exists(path):
        return FileResponse(path, filename="final_product_entries_across_sheets.json", media_type="application/json")
    return {"error": "File not found"}

@app.get("/download/excel")
async def download_combined_json(file_name: str):
    path = os.path.join("outputs", file_name, "final_product_entries_across_sheets.xlsx")
    if os.path.exists(path):
        return FileResponse(path, filename="final_product_entries_across_sheets.xlsx")
    return {"error": "File not found"}


@app.get("/process-boq/dev")
async def process_boq_dev():
    file_path = os.path.join("inputs", "BOQ functionality testing BOQ-1.xlsx")
    try:
        combined_json_path, combined_excel_path, cost_usd, elapsed_time = await BOQ_EXTRACTOR_SERVICE(file_path)
        return {
            "status": "success",
            "json_path": combined_json_path,
            "excel_path": combined_excel_path,
            "cost_usd": cost_usd,
            "time_sec": round(elapsed_time, 2)
        }
    except Exception as e:
        logger.error(f"❌ Error in dev endpoint: {e}")
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    setup_logging()
    print("Starting FastAPI server...")
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
