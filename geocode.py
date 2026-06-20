#!/usr/bin/env python3
"""住所を国土地理院APIでジオコーディングしてdata.jsonにlat/lngを追記"""

import json
import time
import requests

GSI_URL = "https://msearch.gsi.go.jp/address-search/AddressSearch"


def geocode(address: str):
    query = "東京都" + address if not address.startswith("東京") else address
    try:
        resp = requests.get(GSI_URL, params={"q": query}, timeout=10)
        results = resp.json()
        if results:
            coords = results[0]["geometry"]["coordinates"]
            return float(coords[1]), float(coords[0])  # [lng, lat] -> (lat, lng)
    except Exception as e:
        print(f"    ERROR: {e}")
    return None, None


def main():
    with open("data.json", encoding="utf-8") as f:
        data = json.load(f)

    total = len(data)
    hit = 0
    for i, facility in enumerate(data):
        if facility.get("lat"):
            hit += 1
            print(f"[{i+1}/{total}] SKIP {facility['name']}")
            continue
        address = facility.get("address", "")
        if not address:
            print(f"[{i+1}/{total}] 住所なし: {facility['name']}")
            continue
        lat, lng = geocode(address)
        if lat:
            facility["lat"] = lat
            facility["lng"] = lng
            hit += 1
            print(f"[{i+1}/{total}] OK  {facility['name']} -> {lat:.5f},{lng:.5f}")
        else:
            print(f"[{i+1}/{total}] MISS {facility['name']} ({address})")
        time.sleep(0.3)

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n完了: {hit}/{total} 件ジオコーディング済み")


if __name__ == "__main__":
    main()
