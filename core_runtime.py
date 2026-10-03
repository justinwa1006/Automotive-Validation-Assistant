import sys

import os

import json

import html

import hashlib

import re

import textwrap

import mimetypes

import shutil

import time

import subprocess

from collections import Counter

from datetime import datetime

from pathlib import Path

import openpyxl

from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

try:
    import can
except ImportError:
    can = None

try:
    import cantools
except ImportError:
    cantools = None

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

from PySide6.QtCore import QThread, Signal, Qt, QUrl, QMimeData, QSettings, QTimer, QPropertyAnimation, QEasingCurve

from PySide6.QtGui import QPixmap, QTextCursor, QTextDocument, QTextImageFormat, QTextOption

from PySide6.QtWidgets import (
    QApplication, QGraphicsOpacityEffect, QWidget, QLabel, QLineEdit, QTextEdit, QPushButton, QVBoxLayout,
    QHBoxLayout, QComboBox, QMessageBox, QFileDialog, QGroupBox, QListWidget,
    QSizePolicy, QDialog, QScrollArea, QListWidgetItem, QGridLayout, QSplitter,
    QProgressBar, QSpinBox, QCheckBox, QTabWidget, QTabBar, QStackedWidget
)

BLF_MAX_SUMMARY_EVENTS = 50

BLF_MAX_RAW_CHANGES_PER_ID = 3

MAX_PROMPT_CHARS = 24000

TP_MAX_SESSIONS_IN_PROMPT = 30

TP_MAX_PAYLOAD_BYTES = 4095

ENABLE_GEMINI = False

GEMINI_MODEL = "gemini-3.6-flash"

GEMINI_MAX_ATTEMPTS = 6

BASE_DIR = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))

SAVE_DIR = os.path.join(BASE_DIR, "saved_tc")

HISTORY_FILE = os.path.join(BASE_DIR, "history.json")

CUSTOM_PROFILE_PATH = os.path.join(BASE_DIR, "custom_profile.json")

SIGNAL_SET_PATH = os.path.join(BASE_DIR, "signal_sets.json")

os.makedirs(SAVE_DIR, exist_ok=True)

TEMPLATES = {
    "Custom": {"purpose": "", "expected": ""},
    "NFC Authentication": {"purpose": "NFC Authentication 수행", "expected": "Authentication Success"},
    "UWB Session": {"purpose": "UWB Session 생성 확인", "expected": "Session Active"},
    "Walk Away": {"purpose": "Walk Away 동작 검증", "expected": "Vehicle Lock"},
}

