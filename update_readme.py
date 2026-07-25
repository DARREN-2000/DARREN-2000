"""
update_readme.py
================
Programmatically refreshes the GitHub profile README with the latest
role / project / location information.

Designed to run both:
  * locally on Windows (path auto-resolved relative to this script)
  * inside a CI runner (Linux / macOS / Windows) via GitHub Actions

Usage
-----
    python update_readme.py            # apply updates, exit 0 on success
    python update_readme.py --check    # dry-run: report drift, exit 1 if any patch would change content

Exit codes
----------
    0   all replacements applied successfully (or no changes needed in --check)
    1   one or more regex/replacement patterns failed to match
    2   IO error reading / writing the README
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Callable

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Resolve README path relative to this script so it works anywhere.
README_PATH: Path = Path(__file__).resolve().parent / "README.md"


# ---------------------------------------------------------------------------
# Patch definitions
# Each entry: (description, callable that returns (new_content, changed?))
# Using callables so we can compose / order patches flexibly.
# ---------------------------------------------------------------------------

PatchFn = Callable[[str], tuple[str, bool]]


def _regex_replace(label: str, pattern: str, replacement: str, flags: int = 0) -> PatchFn:
    """Build a patch that performs a regex substitution.

    Idempotent: if the pattern doesn't match but the replacement is already
    present in the content, this is treated as success (already applied).
    """

    def patch(content: str) -> tuple[str, bool]:
        new_content, n = re.subn(pattern, replacement, content, flags=flags)
        if n == 0:
            if replacement in content:
                print(f"[OK]   {label}: already applied (idempotent)")
                return content, True
            print(f"[WARN] pattern did not match: {label}", file=sys.stderr)
            return content, False
        print(f"[OK]   {label}: {n} replacement(s)")
        return new_content, True

    return patch


def _literal_replace(label: str, old: str, new: str) -> PatchFn:
    """Build a patch that performs a literal substitution.

    Idempotent: if the old text isn't found but the new text is already
    present, this is treated as success.
    """

    def patch(content: str) -> tuple[str, bool]:
        if old not in content:
            if new in content:
                print(f"[OK]   {label}: already applied (idempotent)")
                return content, True
            print(f"[WARN] literal not found: {label}", file=sys.stderr)
            return content, False
        print(f"[OK]   {label}: replaced")
        return content.replace(old, new), True

    return patch


# ---------------------------------------------------------------------------
# Patches to apply, in order
# ---------------------------------------------------------------------------

PATCHES: list[PatchFn] = [
    # --- Role title normalization -------------------------------------------
    _literal_replace(
        "Telekom role line (legacy intern title)",
        "Deutsche Telekom — MLOps Engineer Intern",
        "Deutsche Telekom — Software Engineer | AI Platforms & LLMOps",
    ),
    _literal_replace(
        "Telekom legacy: Current Role prefix",
        "Current Role: Deutsche Telekom — MLOps Engineer Intern",
        "Deutsche Telekom — Software Engineer | AI Platforms & LLMOps",
    ),
    _literal_replace(
        "MLOps Engineer Intern title anywhere else",
        "MLOps Engineer Intern",
        "Software Engineer",
    ),

    # --- About Me block (regex; idempotent against new format) -------------
    _regex_replace(
        "About Me block refresh",
        r'> \*"Structured AI.*?📍 \*\*Bonn, NRW, Germany\*\* 🇩🇪',
        (
            '> *"AI Engineer with experience building AI products, software services, '
            "and cloud systems. I turn unclear requirements into dependable solutions "
            "and carry them into production. My approach combines experimentation with "
            "scalable design, careful evaluation, and engineering from design through "
            'delivery. I design, build, and operate AI systems that continue to perform '
            'as requirements, data, and usage change."*\n\n'
            "### 🎯 **Professional Identity**\n"
            "- 🚀 **Software Engineer | AI Platforms & LLMOps** @ **Deutsche Telekom**\n"
            "- 🏎️ **Master Thesis** @ **Volkswagen Group (CARIAD)** - Integrating LLMs In Automotive Systems\n"
            "- 🎓 **M.Sc. Data Science** @ Friedrich Alexander University Erlangen-Nuremberg\n"
            "- 🌱 Passionate about **Agentic AI**, **LLMOps**, **Go**, and **Cloud-Native Architecture**\n"
            "- 💡 Transforming complex requirements into production-ready intelligence\n"
            "- 📍 **Nürnberg, Germany** 🇩🇪 | EU Blue Card"
        ),
        flags=re.DOTALL,
    ),

    # --- Current-status footer location normalization -----------------------
    _regex_replace(
        "Footer location: Bonn -> Nurnberg-based",
        r"🏢 Current Position\*\*\s*\n📍 \*\*Bonn, NRW, Germany\*\* 🇩🇪",
        "🏢 Current Position**\n📍 **Nürnberg, Germany** 🇩🇪 | Working from Bonn",
    ),
]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def apply_patches(content: str, patches: list[PatchFn]) -> tuple[str, list[bool]]:
    """Apply each patch in order; collect success flags."""
    results: list[bool] = []
    for patch in patches:
        content, ok = patch(content)
        results.append(ok)
    return content, results


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh GitHub profile README.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Dry-run: report what would change; do not write.",
    )
    args = parser.parse_args()

    try:
        original = README_PATH.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"[FATAL] could not read {README_PATH}: {exc}", file=sys.stderr)
        return 2

    updated, results = apply_patches(original, PATCHES)
    changed = updated != original

    if args.check:
        if not changed:
            print("[CHECK] README is up to date.")
            return 0
        print("[CHECK] README would change. Drifting patches:")
        for patch, ok in zip(PATCHES, results):
            if not ok:
                print(f"  - failed: {getattr(patch, '__name__', repr(patch))}")
        return 1

    if not changed:
        print("[DONE] no changes needed.")
        return 0

    try:
        README_PATH.write_text(updated, encoding="utf-8")
    except OSError as exc:
        print(f"[FATAL] could not write {README_PATH}: {exc}", file=sys.stderr)
        return 2

    print(f"[DONE] README updated at {README_PATH}")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
