#!/usr/bin/env python3
"""
macOS용 경로 최적화 GUI 애플리케이션
더블클릭으로 실행 가능한 .app 번들을 위한 GUI
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import sys
import threading
import subprocess
from pathlib import Path

class RouteOptimizerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("CARRY Route Optimizer")
        self.root.geometry("500x400")
        self.root.resizable(True, True)

        # macOS 스타일 설정
        self.setup_macos_style()

        # GUI 구성 요소 생성
        self.create_widgets()

        # 변수 초기화
        self.selected_file = None
        self.output_dir = os.path.expanduser("~/Desktop")

    def setup_macos_style(self):
        """macOS 네이티브 스타일 설정"""
        try:
            # macOS 다크모드 지원
            self.root.tk.call('tk', 'windowingsystem')
            self.root.configure(bg='#f0f0f0')
        except:
            pass

    def create_widgets(self):
        """GUI 위젯 생성"""
        # 메인 프레임
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 제목
        title_label = ttk.Label(main_frame, text="CARRY Route Optimizer",
                               font=('SF Pro Display', 18, 'bold'))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))

        # 파일 선택 섹션
        file_frame = ttk.LabelFrame(main_frame, text="Excel 파일 선택", padding="10")
        file_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        self.file_label = ttk.Label(file_frame, text="선택된 파일 없음",
                                   foreground="gray")
        self.file_label.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))

        self.browse_button = ttk.Button(file_frame, text="파일 선택",
                                       command=self.browse_file)
        self.browse_button.grid(row=0, column=1)

        # 설정 섹션
        settings_frame = ttk.LabelFrame(main_frame, text="최적화 설정", padding="10")
        settings_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        # 우선순위 설정
        ttk.Label(settings_frame, text="최적화 우선순위:").grid(row=0, column=0, sticky=tk.W)
        self.priority_var = tk.StringVar(value="TIME")
        priority_combo = ttk.Combobox(settings_frame, textvariable=self.priority_var,
                                     values=["TIME", "DISTANCE", "RECOMMEND"],
                                     state="readonly", width=15)
        priority_combo.grid(row=0, column=1, sticky=tk.W, padx=(10, 0))

        # 지도 생성 옵션
        self.map_var = tk.BooleanVar(value=False)
        map_check = ttk.Checkbutton(settings_frame, text="지도 시각화 생성",
                                   variable=self.map_var)
        map_check.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))

        # 출력 디렉토리
        output_frame = ttk.LabelFrame(main_frame, text="결과 저장 위치", padding="10")
        output_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        self.output_label = ttk.Label(output_frame, text=f"저장 위치: {self.output_dir}")
        self.output_label.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))

        output_button = ttk.Button(output_frame, text="변경",
                                  command=self.change_output_dir)
        output_button.grid(row=0, column=1)

        # 실행 버튼
        self.run_button = ttk.Button(main_frame, text="경로 최적화 실행",
                                    command=self.run_optimization,
                                    style="Accent.TButton")
        self.run_button.grid(row=4, column=0, columnspan=2, pady=20, sticky=(tk.W, tk.E))

        # 진행률 표시
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        # 상태 표시
        self.status_var = tk.StringVar(value="파일을 선택하고 실행 버튼을 클릭하세요")
        status_label = ttk.Label(main_frame, textvariable=self.status_var)
        status_label.grid(row=6, column=0, columnspan=2)

        # 그리드 가중치 설정
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        file_frame.columnconfigure(0, weight=1)
        output_frame.columnconfigure(0, weight=1)

    def browse_file(self):
        """Excel 파일 선택"""
        filetypes = [
            ('Excel files', '*.xlsx *.xls'),
            ('All files', '*.*')
        ]

        filename = filedialog.askopenfilename(
            title="Excel 파일 선택",
            filetypes=filetypes,
            initialdir=os.path.expanduser("~/Desktop")
        )

        if filename:
            self.selected_file = filename
            # 파일명만 표시 (경로가 길면 줄임)
            display_name = os.path.basename(filename)
            if len(display_name) > 40:
                display_name = display_name[:37] + "..."
            self.file_label.config(text=display_name, foreground="black")
            self.status_var.set(f"파일 선택됨: {os.path.basename(filename)}")

    def change_output_dir(self):
        """출력 디렉토리 변경"""
        directory = filedialog.askdirectory(
            title="결과 저장 위치 선택",
            initialdir=self.output_dir
        )

        if directory:
            self.output_dir = directory
            # 경로가 길면 줄임
            display_path = directory
            if len(display_path) > 50:
                display_path = "..." + display_path[-47:]
            self.output_label.config(text=f"저장 위치: {display_path}")

    def run_optimization(self):
        """최적화 실행"""
        if not self.selected_file:
            messagebox.showerror("오류", "먼저 Excel 파일을 선택해주세요.")
            return

        if not os.path.exists(self.selected_file):
            messagebox.showerror("오류", "선택한 파일이 존재하지 않습니다.")
            return

        # 버튼 비활성화 및 진행률 표시 시작
        self.run_button.config(state="disabled")
        self.progress.start(10)
        self.status_var.set("최적화 실행 중...")

        # 별도 스레드에서 최적화 실행
        threading.Thread(target=self.execute_optimization, daemon=True).start()

    def execute_optimization(self):
        """실제 최적화 실행 (별도 스레드)"""
        try:
            # 현재 스크립트의 위치를 기준으로 main.py 찾기
            if getattr(sys, 'frozen', False):
                # PyInstaller로 패키징된 경우
                script_dir = sys._MEIPASS
            else:
                # 개발 환경
                script_dir = os.path.dirname(os.path.abspath(__file__))

            main_py = os.path.join(script_dir, 'main.py')

            # 명령어 구성
            cmd = [
                sys.executable, main_py,
                '--input', self.selected_file,
                '--priority', self.priority_var.get()
            ]

            if not self.map_var.get():
                cmd.append('--no-map')

            # 출력 디렉토리 설정
            os.chdir(self.output_dir)

            # 최적화 실행
            result = subprocess.run(cmd, capture_output=True, text=True,
                                  cwd=self.output_dir)

            # UI 업데이트 (메인 스레드에서 실행)
            self.root.after(0, self.optimization_finished, result)

        except Exception as e:
            self.root.after(0, self.optimization_error, str(e))

    def optimization_finished(self, result):
        """최적화 완료 처리"""
        self.progress.stop()
        self.run_button.config(state="normal")

        if result.returncode == 0:
            # 성공
            output_file = os.path.join(self.output_dir, "optimized_route.xlsx")
            self.status_var.set("최적화 완료!")

            messagebox.showinfo("완료",
                f"경로 최적화가 완료되었습니다!\n\n"
                f"결과 파일: {output_file}\n\n"
                f"파일을 여시겠습니까?")

            # 결과 파일 열기
            if os.path.exists(output_file):
                subprocess.run(['open', output_file])

        else:
            # 실패
            error_msg = result.stderr if result.stderr else "알 수 없는 오류"
            self.status_var.set("최적화 실패")
            messagebox.showerror("오류",
                f"최적화 중 오류가 발생했습니다:\n\n{error_msg}")

    def optimization_error(self, error_msg):
        """최적화 오류 처리"""
        self.progress.stop()
        self.run_button.config(state="normal")
        self.status_var.set("오류 발생")

        messagebox.showerror("오류",
            f"최적화 실행 중 오류가 발생했습니다:\n\n{error_msg}")

def main():
    # GUI 생성 및 실행
    root = tk.Tk()

    # macOS에서 실행 중인지 확인
    if sys.platform != 'darwin':
        messagebox.showwarning("경고", "이 애플리케이션은 macOS용으로 제작되었습니다.")

    app = RouteOptimizerGUI(root)

    try:
        root.mainloop()
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    main()