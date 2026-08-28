output "database_name" {
  description = "Platform control database name."
  value       = snowflake_database.this.name
}

output "database_fully_qualified_name" {
  description = "Platform control database fully qualified name."
  value       = snowflake_database.this.fully_qualified_name
}

output "schema_fully_qualified_names" {
  description = "Platform control schema fully qualified names."
  value       = { for key, schema in snowflake_schema.control : key => schema.fully_qualified_name }
}
