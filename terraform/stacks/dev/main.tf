locals {
  config        = yamldecode(file("${path.root}/../../../config/environments/dev.yml"))
  project_codes = toset([for project in values(local.config.projects) : project.code])
}

module "analytics_environment" {
  source   = "../../modules/analytics-environment"
  for_each = local.config.analytics_databases

  providers = {
    snowflake = snowflake.objects
  }

  database_name           = each.value.name
  environment             = "dev-${each.key}"
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
  comment                   = "DEV account ${each.key} workload; managed by enterprise-snowflake-platform-infra."
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

  # Human domain roles are attached only to stable DEV_<DOMAIN> databases.
  # CI_<DOMAIN> databases are intentionally excluded and handled by the
  # machine-only workspace_access module below.
  database_projects = {
    for key, environment in module.analytics_environment :
    environment.database_name => local.config.analytics_databases[key].project_code
    if startswith(environment.database_name, "DEV_")
  }

  stable_schemas_by_database = {
    for key, environment in module.analytics_environment :
    environment.database_name => toset(local.config.analytics_databases[key].schemas)
    if startswith(environment.database_name, "DEV_")
  }

  published_schemas_by_database = {
    for key, environment in module.analytics_environment :
    environment.database_name => toset(local.config.analytics_databases[key].published_schemas)
    if startswith(environment.database_name, "DEV_")
  }

  # DEV is the only human environment where DEVELOPER receives WRITE.
  grant_developer_write = true

  warehouse_grants = merge(
    {
      for project in values(local.config.projects) :
      "AR_${project.code}_GUEST" => toset([
        module.warehouse[project.warehouse_keys.query].fully_qualified_name,
      ])
    },
    {
      for project in values(local.config.projects) :
      "AR_${project.code}_DEVELOPER" => toset([
        module.warehouse[project.warehouse_keys.transform].fully_qualified_name,
      ])
    },
    {
      for project in values(local.config.projects) :
      "AR_${project.code}_DEPLOY" => toset([
        module.warehouse[project.warehouse_keys.transform].fully_qualified_name,
      ])
    },
    {
      AR_PLATFORM_ENGINEER = toset([module.warehouse["platform_ops"].fully_qualified_name])
    },
  )
}

module "workspace_access" {
  source = "../../modules/workspace-access"

  providers = {
    snowflake.objects  = snowflake.objects
    snowflake.security = snowflake.security
  }

  developer_databases = {
    for key, environment in module.analytics_environment :
    environment.database_name => local.config.analytics_databases[key].project_code
    if startswith(environment.database_name, "DEV_")
  }

  ci_databases = {
    for key, environment in module.analytics_environment :
    environment.database_name => local.config.analytics_databases[key].project_code
    if startswith(environment.database_name, "CI_")
  }

  ci_warehouses_by_project = {
    for project in values(local.config.projects) :
    project.code => module.warehouse[project.warehouse_keys.ci].fully_qualified_name
  }

  depends_on = [module.rbac]
}
