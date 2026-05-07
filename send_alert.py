import requests
import os
import re
from datetime import datetime

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
}

def send_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    r = requests.post(url, json=payload)
    return r.json()

def clean(text):
    text = re.sub(r'<[^>]+>', '', text)
    entities = [
        ('&amp;', '&'), ('&lt;', '<'), ('&gt;', '>'), ('&quot;', '"'),
        ('&#039;', "'"), ('&nbsp;', ' '), ('&hellip;', '...'),
        ('&darr;', 'v'), ('&uarr;', '^'), ('&ldquo;', '"'), ('&rdquo;', '"'),
        ('&lsquo;', "'"), ('&rsquo;', "'"), ('&laquo;', '<<'), ('&raquo;', '>>'),
        ('&middot;', '.'), ('&bull;', '-'), ('&mdash;', '-'), ('&ndash;', '-'),
    ]
    for old, new in entities:
        text = text.replace(old, new)
    text = re.sub(r'&#(\d+);', lambda m: chr(int(m.group(1))), text)
    text = re.sub(r'&#x([0-9a-fA-F]+);', lambda m: chr(int(m.group(1), 16)), text)
    return text.strip()

def fmt_price(price):
    return f"{price:,}\uC6D0"

def get_stock_price_yahoo(code, market_code=0):
    suffixes = ['.KS', '.KQ'] if market_code == 0 else ['.KQ', '.KS']
    for suffix in suffixes:
        try:
            url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={code}{suffix}"
            r = requests.get(url, headers=HEADERS, timeout=8)
            data = r.json()
            results = data.get('quoteResponse', {}).get('result', [])
            if results:
                price = results[0].get('regularMarketPrice')
                if price:
                    return int(price)
        except Exception as e:
            print(f"  Yahoo({code}{suffix}) fail: {e}")
    return None

def get_stock_price_naver_api(code):
    try:
        url = f"https://polling.finance.naver.com/api/realtime/domestic/stock/{code}"
        r = requests.get(url, headers=HEADERS, timeout=8)
        data = r.json()
        datas = data.get('datas', [])
        if datas:
            price = datas[0].get('closePrice') or datas[0].get('stockEndPrice')
            if price:
                return int(str(price).replace(',', ''))
    except Exception as e:
        print(f"  NaverAPI({code}) fail: {e}")
    return None

def get_stock_price(code, market_code=0):
    price = get_stock_price_naver_api(code)
    if price:
        return price
    return get_stock_price_yahoo(code, market_code)

def get_hot_stocks():
    stocks = []
    exclude_keywords = ['\uCF54\uC2A4', 'ETF', 'KODEX', 'TIGER', 'KBSTAR', 'HANARO', 'ARIRANG', 'WOORI', 'SMART', 'FOCUS', 'PLUS']

    urls_to_try = [
        ("https://finance.naver.com/sise/sise_rise.naver?sosok=0", 0),
        ("https://finance.naver.com/sise/sise_rise.naver?sosok=1", 1),
        ("https://finance.naver.com/sise/sise_quant.naver?sosok=0", 0),
        ("https://finance.naver.com/sise/sise_quant.naver?sosok=1", 1),
    ]

    for url, market_code in urls_to_try:
        if len(stocks) >= 5:
            break
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            r.encoding = 'euc-kr'
            matches = re.findall(r'code=(\d{6})">([^<]{2,15})</a>', r.text)
            print(f"URL({url[-30:]}): {len(matches)} candidates")

            if not matches:
                print(f"  HTML snippet: {r.text[2000:2200]}")
                continue

            seen = {s['name'] for s in stocks}
            for code, name in matches:
                name = clean(name).strip()
                if (name
                    and len(name) >= 2
                    and name not in seen
                    and not any(x in name for x in exclude_keywords)
                    and not name.startswith('[')
                    and '.' not in name[:3]):
                    seen.add(name)
                    print(f"  checking: {name} ({code})")
                    price = get_stock_price(code, market_code)
                    if price:
                        stocks.append({
                            'name': name,
                            'code': code,
                            'price': price,
                            'stop': int(price * 0.95),
                            'target': int(price * 1.12)
                        })
                        print(f"  OK {name}: {price:,}\uC6D0")
                    else:
                        print(f"  FAIL {name}: no price")
                if len(stocks) >= 5:
                    break
        except Exception as e:
            print(f"error({url[-20:]}): {e}")

    return stocks

