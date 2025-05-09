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
                - Remove brackets and extra spaces and vertical bars.
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


# Handling Previous Product Block:
# - If last_extracted_product_block_in_previous_chunk is provided:
#     - Consider it as the pre-text for the current text chunk.
#     - If the current text chunk contains the REMAINING ROWS of the product block of which `last_extracted_product_block_in_previous_chunk` is a part:
#         - Borrow context, full_product_description, and other fields from `last_extracted_product_block_in_previous_chunk` while extracting product variant entries for REMAINING ROWS (referring to the REMAINING ROWS as mentioned in the above point) from the current chunk.
#     - If the current chunk does not contain the REMAINING ROWS of the product block of which `last_extracted_product_block_in_previous_chunk` is a part:
#         - Still output `last_extracted_product_block_in_previous_chunk` as-is in the output. 
#         - This is very important as otherwise the entries from the last_extracted_product_block_in_previous_chunk will be lost.

system_prompt_product_entries_v2n_2point5 = """
You are a BOQ extraction expert.

Knowledge about the BOQ document:
Each chunk contains rows, where:
- A section is introduced by a heading row (e.g., text like "B | SUPPLY ITEMS: ...".
- Each section can contain one or more product blocks.
- Each product block can contain one or more product variants for the same product.

**Guidelines:**
Header Handling:
- If the header rows are provided as Column 1, Column 2, etc. then infer the Unit/UOM and Quantity columns for the table. 
- Usually the Unit/UOM and Quantity columns are the last two columns in the table.

Context Handling:
- If section_context_from_last_extracted_product_block_in_previous_chunk is provided:
    - Use it as the context for the current text chunk (for all entries) until a new context is found in the chunk.
    - If a new context is found, use the new context for the subsequent entries.

Handling Previous Product Block:
- If `last_extracted_product_block_in_previous_chunk` is provided:
    - Always include it in your output product_blocks list.
    - If the current table continues it (i.e., contains remaining product variant rows), merge the variant entries and then output.
    - Otherwise, include it unchanged before processing new product blocks.


**Task:**
Given the following part of the table (alternatively called as text chunk) from a BOQ document, extract:

    - product_blocks: list of product blocks:
        - section_context_for_this_product_block: All the parent section / header row(s) corresponding to the section in which the product block is present, excluding the full_product_description and the variant-specific information itself.   
        - is_group: true if the block contains multiple variants (e.g., 13.01, 13.02...) false, if the block contains only one variant or no variant at all as per the givne input text chunk.
        - list_of_product_variants: list of product variants in this product block, where each product variant entry should include the following fields:
                1. full_product_description: 
                - complete descriptive information related to the product variant including the variant-specific information from corresponding product block.
                - inherit the product block level description with each variant-level description to form full product variant descriptions.
                - Ensure to also include the ITEM NO or Serial No or the likes for each variant if present in the input.
                - reflect the input exactly as it is. Do not drop any information.

                2. core_product_name
                - Main name describing product type or function.
                - Expand acronyms if unambiguous (e.g. VFD → Vacuum Fluorescent Display).
                - Exclude size, specifications, or qualifiers like “FULL & REDUCED”.
                - Return in lowercase.

                Important: ONLY when pipes are the product, keep the material in the core_product_name. Not for other products.

                3. acronymed_core_product_name
                - Acronymed form of the core product name, if an acronym for the entire core product name or for a part of it is present in the raw product name.
                - Exclude qualifiers like “FULL & REDUCED”. Exclude size, specifications.
                - Return in lowercase.
                Examples:
                Input: Vacuum Fluorescent Display (VFD) Annunciators → VFD Annunciators
                Input: SCADA Control Panel → SCADA Control Panel
                - 

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

                - If the product is a service and not really a proudct, then the feature_or_specifications should be empty and the core_product_name should be the service name.

                
                6. quantity: numerical quantity or R/O, if provided in the input.
                7. unit: corresponding unit, normalized (e.g., "Nos", "M", "KG"), as provided in the input.

                --------------------------------

                **Global Formatting Rules**:
                - Use lowercase for core_product_name, functional_descriptors, acronymed_core_product_name, but be true to original case (as provided in the input) for other fields.
                - **ALWAYS EXPAND ACRONYMS IF UNAMBIGUOUS FOR ALL THE FIELDS, KEEP THEM IN PARENTHESE AFTER THE ORIGINAL ACRONYM.**
                - Remove brackets, extra spaces, or vertical bars.
                - If slashes indicate "or", convert to "or", unless part of an acronym.
                - Preserve order of entries as in the table. 


**Important: Product Block Rules**
- Product blocks must group related variants together under one block. Use cues like shared prefixes in sl. no. (e.g., 13.01, 13.02) or shared product names to group them.
- Do not split variants of the same product into different product blocks.
- Each block should contain all related product entries before moving to the next block.
- Do NOT drop any information from the input.

**Important: Product + Variant Rules for Extraction**
- If a row has a detailed description but an empty Quantity, 99 percent of the times it is a product block level description.
- The following rows with filled Quantity and variant-level description are its variants.
    - IF THE QUANTITY IS NOT FOUND IN THE VARIANT ROW, then resort to SERIAL NO or ITEM NO or the likes TO CONCLUDE THAT IT IS A VARIANT ROW. 
    - Thus finally, do not skip such variant rows.
- Always INHERIT the product block level description with each variant-level description to form full product variant descriptions.
- Never output the product block level description alone if variants exist.
- Do not drop any information from the input.


**Finally, do not skip any variant rows from the input. Extract all the variant rows.**

Return JSON. If any field is not applicable, return as an empty string but do not drop the field name.
i.e.
{
product_blocks: \\array of dictionaries where each dictionary contains the fields mentioned above for a product block
}
"""
                # 3. functional_descriptors_for_product
                # - Include adjectives or terms modifying the function (e.g. "open", "manual", "portable") of the product.
