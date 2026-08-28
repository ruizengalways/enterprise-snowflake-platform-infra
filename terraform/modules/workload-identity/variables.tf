variable "service_user_name" {
  description = "Snowflake SERVICE user used by GitHub Actions Terraform automation."
  type        = string
}

variable "role_name" {
  description = "Dedicated account role used by Terraform automation."
  type        = string
}

variable "oidc_issuer" {
  description = "OIDC issuer trusted by the Snowflake service user."
  type        = string
}

variable "oidc_subject" {
  description = "Exact OIDC subject allowed to authenticate as the service user."
  type        = string
}

variable "oidc_audience" {
  description = "Account-scoped OIDC audience requested by GitHub Actions and trusted by Snowflake."
  type        = string

  validation {
    condition     = length(trimspace(var.oidc_audience)) > 0 && lower(trimspace(var.oidc_audience)) != "snowflakecomputing.com"
    error_message = "oidc_audience must be a non-empty account-scoped value; do not use the shared snowflakecomputing.com audience for this platform identity."
  }
}

variable "account_privileges" {
  description = "Account-level privileges granted to the routine Terraform role."
  type        = set(string)
  default = [
    "CREATE DATABASE",
    "CREATE ROLE",
    "CREATE WAREHOUSE",
    "MANAGE GRANTS",
  ]
}
