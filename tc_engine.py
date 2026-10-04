"""
tc_engine.py - Automotive & General SW Validation Assistant Prompt & Execution Engine
Refactored to 100-Point Prompt Architecture (Multi-Domain Dynamic Few-Shot & Light Mask Protected)

[Revision] 도메인 레지스트리 기반 프롬프트 분기 + 버그 수정판
 - System Instruction / Few-Shot(Generation, Analysis) / Level Scope 를 도메인별로 분기
 - 프로필(current_domain_profile)에 key / few_shot / level_scope 를 넣으면 코드 수정 없이 덮어쓰기 가능
 - Light Mask 별칭 충돌, optimize_prompt_text 의 JSON 스키마 손상, Hex/단위 비교 오류 등 수정
"""

from __future__ import annotations
import json
import re
import textwrap
import hashlib
import math
import os
from collections import Counter
from typing import Dict, Any, List, Tuple, Optional
from PySide6.QtWidgets import QMessageBox, QApplication, QTextEdit
from PySide6.QtGui import QTextCursor, QPixmap, QTextImageFormat, QTextDocument
from PySide6.QtCore import Qt, QUrl

# ==============================================================================
# 1. 100점 프롬프트 아키텍처 핵심 상수 (System Instruction & Domain Few-Shots)
# ==============================================================================

SYSTEM_BASE_INSTRUCTION = """You are a Principal Software Quality Assurance (SQA) Engineer.
Your primary directive is to analyze software requirements or execution logs and output strictly structured JSON specifications.

[LANGUAGE & TERMINOLOGY POLICY]
1. ALL natural language descriptions inside JSON (e.g., tc_name, summary, steps, expected_results, pass_factors, fail_factors) MUST be written in KOREAN (한국어).
2. Domain technical identifiers (signal names, API endpoints, state values, protocol names, equipment names) MUST retain their standard English/Hex notations.

[CRITICAL OUTPUT GRAMMAR]
1. Output MUST be ONLY a single valid JSON object enclosed strictly within a ```json ... ``` markdown code block.
2. Do NOT output any introductory text, explanations, notes, or markdown headings outside the code block.
3. Enum Fields: Output ONLY a single selected string choice (e.g., "PASS"). NEVER output full choice literals like "PASS | FAIL | PARTIAL".
4. Array Symmetry: The 'expected_results' array MUST have the exact same number of elements as the 'steps' array, matching 1-to-1 by index.

[QUANTITATIVE PRECISION MANDATE]
1. Every Test Step and Expected Result MUST contain precise quantitative attributes:
   - Physical units / API Status Codes (ms, s, V, A, Hz, deg, HTTP 200, 404)
   - Logical/Comparison operators (==, !=, >=, <=, >, <)
   - Hexadecimal/Decimal/JSON state values (e.g., 0x01, 13.5V, true, false)
2. Strictly PROHIBITED ambiguous words: "약", "대략", "적절히", "확인할 것", "상응하는", "properly", "roughly", "about"."""

FEW_SHOT_TC_CREATION = """[FEW-SHOT EXAMPLE - TC GENERATION (AUTOMOTIVE)]
Input Feature: Driver Door Unlocking
Input Requirement: BCM must process 'SW_DrvDoorUnlock' hardwire input and transition 'Sig_DrvDoorLockSt' to UNLOCKED (0x01) within 150ms when Power State is IGN_ON (0x02).
Input Acceptance: Signal transition within 150ms and no DTC generated.

Expected Output:
```json
{
  "test_cases": [
    {
      "tc_id": "TC_GEN_001",
      "category": "Positive",
      "title": "운전석 도어 잠금해제 스위치 입력 반응시간 검증",
      "preconditions": [
        "1. 차량 전원 상태: IGN_ON (CAN Signal 'Power_State' == 0x02)",
        "2. BCM 공급 전압: 13.5V ± 0.2V 정상 범위 유지"
      ],
      "steps": [
        "1. Vector CANoe를 통해 CAN 신호 'Power_State' = 0x02 인가한다.",
        "2. 운전석 도어 잠금해제 하드와이어 스위치 'SW_DrvDoorUnlock'을 LOW (0V)로 50ms 동안 입력한다.",
        "3. CAN 버스 메시지 'BCM_DoorStatus'의 'Sig_DrvDoorLockSt' 신호 상태를 관찰한다."
      ],
      "expected_results": [
        "1. Power_State 신호가 0x02 (IGN_ON)로 정상 설정된다.",
        "2. 하드와이어 스위치 입력 트리가 정상 감지된다.",
        "3. 스위치 입력 시점으로부터 150ms 이내에 'Sig_DrvDoorLockSt' 신호값이 UNLOCKED (0x01)로 전이된다."
      ],
      "risk": "HIGH",
      "risk_description": "도어 잠금해제 신호 지연 시 비상 탈출 및 승하차 편의 기능에 중대한 결함 발생"
    }
  ]
}
```"""

FEW_SHOT_TC_CREATION_WEB_API = """[FEW-SHOT EXAMPLE - TC GENERATION (WEB/API)]
Input Feature: User Authentication API
Input Requirement: POST /api/v1/auth/login must validate credentials and return HTTP 200 with JWT token within 200ms for valid credentials.
Input Acceptance: Return HTTP 200 with valid JWT payload within 200ms.

Expected Output:
```json
{
  "test_cases": [
    {
      "tc_id": "TC_API_001",
      "category": "Positive",
      "title": "사용자 로그인 API 정상 응답 및 토큰 발급 검증",
      "preconditions": [
        "1. 인증 서비스 정상 가동 중 (HTTP Status 200)",
        "2. 테스트용 유효 계정(user@test.com) 사전 준비 완료"
      ],
      "steps": [
        "1. POST /api/v1/auth/login 요청 바디에 올바른 ID/PW를 실어 전송한다.",
        "2. 응답 HTTP Status Code 및 Header의 Content-Type을 확인한다.",
        "3. Response Body 내 accessToken 존재 여부 및 응답 시간을 확인한다."
      ],
      "expected_results": [
        "1. HTTP Status Code == 200 OK 수신",
        "2. Response Header Content-Type == application/json",
        "3. 200ms 이내 유효한 JWT accessToken이 포함된 JSON 응답 수신"
      ],
      "risk": "HIGH",
      "risk_description": "인증 실패 시 시스템 전체 접근 불능"
    }
  ]
}
```"""

FEW_SHOT_VALIDATION_ANALYSIS = """[FEW-SHOT EXAMPLE - VALIDATION ANALYSIS]
Input TC Name: TC_BCM_DOOR_001
Input Purpose: Verify IGN_ON state transition and door unlock signal delay < 150ms.
Input Evidence Log: Timestamp 10.000s: Power_State=0x02, Timestamp 10.050s: SW_DrvDoorUnlock=0V, Timestamp 10.130s: Sig_DrvDoorLockSt=0x01.

Expected Output:
```json
{
  "result": "PASS",
  "confidence": "HIGH",
  "confidence_reason": [
    "BLF 로그 분석 결과, 스위치 입력(10.050s) 후 80ms 시점(10.130s)에 Sig_DrvDoorLockSt 신호가 0x01로 전이됨을 확인함 (기대 기준: 150ms 이내)"
  ],
  "risk": "LOW",
  "summary": "운전석 도어 잠금해제 신호전이 응답시간이 80ms로 측정되어 요구사항(150ms 이내)을 충족함.",
  "evidence_status": "SUFFICIENT",
  "pass_factors": [
    "스위치 입력 후 80ms 시점에 신호 전이 완료 (80ms <= 150ms)",
    "CAN 버스 에러 프레임 미발생"
  ],
  "fail_factors": [],
  "evidence_coverage": {
    "required_items": 2,
    "verified_items": 2,
    "coverage_percent": 100,
    "missing_items": []
  },
  "observations": [
    "10.000s: Power_State == 0x02 수신",
    "10.050s: SW_DrvDoorUnlock == 0V 인가",
    "10.130s: Sig_DrvDoorLockSt == 0x01 전이 완료"
  ],
  "gaps": [],
  "recommended_verification": [
    "1. 전압 변동 조건(9.0V ~ 16.0V)에서의 응답시간 한계 검증 추가",
    "2. CAN 버스 로드율 80% 상태에서의 지연시간 비교 측정"
  ]
}
```"""

# ------------------------------------------------------------------------------
# 도메인 레지스트리: 새 도메인은 아래 딕셔너리에 항목만 추가하면 된다.
#   - DOMAIN_SYSTEM_ADDENDUM : 도메인 전용 용어/표기 규칙 (System Instruction 뒤에 결합)
#   - FEW_SHOTS              : 모드별 Few-Shot ("generation" | "analysis")
#   - DOMAIN_LEVEL_EXTRA     : Prompt Level 별 도메인 추가 지침
# 프로필(dict)에 "key", "few_shot", "level_scope" 가 있으면 그 값이 우선한다.
# ------------------------------------------------------------------------------

DEFAULT_DOMAIN_KEY = "automotive"

DOMAIN_SYSTEM_ADDENDUM = {
    "automotive": """[DOMAIN TERMINOLOGY - AUTOMOTIVE]
- CAN/LIN 시그널명(예: Sig_DrvDoorLockSt), ECU 전원 상태(예: IGN_ON, 0x02), UDS 서비스/NRC는 영문/Hex 원문 표기를 유지한다.
- 전압(V), 전류(A), 시간(ms), 주파수(Hz)는 단위와 허용 오차를 함께 명시한다.""",
    "web_api": """[DOMAIN TERMINOLOGY - WEB/API]
- HTTP Method, Endpoint, Status Code, Header, JSON Path 필드명은 영문 원문 표기를 유지한다.
- 응답시간(ms), 페이로드 크기(bytes), 재시도 횟수는 수치와 비교 연산자로 명시한다.""",
}

FEW_SHOT_VALIDATION_ANALYSIS_WEB_API = """[FEW-SHOT EXAMPLE - VALIDATION ANALYSIS (WEB/API)]
Input TC Name: TC_API_AUTH_001
Input Purpose: Verify POST /api/v1/auth/login returns HTTP 200 with JWT accessToken within 200ms for valid credentials.
Input Evidence Log: 12:00:00.000 POST /api/v1/auth/login sent, 12:00:00.145 HTTP 200 received, Content-Type: application/json, body.accessToken present (length 187).

Expected Output:
```json
{
  "result": "PASS",
  "confidence": "HIGH",
  "confidence_reason": [
    "요청 로그(12:00:00.000)와 응답 로그(12:00:00.145)를 비교한 결과 응답시간 145ms로 측정됨 (기대 기준: 200ms 이내)"
  ],
  "risk": "LOW",
  "summary": "로그인 API가 HTTP 200과 accessToken을 145ms에 반환하여 요구사항(200ms 이내)을 충족함.",
  "evidence_status": "SUFFICIENT",
  "pass_factors": [
    "HTTP Status Code == 200 수신",
    "응답시간 145ms <= 200ms",
    "Response Body에 accessToken 존재"
  ],
  "fail_factors": [],
  "evidence_coverage": {
    "required_items": 3,
    "verified_items": 3,
    "coverage_percent": 100,
    "missing_items": []
  },
  "observations": [
    "12:00:00.000: POST /api/v1/auth/login 요청 전송",
    "12:00:00.145: HTTP 200 응답 수신, Content-Type == application/json",
    "응답 Body: accessToken 길이 187"
  ],
  "gaps": [],
  "recommended_verification": [
    "1. 잘못된 비밀번호 입력 시 HTTP 401 반환 및 응답시간 <= 200ms 검증 추가",
    "2. 동시 요청 100건(RPS 100) 조건에서 p95 응답시간 비교 측정"
  ]
}
```"""

FEW_SHOTS = {
    "automotive": {
        "generation": FEW_SHOT_TC_CREATION,
        "analysis": FEW_SHOT_VALIDATION_ANALYSIS,
    },
    "web_api": {
        "generation": FEW_SHOT_TC_CREATION_WEB_API,
        "analysis": FEW_SHOT_VALIDATION_ANALYSIS_WEB_API,
    },
}

LEVEL_SCOPE_COMMON = {
    "Basic": (
        "- 정상 시나리오(Positive), 기본 실패 시나리오(Basic Negative), 핵심 상태 전이(State Transition) 위주로 생성한다.\n"
        "- 각 TC는 tc_id, category, title, preconditions, steps, expected_results, risk, risk_description을 포함한다."
    ),
    "Detailed": (
        "- Positive, Negative, Boundary Value, State Transition, Timeout, Retry, Recovery 관점의 테스트 시나리오를 포함한다.\n"
        "- 시간/수치/상태값 경계 조건(Boundary Conditions)을 정량적 수치로 구체화한다."
    ),
    "Expert": (
        "- 동등 분할(Equivalence Partitioning), 경계값 분석(BVA), 결정 테이블(Decision Table), Fault Injection 조건을 포함한다."
    ),
}

DOMAIN_LEVEL_EXTRA = {
    "automotive": {
        "Detailed": "- 전압/신호값 경계 조건을 정량적 수치로 포함한다.",
        "Expert": "- Communication Loss, Power Cycle 조건을 포함하고, 차량 통신 지연시간 및 세션 타임아웃 오차범위를 정량적으로 포함한다.",
    },
    "web_api": {
        "Detailed": "- 요청 필드 길이/범위, 페이로드 크기(bytes), 응답시간(ms) 경계 조건을 포함한다.",
        "Expert": "- 인증 만료, 동시 요청, Rate Limit(HTTP 429), 5xx 장애 후 복구 조건을 포함하고, 응답시간(ms) 오차범위를 정량적으로 포함한다.",
    },
}

