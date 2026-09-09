# Technical Decisions

## 1. NGINX is the only published application entry point

- **Decision:** Publish only NGINX on `127.0.0.1:8080`; keep Flask, PostgreSQL, and Redis unexposed to the host.
- **Assumptions:** All application traffic enters through the reverse proxy.
- **Alternatives:** Publish Flask ports directly; expose PostgreSQL/Redis for administration.
- **Trade-off:** Centralized access control and smaller attack surface, at the cost of requiring NGINX for application access.
- **Limitations:** The current deployment is local and binds only to loopback.

## 2. Separate frontend and backend Docker networks

- **Decision:** NGINX and application containers use `frontend`; applications, PostgreSQL, and Redis use `backend`.
- **Assumptions:** Application containers require access to both the reverse proxy network and internal dependencies.
- **Alternatives:** Put every service on one shared network.
- **Trade-off:** Better network segmentation and clearer trust boundaries, with slightly more Compose configuration.
- **Limitations:** Network isolation is Docker-level isolation, not a replacement for production firewalling or cloud security groups.

## 3. Keep the backend network internal

- **Decision:** Configure the `backend` Docker network with `internal: true`.
- **Assumptions:** PostgreSQL and Redis do not require direct external connectivity.
- **Alternatives:** Use a normal bridge network.
- **Trade-off:** Reduces accidental external reachability, while application containers still communicate with required dependencies.
- **Limitations:** Exact external egress behavior depends on Docker networking and host configuration.

## 4. Use service names instead of container IP addresses

- **Decision:** Applications connect to `postgres:5432` and `redis:6379`.
- **Assumptions:** Docker Compose DNS provides stable service discovery.
- **Alternatives:** Hard-code container IP addresses.
- **Trade-off:** Service-name discovery survives recreation and scaling, while IP-based addressing would be brittle.
- **Limitations:** The current NGINX configuration names explicit application services for the assignment scenario.

## 5. Persist PostgreSQL and Redis data in named volumes

- **Decision:** PostgreSQL uses `postgres-data`; Redis uses `redis-data`.
- **Assumptions:** Container recreation must not destroy application state.
- **Alternatives:** Store state only in container filesystems.
- **Trade-off:** Persistent state survives container recreation, but volumes require explicit lifecycle and backup management.
- **Limitations:** A named volume is not itself a backup strategy; PostgreSQL logical backup is also implemented.

## 6. Run application containers as a non-root user

- **Decision:** The application image creates and uses an unprivileged user with UID/GID `10001`.
- **Assumptions:** The application does not require root privileges.
- **Alternatives:** Run the Flask process as root.
- **Trade-off:** Reduces impact of application compromise, with minimal configuration complexity.
- **Limitations:** Production hardening should also include read-only filesystem and Linux capability restrictions where compatible.

## 7. Use bounded health/readiness checks

- **Decision:** `/health` verifies process availability and `/ready` verifies PostgreSQL and Redis readiness.
- **Assumptions:** NGINX should route traffic only to healthy application containers.
- **Alternatives:** Use process checks only.
- **Trade-off:** Dependency-aware readiness prevents routing traffic to an instance that cannot serve correctly.
- **Limitations:** The checks are lightweight and do not prove full business-function correctness.

## 8. Enforce explicit container resource limits

- **Decision:** Define CPU and memory limits for NGINX, both application instances, PostgreSQL, and Redis.
- **Assumptions:** Resource usage must be bounded for predictable local execution.
- **Alternatives:** Rely only on host-level resources.
- **Trade-off:** Prevents one service from consuming unlimited resources, at the cost of possible throttling under abnormal load.
- **Limitations:** The selected values are internship-task limits, not production capacity planning.

## 9. Keep secrets outside the image and repository

- **Decision:** Runtime PostgreSQL credentials are supplied through `.env`; `.env`, `config/app.env`, backups, and generated local artifacts are ignored.
- **Assumptions:** Secrets should not be copied into Docker images or committed source.
- **Alternatives:** Bake credentials into the image or Compose file.
- **Trade-off:** Safer secret handling, but deployment requires correct environment configuration.
- **Limitations:** `.env` is suitable for this assignment; production should use a dedicated secret manager.

## 10. Validate behavior with executable checks

- **Decision:** Use `validate.py` and `failure_test.py` as repeatable acceptance checks.
- **Assumptions:** Manual browser or curl checks alone are insufficient for a reproducible submission.
- **Alternatives:** Manual testing only.
- **Trade-off:** Automated checks improve repeatability and CI integration, at the cost of maintaining test code.
- **Limitations:** These checks cover the assignment requirements rather than full production observability and performance testing.
