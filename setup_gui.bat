@echo off
echo ========================================
echo Route Optimizer GUI 설정 및 실행
echo ========================================

:: Node.js 설치 확인
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 오류: Node.js가 설치되지 않았습니다.
    echo Node.js를 https://nodejs.org에서 다운로드하여 설치하세요.
    pause
    exit /b 1
)

:: Python 설치 확인
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 오류: Python이 설치되지 않았습니다.
    echo Python을 https://python.org에서 다운로드하여 설치하세요.
    pause
    exit /b 1
)

echo ✅ Node.js와 Python이 설치되어 있습니다.

:: Python 의존성 설치
echo.
echo 📦 Python 의존성 설치 중...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo 오류: Python 패키지 설치에 실패했습니다.
    pause
    exit /b 1
)

:: Node.js 의존성 설치
echo.
echo 📦 Node.js 의존성 설치 중...
npm install
if %errorlevel% neq 0 (
    echo 오류: Node.js 패키지 설치에 실패했습니다.
    pause
    exit /b 1
)

echo.
echo ✅ 설정 완료!
echo.
echo 다음 명령어로 애플리케이션을 실행할 수 있습니다:
echo   개발 모드: npm run dev
echo   일반 실행: npm start
echo   빌드하기: npm run build
echo.
pause