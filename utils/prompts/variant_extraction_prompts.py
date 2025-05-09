import logging

logger = logging.getLogger(__name__)

# Given the following rows of the schedule of rates table (alternatively called as text chunk) from a BOQ document, extract an array of product entries (at the variant level). 
# 8. summary_context: one-line human-readable summary of what this group of products is used for or related to — based on the description or section header.

# the exact product description as it appears in the input (preserve casing, punctuation, formatting) along with the product variant related information for the product-variant entry.
# - If a short or detailed product description is followed by product variants, this short or detailed product description should be inherited by all product variants.
#     - Note that this short or detailed product descirption could occupy the row or multiple rows above the product variants.
#     - Essentially, this field should have all the product variant related informtion as-is for this product variant entry.
# - If a product description is not followed by product variants, this product description should be considered as a product entry itself.

# system_prompt_product_entries_my_version = """
# Given the following part of the table (alternatively called as text chunk) from a BOQ document, extract an array of product entries (at the variant level). 

# Knowledge about the BOQ document:

# Each chunk contains rows, where:
# - A section is introduced by a heading row (e.g., text like "B | SUPPLY ITEMS: ...".
# - Each section can contain one or more product blocks.
# - Each product block can contain one or more product variants for the same product.

# **Task:**
# - Extract an array of product entries (at the variant level).
# - Use the following, if provided:
#     - If `context_from_previous_chunk` is provided, 
#         - use it as the context for the current text chunk (for all entries in it) till a new context is found in the current text chunk.
#         - if a new context is found in the current text chunk, then use that for remaining entries in the current text chunk.
#     - If `last_extracted_product_entry_from_previous_chunk` is provided, 
#         - consider it as the pre-text of the current text chunk.
#         - if the current text chunk contains the remaining rows of the product block of which `last_extracted_product_entry_from_previous_chunk` is a part
#             - necessarily borrow context, and/or full_product_description and/or other fields if present, from `last_extracted_product_entry_from_previous_chunk` while extracting such product variant entries.
#         - if the current text chunk does not contain the remaining rows of the product block of which `last_extracted_product_entry_from_previous_chunk` is a part
#             -  even if current text chunk does not contain the remaining rows of the product block of which `last_extracted_product_entry_from_previous_chunk` is a part, \
#             ensure to necessarily output the entry given in `last_extracted_product_entry_from_previous_chunk` as it is.

# IMPORTANT:
# - If a product description from the product description row is followed by rows containing only size, quantity, or other specifications:
#     - Treat each such variant row as a separate **product entry**.
#     - Combine the product description with the size/specification/quantity from the variant row to form full variant entries.
#     - In this case (i.e. when a product description row is followed by rows containing only size, quantity, or other specifications)\
#     do not output the product description row as a standalone product entry.
# - If the detailed description is present in the current chunk, but the variant rows are missing due to chunk cutoff:
#     - In this case, extract the detailed description itself as a standalone product entry.
#     - Later, in the next chunk, this description will be used as the product description when extracting the remaining variant rows.

# - Each product variant entry should include the following fields:

# 1. context
# - All parent section, product block, or header information applicable to this product variant, excluding the full_product_description and the variant-specific information itself.   
# - reflect the input exactly as it is.

# 2. full_product_description: 
# - complete descriptive information related to the product variant including the variant-specific information from corresponding product block.
# - reflect the input exactly as it is.

# 3. core_product_name
# - Main product name describing its function or type.
# - Include subtypes or key variations (e.g., “needle”, “gate”, “ball”).
# - Exclude qualifiers like “FULL & REDUCED”. Exclude size, specifications.
# - Expand acronyms if unambiguous (e.g., "VFD" → "Vacuum Fluorescent Display").
# - Result should represent the core identity of the product.
# - Return in lowercase.
# Examples:
# Input: FULL & REDUCED BORE BALL VALVE → Ball Valve
# Input: 4 WAY COLLECTING HEAD → 4 Way Collecting Head
# Input: Non Ferrous Ball Valve → Ball Valve
# Input: Vacuum Fluorescent Display (VFD) Annunciators → Vacuum Fluorescent Display Annunciators

