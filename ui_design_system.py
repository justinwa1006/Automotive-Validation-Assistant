"""
ui_design_system.py  -  Validation Assistant 디자인 시스템 (PySide6)

기존 bright_theme.py / professional_theme.py 에 흩어져 있던 색상·폰트·인라인 스타일을
'디자인 토큰 → QSS 한 벌'로 통합한 모듈입니다. 기존 8,800줄 코드는 수정하지 않습니다.

제공 기능
  - TOKENS / build_qss()      : light, dark 두 테마를 토큰 하나에서 생성
  - apply_theme()             : QSS + QPalette + 폰트 스택을 런타임에 즉시 교체 (재실행 불필요)
  - InlineStyleGuard          : 레거시 코드의 하드코딩 인라인 스타일을 폴리시 시점에 제거
  - normalize_layout()        : 버튼 높이/포커스/커서 등 미세 간격 통일
  - Toast                     : 논블로킹 알림 (성공/안내 팝업 대체)
  - install_shortcuts()       : Ctrl+Enter, Ctrl+S, Ctrl+1/2/3, Ctrl+Shift+T, F1
  - set_native_titlebar_dark(): Windows 제목 표시줄 다크 모드 동기화
  - audit_contrast()          : WCAG 대비비 점검 (python ui_design_system.py --audit)
"""
from __future__ import annotations

import os
import sys
import tempfile
from string import Template

from PySide6.QtCore import QEasingCurve, QEvent, QObject, QPointF, QPropertyAnimation, QTimer, Qt
from PySide6.QtGui import QColor, QFont, QKeySequence, QPainter, QPalette, QPen, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsOpacityEffect,
    QLabel,
    QMessageBox,
    QPushButton,
    QSplitter,
    QWidget,
)

# ----------------------------------------------------------------------------
# 1. 디자인 토큰
# ----------------------------------------------------------------------------
THEME_ALIASES = {
    "light": "light", "bright": "light",
    "dark": "dark", "professional": "dark",
}

FONT_FAMILIES = ["Segoe UI", "Malgun Gothic", "Apple SD Gothic Neo", "Noto Sans CJK KR", "sans-serif"]
MONO_FAMILIES = '"Cascadia Mono","Consolas","D2Coding","Malgun Gothic",monospace'

TOKENS = {
    "light": {
        "bg": "#F2F5F8", "surface": "#FFFFFF", "surface_alt": "#E9EFF4", "surface_sunken": "#F6F9FB",
        "input_bg": "#FFFFFF", "border": "#D5DEE6", "border_strong": "#B3C1CC", "border_hover": "#7F95A5",
        "text": "#1A2A35", "text_strong": "#0F1D27", "text_muted": "#53687A", "text_disabled": "#93A3AF",
        "placeholder": "#7C8E9B",
        "accent": "#0B7F75", "accent_hover": "#096E65", "accent_pressed": "#075A53", "accent_text": "#FFFFFF",
        "accent_fg": "#0A6E66", "accent_line": "#0B7F75", "accent_soft": "#E1F3F1",
        "btn_bg": "#EDF2F6", "btn_hover": "#E0E8EE", "btn_pressed": "#D3DEE6", "disabled_bg": "#EEF2F5",
        "selection_bg": "#CBEDE8", "selection_fg": "#0F2F2B",
        "scroll": "#BAC7D1", "scroll_hover": "#92A5B3",
        "success_bg": "#E3F5E9", "success_fg": "#166534", "success_solid": "#15803D",
        "warn_bg": "#FEF3E2", "warn_fg": "#92400E", "warn_solid": "#B45309",
        "danger_bg": "#FDE8E8", "danger_fg": "#991B1B", "danger_solid": "#B91C1C",
        "neutral_solid": "#64748B",
        "chip_bg": "#E6F4F2", "chip_fg": "#0A6E66", "chip_border": "#A8D8D2",
        "tooltip_bg": "#1F2F3A", "tooltip_fg": "#F3F7FA", "toast_bg": "#1F2F3A", "toast_fg": "#FFFFFF",
    },
    "dark": {
        "bg": "#0C1620", "surface": "#121F2B", "surface_alt": "#182938", "surface_sunken": "#0E1A25",
        "input_bg": "#0E1A25", "border": "#27394A", "border_strong": "#3B5367", "border_hover": "#5E7C93",
        "text": "#E6EEF3", "text_strong": "#FFFFFF", "text_muted": "#9DB0BE", "text_disabled": "#5F7385",
        "placeholder": "#6F8394",
        "accent": "#0E8277", "accent_hover": "#0B7066", "accent_pressed": "#085A52", "accent_text": "#FFFFFF",
        "accent_fg": "#4FE0D2", "accent_line": "#1FB5A8", "accent_soft": "#12312F",
        "btn_bg": "#1B2D3C", "btn_hover": "#243B4E", "btn_pressed": "#14222E", "disabled_bg": "#111C27",
        "selection_bg": "#14524E", "selection_fg": "#FFFFFF",
        "scroll": "#35505F", "scroll_hover": "#4E6E80",
        "success_bg": "#12301F", "success_fg": "#6EE7A0", "success_solid": "#15803D",
        "warn_bg": "#35240F", "warn_fg": "#FBBF6A", "warn_solid": "#B45309",
        "danger_bg": "#3A1618", "danger_fg": "#FCA5A5", "danger_solid": "#B91C1C",
        "neutral_solid": "#64748B",
        "chip_bg": "#12302F", "chip_fg": "#5FE6D8", "chip_border": "#1F6B66",
        "tooltip_bg": "#E6EEF3", "tooltip_fg": "#0C1620", "toast_bg": "#243B4E", "toast_fg": "#FFFFFF",
    },
}


