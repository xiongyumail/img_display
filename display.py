import webbrowser
import threading
import requests
from web import WebApp, Paginator
from config import get_config

class ImageGalleryApp:
    def __init__(self):
        self.args = get_config()
        self.web_app = WebApp(self.args)

    def input_listener(self) -> None:
        print('Press Q to quit...')
        while True:
            if input().lower() == 'q':
                try:
                    requests.post(f'http://127.0.0.1:{self.args.port}/shutdown')
                except Exception as e:
                    self.web_app.app.logger.error(f"Shutdown failed: {str(e)}")
                finally:
                    break

    def run(self):
        if not self.args.no_browser:  # 只有在没有指定 --no_browser 时才打开浏览器
            threading.Timer(1, lambda: webbrowser.open(f'http://127.0.0.1:{self.args.port}')).start()
        input_thread = threading.Thread(target=self.input_listener, daemon=True)
        input_thread.start()
        self.web_app.app.run(host=self.args.host, port=self.args.port, debug=self.args.debug, use_reloader=False)

if __name__ == '__main__':
    app = ImageGalleryApp()
    app.run()