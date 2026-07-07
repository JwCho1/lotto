import json
import os
import time
import requests

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "lotto_history.json")
API_URL = "https://www.dhlottery.co.kr/common.do?method=getLottoNumber&drwNo={}"


def load_history():
    if os.path.exists(DATA_PATH):
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"draws": []}


def save_history(data):
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def fetch_draw(drw_no):
    res = requests.get(API_URL.format(drw_no), timeout=10)
    res.raise_for_status()
    payload = res.json()
    if payload.get("returnValue") != "success":
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


def main():
    history = load_history()
    existing_nos = {d["drwNo"] for d in history["draws"]}
    start_no = (max(existing_nos) + 1) if existing_nos else 1

    new_draws = []
    no = start_no
    while True:
        draw = fetch_draw(no)
        if draw is None:
            break
        new_draws.append(draw)
        no += 1
        time.sleep(0.3)

    if new_draws:
        history["draws"].extend(new_draws)
        history["draws"].sort(key=lambda d: d["drwNo"])
        save_history(history)
        print(f"{len(new_draws)}개 회차 추가됨: {[d['drwNo'] for d in new_draws]}")
    else:
        print("새로운 회차 없음")


if __name__ == "__main__":
    main()
