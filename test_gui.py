import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyQt6 테스트")
        self.setGeometry(300, 300, 400, 200)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)

        label = QLabel("PyQt6 GUI가 정상적으로 작동합니다!")
        layout.addWidget(label)

        button = QPushButton("테스트 버튼")
        button.clicked.connect(lambda: print("버튼이 클릭되었습니다!"))
        layout.addWidget(button)

def main():
    try:
        print("PyQt6 애플리케이션 시작...")
        app = QApplication(sys.argv)

        print("메인 윈도우 생성...")
        window = TestWindow()
        window.show()

        print("GUI 창이 열렸습니다!")
        return app.exec()

    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()
        input("Enter를 눌러 종료...")
        return 1

if __name__ == '__main__':
    exit_code = main()
    print(f"애플리케이션 종료 (코드: {exit_code})")