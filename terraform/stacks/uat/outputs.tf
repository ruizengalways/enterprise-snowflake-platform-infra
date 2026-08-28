output "analytics_databases" {
  description = "UAT account analytics databases by workload key."
  value       = { for key, environment in module.analytics_environment : key => environment.database_name }
}

output "warehouses" {
  description = "UAT account warehouses by workload key."
  value       = { for key, warehouse in module.warehouse : key => warehouse.name }
}

output "platform_control_database" {
  description = "UAT account platform control database."
  value       = module.platform_control.database_name
}

output "account_roles" {
  description = "UAT account platform and project capability roles."
  value       = module.rbac.account_role_names
}

output "database_roles" {
  description = "UAT account project database roles."
  value       = module.rbac.database_role_fully_qualified_names
}
