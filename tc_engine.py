"""
tc_engine.py - Automotive Validation Assistant Prompt & Execution Engine
Refactored to 100-Point Prompt Architecture (100% Backward Compatible)
"""

from __future__ import annotations
import json
import re
import textwrap
import hashlib
from collections import Counter
from typing import Dict, Any, List, Tuple, Optional
from PySide6.QtWidgets import QMessageBox, QApplication, QTextEdit
from PySide6.QtGui import QTextCursor, QPixmap, QTextImageFormat
from PySide6.QtCore import Qt, QUrl

# ==============================================================================
# 1. 100점 프롬프트 아키텍처 핵심 상수 (System Instruction & Concrete Few-Shot)
# ==============================================================================

SYSTEM_BASE_INSTRUCTION = """You are a Principal Software Quality Assurance (SQA) Engineer specializing in Automotive Electronic Control Units (ECU), CAN/LIN/Ethernet networks, and Vehicle Domain Controllers (BCM, BCU, BDC).
Your primary directive is to analyze automotive software requirements or trace logs and output strictly structured JSON specifications.

[LANGUAGE & TERMINOLOGY POLICY]
1. ALL natural language descriptions inside JSON (e.g., tc_name, summary, steps, expected_results, pass_factors, fail_factors) MUST be written in KOREAN (한국어).
2. Automotive technical identifiers, CAN/LIN signal names (e.g., Sig_DrvDoorLockSt), ECU power states (e.g., IGN_ON, 0x02), protocol names (UDS, ISO-TP), and equipment names (Vector CANoe) MUST retain their standard English/Hex notations.

[CRITICAL OUTPUT GRAMMAR]
1. Output MUST be ONLY a single valid JSON object enclosed strictly within a ```json ... ``` markdown code block.
2. Do NOT output any introductory text, explanations, notes, or markdown headings outside the code block.
3. Enum Fields: Output ONLY a single selected string choice (e.g., "PASS"). NEVER output full choice literals like "PASS | FAIL | PARTIAL".
4. Array Symmetry: The 'expected_results' array MUST have the exact same number of elements as the 'steps' array, matching 1-to-1 by index.

[QUANTITATIVE PRECISION MANDATE]
1. Every Test Step and Expected Result MUST contain precise quantitative attributes:
   - Physical units (ms, s, V, A, Hz, deg)
   - Logical/Comparison operators (==, !=, >=, <=, >, <)
   - Hexadecimal/Decimal state values (e.g., 0x01, 13.5V)
2. Strictly PROHIBITED ambiguous words: "약", "대략", "적절히", "확인할 것", "상응하는", "properly", "roughly", "about"."""

FEW_SHOT_TC_CREATION = """[FEW-SHOT EXAMPLE - TC GENERATION]
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
    "BLF 로그 분석 결과, 스위치 입력(10.050s) 후 80ms 시점(10.130s)에 Sig_DrvDoorLockSt 신호가 0x01로 전이됨을 확인 함 (기대 기준: 150ms 이내)"
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
    "1. 전압 변동 조건(9.0V ~ 16.0V)에서의 응답시간 한계 검증추가",
    "2. CAN 버스 로드율 80% 상태에서의 지연시간 비교 측정"
  ]
}
```"""

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
- 초기 상태 설정 -> 물리적 조작 -> 기능 Trigger -> Signal 상태 전이 확인 -> 최종 물리 동작 확인 순으로 구성한다.
- 물리적 조작과 Signal 확인을 각각 독립된 별도 Step으로 작성한다.
- 수치 조건이 명시되지 않은 시간, 전압, 횟수는 TBD 표기를 유지한다.
"""
        elif mode == "사용자 흐름 우선":
            sequence_instruction = """