def normalize_theme(name) -> str:
    return THEME_ALIASES.get(str(name or "").strip().lower(), "dark")


# ----------------------------------------------------------------------------
# 2. QSS 템플릿  (타입 스케일: 9 / 10 / 11 / 14pt, 반경: 6 / 8 / 10px)
# ----------------------------------------------------------------------------
_QSS = Template(r"""
QWidget { color:$text; font-size:10pt; }
QDialog, QMessageBox, QInputDialog, QFileDialog { background:$bg; }
QWidget#uShell { background:$bg; }
QLabel { background:transparent; border:none; }
QToolTip { background:$tooltip_bg; color:$tooltip_fg; border:1px solid $border_strong; border-radius:4px; padding:5px 8px; }

/* ---------- 컨테이너 ---------- */
QWidget#uCard { background:$surface; border:1px solid $border; border-radius:10px; }
QWidget#uCommon { background:$surface_alt; border:1px solid $border; border-radius:8px; }
QWidget#uInfoHeader, QWidget#uResultHeader, QWidget#uResultActionRow, QWidget#uResultActionSpacer,
QWidget#uResultPane, QWidget#uAutoPanel, QWidget#uEvidenceHeader, QWidget#uGenerationPage,
QWidget#uGenerationSettingRow { background:transparent; border:none; }

/* ---------- 타이포 ---------- */
QLabel#uTitle { color:$text_strong; font-size:14pt; font-weight:700; }
QLabel#uSection { color:$accent_fg; font-size:11pt; font-weight:700; padding:6px 2px; border:none; border-bottom:2px solid $accent_line; }
QLabel#uField { color:$text_muted; font-size:9pt; font-weight:700; padding-top:2px; }
QLabel#uExampleTitle { color:$text_strong; font-size:12pt; font-weight:700; padding:6px; }
QLabel#uStructuredEmptyGuide, QLabel#uGalleryEmpty { color:$text_muted; background:transparent; padding:24px; }

/* ---------- 상태 칩 ---------- */
QLabel#uResourceStatus, QLabel#uBlfStatus { background:$chip_bg; color:$chip_fg; border:1px solid $chip_border; border-radius:6px; padding:6px 10px; font-weight:600; }
QLabel#uBlfStatus[state="ready"] { background:$success_bg; color:$success_fg; border:1px solid $success_fg; }
QLabel#uBlfStatus[state="pending"] { background:$warn_bg; color:$warn_fg; border:1px solid $warn_fg; }

/* ---------- 입력 ---------- */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background:$input_bg; color:$text; border:1px solid $border_strong; border-radius:6px; padding:6px 10px;
    selection-background-color:$selection_bg; selection-color:$selection_fg; }
QTextEdit, QPlainTextEdit { padding:8px; }
QLineEdit:hover, QTextEdit:hover, QPlainTextEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover, QComboBox:hover { border:1px solid $border_hover; }
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus { border:1px solid $accent_line; }
QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled, QSpinBox:disabled, QComboBox:disabled { background:$disabled_bg; color:$text_disabled; border:1px solid $border; }
QTextEdit[readOnly="true"], QTextEdit[exampleEditor="true"] { font-family:$mono; font-size:9.5pt; }
QComboBox { min-height:20px; }
$combo_arrow
QComboBox QAbstractItemView { background:$surface; color:$text; border:1px solid $border_strong; padding:4px; selection-background-color:$selection_bg; selection-color:$selection_fg; }

/* ---------- 버튼 ---------- */
QPushButton { background:$btn_bg; color:$text; border:1px solid $border_strong; border-radius:6px; padding:6px 14px; font-weight:600; min-height:20px; }
QPushButton:hover { background:$btn_hover; border:1px solid $border_hover; }
QPushButton:pressed { background:$btn_pressed; }
QPushButton:focus { border:1px solid $accent_line; }
QPushButton:disabled { background:$disabled_bg; color:$text_disabled; border:1px solid $border; }
QPushButton#primaryButton { background:$accent; color:$accent_text; border:1px solid $accent_pressed; font-weight:700; padding:8px 16px; }
QPushButton#primaryButton:hover { background:$accent_hover; border:1px solid $accent_pressed; }
QPushButton#primaryButton:pressed { background:$accent_pressed; }
QPushButton#primaryButton:focus { border:2px solid $accent_text; }
QPushButton#primaryButton:disabled { background:$disabled_bg; color:$text_disabled; border:1px solid $border; }

/* ---------- 탭 ---------- */
QTabBar { qproperty-drawBase:0; }
QTabBar#uTabs::tab { min-width:120px; padding:8px 16px; margin:0 4px 0 0; background:$surface; color:$text_muted; border:1px solid $border; border-radius:8px; font-weight:600; }
QTabBar#uTabs::tab:hover:!selected { background:$btn_hover; color:$text; }
QTabBar#uTabs::tab:selected { background:$accent; color:$accent_text; border:1px solid $accent_pressed; font-weight:700; }
QTabWidget::pane { background:$surface; border:1px solid $border; border-radius:6px; top:-1px; }
QTabBar::tab { background:$surface_alt; color:$text_muted; border:1px solid $border; border-bottom:none; padding:7px 16px; margin-right:2px; border-top-left-radius:6px; border-top-right-radius:6px; font-weight:600; }
QTabBar::tab:hover:!selected { background:$btn_hover; color:$text; }
QTabBar::tab:selected { background:$surface; color:$accent_fg; border-bottom:2px solid $accent_line; font-weight:700; }
QTabWidget QTextEdit#uTabEditor { border:none; border-radius:0; background:$input_bg; }

/* ---------- 그룹박스 (제목이 테두리와 겹치지 않는 구조) ---------- */
QGroupBox { background:$surface_sunken; color:$text; border:1px solid $border; border-radius:8px; margin-top:0; padding:28px 8px 8px 8px; font-weight:700; }
QGroupBox::title { subcontrol-origin:padding; subcontrol-position:top left; left:12px; top:7px; padding:0; color:$text_muted; }
QGroupBox#uEvidencePanel { background:$surface; }
QGroupBox#uValidationVerdictBox { background:$surface; border:1px solid $border_strong; }

/* ---------- 체크박스 ---------- */
QCheckBox { background:transparent; spacing:8px; }
QCheckBox::indicator { width:16px; height:16px; border:1px solid $border_strong; border-radius:4px; background:$input_bg; }
QCheckBox::indicator:hover { border:1px solid $accent_line; }
QCheckBox::indicator:checked { background:$accent; border:1px solid $accent_pressed; $check_image }
QCheckBox::indicator:disabled { background:$disabled_bg; border:1px solid $border; }

/* ---------- 리스트 / 메뉴 ---------- */
QListWidget, QListView, QTreeView, QTableView { background:$surface; color:$text; border:1px solid $border; border-radius:6px; padding:4px; }
QListWidget::item { padding:7px 8px; border-radius:4px; }
QListWidget::item:hover { background:$btn_hover; }
QListWidget::item:selected { background:$selection_bg; color:$selection_fg; }
QMenu { background:$surface; color:$text; border:1px solid $border_strong; padding:4px; }
QMenu::item { padding:6px 22px; border-radius:4px; }
QMenu::item:selected { background:$selection_bg; color:$selection_fg; }

/* ---------- 스크롤바 (세로/가로) ---------- */
QScrollBar:vertical { background:transparent; width:12px; margin:2px; }
QScrollBar::handle:vertical { background:$scroll; min-height:32px; border-radius:4px; }
QScrollBar::handle:vertical:hover { background:$scroll_hover; }
QScrollBar:horizontal { background:transparent; height:12px; margin:2px; }
QScrollBar::handle:horizontal { background:$scroll; min-width:32px; border-radius:4px; }
QScrollBar::handle:horizontal:hover { background:$scroll_hover; }
QScrollBar::add-line, QScrollBar::sub-line { width:0; height:0; border:none; background:none; }
QScrollBar::add-page, QScrollBar::sub-page { background:transparent; }

/* ---------- 스플리터 / 진행바 ---------- */
QSplitter::handle { background:transparent; }
QSplitter::handle:horizontal { background:$border; margin:8px 3px; border-radius:1px; }
QSplitter::handle:vertical { background:$border; margin:3px 8px; border-radius:1px; }
QSplitter::handle:hover { background:$accent_line; }
QProgressBar { background:$surface_alt; color:$text; border:1px solid $border; border-radius:4px; text-align:center; }
QProgressBar::chunk { background:$accent; border-radius:3px; }

/* ---------- 결과 영역 ---------- */
QScrollArea { background:transparent; border:none; }
QScrollArea QWidget#qt_scrollarea_viewport { background:transparent; }
QScrollArea#uStructuredResult, QScrollArea#uEvidenceGallery { background:$surface_sunken; border:1px solid $border; border-radius:8px; }
QScrollArea#uStructuredResult QWidget#qt_scrollarea_viewport, QScrollArea#uEvidenceGallery QWidget#qt_scrollarea_viewport { background:$surface_sunken; }
QScrollArea#uStructuredResult > QWidget > QWidget, QScrollArea#uEvidenceGallery > QWidget > QWidget { background:transparent; }
QScrollArea#uStructuredResult QGroupBox { background:$surface; }
QWidget#uImageCard { background:$surface; border:1px solid $border; border-radius:8px; }
QLabel#uThumbnail { background:$surface_sunken; border:1px solid $border; border-radius:6px; }

QLabel#uStructuredMetric { background:$surface_alt; color:$text_muted; border:1px solid $border; border-radius:8px; padding:6px 12px; font-size:10pt; font-weight:700; }
QLabel#uStructuredMetric[metricState="high"] { background:$success_bg; color:$success_fg; border:1px solid $success_fg; }
QLabel#uStructuredMetric[metricState="mid"] { background:$warn_bg; color:$warn_fg; border:1px solid $warn_fg; }
QLabel#uStructuredMetric[metricState="low"] { background:$danger_bg; color:$danger_fg; border:1px solid $danger_fg; }

QLabel#uLargeVerdict { min-height:44px; background:$neutral_solid; color:#FFFFFF; border-radius:8px; font-size:15pt; font-weight:800; padding:8px 14px; }
QLabel#uLargeVerdict[verdict="PASS"], QLabel#uVerdict[verdict="PASS"] { background:$success_solid; }
QLabel#uLargeVerdict[verdict="FAIL"], QLabel#uVerdict[verdict="FAIL"] { background:$danger_solid; }
QLabel#uLargeVerdict[verdict="PARTIAL"], QLabel#uLargeVerdict[verdict="NEEDS IMPROVEMENT"], QLabel#uLargeVerdict[verdict="INCONCLUSIVE"],
QLabel#uVerdict[verdict="PARTIAL"], QLabel#uVerdict[verdict="NEEDS IMPROVEMENT"], QLabel#uVerdict[verdict="INCONCLUSIVE"] { background:$warn_solid; }
QLabel#uVerdict { background:$neutral_solid; color:#FFFFFF; border-radius:12px; padding:5px 12px; font-weight:800; }

/* ---------- 토스트 ---------- */
QLabel#uToast { background:$toast_bg; color:$toast_fg; border:1px solid $border_strong; border-left:4px solid $accent_line; border-radius:8px; padding:10px 18px; font-weight:600; }
QLabel#uToast[kind="success"] { border-left:4px solid $success_solid; }
QLabel#uToast[kind="warn"] { border-left:4px solid $warn_solid; }
QLabel#uToast[kind="error"] { border-left:4px solid $danger_solid; }
""")


