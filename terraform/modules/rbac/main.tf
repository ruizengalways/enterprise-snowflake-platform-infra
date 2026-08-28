locals {
  platform_capabilities = toset(["READER", "ENGINEER", "ADMIN"])
  project_capabilities  = toset(["GUEST", "READER", "DEVELOPER", "ADMIN"])
  database_access       = toset(["GUEST", "READ", "WRITE", "OWNER"])

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

  # Each analytics database has one owning data product/domain. This deliberately
  # avoids creating HEALTH database roles in TRANSPORT databases (and vice versa).
  database_project_pairs = {
    for database_name, project_code in var.database_projects :
    database_name => {
      database = database_name
      project  = project_code
    }
  }

  # Human GUEST access exists only where at least one published schema is declared.
  # CI databases intentionally publish no schemas, so domain guests receive no CI
  # database role and not even database USAGE there.
  guest_database_project_pairs = {
    for database_name, pair in local.database_project_pairs : database_name => pair
    if length(lookup(var.published_schemas_by_database, database_name, toset([]))) > 0
  }

  database_roles = {
    for item in flatten([
      for database_name, project_code in var.database_projects : [
        for access in local.database_access : {
          key      = "${database_name}|${project_code}|${access}"
          database = database_name
          project  = project_code
          access   = access
          name     = "DR_${project_code}_ANALYTICS_${access}"
        }
      ]
    ]) : item.key => item
  }

  schema_entries = {
    for item in flatten([
      for database_name, schemas in var.stable_schemas_by_database : [
        for schema_name in schemas : {
          key        = "${database_name}|${schema_name}"
          database   = database_name
          project    = var.database_projects[database_name]
          schema     = schema_name
          schema_fqn = "\"${database_name}\".\"${schema_name}\""
        }
      ]
    ]) : item.key => item
  }

  published_schema_entries = {
    for key, entry in local.schema_entries : key => entry
    if contains(lookup(var.published_schemas_by_database, entry.database, toset([])), entry.schema)
  }

  readable_object_grants = {
    for pair in setproduct(keys(local.schema_entries), toset(["TABLES", "VIEWS", "SEMANTIC VIEWS"])) :
    "${pair[0]}|${pair[1]}" => {
      schema             = local.schema_entries[pair[0]]
      object_type_plural = pair[1]
    }
  }

  guest_readable_object_grants = {
    for pair in setproduct(keys(local.published_schema_entries), toset(["TABLES", "VIEWS", "SEMANTIC VIEWS"])) :
    "${pair[0]}|${pair[1]}" => {
      schema             = local.published_schema_entries[pair[0]]
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

# Domain capability inheritance: GUEST -> READER -> DEVELOPER -> ADMIN.
# GUEST is intentionally the narrow published-data consumer role.
resource "snowflake_grant_account_role" "project_guest_to_reader" {
  provider = snowflake.securityadmin
  for_each = var.project_codes

  role_name        = snowflake_account_role.this["${each.value}|GUEST"].name
  parent_role_name = snowflake_account_role.this["${each.value}|READER"].name
}

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
# making platform administration imply domain administration.
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

# Database-role inheritance: GUEST -> READ -> WRITE -> OWNER.
resource "snowflake_grant_database_role" "guest_to_read" {
  provider = snowflake.securityadmin
  for_each = local.database_project_pairs

  database_role_name        = snowflake_database_role.project["${each.value.database}|${each.value.project}|GUEST"].fully_qualified_name
  parent_database_role_name = snowflake_database_role.project["${each.value.database}|${each.value.project}|READ"].fully_qualified_name
}

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

resource "snowflake_grant_database_role" "guest_to_project_guest" {
  provider = snowflake.securityadmin
  for_each = local.guest_database_project_pairs

  database_role_name = snowflake_database_role.project["${each.value.database}|${each.value.project}|GUEST"].fully_qualified_name
  parent_role_name   = snowflake_account_role.this["${each.value.project}|GUEST"].name
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

# GUEST can resolve only databases that explicitly publish consumer schemas.
resource "snowflake_grant_privileges_to_database_role" "guest_database_usage" {
  provider = snowflake.sysadmin
  for_each = local.guest_database_project_pairs

  privileges         = ["USAGE"]
  database_role_name = snowflake_database_role.project["${each.value.database}|${each.value.project}|GUEST"].fully_qualified_name
  on_database        = snowflake_database_role.project["${each.value.database}|${each.value.project}|GUEST"].database
}

resource "snowflake_grant_privileges_to_database_role" "guest_schema_usage" {
  provider = snowflake.sysadmin
  for_each = local.published_schema_entries

  privileges         = ["USAGE"]
  database_role_name = snowflake_database_role.project["${each.value.database}|${each.value.project}|GUEST"].fully_qualified_name

  on_schema {
    schema_name = each.value.schema_fqn
  }
}

resource "snowflake_grant_privileges_to_database_role" "guest_current_objects" {
  provider = snowflake.sysadmin
  for_each = local.guest_readable_object_grants

  privileges         = ["SELECT"]
  database_role_name = snowflake_database_role.project["${each.value.schema.database}|${each.value.schema.project}|GUEST"].fully_qualified_name

  on_schema_object {
    all {
      object_type_plural = each.value.object_type_plural
      in_schema          = each.value.schema.schema_fqn
    }
  }
}

resource "snowflake_grant_privileges_to_database_role" "guest_future_objects" {
  provider = snowflake.sysadmin
  for_each = local.guest_readable_object_grants

  privileges         = ["SELECT"]
  database_role_name = snowflake_database_role.project["${each.value.schema.database}|${each.value.schema.project}|GUEST"].fully_qualified_name

  on_schema_object {
    future {
      object_type_plural = each.value.object_type_plural
      in_schema          = each.value.schema.schema_fqn
    }
  }
}

# READER can inspect every stable domain schema. It also inherits GUEST.
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

# WRITE adds only the core schema-level DDL needed for ordinary dbt development.
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

# Warehouses are account objects, so USAGE is granted to account roles.
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
