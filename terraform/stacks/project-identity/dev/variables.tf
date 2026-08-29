variable "oidc_audience" {
  description = "DEV Snowflake account-scoped OIDC audience shared by approved project CI and deployment service identities."
  type        = string

  validation {
    condition     = length(trimspace(var.oidc_audience)) > 0 && lower(trimspace(var.oidc_audience)) != "snowflakecomputing.com"
    error_message = "oidc_audience must be a non-empty DEV-account-scoped value and must not use the shared snowflakecomputing.com audience."
  }
}
