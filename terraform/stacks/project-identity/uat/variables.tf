variable "oidc_audience" {
  description = "UAT Snowflake account-scoped OIDC audience shared by approved project deployment service identities."
  type        = string

  validation {
    condition     = length(trimspace(var.oidc_audience)) > 0 && lower(trimspace(var.oidc_audience)) != "snowflakecomputing.com"
    error_message = "oidc_audience must be a non-empty UAT-account-scoped value and must not use the shared snowflakecomputing.com audience."
  }
}