# ------------------------------------------------------------------------------
# 추가 도메인: mobile_app / embedded_fw / db_backend / network_protocol
# 새 도메인을 더 늘릴 때도 아래와 같은 순서로 등록한다.
#   1) Few-Shot(generation, analysis)  2) DOMAIN_SYSTEM_ADDENDUM  3) DOMAIN_LEVEL_EXTRA
#   4) DOMAIN_DEFAULTS(프로필에 role/rules 가 없을 때 쓰는 기본값)  5) _DOMAIN_NAME_PATTERNS
# ------------------------------------------------------------------------------

FEW_SHOT_TC_CREATION_MOBILE_APP = """[FEW-SHOT EXAMPLE - TC GENERATION (MOBILE APP)]
Input Feature: Push Notification Deep Link
Input Requirement: When the user taps a push notification containing 'myapp://order/12345' while the app process is terminated, the app must cold start and display the Order Detail screen within 2000ms.
Input Acceptance: Order Detail screen shows order number 12345 within 2000ms and no crash or ANR occurs.

Expected Output:
```json
{
  "test_cases": [
    {
      "tc_id": "TC_APP_001",
      "category": "Positive",
      "title": "앱 종료 상태에서 푸시 알림 딥링크 진입 시 주문 상세 화면 표시 검증",
      "preconditions": [
        "1. 단말: Android 14 (Pixel 8), 앱 버전 3.2.0 설치 및 로그인 완료",
        "2. 앱 프로세스 종료 상태 (최근 앱 목록에서 제거), 네트워크 Wi-Fi 연결 (RTT <= 50ms)",
        "3. 알림 권한 'android.permission.POST_NOTIFICATIONS' == GRANTED"
      ],
      "steps": [
        "1. 테스트 서버에서 딥링크 'myapp://order/12345'를 포함한 푸시 알림을 단말로 전송한다.",
        "2. 알림 센터에 표시된 알림을 탭하고 탭 시점부터 화면 표시까지의 시간을 측정한다.",
        "3. 표시된 화면의 제목 요소 'tv_order_title'과 주문번호 텍스트를 확인한다."
      ],
      "expected_results": [
        "1. 푸시 알림이 10s 이내 수신되어 알림 센터에 1건 표시된다.",
        "2. 앱이 Cold Start로 실행되어 주문 상세 화면(OrderDetailActivity)이 탭 시점으로부터 2000ms 이내 표시된다.",
        "3. 'tv_order_title' 요소가 visible == true 이고 주문번호 == 12345 로 표시되며, 크래시와 ANR이 0건 발생한다."
      ],
      "risk": "MEDIUM",
      "risk_description": "딥링크 처리 실패 시 알림으로 유입된 사용자가 주문 정보에 접근하지 못해 전환율 저하 발생"
    }
  ]
}
```"""

FEW_SHOT_VALIDATION_ANALYSIS_MOBILE_APP = """[FEW-SHOT EXAMPLE - VALIDATION ANALYSIS (MOBILE APP)]
Input TC Name: TC_APP_LAUNCH_001
Input Purpose: Verify cold start to the Home screen is displayed within 2000ms on Android 14.
Input Evidence Log: Logcat 14:20:01.000 ActivityTaskManager START com.example.app/.MainActivity, 14:20:03.420 ActivityTaskManager Displayed com.example.app/.MainActivity: +2s420ms, no FATAL EXCEPTION or ANR entries, Device Pixel 8 Android 14.

Expected Output:
```json
{
  "result": "FAIL",
  "confidence": "HIGH",
  "confidence_reason": [
    "Logcat의 Displayed 로그에서 Cold Start 시간이 2420ms로 측정됨 (기대 기준: 2000ms 이내)"
  ],
  "risk": "MEDIUM",
  "summary": "Cold Start 시간이 2420ms로 측정되어 요구사항(2000ms 이내)을 420ms 초과함.",
  "evidence_status": "SUFFICIENT",
  "pass_factors": [
    "FATAL EXCEPTION 및 ANR 로그 0건"
  ],
  "fail_factors": [
    "Cold Start 2420ms > 2000ms (420ms 초과)"
  ],
  "evidence_coverage": {
    "required_items": 2,
    "verified_items": 2,
    "coverage_percent": 100,
    "missing_items": []
  },
  "observations": [
    "14:20:01.000: MainActivity START 기록",
    "14:20:03.420: MainActivity Displayed +2s420ms 기록",
    "단말/OS: Pixel 8, Android 14 확인"
  ],
  "gaps": [
    "단말 온도 및 백그라운드 프로세스 수 정보가 로그에 없음"
  ],
  "recommended_verification": [
    "1. 동일 조건에서 Cold Start를 10회 반복 측정하여 평균과 최대값이 2000ms 이내인지 확인",
    "2. 저사양 단말(RAM 4GB 이하) 및 Android 12 조건에서 Cold Start 시간 비교 측정"
  ]
}
```"""

FEW_SHOT_TC_CREATION_EMBEDDED_FW = """[FEW-SHOT EXAMPLE - TC GENERATION (EMBEDDED FIRMWARE)]
Input Feature: UART RX Interrupt Response
Input Requirement: The MCU (168MHz) must raise the UART2 RXNE interrupt after the last byte of an 8-byte frame is received at 115200bps, and the ISR must set GPIO PA5 to HIGH within 50us after the end of the last stop bit.
Input Acceptance: PA5 rises within 50us and no framing or overrun error occurs.

Expected Output:
```json
{
  "test_cases": [
    {
      "tc_id": "TC_FW_001",
      "category": "Positive",
      "title": "UART2 수신 완료 인터럽트 ISR의 GPIO 응답시간 검증",
      "preconditions": [
        "1. 보드 공급 전압 3.3V ± 0.1V, 시스템 클럭 168MHz, 펌웨어 v1.4.2 기록 완료",
        "2. UART2 설정: 115200bps, 8N1, GPIO PA5 초기 레벨 LOW (<= 0.4V)",
        "3. 로직 애널라이저 2채널(UART2_RX, PA5) 연결, 샘플링 레이트 24MHz"
      ],
      "steps": [
        "1. 보드를 Power On 하고 GPIO PA5의 레벨을 측정한다.",
        "2. 호스트에서 UART2_RX로 0x01~0x08 8바이트 프레임을 115200bps로 전송한다.",
        "3. 로직 애널라이저로 마지막 바이트(0x08)의 stop bit 종료 시점과 PA5 Rising Edge 시점 간 간격을 측정한다."
      ],
      "expected_results": [
        "1. PA5 레벨 == LOW (<= 0.4V)로 측정된다.",
        "2. 8바이트가 모두 수신되어 수신 카운터 == 8 이고, 에러 플래그 SR.FE == 0, SR.ORE == 0 이다.",
        "3. PA5 Rising Edge가 stop bit 종료로부터 50us 이내 발생하고 (간격 <= 50us), PA5 레벨 >= 2.4V 이다."
      ],
      "risk": "HIGH",
      "risk_description": "ISR 응답 지연 시 후속 프레임 수신 누락 및 제어 주기 위반 발생"
    }
  ]
}
```"""

FEW_SHOT_VALIDATION_ANALYSIS_EMBEDDED_FW = """[FEW-SHOT EXAMPLE - VALIDATION ANALYSIS (EMBEDDED FIRMWARE)]
Input TC Name: TC_FW_UART_001
Input Purpose: Verify GPIO PA5 rises within 50us after the end of the last stop bit of an 8-byte UART2 frame.
Input Evidence Log: Logic analyzer capture (24MHz) t=0.000000s end of last stop bit on UART2_RX, t=0.000032s PA5 rising edge to 3.3V. Serial log: rx_count=8, SR.FE=0, SR.ORE=0.

Expected Output:
```json
{
  "result": "PASS",
  "confidence": "HIGH",
  "confidence_reason": [
    "로직 애널라이저 캡처에서 마지막 stop bit 종료(0.000000s) 후 32us 시점(0.000032s)에 PA5 Rising Edge가 확인됨 (기대 기준: 50us 이내)"
  ],
  "risk": "LOW",
  "summary": "PA5 응답시간이 32us로 측정되어 요구사항(50us 이내)을 충족함.",
  "evidence_status": "SUFFICIENT",
  "pass_factors": [
    "PA5 응답시간 32us <= 50us",
    "rx_count == 8, SR.FE == 0, SR.ORE == 0"
  ],
  "fail_factors": [],
  "evidence_coverage": {
    "required_items": 2,
    "verified_items": 2,
    "coverage_percent": 100,
    "missing_items": []
  },
  "observations": [
    "0.000000s: UART2_RX 마지막 stop bit 종료",
    "0.000032s: PA5 Rising Edge, 레벨 3.3V",
    "시리얼 로그: rx_count == 8, SR.FE == 0, SR.ORE == 0"
  ],
  "gaps": [],
  "recommended_verification": [
    "1. 공급 전압 경계(3.0V, 3.6V) 조건에서 PA5 응답시간 측정 추가",
    "2. 연속 프레임 1000회 전송 시 최대 응답시간(us) 및 프레임 누락 건수 측정"
  ]
}
```"""

FEW_SHOT_TC_CREATION_DB_BACKEND = """[FEW-SHOT EXAMPLE - TC GENERATION (DB / BACKEND)]
Input Feature: Order Save Transaction
Input Requirement: When an order is created, one row in 'orders' and N rows in 'order_items' must be saved in a single transaction. If saving any order_items row fails, the whole transaction including 'orders' must be rolled back.
Input Acceptance: On failure, row counts of both tables do not increase and the API returns HTTP 422.

Expected Output:
```json
{
  "test_cases": [
    {
      "tc_id": "TC_DB_001",
      "category": "Negative",
      "title": "order_items 저장 실패 시 주문 트랜잭션 전체 롤백 검증",
      "preconditions": [
        "1. DB: PostgreSQL 15, 격리 수준 READ COMMITTED, orders 및 order_items 테이블 row 수 각각 0건",
        "2. order_items.product_id 에 FK 제약(products.id) 설정, products.id == 9999 레코드는 존재하지 않음"
      ],
      "steps": [
        "1. POST /api/v1/orders 요청에 items=[{product_id: 1, qty: 1}, {product_id: 9999, qty: 1}]를 담아 전송한다.",
        "2. 응답의 HTTP Status Code와 에러 코드를 확인한다.",
        "3. SELECT COUNT(*) FROM orders; 와 SELECT COUNT(*) FROM order_items; 를 실행한다."
      ],
      "expected_results": [
        "1. 서버 로그에 트랜잭션 BEGIN 이 1건 기록된다.",
        "2. HTTP Status Code == 422 이고 에러 코드 == FK_VIOLATION 이며 응답시간 <= 500ms 이다.",
        "3. orders COUNT == 0, order_items COUNT == 0 이고 서버 로그에 ROLLBACK 이 1건 기록된다."
      ],
      "risk": "HIGH",
      "risk_description": "부분 저장 시 주문 헤더만 존재하는 고아 데이터가 발생하여 정산 불일치 초래"
    }
  ]
}
```"""

FEW_SHOT_VALIDATION_ANALYSIS_DB_BACKEND = """[FEW-SHOT EXAMPLE - VALIDATION ANALYSIS (DB / BACKEND)]
Input TC Name: TC_DB_BATCH_001
Input Purpose: Verify the nightly settlement batch copies all rows from staging.settlement_raw to settlement within 600s with identical row counts.
Input Evidence Log: Batch log 02:00:00 JOB_START settle_daily, 02:08:41 JOB_END status=SUCCESS elapsed=521s. Query result: SELECT COUNT(*) FROM staging.settlement_raw = 1000000, SELECT COUNT(*) FROM settlement = 999987.

Expected Output:
```json
{
  "result": "FAIL",
  "confidence": "HIGH",
  "confidence_reason": [
    "소스 테이블 1,000,000건 대비 타깃 테이블 999,987건으로 13건 불일치함 (기대 기준: 소스 건수 == 타깃 건수)"
  ],
  "risk": "HIGH",
  "summary": "배치가 SUCCESS로 종료되었으나 타깃에 13건이 누락되어 정합성 요구사항을 충족하지 못함.",
  "evidence_status": "SUFFICIENT",
  "pass_factors": [
    "배치 처리시간 521s <= 600s",
    "배치 종료 상태 == SUCCESS"
  ],
  "fail_factors": [
    "건수 불일치: 1,000,000 != 999,987 (13건 누락)"
  ],
  "evidence_coverage": {
    "required_items": 3,
    "verified_items": 3,
    "coverage_percent": 100,
    "missing_items": []
  },
  "observations": [
    "02:00:00: JOB_START settle_daily 기록",
    "02:08:41: JOB_END status == SUCCESS, elapsed == 521s 기록",
    "COUNT 비교: staging.settlement_raw == 1000000, settlement == 999987"
  ],
  "gaps": [
    "누락된 13건의 키 목록과 스킵 또는 에러 처리 로그가 없음"
  ],
  "recommended_verification": [
    "1. NOT EXISTS 조회로 소스 대비 타깃에 없는 13건의 키를 추출하여 누락 원인 확인",
    "2. 배치 종료 시 소스/타깃 건수 비교 단계를 추가하고 불일치 건수 > 0 이면 status == FAILED 로 종료되는지 검증"
  ]
}
```"""

