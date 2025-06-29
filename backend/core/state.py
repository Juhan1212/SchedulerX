class AppState:
    """
    애플리케이션 전역 상태를 관리하는 클래스.
    """
    def __init__(self):
        self.shared_tickers = set()

# 싱글톤 인스턴스 생성
state = AppState()
