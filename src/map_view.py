# -*- coding: utf-8 -*-
"""
청주 동별 평균 시세 지도 (Folium) -> output/cheongju_map.html
사용법: python src/map_view.py
"""
import os
import pandas as pd
import folium

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
OUT = os.path.join(BASE, "output")

df = pd.read_csv(os.path.join(DATA, "cheongju_apt_clean.csv"))
geo = pd.read_csv(os.path.join(DATA, "dong_coords.csv")).dropna(subset=["위도", "경도"])

agg = df.groupby("동").agg(
    평당가=("평당가_만원", "mean"),
    평균가억=("거래금액_억", "mean"),
    건수=("거래금액_억", "size"),
).reset_index()
m_df = agg.merge(geo, on="동", how="inner")
print(f"지도에 표시할 동: {len(m_df)}개")


def color(v):
    if v >= 1400: return "red"
    if v >= 1100: return "orange"
    if v >= 900:  return "green"
    return "blue"


m = folium.Map(location=[36.64, 127.49], zoom_start=12, tiles="CartoDB positron")
for _, r in m_df.iterrows():
    popup = (f"<b>{r['동']}</b><br>평당가: {r['평당가']:.0f}만원<br>"
             f"평균 거래가: {r['평균가억']:.2f}억<br>거래: {int(r['건수'])}건")
    folium.CircleMarker(
        location=[r["위도"], r["경도"]],
        radius=5 + (r["건수"] ** 0.5),
        color=color(r["평당가"]), fill=True, fill_opacity=0.6,
        popup=folium.Popup(popup, max_width=200),
        tooltip=f"{r['동']} {r['평당가']:.0f}만원",
    ).add_to(m)

os.makedirs(OUT, exist_ok=True)
out_path = os.path.join(OUT, "cheongju_map.html")
m.save(out_path)
print(f"지도 저장 완료 -> {out_path}")
