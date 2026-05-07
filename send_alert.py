import requests
import os
from datetime import datetime

# 텔레그램 설정
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    response = requests.post(url, json=payload)
    return response.json()

def get_naver_news(query):
    client_id = os.environ.get("NAVER_CLIENT_ID")
    client_secret = os.environ.get("NAVER_CLIENT_SECRET")
    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret
    }
    params = {
        "query": query,
        "display": 5,
        "sort": "date"
    }
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json().get("items", [])
    return []

def clean_html(text):
    import re
    text = re.sub(r'<[^>]+>', '', text)
    text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"').replace('&#039;', "'")
    return text.strip()

def main():
    today = datetime.now().strftime("%Y년 %m월 %d일")

    # 뉴스 수집
    queries = ["주식 급등 오늘", "코스피 코스닥 주목 종목", "외국인 기관 매수 종목"]
    all_news = []
    seen_titles = set()

    for query in queries:
        items = get_naver_news(query)
        for item in items:
            title = clean_html(item.get("title", ""))
            desc = clean_html(item.get("description", ""))
            link = item.get("originallink") or item.get("link", "")
            if title not in seen_titles:
                seen_titles.add(title)
                all_news.append({"title": title, "desc": desc, "link": link})
        if len(all_news) >= 6:
            break

    # 메시지 구성
    msg = f"📰 *오늘의 주식 모닝 브리핑*\n📅 {today}\n\n"

    msg += "🔥 *주목 뉴스*\n"
    for i, news in enumerate(all_news[:5], 1):
        title = news['title'][:40] + "..." if len(news['title']) > 40 else news['title']
        msg += f"{i}\\. {title}\n"

    msg += "\n💡 *스윙 매매 포인트*\n"
    msg += "• 외국인·기관 연속 매수 종목 주목\n"
    msg += "• 거래량 급증 + 양봉 마감 종목 체크\n"
    msg += "• 52주 신고가 돌파 종목 모멘텀 확인\n"
    msg += "• 실적 시즌 수혜 섹터 (반도체, 2차전지, 바이오) 관심\n"

    msg += "\n⚠️ _본 내용은 투자 참고용이며 투자 판단은 본인 책임입니다._"

    result = send_telegram(msg)
    if result.get("ok"):
        print("✅ 텔레그램 전송 성공!")
    else:
        print(f"❌ 전송 실패: {result}")

if __name__ == "__main__":
    main()
