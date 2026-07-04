import json
import os

import httpx

FALLBACK_REPLY = 'The language model is currently unavailable. Please try again in a moment.'


def generate_reply(message: str) -> str:
    LLM_ENDPOINT = os.environ.get('LLM_ENDPOINT', 'http://localhost:1234/v1/chat/completions')
    LLM_MODEL = os.environ.get('LLM_MODEL', 'local-model')
    LLM_SYSTEM_PROMPT = os.environ.get('LLM_SYSTEM_PROMPT', '')
    LLM_TIMEOUT_SECONDS = os.environ.get('LLM_TIMEOUT_SECONDS', '120')

    messages: list[dict[str, str]] = []
    if LLM_SYSTEM_PROMPT:
        messages.append({"role": "system", "content": LLM_SYSTEM_PROMPT})
    messages.append({"role": "user", "content": message})

    request_body = {
        "model": LLM_MODEL,
        "messages": messages,
        "stream": False,
    }

    try:
        with httpx.Client() as client:
            response = client.post(
                LLM_ENDPOINT,
                json=request_body,
                timeout=float(LLM_TIMEOUT_SECONDS),
            )

        if response.status_code != 200:
            return FALLBACK_REPLY

        data = response.json()
        content = (data.get("choices", [{}])[0].get("message", {}).get("content"))
        if content:
            return content

    except (httpx.HTTPError, json.JSONDecodeError, KeyError, IndexError, ValueError):
        return FALLBACK_REPLY

    return FALLBACK_REPLY