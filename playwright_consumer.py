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

AUTH = "brd-customer-hl_8019b21f-zone-scraping_browser1-country-il:w2dey5l5cws2"
SBR_WS_CDP = f"wss://{AUTH}@brd.superproxy.io:9222"


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
    try:
        async with async_playwright() as playwright:
            logger.info("[Browser] Đang kết nối tới Bright Data browser...")
            # Cấu hình browser với timeout dài hơn
            browser = await playwright.chromium.connect_over_cdp(
                SBR_WS_CDP, timeout=60000  # Tăng timeout lên 60 giây
            )
            logger.info("[Browser] Kết nối thành công")
            return browser
    except Exception as e:
        logger.error(f"[Browser] Lỗi khi kết nối browser: {str(e)}")
        raise  # Re-raise để worker_instance có thể xử lý


async def process_task(browser, task):
    try:
        logger.info("[Open Page]")
        page = await browser.new_page()

        try:
            url = task["url"]
            req_id = task["req_id"]

            # Load cookies nếu có
            # await load_cookies(page)

            # Thêm random delay trước khi truy cập
            await asyncio.sleep(random.uniform(1, 3))

            logger.info(f"[Open URL] {url}")

            # Cấu hình timeout và waitUntil
            await page.goto(
                url,
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
            # await save_cookies(page)

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
        retry_count = 0
        max_retries = 3

        while retry_count < max_retries and not stop_event.is_set():
            try:
                browser = await create_browser_instance()

                try:
                    # Mở trang cơ sở
                    logger.info("[Worker] Đang mở trang cơ sở...")
                    page = await browser.new_page()
                    await page.goto("https://m.coupang.com/", timeout=30000)
                    logger.info("[Worker] Đã mở trang cơ sở thành công")

                    print("Worker started (PID:", os.getpid(), ")")

                    while not stop_event.is_set():
                        try:
                            task_item = redis_client.blpop(
                                "toktak:crawl_coupang_queue", timeout=10
                            )
                            if task_item:
                                _, task_json = task_item
                                task = json.loads(task_json)
                                logger.info(
                                    f"[Worker] Nhận được task mới: {task['req_id']}"
                                )
                                await process_task(browser, task)
                                logger.info(
                                    f"[Worker] Hoàn thành task: {task['req_id']}"
                                )

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
                    await browser.close()
                    logger.info("[Worker] Đóng browser")
                    print("Worker stopped (PID:", os.getpid(), ")")

                return True  # Thoát vòng lặp nếu mọi thứ OK

            except Exception as e:
                retry_count += 1
                logger.error(f"[Worker] Lỗi lần {retry_count}: {str(e)}")
                await asyncio.sleep(5)  # Chờ 5 giây trước khi thử lại

        if retry_count >= max_retries:
            logger.error("[Worker] Đã thử lại quá số lần cho phép, dừng worker")
        return False


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
