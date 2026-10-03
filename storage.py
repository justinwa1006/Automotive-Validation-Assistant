from .core_runtime import *


class StorageMixin:
    def strip_existing_list_prefix(self, value):
            text = "" if value is None else str(value).strip()
            previous = None
            while text and text != previous:
                previous = text
                text = re.sub(r"^\s*(?:(?:step|precondition|expected(?: result)?)\s*)?(?:\d+(?:\.\d+)*(?:[.)]|(?=\s))|[-•▪◦])\s*", "", text, flags=re.IGNORECASE).strip()
            return text

    def list_to_cell_text(self, value, numbered=False):
            if isinstance(value, list):
                cleaned = [self.strip_existing_list_prefix(item) if numbered else str(item).strip() for item in value]
                cleaned = [item for item in cleaned if item]
                return "\n".join(f"{i}. {item}" for i,item in enumerate(cleaned,1)) if numbered else "\n".join(cleaned)
            return self.strip_existing_list_prefix(value) if numbered else ("" if value is None else str(value))

    def style_excel_sheet(self, ws):
            header_fill = PatternFill("solid", fgColor="1F4E78")
            header_font = Font(color="FFFFFF", bold=True)
            thin = Side(style="thin", color="BFBFBF")
            border = Border(left=thin, right=thin, top=thin, bottom=thin)
            for cell in ws[1]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                cell.border = border
            for row in ws.iter_rows(min_row=2):
                for cell in row:
                    cell.alignment = Alignment(vertical="top", wrap_text=True)
                    cell.border = border
            for column_cells in ws.columns:
                letter = column_cells[0].column_letter
                length = max((max((len(line) for line in str(c.value or "").split("\n")), default=0) for c in column_cells), default=0)
                ws.column_dimensions[letter].width = min(max(length + 2, 12), 50)
            ws.freeze_panes = "A2"
            if ws.max_row and ws.max_column:
                ws.auto_filter.ref = ws.dimensions

    def get_current_result_data(self):
            data = getattr(self, "current_ai_result_data", {})
            if data:
                return data
            raw = self.ai_result.toPlainText().strip()
            json_text = self.extract_json_from_text(raw) if raw else None
            if not json_text:
                return {}
            try:
                return json.loads(json_text)
            except json.JSONDecodeError:
                return {}

    def make_safe_filename(self, text, fallback="Validation_Result"):
            """Windows 파일명에 사용할 수 없는 문자를 제거한다."""
            invalid_chars = '<>:"/\\|?*'
    
            safe_name = str(text or "").strip()
    
            for char in invalid_chars:
                safe_name = safe_name.replace(char, "_")
    
            # 줄바꿈과 연속 공백 정리
            safe_name = " ".join(safe_name.split())
    
            # Windows에서 파일명 끝의 점과 공백은 사용할 수 없음
            safe_name = safe_name.rstrip(". ")
    
            # 파일명이 지나치게 길어지지 않게 제한
            safe_name = safe_name[:100]
    
            return safe_name or fallback

    def add_generation_review_sheets(self, workbook, generation_data):
            """TC Generation Excel에 Review Summary와 TC Auto Review 시트를 추가한다."""
            review_data = self.build_rule_based_tc_review(generation_data)
            summary = workbook.create_sheet("Review Summary")
            summary.append(["Item", "Value"])
            info = review_data["summary"]
            summary.append(["Total TC", info["total_count"]])
            summary.append(["PASS", info["pass_count"]])
            summary.append(["Needs Improvement", info["needs_improvement_count"]])
            summary.append(["Review Method", info["review_method"]])
            summary.append(["Note", "자동 리뷰는 구조 및 기본 품질 검사이며 최종 검토는 담당자가 수행합니다."])
            self.style_excel_sheet(summary)
    
            review = workbook.create_sheet("TC Auto Review")
            review.append([
                "TC ID", "Title", "Review Result", "Score", "Issues",
                "Recommendations", "Steps Count", "Expected Results Count", "Risk"
            ])
            for item in review_data["reviewed_test_cases"]:
                review.append([
                    item["tc_id"], item["title"], item["review_result"], item["score"],
                    self.list_to_cell_text(item["issues"]),
                    self.list_to_cell_text(item["recommendations"]),
                    item["steps_count"], item["expected_results_count"], item["risk"]
                ])
            self.style_excel_sheet(review)
    
            # 결과별 색상 강조
            pass_fill = PatternFill("solid", fgColor="C6EFCE")
            review_fill = PatternFill("solid", fgColor="FFF2CC")
            for row in range(2, review.max_row + 1):
                result = review.cell(row=row, column=3).value
                fill = pass_fill if result == "PASS" else review_fill
                for cell in review[row]:
                    cell.fill = fill

    def export_excel(self):
            data = self.get_current_result_data()
            if not data:
                QMessageBox.warning(self, "Export XLSX", "내보낼 구조화 JSON 결과가 없습니다.")
                return
    
            valid, errors, _warnings, data = self.validate_result_by_mode(data)
            if not valid:
                QMessageBox.warning(self, "Export XLSX", "\n".join(errors))
                return
    
            mode = self.mode.currentText()
            tc_title = self.tc.text().strip()
    
            safe_tc_title = self.make_safe_filename(tc_title, fallback="Untitled_TC")
    
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
            if "TC Generation" in mode:
                mode_suffix = "TC_Generation"
    
            elif "TC Review" in mode:
                mode_suffix = "TC_Review"
    
            else:
                mode_suffix = "Validation_Analysis"
    
            default_name = (f"{safe_tc_title}_{mode_suffix}_{timestamp}.xlsx")
    
            last_save_dir = self.settings.value("excel_save_directory", os.path.expanduser("~/Desktop"))
    
            suggested_path = os.path.join(last_save_dir,default_name)
    
            file_name, _ = QFileDialog.getSaveFileName(self, "Excel 저장", suggested_path, "Excel Workbook (*.xlsx)")
    
            if not file_name:
                return
    
            if not file_name.lower().endswith(".xlsx"):
                file_name += ".xlsx"
    
            selected_directory = os.path.dirname(file_name)
    
            self.settings.setValue("excel_save_directory", selected_directory)
    
            if not file_name:
                return
    
            if not file_name.lower().endswith(".xlsx"):
                file_name += ".xlsx"
    
            wb = openpyxl.Workbook()
            if "TC Generation" in mode:
                ws = wb.active
                ws.title = "Generated Test Cases"
                ws.append(["TC ID", "Category", "Title", "Preconditions", "Test Steps", "Expected Results", "Risk Level", "Risk Description", "Actual Result"])
                for item in data["test_cases"]:
                    ws.append([
                        item.get("tc_id", ""), item.get("category", ""), item.get("title", ""),
                        self.list_to_cell_text(item.get("preconditions", []), True),
                        self.list_to_cell_text(item.get("steps", []), True),
                        self.list_to_cell_text(item.get("expected_results", []), True),
                        item.get("risk", ""), item.get("risk_description", ""), item.get("Actual Result", "")
                    ])
                self.style_excel_sheet(ws)
                self.add_generation_review_sheets(wb, data)
                self.add_dbc_context_match_sheet(wb)
            elif "TC Review" in mode:
                summary = wb.active
                summary.title = "Review Summary"
                summary.append(["Item", "Value"])
                info = data.get("review_summary", {})
                for key, label in (("total_count", "Total Count"), ("pass_count", "Pass Count"),
                                   ("needs_improvement_count", "Needs Improvement Count"),
                                   ("overall_comment", "Overall Comment")):
                    summary.append([label, info.get(key, "")])
                review = wb.create_sheet("Reviewed Test Cases")
                review.append(["TC ID", "Original Title", "Review Result", "Score", "Requirement Coverage", "Clarity", "Testability", "Missing Conditions", "Issues", "Recommendations", "Revised Title", "Revised Precondition", "Revised Steps", "Revised Expected Result", "Risk"])
                for item in data["reviewed_test_cases"]:
                    review.append([
                        item.get("tc_id", ""), item.get("original_title", ""), item.get("review_result", ""), item.get("score", ""),
                        item.get("requirement_coverage", ""), item.get("clarity", ""), item.get("testability", ""),
                        self.list_to_cell_text(item.get("missing_conditions", [])), self.list_to_cell_text(item.get("issues", [])),
                        self.list_to_cell_text(item.get("recommendations", [])), item.get("revised_title", ""),
                        item.get("revised_precondition", ""), self.list_to_cell_text(item.get("revised_steps", []), True),
                        item.get("revised_expected_result", ""), item.get("risk", "")
                    ])
                self.style_excel_sheet(summary)
                self.style_excel_sheet(review)
            else:
                ws = wb.active
                ws.title = "Validation Analysis"
                ws.append(["TC Name", "Result", "Final Verdict", "Summary", "Confidence", "Risk", "Evidence Status", "Pass Factors", "Fail Factors", "Observations", "Gaps", "Recommended Verification"])
                ws.append([
                    self.tc.text().strip(), data.get("result", ""), data.get("final_verdict", ""), data.get("summary", ""),
                    data.get("confidence", ""), data.get("risk", ""), data.get("evidence_status", ""),
                    self.list_to_cell_text(data.get("pass_factors", [])), self.list_to_cell_text(data.get("fail_factors", [])),
                    self.list_to_cell_text(data.get("observations", [])), self.list_to_cell_text(data.get("gaps", [])),
                    self.list_to_cell_text(data.get("recommended_verification", []))
                ])
                self.style_excel_sheet(ws)
    
            try:
                wb.save(file_name)
            except Exception as error:
                QMessageBox.critical(self, "Export XLSX Error", f"Excel 저장에 실패했습니다.\n\n{type(error).__name__}: {error}")
                return
            QMessageBox.information(self, "Export Complete", f"{mode} 결과를 저장했습니다.\n\n{file_name}")

    def copy_attachments_for_tc(self, safe_tc_name):
            """TC와 함께 증적 파일을 상대 경로로 보관해 다른 PC에서도 불러올 수 있게 한다."""
            if not self.attachments:
                return []
    
            evidence_dir = os.path.join(SAVE_DIR, f"{safe_tc_name}_evidence")
            os.makedirs(evidence_dir, exist_ok=True)
    
            copied_paths = []
    
            for index, source_path in enumerate(self.attachments, start=1):
                if not os.path.isfile(source_path):
                    # 이미 BASE_DIR 기준 상대 경로로 존재하는지 확인
                    if os.path.isfile(os.path.join(BASE_DIR, source_path)):
                        source_path = os.path.join(BASE_DIR, source_path)
                    else:
                        continue
    
                file_name = os.path.basename(source_path)
                destination_path = os.path.join(
                    evidence_dir,
                    f"{index:02d}_{file_name}"
                )
    
                if os.path.abspath(source_path) != os.path.abspath(destination_path):
                    shutil.copy2(source_path, destination_path)
    
                rel_path = os.path.relpath(destination_path, BASE_DIR)
                copied_paths.append(rel_path)
    
            return copied_paths

    def restore_full_project_state(self, data):
            """저장 파일의 TC 본문, DBC/BLF, 시간, Signal, 결과와 보안 모드를 모두 복원한다."""
            if hasattr(self,"validation_preconditions"):
                self.validation_preconditions.setPlainText(data.get("validation_preconditions", ""))
                self.validation_steps.setPlainText(data.get("validation_steps", ""))
                self.validation_expected_results.setPlainText(data.get("validation_expected_results", ""))
                self.validation_actual_results.setPlainText(data.get("validation_actual_results", ""))
            # 구버전 저장 파일은 purpose/expected 블록에서 복구한다.
            if hasattr(self,"validation_preconditions") and not any((self.validation_preconditions.toPlainText(),self.validation_steps.toPlainText(),self.validation_expected_results.toPlainText())):
                purpose=str(data.get("purpose", "")); actual=str(data.get("expected", ""))
                patterns=[("validation_preconditions",r"\[Preconditions\]\s*(.*?)(?=\n\s*\[|\Z)"),("validation_steps",r"\[Test Steps\]\s*(.*?)(?=\n\s*\[|\Z)"),("validation_expected_results",r"\[Expected Results\]\s*(.*?)(?=\n\s*\[|\Z)")]
                for name,pattern in patterns:
                    match=re.search(pattern,purpose,re.S|re.I)
                    if match: getattr(self,name).setPlainText(match.group(1).strip())
                self.validation_actual_results.setPlainText(actual)
            blf_path=str(data.get("blf_file_path", ""))
            if blf_path and os.path.isfile(blf_path): self.blf_file_path=blf_path
            dbc_paths=[path for path in data.get("dbc_file_paths", []) if os.path.isfile(path)]
            if dbc_paths:
                self.dbc_file_paths=dbc_paths; self._dbc_cache_key=None; self._dbc_database_cache=None; self._dbc_catalog_cache=[]
            self.tc_related_parse_signals=list(data.get("tc_related_parse_signals", []))
            if hasattr(self,"blf_start_time"): self.blf_start_time.setText(str(data.get("blf_start_time", "")))
            if hasattr(self,"blf_end_time"): self.blf_end_time.setText(str(data.get("blf_end_time", "")))
            if hasattr(self,"signal_filter"): self.signal_filter.setText(str(data.get("signal_filter", "")))
            self.tc_blf_validation_data=data.get("tc_blf_validation_data", {})
            self.current_ai_result_data=data.get("current_ai_result_data", getattr(self,"current_ai_result_data",{}))
            if hasattr(self,"ai_transmission_mode"):
                index=max(0,min(2,int(data.get("ai_transmission_mode_index",1))))
                self.ai_transmission_mode.setCurrentIndex(index); self.update_ai_transmission_mode_notice()
            if hasattr(self,"u_security_mode"):
                self.u_security_mode.blockSignals(True); self.u_security_mode.setCurrentIndex(self.ai_transmission_mode.currentIndex()); self.u_security_mode.blockSignals(False)
            if hasattr(self,"u_start"): self.u_start.setText(self.blf_start_time.text())
            if hasattr(self,"u_end"): self.u_end.setText(self.blf_end_time.text())
            if hasattr(self,"u_filter"): self.u_filter.setText(self.signal_filter.text())
            if hasattr(self,"u_tc_signal_status"): self.u_tc_signal_status.setText(f"분석 Signal {len(self.tc_related_parse_signals)}개 확정")
            if hasattr(self,"u_tabs"):
                mode_text=self.mode.currentText(); index=1 if "TC Generation" in mode_text else 2 if "TC Review" in mode_text else 0
                self.u_tabs.setCurrentIndex(index); self._u_tab_changed(index)
            self.update_blf_status()
            if hasattr(self,"_u_update_blf_status"): self._u_update_blf_status()
            if hasattr(self,"_u_display_current_structured_result"): self._u_display_current_structured_result()
            self.update_validation_pair_status()

    def save_tc(self):
            tc_name = self.tc.text().strip()
    
            if not tc_name:
                QMessageBox.warning(self, "Warning", "TC Name을 입력하세요.")
                return
    
            if (
                "Validation Analysis" in self.mode.currentText()
                and not self.ai_result.toPlainText().strip()
            ):
                reply = QMessageBox.question(
                    self,
                    "Analysis Result 확인",
                    "AI Analysis Result가 비어 있습니다.\n\n분석 결과 없이 저장할까요?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
    
                if reply != QMessageBox.Yes:
                    return
    
            try:
                os.makedirs(SAVE_DIR, exist_ok=True)
    
                invalid_chars = '<>:"/\\|?*'
                safe_file_name = "".join(
                    "_" if character in invalid_chars else character
                    for character in tc_name
                ).strip().rstrip(". ")
    
                if not safe_file_name:
                    safe_file_name = "Validation_TC"
    
                saved_attachments = self.copy_attachments_for_tc(safe_file_name)
    
                data = {
                    "qa_domain": self.qa_domain.currentText() if hasattr(self,"qa_domain") else "Automotive CANoe",
                    "domain_evidence_files": list(getattr(self,"domain_evidence_files",[])),
                    "tc": self.tc.text().strip(),
                    "purpose": self.purpose.toPlainText().strip(),
                    "expected": self.expected.toPlainText().strip(),
                    "validation_preconditions": self.validation_preconditions.toPlainText().strip() if hasattr(self,"validation_preconditions") else "",
                    "validation_steps": self.validation_steps.toPlainText().strip() if hasattr(self,"validation_steps") else "",
                    "validation_expected_results": self.validation_expected_results.toPlainText().strip() if hasattr(self,"validation_expected_results") else "",
                    "validation_actual_results": self.validation_actual_results.toPlainText().strip() if hasattr(self,"validation_actual_results") else "",
                    "blf_file_path": self.blf_file_path,
                    "dbc_file_paths": list(self.dbc_file_paths),
                    "blf_start_time": self.blf_start_time.text() if hasattr(self,"blf_start_time") else "",
                    "blf_end_time": self.blf_end_time.text() if hasattr(self,"blf_end_time") else "",
                    "tc_related_parse_signals": list(getattr(self,"tc_related_parse_signals",[])),
                    "tc_blf_validation_data": getattr(self,"tc_blf_validation_data",{}),
                    "current_ai_result_data": getattr(self,"current_ai_result_data",{}),
                    "tc_generation_page": self.tc_generation_page,
                    "tc_generation_requirement": self.tc_generation_requirement,
                    "tc_generation_acceptance": self.tc_generation_acceptance,
                    "tc_generation_preconditions": self.tc_generation_preconditions,
                    "tc_generation_observations": self.tc_generation_observations,
                    "tc_generation_sequence": self.tc_generation_sequence,
                    "tc_generation_checkpoints": self.tc_generation_checkpoints,
                    "tc_generation_sequence_mode": self.tc_generation_sequence_mode,
                    "analysis_question": (
                        self.analysis_question.toPlainText().strip()
                        if hasattr(self, "analysis_question")
                        else ""
                    ),
                    "analysis_purpose": (
                        self.analysis_purpose.currentText()
                        if hasattr(self, "analysis_purpose")
                        else "전체 분석"
                    ),
                    "blf_summary": self.blf_summary_data,
                    "blf_file_name": os.path.basename(self.blf_file_path) if self.blf_file_path else "",
                    "dbc_file_names": [
                        os.path.basename(path) for path in self.dbc_file_paths
                    ],
                    "signal_filter": self.signal_filter.text() if hasattr(self, "signal_filter") else "",
                    "ai_event_limit": self.ai_event_limit.value() if hasattr(self, "ai_event_limit") else 40,
                    "tp_mode": self.tp_mode.currentText() if hasattr(self, "tp_mode") else "Off",
                    "tp_can_ids": self.tp_can_ids.text() if hasattr(self, "tp_can_ids") else "",
                    "mode": self.mode.currentText(),
                    "prompt_level": self.prompt_level.currentText(),
                    "template": self.template.currentText(),
                    "attachments": saved_attachments,
                    "generated_prompt": self.generated_prompt,
                    "ai_analysis_result": self.ai_result.toPlainText().strip(),
                    "structured_ai_result": getattr(
                        self,
                        "current_ai_result_data",
                        {}
                    ),
                    "dbc_context_match_report": self.dbc_context_match_report,
                    "preferred_dbc_signals": self.preferred_dbc_signals,
                    "signal_function_mapping": self.signal_function_mapping,
                    "auto_mapping_report": self.auto_mapping_report,
                    "anonymize_signals_for_ai": self.anonymize_signals_for_ai.isChecked() if hasattr(self,"anonymize_signals_for_ai") else True,
                    "ai_transmission_mode_index": self.ai_transmission_mode.currentIndex() if hasattr(self, "ai_transmission_mode") else 0,
                    "saved_date": datetime.now().strftime("%Y-%m-%d %H:%M")
                }
    
                file_path = os.path.join(SAVE_DIR, safe_file_name + ".json")
    
                with open(file_path, "w", encoding="utf-8") as file:
                    json.dump(data, file, ensure_ascii=False, indent=4)
    
                QMessageBox.information(
                    self,
                    "Saved",
                    f"저장 완료\n\n{file_path}"
                )
    
                self.refresh_saved_tc_list()
                self.update_dashboard()
    
            except Exception as error:
                QMessageBox.critical(
                    self,
                    "Save Error",
                    f"JSON 저장 중 오류가 발생했습니다.\n\n{type(error).__name__}: {error}"
                )

    def load_tc(self):
            os.makedirs(SAVE_DIR, exist_ok=True)
    
            file_name, _ = QFileDialog.getOpenFileName(
                self,
                "Load TC",
                SAVE_DIR,
                "JSON Files (*.json);;All Files (*.*)"
            )
    
            if not file_name:
                return
    
            try:
                with open(file_name, "r", encoding="utf-8-sig") as file:
                    data = json.load(file)
    
                saved_domain=data.get("qa_domain","Automotive CANoe")
                if hasattr(self,"qa_domain") and self.qa_domain.findText(saved_domain)>=0:
                    self.qa_domain.setCurrentText(saved_domain)
                self.domain_evidence_files=data.get("domain_evidence_files",[])
                if hasattr(self,"domain_evidence_list"):
                    self.domain_evidence_list.clear()
                    self.domain_evidence_list.addItems([os.path.basename(x) for x in self.domain_evidence_files])
                saved_mode = data.get("mode", "🔍 Validation Analysis")
                mode_index = self.mode.findText(saved_mode)
                if mode_index >= 0:
                    self.mode.setCurrentIndex(mode_index)
    
                saved_level = data.get("prompt_level", "Basic")
                level_index = self.prompt_level.findText(saved_level)
                if level_index >= 0:
                    self.prompt_level.setCurrentIndex(level_index)
    
                saved_template = data.get("template", "Custom")
                template_index = self.template.findText(saved_template)
                if template_index >= 0:
                    self.template.setCurrentIndex(template_index)
                else:
                    self.template.addItem(saved_template)
                    self.template.setCurrentText(saved_template)
    
                self.tc.setText(data.get("tc", ""))
                self.purpose.setPlainText(data.get("purpose", ""))
                self.expected.setPlainText(data.get("expected", ""))
                if hasattr(self, "analysis_purpose"):
                    saved_analysis_purpose = data.get("analysis_purpose", "전체 분석")
                    purpose_index = self.analysis_purpose.findText(saved_analysis_purpose)
                    if purpose_index >= 0:
                        self.analysis_purpose.setCurrentIndex(purpose_index)
                if hasattr(self, "analysis_question"):
                    self.analysis_question.setPlainText(
                        data.get("analysis_question", "")
                    )
                self.tc_generation_page = data.get("tc_generation_page", "basic")
                self.tc_generation_requirement = data.get("tc_generation_requirement", data.get("purpose", ""))
                self.tc_generation_acceptance = data.get("tc_generation_acceptance", data.get("expected", ""))
                self.tc_generation_preconditions = data.get("tc_generation_preconditions", "")
                self.tc_generation_observations = data.get("tc_generation_observations", "")
                self.tc_generation_sequence = data.get("tc_generation_sequence", "")
                self.tc_generation_checkpoints = data.get("tc_generation_checkpoints", "")
                self.tc_generation_sequence_mode = data.get("tc_generation_sequence_mode", "사용자 흐름 우선")
                self.blf_summary_data = data.get("blf_summary", {})
                self.preferred_dbc_signals = data.get("preferred_dbc_signals", [])
                self.signal_function_mapping = data.get("signal_function_mapping", {})
                self.auto_mapping_report = data.get("auto_mapping_report", [])
                self.rebuild_signal_aliases()
                if hasattr(self,"anonymize_signals_for_ai"):
                    self.anonymize_signals_for_ai.setChecked(data.get("anonymize_signals_for_ai", True))
                if hasattr(self, "ai_transmission_mode"):
                    self.ai_transmission_mode.setCurrentIndex(int(data.get("ai_transmission_mode_index", 0)))
                    self.update_ai_transmission_mode_notice()
                self.refresh_signal_tools_status()
                if hasattr(self, "blf_summary_preview"):
                    self.blf_summary_preview.setPlainText(
                        json.dumps(self.blf_summary_data, ensure_ascii=False, indent=2)
                        if self.blf_summary_data else ""
                    )
                self.generated_prompt = data.get("generated_prompt", "")
                self.restore_full_project_state(data)
                self.restore_ai_result_from_saved_data(data)
    
                # 첨부 이미지 상대 경로 및 절대 경로 자동 복원
                raw_attachments = data.get("attachments", [])
                resolved_attachments = []
    
                for path in raw_attachments:
                    if os.path.isabs(path) and os.path.exists(path):
                        resolved_attachments.append(path)
                    else:
                        abs_path = os.path.join(BASE_DIR, path)
                        if os.path.exists(abs_path):
                            resolved_attachments.append(abs_path)
                        else:
                            base_file_name = os.path.basename(path)
                            found = False
                            for root, _, files in os.walk(SAVE_DIR):
                                if base_file_name in files:
                                    resolved_attachments.append(
                                        os.path.join(root, base_file_name)
                                    )
                                    found = True
                                    break
                            if not found:
                                resolved_attachments.append(path)
    
                self.attachments = resolved_attachments
    
                self.refresh_attachment_list()
                self.refresh_image_gallery()
                self.update_mode_ui()
                self.update_prompt_preview()
                self.update_dashboard()
    
                QMessageBox.information(
                    self,
                    "Loaded",
                    f"불러오기 완료\n\n{os.path.basename(file_name)}"
                )
    
            except json.JSONDecodeError as error:
                QMessageBox.critical(
                    self,
                    "JSON 오류",
                    f"JSON 파일 형식이 올바르지 않습니다.\n\n{error}"
                )
            except Exception as error:
                QMessageBox.critical(
                    self,
                    "Load Error",
                    f"파일을 불러오는 중 오류가 발생했습니다.\n\n{type(error).__name__}: {error}"
                )

    def save_history(self):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except (OSError, json.JSONDecodeError):
                history = []
    
            tc_name = self.tc.text().strip()
            if tc_name:
                if tc_name in history:
                    history.remove(tc_name)
                history.insert(0, tc_name)
    
            history = history[:10]
    
            try:
                with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                    json.dump(history, f, ensure_ascii=False, indent=4)
            except OSError as error:
                print("[HISTORY SAVE ERROR]", error)

    def refresh_saved_tc_list(self):
            self.saved_tc_list.clear()
            os.makedirs(SAVE_DIR, exist_ok=True)
    
            for file_name in sorted(os.listdir(SAVE_DIR)):
                if not file_name.lower().endswith(".json"):
                    continue
    
                file_path = os.path.join(SAVE_DIR, file_name)
    
                try:
                    with open(file_path, "r", encoding="utf-8-sig") as f:
                        data = json.load(f)
    
                    tc_name = data.get("tc", os.path.splitext(file_name)[0])
                    saved_date = data.get("saved_date", "")
    
                    item = QListWidgetItem(f"{tc_name} ({saved_date})")
                    item.setData(Qt.UserRole, file_name)
                    self.saved_tc_list.addItem(item)
    
                except (json.JSONDecodeError, OSError) as error:
                    print("[LIST ERROR]", file_path, repr(error))

    def filter_saved_tc(self):
            keyword = self.tc_search.text().lower()
            for i in range(self.saved_tc_list.count()):
                item = self.saved_tc_list.item(i)
                item.setHidden(keyword not in item.text().lower())

    def restore_ai_result_from_saved_data(self, data):
            saved_ai_result_text = str(data.get("ai_analysis_result", "")).strip()
            saved_structured_result = data.get("structured_ai_result", {})
    
            self.current_ai_result_data = {}
            self.clear_structured_ai_result()
    
            if isinstance(saved_structured_result, dict) and saved_structured_result:
                if self.apply_ai_result_data(saved_structured_result, show_warning=False):
                    return
    
            if saved_ai_result_text:
                json_text = self.extract_json_from_text(saved_ai_result_text)
                if json_text:
                    try:
                        parsed_result = json.loads(json_text)
                        if self.apply_ai_result_data(parsed_result, show_warning=False):
                            return
                    except json.JSONDecodeError:
                        pass
    
            self.ai_result.setPlainText(saved_ai_result_text)
            self.current_ai_result_data = {}
            self.clear_structured_ai_result()

    def load_saved_tc(self, item):
            file_name = item.data(Qt.UserRole)
            file_path = os.path.join(SAVE_DIR, file_name)
    
            try:
                with open(file_path, "r", encoding="utf-8-sig") as file:
                    content = file.read().strip()
    
                if not content:
                    return
    
                data = json.loads(content)
    
                saved_domain=data.get("qa_domain","Automotive CANoe")
                if hasattr(self,"qa_domain") and self.qa_domain.findText(saved_domain)>=0:
                    self.qa_domain.setCurrentText(saved_domain)
                self.domain_evidence_files=data.get("domain_evidence_files",[])
                if hasattr(self,"domain_evidence_list"):
                    self.domain_evidence_list.clear()
                    self.domain_evidence_list.addItems([os.path.basename(x) for x in self.domain_evidence_files])
                saved_mode = data.get("mode", "🔍 Validation Analysis")
                mode_index = self.mode.findText(saved_mode)
                if mode_index >= 0:
                    self.mode.setCurrentIndex(mode_index)
    
                saved_level = data.get("prompt_level", "Basic")
                level_index = self.prompt_level.findText(saved_level)
                if level_index >= 0:
                    self.prompt_level.setCurrentIndex(level_index)
    
                saved_template = data.get("template", "Custom")
                template_index = self.template.findText(saved_template)
                if template_index >= 0:
                    self.template.setCurrentIndex(template_index)
                else:
                    self.template.addItem(saved_template)
                    self.template.setCurrentText(saved_template)
    
                self.tc.setText(data.get("tc", ""))
                self.purpose.setPlainText(data.get("purpose", ""))
                self.expected.setPlainText(data.get("expected", ""))
                if hasattr(self, "analysis_purpose"):
                    saved_analysis_purpose = data.get("analysis_purpose", "전체 분석")
                    purpose_index = self.analysis_purpose.findText(saved_analysis_purpose)
                    if purpose_index >= 0:
                        self.analysis_purpose.setCurrentIndex(purpose_index)
                if hasattr(self, "analysis_question"):
                    self.analysis_question.setPlainText(
                        data.get("analysis_question", "")
                    )
                self.tc_generation_page = data.get("tc_generation_page", "basic")
                self.tc_generation_requirement = data.get("tc_generation_requirement", data.get("purpose", ""))
                self.tc_generation_acceptance = data.get("tc_generation_acceptance", data.get("expected", ""))
                self.tc_generation_preconditions = data.get("tc_generation_preconditions", "")
                self.tc_generation_observations = data.get("tc_generation_observations", "")
                self.tc_generation_sequence = data.get("tc_generation_sequence", "")
                self.tc_generation_checkpoints = data.get("tc_generation_checkpoints", "")
                self.tc_generation_sequence_mode = data.get("tc_generation_sequence_mode", "사용자 흐름 우선")
                self.blf_summary_data = data.get("blf_summary", {})
                self.preferred_dbc_signals = data.get("preferred_dbc_signals", [])
                self.signal_function_mapping = data.get("signal_function_mapping", {})
                self.auto_mapping_report = data.get("auto_mapping_report", [])
                self.rebuild_signal_aliases()
                if hasattr(self,"anonymize_signals_for_ai"):
                    self.anonymize_signals_for_ai.setChecked(data.get("anonymize_signals_for_ai", True))
                if hasattr(self, "ai_transmission_mode"):
                    self.ai_transmission_mode.setCurrentIndex(int(data.get("ai_transmission_mode_index", 0)))
                    self.update_ai_transmission_mode_notice()
                self.refresh_signal_tools_status()
                if hasattr(self, "blf_summary_preview"):
                    self.blf_summary_preview.setPlainText(
                        json.dumps(self.blf_summary_data, ensure_ascii=False, indent=2)
                        if self.blf_summary_data else ""
                    )
                self.generated_prompt = data.get("generated_prompt", "")
                self.restore_full_project_state(data)
    
                self.restore_ai_result_from_saved_data(data)
    
                raw_attachments = data.get("attachments", [])
                resolved_attachments = []
    
                for path in raw_attachments:
                    if os.path.isabs(path) and os.path.exists(path):
                        resolved_attachments.append(path)
                    else:
                        abs_path = os.path.join(BASE_DIR, path)
                        if os.path.exists(abs_path):
                            resolved_attachments.append(abs_path)
                        else:
                            base_file_name = os.path.basename(path)
                            found = False
                            for root, _, files in os.walk(SAVE_DIR):
                                if base_file_name in files:
                                    resolved_attachments.append(
                                        os.path.join(root, base_file_name)
                                    )
                                    found = True
                                    break
                            if not found:
                                resolved_attachments.append(path)
    
                self.attachments = resolved_attachments
    
                self.refresh_attachment_list()
                self.refresh_image_gallery()
                self.update_prompt_preview()
                self.update_mode_ui()
                self.update_dashboard()
    
            except Exception as error:
                QMessageBox.warning(self, "Load Error", str(error))

    def delete_tc(self):
            item = self.saved_tc_list.currentItem()
            if not item:
                return
    
            reply = QMessageBox.question(
                self,
                "Delete TC",
                f"{item.text()} 를 삭제할까요?"
            )
    
            if reply != QMessageBox.Yes:
                return
    
            file_name = item.data(Qt.UserRole)
            file_path = os.path.join(SAVE_DIR, file_name)
    
            if os.path.exists(file_path):
                os.remove(file_path)
    
            self.update_mode_ui()
            self.update_dashboard()
            self.refresh_saved_tc_list()

    def refresh_attachment_list(self):
            self.attachment_list.clear()
            for file_path in self.attachments:
                self.attachment_list.addItem(os.path.basename(file_path))

    def remove_attachment(self, file_path):
            if file_path not in self.attachments:
                return
    
            file_name = os.path.basename(file_path)
    
            reply = QMessageBox.question(
                self,
                "Remove Evidence",
                f"{file_name}\n\n이 이미지를 첨부 목록에서 제거할까요?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
    
            if reply != QMessageBox.Yes:
                return
    
            self.attachments = [
                attachment_path
                for attachment_path in self.attachments
                if attachment_path != file_path
            ]
    
            self.refresh_attachment_list()
            self.refresh_image_gallery()
    
            if self.generated_prompt:
                self.update_prompt_preview()
    
            self.update_dashboard()

    def refresh_image_gallery(self):
            while self.image_layout.count():
                item = self.image_layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
    
            if not self.attachments:
                empty_label = QLabel(
                    "첨부된 이미지가 없습니다.\n"
                    "Attach Screenshot 버튼으로 이미지를 추가하세요."
                )
                empty_label.setObjectName("emptyImageLabel")
                empty_label.setAlignment(Qt.AlignCenter)
                self.image_layout.addWidget(empty_label, 0, 0, 1, 2)
                return
    
            visible_index = 0
    
            for file_path in self.attachments:
                card = QWidget()
                card.setObjectName("imageCard")
    
                card_layout = QVBoxLayout(card)
                card_layout.setContentsMargins(6, 6, 6, 6)
                card_layout.setSpacing(5)
    
                card_header = QHBoxLayout()
                card_header.setContentsMargins(0, 0, 0, 0)
                card_header.setSpacing(4)
    
                file_name = os.path.basename(file_path)
                file_name_label = QLabel(file_name)
                file_name_label.setObjectName("imageFileName")
                file_name_label.setToolTip(file_path)
    
                if len(file_name) > 18:
                    file_name_label.setText(file_name[:15] + "...")
    
                delete_image_btn = QPushButton("✕")
                delete_image_btn.setObjectName("imageDeleteButton")
                delete_image_btn.setToolTip("이 Evidence 제거")
                delete_image_btn.setFixedSize(24, 24)
                delete_image_btn.clicked.connect(
                    lambda checked=False, path=file_path:
                    self.remove_attachment(path)
                )
    
                card_header.addWidget(file_name_label, 1)
                card_header.addWidget(delete_image_btn)
                card_layout.addLayout(card_header)
    
                thumbnail = QLabel()
                thumbnail.setObjectName("imageThumbnail")
                thumbnail.setAlignment(Qt.AlignCenter)
                thumbnail.setMinimumSize(120, 95)
                thumbnail.setMaximumHeight(105)
    
                if os.path.exists(file_path):
                    pixmap = QPixmap(file_path)
                    if not pixmap.isNull():
                        thumbnail.setPixmap(
                            pixmap.scaled(
                                135,
                                95,
                                Qt.KeepAspectRatio,
                                Qt.SmoothTransformation
                            )
                        )
                    else:
                        thumbnail.setText("이미지 로드 실패")
                else:
                    thumbnail.setText("파일을 찾을 수 없음")
    
                thumbnail.mousePressEvent = (
                    lambda event, path=file_path:
                    self.open_image_file(path)
                )
    
                card_layout.addWidget(thumbnail)
    
                row = visible_index // 2
                column = visible_index % 2
    
                self.image_layout.addWidget(card, row, column)
                self.image_layout.setColumnStretch(column, 1)
                visible_index += 1

    def attach_file(self):
            files, _ = QFileDialog.getOpenFileNames(
                self,
                "Select Screenshots",
                "",
                "Image Files (*.png *.jpg *.jpeg *.bmp *.webp)"
            )
    
            if not files:
                return
    
            for file_path in files:
                if file_path not in self.attachments:
                    self.attachments.append(file_path)
    
            self.refresh_attachment_list()
            self.refresh_image_gallery()
            self.update_dashboard()
    
            if self.generated_prompt:
                self.update_prompt_preview()

    def open_image_file(self, image_path):
            try:
                if sys.platform.startswith("win"):
                    os.startfile(image_path)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", image_path])
                else:
                    subprocess.Popen(["xdg-open", image_path])
            except Exception as error:
                print("[IMAGE OPEN ERROR]", error)

    def copy_evidence_files_only(self):
            valid_files = [
                os.path.abspath(path) for path in self.attachments
                if os.path.isfile(os.path.abspath(path))
            ]
    
            if not valid_files:
                QMessageBox.warning(self, "Copy Evidence", "복사할 Evidence 이미지가 없습니다.")
                return False
    
            try:
                from PySide6.QtGui import QImage, QPainter, QColor, QFont
    
                images = []
                for path in valid_files:
                    img = QImage(path)
                    if not img.isNull():
                        images.append((os.path.basename(path), img))
    
                if not images:
                    QMessageBox.warning(self, "Copy Evidence Error", "유효한 이미지를 로드할 수 없습니다.")
                    return False
    
                padding = 20
                header_height = 30
                max_limit_width = 1200
    
                processed_items = []
                max_actual_width = 0
                total_height = padding
    
                for name, img in images:
                    target_w = min(img.width(), max_limit_width - (padding * 2))
                    target_h = int(img.height() * (target_w / img.width()))
    
                    scaled_img = img.scaled(
                        target_w, target_h,
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation
                    )
    
                    card_h = header_height + scaled_img.height() + padding
                    processed_items.append((name, scaled_img, target_w, card_h))
    
                    if target_w > max_actual_width:
                        max_actual_width = target_w
    
                    total_height += card_h
    
                canvas_width = max_actual_width + (padding * 2)
    
                merged_image = QImage(
                    canvas_width,
                    total_height,
                    QImage.Format_ARGB32
                )
                merged_image.fill(QColor("#0d1117"))
    
                painter = QPainter(merged_image)
                painter.setRenderHint(QPainter.Antialiasing)
    
                font = QFont("Segoe UI", 11, QFont.Bold)
                painter.setFont(font)
    
                current_y = padding
    
                for idx, (name, scaled_img, img_w, card_h) in enumerate(processed_items, 1):
                    painter.setPen(QColor("#38bdf8"))
                    label_text = f"Evidence {idx}: {name}"
                    painter.drawText(padding, current_y + 20, label_text)
    
                    img_x = padding
                    img_y = current_y + header_height
                    painter.drawImage(img_x, img_y, scaled_img)
    
                    painter.setPen(QColor("#334155"))
                    painter.drawRect(
                        img_x - 1,
                        img_y - 1,
                        scaled_img.width() + 1,
                        scaled_img.height() + 1
                    )
    
                    current_y += card_h
    
                painter.end()
    
                QApplication.clipboard().setImage(merged_image)
    
                QMessageBox.information(
                    self,
                    "Copy Evidence",
                    f"Evidence 이미지 {len(images)}개가\n"
                    "하나의 통합 이미지로 클립보드에 복사되었습니다.\n\n"
                    "원하는 AI에 접속하여 Ctrl+V를 눌러 붙여넣으세요."
                )
    
                return True
    
            except Exception as error:
                QMessageBox.critical(
                    self,
                    "Copy Evidence Error",
                    f"이미지 병합 및 복사 중 오류가 발생했습니다.\n\n{type(error).__name__}: {error}"
                )
                return False

    def attach_domain_evidence(self):
            files,_=QFileDialog.getOpenFileNames(self,"Attach QA Evidence","","Evidence (*.txt *.log *.json *.csv *.har *.xml *.yaml *.yml);;All Files (*.*)")
            for path in files:
                if path not in self.domain_evidence_files: self.domain_evidence_files.append(path)
            self.domain_evidence_list.clear()
            self.domain_evidence_list.addItems([os.path.basename(p) for p in self.domain_evidence_files])

    def get_domain_evidence_summary(self):
            if not getattr(self,"domain_evidence_files",[]): return "추가 Evidence 파일 없음"
            result=[]; budget=12000
            for path in self.domain_evidence_files:
                if budget<=0: break
                try:
                    with open(path,"r",encoding="utf-8-sig",errors="replace") as f: text=f.read(min(budget,4000))
                    result.append(f"[File: {os.path.basename(path)}]\n{text}")
                    budget-=len(text)
                except Exception as e:
                    result.append(f"[File: {os.path.basename(path)} / 읽기 실패: {e}]")
            return "\n\n".join(result)

