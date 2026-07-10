# -*- coding: utf-8 -*-
"""
동 이름 -> 좌표 변환 (카카오 로컬 API, 주소 검색)
data/cheongju_apt_clean.csv -> data/dong_coords.csv
사용법: python src/geocode.py  (한 번만 실행)
"""
import os
import time
import requests
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")

from dotenv import load_dotenv
load_dotenv(os.path.join(BASE, ".env"))
KAKAO_KEY = os.getenv("KAKAO_KEY")

INPUT_CSV = os.path.join(DATA, "cheongju_apt_clean.csv")
OUTPUT_CSV = os.path.join(DATA, "dong_coords.csv")
URL = "https://dapi.kakao.com/v2/local/search/address.json"


def main():
    if KAKAO_KEY.startswith("여기에"):
        print("먼저 KAKAO_KEY 에 REST API 키를 넣어주세요.")
        return

    df = pd.read_csv(INPUT_CSV)
    dongs = sorted(df["동"].dropna().unique())
    print(f"변환할 동: {len(dongs)}개")

    headers = {"Authorization": f"KakaoAK {KAKAO_KEY}"}
    rows = []
    for d in dongs:
        query = f"충청북도 청주시 {d}"
        try:
            r = requests.get(URL, headers=headers,
                             params={"query": query}, timeout=10)
            docs = r.json().get("documents", [])
            if docs:
                rows.append({"동": d,
                             "위도": float(docs[0]["y"]),
                             "경도": float(docs[0]["x"])})
                print(f"  {d}: OK")
            else:
                rows.append({"동": d, "위도": None, "경도": None})
                print(f"  {d}: 좌표 없음")
        except Exception as e:
            rows.append({"동": d, "위도": None, "경도": None})
            print(f"  {d}: 에러 {e}")
        time.sleep(0.15)

    geo = pd.DataFrame(rows)
    geo.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    ok = geo["위도"].notna().sum()
    print(f"\n완료: {ok}/{len(geo)}개 좌표 확보 -> {OUTPUT_CSV}")


if __name__ == "__main__":
    main()