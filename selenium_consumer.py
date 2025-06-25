import base64
from concurrent.futures import ProcessPoolExecutor, as_completed
import glob
import json
import os
import random
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

SELENIUM_URL = "https://brd-customer-hl_8019b21f-zone-scraping_browser1:w2dey5l5cws2@brd.superproxy.io:9515"


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

    # Ẩn dấu vết Selenium và Automation
    chrome_options.add_experimental_option(
        "excludeSwitches", ["enable-automation", "enable-logging"]
    )
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")

    # Thêm các tham số stealth mode
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--disable-features=IsolateOrigins,site-per-process")
    chrome_options.add_argument("--disable-site-isolation-trials")
    chrome_options.add_argument("--disable-features=BlockCredentialedSubresources")
    chrome_options.add_argument("--disable-plugins-discovery")
    chrome_options.add_argument("--disable-single-click-autofill")
    chrome_options.add_argument("--disable-prompt-on-repost")
    chrome_options.add_argument("--no-default-browser-check")
    chrome_options.add_argument("--no-first-run")

    # Thêm các tham số để giả lập người dùng thực
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--ignore-ssl-errors")

    # Random window size để tránh detection
    widths = [360, 375, 390, 412, 414]
    heights = [640, 720, 780, 800, 850]
    width = random.choice(widths)
    height = random.choice(heights)

    # Cấu hình giả lập Android
    mobile_emulation = {
        "deviceMetrics": {
            "width": width,
            "height": height,
            "pixelRatio": 3.0,
            "touch": True,
            "mobile": True,
        },
        "userAgent": "Mozilla/5.0 (Linux; Android 13; SM-S908B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36",
    }
    chrome_options.add_experimental_option("mobileEmulation", mobile_emulation)

    # Thêm các tham số giả lập Android
    chrome_options.add_argument("--enable-touch-events")
    chrome_options.add_argument("--touch-events=enabled")
    chrome_options.add_argument("--disable-hover")

    # Cấu hình proxy với xác thực
    proxies = [
        {
            "host": "gw.dataimpulse.com",
            "port": "823",
            "username": "27222558ddfa5c9d6449__cr.il",
            "password": "69271afa03d6c430",
        },
        {
            "host": "gw.dataimpulse.com",
            "port": "823",
            "username": "27222558ddfa5c9d6449__cr.il",
            "password": "69271afa03d6c430",
        },
        {
            "host": "gw.dataimpulse.com",
            "port": "823",
            "username": "27222558ddfa5c9d6449__cr.il",
            "password": "69271afa03d6c430",
        },
    ]

    proxy = random.choice(proxies)
    manifest_json = """
    {
        "version": "1.0.0",
        "manifest_version": 2,
        "name": "Chrome Proxy",
        "permissions": [
            "proxy",
            "tabs",
            "unlimitedStorage",
            "storage",
            "webRequest",
            "webRequestBlocking"
        ],
        "background": {
            "scripts": ["background.js"]
        },
        "minimum_chrome_version":"22.0.0"
    }
    """

    background_js = """
    var config = {
        mode: "fixed_servers",
        rules: {
            singleProxy: {
                scheme: "http",
                host: "%s",
                port: parseInt(%s)
            },
            bypassList: []
        }
    };
    chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});
    function callbackFn(details) {
        return {
            authCredentials: {
                username: "%s",
                password: "%s"
            }
        };
    }
    chrome.webRequest.onAuthRequired.addListener(
        callbackFn,
        {urls: ["<all_urls>"]},
        ['blocking']
    );
    """ % (
        proxy["host"],
        proxy["port"],
        proxy["username"],
        proxy["password"],
    )

    plugin_dir = "chrome_proxy_extension"
    if not os.path.exists(plugin_dir):
        os.makedirs(plugin_dir)

    with open(f"{plugin_dir}/manifest.json", "w") as f:
        f.write(manifest_json)
    with open(f"{plugin_dir}/background.js", "w") as f:
        f.write(background_js)

    chrome_options.add_argument(f"--load-extension={os.path.abspath(plugin_dir)}")

    # Giả lập vị trí địa lý (Jerusalem, Israel)
    chrome_options.add_argument("--enable-geolocation")
    location = {"latitude": 31.7683, "longitude": 35.2137, "accuracy": 100}
    chrome_options.add_experimental_option(
        "prefs",
        {
            "profile.default_content_setting_values.geolocation": 1,
            "profile.default_content_settings.geolocation": 1,
            "profile.content_settings.exceptions.geolocation": {"*": {"setting": 1}},
            # Thêm các preferences để giả lập người dùng thực
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            "profile.default_content_setting_values.notifications": 2,
            "profile.managed_default_content_settings.images": 1,
            "profile.default_content_setting_values.cookies": 1,
            "profile.default_content_setting_values.plugins": 1,
            "profile.default_content_setting_values.popups": 1,
            "profile.default_content_setting_values.geolocation": 1,
            "profile.default_content_setting_values.auto_select_certificate": 1,
            "profile.default_content_setting_values.mixed_script": 1,
            "profile.default_content_setting_values.media_stream": 1,
            "profile.default_content_setting_values.media_stream_mic": 1,
            "profile.default_content_setting_values.media_stream_camera": 1,
            "profile.default_content_setting_values.protocol_handlers": 1,
            "profile.default_content_setting_values.midi_sysex": 1,
            "profile.default_content_setting_values.push_messaging": 1,
            "profile.default_content_setting_values.ssl_cert_decisions": 1,
            "profile.default_content_setting_values.metro_switch_to_desktop": 1,
            "profile.default_content_setting_values.protected_media_identifier": 1,
            "profile.default_content_setting_values.site_engagement": 1,
            "profile.default_content_setting_values.durable_storage": 1,
        },
    )

    # Sử dụng ChromeDriver local
    service = Service(ChromeDriverManager().install())

    # Ẩn chuỗi ChromeDriver trong capabilities
    service.creation_flags = 0x08000000  # CREATE_NO_WINDOW flag

    driver = webdriver.Chrome(service=service, options=chrome_options)

    # Xóa các thuộc tính tiết lộ automation
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {
            "source": """
            // Ẩn webdriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Giả lập ngôn ngữ
            Object.defineProperty(navigator, 'languages', {
                get: () => ['ko-KR', 'ko', 'en-US', 'en']
            });
            
            // Giả lập plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    {
                        0: {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format"},
                        description: "Portable Document Format",
                        filename: "internal-pdf-viewer",
                        length: 1,
                        name: "Chrome PDF Plugin"
                    },
                    {
                        0: {type: "application/pdf", suffixes: "pdf", description: "Portable Document Format"},
                        description: "Portable Document Format",
                        filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai",
                        length: 1,
                        name: "Chrome PDF Viewer"
                    }
                ]
            });
            
            // Ẩn automation flags
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
            
            // Giả lập WebGL
            const getParameter = WebGLRenderingContext.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) {
                    return 'Intel Inc.'
                }
                if (parameter === 37446) {
                    return 'Intel(R) Iris(TM) Graphics 6100'
                }
                return getParameter(parameter);
            };
            
            // Giả lập thông tin phần cứng
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => 8
            });
            Object.defineProperty(navigator, 'deviceMemory', {
                get: () => 8
            });
            Object.defineProperty(screen, 'colorDepth', {
                get: () => 24
            });
            
            // Giả lập hành vi touch
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({state: Notification.permission}) :
                    originalQuery(parameters)
            );
            
            // Thêm một số thuộc tính ngẫu nhiên
            const now = new Date();
            Object.defineProperty(navigator, 'getBattery', {
                get: () => () => Promise.resolve({
                    charging: true,
                    chargingTime: 0,
                    dischargingTime: Infinity,
                    level: 0.98
                })
            });
        """
        },
    )

    # Set geolocation after driver creation
    driver.execute_cdp_cmd("Emulation.setGeolocationOverride", location)

    # Thêm một số hành vi ngẫu nhiên để giống người dùng thực
    driver.execute_cdp_cmd("Network.enable", {})
    driver.execute_cdp_cmd(
        "Network.setUserAgentOverride",
        {
            "userAgent": mobile_emulation["userAgent"],
            "platform": "Android",
            "acceptLanguage": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        },
    )

    # Thêm headers tùy chỉnh
    driver.execute_cdp_cmd(
        "Network.setExtraHTTPHeaders",
        {
            "headers": {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
                "Cache-Control": "max-age=0",
                "Sec-Ch-Ua": '"Not.A/Brand";v="8", "Chromium";v="112"',
                "Sec-Ch-Ua-Mobile": "?1",
                "Sec-Ch-Ua-Platform": '"Android"',
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1",
            }
        },
    )

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
        browser.get("https://m.coupang.com/")
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
