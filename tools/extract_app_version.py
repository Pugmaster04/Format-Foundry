import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from app_identity import PACKAGE_VERSION

    print(PACKAGE_VERSION)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
