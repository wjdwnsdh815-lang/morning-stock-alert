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
    for old, new in [('&amp;','&'),('&lt;','<'),('&gt;','>'),('&quot;','"'),('&#039;',"'"),('&nbsp;',' ')]:
        text = text.replace(old, new)
    return text.strip()

def fmt(price):
    return f"{price:,}원"

def get_stock_price(code):
    try:
        url = f"https://finance.naver.com/item/main.naver?code={code}"
        r = requests.get(url, headers=HEADERS, timeout=8)
        r.encoding = 'euc-kr'
        match = re.search(r'no_today.*?blind">([0-9,]+)<', r.text, re.DOTALL)
        if match:
            return int(match.group(1).replace(',', ''))
    except:
        pass
    return None

def get_hot_stocks():
    stocks = []
    for sosok in ['0', '1']:
        try:
            url = f"https://finance.naver.com/sise/sise_rise.naver?sosok={sosok}"
            r = requests.get(url, headers=HEADERS, timeout=10)
            r.encoding = 'euc-kr'
            matches = re.findall(r'code=(\d{6})">([^<]{2,10})</a>', r.text)
            seen = {s['name'] for s in stocks}
            skip = ['코스','ETF','KODEX','TIGER','KINDEX','ARIRANG','HANARO']
            for code, name in matches:
                name = clean(name)
                if name and len(name) >= 2 and name not in seen and not any(x in name for x in skip):
                    seen.add(name)
                    price = get_stock_price(code)
                    if price:
                        stocks.append({
                            'name': name, 'code': code, 'price': price,
                            'stop': int(price * 0.95),
                            'target': int(price * 1.12)
                        })
                if len(stocks) >= 5:
                    break
        except Exception as e:
            print(f"급등주 오류: {e}")
        if len(stocks) >= 5:
            break
    return stocks

def get_finance_news():
    news = []
    try:
        r = requests.get(
            "https://finance.naver.com/news/news_list.naver?mode=LSS2D&section_id=101&section_id2=258",
            headers=HEADERS, timeout=10
        )
        r.encoding = 'euc-kr'
        titles = re.findall(r'title="([^"]{10,80})"', r.text)
        seen = set()
        for t in titles:
            t = clean(t)
            if t and t not in seen and len(t) > 8:
                seen.add(t)
                news.append(t)
            if len(news) >= 5:
                break
    except Exception as e:
        print(f"뉴스 오류: {e}")
    return news

def main():
    days = ["월요일","화요일","수요일","목요일","금요일","토요일","일요일"]
    now = datetime.now()
    today = f"{now.strftime('%Y년 %m월 %d일')} ({days[now.weekday()]})"

    print("뉴스 수집 중...")
    news = get_finance_news()
    print("급등주 수집 중...")
    stocks = get_hot_stocks()

    lines = []
    lines.append("=== 모닝 주식 브리핑 ===")
    lines.append(today)
    lines.append("")

    lines.append("[오늘의 주요 증시 뉴스]")
    if news:
        for i, n in enumerate(news[:5], 1):
            title = n[:50] + "..." if len(n) > 50 else n
            lines.append(f"{i}. {title}")
    else:
        lines.append("뉴스를 불러오지 못했습니다.")
    lines.append("")

    lines.append("[스윙 매매 추천 종목]")
    if stocks:
        for s in stocks:
            lines.append(f"")
            lines.append(f"▶ {s['name']} ({s['code']})")
            lines.append(f"  현재가 : {fmt(s['price'])}")
            lines.append(f"  진입가 : {fmt(s['price'])} 부근")
            lines.append(f"  손절가 : {fmt(s['stop'])} (-5%)")
            lines.append(f"  목표가 : {fmt(s['target'])} (+12%)")
    else:
        lines.append("장 시작 후 네이버 증권 급등주 탭을 확인하세요.")
    lines.append("")

    lines.append("[스윙 체크포인트]")
    lines.append("• 외국인·기관 동시 순매수 종목 우선")
    lines.append("• 거래량 평균 3배 이상 + 양봉 마감")
    lines.append("• 52주 신고가 돌파 종목 모멘텀 확인")
    lines.append("")
    lines.append("※ 투자 판단은 본인 책임입니다.")

    msg = "\n".join(lines)

    print("전송 중...")
    result = send_telegram(msg)
    print("✅ 성공!" if result.get("ok") else f"❌ 실패: {result}")

if __name__ == "__main__":
    main()
