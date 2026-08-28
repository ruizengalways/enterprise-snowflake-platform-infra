output "account_names" {
  description = "Environment Snowflake accounts created by the organization bootstrap."
  value       = { for key, account in snowflake_account.environment : key => account.name }
}

output "account_fully_qualified_names" {
  description = "Fully qualified Snowflake account identifiers for downstream bootstrap/reference."
  value       = { for key, account in snowflake_account.environment : key => account.fully_qualified_name }
}
