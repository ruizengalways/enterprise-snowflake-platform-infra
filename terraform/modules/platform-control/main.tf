resource "snowflake_database" "this" {
  name                           = var.database_name
  comment                        = "Central runtime and operational control state for the Enterprise Snowflake Platform."
  data_retention_time_in_days    = var.retention_days
  drop_public_schema_on_creation = true
}

resource "snowflake_schema" "control" {
  for_each = var.schemas

  database                    = snowflake_database.this.name
  name                        = each.value
  comment                     = "Platform control schema ${each.value}; structural objects are Terraform-owned."
  with_managed_access         = "true"
  is_transient                = "false"
  data_retention_time_in_days = var.retention_days
}