[Sequence Generation Mode: USER FLOW FIRST]
- [Mandatory Test Execution Sequence]의 핵심 흐름과 순서를 완벽히 유지한다.
- 축약된 흐름을 실제 수행 가능한 상세 Step으로 확장하되, 물리적 조작과 Signal 확인을 분리한다.
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
            match = re.match(r"^(?:Step\s*)?(\d+(?:[-.]\d+)*)\s*[.)：:]?\s*(.*)$", line, re.I)
            if match:
                items.append((match.group(1), match.group(2).strip() or line))
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
        for function_name, signal_name in self.signal_function_mapping.items():
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
        try:
            return float(text)
        except Exception:
            return text.upper()

    def _compare_rule_value(self, observed: Any, operator: str, expected: Any) -> Optional[bool]:
        left = self._coerce_rule_value(observed)
        right = self._coerce_rule_value(expected)
        if operator in {'=', '=='}:
            return left == right
        if operator == '!=':
            return left != right
        if not isinstance(left, float) or not isinstance(right, float):
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

    def apply_tc_generation_light_mask(self, text: str) -> str:
        if not text or not hasattr(self, "tc_generation_signal_mode"):
            return str(text or "")
        mode = self.tc_generation_signal_mode.currentIndex()
        self.reset_tc_generation_light_aliases()
        if mode == 2:
            return str(text)
        pattern = re.compile(r"\b[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+\b")
        protected = {"PASS_FAIL", "JSON_OUTPUT", "NOT_EVALUATED", "TC_GENERATION"}

        def repl(match):
            token = match.group(0)
            if token.upper() in protected or re.search(r"_[A-Z][0-9]$", token):
                return token
            alias = (f"SIG_{len(self.tc_generation_light_alias_map)+1:03d}" if mode == 1 else token + self._light_alias_suffix(token))
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
        if self.is_semantic_preserve_mode() or self.anonymize_signals_for_ai.isChecked():
            for signal, alias_name in self.preferred_signal_aliases.items():
                summary = summary.replace(signal, alias_name)
        return summary

    def get_domain_prompt_values(self) -> Tuple[str, str, str]:
        profile = self.current_domain_profile()
        mode = self.mode.currentText()
        if "Validation Analysis" in mode:
            rule_key = "analysis_rules"
        elif "TC Review" in mode:
            rule_key = "review_rules"
        else:
            rule_key = "generation_rules"
        role = profile.get("role", "Software Quality Assurance Specialist")
        rules = profile.get(rule_key, [])
        rule_text = "\n".join(f"- {rule}" for rule in rules)
        evidence = (
            self.get_blf_summary_for_prompt()
            if profile.get("automotive_tools")
            else self.get_domain_evidence_summary()
        )
        return role, rule_text, evidence

    # ==========================================================================
    # 3. 100점 프롬프트 템플릿 기반 핵심 파서 및 생성 메서드 (Refactored)
    # ==========================================================================

    def generate_tc_creation_prompt(
        self,
        feature_name: str,
        requirement: str,
        expected_behavior: str,
        level: str
    ):
        """
        100점 프롬프트 엔지니어링 가이드라인이 반영된 TC Creation Prompt 생성기.
        System Base Instruction + In-Context Few-Shot + 정량적 제약 조건 결합.
        """
        seq_mode = getattr(self, "tc_generation_sequence_mode", "사용자 흐름 우선")
        
        if level == "Basic":
            level_scope = """[Generation Scope - Basic Level]
- 정상 시나리오(Positive), 기본 실패 시나리오(Basic Negative), 핵심 상태 전이(State Transition) 위주로 생성한다.
- 각 TC는 tc_id, category, title, preconditions, steps, expected_results, risk, risk_description을 포함한다."""
        elif level == "Detailed":
            level_scope = """[Generation Scope - Detailed Level]
- Positive, Negative, Boundary Value, State Transition, Timeout, Retry, Recovery 관점의 테스트 시나리오를 포함한다.
- 전압/시간/신호값 경계 조건(Boundary Conditions)을 정량적 수치로 구체화한다."""
        else:
            level_scope = """[Generation Scope - Expert Level]
- 동등 분할(Equivalence Partitioning), 경계값 분석(BVA), 결정 테이블(Decision Table), Fault Injection, Communication Loss, Power Cycle 조건을 포함한다.
- 차량 통신 지연시간 및 세션 타임아웃 오차범위를 정량적으로 포함한다."""

        prompt_block = f"""{SYSTEM_BASE_INSTRUCTION}

{FEW_SHOT_TC_CREATION}

너는 __DOMAIN_ROLE__이다.
다음 분야별 검증 기준을 적용하라.
__DOMAIN_RULES__

[Target Generation Metadata]
Feature / Function: __FEATURE_NAME__
Requirement / System Behavior: __REQUIREMENT__
Target Behavior / Acceptance Criteria: __EXPECTED_BEHAVIOR__
Prompt Level: __LEVEL__
Sequence Strategy: {seq_mode}

{level_scope}

[Generation & Self-Review Process]
1. 요구사항을 정량적으로 측정 가능한 단위(ms, V, Hz, 0xHEX, ==, >=, <=)로 분해한다.
2. 입력된 [Mandatory Test Execution Sequence]가 존재할 경우 번호 순서를 생략하거나 재배치하지 않는다.
3. 물리적 조작(Switch, Power)과 통신 신호 확인(CAN Signal)을 반드시 별개의 독립 Step으로 분리한다.
4. steps와 expected_results의 배열 요소 개수는 1:1로 정확히 일치해야 한다.
5. 확인되지 않은 사양은 임의로 수치를 확정하지 않고 TBD 또는 UNKNOWN으로 표기한다.

[Output Format Instructions]
반드시 유효한 단일 JSON Object만 출력하라. JSON 앞뒤에 일반 설명문을 작성하지 마라.
결과 전체를 하나의 ```json 코드 블록 안에 출력하라.
"""
        self.generated_prompt = (
            prompt_block
            .replace("__FEATURE_NAME__", feature_name)
            .replace("__REQUIREMENT__", requirement)
            .replace("__EXPECTED_BEHAVIOR__", expected_behavior)
            .replace("__LEVEL__", level)
        )

    def build_generated_tc_review_prompt(self, generated_data: Dict[str, Any]) -> str:
        """
        생성된 TC JSON 결과를 독립적 Reviewer 관점에서 2차 재검토하는 Prompt 생성기.
        """
        profile = self.current_domain_profile()
        role = profile.get("role", "Software Quality Assurance Specialist")
        review_rules = "\n".join(f"- {rule}" for rule in profile.get("review_rules", []))
        generated_json = json.dumps(generated_data, ensure_ascii=False, indent=2)

        return self.clean_prompt_block(f"""{SYSTEM_BASE_INSTRUCTION}

너는 {role}이다.
방금 생성된 Test Case 전체를 독립적인 Lead SQA Reviewer 관점에서 다시 검토하라.

[Domain Review Rules]
{review_rules}

[Generated Test Cases to Review]
{generated_json}

[Review & Verification Instructions]
1. 생성된 모든 TC에 대해 요구사항 추적성, 정량적 측정 가능성, 스텝 1:1 대칭성을 검증한다.
2. 모호한 정성적 문구("적절히", "확인할 것")가 존재할 경우 정량적 수치(ms, V, 0xHEX)로 수정안을 작성한다.
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

    def optimize_prompt_text(self, text: str) -> str:
        if not text:
            return ""
        text = textwrap.dedent(text).replace("\t", "    ")
        output = []
        in_code = False
        previous_blank = False
        seen_lines = set()
        seen_sections = set()
        repeatable_prefixes = ("- ", "1. ", "2. ", "3. ", "4. ", "5. ")
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
            if stripped.startswith("[") and stripped.endswith("]"):
                section_key = stripped.lower()
                if section_key in seen_sections:
                    continue
                seen_sections.add(section_key)
            normalized = re.sub(r"\s+", " ", stripped).lower()
            if normalized in seen_lines and not stripped.startswith(repeatable_prefixes):
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

                resource_name = f"prompt_evidence_{index}_{os.path.abspath(file_path)}"
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
        if "Validation Analysis" in self.mode.currentText() or "TC Review" in self.mode.currentText():
            self.sync_structured_validation_to_legacy_fields()
        tc = self.tc.text().strip()
        purpose = self.purpose.toPlainText().strip()
        expected = self.expected.toPlainText().strip()

        if "Validation Analysis" in self.mode.currentText() and hasattr(self, "validation_preconditions"):
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

        mode = self.mode.currentText()
        level = self.prompt_level.currentText()
        if "TC Generation" in mode:
            purpose, expected = self.get_tc_generation_prompt_inputs()

        if not tc:
            QMessageBox.warning(self, "입력 확인", "TC Name 또는 Feature Name을 입력하세요.")
            return

        if not purpose:
            QMessageBox.warning(self, "입력 확인", "Purpose 또는 Requirement를 입력하세요.")
            return

        # 보안 기본 모드 처리
        if "Validation Analysis" in mode and self.is_safe_summary_mode():
            tc = "LOCAL_TC_REFERENCE_OMITTED"
            purpose = "TC 원문은 보안 정책 확인 전이므로 제공하지 않음. Preconditions/Steps는 로컬에 보관됨."
            local_rules = self.extract_tc_blf_validation_rules()
            selected_signals = list(getattr(self, "tc_related_parse_signals", []) or [])
            expected = f"Actual Result 원문 제외. 로컬 Expected 조건 {len(local_rules)}개 비교 적용됨. Signal: {', '.join(selected_signals) if selected_signals else '미확정'}"
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
            validation_template = f"""{SYSTEM_BASE_INSTRUCTION}

{FEW_SHOT_VALIDATION_ANALYSIS}

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
            self.generated_prompt = (
                validation_template
                .replace("__TC_NAME__", tc)
                .replace("__PURPOSE__", purpose)
                .replace("__EXPECTED__", expected)
                .replace("__ANALYSIS_PURPOSE__", self.analysis_purpose.currentText() if hasattr(self, "analysis_purpose") else "전체 분석")
                .replace("__ANALYSIS_QUESTION__", analysis_question or "Actual Result와 Expected Result 간 차이 원인을 정량 분석하라.")
                .replace("__BLF_SUMMARY__", self.get_blf_summary_for_prompt())
            )

        # ======================================================================
        # 2. TC Review Prompt 빌드
        # ======================================================================
        elif "TC Review" in mode:
            review_template = f"""{SYSTEM_BASE_INSTRUCTION}

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
            self.generated_prompt = (
                review_template
                .replace("__TC_NAME__", tc)
                .replace("__PURPOSE__", purpose)
                .replace("__EXPECTED__", expected)
            )

        # ======================================================================
        # 3. TC Generation Prompt 빌드
        # ======================================================================
        elif "TC Generation" in mode:
            if not expected:
                expected = "요구사항에 부합하는 정량적 Expected Result 및 PASS 기준을 도출한다."
            self.generate_tc_creation_prompt(tc, purpose, expected, level)

        else:
            QMessageBox.warning(self, "Mode Error", "지원하지 않는 Mode입니다.")
            return

        domain_role, domain_rules, domain_evidence = self.get_domain_prompt_values()
        self.generated_prompt = (
            self.generated_prompt
            .replace("__DOMAIN_ROLE__", domain_role)
            .replace("__DOMAIN_RULES__", domain_rules)
            .replace("__DOMAIN_EVIDENCE__", domain_evidence)
        )
        self.generated_prompt = self.clean_prompt_block(self.generated_prompt)

        if "TC Review" in mode:
            self.generated_prompt += "\n\n" + self.build_tc_review_json_instruction()

        self.generated_prompt = self.optimize_prompt_text(self.generated_prompt)
        if "TC Generation" in mode:
            self.generated_prompt = self.apply_tc_generation_light_mask(self.generated_prompt)
        else:
            self.reset_tc_generation_light_aliases()
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
      "missing_conditions": ["신호 지연시간 수치 미비"],
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
        return self.clean_prompt_block(f"""{SYSTEM_BASE_INSTRUCTION}

[Gemini API Output Rules]
1. Markdown 설명문 없이 오직 유효한 단일 JSON Object만 반환하라.
2. 모든 설명 문구는 한국어로 작성하되, 기술 식별자(Signal, ECU)는 영문/Hex 표기를 유지하라.
3. Enum 값에는 선택지 전체 문자열이 아닌 단일 선택 판정값(예: "PASS") 하나만 작성하라.
""")