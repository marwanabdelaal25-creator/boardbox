#!/usr/bin/env python3
"""Post-bootstrap import fixes for boardbox."""
from pathlib import Path

ROOT = Path(r"e:\AfterQuery\Silver\boardbox")

REPLACEMENTS = [
    ("boardbox.format", "boardbox.edition"),
    ("from boardbox.studio import", "from boardbox.publisher import"),
    ("boardbox.studio import", "boardbox.publisher import"),
]

for py in list((ROOT / "src" / "boardbox").glob("*.py")) + list((ROOT / "tests").glob("*.py")):
    text = py.read_text(encoding="utf-8")
    for a, b in REPLACEMENTS:
        text = text.replace(a, b)
    py.write_text(text, encoding="utf-8")

extra = ROOT / "src" / "boardbox" / "studio_name.py"
if extra.exists():
    extra.unlink()
    print("removed studio_name.py duplicate")

print("fixed imports")
