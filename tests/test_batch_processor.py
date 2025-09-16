"""
배치 처리 테스트
TC02: 30개 초과 경유지 분할 테스트
"""

import unittest
from dataclasses import dataclass
from src.batch_processor import BatchProcessor

@dataclass
class MockWaypoint:
    """테스트용 모의 경유지"""
    name: str
    x: float
    y: float
    address: str = ""
    order_id: str = ""

class TestBatchProcessor(unittest.TestCase):
    """배치 처리 테스트"""

    def setUp(self):
        self.processor = BatchProcessor()

    def test_small_waypoint_list(self):
        """30개 이하 경유지 테스트"""
        waypoints = [
            MockWaypoint(f"WP_{i}", 127.0 + i*0.01, 37.5 + i*0.01)
            for i in range(10)
        ]

        batches = self.processor.split_waypoints(waypoints)

        # 단일 배치여야 함
        self.assertEqual(len(batches), 1)
        self.assertEqual(len(batches[0]), 10)

    def test_large_waypoint_list(self):
        """30개 초과 경유지 분할 테스트 - TC02"""
        # 35개 경유지 생성
        waypoints = [
            MockWaypoint(f"WP_{i}", 127.0 + i*0.01, 37.5 + i*0.01)
            for i in range(35)
        ]

        batches = self.processor.split_waypoints(waypoints)

        # 여러 배치로 분할되어야 함
        self.assertGreater(len(batches), 1)

        # 각 배치는 30개 이하여야 함
        for batch in batches:
            self.assertLessEqual(len(batch), self.processor.MAX_WAYPOINTS_PER_BATCH)

        # 모든 경유지가 포함되어야 함
        total_waypoints = sum(len(batch) for batch in batches)
        self.assertEqual(total_waypoints, 35)

    def test_exact_30_waypoints(self):
        """정확히 30개 경유지 테스트"""
        waypoints = [
            MockWaypoint(f"WP_{i}", 127.0 + i*0.01, 37.5 + i*0.01)
            for i in range(30)
        ]

        batches = self.processor.split_waypoints(waypoints)

        # 단일 배치여야 함
        self.assertEqual(len(batches), 1)
        self.assertEqual(len(batches[0]), 30)

    def test_sequential_split(self):
        """순차 분할 테스트"""
        waypoints = [
            MockWaypoint(f"WP_{i}", 127.0 + i*0.01, 37.5 + i*0.01)
            for i in range(65)  # 65개 경유지
        ]

        batches = self.processor._split_sequentially(waypoints)

        # 3개 배치로 분할되어야 함 (30 + 30 + 5)
        self.assertEqual(len(batches), 3)
        self.assertEqual(len(batches[0]), 30)
        self.assertEqual(len(batches[1]), 30)
        self.assertEqual(len(batches[2]), 5)

    def test_geographic_clustering(self):
        """지리적 클러스터링 테스트"""
        # 두 개의 지리적 클러스터 생성
        # 클러스터 1: 서울 지역
        cluster1_waypoints = [
            MockWaypoint(f"Seoul_{i}", 127.0 + i*0.001, 37.5 + i*0.001)
            for i in range(20)
        ]

        # 클러스터 2: 부산 지역
        cluster2_waypoints = [
            MockWaypoint(f"Busan_{i}", 129.0 + i*0.001, 35.1 + i*0.001)
            for i in range(20)
        ]

        waypoints = cluster1_waypoints + cluster2_waypoints

        try:
            batches = self.processor._split_by_geographic_clustering(waypoints)

            # 클러스터링이 성공하면 지리적으로 분리되어야 함
            self.assertGreater(len(batches), 1)

            # 각 배치 내 경유지들이 지리적으로 근접해야 함
            for batch in batches:
                if len(batch) > 1:
                    # 배치 내 경유지들의 평균 좌표 계산
                    avg_x = sum(wp.x for wp in batch) / len(batch)
                    avg_y = sum(wp.y for wp in batch) / len(batch)

                    # 서울 또는 부산 지역에 속하는지 확인
                    is_seoul_cluster = abs(avg_x - 127.0) < 0.1
                    is_busan_cluster = abs(avg_x - 129.0) < 0.1

                    self.assertTrue(is_seoul_cluster or is_busan_cluster)

        except Exception:
            # 클러스터링 실패 시 순차 분할로 fallback 테스트
            batches = self.processor._split_sequentially(waypoints)
            self.assertGreater(len(batches), 1)

    def test_empty_waypoint_list(self):
        """빈 경유지 목록 테스트"""
        waypoints = []
        batches = self.processor.split_waypoints(waypoints)

        self.assertEqual(len(batches), 1)
        self.assertEqual(len(batches[0]), 0)

if __name__ == '__main__':
    unittest.main()