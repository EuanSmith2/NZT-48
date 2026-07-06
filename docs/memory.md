# Memory

NZT-48 memory has three speeds: always-on, on-demand, and write-gated. Every agent response uses all three.

## Architecture

```
  message in
      ↓
  hot cache ────────────────────────────────→  HOT-CACHE.md (≤ 1,200 chars)
  (injected into every prompt, mtime-cached)   always-on; never searched

  warm retrieval ───────────────────────────→  rest of vault
  (scored per query — BM25 + path weighting)   pulled when the intent needs it

  vault write ──────────────────────────────→  approval gate
  (any write to a protected prefix)            tap required before commit
```

## Hot cache

`HOT-CACHE.md` is the system's working memory. It is injected verbatim into every agent prompt before any vault search runs. It should contain:

- Your current top priority (one sentence)
- Active deadlines
- Anything the system should never forget between sessions

Keep it under 1,200 characters. The briefing agent rewrites it each morning after the brief runs. Edits from outside — web search results, forwarded messages — are blocked by the write gate regardless of who requests them.

## Warm retrieval

On every non-trivial message, `memory.py` scores the vault for relevance to the current query using a pure-Python scorer (no vector DB, no embedding API):

- **BM25** term frequency over markdown content
- **Path weighting** — `intent_folders` in `config.yml` boosts folders relevant to the current intent (BUSINESS → `04-PROJECTS`, `09-FINANCE`; PREP → `03-PEOPLE`, `08-EVENTS`)
- **Recency decay** — recent files score higher on equal term match
- Top-k files are appended to the agent context after the hot cache

Configure retrieval scope in `config.yml`:

```yaml
vault:
  intent_folders:
    BUSINESS: ["04-PROJECTS", "09-FINANCE"]
    PREP:     ["03-PEOPLE", "08-EVENTS", "04-PROJECTS"]
    LEARNING: ["06-LEARNING"]
    RESEARCH: ["05-KNOWLEDGE"]
```

## Write gate

All vault writes go through `vault_write()` in `memory.py`. The function:

1. Resolves the path and rejects `../` traversal and absolute paths
2. Checks if the target is under `protected_prefixes` in config
3. If protected (or if the write originates from untrusted content), stages the write and sends a Telegram confirmation request
4. Executes only on explicit approval; auto-cancels after 5 minutes of silence

```
  agent wants to write → protected? ──yes──→ stage + ask Euan
                                    ──no──→  untrusted source? ──yes──→ stage + ask
                                                               ──no──→  write directly
```

## Untrusted content

Any content that arrives from outside your Telegram account — a PDF, a screenshot, a web-search snippet, a forwarded message — is marked `untrusted=True` in the agent call. Untrusted writes are always gated, regardless of the destination path. This is not configurable.

The rule closed a real prompt-injection hole: a web search result containing a carefully worded instruction could previously cause a write to `HOT-CACHE.md`. The fix required no NLP — just tracking provenance from ingest to write.

## Vault layout

The scaffolded vault has this structure:

```
vault/
  00-META/
    HOT-CACHE.md       ← always in prompt
    PRIORITIES.md      ← injected alongside hot cache
  01-PROFILE/          ← protected
  02-GOALS/            ← protected
  03-PEOPLE/           ← CRM cards
  04-PROJECTS/
  05-KNOWLEDGE/
  06-LEARNING/
  08-EVENTS/
  09-FINANCE/
```

Any folder structure works as long as `config.yml` maps your paths to the right intent keys.
