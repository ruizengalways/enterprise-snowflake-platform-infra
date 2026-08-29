output "ci_account_roles" {
  description = "Machine-only CI account role names keyed by domain code."
  value = {
    for project_code, role in snowflake_account_role.ci :
    project_code => role.name
  }
}

output "ci_database_roles" {
  description = "CI workspace database role fully-qualified names keyed by database."
  value = {
    for database_name, role in snowflake_database_role.ci_workspace :
    database_name => role.fully_qualified_name
  }
}
