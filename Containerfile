FROM python:3.12-slim

# System dependencies. D-53: no OpenCode here — nothing in this container
# calls an LLM anymore (that happens on the host via scripts/llm-call.sh
# before the container ever starts); this image runs pytest/smoke_check
# against untrusted generated code only, hence --network none in
# sandbox-run.sh and no curl/agent-runtime install here either.
RUN apt-get update && apt-get install -y --no-install-recommends \
    git ca-certificates tar \
    && rm -rf /var/lib/apt/lists/*

# Pytest toolchain + app deps (always installed). pytest-xdist: suite
# parallelization (-n auto --dist=loadfile); the conftest port allocator is
# per-process so each worker self-allocates loopback ports without collision.
RUN pip install --no-cache-dir \
    pytest pytest-json-report pytest-asyncio pytest-cov pytest-xdist ruff mypy respx \
    fastapi uvicorn httpx pydantic

# Browser oracle (D-58): chromium + playwright baked at BUILD time — the
# sandbox runs --network none. Spike-proven on aarch64 (2026-07-07). HOME is
# tmpfs at run time, so browsers install to a fixed root-owned path.
RUN pip install --no-cache-dir playwright==1.61.0 pytest-playwright==0.8.0 && \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright playwright install --with-deps chromium
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Project deps. Copy ONLY the dependency manifest: COPY . would retain source,
# local env files, pipeline state, and captures in an earlier image layer even
# if a later RUN removed the directory.
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && \
    rm -f /tmp/requirements.txt

# Non-root user
RUN useradd -m -u 1000 agent
USER agent
WORKDIR /work
