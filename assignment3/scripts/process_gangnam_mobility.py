#!/usr/bin/env python3
"""Stream and aggregate 2025 Seoul living-mobility ZIPs for Gangnam flows.

No source ZIP is extracted. Only selected hourly CSV members are read.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import re
import sys
import zipfile
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


REQUIRED_COLUMNS = {
    "대상연월",
    "요일",
    "도착시간",
    "출발 행정동 코드",
    "도착 행정동 코드",
    "이동유형",
    "평균 이동 시간(분)",
    "이동인구(합)",
}
MORNING_HOURS = {"07", "08", "09"}
EVENING_HOURS = {"17", "18", "19", "20"}
WEEKDAYS = {"월", "화", "수", "목", "금"}
ZIP_PATTERN = re.compile(r"생활이동_행정동_2025(0[1-9]|1[0-2])\.zip$")
HOUR_PATTERN = re.compile(r"_(\d{2})시\.csv$", re.IGNORECASE)

OUTPUT_COLUMNS = [
    "분석흐름",
    "대상연월",
    "요일",
    "도착시간",
    "출발_행정동_코드",
    "도착_행정동_코드",
    "이동유형",
    "이동인구_보고값_합",
    "평균이동시간_인구가중_분",
    "이동인구_숫자행수",
    "이동인구_비식별행수",
    "이동인구_기타오류행수",
    "이동시간_사용불가행수",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="2025 월간 행정동 생활이동 ZIP에서 강남구 연계 흐름을 집계합니다."
    )
    parser.add_argument(
        "--input-dir",
        required=True,
        type=Path,
        help="2025년 월별 ZIP 파일이 있는 폴더",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="결과 폴더 (기본값: 입력 폴더 아래 outputs)",
    )
    parser.add_argument(
        "--gangnam-prefix",
        default="11230",
        help="행정동 코드에서 강남구를 구분하는 접두 코드 (기본값: 11230)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="ZIP을 풀거나 행을 읽지 않고 처리 대상 파일만 확인",
    )
    return parser.parse_args()


def find_archives(input_dir: Path) -> list[tuple[Path, str]]:
    if not input_dir.exists() or not input_dir.is_dir():
        raise FileNotFoundError(f"입력 폴더를 찾을 수 없습니다: {input_dir}")

    found: list[tuple[Path, str]] = []
    for path in sorted(input_dir.rglob("생활이동_행정동_2025*.zip")):
        match = ZIP_PATTERN.search(path.name)
        if match:
            found.append((path, f"2025{match.group(1)}"))
    if not found:
        raise FileNotFoundError(
            "생활이동_행정동_2025MM.zip 형식의 ZIP 파일을 찾지 못했습니다."
        )
    found_months = [month for _, month in found]
    duplicates = sorted({month for month in found_months if found_months.count(month) > 1})
    if duplicates:
        raise ValueError("같은 월 ZIP이 여러 개 있습니다: " + ", ".join(duplicates))
    return found


def selected_members(
    archive: zipfile.ZipFile,
) -> tuple[list[tuple[zipfile.ZipInfo, str]], list[str]]:
    selected: list[tuple[zipfile.ZipInfo, str]] = []
    missing: list[str] = []
    present_hours: set[str] = set()

    for info in archive.infolist():
        if info.is_dir():
            continue
        match = HOUR_PATTERN.search(Path(info.filename).name)
        if not match:
            continue
        hour = match.group(1)
        present_hours.add(hour)
        if hour in MORNING_HOURS | EVENING_HOURS:
            selected.append((info, hour))

    for hour in sorted(MORNING_HOURS | EVENING_HOURS):
        if hour not in present_hours:
            missing.append(hour)
    return sorted(selected, key=lambda item: item[1]), missing


def normalize_weekday(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    return value[0]


def text_cell(row: dict[str, Any], column: str) -> str:
    value = row.get(column)
    return value.strip() if isinstance(value, str) else ""


def parse_number(value: str) -> float | None:
    value = value.strip().replace(",", "")
    if not value or value == "*":
        return None
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"유한한 숫자가 아닙니다: {value}")
    return number


def direction_for(
    movement_type: str,
    hour: str,
    origin: str,
    destination: str,
    gangnam_prefix: str,
) -> str | None:
    if movement_type == "HW" and hour in MORNING_HOURS:
        return "오전_강남도착" if destination.startswith(gangnam_prefix) else None
    if movement_type == "WH" and hour in EVENING_HOURS:
        return "저녁_강남출발" if origin.startswith(gangnam_prefix) else None
    return None


def write_csv(
    path: Path,
    rows: list[dict[str, Any]],
    columns: list[str],
    *,
    mode: str = "w",
    write_header: bool = True,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoding = "utf-8-sig" if mode == "w" else "utf-8"
    with path.open(mode, encoding=encoding, newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=columns, extrasaction="ignore")
        if write_header:
            writer.writeheader()
        writer.writerows(rows)


def run() -> int:
    args = parse_args()
    input_dir = args.input_dir.expanduser().resolve()
    output_dir = (args.output_dir or input_dir / "outputs").expanduser().resolve()
    gangnam_prefix = args.gangnam_prefix.strip()
    if not gangnam_prefix.isdigit() or len(gangnam_prefix) < 5:
        raise ValueError("강남구 접두 코드는 숫자 5자리 이상이어야 합니다.")

    archives = find_archives(input_dir)
    month_names = [month for _, month in archives]
    missing_months = sorted(set(f"2025{month:02d}" for month in range(1, 13)) - set(month_names))

    print(f"입력 ZIP: {len(archives)}개")
    for archive_path, month in archives:
        print(f"  {month}: {archive_path.name} ({archive_path.stat().st_size / 1024**2:.1f} MB)")
    if missing_months:
        print("경고: 자료가 없는 월: " + ", ".join(missing_months))

    if args.dry_run:
        print("\n미리보기: 아래 시간대 파일만 읽을 예정입니다. 원본 ZIP은 압축 해제하지 않습니다.")
        for archive_path, month in archives:
            with zipfile.ZipFile(archive_path) as archive:
                members, missing_hours = selected_members(archive)
                print(f"\n{month}: 선택 {len(members)}개")
                for info, hour in members:
                    print(f"  {hour}시 | {info.filename} | {info.file_size / 1024**2:.1f} MB")
                if missing_hours:
                    print("  경고: 빠진 시간대 " + ", ".join(missing_hours))
        return 0

    run_stats: dict[str, Any] = {
        "archives_found": len(archives),
        "months_found": month_names,
        "months_missing": missing_months,
        "selected_members": 0,
        "missing_hour_members": [],
        "rows_read_from_selected_members": 0,
        "rows_matching_analysis_flows": 0,
        "weekend_rows_skipped": 0,
        "unknown_weekday_rows_skipped": 0,
        "suppressed_volume_rows": 0,
        "invalid_volume_rows": 0,
        "unavailable_duration_rows": 0,
        "output_groups": 0,
        "gangnam_code_prefix": gangnam_prefix,
        "notes": [
            "Source rows are aggregated by month and weekday and have no calendar date; exact public-holiday exclusion is not possible.",
            "HW/WH are nighttime-residence/daytime-activity movement proxies, not confirmed work-only trips.",
            "Asterisk-suppressed movement values are excluded from numeric sums, so reported totals may be understated.",
        ],
    }
    required_hours = MORNING_HOURS | EVENING_HOURS
    output_dir.mkdir(parents=True, exist_ok=True)
    flow_path = output_dir / "gangnam_mobility_flows_2025.csv"
    partial_flow_path = output_dir / "gangnam_mobility_flows_2025.partial.csv"
    write_csv(partial_flow_path, [], OUTPUT_COLUMNS)

    for archive_path, archive_month in archives:
        print(f"\n처리 중: {archive_path.name}")
        aggregates: dict[
            tuple[str, str, str, str, str, str, str], dict[str, Any]
        ] = defaultdict(
            lambda: {
                "movement_population": 0.0,
                "volume_rows": 0,
                "suppressed_volume_rows": 0,
                "invalid_volume_rows": 0,
                "weighted_minutes_sum": 0.0,
                "weighted_minutes_population": 0.0,
                "unavailable_duration_rows": 0,
            }
        )
        with zipfile.ZipFile(archive_path) as archive:
            members, missing_hours = selected_members(archive)
            run_stats["selected_members"] += len(members)
            for hour in missing_hours:
                run_stats["missing_hour_members"].append(
                    {"archive": archive_path.name, "hour": hour}
                )
            if missing_hours:
                print("  경고: 빠진 시간대 " + ", ".join(missing_hours))

            for info, member_hour in members:
                print(f"  읽는 중: {member_hour}시 ({info.file_size / 1024**2:.1f} MB)")
                with archive.open(info, "r") as raw_member:
                    text_member = io.TextIOWrapper(raw_member, encoding="cp949", newline="")
                    reader = csv.DictReader(text_member)
                    if reader.fieldnames is None:
                        raise ValueError(f"CSV 헤더를 읽지 못했습니다: {archive_path.name}/{info.filename}")
                    reader.fieldnames = [name.strip() for name in reader.fieldnames]
                    absent_columns = sorted(REQUIRED_COLUMNS - set(reader.fieldnames))
                    if absent_columns:
                        raise ValueError(
                            f"필수 열이 없습니다 ({archive_path.name}/{info.filename}): "
                            + ", ".join(absent_columns)
                        )

                    for row in reader:
                        run_stats["rows_read_from_selected_members"] += 1
                        month = text_cell(row, "대상연월") or archive_month
                        weekday = normalize_weekday(text_cell(row, "요일"))
                        hour = text_cell(row, "도착시간").zfill(2)
                        origin = text_cell(row, "출발 행정동 코드")
                        destination = text_cell(row, "도착 행정동 코드")
                        movement_type = text_cell(row, "이동유형").upper()

                        if month != archive_month:
                            raise ValueError(
                                f"ZIP 월과 행의 대상연월이 다릅니다: {archive_path.name}, {month}"
                            )
                        if hour != member_hour or hour not in required_hours:
                            continue
                        if weekday not in WEEKDAYS:
                            if weekday in {"토", "일"}:
                                run_stats["weekend_rows_skipped"] += 1
                            else:
                                run_stats["unknown_weekday_rows_skipped"] += 1
                            continue

                        direction = direction_for(
                            movement_type, hour, origin, destination, gangnam_prefix
                        )
                        if direction is None:
                            continue
                        run_stats["rows_matching_analysis_flows"] += 1
                        key = (direction, month, weekday, hour, origin, destination, movement_type)
                        group = aggregates[key]

                        raw_volume = text_cell(row, "이동인구(합)")
                        try:
                            volume = parse_number(raw_volume)
                        except ValueError:
                            volume = None
                            group["invalid_volume_rows"] += 1
                            run_stats["invalid_volume_rows"] += 1
                            continue

                        if volume is None:
                            if raw_volume == "*":
                                group["suppressed_volume_rows"] += 1
                                run_stats["suppressed_volume_rows"] += 1
                            else:
                                group["invalid_volume_rows"] += 1
                                run_stats["invalid_volume_rows"] += 1
                            continue
                        if volume < 0:
                            group["invalid_volume_rows"] += 1
                            run_stats["invalid_volume_rows"] += 1
                            continue

                        group["movement_population"] += volume
                        group["volume_rows"] += 1
                        raw_duration = text_cell(row, "평균 이동 시간(분)")
                        try:
                            duration = parse_number(raw_duration)
                        except ValueError:
                            duration = None
                        if duration is None or duration < 0:
                            group["unavailable_duration_rows"] += 1
                            run_stats["unavailable_duration_rows"] += 1
                        else:
                            group["weighted_minutes_sum"] += duration * volume
                            group["weighted_minutes_population"] += volume

        output_rows: list[dict[str, Any]] = []
        for key, group in sorted(aggregates.items()):
            direction, month, weekday, hour, origin, destination, movement_type = key
            weight = group["weighted_minutes_population"]
            mean_duration = group["weighted_minutes_sum"] / weight if weight > 0 else ""
            volume_output: float | str = (
                round(group["movement_population"], 4)
                if group["volume_rows"] > 0
                else ""
            )
            output_rows.append(
                {
                    "분석흐름": direction,
                    "대상연월": month,
                    "요일": weekday,
                    "도착시간": hour,
                    "출발_행정동_코드": origin,
                    "도착_행정동_코드": destination,
                    "이동유형": movement_type,
                    "이동인구_보고값_합": volume_output,
                    "평균이동시간_인구가중_분": round(mean_duration, 2)
                    if mean_duration != ""
                    else "",
                    "이동인구_숫자행수": group["volume_rows"],
                    "이동인구_비식별행수": group["suppressed_volume_rows"],
                    "이동인구_기타오류행수": group["invalid_volume_rows"],
                    "이동시간_사용불가행수": group["unavailable_duration_rows"],
                }
            )

        write_csv(
            partial_flow_path,
            output_rows,
            OUTPUT_COLUMNS,
            mode="a",
            write_header=False,
        )
        run_stats["output_groups"] += len(output_rows)
        print(f"  월 집계 그룹: {len(output_rows):,}개 (월 단위로 결과 저장)")
        del output_rows, aggregates

    run_stats["completed_at_local"] = datetime.now().astimezone().isoformat(timespec="seconds")
    summary_path = output_dir / "gangnam_mobility_run_summary.json"
    partial_summary_path = output_dir / "gangnam_mobility_run_summary.partial.json"
    partial_summary_path.write_text(
        json.dumps(run_stats, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    partial_summary_path.replace(summary_path)
    partial_flow_path.replace(flow_path)

    print(f"\n완료: 집계 그룹 {run_stats['output_groups']:,}개")
    print(f"흐름 집계: {flow_path}")
    print(f"실행 요약: {summary_path}")
    print(
        "주의: 이 자료에는 날짜 열이 없어 평일 공휴일을 개별 제외하지 않았습니다. "
        "결과를 공휴일 제외 평일 수치로 해석하지 마세요."
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(run())
    except (OSError, UnicodeError, zipfile.BadZipFile, csv.Error, ValueError) as error:
        print(f"오류: {error}", file=sys.stderr)
        raise SystemExit(1)

