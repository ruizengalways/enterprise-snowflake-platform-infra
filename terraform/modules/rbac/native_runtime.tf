# Project deployment is a machine capability, separate from the human
# GUEST/READER/DEVELOPER/ADMIN chain. It receives the ordinary analytics WRITE
# database role for dbt-managed data objects, then only the extra Snowflake-native
# schema/account privileges required for Streams, Tasks and Dynamic Tables.

resource "snowflake_grant_database_role" "write_to_project_deploy" {
  provider = snowflake.securityadmin
  for_each = local.database_project_pairs

  database_role_name = snowflake_database_role.project["${each.value.database}|${each.value.project}|WRITE"].fully_qualified_name
  parent_role_name   = snowflake_account_role.this["${each.value.project}|DEPLOY"].name
}

resource "snowflake_grant_privileges_to_account_role" "deploy_native_schema_ddl" {
  provider = snowflake.securityadmin
  for_each = local.schema_entries

  privileges = [
    "CREATE DYNAMIC TABLE",
    "CREATE STREAM",
    "CREATE TASK",
  ]

  account_role_name = snowflake_account_role.this["${each.value.project}|DEPLOY"].name

  on_schema {
    schema_name = each.value.schema_fqn
  }
}

# Snowflake requires the role that owns a Task to retain the global EXECUTE TASK
# privilege for warehouse-backed tasks to run. Serverless EXECUTE MANAGED TASK is
# intentionally not granted because the platform baseline uses named warehouses.
resource "snowflake_grant_privileges_to_account_role" "deploy_execute_task" {
  provider = snowflake.securityadmin
  for_each = var.project_codes

  privileges        = ["EXECUTE TASK"]
  account_role_name = snowflake_account_role.this["${each.value}|DEPLOY"].name
  on_account        = true
}
