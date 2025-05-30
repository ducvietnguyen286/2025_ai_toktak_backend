from http.cookiejar import CookieJar
import traceback
from bs4 import BeautifulSoup
import requests
from app.lib.header import generate_desktop_user_agent
from app.lib.logger import logger
from urllib.parse import unquote, urlparse

from app.scraper.pages.domeggook.parser import Parser
from urllib.parse import unquote


class DomeggookScraper:
    def __init__(self, params):
        self.url = params["url"]

    def un_shortend_url(self, url, retry=0):
        try:
            cookie_jar = CookieJar()
            session = requests.Session()
            session.cookies = cookie_jar
            user_agent = generate_desktop_user_agent()
            headers = {
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "accept-encoding": "gzip, deflate, br, zstd",
                "accept-language": "en",
                "priority": "u=0, i",
                "referer": "",
                "upgrade-insecure-requests": "1",
                "user-agent": user_agent,
            }
            logger.info("Unshortend URL: {0}".format(url))
            response = session.get(
                url, allow_redirects=False, headers=headers, timeout=5
            )
            if "Location" in response.headers:
                redirect_url = response.headers["Location"]
                parser = urlparse(redirect_url)
                if not parser.netloc:
                    redirect_url = (
                        urlparse("https://domeggook.com")
                        ._replace(path=redirect_url)
                        .geturl()
                    )
                if "redirectUrl/share" in redirect_url:
                    query_params = parser.query
                    if type(query_params) == dict:
                        redirect_url = query_params.get("redirectUrl")
                    else:
                        redirect_url = redirect_url.split("redirectUrl=")[-1]
                        redirect_url = unquote(redirect_url)

                logger.info("Unshortend URL AFTER: {0}".format(redirect_url))
                return redirect_url
            else:
                return url
        except Exception as e:
            logger.error("Exception: {0}".format(str(e)))
            traceback.print_exc()
            if retry < 3:
                return self.un_shortend_url(url, retry + 1)
            return url

    def run(self):
        try:
            path = urlparse(self.url).path
            if not path.strip("/").isdigit():
                request_url = self.un_shortend_url(self.url)
            else:
                request_url = self.url

            if "mobile." in request_url:
                request_url = request_url.replace("mobile.", "")

            parsed_url = urlparse(request_url)
            real_url = parsed_url.scheme + "://" + parsed_url.netloc + parsed_url.path
            product_id = parsed_url.path.strip("/").split("/")[-1]
            domeggook_data = self.get_page_html(real_url)
            if not domeggook_data:
                return {}
            # file_html = open("demo.html", "w", encoding="utf-8")
            # file_html.write(str(domeggook_data))
            # file_html.close()
            response = Parser(domeggook_data).parse(real_url)
            response["meta_id"] = ""
            response["item_id"] = product_id
            response["vendor_id"] = ""
            return response
        except Exception as e:
            traceback.print_exc()
            logger.error("Exception: {0}".format(str(e)))
            return {}

    def get_page_html(self, url, count=0, added_headers=None):
        try:
            if count > 10:
                return False

            session = requests.Session()
            headers = self.generate_random_headers_request()

            response = session.get(url, headers=headers, timeout=5)
            info = response.content
            html = BeautifulSoup(info, "html.parser")
            # file_html = open("demo.html", "w", encoding="utf-8")
            # file_html.write(info.decode("utf-8"))
            # file_html.close()
            return html
        except Exception as e:
            logger.error(e)
            traceback.print_exc()
            count = count + 1
            return self.get_page_html(url, count, added_headers)

    def generate_random_headers_request(self):
        user_agent = generate_desktop_user_agent()
        headers = {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Encoding": "gzip, compress, br",
        }
        return headers
