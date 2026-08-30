package datamesh.masking

import future.keywords.if
import future.keywords.in

# PII columns that require masking for non-steward roles
pii_columns := {"account_number", "national_insurance_number", "date_of_birth"}

# data-steward and data-owner may see unmasked PII
# data-owner has product accountability and must be able to audit PII fields
privileged_roles := {"data-steward", "data-owner"}

# HMAC secret — must match the token issuer
jwt_secret := "datamesh-dev-secret-change-in-prod"

# Default: mask all PII columns
default masked_columns := {"account_number", "national_insurance_number", "date_of_birth"}

# Privileged roles see everything unmasked
masked_columns := set() if {
	token := input.context.identity.token
	io.jwt.verify_hs256(token, jwt_secret)
	payload := io.jwt.decode(token)[1]
	payload.role in privileged_roles
}

# Expose allow decision for RBAC gate
default allow := false

allow if {
	token := input.context.identity.token
	io.jwt.verify_hs256(token, jwt_secret)
	payload := io.jwt.decode(token)[1]
	payload.role in {"data-analyst", "data-steward", "data-owner"}
}
