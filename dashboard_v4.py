"""
문화시설 빅데이터 대시보드 v4
- Page1(장소 공급 현황) 중심 개편
- 차트 탐색(A/B): 왼쪽 사이드바
- 지도 마커: 원천 카테고리 색상 표현
"""

from __future__ import annotations

import json
from pathlib import Path
import math

import folium
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from streamlit_folium import st_folium


# ── 기본 설정 ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="문화시설 빅데이터 대시보드 v4",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ── 스타일 ─────────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
[data-testid="stAppViewContainer"] { background: #F4F5F7; }
header[data-testid="stHeader"] { background: #F4F5F7 !important; border-bottom: none !important; }
.block-container { padding-top: 4.2rem !important; padding-bottom: 0.5rem !important; max-width: 100% !important; }
[data-testid="stVerticalBlock"] > div { gap: 0.5rem !important; }
[data-testid="stSidebar"] { background: #FFFFFF !important; border-right: 1px solid #EDEEF2; }
[data-testid="stSidebar"] * { color: #2D2D3A !important; }
[data-testid="stSidebar"] .stButton > button {
    background: transparent !important; color: #6B6B7D !important;
    border: none !important; border-radius: 6px !important; text-align: left !important;
    justify-content: flex-start !important; padding: 9px 14px !important; margin: 1px 0 !important;
    font-size: 0.88rem !important; font-weight: 500 !important; box-shadow: none !important;
}
[data-testid="stSidebar"] .stButton > button:hover { background: #F5F2FF !important; color: #A05AFF !important; }
[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    color: #A05AFF !important; font-weight: 700 !important; border-left: 3px solid #A05AFF !important;
    border-radius: 0 6px 6px 0 !important;
}
/* 차트 탐색 블록: 테마 포인트 컬러 */
.sidebar-chart-explore {
    margin-top: 0.75rem; padding: 12px 10px 14px 10px;
    border-radius: 10px; border: 1px solid #EDEEF2; background: linear-gradient(180deg, #FAFAFF 0%, #FFFFFF 100%);
    box-shadow: 0 1px 3px rgba(160, 90, 255, 0.06);
}
.sidebar-chart-explore h3 {
    font-size: 0.82rem !important; font-weight: 700 !important; letter-spacing: 0.02em;
    color: #1E1B4B !important; margin: 0 0 10px 0 !important; padding-bottom: 8px !important;
    border-bottom: 2px solid #A05AFF !important;
}
.kpi-card {
    border-radius: 14px; padding: 20px 22px; color: #fff; position: relative; overflow: hidden;
    box-shadow: 0 4px 14px rgba(0,0,0,0.08); min-height: 112px;
}
.kpi-label { font-size: 0.86rem; font-weight: 600; opacity: 0.95; margin-bottom: 8px; }
.kpi-value { font-size: 1.9rem; font-weight: 800; line-height: 1.1; }
.kpi-unit  { font-size: 0.72rem; font-weight: 500; opacity: 0.85; margin-left: 4px; }
.kpi-sub   { font-size: 0.72rem; opacity: 0.85; margin-top: 8px; }
.note-box {
    background: #FAFAFA; border-left: 3px solid #E0E0E0;
    padding: 8px 12px; border-radius: 4px; font-size: 0.74rem; color: #777; line-height: 1.6;
}
/* 본문 '하단 탐색 영역' 제목 ↔ 사이드바 '차트 탐색' expander 헤더 타이포 정렬 */
h3.bottom-zone-title {
    font-size: 1.17rem !important; font-weight: 800 !important; color: #1E1B4B !important;
    margin: 0 0 6px 0 !important; line-height: 1.35 !important;
}
[data-testid="stSidebar"] div[data-testid="stExpander"] summary {
    font-size: 1.17rem !important; font-weight: 800 !important; color: #1E1B4B !important;
    line-height: 1.35 !important;
}
</style>
""",
    unsafe_allow_html=True,
)


# ── 경로/상수 ──────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent

# GitHub 배포용: 데이터 파일은 스크립트와 같은 폴더(BASE_DIR)에 둡니다.
P_NAVER = BASE_DIR / "culture_data_clean.csv"
P_PUBLIC = BASE_DIR / "서울시_공공문화시설_10개동.csv"
P_LOCALPPL = BASE_DIR / "LOCAL_PEOPLE_DONG_three_zones_merged_202503_202602.csv"
# 3권역 10개 행정동 경계 (대시보드 폴더, v3와 동일 소스)
P_BOUNDARY_GEOJSON = BASE_DIR / "seoul_dong_boundary.geojson"

AREAS_STD = ["성수동", "이태원한남", "홍대합정"]
# GeoJSON `dong` → 대시보드 권역명 (seoul_dong_boundary.geojson 속성과 일치)
DONG_TO_AREA_STD: dict[str, str] = {
    "이태원1동": "이태원한남",
    "이태원2동": "이태원한남",
    "한남동": "이태원한남",
    "성수1가1동": "성수동",
    "성수1가2동": "성수동",
    "성수2가1동": "성수동",
    "성수2가3동": "성수동",
    "서교동": "홍대합정",
    "합정동": "홍대합정",
    "서강동": "홍대합정",
}
AREA_COLORS = {"성수동": "#A05AFF", "이태원한남": "#FE9496", "홍대합정": "#1BCFB4"}
AREA_CENTERS = {
    "성수동": [37.5445, 127.0557],
    "이태원한남": [37.5340, 126.9944],
    "홍대합정": [37.5503, 126.9218],
}
AREA_NORM = {"성수": "성수동", "이태원한남": "이태원한남", "홍대": "홍대합정"}

MAP_HEIGHT = int(420 * 1.4)
# 하단 현황: 차트·표 상단 정렬용(제목은 plotly 밖에서 공통 표시)
STATUS_BLOCK_H = 460
# B 분석: 표 높이 = 우측 그래프와 맞춤
B_ROW1_CHART_H = 380
B_ROW2_CHART_H = 400

# 업로드 스펙트럼 참고 팔레트 (지도·Lift 도넛 공통)
SPECTRUM = [
    "#B0004A",
    "#D73A52",
    "#F36C3D",
    "#F2A85C",
    "#EBCF80",
    "#DFE4A7",
    "#CCD980",
    "#9DCB8F",
    "#6AB89D",
    "#3F8BB9",
    "#6358A8",
]


def make_color_map(labels: list[str]) -> dict[str, str]:
    labels_sorted = sorted([str(x) for x in labels if pd.notna(x)])
    cmap: dict[str, str] = {}
    for i, lb in enumerate(labels_sorted):
        cmap[lb] = SPECTRUM[i % len(SPECTRUM)]
    return cmap


def append_footer_sums(
    df: pd.DataFrame,
    area_cols: list[str],
    *,
    cat_col: str = "category",
    label: str = "(표시 범위 권역 합계)",
    include_total: bool = True,
    count_as_integer: bool = False,
) -> pd.DataFrame:
    """카테고리 표 아래에 권역별 열 합계 행 추가(건수·비중(%) 공통)."""
    out = df.copy()
    foot: dict = {cat_col: label}
    for c in area_cols:
        if c in out.columns:
            foot[c] = float(pd.to_numeric(out[c], errors="coerce").fillna(0).sum())
    if include_total and "total" in out.columns:
        foot["total"] = float(pd.to_numeric(out["total"], errors="coerce").fillna(0).sum())
    if count_as_integer:
        for c in area_cols:
            if c in foot:
                foot[c] = int(round(foot[c]))
        if include_total and "total" in foot:
            foot["total"] = int(round(foot["total"]))
    else:
        for c in area_cols:
            if c in foot:
                foot[c] = round(foot[c], 2)
    return pd.concat([out, pd.DataFrame([foot])], ignore_index=True)


def ym_to_label(v) -> str:
    """data_ym(문자/숫자) → 'YYYY-MM' (Plotly에 숫자 ym만 넣으면 ms로 오인식되어 축이 1970년대로 깨짐)."""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return ""
    s = str(v).strip()
    if "." in s and s.replace(".", "").isdigit():
        s = s.split(".")[0]
    s = "".join(ch for ch in s if ch.isdigit())
    if len(s) >= 6:
        return f"{s[:4]}-{s[4:6]}"
    return s


@st.cache_data
def load_seoul_boundary_geojson() -> dict:
    """3권역 10개 행정동 경계 GeoJSON (`7_dashboard/seoul_dong_boundary.geojson`)."""
    if not P_BOUNDARY_GEOJSON.exists():
        return {"type": "FeatureCollection", "features": []}
    with open(P_BOUNDARY_GEOJSON, encoding="utf-8") as f:
        return json.load(f)


def feature_centroid_latlon(feature: dict) -> tuple[float, float]:
    """GeoJSON Feature 폴리곤 대표점(꼭짓점 평균) → Folium용 [lat, lon]."""
    geom = feature.get("geometry") or {}
    coords = geom.get("coordinates")
    geo_type = geom.get("type")
    pts: list = []
    if geo_type == "Polygon" and coords:
        pts = coords[0]
    elif geo_type == "MultiPolygon" and coords:
        for poly in coords:
            if poly:
                pts.extend(poly[0])
    if not pts:
        return 37.55, 127.0
    avg_lon = sum(p[0] for p in pts) / len(pts)
    avg_lat = sum(p[1] for p in pts) / len(pts)
    return avg_lat, avg_lon


def boundary_geojson_for_area(geojson_data: dict, area_std: str) -> dict:
    """권역별로 해당하는 행정동 폴리곤만 담은 FeatureCollection."""
    out: list[dict] = []
    for feat in geojson_data.get("features", []):
        dong = str((feat.get("properties") or {}).get("dong", "")).strip()
        if DONG_TO_AREA_STD.get(dong) == area_std:
            out.append(feat)
    return {"type": "FeatureCollection", "features": out}


def add_boundary_and_labels(fmap: folium.Map, area_std: str, geojson_data: dict) -> None:
    """행정경계(얇은 선) + 동 이름 라벨을 지도에 겹침."""
    gj = boundary_geojson_for_area(geojson_data, area_std)
    if not gj.get("features"):
        return
    folium.GeoJson(
        gj,
        style_function=lambda _feat: {
            "fillColor": "#000000",
            "color": "#5c5c5c",
            "weight": 1,
            "fillOpacity": 0.0,
        },
    ).add_to(fmap)
    for feat in gj["features"]:
        dong = str((feat.get("properties") or {}).get("dong", "")).strip()
        if not dong:
            continue
        lat, lon = feature_centroid_latlon(feat)
        folium.Marker(
            location=[lat, lon],
            icon=folium.DivIcon(
                html=(
                    f'<div style="font-size:10px;font-weight:700;color:#1e293b;'
                    f'text-shadow:0 0 4px #fff,0 0 6px #fff;white-space:nowrap;">{dong}</div>'
                ),
                icon_size=(120, 16),
                icon_anchor=(60, 8),
            ),
        ).add_to(fmap)


# ── 데이터 로드 ────────────────────────────────────────────────────────────
@st.cache_data
def load_page1_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    naver = pd.read_csv(P_NAVER, encoding="utf-8-sig")
    public = pd.read_csv(P_PUBLIC, encoding="utf-8-sig")
    lp = pd.read_csv(P_LOCALPPL, encoding="utf-8-sig")

    naver["area_std"] = naver["area"].map(AREA_NORM)
    naver["lat"] = pd.to_numeric(naver["y"], errors="coerce")
    naver["lon"] = pd.to_numeric(naver["x"], errors="coerce")
    naver["cat_src"] = naver["category"].astype(str)
    naver["name_src"] = naver["name"].astype(str)

    perf_kw = ["홀", "스테이지", "Stage", "STAGE", "라이브", "클럽", "인디팍", "벨로주", "가가"]

    def reclassify_public(row: pd.Series) -> str:
        sub = str(row.get("소분류", ""))
        nm = str(row.get("시설명", ""))
        if sub in ["공연장", "문화예술회관"]:
            return "공연장"
        if sub == "미술관/갤러리":
            return "전시·갤러리"
        if sub == "박물관/기념관":
            return "박물관/기념관"
        if sub == "도서관":
            return "도서관"
        if any(k in nm for k in perf_kw):
            return "공연장"
        return "복합·생활문화"

    public["area_std"] = public["area"].map(AREA_NORM)
    public["lat"] = pd.to_numeric(public["lat"], errors="coerce")
    public["lon"] = pd.to_numeric(public["lon"], errors="coerce")
    public["cat_src"] = public.apply(reclassify_public, axis=1)
    public["name_src"] = public["시설명"].astype(str)

    lp["기준일ID"] = pd.to_numeric(lp["기준일ID"], errors="coerce").fillna(0).astype(int).astype(str)
    # 역지오/병합 과정에서 0·결측 일자가 섞이면 월 집계·축이 깨짐 → 유효 8자리(YYYYMMDD)만 사용
    lp = lp[lp["기준일ID"].str.match(r"^[12]\d{7}$", na=False)].copy()
    lp["date"] = pd.to_datetime(lp["기준일ID"], format="%Y%m%d", errors="coerce")
    lp["총생활인구수"] = pd.to_numeric(lp["총생활인구수"], errors="coerce").fillna(0.0)
    lp["dow"] = lp["date"].dt.dayofweek
    lp["daytype"] = np.where(lp["dow"] >= 5, "주말", "평일")
    lp["area_std"] = (
        lp["zone"].astype(str).str.strip().map(
            {"성수": "성수동", "이태원한남": "이태원한남", "홍대권": "홍대합정"}
        )
    )
    lp["data_ym"] = lp["data_ym"].astype(str).str.replace(r"\.0$", "", regex=True)

    return naver, public, lp


def get_pop_metrics(lp: pd.DataFrame, area_std: str) -> tuple[float, float, float]:
    d = lp[lp["area_std"] == area_std].copy()
    if d.empty:
        return 0.0, 0.0, 0.0
    g = d.groupby(["기준일ID", "시간대구분"], as_index=False)["총생활인구수"].sum()
    day_meta = d.drop_duplicates("기준일ID")[["기준일ID", "daytype"]]
    per_day = g.groupby("기준일ID", as_index=False)["총생활인구수"].mean().rename(
        columns={"총생활인구수": "daily_hourly_mean"}
    )
    per_day = per_day.merge(day_meta, on="기준일ID", how="left")
    wknd = float(per_day.loc[per_day["daytype"] == "주말", "daily_hourly_mean"].mean())
    wkdy = float(per_day.loc[per_day["daytype"] == "평일", "daily_hourly_mean"].mean())
    peak = float(g.groupby("시간대구분")["총생활인구수"].mean().max())
    return wknd, wkdy, peak


@st.cache_data
def monthly_zone_avg_population(lp: pd.DataFrame) -> pd.DataFrame:
    """권역·월별: 일자별 권역 시간대 합계의 시간평균 → 월 평균 (권역별 월별 추이선용)."""
    d = lp.dropna(subset=["기준일ID", "area_std", "data_ym"]).copy()
    d = d[d["기준일ID"].astype(str).str.match(r"^[12]\d{7}$", na=False)].copy()
    if d.empty:
        return pd.DataFrame(columns=["data_ym", "area_std", "월평균_일별_체류인구", "data_ym_label"])
    # 시간대·권역·일자: 동 단위 합 = 권역 해당 시각 총생활인구
    zh = d.groupby(["기준일ID", "시간대구분", "area_std"], as_index=False)["총생활인구수"].sum()
    # 일자·권역: 하루 시간대 평균 ≈ 일별 평균 체류 규모
    daily = zh.groupby(["기준일ID", "area_std"], as_index=False)["총생활인구수"].mean()
    daily["data_ym"] = daily["기준일ID"].str.slice(0, 6)
    out = (
        daily.groupby(["data_ym", "area_std"], as_index=False)["총생활인구수"]
        .mean()
        .rename(columns={"총생활인구수": "월평균_일별_체류인구"})
    )
    # 반드시 문자열 월 라벨 (숫자 ym만 x에 넣으면 Plotly 축 오류)
    out["data_ym_label"] = out["data_ym"].map(ym_to_label)
    out = out[out["data_ym_label"].astype(str).str.len() >= 7].copy()
    return out.sort_values(["data_ym", "area_std"])


def calc_diversity_by_area(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for area in AREAS_STD:
        sub = df[df["area_std"] == area]
        vc = sub["cat_src"].value_counts()
        total = vc.sum()
        if total == 0:
            rows.append({
                "권역": area, "시설수": 0, "카테고리수": 0,
                "HHI(집중도)": 0.0, "Entropy(다양도)": 0.0, "효과적_카테고리수": 0.0,
            })
            continue
        p = (vc / total).values
        hhi = float((p ** 2).sum())
        ent = float(-(p * np.log(p)).sum())
        eff = float(np.exp(ent))
        rows.append({
            "권역": area,
            "시설수": int(total),
            "카테고리수": int((vc > 0).sum()),
            "HHI(집중도)": round(hhi, 4),
            "Entropy(다양도)": round(ent, 4),
            "효과적_카테고리수": round(eff, 2),
        })
    return pd.DataFrame(rows)


def calc_lift(df: pd.DataFrame, min_count: int = 3) -> pd.DataFrame:
    out = []
    all_share = df["cat_src"].value_counts(normalize=True)
    for area in AREAS_STD:
        sub = df[df["area_std"] == area]
        vc = sub["cat_src"].value_counts()
        sh = vc / max(vc.sum(), 1)
        for cat, cnt in vc.items():
            if cnt < min_count:
                continue
            s_all = float(all_share.get(cat, np.nan))
            lift = float(sh[cat] / s_all) if s_all and not math.isnan(s_all) else np.nan
            out.append({
                "권역": area,
                "category": cat,
                "count": int(cnt),
                "share_area": float(sh[cat]),
                "share_all": s_all,
                "lift": lift,
            })
    res = pd.DataFrame(out)
    if res.empty:
        return res
    return res.sort_values(["권역", "lift"], ascending=[True, False])


def diversity_radar_figure(div_df: pd.DataFrame, height: int = 400) -> go.Figure:
    """HHI·Entropy·효과적 카테고리 수를 0~1 스케일로 맞춘 레이더."""
    metrics = [
        ("HHI(집중도)", "HHI(집중도)", True),
        ("Entropy(다양도)", "Entropy(다양도)", False),
        ("효과적_카테고리수", "효과적_카테고리수", False),
    ]
    theta = [m[1] for m in metrics]
    fig = go.Figure()
    hhi_max = max(div_df["HHI(집중도)"].max(), 1e-6)
    ent_max = max(div_df["Entropy(다양도)"].max(), 1e-6)
    eff_max = max(div_df["효과적_카테고리수"].max(), 1e-6)
    for _, row in div_df.iterrows():
        area = row["권역"]
        r1 = float(row["HHI(집중도)"]) / hhi_max
        r2 = float(row["Entropy(다양도)"]) / ent_max
        r3 = float(row["효과적_카테고리수"]) / eff_max
        fig.add_trace(
            go.Scatterpolar(
                r=[r1, r2, r3],
                theta=theta,
                fill="toself",
                name=area,
                line_color=AREA_COLORS.get(area, "#888"),
                opacity=0.55,
            )
        )
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1.05], tickformat=".0%")),
        showlegend=True,
        height=height,
        paper_bgcolor="#F4F5F7",
        plot_bgcolor="#fff",
        margin=dict(l=50, r=50, t=28, b=40),
        title=None,
    )
    return fig


# ── 사이드바: 네비 + (Page1) 차트 탐색 ───────────────────────────────────────
st.sidebar.markdown("## THEME")
page_map = {
    "1": "1. 장소 공급 현황",
    "2": "2. 생활인구 (준비중)",
    "3": "3. 매출 분석 (준비중)",
    "4": "4. 소비자 유입 (준비중)",
    "5": "5. 종합 인사이트 (준비중)",
}
if "page" not in st.session_state:
    st.session_state.page = "1"

for pid, label in page_map.items():
    is_active = st.session_state.page == pid
    if st.sidebar.button(label, key=f"nav_{pid}", type="primary" if is_active else "secondary"):
        st.session_state.page = pid

# Page1 전용: 차트 탐색 — 사이드바 expander (헤더 타이포는 CSS로 본문 '하단 탐색 영역'과 맞춤)
if st.session_state.page == "1":
    with st.sidebar.expander("차트 탐색", expanded=True):
        st.markdown(
            '<p style="font-size:0.78rem;color:#6B6B7D;margin:0 0 10px 0;border-left:3px solid #A05AFF;padding-left:8px;">'
            "Page1 · 현황(A) / 분석(B)</p>",
            unsafe_allow_html=True,
        )
        chart_mode = st.segmented_control(
            "보기 모드",
            ["A. 현황 탐색", "B. 분석 지표"],
            default="A. 현황 탐색",
            key="v4_chart_mode",
        )
        # B일 때는 현황(A) 전용 옵션 숨김 → 혼동 방지
        if chart_mode == "A. 현황 탐색":
            st.multiselect(
                "권역 선택", AREAS_STD, default=AREAS_STD, key="v4_area_sel"
            )
            st.radio(
                "표시 단위", ["건수", "비중(%)"], horizontal=True, key="v4_metric_mode"
            )
            st.slider("카테고리 Top N", 5, 20, 10, key="v4_topn")
            st.checkbox("상세 표 보기", value=True, key="v4_show_table")
        else:
            st.markdown("---")
            st.caption("분석 지표 (B) 옵션")
            st.slider("Lift 최소 표본 수(n)", 1, 10, 3, key="v4_min_count")
            st.slider("권역별 Lift Top N", 3, 12, 7, key="v4_topk_lift")


# ── Page1 본문 ───────────────────────────────────────────────────────────────
if st.session_state.page == "1":
    naver, public, lp = load_page1_data()
    monthly_pop = monthly_zone_avg_population(lp)

    st.markdown(
        "<div style='font-size:1.6rem; font-weight:800; color:#1E1B4B; padding:0 0 4px 0'>장소 공급 현황 (v4)</div>",
        unsafe_allow_html=True,
    )
    st.markdown("---")

    c1, c2 = st.columns([1, 1])
    with c1:
        src = st.segmented_control("데이터 소스", ["네이버", "공공"], default="네이버")
    with c2:
        map_cat_topn = st.slider("지도 범례 표시 카테고리 수", min_value=6, max_value=18, value=12, step=1)

    if src == "네이버":
        df = naver.copy()
        src_note = "네이버 문화시설 (원천 category)"
    else:
        df = public.copy()
        src_note = "서울시 공공 문화시설 (재분류 cat_std)"

    st.caption(f"데이터: {src_note}")

    kpi_grad = {
        "성수동": "linear-gradient(135deg, #A05AFF 0%, #C98BFF 100%)",
        "이태원한남": "linear-gradient(135deg, #FE9496 0%, #FFB8A8 100%)",
        "홍대합정": "linear-gradient(135deg, #1BCFB4 0%, #5EE3C9 100%)",
    }
    cols = st.columns(3)
    for i, area in enumerate(AREAS_STD):
        sub = df[df["area_std"] == area]
        cnt = len(sub)
        top_cat = sub["cat_src"].value_counts().idxmax() if cnt > 0 else "-"
        with cols[i]:
            st.markdown(
                f"""
                <div class='kpi-card' style='background:{kpi_grad[area]}'>
                  <div class='kpi-label'>{area} · 시설 수</div>
                  <div class='kpi-value'>{cnt:,}<span class='kpi-unit'>개소</span></div>
                  <div class='kpi-sub'>최다 카테고리: {top_cat}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("#### 권역별 시설 분포 (원천 카테고리 색상)")
    st.caption(
        "행정동 경계는 얇은 회색선으로 표시되며, 동 이름은 해당 구역 중심에 겹쳐 둡니다. "
        f"(경계 데이터: `{P_BOUNDARY_GEOJSON.name}`)"
    )
    cat_counts = df["cat_src"].value_counts()
    shown_cats = list(cat_counts.head(map_cat_topn).index)
    cmap = make_color_map(shown_cats + ["기타"])

    boundary_fc = load_seoul_boundary_geojson()
    mcols = st.columns(3)
    for i, area in enumerate(AREAS_STD):
        sub = df[(df["area_std"] == area)].dropna(subset=["lat", "lon"])
        fmap = folium.Map(location=AREA_CENTERS[area], zoom_start=15, tiles="CartoDB positron")
        add_boundary_and_labels(fmap, area, boundary_fc)
        for _, r in sub.iterrows():
            cat = r["cat_src"]
            cat_key = cat if cat in cmap else "기타"
            folium.CircleMarker(
                location=[r["lat"], r["lon"]],
                radius=5.5,
                color="#ffffff",
                weight=0.8,
                fill=True,
                fill_color=cmap.get(cat_key, "#9CA3AF"),
                fill_opacity=0.85,
                tooltip=f"{r['name_src']}<br>{cat}",
            ).add_to(fmap)
        with mcols[i]:
            st.markdown(f"**{area}**")
            st_folium(
                fmap,
                width="100%",
                height=MAP_HEIGHT,
                returned_objects=[],
                key=f"v4_map_{src}_{area}",
            )

    legend_items = "".join(
        [
            f"<span style='display:inline-flex;align-items:center;margin-right:10px;'>"
            f"<span style='width:10px;height:10px;border-radius:50%;background:{cmap[c]};display:inline-block;margin-right:4px;'></span>{c}</span>"
            for c in shown_cats
        ]
    )
    st.markdown(
        f"<div class='note-box'><b>카테고리 범례</b><br>{legend_items}</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        '<h3 class="bottom-zone-title">하단 탐색 영역</h3>',
        unsafe_allow_html=True,
    )
    st.caption("좌측 사이드바 **차트 탐색**에서 모드·권역·표시 단위를 조정할 수 있습니다.")

    chart_mode = st.session_state.get("v4_chart_mode", "A. 현황 탐색")
    area_sel = st.session_state.get("v4_area_sel", AREAS_STD)
    metric_mode = st.session_state.get("v4_metric_mode", "건수")
    topn = st.session_state.get("v4_topn", 10)
    show_table = st.session_state.get("v4_show_table", True)

    if chart_mode == "A. 현황 탐색":
        if not area_sel:
            st.warning("사이드바에서 권역을 한 곳 이상 선택해 주세요.")
        else:
            d = df[df["area_std"].isin(area_sel)].copy()
            if d.empty:
                st.info("선택 조건에 해당하는 데이터가 없습니다.")
            else:
                ctab = pd.crosstab(d["cat_src"], d["area_std"]).reindex(columns=area_sel, fill_value=0)
                ctab["total"] = ctab.sum(axis=1)
                ctab = ctab.sort_values("total", ascending=False).head(topn)
                plot = ctab[area_sel].copy()

                # 제목은 plotly 밖(전체 너비)에 두어 좌·우 열 상단을 맞춤
                if metric_mode == "건수":
                    st.markdown(f"##### 카테고리별 현황 (건수) — {src}")
                else:
                    st.markdown(f"##### 권역별 카테고리 비중 (%) — Top {topn} — {src}")

                col_chart, col_tbl = st.columns([1, 1], gap="medium")

                if metric_mode == "건수":
                    with col_chart:
                        fig = go.Figure()
                        for area in area_sel:
                            fig.add_trace(
                                go.Bar(
                                    x=plot.index.tolist(),
                                    y=plot[area].values,
                                    name=area,
                                    marker_color=AREA_COLORS[area],
                                )
                            )
                        fig.update_layout(
                            barmode="group",
                            title=None,
                            plot_bgcolor="#fff",
                            paper_bgcolor="#F4F5F7",
                            height=STATUS_BLOCK_H,
                            margin=dict(l=40, r=20, t=24, b=60),
                            legend=dict(orientation="h", y=1.02, x=0.5, xanchor="center"),
                        )
                        fig.update_xaxes(tickangle=-25)
                        st.plotly_chart(fig, width="stretch")

                    with col_tbl:
                        if show_table:
                            t = ctab.reset_index().rename(columns={"cat_src": "category"})
                            t_disp = append_footer_sums(
                                t,
                                area_sel,
                                label="(표시 범위 권역 합계)",
                                count_as_integer=True,
                            )
                            st.dataframe(
                                t_disp,
                                width="stretch",
                                hide_index=True,
                                height=STATUS_BLOCK_H,
                            )
                            st.caption(
                                "하단 합계 행: 위에 표시된 카테고리(Top N)에 한해 권역별로 합산한 값입니다."
                            )
                        else:
                            st.empty()

                else:
                    # 비중: 권역별 도넛 (Top N 카테고리 기준)
                    share = (plot.div(plot.sum(axis=0), axis=1) * 100).fillna(0).round(2)
                    ncols = max(1, len(area_sel))
                    specs = [[{"type": "domain"}] * ncols]
                    fig_d = make_subplots(rows=1, cols=ncols, specs=specs, subplot_titles=area_sel)

                    all_cats_in_view = list(plot.index)
                    donut_cmap = make_color_map(all_cats_in_view + ["기타"])

                    for j, area in enumerate(area_sel):
                        labels = list(plot.index)
                        vals = share[area].values.tolist()
                        fig_d.add_trace(
                            go.Pie(
                                labels=labels,
                                values=vals,
                                hole=0.52,
                                marker=dict(colors=[donut_cmap.get(lb, "#9CA3AF") for lb in labels]),
                                textinfo="percent",
                                textposition="inside",
                                showlegend=(j == 0),
                                name=area,
                            ),
                            row=1,
                            col=j + 1,
                        )

                    fig_d.update_layout(
                        title_text=None,
                        paper_bgcolor="#F4F5F7",
                        height=STATUS_BLOCK_H,
                        margin=dict(l=20, r=20, t=48, b=20),
                    )
                    with col_chart:
                        st.plotly_chart(fig_d, width="stretch")

                    with col_tbl:
                        # 서브플롯 제목 줄만큼 표를 내려 도넛(링) 시작 높이에 맞춤
                        st.markdown(
                            "<div style='height:44px;min-height:44px'></div>",
                            unsafe_allow_html=True,
                        )
                        if show_table:
                            pct_tbl = share.copy()
                            pct_tbl.index.name = "category"
                            pr = pct_tbl.reset_index().rename(columns={"cat_src": "category"})
                            pct_disp = append_footer_sums(
                                pr,
                                area_sel,
                                label="(표시 Top N 비중 합계, %)",
                                include_total=False,
                                count_as_integer=False,
                            )
                            st.dataframe(
                                pct_disp,
                                width="stretch",
                                hide_index=True,
                                height=max(STATUS_BLOCK_H - 44, 320),
                            )
                            st.caption(
                                "하단 합계 행: 각 권역에서 표시된 카테고리 비중(%)의 합으로, Top N이 전체가 아니면 100% 미만일 수 있습니다."
                            )
                        else:
                            st.empty()

                if src == "네이버":
                    st.markdown(
                        "<div class='note-box'>현황 모드에서는 규모·분포를 빠르게 탐색할 수 있습니다.</div>",
                        unsafe_allow_html=True,
                    )

    else:
        if src != "네이버":
            st.info("분석 지표(B)는 현재 네이버 데이터 기준으로 제공됩니다. 상단 소스를 네이버로 바꿔주세요.")
        else:
            min_count = st.session_state.get("v4_min_count", 3)
            topk_lift = st.session_state.get("v4_topk_lift", 7)
            d = naver.copy()

            # (1) 체류인구 보정 밀도 + 월별 생활인구 추이
            st.markdown("#### 분석지표 1) 체류인구 보정 시설 밀도 · 월별 일일 평균 생활인구")
            rows = []
            for area in AREAS_STD:
                fac = int((d["area_std"] == area).sum())
                wknd, wkdy, peak = get_pop_metrics(lp, area)
                rows.append({
                    "권역": area,
                    "시설수": fac,
                    "주말_시간평균체류인구": round(wknd, 1),
                    "평일_시간평균체류인구": round(wkdy, 1),
                    "피크_시간대체류인구": round(peak, 1),
                    "시설/주말체류(1만명당)": round((fac / wknd * 10000) if wknd > 0 else 0, 2),
                    "시설/평일체류(1만명당)": round((fac / wkdy * 10000) if wkdy > 0 else 0, 2),
                    "시설/피크체류(1만명당)": round((fac / peak * 10000) if peak > 0 else 0, 2),
                })
            pop_df = pd.DataFrame(rows)

            tb1, ch1 = st.columns([3, 7], gap="medium")
            with tb1:
                st.markdown("##### 체류인구 보정 시설 밀도 (1만명당)")
                st.dataframe(
                    pop_df,
                    width="stretch",
                    hide_index=True,
                    height=B_ROW1_CHART_H,
                )
            with ch1:
                if monthly_pop.empty:
                    st.caption("월별 생활인구 추이를 계산할 데이터가 없습니다.")
                else:
                    st.markdown(
                        "##### 권역별 월별 일일 평균 생활인구 (2025-03 ~ 2026-02, 월별)"
                    )
                    line_df = monthly_pop[monthly_pop["area_std"].isin(AREAS_STD)].copy()
                    line_df["data_ym_label"] = line_df["data_ym_label"].astype(str)
                    month_order = sorted(line_df["data_ym_label"].dropna().unique())
                    fig_m = px.line(
                        line_df,
                        x="data_ym_label",
                        y="월평균_일별_체류인구",
                        color="area_std",
                        markers=True,
                        color_discrete_map=AREA_COLORS,
                        labels={
                            "data_ym_label": "월",
                            "월평균_일별_체류인구": "월별 일일 평균 생활인구",
                            "area_std": "권역",
                        },
                        title=None,
                    )
                    fig_m.update_layout(
                        paper_bgcolor="#F4F5F7",
                        plot_bgcolor="#fff",
                        height=B_ROW1_CHART_H,
                        margin=dict(l=50, r=30, t=28, b=50),
                        legend=dict(orientation="h", y=1.12, x=0.5, xanchor="center"),
                    )
                    # 숫자 ym만 x에 넣으면 Plotly가 ms 시계열로 오인식 → 문자열 월 + category 축
                    fig_m.update_xaxes(
                        type="category",
                        categoryorder="array",
                        categoryarray=month_order,
                        title="월",
                    )
                    st.plotly_chart(fig_m, width="stretch")

            # (2) 다양도 표 30% + 레이더
            st.markdown("#### 분석지표 2) 다양도/집중도 (HHI, Entropy) · 레이더")
            div_df = calc_diversity_by_area(d)
            tb2, rd2 = st.columns([3, 7], gap="medium")
            with tb2:
                st.markdown("##### 다양도·집중도 요약 표")
                st.dataframe(
                    div_df,
                    width="stretch",
                    hide_index=True,
                    height=B_ROW2_CHART_H,
                )
            with rd2:
                st.markdown("##### 다양도·집중도 (레이더)")
                st.plotly_chart(
                    diversity_radar_figure(div_df, height=B_ROW2_CHART_H),
                    width="stretch",
                )

            # (3) Lift: 권역별 도넛 + 표는 권역 선택
            st.markdown("#### 분석지표 3) 권역별 상대 특화 (Lift)")
            lift_df = calc_lift(d, min_count=min_count)
            if lift_df.empty:
                st.warning("Lift 계산 결과가 없습니다. 조건을 완화해 보세요.")
            else:
                lift_cat_labels = sorted(lift_df["category"].unique().tolist())
                lift_cmap = make_color_map(lift_cat_labels + ["기타"])

                donut_cols = st.columns(3)
                for idx, area in enumerate(AREAS_STD):
                    sub = lift_df[lift_df["권역"] == area].head(topk_lift).copy()
                    with donut_cols[idx]:
                        if sub.empty:
                            st.caption(f"{area}: 표본 부족")
                            continue
                        labels = sub["category"].tolist()
                        # 도넛: Top-K Lift 카테고리의 권역 내 점유(share_area) 비중 — 합이 100%가 되도록 정규화
                        w = sub["share_area"].astype(float).values
                        s = float(np.nansum(w))
                        if s <= 0:
                            w = np.ones(len(sub)) / max(len(sub), 1)
                        else:
                            w = w / s
                        fig_p = go.Figure(
                            data=[
                                go.Pie(
                                    labels=labels,
                                    values=w,
                                    hole=0.5,
                                    marker=dict(colors=[lift_cmap.get(l, "#9CA3AF") for l in labels]),
                                    textinfo="label+percent",
                                    textposition="outside",
                                    sort=False,
                                )
                            ]
                        )
                        fig_p.update_layout(
                            title=f"{area}<br><sub>Top {topk_lift} Lift — 점유 비중</sub>",
                            paper_bgcolor="#F4F5F7",
                            height=340,
                            margin=dict(l=10, r=10, t=50, b=10),
                            showlegend=False,
                        )
                        st.plotly_chart(fig_p, width="stretch")

                lift_area_pick = st.selectbox(
                    "표에서 볼 권역",
                    AREAS_STD,
                    key="v4_lift_table_area",
                )
                show_cols = ["권역", "category", "count", "share_area", "share_all", "lift"]
                sub_tbl = lift_df[lift_df["권역"] == lift_area_pick][show_cols]
                with st.expander("선택 권역 Lift 상세 표", expanded=False):
                    st.dataframe(sub_tbl, width="stretch", hide_index=True)

            st.markdown(
                "<div class='note-box'>B모드: 보고서 슬라이드 3~5에 해당하는 지표 탐색용입니다.</div>",
                unsafe_allow_html=True,
            )

else:
    st.markdown(
        f"<div style='font-size:1.5rem; font-weight:800; color:#1E1B4B;'>"
        f"{page_map[st.session_state.page]}</div>",
        unsafe_allow_html=True,
    )
    st.markdown("---")
    st.info("이 페이지는 다음 단계에서 순차적으로 확장할 예정입니다. (현재는 Page1 우선 개편)")
