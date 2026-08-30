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
- `.env` file with `OPAL_POLICY_REPO_URL` set to the Git repo

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
