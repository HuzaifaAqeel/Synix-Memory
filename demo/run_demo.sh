#!/usr/bin/env bash
# run_demo.sh — Synix-Memory offline demo.
# Builds a real memory pipeline (sessions -> episodes -> monthly rollups ->
# core memory -> search index) against the local stub LLM server.
set -euo pipefail

# Sandbox quirk: some environments ship a no_proxy containing IPv6 entries
# like [::1] which httpx cannot parse — restrict to plain hostnames.
export no_proxy="localhost,127.0.0.1"
export NO_PROXY="$no_proxy"
# Offline demo: don't attempt to download the fastembed model — the pipeline
# falls back to keyword search, which is all this demo needs. Remove this to
# enable semantic search with a cached model.
export HF_HUB_OFFLINE=1

DEMO_DIR="$(cd "$(dirname "$0")" && pwd)"
WORK="$(mktemp -d)"
PORT=8765

echo "== 1. starting stub LLM server =="
python3 "$DEMO_DIR/stub_server.py" "$PORT" > "$WORK/stub.log" 2>&1 &
STUB_PID=$!
trap 'kill $STUB_PID 2>/dev/null' EXIT
sleep 1

export SYNIX_LLM_PROVIDER=openai-compatible
export SYNIX_LLM_BASE_URL="http://127.0.0.1:$PORT/v1"
export OPENAI_API_KEY=demo
export SYNIX_API_KEY=demo

echo "== 2. scaffolding project from the agent-memory template =="
cd "$WORK"
synix init my-agent --template 08-agent-memory > /dev/null
cd "$WORK/my-agent"
cp "$DEMO_DIR/sessions/"*.md sources/

echo "== 3. building the memory pipeline =="
synix build --plain

echo "== 4. releasing =="
synix release HEAD --to local

echo "== 5. searching memory =="
synix search "database migrations" --release local
echo
synix search "slow queries" --release local

echo
echo "[demo] work dir kept at: $WORK/my-agent"
kill $STUB_PID 2>/dev/null
trap - EXIT
