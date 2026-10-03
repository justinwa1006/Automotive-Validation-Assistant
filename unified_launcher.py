"""
unified_launcher.py  -  Validation Assistant 통합 런처 (디자인 시스템 & 리팩토링 모듈 호환판)
"""
import argparse
import os
import re
import subprocess
import sys
import traceback
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

SETTINGS_ORG = "ValidationAssistant"
SETTINGS_APP = "AutomotiveValidationAI"

# 모듈 호환 임포트
try:
    import bright_theme as engine
    import ui_design_system as ds
except ImportError:
    try:
        from . import engine, ui_design_system as ds
    except ImportError:
        _project_parent = BASE.parent
        if str(_project_parent) not in sys.path:
            sys.path.insert(0, str(_project_parent))
        from Validation_Assistant_Refactored import engine, ui_design_system as ds


def _legacy(args) -> int:
    target = BASE / ("bright_theme.py" if args.theme in ("bright", "light") else "professional_theme.py")
    env = os.environ.copy()
    env["VA_UNIFIED_LAUNCHER"] = str(Path(__file__).resolve())
    if args.restore_state:
        env["VA_UNIFIED_RESTORE"] = "1"
    return subprocess.call([sys.executable, str(target)], env=env)


def _log_patch_error(name: str):
    print(f"[design-patch skipped] {name}", file=sys.stderr)
    traceback.print_exc()


def patch_engine(engine, ds):
    """엔진 클래스에 디자인 패치를 적용한다."""
    from PySide6.QtCore import QSettings, Qt
    from PySide6.QtWidgets import QApplication, QLabel

    VA = engine.ValidationAssistant

    # 1) 엔진 내부 QSS 미사용 처리
    try:
        VA._u_theme_css = lambda self: ""
    except Exception:
        _log_patch_error("theme css")

    # 2) 재실행 없이 즉시 테마 전환
    try:
        def apply_to_window(window, theme):
            app = QApplication.instance()
            ds.apply_theme(app, theme)
            window._ds_theme = theme
            dark = (theme == "dark")
            
            btn = getattr(window, "u_theme_switch_btn", None)
            if btn is not None:
                btn.setText("☀ 밝은 화면" if dark else "☾ 어두운 화면")
                
            window.setWindowTitle("Validation Assistant Unified - " + ("Professional" if dark else "Bright"))
            ds.set_native_titlebar_dark(window, dark)
            QSettings(SETTINGS_ORG, SETTINGS_APP).setValue("ui/theme", theme)

        def switch_unified_theme(self, target=None):
            current = getattr(self, "_ds_theme", "dark")
            theme = ds.normalize_theme(target) if target else ("light" if current == "dark" else "dark")
            if theme == current:
                return
            apply_to_window(self, theme)
            toast = getattr(self, "_ds_toast", None)
            if toast is not None:
                toast.popup("어두운 화면으로 전환했습니다." if theme == "dark" else "밝은 화면으로 전환했습니다.")

        VA.switch_unified_theme = switch_unified_theme
        VA._ds_apply_to_window = staticmethod(apply_to_window)
    except Exception:
        _log_patch_error("theme switch")

    # 3) 검증 결과 패널의 빈 상태 안내
    try:
        original_show = getattr(VA, "_u_show_structured_result", None)
        if original_show:
            def show_structured(self, key, data):
                original_show(self, key, data)
                if key == "validation" and (not isinstance(data, dict) or not data):
                    layout = getattr(self, "u_structured_layouts", {}).get(key)
                    if layout is not None:
                        label = QLabel("AI JSON 결과를 Paste하면\n판정과 상세 결과가 여기에 표시됩니다.")
                        label.setObjectName("uStructuredEmptyGuide")
                        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                        label.setWordWrap(True)
                        layout.insertWidget(0, label)
                        layout.insertStretch(0, 1)

            VA._u_show_structured_result = show_structured
    except Exception:
        _log_patch_error("empty state")

    # 4) TOTAL SCORE 점수대별 구분
    try:
        original_metric = getattr(VA, "_u_set_result_metric", None)
        if original_metric:
            def set_metric(self, key, value):
                original_metric(self, key, value)
                label = getattr(self, "u_validation_metric_label", None)
                if key == "validation" and label is not None:
                    m = re.search(r"SCORE\s+(\d{1,3})", label.text())
                    state = "guide" if not m else ("high" if int(m.group(1)) >= 80 else "mid" if int(m.group(1)) >= 50 else "low")
                    label.setProperty("metricState", state)
                    ds.repolish(label)

            VA._u_set_result_metric = set_metric
    except Exception:
        _log_patch_error("score tiers")

