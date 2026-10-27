#!/usr/bin/env python3
"""Build the small, static data bundle used by the Seoul research page.

This reads the official SGIS 2025 Q2 nationwide district shapefile ZIP plus
the already aggregated project CSVs. It writes only Seoul's 25 district
polygons and aggregate indicators; it never exports transaction-level rows.
"""

import argparse
import csv
import io
import json
import math
import struct
import zipfile
from pathlib import Path

SIMPLIFY_TOLERANCE_M = 45.0


def read_csv(path):
    with Path(path).open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def as_float(value):
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def decode_text(raw, encoding):
    try:
        return raw.decode(encoding).strip()
    except (UnicodeDecodeError, LookupError):
        return raw.decode("cp949", errors="replace").strip()


def dbf_rows(dbf_bytes, encoding):
    record_count = struct.unpack_from("<I", dbf_bytes, 4)[0]
    header_length = struct.unpack_from("<H", dbf_bytes, 8)[0]
    record_length = struct.unpack_from("<H", dbf_bytes, 10)[0]
    fields = []
    offset = 32
    while dbf_bytes[offset] != 0x0D:
        descriptor = dbf_bytes[offset:offset + 32]
        name = descriptor[:11].split(b"\0", 1)[0].decode("ascii")
        length = descriptor[16]
        fields.append((name, length))
        offset += 32

    result = []
    for index in range(record_count):
        start = header_length + index * record_length
        record = dbf_bytes[start:start + record_length]
        if not record or record[:1] == b"*":
            result.append(None)
            continue
        values = {}
        cursor = 1
        for name, length in fields:
            values[name] = decode_text(record[cursor:cursor + length], encoding)
            cursor += length
        result.append(values)
    return result


def point_segment_distance_sq(point, start, end):
    dx, dy = end[0] - start[0], end[1] - start[1]
    if dx == 0 and dy == 0:
        return (point[0] - start[0]) ** 2 + (point[1] - start[1]) ** 2
    t = max(0.0, min(1.0, ((point[0] - start[0]) * dx + (point[1] - start[1]) * dy) / (dx * dx + dy * dy)))
    x, y = start[0] + t * dx, start[1] + t * dy
    return (point[0] - x) ** 2 + (point[1] - y) ** 2


def simplify_ring(points, tolerance):
    if len(points) <= 4:
        return points
    closed = points[0] == points[-1]
    body = points[:-1] if closed else points
    if len(body) <= 3:
        return points
    keep = {0, len(body) - 1}
    stack = [(0, len(body) - 1)]
    tolerance_sq = tolerance * tolerance
    while stack:
        first, last = stack.pop()
        farthest_index, farthest_distance = -1, tolerance_sq
        for index in range(first + 1, last):
            distance = point_segment_distance_sq(body[index], body[first], body[last])
            if distance > farthest_distance:
                farthest_index, farthest_distance = index, distance
        if farthest_index >= 0:
            keep.add(farthest_index)
            stack.append((first, farthest_index))
            stack.append((farthest_index, last))
    simplified = [body[index] for index in sorted(keep)]
    if len(simplified) < 4:
        simplified = body[:]
    if closed:
        simplified.append(simplified[0])
    return simplified


def read_shape_record(content):
    shape_type = struct.unpack_from("<i", content, 0)[0]
    if shape_type == 0:
        return []
    if shape_type not in (5, 15, 25):
        raise ValueError(f"Unsupported district shape type: {shape_type}")
    part_count, point_count = struct.unpack_from("<ii", content, 36)
    parts_offset = 44
    parts = struct.unpack_from(f"<{part_count}i", content, parts_offset) if part_count else ()
    points_offset = parts_offset + part_count * 4
    points = [struct.unpack_from("<dd", content, points_offset + i * 16) for i in range(point_count)]
    rings = []
    for index, start in enumerate(parts):
        end = parts[index + 1] if index + 1 < len(parts) else point_count
        ring = [(round(x, 1), round(y, 1)) for x, y in points[start:end]]
        if len(ring) >= 4:
            if ring[0] != ring[-1]:
                ring.append(ring[0])
            ring = simplify_ring(ring, SIMPLIFY_TOLERANCE_M)
            if len(ring) >= 4:
                rings.append(ring)
    return rings


def read_sgis_seoul_features(boundary_zip, metrics_by_name):
    with zipfile.ZipFile(boundary_zip) as archive:
        shp_name = next(name for name in archive.namelist() if name.endswith("bnd_sigungu_00_2025_2Q.shp"))
        dbf_name = shp_name[:-4] + ".dbf"
        cpg_name = shp_name[:-4] + ".cpg"
        encoding = archive.read(cpg_name).decode("ascii", errors="ignore").strip() or "UTF-8"
        attributes = dbf_rows(archive.read(dbf_name), encoding)
        features = []
        with archive.open(shp_name) as stream:
            header = stream.read(100)
            if len(header) != 100:
                raise ValueError("The SGIS shapefile header is incomplete.")
            index = 0
            while True:
                record_header = stream.read(8)
                if not record_header:
                    break
                if len(record_header) != 8:
                    raise ValueError("The SGIS shapefile record header is incomplete.")
                _, content_words = struct.unpack(">ii", record_header)
                content = stream.read(content_words * 2)
                if len(content) != content_words * 2:
                    raise ValueError("The SGIS shapefile record is incomplete.")
                attribute = attributes[index] if index < len(attributes) else None
                index += 1
                if not attribute:
                    continue
                code = attribute.get("SIGUNGU_CD", "").strip()
                if not code.startswith("11"):
                    continue
                name = attribute.get("SIGUNGU_NM", "").strip()
                metrics = metrics_by_name.get(name)
                if not metrics:
                    continue
                rings = read_shape_record(content)
                if rings:
                    features.append({"name": name, "code": metrics["code"], "rings": rings, "metrics": metrics["metrics"]})
        return features


