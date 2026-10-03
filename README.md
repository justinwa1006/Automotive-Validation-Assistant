# Validation Assistant - Refactored

기존 대형 `bright_theme.py` / `professional_theme.py`를 기능별 Mixin 모듈로 분리한 버전입니다.

## 실행
프로젝트 상위 폴더에서: `python -m Validation_Assistant_Refactored.unified_launcher --theme dark`

## 구조
- `core_runtime.py`: 공통 import, 설정, 프로필, 공용 클래스/상수
- `automotive.py`: BLF/DBC/ISO-TP/UDS/Signal Mapping
- `tc_engine.py`: TC 생성/검증/프롬프트
- `ai_engine.py`: AI 결과 파싱/검증/표시/Gemini
- `storage.py`: 저장/히스토리/Excel/첨부파일
- `ui_main.py`: 메인 윈도우 초기화/템플릿/도메인 UI
- `ui_components.py`: 화면 컴포넌트 및 결과 패널
- `engine.py`: 위 모듈을 조합한 `ValidationAssistant`
- `main.py`: 기본 실행 진입점
- `unified_launcher.py`: light/dark 테마 실행

`bright_theme.py`와 `professional_theme.py`는 기존 실행 호환용 얇은 래퍼입니다.

## Dependencies
`pip install -r requirements.txt`

직접 실행: `python unified_launcher.py --theme dark` 또는 `python main.py`


## Windows 실행 방법

압축 해제 후 이 폴더에서 PowerShell 또는 CMD를 열고 다음 순서로 실행하세요.

```bat
python -m pip install -r requirements.txt
python unified_launcher.py
```

테마 지정:

```bat
python unified_launcher.py --theme dark
python unified_launcher.py --theme bright
```

또는 `run_validation_assistant.bat`을 더블클릭해서 실행할 수 있습니다.

`unified_launcher.py`는 이제 직접 실행(`python unified_launcher.py`)과 패키지 방식 실행을 모두 지원합니다.
