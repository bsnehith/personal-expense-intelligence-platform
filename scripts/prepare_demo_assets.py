"""
Prepare submission/demo assets expected by assessors.

Current action:
- Ensure docs/architecture.png exists by copying from docs/assets/architecture_diagram.png.
"""
from __future__ import annotations

import shutil
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    src = root / "docs" / "assets" / "architecture_diagram.png"
    dst = root / "docs" / "architecture.png"
    if not src.is_file():
        raise FileNotFoundError(f"Missing source architecture diagram: {src}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
    print(f"Prepared: {dst}")


if __name__ == "__main__":
    main()
