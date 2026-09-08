#!/usr/bin/env python3

import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid


BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8080")
COMPOSE_PROJECT = os.getenv("COMPOSE_PROJECT", "barq-assessment")

REQUIRED_SERVICES = {
    "nginx",
    "app-01",
    "app-02",
    "postgres",
    "redis",
}

EXPECTED_NETWORKS = {
    "nginx": {"frontend"},
    "app-01": {"frontend", "backend"},
    "app-02": {"frontend", "backend"},
    "postgres": {"backend"},
    "redis": {"backend"},
}

PROHIBITED_HOST_PORT_SERVICES = {
    "app-01",
    "app-02",
    "postgres",
    "redis",
}


class ValidationError(Exception):
    pass


def run_command(command, timeout=10):
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        raise ValidationError(
            f"command failed: {' '.join(command)}: {exc}"
        ) from exc

    if result.returncode != 0:
        raise ValidationError(
            f"command failed ({result.returncode}): {' '.join(command)}\n"
            f"{result.stderr.strip()}"
        )

    return result.stdout.strip()


def http_request(path, method="GET", payload=None, timeout=5):
    url = f"{BASE_URL}{path}"

    data = None
    headers = {}

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        url,
        data=data,
        headers=headers,
        method=method,
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            return response.status, body
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return exc.code, body
    except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        raise ValidationError(
            f"{method} {path} failed: {exc}"
        ) from exc


def check_http_endpoint(path, expected_status=200):
    status, body = http_request(path)

    if status != expected_status:
        raise ValidationError(
            f"{path}: expected HTTP {expected_status}, got {status}"
        )

    if not body.strip():
        raise ValidationError(f"{path}: empty response")

    print(f"PASS endpoint {path} -> HTTP {status}")
    return body


def wait_for_http(timeout=60):
    deadline = time.time() + timeout

    while time.time() < deadline:
        try:
            status, _ = http_request("/health", timeout=2)
            if status == 200:
                return
        except ValidationError:
            pass

        time.sleep(2)

    raise ValidationError(
        f"NGINX did not become healthy within {timeout}s"
    )


def inspect_networks(container):
    output = run_command(
        [
            "docker",
            "inspect",
            container,
            "--format",
            "{{range $name, $net := .NetworkSettings.Networks}}{{$name}} {{end}}",
        ]
    )

    return {
        item.strip()
        for item in output.split()
        if item.strip()
    }


def inspect_host_ports(container):
    output = run_command(
        [
            "docker",
            "port",
            container,
        ]
    )

    return output.strip()


def check_compose_services():
    output = run_command(
        [
            "docker",
            "compose",
            "-p",
            COMPOSE_PROJECT,
            "ps",
            "--services",
        ]
    )

    services = set(output.splitlines())

    missing = REQUIRED_SERVICES - services

    if missing:
        raise ValidationError(
            f"missing Compose services: {', '.join(sorted(missing))}"
        )

    print("PASS required Compose services")


def check_container_state():
    output = run_command(
        [
            "docker",
            "compose",
            "-p",
            COMPOSE_PROJECT,
            "ps",
            "-q",
        ]
    )

    containers = [
        item.strip()
        for item in output.splitlines()
        if item.strip()
    ]

    if len(containers) < len(REQUIRED_SERVICES):
        raise ValidationError(
            "not all required containers are running"
        )

    for container in sorted(REQUIRED_SERVICES):
        state = run_command(
            [
                "docker",
                "inspect",
                container,
                "--format",
                "{{.State.Status}}",
            ]
        )

        if state != "running":
            raise ValidationError(
                f"{container}: state is {state}, expected running"
            )

    print("PASS required containers running")


def check_network_isolation():
    for container, expected_suffixes in EXPECTED_NETWORKS.items():
        actual_full = inspect_networks(container)

        actual_suffixes = {
            network.rsplit("_", 1)[-1]
            for network in actual_full
        }

        if actual_suffixes != expected_suffixes:
            raise ValidationError(
                f"{container}: networks {sorted(actual_suffixes)}, "
                f"expected {sorted(expected_suffixes)}"
            )

        print(
            f"PASS networks {container} -> "
            f"{', '.join(sorted(actual_suffixes))}"
        )

    backend_network = f"{COMPOSE_PROJECT}_backend"

    internal = run_command(
        [
            "docker",
            "network",
            "inspect",
            backend_network,
            "--format",
            "{{.Internal}}",
        ]
    )

    if internal.lower() != "true":
        raise ValidationError(
            f"{backend_network}: expected Internal=true, got {internal}"
        )

    print("PASS backend network is internal")


def check_host_ports():
    nginx_ports = inspect_host_ports("nginx")

    if "127.0.0.1:8080" not in nginx_ports:
        raise ValidationError(
            f"nginx: expected host binding on 127.0.0.1:8080, got {nginx_ports}"
        )

    print("PASS nginx published port 127.0.0.1:8080")

    for container in sorted(PROHIBITED_HOST_PORT_SERVICES):
        try:
            output = inspect_host_ports(container)
        except ValidationError:
            output = ""

        if output:
            raise ValidationError(
                f"{container}: prohibited host port detected: {output}"
            )

        print(f"PASS no host port for {container}")


