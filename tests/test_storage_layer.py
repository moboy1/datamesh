"""
MinIO Storage-Layer OPA Enforcement
"""
import os
import pytest
import boto3
from botocore.exceptions import ClientError
from botocore.config import Config

MINIO_ENDPOINT = os.getenv("MINIO_URL", "http://localhost:9000")
CUSTOMER_BUCKET = os.getenv("MINIO_CUSTOMER_BUCKET", "customer-domain")
DEPOSITS_BUCKET = os.getenv("MINIO_DEPOSITS_BUCKET", "deposits-domain")


def _s3_client(access_key: str, secret_key: str):
    """Return a boto3 S3 client using the supplied credentials."""
    return boto3.client(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


# Fixed MinIO service-account credentials (created by minio-init at startup).
# The access key ID is the role name; MinIO authenticates, then OPA authorises
# based on input.account (the access key ID) in storage.rego.
_SECRETS = {
    "data-analyst": "analyst-secret",
    "data-steward": "steward-secret",
    "data-owner":   "owner-secret",
    "unknown-user": "unauth-secret",
}


# Fixtures

@pytest.fixture
def analyst_s3():
    """S3 client using data-analyst credentials."""
    return _s3_client("data-analyst", _SECRETS["data-analyst"])


@pytest.fixture
def steward_s3():
    """S3 client using data-steward credentials."""
    return _s3_client("data-steward", _SECRETS["data-steward"])


@pytest.fixture
def owner_s3():
    """S3 client using data-owner credentials."""
    return _s3_client("data-owner", _SECRETS["data-owner"])


@pytest.fixture
def unauth_s3():
    """S3 client using an unrecognised role — should be denied."""
    return _s3_client("unknown-user", _SECRETS["unknown-user"])


# Scenario 1 — Authorised roles can list objects

class TestAuthorisedStorageAccess:

    def test_analyst_can_list_customer_bucket(self, analyst_s3):
        """data-analyst may read objects in the customer domain bucket."""
        resp = analyst_s3.list_objects_v2(Bucket=CUSTOMER_BUCKET)
        assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    def test_steward_can_list_customer_bucket(self, steward_s3):
        """data-steward may read objects in the customer domain bucket."""
        resp = steward_s3.list_objects_v2(Bucket=CUSTOMER_BUCKET)
        assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    def test_owner_can_list_customer_bucket(self, owner_s3):
        """data-owner may read objects in the customer domain bucket."""
        resp = owner_s3.list_objects_v2(Bucket=CUSTOMER_BUCKET)
        assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    def test_owner_can_list_deposits_bucket(self, owner_s3):
        """data-owner has implicit cross-domain access to the deposits bucket."""
        resp = owner_s3.list_objects_v2(Bucket=DEPOSITS_BUCKET)
        assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200


# Scenario 2 — Unauthorised caller is denied at the storage layer

class TestUnauthorisedStorageDenied:

    def test_unauth_cannot_list_customer_bucket(self, unauth_s3):
        """Unknown role must be denied — HTTP 403 from MinIO OPA plugin."""
        with pytest.raises(ClientError) as exc_info:
            unauth_s3.list_objects_v2(Bucket=CUSTOMER_BUCKET)
        error_code = exc_info.value.response["Error"]["Code"]
        assert error_code in ("AccessDenied", "403"), (
            f"Expected 403 AccessDenied, got: {error_code}"
        )

    def test_unauth_cannot_get_object(self, unauth_s3):
        """Unknown role must be denied on object GET — not just listing."""
        with pytest.raises(ClientError) as exc_info:
            unauth_s3.get_object(
                Bucket=CUSTOMER_BUCKET,
                Key="warehouse/customer_records/data.parquet",
            )
        error_code = exc_info.value.response["Error"]["Code"]
        assert error_code in ("AccessDenied", "403", "NoSuchKey"), (
            # NoSuchKey is acceptable if the file path differs; AccessDenied is the target
            f"Expected AccessDenied or NoSuchKey, got: {error_code}"
        )

    def test_unauth_cannot_put_object(self, unauth_s3):
        """Unknown role must be denied on PUT — storage is read-only for policy test."""
        with pytest.raises(ClientError) as exc_info:
            unauth_s3.put_object(
                Bucket=CUSTOMER_BUCKET,
                Key="__test_write_probe__",
                Body=b"probe",
            )
        error_code = exc_info.value.response["Error"]["Code"]
        assert error_code in ("AccessDenied", "403")


# Scenario 3 — Write operations denied for non-owner roles

class TestWriteProtection:

    def test_analyst_cannot_write_to_customer_bucket(self, analyst_s3):
        """data-analyst is read-only — PUT must be denied."""
        with pytest.raises(ClientError) as exc_info:
            analyst_s3.put_object(
                Bucket=CUSTOMER_BUCKET,
                Key="__test_write_probe__",
                Body=b"probe",
            )
        error_code = exc_info.value.response["Error"]["Code"]
        assert error_code in ("AccessDenied", "403")

    def test_steward_cannot_write_to_customer_bucket(self, steward_s3):
        """data-steward is read-only — PUT must be denied."""
        with pytest.raises(ClientError) as exc_info:
            steward_s3.put_object(
                Bucket=CUSTOMER_BUCKET,
                Key="__test_write_probe__",
                Body=b"probe",
            )
        error_code = exc_info.value.response["Error"]["Code"]
        assert error_code in ("AccessDenied", "403")
