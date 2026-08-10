"""Model management service for LM Studio and script-run local model servers."""

import logging
import os
import signal
import subprocess
import time
from urllib.parse import urlparse

import httpx
import psutil

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

DEEPSEEK_0731_BASE_URL = os.environ.get('DS4_0731_URL', 'http://127.0.0.1:8005')
DEEPSEEK_0731_CHAT_ENDPOINT = DEEPSEEK_0731_BASE_URL + '/v1/chat/completions'
DEEPSEEK_0731_READY_URL = DEEPSEEK_0731_BASE_URL + '/v1/models'
DEEPSEEK_0731_SCRIPT_PATH = '/Users/arc.elixir/dev/ds4/run-server-0731.sh'
DEEPSEEK_0731_READY_TIMEOUT_SECONDS = 300

SCRIPT_MODEL_TERMINATE_GRACE_SECONDS = NEMOTRON_TERMINATE_GRACE_SECONDS


def _find_listening_pid(port: int) -> int | None:
    """Return the PID listening on `port`, else None."""
    for proc in psutil.process_iter(['pid']):
        try:
            for conn in proc.net_connections(kind='inet'):
                if conn.status == psutil.CONN_LISTEN and conn.laddr.port == port:
                    return proc.pid
        except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.Error):
            continue   # not our process; skip it and keep scanning
    return None


def _terminate_pid(pid: int) -> None:
    """Send SIGINT, grace period, then SIGKILL if still alive."""
    try:
        os.kill(pid, signal.SIGINT)
    except ProcessLookupError:
        # Process already exited — nothing to terminate, safe to ignore.
        return
    deadline = time.monotonic() + SCRIPT_MODEL_TERMINATE_GRACE_SECONDS
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            # Process already exited during grace period — safe to ignore.
            return
        time.sleep(0.25)
    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        # Process already exited — safe to ignore.
        pass


def _pid_is_model_server(pid: int, entry: dict) -> bool:
    """Return True if the process cmdline matches the model server entry."""
    try:
        cmdline = psutil.Process(pid).cmdline()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False
    target = None
    for token in reversed(entry['command']):
        if not token.isdigit():
            target = os.path.basename(token)
            break
    if target is None:
        return False
    for token in cmdline:
        if os.path.basename(token) == target:
            return True
    return False


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
    'deepseek-v4-flash-0731': {
        'id': 'deepseek-v4-flash-0731',
        'base_url': DEEPSEEK_0731_BASE_URL,
        'chat_endpoint': DEEPSEEK_0731_CHAT_ENDPOINT,
        'ready_url': DEEPSEEK_0731_READY_URL,
        'command': [DEEPSEEK_0731_SCRIPT_PATH],
        'ready_timeout_attr': 'DEEPSEEK_0731_READY_TIMEOUT_SECONDS',
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
            if is_script_model_loaded(other_id):
                raise RuntimeError(f'failed to evict {other_id}')


def load_script_model(model_id: str) -> dict:
    entry = SCRIPT_MODELS[model_id]

    if is_script_model_loaded(model_id):
        return {'status': 'loaded'}

    # Evict any other script model before spawning.
    for other_id in SCRIPT_MODELS:
        if other_id == model_id:
            continue
        if _get_process(other_id) is not None or is_script_model_loaded(other_id):
            logger.info('Unloading %s before loading %s', other_id, model_id)
            result = unload_script_model(other_id)
            if result['status'] == 'error':
                return {'status': 'error', 'message': f'could not evict {other_id}'}

    process = subprocess.Popen(entry['command'])
    _set_process(model_id, process)

    timeout_seconds = globals()[entry['ready_timeout_attr']]
    deadline = time.monotonic() + timeout_seconds
    child_exited = False
    while time.monotonic() < deadline:
        if process.poll() is not None:
            child_exited = True
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

    if child_exited:
        return {'status': 'error', 'message': f'child exited before {model_id} became ready'}
    return {'status': 'error', 'message': f'timeout waiting for {model_id} to become ready'}


def unload_script_model(model_id: str) -> dict:
    entry = SCRIPT_MODELS[model_id]
    # A tracked process is terminated even when its HTTP side is unresponsive:
    # a hung server still holds RAM, and _unload_other_script_models relies on
    # this kill for the mutual-exclusion guarantee. Gating on the ready check
    # here would leak exactly the zombie it exists to evict.
    process = _get_process(model_id)
    if process is not None:
        _terminate_process(process)
    else:
        # No tracked handle — discover the server by its listening port and
        # attempt termination (AC-102).
        port = urlparse(entry['ready_url']).port
        pid = _find_listening_pid(port)
        if pid is not None and not _pid_is_model_server(pid, entry):
            return {'status': 'error', 'message': f'{model_id} port {port} is held by an unidentified process (pid {pid}); refusing to terminate'}
        if pid is not None:
            _terminate_pid(pid)

    # Re-check reachability after termination attempt.
    port = urlparse(entry['ready_url']).port
    if _responds_ready(entry['ready_url']) or _find_listening_pid(port) is not None:
        return {'status': 'error', 'message': f'{model_id} still reachable'}

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
