# Extending

NZT-48 has three extension points: agents, monitors, and integrations.

## Adding an agent

An agent is a system prompt (a `.txt` file) plus an entry in `agents.py`. The system prompt is the hard part — the wiring is five lines.

**1. Write the prompt**

Create `prompts/agents/myagent.txt`:

```
You are the {USER_NAME} {ROLE} agent. Your job is to ...

Output format (JSON envelope — do not deviate):
{
  "reply": "what to send to Telegram",
  "vault_writes": [{"path": "relative/path.md", "content": "..."}],
  "action": null
}

Current context:
{HOT_CACHE}
```

Available template variables: `{USER_NAME}`, `{USER_GOAL}`, `{USER_BUSINESS}`, `{HOT_CACHE}`, `{VAULT_CONTEXT}`.

Private prompt override: place the file at `private/agents/myagent.txt` — it shadows the public version automatically.

**2. Register in router.py**

Add a new intent constant and a classification rule. The router uses a two-stage process: fast regex rules first, then a local model classifier for anything that doesn't match:

```python
# router.py
MYAGENT = "MYAGENT"

RULES = [
    ...
    (re.compile(r'\b(my trigger word|another phrase)\b', re.I), MYAGENT),
]
```

**3. Wire in agents.py**

```python
from router import MYAGENT

AGENT_MAP = {
    ...
    MYAGENT: "myagent",   # maps intent → prompt filename (no .txt)
}
```

That is the entire wiring. `run_agent()` in `agents.py` loads the prompt, injects context, calls Claude Code, parses the envelope, and routes `vault_writes` through the write gate.

## Adding a monitor

A monitor is an async function that runs on a timer inside `monitors.py`. It fires every `monitoring.interval_minutes` minutes within the configured window.

```python
# monitors.py

async def my_monitor(bot, config, state):
    """Check something and nudge if needed."""
    # read from state or vault
    last_check = state.get_kv("my_monitor_last") or 0
    if time.time() - last_check < 3600:
        return   # too soon

    # do the check
    if something_needs_attention():
        await bot.send_message(
            config["telegram"]["chat_id"],
            "⚠ Something needs attention"
        )
        state.set_kv("my_monitor_last", time.time())

# register it
MONITORS = [
    deadline_monitor,
    pipeline_monitor,
    my_monitor,       # ← add here
]
```

Monitors respect `monitoring.max_per_day` — the count is shared across all monitors. Heavy checks should also track their own last-run timestamp in `state.db` to avoid firing on every tick.

## Adding a Composio integration

If the service is already connected at `app.composio.dev`, add it to `tools/composio_tools.py`:

```python
from composio_tools import client, gate

def my_tool_read(param: str) -> dict:
    """Read-only — runs silently."""
    result = client.get_entity("default").execute_action(
        action="MY_SERVICE_ACTION",
        params={"param": param},
    )
    return result.get("data", {})

def my_tool_write(content: str) -> dict:
    """Write action — goes through approval gate."""
    return gate(
        action="my_service_write",
        payload={"content": content},
        preview=f"Create entry: {content[:80]}",
    )
```

Then call it from the relevant agent's `action` field in the envelope:

```json
{
  "reply": "Done — here's what I'll send:",
  "vault_writes": [],
  "action": { "tool": "my_tool_write", "args": { "content": "..." } }
}
```

`agents.py` dispatches `action.tool` → the matching function in `tools/composio_tools.py`. Write actions return to the approval gate before executing.

## Private overlay

The cleanest extension pattern is the private overlay. Add anything to `private/euan.yml` that you don't want committed — extra config keys, module toggles, API keys. Add agent prompts to `private/agents/<name>.txt` to override public prompts without touching the repo.

This is how the "Pro" tier works: it's just a richer `private/` folder.