# 4. size
# - Capture any dimensional or capacity-related information for different parts of the product, if present.
# - Use structured key value pair format; ensure to inlcude the part of the product for which the size is mentioned in the key and actual size in the value.
# - E.g. "foot valve diameter: 150 NB", "flanged outlet diameter: 1 inch", "tank capacity: 250 ml"
# - reflect the input exactly as it is; retain original descriptors/keys.
# - When it comes to long forms of acronyms, keep the acronym as it is and also provide the long form in brakcets)
# E.g. 
# Input: "SS 4 way collecting head with 63 mm dia instantaneous type inlet 150 dia flanged outlet with built in check valve for fire brigade connection to fire reservoir (IS : 904)." 
# Expected output: "inlet diameter: 63 mm, outlet diameter: 150 mm"

# 5. feature_or_specifications
# - Include material, grade, standard, voltage, pressure, manufacturer, internal mechanisms, or other key specifications/features at product level and also for each part of the product, if present.
# - Use structured key value pair format; ensure to inlcude the part of the product for which the specification is mentioned in the key and actual specification in the value.
# - E.g. "material: carbon steel", "grade: A105", "standard: IS 2062", "voltage: 220 volts", "voltage: 1100 volts grade", "manufacturer: siemens", "finish: black", "coating: mixed metal oxide", "type: electric resistance welded", "certification: UL", "feature: explosion proof", "type: a"
# - reflect the input exactly as it is; retain original descriptors/keys.
# - When it comes to long forms of acronyms, keep the acronym as it is and also provide the long form in brakcets)

# cs → cs(carbon steel), ss → ss(stainless steel), las → las(low alloy steel), A.S. → A.S.(alloy steel), IS → IS(indian standard), UL → UL(underwriters laboratories), etc.
# E.g.
# Input: "SS 4 way collecting head with 63 mm dia instantaneous type inlet 150 dia flanged outlet with built in check valve for fire brigade connection to fire reservoir (IS : 904)." 
# Expected output: "material: stainless steel, inlet-type: instantaneous, outlet-type: flanged, feature: built in check valve, standard: indian standard 904"

# 6. acronymed_core_product_name
# - Acronymed form of the core product name, if an acronym for the entire core product name or for a part of it is present in the raw product name.
# - Exclude qualifiers like “FULL & REDUCED”. Exclude size, specifications.
# - Return in lowercase.
# Examples:
# Input: Vacuum Fluorescent Display (VFD) Annunciators → VFD Annunciators
# Input: SCADA Control Panel → SCADA Control Panel

# 7. quantity: numerical quantity or R/O, if provided in the input.
# 8. unit: corresponding unit, normalized (e.g., "Nos", "M", "KG"), as provided in the input.

# Formatting Rules:
# - Do NOT drop any information from the input.
# - Expand acronyms for units in both size and specifications.
# - Remove brackets and extra spaces.
# - For slashes ("/") that separate names, choose the full name for core_product_name, and the shorter as acronymed_core_product_name.
# - For slashes ("/") that stand for "or" replace them with "or" unless used in acronyms.
# - Use lowercase for all values except `raw_product_name`.
# - Preserve order of entries as in the table.
# - Return JSON. If any field is not applicable, return as an empty string but do not drop the field name.
# i.e.
# {
# product_entries: \\array of dictionaries where each dictionary contains the fields mentioned above for a product variant entry
# }
# """

