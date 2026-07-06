# Security

## Threat model

NZT-48 runs on your own machine with your own keys. The surfaces it is designed to defend:

- **Prompt injection** via inbound content (web, PDF, forwarded messages)
- **Vault poisoning** — an attacker-controlled write reaching `HOT-CACHE.md` or protected profile files
- **Path traversal** — a crafted filename escaping the vault root
- **Credential leakage** — API keys appearing in logs or error text
- **Unauthorised access** — the bot responding to anyone other than you

## Inbound sanitiser

Every message that arrives from outside Telegram (web search snippets, PDF text, screenshots) is stripped of common injection patterns before it reaches the model. The sanitiser runs in `router.py` as a pre-processing step on the raw content, not on the model's output.

## Untrusted content gate

Any input that did not originate from your own Telegram account is marked `untrusted=True` at ingest and carries that flag through to the write call. Untrusted writes are always staged for approval — there is no config key that disables this. The flag is set at the source, not inferred from content.

This was retrofitted after a live red-team: a web search result containing an embedded instruction reached `HOT-CACHE.md` in an earlier version. The fix is in the commit history (`vault/04-PROJECTS/nzt-48-fable-audit.md`).

## Vault write gate

```
  write requested
       ↓
  path resolved → rejects ../ traversal and absolute paths
       ↓
  protected prefix? ──yes──→ stage write, send Telegram confirmation
  untrusted source? ──yes──→ stage write, send Telegram confirmation
       ↓ (both no)
  write executes
```

Confirmation messages show the full target path and a diff of what will change. Approval requires a reply of `yes`; anything else cancels. Auto-cancels after 5 minutes.

## Allowlist

The bot only responds to Telegram IDs in `telegram.allowed_ids`. An empty list answers nobody — there is no open/public mode. Set this in `private/euan.yml`:

```yaml
telegram:
  allowed_ids: [123456789]
```

Find your ID by messaging [@userinfobot](https://t.me/userinfobot).

## API key handling

- All secrets live in `.env` (0600, gitignored) or `private/*.yml` (gitignored)
- `cc_client.py` strips `ANTHROPIC_API_KEY` from the child environment before spawning Claude Code — so there is no per-token billing path even if something went wrong
- `requests` exception text can embed URLs containing tokens; redaction happens at the print site, not by catching exceptions

## Path traversal

`vault_write()` resolves the requested path against the vault root and rejects anything that resolves outside it. Absolute paths are also rejected. The check runs before the protected-prefix gate, so a traversal attempt never reaches the approval flow.

## Secrets in git

The `.gitignore` excludes:

```
.env
private/
config.yml          # example only; your real config is not committed
state.db
logs/
```

If you fork and add secrets: rotate them. Do not rely on git history rewrites.
