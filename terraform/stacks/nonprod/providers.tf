# Authentication is intentionally not configured here. The Snowflake provider
# reads organization/account/user/credential material from supported environment
# variables or local config. CI/CD will move to workload identity federation.
provider "snowflake" {
  alias = "sysadmin"
  role  = "SYSADMIN"
}

provider "snowflake" {
  alias = "securityadmin"
  role  = "SECURITYADMIN"
}
