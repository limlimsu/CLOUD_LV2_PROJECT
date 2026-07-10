# -*- coding: utf-8 -*-
"""
청주 우리동네 시세 - Streamlit 웹 대시보드

PostgreSQL의 apt_clean 테이블을 읽어 청주 4개 구의 아파트 실거래가를
5개 탭(우리 동네, 지도, 가격 분석, 시세 추세, 거래 조회)으로 시각화한다.

사용법: streamlit run src/app.py
"""
import os
import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium
import plotly.express as px
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="청주 우리동네 시세", page_icon="🏠", layout="wide")

GREEN = "#0F6E56"
BLUE = "#185FA5"
GU_COLORS = {"흥덕구": "#0F6E56", "상당구": "#185FA5",
             "서원구": "#BA7517", "청원구": "#993C1D"}


def get_engine():
    """PostgreSQL 접속 엔진 생성 (.env의 DB_* 값 사용)."""
    return create_engine(
        f"postgresql+psycopg2://"
        f"{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
        f"@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}"
        f"/{os.getenv('DB_NAME')}"
    )


@st.cache_data(ttl=3600)
def load_data():
    """apt_clean 테이블 조회. 영문 컬럼을 한글 별칭으로 매핑."""
    engine = get_engine()
    query = """
        SELECT
            gu            AS "구",
            dong          AS "동",
            apt_name      AS "아파트명",
            trade_date    AS "거래일자",
            trade_year_month AS "거래연월",
            trade_amount_float AS "거래금액_억",
            exclusive_area AS "전용면적",
            pyeong_price  AS "평당가_만원",
            floor         AS "층",
            build_year    AS "건축년도",
            age           AS "연식",
            trade_type    AS "거래유형"
        FROM apt_clean
    """
    df = pd.read_sql(query, engine)
    df["거래일자"] = pd.to_datetime(df["거래일자"])
    return df


@st.cache_data(ttl=3600)
def load_coords():
    """동별 좌표 조회 (지도 시각화용)."""
    engine = get_engine()
    query = """
        SELECT
            dong      AS "동",
            latitude  AS "위도",
            longitude AS "경도"
        FROM dong_coords
    """
    return pd.read_sql(query, engine).dropna(subset=["위도", "경도"])


df = load_data()
geo = load_coords()

# ---------------- 헤더 ----------------
st.title("🏠 청주 우리동네 시세")
st.caption("국토교통부 실거래가 기반 · 청주 4개 구 · 최근 1년")

with st.expander("📖 사이트 소개 · 사용법"):
    st.markdown(
        "**소개** — 청주 지역 아파트 실거래가를 공공데이터로 수집·가공해 동네별 시세를 "
        "지도와 통계로 제공하는 데이터 파이프라인 프로젝트. 국토교통부 실거래가 API 기반, "
        "청주 4개 구 최근 1년 거래를 다룸.\n\n"
        "**사용법** — 왼쪽 필터로 조건 선택 시 전체 화면이 갱신됨. "
        "`🏠 우리 동네` 탭에서 동 선택 시 해당 동의 시세·추세·최근 거래 확인 가능.\n\n"
        "**용어** — 평당가: 1평(3.3㎡)당 가격(크기 다른 아파트의 공정 비교 기준) · "
        "전용면적: 실사용 공간(㎡), 84㎡ ≈ 약 25평")

# ---------------- 사이드바 필터 ----------------
st.sidebar.header("🔎 조건 선택")
st.sidebar.caption("조건을 고르면 지도·통계가 갱신됩니다")

gu_sel = st.sidebar.multiselect(
    "구", sorted(df["구"].unique()), default=sorted(df["구"].unique()),
    help="보고 싶은 구 선택")

if "거래유형" in df.columns:
    types = [t for t in df["거래유형"].dropna().unique()]
    type_sel = st.sidebar.multiselect(
        "거래유형", types, default=types,
        help="중개거래=공인중개사 통한 거래, 직거래=개인 간 직접 거래")
else:
    type_sel = None

dmin, dmax = df["거래일자"].min().date(), df["거래일자"].max().date()
date_sel = st.sidebar.date_input("거래 기간", (dmin, dmax),
                                 min_value=dmin, max_value=dmax)

amax = int(df["전용면적"].max()) + 1
area_sel = st.sidebar.slider("전용면적 (㎡)", 0, amax, (0, amax),
                             help="실사용 공간. 84㎡ ≈ 약 25평")

pmax = float(df["거래금액_억"].max())
price_sel = st.sidebar.slider("거래금액 (억)", 0.0, round(pmax, 1),
                              (0.0, round(pmax, 1)))

# ---------------- 필터 적용 ----------------
f = df[df["구"].isin(gu_sel)
       & df["전용면적"].between(*area_sel)
       & df["거래금액_억"].between(*price_sel)]
