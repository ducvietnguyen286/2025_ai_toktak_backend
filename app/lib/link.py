from urllib.parse import parse_qs, urlparse


def get_item_id_from_url_coupang(url):
    if not url:
        return ""

    parsed_url = urlparse(url)
    query_params = parsed_url.query
    query_params_dict = parse_qs(query_params)
    item_id = query_params_dict.get("itemId")
    return item_id[0] if item_id else ""


def get_vendor_id_from_url_coupang(url):
    if not url:
        return ""

    parsed_url = urlparse(url)
    query_params = parsed_url.query
    query_params_dict = parse_qs(query_params)
    vendor_item_id = query_params_dict.get("vendorItemId")
    return vendor_item_id[0] if vendor_item_id else ""


def get_item_id(data):
    if "item_id" in data:
        return data["item_id"]
    elif "url_crawl" in data and data["url_crawl"] != "":
        type = get_link_type(data["url_crawl"])
        if type == "COUPANG":
            meta_url = data.get("meta_url", "")
            item_id = get_item_id_from_url_coupang(meta_url)
        elif type == "ALIEXPRESS":
            item_id = data["url_crawl"].split("/")[-1].split(".")[0]
        elif type == "DOMEGGOOK":
            item_id = data["url_crawl"].split("/")[-1]

        return item_id
    else:
        return ""


def get_vendor_id(data):
    if "vendor_id" in data:
        return data["vendor_id"]
    elif "url_crawl" in data and data["url_crawl"] != "":
        type = get_link_type(data["url_crawl"])
        if type == "COUPANG":
            meta_url = data.get("meta_url", "")
            vendor_id = get_vendor_id_from_url_coupang(meta_url)

        return vendor_id
    else:
        return ""


def get_link_type(link):
    if "coupang" in link:
        return "COUPANG"
    elif "aliexpress" in link:
        return "ALIEXPRESS"
    elif "domeggook" in link:
        return "DOMEGGOOK"
    else:
        return "UNKNOWN"