DOMAIN_PROFILES = {'Automotive CANoe': {'role': 'Automotive Electronics and Connectivity Validation Specialist', 'generation': ['Feature / Function Name', 'Requirement / System Behavior', 'Target Behavior / Acceptance Criteria'], 'analysis': ['TC Name', 'TC Definition / Expected Behavior', 'Actual Result / Issue'], 'rules': ['Vehicle state, CAN signal, timing, communication loss, timeout, retry and recovery를 고려한다.', 'BLF/DBC/ISO-TP/UDS 요약이 있으면 직접 확인된 근거로 활용한다.'], 'automotive_tools': True, 'evidence': 'BLF, DBC, screenshot', 'generation_rules': ['Vehicle state별 Positive, Negative, Boundary TC를 생성한다.', 'CAN signal의 송신, 수신, 상태 전이, timeout, retry, recovery를 검증한다.', '진단 기능은 ISO-TP/UDS request, positive/negative response, NRC, sequence 오류를 고려한다.', '측정 가능한 signal value, 상태, 시간 기준을 Expected Result에 작성한다.'], 'analysis_rules': ['TC Expected와 Actual, CAN signal timeline, TP/UDS transaction을 시간순으로 비교한다.', 'DBC로 해석된 signal만 의미를 확정하고 raw payload는 임의 해석하지 않는다.', 'Vehicle State, CAN Communication, Diagnostic Response, TP Sequence, Test Condition을 원인 후보로 분류한다.'], 'review_rules': ['Vehicle State와 precondition이 구체적인지 검토한다.', '각 Step에 대응하는 signal 또는 관찰 가능한 Expected Result가 있는지 검토한다.', 'Timeout, retry, recovery, communication loss, power cycle 누락을 검토한다.'], 'test_categories': ['Positive', 'Negative', 'Boundary', 'State Transition', 'Timeout', 'Recovery', 'Communication Loss', 'Diagnostic'], 'cause_categories': ['PRODUCT_BEHAVIOR', 'TC_DEFINITION', 'VEHICLE_STATE', 'CAN_COMMUNICATION', 'DIAGNOSTIC_RESPONSE', 'TP_SEQUENCE', 'TEST_ENVIRONMENT', 'EVIDENCE_INSUFFICIENT'], 'domain_output_fields': {'vehicle_state': 'TBD', 'network': 'CAN/CAN FD/TBD', 'relevant_signals': [], 'diagnostic_service': 'TBD', 'required_evidence': ['BLF', 'DBC']}}, 'Web / API QA': {'role': 'Web Application and REST API QA Specialist', 'generation': ['API / Feature Name', 'API Specification / Requirement', 'Expected Response / Acceptance Criteria'], 'analysis': ['TC / API Name', 'Request and Expected Response', 'Actual Response / Error'], 'rules': ['HTTP method, status code, headers, schema, authentication, authorization, error handling, timeout and rate limit를 고려한다.', '응답 데이터와 성능 기준은 입력된 사양 범위에서만 판단한다.'], 'automotive_tools': False, 'evidence': 'HAR, JSON, TXT, CSV, screenshot', 'generation_rules': ['HTTP method, endpoint, headers, parameters, body, status code와 response schema를 명시한다.', 'Authentication, authorization, invalid input, rate limit, timeout, idempotency, pagination TC를 고려한다.', '보안상 민감정보 노출과 오류 메시지의 적절성을 검증한다.'], 'analysis_rules': ['Request와 Response를 분리하고 status, headers, body, schema, latency를 비교한다.', 'Client Request, Server Logic, Authentication, Authorization, Schema, Network, Performance로 원인 후보를 분류한다.'], 'review_rules': ['Expected status code와 response schema가 측정 가능하게 정의됐는지 검토한다.', '인증, 권한, 오류 응답, boundary, rate limit, timeout TC 누락을 검토한다.'], 'test_categories': ['Positive', 'Negative', 'Boundary', 'Authentication', 'Authorization', 'Schema', 'Rate Limit', 'Performance'], 'cause_categories': ['CLIENT_REQUEST', 'SERVER_LOGIC', 'AUTHENTICATION', 'AUTHORIZATION', 'SCHEMA_MISMATCH', 'NETWORK', 'PERFORMANCE', 'TEST_DATA', 'EVIDENCE_INSUFFICIENT'], 'domain_output_fields': {'http_method': 'TBD', 'endpoint': 'TBD', 'request_data': 'TBD', 'expected_status_code': 'TBD', 'expected_response_schema': 'TBD', 'response_time_criteria': 'TBD'}}, 'Mobile App QA': {'role': 'Mobile Application QA Specialist', 'generation': ['App Feature', 'Functional Requirement / User Flow', 'Expected App Behavior'], 'analysis': ['TC / App Feature', 'Device, OS, Preconditions and Steps', 'Actual App Behavior / Error'], 'rules': ['OS version, device dependency, permission, network state, foreground/background, restart and orientation을 고려한다.', '기기나 OS에 없는 동작을 임의로 가정하지 않는다.'], 'automotive_tools': False, 'evidence': 'screenshot, crash log, TXT, JSON', 'generation_rules': ['Device, OS, app version, permission, network, orientation과 lifecycle 상태를 precondition에 포함한다.', 'Foreground/background, interruption, restart, upgrade, offline/online 전환 TC를 고려한다.', '화면, 알림, 저장 상태, crash 여부를 관찰 가능한 Expected Result로 작성한다.'], 'analysis_rules': ['App Logic, Device, OS Compatibility, Permission, Network, Lifecycle, Test Condition으로 원인 후보를 분류한다.', 'Screenshot, crash log, app log에서 확인된 사실과 추론을 구분한다.'], 'review_rules': ['Device/OS/app version 조건과 permission 상태가 명확한지 검토한다.', 'network 변경, background 복귀, interruption, restart, orientation 누락을 검토한다.'], 'test_categories': ['Positive', 'Negative', 'Permission', 'Network', 'Lifecycle', 'Compatibility', 'Interruption', 'Recovery'], 'cause_categories': ['APP_LOGIC', 'DEVICE_DEPENDENCY', 'OS_COMPATIBILITY', 'PERMISSION', 'NETWORK', 'APP_LIFECYCLE', 'TEST_CONDITION', 'EVIDENCE_INSUFFICIENT'], 'domain_output_fields': {'device': 'TBD', 'os_version': 'TBD', 'app_version': 'TBD', 'network_condition': 'TBD', 'permission_state': 'TBD', 'app_lifecycle_state': 'TBD'}}, 'Embedded / Device QA': {'role': 'Embedded System and Device Validation Specialist', 'generation': ['Device / Firmware Feature', 'Interface / System Requirement', 'Expected Device Output / Acceptance Criteria'], 'analysis': ['TC / Device Feature', 'Firmware, Interface, Input Condition and Steps', 'Actual Output / Device Log'], 'rules': ['firmware version, power state, timing, reset, UART, GPIO, communication and recovery를 고려한다.', '측정되지 않은 전기적 특성은 임의로 확정하지 않는다.'], 'automotive_tools': False, 'evidence': 'serial log, TXT, CSV, JSON, screenshot', 'generation_rules': ['Firmware, hardware revision, interface, power state, input range와 timing 조건을 정의한다.', 'Power cycle, reset, communication loss, boundary input, fault injection, recovery TC를 고려한다.', 'GPIO, UART, current, voltage, response time 등 측정 가능한 Expected Result를 작성한다.'], 'analysis_rules': ['Firmware Logic, Hardware, Interface, Power, Timing, Communication, Configuration으로 원인 후보를 분류한다.', '측정 로그와 serial log의 시간순 이벤트를 근거로 사용한다.'], 'review_rules': ['Firmware/hardware/interface 조건과 측정 장비가 명확한지 검토한다.', '전원 변동, reset, boundary, timing tolerance, communication loss, recovery 누락을 검토한다.'], 'test_categories': ['Positive', 'Negative', 'Boundary', 'Power', 'Timing', 'Interface', 'Fault Injection', 'Recovery'], 'cause_categories': ['FIRMWARE_LOGIC', 'HARDWARE', 'INTERFACE', 'POWER_STATE', 'TIMING', 'COMMUNICATION', 'CONFIGURATION', 'EVIDENCE_INSUFFICIENT'], 'domain_output_fields': {'firmware_version': 'TBD', 'hardware_revision': 'TBD', 'interface': 'TBD', 'power_condition': 'TBD', 'input_range': 'TBD', 'timing_criteria': 'TBD'}}, 'Desktop Software QA': {'role': 'Desktop Software Quality Assurance Specialist', 'generation': ['Application Feature', 'Software Requirement / Workflow', 'Expected Desktop Behavior'], 'analysis': ['TC / Application Feature', 'OS, Version, Preconditions and Steps', 'Actual Behavior / Error'], 'rules': ['OS version, installation, permissions, file handling, upgrade, compatibility and recovery를 고려한다.'], 'automotive_tools': False, 'evidence': 'TXT, JSON, CSV, log, screenshot', 'generation_rules': ['OS, architecture, application version, permission과 installation 상태를 정의한다.', 'Install, uninstall, upgrade, file handling, multi-instance, crash recovery, compatibility TC를 고려한다.', 'UI 상태, file output, process 상태와 오류 메시지를 측정 가능한 결과로 작성한다.'], 'analysis_rules': ['Application Logic, OS Compatibility, Permission, Installation, File I/O, Dependency, Resource로 원인 후보를 분류한다.'], 'review_rules': ['OS/version/permission/dependency 조건이 명확한지 검토한다.', 'install, upgrade, rollback, file corruption, multi-instance, crash recovery 누락을 검토한다.'], 'test_categories': ['Positive', 'Negative', 'Installation', 'Upgrade', 'Compatibility', 'File I/O', 'Multi-instance', 'Recovery'], 'cause_categories': ['APPLICATION_LOGIC', 'OS_COMPATIBILITY', 'PERMISSION', 'INSTALLATION', 'FILE_IO', 'DEPENDENCY', 'RESOURCE', 'EVIDENCE_INSUFFICIENT'], 'domain_output_fields': {'os': 'TBD', 'architecture': 'TBD', 'application_version': 'TBD', 'permission_level': 'TBD', 'installation_state': 'TBD', 'dependency': 'TBD'}}, 'General QA': {'role': 'Software Quality Assurance Specialist', 'generation': ['Feature Name', 'Requirement', 'Acceptance Criteria'], 'analysis': ['TC Name', 'Test Definition / Expected Result', 'Actual Result / Issue'], 'rules': ['Positive, negative, boundary, state transition, timeout and recovery를 고려한다.', '분야 고유 사양은 입력에 없으면 TBD로 표시한다.'], 'automotive_tools': False, 'evidence': 'TXT, JSON, CSV, screenshot', 'generation_rules': ['Positive, Negative, Boundary, State Transition, Timeout, Recovery를 균형 있게 생성한다.', 'Preconditions, Steps, Expected Results를 번호 배열로 작성하고 Step과 Expected를 1:1 대응한다.'], 'analysis_rules': ['Requirement, Actual Result, Environment, Test Data, User Operation, Evidence로 원인 후보를 분류한다.'], 'review_rules': ['명확성, 실행 가능성, 측정 가능성, 중복, 누락 시나리오를 검토한다.'], 'test_categories': ['Positive', 'Negative', 'Boundary', 'State Transition', 'Timeout', 'Recovery'], 'cause_categories': ['PRODUCT_BEHAVIOR', 'TC_DEFINITION', 'TEST_CONDITION', 'TEST_DATA', 'USER_OPERATION', 'TEST_ENVIRONMENT', 'EVIDENCE_INSUFFICIENT'], 'domain_output_fields': {'environment': 'TBD', 'test_data': 'TBD', 'dependency': 'TBD', 'measurement_criteria': 'TBD'}}, 'Custom': {'role': 'Custom Domain Quality Assurance Specialist', 'generation': ['Feature Name', 'Requirement', 'Acceptance Criteria'], 'analysis': ['TC Name', 'Test Definition / Expected Result', 'Actual Result / Issue'], 'rules': ['custom_profile.json에 정의된 규칙을 적용한다.'], 'automotive_tools': False, 'evidence': 'TXT, JSON, CSV, screenshot', 'generation_rules': ['custom_profile.json의 generation_rules를 적용한다.'], 'analysis_rules': ['custom_profile.json의 analysis_rules와 cause_categories를 적용한다.'], 'review_rules': ['custom_profile.json의 review_rules를 적용한다.'], 'test_categories': ['Positive', 'Negative', 'Boundary'], 'cause_categories': ['CUSTOM_CAUSE', 'EVIDENCE_INSUFFICIENT'], 'domain_output_fields': {}}}

