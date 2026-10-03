from .core_runtime import *


class TcEngineMixin:
    def update_tc_generation_sequence_mode(self, mode):
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

    def switch_tc_generation_page(self, page):
            if "TC Generation" not in self.mode.currentText():
                return
            page = page if page in {"basic", "execution", "sequence"} else "basic"
            if page != self.tc_generation_page:
                self.store_tc_generation_page_values()
                self.tc_generation_page = page
                self.load_tc_generation_page_values()

    def get_tc_generation_prompt_inputs(self):
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
    - Signal 확인만 연속으로 나열하지 않는다.
    - 각 Signal 확인 전에 해당 상태를 발생시키는 물리적 조작을 배치한다.
    - Door Open, Door Close, Lock, Unlock, Key 이동은 필요한 경우 각각 별도 Step으로 작성한다.
    - 수행 가능한 조작에 없는 ECU 내부 변수 변경이나 Signal 강제 설정을 생성하지 않는다.
    - 요구사항에 없는 시간, 거리, 횟수는 TBD로 유지한다.
    - 생성한 수행 순서는 사용자 검토가 필요한 초안으로 취급한다.
    """
            elif mode == "사용자 흐름 우선":
                sequence_instruction = """
    [Sequence Generation Mode: USER FLOW FIRST]
    - [Mandatory Test Execution Sequence]의 핵심 흐름과 순서를 유지한다.
    - 축약된 흐름을 실제 수행 가능한 상세 Step으로 확장한다.
    - 필요한 초기 Signal 확인, 상태 전이 확인, 최종 물리 동작 확인을 적절한 위치에 추가한다.
    - 물리적 조작과 Signal 확인을 별도 Step으로 작성한다.
    - 중복 Signal 확인은 제거하되 사용자가 지정한 핵심 조작은 삭제하지 않는다.
    """
            else:
                sequence_instruction = """
    [Sequence Generation Mode: USER SEQUENCE FIXED]
    - [Mandatory Test Execution Sequence]의 번호, 항목 수, 순서를 변경하지 않는다.
    - 사용자 Step을 추가, 삭제, 병합, 분할 또는 재배열하지 않는다.
    - 각 Step의 문장만 명확하게 정리하고 같은 번호의 Expected Result를 작성한다.
    - 필요한 Signal과 기대 상태는 기존 Step 문장 또는 Expected Result 안에서만 구체화한다.
    """
            requirement += "\n" + sequence_instruction.strip()
            return requirement.strip(), self.tc_generation_acceptance.strip()

    def _numbered_items(self, text):
            items=[]
            for raw in str(text or "").splitlines():
                line=raw.strip()
                if not line: continue
                match=re.match(r"^(?:Step\s*)?(\d+(?:[-.]\d+)*)\s*[.)：:]?\s*(.*)$",line,re.I)
                if match:
                    items.append((match.group(1),match.group(2).strip() or line))
                else:
                    items.append((str(len(items)+1),line))
            return items

    def update_validation_pair_status(self):
            if not hasattr(self,'validation_pair_status'): return
            pc=self._numbered_items(self.validation_preconditions.toPlainText()) if hasattr(self,'validation_preconditions') else []
            st=self._numbered_items(self.validation_steps.toPlainText()) if hasattr(self,'validation_steps') else []
            ex=self._numbered_items(self.validation_expected_results.toPlainText()) if hasattr(self,'validation_expected_results') else []
            ac=self._numbered_items(self.validation_actual_results.toPlainText()) if hasattr(self,'validation_actual_results') else []
            step_ids={n for n,_ in st}; expected_ids={n for n,_ in ex}; actual_ids={n for n,_ in ac}
            paired=len(step_ids & expected_ids)
            missing_ex=len(step_ids-expected_ids)
            missing_ac=len(step_ids-actual_ids) if ac else len(step_ids)
            fourth_name = "Review 기준" if hasattr(self,"mode") and "TC Review" in self.mode.currentText() else "Actual"
            self.validation_pair_status.setText(
                f"Precondition {len(pc)} | Step {len(st)} | Expected {len(ex)} | {fourth_name} {len(ac)} | 대응 {paired} | Expected 누락 {missing_ex}"
            )
            color='#16836f' if missing_ex==0 and st else '#a56a08'
            self.validation_pair_status.setStyleSheet(f"color:{color}; font-size:8pt; padding:2px 4px;")

    def normalize_active_validation_tab(self):
            if not hasattr(self, "validation_tabs"):
                return
            editor=self.validation_tabs.currentWidget()
            if hasattr(editor, "normalize_current_text"):
                editor.normalize_current_text()
            self.update_validation_pair_status()

    def sync_structured_validation_to_legacy_fields(self):
            if not hasattr(self,'validation_preconditions'):
                return
            mode=self.mode.currentText() if hasattr(self,"mode") else ""
            pre=self.validation_preconditions.toPlainText().strip()
            steps=self.validation_steps.toPlainText().strip()
            expected=self.validation_expected_results.toPlainText().strip()
            fourth=self.validation_actual_results.toPlainText().strip()
    
            purpose_blocks=[]
            if pre: purpose_blocks.append('[Preconditions]\n'+pre)
            if steps: purpose_blocks.append('[Test Steps]\n'+steps)
    
            if "TC Review" in mode:
                expected_blocks=[]
                if expected: expected_blocks.append('[Expected Results]\n'+expected)
                if fourth: expected_blocks.append('[Review Criteria]\n'+fourth)
                self.purpose.setPlainText('\n\n'.join(purpose_blocks))
                self.expected.setPlainText('\n\n'.join(expected_blocks))
            else:
                if expected: purpose_blocks.append('[Expected Results]\n'+expected)
                self.purpose.setPlainText('\n\n'.join(purpose_blocks))
                self.expected.setPlainText(fourth)
            self.update_validation_pair_status()

    def extract_tc_blf_validation_rules(self):
            if hasattr(self,'validation_expected_results') and 'Validation Analysis' in self.mode.currentText():
                source=self.validation_expected_results.toPlainText()
            else:
                source=self.purpose.toPlainText()+'\n'+self.expected.toPlainText()
            pattern=re.compile(r"(?<![A-Za-z0-9_])(?P<signal>[A-Za-z][A-Za-z0-9_]{2,})\s*(?P<op>==|!=|>=|<=|=|>|<)\s*(?P<value>[A-Za-z0-9_.+\-]+)")
            rules=[]
            current='UNSPECIFIED'
            for line_no,line in enumerate(source.splitlines(),1):
                sm=re.search(r"(?:Step|Expected(?:\s*Result)?|Result|단계)\s*[-:#.]?\s*(\d+(?:[-.]\d+)*)",line,re.I)
                if sm: current=sm.group(1)
                for m in pattern.finditer(line):
                    rules.append({'rule_id':f'R{len(rules)+1:03d}','step':current,'source_line':line_no,'source_text':line.strip(),'signal':m.group('signal'),'operator':m.group('op'),'expected':m.group('value')})
            return rules

    def _normalize_signal_match_name(self, value):
            text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(value or ""))
            text = re.sub(r"[^A-Za-z0-9]+", " ", text).lower().strip()
            aliases = {"req":"request","sts":"status","stat":"status","res":"result","rsp":"response","cmd":"command","drv":"driver","psg":"passenger","veh":"vehicle"}
            return " ".join(aliases.get(token, token) for token in text.split())

    def resolve_tc_signal_to_dbc(self, requested_name):
            """TC 문구 Signal명을 DBC 실제 Signal명에 임계값 기반으로 연결한다."""
            requested=str(requested_name or "").strip(); catalog,_=self.build_dbc_context_catalog()
            if not requested or not catalog: return {"requested":requested,"resolved":requested,"score":0.0,"status":"UNRESOLVED"}
            by_name={}
            for item in catalog: by_name.setdefault(item.get("signal",""),item)
            for function_name,signal_name in self.signal_function_mapping.items():
                if requested.lower() in {str(function_name).lower(),str(signal_name).lower()} and signal_name in by_name:
                    return {"requested":requested,"resolved":signal_name,"score":1.0,"status":"DIRECT_MAPPING"}
            wanted_norm=self._normalize_signal_match_name(requested)
            exact=[name for name in by_name if self._normalize_signal_match_name(name)==wanted_norm]
            if len(exact)==1: return {"requested":requested,"resolved":exact[0],"score":1.0,"status":"NORMALIZED_EXACT"}
            wanted_tokens=set(wanted_norm.split()); ranked=[]
            for name,item in by_name.items():
                candidate_norm=self._normalize_signal_match_name(name); candidate_tokens=set(candidate_norm.split())
                if not wanted_tokens or not candidate_tokens: continue
                common=wanted_tokens & candidate_tokens; union=wanted_tokens | candidate_tokens
                containment=len(common)/max(1,min(len(wanted_tokens),len(candidate_tokens)))
                jaccard=len(common)/max(1,len(union))
                substring=1.0 if wanted_norm in candidate_norm or candidate_norm in wanted_norm else 0.0
                context_score=self.score_dbc_context_candidate(requested,item)
                score=0.45*containment+0.25*jaccard+0.20*context_score+0.10*substring
                ranked.append((score,name,item))
            ranked.sort(key=lambda row:row[0],reverse=True)
            if not ranked: return {"requested":requested,"resolved":requested,"score":0.0,"status":"UNRESOLVED"}
            best_score,best_name,best_item=ranked[0]; second=ranked[1][0] if len(ranked)>1 else 0.0; margin=best_score-second
            base={"requested":requested,"resolved":best_name,"score":round(best_score,3),"margin":round(margin,3),"message":best_item.get("message",""),"can_id":best_item.get("can_id","")}
            if best_score>=0.60 and margin>=0.08: base["status"]="FUZZY_APPLIED"; return base
            if best_score>=0.45: base["status"]="REVIEW_REQUIRED"; return base
            return {"requested":requested,"resolved":requested,"score":round(best_score,3),"margin":round(margin,3),"status":"UNRESOLVED"}

    def _coerce_rule_value(self,value):
            text=str(value).strip()
            try:return float(text)
            except Exception:return text.upper()

    def _compare_rule_value(self,observed,operator,expected):
            left=self._coerce_rule_value(observed); right=self._coerce_rule_value(expected)
            if operator in {'=','=='}: return left==right
            if operator=='!=': return left!=right
            if not isinstance(left,float) or not isinstance(right,float): return None
            return {'>':left>right,'<':left<right,'>=':left>=right,'<=':left<=right}.get(operator)

    def run_tc_blf_auto_validation(self):
            if not getattr(self,'blf_summary_data',None):
                QMessageBox.warning(self,'TC-BLF Auto Validation','먼저 BLF와 DBC를 선택하고 Parse BLF Locally를 실행하세요.'); return
            timeline=getattr(self,'blf_full_signal_timeline',[])
            if not timeline:
                # 이전 파서가 가진 key_timeline도 안전하게 fallback으로 사용
                timeline=[e for e in self.blf_summary_data.get('key_timeline',[]) if e.get('event_type')=='signal_change']
            rules=self.extract_tc_blf_validation_rules()
            if not rules:
                QMessageBox.information(self,'TC-BLF Auto Validation',"Expected Results에서 'Signal = Value' 형식의 조건을 찾지 못했습니다.\n정확한 Signal은 AUTO, 기능 설명은 DBC Mapping 후 분석하세요."); return
            results=[]
            for rule in rules:
                resolution=self.resolve_tc_signal_to_dbc(rule['signal'])
                resolved_signal=resolution.get('resolved') or rule['signal']
                events=[e for e in timeline if str(e.get('signal','')).lower()==str(resolved_signal).lower()]
                item=dict(rule); item['observations']=[]
                item['signal_resolution']=resolution; item['resolved_signal']=resolved_signal
                if not events:
                    item.update(result='INCONCLUSIVE',confidence='LOW',reason=('DBC Decode Timeline에서 대상 Signal을 찾지 못했습니다.' + (f" 후보 {resolved_signal}은 임계값/후보 차이 부족으로 검토가 필요합니다." if resolution.get('status')=='REVIEW_REQUIRED' else '')),cause_candidates=['DBC/BLF 버전 확인','Signal Filter 및 분석 구간 확인','DBC Context Match로 Signal Mapping 확인'])
                else:
                    matched=[]
                    for e in events:
                        ok=self._compare_rule_value(e.get('to'),rule['operator'],rule['expected'])
                        item['observations'].append({'time_sec':e.get('time_sec'),'message':e.get('message'),'from':e.get('from'),'to':e.get('to'),'matched':ok})
                        if ok is True: matched.append(e)
                    if matched:
                        item.update(result='PASS',confidence='HIGH',reason='기대 조건과 일치하는 값이 BLF에서 직접 확인되었습니다.',first_match_time_sec=matched[0].get('time_sec'))
                    else:
                        item.update(result='FAIL',confidence='HIGH',reason='Signal은 수신됐지만 기대 조건과 일치하는 값이 확인되지 않았습니다.',cause_candidates=['선행 Vehicle/ECU 상태 미충족','요청 이후 응답 또는 상태 전이 지연','Validity/Timeout/통신 영향','DBC와 SW 버전 불일치 가능성'])
                results.append(item)
            counts=Counter(r['result'] for r in results)
            report={'engine':'TC-BLF Local Validation v1','notice':'명확한 Signal 조건만 로컬 계산합니다. 원인 후보는 확정 원인이 아닙니다.','summary':{'rules':len(results),'PASS':counts.get('PASS',0),'FAIL':counts.get('FAIL',0),'REVIEW':counts.get('REVIEW',0),'INCONCLUSIVE':counts.get('INCONCLUSIVE',0)},'results':results}
            self.tc_blf_validation_data=report
            self.blf_summary_data['tc_blf_local_validation']=report
            self.blf_summary_preview.setPlainText(json.dumps(report,ensure_ascii=False,indent=2))
            QMessageBox.information(self,'TC-BLF Auto Validation',f"로컬 비교 완료\nPASS {counts.get('PASS',0)} | FAIL {counts.get('FAIL',0)} | INCONCLUSIVE {counts.get('INCONCLUSIVE',0)}")

    def is_safe_summary_mode(self):
            return (
                not hasattr(self, "ai_transmission_mode")
                or self.ai_transmission_mode.currentIndex() == 0
            )

    def is_semantic_preserve_mode(self):
            return hasattr(self,"ai_transmission_mode") and self.ai_transmission_mode.currentIndex()==1

    def _ensure_semantic_signal_aliases(self):
            ordered=[]
            for signal in list(getattr(self,"tc_related_parse_signals",[]) or []) + self.mapped_signals_for_analysis():
                if signal and signal not in ordered: ordered.append(signal)
            catalog,_errors=self.build_dbc_context_catalog()
            tc_text=self._tc_text_for_signal_selection() if hasattr(self,"_tc_text_for_signal_selection") else ""
            for item in catalog:
                signal=item.get("signal","")
                if signal and signal in tc_text and signal not in ordered: ordered.append(signal)
            self.preferred_signal_aliases={signal:f"SIG_{index:03d}" for index,signal in enumerate(ordered,1)}
            return dict(self.preferred_signal_aliases)

    def _semantic_rewrite_line(self, text, aliases):
            """문장 구조는 유지하고 Signal 및 기술 식별자만 일관된 별칭으로 치환한다."""
            line=str(text or "").strip()
            if not line: return ""
            for signal,alias in sorted(aliases.items(),key=lambda row:len(row[0]),reverse=True):
                line=re.sub(r"(?<![A-Za-z0-9_])"+re.escape(signal)+r"(?![A-Za-z0-9_])",alias,line,flags=re.I)
            if not hasattr(self,"semantic_entity_aliases"):
                self.semantic_entity_aliases={}
            protected={
                "ON","OFF","OPEN","CLOSE","CLOSED","LOCK","LOCKED","UNLOCK","UNLOCKED",
                "ACTIVE","INACTIVE","REQUEST","SUCCESS","FAIL","FAILED","PASS","CAN","LIN",
                "UDS","ISO","TP","BLF","DBC","AUTO","TIMEOUT","TRUE","FALSE"
            }
            protected.update(aliases.values())
            def mask_identifier(match):
                token=match.group(0)
                upper=token.upper()
                if upper in protected or re.fullmatch(r"SIG_\d{3}",upper): return token
                if re.fullmatch(r"0x[0-9A-Fa-f]+",token): return token
                # 일반 영단어와 단위는 유지하고, 사내 코드/기능/ECU 식별자 형태만 치환한다.
                technical=("_" in token or bool(re.search(r"[a-z][A-Z]|[A-Z][a-z]+[A-Z]",token)) or bool(re.search(r"\d",token)))
                if not technical: return token
                if token not in self.semantic_entity_aliases:
                    self.semantic_entity_aliases[token]=f"LOCAL_REF_{len(self.semantic_entity_aliases)+1:03d}"
                return self.semantic_entity_aliases[token]
            return re.sub(r"\b[A-Za-z][A-Za-z0-9_]{3,}\b",mask_identifier,line)

    def build_semantic_preserved_tc_context(self):
            """TC 원문을 보내지 않고 의미 단위 구조, Signal 별칭, 판정 수치만 생성한다."""
            aliases=self._ensure_semantic_signal_aliases()
            self.semantic_entity_aliases={}
            sections=[
                ("Preconditions",getattr(self,"validation_preconditions",None)),
                ("Actions",getattr(self,"validation_steps",None)),
                ("Expected Behavior",getattr(self,"validation_expected_results",None)),
                ("Actual Observation",getattr(self,"validation_actual_results",None)),
            ]
            context=[]
            for title,widget in sections:
                text=widget.toPlainText().strip() if isinstance(widget,QTextEdit) else ""
                lines=[]
                for raw in text.splitlines():
                    rewritten=self._semantic_rewrite_line(raw,aliases)
                    if rewritten: lines.append("- "+rewritten)
                context.append(f"[{title}]\n"+("\n".join(lines) if lines else "- 정보 없음"))
            rules=self.extract_tc_blf_validation_rules()
            if rules:
                rule_lines=[]
                for rule in rules:
                    signal=aliases.get(rule.get("signal"),rule.get("signal"))
                    rule_lines.append(f"- {signal} {rule.get('operator')} {rule.get('expected')} (Step {rule.get('step')})")
                context.append("[Preserved Validation Criteria]\n"+"\n".join(rule_lines))
            context.append("[Signal Alias Policy]\n- 실제 DBC Signal명은 로컬에서만 관리한다.\n- AI에는 SIG_### 별칭만 제공한다.\n- 값, 비교 연산자, 시간과 단위는 원래 판정 의미를 유지한다.")
            return "\n\n".join(context), aliases

    def build_secure_blf_summary(self):
            """TC 원문, 파일명, 실제 Message/Signal 이름과 raw payload 없이 BLF 로컬 요약만 만든다."""
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
            if not hasattr(self,"ai_transmission_notice"): return
            index=self.ai_transmission_mode.currentIndex() if hasattr(self,"ai_transmission_mode") else 0
            if index==0:
                text="보안 기본 · TC 원문/Expected 원문 제외 · 익명 BLF 로컬 요약만 포함"
                style="color:#28645f; background:#edf9f7; border:1px solid #addbd5; border-radius:4px; padding:5px; font-size:8pt;"
            elif index==1:
                text="의미 보존 · 문장 구조 유지 · Signal/기능/ECU 식별자 별칭 · 값/시간/단위 유지"
                style="color:#155c75; background:#eaf7fb; border:1px solid #9ccfdf; border-radius:4px; padding:5px; font-size:8pt;"
            else:
                text="주의 · 승인된 경우에만 TC 원문과 실제 Signal명 포함"
                style="color:#8a4b00; background:#fff5df; border:1px solid #e7c88b; border-radius:4px; padding:5px; font-size:8pt;"
            self.ai_transmission_notice.setText(text); self.ai_transmission_notice.setStyleSheet(style)

    def reset_tc_generation_light_aliases(self):
            self.tc_generation_light_alias_map = {}
            self.tc_generation_light_reverse_map = {}

    def _light_alias_suffix(self, token):
            digest = hashlib.sha256(("VA_LIGHT_MASK_V1|" + str(token)).encode("utf-8")).hexdigest().upper()
            letters = "ABCDEFGHJKLMNPQRSTUVWXYZ"
            return f"_{letters[int(digest[:2],16)%len(letters)]}{int(digest[2:4],16)%10}"

    def apply_tc_generation_light_mask(self, text):
            if not text or not hasattr(self, "tc_generation_signal_mode"):
                return str(text or "")
            mode = self.tc_generation_signal_mode.currentIndex()
            self.reset_tc_generation_light_aliases()
            if mode == 2:
                return str(text)
            pattern = re.compile(r"\b[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+\b")
            protected = {"PASS_FAIL","JSON_OUTPUT","NOT_EVALUATED","TC_GENERATION"}
            def repl(match):
                token=match.group(0)
                if token.upper() in protected or re.search(r"_[A-Z][0-9]$",token): return token
                alias=(f"SIG_{len(self.tc_generation_light_alias_map)+1:03d}" if mode==1 else token+self._light_alias_suffix(token))
                self.tc_generation_light_alias_map[token]=alias
                self.tc_generation_light_reverse_map[alias]=token
                return alias
            return pattern.sub(repl,str(text))

    def restore_tc_generation_light_aliases(self,text):
            restored=str(text or "")
            for alias,original in sorted(getattr(self,"tc_generation_light_reverse_map",{}).items(),key=lambda x:len(x[0]),reverse=True):
                restored=re.sub(rf"\b{re.escape(alias)}\b",original,restored)
            return restored

    def update_tc_generation_signal_notice(self,*_args):
            if not hasattr(self,"tc_generation_signal_notice"): return
            messages=[
                "원본명에 고정 코드를 추가합니다. 완전한 익명화는 아닙니다.",
                "기술 식별자를 SIG_001 형식으로 바꿉니다. 의미 이해가 낮아질 수 있습니다.",
                "사내 AI 입력 승인을 확인한 경우에만 원본을 유지하세요.",
            ]
            self.tc_generation_signal_notice.setText(messages[self.tc_generation_signal_mode.currentIndex()])

    def get_blf_summary_for_prompt(self):
            if self.is_safe_summary_mode():
                return json.dumps(
                    self.build_secure_blf_summary(),
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            if not self.blf_summary_data:
                return "BLF 요약 없음"
            level=self.prompt_level.currentText(); event_limits={"Basic":15,"Detailed":25,"Expert":40}; session_limits={"Basic":6,"Detailed":12,"Expert":20}
            tp=self.blf_summary_data.get("transport_protocol_summary",{}); sessions=tp.get("sessions",[]); stats=self.blf_summary_data.get("statistics",{}); source=self.blf_summary_data.get("source",{})
            compact={"source":{"blf_file":source.get("blf_file",""),"raw_file_sent_to_ai":False},"analysis_window":self.blf_summary_data.get("analysis_window",{}),"parse_quality":{"selected_messages":stats.get("selected_messages",0),"decoded_messages":stats.get("decoded_messages",0),"decode_errors":stats.get("decode_errors",0)},"important_findings":self.blf_summary_data.get("important_findings",[])[:10],"key_timeline":self.blf_summary_data.get("key_timeline",[])[:event_limits.get(level,25)],"transport_protocol_summary":{"mode":tp.get("mode","Off"),"sessions":sessions[:session_limits.get(level,12)]}}
            summary=json.dumps(compact,ensure_ascii=False,separators=(",",":"))
            if self.is_semantic_preserve_mode(): self._ensure_semantic_signal_aliases()
            if self.is_semantic_preserve_mode() or self.anonymize_signals_for_ai.isChecked():
                for signal,alias_name in self.preferred_signal_aliases.items():
                    summary=summary.replace(signal,alias_name)
            return summary

    def get_domain_prompt_values(self):
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

    def generate_tc_creation_prompt(
            self,
            feature_name,
            requirement,
            expected_behavior,
            level
        ):
            if level == "Basic":
                generation_instruction = self.clean_prompt_block("""
                    [Generation Scope]
    
                    다음 범위에서 핵심 테스트 케이스를 생성하라.
    
                    - 정상 시나리오
                    - 기본 실패 시나리오
                    - 핵심 상태 전이
    
                    각 테스트 케이스는 다음 항목을 포함한다.
    
                    - TC ID
                    - TC Name
                    - Purpose
                    - Preconditions
                    - Test Steps
                    - Expected Result
    
                    [Generation Scope - Basic Level]
                    - 정상 시나리오, 기본 실패 시나리오, 핵심 상태 전이 위주로 생성하라.
                """)
    
            elif level == "Detailed":
                generation_instruction = self.clean_prompt_block("""
                    [Generation Scope]
                    
                    요구사항을 분석하여 정상, 비정상, 경계 조건을 포함한
                    테스트 케이스를 생성하라.
                    
                    반드시 다음 테스트 관점을 포함한다.
                    
                    - Positive Scenario
                    - Negative Scenario
                    - Boundary Condition
                    - State Transition
                    - Timeout
                    - Retry
                    - Recovery
                    - User Interaction
                    - Domain-specific environment dependency
                    
                    각 테스트 케이스는 다음 항목을 포함한다.
                    
                    - TC ID
                    - TC Name
                    - Category
                    - Priority
                    - Purpose
                    - Preconditions
                    - Test Data
                    - Test Steps
                    - Expected Result
                    - Pass Criteria
                    
                    [Generation Scope - Detailed Level]
                    - Positive, Negative, Boundary, State Transition, Timeout, Retry, Recovery 및 선택 Domain 전용 시나리오를 포함하라.
                """)
    
            else:
                generation_instruction = self.clean_prompt_block("""
                    [Requirement Analysis Method]
    
                    다음 절차에 따라 요구사항을 분석하라.
    
                    1. 요구사항을 검증 가능한 조건으로 분해
                    2. 주요 시스템 상태와 상태 전이 식별
                    3. 입력값과 출력값 식별
                    4. 의존 시스템 및 통신 인터페이스 식별
                    5. 정상, 비정상, 경계 조건 식별
                    6. Timeout, Retry, Recovery 조건 식별
                    7. Safety 및 Security 관련 위험 식별
                    8. 요구사항 추적성과 테스트 커버리지 검토
    
                    [Test Design Techniques]
    
                    다음 테스트 설계 기법을 적용하라.
    
                    - Equivalence Partitioning
                    - Boundary Value Analysis
                    - State Transition Testing
                    - Decision Table Testing
                    - Error Guessing
                    - Negative Testing
                    - Recovery Testing
                    - Timing and Timeout Testing
                    - Power Cycle Testing
                    - Communication Loss Testing
                    - Repeated Operation Testing
    
                    각 테스트 케이스는 다음 항목을 포함한다.
    
                    - TC ID
                    - Requirement ID
                    - TC Name
                    - Category
                    - Priority
                    - Test Objective
                    - Preconditions
                    - Test Environment
                    - Test Data
                    - Test Steps
                    - Expected Result
                    - Pass Criteria
                    - Cleanup / Recovery
                    - Traceability
                    - Automation Candidate
                    
                    [Generation Scope - Expert Level]
                    - 요구사항 분해 및 테스트 설계 기법(Boundary Value, State Transition, Decision Table, Error Guessing, Recovery 등)을 선택 Domain에 맞게 적용하라.
                """)
    
            generation_template = self.clean_prompt_block("""
                너는 __DOMAIN_ROLE__이다.
                다음 분야별 검증 기준을 적용하라.
                __DOMAIN_RULES__
    
                아래 입력 정보를 기반으로
                실행 가능하고 측정 가능한 Test Case를 생성하라.
    
                [Input Information]
    
                Feature / Function:
                __FEATURE_NAME__
    
                Requirement / System Behavior:
                __REQUIREMENT__
    
                Target Behavior / Acceptance Criteria:
                __EXPECTED_BEHAVIOR__
    
                Prompt Level:
                __LEVEL__
    
                [Generation Rules]
    
                - 하나의 테스트 케이스는 하나의 주요 검증 목적을 가져야 한다.
                - [Mandatory Test Execution Sequence]가 있으면 작성된 순서를 생략하거나 변경하지 않는다.
                - Door Open, Door Close, Lock, Unlock, Key 이동 등 물리적 조작을 각각 독립된 Step으로 작성한다.
                - 물리적 조작과 Signal 확인을 하나의 Step에 혼합하지 않는다.
                - 동일 Signal을 여러 번 확인할 때는 초기값 확인과 상태 전이 확인을 구분한다.
                - Signal 확인 Step에는 확인 시점과 기대 전이(예: Locked에서 Unlocked)를 명확히 작성한다.
                - [Signals and Observation Checkpoints]의 항목을 관련 수행 Step 뒤에 배치한다.
                - 각 Test Step에는 대응되는 Expected Result가 있어야 한다.
                - 결과는 관찰하거나 측정할 수 있어야 한다.
                - 모호한 표현을 사용하지 않는다.
                - 정상 시나리오뿐만 아니라 실패 및 복구 시나리오를 포함한다.
                - 중복되는 테스트 케이스는 통합한다.
                - 입력 정보에 없는 사양을 임의로 확정하지 않는다.
                - 정보가 부족한 항목은 Assumption 또는 TBD로 표시한다.
                - 테스트 케이스 ID는 TC_GEN_001 형식으로 생성한다.
                - 결과는 한국어로 작성한다.
                - 차량 및 통신 전문 용어는 필요한 경우 영문을 병기한다.
    
                [Generation and Self-Review Process]
    
                다음 작업을 내부적으로 순서대로 수행하라.
    
                1. 입력된 요구사항을 검증 가능한 조건으로 분해한다.
                2. 요구사항을 기준으로 테스트케이스 초안을 생성한다.
                3. 생성된 테스트케이스 전체를 다시 검토한다.
                4. 테스트 목적과 조건이 동일한 중복 TC를 제거하거나 통합한다.
                5. Positive, Negative, Boundary 시나리오의 누락 여부를 확인한다.
                6. 필요한 State Transition, Timeout, Retry 및 Recovery 조건을 확인한다.
                7. 각 Precondition이 실제 수행 가능한 조건인지 확인한다.
                8. 각 Test Step이 실행 순서대로 명확하게 작성되었는지 확인한다.
                9. Test Step 하나에 여러 동작이 혼합되어 있으면 분리한다.
                10. Expected Result가 관찰하거나 측정 가능한지 확인한다.
                11. Expected Result에 모호한 표현이 있으면 구체적으로 수정한다.
                12. risk와 risk_description이 서로 일치하는지 확인한다.
                13. 입력 요구사항에 없는 수치, 거리, 시간 및 시스템 동작을 임의로 확정하지 않는다.
                14. 확인할 수 없는 사양은 TBD 또는 UNKNOWN으로 표시한다.
                15. 자체 검토에서 문제가 발견된 테스트케이스는 수정한다.
                16. 검토 과정과 초안은 출력하지 않는다.
                17. 자체 검토가 완료된 최종 JSON Object만 출력한다.
    
                [Self-Review Quality Checklist]
    
                최종 출력 전에 내부적으로 다음 항목을 확인하라.
    
                - 모든 TC에 tc_id가 있는가?
                - 모든 TC에 category가 있는가?
                - 모든 TC에 title이 있는가?
                - 모든 TC의 preconditions가 비어 있지 않은 JSON 배열인가?
                - 모든 TC의 steps가 비어 있지 않은 JSON 배열인가?
                - 모든 TC의 expected_results가 비어 있지 않은 JSON 배열인가?
                - steps와 expected_results의 항목 수가 정확히 일치하는가?
                - 모든 TC의 risk가 허용된 값인가?
                - 모든 TC의 risk_description이 구체적인 영향으로 작성되었는가?
                - 동일하거나 실질적으로 같은 TC가 중복되지 않았는가?
                - 요구사항에 없는 사양을 임의로 만들지 않았는가?
    
                위 체크 결과는 출력하지 말고 최종 JSON에만 반영하라.
    
                __GENERATION_INSTRUCTION__
    
                [Output Format Instructions]
    
                반드시 유효한 단일 JSON Object만 출력하라.
                JSON 앞뒤에 일반 설명문을 작성하지 마라.
                결과 전체를 하나의 ```json 코드 블록 안에 출력하라.
                사용자가 AI 화면의 Copy 버튼으로 즉시 복사할 수 있도록 JSON을 여러 줄로 보기 좋게 들여쓰기하라.
                코드 블록 밖에는 제목, 설명, 안내 문구를 절대 작성하지 마라.
                Requirement Analysis, Assumptions, Coverage Summary 등의
                일반 텍스트를 별도로 출력하지 마라.
    
                아래 JSON 구조와 필드명을 정확히 사용하라.
    
                {
                    "test_cases": [
                        {
                            "tc_id": "TC_GEN_001",
                            "category": "Positive",
                            "title": "테스트 시나리오명",
                            "preconditions": [
                                "첫 번째 사전 조건",
                                "두 번째 사전 조건"
                            ],
                            "steps": [
                                "첫 번째 실행 절차",
                                "두 번째 실행 절차"
                            ],
                            "expected_results": [
                                "첫 번째 Step에 대응하는 기대 결과",
                                "두 번째 Step에 대응하는 기대 결과"
                            ],
                            "risk": "HIGH",
                            "risk_description": "해당 TC 실패 시 발생 가능한 구체적인 기능 또는 서비스 영향"
                        }
                    ]
                }
    
                [JSON Output Rules]
    
                - test_cases에는 하나 이상의 테스트 케이스를 작성한다.
                - tc_id는 TC_GEN_001 형식으로 작성한다.
                - preconditions는 반드시 JSON 배열로 작성하고 1부터 순서대로 번호를 붙인다.
                - steps는 반드시 JSON 배열로 작성하고 1부터 순서대로 번호를 붙인다.
                - 각 steps 항목은 하나의 실행 동작만 포함한다.
                - expected_results는 반드시 JSON 배열로 작성한다.
                - expected_results 항목 수는 steps 항목 수와 정확히 같아야 한다.
                - expected_results의 각 번호는 같은 번호의 step에 대응해야 한다.
                - expected_results는 관찰하거나 측정할 수 있게 작성한다.
                - risk는 HIGH, MEDIUM, LOW, UNKNOWN 중 하나만 작성한다.
                - risk_description은 빈 문자열로 작성하지 않는다.
                - risk_description에는 해당 테스트 실패 시 발생 가능한 영향을 작성한다.
                - 입력에서 확인할 수 없는 값은 임의로 확정하지 않는다.
                - JSON 문자열 안에 주석을 작성하지 않는다.
                - trailing comma, None, NaN을 사용하지 않는다.
                - 마지막 닫는 중괄호 뒤에는 JSON 코드 블록을 닫는 ```만 작성한다.
                - JSON을 한 줄로 압축하지 말고, 객체와 배열을 여러 줄로 들여쓰기한다.
                - AI 채팅 화면에서 코드 블록의 Copy 버튼으로 전체 결과를 한 번에 복사할 수 있어야 한다.
            """)
    
            self.generated_prompt = (
                generation_template
                .replace("__FEATURE_NAME__", feature_name)
                .replace("__REQUIREMENT__", requirement)
                .replace("__EXPECTED_BEHAVIOR__", expected_behavior)
                .replace("__LEVEL__", level)
                .replace("__GENERATION_INSTRUCTION__", generation_instruction)
            )

    def build_generated_tc_review_prompt(self, generated_data):
            """TC Generation JSON을 동일 Domain 기준으로 자체 검토하는 2차 Review Prompt를 만든다."""
            profile = self.current_domain_profile()
            role = profile.get("role", "Software Quality Assurance Specialist")
            review_rules = "\n".join(
                f"- {rule}" for rule in profile.get("review_rules", [])
            )
            generated_json = json.dumps(generated_data, ensure_ascii=False, indent=2)
            return self.clean_prompt_block(f"""
                너는 {role}이다.
                방금 생성된 Test Case 전체를 독립적인 Reviewer 관점에서 다시 검토하라.
    
                [Domain Review Rules]
                {review_rules}
    
                [Generated Test Cases]
                {generated_json}
    
                [Review Rules]
                - 생성된 모든 TC를 하나씩 검토한다.
                - 요구사항과 직접 연결되지 않는 TC를 식별한다.
                - 중복되거나 실질적으로 같은 TC를 식별한다.
                - Preconditions가 실행 가능하고 빠짐없이 정의됐는지 확인한다.
                - Steps와 Expected Results의 항목 수가 정확히 같은지 확인한다.
                - 각 Step과 같은 번호의 Expected Result가 1:1로 대응하는지 확인한다.
                - 각 Step에는 하나의 실행 동작만 포함되어야 한다.
                - Expected Result는 관찰하거나 측정할 수 있어야 한다.
                - 정상, 실패, 경계, 상태 전이, Timeout, Recovery 시나리오의 누락을 확인한다.
                - 입력 요구사항에 없는 수치나 동작을 임의로 만든 부분을 식별한다.
                - 문제가 있는 TC는 revised_preconditions, revised_steps, revised_expected_results에 수정안을 작성한다.
                - 문제가 없는 TC도 review_result를 PASS로 명시한다.
                - 검토 과정의 설명은 출력하지 않는다.
    
                [Output Format]
                결과 전체를 하나의 ```json 코드 블록 안에 출력한다.
                코드 블록 밖에는 어떠한 설명도 작성하지 않는다.
                아래 구조와 필드명을 정확히 사용한다.
    
                {{
                  "review_summary": {{
                    "total_count": 0,
                    "pass_count": 0,
                    "needs_improvement_count": 0,
                    "overall_comment": ""
                  }},
                  "reviewed_test_cases": [
                    {{
                      "tc_id": "TC_GEN_001",
                      "original_title": "",
                      "review_result": "PASS | NEEDS_IMPROVEMENT | FAIL",
                      "score": 0,
                      "issues": [],
                      "missing_conditions": [],
                      "recommendations": [],
                      "revised_preconditions": [],
                      "revised_steps": [],
                      "revised_expected_results": [],
                      "risk": "HIGH | MEDIUM | LOW | UNKNOWN"
                    }}
                  ]
                }}
    
                [Final Check]
                - reviewed_test_cases 개수는 입력 test_cases 개수와 같아야 한다.
                - score는 0부터 100 사이의 정수로 작성한다.
                - 배열은 내용이 없으면 []로 작성한다.
                - 유효한 JSON 문법을 사용한다.
            """)

    def prepare_generated_tc_auto_review(self, generated_data, show_message=True):
            """생성 결과를 Review Prompt로 변환하고 Preview와 클립보드에 준비한다."""
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

    def normalize_prompt_spacing(self, text):
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

    def optimize_prompt_text(self, text):
            """코드 블록은 유지하고 중복 문장, 중복 섹션, 과도한 앞 공백을 제거한다."""
            if not text:
                return ""
            text=textwrap.dedent(text).replace("\t","    ")
            output=[]; in_code=False; previous_blank=False; seen_lines=set(); seen_sections=set()
            repeatable_prefixes=("- ","1. ","2. ","3. ","4. ","5. ")
            for raw in text.splitlines():
                line=raw.rstrip(); stripped=line.strip()
                if stripped.startswith("```"):
                    in_code=not in_code; output.append(stripped); previous_blank=False; continue
                if in_code:
                    output.append(line); previous_blank=False; continue
                if not stripped:
                    if output and not previous_blank: output.append("")
                    previous_blank=True; continue
                if stripped.startswith("[") and stripped.endswith("]"):
                    section_key=stripped.lower()
                    if section_key in seen_sections:
                        continue
                    seen_sections.add(section_key)
                normalized=re.sub(r"\s+"," ",stripped).lower()
                if normalized in seen_lines and not stripped.startswith(repeatable_prefixes):
                    continue
                seen_lines.add(normalized)
                output.append(line.lstrip()); previous_blank=False
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

    def clean_prompt_block(self, text):
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
            if "Validation Analysis" in self.mode.currentText() or "TC Review" in self.mode.currentText():
                self.sync_structured_validation_to_legacy_fields()
            tc = self.tc.text().strip()
            purpose = self.purpose.toPlainText().strip()
            expected = self.expected.toPlainText().strip()
            if "Validation Analysis" in self.mode.currentText() and hasattr(self,"validation_preconditions"):
                pre=self.validation_preconditions.toPlainText().strip()
                steps=self.validation_steps.toPlainText().strip()
                expected_result=self.validation_expected_results.toPlainText().strip()
                actual_result=self.validation_actual_results.toPlainText().strip()
                blocks=[]
                if pre: blocks.append("[Preconditions]\n"+pre)
                if steps: blocks.append("[Test Steps]\n"+steps)
                if expected_result: blocks.append("[Expected Results]\n"+expected_result)
                purpose="\n\n".join(blocks)
                expected=actual_result
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
    
            # 보안 기본 모드에서는 로컬 입력 원문을 Prompt 변수에 절대 넣지 않는다.
            # 화면/저장 데이터는 유지되고, 전송용 Prompt 복사본만 최소화한다.
            if "Validation Analysis" in mode and self.is_safe_summary_mode():
                tc = "LOCAL_TC_REFERENCE_OMITTED"
                purpose = (
                    "TC 원문은 보안 정책 확인 전이므로 제공하지 않음. "
                    "Precondition, Steps, Expected Results는 로컬 프로그램에만 보관됨."
                )
                local_rules=self.extract_tc_blf_validation_rules()
                selected_signals=list(getattr(self,"tc_related_parse_signals",[]) or [])
                expected = (
                    "Actual Result 원문은 제공하지 않음. "
                    f"로컬 Expected 조건 {len(local_rules)}개가 TC-BLF 비교에 적용됨. "
                    f"선택 분석 Signal: {', '.join(selected_signals) if selected_signals else '미확정'}"
                )
                analysis_question = (
                    "제공된 익명화 BLF 로컬 요약만 분석한다. 상태 전이, 지연, 오류, "
                    "미완료 통신을 관찰 사실로 정리하고, TC 기대값이 없으므로 PASS/FAIL과 Root Cause를 확정하지 않는다."
                )
    
            elif "Validation Analysis" in mode and self.is_semantic_preserve_mode():
                semantic_context, semantic_aliases=self.build_semantic_preserved_tc_context()
                tc_hash=hashlib.sha256(tc.encode("utf-8")).hexdigest()[:10].upper()
                tc=f"LOCAL_TC_{tc_hash}"
                purpose=semantic_context
                actual_widget=getattr(self,"validation_actual_results",None)
                actual_text=actual_widget.toPlainText().strip() if isinstance(actual_widget,QTextEdit) else expected
                expected=self._semantic_rewrite_line(actual_text,semantic_aliases) or "관찰 결과 정보 없음"
                analysis_question=(
                    "의미 보존 변환된 Preconditions, Actions, Expected Behavior와 Actual Observation을 비교한다. "
                    "SIG_### 별칭의 값, 상태 전이, 순서, 시간 제한 및 유지 조건을 보존하여 판정하고, "
                    "근거가 부족하면 PASS/FAIL을 확정하지 않는다."
                )
    
            # =================================================
            # 1. Validation Analysis
            # =================================================
            if "Validation Analysis" in mode:
                if level == "Basic":
                    extra_section = self.clean_prompt_block("""
                        [Summary]
    
                        [PASS / FAIL]
    
                        [JSON OUTPUT]
    
                        일반 텍스트 설명은 출력하지 마라.
                        아래 JSON 형식으로만 출력하라.
    
                        {
                        "result": "PASS | FAIL | PARTIAL | INCONCLUSIVE | EVIDENCE INSUFFICIENT",
                        "summary": "핵심 결과 요약",
                        "pass_factors": [],
                        "fail_factors": [],
                        "evidence_status": "SUFFICIENT | INSUFFICIENT | PARTIAL | UNKNOWN"
                        }
    
                        JSON은 반드시 분석 결과의 마지막 부분에 출력한다.
                        JSON 앞뒤에 일반적인 분석 내용을 작성하지 않는다.
                        JSON은 유효한 JSON 문법을 사용한다.
                        result에는 위 선택지 중 하나만 실제 판정값으로 입력하라.
                        선택지 문자열 전체를 그대로 넣지 않는다.
                    """)
    
                elif level == "Detailed":
                    extra_section = self.clean_prompt_block("""
                        [Executive Summary]
    
                        [Confidence Assessment]
    
                        [Risk Analysis]
    
                        [Observations]
    
                        [Test Gap Analysis]
    
                        [Recommended Verification]
    
                        [JSON OUTPUT]
    
                        일반 텍스트 설명은 출력하지 마라.
                        분석 결과를 아래 JSON 형식으로만 출력하라.
    
                        {
                        "result": "PASS | FAIL | PARTIAL | INCONCLUSIVE | EVIDENCE INSUFFICIENT",
                        "confidence": "HIGH | MEDIUM | LOW | UNKNOWN",
                        "confidence_reason": [],
                        "risk": "HIGH | MEDIUM | LOW | UNKNOWN",
                        "summary": "핵심 결과 요약",
                        "evidence_status": "SUFFICIENT | INSUFFICIENT | PARTIAL | UNKNOWN",
                        "pass_factors": [],
                        "fail_factors": [],
                        "evidence_coverage": {
                            "required_items": 0,
                            "verified_items": 0,
                            "coverage_percent": 0,
                            "missing_items": []
                        },
                        "observations": [],
                        "gaps": [],
                        "recommended_verification": []
                        }
    
                        JSON은 응답의 마지막 부분에 위치시킨다.
                        JSON 밖에 일반 텍스트를 작성하지 않는다.
                        JSON은 유효한 JSON 문법을 사용한다.
                        enum 값에는 선택지 전체가 아니라 실제 값 하나만 작성한다.
                        선택지 문자열 전체를 그대로 넣지 않는다.
                    """)
    
                else:
                    extra_section = self.clean_prompt_block("""
                        [Executive Summary]
    
                        [Event Timeline]
    
                        [Validation Result]
    
                        [Confidence & Risk Analysis]
    
                        [Coverage Assessment]
    
                        [Test Gap Analysis]
    
                        [Potential Root Cause]
    
                        [Recommended Verification]
    
                        [Next Actions]
    
                        [JSON OUTPUT]
    
                        일반 텍스트 설명은 출력하지 마라.
                        분석 결과는 JSON Object 하나로만 출력하라.
    
                        JSON 형식:
    
                        {
                        "result": "PASS | FAIL | PARTIAL | INCONCLUSIVE | EVIDENCE INSUFFICIENT",
                        "final_verdict": "REVIEW REQUIRED | PASS | FAIL | INCONCLUSIVE",
                        "confidence": "HIGH | MEDIUM | LOW | UNKNOWN",
                        "confidence_reason": [],
                        "risk": "HIGH | MEDIUM | LOW | UNKNOWN",
                        "severity": "CRITICAL | HIGH | MEDIUM | LOW | UNKNOWN",
                        "evidence_status": "SUFFICIENT | INSUFFICIENT | PARTIAL | UNKNOWN",
                        "requirement_id": "TBD",
                        "tc_id": "TBD",
                        "summary": "TBD",
                        "pass_factors": [],
                        "fail_factors": [],
                        "evidence_coverage": {
                            "required_items": 0,
                            "verified_items": 0,
                            "coverage_percent": 0,
                            "missing_items": []
                        },
                        "event_timeline": [],
                        "observations": [],
                        "root_cause": [],
                        "gaps": [],
                        "recommended_verification": [],
                        "next_actions": []
                        }            
    
                        중요한 출력 규칙:
                        1. JSON Object 하나만 출력한다.
                        2. JSON은 반드시 전체 응답의 마지막에 출력한다.
                        3. JSON 밖에 일반 텍스트를 작성하지 않는다.
                        4. JSON은 반드시 유효한 JSON 문법으로 작성한다.
                        5. JSON 코드 블록 뒤에는 어떠한 설명도 작성하지 않는다.
                        6. 이미지 또는 로그에서 직접 확인한 사실과 추론을 명확히 구분한다.
                        7. 확인되지 않은 정보는 "EVIDENCE INSUFFICIENT" 또는 "TBD"로 표시한다.
                        8. PASS Factors에는 증적에서 직접 확인된 만족 조건만 작성한다.
                        9. FAIL Factors에는 실패가 직접 확인된 조건과 판정에 필요한 증적이 누락된 조건을 작성한다.
                        10. Confidence Reason에는 Confidence 등급을 선택한 객관적인 근거를 작성한다.
                        11. Observations에는 이미지 또는 로그에서 직접 관찰한 사실만 작성한다.
                        12. Root Cause에는 사실이 아닌 추론 또는 가능한 원인을 작성한다.
                        13. Evidence Coverage는 Required Items와 Verified Items를 기준으로 작성한다.
                        14. coverage_percent는 다음 계산식을 사용한다: round(verified_items / required_items * 100)
                        15. required_items가 0이면 coverage_percent는 0으로 작성한다.
                        16. 선택지 전체(예: "PASS | FAIL ...")를 결과값으로 그대로 넣지 않고 실제 판정값 하나만 입력한다.
                        17. JSON 문자열에는 주석, trailing comma, NaN, None을 사용하지 않는다.
                        18. JSON에 포함할 정보가 없으면 문자열은 "TBD", 배열은 [], 객체는 기본 구조로 작성한다.
                    """)
    
                validation_template = self.clean_prompt_block("""
                    너는 __DOMAIN_ROLE__이다.
                    다음 분야별 분석 기준을 적용하라.
                    __DOMAIN_RULES__
    
                    아래 TC 정보와 제공된 Evidence를 기반으로
                    검증 결과를 분석하라.
    
                    [Validation Information]
    
                    TC Name:
                    __TC_NAME__
    
                    TC Information:
                    __PURPOSE__
    
                    Actual Result / Issue:
                    __EXPECTED__
    
                    Selected Analysis Purpose:
                    __ANALYSIS_PURPOSE__
    
                    User Analysis Question:
                    __ANALYSIS_QUESTION__
    
                    [Evidence Summary]
                    __DOMAIN_EVIDENCE__
    
                    [Input Guide]
    
                    TC Information에는 다음 내용이 포함될 수 있다.
                    - Precondition
                    - Test Steps
                    - Expected Result
    
                    Actual Result / Issue에는 다음 내용이 포함될 수 있다.
                    - 문제가 발생한 Step
                    - 실제 관찰 결과
                    - 화면에 표시된 오류 문구
                    - 재현 횟수
    
                    원본 화면이나 로그가 없을 수 있다.
                    사용자가 작성한 관찰 내용만 확인된 사실로 취급하라.
                    확인하지 못한 원인은 가능한 원인 후보로만 작성하라.
                    정보가 부족하면 INCONCLUSIVE로 판단하라.
    
                    [Attached Evidence]
    
                    [[EVIDENCE_PREVIEW]]
    
                    [Evidence Reference Rules]
    
                    - 이 대화의 첫 번째 요청에 첨부된 모든 이미지를 기본 Validation Evidence로 사용하라.
                    - 이후 같은 대화에서 수행되는 후속 분석에서도 앞서 첨부된 이미지를 계속 참조하라.
                    - 새로운 이미지가 추가되면 기존 이미지와 함께 분석하라.
                    - 이미지에서 직접 확인한 사실과 분석에 따른 추론을 구분하라.
                    - 이미지에서 확인할 수 없는 정보는 임의로 확정하지 말고 "Evidence Insufficient"로 표시하라.
    
                    [Analysis Rules]
    
                    - 입력된 TC 목적과 기대 결과를 기준으로 분석한다.
                    - 확인되지 않은 내용을 사실로 단정하지 않는다.
                    - 증적이 부족한 경우 Evidence Insufficient로 표시한다.
                    - PASS 또는 FAIL 판단 근거를 명확히 작성한다.
                    - 실제 결과와 기대 결과의 차이를 설명한다.
                    - 추가 검증이 필요한 경우 구체적인 확인 방법을 제안한다.
                    - Selected Analysis Purpose와 User Analysis Question을 분석의 중심으로 삼는다.
                    - Evidence Summary가 있으면 확인된 이벤트, 요청, 응답 및 상태 변화를 근거로 활용한다.
                    - Domain Evidence에서 정의되지 않은 데이터의 의미를 임의로 추정하지 않는다.
                    - 구조화되거나 명확히 해석된 Evidence만 직접 근거로 사용한다.
                    - Evidence가 일부 범위로 제한되었으면 원인 확정의 한계로 명시한다.
                    - 제공되지 않은 사실을 만들거나 Root Cause를 확정하지 않는다.
                    - 질문이 비어 있으면 가능한 원인과 다음 확인 항목을 기본 분석 목표로 삼는다.
                    - recommended_verification은 "확인 대상 / 확인 방법 / 예상 판단"이 드러나게 실행 순서대로 작성한다.
                    - Basic은 핵심 판정, 문제 Step, 가능한 원인, 다음 확인 항목 위주로 간결하게 작성한다.
                    - Detailed와 Expert는 추가 근거와 분류를 포함하되 같은 내용을 반복하지 않는다.
                    - 결과는 한국어로 작성한다.
    
                    __EXTRA_SECTION__
                """).strip()
    
                self.generated_prompt = (
                    validation_template
                    .replace("__TC_NAME__", tc)
                    .replace("__PURPOSE__", purpose)
                    .replace("__EXPECTED__", expected)
                    .replace(
                        "__ANALYSIS_PURPOSE__",
                        self.analysis_purpose.currentText()
                        if hasattr(self, "analysis_purpose")
                        else "전체 분석"
                    )
                    .replace(
                        "__ANALYSIS_QUESTION__",
                        analysis_question or (
                            "Actual Result가 예상과 다르게 나온 가능한 이유와 "
                            "다음 확인 항목을 순서대로 제시하라."
                        )
                    )
                    .replace("__BLF_SUMMARY__", self.get_blf_summary_for_prompt())
                    .replace("__EXTRA_SECTION__", extra_section)
                )
    
            # =================================================
            # 2. TC Review
            # =================================================
            elif "TC Review" in mode:
                if level == "Basic":
                    review_section = self.clean_prompt_block("""
                        [Review Summary]
                        [Key Issues]
    
                        [Conclusion]
                    """)
    
                elif level == "Detailed":
                    review_section = self.clean_prompt_block("""
                        [Review Summary]
    
                        [Coverage Assessment]
    
                        [Potential Gaps]
    
                        [Risk Scenarios]
    
                        [Recommended Test Cases]
    
                        [Conclusion]
                    """)
    
                else:
                    review_section = self.clean_prompt_block("""
                        [Review Summary]
    
                        [Coverage Assessment]
    
                        [Test Coverage Matrix]
    
                        [Boundary Conditions]
    
                        [Negative Scenarios]
    
                        [Potential Gaps]
    
                        [Missing Validation Cases]
    
                        [Recommended Additional Test Cases]
    
                        [Risk Assessment]
    
                        [Conclusion]
                    """)
    
                review_template = self.clean_prompt_block("""
                    너는 __DOMAIN_ROLE__이다.
                    다음 분야별 리뷰 기준을 적용하라.
                    __DOMAIN_RULES__
    
                    아래 Test Case를 평가하고,
                    명확성, 실행 가능성, 검증 범위 및 누락 시나리오를 검토하라.
    
                    [TC Information]
    
                    TC Name:
                    __TC_NAME__
    
                    Purpose:
                    __PURPOSE__
    
                    Expected Result:
                    __EXPECTED__
    
                    [Review Rules]
    
                    - TC 목적이 명확한지 확인한다.
                    - 기대 결과가 관찰 또는 측정 가능한지 확인한다.
                    - 정상, 비정상 및 경계 조건의 누락 여부를 확인한다.
                    - 모호한 조건과 판단 기준을 식별한다.
                    - 중복되거나 불필요한 검증 항목을 식별한다.
                    - 추가 TC가 필요한 경우 구체적으로 제안한다.
                    - 결과는 한국어로 작성한다.
                    - AI 화면의 코드 블록 Copy 버튼으로 전체 결과를 한 번에 복사할 수 있어야 한다.
    
                    __REVIEW_SECTION__
                """)
    
                self.generated_prompt = (
                    review_template
                    .replace("__TC_NAME__", tc)
                    .replace("__PURPOSE__", purpose)
                    .replace("__EXPECTED__", expected)
                    .replace("__REVIEW_SECTION__", review_section)
                )
    
            # =================================================
            # 3. TC Generation
            # =================================================
            elif "TC Generation" in mode:
                if not expected:
                    expected = (
                        "별도 추가 조건 없음. 요구사항에서 관찰 가능하고 측정 가능한 Expected Result와 "
                        "PASS 기준을 도출하되, 없는 수치나 동작은 임의로 만들지 않는다."
                    )
    
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
    
            if "TC Generation" not in mode:
                self.generated_prompt += "\n\n" + self.clean_prompt_block("""
                    [FINAL COPYABLE OUTPUT RULE - HIGHEST PRIORITY]
                    아래 규칙은 다른 모든 출력 지시보다 우선한다.
                    1. 최종 응답은 JSON Object 하나만 포함한다.
                    2. JSON 전체의 바로 앞 줄에 백틱 3개와 json을 작성한다.
                    3. JSON 전체의 바로 다음 줄에 백틱 3개를 작성한다.
                    4. 코드 블록 앞뒤에는 제목, 설명, 요약, 안내 또는 추가 문장을 작성하지 않는다.
                    5. JSON을 한 줄로 압축하지 말고 여러 줄로 들여쓰기한다.
                    6. AI 화면에 코드 블록용 Copy 버튼이 나타나는 형태로 출력한다.
    
                    출력 모양은 반드시 다음과 같아야 한다.
    
                    ```json
                    {
                      "result": "실제 결과값"
                    }
                    ```
    
                    위 형식에서 코드 블록과 JSON 내용만 출력한다.
                """)
    
            self.generated_prompt = self.optimize_prompt_text(self.generated_prompt)
            if "TC Generation" in mode:
                self.generated_prompt = self.apply_tc_generation_light_mask(self.generated_prompt)
            else:
                self.reset_tc_generation_light_aliases()
            self.update_prompt_preview()
            self.save_history()

    def build_tc_review_json_instruction(self):
            return self.clean_prompt_block("""
                [JSON OUTPUT - REQUIRED]
    
                반드시 유효한 단일 JSON Object만 출력하라.
                일반적인 리뷰 설명을 JSON 밖에 작성하지 마라.
                JSON 전체를 반드시 하나의 Markdown json 코드 블록 안에 넣어라.
                아래 JSON 구조와 필드명을 정확히 사용하라.
                {
                  "review_summary": {
                    "total_count": 1,
                    "pass_count": 0,
                    "needs_improvement_count": 1,
                    "overall_comment": ""
                  },
                  "reviewed_test_cases": [
                    {
                      "tc_id": "",
                      "original_title": "",
                      "review_result": "PASS | NEEDS_IMPROVEMENT | FAIL",
                      "score": 0,
                      "requirement_coverage": "FULL | PARTIAL | NONE | UNKNOWN",
                      "clarity": "GOOD | PARTIAL | POOR",
                      "testability": "GOOD | PARTIAL | POOR",
                      "missing_conditions": [],
                      "issues": [],
                      "recommendations": [],
                      "revised_title": "",
                      "revised_precondition": "",
                      "revised_steps": [],
                      "revised_expected_result": "",
                      "risk": "HIGH | MEDIUM | LOW | UNKNOWN"
                    }
                  ]
                }
            """)

    def get_prompt_text_for_copy(self):
            if not self.generated_prompt:
                return ""
    
            if self.attachments:
                evidence_text = "\n".join(
                    f"Evidence {index}: {os.path.basename(file_path)}"
                    for index, file_path in enumerate(self.attachments, start=1)
                )
            else:
                evidence_text = "첨부된 이미지 없음"
    
            prompt_text = self.generated_prompt.replace(
                "[[EVIDENCE_PREVIEW]]",
                evidence_text
            )
    
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
                    "프롬프트가 아직 너무 깁니다.\n\n"
                    f"현재 길이: {len(prompt_text):,}자\n"
                    f"권장 최대: {MAX_PROMPT_CHARS:,}자\n\n"
                    "Start/End 구간을 줄이거나 Signal Filter를 더 구체적으로 설정하고 "
                    "AI Event Limit을 낮춘 뒤 다시 Parse BLF Locally를 실행하세요."
                )
                return
            QApplication.clipboard().setText(prompt_text)
    
            if self.attachments:
                message = (
                    "Prompt 텍스트가 복사되었습니다.\n\n"
                    "1. 원하는 AI를 선택하여 입력창에서 Ctrl+V로 Prompt를 붙여넣으세요.\n\n"
                    "2. 앱의 Copy Evidence Files 버튼을 누르세요.\n\n"
                    "3. 원하는 AI에 접속하여 다시 Ctrl+V를 눌러 이미지를 첨부하세요.\n\n"
                    f"등록된 Evidence: {len(self.attachments)}개"
                )
            else:
                message = (
                    "Prompt 텍스트가 복사되었습니다.\n\n"
                    "원하는 AI에 접속하여 Ctrl+V를 누르세요.\n\n"
                    "현재 등록된 Evidence 이미지는 없습니다."
                )
    
            QMessageBox.information(self, "Ready", message)

    def build_gemini_json_instruction(self):
            """Gemini API 전용 표준 JSON 스키마 지시사항 생성."""
            common_rules = """
                [Gemini API Output Rules]
                - 응답은 Markdown이나 설명 없이 오직 유효한 단일 JSON Object만 반환하라.
                - 모든 설명 문구는 한국어로 작성한다.
                - result에는 "PASS", "FAIL", "PARTIAL", "INCONCLUSIVE", "EVIDENCE INSUFFICIENT" 중 하나의 실제 값만 작성한다.
                - evidence_status에는 "SUFFICIENT", "INSUFFICIENT", "PARTIAL", "UNKNOWN" 중 하나의 실제 값만 작성한다.
                - 선택지 전체 문자열(예: "PASS | FAIL | ...")을 결과값으로 그대로 넣지 마라.
                - 증적에서 직접 확인하지 못한 사실은 추정하지 말고, 배열은 [] 또는 값은 "TBD"로 작성하라.
            """
    
            level = self.prompt_level.currentText()
    
            if level == "Basic":
                fields = """
                    [Required JSON Schema - Basic Level]
                    {
                        "result": "PASS | FAIL | PARTIAL | INCONCLUSIVE | EVIDENCE INSUFFICIENT",
                        "summary": "핵심 결과 요약",
                        "pass_factors": ["통과 요인 목록"],
                        "fail_factors": ["실패 요인 목록"],
                        "evidence_status": "SUFFICIENT | INSUFFICIENT | PARTIAL | UNKNOWN"
                    }
                """
            elif level == "Detailed":
                fields = """
                    [Required JSON Schema - Detailed Level]
                    {
                        "result": "PASS | FAIL | PARTIAL | INCONCLUSIVE | EVIDENCE INSUFFICIENT",
                        "confidence": "HIGH | MEDIUM | LOW | UNKNOWN",
                        "confidence_reason": ["이유 목록"],
                        "risk": "HIGH | MEDIUM | LOW | UNKNOWN",
                        "summary": "핵심 결과 요약",
                        "evidence_status": "SUFFICIENT | INSUFFICIENT | PARTIAL | UNKNOWN",
                        "pass_factors": ["통과 요인 목록"],
                        "fail_factors": ["실패 요인 목록"],
                        "evidence_coverage": {
                            "required_items": 0,
                            "verified_items": 0,
                            "coverage_percent": 0,
                            "missing_items": []
                        },
                        "observations": ["관찰 사실 목록"],
                        "gaps": ["검증 갭 목록"],
                        "recommended_verification": ["추천 검증 항목 목록"]
                    }
                """
            else:
                fields = """
                    [Required JSON Schema - Expert Level]
                    {
                        "result": "PASS | FAIL | PARTIAL | INCONCLUSIVE | EVIDENCE INSUFFICIENT",
                        "final_verdict": "REVIEW REQUIRED | PASS | FAIL | INCONCLUSIVE",
                        "confidence": "HIGH | MEDIUM | LOW | UNKNOWN",
                        "confidence_reason": ["이유 목록"],
                        "risk": "HIGH | MEDIUM | LOW | UNKNOWN",
                        "severity": "CRITICAL | HIGH | MEDIUM | LOW | UNKNOWN",
                        "evidence_status": "SUFFICIENT | INSUFFICIENT | PARTIAL | UNKNOWN",
                        "requirement_id": "요구사항 ID",
                        "tc_id": "테스트케이스 ID",
                        "summary": "핵심 결과 요약",
                        "pass_factors": ["통과 요인 목록"],
                        "fail_factors": ["실패 요인 목록"],
                        "evidence_coverage": {
                            "required_items": 0,
                            "verified_items": 0,
                            "coverage_percent": 0,
                            "missing_items": []
                        },
                        "observations": ["관찰 사실 목록"],
                        "root_cause": ["추단 원인 목록"],
                        "gaps": ["검증 갭 목록"],
                        "recommended_verification": ["추천 검증 항목 목록"],
                        "event_timeline": [
                            {
                                "order": 1,
                                "event": "이벤트명",
                                "status": "VERIFIED | PARTIAL | FAILED | MISSING | UNKNOWN",
                                "evidence": "증적 위치",
                                "timestamp": "시각",
                                "timestamp_type": "EVENT_TIME | OBSERVED_TIME | TBD"
                            }
                        ],
                        "next_actions": [
                            {
                                "priority": "CRITICAL | HIGH | MEDIUM | LOW | UNKNOWN",
                                "action": "조치 내용",
                                "owner": "담당자",
                                "status": "OPEN | IN_PROGRESS | BLOCKED | COMPLETED | CANCELLED | UNKNOWN"
                            }
                        ]
                    }
                """
    
            return self.clean_prompt_block(common_rules + "\n" + fields)

