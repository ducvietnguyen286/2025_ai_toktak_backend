from concurrent.futures import ProcessPoolExecutor, as_completed
import json
import logging
import os
import signal
import sys
import traceback
from dotenv import load_dotenv
from flask import Flask
import requests
import asyncio
from playwright.async_api import async_playwright, Playwright
from bs4 import BeautifulSoup
from app.lib.header import generate_desktop_user_agent
from app.lib.logger import logger
import threading
from app.scraper.pages.coupang.parser import Parser as CoupangParser
from werkzeug.exceptions import default_exceptions
from app.errors.handler import api_error_handler
from app.extensions import redis_client, db
from app.config import configs as config
import random

load_dotenv(override=False)

stop_event = threading.Event()


def signal_handler(sig, frame):
    print("Received shutdown signal. Stopping worker...")
    stop_event.set()


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def __config_logging(app):
    app.logger.setLevel(logging.DEBUG)
    app.logger.info("Start Playwright Consumer...")


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


async def create_browser_instance():
    """Tạo một instance của trình duyệt với các cấu hình nâng cao"""
    p = await async_playwright().start()

    # Cấu hình browser
    browser = await p.chromium.launch(
        headless=False,  # Set True trong production
        args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-accelerated-2d-canvas",
            "--disable-gpu",
            "--disable-features=site-per-process",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-extensions",
            "--disable-popup-blocking",
            "--disable-notifications",
            "--disable-infobars",
            "--enable-touch-events",
            "--touch-events=enabled",
            "--disable-http2",  # Tắt HTTP/2 để tránh lỗi protocol
            "--disable-blink-features=AutomationControlled",  # Ẩn dấu vết automation
            "--ignore-certificate-errors",  # Bỏ qua lỗi chứng chỉ
            "--window-size=412,915",  # Kích thước cửa sổ giống mobile
        ],
    )

    # Cấu hình thiết bị Android
    device = {
        "user_agent": "Mozilla/5.0 (Linux; Android 13; SM-S908B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36",
        "viewport": {"width": 412, "height": 915},
        "device_scale_factor": 3.5,
        "is_mobile": True,
        "has_touch": True,
        "default_browser_type": "chromium",
    }

    # Tạo context với các cấu hình nâng cao
    context = await browser.new_context(
        user_agent=device["user_agent"],
        viewport=device["viewport"],
        device_scale_factor=device["device_scale_factor"],
        is_mobile=device["is_mobile"],
        has_touch=device["has_touch"],
        locale="ko-KR",
        timezone_id="Asia/Seoul",
        geolocation={
            "latitude": 37.5665,
            "longitude": 126.9780,
            "accuracy": 100,
        },  # Seoul coordinates
        permissions=["geolocation"],
        proxy=(
            {
                "server": os.environ.get("PROXY_SERVER", ""),
                "username": os.environ.get("PROXY_USERNAME", ""),
                "password": os.environ.get("PROXY_PASSWORD", ""),
            }
            if os.environ.get("PROXY_SERVER")
            else None
        ),
        extra_http_headers={
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Sec-Ch-Ua": '"Not.A/Brand";v="8", "Chromium";v="112"',
            "Sec-Ch-Ua-Mobile": "?1",
            "Sec-Ch-Ua-Platform": '"Android"',
            "Sec-Ch-Ua-Platform-Version": "13.0.0",
            "Sec-Ch-Ua-Model": "SM-S908B",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            "Pragma": "no-cache",
        },
    )

    # Thêm các script để ngụy trang automation
    await context.add_init_script(
        """
        // Ẩn dấu vết automation
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        Object.defineProperty(navigator, 'languages', { get: () => ['ko-KR', 'ko', 'en-US', 'en'] });
        
        // Giả lập WebGL
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            if (parameter === 37445) return 'Google Inc. (ARM)';
            if (parameter === 37446) return 'ANGLE (ARM, Mali-G78 MP14, OpenGL ES 3.2)';
            return getParameter.apply(this, [parameter]);
        };
        
        // Giả lập thông tin phần cứng
        Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
        Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });
        Object.defineProperty(screen, 'colorDepth', { get: () => 32 });
        
        // Giả lập thông tin thiết bị di động
        Object.defineProperty(navigator, 'platform', { get: () => 'Linux armv8l' });
        Object.defineProperty(navigator, 'maxTouchPoints', { get: () => 5 });
        
        // Giả lập cảm biến
        Object.defineProperty(window, 'DeviceOrientationEvent', {
            get: () => function(){ return true; }
        });
        Object.defineProperty(window, 'DeviceMotionEvent', {
            get: () => function(){ return true; }
        });
        
        // Giả lập permissions
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({state: Notification.permission}) :
                originalQuery(parameters)
        );

        // Giả lập battery
        Object.defineProperty(navigator, 'getBattery', {
            get: () => () => Promise.resolve({
                charging: true,
                chargingTime: 0,
                dischargingTime: Infinity,
                level: 0.89
            })
        });
        
        // Giả lập network
        Object.defineProperty(navigator, 'connection', {
            get: () => ({
                type: '4g',
                downlinkMax: 10,
                effectiveType: '4g',
                rtt: 50,
                saveData: false
            })
        });

        // Ẩn automation flags
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
    """
    )

    return p, browser, context


