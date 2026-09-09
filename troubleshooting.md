# Troubleshooting Journal

## 1. Runtime resource limits were configured but not effective

- **Symptom:** Compose contained resource settings, but `docker inspect` initially showed zero effective CPU/memory limits.
- **Hypothesis:** Compose deploy-time resource settings were not being applied to the local runtime as expected.
- **Commands:** `docker inspect ... --format ...` and Compose recreation.
- **Result:** Runtime limits initially reported `CPU=0` and `MEM=0`.
- **Fix:** Added direct Compose runtime `cpus` and `mem_limit` settings in addition to deployment resource limits.
- **Retest:** Recreated the containers and verified:
  - app-01: CPU 1, RAM 536870912
  - app-02: CPU 1, RAM 536870912
  - postgres: CPU 1, RAM 536870912
  - redis: CPU 0.5, RAM 268435456
  - nginx: CPU 0.5, RAM 134217728
- **Final result:** PASS.

## 2. PostgreSQL restore initially failed

- **Symptom:** The first restore attempt failed because the `records` relation already existed.
- **Hypothesis:** The plain SQL backup was being loaded into an already-populated schema.
- **Result:** PostgreSQL returned an error equivalent to `relation "records" already exists`.
- **Fix:** Updated `restore.sh` to reset the `public` schema before loading the backup:
  `DROP SCHEMA public CASCADE; CREATE SCHEMA public;`
- **Retest:** Ran the new restore script with `ON_ERROR_STOP=1`.
- **Result:** Restore completed successfully and the expected persistence marker was found afterwards.
- **Lesson:** A logical plain SQL dump must be restored into a compatible database state or the restore process must explicitly handle existing objects.

## 3. Application readiness depends on both PostgreSQL and Redis

- **Symptom:** Startup ordering alone is insufficient when dependencies are still initializing.
- **Hypothesis:** Health checks and dependency-aware readiness are required.
- **Fix:** Added PostgreSQL and Redis health checks, Compose health-based dependencies, and an application `/ready` endpoint.
- **Retest:** `validate.py` confirmed HTTP 200 from `/ready` and successful PostgreSQL/Redis readiness.
- **Final result:** PASS.

## 4. Backend failure behavior was tested

- **Procedure:** Establish baseline traffic, stop app-01, generate requests through NGINX, restore app-01, then repeat requests.
- **Result:** Requests continued to succeed while app-01 was stopped, with app-02 serving the traffic; after recovery both instances were observed.
- **Evidence:** `evidence/failure_test.txt`.