if type_sel is not None:
    f = f[f["거래유형"].isin(type_sel)]
if isinstance(date_sel, (list, tuple)) and len(date_sel) == 2:
    d0, d1 = date_sel
    f = f[(f["거래일자"].dt.date >= d0) & (f["거래일자"].dt.date <= d1)]

if f.empty:
    st.warning("조건에 맞는 거래가 없습니다. 왼쪽 필터를 조정해 주세요.")
    st.stop()

# ---------------- 요약 KPI ----------------
k1, k2, k3, k4 = st.columns(4)
k1.metric("거래 건수", f"{len(f):,}건")
k2.metric("평균 거래가", f"{f['거래금액_억'].mean():.2f}억")
k3.metric("평균 평당가", f"{f['평당가_만원'].mean():.0f}만원", help="1평당 평균 가격")
k4.metric("최고 거래가", f"{f['거래금액_억'].max():.1f}억")

gu_price = f.groupby("구")["평당가_만원"].mean()
if len(gu_price) >= 2:
    top_gu, low_gu = gu_price.idxmax(), gu_price.idxmin()
    ratio = gu_price.max() / gu_price.min()
    st.info(f"평당가 최고 **{top_gu}** {gu_price.max():.0f}만원, "
            f"최저 **{low_gu}** {gu_price.min():.0f}만원 · 약 {ratio:.1f}배 차이")

# ---------------- 탭 ----------------
tab0, tab1, tab2, tab3, tab4 = st.tabs(
    ["🏠 우리 동네", "🗺️ 지도", "💰 가격 분석", "📈 시세 추세", "🔍 거래 조회"])

# ===== 탭0: 우리 동네 =====
with tab0:
    st.subheader("우리 동네 시세")
    dong_list = f["동"].value_counts().index.tolist()
    d = st.selectbox("동 선택", dong_list, help="거래 많은 동 순 정렬")
    sub = f[f["동"] == d]

    cheongju_pp = f["평당가_만원"].mean()
    dong_pp = sub["평당가_만원"].mean()
    diff = (dong_pp / cheongju_pp - 1) * 100

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("거래 건수", f"{len(sub):,}건")
    m2.metric("평균 거래가", f"{sub['거래금액_억'].mean():.2f}억")
    m3.metric("평당가", f"{dong_pp:.0f}만원", delta=f"청주 평균 대비 {diff:+.0f}%")
    m4.metric("최근 거래일", f"{sub['거래일자'].max():%y.%m.%d}")

    cc1, cc2 = st.columns([3, 2])
    with cc1:
        st.markdown("**월별 평균 거래가 추이**")
        mt = sub.groupby("거래연월")["거래금액_억"].mean().reset_index()
        fig = px.line(mt, x="거래연월", y="거래금액_억", markers=True,
                      color_discrete_sequence=[GREEN])
        fig.update_layout(height=300, yaxis_title="평균 거래가 (억)", xaxis_title="")
        st.plotly_chart(fig, use_container_width=True)
    with cc2:
        st.markdown("**최근 거래 내역**")
        recent = (sub.sort_values("거래일자", ascending=False)
                  .head(8)[["거래일자", "아파트명", "거래금액_억", "전용면적"]])
        recent["거래일자"] = recent["거래일자"].dt.strftime("%y.%m.%d")
        st.dataframe(recent, use_container_width=True, hide_index=True)

# ===== 탭1: 지도 =====
with tab1:
    st.subheader("동네별 시세 지도")
    st.caption("색 = 시세 수준, 원 크기 = 거래량 · 마우스 오버/클릭 시 상세")
    st.caption("🔴 1400↑  ·  🟠 1100–1400  ·  🟢 900–1100  ·  🔵 900↓  (만원/평)")

    agg = (f.groupby("동").agg(평당가=("평당가_만원", "mean"),
                               평균가억=("거래금액_억", "mean"),
                               건수=("거래금액_억", "size")).reset_index())
    m_df = agg.merge(geo, on="동", how="inner")

    def color(v):
        if v >= 1400: return "#D64545"
        if v >= 1100: return "#E08A2B"
        if v >= 900:  return "#2E9E6B"
        return "#3B7DD8"

    m = folium.Map(location=[36.64, 127.49], zoom_start=12, tiles="CartoDB positron")
    for _, r in m_df.iterrows():
        radius = min(4 + (r["건수"] ** 0.4), 15)
        popup = (f"<b>{r['동']}</b><br>평당가 {r['평당가']:.0f}만원<br>"
                 f"평균 {r['평균가억']:.2f}억 · {int(r['건수'])}건")
        folium.CircleMarker(
            location=[r["위도"], r["경도"]], radius=radius,
            color=color(r["평당가"]), weight=1,
            fill=True, fill_color=color(r["평당가"]), fill_opacity=0.55,
            tooltip=f"{r['동']} · 평당 {r['평당가']:.0f}만원",
            popup=folium.Popup(popup, max_width=200),
        ).add_to(m)
    st_folium(m, width=None, height=470)

