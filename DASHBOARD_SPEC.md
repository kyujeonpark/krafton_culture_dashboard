# DASHBOARD SPEC (2-Page)

본 문서는 `dashboard_culture_two_pages.py`의 목적, 지표, UI 원칙을 정리한 실행 스펙이다.

## 1) 목적

- 3권역(성수, 이태원한남, 홍대)의 문화 인프라/수요/소비 패턴을 한 화면 흐름으로 비교한다.
- 네이버(체감 문화)와 매출(산업 분류 문화)의 불일치를 “오류”가 아니라 “발견 포인트”로 다룬다.
- 지도는 탐색 허브, 차트는 해석 보조 역할로 배치한다.

## 2) 데이터 소스

- 네이버 시설: `1_processed/naver_culture/culture_data_clean.csv`
- 생활인구: `1_processed/localppl/LOCAL_PEOPLE_DONG_three_zones_merged_202503_202602.csv`
- 공공시설(10개동 필터): `1_processed/public_culture/서울시_공공문화시설_10개동.csv`
- 매출 시계열: `1_processed/sales/sales_timeseries.csv`
- 소비자 유입: `1_processed/sales/consumer_region.csv`
- 매장 좌표: `1_processed/sales/stores_master.csv` (`lat`, `lon` 포함)

## 3) 페이지 구성

## Page 1: 한눈에 보기

- 상단: 3권역 KPI 카드
  - 시설 수(네이버)
  - 문화시설공급밀도
  - 월평균매출액
- 중단: 레이더 차트 (권역 상대지수 0~100)
- 하단 탭:
  - 시설 지도 (Folium 레이어 토글: 네이버/공공/매출)
  - 생활인구 (일별 평균, 시간대별 평균)
  - 매출 (월별 매출액/건수, 카테고리별 매출액)
  - 리뷰(상위 10%) 지도 + 상위 시설 리스트

## Page 2: 집중 탐구

- 좌측: 권역별 `total_review` 분포 박스플롯 (롱테일/슈퍼스타 구조)
- 우측: 리뷰 상위 시설 vs 주변 매출 매장 밀도(반경 기반 불일치 탐색)
  - 파라미터: 상위 비율(%), 반경(m)
  - 출력: 상세 테이블 + 히스토그램
- 하단: 해석 주의 문구(미포착 대형시설/데이터 누락 가능성)

## 4) 핵심 지표 정의

- 문화시설공급밀도: `네이버 시설 수 / (권역 피크일 생활인구) * 10,000`
- 일평균생활인구: 권역 내 `총생활인구수`의 일평균
- 월평균매출액: `sales_man` 합 / 월수
- 거래활력도: `sales_cnt` 합 / (월수 * 매장수)
- 외국인소비비율: `외국인 visit_cnt / 전체 visit_cnt * 100`
- 재방문비율: `sum(revfreq_2) / sum(revfreq_1 + revfreq_2) * 100`

## 5) UI/UX 원칙

- 지도: Folium + `cartodbpositron` (라이트 톤)
- 색상 체계: 모노톤 + 포인트 컬러 1개
  - Accent: `#4F46E5`
  - Gray dark: `#374151`
  - Gray light: `#9CA3AF`
- 상호작용: “지도 클릭 이벤트 연동” 대신 “드롭다운/멀티셀렉트”로 안정성 확보

## 6) 해석 가이드

- 네이버 리뷰는 활력의 절대 지표가 아니라 “인지/노출/상업성 혼합 신호”로 사용한다.
- 리뷰 상위인데 주변 매출 매장 밀도가 낮은 경우:
  - 비상업/무료/행사성 문화공간 가능성
  - 매출 데이터 미포착 시설 가능성
- 매출 데이터는 미제공 업체 누락이 존재할 수 있으므로 중규모 시설군 관점으로 보조 해석한다.

## 7) 실행

```powershell
streamlit run dashboard_culture_two_pages.py
```

