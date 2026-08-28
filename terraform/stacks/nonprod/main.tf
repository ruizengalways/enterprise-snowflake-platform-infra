locals {
  config        = yamldecode(file("${path.root}/../../../config/environments/nonprod.yml"))
  project_codes = toset([for project in values(local.config.projects) : project.code])
}

module "analytics_environment" {
  source   = "../../modules/analytics-environment"
  for_each = local.config.analytics_databases

  providers = {
    snowflake = snowflake.sysadmin
  }

  database_name           = each.value.name
  environment             = "nonprod-${each.key}"
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
  comment                   = "NONPROD ${each.key} workload; managed by enterprise-snowflake-platform-infra."
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

  project_codes   = local.project_codes
  database_names = toset([for environment in module.analytics_environment : environment.database_name])

  stable_schemas_by_database = {
    for key, environment in module.analytics_environment :
    environment.database_name => toset(local.config.analytics_databases[key].schemas)
  }

  # NONPROD developers build in stable DEV/UAT project schemas. Personal and PR
  # schema lifecycle is introduced with the delivery framework, not here.
  grant_developer_write = true

  warehouse_grants = {
    AR_HEALTH_READER      = toset([module.warehouse["health_uat"].fully_qualified_name])
    AR_HEALTH_DEVELOPER   = toset([module.warehouse["health_dev"].fully_qualified_name])
    AR_TRANSPORT_READER   = toset([module.warehouse["transport_uat"].fully_qualified_name])
    AR_TRANSPORT_DEVELOPER = toset([module.warehouse["transport_dev"].fully_qualified_name])
    AR_PLATFORM_ENGINEER  = toset([module.warehouse["platform_ops"].fully_qualified_name])
  }
}
