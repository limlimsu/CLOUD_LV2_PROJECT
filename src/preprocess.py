# -*- coding: utf-8 -*-
"""
전처리: data/cheongju_apt_trade.csv -> data/cheongju_apt_clean.csv
사용법: python src/preprocess.py
"""
import os
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")

INPUT_CSV = os.path.join(DATA, "cheongju_apt_trade.csv")
OUTPUT_CSV = os.path.join(DATA, "cheongju_apt_clean.csv")


def main():
    df = pd.read_csv(INPUT_CSV)
    n0 = len(df)
    print(f"원본: {n0:,}건, 컬럼 {df.shape[1]}개")

    # 1) 거래금액: "8,900"(문자, 만원) -> 정수(만원) + 억원
    df["거래금액_만원"] = (
        df["dealAmount"].astype(str).str.replace(",", "", regex=False).str.strip()
    )
    df["거래금액_만원"] = pd.to_numeric(df["거래금액_만원"], errors="coerce")
    df["거래금액_억"] = (df["거래금액_만원"] / 10000).round(2)

    # 2) 숫자화
    df["전용면적"] = pd.to_numeric(df["excluUseAr"], errors="coerce")
    df["층"] = pd.to_numeric(df["floor"], errors="coerce")
    df["건축년도"] = pd.to_numeric(df["buildYear"], errors="coerce")

    # 3) 거래일자 + 거래연월
    df["거래일자"] = pd.to_datetime(
        dict(year=df["dealYear"], month=df["dealMonth"], day=df["dealDay"]),
        errors="coerce",
    )
    df["거래연월"] = df["거래일자"].dt.to_period("M").astype(str)

    # 4) 파생 컬럼
    df["평수"] = df["전용면적"] / 3.3058
    df["평당가_만원"] = (df["거래금액_만원"] / df["평수"]).round(1)
    df["연식"] = df["거래일자"].dt.year - df["건축년도"]

    # 5) 이상치 / 무효 제거
    if "cdealType" in df.columns:
        cancel = df["cdealType"].astype(str).str.strip()
        is_cancel = cancel.notna() & (cancel != "") & (cancel.str.lower() != "nan")
        before = len(df)
        df = df[~is_cancel]
        print(f"취소거래 제외: {before - len(df):,}건")

    df = df.dropna(subset=["거래금액_만원", "전용면적", "거래일자"])
    df = df[(df["전용면적"] > 0) & (df["거래금액_만원"] > 0)]

    # 6) 컬럼 정리
    keep = [
        "구", "umdNm", "aptNm", "거래일자", "거래연월",
        "거래금액_만원", "거래금액_억", "전용면적", "평수", "평당가_만원",
        "층", "건축년도", "연식", "dealingGbn",
    ]
    keep = [c for c in keep if c in df.columns]
    clean = df[keep].rename(
        columns={"umdNm": "동", "aptNm": "아파트명", "dealingGbn": "거래유형"}
    )
    clean = clean.sort_values("거래일자").reset_index(drop=True)
    clean.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    print(f"\n정제 완료: {n0:,}건 -> {len(clean):,}건 -> {OUTPUT_CSV}")
    print("\n[구별 평균 평당가(만원)]")
    print(clean.groupby("구")["평당가_만원"].mean().round(1)
          .sort_values(ascending=False))


if __name__ == "__main__":
    main()
