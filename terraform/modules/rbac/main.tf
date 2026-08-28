locals {
  platform_capabilities = toset(["READER", "ENGINEER", "ADMIN"])
  project_capabilities  = toset(["READER", "DEVELOPER", "ADMIN"])
  database_access       = toset(["READ", "WRITE", "OWNER"])

  platform_roles = {
    for capability in local.platform_capabilities :
    "PLATFORM|${capability}" => {
      name       = "AR_PLATFORM_${capability}"
      scope      = "PLATFORM"
      capability = capability
    }
  }

  project_roles = {
    for pair in setproduct(var.project_codes, local.project_capabilities) :
    "${pair[0]}|${pair[1]}" => {
      name       = "AR_${pair[0]}_${pair[1]}"
      scope      = pair[0]
      capability = pair[1]
    }
  }

  account_roles = merge(local.platform_roles, local.project_roles)

  database_project_pairs = {
    for pair in setproduct(var.database_names, var.project_codes) :
    "${pair[0]}|${pair[1]}" => {
      database = pair[0]
      project  = pair[1]
    }
  }

  database_roles = {
    for triple in setproduct(var.database_names, var.project_codes, local.database_access) :
    "${triple[0]}|${triple[1]}|${triple[2]}" => {
      database = triple[0]
      project  = triple[1]
      access   = triple[2]
      name     = "DR_${triple[1]}_ANALYTICS_${triple[2]}"
    }
  }

  schema_entries = {
    for item in flatten([
      for database_name, schemas in var.stable_schemas_by_database : [
        for project_code in var.project_codes : [
          for schema_name in schemas : {
            key        = "${database_name}|${project_code}|${schema_name}"
            database   = database_name
            project    = project_code
            schema     = schema_name
            schema_fqn = "\"${database_name}\".\"${schema_name}\""
          } if startswith(schema_name, "${project_code}_")
        ]
      ]
    ]) : item.key => item
  }

  readable_object_grants = {
    for pair in setproduct(keys(local.schema_entries), toset(["TABLES", "VIEWS", "SEMANTIC VIEWS"])) :
    "${pair[0]}|${pair[1]}" => {
      schema             = local.schema_entries[pair[0]]
      object_type_plural = pair[1]
    }
  }

  flattened_warehouse_grants = {
    for item in flatten([
      for role_name, warehouses in var.warehouse_grants : [
        for warehouse_name in warehouses : {
          key            = "${role_name}|${warehouse_name}"
          role_name      = role_name
          warehouse_name = warehouse_name
        }
      ]
    ]) : item.key => item
  }
}

resource "snowflake_account_role" "this" {
  provider = snowflake.securityadmin
  for_each = local.account_roles

  name    = each.value.name
  comment = "Capability role for ${each.value.scope} ${each.value.capability}; managed by enterprise-snowflake-platform-infra."
}

# Capability inheritance: READER -> ENGINEER -> ADMIN for platform roles.
resource "snowflake_grant_account_role" "platform_reader_to_engineer" {
  provider = snowflake.securityadmin

  role_name        = snowflake_account_role.this["PLATFORM|READER"].name
  parent_role_name = snowflake_account_role.this["PLATFORM|ENGINEER"].name
}

resource "snowflake_grant_account_role" "platform_engineer_to_admin" {
  provider = snowflake.securityadmin

  role_name        = snowflake_account_role.this["PLATFORM|ENGINEER"].name
  parent_role_name = snowflake_account_role.this["PLATFORM|ADMIN"].name
}

# Capability inheritance: READER -> DEVELOPER -> ADMIN within each project.
resource "snowflake_grant_account_role" "project_reader_to_developer" {
  provider = snowflake.securityadmin
  for_each = var.project_codes

  role_name        = snowflake_account_role.this["${each.value}|READER"].name
  parent_role_name = snowflake_account_role.this["${each.value}|DEVELOPER"].name
}

resource "snowflake_grant_account_role" "project_developer_to_admin" {
  provider = snowflake.securityadmin
  for_each = var.project_codes

  role_name        = snowflake_account_role.this["${each.value}|DEVELOPER"].name
  parent_role_name = snowflake_account_role.this["${each.value}|ADMIN"].name
}

# Keep custom roles reachable from the Snowflake system-role hierarchy without
# making AR_PLATFORM_ADMIN automatically inherit every project role.
resource "snowflake_grant_account_role" "platform_admin_to_sysadmin" {
  provider = snowflake.securityadmin

  role_name        = snowflake_account_role.this["PLATFORM|ADMIN"].name
  parent_role_name = "SYSADMIN"
}

resource "snowflake_grant_account_role" "project_admin_to_sysadmin" {
  provider = snowflake.securityadmin
  for_each = var.project_codes

  role_name        = snowflake_account_role.this["${each.value}|ADMIN"].name
  parent_role_name = "SYSADMIN"
}

resource "snowflake_database_role" "project" {
  provider = snowflake.sysadmin
  for_each = local.database_roles

  database = each.value.database
  name     = each.value.name
  comment  = "${each.value.project} analytics ${each.value.access} access; managed by enterprise-snowflake-platform-infra."
}

