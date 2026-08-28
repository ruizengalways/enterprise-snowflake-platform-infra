# Authentication is intentionally external to source control. CI/CD will use
# workload identity federation once the trust model is implemented.
provider "snowflake" {
  alias = "sysadmin"
  role  = "SYSADMIN"
}

provider "snowflake" {
  alias = "securityadmin"
  role  = "SECURITYADMIN"
}
