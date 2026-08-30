# Containerised Data Mesh PoC

---

## Quick Start

```bash
make demo
```

Runs the full end-to-end sequence: start services -> init iceberg tables -> generate synthetic data -> compliance tests -> capture OPA audit log.

### Prerequisites

- Docker
- Docker Compose 
- Python 3.10+
- OPA CLI
- `.env` file (see below)

### Create your `.env` file

Create a `.env` file in the repo root with the following:

```bash
# MinIO
MINIO_ROOT_USER=admin
MINIO_ROOT_PASSWORD=admin1234
MINIO_CUSTOMER_BUCKET=customer-domain
MINIO_DEPOSITS_BUCKET=deposits-domain
MINIO_AUDIT_BUCKET=audit-logs

# Nessie
NESSIE_PORT=19120

# Trino
TRINO_PORT=8080

# OPA
OPA_PORT=8181

# OPAL
OPAL_SERVER_PORT=7002
OPAL_CLIENT_PORT=7766
# Point at the Git repo (policies/ directory). Public repo — no token needed.
OPAL_POLICY_REPO_URL=https://github.com/moboy1/datamesh
OPAL_POLICY_REPO_MAIN_BRANCH=master
OPAL_POLICY_SUBSCRIPTION_DIRS=policies
OPAL_POLICY_REPO_POLLING_INTERVAL=30

# JWT signing
JWT_SECRET=datamesh-dev-secret-change-in-prod
```

NOTE: `JWT_SECRET` must match the `jwt_secret` value hardcoded in `policies/*.rego`. Tokens signed with a different secret will fail OPA's signature check. If `OPAL_POLICY_REPO_URL` points at a private repo instead, embed a token: `https://oauth2:<token>@gitlab.com/<org>/<repo>` (GitLab) or `https://<token>@github.com/<org>/<repo>` (GitHub).

### Step-by-step

```bash
make up              # Start up all containers
make init-tables     # Create Iceberg schemas and tables in Trino
make generate-data   # Generate synthetic banking data
make generate-token  # Generate token
make test            # Run all compliance scenario tests
make down            # Stop and remove all containers
```

### OPA unit tests (no Docker required)

```bash
make opa-check       # Lint all Rego files
```

### Generate a JWT for manual testing

```bash
ROLE=data-analyst DOMAIN=customer make generate-token
ROLE=data-owner   DOMAIN=deposits  make generate-token
```

### Run individual compliance scenarios

```bash
make test-rbac         # Scenario 1 — Role-Based Access Control
make test-masking      # Scenario 2 — Column-Level Data Masking
make test-crossdomain  # Scenario 3 — Cross-Domain Query Restriction
make test-storage      # MinIO storage-layer bypass test (dual-layer proof)
```

```bash
make help              # Full list of targets
```

---

## JWT Token Claims

All requests carry a signed JWT with the following claims:

```json
{
  "sub": "data-analyst@datamesh",
  "role": "data-analyst",
  "domain": "customer",
  "cross_domain_token": true
}
```

`cross_domain_token` is only present when explicit cross-domain access is granted.

---

## Diagrams

UML source files are in `diagrams/`. Render with `make diagrams` (requires PlantUML + Java) or paste into [plantuml.com](https://www.plantuml.com/plantuml/uml/).

| File | Type | Description |
|---|---|---|
| `diagrams/jwt_auth_flow.puml` | Sequence | JWT auth -> Trino -> OPA -> allow/deny (all 3 scenarios) |
| `diagrams/opal_policy_push_flow.puml` | Sequence | GitOps policy push: Git -> OPAL -> OPA |
| `diagrams/component_diagram.puml` | Component | Five-layer containerised stack with interfaces |

---

## Service Endpoints

| Service | URL |
|---|---|
| MinIO Console | http://localhost:9001 |
| MinIO S3 API | http://localhost:9000 |
| Nessie API | http://localhost:19120/api/v1 |
| Trino UI | http://localhost:8080 |
| OPA API | http://localhost:8181 |
| OPAL Server | http://localhost:7002 |
