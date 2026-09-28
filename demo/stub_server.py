#!/usr/bin/env python3
"""
stub_server.py — tiny OpenAI-compatible stub for the Synix offline demo.

Serves:
  POST /v1/chat/completions  -> canned episode/rollup/core-memory responses,
                               chosen by matching the prompt template text
  POST /v1/messages           -> same canned responses in Anthropic Messages
                               API shape (the demo pipeline uses the
                               anthropic provider by default)
  POST /v1/embeddings         -> deterministic keyword embeddings

This is only for the demo. Point Synix at a real provider (Anthropic, OpenAI,
or any OpenAI-compatible endpoint) for production use.
"""
import hashlib
import json
import re
from http.server import BaseHTTPRequestHandler, HTTPServer

BUCKETS = {
    "deploy": ["deploy", "ci/cd", "pipeline", "docker", "kubernetes", "migration", "staging"],
    "database": ["postgres", "database", "query", "index", "sql", "alembic", "slow query"],
}


def topic_of(text: str) -> str:
    t = text.lower()
    scores = {k: sum(t.count(w) for w in words) for k, words in BUCKETS.items()}
    return max(scores, key=scores.get)


def embed(text: str):
    t = text.lower()
    vec = [0.0] * 16
    for i, (name, words) in enumerate(BUCKETS.items()):
        s = sum(t.count(w) for w in words)
        vec[i * 2] = float(s)
        vec[i * 2 + 1] = 1.0 if s else 0.0
    h = int(hashlib.md5(text.encode()).hexdigest(), 16)
    for i in range(4, 16):
        vec[i] += ((h >> i) % 97) / 97.0 * 0.05
    return vec


def episode_summary(transcript: str) -> str:
    topic = topic_of(transcript)
    first_user = re.search(r"\*\*User:\*\*\s*(.+)", transcript)
    q = first_user.group(1).strip()[:120] if first_user else "the session"
    return (
        f"## Episode summary\n\n"
        f"Main topic: {topic}. The user asked: \"{q}\". "
        f"The assistant provided a detailed, actionable plan covering tooling choices, "
        f"safeguards, and rollout sequencing.\n\n"
        f"**Key decisions:** adopted the recommended approach with staged rollout; "
        f"added safeguards before production changes.\n\n"
        f"**Action items:** implement the plan step by step; add monitoring and "
        f"notifications before the first production run.\n\n"
        f"**Tone:** practical and collaborative; user is building real infrastructure."
    )


def monthly_rollup(episodes: str) -> str:
    return (
        "## Monthly rollup\n\n"
        "**Major themes:** infrastructure automation and data-layer reliability. "
        "The user is standing up deployment pipelines and hardening the database layer.\n\n"
        "**Evolution:** thinking moved from 'what tool should I use' to 'how do I make "
        "this safe at 3am' — a shift toward operational maturity.\n\n"
        "**Key decisions:** staged rollouts with approval gates; migration safety "
        "checks; secrets kept out of container images.\n\n"
        "**Facts & preferences:** small team (3 engineers), Python/FastAPI + "
        "PostgreSQL stack, prefers simple solutions over premature infrastructure."
    )


def core_memory(rollups: str) -> str:
    return (
        "# Core memory\n\n"
        "## Identity\n"
        "Backend engineer on a 3-person team, building a Python/FastAPI + PostgreSQL service.\n\n"
        "## Current focus\n"
        "Standing up CI/CD with safe database migrations; hardening production reliability.\n\n"
        "## Preferences & style\n"
        "- Prefers simple, boring technology over premature infrastructure.\n"
        "- Wants safeguards (approval gates, timeouts, downgrades) before production changes.\n"
        "- Communicates in practical, implementation-focused terms.\n\n"
        "## Standing constraints\n"
        "- Never put secrets in container images.\n"
        "- Every migration needs a downgrade path.\n"
        "- Staging must mirror production before any prod deploy."
    )


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, obj):
        body = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _chat_content(self, prompt: str) -> str:
        if "summarizing a conversation between a user and an AI assistant" in prompt:
            m = re.search(r"<conversation>(.*?)</conversation>", prompt, re.S)
            return episode_summary(m.group(1) if m else prompt)
        elif "synthesizing multiple conversation summaries" in prompt:
            return monthly_rollup(prompt)
        elif "core memory document for an AI agent" in prompt:
            return core_memory(prompt)
        return "Summary: " + prompt[:200]

    @staticmethod
    def _message_text(messages) -> str:
        if not messages:
            return ""
        content = messages[-1].get("content", "")
        if isinstance(content, list):
            return " ".join(b.get("text", "") for b in content if isinstance(b, dict))
        return content

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        payload = json.loads(self.rfile.read(length) or b"{}")

        if self.path.endswith("/chat/completions"):
            prompt = self._message_text(payload.get("messages", []))
            content = self._chat_content(prompt)
            self._json({
                "id": "stub-1", "object": "chat.completion",
                "choices": [{"index": 0, "message": {"role": "assistant", "content": content},
                             "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
            })
        elif self.path.endswith("/messages"):
            # Anthropic Messages API shape
            prompt = self._message_text(payload.get("messages", []))
            system = payload.get("system", "")
            if isinstance(system, list):
                system = " ".join(b.get("text", "") for b in system if isinstance(b, dict))
            content = self._chat_content(system + "\n" + prompt)
            self._json({
                "id": "stub-1", "type": "message", "role": "assistant",
                "model": payload.get("model", "stub"),
                "content": [{"type": "text", "text": content}],
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 10, "output_tokens": 10},
            })
        elif self.path.endswith("/embeddings"):
            texts = payload.get("input", [])
            if isinstance(texts, str):
                texts = [texts]
            self._json({
                "object": "list",
                "data": [{"object": "embedding", "index": i, "embedding": embed(t)}
                         for i, t in enumerate(texts)],
                "usage": {"prompt_tokens": 1, "total_tokens": 1},
            })
        else:
            self.send_response(404)
            self.end_headers()


if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    srv = HTTPServer(("127.0.0.1", port), Handler)
    print(f"[stub] OpenAI-compatible stub on http://127.0.0.1:{port}/v1", flush=True)
    srv.serve_forever()
