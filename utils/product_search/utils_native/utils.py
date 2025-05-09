import time
import os
import json
import re
import unicodedata
from typing import List, Dict
import logging
logger = logging.getLogger(__name__)

# --- Match Engine Utils ---
import pandas as pd
def build_stage2_query(entry: dict) -> str:
    fields = {
        "core_product_name": entry.get("core_product_name"),
        "acronymed_core_product_name": entry.get("acronymed_core_product_name"),
        "size": entry.get("size"),
        "feature_or_specifications": entry.get("feature_or_specifications")
    }
    
    return " | ".join(
        f"{k}: {str(v).strip()}"
        for k, v in fields.items()
        if pd.notna(v) and str(v).strip().lower() != "nan" and str(v).strip()
    )

def normalize_name(name: str) -> str:
    return " ".join(str(name).strip().lower().split())

def normalize_name_for_filename(name: str) -> str:
    # Normalize unicode to ASCII (removes accents, emojis, etc.)
    name = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode("ascii")
    name = name.strip().lower()

    # Replace spaces and slashes with underscores
    name = re.sub(r"[ /\\]", "_", name)

    # Remove everything that's not safe in filenames
    name = re.sub(r"[^a-z0-9._-]", "", name)

    return name[:20]  # truncate for filesystem safety


def sanitize_product_ids(val):
    if pd.isna(val) or str(val).strip().lower() in {"", "nan"}:
        return []
    return [pid.strip() for pid in str(val).split(",") if pid.strip().isdigit()]


# --- Pinecone Utils ---
from pinecone.grpc import PineconeGRPC
from pinecone import ServerlessSpec
from requests.exceptions import HTTPError

EMBED_MODEL = "multilingual-e5-large"
RERANK_MODEL = "bge-reranker-v2-m3"
# PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
REGION = "us-east-1"
CLOUD = "aws"
CORE_INDEX_NAME = "core-products-index-v01"
# VARIANT_INDEX_NAME = "variant-flattened-index-v01" # with AND
VARIANT_INDEX_NAME = "variant-flattened-index-v011" # with | 

# pc = PineconeGRPC(api_key=PINECONE_API_KEY)
pc = PineconeGRPC()
spec = ServerlessSpec(cloud=CLOUD, region=REGION)

# GET PINECONE INDEX
def get_pinecone_index(index_name: str):
    existing_indexes = [idx["name"] for idx in pc.list_indexes()]
    if index_name in existing_indexes:
        print(f"🔍 Index exists: {index_name}")
        index = pc.Index(index_name)
        while not pc.describe_index(index_name).status["ready"]:
            time.sleep(1)
    else:
        print(f"🔍 Index does not exist: {index_name}")
        raise ValueError(f"Index {index_name} does not exist")
    
    print(index.describe_index_stats())

    return index


# --- Logger Utils ---
LOG_DIR = "logs"            # Need to change this and make it per sheet
os.makedirs(LOG_DIR, exist_ok=True)

import numpy as np

def json_safe(obj):
    if isinstance(obj, (np.floating, float)):
        return float(obj)
    if isinstance(obj, (np.integer, int)):
        return int(obj)
    if isinstance(obj, bytes):
        return obj.decode()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def log_intermediate(stage: str, query_id: str, data: dict, base_log_dir: str = LOG_DIR):
    log_file = os.path.join(base_log_dir, f"{query_id}__{stage}.json")
    with open(log_file, "w", encoding="utf-8") as f:
        # json.dump(data, f, indent=2, ensure_ascii=False)
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)



# --- Embedding Utils ---
def embed_texts(texts: List[str], input_type: str = "passage"):
    for attempt in range(5):
        try:
            res = pc.inference.embed(
                model=EMBED_MODEL,
                inputs=texts,
                parameters={"input_type": input_type, "truncate": "END"}
            )
            return [x["values"] for x in res.data]
        except HTTPError:
            time.sleep(2 ** attempt)
        except Exception as e:
            logger.warning(f"Embed error: {e}")
            time.sleep(2 ** attempt)
    raise RuntimeError("Embedding failed after retries")

def query_pinecone_top_k(index, query: str, embedding: List[float], top_k: int, filter: dict = None) -> List[Dict]:
    for attempt in range(5):
        try:
            res = index.query(
                vector=embedding,
                top_k=top_k,
                include_metadata=True,
                filter=filter or {}
            )
            return [
                {"id": match["id"], "score": match["score"], "metadata": match.get("metadata", {})}
                for match in res["matches"]
            ]
        except Exception as e:
            print(f"Retrying query for {query} due to error: {e}")
            time.sleep(2 ** attempt)
    raise RuntimeError(f"Failed to query {query}")