FEW_SHOT_TC_CREATION_NETWORK_PROTOCOL = """[FEW-SHOT EXAMPLE - TC GENERATION (NETWORK / PROTOCOL)]
Input Feature: MQTT Keep Alive
Input Requirement: With Keep Alive set to 60s and no other packets sent, the MQTT v3.1.1 client must send PINGREQ at 60s ± 1s intervals and receive PINGRESP from the broker within 1000ms.
Input Acceptance: PINGREQ interval is 60s ± 1s, PINGRESP delay is within 1000ms, and the TCP connection stays open.

Expected Output:
```json
{
  "test_cases": [
    {
      "tc_id": "TC_NET_001",
      "category": "Positive",
      "title": "Keep Alive 주기 PINGREQ 전송 및 PINGRESP 수신 검증",
      "preconditions": [
        "1. 브로커: Mosquitto 2.0, 포트 1883, 클라이언트 CONNECT 설정 Keep Alive == 60s, Clean Session == 1",
        "2. 네트워크 지연 <= 20ms, 패킷 손실률 == 0%, Wireshark로 클라이언트 NIC 패킷 캡처 시작"
      ],
      "steps": [
        "1. 클라이언트가 CONNECT 패킷을 전송하고 CONNACK 수신 후 구독과 발행 없이 대기한다.",
        "2. 패킷 캡처에서 CONNACK 이후 첫 PINGREQ(0xC0) 전송 시각을 확인한다.",
        "3. PINGREQ 전송 시각부터 PINGRESP(0xD0) 수신 시각까지의 지연을 측정한다."
      ],
      "expected_results": [
        "1. CONNACK Return Code == 0x00 을 수신하고 연결 상태 == Connected 이다.",
        "2. CONNACK 수신 후 PINGREQ(0xC0)가 59s <= 간격 <= 61s 범위에서 전송된다.",
        "3. PINGRESP(0xD0)가 PINGREQ 후 1000ms 이내 수신되고, TCP RST 및 FIN 패킷이 0건이다."
      ],
      "risk": "MEDIUM",
      "risk_description": "Keep Alive 실패 시 단말이 오프라인으로 오인되어 명령 수신 불가"
    }
  ]
}
```"""

FEW_SHOT_VALIDATION_ANALYSIS_NETWORK_PROTOCOL = """[FEW-SHOT EXAMPLE - VALIDATION ANALYSIS (NETWORK / PROTOCOL)]
Input TC Name: TC_NET_MQTT_001
Input Purpose: Verify the client sends PINGREQ at 60s +- 1s and receives PINGRESP within 1000ms with Keep Alive 60s.
Input Evidence Log: pcap No.12 t=0.000s CONNACK RC=0x00, No.31 t=60.012s PINGREQ (0xC0), No.32 t=60.047s PINGRESP (0xD0), no TCP RST or FIN in capture window 0s~120s.

Expected Output:
```json
{
  "result": "PASS",
  "confidence": "HIGH",
  "confidence_reason": [
    "pcap에서 CONNACK(0.000s) 후 60.012s에 PINGREQ가 전송되고 35ms 뒤(60.047s) PINGRESP가 수신됨 (기대 기준: 60s ± 1s, 1000ms 이내)"
  ],
  "risk": "LOW",
  "summary": "PINGREQ 간격 60.012s, PINGRESP 지연 35ms로 측정되어 요구사항을 충족함.",
  "evidence_status": "SUFFICIENT",
  "pass_factors": [
    "PINGREQ 간격 60.012s (59s <= 간격 <= 61s)",
    "PINGRESP 지연 35ms <= 1000ms",
    "캡처 구간 0s~120s 동안 TCP RST 및 FIN 0건"
  ],
  "fail_factors": [],
  "evidence_coverage": {
    "required_items": 3,
    "verified_items": 3,
    "coverage_percent": 100,
    "missing_items": []
  },
  "observations": [
    "0.000s: CONNACK Return Code == 0x00 수신",
    "60.012s: PINGREQ (0xC0) 전송",
    "60.047s: PINGRESP (0xD0) 수신"
  ],
  "gaps": [],
  "recommended_verification": [
    "1. 패킷 손실률 5% 조건에서 PINGRESP 지연 및 재전송 횟수 측정 추가",
    "2. 브로커 응답 차단 시 Keep Alive의 1.5배(90s) 이내 연결 종료 및 재연결 동작 검증 추가"
  ]
}
```"""

FEW_SHOTS.update({
    "mobile_app": {
        "generation": FEW_SHOT_TC_CREATION_MOBILE_APP,
        "analysis": FEW_SHOT_VALIDATION_ANALYSIS_MOBILE_APP,
    },
    "embedded_fw": {
        "generation": FEW_SHOT_TC_CREATION_EMBEDDED_FW,
        "analysis": FEW_SHOT_VALIDATION_ANALYSIS_EMBEDDED_FW,
    },
    "db_backend": {
        "generation": FEW_SHOT_TC_CREATION_DB_BACKEND,
        "analysis": FEW_SHOT_VALIDATION_ANALYSIS_DB_BACKEND,
    },
    "network_protocol": {
        "generation": FEW_SHOT_TC_CREATION_NETWORK_PROTOCOL,
        "analysis": FEW_SHOT_VALIDATION_ANALYSIS_NETWORK_PROTOCOL,
    },
})

DOMAIN_SYSTEM_ADDENDUM.update({
    "mobile_app": """[DOMAIN TERMINOLOGY - MOBILE APP]
- OS/버전(Android 14, iOS 17), 화면/컴포넌트 ID, 권한명(예: android.permission.POST_NOTIFICATIONS), 딥링크 URI, API Endpoint는 영문 원문 표기를 유지한다.
- 응답시간(ms), 앱 실행시간(Cold/Warm Start), 메모리(MB), 배터리 잔량(%), 네트워크 상태(Wi-Fi/LTE/Offline)를 수치와 비교 연산자로 명시한다.""",
    "embedded_fw": """[DOMAIN TERMINOLOGY - EMBEDDED FIRMWARE / HW INTERFACE]
- 레지스터 주소(예: 0x40020000), 비트 필드, GPIO 핀명(예: PA5), 인터럽트/타이머 식별자, 통신 버스(I2C/SPI/UART)는 영문/Hex 원문 표기를 유지한다.
- 전압(V), 전류(mA), 클럭(MHz), 타이밍(us/ms), 전송속도(bps)는 허용 오차와 함께 명시한다.""",
    "db_backend": """[DOMAIN TERMINOLOGY - DB / BACKEND DATA PROCESSING]
- 테이블/컬럼명, SQL 구문, 트랜잭션 격리 수준(예: READ COMMITTED), 큐/토픽명, 배치 Job ID는 영문 원문 표기를 유지한다.
- 처리 건수(rows), 처리 시간(ms/s), 처리량(TPS), 데이터 크기(MB), 재시도 횟수를 수치와 비교 연산자로 명시한다.""",
    "network_protocol": """[DOMAIN TERMINOLOGY - NETWORK / COMMUNICATION PROTOCOL]
- 프로토콜명(TCP, UDP, MQTT, Modbus, BLE 등), 포트 번호, 패킷/프레임 필드명, 메시지 타입, 상태 머신 상태명, 에러 코드는 영문/Hex 원문 표기를 유지한다.
- 지연시간(ms), 패킷 손실률(%), 처리량(Mbps), 타임아웃(s), 재전송 횟수를 허용 오차와 함께 명시한다.""",
})

DOMAIN_LEVEL_EXTRA.update({
    "mobile_app": {
        "Detailed": "- OS 버전, 화면 방향(Portrait/Landscape), 네트워크 상태(Wi-Fi/LTE/Offline) 조합의 경계 조건을 포함한다.",
        "Expert": "- 권한 거부/철회, 백그라운드 전환 및 프로세스 종료 후 복구, 푸시 알림 수신, 저메모리 및 배터리 잔량 15% 이하 조건을 포함하고, 앱 실행시간(ms) 오차범위를 정량적으로 포함한다.",
    },
    "embedded_fw": {
        "Detailed": "- 전원 전압, 클럭, 온도 경계 조건과 타이머/인터럽트 타이밍 경계를 정량적 수치로 포함한다.",
        "Expert": "- 전원 Brown-out, Watchdog Reset, 인터럽트 중첩, 버스 오류(NACK, Framing Error), 플래시 쓰기 중 전원 차단 조건을 포함하고, 타이밍 오차범위(us)를 정량적으로 포함한다.",
    },
    "db_backend": {
        "Detailed": "- 데이터 건수(0건, 1건, 최대 건수), 컬럼 길이/범위, NULL 및 중복 키 경계 조건을 포함한다.",
        "Expert": "- 동시 트랜잭션 충돌(Deadlock, Lock Timeout), 롤백, 부분 실패 후 재처리(멱등성), 1,000,000건 이상 대용량 배치 조건을 포함하고, 처리시간(ms)과 건수 일치 기준을 정량적으로 포함한다.",
    },
    "network_protocol": {
        "Detailed": "- 패킷 크기(최소/최대 MTU), 타임아웃, 재전송 횟수, 지연 및 손실률 경계 조건을 정량적 수치로 포함한다.",
        "Expert": "- 패킷 손실/중복/순서 뒤바뀜, 연결 끊김 후 재연결, 잘못된 필드 값(Malformed Packet), 프로토콜 상태 머신의 비정상 전이 조건을 포함하고, 지연시간과 타임아웃 오차범위를 정량적으로 포함한다.",
    },
})

# 프로필(current_domain_profile)에 role / *_rules 가 없을 때 사용하는 도메인 기본값.
# 프로필에 값이 있으면 프로필이 항상 우선한다.
DOMAIN_DEFAULTS = {
    "mobile_app": {
        "role": "Mobile App (Android/iOS) Quality Assurance Specialist",
        "generation_rules": [
            "대상 OS/버전과 단말 조건(해상도, 화면 방향, 네트워크 상태)을 Precondition에 명시한다.",
            "화면 전환, 권한 요청 팝업, 백그라운드/포그라운드 전환, 푸시 알림 시나리오를 구분하여 Step으로 작성한다.",
            "UI 확인은 화면 요소 ID/텍스트와 표시 상태(visible, enabled)를 기준으로 기대 결과를 작성한다.",
            "네트워크 단절/복구와 앱 강제 종료 후 재실행 시 데이터 유지 여부를 Negative/Recovery 시나리오에 포함한다.",
        ],
        "analysis_rules": [
            "Logcat/Xcode Console 로그, 크래시 리포트, 스크린샷의 시각을 기준으로 관찰 사실과 추론을 구분한다.",
            "OS 버전과 단말 모델이 로그에서 확인되지 않으면 재현 조건 부족으로 gaps에 기록한다.",
            "ANR, Crash, 메모리 경고 등 이상 이벤트는 발생 시각과 직전 사용자 조작을 함께 정리한다.",
        ],
        "review_rules": [
            "OS/단말/네트워크 조건이 누락된 TC는 재현 불가 TC로 지적한다.",
            "'정상 표시', '잘 동작' 같은 모호한 기대 결과를 화면 요소 상태와 수치(ms, MB)로 보정한다.",
            "권한, 백그라운드, 오프라인 경계 조건 누락 여부를 점검한다.",
        ],
    },
    "embedded_fw": {
        "role": "Embedded Firmware / Hardware Interface Quality Assurance Specialist",
        "generation_rules": [
            "대상 보드, 펌웨어 버전, 전원 전압, 클럭, 측정 장비(오실로스코프, 로직 애널라이저)를 Precondition에 명시한다.",
            "입력 신호(GPIO, 버스 데이터)와 출력 관찰(레지스터 값, 핀 레벨, 버스 응답)을 별도 Step으로 분리한다.",
            "타이밍 요구는 측정 지점, 기준 에지(Rising/Falling), 허용 오차(us/ms)를 함께 기술한다.",
            "전원 Cycle, Watchdog, Reset 이후 초기값 복귀 시나리오를 Recovery로 포함한다.",
        ],
        "analysis_rules": [
            "시리얼 로그, 레지스터 덤프, 파형 캡처의 타임스탬프를 기준으로 관찰 사실과 추론을 구분한다.",
            "측정 장비 설정(샘플링 레이트, 트리거 조건)이 확인되지 않으면 gaps에 기록한다.",
            "Reset 원인 레지스터, 폴트 로그, 스택 덤프가 있으면 직접 증거로 우선 사용한다.",
        ],
        "review_rules": [
            "측정 지점, 장비, 허용 오차가 없는 타이밍 기대 결과는 측정 불가 TC로 지적한다.",
            "전원/클럭/온도 경계 조건과 Reset 후 복구 시나리오 누락을 점검한다.",
            "레지스터 값은 Hex와 비트 필드 의미를 함께 기술하도록 보정한다.",
        ],
    },
    "db_backend": {
        "role": "Database / Backend Data Processing Quality Assurance Specialist",
        "generation_rules": [
            "초기 데이터 상태(테이블별 row 수, 기준 키 값)와 DB/서비스 버전을 Precondition에 명시한다.",
            "입력 데이터, 처리 후 DB 상태(SELECT 결과의 row 수와 컬럼 값), 처리 로그를 각각 별도 Step으로 분리한다.",
            "트랜잭션 커밋/롤백, 중복 요청(멱등성), 부분 실패 시 데이터 정합성을 Negative 시나리오에 포함한다.",
            "건수와 합계 같은 정합성 기준은 소스 대비 타깃 비교식(==)으로 기술한다.",
        ],
        "analysis_rules": [
            "쿼리 로그, 실행 계획, 애플리케이션 로그의 타임스탬프를 기준으로 관찰 사실과 추론을 구분한다.",
            "처리 전/후 row 수 비교 증거가 없으면 정합성 판정은 INCONCLUSIVE로 처리하고 gaps에 기록한다.",
            "Deadlock, Lock Timeout, 롤백 로그는 발생 시각과 대상 테이블을 함께 정리한다.",
        ],
        "review_rules": [
            "초기 데이터 상태가 없는 TC는 재현 불가 TC로 지적한다.",
            "'정상 저장', '데이터 일치' 같은 모호한 기대 결과를 row 수와 컬럼 값 비교식으로 보정한다.",
            "NULL, 중복 키, 롤백, 동시성 경계 조건 누락을 점검한다.",
        ],
    },
    "network_protocol": {
        "role": "Network / Communication Protocol Quality Assurance Specialist",
        "generation_rules": [
            "프로토콜 버전, 포트, 단말/서버 역할, 네트워크 조건(대역폭, 지연, 손실률)을 Precondition에 명시한다.",
            "송신 메시지(필드 값 Hex)와 수신 응답(메시지 타입, 상태 코드)을 별도 Step으로 분리하고 패킷 캡처 확인 지점을 명시한다.",
            "타임아웃, 재전송, 연결 재수립 동작은 횟수와 시간(ms/s) 기준으로 기술한다.",
            "잘못된 필드 값, 길이 초과, 순서 오류 패킷에 대한 Negative 시나리오를 포함한다.",
        ],
        "analysis_rules": [
            "패킷 캡처(pcap)와 프로토콜 로그의 타임스탬프를 기준으로 요청-응답 지연을 계산하고 관찰 사실과 추론을 구분한다.",
            "캡처 구간과 필터 조건이 확인되지 않으면 패킷 누락 가능성을 gaps에 기록한다.",
            "재전송, 연결 리셋(RST), 타임아웃 이벤트는 발생 시각과 시퀀스 번호를 함께 정리한다.",
        ],
        "review_rules": [
            "프로토콜 버전/포트/네트워크 조건이 없는 TC는 재현 불가 TC로 지적한다.",
            "'정상 통신', '응답 수신' 같은 모호한 기대 결과를 메시지 타입, 필드 값, 지연시간(ms)으로 보정한다.",
            "타임아웃, 재전송, 재연결, Malformed Packet 경계 조건 누락을 점검한다.",
        ],
    },
}

