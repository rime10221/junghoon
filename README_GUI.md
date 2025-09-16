# Route Optimizer GUI

배송 경로 최적화 프로그램의 그래픽 사용자 인터페이스(GUI) 버전입니다.

## 기능

- 📁 **폴더 기반 배치 처리**: 입력 폴더의 모든 Excel 파일을 한 번에 처리
- 📊 **실시간 진행 상황**: 처리 진행률과 현재 작업 파일 표시
- 📋 **상세 로그**: 터미널 로그를 GUI에서 실시간 확인
- ⚙️ **우선순위 설정**: 시간/거리/추천 최적화 모드 선택
- 🚀 **원클릭 실행**: 복잡한 명령어 없이 간편한 GUI 조작

## 시스템 요구사항

### 필수 설치 프로그램
- **Node.js** 16.0 이상 ([다운로드](https://nodejs.org))
- **Python** 3.8 이상 ([다운로드](https://python.org))

### API 키 설정
카카오 모빌리티 API 키가 필요합니다:
1. `.env` 파일에 `KAKAO_API_KEY=your_api_key` 추가
2. 또는 시스템 환경변수로 설정

## 설치 및 실행

### 1. 자동 설정 (권장)
```bash
# Windows
setup_gui.bat

# 또는 수동으로
npm install
pip install -r requirements.txt
```

### 2. 개발 모드 실행
```bash
npm run dev
```

### 3. 일반 실행
```bash
npm start
```

### 4. 설치 파일 빌드
```bash
# Windows
build_installer.bat

# 또는 수동으로
npm run build
```

## 사용 방법

1. **입력 폴더 선택**: Excel 파일들이 있는 폴더 선택
2. **출력 폴더 선택**: 결과 파일을 저장할 폴더 선택
3. **최적화 우선순위 설정**:
   - 시간 우선 (기본): 빠른 경로 우선
   - 거리 우선: 짧은 거리 우선
   - 추천: 균형잡힌 최적화
4. **배치 처리 시작**: 모든 Excel 파일 일괄 처리
5. **결과 확인**: 출력 폴더에서 최적화된 경로 파일 확인

## 프로젝트 구조

```
├── gui/                    # Electron GUI 파일
│   ├── main.js            # 메인 프로세스
│   ├── preload.js         # 보안 브리지
│   ├── index.html         # GUI 인터페이스
│   ├── styles.css         # 스타일시트
│   ├── renderer.js        # 렌더러 프로세스
│   └── assets/            # 아이콘 등 리소스
├── src/                   # Python 백엔드 로직
├── batch_process.py       # 배치 처리 스크립트
├── main.py               # CLI 버전 메인
├── package.json          # Node.js 설정
├── requirements.txt      # Python 의존성
└── README_GUI.md         # 이 문서
```

## 기술 스택

- **Frontend**: Electron, HTML5, CSS3, JavaScript
- **Backend**: Python 3.8+
- **API**: 카카오 모빌리티 API
- **Build**: electron-builder (Windows NSIS)

## 문제 해결

### 일반적인 문제

1. **"KAKAO_API_KEY가 설정되지 않았습니다"**
   - `.env` 파일에 API 키 추가 또는 환경변수 설정

2. **"Python을 찾을 수 없습니다"**
   - Python이 시스템 PATH에 추가되었는지 확인
   - `python --version` 명령어로 설치 확인

3. **Excel 파일 처리 오류**
   - Excel 파일이 올바른 형식인지 확인
   - 필요한 컬럼(주소, 고객명 등)이 있는지 확인

4. **API 호출 제한**
   - 카카오 API 할당량 확인
   - 처리 간격을 늘려서 재시도

### 로그 확인
- GUI의 로그 패널에서 실시간 처리 상황 확인
- 개발 모드(`npm run dev`)에서 DevTools로 상세 디버깅

## 빌드 및 배포

### 개발 빌드
```bash
npm run pack  # 압축 없이 실행 파일만
```

### 배포용 빌드
```bash
npm run build  # NSIS 설치 파일 생성
```

생성된 설치 파일은 `dist/` 폴더에 저장됩니다.

## 라이선스

MIT License - 자유롭게 사용, 수정, 배포 가능

## 지원

문제가 발생하면 다음을 확인해주세요:
1. 시스템 요구사항 충족 여부
2. API 키 올바른 설정
3. 인터넷 연결 상태
4. Excel 파일 형식 및 내용

추가 도움이 필요하면 이슈를 등록해주세요.