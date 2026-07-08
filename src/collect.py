# -*- coding: utf-8 -*-
"""
청주 아파트 매매 실거래가 수집 -> data/cheongju_apt_trade.csv
사용법: python src/collect.py
"""
import os
import time
import requests
import pandas as pd
import xml.etree.ElementTree as ET
from datetime import datetime
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")

load_dotenv(os.path.join(BASE, ".env"))
SERVICE_KEY = os.getenv("SERVICE_KEY")

DISTRICTS = {
    "43111": "상당구",
    "43112": "서원구",
    "43113": "흥덕구",
    "43114": "청원구",
}
# 현재 시점에서 2개월 전을 마지막 계약월로 사용
# (국토부 API는 계약 후 30일 이내 신고 데이터라 최근 1~2개월은 불완전)
END_YM = (datetime.now() - relativedelta(months=2)).strftime("%Y%m")
MONTHS = 12
OUTPUT_CSV = os.path.join(DATA, "cheongju_apt_trade.csv")
# ====================================

ENDPOINT = ("https://apis.data.go.kr/1613000/"
            "RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev")


def month_list(end_ym, n):
    y, m = int(end_ym[:4]), int(end_ym[4:6])
    out = []
    for _ in range(n):
        out.append(f"{y}{m:02d}")
        m -= 1
        if m == 0:
            m, y = 12, y - 1
    return list(reversed(out))


def fetch(lawd_cd, deal_ymd, max_retries=3):
    rows, page = [], 1
    while True:
        params = {
            "serviceKey": SERVICE_KEY,
            "LAWD_CD": lawd_cd,
            "DEAL_YMD": deal_ymd,
            "pageNo": page,
            "numOfRows": 1000,
        }
        # 재시도 로직
        r = None
        for attempt in range(max_retries):
            try:
                r = requests.get(ENDPOINT, params=params, timeout=60)
                break
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                wait = 2 ** attempt
                print(f"  [재시도 {attempt+1}/{max_retries}] {lawd_cd}/{deal_ymd} p{page}: {e.__class__.__name__}, {wait}초 대기")
                time.sleep(wait)
        if r is None:
            print(f"  [실패] {lawd_cd}/{deal_ymd} p{page} — 재시도 소진, 건너뜀")
            break

        r.encoding = "utf-8"
        try:
            root = ET.fromstring(r.text)
        except ET.ParseError:
            print(f"  [경고] {lawd_cd}/{deal_ymd} XML 파싱 실패: {r.text[:150]}")
            break

        code = root.findtext(".//resultCode")
        if code is None:
            msg = (root.findtext(".//returnAuthMsg")
                   or root.findtext(".//resultMsg") or r.text[:150])
            print(f"  [경고] {lawd_cd}/{deal_ymd} 예상치 못한 응답: {msg}")
            break
        if code not in ("000", "00"):
            print(f"  [경고] {lawd_cd}/{deal_ymd} 응답코드 {code}: "
                  f"{root.findtext('.//resultMsg')}")
            break

        items = root.findall(".//item")
        for it in items:
            rows.append({child.tag: (child.text or "").strip() for child in it})

        total = int(root.findtext(".//totalCount") or 0)
        if not items or page * 1000 >= total:
            break
        page += 1
        time.sleep(0.2)
    return rows


def main():
    if SERVICE_KEY.startswith("여기에"):
        print("먼저 SERVICE_KEY 에 인증키를 넣어주세요.")
        return
    os.makedirs(DATA, exist_ok=True)

    months = month_list(END_YM, MONTHS)
    print(f"수집 기간: {months[0]} ~ {months[-1]} ({len(months)}개월) / "
          f"지역 {len(DISTRICTS)}개")

    all_rows = []
    for lawd_cd, gu in DISTRICTS.items():
        for ym in months:
            rows = fetch(lawd_cd, ym)
            for row in rows:
                row["구"] = gu
            all_rows.extend(rows)
            print(f"  {gu}({lawd_cd}) {ym}: {len(rows)}건")
            time.sleep(0.2)

    if not all_rows:
        print("수집된 데이터가 없습니다. 인증키/기간을 확인하세요.")
        return

    df = pd.DataFrame(all_rows)
    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    print(f"\n완료: 총 {len(df):,}건 -> {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