async def process_task(context, task):
    try:
        logger.info("[Open Page]")
        page = await context.new_page()

        try:
            url = task["url"]
            req_id = task["req_id"]

            # Load cookies nếu có
            await load_cookies(page)

            # Thêm random delay trước khi truy cập
            await asyncio.sleep(random.uniform(1, 3))

            logger.info(f"[Open URL] {url}")

            # Cấu hình timeout và waitUntil
            await page.goto(
                url,
                wait_until="domcontentloaded",  # Thay đổi từ networkidle sang domcontentloaded
                timeout=30000,  # Tăng timeout lên 30 giây
            )

            # Thêm delay ngẫu nhiên sau khi load trang
            await asyncio.sleep(random.uniform(2, 4))

            # Scroll với delay ngẫu nhiên
            await page.evaluate("window.scrollBy(0, 700)")
            logger.info("[Scroll Down 1]")
            await asyncio.sleep(random.uniform(1, 2))

            await page.evaluate("window.scrollBy(700, 1600)")
            logger.info("[Scroll Down 2]")
            await asyncio.sleep(random.uniform(1, 2))

            # Đợi content load xong với timeout dài hơn
            try:
                await page.wait_for_selector(
                    "script[type='application/ld+json']", timeout=20000
                )
                logger.info("[Wait Done]")
            except Exception as e:
                logger.warning(f"Timeout waiting for ld+json script: {str(e)}")

            # Debug
            await page.screenshot(path="debug1.png")
            with open("demo1.html", "w", encoding="utf-8") as f:
                f.write(await page.content())

            # Lưu cookies
            await save_cookies(page)

            # Parse content
            html = BeautifulSoup(await page.content(), "html.parser")
            parser = CoupangParser(html, url)
            data = parser.parse(url)

            redis_client.set(f"toktak:result_coupang:{req_id}", json.dumps(data))

        except Exception as e:
            traceback.print_exc()
            logger.error(f"Error in process_task: {str(e)}")
            print("Error in process_task:", e)
        finally:
            await page.close()
            return True

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        print("Error: ", e)
        return False


async def load_cookies(page):
    COOKIE_FOLDER = os.path.join(os.getcwd(), "app/scraper/pages/coupang")
    try:
        cookie_file = os.path.join(COOKIE_FOLDER, "cookies.json")
        if os.path.exists(cookie_file):
            with open(cookie_file, "r", encoding="utf-8") as f:
                cookies = json.load(f)
                await page.context.add_cookies(cookies)
    except Exception as e:
        logger.info(f"Không load được cookie hoặc file không tồn tại: {str(e)}")


async def save_cookies(page):
    COOKIE_FOLDER = os.path.join(os.getcwd(), "app/scraper/pages/coupang")

    if not os.path.exists(COOKIE_FOLDER):
        os.makedirs(COOKIE_FOLDER)

    cookies = await page.context.cookies()
    if cookies:
        with open(
            os.path.join(COOKIE_FOLDER, "cookies.json"), "w", encoding="utf-8"
        ) as f:
            json.dump(cookies, f, ensure_ascii=False, indent=4)


async def worker_instance():
    """
    Mỗi worker có một instance của trình duyệt.
    Khi có task, worker mở một tab mới, xử lý xong đóng tab đó.
    """
    app = create_app()
    with app.app_context():
        playwright, browser, context = await create_browser_instance()

        try:
            # Mở trang cơ sở
            page = await context.new_page()
            await page.goto("https://m.coupang.com/")

            print("Worker started (PID:", os.getpid(), ")")

            while not stop_event.is_set():
                try:
                    task_item = redis_client.blpop(
                        "toktak:crawl_coupang_queue", timeout=10
                    )
                    if task_item:
                        _, task_json = task_item
                        task = json.loads(task_json)

                        await process_task(context, task)

                        # Commit DB changes
                        db.session.commit()
                    else:
                        await asyncio.sleep(1)

                except Exception as e:
                    logger.error(f"Error in worker_instance loop: {str(e)}")
                    print("Error in worker_instance loop:", e)
                    db.session.rollback()
                finally:
                    # Cleanup session
                    if db.session.is_active:
                        db.session.rollback()
                    db.session.close()
                    db.session.remove()

        finally:
            await context.close()
            await browser.close()
            await playwright.stop()
            print("Worker stopped (PID:", os.getpid(), ")")
            return True


async def run_worker():
    """Hàm wrapper để chạy worker instance"""
    return await worker_instance()


def worker_wrapper():
    """Hàm wrapper để chạy worker trong process pool"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(run_worker())
    loop.close()
    return result


def start_playwright_consumer():
    workers = 3
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(worker_wrapper) for _ in range(workers)]
        for future in as_completed(futures):
            try:
                result = future.result()
                print("Worker kết thúc với kết quả:", result)
            except Exception as exc:
                logger.error(f"Worker generated an exception: {exc}")
                print("Worker exception:", exc)


if __name__ == "__main__":
    try:
        start_playwright_consumer()
    except Exception as e:
        logger.error(f"Main error: {str(e)}")
        sys.exit(1)
