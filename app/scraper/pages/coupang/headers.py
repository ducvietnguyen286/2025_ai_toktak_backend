import random


def list_mobile_headers():
    return [
        {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en,vi;q=0.9,es;q=0.8,vi-VN;q=0.7,fr-FR;q=0.6,fr;q=0.5,en-US;q=0.4",
            "priority": "u=0, i",
            "user-agent": "Mozilla/5.0 (Linux; Android 6.0.1; SM-N920P Build/MMB29K; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/52.0.2743.98 Mobile Safari/537.36 Mobile/1 SellOnEtsy/2.41.1 Android/1",
        },
        {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en,vi;q=0.9,es;q=0.8,vi-VN;q=0.7,fr-FR;q=0.6,fr;q=0.5,en-US;q=0.4",
            "priority": "u=0, i",
            "user-agent": "Mozilla/5.0 (Linux; Android 6.0.1; E6853 Build/32.2.A.0.253) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.98 Mobile Safari/537.36",
        },
        {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en,vi;q=0.9,es;q=0.8,vi-VN;q=0.7,fr-FR;q=0.6,fr;q=0.5,en-US;q=0.4",
            "priority": "u=0, i",
            "user-agent": "Mozilla/5.0 (Linux; Android 4.4.2; QMobile i5i Build/KOT49H) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/30.0.1599.82 Mobile Safari/537.36",
        },
        {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en,vi;q=0.9,es;q=0.8,vi-VN;q=0.7,fr-FR;q=0.6,fr;q=0.5,en-US;q=0.4",
            "priority": "u=0, i",
            "user-agent": "Mozilla/5.0 (Linux; Android 4.4.2; SAMSUNG-SGH-I337 Build/KOT49H) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/30.0.0.0 Mobile Safari/537.36 Indeed App 2.3 Indeed App 2.3",
        },
        {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en,vi;q=0.9,es;q=0.8,vi-VN;q=0.7,fr-FR;q=0.6,fr;q=0.5,en-US;q=0.4",
            "priority": "u=0, i",
            "user-agent": "Mozilla/5.0 (Linux; Android 5.1.1; Redmi 3 Build/LMY47V; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/56.0.2924.87 Mobile Safari/537.36",
        },
        {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en,vi;q=0.9,es;q=0.8,vi-VN;q=0.7,fr-FR;q=0.6,fr;q=0.5,en-US;q=0.4",
            "priority": "u=0, i",
            "user-agent": "Mozilla/5.0 (Linux; Android 7.0; SM-J701F Build/NRD90M; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/60.0.3112.116 Mobile Safari/537.36",
        },
        {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en,vi;q=0.9,es;q=0.8,vi-VN;q=0.7,fr-FR;q=0.6,fr;q=0.5,en-US;q=0.4",
            "priority": "u=0, i",
            "user-agent": "Mozilla/5.0 (Linux; Android 4.2.2; GT-I9152) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.80 Mobile Safari/537.36",
        },
        {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en,vi;q=0.9,es;q=0.8,vi-VN;q=0.7,fr-FR;q=0.6,fr;q=0.5,en-US;q=0.4",
            "priority": "u=0, i",
            "user-agent": "Mozilla/5.0 (Linux; Android 6.0.1; ZTE Blade A462 Build/MMB29M) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Mobile Safari/537.36",
        },
        {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en,vi;q=0.9,es;q=0.8,vi-VN;q=0.7,fr-FR;q=0.6,fr;q=0.5,en-US;q=0.4",
            "priority": "u=0, i",
            "user-agent": "Mozilla/5.0 (Linux; Android 6.0.1; CPH1613 Build/MMB29M) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.68 Mobile Safari/537.36",
        },
        {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en,vi;q=0.9,es;q=0.8,vi-VN;q=0.7,fr-FR;q=0.6,fr;q=0.5,en-US;q=0.4",
            "priority": "u=0, i",
            "user-agent": "Mozilla/5.0 (Linux; Android 7.0; Hawk_from_EE Build/NRD90M) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Mobile Safari/537.36",
        },
        {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en,vi;q=0.9,es;q=0.8,vi-VN;q=0.7,fr-FR;q=0.6,fr;q=0.5,en-US;q=0.4",
            "priority": "u=0, i",
            "user-agent": "Mozilla/5.0 (Linux; Android 4.3; MT2L03 Build/HuaweiMT2L03) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.141 Mobile Safari/537.36",
        },
        {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en,vi;q=0.9,es;q=0.8,vi-VN;q=0.7,fr-FR;q=0.6,fr;q=0.5,en-US;q=0.4",
            "priority": "u=0, i",
            "user-agent": "Mozilla/5.0 (Linux; Android 4.4.2; Micromax A311 Build/KOT49H) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.85 Mobile Safari/537.36",
        },
        {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en,vi;q=0.9,es;q=0.8,vi-VN;q=0.7,fr-FR;q=0.6,fr;q=0.5,en-US;q=0.4",
            "priority": "u=0, i",
            "user-agent": "Mozilla/5.0 (Linux; Android 4.4.4; SAMSUNG-SGH-I337 Build/KTU84P) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.158 Mobile Safari/537.36",
        },
        {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en,vi;q=0.9,es;q=0.8,vi-VN;q=0.7,fr-FR;q=0.6,fr;q=0.5,en-US;q=0.4",
            "priority": "u=0, i",
            "user-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 6_1_4 like Mac OS X) AppleWebKit/536.26 (KHTML, like Gecko) CriOS/32.0.1700.20 Mobile/10B350 Safari/8536.25",
        },
        {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en,vi;q=0.9,es;q=0.8,vi-VN;q=0.7,fr-FR;q=0.6,fr;q=0.5,en-US;q=0.4",
            "priority": "u=0, i",
            "user-agent": "Mozilla/5.0 (Linux; Android 5.0.2; Lenovo A5000 Build/LRX22G) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.158 Mobile Safari/537.36",
        },
    ]


def random_mobile_header():
    headers = list_mobile_headers()
    return random.choice(headers)


def random_web_header():
    return {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "en,vi;q=0.9,es;q=0.8,vi-VN;q=0.7,fr-FR;q=0.6,fr;q=0.5,en-US;q=0.4",
        "upgrade-insecure-requests": "1",
        "user-agent": "Mozilla/5.0 (Linux; U; Android 4.4.2; en-us; SPH-L710 Build/KOT49H) AppleWebKit/534.30 (KHTML, like Gecko) Version/4.0 Mobile Safari/534.30",
    }
