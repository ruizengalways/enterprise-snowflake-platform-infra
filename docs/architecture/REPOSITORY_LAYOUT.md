# Canonical Repository Directory Layout

> **Status:** Accepted architecture plan
>
> **Scope:** All five Enterprise Snowflake repositories
>
> **Rule:** This document plans the target structure before implementation. Git does not track empty directories, so directories are created only when their first real file is introduced. Do not add `.gitkeep` files merely to make the tree look complete.

## 1. Directory design principles

1. **Repository boundaries come before folder convenience.** Shared technical behaviour belongs in the framework or platform repository rather than being duplicated in Health/Transport.
2. **One concern, one authoritative location.** Avoid parallel folders that could own the same Snowflake object or operational behaviour.
3. **Thin project repositories.** Health and Transport mainly contain project metadata, RAW contracts, domain SQL/tests, semantic definitions, and source-specific ingestion configuration.
4. **Executable GitHub workflows live under `.github/workflows/`.** Reusable framework workflows also live there because that is the GitHub-supported location for reusable workflows.
5. **Terraform is organised by reusable capability plus deployable account stack.** Modules contain reusable platform capabilities; stacks compose them for NONPROD and PROD.
6. **Snowflake SQL is separated by lifecycle purpose.** Bootstrap, control-plane, governance, monitoring, alerts and recovery logic do not get mixed with dbt models.
7. **Configuration is data, not code.** Environment/project/access metadata belongs under `config/`; credentials and secrets never do.
8. **No premature placeholder directories.** A planned directory appears in Git only when implementation reaches it.

---

# 2. `enterprise-snowflake-platform-infra`

Central platform repository and architecture authority.

```text
enterprise-snowflake-platform-infra/
├── README.md
├── .gitignore
├── .editorconfig
│
├── docs/
│   ├── PROJECT_BLUEPRINT.md
│   │
│   ├── architecture/
│   │   ├── REPOSITORY_LAYOUT.md
│   │   ├── ACCOUNT_TOPOLOGY.md              # when account topology becomes executable
│   │   ├── RBAC_MODEL.md                    # when Phase 1 role hierarchy is finalised
│   │   └── RELEASE_AND_RECOVERY.md          # when delivery spine is implemented
│   │
│   ├── adr/
│   │   ├── ADR-001-five-repository-architecture.md
│   │   ├── ADR-004-object-ownership-and-terraform-boundary.md
│   │   ├── ADR-006-metadata-driven-technical-behaviour.md
│   │   ├── ADR-007-raw-contract-boundary.md
│   │   └── ...                              # only meaningful decisions get files
│   │
│   ├── standards/
│   │   ├── NAMING_CONVENTIONS.md
│   │   ├── TERRAFORM_STANDARDS.md           # Phase 1
│   │   └── SQL_STANDARDS.md                 # when native SQL begins
│   │
│   └── runbooks/
│       ├── deployment-rollback.md            # later phase
│       ├── data-recovery.md                  # later phase
│       └── incident-response.md              # later phase
│
├── config/
│   ├── environments/
│   │   ├── nonprod.yml
│   │   └── prod.yml
│   │
│   ├── projects/
│   │   ├── health.yml
│   │   └── transport.yml
│   │
│   ├── access-profiles/
│   │   └── ...                              # capability/profile mappings when required
│   │
│   └── governance/
│       └── ...                              # classification/tag/policy config when required
│
├── terraform/
│   ├── modules/
│   │   ├── analytics-environment/           # database + stable environment schemas
│   │   ├── warehouse/                       # standard warehouse controls
│   │   ├── rbac/                            # account/database roles + grants
│   │   ├── platform-control/                # PLATFORM_CONTROL structural objects
│   │   ├── workload-identity/               # GitHub OIDC/workload identity, later in Phase 1
│   │   └── cost-controls/                   # monitors/budgets/tags when implemented
│   │
│   └── stacks/
│       ├── nonprod/
│       │   ├── versions.tf
│       │   ├── providers.tf
│       │   ├── variables.tf
│       │   ├── locals.tf
│       │   ├── main.tf
│       │   ├── outputs.tf
│       │   └── terraform.tfvars.example
│       │
│       └── prod/
│           ├── versions.tf
│           ├── providers.tf
│           ├── variables.tf
│           ├── locals.tf
│           ├── main.tf
│           ├── outputs.tf
│           └── terraform.tfvars.example
│
├── snowflake/
│   ├── bootstrap/
│   │   └── ...                              # minimal privileged bootstrap SQL only
│   │
│   ├── control/
│   │   ├── ddl/
│   │   ├── procedures/
│   │   └── tasks/
│   │
│   ├── governance/
│   │   ├── tags/
│   │   ├── masking/
│   │   └── row-access/
│   │
│   ├── monitoring/
│   │   ├── views/
│   │   └── queries/
│   │
│   ├── alerts/
│   │   └── ...
│   │
│   └── recovery/
│       ├── clone-swap/
│       └── validation/
│
└── .github/
    └── workflows/
        ├── terraform-ci.yml                 # validate/format/lint first
        ├── terraform-plan-nonprod.yml       # when remote execution is wired
        ├── terraform-apply-nonprod.yml      # later; protected
        ├── terraform-plan-prod.yml          # later
        └── terraform-apply-prod.yml         # later; protected/approved
```

