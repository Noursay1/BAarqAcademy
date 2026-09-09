#!/usr/bin/env python3

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections import Counter


BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8080")
APP_CONTAINER = os.getenv("APP_CONTAINER", "app-01")

BASELINE_REQUESTS = int(os.getenv("BASELINE_REQUESTS", "20"))
FAILURE_REQUESTS = int(os.getenv("FAILURE_REQUESTS", "30"))
RECOVERY_REQUESTS = int(os.getenv("RECOVERY_REQUESTS", "20"))

REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "3"))
HEALTH_TIMEOUT = int(os.getenv("HEALTH_TIMEOUT", "60"))
HEALTH_INTERVAL = int(os.getenv("HEALTH_INTERVAL", "2"))


class FailureTestError(Exception):
    pass


def run(command, timeout=15, check=True):
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise FailureTestError(
            f"command timed out: {' '.join(command)}"
        ) from exc
    except OSError as exc:
        raise FailureTestError(
            f"command execution failed: {' '.join(command)}: {exc}"
        ) from exc

    if check and result.returncode != 0:
        raise FailureTestError(
            f"command failed ({result.returncode}): {' '.join(command)}\n"
            f"{result.stderr.strip()}"
        )

    return result


def request(path="/instance"):
    url = f"{BASE_URL}{path}"

    req = urllib.request.Request(
        url,
        method="GET",
    )

    started = time.monotonic()

    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as response:
            body = response.read().decode("utf-8", errors="replace")
            elapsed_ms = (time.monotonic() - started) * 1000

            return {
                "status": response.status,
                "body": body,
                "elapsed_ms": elapsed_ms,
                "error": None,
            }

    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        elapsed_ms = (time.monotonic() - started) * 1000

        return {
            "status": exc.code,
            "body": body,
            "elapsed_ms": elapsed_ms,
            "error": f"HTTP {exc.code}",
        }

    except Exception as exc:
        elapsed_ms = (time.monotonic() - started) * 1000

        return {
            "status": None,
            "body": "",
            "elapsed_ms": elapsed_ms,
            "error": str(exc),
        }


def parse_instance(body):
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return None

    if not isinstance(data, dict):
        return None

    return (
        data.get("instance_id")
        or data.get("instance")
        or data.get("id")
    )


def traffic(label, count):
    results = []
    instances = Counter()
    status_codes = Counter()
    errors = 0
    successes = 0
    total_ms = 0.0

    print(f"\n===== {label} ({count} requests) =====")

    for _ in range(count):
        result = request("/instance")
        results.append(result)

        status = result["status"]

        if status is not None:
            status_codes[str(status)] += 1

        total_ms += result["elapsed_ms"]

        if status == 200:
            successes += 1

            instance = parse_instance(result["body"])
            if instance:
                instances[instance] += 1

        else:
            errors += 1

    avg_ms = total_ms / count if count else 0.0

    print(f"requests={count}")
    print(f"successes={successes}")
    print(f"errors={errors}")
    print(f"average_latency_ms={avg_ms:.2f}")
    print(f"status_codes={dict(status_codes)}")
    print(f"instances={dict(instances)}")

    return {
        "results": results,
        "requests": count,
        "successes": successes,
        "errors": errors,
        "instances": instances,
        "status_codes": status_codes,
        "average_latency_ms": avg_ms,
    }


def container_running(container):
    result = run(
        [
            "docker",
            "inspect",
            container,
            "--format",
            "{{.State.Status}}",
        ]
    )

    return result.stdout.strip() == "running"


def container_healthy(container):
    result = run(
        [
            "docker",
            "inspect",
            container,
            "--format",
            "{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}",
        ]
    )

    return result.stdout.strip() == "healthy"


def wait_for_http_health(timeout=HEALTH_TIMEOUT):
    deadline = time.time() + timeout

    while time.time() < deadline:
        result = request("/health")

        if result["status"] == 200:
            return True

        time.sleep(HEALTH_INTERVAL)

    return False


def wait_for_container_health(container, timeout=HEALTH_TIMEOUT):
    deadline = time.time() + timeout

    while time.time() < deadline:
        try:
            if container_healthy(container):
                return True
        except FailureTestError:
            pass

        time.sleep(HEALTH_INTERVAL)

    return False


def stop_backend(container):
    print(f"\nStopping backend: {container}")
    run(["docker", "stop", container], timeout=20)

    if container_running(container):
        raise FailureTestError(
            f"{container} is still running after docker stop"
        )

    print(f"PASS {container} stopped")


