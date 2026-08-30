"""
Compliance Scenario 2: Column-Level Data Masking
"""

import pytest

OPA_MASKING_PATH = "datamesh/masking"

PII_COLUMNS = {"account_number", "national_insurance_number", "date_of_birth"}


def build_input(token: str) -> dict:
    return {
        "context": {
            "identity": {"token": token},
        }
    }


class TestColumnMasking:

    def test_analyst_receives_masked_pii_columns(self, opa, analyst_token):
        """data-analyst should have all PII columns masked."""
        result = opa.query(OPA_MASKING_PATH, build_input(analyst_token))
        masked = set(result.get("masked_columns", []))
        assert masked == PII_COLUMNS, (
            f"Expected masked_columns={PII_COLUMNS}, got: {masked}"
        )

    def test_steward_receives_no_masked_columns(self, opa, steward_token):
        """data-steward should see all columns unmasked (empty masked set)."""
        result = opa.query(OPA_MASKING_PATH, build_input(steward_token))
        masked = set(result.get("masked_columns", []))
        assert masked == set(), (
            f"Expected no masked columns for data-steward, got: {masked}"
        )

    def test_owner_receives_no_masked_columns(self, opa, owner_token):
        """data-owner has product accountability and must see unmasked PII."""
        result = opa.query(OPA_MASKING_PATH, build_input(owner_token))
        masked = set(result.get("masked_columns", []))
        assert masked == set(), (
            f"Expected no masked columns for data-owner, got: {masked}"
        )

    def test_analyst_is_allowed_access(self, opa, analyst_token):
        """data-analyst should still receive an allow decision (masking, not denial)."""
        result = opa.query(OPA_MASKING_PATH, build_input(analyst_token))
        assert result.get("allow") is True, (
            f"Expected allow=True for data-analyst in masking policy, got: {result}"
        )

    def test_unauthorised_role_is_denied(self, opa, unauth_token):
        """Unknown role should be denied access entirely."""
        result = opa.query(OPA_MASKING_PATH, build_input(unauth_token))
        assert result.get("allow") is False, (
            f"Expected allow=False for unknown role, got: {result}"
        )

    def test_masking_decision_is_deterministic(self, opa, analyst_token):
        """Masking decisions must be consistent across repeated evaluations."""
        results = [
            set(opa.query(OPA_MASKING_PATH, build_input(analyst_token)).get("masked_columns", []))
            for _ in range(5)
        ]
        assert all(r == PII_COLUMNS for r in results), (
            f"Inconsistent masking results: {results}"
        )
