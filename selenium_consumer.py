import base64
from concurrent.futures import ProcessPoolExecutor, as_completed
import glob
import json
import os
import signal
import sys
import time
import traceback
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
from app.lib.header import generate_desktop_user_agent_chrome
from app.lib.logger import logger
import threading
from app.scraper.pages.coupang.parser import Parser as CoupangParser

from werkzeug.exceptions import default_exceptions
from app.errors.handler import api_error_handler
from app.extensions import redis_client, db
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

    proxy = os.environ.get("SELENIUM_PROXY", None)

    if proxy:
        chrome_options.add_argument("--proxy-server={}".format(proxy))

    user_agent = generate_desktop_user_agent_chrome()
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "User-Agent": user_agent,
    }
    for header, value in headers.items():
        chrome_options.add_argument(f"--{header.lower()}={value}")

    # Sử dụng ChromeDriver local
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
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
        browser.get("https://www.coupang.com/")
        base_tab = browser.current_window_handle

        print("Worker started (PID:", os.getpid(), ")")

        while not stop_event.is_set():
            try:
                task_item = redis_client.blpop("toktak:crawl_coupang_queue", timeout=10)
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

                    # Commit any DB changes made during task processing
                    db.session.commit()
                else:
                    time.sleep(1)
            except Exception as e:
                logger.error(f"Error in worker_instance loop: {str(e)}")
                print("Error in worker_instance loop:", e)
                db.session.rollback()
            finally:
                # CRITICAL: Force cleanup session to prevent connection leaks
                try:
                    if db.session.is_active:
                        db.session.rollback()
                    db.session.close()
                    db.session.remove()
                except:
                    pass

        print("Worker stopped (PID:", os.getpid(), ")")
        browser.quit()
        return True


def process_task_on_tab(browser, task):
    try:
        logger.info("[Open Tab]")
        try:
            # load_cookies(browser)
            url = task["url"]
            req_id = task["req_id"]

            time.sleep(1)
            browser.get(url)
            logger.info(f"[Open URL] {url}")

            WebDriverWait(browser, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//script[@type='application/ld+json']")
                )
            )

            browser.execute_script("window.scrollBy(0, 700);")
            logger.info("[Scroll Down 1]")
            time.sleep(1)

            browser.execute_script("window.scrollBy(700, 1600);")
            logger.info("[Scroll Down 2]")

            logger.info("[Wait Done]")

            # save_cookies(browser)

            html = BeautifulSoup(browser.page_source, "html.parser")

            parser = CoupangParser(html, url)
            data = parser.parse(url)

            redis_client.set(f"toktak:result_coupang:{req_id}", json.dumps(data))
        except Exception as e:
            traceback.print_exc()
            print("Error in process_task_on_tab:", e)
        finally:
            return True
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        print("Error: ", e)
        return False


def load_cookies(browser):
    COOKIE_FOLDER = os.path.join(os.getcwd(), "app/scraper/pages/coupang")
    try:
        cookie_file = os.path.join(COOKIE_FOLDER, "cookies.json")
        if os.path.exists(cookie_file):
            cookies = json.load(open(cookie_file, "r", encoding="utf-8"))
            for cookie in cookies:
                browser.add_cookie(cookie)
    except Exception as e:
        logger.info("Không load được cookie hoặc file không tồn tại: " + str(e))


def save_cookies(browser):
    cookies = browser.get_cookies()
    COOKIE_FOLDER = os.path.join(os.getcwd(), "app/scraper/pages/coupang")

    if not os.path.exists(COOKIE_FOLDER):
        os.makedirs(COOKIE_FOLDER)

    if len(cookies) == 0:
        return

    with open(
        os.path.join(COOKIE_FOLDER, "cookies.json"), "w", encoding="utf-8"
    ) as file:
        json.dump(cookies, file, ensure_ascii=False, indent=4)


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
