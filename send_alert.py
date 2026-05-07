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
    text = re.sub(r'&#(d+);', lambda m: chr(int(m.group(1))), text)
    text = re.sub(r'&#x([0-9a-fA-F]+);', lambda m: chr(int(m.group(1), 16)), text)
    return text.strip()

def fmt_price(price):
    return f"{price:,}원"

def get_stock_price_api(code):
    try:
        url = f"https://m.stock.naver.com/api/stock/{code}/basic"
        r = requests.get(url, headers=HEADERS, timeout=8)
        data = r.json()
        price_str = data.get('closePrice') or data.get('currentPrice') or data.get('stockEndPrice')
        if price_str:
            return int(str(price_str).replace(',', ''))
    except:
        pass
    return None

def get_stock_price_scrape(code):
    try:
        url = f"https://finance.naver.com/item/main.naver?code={code}"
        r = requests.get(url, headers=HEADERS, timeout=8)
        r.encoding = 'euc-kr'
        for pattern in [
            r'<strong id="_nowVal">([0-9,]+)</strong>',
            r'"closePrice"s*:s*"?([0-9,]+)"?',
            r'class="no_today"[^>]*>s*<em[^>]*>s*<span class="blind">([0-9,]+)',
        ]:
            match = re.search(pattern, r.text, re.DOTALL)
            if match:
                return int(match.group(1).replace(',', ''))
    except:
        pass
    return None

def get_stock_price(code):
    price = get_stock_price_api(code)
    if price:
        return price
    return get_stock_price_scrape(code)

def get_hot_stocks():
    stocks = []
    exclude_keywords = ['코스', 'ETF', 'KODEX', 'TIGER', 'KBSTAR', 'HANARO', 'ARIRANG', 'WOORI', 'SMART', 'FOCUS']

    for market_code in [0, 1]:
        try:
            url = f"https://finance.naver.com/sise/sise_rise.naver?sosok={market_code}"
            r = requests.get(url, headers=HEADERS, timeout=10)
            r.encoding = 'euc-kr'
            matches = re.findall(r'item/main\.naver\?code=(\d{6})">([^<]{2,15})</a>', r.text)
            seen = {s['name'] for s in stocks}
            for code, name in matches:
                name = clean(name).strip()
                if (name
                    and len(name) >= 2
                    and name not in seen
                    and not any(x in name for x in exclude_keywords)
                    and not name.startswith('[')
                    and '·' not in name):
                    seen.add(name)
                    print(f"  가격 조회 중: {name} ({code})")
                    price = get_stock_price(code)
                    if price:
                        stocks.append({
                            'name': name,
                            'code': code,
                            'price': price,
                            'stop': int(price * 0.95),
                            'target': int(price * 1.12)
                        })
                        print(f"  v {name}: {price:,}원")
                    else:
                        print(f"  x {name}: 가격 조회 실패")
                if len(stocks) >= 5:
                    break
        except Exception as e:
            print(f"급등주 수집 오류: {e}")
        if len(stocks) >= 5:
            break
    return stocks

def get_finance_news():
    news = []
    exclude = ['검색', '로그인', '더보기', '관련기사', '이전', '다음', '회원가입', '구독']
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
            if (t
                and t not in seen
                and len(t) > 10
                and not any(ex in t for ex in exclude)
                and '·' not in t[:6]):
                seen.add(t)
                news.append(t)
            if len(news) >= 5:
                break
    except Exception as e:
        print(f"뉴스 수집 오류: {e}")
    return news

def main():
    days = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
    now = datetime.now()
    today = f"{now.strftime('%Y년 %m월 %d일')} ({days[now.weekday()]})"

    print("뉴스 수집 중...")
    news = get_finance_news()
    print(f"뉴스 {len(news)}개 수집 완료")

    print("급등주 + 현재가 수집 중...")
    stocks = get_hot_stocks()
    print(f"종목 {len(stocks)}개 수집 완료")

    msg = f"=== 모닝 주식 브리핑 ===\n{today}\n\n"

    msg += "[오늘의 주요 증시 뉴스]\n"
    if news:
        for i, n in enumerate(news[:5], 1):
            title = n[:50] + "..." if len(n) > 50 else n
            msg += f"{i}. {title}\n"
    else:
        msg += "뉴스를 불러오지 못했습니다.\n"

    msg += "\n"
    msg += "[스윙 매매 주목 종목]\n"
    if stocks:
        for s in stocks:
            msg += f"\n[{s['name']}] ({s['code']})\n"
            msg += f"  현재가: {fmt_price(s['price'])}\n"
            msg += f"  진입가: {fmt_price(s['price'])} 부근\n"
            msg += f"  손절가: {fmt_price(s['stop'])} (-5%)\n"
            msg += f"  목표가: {fmt_price(s['target'])} (+12%)\n"
    else:
        msg += "장 시작 후 네이버 증권 급등주 탭을 확인하세요.\n"

    msg += "\n"
    msg += "[스윙 체크포인트]\n"
    msg += "- 외국인·기관 동시 순매수 종목 우선\n"
    msg += "- 거래량 평균 3배 이상 + 양봉 마감\n"
    msg += "- 52주 신고가 돌파 종목 모멘텀 확인\n"
    msg += "\n※ 투자 판단은 본인 책임입니다."

    print("텔레그램 전송 중...")
    result = send_telegram(msg)
    if result.get("ok"):
        print("전송 성공!")
    else:
        print(f"전송 실패: {result}")

if __name__ == "__main__":
    main()
