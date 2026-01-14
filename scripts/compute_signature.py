#!/usr/bin/env python3
"""Helper script to compute HMAC signature for webhook requests."""
import sys
import hmac
import hashlib

if len(sys.argv) < 3:
    print("Usage: python compute_signature.py <secret> <body>")
    print("Example: python compute_signature.py 'testsecret' '{\"message_id\":\"m1\",\"from\":\"+919876543210\",\"to\":\"+14155550100\",\"ts\":\"2025-01-15T10:00:00Z\",\"text\":\"Hello\"}'")
    sys.exit(1)

secret = sys.argv[1]
body = sys.argv[2].encode('utf-8')

signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
print(signature)

