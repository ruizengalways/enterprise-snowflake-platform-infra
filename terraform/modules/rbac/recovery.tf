# Full dataset reset is intentionally separate from ordinary development/deploy.
# AR_<DOMAIN>_RECOVERY is intended for Senior Data Engineer+ operators. Domain
# ADMIN inherits it so recovery never depends on one specific person being present.

resource "snowflake_account_role" "recovery" {
  provider = snowflake.securityadmin
  for_each = var.project_codes

  name    = "AR_${each.value}_RECOVERY"
  comment = "Senior engineer recovery capability for ${each.value} full dataset reset; managed by enterprise-snowflake-platform-infra."
}

resource "snowflake_grant_account_role" "recovery_to_project_admin" {
  provider = snowflake.securityadmin
  for_each = var.project_codes

  role_name        = snowflake_account_role.recovery[each.value].name
  parent_role_name = snowflake_account_role.this["${each.value}|ADMIN"].name
}
