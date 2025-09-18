#!/bin/bash

# macOS .pkg 설치 파일 생성 스크립트
# CARRY Route Optimizer를 더블클릭으로 설치 가능한 .pkg로 패키징

set -e  # 오류 시 중단

echo "📦 CARRY Route Optimizer .pkg 설치 파일 생성 시작"

# 현재 디렉토리 확인
if [[ ! -f "main.py" ]]; then
    echo "❌ 오류: main.py 파일이 없습니다. 프로젝트 루트 디렉토리에서 실행해주세요."
    exit 1
fi

# 1단계: 먼저 .app 번들 생성
echo "🔨 1단계: .app 번들 생성..."
chmod +x build_mac_app.sh
./build_mac_app.sh

# .app 번들 생성 확인
if [[ ! -d "dist/CARRY Route Optimizer.app" ]]; then
    echo "❌ .app 번들 생성 실패. build_mac_app.sh 실행을 확인하세요."
    exit 1
fi

# 2단계: .pkg 설치 파일용 디렉토리 구조 생성
echo "🏗️  2단계: 설치 패키지 구조 생성..."

# 임시 디렉토리 정리 및 생성
PKG_ROOT="pkg_root"
SCRIPTS_DIR="pkg_scripts"
rm -rf "$PKG_ROOT" "$SCRIPTS_DIR" "*.pkg"

# 패키지 루트 디렉토리 생성 (Applications 폴더에 설치될 구조)
mkdir -p "$PKG_ROOT/Applications"

# .app을 패키지 루트로 복사
echo "📁 앱 파일 복사 중..."
cp -R "dist/CARRY Route Optimizer.app" "$PKG_ROOT/Applications/"

# 3단계: 설치 스크립트 생성
echo "📝 3단계: 설치 스크립트 생성..."
mkdir -p "$SCRIPTS_DIR"

# postinstall 스크립트 (설치 후 실행)
cat > "$SCRIPTS_DIR/postinstall" << 'EOF'
#!/bin/bash

APP_NAME="CARRY Route Optimizer.app"
APP_PATH="/Applications/$APP_NAME"

echo "CARRY Route Optimizer 설치 후 처리 중..."

# 실행 권한 설정
if [[ -d "$APP_PATH" ]]; then
    chmod -R 755 "$APP_PATH"
    chown -R root:admin "$APP_PATH"
    echo "✅ 앱 권한 설정 완료"

    # Gatekeeper 문제 해결을 위한 속성 제거 (선택사항)
    xattr -cr "$APP_PATH" 2>/dev/null || true
    echo "✅ 보안 속성 정리 완료"

    # Dock에 추가 알림
    echo "📱 설치 완료: Applications 폴더 또는 Spotlight에서 'CARRY Route Optimizer'를 검색하세요"
else
    echo "⚠️  경고: 앱이 올바르게 설치되지 않았을 수 있습니다"
fi

exit 0
EOF

chmod +x "$SCRIPTS_DIR/postinstall"

# 4단계: .pkg 파일 생성
echo "📦 4단계: .pkg 파일 생성 중..."

PKG_NAME="CARRY-Route-Optimizer-Installer.pkg"
IDENTIFIER="com.carry.routeoptimizer.installer"
VERSION="1.0.0"

# pkgbuild로 패키지 생성
pkgbuild \
    --root "$PKG_ROOT" \
    --scripts "$SCRIPTS_DIR" \
    --identifier "$IDENTIFIER" \
    --version "$VERSION" \
    --install-location "/" \
    "$PKG_NAME"

# 5단계: 결과 확인
if [[ -f "$PKG_NAME" ]]; then
    echo "✅ .pkg 설치 파일 생성 완료!"
    echo ""
    echo "🎉 성공!"
    echo "📋 설치 파일 정보:"
    echo "   파일명: $PKG_NAME"
    echo "   위치: $(pwd)/$PKG_NAME"
    echo "   크기: $(du -sh "$PKG_NAME" | cut -f1)"
    echo ""
    echo "💡 사용 방법:"
    echo "   1. $PKG_NAME 파일을 더블클릭"
    echo "   2. '계속' → '설치' 클릭"
    echo "   3. 관리자 암호 입력"
    echo "   4. 자동으로 Applications 폴더에 설치됨"
    echo "   5. Spotlight에서 'CARRY Route Optimizer' 검색하여 실행"
    echo ""
    echo "🔐 보안 참고:"
    echo "   - 최초 실행 시 'App Store에서 다운로드하지 않음' 경고가 나올 수 있습니다"
    echo "   - '시스템 설정 > 개인정보 보호 및 보안'에서 '확인 없이 열기' 클릭"
    echo "   - 또는 앱을 우클릭 → '열기' → '열기' 확인"
    echo ""

    # 패키지 내용 검증
    echo "🔍 패키지 내용 검증:"
    pkgutil --payload-files "$PKG_NAME" | head -10
    echo ""

    # 설치 테스트 제안
    echo "🧪 설치 테스트:"
    echo "   sudo installer -pkg '$PKG_NAME' -target /"
    echo "   (실제 설치됨 - 테스트 시 주의)"

else
    echo "❌ .pkg 파일 생성 실패"
    echo "📋 오류 분석을 위한 정보:"
    echo "   - PKG_ROOT 내용: $(ls -la "$PKG_ROOT" 2>/dev/null || echo "없음")"
    echo "   - SCRIPTS_DIR 내용: $(ls -la "$SCRIPTS_DIR" 2>/dev/null || echo "없음")"
    exit 1
fi

# 6단계: 임시 파일 정리
echo "🧹 임시 파일 정리..."
rm -rf "$PKG_ROOT" "$SCRIPTS_DIR"

echo "🎯 .pkg 설치 파일 생성 완료!"
echo "📁 생성된 파일: $PKG_NAME"