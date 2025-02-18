import random


def list_mobile_headers():
    return [
        {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en",
            "priority": "u=0, i",
            "referer": "https://m.coupang.com/",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (Linux; U; Android 4.4.2; en-us; SPH-L710 Build/KOT49H) AppleWebKit/534.30 (KHTML, like Gecko) Version/4.0 Mobile Safari/534.30",
        },
        {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en",
            "priority": "u=0, i",
            "referer": "",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (Linux; U; Android 4.1.2; en-us; SGH-T599N Build/JZO54K) AppleWebKit/534.30 (KHTML, like Gecko) Version/4.0 Mobile Safari/534.30",
        },
        {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en",
            "priority": "u=0, i",
            "referer": "",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (Linux; U; Android 4.0.4; en-us; SCH-S738C Build/IMM76D) AppleWebKit/534.30 (KHTML, like Gecko) Version/4.0 Mobile Safari/534.30",
        },
        {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en",
            "priority": "u=0, i",
            "referer": "",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (Linux; U; Android 2.3.5; en-in; Micromax A87 Build/GINGERBREAD) AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/533.1",
        },
        {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en",
            "priority": "u=0, i",
            "referer": "",
            "upgrade-insecure-requests": "1",
            "user-agent": "Dalvik/1.6.0 (Linux; U; Android 4.0.4; opensign_x86 Build/IMM76L)",
        },
    ]


def random_mobile_header():
    headers = list_mobile_headers()
    return random.choice(headers)
