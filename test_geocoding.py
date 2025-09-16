#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
지오코딩 기능 테스트
"""

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
        "부산광역시 해운대구 해운대해변로 264",
        "인천광역시 연수구 컨벤시아대로 206",
    ]

    print("🌐 카카오 지오코딩 API 테스트 시작...")

    try:
        geocoder = KakaoGeocoder(api_key, logger)

        for i, address in enumerate(test_addresses, 1):
            print(f"\n🔍 테스트 {i}: {address}")

            result = geocoder._geocode_single_address(address)

            if result.success:
                print(f"  ✅ 성공!")
                print(f"     경도: {result.longitude}")
                print(f"     위도: {result.latitude}")
                print(f"     정제 주소: {result.formatted_address}")
                print(f"     정확도: {result.accuracy}")
            else:
                print(f"  ❌ 실패: {result.error_message}")

        print(f"\n📊 API 호출 총 {geocoder.request_count}회")
        print("✅ 지오코딩 테스트 완료!")

        return True

    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_geocoding()
    if not success:
        sys.exit(1)