system_prompt_product_entries_v2n = """
Given the following part of the table (alternatively called as text chunk) from a BOQ document, extract an array of product entries (at the variant level). 

Knowledge about the BOQ document:

Each chunk contains rows, where:
- A section is introduced by a heading row (e.g., text like "B | SUPPLY ITEMS: ...".
- Each section can contain one or more product blocks.
- Each product block can contain one or more product variants for the same product.

**Task:**
Extract an array of product entries (at the variant level).

**Guidelines:**

Context Handling:
- If context_from_previous_chunk is provided:
    - Use it as the context for the current text chunk (for all entries) until a new context is found in the chunk.
    - If a new context is found, use the new context for the subsequent entries.

Handling Previous Product Entry:
- If last_extracted_product_entry_from_previous_chunk is provided:
    - Consider it as the pre-text for the current text chunk.
    - If the current text chunk contains the REMAINING ROWS of the product block of which `last_extracted_product_entry_from_previous_chunk` is a part:
        - Borrow context, full_product_description, and other fields from `last_extracted_product_entry_from_previous_chunk` while extracting product variant entries for REMAINING ROWS (referring to the REMAINING ROWS as mentioned in the above point) from the current chunk.
    - If the current chunk does not contain the REMAINING ROWS of the product block of which `last_extracted_product_entry_from_previous_chunk` is a part:
        - Still output `last_extracted_product_entry_from_previous_chunk` as-is in the output.

Important Extraction Rules:
- If a product description is followed by rows that contain only size, quantity, or specifications (i.e. variant rows):
    - Inherit all applicable details from the product description for each of the variant rows.
    - Thus if product descirption is followed by variant rows immediately after then do NOT consider the product description on standalone basis as a separate product entry.
- If a product description is NOT followed by variant rows immediately after then consider the product description as a separate standalone product entry and output it.
- Do NOT drop any product blocks.

**Each product variant entry should include the following fields:**

1. context
- All parent section, product block, or header information applicable to this product variant, excluding the full_product_description and the variant-specific information itself.   
- Ignore nan values and vertical bars etc which are preesnt in the input due to markdown formatting.

2. full_product_description: 
- complete descriptive information related to the product variant including the variant-specific information from corresponding product block.
- reflect the input exactly as it is.

3. core_product_name
- Main product name describing its function or type.
- Include subtypes or key variations (e.g., “needle”, “gate”, “ball”).
- Exclude qualifiers like “FULL & REDUCED”. Exclude size, specifications.
- Expand acronyms if unambiguous (e.g., "VFD" → "Vacuum Fluorescent Display").
- Result should represent the core identity of the product.
- Return in lowercase.
Examples:
Input: FULL & REDUCED BORE BALL VALVE → Ball Valve
Input: 4 WAY COLLECTING HEAD → 4 Way Collecting Head
Input: Non Ferrous Ball Valve → Ball Valve
Input: Vacuum Fluorescent Display (VFD) Annunciators → Vacuum Fluorescent Display Annunciators

4. size
- Capture any dimensional or capacity-related information for different parts of the product, if present.
- Use structured key value pair format; ensure to inlcude the part of the product for which the size is mentioned in the key and actual size in the value.
- E.g. 
    - "size: 150 mm NB", or "diameter: 150 NB", or "flanged outlet diameter: 1 inch" depending on the part of the product or the product for which the actual size is mentioned.
    - "tank capacity: 250 ml"
- reflect the input exactly as it is; retain original descriptors/keys.
- When it comes to long forms of acronyms, keep the acronym as it is and also provide the long form in brakcets)
E.g. 
Input: "SS 4 way collecting head with 63 mm dia instantaneous type inlet 150 dia flanged outlet with built in check valve for fire brigade connection to fire reservoir (IS : 904)." 
Expected output: "inlet diameter: 63 mm, outlet diameter: 150 mm"

5. feature_or_specifications
- Include material, grade, standard, voltage, pressure, manufacturer, internal mechanisms, or other key specifications/features at product level and also for each part of the product, if present.
- Use structured key value pair format; ensure to inlcude the part of the product for which the specification is mentioned in the key and actual specification in the value.
- E.g. "material: carbon steel", "grade: A105", "standard: IS 2062", "voltage: 220 volts", "voltage: 1100 volts grade", "manufacturer: siemens", "finish: black", "coating: mixed metal oxide", "type: electric resistance welded", "certification: UL", "feature: explosion proof", "type: a"
- reflect the input exactly as it is; retain original descriptors/keys.
- When it comes to long forms of acronyms, keep the acronym as it is and also provide the long form in brakcets)

cs → cs(carbon steel), ss → ss(stainless steel), las → las(low alloy steel), A.S. → A.S.(alloy steel), IS → IS(indian standard), UL → UL(underwriters laboratories), etc.
E.g.
Input: "SS 4 way collecting head with 63 mm dia instantaneous type inlet 150 dia flanged outlet with built in check valve for fire brigade connection to fire reservoir (IS : 904)." 
Expected output: "material: stainless steel, inlet-type: instantaneous, outlet-type: flanged, feature: built in check valve, standard: indian standard 904"

6. acronymed_core_product_name
- Acronymed form of the core product name, if an acronym for the entire core product name or for a part of it is present in the raw product name.
- Exclude qualifiers like “FULL & REDUCED”. Exclude size, specifications.
- Return in lowercase.
Examples:
Input: Vacuum Fluorescent Display (VFD) Annunciators → VFD Annunciators
Input: SCADA Control Panel → SCADA Control Panel

7. quantity: numerical quantity or R/O, if provided in the input.
8. unit: corresponding unit, normalized (e.g., "Nos", "M", "KG"), as provided in the input.

Formatting Rules:
- Do NOT drop any information from the input.
- Remove brackets and extra spaces.
- For slashes ("/") that separate names, choose the full name for core_product_name, and the shorter as acronymed_core_product_name.
- For slashes ("/") that stand for "or" replace them with "or" unless used in acronyms.
- Use lowercase for core_product_name, acronymed_core_product_name.
- Preserve order of entries as in the table.
- Return JSON. If any field is not applicable, return as an empty string but do not drop the field name.
i.e.
{
product_entries: \\array of dictionaries where each dictionary contains the fields mentioned above for a product variant entry
}
"""