### Platform Infra ownership notes

- `terraform/` owns stable infrastructure state.
- `snowflake/` owns selected native SQL objects that Terraform/dbt should not own.
- `config/` provides non-secret declarative inputs; Terraform and later operational tooling consume them where appropriate.
- Do **not** create a separate top-level `observability/` folder unless we later have assets that clearly do not belong in `snowflake/monitoring`, dashboards, or control-plane SQL. This avoids duplicate ownership.
- Terraform state, `.tfvars` containing real values, keys, passwords and tokens are never committed.

### Phase 1 minimum structure actually required

Phase 1 should begin with only these real paths:

```text
docs/architecture/REPOSITORY_LAYOUT.md
config/environments/
terraform/modules/analytics-environment/
terraform/modules/warehouse/
terraform/modules/rbac/
terraform/modules/platform-control/
terraform/stacks/nonprod/
.github/workflows/terraform-ci.yml
```

`prod/`, workload identity, cost controls and native Snowflake SQL are added only when their implementation step begins.

---

# 3. `enterprise-snowflake-data-project-framework`

Versioned golden path consumed by data project repositories.

```text
enterprise-snowflake-data-project-framework/
├── README.md
├── CHANGELOG.md
│
├── dbt_package/
│   ├── dbt_project.yml
│   │
│   ├── macros/
│   │   ├── environment/
│   │   ├── loading/
│   │   │   ├── full_refresh/
│   │   │   ├── append_only/
│   │   │   └── incremental_merge/
│   │   ├── scd2/
│   │   │   ├── snapshot/
│   │   │   ├── merge/
│   │   │   └── stream_task/
│   │   ├── reconciliation/
│   │   ├── freshness/
│   │   ├── audit/
│   │   └── operations/
│   │
│   └── tests/
│       └── generic/
│
├── project_schema/
│   ├── project.schema.json
│   ├── dataset.schema.json
│   └── raw_contract.schema.json             # when contract CI begins
│
├── validation/
│   ├── pyproject.toml                       # only if validator becomes a Python package
│   ├── src/
│   └── tests/
│
├── bootstrap/
│   ├── templates/
│   └── scripts/
│
├── examples/
│   ├── minimal-project/
│   └── metadata/
│
├── docs/
│   ├── patterns/
│   │   ├── load-strategies.md
│   │   ├── scd2.md
│   │   └── metadata.md
│   └── operations/
│       ├── reconciliation.md
│       ├── freshness.md
│       ├── backfill.md
│       └── recovery.md
│
└── .github/
    └── workflows/
        ├── framework-ci.yml
        ├── pr-ci.yml                        # reusable workflow
        ├── deploy-dev.yml                   # reusable workflow
        ├── promote-uat.yml                  # reusable workflow
        ├── promote-prod.yml                 # reusable workflow
        ├── rollback-prod.yml                # reusable workflow
        ├── recover-data.yml                 # reusable workflow
        └── backfill.yml                     # reusable workflow
```

