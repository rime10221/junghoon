"""
좌표 검증 및 변환 유틸리티
WGS84 좌표계 처리 및 거리 계산
"""

import math
from typing import Tuple, List, Dict, Any, Optional

class CoordinateValidator:
    """좌표 유효성 검증 클래스"""

    # WGS84 좌표계 범위
    MIN_LONGITUDE = -180.0
    MAX_LONGITUDE = 180.0
    MIN_LATITUDE = -90.0
    MAX_LATITUDE = 90.0

    # 한국 지역 대략적 범위
    KOREA_MIN_LONGITUDE = 124.0
    KOREA_MAX_LONGITUDE = 132.0
    KOREA_MIN_LATITUDE = 33.0
    KOREA_MAX_LATITUDE = 43.0

    def is_valid_coordinate(self, longitude: float, latitude: float,
                          strict_korea: bool = True) -> bool:
        """
        좌표 유효성 검증

        Args:
            longitude: 경도
            latitude: 위도
            strict_korea: 한국 지역 제한 여부

        Returns:
            유효성 여부
        """
        # 기본 WGS84 범위 검증
        if not (self.MIN_LONGITUDE <= longitude <= self.MAX_LONGITUDE):
            return False
        if not (self.MIN_LATITUDE <= latitude <= self.MAX_LATITUDE):
            return False

        # 한국 지역 제한 검증
        if strict_korea:
            if not (self.KOREA_MIN_LONGITUDE <= longitude <= self.KOREA_MAX_LONGITUDE):
                return False
            if not (self.KOREA_MIN_LATITUDE <= latitude <= self.KOREA_MAX_LATITUDE):
                return False

        return True

    def calculate_distance(self, coord1: Tuple[float, float],
                          coord2: Tuple[float, float]) -> float:
        """
        두 좌표 간 거리 계산 (하버사인 공식)

        Args:
            coord1: 첫 번째 좌표 (경도, 위도)
            coord2: 두 번째 좌표 (경도, 위도)

        Returns:
            거리 (미터)
        """
        lon1, lat1 = coord1
        lon2, lat2 = coord2

        # 라디안 변환
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        # 하버사인 공식
        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(delta_lon / 2) ** 2)
        c = 2 * math.asin(math.sqrt(a))

        # 지구 반지름 (미터)
        earth_radius = 6371000
        distance = earth_radius * c

        return distance

    def validate_coordinate_list(self, coordinates: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """
        좌표 목록 검증 및 정제

        Args:
            coordinates: 좌표 목록

        Returns:
            유효한 좌표 목록
        """
        valid_coordinates = []

        for lon, lat in coordinates:
            if self.is_valid_coordinate(lon, lat):
                valid_coordinates.append((lon, lat))

        return valid_coordinates

    def get_bounding_box(self, coordinates: List[Tuple[float, float]]) -> Dict[str, float]:
        """
        좌표 목록의 바운딩 박스 계산

        Args:
            coordinates: 좌표 목록

        Returns:
            바운딩 박스 정보
        """
        if not coordinates:
            return {}

        lons = [coord[0] for coord in coordinates]
        lats = [coord[1] for coord in coordinates]

        return {
            'min_longitude': min(lons),
            'max_longitude': max(lons),
            'min_latitude': min(lats),
            'max_latitude': max(lats),
            'center_longitude': (min(lons) + max(lons)) / 2,
            'center_latitude': (min(lats) + max(lats)) / 2
        }

    def calculate_route_distance(self, coordinates: List[Tuple[float, float]]) -> float:
        """
        경로의 총 거리 계산

        Args:
            coordinates: 순서대로 정렬된 좌표 목록

        Returns:
            총 거리 (미터)
        """
        if len(coordinates) < 2:
            return 0.0

        total_distance = 0.0
        for i in range(len(coordinates) - 1):
            distance = self.calculate_distance(coordinates[i], coordinates[i + 1])
            total_distance += distance

        return total_distance

    def find_center_point(self, coordinates: List[Tuple[float, float]]) -> Optional[Tuple[float, float]]:
        """
        좌표들의 중심점 계산

        Args:
            coordinates: 좌표 목록

        Returns:
            중심점 좌표 (경도, 위도)
        """
        if not coordinates:
            return None

        total_lon = sum(coord[0] for coord in coordinates)
        total_lat = sum(coord[1] for coord in coordinates)
        count = len(coordinates)

        center_lon = total_lon / count
        center_lat = total_lat / count

        return (center_lon, center_lat)

    def is_within_korea_bounds(self, longitude: float, latitude: float) -> bool:
        """
        한국 경계 내 좌표인지 확인

        Args:
            longitude: 경도
            latitude: 위도

        Returns:
            한국 경계 내 여부
        """
        return (self.KOREA_MIN_LONGITUDE <= longitude <= self.KOREA_MAX_LONGITUDE and
                self.KOREA_MIN_LATITUDE <= latitude <= self.KOREA_MAX_LATITUDE)

    def validate_waypoint_data(self, waypoint_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        경유지 데이터 검증

        Args:
            waypoint_data: 경유지 데이터 목록

        Returns:
            검증된 경유지 데이터 목록
        """
        validated_data = []

        for waypoint in waypoint_data:
            try:
                # 좌표 추출
                longitude = float(waypoint.get('longitude', 0))
                latitude = float(waypoint.get('latitude', 0))

                # 좌표 유효성 검증
                if self.is_valid_coordinate(longitude, latitude):
                    validated_data.append(waypoint)
                else:
                    print(f"잘못된 좌표 제외: {waypoint.get('address', 'Unknown')} ({longitude}, {latitude})")

            except (ValueError, TypeError) as e:
                print(f"좌표 변환 실패: {waypoint.get('address', 'Unknown')} - {str(e)}")
                continue

        return validated_data

    def optimize_coordinate_precision(self, longitude: float, latitude: float,
                                    precision: int = 6) -> Tuple[float, float]:
        """
        좌표 정밀도 최적화 (소수점 자리수 제한)

        Args:
            longitude: 경도
            latitude: 위도
            precision: 소수점 자리수

        Returns:
            최적화된 좌표
        """
        return (round(longitude, precision), round(latitude, precision))

    def detect_coordinate_system(self, coordinates: List[Tuple[float, float]]) -> str:
        """
        좌표계 추정

        Args:
            coordinates: 좌표 목록

        Returns:
            추정된 좌표계
        """
        if not coordinates:
            return "UNKNOWN"

        # 좌표 범위 확인
        lons = [coord[0] for coord in coordinates]
        lats = [coord[1] for coord in coordinates]

        min_lon, max_lon = min(lons), max(lons)
        min_lat, max_lat = min(lats), max(lats)

        # WGS84 (경도/위도) 범위 확인
        if (-180 <= min_lon <= 180 and -90 <= min_lat <= 90 and
            -180 <= max_lon <= 180 and -90 <= max_lat <= 90):
            # 한국 좌표 범위 확인
            if (124 <= min_lon <= 132 and 33 <= min_lat <= 43):
                return "WGS84_KOREA"
            else:
                return "WGS84_GLOBAL"

        # 한국 측지계 (KATEC/TM) 추정
        if (min_lon > 100000 and min_lat > 100000):
            return "KATEC_OR_TM"

        return "UNKNOWN"

    def format_coordinate(self, longitude: float, latitude: float,
                         format_type: str = "decimal") -> str:
        """
        좌표 포맷 변환

        Args:
            longitude: 경도
            latitude: 위도
            format_type: 포맷 타입 (decimal, dms)

        Returns:
            포맷된 좌표 문자열
        """
        if format_type == "decimal":
            return f"{longitude:.6f}, {latitude:.6f}"
        elif format_type == "dms":
            # 도분초 변환
            def decimal_to_dms(decimal_degree):
                degrees = int(decimal_degree)
                minutes_float = (decimal_degree - degrees) * 60
                minutes = int(minutes_float)
                seconds = (minutes_float - minutes) * 60
                return degrees, minutes, seconds

            lon_d, lon_m, lon_s = decimal_to_dms(abs(longitude))
            lat_d, lat_m, lat_s = decimal_to_dms(abs(latitude))

            lon_dir = "E" if longitude >= 0 else "W"
            lat_dir = "N" if latitude >= 0 else "S"

            return f"{lat_d}°{lat_m}'{lat_s:.2f}\"{lat_dir}, {lon_d}°{lon_m}'{lon_s:.2f}\"{lon_dir}"

        return f"{longitude}, {latitude}"