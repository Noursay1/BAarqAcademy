# Log Analysis

## 1. Log inventory
- access.log: 726 lines; parsed JSON records: 725; malformed JSON: 1
- application.log: 730 lines; parsed JSON records: 729; malformed JSON: 1
- error.log: 68 lines

## 2. Time ranges
- access.log: 2026-08-20T11:00:00.015000+00:00 -> 2026-08-20T11:29:57.578000+00:00
- application.log: 2026-08-20T11:00:00.015000+00:00 -> 2026-08-20T11:29:57.578000+00:00

## 3. Access-log request statistics
- Access records: 725
- Distinct request IDs: 720
- Request IDs appearing more than once: 5
- Total duplicate access records beyond first occurrence: 5

## 4. HTTP status distribution
- 200: 620
- 404: 10
- 502: 40
- 503: 47
- 504: 8

## 5. Error rate
- HTTP responses parsed: 725
- HTTP 4xx/5xx responses: 105
- Raw response error rate: 14.483%
- Note: This is response-level error rate. Request-level analysis must account for retries/duplicate request IDs.

## 6. Most common paths
- /: 123
- /records: 119
- /instance: 119
- /health: 118
- /ready: 118
- /counter: 118
- /missing: 10

## 7. Upstream / instance distribution
- 172.23.0.11:8080: 365
- 172.23.0.12:8080: 341
- 172.23.0.12:8080, 172.23.0.11:8080: 19

## 8. Request latency
- Samples: 725
- Min: 3.00 ms
- Median: 54.00 ms
- P95: 2001.00 ms
- Max: 2025.00 ms
- Percentile method: linear interpolation over the sorted samples using the (N-1)*p rank.

## 9. Representative successful request
- request_id: lab-000002
- path: /health
- status: 200
- upstream/instance: 172.23.0.12:8080
- matching application records: 1

## 10. Representative failed request
- request_id: lab-000122
- path: /health
- status: 502
- upstream/instance: 172.23.0.12:8080
- matching application records: 0

## 11. NGINX error-log findings
- Error-log lines matching upstream/connectivity patterns: 67
- request_id=lab-000122 | 2026/08/20 11:05:02 [error] 31#31: *122 connect() failed (111: Connection refused) while connecting to upstream, request_id=lab-000122, request: "GET /health HTTP/1.1", upstream: "http://172.23.0.12:8080/health"
- request_id=lab-000124 | 2026/08/20 11:05:07 [error] 31#31: *124 connect() failed (111: Connection refused) while connecting to upstream, request_id=lab-000124, request: "GET /ready HTTP/1.1", upstream: "http://172.23.0.12:8080/ready"
- request_id=lab-000126 | 2026/08/20 11:05:12 [error] 31#31: *126 connect() failed (111: Connection refused) while connecting to upstream, request_id=lab-000126, request: "GET /records HTTP/1.1", upstream: "http://172.23.0.12:8080/records"
- request_id=lab-000128 | 2026/08/20 11:05:17 [error] 31#31: *128 connect() failed (111: Connection refused) while connecting to upstream, request_id=lab-000128, request: "GET /counter HTTP/1.1", upstream: "http://172.23.0.12:8080/counter"
- request_id=lab-000130 | 2026/08/20 11:05:22 [error] 31#31: *130 connect() failed (111: Connection refused) while connecting to upstream, request_id=lab-000130, request: "GET /instance HTTP/1.1", upstream: "http://172.23.0.12:8080/instance"
- request_id=lab-000132 | 2026/08/20 11:05:27 [error] 31#31: *132 connect() failed (111: Connection refused) while connecting to upstream, request_id=lab-000132, request: "GET / HTTP/1.1", upstream: "http://172.23.0.12:8080/"
- request_id=lab-000134 | 2026/08/20 11:05:32 [error] 31#31: *134 connect() failed (111: Connection refused) while connecting to upstream, request_id=lab-000134, request: "GET /health HTTP/1.1", upstream: "http://172.23.0.12:8080/health"
- request_id=lab-000136 | 2026/08/20 11:05:37 [error] 31#31: *136 connect() failed (111: Connection refused) while connecting to upstream, request_id=lab-000136, request: "GET /ready HTTP/1.1", upstream: "http://172.23.0.12:8080/ready"
- request_id=lab-000138 | 2026/08/20 11:05:42 [error] 31#31: *138 connect() failed (111: Connection refused) while connecting to upstream, request_id=lab-000138, request: "GET /records HTTP/1.1", upstream: "http://172.23.0.12:8080/records"
- request_id=lab-000140 | 2026/08/20 11:05:47 [error] 31#31: *140 connect() failed (111: Connection refused) while connecting to upstream, request_id=lab-000140, request: "GET /counter HTTP/1.1", upstream: "http://172.23.0.12:8080/counter"
- request_id=lab-000142 | 2026/08/20 11:05:52 [error] 31#31: *142 connect() failed (111: Connection refused) while connecting to upstream, request_id=lab-000142, request: "GET /instance HTTP/1.1", upstream: "http://172.23.0.12:8080/instance"
- request_id=lab-000144 | 2026/08/20 11:05:57 [error] 31#31: *144 connect() failed (111: Connection refused) while connecting to upstream, request_id=lab-000144, request: "GET / HTTP/1.1", upstream: "http://172.23.0.12:8080/"
- request_id=lab-000146 | 2026/08/20 11:06:02 [error] 31#31: *146 connect() failed (111: Connection refused) while connecting to upstream, request_id=lab-000146, request: "GET /health HTTP/1.1", upstream: "http://172.23.0.12:8080/health"
- request_id=lab-000148 | 2026/08/20 11:06:07 [error] 31#31: *148 connect() failed (111: Connection refused) while connecting to upstream, request_id=lab-000148, request: "GET /ready HTTP/1.1", upstream: "http://172.23.0.12:8080/ready"
- request_id=lab-000150 | 2026/08/20 11:06:12 [error] 31#31: *150 connect() failed (111: Connection refused) while connecting to upstream, request_id=lab-000150, request: "GET /records HTTP/1.1", upstream: "http://172.23.0.12:8080/records"
- request_id=lab-000152 | 2026/08/20 11:06:17 [error] 31#31: *152 connect() failed (111: Connection refused) while connecting to upstream, request_id=lab-000152, request: "GET /counter HTTP/1.1", upstream: "http://172.23.0.12:8080/counter"
- request_id=lab-000154 | 2026/08/20 11:06:22 [error] 31#31: *154 connect() failed (111: Connection refused) while connecting to upstream, request_id=lab-000154, request: "GET /instance HTTP/1.1", upstream: "http://172.23.0.12:8080/instance"
- request_id=lab-000156 | 2026/08/20 11:06:27 [error] 31#31: *156 connect() failed (111: Connection refused) while connecting to upstream, request_id=lab-000156, request: "GET / HTTP/1.1", upstream: "http://172.23.0.12:8080/"
- request_id=lab-000158 | 2026/08/20 11:06:32 [error] 31#31: *158 connect() failed (111: Connection refused) while connecting to upstream, request_id=lab-000158, request: "GET /health HTTP/1.1", upstream: "http://172.23.0.12:8080/health"
- request_id=lab-000160 | 2026/08/20 11:06:37 [error] 31#31: *160 connect() failed (111: Connection refused) while connecting to upstream, request_id=lab-000160, request: "GET /ready HTTP/1.1", upstream: "http://172.23.0.12:8080/ready"
- ... 47 additional matching lines omitted.

