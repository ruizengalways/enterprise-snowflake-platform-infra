locals {
  ci_projects = toset(values(var.ci_databases))
}

# Personal DEV schemas are a developer workspace convention, not a security
# boundary between individual developers. The shared domain WRITE database role
# receives CREATE SCHEMA only in DEV_<DOMAIN> databases selected by the root.
resource "snowflake_grant_privileges_to_database_role" "developer_create_schema" {
  provider = snowflake.objects
  for_each = var.developer_databases

  privileges = ["CREATE SCHEMA"]

  database_role_name = "\"${each.key}\".\"DR_${each.value}_ANALYTICS_WRITE\""
  on_database        = each.key
}

# PR CI workspaces use a separate machine-only account role per domain. They do
# not inherit the human GUEST/READER/DEVELOPER/ADMIN hierarchy.
resource "snowflake_account_role" "ci" {
  provider = snowflake.security
  for_each = local.ci_projects

  name    = "AR_${each.value}_CI"
  comment = "Machine-only ${each.value} PR CI workspace role; managed by enterprise-snowflake-platform-infra."
}

resource "snowflake_grant_account_role" "ci_to_sysadmin" {
  provider = snowflake.security
  for_each = local.ci_projects

  role_name        = snowflake_account_role.ci[each.value].name
  parent_role_name = "SYSADMIN"
}

resource "snowflake_database_role" "ci_workspace" {
  provider = snowflake.objects
  for_each = var.ci_databases

  database = each.key
  name     = "DR_${each.value}_CI_WORKSPACE"
  comment  = "${each.value} ephemeral PR workspace creation in ${each.key}; managed by enterprise-snowflake-platform-infra."
}

resource "snowflake_grant_privileges_to_database_role" "ci_database_workspace" {
  provider = snowflake.objects
  for_each = var.ci_databases

  privileges = [
    "CREATE SCHEMA",
    "USAGE",
  ]

  database_role_name = snowflake_database_role.ci_workspace[each.key].fully_qualified_name
  on_database        = each.key
}

resource "snowflake_grant_database_role" "ci_workspace_to_account_role" {
  provider = snowflake.security
  for_each = var.ci_databases

  database_role_name = snowflake_database_role.ci_workspace[each.key].fully_qualified_name
  parent_role_name   = snowflake_account_role.ci[each.value].name
}

resource "snowflake_grant_privileges_to_account_role" "ci_warehouse_usage" {
  provider = snowflake.security
  for_each = var.ci_warehouses_by_project

  privileges        = ["USAGE"]
  account_role_name = snowflake_account_role.ci[each.key].name

  on_account_object {
    object_type = "WAREHOUSE"
    object_name = each.value
  }
}