SEQUENCE_MODE_RULES = {
    "AI 자동 생성": "- 요구사항을 분석해 Step 순서를 직접 구성하고, steps와 expected_results를 1:1로 대응시킨다.",
    "사용자 흐름 우선": "- 사용자가 지정한 핵심 흐름과 순서를 유지하며 상세 Step으로 확장하고, steps와 expected_results를 1:1로 대응시킨다.",
    "사용자 순서 고정": "- 사용자 지정 순서와 항목 수를 변경하지 않고, steps와 expected_results를 1:1로 대응시킨다.",
}

# 프로필에 "key" 가 없을 때 이름으로 도메인을 추정한다. 위에서부터 먼저 맞는 항목이 선택된다.
_DOMAIN_NAME_PATTERNS = [
    ("automotive", re.compile(r"\b(?:automotive|vehicle|ecu|bcm|can|lin|uds|autosar)\b|자동차|차량|전장", re.I)),
    ("mobile_app", re.compile(r"\b(?:mobile|android|ios)\b|모바일|안드로이드", re.I)),
    ("db_backend", re.compile(r"\b(?:db|database|sql|etl|batch)\b|데이터베이스|데이터\s*처리|배치", re.I)),
    ("network_protocol", re.compile(r"\b(?:network|protocol|tcp|udp|mqtt|modbus|ble|bluetooth)\b|네트워크|프로토콜|통신", re.I)),
    ("embedded_fw", re.compile(r"\b(?:embedded|firmware|mcu|rtos|hw|hardware)\b|펌웨어|임베디드|하드웨어", re.I)),
    ("web_api", re.compile(r"\b(?:web|api|rest|http)\b|웹", re.I)),
]
_SECTION_HEADER_RE = re.compile(r'^\[{1,2}[^\[\]"]+\]{1,2}$')
_NUMBERED_PREFIX_RE = re.compile(r"^\d+[.)]\s")
_NUMBERED_ITEM_RE = re.compile(
    r"^(?P<step>Step\s*)?(?P<num>\d+(?:[-.]\d+)*)(?P<sep>\s*[.)：:](?!\d)\s*|\s+|$)(?P<rest>.*)$",
    re.I,
)
_DECIMAL_RE = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$")
_HEX_RE = re.compile(r"^[+-]?0[xX][0-9A-Fa-f]+$")
_UNIT_NUMBER_RE = re.compile(
    r"^([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*(?:ms|us|µs|s|mv|v|ma|a|khz|hz|deg|%)$", re.I
)

MAX_PROMPT_CHARS = 12000


# ==============================================================================
# 2. TcEngineMixin 구현부 (100% 비즈니스 로직 및 인터페이스 호환)
# ==============================================================================

