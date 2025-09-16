# 다중 경유지 최적화 프로그램 Docker 이미지

FROM python:3.9-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 업데이트 및 필요한 패키지 설치
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드 복사
COPY . .

# 환경변수 설정
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# 입출력 디렉토리 생성
RUN mkdir -p /app/input /app/output /app/logs

# 볼륨 마운트 포인트
VOLUME ["/app/input", "/app/output", "/app/logs"]

# 기본 명령어
ENTRYPOINT ["python", "main.py"]

# 사용 예시:
# docker build -t route-optimizer .
# docker run -v $(pwd)/data:/app/input -v $(pwd)/results:/app/output \
#   -e KAKAO_API_KEY=your_api_key route-optimizer \
#   --input /app/input/orders.xlsx --output /app/output/optimized.xlsx