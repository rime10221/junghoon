"""
카카오 지오코딩 API 클라이언트
주소를 좌표로 변환하는 기능
"""

import requests
import logging
import time
import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

@dataclass
class GeocodingResult:
    """지오코딩 결과"""
    original_address: str
    formatted_address: str
    longitude: float
    latitude: float
    accuracy: str
    success: bool
    error_message: str = ""

class KakaoGeocoder:
    """카카오 지오코딩 API 클라이언트"""

    BASE_URL = "https://dapi.kakao.com/v2/local/search/address.json"

    def __init__(self, api_key: str, logger: logging.Logger = None):
        self.api_key = api_key
        self.logger = logger or logging.getLogger(__name__)
        self.headers = {
            'Authorization': f'KakaoAK {self.api_key}'
        }
        self.request_count = 0
        self.max_requests_per_second = 10  # 카카오 API 제한

    def geocode_addresses(self, order_data: List[Dict]) -> List[Dict]:
        """
        주문 데이터의 주소를 좌표로 변환

        Args:
            order_data: 주문 데이터 리스트

        Returns:
            좌표가 추가된 주문 데이터 리스트
        """
        geocoded_data = []
        total_count = len(order_data)
        success_count = 0
        failed_addresses = []

        self.logger.info(f"🌐 총 {total_count}개 주소 지오코딩 시작...")

        for i, order in enumerate(order_data, 1):
            try:
                # 진행률 표시
                if i % 50 == 0 or i == total_count:
                    self.logger.info(f"진행률: {i}/{total_count} ({i/total_count*100:.1f}%)")

                # 주소 추출
                address = self._extract_address(order)
                if not address:
                    self.logger.warning(f"주문 {order.get('id', i)}: 주소 정보 없음")
                    continue

                # 기존에 좌표가 있는지 확인
                existing_coords = self._check_existing_coordinates(order)
                if existing_coords:
                    order['longitude'] = existing_coords[0]
                    order['latitude'] = existing_coords[1]
                    order['geocoding_source'] = 'existing'
                    geocoded_data.append(order)
                    success_count += 1
                    continue

                # 지오코딩 수행
                result = self._geocode_single_address(address)

                if result.success:
                    order['longitude'] = result.longitude
                    order['latitude'] = result.latitude
                    order['formatted_address'] = result.formatted_address
                    order['geocoding_accuracy'] = result.accuracy
                    order['geocoding_source'] = 'kakao_api'
                    geocoded_data.append(order)
                    success_count += 1
                else:
                    self.logger.warning(f"지오코딩 실패: {address} - {result.error_message}")
                    failed_addresses.append({
                        'order_id': order.get('id', i),
                        'address': address,
                        'error': result.error_message
                    })

                # API 호출 제한 준수
                self._rate_limit()

            except Exception as e:
                self.logger.error(f"주문 {order.get('id', i)} 처리 중 오류: {str(e)}")
                failed_addresses.append({
                    'order_id': order.get('id', i),
                    'address': order.get('address', 'Unknown'),
                    'error': str(e)
                })

        # 결과 요약
        self.logger.info(f"✅ 지오코딩 완료: 성공 {success_count}/{total_count} ({success_count/total_count*100:.1f}%)")

        if failed_addresses:
            self.logger.warning(f"❌ 실패한 주소 {len(failed_addresses)}개:")
            for failed in failed_addresses[:5]:  # 처음 5개만 로그
                self.logger.warning(f"  - {failed['address']}: {failed['error']}")
            if len(failed_addresses) > 5:
                self.logger.warning(f"  ... 및 {len(failed_addresses) - 5}개 더")

        return geocoded_data

    def _extract_address(self, order: Dict) -> str:
        """주문 데이터에서 주소 추출"""
        # 우선순위: road_address > address > detail_address
        address_fields = ['road_address', 'address', 'detail_address']

        for field in address_fields:
            if field in order and order[field]:
                addr = str(order[field]).strip()
                if addr and addr.lower() not in ['nan', 'none', 'null', '']:
                    return addr

        return ""

    def _check_existing_coordinates(self, order: Dict) -> Optional[Tuple[float, float]]:
        """기존 좌표 정보 확인"""
        try:
            # 경도, 위도 필드 확인
            lng_fields = ['longitude', 'lng', 'x', 'lon']
            lat_fields = ['latitude', 'lat', 'y']

            longitude = None
            latitude = None

            for field in lng_fields:
                if field in order and order[field] is not None:
                    try:
                        longitude = float(order[field])
                        break
                    except (ValueError, TypeError):
                        continue

            for field in lat_fields:
                if field in order and order[field] is not None:
                    try:
                        latitude = float(order[field])
                        break
                    except (ValueError, TypeError):
                        continue

            if longitude and latitude:
                # 한국 좌표 범위 검증
                if 124.0 <= longitude <= 132.0 and 33.0 <= latitude <= 43.0:
                    return (longitude, latitude)

            return None

        except Exception:
            return None

    def _geocode_single_address(self, address: str) -> GeocodingResult:
        """단일 주소 지오코딩"""
        try:
            # API 요청
            params = {'query': address}
            response = requests.get(
                self.BASE_URL,
                headers=self.headers,
                params=params,
                timeout=10
            )

            self.request_count += 1

            if response.status_code != 200:
                return GeocodingResult(
                    original_address=address,
                    formatted_address="",
                    longitude=0.0,
                    latitude=0.0,
                    accuracy="",
                    success=False,
                    error_message=f"HTTP {response.status_code}"
                )

            data = response.json()
            documents = data.get('documents', [])

            if not documents:
                return GeocodingResult(
                    original_address=address,
                    formatted_address="",
                    longitude=0.0,
                    latitude=0.0,
                    accuracy="",
                    success=False,
                    error_message="주소를 찾을 수 없음"
                )

            # 첫 번째 결과 사용
            doc = documents[0]

            # 도로명 주소 우선, 없으면 지번 주소
            if doc.get('road_address'):
                addr_info = doc['road_address']
                formatted_addr = addr_info['address_name']
                accuracy = "road_address"
            else:
                addr_info = doc['address']
                formatted_addr = addr_info['address_name']
                accuracy = "jibun_address"

            longitude = float(doc['x'])
            latitude = float(doc['y'])

            return GeocodingResult(
                original_address=address,
                formatted_address=formatted_addr,
                longitude=longitude,
                latitude=latitude,
                accuracy=accuracy,
                success=True
            )

        except requests.RequestException as e:
            return GeocodingResult(
                original_address=address,
                formatted_address="",
                longitude=0.0,
                latitude=0.0,
                accuracy="",
                success=False,
                error_message=f"네트워크 오류: {str(e)}"
            )
        except Exception as e:
            return GeocodingResult(
                original_address=address,
                formatted_address="",
                longitude=0.0,
                latitude=0.0,
                accuracy="",
                success=False,
                error_message=f"처리 오류: {str(e)}"
            )

    def _rate_limit(self):
        """API 호출 제한 준수"""
        if self.request_count % self.max_requests_per_second == 0:
            time.sleep(1.1)  # 1초 대기

    def batch_geocode_with_retry(self, addresses: List[str], max_retries: int = 3) -> List[GeocodingResult]:
        """배치 지오코딩 (재시도 포함)"""
        results = []

        for address in addresses:
            retry_count = 0
            result = None

            while retry_count <= max_retries:
                result = self._geocode_single_address(address)

                if result.success:
                    break

                retry_count += 1
                if retry_count <= max_retries:
                    self.logger.debug(f"재시도 {retry_count}/{max_retries}: {address}")
                    time.sleep(2 ** retry_count)  # 지수 백오프

            results.append(result)
            self._rate_limit()

        return results