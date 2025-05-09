import json
import logging

logger = logging.getLogger(__name__)

# system_prompt_merge_product_entries_v1 = """
# You are given a set of product entries that may belong to the same product block but are split across two consecutive chunks of a BOQ table.

# Your task is to:
# - Consolidate these into a new set of product entries, based on context and structure. Particularly,
#     - Merge variants appropriately.
#     - Remove duplicates or redundant description-only entries.
#     - Ensure each output entry is a valid variant entry.

# Return the corrected array of product entries in the same json format as before (field names unchanged).
# """

# v2

system_prompt_merge_product_entries = """
You are given a Last entry from first chunk and all the *incomplete* product entries from the second chunk of a BOQ table.

Incomplete as in, their `raw_product_description` does not adhere to the following:
- it does not contain complete information related to the product variant from corresponding product block.
- it does not include any description/header information for the product block in which the variant is present.
Thus the field `raw_product_description` is to be completed by combining the appropriate information from the last entry from first chunk for each of the incomplete entries from the second chunk.

Do not alter field names.
Do not drop fields but is_only_product_specs_row should be dropped.
Output must be in the JSON format:
{
  "products": [ array of merged product entries ]
}
"""

def make_user_prompt_for_merge(last_entry: dict, spec_only_entries: list[dict]):
    return f"""
Last entry from first chunk:
{json.dumps({"products": [last_entry]}, indent=2, ensure_ascii=False)}

Entries from second chunk (only the incomplete ones):
{json.dumps({"products": spec_only_entries}, indent=2, ensure_ascii=False)}
"""
# ones with `is_only_product_specs_row = "Y"`