def get_finance_news():
    news = []
    exclude = ['\uAC80\uC0C9', '\uB85C\uADF8\uC778', '\uB354\uBCF4\uAE30', '\uAD00\uB828\uAE30\uC0AC', '\uC774\uC804', '\uB2E4\uC74C', '\uD68C\uC6D0\uAC00\uC785', '\uAD6C\uB3C5', '\uC885\uBAA9\uBA85']
    try:
        r = requests.get(
            "https://finance.naver.com/news/news_list.naver?mode=LSS2D&section_id=101&section_id2=258",
            headers=HEADERS, timeout=10
        )
        r.encoding = 'euc-kr'
        titles = re.findall(r'<a[^>]+href="[^"]*article[^"]*"[^>]*>([^<]{10,100})</a>', r.text)
        if len(titles) < 3:
            titles = re.findall(r'title="([^"]{10,80})"', r.text)
        seen = set()
        for t in titles:
            t = clean(t)
            if (t and t not in seen and len(t) > 10
                and not any(ex in t for ex in exclude)
                and '.' not in t[:4]):
                seen.add(t)
                news.append(t)
            if len(news) >= 5:
                break
    except Exception as e:
        print(f"news error: {e}")
    return news

def main():
    days = ["\uC6D4\uC694\uC77C", "\uD654\uC694\uC77C", "\uC218\uC694\uC77C", "\uBAA9\uC694\uC77C", "\uAE08\uC694\uC77C", "\uD1A0\uC694\uC77C", "\uC77C\uC694\uC77C"]
    now = datetime.now()
    today = f"{now.strftime('%Y\uB144 %m\uC6D4 %d\uC77C')} ({days[now.weekday()]})"
    print(f"run: {now.strftime('%Y-%m-%d %H:%M')} UTC")

    print("news...")
    news = get_finance_news()
    print(f"news count: {len(news)}")

    print("stocks...")
    stocks = get_hot_stocks()
    print(f"stock count: {len(stocks)}")

    msg = f"=== \uBAA8\uB2DD \uC8FC\uC2DD \uBE0C\uB9AC\uD551 ===\n{today}\n\n"

    msg += "[\uC624\uB298\uC758 \uC8FC\uC694 \uC99D\uC2DC \uB274\uC2A4]\n"
    if news:
        for i, n in enumerate(news[:5], 1):
            title = n[:50] + "..." if len(n) > 50 else n
            msg += f"{i}. {title}\n"
    else:
        msg += "\uB274\uC2A4 \uBD88\uB7EC\uC624\uAE30 \uC2E4\uD328\n"

    msg += "\n"
    msg += "[\uC2A4\uC717 \uB9E4\uB9E4 \uC8FC\uBAA9 \uC885\uBAA9]\n"
    if stocks:
        for s in stocks:
            msg += f"\n[{s['name']}] ({s['code']})\n"
            msg += f"  \uD604\uC7AC\uAC00: {fmt_price(s['price'])}\n"
            msg += f"  \uC9C4\uC785\uAC00: {fmt_price(s['price'])} \uBD80\uADFC\n"
            msg += f"  \uC190\uC808\uAC00: {fmt_price(s['stop'])} (-5%)\n"
            msg += f"  \uBAA9\uD45C\uAC00: {fmt_price(s['target'])} (+12%)\n"
    else:
        msg += "\uC804\uC77C \uAE09\uB4F1\uC8FC \uC5C6\uC74C - \uC624\uB298 \uC7A5 \uC2DC\uC791 \uD6C4 \uD655\uC778\uD544\uC694\n"

    msg += "\n"
    msg += "[\uC2A4\uC717 \uCCB4\uD06C\uD3EC\uC778\uD2B8]\n"
    msg += "- \uC678\uAD6D\uC778.\uAE30\uAD00 \uB3D9\uC2DC \uC21C\uB9E4\uC218 \uC885\uBAA9 \uC6B0\uC120\n"
    msg += "- \uAC70\uB798\uB7C9 \uD3C9\uADE0 3\uBC30 \uC774\uC0C1 + \uC591\uBD09 \uB9C8\uAC10\n"
    msg += "- 52\uC8FC \uC2E0\uACE0\uAC00 \uB3CC\uD30C \uC885\uBAA9 \uBAA8\uBA58\uD140 \uD655\uC778\n"
    msg += "\n\u203B \uD22C\uC790 \uD310\uB2E8\uC740 \uBCF8\uC778 \uCC45\uC784\uC785\uB2C8\uB2E4."

    print("sending...")
    result = send_telegram(msg)
    if result.get("ok"):
        print("success!")
    else:
        print(f"fail: {result}")

if __name__ == "__main__":
    main()
