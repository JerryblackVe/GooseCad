"""PyInstaller entry point; keep module invocation and frozen entry aligned."""
from goosecad.ui.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main())
