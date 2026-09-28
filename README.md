# Synix-Memory — Programmable Memory Pipelines for AI Agents

Every agent-memory tool gives you one flat bucket: same storage, same rules,
same lifecycle. **Synix lets you program how memory works** — define the
layers, write the prompts, control the lifecycle. Change your mind later?
Rebuild incrementally; only new inputs re-process.

## The pipeline

```
sources/  →  episodes  →  monthly rollups  →  core memory  →  search index
 (raw)       (1:1 LLM)     (N:M synthesis)      (N:1 doc)
```

1. **Sources** — raw data parsed from `./sources/` (chat exports, transcripts, docs).
2. **Episodes** — each source gets an LLM-generated summary (1:1).
3. **Rollups** — episodes grouped (by month, or topically) and synthesized (N:M).
4. **Core memory** — all rollups compressed into one evolving document (N:1).
5. **Search index** — everything indexed for full-text / semantic / hybrid search,
   with **full provenance**: every insight traces back to the session that produced it.

## 60-second start

```bash
pip install -e .
cp .env.example .env          # add your API key
synix init my-project          # scaffold from the agent-memory template
cd my-project
# drop session transcripts into ./sources/
synix build
synix release HEAD --to local
synix search "deployment process" --release local
```

Works with **Anthropic**, **OpenAI**, **DeepSeek**, or any **OpenAI-compatible**
endpoint (Ollama, vLLM, LM Studio) — set `SYNIX_LLM_PROVIDER=openai-compatible`
and `SYNIX_LLM_BASE_URL`. Keys resolve from env vars; nothing is hardcoded.

## Your agent reads the output at runtime

```python
import synix

project = synix.open_project("./my-project")
mem = project.release("local")

results = mem.search("return policy", limit=5)
for r in results:
    print(f"[{r.layer}] {r.label} ({r.score:.2f})")

context = mem.flat_file("context-doc")   # inject into your system prompt
```

Synix runs offline; your agent reads the materialized release. Decoupled by design.

## Customizing

Open `pipeline.py` — it's a DAG of transforms you define in Python. Swap
`MonthlyRollup` for `TopicalRollup`, change prompts, add layers, set per-layer
`llm_config` overrides (e.g. cheap model for episodes, strong model for core
memory). `synix build` only re-processes what changed.

## Offline demo (no API key)

```bash
bash demo/run_demo.sh
```

Spins up a local OpenAI-compatible stub, scaffolds a project from the bundled
`08-agent-memory` template, builds the full pipeline on two sample sessions,
releases, and runs searches — end to end.

## Layout

```
src/synix/            # the package: CLI, build engine, search, SDK, MCP/server
  templates/          # 9 bundled project templates (08-agent-memory is default)
  build/prompts/      # the memory-synthesis prompts (episode/rollup/core)
demo/
  stub_server.py      # tiny OpenAI-compatible stub for the offline demo
  run_demo.sh         # end-to-end demo: init -> build -> release -> search
  sessions/           # two sample session transcripts
```

## License

MIT — see `LICENSE`.
