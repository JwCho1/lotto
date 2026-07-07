import json
import os
import re
import time
import requests
from datetime import datetime
from bs4 import BeautifulSoup

DATA_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "lotto_history.json"
)

# JSON API(common.do?method=getLottoNumber) 대신, 사람이 보는 일반 결과 페이지를 파싱한다.
# 클라우드 서버 IP에서 JSON API 호출 시 봇으로 감지되어 홈페이지로 리다이렉트되는
# 문제가 있어, 검색엔진에도 노출되는 이 페이지로 우회한다.
RESULT_URL = "https://www.dhlottery.co.kr/gameResult.do?method=byWin&drwNo={}"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/138.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.dhlottery.co.kr/gameResult.do?method=byWin",
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


def won_to_int(text):
    """'83,595,692,700원' 같은 문자열을 정수로 변환"""
    digits = re.sub(r"[^0-9]", "", text or "")
    return int(digits) if digits else 0


def fetch_draw(session, drw_no):
    try:
        res = session.get(RESULT_URL.format(drw_no), headers=HEADERS, timeout=10)
        print(f"\n=== 회차 {drw_no} ===")
        print("STATUS:", res.status_code)
        res.raise_for_status()

        soup = BeautifulSoup(res.text, "lxml")

        # 날짜 파싱 실패 = 아직 추첨 안 된 회차(또는 페이지가 없음)로 간주하고 중단
        desc_tag = soup.find("p", class_="desc")
        if desc_tag is None:
            print("desc 태그 없음 -> 아직 추첨되지 않은 회차로 판단")
            print("최종 응답 URL:", res.url)
            print("페이지 title:", soup.title.string if soup.title else "(title 없음)")
            print("응답 앞부분 500자:")
            print(res.text[:500])
            return None

        try:
            date_obj = datetime.strptime(desc_tag.text.strip(), "(%Y년 %m월 %d일 추첨)")
        except ValueError:
            print("날짜 파싱 실패:", desc_tag.text)
            return None

        win_div = soup.find("div", class_="num win")
        bonus_div = soup.find("div", class_="num bonus")
        if win_div is None or bonus_div is None:
            print("당첨번호/보너스 영역을 찾을 수 없음")
            return None

        numbers = [int(x) for x in win_div.find("p").text.strip().split("\n") if x.strip()]
        bonus = int(bonus_div.find("p").text.strip())

        if len(numbers) != 6:
            print("당첨번호 개수 이상:", numbers)
            return None

        # 순위별 당첨금액 표 파싱 (1등 정보만 사용)
        first_prize_total = 0
        first_prize_per_winner = 0
        first_winner_count = 0

        table = soup.find("table", class_="tbl_data_col")
        if table:
            first_row = table.find("tbody").find("tr")
            cells = first_row.find_all("td")
            # cells[0]: 순위, cells[1]: 총 당첨금액, cells[2]: 당첨게임 수, cells[3]: 1게임당 당첨금액
            first_prize_total = won_to_int(cells[1].get_text())
            first_winner_count = int(re.sub(r"[^0-9]", "", cells[2].get_text()) or 0)
            first_prize_per_winner = won_to_int(cells[3].get_text())

        return {
            "drwNo": drw_no,
            "date": date_obj.strftime("%Y-%m-%d"),
            "numbers": numbers,
            "bonus": bonus,
            "firstPrizePerWinner": first_prize_per_winner,
            "firstWinnerCount": first_winner_count,
            "firstTotalPrize": first_prize_total,
        }
    except requests.RequestException as e:
        print("요청 실패:", e)
        return None
    except Exception as e:
        print("파싱 중 예외:", e)
        return None


def main():
    history = load_history()
    existing_nos = {d["drwNo"] for d in history["draws"]}
    start_no = max(existing_nos) + 1 if existing_nos else 1

    session = requests.Session()

    new_draws = []
    no = start_no
    while True:
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
