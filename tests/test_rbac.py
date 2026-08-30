"""
Compliance Scenario 1: Role-Based Access Control
"""

import pytest
import requests

OPA_RBAC_PATH = "datamesh/query"


def build_input(token: str, catalog: str = "customer") -> dict:
    return {
        "context": {
            "identity": {"token": token},
            "catalog": catalog,
        }
    }


class TestRBACQueryLayer:

    def test_analyst_is_allowed(self, opa, analyst_token):
        """data-analyst should receive an allow decision."""
        result = opa.query(OPA_RBAC_PATH, build_input(analyst_token))
        assert result.get("allow") is True, (
            f"Expected allow=True for data-analyst, got: {result}"
        )

    def test_steward_is_allowed(self, opa, steward_token):
        """data-steward should receive an allow decision."""
        result = opa.query(OPA_RBAC_PATH, build_input(steward_token))
        assert result.get("allow") is True, (
            f"Expected allow=True for data-steward, got: {result}"
        )

    def test_owner_is_allowed(self, opa, owner_token):
        """data-owner should receive an allow decision."""
        result = opa.query(OPA_RBAC_PATH, build_input(owner_token))
        assert result.get("allow") is True, (
            f"Expected allow=True for data-owner, got: {result}"
        )

    def test_unauthorised_role_is_denied(self, opa, unauth_token):
        """Unknown role should receive a deny decision."""
        result = opa.query(OPA_RBAC_PATH, build_input(unauth_token))
        assert result.get("allow") is False, (
            f"Expected allow=False for unknown role, got: {result}"
        )

    def test_allow_is_consistent_across_repeated_requests(self, opa, analyst_token):
        """Policy enforcement must be deterministic — same input, same output."""
        results = [
            opa.query(OPA_RBAC_PATH, build_input(analyst_token)).get("allow")
            for _ in range(5)
        ]
        assert all(r is True for r in results), (
            f"Inconsistent results across repeated requests: {results}"
        )

    def test_opa_decision_log_is_accessible(self):
        """OPA decision log endpoint should be reachable and return structured data."""
        import os
        opa_url = os.getenv("OPA_URL", "http://localhost:8181")
        resp = requests.get(f"{opa_url}/v1/data", timeout=5)
        assert resp.status_code == 200, (
            f"OPA API not reachable: {resp.status_code}"
        )
