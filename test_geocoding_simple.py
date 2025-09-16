#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from geocoder import KakaoGeocoder
import logging

def test_geocoding():
    """지오코딩 기능 테스트"""

    # 로거 설정
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)

    # API 키
    api_key = "d4d4b1bace236136ca0dea3bd5258ddf"

    # 테스트 주소들
    test_addresses = [
        "서울시 강남구 테헤란로 427",
        "서울특별시 중구 세종대로 110",
    ]

    print("Kakao Geocoding API Test Start...")

    try:
        geocoder = KakaoGeocoder(api_key, logger)

        for i, address in enumerate(test_addresses, 1):
            print(f"\nTest {i}: {address}")

            result = geocoder._geocode_single_address(address)

            if result.success:
                print(f"  SUCCESS!")
                print(f"     Longitude: {result.longitude}")
                print(f"     Latitude: {result.latitude}")
                print(f"     Formatted: {result.formatted_address}")
                print(f"     Accuracy: {result.accuracy}")
            else:
                print(f"  FAILED: {result.error_message}")

        print(f"\nTotal API calls: {geocoder.request_count}")
        print("Geocoding test completed!")

        return True

    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_geocoding()
    if not success:
        sys.exit(1)