def build_qss(theme: str, icons: dict | None = None) -> str:
    theme = normalize_theme(theme)
    icons = icons or {}
    values = dict(TOKENS[theme])
    values["mono"] = MONO_FAMILIES
    chevron = icons.get("chevron")
    check = icons.get("check")
    values["combo_arrow"] = (
        'QComboBox::drop-down { subcontrol-origin:padding; subcontrol-position:center right; width:26px; border:none; }\n'
        'QComboBox::down-arrow { image:url("%s"); width:12px; height:12px; }' % chevron
        if chevron else ""
    )
    values["check_image"] = 'image:url("%s");' % check if check else ""
    return _QSS.safe_substitute(values)


def build_palette(theme: str) -> QPalette:
    t = TOKENS[normalize_theme(theme)]
    pal = QPalette()
    roles = {
        QPalette.ColorRole.Window: t["bg"], QPalette.ColorRole.WindowText: t["text"],
        QPalette.ColorRole.Base: t["input_bg"], QPalette.ColorRole.AlternateBase: t["surface_alt"],
        QPalette.ColorRole.Text: t["text"], QPalette.ColorRole.PlaceholderText: t["placeholder"],
        QPalette.ColorRole.Button: t["btn_bg"], QPalette.ColorRole.ButtonText: t["text"],
        QPalette.ColorRole.Highlight: t["selection_bg"], QPalette.ColorRole.HighlightedText: t["selection_fg"],
        QPalette.ColorRole.ToolTipBase: t["tooltip_bg"], QPalette.ColorRole.ToolTipText: t["tooltip_fg"],
        QPalette.ColorRole.Link: t["accent_fg"],
    }
    for role, color in roles.items():
        pal.setColor(role, QColor(color))
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.ButtonText, QPalette.ColorRole.WindowText):
        pal.setColor(QPalette.ColorGroup.Disabled, role, QColor(t["text_disabled"]))
    return pal