# **Important: A note on Product Extraction**
# - When extracting product entries, we only want to keep the details of the product that is being sourced in the BOQ, and no thte details of the existing products or systems that are to be replaced using this sourced product.





system_prompt_product_entries_v2n_3 = """
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
                - reflect the input exactly as it is. Do not drop any information.

                2. core_product_name
                - Main name describing product type or function.
                - Expand acronyms if unambiguous (e.g. VFD → Vacuum Fluorescent Display).
                - Exclude size, specifications, or qualifiers like “FULL & REDUCED”.
                - Return in lowercase.

                3. acronymed_core_product_name
                - Acronymed version of product name if present (e.g. "VFD Annunciators").
                - Exclude qualifiers or specs.

                Note: The fields `core_product_name`, `functional_descriptors_for_product`, and `acronymed_core_product_name` are always singular, non-repeating, and not sub-part dependent. These should not be structured into a list or multi-level dictionary.

                4. list_of_specific_attributes
                - a list of dicttionaries containing part, attribute, value as the fields.
                    - 'part': the component or sub-part of the product (e.g., inlet, outlet, nozzle) 
                        - write "product" here if the attribute is meant for the product as a whole and not for a specific sub-part of the product.
                    - 'attribute': the type of property (e.g., diameter, coating, standard, connection type)
                    - 'value': the corresponding value (e.g., 150 mm, hot dip galvanized, IS 1239)
                - Where the attribute is one of the following:
                    - material: MS, SS, Al, PVC, Rubber, etc.
                    - size_or_capacity: NB, OD, Sqmm, Flow, Pressure, Voltage
                    - type_or_class: Pipe Class, Cable Type, Valve Class
                    - standards_and_approvals: IS, IEC, ASTM, API, UL/FM, CE
                    - construction_features: Armour, Sheathing, End Connections, Flanges
                    - protection_features: Fireproof, UV proof, Anti-corrosion, Explosion proof
                    - mounting_or_installation: Hanger, Clamps, Supports, Surface/Underground
                    - operating_conditions: Temperature, Pressure, Environment (Indoor/Outdoor)
                    - connection_details: Threaded, Flanged, Glands, Couplings
                    - accessories_or_attachments: Lugs, Elbows, Reducers, JBs, Fasteners
                    - testing_or_inspection: Hydro test, FAT, TPI, Fire Safety Compliance
                    - special_attributes: Shielded cable, Bending Radius, Drum Length (cables), Seamed/Seamless (pipes)
                - The above-mentioned set of values for each attribute is non-exhaustive and is just for illustration.

                Note: 
                - This structure is important to allow granular indexing and querying in downstream systems. Thus, use this structure consistently across all the attributes listed above. 
                - Do not vary the key names.                
                - Do **not** include fields that are not present — avoid empty fields to minimize output size.
                - Thus output a compact JSON object with only relevant keys.
                - **Very Important: Do not output the attribute field in flat format but stick to list of dictionaries with *part*, attribute, value as the fields.**
                - **Important**: A product detail may be valid for more than one field — that is fine. However, no relevant product detail should be skipped. Prioritize accuracy and completeness over strict disjoint classification.
                
                5. quantity: numerical quantity or R/O, if provided in the input.
                6. unit: corresponding unit, normalized (e.g., "Nos", "M", "KG"), as provided in the input.

                --------------------------------

                **Global Formatting Rules**:
                - Use lowercase for core_product_name, functional_descriptors, acronymed_core_product_name, but be true to original case (as provided in the input) for other fields.
                - Remove brackets, extra spaces, or vertical bars.
                - If slashes indicate "or", convert to "or", unless part of an acronym.
                - Preserve order of entries as in the table.


**Important: Product Block Rules**
- Product blocks must group related variants together under one block. Use cues like shared prefixes in sl. no. (e.g., 13.01, 13.02) or shared product names to group them.
- Do not split variants of the same product into different product blocks.
- Each block should contain all related product entries before moving to the next block.
- Do NOT drop any information from the input.

**Important: Product + Variant Rules for Extraction**
- If a row has a detailed description but an empty Quantity, 99 percent of the times it is a parent product.
- The following rows with filled Quantity and variant-specific description are its variants.
- Never output the parent row alone if variants exist.
- **Very Important:** Always INHERIT the parent description with each variant to form full product variant entries.

**Important: A note on Product Extraction**
- When extracting product entries, we only want to keep the details of the product that is being sourced in the BOQ, and no thte details of the existing products or systems that are to be replaced using this sourced product
- The part field in the list_of_specific_attributes should correspond to the part of the product that is being sourced in the BOQ. 
    - and respectively attribute and value should be the corresponding to this part of the product that is being sourced in the BOQ.


Return JSON. If any field is not applicable, return as an empty string but do not drop the field name.
i.e.
{
product_blocks: \\array of dictionaries where each dictionary contains the fields mentioned above for a product block
}
"""
                # 3. functional_descriptors_for_product
                # - Include adjectives or terms modifying the function (e.g. "open", "manual", "portable") of the product.




                
