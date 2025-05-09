import pandas as pd
import difflib
import logging

logger = logging.getLogger(__name__)

def load_first_n_rows_as_markdown(df: pd.DataFrame, num_rows: int = 20) -> str:
    df_chunk = df.iloc[:num_rows]
    markdown_lines = df_chunk.apply(lambda row: ' | '.join(row.astype(str)), axis=1).tolist()
    return '\n'.join(markdown_lines)

def find_max_column_idx(header_md: str) -> int:
    """
    Given a markdown-style header block, find the maximum number of columns based on row splits.
    """
    header_lines = [line.strip() for line in header_md.strip().split("\n") if line.strip()]
    col_counts = [len(row.split("|")) for row in header_lines]
    return max(col_counts) if col_counts else 0

def find_header_start_idx(df: pd.DataFrame, header_md: str) -> int:
    header_lines = [line.strip() for line in header_md.strip().split("\n") if line.strip()]
    header_row_blocks = [[cell.strip() for cell in row] for row in df.astype(str).values.tolist()]

    for i in range(len(header_row_blocks) - len(header_lines) + 1):
        block = header_row_blocks[i:i + len(header_lines)]
        joined_block = [' | '.join(row) for row in block]
        score = sum(
            difflib.SequenceMatcher(None, a, b).ratio()
            for a, b in zip(joined_block, header_lines)
        ) / len(header_lines)
        if score >= 0.7:
            return i + len(header_lines)

    raise ValueError("Header block not found")