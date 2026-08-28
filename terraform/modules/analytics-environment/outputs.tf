output "database_name" {
  description = "Created analytics database name."
  value       = snowflake_database.this.name
}

output "database_fully_qualified_name" {
  description = "Created analytics database fully qualified name."
  value       = snowflake_database.this.fully_qualified_name
}

output "schema_names" {
  description = "Stable schema names managed by this module."
  value       = { for key, schema in snowflake_schema.stable : key => schema.name }
}

output "schema_fully_qualified_names" {
  description = "Stable schema fully qualified names managed by this module."
  value       = { for key, schema in snowflake_schema.stable : key => schema.fully_qualified_name }
}
