"""
카카오 모빌리티 길찾기 API 클라이언트
다중 경유지 경로 최적화 API 호출
"""

import requests
import logging
import time
from typing import Dict, List, Any, Optional
import json

class KakaoRouteApiClient:
    """카카오 모빌리티 길찾기 API 클라이언트"""

    BASE_URL = "https://apis-navi.kakaomobility.com/v1"

    def __init__(self, api_key: str, logger: logging.Logger = None):
        # API 인증 설정
        self.api_key = api_key
        if not self.api_key:
            raise ValueError("API 키가 필요합니다. --api-key 옵션 또는 KAKAO_API_KEY 환경변수를 설정하세요.")

        self.headers = {
            'Authorization': f'KakaoAK {self.api_key}',
            'Content-Type': 'application/json'
        }
        self.logger = logger or logging.getLogger(__name__)
        self.request_count = 0

    def get_optimized_route(self, origin: Dict, destination: Dict,
                          waypoints: List[Dict], priority: str = "RECOMMEND") -> Dict[str, Any]:
        """
        다중 경유지 경로 최적화 API 호출

        Args:
            origin: 출발지 {"x": longitude, "y": latitude, "name": "출발지명"}
            destination: 목적지 {"x": longitude, "y": latitude, "name": "목적지명"}
            waypoints: 경유지 리스트 [{"x": longitude, "y": latitude, "name": "경유지명"}]
            priority: 경로 우선순위 (RECOMMEND/TIME/DISTANCE)

        Returns:
            API 응답 데이터
        """

        # 경유지 수 제한 검증
        if len(waypoints) > 30:
            raise ValueError(f"경유지는 최대 30개까지 허용됩니다. 현재: {len(waypoints)}개")

        # API 요청 데이터 구성
        request_data = {
            "origin": {
                "x": str(origin["x"]),
                "y": str(origin["y"]),
                "name": origin.get("name", "출발지")
            },
            "destination": {
                "x": str(destination["x"]),
                "y": str(destination["y"]),
                "name": destination.get("name", "목적지")
            },
            "waypoints": [
                {
                    "x": str(wp["x"]),
                    "y": str(wp["y"]),
                    "name": wp.get("name", f"경유지_{i+1}")
                }
                for i, wp in enumerate(waypoints)
            ],
            "priority": priority,  # 경로 우선순위
            "car_fuel": "GASOLINE",
            "car_hipass": False,
            "alternatives": False,
            "road_details": False,
            "summary": False
        }

        self.logger.debug(f"API 요청 데이터: {len(waypoints)}개 경유지, 우선순위: {priority}")

        try:
            # API 호출 실행
            response = requests.post(
                f"{self.BASE_URL}/waypoints/directions",
                headers=self.headers,
                json=request_data,
                timeout=30
            )

            self.request_count += 1

            # HTTP 상태 코드 검증
            if response.status_code != 200:
                self._handle_http_error(response)

            # API 응답 구조 파싱
            response_data = response.json()
            self._validate_api_response(response_data)

            # 성공 로그
            if response_data.get('routes') and len(response_data['routes']) > 0:
                route = response_data['routes'][0]
                if route.get('result_code') == 0:
                    summary = route.get('summary', {})
                    distance_km = summary.get('distance', 0) / 1000
                    duration_min = summary.get('duration', 0) / 60
                    self.logger.info(f"경로 탐색 성공: {distance_km:.1f}km, {duration_min:.1f}분")

            return response_data

        except requests.RequestException as e:
            self.logger.error(f"API 호출 실패: {str(e)}")
            raise RuntimeError(f"네트워크 오류: {str(e)}")

    def _handle_http_error(self, response: requests.Response):
        """HTTP 오류 처리"""
        status_code = response.status_code

        try:
            error_data = response.json()
            error_msg = error_data.get('msg', '알 수 없는 오류')
        except:
            error_msg = response.text or '응답 없음'

        # 오류 코드별 처리
        if status_code == 400:
            raise ValueError(f"잘못된 요청: {error_msg}")
        elif status_code == 401:
            raise ValueError(f"인증 실패: API 키를 확인하세요. {error_msg}")
        elif status_code == 403:
            raise ValueError(f"권한 없음: {error_msg}")
        elif status_code == 429:
            raise ValueError(f"요청 한도 초과: {error_msg}")
        elif status_code >= 500:
            raise RuntimeError(f"서버 오류: {error_msg}")
        else:
            raise RuntimeError(f"HTTP {status_code}: {error_msg}")

    def _validate_api_response(self, response_data: Dict):
        """API 응답 유효성 검증"""
        if 'routes' not in response_data:
            raise ValueError("잘못된 API 응답: routes 정보 없음")

        if not response_data['routes']:
            raise ValueError("경로를 찾을 수 없습니다")

        route = response_data['routes'][0]
        result_code = route.get('result_code', -1)

        # 경로 탐색 결과 코드 검증
        if result_code != 0:
            result_msg = route.get('result_msg', '알 수 없는 오류')
            if result_code == 1:
                raise ValueError(f"경로를 찾을 수 없습니다: {result_msg}")
            elif 101 <= result_code <= 107:
                raise ValueError(f"지점 주변 도로 탐색 실패: {result_msg}")
            else:
                raise ValueError(f"경로 탐색 실패 (코드: {result_code}): {result_msg}")

    def get_route_summary(self, api_response: Dict) -> Dict[str, Any]:
        """API 응답에서 경로 요약 정보 추출"""
        if not api_response.get('routes'):
            return {}

        route = api_response['routes'][0]
        summary = route.get('summary', {})

        return {
            'result_code': route.get('result_code', -1),
            'result_msg': route.get('result_msg', ''),
            'total_distance': summary.get('distance', 0),  # 미터
            'total_duration': summary.get('duration', 0),  # 초
            'taxi_fare': summary.get('fare', {}).get('taxi', 0),  # 원
            'toll_fare': summary.get('fare', {}).get('toll', 0),  # 원
            'waypoints_count': len(summary.get('waypoints', [])),
            'sections_count': len(route.get('sections', [])),
            'priority': summary.get('priority', 'RECOMMEND')
        }

    def extract_route_details(self, api_response: Dict) -> List[Dict[str, Any]]:
        """API 응답에서 상세 경로 정보 추출"""
        if not api_response.get('routes'):
            return []

        route = api_response['routes'][0]
        sections = route.get('sections', [])

        route_details = []
        cumulative_distance = 0
        cumulative_duration = 0

        for i, section in enumerate(sections):
            section_distance = section.get('distance', 0)
            section_duration = section.get('duration', 0)

            cumulative_distance += section_distance
            cumulative_duration += section_duration

            route_details.append({
                'section_index': i,
                'distance': section_distance,
                'duration': section_duration,
                'cumulative_distance': cumulative_distance,
                'cumulative_duration': cumulative_duration,
                'bound': section.get('bound', {}),
                'roads_count': len(section.get('roads', [])),
                'guides_count': len(section.get('guides', []))
            })

        return route_details

    def batch_route_requests(self, route_requests: List[Dict]) -> List[Dict]:
        """
        여러 경로 요청을 순차적으로 처리
        30개 초과 경유지를 배치로 나눠서 처리할 때 사용
        """
        results = []

        for i, request in enumerate(route_requests):
            try:
                self.logger.info(f"배치 {i+1}/{len(route_requests)} 처리 중...")

                result = self.get_optimized_route(
                    origin=request['origin'],
                    destination=request['destination'],
                    waypoints=request['waypoints'],
                    priority=request.get('priority', 'RECOMMEND')
                )

                results.append({
                    'batch_index': i,
                    'success': True,
                    'data': result,
                    'summary': self.get_route_summary(result)
                })

                # API 호출 제한 준수
                if i < len(route_requests) - 1:  # 마지막이 아니면 대기
                    time.sleep(1.0)  # 1초 대기

            except Exception as e:
                self.logger.error(f"배치 {i+1} 처리 실패: {str(e)}")
                results.append({
                    'batch_index': i,
                    'success': False,
                    'error': str(e),
                    'data': None,
                    'summary': {}
                })

        return results

    def get_api_usage_info(self) -> Dict[str, Any]:
        """API 사용량 정보 반환"""
        return {
            'total_requests': self.request_count,
            'estimated_cost': self.request_count * 0.5,  # 대략적인 비용 (원)
            'api_endpoint': f"{self.BASE_URL}/waypoints/directions"
        }