### Framework ownership notes

- Reusable GitHub workflows live under `.github/workflows/`, not a custom `workflows/` directory, so project repositories can call them with `uses:` and a pinned tag/SHA.
- `validation/` is for metadata/schema validation tooling only; it must not grow into a second orchestration framework.
- Domain-specific SQL never belongs here.
- New strategies are added only when two or more projects can plausibly benefit, or when they are explicitly part of the approved platform pattern catalog.

---

# 4. `enterprise-snowflake-demo-source-systems`

Represents the external world. Its responsibility ends at the source/RAW boundary.

```text
enterprise-snowflake-demo-source-systems/
├── README.md
├── pyproject.toml
├── .env.example
│
├── sources/
│   ├── health/
│   │   ├── generator/
│   │   ├── database/
│   │   └── files/
│   │
│   └── transport/
│       ├── generator/
│       └── files/
│
├── adapters/
│   ├── rest/
│   ├── sse/
│   └── gtfs_realtime/
│
├── sinks/
│   ├── files/
│   ├── sql_server/
│   ├── snowflake_direct/
│   ├── snowpipe_streaming/
│   └── kafka/
│
├── scenarios/
│   ├── normal/
│   ├── late_arriving/
│   ├── out_of_order/
│   ├── duplicates/
│   ├── deletes/
│   ├── bad_data/
│   ├── source_outage/
│   ├── schema_change/
│   └── volume_spike/
│
├── config/
│   ├── health/
│   └── transport/
│
└── tests/
    ├── unit/
    └── integration/
```

### Demo Source ownership notes

- `sources/` generates logical source records.
- `sinks/` changes delivery technology without changing the logical source generator.
- `scenarios/` describes deterministic mutations/failure modes reused across source domains where possible.
- No dbt models, marts, semantic views, downstream reconciliation, or project SCD2 logic are allowed here.
- Direct Snowpipe Streaming and Kafka should consume the same Transport logical event model.

---

# 5. `enterprise-snowflake-health-analytics`

Thin Health project repository for traditional enterprise/batch/CDC behaviour.

```text
enterprise-snowflake-health-analytics/
├── README.md
│
├── config/
│   ├── project.yml
│   ├── datasets/
│   │   └── <dataset>.yml
│   ├── contracts/
│   │   └── raw/
│   │       └── <source_entity>.yml
│   └── operations/
│       └── ...                              # project-specific thresholds/overrides only
│
├── dbt/
│   ├── dbt_project.yml
│   ├── packages.yml                         # pins framework version/tag
│   │
│   ├── models/
│   │   ├── staging/
│   │   ├── intermediate/
│   │   ├── canonical/
│   │   ├── marts/
│   │   └── semantic/
│   │
│   ├── snapshots/
│   ├── tests/
│   │   ├── singular/
│   │   └── domain/
│   └── seeds/                               # only small reference/test data when justified
│
├── ingestion/
│   └── openflow/                            # Phase 8 only
│       └── ...
│
└── .github/
    └── workflows/
        ├── pr-ci.yml                        # thin caller of framework workflow
        ├── deploy-dev.yml
        ├── promote-uat.yml
        └── promote-prod.yml
```

### Health ownership notes

