#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
지도 시각화 모듈
최적화된 경로를 지도상에 시각적으로 표시
"""

import os
import folium
from folium import plugins
from typing import List, Dict, Any, Optional
import logging
from dataclasses import dataclass
import pandas as pd

@dataclass
class MapVisualizationConfig:
    """지도 시각화 설정"""
    center_lat: float = 37.5665  # 서울 중심
    center_lon: float = 126.9780
    zoom_start: int = 11
    marker_size: int = 10
    line_width: int = 3
    show_popup_details: bool = True
    enable_clustering: bool = False

class MapVisualizer:
    """최적화 결과 지도 시각화 클래스"""

    def __init__(self, config: Optional[MapVisualizationConfig] = None, logger: Optional[logging.Logger] = None):
        self.config = config or MapVisualizationConfig()
        self.logger = logger or logging.getLogger(__name__)

        # 배치별 색상 팔레트
        self.batch_colors = [
            '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7',
            '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9',
            '#F8C471', '#82E0AA', '#F1948A', '#85C1E9', '#F4D03F'
        ]

    def visualize_optimization_results(self, optimization_results: List[Any],
                                     output_path: str = "route_map.html") -> str:
        """
        최적화 결과를 지도로 시각화

        Args:
            optimization_results: 경로 최적화 결과 리스트
            output_path: 출력 HTML 파일 경로

        Returns:
            생성된 HTML 파일 경로
        """
        try:
            # 유효한 결과만 필터링
            valid_results = [r for r in optimization_results if r.success and r.optimized_waypoints]

            if not valid_results:
                self.logger.error("시각화할 유효한 결과가 없습니다")
                return ""

            # 지도 중심점 계산
            center_lat, center_lon = self._calculate_map_center(valid_results)

            # Folium 지도 생성
            map_viz = folium.Map(
                location=[center_lat, center_lon],
                zoom_start=self.config.zoom_start,
                tiles='OpenStreetMap'
            )

            # 배치별로 경로 그리기
            self._add_batch_routes(map_viz, valid_results)

            # 통계 정보 추가
            self._add_statistics_panel(map_viz, valid_results)

            # 범례 추가
            self._add_legend(map_viz, valid_results)

            # HTML 파일로 저장
            map_viz.save(output_path)
            self.logger.info(f"지도 시각화 완료: {output_path}")

            return output_path

        except Exception as e:
            self.logger.error(f"지도 시각화 실패: {str(e)}")
            return ""

    def _calculate_map_center(self, results: List[Any]) -> tuple[float, float]:
        """모든 경유지의 중심점 계산"""
        all_lats = []
        all_lons = []

        for result in results:
            for waypoint in result.optimized_waypoints:
                all_lats.append(waypoint['latitude'])
                all_lons.append(waypoint['longitude'])

        if all_lats and all_lons:
            center_lat = sum(all_lats) / len(all_lats)
            center_lon = sum(all_lons) / len(all_lons)
            return center_lat, center_lon

        return self.config.center_lat, self.config.center_lon

    def _add_batch_routes(self, map_viz: folium.Map, results: List[Any]) -> None:
        """배치별 경로를 지도에 추가"""

        for batch_idx, result in enumerate(results):
            color = self.batch_colors[batch_idx % len(self.batch_colors)]

            # 경유지 좌표 추출
            route_coords = []
            waypoint_data = []

            for wp in result.optimized_waypoints:
                coord = [wp['latitude'], wp['longitude']]
                route_coords.append(coord)
                waypoint_data.append(wp)

            if len(route_coords) < 2:
                continue

            # 경로 선 그리기
            folium.PolyLine(
                locations=route_coords,
                color=color,
                weight=self.config.line_width,
                opacity=0.8,
                popup=f"배치 {batch_idx + 1} - 총 {len(route_coords)}개 지점"
            ).add_to(map_viz)

            # 마커 추가
            self._add_waypoint_markers(map_viz, waypoint_data, batch_idx, color)

    def _add_waypoint_markers(self, map_viz: folium.Map, waypoints: List[Dict],
                            batch_idx: int, color: str) -> None:
        """경유지 마커 추가"""

        for idx, waypoint in enumerate(waypoints):
            # 마커 아이콘 선택
            if waypoint['waypoint_type'] == 'origin':
                icon = folium.Icon(color='green', icon='play', prefix='fa')
                marker_color = 'green'
            elif waypoint['waypoint_type'] == 'destination':
                icon = folium.Icon(color='red', icon='stop', prefix='fa')
                marker_color = 'red'
            else:
                icon = folium.Icon(color='blue', icon='circle', prefix='fa')
                marker_color = 'blue'

            # 팝업 내용 생성
            popup_html = self._create_popup_content(waypoint, batch_idx, idx)

            # 마커 추가
            folium.Marker(
                location=[waypoint['latitude'], waypoint['longitude']],
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=f"{waypoint['name']} (배치 {batch_idx + 1})",
                icon=icon
            ).add_to(map_viz)

            # 순서 표시 (숫자 마커)
            if waypoint['waypoint_type'] == 'waypoint':
                folium.plugins.BeautifyIcon(
                    icon='circle',
                    iconShape='circle',
                    textColor='white',
                    backgroundColor=color,
                    borderColor='white',
                    borderWidth=2,
                    text=str(idx + 1)
                ).add_to(folium.Marker(
                    location=[waypoint['latitude'], waypoint['longitude']],
                    tooltip=f"순서 {idx + 1}"
                ).add_to(map_viz))

    def _create_popup_content(self, waypoint: Dict, batch_idx: int, sequence: int) -> str:
        """마커 팝업 내용 생성"""

        waypoint_type_kr = {
            'origin': '출발지',
            'destination': '도착지',
            'waypoint': '경유지'
        }

        html = f"""
        <div style="width: 250px; font-family: Arial, sans-serif;">
            <h4 style="margin: 0; color: #333;">
                <i class="fa fa-map-marker"></i> {waypoint_type_kr.get(waypoint['waypoint_type'], '경유지')}
            </h4>
            <hr style="margin: 5px 0;">

            <p style="margin: 2px 0;"><strong>배치:</strong> {batch_idx + 1}</p>
            <p style="margin: 2px 0;"><strong>순서:</strong> {sequence + 1}</p>
            <p style="margin: 2px 0;"><strong>주문 ID:</strong> {waypoint.get('order_id', 'N/A')}</p>

            <p style="margin: 2px 0;"><strong>주소:</strong><br>
            {waypoint.get('address', 'N/A')}</p>

            {f'<p style="margin: 2px 0;"><strong>도로명:</strong><br>{waypoint["road_address"]}</p>' if waypoint.get('road_address') else ''}

            {f'<p style="margin: 2px 0;"><strong>연락처:</strong> {waypoint["user_phone"]}</p>' if waypoint.get('user_phone') else ''}

            {f'<p style="margin: 2px 0;"><strong>메모:</strong><br>{waypoint["msg_to_rider"]}</p>' if waypoint.get('msg_to_rider') else ''}

            <hr style="margin: 5px 0;">
            <p style="margin: 2px 0; font-size: 11px;">
                <strong>이전 구간:</strong><br>
                거리: {waypoint.get('distance_from_prev', 0):.0f}m<br>
                시간: {waypoint.get('duration_from_prev', 0):.0f}초
            </p>

            <p style="margin: 2px 0; font-size: 11px;">
                <strong>누적:</strong><br>
                거리: {waypoint.get('cumulative_distance', 0) / 1000:.2f}km<br>
                시간: {waypoint.get('cumulative_duration', 0) / 60:.1f}분
            </p>
        </div>
        """
        return html

    def _add_statistics_panel(self, map_viz: folium.Map, results: List[Any]) -> None:
        """통계 정보 패널 추가"""

        total_distance = sum(r.total_distance for r in results) / 1000  # km
        total_duration = sum(r.total_duration for r in results) / 3600  # hours
        total_waypoints = sum(r.total_waypoints for r in results)
        total_batches = len(results)
        avg_speed = total_distance / total_duration if total_duration > 0 else 0

        stats_html = f"""
        <div style="position: fixed;
                    top: 10px; right: 10px; width: 250px; height: auto;
                    background-color: white; border: 2px solid grey; z-index: 9999;
                    padding: 10px; border-radius: 5px; box-shadow: 0 0 10px rgba(0,0,0,0.3);">
            <h4 style="margin: 0 0 10px 0; text-align: center; color: #333;">
                <i class="fa fa-bar-chart"></i> 최적화 결과 요약
            </h4>

            <table style="width: 100%; font-size: 12px; border-collapse: collapse;">
                <tr style="background-color: #f0f0f0;">
                    <td style="padding: 3px; border: 1px solid #ddd;"><strong>총 배치 수</strong></td>
                    <td style="padding: 3px; border: 1px solid #ddd; text-align: right;">{total_batches}개</td>
                </tr>
                <tr>
                    <td style="padding: 3px; border: 1px solid #ddd;"><strong>총 경유지</strong></td>
                    <td style="padding: 3px; border: 1px solid #ddd; text-align: right;">{total_waypoints}개</td>
                </tr>
                <tr style="background-color: #f0f0f0;">
                    <td style="padding: 3px; border: 1px solid #ddd;"><strong>총 거리</strong></td>
                    <td style="padding: 3px; border: 1px solid #ddd; text-align: right;">{total_distance:.2f}km</td>
                </tr>
                <tr>
                    <td style="padding: 3px; border: 1px solid #ddd;"><strong>예상 시간</strong></td>
                    <td style="padding: 3px; border: 1px solid #ddd; text-align: right;">{total_duration:.2f}시간</td>
                </tr>
                <tr style="background-color: #f0f0f0;">
                    <td style="padding: 3px; border: 1px solid #ddd;"><strong>평균 속도</strong></td>
                    <td style="padding: 3px; border: 1px solid #ddd; text-align: right;">{avg_speed:.1f}km/h</td>
                </tr>
            </table>

            <p style="margin: 10px 0 0 0; font-size: 11px; text-align: center; color: #666;">
                <i class="fa fa-info-circle"></i> 마커 클릭으로 상세 정보 확인
            </p>
        </div>
        """

        map_viz.get_root().html.add_child(folium.Element(stats_html))

    def _add_legend(self, map_viz: folium.Map, results: List[Any]) -> None:
        """범례 추가"""

        legend_html = """
        <div style="position: fixed;
                    bottom: 10px; right: 10px; width: 200px; height: auto;
                    background-color: white; border: 2px solid grey; z-index: 9999;
                    padding: 10px; border-radius: 5px; box-shadow: 0 0 10px rgba(0,0,0,0.3);">
            <h5 style="margin: 0 0 10px 0; text-align: center; color: #333;">
                <i class="fa fa-info"></i> 범례
            </h5>

            <div style="display: flex; align-items: center; margin: 5px 0;">
                <i class="fa fa-play" style="color: green; margin-right: 8px;"></i>
                <span style="font-size: 12px;">출발지</span>
            </div>

            <div style="display: flex; align-items: center; margin: 5px 0;">
                <i class="fa fa-stop" style="color: red; margin-right: 8px;"></i>
                <span style="font-size: 12px;">도착지</span>
            </div>

            <div style="display: flex; align-items: center; margin: 5px 0;">
                <i class="fa fa-circle" style="color: blue; margin-right: 8px;"></i>
                <span style="font-size: 12px;">경유지</span>
            </div>

            <hr style="margin: 8px 0;">

            <div style="font-size: 11px; color: #666;">
                <div style="margin: 2px 0;"><span style="display: inline-block; width: 15px; height: 3px; background-color: #FF6B6B;"></span> 배치별 경로</div>
                <div style="margin: 2px 0;"><span style="color: white; background-color: #FF6B6B; padding: 1px 4px; border-radius: 50%; font-size: 10px;">1</span> 방문 순서</div>
            </div>
        </div>
        """

        map_viz.get_root().html.add_child(folium.Element(legend_html))

    def create_summary_map(self, optimization_results: List[Any], output_path: str = "summary_map.html") -> str:
        """
        간단한 요약 지도 생성 (배치별 중심점만 표시)

        Args:
            optimization_results: 경로 최적화 결과
            output_path: 출력 파일 경로

        Returns:
            생성된 HTML 파일 경로
        """
        try:
            valid_results = [r for r in optimization_results if r.success and r.optimized_waypoints]

            if not valid_results:
                return ""

            # 지도 중심점 계산
            center_lat, center_lon = self._calculate_map_center(valid_results)

            # 간단한 지도 생성
            map_viz = folium.Map(
                location=[center_lat, center_lon],
                zoom_start=self.config.zoom_start - 1,
                tiles='OpenStreetMap'
            )

            # 배치별 중심점 마커만 추가
            for batch_idx, result in enumerate(valid_results):
                color = self.batch_colors[batch_idx % len(self.batch_colors)]

                # 배치 중심점 계산
                if result.optimized_waypoints:
                    lats = [wp['latitude'] for wp in result.optimized_waypoints]
                    lons = [wp['longitude'] for wp in result.optimized_waypoints]

                    center_lat = sum(lats) / len(lats)
                    center_lon = sum(lons) / len(lons)

                    folium.Marker(
                        location=[center_lat, center_lon],
                        popup=f"배치 {batch_idx + 1}<br>경유지 {len(result.optimized_waypoints)}개<br>거리: {result.total_distance/1000:.2f}km",
                        tooltip=f"배치 {batch_idx + 1}",
                        icon=folium.Icon(color='red', icon='info-sign')
                    ).add_to(map_viz)

            # 요약 통계 추가
            self._add_statistics_panel(map_viz, valid_results)

            map_viz.save(output_path)
            self.logger.info(f"요약 지도 생성 완료: {output_path}")

            return output_path

        except Exception as e:
            self.logger.error(f"요약 지도 생성 실패: {str(e)}")
            return ""

    def export_route_data(self, optimization_results: List[Any], output_path: str = "route_data.csv") -> str:
        """
        경로 데이터를 CSV로 내보내기

        Args:
            optimization_results: 최적화 결과
            output_path: CSV 파일 경로

        Returns:
            생성된 CSV 파일 경로
        """
        try:
            all_waypoints = []

            for batch_idx, result in enumerate(optimization_results):
                if not result.success:
                    continue

                for wp in result.optimized_waypoints:
                    waypoint_data = {
                        'batch_id': batch_idx + 1,
                        'sequence': wp.get('sequence', 0),
                        'waypoint_type': wp.get('waypoint_type', 'waypoint'),
                        'order_id': wp.get('order_id', ''),
                        'name': wp.get('name', ''),
                        'address': wp.get('address', ''),
                        'road_address': wp.get('road_address', ''),
                        'latitude': wp.get('latitude', 0),
                        'longitude': wp.get('longitude', 0),
                        'user_phone': wp.get('user_phone', ''),
                        'msg_to_rider': wp.get('msg_to_rider', ''),
                        'distance_from_prev': wp.get('distance_from_prev', 0),
                        'duration_from_prev': wp.get('duration_from_prev', 0),
                        'cumulative_distance': wp.get('cumulative_distance', 0),
                        'cumulative_duration': wp.get('cumulative_duration', 0)
                    }
                    all_waypoints.append(waypoint_data)

            # DataFrame 생성 및 CSV 저장
            df = pd.DataFrame(all_waypoints)
            df.to_csv(output_path, index=False, encoding='utf-8-sig')

            self.logger.info(f"경로 데이터 CSV 내보내기 완료: {output_path}")
            return output_path

        except Exception as e:
            self.logger.error(f"CSV 내보내기 실패: {str(e)}")
            return ""