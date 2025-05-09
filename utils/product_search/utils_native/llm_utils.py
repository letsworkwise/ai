import logging
logger = logging.getLogger(__name__)

from utils.product_search.utils_native.product_match_prompts import CORE_MATCH_SYSTEM_PROMPT, VARIANT_MATCH_SYSTEM_PROMPT, build_user_prompt
from utils.product_search.utils_native.llm_core_utils import llm_call_basic_with_llmcallfailure_exception

def build_prompts(query: str, candidates: list, stage: str) -> tuple[str, str]:
    system_prompt = CORE_MATCH_SYSTEM_PROMPT if stage == "core" else VARIANT_MATCH_SYSTEM_PROMPT
    user_prompt = build_user_prompt(query, candidates)
    return system_prompt, user_prompt

def finalize_matches_via_llm(query: str, candidates: list, stage: str) -> list:
    system_prompt, user_prompt = build_prompts(query, candidates, stage)
    result, tokens_used = llm_call_basic_with_llmcallfailure_exception(system_prompt, user_prompt)
    return result.get("matches"), tokens_used