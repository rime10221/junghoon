#!/bin/bash

# 즉시 PKG 생성 스크립트 - GitHub Actions 없이
echo "🚀 즉시 PKG 생성 시작 (로컬 전용)"

# 앱 번들 생성
APP_NAME="CARRY Route Optimizer.app"
rm -rf "$APP_NAME" *.pkg

echo "📱 앱 번들 생성 중..."
mkdir -p "$APP_NAME/Contents/MacOS"
mkdir -p "$APP_NAME/Contents/Resources"

# Info.plist
cat > "$APP_NAME/Contents/Info.plist" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>start_app</string>
    <key>CFBundleIdentifier</key>
    <string>com.carry.routeoptimizer</string>
    <key>CFBundleName</key>
    <string>CARRY Route Optimizer</string>
    <key>CFBundleVersion</key>
    <string>1.0.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
</dict>
</plist>
EOF

# 실행 스크립트
cat > "$APP_NAME/Contents/MacOS/start_app" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")/../Resources"
python3 gui_perfect.py
EOF

chmod +x "$APP_NAME/Contents/MacOS/start_app"

# 파일 복사
cp gui_perfect.py "$APP_NAME/Contents/Resources/"
cp main.py "$APP_NAME/Contents/Resources/"
cp .env "$APP_NAME/Contents/Resources/"
cp -r src "$APP_NAME/Contents/Resources/"

echo "✅ 앱 번들 완성"

# PKG 생성
echo "📦 PKG 생성 중..."
mkdir -p pkg_root/Applications
cp -R "$APP_NAME" pkg_root/Applications/

pkgbuild \
  --root pkg_root \
  --identifier com.carry.routeoptimizer \
  --version 1.0.0 \
  --install-location / \
  "CARRY-Route-Optimizer-LOCAL.pkg"

if [[ -f "CARRY-Route-Optimizer-LOCAL.pkg" ]]; then
  echo "🎉 PKG 생성 완료!"
  echo "파일: CARRY-Route-Optimizer-LOCAL.pkg"
  echo "크기: $(du -sh CARRY-Route-Optimizer-LOCAL.pkg | cut -f1)"
  ls -la *.pkg
else
  echo "❌ PKG 생성 실패"
fi

rm -rf pkg_root
echo "✅ 완료!"