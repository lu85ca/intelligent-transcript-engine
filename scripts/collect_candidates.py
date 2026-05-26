#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    scripts_dir = Path(__file__).resolve().parent
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    import manage_candidates

    sys.argv = ["manage_candidates.py", "collect", *sys.argv[1:]]
    return manage_candidates.main()


if __name__ == "__main__":
    raise SystemExit(main())
