# 강남까지 걸리는 시간, 서울의 주거비

2025년 서울 25개 자치구의 강남 도착 생활이동 평균시간과 아파트 주거비를 비교하는 정적 시각화입니다. 강남구를 일자리 중심지로 가정하고, 구별로 공개된 집계 이동 흐름을 주거비와 나란히 읽습니다.

## 연구 질문

**2025년 서울 각 자치구에서 강남구로 향하는 야간 상주지→주간 활동지(HW) 흐름의 평균 이동시간과 아파트 주거비는 어떻게 다르며, 두 조건을 함께 볼 때 상대적으로 부담이 낮은 거주 후보지는 어디인가?**

분석 결과는 개인의 실제 주거 선택을 보여주지 않습니다. 상대적으로 낮은 구별 주거비와 짧은 구별 이동시간이 함께 나타나는 지역을 탐색하는 비교입니다.

## 지표

### 강남 도착 흐름 및 이동시간

- 출발·도착 행정동 단위 2025 생활이동 자료에서 평일 요일 범주(월–금), 오전 07–09시, `HW` 유형 중 도착지가 강남구인 흐름을 선택합니다.
- 이동유형 `HW`는 야간 상주지에서 주간 활동지로 이동한 추정 흐름으로, 출근·등교 대리 지표입니다.
- 출발 자치구별 평균 이동시간은 행별 평균시간을 숫자형 이동 공개값으로 가중해 계산합니다.

`Σ(행별 평균 이동시간 × 숫자형 공개 이동값) ÷ Σ(시간이 있는 숫자형 공개 이동값)`

- 지도 선 굵기는 출발 구별 숫자형 공개 이동값 합계를 나타냅니다. 이동시간은 선·구역 설명과 상세 패널에서 확인합니다.
- 강남구 내부 이동은 외부 거주 후보지 비교에서 분리합니다.

### 주거비

- 2025년 계약일 기준 아파트 거래에서 취소 매매를 제외하고 거래별 금액을 면적으로 나눈 값의 자치구별 중위값을 계산합니다.
- 매매가, 전세 보증금, 월세 임대료는 별도 지표로 표시하며 임의 전월세 전환율은 적용하지 않습니다.
- 법정동 거래를 행정동에 임의 배분하지 않고, 공통 공간 단위인 자치구로 맞춥니다.

산점도는 가로축에 선택한 주거비, 세로축에 평균 이동시간, 점 크기에 공개 이동값 합계를 둡니다. 두 축 모두 24개 후보 구의 중앙값 이하인 지역을 표시하되 임의의 복합 점수나 최적 거주지를 만들지 않습니다.

## 공개 파일

- `dist/index.html`: 지도·흐름선, 상세 패널, 산점도, 순위 그래프, 방법 및 한계
- `dist/data/seoul-gangnam-data.js`: 25개 구의 단순화 경계와 구별 집계지표
- `data/gangnam_commute_housing_by_gu_2025.csv`: 공개 가능한 구별 집계 결과
- `data/mobility_to_mois_admin_crosswalk_2025.csv`: 이동 행정동 코드의 자치구명 연결표
- `scripts/dashboard.js`: 페이지의 지도·그래프 표시
- `scripts/summarize_gangnam_commute_by_gu.py`: 행정동 OD 집계를 구별 통근 요약과 주거비에 연결
- `scripts/build_static_dataset.py`: SGIS 구 경계와 집계표를 정적 페이지 데이터로 변환
- `scripts/process_gangnam_mobility.py`: 원본 월별 ZIP을 압축 해제하지 않고 선택 시간대의 행정동 OD 집계 생성

원본 ZIP, 거래별 행, API 키, 개인 단위 이동기록은 공개 패키지에 포함하지 않습니다. 웹페이지 방문 중 API를 호출하지 않습니다.

## 재현 방법

Python 3에서 과제 폴더와 공개용 코드 폴더 경로를 맞춰 실행합니다. 원본 12개월 ZIP은 로컬에 둡니다.

```powershell
python .\scripts\process_gangnam_mobility.py `
  --input-dir "<월별 생활이동 ZIP 폴더>" `
  --output-dir "<과제3 출력 폴더>\outputs"

python .\scripts\summarize_gangnam_commute_by_gu.py `
  --flows-csv "<과제3 출력 폴더>\outputs\gangnam_mobility_flows_2025.csv" `
  --mobility-crosswalk-csv .\data\mobility_to_mois_admin_crosswalk_2025.csv `
  --housing-gu-csv "<과제3 출력 폴더>\outputs\seoul_gu_housing_gangnam_mobility_2025_api_updated.csv" `
  --output-csv "<과제3 출력 폴더>\outputs\gangnam_commute_housing_by_gu_2025.csv" `
  --summary-json "<과제3 출력 폴더>\outputs\gangnam_commute_summary_2025.json"
```

정적 경계 번들은 SGIS 경계 ZIP, 이동·주거비 집계표와 거래자료에서 만든 자치구 코드표로 갱신합니다.

```powershell
python .\scripts\build_static_dataset.py `
  --boundary-zip "<SGIS 경계 ZIP>" `
  --comparison-csv "<과제3 출력 폴더>\outputs\seoul_gu_housing_gangnam_mobility_2025_api_updated.csv" `
  --sales-gu-csv "<과제3 출력 폴더>\outputs\sales_apartment_gu_2025_api.csv" `
  --commute-gu-csv "<과제3 출력 폴더>\outputs\gangnam_commute_housing_by_gu_2025.csv" `
  --output .\dist\data\seoul-gangnam-data.js
```

## 자료 출처

- [서울 열린데이터광장 · 서울 생활이동 데이터](https://data.seoul.go.kr/dataVisual/seoul/seoulLivingMigration.do)
- [서울 열린데이터광장 · 서울시 부동산 실거래가 정보](https://data.seoul.go.kr/dataList/OA-21275/A/1/datasetView.do)
- [서울 열린데이터광장 · 서울시 부동산 전월세가 정보](https://data.seoul.go.kr/dataList/OA-21276/S/1/datasetView.do)
- [국가데이터처 SGIS · 행정구역 경계](https://www.data.go.kr/data/15129688/fileData.do)

## 해석상 한계

- 자료는 월·요일 단위로 제공되어 특정 날짜가 없습니다. 평일 공휴일을 개별 제외하지 못했습니다.
- 숫자형 공개 이동값은 고유 인원 수나 실제 연간 통행량이 아닙니다. 비식별 `*` 값은 합계에서 제외됩니다.
- 이동시간은 출발 구 단위 평균이며, 개인의 문전 간 통근시간이나 대기·환승시간이 아닙니다.
- HW에는 출근 이외의 등교 등 주간 활동지 이동이 포함될 수 있습니다.
- 주거비는 자치구별 아파트 거래 중위값으로 개인의 소득·주거유형·실제 지불액을 나타내지 않습니다.
- 분석 범위는 서울 25개 구이며 경기·인천 주거비는 포함하지 않았습니다.
- 관측된 구별 시간과 비용의 동반 패턴은 실제 노동자의 선택이나 인과관계를 입증하지 않습니다.

