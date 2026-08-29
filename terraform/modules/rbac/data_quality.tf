# Snowflake-native Data Quality Monitoring capability.
#
# Domain ADMIN is the narrow baseline role allowed to associate/schedule system
# Data Metric Functions. GUEST/READER/DEVELOPER intentionally do not receive the
# account-level serverless execution privilege.
#
# Project/framework DMF association DDL uses EXECUTE AS ROLE AR_<DOMAIN>_ADMIN,
# allowing this role to use inherited SELECT privileges without requiring object
# ownership transfer from the data-project lifecycle.
resource "snowflake_grant_privileges_to_account_role" "project_admin_execute_data_metric_function" {
  provider = snowflake.securityadmin
  for_each = var.project_codes

  privileges        = ["EXECUTE DATA METRIC FUNCTION"]
  account_role_name = snowflake_account_role.this["${each.value}|ADMIN"].name
  on_account        = true
}

# Snowflake owns the Data Quality Monitoring result store. Grant the official
# viewer application role rather than copying native DMF results into a custom
# platform table solely for observability.
resource "snowflake_grant_application_role" "project_admin_data_quality_viewer" {
  provider = snowflake.securityadmin
  for_each = var.project_codes

  application_role_name    = "\"SNOWFLAKE\".\"DATA_QUALITY_MONITORING_VIEWER\""
  parent_account_role_name = snowflake_account_role.this["${each.value}|ADMIN"].name
}