# ----------------------------------------------------------------------------
# 3. 아이콘(체크, 콤보 화살표)  -  플러그인 의존 없이 PNG 로 직접 그린다
# ----------------------------------------------------------------------------
def _draw_icon(path: str, kind: str, color: str, size: int):
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    pen = QPen(QColor(color))
    pen.setWidthF(size / 12 * 1.7)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    s = size / 12.0
    pts = [(2.6, 4.4), (6.0, 7.8), (9.4, 4.4)] if kind == "chevron" else [(2.4, 6.4), (5.0, 9.0), (9.8, 3.4)]
    p.drawPolyline([QPointF(x * s, y * s) for x, y in pts])
    p.end()
    pix.save(path, "PNG")


def ensure_icons(theme: str) -> dict:
    theme = normalize_theme(theme)
    t = TOKENS[theme]
    try:
        folder = os.path.join(tempfile.gettempdir(), "va_design_system")
        os.makedirs(folder, exist_ok=True)
        out = {}
        for kind, color in (("chevron", t["text_muted"]), ("check", "#FFFFFF")):
            base = os.path.join(folder, f"{kind}_{theme}.png")
            _draw_icon(base, kind, color, 12)
            _draw_icon(os.path.join(folder, f"{kind}_{theme}@2x.png"), kind, color, 24)
            out[kind] = base.replace("\\", "/")
        return out
    except Exception:
        return {}


