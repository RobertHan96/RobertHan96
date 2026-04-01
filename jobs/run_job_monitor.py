from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from jobs.core import main
else:
    from .core import main


if __name__ == "__main__":
    main()
