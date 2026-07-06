"""Model management service for LM Studio and Nemotron backends."""

import logging
import os
import subprocess
import time

import httpx

logger = logging.getLogger(__name__)

NEMOTRON_BASE_URL = 'http://localhost:8000'
NEMOTRON_CHAT_ENDPOINT = NEMOTRON_BASE_URL + '/v1/chat/completions'
NEMOTRON_READY_URL = NEMOTRON_BASE_URL + '/v1/models'
NEMOTRON_SCRIPT_PATH = '~/nemotron-vmlx.py'
NEMOTRON_READY_TIMEOUT_SECONDS = 30
NEMOTRON_TERMINATE_GRACE_SECONDS = 5

_nemotron_process: subprocess.Popen | None = None


def list_models() -> list[dict]:
    models: list[dict] = []

    llm_endpoint = os.environ.get('LLM_ENDPOINT', 'http://localhost:1234/v1/chat/completions')
    if llm_endpoint:
        base = llm_endpoint.removesuffix('/v1/chat/completions')
        try:
            response = httpx.get(base + '/api/v1/models', timeout=5)
            if response.status_code == 200:
                for model in response.json().get('models', []):
                    if model.get('loaded_instances'):
                        models.append({'id': model['key'], 'source': 'lmstudio'})
        except Exception:
            logger.exception('Failed to fetch LM Studio models')

    if is_nemotron_loaded():
        models.append({'id': 'nemotron', 'source': 'nemotron'})

    return models


def is_nemotron_loaded() -> bool:
    try:
        response = httpx.get(NEMOTRON_READY_URL, timeout=2)
        return response.status_code == 200
    except Exception:
        return False


def load_nemotron() -> dict:
    global _nemotron_process

    if is_nemotron_loaded():
        return {'status': 'loaded'}

    script_path = os.path.expanduser(NEMOTRON_SCRIPT_PATH)
    process = subprocess.Popen(['python3', script_path])
    _nemotron_process = process

    deadline = time.monotonic() + NEMOTRON_READY_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if process.poll() is not None:
            break
        try:
            response = httpx.get(NEMOTRON_READY_URL, timeout=5)
            if response.status_code == 200:
                return {'status': 'loaded'}
        except Exception:
            pass
        time.sleep(1)

    _nemotron_process.terminate()
    try:
        _nemotron_process.wait(timeout=NEMOTRON_TERMINATE_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        _nemotron_process.kill()
    _nemotron_process = None

    return {'status': 'error', 'message': 'timeout waiting for nemotron to become ready'}


def unload_nemotron() -> dict:
    global _nemotron_process

    if not is_nemotron_loaded():
        return {'status': 'unloaded'}

    if _nemotron_process is not None:
        _nemotron_process.terminate()
        try:
            _nemotron_process.wait(timeout=NEMOTRON_TERMINATE_GRACE_SECONDS)
        except subprocess.TimeoutExpired:
            _nemotron_process.kill()

    _nemotron_process = None
    return {'status': 'unloaded'}