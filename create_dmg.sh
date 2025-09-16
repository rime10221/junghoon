#!/bin/bash

# macOS DMG 이미지 생성 스크립트
# 배포용 DMG 파일 생성

set -e

echo "💿 CARRY Route Optimizer DMG 생성 시작"

# .app 파일 존재 확인
APP_PATH="dist/CARRY Route Optimizer.app"
if [[ ! -d "$APP_PATH" ]]; then
    echo "❌ 오류: $APP_PATH가 없습니다."
    echo "   먼저 './build_mac_app.sh'를 실행하여 .app 번들을 생성하세요."
    exit 1
fi

# 변수 설정
APP_NAME="CARRY Route Optimizer"
DMG_NAME="CARRY-Route-Optimizer-v1.0.0"
DMG_DIR="dmg_temp"
VOLUME_NAME="CARRY Route Optimizer"

# 이전 임시 파일 정리
echo "🧹 임시 파일 정리..."
rm -rf "$DMG_DIR"
rm -f "${DMG_NAME}.dmg"

# 임시 디렉토리 생성
echo "📁 임시 디렉토리 생성..."
mkdir -p "$DMG_DIR"

# .app 파일 복사
echo "📋 앱 파일 복사..."
cp -R "$APP_PATH" "$DMG_DIR/"

# Applications 폴더 심볼릭 링크 생성
echo "🔗 Applications 링크 생성..."
ln -s /Applications "$DMG_DIR/Applications"

# README 파일 생성
echo "📝 README 파일 생성..."
cat > "$DMG_DIR/README.txt" << 'EOF'
CARRY Route Optimizer v1.0.0

🚀 설치 방법:
1. "CARRY Route Optimizer.app"을 "Applications" 폴더로 드래그하세요
2. Launchpad나 Applications 폴더에서 앱을 찾아 실행하세요

📋 사용 방법:
1. Excel 파일을 선택하세요 (주문 데이터가 포함된 파일)
2. 최적화 설정을 선택하세요
3. "경로 최적화 실행" 버튼을 클릭하세요
4. 결과 파일이 자동으로 생성됩니다

⚙️ 시스템 요구사항:
- macOS 10.14 (Mojave) 이상
- 인터넷 연결 (카카오 맵 API 사용)

❓ 문제 해결:
- "개발자를 확인할 수 없습니다" 오류 시:
  시스템 환경설정 > 보안 및 개인 정보 보호 > 일반 > "확인 없이 열기"

- API 키 오류 시:
  애플리케이션 패키지 내용 보기 > Contents > Resources > .env 파일에서 API 키 설정

📞 지원:
문제가 발생하면 개발팀에 문의하세요.

Copyright © 2024 CARRY. All rights reserved.
EOF

# DMG 이미지 생성 (create-dmg 도구 사용)
echo "💿 DMG 이미지 생성..."

# create-dmg 설치 여부 확인
if ! command -v create-dmg &> /dev/null; then
    echo "📦 create-dmg 설치 중..."
    if command -v brew &> /dev/null; then
        brew install create-dmg
    else
        echo "❌ Homebrew가 설치되어 있지 않습니다."
        echo "   수동 DMG 생성 방법:"
        echo "   1. Disk Utility 실행"
        echo "   2. 파일 > 새로운 이미지 > 폴더에서 이미지"
        echo "   3. $DMG_DIR 폴더 선택"
        echo "   4. 이미지 포맷: 읽기 전용"
        exit 1
    fi
fi

# DMG 생성 옵션 설정
CREATE_DMG_OPTIONS=(
    --volname "$VOLUME_NAME"
    --volicon "app_icon.icns"  # 아이콘 파일이 있다면
    --window-pos 200 120
    --window-size 600 400
    --icon-size 100
    --icon "$APP_NAME.app" 150 185
    --hide-extension "$APP_NAME.app"
    --app-drop-link 450 185
    --background "dmg_background.png"  # 배경 이미지가 있다면
    --no-internet-enable
)

# 아이콘과 배경 파일이 없다면 해당 옵션 제거
if [[ ! -f "app_icon.icns" ]]; then
    CREATE_DMG_OPTIONS=("${CREATE_DMG_OPTIONS[@]/--volicon*}")
fi

if [[ ! -f "dmg_background.png" ]]; then
    CREATE_DMG_OPTIONS=("${CREATE_DMG_OPTIONS[@]/--background*}")
fi

# DMG 생성 실행
create-dmg "${CREATE_DMG_OPTIONS[@]}" "${DMG_NAME}.dmg" "$DMG_DIR"

# 결과 확인
if [[ -f "${DMG_NAME}.dmg" ]]; then
    echo ""
    echo "✅ DMG 생성 완료!"
    echo "📋 DMG 정보:"
    echo "   파일명: ${DMG_NAME}.dmg"
    echo "   위치: $(pwd)/${DMG_NAME}.dmg"
    echo "   크기: $(du -sh "${DMG_NAME}.dmg" | cut -f1)"
    echo ""
    echo "🎉 배포 준비 완료!"
    echo "💡 사용자에게 배포 방법:"
    echo "   1. ${DMG_NAME}.dmg 파일 다운로드"
    echo "   2. 더블클릭하여 마운트"
    echo "   3. 앱을 Applications 폴더로 드래그"
    echo "   4. DMG 언마운트 후 사용"

    # 자동으로 DMG 열기
    echo "📂 DMG 파일 열기..."
    open "${DMG_NAME}.dmg"
else
    echo "❌ DMG 생성 실패"
    exit 1
fi

# 임시 파일 정리
echo "🧹 임시 파일 정리..."
rm -rf "$DMG_DIR"

echo "🎯 DMG 생성 완료!"