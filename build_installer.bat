@echo off
echo ========================================
echo Route Optimizer GUI 설치 파일 빌드
echo ========================================

:: 빌드 전 의존성 확인
echo 📦 의존성 확인 중...
npm install
if %errorlevel% neq 0 (
    echo 오류: 의존성 설치에 실패했습니다.
    pause
    exit /b 1
)

:: 이전 빌드 정리
echo 🧹 이전 빌드 파일 정리 중...
if exist dist rmdir /s /q dist

:: 설치 파일 빌드
echo 🔨 설치 파일 빌드 중...
npm run build
if %errorlevel% neq 0 (
    echo 오류: 빌드에 실패했습니다.
    pause
    exit /b 1
)

echo.
echo ✅ 빌드 완료!
echo 📁 설치 파일은 dist 폴더에 생성되었습니다.
echo.

:: 빌드 결과 표시
if exist "dist\*.exe" (
    echo 생성된 설치 파일:
    dir /b dist\*.exe
) else (
    echo ⚠️  설치 파일(.exe)을 찾을 수 없습니다.
    echo dist 폴더를 확인해주세요.
)

echo.
pause