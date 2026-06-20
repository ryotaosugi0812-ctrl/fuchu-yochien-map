#!/usr/bin/env python3
"""定員・空き情報をdata.jsonに追記"""

import json, re, time, requests
from bs4 import BeautifulSoup

BASE = "https://www.city.fuchu.tokyo.jp"
S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0 (compatible; research)"})

def fetch(path):
    url = BASE + path if path.startswith("/") else path
    r = S.get(url, timeout=12)
    r.encoding = r.apparent_encoding or "utf-8"
    return BeautifulSoup(r.text, "html.parser")

# ── 市立保育所：個別ページから定員を抽出 ──────────────────
def scrape_shiritsu_capacity():
    print("市立保育所 定員を取得中...")
    cap = {}
    paths = [
        ("/shisetu/kosodate/shiritu/kita.html",     "北保育所"),
        ("/shisetu/kosodate/shiritu/higashi.html",  "東保育所"),
        ("/shisetu/kosodate/shiritu/nishi.html",    "西保育所"),
        ("/shisetu/kosodate/shiritu/chuo.html",     "中央保育所"),
        ("/shisetu/kosodate/shiritu/kitayama.html", "北山保育所"),
        ("/shisetu/kosodate/shiritu/sumiyoshi.html","住吉保育所"),
        ("/shisetu/kosodate/shiritu/hiyoshi.html",  "日吉保育所"),
        ("/shisetu/kosodate/shiritu/honcho.html",   "本町保育所"),
        ("/shisetu/kosodate/shiritu/sanbongi.html", "三本木保育所"),
        ("/shisetu/kosodate/shiritu/miyoshi.html",  "美好保育所"),
    ]
    for path, name in paths:
        soup = fetch(path)
        text = soup.get_text(" ", strip=True)
        # 定員（令和X年度） 110名
        m = re.search(r'定員[（(][^)）]*[)）]\s*(\d+)名', text)
        total = int(m.group(1)) if m else None
        # 年齢別: ●0歳児 3名 etc.
        ages = {}
        for age_m in re.finditer(r'[●•]\s*(\d)歳児?\s*(\d+)名', text):
            ages[f"{age_m.group(1)}歳"] = int(age_m.group(2))
        cap[name] = {"定員合計": total, "年齢別定員": ages if ages else None}
        print(f"  {name}: 定員{total}名 {ages}")
        time.sleep(0.5)
    return cap

# ── 認証保育所：空き情報ページから人数取得 ──────────────────
def scrape_ninsho_vacancy():
    print("認証保育所 空き情報を取得中...")
    soup = fetch("/kosodate/shussan/hoikujo/ninsyo.html")
    text = soup.get_text(" ", strip=True)
    vacancies = {}
    # テーブル行を探す
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        for row in rows:
            cells = [c.get_text(strip=True) for c in row.find_all(["td","th"])]
            if len(cells) >= 2:
                name = cells[0]
                # 数値だけ取り出す（0〜5歳 + 合計）
                nums = []
                for c in cells[1:]:
                    m = re.match(r'^(\d+|-)$', c)
                    nums.append(int(c) if (m and c != '-') else None)
                if name and any(n is not None for n in nums):
                    vacancies[name] = nums  # [0歳,1歳,2歳,3歳,4歳,5歳,合計?]
    if not vacancies:
        # テーブルがない場合、正規表現でパース
        for m in re.finditer(r'([^\s]{3,30}保育[所園室])\s+([\d\-\s]+)', text):
            name = m.group(1)
            nums_str = m.group(2).strip().split()
            nums = [int(n) if n.isdigit() else None for n in nums_str]
            vacancies[name] = nums
    print(f"  {len(vacancies)} 施設の空き情報を取得")
    return vacancies

# ── メイン ──────────────────────────────────────────────────
def main():
    with open("data.json", encoding="utf-8") as f:
        data = json.load(f)

    shiritsu_cap  = scrape_shiritsu_capacity()
    ninsho_vac    = scrape_ninsho_vacancy()
    VACANCY_URL   = BASE + "/kosodate/shussan/hoikujo/ninsyo.html"
    CAPACITY_PDF  = BASE + "/kosodate/shussan/hoikujo/ukeireyotei.html"

    for facility in data:
        name = facility["name"]
        cat  = facility["category"]

        if cat == "認可保育所（市立）":
            info = shiritsu_cap.get(name, {})
            facility["定員合計"]  = info.get("定員合計")
            facility["年齢別定員"] = info.get("年齢別定員")
            facility["空き情報URL"] = CAPACITY_PDF

        elif cat == "認証保育所（東京都）":
            # 名前の前方一致でマッチング
            matched = next((v for k, v in ninsho_vac.items() if name[:6] in k or k[:6] in name), None)
            if matched:
                ages = ["0歳","1歳","2歳","3歳","4歳","5歳"]
                age_vac = {a: matched[i] for i, a in enumerate(ages) if i < len(matched) and matched[i] is not None}
                facility["空き人数"]  = age_vac
                facility["空き合計"]  = matched[-1] if len(matched) > 6 else None
            facility["空き情報URL"] = VACANCY_URL

        elif cat in ("認可保育所（私立）", "企業主導型", "地域型保育（認可）"):
            facility["空き情報URL"] = CAPACITY_PDF

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("\ndata.json を更新しました")

if __name__ == "__main__":
    main()