DEFAULT_CUSTOM_PROFILE = {'role': 'Custom Domain QA Specialist', 'generation': ['Feature Name', 'Requirement', 'Acceptance Criteria'], 'analysis': ['TC Name', 'Test Definition', 'Actual Result'], 'rules': ['사용자가 정의한 분야 규칙을 적용한다.'], 'automotive_tools': False, 'evidence': 'TXT, JSON, CSV, screenshot', 'generation_rules': ['custom_profile.json의 generation_rules를 적용한다.'], 'analysis_rules': ['custom_profile.json의 analysis_rules와 cause_categories를 적용한다.'], 'review_rules': ['custom_profile.json의 review_rules를 적용한다.'], 'test_categories': ['Positive', 'Negative', 'Boundary'], 'cause_categories': ['CUSTOM_CAUSE', 'EVIDENCE_INSUFFICIENT'], 'domain_output_fields': {}}

APP_STYLE = 'QWidget { background-color:#eef2f6; color:#344451; font-family:"Segoe UI"; font-size:9pt; }\nQWidget#panel { background-color:#ffffff; border:1px solid #cdd6df; border-radius:6px; }\nQScrollArea { background:transparent; border:none; }\nQLabel { color:#344451; font-weight:600; background:transparent; border:none; }\nQLabel#sectionTitle { color:#173b4f; background:#e6f1f4; border-left:4px solid #0f8b8d; border-radius:3px; font-size:12pt; font-weight:700; padding:7px 10px; }\nQLabel#subSectionTitle { color:#48606f; font-size:10pt; font-weight:700; padding:6px 2px 3px 2px; }\nQLabel#dashboardLabel { color:#3e5564; background:#ffffff; border:1px solid #d1dce3; border-radius:4px; padding:7px 10px; font-family:"Consolas"; }\nQLineEdit,QTextEdit,QComboBox,QSpinBox { background:#ffffff; color:#173b4f; border:1px solid #b9c6d0; border-radius:4px; padding:6px 8px; selection-background-color:#0f7f81; }\nQLineEdit:focus,QTextEdit:focus,QComboBox:focus,QSpinBox:focus { border:1px solid #0f8b8d; background:#fbfefe; }\nQComboBox QAbstractItemView { background:#ffffff; color:#173b4f; border:1px solid #aebdc8; selection-background-color:#0f7f81; }\nQTextEdit#promptPreview { background:#f8fafc; color:#253746; border:1px solid #bdc9d2; border-radius:5px; padding:8px; font-family:"Cascadia Mono","Consolas"; }\nQTextEdit#aiResultEditor { background:#ffffff; color:#253746; border:1px solid #bdc9d2; border-radius:5px; padding:8px; }\nQListWidget { background:#ffffff; color:#344451; border:1px solid #bdc9d2; border-radius:5px; padding:3px; }\nQListWidget::item { padding:7px; border-bottom:1px solid #e8edf1; }\nQListWidget::item:selected { background:#cce8eb; color:white; }\nQPushButton { background:#e8eef2; color:#344956; border:1px solid #b9c6d0; border-radius:4px; padding:6px 10px; font-weight:700; }\nQPushButton:hover { background:#dce7eb; border-color:#7893a3; }\nQPushButton#primaryButton { background:#0f7f81; color:white; border:1px solid #0b6e70; border-radius:4px; font-size:10.5pt; font-weight:800; padding:8px; }\nQPushButton#primaryButton:hover { background:#0b6f71; }\nQPushButton#secondaryButton,QPushButton#smallButton { background:#edf2f5; color:#405764; border:1px solid #b9c6d0; border-radius:4px; }\nQGroupBox { color:#3e5564; border:1px solid #d0d9df; border-radius:5px; margin-top:10px; padding-top:9px; font-weight:700; }\nQGroupBox::title { subcontrol-origin:margin; left:9px; padding:0 5px; }\nQCheckBox { color:#3e5564; }\nQProgressBar { background:#e8eef1; color:#173b4f; border:1px solid #b9c6d0; border-radius:3px; text-align:center; }\nQProgressBar::chunk { background:#0f7f81; }\nQScrollBar:vertical { background:#e7ecef; width:9px; }\nQScrollBar::handle:vertical { background:#9fadb7; min-height:28px; border-radius:4px; }\nQSplitter::handle { background:#dfe5e9; }\nQSplitter::handle:horizontal { width:5px; }\nQSplitter::handle:horizontal:hover { background:#0f7f81; }\nQWidget#imageCard { background:#fbfcfd; border:1px solid #bdc9d2; border-radius:5px; }\nQLabel#imageThumbnail { background:#f2f5f7; border:1px solid #ccd6dd; border-radius:4px; }\n'

