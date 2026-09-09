#!/usr/bin/env python3

import json
import re
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "logs"


def parse_dt(value: str):
    value = value.strip()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def percentile(values, p):
    if not values:
        return None
    values = sorted(values)
    if len(values) == 1:
        return values[0]
    rank = (len(values) - 1) * p
    lo = int(rank)
    hi = min(lo + 1, len(values) - 1)
    frac = rank - lo
    return values[lo] + (values[hi] - values[lo]) * frac


def read_lines(path):
    with path.open("r", encoding="utf-8") as f:
        return [line.rstrip("\n") for line in f]


def analyze_json_log(path):
    lines = read_lines(path)
    rows = []
    malformed = []

    for n, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            malformed.append((n, line))

    return lines, rows, malformed


def iso_min_max(rows):
    timestamps = []
    for row in rows:
        for key in ("timestamp", "@timestamp", "time", "datetime"):
            value = row.get(key)
            if isinstance(value, str):
                try:
                    timestamps.append(parse_dt(value))
                    break
                except Exception:
                    pass

    if not timestamps:
        return None, None

    return min(timestamps), max(timestamps)


def get_request_id(row):
    for key in ("request_id", "requestId", "request-id"):
        if key in row:
            return str(row[key])
    return None


def get_status(row):
    for key in ("status", "status_code", "statusCode", "http_status"):
        if key in row:
            try:
                return int(row[key])
            except Exception:
                return str(row[key])
    return None


def get_path(row):
    for key in ("path", "uri", "request_uri", "request"):
        value = row.get(key)
        if isinstance(value, str):
            return value
    return None


def get_upstream(row):
    for key in ("upstream", "upstream_addr", "backend", "instance", "instance_id"):
        value = row.get(key)
        if value:
            return str(value)
    return None


def get_request_time_ms(row):
    for key in ("request_time_ms", "duration_ms", "latency_ms"):
        value = row.get(key)
        if value is not None:
            try:
                return float(value)
            except Exception:
                pass

    for key in ("request_time", "duration", "latency"):
        value = row.get(key)
        if value is not None:
            try:
                return float(value) * 1000.0
            except Exception:
                pass

    return None


