#!/usr/bin/env python3
"""
다중 경유지 최적화 동선 프로그램
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
@click.option('--map-output', '-m', 'map_output',
              help='지도 시각화 HTML 파일 경로 (기본: route_map.html)')
@click.option('--no-map', is_flag=True,
              help='지도 시각화 건너뛰기')
@click.option('--departure-time', '-t', 'departure_time',
              help='출발 시간 (예: "09:00", "14:30") - 현재는 로그 기록용')
def main(input_file: str, output_file: str, priority: str, api_key: str, verbose: bool, geocode_only: bool, map_output: str, no_map: bool, departure_time: str):
    """
    다중 경유지 최적화 동선 계획 프로그램

    Excel 파일의 주문 정보를 읽어 최적화된 배송 경로를 생성합니다.
    카카오 모빌리티 API를 사용하여 실제 도로 기반 경로를 계산합니다.

    주소만 있는 Excel 파일도 지원하며, 자동으로 좌표 변환을 수행합니다.
    """
    from route_optimizer import RouteOptimizer
    from excel_handler import ExcelHandler
    from logger_config import setup_logger
    from geocoder import KakaoGeocoder

    # 지도 시각화는 선택적으로 import (현재 비활성화)
    MAP_VISUALIZATION_AVAILABLE = False
    if verbose and not no_map:
        click.echo("⚠️ 지도 시각화는 현재 개발 중입니다.")

    # 로깅 설정
    logger = setup_logger(verbose)

    # 출발시간 로그 기록
    if departure_time:
        logger.info(f"🕐 지정된 출발시간: {departure_time} (참고: 카카오 API는 현재 교통상황 기준)")
        click.echo(f"출발시간: {departure_time} (현재 교통상황 기반 경로 생성)")

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
        # 📊 전체 파이프라인 추적 시작
        logger.info("🔍 === 데이터 흐름 추적 시작 ===")

        # Step 1: Excel 파일 파싱
        logger.info("📂 Excel 파일 파싱 시작...")
        input_path = validate_file_path(input_file)
        excel_handler = ExcelHandler()
        raw_order_data = excel_handler.parse_input_file(input_path)
        logger.info(f"🔍 Step 1 완료: {len(raw_order_data)}개 원본 주문 데이터 파싱")

        # Step 2: 주소 -> 좌표 변환 (지오코딩)
        logger.info("🌐 주소를 좌표로 변환 중...")
        geocoder = KakaoGeocoder(final_api_key, logger)
        geocoded_data = geocoder.geocode_addresses(raw_order_data)
        logger.info(f"🔍 Step 2 완료: {len(geocoded_data)}개 지오코딩 완료 데이터")

        # 지오코딩만 수행하는 경우
        if geocode_only:
            geocode_output = output_file or "geocoded_addresses.xlsx"
            excel_handler.save_geocoded_data(geocoded_data, geocode_output)
            click.echo(f"✅ 지오코딩 완료! 결과: {geocode_output}")
            return

        # Step 3: 경로 최적화 실행
        logger.info("🚗 경로 최적화 실행...")
        route_optimizer = RouteOptimizer(final_api_key, logger)
        optimization_results = route_optimizer.optimize_route(geocoded_data, priority)
        total_optimized_waypoints = sum(len(r.optimized_waypoints) for r in optimization_results if r.success)
        logger.info(f"🔍 Step 3 완료: {len(optimization_results)}개 배치, 총 {total_optimized_waypoints}개 최적화된 지점")

        if not optimization_results:
            click.echo("❌ 경로 최적화 결과가 없습니다.", err=True)
            sys.exit(1)

        # Step 4: Excel 출력
        logger.info("📊 결과 파일 생성...")
        output_path = output_file or "optimized_route.xlsx"
        excel_handler.save_optimization_results(optimization_results, output_path)

        # 📊 최종 데이터 흐름 추적 요약
        logger.info("🔍 === 데이터 흐름 추적 완료 ===")
        logger.info(f"🔍 원본 데이터: {len(raw_order_data)}개")
        logger.info(f"🔍 지오코딩 후: {len(geocoded_data)}개")
        logger.info(f"🔍 최적화 후: {total_optimized_waypoints}개")
        logger.info(f"🔍 데이터 손실: {len(raw_order_data) - total_optimized_waypoints}개")

        click.echo(f"🎉 최적화 완료! 결과: {output_path}")
        click.echo(f"📊 데이터 흐름: {len(raw_order_data)} → {len(geocoded_data)} → {total_optimized_waypoints} (손실: {len(raw_order_data) - total_optimized_waypoints}개)")

        # Step 5: 지도 시각화 (선택사항)
        if not no_map and MAP_VISUALIZATION_AVAILABLE:
            logger.info("🗺️ 지도 시각화 생성...")
            try:
                map_visualizer = MapVisualizer(logger=logger)
                map_path = map_output or "route_map.html"

                # 상세 지도 생성
                created_map = map_visualizer.visualize_optimization_results(optimization_results, map_path)
                if created_map:
                    click.echo(f"🗺️ 지도 시각화 완료! 결과: {created_map}")

                    # 요약 지도도 생성
                    summary_map_path = map_path.replace('.html', '_summary.html')
                    created_summary = map_visualizer.create_summary_map(optimization_results, summary_map_path)
                    if created_summary:
                        click.echo(f"📍 요약 지도 생성: {created_summary}")

                    # CSV 데이터도 내보내기
                    csv_path = map_path.replace('.html', '_data.csv')
                    created_csv = map_visualizer.export_route_data(optimization_results, csv_path)
                    if created_csv:
                        click.echo(f"📄 CSV 데이터 내보내기: {created_csv}")

                else:
                    click.echo("⚠️ 지도 시각화에 실패했습니다")

            except Exception as e:
                logger.error(f"지도 시각화 오류: {str(e)}")
                click.echo(f"⚠️ 지도 시각화 오류: {str(e)}")
        elif not no_map and not MAP_VISUALIZATION_AVAILABLE:
            click.echo("⚠️ 지도 시각화를 위해 folium 라이브러리가 필요합니다: pip install folium")

        # 결과 요약 출력
        summary = route_optimizer.get_optimization_summary(optimization_results)

        click.echo(f"📊 결과 요약:")
        click.echo(f"   총 경유지: {summary['total_waypoints']}개")
        click.echo(f"   성공 배치: {summary['successful_batches']}/{summary['total_batches']}개")
        click.echo(f"   총 거리: {summary['total_distance_km']:.2f}km")
        click.echo(f"   총 시간: {summary['total_duration_hours']:.2f}시간")
        click.echo(f"   평균 속도: {summary['average_speed_kmh']:.1f}km/h")
        click.echo(f"   성공률: {summary['success_rate']:.1f}%")

    except Exception as e:
        logger.error(f"처리 중 오류 발생: {str(e)}")
        click.echo(f"❌ 오류: {str(e)}", err=True)
        if verbose:
            import traceback
            click.echo(traceback.format_exc(), err=True)
        sys.exit(1)

if __name__ == '__main__':
    main()