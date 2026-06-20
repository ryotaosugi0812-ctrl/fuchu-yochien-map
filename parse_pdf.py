#!/usr/bin/env python3
"""
府中市 受入予定人数PDFを解析してdata.jsonに追記する。
毎月更新される最新PDFをダウンロードして実行する想定。

使い方:
  python3 parse_pdf.py              # 最新PDFを自動DL
  python3 parse_pdf.py waku.pdf     # ローカルPDFを使用
"""

import json, re, sys, requests
import pdfplumber
from pathlib import Path

BASE = "https://www.city.fuchu.tokyo.jp/kosodate/shussan/hoikujo"
AGES = ["0歳","1歳","2歳","3歳","4歳","5歳"]


def latest_pdf_url():
    """ページから最新のPDF URLを取得"""
    resp = requests.get(f"{BASE}/ukeireyotei.html", timeout=10)
    resp.encoding = resp.apparent_encoding
    m = re.search(r'ukeireyotei\.files/(\d{4}waku(?:-\d+)?\.pdf)', resp.text)
    if not m:
        raise RuntimeError("PDFリンクが見つかりません")
    return f"{BASE}/ukeireyotei.files/{m.group(1)}", m.group(1)


def parse_cell(s):
    """'3', '0（1）', '' などを数値に変換。括弧内は条件付き枠で無視。"""
    if not s or not s.strip():
        return 0
    s = s.strip()
    m = re.match(r'^(\d+)', s)
    return int(m.group(1)) if m else 0


def parse_pdf(path: str) -> dict:
    """PDFを解析し {施設名: {age: count, ...}} を返す"""
    result = {}
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    # 9列: [区分, 施設名, 0歳, 1歳, 2歳, 3歳, 4歳, 5歳, 計]
                    if len(row) < 9:
                        continue
                    name = (row[1] or "").strip()
                    if not name or name in ("保育所等名", "合 計", "合計"):
                        continue
                    # ヘッダー行スキップ
                    if "歳" in name or name in ("０歳児", "計"):
                        continue
                    ages = {}
                    for i, age in enumerate(AGES):
                        ages[age] = parse_cell(row[i + 2])
                    ages["計"] = sum(ages.values())
                    result[name] = ages
    return result


def normalize(name: str) -> str:
    """名寄せ用正規化（全角スペース・記号・ふりがな括弧を除去）"""
    name = re.sub(r'[（(][ぁ-ん\s　]+[）)]', '', name)  # （ふりがな）を除去
    return re.sub(r'[\s　・\-－]', '', name).replace('（', '(').replace('）', ')') \
             .replace('第２', '第2').replace('２', '2')


def match(pdf_name: str, data_name: str) -> bool:
    a, b = normalize(pdf_name), normalize(data_name)
    return a == b or a in b or b in a or a[:8] == b[:8]


def main():
    # PDF取得
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        pdf_label = Path(pdf_path).name
    else:
        print("最新PDFをダウンロード中...", flush=True)
        url, fname = latest_pdf_url()
        pdf_path = fname
        resp = requests.get(url, timeout=20)
        Path(fname).write_bytes(resp.content)
        print(f"  {fname} ({len(resp.content)//1024}KB)", flush=True)
        pdf_label = fname

    print(f"PDFを解析: {pdf_path}", flush=True)
    pdf_data = parse_pdf(pdf_path)
    print(f"  {len(pdf_data)} 施設分を抽出", flush=True)

    # data.json読み込み
    with open("data.json", encoding="utf-8") as f:
        facilities = json.load(f)

    # マッチング & 更新
    hit, miss = 0, []
    for f in facilities:
        cat = f.get("category","")
        if cat not in ("認可保育所（市立）","認可保育所（私立）","地域型保育（認可）"):
            continue
        matched = next(
            (v for k, v in pdf_data.items() if match(k, f["name"])), None
        )
        if matched:
            f["募集人数"] = matched   # {"0歳":0,"1歳":1,...,"計":1}
            f["募集PDF"] = pdf_label
            hit += 1
        else:
            miss.append(f["name"])

    print(f"\nマッチ: {hit} 施設")
    if miss:
        print(f"未マッチ: {len(miss)} 施設")
        for n in miss: print(f"  - {n}")

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(facilities, f, ensure_ascii=False, indent=2)
    print("\ndata.json を更新しました")


if __name__ == "__main__":
    main()
