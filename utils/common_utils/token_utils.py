import logging
import os

from utils.common_utils.json_helpers import save_output_json

logger = logging.getLogger(__name__)

input_cost_gpt_4o = 2.5 # per million input tokens
output_cost_gpt_4o = 10 # per million output tokens

def aggregate_token_usage(results):
    total_prompt, total_completion = 0, 0
    for prompt, completion in results:
        total_prompt += prompt
        total_completion += completion
    return total_prompt, total_completion

def reverse_tokens(tokens_used_tuple):
    return tokens_used_tuple[1], tokens_used_tuple[0]


def log_costs(prompt_tokens: int, completion_tokens: int):
    cost_prompt = (prompt_tokens / 1_000_000) * input_cost_gpt_4o
    cost_completion = (completion_tokens / 1_000_000) * output_cost_gpt_4o
    total_cost = cost_prompt + cost_completion
    logger.info(f"🧠 Prompt tokens: {prompt_tokens}, Completion tokens: {completion_tokens}")
    logger.info(f"💰 Estimated Cost: ${total_cost:.4f} (Prompt: ${cost_prompt:.4f}, Completion: ${cost_completion:.4f})")

    return total_cost  # ✅ added return value

def summarize_cost_and_processing_time(file_path: str, total_prompt_tokens: int, total_completion_tokens: int, total_cost: float, total_processing_time: float):
    summary_data = {
        "total_prompt_tokens": total_prompt_tokens,
        "total_completion_tokens": total_completion_tokens,
        "aggregate_cost_usd": round(total_cost, 4),
        "total_processing_time": total_processing_time
    }
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    safe_base = "".join(c if c.isalnum() or c in ("_", "-") else "_" for c in base_name)
    os.makedirs(os.path.join("outputs", safe_base), exist_ok=True)
    save_output_json(os.path.join("outputs", safe_base, "cost_and_processing_time_for_extraction.json"), summary_data)

    return summary_data["aggregate_cost_usd"], summary_data["total_processing_time"]


def log_cost_and_processing_time(file_path: str, prompt_tokens: int, completion_tokens: int, elapsed_time: float):
    logger.info("===== Aggregate Token and Cost Summary  for extraction part =====")
    total_cost = log_costs(prompt_tokens, completion_tokens)
    logger.info("================================================================")
    logger.info(f"✅ All sheets processed in {elapsed_time:.2f} seconds")

    aggregate_cost_usd, total_processing_time = summarize_cost_and_processing_time(file_path, prompt_tokens, completion_tokens, total_cost, elapsed_time)
    return aggregate_cost_usd, total_processing_time
