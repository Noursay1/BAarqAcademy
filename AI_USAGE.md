# AI Usage Disclosure

AI assistance was used during development of this internship submission.

## Tools / models
- OpenAI ChatGPT (exact model version not recorded at the time of use)
- Anthropic Claude, accessed via claude.ai

Both tools were used at different points during development, alongside manual investigation and local testing.

## Purpose
- Troubleshooting Docker Compose networking, health checks, resource limits, persistence, backup/restore, validation, CI structure, and documentation.
- Reviewing implementation choices against the assignment requirements.
- Generating draft scripts and documentation that were then executed and verified locally.

## Files or decisions affected
- `docker-compose.yml`
- `Dockerfile`
- `validate.py`
- `failure_test.py`
- `backup.sh`
- `restore.sh`
- `.github/workflows/ci.yml`
- `README.md`
- `troubleshooting.md`
- `decisions.md`
- `security_review.md`
- `log_analysis.md`
- `docs/ARCHITECTURE.md`
- `docs/EVIDENCE_INDEX.md`

## What was changed or rejected
- Proposed fixes were inspected and tested locally before being kept.
- A resource-limit approach that was present in Compose but ineffective at runtime was corrected after `docker inspect` verification.
- The first PostgreSQL restore implementation failed against an existing schema and was replaced with a schema-reset restore flow.
- Secrets were removed from the active Docker build path and local secret files were added to `.gitignore`.

## Independent verification
- `docker compose config --quiet`
- `bash -n` for shell scripts
- Python compilation checks
- `validate.py`
- `failure_test.py`
- Docker network and port inspection
- Container resource inspection
- Real PostgreSQL backup and restore
- Persistence verification after container recreation
- `git diff --check`

## Related commits
AI-assisted changes were committed progressively as investigation, fixes, and verification work. Final commit references must be recorded in the evidence index after the final history is cleaned and pushed.
