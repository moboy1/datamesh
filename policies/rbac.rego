package datamesh.query

import future.keywords.if
import future.keywords.in

# Roles permitted to read customer data products
# data-owner: accountability and product authority (Dehghani, 2022)
# data-steward: quality and compliance custodian
# data-analyst: read-only consumer
allowed_roles := {"data-analyst", "data-steward", "data-owner"}

# HMAC secret — shared between token issuer and OPA for signature verification
jwt_secret := "datamesh-dev-secret-change-in-prod"

# Default deny
default allow := false

# Allow Trino admin user — infrastructure/DDL operations (CREATE TABLE etc.)
allow if {
	input.context.identity.user == "admin"
}

# Allow by Trino username — direct connections where username IS the role
# Enables end-to-end Trino enforcement tests without requiring JWT auth config
allow if {
	input.context.identity.user in allowed_roles
}

# Allow by verified JWT — signature checked before trusting role claim
# io.jwt.verify_hs256 returns false for forged or tampered tokens
allow if {
	token := input.context.identity.token
	io.jwt.verify_hs256(token, jwt_secret)
	payload := io.jwt.decode(token)[1]
	payload.role in allowed_roles
}
