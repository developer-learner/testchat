"""Model management service for LM Studio and script-run local model servers."""

import logging
import os
import signal
import subprocess
import time

import httpx

logger = logging.getLogger(__name__)

NEMOTRON_BASE_URL = os.environ.get('NEMOTRON_URL', 'http://localhost:8600')
NEMOTRON_CHAT_ENDPOINT = NEMOTRON_BASE_URL + '/v1/chat/completions'
NEMOTRON_READY_URL = NEMOTRON_BASE_URL + '/v1/models'
NEMOTRON_SCRIPT_PATH = '~/nemotron-vmlx.py'
NEMOTRON_READY_TIMEOUT_SECONDS = 240
NEMOTRON_TERMINATE_GRACE_SECONDS = 5

DEEPSEEK_BASE_URL = os.environ.get('DS4_URL', 'http://127.0.0.1:8000')
DEEPSEEK_CHAT_ENDPOINT = DEEPSEEK_BASE_URL + '/v1/chat/completions'
DEEPSEEK_READY_URL = DEEPSEEK_BASE_URL + '/v1/models'
DEEPSEEK_SCRIPT_PATH = '/Users/arc.elixir/dev/ds4/run-server.sh'
DEEPSEEK_READY_TIMEOUT_SECONDS = 180

SCRIPT_MODEL_TERMINATE_GRACE_SECONDS = NEMOTRON_TERMINATE_GRACE_SECONDS

# Registry of script-run models. `command` is the argv to launch the server;
# `ready_timeout_attr` names the module-level timeout constant so tests can
# monkeypatch e.g. NEMOTRON_READY_TIMEOUT_SECONDS and be observed at call time.
SCRIPT_MODELS: dict[str, dict] = {
    'nemotron': {
        'id': 'nemotron',
        'base_url': NEMOTRON_BASE_URL,
        'chat_endpoint': NEMOTRON_CHAT_ENDPOINT,
        'ready_url': NEMOTRON_READY_URL,
        'command': ['python3', os.path.expanduser(NEMOTRON_SCRIPT_PATH)],
        'ready_timeout_attr': 'NEMOTRON_READY_TIMEOUT_SECONDS',
    },
    'deepseek-v4-flash': {
        'id': 'deepseek-v4-flash',
        'base_url': DEEPSEEK_BASE_URL,
        'chat_endpoint': DEEPSEEK_CHAT_ENDPOINT,
        'ready_url': DEEPSEEK_READY_URL,
        'command': [DEEPSEEK_SCRIPT_PATH],
        'ready_timeout_attr': 'DEEPSEEK_READY_TIMEOUT_SECONDS',
    },
}

_script_processes: dict[str, subprocess.Popen | None] = {}
# Back-compat alias used by tests and src/api/status.py; kept in sync below.
_nemotron_process: subprocess.Popen | None = None


def get_script_model(model_id: str) -> dict | None:
    return SCRIPT_MODELS.get(model_id)


def _sync_nemotron_alias() -> None:
    global _nemotron_process
    _nemotron_process = _script_processes.get('nemotron')


def _get_process(model_id: str) -> subprocess.Popen | None:
    # `_nemotron_process` is the historical public handle (status API, tests
    # assign it directly), so it stays authoritative for nemotron.
    if model_id == 'nemotron':
        return _nemotron_process
    return _script_processes.get(model_id)


def _set_process(model_id: str, process: subprocess.Popen | None) -> None:
    global _nemotron_process
    _script_processes[model_id] = process
    if model_id == 'nemotron':
        _nemotron_process = process


def _responds_ready(ready_url: str) -> bool:
    try:
        response = httpx.get(ready_url, timeout=2)
        return response.status_code == 200
    except Exception:
        return False


def is_script_model_loaded(model_id: str) -> bool:
    if model_id == 'nemotron':
        # Route through the module attribute so existing monkeypatches of
        # is_nemotron_loaded keep working.
        return is_nemotron_loaded()
    entry = SCRIPT_MODELS[model_id]
    return _responds_ready(entry['ready_url'])


def _terminate_process(process: subprocess.Popen) -> None:
    process.send_signal(signal.SIGINT)
    try:
        process.wait(timeout=SCRIPT_MODEL_TERMINATE_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        process.kill()


def _unload_other_script_models(model_id: str) -> None:
    """Mutual exclusion: script models are RAM-heavy, only one runs at a time."""
    for other_id in SCRIPT_MODELS:
        if other_id == model_id:
            continue
        if _get_process(other_id) is not None or is_script_model_loaded(other_id):
            logger.info('Unloading %s before loading %s', other_id, model_id)
            unload_script_model(other_id)


def load_script_model(model_id: str) -> dict:
    entry = SCRIPT_MODELS[model_id]

    if is_script_model_loaded(model_id):
        return {'status': 'loaded'}

    _unload_other_script_models(model_id)

    process = subprocess.Popen(entry['command'])
    _set_process(model_id, process)

    timeout_seconds = globals()[entry['ready_timeout_attr']]
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if process.poll() is not None:
            break
        try:
            response = httpx.get(entry['ready_url'], timeout=5)
            if response.status_code == 200:
                return {'status': 'loaded'}
        except Exception:
            # ready-poll: connection errors are expected until the server
            # binds; retried until the deadline
            pass
        time.sleep(1)

    _terminate_process(process)
    _set_process(model_id, None)

    return {'status': 'error', 'message': f'timeout waiting for {model_id} to become ready'}


def unload_script_model(model_id: str) -> dict:
    # A tracked process is terminated even when its HTTP side is unresponsive:
    # a hung server still holds RAM, and _unload_other_script_models relies on
    # this kill for the mutual-exclusion guarantee. Gating on the ready check
    # here would leak exactly the zombie it exists to evict.
    process = _get_process(model_id)
    if process is not None:
        _terminate_process(process)

    _set_process(model_id, None)
    return {'status': 'unloaded'}


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

    for model_id in SCRIPT_MODELS:
        if is_script_model_loaded(model_id):
            models.append({'id': model_id, 'source': model_id})

    return models


def list_model_catalog() -> list[dict]:
    return [
        {'id': model_id, 'source': model_id, 'loaded': is_script_model_loaded(model_id)}
        for model_id in SCRIPT_MODELS
    ]


def is_nemotron_loaded() -> bool:
    return _responds_ready(NEMOTRON_READY_URL)


def load_nemotron() -> dict:
    return load_script_model('nemotron')


def unload_nemotron() -> dict:
    return unload_script_model('nemotron')
