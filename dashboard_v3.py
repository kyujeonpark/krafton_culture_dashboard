"""
문화시설 빅데이터 대시보드 v2
5페이지 구조: 사이드바 THEME 버튼으로 페이지 전환
현재 구현: Page 3 — 매출 분석
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import folium
from streamlit_folium import st_folium
from pathlib import Path
import re
import json
import urllib.request
import warnings
warnings.filterwarnings("ignore")

# 스크립트 위치 기준으로 상대경로 고정 (어디서 실행해도 CSV를 찾도록)
BASE_DIR = Path(__file__).resolve().parent

# ── 기본 설정 ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="문화시설 빅데이터 대시보드",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 스타일 ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* 전체 배경 */
[data-testid="stAppViewContainer"] { background: #F4F5F7; }

/* 상단 헤더 — 배경색만 맞추기 (숨기지 않음, 사이드바 토글 유지) */
header[data-testid="stHeader"] {
    background: #F4F5F7 !important;
    border-bottom: none !important;
}

/* 상단/하단 여백 (FHD 기준 — 헤더 높이 약 60px 확보) */
.block-container {
    padding-top: 4.5rem !important;
    padding-bottom: 0.5rem !important;
    max-width: 100% !important;
}
[data-testid="stVerticalBlock"] > div { gap: 0.5rem !important; }

/* 사이드바 — 흰색 테마 */
[data-testid="stSidebar"] { background: #FFFFFF !important; border-right: 1px solid #EDEEF2; }
[data-testid="stSidebar"] * { color: #2D2D3A !important; }
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3, [data-testid="stSidebar"] h4,
[data-testid="stSidebar"] h5 { color: #A05AFF !important; }
[data-testid="stSidebar"] hr { border-color: #EDEEF2 !important; margin: 0.6rem 0 !important; }

/* 사이드바 버튼 — 리스트 스타일 */
[data-testid="stSidebar"] .stButton > button {
    background: transparent !important;
    color: #6B6B7D !important;
    border: none !important;
    border-radius: 6px !important;
    text-align: left !important;
    justify-content: flex-start !important;
    padding: 9px 14px !important;
    margin: 1px 0 !important;
    font-size: 0.88rem !important;
    font-weight: 500 !important;
    box-shadow: none !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: #F5F2FF !important;
    color: #A05AFF !important;
}
[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background: transparent !important;
    color: #A05AFF !important;
    font-weight: 700 !important;
    border-left: 3px solid #A05AFF !important;
    border-radius: 0 6px 6px 0 !important;
}

/* KPI 그라디언트 카드 */
.kpi-card {
    border-radius: 14px; padding: 22px 24px;
    color: #fff; position: relative; overflow: hidden;
    box-shadow: 0 4px 14px rgba(0,0,0,0.08);
    min-height: 120px;
}
.kpi-card::before {
    content: ""; position: absolute; top: -30px; right: -30px;
    width: 140px; height: 140px; border-radius: 50%;
    background: rgba(255,255,255,0.12);
}
.kpi-card::after {
    content: ""; position: absolute; bottom: -40px; right: 20px;
    width: 100px; height: 100px; border-radius: 50%;
    background: rgba(255,255,255,0.08);
}
.kpi-label { font-size: 0.88rem; font-weight: 600; opacity: 0.95; margin-bottom: 10px; position: relative; z-index: 1; }
.kpi-value { font-size: 2.0rem; font-weight: 800; line-height: 1.1; position: relative; z-index: 1; }
.kpi-unit  { font-size: 0.72rem; font-weight: 500; opacity: 0.85; margin-left: 4px; }
.kpi-sub   { font-size: 0.72rem; opacity: 0.85; margin-top: 8px; position: relative; z-index: 1; }

/* 지도 라벨 */
.map-label { text-align: center; font-size: 0.85rem; font-weight: 700; margin-bottom: 6px; }

/* 주석 영역 */
.note-box {
    background: #FAFAFA; border-left: 3px solid #E0E0E0;
    padding: 8px 14px; border-radius: 4px;
    font-size: 0.72rem; color: #888; line-height: 1.8;
}
</style>
""", unsafe_allow_html=True)

# ── 상수 ───────────────────────────────────────────────────────────────────
AREAS = ["성수동", "이태원한남", "홍대합정"]
AREA_COLORS = {"성수동": "#A05AFF", "이태원한남": "#FE9496", "홍대합정": "#1BCFB4"}
AREA_CENTERS = {
    "성수동":   [37.5445, 127.0557],
    "이태원한남": [37.5340, 126.9944],
    "홍대합정": [37.5503, 126.9218],
}

# Page 1 — 네이버/공공 area명 → 표준 area명 매핑
AREA_NORM = {"성수": "성수동", "이태원한남": "이태원한남", "홍대": "홍대합정"}

# ── 통합 4개 카테고리 ───────────────────────────────────────────────────────
UNIFIED_CATS = ["전시·관람", "공연·극장", "복합·체험", "도서·독립"]

UNIFIED_CAT_COLORS = {
    "전시·관람": "#2563EB",  # 다크 블루
    "공연·극장": "#EA580C",  # 번트 오렌지
    "복합·체험": "#65A30D",  # 올리브 그린
    "도서·독립": "#CA8A04",  # 다크 앰버
}

# 소스별 → 통합 카테고리 매핑
NAVER_TO_UNIFIED = {
    "전시·갤러리":   "전시·관람",
    "공연·극장":    "공연·극장",
    "복합·체험":    "복합·체험",
    "창작·공방":    "복합·체험",
    "서점·독립문화": "도서·독립",
}
PUBLIC_TO_UNIFIED = {
    "전시·갤러리":  "전시·관람",
    "박물관/기념관": "전시·관람",
    "공연장":      "공연·극장",
    "복합·생활문화": "복합·체험",
    "도서관":      "도서·독립",
}

# 통합 카테고리 주석
UNIFIED_CAT_NOTE = {
    "전시·관람": {
        "네이버": "갤러리·화랑, 미술관, 전시관, 갤러리카페, 박물관, 박람회 등 (전시·갤러리 분류)",
        "공공":   "서울시 등록 미술관·갤러리 + 박물관·기념관·가옥 등",
    },
    "공연·극장": {
        "네이버": "공연장, 공연기획사, 공연·연극시설, 영화관, 극단, 라이브카페 등",
        "공공":   "서울시 등록 공연장 + 문화예술회관 + 라이브홀·스테이지(드림홀, 벨로주, 라디오가가 등)",
    },
    "복합·체험": {
        "네이버": "복합문화공간, 관람·체험, 팝업스토어, 방탈출카페, 공방, 스튜디오, 문화·예술단체 등",
        "공공":   "복합문화공간, 생활문화센터, 아트라이브러리, 문화원 등 (원분류 '기타'·'문화원' 포함)",
    },
    "도서·독립": {
        "네이버": "서점, 독립서점, 북카페, 문학, 국가유산, 클럽 등",
        "공공":   "공립 도서관, 대학 도서관, 평생학습관",
    },
}
QUARTER_ORDER = ["2024Q1","2024Q2","2024Q3","2024Q4",
                 "2025Q1","2025Q2","2025Q3","2025Q4","2026Q1"]

# ── 데이터 로드 ────────────────────────────────────────────────────────────
@st.cache_data
def load_page1_data():
    naver  = pd.read_csv(BASE_DIR / "culture_data_clean.csv", encoding="utf-8-sig")
    public = pd.read_csv(BASE_DIR / "서울시_공공문화시설_10개동.csv", encoding="utf-8-sig")
    # area 정규화
    naver["area_std"]  = naver["area"].map(AREA_NORM)
    public["area_std"] = public["area"].map(AREA_NORM)

    # 공공 카테고리 재분류
    PERF_KW = ["홀", "스테이지", "Stage", "STAGE", "라이브", "클럽", "인디팍", "벨로주", "가가", "FIVE"]
    def reclassify_public(row):
        sub = row["소분류"]
        nm  = row["시설명"]
        if sub in ["공연장", "문화예술회관"]:
            return "공연장"
        if sub == "미술관/갤러리":
            return "전시·갤러리"
        if sub == "박물관/기념관":
            return "박물관/기념관"
        if sub == "도서관":
            return "도서관"
        # 기타·문화원 → 시설명 키워드로 분류
        if any(k in nm for k in PERF_KW):
            return "공연장"
        return "복합·생활문화"

    public["cat_std"] = public.apply(reclassify_public, axis=1)

    # 통합 카테고리 매핑
    naver["cat_unified"]  = naver["category_main"].map(NAVER_TO_UNIFIED)
    public["cat_unified"] = public["cat_std"].map(PUBLIC_TO_UNIFIED)

    return naver, public

def _centroid(feature):
    """GeoJSON feature의 좌표 centroid를 [lat, lon]으로 반환."""
    coords = feature["geometry"]["coordinates"]
    geo_type = feature["geometry"]["type"]
    pts = []
    if geo_type == "Polygon":
        pts = coords[0]
    elif geo_type == "MultiPolygon":
        for poly in coords:
            pts.extend(poly[0])
    if not pts:
        return [37.55, 127.0]
    avg_lon = sum(p[0] for p in pts) / len(pts)
    avg_lat = sum(p[1] for p in pts) / len(pts)
    return [avg_lat, avg_lon]


@st.cache_data
def load_local_people():
    """
    Page 2(생활인구)용 데이터 로드.

    - 소스: LOCAL_PEOPLE_DONG_three_zones_merged_202503_202602.csv (동 단위/시간대 단위)
    - 주요 컬럼(가정): 기준일ID(YYYYMMDD), 시간대구분, 행정동명, 총생활인구수, zone, data_ym
    - 주의: 기준일ID가 float로 저장된 경우가 있어, 숫자→int→str 변환 후 날짜 파싱.
    """
    lp = pd.read_csv(
        BASE_DIR / "LOCAL_PEOPLE_DONG_three_zones_merged_202503_202602.csv",
        encoding="utf-8-sig",
    )
    lp["기준일ID"] = (
        pd.to_numeric(lp["기준일ID"], errors="coerce")
        .fillna(0)
        .astype(int)
        .astype(str)
    )
    lp["date"] = pd.to_datetime(lp["기준일ID"], format="%Y%m%d", errors="coerce")
    lp["총생활인구수"] = pd.to_numeric(lp["총생활인구수"], errors="coerce").fillna(0)
    lp["data_ym"] = lp["data_ym"].astype(str)
    return lp

