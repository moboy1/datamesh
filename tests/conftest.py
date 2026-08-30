"""
Shared fixtures for compliance scenario tests.
Generates JWT tokens with different role/domain combinations
and provides a configured OPA client and Trino connection.
"""

import os
import jwt
import pytest
import requests
import trino

JWT_SECRET  = os.getenv("JWT_SECRET", "datamesh-dev-secret-change-in-prod")
OPA_URL     = os.getenv("OPA_URL", "http://localhost:8181")
TRINO_HOST  = os.getenv("TRINO_HOST", "localhost")
TRINO_PORT  = int(os.getenv("TRINO_PORT", "8080"))


def make_token(role: str, domain: str, cross_domain: bool = False) -> str:
    """Create a signed JWT with the given role and domain claims."""
    payload = {
        "sub":  f"{role}@datamesh",
        "role": role,
        "domain": domain,
    }
    if cross_domain:
        payload["cross_domain_token"] = True
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


@pytest.fixture
def analyst_token():
    """data-analyst in the customer domain."""
    return make_token("data-analyst", "customer")


@pytest.fixture
def steward_token():
    """data-steward in the customer domain."""
    return make_token("data-steward", "customer")


@pytest.fixture
def unauth_token():
    """Unknown role — should be denied."""
    return make_token("unknown-role", "customer")


@pytest.fixture
def owner_token():
    """data-owner scoped to the customer domain."""
    return make_token("data-owner", "customer")


@pytest.fixture
def owner_deposits_token():
    """data-owner scoped to the deposits domain."""
    return make_token("data-owner", "deposits")


@pytest.fixture
def owner_cross_domain_token():
    """data-owner (customer domain) with explicit cross_domain_token — for cross-domain access."""
    return make_token("data-owner", "customer", cross_domain=True)


@pytest.fixture
def cross_domain_token():
    """data-analyst with explicit cross-domain access."""
    return make_token("data-analyst", "customer", cross_domain=True)


@pytest.fixture
def no_cross_domain_token():
    """data-analyst without cross-domain token — cross-domain queries denied."""
    return make_token("data-analyst", "customer", cross_domain=False)


@pytest.fixture
def opa():
    """Simple OPA query helper."""
    class OPAClient:
        def query(self, path: str, input_data: dict) -> dict:
            resp = requests.post(
                f"{OPA_URL}/v1/data/{path}",
                json={"input": input_data},
                timeout=5,
            )
            resp.raise_for_status()
            return resp.json().get("result", {})
    return OPAClient()


@pytest.fixture
def trino_conn():
    """Trino connection for the customer catalog."""
    conn = trino.dbapi.connect(
        host=TRINO_HOST,
        port=TRINO_PORT,
        user="test-runner",
        catalog="customer",
        schema="default",
    )
    yield conn
    conn.close()
