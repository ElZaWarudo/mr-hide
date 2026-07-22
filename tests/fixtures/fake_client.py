from __future__ import annotations

import sys


def main() -> int:
    if len(sys.argv) >= 3 and sys.argv[1] == "--version":
        print(f"fake-client {sys.argv[2]}")
        return 0
    if len(sys.argv) >= 2 and sys.argv[1] == "--version-bytes":
        sys.stdout.buffer.write(b"fake-client \xff\xfe\n")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
