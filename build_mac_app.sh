#!/bin/bash

# macOS .app 번들 생성 스크립트
# CARRY Route Optimizer를 macOS 앱으로 패키징

set -e  # 오류 시 중단

echo "🍎 CARRY Route Optimizer macOS 앱 빌드 시작"

# 현재 디렉토리 확인
if [[ ! -f "main.py" ]]; then
    echo "❌ 오류: main.py 파일이 없습니다. 프로젝트 루트 디렉토리에서 실행해주세요."
    exit 1
fi

# Python 버전 확인
echo "📋 Python 버전 확인..."
python3 --version

# 가상환경 생성 (있다면 제거 후 재생성)
echo "🔧 가상환경 설정..."
if [[ -d "venv_mac" ]]; then
    rm -rf venv_mac
fi

python3 -m venv venv_mac
source venv_mac/bin/activate

# 필수 패키지 업그레이드
echo "📦 기본 패키지 업그레이드..."
pip install --upgrade pip setuptools wheel

# py2app 설치
echo "📦 py2app 설치..."
pip install py2app

# 프로젝트 의존성 설치
echo "📦 프로젝트 의존성 설치..."
pip install -r requirements.txt

# PyQt6 설치 (macOS용 GUI)
echo "📦 PyQt6 설치..."
pip install PyQt6

# .env 파일 확인
if [[ ! -f ".env" ]]; then
    echo "❌ 오류: .env 파일이 필요합니다."
    echo "💡 GitHub에 .env 파일이 올라가 있는지 확인하세요."
    exit 1
fi

echo "📝 .env 파일 확인됨"

# 이전 빌드 정리
echo "🧹 이전 빌드 파일 정리..."
rm -rf build dist *.egg-info

# .app 번들 생성
echo "🔨 .app 번들 생성 중..."
python setup_mac.py py2app

# 빌드 결과 확인
if [[ -d "dist/gui_perfect.app" ]]; then
    echo "✅ .app 번들 생성 완료!"
    echo "📁 위치: $(pwd)/dist/gui_perfect.app"

    # 앱 이름 변경
    if [[ ! -d "dist/CARRY Route Optimizer.app" ]]; then
        mv "dist/gui_perfect.app" "dist/CARRY Route Optimizer.app"
        echo "📝 앱 이름 변경: CARRY Route Optimizer.app"
    fi

    # 앱 정보 출력
    echo ""
    echo "🎉 빌드 성공!"
    echo "📋 앱 정보:"
    echo "   이름: CARRY Route Optimizer.app"
    echo "   위치: $(pwd)/dist/"
    echo "   크기: $(du -sh "dist/CARRY Route Optimizer.app" | cut -f1)"
    echo ""
    echo "💡 사용 방법:"
    echo "   1. dist/CARRY Route Optimizer.app을 Applications 폴더로 복사"
    echo "   2. 더블클릭으로 실행"
    echo "   3. Excel 파일 선택하여 경로 최적화 실행"
    echo ""
    echo "📦 배포용 DMG 생성을 원하시면 'create_dmg.sh'를 실행하세요."

    # 실행 가능 여부 테스트 (GitHub Actions에서는 스킵)
    if [[ -z "$GITHUB_ACTIONS" ]]; then
        echo "🧪 앱 실행 테스트..."
        open "dist/CARRY Route Optimizer.app" --args --test
    else
        echo "🧪 GitHub Actions 환경에서는 실행 테스트를 스킵합니다."
    fi

else
    echo "❌ .app 번들 생성 실패"
    echo "📋 로그 확인:"
    ls -la dist/ || echo "dist 폴더가 생성되지 않았습니다."
    exit 1
fi

# 가상환경 비활성화
deactivate

echo "🎯 macOS 앱 빌드 완료!"