def restore_backend(container):
    print(f"\nRestoring backend: {container}")
    run(["docker", "start", container], timeout=20)

    print(f"Waiting for {container} health...")

    if not wait_for_container_health(container):
        raise FailureTestError(
            f"{container} did not become healthy within "
            f"{HEALTH_TIMEOUT}s"
        )

    print(f"PASS {container} is healthy again")

    if not wait_for_http_health():
        raise FailureTestError(
            "NGINX /health did not recover after backend restoration"
        )

    print("PASS NGINX health recovered")


def main():
    failure = False
    backend_was_stopped = False

    print("BARQ backend failure/recovery test")
    print(f"BASE_URL={BASE_URL}")
    print(f"APP_CONTAINER={APP_CONTAINER}")

    try:
        # ---------------------------------------------------------
        # 1. Baseline
        # ---------------------------------------------------------
        if not container_running(APP_CONTAINER):
            raise FailureTestError(
                f"{APP_CONTAINER} is not running before test"
            )

        if not wait_for_http_health():
            raise FailureTestError(
                "NGINX /health is not available before failure test"
            )

        baseline = traffic(
            "BASELINE",
            BASELINE_REQUESTS,
        )

        if baseline["successes"] != BASELINE_REQUESTS:
            raise FailureTestError(
                "baseline traffic is not fully successful"
            )

        if APP_CONTAINER not in baseline["instances"]:
            raise FailureTestError(
                f"baseline did not observe {APP_CONTAINER}"
            )

        if "app-02" not in baseline["instances"]:
            raise FailureTestError(
                "baseline did not observe app-02"
            )

        print("PASS baseline traffic")

        # ---------------------------------------------------------
        # 2. Stop one backend
        # ---------------------------------------------------------
        stop_backend(APP_CONTAINER)
        backend_was_stopped = True

        # Give NGINX a moment to detect the failed upstream.
        time.sleep(2)

        # ---------------------------------------------------------
        # 3. Traffic during failure
        # ---------------------------------------------------------
        failure_run = traffic(
            "DURING BACKEND FAILURE",
            FAILURE_REQUESTS,
        )

        if failure_run["successes"] == 0:
            raise FailureTestError(
                "no successful traffic remained while one backend was down"
            )

        if "app-02" not in failure_run["instances"]:
            raise FailureTestError(
                "app-02 did not serve traffic while app-01 was down"
            )

        print("PASS service remained available through app-02")

        # ---------------------------------------------------------
        # 4. Restore backend
        # ---------------------------------------------------------
        restore_backend(APP_CONTAINER)
        backend_was_stopped = False

        # ---------------------------------------------------------
        # 5. Prove restored backend serves again
        # ---------------------------------------------------------
        recovery = traffic(
            "RECOVERY",
            RECOVERY_REQUESTS,
        )

        if recovery["successes"] != RECOVERY_REQUESTS:
            raise FailureTestError(
                "recovery traffic was not fully successful"
            )

        if APP_CONTAINER not in recovery["instances"]:
            raise FailureTestError(
                f"recovered backend {APP_CONTAINER} "
                "was not observed serving requests"
            )

        if "app-02" not in recovery["instances"]:
            raise FailureTestError(
                "app-02 was not observed after recovery"
            )

        print("PASS recovered backend served traffic again")

        # ---------------------------------------------------------
        # 6. Final health check
        # ---------------------------------------------------------
        if not wait_for_http_health():
            raise FailureTestError(
                "final NGINX health check failed"
            )

        print("PASS final /health check")

        # ---------------------------------------------------------
        # Summary
        # ---------------------------------------------------------
        print("\n===== FAILURE TEST SUMMARY =====")
        print(
            f"baseline: successes={baseline['successes']} "
            f"errors={baseline['errors']}"
        )
        print(
            f"during_failure: successes={failure_run['successes']} "
            f"errors={failure_run['errors']}"
        )
        print(
            f"recovery: successes={recovery['successes']} "
            f"errors={recovery['errors']}"
        )

        print(
            "\nFAILURE TEST: PASS"
        )

        return 0

    except FailureTestError as exc:
        failure = True
        print(f"\nFAIL: {exc}", file=sys.stderr)
        return 1

    finally:
        # Safety cleanup:
        # if interrupted/failure occurred while app-01 was stopped,
        # bring it back without touching the rest of the environment.
        if backend_was_stopped:
            print(
                f"\nCleanup: restoring {APP_CONTAINER}",
                file=sys.stderr,
            )

            try:
                restore_backend(APP_CONTAINER)
            except Exception as exc:
                print(
                    f"Cleanup failed: {exc}",
                    file=sys.stderr,
                )

        if failure:
            print(
                "\nFAILURE TEST: FAIL",
                file=sys.stderr,
            )


if __name__ == "__main__":
    sys.exit(main())
