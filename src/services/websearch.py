"""Tavily web search client (M25). Key from TAVILY_API_KEY; endpoint overridable via TAVILY_ENDPOINT for the sandboxed suite."""

import json
import logging
import os
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)

DEFAULT_ENDPOINT = 'https://api.tavily.com/search'
MAX_SOURCES = 4
MAX_CONTENT_CHARS = 2000


class WebSearchError(Exception):
    """Any failure to obtain search results — caller falls back to an un-augmented call."""


def is_configured() -> bool:
    return bool(os.environ.get('TAVILY_API_KEY', '').strip())


def search_web(query: str) -> list[dict]:
    if not is_configured():
        raise WebSearchError('TAVILY_API_KEY not configured')

    endpoint = os.environ.get('TAVILY_ENDPOINT', DEFAULT_ENDPOINT)
    api_key = os.environ.get('TAVILY_API_KEY', '')
    # A malformed TAVILY_TIMEOUT_SECONDS must degrade like any other search
    # failure (WebSearchError → the caller's notice), not raise a bare
    # ValueError that escapes the stream's WebSearchError handler.
    raw_timeout = os.environ.get('TAVILY_TIMEOUT_SECONDS', '10')
    try:
        timeout = float(raw_timeout)
    except (TypeError, ValueError) as exc:
        logger.warning('Invalid TAVILY_TIMEOUT_SECONDS %r: %s', raw_timeout, exc)
        raise WebSearchError(f'invalid TAVILY_TIMEOUT_SECONDS: {raw_timeout!r}') from exc

    payload = json.dumps({'query': query, 'max_results': MAX_SOURCES}).encode('utf-8')
    req = urllib.request.Request(
        endpoint,
        data=payload,
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}',
        },
        method='POST',
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode('utf-8')
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
        logger.warning('Tavily search request failed: %s', exc)
        raise WebSearchError(str(exc)) from exc

    try:
        data = json.loads(body)
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning('Tavily search response JSON parse failed: %s', exc)
        raise WebSearchError(str(exc)) from exc

    try:
        results = data['results']
    except (KeyError, TypeError) as exc:
        logger.warning('Tavily search response missing results: %s', exc)
        raise WebSearchError(str(exc)) from exc

    sources: list[dict] = []
    for r in results[:MAX_SOURCES]:
        try:
            sources.append({
                'title': str(r.get('title', '')),
                'url': str(r.get('url', '')),
                'content': str(r.get('content', ''))[:MAX_CONTENT_CHARS],
            })
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning('Tavily result parsing failed: %s', exc)
            raise WebSearchError(str(exc)) from exc

    return sources


def build_prompt(message: str, sources: list[dict]) -> str:
    lines = [
        'Web search results below. Cite as [1] or [2] — plain square brackets '
        'with a number, nothing else. Prefer the most specific/recent number '
        'from any source; if sources disagree, list both with citations.\n\n'
    ]
    for i, src in enumerate(sources, 1):
        lines.append(f'[{i}] {src["title"]}\n{src["url"]}\n{src["content"]}\n\n')
    lines.append(f'Using the results above when relevant, answer:\n{message}')
    return ''.join(lines)