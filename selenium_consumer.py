from concurrent.futures import ProcessPoolExecutor, as_completed
import glob
import json
import os
import signal
import sys
import time
from dotenv import load_dotenv
import requests

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
from app.scraper.pages.aliexpress.parser import Parser as AliExpressParser

from werkzeug.exceptions import default_exceptions
from app.errors.handler import api_error_handler
from app.extensions import redis_client, db, db_mongo
from app.config import configs as config

stop_event = threading.Event()


def clear_profile_lock(profile_dir):
    """
    Xóa các tệp khóa trong thư mục profile.
    :param profile_dir: Đường dẫn đến thư mục profile.
    """
    if not os.path.exists(profile_dir):
        print(f"Thư mục {profile_dir} không tồn tại.")
        return

    for lock_file in glob.glob(os.path.join(profile_dir, "*lock*")):
        try:
            os.remove(lock_file)
            print(f"Đã xóa tệp khóa: {lock_file}")
        except PermissionError:
            print(f"Không đủ quyền để xóa {lock_file}.")
        except OSError as e:
            print(f"Không thể xóa {lock_file}: {e}")
        except Exception as e:
            print(f"Lỗi không mong đợi khi xóa {lock_file}: {e}")

    # Kiểm tra lại thư mục profile
    remaining = glob.glob(os.path.join(profile_dir, "*lock*"))
    if remaining:
        print("Vẫn còn file khóa:", remaining)
    else:
        print("Đã xóa hết các file khóa trong", profile_dir)


def signal_handler(sig, frame):
    print("Received shutdown signal. Stopping worker...")
    stop_event.set()


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


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


def create_driver_instance():
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

    # if no_gui or config_name == "production":
    # chrome_options.add_argument("--headless=new")
    # chrome_options.add_argument("--disable-gpu")

    if proxy:
        chrome_options.add_argument("--proxy-server={}".format(proxy))

    user_agent = generate_desktop_user_agent()
    headers = {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    }
    for header, value in headers.items():
        chrome_options.add_argument(f"--{header.lower()}={value}")

    SELENIUM_URL = os.environ.get("SELENIUM_URL", "http://localhost:4567/wd/hub")

    driver = webdriver.Remote(command_executor=SELENIUM_URL, options=chrome_options)
    return driver


def worker_instance():
    """
    Mỗi worker có một instance của trình duyệt.
    Khi có task, worker mở một tab mới, xử lý xong đóng tab đó và quay về tab cơ sở.
    """
    app = create_app()
    with app.app_context():
        browser = create_driver_instance()
        # Mở trang cơ sở để làm tab gốc (base tab)
        browser.get("https://ko.aliexpress.com/")
        base_tab = browser.current_window_handle

        print("Worker started (PID:", os.getpid(), ")")

        while not stop_event.is_set():
            try:
                task_item = redis_client.blpop("toktak:crawl_ali_queue", timeout=10)
                if task_item:
                    _, task_json = task_item
                    task = json.loads(task_json)

                    # Mở tab mới để xử lý task
                    browser.execute_script("window.open('about:blank', '_blank');")
                    new_tab_handle = browser.window_handles[-1]
                    browser.switch_to.window(new_tab_handle)
                    process_task_on_tab(browser, task)

                    logger.info("[Close Tab]")
                    browser.close()
                    time.sleep(1)

                    # Quay lại tab cơ sở
                    browser.switch_to.window(base_tab)
                else:
                    time.sleep(1)
            except Exception as e:
                logger.error(f"Error in worker_instance loop: {str(e)}")
                print("Error in worker_instance loop:", e)

        print("Worker stopped (PID:", os.getpid(), ")")
        browser.quit()
        return True