@st.cache_data
def load_data():
    stores = pd.read_csv(BASE_DIR / "stores_master.csv", encoding="utf-8-sig")
    sales  = pd.read_csv(BASE_DIR / "sales_timeseries.csv", encoding="utf-8-sig")

    # ── 업종 카테고리 통합 매핑 (스포츠 등 분리된 항목 → 공통 카테고리) ──
    CAT_MI_NORM = {
        # 스포츠 계열 → 복합·체험으로 통합
        "스포츠": "복합·체험",
        "스포츠시설": "복합·체험",
        "스포츠/레저": "복합·체험",
        "레저": "복합·체험",
        # 기존 카테고리 명칭 정규화
        "전시·갤러리":   "전시·관람",
        "박물관/기념관":  "전시·관람",
        "공연장":        "공연·극장",
        "공연·극장":     "공연·극장",
        "복합·체험":     "복합·체험",
        "복합·생활문화":  "복합·체험",
        "도서관":        "도서·독립",
        "서점·독립문화":  "도서·독립",
    }
    stores["cat_mi"] = stores["cat_mi"].map(
        lambda x: CAT_MI_NORM.get(x, x) if pd.notna(x) else x
    )

    sales["ym_str"]  = sales["ym"].astype(str)
    sales["year"]    = sales["ym_str"].str[:4].astype(int)
    sales["month"]   = sales["ym_str"].str[4:6].astype(int)
    sales["quarter"] = (sales["year"].astype(str) + "Q"
                        + ((sales["month"] - 1) // 3 + 1).astype(str))

    sales = sales.merge(
        stores[["store_id","lat","lon","cat_mi","area"]].drop_duplicates("store_id"),
        on="store_id", how="left", suffixes=("", "_s")
    )
    for col in ["area", "cat_mi"]:
        if col+"_s" in sales.columns:
            sales[col] = sales[col].fillna(sales[col+"_s"])
            sales.drop(columns=[col+"_s"], inplace=True)

    return stores, sales


@st.cache_data
def load_consumer_region():
    df = pd.read_csv(BASE_DIR / "consumer_region.csv", encoding="utf-8-sig")
    df["ym"] = df["ym"].astype(str)
    df["visit_cnt"] = pd.to_numeric(df["visit_cnt"], errors="coerce").fillna(0)
    df["region_code"] = df["region_code"].astype(str)
    df["region_len"] = df["region_code"].str.len()
    return df


@st.cache_data
def load_hjd_geojson():
    """
    전국 행정동 경계를 로드한다.
    - 우선 로컬 파일 사용
    - 없으면 공개 저장소에서 1회 다운로드 후 로컬 저장
    """
    local_geo = BASE_DIR / "HangJeongDong_ver20241001.geojson"
    if not local_geo.exists():
        url = "https://raw.githubusercontent.com/vuski/admdongkor/master/ver20241001/HangJeongDong_ver20241001.geojson"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = resp.read().decode("utf-8")
        local_geo.write_text(data, encoding="utf-8")
    with open(local_geo, encoding="utf-8") as f:
        return json.load(f)

stores, sales = load_data()

# ── 사이드바 ───────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        "<div style='padding:2px 4px 8px 8px'>"
        "<div style='font-size:3.6rem; font-weight:900; color:#A05AFF; letter-spacing:-0.03em; line-height:1.0'>Culture</div>"
        "<div style='font-size:0.7rem; color:#9A9AAA; margin-top:4px; letter-spacing:0.04em'>Seoul Big Data Dashboard</div>"
        "</div>",
        unsafe_allow_html=True
    )
    st.markdown("---")
    st.markdown(
        "<div style='font-size:0.68rem; color:#A0A0B0; padding:0 4px 4px 4px; letter-spacing:0.1em'>THEMES</div>",
        unsafe_allow_html=True
    )

    pages = [
        ("1", "장소 공급 현황"),
        ("2", "생활인구"),
        ("3", "매출 분석"),
        ("4", "방문자 출신지"),
        ("5", "시설 순위"),
    ]

    if "page" not in st.session_state:
        st.session_state.page = "3"

    for pid, plabel in pages:
        is_active = st.session_state.page == pid
        if st.button(plabel, key=f"page_btn_{pid}", use_container_width=True,
                     type="primary" if is_active else "secondary"):
            st.session_state.page = pid
            st.rerun()

    st.markdown("---")

    # Page 1 전용 서브필터
    if st.session_state.get("page") == "1":
        st.markdown(
            "<div style='font-size:0.68rem; color:#A0A0B0; padding:4px 4px 4px 4px; "
            "letter-spacing:0.1em; border-top:1px solid #EDEEF2; padding-top:10px'>데이터 소스</div>",
            unsafe_allow_html=True
        )
        if "src1" not in st.session_state:
            st.session_state.src1 = "네이버"
        t_n = "primary" if st.session_state.src1 == "네이버" else "secondary"
        t_p = "primary" if st.session_state.src1 == "공공" else "secondary"
        if st.button("네이버 플레이스", key="src1_n", type=t_n, use_container_width=True):
            st.session_state.src1 = "네이버"; st.rerun()
        if st.button("공공 문화시설", key="src1_p", type=t_p, use_container_width=True):
            st.session_state.src1 = "공공"; st.rerun()

        st.markdown(
            "<div style='font-size:0.68rem; color:#A0A0B0; padding:10px 4px 2px 4px; letter-spacing:0.06em'>카테고리 필터</div>",
            unsafe_allow_html=True
        )
        cat1_opts = ["전체"] + UNIFIED_CATS
        if "cat1_filter" not in st.session_state:
            st.session_state.cat1_filter = "전체"
        chosen_cat = st.selectbox(
            "", cat1_opts,
            index=cat1_opts.index(st.session_state.cat1_filter),
            key="cat1_box", label_visibility="collapsed"
        )
        if chosen_cat != st.session_state.cat1_filter:
            st.session_state.cat1_filter = chosen_cat; st.rerun()
        st.markdown("---")

    # Page 2 전용 서브필터 — 차트 보기 + 공간범위
    if st.session_state.get("page") == "2":
        st.markdown(
            "<div style='font-size:0.68rem; color:#A0A0B0; padding:4px 4px 4px 4px; "
            "letter-spacing:0.1em; border-top:1px solid #EDEEF2; padding-top:10px'>공간 범위</div>",
            unsafe_allow_html=True
        )
        if "p2_scope" not in st.session_state:
            st.session_state.p2_scope = "전체"
        for lbl in ["전체", "동별 비교"]:
            is_act = st.session_state.p2_scope == lbl
            if st.button(lbl, key=f"p2s_{lbl}", use_container_width=True,
                         type="primary" if is_act else "secondary"):
                st.session_state.p2_scope = lbl
                st.rerun()

        st.markdown(
            "<div style='height:260px'></div>"
            "<div style='font-size:0.68rem; color:#A0A0B0; padding:4px 4px 4px 4px; "
            "letter-spacing:0.1em; border-top:1px solid #EDEEF2; padding-top:10px'>차트 보기</div>",
            unsafe_allow_html=True
        )
        if "chart2" not in st.session_state:
            st.session_state.chart2 = "월별"
        for lbl in ["월별", "시간대별"]:
            is_act = st.session_state.chart2 == lbl
            if st.button(lbl, key=f"c2_{lbl}", use_container_width=True,
                         type="primary" if is_act else "secondary"):
                st.session_state.chart2 = lbl
                st.rerun()

        # 시간대별 모드일 때 기준 월 선택
        if st.session_state.chart2 == "시간대별":
            lp_sidebar = load_local_people()
            month_values = sorted(lp_sidebar["data_ym"].astype(str).unique().tolist())
            month_labels = {"전체평균": "전체평균", "최근월": "최근월"}
            for m in month_values:
                month_labels[m] = f"{m[:4]}.{m[4:6]}"

            if "p2_hour_month" not in st.session_state:
                st.session_state.p2_hour_month = "전체평균"
            sel_key = st.selectbox(
                "시간대 기준 월",
                ["전체평균", "최근월"] + month_values,
                index=(["전체평균", "최근월"] + month_values).index(
                    st.session_state.p2_hour_month
                    if st.session_state.p2_hour_month in (["전체평균", "최근월"] + month_values)
                    else "전체평균"
                ),
                format_func=lambda x: month_labels.get(x, x),
                key="p2_hour_month_box",
            )
            if sel_key != st.session_state.p2_hour_month:
                st.session_state.p2_hour_month = sel_key
                st.rerun()
        st.markdown("---")

    # Page 3 전용 서브필터 — 차트 시작 높이에 맞춰 spacer 조정
    if st.session_state.get("page") == "3":
        st.markdown(
            "<div style='height:440px'></div>"
            "<div style='font-size:0.68rem; color:#A0A0B0; padding:4px 4px 4px 4px; "
            "letter-spacing:0.1em; border-top:1px solid #EDEEF2; padding-top:10px'>차트 보기</div>",
            unsafe_allow_html=True
        )
        if "chart3" not in st.session_state:
            st.session_state.chart3 = "분기별 추이"
        t1 = "primary" if st.session_state.chart3 == "분기별 추이" else "secondary"
        t2 = "primary" if st.session_state.chart3 == "업종별 비교" else "secondary"
        if st.button("분기별 추이", key="c3_q", type=t1, use_container_width=True):
            st.session_state.chart3 = "분기별 추이"
            st.session_state.map_filter_cat = None
            st.rerun()
        if st.button("업종별 비교", key="c3_cat", type=t2, use_container_width=True):
            st.session_state.chart3 = "업종별 비교"
            st.rerun()

        # 업종별 비교일 때 권역 드롭다운
        if st.session_state.chart3 == "업종별 비교":
            st.markdown(
                "<div style='font-size:0.68rem; color:#A0A0B0; padding:10px 4px 2px 4px; letter-spacing:0.06em'>권역 선택</div>",
                unsafe_allow_html=True
            )
            if "cat_area_sel" not in st.session_state:
                st.session_state.cat_area_sel = "전체"
            area_options = ["전체"] + AREAS
            sel_idx = area_options.index(st.session_state.get("cat_area_sel", "전체"))
            chosen = st.selectbox("", area_options, index=sel_idx,
                                  key="cat_area_box", label_visibility="collapsed")
            if chosen != st.session_state.get("cat_area_sel"):
                st.session_state.cat_area_sel = chosen
                st.rerun()

        # 지도 필터 초기화 버튼 (업종 선택된 경우)
        if st.session_state.get("map_filter_cat"):
            st.markdown(
                f"<div style='font-size:0.72rem; color:#A05AFF; padding:6px 14px'>선택: {st.session_state.map_filter_cat}</div>",
                unsafe_allow_html=True
            )
            if st.button("전체 보기", key="clear_cat", use_container_width=True):
                st.session_state.map_filter_cat = None
                st.rerun()

        st.markdown("---")

    # Page 4 전용 서브필터
    if st.session_state.get("page") == "4":
        st.markdown(
            "<div style='font-size:0.68rem; color:#A0A0B0; padding:4px 4px 4px 4px; "
            "letter-spacing:0.1em; border-top:1px solid #EDEEF2; padding-top:10px'>방문자 유형</div>",
            unsafe_allow_html=True
        )
        if "p4_visitor" not in st.session_state:
            st.session_state.p4_visitor = "내국인"
        for lbl in ["내국인", "외국인", "전체"]:
            is_act = st.session_state.p4_visitor == lbl
            if st.button(lbl, key=f"p4v_{lbl}", use_container_width=True,
                         type="primary" if is_act else "secondary"):
                st.session_state.p4_visitor = lbl
                st.rerun()

        st.markdown(
            "<div style='font-size:0.68rem; color:#A0A0B0; padding:10px 4px 2px 4px; letter-spacing:0.06em'>지도 범위</div>",
            unsafe_allow_html=True
        )
        if "p4_scope" not in st.session_state:
            st.session_state.p4_scope = "서울시"
        for lbl in ["서울시", "수도권"]:
            is_act = st.session_state.p4_scope == lbl
            if st.button(lbl, key=f"p4s_{lbl}", use_container_width=True,
                         type="primary" if is_act else "secondary"):
                st.session_state.p4_scope = lbl
                st.rerun()

        st.markdown(
            "<div style='font-size:0.68rem; color:#A0A0B0; padding:10px 4px 2px 4px; letter-spacing:0.06em'>하단 차트</div>",
            unsafe_allow_html=True
        )
        if "p4_chart" not in st.session_state:
            st.session_state.p4_chart = "월별 유입구조"
        for lbl in ["월별 유입구조", "상위 유입지역"]:
            is_act = st.session_state.p4_chart == lbl
            if st.button(lbl, key=f"p4c_{lbl}", use_container_width=True,
                         type="primary" if is_act else "secondary"):
                st.session_state.p4_chart = lbl
                st.rerun()
        st.markdown("---")

    # Page 5 전용 서브필터
    if st.session_state.get("page") == "5":
        st.markdown(
            "<div style='font-size:0.68rem; color:#A0A0B0; padding:4px 4px 4px 4px; "
            "letter-spacing:0.1em; border-top:1px solid #EDEEF2; padding-top:10px'>랭킹 지표</div>",
            unsafe_allow_html=True
        )
        if "p5_rank_metric" not in st.session_state:
            st.session_state.p5_rank_metric = "매출건수"
        for lbl in ["매출건수 Top 10", "방문자리뷰 Top 10", "블로그리뷰 Top 10"]:
            is_act = st.session_state.p5_rank_metric == lbl
            if st.button(lbl, key=f"p5r_{lbl}", use_container_width=True,
                         type="primary" if is_act else "secondary"):
                st.session_state.p5_rank_metric = lbl
                st.rerun()
        st.markdown("---")

    st.markdown(
        "<small style='color:#AAA; font-size:0.68rem'>데이터 기준: 2024.01 ~ 2026.02</small>",
        unsafe_allow_html=True
    )

# ── 페이지 라우팅 ──────────────────────────────────────────────────────────
page = st.session_state.page

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — 매출 분석
# ══════════════════════════════════════════════════════════════════════════════
if page == "3":

    st.markdown(
        "<div style='font-size:1.6rem; font-weight:800; color:#1E1B4B; "
        "padding:0 0 6px 0; margin-top:0; line-height:1.2'>매출 분석</div>",
        unsafe_allow_html=True
    )
    st.markdown("---")

    # 최신 3개월
    latest_yms   = sorted(sales["ym"].unique())[-3:]
    period_label = (f"{str(latest_yms[0])[:4]}.{str(latest_yms[0])[4:6]}"
                    f" ~ {str(latest_yms[-1])[:4]}.{str(latest_yms[-1])[4:6]}")
    recent = sales[sales["ym"].isin(latest_yms)]

    # ── KPI 상단 ───────────────────────────────────────────────────────────
    kpi      = recent.groupby("area").agg(total=("sales_man","sum")).reset_index()
    store_cnt = stores.groupby("area")["store_id"].nunique().reset_index(name="cnt")
    kpi       = kpi.merge(store_cnt, on="area")
    kpi["avg_monthly"] = kpi["total"] / kpi["cnt"] / 3

    KPI_GRADIENTS = {
        "성수동":   "linear-gradient(135deg, #A05AFF 0%, #C98BFF 100%)",
        "이태원한남": "linear-gradient(135deg, #FE9496 0%, #FFB8A8 100%)",
        "홍대합정": "linear-gradient(135deg, #1BCFB4 0%, #5EE3C9 100%)",
    }

    kpi_cols = st.columns(3)
    for i, area in enumerate(AREAS):
        row = kpi[kpi["area"] == area]
        if row.empty:
            continue
        avg  = int(row["avg_monthly"].values[0])
        cnt  = int(row["cnt"].values[0])
        grad = KPI_GRADIENTS[area]
        with kpi_cols[i]:
            st.markdown(f"""
            <div class='kpi-card' style='background:{grad}'>
              <div class='kpi-label'>{area} · 매장당 월평균 매출</div>
              <div class='kpi-value'>{avg:,}<span class='kpi-unit'>만원 / 월</span></div>
              <div class='kpi-sub'>매장 {cnt}개 · 기준: {period_label}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown(
        "<div style='font-size:0.7rem; color:#999; margin:6px 0 10px 2px'>"
        "※ 매장당 월평균 매출 = 최근 3개월 합계 ÷ 매장수 ÷ 3개월"
        "</div>",
        unsafe_allow_html=True
    )

    # ── 지도 3개 ───────────────────────────────────────────────────────────
    filter_cat = st.session_state.get("map_filter_cat")  # None 이면 전체
    filter_label = f" — '{filter_cat}' 필터 적용" if filter_cat else ""

    st.markdown(
        f"<div style='font-size:0.92rem; font-weight:700; margin-bottom:6px'>"
        f"권역별 매출액 분포"
        f"<span style='font-size:0.72rem; color:#888; font-weight:400; margin-left:8px'>"
        f"{period_label} 평균 · 순위 기반 통합 스케일{filter_label}"
        f"</span></div>",
        unsafe_allow_html=True
    )

    store_recent = recent.groupby("store_id").agg(
        avg_sales=("sales_man","mean"),
        lat=("lat","first"),
        lon=("lon","first"),
        area=("area","first"),
        store_nm=("store_nm","first"),
        cat_mi=("cat_mi","first"),
    ).reset_index()

    # percentile 기반 통합 스케일
    store_recent["rank_pct"] = store_recent["avg_sales"].rank(method="average", pct=True)
    vmin = store_recent["avg_sales"].min()
    vmax = store_recent["avg_sales"].max()
    vmed = store_recent["avg_sales"].median()

    def sales_to_color(t):
        t = float(np.clip(t, 0, 1))
        # orange 그라데이션: 연한 노란-주황(#FEF3C7) → 진한 오렌지(#EA580C)
        r = int(254 - t * (254 - 234))
        g = int(243 - t * (243 - 88))
        b = int(199 - t * (199 - 12))
        return f"#{r:02X}{g:02X}{b:02X}"

    map_cols = st.columns(3)
    for i, area in enumerate(AREAS):
        area_data = store_recent[store_recent["area"] == area]
        center    = AREA_CENTERS[area]
        m = folium.Map(location=center, zoom_start=15, tiles="CartoDB positron")

        for _, row in area_data.iterrows():
            if pd.isna(row["lat"]) or pd.isna(row["lon"]):
                continue

            # 업종 필터: 선택된 cat_mi 이외는 반투명 회색
            if filter_cat and row["cat_mi"] != filter_cat:
                fill_c   = "#CCCCCC"
                fill_op  = 0.35
                radius   = 6
            else:
                fill_c   = sales_to_color(row["rank_pct"])
                fill_op  = 0.93
                radius   = 8 if filter_cat else 7

            folium.CircleMarker(
                location=[row["lat"], row["lon"]],
                radius=radius,
                color="#fff",
                weight=1,
                fill=True,
                fill_color=fill_c,
                fill_opacity=fill_op,
                tooltip=(f"{row['store_nm']}<br>"
                         f"{int(row['avg_sales']):,}만원/월<br>"
                         f"{row['cat_mi']}")
            ).add_to(m)

        with map_cols[i]:
            st.markdown(
                f"<div class='map-label' style='color:{AREA_COLORS[area]}'>● {area}</div>",
                unsafe_allow_html=True
            )
            st_folium(m, width="100%", height=520,
                      returned_objects=[], key=f"map3_{area}")

    # 범례
    st.markdown(
        f"<div style='display:flex; align-items:center; gap:8px; margin:6px 0 10px 0;"
        f"font-size:0.71rem; color:#666'>"
        f"<span>하위</span>"
        f"<div style='width:140px; height:9px; border-radius:4px;"
        f"background:linear-gradient(to right, #FEF3C7, #EA580C);'></div>"
        f"<span>상위</span>"
        f"<span style='margin-left:12px; color:#999'>"
        f"최소 {vmin:,.0f} / 중앙 {vmed:,.0f} / 최대 {vmax:,.0f} 만원</span>"
        f"</div>",
        unsafe_allow_html=True
    )

    # ── 하단 차트 ──────────────────────────────────────────────────────────
    if "chart3" not in st.session_state:
        st.session_state.chart3 = "분기별 추이"

    # ── 분기별 추이 (Y축: 매장당 월평균) ──────────────────────────────────
    if st.session_state.chart3 == "분기별 추이":

        # 분기별 매장 수 (분기마다 달라질 수 있으므로 동적 계산)
        q_store = (sales[sales["quarter"].isin(QUARTER_ORDER)]
                   .groupby(["area","quarter"])["store_id"].nunique()
                   .reset_index(name="store_cnt"))
        # 분기별 월 수 (2026Q1 = 2개월)
        q_month_cnt = {q: 3 for q in QUARTER_ORDER}
        q_month_cnt["2026Q1"] = 2

        q_sales = (sales[sales["quarter"].isin(QUARTER_ORDER)]
                   .groupby(["area","quarter"])["sales_man"].sum()
                   .reset_index())
        q_sales = q_sales.merge(q_store, on=["area","quarter"])
        q_sales["month_n"] = q_sales["quarter"].map(q_month_cnt)
        # 매장당 월평균 = 분기합계 / 매장수 / 월수
        q_sales["avg_per_store"] = q_sales["sales_man"] / q_sales["store_cnt"] / q_sales["month_n"]
        q_sales["quarter"] = pd.Categorical(q_sales["quarter"], categories=QUARTER_ORDER, ordered=True)
        q_sales = q_sales.sort_values("quarter")

        fig = go.Figure()
        for area in AREAS:
            d = q_sales[q_sales["area"] == area]
            fig.add_trace(go.Scatter(
                x=d["quarter"].astype(str),
                y=d["avg_per_store"],
                name=area,
                mode="lines+markers",
                line=dict(color=AREA_COLORS[area], width=2.5),
                marker=dict(size=7),
                hovertemplate="%{x}<br>%{y:,.0f}만원/월·매장<extra>" + area + "</extra>"
            ))

        fig.update_layout(
            title="권역별 분기별 매장당 월평균 매출",
            xaxis_title=None, yaxis_title="매장당 월평균 매출 (만원)",
            legend=dict(
                orientation="h",
                yanchor="bottom", y=1.04,
                xanchor="center", x=0.5,
            ),
            plot_bgcolor="#fff", paper_bgcolor="#F4F5F7",
            height=544,
            hovermode="x unified",
            margin=dict(l=70, r=20, t=90, b=40),
        )
        fig.update_yaxes(tickformat=",", gridcolor="#EFEFEF")
        fig.update_xaxes(gridcolor="#EFEFEF")
        st.plotly_chart(fig, use_container_width=True)

        st.markdown(
            "<div class='note-box'>"
            "※ 매장당 월평균 매출 = 분기 합계 ÷ 해당 분기 매장수 ÷ 월수<br>"
            "※ 2026Q1은 데이터 기준월 2026.01~02 (2개월) 반영 — 평균 단위로 정규화됨<br>"
            "※ 대규모 공연 시설 매출 누락."
            "</div>",
            unsafe_allow_html=True
        )

    # ── 업종별 비교 — 2024 vs 2025 연도별 (클릭 → 지도 필터) ──────────────
    else:
        sel_area = st.session_state.get("cat_area_sel", "전체")

        cat_year = sales[sales["year"].isin([2024, 2025])].copy()
        if sel_area != "전체":
            cat_year = cat_year[cat_year["area"] == sel_area]

        cat_agg = cat_year.groupby(["year","cat_mi"])["sales_man"].sum().reset_index()
        cat_order = (cat_agg.groupby("cat_mi")["sales_man"].sum()
                     .sort_values(ascending=False).index.tolist())

        # 성장률 계산 (hover용)
        pivot = cat_agg.pivot(index="cat_mi", columns="year", values="sales_man").fillna(0)
        pivot.columns.name = None
        if 2024 in pivot.columns and 2025 in pivot.columns:
            pivot["growth"] = ((pivot[2025] - pivot[2024]) / (pivot[2024] + 1) * 100).round(1)
        else:
            pivot["growth"] = 0

        YEAR_COLORS = {2024: "#C0C0C0", 2025: "#606060"}

        fig = go.Figure()
        for year in [2024, 2025]:
            d = (cat_agg[cat_agg["year"] == year]
                 .set_index("cat_mi").reindex(cat_order).reset_index())
            growth_vals = [pivot.loc[c, "growth"] if c in pivot.index else 0
                           for c in d["cat_mi"]]
            customdata = [[g] for g in growth_vals]

            # 2024: 연한 gray + dot pattern / 2025: solid dark gray
            if year == 2024:
                marker = dict(
                    color="#C0C0C0",
                    pattern=dict(shape=".", size=4, solidity=0.5, fgcolor="#888888"),
                )
            else:
                marker = dict(color="#606060")

            fig.add_trace(go.Bar(
                name=str(year),
                x=d["cat_mi"],
                y=d["sales_man"],
                marker=marker,
                customdata=customdata,
                hovertemplate=(
                    f"{year}  %{{x}}<br>매출: %{{y:,.0f}}만원"
                    + ("<br>전년 대비: %{customdata[0]:+.1f}%" if year == 2025 else "")
                    + "<extra></extra>"
                )
            ))

        area_label = f" — {sel_area}" if sel_area != "전체" else " — 3권역 합산"
        fig.update_layout(
            title=f"업종별 매출 합계 비교 (2024 vs 2025){area_label}  ·  막대 클릭 시 지도에 해당 업종 강조",
            barmode="group",
            xaxis_title=None, yaxis_title="매출 합계 (만원)",
            legend=dict(
                orientation="h",
                yanchor="bottom", y=1.04,
                xanchor="center", x=0.5,
            ),
            plot_bgcolor="#fff", paper_bgcolor="#F4F5F7",
            height=544,
            bargroupgap=0.12,
            margin=dict(l=70, r=20, t=90, b=80),
            clickmode="event+select",
        )
        fig.update_yaxes(tickformat=",", gridcolor="#EFEFEF")
        fig.update_xaxes(tickangle=-20)

        selected = st.plotly_chart(
            fig,
            on_select="rerun",
            selection_mode="points",
            use_container_width=True,
        )

        # 클릭 이벤트 처리 → 지도 필터 업데이트
        if selected and selected.selection and selected.selection.points:
            clicked_x = selected.selection.points[0].get("x")
            if clicked_x and clicked_x != st.session_state.get("map_filter_cat"):
                st.session_state.map_filter_cat = clicked_x
                st.rerun()

        st.markdown(
            "<div class='note-box'>"
            "※ 2024.01~12 / 2025.01~12 연간 합산 기준 (2026년 제외)<br>"
            "※ 대규모 공연 시설 매출 누락."
            "</div>",
            unsafe_allow_html=True
        )


# ══════════════════════════════════════════════════════════════════════════════
# 미구현 페이지 플레이스홀더
# ══════════════════════════════════════════════════════════════════════════════
elif page == "1":

    naver, public = load_page1_data()
    src = st.session_state.get("src1", "네이버")

    cat_filter = st.session_state.get("cat1_filter", "전체")

    if src == "네이버":
        df       = naver.copy()
        lat_col, lon_col = "y", "x"
        nm_col   = "name"
        src_note = "네이버 플레이스 · 2024년 수집 (문화키워드 검색)"
    else:
        df       = public.copy()
        lat_col, lon_col = "lat", "lon"
        nm_col   = "시설명"
        src_note = "서울시 공공 문화시설 · 행정 등록 기준"

    cat_col = "cat_unified"  # 통합 카테고리 공통 사용

    st.markdown(
        f"<div style='font-size:1.6rem; font-weight:800; color:#1E1B4B; padding:0 0 4px 0'>장소 공급 현황</div>"
        f"<div style='font-size:0.75rem; color:#999; margin-bottom:8px'>{src_note}</div>",
        unsafe_allow_html=True
    )
    st.markdown("---")

    # ── KPI 상단 ───────────────────────────────────────────────────────────
    KPI_GRADIENTS = {
        "성수동":   "linear-gradient(135deg, #A05AFF 0%, #C98BFF 100%)",
        "이태원한남": "linear-gradient(135deg, #FE9496 0%, #FFB8A8 100%)",
        "홍대합정": "linear-gradient(135deg, #1BCFB4 0%, #5EE3C9 100%)",
    }
    kpi_cols = st.columns(3)
    for i, area in enumerate(AREAS):
        area_df = df[df["area_std"] == area]
        if cat_filter != "전체":
            area_df = area_df[area_df[cat_col] == cat_filter]
        cnt     = area_df.shape[0]
        top_cat = (area_df[cat_col].value_counts().idxmax()
                   if cnt > 0 else "-")
        with kpi_cols[i]:
            st.markdown(f"""
            <div class='kpi-card' style='background:{KPI_GRADIENTS[area]}'>
              <div class='kpi-label'>{area} · 문화시설 수</div>
              <div class='kpi-value'>{cnt:,}<span class='kpi-unit'>개소</span></div>
              <div class='kpi-sub'>최다: {top_cat}{"  ·  필터: "+cat_filter if cat_filter!="전체" else ""}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown(
        f"<div style='font-size:0.7rem; color:#999; margin:6px 0 10px 2px'>"
        f"※ {src_note}</div>", unsafe_allow_html=True
    )

    # ── 지도 3개 ───────────────────────────────────────────────────────────
    st.markdown(
        "<div style='font-size:0.92rem; font-weight:700; margin-bottom:6px'>"
        "권역별 문화시설 분포"
        "<span style='font-size:0.72rem; color:#888; font-weight:400; margin-left:8px'>"
        "카테고리별 색상</span></div>",
        unsafe_allow_html=True
    )

    map_cols = st.columns(3)
    for i, area in enumerate(AREAS):
        area_df = df[df["area_std"] == area].dropna(subset=[lat_col, lon_col])
        center  = AREA_CENTERS[area]
        m = folium.Map(location=center, zoom_start=15, tiles="CartoDB positron")

        for _, row in area_df.iterrows():
            cat = row[cat_col] if pd.notna(row[cat_col]) else "기타"
            # 필터 적용: 선택된 카테고리만 진하게, 나머지 연하게
            if cat_filter == "전체" or cat == cat_filter:
                fill_c  = "#374151"   # Dark Gray (약간 옅게: 1F2937 → 374151)
                fill_op = 0.82
                radius  = 6.3         # 7 * 0.9
            else:
                fill_c  = "#D1D5DB"   # Light Gray
                fill_op = 0.35
                radius  = 4.5         # 5 * 0.9
            folium.CircleMarker(
                location=[row[lat_col], row[lon_col]],
                radius=radius,
                color="#fff", weight=1,
                fill=True, fill_color=fill_c, fill_opacity=fill_op,
                tooltip=f"{row[nm_col]}<br>{cat}"
            ).add_to(m)

        with map_cols[i]:
            cat_badge = (
                f"<span style='background:#F5F2FF; color:#A05AFF; border:1px solid #D8CCFF; "
                f"border-radius:4px; font-size:0.7rem; font-weight:600; padding:2px 8px; margin-left:6px'>"
                f"{cat_filter}</span>"
                if cat_filter != "전체" else
                f"<span style='background:#F5F5F5; color:#888; border:1px solid #E0E0E0; "
                f"border-radius:4px; font-size:0.7rem; font-weight:500; padding:2px 8px; margin-left:6px'>"
                f"전체</span>"
            )
            st.markdown(
                f"<div class='map-label' style='color:{AREA_COLORS[area]}'>● {area}{cat_badge}</div>",
                unsafe_allow_html=True
            )
            st_folium(m, width="100%", height=520,
                      returned_objects=[], key=f"map1_{area}_{src}_{cat_filter}")

    # 지도 범례
    filter_txt = f"'{cat_filter}' 필터 적용 중" if cat_filter != "전체" else "전체 카테고리"
    st.markdown(
        f"<div style='font-size:0.71rem; color:#888; margin:6px 0 12px 0'>"
        f"● 진한 점: 해당 시설  ·  연한 점: 기타 카테고리  ·  {filter_txt}"
        f"</div>",
        unsafe_allow_html=True
    )

    # ── 하단 차트 — 통합 카테고리 × 권역 grouped bar ─────────────────
    fig = go.Figure()
    for area in AREAS:
        area_df = df[df["area_std"] == area]
        counts  = area_df[cat_col].value_counts().reindex(UNIFIED_CATS, fill_value=0)
        fig.add_trace(go.Bar(
            name=area,
            x=UNIFIED_CATS,
            y=counts.values,
            marker_color=AREA_COLORS[area],
            hovertemplate="%{x}<br>%{y}개소<extra>" + area + "</extra>"
        ))

    fig.update_layout(
        title=f"카테고리별 문화시설 수 비교 — {src}",
        barmode="group",
        xaxis_title=None, yaxis_title="시설 수 (개소)",
        legend=dict(orientation="h", yanchor="bottom", y=1.04, xanchor="center", x=0.5),
        plot_bgcolor="#fff", paper_bgcolor="#F4F5F7",
        height=544,
        margin=dict(l=60, r=20, t=80, b=60),
        bargroupgap=0.1,
    )
    fig.update_yaxes(gridcolor="#EFEFEF", dtick=5)
    fig.update_xaxes(tickangle=0)
    st.plotly_chart(fig, use_container_width=True)

    # ── 카테고리 주석 expander ─────────────────────────────────────────
    with st.expander("카테고리 분류 기준 보기"):
        for cat in UNIFIED_CATS:
            color = UNIFIED_CAT_COLORS.get(cat, "#888")
            note  = UNIFIED_CAT_NOTE.get(cat, {})
            st.markdown(
                f"<div style='margin-bottom:10px; font-size:0.8rem'>"
                f"<span style='display:inline-flex; align-items:center; gap:6px; font-weight:700; margin-bottom:3px'>"
                f"<span style='width:12px; height:12px; border-radius:50%; background:{color}; display:inline-block'></span>"
                f"{cat}</span><br>"
                f"<span style='color:#666; margin-left:18px'>네이버: {note.get('네이버','')}</span><br>"
                f"<span style='color:#666; margin-left:18px'>공공: {note.get('공공','')}</span>"
                f"</div>",
                unsafe_allow_html=True
            )
elif page == "2":
    # ═════════════════════════════════════════════════════════════════════════
    # PAGE 2 — 생활인구
    # ═════════════════════════════════════════════════════════════════════════

    import json as _json

    st.markdown(
        "<div style='font-size:1.6rem; font-weight:800; color:#1E1B4B; "
        "padding:0 0 6px 0; margin-top:0; line-height:1.2'>생활인구</div>",
        unsafe_allow_html=True
    )
    st.markdown("---")

    # ── 데이터 로드 ───────────────────────────────────────────────────────
    lp = load_local_people()

    LOCAL_ZONE_TO_AREA = {"성수": "성수동", "이태원한남": "이태원한남", "홍대권": "홍대합정"}
    lp["area_std"] = lp["zone"].map(LOCAL_ZONE_TO_AREA)

    # 평일/주말 파생
    lp["dow"] = lp["date"].dt.dayofweek  # 0=Mon … 6=Sun
    lp["daytype"] = lp["dow"].apply(lambda x: "주말" if x >= 5 else "평일")

    # 행정동 경계 GeoJSON
    GEOJSON_PATH = BASE_DIR / "seoul_dong_boundary.geojson"
    with open(GEOJSON_PATH, encoding="utf-8") as _f:
        geojson_data = _json.load(_f)

    DONG_TO_AREA = {
        "이태원1동": "이태원한남", "이태원2동": "이태원한남", "한남동": "이태원한남",
        "성수1가1동": "성수동", "성수1가2동": "성수동",
        "성수2가1동": "성수동", "성수2가3동": "성수동",
        "서교동": "홍대합정", "합정동": "홍대합정", "서강동": "홍대합정",
    }

    # ── KPI 상단 ──────────────────────────────────────────────────────────
    KPI_GRADIENTS = {
        "성수동":   "linear-gradient(135deg, #A05AFF 0%, #C98BFF 100%)",
        "이태원한남": "linear-gradient(135deg, #FE9496 0%, #FFB8A8 100%)",
        "홍대합정": "linear-gradient(135deg, #1BCFB4 0%, #5EE3C9 100%)",
    }

    kpi_cols = st.columns(3)
    for i, area in enumerate(AREAS):
        d = lp[lp["area_std"] == area].dropna(subset=["date"])
        if d.empty:
            continue
        daily = d.groupby("기준일ID", as_index=False)["총생활인구수"].sum()
        avg_daily = float(daily["총생활인구수"].mean())
        peak_daily = float(daily["총생활인구수"].max())
        dong_n = int(d["행정동명"].nunique())

        with kpi_cols[i]:
            st.markdown(
                f"<div class='kpi-card' style='background:{KPI_GRADIENTS[area]}'>"
                f"<div class='kpi-label'>{area} · 일평균 생활인구</div>"
                f"<div class='kpi-value'>{avg_daily:,.0f}<span class='kpi-unit'>명 / 일</span></div>"
                f"<div class='kpi-sub'>피크 {peak_daily:,.0f}명 · 행정동 {dong_n}개</div>"
                f"</div>",
                unsafe_allow_html=True
            )

    st.markdown(
        "<div style='font-size:0.7rem; color:#999; margin:6px 0 10px 2px'>"
        "※ 일평균 생활인구 = (시간대별 합산 → 일합계) 전체 기간 평균"
        "</div>",
        unsafe_allow_html=True
    )

    # ── 동별 평균 생활인구 (choropleth 값) ────────────────────────────────
    dong_avg = (
        lp.groupby(["행정동명"], as_index=False)
        .agg(avg_pop=("총생활인구수", "mean"))
    )
    dong_avg_map = dict(zip(dong_avg["행정동명"], dong_avg["avg_pop"]))

    # ── 지도 3개: 동 경계(choropleth) + 클릭 연동 ─────────────────────────
    scope = st.session_state.get("p2_scope", "전체")
    chart_mode = st.session_state.get("chart2", "월별")
    hour_month_sel = st.session_state.get("p2_hour_month", "전체평균")

    st.markdown(
        "<div style='font-size:0.92rem; font-weight:700; margin-bottom:6px'>"
        "권역별 생활인구 분포"
        "<span style='font-size:0.72rem; color:#888; font-weight:400; margin-left:8px'>"
        "동 경계 색상 = 평균 생활인구 · 동을 클릭하면 하단 차트가 연동됩니다"
        "</span></div>",
        unsafe_allow_html=True
    )

    # 권역별 선택 동 (session state): 성수동/이태원한남/홍대합정 각각 1개씩 유지
    area_dong_options = {
        area: sorted(lp.loc[lp["area_std"] == area, "행정동명"].dropna().unique().tolist())
        for area in AREAS
    }
    if "p2_sel_dong_by_area" not in st.session_state:
        st.session_state.p2_sel_dong_by_area = {
            area: (area_dong_options[area][0] if area_dong_options[area] else None)
            for area in AREAS
        }

    def _extract_dong(raw_text: str, candidates: list[str]) -> str | None:
        """folium 클릭 반환값(HTML 포함 가능)에서 동 이름만 추출."""
        if not raw_text:
            return None
        txt = re.sub(r"<[^>]*>", " ", str(raw_text))
        txt = re.sub(r"\s+", " ", txt).strip()
        for d in candidates:
            if d in txt:
                return d
        return None

    def _color_scale(global_t, local_t, base_rgb):
        """전권역 공통강도(global) + 권역내 상대강도(local) 혼합."""
        # 공통 기준(35%) + 권역내 대비(65%)로 섞어 편차를 줄이되 비교 가능성 유지
        t = 0.35 * float(global_t) + 0.65 * float(local_t)
        # 너무 하얗게 뜨는 문제를 줄이기 위해 하한을 올림
        t = 0.22 + 0.78 * max(0.0, min(1.0, t))
        r = int(255 - t * (255 - base_rgb[0]))
        g = int(255 - t * (255 - base_rgb[1]))
        b = int(255 - t * (255 - base_rgb[2]))
        return f"#{r:02X}{g:02X}{b:02X}"

    AREA_BASE_RGB = {
        "성수동":   (160, 90, 255),
        "이태원한남": (254, 148, 150),
        "홍대합정": (27, 207, 180),
    }

    # 전권역 공통 min/max (공통 스케일 기준)
    global_vals = [v for v in dong_avg_map.values() if pd.notna(v)]
    gmin = min(global_vals) if global_vals else 0.0
    gmax = max(global_vals) if global_vals else 1.0

    map_cols = st.columns(3)
    click_results = {}
    for i, area in enumerate(AREAS):
        center = AREA_CENTERS[area]
        m = folium.Map(location=center, zoom_start=14, tiles="CartoDB positron")

        area_dongs = [d for d, a in DONG_TO_AREA.items() if a == area]
        area_features = [
            f for f in geojson_data["features"]
            if f["properties"].get("dong") in area_dongs
        ]

        vals = [dong_avg_map.get(d, 0) for d in area_dongs]
        vmin = min(vals) if vals else 0
        vmax = max(vals) if vals else 1
        base_rgb = AREA_BASE_RGB[area]

        for feat in area_features:
            dong_nm = feat["properties"]["dong"]
            pop = float(dong_avg_map.get(dong_nm, 0))
            global_t = (pop - gmin) / (gmax - gmin) if gmax > gmin else 0.5
            local_t = (pop - vmin) / (vmax - vmin) if vmax > vmin else 0.5
            fill_c = _color_scale(global_t, local_t, base_rgb)
            is_selected = st.session_state.p2_sel_dong_by_area.get(area) == dong_nm
            weight = 3 if is_selected else 1.5
            border_c = "#111" if is_selected else "#888"

            folium.GeoJson(
                feat,
                style_function=lambda _feat, fc=fill_c, w=weight, bc=border_c: {
                    "fillColor": fc,
                    "color": bc,
                    "weight": w,
                    "fillOpacity": 0.72,
                },
                tooltip=folium.GeoJsonTooltip(
                    fields=["dong"],
                    aliases=["행정동"],
                    style="font-size:13px;",
                ),
                highlight_function=lambda _feat: {
                    "weight": 3,
                    "color": "#333",
                    "fillOpacity": 0.75,
                },
            ).add_to(m)

            folium.Marker(
                location=_centroid(feat),
                icon=folium.DivIcon(
                    html=f"<div style='font-size:10px;font-weight:700;color:#333;"
                         f"white-space:nowrap;text-shadow:0 0 3px #fff'>{dong_nm}</div>",
                    icon_size=(90, 16),
                    icon_anchor=(45, 8),
                ),
            ).add_to(m)

        with map_cols[i]:
            st.markdown(
                f"<div class='map-label' style='color:{AREA_COLORS[area]}'>● {area}</div>",
                unsafe_allow_html=True
            )
            result = st_folium(
                m, width="100%", height=520,
                returned_objects=["last_object_clicked_tooltip"],
                key=f"map2_{area}",
            )
            click_results[area] = result

    # 클릭 → 권역별 동 선택 처리
    for area, result in click_results.items():
        if result and result.get("last_object_clicked_tooltip"):
            raw = result["last_object_clicked_tooltip"]
            clicked_dong = _extract_dong(raw, area_dong_options.get(area, []))
            if clicked_dong and clicked_dong != st.session_state.p2_sel_dong_by_area.get(area):
                st.session_state.p2_sel_dong_by_area[area] = clicked_dong
                # 동 클릭 시 동별 비교 모드로 자동 전환
                st.session_state.p2_scope = "동별 비교"
                st.rerun()

    # 범례
    st.markdown(
        "<div style='display:flex; align-items:center; gap:8px; margin:6px 0 8px 0;"
        "font-size:0.71rem; color:#666'>"
        "<span>낮음</span>"
        "<div style='width:120px; height:9px; border-radius:4px;"
        "background:linear-gradient(to right, #F0E0FF, #A05AFF);'></div>"
        "<span>높음</span>"
        "<span style='margin-left:8px; color:#999'>평균 생활인구(동별)</span>"
        "</div>",
        unsafe_allow_html=True
    )

    # 권역별 대표동 선택(3개 동시 유지)
    sel_cols = st.columns(3)
    for i, area in enumerate(AREAS):
        options = area_dong_options.get(area, [])
        current = st.session_state.p2_sel_dong_by_area.get(area)
        if options and current not in options:
            current = options[0]
            st.session_state.p2_sel_dong_by_area[area] = current
        with sel_cols[i]:
            st.caption(f"{area} 대표동")
            if options:
                chosen = st.selectbox(
                    f"{area} 동 선택",
                    options,
                    index=options.index(current),
                    key=f"p2_dong_{area}",
                    label_visibility="collapsed",
                )
                if chosen != st.session_state.p2_sel_dong_by_area.get(area):
                    st.session_state.p2_sel_dong_by_area[area] = chosen
                    st.rerun()

    sel_summary = " / ".join(
        f"{area}: {st.session_state.p2_sel_dong_by_area.get(area, '-')}"
        for area in AREAS
    )
    st.caption(f"선택 대표동 · {sel_summary}")

    # ── 하단 차트 ─────────────────────────────────────────────────────────
    # 필터: 전체 vs 동별(권역별 대표동 3개 동시)
    if scope == "동별 비교":
        frames = []
        for area in AREAS:
            dong = st.session_state.p2_sel_dong_by_area.get(area)
            if dong:
                frames.append(lp[(lp["area_std"] == area) & (lp["행정동명"] == dong)])
        lp_chart = pd.concat(frames, ignore_index=True) if frames else lp.iloc[0:0].copy()
        chart_scope_label = " / ".join(
            f"{area}:{st.session_state.p2_sel_dong_by_area.get(area, '-')}" for area in AREAS
        )
    else:
        lp_chart = lp.copy()
        chart_scope_label = "3권역 전체"

    DAYTYPE_DASH   = {"평일": "solid", "주말": "dot"}

    # ── 모드 1: 월별 (평일/주말) ─────────────────────────────────────────
    if chart_mode == "월별":
        daily_c = (
            lp_chart.dropna(subset=["date"])
            .groupby(["area_std", "data_ym", "daytype", "기준일ID"], as_index=False)["총생활인구수"]
            .sum()
        )
        monthly_c = (
            daily_c.groupby(["area_std", "data_ym", "daytype"], as_index=False)["총생활인구수"]
            .mean()
            .rename(columns={"총생활인구수": "avg_pop"})
            .sort_values("data_ym")
        )
        # 월축을 datetime으로 고정해 숫자 축(콤마) 문제를 제거
        monthly_c["month_dt"] = pd.to_datetime(
            monthly_c["data_ym"].astype(str) + "01",
            format="%Y%m%d",
            errors="coerce",
        )

        fig = go.Figure()
        for area in AREAS:
            for dt in ["평일", "주말"]:
                d = monthly_c[(monthly_c["area_std"] == area) & (monthly_c["daytype"] == dt)]
                fig.add_trace(go.Scatter(
                    x=d["month_dt"], y=d["avg_pop"],
                    name=f"{area} · {dt}",
                    mode="lines+markers",
                    line=dict(color=AREA_COLORS[area], width=2.5,
                              dash=DAYTYPE_DASH[dt]),
                    marker=dict(size=6,
                                symbol="circle" if dt == "평일" else "diamond"),
                    hovertemplate="%{x|%Y.%m}<br>%{y:,.0f}명/일<extra>" + f"{area} {dt}" + "</extra>",
                ))

        fig.update_layout(
            title=f"월별 일평균 생활인구 · 평일 vs 주말 — {chart_scope_label}",
            xaxis_title="월 (YYYY.MM)",
            yaxis_title="일평균 생활인구 (명/일)",
            legend=dict(orientation="h", yanchor="bottom", y=1.04, xanchor="center", x=0.5),
            plot_bgcolor="#fff", paper_bgcolor="#F4F5F7",
            height=544, hovermode="x unified",
            margin=dict(l=70, r=20, t=90, b=40),
        )
        fig.update_yaxes(tickformat=",", gridcolor="#EFEFEF")
        fig.update_xaxes(
            gridcolor="#EFEFEF",
            tickformat="%Y.%m",
            dtick="M1",
            tickangle=0,
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown(
            "<div class='note-box'>"
            "※ 평일=월~금, 주말=토~일 · 실선=평일, 점선=주말<br>"
            "※ 동을 선택하면(지도 클릭/드롭다운) + '동별 비교' 모드에서 해당 동만 필터"
            "</div>",
            unsafe_allow_html=True
        )

    # ── 모드 2: 시간대별 (평일/주말) ─────────────────────────────────────
    else:
        # 시간대 차트 기준 월 필터
        if hour_month_sel == "최근월":
            target_month = max(lp_chart["data_ym"].astype(str)) if not lp_chart.empty else None
            lp_hour = lp_chart[lp_chart["data_ym"].astype(str) == target_month] if target_month else lp_chart.iloc[0:0]
            month_label = f"{target_month[:4]}.{target_month[4:6]}" if target_month else "데이터 없음"
        elif hour_month_sel == "전체평균":
            lp_hour = lp_chart
            month_label = "전체평균"
        else:
            target_month = str(hour_month_sel)
            lp_hour = lp_chart[lp_chart["data_ym"].astype(str) == target_month]
            month_label = f"{target_month[:4]}.{target_month[4:6]}"

        hourly = (
            lp_hour.dropna(subset=["date"])
            .groupby(["area_std", "시간대구분", "daytype"], as_index=False)["총생활인구수"]
            .mean()
            .rename(columns={"총생활인구수": "avg_pop"})
            .sort_values("시간대구분")
        )

        fig = go.Figure()
        for area in AREAS:
            for dt in ["평일", "주말"]:
                d = hourly[(hourly["area_std"] == area) & (hourly["daytype"] == dt)]
                fig.add_trace(go.Scatter(
                    x=d["시간대구분"], y=d["avg_pop"],
                    name=f"{area} · {dt}",
                    mode="lines+markers",
                    line=dict(color=AREA_COLORS[area], width=2.5,
                              dash=DAYTYPE_DASH[dt]),
                    marker=dict(size=6,
                                symbol="circle" if dt == "평일" else "diamond"),
                    hovertemplate="시간대 %{x}<br>%{y:,.0f}명<extra>" + f"{area} {dt}" + "</extra>",
                ))

        fig.update_layout(
            title=f"시간대별 평균 생활인구 · 평일 vs 주말 — {chart_scope_label} (기준월: {month_label})",
            xaxis_title="시간대 (0~23)",
            yaxis_title="평균 생활인구 (명)",
            legend=dict(orientation="h", yanchor="bottom", y=1.04, xanchor="center", x=0.5),
            plot_bgcolor="#fff", paper_bgcolor="#F4F5F7",
            height=544, hovermode="x unified",
            margin=dict(l=70, r=20, t=90, b=40),
        )
        fig.update_yaxes(tickformat=",", gridcolor="#EFEFEF")
        fig.update_xaxes(gridcolor="#EFEFEF", dtick=1)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown(
            "<div class='note-box'>"
            "※ 시간대구분 0~19 (서울 열린데이터 기준 0=00시, 19=19시 이후 합산)<br>"
            "※ 사이드바에서 기준월(전체평균/최근월/특정월) 선택 가능<br>"
            "※ 실선=평일, 점선=주말 · 동을 선택하면 해당 동만 필터"
            "</div>",
            unsafe_allow_html=True
        )
elif page == "4":
    st.markdown(
        "<div style='font-size:1.6rem; font-weight:800; color:#1E1B4B; "
        "padding:0 0 6px 0; margin-top:0; line-height:1.2'>방문자 출신지</div>",
        unsafe_allow_html=True
    )
    st.markdown("---")

    consumer = load_consumer_region()
    hjd_geo = load_hjd_geojson()

    # area 정규화
    AREA_RAW_TO_STD = {"성수동": "성수동", "이태원한남": "이태원한남", "홍대합정": "홍대합정"}
    consumer["area_std"] = consumer["area"].map(AREA_RAW_TO_STD).fillna(consumer["area"])

    # 방문자 유형 필터
    visitor_sel = st.session_state.get("p4_visitor", "내국인")
    if visitor_sel == "내국인":
        c = consumer[consumer["visitor_type"].astype(str).str.contains("내국", na=False)].copy()
    elif visitor_sel == "외국인":
        c = consumer[consumer["visitor_type"].astype(str).str.contains("외국", na=False)].copy()
    else:
        c = consumer.copy()

    # 시군구 수준(5자리)만 사용
    c5 = c[c["region_len"] == 5].copy()

    # GeoJSON feature를 시군구 단위로 준비 (행정동 경계를 시군구 집계색으로 표현)
    scope = st.session_state.get("p4_scope", "서울시")
    if scope == "서울시":
        valid_sido = {"서울특별시"}
        region_title = "서울시 자치구"
    else:
        valid_sido = {"서울특별시", "경기도", "인천광역시"}
        region_title = "수도권 시군구"

    feature_list = [
        f for f in hjd_geo["features"]
        if f["properties"].get("sidonm") in valid_sido
    ]

    # 권역별 지도 3개
    st.markdown(
        f"<div style='font-size:0.92rem; font-weight:700; margin-bottom:6px'>"
        f"권역별 방문자 유입 분포 ({region_title})"
        f"<span style='font-size:0.72rem; color:#888; font-weight:400; margin-left:8px'>"
        f"동 경계에 시군구 집계색을 입힌 단계구분도</span></div>",
        unsafe_allow_html=True
    )

    # 전권역 공통 스케일
    area_sgg = (
        c5.groupby(["area_std", "region_code", "region_nm"], as_index=False)["visit_cnt"]
        .sum()
    )
    global_vals = area_sgg["visit_cnt"].values
    gmin = float(np.min(global_vals)) if len(global_vals) else 0.0
    gmax = float(np.max(global_vals)) if len(global_vals) else 1.0

    def _sgg_color(v, base_rgb):
        t = (v - gmin) / (gmax - gmin) if gmax > gmin else 0.5
        t = np.clip(t, 0, 1)
        t = 0.20 + 0.80 * t
        r = int(255 - t * (255 - base_rgb[0]))
        g = int(255 - t * (255 - base_rgb[1]))
        b = int(255 - t * (255 - base_rgb[2]))
        return f"#{r:02X}{g:02X}{b:02X}"

    BASE_RGB = {"성수동": (160, 90, 255), "이태원한남": (254, 148, 150), "홍대합정": (27, 207, 180)}
    MAP_CENTER = {"서울시": [37.56, 126.99], "수도권": [37.45, 127.10]}
    MAP_ZOOM = {"서울시": 11, "수도권": 9}

    map_cols = st.columns(3)
    for i, area in enumerate(AREAS):
        base_rgb = BASE_RGB[area]
        m = folium.Map(location=MAP_CENTER[scope], zoom_start=MAP_ZOOM[scope], tiles="CartoDB positron")

        d = area_sgg[area_sgg["area_std"] == area].copy()
        code_to_val = dict(zip(d["region_code"], d["visit_cnt"]))
        code_to_nm = dict(zip(d["region_code"], d["region_nm"]))

        for feat in feature_list:
            props = feat["properties"]
            sgg_code = str(props.get("sgg", ""))
            sgg_name = str(props.get("sggnm", ""))
            visit = float(code_to_val.get(sgg_code, 0.0))
            fill = _sgg_color(visit, base_rgb) if visit > 0 else "#F2F3F5"

            folium.GeoJson(
                feat,
                style_function=lambda _f, fc=fill: {
                    "fillColor": fc,
                    "color": "#B8BCC6",
                    "weight": 0.35,
                    "fillOpacity": 0.80,
                },
                tooltip=folium.Tooltip(
                    f"{sgg_name}<br>{int(visit):,}명",
                    style="font-size:12px;"
                ),
            ).add_to(m)

        with map_cols[i]:
            st.markdown(
                f"<div class='map-label' style='color:{AREA_COLORS[area]}'>● {area}</div>",
                unsafe_allow_html=True
            )
            st_folium(m, width="100%", height=520, returned_objects=[], key=f"map4_{scope}_{area}")

    # 범례
    st.markdown(
        "<div style='display:flex; align-items:center; gap:8px; margin:6px 0 10px 0;font-size:0.71rem; color:#666'>"
        "<span>적음</span>"
        "<div style='width:140px; height:9px; border-radius:4px;background:linear-gradient(to right, #F3F4F6, #A05AFF);'></div>"
        "<span>많음</span>"
        f"<span style='margin-left:10px; color:#999'>방문자수 최소 {gmin:,.0f} · 최대 {gmax:,.0f} (공통스케일)</span>"
        "</div>",
        unsafe_allow_html=True
    )

    # 하단 차트(아이디어): 월별 유입구조 / 상위 유입지역
    chart_mode = st.session_state.get("p4_chart", "월별 유입구조")
    if chart_mode == "월별 유입구조":
        tmp = c5.copy()
        if scope == "서울시":
            tmp["geo_group"] = np.where(tmp["region_code"].str.startswith("11"), "서울시", "기타")
        else:
            tmp["geo_group"] = np.where(tmp["region_code"].str.startswith("11"), "서울",
                                np.where(tmp["region_code"].str.startswith("28"), "인천",
                                np.where(tmp["region_code"].str.startswith("41"), "경기", "기타")))
        g = tmp.groupby(["area_std", "ym", "geo_group"], as_index=False)["visit_cnt"].sum()
        g["ym_dt"] = pd.to_datetime(g["ym"] + "01", format="%Y%m%d", errors="coerce")

        fig = go.Figure()
        for area in AREAS:
            d = g[g["area_std"] == area].copy()
            if d.empty:
                continue
            pivot = d.pivot_table(index="ym_dt", columns="geo_group", values="visit_cnt", aggfunc="sum", fill_value=0)
            pivot["total"] = pivot.sum(axis=1)
            if scope == "서울시":
                pivot["target_share"] = np.where(pivot["total"] > 0, pivot.get("서울시", 0) / pivot["total"] * 100, 0)
            else:
                pivot["target_share"] = np.where(pivot["total"] > 0, (pivot.get("서울", 0) + pivot.get("경기", 0) + pivot.get("인천", 0)) / pivot["total"] * 100, 0)
            fig.add_trace(go.Scatter(
                x=pivot.index, y=pivot["target_share"],
                mode="lines+markers",
                name=area,
                line=dict(color=AREA_COLORS[area], width=2.8),
                marker=dict(size=7),
                hovertemplate="%{x|%Y.%m}<br>%{y:.1f}%<extra>" + area + "</extra>",
            ))

        fig.update_layout(
            title=f"권역별 월간 유입구조 비율 ({region_title} 비중)",
            xaxis_title="월 (YYYY.MM)",
            yaxis_title="비중 (%)",
            legend=dict(orientation="h", yanchor="bottom", y=1.04, xanchor="center", x=0.5),
            plot_bgcolor="#fff", paper_bgcolor="#F4F5F7",
            height=544, hovermode="x unified",
            margin=dict(l=70, r=20, t=90, b=40),
        )
        fig.update_yaxes(range=[0, 100], gridcolor="#EFEFEF")
        fig.update_xaxes(gridcolor="#EFEFEF", tickformat="%Y.%m", dtick="M1")
        st.plotly_chart(fig, use_container_width=True)
        st.markdown(
            "<div class='note-box'>"
            "※ 차트는 지역권역 내부(서울시 또는 수도권)에서 발생한 유입 비중을 월별로 보여줍니다.<br>"
            "※ 절대 방문자 규모는 지도에서, 구조 변화는 이 차트에서 함께 해석하세요."
            "</div>",
            unsafe_allow_html=True
        )
    else:
        # 상위 유입지역: 권역별 Top N 가로막대
        topn = 12
        rank_rows = []
        for area in AREAS:
            d = c5[c5["area_std"] == area].copy()
            if scope == "서울시":
                d = d[d["region_code"].str.startswith("11")]
            else:
                d = d[d["region_code"].str.startswith(("11", "28", "41"))]
            g = d.groupby(["region_code", "region_nm"], as_index=False)["visit_cnt"].sum()
            g = g.sort_values("visit_cnt", ascending=False).head(topn)
            g["area_std"] = area
            rank_rows.append(g)
        out = pd.concat(rank_rows, ignore_index=True) if rank_rows else pd.DataFrame(columns=["region_nm", "visit_cnt", "area_std"])

        fig = px.bar(
            out,
            x="visit_cnt",
            y="region_nm",
            color="area_std",
            facet_col="area_std",
            orientation="h",
            category_orders={"area_std": AREAS},
            color_discrete_map=AREA_COLORS,
            title=f"권역별 상위 유입 {region_title} Top {topn}",
        )
        fig.update_layout(
            plot_bgcolor="#fff", paper_bgcolor="#F4F5F7",
            height=544, margin=dict(l=30, r=20, t=90, b=40),
            showlegend=False,
        )
        fig.update_xaxes(tickformat=",", gridcolor="#EFEFEF")
        fig.update_yaxes(gridcolor="#EFEFEF")
        st.plotly_chart(fig, use_container_width=True)
        st.markdown(
            "<div class='note-box'>"
            "※ 권역별 방문자 유입 상위 지역을 비교해 '어디서 많이 오는지'를 빠르게 확인할 수 있습니다."
            "</div>",
            unsafe_allow_html=True
        )
elif page == "5":
    st.markdown(
        "<div style='font-size:1.6rem; font-weight:800; color:#1E1B4B; "
        "padding:0 0 6px 0; margin-top:0; line-height:1.2'>상권집중도 · 방문성과지표</div>",
        unsafe_allow_html=True
    )
    st.markdown("---")

    naver, _public = load_page1_data()
    stores, sales = load_data()

    # 데이터 정규화
    naver = naver.copy()
    naver["area_std"] = naver["area"].map(AREA_NORM)
    naver["lat"] = pd.to_numeric(naver.get("y"), errors="coerce")
    naver["lon"] = pd.to_numeric(naver.get("x"), errors="coerce")
    naver["visitor_review"] = pd.to_numeric(naver.get("visitor_review"), errors="coerce").fillna(0)
    naver["blog_review"] = pd.to_numeric(naver.get("blog_review"), errors="coerce").fillna(0)
    naver["total_review"] = pd.to_numeric(naver.get("total_review"), errors="coerce").fillna(
        naver["visitor_review"] + naver["blog_review"]
    )

    stores = stores.copy()
    stores["lat"] = pd.to_numeric(stores.get("lat"), errors="coerce")
    stores["lon"] = pd.to_numeric(stores.get("lon"), errors="coerce")

    sales = sales.copy()
    sales["sales_cnt"] = pd.to_numeric(sales.get("sales_cnt"), errors="coerce").fillna(0)
    latest_yms = sorted(sales["ym"].astype(str).unique().tolist())[-3:]
    recent = sales[sales["ym"].astype(str).isin(latest_yms)].copy()
    sales_store = (
        recent.groupby("store_id", as_index=False)["sales_cnt"].sum()
        .rename(columns={"sales_cnt": "sales_cnt_3m"})
    )
    store_rank = stores.merge(sales_store, on="store_id", how="left")
    store_rank["sales_cnt_3m"] = store_rank["sales_cnt_3m"].fillna(0)

    rank_metric = st.session_state.get("p5_rank_metric", "매출건수 Top 10")

    # 상단 지도 지표 토글 (매출건수 / 리뷰수)
    top_l, top_r = st.columns([8, 2])
    with top_r:
        if "p5_map_metric" not in st.session_state:
            st.session_state.p5_map_metric = "매출건수"
        m1 = "primary" if st.session_state.p5_map_metric == "매출건수" else "secondary"
        m2 = "primary" if st.session_state.p5_map_metric == "리뷰수" else "secondary"
        cbtn1, cbtn2 = st.columns(2)
        with cbtn1:
            if st.button("매출건수", key="p5_map_sales", type=m1, use_container_width=True):
                st.session_state.p5_map_metric = "매출건수"
                st.rerun()
        with cbtn2:
            if st.button("리뷰수", key="p5_map_review", type=m2, use_container_width=True):
                st.session_state.p5_map_metric = "리뷰수"
                st.rerun()

    st.markdown(
        "<div style='font-size:0.92rem; font-weight:700; margin-bottom:6px'>"
        "권역별 핵심 점포/시설 분포"
        "<span style='font-size:0.72rem; color:#888; font-weight:400; margin-left:8px'>"
        "원 크기 = 선택 지표 크기</span></div>",
        unsafe_allow_html=True
    )

    # 지도 3개 (height=520)
    map_metric = st.session_state.get("p5_map_metric", "매출건수")
    map_cols = st.columns(3)
    for i, area in enumerate(AREAS):
        m = folium.Map(location=AREA_CENTERS[area], zoom_start=15, tiles="CartoDB positron")

        if map_metric == "매출건수":
            d = store_rank[store_rank["area"] == area].dropna(subset=["lat", "lon"]).copy()
            vmax = float(d["sales_cnt_3m"].max()) if not d.empty else 1.0
            vmax = vmax if vmax > 0 else 1.0
            for _, r in d.iterrows():
                v = float(r["sales_cnt_3m"])
                radius = 4 + 16 * (v / vmax)
                folium.CircleMarker(
                    location=[float(r["lat"]), float(r["lon"])],
                    radius=radius,
                    color="#ffffff",
                    weight=1,
                    fill=True,
                    fill_color=AREA_COLORS[area],
                    fill_opacity=0.78,
                    tooltip=f"{r.get('store_nm','')}<br>매출건수(최근3개월): {int(v):,}",
                ).add_to(m)
        else:
            d = naver[naver["area_std"] == area].dropna(subset=["lat", "lon"]).copy()
            vmax = float(d["total_review"].max()) if not d.empty else 1.0
            vmax = vmax if vmax > 0 else 1.0
            for _, r in d.iterrows():
                v = float(r["total_review"])
                radius = 4 + 16 * (v / vmax)
                folium.CircleMarker(
                    location=[float(r["lat"]), float(r["lon"])],
                    radius=radius,
                    color="#ffffff",
                    weight=1,
                    fill=True,
                    fill_color=AREA_COLORS[area],
                    fill_opacity=0.78,
                    tooltip=f"{r.get('name','')}<br>리뷰수: {int(v):,}",
                ).add_to(m)

        with map_cols[i]:
            st.markdown(
                f"<div class='map-label' style='color:{AREA_COLORS[area]}'>● {area}</div>",
                unsafe_allow_html=True
            )
            st_folium(m, width="100%", height=520, returned_objects=[], key=f"map5_{area}_{map_metric}")

    # 하단 테이블 3개 (height=544 체감 맞춤: 테이블 높이 키움)
    st.markdown(
        "<div style='font-size:0.92rem; font-weight:700; margin:10px 0 6px 0'>"
        f"{rank_metric} · 권역별 Top 10"
        "</div>",
        unsafe_allow_html=True
    )

    tbl_cols = st.columns(3)
    for i, area in enumerate(AREAS):
        with tbl_cols[i]:
            st.markdown(
                f"<div class='map-label' style='color:{AREA_COLORS[area]}'>● {area}</div>",
                unsafe_allow_html=True
            )
            if rank_metric == "매출건수 Top 10":
                d = (
                    store_rank[store_rank["area"] == area]
                    .sort_values("sales_cnt_3m", ascending=False)
                    .head(10)[["store_nm", "cat_mi", "sales_cnt_3m"]]
                    .rename(columns={"store_nm": "매장명", "cat_mi": "업종", "sales_cnt_3m": "매출건수(3개월)"})
                )
            elif rank_metric == "방문자리뷰 Top 10":
                d = (
                    naver[naver["area_std"] == area]
                    .sort_values("visitor_review", ascending=False)
                    .head(10)[["name", "category_main", "visitor_review"]]
                    .rename(columns={"name": "시설명", "category_main": "분류", "visitor_review": "방문자리뷰"})
                )
            else:
                d = (
                    naver[naver["area_std"] == area]
                    .sort_values("blog_review", ascending=False)
                    .head(10)[["name", "category_main", "blog_review"]]
                    .rename(columns={"name": "시설명", "category_main": "분류", "blog_review": "블로그리뷰"})
                )
            st.dataframe(d.reset_index(drop=True), use_container_width=True, height=500)
