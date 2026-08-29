variable "service_user_name" {
  description = "Snowflake SERVICE user name for an external workload."
  type        = string
}

variable "role_name" {
  description = "Existing Snowflake account role granted to the service user. The module does not create this role."
  type        = string
}

variable "oidc_issuer" {
  description = "OIDC issuer trusted by Snowflake."
  type        = string
}

variable "oidc_subject" {
  description = "Exact OIDC subject trusted by the Snowflake service user."
  type        = string
}

variable "oidc_audience" {
  description = "Account-scoped OIDC audience requested by the workload and trusted by Snowflake."
  type        = string

  validation {
    condition     = length(trimspace(var.oidc_audience)) > 0 && lower(trimspace(var.oidc_audience)) != "snowflakecomputing.com"
    error_message = "oidc_audience must be a non-empty account-scoped value; do not use the shared snowflakecomputing.com audience for project identities."
  }
}

variable "comment" {
  description = "Service-user comment."
  type        = string
  default     = "GitHub Actions workload identity; no password or private key."
}
