# Architecture

See `architecture.png` / `architecture.pdf` at the repository root for the full diagram this document describes.

## Overview

The BARQ assessment environment uses NGINX as the only host-published entry point, two Flask application instances (`app-01`, `app-02`), PostgreSQL for durable application data, and Redis for counter/state functionality.

## Request flow

1. A client sends an HTTP request to `127.0.0.1:8080` (the only host-published port).
2. NGINX (container `nginx`) receives the request on its internal port `80` and reverse-proxies it, over the `frontend` network, to one of the two upstream Flask instances using NGINX's built-in load balancing. Upstreams are referenced by Compose service name (`app-01`, `app-02`), not container IP.
3. Each Flask instance (`app-01`, `app-02`) listens internally on `:8080` and, for endpoints that need it, connects over the `backend` network to `postgres:5432` and/or `redis:6379`.
4. The response returns back through the same path: application -> NGINX -> client.

## Ports

| Component | Listens on | Host-published? |
|---|---|---|
| nginx | `:80` internally | Yes — `127.0.0.1:8080` (configurable via `PUBLIC_PORT`) |
| app-01 / app-02 | `:8080` internally | No |
| postgres | `:5432` internally | No |
| redis | `:6379` internally | No |

Only NGINX is published to the host. This centralizes the attack surface and access control at a single reverse-proxy entry point (see `decisions.md` #1 and `security_review.md` #3).

## Networks

- **`frontend`** — connects `nginx` to `app-01` and `app-02`. Used only for client-facing HTTP traffic.
- **`backend`** — connects `app-01`, `app-02`, `postgres`, and `redis`. Declared `internal: true`, so it has no route to the outside world; PostgreSQL and Redis are reachable only from the application containers, never from NGINX or the host (see `decisions.md` #2–#3 and `security_review.md` #4).

Services address each other by Compose service name (`postgres`, `redis`, `app-01`, `app-02`), never by container IP, so the topology survives container recreation (see `decisions.md` #4).

## Storage

- **`postgres-data`** — named volume mounted into the `postgres` container. Holds all durable application records (the `records` table). Survives container recreation; verified in the backup/restore and persistence tests (see `decisions.md` #5, `troubleshooting.md` #2).
- **`redis-data`** — named volume mounted into the `redis` container, with append-only file (AOF) persistence enabled so the counter survives a Redis restart.

## Health and readiness relationships

- **`/health`** — liveness only. Confirms the Flask process is up; does not check dependencies.
- **`/ready`** — readiness. Confirms both PostgreSQL and Redis are reachable and responding, so NGINX/orchestration can distinguish "process is running" from "process can actually serve traffic" (see `decisions.md` #7).
- Compose health checks are defined for `postgres`, `redis`, and each app instance, and application containers use `depends_on` health conditions so they don't start accepting dependency-bound work before PostgreSQL/Redis report healthy (see `troubleshooting.md` #3).
- NGINX itself does not perform active health checks against upstreams in this setup; instance identity and rotation are verified functionally through `/instance` and `validate.py`.

## Identity and load balancing

`/instance` returns which backend (`app-01` or `app-02`) served a given request, which is how load balancing and post-recovery behavior are proven in `validate.py`, `failure_test.py`, and the video demonstration.
