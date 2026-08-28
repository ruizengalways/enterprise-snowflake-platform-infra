output "analytics_databases" {
  description = "DEV account analytics databases by workload key."
  value       = { for key, environment in module.analytics_environment : key => environment.database_name }
}

output "warehouses" {
  description = "DEV account warehouses by workload key."
  value       = { for key, warehouse in module.warehouse : key => warehouse.name }
}

output "platform_control_database" {
  description = "DEV account platform control database."
  value       = module.platform_control.database_name
}

output "account_roles" {
  description = "DEV account platform and project capability roles."
  value       = module.rbac.account_role_names
}

output "database_roles" {
  description = "DEV account project database roles."
  value       = module.rbac.database_role_fully_qualified_names
}
