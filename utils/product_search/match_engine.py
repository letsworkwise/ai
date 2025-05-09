import pandas as pd
import json
import re
from uuid import uuid4
import logging
logger = logging.getLogger(__name__)

from utils.product_search.utils_native.utils import build_stage2_query, sanitize_product_ids, normalize_name, normalize_name_for_filename
from utils.product_search.utils_native.utils import VARIANT_INDEX_NAME, get_pinecone_index
from utils.product_search.utils_native.utils import log_intermediate
from utils.product_search.utils_native.utils import embed_texts
from utils.product_search.utils_native.utils import query_pinecone_top_k
from utils.product_search.utils_native.llm_utils import finalize_matches_via_llm

VARIANT_INDEX_NAME = get_pinecone_index(VARIANT_INDEX_NAME)
TOP_K = 30 # based on the performance and cost, include reranking of top 10 of these 30 retrieval results

import unicodedata

def clean_prompt_text(text: str) -> str:
    # Remove control chars (Unicode category C), normalize weird unicode, remove BOMs, and strip leading/trailing junk
    return ''.join(
        ch for ch in unicodedata.normalize("NFKC", text)
        if unicodedata.category(ch)[0] != "C"
    ).replace('\uFEFF', '').strip()


def match_product_entry(i: int, entry: dict, log_dir: str = "logs"):
    core = entry.get("core_product_name")
    acronym = entry.get("acronymed_core_product_name")
    if core:
        query_id = f"{i}_core_{normalize_name_for_filename(core)}_{uuid4().hex}" 
    elif acronym:
        query_id = f"{i}_acronym_{normalize_name_for_filename(acronym)}_{uuid4().hex}"
    else:
        query_id = f"{i}_no_core_or_acronym_extracted_{uuid4().hex}"


    # ---- Direct Variant-level Matching ----
    stage2_query = build_stage2_query(entry)

    if not stage2_query.strip():
        logger.error(f"❌ Empty query sent to embed_texts() for entry {i}, query: {stage2_query}")
        raise ValueError("Empty query sent to embed_texts()")

    stage2_emb = embed_texts([stage2_query], input_type="query")[0]
    stage2_results = query_pinecone_top_k(
        VARIANT_INDEX_NAME,
        stage2_query,
        stage2_emb,
        TOP_K,
        # filter={"core_id": {"$in": shortlisted_core_ids}}         # this is how we shall proceed in future
    )

    # print(stage2_results) if i == 17 else None

    log_intermediate("stage2_topk", query_id, {"query": stage2_query, "retrieval_results": stage2_results}, base_log_dir=log_dir)
    
    flat_stage2_results = [
        {
            "retrieval_score": res["score"], 
            "text": res["metadata"]["text"], 
            "core_id": res["metadata"]["core_id"], 
            "raw_product_name": res["metadata"]["raw_product_name"],
            "list_of_product_ids": sanitize_product_ids(res["metadata"].get("list_of_product_ids", ""))
        }
        for res in stage2_results
    ]
    log_intermediate("flat_stage2_results", query_id, {"flat_stage2_results": flat_stage2_results}, base_log_dir=log_dir)
    
    product_id_lookup = {
        normalize_name(res["raw_product_name"]): res["list_of_product_ids"]
        for res in flat_stage2_results
    }

    log_intermediate("product_id_lookup", query_id, {"product_id_lookup": product_id_lookup}, base_log_dir=log_dir)

    flat_stage2_results_for_llm = [
        {
            "text": res["text"],
            "raw_product_name": clean_prompt_text(res["raw_product_name"]),
        }
        for res in flat_stage2_results
    ]

    log_intermediate("flat_stage2_results_for_llm", query_id, {"flat_stage2_results_for_llm": flat_stage2_results_for_llm}, base_log_dir=log_dir)

    final_variant_matches, (prompt_tokens, completion_tokens) = finalize_matches_via_llm(
        stage2_query, flat_stage2_results_for_llm, stage="variant"
        )
    

    flat_final_variant_matches = [
        {
            "text": match["match_details"]["text"],
            "raw_product_name": match["match_details"]["raw_product_name"],
        }
        for match in final_variant_matches
    ]
    
    log_intermediate("flat_final_variant_matches", query_id, {"final_variant_matches": flat_final_variant_matches}, base_log_dir=log_dir)

    for match in final_variant_matches:
        try:
            raw_name = normalize_name(match["match_details"]["raw_product_name"])
            match["match_details"]["list_of_product_ids"] = product_id_lookup.get(raw_name, [])
        except KeyError as e:
            logger.error(f"Missing key in LLM match result at entry {i}: {e}\nMatch: {match}")
            # raise

    log_intermediate("stage2_llm_matches", query_id, {"query": stage2_query, "final_matches": final_variant_matches}, base_log_dir=log_dir)

    # return object of type 
    # {
    #   "rank": 1,
    #   "fields_matched": [
    #     "core_product_name",
    #     "acronymed_core_product_name"
    #   ],
    #   "match_details": {
    #     "text": "core_product_name: galvanized iron pipe | acronymed_core_product_name: gi pipe",
    #     "raw_product_name": "GI PIPE",
    #     "list_of_product_ids": [
    #       "15427",
    #       "17238",
    #       "17227",
    #       "30897",
    #       "30959",
    #       "27363",
    #       "28754",
    #       "28918",
    #       "28967",
    #       "35290",
    #       "35308",
    #       "35313",
    #       "39993"
    #     ]
    #   }
    # }

    return {
        "top_match": final_variant_matches[0],
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens
    }

if __name__ == "__main__":
    # entry = {
    #     "core_product_name": "pipe",
    #     "size": "nominal bore: 200",
    #     "feature_or_specifications": "material: galvanized iron, class: c, standard: indian standard 1239 part-i, manufacturer: tata",
    #     "acronymed_core_product_name": "",
    # }
    entry =    {
      "section_context_for_this_product_block": [
        "D | Grooved 90° Elbow"
      ],
      "full_product_description": "1 | 200NB",

      "core_product_name": "grooved 90° elbow",
      "acronymed_core_product_name": "",
      "size": "elbow size: 200 NB",
      "feature_or_specifications": "",

      "quantity": "4.0",
      "unit": "Nos.",
    }
    match_product_entry_result = match_product_entry(0, entry)
    print(match_product_entry_result)

