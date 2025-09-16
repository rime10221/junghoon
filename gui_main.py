#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PyQt6 GUI wrapper for route optimizer
main.py를 통해서 route optimizer에 접근
"""

import sys
import os
import subprocess
import json
import threading
import time
from pathlib import Path
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QPushButton, QLineEdit, QComboBox, QTextEdit,
    QProgressBar, QFileDialog, QFrame, QScrollArea
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QPalette, QBrush, QLinearGradient, QColor

class RouteOptimizerThread(QThread):
    progress_update = pyqtSignal(str, str)  # message, level
    file_progress = pyqtSignal(str)  # current file
    overall_progress = pyqtSignal(int)  # percentage
    finished_signal = pyqtSignal(bool, str)  # success, message

    def __init__(self, input_folder, output_folder, api_key, priority):
        super().__init__()
        self.input_folder = input_folder
        self.output_folder = output_folder
        self.api_key = api_key
        self.priority = priority
        self.is_running = True

    def run(self):
        try:
            self.progress_update.emit("배치 처리를 시작합니다...", "info")

            # Find Excel files
            excel_files = list(Path(self.input_folder).glob("*.xlsx"))
            if not excel_files:
                self.finished_signal.emit(False, "입력 폴더에서 Excel 파일을 찾을 수 없습니다.")
                return

            total_files = len(excel_files)
            self.progress_update.emit(f"{total_files}개의 Excel 파일을 발견했습니다.", "info")

            success_count = 0
            for i, excel_file in enumerate(excel_files):
                if not self.is_running:
                    break

                self.file_progress.emit(f"처리 중: {excel_file.name}")
                self.overall_progress.emit(int((i / total_files) * 100))

                try:
                    # Use main.py to process the file
                    self.progress_update.emit(f"📂 {excel_file.name} 파일 처리 시작", "info")

                    # Prepare command
                    cmd = [
                        "C:\\ProgramData\\anaconda3\\python.exe",
                        "main.py",
                        "--input", str(excel_file),
                        "--no-map",
                        "--priority", self.priority
                    ]

                    # Set API key environment
                    env = os.environ.copy()
                    if self.api_key:
                        env['KAKAO_REST_API_KEY'] = self.api_key

                    # Run the command
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        cwd=os.getcwd(),
                        env=env,
                        timeout=300  # 5 minute timeout
                    )

                    if result.returncode == 0:
                        # Move result to output folder
                        original_output = Path("optimized_route.xlsx")
                        if original_output.exists():
                            new_output = Path(self.output_folder) / f"최적화_{excel_file.name}"
                            original_output.rename(new_output)
                            self.progress_update.emit(f"✅ {excel_file.name} 처리 완료 → {new_output.name}", "success")
                            success_count += 1
                        else:
                            self.progress_update.emit(f"⚠️ {excel_file.name} 결과 파일을 찾을 수 없습니다", "warning")
                    else:
                        error_msg = result.stderr.strip() or "알 수 없는 오류"
                        self.progress_update.emit(f"❌ {excel_file.name} 처리 실패: {error_msg}", "error")

                except subprocess.TimeoutExpired:
                    self.progress_update.emit(f"⏰ {excel_file.name} 처리 시간 초과 (5분)", "error")
                except Exception as e:
                    self.progress_update.emit(f"❌ {excel_file.name} 오류: {str(e)}", "error")

            self.overall_progress.emit(100)
            self.finished_signal.emit(True, f"배치 처리 완료! {success_count}/{total_files}개 파일 처리 성공")

        except Exception as e:
            import traceback
            error_msg = f"배치 처리 오류: {str(e)}\n{traceback.format_exc()}"
            self.progress_update.emit(error_msg, "error")
            self.finished_signal.emit(False, f"배치 처리 오류: {str(e)}")

    def stop(self):
        self.is_running = False

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.worker_thread = None
        self.init_ui()
        self.apply_styles()

    def init_ui(self):
        self.setWindowTitle("🚚 배송 경로 최적화")
        self.setGeometry(100, 100, 1200, 800)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout (2-panel)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Left panel
        left_panel = self.create_left_panel()
        main_layout.addWidget(left_panel, 1)

        # Right panel
        right_panel = self.create_right_panel()
        main_layout.addWidget(right_panel, 1)

    def create_left_panel(self):
        # Left panel container
        left_container = QVBoxLayout()

        # Config panel
        config_frame = QFrame()
        config_frame.setObjectName("config-panel")
        config_layout = QVBoxLayout(config_frame)

        # Folder selection section
        folder_section = self.create_folder_section()
        config_layout.addLayout(folder_section)

        # Settings section
        settings_section = self.create_settings_section()
        config_layout.addLayout(settings_section)

        # Action buttons
        actions_section = self.create_actions_section()
        config_layout.addLayout(actions_section)

        left_container.addWidget(config_frame)

        # Status panel
        status_frame = self.create_status_panel()
        left_container.addWidget(status_frame)

        # Create left widget
        left_widget = QWidget()
        left_widget.setLayout(left_container)
        return left_widget

    def create_folder_section(self):
        layout = QVBoxLayout()

        # Input folder
        input_layout = QVBoxLayout()
        input_label = QLabel("📁 입력 폴더 (Excel 파일들)")
        input_label.setObjectName("folder-label")
        input_layout.addWidget(input_label)

        input_row = QHBoxLayout()
        self.input_folder_edit = QLineEdit()
        self.input_folder_edit.setPlaceholderText("Excel 파일이 있는 폴더를 선택하세요")
        self.input_folder_edit.setReadOnly(True)
        input_row.addWidget(self.input_folder_edit)

        input_btn = QPushButton("폴더 선택")
        input_btn.setObjectName("btn-primary")
        input_btn.clicked.connect(self.select_input_folder)
        input_row.addWidget(input_btn)

        input_layout.addLayout(input_row)

        # File list
        self.input_files_label = QLabel("")
        self.input_files_label.setObjectName("file-list")
        input_layout.addWidget(self.input_files_label)

        layout.addLayout(input_layout)

        # Output folder
        output_layout = QVBoxLayout()
        output_label = QLabel("📤 출력 폴더 (결과 파일들)")
        output_label.setObjectName("folder-label")
        output_layout.addWidget(output_label)

        output_row = QHBoxLayout()
        self.output_folder_edit = QLineEdit()
        self.output_folder_edit.setPlaceholderText("결과 파일을 저장할 폴더를 선택하세요")
        self.output_folder_edit.setReadOnly(True)
        output_row.addWidget(self.output_folder_edit)

        output_btn = QPushButton("폴더 선택")
        output_btn.setObjectName("btn-primary")
        output_btn.clicked.connect(self.select_output_folder)
        output_row.addWidget(output_btn)

        output_layout.addLayout(output_row)
        layout.addLayout(output_layout)

        return layout

    def create_settings_section(self):
        layout = QVBoxLayout()

        # API Key
        api_layout = QVBoxLayout()
        api_label = QLabel("🔑 카카오 API 키")
        api_label.setObjectName("folder-label")
        api_layout.addWidget(api_label)

        api_row = QHBoxLayout()
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setPlaceholderText("카카오 모빌리티 API 키를 입력하세요")
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        api_row.addWidget(self.api_key_edit)

        self.toggle_api_btn = QPushButton("👁️")
        self.toggle_api_btn.setObjectName("btn-small")
        self.toggle_api_btn.clicked.connect(self.toggle_api_visibility)
        api_row.addWidget(self.toggle_api_btn)

        api_layout.addLayout(api_row)

        api_help = QLabel("환경변수 또는 .env 파일에 설정된 키가 기본값으로 사용됩니다")
        api_help.setObjectName("api-key-help")
        api_layout.addWidget(api_help)

        layout.addLayout(api_layout)

        # Priority selection
        priority_layout = QVBoxLayout()
        priority_label = QLabel("🎯 최적화 우선순위")
        priority_label.setObjectName("folder-label")
        priority_layout.addWidget(priority_label)

        self.priority_combo = QComboBox()
        self.priority_combo.addItems([
            "시간 우선 (기본)",
            "거리 우선",
            "추천 (균형)"
        ])
        priority_layout.addWidget(self.priority_combo)

        layout.addLayout(priority_layout)

        return layout

    def create_actions_section(self):
        layout = QHBoxLayout()
        layout.setSpacing(15)

        self.start_btn = QPushButton("🚀 배치 처리 시작")
        self.start_btn.setObjectName("btn-success")
        self.start_btn.clicked.connect(self.start_processing)
        self.start_btn.setEnabled(False)
        layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("⏹️ 처리 중단")
        self.stop_btn.setObjectName("btn-danger")
        self.stop_btn.clicked.connect(self.stop_processing)
        self.stop_btn.setEnabled(False)
        layout.addWidget(self.stop_btn)

        return layout

    def create_status_panel(self):
        status_frame = QFrame()
        status_frame.setObjectName("status-panel")
        status_layout = QVBoxLayout(status_frame)

        # Header
        header_layout = QHBoxLayout()
        status_title = QLabel("📊 처리 상태")
        status_title.setObjectName("status-title")
        header_layout.addWidget(status_title)

        self.status_indicator = QLabel("준비")
        self.status_indicator.setObjectName("status-ready")
        header_layout.addWidget(self.status_indicator)

        status_layout.addLayout(header_layout)

        # Progress info
        self.current_file_label = QLabel("")
        self.current_file_label.setObjectName("current-file")
        status_layout.addWidget(self.current_file_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("progress-bar")
        status_layout.addWidget(self.progress_bar)

        self.progress_text = QLabel("0%")
        self.progress_text.setObjectName("progress-text")
        self.progress_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_layout.addWidget(self.progress_text)

        return status_frame

    def create_right_panel(self):
        right_frame = QFrame()
        right_frame.setObjectName("log-panel")
        right_layout = QVBoxLayout(right_frame)

        # Header
        header_layout = QHBoxLayout()
        log_title = QLabel("📋 처리 로그")
        log_title.setObjectName("log-title")
        header_layout.addWidget(log_title)

        clear_btn = QPushButton("로그 지우기")
        clear_btn.setObjectName("btn-small")
        clear_btn.clicked.connect(self.clear_log)
        header_layout.addWidget(clear_btn)

        right_layout.addLayout(header_layout)

        # Log container
        self.log_text = QTextEdit()
        self.log_text.setObjectName("log-container")
        self.log_text.setReadOnly(True)
        right_layout.addWidget(self.log_text)

        # Initial log entry
        self.add_log_entry("🚀 실제 경로 최적화 기능이 활성화되었습니다!", "success")
        self.add_log_entry("입력 폴더와 출력 폴더를 선택한 후 배치 처리를 시작하세요.", "info")

        return right_frame

    def apply_styles(self):
        style = """
        QMainWindow {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #667eea, stop:1 #764ba2);
            font-family: 'Malgun Gothic', 'Arial', sans-serif;
            color: #333;
        }

        QFrame#config-panel, QFrame#status-panel {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #ffffff, stop:1 #f8f9ff);
            border-radius: 12px;
            padding: 25px;
            margin: 5px;
            border: 1px solid rgba(0,0,0,0.1);
        }

        QFrame#log-panel {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #ffffff, stop:1 #f0f8ff);
            border-radius: 12px;
            padding: 25px;
            margin: 5px;
            border: 1px solid rgba(0,0,0,0.1);
        }

        QLabel#folder-label, QLabel#status-title, QLabel#log-title {
            font-size: 18px;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 8px;
        }

        QLineEdit {
            padding: 12px 16px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 14px;
            background: white;
        }

        QLineEdit:focus {
            border-color: #667eea;
        }

        QPushButton#btn-primary {
            background: #667eea;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 12px 24px;
            font-size: 14px;
            font-weight: bold;
        }

        QPushButton#btn-primary:hover {
            background: #5a6fd8;
        }

        QPushButton#btn-success {
            background: #28a745;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 12px 24px;
            font-size: 14px;
            font-weight: bold;
        }

        QPushButton#btn-success:hover {
            background: #218838;
        }

        QPushButton#btn-danger {
            background: #dc3545;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 12px 24px;
            font-size: 14px;
            font-weight: bold;
        }

        QPushButton#btn-danger:hover {
            background: #c82333;
        }

        QPushButton#btn-small {
            padding: 8px 16px;
            font-size: 12px;
        }

        QComboBox {
            padding: 12px 16px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 14px;
            background: white;
        }

        QComboBox:focus {
            border-color: #667eea;
        }

        QLabel#status-ready {
            background: #e3f2fd;
            color: #1976d2;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
        }

        QLabel#status-processing {
            background: #fff3e0;
            color: #f57c00;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
        }

        QLabel#status-success {
            background: #e8f5e8;
            color: #2e7d32;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
        }

        QLabel#status-error {
            background: #ffebee;
            color: #c62828;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
        }

        QLabel#current-file {
            font-size: 12px;
            color: #666;
            margin-bottom: 10px;
            min-height: 20px;
        }

        QProgressBar {
            border: none;
            border-radius: 4px;
            background: #e0e0e0;
            height: 8px;
        }

        QProgressBar::chunk {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #667eea, stop:1 #764ba2);
            border-radius: 4px;
        }

        QLabel#progress-text {
            text-align: center;
            font-size: 12px;
            color: #666;
        }

        QLabel#file-list {
            padding: 10px;
            background: #f1f3f4;
            border-radius: 6px;
            min-height: 40px;
            font-size: 12px;
            color: #666;
        }

        QLabel#api-key-help {
            font-size: 11px;
            color: #666;
            font-style: italic;
            margin-top: 5px;
        }

        QTextEdit#log-container {
            background: #f8f9fa;
            border-radius: 8px;
            border: 1px solid #e9ecef;
            padding: 8px;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 11px;
            line-height: 1.1;
        }
        """
        self.setStyleSheet(style)

    def select_input_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "입력 폴더 선택",
            str(Path.home())
        )
        if folder:
            self.input_folder_edit.setText(folder)
            self.update_file_list(folder)
            self.check_ready_state()

    def select_output_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "출력 폴더 선택",
            str(Path.home())
        )
        if folder:
            self.output_folder_edit.setText(folder)
            self.check_ready_state()

    def update_file_list(self, folder_path):
        try:
            excel_files = list(Path(folder_path).glob("*.xlsx"))
            if excel_files:
                file_list = "\n".join([f"• {f.name}" for f in excel_files[:5]])
                if len(excel_files) > 5:
                    file_list += f"\n... 외 {len(excel_files) - 5}개"
                self.input_files_label.setText(file_list)
                self.input_files_label.setObjectName("file-list-has-files")
            else:
                self.input_files_label.setText("Excel 파일이 없습니다.")
                self.input_files_label.setObjectName("file-list")
        except Exception as e:
            self.input_files_label.setText(f"오류: {str(e)}")

    def check_ready_state(self):
        input_ready = bool(self.input_folder_edit.text().strip())
        output_ready = bool(self.output_folder_edit.text().strip())
        self.start_btn.setEnabled(input_ready and output_ready)

    def toggle_api_visibility(self):
        if self.api_key_edit.echoMode() == QLineEdit.EchoMode.Password:
            self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_api_btn.setText("🙈")
        else:
            self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_api_btn.setText("👁️")

    def get_priority_value(self):
        priority_map = {
            "시간 우선 (기본)": "TIME",
            "거리 우선": "DISTANCE",
            "추천 (균형)": "RECOMMEND"
        }
        return priority_map.get(self.priority_combo.currentText(), "TIME")

    def start_processing(self):
        # Validate inputs
        input_folder = self.input_folder_edit.text().strip()
        output_folder = self.output_folder_edit.text().strip()
        api_key = self.api_key_edit.text().strip()

        if not input_folder or not output_folder:
            self.add_log_entry("❌ 입력 폴더와 출력 폴더를 모두 선택해주세요.", "error")
            return

        # Get API key from env if not provided
        if not api_key:
            api_key = os.getenv('KAKAO_REST_API_KEY')
            if not api_key:
                # Try to load from .env file
                env_file = Path('.env')
                if env_file.exists():
                    with open(env_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            if line.startswith('KAKAO_REST_API_KEY='):
                                api_key = line.split('=', 1)[1].strip().strip('"\'')
                                break

        if not api_key:
            self.add_log_entry("❌ API 키를 입력하거나 환경변수에 설정해주세요.", "error")
            return

        # Update UI state
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_indicator.setText("처리중")
        self.status_indicator.setObjectName("status-processing")
        self.status_indicator.setStyleSheet(self.styleSheet())

        # Start worker thread
        priority = self.get_priority_value()
        self.worker_thread = RouteOptimizerThread(
            input_folder, output_folder, api_key, priority
        )

        # Connect signals
        self.worker_thread.progress_update.connect(self.add_log_entry)
        self.worker_thread.file_progress.connect(self.update_file_progress)
        self.worker_thread.overall_progress.connect(self.update_progress)
        self.worker_thread.finished_signal.connect(self.processing_finished)

        # Start processing
        self.worker_thread.start()
        self.add_log_entry("🚀 실제 배치 처리를 시작합니다...", "info")

    def stop_processing(self):
        if self.worker_thread and self.worker_thread.isRunning():
            self.add_log_entry("⏹️ 처리 중단 중...", "warning")
            self.worker_thread.stop()
            self.worker_thread.wait(3000)

        self.reset_ui_state()
        self.add_log_entry("⏹️ 처리가 중단되었습니다.", "warning")

    def update_file_progress(self, filename):
        self.current_file_label.setText(filename)

    def update_progress(self, percentage):
        self.progress_bar.setValue(percentage)
        self.progress_text.setText(f"{percentage}%")

    def processing_finished(self, success, message):
        self.reset_ui_state()

        if success:
            self.status_indicator.setText("완료")
            self.status_indicator.setObjectName("status-success")
            self.add_log_entry(f"✅ {message}", "success")
        else:
            self.status_indicator.setText("오류")
            self.status_indicator.setObjectName("status-error")
            self.add_log_entry(f"❌ {message}", "error")

        self.status_indicator.setStyleSheet(self.styleSheet())
        self.current_file_label.setText("")

    def reset_ui_state(self):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_indicator.setText("준비")
        self.status_indicator.setObjectName("status-ready")
        self.status_indicator.setStyleSheet(self.styleSheet())
        self.progress_bar.setValue(0)
        self.progress_text.setText("0%")

    def add_log_entry(self, message, level="info"):
        timestamp = datetime.now().strftime("[%H:%M]")

        # Color mapping for different log levels
        color_map = {
            "info": "#1565c0",
            "success": "#2e7d32",
            "error": "#c62828",
            "warning": "#ef6c00"
        }

        color = color_map.get(level, "#1565c0")

        # Format log entry with HTML for styling
        log_entry = f'<span style="color: #666; font-weight: bold; margin-right: 8px;">{timestamp}</span>'
        log_entry += f'<span style="color: {color};">{message}</span><br>'

        # Append to log
        self.log_text.insertHtml(log_entry)

        # Auto-scroll to bottom
        cursor = self.log_text.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.log_text.setTextCursor(cursor)

    def clear_log(self):
        self.log_text.clear()
        self.add_log_entry("🚀 실제 경로 최적화 기능이 활성화되었습니다!", "success")
        self.add_log_entry("입력 폴더와 출력 폴더를 선택한 후 배치 처리를 시작하세요.", "info")

def main():
    try:
        app = QApplication(sys.argv)

        # Set application properties
        app.setApplicationName("CARRY Route Optimizer")
        app.setApplicationVersion("1.0.0")

        # Create and show main window
        window = MainWindow()
        window.show()

        print("🚀 실제 경로 최적화 기능이 활성화된 GUI가 열렸습니다!")
        sys.exit(app.exec())

    except Exception as e:
        print(f"GUI 실행 오류: {e}")
        import traceback
        traceback.print_exc()
        input("Enter를 눌러서 종료하세요...")

if __name__ == '__main__':
    main()