# ===== 탭2: 가격 분석 =====
with tab2:
    st.subheader("가격 결정 요인")

    st.markdown("**① 면적대별 평균 거래가**")
    st.caption("면적 구간별 평균 거래가")
    tmp2 = f.copy()
    tmp2["면적대"] = pd.cut(
        tmp2["전용면적"], bins=[0, 60, 85, 102, 135, 100000],
        labels=["60㎡↓", "60~85㎡", "85~102㎡", "102~135㎡", "135㎡↑"])
    area_bar = (tmp2.groupby("면적대", observed=True)["거래금액_억"]
                .mean().round(2).reset_index())
    fig = px.bar(area_bar, x="면적대", y="거래금액_억", text_auto=True,
                 color_discrete_sequence=[GREEN])
    fig.update_layout(yaxis_title="평균 거래가 (억)", xaxis_title="", height=360)
    st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**② 연식대별 평균 평당가**")
        tmp = f.copy()
        tmp["연식대"] = pd.cut(tmp["연식"], bins=[-1, 5, 10, 20, 30, 100],
                               labels=["5년↓", "6-10년", "11-20년", "21-30년", "30년↑"])
        age = (tmp.groupby("연식대", observed=True)["평당가_만원"].mean()
               .round(0).reset_index())
        fig = px.bar(age, x="연식대", y="평당가_만원", color_discrete_sequence=[BLUE],
                     text_auto=True)
        fig.update_layout(yaxis_title="평당가 (만원/평)", xaxis_title="", height=330)
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.markdown("**③ 구별 평당가 분포**")
        st.caption("상자 길이 = 구 내 가격 편차")
        fig = px.box(f, x="구", y="평당가_만원", color="구", color_discrete_map=GU_COLORS)
        fig.update_layout(showlegend=False, yaxis_title="평당가 (만원/평)",
                          xaxis_title="", height=330)
        st.plotly_chart(fig, use_container_width=True)

# ===== 탭3: 시세 추세 =====
with tab3:
    st.subheader("월별 시세 추세")
    st.caption("선 = 구별 월평균 평당가")

    trend = (f.groupby(["거래연월", "구"])["평당가_만원"].mean().reset_index())
    fig = px.line(trend, x="거래연월", y="평당가_만원", color="구",
                  color_discrete_map=GU_COLORS, markers=True)
    fig.update_layout(height=400, yaxis_title="평당가 (만원/평)", xaxis_title="",
                      legend_title_text="구")
    st.plotly_chart(fig, use_container_width=True)

    monthly = f.groupby("거래연월")["평당가_만원"].mean()
    if len(monthly) >= 2 and monthly.iloc[0] > 0:
        chg = (monthly.iloc[-1] - monthly.iloc[0]) / monthly.iloc[0] * 100
        word = "상승" if chg >= 0 else "하락"
        st.info(f"{monthly.index[0]}~{monthly.index[-1]} 청주 전체 평균 평당가 "
                f"약 {abs(chg):.1f}% {word}")

    st.markdown("**월별 거래량**")
    st.caption("거래 건수 = 시장 활발도 지표")
    vol = f.groupby("거래연월").size().reset_index(name="거래량")
    fig2 = px.bar(vol, x="거래연월", y="거래량", color_discrete_sequence=["#9CA3AF"])
    fig2.update_layout(height=260, yaxis_title="거래 건수", xaxis_title="")
    st.plotly_chart(fig2, use_container_width=True)

# ===== 탭4: 거래 조회 =====
with tab4:
    st.subheader("거래 내역 조회")
    st.caption("아파트명·동 검색 후 결과 다운로드 가능")
    q = st.text_input("아파트명 또는 동 검색", placeholder="예: 지웰시티, 복대동")
    show = f
    if q:
        show = f[f["아파트명"].str.contains(q, na=False)
                 | f["동"].str.contains(q, na=False)]
    cols = ["거래일자", "구", "동", "아파트명", "거래금액_억", "전용면적",
            "평당가_만원", "층", "건축년도", "거래유형"]
    cols = [c for c in cols if c in show.columns]
    view = show[cols].sort_values("거래일자", ascending=False)

    st.caption(f"검색 결과: {len(view):,}건")
    st.dataframe(view, use_container_width=True, hide_index=True)

    csv = view.to_csv(index=False).encode("utf-8-sig")
    st.download_button("📥 조회 결과 CSV 다운로드", csv,
                       "cheongju_apt_filtered.csv", "text/csv")
