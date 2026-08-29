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
  description = "DEV account platform and human domain capability roles."
  value       = module.rbac.account_role_names
}

output "database_roles" {
  description = "DEV stable database human domain roles."
  value       = module.rbac.database_role_fully_qualified_names
}

output "ci_account_roles" {
  description = "DEV machine-only CI account roles keyed by domain."
  value       = module.workspace_access.ci_account_roles
}

output "ci_database_roles" {
  description = "DEV CI workspace database roles keyed by CI database."
  value       = module.workspace_access.ci_database_roles
}
