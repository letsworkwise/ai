import json
import logging
from openai import OpenAI
import os
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

logger = logging.getLogger(__name__)

def parse_llm_response(content: str) -> dict:
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        logger.warning(f"JSON parse error: \n{e}")
        return {"ERROR": "JSON parse error for ...."}

import time
import random


class LLMCallFailure(Exception):
    pass

def llm_call_basic_with_llmcallfailure_exception(system_prompt, user_prompt, max_retries=3):
    attempt = 0
    content = None

    while attempt < max_retries:
        try:
            response = client.chat.completions.create(
                model="gpt-4.1", # "gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=16000,
                response_format={"type": "json_object"}
            )
            content = parse_llm_response(response.choices[0].message.content)
            tokens_used = (response.usage.prompt_tokens, response.usage.completion_tokens)
            return content, tokens_used

        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed: {e}")
            wait_time = 2 ** attempt + random.uniform(0, 1)
            time.sleep(wait_time)
            attempt += 1

    # Final failure
    raise LLMCallFailure("LLM call failed after retries")


