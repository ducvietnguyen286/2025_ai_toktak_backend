import multiprocessing
from app.scraper.pages.coupang import CoupangScraper
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
import os
from dotenv import load_dotenv
from flask import Flask
from app.config import configs as config
from app.extensions import redis_client

# Load environment variables
load_dotenv(override=False)


def init_app():
    config_name = os.environ.get("FLASK_CONFIG") or "develop"
    config_app = config[config_name]
    app = Flask(__name__)
    app.config.from_object(config_app)
    redis_client.init_app(app)
    return app


def run_single_scraper(url):
    # Initialize app for each process
    app = init_app()
    with app.app_context():
        scraper = CoupangScraper({"url": url})
        start_time = time.time()
        result = scraper.run_puppeteer()
        end_time = time.time()
        return {
            "url": url,
            "time_taken": end_time - start_time,
            "success": result is not None,
            "result": result,
        }


def main():
    # Initialize main app

    # List of test URLs - replace these with actual Coupang URLs
    test_urls = [
        "https://www.coupang.com/vp/products/7925672229?itemId=21787939168&searchId=e365d0cc3b884526be8f800224a4d058&sourceType=brandstore_sdp_atf-all_products&storeId=20491&subSourceType=brandstore_sdp_atf-all_products&vendorId=A00732340&vendorItemId=88836627901",
        # "https://www.coupang.com/vp/products/7104288755?itemId=17741889686&searchId=feed-0318f6df383f4f7580e65bccb788c013-view_together_ads-P7925672229&vendorItemId=84906507895&sourceType=SDP_ADS&clickEventId=34dd11e0-570d-11f0-8380-1ec548b2d7a5",
        # "https://www.coupang.com/vp/products/8057441865?itemId=22620178527&searchId=feed-d1e11615c2fc4b578b13ca31dd085c07-view_together_ads-P7104288755&vendorItemId=89661730245&sourceType=SDP_ADS&clickEventId=b6349d00-5710-11f0-b8a9-0513ff48a5c1",
        # "https://www.coupang.com/vp/products/8550240164?itemId=24758867850&searchId=feed-74d512896bb94da48290f27f4822a1e5-view_together_ads-P8057441865&vendorItemId=91805798144&sourceType=SDP_ADS&clickEventId=b9270200-5710-11f0-92c3-4b92300987d7",
        # "https://www.coupang.com/vp/products/7542258674?vendorItemId=86931998067&sourceType=sdp_bottom_promotion&searchId=feed-585f5282d7114cbcb9b7907844f7339b-gw_promotion",
        # "https://www.coupang.com/vp/products/6981367244?itemId=11071527085&searchId=feed-cdb5dcfee75c46a8b4729ad65563f956-view_together_ads-P7542258674&vendorItemId=86283351444&sourceType=SDP_ADS&clickEventId=bf3944a0-5710-11f0-9a5c-5e74a1d144d0",
        # "https://www.coupang.com/vp/products/7613376298?itemId=20168819569&searchId=feed-02b6d0d6bf184bafbedc144aa4ca21b1-view_together_ads-P6981367244&vendorItemId=87044541529&sourceType=SDP_ADS&clickEventId=c2412d70-5710-11f0-8b7c-a92a2f2a0a74",
        # "https://www.coupang.com/vp/products/8222114080?itemId=23636681493&searchId=feed-ae0c4946cb6044a198c4c3a6d2657ba8-view_together_ads-P7613376298&vendorItemId=90788489175&sourceType=SDP_ADS&clickEventId=c9e867f0-5710-11f0-9cff-cc6fbb5b8385",
        # "https://www.coupang.com/vp/products/7892895563?vendorItemId=88664629224&sourceType=sdp_bottom_promotion&searchId=feed-d0eec386e06c4ff394297ac695655a3e-gw_promotion",
        # "https://www.coupang.com/vp/products/8533069119?vendorItemId=91828787337&sourceType=sdp_bottom_promotion&searchId=feed-3b38bb54af6d4be099e7c1e18448f4e4-gw_promotion",
    ]

    print(f"Starting {len(test_urls)} parallel scraping processes...")
    start_total = time.time()

    # Using ProcessPoolExecutor to manage the process pool
    with ProcessPoolExecutor(max_workers=10) as executor:
        # Submit all tasks
        future_to_url = {
            executor.submit(run_single_scraper, url): url for url in test_urls
        }

        # Process results as they complete
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                data = future.result()
                print(f"Time taken: {data['time_taken']:.2f} seconds")
                print(f"Success: {data['success']}")
                if data["success"]:
                    print(f"Data received: {bool(data['result'])}")
            except Exception as e:
                print(f"\nError processing {url}: {str(e)}")

    end_total = time.time()
    print(f"\nTotal time taken: {end_total - start_total:.2f} seconds")


if __name__ == "__main__":
    # Required for Windows multiprocessing
    multiprocessing.freeze_support()
    main()
