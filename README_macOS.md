# 🍎 CARRY Route Optimizer - macOS 앱 생성 가이드

## 📋 개요

Windows에서 개발된 CARRY Route Optimizer를 macOS용 더블클릭 실행 가능한 `.app` 번들로 패키징하는 방법입니다.

## 🎯 최종 결과물

- **CARRY Route Optimizer.app**: 더블클릭으로 실행되는 macOS 앱
- **CARRY-Route-Optimizer-v1.0.0.dmg**: 배포용 DMG 이미지
- 터미널 사용 없이 GUI로만 사용 가능

## 🔧 빌드 과정 (macOS에서 실행)

### 1단계: 프로젝트 파일 macOS로 복사
```bash
# 전체 프로젝트 폴더를 macOS로 복사
# - main.py
# - src/ 폴더
# - requirements.txt
# - .env 파일 (API 키 설정)
# - gui_perfect.py (완성된 PyQt6 GUI)
# - setup_mac.py
# - build_mac_app.sh
# - create_dmg.sh
```

### 2단계: 실행 권한 부여
```bash
chmod +x build_mac_app.sh
chmod +x create_dmg.sh
```

### 3단계: .app 번들 생성
```bash
./build_mac_app.sh
```

### 4단계: 배포용 DMG 생성 (선택사항)
```bash
./create_dmg.sh
```

## 📦 생성되는 파일들

```
dist/
├── CARRY Route Optimizer.app    # 실행 파일
└── build/                       # 빌드 임시 파일

CARRY-Route-Optimizer-v1.0.0.dmg # 배포용 DMG (create_dmg.sh 실행 시)
```

## 🚀 사용자 배포 방법

### 방법 1: .app 파일 직접 배포
1. `dist/CARRY Route Optimizer.app`을 사용자에게 전달
2. 사용자가 Applications 폴더로 드래그
3. 더블클릭으로 실행

### 방법 2: DMG 파일 배포 (권장)
1. `CARRY-Route-Optimizer-v1.0.0.dmg` 파일 전달
2. 사용자가 DMG 더블클릭하여 마운트
3. 앱을 Applications 폴더로 드래그
4. DMG 언마운트 후 사용

## 🎨 GUI 기능 (gui_perfect.py - 완전한 성능)

### 핵심 개선사항
- **실시간 진행률 바**: 실제 작업 현황에 따라 정확히 움직임
- **터미널 로그 동기화**: 모든 DEBUG/INFO/WARNING 로그 GUI에서 확인 가능
- **다중 파일 지원**: 여러 파일 처리 시 정확한 진행률 계산
- **실제 작업 상황 반영**: 단계별 실시간 상태 업데이트

### 메인 화면 구조 (2-Panel Layout)
**왼쪽 패널**:
- 📁 입력 폴더 선택 (Excel 파일들)
- 📤 출력 폴더 선택 (결과 파일들)
- 🔑 카카오 API 키 입력 (환경변수 사용 가능)
- 🎯 최적화 우선순위 (시간/거리/추천)
- 🚀 배치 처리 시작/중단 버튼
- 📊 실시간 처리 상태 및 정확한 진행률 표시

**오른쪽 패널**:
- 📋 완전한 터미널 로그 동기화
- 모든 DEBUG 레벨까지 포함된 상세 로그
- 타임스탬프가 포함된 실시간 로그
- 로그 지우기 기능

### GUI 특징
- **완전한 성능**: Electron GUI와 100% 동일한 기능과 성능
- **Modern Design**: 그라데이션 배경과 둥근 모서리
- **정확한 피드백**: 실제 작업에 따른 진행률 바 업데이트
- **완벽한 로그 동기화**: 터미널과 완전히 동일한 모든 로그 표시
- **상태 인디케이터**: 준비/처리중/완료/오류 상태 실시간 표시
- **직관적 UX**: 폴더 선택과 파일 목록 미리보기

### 실행 과정
1. **입력 폴더 선택**: Excel 파일들이 있는 폴더 선택
2. **출력 폴더 선택**: 최적화 결과를 저장할 폴더 선택
3. **API 키 설정**: 카카오 모빌리티 API 키 입력 (선택사항)
4. **최적화 설정**: 시간/거리/추천 중 우선순위 선택
5. **배치 처리 시작**: 모든 Excel 파일을 순차적으로 처리
6. **실시간 모니터링**: 진행률과 로그를 통한 진행 상황 확인
7. **완료**: 최적화된 Excel 파일들이 출력 폴더에 저장

## ⚠️ 주의사항

### macOS 보안 설정
- 처음 실행 시 "개발자를 확인할 수 없습니다" 경고 발생 가능
- 해결방법: 시스템 환경설정 > 보안 및 개인 정보 보호 > 일반 > "확인 없이 열기"

### API 키 설정
- .env 파일에 KAKAO_REST_API_KEY 설정 필요
- 앱 내부에 포함되므로 빌드 전에 설정

### 시스템 요구사항
- macOS 10.14 (Mojave) 이상
- 인터넷 연결 (카카오 맵 API 사용)

## 🔍 트러블슈팅

### 빌드 오류
```bash
# Python 버전 확인
python3 --version  # 3.8 이상 필요

# py2app 재설치
pip install --upgrade py2app

# 의존성 재설치
pip install -r requirements.txt
```

### 실행 오류
```bash
# 앱 실행 테스트
open "dist/CARRY Route Optimizer.app"

# 콘솔에서 오류 확인
tail -f /var/log/system.log | grep "CARRY Route Optimizer"
```

### 권한 문제
```bash
# 실행 권한 부여
chmod +x "dist/CARRY Route Optimizer.app/Contents/MacOS/mac_gui"

# 전체 앱 권한 확인
xattr -d com.apple.quarantine "dist/CARRY Route Optimizer.app"
```

## 📚 추가 개선 사항

### 아이콘 추가
```bash
# .icns 파일 생성 후 setup_mac.py에서 경로 지정
'iconfile': 'app_icon.icns'
```

### 코드 사이닝 (배포용)
```bash
# Apple Developer 계정 필요
codesign --force --sign "Developer ID Application: Your Name" "CARRY Route Optimizer.app"
```

### 자동 업데이트
```python
# Sparkle 프레임워크 통합으로 자동 업데이트 기능 추가
```

## 🎉 완료!

이제 macOS 사용자들이 터미널 없이 더블클릭만으로 CARRY Route Optimizer를 사용할 수 있습니다!

---

**개발**: CARRY Route Optimizer Team
**버전**: 1.0.0
**플랫폼**: macOS 10.14+
**라이선스**: All rights reserved