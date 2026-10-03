from __future__ import annotations
import sys
from PySide6.QtWidgets import QApplication
try:
    from .core_runtime import APP_STYLE
    from .engine import ValidationAssistant
except ImportError:
    # Direct execution: python main.py
    from pathlib import Path
    _project_dir = Path(__file__).resolve().parent
    _project_parent = _project_dir.parent
    if str(_project_parent) not in sys.path:
        sys.path.insert(0, str(_project_parent))
    from Validation_Assistant_Refactored.core_runtime import APP_STYLE
    from Validation_Assistant_Refactored.engine import ValidationAssistant

def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_STYLE)
    window = ValidationAssistant()
    available = QApplication.primaryScreen().availableGeometry()
    window.setMinimumSize(1100, 680)
    width = max(1100, min(1500, int(available.width() * 0.96)))
    height = max(680, min(900, int(available.height() * 0.94)))
    window.resize(width, height)
    window.apply_responsive_input_heights(height)
    window.move(available.x() + (available.width() - width) // 2, available.y() + (available.height() - height) // 2)
    window.show()
    return app.exec()

if __name__ == "__main__":
    raise SystemExit(main())
