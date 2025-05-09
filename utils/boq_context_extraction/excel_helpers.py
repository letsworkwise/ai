import pandas as pd
import re
from typing import List
import logging


logger = logging.getLogger(__name__)


def load_and_clean_excel(file_path: str, sheet_name: str) -> pd.DataFrame:
    df = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
    df = df.fillna('').map(lambda x: re.sub(r'\r\n|\r|\n', ' ', str(x)).strip())
    return df


def save_output_excel(filepath: str, final_products: List[dict]):
    df = pd.DataFrame(final_products)
    df.to_excel(filepath, index=False)