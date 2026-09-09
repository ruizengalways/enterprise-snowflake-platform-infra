# Full dataset reset is intentionally separate from ordinary development/deploy.
# AR_<DOMAIN>_RECOVERY is intended for Senior Data Engineer+ operators. Domain
# ADMIN inherits it so recovery never depends on one specific person being present.
#
# Recovery is deliberately practical rather than over-gated: the role can read
# its stable domain database and TRUNCATE reconstructable Silver/Gold tables, plus
# use the transform warehouse. Bronze is trusted landed evidence and remains
# read-only to this processing-recovery capability. The role does not receive
# INSERT/UPDATE/DELETE/OWNERSHIP and receives no direct DML on shared
# PLATFORM_CONTROL base tables.

locals {
  recovery_warehouse_pairs = {
    for item in flatten([
      for project_code, warehouses in var.recovery_warehouse_grants : [
        for warehouse_name in warehouses : {
          key            = "${project_code}|${warehouse_name}"
          project_code   = project_code
          warehouse_name = warehouse_name
        }
      ]
    ]) : item.key => item
  }

  # Processing reset must never destroy ingestion-owned Bronze evidence. Limit
  # destructive recovery privileges to the stable reconstructable processing
  # layers. DQ is intentionally excluded as well; dataset reset plans should name
  # only the relations they are responsible for rebuilding.
  recovery_schema_entries = {
    for key, entry in local.schema_entries : key => entry
    if contains([
      "SILVER_STAGING",
      "SILVER_INTERMEDIATE",
      "SILVER_CANONICAL",
      "GOLD_MARTS",
      "GOLD_SEMANTIC",
    ], entry.schema)
  }
}

resource "snowflake_account_role" "recovery" {
  provider = snowflake.securityadmin
  for_each = var.project_codes

  name    = "AR_${each.value}_RECOVERY"
  comment = "Senior engineer processing-recovery capability for ${each.value}; managed by enterprise-snowflake-platform-infra."
}

resource "snowflake_grant_account_role" "recovery_to_project_admin" {
  provider = snowflake.securityadmin
  for_each = var.project_codes

  role_name        = snowflake_account_role.recovery[each.value].name
  parent_role_name = snowflake_account_role.this["${each.value}|ADMIN"].name
}

# Recovery can inspect its own stable domain data through the existing READ
# database role, without inheriting normal DEVELOPER/DEPLOY capabilities.
resource "snowflake_grant_database_role" "read_to_project_recovery" {
  provider = snowflake.securityadmin
  for_each = local.database_project_pairs

  database_role_name = snowflake_database_role.project["${each.value.database}|${each.value.project}|READ"].fully_qualified_name
  parent_role_name   = snowflake_account_role.recovery[each.value.project].name
}

# Full processing reset needs TRUNCATE only on reconstructable Silver/Gold tables.
# Grant it on current and future tables in those schemas so newly deployed
# datasets remain recoverable without a Terraform change. Bronze is deliberately
# excluded: source re-ingestion/reset is a separate ingestion concern.
resource "snowflake_grant_privileges_to_account_role" "recovery_current_table_truncate" {
  provider = snowflake.securityadmin
  for_each = local.recovery_schema_entries

  privileges        = ["TRUNCATE"]
  account_role_name = snowflake_account_role.recovery[each.value.project].name

  on_schema_object {
    all {
      object_type_plural = "TABLES"
      in_schema          = each.value.schema_fqn
    }
  }
}

resource "snowflake_grant_privileges_to_account_role" "recovery_future_table_truncate" {
  provider = snowflake.securityadmin
  for_each = local.recovery_schema_entries

  privileges        = ["TRUNCATE"]
  account_role_name = snowflake_account_role.recovery[each.value.project].name

  on_schema_object {
    future {
      object_type_plural = "TABLES"
      in_schema          = each.value.schema_fqn
    }
  }
}

resource "snowflake_grant_privileges_to_account_role" "recovery_warehouse_usage" {
  provider = snowflake.securityadmin
  for_each = local.recovery_warehouse_pairs

  privileges        = ["USAGE"]
  account_role_name = snowflake_account_role.recovery[each.value.project_code].name

  on_account_object {
    object_type = "WAREHOUSE"
    object_name = each.value.warehouse_name
  }
}