def get_gemini_api_key():
    api_key = os.getenv("GEMINI_API_KEY", "").strip() or os.getenv("GOOGLE_API_KEY", "").strip()
    if api_key:
        return api_key
    for env_name in (".env", "Try_API.env"):
        env_path = os.path.join(BASE_DIR, env_name)
        if not os.path.isfile(env_path):
            continue
        try:
            with open(env_path, "r", encoding="utf-8-sig") as env_file:
                for line in env_file:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, value = line.split("=", 1)
                    if key.strip() in {"GEMINI_API_KEY", "GOOGLE_API_KEY"}:
                        return value.strip().strip('"').strip("'")
        except OSError:
            pass
    return ""

def load_profiles():
    profiles = json.loads(json.dumps(DOMAIN_PROFILES, ensure_ascii=False))
    if os.path.isfile(CUSTOM_PROFILE_PATH):
        try:
            with open(CUSTOM_PROFILE_PATH, "r", encoding="utf-8") as file:
                profiles["Custom"] = json.load(file)
        except Exception:
            pass
    return profiles

def profile_for(name):
    profiles = load_profiles()
    return profiles.get(name, profiles["General QA"])

def normalize_pasted_tc_text(text):
    """브라우저/Excel/사내 시스템에서 한 줄로 복사된 TC를 번호 기준으로 정리한다."""
    text = str(text or "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u00a0", " ").replace("\u200b", "")
    text = text.replace("\t", " ")
    text = re.sub(r"[ ]{2,}", " ", text)
    text = re.sub(r" *\n *", "\n", text)

    # 이미 줄바꿈이 있어도 한 줄 안에 붙은 1., 2., 3-1., 4-2) 항목을 분리한다.
    # 0x2, 10.5, CAN ID 등 값 표기는 분리하지 않는다.
    numbered = re.compile(
        r"(?<![A-Za-z0-9_])"
        r"(?P<num>\d+(?:-\d+)*)"
        r"(?P<mark>[.)])"
        r"\s*"
    )
    output=[]
    for original_line in text.split("\n"):
        line=original_line.strip()
        if not line:
            if output and output[-1] != "": output.append("")
            continue
        matches=list(numbered.finditer(line))
        # 번호가 문장 시작 또는 공백/세미콜론 뒤에 있을 때만 항목 마커로 판단한다.
        valid=[]
        for m in matches:
            start=m.start()
            prev=line[start-1] if start>0 else ""
            number=m.group("num")
            if start==0 or prev.isspace() or prev in ";/|":
                # 소수점과 0x 계열 방지
                if start>=2 and line[start-2:start].lower()=="0x":
                    continue
                valid.append(m)
        if not valid:
            output.append(line)
            continue
        prefix=line[:valid[0].start()].strip(" ;/")
        if prefix: output.append(prefix)
        for idx,m in enumerate(valid):
            end=valid[idx+1].start() if idx+1<len(valid) else len(line)
            body=line[m.end():end].strip(" ;")
            item=f"{m.group('num')}. {body}".rstrip()
            output.append(item)

    # 일부 시스템은 'Step1 3 DK_Sleep...'처럼 번호의 점을 제거한다.
    # 대문자/한글로 시작하는 내용 앞의 독립 번호만 보수적으로 분리한다.
    final=[]
    missing_mark=re.compile(r"\s+(?P<num>\d+(?:-\d+)*)\s+(?=(?:[A-Z][A-Za-z0-9_./-]*|[가-힣]))")
    for line in output:
        if not line:
            if final and final[-1] != "": final.append("")
            continue
        parts=[]; last=0
        for m in missing_mark.finditer(line):
            before=line[max(0,m.start()-8):m.start()].lower()
            # Step 1, sec 10, 값 = 3 같은 수치는 항목 번호로 분리하지 않는다.
            if re.search(r"(?:step|sec|ms|0x|=|>=|<=)\s*$", before):
                continue
            parts.append(line[last:m.start()].strip())
            last=m.start('num')
        if parts:
            parts.append(line[last:].strip())
            final.extend(p for p in parts if p)
        else:
            final.append(line)

    cleaned=[]
    for line in final:
        if line=="" and (not cleaned or cleaned[-1]==""): continue
        cleaned.append(line)

    # 번호가 없는 긴 TC 문장은 마침표/세미콜론 뒤를 문장 단위로 정리한다.
    # 소수점(10.5), CAN ID, Signal 식별자는 분리하지 않는다.
    sentence_lines=[]
    for line in cleaned:
        if not line:
            if sentence_lines and sentence_lines[-1] != "": sentence_lines.append("")
            continue
        if len(line) >= 70 and not re.match(r"^\d+(?:-\d+)*[.)]", line):
            parts=re.split(r"(?<=[가-힣A-Za-z])\.\s+(?=[가-힣A-Z])|;\s+(?=(?:\d+(?:-\d+)*[.)]|[가-힣A-Z]))", line)
            sentence_lines.extend(part.strip() for part in parts if part.strip())
        else:
            sentence_lines.append(line)
    return "\n".join(sentence_lines).strip()

