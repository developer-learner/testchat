#!/bin/bash
# testchat script-model launcher: deepseek-v4-flash-0731 (unsloth Q2_K_XL)
# Serves the OpenAI-compatible protocol (GET /v1/models, POST /v1/chat/completions).
exec /opt/homebrew/bin/llama-server \
  --host 127.0.0.1 \
  --port 8101 \
  --ctx-size 65536 \
  --model /Users/arc.elixir/.lmstudio/models/unsloth/DeepSeek-V4-Flash-0731-GGUF/DeepSeek-V4-Flash-0731-UD-Q2_K_XL-00001-of-00003.gguf