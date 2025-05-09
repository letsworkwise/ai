import os
import json
import pandas as pd
from typing import Tuple
import logging

logger = logging.getLogger(__name__)

def combine_boq_outputs_across_sheets(file_path: str) -> Tuple[str, str]:
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    safe_base = "".join(c if c.isalnum() or c in ("_", "-") else "_" for c in base_name)
    combined_json = []
    combined_excel = pd.DataFrame()

    sheet_order = pd.ExcelFile(file_path).sheet_names

    for sheet_name in sheet_order:
        sheet_name_safe = "".join(c if c.isalnum() or c in ("_", "-") else "_" for c in sheet_name)
        sheet_folder = os.path.join("outputs", safe_base, sheet_name_safe)
        if not os.path.isdir(sheet_folder):
            logger.warning(f"Sheet folder not found: {sheet_folder}")
            continue

        json_path = os.path.join(sheet_folder, "final_output", "final_product_entries.json")
        excel_path = os.path.join(sheet_folder, "final_output", "final_product_entries.xlsx")
        logger.info(f"Combining {json_path} and {excel_path}")
        logger.info(f"sheet_name: {sheet_name_safe}")

        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data.get("products_entries", []):
                        item["sheet_name"] = sheet_name
                        combined_json.append(item)
            except FileNotFoundError:
                logger.warning(f"File not found: {json_path}")
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to load JSON from {json_path}: {e}")
            except Exception as e:
                logger.warning(f"Error processing JSON from {json_path}: {e}")

        if os.path.exists(excel_path):
            try:
                df = pd.read_excel(excel_path)
                df["sheet_name"] = sheet_name
                combined_excel = pd.concat([combined_excel, df], ignore_index=True)
            except Exception as e:
                logger.warning(f"Failed to load Excel from {excel_path}: {e}")

    output_dir = os.path.join("outputs", safe_base)
    os.makedirs(output_dir, exist_ok=True)

    combined_json_path = os.path.join(output_dir, "product_entries_combined_across_sheets.json")
    combined_excel_path = os.path.join(output_dir, "product_entries_combined_across_sheets.xlsx")

    with open(combined_json_path, "w", encoding="utf-8") as f:
        json.dump(combined_json, f, indent=2, ensure_ascii=False)

    combined_excel.to_excel(combined_excel_path, index=False)

    logger.info(f"✅ Combined outputs saved in '{output_dir}':")
    logger.info(f"  - {os.path.basename(combined_json_path)}")
    logger.info(f"  - {os.path.basename(combined_excel_path)}")

    return combined_json_path, combined_excel_path
