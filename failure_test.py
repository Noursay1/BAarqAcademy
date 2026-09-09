#!/usr/bin/env python3
"""Stop one backend (app-01), prove continued availability through app-02,
restore app-01, and prove both instances serve again.

Bounded waits, PASS/FAIL summary, non-zero exit on failure, and the target
container is always restarted (even on error/interrupt) so the environment
is never left in a torn-down state.
"""

import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8080")
COMPOSE_PROJECT = os.getenv("COMPOSE_PROJECT", "barq-assessment")
TARGET_CONTAINER = os.getenv("FAILURE_TARGET", "app-01")
SURVIVOR_CONTAINER = "app-02" if TARGET_CONTAINER == "app-01" else "app-01"

BASELINE_REQUESTS = 10
DURING_FAILURE_REQUESTS = 20
AFTER_RECOVERY_REQUESTS = 10
RECOVERY_TIMEOUT = 60
REQUEST_TIMEOUT = 4
REQUEST_INTERVAL = 0.2

EVIDENCE_PATH = os.getenv("EVIDENCE_PATH", "evidence/failure_test.txt")


class FailureTestError(Exception):
    pass


def run_command(command, timeout=15, check=True):
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        raise FailureTestError(f"command failed: {' '.join(command)}: {exc}") from exc

    if check and result.returncode != 0:
        raise FailureTestError(
            f"command failed ({result.returncode}): {' '.join(command)}\n"
            f"{result.stderr.strip()}"
        )

    return result


def http_request(path, timeout=REQUEST_TIMEOUT):
    url = f"{BASE_URL}{path}"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
            return response.status, body
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return exc.code, body
    except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        return None, str(exc)


def instance_of(body):
    try:
        data = json.loads(body)
    except (json.JSONDecodeError, TypeError):
        return None
    return data.get("instance_id") or data.get("instance") or data.get("id")


def sample_instance(path="/instance", count=10, interval=REQUEST_INTERVAL):
    """Hit the given endpoint `count` times and return (successes, errors,
    instances_seen) without ever raising -- callers decide pass/fail."""
    successes = 0
    errors = 0
    instances_seen = set()

    for _ in range(count):
        status, body = http_request(path)
        if status == 200:
            successes += 1
            instance = instance_of(body)
            if instance:
                instances_seen.add(str(instance))
        else:
            errors += 1
        time.sleep(interval)

    return successes, errors, instances_seen


def container_state(container):
    result = run_command(
        ["docker", "inspect", container, "--format", "{{.State.Status}}"],
        check=False,
    )
    if result.returncode != 0:
        return "missing"
    return result.stdout.strip()


def stop_container(container):
    run_command(["docker", "compose", "-p", COMPOSE_PROJECT, "stop", container])


def start_container(container):
    run_command(["docker", "compose", "-p", COMPOSE_PROJECT, "start", container])


def wait_for_healthy(container, timeout=RECOVERY_TIMEOUT):
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = run_command(
            ["docker", "inspect", container, "--format", "{{.State.Health.Status}}"],
            check=False,
        )
        status = result.stdout.strip() if result.returncode == 0 else ""
        if status == "healthy":
            return
        if status == "":
            # No health check defined -- fall back to running state.
            if container_state(container) == "running":
                return
        time.sleep(2)

    raise FailureTestError(
        f"{container} did not become healthy within {timeout}s"
    )


