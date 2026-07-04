"""First-run vault scaffold — every file a fresh clone needs so finance,
monitors, briefing and memory don't run on an empty vault.

Neutral placeholders only: nothing that fires fake nudges (target_clients: 0
keeps every business monitor silent until real data or the /setup wizard
turns it on). The pipeline schema is STRICT — section names, the 12 Prospects
columns and Snapshot/Assumptions keys are exactly what finance.py parses.

Idempotent: creates missing files only, never overwrites.
"""
from pathlib import Path

from config import (BUSINESS_ENABLED, LEARNING_ENABLED,
                    LEARNING_PROGRESS_FILE, PIPELINE_FILE)

PIPELINE_TEMPLATE = """# Web Business Pipeline

## Snapshot
target_clients: 0
clients_won: 0
income_received_eur: 0
mrr_eur: 0
deadline: 2026-12-31

## Assumptions
call_to_conversation: 0.40
conversation_to_proposal: 0.25
proposal_to_won: 0.40
avg_deal_eur: 500

## Prospects
| Name | Business | Area | Phone | Website | Score | Tier | Date | LastContact | Channel | Status | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|

## Income Outstanding
| Client | Amount | Sent | Due | Status | Days overdue |
|---|---|---|---|---|---|

## Income Received
| Date | Client | Amount | Project | Method |
|---|---|---|---|---|

## Activity Log
"""

LEARNING_TEMPLATE = """# Learning — Progress

## Active
- Platform:
- Current module:
- Streak: 0

## SR Schedule
| concept | last_seen | interval_days | next_due |
|---|---|---|---|
"""

BASE_FILES: dict[str, str] = {
    "00-META/HOT-CACHE.md":
        "# Hot Cache\nAlways-loaded context. Keep it short (max ~600 tokens).\n\n"
        "- (empty — fill with the state you want always present)\n",
    "00-META/PRIORITIES.md":
        "# Priorities\nWhat matters right now. The brief reads the top 3.\n\n"
        "- Set your priorities here\n",
    "00-META/LOG.md": "# Log\n",
    "00-META/INBOX/unfiled.md":
        "# Unfiled\nAmbiguous captures land here until you sort them.\n",
    "00-META/daily-briefings/.gitkeep": "",
    "01-PROFILE/profile.md":
        "# Profile\n- Name:\n- What I do:\n- How I introduce myself to someone new:\n",
    "02-GOALS/goals.md": "# Goals\n\n## Current\n- (main goal + deadline)\n",
    "03-PEOPLE/INDEX.md":
        "# People — Index\n| Name | File | Last contact |\n|---|---|---|\n",
    "04-PROJECTS/INDEX.md":
        "# Projects — Index\n| Project | Status | File |\n|---|---|---|\n",
    "05-KNOWLEDGE/.gitkeep": "",
    "07-CONTENT/BRAND-VOICE.md":
        "# Brand Voice\nHow I write. Short sentences, concrete. Nothing corporate.\n",
    "08-EVENTS/prep/.gitkeep": "",
}


def ensure_vault(vault: Path) -> list[str]:
    """Create any missing scaffold files. Returns the list created."""
    created = []
    files = dict(BASE_FILES)
    if BUSINESS_ENABLED:
        files[PIPELINE_FILE] = PIPELINE_TEMPLATE
    if LEARNING_ENABLED:
        files[LEARNING_PROGRESS_FILE] = LEARNING_TEMPLATE
    for rel, content in files.items():
        p = vault / rel
        if p.exists():
            continue
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        created.append(rel)
    return created


if __name__ == "__main__":
    from config import VAULT
    made = ensure_vault(VAULT)
    print(f"created {len(made)} file(s)" + (":\n  " + "\n  ".join(made) if made else " — vault already complete"))
