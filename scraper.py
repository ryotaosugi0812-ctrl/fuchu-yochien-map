#!/usr/bin/env python3
"""府中市 幼稚園・保育所 認証認可情報スクレイパー"""

import json
import re
import time
import sys
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.city.fuchu.tokyo.jp"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0 (compatible; research bot)"})


def fetch(path: str) -> BeautifulSoup:
    url = BASE_URL + path if path.startswith("/") else path
    resp = SESSION.get(url, timeout=15)
    resp.encoding = resp.apparent_encoding or "utf-8"
    return BeautifulSoup(resp.text, "html.parser")


def extract_address_phone(soup: BeautifulSoup):
    text = soup.get_text(" ", strip=True)
    addr_match = re.search(r'府中市[゠-ヿ぀-ゟ一-鿿\d\-]+[0-9番地号]+', text)
    address = addr_match.group().strip() if addr_match else ""
    phone_match = re.search(r'0\d{1,4}[\-ー]\d{2,4}[\-ー]\d{4}', text)
    phone = phone_match.group().replace("ー", "-").strip() if phone_match else ""
    return address, phone


def scrape_list_page(path: str, category_key: str):
    """リストページから施設名とリンクを収集"""
    soup = fetch(path)
    links = []
    base_dir = "/".join(path.split("/")[:-1]) + "/"
    for a in soup.find_all("a", href=True):
        href = a["href"]
        name = a.get_text(strip=True)
        if not name or href in ("#", "index.html", path):
            continue
        if category_key in href and href.endswith(".html") and "index" not in href:
            full_path = href if href.startswith("/") else base_dir + href
            links.append((name, full_path))
    return links


def scrape_category(list_path: str, facility_type: str, category: str, category_key: str):
    print(f"  スクレイピング中: {facility_type}", flush=True)
    links = scrape_list_page(list_path, category_key)
    facilities = []
    for i, (name, path) in enumerate(links):
        print(f"    [{i+1}/{len(links)}] {name}", flush=True)
        try:
            detail = fetch(path)
            address, phone = extract_address_phone(detail)
            facilities.append({
                "name": name,
                "type": facility_type,
                "category": category,
                "address": address,
                "phone": phone,
                "url": BASE_URL + path,
            })
        except Exception as e:
            print(f"    ERROR: {e}", flush=True)
            facilities.append({
                "name": name,
                "type": facility_type,
                "category": category,
                "address": "",
                "phone": "",
                "url": BASE_URL + path,
            })
        time.sleep(0.4)
    return facilities


def scrape_ninsho():
    """認証保育施設は一覧ページのリンクから個別ページをスクレイピング"""
    print("  スクレイピング中: 認証保育施設", flush=True)
    path = "/shisetu/kosodate/ninsho/index.html"
    soup = fetch(path)
    facilities = []
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)
        if "ninsho/" in href and href.endswith(".html") and "index" not in href:
            full_path = href if href.startswith("/") else "/shisetu/kosodate/ninsho/" + href
            # テキストから種別と施設名を分離 (例: "A型：まなびの森...")
            subtype = ""
            name = text
            if "：" in text:
                parts = text.split("：", 1)
                subtype = parts[0].strip()
                name = parts[1].strip()
            links.append((name, subtype, full_path))

    for i, (name, subtype, detail_path) in enumerate(links):
        print(f"    [{i+1}/{len(links)}] {name}", flush=True)
        try:
            detail = fetch(detail_path)
            address, phone = extract_address_phone(detail)
            facilities.append({
                "name": name,
                "type": "認証保育施設",
                "category": "認証保育所（東京都）",
                "subtype": subtype,
                "address": address,
                "phone": phone,
                "url": BASE_URL + detail_path,
            })
        except Exception as e:
            print(f"    ERROR: {e}", flush=True)
        time.sleep(0.4)
    return facilities


