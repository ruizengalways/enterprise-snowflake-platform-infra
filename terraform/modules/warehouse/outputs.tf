output "name" {
  description = "Warehouse name."
  value       = snowflake_warehouse.this.name
}

output "fully_qualified_name" {
  description = "Warehouse fully qualified name."
  value       = snowflake_warehouse.this.fully_qualified_name
}