def write_evidence(lines):
    os.makedirs(os.path.dirname(EVIDENCE_PATH) or ".", exist_ok=True)
    with open(EVIDENCE_PATH, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main():
    evidence = []
    evidence.append(f"BARQ failure/recovery test: target={TARGET_CONTAINER}")
    evidence.append(f"started_at={time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}")

    failures = 0

    try:
        # 1. Baseline: confirm both instances currently answer.
        print(f"Baseline: sampling /instance x{BASELINE_REQUESTS}")
        b_success, b_errors, b_instances = sample_instance(count=BASELINE_REQUESTS)
        evidence.append(
            f"baseline: success={b_success} errors={b_errors} "
            f"instances_seen={sorted(b_instances)}"
        )
        if b_errors > 0 or {"app-01", "app-02"} - b_instances:
            failures += 1
            print(
                f"FAIL baseline: errors={b_errors}, "
                f"instances_seen={sorted(b_instances)} (expected both instances, zero errors)",
                file=sys.stderr,
            )
        else:
            print(f"PASS baseline: {b_success} requests, both instances observed")

        # 2. Stop the target backend.
        print(f"Stopping {TARGET_CONTAINER}...")
        stop_container(TARGET_CONTAINER)
        state = container_state(TARGET_CONTAINER)
        evidence.append(f"stopped_state={state}")
        if state not in ("exited", "missing"):
            failures += 1
            print(f"FAIL {TARGET_CONTAINER} did not stop (state={state})", file=sys.stderr)
        else:
            print(f"PASS {TARGET_CONTAINER} stopped (state={state})")

        # 3. Traffic during failure: service must continue via the survivor,
        #    and any errors must be attributable to the stopped instance's
        #    in-flight/retry window, not total unavailability.
        print(f"During failure: sampling /instance x{DURING_FAILURE_REQUESTS}")
        d_success, d_errors, d_instances = sample_instance(count=DURING_FAILURE_REQUESTS)
        evidence.append(
            f"during_failure: success={d_success} errors={d_errors} "
            f"instances_seen={sorted(d_instances)}"
        )
        if d_success == 0:
            failures += 1
            print("FAIL during-failure: no successful responses through NGINX", file=sys.stderr)
        elif SURVIVOR_CONTAINER not in d_instances:
            failures += 1
            print(
                f"FAIL during-failure: {SURVIVOR_CONTAINER} did not serve any requests",
                file=sys.stderr,
            )
        elif TARGET_CONTAINER in d_instances:
            failures += 1
            print(
                f"FAIL during-failure: stopped container {TARGET_CONTAINER} "
                f"still reported as serving traffic",
                file=sys.stderr,
            )
        else:
            print(
                f"PASS during-failure: {d_success} succeeded via {SURVIVOR_CONTAINER}, "
                f"{d_errors} errors observed while {TARGET_CONTAINER} was down"
            )

        # 4. Restore the backend.
        print(f"Restoring {TARGET_CONTAINER}...")
        start_container(TARGET_CONTAINER)
        wait_for_healthy(TARGET_CONTAINER)
        evidence.append(f"restored_state={container_state(TARGET_CONTAINER)}")
        print(f"PASS {TARGET_CONTAINER} healthy again")

        # 5. Traffic after recovery: both instances must serve again.
        print(f"After recovery: sampling /instance x{AFTER_RECOVERY_REQUESTS}")
        a_success, a_errors, a_instances = sample_instance(count=AFTER_RECOVERY_REQUESTS)
        evidence.append(
            f"after_recovery: success={a_success} errors={a_errors} "
            f"instances_seen={sorted(a_instances)}"
        )
        if a_errors > 0 or {"app-01", "app-02"} - a_instances:
            failures += 1
            print(
                f"FAIL after-recovery: errors={a_errors}, "
                f"instances_seen={sorted(a_instances)} (expected both instances, zero errors)",
                file=sys.stderr,
            )
        else:
            print(f"PASS after-recovery: {a_success} requests, both instances observed")

    except FailureTestError as exc:
        failures += 1
        evidence.append(f"error={exc}")
        print(f"FAIL {exc}", file=sys.stderr)

    finally:
        # Safe cleanup: always make sure the target container is running,
        # regardless of what happened above.
        if container_state(TARGET_CONTAINER) != "running":
            print(f"Cleanup: ensuring {TARGET_CONTAINER} is started")
            try:
                start_container(TARGET_CONTAINER)
                wait_for_healthy(TARGET_CONTAINER, timeout=RECOVERY_TIMEOUT)
            except FailureTestError as exc:
                print(f"Cleanup FAILED to restore {TARGET_CONTAINER}: {exc}", file=sys.stderr)

        evidence.append(f"finished_at={time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}")
        evidence.append(f"failures={failures}")
        write_evidence(evidence)
        print(f"Evidence written to {EVIDENCE_PATH}")

    print()
    if failures:
        print(f"FAILURE TEST: FAIL ({failures} check(s) failed)")
        return 1

    print("FAILURE TEST: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
