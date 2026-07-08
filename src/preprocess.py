# -*- coding: utf-8 -*-
"""
전처리: data/cheongju_apt_trade.csv -> data/cheongju_apt_clean.csv + PostgreSQL 적재
사용법: python src/preprocess.py
"""
import os
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")

load_dotenv(os.path.join(BASE, ".env"))

INPUT_CSV = os.path.join(DATA, "cheongju_apt_trade.csv")
OUTPUT_CSV = os.path.join(DATA, "cheongju_apt_clean.csv")


def get_engine():
    return create_engine(
        f"postgresql+psycopg2://"
        f"{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
        f"@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}"
        f"/{os.getenv('DB_NAME')}"
    )


def load_to_postgres(clean_df, raw_df):
    """정제 데이터와 원본 데이터를 PostgreSQL에 적재 (기존 데이터 대체)"""
    engine = get_engine()

    # apt_clean 테이블용 컬럼명 매핑 (한글 → 영문)
    clean_for_db = clean_df.rename(columns={
        "구": "gu",
        "동": "dong",
        "아파트명": "apt_name",
        "거래일자": "trade_date",
        "거래연월": "trade_year_month",
        "거래금액_만원": "trade_amount_int",
        "거래금액_억": "trade_amount_float",
        "전용면적": "exclusive_area",
        "평수": "pyeong",
        "평당가_만원": "pyeong_price",
        "층": "floor",
        "건축년도": "build_year",
        "연식": "age",
        "거래유형": "trade_type",
    })

    with engine.begin() as conn:
        clean_for_db.to_sql("apt_clean", conn, if_exists="replace", index=False)
        raw_df.to_sql("apt_trade", conn, if_exists="replace", index=False)

    print(f"PostgreSQL 적재 완료: apt_clean {len(clean_for_db):,}건, apt_trade {len(raw_df):,}건")


def main():
    df = pd.read_csv(INPUT_CSV)
    raw_df = df.copy()
    n0 = len(df)
    print(f"원본: {n0:,}건, 컬럼 {df.shape[1]}개")

    # 1) 거래금액
    df["거래금액_만원"] = (
        df["dealAmount"].astype(str).str.replace(",", "", regex=False).str.strip()
    )
    df["거래금액_만원"] = pd.to_numeric(df["거래금액_만원"], errors="coerce")
    df["거래금액_억"] = (df["거래금액_만원"] / 10000).round(2)

    # 2) 숫자화
    df["전용면적"] = pd.to_numeric(df["excluUseAr"], errors="coerce")
    df["층"] = pd.to_numeric(df["floor"], errors="coerce")
    df["건축년도"] = pd.to_numeric(df["buildYear"], errors="coerce")

    # 3) 거래일자
    df["거래일자"] = pd.to_datetime(
        dict(year=df["dealYear"], month=df["dealMonth"], day=df["dealDay"]),
        errors="coerce",
    )
    df["거래연월"] = df["거래일자"].dt.to_period("M").astype(str)

    # 4) 파생
    df["평수"] = df["전용면적"] / 3.3058
    df["평당가_만원"] = (df["거래금액_만원"] / df["평수"]).round(1)
    df["연식"] = df["거래일자"].dt.year - df["건축년도"]

    # 5) 이상치 제거
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

    # 7) PostgreSQL 적재
    load_to_postgres(clean, raw_df)


if __name__ == "__main__":
    main()