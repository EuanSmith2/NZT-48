"""Video agent — natural-language brief → Remotion composition → mp4.

Template project lives at private/remotion/ (gitignored). One-time setup:
    cd private/remotion && npm install          (~1 min, ~400MB node_modules)

Flow: cc (with Write scoped to the remotion project) rewrites src/Video.tsx
from the brief + vault data it reads, then `npx remotion render` produces
out/video.mp4. Vertical 1080x1920, 30fps — TikTok/Reels native.
"""
import subprocess
from pathlib import Path

import cc_client
from config import NZT

PROJECT = NZT / "private" / "remotion"

SYSTEM = """You are the Video Agent. You write ONE Remotion composition from
the brief, editing ONLY src/Video.tsx in the current project.

CONSTRAINTS:
- Keep the existing export name (Video) and props signature — Root.tsx
  registers it; do not touch any other file.
- 1080x1920 vertical, 30fps, duration set via the durationInFrames constant
  already exported from Video.tsx (change its value to fit the content).
- Dark terminal aesthetic unless the brief says otherwise: #0a0a0a
  background, #00ff66 accents, monospace type, sharp cuts over slow fades.
- Text must be readable on a phone: min ~64px, high contrast, one idea per
  beat. Numbers get the emphasis frames.
- Use only remotion core (interpolate, spring, Sequence, AbsoluteFill) —
  no new npm deps.
- If the brief references vault data (streaks, pipeline), read the files and
  hard-code the real numbers into the composition.
When done, reply with one line: what the video shows and its duration."""


def setup_ok() -> str | None:
    if not PROJECT.exists():
        return "remotion template missing — private/remotion/ was not created"
    if not (PROJECT / "node_modules").exists():
        return ("remotion not installed yet — run once:\n"
                f"cd {PROJECT} && npm install")
    return None


def make(brief: str, timeout: int = 900) -> str:
    err = setup_ok()
    if err:
        return err
    result = cc_client.run(
        f"BRIEF: {brief}\n\nProject root: {PROJECT}", system=SYSTEM,
        model="sonnet", allowed_tools="Read,Glob,Grep,Write,Edit",
        max_turns=20, timeout=300, cwd=str(PROJECT))
    render = subprocess.run(
        ["npx", "remotion", "render", "Main", "out/video.mp4"],
        cwd=PROJECT, capture_output=True, text=True, timeout=timeout)
    if render.returncode != 0:
        return f"composition written but render failed:\n{render.stderr[-400:]}"
    return f"{result}\n\n🎬 rendered: {PROJECT / 'out/video.mp4'}"
