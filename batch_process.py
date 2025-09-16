#!/usr/bin/env python3
"""
배치 처리 스크립트 - GUI에서 호출
여러 Excel 파일을 일괄 처리하여 최적화된 경로 생성
"""

import os
import sys
import argparse
import glob
from pathlib import Path
from dotenv import load_dotenv
import time

# 현재 디렉토리를 Python 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
sys.path.insert(0, current_dir)
sys.path.insert(0, src_dir)

# 환경변수 로드
load_dotenv()

def setup_logging():
    """간단한 로깅 설정 (GUI용)"""
    import logging
    import io

    # UTF-8 출력 보장
    if sys.stdout.encoding != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    if sys.stderr.encoding != 'utf-8':
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    return logging.getLogger(__name__)

def find_excel_files(folder_path):
    """폴더에서 Excel 파일 찾기"""
    excel_patterns = ['*.xlsx', '*.xls']
    excel_files = []

    for pattern in excel_patterns:
        excel_files.extend(glob.glob(os.path.join(folder_path, pattern)))

    return sorted(excel_files)

def process_single_file(input_file, output_folder, priority, api_key, logger):
    """단일 Excel 파일 처리"""
    try:
        # 모듈 import
        from route_optimizer import RouteOptimizer
        from excel_handler import ExcelHandler
        from geocoder import KakaoGeocoder

        logger.info(f"📂 처리 시작: {os.path.basename(input_file)}")

        # API 키 확인 - 이미 검증된 키가 전달됨
        if not api_key:
            raise Exception("API 키가 설정되지 않았습니다.")

        # 출력 파일명 생성
        input_name = Path(input_file).stem
        output_file = os.path.join(output_folder, f"{input_name}_optimized.xlsx")

        # Excel 파일 파싱
        logger.info(f"📊 Excel 파일 파싱 중...")
        excel_handler = ExcelHandler()
        raw_order_data = excel_handler.parse_input_file(input_file)
        logger.info(f"✅ {len(raw_order_data)}개 주문 데이터 파싱 완료")

        if not raw_order_data:
            logger.warning(f"⚠️  파일에 처리할 데이터가 없습니다: {os.path.basename(input_file)}")
            return False

        # 지오코딩
        logger.info(f"🌐 주소를 좌표로 변환 중...")
        geocoder = KakaoGeocoder(api_key, logger)
        geocoded_data = geocoder.geocode_addresses(raw_order_data)
        logger.info(f"✅ {len(geocoded_data)}개 지오코딩 완료")

        if not geocoded_data:
            logger.warning(f"⚠️  지오코딩된 데이터가 없습니다: {os.path.basename(input_file)}")
            return False

        # 경로 최적화
        logger.info(f"🚗 경로 최적화 실행 중...")
        route_optimizer = RouteOptimizer(api_key, logger)
        optimization_results = route_optimizer.optimize_route(geocoded_data, priority)

        if not optimization_results:
            logger.warning(f"⚠️  최적화 결과가 없습니다: {os.path.basename(input_file)}")
            return False

        total_optimized_waypoints = sum(len(r.optimized_waypoints) for r in optimization_results if r.success)
        logger.info(f"✅ {len(optimization_results)}개 배치, 총 {total_optimized_waypoints}개 지점 최적화 완료")

        # 결과 저장
        logger.info(f"💾 결과 파일 저장 중...")
        excel_handler.save_optimization_results(optimization_results, output_file)

        # 결과 요약
        summary = route_optimizer.get_optimization_summary(optimization_results)
        logger.info(f"📊 처리 완료: {os.path.basename(input_file)}")
        logger.info(f"   └─ 총 경유지: {summary['total_waypoints']}개")
        logger.info(f"   └─ 성공 배치: {summary['successful_batches']}/{summary['total_batches']}개")
        logger.info(f"   └─ 총 거리: {summary['total_distance_km']:.2f}km")
        logger.info(f"   └─ 총 시간: {summary['total_duration_hours']:.2f}시간")
        logger.info(f"   └─ 결과 파일: {os.path.basename(output_file)}")

        return True

    except Exception as e:
        logger.error(f"❌ 파일 처리 오류 ({os.path.basename(input_file)}): {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description='배송 경로 최적화 배치 처리')
    parser.add_argument('--input-folder', required=True, help='입력 폴더 경로 (Excel 파일들)')
    parser.add_argument('--output-folder', required=True, help='출력 폴더 경로')
    parser.add_argument('--priority', default='TIME',
                       choices=['TIME', 'DISTANCE', 'RECOMMEND'],
                       help='최적화 우선순위')
    parser.add_argument('--api-key', help='카카오 API 키 (환경변수보다 우선)')

    args = parser.parse_args()

    # 로깅 설정
    logger = setup_logging()

    try:
        # 입력 폴더 확인
        if not os.path.exists(args.input_folder):
            raise Exception(f"입력 폴더를 찾을 수 없습니다: {args.input_folder}")

        # API 키 확인 및 설정
        api_key = args.api_key or os.getenv('KAKAO_API_KEY')
        if not api_key:
            logger.error("❌ API 키가 필요합니다.")
            logger.error("해결 방법:")
            logger.error("  1. GUI에서 API 키 입력")
            logger.error("  2. .env 파일에 KAKAO_API_KEY 설정")
            logger.error("  3. 환경변수 KAKAO_API_KEY 설정")
            return 1

        # 출력 폴더 생성
        os.makedirs(args.output_folder, exist_ok=True)

        # Excel 파일 찾기
        excel_files = find_excel_files(args.input_folder)

        if not excel_files:
            logger.warning(f"⚠️  입력 폴더에 Excel 파일이 없습니다: {args.input_folder}")
            return 1

        logger.info(f"🚀 배치 처리 시작")
        logger.info(f"📁 입력 폴더: {args.input_folder}")
        logger.info(f"📤 출력 폴더: {args.output_folder}")
        logger.info(f"🎯 최적화 우선순위: {args.priority}")
        logger.info(f"📊 처리할 파일 수: {len(excel_files)}개")
        logger.info("=" * 60)

        # 파일별 처리
        successful_files = 0
        failed_files = 0
        start_time = time.time()

        for i, excel_file in enumerate(excel_files, 1):
            logger.info(f"📂 [{i}/{len(excel_files)}] 시작: {os.path.basename(excel_file)}")

            if process_single_file(excel_file, args.output_folder, args.priority, api_key, logger):
                successful_files += 1
                logger.info(f"✅ 성공: {os.path.basename(excel_file)} ({successful_files}/{len(excel_files)} 완료)")
            else:
                failed_files += 1
                logger.error(f"❌ 실패: {os.path.basename(excel_file)} ({successful_files}/{len(excel_files)} 완료)")

            # 진행률 표시
            progress_percent = ((successful_files + failed_files) / len(excel_files)) * 100
            logger.info(f"📊 전체 진행률: {progress_percent:.1f}% ({successful_files + failed_files}/{len(excel_files)})")
            logger.info("-" * 50)

            # 약간의 지연 (API 호출 제한 고려)
            if i < len(excel_files):
                time.sleep(1)

        # 최종 결과 요약
        end_time = time.time()
        elapsed_time = end_time - start_time

        logger.info("=" * 60)
        logger.info("🎉 배치 처리 완료!")
        logger.info(f"📊 처리 결과:")
        logger.info(f"   ✅ 성공: {successful_files}개")
        logger.info(f"   ❌ 실패: {failed_files}개")
        logger.info(f"   📈 성공률: {(successful_files/(successful_files+failed_files)*100):.1f}%")
        logger.info(f"   ⏱️  총 소요시간: {elapsed_time/60:.1f}분")
        logger.info(f"📁 결과 파일들은 다음 폴더에 저장되었습니다: {args.output_folder}")

        return 0 if failed_files == 0 else 1

    except KeyboardInterrupt:
        logger.info("\n⏹️  사용자에 의해 처리가 중단되었습니다.")
        return 1
    except Exception as e:
        logger.error(f"❌ 배치 처리 오류: {str(e)}")
        return 1

if __name__ == '__main__':
    sys.exit(main())