def check_ready():
    body = check_http_endpoint("/ready", 200)

    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise ValidationError(
            "/ready: response is not valid JSON"
        ) from exc

    text = json.dumps(data).lower()

    if "postgres" not in text:
        raise ValidationError(
            "/ready: PostgreSQL readiness not reported"
        )

    if "redis" not in text:
        raise ValidationError(
            "/ready: Redis readiness not reported"
        )

    print("PASS /ready reports PostgreSQL and Redis")


def check_instances():
    seen = set()

    for _ in range(10):
        body = check_http_endpoint("/instance", 200)

        try:
            data = json.loads(body)
        except json.JSONDecodeError as exc:
            raise ValidationError(
                "/instance: response is not valid JSON"
            ) from exc

        instance = (
            data.get("instance_id")
            or data.get("instance")
            or data.get("id")
        )

        if instance:
            seen.add(str(instance))

    expected = {"app-01", "app-02"}

    if seen != expected:
        raise ValidationError(
            f"/instance: observed {sorted(seen)}, expected both app-01 and app-02"
        )

    print("PASS load balancing observed app-01 and app-02")


def check_records():
    body = check_http_endpoint("/records", 200)

    try:
        records = json.loads(body)
    except json.JSONDecodeError as exc:
        raise ValidationError(
            "/records: response is not valid JSON"
        ) from exc

    if not isinstance(records, (list, dict)):
        raise ValidationError(
            "/records: unexpected response type"
        )

    marker = f"validation-{uuid.uuid4().hex[:12]}"

    status, post_body = http_request(
        "/records",
        method="POST",
        payload={"title": marker},
    )

    if status not in (200, 201):
        raise ValidationError(
            f"/records POST: expected 200/201, got {status}: {post_body}"
        )

    print(f"PASS /records POST -> HTTP {status}")

    body = check_http_endpoint("/records", 200)

    if marker not in body:
        raise ValidationError(
            "record created successfully but was not found in subsequent GET"
        )

    print("PASS /records persistence verified")


def check_counter():
    status1, body1 = http_request("/counter")
    if status1 != 200:
        raise ValidationError(
            f"/counter first request: HTTP {status1}"
        )

    status2, body2 = http_request("/counter")
    if status2 != 200:
        raise ValidationError(
            f"/counter second request: HTTP {status2}"
        )

    try:
        value1 = int(body1.strip())
        value2 = int(body2.strip())
    except ValueError:
        try:
            value1 = int(json.loads(body1)["counter"])
            value2 = int(json.loads(body2)["counter"])
        except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            raise ValidationError(
                "/counter: response is not an integer or expected JSON"
            ) from exc

    if value2 <= value1:
        raise ValidationError(
            f"/counter did not increase: {value1} -> {value2}"
        )

    print(f"PASS /counter increased {value1} -> {value2}")


def check_resource_limits():
    expected = {
        "app-01": ("1", "536870912"),
        "app-02": ("1", "536870912"),
        "postgres": ("1", "536870912"),
        "redis": ("0.5", "268435456"),
        "nginx": ("0.5", "134217728"),
    }

    for container, (expected_cpu, expected_memory) in expected.items():
        cpu = run_command(
            [
                "docker",
                "inspect",
                container,
                "--format",
                "{{.HostConfig.NanoCpus}}",
            ]
        )

        memory = run_command(
            [
                "docker",
                "inspect",
                container,
                "--format",
                "{{.HostConfig.Memory}}",
            ]
        )

        expected_nano_cpus = str(int(float(expected_cpu) * 1_000_000_000))

        if cpu != expected_nano_cpus:
            raise ValidationError(
                f"{container}: CPU limit {cpu}, "
                f"expected {expected_nano_cpus}"
            )

        if memory != expected_memory:
            raise ValidationError(
                f"{container}: memory limit {memory}, "
                f"expected {expected_memory}"
            )

        print(
            f"PASS resources {container} -> "
            f"CPU {expected_cpu}, RAM {expected_memory}"
        )


def main():
    checks = [
        ("Compose services", check_compose_services),
        ("container state", check_container_state),
        ("network isolation", check_network_isolation),
        ("host ports", check_host_ports),
        ("resource limits", check_resource_limits),
        ("HTTP availability", wait_for_http),
        ("/", lambda: check_http_endpoint("/")),
        ("/health", lambda: check_http_endpoint("/health")),
        ("/ready", check_ready),
        ("/instance", check_instances),
        ("/records", check_records),
        ("/counter", check_counter),
    ]

    failures = 0

    print(f"BARQ validation starting: {BASE_URL}")
    print()

    for name, check in checks:
        try:
            check()
        except ValidationError as exc:
            failures += 1
            print(f"FAIL {name}: {exc}", file=sys.stderr)

    print()

    if failures:
        print(f"VALIDATION: FAIL ({failures} check(s) failed)")
        return 1

    print("VALIDATION: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