- Generic SCD2 macros/mechanics stay in the framework; Health selects a strategy with metadata and owns genuine Health business logic.
- RAW contracts are project-owned and remain stable when ingestion changes from synthetic/file/database simulation to Openflow later.
- Project workflow files should be thin wrappers around versioned framework reusable workflows.

---

# 6. `enterprise-snowflake-transport-analytics`

Thin Transport project repository for event/streaming behaviour.

```text
enterprise-snowflake-transport-analytics/
├── README.md
│
├── config/
│   ├── project.yml
│   ├── datasets/
│   │   └── <dataset>.yml
│   ├── contracts/
│   │   └── raw/
│   │       └── <event_contract>.yml
│   └── operations/
│       └── ...
│
├── dbt/
│   ├── dbt_project.yml
│   ├── packages.yml                         # pins framework version/tag
│   │
│   ├── models/
│   │   ├── staging/
│   │   ├── intermediate/
│   │   ├── canonical/
│   │   ├── marts/
│   │   └── semantic/
│   │
│   ├── snapshots/
│   ├── tests/
│   │   ├── singular/
│   │   └── domain/
│   └── seeds/
│
├── ingestion/
│   ├── snowpipe_streaming/
│   │   └── ...                              # direct path configuration/integration
│   └── kafka_connector/
│       └── ...                              # Kafka Connector configuration/integration
│
└── .github/
    └── workflows/
        ├── pr-ci.yml
        ├── deploy-dev.yml
        ├── promote-uat.yml
        └── promote-prod.yml
```

### Transport ownership notes

- Both ingestion paths target the same project-owned RAW event contract.
- Only one path is normally active for a given test run/environment unless a test explicitly evaluates duplicates.
- Producer/runtime code belongs in Demo Source Systems; project-side connector/integration configuration belongs here.
- Event ordering, lateness and deduplication policy may be metadata-driven when generic; genuinely Transport-specific interpretation remains explicit SQL.

---

# 7. Cross-repository dependency direction

Allowed dependency direction:

```text
enterprise-snowflake-platform-infra
        │
        ├── provisions platform guardrails / infrastructure
        │
        ▼
health-analytics / transport-analytics
        ▲
        │ consume pinned reusable package/workflows
        │
enterprise-snowflake-data-project-framework

enterprise-snowflake-demo-source-systems
        │
        └── produces external-style source data/events
                ↓
             RAW contract
                ↓
      health / transport projects
```

Important rules:

- Framework must not import project code.
- Platform Infra must not contain Health/Transport business models.
- Demo Source Systems must not depend on downstream analytics models.
- Project repositories may depend on a pinned framework release, never on an unversioned copy of framework files.
- Project repositories do not call each other directly.

---

# 8. Files/folders intentionally not created yet

Planning a path does **not** mean the capability exists. Until its phase begins, do not create cosmetic placeholder content for:

- Kafka Connector;
- direct Snowpipe Streaming;
- Openflow;
- masking/row-access policies;
- production rollback automation;
- recovery procedures;
- semantic regression tooling;
- full reconciliation engine;
- full observability dashboards;
- PROD apply workflows.

The repository tree should grow with working capabilities, not ahead of them.

---

# 9. Next directory creation sequence

For **Phase 1 Platform Foundation**, create real files in this order:

1. `terraform/stacks/nonprod/` — provider/version/variable/stack boundary.
2. `terraform/modules/analytics-environment/` — first reusable Snowflake environment primitive.
3. `terraform/modules/warehouse/` — workload compute primitive.
4. `terraform/modules/rbac/` — capability roles/database roles/grants.
5. `terraform/modules/platform-control/` — structural control database/schemas.
6. `config/environments/nonprod.yml` — non-secret environment input where it adds value.
7. `.github/workflows/terraform-ci.yml` — format/validate checks only at first.
8. Add `prod/`, workload identity and cost-control paths only after NONPROD foundation is proven.

After each meaningful step, update `docs/PROJECT_BLUEPRINT.md` with actual implementation status and any architecture change.