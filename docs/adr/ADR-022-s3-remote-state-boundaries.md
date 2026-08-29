# ADR-022 — S3 remote state with independent lifecycle boundaries

- **Status:** Superseded by ADR-024
- **Date:** 2026-08-29

## Context

The platform needed durable Terraform state with locking/recovery and initially selected Amazon S3 as the reference backend.

## Historical decision

The original implementation used S3 with native lock files, bucket versioning, GitHub OIDC to AWS, and seven independent state object keys for organization, identity and platform lifecycles.

That state-boundary decision remains valid, but the AWS-specific backend choice is no longer canonical.

## Superseded by

ADR-024 keeps the seven independent state boundaries while making the Snowflake platform backend-agnostic. Azure Blob Storage is the Microsoft-first reference profile and Amazon S3 remains a supported alternative.

OneDrive/SharePoint is explicitly not a Terraform state backend.
