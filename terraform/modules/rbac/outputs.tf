output "account_role_names" {
  description = "Capability account roles keyed by scope and capability."
  value       = { for key, role in snowflake_account_role.this : key => role.name }
}

output "database_role_fully_qualified_names" {
  description = "Project database roles keyed by database, project and access level."
  value       = { for key, role in snowflake_database_role.project : key => role.fully_qualified_name }
}
