# 🍎 macOS .app 파일 생성 가이드

## 🚀 한번에 실행하기

macOS에서 터미널을 열고 다음 명령어들을 순서대로 실행하세요:

```bash
# 1. 프로젝트 폴더로 이동
cd /path/to/your/project

# 2. 실행 권한 부여
chmod +x build_mac_app.sh

# 3. .app 파일 생성
./build_mac_app.sh
```

## 📦 결과물

성공하면 다음 파일이 생성됩니다:
```
dist/CARRY Route Optimizer.app
```

## 🎯 사용법

1. `CARRY Route Optimizer.app`을 Applications 폴더로 복사
2. 더블클릭으로 실행
3. GUI에서 Excel 파일 처리

## ⚡ gui_perfect.py 특징

- **실시간 진행률**: 실제 작업에 따라 정확히 움직임
- **완전한 로그 동기화**: 터미널 로그와 100% 동일
- **다중 파일 지원**: 여러 파일도 정확한 진행률 표시
- **DEBUG 로그 포함**: 모든 상세 로그 GUI에서 확인 가능

## 🔧 문제 해결

빌드 실패 시:
```bash
# Python 버전 확인 (3.8+ 필요)
python3 --version

# 의존성 재설치
pip install --upgrade py2app PyQt6
```

## ✅ 완료!

이제 macOS 사용자에게 .app 파일 하나만 주면 끝입니다!