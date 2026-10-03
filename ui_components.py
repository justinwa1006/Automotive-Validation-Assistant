from .core_runtime import *


class UiComponentsMixin:
    def _u_label(self, text, section=False):
            w = QLabel(text)
            w.setObjectName("uSection" if section else "uField")
            return w

    def _u_button(self, text, callback, primary=False):
            b = QPushButton(text)
            b.setObjectName("primaryButton" if primary else "secondaryButton")
            b.setMinimumHeight(34)
            b.clicked.connect(callback)
            b.clicked.connect(lambda _checked=False, button=b: self._u_animate_button_click(button))
            return b

    def _u_animate_button_click(self, button):
            try:
                effect=button.graphicsEffect()
                if not isinstance(effect,QGraphicsOpacityEffect):
                    effect=QGraphicsOpacityEffect(button); effect.setOpacity(1.0); button.setGraphicsEffect(effect)
                animation=QPropertyAnimation(effect,b'opacity',button); animation.setDuration(150); animation.setStartValue(0.68); animation.setEndValue(1.0); animation.setEasingCurve(QEasingCurve.OutCubic)
                if not hasattr(self,'_u_button_animation_refs'): self._u_button_animation_refs=[]
                self._u_button_animation_refs.append(animation)
                animation.finished.connect(lambda anim=animation: self._u_button_animation_refs.remove(anim) if anim in self._u_button_animation_refs else None)
                animation.start()
            except Exception:
                pass

    def _u_card(self):
            w=QWidget(); w.setObjectName("uCard")
            l=QVBoxLayout(w); l.setContentsMargins(12,10,12,10); l.setSpacing(7)
            return w,l

    def _u_row(self, widgets, stretches=None):
            w=QWidget(); l=QHBoxLayout(w); l.setContentsMargins(0,0,0,0); l.setSpacing(7)
            for i,child in enumerate(widgets): l.addWidget(child, stretches[i] if stretches else 1)
            return w

    def _u_bind_line(self, proxy, backend):
            proxy.setText(backend.text())
            proxy.textChanged.connect(lambda t: backend.setText(t) if backend.text()!=t else None)
            backend.textChanged.connect(lambda t: proxy.setText(t) if proxy.text()!=t else None)

    def _u_bind_text(self, proxy, backend):
            proxy.setPlainText(backend.toPlainText())
            proxy.textChanged.connect(lambda: backend.setPlainText(proxy.toPlainText()) if backend.toPlainText()!=proxy.toPlainText() else None)
            backend.textChanged.connect(lambda: proxy.setPlainText(backend.toPlainText()) if proxy.toPlainText()!=backend.toPlainText() else None)

    def _u_bind_combo(self, proxy, backend):
            proxy.addItems([backend.itemText(i) for i in range(backend.count())])
            proxy.setCurrentText(backend.currentText())
            proxy.currentTextChanged.connect(backend.setCurrentText)
            backend.currentTextChanged.connect(lambda t: proxy.setCurrentText(t) if proxy.currentText()!=t else None)

    def _u_sync_results(self):
            prompt=self.result.toPlainText(); ai=self.ai_result.toPlainText()
            if hasattr(self,'u_prompt') and self.u_prompt.toPlainText()!=prompt: self.u_prompt.setPlainText(prompt)
            for n in ('u_gen_result','u_review_result','u_val_result'):
                w=getattr(self,n,None)
                if w is not None and w.toPlainText()!=ai: w.setPlainText(ai)

    def _u_generate(self, mode):
            self.mode.setCurrentText(mode); self.Prompt_Generation(); QTimer.singleShot(30,self._u_sync_results)

    def _u_paste(self):
            self.paste_ai_result(); QTimer.singleShot(30,self._u_sync_current_mode_only)

    def _u_resource_count_text(self):
            domain=self.qa_domain.currentText()
            if domain=='Automotive CANoe':
                n=len(getattr(self,'dbc_file_paths',[]))
                return 'DBC: 미선택' if not n else (f'DBC: {os.path.basename(self.dbc_file_paths[0])}' if n==1 else f'DBC: {n}개')
            n=len(getattr(self,'domain_evidence_files',[]))
            return f'Resources: {n}개'

    def _u_manage_resources(self):
            domain=self.qa_domain.currentText()
            if domain=='Automotive CANoe':
                self.attach_dbc_file(); self._u_update_domain_resource_ui(); return
            d=QDialog(self); d.setWindowTitle(f'{domain} · Common Resources'); d.resize(720,560)
            l=QVBoxLayout(d)
            guide=QLabel('모든 Mode에서 공유되는 공통 자료입니다.\nReference / Specification, Execution Log, Screenshot Evidence, Test Environment를 관리하세요.')
            guide.setWordWrap(True); l.addWidget(guide)
            tabs=QTabWidget()
            files_page=QWidget(); fl=QVBoxLayout(files_page)
            files=QListWidget(); files.addItems([os.path.basename(x) for x in getattr(self,'domain_evidence_files',[])])
            add_files=QPushButton('Attach Reference / Log Files')
            def attach_and_refresh():
                self.attach_domain_evidence(); files.clear(); files.addItems([os.path.basename(x) for x in getattr(self,'domain_evidence_files',[])])
            add_files.clicked.connect(attach_and_refresh); fl.addWidget(files,1); fl.addWidget(add_files)
            tabs.addTab(files_page,'Reference / Logs')
            shot_page=QWidget(); sl=QVBoxLayout(shot_page); shot_info=QLabel('Screenshot Evidence는 기존 증적 관리 기능과 공유됩니다.'); shot_info.setWordWrap(True)
            shot_btn=QPushButton('Attach Screenshots'); shot_btn.clicked.connect(self.attach_file); sl.addWidget(shot_info); sl.addWidget(shot_btn); sl.addStretch(); tabs.addTab(shot_page,'Screenshots')
            env_page=QWidget(); el=QVBoxLayout(env_page); env=QTextEdit(); env.setPlaceholderText('예:\nOS / Platform: Windows 11\nProduct Version: 1.2.0\nBuild: 2026.09.29\nDevice / Target: Test PC A\nNetwork: 사내망\nConfiguration: Default'); env.setPlainText(getattr(self,'test_environment',''))
            env.textChanged.connect(lambda: setattr(self,'test_environment',env.toPlainText())); el.addWidget(env); tabs.addTab(env_page,'Test Environment')
            l.addWidget(tabs,1); close=QPushButton('Close'); close.clicked.connect(d.accept); l.addWidget(close); d.exec(); self._u_update_domain_resource_ui()

    def _u_update_domain_resource_ui(self):
            if not hasattr(self,'u_resource_btn'): return
            domain=self.qa_domain.currentText(); auto=(domain=='Automotive CANoe')
            self.u_resource_status.setText(self._u_resource_count_text())
            self.u_resource_btn.setText('Attach / Manage DBC' if auto else 'Manage Common Resources')
            self.u_resource_status.setToolTip('\n'.join(getattr(self,'dbc_file_paths',[]) if auto else getattr(self,'domain_evidence_files',[])))
            if hasattr(self,'u_auto_panel'): self.u_auto_panel.setVisible(auto)
            if hasattr(self,'u_general_panel'): self.u_general_panel.setVisible(not auto)

    def _u_prompt_dialog(self):
            d=QDialog(self); d.setWindowTitle('Prompt Preview'); d.resize(900,650); l=QVBoxLayout(d)
            t=QTextEdit(); t.setReadOnly(True); t.setPlainText(self.result.toPlainText() or 'Prompt Generation을 실행하면 Prompt가 표시됩니다.'); l.addWidget(t,1)
            b=QPushButton('Copy Prompt'); b.clicked.connect(lambda: QApplication.clipboard().setText(t.toPlainText())); l.addWidget(b); d.exec()

    def _u_saved_dialog(self):
            self.refresh_saved_tc_list(); d=QDialog(self); d.setWindowTitle('Saved TC / Projects'); d.resize(680,520); l=QVBoxLayout(d)
            q=QLineEdit(); q.setPlaceholderText('예: TC_DOOR_LOCK 또는 저장 날짜로 검색'); lst=QListWidget()
            for i in range(self.saved_tc_list.count()):
                src=self.saved_tc_list.item(i); it=QListWidgetItem(src.text()); it.setData(Qt.UserRole,src.data(Qt.UserRole)); lst.addItem(it)
            q.textChanged.connect(lambda text:[lst.item(i).setHidden(text.lower() not in lst.item(i).text().lower()) for i in range(lst.count())])
            def open_item(item=None):
                item=item or lst.currentItem()
                if item: self.load_saved_tc(item); d.accept(); QTimer.singleShot(30,self._u_sync_results)
            lst.itemDoubleClicked.connect(open_item); row=QHBoxLayout(); op=QPushButton('Open'); op.clicked.connect(lambda:open_item()); close=QPushButton('Close'); close.clicked.connect(d.reject); row.addWidget(op); row.addStretch(); row.addWidget(close)
            l.addWidget(q); l.addWidget(lst,1); l.addLayout(row); d.exec()

    def _u_tab_changed(self,index):
            if hasattr(self,'u_stack'): self._u_save_mode_state(self.u_stack.currentIndex())
            modes=['🔍 Validation Analysis','✨ TC Generation','📝 TC Review']; names=['Validation Analysis','TC Generation','TC Review']
            self.mode.setCurrentText(modes[index]); self.u_stack.setCurrentIndex(index); self.u_title.setText(f'📋 Validation Assistant · {names[index]}')
            self.u_prompt_btn.setVisible(index!=1); self._u_update_domain_resource_ui(); self._u_restore_mode_state(index); self._u_refresh_evidence_gallery(); QTimer.singleShot(0,self._u_refresh_auto_wrap)

    def _u_apply_example_placeholders(self):
            """Apply concise, domain-aware examples without inserting real data."""
            if not hasattr(self, 'u_val_tc'):
                return
            domain = self.qa_domain.currentText()
            examples = {
                'Automotive CANoe': {
                    'tc': '예: TC_DOOR_LOCK_001',
                    'feature': '예: Automatic Door Lock',
                    'requirement': '예: 인증 성공 후 모든 도어가 CLOSED이면 자동 잠금을 수행한다.',
                    'acceptance': '예: Lock_Request 발생 후 2초 이내 DoorLock_Status = LOCKED',
                    'pre': '예:\n1. IGN = ON\n2. 모든 도어 = CLOSED\n3. Key_AuthStatus = SUCCESS',
                    'steps': '예:\n1. 키를 NEAR에서 FAR 영역으로 이동한다.\n2. 잠금 요청 상태를 확인한다.',
                    'expected': '예:\n1. DoorLock_Request = REQUEST\n2. 2초 이내 DoorLock_Status = LOCKED',
                    'actual': '예:\n1. DoorLock_Request = REQUEST 확인\n2. DoorLock_Status = UNLOCKED 유지',
                    'review': '예: Signal명, 시간 조건, 판정 기준, Negative 조건을 검토한다.',
                    'flow': '예:\n1. 초기 상태 확인\n2. Trigger 수행\n3. Signal 및 물리 상태 확인',
                    'observation': '예: DoorLock_Request, DoorLock_Status, 실제 도어 잠금 상태',
                },
                'Web / API QA': {
                    'tc': '예: TC_LOGIN_API_001', 'feature': '예: 사용자 로그인 API',
                    'requirement': '예: 유효한 계정으로 로그인 요청 시 Access Token을 반환한다.',
                    'acceptance': '예: HTTP 200, token 필드 존재, 응답 시간 2초 이내',
                    'pre': '예:\n1. 테스트 계정 활성화\n2. API 서버 정상 연결',
                    'steps': '예:\n1. POST /login 요청\n2. 응답 Status와 Body 확인',
                    'expected': '예:\n1. HTTP 200\n2. token 값이 비어 있지 않음',
                    'actual': '예: HTTP 401, error = INVALID_CREDENTIALS',
                    'review': '예: Endpoint, 입력값, Status Code, Schema, 경계값을 검토한다.',
                    'flow': '예: Request 구성 → API 호출 → Status 확인 → Body 검증',
                    'observation': '예: Status Code, Response Body, Header, Response Time',
                },
                'Mobile App QA': {
                    'tc': '예: TC_APP_LOGIN_001', 'feature': '예: 앱 로그인',
                    'requirement': '예: 유효한 계정으로 로그인하면 홈 화면으로 이동한다.',
                    'acceptance': '예: 오류 메시지 없이 홈 화면 표시, 사용자 정보 정상 노출',
                    'pre': '예:\n1. 앱 신규 설치\n2. 네트워크 연결\n3. 테스트 계정 준비',
                    'steps': '예:\n1. ID/PW 입력\n2. 로그인 버튼 선택\n3. 이동 화면 확인',
                    'expected': '예: 홈 화면과 사용자 이름이 정상 표시됨',
                    'actual': '예: 로딩 후 로그인 화면에 그대로 머무름',
                    'review': '예: OS, 기기, 앱 버전, 권한, 네트워크 조건을 검토한다.',
                    'flow': '예: 앱 실행 → 로그인 정보 입력 → 버튼 선택 → 화면 전환 확인',
                    'observation': '예: 화면 전환, Toast, App Log, Network 상태',
                },
                'Embedded / Device QA': {
                    'tc': '예: TC_FW_UPDATE_001', 'feature': '예: 펌웨어 업데이트',
                    'requirement': '예: 유효한 펌웨어 파일을 선택하면 업데이트를 완료하고 장치를 재시작한다.',
                    'acceptance': '예: 업데이트 완료 메시지 표시, Firmware Version = 2.1.0',
                    'pre': '예:\n1. 장치 전원 안정\n2. 통신 연결 확인\n3. 유효한 펌웨어 파일 준비',
                    'steps': '예:\n1. 펌웨어 파일을 선택한다.\n2. Update를 실행한다.\n3. 재시작 후 버전을 확인한다.',
                    'expected': '예: 업데이트가 완료되고 Firmware Version = 2.1.0으로 표시된다.',
                    'actual': '예: 진행률 80%에서 중단되고 TIMEOUT 오류가 기록된다.',
                    'review': '예: 장치 상태, 통신 조건, Timeout, 복구 절차, 판정 기준을 검토한다.',
                    'flow': '예: 연결 확인 → 파일 선택 → 업데이트 실행 → 재시작 → 버전 확인',
                    'observation': '예: Device Log, Firmware Version, 진행률, 오류 코드',
                },
                'Desktop Software QA': {
                    'tc': '예: TC_EXPORT_XLSX_001', 'feature': '예: Excel 보고서 내보내기',
                    'requirement': '예: 분석 결과를 선택한 경로에 XLSX 파일로 저장한다.',
                    'acceptance': '예: 파일 생성, 필수 Sheet 존재, 행 번호와 결과값 정상 표시',
                    'pre': '예:\n1. 분석 결과 존재\n2. 저장 경로 쓰기 권한 확보',
                    'steps': '예:\n1. Export Excel을 선택한다.\n2. 저장 경로를 지정한다.\n3. 생성 파일을 연다.',
                    'expected': '예: XLSX 파일이 생성되고 Summary와 Result Sheet가 정상 표시된다.',
                    'actual': '예: 파일은 생성되었으나 Result Sheet가 비어 있다.',
                    'review': '예: OS, 앱 버전, 파일 권한, 출력 형식, 오류 처리를 검토한다.',
                    'flow': '예: 결과 준비 → Export 실행 → 경로 지정 → 파일 내용 확인',
                    'observation': '예: Application Log, 생성 파일, 오류 메시지, 저장 경로',
                },
                'General QA': {
                    'tc': '예: TC_FEATURE_001', 'feature': '예: 검증할 기능 이름',
                    'requirement': '예: 특정 조건에서 기능이 수행해야 하는 동작을 입력하세요.',
                    'acceptance': '예: 관찰 가능한 상태, 출력값, 시간 또는 화면 결과를 입력하세요.',
                    'pre': '예:\n1. 시험 환경 준비\n2. 초기 상태 설정\n3. 필요한 데이터 준비',
                    'steps': '예:\n1. 기능을 실행한다.\n2. 결과를 확인한다.\n3. 시험 상태를 정리한다.',
                    'expected': '예: 요구사항에 정의된 상태 또는 결과가 확인된다.',
                    'actual': '예: 실제 관찰한 상태, 출력값 또는 오류 내용을 입력한다.',
                    'review': '예: 누락, 모호성, 실행 가능성, 판정 가능성을 검토한다.',
                    'flow': '예: 초기 상태 확인 → 기능 실행 → 결과 확인 → 상태 정리',
                    'observation': '예: 로그, 상태값, 화면, 오류 메시지, 생성 파일',
                },
                'Custom': {
                    'tc': '예: TC_CUSTOM_001', 'feature': '예: 사용자 정의 검증 기능',
                    'requirement': '예: 적용할 조건, 입력, 동작 규칙을 구체적으로 입력하세요.',
                    'acceptance': '예: 통과 여부를 판단할 수 있는 측정값 또는 결과를 입력하세요.',
                    'pre': '예:\n1. 사용자 정의 환경 준비\n2. 초기 조건 설정',
                    'steps': '예:\n1. 정의된 입력을 적용한다.\n2. 결과와 Evidence를 확인한다.',
                    'expected': '예: 정의한 통과 기준과 일치하는 결과가 확인된다.',
                    'actual': '예: 실제 결과와 기대 결과의 차이를 입력한다.',
                    'review': '예: 사용자 정의 규칙, 누락 조건, 판정 기준을 검토한다.',
                    'flow': '예: 환경 준비 → 입력 적용 → 결과 확인 → Evidence 저장',
                    'observation': '예: 사용자 정의 로그, 상태값, 화면 또는 출력 파일',
                },
            }
            default = {
                'tc': '예: TC_FEATURE_001', 'feature': '예: 검증할 기능 이름',
                'requirement': '예: 사용 조건과 기대 동작을 구체적으로 입력하세요.',
                'acceptance': '예: 관찰 가능한 값, 상태, 시간 또는 화면 결과를 입력하세요.',
                'pre': '예:\n1. 시험 환경 준비\n2. 초기 상태 설정\n3. 필요한 데이터 준비',
                'steps': '예:\n1. 기능을 실행한다.\n2. 결과를 확인한다.',
                'expected': '예: 기대 상태, 출력값 또는 화면 결과가 확인된다.',
                'actual': '예: 실제 관찰된 상태, 출력값 또는 오류 내용을 입력한다.',
                'review': '예: 누락, 모호성, 실행 가능성, 판정 가능성을 검토한다.',
                'flow': '예: 초기 상태 확인 → 기능 실행 → 결과 확인 → 정리',
                'observation': '예: 로그, 상태값, 화면, 오류 메시지 등 확인할 항목',
            }
            ex = examples.get(domain, default)
            self.u_val_tc.setPlaceholderText(ex['tc'])
            self.u_gen_tc.setPlaceholderText(ex['feature'])
            self.u_gen_req.setPlaceholderText(ex['requirement'])
            self.u_gen_acc.setPlaceholderText(ex['acceptance'])
            self.u_pre.setPlaceholderText(ex['pre'])
            self.u_obs.setPlaceholderText(ex['observation'])
            self.u_flow.setPlaceholderText(ex['flow'])
            self.u_review_tc.setPlaceholderText(ex['tc'])
            validation_placeholders = [ex['pre'], ex['steps'], ex['expected'], ex['actual']]
            review_placeholders = [ex['pre'], ex['steps'], ex['expected'], ex['review']]
            for editor, placeholder in zip(getattr(self, 'u_validation_editors', []), validation_placeholders):
                editor.setPlaceholderText(placeholder)
            for editor, placeholder in zip(getattr(self, 'u_review_editors', []), review_placeholders):
                editor.setPlaceholderText(placeholder)
            self.u_start.setPlaceholderText('예: 0.0초')
            self.u_end.setPlaceholderText('예: 60.0초')
            self.u_filter.setPlaceholderText('예: DoorLock_*, Key_AuthStatus, Error_*')

    def _u_show_raw_json(self,key):
            widget={'validation':self.u_val_result,'review':self.u_review_result}.get(key)
            if widget is None:return
            dialog=QDialog(self); dialog.setWindowTitle('AI JSON 원문'); dialog.resize(900,680); layout=QVBoxLayout(dialog)
            viewer=QTextEdit(); self._u_enable_auto_wrap(viewer); viewer.setReadOnly(True); viewer.setPlainText(widget.toPlainText() or '붙여넣은 JSON 원문이 없습니다.'); layout.addWidget(viewer,1)
            row=QHBoxLayout(); copy=QPushButton('JSON 복사'); copy.clicked.connect(lambda:QApplication.clipboard().setText(viewer.toPlainText())); close=QPushButton('닫기'); close.clicked.connect(dialog.accept); row.addWidget(copy); row.addStretch(); row.addWidget(close); layout.addLayout(row); dialog.exec()

    def _u_result_action_row(self,key):
            buttons=[self._u_button('Paste',self._u_paste),self._u_button('JSON 원문 보기',lambda _checked=False,k=key:self._u_show_raw_json(k)),self._u_button('현재 결과 지우기',self._u_clear_current_mode)]
            for button in buttons:
                font=button.font(); font.setPointSize(9); font.setBold(True); button.setFont(font); button.setFixedHeight(50)
            return self._u_row(buttons,[1,1,1])

    def _u_remove_all_evidence(self):
            image_paths=[p for p in getattr(self,'attachments',[]) if str(p).lower().endswith(('.png','.jpg','.jpeg','.bmp','.webp'))]
            if not image_paths:
                QMessageBox.information(self,'사진 전체 삭제','삭제할 첨부 이미지가 없습니다.'); return
            reply=QMessageBox.question(self,'사진 전체 삭제',f'첨부 이미지 {len(image_paths)}개를 현재 프로젝트에서 모두 제거할까요?\n\n원본 파일은 삭제되지 않습니다.',QMessageBox.Yes|QMessageBox.No,QMessageBox.No)
            if reply!=QMessageBox.Yes:return
            image_set=set(image_paths); self.attachments=[p for p in self.attachments if p not in image_set]
            self.refresh_attachment_list(); self.refresh_image_gallery(); self._u_refresh_evidence_gallery(); self.update_dashboard()
            if self.generated_prompt:self.update_prompt_preview()

    def _u_attach_screenshots(self):
            self.attach_file(); self._u_refresh_evidence_gallery()

    def _u_remove_evidence(self,path):
            self.remove_attachment(path); self._u_refresh_evidence_gallery()

    def _u_refresh_evidence_gallery(self):
            if not hasattr(self,'u_evidence_grid'):return
            self._u_clear_layout(self.u_evidence_grid)
            image_paths=[p for p in getattr(self,'attachments',[]) if str(p).lower().endswith(('.png','.jpg','.jpeg','.bmp','.webp'))]
            self.u_evidence_count.setText(f'첨부 이미지 {len(image_paths)}개')
            if not image_paths:
                empty=QLabel('첨부된 이미지가 없습니다.\nScreenshot Evidence 버튼으로 이미지를 추가하세요.'); empty.setAlignment(Qt.AlignCenter); empty.setObjectName('uGalleryEmpty'); self.u_evidence_grid.addWidget(empty,0,0,1,2); return
            for i,path in enumerate(image_paths):
                card=QWidget(); card.setObjectName('uImageCard'); box=QVBoxLayout(card); box.setContentsMargins(5,5,5,5); box.setSpacing(4)
                top=QHBoxLayout(); name=QLabel(os.path.basename(path)); name.setToolTip(path); name.setTextInteractionFlags(Qt.TextSelectableByMouse); delete=QPushButton('삭제'); delete.setMaximumWidth(50); delete.clicked.connect(lambda _checked=False,p=path:self._u_remove_evidence(p)); top.addWidget(name,1); top.addWidget(delete); box.addLayout(top)
                thumb=QLabel(); thumb.setObjectName('uThumbnail'); thumb.setAlignment(Qt.AlignCenter); thumb.setMinimumHeight(150); thumb.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed); thumb.setCursor(Qt.PointingHandCursor); pix=QPixmap(path) if os.path.isfile(path) else QPixmap()
                if not pix.isNull(): thumb.setPixmap(pix.scaled(340,190,Qt.KeepAspectRatio,Qt.SmoothTransformation))
                else: thumb.setText('이미지 미리보기 실패')
                thumb.setToolTip('클릭하면 기본 사진 앱으로 엽니다.'); thumb.mousePressEvent=lambda event,p=path:self.open_image_file(p); box.addWidget(thumb)
                self.u_evidence_grid.addWidget(card,i,0)
            self.u_evidence_grid.setColumnStretch(0,1)

    def _u_create_evidence_gallery(self):
            panel=QGroupBox('Screenshot Evidence'); panel.setObjectName('uEvidencePanel'); panel.setStyleSheet("QGroupBox#uEvidencePanel{background:#111d28;color:#e7eef3;border:1px solid #395267;border-radius:6px;margin-top:10px;padding-top:9px;} QGroupBox#uEvidencePanel::title{background:#111d28;color:#e7eef3;subcontrol-origin:margin;left:9px;padding:0 5px;}"); layout=QVBoxLayout(panel); header_widget=QWidget(); header_widget.setObjectName('uEvidenceHeader'); header_widget.setStyleSheet("background:#111d28;color:#e7eef3;border:none;"); head=QHBoxLayout(header_widget); head.setContentsMargins(0,0,0,0); self.u_evidence_count=QLabel('첨부 이미지 0개'); add=self._u_button('사진 첨부',self._u_attach_screenshots); copy_all=self._u_button('사진 복사',self.copy_evidence_files_only); copy_all.setToolTip('첨부된 모든 이미지를 하나의 이미지로 정리하여 클립보드에 복사합니다.'); delete_all=self._u_button('사진 전체 삭제',self._u_remove_all_evidence); head.addWidget(self.u_evidence_count); head.addStretch(); head.addWidget(add); head.addWidget(copy_all); head.addWidget(delete_all); layout.addWidget(header_widget)
            scroll=QScrollArea(); scroll.setWidgetResizable(True); scroll.setObjectName('uEvidenceGallery'); scroll.setStyleSheet("QScrollArea#uEvidenceGallery{background:#0d1923;border:1px solid #395267;border-radius:5px;} QScrollArea#uEvidenceGallery QWidget#qt_scrollarea_viewport{background:#0d1923;}"); body=QWidget(); body.setStyleSheet("background:#0d1923;"); self.u_evidence_grid=QGridLayout(body); self.u_evidence_grid.setContentsMargins(5,5,5,5); self.u_evidence_grid.setSpacing(7); scroll.setWidget(body); scroll.setMinimumHeight(240); scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff); layout.addWidget(scroll,1); self._u_refresh_evidence_gallery(); return panel

    def _u_clear_layout(self, layout):
            if layout is None: return
            while layout.count():
                item=layout.takeAt(0); widget=item.widget(); child=item.layout()
                if widget: widget.deleteLater()
                elif child: self._u_clear_layout(child)

    def _u_format_result_value(self, value):
            if isinstance(value,list): return '\n'.join(f'{i}. {self._u_format_result_value(v)}' for i,v in enumerate(value,1)) if value else '내용 없음'
            if isinstance(value,dict): return json.dumps(value,ensure_ascii=False,indent=2)
            return str(value or '내용 없음')

    def _u_result_card(self,title,content):
            box=QGroupBox(title); lay=QVBoxLayout(box); label=QLabel(self._u_format_result_value(content)); label.setWordWrap(True); label.setTextInteractionFlags(Qt.TextSelectableByMouse); lay.addWidget(label); return box

    def _u_review_overall_result(self,data):
            reviews=data.get('reviewed_test_cases',[]) if isinstance(data,dict) else []
            values=[str(x.get('review_result','')).upper() for x in reviews if isinstance(x,dict)]
            if any('FAIL' in x for x in values): return 'FAIL'
            if any('NEEDS_IMPROVEMENT' in x or 'PARTIAL' in x for x in values): return 'NEEDS IMPROVEMENT'
            if values and all('PASS' in x for x in values): return 'PASS'
            summary=data.get('review_summary',{}) if isinstance(data,dict) else {}
            if int(summary.get('needs_improvement_count',0) or 0)>0:return 'NEEDS IMPROVEMENT'
            if int(summary.get('pass_count',0) or 0)>0:return 'PASS'
            return 'UNKNOWN'

    def _u_show_structured_result(self,key,data):
            if key not in ('validation','review'): return
            layout=self.u_structured_layouts.get(key); self._u_clear_layout(layout)
            if not isinstance(data,dict) or not data:
                if key=='validation': self._u_set_result_metric('validation','')
                else:
                    empty=QLabel('JSON 결과를 Paste하면 판정과 상세 결과가 표시됩니다.'); empty.setWordWrap(True); empty.setObjectName('uStructuredEmptyGuide'); layout.addWidget(empty)
                layout.addStretch(1); return
            if key=='validation':
                self._u_set_result_metric('validation',self._u_extract_result_metric('validation',data))
                result=str(data.get('result','UNKNOWN')).upper(); summary=data.get('summary',''); confidence=data.get('confidence','UNKNOWN'); risk=data.get('risk','UNKNOWN')
                header=QGroupBox('Validation 판정'); header.setObjectName('uValidationVerdictBox'); header.setStyleSheet('QGroupBox#uValidationVerdictBox{background:#101c27;color:#f3f7f9;border:1px solid #4a6578;border-radius:7px;margin-top:12px;padding-top:8px;} QGroupBox#uValidationVerdictBox::title{subcontrol-origin:margin;left:12px;padding:0 6px;background:#101c27;color:#f3f7f9;font-size:9pt;font-weight:800;}'); grid=QGridLayout(header); grid.setContentsMargins(14,14,14,12); grid.setHorizontalSpacing(16)
                verdict=QLabel(self.get_result_display_text(result)); verdict.setObjectName('uLargeVerdict'); verdict.setProperty('verdict',result); verdict.setAlignment(Qt.AlignCenter)
                grid.addWidget(verdict,0,0); grid.addWidget(QLabel(f'CONFIDENCE\n{confidence}'),0,1); grid.addWidget(QLabel(f'RISK\n{risk}'),0,2); layout.addWidget(header)
                layout.addWidget(self._u_result_card('Executive Summary',summary))
                layout.addWidget(self._u_result_card('PASS Factors',data.get('pass_factors',[])))
                layout.addWidget(self._u_result_card('FAIL Factors',data.get('fail_factors',[])))
                for title,field in [('Observations','observations'),('Test Gaps','gaps'),('Recommended Verification','recommended_verification'),('Next Actions','next_actions')]:
                    if data.get(field): layout.addWidget(self._u_result_card(title,data.get(field)))
            else:
                overall=self._u_review_overall_result(data); summary=data.get('review_summary',{})
                header=QGroupBox('TC Review 판정'); grid=QGridLayout(header); verdict=QLabel(overall); verdict.setObjectName('uLargeVerdict'); verdict.setProperty('verdict',overall); verdict.setAlignment(Qt.AlignCenter); grid.addWidget(verdict,0,0)
                grid.addWidget(QLabel(f"PASS\n{summary.get('pass_count',0)}"),0,1); grid.addWidget(QLabel(f"개선 필요\n{summary.get('needs_improvement_count',0)}"),0,2); layout.addWidget(header)
                if summary.get('overall_comment'): layout.addWidget(self._u_result_card('Overall Comment',summary.get('overall_comment')))
                for item in data.get('reviewed_test_cases',[]):
                    if not isinstance(item,dict):continue
                    title=f"{item.get('tc_id','TC')} · {item.get('review_result','UNKNOWN')} · Score {item.get('score','-')}"
                    content={'Issues':item.get('issues',[]),'Missing Conditions':item.get('missing_conditions',[]),'Recommendations':item.get('recommendations',[])}
                    layout.addWidget(self._u_result_card(title,content))
            layout.addStretch()

    def _u_display_current_structured_result(self):
            key=self._u_mode_key(); data=getattr(self,'current_ai_result_data',{}) or {}; self._u_show_structured_result(key,data)

    def _u_create_structured_panel(self,key):
            scroll=QScrollArea(); scroll.setWidgetResizable(True); scroll.setObjectName('uStructuredResult'); scroll.setStyleSheet("QScrollArea#uStructuredResult{background:#0d1923;border:1px solid #395267;border-radius:5px;} QScrollArea#uStructuredResult QWidget#qt_scrollarea_viewport{background:#0d1923;}")
            container=QWidget(); container.setStyleSheet("background:#0d1923;color:#e7eef3;"); layout=QVBoxLayout(container); layout.setContentsMargins(8,8,8,8); layout.setSpacing(8); scroll.setWidget(container)
            self.u_structured_layouts[key]=layout; self._u_show_structured_result(key,{})
            return scroll

    def _u_mode_key(self, index=None):
            index=self.u_tabs.currentIndex() if index is None else index
            return ('validation','generation','review')[max(0,min(2,index))]

    def _u_save_mode_state(self, index=None):
            if not hasattr(self,'u_mode_states'): return
            key=self._u_mode_key(index)
            prompt_widget={'validation':None,'generation':getattr(self,'u_prompt',None),'review':None}[key]
            result_widget={'validation':getattr(self,'u_val_result',None),'generation':getattr(self,'u_gen_result',None),'review':getattr(self,'u_review_result',None)}[key]
            if prompt_widget is not None: self.u_mode_states[key]['prompt']=prompt_widget.toPlainText()
            if result_widget is not None: self.u_mode_states[key]['result']=result_widget.toPlainText()
            if hasattr(self,'u_verdict_labels') and key in self.u_verdict_labels:
                self.u_mode_states[key]['verdict']=self.u_verdict_labels[key].text()

    def _u_restore_mode_state(self,index):
            if not hasattr(self,'u_mode_states'): return
            key=self._u_mode_key(index); state=self.u_mode_states[key]
            if key=='generation' and hasattr(self,'u_prompt'): self.u_prompt.setPlainText(state.get('prompt',''))
            result_widget={'validation':self.u_val_result,'generation':self.u_gen_result,'review':self.u_review_result}[key]
            result_widget.setPlainText(state.get('result',''))
            restored_metric=state.get('verdict','')
            if str(restored_metric).upper() in ('UNKNOWN','대기','WAITING'): restored_metric=''
            self._u_set_result_metric(key,restored_metric)

    def _u_extract_verdict(self):
            data=getattr(self,'current_ai_result_data',{}) or {}
            candidates=[data.get('result'),data.get('verdict'),data.get('status')]
            conclusion=data.get('final_conclusion',{})
            if isinstance(conclusion,dict): candidates += [conclusion.get('final_verdict'),conclusion.get('result')]
            text=' '.join(str(x or '') for x in candidates).upper()
            if 'INCONCLUSIVE' in text or 'REVIEW REQUIRED' in text or 'NEEDS IMPROVEMENT' in text: return 'INCONCLUSIVE'
            if 'FAIL' in text or 'FAILED' in text or 'NG' in text: return 'FAIL'
            if 'PASS' in text or 'PASSED' in text or 'APPROVED' in text: return 'PASS'
            return 'UNKNOWN'

    def _u_score_value(self, value):
            """AI JSON의 점수 후보를 0~100 범위 숫자로 정규화한다."""
            if isinstance(value,bool) or value is None:
                return None
            try:
                if isinstance(value,str):
                    match=re.search(r"-?\d+(?:\.\d+)?",value)
                    if not match: return None
                    number=float(match.group(0))
                else:
                    number=float(value)
                if 0.0 <= number <= 1.0:
                    number*=100.0
                return max(0,min(100,int(round(number))))
            except Exception:
                return None

    def _u_extract_result_metric(self,key,data=None):
            """JSON 직접 점수를 우선 사용하고, 없으면 판정 근거로 0~100 로컬 총점을 계산한다."""
            data=data if isinstance(data,dict) else (getattr(self,'current_ai_result_data',{}) or {})
            if not isinstance(data,dict) or not data:
                return 'SCORE -- / 100'
            score_keys=('score','overall_score','quality_score','confidence_score','validation_score')
            for field in score_keys:
                score=self._u_score_value(data.get(field))
                if score is not None:return f'SCORE {score} / 100'
            summary=data.get('review_summary',{})
            if isinstance(summary,dict):
                for field in score_keys:
                    score=self._u_score_value(summary.get(field))
                    if score is not None:return f'SCORE {score} / 100'
            reviewed=data.get('reviewed_test_cases',[])
            scores=[]
            if isinstance(reviewed,list):
                for item in reviewed:
                    if isinstance(item,dict):
                        score=self._u_score_value(item.get('score'))
                        if score is not None:scores.append(score)
            if scores:return f'SCORE {int(round(sum(scores)/len(scores)))} / 100'
            result=' '.join(str(data.get(k,'') or '') for k in ('result','final_verdict','verdict','status','evidence_status')).upper()
            if 'PASS' in result and 'FAIL' not in result: score=90
            elif 'FAIL' in result and 'INSUFFICIENT' not in result: score=35
            elif 'INSUFFICIENT' in result: score=45
            elif any(word in result for word in ('INCONCLUSIVE','REVIEW REQUIRED','NEEDS IMPROVEMENT')): score=55
            else: score=60
            confidence=str(data.get('confidence','') or '').upper()
            score += {'HIGH':5,'MEDIUM':0,'LOW':-8,'UNKNOWN':-12}.get(confidence,0)
            evidence=str(data.get('evidence_status','') or '').upper()
            if 'SUFFICIENT' in evidence and 'INSUFFICIENT' not in evidence:score+=5
            if 'INSUFFICIENT' in evidence:score-=8
            gaps=data.get('gaps',[]) or data.get('test_gaps',[]) or []
            if isinstance(gaps,list):score-=min(12,len(gaps)*3)
            return f'SCORE {max(0,min(100,int(round(score))))} / 100'

    def _u_set_result_metric(self,key,value):
            text=str(value or '').strip()
            if key=='validation' and hasattr(self,'u_validation_metric_label'):
                label=self.u_validation_metric_label
                m=re.search(r'(\d{1,3})',text); score=m.group(1) if m else '--'
                label.setText(f"TOTAL SCORE   {score} / 100")
                label.setVisible(True); return
            if not hasattr(self,'u_verdict_labels') or key not in self.u_verdict_labels:return
            label=self.u_verdict_labels[key]; label.setVisible(bool(text))
            if text: label.setText(text)

    def _u_set_verdict(self,key,value):
            if not hasattr(self,'u_verdict_labels') or key not in self.u_verdict_labels:return
            value=(value or 'UNKNOWN').upper(); label=self.u_verdict_labels[key]
            visible=value not in ('대기','WAITING','')
            label.setVisible(visible)
            if not visible: return
            label.setText(value); label.setProperty('verdict',value); label.style().unpolish(label); label.style().polish(label)

    def _u_result_header(self,key,title):
            row=QWidget(); row.setObjectName('uResultHeader'); lay=QHBoxLayout(row); lay.setContentsMargins(0,0,0,0)
            lay.addWidget(self._u_label(title,True),1); badge=QLabel(''); badge.setObjectName('uVerdict'); badge.setAlignment(Qt.AlignCenter); badge.setMinimumWidth(145); badge.setVisible(False); badge.setToolTip('AI JSON에 포함된 Score 또는 Confidence를 표시합니다.'); self.u_verdict_labels[key]=badge
            if key!='validation': lay.addWidget(badge)
            return row

    def _u_sync_current_mode_only(self):
            key=self._u_mode_key(); prompt=self.result.toPlainText(); ai=self.ai_result.toPlainText()
            if key=='generation': self.u_prompt.setPlainText(prompt); self.u_gen_result.setPlainText(ai)
            elif key=='review': self.u_review_result.setPlainText(ai)
            else: self.u_val_result.setPlainText(ai)
            metric=self._u_extract_result_metric(key); self._u_set_result_metric(key,metric); self._u_display_current_structured_result()
            self.u_mode_states[key]={'prompt':prompt if key=='generation' else self.u_mode_states[key].get('prompt',''),'result':ai,'verdict':metric}; QTimer.singleShot(0,self._u_refresh_auto_wrap)

    def _u_clear_current_mode(self):
            key=self._u_mode_key(); self.u_mode_states[key]={'prompt':'','result':'','verdict':'대기'}
            if key=='generation': self.u_prompt.clear(); self.u_gen_result.clear()
            elif key=='review': self.u_review_result.clear()
            else: self.u_val_result.clear()
            self._u_set_result_metric(key,''); self._u_show_structured_result(key,{})
            self.clear_ai_result(); self.result.clear()

    def _u_clear_all(self):
            reply=QMessageBox.question(self,'전체 지우기','현재 입력, Prompt, AI 결과, BLF/DBC 분석 상태를 모두 지울까요?',QMessageBox.Yes|QMessageBox.No,QMessageBox.No)
            if reply!=QMessageBox.Yes:return
            self.tc.clear(); self.purpose.clear(); self.expected.clear()
            for w in (self.validation_preconditions,self.validation_steps,self.validation_expected_results,self.validation_actual_results): w.clear()
            for w in (getattr(self,'u_pre',None),getattr(self,'u_obs',None),getattr(self,'u_flow',None)):
                if w is not None:w.clear()
            self.clear_ai_result(); self.result.clear(); self.blf_file_path=''; self.dbc_file_paths=[]; self.blf_summary_data={}
            self.u_mode_states={k:{'prompt':'','result':'','verdict':'대기'} for k in ('validation','generation','review')}
            for k in self.u_mode_states:self._u_set_result_metric(k,''); self._u_show_structured_result(k,{}) if k in ('validation','review') else None
            for w in (self.u_prompt,self.u_val_result,self.u_gen_result,self.u_review_result):w.clear()
            self._u_update_domain_resource_ui(); self._u_update_blf_status()

    def _u_update_blf_status(self):
            if not hasattr(self,'u_blf_status'):return
            if getattr(self,'blf_summary_data',{}):
                stats=self.blf_summary_data.get('statistics',{}); self.u_blf_status.setText(f"AI Context 준비 완료 · Decoded {stats.get('decoded_messages',0)}")
                self.u_blf_status.setProperty('state','ready')
            elif getattr(self,'blf_file_path',''):
                self.u_blf_status.setText('BLF 선택됨 · 로컬 분석 필요'); self.u_blf_status.setProperty('state','pending')
            else:self.u_blf_status.setText('BLF 미선택'); self.u_blf_status.setProperty('state','empty')
            self.u_blf_status.style().unpolish(self.u_blf_status); self.u_blf_status.style().polish(self.u_blf_status)

    def _u_attach_blf(self):
            self.attach_blf_file(); self._u_update_blf_status()
            if getattr(self,"blf_file_path",""):
                self.u_start.setText(self.blf_start_time.text()); self.u_end.setText(self.blf_end_time.text())
                self.sync_selected_signals_to_filter()

    def _u_parse_blf(self):
            self.blf_start_time.setText(self.u_start.text()); self.blf_end_time.setText(self.u_end.text()); self.signal_filter.setText(self.u_filter.text())
            self.parse_blf_locally(); self._u_update_blf_status()

    def _u_show_blf_summary(self):
            d=QDialog(self); d.setWindowTitle('AI 전달용 BLF Summary'); d.resize(850,650); l=QVBoxLayout(d); t=QTextEdit(); self._u_enable_auto_wrap(t); t.setReadOnly(True); t.setPlainText(self.get_blf_summary_for_prompt()); l.addWidget(t,1); c=QPushButton('닫기'); c.clicked.connect(d.accept); l.addWidget(c); d.exec()

    def _u_generate_with_blf_check(self,mode):
            if 'Validation Analysis' in mode and getattr(self,'blf_file_path','') and not getattr(self,'blf_summary_data',{}):
                box=QMessageBox(self); box.setWindowTitle('BLF 분석 필요'); box.setText('BLF 파일이 선택되었지만 아직 로컬 분석되지 않았습니다.'); parse_btn=box.addButton('분석 후 Prompt 생성',QMessageBox.AcceptRole); without_btn=box.addButton('BLF 없이 생성',QMessageBox.DestructiveRole); box.addButton('취소',QMessageBox.RejectRole); box.exec()
                if box.clickedButton()==parse_btn:self._u_parse_blf()
                elif box.clickedButton()!=without_btn:return
            self.mode.setCurrentText(mode); self.Prompt_Generation(); QTimer.singleShot(30,self._u_sync_current_mode_only)

    def _u_mode_example_data(self, mode_index=None):
            domain=self.qa_domain.currentText()
            mode_index=self.u_tabs.currentIndex() if mode_index is None else mode_index
            domain_data={
                'Automotive CANoe': {
                    'tc':'TC_DOOR_LOCK_001','feature':'Automatic Door Lock',
                    'requirement':'인증 성공 후 모든 도어가 CLOSED 상태이면 자동 잠금을 수행한다.',
                    'acceptance':'DoorLock_Request 발생 후 2초 이내 DoorLock_Status = LOCKED가 되어야 한다.',
                    'pre':'1. IGN = ON\n2. 모든 도어 = CLOSED\n3. Key_AuthStatus = SUCCESS',
                    'steps':'1. 키를 NEAR 영역에서 FAR 영역으로 이동한다.\n2. DoorLock_Request 상태를 확인한다.\n3. 실제 도어 잠금 상태를 확인한다.',
                    'expected':'1. DoorLock_Request = REQUEST\n2. 요청 후 2초 이내 DoorLock_Status = LOCKED\n3. 모든 도어가 실제로 잠긴다.',
                    'actual':'1. DoorLock_Request = REQUEST 확인\n2. DoorLock_Status = UNLOCKED 유지\n3. 운전석 도어가 잠기지 않음',
                    'review':'1. 각 Step에 대응하는 Expected가 있는지 확인\n2. 시간 기준이 측정 가능한지 확인\n3. Signal명과 값이 DBC에 존재하는지 확인\n4. Timeout 및 Negative 조건이 포함되었는지 확인',
                    'condition':'1. IGN = ON\n2. 모든 도어 = CLOSED\n3. Key_AuthStatus = SUCCESS',
                    'observation':'DoorLock_Request\nDoorLock_Status\n실제 도어 잠금 상태',
                    'flow':'1. 초기 차량 상태를 확인한다.\n2. 키를 FAR 영역으로 이동한다.\n3. 잠금 요청 Signal을 확인한다.\n4. 잠금 상태와 실제 도어 상태를 확인한다.'},
                'Web / API QA': {
                    'tc':'TC_LOGIN_API_001','feature':'사용자 로그인 API',
                    'requirement':'유효한 계정으로 POST /login 요청 시 Access Token을 반환한다.',
                    'acceptance':'HTTP 200, token 필드 존재, 응답 시간 2초 이내여야 한다.',
                    'pre':'1. 테스트 계정 활성화\n2. API 서버 정상 연결\n3. 유효한 Request Body 준비',
                    'steps':'1. POST /login 요청을 전송한다.\n2. Status Code를 확인한다.\n3. Response Body와 응답 시간을 확인한다.',
                    'expected':'1. HTTP 200\n2. token 값이 비어 있지 않음\n3. 응답 시간 2초 이내',
                    'actual':'1. HTTP 401\n2. error = INVALID_CREDENTIALS\n3. 응답 시간 0.8초',
                    'review':'Endpoint, Method, 필수 Parameter, Status Code, Response Schema, 경계값을 검토한다.',
                    'condition':'1. API 서버 정상\n2. 테스트 계정 활성화\n3. 인증 Header 준비',
                    'observation':'Status Code\nResponse Body\nHeader\nResponse Time',
                    'flow':'Request 구성 → API 호출 → Status 확인 → Body 검증 → 응답 시간 확인'},
                'Mobile App QA': {
                    'tc':'TC_APP_LOGIN_001','feature':'앱 로그인',
                    'requirement':'유효한 계정으로 로그인하면 홈 화면으로 이동한다.',
                    'acceptance':'오류 메시지 없이 홈 화면과 사용자 정보가 정상 표시되어야 한다.',
                    'pre':'1. 앱 신규 설치\n2. 네트워크 연결\n3. 테스트 계정 준비',
                    'steps':'1. ID와 Password를 입력한다.\n2. 로그인 버튼을 선택한다.\n3. 이동 화면을 확인한다.',
                    'expected':'홈 화면으로 이동하고 사용자 이름이 정상 표시된다.',
                    'actual':'로딩 표시 후 로그인 화면에 그대로 머무른다.',
                    'review':'OS, 기기, 앱 버전, 권한, 네트워크 조건과 화면 판정 기준을 검토한다.',
                    'condition':'1. Android 15\n2. App 3.4.1\n3. Wi-Fi 연결',
                    'observation':'화면 전환\nToast 메시지\nApp Log\nNetwork 상태',
                    'flow':'앱 실행 → 로그인 정보 입력 → 버튼 선택 → 화면 전환 확인'},
                'Embedded / Device QA': {
                    'tc':'TC_FW_UPDATE_001','feature':'펌웨어 업데이트',
                    'requirement':'유효한 펌웨어 파일을 선택하면 업데이트 후 장치를 재시작한다.',
                    'acceptance':'업데이트 완료 후 Firmware Version = 2.1.0으로 표시되어야 한다.',
                    'pre':'1. 장치 전원 안정\n2. 통신 연결 확인\n3. 유효한 펌웨어 준비',
                    'steps':'1. 펌웨어 파일을 선택한다.\n2. Update를 실행한다.\n3. 재시작 후 버전을 확인한다.',
                    'expected':'업데이트가 완료되고 Firmware Version = 2.1.0으로 표시된다.',
                    'actual':'진행률 80%에서 중단되고 TIMEOUT 오류가 기록된다.',
                    'review':'장치 상태, 통신 조건, Timeout, 복구 절차와 판정 기준을 검토한다.',
                    'condition':'전원 안정, 통신 연결, 펌웨어 파일 준비',
                    'observation':'Device Log\nFirmware Version\n진행률\n오류 코드',
                    'flow':'연결 확인 → 파일 선택 → 업데이트 실행 → 재시작 → 버전 확인'},
                'Desktop Software QA': {
                    'tc':'TC_EXPORT_XLSX_001','feature':'Excel 보고서 내보내기',
                    'requirement':'분석 결과를 선택한 경로에 XLSX 파일로 저장한다.',
                    'acceptance':'파일이 생성되고 Summary와 Result Sheet가 정상 표시되어야 한다.',
                    'pre':'1. 분석 결과 존재\n2. 저장 경로 쓰기 권한 확보',
                    'steps':'1. Export Excel을 선택한다.\n2. 저장 경로를 지정한다.\n3. 생성 파일을 연다.',
                    'expected':'XLSX 파일이 생성되고 필수 Sheet와 결과값이 표시된다.',
                    'actual':'파일은 생성되었으나 Result Sheet가 비어 있다.',
                    'review':'OS, 앱 버전, 파일 권한, 출력 형식과 오류 처리를 검토한다.',
                    'condition':'Windows 11, App 1.2.0, 저장 경로 쓰기 가능',
                    'observation':'Application Log\n생성 파일\n오류 메시지\n저장 경로',
                    'flow':'결과 준비 → Export 실행 → 경로 지정 → 파일 내용 확인'}
            }
            d=domain_data.get(domain,{
                'tc':'TC_FEATURE_001','feature':'검증할 기능 이름','requirement':'특정 조건에서 기능이 수행해야 하는 동작을 입력한다.',
                'acceptance':'관찰 가능한 상태, 출력값, 시간 또는 화면 결과를 입력한다.','pre':'1. 시험 환경 준비\n2. 초기 상태 설정\n3. 필요한 데이터 준비',
                'steps':'1. 기능을 실행한다.\n2. 결과를 확인한다.\n3. 시험 상태를 정리한다.','expected':'요구사항에 정의된 상태 또는 결과가 확인된다.',
                'actual':'실제 관찰한 상태, 출력값 또는 오류 내용을 입력한다.','review':'누락, 모호성, 실행 가능성, 판정 가능성을 검토한다.',
                'condition':'시험 환경, 초기 상태, 입력 데이터를 정의한다.','observation':'로그, 상태값, 화면, 오류 메시지, 생성 파일','flow':'초기 상태 확인 → 기능 실행 → 결과 확인 → 상태 정리'})
            if mode_index==0:
                return [('TC Name',d['tc']),('Precondition',d['pre']),('Steps',d['steps']),('Expected',d['expected']),('Actual',d['actual'])]
            if mode_index==1:
                return [('기능 이름',d['feature']),('요구사항 및 동작',d['requirement']),('정상 동작 / 합격 기준',d['acceptance']),('시험 조건',d['condition']),('추가 관찰 지점',d['observation']),('수행 순서',d['flow'])]
            return [('TC Name',d['tc']),('Precondition',d['pre']),('Steps',d['steps']),('Expected',d['expected']),('Review 기준',d['review'])]

    def _u_enable_auto_wrap(self, editor):
            """Force responsive visual wrapping without modifying the stored text."""
            if not isinstance(editor, QTextEdit):
                return editor
            editor.setAcceptRichText(False)
            editor.setLineWrapMode(QTextEdit.WidgetWidth)
            editor.setLineWrapColumnOrWidth(0)
            editor.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
            editor.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            option = editor.document().defaultTextOption()
            option.setWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
            editor.document().setDefaultTextOption(option)
            editor.document().setDocumentMargin(8)
            editor.viewport().update()
            return editor

    def _u_refresh_auto_wrap(self):
            """Recalculate wrap widths after tab changes, resizing, and text updates."""
            if not hasattr(self, 'u_shell'):
                return
            for editor in self.u_shell.findChildren(QTextEdit):
                self._u_enable_auto_wrap(editor)
                editor.document().adjustSize()
                editor.viewport().update()

    def _u_enable_all_auto_wrap(self):
            """Apply auto wrapping to every editor in the unified UI and example dialog."""
            if not hasattr(self, 'u_shell'):
                return
            for editor in self.u_shell.findChildren(QTextEdit):
                self._u_enable_auto_wrap(editor)

    def _u_example_targets(self, mode_index):
            """Return example-dialog targets in the same order as _u_mode_example_data()."""
            if mode_index == 0:
                return [self.u_val_tc] + list(getattr(self, 'u_validation_editors', []))
            if mode_index == 1:
                return [
                    self.u_gen_tc,
                    self.u_gen_req,
                    self.u_gen_acc,
                    self.u_pre,
                    self.u_obs,
                    self.u_flow,
                ]
            return [self.u_review_tc] + list(getattr(self, 'u_review_editors', []))

    def _u_set_example_target(self, widget, text):
            if isinstance(widget, QLineEdit):
                widget.setText(text)
            elif isinstance(widget, QTextEdit):
                self._u_enable_auto_wrap(widget)
                widget.setPlainText(text)
            widget.setFocus(); QTimer.singleShot(0,self._u_refresh_auto_wrap)

    def _u_apply_current_example(self, mode_index, tabs, data):
            index = tabs.currentIndex()
            targets = self._u_example_targets(mode_index)
            if 0 <= index < len(targets) and index < len(data):
                self._u_set_example_target(targets[index], data[index][1])

    def _u_apply_all_examples(self, mode_index, data):
            targets = self._u_example_targets(mode_index)
            for target, (_title, text) in zip(targets, data):
                self._u_set_example_target(target, text)
            # Keep the first field active after bulk application.
            if targets:
                targets[0].setFocus()

    def _u_show_example_dialog(self, mode_index=None):
            mode_index=self.u_tabs.currentIndex() if mode_index is None else mode_index
            mode_names=['Validation Analysis','TC Generation','TC Review']
            data=self._u_mode_example_data(mode_index)
            dialog=QDialog(self); dialog.setWindowTitle(f'작성 예시 · {mode_names[mode_index]} · {self.qa_domain.currentText()}'); dialog.resize(820,680)
            root=QVBoxLayout(dialog)
            header=QLabel(f'{self.qa_domain.currentText()} / {mode_names[mode_index]} 작성 예시'); header.setObjectName('uExampleTitle'); root.addWidget(header)
            tabs=QTabWidget(); editors=[]
            for title,text in data:
                editor=QTextEdit(); self._u_enable_auto_wrap(editor); editor.setReadOnly(True); editor.setPlainText(text); editor.setProperty('exampleEditor',True); tabs.addTab(editor,title); editors.append(editor)
            root.addWidget(tabs,1)
            note=QLabel("현재 탭에 적용은 선택한 항목만, 전체 예시 적용은 현재 Mode의 모든 입력칸을 채웁니다. 적용 후 실제 사양과 시험 조건에 맞게 수정하세요."); note.setWordWrap(True); root.addWidget(note)
            buttons=QHBoxLayout()
            apply_current=QPushButton('현재 탭에 적용')
            apply_current.setToolTip('현재 보고 있는 예시를 해당 입력 탭에 자동 입력합니다.')
            apply_current.clicked.connect(lambda: self._u_apply_current_example(mode_index, tabs, data))
            apply_all=QPushButton('전체 예시 적용')
            apply_all.setToolTip('현재 Mode의 모든 예시를 각 입력 항목에 자동 입력합니다.')
            apply_all.clicked.connect(lambda: self._u_apply_all_examples(mode_index, data))
            copy_current=QPushButton('현재 예시 복사')
            copy_current.clicked.connect(lambda: QApplication.clipboard().setText(editors[tabs.currentIndex()].toPlainText()))
            close=QPushButton('닫기'); close.clicked.connect(dialog.accept)
            buttons.addWidget(apply_current); buttons.addWidget(apply_all); buttons.addWidget(copy_current)
            buttons.addStretch(); buttons.addWidget(close); root.addLayout(buttons)
            dialog.setStyleSheet('QLabel#uExampleTitle{font-size:12pt;font-weight:800;padding:6px;} QTextEdit[exampleEditor="true"]{font-family:"Cascadia Mono","Consolas","Malgun Gothic";font-size:10pt;line-height:1.4;}')
            dialog.exec()

    def _u_info_header(self, mode_index):
            row=QWidget(); row.setObjectName('uInfoHeader'); layout=QHBoxLayout(row); layout.setContentsMargins(0,0,0,0); layout.setSpacing(6)
            layout.addWidget(self._u_label('TC Information',True),1)
            button=self._u_button('💡 예시 보기',lambda _checked=False,i=mode_index:self._u_show_example_dialog(i)); button.setMaximumWidth(110); layout.addWidget(button)
            return row

    def _u_apply_short_guides(self):
            if not hasattr(self,'u_validation_editors'): return
            self.u_val_tc.setPlaceholderText('TC 이름 또는 식별자를 입력하세요.')
            self.u_gen_tc.setPlaceholderText('검증할 기능 이름을 입력하세요.')
            self.u_gen_req.setPlaceholderText('요구사항과 시스템 동작을 입력하세요.')
            self.u_gen_acc.setPlaceholderText('측정하거나 관찰할 수 있는 합격 기준을 입력하세요.')
            self.u_pre.setPlaceholderText('시험 시작 전 조건을 입력하세요.')
            self.u_obs.setPlaceholderText('추가로 확인할 로그, 상태값 또는 화면을 입력하세요.')
            self.u_flow.setPlaceholderText('수행 순서를 번호로 입력하세요. 비워두면 AI가 생성합니다.')
            self.u_review_tc.setPlaceholderText('검토할 TC 이름을 입력하세요.')
            for editor,text in zip(self.u_validation_editors,['시험 시작 전 조건을 번호로 입력하세요.','수행 절차를 Step 번호별로 입력하세요.','각 Step에 대응하는 기대 결과를 입력하세요.','실제로 관찰한 결과를 입력하세요.']): editor.setPlaceholderText(text)
            for editor,text in zip(self.u_review_editors,['시험 시작 전 조건을 입력하세요.','검토할 수행 절차를 입력하세요.','검토할 기대 결과를 입력하세요.','누락, 모호성, 판정 기준 등 중점 항목을 입력하세요.']): editor.setPlaceholderText(text)

    def build_unified_domain_workspace(self):
            self.test_environment=getattr(self,'test_environment',''); self.u_structured_layouts={}; self.u_mode_states={k:{'prompt':'','result':'','verdict':'대기'} for k in ('validation','generation','review')}; self.u_verdict_labels={}
            self.u_shell=QWidget(self); self.u_shell.setObjectName('uShell'); root=QVBoxLayout(self.u_shell); root.setContentsMargins(12,10,12,12); root.setSpacing(8)
            head=QHBoxLayout(); self.u_title=QLabel('📋 Validation Assistant · Validation Analysis'); self.u_title.setObjectName('uTitle'); head.addWidget(self.u_title); head.addStretch()
            self.u_tabs=QTabBar(); self.u_tabs.setObjectName('uTabs'); self.u_tabs.setExpanding(False)
            for x in ('Validation Analysis','TC Generation','TC Review'): self.u_tabs.addTab(x)
            head.addWidget(self.u_tabs)
            self.u_theme_switch_btn=QPushButton('☀ 밝은 화면'); self.u_theme_switch_btn.setObjectName('uSecondary')
            self.u_theme_switch_btn.setToolTip('입력값과 결과를 유지하면서 테마를 전환합니다.')
            self.u_theme_switch_btn.clicked.connect(lambda: self.switch_unified_theme('bright'))
            head.addWidget(self.u_theme_switch_btn); root.addLayout(head)
            bar=QWidget(); bar.setObjectName('uCommon'); bl=QHBoxLayout(bar); bl.setContentsMargins(7,5,7,5); bl.setSpacing(6)
            bl.addWidget(QLabel('QA Domain')); self.u_domain=QComboBox(); self._u_bind_combo(self.u_domain,self.qa_domain); self.u_domain.setMinimumWidth(150); bl.addWidget(self.u_domain)
            bl.addWidget(QLabel('Prompt Level')); self.u_level=QComboBox(); self._u_bind_combo(self.u_level,self.prompt_level); self.u_level.setMinimumWidth(90); bl.addWidget(self.u_level)
            self.u_resource_status=QLabel(); self.u_resource_status.setObjectName('uResourceStatus'); bl.addWidget(self.u_resource_status)
            self.u_resource_btn=self._u_button('Manage Resources',self._u_manage_resources); bl.addWidget(self.u_resource_btn); bl.addStretch()
            self.u_prompt_btn=self._u_button('프롬프트 보기',self._u_prompt_dialog); bl.addWidget(self.u_prompt_btn)
            for txt,fn in [('저장',self.save_tc),('파일 열기',self.load_tc),('저장 목록',self._u_saved_dialog),('Excel 내보내기',self.export_excel)]: bl.addWidget(self._u_button(txt,fn))
            bl.addWidget(self._u_button('전체 지우기',self._u_clear_all))
            root.addWidget(bar)
            self.u_stack=QStackedWidget(); root.addWidget(self.u_stack,1)
    
            # Validation
            page=QWidget(); pl=QHBoxLayout(page); pl.setContentsMargins(0,0,0,0); pl.setSpacing(10); left,ll=self._u_card(); right,rl=self._u_card()
            ll.addWidget(self._u_info_header(0)); self.u_val_tc=QLineEdit(); self._u_bind_line(self.u_val_tc,self.tc); ll.addWidget(self._u_label('TC Name')); ll.addWidget(self.u_val_tc)
            vt=QTabWidget(); vt.setObjectName('uValidationTabs'); self.u_validation_editors=[]
            for name,back in [('Precondition',self.validation_preconditions),('Steps',self.validation_steps),('Expected',self.validation_expected_results),('Actual',self.validation_actual_results)]:
                e=QTextEdit(); e.setObjectName('uTabEditor'); self._u_bind_text(e,back); vt.addTab(e,name); self.u_validation_editors.append(e)
            ll.addWidget(vt,1)
            result_split=QSplitter(Qt.Horizontal); result_split.setObjectName('uValidationResultSplitter')
            raw_box=QWidget(); raw_box.setObjectName('uResultPane'); raw_box.setStyleSheet("background:#111d28;color:#e7eef3;"); raw_layout=QVBoxLayout(raw_box); raw_layout.setContentsMargins(0,0,0,0); raw_layout.setSpacing(6)
            raw_layout.addWidget(self._u_result_header('validation','AI Analysis Result')); validation_action_row=self._u_result_action_row('validation'); validation_action_row.setObjectName('uResultActionRow'); validation_action_row.setStyleSheet("background:#111d28;color:#e7eef3;border:none;"); validation_action_row.setFixedHeight(50); raw_layout.addWidget(validation_action_row)
            self.u_val_result=QTextEdit(); self.u_val_result.setReadOnly(True); self.u_val_result.setMinimumHeight(0); self.u_val_result.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding); self.u_val_result.setStyleSheet('QTextEdit{background:#0d1923;color:#edf4f7;border:1px solid #4a6578;border-radius:6px;padding:8px;}'); self.u_val_result.setPlaceholderText('AI JSON을 Paste하면 원문이 표시됩니다.'); raw_layout.addWidget(self.u_val_result,1)
            structured_box=QWidget(); structured_box.setObjectName('uResultPane'); structured_box.setStyleSheet("background:#111d28;color:#e7eef3;"); structured_layout=QVBoxLayout(structured_box); structured_layout.setContentsMargins(0,0,0,0); structured_layout.setSpacing(6)
            structured_header=self._u_label('AI 구조화 결과',True); structured_header.setStyleSheet("background:#111d28;color:#33ddd5;border:none;font-weight:800;padding:6px;"); structured_layout.addWidget(structured_header); self.u_validation_metric_label=QLabel('TOTAL SCORE   -- / 100'); self.u_validation_metric_label.setObjectName('uStructuredMetric'); self.u_validation_metric_label.setWordWrap(False); self.u_validation_metric_label.setFixedHeight(50); metric_font=self.u_validation_metric_label.font(); metric_font.setPointSize(9); metric_font.setBold(True); self.u_validation_metric_label.setFont(metric_font); self.u_validation_metric_label.setAlignment(Qt.AlignLeft|Qt.AlignVCenter); self.u_validation_metric_label.setProperty('metricState','guide'); self.u_validation_metric_label.setStyleSheet('background:#172432;color:#c6d2d9;border:1px solid #40586b;border-radius:5px;padding:6px 10px;font-size:9pt;font-weight:700;'); structured_layout.addWidget(self.u_validation_metric_label); structured_validation=self._u_create_structured_panel('validation'); structured_validation.setStyleSheet('QScrollArea#uStructuredResult{background:#0d1923;border:1px solid #4a6578;border-radius:6px;} QScrollArea#uStructuredResult QWidget#qt_scrollarea_viewport{background:#0d1923;}'); structured_validation.setMinimumHeight(0); structured_validation.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding); structured_layout.addWidget(structured_validation,1)
            raw_box.setMinimumWidth(280); structured_box.setMinimumWidth(280); raw_box.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding); structured_box.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding); result_split.addWidget(raw_box); result_split.addWidget(structured_box); result_split.setChildrenCollapsible(False); result_split.setHandleWidth(5); result_split.setSizes([500,500]); result_split.setStretchFactor(0,1); result_split.setStretchFactor(1,1); result_split.setOpaqueResize(True); ll.addWidget(result_split,3); QTimer.singleShot(0,lambda rs=result_split: rs.setSizes([1,1]))
            ll.addWidget(self._u_button('Prompt Generation',lambda:self._u_generate_with_blf_check('🔍 Validation Analysis'),True))
            self.u_auto_panel=QWidget(); self.u_auto_panel.setObjectName('uAutoPanel'); ar=QVBoxLayout(self.u_auto_panel); ar.setContentsMargins(0,0,0,0); ar.setSpacing(5)
            ar.addWidget(self._u_label('Automotive Log Analysis',True)); ar.addWidget(self._u_button('Attach BLF',self._u_attach_blf)); self.u_blf_status=QLabel('BLF 미선택'); self.u_blf_status.setObjectName('uBlfStatus'); ar.addWidget(self.u_blf_status); ar.addWidget(QLabel('DBC는 상단 공통 Resource에서 연결합니다.'))
            self.u_start=QLineEdit(); self.u_end=QLineEdit(); self.u_start.setPlaceholderText('Start sec'); self.u_end.setPlaceholderText('End sec'); ar.addWidget(self._u_row([self.u_start,self.u_end])); self.u_filter=QLineEdit(); self.u_filter.setPlaceholderText('Signal Filter'); ar.addWidget(self.u_filter)
            self.u_security_mode=QComboBox(); self.u_security_mode.addItems(["1. 보안 기본 · 익명 요약","2. 의미 보존 변환 · 전체 식별자 별칭","3. 승인 후 원문 포함"]); self.u_security_mode.setCurrentIndex(self.ai_transmission_mode.currentIndex()); self.u_security_mode.currentIndexChanged.connect(self.ai_transmission_mode.setCurrentIndex); self.ai_transmission_mode.currentIndexChanged.connect(self.u_security_mode.setCurrentIndex); ar.addWidget(self._u_label('AI 전송 보안 모드')); ar.addWidget(self.u_security_mode)
            self.u_security_notice=QLabel(); self.u_security_notice.setWordWrap(True); ar.addWidget(self.u_security_notice); self.ai_transmission_mode.currentIndexChanged.connect(lambda _i:self.u_security_notice.setText(self.ai_transmission_notice.text())); self.u_security_notice.setText(self.ai_transmission_notice.text())
            self.u_tc_signal_status=QLabel('TC 관련 Signal 미확정'); self.u_tc_signal_status.setWordWrap(True); ar.addWidget(self.u_tc_signal_status)
            button_grid=QGridLayout(); button_grid.setContentsMargins(0,0,0,0); button_grid.setHorizontalSpacing(5); button_grid.setVerticalSpacing(5)
            b1=self._u_button('TC 관련 Signal 찾기',lambda:self.select_tc_related_signals(show_dialog=True)); b2=self._u_button('Signal 직접 추가',self.add_manual_dbc_signals); b3=self._u_button('TC Signal만 Parse',self._u_parse_blf,True); b4=self._u_button('BLF Summary 보기',self._u_show_blf_summary)
            for button in (b1,b2,b3,b4): button.setMinimumHeight(30); button.setMaximumHeight(34)
            button_grid.addWidget(b1,0,0); button_grid.addWidget(b2,0,1); button_grid.addWidget(b3,1,0); button_grid.addWidget(b4,1,1); ar.addLayout(button_grid); ar.addStretch(); rl.addWidget(self.u_auto_panel)
            self.u_general_panel=QWidget(); gr=QVBoxLayout(self.u_general_panel); gr.setContentsMargins(0,0,0,0); gr.addWidget(self._u_label('General Evidence Analysis',True)); gr.addWidget(QLabel('Reference, Log, Screenshot, Test Environment를 공통 Resource로 관리합니다.')); gr.addWidget(self._u_button('Manage Common Resources',self._u_manage_resources)); gr.addStretch(); rl.addWidget(self.u_general_panel); rl.addWidget(self._u_create_evidence_gallery(),1)
            pl.addWidget(left,72); pl.addWidget(right,28); self.u_stack.addWidget(page)
    
            # Generation
            page=QWidget(); pl=QHBoxLayout(page); pl.setContentsMargins(0,0,0,0); pl.setSpacing(10); left,ll=self._u_card(); right,rr=self._u_card(); ll.addWidget(self._u_info_header(1)); gt=QTabWidget(); gt.setObjectName('uGenerationTabs')
            basic=QWidget(); basic.setObjectName('uGenerationPage'); x=QVBoxLayout(basic); self.u_gen_tc=QLineEdit(); self._u_bind_line(self.u_gen_tc,self.tc); self.u_gen_req=QTextEdit(); self._u_bind_text(self.u_gen_req,self.purpose); self.u_gen_acc=QTextEdit(); self._u_bind_text(self.u_gen_acc,self.expected); x.addWidget(self._u_label('기능 이름')); x.addWidget(self.u_gen_tc); x.addWidget(self._u_label('요구사항 및 동작')); x.addWidget(self.u_gen_req,2); x.addWidget(self._u_label('정상 동작 / 합격 기준')); x.addWidget(self.u_gen_acc,1); gt.addTab(basic,'기본 내용')
            cond=QWidget(); cond.setObjectName('uGenerationPage'); x=QVBoxLayout(cond); self.u_pre=QTextEdit(); self.u_obs=QTextEdit(); self.u_pre.textChanged.connect(lambda:setattr(self,'tc_generation_preconditions',self.u_pre.toPlainText())); self.u_obs.textChanged.connect(lambda:setattr(self,'tc_generation_observations',self.u_obs.toPlainText())); x.addWidget(self._u_label('시험 조건')); x.addWidget(self.u_pre); x.addWidget(self._u_label('추가 관찰 지점')); x.addWidget(self.u_obs); gt.addTab(cond,'시험 조건')
            seq=QWidget(); seq.setObjectName('uGenerationPage'); x=QVBoxLayout(seq); self.u_flow=QTextEdit(); self.u_flow.textChanged.connect(lambda:setattr(self,'tc_generation_sequence',self.u_flow.toPlainText())); self.u_seq=QComboBox(); self._u_bind_combo(self.u_seq,self.tc_generation_sequence_mode_combo); self.u_sig=QComboBox(); self._u_bind_combo(self.u_sig,self.tc_generation_signal_mode); chk=QCheckBox('자동 Review Prompt'); chk.setChecked(self.auto_tc_review.isChecked()); chk.toggled.connect(self.auto_tc_review.setChecked); x.addWidget(self._u_label('수행 순서')); x.addWidget(self.u_flow); seq_mode_row=self._u_row([self._u_label('순서 생성'),self.u_seq],[1,3]); seq_mode_row.setObjectName('uGenerationSettingRow'); x.addWidget(seq_mode_row); signal_mode_row=self._u_row([self._u_label('Signal 처리'),self.u_sig],[1,3]); signal_mode_row.setObjectName('uGenerationSettingRow'); x.addWidget(signal_mode_row); chk.setObjectName('uGenerationCheck'); x.addWidget(chk); x.addWidget(self._u_button('DBC Context Match',lambda:self.apply_dbc_combined_autocorrection(show_message=True))); gt.addTab(seq,'수행 순서 / 설정')
            ll.addWidget(gt,1); ll.addWidget(self._u_button('Prompt Generation',lambda:self._u_generate_with_blf_check('✨ TC Generation'),True)); rr.addWidget(self._u_label('Prompt Preview',True)); self.u_prompt=QTextEdit(); self.u_prompt.setReadOnly(True); rr.addWidget(self.u_prompt,1); rr.addWidget(self._u_result_header('generation','AI Result')); rr.addWidget(self._u_row([self._u_button('Paste',self._u_paste),self._u_button('현재 결과 지우기',self._u_clear_current_mode)])); self.u_gen_result=QTextEdit(); self.u_gen_result.setReadOnly(True); rr.addWidget(self.u_gen_result,1); pl.addWidget(left,48); pl.addWidget(right,52); self.u_stack.addWidget(page)
    
            # Review
            page=QWidget(); pl=QHBoxLayout(page); pl.setContentsMargins(0,0,0,0); pl.setSpacing(10); left,ll=self._u_card(); right,rr=self._u_card(); ll.addWidget(self._u_info_header(2)); self.u_review_tc=QLineEdit(); self._u_bind_line(self.u_review_tc,self.tc); ll.addWidget(self._u_label('TC Name')); ll.addWidget(self.u_review_tc); rt=QTabWidget(); rt.setObjectName('uReviewTabs')
            self.u_review_editors=[]
            for name,back in [('Precondition',self.validation_preconditions),('Steps',self.validation_steps),('Expected',self.validation_expected_results),('Review 기준',self.validation_actual_results)]:
                e=QTextEdit(); e.setObjectName('uTabEditor'); self._u_bind_text(e,back); rt.addTab(e,name); self.u_review_editors.append(e)
            ll.addWidget(rt,1); ll.addWidget(self._u_button('Prompt Generation',lambda:self._u_generate_with_blf_check('📝 TC Review'),True)); rr.addWidget(self._u_result_header('review','AI Review Result')); rr.addWidget(self._u_result_action_row('review')); self.u_review_result=QTextEdit(); self.u_review_result.setReadOnly(True); self.u_review_result.setMaximumHeight(95); self.u_review_result.setPlaceholderText('AI Review JSON을 Paste하면 아래에 판정과 개선 항목이 정리됩니다.'); rr.addWidget(self.u_review_result); structured_review=self._u_create_structured_panel('review'); structured_review.setMinimumHeight(300); rr.addWidget(structured_review,3); pl.addWidget(left,55); pl.addWidget(right,45); self.u_stack.addWidget(page)
    
            self.u_shell.setStyleSheet(self._u_theme_css())
            self.u_tabs.currentChanged.connect(self._u_tab_changed);  self.qa_domain.currentTextChanged.connect(lambda _t:self._u_update_domain_resource_ui())
            self.u_tabs.setCurrentIndex(0); self._u_tab_changed(0); self._u_apply_short_guides(); self._u_enable_all_auto_wrap(); self.u_shell.setGeometry(self.rect()); self.u_shell.show(); self.u_shell.raise_()

    def _u_theme_css(self):
            return """
            QWidget#uShell { background:#0b141d; color:#edf3f7; font-family:"Segoe UI","Malgun Gothic"; }
            QWidget#uShell QWidget { background-color:transparent; color:#e7eef3; }
            QWidget#uCard, QWidget#uCommon, QWidget#uAutoPanel, QWidget#uEvidencePanel { background:#111d28; border:1px solid #2f4658; border-radius:7px; }
            QWidget#uInfoHeader, QWidget#uResultHeader, QWidget#uResultActionRow, QWidget#uResultActionSpacer, QWidget#uResultPane { background:#111d28; border:none; color:#e7eef3; }
            QLabel { color:#e8eef3; background:transparent; font-weight:600; }
            QLabel#uTitle { color:#ffffff; font-size:13pt; font-weight:800; }
            QLabel#uSection { color:#4adce8; background:#111d28; font-size:11pt; font-weight:800; border-bottom:1px solid #2f4658; padding:6px; }
            QLabel#uField { color:#edf3f7; font-weight:700; }
            QLabel#uResourceStatus { color:#52e4dc; background:#132731; border:1px solid #286b68; border-radius:4px; padding:7px; }
            QLabel#uGalleryEmpty { color:#718a98; background:#0d1822; padding:22px; }
            QLabel#uBlfStatus { color:#dce7ed; background:#172634; border:1px solid #395267; border-radius:4px; padding:7px; }
            QLineEdit,QTextEdit,QComboBox,QSpinBox { background:#0d1923; color:#edf4f7; border:1px solid #395267; border-radius:4px; padding:6px; selection-background-color:#0f8f83; }
            QLineEdit:focus,QTextEdit:focus,QComboBox:focus,QSpinBox:focus { border:1px solid #20c9bd; }
            QComboBox QAbstractItemView { background:#111d28; color:#edf4f7; border:1px solid #395267; selection-background-color:#0f8f83; }
            QPushButton { background:#1d2a38; color:#f3f6f9; border:1px solid #4a5d70; border-radius:4px; padding:6px 10px; font-family:"Segoe UI","Malgun Gothic"; font-size:9pt; font-weight:700; }
            QPushButton:hover { background:#293b4d; color:#ffffff; border-color:#6b8195; }
            QPushButton#primaryButton { background:#0f8279; color:#ffffff; border:1px solid #19b9ae; font-size:9.5pt; font-weight:800; }
            QPushButton#primaryButton:hover { background:#10988d; color:#ffffff; border-color:#42d6cb; }
            QTabBar#uTabs::tab { min-width:130px; padding:8px 13px; margin-left:5px; background:#172432; color:#e1e9ee; border:1px solid #3b5264; border-radius:5px; }
            QTabBar#uTabs::tab:selected { background:#0c8b80; color:#ffffff; border-color:#22c9bd; }
            QTabWidget::pane, QTabWidget#uGenerationTabs::pane, QTabWidget#uValidationTabs::pane, QTabWidget#uReviewTabs::pane { background:#0d1923; border:1px solid #395267; }
            QTabWidget QWidget { background:#0d1923; }
            QTabBar::tab { background:#172432; color:#e1e9ee; border:1px solid #3b5264; padding:6px 12px; }
            QTabBar::tab:selected { background:#0d1923; color:#38ddd5; border-bottom:2px solid #18b8ad; }
            QScrollArea, QScrollArea#uStructuredResult, QScrollArea#uEvidenceGallery { background:#0d1923; border:1px solid #395267; border-radius:6px; }
            QScrollArea QWidget#qt_scrollarea_viewport { background:#0d1923; }
            QScrollArea > QWidget > QWidget, QScrollArea#uStructuredResult > QWidget > QWidget, QScrollArea#uEvidenceGallery > QWidget > QWidget { background:#0d1923; }
            QScrollArea#uStructuredResult QLabel { color:#e7eef3; background:transparent; }
            QScrollArea#uStructuredResult QGroupBox { color:#e7eef3; background:#132332; border:1px solid #395267; border-radius:6px; margin-top:8px; }
            QGroupBox { color:#e7eef3; background:#111d28; border:1px solid #395267; border-radius:6px; margin-top:8px; }
            QGroupBox::title { color:#e7eef3; subcontrol-origin:margin; left:10px; padding:0 4px; background:#111d28; }
            QLabel#uLargeVerdict, QLabel#uVerdict { background:#64748b; color:white; border-radius:7px; font-weight:900; padding:8px; }
            QLabel#uLargeVerdict[verdict="PASS"], QLabel#uVerdict[verdict="PASS"] { background:#15803d; }
            QLabel#uLargeVerdict[verdict="FAIL"], QLabel#uVerdict[verdict="FAIL"] { background:#b91c1c; }
            QLabel#uLargeVerdict[verdict="INCONCLUSIVE"] { background:#b45309; }
            QListWidget { background:#0d1923; color:#e7eef3; border:1px solid #395267; }
            QSplitter#uValidationResultSplitter { background:#111d28; }
            QSplitter#uValidationResultSplitter::handle { background:#2f4658; width:5px; margin:0; }
            QSplitter#uValidationResultSplitter::handle:hover { background:#18b8ad; }
            QScrollBar:vertical { background:#0d1923; width:11px; }
            QScrollBar::handle:vertical { background:#395267; min-height:24px; border-radius:5px; }
            QPushButton:pressed { background:#13202c; color:#ffffff; border-color:#19b9ae; padding-top:8px; padding-bottom:4px; }
            QPushButton#primaryButton:pressed { background:#096b64; color:#ffffff; border-color:#5eead4; padding-top:8px; padding-bottom:4px; }
    
            """

    def apply_responsive_input_heights(self, client_height):
            """작은 화면에서 TC Generation 입력 박스가 다음 항목을 덮지 않도록 높이를 제한한다."""
            mode = self.mode.currentText() if hasattr(self, "mode") else ""
            is_validation = "Validation Analysis" in mode
            is_generation = "TC Generation" in mode
    
            if is_generation:
                purpose_height = 96
                expected_height = 90
                question_height = 42
            else:
                if client_height < 700:
                    purpose_height, expected_height, question_height = 64, 62, 38
                elif client_height < 790:
                    purpose_height, expected_height, question_height = 76, 72, 42
                elif client_height < 860:
                    purpose_height, expected_height, question_height = 86, 82, 46
                else:
                    purpose_height, expected_height, question_height = 96, 90, 52
    
            if is_validation:
                purpose_height = max(58, purpose_height - 8)
                expected_height = max(58, expected_height - 8)
    
            self.purpose.setFixedHeight(purpose_height)
            self.expected.setFixedHeight(expected_height)
            self.analysis_question.setFixedHeight(question_height)
    
            # 경량 변형 설명은 작은 화면에서 한 줄만 사용한다.
            if hasattr(self, "tc_generation_signal_notice"):
                self.tc_generation_signal_notice.setFixedHeight(24)
                self.tc_generation_signal_notice.setWordWrap(False)
            if hasattr(self, "validation_tabs"):
                mode_now=self.mode.currentText() if hasattr(self,"mode") else ""
                if "Validation Analysis" in mode_now or "TC Review" in mode_now:
                    tab_height = 190 if client_height < 760 else (215 if client_height < 900 else 240)
                    self.validation_tabs.setFixedHeight(tab_height)

