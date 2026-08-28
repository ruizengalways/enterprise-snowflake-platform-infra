output "service_user_name" {
  value       = snowflake_service_user.terraform.name
  description = "Snowflake service user trusted for GitHub OIDC."
}

output "role_name" {
  value       = snowflake_account_role.terraform.name
  description = "Dedicated Terraform execution role."
}

output "oidc_subject" {
  value       = var.oidc_subject
  description = "Exact GitHub OIDC subject trusted by Snowflake."
}

output "oidc_audience" {
  value       = var.oidc_audience
  description = "Account-scoped OIDC audience trusted by Snowflake."
}
