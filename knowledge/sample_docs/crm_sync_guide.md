# CRM Webhook and Synchronization Integration Runbook [INT-CRM-03]

Version: 1.4
Status: Approved
Author: Partner Integrations Engineering

## Overview
PSAI communicates with external CRM systems via outbound HTTPS webhooks and asynchronous batch synchronization workers.

## Webhook Timeout Beyond 10,000ms
External CRM partner endpoints must acknowledge webhook payloads within a strict 10,000ms (10 seconds) socket timeout window.

Failure symptoms:
- Outbound worker error: `HTTPConnectionTimeout: Request exceeded 10,000ms threshold`.
- Sync queue depth accumulates unacknowledged customer records.
- Repeated retry attempts result in circuit breaker activation.

## Diagnostic Protocol
1. Execute `check_crm_webhook_connectivity` to evaluate latency, TLS handshake time, and packet loss.
2. If the initial probe fails with socket timeout, trigger a second probe to distinguish transient latency from sustained partner downtime.
3. If the partner endpoint remains unresponsive after retries, automated recovery cannot succeed. Immediately escalate to Integrations Tier 2 via `mock_service_escalation`.
