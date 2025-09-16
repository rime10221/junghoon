#!/usr/bin/env python3
"""
다중 경유지 최적화 동선 프로그램 (간소화 버전)
카카오 모빌리티 API를 활용한 배송 경로 최적화 CLI 도구
"""

import click
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# src 디렉토리를 Python 경로에 추가
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# 환경변수 로드
load_dotenv()

def validate_file_path(file_path: str) -> Path:
    """입력 파일 경로 검증"""
    path = Path(file_path)
    if not path.exists():
        raise click.FileError(f"파일을 찾을 수 없습니다: {file_path}")
    if not path.suffix.lower() in ['.xlsx', '.xls']:
        raise click.ClickException("Excel 파일(.xlsx, .xls)만 지원됩니다.")
    return path

@click.command()
@click.option('--input', '-i', 'input_file', required=True,
              help='입력 Excel 파일 경로 (주문현황)')
@click.option('--output', '-o', 'output_file',
              help='출력 Excel 파일 경로 (기본: optimized_route.xlsx)')
@click.option('--priority', '-p',
              type=click.Choice(['RECOMMEND', 'TIME', 'DISTANCE']),
              default='TIME',
              help='경로 탐색 우선순위')
@click.option('--api-key', '-k', 'api_key',
              help='카카오 API 키 (또는 KAKAO_API_KEY 환경변수 사용)')
@click.option('--verbose', '-v', is_flag=True, help='상세 로그 출력')
@click.option('--geocode-only', is_flag=True,
              help='주소 -> 좌표 변환만 수행 (경로 최적화 안함)')
def main(input_file: str, output_file: str, priority: str, api_key: str, verbose: bool, geocode_only: bool):
    """
    다중 경유지 최적화 동선 계획 프로그램 (간소화 버전)

    Excel 파일의 주문 정보를 읽어 최적화된 배송 경로를 생성합니다.
    카카오 모빌리티 API를 사용하여 실제 도로 기반 경로를 계산합니다.

    주소만 있는 Excel 파일도 지원하며, 자동으로 좌표 변환을 수행합니다.
    """
    print("간소화 버전 실행 중...")

    # 필수 모듈만 import (pandas 문제 해결을 위해)
    try:
        from route_optimizer import RouteOptimizer
        from excel_handler import ExcelHandler
        from logger_config import setup_logger
        from geocoder import KakaoGeocoder
    except ImportError as e:
        print(f"❌ 모듈 import 오류: {e}")
        print("pandas/numpy 호환성 문제일 수 있습니다.")
        sys.exit(1)

    # 로깅 설정
    logger = setup_logger(verbose)

    # API 키 확인
    final_api_key = api_key or os.getenv('KAKAO_API_KEY')
    if not final_api_key:
        click.echo("❌ 오류: API 키가 필요합니다.", err=True)
        click.echo("해결 방법:")
        click.echo("  1. .env 파일에 KAKAO_API_KEY 설정")
        click.echo("  2. --api-key 옵션 사용")
        click.echo("  3. 환경변수 KAKAO_API_KEY 설정")
        sys.exit(1)

    try:
        # Step 1: Excel 파일 파싱
        print("Excel 파일 파싱 중...")
        input_path = validate_file_path(input_file)
        excel_handler = ExcelHandler()
        raw_order_data = excel_handler.parse_input_file(input_path)
        print(f"{len(raw_order_data)}개 주문 데이터 로드 완료")

        # Step 2: 주소 -> 좌표 변환 (지오코딩)
        print("주소를 좌표로 변환 중...")
        geocoder = KakaoGeocoder(final_api_key, logger)
        geocoded_data = geocoder.geocode_addresses(raw_order_data)
        print(f"{len(geocoded_data)}개 주소 좌표 변환 완료")

        # 지오코딩만 수행하는 경우
        if geocode_only:
            geocode_output = output_file or "geocoded_addresses.xlsx"
            excel_handler.save_geocoded_data(geocoded_data, geocode_output)
            click.echo(f"지오코딩 완료! 결과: {geocode_output}")
            return

        # Step 3: 경로 최적화 실행
        print("경로 최적화 실행 중...")
        route_optimizer = RouteOptimizer(final_api_key, logger)
        optimization_results = route_optimizer.optimize_route(geocoded_data, priority)
        print("경로 최적화 완료")

        if not optimization_results:
            click.echo("경로 최적화 결과가 없습니다.", err=True)
            sys.exit(1)

        # Step 4: Excel 출력
        print("결과 파일 생성 중...")
        output_path = output_file or "optimized_route.xlsx"
        excel_handler.save_optimization_results(optimization_results, output_path)

        print(f"최적화 완료! 결과: {output_path}")

        # 결과 요약 출력
        summary = route_optimizer.get_optimization_summary(optimization_results)

        print(f"결과 요약:")
        print(f"   총 경유지: {summary['total_waypoints']}개")
        print(f"   성공 배치: {summary['successful_batches']}/{summary['total_batches']}개")
        print(f"   총 거리: {summary['total_distance_km']:.2f}km")
        print(f"   총 시간: {summary['total_duration_hours']:.2f}시간")
        print(f"   평균 속도: {summary['average_speed_kmh']:.1f}km/h")
        print(f"   성공률: {summary['success_rate']:.1f}%")

    except Exception as e:
        logger.error(f"처리 중 오류 발생: {str(e)}")
        print(f"❌ 오류: {str(e)}")
        if verbose:
            import traceback
            print(traceback.format_exc())
        sys.exit(1)

if __name__ == '__main__':
    main()