# ----------------------------------------------------------------------------
# 4. 테마 적용
# ----------------------------------------------------------------------------
def apply_theme(app: QApplication, theme: str) -> str:
    theme = normalize_theme(theme)
    app.setPalette(build_palette(theme))
    font = app.font()
    try:
        font.setFamilies(FONT_FAMILIES)
    except Exception:
        font.setFamily(FONT_FAMILIES[0])
    font.setPointSizeF(10.0)
    app.setFont(font)
    app.setStyleSheet(build_qss(theme, ensure_icons(theme)))
    return theme


def set_native_titlebar_dark(widget: QWidget, dark: bool):
    """Windows 10/11 제목 표시줄을 앱 테마와 맞춘다 (다른 OS 에서는 무시)."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        hwnd = int(widget.winId())
        value = ctypes.c_int(1 if dark else 0)
        for attr in (20, 19):  # DWMWA_USE_IMMERSIVE_DARK_MODE (신/구 빌드)
            if ctypes.windll.dwmapi.DwmSetWindowAttribute(
                ctypes.c_void_p(hwnd), attr, ctypes.byref(value), ctypes.sizeof(value)
            ) == 0:
                break
    except Exception:
        pass


# ----------------------------------------------------------------------------
# 5. 레거시 인라인 스타일 제거 + 레이아웃 정리
# ----------------------------------------------------------------------------
class InlineStyleGuard(QObject):
    """위젯이 처음 폴리시될 때 하드코딩된 setStyleSheet 를 비워 중앙 QSS 가 적용되게 한다.
    dsKeep 속성이 True 인 위젯은 건드리지 않는다."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._busy = False

    def eventFilter(self, obj, event):
        if self._busy or event.type() != QEvent.Type.Polish:
            return False
        try:
            if obj.isWidgetType() and obj.styleSheet() and not obj.property("dsKeep"):
                self._busy = True
                try:
                    obj.setStyleSheet("")
                finally:
                    self._busy = False
        except Exception:
            self._busy = False
        return False


