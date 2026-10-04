# 🚗 Validation Assistant (쉬운 사용 가이드)

> **컴퓨터나 코딩을 잘 몰라도 OK!**  
> AI를 활용해 테스트케이스(TC)를 만들고 실행 로그를 분석해 주는 **SW 검증 보조 프로그램**입니다.

## ❓ 어떤 프로그램인가요?

* **테스트케이스(TC) 자동 작성**: 요구사항만 적으면 AI가 정량적이고 정확한 테스트케이스를 만들어 줍니다.
* **실행 로그 분석**: 실제 작동 로그를 넣으면 기대 결과와 비교해 PASS/FAIL 원인을 분석해 줍니다.
* **보안 안전 지원**: 회사 내부 기술명이나 신호명이 AI로 그대로 유출되지 않도록 가려주는(마스킹) 기능이 포함되어 있습니다.

## 📥 다운로드 및 설치 방법 (3분 완성)

### 1단계: 컴퓨터에 Python(파이썬)이 설치되어 있는지 확인
이 프로그램은 **Python 3.10 이상**이 필요합니다.
* 컴퓨터에 파이썬이 없다면 [파이썬 공식 다운로드 페이지](https://www.python.org/downloads/)에서 설치해 주세요.
* ⚠️ **주의**: 설치창 아래쪽에 **`Add Python to PATH`** 체크박스가 있다면 꼭 체크하고 설치해 주세요!

### 2단계: 프로그램 다운로드하기

**방법 A. 가장 쉬운 방법 (ZIP 파일 다운로드)**
1. 상단 오른쪽 초록색 **`Code`** -> Download.zip 클릭
2. 다운로드한 파일의 압축을 풉니다.
3. 폴더명은 Validation_Assistant_Refactored 이름으로사용해야합니다.(사용하고 싶은 폴더명이 있으면 여기서 수정)
<img width="674" height="238" alt="image" src="https://github.com/user-attachments/assets/e0739438-87d6-49cd-a87e-af27942cbba0" />


**방법 B. Git을 사용하는 경우**
명령 프롬프트(cmd) 창을 열고 아래 명령어를 입력합니다:
```bash
git clone [https://github.com/justinwa1006/Validation_Assistant_Refactored.git](https://github.com/justinwa1006/Validation_Assistant_Refactored.git)
cd Validation_Assistant_Refactored

3단계: 필요한 프로그램 재료(라이브러리) 설치
압축을 푼 폴더의 빈 공간에서 Shift + 마우스 우클릭 후 여기서 명령 창 열기 또는 PowerShell / 터미널 열기를 누릅니다.

아래 명령어를 그대로 복사해서 붙여넣고 엔터(Enter)를 누릅니다:

Bash
pip install PySide6 openpyxl
🚀 프로그램 실행하기
💡 윈도우(Windows) 사용자 (가장 쉬운 방법)
폴더 안에 있는 run_validation_assistant.bat 파일을 마우스로 더블 클릭하면 바로 프로그램이 실행됩니다!

💻 검은 창(터미널)에서 실행할 경우
Bash
python unified_launcher.py
📖 초간단 사용법
상단 QA Domain 선택: 내가 검증하려는 분야(Automotive ECU, Web / API QA 등)를 고릅니다.

내용 입력: 기능 이름과 요구사항을 입력합니다.

프롬프트 복사: 오른쪽에 자동으로 생성된 글을 [복사] 버튼으로 가져옵니다.

AI에게 전달: ChatGPT나 Gemini 같은 AI 모델에 붙여넣으면 고품질의 결과를 얻을 수 있습니다.

⚠️ 자주 묻는 질문 (오류 해결)
Q. run_validation_assistant.bat을 눌렀는데 검은 창이 켜졌다가 바로 꺼져요!

파이썬 설치가 안 되었거나 환경변수(PATH) 설정이 안 된 경우입니다. 파이썬을 재설치하면서 Add Python to PATH를 체크했는지 확인해 주세요.

Q. No module named PySide6 에러가 떠요!

3단계의 pip install PySide6 openpyxl 명령어를 다시 실행하여 필요한 라이브러리를 설치해 주세요.