# for products and services both
system_prompt_product_entries_v2n_4 = """
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
                - reflect the input exactly as it is. Do not drop any information.
                
                2. is_service_and_not_product
                - true if the entry in consideration is a service and not a product.

                3. core_product_name / core_service_name (use respective field names for product and service)
                - Main name describing product type or function.
                - Expand acronyms if unambiguous (e.g. VFD → Vacuum Fluorescent Display).
                - Exclude size, specifications, or qualifiers like “FULL & REDUCED”.
                - Return in lowercase.

                4. functional_descriptors_for_product / functional_descriptors_for_service (use respective field names for product and service)
                - Include adjectives or terms modifying the function (e.g. "open", "manual", "portable").

                5. acronymed_core_product_name / acronymed_core_service_name (use respective field names for product and service)
                - Acronymed version of product name if present (e.g. "VFD Annunciators").
                - Exclude qualifiers or specs.

                Note: The fields `core_product_name / core_service_name`, `functional_descriptors_for_product / functional_descriptors_for_service`, and `acronymed_core_product_name / acronymed_core_service_name` are always singular, non-repeating, and not sub-part dependent. These should not be structured into a list or multi-level dictionary.

                6. list_of_specific_attributes (only for product entries)
                - a dict containing part, attribute, value as the fields.
                - Where the attribute is one of the following:
                    - material: MS, SS, Al, PVC, Rubber, etc.
                    - size_or_capacity: NB, OD, Sqmm, Flow, Pressure, Voltage
                    - type_or_class: Pipe Class, Cable Type, Valve Class
                    - standards_and_approvals: IS, IEC, ASTM, API, UL/FM, CE
                    - construction_features: Armour, Sheathing, End Connections, Flanges
                    - protection_features: Fireproof, UV proof, Anti-corrosion, Explosion proof
                    - mounting_or_installation: Hanger, Clamps, Supports, Surface/Underground
                    - operating_conditions: Temperature, Pressure, Environment (Indoor/Outdoor)
                    - connection_details: Threaded, Flanged, Glands, Couplings
                    - accessories_or_attachments: Lugs, Elbows, Reducers, JBs, Fasteners
                    - testing_or_inspection: Hydro test, FAT, TPI, Fire Safety Compliance
                    - special_attributes: Shielded cable, Bending Radius, Drum Length (cables), Seamed/Seamless (pipes)
                - The above-mentioned set of values for each attribute is non-exhaustive and is just for illustration.


                Note: 
                **Structured Output Format Guidance**:
                For the specific_attributes field, represent values as a list of dictionaries. 

                Each item in the list must be a dictionary with the following keys:
                - 'part': the component or sub-part of the product (e.g., inlet, outlet, nozzle) 
                    - write "product" here if the attribute is meant for the product as a whole and not for a specific sub-part of the product.
                - 'attribute': the type of property (e.g., diameter, coating, standard, connection type)
                - 'value': the corresponding value (e.g., 150 mm, hot dip galvanized, IS 1239)

                - This structure is important to allow granular indexing and querying in downstream systems. Thus, use this structure consistently across all the attributes listed above. 
                - Do not vary the key names.
                - **Very Important: Do not output the attribute field in flat format but stick to list of dictionaries with *part*, attribute, value as the fields.**
                - Do **not** include fields that are not present — avoid empty fields to minimize output size.
                - Thus output a compact JSON object with only relevant keys.
                **Important**: A product detail may be valid for more than one field — that is fine. However, no relevant product detail should be skipped. Prioritize accuracy and completeness over strict disjoint classification.

                *This correct format should be followed strictly for every attribute under the specific_attributes field.*
                *Examples of incorrect vs correct output formats for the same input: *

                Input: "Tri-Rated Flex Cables"
                Incorrect Output: {'core_product_name': 'cable', 'functional_descriptors': 'flex', 'specific_attributes': [{'part': 'product', 'type_or_class': 'Tri-Rated'}]}
                Correct Output: {'core_product_name': 'cable', 'functional_descriptors': 'flex', 'specific_attributes': [{'part': 'product', 'attribute': 'type_or_class', 'value': 'Tri-Rated'}]}

                Input: "THWN Wires" 
                Incorrect Output: {'core_product_name': 'wire', 'acronymed_core_product_name': 'THWN Wires', 'type_or_class': [{'part': 'product', 'attribute': 'cable type', 'value': 'THWN'}]}
                Correct Output: {'core_product_name': 'wire', 'acronymed_core_product_name': 'THWN Wires', 'specific_attributes': [{'part': 'product', 'attribute': 'type_or_class', 'value': 'THWN'}]}

                Input: "THHN-2 Wires"   
                Incorrect Output: {'core_product_name': 'wire', 'acronymed_core_product_name': 'thhn-2 wire', 'type_or_class': [{'part': 'product', 'attribute': 'cable type', 'value': 'THHN-2'}]}
                Correct Output: {'core_product_name': 'wire', 'acronymed_core_product_name': 'thhn-2 wire', 'specific_attributes': [{'part': 'product', 'attribute': 'type_or_class', 'value': 'THHN-2'}]}
                
                7. quantity: numerical quantity or R/O, if provided in the input.
                8. unit: corresponding unit, normalized (e.g., "Nos", "M", "KG"), as provided in the input.

                --------------------------------

                **Global Formatting Rules**:
                - Use lowercase for core_product_name, functional_descriptors, acronymed_core_product_name, but be true to original case (as provided in the input) for other fields.
                - Remove brackets, extra spaces, or vertical bars.
                - If slashes indicate "or", convert to "or", unless part of an acronym.
                - Preserve order of entries as in the table.


**Important: Product Block Rules**
- Product blocks must group related variants together under one block. Use cues like shared prefixes in sl. no. (e.g., 13.01, 13.02) or shared product names to group them.
- Do not split variants of the same product into different product blocks.
- Each block should contain all related product entries before moving to the next block.
- Do NOT drop any information from the input.

**Important: Product + Variant Rules for Extraction**
- If a row has a detailed description but an empty Quantity, 99 percent of the times it is a parent product.
- The following rows with filled Quantity and variant-specific description are its variants.
- Always INHERIT the parent description with each variant to form full product variant entries.
- Never output the parent row alone if variants exist.

**Very Very Important: Product and Service Rules**
- Note that a particular entry in a boq may refer to a product, or a service, or one or more services with the details of the products required for the service(s).
- If it consists of one or more services with the details of the products required for the service(s), 
    - then output the service(s) as a service entry with is_service_and_not_product as true.
    - and output the products required for the service(s) as product entries with is_service_and_not_product as false.
- The full_product_description should be the same for each of these product entries. But the core_product_name / core_service_name, functional_descriptors_for_product / functional_descriptors_for_service, and acronymed_core_product_name / acronymed_core_service_name shall be specific to the product or service being extracted.
- The list_of_specific_attributes should be different for each of these product entries and should only be present for the product entries.
- The quantity and unit shall be included only for the product entries.

Return JSON. If any field is not applicable, return as an empty string but do not drop the field name.
i.e.
{
product_blocks: \\array of dictionaries where each dictionary contains the fields mentioned above for a product block
}
"""

