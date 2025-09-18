#!/bin/bash

# CARRY Route Optimizer - 최종 PKG 빌드 스크립트
# 확실하게 작동하는 단순한 방식

set -e  # 오류 시 중단

echo "🚀 CARRY Route Optimizer PKG 빌드 시작"
echo "======================================"

# 환경 확인
echo "📋 환경 확인..."
echo "OS: $(uname -a)"
echo "Python: $(which python3) $(python3 --version 2>&1)"
echo "Working Directory: $(pwd)"

# 필수 파일 확인
echo ""
echo "📁 필수 파일 확인..."
REQUIRED_FILES=("gui_perfect.py" "main.py" ".env" "src")
for file in "${REQUIRED_FILES[@]}"; do
    if [[ -e "$file" ]]; then
        echo "✅ $file - 존재"
    else
        echo "❌ $file - 없음"
        exit 1
    fi
done

# Python 패키지 확인
echo ""
echo "📦 Python 패키지 확인..."
python3 -c "import PyQt6; print('✅ PyQt6 - OK')" 2>/dev/null || {
    echo "⚠️ PyQt6 없음, 설치 시도..."
    pip3 install PyQt6
}

python3 -c "import pandas; print('✅ pandas - OK')" 2>/dev/null || {
    echo "⚠️ pandas 없음, 설치 시도..."
    pip3 install pandas
}

# 이전 빌드 정리
echo ""
echo "🧹 이전 빌드 정리..."
rm -rf "CARRY Route Optimizer.app" *.pkg pkg_*

# 앱 번들 생성
echo ""
echo "🏗️ 앱 번들 생성 중..."
APP_NAME="CARRY Route Optimizer.app"

# 디렉토리 구조 생성
mkdir -p "$APP_NAME/Contents/MacOS"
mkdir -p "$APP_NAME/Contents/Resources"

# Info.plist 생성
cat > "$APP_NAME/Contents/Info.plist" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>launcher</string>
    <key>CFBundleIdentifier</key>
    <string>com.carry.routeoptimizer</string>
    <key>CFBundleName</key>
    <string>CARRY Route Optimizer</string>
    <key>CFBundleDisplayName</key>
    <string>CARRY Route Optimizer</string>
    <key>CFBundleVersion</key>
    <string>1.0.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
EOF

echo "✅ Info.plist 생성 완료"

# 런처 스크립트 생성
cat > "$APP_NAME/Contents/MacOS/launcher" << 'EOF'
#!/bin/bash

# CARRY Route Optimizer 런처 스크립트
echo "CARRY Route Optimizer 시작 중..."

# Resources 디렉토리로 이동
RESOURCE_DIR="$(dirname "$0")/../Resources"
cd "$RESOURCE_DIR"

# Python 경로 설정
export PYTHONPATH="$PWD:$PYTHONPATH"

# Python 실행
if command -v python3 >/dev/null 2>&1; then
    python3 gui_perfect.py "$@"
elif command -v python >/dev/null 2>&1; then
    python gui_perfect.py "$@"
else
    echo "Python을 찾을 수 없습니다."
    exit 1
fi
EOF

chmod +x "$APP_NAME/Contents/MacOS/launcher"
echo "✅ 런처 스크립트 생성 완료"

# 리소스 파일 복사
echo "📂 리소스 파일 복사 중..."
cp gui_perfect.py "$APP_NAME/Contents/Resources/"
cp main.py "$APP_NAME/Contents/Resources/"
cp .env "$APP_NAME/Contents/Resources/"
cp -r src "$APP_NAME/Contents/Resources/"

echo "✅ 앱 번들 생성 완료"

# 앱 번들 검증
echo ""
echo "🔍 앱 번들 검증..."
if [[ -d "$APP_NAME" ]]; then
    echo "✅ 앱 번들 구조:"
    find "$APP_NAME" -type f | head -10
    echo "앱 크기: $(du -sh "$APP_NAME" | cut -f1)"
else
    echo "❌ 앱 번들 생성 실패"
    exit 1
fi

# PKG 생성
echo ""
echo "📦 PKG 인스톨러 생성 중..."
PKG_NAME="CARRY-Route-Optimizer-$(date +%Y%m%d).pkg"

# 패키지 페이로드 디렉토리 생성
mkdir -p pkg_payload/Applications
cp -R "$APP_NAME" pkg_payload/Applications/

# PKG 빌드
pkgbuild \
    --root pkg_payload \
    --identifier com.carry.routeoptimizer.installer \
    --version 1.0.0 \
    --install-location / \
    "$PKG_NAME"

# PKG 검증
if [[ -f "$PKG_NAME" ]]; then
    echo ""
    echo "🎉 PKG 생성 성공!"
    echo "======================================="
    echo "📁 파일: $PKG_NAME"
    echo "📊 크기: $(du -sh "$PKG_NAME" | cut -f1)"
    echo "🏷️ 식별자: com.carry.routeoptimizer.installer"
    echo ""
    echo "💡 설치 방법:"
    echo "   1. $PKG_NAME 파일을 더블클릭"
    echo "   2. 설치 마법사 따라하기"
    echo "   3. Applications 폴더에서 'CARRY Route Optimizer' 실행"
    echo ""
    echo "🔐 보안 알림이 나타나면:"
    echo "   - 시스템 설정 > 개인정보 보호 및 보안 > 확인 없이 열기"
    echo "   - 또는 앱을 우클릭 > 열기 > 열기"
    echo ""

    # 패키지 내용 확인
    echo "📋 패키지 내용:"
    pkgutil --payload-files "$PKG_NAME" | head -5
    echo "..."

else
    echo "❌ PKG 생성 실패"
    exit 1
fi

# 정리
echo ""
echo "🧹 임시 파일 정리..."
rm -rf pkg_payload

echo "✅ 빌드 완료! 🎯"