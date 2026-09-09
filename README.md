# BARQ Systems DevOps Internship Task

Containerized Flask API environment with NGINX load balancing, PostgreSQL, Redis, health/readiness checks, persistence, backup/restore, automated validation, failure testing, and CI.

## Architecture

The runtime consists of:

- NGINX reverse proxy
- `app-01` Flask application instance
- `app-02` Flask application instance
- PostgreSQL
- Redis

Network segmentation:

- `frontend`: NGINX + application instances
- `backend`: application instances + PostgreSQL + Redis
- `backend` is Docker `internal: true`

Only NGINX is published to the host.

### Runtime topology

```text
Client
  |
  | 127.0.0.1:8080
  v
+-------------------+
| nginx :80         |
+-------------------+
          |
      frontend
      /       \
     v         v
+---------+ +---------+
| app-01  | | app-02  |
| :8080   | | :8080   |
+---------+ +---------+
      \       /
       \     /
        backend
        /     \
       v       v
+-----------+ +---------+
| postgres  | | redis   |
| :5432     | | :6379   |
+-----------+ +---------+
     |             |
     v             v
postgres-data   redis-data
```

## Prerequisites

- Docker Engine
- Docker Compose v2
- Bash
- Python 3
- curl

## Configuration

Create `.env` from the example:

```bash
cp .env.example .env
```

Set a strong local PostgreSQL password:

```bash
POSTGRES_PASSWORD=change-this-local-password
PUBLIC_PORT=8080
```

`.env` is intentionally ignored by Git.

## Build and start

```bash
docker compose -p barq-assessment build
docker compose -p barq-assessment up -d
```

Check service state:

```bash
docker compose -p barq-assessment ps
```

## Health and readiness

Application health:

```bash
curl -fsS http://127.0.0.1:8080/health
```

Dependency-aware readiness:

```bash
curl -fsS http://127.0.0.1:8080/ready
```

Instance identity:

```bash
curl -fsS http://127.0.0.1:8080/instance
```

## API endpoints

**Root**
```bash
curl -fsS http://127.0.0.1:8080/
```

**Health**
```bash
curl -fsS http://127.0.0.1:8080/health
```

**Readiness**
```bash
curl -fsS http://127.0.0.1:8080/ready
```

**Instance**
```bash
curl -fsS http://127.0.0.1:8080/instance
```

Run it repeatedly to observe load balancing:

```bash
for i in $(seq 1 10); do
  curl -fsS http://127.0.0.1:8080/instance
  echo
done
```

**Records**

List records:

```bash
curl -fsS http://127.0.0.1:8080/records
```

Create a record:

```bash
curl -fsS \
  -X POST \
  -H 'Content-Type: application/json' \
  -d '{"title":"readme-test"}' \
  http://127.0.0.1:8080/records
```

**Counter**
```bash
curl -fsS http://127.0.0.1:8080/counter
```

## Automated validation

Run the complete assignment validation:

```bash
./validate.py
```

The validator checks:

- required services
- required containers
- network topology
- internal backend network
- host-port exposure
- resource limits
- HTTP endpoints
- dependency readiness
- load balancing
- record persistence
- Redis-backed counter behavior

A successful run ends with:

```text
VALIDATION: PASS
```

## Failure test

Run:

```bash
./failure_test.py
```

The test:

1. Establishes baseline traffic.
2. Stops app-01.
3. Sends traffic through NGINX.
4. Verifies service continuity through app-02.
5. Restores app-01.
6. Verifies both instances recover.

Evidence is stored under `evidence/`.

## Backup

Create a PostgreSQL logical backup:

```bash
./backup.sh
```

Backups are written to:

```text
backups/
```

The directory is intentionally ignored by Git.

## Restore

Restore a PostgreSQL backup:

```bash
./restore.sh backups/<backup-file>.sql
```

The restore script:

- validates the backup
- verifies PostgreSQL is running
- resets the `public` schema
- restores the SQL dump with `ON_ERROR_STOP=1`
- verifies the `records` table exists

## Persistence test

PostgreSQL data is stored in the named volume:

```text
barq-assessment_postgres-data
```

Recreating the PostgreSQL and application containers does not remove the volume:

```bash
docker compose -p barq-assessment up -d --force-recreate postgres app-01 app-02
```

The persistence marker can then be verified through:

```bash
curl -fsS http://127.0.0.1:8080/records
```

## Network inspection

Check backend isolation:

```bash
docker network inspect barq-assessment_backend \
  --format 'Internal={{.Internal}} Gateway={{.IPAM.Config}}'
```

Check frontend:

```bash
docker network inspect barq-assessment_frontend \
  --format 'Internal={{.Internal}} Gateway={{.IPAM.Config}}'
```

Inspect exposed ports:

```bash
docker compose -p barq-assessment ps
```

Only NGINX should have a host-published port.

## CI

GitHub Actions workflow:

```text
.github/workflows/ci.yml
```

The workflow performs:

1. checkout
2. required-file checks
3. Python syntax checks
4. shell syntax checks
5. Compose configuration validation
6. image build
7. service startup
8. readiness wait
9. complete validation
10. cleanup

## Stop

```bash
docker compose -p barq-assessment stop
```

**Start again**

```bash
docker compose -p barq-assessment start
```

**Stop and remove containers**

```bash
docker compose -p barq-assessment down
```

**Remove containers and persistent volumes**

Only use this when intentionally deleting application data:

```bash
docker compose -p barq-assessment down -v
```

## Project documentation

- `troubleshooting.md` — investigation journal and failed attempts
- `log_analysis.md` — analysis of the supplied logs
- `decisions.md` — architectural and implementation decisions
- `security_review.md` — implemented security controls and production recommendations
- `AI_USAGE.md` — AI assistance disclosure
- `docs/ARCHITECTURE.md` — architecture description
- `docs/EVIDENCE_INDEX.md` — requirement-to-evidence mapping

## Evidence

Generated verification artifacts are stored under:

```text
evidence/
```

Examples:

- `resource_limits_verification.txt`
- `failure_test.txt`
- `backup_restore_verification.txt`
- `backup_restore_final.txt`

## Security notes

Do not commit:

- `.env`
- `config/app.env`
- `config/app.env.save`
- database backups
- generated local assessment artifacts

The repository must be reviewed for historical secrets before public push.

## License

This repository is an internship assignment submission for BARQ Systems.
