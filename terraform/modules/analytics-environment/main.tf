resource "snowflake_database" "this" {
  name                           = var.database_name
  comment                        = "Managed by enterprise-snowflake-platform-infra for ${upper(var.environment)} analytics workloads."
  data_retention_time_in_days    = var.database_retention_days
  drop_public_schema_on_creation = var.drop_public_schema
}

resource "snowflake_schema" "stable" {
  for_each = var.schemas

  database                    = snowflake_database.this.name
  name                        = each.value
  comment                     = "Stable ${upper(var.environment)} analytics schema managed by enterprise-snowflake-platform-infra."
  with_managed_access         = "true"
  is_transient                = "false"
  data_retention_time_in_days = var.schema_retention_days
}
