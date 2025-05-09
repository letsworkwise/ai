import json
import pandas as pd

# Load the JSON data
with open("outputs/Miraj-BOQ_Electrical_Works/final_product_entries_with_matches_across_sheets.json", "r") as f:
    data = json.load(f)

# Convert to DataFrame
df = pd.DataFrame(data)

# Convert list columns to string (optional but helps with Excel formatting)
if 'list_of_product_ids' in df.columns:
    df['list_of_product_ids'] = df['list_of_product_ids'].apply(lambda x: ", ".join(x) if isinstance(x, list) else x)

# Save to Excel
df.to_excel("outputs/Miraj-BOQ_Electrical_Works/final_product_entries_with_matches_across_sheets.xlsx", index=False)

print("✅ JSON converted to Excel successfully.")
