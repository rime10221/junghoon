"""
py2app setup script for macOS .app bundle creation
macOS용 .app 번들 생성을 위한 설정 파일
"""

from setuptools import setup
import py2app
import os

# 앱 정보
APP = ['gui_perfect.py']
DATA_FILES = [
    # 메인 프로그램 파일들
    'main.py',
    'src/',
    'requirements.txt',
    # 설정 파일 (있다면)
    '.env.example'
]

# py2app 옵션
OPTIONS = {
    'py2app': {
        'argv_emulation': False,
        'iconfile': None,  # 아이콘 파일이 있다면 경로 지정
        'plist': {
            'CFBundleName': 'CARRY Route Optimizer',
            'CFBundleDisplayName': 'CARRY Route Optimizer',
            'CFBundleIdentifier': 'com.carry.routeoptimizer',
            'CFBundleVersion': '1.0.0',
            'CFBundleShortVersionString': '1.0.0',
            'CFBundleGetInfoString': 'CARRY Route Optimizer v1.0.0',
            'NSHumanReadableCopyright': 'Copyright © 2024 CARRY. All rights reserved.',
            'CFBundleDocumentTypes': [
                {
                    'CFBundleTypeName': 'Excel Files',
                    'CFBundleTypeExtensions': ['xlsx', 'xls'],
                    'CFBundleTypeRole': 'Editor',
                    'CFBundleTypeIconFile': None,
                    'LSHandlerRank': 'Owner',
                }
            ],
            # macOS 권한 설정
            'NSAppleEventsUsageDescription': 'Excel 파일 열기를 위해 필요합니다.',
            'NSDesktopFolderUsageDescription': '결과 파일 저장을 위해 데스크톱 접근이 필요합니다.',
            'NSDocumentsFolderUsageDescription': '파일 접근을 위해 필요합니다.',
            'NSDownloadsFolderUsageDescription': '파일 접근을 위해 필요합니다.',
        },
        'packages': [
            'requests',
            'pandas',
            'openpyxl',
            'click',
            'python-dotenv',
            'urllib3',
            'certifi',
            'PyQt6',
            'PyQt6.QtCore',
            'PyQt6.QtWidgets',
            'PyQt6.QtGui'
        ],
        'includes': [
            'PyQt6.QtCore',
            'PyQt6.QtWidgets',
            'PyQt6.QtGui',
            'threading',
            'subprocess',
            'os',
            'sys',
            'pathlib',
            'logging',
            'src.route_optimizer',
            'src.excel_handler',
            'src.geocoder',
            'src.logger_config',
            'src.global_route_optimizer',
            'src.batch_processor',
            'src.kakao_api',
            'src.tsp_solver'
        ],
        'resources': [],
        'frameworks': [],
        'site_packages': True,
        'strip': False,
        'debug_modulegraph': False,
        'debug_skip_macholib': False,
    }
}

setup(
    name='CARRY Route Optimizer',
    app=APP,
    data_files=DATA_FILES,
    options=OPTIONS,
    setup_requires=['py2app'],
    install_requires=[
        'requests>=2.31.0',
        'pandas>=2.0.0',
        'openpyxl>=3.1.0',
        'click>=8.1.0',
        'python-dotenv>=1.0.0',
        'PyQt6>=6.4.0'
    ]
)