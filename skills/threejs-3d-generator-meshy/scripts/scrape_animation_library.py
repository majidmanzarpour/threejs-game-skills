#!/usr/bin/env python3
"""Rebuild references/animations.csv from a saved copy of Meshy's animation library page.

The Animation API takes an `action_id`, and the only published mapping from id to name is
the documentation table. Keeping a local CSV lets the tooling resolve clip names ("walk",
"idle") without a network round trip on every call.

    curl -sL https://docs.meshy.ai/en/api/animation-library -o library.html
    python3 scripts/scrape_animation_library.py library.html references/animations.csv
"""

from __future__ import annotations

import csv
import html
from pathlib import Path
import re
import sys

ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
CELL = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S)
TAG = re.compile(r"<[^>]+>")


def text_of(cell: str) -> str:
    return html.unescape(TAG.sub("", cell)).strip()


def scrape(source: Path) -> list[list[str]]:
    rows: list[list[str]] = []
    for row in ROW.findall(source.read_text(encoding="utf-8")):
        cells = CELL.findall(row)
        if len(cells) < 4:
            continue
        values = [text_of(c) for c in cells[:4]]
        if not values[0].isdigit():
            continue
        rows.append(values)
    return rows


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    rows = scrape(Path(sys.argv[1]))
    if not rows:
        print("no animation rows found - the docs markup may have changed", file=sys.stderr)
        return 1
    out = Path(sys.argv[2])
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["action_id", "name", "category", "subcategory"])
        writer.writerows(rows)
    print(f"{out}: {len(rows)} animations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
