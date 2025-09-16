#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import sys
import os

def check_excel_structure():
    file_path = "CARRY X Doeat 주문현황.xlsx"

    if not os.path.exists(file_path):
        print(f"ERROR: 파일을 찾을 수 없습니다: {file_path}")
        return False

    try:
        # Excel 파일 읽기
        df = pd.read_excel(file_path, engine='openpyxl')

        print("=" * 50)
        print("📊 EXCEL 파일 구조 분석 결과")
        print("=" * 50)
        print(f"✅ Excel 파일 읽기 성공!")
        print(f"📋 전체 행 수: {len(df)}")
        print(f"📋 전체 컬럼 수: {len(df.columns)}")

        print("\n🔍 컬럼 목록:")
        for i, col in enumerate(df.columns, 1):
            print(f"  {i:2d}. {col}")

        print(f"\n📄 첫 3행 미리보기:")
        print(df.head(3).to_string())

        print(f"\n🔍 컬럼별 샘플 데이터:")
        for col in df.columns:
            sample_value = df[col].iloc[0] if len(df) > 0 else "N/A"
            print(f"  {col}: {sample_value}")

        print(f"\n📊 데이터 타입:")
        print(df.dtypes)

        print(f"\n❌ 누락 데이터 확인:")
        print(df.isnull().sum())

        return True

    except Exception as e:
        print(f"ERROR: Excel 파일 읽기 실패: {str(e)}")
        return False

if __name__ == "__main__":
    success = check_excel_structure()
    if not success:
        print("\n❌ Excel 파일 분석 실패 - 작업을 중단합니다.")
        sys.exit(1)
    else:
        print("\n✅ Excel 파일 분석 완료")