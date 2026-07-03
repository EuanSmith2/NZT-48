"""Generate + install the NZT-48 Apple Terminal profile.
Run once: python setup_terminal.py
Then in Terminal → Settings → Profiles → select NZT-48 → Default.
"""
import base64
import io
import os
import plistlib
import subprocess
import tempfile
from pathlib import Path


def _nscolor(r: float, g: float, b: float, a: float = 1.0) -> bytes:
    """Return NSKeyedArchiver binary plist for an NSColor (calibrated RGB)."""
    data = {
        "$archiver": "NSKeyedArchiver",
        "$version": 100000,
        "$top": {"root": plistlib.UID(1)},
        "$objects": [
            "$null",
            {
                "$class": plistlib.UID(2),
                "NSColorSpace": 2,          # NSCalibratedRGBColorSpace
                "NSRGB": (f"{r} {g} {b}").encode() + b"\x00",
            },
            {
                "$classname": "NSColor",
                "$classes": ["NSColor", "NSObject"],
            },
        ],
    }
    buf = io.BytesIO()
    plistlib.dump(data, buf, fmt=plistlib.FMT_BINARY)
    return buf.getvalue()


def _font_data(name: str = "MenloRegular", size: float = 13.0) -> bytes:
    """Return NSKeyedArchiver binary plist for an NSFont."""
    # NSFont stores: NSName (postscript name), NSSize, NSfFlags
    data = {
        "$archiver": "NSKeyedArchiver",
        "$version": 100000,
        "$top": {"root": plistlib.UID(1)},
        "$objects": [
            "$null",
            {
                "$class": plistlib.UID(2),
                "NSName": name,
                "NSSize": size,
                "NSfFlags": 16,
            },
            {
                "$classname": "NSFont",
                "$classes": ["NSFont", "NSObject"],
            },
        ],
    }
    buf = io.BytesIO()
    plistlib.dump(data, buf, fmt=plistlib.FMT_BINARY)
    return buf.getvalue()


def build_profile() -> dict:
    black  = _nscolor(0.039, 0.039, 0.039)   # #0a0a0a background
    green  = _nscolor(0.0, 1.0, 0.4)          # #00ff66
    white  = _nscolor(0.85, 0.85, 0.85)       # selection
    yellow = _nscolor(0.94, 0.71, 0.16)       # #f0b429 ANSI yellow
    red    = _nscolor(1.0, 0.37, 0.34)        # #ff5f57 ANSI red
    blue   = _nscolor(0.09, 0.46, 0.82)       # ANSI blue
    cyan   = _nscolor(0.12, 0.76, 0.67)       # ANSI cyan
    mag    = _nscolor(0.67, 0.37, 0.82)       # ANSI magenta
    d_grey = _nscolor(0.2, 0.2, 0.2)          # ANSI bright black
    font   = _font_data("Menlo-Regular", 13.0)

    return {
        "name": "NZT-48",
        "type": "Window Settings",
        "BackgroundColor":              black,
        "TextColor":                    green,
        "BoldTextColor":                green,
        "CursorColor":                  green,
        "SelectionColor":               white,
        "ANSIBlackColor":               _nscolor(0.1, 0.1, 0.1),
        "ANSIRedColor":                 red,
        "ANSIGreenColor":               green,
        "ANSIYellowColor":              yellow,
        "ANSIBlueColor":                blue,
        "ANSIMagentaColor":             mag,
        "ANSICyanColor":                cyan,
        "ANSIWhiteColor":               _nscolor(0.7, 0.7, 0.7),
        "ANSIBrightBlackColor":         d_grey,
        "ANSIBrightRedColor":           _nscolor(1.0, 0.5, 0.5),
        "ANSIBrightGreenColor":         _nscolor(0.0, 1.0, 0.5),
        "ANSIBrightYellowColor":        _nscolor(1.0, 0.85, 0.4),
        "ANSIBrightBlueColor":          _nscolor(0.2, 0.6, 1.0),
        "ANSIBrightMagentaColor":       _nscolor(0.8, 0.5, 1.0),
        "ANSIBrightCyanColor":          _nscolor(0.0, 0.9, 0.8),
        "ANSIBrightWhiteColor":         _nscolor(0.95, 0.95, 0.95),
        "Font":                         font,
        "FontAntialias":                True,
        "FontWidthSpacing":             1.0,
        "CursorType":                   0,         # block cursor
        "CursorBlink":                  False,
        "columnCount":                  220,
        "rowCount":                     50,
        "scrollbackLines":              10000,
        "UseBoldFonts":                 True,
        "UseBrightBold":                True,
        "useOptionAsMetaKey":           True,
        "ShowActiveProcessInTitle":     False,
        "ShowActiveProcessArgumentsInTitle": False,
        "ShowCommandKeyInTitle":        False,
        "ShowDimensionsInTitle":        False,
        "ShowShellCommandInTitle":      False,
        "ShowTTYNameInTitle":           False,
        "ShowWindowSettingsNameInTitle": False,
        "BackgroundAlphaInactive":      1.0,
        "BackgroundBlur":               0.0,
    }


def install():
    profile = build_profile()
    out_path = Path(__file__).parent / "nzt48.terminal"
    with open(out_path, "wb") as f:
        plistlib.dump(profile, f, fmt=plistlib.FMT_XML)
    print(f"profile written → {out_path}")

    # Open it — Terminal.app will offer to import it
    subprocess.run(["open", str(out_path)], check=True)
    print(
        "\nTerminal opened the profile.\n"
        "Go to: Settings → Profiles → select NZT-48 → click Default\n"
        "Then: Shell → Use Settings as Default\n"
        "\nTip: set your prompt too:\n"
        '  export PS1="\\[\\033[38;5;46m\\]\\u@\\h \\[\\033[38;5;35m\\]\\W\\[\\033[0m\\] % "\n'
        "Add that to ~/.zshrc"
    )


if __name__ == "__main__":
    install()
