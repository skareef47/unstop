# API Authentication and Key Rotation Troubleshooting Guide [SEC-AUTH-01]

Version: 2.1
Status: Approved
Author: Security & Identity Architecture Team

## Overview
This runbook guides technical support engineers and developers through diagnosing authentication errors across PSAI public and private API endpoints.

## HTTP 401 Unauthorized After Key Rotation
When credentials or API keys are rotated in the enterprise secret vault, upstream API gateways often cache verification tokens for up to 30 minutes to reduce cryptographic overhead.

Common symptoms:
- Client receives HTTP 401 Unauthorized despite passing the new API key.
- Error message returns `Invalid or expired credentials`.
- Requests using old credentials fail immediately with `Revoked credential key`.

## Root Cause and Token Cache Invalidation
1. **Stale Gateway Cache**: The edge API gateway has not invalidated its local cache. It attempts to verify the incoming signature against the superseded key version.
2. **Client Environment Delay**: Containerized customer services have not reloaded their configuration variables from the secret manager.

## Diagnostic Procedures
1. Run the `check_api_credentials` diagnostic tool to test active gateway cache keys against the master vault.
2. If cache mismatch is confirmed, execute `mock_config_correction` to trigger an immediate cache invalidation signal.
3. Verify resolution using `verify_config_sync` to validate active token acceptance.
