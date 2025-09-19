# GitHub Actions macOS Runner 대기열 문제 해결 가이드

## 🚨 현재 상황 분석

**문제**: GitHub Actions macOS runner가 20시간 동안 "Queued" 상태로 멈춤
**원인**: GitHub Actions 무료 계정의 macOS runner 제약사항

## 📊 GitHub Actions 제약사항 분석

### 무료 계정 제한사항
- **월 사용량**: 2,000분 (33시간)
- **macOS 비용**: Linux 대비 10배 (1분 사용 = 10분 차감)
- **실제 macOS 사용 가능**: 월 200분 (3.3시간)
- **대기열 우선순위**: 유료 계정 > 무료 계정

### macOS Runner 가용성 패턴
- **혼잡 시간대**: 미국 근무시간 (PST 9AM-6PM)
- **한산한 시간대**: 미국 새벽/주말 (PST 11PM-7AM)
- **월말 현상**: 무료 계정 한도 소진으로 대기 증가

## ⚡ 즉시 적용 가능한 해결책

### 1. 최적화된 워크플로우 사용

```bash
# 기존 워크플로우 대신 새로운 것 사용
.github/workflows/build-pkg-optimized.yml  # 최적화된 전체 빌드
.github/workflows/build-pkg-lite.yml       # 초고속 경량 빌드 (3-5분)
.github/workflows/build-cross-platform.yml # macOS runner 우회
```

### 2. 빌드 트리거 전략

**A. 한산한 시간대 활용**
```yaml
# 한국 시간 기준 권장 실행 시간
- 오전 12시 ~ 4시 (PST 8AM ~ 12PM)
- 오후 1시 ~ 3시 (PST 9PM ~ 11PM)
- 주말 전체
```

**B. 수동 실행 우선 사용**
```bash
# GitHub 웹에서 수동 실행
Actions → Build PKG (Lite) → Run workflow
```

### 3. 큐 우회 전략

**우선순위 1: 경량 빌드**
```yaml
# build-pkg-lite.yml 사용
- 빌드 시간: 3-5분
- 리소스 사용량: 최소
- 큐 우선순위: 높음
```

**우선순위 2: 크로스 플랫폼 빌드**
```yaml
# build-cross-platform.yml 사용
- Linux runner 사용 (무제한)
- macOS 호환 패키지 생성
- 빌드 시간: 2-3분
```

## 🔧 워크플로우별 사용 가이드

### build-pkg-optimized.yml
```yaml
# 언제 사용: 완전한 PKG 파일이 필요할 때
# 예상 시간: 8-12분
# 큐 대기: 보통 (혼잡 시간대 피해서)
장점: 완전한 기능, 서명 가능
단점: 시간 오래 걸림
```

### build-pkg-lite.yml (⭐ 추천)
```yaml
# 언제 사용: 빠른 테스트, 급한 배포
# 예상 시간: 3-5분
# 큐 대기: 낮음 (짧은 timeout으로 우선순위 향상)
장점: 초고속, 큐 우회 가능성 높음
단점: 기본 기능만
```

### build-cross-platform.yml (🚀 큐 우회)
```yaml
# 언제 사용: macOS runner 완전히 막혔을 때
# 예상 시간: 2-3분
# 큐 대기: 없음 (Linux runner)
장점: 즉시 실행, 무제한 사용
단점: 수동 설치 과정 필요
```

## 📋 단계별 실행 가이드

### Step 1: 즉시 시도 (큐 우회)
```bash
1. build-cross-platform.yml 실행
   → Actions → Cross-Platform Build → Run workflow

2. 결과물 다운로드
   → Artifacts → CARRY-Route-Optimizer-CrossPlatform

3. macOS에서 테스트
   → ZIP 압축 해제 → install_macos.sh 실행
```

### Step 2: 경량 빌드 시도
```bash
1. 한산한 시간대에 build-pkg-lite.yml 실행
   → 권장: 한국시간 새벽 12-4시, 오후 1-3시

2. 큐에 걸리면 즉시 취소 후 다른 시간 재시도
```

### Step 3: 최적화된 빌드 (최종)
```bash
1. 주말이나 완전히 한산한 시간에 시도
2. build-pkg-optimized.yml 실행
3. 완전한 PKG 파일 획득
```

## 🛠️ 추가 최적화 방법

### 1. 의존성 캐싱 활용
```yaml
# requirements.txt 버전 고정으로 캐시 적중률 향상
PyQt6>=6.4.0  # 버전 범위 제한
pandas>=2.0.0,<3.0.0  # 상한 설정
```

### 2. 병렬 빌드 방지
```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true  # 중복 실행 방지
```

### 3. 타임아웃 최적화
```yaml
timeout-minutes: 25  # 짧게 설정하여 큐 우선순위 향상
```

## 🔍 문제 진단 방법

### 큐 상태 확인
```bash
1. Actions 탭에서 워크플로우 상태 확인
2. "Queued" 시간이 5분 이상이면 취소
3. 다른 시간대에 재시도
```

### GitHub 상태 페이지 확인
```bash
https://www.githubstatus.com/
→ Actions 서비스 상태 확인
```

### 사용량 확인
```bash
Settings → Billing → Usage this month
→ Actions minutes 사용량 확인
```

## 💡 장기적 해결책

### 1. GitHub Pro 업그레이드 고려
```yaml
비용: $4/월
혜택:
- 3,000분/월 Actions 시간
- macOS runner 우선순위 향상
- 300분 → 30시간 macOS 사용 가능
```

### 2. 자체 Runner 구축
```yaml
# GitHub Self-hosted Runner
- macOS 장비에 직접 설치
- 무제한 사용
- 설정 복잡도: 높음
```

### 3. 대안 CI/CD 서비스
```yaml
- GitLab CI: 400분/월 무료
- CircleCI: 2,500 크레딧/월 무료
- Travis CI: 오픈소스 무료
```

## 🎯 권장 즉시 실행 계획

### 지금 당장 실행할 것
```bash
1. build-cross-platform.yml 실행 (큐 없음, 2-3분)
2. 결과물로 테스트 진행
3. 문제없으면 이 방식으로 당분간 사용
```

### 오늘 밤 시도할 것
```bash
한국시간 자정~새벽 4시에:
1. build-pkg-lite.yml 실행 (큐 가능성 낮음, 3-5분)
2. 성공하면 PKG 파일 획득
```

### 주말에 시도할 것
```bash
토요일이나 일요일에:
1. build-pkg-optimized.yml 실행 (완전한 빌드)
2. 최종 배포용 PKG 파일 생성
```

## 📞 추가 지원

문제가 계속되면:
1. GitHub Support에 문의 (Pro 계정 권장)
2. 이 가이드의 대안 방법들 활용
3. 필요시 다른 CI/CD 서비스 고려

---

**💡 핵심 요약**: macOS runner 대기열 문제는 GitHub Actions 무료 계정의 구조적 한계입니다. 위의 대안 방법들을 활용하면 즉시 문제를 우회하여 PKG 파일을 생성할 수 있습니다.