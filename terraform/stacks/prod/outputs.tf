output "analytics_databases" {
  description = "PROD analytics databases by logical environment."
  value       = { for key, environment in module.analytics_environment : key => environment.database_name }
}

output "warehouses" {
  description = "PROD warehouses by workload key."
  value       = { for key, warehouse in module.warehouse : key => warehouse.name }
}

output "platform_control_database" {
  description = "PROD platform control database."
  value       = module.platform_control.database_name
}

output "account_roles" {
  description = "PROD platform and project capability roles."
  value       = module.rbac.account_role_names
}

output "database_roles" {
  description = "PROD project database roles."
  value       = module.rbac.database_role_fully_qualified_names
}
