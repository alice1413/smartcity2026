#!/usr/bin/env python3
"""Join pooled 2025 morning HW flow-time estimates to Seoul gu housing summaries."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


SEOUL_GUS = {
    "종로구", "중구", "용산구", "성동구", "광진구", "동대문구", "중랑구", "성북구",
    "강북구", "도봉구", "노원구", "은평구", "서대문구", "마포구", "양천구",
    "강서구", "구로구", "금천구", "영등포구", "동작구", "관악구", "서초구",
    "강남구", "송파구", "강동구",
}


def number(value: str | None) -> float | None:
    try:
        text = (value or "").strip().replace(",", "")
        return float(text) if text else None
    except ValueError:
        return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--flows-csv", required=True, type=Path)
    parser.add_argument("--mobility-crosswalk-csv", required=True, type=Path)
    parser.add_argument("--housing-gu-csv", required=True, type=Path)
    parser.add_argument("--output-csv", required=True, type=Path)
    parser.add_argument("--summary-json", required=True, type=Path)
    args = parser.parse_args()

    code_to_gu: dict[str, str] = {}
    with args.mobility_crosswalk_csv.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            code = row["생활이동_행정동코드_7자리"].strip()
            parts = row["코드표_전체주소"].split()
            if len(code) == 7 and code.isdigit() and len(parts) >= 3 and parts[0] == "서울특별시":
                gu = parts[1]
                if gu in SEOUL_GUS:
                    code_to_gu[code] = gu

    stats: dict[str, dict] = defaultdict(lambda: {
        "flow": 0.0,
        "weighted_minutes": 0.0,
        "time_weight": 0.0,
        "numeric_flow_rows": 0,
        "suppressed_rows": 0,
        "unusable_duration_rows": 0,
        "origin_dongs": set(),
    })
    missing_seoul_codes: set[str] = set()
    non_seoul_codes: set[str] = set()
    non_seoul_rows = 0
    rows_seen = 0
    with args.flows_csv.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            if row.get("분석흐름") != "오전_강남도착" or row.get("이동유형") != "HW":
                continue
            rows_seen += 1
            origin = row.get("출발_행정동_코드", "").strip()
            gu = code_to_gu.get(origin)
            if not gu:
                (missing_seoul_codes if origin.startswith("11") else non_seoul_codes).add(origin)
                non_seoul_rows += 1
                continue
            cell = stats[gu]
            cell["origin_dongs"].add(origin)
            flow = number(row.get("이동인구_보고값_합"))
            cell["suppressed_rows"] += int(number(row.get("이동인구_비식별행수")) or 0)
            cell["unusable_duration_rows"] += int(number(row.get("이동시간_사용불가행수")) or 0)
            if flow is None or flow <= 0:
                continue
            cell["flow"] += flow
            cell["numeric_flow_rows"] += int(number(row.get("이동인구_숫자행수")) or 0)
            minutes = number(row.get("평균이동시간_인구가중_분"))
            if minutes is not None and minutes >= 0:
                cell["weighted_minutes"] += minutes * flow
                cell["time_weight"] += flow

    housing = {}
    with args.housing_gu_csv.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            housing[row["자치구명"].strip()] = row

    rows = []
    for gu in sorted(SEOUL_GUS):
        cell = stats[gu]
        h = housing.get(gu, {})
        rows.append({
            "자치구명": gu,
            "강남도착_공개값합": round(cell["flow"], 2),
            "평균이동시간_분": round(cell["weighted_minutes"] / cell["time_weight"], 2) if cell["time_weight"] else "",
            "시간산출_가중공개값": round(cell["time_weight"], 2),
            "시간산출_공개값포괄률_pct": round(100 * cell["time_weight"] / cell["flow"], 2) if cell["flow"] else "",
            "출발_행정동수": len(cell["origin_dongs"]),
            "이동값_숫자행수": cell["numeric_flow_rows"],
            "이동값_비식별행수": cell["suppressed_rows"],
            "이동시간_사용불가행수": cell["unusable_duration_rows"],
            "매매_거래건수": h.get("매매_거래건수", ""),
            "매매_중위만원_m2": h.get("매매_중위만원_m2", ""),
            "전세_거래건수": h.get("전세_거래건수", ""),
            "전세_중위보증금만원_m2": h.get("전세_중위보증금만원_m2", ""),
            "월세_거래건수": h.get("월세_거래건수", ""),
            "월세_중위임대료만원_m2": h.get("월세_중위임대료만원_m2", ""),
        })

    columns = list(rows[0])
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.output_csv.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)

    report = {
        "year": 2025,
        "flow_filter": "오전 07–09시, 월–금 요일 범주, HW, 도착 행정동이 강남구인 월별 공개 집계",
        "flow_rows_scanned": rows_seen,
        "seoul_gu_count": len(rows),
        "seoul_gu_with_numeric_flow": sum(bool(s["flow"]) for s in stats.values()),
        "unmapped_seoul_codes": len(missing_seoul_codes),
        "non_seoul_codes_excluded": len(non_seoul_codes),
        "notes": [
            "평균 이동시간은 출발 구별 숫자형 공개값을 가중치로 사용.",
            "합계는 월·요일·시간 구간별 공개값의 합이며, 고유 인원이나 실제 연간 통행량이 아님.",
            "월·요일 자료에는 날짜가 없어 공휴일을 개별 제외하지 못함.",
            "강남구 내부 흐름은 목적지와 출발지가 같은 값으로 후보지 비교에서 분리.",
            "주거비는 거래 법정동을 행정동에 배분하지 않고 기존 자치구 단위 거래 통계와 결합.",
        ],
    }
    args.summary_json.parent.mkdir(parents=True, exist_ok=True)
    args.summary_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "seoul_gus": len(rows),
        "with_numeric_flow": report["seoul_gu_with_numeric_flow"],
        "unmapped_seoul_codes": len(missing_seoul_codes),
        "non_seoul_codes_excluded": len(non_seoul_codes),
        "non_seoul_rows_skipped": non_seoul_rows,
        "top_flow": sorted(rows, key=lambda x: float(x["강남도착_공개값합"]), reverse=True)[:5],
        "shortest_minutes": sorted((x for x in rows if x["평균이동시간_분"] != ""), key=lambda x: float(x["평균이동시간_분"]))[:5],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

