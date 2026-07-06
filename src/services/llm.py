import json
import os
from typing import Iterator, Sequence

import urllib.error
import urllib.request


StreamChunk = tuple[str, ...]

FALLBACK_REPLY = "The language model is currently unavailable. Please try again in a moment."


def stream_reply(
    message: str,
    history: Sequence[dict[str, str]] = (),
    endpoint_override: str | None = None,
    model: str | None = None,
) -> Iterator[StreamChunk]:
    endpoint = (
        endpoint_override
        if endpoint_override is not None
        else os.environ.get("LLM_ENDPOINT", "http://localhost:1234/v1/chat/completions")
    )
    LLM_SYSTEM_PROMPT = os.environ.get("LLM_SYSTEM_PROMPT", "")
    LLM_TIMEOUT_SECONDS = float(os.environ.get("LLM_TIMEOUT_SECONDS", "120"))

    request_model = (
        model if model is not None else os.environ.get("LLM_MODEL", "local-model")
    )

    messages: list[dict[str, str]] = []
    if LLM_SYSTEM_PROMPT:
        messages.append({"role": "system", "content": LLM_SYSTEM_PROMPT})
    for entry in history:
        messages.append({"role": entry["role"], "content": entry["content"]})
    messages.append({"role": "user", "content": message})

    request_body = {
        "model": request_model,
        "messages": messages,
        "stream": True,
    }

    tokens_yielded = False

    try:
        req = urllib.request.Request(
            endpoint,
            json.dumps(request_body).encode(),
            {"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=LLM_TIMEOUT_SECONDS) as response:
            if response.status != 200:
                yield ("error",)
                return

            buf = b""
            while True:
                chunk = response.fp.read1(4096)
                if not chunk:
                    break
                buf += chunk
                while b"\n" in buf:
                    raw_line, buf = buf.split(b"\n", 1)
                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if not line.startswith("data: "):
                        continue

                    data = line[6:]

                    if data.strip() == "[DONE]":
                        if tokens_yielded:
                            yield ("done",)
                        else:
                            yield ("error",)
                        return

                    try:
                        parsed = json.loads(data)
                        content = (
                            parsed.get("choices", [{}])[0]
                            .get("delta", {})
                            .get("content")
                        )
                        if content:
                            yield ("token", content)
                            tokens_yielded = True
                    except (json.JSONDecodeError, KeyError, IndexError):
                        yield ("error",)
                        return

        yield ("error",)

    except (urllib.error.URLError, ValueError, OSError):
        yield ("error",)


__all__ = ["stream_reply", "FALLBACK_REPLY"]