# 5) 토스트 메시지 설치 (QMessageBox 속성 유무 확인 후 안전 호출)
    try:
        if hasattr(ds, "install_toast_for_information") and hasattr(engine, "QMessageBox"):
            ds.install_toast_for_information(engine)
    except Exception:
        pass  # 모듈에 QMessageBox가 없는 경우 로그 없이 자연스럽게 통과


def finish_window(window, ds, theme):
    """윈도우 생성 직후 마무리 세팅"""
    try:
        window._ds_theme = theme
        if hasattr(ds, "Toast"):
            window._ds_toast = ds.Toast(window)
    except Exception:
        _log_patch_error("toast widget")
        
    try:
        btn = getattr(window, "u_theme_switch_btn", None)
        if btn is not None:
            try:
                btn.clicked.disconnect()
            except Exception:
                pass
            btn.clicked.connect(lambda _checked=False: window.switch_unified_theme())
            btn.setText("☀ 밝은 화면" if theme == "dark" else "☾ 어두운 화면")
            btn.setToolTip("화면 테마 전환 (Ctrl+Shift+T). 입력값과 결과는 그대로 유지됩니다.")
    except Exception:
        _log_patch_error("theme button")
        
    try:
        if hasattr(window, "u_shell"):
            ds.normalize_layout(window.u_shell)
    except Exception:
        _log_patch_error("layout normalize")
        
    try:
        if hasattr(ds, "install_shortcuts"):
            ds.install_shortcuts(window, lambda: window.switch_unified_theme())
    except Exception:
        _log_patch_error("shortcuts")
        
    window.setWindowTitle("Validation Assistant Unified - " + ("Professional" if theme == "dark" else "Bright"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--theme", choices=["bright", "professional", "light", "dark"], default=None)
    parser.add_argument("--restore-state", action="store_true")
    parser.add_argument("--legacy", action="store_true", help="이전 방식(서브프로세스)으로 실행")
    args = parser.parse_args()

    os.environ["VA_UNIFIED_LAUNCHER"] = str(Path(__file__).resolve())
    if args.restore_state:
        os.environ["VA_UNIFIED_RESTORE"] = "1"
    if args.legacy:
        return _legacy(args)

    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    saved = QSettings(SETTINGS_ORG, SETTINGS_APP).value("ui/theme", "dark")
    theme = ds.normalize_theme(args.theme or saved)

    if hasattr(ds, "InlineStyleGuard"):
        guard = ds.InlineStyleGuard(app)
        app.installEventFilter(guard)

    ds.apply_theme(app, theme)
    patch_engine(engine, ds)

    window = engine.ValidationAssistant()
    finish_window(window, ds, theme)

    available = app.primaryScreen().availableGeometry()
    window.setMinimumSize(1100, 680)
    width = max(1100, min(1500, int(available.width() * 0.96)))
    height = max(680, min(900, int(available.height() * 0.94)))
    window.resize(width, height)
    try:
        window.apply_responsive_input_heights(height)
    except Exception:
        pass
    window.move(available.x() + (available.width() - width) // 2, available.y() + (available.height() - height) // 2)
    window.show()
    ds.set_native_titlebar_dark(window, theme == "dark")
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())