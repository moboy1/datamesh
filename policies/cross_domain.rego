package datamesh.crossdomain

import future.keywords.if
import future.keywords.in

# Known domains in this PoC
domains := {"customer", "deposits"}

# HMAC secret — must match the token issuer
jwt_secret := "datamesh-dev-secret-change-in-prod"

# Default deny
default allow := false

# Intra-domain: requester's domain matches the target catalog
# Applies to all roles including data-owner (scoped to their own domain)
allow if {
	token := input.context.identity.token
	io.jwt.verify_hs256(token, jwt_secret)
	payload := io.jwt.decode(token)[1]
	payload.domain == input.context.catalog
}

# Cross-domain: requires explicit cross_domain_token claim
# All roles — including data-owner — must hold an explicit token to query
# outside their domain. This creates an auditable cross-domain access event.
allow if {
	token := input.context.identity.token
	io.jwt.verify_hs256(token, jwt_secret)
	payload := io.jwt.decode(token)[1]
	payload.cross_domain_token == true
	payload.role in {"data-analyst", "data-steward", "data-owner"}
	input.context.catalog in domains
}

# Audit metadata returned with every decision
reason := msg if {
	not allow
	msg := "cross-domain access denied: no cross_domain_token present in JWT"
}
