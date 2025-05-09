
from utils.llm_interface.calling import llm_call_basic_with_llmcallfailure_exception
from utils.prompts.boq_context_prompts import system_prompt_boq_context, custom_instructions_boq_context
from utils.prompts.user_prompts import user_prompt_basic
from typing import Tuple
import logging


logger = logging.getLogger(__name__)

def extract_boq_context(full_markdown_table: str, custom_instructions_user_input: str = "") -> Tuple[dict, int]:
    custom_instructions = (
        custom_instructions_boq_context.format(custom_instructions=custom_instructions_user_input)
        if custom_instructions_user_input.strip() else None
    )
    system_prompt = system_prompt_boq_context
    if custom_instructions:
        system_prompt += custom_instructions_boq_context.format(custom_instructions=custom_instructions)
    user_prompt = user_prompt_basic.format(text=full_markdown_table)
    content, tokens_used = llm_call_basic_with_llmcallfailure_exception(system_prompt, user_prompt)
    return content, tokens_used
