import pandas as pd
import logging

logger = logging.getLogger(__name__)

def format_batch_as_markdown(df_schedule: pd.DataFrame, header_md: str, start_idx: int = 0, batch_size: int = 20) -> str:
    df_batch = df_schedule.iloc[start_idx:min(start_idx + batch_size, len(df_schedule))]

    # Parse header and get expected number of columns
    header_lines = [line.strip() for line in header_md.strip().split("\n") if line.strip()]
    num_cols = max(line.count("|") for line in header_lines)
    header_rows = "\n".join(header_lines)
    
    # Build proper markdown header and separator
    separator = " | ".join(["---"] * (num_cols + 1))

    # Sanitize batch rows to match header column count
    markdown_rows = []
    for _, row in df_batch.iterrows():
        cells = list(row.astype(str))
        cells = cells[:num_cols + 1]  # trim extra cols
        cells += [""] * (num_cols + 1 - len(cells))  # pad missing cols
        markdown_rows.append(" | ".join(cells))

    return f"{header_rows}\n{separator}\n" + '\n'.join(markdown_rows)
