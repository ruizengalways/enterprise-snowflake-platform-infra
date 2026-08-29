# ADR-024 — Cloud-agnostic Terraform state backend profiles

- **Status:** Accepted
- **Date:** 2026-08-29
- **Supersedes:** ADR-022 backend selection; preserves its independent state-boundary decision

## Context

The Snowflake platform should not require AWS merely to store Terraform state. Enterprises commonly standardise on different control-plane ecosystems, especially Microsoft/Azure or AWS.

Terraform still needs durable remote state with concurrency protection, recovery, encryption and machine-oriented access control. A normal file-sync product such as OneDrive or SharePoint is useful for documents and evidence, but is not an appropriate concurrent Terraform state backend.

Terraform permits only one backend block in a root and the backend type cannot be selected through Terraform input variables. Therefore backend portability must be implemented outside the domain/platform modules rather than by embedding cloud conditionals throughout the Snowflake infrastructure code.

## Decision

Keep all Snowflake Terraform roots backend-agnostic in source. Select a backend profile at execution time by materialising a temporary `backend.generated.tf` into the target root.

Supported reference profiles:

```text
azurerm  -> Azure Blob Storage
s3       -> Amazon S3
```

The selector is:

```text
terraform/scripts/select-backend.sh
```

Profiles are stored under:

```text
terraform/backend-profiles/azurerm/backend.tf
terraform/backend-profiles/s3/backend.tf
```

`backend.generated.tf` is ignored by Git and must never become authoritative source.

## Microsoft-first reference profile

Azure Blob Storage is the current default/reference example for organisations centred on Microsoft Entra ID.

Use the Terraform `azurerm` backend with:

- Microsoft Entra ID data-plane authentication;
- GitHub OIDC / workload identity federation;
- no client secret for routine CI;
- container-scoped `Storage Blob Data Contributor` as the baseline data-plane role;
- Blob Storage native state locking and consistency checking.

The DEV plan workflow defaults an empty `TF_STATE_BACKEND` to `azurerm`.

## AWS reference profile

Amazon S3 remains supported for AWS-centred organisations.

Use:

- GitHub OIDC -> AWS IAM role;
- S3 bucket versioning;
- server-side encryption;
- native Terraform S3 lock files (`use_lockfile = true`);
- object-prefix permissions restricted to the required state and `.tflock` keys.

Do not add DynamoDB locking to new deployments; the Terraform S3 backend marks DynamoDB-based locking deprecated.

## OneDrive / SharePoint boundary

OneDrive and SharePoint may store:

```text
architecture documents
runbooks
change evidence
approved reports
exported audit material
```

They must not be the authoritative location for live `terraform.tfstate`.

File-sync semantics do not replace a Terraform backend's state locking, consistency and machine-access contract.

## State boundaries

Backend portability does not change the seven lifecycle boundaries:

```text
enterprise-snowflake-platform-infra/organization/terraform.tfstate
enterprise-snowflake-platform-infra/identity/dev/terraform.tfstate
enterprise-snowflake-platform-infra/identity/uat/terraform.tfstate
enterprise-snowflake-platform-infra/identity/prod/terraform.tfstate
enterprise-snowflake-platform-infra/platform/dev/terraform.tfstate
enterprise-snowflake-platform-infra/platform/uat/terraform.tfstate
enterprise-snowflake-platform-infra/platform/prod/terraform.tfstate
```

A deployment chooses one authoritative backend for these states. Do not actively mirror the same Terraform state between S3 and Azure Blob and treat both as writable sources of truth.

## Consequences

- Snowflake platform modules remain independent of the enterprise cloud used for Terraform state.
- Microsoft/Azure and AWS organisations can adopt the same platform code.
- Backend-specific authentication and configuration live at the execution edge, not in domain modules.
- Switching an existing live state backend is a controlled Terraform state migration, not a normal configuration toggle.
- Static CI validates both backend declarations without connecting to either cloud.
- A real remote plan still requires one chosen control-plane backend to exist first.
