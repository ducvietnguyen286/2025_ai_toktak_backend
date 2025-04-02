import hashlib
import hmac
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
            "CODE": authorization_code,
            "simplify": "true",
        }
        sign = sign_api_request(ACTION, params, ALI_APP_SECRET)
        params["sign"] = sign
        response = requests.get(f"{BASE_URL}{ACTION}", params=params, timeout=10)
        res = response.json()
        if res.status_code == 200:
            return res
        else:
            return None

    def refresh_access_token(self):
        # Logic to refresh access token from AliExpress API
        pass
