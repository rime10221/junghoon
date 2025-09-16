#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
지오코딩 전용 스크립트
Excel의 모든 주소를 좌표로 변환
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

import click
from pathlib import Path
from dotenv import load_dotenv
from excel_handler import ExcelHandler
from geocoder import KakaoGeocoder
from logger_config import setup_logger

# 환경변수 로드
load_dotenv()

@click.command()
@click.option('--input', '-i', 'input_file', required=True,
              help='입력 Excel 파일 경로')
@click.option('--output', '-o', 'output_file', default='geocoded_addresses.xlsx',
              help='출력 Excel 파일 경로')
@click.option('--limit', '-l', default=0,
              help='처리할 주소 수 제한 (0=전체)')
@click.option('--verbose', '-v', is_flag=True, help='상세 로그 출력')
def main(input_file: str, output_file: str, limit: int, verbose: bool):
    """
    Excel 파일의 모든 주소를 좌표로 변환
    """

    # 로깅 설정
    logger = setup_logger(verbose)

    # API 키 확인
    api_key = os.getenv('KAKAO_API_KEY')
    if not api_key:
        click.echo("ERROR: KAKAO_API_KEY environment variable is required")
        click.echo("Please check your .env file")
        sys.exit(1)

    try:
        # Step 1: Excel 파일 파싱
        logger.info("Loading Excel file...")
        input_path = Path(input_file)
        if not input_path.exists():
            click.echo(f"ERROR: File not found: {input_file}")
            sys.exit(1)

        excel_handler = ExcelHandler()
        raw_data = excel_handler.parse_input_file(input_path)
        logger.info(f"Loaded {len(raw_data)} orders")

        # 제한 적용
        if limit > 0 and len(raw_data) > limit:
            raw_data = raw_data[:limit]
            logger.info(f"Limited to first {limit} orders")

        # Step 2: 지오코딩 수행
        logger.info("Starting geocoding...")
        geocoder = KakaoGeocoder(api_key, logger)
        geocoded_data = geocoder.geocode_addresses(raw_data)

        # Step 3: 결과 저장
        logger.info("Saving results...")
        excel_handler.save_geocoded_data(geocoded_data, output_file)

        # 결과 요약
        total = len(raw_data)
        success = len(geocoded_data)
        success_rate = (success / total * 100) if total > 0 else 0

        click.echo(f"\nGeocoding Summary:")
        click.echo(f"  Total addresses: {total}")
        click.echo(f"  Successfully geocoded: {success}")
        click.echo(f"  Success rate: {success_rate:.1f}%")
        click.echo(f"  Output file: {output_file}")

        if success_rate < 90:
            click.echo("WARNING: Low success rate. Check address quality.")

    except Exception as e:
        logger.error(f"Error occurred: {str(e)}")
        click.echo(f"ERROR: {str(e)}", err=True)
        if verbose:
            import traceback
            click.echo(traceback.format_exc(), err=True)
        sys.exit(1)

if __name__ == '__main__':
    main()