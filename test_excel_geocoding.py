#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

import pandas as pd
from geocoder import KakaoGeocoder
from excel_handler import ExcelHandler
import logging
from pathlib import Path

def test_excel_geocoding():
    """실제 Excel 파일로 지오코딩 테스트"""

    # 로거 설정
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)

    try:
        print("Excel file geocoding test start...")

        # Excel 파일 파싱
        excel_handler = ExcelHandler()
        input_path = Path("CARRY X Doeat 주문현황.xlsx")

        print("1. Loading Excel file...")
        raw_data = excel_handler.parse_input_file(input_path)
        print(f"   Loaded {len(raw_data)} orders")

        # 처음 5개만 테스트 (API 호출 제한)
        test_data = raw_data[:5]

        # 지오코딩 수행
        print("2. Starting geocoding...")
        api_key = "d4d4b1bace236136ca0dea3bd5258ddf"
        geocoder = KakaoGeocoder(api_key, logger)

        geocoded_data = geocoder.geocode_addresses(test_data)

        print(f"3. Geocoding completed: {len(geocoded_data)} results")

        # 결과 출력
        print("\nResults:")
        for i, data in enumerate(geocoded_data, 1):
            address = data.get('address', data.get('road_address', 'No address'))
            longitude = data.get('longitude', 0)
            latitude = data.get('latitude', 0)
            source = data.get('geocoding_source', 'unknown')

            print(f"{i}. {address}")
            print(f"   -> {longitude}, {latitude} (source: {source})")

        # 결과 저장 테스트
        print("\n4. Saving results to Excel...")
        excel_handler.save_geocoded_data(geocoded_data, "test_geocoded_sample.xlsx")
        print("   Saved to: test_geocoded_sample.xlsx")

        print("\nTest completed successfully!")
        return True

    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_excel_geocoding()
    if not success:
        sys.exit(1)