def strip_inline_styles(root: QWidget):
    for widget in [root] + root.findChildren(QWidget):
        try:
            if widget.styleSheet() and not widget.property("dsKeep"):
                widget.setStyleSheet("")
        except Exception:
            pass


def normalize_layout(root: QWidget):
    """레거시 코드의 들쭉날쭉한 고정 높이/폰트/포커스 정책을 통일한다."""
    for widget in root.findChildren(QWidget):
        try:
            if widget.minimumHeight() == widget.maximumHeight() == 50:
                widget.setFixedHeight(42)
            if isinstance(widget, QPushButton):
                widget.setFont(QFont())                       # 개별 9pt 지정 해제 → 앱 폰트 상속
                widget.setFocusPolicy(Qt.FocusPolicy.TabFocus)  # 키보드 이동 시에만 포커스 링 표시
                widget.setCursor(Qt.CursorShape.PointingHandCursor)
            elif isinstance(widget, QSplitter):
                widget.setHandleWidth(12)
        except Exception:
            pass


def repolish(widget: QWidget):
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()


# ----------------------------------------------------------------------------
# 6. 토스트
# ----------------------------------------------------------------------------
class Toast(QLabel):
    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setObjectName("uToast")
        self.setWordWrap(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._fx = QGraphicsOpacityEffect(self)
        self._fx.setOpacity(0.0)
        self.setGraphicsEffect(self._fx)
        self._anim = QPropertyAnimation(self._fx, b"opacity", self)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._fade_out)
        self.hide()

    def popup(self, text: str, kind: str = "info", msec: int = 2400):
        parent = self.parentWidget()
        if parent is None:
            return
        self.setProperty("kind", kind)
        repolish(self)
        self.setText(text)
        self.setMaximumWidth(max(240, min(560, parent.width() - 60)))
        self.adjustSize()
        self.move((parent.width() - self.width()) // 2, parent.height() - self.height() - 28)
        self.show()
        self.raise_()
        self._animate(self._fx.opacity(), 1.0, 160)
        self._timer.start(msec)

    def _fade_out(self):
        self._animate(self._fx.opacity(), 0.0, 260)
        QTimer.singleShot(280, self.hide)

    def _animate(self, start, end, ms):
        self._anim.stop()
        self._anim.setDuration(ms)
        self._anim.setStartValue(start)
        self._anim.setEndValue(end)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.start()


def install_toast_for_information(engine_module):
    """QMessageBox.information 중 짧은 한 줄 안내는 토스트로 대체한다. 긴 내용/질문/경고는 기존 대화상자 유지."""
    Base = engine_module.QMessageBox

    class ToastMessageBox(Base):
        @staticmethod
        def information(parent, title, text, *args, **kwargs):
            toast = getattr(parent, "_ds_toast", None) if parent is not None else None
            if toast is not None and isinstance(text, str) and len(text) <= 90 and "\n" not in text:
                ok = any(word in text for word in ("완료", "저장", "복사", "성공", "적용"))
                toast.popup(text, "success" if ok else "info")
                return Base.StandardButton.Ok
            return Base.information(parent, title, text, *args, **kwargs)

    engine_module.QMessageBox = ToastMessageBox


# ----------------------------------------------------------------------------
# 7. 단축키
# ----------------------------------------------------------------------------
SHORTCUT_HELP = (
    "Ctrl+Enter  Prompt Generation 실행\n"
    "Ctrl+S  저장    Ctrl+O  파일 열기    Ctrl+E  Excel 내보내기\n"
    "Ctrl+1 / 2 / 3  Validation / Generation / Review 탭 이동\n"
    "Ctrl+Shift+T  밝은/어두운 화면 전환\n"
    "F1  단축키 도움말"
)


def install_shortcuts(window: QWidget, toggle_theme_cb):
    def bind(keys, callback):
        for key in keys:
            sc = QShortcut(QKeySequence(key), window)
            sc.setContext(Qt.ShortcutContext.WindowShortcut)
            sc.activated.connect(callback)
            window._ds_shortcuts.append(sc)

    window._ds_shortcuts = []

    def run_primary():
        page = window.u_stack.currentWidget()
        for button in page.findChildren(QPushButton):
            if button.objectName() == "primaryButton" and button.text().startswith("Prompt") and button.isEnabled():
                button.click()
                return

    def call(name):
        def _inner():
            fn = getattr(window, name, None)
            if callable(fn):
                fn()
        return _inner

    bind(("Ctrl+Return", "Ctrl+Enter"), run_primary)
    bind(("Ctrl+S",), call("save_tc"))
    bind(("Ctrl+O",), call("load_tc"))
    bind(("Ctrl+E",), call("export_excel"))
    bind(("Ctrl+Shift+T",), toggle_theme_cb)
    for i in range(3):
        bind((f"Ctrl+{i + 1}",), lambda idx=i: window.u_tabs.setCurrentIndex(idx))
    bind(("F1",), lambda: QMessageBox.information(window, "단축키", SHORTCUT_HELP))


# ----------------------------------------------------------------------------
# 8. 접근성 점검 (WCAG 2.1 대비비)
# ----------------------------------------------------------------------------
def _lum(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def contrast_ratio(fg: str, bg: str) -> float:
    a, b = _lum(fg), _lum(bg)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


AUDIT_PAIRS = [
    ("본문 텍스트", "text", "surface"), ("본문 텍스트(앱 배경)", "text", "bg"),
    ("보조 텍스트", "text_muted", "surface"), ("입력창 텍스트", "text", "input_bg"),
    ("Primary 버튼", "accent_text", "accent"), ("Primary 버튼 hover", "accent_text", "accent_hover"),
    ("강조 텍스트(섹션)", "accent_fg", "surface"), ("선택 항목", "selection_fg", "selection_bg"),
    ("성공 칩", "success_fg", "success_bg"), ("경고 칩", "warn_fg", "warn_bg"), ("오류 칩", "danger_fg", "danger_bg"),
    ("PASS 배지", "accent_text", "success_solid"), ("FAIL 배지", "accent_text", "danger_solid"),
    ("WARN 배지", "accent_text", "warn_solid"), ("상태 칩", "chip_fg", "chip_bg"),
    ("토스트", "toast_fg", "toast_bg"),
]


def audit_contrast(minimum: float = 4.5, stream=None) -> bool:
    out = stream or sys.stdout
    ok_all = True
    for theme in ("light", "dark"):
        print(f"[{theme}]", file=out)
        for label, fg, bg in AUDIT_PAIRS:
            ratio = contrast_ratio(TOKENS[theme][fg], TOKENS[theme][bg])
            ok = ratio >= minimum
            ok_all &= ok
            print(f"  {'OK  ' if ok else 'FAIL'} {ratio:5.2f}:1  {label}", file=out)
    return ok_all


if __name__ == "__main__":
    if "--audit" in sys.argv:
        raise SystemExit(0 if audit_contrast() else 1)
    print("python ui_design_system.py --audit  : 대비비 점검")
