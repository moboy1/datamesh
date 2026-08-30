#!/usr/bin/env python3
"""
JWT Token Generator

Usage:
    python scripts/generate_token.py --role data-analyst --domain customer
    python scripts/generate_token.py --role data-owner --domain customer --cross-domain
    python scripts/generate_token.py --role data-steward --domain deposits
"""

import argparse
import os
import jwt

JWT_SECRET = os.getenv("JWT_SECRET", "datamesh-dev-secret-change-in-prod")

ROLES = ["data-analyst", "data-steward", "data-owner"]
DOMAINS = ["customer", "deposits"]


def generate(role: str, domain: str, cross_domain: bool = False) -> str:
    payload = {
        "sub": f"{role}@datamesh",
        "role": role,
        "domain": domain,
    }
    if cross_domain:
        payload["cross_domain_token"] = True
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def main():
    parser = argparse.ArgumentParser(description="Generate a signed JWT for datamesh PoC")
    parser.add_argument("--role",   required=True, choices=ROLES,   help="User role")
    parser.add_argument("--domain", required=True, choices=DOMAINS, help="User domain")
    parser.add_argument("--cross-domain", action="store_true",
                        help="Include cross_domain_token=true claim")
    args = parser.parse_args()

    token = generate(args.role, args.domain, args.cross_domain)

    print(f"\nRole:    {args.role}")
    print(f"Domain:  {args.domain}")
    print(f"Cross-domain: {args.cross_domain}")
    print(f"\nToken:\n{token}\n")

    # Also print a ready-to-use OPA curl command for demonstration
    import json
    input_payload = json.dumps({
        "input": {
            "context": {
                "identity": {"token": token},
                "catalog": args.domain
            }
        }
    }, indent=2)
    print(f"curl -s -X POST http://localhost:8181/v1/data/datamesh/query \\")
    print(f"  -H 'Content-Type: application/json' \\")
    oneliner = input_payload.replace("\n", " ").replace("  ", " ")
    print(f"  -d '{oneliner}' | python3 -m json.tool")
    print()


if __name__ == "__main__":
    main()
