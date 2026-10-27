# 강남으로 향하는 이동, 서울의 주거비

서울 25개 자치구를 단위로 2025년 강남 방향 생활이동 공개값과 아파트 매매·전월세 비용을 함께 살펴보는 정적 시각화 페이지입니다.

## 공개된 결과

- `dist/index.html`: 지도, 구별 상세 패널, 산점도, 순위 그래프, 수도권 출발지 비교 및 자료 설명
- `dist/data/seoul-gangnam-data.js`: 서울 25개 구의 단순화 경계와 구 단위 집계 통계만 포함
- `scripts/build_static_dataset.py`: SGIS 경계 ZIP과 집계 CSV를 페이지용 정적 데이터로 바꾸는 재현 스크립트

원본 거래내역, 개인 단위 이동자료, API 키, 전체 SGIS 경계 파일은 이 사이트 패키지에 포함하지 않습니다. 페이지는 별도 API 요청 없이 사전 집계 파일만 읽습니다.

## 연구 질문 및 지표

**질문:** 2025년 서울 25개 구의 강남 방향 생활이동 흐름과 아파트 주거비는 어떻게 다르고, 두 지표 사이에는 어떤 관계가 나타나는가?

1. 오전 강남 도착 비중 = 구별 공개값 합계 ÷ 서울 구내 공개값 총합 × 100
2. 저녁 강남 출발 비중 = 구별 공개값 합계 ÷ 서울 구내 공개값 총합 × 100
3. 매매가격, 전세 보증금, 월세 보증금·임대료 = 2025년 아파트 거래별 금액/㎡의 자치구별 중위값

공간 단위는 서울 자치구 25개입니다. 강남 방향 이동은 오전 07–09시 HW, 저녁 17–20시 WH 유형을 사용합니다. 지도의 SGIS 시군구 경계는 2025-06-30 기준이며 경계자료의 시군구명으로 집계표와 결합했습니다. 생활이동의 2021 코드표는 자치구 이름으로 다시 묶었습니다.

## 해석 주의

- 이동자료에는 날짜가 아니라 월·요일별 집계가 있어 공휴일을 날짜 단위로 제외하지 못했습니다.
- 숫자형 공개값 합계는 고유 인원이나 실제 연간 통행량이 아닙니다. 비식별 `*` 값은 합계에서 빠집니다.
- HW·WH는 주간 활동지와 야간 상주지 사이의 이동 유형이며, 업무 목적만 확인된 통근량은 아닙니다.
- 강남구 값에는 강남구 내부 이동이 포함됩니다. 상관계수는 강남구 포함·제외 결과를 함께 표시합니다.
- 상관관계는 인과를 뜻하지 않으며, 인구·대중교통·업무시설 등의 요인을 통제하지 않았습니다.

## 데이터 출처

- [서울 생활이동 데이터](https://data.seoul.go.kr/dataVisual/seoul/seoulLivingMigration.do)
- [서울 부동산 실거래가 정보](https://data.seoul.go.kr/dataList/OA-21275/A/1/datasetView.do)
- [서울 부동산 전월세가 정보](https://data.seoul.go.kr/dataList/OA-21276/S/1/datasetView.do)
- [국가데이터처 SGIS 행정구역 경계](https://www.data.go.kr/data/15129688/fileData.do)

## 정적 데이터 다시 만들기

개인 환경에 내려받은 SGIS ZIP과 과제 폴더의 구 단위 집계 CSV를 사용해 빌드합니다. 경계 ZIP은 저장소에 올리지 않습니다.

```powershell
python scripts/build_static_dataset.py `
  --boundary-zip "<local SGIS boundary ZIP>" `
  --comparison-csv "<2025 gu comparison CSV>" `
  --sales-gu-csv "<2025 sales by gu CSV>" `
  --province-csv "<2025 province mobility CSV>" `
  --output dist/data/seoul-gangnam-data.js
```