## 12. Correlation observations
- Error-log request IDs that also occur in access.log: 67
- Distinct access request IDs: 720
- Distinct access request IDs with multiple access records: 5
- Request IDs should be treated as the correlation key when present in all relevant logs.
- Repeated access records for one request ID can indicate retries or repeated logging; they must not automatically be counted as independent client requests.

## 13. Interpretation
- The access log is the source for client-visible HTTP outcomes and request timing.
- The application log is used to correlate application-side handling using request IDs.
- The NGINX error log is used to identify proxy/upstream connectivity problems.
- A connection-refused error at the proxy indicates an upstream connectivity/availability problem; it does not by itself prove the underlying root cause inside the application container.
- The logs cannot prove host-level compromise, packet loss outside the environment, or infrastructure conditions that were not logged.

## 14. Reproduction commands
```bash
wc -l logs/access.log logs/error.log logs/application.log
grep -Ei 'upstream|connect\(\)|connection refused' logs/error.log
grep -E '"request_id"|request_id' logs/access.log logs/application.log
python3 scripts/analyze_logs.py
```

## 15. Incident timeline

The supplied logs show a concentrated upstream connectivity failure beginning at approximately `2026-08-20 11:05:02Z`.

The first correlated failure is:

- `request_id=lab-000122`
- `GET /health`
- HTTP `502`
- upstream `172.23.0.12:8080`
- NGINX error: `connect() failed (111: Connection refused)`

Subsequent requests show the same connection-refused condition against the same upstream address at roughly five-second intervals while requests continue across different endpoints.

The failure pattern is visible at the proxy layer because NGINX could not establish the upstream TCP connection. The access log records the client-visible HTTP failure, while the NGINX error log records the upstream connection failure.

The application log has no matching application record for representative request `lab-000122`, which is consistent with the request failing before it reached the application process.

## 16. Retry and duplicate-request interpretation

The access log contains 725 parsed responses but 720 distinct request IDs.

Five request IDs occur more than once, producing five additional access records beyond the first occurrence of each duplicated ID.

Therefore:

- response-level counting uses 725 access records;
- request-level counting should use 720 distinct request IDs;
- duplicate request IDs must not automatically be interpreted as 5 additional client requests;
- a duplicate may represent retry behavior or repeated proxy-side logging.

The supplied logs alone do not prove the exact internal retry policy without examining the NGINX configuration and request sequence for each duplicate ID.

## 17. Failure classification

The strongest evidence for the concentrated failure period is an upstream availability/connectivity problem at NGINX:

`connect() failed (111: Connection refused) while connecting to upstream`

This means the TCP connection to the selected upstream endpoint was refused.

The logs do not, by themselves, prove whether the underlying cause was:

- an application process being down;
- a container restart;
- an incorrect/unavailable upstream endpoint;
- a network-level condition.

Those causes require runtime/container evidence in addition to the supplied historical logs.

## 18. Request-level error-rate caveat

The raw response error rate is:

`105 / 725 = 14.483%`

The denominator contains access-log responses, not unique client requests.

There are 720 distinct request IDs, so a request-level calculation should first determine the final outcome of each unique request ID and explicitly model retries.

The raw response rate is therefore retained as the directly reproducible access-log metric.

## 19. Evidence commands

The following commands reproduce the main findings:

```bash
wc -l logs/access.log logs/error.log logs/application.log

python3 scripts/analyze_logs.py

grep -Ei 'upstream|connect\(\)|connection refused' logs/error.log

grep -E '"request_id"|request_id' logs/access.log logs/application.log

grep -E '"status": *(4|5)[0-9][0-9]' logs/access.log
```

## 20. Limitations

The supplied historical logs are static application/proxy evidence.

They cannot independently establish:

- host compromise;
- infrastructure availability outside the logged environment;
- packet loss outside the Docker/network path;
- the exact reason the upstream process was unavailable;
- production-scale performance characteristics.

Runtime Docker inspection and the current validation/failure tests provide the complementary infrastructure evidence.
