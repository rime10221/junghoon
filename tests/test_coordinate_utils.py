"""
좌표 유틸리티 테스트
TC04: 좌표 검증 테스트 케이스
"""

import unittest
from src.coordinate_utils import CoordinateValidator

class TestCoordinateValidator(unittest.TestCase):
    """좌표 검증 테스트"""

    def setUp(self):
        self.validator = CoordinateValidator()

    def test_valid_coordinates(self):
        """유효한 좌표 테스트 - TC01 관련"""
        # 서울 좌표
        self.assertTrue(self.validator.is_valid_coordinate(127.0276, 37.4979))
        # 부산 좌표
        self.assertTrue(self.validator.is_valid_coordinate(129.0756, 35.1796))

    def test_invalid_coordinates(self):
        """무효한 좌표 테스트 - TC04"""
        # 경도 범위 초과
        self.assertFalse(self.validator.is_valid_coordinate(200.0, 37.4979))
        self.assertFalse(self.validator.is_valid_coordinate(-200.0, 37.4979))

        # 위도 범위 초과
        self.assertFalse(self.validator.is_valid_coordinate(127.0276, 100.0))
        self.assertFalse(self.validator.is_valid_coordinate(127.0276, -100.0))

    def test_distance_calculation(self):
        """거리 계산 테스트"""
        # 서울-부산 대략 거리 (약 325km)
        seoul = (127.0276, 37.4979)
        busan = (129.0756, 35.1796)

        distance = self.validator.calculate_distance(seoul, busan)

        # 대략적 거리 검증 (300-350km 범위)
        self.assertGreater(distance, 300000)  # 300km
        self.assertLess(distance, 350000)     # 350km

    def test_coordinate_list_validation(self):
        """좌표 목록 검증 테스트"""
        coordinates = [
            (127.0276, 37.4979),  # 유효
            (200.0, 37.4979),     # 무효 (경도 초과)
            (129.0756, 35.1796),  # 유효
            (127.0276, 100.0),    # 무효 (위도 초과)
        ]

        valid_coords = self.validator.validate_coordinate_list(coordinates)

        # 유효한 좌표만 2개 남아야 함
        self.assertEqual(len(valid_coords), 2)
        self.assertIn((127.0276, 37.4979), valid_coords)
        self.assertIn((129.0756, 35.1796), valid_coords)

if __name__ == '__main__':
    unittest.main()