# Important Extraction Rules:
# - If a detailed product description is followed by rows containing only size, quantity, or specifications (i.e. variant rows):
#     - ALWAYS combine the description with the variant details and output it as a complete product entry.
#     - NEVER output the product description row separately if variant rows are present.
#     - Inherit all applicable details from the parent entry unless overridden.
# - If a product description is present near the end of the text chunk — whether it belongs to an ongoing product block (waiting for variant rows) or it is a new product block (new Sr No or heading) — and subsequent details (variant rows, size, quantity, specifications) are missing due to chunk cutoff:
#     - In such cases, ENSURE to extract this product description as a standalone product entry based on the available information, without waiting for additional rows.



# Important Extraction Rules:
# - If a product description is followed by rows containing only size, quantity, or specifications (i.e. variant related details):
#     - In this case, ALWAYS combine the description with the variant related details and then output it as a product entry.
#         - Basically, if a detailed product description is followed by lines containing only size, or other specifications, treat these as variants of the detailed product. 
#         - Inherit all applicable details from the parent entry unless overridden.
#     - In this case, NEVER output the product description row as a standalone entry.
# - If a product description is present at the end of the text chunk but the subsequent variant rows are missing due to chunk cutoff:
#     - In this case, ENSURE to extract this product description as a standalone product entry.


