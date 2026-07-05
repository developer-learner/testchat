import json
import os
from typing import Iterator, NamedTuple, Optional, Sequence

import urllib.error
import urllib.request


class StreamChunk(NamedTuple):
    event: str  # "token", "done", or "error"
    content: Optional[str] = None


FALLBACK_REPLY = 'The language model is currently unavailable. Please try again in a moment.'


def stream_reply(message: str, history: Sequence[dict[str, str]] = ()) -> Iterator[StreamChunk]:
    LLM_ENDPOINT = os.environ.get('LLM_ENDPOINT', 'http://localhost:1234/v1/chat/completions')
    LLM_MODEL = os.environ.get('LLM_MODEL', 'local-model')
    LLM_SYSTEM_PROMPT = os.environ.get('LLM_SYSTEM_PROMPT', '')
    LLM_TIMEOUT_SECONDS = float(os.environ.get('LLM_TIMEOUT_SECONDS', '120'))

    messages: list[dict[str, str]] = []
    if LLM_SYSTEM_PROMPT:
        messages.append({"role": "system", "content": LLM_SYSTEM_PROMPT})
    for entry in history:
        messages.append({"role": entry["role"], "content": entry["content"]})
    messages.append({"role": "user", "content": message})

    request_body = {
        "model": LLM_MODEL,
        "messages": messages,
        "stream": True,
    }

    tokens_yielded = False

    try:
        req = urllib.request.Request(
            LLM_ENDPOINT,
            json.dumps(request_body).encode(),
            {"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=LLM_TIMEOUT_SECONDS) as response:
            if response.status != 200:
                yield StreamChunk("error")
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
                            yield StreamChunk("done")
                        else:
                            yield StreamChunk("error")
                        return

                    try:
                        parsed = json.loads(data)
                        content = (parsed.get("choices", [{}])[0].get("delta", {}).get("content"))
                        if content:
                            yield StreamChunk("token", content)
                            tokens_yielded = True
                    except (json.JSONDecodeError, KeyError, IndexError):
                        yield StreamChunk("error")
                        return

        yield StreamChunk("error")

    except (urllib.error.URLError, ValueError, OSError):
        yield StreamChunk("error")


__all__ = ["stream_reply", "FALLBACK_REPLY"]