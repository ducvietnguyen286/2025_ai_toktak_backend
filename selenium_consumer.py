import json
import os
import time
from dotenv import load_dotenv

load_dotenv(override=False)

import logging
from flask import Flask

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from app.lib.header import generate_desktop_user_agent
from app.lib.logger import logger
import threading
from app.extensions import redis_client
from app.scraper.pages.aliexpress.parser import Parser as AliExpressParser

from werkzeug.exceptions import default_exceptions
from app.errors.handler import api_error_handler
from app.extensions import redis_client, db, db_mongo
from app.config import configs as config


def __config_logging(app):
    app.logger.setLevel(logging.DEBUG)
    app.logger.info("Start Selenium Consumer...")


def __init_app(app):
    db.init_app(app)
    redis_client.init_app(app)
    db_mongo.init_app(app)


def __config_error_handlers(app):
    for exp in default_exceptions:
        app.register_error_handler(exp, api_error_handler)
    app.register_error_handler(Exception, api_error_handler)


def create_app():
    config_name = os.environ.get("FLASK_CONFIG") or "develop"
    config_app = config[config_name]
    app = Flask(__name__)
    app.config.from_object(config_app)
    __init_app(app)
    __config_logging(app)
    __config_error_handlers(app)
    return app


def start_selenium_consumer():
    create_app()

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

    no_gui = os.environ.get("SELENIUM_NO_GUI", "false") == "true"
    proxy = os.environ.get("SELENIUM_PROXY", None)

    if no_gui or config_name == "production":
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")

    if proxy:
        chrome_options.add_argument("--proxy-server={}".format(proxy))

    user_agent = generate_desktop_user_agent()
    headers = {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    }

    for header, value in headers.items():
        header = header.lower()
        chrome_options.add_argument(f"--{header}={value}")

    driver_version = None

    if config_name == "production":
        chrome_options.binary_location = "/usr/bin/google-chrome"
        driver_version = "123.0.6312.58"

    browser = webdriver.Chrome(
        service=Service(ChromeDriverManager(driver_version=driver_version).install()),
        options=chrome_options,
    )

    browser.get("https://ko.aliexpress.com/")

    def process_url(task):
        try:
            logger.info("[Open Tab]")
            try:
                COOKIE_FOLDER = os.path.join(
                    os.getcwd(), "app/scraper/pages/aliexpress"
                )

                cookies = json.load(open(os.path.join(COOKIE_FOLDER, "cookies.json")))
                for cookie in cookies:
                    browser.add_cookie(cookie)

                url = task["url"]
                wait_id = task["wait_id"]
                wait_class = task["wait_class"]
                req_id = task["req_id"]
                page = task["page"]

                browser.execute_script("window.open('');")
                browser.switch_to.window(browser.window_handles[-1])

                time.sleep(1)

                browser.get(url)

                try:
                    elements = browser.find_elements(
                        By.CSS_SELECTOR, "div.J_MIDDLEWARE_FRAME_WIDGET"
                    )
                    finded_id = browser.find_element(By.ID, wait_id)
                    finded_class = browser.find_element(By.CLASS_NAME, wait_class)
                    if elements and not finded_id and not finded_class:
                        print("Found J_MIDDLEWARE_FRAME_WIDGET")

                        outer_frame = browser.find_element(
                            By.CSS_SELECTOR, "div.J_MIDDLEWARE_FRAME_WIDGET iframe"
                        )
                        browser.switch_to.frame(outer_frame)

                        print("Switch To Outer Frame")

                        middle_frame = browser.find_element(By.XPATH, "//iframe[1]")
                        browser.switch_to.frame(middle_frame)

                        print("Switch To Middle Frame")

                        inner_frame = browser.find_element(By.XPATH, "//iframe[1]")
                        browser.switch_to.frame(inner_frame)

                        print("Switch To Captcha Frame")

                        # file_html = open("demo.html", "w", encoding="utf-8")
                        # file_html.write(browser.page_source)
                        # file_html.close()

                        checkbox = WebDriverWait(browser, 10).until(
                            EC.element_to_be_clickable((By.ID, "recaptcha-anchor"))
                        )
                        checkbox.click()

                        browser.switch_to.default_content()
                except Exception as e:
                    print("Error: ", str(e))

                # file_html = open("demo1.html", "w", encoding="utf-8")
                # file_html.write(browser.page_source)
                # file_html.close()

                time.sleep(1)

                browser.execute_script("window.scrollBy(0, 2000);")

                if wait_id != "":
                    WebDriverWait(browser, 10).until(
                        EC.presence_of_element_located((By.ID, wait_id))
                    )
                if wait_class != "":
                    WebDriverWait(browser, 10).until(
                        EC.presence_of_element_located((By.CLASS_NAME, wait_class))
                    )

                # file_html = open("demo2.html", "w", encoding="utf-8")
                # file_html.write(browser.page_source)
                # file_html.close()

                browser_cookie = browser.get_cookies()
                formatted_cookies = []
                for cookie in browser_cookie:
                    formatted_cookie = {
                        "name": cookie.get("name"),
                        "value": cookie.get("value"),
                        "domain": cookie.get("domain"),
                        "path": cookie.get("path", "/"),
                        "expires": cookie.get("expiry", -1),
                        "httpOnly": cookie.get("httpOnly", False),
                        "secure": cookie.get("secure", False),
                    }
                    formatted_cookies.append(formatted_cookie)
                with open(
                    os.path.join(COOKIE_FOLDER, "cookies.json"), "w", encoding="utf-8"
                ) as file:
                    json.dump(formatted_cookies, file, ensure_ascii=False, indent=4)

                html = BeautifulSoup(browser.page_source, "html.parser")

                parser = None
                if page == "ali":
                    parser = AliExpressParser(html)
                data = parser.parse(url)

                redis_client.set(f"toktak:result-ali:{req_id}", json.dumps(data))
            finally:
                logger.info("[Close Tab]")
                browser.close()
                browser.switch_to.window(browser.window_handles[0])
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            print("Error: ", e)
            return {}

    def worker():
        """
        Worker liên tục chờ các task từ Redis queue 'toktak:crawl_ali_queue'
        và xử lý từng task khi có.
        """
        print("Start worker NOW...")
        while True:
            task_item = redis_client.blpop("toktak:crawl_ali_queue", timeout=10)
            if task_item:
                _, task_json = task_item
                task = json.loads(task_json)
                process_url(task)
            else:
                time.sleep(1)

    try:
        worker_thread = threading.Thread(target=worker)
        worker_thread.start()
    except Exception as e:
        logger.error(f"Error: {str(e)}")


if __name__ == "__main__":
    start_selenium_consumer()
