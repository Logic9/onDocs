# **onDocs 설치 및 실행 가이드 (macOS)**

이 문서는 **onDocs** 프로젝트를 Mac(Apple Silicon/Intel) 환경에서 처음부터 설치하고 실행하는 과정을 다룹니다. 터미널 명령어를 단계별로 복사하여 실행하면 간편하게 환경을 구축할 수 있습니다.

## **1단계: 필수 시스템 도구 설치**

터미널(Terminal)을 실행한 후 아래 명령어들을 순서대로 입력하세요.

### **1.1 Homebrew 및 언어 런타임 설치**

패키지 매니저인 Homebrew가 없다면 설치하고, Git, Python, Node.js를 한 번에 설치하는 명령어입니다.

\# 1\. Homebrew 설치 확인 및 설치  
if \! command \-v brew &\> /dev/null; then  
 /bin/bash \-c "$(curl \-fsSL \[https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh\](https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh))"

    \# Apple Silicon (M1/M2/M3) 환경변수 설정
    if \[\[ $(uname \-m) \== 'arm64' \]\]; then
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' \>\> \~/.zprofile
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi

fi

\# 2\. 필수 패키지 (Git, Python, Node.js) 설치  
brew update  
brew install git python node

\# 3\. 설치 버전 확인  
echo "--------------------------------"  
echo "Git: $(git \--version)"  
echo "Python: $(python3 \--version)"  
echo "Node: $(node \-v)"  
echo "--------------------------------"

### **1.2 Ollama (AI 모델 실행기) 설치**

1. [Ollama 다운로드 페이지](https://ollama.com/download/mac)에서 Mac용 앱을 다운로드하고 설치/실행합니다.
2. 앱이 실행된 상태에서 아래 명령어로 AI 모델을 다운로드합니다.

\# backend/main.py에 설정된 모델 다운로드  
ollama pull gemma3n:e2b

## **2단계: 프로젝트 설치 및 백엔드 실행**

프로젝트 코드를 내려받고 Python 백엔드 서버를 구동합니다.

\# 1\. 프로젝트 다운로드 (본인의 경로에 맞게 수정 가능)  
cd \~/Documents  
git clone \[https://github.com/sssh12/onDocs.git\](https://github.com/sssh12/onDocs.git)  
cd onDocs/backend

\# 2\. 가상환경 생성 및 활성화  
python3 \-m venv venv  
source venv/bin/activate

\# 3\. 파이썬 의존성 라이브러리 설치  
pip install \--upgrade pip  
pip install \-r requirements.txt

\# 4\. 임베딩 모델 ONNX 변환 (최초 1회 필수, 시간 소요됨)  
python export_onnx.py

\# 5\. 백엔드 서버 시작  
python main.py

**중요:** 서버가 실행되면 Application startup complete 메시지가 뜹니다. 이 터미널 창을 **끄지 말고 그대로 두세요.**

## **3단계: 프론트엔드 설정 및 실행**

\*\*새로운 터미널 창(Command \+ T)\*\*을 열고 아래 명령어를 복사해서 실행하세요.

\# 1\. 프론트엔드 폴더로 이동 (경로는 설치 위치에 따라 다를 수 있음)  
cd \~/Documents/onDocs/frontend

\# 2\. Node.js 패키지 설치  
npm install

\# 3\. 프론트엔드 개발 서버 시작  
npm run dev

## **4단계: 접속하기**

모든 설정이 완료되었습니다\! 웹 브라우저(Chrome, Safari 등)를 열고 아래 주소로 접속하세요.

👉 **http://localhost:3000**

## **💡 문제 해결 (Troubleshooting)**

- **command not found: python**: macOS 기본 명령어는 python3입니다. 가상환경(source venv/bin/activate)이 활성화되었는지 확인하세요.
- **Ollama 연결 실패**: 백엔드에서 Connection Refused 오류가 발생하면, 상단 메뉴바에 귀여운 라마 아이콘(Ollama)이 떠 있는지 확인하세요.
- **포트 충돌 (Address already in use)**:
  - 8000번(백엔드) 또는 3000번(프론트) 포트가 이미 사용 중입니다.
  - 기존 터미널을 종료하거나, lsof \-i :8000 명령어로 PID를 찾아 kill \-9 \[PID\]로 종료하세요.
