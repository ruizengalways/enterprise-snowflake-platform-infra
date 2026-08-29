output "service_user_name" {
  description = "Snowflake SERVICE user name."
  value       = snowflake_service_user.this.name
}

output "role_name" {
  description = "Existing role granted to the service user."
  value       = var.role_name
}

output "oidc_subject" {
  description = "OIDC subject trusted by the service user."
  value       = var.oidc_subject
}