class TcEngineMixin:
    """
    Validation Assistant의 Prompt Generation, BLF/DBC Local Validation, 
    Text Optimization 및 Review Pipeline을 구현한 엔진 믹스인 클래스.
    """

    def update_tc_generation_sequence_mode(self, mode: str):
        if mode not in {"AI 자동 생성", "사용자 흐름 우선", "사용자 순서 고정"}:
            mode = "사용자 흐름 우선"
        self.tc_generation_sequence_mode = mode
        is_fixed = mode == "사용자 순서 고정"
        if hasattr(self, "tc_generation_sequence_btn"):
            self.tc_generation_sequence_btn.setToolTip(
                "입력한 번호 순서를 변경하지 않습니다." if is_fixed
                else "핵심 흐름만 입력해도 AI가 상세 Step으로 확장합니다."
            )

    def store_tc_generation_page_values(self):
        if not hasattr(self, "purpose"):
            return
        if self.tc_generation_page == "execution":
            self.tc_generation_preconditions = self.purpose.toPlainText()
            self.tc_generation_observations = self.expected.toPlainText()
        elif self.tc_generation_page == "sequence":
            self.tc_generation_sequence = self.purpose.toPlainText()
            self.tc_generation_checkpoints = self.expected.toPlainText()
        else:
            self.tc_generation_requirement = self.purpose.toPlainText()
            self.tc_generation_acceptance = self.expected.toPlainText()

    def load_tc_generation_page_values(self):
        if self.tc_generation_page == "execution":
            self.purpose_label.setText("시험 전 상태 / 시험 환경")
            self.expected_label.setText("가능한 조작 / 제한 조건")
            self.purpose.setPlaceholderText("차량 초기 상태, Door 상태, Key 등록 상태, CANoe/DBC 환경을 번호로 입력하세요.")
            self.expected.setPlaceholderText("가능한 조작과 불가능한 조작, 시험 제한 조건을 입력하세요.")
            self.purpose.setPlainText(self.tc_generation_preconditions)
            self.expected.setPlainText(self.tc_generation_observations)
        elif self.tc_generation_page == "sequence":
            self.purpose_label.setText("시험 수행 순서")
            self.expected_label.setText("확인 Signal / 관찰 항목")
            self.purpose.setPlaceholderText(
                "번호 순서로 입력하세요. 예:\n"
                "1. 운전석 도어를 Open한다.\n"
                "2. 운전석 도어를 Close한다.\n"
                "3. 운전석 도어를 Lock한다.\n"
                "4. 모바일 기기를 접근 영역으로 이동한다."
            )
            self.expected.setPlaceholderText(
                "각 단계에서 확인할 Signal 또는 물리 상태를 입력하세요. 예:\n"
                "- Door Lock 초기 상태\n"
                "- Digital Key 위치 상태\n"
                "- 인증 결과\n"
                "- 실제 도어 Open 가능 여부"
            )
            self.purpose.setPlainText(self.tc_generation_sequence)
            self.expected.setPlainText(self.tc_generation_checkpoints)
        else:
            self.purpose_label.setText("기능 동작 / 요구사항")
            self.expected_label.setText("정상 동작 / 합격 기준")
            self.purpose.setPlaceholderText("기능 Trigger, 성공/실패 및 Recovery 흐름을 입력하세요.")
            self.expected.setPlaceholderText("관찰 또는 측정 가능한 PASS 기준을 입력하세요.")
            self.purpose.setPlainText(self.tc_generation_requirement)
            self.expected.setPlainText(self.tc_generation_acceptance)
        self.tc_generation_basic_btn.setChecked(self.tc_generation_page == "basic")
        self.tc_generation_execution_btn.setChecked(self.tc_generation_page == "execution")
        self.tc_generation_sequence_btn.setChecked(self.tc_generation_page == "sequence")
        if hasattr(self, "tc_generation_sequence_mode_combo"):
            self.tc_generation_sequence_mode_combo.blockSignals(True)
            self.tc_generation_sequence_mode_combo.setCurrentText(self.tc_generation_sequence_mode)
            self.tc_generation_sequence_mode_combo.blockSignals(False)

    def switch_tc_generation_page(self, page: str):
        if "TC Generation" not in self.mode.currentText():
            return
        page = page if page in {"basic", "execution", "sequence"} else "basic"
        if page != self.tc_generation_page:
            self.store_tc_generation_page_values()
            self.tc_generation_page = page
            self.load_tc_generation_page_values()

    def get_tc_generation_prompt_inputs(self) -> Tuple[str, str]:
        self.store_tc_generation_page_values()
        requirement = self.tc_generation_requirement.strip()
        if self.tc_generation_preconditions.strip():
            requirement += "\n\n[Preconditions / Test Environment]\n" + self.tc_generation_preconditions.strip()
        if self.tc_generation_observations.strip():
            requirement += "\n\n[Available Operations / Constraints]\n" + self.tc_generation_observations.strip()
        if self.tc_generation_sequence.strip():
            requirement += "\n\n[Mandatory Test Execution Sequence]\n" + self.tc_generation_sequence.strip()
        if self.tc_generation_checkpoints.strip():
            requirement += "\n\n[Signals and Observation Checkpoints]\n" + self.tc_generation_checkpoints.strip()

        if not requirement.strip():
            QMessageBox.warning(
                self,
                "입력 확인",
                "기능 동작/요구사항, 시험 전 상태, 수행 순서 중 하나 이상을 입력하세요."
            )
            return "", self.tc_generation_acceptance.strip()

        mode = self.tc_generation_sequence_mode
        sequence_exists = bool(self.tc_generation_sequence.strip())
        if mode == "사용자 순서 고정" and not sequence_exists:
            QMessageBox.warning(
                self,
                "수행 순서 입력 확인",
                "'사용자 순서 고정' 모드에서는 수행 순서를 번호로 입력해야 합니다."
            )
            return "", self.tc_generation_acceptance.strip()

        if mode == "AI 자동 생성" or (mode == "사용자 흐름 우선" and not sequence_exists):
            sequence_instruction = """
[Sequence Generation Mode: AI AUTO]
- 요구사항, 시험 전 상태, 가능한 조작과 제한 조건을 분석하여 전체 시험 수행 순서를 생성한다.
- 초기 상태 설정 -> 입력/조작(요청) -> 기능 Trigger -> 상태/응답 확인 -> 최종 동작 확인 순으로 구성한다.
- 입력/조작과 상태/응답 확인을 각각 독립된 별도 Step으로 작성한다.
- 수치 조건이 명시되지 않은 시간, 전압, 건수, 횟수 등은 TBD 표기를 유지한다.
"""
        elif mode == "사용자 흐름 우선":
            sequence_instruction = """
[Sequence Generation Mode: USER FLOW FIRST]
- [Mandatory Test Execution Sequence]의 핵심 흐름과 순서를 완벽히 유지한다.
- 축약된 흐름을 실제 수행 가능한 상세 Step으로 확장하되, 조작과 관찰 항목을 분리한다.
- 사용자가 지정한 핵심 조작은 절대로 삭제하거나 순서를 바꾸지 않는다.
"""
        else:
            sequence_instruction = """
[Sequence Generation Mode: USER SEQUENCE FIXED]
- [Mandatory Test Execution Sequence]의 번호, 항목 수, 순서를 변경하지 않는다.
- 사용자 Step을 추가, 삭제, 병합, 분할 또는 재배열하지 않는다.
- 각 Step 문장만 정량적 표현으로 명확히 정리하고 동일 번호의 Expected Result를 생성한다.
"""
        requirement += "\n" + sequence_instruction.strip()
        return requirement.strip(), self.tc_generation_acceptance.strip()

    def _numbered_items(self, text: str) -> List[Tuple[str, str]]:
        items = []
        for raw in str(text or "").splitlines():
            line = raw.strip()
            if not line:
                continue
            match = _NUMBERED_ITEM_RE.match(line)
            # "13.5V 인가", "150ms 이내" 같은 수치 시작 문장은 번호로 보지 않는다.
            is_numbered = bool(
                match
                and (
                    match.group("step")
                    or match.group("sep").strip()
                    or re.search(r"[-.]", match.group("num"))
                )
            )
            if is_numbered:
                items.append((match.group("num"), match.group("rest").strip() or line))
            else:
                items.append((str(len(items) + 1), line))
        return items

    def update_validation_pair_status(self):
        if not hasattr(self, 'validation_pair_status'):
            return
        pc = self._numbered_items(self.validation_preconditions.toPlainText()) if hasattr(self, 'validation_preconditions') else []
        st = self._numbered_items(self.validation_steps.toPlainText()) if hasattr(self, 'validation_steps') else []
        ex = self._numbered_items(self.validation_expected_results.toPlainText()) if hasattr(self, 'validation_expected_results') else []
        ac = self._numbered_items(self.validation_actual_results.toPlainText()) if hasattr(self, 'validation_actual_results') else []
        step_ids = {n for n, _ in st}
        expected_ids = {n for n, _ in ex}
        paired = len(step_ids & expected_ids)
        missing_ex = len(step_ids - expected_ids)
        fourth_name = "Review 기준" if hasattr(self, "mode") and "TC Review" in self.mode.currentText() else "Actual"
        self.validation_pair_status.setText(
            f"Precondition {len(pc)} | Step {len(st)} | Expected {len(ex)} | {fourth_name} {len(ac)} | 대응 {paired} | Expected 누락 {missing_ex}"
        )
        color = '#16836f' if missing_ex == 0 and st else '#a56a08'
        self.validation_pair_status.setStyleSheet(f"color:{color}; font-size:8pt; padding:2px 4px;")

    def normalize_active_validation_tab(self):
        if not hasattr(self, "validation_tabs"):
            return
        editor = self.validation_tabs.currentWidget()
        if hasattr(editor, "normalize_current_text"):
            editor.normalize_current_text()
        self.update_validation_pair_status()

    def sync_structured_validation_to_legacy_fields(self):
        if not hasattr(self, 'validation_preconditions'):
            return
        mode = self.mode.currentText() if hasattr(self, "mode") else ""
        pre = self.validation_preconditions.toPlainText().strip()
        steps = self.validation_steps.toPlainText().strip()
        expected = self.validation_expected_results.toPlainText().strip()
        fourth = self.validation_actual_results.toPlainText().strip()

        purpose_blocks = []
        if pre:
            purpose_blocks.append('[Preconditions]\n' + pre)
        if steps:
            purpose_blocks.append('[Test Steps]\n' + steps)

        if "TC Review" in mode:
            expected_blocks = []
            if expected:
                expected_blocks.append('[Expected Results]\n' + expected)
            if fourth:
                expected_blocks.append('[Review Criteria]\n' + fourth)
            self.purpose.setPlainText('\n\n'.join(purpose_blocks))
            self.expected.setPlainText('\n\n'.join(expected_blocks))
        else:
            if expected:
                purpose_blocks.append('[Expected Results]\n' + expected)
            self.purpose.setPlainText('\n\n'.join(purpose_blocks))
            self.expected.setPlainText(fourth)
        self.update_validation_pair_status()

    def extract_tc_blf_validation_rules(self) -> List[Dict[str, Any]]:
        if hasattr(self, 'validation_expected_results') and 'Validation Analysis' in self.mode.currentText():
            source = self.validation_expected_results.toPlainText()
        else:
            source = self.purpose.toPlainText() + '\n' + self.expected.toPlainText()
        pattern = re.compile(r"(?<![A-Za-z0-9_])(?P<signal>[A-Za-z][A-Za-z0-9_]{2,})\s*(?P<op>==|!=|>=|<=|=|>|<)\s*(?P<value>[A-Za-z0-9_.+\-]+)")
        rules = []
        current = 'UNSPECIFIED'
        for line_no, line in enumerate(source.splitlines(), 1):
            sm = re.search(r"(?:Step|Expected(?:\s*Result)?|Result|단계)\s*[-:#.]?\s*(\d+(?:[-.]\d+)*)", line, re.I)
            if sm:
                current = sm.group(1)
            for m in pattern.finditer(line):
                rules.append({
                    'rule_id': f'R{len(rules)+1:03d}',
                    'step': current,
                    'source_line': line_no,
                    'source_text': line.strip(),
                    'signal': m.group('signal'),
                    'operator': m.group('op'),
                    'expected': m.group('value')
                })
        return rules

    def _normalize_signal_match_name(self, value: Any) -> str:
        text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(value or ""))
        text = re.sub(r"[^A-Za-z0-9]+", " ", text).lower().strip()
        aliases = {"req": "request", "sts": "status", "stat": "status", "res": "result", "rsp": "response", "cmd": "command", "drv": "driver", "psg": "passenger", "veh": "vehicle"}
        return " ".join(aliases.get(token, token) for token in text.split())

    def resolve_tc_signal_to_dbc(self, requested_name: str) -> Dict[str, Any]:
        requested = str(requested_name or "").strip()
        catalog, _ = self.build_dbc_context_catalog()
        if not requested or not catalog:
            return {"requested": requested, "resolved": requested, "score": 0.0, "status": "UNRESOLVED"}
        by_name = {}
        for item in catalog:
            by_name.setdefault(item.get("signal", ""), item)
        for function_name, signal_name in (getattr(self, "signal_function_mapping", None) or {}).items():
            if requested.lower() in {str(function_name).lower(), str(signal_name).lower()} and signal_name in by_name:
                return {"requested": requested, "resolved": signal_name, "score": 1.0, "status": "DIRECT_MAPPING"}
        wanted_norm = self._normalize_signal_match_name(requested)
        exact = [name for name in by_name if self._normalize_signal_match_name(name) == wanted_norm]
        if len(exact) == 1:
            return {"requested": requested, "resolved": exact[0], "score": 1.0, "status": "NORMALIZED_EXACT"}
        wanted_tokens = set(wanted_norm.split())
        ranked = []
        for name, item in by_name.items():
            candidate_norm = self._normalize_signal_match_name(name)
            candidate_tokens = set(candidate_norm.split())
            if not wanted_tokens or not candidate_tokens:
                continue
            common = wanted_tokens & candidate_tokens
            union = wanted_tokens | candidate_tokens
            containment = len(common) / max(1, min(len(wanted_tokens), len(candidate_tokens)))
            jaccard = len(common) / max(1, len(union))
            substring = 1.0 if wanted_norm in candidate_norm or candidate_norm in wanted_norm else 0.0
            context_score = self.score_dbc_context_candidate(requested, item)
            score = 0.45 * containment + 0.25 * jaccard + 0.20 * context_score + 0.10 * substring
            ranked.append((score, name, item))
        ranked.sort(key=lambda row: row[0], reverse=True)
        if not ranked:
            return {"requested": requested, "resolved": requested, "score": 0.0, "status": "UNRESOLVED"}
        best_score, best_name, best_item = ranked[0]
        second = ranked[1][0] if len(ranked) > 1 else 0.0
        margin = best_score - second
        base = {
            "requested": requested,
            "resolved": best_name,
            "score": round(best_score, 3),
            "margin": round(margin, 3),
            "message": best_item.get("message", ""),
            "can_id": best_item.get("can_id", "")
        }
        if best_score >= 0.60 and margin >= 0.08:
            base["status"] = "FUZZY_APPLIED"
            return base
        if best_score >= 0.45:
            base["status"] = "REVIEW_REQUIRED"
            return base
        return {"requested": requested, "resolved": requested, "score": round(best_score, 3), "margin": round(margin, 3), "status": "UNRESOLVED"}

    def _coerce_rule_value(self, value: Any) -> Any:
        text = str(value).strip()
        if _HEX_RE.match(text):
            return float(int(text, 16))
        if _DECIMAL_RE.match(text):
            return float(text)
        unit_match = _UNIT_NUMBER_RE.match(text)
        if unit_match:
            return float(unit_match.group(1))
        return text.upper()

    def _compare_rule_value(self, observed: Any, operator: str, expected: Any) -> Optional[bool]:
        left = self._coerce_rule_value(observed)
        right = self._coerce_rule_value(expected)
        both_numeric = isinstance(left, float) and isinstance(right, float)
        if operator in {'=', '=='}:
            return math.isclose(left, right, rel_tol=1e-9, abs_tol=1e-9) if both_numeric else left == right
        if operator == '!=':
            return (not math.isclose(left, right, rel_tol=1e-9, abs_tol=1e-9)) if both_numeric else left != right
        if not both_numeric:
            return None
        return {'>': left > right, '<': left < right, '>=': left >= right, '<=': left <= right}.get(operator)

    def run_tc_blf_auto_validation(self):
        if not getattr(self, 'blf_summary_data', None):
            QMessageBox.warning(self, 'TC-BLF Auto Validation', '먼저 BLF와 DBC를 선택하고 Parse BLF Locally를 실행하세요.')
            return
        timeline = getattr(self, 'blf_full_signal_timeline', [])
        if not timeline:
            timeline = [e for e in self.blf_summary_data.get('key_timeline', []) if e.get('event_type') == 'signal_change']
        rules = self.extract_tc_blf_validation_rules()
        if not rules:
            QMessageBox.information(self, 'TC-BLF Auto Validation', "Expected Results에서 'Signal = Value' 형식의 조건을 찾지 못했습니다.\n정확한 Signal은 AUTO, 기능 설명은 DBC Mapping 후 분석하세요.")
            return
        results = []
        for rule in rules:
            resolution = self.resolve_tc_signal_to_dbc(rule['signal'])
            resolved_signal = resolution.get('resolved') or rule['signal']
            events = [e for e in timeline if str(e.get('signal', '')).lower() == str(resolved_signal).lower()]
            item = dict(rule)
            item['observations'] = []
            item['signal_resolution'] = resolution
            item['resolved_signal'] = resolved_signal
            if not events:
                item.update(
                    result='INCONCLUSIVE',
                    confidence='LOW',
                    reason=('DBC Decode Timeline에서 대상 Signal을 찾지 못했습니다.' + (f" 후보 {resolved_signal}은 임계값/후보 차이 부족으로 검토가 필요합니다." if resolution.get('status') == 'REVIEW_REQUIRED' else '')),
                    cause_candidates=['DBC/BLF 버전 확인', 'Signal Filter 및 분석 구간 확인', 'DBC Context Match로 Signal Mapping 확인']
                )
            else:
                matched = []
                for e in events:
                    ok = self._compare_rule_value(e.get('to'), rule['operator'], rule['expected'])
                    item['observations'].append({'time_sec': e.get('time_sec'), 'message': e.get('message'), 'from': e.get('from'), 'to': e.get('to'), 'matched': ok})
                    if ok is True:
                        matched.append(e)
                if matched:
                    item.update(result='PASS', confidence='HIGH', reason='기대 조건과 일치하는 값이 BLF에서 직접 확인되었습니다.', first_match_time_sec=matched[0].get('time_sec'))
                else:
                    item.update(result='FAIL', confidence='HIGH', reason='Signal은 수신됐지만 기대 조건과 일치하는 값이 확인되지 않았습니다.', cause_candidates=['선행 Vehicle/ECU 상태 미충족', '요청 이후 응답 또는 상태 전이 지연', 'Validity/Timeout/통신 영향', 'DBC와 SW 버전 불일치 가능성'])
            if resolution.get('status') == 'REVIEW_REQUIRED' and item.get('result') in ('PASS', 'FAIL'):
                item['confidence'] = 'LOW'
                item['reason'] = f"{item.get('reason', '')} (Signal 매핑 '{resolved_signal}'이 확정되지 않아 신뢰도를 낮춤)".strip()
            results.append(item)
        counts = Counter(r['result'] for r in results)
        report = {
            'engine': 'TC-BLF Local Validation v1',
            'notice': '명확한 Signal 조건만 로컬 계산합니다. 원인 후보는 확정 원인이 아닙니다.',
            'summary': {'rules': len(results), 'PASS': counts.get('PASS', 0), 'FAIL': counts.get('FAIL', 0), 'REVIEW': counts.get('REVIEW', 0), 'INCONCLUSIVE': counts.get('INCONCLUSIVE', 0)},
            'results': results
        }
        self.tc_blf_validation_data = report
        self.blf_summary_data['tc_blf_local_validation'] = report
        self.blf_summary_preview.setPlainText(json.dumps(report, ensure_ascii=False, indent=2))
        QMessageBox.information(self, 'TC-BLF Auto Validation', f"로컬 비교 완료\nPASS {counts.get('PASS',0)} | FAIL {counts.get('FAIL',0)} | INCONCLUSIVE {counts.get('INCONCLUSIVE',0)}")

    def is_safe_summary_mode(self) -> bool:
        return (
            not hasattr(self, "ai_transmission_mode")
            or self.ai_transmission_mode.currentIndex() == 0
        )

    def is_semantic_preserve_mode(self) -> bool:
        return hasattr(self, "ai_transmission_mode") and self.ai_transmission_mode.currentIndex() == 1

    def _ensure_semantic_signal_aliases(self) -> Dict[str, str]:
        ordered = []
        for signal in list(getattr(self, "tc_related_parse_signals", []) or []) + self.mapped_signals_for_analysis():
            if signal and signal not in ordered:
                ordered.append(signal)
        catalog, _errors = self.build_dbc_context_catalog()
        tc_text = self._tc_text_for_signal_selection() if hasattr(self, "_tc_text_for_signal_selection") else ""
        for item in catalog:
            signal = item.get("signal", "")
            if signal and signal in tc_text and signal not in ordered:
                ordered.append(signal)
        self.preferred_signal_aliases = {signal: f"SIG_{index:03d}" for index, signal in enumerate(ordered, 1)}
        return dict(self.preferred_signal_aliases)

    def _semantic_rewrite_line(self, text: str, aliases: Dict[str, str]) -> str:
        line = str(text or "").strip()
        if not line:
            return ""
        for signal, alias in sorted(aliases.items(), key=lambda row: len(row[0]), reverse=True):
            line = re.sub(r"(?<![A-Za-z0-9_])" + re.escape(signal) + r"(?![A-Za-z0-9_])", alias, line, flags=re.I)
        if not hasattr(self, "semantic_entity_aliases"):
            self.semantic_entity_aliases = {}
        protected = {
            "ON", "OFF", "OPEN", "CLOSE", "CLOSED", "LOCK", "LOCKED", "UNLOCK", "UNLOCKED",
            "ACTIVE", "INACTIVE", "REQUEST", "SUCCESS", "FAIL", "FAILED", "PASS", "CAN", "LIN",
            "UDS", "ISO", "TP", "BLF", "DBC", "AUTO", "TIMEOUT", "TRUE", "FALSE"
        }
        protected.update(aliases.values())

        def mask_identifier(match):
            token = match.group(0)
            upper = token.upper()
            if upper in protected or re.fullmatch(r"SIG_\d{3}", upper):
                return token
            if re.fullmatch(r"0x[0-9A-Fa-f]+", token):
                return token
            technical = ("_" in token or bool(re.search(r"[a-z][A-Z]|[A-Z][a-z]+[A-Z]", token)) or bool(re.search(r"\d", token)))
            if not technical:
                return token
            if token not in self.semantic_entity_aliases:
                self.semantic_entity_aliases[token] = f"LOCAL_REF_{len(self.semantic_entity_aliases)+1:03d}"
            return self.semantic_entity_aliases[token]

        return re.sub(r"\b[A-Za-z][A-Za-z0-9_]{3,}\b", mask_identifier, line)

    def build_semantic_preserved_tc_context(self) -> Tuple[str, Dict[str, str]]:
        aliases = self._ensure_semantic_signal_aliases()
        self.semantic_entity_aliases = {}
        sections = [
            ("Preconditions", getattr(self, "validation_preconditions", None)),
            ("Actions", getattr(self, "validation_steps", None)),
            ("Expected Behavior", getattr(self, "validation_expected_results", None)),
            ("Actual Observation", getattr(self, "validation_actual_results", None)),
        ]
        context = []
        for title, widget in sections:
            text = widget.toPlainText().strip() if isinstance(widget, QTextEdit) else ""
            lines = []
            for raw in text.splitlines():
                rewritten = self._semantic_rewrite_line(raw, aliases)
                if rewritten:
                    lines.append("- " + rewritten)
            context.append(f"[{title}]\n" + ("\n".join(lines) if lines else "- 정보 없음"))
        rules = self.extract_tc_blf_validation_rules()
        if rules:
            rule_lines = []
            for rule in rules:
                signal = aliases.get(rule.get("signal"), rule.get("signal"))
                rule_lines.append(f"- {signal} {rule.get('operator')} {rule.get('expected')} (Step {rule.get('step')})")
            context.append("[Preserved Validation Criteria]\n" + "\n".join(rule_lines))
        context.append("[Signal Alias Policy]\n- 실제 DBC Signal명은 로컬에서만 관리한다.\n- AI에는 SIG_### 별칭만 제공한다.\n- 값, 비교 연산자, 시간과 단위는 원래 판정 의미를 유지한다.")
        return "\n\n".join(context), aliases

    def build_secure_blf_summary(self) -> Dict[str, Any]:
        if not self.blf_summary_data:
            return {
                "security_mode": "TC_SOURCE_OMITTED_BLF_LOCAL_SUMMARY_ONLY",
                "raw_blf_sent_to_ai": False,
                "status": "BLF_SUMMARY_NOT_AVAILABLE",
            }

        level = self.prompt_level.currentText()
        event_limits = {"Basic": 15, "Detailed": 25, "Expert": 40}
        session_limits = {"Basic": 6, "Detailed": 12, "Expert": 20}
        stats = self.blf_summary_data.get("statistics", {})
        window = self.blf_summary_data.get("analysis_window", {})
        tp = self.blf_summary_data.get("transport_protocol_summary", {})

        signal_aliases = {}
        message_aliases = {}
        state_aliases = {}

        def alias(mapping, prefix, value):
            key = str(value or "").strip()
            if not key:
                return "UNKNOWN"
            if key not in mapping:
                mapping[key] = f"{prefix}_{len(mapping) + 1:03d}"
            return mapping[key]

        def safe_state(value):
            text = str(value if value is not None else "UNKNOWN").strip()
            if text == "UNOBSERVED":
                return "UNOBSERVED"
            try:
                return float(text)
            except Exception:
                return alias(state_aliases, "STATE", text)

        safe_timeline = []
        for event in self.blf_summary_data.get("key_timeline", [])[:event_limits.get(level, 25)]:
            event_type = event.get("event_type")
            if event_type == "signal_change":
                safe_timeline.append({
                    "time_sec": event.get("time_sec"),
                    "event_type": "signal_change",
                    "message": alias(message_aliases, "MSG", event.get("message")),
                    "signal": alias(signal_aliases, "SIG", event.get("signal")),
                    "from": safe_state(event.get("from")),
                    "to": safe_state(event.get("to")),
                })
            elif event_type == "raw_payload_change":
                safe_timeline.append({
                    "time_sec": event.get("time_sec"),
                    "event_type": "raw_message_changed",
                    "can_channel": alias(message_aliases, "CAN", event.get("can_id")),
                    "payload_value_removed": True,
                })

        safe_sessions = []
        for session in tp.get("sessions", [])[:session_limits.get(level, 12)]:
            uds = session.get("uds", {}) if isinstance(session.get("uds"), dict) else {}
            safe_uds = {
                key: value for key, value in uds.items()
                if key in {
                    "response_type", "service_name", "negative_response_name",
                    "service_id", "request_service_id"
                }
            }
            safe_sessions.append({
                "protocol": session.get("protocol", "ISO-TP"),
                "channel": alias(message_aliases, "TP_CH", session.get("can_id")),
                "start_time_sec": session.get("start_time_sec"),
                "end_time_sec": session.get("end_time_sec"),
                "duration_ms": session.get("duration_ms"),
                "frame_count": session.get("frame_count"),
                "status": session.get("status"),
                "issues": session.get("issues", []),
                "uds": safe_uds,
                "payload_removed": True,
            })

        return {
            "security_mode": "TC_SOURCE_OMITTED_BLF_LOCAL_SUMMARY_ONLY",
            "raw_blf_sent_to_ai": False,
            "tc_source_included": False,
            "file_names_included": False,
            "real_signal_names_included": False,
            "raw_payload_included": False,
            "analysis_window": {
                "start_sec": window.get("start_sec", 0),
                "end_sec": window.get("end_sec"),
                "time_reference": "local_log_start_equals_zero",
            },
            "parse_quality": {
                "selected_messages": stats.get("selected_messages", 0),
                "decoded_messages": stats.get("decoded_messages", 0),
                "decode_errors": stats.get("decode_errors", 0),
            },
            "key_timeline": safe_timeline,
            "transport_protocol_summary": {
                "mode": tp.get("mode", "Off"),
                "session_count": tp.get("session_count", len(safe_sessions)),
                "sessions": safe_sessions,
            },
            "analysis_instruction": (
                "TC 원문과 기대값은 제공되지 않았다. 로그에서 직접 확인되는 상태 전이, "
                "지연, 오류, 미완료 세션만 관찰 사실로 정리하고 PASS/FAIL이나 Root Cause를 확정하지 않는다."
            ),
        }

    def update_ai_transmission_mode_notice(self, *_args):
        if not hasattr(self, "ai_transmission_notice"):
            return
        index = self.ai_transmission_mode.currentIndex() if hasattr(self, "ai_transmission_mode") else 0
        if index == 0:
            text = "보안 기본 · TC 원문/Expected 원문 제외 · 익명 BLF 로컬 요약만 포함"
            style = "color:#28645f; background:#edf9f7; border:1px solid #addbd5; border-radius:4px; padding:5px; font-size:8pt;"
        elif index == 1:
            text = "의미 보존 · 문장 구조 유지 · Signal/기능/ECU 식별자 별칭 · 값/시간/단위 유지"
            style = "color:#155c75; background:#eaf7fb; border:1px solid #9ccfdf; border-radius:4px; padding:5px; font-size:8pt;"
        else:
            text = "주의 · 승인된 경우에만 TC 원문과 실제 Signal명 포함"
            style = "color:#8a4b00; background:#fff5df; border:1px solid #e7c88b; border-radius:4px; padding:5px; font-size:8pt;"
        self.ai_transmission_notice.setText(text)
        self.ai_transmission_notice.setStyleSheet(style)

    def reset_tc_generation_light_aliases(self):
        self.tc_generation_light_alias_map = {}
        self.tc_generation_light_reverse_map = {}

    def _light_alias_suffix(self, token: str) -> str:
        digest = hashlib.sha256(("VA_LIGHT_MASK_V1|" + str(token)).encode("utf-8")).hexdigest().upper()
        letters = "ABCDEFGHJKLMNPQRSTUVWXYZ"
        return f"_{letters[int(digest[:2],16)%len(letters)]}{int(digest[2:4],16)%10}"

    def apply_tc_generation_light_mask(self, text: str, reset: bool = True) -> str:
        """
        reset=True  : 별칭 map 을 새로 시작 (단독 호출)
        reset=False : 기존 map 을 이어서 사용 (한 프롬프트 안에서 여러 입력을 연속 마스킹할 때)
        """
        if not text or not hasattr(self, "tc_generation_signal_mode"):
            return str(text or "")
        mode = self.tc_generation_signal_mode.currentIndex()
        if reset or not hasattr(self, "tc_generation_light_alias_map"):
            self.reset_tc_generation_light_aliases()
        if mode == 2:
            return str(text)
        pattern = re.compile(r"\b[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+\b")
        protected = {"PASS_FAIL", "JSON_OUTPUT", "NOT_EVALUATED", "TC_GENERATION"}

        def repl(match):
            token = match.group(0)
            if token.upper() in protected or token in self.tc_generation_light_reverse_map:
                return token  # 보호 토큰 또는 이미 변환된 별칭
            alias = self.tc_generation_light_alias_map.get(token)
            if alias is None:  # 같은 토큰은 항상 같은 별칭, 새 토큰만 번호 증가
                alias = (
                    f"SIG_{len(self.tc_generation_light_alias_map) + 1:03d}"
                    if mode == 1
                    else token + self._light_alias_suffix(token)
                )
                self.tc_generation_light_alias_map[token] = alias
                self.tc_generation_light_reverse_map[alias] = token
            return alias

        return pattern.sub(repl, str(text))

    def restore_tc_generation_light_aliases(self, text: str) -> str:
        restored = str(text or "")
        for alias, original in sorted(getattr(self, "tc_generation_light_reverse_map", {}).items(), key=lambda x: len(x[0]), reverse=True):
            restored = re.sub(rf"\b{re.escape(alias)}\b", original, restored)
        return restored

    def update_tc_generation_signal_notice(self, *_args):
        if not hasattr(self, "tc_generation_signal_notice"):
            return
        messages = [
            "원본명에 고정 코드를 추가합니다. 완전한 익명화는 아닙니다.",
            "기술 식별자를 SIG_001 형식으로 바꿉니다. 의미 이해가 낮아질 수 있습니다.",
            "사내 AI 입력 승인을 확인한 경우에만 원본을 유지하세요.",
        ]
        self.tc_generation_signal_notice.setText(messages[self.tc_generation_signal_mode.currentIndex()])

    def get_blf_summary_for_prompt(self) -> str:
        if self.is_safe_summary_mode():
            return json.dumps(
                self.build_secure_blf_summary(),
                ensure_ascii=False,
                separators=(",", ":"),
            )
        if not self.blf_summary_data:
            return "BLF 요약 없음"
        level = self.prompt_level.currentText()
        event_limits = {"Basic": 15, "Detailed": 25, "Expert": 40}
        session_limits = {"Basic": 6, "Detailed": 12, "Expert": 20}
        tp = self.blf_summary_data.get("transport_protocol_summary", {})
        sessions = tp.get("sessions", [])
        stats = self.blf_summary_data.get("statistics", {})
        source = self.blf_summary_data.get("source", {})
        compact = {
            "source": {"blf_file": source.get("blf_file", ""), "raw_file_sent_to_ai": False},
            "analysis_window": self.blf_summary_data.get("analysis_window", {}),
            "parse_quality": {
                "selected_messages": stats.get("selected_messages", 0),
                "decoded_messages": stats.get("decoded_messages", 0),
                "decode_errors": stats.get("decode_errors", 0)
            },
            "important_findings": self.blf_summary_data.get("important_findings", [])[:10],
            "key_timeline": self.blf_summary_data.get("key_timeline", [])[:event_limits.get(level, 25)],
            "transport_protocol_summary": {"mode": tp.get("mode", "Off"), "sessions": sessions[:session_limits.get(level, 12)]}
        }
        summary = json.dumps(compact, ensure_ascii=False, separators=(",", ":"))
        if self.is_semantic_preserve_mode():
            self._ensure_semantic_signal_aliases()
        anonymize_widget = getattr(self, "anonymize_signals_for_ai", None)
        anonymize = bool(anonymize_widget.isChecked()) if anonymize_widget is not None else False
        if self.is_semantic_preserve_mode() or anonymize:
            aliases = getattr(self, "preferred_signal_aliases", None) or {}
            # 긴 이름부터, 식별자 경계 기준으로 치환 (Sig_Door 가 Sig_DoorLock 을 깨뜨리지 않도록)
            for signal, alias_name in sorted(aliases.items(), key=lambda row: len(row[0]), reverse=True):
                summary = re.sub(
                    r"(?<![A-Za-z0-9_])" + re.escape(signal) + r"(?![A-Za-z0-9_])", alias_name, summary
                )
        return summary

    # --------------------------------------------------------------------------
    # 도메인 레지스트리 조회 헬퍼
    # --------------------------------------------------------------------------
    def get_domain_key(self) -> str:
            """
            현재 UI 콤보박스 선택값 및 도메인 프로필을 기반으로 
            레지스트리 키('automotive', 'web_api', 'mobile_app' 등)를 정확히 추출합니다.
            """
            profile = self.current_domain_profile() or {}
            
            # 1. 프로필에 'key'가 명시되어 있으면 최우선 사용
            key = str(profile.get("key", "")).strip().lower()
            if key in FEW_SHOTS:
                return key
                
            # 2. UI 콤보박스(qa_domain 또는 mode)에서 선택된 텍스트 직접 확인
            domain_text = ""
            if hasattr(self, "qa_domain") and hasattr(self.qa_domain, "currentText"):
                domain_text = self.qa_domain.currentText()
            elif hasattr(self, "qa_domain_combo") and hasattr(self.qa_domain_combo, "currentText"):
                domain_text = self.qa_domain_combo.currentText()
            else:
                domain_text = str(profile.get("name", ""))
    
            # 3. 텍스트 정규식 패턴 매칭
            text_to_check = f"{profile.get('name', '')} {domain_text}"
            for domain_key, pattern in _DOMAIN_NAME_PATTERNS:
                if pattern.search(text_to_check):
                    return domain_key
                    
            # 4. 자동차 전용 툴(CANoe/DBC/BLF)을 사용하는 프로필인 경우
            if profile.get("automotive_tools"):
                return "automotive"
    
            return DEFAULT_DOMAIN_KEY

    def get_domain_few_shot(self, kind: str) -> str:
        """kind: 'generation' | 'analysis'. 프로필 few_shot 이 있으면 우선, 없으면 레지스트리."""
        profile = self.current_domain_profile() or {}
        custom = profile.get("few_shot")
        if isinstance(custom, dict) and custom.get(kind):
            return str(custom[kind])
        shots = FEW_SHOTS.get(self.get_domain_key(), FEW_SHOTS[DEFAULT_DOMAIN_KEY])
        return shots.get(kind, "")

    def build_system_instruction(self) -> str:
        addendum = DOMAIN_SYSTEM_ADDENDUM.get(self.get_domain_key(), "")
        return SYSTEM_BASE_INSTRUCTION + (f"\n\n{addendum}" if addendum else "")

    def get_domain_profile_value(self, field: str, default: Any = None) -> Any:
        """프로필 값이 있으면 그 값을, 없으면 도메인 기본값(DOMAIN_DEFAULTS)을, 그것도 없으면 default 를 반환."""
        profile = self.current_domain_profile() or {}
        value = profile.get(field)
        if value:
            return value
        fallback = DOMAIN_DEFAULTS.get(self.get_domain_key(), {}).get(field)
        return fallback if fallback else default

    def build_level_scope(self, level: str) -> str:
        profile = self.current_domain_profile() or {}
        level_key = level if level in ("Basic", "Detailed") else "Expert"
        custom = profile.get("level_scope")
        if isinstance(custom, dict) and custom.get(level_key):
            body = str(custom[level_key])
        else:
            extra = DOMAIN_LEVEL_EXTRA.get(self.get_domain_key(), {}).get(level_key, "")
            body = LEVEL_SCOPE_COMMON[level_key] + (f"\n{extra}" if extra else "")
        return f"[Generation Scope - {level_key} Level]\n{body}"

    @staticmethod
    def _fill_template(template: str, values: Dict[str, Any]) -> str:
        """플레이스홀더를 한 번에(single-pass) 치환한다. 사용자 입력 안의 __XXX__ 는 재치환되지 않는다."""
        if not values:
            return template
        pattern = re.compile("|".join(re.escape(k) for k in sorted(values, key=len, reverse=True)))
        return pattern.sub(lambda m: str(values[m.group(0)]), template)

    def get_domain_prompt_values(
        self, mode_override: Optional[str] = None, with_evidence: bool = True
    ) -> Tuple[str, str, str]:
        profile = self.current_domain_profile() or {}
        mode = mode_override if mode_override else (self.mode.currentText() if hasattr(self, "mode") else "")
        if "Validation Analysis" in mode:
            rule_key = "analysis_rules"
        elif "TC Review" in mode:
            rule_key = "review_rules"
        else:
            rule_key = "generation_rules"
        role = self.get_domain_profile_value("role", "Software Quality Assurance Specialist")
        rules = self.get_domain_profile_value(rule_key, [])
        rule_text = "\n".join(f"- {rule}" for rule in rules)
        evidence = ""
        if with_evidence:  # evidence 가 쓰이지 않는 모드에서는 BLF 요약 계산을 생략
            evidence = (
                self.get_blf_summary_for_prompt()
                if profile.get("automotive_tools")
                else self.get_domain_evidence_summary()
            )
        return role, rule_text, evidence

    # ==========================================================================
    # 3. 100점 프롬프트 템플릿 기반 핵심 파서 및 생성 메서드 (Refactored)
    # ==========================================================================

    def generate_tc_creation_prompt(self, feature_name: str, requirement: str, expected_behavior: str, level: str) -> str:
        """
        100점 프롬프트 엔지니어링 가이드라인이 반영된 TC Creation Prompt 생성기.
        System Instruction(+도메인 용어) + 도메인 Few-Shot + 정량적 제약 조건 결합.
        """
        system_instruction = self.build_system_instruction()
        few_shot_example = self.get_domain_few_shot("generation")

        # 사용자 입력에만 Light Mask 적용 (시스템 템플릿 마스킹 방지).
        # 별칭 map 은 이 프롬프트 생성 동안 공유해야 요구사항/기대동작 간 별칭이 충돌하지 않는다.
        self.reset_tc_generation_light_aliases()
        masked_req = self.apply_tc_generation_light_mask(requirement, reset=False)
        masked_exp = self.apply_tc_generation_light_mask(expected_behavior, reset=False)

        seq_mode = getattr(self, "tc_generation_sequence_mode", "사용자 흐름 우선")
        sequence_rule = SEQUENCE_MODE_RULES.get(seq_mode, SEQUENCE_MODE_RULES["사용자 흐름 우선"])
        level_scope = self.build_level_scope(level)
        role_text, rule_text, _ = self.get_domain_prompt_values("TC Generation", with_evidence=False)

        prompt = f"""{system_instruction}

{few_shot_example}

[Domain Role]
{role_text}

[Domain Rules]
{rule_text}

{level_scope}

[Sequence Mode Rules: {seq_mode}]
{sequence_rule}

[Target Feature Input]
Feature Name: {feature_name}
Requirement: {masked_req}
Expected Behavior: {masked_exp}
Prompt Level: {level}
"""
        return prompt

    def build_generated_tc_review_prompt(self, generated_data: Dict[str, Any]) -> str:
        """
        생성된 TC JSON 결과를 독립적 Reviewer 관점에서 2차 재검토하는 Prompt 생성기.
        """
        profile = self.current_domain_profile() or {}
        role = self.get_domain_profile_value("role", "Software Quality Assurance Specialist")
        review_rules = "\n".join(f"- {rule}" for rule in self.get_domain_profile_value("review_rules", []))
        generated_json = json.dumps(generated_data, ensure_ascii=False, indent=2)

        return self.clean_prompt_block(f"""{self.build_system_instruction()}

너는 {role}이다.
방금 생성된 Test Case 전체를 독립적인 Lead SQA Reviewer 관점에서 다시 검토하라.

[Domain Review Rules]
{review_rules}

[Generated Test Cases to Review]
{generated_json}

[Review & Verification Instructions]
1. 생성된 모든 TC에 대해 요구사항 추적성, 정량적 측정 가능성, 스텝 1:1 대칭성을 검증한다.
2. 모호한 정성적 문구("적절히", "확인할 것")가 존재할 경우 정량적 수치(ms, V, 0xHEX, HTTP Status)로 수정안을 작성한다.
3. steps와 expected_results 항목 수가 일치하지 않는 경우 배열 개수를 수정한다.

[Output Format Instructions]
결과 전체를 하나의 ```json 코드 블록 안에 출력하라. 코드 블록 밖에는 어떠한 설명도 작성하지 마라.

{{
  "review_summary": {{
    "total_count": 0,
    "pass_count": 0,
    "needs_improvement_count": 0,
    "overall_comment": "한국어로 작성된 전체 총평"
  }},
  "reviewed_test_cases": [
    {{
      "tc_id": "TC_GEN_001",
      "original_title": "테스트케이스 제목",
      "review_result": "PASS",
      "score": 95,
      "issues": [],
      "missing_conditions": [],
      "recommendations": [],
      "revised_preconditions": [],
      "revised_steps": [],
      "revised_expected_results": [],
      "risk": "HIGH"
    }}
  ]
}}
""")

    def prepare_generated_tc_auto_review(self, generated_data: Dict[str, Any], show_message: bool = True) -> bool:
        if not isinstance(generated_data, dict) or not generated_data.get("test_cases"):
            return False
        review_prompt = self.build_generated_tc_review_prompt(generated_data)
        self.generated_prompt = review_prompt
        self.update_prompt_preview()
        QApplication.clipboard().setText(review_prompt)
        self.pending_generated_tc_data = generated_data
        if show_message:
            QMessageBox.information(
                self,
                "TC Auto Review Ready",
                "생성된 TC를 기반으로 2차 Review Prompt를 자동 생성했습니다.\n\n"
                "Review Prompt가 클립보드에 복사되었으며 Prompt Preview에도 표시됩니다.\n"
                "사용 중인 AI에 붙여넣고, Review JSON 결과를 Paste 버튼으로 가져오세요."
            )
        return True

    def normalize_prompt_spacing(self, text: str) -> str:
        if not text:
            return ""
        lines = [line.rstrip() for line in text.splitlines()]
        cleaned_lines = []
        previous_blank = False
        for line in lines:
            is_blank = not line.strip()
            if is_blank and previous_blank:
                continue
            cleaned_lines.append(line)
            previous_blank = is_blank
        return "\n".join(cleaned_lines).strip()

    @staticmethod
    def _is_structural_line(stripped: str) -> bool:
        """JSON 스키마 등 들여쓰기/중복이 의미를 갖는 구조 라인 판별."""
        if stripped[0] in '{}]"':
            return True
        return stripped[0] == "[" and not _SECTION_HEADER_RE.match(stripped)

    def optimize_prompt_text(self, text: str) -> str:
        if not text:
            return ""
        text = textwrap.dedent(text).replace("\t", "    ")
        output = []
        in_code = False
        previous_blank = False
        seen_lines = set()
        seen_sections = set()
        for raw in text.splitlines():
            line = raw.rstrip()
            stripped = line.strip()
            if stripped.startswith("```"):
                in_code = not in_code
                output.append(stripped)
                previous_blank = False
                continue
            if in_code:
                output.append(line)
                previous_blank = False
                continue
            if not stripped:
                if output and not previous_blank:
                    output.append("")
                previous_blank = True
                continue
            if self._is_structural_line(stripped):
                # 코드블록 밖 JSON 스키마: '}' ']' 중복 제거/들여쓰기 제거로 깨지지 않게 그대로 보존
                output.append(line)
                previous_blank = False
                continue
            if _SECTION_HEADER_RE.match(stripped):
                section_key = stripped.lower()
                if section_key in seen_sections:
                    continue
                seen_sections.add(section_key)
            normalized = re.sub(r"\s+", " ", stripped).lower()
            is_list_item = stripped.startswith("- ") or bool(_NUMBERED_PREFIX_RE.match(stripped))
            if normalized in seen_lines and not is_list_item:
                continue
            seen_lines.add(normalized)
            output.append(line.lstrip())
            previous_blank = False
        return "\n".join(output).strip()

    def update_prompt_preview(self):
        self.result.clear()
        document = self.result.document()
        cursor = self.result.textCursor()
        preview_marker = "[[EVIDENCE_PREVIEW]]"

        if not self.generated_prompt:
            cursor.insertText("생성된 Prompt가 없습니다.")
            self.result.moveCursor(QTextCursor.Start)
            return

        if preview_marker not in self.generated_prompt:
            display_prompt = self.normalize_prompt_spacing(self.generated_prompt)
            cursor.insertText(display_prompt)
            self.result.moveCursor(QTextCursor.Start)
            return

        before_evidence, after_evidence = self.generated_prompt.split(preview_marker, 1)
        before_evidence = self.normalize_prompt_spacing(before_evidence)
        after_evidence = self.normalize_prompt_spacing(after_evidence)

        cursor.insertText(before_evidence.rstrip() + "\n\n")

        if not self.attachments:
            cursor.insertText("첨부된 이미지 없음")
        else:
            available_width = self.result.viewport().width() - 50
            image_width = max(250, min(available_width, 650))

            for index, file_path in enumerate(self.attachments, start=1):
                file_name = os.path.basename(file_path)
                cursor.insertText(f"Evidence {index}: {file_name}\n")

                if not os.path.exists(file_path):
                    cursor.insertText("[이미지 파일을 찾을 수 없습니다.]\n\n")
                    continue

                pixmap = QPixmap(file_path)
                if pixmap.isNull():
                    cursor.insertText("[이미지를 불러올 수 없습니다.]\n\n")
                    continue

                scaled_pixmap = pixmap.scaled(
                    image_width,
                    360,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )

                path_digest = hashlib.sha256(os.path.abspath(file_path).encode("utf-8")).hexdigest()[:12]
                resource_name = f"prompt_evidence_{index}_{path_digest}"
                resource_url = QUrl(resource_name)

                document.addResource(
                    QTextDocument.ImageResource,
                    resource_url,
                    scaled_pixmap
                )

                image_format = QTextImageFormat()
                image_format.setName(resource_name)
                image_format.setWidth(scaled_pixmap.width())
                image_format.setHeight(scaled_pixmap.height())

                cursor.insertImage(image_format)
                cursor.insertText("\n\n")

        cursor.insertText("\n\n" + after_evidence.lstrip())
        self.result.moveCursor(QTextCursor.Start)

    def clean_prompt_block(self, text: str) -> str:
        if not text:
            return ""
        text = textwrap.dedent(text)
        text = text.replace("\t", "    ")
        lines = text.splitlines()
        cleaned_lines = []
        previous_blank = False
        for line in lines:
            line = line.rstrip()
            is_blank = not line.strip()
            if is_blank:
                if previous_blank:
                    continue
                cleaned_lines.append("")
                previous_blank = True
                continue
            cleaned_lines.append(line)
            previous_blank = False
        return "\n".join(cleaned_lines).strip()

    def generate_prompt(self):
        """
        Validation Analysis, TC Review, TC Generation 모드 통합 프롬프트 빌더.
        """
        mode = self.mode.currentText()
        if "Validation Analysis" in mode or "TC Review" in mode:
            self.sync_structured_validation_to_legacy_fields()
        tc = self.tc.text().strip()
        purpose = self.purpose.toPlainText().strip()
        expected = self.expected.toPlainText().strip()

        if "Validation Analysis" in mode and hasattr(self, "validation_preconditions"):
            pre = self.validation_preconditions.toPlainText().strip()
            steps = self.validation_steps.toPlainText().strip()
            expected_result = self.validation_expected_results.toPlainText().strip()
            actual_result = self.validation_actual_results.toPlainText().strip()
            blocks = []
            if pre:
                blocks.append("[Preconditions]\n" + pre)
            if steps:
                blocks.append("[Test Steps]\n" + steps)
            if expected_result:
                blocks.append("[Expected Results]\n" + expected_result)
            purpose = "\n\n".join(blocks)
            expected = actual_result

        analysis_question = (
            self.analysis_question.toPlainText().strip()
            if hasattr(self, "analysis_question")
            else ""
        )

        level = self.prompt_level.currentText()

        if not tc:
            QMessageBox.warning(self, "입력 확인", "TC Name 또는 Feature Name을 입력하세요.")
            return

        if "TC Generation" in mode:
            purpose, expected = self.get_tc_generation_prompt_inputs()
            if not purpose:
                return  # 입력 오류 안내는 get_tc_generation_prompt_inputs 에서 이미 표시됨

        if not purpose:
            QMessageBox.warning(self, "입력 확인", "Purpose 또는 Requirement를 입력하세요.")
            return

        # 보안 기본 모드 처리
        if "Validation Analysis" in mode and self.is_safe_summary_mode():
            tc = "LOCAL_TC_REFERENCE_OMITTED"
            purpose = "TC 원문은 보안 정책 확인 전이므로 제공하지 않음. Preconditions/Steps는 로컬에 보관됨."
            local_rules = self.extract_tc_blf_validation_rules()
            selected_signal_count = len(list(getattr(self, "tc_related_parse_signals", []) or []))
            # 보안 기본 모드에서는 실제 Signal 명을 프롬프트에 넣지 않고 개수만 전달한다.
            signal_note = f"선택 Signal {selected_signal_count}개(실명은 로컬에서만 관리)" if selected_signal_count else "Signal 미확정"
            expected = f"Actual Result 원문 제외. 로컬 Expected 조건 {len(local_rules)}개 비교 적용됨. {signal_note}"
            analysis_question = "제공된 익명화 BLF 요약만 분석하고 PASS/FAIL 판정을 확정하지 않는다."

        elif "Validation Analysis" in mode and self.is_semantic_preserve_mode():
            semantic_context, semantic_aliases = self.build_semantic_preserved_tc_context()
            tc_hash = hashlib.sha256(tc.encode("utf-8")).hexdigest()[:10].upper()
            tc = f"LOCAL_TC_{tc_hash}"
            purpose = semantic_context
            actual_widget = getattr(self, "validation_actual_results", None)
            actual_text = actual_widget.toPlainText().strip() if isinstance(actual_widget, QTextEdit) else expected
            expected = self._semantic_rewrite_line(actual_text, semantic_aliases) or "관찰 결과 정보 없음"
            analysis_question = "의미 보존 변환된 시그널 별칭(SIG_###)과 수치를 바탕으로 비교 분석을 수행한다."

        # ======================================================================
        # 1. Validation Analysis Prompt 빌드
        # ======================================================================
        if "Validation Analysis" in mode:
            domain_role, domain_rules, domain_evidence = self.get_domain_prompt_values(mode)
            validation_template = f"""{self.build_system_instruction()}

{self.get_domain_few_shot("analysis")}

너는 __DOMAIN_ROLE__이다.
다음 분야별 분석 기준을 적용하라.
__DOMAIN_RULES__

[Validation Information]
TC Name: __TC_NAME__
TC Information: __PURPOSE__
Actual Result / Issue: __EXPECTED__
Selected Analysis Purpose: __ANALYSIS_PURPOSE__
User Analysis Question: __ANALYSIS_QUESTION__

[Evidence Summary]
__DOMAIN_EVIDENCE__

[Attached Evidence]
[[EVIDENCE_PREVIEW]]

[Analysis Rules]
1. 입력된 TC 목적과 기대 결과를 기준으로 관찰 사실과 추론을 명확히 구분한다.
2. 증적이 부족한 경우 result는 "INCONCLUSIVE" 또는 "EVIDENCE INSUFFICIENT"로 처리한다.
3. recommended_verification은 정량적 확인 방법과 판단 기준을 포함하여 작성한다.
"""
            self.generated_prompt = self._fill_template(validation_template, {
                "__DOMAIN_ROLE__": domain_role,
                "__DOMAIN_RULES__": domain_rules,
                "__DOMAIN_EVIDENCE__": domain_evidence,
                "__TC_NAME__": tc,
                "__PURPOSE__": purpose,
                "__EXPECTED__": expected,
                "__ANALYSIS_PURPOSE__": self.analysis_purpose.currentText() if hasattr(self, "analysis_purpose") else "전체 분석",
                "__ANALYSIS_QUESTION__": analysis_question or "Actual Result와 Expected Result 간 차이 원인을 정량 분석하라.",
            })

        # ======================================================================
        # 2. TC Review Prompt 빌드
        # ======================================================================
        elif "TC Review" in mode:
            domain_role, domain_rules, _ = self.get_domain_prompt_values(mode, with_evidence=False)
            review_template = f"""{self.build_system_instruction()}

너는 __DOMAIN_ROLE__이다.
다음 분야별 리뷰 기준을 적용하라.
__DOMAIN_RULES__

[TC Information]
TC Name: __TC_NAME__
Purpose: __PURPOSE__
Expected Result: __EXPECTED__

[Review Rules]
1. TC의 명확성, 정량적 측정 가능성, 누락된 경계 조건(Boundary Conditions)을 검토한다.
2. 모호한 정성적 문구가 있을 경우 정량적 수치 조건(ms, V, 0xHEX)으로 보정안을 제시한다.
"""
            self.generated_prompt = self._fill_template(review_template, {
                "__DOMAIN_ROLE__": domain_role,
                "__DOMAIN_RULES__": domain_rules,
                "__TC_NAME__": tc,
                "__PURPOSE__": purpose,
                "__EXPECTED__": expected,
            })

        # ======================================================================
        # 3. TC Generation Prompt 빌드
        # ======================================================================
        elif "TC Generation" in mode:
            if not expected:
                expected = "요구사항에 부합하는 정량적 Expected Result 및 PASS 기준을 도출한다."
            self.generated_prompt = self.generate_tc_creation_prompt(tc, purpose, expected, level)

        else:
            QMessageBox.warning(self, "Mode Error", "지원하지 않는 Mode입니다.")
            return

        self.generated_prompt = self.clean_prompt_block(self.generated_prompt)

        if "TC Review" in mode:
            self.generated_prompt += "\n\n" + self.build_tc_review_json_instruction()

        self.generated_prompt = self.optimize_prompt_text(self.generated_prompt)
        self.update_prompt_preview()
        self.save_history()

    def build_tc_review_json_instruction(self) -> str:
        return self.clean_prompt_block("""
[JSON OUTPUT - REQUIRED]
반드시 유효한 단일 JSON Object만 출력하라. 일반 설명을 JSON 밖에 작성하지 마라.
JSON 전체를 하나의 ```json 코드 블록 안에 넣어라.

{
  "review_summary": {
    "total_count": 1,
    "pass_count": 0,
    "needs_improvement_count": 1,
    "overall_comment": "한국어 검토 총평"
  },
  "reviewed_test_cases": [
    {
      "tc_id": "TC_REV_001",
      "original_title": "",
      "review_result": "NEEDS_IMPROVEMENT",
      "score": 80,
      "requirement_coverage": "PARTIAL",
      "clarity": "POOR",
      "testability": "PARTIAL",
      "missing_conditions": ["신호/응답 지연시간 수치 미비"],
      "issues": ["정성적 표현 사용됨"],
      "recommendations": ["150ms 이내 전이 조건 추가"],
      "revised_title": "",
      "revised_precondition": "",
      "revised_steps": [],
      "revised_expected_result": "",
      "risk": "HIGH"
    }
  ]
}
""")

    def get_prompt_text_for_copy(self) -> str:
        if not self.generated_prompt:
            return ""
        if self.attachments:
            evidence_text = "\n".join(
                f"Evidence {index}: {os.path.basename(file_path)}"
                for index, file_path in enumerate(self.attachments, start=1)
            )
        else:
            evidence_text = "첨부된 이미지 없음"
        prompt_text = self.generated_prompt.replace("[[EVIDENCE_PREVIEW]]", evidence_text)
        return self.normalize_prompt_spacing(prompt_text)

    def Prompt_Generation(self):
        self.generated_prompt = ""
        self.generate_prompt()
        if not self.generated_prompt:
            return
        prompt_text = self.get_prompt_text_for_copy()
        if not prompt_text.strip():
            QMessageBox.warning(self, "Copy Error", "복사할 Prompt가 없습니다.")
            return
        if len(prompt_text) > MAX_PROMPT_CHARS:
            QMessageBox.warning(
                self,
                "Prompt Too Long",
                f"프롬프트가 권장 최대 길이({MAX_PROMPT_CHARS:,}자)를 초과했습니다.\n현재 길이: {len(prompt_text):,}자"
            )
            return
        QApplication.clipboard().setText(prompt_text)
        message = "Prompt 텍스트가 클립보드에 복사되었습니다. 원하는 AI 입력창에 붙여넣으세요."
        QMessageBox.information(self, "Ready", message)

    def build_gemini_json_instruction(self) -> str:
        """Gemini API 전용 표준 JSON 스키마 지시사항 생성"""
        return self.clean_prompt_block(f"""{self.build_system_instruction()}

[Gemini API Output Rules]
1. Markdown 설명문 없이 오직 유효한 단일 JSON Object만 반환하라.
2. 모든 설명 문구는 한국어로 작성하되, 기술 식별자(Signal, ECU, API Endpoint)는 영문/Hex 표기를 유지하라.
3. Enum 값에는 선택지 전체 문자열이 아닌 단일 선택 판정값(예: "PASS") 하나만 작성하라.
""")
