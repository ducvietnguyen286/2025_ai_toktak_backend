import hashlib
import hmac
import json
import os
import time

import requests


def sign_api_request(api, parameters, secret):
    sort_dict = sorted(parameters)
    if "/" in api:
        parameters_str = "%s%s" % (
            api,
            str().join("%s%s" % (key, parameters[key]) for key in sort_dict),
        )
    else:
        parameters_str = str().join(
            "%s%s" % (key, parameters[key]) for key in sort_dict
        )

    h = hmac.new(
        secret.encode(encoding="utf-8"),
        parameters_str.encode(encoding="utf-8"),
        digestmod=hashlib.sha256,
    )

    return h.hexdigest().upper()


class TokenAliExpress:

    def get_access_token(self, authorization_code):
        ALI_APP_KEY = os.environ.get("ALI_APP_KEY") or ""
        ALI_APP_SECRET = os.environ.get("ALI_APP_SECRET") or ""

        BASE_URL = "https://api-sg.aliexpress.com/rest"
        ACTION = "/auth/token/create"
        CURRENT_TIME = int(time.time()) * 1000
        SIGN_METHOD = "sha256"

        params = {
            "app_key": ALI_APP_KEY,
            "timestamp": CURRENT_TIME,
            "sign_method": SIGN_METHOD,
            "code": authorization_code,
            "simplify": "true",
        }
        sign = sign_api_request(ACTION, params, ALI_APP_SECRET)
        params["sign"] = sign
        response = requests.get(f"{BASE_URL}{ACTION}", params=params, timeout=10)
        res = response.json()
        if res:
            return res
        else:
            return None

    def refresh_access_token(self, user):
        ALI_APP_KEY = os.environ.get("ALI_APP_KEY") or ""
        ALI_APP_SECRET = os.environ.get("ALI_APP_SECRET") or ""

        BASE_URL = "https://api-sg.aliexpress.com/rest"
        ACTION = "/auth/token/refresh"
        CURRENT_TIME = int(time.time()) * 1000
        SIGN_METHOD = "sha256"

        ali_info = user.ali_express_info
        ali_info = json.loads(ali_info) if ali_info else {}
        refresh_token = ali_info.get("refresh_token")
        if not refresh_token:
            return None

        params = {
            "app_key": ALI_APP_KEY,
            "timestamp": CURRENT_TIME,
            "sign_method": SIGN_METHOD,
            "refresh_token": refresh_token,
        }
        sign = sign_api_request(ACTION, params, ALI_APP_SECRET)
        params["sign"] = sign
        response = requests.get(f"{BASE_URL}{ACTION}", params=params, timeout=10)
        res = response.json()
        if res:
            return res
        else:
            return None


class AliExpressAPI:

    def get_product_info(self, user, product_id):
        ALI_APP_KEY = os.environ.get("ALI_APP_KEY") or ""
        ALI_APP_SECRET = os.environ.get("ALI_APP_SECRET") or ""

        BASE_URL = "https://api-sg.aliexpress.com/sync"
        ACTION = "aliexpress.solution.product.info.get"
        CURRENT_TIME = int(time.time()) * 1000
        SIGN_METHOD = "sha256"

        ali_info = user.ali_express_info
        ali_info = json.loads(ali_info) if ali_info else {}
        access_token = ali_info.get("access_token")
        if not access_token:
            return None

        params = {
            "method": ACTION,
            "app_key": ALI_APP_KEY,
            "timestamp": CURRENT_TIME,
            "sign_method": SIGN_METHOD,
            "product_id": product_id,
            "access_token": access_token,
        }
        sign = sign_api_request(ACTION, params, ALI_APP_SECRET)
        params["sign"] = sign
        response = requests.get(f"{BASE_URL}{ACTION}", params=params, timeout=10)
        res = response.json()
        if res:
            return res
        else:
            return None
