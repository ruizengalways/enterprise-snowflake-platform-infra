# Project workload identity bootstrap is privileged and runs only after the UAT
# platform stack has created AR_<DOMAIN>_DEPLOY roles. Authentication stays external.
provider "snowflake" {
  role = "ACCOUNTADMIN"

  experimental_features_enabled = [
    "USER_ENABLE_DEFAULT_WORKLOAD_IDENTITY",
  ]
}
