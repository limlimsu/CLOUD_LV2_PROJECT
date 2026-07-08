# 청주 우리동네 시세 🏠

국토교통부 실거래가 API 기반 청주 아파트 시세 데이터 파이프라인 및 시각화 웹 서비스

---

## 프로젝트 개요

청주 4개 구(흥덕구·상당구·서원구·청원구)의 아파트 실거래가 데이터를 수집·가공하여 동네별 시세를 지도와 통계로 제공합니다.

## 아키텍처

```
국토부 실거래가 API (XML)
        │
        ▼
① 수집 (collect.py)
        │ 원본
        ▼
② 저장 Raw (PostgreSQL · apt_trade)
        │
        ▼
③ 가공 (preprocess.py · geocode.py)
        │ 정제
        ▼
④ 저장 정제 (PostgreSQL · apt_clean · dong_coords)
        │
        ▼
⑤ 제공 (Streamlit · 8501)
        │ HTTP
        ▼
사용자 · 웹 브라우저
```

**인프라:** OCI CBNU 컴파트먼트 · Compute VM (2 OCPU / 16GB)  
**DB:** PostgreSQL 16 (VM 내 설치 · `cj_apt_db`)

## 기술 스택

| 역할 | 기술 |
|---|---|
| 데이터 수집 | Python `requests`, 국토부 실거래가 API |
| 가공 | `pandas`, `geopy` (지오코딩) |
| 저장 | PostgreSQL 16 |
| 시각화 | Streamlit, Plotly, Folium |
| 인프라 | Oracle Cloud Infrastructure (OCI) |

## 프로젝트 구조

```
CLOUD_LV2_PROJECT/
├── src/
│   ├── app.py          # Streamlit 웹 앱
│   ├── collect.py      # 국토부 API 수집
│   ├── preprocess.py   # 데이터 정제
│   ├── geocode.py      # 지오코딩
│   └── map_view.py     # 지도 유틸
├── data/               # 로컬 개발용 CSV
├── output/             # EDA 결과물
├── requirements.txt
└── .env                # DB 접속정보 (git 제외)
```

## 로컬 실행

**1. 환경 설정**
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**2. .env 파일 생성**
```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=cj_apt_db
DB_USER=postgres
DB_PASSWORD=<비밀번호>
```

**3. 실행**
```bash
streamlit run src/app.py
```

## 주요 기능

- **우리 동네 탭** — 동 선택 시 월별 시세 추이 및 최근 거래 내역
- **지도 탭** — 동별 평당가를 색상·크기로 표현한 인터랙티브 지도
- **가격 분석 탭** — 면적대·연식·구별 가격 분포
- **시세 추세 탭** — 구별 월평균 평당가 추이 및 거래량
- **거래 조회 탭** — 아파트명·동 검색 및 CSV 다운로드

## 데이터

- **출처:** 국토교통부 아파트 매매 실거래가 공개시스템
- **범위:** 청주시 4개 구 · 2024년 7월 ~ 2025년 6월
- **규모:** 약 11,835건

## 팀

충북대학교 컴퓨터과학과 · Cloud_LV2 팀