def process_task_on_tab(browser, task):
    try:
        logger.info("[Open Tab]")
        try:
            load_cookies(browser)
            url = task["url"]
            # wait_id = task["wait_id"]
            # wait_class = task["wait_class"]
            # wait_script = task["wait_script"]
            req_id = task["req_id"]
            # page = task["page"]

            time.sleep(1)

            browser.get(url)

            logger.info(f"[Open URL] {url}")
            try:
                iframe_tag = browser.find_elements(
                    By.XPATH,
                    "//iframe[contains(@src, 'https://acs.aliexpress.com:443//h5/mtop.aliexpress.pdp.pc.query/1.0/_____tmd_____/punish')]",
                )
                finded_script = browser.find_elements(
                    By.XPATH, "//script[@type='application/ld+json']"
                )
                print("iframe_tag", iframe_tag)
                print("finded_script", finded_script)
                if iframe_tag and not finded_script:
                    print(
                        "Found J_MIDDLEWARE_FRAME_WIDGET and script with type application/ld+json"
                    )

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

            time.sleep(1)

            browser.execute_script("window.scrollBy(0, 700);")
            logger.info("[Scroll Down 1]")
            time.sleep(1)

            browser.execute_script("window.scrollBy(700, 1600);")
            logger.info("[Scroll Down 2]")

            file_html = open("demo1.html", "w", encoding="utf-8")
            file_html.write(browser.page_source)
            file_html.close()

            # save_cookies(browser)

            WebDriverWait(browser, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//script[@type='application/ld+json']")
                )
            )
            # logger.info("[Wait for script tag with type application/ld+json]")

            # if wait_id != "":
            #     WebDriverWait(browser, 10).until(
            #         EC.presence_of_element_located((By.ID, wait_id))
            #     )
            # if wait_class != "":
            #     WebDriverWait(browser, 10).until(
            #         EC.presence_of_element_located((By.CLASS_NAME, wait_class))
            #     )

            logger.info("[Wait Done]")

            # file_html = open("demo2.html", "w", encoding="utf-8")
            # file_html.write(browser.page_source)
            # file_html.close()

            save_cookies(browser)

            html = BeautifulSoup(browser.page_source, "html.parser")

            parser = AliExpressParser(html)
            data = parser.parse(url)

            redis_client.set(f"toktak:result-ali:{req_id}", json.dumps(data))
        except Exception as e:
            logger.error(f"Error in process_task_on_tab: {str(e)}")
            print("Error in process_task_on_tab:", e)
        finally:
            return True
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        print("Error: ", e)
        return False


def load_cookies(browser):
    COOKIE_FOLDER = os.path.join(os.getcwd(), "app/scraper/pages/aliexpress")
    try:
        cookie_file = os.path.join(COOKIE_FOLDER, "cookies.json")
        if os.path.exists(cookie_file):
            cookies = json.load(open(cookie_file, "r", encoding="utf-8"))
            for cookie in cookies:
                browser.add_cookie(cookie)
    except Exception as e:
        logger.info("Không load được cookie hoặc file không tồn tại: " + str(e))


def save_cookies(browser):
    cookies = browser.execute_script("return document.cookie")

    cookie_dict = {}
    for cookie in cookies.split("; "):
        key, value = cookie.split("=", 1)
        cookie_dict[key] = value
    print("Parsed Cookies:", cookie_dict)

    COOKIE_FOLDER = os.path.join(os.getcwd(), "app/scraper/pages/aliexpress")
    formatted_cookies = []
    current_cookies = []
    cookie_file = os.path.join(COOKIE_FOLDER, "cookies.json")
    if os.path.exists(cookie_file):
        with open(cookie_file, "r", encoding="utf-8") as file:
            current_cookies = json.load(file)

    for cookie in current_cookies:
        new_value = cookie_dict.get(cookie.get("name"))
        if new_value:
            cookie["value"] = new_value
            formatted_cookies.append(cookie)

    if not os.path.exists(COOKIE_FOLDER):
        os.makedirs(COOKIE_FOLDER)

    if len(formatted_cookies) == 0:
        return

    with open(
        os.path.join(COOKIE_FOLDER, "cookies.json"), "w", encoding="utf-8"
    ) as file:
        json.dump(formatted_cookies, file, ensure_ascii=False, indent=4)


def start_selenium_consumer():
    workers = 3
    with ProcessPoolExecutor(max_workers=workers) as executor:
        # Submit worker_instance trong mỗi tiến trình
        futures = [executor.submit(worker_instance) for _ in range(workers)]
        for future in as_completed(futures):
            try:
                result = future.result()
                print("Worker kết thúc với kết quả:", result)
            except Exception as exc:
                logger.error(f"Worker generated an exception: {exc}")
                print("Worker exception:", exc)


if __name__ == "__main__":
    try:
        start_selenium_consumer()
    except Exception as e:
        logger.error(f"Main error: {str(e)}")
        sys.exit(1)