def scrape_kigyo():
    """企業主導型保育施設"""
    print("  スクレイピング中: 企業主導型保育施設", flush=True)
    path = "/shisetu/kosodate/kigyo/index.html"
    try:
        soup = fetch(path)
        facilities = []
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            name = a.get_text(strip=True)
            if name and "kigyo" in href and href.endswith(".html") and "index" not in href:
                full_path = href if href.startswith("/") else "/shisetu/kosodate/kigyo/" + href
                links.append((name, full_path))
        for i, (name, path_) in enumerate(links):
            print(f"    [{i+1}/{len(links)}] {name}", flush=True)
            try:
                detail = fetch(path_)
                address, phone = extract_address_phone(detail)
                facilities.append({
                    "name": name,
                    "type": "企業主導型保育施設",
                    "category": "企業主導型",
                    "address": address,
                    "phone": phone,
                    "url": BASE_URL + path_,
                })
                time.sleep(0.4)
            except Exception as e:
                print(f"    ERROR: {e}", flush=True)
        return facilities
    except Exception as e:
        print(f"  ERROR: {e}", flush=True)
        return []


def scrape_chiiki():
    """地域型保育事業"""
    print("  スクレイピング中: 地域型保育事業", flush=True)
    path = "/shisetu/kosodate/chiikigata/index.html"
    soup = fetch(path)
    facilities = []
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)
        if "chiikigata/" in href and href.endswith(".html") and "index" not in href:
            full_path = href if href.startswith("/") else "/shisetu/kosodate/chiikigata/" + href
            subtype, name = "", text
            if "：" in text:
                parts = text.split("：", 1)
                subtype = parts[0].strip()
                name = parts[1].strip()
            links.append((name, subtype, full_path))

    for i, (name, subtype, detail_path) in enumerate(links):
        print(f"    [{i+1}/{len(links)}] {name}", flush=True)
        try:
            detail = fetch(detail_path)
            address, phone = extract_address_phone(detail)
            facilities.append({
                "name": name,
                "type": "地域型保育事業",
                "category": "地域型保育（認可）",
                "subtype": subtype,
                "address": address,
                "phone": phone,
                "url": BASE_URL + detail_path,
            })
        except Exception as e:
            print(f"    ERROR: {e}", flush=True)
        time.sleep(0.4)
    return facilities


def main():
    all_facilities = []

    print("=== 府中市 幼稚園・保育所 スクレイピング開始 ===", flush=True)

    # 1. 私立幼稚園（認可）
    yochien = scrape_category(
        "/shisetu/kyoiku/watakushiritu/index.html",
        "私立幼稚園",
        "認可幼稚園",
        "watakushiritu/",
    )
    all_facilities.extend(yochien)

    # 2. 市立保育所（認可）
    shiritsu = scrape_category(
        "/shisetu/kosodate/shiritu/index.html",
        "市立保育所",
        "認可保育所（市立）",
        "shiritu/",
    )
    all_facilities.extend(shiritsu)

    # 3. 私立保育園（認可）
    private = scrape_category(
        "/shisetu/kosodate/hoikuen/index.html",
        "私立保育園",
        "認可保育所（私立）",
        "hoikuen/",
    )
    all_facilities.extend(private)

    # 4. 認証保育施設
    ninsho = scrape_ninsho()
    all_facilities.extend(ninsho)

    # 5. 企業主導型保育施設
    kigyo = scrape_kigyo()
    all_facilities.extend(kigyo)

    # 6. 地域型保育事業
    chiiki = scrape_chiiki()
    all_facilities.extend(chiiki)

    print(f"\n合計 {len(all_facilities)} 施設を収集しました", flush=True)

    summary = {}
    for f in all_facilities:
        summary[f["category"]] = summary.get(f["category"], 0) + 1
    for cat, count in sorted(summary.items()):
        print(f"  {cat}: {count}施設", flush=True)

    with open("data.json", "w", encoding="utf-8") as fp:
        json.dump(all_facilities, fp, ensure_ascii=False, indent=2)
    print("\ndata.json を保存しました", flush=True)


if __name__ == "__main__":
    main()