class RobustTcTextEdit(QTextEdit):
    """붙여넣을 때 TC 번호를 감지해 자동 줄바꿈하는 입력창."""
    def insertFromMimeData(self, source):
        if source and source.hasText():
            text=normalize_pasted_tc_text(source.text())
            cursor=self.textCursor()
            cursor.insertText(text)
            self.setTextCursor(cursor)
            return
        super().insertFromMimeData(source)

    def normalize_current_text(self):
        cursor=self.textCursor()
        position=cursor.position()
        normalized=normalize_pasted_tc_text(self.toPlainText())
        self.setPlainText(normalized)
        cursor=self.textCursor()
        cursor.setPosition(min(position,len(normalized)))
        self.setTextCursor(cursor)

class GeminiWorker(QThread):
    finished = Signal(str)
    failed = Signal(str)

    def __init__(self, prompt, attachment_paths):
        super().__init__()
        self.prompt = prompt
        self.attachment_paths = attachment_paths

    def run(self):
        try:
            api_key = get_gemini_api_key()

            if not api_key:
                raise ValueError(
                    "GEMINI_API_KEY가 없습니다. 프로그램 폴더의 Try_API.env 또는 .env 파일에 설정하세요."
                )

            client = genai.Client(api_key=api_key)
            contents = [self.prompt]

            for image_path in self.attachment_paths:
                if not os.path.isfile(image_path):
                    continue

                mime_type, _ = mimetypes.guess_type(image_path)
                if mime_type not in {
                    "image/png",
                    "image/jpeg",
                    "image/webp",
                    "image/gif",
                }:
                    continue

                with open(image_path, "rb") as image_file:
                    contents.append(
                        types.Part.from_bytes(
                            data=image_file.read(),
                            mime_type=mime_type,
                        )
                    )

            last_error = None

            for attempt in range(GEMINI_MAX_ATTEMPTS):
                try:
                    response = client.models.generate_content(
                        model=GEMINI_MODEL,
                        contents=contents,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                        ),
                    )
                    self.finished.emit(response.text)
                    return

                except Exception as error:
                    last_error = error
                    error_text = str(error).upper()

                    is_transient = (
                        "503" in error_text
                        or "UNAVAILABLE" in error_text
                        or "RESOURCE_EXHAUSTED" in error_text
                    )

                    if not is_transient or attempt == GEMINI_MAX_ATTEMPTS - 1:
                        raise

                    time.sleep(min(5 * (2 ** attempt), 60))

            raise last_error

        except Exception as error:
            self.failed.emit(f"{type(error).__name__}: {error}")

if __name__ == "__main__":
    raise SystemExit(main())
