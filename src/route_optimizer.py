#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
경로 최적화 엔진
지오코딩된 주소를 바탕으로 카카오 모빌리티 API를 통한 경로 최적화
"""

import logging
import math
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from kakao_api_client import KakaoRouteApiClient
from coordinate_utils import CoordinateValidator
from global_route_optimizer import GlobalRouteOptimizer

@dataclass
class RouteOptimizationResult:
    """경로 최적화 결과"""
    batch_id: int
    success: bool
    optimized_waypoints: List[Dict[str, Any]]
    total_distance: float  # 미터
    total_duration: float  # 초
    total_waypoints: int
    error_message: Optional[str] = None
    cluster_connection_distance: float = 0.0  # 이전 클러스터로부터의 연결거리 (미터)
    cluster_connection_duration: float = 0.0  # 이전 클러스터로부터의 연결시간 (초)

class RouteOptimizer:
    """다중 경유지 경로 최적화 클래스"""

    def __init__(self, api_key: str, logger: logging.Logger = None):
        self.api_client = KakaoRouteApiClient(api_key, logger)
        self.coordinate_validator = CoordinateValidator()
        self.global_optimizer = GlobalRouteOptimizer(logger, api_key)
        self.logger = logger or logging.getLogger(__name__)

        # 카카오 API 제약 조건
        self.MAX_WAYPOINTS_PER_BATCH = 30
        self.MAX_TOTAL_DISTANCE_KM = 1500

    def optimize_route(self, geocoded_data: List[Dict[str, Any]],
                      priority: str = "TIME") -> List[RouteOptimizationResult]:
        """
        지오코딩된 데이터를 기반으로 경로 최적화 수행

        Args:
            geocoded_data: 지오코딩된 주문 데이터
            priority: 경로 우선순위 (RECOMMEND/TIME/DISTANCE)

        Returns:
            배치별 최적화 결과 리스트
        """

        # Step 1: 좌표 검증 및 정제
        self.logger.info(f"🔍 입력 데이터: {len(geocoded_data)}개 주소")
        valid_waypoints = self._validate_and_filter_waypoints(geocoded_data)
        self.logger.info(f"🔍 좌표 검증 후: {len(valid_waypoints)}개 유효 지점")

        if not valid_waypoints:
            self.logger.error("유효한 경유지가 없습니다")
            return []

        self.logger.info(f"총 {len(valid_waypoints)}개 경유지 중 {len(valid_waypoints)}개 유효")

        # Step 2: Global Route Optimizer 통합 최적화 (API 기반 정확한 거리/시간)
        global_result = self.global_optimizer.optimize_global_clustering(valid_waypoints)

        # Global Route Optimizer 결과 구조 확인
        if isinstance(global_result, dict) and 'clusters' in global_result:
            # 새로운 구조적 결과 사용 - 하지만 기존 배치별 처리로 안전하게 처리
            batches = global_result['clusters']
            total_duration_minutes = global_result['total_duration_minutes']
            total_distance_km = global_result['total_distance_km']
            cluster_count = global_result['cluster_count']

            self.logger.info(f"🎉 Global Route Optimizer 최적 결과 사용:")
            self.logger.info(f"   총 시간: {total_duration_minutes:.3f}분")
            self.logger.info(f"   총 거리: {total_distance_km:.1f}km")
            self.logger.info(f"   클러스터: {cluster_count}개")

            # 기존 배치별 처리를 사용하되 Global Route Optimizer 총합 정보만 활용
            self.logger.info(f"⚡ Global 결과 적용을 위해 기존 배치별 처리 사용")
            # Global 결과를 저장해서 나중에 적용
            global_total_distance_km = total_distance_km
            global_total_duration_minutes = total_duration_minutes

        # 기존 방식으로 배치별 처리 (Global 또는 기존 결과 모두)
        if not isinstance(global_result, dict) or 'clusters' not in global_result:
            batches = global_result

        total_batch_waypoints = sum(len(batch) for batch in batches)
        self.logger.info(f"🔍 전역 최적화 후: {len(batches)}개 배치, 총 {total_batch_waypoints}개 지점")

        # 배치 누락 검사
        if total_batch_waypoints != len(valid_waypoints):
            self.logger.error(f"❌ 배치 분할 중 누락: {len(valid_waypoints)}개 → {total_batch_waypoints}개")
            for i, batch in enumerate(batches):
                self.logger.error(f"   배치 {i}: {len(batch)}개 지점")

        self.logger.info(f"전역 최적화: 총 {len(batches)}개 배치로 분할")

        # Step 3: 배치별 경로 최적화 (기존 방식)
        results = []
        prev_batch_last_waypoint = None

        for batch_idx, batch_waypoints in enumerate(batches):
            self.logger.info(f"🔍 배치 {batch_idx} 처리 시작: {len(batch_waypoints)}개 지점")
            result = self._optimize_single_batch(batch_idx, batch_waypoints, priority)

            # 클러스터간 연결거리 계산 (두 번째 배치부터)
            if batch_idx > 0 and prev_batch_last_waypoint and len(result.optimized_waypoints) > 0:
                current_batch_first_waypoint = result.optimized_waypoints[0]

                # 이전 배치 마지막 지점과 현재 배치 첫 지점 간 거리 계산
                connection_distance = self.coordinate_validator.calculate_distance(
                    (prev_batch_last_waypoint['longitude'], prev_batch_last_waypoint['latitude']),
                    (current_batch_first_waypoint['longitude'], current_batch_first_waypoint['latitude'])
                )

                # 연결시간 추정 (30km/h 평균속도 가정) - 주석처리: Global Route Optimizer의 정확한 API 결과 사용
                # connection_duration = (connection_distance / 1000) / 30 * 3600  # 초 단위

                # Global Route Optimizer에서 정확한 API 연결 거리/시간을 제공하므로 추정값 사용 중단
                result.cluster_connection_distance = connection_distance
                result.cluster_connection_duration = 0  # 추정값 대신 0으로 설정 (Global 결과 사용)

                self.logger.debug(f"🔗 배치간 연결: {connection_distance:.0f}m (추정시간 제거됨 - Global 결과 사용)")

            results.append(result)

            # 다음 배치를 위해 현재 배치의 마지막 지점 저장
            if len(result.optimized_waypoints) > 0:
                prev_batch_last_waypoint = result.optimized_waypoints[-1]

            self.logger.info(f"🔍 배치 {batch_idx} 완료: 성공={result.success}, 지점={len(result.optimized_waypoints)}개")

        # Global Route Optimizer 총합 정보를 첫 번째 결과에 적용
        if isinstance(global_result, dict) and 'clusters' in global_result and results:
            self.logger.info(f"🎉 Global Route Optimizer 총합 정보 적용:")
            self.logger.info(f"   총 시간: {global_total_duration_minutes:.3f}분")
            self.logger.info(f"   총 거리: {global_total_distance_km:.1f}km")

            # 첫 번째 결과에 Global 총합 정보 저장 (km를 미터로, 분을 초로 변환)
            results[0].total_distance = global_total_distance_km * 1000  # km → 미터
            results[0].total_duration = global_total_duration_minutes * 60  # 분 → 초

        # 최종 결과 검증
        total_result_waypoints = sum(len(r.optimized_waypoints) for r in results)
        success_count = sum(1 for r in results if r.success)
        self.logger.info(f"🔍 최종 결과: {len(results)}개 배치, 성공={success_count}/{len(results)} ({success_count/len(results)*100:.1f}%)")
        self.logger.info(f"🔍 최종 지점 수: {total_result_waypoints}개 (원본 {len(valid_waypoints)}개)")

        if total_result_waypoints != len(valid_waypoints):
            self.logger.error(f"❌ 최종 단계에서 누락 발생: {len(valid_waypoints)}개 → {total_result_waypoints}개")

        return results

    def _validate_and_filter_waypoints(self, geocoded_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """좌표 유효성 검증 및 정제"""
        valid_waypoints = []
        invalid_count = 0

        self.logger.debug(f"좌표 검증 시작: {len(geocoded_data)}개 주소")

        for i, order in enumerate(geocoded_data):
            try:
                longitude = float(order.get('longitude', 0))
                latitude = float(order.get('latitude', 0))

                # 좌표 유효성 검증
                if self.coordinate_validator.is_valid_coordinate(longitude, latitude):
                    waypoint = {
                        'id': order.get('id', ''),
                        'name': order.get('address', f"주문_{order.get('id', '')}"),
                        'x': longitude,  # 카카오 API는 x=경도, y=위도
                        'y': latitude,
                        'address': order.get('address', ''),
                        'road_address': order.get('road_address', ''),
                        'user_phone': order.get('user_phone', ''),
                        'msg_to_rider': order.get('msg_to_rider', ''),
                        'original_data': order
                    }
                    valid_waypoints.append(waypoint)
                else:
                    invalid_count += 1
                    self.logger.warning(f"❌ 유효하지 않은 좌표 #{i}: {order.get('address', 'Unknown')} ({longitude}, {latitude})")

            except (ValueError, TypeError) as e:
                invalid_count += 1
                self.logger.error(f"❌ 좌표 변환 실패 #{i}: {order.get('address', 'Unknown')} - {str(e)}")
                continue

        self.logger.info(f"좌표 검증 완료: {len(valid_waypoints)}개 유효, {invalid_count}개 무효")
        if invalid_count > 0:
            self.logger.error(f"❌ 좌표 검증 단계에서 {invalid_count}개 누락")

        return valid_waypoints

    def _split_into_batches(self, waypoints: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """경유지를 배치로 분할"""

        if len(waypoints) <= self.MAX_WAYPOINTS_PER_BATCH:
            return [waypoints]

        # 지리적 클러스터링 시도
        try:
            return self._geographic_clustering(waypoints)
        except Exception as e:
            self.logger.warning(f"지리적 클러스터링 실패: {str(e)}")
            # 순차적 분할로 대체
            return self._sequential_split(waypoints)

    def _geographic_clustering(self, waypoints: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """개선된 지리적 클러스터링 - 균등한 분포와 실무적 순서 고려"""

        num_batches = math.ceil(len(waypoints) / self.MAX_WAYPOINTS_PER_BATCH)

        # K-means 클러스터링으로 균등 분할
        clusters = self._improved_kmeans_clustering(waypoints, num_batches)

        # 클러스터별로 TSP 순서 최적화 (각 클러스터 내에서 효율적인 순서)
        optimized_batches = []
        for cluster in clusters:
            if len(cluster) > 2:
                # 클러스터 내 TSP 근사 알고리즘 적용
                ordered_cluster = self._optimize_cluster_order(cluster)
                optimized_batches.append(ordered_cluster)
            else:
                optimized_batches.append(cluster)

        return optimized_batches

    def _improved_kmeans_clustering(self, waypoints: List[Dict[str, Any]], k: int) -> List[List[Dict[str, Any]]]:
        """개선된 K-means 클러스터링 - 균등한 분포를 위한 제약 추가"""

        if k >= len(waypoints):
            return [[wp] for wp in waypoints]

        # K-means++ 초기화 (더 나은 초기 중심점 선택)
        centroids = self._kmeans_plus_plus_init(waypoints, k)

        max_iterations = 20
        target_size = len(waypoints) // k

        for iteration in range(max_iterations):
            # 각 경유지를 가장 가까운 중심점에 할당
            clusters = [[] for _ in range(k)]

            for waypoint in waypoints:
                closest_centroid_idx = self._find_closest_centroid_idx(waypoint, centroids)
                clusters[closest_centroid_idx].append(waypoint)

            # 클러스터 크기 균형 조정
            clusters = self._balance_cluster_sizes(clusters, target_size)

            # 새로운 중심점 계산
            new_centroids = []
            converged = True

            for i, cluster in enumerate(clusters):
                if cluster:
                    avg_x = sum(wp['x'] for wp in cluster) / len(cluster)
                    avg_y = sum(wp['y'] for wp in cluster) / len(cluster)
                    new_centroid = (avg_x, avg_y)

                    # 수렴 검사
                    if self.coordinate_validator.calculate_distance(centroids[i], new_centroid) > 100:  # 100m 이상 변화
                        converged = False

                    new_centroids.append(new_centroid)
                else:
                    new_centroids.append(centroids[i])

            centroids = new_centroids

            if converged:
                break

        return [cluster for cluster in clusters if cluster]

    def _kmeans_plus_plus_init(self, waypoints: List[Dict[str, Any]], k: int) -> List[Tuple[float, float]]:
        """K-means++ 초기화 - 더 나은 초기 중심점 선택"""
        centroids = []

        # 첫 번째 중심점은 랜덤 선택
        first_wp = waypoints[0]  # 안정성을 위해 첫 번째 사용
        centroids.append((first_wp['x'], first_wp['y']))

        # 나머지 중심점들을 거리 기반으로 선택
        for _ in range(k - 1):
            max_min_distance = 0
            best_candidate = None

            for wp in waypoints:
                wp_coord = (wp['x'], wp['y'])
                # 가장 가까운 기존 중심점까지의 거리 찾기
                min_distance_to_centroids = min(
                    self.coordinate_validator.calculate_distance(wp_coord, centroid)
                    for centroid in centroids
                )

                # 가장 먼 거리의 점을 다음 중심점으로 선택
                if min_distance_to_centroids > max_min_distance:
                    max_min_distance = min_distance_to_centroids
                    best_candidate = wp_coord

            if best_candidate:
                centroids.append(best_candidate)
            else:
                # fallback: 임의의 점 선택
                fallback_wp = waypoints[len(centroids)]
                centroids.append((fallback_wp['x'], fallback_wp['y']))

        return centroids

    def _find_closest_centroid_idx(self, waypoint: Dict[str, Any], centroids: List[Tuple[float, float]]) -> int:
        """가장 가까운 중심점의 인덱스 찾기"""
        wp_coord = (waypoint['x'], waypoint['y'])
        min_distance = float('inf')
        closest_idx = 0

        for i, centroid in enumerate(centroids):
            distance = self.coordinate_validator.calculate_distance(wp_coord, centroid)
            if distance < min_distance:
                min_distance = distance
                closest_idx = i

        return closest_idx

    def _balance_cluster_sizes(self, clusters: List[List[Dict[str, Any]]], target_size: int) -> List[List[Dict[str, Any]]]:
        """클러스터 크기 균형 조정 - 너무 큰 클러스터에서 작은 클러스터로 이동"""
        max_allowed_size = self.MAX_WAYPOINTS_PER_BATCH

        # 크기가 초과된 클러스터에서 가장 가까운 다른 클러스터로 이동
        while True:
            moved = False

            for i, cluster in enumerate(clusters):
                if len(cluster) > max_allowed_size:
                    # 가장 외곽의 점을 찾아서 이동
                    if len(cluster) > 1:
                        # 클러스터 중심 계산
                        center_x = sum(wp['x'] for wp in cluster) / len(cluster)
                        center_y = sum(wp['y'] for wp in cluster) / len(cluster)

                        # 중심에서 가장 먼 점 찾기
                        max_distance = 0
                        farthest_wp = None
                        farthest_idx = -1

                        for j, wp in enumerate(cluster):
                            distance = self.coordinate_validator.calculate_distance(
                                (center_x, center_y), (wp['x'], wp['y'])
                            )
                            if distance > max_distance:
                                max_distance = distance
                                farthest_wp = wp
                                farthest_idx = j

                        if farthest_wp:
                            # 가장 여유 있는 클러스터 찾기
                            min_size = min(len(c) for c in clusters)
                            for j, other_cluster in enumerate(clusters):
                                if i != j and len(other_cluster) == min_size and len(other_cluster) < max_allowed_size:
                                    # 점 이동
                                    clusters[i].remove(farthest_wp)
                                    clusters[j].append(farthest_wp)
                                    moved = True
                                    break

            if not moved:
                break

        return clusters

    def _optimize_cluster_order(self, cluster: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """클러스터 내 경유지 순서 최적화 (TSP 근사 알고리즘)"""
        if len(cluster) <= 2:
            return cluster

        # Nearest Neighbor TSP 알고리즘
        visited = set()
        ordered_cluster = []

        # 시작점: 클러스터 내 가장 외곽 점 (배송 효율성 고려)
        current = self._find_cluster_boundary_point(cluster)
        visited.add(id(current))
        ordered_cluster.append(current)

        # 가장 가까운 미방문 점을 순차적으로 선택
        while len(visited) < len(cluster):
            nearest_wp = None
            min_distance = float('inf')

            current_coord = (current['x'], current['y'])

            for wp in cluster:
                if id(wp) not in visited:
                    distance = self.coordinate_validator.calculate_distance(
                        current_coord, (wp['x'], wp['y'])
                    )
                    if distance < min_distance:
                        min_distance = distance
                        nearest_wp = wp

            if nearest_wp:
                visited.add(id(nearest_wp))
                ordered_cluster.append(nearest_wp)
                current = nearest_wp

        return ordered_cluster

    def _find_cluster_boundary_point(self, cluster: List[Dict[str, Any]]) -> Dict[str, Any]:
        """클러스터의 경계점(가장 외곽) 찾기"""
        # 클러스터 중심 계산
        center_x = sum(wp['x'] for wp in cluster) / len(cluster)
        center_y = sum(wp['y'] for wp in cluster) / len(cluster)

        # 중심에서 가장 먼 점이 경계점
        max_distance = 0
        boundary_point = cluster[0]

        for wp in cluster:
            distance = self.coordinate_validator.calculate_distance(
                (center_x, center_y), (wp['x'], wp['y'])
            )
            if distance > max_distance:
                max_distance = distance
                boundary_point = wp

        return boundary_point

    def _sequential_split(self, waypoints: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """순차적 분할"""
        batches = []
        for i in range(0, len(waypoints), self.MAX_WAYPOINTS_PER_BATCH):
            batch = waypoints[i:i + self.MAX_WAYPOINTS_PER_BATCH]
            batches.append(batch)
        return batches

    def _select_optimal_start_end_points(self, waypoints: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        최적의 출발지와 종료지를 선택
        - 서로 가장 가까운 두 지점을 선택하되, 너무 가까우면 제외
        - 기사가 시작 지점으로 돌아올 수 있도록 고려
        """
        if len(waypoints) == 2:
            return waypoints[0], waypoints[1]

        min_distance = float('inf')
        best_origin = waypoints[0]
        best_destination = waypoints[-1]

        # 최소 거리 임계값 설정 (500미터 - 너무 가까운 지점 제외)
        MIN_DISTANCE_THRESHOLD = 500

        # 모든 지점 쌍에 대해 거리 계산
        for i, origin_candidate in enumerate(waypoints):
            for j, dest_candidate in enumerate(waypoints):
                if i == j:
                    continue

                distance = self.coordinate_validator.calculate_distance(
                    (origin_candidate['x'], origin_candidate['y']),
                    (dest_candidate['x'], dest_candidate['y'])
                )

                # 너무 가까우면 제외
                if distance < MIN_DISTANCE_THRESHOLD:
                    continue

                # 가장 가까운 지점 쌍 찾기
                if distance < min_distance:
                    min_distance = distance
                    best_origin = origin_candidate
                    best_destination = dest_candidate

        # 적절한 지점 쌍을 찾지 못한 경우, 기존 방식 사용
        if min_distance == float('inf'):
            self.logger.warning("적절한 출발지/종료지 쌍을 찾지 못함. 기존 방식 사용")
            return waypoints[0], waypoints[-1]

        self.logger.info(f"선택된 출발지-종료지 거리: {min_distance:.0f}m")
        return best_origin, best_destination

    def _optimize_single_batch(self, batch_idx: int, waypoints: List[Dict[str, Any]],
                              priority: str) -> RouteOptimizationResult:
        """단일 배치 경로 최적화"""

        try:
            # 단일 지점 처리: 출발지=목적지로 설정하여 정상 처리
            if len(waypoints) == 1:
                single_waypoint = waypoints[0]
                self.logger.info(f"배치 {batch_idx}: 단일 지점 처리 (출발지=목적지)")

                # 단일 지점의 경우 기본 배송 시간과 최소 이동거리 설정
                base_duration = 120  # 2분 (기본 배송/처리 시간, 초 단위)
                base_distance = 50   # 50미터 (최소 이동 거리, 미터 단위)

                optimized_waypoints = [
                    {
                        'sequence': 0,
                        'waypoint_type': '출발지/목적지',
                        'order_id': single_waypoint.get('id', ''),
                        'name': single_waypoint.get('name', ''),
                        'address': single_waypoint.get('address', ''),
                        'road_address': single_waypoint.get('road_address', ''),
                        'longitude': single_waypoint.get('x', 0.0),  # x = 경도
                        'latitude': single_waypoint.get('y', 0.0),   # y = 위도
                        'user_phone': single_waypoint.get('user_phone', ''),
                        'msg_to_rider': single_waypoint.get('msg_to_rider', ''),
                        'distance_from_prev': base_distance,
                        'duration_from_prev': base_duration,
                        'cumulative_distance': base_distance,
                        'cumulative_duration': base_duration
                    }
                ]

                return RouteOptimizationResult(
                    batch_id=batch_idx,
                    success=True,
                    optimized_waypoints=optimized_waypoints,
                    total_distance=base_distance,
                    total_duration=base_duration,
                    total_waypoints=1,
                    error_message=None
                )

            if len(waypoints) < 1:
                return RouteOptimizationResult(
                    batch_id=batch_idx,
                    success=False,
                    optimized_waypoints=[],
                    total_distance=0,
                    total_duration=0,
                    total_waypoints=len(waypoints),
                    error_message="유효한 지점이 없습니다"
                )

            # 전역 최적화에서 이미 순서가 최적화되었으므로 첫 번째와 마지막을 시작/종료점으로 사용
            origin = waypoints[0]
            destination = waypoints[-1]
            intermediate_waypoints = waypoints[1:-1] if len(waypoints) > 2 else []

            self.logger.info(f"배치 {batch_idx}: 출발지 1개, 경유지 {len(intermediate_waypoints)}개, 목적지 1개")

            # 카카오 API 호출
            api_response = self.api_client.get_optimized_route(
                origin=origin,
                destination=destination,
                waypoints=intermediate_waypoints,
                priority=priority
            )

            # 결과 파싱
            route_summary = self.api_client.get_route_summary(api_response)

            if route_summary.get('result_code') != 0:
                return RouteOptimizationResult(
                    batch_id=batch_idx,
                    success=False,
                    optimized_waypoints=[],
                    total_distance=0,
                    total_duration=0,
                    total_waypoints=len(waypoints),
                    error_message=route_summary.get('result_msg', '경로 최적화 실패')
                )

            # 최적화된 경유지 순서 생성
            optimized_waypoints = self._build_optimized_waypoint_sequence(
                api_response, origin, destination, intermediate_waypoints
            )

            return RouteOptimizationResult(
                batch_id=batch_idx,
                success=True,
                optimized_waypoints=optimized_waypoints,
                total_distance=route_summary.get('total_distance', 0),
                total_duration=route_summary.get('total_duration', 0),
                total_waypoints=len(waypoints)
            )

        except Exception as e:
            self.logger.error(f"배치 {batch_idx} 최적화 실패: {str(e)}")
            return RouteOptimizationResult(
                batch_id=batch_idx,
                success=False,
                optimized_waypoints=[],
                total_distance=0,
                total_duration=0,
                total_waypoints=len(waypoints),
                error_message=str(e)
            )

    def _build_optimized_waypoint_sequence(self, api_response: Dict, origin: Dict,
                                         destination: Dict, waypoints: List[Dict]) -> List[Dict[str, Any]]:
        """API 응답을 기반으로 최적화된 경유지 순서 구성"""

        optimized_sequence = []
        cumulative_distance = 0
        cumulative_duration = 0

        # 출발지 추가
        optimized_sequence.append({
            'sequence': 0,
            'waypoint_type': 'origin',
            'order_id': origin.get('id', ''),
            'name': origin.get('name', ''),
            'address': origin.get('address', ''),
            'road_address': origin.get('road_address', ''),
            'longitude': origin['x'],
            'latitude': origin['y'],
            'user_phone': origin.get('user_phone', ''),
            'msg_to_rider': origin.get('msg_to_rider', ''),
            'distance_from_prev': 0,
            'duration_from_prev': 0,
            'cumulative_distance': cumulative_distance,
            'cumulative_duration': cumulative_duration
        })

        # API 응답에서 경로 상세 정보 추출
        route_details = self.api_client.extract_route_details(api_response)

        # 중간 경유지들 추가 (API에서 최적화된 순서로)
        for i, waypoint in enumerate(waypoints):
            section_info = route_details[i] if i < len(route_details) else {}

            distance_from_prev = section_info.get('distance', 0)
            duration_from_prev = section_info.get('duration', 0)
            cumulative_distance += distance_from_prev
            cumulative_duration += duration_from_prev

            optimized_sequence.append({
                'sequence': i + 1,
                'waypoint_type': 'waypoint',
                'order_id': waypoint.get('id', ''),
                'name': waypoint.get('name', ''),
                'address': waypoint.get('address', ''),
                'road_address': waypoint.get('road_address', ''),
                'longitude': waypoint['x'],
                'latitude': waypoint['y'],
                'user_phone': waypoint.get('user_phone', ''),
                'msg_to_rider': waypoint.get('msg_to_rider', ''),
                'distance_from_prev': distance_from_prev,
                'duration_from_prev': duration_from_prev,
                'cumulative_distance': cumulative_distance,
                'cumulative_duration': cumulative_duration
            })

        # 목적지 추가
        final_section = route_details[-1] if route_details else {}
        distance_from_prev = final_section.get('distance', 0)
        duration_from_prev = final_section.get('duration', 0)
        cumulative_distance += distance_from_prev
        cumulative_duration += duration_from_prev

        optimized_sequence.append({
            'sequence': len(optimized_sequence),
            'waypoint_type': 'destination',
            'order_id': destination.get('id', ''),
            'name': destination.get('name', ''),
            'address': destination.get('address', ''),
            'road_address': destination.get('road_address', ''),
            'longitude': destination['x'],
            'latitude': destination['y'],
            'user_phone': destination.get('user_phone', ''),
            'msg_to_rider': destination.get('msg_to_rider', ''),
            'distance_from_prev': distance_from_prev,
            'duration_from_prev': duration_from_prev,
            'cumulative_distance': cumulative_distance,
            'cumulative_duration': cumulative_duration
        })

        return optimized_sequence

    def get_optimization_summary(self, results: List[RouteOptimizationResult]) -> Dict[str, Any]:
        """최적화 결과 요약 정보 생성 - Global Route Optimizer 결과 우선 사용"""

        successful_batches = [r for r in results if r.success]
        failed_batches = [r for r in results if not r.success]

        total_waypoints = sum(r.total_waypoints for r in results)

        # Global Route Optimizer 결과가 있는지 확인 (첫 번째 결과에 저장됨)
        if results and results[0].total_distance > 0:
            # Global Route Optimizer의 정확한 API 결과 사용 (미터→km, 초→시간 변환)
            total_distance_km = results[0].total_distance / 1000  # 미터 → km
            total_duration_hours = results[0].total_duration / 3600  # 초 → 시간
            total_duration_minutes = results[0].total_duration / 60  # 초 → 분

            self.logger.info(f"📊 Global Route Optimizer 정확한 결과 사용:")
            self.logger.info(f"   총 거리: {total_distance_km:.2f}km")
            self.logger.info(f"   총 시간: {total_duration_minutes:.3f}분 ({total_duration_hours:.2f}시간)")

            return {
                'total_batches': len(results),
                'successful_batches': len(successful_batches),
                'failed_batches': len(failed_batches),
                'total_waypoints': total_waypoints,
                'total_distance_km': total_distance_km,
                'total_duration_hours': total_duration_hours,
                'average_speed_kmh': total_distance_km / total_duration_hours if total_duration_hours > 0 else 0,
                'success_rate': len(successful_batches) / len(results) * 100 if results else 0
            }

        else:
            # 기존 방식 (호환성 유지) - 추정값 기반
            self.logger.warning("⚠️ Global Route Optimizer 결과 없음 - 기존 방식 사용 (추정값)")

            # 클러스터 내 거리/시간과 클러스터 간 연결 거리/시간을 모두 포함
            total_distance = sum(r.total_distance for r in successful_batches)
            total_duration = sum(r.total_duration for r in successful_batches)

            # 클러스터 간 연결 거리/시간 추가
            connection_distance = sum(r.cluster_connection_distance for r in successful_batches)
            connection_duration = sum(r.cluster_connection_duration for r in successful_batches)

            # 전체 거리/시간 = 클러스터 내 + 클러스터 간 연결
            total_distance_with_connections = total_distance + connection_distance
            total_duration_with_connections = total_duration + connection_duration

            return {
                'total_batches': len(results),
                'successful_batches': len(successful_batches),
                'failed_batches': len(failed_batches),
                'total_waypoints': total_waypoints,
                'total_distance_km': total_distance_with_connections / 1000,
                'total_duration_hours': total_duration_with_connections / 3600,
                'average_speed_kmh': (total_distance_with_connections / 1000) / (total_duration_with_connections / 3600) if total_duration_with_connections > 0 else 0,
                'success_rate': len(successful_batches) / len(results) * 100 if results else 0
            }