# Database-role inheritance: READ -> WRITE -> OWNER.
resource "snowflake_grant_database_role" "read_to_write" {
  provider = snowflake.securityadmin
  for_each = local.database_project_pairs

  database_role_name        = snowflake_database_role.project["${each.value.database}|${each.value.project}|READ"].fully_qualified_name
  parent_database_role_name = snowflake_database_role.project["${each.value.database}|${each.value.project}|WRITE"].fully_qualified_name
}

resource "snowflake_grant_database_role" "write_to_owner" {
  provider = snowflake.securityadmin
  for_each = local.database_project_pairs

  database_role_name        = snowflake_database_role.project["${each.value.database}|${each.value.project}|WRITE"].fully_qualified_name
  parent_database_role_name = snowflake_database_role.project["${each.value.database}|${each.value.project}|OWNER"].fully_qualified_name
}

resource "snowflake_grant_database_role" "read_to_project_reader" {
  provider = snowflake.securityadmin
  for_each = local.database_project_pairs

  database_role_name = snowflake_database_role.project["${each.value.database}|${each.value.project}|READ"].fully_qualified_name
  parent_role_name   = snowflake_account_role.this["${each.value.project}|READER"].name
}

resource "snowflake_grant_database_role" "write_to_project_developer" {
  provider = snowflake.securityadmin
  for_each = var.grant_developer_write ? local.database_project_pairs : {}

  database_role_name = snowflake_database_role.project["${each.value.database}|${each.value.project}|WRITE"].fully_qualified_name
  parent_role_name   = snowflake_account_role.this["${each.value.project}|DEVELOPER"].name
}

resource "snowflake_grant_database_role" "owner_to_project_admin" {
  provider = snowflake.securityadmin
  for_each = local.database_project_pairs

  database_role_name = snowflake_database_role.project["${each.value.database}|${each.value.project}|OWNER"].fully_qualified_name
  parent_role_name   = snowflake_account_role.this["${each.value.project}|ADMIN"].name
}

# READ database roles can resolve the database and project-owned stable schemas.
resource "snowflake_grant_privileges_to_database_role" "read_database_usage" {
  provider = snowflake.sysadmin
  for_each = local.database_project_pairs

  privileges         = ["USAGE"]
  database_role_name = snowflake_database_role.project["${each.value.database}|${each.value.project}|READ"].fully_qualified_name
  on_database        = snowflake_database_role.project["${each.value.database}|${each.value.project}|READ"].database
}

resource "snowflake_grant_privileges_to_database_role" "read_schema_usage" {
  provider = snowflake.sysadmin
  for_each = local.schema_entries

  privileges         = ["USAGE"]
  database_role_name = snowflake_database_role.project["${each.value.database}|${each.value.project}|READ"].fully_qualified_name

  on_schema {
    schema_name = each.value.schema_fqn
  }
}

resource "snowflake_grant_privileges_to_database_role" "read_current_objects" {
  provider = snowflake.sysadmin
  for_each = local.readable_object_grants

  privileges         = ["SELECT"]
  database_role_name = snowflake_database_role.project["${each.value.schema.database}|${each.value.schema.project}|READ"].fully_qualified_name

  on_schema_object {
    all {
      object_type_plural = each.value.object_type_plural
      in_schema          = each.value.schema.schema_fqn
    }
  }
}

resource "snowflake_grant_privileges_to_database_role" "read_future_objects" {
  provider = snowflake.sysadmin
  for_each = local.readable_object_grants

  privileges         = ["SELECT"]
  database_role_name = snowflake_database_role.project["${each.value.schema.database}|${each.value.schema.project}|READ"].fully_qualified_name

  on_schema_object {
    future {
      object_type_plural = each.value.object_type_plural
      in_schema          = each.value.schema.schema_fqn
    }
  }
}

# WRITE adds the core schema-level DDL needed for normal dbt development.
# Stream/task/procedure privileges are added only when their implementation phase requires them.
resource "snowflake_grant_privileges_to_database_role" "write_schema_ddl" {
  provider = snowflake.sysadmin
  for_each = local.schema_entries

  privileges = [
    "CREATE FILE FORMAT",
    "CREATE SEQUENCE",
    "CREATE STAGE",
    "CREATE TABLE",
    "CREATE VIEW",
  ]

  database_role_name = snowflake_database_role.project["${each.value.database}|${each.value.project}|WRITE"].fully_qualified_name

  on_schema {
    schema_name = each.value.schema_fqn
  }
}

# Warehouse access is deliberately expressed against account roles because
# warehouses are account objects, not database-scoped objects.
resource "snowflake_grant_privileges_to_account_role" "warehouse_usage" {
  provider = snowflake.securityadmin
  for_each = local.flattened_warehouse_grants

  privileges        = ["USAGE"]
  account_role_name = each.value.role_name

  on_account_object {
    object_type = "WAREHOUSE"
    object_name = each.value.warehouse_name
  }

  depends_on = [snowflake_account_role.this]
}
