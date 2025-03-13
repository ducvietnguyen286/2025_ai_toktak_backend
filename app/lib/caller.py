import hmac
import hashlib
import json
import os
import requests
from app.lib.logger import logger
from app.services.request_log import RequestLogService
from time import gmtime, strftime


def generate_coupang_hmac(method, url):
    ACCESS_KEY = os.environ.get("COUPANG_ACCESS_KEY")
    SECRET_KEY = os.environ.get("COUPANG_SECRET_KEY")

    path, *query = url.split("?")
    datetime_gmt = (
        strftime("%y%m%d", gmtime()) + "T" + strftime("%H%M%S", gmtime()) + "Z"
    )
    message = datetime_gmt + method + path + (query[0] if query else "")

    signature = hmac.new(
        bytes(SECRET_KEY, "utf-8"), message.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    return (
        "CEA algorithm=HmacSHA256, access-key={}, signed-date={}, signature={}".format(
            ACCESS_KEY, datetime_gmt, signature
        )
    )


def get_shorted_link_coupang(url):
    try:
        REQUEST_METHOD = "POST"
        DOMAIN = "https://api-gateway.coupang.com"
        URL = "/v2/providers/affiliate_open_api/apis/openapi/v1/deeplink"
        authorization = generate_coupang_hmac(REQUEST_METHOD, URL)
        post_data = {"coupangUrls": [url]}
        headers = {
            "Content-Type": "application/json",
            "Authorization": authorization,
        }

        response = requests.post(f"{DOMAIN}{URL}", json=post_data, headers=headers)
        response_data = response.json()

        RequestLogService.create_request_log(
            post_id=0,
            ai_type="coupang",
            request=json.dumps(post_data),
            response=json.dumps(response_data),
            status=1,
        )

        if response_data.get("code") == "200":
            data = response_data.get("data")
            first_data = data[0] if data and len(data) > 0 else None
            if first_data:
                return first_data.get("shortenUrl")
            return url
        else:
            return url

    except Exception as e:
        logger.error(f"Error while shorting link: {e}")
        return url
