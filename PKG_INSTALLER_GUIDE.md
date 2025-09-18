# 🍎 macOS .pkg 설치 파일 생성 가이드

## 개요
Windows의 `setup.exe`처럼 더블클릭으로 설치 가능한 macOS `.pkg` 파일을 생성합니다.

## 📦 사용 방법

### 방법 1: 전체 빌드 (처음부터)
```bash
# 전체 프로세스: .app 생성 → .pkg 생성
./build_pkg_installer.sh
```

### 방법 2: 빠른 생성 (기존 .app 있는 경우)
```bash
# 이미 dist/CARRY Route Optimizer.app이 있다면
./create_pkg_from_app.sh
```

## 🎯 결과물
- **파일명**: `CARRY-Route-Optimizer-Installer.pkg`
- **크기**: 약 50-100MB
- **설치 위치**: `/Applications/CARRY Route Optimizer.app`

## 💡 최종 사용자 설치 방법

1. **다운로드**: `.pkg` 파일을 Mac으로 전송
2. **더블클릭**: `CARRY-Route-Optimizer-Installer.pkg` 실행
3. **설치 마법사**:
   - "계속" 클릭
   - "설치" 클릭
   - 관리자 암호 입력
4. **설치 완료**: Applications 폴더에 자동 설치
5. **실행**: Spotlight 검색 또는 Applications 폴더에서 실행

## 🔐 보안 알림 해결

### 첫 실행 시 "확인되지 않은 개발자" 경고
1. **앱 우클릭** → "열기"
2. **"열기"** 버튼 클릭
3. 또는 **시스템 설정** → **개인정보 보호 및 보안** → **"확인 없이 열기"** 클릭

### GateKeeper 문제 해결
```bash
# 터미널에서 실행 (필요시)
sudo xattr -r -d com.apple.quarantine "/Applications/CARRY Route Optimizer.app"
```

## 📋 생성된 파일들

```
CARRY-Route-Optimizer-Installer.pkg  ← 최종 배포 파일
dist/CARRY Route Optimizer.app        ← macOS 앱 번들
build_pkg_installer.sh               ← 전체 빌드 스크립트
create_pkg_from_app.sh              ← 빠른 .pkg 생성
```

## ⚡ 장점

✅ **Windows setup.exe와 동일한 경험**
✅ **더블클릭으로 설치**
✅ **자동으로 Applications 폴더에 설치**
✅ **제거도 쉬움** (앱을 휴지통으로 드래그)
✅ **관리자 권한 자동 요청**

## 🚀 배포 방법

1. **직접 전송**: `.pkg` 파일을 이메일/USB로 전송
2. **웹 다운로드**: 웹사이트에 업로드
3. **GitHub Release**: GitHub Releases에 첨부
4. **공유 링크**: 클라우드 스토리지 공유

## 🔧 문제 해결

### "pkgbuild 명령어를 찾을 수 없음"
- macOS 기본 제공 명령어입니다. Xcode Command Line Tools 설치 필요:
```bash
xcode-select --install
```

### ".app 파일 생성 실패"
```bash
# 의존성 확인
pip install -r requirements.txt
pip install PyQt6 py2app

# .env 파일 확인
cp .env.example .env
# .env 파일 편집하여 API 키 설정
```

### "권한 거부" 오류
```bash
# 실행 권한 설정
chmod +x build_pkg_installer.sh
chmod +x create_pkg_from_app.sh
```

## 📞 지원

문제 발생 시:
1. 오류 메시지 확인
2. 로그 파일 검토 (`logs/` 폴더)
3. 의존성 재설치: `pip install -r requirements.txt`
4. 가상환경 초기화 후 재시도