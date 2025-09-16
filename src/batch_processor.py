"""
배치 처리 및 경유지 분할 로직
K9: 배치 처리 최적화, K2: API 제약 조건
"""

import math
from typing import List, Dict, Any
from dataclasses import dataclass
from .coordinate_utils import CoordinateValidator

@dataclass
class WaypointCluster:
    """경유지 클러스터 정보"""
    center_x: float
    center_y: float
    waypoints: List[Any]
    total_distance: float

class BatchProcessor:
    """경유지 배치 처리 클래스"""

    MAX_WAYPOINTS_PER_BATCH = 30  # K2: API 제약 조건

    def __init__(self):
        self.coordinate_validator = CoordinateValidator()

    def split_waypoints(self, waypoints: List[Any]) -> List[List[Any]]:
        """
        경유지를 30개 이하 배치로 분할
        K9: 배치 처리, R5: 30개 초과 분할 규칙
        """
        if len(waypoints) <= self.MAX_WAYPOINTS_PER_BATCH:
            return [waypoints]

        # B1: 분할 전략 선택
        # 지리적 클러스터링 우선, 실패 시 순차 분할
        try:
            return self._split_by_geographic_clustering(waypoints)
        except Exception:
            return self._split_sequentially(waypoints)

    def _split_by_geographic_clustering(self, waypoints: List[Any]) -> List[List[Any]]:
        """
        지리적 근접성 기반 클러스터링 분할
        K3: 좌표계 기반 거리 계산
        """
        # 필요한 클러스터 수 계산
        num_clusters = math.ceil(len(waypoints) / self.MAX_WAYPOINTS_PER_BATCH)

        # K-means 유사 클러스터링 수행
        clusters = self._perform_kmeans_clustering(waypoints, num_clusters)

        # 각 클러스터가 30개 이하인지 검증
        batches = []
        for cluster in clusters:
            if len(cluster.waypoints) <= self.MAX_WAYPOINTS_PER_BATCH:
                batches.append(cluster.waypoints)
            else:
                # 큰 클러스터는 추가 분할
                sub_batches = self._split_sequentially(cluster.waypoints)
                batches.extend(sub_batches)

        return batches

    def _perform_kmeans_clustering(self, waypoints: List[Any], k: int) -> List[WaypointCluster]:
        """
        K-means 클러스터링 수행
        K3: 좌표계 기반 중심점 계산
        """
        if k >= len(waypoints):
            # 클러스터 수가 경유지 수보다 많으면 개별 클러스터 생성
            return [WaypointCluster(wp.x, wp.y, [wp], 0.0) for wp in waypoints]

        # 초기 중심점 설정 (첫 k개 경유지 사용)
        centroids = [(waypoints[i].x, waypoints[i].y) for i in range(k)]

        max_iterations = 10
        for iteration in range(max_iterations):
            # 각 경유지를 가장 가까운 중심점에 할당
            clusters = [[] for _ in range(k)]

            for waypoint in waypoints:
                closest_centroid_idx = self._find_closest_centroid(
                    (waypoint.x, waypoint.y), centroids
                )
                clusters[closest_centroid_idx].append(waypoint)

            # 새로운 중심점 계산
            new_centroids = []
            for cluster in clusters:
                if cluster:
                    avg_x = sum(wp.x for wp in cluster) / len(cluster)
                    avg_y = sum(wp.y for wp in cluster) / len(cluster)
                    new_centroids.append((avg_x, avg_y))
                else:
                    # 빈 클러스터는 기존 중심점 유지
                    new_centroids.append(centroids[len(new_centroids)])

            # 수렴 검사
            if self._centroids_converged(centroids, new_centroids):
                break

            centroids = new_centroids

        # 클러스터 객체 생성
        cluster_objects = []
        for i, cluster in enumerate(clusters):
            if cluster:
                total_distance = self._calculate_cluster_total_distance(cluster)
                cluster_objects.append(WaypointCluster(
                    center_x=centroids[i][0],
                    center_y=centroids[i][1],
                    waypoints=cluster,
                    total_distance=total_distance
                ))

        return cluster_objects

    def _find_closest_centroid(self, point: tuple, centroids: List[tuple]) -> int:
        """가장 가까운 중심점 찾기"""
        min_distance = float('inf')
        closest_idx = 0

        for i, centroid in enumerate(centroids):
            distance = self.coordinate_validator.calculate_distance(point, centroid)
            if distance < min_distance:
                min_distance = distance
                closest_idx = i

        return closest_idx

    def _centroids_converged(self, old_centroids: List[tuple],
                           new_centroids: List[tuple], tolerance: float = 0.001) -> bool:
        """중심점 수렴 여부 검사"""
        for old, new in zip(old_centroids, new_centroids):
            distance = self.coordinate_validator.calculate_distance(old, new)
            if distance > tolerance * 1000:  # 1m 단위 허용 오차
                return False
        return True

    def _calculate_cluster_total_distance(self, waypoints: List[Any]) -> float:
        """클러스터 내 총 거리 계산"""
        if len(waypoints) < 2:
            return 0.0

        total_distance = 0.0
        for i in range(len(waypoints) - 1):
            distance = self.coordinate_validator.calculate_distance(
                (waypoints[i].x, waypoints[i].y),
                (waypoints[i + 1].x, waypoints[i + 1].y)
            )
            total_distance += distance

        return total_distance

    def _split_sequentially(self, waypoints: List[Any]) -> List[List[Any]]:
        """
        순차적 분할 (fallback 방법)
        R5: 30개 초과 시 분할 규칙
        """
        batches = []
        current_batch = []

        for waypoint in waypoints:
            current_batch.append(waypoint)

            if len(current_batch) >= self.MAX_WAYPOINTS_PER_BATCH:
                batches.append(current_batch)
                current_batch = []

        # 마지막 배치 추가
        if current_batch:
            batches.append(current_batch)

        return batches

    def estimate_total_distance(self, batches: List[List[Any]]) -> float:
        """배치별 총 예상 거리 계산"""
        total_distance = 0.0

        for batch in batches:
            batch_distance = self._calculate_cluster_total_distance(batch)
            total_distance += batch_distance

        return total_distance