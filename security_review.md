# Security Review

This review separates implemented controls from production recommendations.

## Implemented controls

### 1. Secret leakage into the container image
- **Risk:** Credentials copied into an image become recoverable from image history/layers.
- **Implemented fix:** The application Dockerfile no longer copies `config/app.env` into `/srv`.
- **Evidence:** Dockerfile uses runtime environment variables instead of baking credentials into the image.

### 2. Secret leakage into Git
- **Risk:** Committed credentials remain recoverable from repository history.
- **Implemented fix:** Local secret files are removed from the working tree and ignored.
- **Important limitation:** Repository history must be reviewed and cleaned before public push if any real credential was previously committed.

### 3. Unnecessary host-exposed ports
- **Risk:** Direct access to Flask, PostgreSQL, or Redis increases attack surface.
- **Implemented fix:** Only NGINX is published on the host; application, PostgreSQL, and Redis containers have no host-published ports.
- **Evidence:** `validate.py` explicitly verifies prohibited host ports are absent.

### 4. Excessive network reachability
- **Risk:** A compromised edge-facing service could directly reach infrastructure services.
- **Implemented fix:** Frontend and backend networks are separated and backend is internal.
- **Evidence:** `validate.py` verifies the network topology and backend `internal=true`.

### 5. Root execution
- **Risk:** Application compromise while running as root increases container escape and filesystem impact.
- **Implemented fix:** The application image runs as UID/GID `10001`.
- **Limitation:** NGINX/PostgreSQL/Redis use vendor images and their own runtime users/configuration.

### 6. Resource exhaustion
- **Risk:** Unlimited CPU or memory consumption can destabilize the environment.
- **Implemented fix:** Explicit CPU and memory limits are configured for all five services.
- **Evidence:** `resource_limits_verification.txt` and `validate.py` verify effective runtime limits.

### 7. Dependency readiness
- **Risk:** Applications can receive traffic before PostgreSQL or Redis is ready.
- **Implemented fix:** Compose health checks and dependency conditions are used, and `/ready` verifies PostgreSQL and Redis readiness.
- **Evidence:** `validate.py` confirms `/ready` and both dependency states.

### 8. Data-loss risk during container recreation
- **Risk:** Container-local PostgreSQL storage would be lost during recreation.
- **Implemented fix:** PostgreSQL uses a named persistent volume and Redis uses a named persistent volume.
- **Evidence:** The backup/restore verification proves the application record survived container recreation.

### 9. Backup integrity risk
- **Risk:** A backup can exist but still be unusable for recovery.
- **Implemented fix:** `backup.sh` creates a PostgreSQL logical SQL dump and `restore.sh` performs a real restore followed by schema verification.
- **Evidence:** `evidence/backup_restore_verification.txt` shows successful restore and recovery of the expected record.

### 10. Secret leakage into application logs
- **Risk:** `DATABASE_URL` includes the PostgreSQL password in plain text. Logging it at startup writes the credential to stdout/container logs, which are typically retained, aggregated, and less tightly access-controlled than the secret store itself.
- **Implemented fix:** The startup log event now records only whether `DATABASE_URL`/`REDIS_URL` are configured (booleans), never their values.
- **Evidence:** `app/server.py` startup log call no longer interpolates the raw connection strings.

## Production recommendations

### 11. Backup confidentiality
- Backups may contain application data and should be encrypted at rest and access-controlled.
- Retention, rotation, off-host storage, and restore testing should be implemented.

### 12. Monitoring and alerting
- Production should collect NGINX access/error logs, application logs, container health, CPU/memory metrics, and dependency health.
- Alerts should detect elevated 5xx rates, failed readiness checks, and resource saturation.

### 13. Image supply-chain hardening
- Production images should be scanned continuously, minimized, and ideally pinned by digest.
- CI should enforce dependency and image vulnerability policies.

### 14. Runtime hardening
- Production deployment should consider read-only root filesystems, dropped Linux capabilities, seccomp/AppArmor profiles, and stronger isolation.

### 15. Availability
- Two application replicas provide basic redundancy, but production requires orchestration, health-aware load balancing, autoscaling, and multi-node failure handling.

### 16. Secret management
- Production credentials should be stored in a secret manager rather than a local `.env` file.
