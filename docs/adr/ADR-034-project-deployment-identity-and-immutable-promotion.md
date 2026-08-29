# ADR-034 — Project deployment identity and immutable promotion

- **Status:** Accepted
- **Date:** 2026-08-29

## Context

ADR-027 separated DEV PR-CI service identity from platform Terraform state. Stable DEV/UAT/PROD project delivery now also needs a non-human Snowflake principal that can own long-lived project runtime objects such as Streams, Tasks and Dynamic Tables.

Using `AR_<DOMAIN>_ADMIN` as the routine deployment principal would couple background object ownership to human administration, require standing UAT/PROD transform compute for humans, and make deployment identity depend on employee lifecycle. Reusing platform Terraform identity would also violate the lifecycle boundary between stable platform infrastructure and data-project delivery.

Promotion must also prevent environment branches, unreviewed side-branch commits, or mutable framework references from silently changing code between DEV, UAT and PROD.

## Decision

Create an independent machine deployment role per domain in every environment account:

```text
AR_<DOMAIN>_DEPLOY
```

It is outside the human `GUEST -> READER -> DEVELOPER -> ADMIN` hierarchy and receives only the project delivery capabilities required by the current Snowflake-native runtime baseline:

```text
DR_<DOMAIN>_ANALYTICS_WRITE
USAGE on WH_<DOMAIN>_TRANSFORM
CREATE STREAM on stable domain schemas
CREATE TASK on stable domain schemas
CREATE DYNAMIC TABLE on stable domain schemas
EXECUTE TASK
```

Do not grant `EXECUTE MANAGED TASK` while the baseline uses named warehouses.

Bind the role to a Snowflake SERVICE user through GitHub OIDC / Snowflake Workload Identity Federation:

```text
SU_GITHUB_<DOMAIN>_DEPLOY -> AR_<DOMAIN>_DEPLOY
```

Project deployment service users are created in independent lifecycle roots after the platform root has created their target roles:

```text
identity/<env>
  -> platform/<env>
      -> project-identity/<env>
```

State keys remain independent:

```text
enterprise-snowflake-platform-infra/project-identity/dev/terraform.tfstate
enterprise-snowflake-platform-infra/project-identity/uat/terraform.tfstate
enterprise-snowflake-platform-infra/project-identity/prod/terraform.tfstate
```

The `service-identity` Terraform module owns only SERVICE user/WIF trust and role assignment. RBAC Terraform owns role capabilities.

## GitHub trust boundary

Each service user trusts only its analytics repository and target GitHub Environment, for example:

```text
repo:ruizengalways/enterprise-snowflake-health-analytics:environment:dev
repo:ruizengalways/enterprise-snowflake-health-analytics:environment:uat
repo:ruizengalways/enterprise-snowflake-health-analytics:environment:prod
```

Transport uses the Transport repository. Each Snowflake account uses an account-scoped OIDC audience rather than the shared `snowflakecomputing.com` audience.

Environment-level Snowflake account/audience configuration is consumed only after the protected GitHub Environment job starts. The reusable workflow uses configuration variables from the calling analytics repository, not from the framework repository.

## Immutable promotion

Stable project delivery uses the framework reusable workflow and thin project callers.

A deployment must provide:

```text
full lowercase 40-character project Git SHA
full lowercase 40-character framework Git SHA
```

The project SHA must be reachable from the current `main` branch history. The workflow first checks out full `main` history, verifies the requested commit exists and is an ancestor of current `main`, then switches to that exact commit in detached HEAD mode. An arbitrary commit that exists only on an unmerged side branch therefore cannot be deployed through the standard path.

The framework is checked out by its exact SHA. The workflow also verifies the project's `dbt/packages.yml` framework revision matches the workflow framework SHA.

Promotion is therefore:

```text
same reviewed main-history project SHA
DEV -> UAT -> PROD
```

The environment changes Snowflake account/database/warehouse and GitHub Environment protection, not the source revision. Environment branches are not used.

Deployments to the same domain/environment are serialized and are not cancelled by a newer deployment request.

## Human administration and break-glass

UAT/PROD human roles receive no permanent transform warehouse grant in the baseline. `AR_<DOMAIN>_ADMIN` remains a governed administration role but is not the routine deployment principal.

Emergency manual transform execution must be approved and granted just-in-time through enterprise identity governance, then removed after the incident/change window. Named employee membership and temporary emergency compute entitlement are not encoded in Terraform.

DEV remains different by design: human `DEVELOPER` keeps interactive transform compute for development, while stable DEV deployment automation still uses `AR_<DOMAIN>_DEPLOY`.

## Consequences

- Long-lived project Tasks/Dynamic Tables do not depend on a human owner retaining routine compute.
- Health deployment identity cannot authenticate from the Transport repository, and vice versa.
- Platform Terraform identity is not reused for project delivery.
- UAT/PROD routine transform execution becomes machine-only.
- Break-glass access is visible as an identity-governance event rather than an always-on Terraform grant.
- An unmerged side-branch commit cannot be supplied directly to the standard deployment workflow.
- Promotion can prove that the exact reviewed project revision reaches each environment.
- `project-identity/<env>` must not be applied before `platform/<env>` creates its target deployment roles.

## Verification gate

Static CI proves Terraform/workflow structure only. Before production rollout, live DEV must prove:

1. account-scoped GitHub OIDC authentication;
2. environment-level account/audience configuration becomes available only after the protected environment job starts;
3. `SU_GITHUB_<DOMAIN>_DEPLOY` resolves only `AR_<DOMAIN>_DEPLOY`;
4. a reviewed `main` commit can deploy while an unmerged side-branch SHA is rejected;
5. deployment can create and own warehouse-backed Stream/Task/Dynamic Table objects;
6. Task execution works with `EXECUTE TASK` and the named transform warehouse;
7. no standing human UAT/PROD transform grant is required for routine delivery;
8. the same project Git SHA can be promoted without source mutation.

## Related decisions

- ADR-023 — platform Terraform GitHub OIDC identity.
- ADR-024 — selectable Azure Blob / S3 Terraform state backend profiles.
- ADR-025 — DEV personal and PR workspace lifecycle.
- ADR-027 — DEV PR-CI OIDC identity lifecycle.
- ADR-033 — prefer Snowflake-native primitives before custom runtime.
