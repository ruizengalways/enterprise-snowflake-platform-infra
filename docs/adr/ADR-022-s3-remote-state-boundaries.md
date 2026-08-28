# ADR-022 — S3 remote state with independent lifecycle boundaries

- **Status:** Accepted
- **Date:** 2026-08-29

## Context

The platform now has organization bootstrap, per-account workload-identity bootstrap, and routine DEV/UAT/PROD Terraform lifecycles. Local state or one shared state file would create unacceptable loss, concurrency and blast-radius risk.

The state backend must support durable storage, locking, recovery and secretless GitHub access without coupling Snowflake authentication to Terraform state authentication.

## Decision

Use an Amazon S3 backend as the reference platform control-plane state store.

Every Terraform root declares a partial S3 backend:

```hcl
terraform {
  backend "s3" {
    encrypt      = true
    use_lockfile = true
  }
}
```

Bucket and region are supplied at `terraform init` time rather than committed into each root. GitHub Actions accesses the bucket through AWS OIDC and a narrowly scoped IAM role; static AWS access keys are not stored in GitHub.

The bucket is a one-time control-plane prerequisite and must have versioning enabled. Bucket access must be restricted to the exact state/lock object prefixes required by the relevant automation identities.

DynamoDB locking is not used. Terraform's S3 lockfile mechanism is the selected locking mechanism.

## State boundaries

Use separate state objects:

```text
enterprise-snowflake-platform-infra/organization/terraform.tfstate
enterprise-snowflake-platform-infra/identity/dev/terraform.tfstate
enterprise-snowflake-platform-infra/identity/uat/terraform.tfstate
enterprise-snowflake-platform-infra/identity/prod/terraform.tfstate
enterprise-snowflake-platform-infra/platform/dev/terraform.tfstate
enterprise-snowflake-platform-infra/platform/uat/terraform.tfstate
enterprise-snowflake-platform-infra/platform/prod/terraform.tfstate
```

Organization state must not contain account-level platform objects. Identity state must not contain normal project databases/warehouses/RBAC. Routine platform state must not own the service user used to authenticate that same routine workflow.

## Why S3

- mature Terraform backend support;
- native state locking via `.tflock`;
- bucket versioning provides a practical state-recovery mechanism;
- fine-grained object-prefix IAM policies support environment separation;
- GitHub can obtain AWS credentials through OIDC rather than long-lived access keys;
- the backend is independent of the Snowflake account itself, so a broken Snowflake account does not remove its Terraform state.

Using S3 for control-plane state does not require Snowflake itself to run on AWS.

## Consequences

- An AWS account/control-plane bucket is an explicit external prerequisite.
- State bucket bootstrap is not recursively managed by a Terraform state that depends on that same bucket.
- GitHub environments must provide `TF_STATE_BUCKET`, `TF_STATE_REGION`, and `AWS_TERRAFORM_STATE_ROLE_ARN` before remote plan/apply can run.
- State remains sensitive even when credentials are secretless; bucket encryption, restrictive IAM, versioning and audit logging remain required.
- PROD state permissions must be narrower and independently approvable from DEV.
