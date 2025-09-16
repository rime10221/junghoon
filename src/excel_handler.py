"""
Excel 파일 처리 핸들러
K5: Excel 데이터 구조, K10: Excel 출력 형식
"""

import pandas as pd
import logging
from typing import List, Dict, Any, Tuple
from pathlib import Path
from datetime import datetime

class ExcelHandler:
    """Excel 입출력 처리 클래스"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def parse_input_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        입력 Excel 파일 파싱
        실제 CARRY X Doeat 주문현황 Excel 구조에 맞춰 파싱
        """
        try:
            # Excel 파일 읽기 (실제 값만 읽기)
            df = pd.read_excel(file_path, engine='openpyxl')
            self.logger.info(f"Excel 파일 로드 완료: {len(df)}행")

            self.logger.info(f"감지된 컬럼: {list(df.columns)}")

            # 데이터 변환
            order_data = []
            for idx, row in df.iterrows():
                try:
                    # 실제 컬럼 구조에 맞춰 데이터 추출
                    order_dict = {
                        'id': row.get('id', f"ORDER_{idx+1}"),
                        'created_at': row.get('created_at', ''),
                        'user_id': row.get('user_id', ''),
                        'order_price': row.get('order_price', 0),
                        'product_id': row.get('product_id', ''),
                        'menu_name': row.get('menu_name', ''),
                        'status': row.get('status', ''),
                        'user_phone': row.get('user_phone', ''),
                        'address': row.get('address', ''),  # 메인 주소
                        'road_address': row.get('road_address', ''),  # 도로명 주소
                        'detail_address': row.get('detail_address', ''),
                        'msg_to_rider': row.get('msg_to_rider', ''),
                    }

                    # 주소 정보 확인
                    has_address = bool(order_dict['address'] or order_dict['road_address'])

                    if not has_address:
                        self.logger.warning(f"행 {idx+1}: 주소 정보 없음, 건너뜀")
                        continue

                    # None 값들을 빈 문자열로 변환
                    for key, value in order_dict.items():
                        if value is None or str(value).lower() in ['nan', 'none', 'null']:
                            order_dict[key] = '' if isinstance(value, str) else 0 if key in ['order_price', 'product_id'] else ''

                    order_data.append(order_dict)

                except Exception as e:
                    self.logger.warning(f"행 {idx+1} 파싱 실패: {str(e)}")
                    continue

            if not order_data:
                raise ValueError("유효한 주문 데이터가 없습니다. Excel 파일의 주소 정보를 확인해주세요.")

            self.logger.info(f"총 {len(order_data)}개 주문 데이터 파싱 완료")
            return order_data

        except Exception as e:
            self.logger.error(f"Excel 파일 파싱 실패: {str(e)}")
            raise

    def _extract_value(self, row: pd.Series, column_mapping: Dict[str, str],
                      standard_name: str, default_value: str = '') -> str:
        """행에서 값 추출"""
        for original_col, mapped_name in column_mapping.items():
            if mapped_name == standard_name and original_col in row.index:
                value = row[original_col]
                if pd.notna(value):
                    return str(value).strip()
        return default_value

    def _extract_coordinate(self, row: pd.Series, column_mapping: Dict[str, str],
                          coord_type: str) -> float:
        """좌표 값 추출 및 변환"""
        for original_col, mapped_name in column_mapping.items():
            if mapped_name == coord_type and original_col in row.index:
                value = row[original_col]
                if pd.notna(value):
                    try:
                        return float(value)
                    except (ValueError, TypeError):
                        continue
        return 0.0

    def generate_output_file(self, route_results: List[Any], output_path: str):
        """
        최적화 결과를 Excel 파일로 출력
        K10: Excel 출력 형식 - 최적화된 동선 결과
        """
        try:
            all_routes_data = []
            global_cumulative_distance = 0  # 전체 경로 누적거리
            global_cumulative_duration = 0  # 전체 경로 누적시간

            for batch_idx, route_result in enumerate(route_results):
                # 배치별 결과 처리 (전역 누적 거리/시간 전달)
                batch_data, global_cumulative_distance, global_cumulative_duration = self._format_route_result_with_global(
                    route_result,
                    batch_idx + 1,
                    global_cumulative_distance,
                    global_cumulative_duration
                )
                all_routes_data.extend(batch_data)

            # DataFrame 생성
            df_output = pd.DataFrame(all_routes_data)

            # Excel 파일 생성 (여러 시트)
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                # 메인 시트: 최적화된 경로 순서
                df_output.to_excel(writer, sheet_name='최적화경로', index=False)

                # 요약 시트: 배치별 통계
                summary_data = self._generate_summary_data(route_results)
                df_summary = pd.DataFrame(summary_data)
                df_summary.to_excel(writer, sheet_name='경로요약', index=False)

                # 설명 시트
                self._add_instruction_sheet(writer)

            self.logger.info(f"결과 파일 생성 완료: {output_path}")

        except Exception as e:
            self.logger.error(f"출력 파일 생성 실패: {str(e)}")
            raise

    def _format_route_result_with_global(self, route_result: Any, batch_number: int,
                                        start_cumulative_distance: float, start_cumulative_duration: float) -> Tuple[List[Dict[str, Any]], float, float]:
        """경로 결과를 출력 형식으로 변환 (전역 누적 거리/시간 계산)"""
        formatted_data = []
        current_cumulative_distance = start_cumulative_distance
        current_cumulative_duration = start_cumulative_duration

        for idx, waypoint in enumerate(route_result.waypoints_order):
            # 이전 지점으로부터의 거리/시간 계산 (sections 정보 활용)
            if idx == 0 and batch_number > 1:
                # 클러스터간 연결 거리/시간 추정 (이전 배치의 마지막 지점과 현재 배치의 첫 지점 간)
                distance_from_prev = getattr(route_result, 'cluster_connection_distance', 0.0)
                duration_from_prev = getattr(route_result, 'cluster_connection_duration', 0.0)
                # 연결정보가 없다면 0으로 처리 (단일지점일 경우)
            elif idx == 0:
                # 첫 번째 배치의 첫 지점
                distance_from_prev = 0
                duration_from_prev = 0
            else:
                # sections에서 해당 구간 정보 추출
                if idx - 1 < len(route_result.sections):
                    section = route_result.sections[idx - 1]
                    distance_from_prev = section.get('distance', 0)
                    duration_from_prev = section.get('duration', 0)
                else:
                    distance_from_prev = 0
                    duration_from_prev = 0

            # 전역 누적 계산
            if idx > 0 or batch_number == 1:  # 첫 번째 지점이 아니거나 첫 번째 배치
                current_cumulative_distance += distance_from_prev
                current_cumulative_duration += duration_from_prev

            # 지점 유형 결정
            if idx == 0:
                point_type = "출발지"
            elif idx == len(route_result.waypoints_order) - 1:
                point_type = "목적지"
            else:
                point_type = "경유지"

            formatted_data.append({
                '배치번호': batch_number,
                '순서': idx + 1,
                '지점유형': point_type,
                '주문번호': waypoint.order_id,
                '이름': waypoint.name,
                '주소': waypoint.address,
                '경도': waypoint.x,
                '위도': waypoint.y,
                '이전지점거리(m)': distance_from_prev,
                '이전지점시간(초)': duration_from_prev,
                '이전지점시간(분)': round(duration_from_prev / 60, 1) if duration_from_prev > 0 else 0,
                '누적거리(m)': int(current_cumulative_distance),
                '누적시간(초)': int(current_cumulative_duration),
                '누적시간(분)': round(current_cumulative_duration / 60, 1),
                '누적거리(km)': round(current_cumulative_distance / 1000, 2)
            })

        return formatted_data, current_cumulative_distance, current_cumulative_duration

    def _format_route_result(self, route_result: Any, batch_number: int) -> List[Dict[str, Any]]:
        """경로 결과를 출력 형식으로 변환"""
        formatted_data = []

        for idx, waypoint in enumerate(route_result.waypoints_order):
            # 이전 지점으로부터의 거리/시간 계산 (sections 정보 활용)
            if idx == 0:
                # 출발지
                distance_from_prev = 0
                duration_from_prev = 0
                cumulative_distance = 0
                cumulative_duration = 0
            else:
                # sections에서 해당 구간 정보 추출
                if idx - 1 < len(route_result.sections):
                    section = route_result.sections[idx - 1]
                    distance_from_prev = section.get('distance', 0)
                    duration_from_prev = section.get('duration', 0)
                else:
                    distance_from_prev = 0
                    duration_from_prev = 0

                # 누적 계산
                if formatted_data:
                    cumulative_distance = formatted_data[-1]['누적거리(m)'] + distance_from_prev
                    cumulative_duration = formatted_data[-1]['누적시간(초)'] + duration_from_prev
                else:
                    cumulative_distance = distance_from_prev
                    cumulative_duration = duration_from_prev

            # 지점 유형 결정
            if idx == 0:
                point_type = "출발지"
            elif idx == len(route_result.waypoints_order) - 1:
                point_type = "목적지"
            else:
                point_type = "경유지"

            formatted_data.append({
                '배치번호': batch_number,
                '순서': idx + 1,
                '지점유형': point_type,
                '주문번호': waypoint.order_id,
                '이름': waypoint.name,
                '주소': waypoint.address,
                '경도': waypoint.x,
                '위도': waypoint.y,
                '이전지점거리(m)': distance_from_prev,
                '이전지점시간(초)': duration_from_prev,
                '이전지점시간(분)': round(duration_from_prev / 60, 1) if duration_from_prev > 0 else 0,
                '누적거리(m)': cumulative_distance,
                '누적시간(초)': cumulative_duration,
                '누적시간(분)': round(cumulative_duration / 60, 1),
                '누적거리(km)': round(cumulative_distance / 1000, 2)
            })

        return formatted_data

    def _format_optimization_result_with_global_cumulative(self, result, batch_number: int,
                                                          start_cumulative_distance: float,
                                                          start_cumulative_duration: float) -> Tuple[List[Dict[str, Any]], float, float]:
        """RouteOptimizationResult를 전체 누적거리/시간과 함께 Excel 형식으로 변환"""
        formatted_data = []
        current_cumulative_distance = start_cumulative_distance
        current_cumulative_duration = start_cumulative_duration

        for idx, waypoint in enumerate(result.optimized_waypoints):
            # 이전 지점으로부터의 거리/시간 계산
            if idx == 0 and batch_number > 1:
                # 배치간 연결 거리/시간 (Global Route Optimizer에서 계산됨)
                distance_from_prev = getattr(result, 'cluster_connection_distance', 0.0)
                duration_from_prev = getattr(result, 'cluster_connection_duration', 0.0)
            elif idx == 0:
                # 첫 번째 배치의 첫 지점
                distance_from_prev = 0
                duration_from_prev = 0
            else:
                # waypoint에 저장된 거리/시간 정보 사용
                distance_from_prev = waypoint.get('distance_from_prev', 0)
                duration_from_prev = waypoint.get('duration_from_prev', 0)

            # 전역 누적 계산
            if idx > 0 or batch_number > 1:  # 첫 번째 배치의 첫 지점이 아닌 경우
                current_cumulative_distance += distance_from_prev
                current_cumulative_duration += duration_from_prev

            # 지점 유형 결정
            if idx == 0:
                point_type = "출발지"
            elif idx == len(result.optimized_waypoints) - 1:
                point_type = "목적지"
            else:
                point_type = "경유지"

            formatted_data.append({
                '배치번호': batch_number,
                '순서': waypoint.get('sequence', idx) + 1,
                '지점유형': waypoint.get('waypoint_type', point_type),
                '주문번호': waypoint.get('order_id', ''),
                '이름': waypoint.get('name', ''),
                '주소': waypoint.get('address', ''),
                '도로명주소': waypoint.get('road_address', ''),
                '경도': waypoint.get('longitude', waypoint.get('x', 0)),
                '위도': waypoint.get('latitude', waypoint.get('y', 0)),
                '연락처': waypoint.get('user_phone', ''),
                '배송메모': waypoint.get('msg_to_rider', ''),
                '이전지점거리(m)': distance_from_prev,
                '이전지점시간(초)': duration_from_prev,
                '이전지점시간(분)': round(duration_from_prev / 60, 1) if duration_from_prev > 0 else 0,
                '누적거리(m)': int(current_cumulative_distance),
                '누적시간(초)': int(current_cumulative_duration),
                '누적시간(분)': round(current_cumulative_duration / 60, 1),
                '누적거리(km)': round(current_cumulative_distance / 1000, 2)
            })

        return formatted_data, current_cumulative_distance, current_cumulative_duration

    def _generate_summary_data(self, route_results: List[Any]) -> List[Dict[str, Any]]:
        """배치별 요약 통계 생성"""
        summary_data = []

        total_distance = 0
        total_duration = 0

        for idx, route_result in enumerate(route_results):
            batch_distance = route_result.total_distance
            batch_duration = route_result.total_duration

            total_distance += batch_distance
            total_duration += batch_duration

            summary_data.append({
                '배치번호': idx + 1,
                '경유지수': len(route_result.waypoints_order) - 2,  # 출발지, 목적지 제외
                '총거리(m)': batch_distance,
                '총거리(km)': round(batch_distance / 1000, 2),
                '총시간(초)': batch_duration,
                '총시간(분)': round(batch_duration / 60, 1),
                '총시간(시간)': round(batch_duration / 3600, 2),
                '평균속도(km/h)': round((batch_distance / 1000) / (batch_duration / 3600), 1) if batch_duration > 0 else 0
            })

        # 전체 합계 추가
        summary_data.append({
            '배치번호': '전체',
            '경유지수': sum(len(r.waypoints_order) - 2 for r in route_results),
            '총거리(m)': total_distance,
            '총거리(km)': round(total_distance / 1000, 2),
            '총시간(초)': total_duration,
            '총시간(분)': round(total_duration / 60, 1),
            '총시간(시간)': round(total_duration / 3600, 2),
            '평균속도(km/h)': round((total_distance / 1000) / (total_duration / 3600), 1) if total_duration > 0 else 0
        })

        return summary_data

    def save_geocoded_data(self, geocoded_data: List[Dict], output_path: str):
        """
        지오코딩 결과를 Excel 파일로 저장
        --geocode-only 옵션용
        """
        try:
            # DataFrame 생성
            df_geocoded = pd.DataFrame(geocoded_data)

            # 컬럼 순서 정리
            column_order = [
                'id', 'created_at', 'user_id', 'order_price',
                'address', 'road_address', 'detail_address',
                'longitude', 'latitude', 'formatted_address',
                'geocoding_accuracy', 'geocoding_source',
                'menu_name', 'status', 'user_phone', 'msg_to_rider'
            ]

            # 존재하는 컬럼만 선택
            available_columns = [col for col in column_order if col in df_geocoded.columns]
            df_geocoded = df_geocoded[available_columns]

            # Excel 파일 생성
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                df_geocoded.to_excel(writer, sheet_name='지오코딩결과', index=False)

                # 요약 시트 추가
                summary_data = [
                    {'항목': '전체 주문 수', '값': len(geocoded_data)},
                    {'항목': '좌표 변환 성공', '값': len([d for d in geocoded_data if d.get('longitude', 0) != 0])},
                    {'항목': '카카오 API 사용', '값': len([d for d in geocoded_data if d.get('geocoding_source') == 'kakao_api'])},
                    {'항목': '기존 좌표 사용', '값': len([d for d in geocoded_data if d.get('geocoding_source') == 'existing'])},
                    {'항목': '생성일시', '값': datetime.now().strftime('%Y-%m-%d %H:%M:%S')},
                ]

                df_summary = pd.DataFrame(summary_data)
                df_summary.to_excel(writer, sheet_name='요약', index=False)

            self.logger.info(f"지오코딩 결과 저장 완료: {output_path}")

        except Exception as e:
            self.logger.error(f"지오코딩 결과 저장 실패: {str(e)}")
            raise

    def _add_instruction_sheet(self, writer):
        """사용법 설명 시트 추가"""
        instructions = [
            {'항목': '프로그램명', '설명': '다중 경유지 최적화 동선 프로그램'},
            {'항목': '생성일시', '설명': datetime.now().strftime('%Y-%m-%d %H:%M:%S')},
            {'항목': '', '설명': ''},
            {'항목': '시트 설명', '설명': ''},
            {'항목': '- 최적화경로', '설명': '최적화된 경로 순서별 상세 정보'},
            {'항목': '- 경로요약', '설명': '배치별 거리/시간 요약 통계'},
            {'항목': '- 사용법', '설명': '현재 시트 - 프로그램 사용법'},
            {'항목': '', '설명': ''},
            {'항목': '주의사항', '설명': ''},
            {'항목': '- API 제약', '설명': '경유지 최대 30개, 총거리 1,500km 미만'},
            {'항목': '- 좌표 형식', '설명': 'WGS84 경위도 좌표계 사용'},
            {'항목': '- 30개 초과', '설명': '자동으로 배치 분할 처리됨'},
            {'항목': '', '설명': ''},
            {'항목': '컬럼 설명', '설명': ''},
            {'항목': '- 배치번호', '설명': '30개 초과 시 분할된 배치 번호'},
            {'항목': '- 순서', '설명': '최적화된 방문 순서'},
            {'항목': '- 누적거리/시간', '설명': '출발지부터 해당 지점까지 누적값'},
            {'항목': '- 이전지점거리/시간', '설명': '바로 이전 지점으로부터의 거리/시간'},
        ]

        df_instructions = pd.DataFrame(instructions)
        df_instructions.to_excel(writer, sheet_name='사용법', index=False)

    def save_optimization_results(self, optimization_results: List[Any], output_path: str):
        """
        경로 최적화 결과를 Excel 파일로 저장
        RouteOptimizationResult 객체들을 처리
        """
        try:
            # 📊 엑셀 출력 단계 추적 시작
            self.logger.info(f"🔍 엑셀 출력 단계: {len(optimization_results)}개 최적화 결과 처리 시작")

            all_routes_data = []
            summary_data = []
            total_waypoints_processed = 0
            global_cumulative_distance = 0  # 전체 경로 누적거리
            global_cumulative_duration = 0  # 전체 경로 누적시간

            for idx, result in enumerate(optimization_results):
                batch_waypoints = len(result.optimized_waypoints) if result.success else 0
                total_waypoints_processed += batch_waypoints

                self.logger.info(f"🔍 배치 {idx+1}: 성공={result.success}, 지점수={batch_waypoints}")

                if result.success:
                    # 전체 누적거리를 고려한 배치별 경로 데이터 생성
                    batch_routes, global_cumulative_distance, global_cumulative_duration = self._format_optimization_result_with_global_cumulative(
                        result, idx + 1, global_cumulative_distance, global_cumulative_duration
                    )
                    all_routes_data.extend(batch_routes)
                    self.logger.debug(f"🔍 배치 {idx+1}: {len(batch_routes)}개 지점 엑셀 데이터로 변환 완료 (누적거리: {global_cumulative_distance:.0f}m)")

                # 배치 요약 정보 추가
                summary_data.append({
                    '배치번호': result.batch_id + 1,
                    '성공여부': '성공' if result.success else '실패',
                    '경유지수': result.total_waypoints,
                    '총거리(m)': result.total_distance,
                    '총거리(km)': round(result.total_distance / 1000, 2),
                    '총시간(초)': result.total_duration,
                    '총시간(분)': round(result.total_duration / 60, 1),
                    '총시간(시간)': round(result.total_duration / 3600, 2),
                    '평균속도(km/h)': round((result.total_distance / 1000) / (result.total_duration / 3600), 1) if result.total_duration > 0 else 0,
                    '오류메시지': result.error_message or ''
                })

            # 📊 최종 엑셀 파일 생성 전 검증
            self.logger.info(f"🔍 엑셀 생성 직전: 총 {total_waypoints_processed}개 지점, 엑셀 행={len(all_routes_data)}")
            self.logger.info(f"🔍 성공한 배치 수: {len([r for r in optimization_results if r.success])}/{len(optimization_results)}")

            # Excel 파일 생성
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                # 메인 시트: 최적화된 경로
                if all_routes_data:
                    df_routes = pd.DataFrame(all_routes_data)
                    df_routes.to_excel(writer, sheet_name='최적화경로', index=False)
                    self.logger.info(f"🔍 엑셀 '최적화경로' 시트: {len(df_routes)}행 저장")

                # 요약 시트: 배치별 통계
                df_summary = pd.DataFrame(summary_data)
                df_summary.to_excel(writer, sheet_name='경로요약', index=False)
                self.logger.info(f"🔍 엑셀 '경로요약' 시트: {len(df_summary)}행 저장")

                # 설명 시트
                self._add_instruction_sheet(writer)

            self.logger.info(f"🔍 최적화 결과 저장 완료: {output_path}")
            self.logger.info(f"🔍 최종 엑셀 파일에 포함된 주소 수: {len(all_routes_data)}개")

        except Exception as e:
            self.logger.error(f"최적화 결과 저장 실패: {str(e)}")
            raise

    def _format_optimization_result(self, result: Any) -> List[Dict[str, Any]]:
        """RouteOptimizationResult를 출력 형식으로 변환"""
        formatted_data = []

        for waypoint in result.optimized_waypoints:
            formatted_data.append({
                '배치번호': result.batch_id + 1,
                '순서': waypoint['sequence'] + 1,
                '지점유형': waypoint['waypoint_type'],
                '주문번호': waypoint['order_id'],
                '이름': waypoint['name'],
                '주소': waypoint['address'],
                '도로명주소': waypoint['road_address'],
                '경도': waypoint['longitude'],
                '위도': waypoint['latitude'],
                '연락처': waypoint['user_phone'],
                '배송메모': waypoint['msg_to_rider'],
                '이전지점거리(m)': waypoint['distance_from_prev'],
                '이전지점시간(초)': waypoint['duration_from_prev'],
                '이전지점시간(분)': round(waypoint['duration_from_prev'] / 60, 1) if waypoint['duration_from_prev'] > 0 else 0,
                '누적거리(m)': waypoint['cumulative_distance'],
                '누적시간(초)': waypoint['cumulative_duration'],
                '누적시간(분)': round(waypoint['cumulative_duration'] / 60, 1),
                '누적거리(km)': round(waypoint['cumulative_distance'] / 1000, 2)
            })

        return formatted_data