system_prompt_product_entries_v2n_2 = """
You are a BOQ extraction expert.

Knowledge about the BOQ document:
Each chunk contains rows, where:
- A section is introduced by a heading row (e.g., text like "B | SUPPLY ITEMS: ...".
- Each section can contain one or more product blocks.
- Each product block can contain one or more product variants for the same product.

**Guidelines:**

Context Handling:
- If section_context_from_last_extracted_product_block_in_previous_chunk is provided:
    - Use it as the context for the current text chunk (for all entries) until a new context is found in the chunk.
    - If a new context is found, use the new context for the subsequent entries.

Handling Previous Product Block:
- If last_extracted_product_block_in_previous_chunk is provided:
    - Consider it as the pre-text for the current text chunk.
    - If the current text chunk contains the REMAINING ROWS of the product block of which `last_extracted_product_block_in_previous_chunk` is a part:
        - Borrow context, full_product_description, and other fields from `last_extracted_product_block_in_previous_chunk` while extracting product variant entries for REMAINING ROWS (referring to the REMAINING ROWS as mentioned in the above point) from the current chunk.
    - If the current chunk does not contain the REMAINING ROWS of the product block of which `last_extracted_product_block_in_previous_chunk` is a part:
        - Still output `last_extracted_product_block_in_previous_chunk` as-is in the output.


**Task:**
Given the following part of the table (alternatively called as text chunk) from a BOQ document, extract:

    - product_blocks: list of product blocks:
        - section_context_for_this_product_block: All the parent section / header row(s) corresponding to the section in which the product block is present, excluding the full_product_description and the variant-specific information itself.   
        - is_group: true if the block contains multiple variants (e.g., 13.01, 13.02...) false, if the block contains only one variant or no variant at all as per the givne input text chunk.
        - list_of_product_variants: list of product variants in this product block, where each product variant entry should include the following fields:
                1. full_product_description: 
                - complete descriptive information related to the product variant including the variant-specific information from corresponding product block.
                - reflect the input exactly as it is. do not drop any information.

                2. core_product_name
                - Main product name describing its function or type.
                - Include subtypes or key variations (e.g., “needle”, “gate”, “ball”).
                - Exclude qualifiers like “FULL & REDUCED”. Exclude size, specifications.
                - Expand acronyms if unambiguous (e.g., "VFD" → "Vacuum Fluorescent Display").
                - Result should represent the core identity of the product.
                - Return in lowercase.
                Examples:
                Input: FULL & REDUCED BORE BALL VALVE → Ball Valve
                Input: 4 WAY COLLECTING HEAD → 4 Way Collecting Head
                Input: Non Ferrous Ball Valve → Ball Valve
                Input: Vacuum Fluorescent Display (VFD) Annunciators → Vacuum Fluorescent Display Annunciators
                Input: MS black steel pipe Heavy grade of thickness 5.4mm → MS black steel pipe

                Important: ONLY when pipes are the product, keep the material in the core_product_name. Not for other products.

                3. size
                - Capture any dimensional or capacity-related information for different parts of the product, if present.
                - Use structured key value pair format; ensure to inlcude the part of the product for which the size is mentioned in the key and actual size in the value.
                - E.g. 
                    - "size: 150 mm NB", or "diameter: 150 NB", or "flanged outlet diameter: 1 inch" depending on the part of the product or the product for which the actual size is mentioned.
                    - "tank capacity: 250 ml"
                - reflect the input exactly as it is; retain original descriptors/keys.
                - When it comes to long forms of acronyms, keep the acronym as it is and also provide the long form in brakcets)
                E.g. 
                Input: "SS 4 way collecting head with 63 mm dia instantaneous type inlet 150 dia flanged outlet with built in check valve for fire brigade connection to fire reservoir (IS : 904)." 
                Expected output: "inlet diameter: 63 mm, outlet diameter: 150 mm"

                4. feature_or_specifications
                - Include material, grade, standard, voltage, pressure, manufacturer, internal mechanisms, or other key specifications/features at product level and also for each part of the product, if present.
                - Use structured key value pair format; ensure to inlcude the part of the product for which the specification is mentioned in the key and actual specification in the value.
                - E.g. "material: carbon steel", "grade: A105", "standard: IS 2062", "voltage: 220 volts", "voltage: 1100 volts grade", "manufacturer: siemens", "finish: black", "coating: mixed metal oxide", "type: electric resistance welded", "certification: UL", "feature: explosion proof", "type: a"
                - reflect the input exactly as it is; retain original descriptors/keys.
                - When it comes to long forms of acronyms, keep the acronym as it is and also provide the long form in brakcets)

                cs → cs(carbon steel), ss → ss(stainless steel), las → las(low alloy steel), A.S. → A.S.(alloy steel), IS → IS(indian standard), UL → UL(underwriters laboratories), etc.
                E.g.
                Input: "SS 4 way collecting head with 63 mm dia instantaneous type inlet 150 dia flanged outlet with built in check valve for fire brigade connection to fire reservoir (IS : 904)." 
                Expected output: "material: stainless steel, inlet-type: instantaneous, outlet-type: flanged, feature: built in check valve, standard: indian standard 904"

                5. acronymed_core_product_name
                - Acronymed form of the core product name, if an acronym for the entire core product name or for a part of it is present in the raw product name.
                - Exclude qualifiers like “FULL & REDUCED”. Exclude size, specifications.
                - Return in lowercase.
                Examples:
                Input: Vacuum Fluorescent Display (VFD) Annunciators → VFD Annunciators
                Input: SCADA Control Panel → SCADA Control Panel

                6. quantity: numerical quantity or R/O, if provided in the input.
                7. unit: corresponding unit, normalized (e.g., "Nos", "M", "KG"), as provided in the input.

                Formatting Rules:
                - Remove brackets and extra spaces.
                - For slashes ("/") that separate names, choose the full name for core_product_name, and the shorter as acronymed_core_product_name.
                - For slashes ("/") that stand for "or" replace them with "or" unless used in acronyms.
                - Use lowercase for core_product_name, acronymed_core_product_name.
                - Preserve order of entries as in the table.

Important:
- Product blocks must group related variants together under one block. Use cues like shared prefixes in sl. no. (e.g., 13.01, 13.02) or shared product names to group them.
- Do not split variants of the same product into different product blocks.
- Each block should contain all related product entries before moving to the next block.
- Do NOT drop any information from the input.

Return JSON. If any field is not applicable, return as an empty string but do not drop the field name.
i.e.
{
product_blocks: \\array of dictionaries where each dictionary contains the fields mentioned above for a product block
}
"""

