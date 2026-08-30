package datamesh.storage

import future.keywords.if
import future.keywords.in

known_roles := {"data-analyst", "data-steward", "data-owner"}
write_actions := {
	"s3:PutObject", "s3:DeleteObject", "s3:AbortMultipartUpload",
	"s3:CreateBucket", "s3:DeleteBucket", "s3:DeleteObjectVersion",
}

default allow := false

# Root admin (MinIO owner) always allowed
allow if {
	input.owner == true
}

# Known roles may perform any non-write action (read, list, head)
allow if {
	input.account in known_roles
	not input.action in write_actions
}

# Only data-owner may write
allow if {
	input.account == "data-owner"
	input.action in write_actions
}
