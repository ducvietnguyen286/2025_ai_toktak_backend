import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


class ShopeeScarper:
    def __init__(self, params):
        self.url = params["url"]

    def run(self):
        return self.run_scraper()

    def create_selenium_instance(self):
        config_name = os.environ.get("FLASK_CONFIG") or "develop"
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_argument("--ignore-ssl-errors")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-site-isolation-trials")
        chrome_options.add_argument(
            "--disable-blink-features=BlockCredentialedSubresources"
        )
        chrome_options.add_argument("--enable-unsafe-swiftshader")
        chrome_options.add_argument("--window-size=1920x1080")

        # Thêm một số option bổ sung để tránh lỗi
        chrome_options.add_argument("--no-first-run")
        chrome_options.add_argument("--no-default-browser-check")
        chrome_options.add_argument("--disable-extensions")

        no_gui = os.environ.get("SELENIUM_NO_GUI", "false") == "true"
        proxy = os.environ.get("SELENIUM_PROXY", None)

        if no_gui or config_name == "production":
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--disable-gpu")

        if proxy:
            chrome_options.add_argument("--proxy-server={}".format(proxy))

        SELENIUM_URL = os.environ.get("SELENIUM_URL", "http://localhost:4567/wd/hub")

        driver = webdriver.Remote(command_executor=SELENIUM_URL, options=chrome_options)
        return driver

    def run_scraper(self):
        driver = self.create_selenium_instance()

        driver.get(self.url)

        # Chờ cho phần tử có ID là "main" xuất hiện trong tối đa 10 giây
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "main"))
            )
        except Exception as e:
            print(f"Error: {e}")
            driver.quit()
            return None

        # Lấy mã HTML của trang
        html = driver.page_source

        # Đóng trình duyệt
        driver.quit()

        return html
