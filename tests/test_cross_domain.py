"""
Compliance Scenario 3: Cross-Domain Query Restriction
"""

import pytest

OPA_CROSSDOMAIN_PATH = "datamesh/crossdomain"


def build_input(token: str, target_catalog: str) -> dict:
    return {
        "context": {
            "identity": {"token": token},
            "catalog": target_catalog,
        }
    }


class TestCrossDomainRestriction:

    def test_intra_domain_query_is_allowed(self, opa, analyst_token):
        """Analyst querying their own domain (customer->customer) should be allowed."""
        result = opa.query(
            OPA_CROSSDOMAIN_PATH,
            build_input(analyst_token, target_catalog="customer"),
        )
        assert result.get("allow") is True

    def test_cross_domain_with_token_is_allowed(self, opa, cross_domain_token):
        """Analyst with explicit cross_domain_token querying deposits -> allowed."""
        result = opa.query(
            OPA_CROSSDOMAIN_PATH,
            build_input(cross_domain_token, target_catalog="deposits"),
        )
        assert result.get("allow") is True

    def test_cross_domain_without_token_is_denied(self, opa, no_cross_domain_token):
        """Analyst without cross_domain_token querying deposits -> denied."""
        result = opa.query(
            OPA_CROSSDOMAIN_PATH,
            build_input(no_cross_domain_token, target_catalog="deposits"),
        )
        assert result.get("allow") is False

    def test_denial_includes_reason(self, opa, no_cross_domain_token):
        """OPA should return a reason string explaining the denial."""
        result = opa.query(
            OPA_CROSSDOMAIN_PATH,
            build_input(no_cross_domain_token, target_catalog="deposits"),
        )
        assert "reason" in result
        assert "cross_domain_token" in result["reason"]

    # Domain-scoped ownership

    def test_owner_can_access_own_domain(self, opa, owner_token):
        """Customer-domain owner querying customer catalog -> allowed (intra-domain)."""
        result = opa.query(
            OPA_CROSSDOMAIN_PATH,
            build_input(owner_token, target_catalog="customer"),
        )
        assert result.get("allow") is True

    def test_owner_denied_cross_domain_without_token(self, opa, owner_token):
        """Customer-domain owner querying deposits -> denied without cross_domain_token."""
        result = opa.query(
            OPA_CROSSDOMAIN_PATH,
            build_input(owner_token, target_catalog="deposits"),
        )
        assert result.get("allow") is False, (
            "Expected domain-scoped owner to be denied cross-domain access "
            f"without explicit token, got: {result}"
        )

    def test_owner_allowed_cross_domain_with_token(self, opa, owner_cross_domain_token):
        """Customer-domain owner with cross_domain_token -> allowed on deposits."""
        result = opa.query(
            OPA_CROSSDOMAIN_PATH,
            build_input(owner_cross_domain_token, target_catalog="deposits"),
        )
        assert result.get("allow") is True

    def test_deposits_owner_can_access_deposits(self, opa, owner_deposits_token):
        """Deposits-domain owner querying deposits catalog -> allowed (intra-domain)."""
        result = opa.query(
            OPA_CROSSDOMAIN_PATH,
            build_input(owner_deposits_token, target_catalog="deposits"),
        )
        assert result.get("allow") is True

    def test_deposits_owner_denied_customer_domain(self, opa, owner_deposits_token):
        """Deposits-domain owner cannot query customer domain without a token."""
        result = opa.query(
            OPA_CROSSDOMAIN_PATH,
            build_input(owner_deposits_token, target_catalog="customer"),
        )
        assert result.get("allow") is False

    def test_unknown_domain_is_denied(self, opa, cross_domain_token):
        """Cross-domain token to an unknown catalog should be denied."""
        result = opa.query(
            OPA_CROSSDOMAIN_PATH,
            build_input(cross_domain_token, target_catalog="unknown-catalog"),
        )
        assert result.get("allow") is False

    def test_owner_cannot_access_unknown_domain(self, opa, owner_token):
        """data-owner is bounded to known domains even with a cross_domain_token."""
        result = opa.query(
            OPA_CROSSDOMAIN_PATH,
            build_input(owner_token, target_catalog="unknown-catalog"),
        )
        assert result.get("allow") is False
