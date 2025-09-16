#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
전역 경로 최적화 엔진
클러스터 간 연결성을 고려한 스마트 클러스터링
"""

import logging
import math
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from coordinate_utils import CoordinateValidator

@dataclass
class GlobalRouteCluster:
    """전역 최적화된 클러스터"""
    id: int
    waypoints: List[Dict[str, Any]]
    start_point: Dict[str, Any]
    end_point: Dict[str, Any]
    internal_distance: float  # 클러스터 내부 예상 거리

@dataclass
class ClusteringPerformance:
    """클러스터링 성능 평가 결과"""
    num_clusters: int
    clusters: List[GlobalRouteCluster]
    estimated_total_time: float  # 예상 총 시간 (분)
    estimated_total_distance: float  # 예상 총 거리 (km)
    balance_score: float  # 클러스터 간 균형 점수 (0-1)
    connectivity_score: float  # 클러스터 간 연결성 점수 (0-1)

class GlobalRouteOptimizer:
    """전역 경로 연결성을 고려한 클러스터링 최적화"""

    def __init__(self, logger: logging.Logger = None, api_key: str = None):
        self.coordinate_validator = CoordinateValidator()
        self.logger = logger or logging.getLogger(__name__)
        self.MAX_WAYPOINTS_PER_BATCH = 30
        self.api_key = api_key  # 실제 API 호출을 위한 키

    def optimize_global_clustering(self, waypoints: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        성능 기반 전역 경로 최적화 메인 함수
        1. 단일 클러스터 가능하면 → 시간 측정 후 최적 선택
        2. 다중 클러스터 → 2~5개 시나리오 중 가장 빠른 것 선택
        """
        total_waypoints = len(waypoints)

        # 카카오 API가 경유지 순서 최적화를 제공하지 않으므로
        # 모든 경우에 클러스터링으로 TSP 최적화 적용
        if total_waypoints <= 3:
            # 극소수 경유지는 단순 TSP로 처리 (3개 이하)
            self.logger.info(f"극소규모 TSP 모드: {total_waypoints}개 지점 직접 최적화")
            single_cluster = self._optimize_single_cluster_global(waypoints)
            # 단일 클러스터도 동일한 형식으로 반환
            return {
                'clusters': [single_cluster],
                'total_duration_minutes': 0,  # 단일 클러스터는 API 측정값 없음
                'total_distance_km': 0,       # 단일 클러스터는 API 측정값 없음
                'cluster_count': 1
            }
        else:
            # 성능 기반 다중 클러스터 최적화
            self.logger.info(f"성능 기반 클러스터링 모드: {total_waypoints}개 → 최고 성능 시나리오 탐색")
            return self._find_optimal_clustering_performance(waypoints)

    def _find_optimal_clustering_performance(self, waypoints: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """실제 API 호출 기반 최적 클러스터링 탐색"""
        total_waypoints = len(waypoints)

        # 실제 측정 기반 클러스터 개수 범위 - 절반까지만 테스트
        min_clusters = 2  # 최소 2개 클러스터
        max_clusters = max(2, round(total_waypoints / 2))  # 최대값: 경유지 수의 절반 (홀수면 반올림)

        self.logger.info(f"🔍 실제 API 성능 측정: {total_waypoints}개 경유지 → {min_clusters}~{max_clusters}개 클러스터 전체 테스트")

        best_performance = None
        best_actual_time = float('inf')
        self._best_global_distance = float('inf')  # 순환성 비교를 위한 초기값

        # 모든 가능한 클러스터 개수에 대해 실제 API 테스트
        for num_clusters in range(min_clusters, max_clusters + 1):
            try:
                self.logger.info(f"📊 {num_clusters}개 클러스터 실제 API 테스트 시작...")

                # 실제 API 호출로 성능 측정
                actual_time, actual_distance, clusters = self._test_real_api_performance(waypoints, num_clusters)

                self.logger.info(f"✅ {num_clusters}개 클러스터: 실제 시간 {actual_time:.3f}분, 거리 {actual_distance:.1f}km")

                # 최고 성능 업데이트 (시간 우선, 동일 시간일 때 순환성 고려)
                is_better = False

                # 순환성 계산 (시작-끝점 거리)
                global_distance_m = float('inf')
                if len(clusters) > 1:
                    global_start = clusters[0][0] if clusters[0] else None
                    global_end = clusters[-1][-1] if clusters[-1] else None
                    if global_start and global_end:
                        global_distance_m = self.coordinate_validator.calculate_distance(
                            (global_start['x'], global_start['y']),
                            (global_end['x'], global_end['y'])
                        )

                if actual_time < best_actual_time:
                    # 더 빠른 시간 → 무조건 선택
                    is_better = True
                    self.logger.info(f"🏆 새로운 최고 기록: {num_clusters}개 클러스터 ({actual_time:.3f}분) - 시간 개선")
                elif abs(actual_time - best_actual_time) < 0.1:  # 시간이 0.1분 이하 차이
                    # 비슷한 시간일 때는 순환성 우선 고려
                    current_global_distance = getattr(self, '_best_global_distance', float('inf'))
                    if global_distance_m < current_global_distance:
                        is_better = True
                        self.logger.info(f"🏆 새로운 최고 기록: {num_clusters}개 클러스터 ({actual_time:.3f}분) - 순환성 개선 ({global_distance_m:.0f}m)")

                if is_better:
                    best_actual_time = actual_time
                    best_performance = clusters
                    self._best_global_distance = actual_distance * 1000  # km를 미터로 변환해서 저장

            except Exception as e:
                self.logger.warning(f"❌ {num_clusters}개 클러스터 테스트 실패: {e}")
                continue

        if not best_performance:
            self.logger.error("모든 실제 API 테스트 실패, 기존 방식으로 대체")
            return self._optimize_multi_cluster_fallback(waypoints)

        self.logger.info(f"🎉 최종 선택: 실제 측정 기준 최고 성능 ({best_actual_time:.3f}분)")
        # 최고 성능의 거리/시간 정보도 함께 반환
        best_distance_km = self._best_global_distance / 1000 if hasattr(self, '_best_global_distance') else 0
        return {
            'clusters': best_performance,
            'total_duration_minutes': best_actual_time,
            'total_distance_km': best_distance_km,
            'cluster_count': len(best_performance) if best_performance else 0
        }

    def _test_real_api_performance(self, waypoints: List[Dict[str, Any]], num_clusters: int) -> Tuple[float, float, List[List[Dict[str, Any]]]]:
        """실제 카카오 API 호출을 통한 성능 측정"""
        if not self.api_key:
            raise ValueError("실제 API 테스트를 위해서는 API 키가 필요합니다")

        # 1. 클러스터링 생성 (클러스터 개수에 비례한 대표점 선택)
        # 모든 지점을 대표점으로 사용 (가장 정확한 접근)
        representative_points = waypoints
        road_distance_matrix = self._estimate_road_distances(representative_points)
        clusters = self._road_aware_clustering(waypoints, representative_points, road_distance_matrix, num_clusters)

        # 2. 클러스터 순서 및 연결점 최적화
        optimized_clusters = self._optimize_cluster_sequence(clusters)
        connected_clusters = self._optimize_cluster_connections(optimized_clusters)
        final_clusters = self._optimize_global_start_end(connected_clusters)

        # 3. 실제 API 호출로 각 클러스터의 실제 시간 측정
        import requests
        import json

        total_actual_time = 0.0
        total_actual_distance = 0.0
        result_clusters = []

        for i, cluster in enumerate(final_clusters):
            # 실제 API 호출 보장 (재시도 포함)
            cluster_waypoints = cluster.waypoints
            self.logger.debug(f"클러스터 {i} 처리 시작: {len(cluster_waypoints)}개 지점")

            if len(cluster_waypoints) < 1:
                self.logger.warning(f"클러스터 {i}: 지점이 0개, 배치 생성 생략")
                continue
            elif len(cluster_waypoints) == 1:
                self.logger.warning(f"클러스터 {i}: 지점이 1개, 단일 지점 배치로 처리")
                # 단일 지점도 적절한 시간과 거리 설정 (기본 배송 시간)
                single_point_duration = 0.5  # 30초 (기본 배송/처리 시간)
                single_point_distance = 0.05  # 50미터 (최소 이동 거리)

                total_actual_time += single_point_duration
                total_actual_distance += single_point_distance
                result_clusters.append(cluster_waypoints)

                self.logger.debug(f"클러스터 {i}: 단일 지점 처리 완료 ({single_point_duration}분, {single_point_distance}km)")
                continue

            # API 재시도 로직으로 실제 시간 측정
            duration, distance = self._call_kakao_api_with_retry(cluster, i)

            total_actual_time += duration
            total_actual_distance += distance
            result_clusters.append(cluster.waypoints)

            self.logger.debug(f"클러스터 {i} API 호출 완료: {duration:.3f}분, {distance:.1f}km")

            # 클러스터 간 연결 시간 추가 계산
            if i < len(final_clusters) - 1:
                next_cluster = final_clusters[i + 1]
                connection_time, connection_distance = self._calculate_cluster_connection_time(cluster, next_cluster)
                total_actual_time += connection_time
                total_actual_distance += connection_distance

                # 연결 지점 검증 로그
                self.logger.info(f"📍 클러스터 {i} → {i+1} 연결: {connection_time:.3f}분, {connection_distance:.1f}km")
                self.logger.debug(f"   연결점: ({cluster.end_point['x']:.4f},{cluster.end_point['y']:.4f}) → "
                                f"({next_cluster.start_point['x']:.4f},{next_cluster.start_point['y']:.4f})")

        # 전체 경로 연속성 검증
        self._validate_route_continuity(final_clusters, total_actual_time, total_actual_distance)

        # 전체 지점 수 보존 검증
        total_result_waypoints = sum(len(cluster) for cluster in result_clusters)
        if total_result_waypoints != len(waypoints):
            self.logger.error(f"❌ 경유지 개수 불일치: 입력 {len(waypoints)}개 → 출력 {total_result_waypoints}개")
            self.logger.error(f"   클러스터 개수: {len(final_clusters)}개 → 결과 배치: {len(result_clusters)}개")
            for i, cluster in enumerate(result_clusters):
                self.logger.error(f"   클러스터 {i}: {len(cluster)}개 지점")

            # 누락된 클러스터 찾기
            processed_cluster_ids = set(range(len(result_clusters)))
            total_cluster_ids = set(range(len(final_clusters)))
            missing_clusters = total_cluster_ids - processed_cluster_ids
            if missing_clusters:
                self.logger.error(f"   누락된 클러스터: {missing_clusters}")
        else:
            self.logger.info(f"✅ 경유지 개수 보존: {len(waypoints)}개 → {total_result_waypoints}개")

        return total_actual_time, total_actual_distance, result_clusters

    def _validate_route_continuity(self, clusters: List[GlobalRouteCluster], total_time: float, total_distance: float):
        """전체 경로의 연속성과 완전성 검증"""
        if not clusters:
            self.logger.warning("⚠️ 클러스터가 없음 - 경로 검증 불가")
            return

        # 1. 클러스터 개수 및 총 지점 수 검증
        total_waypoints = sum(len(cluster.waypoints) for cluster in clusters)
        cluster_count = len(clusters)

        self.logger.info(f"🔍 경로 연속성 검증: {cluster_count}개 클러스터, 총 {total_waypoints}개 지점")

        # 2. 클러스터 간 연결점 검증
        for i in range(len(clusters) - 1):
            current_cluster = clusters[i]
            next_cluster = clusters[i + 1]

            # 연결 거리 확인 (100km 이상이면 경고, 500km 이상이면 심각한 문제)
            connection_distance_m = self.coordinate_validator.calculate_distance(
                (current_cluster.end_point['x'], current_cluster.end_point['y']),
                (next_cluster.start_point['x'], next_cluster.start_point['y'])
            )
            connection_distance_km = connection_distance_m / 1000  # 미터 → km

            if connection_distance_km > 500:  # 500km 이상 - 심각한 문제
                self.logger.error(f"❌ 클러스터 {i}→{i+1} 연결 거리 비정상: {connection_distance_km:.1f}km")
            elif connection_distance_km > 100:  # 100km 이상 - 경고
                self.logger.warning(f"⚠️ 클러스터 {i}→{i+1} 연결 거리 멀음: {connection_distance_km:.1f}km")
            else:
                self.logger.debug(f"클러스터 {i}→{i+1} 연결: {connection_distance_km:.1f}km")

        # 3. 전역 시작-끝점 거리 검증
        if len(clusters) > 1:
            global_start = clusters[0].start_point
            global_end = clusters[-1].end_point
            global_distance_m = self.coordinate_validator.calculate_distance(
                (global_start['x'], global_start['y']),
                (global_end['x'], global_end['y'])
            )

            self.logger.info(f"🌐 전역 시작-끝점 거리: {global_distance_m:.0f}m")

            if global_distance_m < 500:  # 500m 미만이면 좋은 순환 경로
                self.logger.info("✅ 우수한 순환 경로 (시작-끝점 근접)")
            elif global_distance_m > 10000:  # 10km 이상이면 경고
                self.logger.warning("⚠️ 순환성 부족 (시작-끝점 원거리)")

        # 4. 총 시간/거리 요약
        avg_speed = (total_distance / (total_time / 60)) if total_time > 0 else 0
        self.logger.info(f"📊 경로 요약: 총 {total_time:.3f}분, {total_distance:.1f}km (평균 {avg_speed:.1f}km/h)")

    def _call_kakao_api_with_retry(self, cluster: GlobalRouteCluster, cluster_id: int, max_retries: int = 3) -> Tuple[float, float]:
        """카카오 API 재시도 보장 호출 - 백업 추정 없이 실제 API만 사용"""
        import requests
        import time

        # 클러스터 내부 TSP 최적화 적용
        cluster_waypoints = self._optimize_cluster_internal_order(cluster)
        cluster.waypoints = cluster_waypoints  # 최적화된 순서로 업데이트

        # API 요청 데이터 구성
        api_data = {
            "origin": {
                "x": cluster.start_point['x'],
                "y": cluster.start_point['y']
            },
            "destination": {
                "x": cluster.end_point['x'],
                "y": cluster.end_point['y']
            },
            "waypoints": [
                {"x": wp['x'], "y": wp['y']}
                for wp in cluster_waypoints[1:-1]  # 중간 경유지만
            ] if len(cluster_waypoints) > 2 else [],
            "priority": "TIME",
            "car_fuel": "GASOLINE",
            "car_hipass": False,
            "alternatives": False,
            "road_details": False
        }

        headers = {
            "Authorization": f"KakaoAK {self.api_key}",
            "Content-Type": "application/json"
        }

        last_error = None

        # 최대 3번 재시도
        for attempt in range(max_retries):
            try:
                self.logger.debug(f"클러스터 {cluster_id}: API 호출 시도 {attempt + 1}/{max_retries}")

                response = requests.post(
                    "https://apis-navi.kakaomobility.com/v1/waypoints/directions",
                    headers=headers,
                    json=api_data,
                    timeout=30
                )

                if response.status_code == 200:
                    result = response.json()

                    if 'routes' in result and len(result['routes']) > 0:
                        route = result['routes'][0]

                        # API 응답 구조 디버깅
                        self.logger.debug(f"클러스터 {cluster_id} API 응답 구조: {list(route.keys())}")

                        # result_code 확인 (104 = 출발지와 도착지가 5m 이내)
                        route_result_code = route.get('result_code', 0)
                        if route_result_code == 104:
                            # 5m 이내 거리로 인한 경로 탐색 불가 - 단일 지점으로 처리
                            self.logger.warning(f"클러스터 {cluster_id}: 지점들이 너무 가까움 (5m 이내), 단일 지점으로 처리")
                            # 매우 짧은 거리와 시간으로 처리
                            duration_sec = 30  # 30초 (최소 이동 시간)
                            distance_m = 10  # 10미터 (최소 이동 거리)
                            duration = duration_sec / 60.0
                            distance = distance_m / 1000.0

                            self.logger.info(f"✅ 클러스터 {cluster_id}: {len(cluster_waypoints)}개 지점, "
                                           f"{duration:.3f}분, {distance:.3f}km (근접지점 처리)")
                            return duration, distance

                        elif route_result_code != 0:
                            # 기타 오류 코드 처리
                            route_result_msg = route.get('result_msg', '알 수 없는 오류')
                            last_error = f"API 결과 코드 {route_result_code}: {route_result_msg}"
                            self.logger.warning(f"클러스터 {cluster_id}: {last_error}")
                            continue

                        # summary 키 존재 여부 확인 및 대안 접근
                        if 'summary' in route:
                            duration_sec = route['summary']['duration']  # API는 초 단위로 반환
                            distance_m = route['summary']['distance']
                        elif 'sections' in route and len(route['sections']) > 0:
                            # sections를 통한 대안 접근
                            total_duration = 0
                            total_distance = 0
                            for section in route['sections']:
                                if 'summary' in section:
                                    total_duration += section['summary']['duration']
                                    total_distance += section['summary']['distance']
                            duration_sec = total_duration  # API는 초 단위로 반환
                            distance_m = total_distance
                            self.logger.debug(f"클러스터 {cluster_id}: sections 기반 계산 ({len(route['sections'])}개 구간)")
                        else:
                            # 응답 구조를 더 자세히 로깅
                            self.logger.error(f"클러스터 {cluster_id}: 예상치 못한 API 응답 구조")
                            self.logger.error(f"응답 내용: {result}")
                            last_error = f"API 응답에 summary/sections 정보 없음"
                            continue

                        duration = duration_sec / 60.0  # 초 → 분 (올바른 변환)
                        distance = distance_m / 1000.0   # 미터 → km

                        # 디버깅: 원본 값 및 변환 결과 확인
                        self.logger.debug(f"클러스터 {cluster_id} API 변환: "
                                        f"{duration_sec}초→{duration:.3f}분, {distance_m}m→{distance:.3f}km")

                        # 비정상적 결과 검증 및 속도 검증
                        is_critical_error = False

                        if duration_sec <= 0:  # 0초 또는 음수 - 심각한 오류
                            self.logger.error(f"❌ 클러스터 {cluster_id}: API 응답 duration=0초 "
                                             f"({len(cluster_waypoints)}개 지점)")
                            is_critical_error = True

                        if distance > 1000:  # 1000km 초과 - 심각한 오류
                            self.logger.error(f"❌ 클러스터 {cluster_id}: 비정상적 장거리 {distance:.1f}km "
                                             f"(원본: {distance_m}m)")
                            is_critical_error = True

                        # 속도 검증: 비현실적인 고속 주행 검출
                        if duration > 0 and distance > 0:
                            calculated_speed = (distance / duration) * 60  # km/h
                            if calculated_speed > 150:  # 150km/h 초과 시 경고 (사용자 요청)
                                self.logger.warning(f"⚡ 클러스터 {cluster_id}: 비현실적 속도 {calculated_speed:.1f}km/h "
                                                  f"({distance:.1f}km ÷ {duration:.3f}분)")
                                self.logger.warning(f"   원본 API 응답: {duration_sec}초 → {duration:.3f}분 변환")
                                # 매우 높은 속도(800km/h 이상)는 재시도
                                if calculated_speed > 800 and attempt == 0:
                                    self.logger.info(f"클러스터 {cluster_id}: 극도로 높은 속도로 인한 재시도")
                                    is_critical_error = True

                            # 비현실적으로 짧은 시간 검출 (추가 검증)
                            min_expected_time_sec = len(cluster_waypoints) * 10  # 지점당 최소 10초
                            if duration_sec < min_expected_time_sec:
                                self.logger.warning(f"🕐 클러스터 {cluster_id}: API 시간이 비현실적으로 짧음 "
                                                  f"{duration_sec}초 < {min_expected_time_sec}초 예상시간")
                                self.logger.warning(f"   {len(cluster_waypoints)}개 지점을 {duration_sec:.1f}초에 방문은 불가능")

                        # 심각한 오류만 재시도 (첫 번째 시도에서만)
                        if is_critical_error and attempt == 0:
                            self.logger.info(f"클러스터 {cluster_id}: 심각한 오류로 인한 재시도")
                            time.sleep(2)  # 2초 대기
                            continue

                        # 정상/경고 수준은 그대로 사용
                        if duration < 1.0 and len(cluster_waypoints) > 5:  # 경고만 표시
                            self.logger.warning(f"⚠️ 클러스터 {cluster_id}: 짧은 시간 {duration:.3f}분 "
                                             f"({len(cluster_waypoints)}개 지점, {distance:.1f}km)")
                        elif duration > 120:  # 2시간 초과 경고
                            self.logger.warning(f"⚠️ 클러스터 {cluster_id}: 긴 시간 {duration:.3f}분 "
                                             f"({len(cluster_waypoints)}개 지점, {distance:.1f}km)")

                        self.logger.info(f"✅ 클러스터 {cluster_id}: {len(cluster_waypoints)}개 지점, "
                                       f"{duration:.3f}분, {distance:.1f}km (시도 {attempt + 1})")

                        return duration, distance
                    else:
                        last_error = f"API 응답에 경로 정보 없음: {result}"
                        self.logger.warning(f"클러스터 {cluster_id}: {last_error}")

                elif response.status_code == 429:  # Rate limit
                    last_error = f"Rate limit (429): {response.text}"
                    self.logger.warning(f"클러스터 {cluster_id}: 요청 제한, 5초 대기...")
                    time.sleep(5)
                    continue

                else:
                    last_error = f"API 호출 실패 ({response.status_code}): {response.text}"
                    self.logger.warning(f"클러스터 {cluster_id}: {last_error}")

            except requests.exceptions.Timeout:
                last_error = "API 호출 타임아웃"
                self.logger.warning(f"클러스터 {cluster_id}: 타임아웃, 재시도...")

            except Exception as e:
                last_error = f"예외 발생: {str(e)}"
                self.logger.warning(f"클러스터 {cluster_id}: {last_error}")

            # 재시도 전 대기
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # 지수 백오프: 1초, 2초, 4초

        # 모든 재시도 실패
        self.logger.error(f"❌ 클러스터 {cluster_id}: {max_retries}번 모든 시도 실패 - {last_error}")
        raise Exception(f"클러스터 {cluster_id} API 호출 완전 실패: {last_error}")

    def _calculate_cluster_connection_time(self, from_cluster: GlobalRouteCluster, to_cluster: GlobalRouteCluster) -> Tuple[float, float]:
        """클러스터 간 연결 시간을 실제 API로 계산"""
        import requests
        import time

        # 출발지: from_cluster의 end_point
        # 목적지: to_cluster의 start_point
        api_data = {
            "origin": {
                "x": from_cluster.end_point['x'],
                "y": from_cluster.end_point['y']
            },
            "destination": {
                "x": to_cluster.start_point['x'],
                "y": to_cluster.start_point['y']
            },
            "priority": "TIME",
            "car_fuel": "GASOLINE",
            "car_hipass": False,
            "alternatives": False,
            "road_details": False
        }

        headers = {
            "Authorization": f"KakaoAK {self.api_key}",
            "Content-Type": "application/json"
        }

        # API 재시도 로직 (최대 3번)
        for attempt in range(3):
            try:
                response = requests.post(
                    "https://apis-navi.kakaomobility.com/v1/waypoints/directions",
                    headers=headers,
                    json=api_data,
                    timeout=30
                )

                if response.status_code == 200:
                    data = response.json()
                    route = data['routes'][0]

                    # result_code 확인 (104 = 출발지와 도착지가 5m 이내)
                    route_result_code = route.get('result_code', 0)
                    if route_result_code == 104:
                        # 클러스터 연결이 너무 가까움 - 최소 값으로 처리
                        self.logger.debug(f"클러스터 연결: 지점들이 너무 가까움 (5m 이내), 최소값으로 처리")
                        return 0.5 / 60.0, 0.01  # 30초, 10미터
                    elif route_result_code != 0:
                        route_result_msg = route.get('result_msg', '알 수 없는 오류')
                        self.logger.warning(f"클러스터 연결 API 오류 코드 {route_result_code}: {route_result_msg}")
                        continue

                    # API 응답 구조 확인 및 대안 접근
                    if 'summary' in route:
                        duration_sec = route['summary']['duration']  # API는 초 단위로 반환
                        distance_m = route['summary']['distance']
                    elif 'sections' in route and len(route['sections']) > 0:
                        # sections를 통한 대안 접근
                        total_duration = 0
                        total_distance = 0
                        for section in route['sections']:
                            if 'summary' in section:
                                total_duration += section['summary']['duration']
                                total_distance += section['summary']['distance']
                        duration_sec = total_duration  # API는 초 단위로 반환
                        distance_m = total_distance
                        self.logger.debug(f"클러스터 연결: sections 기반 계산 ({len(route['sections'])}개 구간)")
                    else:
                        # 응답 구조 로깅
                        self.logger.error(f"클러스터 연결: 예상치 못한 API 응답 구조")
                        self.logger.error(f"응답 내용: {data}")
                        continue

                    duration = duration_sec / 60.0  # 초 → 분 (올바른 변환)
                    distance = distance_m / 1000.0   # 미터 → km

                    self.logger.debug(f"클러스터 연결 API 변환: "
                                    f"{duration_sec}초→{duration:.3f}분, {distance_m}m→{distance:.3f}km")
                    return duration, distance

                elif response.status_code == 429:  # Rate limit
                    wait_time = 2 ** attempt  # 지수적 백오프
                    self.logger.warning(f"클러스터 연결 API 속도 제한, {wait_time}초 대기...")
                    time.sleep(wait_time)
                    continue
                else:
                    self.logger.warning(f"클러스터 연결 API 오류 (시도 {attempt+1}/3): {response.status_code}")

            except requests.exceptions.RequestException as e:
                self.logger.warning(f"클러스터 연결 API 요청 실패 (시도 {attempt+1}/3): {e}")
                if attempt < 2:  # 마지막 시도가 아니면 잠시 대기
                    time.sleep(1)

        # API 실패 시 직선거리 기반 추정 (최후 수단)
        straight_distance_m = self.coordinate_validator.calculate_distance(
            (from_cluster.end_point['x'], from_cluster.end_point['y']),
            (to_cluster.start_point['x'], to_cluster.start_point['y'])
        )
        estimated_road_distance_m = straight_distance_m * 1.3  # 도로 계수 적용 (미터)
        estimated_road_distance_km = estimated_road_distance_m / 1000  # 미터 → km 변환
        estimated_time = estimated_road_distance_km / 0.5  # 평균 속도 30km/h = 0.5km/분

        self.logger.warning(f"클러스터 연결 API 완전 실패, 추정값 사용: {estimated_time:.3f}분, {estimated_road_distance_km:.1f}km")
        return estimated_time, estimated_road_distance_km

    def _optimize_cluster_internal_order(self, cluster: GlobalRouteCluster) -> List[Dict[str, Any]]:
        """클러스터 내부 경유지 순서를 TSP로 최적화"""
        waypoints = cluster.waypoints.copy()

        if len(waypoints) <= 2:
            return waypoints

        # 시작점과 끝점은 고정, 중간점들만 최적화
        if len(waypoints) == 3:
            return waypoints  # 시작-중간-끝 순서가 유일

        start_point = cluster.start_point
        end_point = cluster.end_point

        # 중간 경유지들 추출 (시작점, 끝점 제외) - ID 기준으로 비교
        start_id = start_point.get('id') if isinstance(start_point, dict) else None
        end_id = end_point.get('id') if isinstance(end_point, dict) else None

        middle_waypoints = []
        for wp in waypoints:
            wp_id = wp.get('id') if isinstance(wp, dict) else None
            if wp_id != start_id and wp_id != end_id:
                middle_waypoints.append(wp)

        self.logger.debug(f"TSP 지점 분석: 전체 {len(waypoints)}개, 시작점 ID={start_id}, "
                         f"끝점 ID={end_id}, 중간점 {len(middle_waypoints)}개")

        if not middle_waypoints:
            return [start_point, end_point]

        # TSP 최적화: 시작점에서 출발하여 모든 중간점을 거쳐 끝점으로 가는 최단 경로
        optimized_middle = self._traveling_salesman_with_fixed_endpoints(
            start_point, middle_waypoints, end_point
        )

        # 시작점과 끝점이 같은 경우 중복 제거
        if start_id == end_id:
            # 순환 경로: 시작점 + 최적화된 중간점들 (끝점 제외)
            result = [start_point] + optimized_middle
            self.logger.debug(f"순환 클러스터 감지: 시작점=끝점 (ID={start_id}), 중복 제거")
        else:
            # 일반 경로: 시작점 + 최적화된 중간점들 + 끝점
            result = [start_point] + optimized_middle + [end_point]

        # 지점 개수 검증
        if len(result) != len(waypoints):
            self.logger.error(f"❌ TSP 최적화 오류: 입력 {len(waypoints)}개 → 출력 {len(result)}개")
            self.logger.error(f"   시작점: {start_id}, 끝점: {end_id}, 중간점: {len(middle_waypoints)}개")
            self.logger.error(f"   동일 ID 여부: {start_id == end_id}")
            # 원본 그대로 반환 (안전장치)
            return waypoints

        self.logger.debug(f"클러스터 {cluster.id}: TSP 최적화 적용 ({len(waypoints)}→{len(result)}개 지점)")
        return result

    def _traveling_salesman_with_fixed_endpoints(self, start_point: Dict[str, Any],
                                               middle_waypoints: List[Dict[str, Any]],
                                               end_point: Dict[str, Any]) -> List[Dict[str, Any]]:
        """시작점과 끝점이 고정된 TSP 최적화 (Nearest Neighbor 휴리스틱)"""
        if not middle_waypoints:
            return []

        if len(middle_waypoints) == 1:
            return middle_waypoints

        # Nearest Neighbor 알고리즘
        unvisited = middle_waypoints.copy()
        route = []
        current_point = start_point

        while unvisited:
            # 현재 지점에서 가장 가까운 미방문 지점 찾기
            nearest_point = min(unvisited, key=lambda wp: self.coordinate_validator.calculate_distance(
                (current_point['x'], current_point['y']),
                (wp['x'], wp['y'])
            ))

            route.append(nearest_point)
            unvisited.remove(nearest_point)
            current_point = nearest_point

        return route

    def _evaluate_clustering_scenario(self, waypoints: List[Dict[str, Any]], num_clusters: int) -> ClusteringPerformance:
        """특정 클러스터 개수에 대한 성능 평가"""
        # 1. 대표점 선택 (클러스터 개수에 비례)
        # 모든 지점을 대표점으로 사용 (가장 정확한 접근)
        representative_points = waypoints

        # 2. 도로 거리 추정
        road_distance_matrix = self._estimate_road_distances(representative_points)

        # 3. 클러스터링 생성
        clusters = self._road_aware_clustering(waypoints, representative_points, road_distance_matrix, num_clusters)

        # 4. 클러스터 순서 최적화
        optimized_clusters = self._optimize_cluster_sequence(clusters)

        # 5. 클러스터 연결점 최적화
        connected_clusters = self._optimize_cluster_connections(optimized_clusters)

        # 6. 전역 시작-끝점 최적화
        final_clusters = self._optimize_global_start_end(connected_clusters)

        # 7. 성능 측정
        total_time, total_distance, balance_score, connectivity_score = self._calculate_performance_metrics(final_clusters)

        return ClusteringPerformance(
            num_clusters=num_clusters,
            clusters=final_clusters,
            estimated_total_time=total_time,
            estimated_total_distance=total_distance,
            balance_score=balance_score,
            connectivity_score=connectivity_score
        )

    def _calculate_performance_metrics(self, clusters: List[GlobalRouteCluster]) -> Tuple[float, float, float, float]:
        """실제 API 데이터 기반 정확한 성능 지표 계산"""
        total_time = 0.0
        total_distance = 0.0
        cluster_sizes = []
        connection_distances = []

        # 각 클러스터의 실제 성능 기반 시간 추정
        for cluster in clusters:
            cluster_waypoints = len(cluster.waypoints)
            cluster_sizes.append(cluster_waypoints)

            # 실제 API 결과 기반 시간 추정 공식 (39개 경유지 데이터 분석 결과)
            if cluster_waypoints <= 2:
                internal_time = cluster_waypoints * 8  # 소규모: 8분/지점
                internal_distance = cluster_waypoints * 1.5  # 1.5km/지점
            elif cluster_waypoints <= 6:
                # 소규모 클러스터: 효율성 떨어짐 (5.0분/개)
                internal_time = cluster_waypoints * 5.0
                internal_distance = cluster_waypoints * 1.2
            elif cluster_waypoints <= 15:
                # 최적 효율 구간: 10~15개 (2.9분/개)
                internal_time = cluster_waypoints * 2.9
                internal_distance = cluster_waypoints * 0.8
            elif cluster_waypoints <= 25:
                # 중대형: 약간 비효율 (3.5분/개)
                internal_time = cluster_waypoints * 3.5
                internal_distance = cluster_waypoints * 1.0
            else:
                # 대형: 매우 비효율 (5.5분/개)
                internal_time = cluster_waypoints * 5.5
                internal_distance = cluster_waypoints * 1.4

            total_distance += internal_distance
            total_time += internal_time

        # 클러스터 간 연결 거리 추정
        for i in range(len(clusters) - 1):
            current_cluster = clusters[i]
            next_cluster = clusters[i + 1]

            connection_distance = self.coordinate_validator.calculate_distance(
                (current_cluster.end_point['x'], current_cluster.end_point['y']),
                (next_cluster.start_point['x'], next_cluster.start_point['y'])
            ) / 1000  # km

            connection_distances.append(connection_distance)
            total_distance += connection_distance
            total_time += connection_distance * 2.5  # 연결 이동 시간: 2.5분/km

        # 균형 점수 계산 (클러스터 크기 표준편차 기반)
        if len(cluster_sizes) > 1:
            avg_size = sum(cluster_sizes) / len(cluster_sizes)
            variance = sum((size - avg_size) ** 2 for size in cluster_sizes) / len(cluster_sizes)
            balance_score = max(0, 1 - (variance / (avg_size ** 2)))
        else:
            balance_score = 1.0

        # 연결성 점수 계산 (클러스터 간 평균 거리 기반)
        if connection_distances:
            avg_connection = sum(connection_distances) / len(connection_distances)
            # 5km 이하면 좋은 연결성, 20km 이상은 나쁜 연결성
            connectivity_score = max(0, min(1, (20 - avg_connection) / 15))
        else:
            connectivity_score = 1.0

        return total_time, total_distance, balance_score, connectivity_score

    def _optimize_multi_cluster_fallback(self, waypoints: List[Dict[str, Any]]) -> Dict[str, Any]:
        """백업용 기존 다중 클러스터 방식 - 구조적 결과 반환"""
        self.logger.info("백업 모드: 기존 클러스터링 방식 사용")

        # 기존 로직 사용 (단순 수학적 분할)
        num_clusters = math.ceil(len(waypoints) / self.MAX_WAYPOINTS_PER_BATCH)
        # 모든 지점을 대표점으로 사용 (가장 정확한 접근)
        representative_points = waypoints
        road_distance_matrix = self._estimate_road_distances(representative_points)
        clusters = self._road_aware_clustering(waypoints, representative_points, road_distance_matrix, num_clusters)

        # 기본 최적화만 적용
        optimized_clusters = self._optimize_cluster_sequence(clusters)
        connected_clusters = self._optimize_cluster_connections(optimized_clusters)
        final_clusters = self._optimize_global_start_end(connected_clusters)

        # 백업 모드에서는 추정값 사용 (API 호출 없음)
        estimated_total_distance = 0.0
        estimated_total_time = 0.0

        for cluster in final_clusters:
            # 클러스터 내부 거리 추정
            for i in range(len(cluster.waypoints) - 1):
                current = cluster.waypoints[i]
                next_point = cluster.waypoints[i + 1]
                distance = self.coordinate_validator.calculate_distance(
                    (current['x'], current['y']),
                    (next_point['x'], next_point['y'])
                )
                estimated_total_distance += distance
                # 도시 주행 평균 속도 20km/h로 추정
                estimated_total_time += (distance / 1000) / 20 * 60  # 분 단위

        # 클러스터 간 연결 거리 추가
        for i in range(len(final_clusters) - 1):
            current_cluster = final_clusters[i]
            next_cluster = final_clusters[i + 1]
            connection_distance = self.coordinate_validator.calculate_distance(
                (current_cluster.end_point['x'], current_cluster.end_point['y']),
                (next_cluster.start_point['x'], next_cluster.start_point['y'])
            )
            estimated_total_distance += connection_distance
            estimated_total_time += (connection_distance / 1000) / 20 * 60

        self.logger.warning(f"⚠️ 백업 모드 결과 (추정값): {estimated_total_time:.1f}분, {estimated_total_distance/1000:.1f}km")

        return {
            'clusters': [cluster.waypoints for cluster in final_clusters],
            'total_duration_minutes': estimated_total_time,
            'total_distance_km': estimated_total_distance / 1000,
            'cluster_count': len(final_clusters)
        }

    def _optimize_single_cluster_global(self, waypoints: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """단일 클러스터에서 시작-끝점이 가장 가까운 TSP 순서 생성"""
        if len(waypoints) <= 2:
            return waypoints

        best_route = waypoints
        min_start_end_distance = float('inf')

        # 여러 TSP 근사를 시도하여 시작-끝점 거리가 최소인 것 선택
        for attempt in range(min(10, len(waypoints))):
            route = self._traveling_salesman_approximation(waypoints, start_idx=attempt)
            start_end_distance = self.coordinate_validator.calculate_distance(
                (route[0]['x'], route[0]['y']),
                (route[-1]['x'], route[-1]['y'])
            )

            if start_end_distance < min_start_end_distance:
                min_start_end_distance = start_end_distance
                best_route = route

        self.logger.info(f"최적 전역 시작-끝점 거리: {min_start_end_distance:.0f}m")
        return best_route

    def _optimize_multi_cluster_global(self, waypoints: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """다중 클러스터에서 전역 연결성 최적화"""

        # 1. 대표점 샘플링 기반 도로 거리 추정
        # 모든 지점을 대표점으로 사용 (가장 정확한 접근)
        representative_points = waypoints
        road_distance_matrix = self._estimate_road_distances(representative_points)

        # 2. 도로 거리 기반 초기 클러스터링
        num_clusters = math.ceil(len(waypoints) / self.MAX_WAYPOINTS_PER_BATCH)
        initial_clusters = self._road_aware_clustering(waypoints, representative_points,
                                                     road_distance_matrix, num_clusters)

        # 3. 전역 TSP로 클러스터 순서 최적화
        cluster_sequence = self._optimize_cluster_sequence(initial_clusters)

        # 4. 클러스터 간 연결점 최적화
        connected_clusters = self._optimize_cluster_connections(cluster_sequence)

        # 5. 전역 시작-끝점 최적화
        final_clusters = self._optimize_global_start_end(connected_clusters)

        return [cluster.waypoints for cluster in final_clusters]

    def _select_representative_points(self, waypoints: List[Dict[str, Any]],
                                    sample_size: int) -> List[Dict[str, Any]]:
        """지리적으로 분산된 대표점들 선택"""
        if len(waypoints) <= sample_size:
            return waypoints

        # K-means++와 유사한 방식으로 분산된 점들 선택
        representatives = []
        remaining = waypoints.copy()

        # 첫 번째는 고정적으로 선택 (일관성 보장)
        first = remaining[0]
        representatives.append(first)
        remaining.remove(first)

        # 나머지는 기존 대표점들로부터 가장 먼 점들 선택
        for _ in range(sample_size - 1):
            if not remaining:
                break

            max_min_distance = 0
            farthest_point = None

            for candidate in remaining:
                min_distance = float('inf')
                for rep in representatives:
                    distance = self.coordinate_validator.calculate_distance(
                        (candidate['x'], candidate['y']),
                        (rep['x'], rep['y'])
                    )
                    min_distance = min(min_distance, distance)

                if min_distance > max_min_distance:
                    max_min_distance = min_distance
                    farthest_point = candidate

            if farthest_point:
                representatives.append(farthest_point)
                remaining.remove(farthest_point)

        self.logger.info(f"대표점 {len(representatives)}개 선택 (전체 {len(waypoints)}개 중)")
        return representatives

    def _estimate_road_distances(self, representative_points: List[Dict[str, Any]]) -> Dict[Tuple[int, int], float]:
        """대표점들 간의 도로 거리 추정 (직선거리 × 도로 계수)"""
        distance_matrix = {}
        road_factor = 1.3  # 도로는 직선거리보다 약 30% 더 길다고 가정

        for i, point1 in enumerate(representative_points):
            for j, point2 in enumerate(representative_points):
                if i != j:
                    straight_distance = self.coordinate_validator.calculate_distance(
                        (point1['x'], point1['y']),
                        (point2['x'], point2['y'])
                    )
                    estimated_road_distance = straight_distance * road_factor
                    distance_matrix[(i, j)] = estimated_road_distance
                else:
                    distance_matrix[(i, j)] = 0

        return distance_matrix

    def _road_aware_clustering(self, waypoints: List[Dict[str, Any]],
                              representatives: List[Dict[str, Any]],
                              road_matrix: Dict[Tuple[int, int], float],
                              num_clusters: int) -> List[GlobalRouteCluster]:
        """도로 거리를 고려한 클러스터링"""

        # 대표점들을 num_clusters개로 클러스터링
        rep_clusters = self._cluster_representatives(representatives, road_matrix, num_clusters)

        # 각 waypoint를 가장 가까운 대표점 클러스터에 할당
        clusters = []
        for cluster_id, rep_cluster in enumerate(rep_clusters):
            cluster_waypoints = []

            for waypoint in waypoints:
                closest_rep_cluster = 0
                min_distance = float('inf')

                for rep_cluster_id, reps in enumerate(rep_clusters):
                    # 각 클러스터의 대표점들 중 가장 가까운 점까지의 거리
                    cluster_min_distance = float('inf')
                    for rep in reps:
                        distance = self.coordinate_validator.calculate_distance(
                            (waypoint['x'], waypoint['y']),
                            (rep['x'], rep['y'])
                        )
                        cluster_min_distance = min(cluster_min_distance, distance)

                    if cluster_min_distance < min_distance:
                        min_distance = cluster_min_distance
                        closest_rep_cluster = rep_cluster_id

                if closest_rep_cluster == cluster_id:
                    cluster_waypoints.append(waypoint)

            if cluster_waypoints:
                # 가까운 지점들을 통합하여 API 오류 방지
                # 데이터 손실 방지를 위해 지점 통합 비활성화, 경고만 표시
                merged_waypoints = self._check_nearby_waypoints(cluster_waypoints, min_distance=10.0)

                clusters.append(GlobalRouteCluster(
                    id=cluster_id,
                    waypoints=merged_waypoints,
                    start_point=merged_waypoints[0],  # 임시
                    end_point=merged_waypoints[-1],   # 임시
                    internal_distance=0  # 나중에 계산
                ))

        # 빈 클러스터 제거 및 크기 재조정
        non_empty_clusters = [c for c in clusters if c.waypoints]
        balanced_clusters = self._balance_cluster_sizes(non_empty_clusters)

        return balanced_clusters

    def _cluster_representatives(self, representatives: List[Dict[str, Any]],
                               road_matrix: Dict[Tuple[int, int], float],
                               num_clusters: int) -> List[List[Dict[str, Any]]]:
        """대표점들을 도로 거리 기반으로 클러스터링"""
        if num_clusters >= len(representatives):
            return [[rep] for rep in representatives]

        # 간단한 도로 거리 기반 K-means
        clusters = [[] for _ in range(num_clusters)]

        # 초기 중심점 선택 (가장 멀리 떨어진 점들)
        centroids = []
        remaining = list(range(len(representatives)))

        # 첫 중심점
        centroids.append(0)
        remaining.remove(0)

        # 나머지 중심점들 (기존 중심점들로부터 가장 먼 점들)
        for _ in range(num_clusters - 1):
            if not remaining:
                break

            max_min_distance = 0
            farthest_idx = remaining[0]

            for candidate_idx in remaining:
                min_distance = float('inf')
                for centroid_idx in centroids:
                    distance = road_matrix.get((candidate_idx, centroid_idx), float('inf'))
                    min_distance = min(min_distance, distance)

                if min_distance > max_min_distance:
                    max_min_distance = min_distance
                    farthest_idx = candidate_idx

            centroids.append(farthest_idx)
            remaining.remove(farthest_idx)

        # 각 대표점을 가장 가까운 중심점에 할당
        for rep_idx, rep in enumerate(representatives):
            closest_centroid = 0
            min_distance = float('inf')

            for cluster_idx, centroid_idx in enumerate(centroids):
                distance = road_matrix.get((rep_idx, centroid_idx), float('inf'))
                if distance < min_distance:
                    min_distance = distance
                    closest_centroid = cluster_idx

            clusters[closest_centroid].append(rep)

        return [cluster for cluster in clusters if cluster]

    def _balance_cluster_sizes(self, clusters: List[GlobalRouteCluster]) -> List[GlobalRouteCluster]:
        """클러스터 크기 균형 조정"""
        if not clusters:
            return clusters

        # 너무 큰 클러스터를 분할
        balanced = []
        for cluster in clusters:
            if len(cluster.waypoints) > self.MAX_WAYPOINTS_PER_BATCH:
                # 큰 클러스터를 여러 개로 분할
                sub_clusters = self._split_large_cluster(cluster)
                balanced.extend(sub_clusters)
            else:
                balanced.append(cluster)

        return balanced

    def _split_large_cluster(self, large_cluster: GlobalRouteCluster) -> List[GlobalRouteCluster]:
        """큰 클러스터를 작은 클러스터들로 분할"""
        waypoints = large_cluster.waypoints
        num_sub_clusters = math.ceil(len(waypoints) / self.MAX_WAYPOINTS_PER_BATCH)

        # TSP 순서로 배치한 후 순차적으로 분할 (연결성 보장)
        ordered_waypoints = self._traveling_salesman_approximation(waypoints)

        sub_clusters = []
        waypoints_per_cluster = len(ordered_waypoints) // num_sub_clusters

        for i in range(num_sub_clusters):
            start_idx = i * waypoints_per_cluster
            if i == num_sub_clusters - 1:  # 마지막 클러스터는 나머지 모두
                end_idx = len(ordered_waypoints)
            else:
                end_idx = start_idx + waypoints_per_cluster

            sub_waypoints = ordered_waypoints[start_idx:end_idx]
            if sub_waypoints:
                sub_clusters.append(GlobalRouteCluster(
                    id=large_cluster.id * 100 + i,
                    waypoints=sub_waypoints,
                    start_point=sub_waypoints[0],
                    end_point=sub_waypoints[-1],
                    internal_distance=0
                ))

        return sub_clusters

    def _optimize_cluster_sequence(self, clusters: List[GlobalRouteCluster]) -> List[GlobalRouteCluster]:
        """클러스터들 간의 최적 순서 결정 (클러스터 레벨 TSP)"""
        if len(clusters) <= 2:
            return clusters

        # 클러스터 간 연결 비용 계산 (중심점 간 거리)
        cluster_distances = {}
        for i, cluster1 in enumerate(clusters):
            for j, cluster2 in enumerate(clusters):
                if i != j:
                    center1 = self._get_cluster_center(cluster1)
                    center2 = self._get_cluster_center(cluster2)
                    distance = self.coordinate_validator.calculate_distance(center1, center2)
                    cluster_distances[(i, j)] = distance

        # 클러스터 레벨 TSP 해결
        best_sequence = list(range(len(clusters)))
        best_total_distance = self._calculate_cluster_sequence_distance(best_sequence, cluster_distances)

        # 여러 시작점으로 TSP 시도
        for start_cluster in range(len(clusters)):
            sequence = self._cluster_tsp_approximation(clusters, cluster_distances, start_cluster)
            total_distance = self._calculate_cluster_sequence_distance(sequence, cluster_distances)

            if total_distance < best_total_distance:
                best_total_distance = total_distance
                best_sequence = sequence

        # 최적 순서로 클러스터 재배열
        reordered_clusters = [clusters[i] for i in best_sequence]

        self.logger.info(f"클러스터 순서 최적화: 총 연결 거리 {best_total_distance/1000:.1f}km")
        return reordered_clusters

    def _get_cluster_center(self, cluster: GlobalRouteCluster) -> Tuple[float, float]:
        """클러스터의 중심점 계산"""
        if not cluster.waypoints:
            return (0.0, 0.0)

        avg_x = sum(wp['x'] for wp in cluster.waypoints) / len(cluster.waypoints)
        avg_y = sum(wp['y'] for wp in cluster.waypoints) / len(cluster.waypoints)
        return (avg_x, avg_y)

    def _cluster_tsp_approximation(self, clusters: List[GlobalRouteCluster],
                                  distances: Dict[Tuple[int, int], float],
                                  start_idx: int) -> List[int]:
        """클러스터 간 TSP 근사 해법"""
        unvisited = set(range(len(clusters)))
        unvisited.remove(start_idx)

        sequence = [start_idx]
        current = start_idx

        while unvisited:
            nearest = min(unvisited, key=lambda x: distances.get((current, x), float('inf')))
            sequence.append(nearest)
            unvisited.remove(nearest)
            current = nearest

        return sequence

    def _calculate_cluster_sequence_distance(self, sequence: List[int],
                                           distances: Dict[Tuple[int, int], float]) -> float:
        """클러스터 순서의 총 연결 거리 계산"""
        total_distance = 0
        for i in range(len(sequence) - 1):
            total_distance += distances.get((sequence[i], sequence[i+1]), 0)
        return total_distance

    def _optimize_cluster_connections(self, cluster_sequence: List[GlobalRouteCluster]) -> List[GlobalRouteCluster]:
        """클러스터 간 연결점 최적화 (각 클러스터의 시작-끝점 조정)"""

        for i in range(len(cluster_sequence)):
            cluster = cluster_sequence[i]

            if i == 0:
                # 첫 번째 클러스터: 다음 클러스터와의 연결만 고려
                if len(cluster_sequence) > 1:
                    next_cluster = cluster_sequence[1]
                    cluster.end_point = self._find_closest_point_to_cluster(
                        cluster.waypoints, next_cluster
                    )
                else:
                    # 단일 클러스터인 경우: 첫 번째와 마지막 점 사용 (순환성은 전체 경로에서만 고려)
                    cluster.start_point = cluster.waypoints[0]
                    cluster.end_point = cluster.waypoints[-1]

            elif i == len(cluster_sequence) - 1:
                # 마지막 클러스터: 이전 클러스터와의 연결만 고려
                prev_cluster = cluster_sequence[i-1]
                cluster.start_point = self._find_closest_point_to_cluster(
                    cluster.waypoints, prev_cluster
                )
                # 끝점은 자동 설정됨 (전체 경로 순환성은 _optimize_global_start_end에서 처리)

            else:
                # 중간 클러스터: 이전-다음 클러스터 모두 고려
                prev_cluster = cluster_sequence[i-1]
                next_cluster = cluster_sequence[i+1]

                cluster.start_point = self._find_closest_point_to_cluster(
                    cluster.waypoints, prev_cluster
                )
                cluster.end_point = self._find_closest_point_to_cluster(
                    cluster.waypoints, next_cluster
                )

        return cluster_sequence

    def _find_closest_point_to_cluster(self, points: List[Dict[str, Any]],
                                     target_cluster: GlobalRouteCluster) -> Dict[str, Any]:
        """특정 클러스터에 가장 가까운 점 찾기"""
        target_center = self._get_cluster_center(target_cluster)

        closest_point = points[0]
        min_distance = float('inf')

        for point in points:
            distance = self.coordinate_validator.calculate_distance(
                (point['x'], point['y']), target_center
            )
            if distance < min_distance:
                min_distance = distance
                closest_point = point

        return closest_point

    def _find_closest_pair_in_cluster(self, waypoints: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """클러스터 내에서 가장 가까운 두 점 찾기"""
        if len(waypoints) < 2:
            return waypoints[0], waypoints[0] if waypoints else (None, None)

        min_distance = float('inf')
        best_pair = (waypoints[0], waypoints[1])

        for i, point1 in enumerate(waypoints):
            for j, point2 in enumerate(waypoints[i+1:], i+1):
                distance = self.coordinate_validator.calculate_distance(
                    (point1['x'], point1['y']),
                    (point2['x'], point2['y'])
                )
                if distance < min_distance:
                    min_distance = distance
                    best_pair = (point1, point2)

        return best_pair

    def _optimize_global_start_end(self, clusters: List[GlobalRouteCluster]) -> List[GlobalRouteCluster]:
        """전역 경로의 시작점과 끝점이 가까워지도록 최적화"""
        if len(clusters) <= 1:
            return clusters

        first_cluster = clusters[0]
        last_cluster = clusters[-1]

        # 첫 클러스터의 시작점과 마지막 클러스터의 끝점이 가장 가까운 조합 찾기
        min_global_distance = float('inf')
        best_global_start = first_cluster.start_point
        best_global_end = last_cluster.end_point

        for start_candidate in first_cluster.waypoints:
            for end_candidate in last_cluster.waypoints:
                distance = self.coordinate_validator.calculate_distance(
                    (start_candidate['x'], start_candidate['y']),
                    (end_candidate['x'], end_candidate['y'])
                )
                if distance < min_global_distance:
                    min_global_distance = distance
                    best_global_start = start_candidate
                    best_global_end = end_candidate

        # 최적 전역 시작-끝점 설정
        first_cluster.start_point = best_global_start
        last_cluster.end_point = best_global_end

        self.logger.info(f"전역 시작-끝점 거리: {min_global_distance:.0f}m")
        return clusters

    def _traveling_salesman_approximation(self, waypoints: List[Dict[str, Any]],
                                        start_idx: int = 0) -> List[Dict[str, Any]]:
        """TSP 근사 알고리즘 (Nearest Neighbor)"""
        if len(waypoints) <= 2:
            return waypoints

        unvisited = set(range(len(waypoints)))
        if start_idx < len(waypoints):
            unvisited.remove(start_idx)
        else:
            start_idx = 0
            unvisited.remove(start_idx)

        route = [waypoints[start_idx]]
        current_idx = start_idx

        while unvisited:
            nearest_idx = min(unvisited, key=lambda i: self.coordinate_validator.calculate_distance(
                (waypoints[current_idx]['x'], waypoints[current_idx]['y']),
                (waypoints[i]['x'], waypoints[i]['y'])
            ))

            route.append(waypoints[nearest_idx])
            unvisited.remove(nearest_idx)
            current_idx = nearest_idx

        return route

    def _check_nearby_waypoints(self, waypoints: List[Dict[str, Any]], min_distance: float = 10.0) -> List[Dict[str, Any]]:
        """가까운 지점들을 확인하고 경고만 표시 (데이터 손실 방지)"""
        if len(waypoints) <= 1:
            return waypoints

        nearby_pairs = []

        for i, waypoint in enumerate(waypoints):
            for j in range(i + 1, len(waypoints)):
                other_waypoint = waypoints[j]
                distance = self.coordinate_validator.calculate_distance(
                    (waypoint.get('x', 0), waypoint.get('y', 0)),
                    (other_waypoint.get('x', 0), other_waypoint.get('y', 0))
                )

                if distance <= min_distance:  # 10미터 이내
                    nearby_pairs.append((i, j, distance))

        # 가까운 지점들에 대한 경고만 표시
        if nearby_pairs:
            self.logger.warning(f"⚠️ {len(nearby_pairs)}쌍의 지점이 {min_distance}m 이내에 위치 (데이터 손실 방지를 위해 통합하지 않음)")
            for i, j, distance in nearby_pairs:
                customer1 = waypoints[i].get('customer_name', f"지점{i}")
                customer2 = waypoints[j].get('customer_name', f"지점{j}")
                self.logger.debug(f"   - {customer1} ↔ {customer2}: {distance:.1f}m")

        # 모든 지점을 그대로 반환 (데이터 손실 없음)
        return waypoints