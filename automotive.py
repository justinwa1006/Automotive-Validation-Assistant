from .core_runtime import *


class AutomotiveMixin:
    def load_signal_sets(self):
            self.signal_sets = {}
            if os.path.isfile(SIGNAL_SET_PATH):
                try:
                    with open(SIGNAL_SET_PATH, "r", encoding="utf-8-sig") as f: data=json.load(f)
                    self.signal_sets=data.get("signal_sets",data) if isinstance(data,dict) else {}
                except Exception as error: print("[SIGNAL SET LOAD ERROR]",repr(error))

    def save_signal_sets(self):
            temp=SIGNAL_SET_PATH+".tmp"
            with open(temp,"w",encoding="utf-8") as f:
                json.dump({"schema_version":2,"signal_sets":self.signal_sets},f,ensure_ascii=False,indent=2); f.flush(); os.fsync(f.fileno())
            os.replace(temp,SIGNAL_SET_PATH)

    def apply_signal_set(self,name,show_message=True):
            item=self.signal_sets.get(name,{})
            mappings=dict(item.get("mappings",{})); missing=[]
            if self.dbc_file_paths and cantools is not None:
                catalog,_=self.build_dbc_context_catalog(); names={x.get("signal","") for x in catalog}
                missing=[(k,v) for k,v in mappings.items() if v not in names]; mappings={k:v for k,v in mappings.items() if v in names}
            self.signal_function_mapping=mappings; self.preferred_dbc_signals=list(item.get("preferred_signals",[])); self.active_signal_set=name
            self.rebuild_signal_aliases(); self.refresh_signal_tools_status()
            if show_message:
                QMessageBox.information(self,"신호 세트",f"'{name}' 적용: {len(mappings)}개 / 누락: {len(missing)}개")
            return True

    def open_signal_set_manager(self):
            d=QDialog(self); d.setWindowTitle("로컬 신호 세트 관리"); d.resize(650,460); l=QVBoxLayout(d)
            g=QLabel("직접 확인한 기능-신호 매핑을 이 PC에 저장하고 재사용합니다."); g.setWordWrap(True); l.addWidget(g)
            name=QLineEdit(); name.setPlaceholderText("신호 세트 이름"); l.addWidget(name)
            items=QListWidget(); l.addWidget(items,1)
            def refresh():
                items.clear()
                for key in sorted(self.signal_sets):
                    row=QListWidgetItem(key); row.setData(Qt.UserRole,key); items.addItem(row)
            def save():
                key=name.text().strip()
                if not key or not self.signal_function_mapping: QMessageBox.warning(d,"신호 세트","이름 입력 후 신호를 먼저 지정하세요."); return
                self.signal_sets[key]={"mappings":dict(self.signal_function_mapping),"preferred_signals":list(self.preferred_dbc_signals),"local_only":True}; self.save_signal_sets(); self.active_signal_set=key; self.refresh_signal_tools_status(); refresh()
            def load():
                row=items.currentItem()
                if row: self.apply_signal_set(row.data(Qt.UserRole)); d.accept()
            def delete():
                row=items.currentItem()
                if row: self.signal_sets.pop(row.data(Qt.UserRole),None); self.save_signal_sets(); refresh()
            row=QHBoxLayout(); a=QPushButton("현재 매핑 저장"); b=QPushButton("선택 세트 적용"); c=QPushButton("삭제"); x=QPushButton("닫기")
            for w in (a,b,c): row.addWidget(w)
            row.addStretch(); row.addWidget(x); l.addLayout(row)
            a.clicked.connect(save); b.clicked.connect(load); c.clicked.connect(delete); x.clicked.connect(d.accept); refresh(); d.exec()

    def auto_fill_blf_time_and_signal_filter(self, show_message=False):
            """BLF 전체 기록 시간을 Start/End에 넣고 확정 Signal을 Filter에 동기화한다."""
            if not self.blf_file_path or not os.path.isfile(self.blf_file_path):
                if show_message: QMessageBox.warning(self,"BLF 자동 입력","먼저 BLF 파일을 선택하세요.")
                return False
            if can is None:
                if show_message: QMessageBox.warning(self,"BLF 자동 입력","python-can이 필요합니다.")
                return False
            first_timestamp=None; last_timestamp=None; message_count=0
            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                reader=can.BLFReader(self.blf_file_path)
                try:
                    for message in reader:
                        timestamp=float(message.timestamp); message_count+=1
                        if first_timestamp is None: first_timestamp=timestamp
                        last_timestamp=timestamp
                finally:
                    if hasattr(reader,"stop"): reader.stop()
            except Exception as error:
                if show_message: QMessageBox.critical(self,"BLF 자동 입력 오류",f"BLF 기록 시간을 읽지 못했습니다.\n\n{error}")
                return False
            finally:
                QApplication.restoreOverrideCursor()
            if first_timestamp is None or last_timestamp is None:
                if show_message: QMessageBox.warning(self,"BLF 자동 입력","BLF에서 CAN Message를 찾지 못했습니다.")
                return False
            duration=max(0.0,last_timestamp-first_timestamp)
            start_text="0.000"
            end_text=f"{duration:.3f}"
            selected=list(getattr(self,"tc_related_parse_signals",[]) or [])
            filter_text=", ".join(selected)
            if hasattr(self,"blf_start_time"): self.blf_start_time.setText(start_text)
            if hasattr(self,"blf_end_time"): self.blf_end_time.setText(end_text)
            if hasattr(self,"signal_filter") and filter_text: self.signal_filter.setText(filter_text)
            if hasattr(self,"u_start"): self.u_start.setText(start_text)
            if hasattr(self,"u_end"): self.u_end.setText(end_text)
            if hasattr(self,"u_filter") and filter_text: self.u_filter.setText(filter_text)
            self.blf_auto_scope={"start_sec":0.0,"end_sec":round(duration,3),"message_count":message_count,"signals":selected}
            if show_message:
                QMessageBox.information(self,"BLF 자동 입력",f"기록 구간: 0.000 ~ {duration:.3f} sec\n메시지: {message_count:,}개\nSignal Filter: {filter_text or '확정 Signal 없음'}")
            return True

    def sync_selected_signals_to_filter(self):
            selected=list(getattr(self,"tc_related_parse_signals",[]) or [])
            text=", ".join(selected)
            if hasattr(self,"signal_filter"): self.signal_filter.setText(text)
            if hasattr(self,"u_filter"): self.u_filter.setText(text)
            if hasattr(self,"u_tc_signal_status"): self.u_tc_signal_status.setText(f"분석 Signal {len(selected)}개 확정")
            return text

    def attach_blf_file(self):
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Select Vector BLF Log",
                "",
                "Vector BLF Files (*.blf);;All Files (*.*)"
            )
            if not file_path:
                return
            self.blf_file_path = file_path
            self.blf_summary_data = {}
            self.blf_full_signal_timeline = []
            self.tc_blf_validation_data = {}
            self.blf_summary_preview.clear()
            self.update_blf_status()
            self.auto_fill_blf_time_and_signal_filter(show_message=False)

    def attach_dbc_file(self):
            file_paths, _ = QFileDialog.getOpenFileNames(
                self, "Select CAN Databases", "", "CAN Database Files (*.dbc);;All Files (*.*)"
            )
            if not file_paths:
                return
            changed = False
            for file_path in file_paths:
                if file_path not in self.dbc_file_paths:
                    self.dbc_file_paths.append(file_path)
                    changed = True
            if changed:
                # DBC가 바뀔 때만 캐시를 무효화한다. 같은 DBC의 반복 파싱을 막는다.
                self._dbc_cache_key = None
                self._dbc_catalog_cache = []
                self._dbc_name_index_cache = {}
                self._dbc_cache_errors = []
                self._dbc_database_cache = None
            self.blf_summary_data = {}
            self.blf_summary_preview.clear()
            self.update_blf_status()
            if changed:
                QApplication.setOverrideCursor(Qt.WaitCursor)
                try:
                    self.build_dbc_context_catalog()
                finally:
                    QApplication.restoreOverrideCursor()
            if "TC Generation" in self.mode.currentText() and getattr(self, "current_ai_result_data", {}).get("test_cases"):
                self.apply_dbc_combined_autocorrection(show_message=True)

    def current_dbc_cache_key(self):
            key=[]
            for path in self.dbc_file_paths:
                try:
                    stat=os.stat(path)
                    key.append((os.path.abspath(path),stat.st_mtime_ns,stat.st_size))
                except OSError:
                    key.append((os.path.abspath(path),0,0))
            return tuple(key)

    def ensure_dbc_cache(self):
            """DBC를 파일 변경 시 한 번만 읽고 Signal catalog와 name index를 재사용한다."""
            key=self.current_dbc_cache_key()
            if key == getattr(self,"_dbc_cache_key",None) and getattr(self,"_dbc_catalog_cache",None):
                return
            self._dbc_cache_key=key
            self._dbc_catalog_cache=[]
            self._dbc_name_index_cache={}
            self._dbc_cache_errors=[]
            self._dbc_database_cache=None
            if cantools is None or not self.dbc_file_paths:
                return
            merged=cantools.database.Database()
            used_ids=set()
            for dbc_path in self.dbc_file_paths:
                try:
                    database=cantools.database.load_file(dbc_path)
                    for message in database.messages:
                        if message.frame_id not in used_ids:
                            try:
                                merged.messages.append(message)
                                used_ids.add(message.frame_id)
                            except Exception:
                                pass
                        msg_norm=re.sub(r"[^a-z0-9]","",message.name.lower())
                        self._dbc_name_index_cache.setdefault(msg_norm,set()).add(message.name)
                        for signal in message.signals:
                            sig_norm=re.sub(r"[^a-z0-9]","",signal.name.lower())
                            self._dbc_name_index_cache.setdefault(sig_norm,set()).add(signal.name)
                            self._dbc_catalog_cache.append({
                                "signal":signal.name,
                                "message":message.name,
                                "can_id":f"0x{message.frame_id:X}",
                                "words":set(self.split_dbc_identifier_words(signal.name)),
                                "choices":{str(k):str(v) for k,v in (signal.choices or {}).items()},
                            })
                except Exception as error:
                    self._dbc_cache_errors.append(f"{os.path.basename(dbc_path)}: {type(error).__name__}: {error}")
            try:
                merged.refresh()
                self._dbc_database_cache=merged
            except Exception:
                self._dbc_database_cache=None

    def build_local_dbc_name_index(self):
            """캐시된 DBC Message/Signal 명칭을 반환한다."""
            self.ensure_dbc_cache()
            return self._dbc_name_index_cache, list(self._dbc_cache_errors)

    def apply_dbc_safe_autocorrection(self, show_message=True):
            """AI TC의 식별자를 DBC 실제 명칭으로 안전하게 정규화한다.
    
            대소문자, 공백, 하이픈, 언더스코어만 다른 경우이면서 DBC 후보가 하나일 때만 수정한다.
            기능 로직, 상태값, 시간값은 추측해서 변경하지 않는다.
            """
            data = getattr(self, "current_ai_result_data", {})
            if not isinstance(data, dict) or not isinstance(data.get("test_cases"), list):
                if show_message:
                    QMessageBox.information(self, "DBC Auto Correction", "먼저 TC Generation JSON을 Paste하세요.")
                return 0
            if not self.dbc_file_paths:
                if show_message:
                    QMessageBox.information(self, "DBC Auto Correction", "먼저 DBC 파일을 선택하세요.")
                return 0
            index, errors = self.build_local_dbc_name_index()
            if not index:
                if show_message:
                    QMessageBox.warning(self, "DBC Auto Correction", "DBC에서 Message/Signal 명칭을 읽지 못했습니다.\n" + "\n".join(errors))
                return 0
    
            changed=0
            identifier_pattern=re.compile(r"\b[A-Za-z][A-Za-z0-9_-]{2,}\b")
    
            def fix_text(value):
                nonlocal changed
                text=str(value)
                def replace(match):
                    nonlocal changed
                    original=match.group(0)
                    normalized=re.sub(r"[^a-z0-9]", "", original.lower())
                    candidates=index.get(normalized, set())
                    if len(candidates) != 1:
                        return original
                    canonical=next(iter(candidates))
                    if original == canonical:
                        return original
                    changed += 1
                    return canonical
                return identifier_pattern.sub(replace,text)
    
            for tc in data["test_cases"]:
                tc_changes=[]
                for field in ("title", "risk_description"):
                    if isinstance(tc.get(field), str):
                        before=tc[field]; after=fix_text(before)
                        if after != before:
                            tc[field]=after; tc_changes.append(f"{field}: DBC 실제 명칭으로 정규화")
                for field in ("preconditions", "steps", "expected_results"):
                    values=tc.get(field)
                    if isinstance(values,list):
                        fixed=[]
                        field_changed=False
                        for item in values:
                            after=fix_text(item)
                            fixed.append(after)
                            field_changed = field_changed or after != str(item)
                        tc[field]=fixed
                        if field_changed:
                            tc_changes.append(f"{field}: DBC 실제 명칭으로 정규화")
                if tc_changes:
                    auto=tc.setdefault("auto_review", {})
                    revisions=auto.setdefault("revisions_applied", [])
                    for note in tc_changes:
                        if note not in revisions:
                            revisions.append(note)
                    auto["review_result"]="PASS_AFTER_REVISION"
                    auto["review_comment"]=(str(auto.get("review_comment", "")).strip()+" DBC 로컬 명칭 정규화를 적용했습니다.").strip()
    
            self.current_ai_result_data=data
            self.ai_result.setPlainText(json.dumps(data,ensure_ascii=False,indent=4))
            if show_message:
                msg=f"DBC 로컬 자동 보정 완료\n\n변경된 식별자: {changed}개"
                if errors:
                    msg += "\n\n읽기 경고:\n" + "\n".join(errors)
                msg += "\n\n기능 로직, 상태값, 시간 기준은 자동 변경하지 않았습니다."
                QMessageBox.information(self,"DBC Auto Correction",msg)
            return changed

    def split_dbc_identifier_words(self, value):
            text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(value))
            text = re.sub(r"[^A-Za-z0-9]+", " ", text).lower()
            return [word for word in text.split() if word]

    def build_dbc_context_catalog(self):
            """캐시된 DBC Signal catalog를 반환한다. DBC가 바뀔 때만 다시 생성한다."""
            self.ensure_dbc_cache()
            return self._dbc_catalog_cache, list(self._dbc_cache_errors)

    def context_terms_from_sentence(self, sentence):
            """TBD 주변 한글/영문 설명을 DBC 식별자 비교용 영문 개념어로 변환한다."""
            text = str(sentence).lower()
            terms = set(self.split_dbc_identifier_words(text))
            aliases = {
                "digital": ("digital", "디지털"),
                "key": ("key", "키"),
                "auth": ("auth", "authentication", "인증"),
                "result": ("result", "결과"),
                "status": ("status", "state", "상태"),
                "request": ("request", "req", "요청"),
                "door": ("door", "도어"),
                "driver": ("driver", "운전석", "driver door"),
                "unlock": ("unlock", "잠금 해제", "해제"),
                "lock": ("lock", "잠금"),
                "uwb": ("uwb",),
                "ble": ("ble",),
                "nfc": ("nfc",),
                "ranging": ("ranging", "거리 측정", "레인징"),
                "position": ("position", "location", "위치"),
                "connection": ("connection", "connect", "연결"),
                "session": ("session", "세션"),
                "error": ("error", "fault", "오류", "에러"),
                "timeout": ("timeout", "타임아웃"),
                "active": ("active", "활성"),
                "vehicle": ("vehicle", "차량"),
            }
            for canonical, patterns in aliases.items():
                if any(pattern in text for pattern in patterns):
                    terms.add(canonical)
            return terms

    def score_dbc_context_candidate(self, sentence, candidate):
            terms = self.context_terms_from_sentence(sentence)
            words = candidate.get("words", set())
            if not terms or not words:
                return 0.0
            exact = len(terms & words)
            partial = 0
            for term in terms - words:
                if any(term in word or word in term for word in words if len(term) >= 3 and len(word) >= 3):
                    partial += 1
            important = {"auth", "request", "door", "driver", "unlock", "lock", "uwb", "ble", "ranging", "position", "connection", "result", "status"}
            important_hits = len((terms & words) & important)
            denominator = max(2, min(len(terms & important) or len(terms), len(words)))
            score = (exact + 0.45 * partial + 0.35 * important_hits) / denominator
            return min(score, 1.0)

    def apply_dbc_context_match(self, show_message=True):
            """'신호(TBD)' 문맥을 DBC Signal 후보와 비교한다.
    
            고유하고 신뢰도 높은 후보만 자동 적용한다. 거리, 시간, 영역, 횟수 TBD는 유지한다.
            """
            data = getattr(self, "current_ai_result_data", {})
            if not isinstance(data, dict) or not isinstance(data.get("test_cases"), list):
                return 0
            catalog, errors = self.build_dbc_context_catalog()
            if not catalog:
                return 0
            report = []
            changed = 0
            protected_terms = ("영역", "거리", "시간", "timeout 기준", "타임아웃 기준", "횟수", "주기", "반경")
            signal_markers = ("신호", "signal", "can", "상태", "요청", "결과")
            tbd_pattern = re.compile(r"(?P<context>[^\n]{2,80}?)(?:\s*(?:신호|signal|can signal|can 신호))?\s*\(tbd\)", re.I)
    
            def replace_text(tc_id, field, value):
                nonlocal changed
                text = str(value)
                def repl(match):
                    nonlocal changed
                    full = match.group(0)
                    context = match.group("context").strip()
                    lower = full.lower()
                    if any(term in lower for term in protected_terms):
                        report.append({"tc_id":tc_id,"field":field,"original":full,"candidate":"","score":0,"message":"","can_id":"","status":"KEPT_TBD","reason":"요구사항 기준값 TBD"})
                        return full
                    if not any(marker in lower for marker in signal_markers):
                        return full
                    scored = sorted(((self.score_dbc_context_candidate(full, item), item) for item in catalog), key=lambda x:x[0], reverse=True)
                    best_score, best = scored[0]
                    second_score = scored[1][0] if len(scored)>1 else 0.0
                    margin = best_score - second_score
                    if best_score >= 0.72 and margin >= 0.12:
                        changed += 1
                        replacement = best["signal"] + " Signal"
                        report.append({"tc_id":tc_id,"field":field,"original":full,"candidate":best["signal"],"score":round(best_score,3),"message":best["message"],"can_id":best["can_id"],"status":"APPLIED","reason":"고유한 고신뢰도 문맥 일치"})
                        return replacement
                    if best_score >= 0.48:
                        report.append({"tc_id":tc_id,"field":field,"original":full,"candidate":best["signal"],"score":round(best_score,3),"message":best["message"],"can_id":best["can_id"],"status":"확인 필요","reason":"후보 유사도 또는 후보 간 점수 차이 부족"})
                    return full
                return tbd_pattern.sub(repl, text)
    
            for tc in data["test_cases"]:
                tc_id = tc.get("tc_id", "")
                notes = []
                for field in ("preconditions", "steps", "expected_results"):
                    values = tc.get(field)
                    if not isinstance(values, list):
                        continue
                    fixed = []
                    field_changed = False
                    for value in values:
                        updated = replace_text(tc_id, field, value)
                        fixed.append(updated)
                        field_changed = field_changed or updated != str(value)
                    tc[field] = fixed
                    if field_changed:
                        notes.append(f"{field}: DBC Context Match 적용")
                if notes:
                    auto = tc.setdefault("auto_review", {})
                    revisions = auto.setdefault("revisions_applied", [])
                    for note in notes:
                        if note not in revisions:
                            revisions.append(note)
                    auto["review_result"] = "PASS_AFTER_REVISION"
                    auto["review_comment"] = (str(auto.get("review_comment", "")).strip() + " DBC Context Match 적용.").strip()
            self.dbc_context_match_report = report
            self.current_ai_result_data = data
            self.ai_result.setPlainText(json.dumps(data, ensure_ascii=False, indent=4))
            if show_message:
                recommended = sum(1 for row in report if row["status"] == "확인 필요")
                kept = sum(1 for row in report if row["status"] == "KEPT_TBD")
                QMessageBox.information(self, "DBC Context Match", f"자동 적용: {changed}개\n검토 추천: {recommended}개\n요구사항 TBD 유지: {kept}개\n\n거리, 시간, 영역, 횟수 기준은 자동 변경하지 않습니다.")
            return changed

    def apply_dbc_combined_autocorrection(self, show_message=True):
            exact_count = self.apply_dbc_safe_autocorrection(show_message=False)
            context_count = self.apply_dbc_context_match(show_message=False)
            if show_message:
                review_count = sum(1 for row in self.dbc_context_match_report if row.get("status") == "확인 필요")
                QMessageBox.information(self, "DBC Auto Correction", f"정확 명칭 보정: {exact_count}개\n문맥 기반 Signal 적용: {context_count}개\n검토 추천: {review_count}개\n\nDBC 분석과 수정은 현재 PC에서 로컬로 수행됩니다.")
            return exact_count + context_count

    def add_dbc_context_match_sheet(self, workbook):
            if not self.dbc_context_match_report:
                return
            ws = workbook.create_sheet("DBC Context Match")
            ws.append(["TC ID","Field","Original","DBC Candidate","Score","Message","CAN ID","Status","Reason"])
            for row in self.dbc_context_match_report:
                ws.append([row.get("tc_id",""),row.get("field",""),row.get("original",""),row.get("candidate",""),row.get("score",""),row.get("message",""),row.get("can_id",""),row.get("status",""),row.get("reason","")])
            self.style_excel_sheet(ws)
            colors={"APPLIED":"C6EFCE","확인 필요":"FFF2CC","KEPT_TBD":"E7E6E6"}
            for row_index in range(2, ws.max_row+1):
                fill=PatternFill("solid",fgColor=colors.get(str(ws.cell(row_index,8).value),"FFFFFF"))
                for cell in ws[row_index]: cell.fill=fill

    def rebuild_signal_aliases(self):
            ordered=[]
            for signal in self.preferred_dbc_signals + list(self.signal_function_mapping.values()):
                if signal and signal not in ordered:
                    ordered.append(signal)
            self.preferred_signal_aliases={signal:f"SIG_{index:03d}" for index,signal in enumerate(ordered,1)}

    def refresh_signal_tools_status(self):
            review_count=sum(1 for row in self.auto_mapping_report if row.get("status")=="확인 필요")
            if hasattr(self,"preferred_signal_status"):
                self.preferred_signal_status.setText(f"세트 {self.active_signal_set or '없음'} | 매핑 {len(self.signal_function_mapping)} | 선택 {len(self.preferred_dbc_signals)} | 검토 {review_count}")
                self.preferred_signal_status.setWordWrap(True)
            if hasattr(self,"signal_mapping_status"): self.signal_mapping_status.hide()

    def mapped_signals_for_analysis(self):
            result=[]
            for signal in self.preferred_dbc_signals + list(self.signal_function_mapping.values()):
                if signal and signal not in result:
                    result.append(signal)
            return result

    def extract_function_items_for_mapping(self):
            """TC Generation 실행 조건 또는 Validation 입력에서 Signal 기능 항목을 추출한다."""
            if "TC Generation" in self.mode.currentText():
                self.store_tc_generation_page_values()
                source=self.tc_generation_observations
            else:
                source=self.purpose.toPlainText()+"\n"+self.expected.toPlainText()
            items=[]
            for raw in source.splitlines():
                text=re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*","",raw).strip()
                text=re.sub(r"\s*(?:신호|signal|can signal|can 신호)?\s*\(tbd\)\s*$","",text,flags=re.I).strip()
                if len(text)<2: continue
                if any(word in text.lower() for word in ("가능한 조작","불가능한 조작","can monitoring","blf recording")): continue
                if any(marker in raw.lower() for marker in ("신호","signal","request","status","result","상태","결과","요청","ranging","인증")):
                    if text not in items: items.append(text)
            return items

    def auto_mapping_score(self, function_name, candidate):
            """100점 기준: Signal 65, Message 15, Preferred 10, 상태값 목록 10, 충돌 감점."""
            function_terms=self.context_terms_from_sentence(function_name)
            signal_terms=set(self.split_dbc_identifier_words(candidate.get("signal","")))
            message_terms=set(self.split_dbc_identifier_words(candidate.get("message","")))
            important={"digital","key","auth","result","status","request","door","driver","passenger","front","rear","lock","unlock","open","closed","uwb","ble","ranging","position","connection","session","error","timeout"}
            common=function_terms & signal_terms
            important_common=common & important
            signal_score=min(65, len(common)*10 + len(important_common)*7)
            message_common=function_terms & message_terms
            message_score=min(15, len(message_common)*5)
            preferred_score=10 if candidate.get("signal") in self.preferred_dbc_signals else 0
            choices_text=" ".join(candidate.get("choices",{}).values()).lower()
            value_score=0
            aliases={"lock":("locked","lock"),"unlock":("unlocked","unlock"),"open":("open","opened"),"closed":("closed","close"),"success":("success","ok"),"fail":("fail","failed","error")}
            for term,patterns in aliases.items():
                if term in function_terms and any(pattern in choices_text for pattern in patterns): value_score+=5
            value_score=min(10,value_score)
            conflicts=[("lock","unlock",35),("open","lock",20),("request","status",15),("result","request",15),("front","rear",30),("driver","passenger",30)]
            penalty=0; conflict_labels=[]
            for wanted,opposite,cost in conflicts:
                if wanted in function_terms and opposite in signal_terms and wanted not in signal_terms:
                    penalty+=cost; conflict_labels.append(f"{wanted}!={opposite}")
                if opposite in function_terms and wanted in signal_terms and opposite not in signal_terms:
                    penalty+=cost; conflict_labels.append(f"{opposite}!={wanted}")
            score=max(0,min(100,signal_score+message_score+preferred_score+value_score-penalty))
            return score, sorted(common), conflict_labels

    def recommend_signal_mappings(self, function_items=None):
            """각 기능 항목에 대해 60점 이상 상위 5개 후보를 반환한다."""
            catalog, errors = self.build_dbc_context_catalog()
            if not catalog:
                return []
            function_items = function_items or self.extract_function_items_for_mapping()
            report = []
            for function_name in function_items:
                if function_name in self.signal_function_mapping:
                    signal_name = self.signal_function_mapping[function_name]
                    report.append({
                        "function": function_name,
                        "candidate": signal_name,
                        "score": 100,
                        "margin": 100,
                        "status": "직접 지정",
                        "matched": [],
                        "conflicts": [],
                        "candidates": [{
                            "signal": signal_name, "message": "", "can_id": "",
                            "score": 100, "matched": [], "conflicts": [],
                        }],
                    })
                    continue
    
                ranked = []
                for candidate in catalog:
                    score, matched, conflicts = self.auto_mapping_score(function_name, candidate)
                    ranked.append({
                        "signal": candidate.get("signal", ""),
                        "message": candidate.get("message", ""),
                        "can_id": candidate.get("can_id", ""),
                        "score": score,
                        "matched": matched,
                        "conflicts": conflicts,
                        "choices": candidate.get("choices", {}),
                    })
                ranked.sort(key=lambda row: row["score"], reverse=True)
                best = ranked[0]
                second_score = ranked[1]["score"] if len(ranked) > 1 else 0
                margin = best["score"] - second_score
                core_hits = len([
                    term for term in best["matched"]
                    if term in {"auth", "request", "door", "lock", "unlock", "uwb", "ble", "ranging", "result", "status", "driver", "passenger"}
                ])
                if best["score"] >= 90 and margin >= 12 and core_hits >= 2 and not best["conflicts"]:
                    status = "자동 적용"
                elif best["score"] >= 70:
                    status = "확인 필요"
                else:
                    status = "연결 안 됨"
    
                visible_candidates = [row for row in ranked if row["score"] >= 60][:5]
                if not visible_candidates:
                    visible_candidates = ranked[:3]
                report.append({
                    "function": function_name,
                    "candidate": best["signal"],
                    "message": best["message"],
                    "can_id": best["can_id"],
                    "score": best["score"],
                    "margin": margin,
                    "status": status,
                    "matched": best["matched"],
                    "conflicts": best["conflicts"],
                    "candidates": visible_candidates,
                })
            self.auto_mapping_report = report
            return report

    def open_signal_mapping_dialog(self):
            catalog, errors = self.build_dbc_context_catalog()
            if not catalog:
                QMessageBox.warning(self, "신호 설정", "먼저 DBC 파일을 선택하세요.")
                return
            unique = {}
            for item in catalog:
                unique.setdefault(item["signal"], item)
    
            dialog = QDialog(self)
            dialog.setWindowTitle("기능별 신호 후보 찾기")
            dialog.resize(920, 680)
            layout = QVBoxLayout(dialog)
            guide = QLabel(
                "각 기능 항목마다 관련 후보를 최대 5개 보여줍니다. "
                "확실한 항목만 자동 적용하고, 비슷한 후보가 여러 개면 원하는 후보를 직접 선택하세요."
            )
            guide.setWordWrap(True)
            layout.addWidget(guide)
    
            button_row = QHBoxLayout()
            load_btn = QPushButton("확인 항목 가져오기")
            recommend_btn = QPushButton("비슷한 신호 찾기")
            apply_auto_btn = QPushButton("확실한 추천만 적용")
            button_row.addWidget(load_btn)
            button_row.addWidget(recommend_btn)
            button_row.addWidget(apply_auto_btn)
            button_row.addStretch()
            layout.addLayout(button_row)
    
            result_list = QListWidget()
            result_list.setSelectionMode(QListWidget.SingleSelection)
            layout.addWidget(result_list, 1)
    
            detail_label = QLabel("후보를 선택하면 Message, CAN ID, 점수와 일치 단어를 확인할 수 있습니다.")
            detail_label.setWordWrap(True)
            detail_label.setStyleSheet("padding:6px; border:1px solid #b9c6d0; border-radius:4px;")
            layout.addWidget(detail_label)
    
            edit_row = QHBoxLayout()
            function_edit = QLineEdit()
            function_edit.setPlaceholderText("기능 항목")
            signal_combo = QComboBox()
            signal_combo.setEditable(True)
            signal_combo.addItems(sorted(unique, key=str.lower))
            set_btn = QPushButton("이 신호로 지정")
            edit_row.addWidget(function_edit, 2)
            edit_row.addWidget(signal_combo, 2)
            edit_row.addWidget(set_btn)
            layout.addLayout(edit_row)
    
            working = dict(self.signal_function_mapping)
            functions = []
            current_report = []
    
            def render():
                result_list.clear()
                rows = current_report or [
                    {
                        "function": key, "candidate": value, "score": 100,
                        "margin": 100, "status": "직접 지정",
                        "matched": [], "conflicts": [],
                        "candidates": [{"signal": value, "message": "", "can_id": "", "score": 100, "matched": [], "conflicts": []}],
                    }
                    for key, value in working.items()
                ]
                for row in rows:
                    header = QListWidgetItem(
                        f'[{row["status"]}] {row["function"]} | 1위 {row["candidate"]} | {row["score"]}점 | 후보 차이 {row["margin"]}점'
                    )
                    header.setData(Qt.UserRole, {"type": "function", "row": row})
                    result_list.addItem(header)
                    for rank, candidate in enumerate(row.get("candidates", []), start=1):
                        conflict_text = ", ".join(candidate.get("conflicts", [])) or "없음"
                        item = QListWidgetItem(
                            f'    {rank}. {candidate["signal"]} | {candidate.get("message", "")} | '
                            f'{candidate.get("can_id", "")} | {candidate["score"]}점 | 충돌: {conflict_text}'
                        )
                        item.setData(Qt.UserRole, {
                            "type": "candidate", "function": row["function"], "candidate": candidate,
                        })
                        result_list.addItem(item)
    
            def load_items():
                nonlocal functions, current_report
                functions = self.extract_function_items_for_mapping()
                current_report = []
                result_list.clear()
                for function_name in functions:
                    item = QListWidgetItem(f"[대기] {function_name}")
                    result_list.addItem(item)
                QMessageBox.information(dialog, "확인 항목", f"기능 항목 {len(functions)}개를 가져왔습니다.")
    
            def recommend():
                nonlocal current_report
                current_report = self.recommend_signal_mappings(functions or self.extract_function_items_for_mapping())
                render()
    
            def apply_auto():
                for row in current_report:
                    if row["status"] == "자동 적용":
                        working[row["function"]] = row["candidate"]
                render()
    
            def select_row(item):
                data = item.data(Qt.UserRole)
                if not isinstance(data, dict):
                    return
                if data.get("type") == "candidate":
                    function_name = data["function"]
                    candidate = data["candidate"]
                    function_edit.setText(function_name)
                    signal_combo.setCurrentText(candidate["signal"])
                    matched = ", ".join(candidate.get("matched", [])) or "없음"
                    conflicts = ", ".join(candidate.get("conflicts", [])) or "없음"
                    detail_label.setText(
                        f'기능 항목: {function_name}\n'
                        f'신호: {candidate["signal"]}\n'
                        f'Message: {candidate.get("message", "")}\n'
                        f'CAN ID: {candidate.get("can_id", "")}\n'
                        f'점수: {candidate["score"]}\n'
                        f'일치 단어: {matched}\n'
                        f'의미 충돌: {conflicts}'
                    )
                elif data.get("type") == "function":
                    row = data["row"]
                    function_edit.setText(row["function"])
                    signal_combo.setCurrentText(row["candidate"])
    
            def set_manual():
                function_name = function_edit.text().strip()
                signal_name = signal_combo.currentText().strip()
                if not function_name or signal_name not in unique:
                    QMessageBox.warning(dialog, "직접 지정", "기능 항목과 DBC 신호를 선택하세요.")
                    return
                working[function_name] = signal_name
                found = False
                for row in current_report:
                    if row["function"] == function_name:
                        dbc_item = unique[signal_name]
                        row.update({
                            "candidate": signal_name, "score": 100, "margin": 100,
                            "status": "직접 지정", "conflicts": [],
                            "candidates": [{
                                "signal": signal_name, "message": dbc_item.get("message", ""),
                                "can_id": dbc_item.get("can_id", ""), "score": 100,
                                "matched": [], "conflicts": [],
                            }],
                        })
                        found = True
                        break
                if not found:
                    current_report.append({
                        "function": function_name, "candidate": signal_name,
                        "score": 100, "margin": 100, "status": "직접 지정",
                        "matched": [], "conflicts": [],
                        "candidates": [{
                            "signal": signal_name, "message": unique[signal_name].get("message", ""),
                            "can_id": unique[signal_name].get("can_id", ""),
                            "score": 100, "matched": [], "conflicts": [],
                        }],
                    })
                render()
    
            load_btn.clicked.connect(load_items)
            recommend_btn.clicked.connect(recommend)
            apply_auto_btn.clicked.connect(apply_auto)
            result_list.itemClicked.connect(select_row)
            set_btn.clicked.connect(set_manual)
    
            bottom = QHBoxLayout()
            save_btn = QPushButton("설정 저장")
            cancel_btn = QPushButton("취소")
            bottom.addStretch()
            bottom.addWidget(save_btn)
            bottom.addWidget(cancel_btn)
            layout.addLayout(bottom)
            save_btn.clicked.connect(dialog.accept)
            cancel_btn.clicked.connect(dialog.reject)
            render()
    
            if dialog.exec() != QDialog.Accepted:
                return
            self.signal_function_mapping = working
            self.rebuild_signal_aliases()
            self.refresh_signal_tools_status()

    def apply_signal_mapping_to_tc(self):
            data=getattr(self,"current_ai_result_data",{}); cases=data.get("test_cases") if isinstance(data,dict) else None
            if not self.signal_function_mapping or not isinstance(cases,list): return 0
            changed=0
            def fix(value):
                nonlocal changed
                text=str(value); sentence_terms=self.context_terms_from_sentence(text); ranked=[]
                for fn,sig in self.signal_function_mapping.items():
                    terms=self.context_terms_from_sentence(fn); score=len(terms & sentence_terms)+(10 if fn.lower() in text.lower() else 0); ranked.append((score,fn,sig))
                ranked.sort(reverse=True)
                if not ranked or ranked[0][0]<=0: return text
                score,fn,sig=ranked[0]
                updated=re.sub(re.escape(fn)+r"\s*(?:신호|signal|can signal|can 신호)?\s*\(tbd\)",sig+" Signal",text,flags=re.I)
                if updated==text and score>=2 and "(tbd)" in text.lower(): updated=re.sub(r"[^\n]{0,60}?\(tbd\)",sig+" Signal",text,count=1,flags=re.I)
                if updated!=text: changed+=1
                return updated
            for tc in cases:
                for field in ("preconditions","steps","expected_results"):
                    if isinstance(tc.get(field),list): tc[field]=[fix(item) for item in tc[field]]
            if changed: self.current_ai_result_data=data; self.ai_result.setPlainText(json.dumps(data,ensure_ascii=False,indent=4))
            return changed

    def update_blf_status(self):
            blf_name = os.path.basename(self.blf_file_path) if self.blf_file_path else "미선택"
            dbc_names = [os.path.basename(path) for path in self.dbc_file_paths]
            if not dbc_names:
                dbc_text = "미선택"
            elif len(dbc_names) <= 3:
                dbc_text = ", ".join(dbc_names)
            else:
                dbc_text = ", ".join(dbc_names[:3]) + f" 외 {len(dbc_names) - 3}개"
            decoded = "Signal Decode 가능" if self.dbc_file_paths else "Raw CAN 요약"
            self.blf_status_label.setText(
                f"BLF: {blf_name}\nDBC ({len(dbc_names)}개): {dbc_text}\nMode: {decoded}"
            )

    def get_blf_time_range(self):
            start_text = self.blf_start_time.text().strip()
            end_text = self.blf_end_time.text().strip()
            try:
                start_sec = float(start_text) if start_text else 0.0
                end_sec = float(end_text) if end_text else None
            except ValueError:
                raise ValueError("Start sec와 End sec는 숫자로 입력하세요.")
            if start_sec < 0:
                raise ValueError("Start sec는 0 이상이어야 합니다.")
            if end_sec is not None and end_sec <= start_sec:
                raise ValueError("End sec는 Start sec보다 커야 합니다.")
            return start_sec, end_sec

    def get_signal_filter_keywords(self):
            if not hasattr(self, "signal_filter"):
                return []
            return [
                keyword.strip().lower()
                for keyword in self.signal_filter.text().split(",")
                if keyword.strip()
            ]

    def matches_signal_filter(self, message_name, signal_name, keywords):
            selected=self.mapped_signals_for_analysis()
            if selected:
                return signal_name in selected
            if not keywords:
                return True
            searchable=f"{message_name} {signal_name}".lower()
            return any(keyword in searchable for keyword in keywords)

    def event_priority(self, event):
            text = json.dumps(event, ensure_ascii=False).lower()
            critical_words = ("error", "fail", "failed", "timeout", "invalid", "fault")
            if any(word in text for word in critical_words):
                return 0
            if event.get("event_type") == "signal_change":
                return 1
            return 2

    def get_tp_can_id_filter(self):
            if not hasattr(self, "tp_can_ids"):
                return set()
            values = set()
            for token in self.tp_can_ids.text().replace(";", ",").split(","):
                token = token.strip()
                if not token:
                    continue
                try:
                    values.add(int(token, 0))
                except ValueError:
                    raise ValueError(f"잘못된 TP CAN ID: {token}")
            return values

    def decode_uds_payload(self, payload):
            if not payload:
                return {}
            sid = payload[0]
            service_names = {
                0x10: "DiagnosticSessionControl", 0x11: "ECUReset",
                0x14: "ClearDiagnosticInformation", 0x19: "ReadDTCInformation",
                0x22: "ReadDataByIdentifier", 0x23: "ReadMemoryByAddress",
                0x27: "SecurityAccess", 0x28: "CommunicationControl",
                0x2E: "WriteDataByIdentifier", 0x2F: "InputOutputControlByIdentifier",
                0x31: "RoutineControl", 0x34: "RequestDownload",
                0x36: "TransferData", 0x37: "RequestTransferExit",
                0x3E: "TesterPresent", 0x85: "ControlDTCSetting"
            }
            nrc_names = {
                0x10: "General Reject", 0x11: "Service Not Supported",
                0x12: "SubFunction Not Supported", 0x13: "Incorrect Message Length",
                0x21: "Busy Repeat Request", 0x22: "Conditions Not Correct",
                0x24: "Request Sequence Error", 0x31: "Request Out Of Range",
                0x33: "Security Access Denied", 0x35: "Invalid Key",
                0x36: "Exceeded Number Of Attempts", 0x37: "Required Time Delay Not Expired",
                0x70: "Upload Download Not Accepted", 0x71: "Transfer Data Suspended",
                0x72: "General Programming Failure", 0x73: "Wrong Block Sequence Counter",
                0x78: "Response Pending"
            }
            result = {"service_id": f"0x{sid:02X}"}
            if sid == 0x7F and len(payload) >= 3:
                request_sid, nrc = payload[1], payload[2]
                result.update({
                    "response_type": "NEGATIVE",
                    "request_service_id": f"0x{request_sid:02X}",
                    "service_name": service_names.get(request_sid, "UNKNOWN"),
                    "negative_response_code": f"0x{nrc:02X}",
                    "negative_response_name": nrc_names.get(nrc, "UNKNOWN")
                })
            elif sid >= 0x40 and (sid - 0x40) in service_names:
                request_sid = sid - 0x40
                result.update({
                    "response_type": "POSITIVE",
                    "request_service_id": f"0x{request_sid:02X}",
                    "service_name": service_names[request_sid]
                })
            else:
                result.update({
                    "response_type": "REQUEST_OR_UNCLASSIFIED",
                    "service_name": service_names.get(sid, "UNKNOWN")
                })
            if sid in (0x22, 0x2E, 0x2F) and len(payload) >= 3:
                result["did"] = f"0x{payload[1]:02X}{payload[2]:02X}"
            if sid in (0x62, 0x6E, 0x6F) and len(payload) >= 3:
                result["did"] = f"0x{payload[1]:02X}{payload[2]:02X}"
            if sid in (0x10, 0x11, 0x27, 0x28, 0x31, 0x3E) and len(payload) >= 2:
                result["sub_function"] = f"0x{payload[1]:02X}"
            return result

    def process_isotp_frame(self, message, relative_time, sessions, active, tp_ids):
            can_id = int(message.arbitration_id)
            if tp_ids and can_id not in tp_ids:
                return
            data = bytes(message.data)
            if not data:
                return
            frame_type = data[0] >> 4
            if frame_type not in (0, 1, 2, 3):
                return
            # Auto mode may false-positive on normal CAN. Requiring valid PCI lengths limits it.
            if frame_type == 0:
                length = data[0] & 0x0F
                if length == 0 or length > len(data) - 1:
                    return
                payload = data[1:1 + length]
                sessions.append({
                    "protocol": "ISO-TP", "can_id": f"0x{can_id:X}",
                    "start_time_sec": round(relative_time, 6), "end_time_sec": round(relative_time, 6),
                    "frame_count": 1, "payload_length": len(payload), "status": "COMPLETE",
                    "payload_hex": payload.hex(" ").upper(), "uds": self.decode_uds_payload(payload)
                })
            elif frame_type == 1:
                if len(data) < 2:
                    return
                total_length = ((data[0] & 0x0F) << 8) | data[1]
                if total_length <= 7 or total_length > TP_MAX_PAYLOAD_BYTES:
                    return
                active[can_id] = {
                    "start": relative_time, "total_length": total_length,
                    "payload": bytearray(data[2:]), "frame_count": 1,
                    "next_sequence": 1, "issues": [], "flow_control": []
                }
            elif frame_type == 2:
                state = active.get(can_id)
                if not state:
                    return
                sequence = data[0] & 0x0F
                if sequence != state["next_sequence"]:
                    state["issues"].append(
                        f"SEQUENCE_MISMATCH expected={state['next_sequence']} received={sequence}"
                    )
                state["next_sequence"] = (sequence + 1) & 0x0F
                state["payload"].extend(data[1:])
                state["frame_count"] += 1
                if len(state["payload"]) >= state["total_length"]:
                    payload = bytes(state["payload"][:state["total_length"]])
                    sessions.append({
                        "protocol": "ISO-TP", "can_id": f"0x{can_id:X}",
                        "start_time_sec": round(state["start"], 6),
                        "end_time_sec": round(relative_time, 6),
                        "duration_ms": round((relative_time - state["start"]) * 1000, 3),
                        "frame_count": state["frame_count"],
                        "payload_length": len(payload),
                        "status": "COMPLETE" if not state["issues"] else "COMPLETE_WITH_ISSUES",
                        "issues": state["issues"],
                        "payload_hex": payload.hex(" ").upper(),
                        "uds": self.decode_uds_payload(payload)
                    })
                    del active[can_id]
            elif frame_type == 3:
                flow_status = data[0] & 0x0F
                sessions.append({
                    "protocol": "ISO-TP", "can_id": f"0x{can_id:X}",
                    "start_time_sec": round(relative_time, 6), "end_time_sec": round(relative_time, 6),
                    "frame_count": 1, "status": "FLOW_CONTROL",
                    "flow_status": {0: "CONTINUE", 1: "WAIT", 2: "OVERFLOW"}.get(flow_status, "UNKNOWN"),
                    "block_size": data[1] if len(data) > 1 else None,
                    "st_min_raw": data[2] if len(data) > 2 else None
                })

    def add_manual_dbc_signals(self):
            """자동 후보와 별개로 DBC 전체 목록에서 분석 Signal을 직접 추가한다."""
            catalog,_errors=self.build_dbc_context_catalog()
            if not catalog:
                QMessageBox.warning(self,"Signal 직접 추가","먼저 DBC 파일을 연결하세요."); return []
            dialog=QDialog(self); dialog.setWindowTitle("분석 Signal 직접 추가"); dialog.resize(760,620)
            layout=QVBoxLayout(dialog); guide=QLabel("검색 후 원하는 DBC Signal을 체크하세요. 기존 TC 관련 Signal 선택에 추가됩니다."); guide.setWordWrap(True); layout.addWidget(guide)
            search=QLineEdit(); search.setPlaceholderText("Signal / Message / CAN ID 검색"); layout.addWidget(search)
            items=QListWidget(); layout.addWidget(items,1)
            unique=[]; seen=set()
            for row in catalog:
                key=(row.get("signal",""),row.get("message",""),row.get("can_id",""))
                if key[0] and key not in seen: seen.add(key); unique.append(row)
            current=set(getattr(self,"tc_related_parse_signals",[]) or [])
            def refresh(text=""):
                query=str(text).strip().lower(); items.clear()
                for row in unique:
                    label=f"{row.get('signal','')}  |  {row.get('message','')}  |  {row.get('can_id','')}"
                    if query and query not in label.lower(): continue
                    item=QListWidgetItem(label); item.setData(Qt.UserRole,row.get("signal","")); item.setFlags(item.flags()|Qt.ItemIsUserCheckable)
                    item.setCheckState(Qt.Checked if row.get("signal","") in current else Qt.Unchecked); items.addItem(item)
            search.textChanged.connect(refresh); refresh()
            row=QHBoxLayout(); ok=QPushButton("선택 Signal 추가"); cancel=QPushButton("취소"); row.addStretch(); row.addWidget(ok); row.addWidget(cancel); layout.addLayout(row); ok.clicked.connect(dialog.accept); cancel.clicked.connect(dialog.reject)
            if dialog.exec()!=QDialog.Accepted: return []
            added=[]
            for i in range(items.count()):
                item=items.item(i)
                if item.checkState()==Qt.Checked: added.append(item.data(Qt.UserRole))
            merged=[]
            for signal in list(current)+added:
                if signal and signal not in merged: merged.append(signal)
            self.tc_related_parse_signals=merged
            self.sync_selected_signals_to_filter()
            return merged

    def _tc_text_for_signal_selection(self):
            """현재 Validation TC의 모든 판정 문구를 하나의 검색 문맥으로 합친다."""
            parts=[]
            widgets=("tc","validation_preconditions","validation_steps","validation_expected_results","validation_actual_results","analysis_question")
            for name in widgets:
                widget=getattr(self,name,None)
                if isinstance(widget,QLineEdit): parts.append(widget.text())
                elif isinstance(widget,QTextEdit): parts.append(widget.toPlainText())
            return "\n".join(part for part in parts if str(part).strip())

    def find_tc_related_dbc_signals(self, limit=30):
            """TC 문구와 DBC 메타데이터를 비교해 관련 Signal 후보만 반환한다."""
            tc_text=self._tc_text_for_signal_selection().strip()
            catalog,_errors=self.build_dbc_context_catalog()
            if not tc_text or not catalog: return []
            normalized_text=self._normalize_signal_match_name(tc_text)
            text_tokens=set(normalized_text.split())
            explicit=set(self.mapped_signals_for_analysis())
            rows=[]; seen=set()
            for item in catalog:
                name=str(item.get("signal","")).strip()
                if not name or name in seen: continue
                seen.add(name)
                norm=self._normalize_signal_match_name(name); tokens=set(norm.split())
                direct=bool(norm and norm in normalized_text)
                overlap=len(tokens & text_tokens)/max(1,len(tokens))
                message_norm=self._normalize_signal_match_name(item.get("message",""))
                message_overlap=len(set(message_norm.split()) & text_tokens)/max(1,len(set(message_norm.split()))) if message_norm else 0.0
                context=self.score_dbc_context_candidate(tc_text,item)
                score=1.0 if name in explicit else (0.72 if direct else 0.0)+0.18*overlap+0.10*message_overlap+0.18*context
                if name in explicit or direct or overlap>=0.50 or score>=0.48:
                    rows.append({"signal":name,"message":item.get("message",""),"can_id":item.get("can_id",""),"score":round(min(score,1.0),3),"direct":direct,"explicit":name in explicit})
            rows.sort(key=lambda row:(row["explicit"],row["direct"],row["score"]),reverse=True)
            return rows[:limit]

    def select_tc_related_signals(self, show_dialog=True):
            """후보를 체크 목록으로 보여주고 BLF 파싱 대상을 확정한다."""
            rows=self.find_tc_related_dbc_signals()
            if not rows:
                QMessageBox.warning(self,"TC 관련 Signal","TC 문구와 DBC에서 관련 Signal 후보를 찾지 못했습니다.\n\nTC의 Precondition, Steps, Expected, Actual에 기능명 또는 Signal명을 더 구체적으로 작성하세요.")
                return []
            if not show_dialog:
                self.tc_related_parse_signals=[row["signal"] for row in rows if row["explicit"] or row["direct"] or row["score"]>=0.58]
                return list(self.tc_related_parse_signals)
            dialog=QDialog(self); dialog.setWindowTitle("TC 관련 Signal 확정"); dialog.resize(720,560)
            layout=QVBoxLayout(dialog)
            guide=QLabel("TC 문구와 DBC를 비교한 후보입니다. 체크된 Signal만 BLF에서 디코딩·분석합니다.\n변화가 없어도 체크된 Signal은 판정 근거로 유지됩니다.")
            guide.setWordWrap(True); layout.addWidget(guide)
            items=QListWidget(); layout.addWidget(items,1)
            current=set(getattr(self,"tc_related_parse_signals",[]) or [])
            for row in rows:
                label=f"{row['signal']}  |  {row['message']}  |  {row['can_id']}  |  score {row['score']:.2f}"
                item=QListWidgetItem(label); item.setData(Qt.UserRole,row["signal"]); item.setFlags(item.flags()|Qt.ItemIsUserCheckable)
                auto=row["explicit"] or row["direct"] or row["score"]>=0.58
                item.setCheckState(Qt.Checked if (row["signal"] in current or auto) else Qt.Unchecked); items.addItem(item)
            button_row=QHBoxLayout(); all_btn=QPushButton("전체 선택"); clear_btn=QPushButton("전체 해제"); ok_btn=QPushButton("분석 Signal 확정"); cancel_btn=QPushButton("취소")
            all_btn.clicked.connect(lambda:[items.item(i).setCheckState(Qt.Checked) for i in range(items.count())])
            clear_btn.clicked.connect(lambda:[items.item(i).setCheckState(Qt.Unchecked) for i in range(items.count())])
            ok_btn.clicked.connect(dialog.accept); cancel_btn.clicked.connect(dialog.reject)
            for button in (all_btn,clear_btn): button_row.addWidget(button)
            button_row.addStretch(); button_row.addWidget(ok_btn); button_row.addWidget(cancel_btn); layout.addLayout(button_row)
            if dialog.exec()!=QDialog.Accepted: return []
            selected=[items.item(i).data(Qt.UserRole) for i in range(items.count()) if items.item(i).checkState()==Qt.Checked]
            if not selected:
                QMessageBox.warning(self,"TC 관련 Signal","최소 1개 Signal을 선택해야 합니다."); return []
            self.tc_related_parse_signals=selected
            self.sync_selected_signals_to_filter()
            return list(selected)

    def parse_blf_locally(self):
            if can is None:
                QMessageBox.warning(
                    self,
                    "BLF Parser Missing",
                    "BLF 로컬 파싱에 python-can이 필요합니다.\n\n"
                    "설치 명령:\npip install python-can\n\n"
                    "DBC 신호 해석도 사용하려면:\npip install cantools"
                )
                return
            if not self.blf_file_path or not os.path.isfile(self.blf_file_path):
                QMessageBox.warning(self, "BLF 확인", "먼저 BLF 파일을 선택하세요.")
                return
            if self.dbc_file_paths and cantools is None:
                QMessageBox.warning(
                    self,
                    "DBC Decoder Missing",
                    "DBC 신호 해석에 cantools가 필요합니다.\n\n설치 명령:\npip install cantools"
                )
                return
    
            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                start_sec, end_sec = self.get_blf_time_range()
                keywords = self.get_signal_filter_keywords()
                event_limit = self.ai_event_limit.value() if hasattr(self, "ai_event_limit") else 40
    
                database = None
                dbc_load_errors = []
                if self.dbc_file_paths:
                    database = cantools.database.Database()
                    used_frame_ids = set()
                    for dbc_path in self.dbc_file_paths:
                        try:
                            loaded_database = cantools.database.load_file(dbc_path)
                            for dbc_message in loaded_database.messages:
                                if dbc_message.frame_id in used_frame_ids:
                                    dbc_load_errors.append(
                                        f"중복 CAN ID 0x{dbc_message.frame_id:X}: {dbc_message.name} 제외"
                                    )
                                    continue
                                database.messages.append(dbc_message)
                                used_frame_ids.add(dbc_message.frame_id)
                        except Exception as error:
                            dbc_load_errors.append(
                                f"{os.path.basename(dbc_path)}: {type(error).__name__}: {error}"
                            )
                    database.refresh()
                    if not database.messages:
                        raise ValueError("선택한 DBC 파일에서 메시지를 불러오지 못했습니다.")
    
                tc_only_mode=True
                selected_tc_signals=set(getattr(self,"tc_related_parse_signals",[]) or [])
                if tc_only_mode and database is not None and not selected_tc_signals:
                    QApplication.restoreOverrideCursor()
                    selected=self.select_tc_related_signals(show_dialog=True)
                    QApplication.setOverrideCursor(Qt.WaitCursor)
                    selected_tc_signals=set(selected)
                    if not selected_tc_signals: return
                selected_tc_frame_ids=set()
                if database is not None and selected_tc_signals:
                    for dbc_message in database.messages:
                        if any(signal.name in selected_tc_signals for signal in dbc_message.signals):
                            selected_tc_frame_ids.add(int(dbc_message.frame_id))
    
                reader = can.BLFReader(self.blf_file_path)
                first_timestamp = None
                total_messages = 0
                selected_messages = 0
                decoded_messages = 0
                decode_errors = 0
                filtered_signal_changes = 0
                repeated_values_removed = 0
                id_counts = Counter()
                signal_states = {}
                raw_states = {}
                raw_change_counts = Counter()
                candidate_events = []
                all_decoded_signal_events = []
                tp_sessions = []
                active_tp_sessions = {}
                tp_ids = self.get_tp_can_id_filter()
                tp_enabled = hasattr(self, "tp_mode") and self.tp_mode.currentText() != "Off"
    
                try:
                    for message in reader:
                        total_messages += 1
                        if first_timestamp is None:
                            first_timestamp = float(message.timestamp)
                        relative_time = float(message.timestamp) - first_timestamp
                        if relative_time < start_sec:
                            continue
                        if end_sec is not None and relative_time > end_sec:
                            break
    
                        selected_messages += 1
                        can_id = int(message.arbitration_id)
                        if selected_tc_frame_ids and can_id not in selected_tc_frame_ids:
                            continue
                        can_id_text = f"0x{can_id:X}"
                        id_counts[can_id_text] += 1
                        payload = bytes(message.data)
                        if tp_enabled:
                            self.process_isotp_frame(
                                message, relative_time, tp_sessions, active_tp_sessions, tp_ids
                            )
                        decoded_ok = False
    
                        if database is not None:
                            try:
                                dbc_message = database.get_message_by_frame_id(can_id)
                                decoded = dbc_message.decode(
                                    payload,
                                    decode_choices=True,
                                    allow_truncated=True
                                )
                                decoded_messages += 1
                                decoded_ok = True
                                for signal_name, value in decoded.items():
                                    if selected_tc_signals and signal_name not in selected_tc_signals:
                                        continue
                                    state_key = f"{dbc_message.name}.{signal_name}"
                                    value_text = str(value)
                                    if state_key in signal_states and signal_states[state_key] == value_text:
                                        repeated_values_removed += 1
                                        continue
                                    previous = signal_states.get(state_key, "UNOBSERVED")
                                    signal_states[state_key] = value_text
                                    signal_event = {
                                        "time_sec": round(relative_time, 6),
                                        "event_type": "signal_change",
                                        "message": dbc_message.name,
                                        "signal": signal_name,
                                        "from": previous,
                                        "to": value_text
                                    }
                                    # TC-BLF 판정용 전체 Timeline은 Signal Filter와 무관하게 로컬 보관한다.
                                    all_decoded_signal_events.append(signal_event)
                                    # Signal Filter는 화면/AI 요약 이벤트 수를 줄이는 데만 사용한다.
                                    if not self.matches_signal_filter(
                                        dbc_message.name,
                                        signal_name,
                                        keywords
                                    ):
                                        continue
                                    filtered_signal_changes += 1
                                    candidate_events.append(dict(signal_event))
                            except Exception:
                                decode_errors += 1
    
                        if not decoded_ok:
                            previous_payload = raw_states.get(can_id)
                            if previous_payload == payload:
                                repeated_values_removed += 1
                                continue
                            raw_states[can_id] = payload
                            if raw_change_counts[can_id] >= BLF_MAX_RAW_CHANGES_PER_ID:
                                continue
                            raw_change_counts[can_id] += 1
                            candidate_events.append({
                                "time_sec": round(relative_time, 6),
                                "event_type": "raw_payload_change",
                                "can_id": can_id_text,
                                "previous_data": (
                                    previous_payload.hex(" ").upper()
                                    if previous_payload is not None else "UNOBSERVED"
                                ),
                                "current_data": payload.hex(" ").upper()
                            })
                finally:
                    reader.stop()
    
                for can_id, state in active_tp_sessions.items():
                    payload = bytes(state["payload"][:state["total_length"]])
                    tp_sessions.append({
                        "protocol": "ISO-TP", "can_id": f"0x{can_id:X}",
                        "start_time_sec": round(state["start"], 6),
                        "end_time_sec": None, "frame_count": state["frame_count"],
                        "expected_payload_length": state["total_length"],
                        "received_payload_length": len(payload),
                        "status": "INCOMPLETE", "issues": state["issues"] + ["MISSING_CONSECUTIVE_FRAME"],
                        "payload_hex": payload.hex(" ").upper(),
                        "uds": self.decode_uds_payload(payload)
                    })
    
                # 최초 관측값만 있고 실제 값 전이가 없는 Signal은 핵심 분석에서 제외한다.
                # 직접 선택하거나 매핑한 Signal은 현재값 확인을 위해 유지한다.
                signal_value_sets={}; signal_real_change_counts=Counter()
                for event in all_decoded_signal_events:
                    signal_key=(event.get("message",""),event.get("signal",""))
                    signal_value_sets.setdefault(signal_key,set()).add(str(event.get("to")))
                    if event.get("from")!="UNOBSERVED" and str(event.get("from"))!=str(event.get("to")):
                        signal_real_change_counts[signal_key]+=1
                always_keep_signals=set(self.mapped_signals_for_analysis()) | set(selected_tc_signals)
                changing_signal_keys={key for key,values in signal_value_sets.items() if len(values)>1 or signal_real_change_counts.get(key,0)>0 or key[1] in always_keep_signals}
                no_change_signals_removed=len(signal_value_sets)-len(changing_signal_keys)
                all_decoded_signal_events=[event for event in all_decoded_signal_events if (event.get("message",""),event.get("signal","")) in changing_signal_keys]
                candidate_events=[event for event in candidate_events if event.get("event_type")!="signal_change" or (event.get("message",""),event.get("signal","")) in changing_signal_keys]
    
                # Full decoded timeline is kept locally for deterministic TC-BLF comparison.
                self.blf_full_signal_timeline = list(all_decoded_signal_events)
    
                # Error/failure events first, then preserve chronological order within the selected set.
                prioritized = sorted(
                    candidate_events,
                    key=lambda item: (self.event_priority(item), item.get("time_sec", 0))
                )[:event_limit]
                key_timeline = sorted(prioritized, key=lambda item: item.get("time_sec", 0))
    
                important_findings = []
                for event in key_timeline:
                    event_text = json.dumps(event, ensure_ascii=False).lower()
                    if any(word in event_text for word in ("error", "fail", "timeout", "invalid", "fault")):
                        if event.get("event_type") == "signal_change":
                            important_findings.append(
                                f"{event['time_sec']}s {event['signal']}: {event['from']} -> {event['to']}"
                            )
                        else:
                            important_findings.append(
                                f"{event['time_sec']}s {event['can_id']} raw payload changed"
                            )
                    if len(important_findings) >= 10:
                        break
    
                self.blf_summary_data = {
                    "source": {
                        "blf_file": os.path.basename(self.blf_file_path),
                        "dbc_files": [os.path.basename(path) for path in self.dbc_file_paths],
                        "raw_file_sent_to_ai": False
                    },
                    "analysis_window": {
                        "start_sec": start_sec,
                        "end_sec": end_sec,
                        "time_reference": "BLF first message = 0 sec"
                    },
                    "compression": {
                        "method": "signal changes only; repeated values removed",
                        "signal_filter": keywords,
                        "event_limit": event_limit,
                        "candidate_changes": len(candidate_events),
                        "prompt_events": len(key_timeline),
                        "repeated_values_removed": repeated_values_removed,
                        "no_change_signals_removed": no_change_signals_removed,
                        "tc_related_signals": sorted(selected_tc_signals),
                        "parse_scope": "TC_RELATED_ONLY",
                        "events_truncated": len(candidate_events) > len(key_timeline)
                    },
                    "statistics": {
                        "total_messages_scanned": total_messages,
                        "selected_messages": selected_messages,
                        "decoded_messages": decoded_messages,
                        "decode_errors": decode_errors,
                        "filtered_signal_changes": filtered_signal_changes,
                        "local_validation_signal_changes": len(all_decoded_signal_events),
                        "local_validation_unique_signals": len({e.get("signal") for e in all_decoded_signal_events}),
                        "unique_can_ids": len(id_counts),
                        "dbc_load_errors": dbc_load_errors
                    },
                    "important_findings": important_findings,
                    "key_timeline": key_timeline,
                    "transport_protocol_summary": {
                        "mode": self.tp_mode.currentText() if hasattr(self, "tp_mode") else "Off",
                        "configured_can_ids": [f"0x{value:X}" for value in sorted(tp_ids)],
                        "session_count": len(tp_sessions),
                        "sessions_truncated": len(tp_sessions) > TP_MAX_SESSIONS_IN_PROMPT,
                        "sessions": tp_sessions[:TP_MAX_SESSIONS_IN_PROMPT]
                    }
                }
    
                formatted = json.dumps(self.blf_summary_data, ensure_ascii=False, indent=2)
                estimated_prompt_chars = len(formatted)
                self.blf_summary_preview.setPlainText(formatted)
                self.update_blf_status()
                self.blf_status_label.setText(
                    self.blf_status_label.text()
                    + f"\nCompressed: {selected_messages:,} msgs -> {len(key_timeline)} events"
                    + f" | Summary: {estimated_prompt_chars:,} chars"
                )
                QMessageBox.information(
                    self,
                    "BLF Compact Parse Complete",
                    f"선택 메시지: {selected_messages:,}개\n"
                    f"반복값 제거: {repeated_values_removed:,}개\n"
                    f"변화 없는 Signal 제외: {no_change_signals_removed:,}개\n"
                    f"AI 핵심 이벤트: {len(key_timeline)}개\n"
                    f"요약 길이: {estimated_prompt_chars:,}자\n\n"
                    "BLF 원본은 AI로 전송되지 않습니다."
                )
            except Exception as error:
                self.blf_summary_data = {}
                QMessageBox.critical(
                    self,
                    "BLF Parse Error",
                    f"BLF 파일을 분석하지 못했습니다.\n\n{type(error).__name__}: {error}"
                )
            finally:
                QApplication.restoreOverrideCursor()

