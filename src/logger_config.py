"""
로깅 설정 모듈
K8: 오류 처리 체계 - 로그 및 사용자 메시지
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

def setup_logger(verbose: bool = False) -> logging.Logger:
    """
    로거 설정 및 초기화
    K8: 오류 처리 - 구조화된 로깅 시스템
    """

    # 로그 레벨 설정
    log_level = logging.DEBUG if verbose else logging.INFO

    # 로그 포맷 설정
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 루트 로거 설정
    logger = logging.getLogger('route_optimizer')
    logger.setLevel(log_level)

    # 기존 핸들러 제거
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # 콘솔 핸들러 설정
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 파일 핸들러 설정 (선택적)
    if verbose:
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)

        log_filename = f"route_optimizer_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        log_filepath = log_dir / log_filename

        file_handler = logging.FileHandler(log_filepath, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        logger.info(f"상세 로그 파일: {log_filepath}")

    # 중복 로그 방지
    logger.propagate = False

    return logger


class ProgressReporter:
    """진행 상황 리포팅 클래스"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def report_parsing_progress(self, current: int, total: int, item_name: str = "항목"):
        """파싱 진행상황 리포트"""
        percentage = (current / total) * 100
        self.logger.info(f"파싱 진행: {current}/{total} {item_name} ({percentage:.1f}%)")

    def report_api_progress(self, current_batch: int, total_batches: int,
                          waypoints_in_batch: int):
        """API 호출 진행상황 리포트"""
        self.logger.info(f"API 호출: 배치 {current_batch}/{total_batches} "
                        f"(경유지 {waypoints_in_batch}개)")

    def report_optimization_progress(self, stage: str, details: str = ""):
        """최적화 단계별 진행상황 리포트"""
        message = f"최적화 단계: {stage}"
        if details:
            message += f" - {details}"
        self.logger.info(message)


def log_api_request(logger: logging.Logger, request_data: dict):
    """API 요청 로깅"""
    origin = request_data.get('origin', {})
    destination = request_data.get('destination', {})
    waypoints_count = len(request_data.get('waypoints', []))
    priority = request_data.get('priority', 'RECOMMEND')

    logger.debug(f"API 요청: 출발지({origin.get('name', 'Unknown')}) -> "
                f"경유지 {waypoints_count}개 -> 목적지({destination.get('name', 'Unknown')}) "
                f"[우선순위: {priority}]")


def log_api_response(logger: logging.Logger, response_data: dict):
    """API 응답 로깅"""
    if 'routes' in response_data and response_data['routes']:
        route = response_data['routes'][0]
        result_code = route.get('result_code', -1)
        result_msg = route.get('result_msg', 'Unknown')

        if result_code == 0:
            summary = route.get('summary', {})
            distance = summary.get('distance', 0)
            duration = summary.get('duration', 0)

            logger.debug(f"API 응답 성공: 거리 {distance}m, 시간 {duration}초 "
                        f"({duration/60:.1f}분)")
        else:
            logger.warning(f"API 응답 실패: 코드 {result_code} - {result_msg}")
    else:
        logger.error("유효하지 않은 API 응답")


def log_error_with_context(logger: logging.Logger, error: Exception,
                          context: str, user_action: str = ""):
    """컨텍스트가 있는 오류 로깅"""
    logger.error(f"오류 발생 [{context}]: {str(error)}")
    if user_action:
        logger.info(f"해결 방법: {user_action}")

    # 디버그 모드에서 스택 트레이스 로깅
    if logger.isEnabledFor(logging.DEBUG):
        logger.exception("상세 오류 정보:")