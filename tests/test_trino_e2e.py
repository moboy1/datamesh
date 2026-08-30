"""
End-to-End Trino Enforcement Tests
"""

import os
import pytest
import requests
import boto3
import trino
from botocore.config import Config
from botocore.exceptions import ClientError
from trino.exceptions import TrinoQueryError

OPA_URL    = os.getenv("OPA_URL",    "http://localhost:8181")
TRINO_HOST = os.getenv("TRINO_HOST", "localhost")
TRINO_PORT = int(os.getenv("TRINO_PORT", "8080"))

JWT_SECRET = os.getenv("JWT_SECRET", "datamesh-dev-secret-change-in-prod")

PII_COLUMNS = {"account_number", "national_insurance_number", "date_of_birth"}


def _trino(user: str, catalog: str = "customer", schema: str = "default"):
    """Open a Trino connection authenticated as the given user."""
    return trino.dbapi.connect(
        host=TRINO_HOST,
        port=TRINO_PORT,
        user=user,
        catalog=catalog,
        schema=schema,
        http_scheme="http",
    )


def _run(conn, sql: str):
    cur = conn.cursor()
    cur.execute(sql)
    return cur.fetchall(), [d[0] for d in cur.description]


# Scenario 1 — RBAC enforced at Trino query layer

class TestTrinoRBACEnforcement:

    def test_data_analyst_can_select_customer_records(self):
        """data-analyst is in allowed_roles -> Trino executes the query."""
        conn = _trino("data-analyst")
        rows, cols = _run(conn, "SELECT COUNT(*) FROM customer_records")
        assert rows[0][0] > 0, "Expected rows in customer_records"
        conn.close()

    def test_data_steward_can_select_customer_records(self):
        """data-steward is in allowed_roles -> Trino executes the query."""
        conn = _trino("data-steward")
        rows, _ = _run(conn, "SELECT COUNT(*) FROM customer_records")
        assert rows[0][0] > 0
        conn.close()

    def test_data_owner_can_select_customer_records(self):
        """data-owner is in allowed_roles -> Trino executes the query."""
        conn = _trino("data-owner")
        rows, _ = _run(conn, "SELECT COUNT(*) FROM customer_records")
        assert rows[0][0] > 0
        conn.close()

    def test_unknown_role_is_denied_by_trino(self):
        conn = _trino("unknown-role")
        with pytest.raises(TrinoQueryError) as exc_info:
            _run(conn, "SELECT COUNT(*) FROM customer_records")
        assert "Access Denied" in str(exc_info.value), (
            f"Expected Access Denied from OPA, got: {exc_info.value}"
        )
        conn.close()

    def test_unknown_role_denied_on_transactions_too(self):
        """OPA denial applies to all tables, not just customer_records."""
        conn = _trino("unknown-role")
        with pytest.raises(TrinoQueryError):
            _run(conn, "SELECT COUNT(*) FROM transactions")
        conn.close()


# Scenario 2 — Column masking: OPA decision -> application enforcement

class TestColumnMaskingE2E:

    def _get_masked_columns(self, token: str) -> set:
        """Ask OPA which columns must be masked for this JWT."""
        resp = requests.post(
            f"{OPA_URL}/v1/data/datamesh/masking/masked_columns",
            json={"input": {"context": {"identity": {"token": token}}}},
            timeout=5,
        )
        resp.raise_for_status()
        return set(resp.json().get("result", []))

    def _apply_mask(self, rows: list, cols: list, masked: set) -> list:
        """Replace masked column values with '***' before presenting to user."""
        masked_indices = {i for i, c in enumerate(cols) if c in masked}
        return [
            tuple("***" if i in masked_indices else v for i, v in enumerate(row))
            for row in rows
        ]

    def test_analyst_pii_is_masked_in_output(self, analyst_token):
        """
        data-analyst receives PII columns masked in the final output.
        OPA returns masked_columns; application applies the redaction.
        """
        masked_cols = self._get_masked_columns(analyst_token)
        assert masked_cols == PII_COLUMNS, (
            f"Expected OPA to mask {PII_COLUMNS}, got {masked_cols}"
        )

        conn = _trino("data-analyst")
        rows, cols = _run(
            conn,
            "SELECT customer_id, full_name, email, account_number, "
            "national_insurance_number, date_of_birth FROM customer_records LIMIT 3",
        )
        conn.close()

        masked_rows = self._apply_mask(rows, cols, masked_cols)
        col_idx = {c: i for i, c in enumerate(cols)}

        for row in masked_rows:
            assert row[col_idx["account_number"]] == "***", \
                "account_number must be masked for data-analyst"
            assert row[col_idx["national_insurance_number"]] == "***", \
                "national_insurance_number must be masked for data-analyst"
            assert row[col_idx["date_of_birth"]] == "***", \
                "date_of_birth must be masked for data-analyst"
            # Non-PII columns are intact
            assert row[col_idx["full_name"]] != "***"
            assert row[col_idx["email"]] != "***"

    def test_steward_sees_unmasked_pii(self, steward_token):
        """data-steward receives no masking — full PII visible for compliance."""
        masked_cols = self._get_masked_columns(steward_token)
        assert masked_cols == set(), \
            f"data-steward should see no masking, got {masked_cols}"

        conn = _trino("data-steward")
        rows, cols = _run(
            conn,
            "SELECT account_number, national_insurance_number, date_of_birth "
            "FROM customer_records LIMIT 1",
        )
        conn.close()

        col_idx = {c: i for i, c in enumerate(cols)}
        row = rows[0]
        assert row[col_idx["account_number"]] != "***"
        assert row[col_idx["national_insurance_number"]] != "***"

    def test_owner_sees_unmasked_pii(self, owner_token):
        """data-owner has product authority — full PII visible."""
        masked_cols = self._get_masked_columns(owner_token)
        assert masked_cols == set()

        conn = _trino("data-owner")
        rows, cols = _run(
            conn,
            "SELECT account_number FROM customer_records LIMIT 1",
        )
        conn.close()
        assert rows[0][0] != "***"


