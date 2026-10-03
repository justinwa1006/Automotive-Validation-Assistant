# 🚗 Automotive Validation Assistant

PySide6 기반의 차량용 SW(CANoe/CAN, Controller Log 등) 검증 및 AI Test Case 분석 지원 도구입니다.

## 🌟기술적 특징 (Key Engineering Highlights)

### 1. SQA 검증 스코어링 & UI 시각화
- AI 분석 결과(TOTAL SCORE) 점수 구간대별(80점 이상 / 50점 이상 / 미만) Dynamic QSS Property 적용으로 검증 상태의 직관적 시각화 지원.
- 비동기 처리 및 토스트(Toast) 메시지 시스템 도입으로 검증 진행 상황 Feedback 개선.

### 2. 모듈 독립성 및 경로 안정성 확보
- `Path(__file__).resolve().parent` 기반의 상대/절대 경로 자동 해소 로직을 구축하여 CWD(현재 작업 디렉토리) 변경에 독립적인 런처 구현.

## 📁 프로젝트 구조 (Architecture)

- `unified_launcher.py`: 통합 런처 (실시간 테마 패치, 단축키 이벤트 핸들링, Entry Point)
- `engine.py`: Validation Assistant 핵심 제어 및 AI 분석 통합 엔진
- `ui_design_system.py`: QSS 테마 관리, Dynamic Property, Toast 시스템
- `ui_main.py` & `ui_components.py`: PySide6 컴포넌트 및 도메인 UI 레이아웃
- `tc_engine.py` & `ai_engine.py`: Test Case 생성/검증 및 AI 결과 파싱

## 🛠 Tech Stack
- **Language**: Python 3.10+
- **GUI Framework**: PySide6 (Qt for Python)
- **Data & Export**: OpenPyXL, JSON
- **Domain**: Automotive SQA, Vector CANoe Log Validation
