locals {
  config        = yamldecode(file("${path.root}/../../../config/environments/uat.yml"))
  project_codes = toset([for project in values(local.config.projects) : project.code])
}

module "analytics_environment" {
  source   = "../../modules/analytics-environment"
  for_each = local.config.analytics_databases

  providers = {
    snowflake = snowflake.objects
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
    snowflake = snowflake.objects
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
    snowflake = snowflake.objects
  }

  database_name  = local.config.platform_control.name
  schemas        = toset(local.config.platform_control.schemas)
  retention_days = local.config.platform_control.retention_days
}

module "rbac" {
  source = "../../modules/rbac"

  providers = {
    snowflake.securityadmin = snowflake.security
    snowflake.sysadmin      = snowflake.objects
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

  published_schemas_by_database = {
    for key, environment in module.analytics_environment :
    environment.database_name => toset(local.config.analytics_databases[key].published_schemas)
  }

  # UAT is production-like: human developers can query but do not receive WRITE.
  # Domain admins retain transform compute until deployment machine identity exists.
  grant_developer_write = false

  warehouse_grants = {
    AR_HEALTH_GUEST      = toset([module.warehouse["health_query"].fully_qualified_name])
    AR_HEALTH_ADMIN      = toset([module.warehouse["health_transform"].fully_qualified_name])
    AR_TRANSPORT_GUEST   = toset([module.warehouse["transport_query"].fully_qualified_name])
    AR_TRANSPORT_ADMIN   = toset([module.warehouse["transport_transform"].fully_qualified_name])
    AR_PLATFORM_ENGINEER = toset([module.warehouse["platform_ops"].fully_qualified_name])
  }
}
