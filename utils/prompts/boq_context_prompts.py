import json
import logging

logger = logging.getLogger(__name__)

system_prompt_boq_context = """
Below is a table from a BOQ Excel sheet in markdown format. Your task is to extract only:

1. The context rows — these appear **before** the schedule of rates starts. These rows provide project metadata, section titles, or annotations. type: string
2. The header row(s) — these are the row(s) (one or more) that define the column headers for the schedule of rates (e.g., columns like ITEM, UNIT, PH, etc.). type: string

⚠️ Important:
- Return the string of **only** those rows in the **exact as-is markdown format** of each row.
- Do not drop any informaiton or any cell from the input rows.

Return in JSON format with the following fields:
- context_rows: string
- header_rows: string

Ignore the custom instructions if provied.

### Markdown Table:
"""


custom_instructions_boq_context = "\n\nCustom Instructions:{custom_instructions}"