def main():
    access_path = LOG_DIR / "access.log"
    app_path = LOG_DIR / "application.log"
    error_path = LOG_DIR / "error.log"

    access_lines, access_rows, access_bad = analyze_json_log(access_path)
    app_lines, app_rows, app_bad = analyze_json_log(app_path)
    error_lines = read_lines(error_path)

    print("# Log Analysis\n")

    print("## 1. Log inventory")
    print(f"- access.log: {len(access_lines)} lines; parsed JSON records: {len(access_rows)}; malformed JSON: {len(access_bad)}")
    print(f"- application.log: {len(app_lines)} lines; parsed JSON records: {len(app_rows)}; malformed JSON: {len(app_bad)}")
    print(f"- error.log: {len(error_lines)} lines")
    print()

    print("## 2. Time ranges")
    for name, rows in [("access.log", access_rows), ("application.log", app_rows)]:
        start, end = iso_min_max(rows)
        print(f"- {name}: {start.isoformat() if start else 'N/A'} -> {end.isoformat() if end else 'N/A'}")
    print()

    request_ids = [get_request_id(r) for r in access_rows if get_request_id(r)]
    rid_counts = Counter(request_ids)

    unique_ids = set(request_ids)
    duplicated_ids = {rid: count for rid, count in rid_counts.items() if count > 1}

    print("## 3. Access-log request statistics")
    print(f"- Access records: {len(access_rows)}")
    print(f"- Distinct request IDs: {len(unique_ids)}")
    print(f"- Request IDs appearing more than once: {len(duplicated_ids)}")
    if duplicated_ids:
        print(f"- Total duplicate access records beyond first occurrence: {sum(c - 1 for c in duplicated_ids.values())}")
    print()

    statuses = Counter()
    paths = Counter()
    upstreams = Counter()
    request_times = []

    for row in access_rows:
        status = get_status(row)
        if status is not None:
            statuses[str(status)] += 1

        path = get_path(row)
        if path:
            paths[path] += 1

        upstream = get_upstream(row)
        if upstream:
            upstreams[upstream] += 1

        rt = get_request_time_ms(row)
        if rt is not None:
            request_times.append(rt)

    print("## 4. HTTP status distribution")
    for status, count in sorted(statuses.items()):
        print(f"- {status}: {count}")
    print()

    total_status = sum(statuses.values())
    errors_4xx_5xx = sum(count for status, count in statuses.items() if status.isdigit() and int(status) >= 400)
    print("## 5. Error rate")
    print(f"- HTTP responses parsed: {total_status}")
    print(f"- HTTP 4xx/5xx responses: {errors_4xx_5xx}")
    if total_status:
        print(f"- Raw response error rate: {(errors_4xx_5xx / total_status) * 100:.3f}%")
    print("- Note: This is response-level error rate. Request-level analysis must account for retries/duplicate request IDs.")
    print()

    print("## 6. Most common paths")
    for path, count in paths.most_common(15):
        print(f"- {path}: {count}")
    print()

    print("## 7. Upstream / instance distribution")
    for upstream, count in upstreams.most_common():
        print(f"- {upstream}: {count}")
    print()

    print("## 8. Request latency")
    if request_times:
        print(f"- Samples: {len(request_times)}")
        print(f"- Min: {min(request_times):.2f} ms")
        print(f"- Median: {statistics.median(request_times):.2f} ms")
        print(f"- P95: {percentile(request_times, 0.95):.2f} ms")
        print(f"- Max: {max(request_times):.2f} ms")
        print("- Percentile method: linear interpolation over the sorted samples using the (N-1)*p rank.")
    else:
        print("- No request timing field was detected.")
    print()

    app_rids = defaultdict(list)
    for row in app_rows:
        rid = get_request_id(row)
        if rid:
            app_rids[rid].append(row)

    failed_access = []
    success_access = []

    for row in access_rows:
        rid = get_request_id(row)
        status = get_status(row)
        if status is None:
            continue

        if isinstance(status, int) and status >= 500:
            failed_access.append(row)
        elif status == 200:
            success_access.append(row)

    print("## 9. Representative successful request")
    if success_access:
        row = success_access[0]
        rid = get_request_id(row)
        print(f"- request_id: {rid}")
        print(f"- path: {get_path(row)}")
        print(f"- status: {get_status(row)}")
        print(f"- upstream/instance: {get_upstream(row)}")
        print(f"- matching application records: {len(app_rids.get(rid, []))}")
    else:
        print("- No HTTP 200 sample found.")
    print()

    print("## 10. Representative failed request")
    if failed_access:
        row = failed_access[0]
        rid = get_request_id(row)
        print(f"- request_id: {rid}")
        print(f"- path: {get_path(row)}")
        print(f"- status: {get_status(row)}")
        print(f"- upstream/instance: {get_upstream(row)}")
        print(f"- matching application records: {len(app_rids.get(rid, []))}")
    else:
        print("- No HTTP 5xx sample found in access.log.")
    print()

    refused = []
    request_id_pattern = re.compile(r"\b(?:request_id|request-id)[=:]\s*([A-Za-z0-9._-]+)", re.I)

    for line in error_lines:
        if re.search(r"connect\(\)|connection refused|upstream", line, re.I):
            match = request_id_pattern.search(line)
            refused.append((match.group(1) if match else None, line))

    print("## 11. NGINX error-log findings")
    print(f"- Error-log lines matching upstream/connectivity patterns: {len(refused)}")
    for rid, line in refused[:20]:
        print(f"- request_id={rid or 'N/A'} | {line}")
    if len(refused) > 20:
        print(f"- ... {len(refused) - 20} additional matching lines omitted.")
    print()

    print("## 12. Correlation observations")
    correlation_hits = 0
    for rid, _ in refused:
        if rid and rid in unique_ids:
            correlation_hits += 1

    print(f"- Error-log request IDs that also occur in access.log: {correlation_hits}")
    print(f"- Distinct access request IDs: {len(unique_ids)}")
    print(f"- Distinct access request IDs with multiple access records: {len(duplicated_ids)}")
    print("- Request IDs should be treated as the correlation key when present in all relevant logs.")
    print("- Repeated access records for one request ID can indicate retries or repeated logging; they must not automatically be counted as independent client requests.")
    print()

    print("## 13. Interpretation")
    print("- The access log is the source for client-visible HTTP outcomes and request timing.")
    print("- The application log is used to correlate application-side handling using request IDs.")
    print("- The NGINX error log is used to identify proxy/upstream connectivity problems.")
    print("- A connection-refused error at the proxy indicates an upstream connectivity/availability problem; it does not by itself prove the underlying root cause inside the application container.")
    print("- The logs cannot prove host-level compromise, packet loss outside the environment, or infrastructure conditions that were not logged.")
    print()

    print("## 14. Reproduction commands")
    print("```bash")
    print("wc -l logs/access.log logs/error.log logs/application.log")
    print("grep -Ei 'upstream|connect\\(\\)|connection refused' logs/error.log")
    print("grep -E '\"request_id\"|request_id' logs/access.log logs/application.log")
    print("python3 scripts/analyze_logs.py")
    print("```")


if __name__ == "__main__":
    main()
