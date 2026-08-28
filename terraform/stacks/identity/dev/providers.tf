# Identity bootstrap is intentionally privileged and separate from routine
# Terraform. Authentication material remains external to source control.
provider "snowflake" {
  role = "ACCOUNTADMIN"

  experimental_features_enabled = [
    "USER_ENABLE_DEFAULT_WORKLOAD_IDENTITY",
  ]
}