# Scenario 3 — Cross-domain: OPA restricts catalog access

class TestCrossDomainE2E:

    def test_analyst_can_query_own_domain(self):
        """data-analyst can SELECT from customer catalog (intra-domain)."""
        conn = _trino("data-analyst", catalog="customer")
        rows, _ = _run(conn, "SELECT COUNT(*) FROM customer_records")
        assert rows[0][0] > 0
        conn.close()

    def test_owner_can_query_own_domain(self):
        """data-owner can query their own domain catalog (customer) via Trino."""
        conn = _trino("data-owner", catalog="customer")
        rows, _ = _run(conn, "SELECT COUNT(*) FROM customer_records")
        assert rows[0][0] > 0
        conn.close()

    def test_cross_domain_restriction_enforced_via_opa(self):
        """
        Cross-domain restriction for domain-scoped owners is enforced at the
        OPA policy layer.
        """
        import requests as _req
        owner_customer_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkYXRhLW93bmVyQGRhdGFtZXNoIiwicm9sZSI6ImRhdGEtb3duZXIiLCJkb21haW4iOiJjdXN0b21lciJ9.Og_EXZdFNq__QznUgqwkS-RFs6th2b2ob9NYX4_auyY"
        resp = _req.post(
            f"{OPA_URL}/v1/data/datamesh/crossdomain/allow",
            json={"input": {"context": {"identity": {"token": owner_customer_token}, "catalog": "deposits"}}},
            timeout=5,
        )
        assert resp.json()["result"] is False, (
            "Customer-domain owner must be denied deposits access without cross_domain_token"
        )


# Dual-layer enforcement — the Trino bypass proof

MINIO_URL       = os.getenv("MINIO_URL", "http://localhost:9000")
CUSTOMER_BUCKET = os.getenv("MINIO_CUSTOMER_BUCKET", "customer-domain")
DEPOSITS_BUCKET = os.getenv("MINIO_DEPOSITS_BUCKET", "deposits-domain")

_S3_SECRETS = {
    "data-analyst": "analyst-secret",
    "data-steward": "steward-secret",
    "data-owner":   "owner-secret",
    "unknown-user": "unauth-secret",
}


def _s3(role: str):
    return boto3.client(
        "s3",
        endpoint_url=MINIO_URL,
        aws_access_key_id=role,
        aws_secret_access_key=_S3_SECRETS[role],
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


class TestTrinoBypassBlocked:

    def test_unknown_role_denied_at_trino(self):
        """Step 1 — Trino query layer denies unknown-role (RBAC enforcement)."""
        conn = _trino("unknown-role")
        with pytest.raises(TrinoQueryError) as exc_info:
            _run(conn, "SELECT COUNT(*) FROM customer_records")
        assert "Access Denied" in str(exc_info.value)
        conn.close()

    def test_unknown_role_also_denied_at_minio_bypass(self):
        """
        Step 2 — Storage layer denies unknown-user even if Trino is bypassed.
        MinIO calls OPA at MINIO_POLICY_PLUGIN_URL; storage.rego denies
        accounts not in known_roles. There is no path to the raw Parquet data.
        """
        with pytest.raises(ClientError) as exc_info:
            _s3("unknown-user").list_objects_v2(Bucket=CUSTOMER_BUCKET)
        error_code = exc_info.value.response["Error"]["Code"]
        assert error_code in ("AccessDenied", "403"), (
            f"Expected 403 AccessDenied from MinIO OPA plugin, got: {error_code}"
        )

    def test_known_role_allowed_through_trino(self):
        """Step 3 — Legitimate analyst can query through Trino normally."""
        conn = _trino("data-analyst")
        rows, _ = _run(conn, "SELECT COUNT(*) FROM customer_records")
        assert rows[0][0] > 0
        conn.close()

    def test_known_role_also_allowed_at_storage_layer(self):
        """
        Step 4 — Same analyst is also allowed direct S3 access (read-only).
        Consistent policy: governance is uniform across both layers.
        """
        resp = _s3("data-analyst").list_objects_v2(Bucket=CUSTOMER_BUCKET)
        assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    def test_analyst_cannot_write_via_s3_bypass(self):
        """
        Step 5 — Even a legitimate analyst cannot write to the storage layer.
        """
        with pytest.raises(ClientError) as exc_info:
            _s3("data-analyst").put_object(
                Bucket=CUSTOMER_BUCKET,
                Key="__bypass_write_probe__",
                Body=b"exfiltrated data",
            )
        error_code = exc_info.value.response["Error"]["Code"]
        assert error_code in ("AccessDenied", "403")
