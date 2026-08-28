variable "oidc_audience" {
  description = "Account-scoped OIDC audience for the UAT Snowflake account. Supply at plan/apply time; do not use snowflakecomputing.com."
  type        = string
}
