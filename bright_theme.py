try:
    from .engine import ValidationAssistant
    from .main import main
except ImportError:
    import sys
    from pathlib import Path
    _project_dir = Path(__file__).resolve().parent
    _project_parent = _project_dir.parent
    if str(_project_parent) not in sys.path:
        sys.path.insert(0, str(_project_parent))
    from Validation_Assistant_Refactored.engine import ValidationAssistant
    from Validation_Assistant_Refactored.main import main

if __name__ == "__main__":
    raise SystemExit(main())
