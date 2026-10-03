from .core_runtime import *


class UiMainMixin:
    def __init__(self):
            super().__init__()
    
            self.generated_prompt = ""
            self.blf_file_path = ""
            self.dbc_file_paths = []
            self.blf_summary_data = {}
            if hasattr(self, "blf_start_time"):
                self.blf_start_time.clear()
                self.blf_end_time.clear()
                self.blf_summary_preview.clear()
                self.update_blf_status()
            self.attachments = []
            self.tc_related_parse_signals = []
            self.current_ai_result_data = {}
            self.dbc_context_match_report = []
            self.preferred_dbc_signals = []
            self.signal_function_mapping = {}
            self.signal_sets = {}
            self.active_signal_set = ""
            self.load_signal_sets()
            self.auto_mapping_report = []
            self.preferred_signal_aliases = {}
            self.tc_generation_light_alias_map = {}
            self.tc_generation_light_reverse_map = {}
            self.tc_generation_page = "basic"
            self.tc_generation_requirement = ""
            self.tc_generation_acceptance = ""
            self.tc_generation_preconditions = ""
            self.tc_generation_observations = ""
            self.tc_generation_sequence = ""
            self.tc_generation_checkpoints = ""
            self.tc_generation_sequence_mode = "사용자 흐름 우선"
            self._last_mode_text = ""
            self._dbc_cache_key = None
            self._dbc_catalog_cache = []
            self._dbc_name_index_cache = {}
            self._dbc_cache_errors = []
            self._dbc_database_cache = None
            self.domain_evidence_files = []
            self.domain_profiles = load_profiles()
            self.blf_file_path = ""
            self.dbc_file_paths = []
            self.blf_summary_data = {}
            self.settings = QSettings("ValidationAssistant", "AutomotiveValidationAI")
            self.setWindowTitle(
                'Validation Assistant Unified - Professional'
            )
    
            self.init_ui()
    
            self.update_mode_ui()
            self.update_domain_ui()
            self.update_dashboard()
            self.refresh_saved_tc_list()
    
            self.prompt_level.currentTextChanged.connect(
                self.update_dashboard
            )
    
            if os.environ.get("VA_UNIFIED_RESTORE") == "1":
                QTimer.singleShot(0, self._theme_restore_state)

    def update_tc_generation_beginner_ui(self, *_args):
            """TC Generation 전용 위젯을 현재 모드와 고급 설정 상태에 맞춰 정확히 표시한다."""
            if not hasattr(self, "tc_generation_advanced_toggle"):
                return
            is_generation = "TC Generation" in self.mode.currentText()
            expanded = is_generation and self.tc_generation_advanced_toggle.isChecked()
    
            self.tc_generation_advanced_toggle.setVisible(is_generation)
            self.tc_generation_advanced_container.setVisible(False)
    
            # 실제 위젯들이 기존 left_layout에 있더라도 명시적으로 제어해 모드 누수를 막는다.
            self.tc_generation_sequence_mode_row.setVisible(is_generation)
            self.tc_generation_signal_mode_label.setVisible(is_generation)
            self.tc_generation_signal_mode.setVisible(is_generation)
            self.tc_generation_signal_notice.setVisible(is_generation)
            for widget in (
                self.tc_generation_page_row,
            ):
                widget.setVisible(expanded)
    
            # 품질에 직접 관련된 두 기능은 기본 화면에 유지한다.
            self.auto_tc_review.setVisible(is_generation)
            self.dbc_context_match_btn.setVisible(is_generation)
            self.tc_generation_advanced_toggle.setText(
                "▲ 고급 설정 접기" if expanded else "▶ 고급 설정 펼치기"
            )

    def fill_tc_generation_beginner_example(self):
            self.mode.setCurrentText("✨ TC Generation")
            self.tc_generation_page = "basic"
            self.tc.setText("Sample Automatic Door Lock")
            self.tc_generation_requirement = (
                "등록된 가상 키의 인증이 성공하고 모든 도어가 닫힌 경우 자동 잠금을 수행한다.\n\n"
                "Sample_LockRequest = REQUEST 이후 2초 이내 Sample_DoorStatus = LOCKED가 되어야 한다.\n\n"
                "인증 실패 또는 도어 OPEN 상태에서는 잠금 요청이 발생하지 않아야 한다."
            )
            self.tc_generation_acceptance = (
                "초기 도어 상태는 UNLOCKED이다.\n"
                "키 이동 순서는 NEAR에서 FAR로 한다.\n"
                "제한시간 초과 시 Sample_LockErrorStatus = TIMEOUT을 확인한다."
            )
            self.load_tc_generation_page_values()
            self.tc_generation_advanced_toggle.setChecked(False)
            self.update_tc_generation_beginner_ui()
            QMessageBox.information(
                self, "예시 입력 완료",
                "가상 요구사항을 입력했습니다.\n\n내용을 확인한 뒤 Prompt Generation을 누르세요.\n"
                "세부 시험 조건이 필요하면 고급 설정 펼치기를 사용하세요."
            )

    def update_quick_button_label(self, *_args):
            if not hasattr(self, "quick_tc_open_btn"):
                return
            mode = self.mode.currentText()
            if "Validation Analysis" in mode:
                label = "빠른 Validation"
            elif "TC Review" in mode:
                label = "빠른 TC Review"
            else:
                label = "빠른 TC 생성"
            self.quick_tc_open_btn.setText(label)
            self.quick_tc_open_btn.setToolTip(f"현재 {mode} 모드의 간단 입력 창을 엽니다.")

    def open_mode_quick_dialog(self):
            mode = self.mode.currentText()
            if "Validation Analysis" in mode:
                self.open_quick_validation_dialog()
            elif "TC Review" in mode:
                self.open_quick_review_dialog()
            else:
                self.open_quick_tc_dialog()

    def open_quick_validation_dialog(self):
            """Validation 본 화면과 동일한 Precondition/Steps/Expected/Actual 구조의 빠른 입력창."""
            dialog = QDialog(self)
            dialog.setWindowTitle("빠른 Validation Analysis")
            dialog.setModal(True)
            dialog.resize(720, 720)
            layout = QVBoxLayout(dialog)
            layout.setContentsMargins(16, 14, 16, 14)
            layout.setSpacing(7)
    
            guide = QLabel(
                "TC Name과 Precondition, Steps, Expected, Actual을 같은 번호 체계로 입력하세요.\n"
                "붙여넣은 내용은 번호를 기준으로 자동 줄바꿈되며 전체 Validation 화면에 그대로 반영됩니다."
            )
            guide.setWordWrap(True)
            guide.setStyleSheet(
                "color:#405764; background:#f4f9fa; border:1px solid #c8dce1; "
                "border-radius:4px; padding:7px;"
            )
            layout.addWidget(guide)
    
            layout.addWidget(QLabel("1. TC Name"))
            tc_name = QLineEdit()
            tc_name.setPlaceholderText("예: Sleep 진입 후 Reset 동작 검증")
            tc_name.setText(self.tc.text().strip())
            layout.addWidget(tc_name)
    
            tabs = QTabWidget()
            tabs.setFixedHeight(330)
            tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            tabs.setStyleSheet(
                "QTabWidget::pane { border:1px solid #cbd8df; border-radius:4px; background:#ffffff; } "
                "QTabBar::tab { min-width:105px; padding:7px 10px; } "
                "QTabBar::tab:selected { color:#0b7f79; font-weight:700; }"
            )
    
            preconditions = RobustTcTextEdit()
            steps = RobustTcTextEdit()
            expected = RobustTcTextEdit()
            actual = RobustTcTextEdit()
            preconditions.setPlaceholderText("1. 시험 전 상태\n2. 전원/통신/진단 조건")
            steps.setPlaceholderText("1. 수행 동작\n2. 다음 수행 동작")
            expected.setPlaceholderText("1. 기대 결과 또는 Signal = Value\n2. 기능 기대 동작")
            actual.setPlaceholderText("1. 실제 관찰 결과\n2. BLF 분석 필요 또는 확인된 현상")
    
            if hasattr(self, "validation_preconditions"):
                preconditions.setPlainText(self.validation_preconditions.toPlainText())
                steps.setPlainText(self.validation_steps.toPlainText())
                expected.setPlainText(self.validation_expected_results.toPlainText())
                actual.setPlainText(self.validation_actual_results.toPlainText())
    
            tabs.addTab(preconditions, "Precondition")
            tabs.addTab(steps, "Steps")
            tabs.addTab(expected, "Expected")
            tabs.addTab(actual, "Actual")
            layout.addWidget(tabs)
    
            status = QLabel("Precondition 0 | Step 0 | Expected 0 | Actual 0")
            status.setStyleSheet("color:#607786; font-size:8pt; padding:2px 4px;")
            status.setWordWrap(False)
            layout.addWidget(status)
    
            def count_items(editor):
                return len(self._numbered_items(editor.toPlainText()))
    
            def update_status():
                status.setText(
                    f"Precondition {count_items(preconditions)} | Step {count_items(steps)} | "
                    f"Expected {count_items(expected)} | Actual {count_items(actual)}"
                )
            for editor in (preconditions, steps, expected, actual):
                editor.textChanged.connect(update_status)
            update_status()
    
            lower = QGridLayout()
            lower.setHorizontalSpacing(8)
            lower.setVerticalSpacing(5)
            lower.addWidget(QLabel("2. 분석 관점"), 0, 0)
            focus = QComboBox()
            focus.addItems(["전체 분석", "Expected vs Actual 비교", "Signal 상태 전이 분석", "가능한 원인 분석", "다음 확인 항목 제안"])
            lower.addWidget(focus, 0, 1)
            lower.addWidget(QLabel("3. 분석 질문"), 1, 0)
            question = QTextEdit()
            question.setFixedHeight(72)
            question.setPlaceholderText("예: Step별 Expected와 Actual, BLF 요약을 비교하고 확인된 이상과 원인 후보를 구분해주세요.")
            lower.addWidget(question, 1, 1)
            layout.addLayout(lower)
    
            ai_note = QLabel(
                "권장: BLF 원본을 AI에 직접 맡기기보다 먼저 Parse BLF Locally를 실행한 뒤, "
                "로컬에서 Decode한 Signal Timeline과 요약을 Prompt에 포함하세요. "
                "TC-BLF Auto Validation은 정확한 Signal 조건이 있을 때만 선택적으로 사용합니다."
            )
            ai_note.setWordWrap(True)
            ai_note.setStyleSheet(
                "color:#6a5412; background:#fff8e8; border:1px solid #ead8a4; "
                "border-radius:4px; padding:6px; font-size:8pt;"
            )
            layout.addWidget(ai_note)
    
            row = QHBoxLayout()
            normalize_btn = QPushButton("현재 탭 붙여넣기 정리")
            normalize_btn.setObjectName("secondaryButton")
            cancel = QPushButton("취소")
            apply = QPushButton("입력 적용")
            apply.setObjectName("primaryButton")
            row.addWidget(normalize_btn)
            row.addStretch()
            row.addWidget(cancel)
            row.addWidget(apply)
            layout.addLayout(row)
    
            def normalize_active():
                editor = tabs.currentWidget()
                if hasattr(editor, "normalize_current_text"):
                    editor.normalize_current_text()
                update_status()
    
            def apply_values():
                name = tc_name.text().strip()
                if not name:
                    QMessageBox.warning(dialog, "빠른 Validation", "TC Name을 입력하세요.")
                    return
                if not steps.toPlainText().strip() and not expected.toPlainText().strip():
                    QMessageBox.warning(dialog, "빠른 Validation", "Steps 또는 Expected 중 하나 이상을 입력하세요.")
                    return
                self.mode.setCurrentText("🔍 Validation Analysis")
                self.tc.setText(name)
                self.validation_preconditions.setPlainText(preconditions.toPlainText())
                self.validation_steps.setPlainText(steps.toPlainText())
                self.validation_expected_results.setPlainText(expected.toPlainText())
                self.validation_actual_results.setPlainText(actual.toPlainText())
                self.analysis_purpose.setCurrentText(focus.currentText() if focus.currentText() in [self.analysis_purpose.itemText(i) for i in range(self.analysis_purpose.count())] else "전체 분석")
                if question.toPlainText().strip():
                    self.analysis_question.setPlainText(question.toPlainText().strip())
                self.sync_structured_validation_to_legacy_fields()
                self.update_dashboard()
                dialog.accept()
                QMessageBox.information(
                    self,
                    "빠른 Validation",
                    "구조화 입력을 적용했습니다.\n\n"
                    "BLF와 DBC를 첨부한 뒤 Parse BLF Locally를 실행하고, "
                    "Prompt Generation으로 사내 AI 분석용 Prompt를 생성하세요."
                )
    
            normalize_btn.clicked.connect(normalize_active)
            cancel.clicked.connect(dialog.reject)
            apply.clicked.connect(apply_values)
            dialog.exec()

    def open_quick_review_dialog(self):
            dialog = QDialog(self)
            dialog.setWindowTitle("빠른 TC Review")
            dialog.setModal(True)
            dialog.resize(650, 650)
            layout=QVBoxLayout(dialog); layout.setContentsMargins(16,14,16,14); layout.setSpacing(7)
            guide=QLabel("기존 TC와 리뷰 목적을 입력하면 누락, 모호성, 수행 가능성 및 판정 가능성을 검토하는 Prompt에 반영합니다.")
            guide.setWordWrap(True); layout.addWidget(guide)
    
            tc_name=QLineEdit(); tc_name.setPlaceholderText("예: Digital Key Unlock TC Review")
            original=QTextEdit(); original.setFixedHeight(210); original.setPlaceholderText("검토할 기존 TC의 Preconditions, Steps, Expected Results를 붙여넣으세요.")
            criteria=QTextEdit(); criteria.setFixedHeight(100); criteria.setPlaceholderText("중점 검토 기준을 입력하세요.")
            depth=QComboBox(); depth.addItems(["빠른 검토", "상세 검토", "실행 가능성 중심", "DBC Signal 중심"]); depth.setCurrentText("상세 검토")
    
            for label_text,widget in [
                ("1. Review 이름",tc_name),("2. 기존 TC",original),("3. 중점 검토 기준",criteria),("4. Review 방식",depth)]:
                label=QLabel(label_text); label.setObjectName("subSectionTitle"); layout.addWidget(label); layout.addWidget(widget)
    
            row=QHBoxLayout(); example=QPushButton("Digital Key TC 예시"); example.setObjectName("secondaryButton")
            cancel=QPushButton("취소"); apply=QPushButton("입력 적용"); apply.setObjectName("primaryButton")
            row.addWidget(example); row.addStretch(); row.addWidget(cancel); row.addWidget(apply); layout.addLayout(row)
    
            def fill_example():
                tc_name.setText("Digital Key Unlock TC Review")
                original.setPlainText("Preconditions:\n1. 운전석 도어는 잠금 상태이다.\n\nSteps:\n1. 모바일 기기를 차량으로 이동한다.\n2. 인증 Signal을 확인한다.\n3. Door Lock Signal을 확인한다.\n\nExpected Results:\n1. 인증이 성공한다.\n2. 도어가 Unlock된다.")
                criteria.setPlainText("물리 조작과 Signal 확인의 분리, Steps와 Expected Results의 1:1 대응, Signal 역할 정확성, TBD 및 누락 조건을 검토한다.")
                depth.setCurrentText("실행 가능성 중심")
    
            def apply_values():
                if not tc_name.text().strip() or not original.toPlainText().strip():
                    QMessageBox.warning(dialog,"입력 확인","Review 이름과 기존 TC를 입력하세요."); return
                self.tc.setText(tc_name.text().strip())
                self.purpose.setPlainText(original.toPlainText().strip())
                review_text=criteria.toPlainText().strip()
                if depth.currentText(): review_text += f"\n\n[Review 방식]\n{depth.currentText()}"
                self.expected.setPlainText(review_text)
                dialog.accept(); self.update_dashboard()
                QMessageBox.information(self,"빠른 TC Review","입력을 적용했습니다. Prompt Generation을 눌러 Review Prompt를 만드세요.")
            example.clicked.connect(fill_example); cancel.clicked.connect(dialog.reject); apply.clicked.connect(apply_values)
            dialog.exec()

    def show_startup_dialog(self):
            """Show a small startup choice without changing the expert screen layout."""
            dialog = QDialog(self)
            dialog.setWindowTitle("Validation Assistant 시작")
            dialog.setModal(True)
            dialog.setFixedWidth(460)
            layout = QVBoxLayout(dialog)
            layout.setContentsMargins(18, 16, 18, 16)
            layout.setSpacing(10)
    
            title = QLabel("Validation Assistant")
            title.setObjectName("sectionTitle")
            title.setAlignment(Qt.AlignCenter)
            layout.addWidget(title)
    
            guide = QLabel(
                "처음 사용하는 경우 빠른 TC 생성을 선택하세요.\n"
                "기존 DBC, BLF, Signal 및 전체 설정은 전체 기능 화면에서 사용할 수 있습니다."
            )
            guide.setWordWrap(True)
            guide.setAlignment(Qt.AlignCenter)
            layout.addWidget(guide)
    
            quick_btn = QPushButton("빠른 TC 생성")
            quick_btn.setObjectName("primaryButton")
            quick_btn.setMinimumHeight(48)
            quick_btn.setToolTip("필수 입력만 작성한 뒤 전체 기능 화면으로 전달합니다.")
            full_btn = QPushButton("전체 기능 열기")
            full_btn.setObjectName("secondaryButton")
            full_btn.setMinimumHeight(42)
            full_btn.setToolTip("기존 전문가 화면을 바로 엽니다.")
            layout.addWidget(quick_btn)
            layout.addWidget(full_btn)
    
            choice = {"quick": False}
            def choose_quick():
                choice["quick"] = True
                dialog.accept()
            quick_btn.clicked.connect(choose_quick)
            full_btn.clicked.connect(dialog.accept)
            dialog.exec()
    
            if choice["quick"]:
                self.open_quick_tc_dialog()

    def open_quick_tc_dialog(self):
            """Collect only the minimum information needed for a TC Generation draft."""
            dialog = QDialog(self)
            dialog.setWindowTitle("빠른 TC 생성")
            dialog.setModal(True)
            dialog.resize(650, 720)
            layout = QVBoxLayout(dialog)
            layout.setContentsMargins(16, 14, 16, 14)
            layout.setSpacing(7)
    
            intro = QLabel(
                "필수 정보만 입력하세요. 입력한 내용은 전체 기능 화면의 TC Generation 항목에 자동 반영됩니다.\n"
                "DBC와 실제 Signal 연결은 입력 적용 후 오른쪽 영역에서 선택적으로 진행할 수 있습니다."
            )
            intro.setWordWrap(True)
            layout.addWidget(intro)
    
            feature = QLineEdit()
            feature.setPlaceholderText("예: Digital Key Driver Door Unlock")
            requirement = QTextEdit()
            requirement.setPlaceholderText("기능이 언제 시작되고 성공/실패 시 어떻게 동작해야 하는지 입력하세요.")
            requirement.setFixedHeight(105)
            acceptance = QTextEdit()
            acceptance.setPlaceholderText("관찰 가능한 합격 기준을 입력하세요.")
            acceptance.setFixedHeight(80)
            preconditions = QTextEdit()
            preconditions.setPlaceholderText("시험 시작 전 차량 상태와 환경을 입력하세요.")
            preconditions.setFixedHeight(80)
            flow = QTextEdit()
            flow.setPlaceholderText("예: Close → Lock → Key 접근 → 인증 → Unlock → Open\n비워두면 AI가 자동 생성합니다.")
            flow.setFixedHeight(78)
            observations = QTextEdit()
            observations.setPlaceholderText("확인할 Signal 또는 물리 상태를 입력하세요. 선택 사항입니다.")
            observations.setFixedHeight(78)
            sequence_mode = QComboBox()
            sequence_mode.addItems(["AI 자동 생성", "사용자 흐름 우선", "사용자 순서 고정"])
            sequence_mode.setCurrentText("사용자 흐름 우선")
    
            form_items = [
                ("1. 기능 이름", feature),
                ("2. 기능 요구사항", requirement),
                ("3. 합격 기준", acceptance),
                ("4. 시험 전 상태", preconditions),
                ("5. 수행 흐름", flow),
                ("6. 확인 Signal / 관찰 항목", observations),
                ("7. 순서 생성 방식", sequence_mode),
            ]
            for label_text, widget in form_items:
                label = QLabel(label_text)
                label.setObjectName("subSectionTitle")
                layout.addWidget(label)
                layout.addWidget(widget)
    
            button_row = QHBoxLayout()
            example_btn = QPushButton("Digital Key 예시")
            example_btn.setObjectName("secondaryButton")
            cancel_btn = QPushButton("취소")
            apply_btn = QPushButton("입력 적용 후 전체 기능 열기")
            apply_btn.setObjectName("primaryButton")
            button_row.addWidget(example_btn)
            button_row.addStretch()
            button_row.addWidget(cancel_btn)
            button_row.addWidget(apply_btn)
            layout.addLayout(button_row)
    
            def fill_example():
                feature.setText("Digital Key Driver Door Unlock")
                requirement.setPlainText(
                    "등록된 Digital Key가 장착된 모바일 기기가 운전석 접근 영역으로 이동하면 "
                    "차량은 인증을 수행한다. 인증에 성공하면 운전석 도어 잠금을 해제하고, "
                    "인증에 실패하면 잠금 상태를 유지한다."
                )
                acceptance.setPlainText(
                    "인증 성공 후 운전석 도어 잠금 상태가 Locked에서 Unlocked로 전이되어야 한다. "
                    "요구사항에 없는 시간, 거리와 횟수는 TBD로 유지한다."
                )
                preconditions.setPlainText(
                    "1. 차량은 Digital Key 기능이 동작 가능한 전원 상태이다.\n"
                    "2. 운전석 도어는 닫힘 및 잠금 상태이다.\n"
                    "3. 시험용 Digital Key는 차량에 정상 등록되어 있다."
                )
                flow.setPlainText("Close → Lock → Key 접근 → 인증 → Unlock → Open")
                observations.setPlainText(
                    "- Door Lock 초기 Locked 상태\n"
                    "- Key 위치 상태 전이\n"
                    "- 인증 결과\n"
                    "- Door Lock의 Locked → Unlocked 전이\n"
                    "- 실제 Door Open 가능 여부"
                )
                sequence_mode.setCurrentText("사용자 흐름 우선")
    
            def apply_inputs():
                if not feature.text().strip():
                    QMessageBox.warning(dialog, "입력 확인", "기능 이름을 입력하세요.")
                    feature.setFocus()
                    return
                if not requirement.toPlainText().strip():
                    QMessageBox.warning(dialog, "입력 확인", "기능 요구사항을 입력하세요.")
                    requirement.setFocus()
                    return
                if sequence_mode.currentText() == "사용자 순서 고정" and not flow.toPlainText().strip():
                    QMessageBox.warning(dialog, "입력 확인", "사용자 순서 고정 모드에서는 수행 흐름을 입력하세요.")
                    flow.setFocus()
                    return
    
                if self.qa_domain.findText("Automotive CANoe") >= 0:
                    self.qa_domain.setCurrentText("Automotive CANoe")
                generation_index = self.mode.findText("✨ TC Generation")
                if generation_index >= 0:
                    self.mode.setCurrentIndex(generation_index)
                self.prompt_level.setCurrentText("Detailed")
                self.tc.setText(feature.text().strip())
                self.tc_generation_requirement = requirement.toPlainText().strip()
                self.tc_generation_acceptance = acceptance.toPlainText().strip()
                self.tc_generation_preconditions = preconditions.toPlainText().strip()
                self.tc_generation_observations = ""
                self.tc_generation_sequence = flow.toPlainText().strip()
                self.tc_generation_checkpoints = observations.toPlainText().strip()
                self.tc_generation_sequence_mode = sequence_mode.currentText()
                self.tc_generation_page = "basic"
                self.load_tc_generation_page_values()
                self.update_dashboard()
                dialog.accept()
                QMessageBox.information(
                    self,
                    "빠른 입력 적용 완료",
                    "입력 내용을 TC Generation 화면에 적용했습니다.\n\n"
                    "다음 순서:\n"
                    "1. 필요하면 오른쪽에서 DBC와 Signal을 설정합니다.\n"
                    "2. Prompt Generation을 누릅니다.\n"
                    "3. AI JSON 결과를 Paste합니다."
                )
    
            example_btn.clicked.connect(fill_example)
            cancel_btn.clicked.connect(dialog.reject)
            apply_btn.clicked.connect(apply_inputs)
            dialog.exec()

    def _theme_state_path(self):
            return os.path.join(os.path.dirname(os.path.abspath(os.environ.get("VA_UNIFIED_LAUNCHER", __file__))), ".validation_assistant_theme_state.json")

    def _theme_json_safe(self, value):
            if value is None or isinstance(value, (str, int, float, bool)): return value
            if isinstance(value, (list, tuple)): return [self._theme_json_safe(item) for item in value]
            if isinstance(value, dict): return {str(key): self._theme_json_safe(item) for key, item in value.items()}
            return str(value)

    def _theme_collect_state(self):
            state={"widgets":{},"attrs":{}}
            widget_types=(QLineEdit,QTextEdit,QComboBox,QSpinBox,QCheckBox,QTabWidget)
            for i,widget_type in enumerate(widget_types):
                values=[]
                for widget in self.findChildren(widget_type):
                    if isinstance(widget,QLineEdit): value=widget.text()
                    elif isinstance(widget,QTextEdit): value={"plain":widget.toPlainText(),"html":widget.toHtml()}
                    elif isinstance(widget,QComboBox): value={"index":widget.currentIndex(),"text":widget.currentText()}
                    elif isinstance(widget,QSpinBox): value=widget.value()
                    elif isinstance(widget,QCheckBox): value=widget.isChecked()
                    else: value=widget.currentIndex()
                    values.append(value)
                state["widgets"][str(i)]=values
            names=("attachments","domain_evidence_files","current_ai_result_data","generated_prompt","blf_file_path","dbc_file_paths","blf_summary_data","blf_full_signal_timeline","tc_blf_validation_data","dbc_context_match_report","preferred_dbc_signals","signal_function_mapping","active_signal_set","auto_mapping_report","preferred_signal_aliases","tc_generation_light_alias_map","tc_generation_light_reverse_map","tc_generation_page","tc_generation_requirement","tc_generation_acceptance","tc_generation_preconditions","tc_generation_observations","tc_generation_sequence","tc_generation_checkpoints","tc_generation_sequence_mode","tc_related_parse_signals","u_mode_states")
            for name in names:
                if hasattr(self,name): state["attrs"][name]=self._theme_json_safe(getattr(self,name))
            return state

    def _theme_save_state(self):
            path=self._theme_state_path(); temp=path+".tmp"
            try:
                if hasattr(self,"_u_save_mode_state"): self._u_save_mode_state()
                with open(temp,"w",encoding="utf-8") as file:
                    json.dump(self._theme_collect_state(),file,ensure_ascii=False,indent=2); file.flush(); os.fsync(file.fileno())
                os.replace(temp,path); return True
            except Exception as error:
                QMessageBox.critical(self,"테마 상태 저장 오류",f"현재 입력값을 저장하지 못했습니다.\n\n{error}"); return False

    def _theme_restore_state(self):
            path=self._theme_state_path()
            if not os.path.isfile(path): return
            try:
                with open(path,"r",encoding="utf-8-sig") as file: state=json.load(file)
                for name,value in state.get("attrs",{}).items(): setattr(self,name,value)
                widget_types=(QLineEdit,QTextEdit,QComboBox,QSpinBox,QCheckBox,QTabWidget)
                for i,widget_type in enumerate(widget_types):
                    for widget,value in zip(self.findChildren(widget_type),state.get("widgets",{}).get(str(i),[])):
                        widget.blockSignals(True)
                        try:
                            if isinstance(widget,QLineEdit): widget.setText(value or "")
                            elif isinstance(widget,QTextEdit): widget.setHtml(value.get("html","")) if isinstance(value,dict) else widget.setPlainText(str(value or ""))
                            elif isinstance(widget,QComboBox):
                                text=value.get("text","") if isinstance(value,dict) else str(value); index=widget.findText(text)
                                if index>=0: widget.setCurrentIndex(index)
                            elif isinstance(widget,QSpinBox): widget.setValue(int(value))
                            elif isinstance(widget,QCheckBox): widget.setChecked(bool(value))
                            else: widget.setCurrentIndex(max(0,min(widget.count()-1,int(value))))
                        finally: widget.blockSignals(False)
                self.update_mode_ui(); self.update_domain_ui(); self.update_dashboard()
                if hasattr(self,"refresh_image_gallery"): self.refresh_image_gallery()
                if hasattr(self,"update_blf_status"): self.update_blf_status()
                if hasattr(self,"_u_display_current_structured_result"): self._u_display_current_structured_result()
                try: os.remove(path)
                except OSError: pass
            except Exception as error: print("[THEME STATE RESTORE ERROR]",repr(error))

    def switch_unified_theme(self, target_theme):
            import os, sys, subprocess
            from pathlib import Path
            from PySide6.QtWidgets import QMessageBox, QApplication

            # 1. 환경 변수 확인 후, 없으면 현재 파일 폴더 기준으로 unified_launcher.py 경로 지정
            launcher = os.environ.get("VA_UNIFIED_LAUNCHER")
            if not launcher or not os.path.isfile(launcher):
                base_dir = Path(__file__).resolve().parent
                launcher = str(base_dir / "unified_launcher.py")

            # 2. 파일이 진짜 존재하는지 최종 확인
            if not os.path.isfile(launcher):
                QMessageBox.warning(self, "테마 전환", "unified_launcher.py 경로를 찾지 못했습니다.")
                return

            # 3. 상태 저장 후 재실행
            if not self._theme_save_state(): 
                return

            base_dir = str(Path(launcher).resolve().parent)
            subprocess.Popen([sys.executable, launcher, "--theme", target_theme, "--restore-state"], cwd=base_dir)
            QApplication.instance().quit()

    def init_ui(self):
            layout = QVBoxLayout(self)
            layout.setContentsMargins(12, 12, 12, 12)
            layout.setSpacing(8)
    
            left_layout = QVBoxLayout()
            left_layout.setContentsMargins(6, 5, 6, 5)
            left_layout.setSpacing(6)
    
            center_layout = QVBoxLayout()
            center_layout.setContentsMargins(6, 5, 6, 5)
            center_layout.setSpacing(6)
    
            right_layout = QVBoxLayout()
            right_layout.setContentsMargins(6, 5, 6, 5)
            right_layout.setSpacing(2)
    
            header_layout = QHBoxLayout()
    
            configuration_header_row = QHBoxLayout()
            configuration_header_row.setContentsMargins(0, 0, 0, 0)
            configuration_header_row.setSpacing(6)
            left_header = QLabel("⚙️ Configuration")
            left_header.setObjectName("sectionTitle")
            self.quick_tc_open_btn = QPushButton("빠른 입력")
            self.quick_tc_open_btn.setObjectName("secondaryButton")
            self.quick_tc_open_btn.setMinimumHeight(28)
            self.quick_tc_open_btn.setMaximumWidth(110)
            self.quick_tc_open_btn.setToolTip("처음 사용하는 사람을 위한 간단한 TC 입력 창을 엽니다.")
            self.quick_tc_open_btn.clicked.connect(self.open_mode_quick_dialog)
            configuration_header_row.addWidget(left_header, 1)
            configuration_header_row.addWidget(self.quick_tc_open_btn)
            left_layout.addLayout(configuration_header_row)
    
            right_header = QLabel("📋 Prompt Preview")
            right_header.setObjectName("sectionTitle")
            center_layout.addWidget(right_header)
    
            self.dashboard = QLabel()
            self.dashboard.setObjectName("dashboardLabel")
            self.dashboard.setFixedHeight(30)
            center_layout.addWidget(self.dashboard)
    
            self.dashboard.setStyleSheet("""
                font-size: 9pt;
                font-weight: bold;
                color: #3e5564;
            """)
    
            header_layout.addStretch()
            layout.addLayout(header_layout)
    
            left_layout.addWidget(QLabel("QA Domain"))
            domain_row = QHBoxLayout()
            self.qa_domain = QComboBox()
            self.qa_domain.addItems(list(self.domain_profiles.keys()))
            self.qa_domain.currentTextChanged.connect(self.update_domain_ui)
            self.edit_custom_profile_btn = QPushButton("Edit Custom")
            self.edit_custom_profile_btn.setMaximumWidth(100)
            self.edit_custom_profile_btn.clicked.connect(self.open_custom_profile)
            domain_row.addWidget(self.qa_domain, 1)
            domain_row.addWidget(self.edit_custom_profile_btn)
            left_layout.addLayout(domain_row)
    
            self.mode = QComboBox()
            self.mode.addItems([
                "🔍 Validation Analysis",
                "✨ TC Generation",
                "📝 TC Review"
            ])
    
            self.mode.currentTextChanged.connect(self.update_dashboard)
            self.mode.currentTextChanged.connect(self.update_mode_ui)
            self.mode.currentTextChanged.connect(self.update_quick_button_label)
    
            self.prompt_level = QComboBox()
            self.prompt_level.addItems([
                "Basic",
                "Detailed",
                "Expert"
            ])
    
            config_label_layout = QHBoxLayout()
            config_label_layout.addWidget(QLabel("Mode"))
            config_label_layout.addWidget(QLabel("Prompt Level"))
            left_layout.addLayout(config_label_layout)
    
            config_combo_layout = QHBoxLayout()
            config_combo_layout.addWidget(self.mode)
            config_combo_layout.addWidget(self.prompt_level)
            left_layout.addLayout(config_combo_layout)
    
            left_layout.addWidget(QLabel("Template"))
    
            template_layout = QHBoxLayout()
            template_layout.setSpacing(5)
    
            self.template = QComboBox()
            self.template.setEditable(True)
            self.template.blockSignals(True)
            self.template.addItems(TEMPLATES.keys())
            self.load_template_list()
            self.template.blockSignals(False)
    
            self.template.currentTextChanged.connect(self.load_template)
            self.template.currentTextChanged.connect(self.update_dashboard)
    
            template_layout.addWidget(self.template, 1)
    
            template_manage_btn = QPushButton("▼")
            template_manage_btn.setFixedWidth(40)
            template_manage_btn.setToolTip("Template 선택 / 관리")
            template_manage_btn.clicked.connect(self.open_template_popup)
    
            template_layout.addWidget(template_manage_btn)
            left_layout.addLayout(template_layout)
    
            info_header = QHBoxLayout()
    
            info_title = QLabel("📋 TC Information")
            info_title.setStyleSheet("""
                font-size: 13pt;
                font-weight: bold;
                color: #38bdf8;
                padding-top: 4px;
                padding-bottom: 2px;
            """)
    
            clear_btn = QPushButton("Clear")
            clear_btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: #9ca3af;
                    border: none;
                    padding: 0px;
                    margin: 0px;
                }
                QPushButton:hover {
                    color: white;
                }
            """)
            clear_btn.setMaximumWidth(90)
            clear_btn.clicked.connect(self.clear_tc)
    
            info_header.addWidget(info_title, alignment=Qt.AlignVCenter)
            info_header.addStretch()
            info_header.addWidget(clear_btn, alignment=Qt.AlignVCenter)
            left_layout.addLayout(info_header)
    
            self.tc_name_label = QLabel("TC Name")
            left_layout.addWidget(self.tc_name_label)
    
            self.tc = QLineEdit()
            self.tc.setFixedHeight(34)
            left_layout.addWidget(self.tc)
            self.tc.textChanged.connect(self.update_dashboard)
    
            self.tc_generation_advanced_toggle = QPushButton("▶ 고급 설정 펼치기")
            self.tc_generation_advanced_toggle.setCheckable(True)
            self.tc_generation_advanced_toggle.setObjectName("secondaryButton")
            self.tc_generation_advanced_toggle.setFixedHeight(30)
            self.tc_generation_advanced_toggle.toggled.connect(self.update_tc_generation_beginner_ui)
            left_layout.addWidget(self.tc_generation_advanced_toggle)
            self.tc_generation_advanced_container = QWidget()
            self.tc_generation_advanced_layout = QVBoxLayout(self.tc_generation_advanced_container)
            self.tc_generation_advanced_layout.setContentsMargins(0, 0, 0, 0)
            self.tc_generation_advanced_layout.setSpacing(5)
            left_layout.addWidget(self.tc_generation_advanced_container)
    
            self.tc_generation_page_row = QWidget()
            self.tc_generation_page_row.setObjectName("tcGenerationPageRow")
            page_layout = QHBoxLayout(self.tc_generation_page_row)
            page_layout.setContentsMargins(0, 0, 0, 0)
            page_layout.setSpacing(6)
            self.tc_generation_basic_btn = QPushButton("기본 내용")
            self.tc_generation_execution_btn = QPushButton("시험 조건")
            self.tc_generation_sequence_btn = QPushButton("수행 순서")
            for button in (self.tc_generation_basic_btn, self.tc_generation_execution_btn, self.tc_generation_sequence_btn):
                button.setCheckable(True)
                button.setFixedHeight(30)
                button.setObjectName("secondaryButton")
            self.tc_generation_basic_btn.setChecked(True)
            self.tc_generation_basic_btn.clicked.connect(lambda: self.switch_tc_generation_page("basic"))
            self.tc_generation_execution_btn.clicked.connect(lambda: self.switch_tc_generation_page("execution"))
            self.tc_generation_sequence_btn.clicked.connect(lambda: self.switch_tc_generation_page("sequence"))
            page_layout.addWidget(self.tc_generation_basic_btn)
            page_layout.addWidget(self.tc_generation_execution_btn)
            page_layout.addWidget(self.tc_generation_sequence_btn)
            left_layout.addWidget(self.tc_generation_page_row)
    
            self.tc_generation_sequence_mode_row = QWidget()
            self.tc_generation_sequence_mode_row.setObjectName("tcGenerationSequenceRow")
            self.tc_generation_sequence_mode_row.setStyleSheet(
                "QWidget#tcGenerationSequenceRow { background: transparent; border: none; }"
            )
            sequence_mode_layout = QHBoxLayout(self.tc_generation_sequence_mode_row)
            sequence_mode_layout.setContentsMargins(0, 0, 0, 0)
            sequence_mode_layout.setSpacing(6)
            sequence_mode_label = QLabel("순서 생성")
            sequence_mode_label.setFixedWidth(58)
            sequence_mode_label.setStyleSheet("background: transparent; border: none; padding-left: 2px;")
            self.tc_generation_sequence_mode_combo = QComboBox()
            self.tc_generation_sequence_mode_combo.addItems([
                "AI 자동 생성",
                "사용자 흐름 우선",
                "사용자 순서 고정",
            ])
            self.tc_generation_sequence_mode_combo.setCurrentText(self.tc_generation_sequence_mode)
            self.tc_generation_sequence_mode_combo.setToolTip(
                "AI 자동 생성: 요구사항으로 전체 순서 생성\n"
                "사용자 흐름 우선: 입력 흐름을 상세 Step으로 확장, 비어 있으면 자동 생성\n"
                "사용자 순서 고정: 입력한 순서를 변경하지 않고 Expected Result만 보완"
            )
            self.tc_generation_sequence_mode_combo.currentTextChanged.connect(
                self.update_tc_generation_sequence_mode
            )
            sequence_mode_layout.addWidget(sequence_mode_label)
            sequence_mode_layout.addWidget(self.tc_generation_sequence_mode_combo, 1)
            left_layout.addWidget(self.tc_generation_sequence_mode_row)
    
            self.purpose_label = QLabel("Purpose")
            self.purpose_label.setContentsMargins(2, 3, 2, 2)
            left_layout.addWidget(self.purpose_label)
    
            self.purpose = RobustTcTextEdit()
            self.purpose.setObjectName("purposeEditor")
            self.purpose.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self.purpose.setFixedHeight(92)
            self.purpose.setSizePolicy(
                QSizePolicy.Expanding,
                QSizePolicy.Fixed
            )
            left_layout.addWidget(self.purpose)
    
            left_layout.addSpacing(4)
            self.expected_label = QLabel("Expected Result")
            self.expected_label.setContentsMargins(2, 3, 2, 2)
            self.expected_label.setStyleSheet(
                "background-color: #ffffff; color: #344451; "
                "padding: 1px 2px; margin: 0px; border: none;"
            )
            left_layout.addSpacing(4)
            left_layout.addWidget(self.expected_label)
    
            for mode_label in (
                self.tc_name_label,
                self.purpose_label,
                self.expected_label
            ):
                mode_label.setFixedHeight(20)
                mode_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                mode_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    
            self.expected = RobustTcTextEdit()
            self.expected.setObjectName("expectedEditor")
            self.expected.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self.expected.setFixedHeight(88)
            self.expected.setSizePolicy(
                QSizePolicy.Expanding,
                QSizePolicy.Fixed
            )
            left_layout.addWidget(self.expected)
    
            # Validation 전용 4분할 입력. 탭을 사용해 세로 높이를 늘리지 않고 UI 왜곡을 방지한다.
            self.validation_tabs = QTabWidget()
            self.validation_tabs.setObjectName("validationStructuredTabs")
            self.validation_tabs.setFixedHeight(224)
            self.validation_tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.validation_tabs.setStyleSheet(
                "QTabWidget::pane { border:1px solid #cbd8df; border-radius:4px; background:#ffffff; } "
                "QTabBar::tab { min-width:72px; padding:6px 8px; } "
                "QTabBar::tab:selected { color:#0b7f79; font-weight:700; }"
            )
            self.validation_preconditions = RobustTcTextEdit(); self.validation_preconditions.setPlaceholderText("시험 시작 전 조건을 번호로 입력하세요.")
            self.validation_steps = RobustTcTextEdit(); self.validation_steps.setPlaceholderText("실제 수행 동작을 Step 번호별로 입력하세요.")
            self.validation_expected_results = RobustTcTextEdit(); self.validation_expected_results.setPlaceholderText("Step 번호와 같은 번호로 기대 결과를 입력하세요. 예: 1. SignalName = Value")
            self.validation_actual_results = RobustTcTextEdit(); self.validation_actual_results.setPlaceholderText("실제로 관찰한 결과를 같은 번호로 입력하세요. 모르면 'BLF 분석 필요'로 입력할 수 있습니다.")
            for editor in (self.validation_preconditions,self.validation_steps,self.validation_expected_results,self.validation_actual_results):
                editor.setLineWrapMode(QTextEdit.WidgetWidth)
                editor.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding)
                editor.setViewportMargins(0, 0, 0, 12)
                editor.setStyleSheet("QTextEdit { padding-bottom: 14px; }")
                editor.textChanged.connect(self.update_validation_pair_status)
            self.validation_tabs.addTab(self.validation_preconditions,"Precondition")
            self.validation_tabs.addTab(self.validation_steps,"Steps")
            self.validation_tabs.addTab(self.validation_expected_results,"Expected")
            self.validation_tabs.addTab(self.validation_actual_results,"Actual")
            left_layout.addWidget(self.validation_tabs)
            validation_status_row = QHBoxLayout()
            validation_status_row.setContentsMargins(0, 0, 0, 0)
            validation_status_row.setSpacing(5)
            self.validation_pair_status = QLabel("Precondition 0 | Step 0 | Expected 0 | Actual 0")
            self.validation_pair_status.setWordWrap(False)
            self.validation_normalize_btn = QPushButton("붙여넣기 정리")
            self.validation_normalize_btn.setObjectName("smallButton")
            self.validation_normalize_btn.setFixedHeight(26)
            self.validation_normalize_btn.setMaximumWidth(96)
            self.validation_normalize_btn.setToolTip("현재 선택한 탭의 번호 항목을 자동 줄바꿈하고 공백을 정리합니다.")
            self.validation_normalize_btn.clicked.connect(self.normalize_active_validation_tab)
            validation_status_row.addWidget(self.validation_pair_status, 1)
            validation_status_row.addWidget(self.validation_normalize_btn, 0)
            left_layout.addLayout(validation_status_row)
    
            # 별도 위젯 없이 순수 레이아웃 여백만 사용한다.
            left_layout.addSpacing(6)
            # Validation Analysis에서만 표시되는 분석 목적 선택 영역
            self.analysis_purpose_label = QLabel("Analysis Purpose")
            self.analysis_purpose_label.setContentsMargins(0, 0, 0, 0)
            self.analysis_purpose_label.setFixedHeight(20)
            self.analysis_purpose_label.setStyleSheet(
                "QLabel { background-color: #ffffff; color: #344451; "
                "padding: 1px 2px; margin: 0px; border: none; }"
            )
            left_layout.addSpacing(5)
            left_layout.addWidget(self.analysis_purpose_label)
    
            self.analysis_purpose = QComboBox()
            self.analysis_purpose.setFixedHeight(34)
            self.analysis_purpose.addItems([
                "전체 분석",
                "PASS / FAIL 판정 지원",
                "가능한 원인 분석",
                "다음 확인 항목 제안",
                "제품 문제 / TC 문제 구분",
                "결함 등록 정보 정리",
                "직접 입력"
            ])
            self.analysis_purpose.setToolTip(
                "원하는 분석 목적을 선택하면 Analysis Question이 자동으로 채워집니다."
            )
            self.analysis_purpose.currentTextChanged.connect(
                self.apply_analysis_purpose_template
            )
            left_layout.addWidget(self.analysis_purpose)
    
            # Validation Analysis에서만 표시되는 사용자 질문 입력 영역
            self.analysis_question_guide = QLabel(
                "💡 궁금한 원인이나 다음 확인 항목을 구체적으로 적어주세요."
            )
            self.analysis_question_guide.setWordWrap(True)
            self.analysis_question_guide.setStyleSheet(
                "color: #607786; background-color: #f7fafb; "
                "border: 1px solid #d7e0e5; border-radius: 4px; "
                "font-weight: 500; padding: 4px 6px; font-size: 8pt;"
            )
            left_layout.addWidget(self.analysis_question_guide)
    
            left_layout.addSpacing(3)
            self.analysis_question_label = QLabel("Analysis Question")
            self.analysis_question_label.setContentsMargins(0, 0, 0, 0)
            self.analysis_question_label.setFixedHeight(20)
            self.analysis_question_label.setStyleSheet(
                "background-color: #ffffff; color: #344451; "
                "padding: 1px 2px; margin: 0px; border: none;"
            )
            left_layout.addSpacing(4)
            left_layout.addWidget(self.analysis_question_label)
    
            self.analysis_question = QTextEdit()
            self.analysis_question.setObjectName("analysisQuestionEditor")
            self.analysis_question.setFixedHeight(52)
            self.analysis_question.setPlaceholderText(
                "예:\n"
                "- 왜 인증 성공 이후 도어가 열리지 않았나요?\n"
                "- 제품 문제인지 TC 조건 문제인지 구분해주세요.\n"
                "- 다음 수행에서 확인할 항목을 순서대로 알려주세요."
            )
            self.analysis_question.setSizePolicy(
                QSizePolicy.Expanding,
                QSizePolicy.Preferred
            )
            left_layout.addWidget(self.analysis_question)
    
            self.attachment_list = QListWidget()
            self.attachment_list.setVisible(False)
            self.attachment_list.itemClicked.connect(
                self.show_attachment_preview
            )
    
            attach_btn = QPushButton("📎 Attach Screenshot")
            attach_btn.setObjectName("secondaryButton")
            attach_btn.setFixedHeight(30)
            attach_btn.clicked.connect(self.attach_file)
    
            copy_evidence_btn = QPushButton("📋 Copy Evidence Files")
            copy_evidence_btn.setObjectName("secondaryButton")
            copy_evidence_btn.setFixedHeight(30)
            copy_evidence_btn.clicked.connect(self.copy_evidence_files_only)
    
            self.tc_generation_signal_mode_label = QLabel("Signal 처리 방식")
            self.tc_generation_signal_mode = QComboBox()
            self.tc_generation_signal_mode.addItems(["경량 변형 · 원본명 + 고정 코드","완전 치환 · SIG_001","승인 후 · 원본 유지"])
            self.tc_generation_signal_mode.setCurrentIndex(0)
            self.tc_generation_signal_mode.setToolTip("경량 변형 예: CCU_ForcedPowerOffReq → CCU_ForcedPowerOffReq_X7")
            left_layout.addWidget(self.tc_generation_signal_mode_label)
            left_layout.addWidget(self.tc_generation_signal_mode)
            self.tc_generation_signal_notice = QLabel()
            self.tc_generation_signal_notice.setWordWrap(True)
            self.tc_generation_signal_notice.setFixedHeight(24)
            self.tc_generation_signal_notice.setStyleSheet(
                "QLabel { background: transparent; border: none; padding: 2px 4px; font-size: 8pt; }"
            )
            left_layout.addWidget(self.tc_generation_signal_notice)
            self.tc_generation_signal_mode.currentIndexChanged.connect(self.update_tc_generation_signal_notice)
            self.update_tc_generation_signal_notice()
    
            self.auto_tc_review = QCheckBox("TC 생성 결과 자동 Review Prompt 만들기")
            self.auto_tc_review.setChecked(True)
            self.auto_tc_review.setToolTip(
                "TC Generation 결과 JSON을 Paste하면 동일 Domain 기준의 2차 Review Prompt를 자동 생성하고 복사합니다."
            )
            self.auto_tc_review.setStyleSheet(
                "QCheckBox { background: transparent; border: none; padding: 5px 4px; font-weight: 600; } "
                "QCheckBox::indicator { width: 15px; height: 15px; }"
            )
            left_layout.addWidget(self.auto_tc_review)
            self.dbc_context_match_btn = QPushButton("DBC Context Match")
            self.dbc_context_match_btn.setObjectName("secondaryButton")
            self.dbc_context_match_btn.setToolTip("Signal 관련 TBD를 로컬 DBC 후보와 비교합니다. 거리/시간/영역 TBD는 유지합니다.")
            self.dbc_context_match_btn.clicked.connect(lambda: self.apply_dbc_combined_autocorrection(show_message=True))
            left_layout.addWidget(self.dbc_context_match_btn)
    
            # 세부 입력과 Signal 처리만 고급 설정에 포함합니다.
            # 자동 Review Prompt와 DBC Context Match는 기본 화면에 항상 표시합니다.
            for advanced_widget in (
                self.tc_generation_page_row,
            ):
                self.tc_generation_advanced_layout.addWidget(advanced_widget)
    
            analyze_btn = QPushButton("🚀 Prompt Generation")
            analyze_btn.setObjectName("primaryButton")
            analyze_btn.setFixedHeight(38)
            analyze_btn.clicked.connect(self.Prompt_Generation)
            left_layout.addWidget(analyze_btn)
    
            if ENABLE_GEMINI:
                self.gemini_analyze_btn = QPushButton("✦ Gemini Analysis")
                self.gemini_analyze_btn.setObjectName("geminiButton")
                self.gemini_analyze_btn.setFixedHeight(38)
                self.gemini_analyze_btn.clicked.connect(self.request_gemini_analysis)
                left_layout.addWidget(self.gemini_analyze_btn)
    
            btn_layout1 = QHBoxLayout()
            btn_layout1.setContentsMargins(0, 0, 0, 0)
            btn_layout1.setSpacing(6)
    
            save_btn = QPushButton("💾 Save Project")
            save_btn.clicked.connect(self.save_tc)
            btn_layout1.addWidget(save_btn)
    
            load_btn = QPushButton("📂 Load")
            load_btn.clicked.connect(self.load_tc)
            btn_layout1.addWidget(load_btn)
    
            left_layout.addLayout(btn_layout1)
    
            btn_layout2 = QHBoxLayout()
            btn_layout2.setContentsMargins(0, 0, 0, 0)
            btn_layout2.setSpacing(6)
    
            self.excel_btn = QPushButton("📊 Export Excel")
            self.excel_btn.clicked.connect(self.export_excel)
            btn_layout2.addWidget(self.excel_btn)
    
            left_layout.addLayout(btn_layout2)
    
    
            delete_btn = QPushButton("🗑")
            delete_btn.setMaximumWidth(40)
            delete_btn.clicked.connect(self.delete_tc)
    
            self.tc_search = QLineEdit()
            self.tc_search.setPlaceholderText("🔍 Search TC...")
            self.tc_search.textChanged.connect(self.filter_saved_tc)
    
            search_layout = QHBoxLayout()
            search_layout.addWidget(self.tc_search)
            search_layout.addWidget(delete_btn)
    
            self.saved_tc_list = QListWidget()
            self.saved_tc_list.setMinimumHeight(80)
            self.saved_tc_list.setSizePolicy(
                QSizePolicy.Expanding,
                QSizePolicy.Expanding
            )
            self.saved_tc_list.itemDoubleClicked.connect(
                self.load_saved_tc
            )
    
            self.image_scroll = QScrollArea()
            self.image_scroll.setWidgetResizable(True)
            self.image_scroll.setMinimumHeight(85)
            self.image_scroll.setMaximumHeight(115)
            self.image_scroll.setSizePolicy(
                QSizePolicy.Expanding,
                QSizePolicy.Fixed
            )
            self.image_scroll.setObjectName("imageGallery")
            self.image_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self.image_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    
            self.image_container = QWidget()
            self.image_container.setObjectName("imageContainer")
    
            self.image_layout = QGridLayout(self.image_container)
            self.image_layout.setContentsMargins(10, 10, 10, 10)
            self.image_layout.setHorizontalSpacing(10)
            self.image_layout.setVerticalSpacing(10)
            self.image_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
    
            self.image_scroll.setWidget(self.image_container)
    
            self.result = QTextEdit()
            self.result.setObjectName("promptPreview")
            self.result.document().setDocumentMargin(12)
            self.result.setLineWrapMode(QTextEdit.WidgetWidth)
            self.result.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
            self.result.setPlaceholderText(
                "🚀 Prompt Generation을 실행하면 Prompt가 표시됩니다."
            )
            self.result.setReadOnly(True)
            self.result.setSizePolicy(
                QSizePolicy.Expanding,
                QSizePolicy.Expanding
            )
    
            center_layout.addWidget(self.result, 3)
    
            ai_result_header = QHBoxLayout()
            ai_result_title = QLabel("🤖 AI Analysis Result")
            ai_result_title.setObjectName("subSectionTitle")
    
            paste_result_btn = QPushButton("📋 Paste")
            paste_result_btn.setObjectName("smallButton")
            paste_result_btn.setMaximumWidth(90)
            paste_result_btn.setToolTip("AI의 JSON 코드 블록에서 Copy를 누른 뒤 이 버튼을 누르세요.")
            paste_result_btn.clicked.connect(self.paste_ai_result)
    
            clear_result_btn = QPushButton("Clear")
            clear_result_btn.setObjectName("smallButton")
            clear_result_btn.setMaximumWidth(70)
            clear_result_btn.clicked.connect(self.clear_ai_result)
    
            ai_result_header.addWidget(ai_result_title)
            ai_result_header.addStretch()
            ai_result_header.addWidget(paste_result_btn)
            ai_result_header.addWidget(clear_result_btn)
    
            center_layout.addLayout(ai_result_header)
    
            self.ai_result = QTextEdit()
            self.ai_result.setObjectName("aiResultEditor")
            self.ai_result.setPlaceholderText(
                "AI의 분석 결과를 복사한 뒤 Paste 버튼을 누르거나 Ctrl+V로 붙여넣으세요."
            )
            self.ai_result.setAcceptRichText(False)
            self.ai_result.setMinimumHeight(180)
            self.ai_result.setSizePolicy(
                QSizePolicy.Expanding,
                QSizePolicy.Expanding
            )
    
            center_layout.addWidget(self.ai_result, 2)
    
            self.structured_result = QScrollArea()
            self.structured_result.setWidgetResizable(True)
            self.structured_result.setObjectName("structuredResultScroll")
            self.structured_result.setStyleSheet("""
                QScrollArea#structuredResultScroll {
                    background-color: #f7fafb;
                    border: 1px solid #cbd6dd;
                    border-radius: 6px;
                }
                QScrollArea#structuredResultScroll > QWidget > QWidget {
                    background-color: #f7fafb;
                }
            """)
    
            self.structured_result_container = QWidget()
            self.structured_result_container.setStyleSheet(
                "background-color: #f7fafb; color: #263746;"
            )
            self.structured_result_layout = QVBoxLayout(
                self.structured_result_container
            )
            self.structured_result_layout.setContentsMargins(10, 10, 10, 10)
            self.structured_result_layout.setSpacing(10)
    
            self.structured_result.setWidget(
                self.structured_result_container
            )
    
            center_layout.addWidget(self.structured_result, 3)
    
            self.automotive_panel = QWidget()
            self.automotive_panel.setObjectName("automotiveContentPanel")
            self.automotive_panel.setStyleSheet("QWidget#automotiveContentPanel { background: transparent; border: none; }")
            automotive_layout = QVBoxLayout(self.automotive_panel)
            automotive_layout.setContentsMargins(0, 0, 0, 0)
            automotive_layout.setSpacing(4)
            self.log_title = QLabel("📡 Automotive Log Analysis")
            self.log_title.setObjectName("sectionTitle")
            self.log_title.setContentsMargins(0, 0, 0, 0)
            automotive_layout.addWidget(self.log_title)
    
            self.log_guide = QLabel("BLF 원본은 전송하지 않고 로컬 Decode 요약만 활용합니다.")
            self.log_guide.setWordWrap(True)
            self.log_guide.setFixedHeight(34)
            self.log_guide.setStyleSheet("color:#607786;font-size:8pt;padding:2px;")
            automotive_layout.addWidget(self.log_guide)
    
            self.file_attach_row = QWidget()
            blf_button_layout = QHBoxLayout(self.file_attach_row)
            blf_button_layout.setContentsMargins(0,0,0,0)
            blf_button_layout.setSpacing(5)
            self.attach_blf_btn = QPushButton("Attach BLF")
            self.attach_blf_btn.setObjectName("secondaryButton")
            self.attach_blf_btn.clicked.connect(self.attach_blf_file)
            self.attach_dbc_btn = QPushButton("Attach DBCs")
            self.attach_dbc_btn.setObjectName("secondaryButton")
            self.attach_dbc_btn.setToolTip("여러 DBC 파일을 동시에 선택할 수 있습니다.")
            self.attach_dbc_btn.clicked.connect(self.attach_dbc_file)
            blf_button_layout.addWidget(self.attach_blf_btn)
            blf_button_layout.addWidget(self.attach_dbc_btn)
            automotive_layout.addWidget(self.file_attach_row)
            self.signal_tools_row = QWidget()
            signal_tool_row = QHBoxLayout(self.signal_tools_row)
            signal_tool_row.setContentsMargins(0,0,0,0)
            signal_tool_row.setSpacing(5)
            self.signal_mapping_btn = QPushButton("신호 찾기 / 지정")
            self.signal_mapping_btn.setObjectName("secondaryButton")
            self.signal_mapping_btn.clicked.connect(self.open_signal_mapping_dialog)
            signal_tool_row.addWidget(self.signal_mapping_btn)
            self.signal_set_manager_btn = QPushButton("신호 세트")
            self.signal_set_manager_btn.setObjectName("secondaryButton")
            self.signal_set_manager_btn.clicked.connect(self.open_signal_set_manager)
            signal_tool_row.addWidget(self.signal_set_manager_btn)
            transmission_row = QHBoxLayout()
            transmission_label = QLabel("AI 전송 모드")
            transmission_label.setFixedWidth(76)
            self.ai_transmission_mode = QComboBox()
            self.ai_transmission_mode.addItems([
                "1. 보안 기본: TC 원문 미포함 + 익명 로컬 요약",
                "2. 의미 보존 변환: 문장 유지 + 전체 식별자 별칭",
                "3. 승인 후 원문 포함: TC 원문 + 실제 Signal명",
            ])
            self.ai_transmission_mode.setCurrentIndex(1)
            self.ai_transmission_mode.setToolTip(
                "사내 AI 입력 허용 범위가 확인되기 전에는 보안 기본 모드를 사용하세요."
            )
            transmission_row.addWidget(transmission_label)
            transmission_row.addWidget(self.ai_transmission_mode, 1)
            automotive_layout.addLayout(transmission_row)
            self.ai_transmission_notice = QLabel()
            self.ai_transmission_notice.setWordWrap(False)
            self.ai_transmission_notice.setFixedHeight(30)
            self.ai_transmission_notice.setToolTip("TC 원문/BLF 원본/파일명/실제 Signal명/raw payload 제외, 익명 로컬 요약만 포함")
            automotive_layout.addWidget(self.ai_transmission_notice)
            self.ai_transmission_mode.currentIndexChanged.connect(
                self.update_ai_transmission_mode_notice
            )
            self.update_ai_transmission_mode_notice()
    
            self.anonymize_signals_for_ai = QCheckBox("실제 신호명 숨김")
            self.anonymize_signals_for_ai.setChecked(True)
            signal_tool_row.addWidget(self.anonymize_signals_for_ai)
            automotive_layout.addWidget(self.signal_tools_row)
            self.preferred_signal_status = QLabel("우선 선택 신호s: 0개")
            self.signal_mapping_status = QLabel("Signal Mapping: 0개 | AUTO 0 | REVIEW 0")
            automotive_layout.addWidget(self.preferred_signal_status)
            automotive_layout.addWidget(self.signal_mapping_status)
    
            self.time_labels_row = QWidget()
            time_label_layout = QHBoxLayout(self.time_labels_row)
            time_label_layout.setContentsMargins(0,0,0,0)
            time_label_layout.addWidget(QLabel("Start sec"))
            time_label_layout.addWidget(QLabel("End sec"))
            automotive_layout.addWidget(self.time_labels_row)
    
            self.time_inputs_row = QWidget()
            time_input_layout = QHBoxLayout(self.time_inputs_row)
            time_input_layout.setContentsMargins(0,0,0,0)
            self.blf_start_time = QLineEdit()
            self.blf_start_time.setPlaceholderText("예: 10.0")
            self.blf_end_time = QLineEdit()
            self.blf_end_time.setPlaceholderText("예: 15.0")
            time_input_layout.addWidget(self.blf_start_time)
            time_input_layout.addWidget(self.blf_end_time)
            automotive_layout.addWidget(self.time_inputs_row)
    
            self.signal_filter_label = QLabel("Signal Filter (comma separated)")
            automotive_layout.addWidget(self.signal_filter_label)
            self.signal_filter = QLineEdit()
            self.signal_filter.setText(
                "NFC, UWB, BLE, Auth, Key, Door, Lock, Unlock, Session, Error, Fail, Timeout, Status"
            )
            self.signal_filter.setPlaceholderText("비워두면 모든 변경 신호 포함")
            self.signal_filter.setToolTip(
                "신호명 또는 메시지명에 포함될 키워드입니다. 쉼표로 구분하세요."
            )
            automotive_layout.addWidget(self.signal_filter)
    
            self.tp_row = QWidget()
            tp_layout = QHBoxLayout(self.tp_row)
            tp_layout.setContentsMargins(0,0,0,0)
            tp_layout.addWidget(QLabel("TP / UDS"))
            self.tp_mode = QComboBox()
            self.tp_mode.addItems(["Auto ISO-TP", "Off"])
            self.tp_mode.setToolTip("Auto ISO-TP는 Normal Addressing의 SF/FF/CF/FC를 자동 탐지합니다.")
            self.tp_can_ids = QLineEdit()
            self.tp_can_ids.setPlaceholderText("TP CAN IDs (예: 0x7E0,0x7E8) / 빈칸=자동")
            self.tp_can_ids.setToolTip("오탐 방지를 위해 TP CAN ID를 쉼표로 지정할 수 있습니다.")
            tp_layout.addWidget(self.tp_mode)
            tp_layout.addWidget(self.tp_can_ids, 1)
            automotive_layout.addWidget(self.tp_row)
    
            self.event_limit_row = QWidget()
            event_limit_layout = QHBoxLayout(self.event_limit_row)
            event_limit_layout.setContentsMargins(0,0,0,0)
            event_limit_layout.addWidget(QLabel("AI Event Limit"))
            self.ai_event_limit = QSpinBox()
            self.ai_event_limit.setRange(10, 100)
            self.ai_event_limit.setValue(40)
            self.ai_event_limit.setToolTip("AI 프롬프트에 넣을 최대 핵심 이벤트 수")
            event_limit_layout.addWidget(self.ai_event_limit)
            automotive_layout.addWidget(self.event_limit_row)
    
            self.parse_blf_btn = QPushButton("Parse BLF Locally")
            self.parse_blf_btn.setObjectName("primaryButton")
            self.parse_blf_btn.clicked.connect(self.parse_blf_locally)
            automotive_layout.addWidget(self.parse_blf_btn)
            self.tc_blf_validate_btn = QPushButton("TC-BLF Auto Validation")
            self.tc_blf_validate_btn.setMinimumHeight(34)
            self.tc_blf_validate_btn.setObjectName("secondaryButton")
            self.tc_blf_validate_btn.setToolTip("Expected Results의 Signal 조건을 DBC로 Decode한 BLF Timeline과 로컬 비교합니다.")
            self.tc_blf_validate_btn.clicked.connect(self.run_tc_blf_auto_validation)
            automotive_layout.addWidget(self.tc_blf_validate_btn)
    
            self.blf_status_label = QLabel("BLF: 미선택 | DBC: 선택 사항")
            self.blf_status_label.setWordWrap(True)
            self.blf_status_label.setStyleSheet(
                "color: #526a78; background-color: #f5f8fa; "
                "border: 1px solid #d7e0e5; border-radius: 4px; "
                "padding: 5px; font-size: 8pt;"
            )
            automotive_layout.addWidget(self.blf_status_label)
    
            self.blf_summary_preview = QTextEdit()
            self.blf_summary_preview.setReadOnly(True)
            self.blf_summary_preview.setMinimumHeight(55)
            self.blf_summary_preview.setMaximumHeight(70)
            self.blf_summary_preview.setPlaceholderText("문제 구간의 BLF 요약이 여기에 표시됩니다.")
            automotive_layout.addWidget(self.blf_summary_preview)
    
            right_layout.addWidget(self.automotive_panel)
    
            self.domain_evidence_panel = QGroupBox("Domain Evidence")
            de_layout = QVBoxLayout(self.domain_evidence_panel)
            self.domain_evidence_guide = QLabel("현재 QA Domain에서 사용하는 TXT, LOG, JSON, CSV, HAR 등의 증적을 첨부하세요.")
            self.domain_evidence_guide.setWordWrap(True)
            self.domain_evidence_list = QListWidget()
            self.domain_evidence_list.setMaximumHeight(100)
            attach_domain_btn = QPushButton("Attach Evidence Files")
            attach_domain_btn.clicked.connect(self.attach_domain_evidence)
            de_layout.addWidget(self.domain_evidence_guide)
            de_layout.addWidget(self.domain_evidence_list)
            de_layout.addWidget(attach_domain_btn)
            right_layout.addWidget(self.domain_evidence_panel)
    
            evidence_title = QLabel("📷 Image Preview")
            evidence_title.setObjectName("sectionTitle")
    
            right_layout.addWidget(evidence_title)
            right_layout.addWidget(self.image_scroll)
            right_layout.addWidget(attach_btn)
            right_layout.addWidget(copy_evidence_btn)
            right_layout.addLayout(search_layout)
    
            saved_title = QLabel("📁 Saved Test Cases")
            saved_title.setObjectName("subSectionTitle")
    
            right_layout.addWidget(saved_title)
            right_layout.addWidget(self.saved_tc_list, 1)
    
            left_widget = QWidget()
            left_widget.setObjectName("panel")
            left_widget.setLayout(left_layout)
            left_widget.setMinimumWidth(300)
            left_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding)
            left_layout.setAlignment(Qt.AlignTop)
    
            # 작은 화면에서는 입력창을 눌러 찌그러뜨리지 않고 왼쪽 패널만 세로 스크롤한다.
            self.left_panel_scroll = QScrollArea()
            self.left_panel_scroll.setObjectName("leftPanelScroll")
            self.left_panel_scroll.setWidgetResizable(True)
            self.left_panel_scroll.setFrameShape(QScrollArea.NoFrame)
            self.left_panel_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.left_panel_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self.left_panel_scroll.setWidget(left_widget)
            self.left_panel_scroll.setMinimumWidth(300)
            self.left_panel_scroll.setStyleSheet(
                "QScrollArea#leftPanelScroll { background: transparent; border: none; }"
            )
    
            center_widget = QWidget()
            center_widget.setObjectName("panel")
            center_widget.setLayout(center_layout)
            center_widget.setMinimumSize(400, 0)
    
            right_widget = QWidget()
            right_widget.setObjectName("panel")
            right_widget.setLayout(right_layout)
            right_widget.setMinimumSize(320, 0)
    
            splitter = QSplitter(Qt.Horizontal)
            splitter.setObjectName("mainSplitter")
            splitter.addWidget(self.left_panel_scroll)
            splitter.addWidget(center_widget)
            splitter.addWidget(right_widget)
    
            splitter.setSizes([360, 480, 360])
            splitter.setStretchFactor(0, 3)
            splitter.setStretchFactor(1, 4)
            splitter.setStretchFactor(2, 3)
    
            splitter.setCollapsible(0, False)
            splitter.setCollapsible(1, False)
            splitter.setCollapsible(2, False)
    
            layout.addWidget(splitter, 1)
            self.setLayout(layout)
            self.update_quick_button_label()
            self.build_unified_domain_workspace()

    def resizeEvent(self, event):
            """창 크기 변경 시 새 UI도 함께 조정한다."""
            super().resizeEvent(event)
            if hasattr(self,'u_shell'):
                self.u_shell.setGeometry(self.rect()); self.u_shell.raise_(); QTimer.singleShot(0,self._u_refresh_auto_wrap)
            if hasattr(self, "purpose") and hasattr(self, "expected"):
                self.apply_responsive_input_heights(max(event.size().height(), 600))

    def current_domain_profile(self):
            return profile_for(self.qa_domain.currentText()) if hasattr(self,"qa_domain") else profile_for("Automotive CANoe")

    def update_domain_ui(self):
            profile=self.current_domain_profile()
            is_auto=bool(profile.get("automotive_tools"))
            if hasattr(self,"automotive_panel"):
                self.automotive_panel.setVisible(is_auto)
                self.domain_evidence_panel.setVisible(not is_auto)
            if hasattr(self,"edit_custom_profile_btn"):
                self.edit_custom_profile_btn.setVisible(self.qa_domain.currentText()=="Custom")
            self.update_mode_ui()
            self.update_dashboard()

    def apply_domain_labels(self):
            """현재 Mode에 맞는 라벨을 적용하고 TC Review 라벨 덮어쓰기를 방지한다."""
            profile = self.current_domain_profile()
            mode = self.mode.currentText()
    
            if "Validation Analysis" in mode:
                labels = profile.get("analysis", [
                    "TC Name",
                    "TC Definition / Expected Behavior",
                    "Actual Result / Issue"
                ])
            elif "TC Review" in mode:
                labels = [
                    "TC Name",
                    "TC Purpose / Preconditions / Test Steps",
                    "Expected Result / Pass Criteria"
                ]
            else:
                labels = [
                    "1. 기능 이름",
                    "2. 요구사항 및 동작",
                    "3. 추가 조건 (선택)"
                ]
    
            self.tc_name_label.setText(labels[0])
            self.purpose_label.setText(labels[1])
            self.expected_label.setText(labels[2])
            if "TC Generation" in mode:
                self.tc.setPlaceholderText("예: 자동 도어 잠금")
                self.purpose.setPlaceholderText("사양 원문을 그대로 붙여넣으세요. 예: 인증 성공 및 모든 도어 CLOSED 시 자동 잠금을 수행한다.")
                self.expected.setPlaceholderText("초기 상태, 고정할 시험 순서, 꼭 필요한 합격 조건만 적으세요. 비워도 됩니다.")
            else:
                self.tc.setPlaceholderText(f"{labels[0]} 입력")
                self.purpose.setPlaceholderText(f"{labels[1]} 입력")
                self.expected.setPlaceholderText(f"{labels[2]} 입력")

    def open_custom_profile(self):
            if not os.path.isfile(CUSTOM_PROFILE_PATH):
                with open(CUSTOM_PROFILE_PATH, "w", encoding="utf-8") as file:
                    json.dump(DEFAULT_CUSTOM_PROFILE, file, ensure_ascii=False, indent=2)
            try:
                if sys.platform.startswith("win"):
                    os.startfile(CUSTOM_PROFILE_PATH)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", CUSTOM_PROFILE_PATH])
                else:
                    subprocess.Popen(["xdg-open", CUSTOM_PROFILE_PATH])
            except Exception as error:
                QMessageBox.information(
                    self, "Custom Profile",
                    f"다음 파일을 편집하세요:\n{CUSTOM_PROFILE_PATH}\n\n{error}"
                )

    def set_widget_visible_keep_space(self, widget, visible):
            """숨긴 모드 전용 위젯의 공간도 제거해 TC Generation 입력창 잘림을 방지한다."""
            if widget is None:
                return
            size_policy = widget.sizePolicy()
            size_policy.setRetainSizeWhenHidden(False)
            widget.setSizePolicy(size_policy)
            widget.setVisible(visible)
            widget.updateGeometry()

    def apply_analysis_purpose_template(self, purpose_name):
            if not hasattr(self, "analysis_question"):
                return
    
            templates = {
                "전체 분석": (
                    "TC 판정, 문제가 발생한 Step, 기대 결과와 실제 결과의 차이, "
                    "가능한 원인, 부족한 정보, 다음 확인 항목과 리스크를 분석해주세요."
                ),
                "PASS / FAIL 판정 지원": (
                    "현재 관찰 결과로 TC를 PASS, FAIL 또는 INCONCLUSIVE로 판단할 수 있는지 "
                    "근거와 함께 알려주세요."
                ),
                "가능한 원인 분석": (
                    "Actual Result가 발생한 가능한 원인을 우선순위로 정리하고, "
                    "확인된 사실과 추론을 구분해주세요."
                ),
                "다음 확인 항목 제안": (
                    "다음 수행에서 확인할 항목을 실행 순서대로 제시하고, "
                    "각 항목에서 무엇을 확인해야 하는지 알려주세요."
                ),
                "제품 문제 / TC 문제 구분": (
                    "제품 동작 문제, TC 정의 문제, 수행 조건 문제, 환경 문제 가능성을 구분하고 "
                    "각 판단 근거를 알려주세요."
                ),
                "결함 등록 정보 정리": (
                    "결함 등록에 필요한 현상 요약, 재현 조건, 기대 결과, 실제 결과, "
                    "부족한 정보와 추가 확인 항목을 정리해주세요."
                )
            }
    
            if purpose_name == "직접 입력":
                self.analysis_question.clear()
                self.analysis_question.setFocus()
                return
    
            question = templates.get(purpose_name, templates["전체 분석"])
            self.analysis_question.setPlainText(question)

    def update_mode_ui(self):
            mode = self.mode.currentText()
    
            if "Validation Analysis" in mode:
                self.tc_name_label.setText("TC Name")
                self.purpose_label.setText("TC Information")
                self.expected_label.setText("Actual Result / Issue")
    
                self.tc.setPlaceholderText("예: TC_NFC_AUTH_001")
    
                self.purpose.setPlaceholderText(
                    "[Precondition]\n\n"
                    "[Test Steps]\n"
                    "1. \n"
                    "2. \n\n"
                    "[Expected Result]\n"
                )
    
                self.expected.setPlaceholderText(
                    "[Problem Step]\n\n"
                    "[Actual Result]\n\n"
                    "[Error Message / Observed Information]\n\n"
                    "[Reproduction]\n"
                )
                prompt_text = "🚀 TC Issue Analysis Prompt"
                gemini_text = "✦ Gemini TC Issue Analysis"
                excel_text = "📊 Export Validation XLSX"
            elif "TC Review" in mode:
                self.tc_name_label.setText("TC Name")
                self.purpose_label.setText("TC Purpose / Preconditions / Test Steps")
                self.expected_label.setText("Expected Result")
                self.tc.setPlaceholderText("예: TC_NFC_AUTH_001")
                self.purpose.setPlaceholderText("검토할 TC의 목적, 사전 조건 및 Test Step을 입력하세요.")
                self.expected.setPlaceholderText("검토할 Expected Result와 판정 기준을 입력하세요.")
                prompt_text = "🚀 TC Review Prompt"
                gemini_text = "✦ Gemini TC Review"
                excel_text = "📊 Export TC Review XLSX"
            else:
                self.tc_name_label.setText("1. 기능 이름")
                self.purpose_label.setText("2. 요구사항 및 동작")
                self.expected_label.setText("3. 추가 조건 (선택)")
                self.tc.setPlaceholderText("예: 자동 도어 잠금")
                self.purpose.setPlaceholderText("사양 원문을 그대로 붙여넣으세요. 예: 인증 성공 및 모든 도어 CLOSED 시 자동 잠금을 수행한다.")
                self.expected.setPlaceholderText("초기 상태, 고정할 시험 순서, 꼭 필요한 합격 조건만 적으세요. 비워도 됩니다.")
                prompt_text = "🚀 TC Generation Prompt"
                gemini_text = "✦ Gemini TC Generation"
                excel_text = "📊 Export Generated TC XLSX"
    
            is_validation_analysis = "Validation Analysis" in mode
            is_tc_generation = "TC Generation" in mode
            is_tc_review = "TC Review" in mode
            is_structured_mode = is_validation_analysis or is_tc_review
            if hasattr(self, "validation_tabs"):
                self.validation_tabs.setVisible(is_structured_mode)
                self.validation_pair_status.setVisible(is_structured_mode)
                if hasattr(self, "validation_normalize_btn"):
                    self.validation_normalize_btn.setVisible(is_structured_mode)
                self.purpose_label.setVisible(not is_structured_mode)
                self.purpose.setVisible(not is_structured_mode)
                self.expected_label.setVisible(not is_structured_mode)
                self.expected.setVisible(not is_structured_mode)
                self.validation_tabs.setTabText(0, "Precondition")
                self.validation_tabs.setTabText(1, "Steps")
                self.validation_tabs.setTabText(2, "Expected")
                self.validation_tabs.setTabText(3, "Review 기준" if is_tc_review else "Actual")
                if is_tc_review:
                    self.validation_actual_results.setPlaceholderText("모호성, 누락, 실행 가능성, 판정 기준 등 중점 Review 기준을 입력하세요.")
                else:
                    self.validation_actual_results.setPlaceholderText("실제로 관찰한 결과를 같은 번호로 입력하세요. 모르면 'BLF 분석 필요'로 입력할 수 있습니다.")
                if is_structured_mode:
                    self.update_validation_pair_status()
            if hasattr(self, "tc_generation_page_row") and is_tc_generation:
                self.load_tc_generation_page_values()
            if hasattr(self, "tc_generation_advanced_container"):
                self.update_tc_generation_beginner_ui()
    
            if hasattr(self, "auto_tc_review"):
                self.set_widget_visible_keep_space(self.auto_tc_review, is_tc_generation)
            if hasattr(self, "dbc_context_match_btn"):
                self.set_widget_visible_keep_space(self.dbc_context_match_btn, is_tc_generation)
            if hasattr(self, "analysis_question_label"):
                self.set_widget_visible_keep_space(
                    self.analysis_purpose_label,
                    is_validation_analysis
                )
                self.set_widget_visible_keep_space(
                    self.analysis_purpose,
                    is_validation_analysis
                )
                self.set_widget_visible_keep_space(
                    self.analysis_question_label,
                    is_validation_analysis
                )
                self.set_widget_visible_keep_space(
                    self.analysis_question_guide,
                    is_validation_analysis
                )
                self.set_widget_visible_keep_space(
                    self.analysis_question,
                    is_validation_analysis
                )
                if is_validation_analysis and not self.analysis_question.toPlainText().strip():
                    self.apply_analysis_purpose_template(
                        self.analysis_purpose.currentText()
                    )
    
    
            # Mode-focused UI: show only tools relevant to the current task.
            is_review = "TC Review" in mode
            validation_only = [
                self.ai_transmission_mode, self.ai_transmission_notice,
                self.time_labels_row, self.time_inputs_row, self.signal_filter_label, self.signal_filter,
                self.tp_row, self.event_limit_row, self.parse_blf_btn, self.tc_blf_validate_btn,
                self.blf_status_label, self.blf_summary_preview, self.attach_blf_btn,
            ]
            for widget in validation_only:
                widget.setVisible(is_validation_analysis)
            self.attach_dbc_btn.setVisible(True)
            self.log_title.setText("📡 Automotive Log Analysis" if is_validation_analysis else "🧭 DBC & Signal Support")
            self.log_guide.setText(
                "BLF 원본은 전송하지 않고 로컬 Decode 요약만 활용합니다."
                if is_validation_analysis else
                "DBC 후보와 Signal Mapping을 TC 작성 보조에만 사용합니다."
            )
    
            self.apply_domain_labels()
            if hasattr(self, "tc_generation_advanced_toggle"):
                self.update_tc_generation_beginner_ui()
            if is_tc_generation:
                self.load_tc_generation_page_values()
            if "TC Review" in mode:
                self.tc.setPlaceholderText("예: TC_IAU_UWB_UNLOCK_001")
                self.purpose.setPlaceholderText(
                    "TC 목적, Preconditions, Test Steps를 순서대로 입력하세요."
                )
                self.expected.setPlaceholderText(
                    "각 Step의 Expected Result와 PASS 판정 기준을 입력하세요."
                )
            if hasattr(self, "purpose"):
                self.apply_responsive_input_heights(max(self.height(), 600))
            self.updateGeometry()
    
            if hasattr(self, "generate_btn"):
                self.generate_btn.setText(prompt_text)
            if hasattr(self, "gemini_analyze_btn"):
                self.gemini_analyze_btn.setText(gemini_text)
            if hasattr(self, "excel_btn"):
                self.excel_btn.setText(excel_text)

    def clear_tc(self):
            self.tc.clear()
            self.purpose.clear()
            self.expected.clear()
            if hasattr(self,"validation_preconditions"):
                self.validation_preconditions.clear(); self.validation_steps.clear()
                self.validation_expected_results.clear(); self.validation_actual_results.clear()
            if hasattr(self, "analysis_purpose"):
                self.analysis_purpose.setCurrentIndex(0)
            if hasattr(self, "analysis_question"):
                self.analysis_question.clear()
                self.apply_analysis_purpose_template("전체 분석")
    
            self.result.clear()
            self.ai_result.clear()
            self.current_ai_result_data = {}
            self.clear_structured_ai_result()
    
            self.generated_prompt = ""
            self.tc_generation_page = "basic"
            self.tc_generation_requirement = ""
            self.tc_generation_acceptance = ""
            self.tc_generation_preconditions = ""
            self.tc_generation_observations = ""
            self.tc_generation_sequence = ""
            self.tc_generation_checkpoints = ""
            self.tc_generation_sequence_mode = "사용자 흐름 우선"
            if hasattr(self, "tc_generation_sequence_mode_combo"):
                self.tc_generation_sequence_mode_combo.setCurrentText(self.tc_generation_sequence_mode)
            self.attachments = []
            self.attachment_list.clear()
    
            for index in reversed(range(self.image_layout.count())):
                widget = self.image_layout.itemAt(index).widget()
                if widget:
                    widget.deleteLater()
    
            self.refresh_image_gallery()
            self.update_dashboard()

    def open_template_popup(self):
            dialog = QDialog(self)
            dialog.setWindowTitle("Template")
            dialog.setModal(True)
            dialog.resize(380, 420)
    
            dialog.setStyleSheet("""
                QDialog {
                    background-color: #0f172a;
                }
                QLabel {
                    color: #cbd5e1;
                }
                QPushButton {
                    background-color: #1e293b;
                    color: #e2e8f0;
                    border: 1px solid #334155;
                    border-radius: 5px;
                    padding: 7px 10px;
                }
                QPushButton:hover {
                    background-color: #334155;
                }
                QPushButton#templateSelectButton {
                    text-align: left;
                }
                QPushButton#templateDeleteButton {
                    color: #f87171;
                    border: none;
                    background-color: transparent;
                    font-size: 12pt;
                    font-weight: bold;
                }
                QPushButton#templateDeleteButton:hover {
                    color: #ffffff;
                    background-color: #3f1d1d;
                }
            """)
    
            layout = QVBoxLayout(dialog)
            layout.setContentsMargins(12, 12, 12, 12)
            layout.setSpacing(6)
    
            title = QLabel("Template")
            title.setStyleSheet("""
                font-size: 13pt;
                font-weight: bold;
                color: #38bdf8;
                padding-bottom: 6px;
            """)
            layout.addWidget(title)
    
            template_names = [
                self.template.itemText(i)
                for i in range(self.template.count())
            ]
    
            for template_name in template_names:
                row = QHBoxLayout()
                row.setContentsMargins(0, 0, 0, 0)
                row.setSpacing(4)
    
                select_btn = QPushButton(template_name)
                select_btn.setObjectName("templateSelectButton")
                select_btn.setMinimumHeight(36)
                select_btn.clicked.connect(
                    lambda checked=False, name=template_name:
                    self.select_template_from_popup(name, dialog)
                )
                row.addWidget(select_btn, 1)
    
                if template_name not in TEMPLATES:
                    delete_btn = QPushButton("✕")
                    delete_btn.setObjectName("templateDeleteButton")
                    delete_btn.setFixedSize(36, 36)
                    delete_btn.setToolTip("이 Template 삭제")
                    delete_btn.clicked.connect(
                        lambda checked=False, name=template_name:
                        self.delete_template_from_popup(name, dialog)
                    )
                    row.addWidget(delete_btn)
    
                layout.addLayout(row)
    
            layout.addStretch()
    
            close_btn = QPushButton("Close")
            close_btn.setMinimumHeight(34)
            close_btn.clicked.connect(dialog.reject)
            layout.addWidget(close_btn)
    
            dialog.exec()

    def select_template_from_popup(self, template_name, dialog):
            index = self.template.findText(template_name)
            if index >= 0:
                self.template.setCurrentIndex(index)
            else:
                self.template.addItem(template_name)
                self.template.setCurrentText(template_name)
            dialog.accept()

    def delete_template_from_popup(self, template_name, dialog):
            if template_name in TEMPLATES:
                QMessageBox.information(
                    self,
                    "Template 삭제",
                    "기본 Template은 삭제할 수 없습니다."
                )
                return
    
            index = self.template.findText(template_name)
            if index < 0:
                return
    
            reply = QMessageBox.question(
                self,
                "Template 삭제",
                f"다음 Template을 삭제할까요?\n\n{template_name}",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
    
            if reply != QMessageBox.Yes:
                return
    
            was_current = (
                self.template.currentText().strip() == template_name
            )
    
            self.template.removeItem(index)
            self.save_template_list()
    
            if was_current:
                custom_index = self.template.findText("Custom")
                if custom_index >= 0:
                    self.template.setCurrentIndex(custom_index)
                elif self.template.count() > 0:
                    self.template.setCurrentIndex(0)
    
            self.update_dashboard()
            dialog.accept()
    
            QMessageBox.information(
                self,
                "Template 삭제",
                f"'{template_name}' Template이 삭제되었습니다."
            )

    def save_template_list(self):
            templates = [
                self.template.itemText(i)
                for i in range(self.template.count())
            ]
            template_file = os.path.join(BASE_DIR, "templates.json")
    
            try:
                with open(template_file, "w", encoding="utf-8") as f:
                    json.dump(templates, f, ensure_ascii=False, indent=4)
            except Exception as error:
                QMessageBox.warning(
                    self,
                    "Template Save Error",
                    f"Template 저장 중 오류가 발생했습니다.\n\n{type(error).__name__}: {error}"
                )

    def load_template_list(self):
            template_file = os.path.join(BASE_DIR, "templates.json")
            if not os.path.exists(template_file):
                return
    
            try:
                with open(template_file, "r", encoding="utf-8") as f:
                    templates = json.load(f)
    
                existing = {
                    self.template.itemText(i)
                    for i in range(self.template.count())
                }
    
                for template_name in templates:
                    if template_name not in existing:
                        self.template.addItem(template_name)
    
            except (json.JSONDecodeError, OSError) as error:
                print("[TEMPLATE LOAD ERROR]", repr(error))

    def load_template(self):
            template_name = self.template.currentText().strip()
            if not template_name or not hasattr(self, "purpose") or not hasattr(self, "expected"):
                return
    
            if template_name in TEMPLATES:
                data = TEMPLATES[template_name]
                self.purpose.setPlainText(data.get("purpose", ""))
                self.expected.setPlainText(data.get("expected", ""))

    def update_dashboard(self):
            saved_count = 0
            if os.path.exists(SAVE_DIR):
                saved_count = len([
                    f for f in os.listdir(SAVE_DIR)
                    if f.endswith(".json")
                ])
    
            domain=self.qa_domain.currentText(); short={"Automotive CANoe":"CANoe","Web / API QA":"Web/API","Mobile App QA":"Mobile","Embedded / Device QA":"Embedded","Desktop Software QA":"Desktop","General QA":"General","Custom":"Custom"}.get(domain,domain)
            mode=self.mode.currentText(); mode_short="Validation" if "Validation Analysis" in mode else "TC Generation" if "TC Generation" in mode else "TC Review"
            self.dashboard.setText(f"{short} | {mode_short} | {self.prompt_level.currentText()}")
            self.dashboard.setToolTip(f"Domain: {domain}\nMode: {mode}\nTemplate: {self.template.currentText()}\nSaved: {saved_count}")

    def show_attachment_preview(self, item):
            selected_name = item.text()
            for file_path in self.attachments:
                if os.path.basename(file_path) == selected_name:
                    if not os.path.exists(file_path):
                        QMessageBox.warning(self, "Image Error", "이미지 파일을 찾을 수 없습니다.")
                        return
                    self.open_image_file(file_path)
                    break

