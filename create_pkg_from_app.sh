#!/bin/bash

# 기존 .app 파일로부터 .pkg 설치 파일을 빠르게 생성하는 스크립트
# 이미 dist/CARRY Route Optimizer.app이 있을 때 사용

set -e

echo "⚡ 기존 .app으로부터 .pkg 파일 빠르게 생성"

APP_PATH="dist/CARRY Route Optimizer.app"

# .app 파일 존재 확인
if [[ ! -d "$APP_PATH" ]]; then
    echo "❌ 오류: $APP_PATH이 없습니다."
    echo "💡 먼저 './build_mac_app.sh'를 실행하여 .app 파일을 생성하세요."
    exit 1
fi

echo "✅ 기존 .app 파일 확인: $APP_PATH"

# 임시 디렉토리 설정
PKG_ROOT="pkg_temp"
rm -rf "$PKG_ROOT" *.pkg

# Applications 폴더 구조 생성
mkdir -p "$PKG_ROOT/Applications"
cp -R "$APP_PATH" "$PKG_ROOT/Applications/"

echo "📦 .pkg 파일 생성 중..."

# .pkg 파일 생성
pkgbuild \
    --root "$PKG_ROOT" \
    --identifier "com.carry.routeoptimizer.installer" \
    --version "1.0.0" \
    --install-location "/" \
    "CARRY-Route-Optimizer-Installer.pkg"

# 결과 확인
if [[ -f "CARRY-Route-Optimizer-Installer.pkg" ]]; then
    echo "✅ 설치 파일 생성 완료!"
    echo ""
    echo "📋 파일 정보:"
    echo "   파일: CARRY-Route-Optimizer-Installer.pkg"
    echo "   크기: $(du -sh CARRY-Route-Optimizer-Installer.pkg | cut -f1)"
    echo ""
    echo "💡 사용법:"
    echo "   1. .pkg 파일 더블클릭"
    echo "   2. 설치 마법사 따라하기"
    echo "   3. Applications 폴더에 자동 설치"
    echo ""
    echo "🔐 첫 실행 시:"
    echo "   - 우클릭 → '열기' → '열기' (보안 경고 무시)"
else
    echo "❌ .pkg 파일 생성 실패"
fi

# 정리
rm -rf "$PKG_ROOT"

echo "🎉 완료!"