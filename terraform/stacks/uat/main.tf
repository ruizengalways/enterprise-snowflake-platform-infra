locals {
  config        = yamldecode(file("${path.root}/../../../config/environments/uat.yml"))
  project_codes = toset([for project in values(local.config.projects) : project.code])
}

module "analytics_environment" {
  source   = "../../modules/analytics-environment"
  for_each = local.config.analytics_databases

  providers = {
    snowflake = snowflake.sysadmin
  }

  database_name           = each.value.name
  environment             = "uat-${each.key}"
  schemas                 = toset(each.value.schemas)
  database_retention_days = each.value.retention_days
  schema_retention_days   = each.value.retention_days
  drop_public_schema      = true
}

module "warehouse" {
  source   = "../../modules/warehouse"
  for_each = local.config.warehouses

  providers = {
    snowflake = snowflake.sysadmin
  }

  name                      = each.value.name
  warehouse_size            = each.value.size
  auto_suspend_seconds      = each.value.auto_suspend_seconds
  statement_timeout_seconds = each.value.statement_timeout_seconds
  comment                   = "UAT ${each.key} workload; managed by enterprise-snowflake-platform-infra."
}

module "platform_control" {
  source = "../../modules/platform-control"

  providers = {
    snowflake = snowflake.sysadmin
  }

  database_name  = local.config.platform_control.name
  schemas        = toset(local.config.platform_control.schemas)
  retention_days = local.config.platform_control.retention_days
}

module "rbac" {
  source = "../../modules/rbac"

  providers = {
    snowflake.securityadmin = snowflake.securityadmin
    snowflake.sysadmin      = snowflake.sysadmin
  }

  project_codes = local.project_codes

  database_projects = {
    for key, environment in module.analytics_environment :
    environment.database_name => local.config.analytics_databases[key].project_code
  }

  stable_schemas_by_database = {
    for key, environment in module.analytics_environment :
    environment.database_name => toset(local.config.analytics_databases[key].schemas)
  }

  # UAT is production-like: human developers can query but do not receive WRITE.
  # Automated deployment identity is introduced separately.
  grant_developer_write = false

  warehouse_grants = {
    AR_HEALTH_READER      = toset([module.warehouse["health_uat"].fully_qualified_name])
    AR_TRANSPORT_READER   = toset([module.warehouse["transport_uat"].fully_qualified_name])
    AR_PLATFORM_ENGINEER  = toset([module.warehouse["platform_ops"].fully_qualified_name])
  }
}