def pearson(x_values, y_values):
    n = len(x_values)
    if n < 2:
        return None
    x_mean, y_mean = sum(x_values) / n, sum(y_values) / n
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values))
    x_var = sum((x - x_mean) ** 2 for x in x_values)
    y_var = sum((y - y_mean) ** 2 for y in y_values)
    if not x_var or not y_var:
        return None
    return round(numerator / math.sqrt(x_var * y_var), 3)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--boundary-zip", required=True, type=Path)
    parser.add_argument("--comparison-csv", required=True, type=Path)
    parser.add_argument("--sales-gu-csv", required=True, type=Path)
    parser.add_argument("--province-csv", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    comparison = read_csv(args.comparison_csv)
    sales_gu = read_csv(args.sales_gu_csv)
    sales_codes = {row["자치구명"]: row["자치구코드"].zfill(5) for row in sales_gu}
    metrics_by_name = {}
    for row in comparison:
        name = row["자치구명"]
        code = sales_codes.get(name)
        if not code:
            raise ValueError(f"No 5-digit legal district code found for {name}.")
        metrics_by_name[name] = {
            "code": code,
            "metrics": {
                "morningFlow": as_float(row["오전_강남도착_이동인구_공개값합"]),
                "morningShare": as_float(row["오전_서울구내비중_pct"]),
                "eveningFlow": as_float(row["저녁_강남출발_이동인구_공개값합"]),
                "eveningShare": as_float(row["저녁_서울구내비중_pct"]),
                "saleCount": int(float(row["매매_거래건수"])),
                "saleMedian": as_float(row["매매_중위만원_m2"]),
                "jeonseCount": int(float(row["전세_거래건수"])),
                "jeonseMedian": as_float(row["전세_중위보증금만원_m2"]),
                "monthlyCount": int(float(row["월세_거래건수"])),
                "monthlyDepositMedian": as_float(row["월세_중위보증금만원_m2"]),
                "monthlyRentMedian": as_float(row["월세_중위임대료만원_m2"]),
            },
        }

    features = read_sgis_seoul_features(args.boundary_zip, metrics_by_name)
    if len(features) != 25:
        names = sorted(feature["name"] for feature in features)
        raise ValueError(f"Expected 25 Seoul districts, found {len(features)}: {names}")
    features.sort(key=lambda feature: feature["code"])

    all_points = [point for feature in features for ring in feature["rings"] for point in ring]
    bounds = {
        "minX": min(point[0] for point in all_points),
        "minY": min(point[1] for point in all_points),
        "maxX": max(point[0] for point in all_points),
        "maxY": max(point[1] for point in all_points),
    }
    provinces = []
    for row in read_csv(args.province_csv):
        provinces.append({
            "name": row["시도명_코드표기"],
            "morningFlow": as_float(row["오전_강남도착_이동인구_공개값합"]),
            "eveningFlow": as_float(row["저녁_강남출발_이동인구_공개값합"]),
        })
    morning_total = sum(row["morningFlow"] or 0 for row in provinces)
    evening_total = sum(row["eveningFlow"] or 0 for row in provinces)
    for row in provinces:
        row["morningShareOfKnownValues"] = round(100 * row["morningFlow"] / morning_total, 2) if morning_total else None
        row["eveningShareOfKnownValues"] = round(100 * row["eveningFlow"] / evening_total, 2) if evening_total else None

    payload = {
        "meta": {
            "year": 2025,
            "districtCount": len(features),
            "boundarySource": "국가데이터처 SGIS 행정구역 경계, 2025-06-30 기준",
            "boundaryCrs": "EPSG:5179",
            "flowMethod": "숫자형 공개값을 월·요일·시간대별로 합산. 개인별 고유 통근자 수 또는 실제 연간 통행량이 아님.",
            "housingMethod": "2025 계약일 기준 아파트 거래의 거래 단위 ㎡당 중위값. 매매는 취소 거래 제외.",
            "mobilityCodeNote": "생활이동 코드표(2021)를 자치구명으로 집계해 2025 경계와 구 단위로 결합.",
            "suppressionNote": "이동인구가 '*'로 비식별 처리된 행은 공개값 합계에서 제외되어 총량이 실제보다 작을 수 있음.",
            "purposeNote": "HW/WH는 야간 상주지와 주간 활동지 사이의 이동 유형이며 업무 목적만을 확인한 통근량은 아님.",
        },
        "bounds": bounds,
        "features": features,
        "provinces": provinces,
        "correlation": {
            "saleVsMorningSharePearson": pearson(
                [feature["metrics"]["saleMedian"] for feature in features],
                [feature["metrics"]["morningShare"] for feature in features],
            )
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "window.SEOUL_GANGNAM_DATA=" + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )
    ring_count = sum(len(feature["rings"]) for feature in features)
    vertex_count = sum(len(ring) for feature in features for ring in feature["rings"])
    print(json.dumps({"districts": len(features), "rings": ring_count, "vertices_after_simplification": vertex_count,
                      "site_data_bytes": args.output.stat().st_size, "correlation": payload["correlation"]}, ensure_ascii=True))


if __name__ == "__main__":
    main()
