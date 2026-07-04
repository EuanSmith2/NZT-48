"""External-app integrations: Composio connect-apps (500+ apps) and the
Canva MCP. Both are OFF until configured — flip the flags in private/local.yml
after the one-time setup each describes."""
import cc_client
from config import CANVA_ENABLED, COMPOSIO_ENABLED

COMPOSIO_SETUP = (
    "Composio isn't wired up yet. One-time setup (in Claude Code, not here):\n"
    "1. /plugin marketplace add ComposioHQ/awesome-claude-skills\n"
    "2. install the connect-apps plugin, run its auth flow (browser OAuth)\n"
    "3. flip integrations.composio.enabled: true in private/local.yml\n"
    "then /connect gmail (or slack, notion, github…) works from here."
)

CANVA_SETUP = (
    "Canva MCP isn't wired up yet. One-time setup:\n"
    "1. add Anthropic's Canva MCP server to the claude CLI (user scope):\n"
    "   claude mcp add canva <server command from anthropic-quickstarts>\n"
    "2. approve the Canva OAuth in the browser once\n"
    "3. flip integrations.canva.enabled: true in private/local.yml\n"
    "then /mockup <brief> works from here."
)

MOCKUP_SYSTEM = """You are the Design Agent. Use the Canva tools to create
what's asked — client site mockups, social posts, proposal covers.
Brand: dark terminal aesthetic — near-black background, #00ff66 accent,
monospace type — unless the brief names the CLIENT's brand, then use theirs.
Keep layouts clean and confident; no clip-art energy. When done, report the
design title + link. Never publish or share a design externally — create only."""


def connect(app: str) -> str:
    if not COMPOSIO_ENABLED:
        return COMPOSIO_SETUP
    # OAuth flows are interactive — this belongs in an interactive session
    return cc_client.queue_task(
        f"Connect '{app or 'a new app'}' via the Composio connect-apps skill "
        f"and confirm the auth works", "composio oauth is interactive")


def mockup(brief: str) -> str:
    if not CANVA_ENABLED:
        return CANVA_SETUP
    return cc_client.run(f"TASK: {brief}", system=MOCKUP_SYSTEM, model="sonnet",
                         allowed_tools="mcp__canva__*,Read", max_turns=25,
                         timeout=420)
