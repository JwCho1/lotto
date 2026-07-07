import json
import os
import time
import requests

DATA_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "lotto_history.json"
)
API_URL = "https://www.dhlottery.co.kr/common.do?method=getLottoNumber&drwNo={}"
HOME_URL = "https://www.dhlottery.co.kr/common.do?method=main"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/138.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.dhlottery.co.kr/gameResult.do?method=byWin",
    "X-Requested-With": "XMLHttpRequest",
}


def load_history():
    if os.path.exists(DATA_PATH):
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"draws": []}


def save_history(data):
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def make_session():
    """
    동행복권 서버가 세션/쿠키 없는 요청을 봇으로 판단해
    메인 페이지로 리다이렉트시키는 것으로 보여, 먼저 메인 페이지를
    한 번 방문해 쿠키를 확보한 뒤 그 세션으로 API를 호출한다.
    """
    session = requests.Session()
    session.headers.update(HEADERS)
    try:
        home_res = session.get(HOME_URL, timeout=10)
        print("세션 초기화 STATUS:", home_res.status_code)
        print("쿠키:", session.cookies.get_dict())
    except requests.RequestException as e:
        print("세션 초기화 실패:", e)
    return session


def fetch_draw(session, drw_no):
    try:
        res = session.get(
            API_URL.format(drw_no),
            timeout=10
        )
        print(f"\n=== 회차 {drw_no} ===")
        print("URL:", res.url)
        print("최종 응답 URL(res.url):", res.url)
        print("STATUS:", res.status_code)
        print("CONTENT-TYPE:", res.headers.get("Content-Type"))
        res.raise_for_status()
        try:
            payload = res.json()
        except Exception:
            print("JSON 파싱 실패")
            print("응답 내용 앞부분:")
            print(res.text[:500])
            return None
        if payload.get("returnValue") != "success":
            print("returnValue != success:", payload)
            return None
        return {
            "drwNo": payload["drwNo"],
            "date": payload["drwNoDate"],
            "numbers": [payload[f"drwtNo{i}"] for i in range(1, 7)],
            "bonus": payload["bnusNo"],
            "firstPrizePerWinner": payload["firstWinamnt"],
            "firstWinnerCount": payload["firstPrzwnerCo"],
            "firstTotalPrize": payload["firstAccumamnt"],
            "totalSales": payload["totSellamnt"],
        }
    except requests.RequestException as e:
        print("요청 실패:", e)
        return None


def main():
    history = load_history()
    existing_nos = {d["drwNo"] for d in history["draws"]}
    start_no = max(existing_nos) + 1 if existing_nos else 1

    session = make_session()

    new_draws = []
    no = start_no
    fail_count = 0
    while True:
        draw = fetch_draw(session, no)
        if draw is None:
            fail_count += 1
            # 세션 문제일 수도 있으니 한 번 세션을 새로 만들어서 재시도
            if fail_count == 1:
                print(">> 세션을 새로 만들어 1회 재시도합니다.")
                session = make_session()
                draw = fetch_draw(session, no)
            if draw is None:
                break
        new_draws.append(draw)
        no += 1
        time.sleep(0.5)

    if new_draws:
        history["draws"].extend(new_draws)
        history["draws"].sort(key=lambda d: d["drwNo"])
        save_history(history)
        print(f"{len(new_draws)}개 회차 추가")
        print([d["drwNo"] for d in new_draws])
    else:
        print("새로운 회차 없음")


if __name__ == "__main__":
    main()
